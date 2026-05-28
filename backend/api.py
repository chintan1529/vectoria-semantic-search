from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.core.startup import startup_event, shutdown_event, state
from backend.middleware.telemetry import TelemetryMiddleware
from backend.routes.query import router as query_router

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
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
    is_ready = all([
        state.engine is not None,
        state.llm is not None,
        state.rag is not None
    ])
    
    if is_ready:
        return {"status": "ready"}
    else:
        # 503 Service Unavailable if models are still loading
        from fastapi import Response
        return Response(content='{"status": "loading"}', media_type="application/json", status_code=503)

# If running this file directly for debugging
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)
