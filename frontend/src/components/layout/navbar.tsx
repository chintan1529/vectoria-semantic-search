"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useSystemStatus } from "@/lib/hooks/use-system-status";
import { StatusDot } from "@/components/ui/status-dot";

export function Navbar() {
  const pathname = usePathname();
  const status = useSystemStatus();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex h-14 items-center justify-between px-6 lg:px-12 v-glass rounded-none border-t-0 border-x-0 border-b border-white/5 bg-zinc-950/60">
      <div className="flex items-center gap-8">
        <Link 
          href="/" 
          className="flex items-center gap-2 text-zinc-50 font-semibold tracking-tight transition-opacity hover:opacity-80"
        >
          <div className="flex size-6 items-center justify-center rounded bg-v-blue/20 text-v-blue shadow-[0_0_12px_rgba(59,130,246,0.3)]">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polygon points="12 2 2 7 12 12 22 7 12 2" />
              <polyline points="2 17 12 22 22 17" />
              <polyline points="2 12 12 17 22 12" />
            </svg>
          </div>
          Vectoria
        </Link>

        <div className="hidden md:flex items-center gap-1 text-sm font-medium text-zinc-400">
          <Link
            href="/query"
            className={cn(
              "px-3 py-1.5 rounded-md transition-colors",
              pathname === "/query" 
                ? "text-zinc-50 bg-white/5" 
                : "hover:text-zinc-100 hover:bg-white/5"
            )}
          >
            Workspace
          </Link>
          <Link
            href="/evaluate"
            className={cn(
              "px-3 py-1.5 rounded-md transition-colors",
              pathname === "/evaluate" 
                ? "text-zinc-50 bg-white/5" 
                : "hover:text-zinc-100 hover:bg-white/5"
            )}
          >
            Evaluation
          </Link>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-900/50 border border-white/5 text-xs font-mono text-zinc-400">
          <StatusDot status={status} />
          <span className="uppercase tracking-wider">
            {status === "online" ? "System Online" : status === "degraded" ? "Degraded" : "System Offline"}
          </span>
        </div>
        
        <div className="text-xs font-mono text-zinc-500 bg-zinc-900/50 px-2 py-1 rounded border border-white/5">
          v0.1.0
        </div>
      </div>
    </nav>
  );
}
