"use client";

import { motion } from "framer-motion";
import { Navbar } from "@/components/layout/navbar";
import { AnimatedBackground } from "@/components/landing/animated-background";
import { 
  EvalContainer,
  EvalHero, 
  MetricsTable, 
  BaselineComparison, 
  RerankingStory,
  DomainBreakdown,
  LatencyProfile,
  ScoreDistribution
} from "@/components/eval/dashboard-components";

export default function EvaluatePage() {
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
          <MetricsTable />
          
          <div className="mt-16 mb-8 flex items-center">
            <div className="h-px bg-white/10 flex-1" />
            <div className="px-4 text-[10px] font-semibold tracking-[0.2em] uppercase text-zinc-500">
              Deep Dive Analysis
            </div>
            <div className="h-px bg-white/10 flex-1" />
          </div>
          
          <RerankingStory />
          <BaselineComparison />
          <DomainBreakdown />
          <LatencyProfile />
          <ScoreDistribution />
        </motion.div>
      </div>
    </main>
  );
}
