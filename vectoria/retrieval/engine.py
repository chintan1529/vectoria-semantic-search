"""
Search Engine -- Orchestrate query-to-results retrieval pipeline.

This is the top-level retrieval module that wires together the embedding
encoder, FAISS index, chunk storage, and mapping into a clean
``query -> List[SearchResult]`` pipeline.

Query Pipeline
--------------
1. **Validate** -- strip whitespace, reject empty queries.
2. **Encode** -- convert query text to a 384-d L2-normalised vector.
3. **Search** -- find top-K nearest neighbours in the FAISS index.
4. **Map** -- resolve FAISS indices to chunk_ids via the mapping.
5. **Retrieve** -- look up full Chunk objects from the chunk store.
6. **Rank** -- build SearchResult objects sorted by score (desc),
   with chunk_id as a deterministic tie-breaker.
7. **Filter** -- optionally drop results below ``min_score``.

Determinism
-----------
Given the same query, model weights, and persisted data, this engine
returns bitwise-identical results.  Tie-breaking on chunk_id ensures
a stable sort even when scores are equal.

Caching
-------
An optional lightweight in-memory cache (``dict``) avoids recomputing
embeddings and re-searching FAISS for repeated identical queries.
The cache key is ``(query_text, top_k, min_score)`` and is bounded
by ``max_cache_size`` (default 128).

Usage
-----
::

    from vectoria.retrieval.engine import SearchEngine

    engine = SearchEngine()
    engine.load()
    results = engine.search("How do neural networks learn?", top_k=5)
    for r in results:
        print(f"#{r.rank} [{r.score:.4f}] {r.chunk.metadata.title}")
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

import numpy as np

from vectoria.config import (
    CHUNKS_PATH,
    EMBEDDINGS_PATH,
    FAISS_INDEX_PATH,
    MAPPING_PATH,
    TOP_K_DEFAULT,
)
from vectoria.embedding.encoder import EmbeddingEncoder, EmbeddingMapping
from vectoria.indexing.faiss_index import VectorIndex
from vectoria.logger import get_logger
from vectoria.models import Chunk, SearchResult
from vectoria.reranking.reranker import CrossEncoderReranker
from vectoria.storage import analyze_score_distribution, load_chunks
from vectoria.retrieval.bm25 import BM25Retriever

logger = get_logger(__name__)


class SearchEngine:
    """Production retrieval engine orchestrating the full search pipeline.

    Attributes:
        encoder:    Embedding encoder (lazy-loaded model).
        index:      FAISS vector index.
        chunks:     Chunk store (list, indexed by position).
        chunk_map:  Fast lookup from chunk_id to Chunk object.
    """

    def __init__(
        self,
        max_cache_size: int = 128,
        use_reranker: bool = True,
        batch_size: int = 32,
        fetch_k_multiplier: int = 10,
    ) -> None:
        self._encoder: Optional[EmbeddingEncoder] = None
        self._index: Optional[VectorIndex] = None
        self._chunks: Optional[List[Chunk]] = None
        self._chunk_map: Optional[Dict[str, Chunk]] = None
        self._mapping: Optional[EmbeddingMapping] = None
        self._reranker = CrossEncoderReranker(batch_size=batch_size) if use_reranker else None
        self._bm25 = BM25Retriever()
        self._fetch_k_multiplier = fetch_k_multiplier

        # Query cache: (query, top_k, min_score) -> List[SearchResult]
        self._cache: Dict[Tuple, List[SearchResult]] = {}
        self._max_cache_size = max_cache_size

        self._loaded = False

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load all persisted components from storage.

        Loads:
            - Chunk store (``storage/chunks.jsonl``)
            - FAISS index (``storage/faiss.index``)
            - Mapping (``storage/mapping.json``)
            - Embedding encoder (model loaded lazily on first query)

        Raises:
            FileNotFoundError: If any required file is missing.
            ValueError: If component sizes are inconsistent.
        """
        start = time.perf_counter()

        logger.info("Loading search engine components...")

        # 1. Chunks
        self._chunks = load_chunks(CHUNKS_PATH)
        self._chunk_map = {c.chunk_id: c for c in self._chunks}
        self._bm25.fit(self._chunks)

        # 2. FAISS index + mapping
        self._index = VectorIndex.load(
            index_path=FAISS_INDEX_PATH,
            mapping_path=MAPPING_PATH,
        )
        self._mapping = self._index.mapping

        # 3. Encoder (model loads lazily on first query)
        self._encoder = EmbeddingEncoder()

        # 4. Cross-validate counts
        self._validate_alignment()

        self._loaded = True
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        logger.info(
            "Search engine loaded | chunks=%d index_vectors=%d "
            "mapping_entries=%d load_time_ms=%d",
            len(self._chunks),
            len(self._index),
            len(self._mapping) if self._mapping else 0,
            elapsed_ms,
        )

    def load_from_objects(
        self,
        chunks: List[Chunk],
        embeddings: np.ndarray,
        mapping: EmbeddingMapping,
    ) -> None:
        """Load from in-memory objects (for pipeline use without persistence).

        Args:
            chunks:     List of Chunk objects.
            embeddings: (N, dim) float32 embedding matrix.
            mapping:    Bidirectional index <-> chunk_id mapping.
        """
        self._chunks = chunks
        self._chunk_map = {c.chunk_id: c for c in chunks}
        self._bm25.fit(chunks)
        self._mapping = mapping

        self._index = VectorIndex()
        self._index.build(embeddings, mapping)

        self._encoder = EmbeddingEncoder()

        self._validate_alignment()
        self._loaded = True

        logger.info(
            "Search engine loaded from objects | chunks=%d index_vectors=%d",
            len(self._chunks), len(self._index),
        )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = TOP_K_DEFAULT,
        fetch_k: Optional[int] = None,
        min_score: Optional[float] = None,
    ) -> List[SearchResult]:
        """Execute a semantic search query.

        Args:
            query:     Natural language query string.
            top_k:     Maximum number of results to return.
            min_score: Optional minimum similarity score threshold.
                       Results below this score are filtered out.
                       If ``None``, all top-K results are returned.

        Returns:
            List of :class:`~vectoria.models.SearchResult` objects,
            ranked by descending similarity score (1-indexed rank).

        Raises:
            RuntimeError: If the engine has not been loaded.
            ValueError:   If the query is empty.
        """
        if not self._loaded:
            raise RuntimeError(
                "Engine not loaded. Call load() or load_from_objects() first."
            )

        total_start = time.perf_counter()

        # -- 1. Validate query -----------------------------------------
        query = self._validate_query(query)

        # -- 2. Check cache --------------------------------------------
        # Cache key tracks reranker state to avoid serving unranked FAISS results
        # when a reranker is expected. Note: Changes to underlying model weights
        # or batch sizes do not invalidate the cache.
        cache_key = (query, top_k, min_score, self._reranker is not None)
        if cache_key in self._cache:
            logger.debug("Cache hit | query=%s", repr(query[:50]))
            return self._cache[cache_key]

        # -- 3. Resolve fetch_k ----------------------------------------
        if fetch_k is None:
            fetch_k = top_k * self._fetch_k_multiplier if self._reranker else top_k
        fetch_k = max(fetch_k, top_k)

        # -- 4. Encode query -------------------------------------------
        encode_start = time.perf_counter()
        query_vec = self._encoder.encode_query(query)
        encode_ms = int((time.perf_counter() - encode_start) * 1000)

        # -- 5. Search FAISS index -------------------------------------
        search_start = time.perf_counter()
        scores, indices = self._index.search(query_vec, top_k=fetch_k)
        
        # -- 5b. Search BM25 -------------------------------------------
        bm25_scores = self._bm25.get_scores(query)
        search_ms = int((time.perf_counter() - search_start) * 1000)

        # -- 6. Build initial results ----------------------------------
        faiss_candidates = self._build_results(scores, indices, min_score)
        candidates = self._reciprocal_rank_fusion(faiss_candidates, bm25_scores, top_k=fetch_k)

        # -- 7. Apply Reranking ----------------------------------------
        rerank_ms = 0
        if self._reranker and candidates:  # Skip model call if no candidates found
            try:
                rerank_start = time.perf_counter()
                
                # Reranker processes all pairs in a batched forward pass
                reranked_candidates = self._reranker.rerank(query, candidates)
                if len(reranked_candidates) != len(candidates):
                    raise ValueError(
                        f"Reranker returned {len(reranked_candidates)} results, expected {len(candidates)}"
                    )
                candidates = reranked_candidates
                rerank_ms = int((time.perf_counter() - rerank_start) * 1000)
            except Exception as e:
                # Graceful fallback: serve FAISS results if the heavy compute layer fails
                logger.error("Reranker failed | type=%s | msg=%s", type(e).__name__, str(e))

        # -- 8. Final Slicing and Rank Assignment ----------------------
        final_results = candidates[:top_k]
        for rank, res in enumerate(final_results, 1):
            res.rank = rank

        # -- 9. Log + cache --------------------------------------------
        total_ms = int((time.perf_counter() - total_start) * 1000)

        self._log_search(query, top_k, min_score, final_results,
                         scores, encode_ms, search_ms, rerank_ms, total_ms, self._reranker is not None)

        self._cache_put(cache_key, final_results)

        return final_results

    # ------------------------------------------------------------------
    # Internal: result building
    # ------------------------------------------------------------------

    def _build_results(
        self,
        scores: np.ndarray,
        indices: np.ndarray,
        min_score: Optional[float],
    ) -> List[SearchResult]:
        """Convert FAISS output into ranked SearchResult objects.

        Sorting:
            - Primary: score descending.
            - Tie-breaker: chunk_id ascending (deterministic).

        Filtering:
            - Invalid indices (< 0) are discarded.
            - Unmapped chunk_ids are discarded with a warning.
            - Scores below ``min_score`` (if set) are discarded.
        """
        raw: List[Tuple[float, str, Chunk]] = []

        for score_val, idx_val in zip(scores, indices):
            idx = int(idx_val)
            score = float(score_val)

            if idx < 0:
                continue

            # Resolve index -> chunk_id -> Chunk
            try:
                chunk_id = self._index.get_chunk_id(idx)
            except KeyError:
                logger.warning("Unmapped index=%d, skipping", idx)
                continue

            chunk = self._chunk_map.get(chunk_id)
            if chunk is None:
                logger.warning(
                    "Chunk not found in store | chunk_id=%s index=%d",
                    chunk_id, idx,
                )
                continue

            # Optional score threshold
            if min_score is not None and score < min_score:
                continue

            raw.append((score, chunk_id, chunk))

        # Deterministic sort: score desc, then chunk_id asc for ties
        raw.sort(key=lambda t: (-t[0], t[1]))

        # Build SearchResult with 1-indexed rank
        results = [
            SearchResult(chunk=chunk, score=score, rank=rank)
            for rank, (score, _, chunk) in enumerate(raw, 1)
        ]

        return results

    def _reciprocal_rank_fusion(
        self, faiss_candidates: List[SearchResult], bm25_scores: np.ndarray, top_k: int, k: int = 60
    ) -> List[SearchResult]:
        """Combine dense (FAISS) and sparse (BM25) results using RRF."""
        # 1. Rank FAISS
        faiss_ranks = {res.chunk.chunk_id: rank for rank, res in enumerate(faiss_candidates, 1)}
        
        # 2. Rank BM25
        bm25_indices = np.argsort(bm25_scores)[::-1][:top_k*2]  # Get top candidates
        bm25_ranks = {}
        for rank, idx in enumerate(bm25_indices, 1):
            if bm25_scores[idx] > 0:
                chunk = self._chunks[idx]
                bm25_ranks[chunk.chunk_id] = rank
                
        # 3. Fuse scores
        rrf_scores = {}
        all_chunks = {}
        
        for res in faiss_candidates:
            chunk_id = res.chunk.chunk_id
            all_chunks[chunk_id] = res.chunk
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + (1.0 / (k + faiss_ranks[chunk_id]))
            
        for chunk_id, rank in bm25_ranks.items():
            if chunk_id not in all_chunks:
                all_chunks[chunk_id] = self._chunk_map[chunk_id]
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + (1.0 / (k + rank))
            
        # 4. Sort
        fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        return [
            SearchResult(chunk=all_chunks[chunk_id], score=score, rank=i)
            for i, (chunk_id, score) in enumerate(fused, 1)
        ][:top_k]

    # ------------------------------------------------------------------
    # Internal: validation
    # ------------------------------------------------------------------

    def _validate_query(self, query: str) -> str:
        """Validate and normalise query input.

        Returns:
            Stripped query string.

        Raises:
            ValueError: If query is empty after stripping.
        """
        if not isinstance(query, str):
            raise ValueError(f"Query must be a string, got {type(query).__name__}")

        query = query.strip()
        if not query:
            raise ValueError("Query must be a non-empty string")

        return query

    def _validate_alignment(self) -> None:
        """Verify that chunks, index, and mapping are consistent.

        Raises:
            ValueError: If counts do not match.
        """
        n_chunks = len(self._chunks) if self._chunks else 0
        n_index = len(self._index) if self._index else 0
        n_mapping = len(self._mapping) if self._mapping else 0

        if not (n_chunks == n_index == n_mapping):
            raise ValueError(
                f"Component count mismatch: chunks={n_chunks} "
                f"index={n_index} mapping={n_mapping}"
            )

        # Verify all mapped chunk_ids exist in chunk store
        if self._mapping and self._chunk_map:
            for i in range(n_mapping):
                cid = self._mapping.get_chunk_id(i)
                if cid not in self._chunk_map:
                    raise ValueError(
                        f"Mapping entry {i} -> {cid} not found in chunk store"
                    )

    # ------------------------------------------------------------------
    # Internal: logging
    # ------------------------------------------------------------------

    def _log_search(
        self,
        query: str,
        top_k: int,
        min_score: Optional[float],
        results: List[SearchResult],
        faiss_scores: np.ndarray,
        encode_ms: int,
        search_ms: int,
        rerank_ms: int,
        total_ms: int,
        rerank_applied: bool,
    ) -> None:
        """Log search metrics and score distribution."""
        top_score = results[0].score if results else 0.0
        faiss_top_score = float(faiss_scores[0]) if len(faiss_scores) > 0 else 0.0
        final_scores = [round(r.score, 4) for r in results[:3]]

        logger.info(
            "Search executed | query=%s top_k=%d min_score=%s "
            "results=%d top_score=%.4f faiss_top=%.4f final_scores_top3=%s "
            "encode_ms=%d search_ms=%d rerank_ms=%d total_ms=%d rerank_applied=%s",
            repr(query[:50]),
            top_k,
            min_score if min_score is not None else "none",
            len(results),
            top_score,
            faiss_top_score,
            final_scores,
            encode_ms,
            search_ms,
            rerank_ms,
            total_ms,
            rerank_applied,
        )

        # Score distribution for debugging
        if len(faiss_scores) > 0:
            analyze_score_distribution(faiss_scores, label=query[:30] + " (FAISS)")

    # ------------------------------------------------------------------
    # Internal: caching
    # ------------------------------------------------------------------

    def _cache_put(
        self, key: Tuple, results: List[SearchResult]
    ) -> None:
        """Insert into cache, evicting oldest entries if full."""
        if len(self._cache) >= self._max_cache_size:
            # Evict oldest entry (FIFO)
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[key] = results

    def clear_cache(self) -> None:
        """Clear the query cache."""
        count = len(self._cache)
        self._cache.clear()
        logger.debug("Cache cleared | evicted=%d", count)
