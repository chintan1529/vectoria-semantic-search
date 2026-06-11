"""Test how sse_starlette handles dict yields vs ServerSentEvent yields."""
import asyncio
import json
from sse_starlette.sse import EventSourceResponse, ServerSentEvent


async def dict_generator():
    """Yield dicts — this is what our streaming orchestrator does."""
    yield {"event": "context", "data": json.dumps([{"id": "1", "title": "test"}])}
    yield {"event": "token", "data": json.dumps("hello")}
    yield {"event": "done", "data": "{}"}


async def main():
    # Create the EventSourceResponse
    response = EventSourceResponse(dict_generator())
    
    # Manually consume the body to see what gets sent
    body_parts = []
    async for chunk in response.body_iterator:
        if isinstance(chunk, bytes):
            body_parts.append(chunk.decode())
        else:
            body_parts.append(str(chunk))
    
    full_body = "".join(body_parts)
    
    print("=== Raw SSE output from dict yields ===")
    print(repr(full_body))
    print()
    print("=== Formatted ===")
    print(full_body)


asyncio.run(main())
