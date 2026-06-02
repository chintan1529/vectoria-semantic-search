from langfuse import observe
try:
    from langfuse import langfuse_context
except ImportError:
    langfuse_context = None

from backend.core.logging import logger
import os

# We don't strictly need to instantiate a client manually if we use decorators,
# but providing a wrapper helps gracefully disable it if API keys are missing.
LANGFUSE_ENABLED = bool(os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"))

def safe_observe(*args, **kwargs):
    """
    A wrapper around the Langfuse @observe decorator that acts as a no-op 
    if Langfuse credentials are not provided. This ensures the app can 
    start in local/dev without breaking.
    """
    if LANGFUSE_ENABLED:
        return observe(*args, **kwargs)
    
    # If not enabled, return a pass-through decorator
    def decorator(func):
        return func
    return decorator

# Re-export langfuse_context so providers can update generation data
safe_langfuse_context = langfuse_context if LANGFUSE_ENABLED else None
