"use client";

import { RAGResponse } from "@/lib/api/types";
import { ChunkCard } from "./chunk-card";

interface RetrievalInspectorProps {
  response: RAGResponse | null;
}

export function RetrievalInspector({ response }: RetrievalInspectorProps) {
  if (!response) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center px-4 h-full">
        <div className="w-12 h-12 rounded-full bg-zinc-900 border border-white/5 flex items-center justify-center mb-4">
          <svg className="w-5 h-5 text-zinc-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-zinc-500 text-sm">
          Awaiting query execution...
        </p>
      </div>
    );
  }

  // Helper to check if a chunk was cited, and what its citation ID is
  const getCitationInfo = (chunkId: string) => {
    for (const [citationKey, result] of Object.entries(response.citations)) {
      if (result.chunk.chunk_id === chunkId) {
        // citationKey is like "Doc 1"
        const id = citationKey.replace("Doc ", "");
        return { isCited: true, id };
      }
    }
    return { isCited: false, id: undefined };
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Summary Header */}
      <div className="grid grid-cols-2 gap-2 mb-2">
        <div className="p-3 rounded-lg bg-zinc-900 border border-white/5 flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-mono">Retrieved</span>
          <span className="text-lg font-mono font-medium text-zinc-200">{response.num_retrieved}</span>
        </div>
        <div className="p-3 rounded-lg bg-zinc-900 border border-white/5 flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-mono">Avg Score</span>
          <span className="text-lg font-mono font-medium text-zinc-200">{response.context_stats.average_score.toFixed(3)}</span>
        </div>
      </div>

      <div className="text-[10px] uppercase tracking-widest text-zinc-600 font-semibold mb-1 border-b border-white/5 pb-2">
        Cross-Encoder Ranked Results
      </div>

      {/* Chunk List */}
      <div className="flex flex-col gap-3 pb-20">
        {response.retrieved_results.map((result, idx) => {
          const { isCited, id } = getCitationInfo(result.chunk.chunk_id);
          
          return (
            <ChunkCard 
              key={result.chunk.chunk_id}
              result={result}
              isCited={isCited}
              citationId={id}
              index={idx}
            />
          );
        })}
      </div>
    </div>
  );
}
