"""
Context Quality Validation Module.

Validates retrieved chunks against the query to filter out noise,
duplicates, and irrelevant information.
"""
from typing import List, Dict, Tuple
from vectoria.models import SearchResult
from backend.providers.base_provider import BaseLLMProvider
from backend.core.logging import logger
import json

class ContextValidationResult:
    def __init__(self, valid_results: List[SearchResult], rejected_count: int, confidence: str):
        self.valid_results = valid_results
        self.rejected_count = rejected_count
        self.confidence = confidence  # HIGH, MEDIUM, LOW

class ContextValidator:
    """Filters and scores retrieved context for relevance and redundancy."""
    
    def __init__(self, llm_provider: BaseLLMProvider):
        self._llm = llm_provider
        
    async def validate_context(self, query: str, results: List[SearchResult]) -> ContextValidationResult:
        """
        Validates context quality. 
        Note: To save latency, we use a heuristic + lightweight LLM pass.
        If results are empty, return LOW confidence.
        """
        if not results:
            return ContextValidationResult([], 0, "LOW")
            
        # 1. Deduplication (Exact Match or highly similar text)
        unique_results = []
        seen_texts = set()
        
        for res in results:
            # Simple deduplication by exact text or chunk_id
            text_hash = hash(res.chunk.text[:200])  # Hash first 200 chars
            if text_hash not in seen_texts:
                seen_texts.add(text_hash)
                unique_results.append(res)
                
        rejected_dups = len(results) - len(unique_results)
        
        # 2. LLM Relevance Check (Batch evaluate chunks)
        # To avoid massive latency, we evaluate the combined context's overall quality rather than per-chunk loop
        context_blocks = []
        for i, res in enumerate(unique_results, 1):
            context_blocks.append(f"[Chunk {i}]\n{res.chunk.text}")
            
        context_str = "\n\n".join(context_blocks)
        
        prompt = f"""Evaluate if the following retrieved context provides enough information to answer the user's query.

User Query: {query}

Retrieved Context:
{context_str}

Output JSON only, in this exact format:
{{
    "answers_query": <boolean>,
    "confidence_level": "<HIGH|MEDIUM|LOW>",
    "irrelevant_chunks": [<list of chunk numbers that are completely useless, e.g., [2, 4] or [] if all useful>]
}}
"""
        try:
            result = await self._llm.generate([{"role": "user", "content": prompt}], temperature=0.0)
            
            text = result.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
                
            data = json.loads(text.strip())
            
            confidence = data.get("confidence_level", "MEDIUM").upper()
            if confidence not in ["HIGH", "MEDIUM", "LOW"]:
                confidence = "MEDIUM"
                
            irrelevant_indices = data.get("irrelevant_chunks", [])
            
            # Filter out chunks marked as irrelevant
            final_results = []
            for i, res in enumerate(unique_results, 1):
                if i not in irrelevant_indices:
                    final_results.append(res)
                    
            rejected_total = rejected_dups + (len(unique_results) - len(final_results))
            
            # If all chunks were rejected, confidence is LOW
            if not final_results:
                confidence = "LOW"
                
            return ContextValidationResult(final_results, rejected_total, confidence)
            
        except Exception as e:
            logger.warning(f"Context validation LLM call failed, falling back | error={e}")
            # Fallback: assume all deduplicated chunks are valid, base confidence on top score
            top_score = unique_results[0].score if unique_results else 0
            if top_score > 0.8:
                conf = "HIGH"
            elif top_score > 0.4:
                conf = "MEDIUM"
            else:
                conf = "LOW"
            return ContextValidationResult(unique_results, rejected_dups, conf)
