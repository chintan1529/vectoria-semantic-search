"""
Vectoria Configuration — Central configuration for all modules.

All tunable hyperparameters, file paths, and system constants are defined
here. Modules import from this single source of truth rather than
hardcoding values.

Design decisions:
    - Paths are resolved relative to the project root (this file's grandparent).
    - All constants use UPPER_SNAKE_CASE for clarity.
    - Chunk/embedding parameters are chosen for the 8GB RAM, CPU-only constraint.
    - SIMILARITY_METRIC is "cosine" implemented via IndexFlatIP on L2-normalized
      vectors, giving interpretable [0, 1] scores.
"""

from pathlib import Path

# ─────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────

# Project root: two levels up from vectoria/config.py
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Directory containing raw text documents to ingest
DATA_DIR: Path = PROJECT_ROOT / "data" / "wikipedia"

# Persistent storage for embeddings, FAISS index, and chunk metadata
STORAGE_DIR: Path = PROJECT_ROOT / "storage"

# Log output directory
LOG_DIR: Path = PROJECT_ROOT / "logs"

# Specific storage file paths
CHUNKS_PATH: Path = STORAGE_DIR / "chunks.jsonl"
EMBEDDINGS_PATH: Path = STORAGE_DIR / "embeddings.npy"
FAISS_INDEX_PATH: Path = STORAGE_DIR / "faiss.index"
MAPPING_PATH: Path = STORAGE_DIR / "mapping.json"

# ─────────────────────────────────────────────────────────────────────
# Embedding Model
# ─────────────────────────────────────────────────────────────────────

# Lightweight, high-performance model (~80MB, 384 dimensions)
# Chosen for CPU-only environments with limited RAM.
EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

# Dimensionality of the embedding vectors produced by the model.
EMBEDDING_DIM: int = 384

# Number of texts to encode per batch. 64 balances throughput
# against memory usage on an 8GB machine.
BATCH_SIZE: int = 64

# ─────────────────────────────────────────────────────────────────────
# Chunking
# ─────────────────────────────────────────────────────────────────────

# Target chunk size in words. 300 sits in the middle of the
# 200–500 word range specified in requirements.
CHUNK_SIZE_WORDS: int = 300

# Soft lower bound for chunk size (words).  Chunks smaller than this
# are merged with an adjacent chunk during post-processing to avoid
# fragmentation that degrades embedding quality.
CHUNK_MIN_WORDS: int = 200

# Soft upper bound for chunk size (words).  Chunks exceeding this
# are flagged in quality validation but NOT forcibly split (to
# preserve sentence integrity).
CHUNK_MAX_WORDS: int = 400

# Fraction of chunk_size used as overlap between consecutive chunks.
# 0.15 (15%) preserves cross-boundary context without excessive
# redundancy.  Overlap in words = int(300 * 0.15) = 45 words.
CHUNK_OVERLAP_RATIO: float = 0.15

# ─────────────────────────────────────────────────────────────────────
# Retrieval
# ─────────────────────────────────────────────────────────────────────

# Default number of results returned per query.
TOP_K_DEFAULT: int = 5

# Similarity metric.  "cosine" is implemented as inner-product on
# L2-normalized embeddings (IndexFlatIP), yielding scores in [0, 1].
SIMILARITY_METRIC: str = "cosine"

# ─────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────

# Console log level
LOG_LEVEL: str = "INFO"

# File log level (captures more detail for debugging)
LOG_FILE_LEVEL: str = "DEBUG"

# Maximum log file size before rotation (bytes) — 5 MB
LOG_MAX_BYTES: int = 5 * 1024 * 1024

# Number of rotated log backups to keep
LOG_BACKUP_COUNT: int = 3
