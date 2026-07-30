"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Navbar } from "@/components/layout/navbar";
import { GlassCard } from "@/components/ui/glass-card";
import { AnimatedBackground } from "@/components/landing/animated-background";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function ResearchMode() {
  const [query, setQuery] = useState("");
  const [phase, setPhase] = useState<"idle" | "expanding" | "retrieving" | "generating" | "complete" | "error">("idle");
  const [subQueries, setSubQueries] = useState<string[]>([]);
  const [streamingText, setStreamingText] = useState("");
  const [context, setContext] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  
  const containerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [streamingText, phase, subQueries]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || phase !== "idle" && phase !== "complete" && phase !== "error") return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setPhase("expanding");
    setSubQueries([]);
    setStreamingText("");
    setContext([]);
    setError(null);

    try {
      const res = await fetch("http://localhost:8000/api/research/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
        signal: controller.signal,
      });

      if (!res.ok) throw new Error("Failed to start research");

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No reader");
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const eventStr of events) {
          const lines = eventStr.split("\n");
          let eventType = "message";
          let data = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) eventType = line.slice(7).trim();
            else if (line.startsWith("data: ")) data = line.slice(6);
          }

          if (eventType === "phase") {
            setPhase(JSON.parse(data).phase);
          } else if (eventType === "sub_queries") {
            setSubQueries(JSON.parse(data));
          } else if (eventType === "context") {
            setContext(JSON.parse(data));
          } else if (eventType === "token") {
            setStreamingText(prev => prev + JSON.parse(data));
          } else if (eventType === "done") {
            setPhase("complete");
          }
        }
      }
      setPhase(p => p !== "error" ? "complete" : p);
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setError(err.message);
        setPhase("error");
      }
    }
  };

  return (
    <>
      <AnimatedBackground />
      <Navbar />
      <main className="relative flex flex-col h-screen pt-16 px-4 pb-4 max-w-6xl mx-auto w-full z-10">
        <div className="mb-6 mt-4">
          <h1 className="text-2xl font-bold text-white mb-2 font-display tracking-tight flex items-center gap-3">
            <svg className="w-6 h-6 text-v-emerald" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
            Research Mode
          </h1>
          <p className="text-zinc-400 text-sm max-w-2xl">
            Autonomous multi-query synthesis and cross-source evidence comparison for complex investigations.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mb-6 flex gap-3">
          <div className="relative flex-1 group">
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="What would you like to investigate?"
              disabled={phase !== "idle" && phase !== "complete" && phase !== "error"}
              className="w-full bg-black/40 border border-white/10 text-white rounded-xl py-4 pl-5 pr-14 outline-none focus:border-v-emerald/50 focus:ring-1 focus:ring-v-emerald/50 transition-all shadow-inner disabled:opacity-50"
            />
          </div>
          <button
            type="submit"
            disabled={!query.trim() || (phase !== "idle" && phase !== "complete" && phase !== "error")}
            className="bg-v-emerald hover:bg-v-emerald-light text-black font-semibold px-6 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {phase === "idle" || phase === "complete" || phase === "error" ? "Start Research" : "Investigating..."}
          </button>
        </form>

        {(phase !== "idle") && (
          <div className="flex gap-6 flex-1 min-h-0">
            {/* Left Sidebar: Progress & Evidence */}
            <div className="w-80 flex flex-col gap-4 overflow-y-auto pr-2 pb-4" style={{ contain: "layout size" }}>
              <GlassCard className="p-4 border-white/5 bg-black/20">
                <h3 className="text-xs uppercase tracking-wider text-v-emerald font-semibold mb-3">Investigation Progress</h3>
                <div className="space-y-3">
                  <ProgressStep label="Multi-query Expansion" active={phase === "expanding"} done={phase !== "expanding"} />
                  <ProgressStep label="Parallel Retrieval" active={phase === "retrieving"} done={phase === "generating" || phase === "complete"} />
                  <ProgressStep label="Evidence Synthesis" active={phase === "generating"} done={phase === "complete"} />
                </div>
              </GlassCard>

              {subQueries.length > 0 && (
                <GlassCard className="p-4 border-white/5 bg-black/20">
                  <h3 className="text-xs uppercase tracking-wider text-v-blue font-semibold mb-3">Search Strategies</h3>
                  <ul className="space-y-2">
                    {subQueries.map((sq, i) => (
                      <li key={i} className="text-xs text-zinc-300 bg-white/5 p-2 rounded border border-white/5">
                        {sq}
                      </li>
                    ))}
                  </ul>
                </GlassCard>
              )}

              {context.length > 0 && (
                <GlassCard className="p-4 border-white/5 bg-black/20">
                  <h3 className="text-xs uppercase tracking-wider text-v-amber font-semibold mb-3">Unique Sources Examined</h3>
                  <div className="text-3xl font-mono text-zinc-100 mb-1">{context.length}</div>
                  <p className="text-[10px] text-zinc-500 uppercase tracking-wider">High-confidence chunks</p>
                </GlassCard>
              )}
            </div>

            {/* Right Pane: Report */}
            <GlassCard className="flex-1 p-0 border-white/5 bg-black/20 flex flex-col relative overflow-hidden">
              <div ref={containerRef} className="flex-1 overflow-y-auto p-8 relative z-10">
                {phase === "expanding" || phase === "retrieving" ? (
                  <div className="flex flex-col items-center justify-center h-full text-zinc-500 space-y-4">
                    <div className="w-8 h-8 rounded-full border-2 border-v-emerald/30 border-t-v-emerald animate-spin" />
                    <p className="text-sm tracking-wider uppercase animate-pulse">Gathering Intelligence...</p>
                  </div>
                ) : error ? (
                  <div className="text-v-rose p-4 border border-v-rose/30 bg-v-rose/10 rounded-lg">
                    {error}
                  </div>
                ) : (
                  <div className="v-prose max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingText}</ReactMarkdown>
                    {phase === "generating" && <span className="inline-block w-2 h-4 bg-v-emerald ml-1 animate-pulse" />}
                  </div>
                )}
              </div>
            </GlassCard>
          </div>
        )}
      </main>
    </>
  );
}

function ProgressStep({ label, active, done }: { label: string; active: boolean; done: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div className={`w-4 h-4 rounded-full flex items-center justify-center shrink-0 border-2 ${
        done ? "bg-v-emerald border-v-emerald text-black" : 
        active ? "border-v-emerald/50 border-t-v-emerald animate-spin" : 
        "border-zinc-700 bg-transparent"
      }`}>
        {done && <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>}
      </div>
      <span className={`text-xs ${done ? "text-zinc-300" : active ? "text-v-emerald font-medium" : "text-zinc-600"}`}>
        {label}
      </span>
    </div>
  );
}
