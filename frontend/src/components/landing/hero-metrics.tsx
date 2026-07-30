"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { AnimatedNumber } from "@/components/ui/animated-number";
import { api } from "@/lib/api/client";
import { EvalDashboardData, PlatformStatus } from "@/lib/api/types";

export function HeroMetrics() {
  const [data, setData] = useState<{
    precision: number;
    mrr: number;
    hitRate: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadMetrics() {
      try {
        const dashboard = await api.getEvalDashboard();
        
        // Try to get metrics from rolling average, fallback to latest run
        const baselines = dashboard?.baselines?.rolling_avg || {};
        const latest = dashboard?.latest_run?.metrics || {};
        
        const mrr = baselines.mrr || latest.mrr;
        const hitRate = baselines.recall_at_5 || latest.recall_at_5; // using recall as proxy for hit rate if hit rate isn't explicitly tracked
        
        // We might not have precision tracked directly in metrics, fallback to generic
        const ndcg = baselines.ndcg_at_5 || latest.ndcg_at_5;
        
        if (mrr !== undefined && hitRate !== undefined) {
          setData({
             precision: ndcg || 0,
             mrr: mrr || 0,
             hitRate: (hitRate || 0) * 100
          });
        }
      } catch (err) {
        console.error("Failed to load hero metrics:", err);
      } finally {
        setLoading(false);
      }
    }
    loadMetrics();
  }, []);

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.8,
      },
    },
  };

  const item = {
    hidden: { opacity: 0, y: 10 },
    show: { 
      opacity: 1, 
      y: 0,
      transition: { type: "spring" as const, damping: 25 }
    },
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center mt-12 h-24">
        <div className="h-6 w-6 border-2 border-v-emerald border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  // Elegant empty state if no benchmarks exist
  if (!data) {
    return (
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.8 }}
        className="mt-12 text-center text-zinc-500 text-sm font-mono"
      >
        <div className="flex items-center justify-center gap-2 mb-1">
          <div className="h-2 w-2 rounded-full bg-v-emerald animate-pulse"></div>
          Platform Live
        </div>
        No benchmarks executed yet. Waiting for telemetry...
      </motion.div>
    );
  }

  return (
    <motion.div 
      variants={container}
      initial="hidden"
      animate="show"
      className="grid grid-cols-3 gap-4 w-full max-w-xl mx-auto mt-12"
    >
      {/* nDCG Metric (replacing Precision since it's commonly tracked) */}
      <motion.div 
        variants={item}
        className="flex flex-col items-center justify-center p-4 rounded-xl v-surface border-white/5 shadow-lg shadow-black/20"
      >
        <div className="text-3xl font-bold font-mono tracking-tight text-zinc-50 mb-1">
          <AnimatedNumber value={data.precision} format="decimal" decimals={3} />
        </div>
        <div className="text-xs font-medium uppercase tracking-wider text-zinc-500">
          nDCG@5
        </div>
      </motion.div>

      {/* MRR Metric */}
      <motion.div 
        variants={item}
        className="flex flex-col items-center justify-center p-4 rounded-xl v-surface border-white/5 shadow-lg shadow-black/20"
      >
        <div className="text-3xl font-bold font-mono tracking-tight text-zinc-50 mb-1">
          <AnimatedNumber value={data.mrr} format="decimal" decimals={3} />
        </div>
        <div className="text-xs font-medium uppercase tracking-wider text-zinc-500">
          MRR@5
        </div>
      </motion.div>

      {/* Hit Rate Metric */}
      <motion.div 
        variants={item}
        className="flex flex-col items-center justify-center p-4 rounded-xl v-surface border-white/5 shadow-lg shadow-black/20 relative overflow-hidden"
      >
        <div className="absolute inset-0 bg-v-emerald/5 mix-blend-screen" />
        <div className="text-3xl font-bold font-mono tracking-tight text-v-emerald mb-1 relative z-10">
          <AnimatedNumber value={data.hitRate} format="percentage" />
        </div>
        <div className="text-xs font-medium uppercase tracking-wider text-zinc-500 relative z-10">
          Recall@5
        </div>
      </motion.div>
    </motion.div>
  );
}
