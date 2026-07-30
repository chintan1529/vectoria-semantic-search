/**
 * Vectoria SSE Streaming Contract — v3.0.0
 * 
 * Shared Protocol Contract between Backend & Frontend.
 * Defines payload schemas, required fields, and runtime validation.
 */

export interface BaseSSEEventPayload {
  request_id?: string;
  seq?: number;
  event_sequence?: number;
  timestamp?: number;
  provider?: string;
  stage?: string;
}

export interface SSEPhasePayload extends BaseSSEEventPayload {
  phase: "classifying" | "retrieving" | "validating" | "reranking" | "building_context" | "generating" | "verifying" | "evaluating";
  status: "active" | "complete" | "failed";
  action?: string;
  latency_ms?: number;
}

export interface SSEChunkItem {
  id: string;
  title: string;
  score: number;
  text: string;
}

export interface SSEContextPayload extends BaseSSEEventPayload {
  chunks: SSEChunkItem[];
}

export interface SSEDiagnosticsPayload extends BaseSSEEventPayload {
  classification_latency_ms?: number;
  retrieval_latency_ms?: number;
  reranking_latency_ms?: number;
  total_results?: number;
  original_query?: string;
  rewritten_query?: string;
  query_type?: string;
}

export interface SSEReasoningTracePayload extends BaseSSEEventPayload {
  decision?: string;
  action?: string;
  confidence?: number;
  reasoning_steps?: string[];
  refusal_reason?: string;
  clarification_prompt?: string;
}

export interface SSETokenPayload extends BaseSSEEventPayload {
  text: string;
}

export interface SSEDonePayload extends BaseSSEEventPayload {
  generation_latency_ms?: number;
  token_count?: number;
  answer_length?: number;
  action?: string;
}

export interface SSETrustVerificationPayload extends BaseSSEEventPayload {
  claims?: Array<{ claim: string; confidence: string }>;
  citations?: Array<{ chunk_id: string; status: string; reason?: string }>;
  composite_faithfulness_score?: number;
  evidence_coverage_score?: number;
  mode?: string;
}

export interface SSEErrorPayload extends BaseSSEEventPayload {
  message?: string;
  reason?: string;
  error?: string;
}

export interface ValidationResult<T = any> {
  valid: boolean;
  data: T;
  errors: string[];
}

/**
 * Runtime validation for incoming SSE payloads.
 * Prevents malformed backend data from crashing React render trees.
 */
export function validateSSEPayload(eventType: string, rawData: any): ValidationResult {
  const errors: string[] = [];

  if (rawData === null || rawData === undefined) {
    return { valid: false, data: {}, errors: ["Payload is null or undefined"] };
  }

  let parsed = rawData;
  if (typeof rawData === "string") {
    try {
      parsed = JSON.parse(rawData);
    } catch (e) {
      // If it's a raw string token
      if (eventType === "token") {
        return { valid: true, data: { text: rawData }, errors: [] };
      }
      return { valid: false, data: { text: rawData }, errors: ["Failed to parse JSON string"] };
    }
  }

  if (typeof parsed !== "object") {
    if (eventType === "token") {
      return { valid: true, data: { text: String(parsed) }, errors: [] };
    }
    return { valid: false, data: parsed, errors: ["Payload is not an object"] };
  }

  // Event specific schema validation
  switch (eventType) {
    case "phase":
      if (!parsed.phase) errors.push("Missing required field 'phase'");
      break;

    case "context":
      if (!parsed.chunks && !Array.isArray(parsed)) {
        errors.push("Missing 'chunks' array in context payload");
      }
      break;

    case "token":
      if (typeof parsed.text !== "string" && typeof parsed !== "string") {
        errors.push("Token payload missing 'text' property");
      }
      break;

    case "diagnostics":
      if (parsed.retrieval_latency_ms !== undefined && typeof parsed.retrieval_latency_ms !== "number") {
        errors.push("Invalid type for retrieval_latency_ms");
      }
      break;

    case "done":
      // Valid complete payload
      break;

    case "trust_verification":
      break;

    default:
      // Unknown event logger trigger
      break;
  }

  return {
    valid: errors.length === 0,
    data: parsed,
    errors,
  };
}
