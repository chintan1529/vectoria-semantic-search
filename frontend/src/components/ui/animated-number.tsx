"use client";

import { useEffect, useRef, useState } from "react";
import { useInView, useSpring } from "framer-motion";

interface AnimatedNumberProps {
  value: number;
  format?: "decimal" | "percentage" | "integer";
  decimals?: number;
  className?: string;
  delay?: number;
}

/**
 * AnimatedNumber — Smoothly interpolates to the target value using springs.
 * Only animates once it scrolls into view.
 */
export function AnimatedNumber({
  value,
  format = "integer",
  decimals = 2,
  className,
  delay = 0,
}: AnimatedNumberProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });
  const [displayValue, setDisplayValue] = useState("0");

  const spring = useSpring(0, {
    stiffness: 50,
    damping: 15,
    mass: 1,
  });

  useEffect(() => {
    if (isInView) {
      setTimeout(() => {
        spring.set(value);
      }, delay);
    }
  }, [isInView, value, spring, delay]);

  useEffect(() => {
    return spring.on("change", (latest) => {
      let formatted = "";
      if (format === "integer") {
        formatted = Math.round(latest).toLocaleString();
      } else if (format === "decimal") {
        formatted = latest.toFixed(decimals);
      } else if (format === "percentage") {
        formatted = Math.round(latest) + "%";
      }
      
      if (ref.current) {
        ref.current.textContent = formatted;
      } else {
        setDisplayValue(formatted);
      }
    });
  }, [spring, format, decimals]);

  return (
    <span ref={ref} className={className}>
      {displayValue}
    </span>
  );
}
