"use client";

import { motion } from "framer-motion";
import { RAGResponse } from "@/lib/api/types";
import { QueryPhase } from "./pipeline-visualizer";
import { AnimatedNumber } from "@/components/ui/animated-number";

interface MetricsSidebarProps {
  phase: QueryPhase;
  response: RAGResponse | null;
}

export function MetricsSidebar({ phase, response }: MetricsSidebarProps) {
  // If no response yet, show the empty shell state
  if (!response) {
    return (
      <div className="flex flex-col gap-6 w-full opacity-50">
        <div className="flex items-center justify-between pb-4 border-b border-white/5">
          <h2 className="text-xs font-medium uppercase tracking-widest text-zinc-500">
            Telemetry
          </h2>
          {phase !== "idle" && phase !== "error" && (
            <div className="h-1.5 w-1.5 rounded-full bg-v-emerald animate-pulse" />
          )}
        </div>
        
        <div className="space-y-4">
          <div className="space-y-1">
            <div className="text-[10px] uppercase tracking-wider text-zinc-600">Total Latency</div>
            <div className="text-lg font-mono font-medium text-zinc-700">-- ms</div>
          </div>
          <div className="space-y-1">
            <div className="text-[10px] uppercase tracking-wider text-zinc-600">Generation Latency</div>
            <div className="text-lg font-mono font-medium text-zinc-700">-- ms</div>
          </div>
          <div className="pt-4 border-t border-white/5 space-y-1">
            <div className="text-[10px] uppercase tracking-wider text-zinc-600">Model Identity</div>
            <div className="text-sm font-mono text-zinc-700 mt-1">waiting...</div>
          </div>
        </div>
      </div>
    );
  }

  // Active state with real data
  const meta = response.generation_meta;

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col gap-6 w-full"
    >
      <div className="flex items-center justify-between pb-4 border-b border-white/5">
        <h2 className="text-xs font-medium uppercase tracking-widest text-zinc-500">
          Telemetry
        </h2>
        <div className="h-1.5 w-1.5 rounded-full bg-v-blue" />
      </div>

      <div className="space-y-6">
        {/* Latency Section */}
        <div className="space-y-3">
          <div className="space-y-1">
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">Total Latency</div>
            <div className="text-xl font-mono font-bold text-zinc-100 flex items-baseline gap-1">
              <AnimatedNumber value={response.latency_ms} format="integer" />
              <span className="text-xs font-sans text-zinc-500 font-normal">ms</span>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-2 mt-2">
             <div className="space-y-1">
               <div className="text-[9px] uppercase tracking-wider text-zinc-600">Retrieval</div>
               <div className="text-sm font-mono text-zinc-400">
                 <AnimatedNumber value={response.retrieval_latency_ms} format="integer" /> ms
               </div>
             </div>
             <div className="space-y-1">
               <div className="text-[9px] uppercase tracking-wider text-zinc-600">Rerank</div>
               <div className="text-sm font-mono text-zinc-400">
                 <AnimatedNumber value={response.rerank_latency_ms} format="integer" /> ms
               </div>
             </div>
          </div>
          
          <div className="space-y-1 mt-2">
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">Generation Latency</div>
            <div className="text-lg font-mono font-medium text-zinc-300 flex items-baseline gap-1">
              <AnimatedNumber value={response.generation_latency_ms} format="integer" />
              <span className="text-[10px] font-sans text-zinc-500 font-normal">ms</span>
            </div>
          </div>
        </div>

        {/* Tokens Section */}
        <div className="space-y-3 pt-4 border-t border-white/5">
          <div className="space-y-1">
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">Total Tokens</div>
            <div className="text-lg font-mono font-medium text-zinc-200">
              <AnimatedNumber value={meta.total_tokens} format="integer" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <div className="text-[9px] uppercase tracking-wider text-zinc-600">Prompt</div>
              <div className="text-sm font-mono text-zinc-400">
                <AnimatedNumber value={meta.prompt_tokens} format="integer" />
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-[9px] uppercase tracking-wider text-zinc-600">Completion</div>
              <div className="text-sm font-mono text-zinc-400">
                <AnimatedNumber value={meta.completion_tokens} format="integer" />
              </div>
            </div>
          </div>
        </div>

        {/* Model Meta Section */}
        <div className="space-y-3 pt-4 border-t border-white/5">
          <div className="space-y-1">
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">Model Identity</div>
            <div className="text-xs font-mono text-v-violet bg-v-violet/10 px-2 py-1 rounded inline-block">
              {meta.model_used}
            </div>
          </div>
          <div className="space-y-1">
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">Prompt Version</div>
            <div className="text-xs font-mono text-zinc-400">
              {meta.prompt_version}
            </div>
          </div>
        </div>

        {/* Citations Summary */}
        <div className="space-y-1 pt-4 border-t border-white/5">
          <div className="text-[10px] uppercase tracking-wider text-zinc-500">Verified Citations</div>
          <div className="text-lg font-mono font-medium text-v-emerald flex items-center gap-2">
            <AnimatedNumber value={meta.citation_count} format="integer" />
            <svg className="w-4 h-4 text-v-emerald" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </div>

      </div>
    </motion.div>
  );
}
