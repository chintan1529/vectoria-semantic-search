# Vectoria Platform Architecture

Vectoria is a mature, dual-judge RAG intelligence platform designed to eliminate LLM hallucinations through semantic retrieval, deterministic citation mapping, and rigorous evaluation architectures.

## System Architecture

```mermaid
graph TD
    A[Frontend /showcase] --> B[API Gateway]
    B --> C{Orchestrator}
    C --> D[Search Engine]
    C --> E[Provider Factory]
    D --> F[(FAISS Index)]
    D --> G[(Chunk Storage)]
    E --> H[Primary Judge: Gemini]
    E --> I[Secondary Judge: HuggingFace]
```

## Retrieval & Reranking Flow

```mermaid
sequenceDiagram
    participant User
    participant Engine
    participant FAISS
    participant Reranker
    
    User->>Engine: Query
    Engine->>FAISS: Search Top 50 (L2 Distance)
    FAISS-->>Engine: 50 Chunks
    Engine->>Reranker: Cross-Encode (Query, 50 Chunks)
    Reranker-->>Engine: Reordered Top 5
    Engine-->>User: Highly Relevant Context
```

## Dual-Judge Trust Verification Architecture

The evaluation pipeline guarantees answer faithfulness by splitting the validation step between two isolated inference engines.

```mermaid
graph LR
    A[Claim Extracted] --> B[Lexical Chunk Match]
    B --> C[LLM Verification Prompt]
    C --> D[Primary: Gemini]
    C --> E[Secondary: HuggingFace]
    D --> F{Disagreement Detection}
    E --> F
    F -->|Consensus Verified| G[Verified]
    F -->|Divergence| H[Downgrade to WEAK]
    F -->|Consensus Unsupported| I[Unsupported]
```

## Provider Failover Architecture

```mermaid
stateDiagram-v2
    [*] --> Primary_HuggingFace
    Primary_HuggingFace --> Fallback_Gemini: Network Error (getaddrinfo)
    Primary_HuggingFace --> Fallback_Gemini: Rate Limit (429)
    Fallback_Gemini --> [*]: Success
    Fallback_Gemini --> Exhausted: 429 Quota
    Exhausted --> [*]: System Failure Alert
```
