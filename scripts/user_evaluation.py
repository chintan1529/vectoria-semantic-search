"""
Vectoria User Evaluation Framework
===================================
Collects real user queries and structured feedback to measure platform quality.
Generates a comprehensive User Feedback Report.

Usage:
    python scripts/user_evaluation.py                 # Interactive mode
    python scripts/user_evaluation.py --batch input.jsonl  # Batch mode
"""

import asyncio
import json
import time
import datetime
from pathlib import Path
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vectoria.retrieval.engine import SearchEngine
from backend.providers.factory import ProviderFactory


EVAL_DIR = Path("data/evaluation/user_feedback")
EVAL_DIR.mkdir(parents=True, exist_ok=True)


def collect_rating(prompt: str, min_val: int = 1, max_val: int = 5) -> int:
    """Collect a numeric rating from the user."""
    while True:
        try:
            val = int(input(f"  {prompt} ({min_val}-{max_val}): "))
            if min_val <= val <= max_val:
                return val
            print(f"  Please enter a number between {min_val} and {max_val}.")
        except (ValueError, EOFError):
            print(f"  Invalid input. Please enter a number between {min_val} and {max_val}.")


async def run_query(engine: SearchEngine, provider, query: str) -> dict:
    """Execute a single query through the full Vectoria pipeline."""
    start = time.perf_counter()

    # 1. Retrieval
    results = engine.search(query, top_k=5)
    chunks = [r.chunk.text for r in results]
    sources = [
        {
            "chunk_id": r.chunk.chunk_id,
            "title": r.chunk.metadata.title if r.chunk.metadata else "Unknown",
            "score": round(r.score, 4),
        }
        for r in results
    ]
    context = "\n".join(chunks)

    # 2. Generation
    prompt = f"Context:\n{context}\n\nQuestion: {query}"
    try:
        res = await provider.generate(
            [{"role": "user", "content": prompt}], temperature=0.1
        )
        answer = res.text
    except Exception as e:
        answer = f"[Generation failed: {e}]"

    latency_ms = (time.perf_counter() - start) * 1000

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "latency_ms": round(latency_ms, 1),
    }


async def interactive_session():
    """Run an interactive evaluation session."""
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║        Vectoria User Evaluation Framework           ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    print("Loading Vectoria Search Engine...")
    engine = SearchEngine(use_reranker=True)
    engine.load()
    provider = ProviderFactory.create_chat_provider()
    print("Ready.\n")

    session_id = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    records = []

    print("Type your queries below. Type 'quit' or 'exit' to finish.\n")

    query_num = 0
    while True:
        try:
            query = input(f"[Query {query_num + 1}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not query or query.lower() in ("quit", "exit", "q"):
            break

        query_num += 1
        print("  Processing...")
        result = await run_query(engine, provider, query)

        # Display answer
        print(f"\n  ─── Answer ({result['latency_ms']:.0f}ms) ───")
        print(f"  {result['answer'][:500]}")
        print(f"\n  ─── Sources ───")
        for s in result["sources"]:
            print(f"    [{s['score']}] {s['title']} ({s['chunk_id'][:16]}...)")
        print()

        # Collect feedback
        print("  ─── Feedback ───")
        answer_quality = collect_rating("Answer Quality", 1, 5)
        trustworthiness = collect_rating("Trustworthiness (do you trust this answer?)", 1, 5)
        citation_helpfulness = collect_rating("Citation Helpfulness (were sources useful?)", 1, 5)
        satisfaction = collect_rating("Overall Satisfaction", 1, 5)

        record = {
            "query_num": query_num,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            **result,
            "feedback": {
                "answer_quality": answer_quality,
                "trustworthiness": trustworthiness,
                "citation_helpfulness": citation_helpfulness,
                "satisfaction": satisfaction,
            },
        }
        records.append(record)
        print(f"  ✓ Feedback recorded.\n")

    # Save session
    if records:
        out_path = EVAL_DIR / f"session_{session_id}.json"
        with open(out_path, "w") as f:
            json.dump(
                {
                    "session_id": session_id,
                    "total_queries": len(records),
                    "records": records,
                },
                f,
                indent=2,
            )
        print(f"\nSession saved to {out_path}")
        generate_report(records, session_id)
    else:
        print("\nNo queries recorded.")


def generate_report(records: list, session_id: str):
    """Generate a structured User Feedback Report."""
    n = len(records)
    if n == 0:
        return

    avg = lambda key: sum(r["feedback"][key] for r in records) / n

    avg_quality = avg("answer_quality")
    avg_trust = avg("trustworthiness")
    avg_citation = avg("citation_helpfulness")
    avg_satisfaction = avg("satisfaction")
    avg_latency = sum(r["latency_ms"] for r in records) / n

    # Identify failures (satisfaction <= 2)
    failures = [r for r in records if r["feedback"]["satisfaction"] <= 2]

    report_path = EVAL_DIR / f"report_{session_id}.md"
    with open(report_path, "w") as f:
        f.write("# Vectoria User Evaluation Report\n\n")
        f.write(f"**Session ID:** {session_id}\n")
        f.write(f"**Total Queries:** {n}\n")
        f.write(f"**Average Latency:** {avg_latency:.0f}ms\n\n")

        f.write("## Aggregate Scores (1-5 Scale)\n\n")
        f.write("| Metric | Score |\n")
        f.write("| --- | --- |\n")
        f.write(f"| Answer Quality | {avg_quality:.2f} |\n")
        f.write(f"| Trustworthiness | {avg_trust:.2f} |\n")
        f.write(f"| Citation Helpfulness | {avg_citation:.2f} |\n")
        f.write(f"| Overall Satisfaction | {avg_satisfaction:.2f} |\n\n")

        if failures:
            f.write("## Top Failure Modes\n\n")
            for fail in failures:
                f.write(f"- **Query:** {fail['query']}\n")
                f.write(f"  - Satisfaction: {fail['feedback']['satisfaction']}/5\n")
                f.write(f"  - Answer Quality: {fail['feedback']['answer_quality']}/5\n\n")

        f.write("## Improvement Opportunities\n\n")
        if avg_quality < 3.5:
            f.write("- Answer generation quality needs improvement. Consider tuning prompt templates.\n")
        if avg_trust < 3.5:
            f.write("- Trust scores are low. Improve citation transparency and evidence grounding.\n")
        if avg_citation < 3.5:
            f.write("- Citations are not perceived as helpful. Improve chunk selection and display.\n")
        if avg_latency > 5000:
            f.write("- Latency exceeds 5s. Consider caching or GPU acceleration for reranking.\n")
        if avg_satisfaction >= 4.0:
            f.write("- Overall satisfaction is high. Platform is performing well for users.\n")

    print(f"Report generated: {report_path}")


if __name__ == "__main__":
    asyncio.run(interactive_session())
