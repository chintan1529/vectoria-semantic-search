"""
Vector Index -- FAISS-based similarity search over dense embeddings.

This module provides a thin, production-grade wrapper around a FAISS
``IndexFlatIP`` (inner-product) index.  Because all embeddings are
L2-normalised at encoding time, inner product is mathematically
equivalent to cosine similarity::

    cos(a, b) = dot(a, b) / (||a|| * ||b||)

When ||a|| = ||b|| = 1 (L2-normalised), this simplifies to::

    cos(a, b) = dot(a, b)

Hence ``IndexFlatIP`` on normalised vectors gives exact cosine similarity
scores in the range [-1, 1], with 1.0 being identical.

Why IndexFlatIP (brute-force)?
------------------------------
For corpora of <= 10K vectors (Phase 1 target: 100--300 documents,
~500--1500 chunks), brute-force inner-product search is:

- **Exact** -- no approximation error from quantisation or clustering.
- **Fast enough** -- search over 1500 x 384 takes < 1 ms on CPU.
- **Simple** -- no training step, no hyperparameters, no index rebuild.

For larger corpora (100K+ vectors), this can be swapped for
``IndexIVFFlat`` or ``IndexHNSWFlat`` without changing the public API.

Design decisions
----------------
- **Memory contiguity** -- embeddings are forced to C-contiguous float32
  before being added to the index.  FAISS requires this layout.

- **Mapping integration** -- the index stores a reference to the
  :class:`~vectoria.embedding.encoder.EmbeddingMapping` so that search
  results can be resolved to ``chunk_id`` without implicit ordering.

- **Persistence** -- index and mapping are saved/loaded as a pair.
  Loading validates that the index size matches the mapping.

Usage
-----
::

    from vectoria.indexing.faiss_index import VectorIndex

    index = VectorIndex()
    index.build(embeddings, mapping)
    scores, indices = index.search(query_vec, top_k=5)
    index.save()
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional, Tuple

import faiss
import numpy as np

from vectoria.config import EMBEDDING_DIM, FAISS_INDEX_PATH, MAPPING_PATH
from vectoria.embedding.encoder import EmbeddingMapping
from vectoria.logger import get_logger

logger = get_logger(__name__)


class VectorIndex:
    """FAISS-backed vector index for cosine similarity search.

    Attributes:
        dimension:   Embedding dimensionality (default 384).
        index_path:  Default path for persisting the FAISS index.
        mapping_path: Default path for persisting the index mapping.
    """

    def __init__(
        self,
        dimension: int = EMBEDDING_DIM,
        index_path: Path = FAISS_INDEX_PATH,
        mapping_path: Path = MAPPING_PATH,
    ) -> None:
        self.dimension = dimension
        self.index_path = Path(index_path)
        self.mapping_path = Path(mapping_path)

        self._index: Optional[faiss.IndexFlatIP] = None
        self._mapping: Optional[EmbeddingMapping] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        embeddings: np.ndarray,
        mapping: EmbeddingMapping,
    ) -> None:
        """Build a FAISS index from an embedding matrix.

        Args:
            embeddings: ``(N, dimension)`` float32 NumPy array.
                        Must be L2-normalised and C-contiguous.
            mapping:    Bidirectional chunk_id <-> index mapping.

        Raises:
            ValueError: On shape/dtype mismatch or count inconsistency.
        """
        start = time.perf_counter()

        # -- Validate inputs -------------------------------------------
        self._validate_build_inputs(embeddings, mapping)

        # -- Ensure memory layout --------------------------------------
        embeddings = np.ascontiguousarray(embeddings, dtype=np.float32)

        # -- Create index ----------------------------------------------
        self._index = faiss.IndexFlatIP(self.dimension)
        self._index.add(embeddings)
        self._mapping = mapping

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        # -- Validate post-build ---------------------------------------
        if self._index.ntotal != embeddings.shape[0]:
            raise RuntimeError(
                f"Index size mismatch after build: "
                f"index.ntotal={self._index.ntotal}, "
                f"expected={embeddings.shape[0]}"
            )

        logger.info(
            "Index built | index_type=IndexFlatIP vectors=%d "
            "dimension=%d build_time_ms=%d "
            "memory_bytes=%d",
            self._index.ntotal,
            self.dimension,
            elapsed_ms,
            embeddings.nbytes,
        )

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Search the index for the top-K most similar vectors.

        Args:
            query_embedding: A ``(dimension,)`` or ``(1, dimension)``
                             L2-normalised float32 vector.
            top_k:           Number of results to return.

        Returns:
            Tuple of:
                - ``scores``:  ``(top_k,)`` float32 array of similarity
                  scores in descending order (highest first).
                - ``indices``: ``(top_k,)`` int64 array of embedding
                  indices corresponding to the scores.

        Raises:
            RuntimeError: If the index has not been built or loaded.
            ValueError:   If query shape or dtype is invalid.
        """
        if self._index is None:
            raise RuntimeError("Index not built. Call build() or load() first.")

        # -- Validate query --------------------------------------------
        query = self._prepare_query(query_embedding)

        # -- Clamp top_k to index size ---------------------------------
        effective_k = min(top_k, self._index.ntotal)

        # -- Search ----------------------------------------------------
        start = time.perf_counter()
        scores, indices = self._index.search(query, effective_k)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        # Flatten from (1, k) to (k,)
        scores = scores[0]
        indices = indices[0]

        # Filter out invalid indices (FAISS returns -1 for unfilled slots)
        valid_mask = indices >= 0
        scores = scores[valid_mask]
        indices = indices[valid_mask]

        logger.debug(
            "Search complete | top_k=%d results=%d "
            "best_score=%.4f worst_score=%.4f search_time_ms=%d",
            top_k, len(scores),
            float(scores[0]) if len(scores) > 0 else 0.0,
            float(scores[-1]) if len(scores) > 0 else 0.0,
            elapsed_ms,
        )

        return scores, indices

    def get_chunk_id(self, index: int) -> str:
        """Resolve an embedding index to a chunk_id via the mapping.

        Args:
            index: The embedding row index from a search result.

        Returns:
            The corresponding chunk_id string.

        Raises:
            RuntimeError: If no mapping is loaded.
        """
        if self._mapping is None:
            raise RuntimeError("No mapping loaded. Call build() or load() first.")
        return self._mapping.get_chunk_id(index)

    @property
    def mapping(self) -> Optional[EmbeddingMapping]:
        """Access the underlying EmbeddingMapping (read-only)."""
        return self._mapping

    def __len__(self) -> int:
        """Return the number of vectors in the index."""
        if self._index is None:
            return 0
        return self._index.ntotal

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(
        self,
        index_path: Optional[Path] = None,
        mapping_path: Optional[Path] = None,
    ) -> None:
        """Save the FAISS index and mapping to disk.

        Args:
            index_path:   Override for the index file path.
            mapping_path: Override for the mapping file path.

        Raises:
            RuntimeError: If the index has not been built.
        """
        if self._index is None:
            raise RuntimeError("Cannot save: index not built.")

        idx_path = Path(index_path or self.index_path)
        map_path = Path(mapping_path or self.mapping_path)

        idx_path.parent.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self._index, str(idx_path))
        logger.info(
            "FAISS index saved | path=%s vectors=%d",
            idx_path, self._index.ntotal,
        )

        if self._mapping is not None:
            self._mapping.save(map_path)

    @classmethod
    def load(
        cls,
        index_path: Path = FAISS_INDEX_PATH,
        mapping_path: Path = MAPPING_PATH,
        dimension: int = EMBEDDING_DIM,
    ) -> VectorIndex:
        """Load a FAISS index and mapping from disk.

        Args:
            index_path:   Path to the ``.index`` file.
            mapping_path: Path to the ``mapping.json`` file.
            dimension:    Expected embedding dimension.

        Returns:
            A fully initialised :class:`VectorIndex` instance.

        Raises:
            FileNotFoundError: If the index file does not exist.
            ValueError:        If index/mapping sizes are inconsistent.
        """
        idx_path = Path(index_path)
        map_path = Path(mapping_path)

        if not idx_path.exists():
            raise FileNotFoundError(f"Index file not found: {idx_path}")

        start = time.perf_counter()

        instance = cls(dimension=dimension, index_path=idx_path, mapping_path=map_path)
        instance._index = faiss.read_index(str(idx_path))

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "FAISS index loaded | path=%s vectors=%d load_time_ms=%d",
            idx_path, instance._index.ntotal, elapsed_ms,
        )

        # Load mapping
        if map_path.exists():
            instance._mapping = EmbeddingMapping.load(map_path)

            # Cross-validate
            if len(instance._mapping) != instance._index.ntotal:
                raise ValueError(
                    f"Index/mapping size mismatch: "
                    f"index.ntotal={instance._index.ntotal}, "
                    f"mapping.entries={len(instance._mapping)}"
                )
        else:
            logger.warning(
                "Mapping file not found, index loaded without mapping | path=%s",
                map_path,
            )

        return instance

    # ------------------------------------------------------------------
    # Internal validation
    # ------------------------------------------------------------------

    def _validate_build_inputs(
        self, embeddings: np.ndarray, mapping: EmbeddingMapping
    ) -> None:
        """Validate inputs before building the index."""
        # Dtype
        if embeddings.dtype != np.float32:
            raise ValueError(
                f"Embeddings must be float32, got {embeddings.dtype}"
            )

        # Shape
        if embeddings.ndim != 2:
            raise ValueError(
                f"Embeddings must be 2D, got {embeddings.ndim}D"
            )
        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Dimension mismatch: embeddings have {embeddings.shape[1]}, "
                f"expected {self.dimension}"
            )

        # Count consistency
        if embeddings.shape[0] != len(mapping):
            raise ValueError(
                f"Embedding/mapping count mismatch: "
                f"embeddings={embeddings.shape[0]}, mapping={len(mapping)}"
            )

        # NaN check
        if np.any(np.isnan(embeddings)):
            raise ValueError("Embeddings contain NaN values")

    def _prepare_query(self, query_embedding: np.ndarray) -> np.ndarray:
        """Validate and reshape a query vector for FAISS search.

        Returns a ``(1, dimension)`` C-contiguous float32 array.
        """
        query = np.asarray(query_embedding, dtype=np.float32)

        if query.ndim == 1:
            query = query.reshape(1, -1)

        if query.shape != (1, self.dimension):
            raise ValueError(
                f"Query shape mismatch: got {query.shape}, "
                f"expected (1, {self.dimension})"
            )

        return np.ascontiguousarray(query)
