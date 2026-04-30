"""
Text Chunker -- Split documents into semantically coherent, overlapping chunks.

Strategy
--------
This chunker prioritises **sentence-boundary splitting** over naive word-count
slicing.  The algorithm works in four phases:

1. **Sentence segmentation** -- the raw text is split into sentences using a
   regex that handles common abbreviations, decimal numbers, and ellipses.
   This avoids breaking mid-sentence which would degrade embedding quality.

2. **Sentence accumulation** -- sentences are accumulated into a chunk until
   the word count reaches the target (``CHUNK_SIZE_WORDS``, default 300).
   When the threshold is crossed, the chunk is finalised and a new one
   starts.  A configurable number of *overlap sentences* from the tail of
   the previous chunk are prepended to the new chunk to preserve cross-
   boundary context.

3. **Small-chunk merging** -- any chunk below ``CHUNK_MIN_WORDS`` (200) is
   merged with its neighbour to avoid fragmentation that degrades embedding
   quality.  The merge target is the smaller adjacent chunk.

4. **Quality validation** -- every chunk is checked for size bounds
   (200--400 words) and metadata integrity.  Overlap between consecutive
   chunks is measured programmatically and logged.

Overlap Logic
-------------
Instead of overlapping by a flat word count (which may cut mid-sentence),
overlap is computed *sentence-by-sentence* from the end of the previous
chunk.  We accumulate trailing sentences backwards until their combined
word count reaches ``overlap_words`` (default: ``int(300 * 0.15) = 45``).
This guarantees each overlapping region is a complete set of sentences.

Edge Cases
----------
- **Short documents** (< chunk_size words) -- emitted as a single chunk.
- **Giant sentences** (single sentence > chunk_size words) -- force-split
  at word boundaries into sub-sentences of ``chunk_size`` words each, then
  fed back into the normal accumulation loop.
- **Empty text** -- returns an empty list (logged as warning).
- **Tiny trailing chunks** -- merged with the previous chunk.

All output ``Chunk`` objects are *frozen dataclasses*; no mutation occurs
after construction.
"""

from __future__ import annotations

import re
import time
from typing import List

from vectoria.config import (
    CHUNK_SIZE_WORDS,
    CHUNK_OVERLAP_RATIO,
    CHUNK_MIN_WORDS,
    CHUNK_MAX_WORDS,
)
from vectoria.logger import get_logger
from vectoria.models import Chunk, DocumentMeta

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Sentence splitting
# ---------------------------------------------------------------------------

# Split on sentence-ending punctuation (.!?) followed by one or more spaces.
# Abbreviation handling is done in post-processing by _split_into_sentences().
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")

# Known abbreviations that should NOT trigger a sentence split.
_ABBREVIATIONS = frozenset({
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "vs", "etc",
    "approx", "inc", "ltd", "co", "dept", "est", "govt", "univ",
    "vol", "fig", "eq", "no", "st", "ave", "blvd",
})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def chunk_text(
    text: str,
    doc_meta: DocumentMeta,
    chunk_size: int = CHUNK_SIZE_WORDS,
    overlap_ratio: float = CHUNK_OVERLAP_RATIO,
    min_chunk_words: int = CHUNK_MIN_WORDS,
) -> List[Chunk]:
    """Split *text* into overlapping, sentence-aligned chunks.

    Args:
        text:            Raw document text.
        doc_meta:        Metadata of the source document (immutable).
        chunk_size:      Target number of words per chunk.
        overlap_ratio:   Fraction of ``chunk_size`` used as overlap between
                         consecutive chunks (0.0 -- 1.0).
        min_chunk_words: Soft lower bound; chunks below this are merged.

    Returns:
        Ordered list of :class:`~vectoria.models.Chunk` objects.
    """
    if not text or not text.strip():
        logger.warning(
            "Empty text received | doc_id=%s title=%s",
            doc_meta.doc_id[:12],
            doc_meta.title,
        )
        return []

    start = time.perf_counter()
    overlap_words = int(chunk_size * overlap_ratio)

    # Phase 1: split into sentences, handling oversized sentences
    sentences = _split_into_sentences(text)
    sentences = _handle_oversized_sentences(sentences, chunk_size)

    # Phase 2: accumulate sentences into chunks with overlap
    raw_chunks = _accumulate_chunks(sentences, chunk_size, overlap_words)

    # Phase 3: merge undersized chunks
    raw_chunks = _merge_small_chunks(raw_chunks, min_chunk_words)

    # Phase 4: build Chunk objects
    chunks: List[Chunk] = []
    for idx, chunk_text_str in enumerate(raw_chunks):
        chunk = Chunk(
            chunk_id=f"{doc_meta.doc_id}_chunk_{idx}",
            doc_id=doc_meta.doc_id,
            text=chunk_text_str,
            metadata=doc_meta,
            chunk_index=idx,
        )
        chunks.append(chunk)

    # Phase 5: validate metadata integrity
    _validate_metadata(chunks, doc_meta)

    # Log per-document statistics
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    _log_chunk_stats(chunks, doc_meta, elapsed_ms)

    return chunks


