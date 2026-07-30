"""
LLM Client — Production-grade synchronous abstraction over the Google Gemini API.

Responsibilities:
    - Send generation requests to the Gemini REST API via direct HTTPS.
    - Convert provider-agnostic messages (system/user roles) into Gemini's
      ``systemInstruction`` / ``contents`` format internally, so no
      provider-specific logic leaks into the pipeline or prompt builder.
    - Cascade through multiple Gemini models on rate-limit (429) to
      maximise free-tier availability.
    - Enforce timeout, retry, and exponential backoff for transient failures.
    - Handle Gemini-specific responses: safety blocks, finish reasons,
      and token usage metadata.
    - Surface structured errors via a dedicated exception hierarchy.
    - Track observability metrics: generation latency, model used,
      estimated token usage.

Design decisions:
    - Uses ``requests`` directly — no ``google-generativeai`` SDK dependency.
    - Synchronous only.  CPU-bound, single-user system; async adds no value.
    - ``temperature=0.0`` by default for deterministic, reproducible outputs.
    - No streaming in v1.  Streaming is a UX concern, not a correctness one.
    - API key loaded from ``VECTORIA_LLM_API_KEY`` environment variable.
    - Token estimation uses a lightweight ``len(text) / 4`` heuristic when
      the API does not return ``usageMetadata``.  Good enough for budgeting
      and monitoring without pulling in a tokenizer dependency.

Model Fallback Strategy:
    Free-tier Gemini quotas are per-model.  When a 429 is received, the
    client cascades through a prioritised fallback chain before exhausting
    retries.  This maximises the chance of a response without billing changes.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import requests as http_client

from vectoria.logger import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────────────

class LLMError(Exception):
    """Base exception for LLM client errors."""


class LLMTimeoutError(LLMError):
    """API did not respond within the configured timeout."""


class LLMRateLimitError(LLMError):
    """HTTP 429 — retryable rate-limit hit."""


class LLMAuthError(LLMError):
    """HTTP 401/403 — not retryable, bad credentials."""


class LLMGenerationError(LLMError):
    """Unexpected API response or missing content."""


class LLMSafetyBlockError(LLMError):
    """Gemini refused generation due to safety filters."""


# ─────────────────────────────────────────────────────────────────────
# Generation Metadata
# ─────────────────────────────────────────────────────────────────────

@dataclass
class GenerationMeta:
    """Observability metadata from a single LLM generation call.

    Populated after each successful ``generate()`` call and exposed
    via ``LLMClient.last_generation_meta`` for the pipeline to consume.
    """

    model_used: str = ""
    generation_latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable dictionary for logging and response assembly."""
        return {
            "model_used": self.model_used,
            "generation_latency_ms": self.generation_latency_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "finish_reason": self.finish_reason,
        }


# ─────────────────────────────────────────────────────────────────────
# Defaults
# ─────────────────────────────────────────────────────────────────────

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# HTTP status codes that are safe to retry on the same model
_RETRYABLE_STATUS_CODES = {500, 502, 503, 504}

# Ordered fallback chain: best model first, lightest last.
# Each model has its own independent free-tier quota, so cycling
# through them dramatically increases the chance of a successful call.
DEFAULT_FALLBACK_MODELS: Tuple[str, ...] = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-001",
)

# Lightweight token estimation: ~4 characters per token for English text.
# Used only when Gemini does not return usageMetadata.
_CHARS_PER_TOKEN_ESTIMATE = 4


# ─────────────────────────────────────────────────────────────────────
# Client
# ─────────────────────────────────────────────────────────────────────

