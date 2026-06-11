"""
Query Routes — Production-grade with timeout, deduplication, and readiness guards.
"""
import asyncio
import uuid
import time
from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from backend.models.request_models import QueryRequest
from backend.core.logging import logger
from backend.core.startup import state
from backend.orchestration.retrieval_orchestrator import RetrievalOrchestrator
from backend.orchestration.streaming_orchestrator import StreamingOrchestrator
from backend.providers.openai_provider import OpenAIProvider
from backend.core.config import settings
from backend.core.rate_limit import rate_limiter

router = APIRouter()

# Instantiate provider and orchestrators
llm_provider = OpenAIProvider(
    api_key=settings.vectoria_llm_api_key,
    model=settings.vectoria_model_name,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)
retrieval_orchestrator = RetrievalOrchestrator(provider=llm_provider)
streaming_orchestrator = StreamingOrchestrator(provider=llm_provider)

# Request timeout (seconds)
QUERY_TIMEOUT_SECONDS = 90


@router.post("/query/stream")
async def execute_query_stream(request: Request, body: QueryRequest):
    """Execute a semantic search and stream response via Server-Sent Events.
    
    Features:
      - Request ID tracking
      - 90s timeout
      - Rate limiting
      - Readiness guard
    """
    request_id = str(uuid.uuid4())[:8]
    start_time = time.perf_counter()

    # --- Readiness guard ---
    if not state.engine or not state.rag:
        raise HTTPException(
            status_code=503,
            detail="System is still warming up. Models are loading. Please retry in a few seconds.",
        )

    try:
        # Rate Limiting based on client IP
        client_ip = request.client.host if request.client else "unknown"
        await rate_limiter.check_rate_limit(client_ip)

        # 1. Retrieval Phase (with timeout)
        try:
            results, diagnostics = await asyncio.wait_for(
                retrieval_orchestrator.execute_retrieval(body.query, top_k=5),
                timeout=QUERY_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.error(
                "Retrieval timeout | request_id=%s query=%s timeout=%ds",
                request_id, repr(body.query[:50]), QUERY_TIMEOUT_SECONDS,
            )
            raise HTTPException(
                status_code=504,
                detail=f"Retrieval timed out after {QUERY_TIMEOUT_SECONDS}s. Please try a simpler query.",
            )

        # 2. Generation Phase (Streaming)
        return EventSourceResponse(
            streaming_orchestrator.stream_response(
                body.query, results, diagnostics, request_id=request_id
            ),
            headers={
                "X-Request-ID": request_id,
                "X-Vectoria-Version": "3.0.0",
            },
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.error(
            f"Internal RAG pipeline error | request_id={request_id} "
            f"elapsed_ms={elapsed_ms} error={str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred during generation.",
        )


@router.post("/query")
async def execute_query_sync(request: Request, body: QueryRequest):
    """Legacy synchronous endpoint."""
    raise HTTPException(status_code=501, detail="Use /query/stream for production.")
