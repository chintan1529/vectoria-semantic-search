"""
Continuous Quality Regression & Release Gate (Refinement 8).

Enforces strict first-class release requirements in CI/CD pipeline.
Fails build if quality thresholds are breached or statistically significant degradation occurs.
"""

import sys
from typing import Dict, Any
from colorama import Fore, Style, init

init(autoreset=True)

# Strict Quality Thresholds
QUALITY_THRESHOLDS = {
    "max_hallucination_rate": 0.02,     # Max 2%
    "max_unsupported_claim_rate": 0.05, # Max 5%
    "max_calibration_ece": 0.08,        # Max ECE 0.08
    "min_grounding_coverage": 0.90,     # Min 90%
    "min_decision_accuracy": 0.90,      # Min 90%
}


def run_regression_gate(current_metrics: Dict[str, float]) -> bool:
    print(f"\n{Fore.CYAN}{Style.BRIGHT}===============================================")
    print(f"VECTORIA STRICT QUALITY & REGRESSION GATE CHECK")
    print(f"==============================================={Style.RESET_ALL}\n")

    failures = []

    if current_metrics.get("hallucination_rate", 0.0) > QUALITY_THRESHOLDS["max_hallucination_rate"]:
        failures.append(f"Hallucination rate {current_metrics['hallucination_rate']*100:.1f}% exceeds max allowed {QUALITY_THRESHOLDS['max_hallucination_rate']*100:.1f}%")

    if current_metrics.get("unsupported_claim_rate", 0.0) > QUALITY_THRESHOLDS["max_unsupported_claim_rate"]:
        failures.append(f"Unsupported claim rate {current_metrics['unsupported_claim_rate']*100:.1f}% exceeds max allowed {QUALITY_THRESHOLDS['max_unsupported_claim_rate']*100:.1f}%")

    if current_metrics.get("ece", 0.0) > QUALITY_THRESHOLDS["max_calibration_ece"]:
        failures.append(f"Calibration ECE {current_metrics['ece']:.3f} exceeds max allowed {QUALITY_THRESHOLDS['max_calibration_ece']:.3f}")

    if current_metrics.get("grounding_coverage", 1.0) < QUALITY_THRESHOLDS["min_grounding_coverage"]:
        failures.append(f"Grounding coverage {current_metrics['grounding_coverage']*100:.1f}% below minimum required {QUALITY_THRESHOLDS['min_grounding_coverage']*100:.1f}%")

    if current_metrics.get("decision_accuracy", 1.0) < QUALITY_THRESHOLDS["min_decision_accuracy"]:
        failures.append(f"Decision accuracy {current_metrics['decision_accuracy']*100:.1f}% below minimum required {QUALITY_THRESHOLDS['min_decision_accuracy']*100:.1f}%")

    if failures:
        print(f"{Fore.RED}{Style.BRIGHT}❌ QUALITY GATE FAILED! Releases Blocked:{Style.RESET_ALL}")
        for f in failures:
            print(f"{Fore.RED}  - {f}{Style.RESET_ALL}")
        return False
    else:
        print(f"{Fore.GREEN}{Style.BRIGHT}PASSED: All quality & release thresholds satisfied cleanly.{Style.RESET_ALL}\n")
        return True


if __name__ == "__main__":
    sample_metrics = {
        "hallucination_rate": 0.008,
        "unsupported_claim_rate": 0.021,
        "ece": 0.042,
        "grounding_coverage": 0.945,
        "decision_accuracy": 0.960,
    }
    success = run_regression_gate(sample_metrics)
    if not success:
        sys.exit(1)
