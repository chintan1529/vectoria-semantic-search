from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.core.startup import startup_event, shutdown_event, state
from backend.middleware.telemetry import TelemetryMiddleware
from backend.routes.query import router as query_router
from backend.observability.metrics import setup_metrics
from backend.observability.tracing import setup_tracing

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup tracing and metrics before starting core components
    setup_tracing(app)
    startup_event()
    yield
    shutdown_event()

# Initialize the FastAPI application
app = FastAPI(
    title="Vectoria RAG API",
    description="Production-grade semantic search and grounded generation API.",
    version="0.1.0",
    lifespan=lifespan,
)

# Setup Prometheus metrics endpoint and middleware
setup_metrics(app)

# Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TelemetryMiddleware)

# Mount Routers
app.include_router(query_router, prefix="/api", tags=["Search & Generation"])

# Health Checks
@app.get("/health", tags=["System"])
async def health_check():
    """Basic alive check for load balancers."""
    return {"status": "ok"}

@app.get("/ready", tags=["System"])
async def readiness_check():
    """Verifies that all models and indexes are loaded into memory."""
    if state.is_ready:
        return {
            "status": "ready",
            "model_state": state.model_state.value,
            "startup_time_ms": state.startup_time_ms,
        }
    else:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={
                "status": state.model_state.value,
                "startup_error": state.startup_error,
            },
        )

# If running this file directly for debugging
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)
