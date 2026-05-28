from typing import Optional
from vectoria.retrieval.engine import SearchEngine
from vectoria.generation.llm_client import LLMClient
from vectoria.generation.rag_pipeline import RAGPipeline
from backend.core.config import settings
from backend.core.logging import logger

class AppState:
    """Holds global singleton instances for the FastAPI application."""
    engine: Optional[SearchEngine] = None
    llm: Optional[LLMClient] = None
    rag: Optional[RAGPipeline] = None

state = AppState()

def startup_event():
    """Application startup lifecycle event. Loads models and indexes into memory."""
    logger.info("Initializing application state...")
    
    # Initialize and load the core Vectoria search engine
    state.engine = SearchEngine()
    state.engine.load()
    
    # Initialize the LLM client
    state.llm = LLMClient(
        api_key=settings.vectoria_llm_api_key,
        model_name=settings.vectoria_model_name
    )
    
    # Initialize the high-level RAG pipeline
    state.rag = RAGPipeline(
        engine=state.engine,
        llm_client=state.llm,
        top_k=settings.vectoria_top_k_default,
        max_context_chars=settings.vectoria_max_context_tokens,
        min_score_threshold=-100.0  # CrossEncoder logits can be negative, allow all
    )
    
    # Warm up the models by triggering a dummy search to eagerly load transformers
    logger.info("Warming up embedding and reranking models... This may take a minute if downloading weights.")
    state.engine.search("warmup", top_k=1)
    
    logger.info("Application state initialized successfully.")

def shutdown_event():
    """Application shutdown lifecycle event."""
    logger.info("Shutting down application state...")
    state.engine = None
    state.llm = None
    state.rag = None
