"""
Citation Utilities — Parse, validate, and normalize LLM-generated citations.

Responsibilities:
    - Extract ``[Doc X]`` citation tags from generated text via regex.
    - Validate each citation against the known citation map, discarding
      hallucinated references that point to non-existent documents.
    - Normalize raw LLM output: trim whitespace, collapse excessive blank
      lines, and ensure clean downstream rendering.

Design decisions:
    - Regex-only parsing — no NLP libraries, no tokenizers.
    - Deterministic ordering: validated citations are returned in the order
      they first appear in the answer text.
    - Malformed citations (e.g., ``[Doc abc]``, ``[Doc]``) are silently
      ignored rather than crashing the pipeline.
    - All functions are pure: no side effects, no shared state.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from vectoria.models import SearchResult


# Matches [Doc 1], [Doc 2], [Doc 10], etc.  Captures the full tag.
_CITATION_PATTERN = re.compile(r"\[Doc\s+\d+\]")


def extract_valid_citations(
    answer: str,
    citation_map: Dict[str, SearchResult],
) -> Tuple[List[str], Dict[str, SearchResult]]:
    """Parse and validate citations from the LLM's generated answer.

    Args:
        answer:       Raw generated text containing ``[Doc X]`` references.
        citation_map: The authoritative map from ``build_citation_map()``,
                      keyed by ``"[Doc 1]"``, ``"[Doc 2]"``, etc.

    Returns:
        A tuple of:
            - ``valid_tags``: Deduplicated list of citation tags that exist
              in ``citation_map``, ordered by first appearance in the answer.
            - ``valid_map``: Filtered citation map containing only the
              validated entries.

    Notes:
        - Citations not present in ``citation_map`` are hallucinated and
          silently discarded.
        - Duplicate citations in the text are collapsed to a single entry.
        - The function never raises; malformed input returns empty results.
    """
    if not answer or not citation_map:
        return [], {}

    # Find all [Doc X] tags in order of appearance
    found_tags = _CITATION_PATTERN.findall(answer)

    # Deduplicate while preserving first-appearance order
    seen = set()
    valid_tags: List[str] = []
    valid_map: Dict[str, SearchResult] = {}

    for tag in found_tags:
        if tag in seen:
            continue
        seen.add(tag)

        if tag in citation_map:
            valid_tags.append(tag)
            valid_map[tag] = citation_map[tag]

    return valid_tags, valid_map


def normalize_answer(text: str) -> str:
    """Clean raw LLM output for consistent downstream rendering.

    Operations:
        1. Strip leading/trailing whitespace.
        2. Collapse runs of 3+ newlines into exactly 2 (one blank line).
        3. Strip trailing whitespace from each line.

    Citation formatting (``[Doc X]``) is preserved intact.

    Args:
        text: Raw generated text from the LLM.

    Returns:
        Normalized text suitable for UI display or API responses.
    """
    if not text:
        return ""

    # Strip outer whitespace
    text = text.strip()

    # Collapse excessive blank lines (3+ newlines → 2)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip trailing whitespace from each line
    lines = [line.rstrip() for line in text.split("\n")]

    return "\n".join(lines)
