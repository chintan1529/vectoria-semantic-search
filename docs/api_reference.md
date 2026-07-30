# Vectoria API Reference

## Endpoints

### `GET /api/status`
Returns the status of the orchestration engine.
**Response**: `{"status": "READY", "version": "1.2.0"}`

### `GET /api/routes`
Returns all registered routes in the backend.

### `POST /api/query/stream`
The primary streaming endpoint for the Vectoria UI.
**Payload**: `{"query": "string"}`
**Response (SSE)**: Streams events of type:
- `phase`
- `context`
- `diagnostics`
- `token`
- `done`
- `trust_verification`

### `POST /api/research/stream`
Performs multi-hop generation using long-context LLMs and comprehensive chunk coverage.

## Failover Semantics
All generation endpoints automatically catch rate limits (`429`) and network errors. If the Primary Provider fails, the request transparently reroutes to the Fallback Provider, emitting `provider_failover_started` via SSE to the client.
