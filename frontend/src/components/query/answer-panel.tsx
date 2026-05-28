"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { GlassCard } from "@/components/ui/glass-card";
import { RAGResponse, ErrorReason } from "@/lib/api/types";
import { CitationChip } from "./citation-chip";
import { QueryPhase } from "./pipeline-visualizer";

interface AnswerPanelProps {
  phase: QueryPhase;
  response: RAGResponse | null;
  error: string | ErrorReason | null;
}

export function AnswerPanel({ phase, response, error }: AnswerPanelProps) {
  // Parse answer text to inject CitationChips
  const renderTextWithCitations = (text: string) => {
    // Split by paragraphs first
    const paragraphs = text.split("\n").filter((p) => p.trim() !== "");

    return paragraphs.map((paragraph, pIdx) => {
      // Regex to find [Doc X] citations
      const citationRegex = /\[Doc (\d+)\]/g;
      const parts = [];
      let lastIndex = 0;
      let match;

      while ((match = citationRegex.exec(paragraph)) !== null) {
        // Add text before the citation
        if (match.index > lastIndex) {
          parts.push(paragraph.substring(lastIndex, match.index));
        }

        const docIdStr = match[1];
        const citationKey = `Doc ${docIdStr}`;
        const citationData = response?.citations?.[citationKey];

        // Add the citation chip
        parts.push(
          <CitationChip
            key={`${pIdx}-${match.index}`}
            id={docIdStr}
            citation={citationData}
          />
        );

        lastIndex = citationRegex.lastIndex;
      }

      // Add remaining text
      if (lastIndex < paragraph.length) {
        parts.push(paragraph.substring(lastIndex));
      }

      return (
        <motion.div
          key={pIdx}
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: pIdx * 0.1, duration: 0.4 }}
          className="mb-4 last:mb-0 leading-relaxed text-zinc-300"
        >
          {parts}
        </motion.div>
      );
    });
  };

  if (phase === "idle" || phase === "embedding" || phase === "retrieving" || phase === "reranking" || phase === "building_context") {
    return null; // Don't show anything yet
  }

  if (phase === "error") {
    return (
      <GlassCard className="p-6 border-v-rose/30 bg-v-rose/5">
        <div className="flex items-start gap-3 text-v-rose">
          <svg className="w-5 h-5 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <h3 className="font-semibold text-sm">Query Failed</h3>
            <p className="text-sm mt-1 opacity-80">{typeof error === "string" ? error : "An unexpected error occurred."}</p>
          </div>
        </div>
      </GlassCard>
    );
  }

  if (phase === "generating" && !response) {
    return (
      <GlassCard className="p-6 border-white/5">
        {/* Skeleton lines for progressive loading feel */}
        <div className="space-y-3">
          <div className="h-4 bg-zinc-800 rounded w-3/4 animate-pulse" />
          <div className="h-4 bg-zinc-800 rounded w-full animate-pulse" style={{ animationDelay: "100ms" }} />
          <div className="h-4 bg-zinc-800 rounded w-5/6 animate-pulse" style={{ animationDelay: "200ms" }} />
        </div>
      </GlassCard>
    );
  }

  if (response) {
    if (response.refused) {
      return (
        <GlassCard className="p-6 border-v-amber/30 bg-v-amber/5">
          <div className="flex items-start gap-3 text-v-amber">
            <svg className="w-5 h-5 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <h3 className="font-semibold text-sm">Generation Refused</h3>
              <p className="text-sm mt-1 opacity-80">
                The model refused to answer this query. Reason: {response.refusal_reason || "Safety filter triggered"}
              </p>
            </div>
          </div>
        </GlassCard>
      );
    }

    return (
      <GlassCard className="p-6 border-white/10 relative overflow-hidden group">
        {/* Subtle background glow for successful generation */}
        <div className="absolute inset-0 bg-gradient-to-br from-v-blue/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-1000 pointer-events-none" />
        
        <div className="relative z-10 text-[15px]">
          {renderTextWithCitations(response.answer)}
        </div>
      </GlassCard>
    );
  }

  return null;
}
