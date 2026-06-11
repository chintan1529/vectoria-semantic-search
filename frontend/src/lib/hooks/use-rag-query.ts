"use client";

import { useState, useCallback, useRef } from "react";
import { QueryPhase } from "@/components/query/pipeline-visualizer";

export interface RAGQueryState {
  phase: QueryPhase;
  query: string | null;
  streamingText: string;
  diagnostics: any | null;
  context: any | null;
  generationMeta: any | null;
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
const BACKEND_URL = "http://localhost:8000";

export function useRAGQuery() {
  const [state, setState] = useState<RAGQueryState>({
    phase: "idle",
    query: null,
    streamingText: "",
    diagnostics: null,
    context: null,
    generationMeta: null,
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

    setState({
      phase: "classifying",
      query: text,
      streamingText: "",
      diagnostics: null,
      context: null,
      generationMeta: null,
      error: null,
      startTime,
      firstTokenTime: null,
      tokenCount: 0,
    });

    try {
      // --- Pre-flight readiness check ---
      try {
        const healthRes = await fetch(`${BACKEND_URL}/ready`, {
          signal: controller.signal,
        });
        if (!healthRes.ok) {
          setState(s => ({
            ...s,
            phase: "error",
            error: "System is still warming up. Models are loading. Please wait a moment and try again.",
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

      setState(s => ({ ...s, phase: "retrieving" }));

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

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No reader available");
      const decoder = new TextDecoder();

      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const eventStr of events) {
          const lines = eventStr.split("\n");
          let eventType = "message";
          let data = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              data = line.slice(6);
            }
          }

          if (eventType === "phase") {
            const phaseData = JSON.parse(data);
            const phaseMap: Record<string, QueryPhase> = {
              classifying: "classifying",
              retrieving: "retrieving",
              validating: "validating",
              reranking: "reranking",
              generating: "generating",
            };
            const mappedPhase = phaseMap[phaseData.phase];
            if (mappedPhase) {
              setState(s => ({ ...s, phase: mappedPhase }));
            }
          } else if (eventType === "context") {
            const contextData = JSON.parse(data);
            setState(s => ({ ...s, context: contextData }));
          } else if (eventType === "diagnostics") {
            const diagData = JSON.parse(data);
            setState(s => ({ ...s, diagnostics: diagData }));
          } else if (eventType === "token") {
            // Transition to generating on first token if not already
            const token = JSON.parse(data);
            appendToken(token);
          } else if (eventType === "error") {
            const errorData = JSON.parse(data);
            const errorMessage = typeof errorData === "string" ? errorData : errorData.message || "Generation failed";
            throw new Error(errorMessage);
          } else if (eventType === "done") {
            const doneData = JSON.parse(data);
            flushTokenBuffer();
            setState(s => ({ ...s, phase: "complete", generationMeta: doneData }));
          }
        }
      }

      // Final flush in case stream ended without "done" event
      flushTokenBuffer();
      setState(s => {
        if (s.phase === "generating" || s.phase === "retrieving") {
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
      error: null,
      startTime: null,
      firstTokenTime: null,
      tokenCount: 0,
    });
  }, []);

  return { state, submitQuery, reset };
}
