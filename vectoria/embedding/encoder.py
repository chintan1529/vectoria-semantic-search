"""
Embedding Encoder -- Dense vector encoding using sentence-transformers.

This module wraps the ``all-MiniLM-L6-v2`` model to convert text chunks
into 384-dimensional dense embeddings suitable for cosine similarity
search via FAISS.

Design decisions
----------------
- **Lazy model loading** -- the model is downloaded/loaded on first use,
  not at import time.  This keeps module imports fast and avoids loading
  the model when it isn't needed (e.g. during index-only operations).

- **L2 normalisation** -- all embeddings are L2-normalised so that inner
  product (``IndexFlatIP``) equals cosine similarity.  This is done once
  at encoding time rather than at search time for efficiency.

- **Deterministic inference** -- the model is set to ``eval()`` mode and
  ``torch.no_grad()`` is used throughout.  Given the same input text and
  model weights, the output is bitwise reproducible on the same hardware.
  Note: cross-platform reproducibility (e.g. ARM vs x86) is NOT guaranteed
  due to floating-point implementation differences.

- **Explicit float32 dtype** -- all embeddings are explicitly cast to
  float32 and validated.  This guarantees compatibility with FAISS and
  avoids silent precision issues from mixed dtypes.

- **Batch processing** -- texts are encoded in batches of
  ``config.BATCH_SIZE`` (default 64) to balance throughput against memory
  usage on 8 GB RAM machines.  Progress is logged per batch.

- **Explicit index mapping** -- an ``EmbeddingMapping`` is produced
  alongside the embedding matrix, providing bidirectional lookup between
  ``embedding_index <-> chunk_id``.  This eliminates reliance on implicit
  array ordering and is persisted as ``storage/mapping.json``.

Usage
-----
::

    from vectoria.embedding.encoder import EmbeddingEncoder

    encoder = EmbeddingEncoder()
    embeddings, mapping = encoder.encode_chunks(chunks)
    query_vec = encoder.encode_query("search")  # (384,) np.ndarray
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from vectoria.config import EMBEDDING_MODEL, EMBEDDING_DIM, BATCH_SIZE
from vectoria.logger import get_logger
from vectoria.models import Chunk

logger = get_logger(__name__)


# ------------------------------------------------------------------
# Explicit Index Mapping
# ------------------------------------------------------------------


class EmbeddingMapping:
    """Bidirectional mapping between embedding indices and chunk IDs.

    Eliminates reliance on implicit array ordering.  Persisted as JSON
    alongside the embedding matrix so that the relationship survives
    save/load cycles.

    Attributes:
        index_to_chunk_id: Dict mapping embedding row index -> chunk_id.
        chunk_id_to_index: Dict mapping chunk_id -> embedding row index.
    """

    def __init__(self, chunk_ids: List[str]) -> None:
        self.index_to_chunk_id: Dict[int, str] = {
            i: cid for i, cid in enumerate(chunk_ids)
        }
        self.chunk_id_to_index: Dict[str, int] = {
            cid: i for i, cid in enumerate(chunk_ids)
        }

    def __len__(self) -> int:
        return len(self.index_to_chunk_id)

    def get_chunk_id(self, index: int) -> str:
        """Return the chunk_id for a given embedding index."""
        return self.index_to_chunk_id[index]

    def get_index(self, chunk_id: str) -> int:
        """Return the embedding index for a given chunk_id."""
        return self.chunk_id_to_index[chunk_id]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "version": 1,
            "count": len(self),
            "index_to_chunk_id": {str(k): v for k, v in self.index_to_chunk_id.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EmbeddingMapping:
        """Reconstruct from a serialized dict."""
        id_map = data["index_to_chunk_id"]
        chunk_ids = [id_map[str(i)] for i in range(len(id_map))]
        return cls(chunk_ids)

    def save(self, path: Path) -> None:
        """Persist mapping to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info("Mapping saved | path=%s entries=%d", path, len(self))

    @classmethod
    def load(cls, path: Path) -> EmbeddingMapping:
        """Load mapping from a JSON file."""
        with open(Path(path), "r", encoding="utf-8") as f:
            data = json.load(f)
        mapping = cls.from_dict(data)
        logger.info("Mapping loaded | path=%s entries=%d", path, len(mapping))
        return mapping


