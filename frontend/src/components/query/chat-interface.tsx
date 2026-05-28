"use client";

import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github-dark.css";
import { GlassCard } from "@/components/ui/glass-card";

export function ChatInterface({ phase, streamingText, error }: any) {
  if (phase === "idle" || phase === "embedding" || phase === "retrieving") return null;

  if (phase === "error") {
    return (
      <GlassCard className="p-6 border-v-rose/30 bg-v-rose/5 text-v-rose">
        <h3 className="font-semibold text-sm">Query Failed</h3>
        <p className="text-sm mt-1 opacity-80">{error}</p>
      </GlassCard>
    );
  }

  return (
    <GlassCard className="p-6 border-white/10 relative overflow-hidden group min-h-[150px]">
      {phase === "generating" && !streamingText && (
        <div className="space-y-3">
          <div className="h-4 bg-white/10 rounded w-3/4 animate-pulse" />
          <div className="h-4 bg-white/10 rounded w-full animate-pulse" style={{ animationDelay: "100ms" }} />
          <div className="h-4 bg-white/10 rounded w-5/6 animate-pulse" style={{ animationDelay: "200ms" }} />
        </div>
      )}

      {streamingText && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="prose prose-invert prose-sm max-w-none prose-pre:bg-black/50 prose-pre:border prose-pre:border-white/10">
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
            {streamingText}
          </ReactMarkdown>
        </motion.div>
      )}
    </GlassCard>
  );
}
