import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from backend.core.logging import logger

class TelemetryMiddleware(BaseHTTPMiddleware):
    """
    Records request execution time and logs basic request telemetry.
    Ensures that every request is traceable via standard headers.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        request_id = str(uuid.uuid4())
        
        # Process the request
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"Request failed: {request.method} {request.url.path} - {str(e)}", trace_id=request_id)
            raise
            
        process_time_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Log telemetry for API calls (excluding health checks to avoid noise)
        if request.url.path.startswith("/api/"):
            logger.info(
                f"API Request | method={request.method} path={request.url.path} "
                f"status={response.status_code} duration_ms={process_time_ms}",
                trace_id=request_id
            )
            
        # Inject headers for advanced browser debugging and observability
        response.headers["Server-Timing"] = f"total;dur={process_time_ms}"
        response.headers["X-Response-Time"] = f"{process_time_ms}ms"
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Vectoria-Version"] = "2.0.0-enterprise"
        
        return response
