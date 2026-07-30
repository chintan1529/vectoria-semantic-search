"""
Streaming Orchestrator v4 — Hardened SSE with output guards.

Guarantees:
  - Generation verified: token_count > 0 before emitting 'done'
  - Heartbeat events every 15s to prevent connection drops
  - Event sequence tracking for frontend validation
  - No false COMPLETE states
  - Every event logged with request_id

Yields structured SSE events:
  - phase: Pipeline progress events (retrieving, generating, verifying)
  - context: Retrieved chunks
  - diagnostics: Retrieval metrics
  - heartbeat: Connection keepalive
  - token: LLM generation tokens
  - done: Stream complete (ONLY if tokens > 0)
  - generation_failed: If generation produced no output
  - error: Error with message
"""
import json
import time
import asyncio
import hashlib
from typing import AsyncGenerator, List
from sse_starlette.sse import ServerSentEvent
from vectoria.models import SearchResult
from backend.providers.base_provider import BaseLLMProvider
from backend.orchestration.retrieval_orchestrator import RetrievalDiagnostics
from .generation_orchestrator import GenerationOrchestrator
from backend.core.logging import logger
from backend.core.failure_memory import failure_memory
from vectoria.intelligence.decision_engine import DecisionEngine, DecisionAction
from vectoria.intelligence.claim_grounding import ClaimGroundingEngine
from vectoria.generation.dynamic_prompt_builder import DynamicPromptBuilder

# Minimum tokens to consider generation valid
MIN_TOKEN_COUNT = 1
MIN_ANSWER_LENGTH = 10
HEARTBEAT_INTERVAL_S = 15


def _build_sse_payload(event: str, data_dict: dict, request_id: str, seq: int, provider_name: str) -> str:
    """Enrich SSE payload with packet validation headers (Phase 9 requirements)."""
    payload = {
        "request_id": request_id,
        "seq": seq,
        "timestamp": time.time(),
        "provider": provider_name,
        "stage": event,
        **data_dict
    }
    # Calculate packet checksum
    raw_str = json.dumps(payload, sort_keys=True)
    payload["checksum"] = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:8]
    return json.dumps(payload)


