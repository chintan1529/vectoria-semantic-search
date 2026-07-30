"""
Vectoria Core Exceptions & Provider Error Hierarchy (Phase 12)
"""

class VectoriaError(Exception):
    """Base exception for all Vectoria system errors."""
    pass

class ConfigurationError(VectoriaError):
    """Raised when configuration validation fails at startup."""
    pass

class ProviderError(VectoriaError):
    """Base exception for all LLM provider failures."""
    def __init__(self, message: str, provider: str = "unknown", model: str = "unknown"):
        super().__init__(message)
        self.provider = provider
        self.model = model

class AuthenticationError(ProviderError):
    """Raised when provider API key or authentication fails."""
    pass

class RateLimitError(ProviderError):
    """Raised when provider quota or rate limit is exceeded."""
    pass

class TimeoutError(ProviderError):
    """Raised when provider API request times out."""
    pass

class ConnectionError(ProviderError):
    """Raised when provider API network connection fails."""
    pass

class QuotaExceededError(ProviderError):
    """Raised when provider credit or quota is exhausted."""
    pass

class ProviderUnavailableError(ProviderError):
    """Raised when provider health check or endpoint fails."""
    pass

class ModelNotFoundError(ProviderError):
    """Raised when specified model is not supported or accessible."""
    pass
