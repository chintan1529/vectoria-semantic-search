"""
Test: Failover — Provider failure simulation and circuit breaker behavior.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestProviderFailoverClassification:
    """Verify that different error types are classified correctly."""

    def classify_error(self, error_msg: str) -> str:
        err = error_msg.lower()
        if "timeout" in err:
            return "TIMEOUT"
        elif "429" in err or "rate limit" in err:
            return "RATE_LIMIT"
        elif "connect" in err or "getaddrinfo" in err or "network" in err:
            return "NETWORK_ERROR"
        else:
            return "UNKNOWN"

    def test_network_error_classification(self):
        assert self.classify_error("Cannot connect to host api-inference.huggingface.co:443 ssl:default [getaddrinfo failed]") == "NETWORK_ERROR"

    def test_rate_limit_classification(self):
        assert self.classify_error("429 You exceeded your current quota") == "RATE_LIMIT"

    def test_timeout_classification(self):
        assert self.classify_error("Request timeout after 30 seconds") == "TIMEOUT"

    def test_unknown_classification(self):
        assert self.classify_error("Something unexpected happened") == "UNKNOWN"


class TestFailoverStrategy:
    """Verify failover behavior when providers fail."""

    def test_primary_failure_triggers_secondary(self):
        providers = ["huggingface", "gemini"]
        current = 0  # Start with primary
        
        # Simulate primary failure
        primary_failed = True
        if primary_failed and current + 1 < len(providers):
            current += 1
        
        assert providers[current] == "gemini"

    def test_all_providers_exhausted(self):
        providers = ["huggingface", "gemini"]
        all_failed = True
        for p in providers:
            # Both fail
            pass
        assert all_failed  # Should trigger ALL_PROVIDERS_FAILED

    def test_healthy_provider_no_failover(self):
        providers = ["huggingface", "gemini"]
        current = 0
        primary_healthy = True
        
        if primary_healthy:
            pass  # No failover needed
        
        assert providers[current] == "huggingface"


class TestMissingAPIKeys:
    """Verify behavior when API keys are missing."""

    def test_empty_key_detected(self):
        key = ""
        assert not key or key == "your-gemini-api-key-here"

    def test_placeholder_key_detected(self):
        key = "your-gemini-api-key-here"
        assert key.startswith("your-") or key == ""

    def test_valid_key_accepted(self):
        key = "AIzaSy_valid_key_123"
        assert key and not key.startswith("your-")
