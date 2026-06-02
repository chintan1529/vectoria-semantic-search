import pytest
from fastapi.testclient import TestClient
from backend.api import app

client = TestClient(app)

def test_metrics_endpoint():
    """
    Ensure the Prometheus metrics endpoint is mounted and returning valid 
    Prometheus exposition formatted data.
    """
    response = client.get("/metrics")
    
    # 200 OK is expected
    assert response.status_code == 200
    
    # The content should be plain text and contain Prometheus formatted strings
    assert "text/plain" in response.headers["content-type"]
    
    content = response.text
    # Check that our custom metrics or standard python metrics are present
    assert "vectoria_requests_total" in content or "python_gc" in content
