"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { GlassCard } from "@/components/ui/glass-card";

interface Props {
  children: ReactNode;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class StreamingErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("[STREAMING_RENDER_ERROR]", error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  public render() {
    if (this.state.hasError) {
      return (
        <GlassCard className="p-6 border-v-rose/40 bg-v-rose/5 my-4">
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2 text-v-rose font-semibold text-sm">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span>Streaming Synchronization Render Error</span>
            </div>

            <p className="text-xs text-zinc-300">
              {this.state.error?.message || "A component rendering exception occurred while processing the SSE stream."}
            </p>

            {process.env.NODE_ENV !== "production" && this.state.errorInfo && (
              <pre className="text-[10px] font-mono bg-black/60 p-3 rounded border border-white/10 text-zinc-400 overflow-x-auto max-h-40">
                {this.state.errorInfo.componentStack}
              </pre>
            )}

            <div className="flex items-center gap-3 mt-2">
              <button
                onClick={this.handleReset}
                className="px-3 py-1.5 rounded-lg bg-v-rose/20 hover:bg-v-rose/30 text-v-rose border border-v-rose/40 text-xs font-medium transition-colors"
              >
                Reset State & Retry
              </button>
            </div>
          </div>
        </GlassCard>
      );
    }

    return this.props.children;
  }
}
