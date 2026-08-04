"""
Langfuse observability integration — optional dependency.
If langfuse is not installed or credentials are missing, all decorators
become transparent no-ops. This ensures the application always starts
regardless of whether langfuse is available.
"""

import os
from backend.core.logging import logger

# Attempt to import langfuse; gracefully degrade if unavailable
try:
    from langfuse import observe as _observe
    _LANGFUSE_AVAILABLE = True
except ImportError:
    _observe = None
    _LANGFUSE_AVAILABLE = False

try:
    from langfuse import langfuse_context
except ImportError:
    langfuse_context = None

LANGFUSE_ENABLED = _LANGFUSE_AVAILABLE and bool(
    os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")
)

if LANGFUSE_ENABLED:
    logger.info("Langfuse observability enabled")
else:
    if not _LANGFUSE_AVAILABLE:
        logger.debug("Langfuse not installed — observability disabled")
    else:
        logger.debug("Langfuse credentials not configured — observability disabled")


def safe_observe(*args, **kwargs):
    """
    A wrapper around the Langfuse @observe decorator that acts as a no-op
    if Langfuse credentials are not provided or the package is not installed.
    """
    if LANGFUSE_ENABLED and _observe is not None:
        return _observe(*args, **kwargs)

    # If not enabled, return a pass-through decorator
    def decorator(func):
        return func
    return decorator


# Re-export langfuse_context so providers can update generation data
safe_langfuse_context = langfuse_context if LANGFUSE_ENABLED else None
