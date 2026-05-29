"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

interface CitationData {
  rank: number;
  score: number;
  chunk: {
    chunk_id: string;
    doc_id: string;
    text: string;
    metadata: {
      doc_id: string;
      source: string;
      title: string;
      category: string;
    };
    chunk_index: number;
    word_count: number;
  };
}

interface CitationChipProps {
  id: string;
  citation?: CitationData;
}

export function CitationChip({ id, citation }: CitationChipProps) {
  const [isHovered, setIsHovered] = useState(false);
  const chipRef = useRef<HTMLSpanElement>(null);

  // Confidence-based color
  const score = citation?.score ?? 0;
  const confidenceColor =
    score >= 0.8 ? "text-v-emerald bg-v-emerald/10 border-v-emerald/20 hover:border-v-emerald/40" :
    score >= 0.5 ? "text-v-blue bg-v-blue/10 border-v-blue/20 hover:border-v-blue/40" :
    "text-v-amber bg-v-amber/10 border-v-amber/20 hover:border-v-amber/40";

  const glowColor =
    score >= 0.8 ? "shadow-[0_0_8px_rgba(16,185,129,0.2)]" :
    score >= 0.5 ? "shadow-[0_0_8px_rgba(0,112,243,0.2)]" :
    "shadow-[0_0_8px_rgba(245,166,35,0.2)]";

  return (
    <span
      ref={chipRef}
      className="relative inline-block mx-0.5"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* The chip itself */}
      <motion.span
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
        className={cn(
          "inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-mono font-semibold",
          "border cursor-default transition-all duration-200",
          "select-none",
          confidenceColor,
          isHovered && glowColor
        )}
      >
        <svg className="w-3 h-3 opacity-60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        {id}
      </motion.span>

      {/* Hover popover */}
      <AnimatePresence>
        {isHovered && citation && (
          <motion.div
            initial={{ opacity: 0, y: 4, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.97 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-72 pointer-events-none"
          >
            <div className="bg-zinc-900/98 border border-white/10 rounded-lg shadow-2xl shadow-black/50 p-3 backdrop-blur-xl">
              {/* Header */}
              <div className="flex items-start justify-between mb-2 gap-2">
                <span className="text-xs font-semibold text-zinc-200 truncate flex-1">
                  {citation.chunk.metadata.title}
                </span>
                <span className={cn(
                  "text-[10px] font-mono px-1.5 py-0.5 rounded shrink-0",
                  score >= 0.8 ? "text-v-emerald bg-v-emerald/10" :
                  score >= 0.5 ? "text-v-blue bg-v-blue/10" :
                  "text-v-amber bg-v-amber/10"
                )}>
                  {score.toFixed(3)}
                </span>
              </div>

              {/* Score bar */}
              <div className="h-1 bg-zinc-800 rounded-full mb-2 overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(Math.abs(score) * 100, 100)}%` }}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                  className={cn(
                    "h-full rounded-full",
                    score >= 0.8 ? "bg-v-emerald" :
                    score >= 0.5 ? "bg-v-blue" :
                    "bg-v-amber"
                  )}
                />
              </div>

              {/* Text preview */}
              <p className="text-[11px] text-zinc-400 line-clamp-3 leading-relaxed">
                {citation.chunk.text}
              </p>

              {/* Footer */}
              <div className="flex items-center gap-3 mt-2 pt-2 border-t border-white/5 text-[10px] text-zinc-500">
                <span className="capitalize">{citation.chunk.metadata.category}</span>
                <span>•</span>
                <span>{citation.chunk.word_count} words</span>
                <span>•</span>
                <span>Rank #{citation.rank}</span>
              </div>
            </div>

            {/* Popover arrow */}
            <div className="absolute left-1/2 -translate-x-1/2 -bottom-1 w-2 h-2 bg-zinc-900 border-r border-b border-white/10 transform rotate-45" />
          </motion.div>
        )}
      </AnimatePresence>
    </span>
  );
}
