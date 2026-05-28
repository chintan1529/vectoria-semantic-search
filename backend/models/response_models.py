from pydantic import BaseModel
from typing import Any, Dict, List, Optional

class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class APISearchResult(BaseModel):
    """Matches the frontend SearchResult structure."""
    rank: int
    score: float
    chunk: Dict[str, Any]

class APIContextStats(BaseModel):
    num_chunks: int
    total_characters: int
    average_score: float
    unique_sources: int

class RAGAPIResponse(BaseModel):
    """Stable response contract enforced by Pydantic."""
    answer: str
    citations: Dict[str, Any]
    retrieved_results: List[APISearchResult]
    context_stats: APIContextStats
    
    # Granular Latency Metrics
    latency_ms: int
    retrieval_latency_ms: int = 0
    rerank_latency_ms: int = 0
    generation_latency_ms: int = 0
    
    model_name: str
    refused: bool
    refusal_reason: Optional[str]
    generation_meta: Dict[str, Any]
    num_retrieved: int
