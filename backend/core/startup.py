"""
Application Startup — Model lifecycle management with readiness tracking.

Ensures:
  - Models are loaded once at startup
  - Reranker is eagerly warmed up (no cold-start on first query)
  - Explicit readiness state tracking
  - Clear logging at each stage
"""
import time
from enum import Enum
from typing import Optional
from vectoria.retrieval.engine import SearchEngine
from vectoria.generation.llm_client import LLMClient
from vectoria.generation.rag_pipeline import RAGPipeline
from backend.core.config import settings
from backend.core.logging import logger


class ModelState(str, Enum):
    """Tracks the lifecycle state of the model subsystem."""
    UNINITIALIZED = "uninitialized"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


class AppState:
    """Holds global singleton instances for the FastAPI application."""
    engine: Optional[SearchEngine] = None
    llm: Optional[LLMClient] = None
    rag: Optional[RAGPipeline] = None
    model_state: ModelState = ModelState.UNINITIALIZED
    startup_time_ms: int = 0
    startup_error: Optional[str] = None

    @property
    def is_ready(self) -> bool:
        return self.model_state == ModelState.READY


state = AppState()


def startup_event():
    """Application startup lifecycle event. Loads models and indexes into memory.
    
    Stages:
      1. Load search engine (chunks, FAISS index, mapping)
      2. Initialize LLM client
      3. Initialize RAG pipeline
      4. Warm up embedding model (lazy-loaded on first encode)
      5. Warm up reranker model (lazy-loaded on first rerank)
    """
    total_start = time.perf_counter()
    state.model_state = ModelState.LOADING
    logger.info("Initializing application state...")

    try:
        # 1. Load search engine
        stage_start = time.perf_counter()
        state.engine = SearchEngine()
        state.engine.load()
        engine_ms = int((time.perf_counter() - stage_start) * 1000)
        logger.info(f"[Stage 1/5] Search engine loaded | latency_ms={engine_ms}")

        # 2. Initialize LLM client
        state.llm = LLMClient(
            api_key=settings.vectoria_llm_api_key,
            model_name=settings.vectoria_model_name,
        )
        logger.info("[Stage 2/5] LLM client initialized")

        # 3. Initialize RAG pipeline
        state.rag = RAGPipeline(
            engine=state.engine,
            llm_client=state.llm,
            top_k=settings.vectoria_top_k_default,
            max_context_chars=settings.vectoria_max_context_tokens,
            min_score_threshold=-100.0,
        )
        logger.info("[Stage 3/5] RAG pipeline initialized")

        # 4. Warm up embedding model + FAISS + BM25 + reranker with dummy search
        logger.info("[Stage 4/5] Warming up embedding and reranking models...")
        stage_start = time.perf_counter()
        state.engine.search("warmup", top_k=1)
        warmup_ms = int((time.perf_counter() - stage_start) * 1000)
        logger.info(f"[Stage 4/5] Models warmed up | latency_ms={warmup_ms}")

        # 5. Validate readiness
        assert state.engine is not None, "Engine failed to load"
        assert state.llm is not None, "LLM client failed to initialize"
        logger.info("[Stage 5/5] Readiness validation passed")

        state.model_state = ModelState.READY
        state.startup_time_ms = int((time.perf_counter() - total_start) * 1000)

        logger.info(
            "Application state initialized successfully | "
            f"total_startup_ms={state.startup_time_ms} state={state.model_state.value}"
        )

    except Exception as e:
        state.model_state = ModelState.ERROR
        state.startup_error = str(e)
        state.startup_time_ms = int((time.perf_counter() - total_start) * 1000)
        logger.error(
            f"Startup failed | error={e} elapsed_ms={state.startup_time_ms}",
            exc_info=True,
        )
        raise


def shutdown_event():
    """Application shutdown lifecycle event."""
    logger.info("Shutting down application state...")
    state.engine = None
    state.llm = None
    state.rag = None
    state.model_state = ModelState.UNINITIALIZED
