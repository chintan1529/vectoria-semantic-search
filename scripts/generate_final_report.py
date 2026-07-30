"""
Final Platform Intelligence Report Generator

Pulls data from all analytics engines and generates the final markdown report.
"""
import os
import sys
from pathlib import Path
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.failure_memory import failure_memory
from backend.analytics.cache_analytics import cache_analytics
from backend.analytics.provider_analytics import provider_analytics
from backend.analytics.query_intelligence import query_intelligence
from backend.analytics.optimization_advisor import optimization_advisor

OUTPUT_DIR = Path("docs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = OUTPUT_DIR / "final_platform_intelligence_report.md"

def generate_report():
    print("Generating Final Platform Intelligence Report...")
    
    # Gather Data
    fm_stats = failure_memory.generate_report()
    cache_stats = cache_analytics.generate_report()
    prov_stats = provider_analytics.generate_report()
    query_stats = query_intelligence.generate_report()
    recommendations = optimization_advisor.generate_recommendations()
    
    # Build Markdown
    md = []
    md.append("# Vectoria: Final Platform Intelligence Report")
    md.append(f"*Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    md.append("\n## 1. Operational Summary")
    md.append("Vectoria has successfully transitioned from a static RAG pipeline to a continuously measuring, self-aware platform.")
    
    md.append("\n## 2. Quality & Reliability Trends")
    md.append("### Failure Analytics")
    md.append(f"- **Total Tracked Failures:** {fm_stats.get('total_failures', 0)}")
    
    breakdown = fm_stats.get("breakdown", {})
    for k, v in breakdown.items():
        md.append(f"  - {k.replace('_', ' ').title()}: {v}")
        
    md.append("\n### Cache Analytics")
    md.append(f"- **Total Requests:** {cache_stats.get('total_requests', 0)}")
    md.append(f"- **Hit Rate:** {cache_stats.get('hit_rate_pct', 0)}%")
    md.append(f"- **Latency Saved:** {cache_stats.get('latency_saved_ms', 0)} ms")
    md.append(f"- **Cost Saved:** ${cache_stats.get('cost_saved_usd', 0)}")
    
    md.append("\n### Provider Analytics")
    for prov, p_stats in prov_stats.items():
        md.append(f"#### {prov}")
        md.append(f"- Requests: {p_stats['total_requests']}")
        md.append(f"- Failures: {p_stats['total_failures']}")
        md.append(f"- Avg Latency: {p_stats['avg_latency_ms']} ms")
        
    md.append("\n## 3. Query Intelligence")
    md.append("### Most Frequent Queries")
    for q in query_stats.get("most_frequent", [])[:5]:
        md.append(f"- `{q['query']}` (Count: {q['count']})")
        
    md.append("\n### Highest Ambiguity Queries")
    for q in query_stats.get("most_ambiguous", [])[:5]:
        score = q['total_ambiguity_score'] / q['count'] if q['count'] else 0
        md.append(f"- `{q['query']}` (Avg Ambiguity: {score:.2f})")

    md.append("\n## 4. Automated Optimization Advisor")
    if not recommendations:
        md.append("✅ No critical optimizations recommended based on current telemetry.")
    else:
        for rec in recommendations:
            md.append(f"### [{rec['priority']}] {rec['category'].upper()} Optimization")
            md.append(f"- **Observation:** {rec['observation']}")
            md.append(f"- **Recommendation:** {rec['recommendation']}")
            
    md.append("\n## 5. Outstanding Weaknesses & Future Work")
    md.append("1. **Cross-Encoder Latency:** The CPU reranker introduces an 11s latency penalty. GPU acceleration or a lighter model (e.g. Turbo) is required for scale.")
    md.append("2. **Dataset Gold Standard:** The evaluation dataset relies on exact-chunk matching, which artificially depresses Recall@5. Transition to LLM-as-a-judge for semantic evaluation.")
    
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
        
    print(f"Report saved to {REPORT_PATH}")

if __name__ == "__main__":
    generate_report()
