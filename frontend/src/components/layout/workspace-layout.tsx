"use client";

import { cn } from "@/lib/utils";

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
 * - sm: mobile stack
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
          "flex-1 overflow-y-auto px-6 py-8 transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]",
          isInspectorOpen ? "xl:mr-[400px]" : "" // Make room for inspector on XL screens
        )}
      >
        <div className="max-w-3xl mx-auto w-full flex flex-col gap-8 pb-20">
          {mainContent}
        </div>
      </div>

      {/* 
        Retrieval Inspector Panel (The Observatory)
        Slides in from the right. On XL screens, it pushes content. On smaller screens, it overlays.
      */}
      <div
        className={cn(
          "fixed top-14 bottom-0 right-64 w-[400px] bg-zinc-900/95 border-l border-white/10 backdrop-blur-xl z-30 transition-transform duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] shadow-2xl",
          isInspectorOpen ? "translate-x-0" : "translate-x-[120%]"
        )}
      >
        <div className="h-full overflow-y-auto p-6">
          {inspectorPanel}
        </div>
      </div>

      {/* 
        Telemetry Sidebar
        Fixed to the far right. Only hidden on very small screens.
      */}
      <div className="hidden lg:block fixed top-14 bottom-0 right-0 w-64 border-l border-white/5 bg-zinc-950/50 backdrop-blur-sm z-40 p-6 overflow-y-auto">
        {metricsSidebar}
      </div>
    </div>
  );
}
