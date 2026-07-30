"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Navbar } from "@/components/layout/navbar";
import { AnimatedBackground } from "@/components/landing/animated-background";
import { api } from "@/lib/api/client";
import { EvalDashboardData, PlatformStatus } from "@/lib/api/types";
import { 
  EvalContainer,
  EvalHero, 
  MetricsTable, 
  BenchmarkHistory,
  LatencyProfile,
  EmptyState
} from "@/components/eval/dashboard-components";

export default function EvaluatePage() {
  const [dashboardData, setDashboardData] = useState<EvalDashboardData | null>(null);
  const [platformStatus, setPlatformStatus] = useState<PlatformStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [dash, plat] = await Promise.all([
          api.getEvalDashboard(),
          api.getPlatformStatus()
        ]);
        setDashboardData(dash);
        setPlatformStatus(plat);
      } catch (err: any) {
        setError(err.message || "Failed to load telemetry.");
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  return (
    <main className="relative flex min-h-screen flex-col bg-zinc-950">
      <AnimatedBackground />
      <Navbar />
      
      <div className="flex-1 overflow-y-auto pt-24 pb-32 px-6">
        <motion.div 
          variants={EvalContainer.container}
          initial="hidden"
          animate="show"
          className="max-w-5xl mx-auto w-full"
        >
          <EvalHero />

          {loading ? (
             <div className="flex justify-center items-center py-20">
               <div className="h-8 w-8 border-2 border-v-emerald border-t-transparent rounded-full animate-spin"></div>
             </div>
          ) : error ? (
             <div className="p-6 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl font-mono text-sm text-center">
               {error}
             </div>
          ) : !dashboardData?.latest_run ? (
             <EmptyState 
               title="No Benchmarks Found" 
               message="The experiment logger is empty. Execute the evaluation pipeline to populate this dashboard." 
             />
          ) : (
             <>
               <MetricsTable data={dashboardData} />
               
               <div className="mt-16 mb-8 flex items-center">
                 <div className="h-px bg-white/10 flex-1" />
                 <div className="px-4 text-[10px] font-semibold tracking-[0.2em] uppercase text-zinc-500">
                   Deep Dive Analysis
                 </div>
                 <div className="h-px bg-white/10 flex-1" />
               </div>
               
               <BenchmarkHistory history={dashboardData.history} />
               <LatencyProfile 
                 latencyProfile={dashboardData.latency_profile} 
                 latestMetrics={dashboardData.latest_run.metrics} 
               />
             </>
          )}
        </motion.div>
      </div>
    </main>
  );
}
