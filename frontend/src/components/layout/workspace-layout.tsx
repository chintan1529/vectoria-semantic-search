"use client";

import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

interface WorkspaceLayoutProps {
  mainContent: React.ReactNode;
  inspectorPanel: React.ReactNode;
  metricsSidebar: React.ReactNode;
  isInspectorOpen: boolean;
}

/**
 * WorkspaceLayout — The core grid for the /query experience.
 *
 * Responsive behavior:
 * - xl: 3 columns (main + inspector + sidebar) if inspector is open
 * - lg/md: inspector becomes a sliding drawer over the main content
 * - sm: mobile stack, sidebar hidden
 */
export function WorkspaceLayout({
  mainContent,
  inspectorPanel,
  metricsSidebar,
  isInspectorOpen,
}: WorkspaceLayoutProps) {
  return (
    <div className="flex w-full h-[calc(100vh-3.5rem)] pt-14 overflow-hidden bg-zinc-950">
      {/* 
        Main content area (Query + Pipeline + Answer)
        Transitions its width when the inspector opens on large screens
      */}
      <div 
        className={cn(
          "flex-1 overflow-y-auto px-4 sm:px-6 py-6 sm:py-8 transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]",
          isInspectorOpen ? "xl:mr-[400px] lg:mr-0" : "",
          "lg:mr-0 xl:mr-0",
          // Account for sidebar on large screens
          "lg:pr-[calc(16rem+1.5rem)]"
        )}
      >
        <div className="max-w-3xl mx-auto w-full flex flex-col gap-6 sm:gap-8 pb-20">
          {mainContent}
        </div>
      </div>

      {/* Mobile overlay backdrop when inspector is open */}
      <AnimatePresence>
        {isInspectorOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-0 bg-black/40 z-25 xl:hidden top-14"
            aria-hidden="true"
          />
        )}
      </AnimatePresence>

      {/* 
        Retrieval Inspector Panel (The Observatory)
        Slides in from the right. On XL screens, it sits beside content.
        On smaller screens, it overlays with a backdrop.
      */}
      <div
        className={cn(
          "fixed top-14 bottom-0 w-[400px] max-w-[calc(100vw-2rem)] bg-zinc-900/98 border-l border-white/8 backdrop-blur-xl z-30",
          "transition-transform duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]",
          "shadow-[-8px_0_30px_rgba(0,0,0,0.4)]",
          // Position: to the left of the sidebar on xl, overlay on smaller
          isInspectorOpen ? "translate-x-0" : "translate-x-[120%]",
          "right-0 lg:right-64"
        )}
      >
        <div className="h-full overflow-y-auto">
          {inspectorPanel}
        </div>
      </div>

      {/* 
        Telemetry Sidebar
        Fixed to the far right. Hidden on smaller screens.
      */}
      <div className="hidden lg:flex lg:flex-col fixed top-14 bottom-0 right-0 w-64 border-l border-white/5 bg-zinc-950/80 backdrop-blur-sm z-40 p-5 overflow-y-auto">
        {metricsSidebar}
      </div>
    </div>
  );
}
