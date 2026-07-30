from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import psutil
import os
from backend.core.startup import state

router = APIRouter()

@router.get("/routes")
def get_routes(request: Request):
    """Returns all registered application routes."""
    routes = []
    for route in request.app.routes:
        if hasattr(route, "methods"):
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else [],
                "name": route.name
            })
    return {"routes": routes}

@router.get("/health")
def health_check():
    """Basic alive check."""
    return {"status": "ok"}

@router.get("/ready")
def readiness_check():
    """Returns structured readiness report with per-subsystem status."""
    report = state.readiness_report()
    if state.is_ready:
        return report
    return JSONResponse(status_code=503, content=report)

@router.get("/status")
def status_check():
    """Comprehensive system status."""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    provider_info = state.llm.model_info() if state.llm else {}
    
    return {
        "status": "healthy" if state.is_ready else "degraded",
        "provider_health": provider_info,
        "memory": {
            "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
            "vms_mb": round(memory_info.vms / 1024 / 1024, 2)
        },
        "engine": {
            "is_loaded": state.engine is not None,
            "index_size": len(state.engine.mapping) if state.engine and hasattr(state.engine, "mapping") else 0
        }
    }

@router.get("/models")
def get_models():
    """Returns loaded models and providers."""
    return {
        "embedding": "all-MiniLM-L6-v2",
        "reranker": "bge-reranker-base",
        "generation_provider": state.llm.model_info() if state.llm else None
    }
