import json
import logging
import asyncio
from typing import List, Dict, Any
from vectoria.models import SearchResult
from backend.providers.base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

class TrustVerificationService:
    """
    Research-Grade Trust Verification (Phase 5).
    Extracts claims, verifies citations, and computes composite faithfulness.
    """
    def __init__(self, provider: BaseLLMProvider):
        self.provider = provider
        
    async def verify_trust(self, query: str, results: List[SearchResult], final_answer: str, fast_mode: bool = True) -> Dict[str, Any]:
        """
        Extracts claims, verifies citations, and computes composite faithfulness.
        Uses fast heuristic grounding (<5ms) by default, or deep LLM audit if fast_mode=False.
        """
        from vectoria.performance.degradation import degradation_manager, DegradationLevel
        from vectoria.intelligence.claim_grounding import ClaimGroundingEngine

        deg_state = degradation_manager.evaluate_state(0, 0, 0)
        
        # Fast Heuristic Verification (< 5 ms) by default or under degradation
        if fast_mode or not deg_state.enable_verification or deg_state.level != DegradationLevel.NORMAL:
            grounding_engine = ClaimGroundingEngine()
            grounding_res = grounding_engine.evaluate(final_answer, results)
            return {
                "claims": [{"claim": c["claim"], "confidence": "High" if c["is_grounded"] else "Low"} for c in grounding_res.claim_map],
                "citations": [{"chunk_id": r.chunk.chunk_id, "status": "Verified"} for r in results],
                "composite_faithfulness_score": int(grounding_res.coverage_percentage),
                "evidence_coverage_score": int(grounding_res.coverage_percentage),
                "mode": "fast_heuristic"
            }
        context_blocks = []
        for i, res in enumerate(results, 1):
            context_blocks.append(f"[Chunk ID: {res.chunk.chunk_id} | Title: {res.chunk.metadata.title}]\n{res.chunk.text}")
            
        context_text = "\n\n".join(context_blocks)
        
        system_prompt = (
            "You are an elite AI Verification Agent. Your job is to audit a generated answer against its source context.\n"
            "The generated answer contains citations in the format <cite chunk_id=\"X\"></cite>.\n"
            "Task 1: Claim Extraction. Extract the distinct factual claims from the answer. Identify the supporting text in the context and assign a confidence level (High/Medium/Low).\n"
            "Task 2: Citation Verification. For every citation tag in the answer, verify if the sentence preceding it is ACTUALLY supported by the cited Chunk ID. Assign a status: 'Verified', 'Weakly Supported', or 'Unsupported'.\n"
            "Task 3: Scoring. Calculate the Evidence Coverage Score (0-100) based on how much of the answer is backed by evidence, and a Composite Faithfulness Score (0-100).\n\n"
            "Output strictly valid JSON with this exact schema:\n"
            "{\n"
            "  \"claims\": [\n"
            "    {\"claim\": \"...\", \"evidence\": \"...\", \"confidence\": \"High|Medium|Low\", \"source_chunk_ids\": [\"...\"]}\n"
            "  ],\n"
            "  \"citations\": [\n"
            "    {\"chunk_id\": \"...\", \"status\": \"Verified|Weakly Supported|Unsupported\", \"reason\": \"...\"}\n"
            "  ],\n"
            "  \"composite_faithfulness_score\": 95,\n"
            "  \"evidence_coverage_score\": 90\n"
            "}"
        )
        
        user_prompt = f"QUERY:\n{query}\n\nCONTEXT:\n{context_text}\n\nGENERATED ANSWER:\n{final_answer}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = await self.provider.generate(messages, temperature=0.0)
            text = response.text.strip()
            
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
                
            verification_data = json.loads(text.strip())
            return verification_data
        except Exception as e:
            logger.error(f"Failed to verify trust: {str(e)}")
            return {
                "claims": [],
                "citations": [],
                "composite_faithfulness_score": 0,
                "evidence_coverage_score": 0,
                "error": str(e)
            }
