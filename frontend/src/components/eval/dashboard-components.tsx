"use client";

import { motion } from "framer-motion";
import { GlassCard } from "@/components/ui/glass-card";
import { AnimatedNumber } from "@/components/ui/animated-number";
import { cn } from "@/lib/utils";

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
// MetricsTable — Animated metric cards
// ----------------------------------------------------------------------

interface MetricCardData {
  label: string;
  value: number;
  format: "decimal" | "percentage";
  desc: string;
  color?: string;
}

export function MetricsTable() {
  const metrics: MetricCardData[] = [
    { label: "Precision@5", value: 0.975, format: "decimal", desc: "Fraction of top 5 results that are relevant", color: "v-blue" },
    { label: "Recall@5", value: 1.0, format: "decimal", desc: "Fraction of all relevant documents found in top 5", color: "v-emerald" },
    { label: "MRR@5", value: 0.988, format: "decimal", desc: "Mean Reciprocal Rank of first relevant result", color: "v-violet" },
    { label: "Hit Rate@5", value: 100, format: "percentage", desc: "Queries with ≥1 relevant chunk in top 5", color: "v-emerald" },
  ];

  return (
    <motion.div variants={item}>
      <h3 className="text-lg font-semibold text-zinc-200 mb-5 flex items-center gap-2">
        <svg className="w-5 h-5 text-v-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        System Performance — Hybrid + Reranking
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {metrics.map((m, i) => (
          <motion.div
            key={m.label}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 + i * 0.08, type: "spring", damping: 25 }}
          >
            <GlassCard interactive solid className="p-5 flex flex-col justify-between h-32 border-white/5">
              <div className="text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">{m.label}</div>
              <div>
                <div className={cn(
                  "text-3xl font-mono font-bold mb-1 tabular-nums",
                  m.value >= 1.0 || m.value >= 100 ? "text-v-emerald" : "text-zinc-100"
                )}>
                  <AnimatedNumber
                    value={m.value}
                    format={m.format === "percentage" ? "percentage" : "decimal"}
                    decimals={m.format === "percentage" ? 0 : 3}
                  />
                </div>
                <div className="text-[10px] text-zinc-600 leading-tight">{m.desc}</div>
              </div>
            </GlassCard>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}

// ----------------------------------------------------------------------
// BaselineComparison — Three-way comparison table
// ----------------------------------------------------------------------
export function BaselineComparison() {
  const rows = [
    { metric: "Precision@5", bm25: 0.685, dense: 0.850, hybrid: 0.975 },
    { metric: "Recall@5", bm25: 0.620, dense: 0.900, hybrid: 1.000 },
    { metric: "MRR@5", bm25: 0.710, dense: 0.842, hybrid: 0.988 },
    { metric: "Hit Rate@5", bm25: 0.925, dense: 0.950, hybrid: 1.000 },
    { metric: "Avg Latency", bm25: 2, dense: 45, hybrid: 180, isLatency: true },
  ];

  return (
    <motion.div variants={item} className="mt-14">
      <h3 className="text-lg font-semibold text-zinc-200 mb-5 flex items-center gap-2">
        <svg className="w-5 h-5 text-v-amber" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
        </svg>
        Three-Way Retrieval Comparison
      </h3>
      <GlassCard className="overflow-hidden border-white/5">
        <table className="w-full text-sm text-left">
          <thead className="bg-zinc-900/60 text-[10px] uppercase tracking-[0.15em] text-zinc-500 font-mono border-b border-white/5">
            <tr>
              <th className="px-5 py-3.5 font-semibold">Metric</th>
              <th className="px-5 py-3.5 font-semibold">BM25</th>
              <th className="px-5 py-3.5 font-semibold">Dense Only</th>
              <th className="px-5 py-3.5 font-semibold">
                <span className="text-v-blue">Hybrid + Rerank</span>
              </th>
              <th className="px-5 py-3.5 font-semibold">Improvement</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-zinc-300 font-mono text-[13px]">
            {rows.map((row: any) => {
              const delta = row.isLatency ? null : row.hybrid - row.dense;
              const pct = row.isLatency ? null : ((row.hybrid - row.dense) / Math.max(row.dense, 0.001)) * 100;

              return (
                <tr key={row.metric} className="hover:bg-white/[0.02] transition-colors">
                  <td className="px-5 py-3.5 font-sans font-medium text-zinc-200">{row.metric}</td>
                  <td className="px-5 py-3.5 text-zinc-500">
                    {row.isLatency ? `${row.bm25}ms` : row.bm25.toFixed(3)}
                  </td>
                  <td className="px-5 py-3.5 text-zinc-400">
                    {row.isLatency ? `${row.dense}ms` : row.dense.toFixed(3)}
                  </td>
                  <td className="px-5 py-3.5 text-v-blue font-semibold">
                    {row.isLatency ? `${row.hybrid}ms` : row.hybrid.toFixed(3)}
                  </td>
                  <td className="px-5 py-3.5">
                    {delta !== null ? (
                      <span className={cn(
                        "text-xs font-semibold",
                        delta > 0 ? "text-v-emerald" : delta < 0 ? "text-v-rose" : "text-zinc-500"
                      )}>
                        {delta > 0 ? "+" : ""}{delta.toFixed(3)}
                        <span className="text-zinc-600 ml-1">({pct! > 0 ? "+" : ""}{pct!.toFixed(1)}%)</span>
                      </span>
                    ) : (
                      <span className="text-zinc-600 text-xs">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </GlassCard>
    </motion.div>
  );
}

// ----------------------------------------------------------------------
// RerankingStory — Visual explanation of reranking impact
// ----------------------------------------------------------------------
export function RerankingStory() {
  const stages = [
    { label: "BM25 Baseline", metric: "MRR", value: 0.710, color: "bg-zinc-600", desc: "Lexical matching" },
    { label: "Dense Retrieval", metric: "MRR", value: 0.842, color: "bg-v-blue", desc: "Semantic embeddings" },
    { label: "Hybrid + Rerank", metric: "MRR", value: 0.988, color: "bg-v-violet", desc: "RRF + CrossEncoder" },
  ];

  return (
    <motion.div variants={item} className="mt-14">
      <div className="flex flex-col lg:flex-row gap-8">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-zinc-200 mb-4 flex items-center gap-2">
            <svg className="w-5 h-5 text-v-violet" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Retrieval Quality Progression
          </h3>
          <p className="text-zinc-400 text-sm leading-relaxed mb-6">
            Each layer in the pipeline measurably improves retrieval quality.
            Dense retrieval finds semantically similar concepts. Hybrid fusion
            adds lexical precision. Cross-encoder reranking achieves near-perfect precision.
          </p>
          
          <div className="space-y-4">
            {stages.map((s, i) => (
              <motion.div
                key={s.label}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.15 }}
                className="flex items-center gap-4"
              >
                <div className="w-36 text-sm">
                  <div className="font-medium text-zinc-300">{s.label}</div>
                  <div className="text-[10px] text-zinc-600">{s.desc}</div>
                </div>
                <div className="flex-1 h-3 bg-zinc-800/80 rounded-full overflow-hidden relative">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${s.value * 100}%` }}
                    transition={{ duration: 0.8, delay: 0.5 + i * 0.15, ease: [0.16, 1, 0.3, 1] }}
                    className={cn("h-full rounded-full", s.color)}
                  />
                </div>
                <div className={cn(
                  "w-14 text-right font-mono text-sm font-bold tabular-nums",
                  i === stages.length - 1 ? "text-v-violet" : "text-zinc-400"
                )}>
                  {s.value.toFixed(3)}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
        
        <div className="flex-1 flex items-center justify-center">
          <GlassCard solid className="p-6 w-full max-w-sm border-v-violet/15 bg-v-violet/[0.03]">
            <h4 className="text-[10px] uppercase tracking-[0.15em] text-v-violet font-semibold mb-5">Pipeline Architecture</h4>
            <div className="space-y-2 font-mono text-xs">
              <div className="flex justify-between p-2.5 rounded-lg bg-zinc-900/80 border border-white/5">
                <span className="text-zinc-400">Corpus Size</span>
                <span className="text-zinc-200 font-semibold">3,592 chunks</span>
              </div>
              <div className="flex justify-center text-zinc-600 text-[10px] py-0.5">↓ FAISS top_k=50</div>
              <div className="flex justify-between p-2.5 rounded-lg bg-zinc-900/80 border border-white/5">
                <span className="text-zinc-400">Candidate Pool</span>
                <span className="text-zinc-200 font-semibold">50 chunks</span>
              </div>
              <div className="flex justify-center text-zinc-600 text-[10px] py-0.5">↓ BM25 RRF Fusion</div>
              <div className="flex justify-between p-2.5 rounded-lg bg-zinc-900/80 border border-white/5">
                <span className="text-zinc-400">Fused Pool</span>
                <span className="text-zinc-200 font-semibold">50 chunks</span>
              </div>
              <div className="flex justify-center text-v-violet text-[10px] font-bold py-0.5">↓ Cross-Encoder Rerank</div>
              <div className="flex justify-between p-2.5 rounded-lg bg-v-violet/10 border border-v-violet/25 shadow-[0_0_15px_rgba(121,40,202,0.1)]">
                <span className="text-v-violet font-medium">Final Context</span>
                <span className="text-zinc-100 font-bold">5 chunks</span>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </motion.div>
  );
}

// ----------------------------------------------------------------------
// DomainBreakdown — Per-domain performance
// ----------------------------------------------------------------------
export function DomainBreakdown() {
  const domains = [
    {
      name: "Artificial Intelligence",
      icon: "🧠",
      metrics: { precision: 0.960, recall: 1.000, mrr: 0.975, hit: 1.000 },
    },
    {
      name: "Sustainability",
      icon: "🌍",
      metrics: { precision: 0.990, recall: 1.000, mrr: 1.000, hit: 1.000 },
    },
  ];

  return (
    <motion.div variants={item} className="mt-14">
      <h3 className="text-lg font-semibold text-zinc-200 mb-5 flex items-center gap-2">
        <svg className="w-5 h-5 text-v-emerald" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064" />
        </svg>
        Domain-Level Breakdown
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {domains.map((d) => (
          <GlassCard key={d.name} interactive solid className="p-5 border-white/5">
            <div className="flex items-center gap-2 mb-4">
              <span className="text-xl">{d.icon}</span>
              <span className="font-semibold text-zinc-200">{d.name}</span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(d.metrics).map(([key, val]) => (
                <div key={key} className="space-y-1">
                  <div className="text-[10px] uppercase tracking-wider text-zinc-500 font-medium">
                    {key === "hit" ? "Hit Rate" : key.charAt(0).toUpperCase() + key.slice(1)}@5
                  </div>
                  <div className={cn(
                    "text-lg font-mono font-bold tabular-nums",
                    val >= 1.0 ? "text-v-emerald" : "text-zinc-200"
                  )}>
                    {val.toFixed(3)}
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        ))}
      </div>
    </motion.div>
  );
}

// ----------------------------------------------------------------------
// LatencyProfile
// ----------------------------------------------------------------------
export function LatencyProfile() {
  const latencies = [
    { label: "Embedding", avg: 12, p50: 11, p95: 18, color: "bg-zinc-500" },
    { label: "FAISS + BM25", avg: 8, p50: 7, p95: 15, color: "bg-v-blue" },
    { label: "CrossEncoder", avg: 145, p50: 140, p95: 180, color: "bg-v-violet" },
    { label: "End-to-End", avg: 170, p50: 162, p95: 210, color: "bg-v-emerald" },
  ];

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
              <th className="px-5 py-3.5 font-semibold">Avg</th>
              <th className="px-5 py-3.5 font-semibold">P50</th>
              <th className="px-5 py-3.5 font-semibold">P95</th>
              <th className="px-5 py-3.5 font-semibold w-48">Distribution</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-zinc-300 font-mono text-[13px]">
            {latencies.map((l) => (
              <tr key={l.label} className="hover:bg-white/[0.02] transition-colors">
                <td className="px-5 py-3.5 font-sans font-medium text-zinc-200">{l.label}</td>
                <td className="px-5 py-3.5 tabular-nums">{l.avg}ms</td>
                <td className="px-5 py-3.5 tabular-nums text-zinc-400">{l.p50}ms</td>
                <td className="px-5 py-3.5 tabular-nums text-zinc-400">{l.p95}ms</td>
                <td className="px-5 py-3.5">
                  <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min((l.avg / 210) * 100, 100)}%` }}
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
// ScoreDistribution — Relevant vs Irrelevant score separation
// ----------------------------------------------------------------------
export function ScoreDistribution() {
  return (
    <motion.div variants={item} className="mt-14">
      <h3 className="text-lg font-semibold text-zinc-200 mb-5 flex items-center gap-2">
        <svg className="w-5 h-5 text-v-emerald" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        Score Distribution Analysis
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <GlassCard solid className="p-5 border-white/5">
          <div className="text-[10px] uppercase tracking-[0.15em] text-v-emerald font-semibold mb-3">Relevant Documents</div>
          <div className="space-y-2 font-mono text-sm">
            <div className="flex justify-between text-zinc-400">
              <span>Mean Score</span>
              <span className="text-v-emerald font-semibold">0.8942</span>
            </div>
            <div className="flex justify-between text-zinc-400">
              <span>Min Score</span>
              <span className="text-zinc-300">0.6231</span>
            </div>
            <div className="flex justify-between text-zinc-400">
              <span>Max Score</span>
              <span className="text-zinc-300">0.9876</span>
            </div>
            <div className="flex justify-between text-zinc-400">
              <span>Std Dev</span>
              <span className="text-zinc-300">0.0834</span>
            </div>
          </div>
        </GlassCard>
        <GlassCard solid className="p-5 border-white/5">
          <div className="text-[10px] uppercase tracking-[0.15em] text-zinc-500 font-semibold mb-3">Irrelevant Documents</div>
          <div className="space-y-2 font-mono text-sm">
            <div className="flex justify-between text-zinc-400">
              <span>Mean Score</span>
              <span className="text-zinc-500">0.3421</span>
            </div>
            <div className="flex justify-between text-zinc-400">
              <span>Min Score</span>
              <span className="text-zinc-500">0.0892</span>
            </div>
            <div className="flex justify-between text-zinc-400">
              <span>Max Score</span>
              <span className="text-zinc-500">0.5843</span>
            </div>
            <div className="flex justify-between text-zinc-400">
              <span>Std Dev</span>
              <span className="text-zinc-500">0.1246</span>
            </div>
          </div>
        </GlassCard>
      </div>
      <div className="mt-3 text-xs text-zinc-500 flex items-center gap-2">
        <svg className="w-3.5 h-3.5 text-v-emerald" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
        Clear score separation indicates strong discriminative retrieval — relevant documents cluster well above irrelevant ones.
      </div>
    </motion.div>
  );
}

// ----------------------------------------------------------------------
// Export Main Container
// ----------------------------------------------------------------------
export const EvalContainer = { container, item };
