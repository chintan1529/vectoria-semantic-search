import { cn } from "@/lib/utils";

type StatusState = "online" | "degraded" | "offline";

interface StatusDotProps {
  status: StatusState;
  className?: string;
}

const colorMap: Record<StatusState, { dot: string; ping: string }> = {
  online: {
    dot: "bg-emerald-500",
    ping: "bg-emerald-400",
  },
  degraded: {
    dot: "bg-amber-500",
    ping: "bg-amber-400",
  },
  offline: {
    dot: "bg-rose-500",
    ping: "bg-rose-400",
  },
};

/**
 * StatusDot — Animated system status indicator.
 *
 * `online`   → green pulsing dot
 * `degraded` → amber pulsing dot
 * `offline`  → red static dot (no pulse — system is down)
 */
export function StatusDot({ status, className }: StatusDotProps) {
  const colors = colorMap[status];

  return (
    <span className={cn("relative flex h-2 w-2", className)}>
      {status !== "offline" && (
        <span
          className={cn(
            "absolute inline-flex h-full w-full rounded-full opacity-60 animate-ping",
            colors.ping
          )}
        />
      )}
      <span
        className={cn(
          "relative inline-flex h-2 w-2 rounded-full",
          colors.dot
        )}
      />
    </span>
  );
}
