"""
Quality Regression Monitor

Compares the latest benchmark run against:
- Previous Run
- Best Historical Run
- Rolling Average (Last 10 Runs)

Generates regression alerts if a metric drops by >5% relative.
"""
import sys
import os
import json
import statistics
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.experiment_logger import experiment_logger

OUTPUT_DIR = Path("data/evaluation/reports")

# Metrics where HIGHER is better
POSITIVE_METRICS = [
    "recall_at_5",
    "mrr",
    "ndcg_at_5",
    "faithfulness",
    "citation_accuracy"
]

# Metrics where LOWER is better
NEGATIVE_METRICS = [
    "hallucination_rate",
    "ttft_ms",
    "end_to_end_latency_ms"
]

def calculate_baseline(history: List[Dict]) -> Tuple[Dict, Dict, Dict]:
    """Calculates baselines from experiment history."""
    if not history:
        return {}, {}, {}
        
    previous = history[-1]["metrics"]
    
    # Best historical
    best = {}
    for m in POSITIVE_METRICS:
        vals = [run["metrics"].get(m, 0.0) for run in history if m in run["metrics"]]
        if vals:
            best[m] = max(vals)
            
    for m in NEGATIVE_METRICS:
        vals = [run["metrics"].get(m, 99999.0) for run in history if m in run["metrics"]]
        if vals:
            best[m] = min(vals)
            
    # Rolling average (last 10)
    rolling = {}
    last_10 = history[-10:]
    for m in POSITIVE_METRICS + NEGATIVE_METRICS:
        vals = [run["metrics"].get(m) for run in last_10 if run["metrics"].get(m) is not None]
        if vals:
            rolling[m] = statistics.mean(vals)
            
    return previous, best, rolling

def detect_regressions(latest: Dict, previous: Dict, best: Dict, rolling: Dict) -> List[Dict]:
    """Detect meaningful regressions (>5% relative degradation)."""
    alerts = []
    
    def check_metric(name: str, current_val: float, baseline_val: float, baseline_name: str, is_positive: bool):
        if baseline_val == 0.0:
            return
            
        if is_positive:
            # Positive metric went down?
            drop = (baseline_val - current_val) / baseline_val
            if drop >= 0.05:
                alerts.append({
                    "metric": name,
                    "baseline": baseline_name,
                    "baseline_val": round(baseline_val, 4),
                    "current_val": round(current_val, 4),
                    "degradation_pct": round(drop * 100, 2)
                })
        else:
            # Negative metric went up?
            spike = (current_val - baseline_val) / baseline_val
            if spike >= 0.05:
                alerts.append({
                    "metric": name,
                    "baseline": baseline_name,
                    "baseline_val": round(baseline_val, 4),
                    "current_val": round(current_val, 4),
                    "degradation_pct": round(spike * 100, 2)
                })

    for m in POSITIVE_METRICS:
        if m in latest:
            val = latest[m]
            if m in previous: check_metric(m, val, previous[m], "Previous Run", True)
            if m in best: check_metric(m, val, best[m], "Best Historical", True)
            if m in rolling: check_metric(m, val, rolling[m], "Rolling Avg (Last 10)", True)
            
    for m in NEGATIVE_METRICS:
        if m in latest:
            val = latest[m]
            if m in previous: check_metric(m, val, previous[m], "Previous Run", False)
            if m in best: check_metric(m, val, best[m], "Best Historical", False)
            if m in rolling: check_metric(m, val, rolling[m], "Rolling Avg (Last 10)", False)
            
    return alerts

def generate_regression_report(latest_metrics: Dict):
    """Run regression checks and output a report."""
    print("=" * 70)
    print("QUALITY REGRESSION MONITOR")
    print("=" * 70)
    
    history = experiment_logger.get_history()
    if not history:
        print("No historical data available. Baseline established.")
        return
        
    previous, best, rolling = calculate_baseline(history)
    alerts = detect_regressions(latest_metrics, previous, best, rolling)
    
    if not alerts:
        print("✅ No statistically meaningful regressions detected.")
    else:
        print("❌ REGRESSIONS DETECTED:")
        for alert in alerts:
            print(f"  - {alert['metric']}: {alert['current_val']} vs {alert['baseline']} ({alert['baseline_val']}) -> -{alert['degradation_pct']}%")
            
    # Save Report
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT_DIR / "regression_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "latest_metrics": latest_metrics,
            "baselines": {
                "previous": previous,
                "best": best,
                "rolling_avg": rolling
            },
            "alerts": alerts
        }, f, indent=2)
    print(f"\nReport saved to {report_path}")

if __name__ == "__main__":
    # Example execution (assuming a benchmark just finished and passed its metrics here)
    # In practice, the benchmark script will call generate_regression_report directly
    # or pass a JSON file path.
    dummy_latest = {
        "recall_at_5": 0.12, # Regression (Best was ~0.1375)
        "mrr": 0.07,
        "ndcg_at_5": 0.08,
        "latency_ms": 13000
    }
    generate_regression_report(dummy_latest)
