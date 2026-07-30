"use client";

import { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
import { GlassCard } from "@/components/ui/glass-card";

interface GraphData {
  nodes: { id: string; label: string; group: string }[];
  links: { source: string; target: string; label: string }[];
}

interface KnowledgeGraphProps {
  context: any[] | null;
}

export function KnowledgeGraph({ context }: KnowledgeGraphProps) {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!context || context.length === 0) return;
    
    let isMounted = true;
    
    const fetchGraph = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const texts = context.map(c => c.text);
        const res = await fetch("http://localhost:8000/api/query/knowledge-graph/extract", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ texts })
        });
        
        if (!res.ok) throw new Error("Failed to extract knowledge graph");
        
        const data = await res.json();
        if (isMounted) {
          setGraphData(data);
        }
      } catch (err: any) {
        if (isMounted) setError(err.message);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    
    fetchGraph();
    
    return () => { isMounted = false; };
  }, [context]);

  if (!context) return null;

  return (
    <GlassCard className="p-4 mt-4 border-white/5 relative min-h-[300px] flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs uppercase tracking-wider text-v-emerald font-semibold">Knowledge Graph</h3>
        {loading && (
          <div className="w-3 h-3 rounded-full border-2 border-v-emerald/50 border-t-v-emerald animate-spin" />
        )}
      </div>
      
      {error && (
        <div className="flex-1 flex items-center justify-center text-xs text-v-rose">
          {error}
        </div>
      )}
      
      {loading && !graphData && (
        <div className="flex-1 flex flex-col items-center justify-center text-xs text-zinc-500 gap-2">
          <svg className="w-6 h-6 animate-pulse text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Extracting entities from context...
        </div>
      )}
      
      {graphData && !error && (
        <GraphVisualizer data={graphData} />
      )}
    </GlassCard>
  );
}

function GraphVisualizer({ data }: { data: GraphData }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [positions, setPositions] = useState<Record<string, { x: number, y: number }>>({});
  
  useEffect(() => {
    if (!containerRef.current) return;
    const { width, height } = containerRef.current.getBoundingClientRect();
    setDimensions({ width, height });
    
    // Simple circular layout
    const numNodes = data.nodes.length;
    const radius = Math.min(width, height) / 2 - 40;
    const cx = width / 2;
    const cy = height / 2;
    
    const newPositions: Record<string, { x: number, y: number }> = {};
    data.nodes.forEach((node, i) => {
      const angle = (i / numNodes) * 2 * Math.PI;
      newPositions[node.id] = {
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle)
      };
    });
    setPositions(newPositions);
  }, [data]);

  if (dimensions.width === 0) {
    return <div ref={containerRef} className="flex-1 w-full" />;
  }

  const getGroupColor = (group: string) => {
    switch (group.toLowerCase()) {
      case 'person': return 'text-blue-400 bg-blue-400/20 border-blue-400/50';
      case 'organization': return 'text-purple-400 bg-purple-400/20 border-purple-400/50';
      case 'location': return 'text-emerald-400 bg-emerald-400/20 border-emerald-400/50';
      case 'concept': return 'text-amber-400 bg-amber-400/20 border-amber-400/50';
      case 'technology': return 'text-rose-400 bg-rose-400/20 border-rose-400/50';
      default: return 'text-zinc-300 bg-zinc-500/20 border-zinc-500/50';
    }
  };

  return (
    <div ref={containerRef} className="flex-1 w-full relative overflow-hidden bg-black/20 rounded-lg">
      <svg className="absolute inset-0 w-full h-full pointer-events-none">
        {data.links.map((link, i) => {
          const source = positions[link.source];
          const target = positions[link.target];
          if (!source || !target) return null;
          
          const midX = (source.x + target.x) / 2;
          const midY = (source.y + target.y) / 2;
          
          return (
            <g key={i}>
              <line 
                x1={source.x} y1={source.y} 
                x2={target.x} y2={target.y} 
                stroke="rgba(255,255,255,0.15)" strokeWidth={1.5}
              />
              <text x={midX} y={midY - 4} textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize="9">
                {link.label}
              </text>
            </g>
          );
        })}
      </svg>
      
      {data.nodes.map((node) => {
        const pos = positions[node.id];
        if (!pos) return null;
        
        return (
          <motion.div
            key={node.id}
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: 1, scale: 1 }}
            className={`absolute px-2 py-1 rounded text-[10px] whitespace-nowrap cursor-pointer border backdrop-blur-sm ${getGroupColor(node.group)}`}
            style={{ 
              left: pos.x, 
              top: pos.y,
              transform: 'translate(-50%, -50%)',
            }}
            title={node.group}
          >
            {node.label}
          </motion.div>
        );
      })}
    </div>
  );
}
