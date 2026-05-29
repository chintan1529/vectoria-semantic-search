"""
Query Classification Module.

Determines the intent and type of a user query to route it optimally.
"""
from enum import Enum
from typing import Dict, List, Optional
import json

from backend.providers.base_provider import BaseLLMProvider
from backend.core.logging import logger

class QueryType(str, Enum):
    FACTUAL = "factual"
    ANALYTICAL = "analytical"
    CONVERSATIONAL = "conversational"
    SUMMARIZATION = "summarization"
    COMPARISON = "comparison"
    UNKNOWN = "unknown"

class QueryIntent:
    def __init__(self, query_type: QueryType, requires_retrieval: bool, confidence: float, explanation: str = ""):
        self.query_type = query_type
        self.requires_retrieval = requires_retrieval
        self.confidence = confidence
        self.explanation = explanation

class QueryClassifier:
    """Classifies user queries using a lightweight LLM call to guide retrieval strategy."""
    
    def __init__(self, llm_provider: BaseLLMProvider):
        self._llm = llm_provider
        
    async def classify(self, query: str) -> QueryIntent:
        """Classify the query into a predefined type."""
        prompt = f"""You are an intelligent query routing system. Analyze the user's query and classify it.
        
Categories:
- factual: Requires specific facts or data points.
- analytical: Requires deep reasoning, explanations, or how/why questions.
- conversational: Greetings, small talk, or meta-questions about the AI itself.
- summarization: Asking to summarize a broad topic or document.
- comparison: Comparing two or more entities or concepts.

Output JSON only, in this exact format:
{{
    "query_type": "<one of the categories>",
    "requires_retrieval": <boolean, false only for pure conversational greetings>,
    "confidence": <float between 0.0 and 1.0>,
    "explanation": "<brief reason>"
}}

User Query: {query}
"""
        try:
            # We want a fast, deterministic response
            messages = [{"role": "user", "content": prompt}]
            result = await self._llm.generate(messages, temperature=0.0)
            
            text = result.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
                
            data = json.loads(text.strip())
            
            q_type = QueryType(data.get("query_type", "unknown").lower())
            
            # Additional heuristic check: if query is extremely short and just a greeting
            if q_type == QueryType.UNKNOWN and len(query.split()) < 3 and "hi" in query.lower() or "hello" in query.lower():
                q_type = QueryType.CONVERSATIONAL
                data["requires_retrieval"] = False
            
            return QueryIntent(
                query_type=q_type,
                requires_retrieval=bool(data.get("requires_retrieval", True)),
                confidence=float(data.get("confidence", 1.0)),
                explanation=data.get("explanation", "")
            )
            
        except Exception as e:
            logger.warning(f"Query classification failed, falling back to default | error={e}")
            return QueryIntent(QueryType.UNKNOWN, requires_retrieval=True, confidence=0.0)
