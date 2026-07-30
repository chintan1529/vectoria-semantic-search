# Frontend Truth Report

## Overview
This report confirms that all mock data, synthetic telemetry, hardcoded statistics, and simulated progress indicators have been systematically eradicated from the Vectoria frontend application. The entire UI now strictly displays only verifiable runtime metrics and benchmark history produced by backend services.

---

## Component Truth Audit

### 1. Landing Page (`HeroMetrics`)
- **Location**: `frontend/src/components/landing/hero-metrics.tsx`
- **Purpose**: Displays top-level system quality indicators (nDCG@5, MRR@5, Recall@5).
- **Data Source**: Live `/api/analytics/eval-dashboard` endpoint (derived from `experiment_logger` rolling averages).
- **Verification Status**: ✅ Verified. Zero hardcoded percentages or metrics remain.
- **Fallback / Empty State**: Displays a clean "Platform Live - Waiting for telemetry..." state when backend has no benchmark runs.

### 2. Evaluation Dashboard (`MetricsTable`, `BenchmarkHistory`, `LatencyProfile`)
- **Location**: `frontend/src/components/eval/dashboard-components.tsx`
- **Purpose**: Displays system performance metrics, historical benchmark trends, and latency breakdown by stage.
- **Data Source**: Live `/api/analytics/eval-dashboard` and `/api/analytics/platform-status`.
- **Verification Status**: ✅ Verified. All static rows (BM25 vs Dense vs Hybrid mock tables, fake reranking stories, and fake domain breakdowns) have been removed.
- **Fallback / Empty State**: Renders an explicit `EmptyState` component when no benchmark data exists.

### 3. Query Console (`MetricsSidebar`)
- **Location**: `frontend/src/components/query/metrics-sidebar.tsx`
- **Purpose**: Real-time diagnostic telemetry for active RAG queries.
- **Data Source**: Backend Server-Sent Events (SSE) `diagnostics` and `generationMeta` payloads.
- **Verification Status**: ✅ Verified. Strictly consumes streaming telemetry emitted by `streaming_orchestrator.py`.

### 4. API Client (`VectoriaAPIClient`)
- **Location**: `frontend/src/lib/api/client.ts`
- **Purpose**: Typed fetch client for backend endpoints.
- **Verification Status**: ✅ Verified. All `MOCK_RESPONSE` generators and mock fallbacks have been purged. Handles offline/unreachable backend state gracefully by returning `null` rather than throwing uncaught errors.

---

## Conclusion
Vectoria's UI now satisfies the Golden Principle: Every displayed value is produced by the backend, derived from runtime telemetry or benchmark history, traceable, and reproducible.
