"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

const stages = [
  { id: "query", label: "Query", type: "input" },
  { id: "embed", label: "Embedding", type: "process" },
  { id: "faiss", label: "FAISS Index", type: "process" },
  { id: "rerank", label: "CrossEncoder", type: "process" },
  { id: "answer", label: "Grounded Answer", type: "output" },
];

export function RetrievalFlow({ className }: { className?: string }) {
  // Container variant
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.3, // Sequential flow down the pipeline
        delayChildren: 1.5,   // Wait for hero to load
      },
    },
  };

  const nodeVariant = {
    hidden: { opacity: 0, scale: 0.9 },
    show: { opacity: 1, scale: 1, transition: { type: "spring" as const, damping: 20 } },
  };

  const lineVariant = {
    hidden: { height: 0, opacity: 0 },
    show: { height: 24, opacity: 1, transition: { duration: 0.4, ease: "easeInOut" as const } },
  };

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className={cn("flex flex-col items-center", className)}
    >
      {stages.map((stage, index) => (
        <div key={stage.id} className="flex flex-col items-center">
          {/* Connector Line (except for first item) */}
          {index > 0 && (
            <motion.div
              variants={lineVariant}
              className="w-px bg-gradient-to-b from-white/10 to-white/40 my-1"
            />
          )}

          {/* Node */}
          <motion.div
            variants={nodeVariant}
            className={cn(
              "flex items-center justify-center px-4 py-2 rounded-full text-xs font-mono font-medium border tracking-wide",
              stage.type === "input" && "bg-white/5 border-white/10 text-zinc-300",
              stage.type === "process" && "bg-v-blue/10 border-v-blue/30 text-v-blue shadow-[0_0_15px_rgba(59,130,246,0.15)]",
              stage.type === "output" && "bg-v-emerald/10 border-v-emerald/30 text-v-emerald shadow-[0_0_15px_rgba(16,185,129,0.15)]"
            )}
          >
            {stage.label}
          </motion.div>
        </div>
      ))}
    </motion.div>
  );
}
