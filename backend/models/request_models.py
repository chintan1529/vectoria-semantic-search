from pydantic import BaseModel, Field
from typing import Optional

class QueryRequest(BaseModel):
    """Incoming search/RAG query."""
    query: str = Field(..., min_length=1, max_length=1000, description="The user query text.")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Optional override for top_k results.")
    stream: bool = Field(False, description="Whether to stream the response (SSE).")
