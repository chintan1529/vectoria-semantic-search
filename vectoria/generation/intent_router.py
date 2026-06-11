"""
Hybrid Intent Router — Fast local query classification with optional LLM escalation.

Replaces the pure-LLM QueryClassifier with a two-tier system:
  Tier 1: Local keyword/pattern matching (< 1ms, handles 95%+ of queries)
  Tier 2: Lightweight LLM call (only for ambiguous queries with confidence < 90%)

Performance target: < 50ms for 95%+ of requests.
"""
import re
from enum import Enum
from typing import Optional, List, Tuple
from backend.core.logging import logger


class QueryType(str, Enum):
    FACTUAL = "factual"
    ANALYTICAL = "analytical"
    CONVERSATIONAL = "conversational"
    SUMMARIZATION = "summarization"
    COMPARISON = "comparison"
    UNKNOWN = "unknown"


class QueryIntent:
    def __init__(
        self,
        query_type: QueryType,
        requires_retrieval: bool,
        confidence: float,
        explanation: str = "",
        routed_locally: bool = True,
    ):
        self.query_type = query_type
        self.requires_retrieval = requires_retrieval
        self.confidence = confidence
        self.explanation = explanation
        self.routed_locally = routed_locally


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

_GREETING_PATTERNS = re.compile(
    r"^(hi|hello|hey|howdy|good\s*(morning|evening|afternoon)|"
    r"what'?s\s*up|sup|yo|greetings|hola|namaste)\b",
    re.IGNORECASE,
)

_CONVERSATIONAL_PATTERNS = re.compile(
    r"^(who\s+are\s+you|what\s+are\s+you|what\s+can\s+you\s+do|"
    r"how\s+are\s+you|are\s+you\s+an?\s+(ai|bot|assistant)|"
    r"tell\s+me\s+(about\s+yourself|a\s+joke)|thanks|thank\s+you|"
    r"bye|goodbye|see\s+you)\b",
    re.IGNORECASE,
)

_COMPARISON_KEYWORDS = re.compile(
    r"\b(compare|comparison|versus|vs\.?|differ(?:ence|ent|s)?|"
    r"contrast|better|worse|pros?\s+and\s+cons?|advantages?\s+and\s+disadvantages?|"
    r"similarities?\s+and\s+differ)\b",
    re.IGNORECASE,
)

_SUMMARIZATION_KEYWORDS = re.compile(
    r"\b(summarize|summary|overview|brief|outline|recap|"
    r"give\s+me\s+a\s+summary|what\s+is\s+.*\s+about|"
    r"explain\s+in\s+short|tl;?dr|key\s+points?|main\s+ideas?)\b",
    re.IGNORECASE,
)

_ANALYTICAL_KEYWORDS = re.compile(
    r"\b(how\s+does|how\s+do|why\s+does|why\s+do|why\s+is|why\s+are|"
    r"explain|describe|analyze|analyse|elaborate|mechanism|"
    r"how\s+is\s+.+\s+(used|applied|implemented)|"
    r"what\s+causes?|what\s+happens?\s+when|"
    r"what\s+is\s+the\s+(role|purpose|function|impact|effect)|"
    r"in\s+what\s+way|to\s+what\s+extent)\b",
    re.IGNORECASE,
)

_FACTUAL_KEYWORDS = re.compile(
    r"\b(what\s+is|what\s+are|who\s+is|who\s+are|when\s+was|when\s+did|"
    r"where\s+is|where\s+are|define|definition|"
    r"how\s+many|how\s+much|how\s+long|how\s+old|"
    r"name\s+the|list\s+the|which\s+.+\s+is|"
    r"is\s+it\s+true|true\s+or\s+false)\b",
    re.IGNORECASE,
)


class HybridIntentRouter:
    """Fast local intent router with optional LLM escalation.
    
    The router scores queries against pattern categories and returns
    a classification with confidence. If confidence is below the
    escalation threshold, the caller can optionally invoke an LLM.
    """

    def __init__(self, escalation_threshold: float = 0.90):
        self.escalation_threshold = escalation_threshold

    def classify(self, query: str) -> QueryIntent:
        """Classify a query using local heuristics.
        
        Returns a QueryIntent. If confidence < escalation_threshold,
        the caller should consider LLM escalation.
        
        Target: < 1ms execution time.
        """
        query_stripped = query.strip()
        query_lower = query_stripped.lower()
        word_count = len(query_stripped.split())

        # --- Tier 1a: Greeting detection (highest priority) ---
        if word_count <= 5 and _GREETING_PATTERNS.search(query_stripped):
            return QueryIntent(
                query_type=QueryType.CONVERSATIONAL,
                requires_retrieval=False,
                confidence=0.98,
                explanation="Detected greeting pattern",
            )

        # --- Tier 1b: Conversational meta-queries ---
        if _CONVERSATIONAL_PATTERNS.search(query_stripped):
            return QueryIntent(
                query_type=QueryType.CONVERSATIONAL,
                requires_retrieval=False,
                confidence=0.95,
                explanation="Detected conversational/meta pattern",
            )

        # --- Tier 1c: Score each content category ---
        scores: List[Tuple[QueryType, float, str]] = []

        if _COMPARISON_KEYWORDS.search(query_stripped):
            # Boost if query has "vs" or "and" connecting two concepts
            boost = 0.1 if re.search(r"\bvs\.?\b|\band\b", query_lower) else 0.0
            scores.append((QueryType.COMPARISON, 0.90 + boost, "Comparison keywords detected"))

        if _SUMMARIZATION_KEYWORDS.search(query_stripped):
            scores.append((QueryType.SUMMARIZATION, 0.92, "Summarization keywords detected"))

        if _ANALYTICAL_KEYWORDS.search(query_stripped):
            # Analytical queries tend to be longer
            length_boost = min(0.05, (word_count - 5) * 0.01) if word_count > 5 else 0.0
            scores.append((QueryType.ANALYTICAL, 0.92 + length_boost, "Analytical pattern detected"))

        if _FACTUAL_KEYWORDS.search(query_stripped):
            scores.append((QueryType.FACTUAL, 0.90, "Factual pattern detected"))

        # Pick highest confidence match
        if scores:
            scores.sort(key=lambda x: x[1], reverse=True)
            best_type, best_conf, best_reason = scores[0]
            return QueryIntent(
                query_type=best_type,
                requires_retrieval=True,
                confidence=best_conf,
                explanation=best_reason,
            )

        # --- Tier 1d: Default — assume analytical if long, factual if short ---
        if word_count >= 6:
            return QueryIntent(
                query_type=QueryType.ANALYTICAL,
                requires_retrieval=True,
                confidence=0.75,
                explanation="Default: longer query assumed analytical",
            )
        else:
            return QueryIntent(
                query_type=QueryType.FACTUAL,
                requires_retrieval=True,
                confidence=0.70,
                explanation="Default: short query assumed factual",
            )

    @property
    def needs_escalation(self) -> bool:
        """Check if the last classification needs LLM escalation.
        
        This is a convenience — the caller can also just check
        intent.confidence < self.escalation_threshold.
        """
        return False  # placeholder for stateful tracking if needed
