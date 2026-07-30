"use client";

import { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GlassCard } from "@/components/ui/glass-card";
import { useKeyboard } from "@/lib/hooks/use-keyboard";
import { cn } from "@/lib/utils";

interface QueryInputProps {
  onQuerySubmit: (query: string) => void;
  isProcessing: boolean;
  isWarming?: boolean;
}

const EXAMPLE_QUERIES = [
  "How do neural networks learn from data?",
  "What causes climate change?",
  "Explain the transformer architecture",
  "How does reinforcement learning work?",
];

export function QueryInput({ onQuerySubmit, isProcessing, isWarming = false }: QueryInputProps) {
  const [query, setQuery] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const [placeholderIdx, setPlaceholderIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Rotate placeholder text for visual interest
  const handleFocus = () => {
    setIsFocused(true);
  };

  const handleBlur = () => {
    setIsFocused(false);
    setPlaceholderIdx((prev) => (prev + 1) % EXAMPLE_QUERIES.length);
  };

  // Premium Keyboard Shortcuts
  useKeyboard({
    inputRef,
    onSubmit: () => {
      if (query.trim() && !isProcessing) {
        onQuerySubmit(query.trim());
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isProcessing) {
      onQuerySubmit(query.trim());
    }
  };

  return (
    <GlassCard 
      className={cn(
        "relative flex items-center p-2 transition-all duration-300",
        isFocused ? "v-glow-blue scale-[1.003]" : "border-white/10 hover:border-white/15",
        (isProcessing || isWarming) && "opacity-60 pointer-events-none"
      )}
    >
      <form onSubmit={handleSubmit} className="flex w-full relative items-center">
        {/* Search Icon */}
        <div className={cn(
          "pl-4 pr-2 transition-colors duration-300",
          isFocused ? "text-v-blue" : "text-zinc-500"
        )}>
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <path d="m21 21-4.3-4.3"></path>
          </svg>
        </div>

        {/* Input Field */}
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={handleFocus}
          onBlur={handleBlur}
          placeholder={isWarming ? "System warming up... Loading models & indexes" : EXAMPLE_QUERIES[placeholderIdx]}
          disabled={isProcessing || isWarming}
          className="flex-1 bg-transparent border-none outline-none text-zinc-100 placeholder:text-zinc-600 text-lg py-3 px-2 focus:ring-0"
          aria-label="Search query"
        />

        {/* Keyboard hints & Submit button */}
        <div className="pr-2 flex items-center gap-3">
          {/* '/' hint */}
          <AnimatePresence>
            {!isFocused && !query && (
              <motion.kbd
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="hidden sm:inline-flex items-center gap-1 px-2 py-1 text-[10px] font-mono text-zinc-500 bg-white/5 rounded border border-white/10 uppercase"
              >
                Press <span className="text-zinc-300">/</span>
              </motion.kbd>
            )}
          </AnimatePresence>

          {/* 'Cmd+Enter' hint (shows when typing) */}
          <AnimatePresence>
            {isFocused && query && (
              <motion.kbd
                initial={{ opacity: 0, x: 4 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 4 }}
                transition={{ duration: 0.15 }}
                className="hidden sm:inline-flex items-center gap-1 px-2 py-1 text-[10px] font-mono text-zinc-500 bg-white/5 rounded border border-white/10"
              >
                <span className="text-zinc-300">⌘</span> ↵
              </motion.kbd>
            )}
          </AnimatePresence>

          {/* Submit Button */}
          <motion.button
            type="submit"
            disabled={!query.trim() || isProcessing}
            whileTap={{ scale: 0.93 }}
            className={cn(
              "p-2.5 rounded-lg transition-all duration-300",
              query.trim() && !isProcessing
                ? "bg-v-blue text-white hover:bg-blue-400 shadow-[0_0_15px_rgba(0,112,243,0.3)] hover:shadow-[0_0_25px_rgba(0,112,243,0.4)]"
                : "bg-white/5 text-zinc-600 cursor-not-allowed"
            )}
          >
            {isProcessing ? (
              // Spinner
              <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            ) : (
              // Send Icon
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="m22 2-7 20-4-9-9-4Z"></path>
                <path d="M22 2 11 13"></path>
              </svg>
            )}
          </motion.button>
        </div>
      </form>
    </GlassCard>
  );
}
