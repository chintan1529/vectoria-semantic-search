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
        <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] px-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20, filter: "blur(10px)" }}
            animate={{ opacity: 1, scale: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, scale: 0.95, y: -20, filter: "blur(10px)" }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="w-full max-w-xl overflow-hidden rounded-xl border border-white/10 bg-zinc-950/90 shadow-[0_0_40px_rgba(0,0,0,0.5)] v-glow-blue relative z-10"
          >
            <Command
              className="flex w-full flex-col text-foreground"
              loop
            >
              <div className="flex items-center border-b border-white/10 px-4 bg-white/[0.02]">
                <Search className="mr-3 h-5 w-5 text-v-blue" />
                <Command.Input
                  placeholder="Type a command or search..."
                  className="flex h-14 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-zinc-500 text-zinc-100 disabled:cursor-not-allowed disabled:opacity-50"
                  autoFocus
                />
                <div className="ml-auto flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 text-[10px] bg-white/10 rounded font-mono text-zinc-400">ESC</kbd>
                </div>
              </div>

              <Command.List className="max-h-[300px] overflow-y-auto overflow-x-hidden p-2">
                <Command.Empty className="py-6 text-center text-sm text-zinc-500">
                  No results found.
                </Command.Empty>

                <Command.Group heading="Suggestions" className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold mb-1 px-2 py-2">
                  <Command.Item className="group flex cursor-pointer items-center rounded-lg px-3 py-3 text-sm text-zinc-300 hover:bg-white/5 aria-selected:bg-v-blue/10 aria-selected:text-v-blue transition-colors outline-none">
                    <FileText className="mr-3 h-4 w-4 group-aria-selected:text-v-blue" />
                    <span>Search Vectoria Index</span>
                  </Command.Item>
                  <Command.Item className="group flex cursor-pointer items-center rounded-lg px-3 py-3 text-sm text-zinc-300 hover:bg-white/5 aria-selected:bg-v-blue/10 aria-selected:text-v-blue transition-colors outline-none">
                    <Settings className="mr-3 h-4 w-4 group-aria-selected:text-v-blue" />
                    <span>Settings</span>
                  </Command.Item>
                  <Command.Item className="group flex cursor-pointer items-center rounded-lg px-3 py-3 text-sm text-zinc-300 hover:bg-white/5 aria-selected:bg-v-blue/10 aria-selected:text-v-blue transition-colors outline-none">
                    <HelpCircle className="mr-3 h-4 w-4 group-aria-selected:text-v-blue" />
                    <span>Documentation</span>
                  </Command.Item>
                </Command.Group>
              </Command.List>
            </Command>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
