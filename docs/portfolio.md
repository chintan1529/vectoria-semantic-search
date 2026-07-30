# Vectoria — Portfolio Package

## Project Overview

**Vectoria** is a production-grade AI Intelligence Platform that solves the hallucination problem in Large Language Models through retrieval-augmented generation with deterministic citation verification.

Unlike standard RAG implementations, Vectoria implements a **Dual-Judge Trust Verification** architecture where every generated claim is independently verified against source documents by two isolated inference engines (Gemini + HuggingFace), with disagreement detection and conservative downgrading.

---

## Architecture Highlights

### System Design
- **Dual-Pass Retrieval**: FAISS vector search (L2 normalized, exact cosine similarity) followed by BAAI Cross-Encoder reranking
- **Provider Abstraction Layer**: Hot-swappable LLM providers with automatic failover, circuit breaker states, and retry logic
- **Dual-Judge Evaluation**: Primary (Gemini) and Secondary (HuggingFace) judges with consensus-based citation verification
- **Historical Regression Tracking**: Automated nDCG/Faithfulness regression alerts across benchmark runs
- **Full SSE Pipeline**: Real-time streaming with phase events, diagnostics, and provider failover visibility

### Key Metrics Achieved
| Metric | Value |
|---|---|
| Precision@5 | 0.9700 |
| MRR | 0.9875 |
| Hit Rate@3 | 1.0000 |
| Faithfulness (RAG vs Raw) | 0.94 vs 0.41 |
| Hallucination Rate (RAG) | 1.5% |
| Hallucination Rate (Raw LLM) | 100% |

---

## Feature Overview

| Feature | Description |
|---|---|
| **Semantic Search** | 384-dim transformer embeddings with FAISS exact nearest-neighbor retrieval |
| **Cross-Encoder Reranking** | BAAI/bge-reranker for precision-focused result ordering |
| **Grounded Generation** | Context-injected LLM generation with citation mapping |
| **Dual-Judge Verification** | Two-model consensus for hallucination detection |
| **Research Mode** | Multi-hop reasoning with extended context windows |
| **Knowledge Graph Visualization** | Real-time entity-relationship mapping from documents |
| **Trust Analysis** | Per-claim evidence strength and confidence scoring |
| **Executive Showcase** | Split-screen live comparison: Vectoria vs Raw LLM |
| **Benchmark Suite** | Golden dataset evaluation with competitive scoring |
| **Regression Tracking** | Automated alerts when quality metrics degrade |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Framer Motion |
| Backend | Python 3.11, FastAPI, SSE Streaming |
| Retrieval | FAISS, sentence-transformers, BAAI Cross-Encoder |
| LLM Providers | Gemini 2.5 Flash, HuggingFace Inference API |
| Evaluation | Custom dual-judge metrics engine |
| Deployment | Docker, Docker Compose |
| Observability | structlog, OpenTelemetry |

---

## Screenshots

> The `/showcase` route demonstrates a live split-screen comparison between Vectoria's grounded RAG pipeline and a raw zero-shot LLM, displaying real-time Faithfulness, Citation Accuracy, and Hallucination Risk metrics.

---

## Demo Script (5-Minute Walkthrough)

1. **Open the Query Console** (`/query`) — Ask: *"How do neural networks learn from data?"*
   - Show the streaming answer with inline citations
   - Point out the source chunks and confidence scores

2. **Open Research Mode** (`/research`) — Ask: *"Compare the environmental impact of solar vs wind energy"*
   - Demonstrate multi-hop reasoning across multiple documents
   - Show the extended context window and research-grade citations

3. **Open the Executive Showcase** (`/showcase`) — Run the demo query
   - Left panel: Full Vectoria pipeline (Retrieval → Reranking → Evidence → Verification → Answer)
   - Right panel: Raw LLM hallucinating without context
   - Highlight: 0.94 vs 0.41 Faithfulness, 1.5% vs 100% Hallucination Rate

4. **Open the Retrieval Lab** (`/lab`) — Search: *"deforestation and biodiversity loss"*
   - Show FAISS scores, reranker scores, and chunk metadata
   - Demonstrate the precision of semantic retrieval

5. **Mention the Benchmark Suite** — Show the generated scorecards in `data/evaluation/reports/`

---

## Resume Bullet Points

- **Built a production-grade RAG intelligence platform** processing 3,592 document chunks through a dual-pass FAISS + Cross-Encoder retrieval pipeline, achieving 0.97 Precision@5 and 0.99 MRR across 200 benchmark queries
- **Engineered a Dual-Judge Trust Verification system** using Gemini and HuggingFace as independent evaluators with consensus-based citation verification, reducing hallucination rates from 100% (raw LLM) to 1.5%
- **Designed a provider-agnostic LLM abstraction layer** with automatic failover, circuit breaker states (HEALTHY/DEGRADED/UNHEALTHY), retry logic, and real-time SSE streaming with provider failover visibility
- **Implemented a comprehensive evaluation framework** including Golden Dataset generation (200 questions), competitive benchmarking (4 configurations), historical regression tracking, and automated quality alerts
- **Containerized the full-stack platform** (Next.js + FastAPI + FAISS) with multi-stage Docker builds, persistent volume management, health monitoring, and deployment guides for Railway/Render/Fly.io

---

## Technical Interview Talking Points

### 1. "Tell me about a challenging system design decision"
> The Dual-Judge architecture. I needed to prevent the evaluation system from being biased by using the same model for both generation and verification. I split the verification across Gemini (Primary) and HuggingFace (Secondary), implemented disagreement detection, and when judges disagree, the system conservatively downgrades to the weaker assessment. This eliminates self-reinforcing hallucination loops.

### 2. "How do you handle reliability in distributed systems?"
> The Provider Abstraction Layer implements a full circuit breaker pattern. Each provider tracks its own health state (HEALTHY → DEGRADED → UNHEALTHY) with configurable retry counts and backoff. When a provider exhausts retries, the system automatically fails over to the next provider and emits real-time SSE events (`provider_failover_started`, `provider_failover_completed`) so the frontend can inform the user transparently.

### 3. "How do you measure quality?"
> I built a comprehensive benchmark pipeline. A Golden Dataset of 200 questions (120 LLM-generated, 80 deterministic/adversarial) is evaluated across 4 configurations (Vectoria RAG, Vectoria No-Retrieval, Raw Gemini, Raw HF). The system measures Recall@5, nDCG@5, MRR, Faithfulness, Citation Confidence, and Hallucination Rate. Every run is appended to a historical tracker that automatically alerts on regressions.

### 4. "What would you improve?"
> Latency. The Cross-Encoder reranking step currently runs on CPU and adds ~20 seconds per query. I'd migrate to GPU inference or implement a semantic cache layer (Redis) to serve repeated/similar queries from cache. I'd also move from the shared HuggingFace serverless endpoints to dedicated inference endpoints to resolve the 55% network failure rate.
