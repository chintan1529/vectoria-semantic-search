"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export function Navbar() {
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);

  // Track scroll to add subtle border glow
  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  const navLinks = [
    { href: "/", label: "Home" },
    { href: "/query", label: "Query Console" },
    { href: "/evaluate", label: "Evaluation" },
  ];

  return (
    <nav
      className={cn(
        "fixed top-0 left-0 right-0 z-50 h-14 flex items-center px-6 transition-all duration-500",
        "bg-zinc-950/80 backdrop-blur-xl border-b",
        scrolled
          ? "border-white/10 shadow-[0_1px_20px_rgba(0,0,0,0.3)]"
          : "border-transparent"
      )}
    >
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2.5 mr-8 group">
        <div className="relative">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-zinc-100 to-zinc-400 flex items-center justify-center shadow-[0_0_10px_rgba(255,255,255,0.1)] group-hover:shadow-[0_0_15px_rgba(255,255,255,0.2)] transition-shadow duration-300">
            <span className="text-xs font-black text-zinc-900 tracking-tighter">V</span>
          </div>
        </div>
        <span className="text-sm font-bold tracking-wide text-zinc-100 hidden sm:inline">
          VECTORIA
        </span>
      </Link>

      {/* Navigation Links */}
      <div className="flex items-center gap-1">
        {navLinks.map((link) => {
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "relative px-3 py-1.5 text-[13px] font-medium rounded-md transition-colors duration-200",
                isActive
                  ? "text-zinc-100"
                  : "text-zinc-500 hover:text-zinc-300 hover:bg-white/5"
              )}
            >
              {link.label}
              {/* Active indicator */}
              {isActive && (
                <motion.div
                  layoutId="nav-active"
                  className="absolute inset-0 bg-white/8 rounded-md -z-10"
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                />
              )}
            </Link>
          );
        })}
      </div>

      {/* Right side: Status */}
      <div className="ml-auto flex items-center gap-4">
        <div className="hidden sm:flex items-center gap-2 text-[11px] text-zinc-500 font-mono">
          <div className="h-1.5 w-1.5 rounded-full bg-v-emerald animate-pulse" />
          <span>v2.0</span>
        </div>
      </div>
    </nav>
  );
}
