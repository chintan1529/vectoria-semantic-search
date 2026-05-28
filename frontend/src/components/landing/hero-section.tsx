"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { HeroMetrics } from "./hero-metrics";
import { TechStackBar } from "./tech-stack-bar";
import { RetrievalFlow } from "./retrieval-flow";

export function HeroSection() {
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15,
      },
    },
  };

  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { type: "spring" as const, damping: 25 } },
  };

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center pt-20 pb-12 px-6 overflow-hidden z-10">
      
      {/* Background Flow Visual (R6) */}
      <div className="absolute right-12 lg:right-32 top-1/2 -translate-y-1/2 hidden md:block opacity-40 pointer-events-none">
        <RetrievalFlow />
      </div>

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="w-full max-w-4xl flex flex-col items-center text-center z-10"
      >
        {/* Title */}
        <motion.h1 
          variants={item}
          className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight text-transparent bg-clip-text bg-gradient-to-br from-zinc-100 to-zinc-500 mb-6"
        >
          Neural Retrieval &<br /> Grounded Generation
        </motion.h1>

        {/* Subtitle */}
        <motion.p 
          variants={item}
          className="max-w-2xl text-lg md:text-xl text-zinc-400 mb-10 leading-relaxed"
        >
          A production-grade semantic search engine built for precision.
          Evaluate document contexts before generation, not after.
        </motion.p>

        {/* CTA */}
        <motion.div variants={item} className="flex items-center gap-6 mb-16">
          <Link
            href="/query"
            className="group relative inline-flex items-center justify-center gap-2 px-8 py-3.5 text-sm font-semibold text-white bg-zinc-900 rounded-full border border-white/10 hover:bg-zinc-800 transition-all overflow-hidden"
          >
            {/* CTA Glow */}
            <div className="absolute inset-0 bg-gradient-to-r from-v-blue/20 to-v-violet/20 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            
            <span className="relative z-10">Open Query Console</span>
            
            {/* Arrow icon */}
            <svg
              className="relative z-10 w-4 h-4 transition-transform duration-300 group-hover:translate-x-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </Link>
        </motion.div>

        {/* Metrics Grid */}
        <motion.div variants={item} className="w-full">
          <HeroMetrics />
        </motion.div>

        {/* Tech Stack */}
        <motion.div variants={item}>
          <TechStackBar />
        </motion.div>

      </motion.div>
    </div>
  );
}
