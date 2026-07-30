"use client";

import { motion } from "framer-motion";
import { GlassCard } from "@/components/ui/glass-card";
import { AnimatedNumber } from "@/components/ui/animated-number";
import { cn } from "@/lib/utils";
import type { EvalDashboardData } from "@/lib/api/types";

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: "spring" as const, damping: 25 } },
};

// ----------------------------------------------------------------------
// EvalHero
// ----------------------------------------------------------------------
export function EvalHero() {
  return (
    <motion.div variants={item} className="mb-12">
      <div className="flex items-center gap-3 mb-4">
        <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-v-blue to-v-violet flex items-center justify-center shadow-[0_0_20px_rgba(0,112,243,0.2)]">
          <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <div>
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-zinc-100">
            Retrieval Intelligence
          </h1>
          <p className="text-sm text-zinc-500 mt-0.5">Performance benchmarks & quality validation</p>
        </div>
      </div>
      <p className="text-base text-zinc-400 max-w-2xl leading-relaxed">
        Evaluation results across 40 human-curated ground truth queries spanning AI and sustainability domains.
        Three retrieval configurations compared: Dense-only, Hybrid + Reranking, and BM25 baseline.
      </p>
    </motion.div>
  );
}

// ----------------------------------------------------------------------
// MetricsTable — Animated metric cards from Real Data
// ----------------------------------------------------------------------

