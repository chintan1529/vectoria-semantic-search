"""
Phase 13 Test Suite: Provider Architecture, Configuration Validation & Immuntability
"""
import pytest
from backend.core.config import Settings
from backend.core.exceptions import ConfigurationError
from backend.core.config_validator import validate_environment
from backend.providers.factory import ProviderFactory

def test_config_immutability():
    """Verify settings are frozen and immutable after creation."""
    s = Settings(VECTORIA_GEMINI_API_KEY="test_key")
    with pytest.raises(Exception):
        s.vectoria_gemini_model = "mutated_model"

def test_missing_chat_provider_api_key_raises_error(monkeypatch):
    """Verify missing API key for primary chat provider aborts startup."""
    from backend.core.config import settings
    bad_settings = settings.model_copy(update={"vectoria_chat_provider": "gemini", "vectoria_gemini_api_key": ""})
    monkeypatch.setattr("backend.core.config.settings", bad_settings)
    monkeypatch.setattr("backend.core.config_validator.settings", bad_settings)
    with pytest.raises(ConfigurationError):
        validate_environment()

def test_provider_capabilities_model():
    """Verify provider capabilities model returns expected flags."""
    from backend.providers.base_provider import ProviderCapabilities
    caps = ProviderCapabilities(supports_streaming=True, max_context=8000)
    assert caps.supports_streaming is True
    assert caps.max_context == 8000
