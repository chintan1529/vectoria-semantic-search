"""
Document Loader — Load and catalogue text documents from the filesystem.

Responsibilities:
    - Recursively discover ``.txt`` files under a data directory.
    - Read each file with UTF-8 encoding (graceful fallback on errors).
    - Generate deterministic ``doc_id`` via SHA-256 prefix of file content.
    - Derive ``category`` from the immediate parent directory name
      (e.g.  ``data/wikipedia/ai/neural_nets.txt`` → category ``"ai"``).
    - Skip empty / unreadable files and log warnings.
    - Emit structured log metrics on completion.

This module produces ``(raw_text, DocumentMeta)`` tuples that feed
directly into the chunking pipeline.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from vectoria.config import DATA_DIR
from vectoria.logger import get_logger
from vectoria.models import DocumentMeta

logger = get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────


def load_document(filepath: Path) -> Tuple[str, DocumentMeta] | None:
    """Read a single ``.txt`` file and build its metadata.

    Args:
        filepath: Absolute or project-relative path to a text file.

    Returns:
        A ``(text, DocumentMeta)`` tuple, or ``None`` if the file is
        empty, binary, or unreadable.
    """
    filepath = filepath.resolve()

    if not filepath.is_file():
        logger.warning("Skipped (not a file) | path=%s", filepath)
        return None

    if filepath.suffix.lower() != ".txt":
        logger.debug("Skipped (not .txt) | path=%s", filepath)
        return None

    # ── Read with encoding fallback ──────────────────────────────
    raw_text = _read_text_safe(filepath)
    if raw_text is None:
        return None

    raw_text = raw_text.strip()
    if not raw_text:
        logger.warning("Skipped (empty content) | path=%s", filepath)
        return None

    # ── Strip YAML header if present ─────────────────────────────
    header, text = _strip_yaml_header(raw_text)

    if not text.strip():
        logger.warning("Skipped (empty body after header) | path=%s", filepath)
        return None

    # ── Build metadata ───────────────────────────────────────────
    doc_id = _content_hash(text)

    # Prefer header title, fall back to filename
    title = header.get("title", filepath.stem.replace("_", " ").title())
    category = header.get("category", _derive_category(filepath))
    timestamp = header.get("timestamp", datetime.now(timezone.utc).isoformat())

    meta = DocumentMeta(
        doc_id=doc_id,
        source=str(filepath),
        title=title,
        category=category,
        timestamp=timestamp,
    )

    logger.debug(
        "Loaded document | doc_id=%s title=%s chars=%d category=%s",
        doc_id[:12],
        title,
        len(text),
        category,
    )
    return text, meta


def load_documents(
    directory: Path | None = None,
) -> List[Tuple[str, DocumentMeta]]:
    """Batch-load all ``.txt`` files from a directory tree.

    Args:
        directory: Root directory to scan.  Defaults to
                   :data:`vectoria.config.DATA_DIR`.

    Returns:
        List of ``(text, DocumentMeta)`` tuples for every successfully
        loaded document.
    """
    directory = (directory or DATA_DIR).resolve()

    if not directory.is_dir():
        logger.error("Data directory not found | path=%s", directory)
        return []

    start = time.perf_counter()
    results: List[Tuple[str, DocumentMeta]] = []
    skipped = 0
    duplicates = 0
    total_chars = 0
    seen_doc_ids: set[str] = set()

    txt_files = sorted(directory.rglob("*.txt"))
    logger.info(
        "Scanning for documents | directory=%s files_found=%d",
        directory,
        len(txt_files),
    )

    for fpath in txt_files:
        outcome = load_document(fpath)
        if outcome is None:
            skipped += 1
            continue
        text, meta = outcome

        # Deduplicate by content hash (handles Wikipedia redirects)
        if meta.doc_id in seen_doc_ids:
            duplicates += 1
            logger.debug(
                "Skipped duplicate | doc_id=%s title=%s",
                meta.doc_id[:12], meta.title,
            )
            continue
        seen_doc_ids.add(meta.doc_id)

        total_chars += len(text)
        results.append((text, meta))

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    logger.info(
        "Document loading complete | docs_loaded=%d docs_skipped=%d "
        "docs_duplicated=%d total_chars=%d load_time_ms=%d",
        len(results),
        skipped,
        duplicates,
        total_chars,
        elapsed_ms,
    )
    return results


# ─────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────


def _read_text_safe(filepath: Path) -> str | None:
    """Read a file as UTF-8, replacing malformed bytes.

    Returns ``None`` when the file cannot be read at all.
    """
    try:
        return filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError) as exc:
        logger.warning("Skipped (read error) | path=%s error=%s", filepath, exc)
        return None


def _strip_yaml_header(text: str) -> tuple[dict, str]:
    """Strip a YAML-style metadata header from the text.

    If the text starts with ``---``, everything up to and including
    the closing ``---`` is parsed as key-value pairs and removed
    from the body text.

    Returns:
        Tuple of (header_dict, body_text).
        If no header is present, returns ({}, original_text).
    """
    if not text.startswith("---"):
        return {}, text

    lines = text.split("\n")
    header_end = -1

    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            header_end = i
            break

    if header_end < 0:
        return {}, text

    # Parse header key-value pairs
    header = {}
    for line in lines[1:header_end]:
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            header[key.strip()] = value.strip()

    # Body is everything after the closing ---
    body = "\n".join(lines[header_end + 1:]).strip()

    return header, body


def _content_hash(text: str, length: int = 16) -> str:
    """Return a deterministic hex digest (SHA-256 prefix) of *text*.

    Using a 16-character prefix gives 64 bits of collision resistance,
    more than sufficient for corpora of <= 10 K documents.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def _derive_category(filepath: Path) -> str:
    """Derive a domain category from the file's parent directory name.

    For ``data/wikipedia/ai/file.txt`` this returns ``"ai"``.
    If the file sits directly in the data root, returns ``"general"``.
    """
    parent = filepath.parent
    data_root = DATA_DIR.resolve()

    if parent == data_root:
        return "general"

    return parent.name.lower()
