"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { SearchResult } from "@/lib/api/types";
import { ScoreBar } from "@/components/ui/score-bar";
import { cn } from "@/lib/utils";

interface ChunkCardProps {
  result: SearchResult;
  isCited: boolean;
  citationId?: string; // e.g., "1" if it was cited as [Doc 1]
  index: number; // for stagger animation
}

export function ChunkCard({ result, isCited, citationId, index }: ChunkCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { chunk, score, rank } = result;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
      className={cn(
        "flex flex-col gap-3 p-4 rounded-xl transition-all duration-300 relative overflow-hidden group",
        isCited ? "bg-zinc-800/80 border border-v-blue/20" : "bg-zinc-900/50 border border-white/5",
        "hover:border-white/10"
      )}
    >
      {/* Background Glow if cited */}
      {isCited && (
        <div className="absolute inset-0 bg-v-blue/5 pointer-events-none" />
      )}

      {/* Header: Rank, Score, Badge */}
      <div className="flex items-center justify-between gap-3 relative z-10">
        <div className="flex items-center gap-2 flex-1">
          <span className="text-xs font-mono text-zinc-500 w-5">#{rank}</span>
          <ScoreBar score={score} className="w-24" />
        </div>

        {/* Citation Badge */}
        {isCited && (
          <span className="px-1.5 py-0.5 rounded bg-v-blue/20 border border-v-blue/30 text-v-blue text-[10px] font-mono uppercase tracking-wider shadow-[0_0_10px_rgba(59,130,246,0.2)]">
            Doc {citationId}
          </span>
        )}
      </div>

      {/* Title & Metadata */}
      <div className="relative z-10">
        <h4 className="text-sm font-semibold text-zinc-200 line-clamp-1 mb-1">
          {chunk.metadata.title}
        </h4>
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider font-mono text-zinc-500">
          <span className={cn(
            "px-1 py-0.5 rounded",
            chunk.metadata.category === "ai" ? "bg-v-blue/10 text-v-blue" : "bg-v-emerald/10 text-v-emerald"
          )}>
            {chunk.metadata.category}
          </span>
          <span>·</span>
          <span>Chunk {chunk.chunk_index}</span>
          <span>·</span>
          <span>{chunk.word_count} words</span>
        </div>
      </div>

      {/* Text Content */}
      <div className="relative z-10 text-xs leading-relaxed text-zinc-400 font-mono">
        <div className={cn("relative transition-all", !isExpanded && "line-clamp-3")}>
          "{chunk.text}"
          {!isExpanded && (
            <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-zinc-900 to-transparent" />
          )}
        </div>
        
        {/* Expand Toggle */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-2 text-[10px] uppercase tracking-wider text-v-blue hover:text-blue-400 transition-colors focus:outline-none"
        >
          {isExpanded ? "Collapse Text ↑" : "Expand Text ↓"}
        </button>
      </div>
    </motion.div>
  );
}
