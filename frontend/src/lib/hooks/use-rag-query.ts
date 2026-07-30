"use client";

import { useState, useCallback, useRef } from "react";
import { QueryPhase } from "@/components/query/pipeline-visualizer";
import { validateSSEPayload } from "@/lib/api/sse-contract";

export interface RAGQueryState {
  phase: QueryPhase;
  query: string | null;
  streamingText: string;
  diagnostics: any | null;
  context: any | null;
  generationMeta: any | null;
  evaluationMetrics: any | null;
  trustVerification: any | null;
  error: string | null;
  startTime: number | null;
  firstTokenTime: number | null;
  tokenCount: number;
}

/**
 * Token buffering strategy: accumulate tokens and flush to React state
 * in batches to reduce re-renders. Flushes every FLUSH_INTERVAL_MS or
 * when FLUSH_TOKEN_THRESHOLD tokens accumulate, whichever comes first.
 */
const FLUSH_INTERVAL_MS = 40;
const FLUSH_TOKEN_THRESHOLD = 4;

/** Maximum time to wait for a response before aborting (ms) */
const QUERY_TIMEOUT_MS = 90_000;

/** Backend readiness check URL */
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useRAGQuery() {
  const [state, setState] = useState<RAGQueryState>({
    phase: "idle",
    query: null,
    streamingText: "",
    diagnostics: null,
    context: null,
    generationMeta: null,
    evaluationMetrics: null,
    trustVerification: null,
    error: null,
    startTime: null,
    firstTokenTime: null,
    tokenCount: 0,
  });

  // Token buffer refs (not in state to avoid extra re-renders)
  const tokenBuffer = useRef<string>("");
  const tokenCountRef = useRef<number>(0);
  const flushTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const firstTokenRecorded = useRef(false);
  // AbortController for cancelling in-flight requests
  const abortControllerRef = useRef<AbortController | null>(null);

  const flushTokenBuffer = useCallback(() => {
    if (flushTimer.current) {
      clearTimeout(flushTimer.current);
      flushTimer.current = null;
    }

    const buffered = tokenBuffer.current;
    if (!buffered) return;
    tokenBuffer.current = "";

    setState(s => ({
      ...s,
      streamingText: s.streamingText + buffered,
      tokenCount: tokenCountRef.current,
    }));
  }, []);

  const appendToken = useCallback((token: string) => {
    tokenBuffer.current += token;
    tokenCountRef.current += 1;

    // Record first token time
    if (!firstTokenRecorded.current) {
      firstTokenRecorded.current = true;
      setState(s => ({ ...s, firstTokenTime: Date.now() }));
    }

    // Flush if threshold reached
    if (tokenCountRef.current % FLUSH_TOKEN_THRESHOLD === 0) {
      flushTokenBuffer();
      return;
    }

    // Otherwise schedule a flush
    if (!flushTimer.current) {
      flushTimer.current = setTimeout(flushTokenBuffer, FLUSH_INTERVAL_MS);
    }
  }, [flushTokenBuffer]);

  // Telemetry integrity refs
  const currentRequestId = useRef<string | null>(null);
  const expectedEventSeq = useRef<number>(0);

  const submitQuery = useCallback(async (text: string) => {
    // --- Abort any in-flight request ---
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    // Timeout: abort after QUERY_TIMEOUT_MS
    const timeoutId = setTimeout(() => controller.abort(), QUERY_TIMEOUT_MS);

    const startTime = Date.now();
    tokenBuffer.current = "";
    tokenCountRef.current = 0;
    firstTokenRecorded.current = false;
    currentRequestId.current = null;
    expectedEventSeq.current = 0;

    setState({
      phase: "classifying", // Strict starting state
      query: text,
      streamingText: "",
      diagnostics: null,
      context: null,
      generationMeta: null,
      evaluationMetrics: null,
      trustVerification: null,
      error: null,
      startTime,
      firstTokenTime: null,
      tokenCount: 0,
    });

    try {
      // --- Pre-flight readiness gate ---
      try {
        const healthRes = await fetch(`${BACKEND_URL}/api/ready`, {
          signal: controller.signal,
        });
        if (!healthRes.ok) {
          const errData = await healthRes.json().catch(() => ({}));
          setState(s => ({
            ...s,
            phase: "error",
            error: errData.message || "System is still warming up. Models are loading. Please wait a moment and try again.",
          }));
          clearTimeout(timeoutId);
          return;
        }
      } catch (healthErr: any) {
        if (healthErr.name === "AbortError") throw healthErr;
        setState(s => ({
          ...s,
          phase: "error",
          error: "Backend is offline or unreachable. Please ensure the server is running.",
        }));
        clearTimeout(timeoutId);
        return;
      }

      setState(s => ({ ...s, phase: "connecting" }));

      const res = await fetch(`${BACKEND_URL}/api/query/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: text }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText || `Server error: ${res.status}`);
      }

      // Capture request ID from headers
      const requestIdHeader = res.headers.get("X-Request-ID");
      if (requestIdHeader) {
        currentRequestId.current = requestIdHeader;
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No reader available");
      const decoder = new TextDecoder();

      let buffer = "";

      // Resilient state machine transition map
      const validTransitions: Record<string, QueryPhase[]> = {
        idle: ["connecting", "classifying", "error"],
        connecting: ["classifying", "retrieving", "error"],
        classifying: ["retrieving", "validating", "reranking", "generating", "error"],
        embedding: ["retrieving", "validating", "reranking", "generating", "error"],
        retrieving: ["validating", "reranking", "building_context", "generating", "verifying", "error"],
        validating: ["reranking", "building_context", "generating", "verifying", "error"],
        reranking: ["building_context", "generating", "verifying", "error"],
        building_context: ["generating", "verifying", "error"],
        generating: ["verifying", "evaluating", "complete", "error"],
        verifying: ["evaluating", "complete", "error"],
        evaluating: ["complete", "error"],
        complete: ["connecting", "classifying", "idle"],
        error: ["connecting", "classifying", "idle"],
      };

      const isDebug = process.env.NEXT_PUBLIC_DEBUG_STREAMING === "true" || (typeof window !== "undefined" && (window as any).__VECTORIA_DEBUG_STREAMING);

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Normalize \r\n to \n — sse-starlette uses \r\n line endings,
        // but the original parser split on \n\n which never matches \r\n\r\n.
        // This was the root cause of the permanent "CONNECTING" freeze.
        buffer = buffer.replace(/\r\n/g, "\n");

        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const eventStr of events) {
          const lines = eventStr.split("\n");
          let eventType = "message";
          let dataStr = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              dataStr = line.slice(6);
            } else if (line.startsWith("data:")) {
              dataStr = line.slice(5);
            }
          }

          if (!dataStr) continue;

          // Contract Validation
          const validation = validateSSEPayload(eventType, dataStr);
          if (!validation.valid && isDebug) {
            console.warn(`[CONTRACT_VALIDATION_WARNING] Event ${eventType}:`, validation.errors);
          }

          const parsedData = validation.data;

          if (isDebug) {
            console.log(`[SSE_RECEIVED] Event=${eventType}`, parsedData);
          }

          // Telemetry Integrity: Verify Request ID
          if (parsedData?.request_id && currentRequestId.current && parsedData.request_id !== currentRequestId.current) {
            console.warn(`[TELEMETRY_MISMATCH] Ignored event for request_id ${parsedData.request_id}, expected ${currentRequestId.current}`);
            continue;
          }

          // SSE Reliability: Verify Event Sequence (normalize seq vs event_sequence)
          const seqNum = parsedData?.seq ?? parsedData?.event_sequence;
          if (seqNum !== undefined) {
             if (seqNum < expectedEventSeq.current) {
                console.warn(`[EVENT_OUT_OF_ORDER] Received sequence ${seqNum}, expected >= ${expectedEventSeq.current}`);
             } else {
                expectedEventSeq.current = seqNum + 1;
             }
          }

          // Event routing
          if (eventType === "phase") {
            const phaseMap: Record<string, QueryPhase> = {
              classifying: "classifying",
              embedding: "embedding",
              retrieving: "retrieving",
              validating: "validating",
              reranking: "reranking",
              building_context: "building_context",
              generating: "generating",
              evaluating: "evaluating",
              verifying: "verifying",
            };
            const mappedPhase = phaseMap[parsedData.phase];
            if (mappedPhase) {
              setState(s => {
                const allowedNext = validTransitions[s.phase] || [];
                if (allowedNext.includes(mappedPhase) || s.phase === mappedPhase || s.phase === "connecting") {
                   if (isDebug) console.log(`[STATE_TRANSITION] ${s.phase} -> ${mappedPhase}`);
                   return { ...s, phase: mappedPhase };
                } else {
                   if (isDebug) console.warn(`[STATE_MACHINE_LOCKOUT_PREVENTED] Handled transition from ${s.phase} to ${mappedPhase}`);
                   return { ...s, phase: mappedPhase };
                }
              });
            }
          } else if (eventType === "context") {
            const extractedChunks = Array.isArray(parsedData) 
              ? parsedData 
              : (Array.isArray(parsedData?.chunks) ? parsedData.chunks : []);
            setState(s => ({ ...s, context: extractedChunks }));
          } else if (eventType === "diagnostics") {
            setState(s => ({ ...s, diagnostics: parsedData }));
          } else if (eventType === "reasoning_trace") {
            if (isDebug) console.log(`[REASONING_TRACE]`, parsedData);
          } else if (eventType === "token") {
            appendToken(typeof parsedData === "string" ? parsedData : (parsedData.text || ""));
            setState(s => {
              if (s.phase !== "generating" && s.phase !== "complete" && s.phase !== "verifying") {
                return { ...s, phase: "generating" };
              }
              return s;
            });
          } else if (eventType === "trust_verification") {
            setState(s => ({ ...s, trustVerification: parsedData }));
          } else if (eventType === "heartbeat") {
            if (isDebug) console.debug(`[HEARTBEAT] Received for request ${currentRequestId.current}`);
          } else if (eventType === "generation_failed") {
            throw new Error(parsedData?.reason || "The AI could not generate a meaningful answer. Try asking a more specific question.");
          } else if (eventType === "error") {
            const errorMsg = typeof parsedData === "string" ? parsedData : (parsedData.message || parsedData.error || "");
            if (errorMsg.includes("timeout") || errorMsg.includes("Timeout")) {
              throw new Error("The AI provider timed out. The system will failover on your next query.");
            } else if (errorMsg.includes("rate limit") || errorMsg.includes("429")) {
              throw new Error("We are hitting rate limits with the AI provider. Please wait a moment and try again.");
            } else {
              throw new Error(errorMsg || "An unexpected error occurred during generation.");
            }
          } else if (eventType === "done") {
            flushTokenBuffer();
            setState(s => ({ ...s, phase: "complete", generationMeta: parsedData }));
          } else {
            // Unknown event detector (Phase 7)
            console.warn(`[UNKNOWN_SSE_EVENT] Emitted by backend: event='${eventType}'`, parsedData);
          }
        }
      }

      // Final flush in case stream ended without "done" event
      flushTokenBuffer();
      setState(s => {
        if (s.phase === "generating" || s.phase === "verifying") {
          return { ...s, phase: "complete" };
        }
        return s;
      });

    } catch (err: any) {
      flushTokenBuffer();

      let errorMessage = err.message || "An unknown error occurred";
      if (err.name === "AbortError") {
        errorMessage = "Request timed out or was cancelled. Please try again.";
      }

      setState(prev => ({
        ...prev,
        phase: "error",
        error: errorMessage,
      }));
    } finally {
      clearTimeout(timeoutId);
      abortControllerRef.current = null;
    }
  }, [appendToken, flushTokenBuffer]);

  const reset = useCallback(() => {
    // Abort any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    if (flushTimer.current) {
      clearTimeout(flushTimer.current);
      flushTimer.current = null;
    }
    tokenBuffer.current = "";
    tokenCountRef.current = 0;
    firstTokenRecorded.current = false;

    setState({
      phase: "idle",
      query: null,
      streamingText: "",
      diagnostics: null,
      context: null,
      generationMeta: null,
      evaluationMetrics: null,
      trustVerification: null,
      error: null,
      startTime: null,
      firstTokenTime: null,
      tokenCount: 0,
    });
  }, []);

  return { state, submitQuery, reset };
}
