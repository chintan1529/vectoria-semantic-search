"use client";

import { motion } from "framer-motion";
import { SearchResult } from "@/lib/api/types";
import { cn } from "@/lib/utils";

interface CitationChipProps {
  id: string; // e.g., "1"
  citation?: SearchResult; // The full citation data if available
  onClick?: () => void;
  onHoverStart?: () => void;
  onHoverEnd?: () => void;
}

export function CitationChip({ id, citation, onClick, onHoverStart, onHoverEnd }: CitationChipProps) {
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.05 }}
      onHoverStart={onHoverStart}
      onHoverEnd={onHoverEnd}
      onClick={onClick}
      className={cn(
        "inline-flex items-center justify-center relative group cursor-pointer select-none",
        "mx-1 px-1.5 py-0.5 rounded border text-[10px] font-mono font-medium tracking-wide transition-colors",
        citation
          ? "bg-v-blue/10 border-v-blue/30 text-v-blue hover:bg-v-blue/20 hover:border-v-blue/50"
          : "bg-zinc-800/50 border-zinc-700 text-zinc-400"
      )}
    >
      {/* Tooltip on Hover */}
      {citation && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max max-w-xs p-2 rounded-lg bg-zinc-900 border border-white/10 shadow-xl opacity-0 scale-95 group-hover:opacity-100 group-hover:scale-100 transition-all duration-200 pointer-events-none z-50 flex flex-col gap-1">
          <div className="font-sans text-xs font-semibold text-zinc-100 line-clamp-1">
            {citation.chunk.metadata.title}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-zinc-500 uppercase">Score: {citation.score.toFixed(3)}</span>
            <span className={cn(
              "px-1 py-0.5 rounded text-[8px] uppercase tracking-wider",
              citation.chunk.metadata.category === "ai" ? "bg-v-blue/10 text-v-blue" : "bg-v-emerald/10 text-v-emerald"
            )}>
              {citation.chunk.metadata.category}
            </span>
          </div>
        </div>
      )}

      {id}
    </motion.span>
  );
}
