# Vectoria Evaluation & Research Methodology

This document details the evaluation frameworks, statistical metrics, confidence calibration, and benchmark methodologies used across Vectoria's Adaptive AI Intelligence Platform.

---

## 1. Primary Metrics

Beyond standard retrieval metrics (Recall@K, MRR, nDCG), Vectoria evaluates decision intelligence and research credibility:

| Metric | Target / Benchmark | Description |
| :--- | :--- | :--- |
| **Evidence Sufficiency Score** | $\ge 90.0$ for confident generation | 0–100 score derived from similarity distribution & chunk coverage |
| **Expected Calibration Error (ECE)** | $< 0.08$ | Measures alignment between predicted confidence and factual correctness |
| **Answerability Accuracy** | $> 95\%$ | Classification precision across answerable vs unanswerable queries |
| **Claim Grounding Coverage** | $> 90\%$ | Percentage of generated claims supported by chunk evidence |
| **Refusal Precision** | $100\%$ | Zero hallucinations on out-of-corpus queries |

---

## 2. Statistical Rigor & Bootstrap Sampling

Vectoria applies 95% bootstrap confidence intervals across benchmark iterations:

$$\text{ECE} = \sum_{b=1}^B \frac{|B_b|}{N} \left| \text{acc}(B_b) - \text{conf}(B_b) \right|$$

Bootstrap resampling ($B = 1000$ iterations) is used to calculate standard error and confidence intervals for Recall@5, MRR, and ECE score distributions.

---

## 3. Failure Taxonomy & Dataset Gap Analysis

Vectoria categorizes system failures into a structured taxonomy:
1. **Empty Retrieval**: Query yields 0 matching vectors in FAISS.
2. **Low Evidence Sufficiency**: Candidate chunks do not cover query terms.
3. **Contradictory Context**: Conflicting facts or timeline dates across retrieved documents.
4. **Unsupported Claims**: Sentence generated without chunk evidence citation.

Recurring failure patterns automatically generate dataset expansion recommendations in `FailureMemory`.
