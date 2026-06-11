"""Reproduce the @retry + async generator bug."""
import asyncio
from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(2), wait=wait_fixed(0.1))
async def broken_stream():
    """This is what our provider.stream() looks like."""
    yield "hello"
    yield "world"

async def plain_stream():
    """This is what it should look like without @retry."""
    yield "hello"
    yield "world"

async def main():
    # Test 1: Plain async generator (should work)
    print("=== Test 1: Plain async generator ===")
    tokens = []
    async for token in plain_stream():
        tokens.append(token)
    print(f"Tokens: {tokens}")

    # Test 2: @retry-wrapped async generator (EXPECTED TO BREAK)
    print("\n=== Test 2: @retry-wrapped async generator ===")
    try:
        result = broken_stream()
        has_aiter = hasattr(result, "__aiter__")
        is_coro = asyncio.iscoroutine(result)
        print(f"Type: {type(result)}")
        print(f"Is coroutine: {is_coro}")
        print(f"Has __aiter__: {has_aiter}")

        tokens = []
        async for token in broken_stream():
            tokens.append(token)
        print(f"Tokens: {tokens}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

asyncio.run(main())
