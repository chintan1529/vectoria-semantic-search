"""
Storage -- Persistent chunk storage and system integrity validation.

This module provides two critical capabilities:

1. **Chunk persistence** -- serialise/deserialise ``Chunk`` objects to/from
   JSONL (one JSON object per line).  This is the authoritative chunk store
   that the retrieval engine reads at query time.

2. **System integrity validation** -- verify that chunks, embeddings,
   FAISS index, and mapping are all consistent with each other before
   serving queries.

Design decisions
----------------
- **JSONL format** -- one JSON object per line, no framing.  This is
  append-friendly, streamable, and grep-friendly.

- **Ordering preserved** -- chunks are written and read in the same order.
  ``chunks[i]`` after load matches ``chunks[i]`` before save.

- **Lossless round-trip** -- ``Chunk.to_dict()`` / ``Chunk.from_dict()``
  are used directly.  All fields including nested ``DocumentMeta`` survive
  serialisation.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from vectoria.config import (
    CHUNKS_PATH,
    EMBEDDINGS_PATH,
    FAISS_INDEX_PATH,
    MAPPING_PATH,
    EMBEDDING_DIM,
)
from vectoria.logger import get_logger
from vectoria.models import Chunk

logger = get_logger(__name__)


# ------------------------------------------------------------------
# Chunk Persistence
# ------------------------------------------------------------------


def save_chunks(
    chunks: List[Chunk],
    path: Path = CHUNKS_PATH,
) -> None:
    """Save chunks to a JSONL file (one JSON object per line).

    Args:
        chunks: Ordered list of Chunk objects.
        path:   Destination file path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    start = time.perf_counter()

    with open(path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            line = json.dumps(chunk.to_dict(), ensure_ascii=False)
            f.write(line + "\n")

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    size_kb = path.stat().st_size / 1024

    logger.info(
        "Chunks saved | path=%s count=%d size_kb=%.1f write_time_ms=%d",
        path, len(chunks), size_kb, elapsed_ms,
    )


def load_chunks(
    path: Path = CHUNKS_PATH,
) -> List[Chunk]:
    """Load chunks from a JSONL file.

    Args:
        path: Source file path.

    Returns:
        Ordered list of Chunk objects matching the save order.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Chunk file not found: {path}")

    start = time.perf_counter()
    chunks: List[Chunk] = []

    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                chunks.append(Chunk.from_dict(data))
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                logger.warning(
                    "Skipped malformed chunk | line=%d error=%s",
                    line_num, exc,
                )

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    logger.info(
        "Chunks loaded | path=%s count=%d load_time_ms=%d",
        path, len(chunks), elapsed_ms,
    )
    return chunks


# ------------------------------------------------------------------
# Score Inspection Utilities
# ------------------------------------------------------------------


def analyze_score_distribution(
    scores: np.ndarray,
    label: str = "scores",
) -> Dict[str, float]:
    """Compute and log distribution statistics for similarity scores.

    This is an inspection utility for debugging retrieval quality.
    No filtering or thresholding is applied.

    Args:
        scores: 1D array of similarity scores.
        label:  Descriptive label for log output.

    Returns:
        Dict with keys: min, max, mean, std, median.
    """
    if len(scores) == 0:
        logger.warning("Empty score array | label=%s", label)
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0, "median": 0.0}

    stats = {
        "min": float(np.min(scores)),
        "max": float(np.max(scores)),
        "mean": float(np.mean(scores)),
        "std": float(np.std(scores)),
        "median": float(np.median(scores)),
    }

    logger.info(
        "Score distribution | label=%s count=%d "
        "min=%.4f max=%.4f mean=%.4f std=%.4f median=%.4f",
        label, len(scores),
        stats["min"], stats["max"], stats["mean"],
        stats["std"], stats["median"],
    )
    return stats


# ------------------------------------------------------------------
# System Integrity Validation
# ------------------------------------------------------------------


def validate_system_integrity(
    chunks_path: Path = CHUNKS_PATH,
    embeddings_path: Path = EMBEDDINGS_PATH,
    index_path: Path = FAISS_INDEX_PATH,
    mapping_path: Path = MAPPING_PATH,
    dimension: int = EMBEDDING_DIM,
) -> bool:
    """Verify that all persisted components are consistent.

    Checks performed:
        1. All required files exist.
        2. Chunks load successfully from JSONL.
        3. Embeddings load with correct dtype and shape.
        4. Embeddings are C-contiguous float32.
        5. Mapping loads and has matching entry count.
        6. FAISS index loads and has matching vector count.
        7. Every chunk_id in the mapping exists in the chunk store.
        8. No duplicate chunk_ids in the chunk store.
        9. len(chunks) == len(embeddings) == len(mapping) == index.ntotal.

    Args:
        chunks_path:     Path to chunks.jsonl.
        embeddings_path: Path to embeddings.npy.
        index_path:      Path to faiss.index.
        mapping_path:    Path to mapping.json.
        dimension:       Expected embedding dimension.

    Returns:
        ``True`` if all checks pass, ``False`` otherwise.
        Detailed results are logged at INFO/WARNING level.
    """
    logger.info("System integrity check starting...")
    errors: List[str] = []
    warnings: List[str] = []

    # -- 1. File existence ---------------------------------------------
    required_files = {
        "chunks": Path(chunks_path),
        "embeddings": Path(embeddings_path),
        "index": Path(index_path),
        "mapping": Path(mapping_path),
    }

    for name, fpath in required_files.items():
        if not fpath.exists():
            errors.append(f"Missing file: {name} ({fpath})")

    if errors:
        for e in errors:
            logger.error("Integrity FAIL | %s", e)
        return False

    # -- 2. Load chunks ------------------------------------------------
    try:
        chunks = load_chunks(chunks_path)
    except Exception as exc:
        logger.error("Integrity FAIL | chunk_load_error=%s", exc)
        return False

    # -- 3. Load embeddings --------------------------------------------
    try:
        embeddings = np.load(str(embeddings_path)).astype(np.float32)
    except Exception as exc:
        logger.error("Integrity FAIL | embedding_load_error=%s", exc)
        return False

    # -- 4. Embedding dtype & contiguity -------------------------------
    if embeddings.dtype != np.float32:
        errors.append(f"Embedding dtype={embeddings.dtype}, expected float32")

    if not embeddings.flags["C_CONTIGUOUS"]:
        warnings.append("Embeddings are not C-contiguous (performance impact)")

    if embeddings.ndim != 2 or embeddings.shape[1] != dimension:
        errors.append(
            f"Embedding shape={embeddings.shape}, expected (N, {dimension})"
        )

    # NaN/Inf check
    if np.any(np.isnan(embeddings)):
        errors.append("Embeddings contain NaN values")
    if np.any(np.isinf(embeddings)):
        errors.append("Embeddings contain Inf values")

    # -- 5. Load mapping -----------------------------------------------
    try:
        from vectoria.embedding.encoder import EmbeddingMapping
        mapping = EmbeddingMapping.load(mapping_path)
    except Exception as exc:
        logger.error("Integrity FAIL | mapping_load_error=%s", exc)
        return False

    # -- 6. Load FAISS index -------------------------------------------
    try:
        import faiss
        index = faiss.read_index(str(index_path))
    except Exception as exc:
        logger.error("Integrity FAIL | index_load_error=%s", exc)
        return False

    # -- 7. Count consistency ------------------------------------------
    n_chunks = len(chunks)
    n_embeddings = embeddings.shape[0]
    n_mapping = len(mapping)
    n_index = index.ntotal

    if not (n_chunks == n_embeddings == n_mapping == n_index):
        errors.append(
            f"Count mismatch: chunks={n_chunks} embeddings={n_embeddings} "
            f"mapping={n_mapping} index={n_index}"
        )

    # -- 8. Chunk_id consistency ---------------------------------------
    chunk_ids_from_store = [c.chunk_id for c in chunks]

    # Check duplicates
    seen = set()
    duplicates = []
    for cid in chunk_ids_from_store:
        if cid in seen:
            duplicates.append(cid)
        seen.add(cid)

    if duplicates:
        errors.append(f"Duplicate chunk_ids in store: {duplicates[:5]}")

    # Check mapping chunk_ids match store chunk_ids
    chunk_id_set = set(chunk_ids_from_store)
    for i in range(n_mapping):
        mapped_id = mapping.get_chunk_id(i)
        if mapped_id not in chunk_id_set:
            errors.append(
                f"Mapping entry {i} -> {mapped_id} not found in chunk store"
            )
            break  # one error is enough to flag the issue

    # -- 9. Report -----------------------------------------------------
    for w in warnings:
        logger.warning("Integrity WARNING | %s", w)

    if errors:
        for e in errors:
            logger.error("Integrity FAIL | %s", e)
        logger.error(
            "System integrity check FAILED | errors=%d warnings=%d",
            len(errors), len(warnings),
        )
        return False

    logger.info(
        "System integrity check PASSED | "
        "chunks=%d embeddings=%s mapping=%d index=%d "
        "dtype=%s contiguous=%s warnings=%d",
        n_chunks, embeddings.shape, n_mapping, n_index,
        embeddings.dtype, embeddings.flags["C_CONTIGUOUS"],
        len(warnings),
    )
    return True