def chunk_documents(
    documents: list[tuple[str, DocumentMeta]],
    chunk_size: int = CHUNK_SIZE_WORDS,
    overlap_ratio: float = CHUNK_OVERLAP_RATIO,
    min_chunk_words: int = CHUNK_MIN_WORDS,
) -> List[Chunk]:
    """Chunk a batch of documents and return a flat list of all chunks.

    This is a convenience wrapper around :func:`chunk_text` for the
    common case of processing the entire output of
    :func:`~vectoria.ingestion.loader.load_documents`.

    Logs comprehensive quality metrics including chunk-size distribution,
    overlap statistics, and quality flags upon completion.

    Args:
        documents:       List of ``(text, DocumentMeta)`` tuples.
        chunk_size:      Target words per chunk.
        overlap_ratio:   Overlap fraction.
        min_chunk_words: Soft lower bound for merging.

    Returns:
        Flat list of all :class:`Chunk` objects across all documents.
    """
    start = time.perf_counter()
    all_chunks: List[Chunk] = []

    for text, meta in documents:
        doc_chunks = chunk_text(text, meta, chunk_size, overlap_ratio, min_chunk_words)
        all_chunks.extend(doc_chunks)

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    # -- Global quality report -------------------------------------------------
    _log_global_stats(all_chunks, len(documents), elapsed_ms)
    _log_overlap_stats(all_chunks)
    _log_quality_flags(all_chunks)

    return all_chunks