class EmbeddingEncoder:
    """Thin wrapper around a sentence-transformers model.

    Attributes:
        model_name: HuggingFace model identifier.
        dimension:  Expected embedding dimensionality.
    """

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL,
        dimension: int = EMBEDDING_DIM,
    ) -> None:
        self.model_name = model_name
        self.dimension = dimension
        self._model = None  # lazy-loaded

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def encode_texts(
        self,
        texts: List[str],
        batch_size: int = BATCH_SIZE,
    ) -> np.ndarray:
        """Encode a list of text strings into L2-normalised float32 embeddings.

        Args:
            texts:      Ordered list of text strings.
            batch_size: Number of texts per encoding batch.  Clamped to
                        ``len(texts)`` if larger.

        Returns:
            A ``(N, dimension)`` **float32** NumPy array where ``N = len(texts)``.
            Each row is an L2-normalised embedding vector.

        Raises:
            ValueError: If *texts* is empty or any embedding contains NaN.
        """
        if not texts:
            raise ValueError("Cannot encode empty text list")

        model = self._get_model()
        n = len(texts)
        # Clamp batch_size to avoid unnecessarily large internal buffers
        batch_size = min(batch_size, n)

        logger.info(
            "Encoding texts | total=%d batch_size=%d dimension=%d",
            n, batch_size, self.dimension,
        )

        start = time.perf_counter()
        all_embeddings: List[np.ndarray] = []
        batches_processed = 0

        for batch_start in range(0, n, batch_size):
            batch_end = min(batch_start + batch_size, n)
            batch_texts = texts[batch_start:batch_end]

            batch_emb = model.encode(
                batch_texts,
                batch_size=batch_size,
                show_progress_bar=False,
                normalize_embeddings=True,   # L2 normalisation
                convert_to_numpy=True,
            )

            # Enforce float32 immediately per batch
            if batch_emb.dtype != np.float32:
                logger.warning(
                    "Batch dtype mismatch, casting | got=%s expected=float32",
                    batch_emb.dtype,
                )
                batch_emb = batch_emb.astype(np.float32)

            all_embeddings.append(batch_emb)
            batches_processed += 1

            logger.debug(
                "Batch encoded | batch=%d/%d vectors=%d dtype=%s",
                batches_processed,
                (n + batch_size - 1) // batch_size,
                len(batch_texts),
                batch_emb.dtype,
            )

        # Stack all batches into a single (N, dim) array
        embeddings = np.vstack(all_embeddings)

        # Final dtype enforcement
        if embeddings.dtype != np.float32:
            embeddings = embeddings.astype(np.float32)

        elapsed = time.perf_counter() - start
        elapsed_ms = int(elapsed * 1000)
        vectors_per_sec = n / max(elapsed, 1e-6)

        # -- Validation ------------------------------------------------
        self._validate_embeddings(embeddings, n)

        logger.info(
            "Encoding complete | total_vectors=%d dimension=%d dtype=%s "
            "batches_processed=%d embedding_time_ms=%d "
            "vectors_per_sec=%.1f memory_bytes=%d",
            n, embeddings.shape[1], embeddings.dtype,
            batches_processed, elapsed_ms,
            vectors_per_sec, embeddings.nbytes,
        )

        return embeddings

    def encode_chunks(
        self,
        chunks: List[Chunk],
        batch_size: int = BATCH_SIZE,
    ) -> Tuple[np.ndarray, EmbeddingMapping]:
        """Encode Chunk objects into embeddings with explicit index mapping.

        Returns both the embedding matrix and an :class:`EmbeddingMapping`
        that provides bidirectional lookup between embedding indices and
        chunk IDs.  This eliminates any reliance on implicit ordering.

        Args:
            chunks:     Ordered list of Chunk objects.
            batch_size: Number of texts per encoding batch.

        Returns:
            Tuple of:
                - ``(N, dimension)`` float32 NumPy array.
                - :class:`EmbeddingMapping` for index <-> chunk_id lookup.
        """
        texts = [chunk.text for chunk in chunks]
        chunk_ids = [chunk.chunk_id for chunk in chunks]

        embeddings = self.encode_texts(texts, batch_size)
        mapping = EmbeddingMapping(chunk_ids)

        logger.info(
            "Chunk-to-embedding mapping created | entries=%d",
            len(mapping),
        )

        return embeddings, mapping

    def encode_query(self, query: str) -> np.ndarray:
        """Encode a single query string into an L2-normalised embedding.

        Args:
            query: The search query text.

        Returns:
            A ``(dimension,)`` float32 NumPy array.
        """
        if not query or not query.strip():
            raise ValueError("Query must be a non-empty string")

        model = self._get_model()

        start = time.perf_counter()
        embedding = model.encode(
            [query],
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).astype(np.float32)

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.debug(
            "Query encoded | query=%s time_ms=%d",
            repr(query[:50]), elapsed_ms,
        )

        return embedding[0]  # (dim,) not (1, dim)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    @staticmethod
    def save_embeddings(embeddings: np.ndarray, path) -> None:
        """Save embeddings to a ``.npy`` file with a companion checksum.

        A ``.sha256`` file is written alongside the ``.npy`` file so
        that :meth:`load_embeddings` can detect corruption.

        Args:
            embeddings: The (N, dim) float32 array to persist.
            path:       Destination file path.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Enforce dtype before saving
        if embeddings.dtype != np.float32:
            embeddings = embeddings.astype(np.float32)

        np.save(str(path), embeddings)

        # Write checksum
        checksum = _compute_checksum(path)
        checksum_path = path.with_suffix(".sha256")
        checksum_path.write_text(checksum, encoding="utf-8")

        logger.info(
            "Embeddings saved | path=%s shape=%s dtype=%s "
            "size_mb=%.2f checksum=%s",
            path, embeddings.shape, embeddings.dtype,
            embeddings.nbytes / (1024 * 1024),
            checksum[:16],
        )

    @staticmethod
    def load_embeddings(path) -> np.ndarray:
        """Load embeddings from a ``.npy`` file with checksum verification.

        If a companion ``.sha256`` file exists, the loaded file hash
        is compared to detect corruption.

        Args:
            path: Source file path.

        Returns:
            The (N, dim) float32 NumPy array.

        Raises:
            ValueError: If checksum verification fails.
        """
        path = Path(path)
        embeddings = np.load(str(path)).astype(np.float32)

        # Verify checksum if available
        checksum_path = path.with_suffix(".sha256")
        if checksum_path.exists():
            expected = checksum_path.read_text(encoding="utf-8").strip()
            actual = _compute_checksum(path)
            if actual != expected:
                raise ValueError(
                    f"Embedding file corrupted: checksum mismatch "
                    f"(expected {expected[:16]}..., got {actual[:16]}...)"
                )
            logger.debug("Checksum verified | path=%s", path)

        logger.info(
            "Embeddings loaded | path=%s shape=%s dtype=%s",
            path, embeddings.shape, embeddings.dtype,
        )
        return embeddings

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_model(self):
        """Lazy-load the sentence-transformers model.

        The model is loaded once and cached for the lifetime of this
        encoder instance.  Loading time is logged.
        """
        if self._model is not None:
            return self._model

        logger.info("Loading embedding model | model=%s", self.model_name)
        start = time.perf_counter()

        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(self.model_name)
        self._model.eval()  # deterministic inference

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "Model loaded | model=%s dimension=%d load_time_ms=%d",
            self.model_name, self.dimension, elapsed_ms,
        )

        return self._model

    def _validate_embeddings(
        self, embeddings: np.ndarray, expected_count: int
    ) -> None:
        """Validate embedding array for correctness.

        Checks:
            1. dtype is float32.
            2. Shape matches (expected_count, dimension).
            3. No NaN or Inf values.
            4. All vectors are L2-normalised (norm ~ 1.0).
            5. No exact duplicate vectors (basic check).

        Raises:
            ValueError: On any critical validation failure.
        """
        # 1. Dtype check
        if embeddings.dtype != np.float32:
            raise ValueError(
                f"Embedding dtype mismatch: got {embeddings.dtype}, "
                f"expected float32"
            )

        # 2. Count check
        if embeddings.shape[0] != expected_count:
            raise ValueError(
                f"Embedding count mismatch: got {embeddings.shape[0]}, "
                f"expected {expected_count}"
            )

        # 3. Dimension check
        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Embedding dimension mismatch: got {embeddings.shape[1]}, "
                f"expected {self.dimension}"
            )

        # 4. NaN / Inf check
        if np.any(np.isnan(embeddings)):
            raise ValueError("Embeddings contain NaN values")
        if np.any(np.isinf(embeddings)):
            raise ValueError("Embeddings contain Inf values")

        # 5. L2 normalisation check (norms should be ~1.0)
        norms = np.linalg.norm(embeddings, axis=1)
        max_deviation = np.max(np.abs(norms - 1.0))
        if max_deviation > 1e-4:
            logger.warning(
                "L2 norm deviation detected | max_deviation=%.6f",
                max_deviation,
            )

        # 6. Duplicate detection (warn only, don't fail)
        if expected_count > 1:
            # Compare each pair -- O(N^2) but N is small in Phase 1
            # For large N, use a hash-based approach instead
            n_dupes = 0
            if expected_count <= 5000:  # only check for tractable sizes
                for i in range(expected_count):
                    for j in range(i + 1, expected_count):
                        if np.array_equal(embeddings[i], embeddings[j]):
                            n_dupes += 1
                if n_dupes > 0:
                    logger.warning(
                        "Duplicate embeddings detected | count=%d", n_dupes
                    )

        logger.debug(
            "Embedding validation passed | shape=%s dtype=%s "
            "norm_range=[%.4f, %.4f] norm_sample=[%s]",
            embeddings.shape, embeddings.dtype,
            norms.min(), norms.max(),
            ", ".join(f"{n:.4f}" for n in norms[:5]),
        )


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _compute_checksum(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()
