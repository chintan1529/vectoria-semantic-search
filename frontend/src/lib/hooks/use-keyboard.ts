"use client";

import { useEffect } from "react";

/**
 * useKeyboard — Premium keyboard interaction hook (R3).
 *
 * Supports:
 * - "/" focuses a specified input element
 * - "Cmd+Enter" or "Ctrl+Enter" triggers a submit callback
 * - "Esc" triggers an escape callback (e.g., close inspector)
 */
export function useKeyboard({
  inputRef,
  onSubmit,
  onEscape,
}: {
  inputRef?: React.RefObject<HTMLInputElement | HTMLTextAreaElement | null>;
  onSubmit?: () => void;
  onEscape?: () => void;
}) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Avoid intercepting if user is already typing in another input (unless it's our target input)
      const isInputFocused =
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA";

      // 1. Focus input on "/"
      if (e.key === "/" && !isInputFocused) {
        e.preventDefault(); // Prevent "/" from being typed
        inputRef?.current?.focus();
      }

      // 2. Submit on Cmd+Enter or Ctrl+Enter
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
        if (onSubmit) {
          e.preventDefault();
          onSubmit();
        }
      }

      // 3. Escape to close panels
      if (e.key === "Escape") {
        if (onEscape) {
          e.preventDefault();
          onEscape();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [inputRef, onSubmit, onEscape]);
}
