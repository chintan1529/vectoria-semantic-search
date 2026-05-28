"use client";

import { motion } from "framer-motion";
import { GlassCard } from "@/components/ui/glass-card";

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
      <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-zinc-100 mb-4">
        Evaluation Suite Results
      </h1>
      <p className="text-lg text-zinc-400 max-w-2xl leading-relaxed">
        Performance metrics run against 40 human-curated ground truth queries. 
        Tests vector search (FAISS) coupled with cross-encoder reranking.
      </p>
    </motion.div>
  );
}

// ----------------------------------------------------------------------
// MetricsTable
// ----------------------------------------------------------------------
export function MetricsTable() {
  const metrics = [
    { label: "Precision@5", value: "0.975", desc: "Fraction of top 5 that are relevant" },
    { label: "Recall@5", value: "1.000", desc: "Fraction of all relevant found in top 5" },
    { label: "MRR", value: "0.988", desc: "Mean Reciprocal Rank of first relevant" },
    { label: "Hit Rate", value: "100%", desc: "Queries with ≥1 relevant chunk in top 5" },
  ];

  return (
    <motion.div variants={item}>
      <h3 className="text-xl font-semibold text-zinc-200 mb-6 flex items-center gap-2">
        <svg className="w-5 h-5 text-v-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        Aggregate System Performance
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {metrics.map((m) => (
          <GlassCard key={m.label} solid className="p-5 flex flex-col justify-between h-32 border-white/5 hover:border-v-blue/30 transition-colors">
            <div className="text-xs font-medium uppercase tracking-wider text-zinc-500">{m.label}</div>
            <div>
              <div className="text-3xl font-mono font-bold text-zinc-100 mb-1">{m.value}</div>
              <div className="text-[10px] text-zinc-600 leading-tight">{m.desc}</div>
            </div>
          </GlassCard>
        ))}
      </div>
    </motion.div>
  );
}

// ----------------------------------------------------------------------
// BaselineComparison
// ----------------------------------------------------------------------
export function BaselineComparison() {
  return (
    <motion.div variants={item} className="mt-16">
      <h3 className="text-xl font-semibold text-zinc-200 mb-6 flex items-center gap-2">
        <svg className="w-5 h-5 text-v-amber" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
        </svg>
        Baseline Comparison: Neural vs BM25
      </h3>
      <GlassCard className="overflow-hidden border-white/5">
        <table className="w-full text-sm text-left">
          <thead className="bg-zinc-900/50 text-xs uppercase tracking-wider text-zinc-500 font-mono border-b border-white/5">
            <tr>
              <th className="px-6 py-4 font-medium">Metric</th>
              <th className="px-6 py-4 font-medium">Vectoria (Neural)</th>
              <th className="px-6 py-4 font-medium">BM25 (Lexical)</th>
              <th className="px-6 py-4 font-medium">Delta</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-zinc-300 font-mono">
            <tr className="hover:bg-white/[0.02] transition-colors">
              <td className="px-6 py-4 font-sans font-medium text-zinc-200">Hit Rate</td>
              <td className="px-6 py-4 text-v-emerald">100.0%</td>
              <td className="px-6 py-4">92.5%</td>
              <td className="px-6 py-4 text-v-emerald">+ 7.5%</td>
            </tr>
            <tr className="hover:bg-white/[0.02] transition-colors">
              <td className="px-6 py-4 font-sans font-medium text-zinc-200">MRR</td>
              <td className="px-6 py-4 text-v-emerald">0.988</td>
              <td className="px-6 py-4">0.710</td>
              <td className="px-6 py-4 text-v-emerald">+ 0.278</td>
            </tr>
            <tr className="hover:bg-white/[0.02] transition-colors">
              <td className="px-6 py-4 font-sans font-medium text-zinc-200">Precision@5</td>
              <td className="px-6 py-4 text-v-emerald">0.975</td>
              <td className="px-6 py-4">0.685</td>
              <td className="px-6 py-4 text-v-emerald">+ 0.290</td>
            </tr>
          </tbody>
        </table>
      </GlassCard>
    </motion.div>
  );
}

// ----------------------------------------------------------------------
// RerankingStory (R5)
// ----------------------------------------------------------------------
export function RerankingStory() {
  return (
    <motion.div variants={item} className="mt-16">
      <div className="flex flex-col md:flex-row gap-8">
        <div className="flex-1">
          <h3 className="text-xl font-semibold text-zinc-200 mb-4 flex items-center gap-2">
            <svg className="w-5 h-5 text-v-violet" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Why Reranking Matters
          </h3>
          <p className="text-zinc-400 text-sm leading-relaxed mb-6">
            Vector search (FAISS) excels at finding <em>broadly similar</em> concepts, but often struggles with exact intent matching. 
            By passing the top 20 FAISS results through a Cross-Encoder, we achieve a massive boost in precision.
          </p>
          
          <div className="space-y-3">
            <div className="flex items-center gap-4 text-sm">
              <div className="w-32 font-mono text-zinc-500">FAISS Only MRR:</div>
              <div className="flex-1 h-2 bg-zinc-800 rounded-full overflow-hidden">
                <div className="h-full bg-zinc-600 w-[84%]" />
              </div>
              <div className="w-12 font-mono text-zinc-300">0.842</div>
            </div>
            
            <div className="flex items-center gap-4 text-sm">
              <div className="w-32 font-mono text-v-violet">Reranked MRR:</div>
              <div className="flex-1 h-2 bg-zinc-800 rounded-full overflow-hidden relative">
                <div className="absolute inset-y-0 left-0 bg-zinc-600 w-[84%]" />
                {/* The delta boost */}
                <div className="absolute inset-y-0 left-[84%] bg-v-violet w-[14.8%] shadow-[0_0_10px_rgba(139,92,246,0.5)]" />
              </div>
              <div className="w-12 font-mono font-bold text-v-violet">0.988</div>
            </div>
          </div>
        </div>
        
        <div className="flex-1 flex items-center justify-center">
          <GlassCard solid className="p-6 w-full max-w-sm border-v-violet/20 bg-v-violet/5">
            <h4 className="text-xs uppercase tracking-widest text-v-violet font-semibold mb-4">Pipeline Architecture</h4>
            <div className="space-y-2 font-mono text-xs">
              <div className="flex justify-between p-2 rounded bg-zinc-900 border border-white/5">
                <span className="text-zinc-400">Corpus Size</span>
                <span className="text-zinc-200">3,592 chunks</span>
              </div>
              <div className="flex justify-center text-zinc-600 text-[10px]">↓ FAISS top_k=20</div>
              <div className="flex justify-between p-2 rounded bg-zinc-900 border border-white/5">
                <span className="text-zinc-400">Recall Pool</span>
                <span className="text-zinc-200">20 chunks</span>
              </div>
              <div className="flex justify-center text-v-violet text-[10px] font-bold">↓ Cross-Encoder top_k=5</div>
              <div className="flex justify-between p-2 rounded bg-v-violet/10 border border-v-violet/30 shadow-[0_0_15px_rgba(139,92,246,0.15)]">
                <span className="text-v-violet">Final Context</span>
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
// Export Main Container
// ----------------------------------------------------------------------
export const EvalContainer = { container, item };
