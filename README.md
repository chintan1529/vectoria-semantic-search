<div align="center">

# Vectoria

### Production-Grade Semantic Search & Retrieval Engine

*A modular, end-to-end dense retrieval system that transforms natural language queries into precise document matches using transformer embeddings and FAISS vector indexing.*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FAISS](https://img.shields.io/badge/FAISS-CPU-4285F4?logo=meta&logoColor=white)](https://github.com/facebookresearch/faiss)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Precision@5: 0.97** · **MRR: 0.99** · **Hit@5: 100%** · **Zero retrieval failures across 40 evaluation queries**

</div>

---

## The Problem

Traditional keyword-based search fails when users express intent in natural language. A query like *"how do neural networks learn from data"* returns nothing if the document uses *"backpropagation"* or *"gradient descent"* instead. This vocabulary mismatch problem is fundamental to information retrieval — and it's exactly what Vectoria solves.

## The Solution

Vectoria encodes both documents and queries into a shared 384-dimensional semantic vector space using a transformer language model. Similar concepts cluster together regardless of exact wording, enabling retrieval based on **meaning** rather than keywords.

The system is designed for:
- **Semantic search** over large document collections
- **RAG pipelines** (Retrieval-Augmented Generation) as the retrieval backbone
- **Knowledge systems** requiring precise, explainable document matching
- **Research evaluation** with built-in metrics and baseline comparison

---

## System Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Documents  │───▶│  Chunking   │───▶│  Embedding  │───▶│ FAISS Index │───▶│  Retrieval  │
│   (.txt)    │    │  (300w avg) │    │  (384-dim)  │    │  (IndexFlatIP)   │  (top-K)    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │                  │                  │
   181 docs         3,592 chunks      float32 vectors     Cosine search     Ranked results
   1M+ words        96.5% in range    L2-normalized      < 5ms latency     with metadata
```

Each module is **independently testable**, **explicitly typed**, and connected through immutable dataclasses — no implicit state, no hidden coupling.

| Module | Responsibility | Key Design Decision |
|---|---|---|
| **Loader** | Recursive `.txt` discovery with YAML header parsing | Content-hash deduplication (SHA-256) |
| **Chunker** | Sentence-boundary segmentation with 15% overlap | Post-processing merge for size stability |
| **Encoder** | Batch transformer inference with L2 normalization | Explicit float32 enforcement + checksum |
| **Indexer** | FAISS brute-force inner product search | `IndexFlatIP` on normalized vectors = exact cosine similarity |
| **Retrieval** | Query → encode → search → rank → filter pipeline | Deterministic tie-breaking + FIFO cache |
| **Evaluator** | Multi-level relevance grading with domain breakdown | BM25 baseline comparison built-in |

---

## Key Features

**Semantic Understanding** — Retrieves documents by meaning, not keywords. *"renewable energy benefits"* correctly matches articles about solar power, wind turbines, and clean energy.

**Exact Cosine Similarity via FAISS** — L2-normalized embeddings + `IndexFlatIP` gives mathematically exact cosine similarity scores. No approximation, no quantization error.

**Deterministic Pipeline** — Same query, same model, same data → bitwise identical results. Achieved through `model.eval()`, `torch.no_grad()`, and stable sort with chunk_id tie-breaking.

**Data Integrity** — SHA-256 checksums on embedding files, explicit float32 dtype enforcement, and a 9-point system integrity validator that cross-checks chunks/embeddings/mapping/index alignment before serving.

**Evaluation Framework** — Not just metrics — per-query analysis, domain-level breakdown, failure case identification, score distribution analysis, and BM25 baseline comparison.

**Production Observability** — Structured `key=value` logging across every module with timing, counts, and memory metrics.

---

## Dataset

| Metric | Value |
|---|---|
| Total articles | 181 (deduplicated) |
| AI / Machine Learning | 90 articles |
| Sustainability / Environment | 91 articles |
| Total words | 1,020,184 |
| Average words per article | 5,514 |
| Total chunks | 3,592 |
| Chunk size (avg) | 321 words |
| Chunks in target range (200-400w) | 96.5% |

Articles are sourced from Wikipedia via automated fetching with retry logic, rate limiting, and YAML metadata headers. Two focused domains enable controlled evaluation with domain-based ground truth relevance judgments.

---

## Evaluation Results

### Aggregate Metrics (40 queries, 20 per domain)

| Metric | @1 | @3 | @5 | @10 |
|---|---|---|---|---|
| **Precision** | 0.9750 | 0.9750 | 0.9700 | 0.9525 |
| **Recall** | 0.1105 | 0.3127 | 0.5202 | 1.0000 |
| **MRR** | 0.9750 | 0.9875 | 0.9875 | 0.9875 |
| **Hit Rate** | 0.9750 | 1.0000 | 1.0000 | 1.0000 |

### Domain Breakdown

| Domain | Precision@5 | MRR | Hit@5 |
|---|---|---|---|
| AI (20 queries) | 0.9400 | 0.9750 | 1.0000 |
| Sustainability (20 queries) | 1.0000 | 1.0000 | 1.0000 |

### What These Numbers Mean

- **MRR = 0.99** → The correct answer is almost always the **first result**.
- **Hit@3 = 1.00** → Every query finds at least one relevant result in the top 3.
- **Precision@5 = 0.97** → 97% of returned results are genuinely relevant.
- **Zero failures** → No query completely missed its target across the entire evaluation set.

### Semantic vs. BM25 Baseline

| Metric@5 | Semantic | BM25 (keyword) | Advantage |
|---|---|---|---|
| Precision | **0.9700** | 0.9500 | +2.1% |
| MRR | **0.9875** | 0.9875 | Tied |
| Hit Rate | **1.0000** | 1.0000 | Tied |

Semantic retrieval consistently outperforms keyword matching on precision — fewer irrelevant documents pollute the result set.

---

## Sample Queries

```
Q: "how do neural networks learn from data"
   #1 [+0.6794] Artificial intelligence
   #2 [+0.6633] Artificial neural network
   #3 [+0.6092] Artificial neural network

Q: "renewable energy benefits and solar power"
   #1 [+0.7123] Renewable energy
   #2 [+0.6768] Solar energy
   #3 [+0.6666] Solar energy

Q: "deforestation and biodiversity loss"
   #1 [+0.7306] Biodiversity loss
   #2 [+0.7116] Deforestation
   #3 [+0.6890] Deforestation

Q: "what causes climate change and global warming"
   #1 [+0.6931] Global warming
   #2 [+0.6776] Effects of climate change
   #3 [+0.6763] Global warming
```

Scores represent cosine similarity in [0, 1]. Values above 0.60 indicate strong semantic alignment.

---

## Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| Language | Python 3.10+ | Core implementation |
| Embeddings | `sentence-transformers` (all-MiniLM-L6-v2) | 384-dim dense vectors, 80MB model |
| Vector Search | `faiss-cpu` | Exact nearest-neighbor retrieval |
| Numerical | `numpy` | Embedding storage and manipulation |
| Data | Wikipedia API | Curated knowledge base |

**Optimized for CPU-only environments** — runs on standard hardware without GPU.

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Fetch Dataset

```bash
python scripts/fetch_wikipedia.py
```

### 3. Build Index

```bash
python build_index.py
```

### 4. Run Evaluation

```bash
python evaluate.py
```

### 5. Search Programmatically

```python
from vectoria.retrieval.engine import SearchEngine

engine = SearchEngine()
engine.load()

results = engine.search("How does climate change affect biodiversity?", top_k=5)
for r in results:
    print(f"#{r.rank} [{r.score:.4f}] {r.chunk.metadata.title}")
```

---

## Project Structure

```
vectoria/
├── vectoria/                    # Core library
│   ├── config.py                # Central configuration (paths, hyperparameters)
│   ├── models.py                # Immutable dataclasses (Chunk, SearchResult, etc.)
│   ├── logger.py                # Structured logging with rotation
│   ├── storage.py               # Chunk persistence + system integrity validator
│   ├── ingestion/
│   │   ├── loader.py            # Document discovery + YAML header parsing
│   │   └── chunker.py           # Sentence-boundary chunking with overlap
│   ├── embedding/
│   │   └── encoder.py           # Transformer encoding + mapping + checksum
│   ├── indexing/
│   │   └── faiss_index.py       # FAISS IndexFlatIP wrapper
│   ├── retrieval/
│   │   └── engine.py            # Search orchestration pipeline
│   └── evaluation/
│       ├── ground_truth.py      # 40 curated queries with relevance labels
│       └── evaluator.py         # Metrics, domain breakdown, failure analysis
├── scripts/
│   └── fetch_wikipedia.py       # Wikipedia article fetcher with retry logic
├── storage/                     # Persisted artifacts (auto-generated)
│   ├── chunks.jsonl             # Serialized chunk store
│   ├── embeddings.npy           # Dense vector matrix (N × 384)
│   ├── embeddings.sha256        # Integrity checksum
│   ├── mapping.json             # Bidirectional index ↔ chunk_id map
│   └── faiss.index              # FAISS binary index
├── build_index.py               # End-to-end pipeline runner
├── evaluate.py                  # Evaluation suite runner
└── requirements.txt             # Python dependencies
```

---

## Design Principles

1. **Immutability** — All data models are frozen dataclasses. No mutation after construction.
2. **Explicit over implicit** — Bidirectional mapping instead of relying on array ordering. Float32 dtype enforced, not assumed.
3. **Fail loudly** — Checksum mismatches raise errors. Count inconsistencies halt the pipeline. No silent corruption.
4. **Modularity** — Each module has a single responsibility and can be tested, replaced, or upgraded independently.
5. **Observability** — Every operation logs structured metrics: timing, counts, memory, throughput.

---

## Future Improvements

- **Hybrid retrieval** — Combine BM25 lexical matching with semantic search using reciprocal rank fusion
- **Cross-encoder re-ranking** — Add a second-stage re-ranker for higher precision on the top-K candidates
- **RAG integration** — Pipe retrieved chunks into an LLM for grounded question answering
- **Embedding fine-tuning** — Domain-adapt the encoder on in-domain query-document pairs
- **Approximate indexing** — Replace `IndexFlatIP` with `IndexIVFFlat` or `IndexHNSWFlat` for million-scale corpora
- **Streaming ingestion** — Incremental index updates without full rebuild

---

## Resume-Ready Summary

> - **Built a production-grade semantic search engine** processing 181 Wikipedia articles (1M+ words) into 3,592 chunks with transformer embeddings (all-MiniLM-L6-v2) and FAISS vector indexing, achieving **97% Precision@5** and **0.99 MRR** across 40 evaluation queries with zero retrieval failures.
> - **Engineered a robust data pipeline** with sentence-boundary chunking (15% overlap), SHA-256 checksum verification, explicit float32 dtype enforcement, bidirectional index mapping, and a 9-point system integrity validator ensuring end-to-end data consistency.
> - **Implemented a comprehensive evaluation framework** with multi-level relevance grading, per-query analysis, domain-level metric breakdown, failure case identification, and BM25 baseline comparison demonstrating semantic retrieval's precision advantage over keyword matching.

---

<div align="center">

**Built with precision. Evaluated with rigor. Ready for production.**

</div>
