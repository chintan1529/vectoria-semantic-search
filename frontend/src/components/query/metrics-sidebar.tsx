"use client";

import { motion } from "framer-motion";
import { RAGResponse } from "@/lib/api/types";
import { QueryPhase } from "./pipeline-visualizer";
import { AnimatedNumber } from "@/components/ui/animated-number";

interface MetricsSidebarProps {
  phase: QueryPhase;
  diagnostics: any | null;
  generationMeta: any | null;
  evaluationMetrics: any | null;
  trustVerification?: any | null;
  firstTokenTime?: number | null;
  startTime?: number | null;
  tokenCount?: number;
}

const stagger = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.1 },
  },
};

const fadeUp = {
  hidden: { opacity: 0, y: 6 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: "easeOut" as const } },
};

function MetricRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-medium">
        {label}
      </div>
      {children}
    </div>
  );
}

function SectionDivider() {
  return (
    <div className="relative py-1">
      <div className="h-px bg-gradient-to-r from-transparent via-white/8 to-transparent" />
    </div>
  );
}

export function MetricsSidebar({ phase, diagnostics, generationMeta, evaluationMetrics, firstTokenTime, startTime, tokenCount }: MetricsSidebarProps) {
  const isActive = phase !== "idle" && phase !== "error";
  const ttft = firstTokenTime && startTime ? firstTokenTime - startTime : null;

  // If no diagnostics yet, show the empty shell state
  if (!diagnostics) {
    return (
      <div className="flex flex-col gap-5 w-full">
        <div className="flex items-center justify-between pb-3 border-b border-white/5">
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.15em] text-zinc-500">
            Telemetry
          </h2>
          {isActive && (
            <motion.div
              animate={{ scale: [1, 1.3, 1] }}
              transition={{ repeat: Infinity, duration: 1.5 }}
              className="h-1.5 w-1.5 rounded-full bg-v-emerald"
            />
          )}
        </div>
        
        <div className="space-y-4 opacity-40">
          <MetricRow label="Total Latency">
            <div className="text-lg font-mono font-medium text-zinc-700 tabular-nums">— ms</div>
          </MetricRow>
          <MetricRow label="Generation Latency">
            <div className="text-lg font-mono font-medium text-zinc-700 tabular-nums">— ms</div>
          </MetricRow>

          <SectionDivider />

          {ttft !== null && (
            <MetricRow label="Time to First Token">
              <div className="text-sm font-mono text-v-blue tabular-nums">
                {ttft}ms
              </div>
            </MetricRow>
          )}

          <MetricRow label="Model Identity">
            <div className="text-sm font-mono text-zinc-700 mt-1">waiting…</div>
          </MetricRow>
        </div>
      </div>
    );
  }

  // Active state with real data
  const meta = generationMeta || {};
  const totalLatency = meta.generation_latency_ms 
    ? diagnostics.retrieval_latency_ms + meta.generation_latency_ms 
    : 0;

  return (
    <motion.div 
      variants={stagger}
      initial="hidden"
      animate="show"
      className="flex flex-col gap-5 w-full"
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-white/5">
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.15em] text-zinc-500">
          Telemetry
        </h2>
        <div className="h-1.5 w-1.5 rounded-full bg-v-blue" />
      </div>

      {/* Latency Section */}
      <motion.div variants={fadeUp} className="space-y-3">
        <MetricRow label="Total Latency">
          <div className="text-xl font-mono font-bold text-zinc-100 flex items-baseline gap-1 tabular-nums">
            {totalLatency > 0 ? (
              <AnimatedNumber value={totalLatency} format="integer" />
            ) : (
              "—"
            )}
            <span className="text-[10px] font-sans text-zinc-500 font-normal">ms</span>
          </div>
        </MetricRow>
        
        <div className="grid grid-cols-2 gap-2">
           <MetricRow label="Retrieval">
             <div className="text-sm font-mono text-zinc-400 tabular-nums">
               <AnimatedNumber value={diagnostics.retrieval_latency_ms} format="integer" /> ms
             </div>
           </MetricRow>
           <MetricRow label="Rerank">
             <div className="text-sm font-mono text-zinc-400 tabular-nums">
               {diagnostics.reranking_latency_ms ? <AnimatedNumber value={diagnostics.reranking_latency_ms} format="integer" /> : 0} ms
             </div>
           </MetricRow>
        </div>
        
        <MetricRow label="Generation Latency">
          <div className="text-lg font-mono font-medium text-zinc-300 flex items-baseline gap-1 tabular-nums">
            {meta.generation_latency_ms ? (
              <AnimatedNumber value={meta.generation_latency_ms} format="integer" />
            ) : (
              "—"
            )}
            <span className="text-[10px] font-sans text-zinc-500 font-normal">ms</span>
          </div>
        </MetricRow>

        {ttft !== null && (
          <MetricRow label="Time to First Token">
            <div className="text-sm font-mono text-v-blue tabular-nums">
              {ttft}ms
            </div>
          </MetricRow>
        )}
      </motion.div>

      <SectionDivider />

      {/* Tokens Section */}
      <motion.div variants={fadeUp} className="space-y-3">
        <MetricRow label="Total Tokens">
          <div className="text-lg font-mono font-medium text-zinc-200 tabular-nums">
            {tokenCount ? <AnimatedNumber value={tokenCount} format="integer" /> : "—"}
          </div>
        </MetricRow>
        <div className="grid grid-cols-2 gap-2">
          <MetricRow label="Prompt">
            <div className="text-sm font-mono text-zinc-400 tabular-nums">
              {meta.prompt_tokens ? <AnimatedNumber value={meta.prompt_tokens} format="integer" /> : "—"}
            </div>
          </MetricRow>
          <MetricRow label="Completion">
            <div className="text-sm font-mono text-zinc-400 tabular-nums">
              {meta.completion_tokens ? <AnimatedNumber value={meta.completion_tokens} format="integer" /> : "—"}
            </div>
          </MetricRow>
        </div>

        {/* Token throughput */}
        {meta.generation_latency_ms > 0 && meta.completion_tokens > 0 && (
          <MetricRow label="Throughput">
            <div className="text-sm font-mono text-zinc-400 tabular-nums">
              {((meta.completion_tokens / meta.generation_latency_ms) * 1000).toFixed(1)} tok/s
            </div>
          </MetricRow>
        )}
      </motion.div>

      <SectionDivider />

      {/* Model Meta Section */}
      <motion.div variants={fadeUp} className="space-y-3">
        <MetricRow label="Model Identity">
          <div className="text-xs font-mono text-v-violet bg-v-violet/10 px-2 py-1 rounded inline-block">
            {meta.model_used || "streaming..."}
          </div>
        </MetricRow>
        <MetricRow label="Prompt Version">
          <div className="text-xs font-mono text-zinc-400">
            {meta.prompt_version || "—"}
          </div>
        </MetricRow>
        <MetricRow label="Finish Reason">
          <div className="text-xs font-mono text-zinc-500">
            {meta.finish_reason || "—"}
          </div>
        </MetricRow>
      </motion.div>

      <SectionDivider />

      {/* Citations Summary */}
      <motion.div variants={fadeUp}>
        <MetricRow label="Verified Citations">
          <div className="text-lg font-mono font-medium text-v-emerald flex items-center gap-2 tabular-nums">
            {meta.citation_count !== undefined ? <AnimatedNumber value={meta.citation_count} format="integer" /> : "—"}
            <svg className="w-4 h-4 text-v-emerald" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        </MetricRow>
      </motion.div>
      
      {evaluationMetrics && (
        <>
          <SectionDivider />
          <motion.div variants={fadeUp} className="space-y-3">
            <h3 className="text-[10px] uppercase tracking-wider text-v-emerald font-medium border-b border-v-emerald/20 pb-1 mb-2">Answer Evaluation</h3>
            <div className="grid grid-cols-2 gap-2">
              <MetricRow label="Faithfulness">
                <div className="text-sm font-mono text-zinc-300 tabular-nums">
                  <AnimatedNumber value={evaluationMetrics.faithfulness} format="integer" /> / 5
                </div>
              </MetricRow>
              <MetricRow label="Relevance">
                <div className="text-sm font-mono text-zinc-300 tabular-nums">
                  <AnimatedNumber value={evaluationMetrics.relevance} format="integer" /> / 5
                </div>
              </MetricRow>
            </div>
            
            <MetricRow label="Hallucination Risk">
              <div className={`text-xs font-mono px-2 py-1 rounded inline-block ${
                evaluationMetrics.hallucination_risk === 'Low' ? 'text-v-emerald bg-v-emerald/10' :
                evaluationMetrics.hallucination_risk === 'High' ? 'text-red-400 bg-red-400/10' :
                'text-amber-400 bg-amber-400/10'
              }`}>
                {evaluationMetrics.hallucination_risk}
              </div>
            </MetricRow>
          </motion.div>
        </>
      )}
    </motion.div>
  );
}
