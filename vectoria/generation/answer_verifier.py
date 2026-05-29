"""
Answer Verification Module.

Handles self-correction and grounding validation using inline thinking tags.
"""
from typing import Dict, List
from vectoria.models import SearchResult
from backend.providers.base_provider import BaseLLMProvider
from backend.core.logging import logger
from backend.orchestration.retrieval_orchestrator import RetrievalDiagnostics

class AnswerVerifier:
    """Modifies the prompt to enforce inline thought-based verification before streaming the final answer."""
    
    @staticmethod
    def inject_verification_prompt(base_prompt: str, diagnostics: RetrievalDiagnostics) -> str:
        """
        Appends verification instructions to the system prompt.
        If confidence is LOW, adds explicit caution.
        """
        verification_instructions = """
Before providing your final answer, you MUST use a <thinking> block to verify your facts.
Inside the <thinking> block:
1. Identify the key claims required to answer the query.
2. Check if EACH claim is explicitly supported by the provided Context.
3. If a claim is unsupported, revise your plan to exclude it.
4. If the context does not contain enough information, state that clearly in your plan.

After the </thinking> block, output your final, revised, and grounded answer.
"""
        
        caution_instructions = ""
        if diagnostics.retrieval_confidence == "LOW":
            caution_instructions = """
WARNING: The retrieval system has flagged the provided context as LOW CONFIDENCE.
You must be extremely cautious. Explicitly inform the user if the evidence is insufficient or tangentially related. Do not fabricate certainty.
"""
            
        return base_prompt + "\n\n" + verification_instructions + caution_instructions
