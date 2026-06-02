from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from backend.core.logging import logger
import os

def setup_tracing(app: FastAPI):
    """
    Configures OpenTelemetry for distributed tracing.
    Currently defaults to ConsoleSpanExporter for local dev, 
    but can be extended to OTLP (e.g. Jaeger, Datadog) based on env vars.
    """
    try:
        # Set up the tracing resource
        resource = Resource.create({"service.name": "vectoria-api"})
        provider = TracerProvider(resource=resource)
        
        # If OTLP endpoint is provided, you would configure OTLPSpanExporter here.
        # For now, we use a basic ConsoleSpanExporter wrapped in a Batch processor 
        # so it doesn't block the event loop, but we only enable it if explicitly requested
        # to avoid flooding standard out during dev.
        if os.environ.get("ENABLE_OTEL_CONSOLE", "false").lower() == "true":
            processor = BatchSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)
            
        trace.set_tracer_provider(provider)
        
        # Instrument the FastAPI app
        FastAPIInstrumentor.instrument_app(app)
        logger.info("OpenTelemetry distributed tracing configured successfully.")
        
    except Exception as e:
        logger.warning(f"Failed to configure OpenTelemetry: {e}")
