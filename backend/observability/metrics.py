import time
from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram, make_asgi_app

# Define custom Prometheus metrics
VECTORIA_REQUESTS_TOTAL = Counter(
    "vectoria_requests_total", 
    "Total number of requests received", 
    ["method", "endpoint", "status"]
)

VECTORIA_LLM_TOKENS_TOTAL = Counter(
    "vectoria_llm_tokens_total", 
    "Total number of LLM tokens consumed", 
    ["model", "provider", "token_type"]
)

VECTORIA_RETRIEVAL_LATENCY = Histogram(
    "vectoria_retrieval_latency_seconds", 
    "Latency of vector retrieval operations",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
)

VECTORIA_GENERATION_LATENCY = Histogram(
    "vectoria_generation_latency_seconds", 
    "Latency of LLM generation operations",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

def setup_metrics(app: FastAPI):
    """
    Mounts the /metrics endpoint and sets up basic Prometheus metrics.
    """
    # Create the ASGI app for Prometheus metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    
    # Add a middleware to automatically track request counts
    @app.middleware("http")
    async def track_requests(request: Request, call_next):
        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
        except Exception:
            status_code = "500"
            raise
        finally:
            if not request.url.path.startswith("/metrics"):
                VECTORIA_REQUESTS_TOTAL.labels(
                    method=request.method,
                    endpoint=request.url.path,
                    status=status_code
                ).inc()
                
        return response
