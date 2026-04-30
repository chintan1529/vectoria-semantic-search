"""
Vectoria Data Models — Type-safe data structures for the entire pipeline.

All data flowing between modules uses these dataclasses.  This ensures
a consistent contract across ingestion, embedding, indexing, and retrieval
without coupling the modules to each other's internals.

Design decisions:
    - Plain dataclasses (no Pydantic) to avoid extra dependencies.
    - DocumentMeta stores provenance so every chunk traces back to its source.
    - Chunk.chunk_id uses "{doc_id}_chunk_{index}" for deterministic,
      human-readable identification.
    - SearchResult carries the full Chunk (not just an id) so consumers
      never need a second lookup.
    - EvalResult holds per-query and aggregate metrics for the evaluation layer.
    - to_dict / from_dict methods enable JSONL serialization without pickle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass(frozen=True)
class DocumentMeta:
    """Provenance metadata for a source document.

    Attributes:
        doc_id:    Deterministic identifier (SHA-256 prefix of content).
        source:    Original file path or URI.
        title:     Human-readable title (derived from filename).
        category:  Domain category (e.g., "ai", "sustainability").
        timestamp: ISO-8601 ingestion timestamp.
    """

    doc_id: str
    source: str
    title: str
    category: str
    timestamp: str

    # ── Serialization ────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentMeta:
        """Reconstruct from a dictionary."""
        return cls(**data)


@dataclass(frozen=True)
class Chunk:
    """A text segment produced by the chunking pipeline.

    Attributes:
        chunk_id:    Deterministic id in the form "{doc_id}_chunk_{index}".
        doc_id:      Parent document reference.
        text:        The chunk's text content.
        metadata:    Full provenance metadata of the source document.
        chunk_index: Zero-based position of this chunk within its document.
        word_count:  Number of words in *text* (cached for validation).
    """

    chunk_id: str
    doc_id: str
    text: str
    metadata: DocumentMeta
    chunk_index: int
    word_count: int = 0

    def __post_init__(self) -> None:
        # frozen=True requires object.__setattr__ for computed fields
        if self.word_count == 0:
            object.__setattr__(self, "word_count", len(self.text.split()))

    # ── Serialization ────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Chunk:
        """Reconstruct from a dictionary (e.g., loaded from JSONL)."""
        fields = dict(data)  # shallow copy to avoid mutating caller's dict
        fields["metadata"] = DocumentMeta.from_dict(fields["metadata"])
        return cls(**fields)


@dataclass
class SearchResult:
    """A single retrieval result returned to the caller.

    Attributes:
        chunk: The matched chunk with full text and metadata.
        score: Cosine similarity score in [0, 1].
        rank:  1-indexed position in the result list.
    """

    chunk: Chunk
    score: float
    rank: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "chunk": self.chunk.to_dict(),
            "score": round(self.score, 6),
            "rank": self.rank,
        }


@dataclass
class EvalResult:
    """Evaluation metrics for a single query or aggregated across queries.

    Attributes:
        query:        The evaluation query string.
        precision_at_k: Fraction of top-K results that are relevant.
        recall_at_k:    Fraction of all relevant docs found in top-K.
        reciprocal_rank: 1 / rank of the first relevant result (0 if none).
        k:              The K value used for evaluation.
        relevant_retrieved: Count of relevant results in top-K.
        total_relevant:     Total relevant documents in the corpus.
    """

    query: str
    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float
    k: int
    relevant_retrieved: int = 0
    total_relevant: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class EvalReport:
    """Aggregated evaluation report across multiple queries.

    Attributes:
        per_query:       Individual EvalResult for each query.
        mean_precision:  Mean Precision@K across all queries.
        mean_recall:     Mean Recall@K across all queries.
        mean_mrr:        Mean Reciprocal Rank across all queries.
        k:               The K value used.
        num_queries:     Number of queries evaluated.
    """

    per_query: list[EvalResult] = field(default_factory=list)
    mean_precision: float = 0.0
    mean_recall: float = 0.0
    mean_mrr: float = 0.0
    k: int = 5
    num_queries: int = 0

    def summary(self) -> str:
        """Return a human-readable summary string."""
        lines = [
            f"{'─' * 50}",
            f"  Evaluation Report  (K={self.k}, Queries={self.num_queries})",
            f"{'─' * 50}",
            f"  Mean Precision@{self.k}: {self.mean_precision:.4f}",
            f"  Mean Recall@{self.k}:    {self.mean_recall:.4f}",
            f"  Mean MRR:             {self.mean_mrr:.4f}",
            f"{'─' * 50}",
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "mean_precision": round(self.mean_precision, 6),
            "mean_recall": round(self.mean_recall, 6),
            "mean_mrr": round(self.mean_mrr, 6),
            "k": self.k,
            "num_queries": self.num_queries,
            "per_query": [r.to_dict() for r in self.per_query],
        }
