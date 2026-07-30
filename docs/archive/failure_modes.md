# Vectoria Failure Mode Catalog

This document catalogs every known failure mode, its detection mechanism, and the prescribed recovery action.

---

## 1. Provider Failures

| Failure | Detection | Log Event | Recovery |
|---|---|---|---|
| HuggingFace network error | `getaddrinfo failed` in aiohttp | `FAILOVER_NETWORK_ERROR` | Auto-failover to Gemini |
| Gemini 429 Rate Limit | HTTP 429 in response | `FAILOVER_RATE_LIMIT` | Exponential backoff + failover |
| All providers exhausted | Both providers fail retry loop | `ALL_PROVIDERS_FAILED` | Return structured error via SSE `error` event |
| Provider timeout | No response within retry window | `PROVIDER_TIMEOUT` | Failover to next provider |

---

## 2. Retrieval Failures

| Failure | Detection | Log Event | Recovery |
|---|---|---|---|
| Zero results returned | `diagnostics.total_results == 0` | `RETRIEVAL_EMPTY` | Allow generation with warning; answer may lack grounding |
| Empty chunk text | `r.chunk.text` is empty string | `RETRIEVAL_INVALID_CHUNK` | Skip chunk in context; log error |
| FAISS index not loaded | `state.engine is None` | `STAGE_FAILED` | `require_ready()` blocks all queries; return 503 |
| Embedding model crash | Exception during `engine.search()` | `RETRIEVAL_EXCEPTION` | Return 504 timeout to client |

---

## 3. Empty Responses

| Failure | Detection | Log Event | Recovery |
|---|---|---|---|
| Zero tokens generated | `token_count < MIN_TOKEN_COUNT` | `GENERATION_INVALID` | Emit `generation_failed` SSE event; do NOT emit `done` |
| Answer below threshold | `len(answer) < MIN_ANSWER_LENGTH` | `GENERATION_INVALID` | Same as above |
| Provider returns empty | Provider `.generate()` returns empty text | `GENERATION_EMPTY` | Classify as generation failure |

---

## 4. Timeouts

| Failure | Detection | Log Event | Recovery |
|---|---|---|---|
| Retrieval timeout (90s) | `asyncio.TimeoutError` in retrieval | `STAGE_FAILED` | Return HTTP 504 to client |
| SSE connection timeout | Client disconnects before `done` | Detected by EventSourceResponse | Log `SSE_CLIENT_DISCONNECT` |
| Reranker timeout | Cross-encoder takes >30s | Embedded in retrieval timeout | Covered by 90s retrieval timeout |

---

## 5. SSE Breaks

| Failure | Detection | Log Event | Recovery |
|---|---|---|---|
| Connection dropped | Client TCP reset | `SSE_CLIENT_DISCONNECT` | Server-side cleanup; no retry |
| Event lost | Frontend detects gap in `event_sequence` | Frontend-side detection | Frontend requests reconnect |
| Heartbeat timeout | No heartbeat received in 30s | Frontend-side detection | Frontend reconnects or shows warning |

---

## 6. Rate Limits

| Failure | Detection | Log Event | Recovery |
|---|---|---|---|
| Client IP rate limited | `aiolimiter` check fails | `RATE_LIMIT_EXCEEDED` | Return HTTP 429 |
| Provider rate limited | 429 from Gemini/HF | `FAILOVER_RATE_LIMIT` | Auto-failover + exponential backoff |

---

## 7. Model Startup Failures

| Failure | Detection | Log Event | Recovery |
|---|---|---|---|
| Embedding model load fail | Exception during warmup | `STARTUP_FAILED` | `BootState.ERROR`; no traffic served |
| Reranker load fail | Exception during warmup search | `STARTUP_FAILED` | Same as above |
| Provider init fail | ProviderFactory returns None | `PROVIDER_FAILED` | `subsystems.provider = False`; degraded state |
| FAISS index missing | File not found during `engine.load()` | `STARTUP_FAILED` | System halts; must rebuild index |

---

## 8. Index Failures

| Failure | Detection | Log Event | Recovery |
|---|---|---|---|
| chunks.jsonl missing | FileNotFoundError on load | `STARTUP_FAILED` | Rebuild index: `python build_index.py` |
| mapping.json mismatch | Count mismatch between chunks and mapping | Integrity validator | Rebuild index |
| Embedding dimension mismatch | Shape error on FAISS search | Runtime exception | Regenerate embeddings |

---

## 9. Frontend Desynchronization

| Failure | Detection | Log Event | Recovery |
|---|---|---|---|
| Frontend queries before READY | `/api/ready` returns 503 | `SYSTEM_NOT_READY` | Frontend polls `/api/ready` before enabling input |
| Stale telemetry displayed | Telemetry values don't match request_id | Frontend-side validation | Clear telemetry on new request; validate request_id |
| State machine invalid transition | Frontend attempts impossible state change | Console warning | State machine enforces valid transitions only |

---

## Invariants (Must Never Occur)

1. ❌ Pipeline reports COMPLETE with empty answer → Prevented by `GENERATION_INVALID` guard
2. ❌ Pipeline reports RETRIEVAL SUCCESS with zero chunks → Prevented by `RETRIEVAL_EMPTY` warning
3. ❌ Pipeline reports GENERATION SUCCESS with zero tokens → Prevented by `MIN_TOKEN_COUNT` check
4. ❌ Frontend becomes interactive before backend READY → Prevented by `/api/ready` polling gate
5. ❌ Telemetry displays stale values → Prevented by `request_id` binding
6. ❌ SSE events silently disappear → Prevented by `event_sequence` counter
