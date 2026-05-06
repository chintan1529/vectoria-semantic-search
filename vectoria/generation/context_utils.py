"""
Context Utilities for RAG Pre-processing.

These utilities format, filter, and prepare retrieved chunks for downstream 
LLM generation while maintaining determinism, security, and traceability.

SECURITY NOTE: 
The text retrieved from documents is UNTRUSTED user/external data.
Future LLM prompts must explicitly instruct the model to ignore malicious 
instructions or prompt injections that might be present inside the retrieved text.
"""

from typing import List, Dict, Any
from vectoria.models import SearchResult


def deduplicate_chunks(results: List[SearchResult]) -> List[SearchResult]:
    """Remove near-identical or identical chunk texts to avoid context redundancy.
    
    Strategy: 
    Iterates through results (already sorted by rank). If a chunk's text has 
    already been seen (exact string match), it is skipped. This is a lightweight, 
    deterministic approach.
    """
    seen_texts = set()
    deduped = []
    for r in results:
        if r.chunk.text not in seen_texts:
            seen_texts.add(r.chunk.text)
            deduped.append(r)
    return deduped


def build_context(
    results: List[SearchResult], 
    max_context_chars: int = 4000
) -> str:
    """Format and truncate retrieved results into a clean context string.
    
    Format:
    [Doc 1] <chunk text>
    [Doc 2] <chunk text>
    ...
    
    Truncation Strategy:
    Adds chunks sequentially. If adding a chunk exceeds `max_context_chars`, 
    it stops adding more chunks to prevent LLM context overflow.
    """
    clean_results = deduplicate_chunks(results)
    
    context_parts = []
    current_length = 0
    
    for i, r in enumerate(clean_results, 1):
        chunk_str = f"[Doc {i}] {r.chunk.text.strip()}"
        
        # Calculate length including potential newline separators
        added_length = len(chunk_str) + (2 if current_length > 0 else 0)
        
        if current_length + added_length > max_context_chars:
            break
            
        context_parts.append(chunk_str)
        current_length += added_length
        
    return "\n\n".join(context_parts)


def build_citation_map(results: List[SearchResult]) -> Dict[str, SearchResult]:
    """Map deterministic document tags back to their SearchResult objects.
    
    Returns a dictionary mapping "[Doc X]" to the original SearchResult.
    This guarantees that future LLM citations can be resolved safely and accurately.
    """
    clean_results = deduplicate_chunks(results)
    citation_map = {}
    
    for i, r in enumerate(clean_results, 1):
        citation_map[f"[Doc {i}]"] = r
        
    return citation_map


def has_sufficient_context(
    results: List[SearchResult], 
    min_score_threshold: float = 0.3
) -> bool:
    """Determine if the retrieval context is sufficient for an LLM to answer.
    
    Returns False if:
    - No results are returned.
    - The top result's score is below the strict confidence threshold.
    """
    if not results:
        return False
        
    if results[0].score < min_score_threshold:
        return False
        
    return True


def compute_context_stats(results: List[SearchResult]) -> Dict[str, Any]:
    """Compute observability statistics for the retrieved context."""
    if not results:
        return {
            "num_chunks": 0,
            "total_characters": 0,
            "average_score": 0.0,
            "unique_sources": 0
        }
        
    clean_results = deduplicate_chunks(results)
    
    total_chars = sum(len(r.chunk.text) for r in clean_results)
    avg_score = sum(r.score for r in clean_results) / len(clean_results) if clean_results else 0.0
    unique_sources = len(set(r.chunk.metadata.source for r in clean_results))
    
    return {
        "num_chunks": len(clean_results),
        "total_characters": total_chars,
        "average_score": round(avg_score, 4),
        "unique_sources": unique_sources
    }
