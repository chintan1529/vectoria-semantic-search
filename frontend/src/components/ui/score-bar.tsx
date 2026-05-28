"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface ScoreBarProps {
  score: number; // 0.0 to 1.0
  className?: string;
}

export function ScoreBar({ score, className }: ScoreBarProps) {
  // Determine color based on score threshold
  const getColor = (s: number) => {
    if (s >= 0.8) return "from-v-emerald to-emerald-400";
    if (s >= 0.6) return "from-v-blue to-blue-400";
    if (s >= 0.4) return "from-v-amber to-amber-400";
    return "from-v-rose to-rose-400";
  };

  // Convert score to percentage for width
  const percentage = Math.max(0, Math.min(100, score * 100));

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="relative h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden flex-1">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 1, type: "spring", damping: 20 }}
          className={cn("absolute inset-y-0 left-0 bg-gradient-to-r rounded-full", getColor(score))}
        />
      </div>
      <div className="text-[10px] font-mono font-medium text-zinc-400 w-8 text-right tabular-nums">
        {score.toFixed(3)}
      </div>
    </div>
  );
}
