"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { KnowledgeGraph } from "@/components/query/knowledge-graph";

interface RetrievalIntelligenceViewProps {
  context: any;
  diagnostics: any;
}

export function RetrievalIntelligenceView({ context, diagnostics }: RetrievalIntelligenceViewProps) {
  const chunks = Array.isArray(context) ? context : (Array.isArray((context as any)?.chunks) ? (context as any).chunks : []);

  if (!diagnostics && chunks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center p-6">
        <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/8 flex items-center justify-center mb-4">
          <svg className="w-6 h-6 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
        </div>
        <p className="text-sm text-zinc-500 mb-1">No retrieval data yet</p>
        <p className="text-xs text-zinc-600">Submit a query to see retrieval intelligence</p>
      </div>
    );
  }

  const maxScore = chunks.length > 0 ? Math.max(...chunks.map((c: any) => Math.abs(c.score)), 0.001) : 1;

  return (
    <div className="p-4 space-y-6 text-sm text-zinc-300 h-full overflow-y-auto">
      {/* Query Translation */}
      {diagnostics && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <h4 className="font-semibold text-white mb-3 flex items-center gap-2 text-xs uppercase tracking-wider">
            <svg className="w-4 h-4 text-v-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Query Translation
          </h4>
          <div className="bg-white/[0.03] p-3 rounded-lg border border-white/8">
            <div className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1">Original Intent</div>
            <div className="mb-2 font-medium text-zinc-200">{diagnostics.original_query}</div>
            {diagnostics.rewritten_query && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}>
                <div className="text-[10px] uppercase tracking-wider text-zinc-500 mb-1 mt-3 pt-3 border-t border-white/5">
                  Expanded Context
                </div>
                <div className="text-v-blue font-medium">{diagnostics.rewritten_query}</div>
              </motion.div>
            )}
          </div>
        </motion.div>
      )}
      
      {/* Knowledge Graph */}
      {chunks.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          <KnowledgeGraph context={chunks} />
        </motion.div>
      )}
      
      {/* Top Sources */}
      {chunks.length > 0 && (
        <div>
          <h4 className="font-semibold text-white mb-3 flex items-center gap-2 text-xs uppercase tracking-wider">
            <svg className="w-4 h-4 text-v-emerald" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
            </svg>
            Top Sources ({chunks.length})
          </h4>
          <div className="space-y-2.5">
            {chunks.map((c: any, i: number) => {
              const normalizedScore = Math.abs(c.score) / maxScore;
              const scoreColor =
                normalizedScore >= 0.8 ? "text-v-emerald bg-v-emerald/10" :
                normalizedScore >= 0.5 ? "text-v-blue bg-v-blue/10" :
                "text-v-amber bg-v-amber/10";
              const barColor =
                normalizedScore >= 0.8 ? "bg-v-emerald" :
                normalizedScore >= 0.5 ? "bg-v-blue" :
                "bg-v-amber";

              return (
                <motion.div 
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.06, duration: 0.3 }}
                  key={i} 
                  className="bg-white/[0.03] p-3 rounded-lg border border-white/8 group hover:border-white/15 transition-all duration-200"
                >
                  {/* Header row */}
                  <div className="flex justify-between items-start mb-2 gap-2">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <span className="text-[10px] font-mono text-zinc-600 shrink-0">#{i + 1}</span>
                      <span className="font-medium text-zinc-200 text-[13px] truncate">{c.title}</span>
                    </div>
                    <span className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold tracking-wider shrink-0",
                      scoreColor
                    )}>
                      {c.score.toFixed(3)}
                    </span>
                  </div>

                  {/* Score bar */}
                  <div className="h-1 bg-zinc-800/80 rounded-full overflow-hidden mb-2">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${normalizedScore * 100}%` }}
                      transition={{ duration: 0.5, delay: i * 0.06 + 0.2, ease: "easeOut" }}
                      className={cn("h-full rounded-full", barColor)}
                    />
                  </div>

                  {/* Text preview */}
                  <p className="text-[11px] text-zinc-500 line-clamp-2 leading-relaxed group-hover:text-zinc-400 transition-colors">
                    {c.text}
                  </p>
                </motion.div>
              );
            })}
          </div>
        </div>
      )}
      
      {/* Footer stats */}
      {diagnostics && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="flex items-center justify-between text-[10px] text-zinc-500 border-t border-white/5 pt-3 font-mono"
        >
          <span>Latency: <span className="text-zinc-300">{diagnostics.retrieval_latency_ms}ms</span></span>
          <span>Results: <span className="text-zinc-300">{diagnostics.total_results}</span></span>
        </motion.div>
      )}
    </div>
  );
}
