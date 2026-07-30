"""
SSE Streaming Contract & Schema Test Suite (Phase 9).

Verifies that every SSE payload emitted by StreamingOrchestrator matches
the shared contract schema expected by the frontend.
"""

import json
import pytest
from backend.orchestration.streaming_orchestrator import _build_sse_payload


def test_build_sse_payload_schema():
    """Verify _build_sse_payload enriches data with required contract fields."""
    event = "context"
    data = {"chunks": [{"id": "chunk-1", "title": "Doc", "score": 0.95, "text": "sample"}]}
    request_id = "req-12345"
    seq = 2
    provider = "gemini-2.5-flash"

    raw_json = _build_sse_payload(event, data, request_id, seq, provider)
    payload = json.loads(raw_json)

    # 1. Required Envelope Fields
    assert payload["request_id"] == "req-12345"
    assert payload["seq"] == 2
    assert payload["provider"] == "gemini-2.5-flash"
    assert payload["stage"] == "context"
    assert "timestamp" in payload
    assert "checksum" in payload

    # 2. Payload Domain Schema
    assert "chunks" in payload
    assert isinstance(payload["chunks"], list)
    assert len(payload["chunks"]) == 1
    assert payload["chunks"][0]["id"] == "chunk-1"


def test_phase_event_schema():
    """Verify phase events contain valid phase & status fields."""
    event = "phase"
    data = {"phase": "retrieving", "status": "active"}
    raw_json = _build_sse_payload(event, data, "req-1", 1, "test-provider")
    payload = json.loads(raw_json)

    assert payload["stage"] == "phase"
    assert payload["phase"] == "retrieving"
    assert payload["status"] == "active"


def test_token_event_schema():
    """Verify token events contain text property."""
    event = "token"
    data = {"text": "Hello world"}
    raw_json = _build_sse_payload(event, data, "req-1", 5, "test-provider")
    payload = json.loads(raw_json)

    assert payload["stage"] == "token"
    assert payload["text"] == "Hello world"
