"use client";

import { useRef, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github-dark.css";
import { GlassCard } from "@/components/ui/glass-card";

interface ChatInterfaceProps {
  phase: string;
  streamingText: string;
  error?: string | null;
}

export function ChatInterface({ phase, streamingText, error }: ChatInterfaceProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [userScrolled, setUserScrolled] = useState(false);
  const lastScrollTop = useRef(0);

  // Auto-scroll to bottom unless user scrolled up
  useEffect(() => {
    if (!containerRef.current || userScrolled) return;
    const el = containerRef.current;
    el.scrollTop = el.scrollHeight;
  }, [streamingText, userScrolled]);

  // Detect user scroll-up to pause auto-scroll
  const handleScroll = () => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;

    if (el.scrollTop < lastScrollTop.current && !isAtBottom) {
      setUserScrolled(true);
    } else if (isAtBottom) {
      setUserScrolled(false);
    }
    lastScrollTop.current = el.scrollTop;
  };

  // Reset scroll state on new query
  useEffect(() => {
    if (phase === "embedding" || phase === "retrieving") {
      setUserScrolled(false);
    }
  }, [phase]);

  if (phase === "idle") return null;

  if (phase === "error") {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <GlassCard className="p-6 border-v-rose/30 bg-v-rose/5">
          <div className="flex items-start gap-3 text-v-rose">
            <svg className="w-5 h-5 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <h3 className="font-semibold text-sm">Query Failed</h3>
              <p className="text-sm mt-1 opacity-80">{error || "An unexpected error occurred."}</p>
            </div>
          </div>
        </GlassCard>
      </motion.div>
    );
  }

  const isWaitingForTokens = (phase === "embedding" || phase === "retrieving" || phase === "reranking" || phase === "building_context" || (phase === "generating" && !streamingText));
  const isStreaming = phase === "generating" && !!streamingText;
  const isComplete = phase === "complete";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <GlassCard className="p-0 border-white/8 relative overflow-hidden group">
        {/* Subtle background gradient on hover */}
        <div className="absolute inset-0 bg-gradient-to-br from-v-blue/[0.03] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-1000 pointer-events-none" />

        <div
          ref={containerRef}
          onScroll={handleScroll}
          className="relative z-10 p-6 max-h-[65vh] overflow-y-auto"
          style={{ contain: "layout style" }}
        >
          <AnimatePresence mode="wait">
            {/* Skeleton loading state */}
            {isWaitingForTokens && (
              <motion.div
                key="skeleton"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="space-y-3"
              >
                <div className="h-4 rounded w-3/4 v-shimmer" />
                <div className="h-4 rounded w-full v-shimmer" style={{ animationDelay: "200ms" }} />
                <div className="h-4 rounded w-5/6 v-shimmer" style={{ animationDelay: "400ms" }} />
                <div className="h-4 rounded w-2/3 v-shimmer" style={{ animationDelay: "600ms" }} />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Streaming / Complete text */}
          {(isStreaming || isComplete) && streamingText && (
            <div className={`v-prose max-w-none ${isStreaming ? "v-cursor" : ""}`}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                components={{
                  // Stable pre/code rendering to prevent layout shift
                  pre: ({ children, ...props }) => (
                    <pre className="not-prose bg-black/50 border border-white/8 rounded-lg p-4 my-4 overflow-x-auto text-[13px] leading-relaxed" {...props}>
                      {children}
                    </pre>
                  ),
                  code: ({ children, className, ...props }) => {
                    const isInline = !className;
                    if (isInline) {
                      return (
                        <code className="bg-white/8 border border-white/6 rounded px-1.5 py-0.5 text-[0.875em] font-medium" {...props}>
                          {children}
                        </code>
                      );
                    }
                    return <code className={className} {...props}>{children}</code>;
                  },
                  // Stable paragraph rendering
                  p: ({ children }) => (
                    <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>
                  ),
                  // Stable list rendering
                  ul: ({ children }) => (
                    <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>
                  ),
                  li: ({ children }) => (
                    <li className="leading-relaxed">{children}</li>
                  ),
                  // Stable heading rendering
                  h1: ({ children }) => (
                    <h1 className="text-xl font-bold text-zinc-100 mt-5 mb-2">{children}</h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-lg font-semibold text-zinc-100 mt-4 mb-2">{children}</h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-base font-semibold text-zinc-200 mt-3 mb-1.5">{children}</h3>
                  ),
                  blockquote: ({ children }) => (
                    <blockquote className="border-l-3 border-v-blue/40 pl-4 my-3 text-zinc-400 italic">
                      {children}
                    </blockquote>
                  ),
                  // Stable table rendering
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-3">
                      <table className="w-full text-sm border-collapse">{children}</table>
                    </div>
                  ),
                  th: ({ children }) => (
                    <th className="border border-white/10 bg-white/5 px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-zinc-400">{children}</th>
                  ),
                  td: ({ children }) => (
                    <td className="border border-white/10 px-3 py-2 text-zinc-300">{children}</td>
                  ),
                }}
              >
                {streamingText}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Scroll-to-bottom indicator */}
        {userScrolled && isStreaming && (
          <motion.button
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            onClick={() => {
              setUserScrolled(false);
              containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight, behavior: "smooth" });
            }}
            className="absolute bottom-4 right-4 z-20 p-2 rounded-full bg-zinc-800/90 border border-white/10 text-zinc-400 hover:text-white hover:bg-zinc-700/90 transition-all shadow-lg backdrop-blur-sm"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </motion.button>
        )}
      </GlassCard>
    </motion.div>
  );
}
