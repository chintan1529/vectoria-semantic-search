"use client";

import { motion } from "framer-motion";
import { AnimatedNumber } from "@/components/ui/animated-number";

export function HeroMetrics() {
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.8, // Wait for hero title to finish
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

  return (
    <motion.div 
      variants={container}
      initial="hidden"
      animate="show"
      className="grid grid-cols-3 gap-4 w-full max-w-xl mx-auto mt-12"
    >
      {/* Precision Metric */}
      <motion.div 
        variants={item}
        className="flex flex-col items-center justify-center p-4 rounded-xl v-surface border-white/5 shadow-lg shadow-black/20"
      >
        <div className="text-3xl font-bold font-mono tracking-tight text-zinc-50 mb-1">
          <AnimatedNumber value={0.97} format="decimal" decimals={2} />
        </div>
        <div className="text-xs font-medium uppercase tracking-wider text-zinc-500">
          Precision@5
        </div>
      </motion.div>

      {/* MRR Metric */}
      <motion.div 
        variants={item}
        className="flex flex-col items-center justify-center p-4 rounded-xl v-surface border-white/5 shadow-lg shadow-black/20"
      >
        <div className="text-3xl font-bold font-mono tracking-tight text-zinc-50 mb-1">
          <AnimatedNumber value={0.99} format="decimal" decimals={2} />
        </div>
        <div className="text-xs font-medium uppercase tracking-wider text-zinc-500">
          MRR
        </div>
      </motion.div>

      {/* Hit Rate Metric */}
      <motion.div 
        variants={item}
        className="flex flex-col items-center justify-center p-4 rounded-xl v-surface border-white/5 shadow-lg shadow-black/20 relative overflow-hidden"
      >
        {/* Subtle glow for the 100% stat */}
        <div className="absolute inset-0 bg-v-emerald/5 mix-blend-screen" />
        
        <div className="text-3xl font-bold font-mono tracking-tight text-v-emerald mb-1 relative z-10">
          <AnimatedNumber value={100} format="percentage" />
        </div>
        <div className="text-xs font-medium uppercase tracking-wider text-zinc-500 relative z-10">
          Hit@5 Rate
        </div>
      </motion.div>
    </motion.div>
  );
}
