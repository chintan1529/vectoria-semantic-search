from fastapi import APIRouter, Request, BackgroundTasks
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from backend.core.startup import state
from backend.core.config import settings
from backend.providers.openai_provider import OpenAIProvider
from backend.providers.factory import ProviderFactory
from backend.orchestration.retrieval_orchestrator import RetrievalOrchestrator
from backend.orchestration.research_orchestrator import ResearchOrchestrator
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class QueryRequest(BaseModel):
    query: str

@router.post("/stream")
async def stream_research(request: QueryRequest, req: Request):
    """SSE endpoint for Agentic Research Mode."""
    research_provider = ProviderFactory.create_research_provider()
    # The retriever can still use the chat provider or the research provider
    retriever = RetrievalOrchestrator(state.llm)
    orchestrator = ResearchOrchestrator(research_provider, retriever)
    
    return EventSourceResponse(
        orchestrator.stream_research(request.query),
        media_type="text/event-stream"
    )
