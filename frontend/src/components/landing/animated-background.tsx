/**
 * AnimatedBackground — Cinematic gradient orbs + dot grid.
 *
 * Performance:
 *  - Pure CSS animations (no React re-renders, no JS animation loops)
 *  - `will-change: transform` on orbs for GPU compositing
 *  - Only 3 blur surfaces (within the 3-4 limit)
 *  - Fixed position, renders once, never re-paints on scroll
 */
export function AnimatedBackground() {
  return (
    <div
      className="fixed inset-0 -z-10 overflow-hidden pointer-events-none"
      aria-hidden="true"
    >
      {/* Dot grid overlay */}
      <div className="absolute inset-0 v-dot-grid" />

      {/* Gradient orb 1 — Blue (top-left region) */}
      <div
        className="absolute -top-32 -left-32 h-[500px] w-[500px] rounded-full opacity-30 blur-[100px] animate-orb-1 will-change-transform"
        style={{
          background:
            "radial-gradient(circle, rgba(59, 130, 246, 0.4) 0%, transparent 70%)",
        }}
      />

      {/* Gradient orb 2 — Violet (bottom-right region) */}
      <div
        className="absolute -bottom-48 -right-24 h-[450px] w-[450px] rounded-full opacity-25 blur-[100px] animate-orb-2 will-change-transform"
        style={{
          background:
            "radial-gradient(circle, rgba(139, 92, 246, 0.35) 0%, transparent 70%)",
        }}
      />

      {/* Gradient orb 3 — Emerald (center-right region) */}
      <div
        className="absolute top-1/3 right-1/4 h-[350px] w-[350px] rounded-full opacity-20 blur-[100px] animate-orb-3 will-change-transform"
        style={{
          background:
            "radial-gradient(circle, rgba(16, 185, 129, 0.3) 0%, transparent 70%)",
        }}
      />

      {/* Subtle vignette at edges */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at center, transparent 50%, rgba(9, 9, 11, 0.8) 100%)",
        }}
      />
    </div>
  );
}
