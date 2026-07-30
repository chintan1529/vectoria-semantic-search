"""
Application Startup — Elite Boot Manager with granular state machine.

State Machine:
  UNINITIALIZED → STARTING → LOADING_INDEX → LOADING_MODELS → VERIFYING_PROVIDERS → READY
                                                                                    ↘ ERROR

Guarantees:
  - Per-subsystem readiness tracking
  - Global readiness gate for all routes
  - No route serves traffic until READY
  - Every boot stage logged with timing
"""
import time
from enum import Enum
from typing import Optional, Dict
from vectoria.retrieval.engine import SearchEngine
from vectoria.generation.llm_client import LLMClient
from vectoria.generation.rag_pipeline import RAGPipeline
from backend.providers.factory import ProviderFactory
from backend.providers.base_provider import BaseLLMProvider
from backend.core.config import settings
from backend.core.logging import logger


class BootState(str, Enum):
    """Granular application boot states."""
    UNINITIALIZED = "UNINITIALIZED"
    STARTING = "STARTING"
    LOADING_INDEX = "LOADING_INDEX"
    LOADING_MODELS = "LOADING_MODELS"
    VERIFYING_PROVIDERS = "VERIFYING_PROVIDERS"
    READY = "READY"
    ERROR = "ERROR"

# Keep backward compat alias
ModelState = BootState


class SubsystemStatus:
    """Tracks readiness of individual subsystems."""
    def __init__(self):
        self.search_engine: bool = False
        self.embedding_model: bool = False
        self.reranker: bool = False
        self.provider: bool = False
        self.rag_pipeline: bool = False

    def all_ready(self) -> bool:
        return all([
            self.search_engine,
            self.embedding_model,
            self.reranker,
            self.provider,
            self.rag_pipeline,
        ])

    def to_dict(self) -> Dict[str, bool]:
        return {
            "search_engine": self.search_engine,
            "embedding_model": self.embedding_model,
            "reranker": self.reranker,
            "provider": self.provider,
            "rag_pipeline": self.rag_pipeline,
        }

    def failed_subsystems(self) -> list:
        return [k for k, v in self.to_dict().items() if not v]


class AppState:
    """Holds global singleton instances for the FastAPI application."""
    engine: Optional[SearchEngine] = None
    llm: Optional[LLMClient] = None
    rag: Optional[RAGPipeline] = None
    model_state: BootState = BootState.UNINITIALIZED
    subsystems: SubsystemStatus = SubsystemStatus()
    startup_time_ms: int = 0
    startup_error: Optional[str] = None

    @property
    def is_ready(self) -> bool:
        return self.model_state == BootState.READY and self.subsystems.all_ready()

    def readiness_report(self) -> dict:
        """Returns a structured readiness report for the /api/ready endpoint."""
        return {
            "boot_state": self.model_state.value,
            "is_ready": self.is_ready,
            "subsystems": self.subsystems.to_dict(),
            "failed": self.subsystems.failed_subsystems(),
            "startup_time_ms": self.startup_time_ms,
            "error": self.startup_error,
        }


state = AppState()


def require_ready():
    """Global readiness gate. Call at the top of every route handler.
    
    Raises HTTPException 503 with structured readiness report if not ready.
    """
    from fastapi import HTTPException
    if not state.is_ready:
        report = state.readiness_report()
        raise HTTPException(
            status_code=503,
            detail={
                "error": "SYSTEM_NOT_READY",
                "message": f"System is in state {state.model_state.value}. "
                           f"Failed subsystems: {report['failed']}",
                "readiness": report,
            },
        )


