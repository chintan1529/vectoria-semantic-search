"""
Reranker Audit — Evaluates BAAI Reranker Latency vs Quality over varying candidate sizes.
"""
import asyncio
import time
import json
import logging
from typing import List

from backend.core.startup import state, startup_event
from backend.orchestration.retrieval_orchestrator import RetrievalOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QUERIES = [
    "What is stochastic gradient descent?",
    "Explain the role of attention mechanisms in transformers.",
    "How does FAISS accelerate vector search?",
    "Compare hybrid search with standard dense retrieval.",
    "What are the best practices for chunking text for LLMs?",
]

TOP_K_VALUES = [5, 10, 15, 20, 50]


async def audit_reranker():
    logger.info("Initializing system...")
    startup_event()
    
    # Pre-warm
    logger.info("Pre-warming reranker...")
    orchestrator = RetrievalOrchestrator()
    await orchestrator.execute_retrieval("warmup", top_k=5)

    results_data = []

    for top_k in TOP_K_VALUES:
        logger.info(f"\n--- Testing Candidate Pool Size: {top_k} ---")
        latencies = []
        
        for q in QUERIES:
            # Clear cache for accurate timing
            if hasattr(state.engine, "clear_cache"):
                state.engine.clear_cache()
            if hasattr(orchestrator, "_cache"):
                orchestrator._cache.clear()

            start_time = time.perf_counter()
            # In execute_retrieval, it passes top_k*2 to engine.search if analytical, but let's just force top_k
            res, diag = await orchestrator.execute_retrieval(q, top_k=top_k)
            end_time = time.perf_counter()

            # Time includes retrieval + reranking. We can extract reranking from diagnostics if needed, 
            # or just take total retrieval time.
            latencies.append((end_time - start_time) * 1000)

        avg_latency = sum(latencies) / len(latencies)
        logger.info(f"Average Latency for top_k={top_k}: {avg_latency:.2f} ms")
        
        results_data.append({
            "top_k": top_k,
            "avg_latency_ms": round(avg_latency, 2),
            "samples": len(latencies)
        })

    logger.info("\n=== Reranker Audit Results ===")
    print(json.dumps(results_data, indent=2))
    
    # Recommendation
    for r in results_data:
        if r["avg_latency_ms"] > 1000:
            logger.warning(f"Latency exceeds 1000ms at top_k={r['top_k']}. Unacceptable for real-time UX.")
            break

if __name__ == "__main__":
    asyncio.run(audit_reranker())
