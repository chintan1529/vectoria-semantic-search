"""
Prompt & Context Optimization Benchmark

Phase 4: Evaluates prompt templates (Compact, Structured, Research, Trust).
Phase 5: Evaluates context window sizes (top_k = 3, 5, 7, 10).

Measures: Answer length, latency, and prompt efficiency.
NOTE: Full faithfulness/hallucination metrics require LLM-as-judge.
      This script measures structural metrics that correlate with quality.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import numpy as np
from typing import List, Dict
from pathlib import Path

DATASET_PATH = Path("data/evaluation/datasets/dataset_v1.json")
OUTPUT_DIR = Path("data/evaluation/reports")


# --- Prompt Templates ---

PROMPTS = {
    "current": (
        "You are an elite, highly intelligent AI assistant. "
        "Use the provided context to answer the user's query comprehensively and accurately. "
        "You MUST cite your sources using the exact chunk_id in this format: <cite chunk_id=\"X\"></cite> at the end of the sentence. "
        "Do NOT use [Source X] format. Use the XML citation tag so the UI can render it. "
        "If the answer is not contained in the context, state that clearly."
    ),
    "compact": (
        "Answer the query using ONLY the provided context. "
        "Cite sources as <cite chunk_id=\"X\"></cite>. "
        "Be concise. If unsupported, say so."
    ),
    "structured": (
        "You are a precise research assistant. "
        "Answer the query using ONLY the provided context. Structure your answer as:\n"
        "1. **Direct Answer**: A concise answer to the question.\n"
        "2. **Supporting Evidence**: Key details from the sources.\n"
        "3. **Limitations**: What the context does NOT cover.\n\n"
        "Cite each claim with <cite chunk_id=\"X\"></cite>. "
        "If the context is insufficient, state that explicitly."
    ),
    "research": (
        "You are an elite research analyst. "
        "Analyze the provided context to answer the query with academic rigor. "
        "Identify and synthesize insights from multiple sources. "
        "Note any contradictions or gaps in the evidence. "
        "Cite every factual claim with <cite chunk_id=\"X\"></cite>. "
        "If evidence is weak, quantify your confidence level."
    ),
    "trust": (
        "You are a trustworthy AI assistant that NEVER fabricates information. "
        "Use ONLY the provided context to answer. "
        "For each claim, cite the source with <cite chunk_id=\"X\"></cite>. "
        "If a question cannot be fully answered from context, explicitly state: "
        "'Based on available context, I can only confirm...' "
        "NEVER guess. NEVER extrapolate beyond what the sources say."
    ),
}


def load_dataset() -> List[Dict]:
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    questions = data if isinstance(data, list) else data.get("questions", [])
    return questions[:20]  # Use 20 questions for prompt study


def analyze_prompts():
    """Analyze prompt template characteristics without requiring LLM calls."""
    print("=" * 70)
    print("PROMPT & CONTEXT OPTIMIZATION BENCHMARK")
    print("=" * 70)

    dataset = load_dataset()
    print(f"Using {len(dataset)} evaluation questions")

    results = []
    for name, prompt_text in PROMPTS.items():
        # Structural analysis
        word_count = len(prompt_text.split())
        char_count = len(prompt_text)
        has_citation = "<cite" in prompt_text
        has_structure = "**" in prompt_text or "1." in prompt_text
        has_trust_guard = "NEVER" in prompt_text or "ONLY" in prompt_text

        # Token estimation (rough: 1 token ≈ 4 chars)
        estimated_tokens = char_count // 4

        result = {
            "prompt_name": name,
            "word_count": word_count,
            "char_count": char_count,
            "estimated_tokens": estimated_tokens,
            "has_citation_format": has_citation,
            "has_structured_output": has_structure,
            "has_trust_guards": has_trust_guard,
        }
        results.append(result)
        print(f"\n  {name}:")
        print(f"    Words: {word_count}, Chars: {char_count}, Est. Tokens: {estimated_tokens}")
        print(f"    Citations: {has_citation}, Structure: {has_structure}, Trust Guards: {has_trust_guard}")

    # --- Context Size Analysis ---
    print("\n" + "=" * 70)
    print("CONTEXT WINDOW SIZE ANALYSIS")
    print("=" * 70)

    from vectoria.retrieval.engine import SearchEngine
    engine = SearchEngine(use_reranker=True)
    engine.load()

    context_results = []
    for top_k in [3, 5, 7, 10]:
        print(f"\n--- top_k = {top_k} ---")
        latencies = []
        total_context_chars = []
        result_counts = []

        for q in dataset:
            engine.clear_cache()
            start = time.perf_counter()
            try:
                results_list = engine.search(q["query"], top_k=top_k)
            except Exception:
                continue
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
            result_counts.append(len(results_list))
            ctx_chars = sum(len(r.chunk.text) for r in results_list)
            total_context_chars.append(ctx_chars)

        ctx_result = {
            "top_k": top_k,
            "avg_latency_ms": float(np.mean(latencies)) if latencies else 0.0,
            "avg_context_chars": float(np.mean(total_context_chars)) if total_context_chars else 0.0,
            "avg_context_tokens_est": float(np.mean(total_context_chars)) / 4 if total_context_chars else 0.0,
            "avg_results": float(np.mean(result_counts)) if result_counts else 0.0,
            "samples": len(latencies),
        }
        context_results.append(ctx_result)
        print(f"  Avg Latency: {ctx_result['avg_latency_ms']:.1f}ms")
        print(f"  Avg Context: {ctx_result['avg_context_chars']:.0f} chars (~{ctx_result['avg_context_tokens_est']:.0f} tokens)")
        print(f"  Avg Results: {ctx_result['avg_results']:.1f}")

    # Summary
    print("\n" + "=" * 70)
    print("CONTEXT SIZE SUMMARY")
    print("=" * 70)
    print(f"{'top_k':<8} {'Latency(ms)':<14} {'Context(chars)':<16} {'~Tokens':<10} {'Results':<10}")
    print("-" * 58)
    for c in context_results:
        print(f"{c['top_k']:<8} {c['avg_latency_ms']:<14.1f} {c['avg_context_chars']:<16.0f} {c['avg_context_tokens_est']:<10.0f} {c['avg_results']:<10.1f}")

    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "prompt_analysis": results,
        "context_size_analysis": context_results,
    }
    output_path = OUTPUT_DIR / "prompt_context_benchmark.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    analyze_prompts()
