import asyncio
import time
import httpx
from colorama import Fore, Style, init

init(autoreset=True)

API_URL = "http://localhost:8000"

TEST_PROMPTS = [
    "Explain semantic search.",
    "What is the difference between RAG and fine-tuning?",
    "How does FAISS indexing work?",
    "Write a short python snippet for a REST API.",
    "Summarize the history of artificial intelligence in three sentences."
]

PROVIDERS_TO_TEST = [
    {"name": "ollama", "model": "qwen2.5:3b-instruct"},
    {"name": "ollama", "model": "qwen2.5:7b-instruct"},
    {"name": "huggingface", "model": "microsoft/Phi-3-mini-4k-instruct"},
    {"name": "gemini", "model": "gemini-1.5-flash"}
]

# Note: In a real environment, changing the provider via the API dynamically
# would require an admin endpoint. For this benchmark, we will assume we can hit 
# a custom endpoint, or we just instruct the user to configure the backend and run it.
# Wait, the mandate says: "Configuration only. No code modifications." 
# We should build a standalone script that instantiates the providers directly
# and measures them locally, bypassing FastAPI overhead for pure provider benchmarking.

from backend.providers.factory import ProviderFactory
from backend.core.startup import state
from backend.core.config import settings

async def benchmark_provider(provider_name, model_name):

    try:
        # Create non-failover provider for strict benchmarking
        provider = ProviderFactory._create_provider_instance(provider_name)
    except Exception as e:
        print(f"{Fore.RED}Failed to init {provider_name} ({model_name}): {e}")
        return None

    if not provider:
        print(f"{Fore.RED}Provider {provider_name} returned None.")
        return None

    # Health check
    if not await provider.health_check():
        print(f"{Fore.RED}Provider {provider_name} ({model_name}) is UNHEALTHY.")
        return None

    print(f"\n{Fore.CYAN}--- Benchmarking {provider_name} ({model_name}) ---")
    
    results = []
    
    for prompt in TEST_PROMPTS:
        messages = [{"role": "user", "content": prompt}]
        
        # Measure TTFT and Stream metrics
        start_time = time.perf_counter()
        first_token_time = None
        token_count = 0
        success = False
        
        try:
            async for chunk in provider.stream(messages, max_tokens=150):
                if hasattr(chunk, "type") and chunk.type == "failover":
                    continue
                if first_token_time is None:
                    first_token_time = time.perf_counter()
                token_count += 1
                
            completion_time = time.perf_counter()
            success = True
            
            ttft_ms = (first_token_time - start_time) * 1000 if first_token_time else 0
            total_latency_ms = (completion_time - start_time) * 1000
            tps = token_count / (completion_time - first_token_time) if token_count > 1 and completion_time > first_token_time else 0
            
            results.append({
                "ttft_ms": ttft_ms,
                "latency_ms": total_latency_ms,
                "tps": tps,
                "success": success
            })
        except Exception as e:
            print(f"{Fore.RED}Error on prompt '{prompt[:20]}...': {e}")
            results.append({"success": False})

    # Aggregate
    success_count = sum(1 for r in results if r["success"])
    if success_count == 0:
        return {"success_rate": 0}

    avg_ttft = sum(r["ttft_ms"] for r in results if r["success"]) / success_count
    avg_latency = sum(r["latency_ms"] for r in results if r["success"]) / success_count
    avg_tps = sum(r["tps"] for r in results if r["success"]) / success_count

    return {
        "success_rate": (success_count / len(TEST_PROMPTS)) * 100,
        "avg_ttft_ms": avg_ttft,
        "avg_latency_ms": avg_latency,
        "avg_tps": avg_tps
    }

async def run_benchmarks():
    print("Starting Provider Benchmarking Suite...")
    summary = []
    for cfg in PROVIDERS_TO_TEST:
        metrics = await benchmark_provider(cfg["name"], cfg["model"])
        if metrics:
            summary.append({
                "Provider": f"{cfg['name']} ({cfg['model']})",
                **metrics
            })
            
    print(f"\n{Fore.GREEN}=== BENCHMARK REPORT ===")
    print(f"{'Provider & Model':<40} | {'Success':<8} | {'TTFT (ms)':<10} | {'Latency (ms)':<12} | {'Tokens/Sec':<10}")
    print("-" * 90)
    for res in summary:
        print(f"{res['Provider']:<40} | {res['success_rate']:>7.1f}% | {res['avg_ttft_ms']:>9.1f} | {res['avg_latency_ms']:>11.1f} | {res['avg_tps']:>9.1f}")

if __name__ == "__main__":
    asyncio.run(run_benchmarks())