# ---------------------------------------------------------------------------
# Internal helpers -- sentence splitting
# ---------------------------------------------------------------------------


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences, handling abbreviations and decimals.

    Uses a simple regex split on sentence-ending punctuation, then
    rejoins fragments that were incorrectly split on abbreviations
    (e.g., ``"Dr."``  ``"Smith"`` -> ``"Dr. Smith"``).
    """
    raw = _SENTENCE_END_RE.split(text.strip())
    raw = [s.strip() for s in raw if s.strip()]

    if not raw:
        return []

    # Post-process: rejoin fragments split on abbreviations or decimals
    merged: List[str] = [raw[0]]
    for fragment in raw[1:]:
        prev = merged[-1]
        last_word = prev.rsplit(None, 1)[-1].rstrip(".").lower() if prev else ""
        ends_with_abbrev = last_word in _ABBREVIATIONS
        ends_with_digit = (
            prev.rstrip().endswith(".")
            and len(prev) >= 2
            and prev.rstrip()[-2].isdigit()
        )

        if ends_with_abbrev or ends_with_digit:
            merged[-1] = prev + " " + fragment
        else:
            merged.append(fragment)

    return merged


def _handle_oversized_sentences(
    sentences: List[str], chunk_size: int
) -> List[str]:
    """Force-split any sentence longer than *chunk_size* words.

    Oversized sentences are broken at word boundaries into segments
    of at most ``chunk_size`` words each.
    """
    result: List[str] = []
    for sentence in sentences:
        words = sentence.split()
        if len(words) <= chunk_size:
            result.append(sentence)
        else:
            logger.debug(
                "Force-splitting oversized sentence | words=%d chunk_size=%d",
                len(words),
                chunk_size,
            )
            for i in range(0, len(words), chunk_size):
                segment = " ".join(words[i : i + chunk_size])
                if segment:
                    result.append(segment)
    return result


# ---------------------------------------------------------------------------
# Internal helpers -- chunk accumulation
# ---------------------------------------------------------------------------


def _accumulate_chunks(
    sentences: List[str],
    chunk_size: int,
    overlap_words: int,
) -> List[str]:
    """Accumulate sentences into chunks with sentence-level overlap.

    Algorithm:
        1. Walk through sentences, accumulating into the current chunk.
        2. When the current chunk's word count >= chunk_size, finalise it.
        3. Compute overlap: take trailing sentences from the finalised chunk
           whose combined word count is closest to ``overlap_words``.
        4. Start the next chunk with those overlap sentences.

    Returns:
        List of chunk text strings.
    """
    if not sentences:
        return []

    chunks: List[str] = []
    sent_data = [(s, len(s.split())) for s in sentences]

    current_sents: List[str] = []
    current_words = 0
    i = 0

    while i < len(sent_data):
        sent_text, sent_wc = sent_data[i]
        current_sents.append(sent_text)
        current_words += sent_wc
        i += 1

        if current_words >= chunk_size:
            chunk_str = " ".join(current_sents)
            chunks.append(chunk_str)

            overlap_sents = _compute_overlap_sentences(
                current_sents, overlap_words
            )
            current_sents = list(overlap_sents)
            current_words = sum(len(s.split()) for s in current_sents)

    # Flush remaining sentences as the last chunk
    if current_sents:
        chunk_str = " ".join(current_sents)
        if not chunks or chunk_str != chunks[-1]:
            chunks.append(chunk_str)

    return chunks


def _compute_overlap_sentences(
    sentences: List[str], target_words: int
) -> List[str]:
    """Select trailing sentences from *sentences* totalling <= *target_words*.

    Walks backwards through the sentence list, accumulating words until
    the target is reached.  Returns sentences in their original order.
    """
    if target_words <= 0:
        return []

    selected: List[str] = []
    accumulated = 0

    for sent in reversed(sentences):
        wc = len(sent.split())
        if accumulated + wc > target_words and selected:
            break
        selected.append(sent)
        accumulated += wc

    selected.reverse()
    return selected


# ---------------------------------------------------------------------------
# Internal helpers -- small-chunk merging  (NEW)
# ---------------------------------------------------------------------------


def _merge_small_chunks(
    raw_chunks: List[str], min_words: int
) -> List[str]:
    """Merge any chunk below *min_words* into an adjacent chunk.

    Strategy:
        - Walk through the list; if a chunk is undersized, merge it with
          its smaller neighbour to keep sizes balanced.
        - If only one neighbour exists (first or last), merge into that one.
        - Repeat until no undersized chunks remain or only one chunk is left.

    Returns:
        New list of chunk strings (input is not mutated).
    """
    if len(raw_chunks) <= 1:
        return raw_chunks

    merged = list(raw_chunks)
    changed = True

    while changed and len(merged) > 1:
        changed = False
        new_list: List[str] = []
        skip_next = False

        for i in range(len(merged)):
            if skip_next:
                skip_next = False
                continue

            wc = len(merged[i].split())

            if wc < min_words and len(merged) > 1:
                if i == 0 and i + 1 < len(merged):
                    # First chunk: merge forward
                    new_list.append(merged[i] + " " + merged[i + 1])
                    skip_next = True
                elif i == len(merged) - 1:
                    # Last chunk: merge backward
                    if new_list:
                        new_list[-1] = new_list[-1] + " " + merged[i]
                    else:
                        new_list.append(merged[i])
                else:
                    # Middle chunk: merge with smaller neighbour
                    prev_wc = len(new_list[-1].split()) if new_list else float("inf")
                    next_wc = len(merged[i + 1].split())

                    if prev_wc <= next_wc and new_list:
                        new_list[-1] = new_list[-1] + " " + merged[i]
                    else:
                        new_list.append(merged[i] + " " + merged[i + 1])
                        skip_next = True
                changed = True
            else:
                new_list.append(merged[i])

        merged = new_list

    return merged


# ---------------------------------------------------------------------------
# Internal helpers -- validation  (NEW)
# ---------------------------------------------------------------------------


def _validate_metadata(chunks: List[Chunk], doc_meta: DocumentMeta) -> None:
    """Check every chunk for metadata integrity.

    Logs a warning for any chunk that has missing or inconsistent metadata
    fields.  This is a defensive check -- under normal operation all fields
    should be populated by the constructor.
    """
    required_meta_fields = ("doc_id", "source", "title", "category", "timestamp")

    for chunk in chunks:
        # Check chunk-level fields
        if not chunk.chunk_id:
            logger.warning("Chunk missing chunk_id | doc_id=%s", chunk.doc_id[:12])
        if not chunk.doc_id:
            logger.warning("Chunk missing doc_id | chunk_id=%s", chunk.chunk_id)
        if chunk.chunk_index < 0:
            logger.warning(
                "Invalid chunk_index=%d | chunk_id=%s",
                chunk.chunk_index,
                chunk.chunk_id,
            )

        # Check metadata sub-fields
        meta = chunk.metadata
        for field_name in required_meta_fields:
            value = getattr(meta, field_name, None)
            if not value:
                logger.warning(
                    "Chunk metadata missing field | chunk_id=%s field=%s",
                    chunk.chunk_id,
                    field_name,
                )

        # Cross-check consistency
        if chunk.doc_id != doc_meta.doc_id:
            logger.error(
                "doc_id mismatch | chunk_id=%s chunk_doc_id=%s expected=%s",
                chunk.chunk_id,
                chunk.doc_id,
                doc_meta.doc_id,
            )


def _compute_overlap_between(chunk_a: str, chunk_b: str) -> int:
    """Compute the actual word-level overlap between two consecutive chunks.

    Finds the longest suffix of *chunk_a* that matches a prefix of *chunk_b*
    by comparing trailing/leading words.

    Returns:
        Number of overlapping words.
    """
    words_a = chunk_a.split()
    words_b = chunk_b.split()

    max_possible = min(len(words_a), len(words_b))
    overlap = 0

    for length in range(1, max_possible + 1):
        suffix_a = words_a[-length:]
        prefix_b = words_b[:length]
        if suffix_a == prefix_b:
            overlap = length

    return overlap


# ---------------------------------------------------------------------------
# Internal helpers -- logging
# ---------------------------------------------------------------------------


def _log_chunk_stats(
    chunks: List[Chunk], doc_meta: DocumentMeta, elapsed_ms: int
) -> None:
    """Log per-document chunk quality metrics at INFO level."""
    if not chunks:
        return

    word_counts = [c.word_count for c in chunks]
    avg_words = int(sum(word_counts) / len(word_counts))
    min_words = min(word_counts)
    max_words = max(word_counts)

    logger.info(
        "Chunked document | title=%s chunks=%d "
        "avg_chunk_words=%d min_chunk_words=%d max_chunk_words=%d "
        "chunk_time_ms=%d",
        doc_meta.title,
        len(chunks),
        avg_words,
        min_words,
        max_words,
        elapsed_ms,
    )


def _log_global_stats(
    all_chunks: List[Chunk], num_documents: int, elapsed_ms: int
) -> None:
    """Log global batch-level chunk statistics."""
    if not all_chunks:
        logger.warning("No chunks produced from %d documents", num_documents)
        return

    word_counts = [c.word_count for c in all_chunks]
    avg_words = int(sum(word_counts) / len(word_counts))

    # Compute chunks per document
    doc_chunk_counts: dict[str, int] = {}
    for c in all_chunks:
        doc_chunk_counts[c.doc_id] = doc_chunk_counts.get(c.doc_id, 0) + 1
    chunks_per_doc = list(doc_chunk_counts.values())
    avg_chunks_per_doc = sum(chunks_per_doc) / max(len(chunks_per_doc), 1)

    logger.info(
        "Batch chunking complete | total_documents=%d total_chunks=%d "
        "avg_chunk_words=%d min_chunk_words=%d max_chunk_words=%d "
        "avg_chunks_per_doc=%.1f chunk_time_ms=%d",
        num_documents,
        len(all_chunks),
        avg_words,
        min(word_counts),
        max(word_counts),
        avg_chunks_per_doc,
        elapsed_ms,
    )


def _log_overlap_stats(all_chunks: List[Chunk]) -> None:
    """Compute and log programmatic overlap metrics between consecutive chunks.

    Groups chunks by document, then measures actual word-level overlap
    between each pair of consecutive chunks within the same document.
    """
    # Group chunks by doc_id, preserving order
    doc_chunks: dict[str, List[Chunk]] = {}
    for c in all_chunks:
        doc_chunks.setdefault(c.doc_id, []).append(c)

    overlap_counts: List[int] = []

    for doc_id, chunks in doc_chunks.items():
        if len(chunks) < 2:
            continue
        # Sort by chunk_index to be safe
        chunks_sorted = sorted(chunks, key=lambda c: c.chunk_index)
        for i in range(len(chunks_sorted) - 1):
            overlap = _compute_overlap_between(
                chunks_sorted[i].text, chunks_sorted[i + 1].text
            )
            overlap_counts.append(overlap)

    if not overlap_counts:
        logger.info("Overlap stats | no_consecutive_chunk_pairs=true")
        return

    avg_overlap = sum(overlap_counts) / len(overlap_counts)
    min_overlap = min(overlap_counts)
    max_overlap = max(overlap_counts)

    logger.info(
        "Overlap verification | pairs_checked=%d "
        "avg_overlap_words=%.1f min_overlap_words=%d max_overlap_words=%d "
        "target_overlap_words=%d",
        len(overlap_counts),
        avg_overlap,
        min_overlap,
        max_overlap,
        int(CHUNK_SIZE_WORDS * CHUNK_OVERLAP_RATIO),
    )


def _log_quality_flags(all_chunks: List[Chunk]) -> None:
    """Flag chunks outside the acceptable size range and log a summary.

    Flags:
        - undersized: < CHUNK_MIN_WORDS (after merging, should be rare)
        - oversized:  > CHUNK_MAX_WORDS
    """
    if not all_chunks:
        return

    undersized: List[str] = []
    oversized: List[str] = []

    for c in all_chunks:
        if c.word_count < CHUNK_MIN_WORDS:
            undersized.append(f"{c.chunk_id}({c.word_count}w)")
        elif c.word_count > CHUNK_MAX_WORDS:
            oversized.append(f"{c.chunk_id}({c.word_count}w)")

    total = len(all_chunks)
    in_range = total - len(undersized) - len(oversized)
    pct_in_range = (in_range / total) * 100

    logger.info(
        "Chunk quality | total=%d in_range=%d (%.1f%%) "
        "undersized=%d oversized=%d",
        total,
        in_range,
        pct_in_range,
        len(undersized),
        len(oversized),
    )

    if undersized:
        logger.warning(
            "Undersized chunks (<%d words) | count=%d ids=%s",
            CHUNK_MIN_WORDS,
            len(undersized),
            ", ".join(undersized[:5]),  # cap log length
        )
    if oversized:
        logger.warning(
            "Oversized chunks (>%d words) | count=%d ids=%s",
            CHUNK_MAX_WORDS,
            len(oversized),
            ", ".join(oversized[:5]),
        )
