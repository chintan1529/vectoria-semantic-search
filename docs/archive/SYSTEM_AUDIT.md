# Vectoria System Audit

## Overview
This document provides a comprehensive architectural audit of Vectoria's frontend routes, backend services, SSE streaming events, provider layer, retrieval engine, evaluation suite, and analytics modules.

---

## 1. Frontend Routes & Components
| Route | Component | Purpose | Data Source | Status / Debt |
|---|---|---|---|---|
| `/` | `HeroMetrics`, `Landing` | Landing page platform showcase | `/api/analytics/eval-dashboard` | ✅ Real backend data wired. |
| `/query` | `QueryConsole`, `MetricsSidebar` | Real-time RAG query streaming | `/api/query` (SSE) | ✅ Uses live SSE events. Needs packet sequence validation. |
| `/research` | `ResearchConsole` | Multi-hop deep research mode | `/api/research` | ✅ Live execution. |
| `/evaluate` | `MetricsTable`, `BenchmarkHistory` | Retrieval performance dashboard | `/api/analytics/eval-dashboard` | ✅ Wired to real experiment logger. |
| `/lab` | `RetrievalLab` | Interactive index inspection & similarity tuning | `/api/query/inspect` | ✅ Functional inspect route. |
| `/showcase` | `ShowcaseGrid` | End-to-end capabilities demo | Static route / backend status | ✅ Clean. |

---

## 2. Backend Router Matrix
| Endpoint | Method | Service / Handler | Input | Output | Verification |
|---|---|---|---|---|---|
| `/api/query` | POST | `query_handler` / `streaming_orchestrator` | `QueryRequest` | SSE Stream (`RAGResponse`) | ✅ Live. Packet seq numbers being added. |
| `/api/research` | POST | `research_handler` | `ResearchRequest` | `ResearchResponse` | ✅ Live multi-stage agent. |
| `/api/query/inspect` | GET | `inspect_handler` | `chunk_id` | `ChunkMetadata` | ✅ Verified. |
| `/api/query/knowledge-graph` | POST | `kg_handler` | `entities` | `KnowledgeGraph` | ✅ Live extraction. |
| `/api/health` | GET | `health_handler` | None | `{status: ok}` | ✅ Verified. |
| `/api/ready` | GET | `readiness_handler` | None | `{status: ready, models_loaded: true}` | ✅ Readiness gate source. |
| `/api/analytics/platform-status` | GET | `analytics_handler` | None | `PlatformStatus` | ✅ Live CPU/Memory/Commit info. |
| `/api/analytics/eval-dashboard` | GET | `analytics_handler` | None | `EvalDashboardData` | ✅ Live experiment logger baselines. |

---

## 3. Provider Architecture & SDK Audit
- **Gemini Provider (`backend/providers/gemini_provider.py`)**: Uses `google.generativeai` (Deprecated). **Action Required**: Migrate to modern `google.genai` SDK.
- **Provider Factory (`backend/providers/provider_factory.py`)**: Dynamic dispatch for LLM providers (Gemini, Anthropic, HuggingFace). Clean & decoupled.
- **Fallback Router (`backend/providers/fallback_router.py`)**: Automatic provider failover tracking on API rate limits or connection timeouts.

---

## 4. Retrieval & Indexing Pipeline
- **Vector Index (`vectoria/storage.py`)**: FAISS FlatIP index + BM25 Lexical Index (`rank_bm25`). Fused via Reciprocal Rank Fusion (RRF).
- **Semantic Cache (`vectoria/retrieval/semantic_cache.py`)**: High-precision cache with similarity threshold $\ge 0.97$, matching intent classification, and $\ge 60\%$ chunk overlap requirement.
- **Reranker (`vectoria/reranking/reranker.py`)**: CrossEncoder CPU reranking. Introduces ~11s penalty on CPU. **Action Required**: Support adaptive candidate top_k tuning.

---

## 5. Technical Debt & Risk Matrix
1. **Deprecated SDK**: `google.generativeai` in `gemini_provider.py` should be replaced with `google.genai`.
2. **Critical Path Latency**: `streaming_orchestrator.py` previously executed KG extraction inline. Must be offloaded to an asynchronous background task.
3. **Stream Packet Loss Handling**: Frontend SSE client needs sequence number validation and auto-reconnect on dropped frames.
