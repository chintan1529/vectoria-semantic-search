"""
Evaluation and Benchmarking Module for Vectoria.

This module provides tools to measure the retrieval quality of the SearchEngine.

Dataset Format:
    List of dictionaries, where each dict has:
    {
        "query": "The search string",
        "relevant_chunk_ids": ["id1", "id2"]
    }
    This is used as the ground truth to see if the engine returns the expected chunks.

Evaluation Assumptions (Data Leakage & Fairness):
    - The evaluation dataset MUST be completely disjoint from the training data used 
      to fine-tune the cross-encoder or embeddings.
    - If queries from the evaluation set were seen during training, metrics will be 
      artificially inflated, defeating the purpose of benchmarking.

Retrieval Differences:
    - FAISS-Only Pipeline: Retrieves exactly `top_k` results based on cosine similarity (high recall focus).
    - Reranked Pipeline: Retrieves `fetch_k` (usually 10x top_k) from FAISS, computes
      deep cross-attention scores for all candidates, and returns the highest `top_k` (high precision focus).

Latency Semantics:
    - `avg_latency_ms` measures the full end-to-end pipeline execution time.
    - This includes: query embedding, FAISS retrieval, candidate mapping, 
      cross-encoder reranking (if enabled), and deterministic sorting.
"""

import time

import math
from typing import List, Dict, Any

def recall_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """Fraction of relevant docs retrieved in the top K."""
    if not relevant_ids:
        return 0.0
    retrieved_k = retrieved_ids[:k]
    hits = sum(1 for doc_id in relevant_ids if doc_id in retrieved_k)
    return hits / len(relevant_ids)

def reciprocal_rank(retrieved_ids: List[str], relevant_ids: List[str]) -> float:
    """1 / rank of the first relevant result (0 if none found)."""
    for rank, doc_id in enumerate(retrieved_ids, 1):
        if doc_id in relevant_ids:
            return 1.0 / rank
    return 0.0

def precision_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """Fraction of retrieved results that are relevant."""
    retrieved_k = retrieved_ids[:k]
    if not retrieved_k:
        return 0.0
    hits = sum(1 for doc_id in retrieved_k if doc_id in relevant_ids)
    return hits / len(retrieved_k)

def hit_rate_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """1.0 if any relevant doc appears in top K, else 0.0."""
    retrieved_k = retrieved_ids[:k]
    for doc_id in retrieved_k:
        if doc_id in relevant_ids:
            return 1.0
    return 0.0

def ndcg_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """Normalized Discounted Cumulative Gain at K (Binary Relevance).
    
    Note: This assumes binary relevance (a document is either relevant or not).
    If graded relevance labels (e.g., 0 to 3) are available in the future, 
    this formula can be updated to utilize them for more nuanced ranking evaluation.
    """
    if not relevant_ids:
        return 0.0
        
    retrieved_k = retrieved_ids[:k]
    dcg = 0.0
    for i, doc_id in enumerate(retrieved_k):
        if doc_id in relevant_ids:
            dcg += 1.0 / math.log2(i + 2)  # +2 because i is 0-indexed and formula is log2(rank + 1) where rank is 1-indexed

    # Ideal DCG: perfect ranking where all relevant docs appear first
    idcg = 0.0
    ideal_k = min(len(relevant_ids), k)
    for i in range(ideal_k):
        idcg += 1.0 / math.log2(i + 2)

    return dcg / idcg if idcg > 0 else 0.0

def _evaluate_system(engine, dataset: List[Dict[str, Any]], top_k: int) -> Dict[str, float]:
    """Evaluate a configured engine against a dataset."""
    total_recall = 0.0
    total_mrr = 0.0
    total_precision = 0.0
    total_hit_rate = 0.0
    total_ndcg = 0.0
    total_latency_ms = 0
    num_queries = len(dataset)
    
    if num_queries == 0:
        return {
            "recall@k": 0.0, "mrr": 0.0, "precision@k": 0.0,
            "hit_rate@k": 0.0, "ndcg@k": 0.0, "avg_latency_ms": 0.0
        }
        
    for item in dataset:
        query = item["query"]
        relevant_ids = item["relevant_chunk_ids"]
        
        start_time = time.perf_counter()
        results = engine.search(query, top_k=top_k)
        total_latency_ms += int((time.perf_counter() - start_time) * 1000)
        
        retrieved_ids = [r.chunk.chunk_id for r in results]
        
        total_recall += recall_at_k(retrieved_ids, relevant_ids, top_k)
        total_mrr += reciprocal_rank(retrieved_ids, relevant_ids)
        total_precision += precision_at_k(retrieved_ids, relevant_ids, top_k)
        total_hit_rate += hit_rate_at_k(retrieved_ids, relevant_ids, top_k)
        total_ndcg += ndcg_at_k(retrieved_ids, relevant_ids, top_k)
        
    return {
        "recall@k": round(total_recall / num_queries, 4),
        "mrr": round(total_mrr / num_queries, 4),
        "precision@k": round(total_precision / num_queries, 4),
        "hit_rate@k": round(total_hit_rate / num_queries, 4),
        "ndcg@k": round(total_ndcg / num_queries, 4),
        "avg_latency_ms": round(total_latency_ms / num_queries, 2)
    }

def evaluate_search(
    engine_faiss, 
    engine_rerank, 
    dataset: List[Dict[str, Any]], 
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Run benchmark comparing FAISS-only vs Reranked performance.
    
    Args:
        engine_faiss: Initialized SearchEngine with use_reranker=False
        engine_rerank: Initialized SearchEngine with use_reranker=True
        dataset: List of queries and relevant chunk IDs
        top_k: Number of results to retrieve
    """
    # 0. Ensure Shared Data Context
    # Guarantee fair comparison by forcing both engines to point to the exact same underlying in-memory structures
    engine_rerank._index = engine_faiss._index
    engine_rerank._chunk_map = engine_faiss._chunk_map
    engine_rerank._mapping = engine_faiss._mapping
    # Share encoder to ensure embedding consistency and eliminate evaluation drift
    engine_rerank._encoder = engine_faiss._encoder

    # 1. Evaluate FAISS-only
    engine_faiss.clear_cache()
    faiss_metrics = _evaluate_system(engine_faiss, dataset, top_k)
    
    # 2. Evaluate Reranked
    engine_rerank.clear_cache()
    reranked_metrics = _evaluate_system(engine_rerank, dataset, top_k)
        
    # 3. Compute Improvement
    improvement = {}
    for metric in faiss_metrics:
        if metric == "avg_latency_ms":
            # Latency increases are expected, we still compute the % difference
            base = faiss_metrics[metric]
            new = reranked_metrics[metric]
            if base == 0 and new > 0:
                improvement[metric] = "+inf%"
            else:
                imp = ((new - base) / base) * 100 if base > 0 else 0.0
                improvement[metric] = f"{imp:+.2f}%"
            continue
            
        base = faiss_metrics[metric]
        new = reranked_metrics[metric]
        if base > 0:
            imp = ((new - base) / base) * 100
        else:
            imp = 100.0 if new > 0 else 0.0
        improvement[metric] = f"{imp:+.2f}%"
        
    return {
        "faiss": faiss_metrics,
        "reranked": reranked_metrics,
        "improvement": improvement
    }
