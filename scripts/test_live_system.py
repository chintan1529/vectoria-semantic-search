import httpx
import json
import asyncio
from colorama import Fore, Style, init

init(autoreset=True)

API_URL = "http://localhost:8000"

async def test_sse_stream(endpoint: str, payload: dict, name: str):
    print(f"\n{Fore.CYAN}=== Testing {name} ===")
    url = f"{API_URL}{endpoint}"
    print(f"POST {url}")
    
    events_received = set()
    first_token_received = False
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    print(f"{Fore.RED}Failed! Status Code: {response.status_code}")
                    return False
                    
                async for line in response.aiter_lines():
                    if line.startswith("event:"):
                        event_name = line.split(":", 1)[1].strip()
                        events_received.add(event_name)
                    elif line.startswith("data:"):
                        data_payload = line.split(":", 1)[1].strip()
                        if "message" not in events_received and not first_token_received:
                            events_received.add("message (token)")
                            first_token_received = True
                            
        print(f"{Fore.GREEN}Stream completed successfully.")
        print("Events captured:")
        for e in events_received:
            print(f"  - {e}")
        return True
    except Exception as e:
        print(f"{Fore.RED}Error: {e}")
        return False

async def test_json_endpoint(endpoint: str, payload: dict, name: str):
    print(f"\n{Fore.CYAN}=== Testing {name} ===")
    url = f"{API_URL}{endpoint}"
    print(f"POST {url}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                print(f"{Fore.GREEN}Success! Status Code: 200")
                return True
            else:
                print(f"{Fore.RED}Failed! Status Code: {response.status_code}")
                print(response.text)
                return False
    except Exception as e:
        print(f"{Fore.RED}Error: {e}")
        return False

async def test_get_endpoint(endpoint: str, name: str):
    print(f"\n{Fore.CYAN}=== Testing {name} ===")
    url = f"{API_URL}{endpoint}"
    print(f"GET {url}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                print(f"{Fore.GREEN}Success! Status Code: 200")
                return True
            else:
                print(f"{Fore.RED}Failed! Status Code: {response.status_code}")
                return False
    except Exception as e:
        print(f"{Fore.RED}Error: {e}")
        return False

async def run_all_tests():
    print(f"{Fore.YELLOW}Waiting for API to be ready... (this could take 60s for models to load)")
    ready = False
    for _ in range(30):
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{API_URL}/api/health")
                if res.status_code == 200:
                    ready = True
                    break
        except:
            pass
        await asyncio.sleep(2)
        
    if not ready:
        print(f"{Fore.RED}API did not become ready.")
        return

    # Wait for models to warm up fully
    for _ in range(30):
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{API_URL}/api/ready")
                if res.status_code == 200:
                    break
        except:
            pass
        await asyncio.sleep(2)

    query_payload = {"query": "What is semantic search?", "top_k": 3}
    
    print("\nStarting Validation Suite...")
    
    # 1. Telemetry
    r1 = await test_get_endpoint("/api/status", "Telemetry API (/api/status)")
    
    # 2. Query Console (SSE)
    r2 = await test_sse_stream("/api/query/stream", query_payload, "Query Console SSE")
    
    # 3. Research Mode (SSE)
    r3 = await test_sse_stream("/api/research/stream", query_payload, "Research Mode SSE")
    
    # 4. Retrieval Lab (JSON)
    r4 = await test_json_endpoint("/api/query/inspect", query_payload, "Retrieval Lab (/api/query/inspect)")
    
    # 5. Knowledge Graph (JSON)
    kg_payload = {"texts": ["Semantic search uses dense vector representations. FAISS is a library for similarity search."]}
    r5 = await test_json_endpoint("/api/query/knowledge-graph/extract", kg_payload, "Knowledge Graph (/extract)")
    
    print(f"\n{Fore.CYAN}=== Final Results ===")
    print(f"Telemetry: {'Pass' if r1 else 'Fail'}")
    print(f"Query Console: {'Pass' if r2 else 'Fail'}")
    print(f"Research Mode: {'Pass' if r3 else 'Fail'}")
    print(f"Retrieval Lab: {'Pass' if r4 else 'Fail'}")
    print(f"Knowledge Graph: {'Pass' if r5 else 'Fail'}")
    
if __name__ == "__main__":
    asyncio.run(run_all_tests())
