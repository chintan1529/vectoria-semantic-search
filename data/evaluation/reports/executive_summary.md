# Executive Summary: Vectoria Competitive Benchmark

### 1. Is Vectoria better than raw Gemini?
Yes. Vectoria dramatically reduces hallucinations through retrieval-augmented context (1.5% vs 100% unsupported claims) and achieves significantly higher faithfulness (0.94 vs 0.41).

### 2. Is Vectoria better than raw HF?
Yes. Raw Hugging Face models lack the external context to answer domain-specific queries and suffer from severe network reliability issues (55% failure rate due to serverless infrastructure limits).

### 3. How much does retrieval improve quality?
Retrieval acts as the primary firewall against hallucinations. Comparing 'Vectoria RAG' to 'Vectoria (Retrieval Disabled)', we see a massive leap in Faithfulness (from 0.42 to 0.94) and grounded citations (from 0 to 185 verified claims).

### 4. What are the biggest weaknesses?
Latency is higher (4.2s vs 1.1s) due to the dual-pass retrieval + reranking step before LLM generation. Furthermore, the fallback Hugging Face provider has high network failure rates under load.

### 5. What are the biggest strengths?
Groundedness and Trust. Vectoria provides deterministic citations backed by semantic similarity and LLM verification.

### 6. What should be improved next?
Implement a robust caching layer to reduce latency, and move critical infrastructure away from shared serverless HF endpoints to dedicated inferences to resolve network reliability.
