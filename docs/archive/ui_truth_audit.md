# UI Truth Audit

## 1. Landing Page
### `HeroMetrics` (`frontend/src/components/landing/hero-metrics.tsx`)
- **Purpose**: Displays high-level platform capabilities (Precision, MRR, Hit Rate).
- **Data Displayed**: 0.97 Precision, 0.99 MRR, 100% Hit Rate.
- **Status**: ❌ **MOCK**. Values are completely hardcoded.
- **Action Required**: Must be wired to fetch rolling averages from `backend/routes/analytics.py` (via `experiment_logger`).

## 2. Evaluation Dashboard
### `MetricsTable` (`frontend/src/components/eval/dashboard-components.tsx`)
- **Purpose**: Displays key retrieval metrics (Precision@5, Recall@5, MRR@5, Hit Rate@5).
- **Data Displayed**: 0.975, 1.0, 0.988, 100.
- **Status**: ❌ **MOCK**. Hardcoded in `metrics` array.
- **Action Required**: Wire to `experiment_logger` best/latest runs.

### `BaselineComparison` (`frontend/src/components/eval/dashboard-components.tsx`)
- **Purpose**: Compares BM25, Dense, and Hybrid pipelines.
- **Data Displayed**: Hardcoded rows of performance deltas.
- **Status**: ❌ **MOCK**.
- **Action Required**: Replace with real ablation study data or convert to an empty state until ablation benchmarks are natively supported via the analytics API.

### `RerankingStory` (`frontend/src/components/eval/dashboard-components.tsx`)
- **Purpose**: Visual explanation of pipeline filtering.
- **Data Displayed**: 3592 chunks -> 50 -> 50 -> 5.
- **Status**: ❌ **MOCK**.
- **Action Required**: Wire to actual chunk stats from corpus analytics.

### `LatencyProfile` (`frontend/src/components/eval/dashboard-components.tsx`)
- **Purpose**: Shows breakdown of latency by stage.
- **Data Displayed**: Fixed P50/P95 latencies for Embedding, FAISS, CrossEncoder.
- **Status**: ❌ **MOCK**.
- **Action Required**: Derive real latencies from `provider_analytics` and `query_intelligence`.

### `ScoreDistribution` (`frontend/src/components/eval/dashboard-components.tsx`)
- **Purpose**: Shows mean/min/max relevance scores.
- **Data Displayed**: Hardcoded standard deviations and scores.
- **Status**: ❌ **MOCK**.
- **Action Required**: Compute live from `experiment_logger` or remove if backend doesn't trace exact negative sampling.

## 3. Query Console
### `MetricsSidebar` (`frontend/src/components/query/metrics-sidebar.tsx`)
- **Purpose**: Real-time telemetry for the current query.
- **Data Displayed**: Total Latency, TTFT, Tokens, Rerank time, Faithfulness.
- **Status**: ✅ **REAL**. (Mostly)
- **Verification**: Data is correctly derived from the SSE `diagnostics` and `generationMeta` payloads emitted by `streaming_orchestrator.py`.
- **Action Required**: No hardcoded mocks found, but ensure null states are gracefully handled.

## Summary
The Evaluation Dashboard and Landing Page are currently static mockups. They must be entirely rewired to consume data from the new `/api/analytics/*` endpoints.
