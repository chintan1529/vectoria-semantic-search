import asyncio
import time
from colorama import Fore, Style, init

init(autoreset=True)

# 100 queries to be generated or sampled from a standard list.
import random

BASE_PROMPTS = [
    "Explain semantic search.",
    "What is the difference between RAG and fine-tuning?",
    "How does FAISS indexing work?",
    "Write a short python snippet for a REST API.",
    "Summarize the history of artificial intelligence in three sentences.",
    "What is a vector database?",
    "Explain the attention mechanism in Transformers.",
    "Describe what hallucination means in LLMs.",
    "How do embeddings represent text?",
    "What is the chunking strategy in RAG?",
]

def generate_queries(count: int):
    # Just sample base prompts
    queries = []
    for i in range(count):
        queries.append(random.choice(BASE_PROMPTS) + f" (Run {i})")
    return queries

from backend.providers.factory import ProviderFactory
from backend.core.config import settings

MODELS_TO_TEST = [
    "Qwen/Qwen2.5-7B-Instruct",
    "Qwen/Qwen2.5-3B-Instruct",
    "microsoft/Phi-3-mini-4k-instruct",
    "mistralai/Mistral-7B-Instruct"
]

async def benchmark_hf_model(model_name: str, queries: list, stage_name: str):
    settings.vectoria_hf_model = model_name
    provider = ProviderFactory._create_provider_instance("huggingface")
    
    if not provider:
        print(f"{Fore.RED}[{stage_name}] Failed to init {model_name}")
        return None
        
    if not await provider.health_check():
        print(f"{Fore.RED}[{stage_name}] {model_name} is UNHEALTHY or unavailable via serverless api.")
        return None
        
    print(f"\n{Fore.CYAN}--- [{stage_name}] Benchmarking {model_name} ({len(queries)} Queries) ---")
    
    results = []
    
    for i, prompt in enumerate(queries):
        messages = [{"role": "user", "content": prompt}]
        start_time = time.perf_counter()
        first_token_time = None
        token_count = 0
        success = False
        error_type = None
        
        try:
            # We use a short timeout for reliability testing
            async for chunk in provider.stream(messages, max_tokens=100):
                if hasattr(chunk, "type") and chunk.type == "failover":
                    continue
                if first_token_time is None:
                    first_token_time = time.perf_counter()
                token_count += 1
                
            completion_time = time.perf_counter()
            success = True
        except Exception as e:
            error_type = type(e).__name__
            print(f"{Fore.YELLOW}  Query {i+1} failed: {error_type}")
            
        if success:
            ttft_ms = (first_token_time - start_time) * 1000 if first_token_time else 0
            total_latency_ms = (completion_time - start_time) * 1000
            tps = token_count / (completion_time - first_token_time) if token_count > 1 and completion_time > first_token_time else 0
            results.append({"success": True, "ttft_ms": ttft_ms, "latency_ms": total_latency_ms, "tps": tps})
        else:
            results.append({"success": False, "error_type": error_type})
            
        # Rate limit prevention delay
        await asyncio.sleep(0.5)

    success_count = sum(1 for r in results if r["success"])
    if success_count == 0:
        return {"model": model_name, "success_rate": 0, "score": 0}

    avg_ttft = sum(r["ttft_ms"] for r in results if r["success"]) / success_count
    avg_latency = sum(r["latency_ms"] for r in results if r["success"]) / success_count
    avg_tps = sum(r["tps"] for r in results if r["success"]) / success_count
    
    score = (success_count * 10) + (avg_tps * 2) - (avg_ttft / 100) # Arbitrary score for ranking

    return {
        "model": model_name,
        "success_rate": (success_count / len(queries)) * 100,
        "avg_ttft_ms": avg_ttft,
        "avg_latency_ms": avg_latency,
        "avg_tps": avg_tps,
        "score": score,
        "raw_results": results
    }

async def run_stage_1():
    print(f"\n{Fore.GREEN}=== STAGE 1: SMOKE TEST (5 Queries per Model) ===")
    queries = generate_queries(5)
    results = []
    for model in MODELS_TO_TEST:
        res = await benchmark_hf_model(model, queries, "STAGE 1")
        if res:
            results.append(res)
            
    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)
    for r in results:
        print(f"  {r['model']}: {r['success_rate']}% Success | TTFT: {r.get('avg_ttft_ms',0):.1f}ms | TPS: {r.get('avg_tps',0):.1f} | Score: {r['score']:.1f}")
        
    return [r["model"] for r in results[:2]] if len(results) >= 2 else [r["model"] for r in results]

async def run_stage_2(models):
    print(f"\n{Fore.GREEN}=== STAGE 2: SHORT RELIABILITY TEST (25 Queries per Model) ===")
    queries = generate_queries(25)
    results = []
    for model in models:
        res = await benchmark_hf_model(model, queries, "STAGE 2")
        if res:
            results.append(res)
            
    results.sort(key=lambda x: x["score"], reverse=True)
    for r in results:
        print(f"  {r['model']}: {r['success_rate']}% Success | TTFT: {r.get('avg_ttft_ms',0):.1f}ms | TPS: {r.get('avg_tps',0):.1f}")
        
    return results[0]["model"] if results else None

async def run_stage_3(winner_model):
    print(f"\n{Fore.GREEN}=== STAGE 3: FINAL RELIABILITY TEST (100 Queries) ===")
    print(f"Executing endurance test on winning model: {winner_model}")
    queries = generate_queries(100)
    res = await benchmark_hf_model(winner_model, queries, "STAGE 3")
    
    if res:
        print("\n=== FINAL RECOMMENDATION REPORT ===")
        print(f"Model: {winner_model}")
        print(f"Success Rate: {res['success_rate']}%")
        print(f"Average Latency: {res['avg_latency_ms']:.1f}ms")
        print(f"Tokens/Sec: {res['avg_tps']:.1f}")
        
        # Calculate P50, P95, P99
        latencies = sorted([r["latency_ms"] for r in res["raw_results"] if r["success"]])
        if latencies:
            p50 = latencies[int(len(latencies) * 0.5)]
            p95 = latencies[int(len(latencies) * 0.95)] if len(latencies) >= 20 else latencies[-1]
            p99 = latencies[int(len(latencies) * 0.99)] if len(latencies) >= 100 else latencies[-1]
            print(f"P50 Latency: {p50:.1f}ms")
            print(f"P95 Latency: {p95:.1f}ms")
            print(f"P99 Latency: {p99:.1f}ms")
    else:
        print(f"{Fore.RED}Final test failed for {winner_model}.")

async def run_benchmarks():
    top_2 = await run_stage_1()
    if not top_2:
        print(f"{Fore.RED}Stage 1 failed. No viable models found.")
        return
        
    winner = await run_stage_2(top_2)
    if not winner:
        print(f"{Fore.RED}Stage 2 failed. No viable models found.")
        return
        
    await run_stage_3(winner)

if __name__ == "__main__":
    asyncio.run(run_benchmarks())
