from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from backend.models.request_models import QueryRequest
from backend.models.response_models import RAGAPIResponse
from backend.core.logging import logger
from backend.orchestration.retrieval_orchestrator import RetrievalOrchestrator
from backend.orchestration.streaming_orchestrator import StreamingOrchestrator
from backend.providers.openai_provider import OpenAIProvider
from backend.core.config import settings
from backend.core.rate_limit import rate_limiter

router = APIRouter()

# Instantiate provider and orchestrators
# In a real enterprise system, these would be injected or managed via a factory.
llm_provider = OpenAIProvider(api_key=settings.vectoria_llm_api_key, model=settings.vectoria_model_name)
retrieval_orchestrator = RetrievalOrchestrator(provider=llm_provider)
streaming_orchestrator = StreamingOrchestrator(provider=llm_provider)

@router.post("/query/stream")
async def execute_query_stream(request: Request, body: QueryRequest):
    """
    Execute a semantic search and return a streaming response via Server-Sent Events.
    Yields context, diagnostics, tokens, and done events.
    """
    try:
        # Rate Limiting based on client IP
        client_ip = request.client.host if request.client else "unknown"
        await rate_limiter.check_rate_limit(client_ip)
        
        # 1. Retrieval Phase
        results, diagnostics = await retrieval_orchestrator.execute_retrieval(body.query, top_k=5)
        
        # 2. Generation Phase (Streaming)
        return EventSourceResponse(
            streaming_orchestrator.stream_response(body.query, results, diagnostics)
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Invalid query: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal RAG pipeline error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred during generation.")

@router.post("/query", response_model=RAGAPIResponse)
async def execute_query_sync(request: Request, body: QueryRequest):
    """
    Legacy synchronous endpoint.
    """
    raise HTTPException(status_code=501, detail="Use /query/stream for production.")
