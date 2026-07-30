"use client";

import { useState } from "react";
import { Navbar } from "@/components/layout/navbar";
import { GlassCard } from "@/components/ui/glass-card";
import { AnimatedBackground } from "@/components/landing/animated-background";

export default function RetrievalLab() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleInspect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    setLoading(true);
    setError(null);
    setData(null);
    
    try {
      const res = await fetch("http://localhost:8000/api/query/inspect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: 5 }),
      });
      
      if (!res.ok) throw new Error("Inspection failed");
      const result = await res.json();
      setData(result);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <AnimatedBackground />
      <Navbar />
      <main className="relative flex flex-col h-screen pt-20 px-6 pb-6 max-w-[1400px] mx-auto w-full z-10">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white mb-2 font-display tracking-tight flex items-center gap-3">
            <svg className="w-6 h-6 text-v-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
            Retrieval Quality Lab
          </h1>
          <p className="text-zinc-400 text-sm max-w-3xl">
            Deep inspection of the retrieval pipeline. Analyze top candidates, reranking scores, and explore why candidates were rejected by heuristic validation.
          </p>
        </div>

        <form onSubmit={handleInspect} className="mb-6 flex gap-3">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Enter query to inspect the retrieval pipeline..."
            className="w-full max-w-2xl bg-black/40 border border-white/10 text-white rounded-xl py-3 pl-5 pr-4 outline-none focus:border-v-blue/50 focus:ring-1 focus:ring-v-blue/50 transition-all shadow-inner"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="bg-v-blue hover:bg-v-blue-light text-black font-semibold px-6 rounded-xl transition-colors disabled:opacity-50"
          >
            {loading ? "Inspecting..." : "Inspect Pipeline"}
          </button>
        </form>

        {error && (
          <div className="text-v-rose bg-v-rose/10 border border-v-rose/30 p-4 rounded-xl mb-6">
            {error}
          </div>
        )}

        {data && (
          <div className="flex gap-6 flex-1 min-h-0">
            {/* Left Pane: Valid Candidates */}
            <div className="flex-1 flex flex-col gap-4 overflow-hidden">
              <h3 className="text-sm font-semibold text-v-emerald uppercase tracking-wider flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Final Reranked Context ({data.results.length})
              </h3>
              <div className="flex-1 overflow-y-auto pr-2 space-y-4">
                {data.results.map((r: any, i: number) => (
                  <GlassCard key={i} className="p-4 border-v-emerald/30 bg-v-emerald/5">
                    <div className="flex justify-between items-start mb-2">
                      <div className="font-semibold text-zinc-200">{r.title}</div>
                      <div className="text-xs font-mono bg-v-emerald/20 text-v-emerald px-2 py-1 rounded">Score: {r.score.toFixed(3)}</div>
                    </div>
                    <div className="text-xs text-zinc-500 mb-2 font-mono">ID: {r.id}</div>
                    <p className="text-sm text-zinc-300 leading-relaxed">{r.text}</p>
                  </GlassCard>
                ))}
              </div>
            </div>

            {/* Right Pane: Rejected Candidates & Diagnostics */}
            <div className="flex-1 flex flex-col gap-4 overflow-hidden">
              <div className="grid grid-cols-2 gap-4">
                <GlassCard className="p-4 border-white/5 bg-black/20">
                  <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Intent Classification</div>
                  <div className="text-lg font-semibold text-zinc-200">{data.diagnostics.query_type}</div>
                  <div className="text-[10px] text-zinc-500 mt-1">Routed Locally: {data.diagnostics.routed_locally ? "Yes" : "No"}</div>
                </GlassCard>
                <GlassCard className="p-4 border-white/5 bg-black/20">
                  <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Retrieval Latency</div>
                  <div className="text-lg font-semibold text-v-blue">{data.diagnostics.retrieval_latency_ms}ms</div>
                  <div className="text-[10px] text-zinc-500 mt-1">Validation: {data.diagnostics.validation_latency_ms}ms</div>
                </GlassCard>
              </div>

              <h3 className="text-sm font-semibold text-v-rose uppercase tracking-wider mt-2 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Rejected Candidates ({data.diagnostics.rejected_candidates?.length || 0})
              </h3>
              <div className="flex-1 overflow-y-auto pr-2 space-y-4">
                {data.diagnostics.rejected_candidates?.map((r: any, i: number) => (
                  <GlassCard key={i} className="p-4 border-v-rose/20 bg-v-rose/5">
                    <div className="flex justify-between items-start mb-2">
                      <div className="font-medium text-zinc-300">{r.title}</div>
                      <div className="text-[10px] font-mono bg-v-rose/20 text-v-rose px-1.5 py-0.5 rounded uppercase font-bold tracking-wider">
                        {r.reason}
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-xs font-mono text-zinc-500">
                      <span>Score: {r.score.toFixed(3)}</span>
                      <span>ID: {r.chunk_id.substring(0, 15)}...</span>
                    </div>
                  </GlassCard>
                ))}
                
                {(!data.diagnostics.rejected_candidates || data.diagnostics.rejected_candidates.length === 0) && (
                  <div className="text-sm text-zinc-500 text-center mt-10">
                    No candidates were rejected during validation.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
