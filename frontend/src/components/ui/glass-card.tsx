import { cn } from "@/lib/utils";
import { forwardRef, type HTMLAttributes } from "react";

/**
 * GlassCard — Foundational glassmorphism container.
 *
 * Two modes:
 *  - `glass` (default): backdrop-blur surface. Use sparingly — max 3-4 per view.
 *  - `solid`: opaque elevated surface. Use for lists, cards, and secondary panels.
 *
 * Glow can be applied via additional className: `v-glow-blue`, `v-glow-emerald`, etc.
 */
const GlassCard = forwardRef<
  HTMLDivElement,
  HTMLAttributes<HTMLDivElement> & { solid?: boolean }
>(({ className, solid = false, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-xl transition-colors duration-300",
      solid ? "v-surface" : "v-glass",
      className
    )}
    {...props}
  />
));

GlassCard.displayName = "GlassCard";

export { GlassCard };
