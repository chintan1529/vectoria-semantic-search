from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from backend.services.knowledge_graph_service import KnowledgeGraphService
from backend.providers.openai_provider import OpenAIProvider
from backend.core.config import settings

router = APIRouter()

class GraphRequest(BaseModel):
    texts: List[str]

@router.post("/extract")
async def extract_graph(request: GraphRequest):
    if not request.texts:
        raise HTTPException(status_code=400, detail="No texts provided")
        
    from backend.core.startup import state
    if not state.llm:
        raise HTTPException(status_code=503, detail="Provider not ready")
        
    service = KnowledgeGraphService(state.llm)
    
    graph_data = await service.extract_graph(request.texts)
    return graph_data
