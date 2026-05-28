/**
 * Types mirroring the Python backend dataclasses
 */

export interface DocumentMeta {
  doc_id: string;
  source: string;
  title: string;
  category: "ai" | "sustainability";
  timestamp?: string;
}

export interface Chunk {
  chunk_id: string;
  doc_id: string;
  text: string;
  metadata: DocumentMeta;
  chunk_index: number;
  word_count: number;
}

export interface SearchResult {
  chunk: Chunk;
  score: number;
  rank: number;
}

export interface RAGResponse {
  answer: string;
  citations: Record<string, SearchResult>;
  context_stats: {
    num_chunks: number;
    total_characters: number;
    average_score: number;
    unique_sources: number;
  };
  latency_ms: number;
  retrieval_latency_ms: number;
  rerank_latency_ms: number;
  generation_latency_ms: number;
  model_name: string;
  refused: boolean;
  refusal_reason: string | null;
  generation_meta: {
    model_used: string;
    generation_latency_ms: number;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    finish_reason: string;
    prompt_version: string;
    retrieved_chunk_ids: string[];
    citation_count: number;
  };
  num_retrieved: number;
  
  // Array of all chunks for the inspector panel
  retrieved_results: SearchResult[];
}

export type ErrorReason =
  | "insufficient_context"
  | "safety_block"
  | "generation_failure"
  | "timeout"
  | "provider_error"
  | "network_error"
  | "api_unavailable";
