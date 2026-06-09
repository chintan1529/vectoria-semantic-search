"use client";

import { useState, useCallback, useRef } from "react";
import { QueryPhase } from "@/components/query/pipeline-visualizer";

export interface RAGQueryState {
  phase: QueryPhase;
  query: string | null;
  streamingText: string;
  diagnostics: any | null;
  context: any | null;
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

export function useRAGQuery() {
  const [state, setState] = useState<RAGQueryState>({
    phase: "idle",
    query: null,
    streamingText: "",
    diagnostics: null,
    context: null,
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
    const startTime = Date.now();
    tokenBuffer.current = "";
    tokenCountRef.current = 0;
    firstTokenRecorded.current = false;

    setState({
      phase: "embedding",
      query: text,
      streamingText: "",
      diagnostics: null,
      context: null,
      error: null,
      startTime,
      firstTokenTime: null,
      tokenCount: 0,
    });

    try {
      setState(s => ({ ...s, phase: "retrieving" }));

      const res = await fetch("http://localhost:8000/api/query/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: text }),
      });

      if (!res.ok) {
        throw new Error(await res.text());
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No reader available");
      const decoder = new TextDecoder();

      setState(s => ({ ...s, phase: "generating" }));

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

          if (eventType === "context") {
            const contextData = JSON.parse(data);
            setState(s => ({ ...s, context: contextData }));
          } else if (eventType === "diagnostics") {
            const diagData = JSON.parse(data);
            setState(s => ({ ...s, diagnostics: diagData }));
          } else if (eventType === "token") {
            const token = JSON.parse(data);
            appendToken(token);
          } else if (eventType === "error") {
            const errorMessage = JSON.parse(data);
            throw new Error(errorMessage);
          } else if (eventType === "done") {
            // Flush any remaining buffered tokens before completing
            flushTokenBuffer();
            setState(s => ({ ...s, phase: "complete" }));
          }
        }
      }

      // Final flush in case stream ended without "done" event
      flushTokenBuffer();
      // Ensure we don't get stuck in 'generating' if the stream closes prematurely
      setState(s => {
        if (s.phase === "generating") {
           return { ...s, phase: "complete" };
        }
        return s;
      });

    } catch (err: any) {
      flushTokenBuffer();
      setState((prev) => ({
        ...prev,
        phase: "error",
        error: err.message || "An unknown error occurred",
      }));
    }
  }, [appendToken, flushTokenBuffer]);

  const reset = useCallback(() => {
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
      error: null,
      startTime: null,
      firstTokenTime: null,
      tokenCount: 0,
    });
  }, []);

  return { state, submitQuery, reset };
}
