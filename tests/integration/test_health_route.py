"""Integration tests for GET /health endpoint (Module 05: REST API Controller)."""

import pytest
from fastapi.testclient import TestClient
from decide.engine.classifier import MultiTaskClassifier
from decide.engine.lifecycle import get_engine_state
from decide.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_probe_when_initializing(client):
    """Verify /health returns 503 while engine is not loaded."""
    state = get_engine_state()
    state.reset()

    resp = client.get("/health")
    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "initializing"
    assert data["model_loaded"] is False


def test_health_probe_when_healthy(client):
    """Verify /health returns 200 OK when model engine is ready."""
    state = get_engine_state()
    state.set_ready(MultiTaskClassifier(extractor=None, device="cpu"), "cpu")

    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["device"] == "cpu"

    # Verify security and response time headers
    assert "X-Response-Time" in resp.headers
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
