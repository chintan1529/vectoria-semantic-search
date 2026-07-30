import json
import logging
from typing import List, Dict, Any
from vectoria.models import SearchResult
from backend.providers.base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

class EvaluationService:
    """
    Evaluates the quality of generated answers (Phase 2, 4, 7).
    Determines Faithfulness, Relevance, Hallucination Risk.
    """
    def __init__(self, provider: BaseLLMProvider):
        self.provider = provider
        
    async def evaluate_answer(self, query: str, results: List[SearchResult], answer: str) -> Dict[str, Any]:
        """
        Runs an LLM-as-a-judge to evaluate the final answer against the retrieved context.
        """
        context_blocks = []
        for i, res in enumerate(results, 1):
            context_blocks.append(f"[Source {i}: {res.chunk.metadata.title}]\n{res.chunk.text}")
            
        context_text = "\n\n".join(context_blocks)
        
        system_prompt = (
            "You are an impartial, elite AI judge evaluating the quality of an AI-generated answer. "
            "You will be provided with the user's QUERY, the retrieved CONTEXT, and the final ANSWER. "
            "Your task is to score the answer and detect hallucinations.\n\n"
            "Evaluate on the following criteria (1-5 scale):\n"
            "- Faithfulness: Is the answer entirely derived from the context? (1 = totally hallucinated, 5 = perfectly faithful)\n"
            "- Relevance: Does the answer address the query? (1 = irrelevant, 5 = directly answers)\n"
            "- Completeness: Does it use all relevant info from the context? (1 = misses key points, 5 = comprehensive)\n"
            "- Consistency: Are there any contradictions?\n\n"
            "Hallucination Risk:\n"
            "Assign 'Low', 'Medium', or 'High' based on whether the answer invents facts not present in the context.\n\n"
            "Output strictly valid JSON with this exact schema:\n"
            "{\n"
            "  \"faithfulness\": 5,\n"
            "  \"relevance\": 5,\n"
            "  \"completeness\": 5,\n"
            "  \"consistency\": 5,\n"
            "  \"hallucination_risk\": \"Low\",\n"
            "  \"reasoning\": \"Brief explanation of your scores.\"\n"
            "}"
        )
        
        user_prompt = f"QUERY:\n{query}\n\nCONTEXT:\n{context_text}\n\nANSWER:\n{answer}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            # We enforce JSON output if the provider supports it, or parse it out
            response = await self.provider.generate(messages, temperature=0.0)
            text = response.text.strip()
            
            # Clean up markdown JSON block if present
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
                
            metrics = json.loads(text.strip())
            return metrics
        except Exception as e:
            logger.error(f"Failed to evaluate answer: {str(e)}")
            return {
                "faithfulness": 0,
                "relevance": 0,
                "completeness": 0,
                "consistency": 0,
                "hallucination_risk": "Unknown",
                "reasoning": f"Evaluation failed: {str(e)}"
            }
