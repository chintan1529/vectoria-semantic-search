"use client";

import { useState, useEffect, useCallback } from "react";
import { Navbar } from "@/components/layout/navbar";
import { WorkspaceLayout } from "@/components/layout/workspace-layout";
import { QueryInput } from "@/components/query/query-input";
import { MetricsSidebar } from "@/components/query/metrics-sidebar";
import { PipelineVisualizer } from "@/components/query/pipeline-visualizer";
import { ChatInterface } from "@/components/query/chat-interface";
import { RetrievalIntelligenceView } from "@/components/features/retrieval-intelligence-view";
import { useRAGQuery } from "@/lib/hooks/use-rag-query";
import { useKeyboard } from "@/lib/hooks/use-keyboard";
import { AnimatedBackground } from "@/components/landing/animated-background";

export default function QueryWorkspace() {
  const { state, submitQuery, reset } = useRAGQuery();
  const [isInspectorOpen, setIsInspectorOpen] = useState(false);

  // R3: Escape closes the inspector panel
  const handleEscape = useCallback(() => {
    if (isInspectorOpen) setIsInspectorOpen(false);
  }, [isInspectorOpen]);

  useKeyboard({ onEscape: handleEscape });

  // Auto-open inspector when we start retrieving context
  useEffect(() => {
    if (state.phase === "complete" || state.phase === "generating" || state.context) {
      setIsInspectorOpen(true);
    }
  }, [state.phase, state.context]);

  const isProcessing = state.phase !== "idle" && state.phase !== "complete" && state.phase !== "error";

  // Allow submitting a new query after completion
  const handleNewQuery = useCallback((query: string) => {
    setIsInspectorOpen(false);
    reset();
    setTimeout(() => submitQuery(query), 50);
  }, [reset, submitQuery]);

  const MainContent = (
    <>
      <div className="pt-8">
        <QueryInput 
          onQuerySubmit={state.phase === "idle" ? submitQuery : handleNewQuery} 
          isProcessing={isProcessing} 
        />
      </div>
      
      {state.phase !== "idle" && (
        <PipelineVisualizer 
          phase={state.phase} 
          latencies={
            state.diagnostics 
              ? {
                  embedding: Math.round(state.diagnostics.retrieval_latency_ms * 0.4),
                  retrieving: Math.round(state.diagnostics.retrieval_latency_ms * 0.6),
                  reranking: 0,
                  generating: 0,
                }
              : undefined
          }
        />
      )}
      
      <ChatInterface 
        phase={state.phase} 
        streamingText={state.streamingText} 
        error={state.error} 
      />
    </>
  );

  const InspectorPanel = (
    <div className="flex flex-col h-full bg-surface border-l border-white/5">
      <div className="flex items-center justify-between pb-4 border-b border-white/5 mb-2 sticky top-0 z-20 backdrop-blur-xl pt-4 px-4">
        <h2 className="text-sm font-semibold text-zinc-300 flex items-center gap-2">
          <svg className="w-4 h-4 text-v-emerald" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Retrieval Intelligence
        </h2>
        <button 
          onClick={() => setIsInspectorOpen(false)}
          className="text-zinc-500 hover:text-zinc-300 transition-colors p-1 rounded hover:bg-white/5"
          title="Close (Esc)"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      
      {state.diagnostics || state.context ? (
        <RetrievalIntelligenceView context={state.context} diagnostics={state.diagnostics} />
      ) : (
        <div className="p-4 text-sm text-zinc-500 text-center mt-10">
          Awaiting query context...
        </div>
      )}
    </div>
  );

  return (
    <>
      <AnimatedBackground />
      <Navbar />
      <WorkspaceLayout
        mainContent={MainContent}
        inspectorPanel={InspectorPanel}
        metricsSidebar={<MetricsSidebar phase={state.phase} response={null} />}
        isInspectorOpen={isInspectorOpen}
      />
    </>
  );
}
