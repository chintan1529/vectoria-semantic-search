import asyncio
import sys
import os


from backend.core.startup import state, startup_event
from backend.providers.factory import ProviderFactory
from backend.orchestration.retrieval_orchestrator import RetrievalOrchestrator
from backend.orchestration.streaming_orchestrator import StreamingOrchestrator

async def test_sse_query():
    print("Testing Query Stream (SSE)")
    provider = ProviderFactory.create_chat_provider()
    retriever = RetrievalOrchestrator(provider)
    orchestrator = StreamingOrchestrator(provider, retriever)
    
    events = set()
    print("Starting query: What is Vectoria?")
    async for event in orchestrator.stream_answer("What is Vectoria?"):
        event_name = "unknown"
        if "event: " in event:
            event_name = event.split("event: ")[1].split("\n")[0]
            events.add(event_name)
        elif event.startswith("data:"):
            # If there's no event: prefix, it's a default message event (usually tokens)
            if "message" not in events:
                events.add("message (token)")
        print(f"Captured event: {event_name}")
        
    print("\nVerified Events:")
    for e in events:
        print(f" - {e}")
        
if __name__ == "__main__":
    startup_event()
    asyncio.run(test_sse_query())
