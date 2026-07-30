"""
Dynamic Prompt Builder (Refinement 5).

Constructs LLM system and user prompts dynamically conditioned on query intent,
evidence quality, answerability category, and detected contradictions.
"""

from typing import List
from vectoria.models import SearchResult
from vectoria.intelligence.decision_engine import DecisionOutcome, DecisionAction


class DynamicPromptBuilder:
    """Modular prompt builder for grounded LLM answer generation."""

    BASE_SYSTEM = (
        "You are Vectoria, an evidence-grounded AI intelligence assistant. "
        "Strictly answer using ONLY the provided context chunks. "
        "Every claim must be backed by citations [Chunk N]."
    )

    def build_prompts(self, query: str, results: List[SearchResult], decision: DecisionOutcome) -> tuple[str, str]:
        system_parts = [self.BASE_SYSTEM]

        # 1. Condition on Warning / Contradictions
        if decision.action == DecisionAction.GENERATE_WITH_WARNING:
            system_parts.append(
                "NOTICE: The evidence coverage is partial or contains conflicting information. "
                "Explicitly state any assumptions and present conflicting facts clearly."
            )

        if decision.contradictions.has_contradictions:
            system_parts.append(
                "WARNING: Detected date or factual discrepancies in context sources. "
                "Explicitly highlight both viewpoints in your response."
            )

        # 2. Condition on Requested Format
        if decision.query_meta.requested_format == "list":
            system_parts.append("Format your answer as a structured bulleted list.")
        elif decision.query_meta.requested_format == "table":
            system_parts.append("Format your answer as a Markdown table.")
        elif decision.query_meta.requested_format == "code":
            system_parts.append("Include clean, executable code blocks in your answer.")

        system_prompt = "\n".join(system_parts)

        # 3. Format Context Chunks
        context_blocks = []
        for i, r in enumerate(results, 1):
            context_blocks.append(f"[Chunk {i}] (ID: {r.chunk.chunk_id}, Title: {r.chunk.metadata.title})\n{r.chunk.text}")

        context_str = "\n\n".join(context_blocks)
        user_prompt = f"Context Evidence:\n{context_str}\n\nUser Question: {query}\n\nProvide an evidence-grounded answer:"

        return system_prompt, user_prompt
