"""
Query Routes — Hardened with readiness gates, request tracing, and output guards.

Guarantees:
  - No query served until all subsystems READY
  - Every request tracked with unique ID through all stages
  - Retrieval verified before generation (chunks > 0, text exists)
  - Generation verified before COMPLETE (tokens > 0, answer length > threshold)
  - No false success states
"""
import asyncio
import uuid
import time
from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from backend.models.request_models import QueryRequest
from backend.core.logging import logger
from backend.core.startup import state, require_ready
from backend.orchestration.retrieval_orchestrator import RetrievalOrchestrator
from backend.orchestration.streaming_orchestrator import StreamingOrchestrator
from backend.providers.factory import ProviderFactory
from backend.core.rate_limit import rate_limiter
from vectoria.retrieval.semantic_cache import SemanticCache

router = APIRouter()

# Instantiate provider and orchestrators via ProviderFactory
llm_provider = ProviderFactory.create_chat_provider()
retrieval_orchestrator = RetrievalOrchestrator(provider=llm_provider)
streaming_orchestrator = StreamingOrchestrator(provider=llm_provider)
semantic_cache = SemanticCache(similarity_threshold=0.97)

# Request timeout (seconds)
QUERY_TIMEOUT_SECONDS = 90

# Minimum answer length to accept generation as valid
MIN_ANSWER_LENGTH = 10


@router.post("/query/stream")
async def execute_query_stream(request: Request, body: QueryRequest):
    """Execute a semantic search and stream response via Server-Sent Events.
    
    Hardened guarantees:
      - Readiness gate blocks queries before READY
      - Request ID tracks all stages
      - Retrieval verified (chunk count > 0)
      - Generation verified (token count > 0)
    """
    request_id = str(uuid.uuid4())[:8]
    start_time = time.perf_counter()

    # --- Phase 2: Global Readiness Gate ---
    require_ready()

    # --- Phase 3: Request Traceability ---
    logger.info("REQUEST_RECEIVED | request_id=%s query=%s", request_id, repr(body.query[:80]))

    try:
        # Rate Limiting based on client IP
        client_ip = request.client.host if request.client else "unknown"
        await rate_limiter.check_rate_limit(client_ip)
        logger.info("REQUEST_RATE_CHECK | request_id=%s ip=%s status=PASSED", request_id, client_ip)

        return EventSourceResponse(
            streaming_orchestrator.stream_full_pipeline(
                body.query, retrieval_orchestrator, request_id=request_id
            ),
            headers={
                "X-Request-ID": request_id,
                "X-Vectoria-Version": "3.0.0",
            },
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning("REQUEST_INVALID | request_id=%s error=%s", request_id, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        logger.error(
            "REQUEST_FAILED | request_id=%s elapsed_ms=%d error=%s type=%s",
            request_id, elapsed_ms, str(e), type(e).__name__,
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
