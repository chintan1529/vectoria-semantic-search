import asyncio
import json
import logging
import time
from pathlib import Path
from colorama import Fore, Style, init

from backend.core.config import settings

from backend.core.startup import state, startup_event
from backend.providers.factory import ProviderFactory
from backend.orchestration.retrieval_orchestrator import RetrievalOrchestrator
from backend.services.trust_verification_service import TrustVerificationService

init(autoreset=True)
logging.basicConfig(level=logging.WARNING)

ADVERSARIAL_DATASET = [
    {
        "category": "Hallucination Trap",
        "query": "Who is the CEO of Vectoria Inc and what is their favorite color?",
        "expected_faithfulness": 100,
        "expected_hallucination_risk": "Low"
    },
    {
        "category": "Contradictory Sources",
        "query": "Is FAISS faster than Annoy for trillion-scale vectors?",
        "expected_faithfulness": 100,
        "expected_hallucination_risk": "Low"
    }
]

async def run_adversarial_tests():
    print(f"\n{Fore.CYAN}{Style.BRIGHT}===============================================")
    print(f"VECTORIA PHASE 5: ADVERSARIAL TESTING SUITE")
    print(f"==============================================={Style.RESET_ALL}\n")
    
    print("Initializing backend state and loading FAISS indexes...")
    startup_event()
    print("State ready.\n")
    
    provider = ProviderFactory.create_chat_provider()
    retriever = RetrievalOrchestrator(provider)
    trust_service = TrustVerificationService(provider)
    
    results_report = []
    total_score = 0
    
    for i, test in enumerate(ADVERSARIAL_DATASET, 1):
        print(f"{Fore.YELLOW}Test {i}/{len(ADVERSARIAL_DATASET)}: [{test['category']}]{Style.RESET_ALL}")
        print(f"Query: {test['query']}")
        
        # 1. Retrieve
        r_start = time.perf_counter()
        results, diagnostics = await retriever.execute_retrieval(test['query'], top_k=3)
        r_ms = int((time.perf_counter() - r_start) * 1000)
        
        # 2. Generate Answer
        context_blocks = [f"[Chunk ID: {r.chunk.chunk_id}]\n{r.chunk.text}" for r in results]
        context_text = "\n\n".join(context_blocks)
        
        sys_prompt = "You are Vectoria. Answer the query based on context. Use <cite chunk_id=\"X\"></cite> for citations."
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"Query: {test['query']}\n\nContext: {context_text}"}
        ]
        
        g_start = time.perf_counter()
        gen_res = await provider.generate(messages, temperature=0.1)
        final_answer = gen_res.text
        g_ms = int((time.perf_counter() - g_start) * 1000)
        
        print(f"  Generated in {g_ms}ms (Retrieval: {r_ms}ms)")
        
        # 3. Trust Verification
        print(f"  Running Trust Verification...")
        v_start = time.perf_counter()
        verification = await trust_service.verify_trust(test['query'], results, final_answer)
        v_ms = int((time.perf_counter() - v_start) * 1000)
        
        composite_score = verification.get("composite_faithfulness_score", 0)
        total_score += composite_score
        
        color = Fore.GREEN if composite_score >= 90 else Fore.RED
        print(f"  {color}Faithfulness Score: {composite_score}/100{Style.RESET_ALL}")
        
        failed_citations = [c for c in verification.get("citations", []) if c.get("status") != "Verified"]
        if failed_citations:
            print(f"  {Fore.RED}Citation Failures:{Style.RESET_ALL} {len(failed_citations)}")
            for c in failed_citations:
                print(f"    - Chunk {c['chunk_id']}: {c['status']} ({c['reason']})")
        else:
            print(f"  {Fore.GREEN}All citations verified.{Style.RESET_ALL}")
            
        results_report.append({
            "category": test["category"],
            "query": test["query"],
            "faithfulness_score": composite_score,
            "citations_verified": len(verification.get("citations", [])) - len(failed_citations),
            "citations_failed": len(failed_citations),
            "verification_latency_ms": v_ms
        })
        print()
        
    avg_score = total_score / len(ADVERSARIAL_DATASET)
    print(f"{Fore.CYAN}{Style.BRIGHT}===============================================")
    print(f"ADVERSARIAL TESTING COMPLETE")
    print(f"Average Trust Score: {avg_score:.1f}/100")
    print(f"==============================================={Style.RESET_ALL}\n")
    
    report_path = Path("adversarial_report.json")
    with open(report_path, "w") as f:
        json.dump(results_report, f, indent=2)
    print(f"Detailed report saved to {report_path.absolute()}")

if __name__ == "__main__":
    asyncio.run(run_adversarial_tests())
