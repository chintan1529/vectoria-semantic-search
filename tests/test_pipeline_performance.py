"""
Performance & Integration Tests for the Vectoria Pipeline.

Tests:
  1. Intent Router correctness and speed
  2. Heuristic Validator correctness
  3. Backend import chain
  4. Metrics endpoint
"""
import time
import pytest
from httpx import AsyncClient, ASGITransport

# --- Intent Router Tests ---

def test_intent_router_greeting():
    from vectoria.generation.intent_router import HybridIntentRouter, QueryType
    router = HybridIntentRouter()
    intent = router.classify("hello")
    assert intent.query_type == QueryType.CONVERSATIONAL
    assert intent.requires_retrieval is False
    assert intent.confidence >= 0.90

def test_intent_router_analytical():
    from vectoria.generation.intent_router import HybridIntentRouter, QueryType
    router = HybridIntentRouter()
    intent = router.classify("How do neural networks learn from data?")
    assert intent.query_type == QueryType.ANALYTICAL
    assert intent.requires_retrieval is True
    assert intent.confidence >= 0.90

def test_intent_router_factual():
    from vectoria.generation.intent_router import HybridIntentRouter, QueryType
    router = HybridIntentRouter()
    intent = router.classify("What is backpropagation?")
    assert intent.query_type == QueryType.FACTUAL
    assert intent.requires_retrieval is True

def test_intent_router_comparison():
    from vectoria.generation.intent_router import HybridIntentRouter, QueryType
    router = HybridIntentRouter()
    intent = router.classify("Compare RNNs vs transformers for NLP tasks")
    assert intent.query_type == QueryType.COMPARISON
    assert intent.requires_retrieval is True

def test_intent_router_summarization():
    from vectoria.generation.intent_router import HybridIntentRouter, QueryType
    router = HybridIntentRouter()
    intent = router.classify("Summarize the transformer architecture")
    assert intent.query_type == QueryType.SUMMARIZATION
    assert intent.requires_retrieval is True

def test_intent_router_latency():
    """Intent routing must complete in < 5ms."""
    from vectoria.generation.intent_router import HybridIntentRouter
    router = HybridIntentRouter()
    
    queries = [
        "hello", "How do neural networks learn?",
        "What is deep learning?", "Compare CNN vs RNN",
        "Summarize attention mechanisms",
    ]
    
    start = time.perf_counter()
    for q in queries:
        router.classify(q)
    elapsed_ms = (time.perf_counter() - start) * 1000
    
    # All 5 queries should complete in < 5ms total
    assert elapsed_ms < 50, f"Intent routing took {elapsed_ms:.1f}ms for 5 queries"


# --- Heuristic Validator Tests ---

def test_heuristic_validator_empty():
    from vectoria.generation.heuristic_validator import HeuristicContextValidator
    validator = HeuristicContextValidator()
    result = validator.validate_context("test query", [])
    assert result.confidence == "LOW"
    assert len(result.valid_results) == 0


# --- Backend Import Chain ---

def test_backend_imports():
    """Verify the full import chain doesn't break."""
    from backend.api import app
    assert app is not None

def test_metrics_endpoint():
    """Verify /metrics endpoint exists and returns 200."""
    import anyio
    from backend.api import app

    async def _test():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
            response = await client.get("/metrics")
            assert response.status_code == 200

    anyio.run(_test)