export function MetricsTable({ data }: { data: EvalDashboardData }) {
  if (!data?.latest_run) return null;
  const metrics = data.latest_run.metrics;
  const baseline = data.baselines?.previous || {};

  const cards = [
    { label: "nDCG@5", value: metrics.ndcg_at_5 || 0, prev: baseline.ndcg_at_5, format: "decimal" },
    { label: "Recall@5", value: metrics.recall_at_5 || 0, prev: baseline.recall_at_5, format: "decimal" },
    { label: "MRR@5", value: metrics.mrr || 0, prev: baseline.mrr, format: "decimal" },
    { label: "Faithfulness", value: metrics.faithfulness || 0, prev: baseline.faithfulness, format: "decimal", max: 5 },
  ];

  return (
    <motion.div variants={item}>
      <div className="flex justify-between items-center mb-5">
        <h3 className="text-lg font-semibold text-zinc-200 flex items-center gap-2">
          <svg className="w-5 h-5 text-v-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Latest Benchmark Run
        </h3>
        <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest bg-white/5 px-2 py-1 rounded">
          ID: {data.latest_run.experiment_id}
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {cards.map((c, i) => {
          const isImprovement = c.prev !== undefined && c.value > c.prev;
          const isDecline = c.prev !== undefined && c.value < c.prev;
          
          return (
            <motion.div
              key={c.label}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + i * 0.08, type: "spring", damping: 25 }}
            >
              <GlassCard interactive solid className="p-5 flex flex-col justify-between h-32 border-white/5 relative overflow-hidden">
                <div className="text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">{c.label}</div>
                <div>
                  <div className={cn(
                    "text-3xl font-mono font-bold mb-1 tabular-nums",
                    c.value > 0.9 ? "text-v-emerald" : "text-zinc-100"
                  )}>
                    <AnimatedNumber
                      value={c.value}
                      format={c.format as any}
                      decimals={c.format === "percentage" ? 0 : 3}
                    />
                    {c.max && <span className="text-sm text-zinc-500 font-normal ml-1">/ {c.max}</span>}
                  </div>
                  {c.prev !== undefined && (
                     <div className={cn("text-[10px] font-mono flex items-center gap-1", isImprovement ? "text-v-emerald" : isDecline ? "text-v-rose" : "text-zinc-600")}>
                       {isImprovement ? "↑" : isDecline ? "↓" : "−"} from {c.prev.toFixed(3)}
                     </div>
                  )}
                </div>
              </GlassCard>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}

// ----------------------------------------------------------------------
// BenchmarkHistory
// ----------------------------------------------------------------------
export function BenchmarkHistory({ history }: { history: any[] }) {
  if (!history || history.length < 2) return null;
  
  return (
    <motion.div variants={item} className="mt-14">
      <h3 className="text-lg font-semibold text-zinc-200 mb-5 flex items-center gap-2">
        <svg className="w-5 h-5 text-v-amber" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
        </svg>
        Benchmark History
      </h3>
      <GlassCard className="overflow-hidden border-white/5 p-5">
        <div className="space-y-4">
          {history.map((run, i) => (
             <div key={run.experiment_id} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0 text-sm">
               <div className="flex items-center gap-4">
                 <div className="text-[10px] font-mono text-zinc-500 w-24">
                   {new Date(run.timestamp * 1000).toLocaleTimeString()}
                 </div>
                 <div className="font-mono text-v-blue">{run.experiment_id}</div>
               </div>
               <div className="flex items-center gap-6 font-mono text-zinc-300">
                 <div><span className="text-zinc-600 mr-2">nDCG</span>{run.metrics.ndcg_at_5?.toFixed(3) || "---"}</div>
                 <div><span className="text-zinc-600 mr-2">MRR</span>{run.metrics.mrr?.toFixed(3) || "---"}</div>
               </div>
             </div>
          ))}
        </div>
      </GlassCard>
    </motion.div>
  );
}

// ----------------------------------------------------------------------
// LatencyProfile
// ----------------------------------------------------------------------
export function LatencyProfile({ latencyProfile, latestMetrics }: { latencyProfile: any, latestMetrics: any }) {
  if (!latencyProfile || !latestMetrics) return null;
  
  const endToEnd = latestMetrics.end_to_end_latency_ms || latestMetrics.latency_ms || 0;
  
  const latencies = [
    { label: "Embedding", avg: latencyProfile.embedding, color: "bg-zinc-500" },
    { label: "FAISS + BM25", avg: latencyProfile.faiss_bm25, color: "bg-v-blue" },
    { label: "CrossEncoder", avg: latencyProfile.cross_encoder, color: "bg-v-violet" },
    { label: "End-to-End", avg: endToEnd, color: "bg-v-emerald" },
  ];

  const maxLat = Math.max(endToEnd, 1000); // Scale relative to 1s or actual

  return (
    <motion.div variants={item} className="mt-14">
      <h3 className="text-lg font-semibold text-zinc-200 mb-5 flex items-center gap-2">
        <svg className="w-5 h-5 text-v-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Latency Profile (ms)
      </h3>
      <GlassCard className="overflow-hidden border-white/5">
        <table className="w-full text-sm text-left">
          <thead className="bg-zinc-900/60 text-[10px] uppercase tracking-[0.15em] text-zinc-500 font-mono border-b border-white/5">
            <tr>
              <th className="px-5 py-3.5 font-semibold">Stage</th>
              <th className="px-5 py-3.5 font-semibold">Duration (ms)</th>
              <th className="px-5 py-3.5 font-semibold w-64">Relative Scale</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-zinc-300 font-mono text-[13px]">
            {latencies.map((l) => (
              <tr key={l.label} className="hover:bg-white/[0.02] transition-colors">
                <td className="px-5 py-3.5 font-sans font-medium text-zinc-200">{l.label}</td>
                <td className="px-5 py-3.5 tabular-nums">{l.avg} ms</td>
                <td className="px-5 py-3.5">
                  <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min((l.avg / maxLat) * 100, 100)}%` }}
                      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                      className={cn("h-full rounded-full", l.color)}
                    />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </GlassCard>
    </motion.div>
  );
}

// ----------------------------------------------------------------------
// EmptyState
// ----------------------------------------------------------------------
export function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <motion.div variants={item} className="flex flex-col items-center justify-center py-24 text-center">
      <div className="h-16 w-16 rounded-full bg-zinc-900 border border-white/5 flex items-center justify-center mb-6">
        <svg className="w-6 h-6 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
      </div>
      <h3 className="text-xl font-semibold text-zinc-200 mb-2">{title}</h3>
      <p className="text-sm text-zinc-500 max-w-sm">{message}</p>
    </motion.div>
  );
}

export const EvalContainer = { container, item };
