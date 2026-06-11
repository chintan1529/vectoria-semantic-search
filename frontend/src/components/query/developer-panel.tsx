"use client";

import { motion } from "framer-motion";
import { RAGQueryState } from "@/lib/hooks/use-rag-query";

interface DeveloperPanelProps {
  state: RAGQueryState;
}

export function DeveloperPanel({ state }: DeveloperPanelProps) {
  const currentLatency = state.startTime ? Date.now() - state.startTime : 0;
  
  return (
    <div className="flex flex-col gap-3 w-full p-4 bg-black/40 border border-white/10 rounded-xl font-mono text-[11px] text-zinc-400 overflow-y-auto max-h-[500px]">
      <div className="flex items-center justify-between pb-2 border-b border-white/5">
        <h2 className="font-semibold text-v-blue uppercase tracking-widest">Developer Mode</h2>
        <div className={`h-2 w-2 rounded-full ${state.phase === "error" ? "bg-red-500" : state.phase === "complete" ? "bg-emerald-500" : state.phase !== "idle" ? "bg-amber-500 animate-pulse" : "bg-zinc-600"}`} />
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-2">
        <div className="text-zinc-500">Request ID</div>
        <div className="text-zinc-200 truncate">{state.diagnostics?.request_id || state.generationMeta?.request_id || "—"}</div>

        <div className="text-zinc-500">Current Stage</div>
        <div className="text-zinc-200">{state.phase.toUpperCase()}</div>

        <div className="text-zinc-500">Current Latency</div>
        <div className="text-zinc-200">{currentLatency > 0 ? `${currentLatency}ms` : "—"}</div>

        <div className="text-zinc-500">Token Count</div>
        <div className="text-zinc-200">{state.tokenCount}</div>

        <div className="text-zinc-500">Retrieved Chunks</div>
        <div className="text-zinc-200">{state.context ? state.context.length : 0}</div>

        <div className="text-zinc-500">Gen Status</div>
        <div className="text-zinc-200">{state.generationMeta ? "FINISHED" : (state.phase === "generating" ? "STREAMING" : "WAITING")}</div>
      </div>

      {state.error && (
        <div className="mt-2 p-2 bg-red-500/10 border border-red-500/20 text-red-400 rounded">
          <div className="font-semibold mb-1">ERROR</div>
          <div className="whitespace-pre-wrap">{state.error}</div>
        </div>
      )}

      {state.diagnostics && (
        <div className="mt-2 border-t border-white/5 pt-2">
          <div className="text-zinc-500 mb-1">Diagnostics Dump</div>
          <pre className="text-[10px] bg-black/50 p-2 rounded text-zinc-300 overflow-x-auto">
            {JSON.stringify(state.diagnostics, null, 2)}
          </pre>
        </div>
      )}
      
      {state.generationMeta && (
        <div className="mt-2 border-t border-white/5 pt-2">
          <div className="text-zinc-500 mb-1">Generation Meta</div>
          <pre className="text-[10px] bg-black/50 p-2 rounded text-zinc-300 overflow-x-auto">
            {JSON.stringify(state.generationMeta, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
