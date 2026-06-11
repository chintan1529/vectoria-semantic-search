"""
Streaming Orchestrator v3 — Fixed SSE event format.

ROOT CAUSE FIX: EventSourceResponse does NOT auto-format plain dicts into SSE.
We must yield ServerSentEvent objects explicitly.

Yields structured SSE events:
  - phase: Pipeline progress events (retrieving, generating)
  - context: Retrieved chunks
  - diagnostics: Retrieval metrics
  - token: LLM generation tokens
  - done: Stream complete with timing metadata
  - error: Error with message
"""
import json
import time
from typing import AsyncGenerator, List
from sse_starlette.sse import ServerSentEvent
from vectoria.models import SearchResult
from backend.providers.base_provider import BaseLLMProvider
from backend.orchestration.retrieval_orchestrator import RetrievalDiagnostics
from .generation_orchestrator import GenerationOrchestrator
from backend.core.logging import logger


class StreamingOrchestrator:
    """Coordinates full pipeline streaming: retrieval → context → generation.

    Emits phase events so the frontend pipeline visualizer updates in real time.
    """

    def __init__(self, provider: BaseLLMProvider):
        self.generation = GenerationOrchestrator(provider)

    async def stream_response(
        self,
        query: str,
        results: List[SearchResult],
        diagnostics: RetrievalDiagnostics,
        request_id: str = "",
        **kwargs,
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """Yield Server-Sent Events with phase tracking.

        Event flow:
          1. phase:retrieving (with timing from diagnostics)
          2. context (retrieved chunks)
          3. diagnostics (retrieval metrics)
          4. phase:generating
          5. token (streamed LLM tokens)
          6. done
        """
        generation_start = time.perf_counter()

        logger.info(
            "SSE_STREAM_START | request_id=%s query=%s results=%d",
            request_id, repr(query[:50]), len(results),
        )

        # --- Phase: Retrieval complete ---
        yield ServerSentEvent(
            event="phase",
            data=json.dumps({
                "phase": "retrieving",
                "status": "complete",
                "latency_ms": diagnostics.retrieval_latency_ms,
                "request_id": request_id,
            }),
        )

        # --- Context data ---
        context_data = [
            {
                "id": r.chunk.chunk_id,
                "title": r.chunk.metadata.title,
                "score": r.score,
                "text": r.chunk.text,
            }
            for r in results
        ]
        yield ServerSentEvent(
            event="context",
            data=json.dumps(context_data),
        )
        logger.info("SSE_EVENT_SENT | event=context chunks=%d", len(context_data))

        # --- Diagnostics ---
        yield ServerSentEvent(
            event="diagnostics",
            data=diagnostics.model_dump_json(),
        )
        logger.info("SSE_EVENT_SENT | event=diagnostics")

        # --- Phase: Generating ---
        yield ServerSentEvent(
            event="phase",
            data=json.dumps({
                "phase": "generating",
                "status": "active",
                "request_id": request_id,
            }),
        )

        # --- Stream LLM tokens ---
        messages = self.generation.build_prompt(query, results, diagnostics)
        logger.info("GENERATION_REQUEST_SENT | request_id=%s model=%s", request_id, self.generation.provider.model)

        try:
            token_count = 0
            first_token_logged = False

            async for token in self.generation.provider.stream(messages, **kwargs):
                if not first_token_logged:
                    first_token_ms = int((time.perf_counter() - generation_start) * 1000)
                    logger.info("FIRST_TOKEN_RECEIVED | request_id=%s latency_ms=%d", request_id, first_token_ms)
                    first_token_logged = True

                yield ServerSentEvent(
                    event="token",
                    data=json.dumps(token),
                )
                token_count += 1

            generation_ms = int((time.perf_counter() - generation_start) * 1000)
            logger.info(
                "GENERATION_FINISHED | request_id=%s tokens=%d latency_ms=%d",
                request_id, token_count, generation_ms,
            )

            yield ServerSentEvent(
                event="done",
                data=json.dumps({
                    "generation_latency_ms": generation_ms,
                    "token_count": token_count,
                    "request_id": request_id,
                }),
            )

        except Exception as e:
            logger.error(
                "GENERATION_EXCEPTION | request_id=%s error=%s type=%s",
                request_id, str(e), type(e).__name__,
            )
            yield ServerSentEvent(
                event="error",
                data=json.dumps({
                    "message": str(e),
                    "request_id": request_id,
                }),
            )
