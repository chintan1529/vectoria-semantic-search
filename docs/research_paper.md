# Vectoria: Dual-Judge Retrieval-Augmented Generation for Trustworthy AI Systems

## Abstract

Large Language Models (LLMs) generate fluent, confident responses but suffer from hallucination — producing statements unsupported by evidence. This paper presents **Vectoria**, a retrieval-augmented generation (RAG) platform that reduces hallucination rates from 100% (raw LLM) to 1.5% through a novel Dual-Judge Trust Verification architecture. Vectoria combines FAISS-based dense retrieval with BAAI Cross-Encoder reranking, followed by independent citation verification by two isolated inference engines. We evaluate Vectoria against raw Gemini 2.5 Flash and raw HuggingFace models on a Golden Dataset of 200 benchmark questions, demonstrating a 2.3x improvement in faithfulness (0.94 vs 0.41) and near-zero hallucination rates on domain-specific queries.

---

## 1. Introduction

The deployment of LLMs in production systems requires guarantees about factual accuracy. Standard approaches — prompt engineering, fine-tuning, and retrieval-augmented generation — reduce but do not eliminate hallucination. The core problem is that generation and verification use the same model, creating self-reinforcing confidence loops.

Vectoria addresses this by separating the roles of **generator**, **retriever**, and **verifier** into independent subsystems, with verification split across two distinct model architectures (Gemini and HuggingFace) to prevent single-model bias.

---

## 2. Methodology

### 2.1 Dual-Pass Retrieval

Documents are chunked at sentence boundaries (avg. 321 words, 15% overlap) and encoded into 384-dimensional vectors using `all-MiniLM-L6-v2`. FAISS `IndexFlatIP` performs exact cosine similarity search over L2-normalized embeddings, returning 50 candidate chunks. A BAAI Cross-Encoder (`bge-reranker-base`) reranks the candidates, selecting the top 5 for context injection.

### 2.2 Grounded Generation

The retrieved context is prepended to the user query and sent to the primary LLM provider (Gemini 2.5 Flash). The model is instructed to generate answers grounded exclusively in the provided context, with explicit source references.

### 2.3 Dual-Judge Trust Verification

Each claim in the generated answer is independently verified:
1. **Claim Extraction**: The answer is segmented into individual factual claims.
2. **Lexical Matching**: Each claim is matched to its most relevant source chunk via word overlap.
3. **Primary Verification (Gemini)**: The primary judge evaluates whether the source fully supports the claim.
4. **Secondary Verification (HuggingFace)**: An independent secondary judge performs the same evaluation.
5. **Consensus Resolution**: If judges agree, the consensus verdict stands. If they disagree, the system conservatively downgrades to the weaker assessment.

### 2.4 Provider Failover

The system implements a circuit breaker pattern with health states (HEALTHY → DEGRADED → UNHEALTHY). Network failures, rate limits (HTTP 429), and timeouts are tracked independently from answer quality metrics to prevent conflation of infrastructure reliability with model capability.

---

## 3. Evaluation

### 3.1 Dataset

A Golden Dataset of 200 questions was constructed:
- **120 LLM-generated**: Multi-hop, comparison, and analytical questions synthesized from document chunk contexts
- **80 Deterministic/Adversarial**: Edge cases, exact keyword matches, contradictions, and false assumptions

### 3.2 Configurations Tested

| Configuration | Retrieval | LLM | Judge |
|---|---|---|---|
| Vectoria RAG | FAISS + Reranker | Gemini 2.5 Flash | Dual (Gemini + HF) |
| Vectoria (No Retrieval) | None | Gemini 2.5 Flash | Single |
| Raw Gemini | None | Gemini 2.5 Flash | None |
| Raw HuggingFace | None | Qwen-7B-Instruct | None |

### 3.3 Results

| Metric | Vectoria RAG | Raw Gemini | Raw HF |
|---|---|---|---|
| Faithfulness | **0.94** | 0.41 | 0.18 |
| Hallucination Rate | **1.5%** | 100% | 100% |
| Citation Accuracy | **92.5%** | 0% | 0% |
| Recall@5 | **0.895** | N/A | N/A |
| nDCG@5 | **0.824** | N/A | N/A |
| MRR | **0.765** | N/A | N/A |

---

## 4. Limitations

1. **Latency**: The dual-pass retrieval + reranking pipeline adds ~4 seconds per query on CPU hardware. Cross-Encoder reranking is the primary bottleneck (~20s for top-50 reranking on CPU).
2. **Provider Dependency**: The platform relies on external API providers. Network failures on HuggingFace serverless endpoints resulted in a 55% failure rate during stress testing.
3. **Corpus-Bounded**: Vectoria's quality is bounded by the indexed corpus. Questions outside the corpus scope fall back to raw LLM behavior.
4. **Single Embedding Model**: The system uses a single 384-dim model. Larger models (768-dim or 1024-dim) may improve retrieval quality at the cost of memory and latency.

---

## 5. Future Work

1. **Semantic Caching**: Implement Redis-based caching for repeated/similar queries to reduce latency by 80%+ for cache hits.
2. **GPU Acceleration**: Migrate Cross-Encoder reranking and embedding inference to CUDA-enabled hardware.
3. **Agentic RAG**: Introduce specialized agents (Researcher, Critic, Synthesizer) that chain retrieval contexts across multiple reasoning steps.
4. **Adaptive Retrieval**: Dynamically adjust `top_k` and reranking depth based on query complexity classification.
5. **Multi-Modal**: Extend the pipeline to support image and table retrieval alongside text.

---

## 6. Conclusion

Vectoria demonstrates that retrieval-augmented generation, combined with dual-model verification, can reduce LLM hallucination rates to near-zero on domain-specific queries. The key insight is that **verification must be independent of generation** — using the same model for both creates unfalsifiable confidence loops. By splitting verification across two architecturally distinct models and conservatively resolving disagreements, Vectoria achieves production-grade trustworthiness suitable for deployment in knowledge-critical applications.
