# Vectoria Developer Guide

Welcome to the Vectoria Developer Guide. This document provides setup, architectural conventions, and development workflows for extending Vectoria's Adaptive AI Intelligence Platform.

---

## 1. System Requirements & Environment

- **Python**: 3.11+
- **Node.js**: 18+ / Next.js 16
- **Dependencies**: PyTorch, sentence-transformers, FAISS, FastAPI, pydantic v2

### Local Setup

1. **Clone & Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   cd frontend && npm install
   ```

2. **Environment Configuration**:
   Create a `.env` file in the root directory:
   ```env
   VECTORIA_CHAT_PROVIDER=gemini
   VECTORIA_RESEARCH_PROVIDER=gemini
   VECTORIA_FALLBACK_PROVIDER=huggingface
   VECTORIA_GEMINI_API_KEY=your_gemini_api_key
   ```

3. **Run Platform Locally**:
   ```bash
   cd frontend && npm run dev
   ```

---

## 2. Intelligence Subsystem Architecture

Vectoria decouples decision logic from orchestrators:

- **`DecisionEngine` (`vectoria/intelligence/decision_engine.py`)**: Central decision authority evaluating evidence sufficiency, answerability, and query budget.
- **`EvidenceSufficiencyEngine` (`vectoria/intelligence/evidence_sufficiency.py`)**: Computes 0–100 Evidence Sufficiency Score.
- **`AnswerabilityClassifier` (`vectoria/intelligence/answerability.py`)**: Classifies query answerability categories.
- **`ClaimGroundingEngine` (`vectoria/intelligence/claim_grounding.py`)**: Maps claim statements to supporting chunk evidence.

---

## 3. Testing & Verification

Run the comprehensive unit test suite:
```bash
pytest tests/
```
