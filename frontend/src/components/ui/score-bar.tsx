"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface ScoreBarProps {
  score: number;
  maxScore?: number;
  showLabel?: boolean;
  size?: "sm" | "md";
  className?: string;
}

export function ScoreBar({ score, maxScore = 1, showLabel = true, size = "md", className }: ScoreBarProps) {
  const normalized = Math.min(Math.abs(score) / Math.abs(maxScore || 1), 1);
  
  const color =
    normalized >= 0.8 ? "bg-v-emerald" :
    normalized >= 0.5 ? "bg-v-blue" :
    normalized >= 0.3 ? "bg-v-amber" :
    "bg-zinc-600";

  const glowColor =
    normalized >= 0.8 ? "shadow-[0_0_6px_rgba(16,185,129,0.3)]" :
    normalized >= 0.5 ? "shadow-[0_0_6px_rgba(0,112,243,0.3)]" :
    "";

  const height = size === "sm" ? "h-1" : "h-1.5";

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className={cn("flex-1 bg-zinc-800 rounded-full overflow-hidden", height)}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${normalized * 100}%` }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className={cn("h-full rounded-full", color, glowColor)}
        />
      </div>
      {showLabel && (
        <span className={cn(
          "text-[10px] font-mono tabular-nums shrink-0",
          normalized >= 0.8 ? "text-v-emerald" :
          normalized >= 0.5 ? "text-v-blue" :
          normalized >= 0.3 ? "text-v-amber" :
          "text-zinc-500"
        )}>
          {score.toFixed(3)}
        </span>
      )}
    </div>
  );
}
