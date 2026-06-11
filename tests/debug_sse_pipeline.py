"""
End-to-end SSE pipeline diagnostic test.

Sends a real query to the backend and captures every SSE event to find
exactly where the pipeline breaks.
"""
import asyncio
import httpx
import json
import time


async def main():
    url = "http://localhost:8000/api/query/stream"
    query = "What is backpropagation?"

    print(f"=== Sending query: '{query}' ===")
    print(f"URL: {url}")
    print()

    start = time.perf_counter()
    events_received = []

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                url,
                json={"query": query},
                headers={"Content-Type": "application/json"},
            ) as response:
                print(f"HTTP Status: {response.status_code}")
                print(f"Headers: {dict(response.headers)}")
                print()

                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk

                    # Parse SSE events
                    while "\n\n" in buffer:
                        event_str, buffer = buffer.split("\n\n", 1)
                        lines = event_str.strip().split("\n")
                        event_type = "message"
                        data = ""

                        for line in lines:
                            if line.startswith("event: "):
                                event_type = line[7:].strip()
                            elif line.startswith("data: "):
                                data = line[6:]

                        elapsed = int((time.perf_counter() - start) * 1000)
                        events_received.append({
                            "event": event_type,
                            "elapsed_ms": elapsed,
                            "data_preview": data[:200] if data else "(empty)",
                        })

                        print(f"[{elapsed:>6}ms] event={event_type:>12}  data_len={len(data):>5}  preview={data[:120]}")

                        # For token events, just count them
                        if event_type == "token":
                            pass  # Already printed above

    except Exception as e:
        elapsed = int((time.perf_counter() - start) * 1000)
        print(f"\n[{elapsed}ms] CONNECTION ERROR: {type(e).__name__}: {e}")

    total_ms = int((time.perf_counter() - start) * 1000)

    print()
    print(f"=== SUMMARY ===")
    print(f"Total time: {total_ms}ms")
    print(f"Events received: {len(events_received)}")

    # Count by type
    type_counts = {}
    for ev in events_received:
        t = ev["event"]
        type_counts[t] = type_counts.get(t, 0) + 1

    for event_type, count in sorted(type_counts.items()):
        print(f"  {event_type}: {count}")

    if not any(e["event"] == "token" for e in events_received):
        print("\n*** NO TOKEN EVENTS RECEIVED — GENERATION FAILED ***")

    if not any(e["event"] == "context" for e in events_received):
        print("\n*** NO CONTEXT EVENTS RECEIVED — SSE PIPELINE BROKEN ***")

    if not any(e["event"] == "diagnostics" for e in events_received):
        print("\n*** NO DIAGNOSTICS EVENTS RECEIVED ***")

    if any(e["event"] == "error" for e in events_received):
        error_events = [e for e in events_received if e["event"] == "error"]
        print(f"\n*** ERROR EVENTS: ***")
        for e in error_events:
            print(f"  {e['data_preview']}")


asyncio.run(main())
