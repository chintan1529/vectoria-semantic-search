from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.core.startup import startup_event, shutdown_event, state
from backend.middleware.telemetry import TelemetryMiddleware
from backend.routes.query import router as query_router
from backend.observability.metrics import setup_metrics
from backend.observability.tracing import setup_tracing

from contextlib import asynccontextmanager

from backend.core.async_queue import async_worker_queue

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup tracing and metrics before starting core components
    setup_tracing(app)
    async_worker_queue.start()
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

from backend.routes.knowledge_graph_routes import router as kg_router
app.include_router(kg_router, prefix="/api/query/knowledge-graph", tags=["Intelligence"])

from backend.routes.research import router as research_router
app.include_router(research_router, prefix="/api/research", tags=["Research"])

from backend.routes.inspect import router as inspect_router
app.include_router(inspect_router, prefix="/api/query", tags=["Inspect"])

from backend.routes.health import router as health_router
app.include_router(health_router, prefix="/api", tags=["System"])

from backend.routes.analytics import router as analytics_router
app.include_router(analytics_router, prefix="/api", tags=["Analytics"])

from backend.routes.performance_dashboard import router as perf_router
app.include_router(perf_router, prefix="/api", tags=["Performance"])

# Health and readiness routes are now handled by health_router (/api/health, /api/ready)

# If running this file directly for debugging
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)
