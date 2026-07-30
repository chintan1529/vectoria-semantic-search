from fastapi import APIRouter
from pydantic import BaseModel
from backend.core.startup import state
from backend.orchestration.retrieval_orchestrator import RetrievalOrchestrator

router = APIRouter()

class InspectRequest(BaseModel):
    query: str
    top_k: int = 5

@router.post("/inspect")
async def inspect_retrieval(request: InspectRequest):
    """
    Executes retrieval only, returning the valid results and the full diagnostics (including rejected candidates).
    """
    retriever = RetrievalOrchestrator()
    results, diagnostics = await retriever.execute_retrieval(request.query, top_k=request.top_k)
    
    return {
        "results": [{"id": r.chunk.chunk_id, "title": r.chunk.metadata.title, "text": r.chunk.text, "score": r.score} for r in results],
        "diagnostics": diagnostics.model_dump()
    }
