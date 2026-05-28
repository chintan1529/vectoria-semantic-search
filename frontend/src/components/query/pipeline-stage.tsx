"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export type StageState = "idle" | "active" | "complete" | "error";

interface PipelineStageProps {
  label: string;
  loadingLabel: string; // Cinematic loading message (R4)
  state: StageState;
  latencyMs?: number;
  isLast?: boolean;
}

export function PipelineStage({
  label,
  loadingLabel,
  state,
  latencyMs,
  isLast = false,
}: PipelineStageProps) {
  // Glow variants based on state
  const glowVariants = {
    idle: { opacity: 0, scale: 0.8 },
    active: { opacity: 1, scale: 1.2, transition: { repeat: Infinity, duration: 1.5, repeatType: "reverse" as const } },
    complete: { opacity: 0, scale: 1.5, transition: { duration: 0.5 } },
    error: { opacity: 0.8, scale: 1.1 },
  };

  const containerVariants = {
    idle: { opacity: 0.5, y: 0 },
    active: { opacity: 1, y: -2, transition: { type: "spring" as const, damping: 20 } },
    complete: { opacity: 1, y: 0 },
    error: { opacity: 1, x: [-2, 2, -2, 2, 0], transition: { duration: 0.4 } },
  };

  return (
    <div className="flex items-center flex-1">
      <motion.div
        variants={containerVariants}
        initial="idle"
        animate={state}
        className="flex flex-col flex-1 relative group"
      >
        {/* Node & Glow Container */}
        <div className="relative flex items-center mb-3">
          {/* Animated Glow */}
          <motion.div
            variants={glowVariants}
            className={cn(
              "absolute -inset-4 rounded-full blur-md -z-10",
              state === "active" || state === "complete" ? "bg-v-blue/30" : "",
              state === "error" ? "bg-v-rose/30" : ""
            )}
          />

          {/* Node Icon */}
          <div
            className={cn(
              "relative z-10 flex h-8 w-8 items-center justify-center rounded-full border bg-zinc-950 transition-colors duration-300 shadow-sm",
              state === "idle" && "border-zinc-700 text-zinc-600",
              state === "active" && "border-v-blue text-v-blue shadow-[0_0_10px_rgba(59,130,246,0.3)]",
              state === "complete" && "border-v-emerald text-v-emerald bg-v-emerald/10",
              state === "error" && "border-v-rose text-v-rose bg-v-rose/10"
            )}
          >
            {state === "idle" && <div className="h-2 w-2 rounded-full bg-zinc-700" />}
            
            {state === "active" && (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            )}

            {state === "complete" && (
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            )}

            {state === "error" && (
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            )}
          </div>

          {/* Connector Line (Right side) */}
          {!isLast && (
            <div className="flex-1 ml-2 mr-2 h-px relative bg-zinc-800">
              {/* Progress fill */}
              <motion.div
                initial={{ scaleX: 0 }}
                animate={{ scaleX: state === "complete" ? 1 : 0 }}
                transition={{ duration: 0.4, ease: "easeInOut" }}
                className={cn(
                  "absolute inset-0 origin-left",
                  state === "error" ? "bg-v-rose/50" : "bg-gradient-to-r from-v-emerald to-v-blue shadow-[0_0_8px_rgba(59,130,246,0.5)]"
                )}
              />
            </div>
          )}
        </div>

        {/* Labels & Telemetry */}
        <div className="flex flex-col gap-1 pr-4">
          <div className={cn(
            "text-xs font-semibold tracking-wide transition-colors duration-300",
            state === "active" ? "text-v-blue" :
            state === "complete" ? "text-zinc-300" :
            state === "error" ? "text-v-rose" : "text-zinc-600"
          )}>
            {label}
          </div>
          
          <div className="h-4">
            {state === "active" && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-[10px] text-zinc-400 italic"
              >
                {loadingLabel}
              </motion.div>
            )}
            
            {state === "complete" && latencyMs !== undefined && (
              <motion.div
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                className="inline-flex items-center gap-1 rounded bg-zinc-900/50 border border-white/5 px-1.5 py-0.5 text-[10px] font-mono text-zinc-400"
              >
                {latencyMs}ms
              </motion.div>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
}
