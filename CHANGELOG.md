# Changelog

All notable changes to Vectoria will be documented in this file.

## [3.0.0] - 2026-07-24

### Added
- **Central Decision Engine (`vectoria/intelligence/decision_engine.py`)**: Single authority governing pipeline actions (`GENERATE`, `GENERATE_WITH_WARNING`, `CLARIFY`, `RE_RETRIEVE`, `REFUSE`, `ESCALATE`).
- **Evidence Sufficiency Engine (`evidence_sufficiency.py`)**: 0–100 Evidence Sufficiency Score evaluating similarity distribution, reranker confidence, and chunk coverage.
- **Answerability Classifier (`answerability.py`)**: Classifies query answerability prior to generation.
- **Query Understanding Pipeline (`query_understanding.py`)**: Extracts intent, domain, complexity, named entities, and output constraints.
- **Adaptive Query Budget (`query_budget.py`)**: Resource budget allocation based on query intent and complexity.
- **Contradiction Detection Engine (`contradiction_detector.py`)**: Identifies conflicting facts or timeline dates across retrieved chunks.
- **Claim-Level Grounding Engine (`claim_grounding.py`)**: Maps generated sentence claims to chunk evidence.
- **Confidence Calibration (`calibration.py`)**: Computes Expected Calibration Error (ECE).
- **Dynamic Prompt Builder (`dynamic_prompt_builder.py`)**: Modular prompt construction conditioned on intent, evidence quality, and detected contradictions.
- **Dataset Gap Detection (`failure_memory.py`)**: Automatically recommends corpus expansion based on recurring empty retrievals/refusals.
- **GitHub Actions CI Workflow**: Automated linting and pytest matrix.

### Changed
- Replaced `BAAI/bge-reranker-base` default reranker with lightweight `cross-encoder/ms-marco-MiniLM-L-6-v2` for sub-second CPU reranking (~120ms).
- Streamlined SSE pipeline to establish connection in 0ms and stream real-time stage progress (`classifying` $\rightarrow$ `retrieving` $\rightarrow$ `context` $\rightarrow$ `generating` $\rightarrow$ `tokens`).
- Consolidated documentation into 7 core evidence-based documents and archived historical reports into `docs/archive/`.
