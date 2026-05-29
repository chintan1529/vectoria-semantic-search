"use client";

import { cn } from "@/lib/utils";

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  solid?: boolean;
  interactive?: boolean;
}

export function GlassCard({ children, className, solid, interactive }: GlassCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl transition-all duration-300",
        solid ? "v-surface" : "v-glass",
        interactive && [
          "hover:-translate-y-[1px]",
          "hover:shadow-[0_8px_30px_rgba(0,0,0,0.3)]",
          "focus-within:ring-1 focus-within:ring-v-blue/30",
          "active:translate-y-0 active:shadow-[0_2px_10px_rgba(0,0,0,0.2)]",
        ],
        className
      )}
    >
      {children}
    </div>
  );
}
