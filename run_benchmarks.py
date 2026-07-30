import argparse
import sys
from vectoria.retrieval.engine import SearchEngine
from vectoria.evaluation.ground_truth import ALL_QUERIES
from vectoria.evaluation.evaluator import RetrievalEvaluator, format_report

def run_benchmarks(use_reranker: bool = True, max_k: int = 10):
    print("=" * 60)
    print("  VECTORIA GOLDEN DATASET BENCHMARK")
    print("=" * 60)
    
    engine = SearchEngine(use_reranker=use_reranker)
    print("Loading Search Engine components...")
    engine.load()
    
    print(f"Starting evaluation on {len(ALL_QUERIES)} queries...")
    evaluator = RetrievalEvaluator(k_values=[1, 3, 5, 10])
    report = evaluator.evaluate(engine, ALL_QUERIES, max_k=max_k)
    
    print("\n" + format_report(report))
    
    # Save report to JSON if needed later for the dashboard
    import json
    import os
    from datetime import datetime
    
    os.makedirs("storage/evaluations", exist_ok=True)
    timestamp = datetime.now().isoformat().replace(":", "")
    report_dict = {
        "timestamp": timestamp,
        "use_reranker": use_reranker,
        "total_queries": report.total_queries,
        "total_time_ms": report.total_time_ms,
        "metrics": report.aggregate
    }
    with open(f"storage/evaluations/benchmark_{timestamp}.json", "w") as f:
        json.dump(report_dict, f, indent=2)
        
    print(f"Report saved to storage/evaluations/benchmark_{timestamp}.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Vectoria Benchmarks")
    parser.add_argument("--no-reranker", action="store_true", help="Disable reranker")
    args = parser.parse_args()
    
    run_benchmarks(use_reranker=not args.no_reranker)
