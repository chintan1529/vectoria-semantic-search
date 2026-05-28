"use client";

import { useState, useCallback } from "react";
import { QueryPhase } from "@/components/query/pipeline-visualizer";

export interface RAGQueryState {
  phase: QueryPhase;
  query: string | null;
  streamingText: string;
  diagnostics: any | null;
  context: any | null;
  error: string | null;
  startTime: number | null;
}

export function useRAGQuery() {
  const [state, setState] = useState<RAGQueryState>({
    phase: "idle",
    query: null,
    streamingText: "",
    diagnostics: null,
    context: null,
    error: null,
    startTime: null,
  });

  const submitQuery = useCallback(async (text: string) => {
    const startTime = Date.now();
    
    setState({
      phase: "embedding",
      query: text,
      streamingText: "",
      diagnostics: null,
      context: null,
      error: null,
      startTime,
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
            setState(s => ({ ...s, streamingText: s.streamingText + token }));
          } else if (eventType === "done") {
            setState(s => ({ ...s, phase: "complete" }));
          }
        }
      }

    } catch (err: any) {
      setState((prev) => ({
        ...prev,
        phase: "error",
        error: err.message || "An unknown error occurred",
      }));
    }
  }, []);

  const reset = useCallback(() => {
    setState({
      phase: "idle",
      query: null,
      streamingText: "",
      diagnostics: null,
      context: null,
      error: null,
      startTime: null,
    });
  }, []);

  return { state, submitQuery, reset };
}