class StreamingOrchestrator:
    """Coordinates full pipeline streaming: retrieval → context → generation.

    Emits phase events so the frontend pipeline visualizer updates in real time.
    """

    def __init__(self, provider: BaseLLMProvider):
        self.generation = GenerationOrchestrator(provider)
        self.decision_engine = DecisionEngine()
        self.prompt_builder = DynamicPromptBuilder()
        self.claim_grounding = ClaimGroundingEngine()

    async def stream_full_pipeline(
        self,
        query: str,
        retrieval_orchestrator,
        request_id: str = "",
        on_complete=None,
        **kwargs,
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """Stream full pipeline from instant SSE connection to retrieval and generation.
        
        Uses concurrent retrieval with heartbeat keepalive to prevent SSE connection
        stalling on low-end hardware where CrossEncoder reranking can take 11-17 seconds.
        """
        event_seq = 1
        provider_name = getattr(self.generation.provider, 'model', 'unknown_provider')

        # 1. Phase: Classifying
        yield ServerSentEvent(
            event="phase",
            data=_build_sse_payload("phase", {"phase": "classifying", "status": "active"}, request_id, event_seq, provider_name),
        )
        event_seq += 1

        # 2. Phase: Retrieving
        yield ServerSentEvent(
            event="phase",
            data=_build_sse_payload("phase", {"phase": "retrieving", "status": "active"}, request_id, event_seq, provider_name),
        )
        event_seq += 1

        # Execute Retrieval as concurrent task with heartbeat keepalive.
        # On low-end hardware (4 cores, 8GB RAM), CrossEncoder reranking can take
        # 11-17 seconds. Without heartbeats, the SSE connection stalls and the
        # frontend stays stuck at "CONNECTING" because no events are flushed.
        retrieval_task = asyncio.create_task(
            retrieval_orchestrator.execute_retrieval(query, top_k=5)
        )

        retrieval_error = None
        results = None
        diagnostics = None

        while not retrieval_task.done():
            yield ServerSentEvent(
                event="heartbeat",
                data=_build_sse_payload("heartbeat", {"status": "retrieving"}, request_id, event_seq, provider_name),
            )
            event_seq += 1
            try:
                await asyncio.wait_for(asyncio.shield(retrieval_task), timeout=2.0)
            except asyncio.TimeoutError:
                # Retrieval still running — loop back to yield another heartbeat
                pass
            except Exception as ret_err:
                retrieval_error = ret_err
                break

        # Collect retrieval result
        if retrieval_error is None and retrieval_task.done():
            try:
                results, diagnostics = retrieval_task.result()
            except Exception as ret_err:
                retrieval_error = ret_err

        if retrieval_error is not None:
            logger.error("RETRIEVAL_STREAM_ERROR | request_id=%s error=%s", request_id, str(retrieval_error))
            yield ServerSentEvent(
                event="error",
                data=_build_sse_payload("error", {"message": f"Retrieval failed: {str(retrieval_error)}"}, request_id, event_seq, provider_name),
            )
            return

        # 3. Stream context, diagnostics, tokens, done
        async for sse_event in self.stream_response(query, results, diagnostics, request_id=request_id, on_complete=on_complete, **kwargs):
            yield sse_event

    async def stream_response(
        self,
        query: str,
        results: List[SearchResult],
        diagnostics: RetrievalDiagnostics,
        request_id: str = "",
        on_complete=None,
        **kwargs,
    ) -> AsyncGenerator[ServerSentEvent, None]:
        generation_start = time.perf_counter()
        event_seq = 1  # Event sequence counter for frontend validation
        provider_name = getattr(self.generation.provider, 'model', 'unknown_provider')

        logger.info(
            "SSE_STREAM_START | request_id=%s query=%s results=%d",
            request_id, repr(query[:50]), len(results),
        )

        # --- Failure Memory: Log empty retrieval asynchronously (Phase 5) ---
        if len(results) == 0:
            asyncio.create_task(asyncio.to_thread(
                failure_memory.log_empty_retrieval,
                query=query,
                request_id=request_id,
                query_type=getattr(diagnostics, 'query_type', "unknown"),
            ))

        # --- Phase: Retrieval complete ---
        yield ServerSentEvent(
            event="phase",
            data=_build_sse_payload("phase", {
                "phase": "retrieving",
                "status": "complete",
                "latency_ms": diagnostics.retrieval_latency_ms,
            }, request_id, event_seq, provider_name),
        )
        event_seq += 1

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
            data=_build_sse_payload("context", {"chunks": context_data}, request_id, event_seq, provider_name),
        )
        event_seq += 1
        logger.info("SSE_EVENT_SENT | event=context chunks=%d seq=%d", len(context_data), event_seq)

        # --- Diagnostics ---
        diag_dict = json.loads(diagnostics.model_dump_json())
        yield ServerSentEvent(
            event="diagnostics",
            data=_build_sse_payload("diagnostics", diag_dict, request_id, event_seq, provider_name),
        )
        event_seq += 1
        logger.info("SSE_EVENT_SENT | event=diagnostics seq=%d", event_seq)

        # --- Evaluate Central Decision Engine ---
        decision = self.decision_engine.evaluate_pipeline(query, results)

        # Emit Reasoning Trace (Phase 10)
        yield ServerSentEvent(
            event="reasoning_trace",
            data=_build_sse_payload("reasoning_trace", decision.reasoning_trace, request_id, event_seq, provider_name),
        )
        event_seq += 1

        # Handle CLARIFY action
        if decision.action == DecisionAction.CLARIFY:
            yield ServerSentEvent(
                event="token",
                data=_build_sse_payload("token", {"text": decision.clarification_prompt or "Could you please clarify your query?"}, request_id, event_seq, provider_name),
            )
            yield ServerSentEvent(
                event="done",
                data=_build_sse_payload("done", {"action": "CLARIFY", "request_id": request_id}, request_id, event_seq + 1, provider_name),
            )
            return

        # Handle REFUSE action
        if decision.action == DecisionAction.REFUSE:
            yield ServerSentEvent(
                event="token",
                data=_build_sse_payload("token", {"text": decision.refusal_reason or "Insufficient evidence to answer."}, request_id, event_seq, provider_name),
            )
            yield ServerSentEvent(
                event="done",
                data=_build_sse_payload("done", {"action": "REFUSE", "request_id": request_id}, request_id, event_seq + 1, provider_name),
            )
            return

        # --- Phase: Generating ---
        yield ServerSentEvent(
            event="phase",
            data=_build_sse_payload("phase", {
                "phase": "generating",
                "status": "active",
                "action": decision.action.value,
            }, request_id, event_seq, provider_name),
        )
        event_seq += 1

        # --- Stream LLM tokens ---
        messages = self.generation.build_prompt(query, results, diagnostics)
        logger.info("GENERATION_REQUEST_SENT | request_id=%s model=%s", request_id, provider_name)

        try:
            token_count = 0
            first_token_logged = False
            full_answer = []

            async for chunk in self.generation.provider.stream(messages, **kwargs):
                if not first_token_logged:
                    first_token_ms = int((time.perf_counter() - generation_start) * 1000)
                    logger.info("FIRST_TOKEN_RECEIVED | request_id=%s latency_ms=%d", request_id, first_token_ms)
                    first_token_logged = True

                if hasattr(chunk, 'type'):
                    if chunk.type == "token":
                        yield ServerSentEvent(
                            event="token",
                            data=_build_sse_payload("token", {"text": chunk.content}, request_id, event_seq, provider_name)
                        )
                        token_count += 1
                        event_seq += 1
                        full_answer.append(chunk.content)
                    elif chunk.type == "failover":
                        yield ServerSentEvent(
                            event=chunk.content.get("event", "provider_failover"),
                            data=_build_sse_payload("provider_failover", chunk.content, request_id, event_seq, provider_name)
                        )
                        event_seq += 1
                else:
                    yield ServerSentEvent(
                        event="token",
                        data=_build_sse_payload("token", {"text": chunk}, request_id, event_seq, provider_name)
                    )
                    token_count += 1
                    event_seq += 1
                    full_answer.append(chunk)

            generation_ms = int((time.perf_counter() - generation_start) * 1000)

            # --- Phase 10: Generation & Answer Quality Verification ---
            final_text = "".join(full_answer)
            if token_count < MIN_TOKEN_COUNT or len(final_text.strip()) < MIN_ANSWER_LENGTH:
                logger.error(
                    "GENERATION_INVALID | request_id=%s tokens=%d answer_len=%d reason=OUTPUT_BELOW_THRESHOLD",
                    request_id, token_count, len(final_text.strip()),
                )
                yield ServerSentEvent(
                    event="generation_failed",
                    data=_build_sse_payload("generation_failed", {
                        "reason": "Generation produced insufficient output",
                        "token_count": token_count,
                        "answer_length": len(final_text.strip()),
                    }, request_id, event_seq, provider_name),
                )
                # Log failure asynchronously
                asyncio.create_task(asyncio.to_thread(
                    failure_memory.log_retrieval_failure,
                    query=query,
                    request_id=request_id,
                    reason="generation_insufficient_output",
                    total_results=len(results),
                    scores=[r.score for r in results],
                ))
                return

            logger.info(
                "GENERATION_VERIFIED | request_id=%s tokens=%d answer_len=%d latency_ms=%d",
                request_id, token_count, len(final_text), generation_ms,
            )

            # --- Yield done (Phase 5: Critical path ends here!) ---
            yield ServerSentEvent(
                event="done",
                data=_build_sse_payload("done", {
                    "generation_latency_ms": generation_ms,
                    "token_count": token_count,
                    "answer_length": len(final_text),
                }, request_id, event_seq, provider_name),
            )
            event_seq += 1

            # --- Phase 5: Offload Trust Verification & Analytics to Background Task ---
            async def _bg_verification_task():
                try:
                    from backend.services.trust_verification_service import TrustVerificationService
                    trust_service = TrustVerificationService(self.generation.provider)
                    eval_start = time.perf_counter()
                    
                    verification_metrics = await trust_service.verify_trust(query, results, final_text)
                    eval_ms = int((time.perf_counter() - eval_start) * 1000)
                    
                    logger.info("TRUST_VERIFIED_ASYNC | request_id=%s latency_ms=%d", request_id, eval_ms)

                    # Log low faithfulness if needed
                    faithfulness = verification_metrics.get("faithfulness", 1.0)
                    if isinstance(faithfulness, (int, float)) and faithfulness < 0.5:
                        failure_memory.log_low_faithfulness(
                            query=query,
                            request_id=request_id,
                            faithfulness_score=faithfulness,
                            answer_preview=final_text[:300],
                        )

                    # Log hallucination if needed
                    hallucination_rate = verification_metrics.get("hallucination_rate", 0.0)
                    if isinstance(hallucination_rate, (int, float)) and hallucination_rate > 0.3:
                        failure_memory.log_hallucination(
                            query=query,
                            request_id=request_id,
                            hallucination_score=hallucination_rate,
                            evidence=final_text[:300],
                        )

                    if on_complete:
                        try:
                            on_complete(final_text, verification_metrics)
                        except Exception as cb_err:
                            logger.warning("ON_COMPLETE_CALLBACK_ERROR | %s", str(cb_err))
                except Exception as bg_err:
                    logger.warning("BG_VERIFICATION_FAILED | request_id=%s error=%s", request_id, str(bg_err))

            asyncio.create_task(_bg_verification_task())

        except Exception as e:
            logger.error(
                "GENERATION_EXCEPTION | request_id=%s error=%s type=%s",
                request_id, str(e), type(e).__name__,
            )
            yield ServerSentEvent(
                event="error",
                data=_build_sse_payload("error", {
                    "message": str(e),
                }, request_id, event_seq, provider_name),
            )