class LLMClient:
    """Synchronous Google Gemini client with model fallback, retry, and observability.

    On HTTP 429 (rate-limit), the client automatically cascades to the next
    model in the fallback chain.  Server errors (500–504) are retried on
    the *same* model with exponential backoff.  Safety blocks from Gemini
    are surfaced as structured ``LLMSafetyBlockError`` exceptions.

    After each successful call, ``last_generation_meta`` contains latency,
    token usage, and the model that actually responded — ready for the
    pipeline to embed into ``RAGResponse``.

    Args:
        api_key:            Gemini API key.  Falls back to ``VECTORIA_LLM_API_KEY``.
        model_name:         Primary model (default: ``gemini-2.5-flash``).
        fallback_models:    Ordered fallback model tuple.
        temperature:        Sampling temperature (default: ``0.0``).
        max_output_tokens:  Maximum tokens in the response.
        timeout_seconds:    Per-request HTTP timeout.
        max_retries:        Retry count *per model* for server errors.

    Raises:
        LLMAuthError: If no API key is found.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
        fallback_models: Tuple[str, ...] = DEFAULT_FALLBACK_MODELS,
        temperature: float = 0.0,
        max_output_tokens: int = 1024,
        timeout_seconds: int = 30,
        max_retries: int = 1,
    ) -> None:
        from backend.core.config import settings
        self.api_key = api_key or settings.vectoria_gemini_api_key
        if not self.api_key:
            raise LLMAuthError(
                "No Gemini API key provided. Set the VECTORIA_GEMINI_API_KEY environment "
                "variable or pass api_key directly."
            )

        self.model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

        # Build deduplicated, ordered model chain: primary first, then fallbacks
        seen = {model_name}
        self._model_chain: List[str] = [model_name]
        for m in fallback_models:
            if m not in seen:
                seen.add(m)
                self._model_chain.append(m)

        # Observability: populated after each successful generate() call
        self._last_meta = GenerationMeta()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def last_model_used(self) -> str:
        """The model that produced the most recent successful response."""
        return self._last_meta.model_used or self.model_name

    @property
    def last_generation_meta(self) -> GenerationMeta:
        """Full observability metadata from the last generation call."""
        return self._last_meta

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, messages: List[Dict[str, str]]) -> str:
        """Send a generation request, cascading through models on rate-limit.

        Accepts provider-agnostic messages (role: system/user) and converts
        them internally to Gemini format.  The prompt builder and pipeline
        never see Gemini-specific structures.

        Args:
            messages: List of message dicts (``role``, ``content``),
                      as produced by ``prompt_builder.build_messages()``.

        Returns:
            The model's response text.

        Raises:
            LLMTimeoutError:      On timeout after all retries.
            LLMRateLimitError:    On persistent 429 across ALL models.
            LLMAuthError:         On 401/403 (not retried).
            LLMSafetyBlockError:  On Gemini safety filter refusal.
            LLMGenerationError:   On unexpected response format.
        """
        gen_start = time.perf_counter()
        payload = self._build_payload(messages)
        last_exception: Optional[Exception] = None

        for idx, model in enumerate(self._model_chain):
            result = self._try_model(model, payload)

            if isinstance(result, tuple):
                # Success: (text, raw_response_data)
                text, raw_data = result
                gen_ms = int((time.perf_counter() - gen_start) * 1000)
                self._last_meta = self._extract_meta(
                    raw_data, model, gen_ms, messages
                )

                logger.info(
                    "LLM generation success | model=%s latency_ms=%d "
                    "prompt_tokens=%d completion_tokens=%d finish=%s",
                    model, gen_ms,
                    self._last_meta.prompt_tokens,
                    self._last_meta.completion_tokens,
                    self._last_meta.finish_reason,
                )
                return text

            # result is an exception — decide whether to cascade
            last_exception = result

            if isinstance(result, (LLMRateLimitError, LLMGenerationError)):
                # 429 or server errors exhausted — try the next model
                next_model = (
                    self._model_chain[idx + 1]
                    if idx + 1 < len(self._model_chain)
                    else "NONE"
                )
                logger.info(
                    "Model unavailable, cascading | model=%s reason=%s next=%s",
                    model, type(result).__name__, next_model,
                )
                continue

            # Non-cascadable error (auth, safety) — stop immediately
            raise result

        # All models exhausted
        raise last_exception or LLMGenerationError("All models exhausted")

    # ------------------------------------------------------------------
    # Internal: per-model request with retry
    # ------------------------------------------------------------------

    def _try_model(
        self, model: str, payload: dict
    ) -> tuple[str, dict] | Exception:
        """Attempt generation with a single model, retrying on server errors.

        Returns:
            ``(response_text, raw_json)`` on success, or an ``Exception``
            on failure for the caller to decide whether to cascade.
        """
        url = f"{_GEMINI_BASE_URL}/{model}:generateContent?key={self.api_key}"
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 2):
            try:
                response = http_client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout_seconds,
                )
            except http_client.exceptions.Timeout:
                last_exception = LLMTimeoutError(
                    f"Request timed out after {self.timeout_seconds}s "
                    f"(model={model}, attempt {attempt})"
                )
                logger.warning(
                    "LLM timeout | model=%s attempt=%d/%d",
                    model, attempt, self.max_retries + 1,
                )
                self._backoff(attempt)
                continue
            except http_client.exceptions.RequestException as e:
                last_exception = LLMGenerationError(f"Request failed: {e}")
                logger.warning(
                    "LLM request error | model=%s attempt=%d | error=%s",
                    model, attempt, str(e),
                )
                self._backoff(attempt)
                continue

            status = response.status_code

            # -- Auth errors: not retryable, not cascadable ----------------
            if status in (401, 403):
                return LLMAuthError(
                    f"Authentication failed (HTTP {status}). "
                    "Check your VECTORIA_LLM_API_KEY."
                )

            # -- Rate limit: cascade to next model, don't retry same -------
            if status == 429:
                logger.warning("LLM rate-limited | model=%s", model)
                return LLMRateLimitError(f"HTTP 429 on model {model}")

            # -- Server errors: retry on same model with backoff -----------
            if status in _RETRYABLE_STATUS_CODES:
                last_exception = LLMGenerationError(
                    f"HTTP {status} on model {model} (attempt {attempt})"
                )
                logger.warning(
                    "LLM server error | model=%s status=%d attempt=%d/%d",
                    model, status, attempt, self.max_retries + 1,
                )
                self._backoff(attempt)
                continue

            # -- Other client errors: not retryable ------------------------
            if status != 200:
                return LLMGenerationError(
                    f"Unexpected HTTP {status}: {response.text[:300]}"
                )

            # -- Parse successful response ---------------------------------
            raw_data = response.json()
            text = self._parse_response(raw_data)
            return (text, raw_data)

        # Retries exhausted for this model
        return last_exception or LLMGenerationError(
            f"All retries exhausted for model {model}"
        )

    # ------------------------------------------------------------------
    # Internal: payload construction
    # ------------------------------------------------------------------

    def _build_payload(self, messages: List[Dict[str, str]]) -> dict:
        """Convert provider-agnostic messages to Gemini API format.

        Mapping:
            - role=system     → ``systemInstruction.parts``
            - role=user       → ``contents[].role=user``
            - role=assistant  → ``contents[].role=model``
        """
        payload: dict = {
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_output_tokens,
            }
        }

        contents = []
        for msg in messages:
            role = msg["role"]
            text = msg["content"]

            if role == "system":
                payload["systemInstruction"] = {
                    "parts": [{"text": text}]
                }
            elif role == "user":
                contents.append({
                    "role": "user",
                    "parts": [{"text": text}],
                })
            elif role in ("assistant", "model"):
                contents.append({
                    "role": "model",
                    "parts": [{"text": text}],
                })

        payload["contents"] = contents
        return payload

    # ------------------------------------------------------------------
    # Internal: response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(data: dict) -> str:
        """Extract the model's text from the Gemini API response.

        Handles three Gemini-specific cases:
            1. Normal completion — text extracted from candidates[0].
            2. Safety block — no candidates, or candidate with SAFETY
               finish reason.  Raises ``LLMSafetyBlockError``.
            3. Malformed response — missing expected fields.
               Raises ``LLMGenerationError``.
        """
        candidates = data.get("candidates")

        # -- Case: no candidates at all (safety block at request level) ----
        if not candidates:
            # Gemini returns blockReason in promptFeedback when the
            # entire prompt is blocked
            block_reason = (
                data.get("promptFeedback", {})
                .get("blockReason", "UNKNOWN")
            )
            raise LLMSafetyBlockError(
                f"Generation blocked by safety filter: {block_reason}"
            )

        candidate = candidates[0]

        # -- Case: candidate exists but was stopped by safety filter -------
        finish_reason = candidate.get("finishReason", "")
        if finish_reason == "SAFETY":
            safety_ratings = candidate.get("safetyRatings", [])
            blocked_categories = [
                r.get("category", "UNKNOWN")
                for r in safety_ratings
                if r.get("blocked", False)
            ]
            raise LLMSafetyBlockError(
                f"Generation stopped by safety filter: "
                f"categories={blocked_categories}"
            )

        # -- Case: normal completion — extract text ------------------------
        try:
            parts = candidate["content"]["parts"]
            text_parts = [p["text"] for p in parts if "text" in p]
            if not text_parts:
                raise LLMGenerationError(
                    "Response contains no text parts"
                )
            return "".join(text_parts)
        except (KeyError, TypeError) as e:
            raise LLMGenerationError(
                f"Unexpected response structure: {e}"
            ) from e

    # ------------------------------------------------------------------
    # Internal: observability metadata extraction
    # ------------------------------------------------------------------

    def _extract_meta(
        self,
        raw_data: dict,
        model: str,
        gen_ms: int,
        messages: List[Dict[str, str]],
    ) -> GenerationMeta:
        """Build observability metadata from the raw Gemini response.

        Uses ``usageMetadata`` when available.  Falls back to a lightweight
        character-based estimation (len / 4) for prompt tokens when the
        API does not provide usage data.
        """
        usage = raw_data.get("usageMetadata", {})

        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)
        total_tokens = usage.get("totalTokenCount", 0)

        # Fallback estimation if Gemini omits usage metadata
        if total_tokens == 0:
            input_chars = sum(len(m.get("content", "")) for m in messages)
            prompt_tokens = input_chars // _CHARS_PER_TOKEN_ESTIMATE

            # Estimate completion tokens from the response text
            candidates = raw_data.get("candidates", [])
            if candidates:
                try:
                    parts = candidates[0]["content"]["parts"]
                    output_chars = sum(len(p.get("text", "")) for p in parts)
                    completion_tokens = output_chars // _CHARS_PER_TOKEN_ESTIMATE
                except (KeyError, TypeError, IndexError):
                    completion_tokens = 0

            total_tokens = prompt_tokens + completion_tokens

        # Extract finish reason from the first candidate
        finish_reason = ""
        candidates = raw_data.get("candidates", [])
        if candidates:
            finish_reason = candidates[0].get("finishReason", "")

        return GenerationMeta(
            model_used=model,
            generation_latency_ms=gen_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            finish_reason=finish_reason,
        )

    # ------------------------------------------------------------------
    # Internal: backoff
    # ------------------------------------------------------------------

    @staticmethod
    def _backoff(attempt: int) -> None:
        """Exponential backoff: 1s, 2s, 4s, ... capped at 8s."""
        wait = min(2 ** (attempt - 1), 8)
        time.sleep(wait)
