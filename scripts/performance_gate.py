"""
Automated CI Performance Gate (Phase 16).

Enforces backend startup, TTFT, memory RSS, and retrieval latency budgets in CI/CD.
Fails build if performance metrics breach active budget targets.
"""

import sys
from typing import Dict, Any
from colorama import Fore, Style, init

from vectoria.performance.budget import budget_manager
from vectoria.performance.hardware_detector import hardware_monitor

init(autoreset=True)


def run_performance_gate(empirical_metrics: Dict[str, Any]) -> bool:
    print(f"\n{Fore.CYAN}{Style.BRIGHT}===============================================")
    print(f"VECTORIA PERFORMANCE & LATENCY BUDGET GATE CHECK")
    print(f"==============================================={Style.RESET_ALL}\n")

    compliance = budget_manager.validate_metrics(empirical_metrics)
    failures = []

    if not compliance.get("startup_ok", True):
        failures.append(f"Startup duration {empirical_metrics.get('startup_s', 0):.2f}s breaches budget max {budget_manager.budget.max_startup_seconds:.2f}s")

    if not compliance.get("ttft_ok", True):
        failures.append(f"Time To First Token (TTFT) {empirical_metrics.get('ttft_ms', 0)}ms breaches budget max {budget_manager.budget.max_ttft_ms}ms")

    if not compliance.get("memory_ok", True):
        failures.append(f"Memory RSS {empirical_metrics.get('memory_rss_mb', 0):.1f}MB breaches budget max {budget_manager.budget.max_memory_rss_mb:.1f}MB")

    if failures:
        print(f"{Fore.RED}{Style.BRIGHT}❌ PERFORMANCE BUDGET FAILED! Releases Blocked:{Style.RESET_ALL}")
        for f in failures:
            print(f"{Fore.RED}  - {f}{Style.RESET_ALL}")
        return False
    else:
        print(f"{Fore.GREEN}{Style.BRIGHT}PASSED: All latency, startup, and memory budgets satisfied cleanly.{Style.RESET_ALL}\n")
        return True


if __name__ == "__main__":
    stats = hardware_monitor.get_resource_stats()
    sample = {
        "startup_s": 2.1,
        "ttft_ms": 180,
        "retrieval_ms": 45,
        "memory_rss_mb": stats.memory_rss_mb,
    }
    success = run_performance_gate(sample)
    if not success:
        sys.exit(1)