def startup_event():
    """Application startup lifecycle — granular boot manager.
    
    Stages:
      1. STARTING         → Configuration loaded & validated
      2. LOADING_INDEX     → Search engine (chunks, FAISS, mapping)
      3. LOADING_MODELS    → Embedding model + reranker warmed up
      4. VERIFYING_PROVIDERS → LLM provider initialized + RAG pipeline built
      5. READY             → All subsystems verified
    """
    total_start = time.perf_counter()

    # --- Stage 1: STARTING & Strict Config Validation ---
    state.model_state = BootState.STARTING
    state.subsystems = SubsystemStatus()
    logger.info("APPLICATION_START | state=STARTING")
    
    from backend.core.config_validator import validate_environment, print_startup_matrix
    validation_res = validate_environment()
    logger.info("CONFIG_VALIDATED | chat=%s research=%s", settings.vectoria_chat_provider, settings.vectoria_research_provider)

    try:
        # --- Stage 2: LOADING_INDEX ---
        state.model_state = BootState.LOADING_INDEX
        logger.info("BOOT_STAGE | state=LOADING_INDEX")
        stage_start = time.perf_counter()
        state.engine = SearchEngine()
        state.engine.load()
        engine_ms = int((time.perf_counter() - stage_start) * 1000)
        state.subsystems.search_engine = True
        logger.info("INDEX_LOADED | latency_ms=%d chunks=%d", engine_ms, 
                     len(state.engine.chunks) if hasattr(state.engine, 'chunks') else 0)

        # --- Stage 3: LOADING_MODELS ---
        state.model_state = BootState.LOADING_MODELS
        logger.info("BOOT_STAGE | state=LOADING_MODELS")
        stage_start = time.perf_counter()
        state.engine.search("warmup", top_k=1)
        warmup_ms = int((time.perf_counter() - stage_start) * 1000)
        state.subsystems.embedding_model = True
        state.subsystems.reranker = True
        logger.info("EMBEDDING_MODEL_LOADED | warmup_ms=%d", warmup_ms)
        logger.info("RERANKER_LOADED | warmup_ms=%d", warmup_ms)

        # --- Stage 4: VERIFYING_PROVIDERS ---
        state.model_state = BootState.VERIFYING_PROVIDERS
        logger.info("BOOT_STAGE | state=VERIFYING_PROVIDERS")
        state.llm = ProviderFactory.create_chat_provider()

        if state.llm:
            info = state.llm.model_info()
            state.subsystems.provider = True
            logger.info("PROVIDER_INITIALIZED | providers=%s",
                        [p.get('provider') for p in info.get('providers', [])])
        else:
            logger.error("PROVIDER_FAILED | No LLM providers could be initialized")

        state.rag = RAGPipeline(
            engine=state.engine,
            llm_client=state.llm,
            top_k=settings.vectoria_top_k_default,
            max_context_chars=settings.vectoria_max_context_tokens,
            min_score_threshold=-100.0,
        )
        state.subsystems.rag_pipeline = True

        # --- Stage 5: READY ---
        if state.subsystems.all_ready():
            state.model_state = BootState.READY
            print_startup_matrix(validation_res, total_start)
        else:
            state.model_state = BootState.ERROR
            state.startup_error = f"Subsystems failed: {state.subsystems.failed_subsystems()}"

        state.startup_time_ms = int((time.perf_counter() - total_start) * 1000)
        logger.info(
            "READY_STATE_REACHED | state=%s startup_ms=%d subsystems=%s",
            state.model_state.value, state.startup_time_ms, state.subsystems.to_dict(),
        )

    except Exception as e:
        state.model_state = BootState.ERROR
        state.startup_error = str(e)
        state.startup_time_ms = int((time.perf_counter() - total_start) * 1000)
        logger.error("STARTUP_FAILED | error=%s elapsed_ms=%d", e, state.startup_time_ms, exc_info=True)
        raise


def shutdown_event():
    """Application shutdown lifecycle event."""
    logger.info("SHUTDOWN | Releasing resources...")
    state.engine = None
    state.llm = None
    state.rag = None
    state.model_state = BootState.UNINITIALIZED
    state.subsystems = SubsystemStatus()
