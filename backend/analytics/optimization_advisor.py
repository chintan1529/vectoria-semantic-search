"""
Automated Optimization Advisor

Generates deterministic, rule-based recommendations based on metrics from:
- FailureMemory
- CacheAnalytics
- ProviderAnalytics
- QueryIntelligence

No LLM-generated advice is used. All recommendations are backed by evidence.
"""
from typing import Dict, List
from backend.core.failure_memory import failure_memory
from backend.analytics.cache_analytics import cache_analytics
from backend.analytics.provider_analytics import provider_analytics
from backend.analytics.query_intelligence import query_intelligence

class OptimizationAdvisor:
    def __init__(self):
        pass

    def generate_recommendations(self) -> List[Dict]:
        recommendations = []
        
        # 1. Cache Optimization
        cache_stats = cache_analytics.generate_report()
        hit_rate = cache_stats.get("hit_rate_pct", 0)
        total_cache_req = cache_stats.get("total_requests", 0)
        
        if total_cache_req > 50:
            if hit_rate < 10.0:
                recommendations.append({
                    "category": "cache",
                    "priority": "HIGH",
                    "observation": f"Cache hit rate is critically low ({hit_rate}%).",
                    "recommendation": "Decrease semantic similarity threshold from 0.97 to 0.95 or 0.90 to capture more variants."
                })
            elif hit_rate > 80.0:
                recommendations.append({
                    "category": "cache",
                    "priority": "LOW",
                    "observation": f"Cache hit rate is very high ({hit_rate}%).",
                    "recommendation": "Monitor for false positives. Consider increasing similarity threshold to 0.98 if users complain of generic answers."
                })

        # 2. Provider Optimization
        provider_stats = provider_analytics.generate_report()
        for p_name, p_data in provider_stats.items():
            reqs = p_data.get("total_requests", 0)
            fails = p_data.get("total_failures", 0)
            if reqs > 10:
                fail_rate = (fails / reqs) * 100
                if fail_rate > 5.0:
                    recommendations.append({
                        "category": "provider",
                        "priority": "HIGH",
                        "observation": f"Provider {p_name} has a {fail_rate:.1f}% failure rate.",
                        "recommendation": f"Route traffic away from {p_name}. Review failover logs."
                    })
                
                avg_latency = p_data.get("avg_latency_ms", 0)
                if avg_latency > 15000:
                    recommendations.append({
                        "category": "provider",
                        "priority": "MEDIUM",
                        "observation": f"Provider {p_name} has high average latency ({avg_latency}ms).",
                        "recommendation": f"Consider a faster/lighter model for {p_name} or enabling streaming chunks earlier."
                    })

        # 3. Retrieval & Prompt Optimization (via FailureMemory)
        fm_stats = failure_memory.generate_report()
        total_failures = fm_stats.get("total_failures", 0)
        breakdown = fm_stats.get("breakdown", {})
        
        if total_failures > 20:
            hallucinations = breakdown.get("hallucination", 0)
            retrieval_fails = breakdown.get("retrieval_failure", 0)
            
            if (hallucinations / total_failures) > 0.3:
                recommendations.append({
                    "category": "prompt",
                    "priority": "HIGH",
                    "observation": f"High ratio of hallucinations ({hallucinations}/{total_failures} failures).",
                    "recommendation": "Inject stricter trust guards in prompt ('NEVER guess'). Decrease generation temperature."
                })
                
            if (retrieval_fails / total_failures) > 0.4:
                recommendations.append({
                    "category": "retrieval",
                    "priority": "HIGH",
                    "observation": f"Retrieval failures dominate ({retrieval_fails}/{total_failures} failures).",
                    "recommendation": "Increase top_k context window or review chunking strategy."
                })

        return recommendations

# Singleton
optimization_advisor = OptimizationAdvisor()

if __name__ == "__main__":
    import json
    adv = OptimizationAdvisor()
    print(json.dumps(adv.generate_recommendations(), indent=2))
