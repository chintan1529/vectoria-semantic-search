"use client";

import { useEffect, useState } from "react";
import { Command } from "cmdk";
import { Search, Settings, HelpCircle, FileText } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export function CommandPalette() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] px-4 backdrop-blur-sm bg-background/50">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="w-full max-w-xl overflow-hidden rounded-xl border border-white/10 bg-surface shadow-2xl v-glow-blue"
          >
            <Command
              className="flex w-full flex-col text-foreground"
              loop
            >
              <div className="flex items-center border-b border-white/10 px-3">
                <Search className="mr-2 h-5 w-5 text-muted-foreground" />
                <Command.Input
                  placeholder="Type a command or search..."
                  className="flex h-14 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
                  autoFocus
                />
              </div>

              <Command.List className="max-h-[300px] overflow-y-auto overflow-x-hidden p-2">
                <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
                  No results found.
                </Command.Empty>

                <Command.Group heading="Suggestions" className="text-xs text-muted-foreground font-medium mb-1 px-2">
                  <Command.Item className="flex cursor-pointer items-center rounded-md px-2 py-3 text-sm text-foreground hover:bg-white/5 aria-selected:bg-white/10 transition-colors">
                    <FileText className="mr-2 h-4 w-4" />
                    <span>Search Vectoria Index</span>
                  </Command.Item>
                  <Command.Item className="flex cursor-pointer items-center rounded-md px-2 py-3 text-sm text-foreground hover:bg-white/5 aria-selected:bg-white/10 transition-colors">
                    <Settings className="mr-2 h-4 w-4" />
                    <span>Settings</span>
                  </Command.Item>
                  <Command.Item className="flex cursor-pointer items-center rounded-md px-2 py-3 text-sm text-foreground hover:bg-white/5 aria-selected:bg-white/10 transition-colors">
                    <HelpCircle className="mr-2 h-4 w-4" />
                    <span>Documentation</span>
                  </Command.Item>
                </Command.Group>
              </Command.List>
            </Command>
          </motion.div>
          {/* Click away to close */}
          <div className="absolute inset-0 -z-10" onClick={() => setOpen(false)} />
        </div>
      )}
    </AnimatePresence>
  );
}
