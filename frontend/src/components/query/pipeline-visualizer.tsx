"use client";

import { GlassCard } from "@/components/ui/glass-card";
import { PipelineStage, StageState } from "./pipeline-stage";
import { cn } from "@/lib/utils";

// Re-export type since we might need it elsewhere
export type QueryPhase = "idle" | "classifying" | "embedding" | "retrieving" | "validating" | "reranking" | "building_context" | "generating" | "complete" | "error";

interface PipelineVisualizerProps {
  phase: QueryPhase;
  // Final measured latencies from the backend (R1)
  latencies?: {
    embedding: number;
    retrieving: number;
    reranking: number;
    generating: number;
  };
  className?: string;
}

export function PipelineVisualizer({ phase, latencies, className }: PipelineVisualizerProps) {
  // Helper to determine state for a specific pipeline stage based on the overall query phase
  const getStageState = (
    stagePhases: QueryPhase[], 
    isActive: boolean
  ): StageState => {
    if (phase === "error") return "error";
    if (phase === "complete") return "complete";
    if (isActive) return "active";
    
    // If the current phase is "past" this stage's active phase, it's complete
    const allPhases: QueryPhase[] = ["idle", "classifying", "embedding", "retrieving", "validating", "reranking", "building_context", "generating", "complete"];
    const currentIdx = allPhases.indexOf(phase);
    const stageMaxIdx = Math.max(...stagePhases.map(p => allPhases.indexOf(p)));
    
    if (currentIdx > stageMaxIdx) return "complete";
    return "idle";
  };

  return (
    <GlassCard solid className={cn("p-6 border-white/5", className)}>
      <div className="flex items-start w-full">
        <PipelineStage
          label="Classification"
          loadingLabel="Understanding intent..."
          state={getStageState(["classifying"], phase === "classifying")}
        />
        <PipelineStage
          label="Retrieval"
          loadingLabel="Searching vector space..."
          state={getStageState(["embedding", "retrieving", "reranking"], ["embedding", "retrieving", "reranking"].includes(phase))}
          latencyMs={latencies?.retrieving}
        />
        <PipelineStage
          label="Validation"
          loadingLabel="Checking grounding..."
          state={getStageState(["validating"], phase === "validating")}
        />
        <PipelineStage
          label="Generation"
          loadingLabel="Building response..."
          state={getStageState(["building_context", "generating"], phase === "building_context" || phase === "generating")}
          latencyMs={latencies?.generating}
          isLast
        />
      </div>
    </GlassCard>
  );
}
