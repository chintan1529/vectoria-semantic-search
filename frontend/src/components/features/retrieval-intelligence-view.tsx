import { motion } from "framer-motion";

export function RetrievalIntelligenceView({ context, diagnostics }: any) {
  if (!diagnostics || !context) return null;

  return (
    <div className="p-4 space-y-6 text-sm text-zinc-300 h-full overflow-y-auto">
      <div>
        <h4 className="font-semibold text-white mb-2 flex items-center gap-2">
          <svg className="w-4 h-4 text-v-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Query Translation
        </h4>
        <div className="bg-white/5 p-3 rounded-lg border border-white/10 v-surface">
          <div className="text-xs text-zinc-500 mb-1">Original Intent</div>
          <div className="mb-2 font-medium">{diagnostics.original_query}</div>
          {diagnostics.rewritten_query && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}>
              <div className="text-xs text-zinc-500 mb-1 mt-3">Expanded Context</div>
              <div className="text-v-blue font-medium">{diagnostics.rewritten_query}</div>
            </motion.div>
          )}
        </div>
      </div>
      
      <div>
        <h4 className="font-semibold text-white mb-2 flex items-center gap-2">
          <svg className="w-4 h-4 text-v-emerald" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
          </svg>
          Top Sources ({context.length})
        </h4>
        <div className="space-y-3">
          {context.map((c: any, i: number) => (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              key={i} 
              className="bg-white/5 p-3 rounded-lg border border-white/10 v-surface group hover:border-v-emerald/30 transition-colors"
            >
              <div className="flex justify-between items-center mb-2">
                <span className="font-medium text-white truncate mr-2">{c.title}</span>
                <span className="text-[10px] text-v-emerald bg-v-emerald/10 px-2 py-0.5 rounded uppercase tracking-wider font-mono">
                  Score {(c.score).toFixed(3)}
                </span>
              </div>
              <p className="text-xs text-zinc-400 line-clamp-3 leading-relaxed">{c.text}</p>
            </motion.div>
          ))}
        </div>
      </div>
      
      <div className="text-xs text-zinc-500 flex justify-between border-t border-white/10 pt-4">
        <span>Latency: <span className="text-white font-mono">{diagnostics.retrieval_latency_ms}ms</span></span>
        <span>Index Nodes: <span className="text-white font-mono">{diagnostics.total_results}</span></span>
      </div>
    </div>
  );
}
