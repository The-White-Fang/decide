"""Unit tests for decide.api subsystem (Task 05 / Module 05: REST API Controller)."""

from unittest.mock import MagicMock
import pytest
from fastapi import FastAPI, Response, HTTPException, status
from fastapi.testclient import TestClient

from decide.api.routes.health import health_probe, HealthResponse
from decide.api.routes.predict import predict_intent, PredictResponse
from decide.api.middleware import setup_middleware_and_exceptions, SecurityAndLatencyMiddleware
from decide.auth.guardrails import PredictInputSchema
from decide.db.models import APIKey
from decide.engine.classifier import MultiTaskClassifier, ClassificationResult, InferenceException
from decide.engine.lifecycle import EngineState


def test_health_probe_unit_healthy(monkeypatch):
    """Verify health_probe returns 200 healthy when engine is ready and DB is responsive."""
    state = EngineState()
    classifier = MultiTaskClassifier(extractor=None, device="cpu")
    state.set_ready(classifier, "cpu")
    monkeypatch.setattr("decide.api.routes.health.get_engine_state", lambda: state)

    # Mock DB context manager to succeed
    mock_session = MagicMock()
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_session
    mock_cm.__exit__.return_value = None
    monkeypatch.setattr("decide.api.routes.health.get_session_context", lambda: mock_cm)

    response = Response()
    res = health_probe(response)

    assert isinstance(res, HealthResponse)
    assert res.status == "healthy"
    assert res.model_loaded is True
    assert res.device == "cpu"
    assert response.status_code == 200


def test_health_probe_unit_initializing(monkeypatch):
    """Verify health_probe returns 503 initializing when engine is not loaded."""
    state = EngineState()
    monkeypatch.setattr("decide.api.routes.health.get_engine_state", lambda: state)

    response = Response()
    res = health_probe(response)

    assert res.status == "initializing"
    assert res.model_loaded is False
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


def test_health_probe_unit_degraded_db(monkeypatch):
    """Verify health_probe returns 503 degraded when model is loaded but DB fails."""
    state = EngineState()
    state.set_ready(MultiTaskClassifier(extractor=None, device="cuda:0"), "cuda:0")
    monkeypatch.setattr("decide.api.routes.health.get_engine_state", lambda: state)

    # Mock DB context manager to raise an exception
    mock_cm = MagicMock()
    mock_cm.__enter__.side_effect = RuntimeError("Database disk full")
    monkeypatch.setattr("decide.api.routes.health.get_session_context", lambda: mock_cm)

    response = Response()
    res = health_probe(response)

    assert res.status == "degraded"
    assert res.model_loaded is True
    assert res.device == "cuda:0"
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


def test_predict_route_unit_uninitialized_engine(monkeypatch):
    """Verify predict_intent raises HTTPException 500 when engine is not loaded."""
    state = EngineState()
    monkeypatch.setattr("decide.api.routes.predict.get_engine_state", lambda: state)

    payload = PredictInputSchema(
        text="Sample inquiry",
        tasks={"intent": ["support", "billing"]},
    )
    mock_bg = MagicMock()
    mock_key = APIKey(id=1, name="test", hashed_key="h", is_active=True)

    with pytest.raises(HTTPException) as exc_info:
        predict_intent(payload=payload, background_tasks=mock_bg, current_key=mock_key)

    assert exc_info.value.status_code == 500
    assert "not loaded or engine is uninitialized" in exc_info.value.detail


def test_predict_route_unit_inference_failure(monkeypatch):
    """Verify predict_intent raises HTTPException 500 when model inference fails."""
    state = EngineState()
    mock_classifier = MagicMock()
    mock_classifier.predict.side_effect = RuntimeError("GPU out of memory")
    state.set_ready(mock_classifier, "cuda:0")
    monkeypatch.setattr("decide.api.routes.predict.get_engine_state", lambda: state)

    payload = PredictInputSchema(
        text="Sample inquiry",
        tasks={"intent": ["support"]},
    )
    mock_bg = MagicMock()
    mock_key = APIKey(id=1, name="test", hashed_key="h", is_active=True)

    with pytest.raises(HTTPException) as exc_info:
        predict_intent(payload=payload, background_tasks=mock_bg, current_key=mock_key)

    assert exc_info.value.status_code == 500
    assert "Model inference failed" in exc_info.value.detail


def test_predict_route_unit_success(monkeypatch):
    """Verify predict_intent returns structured PredictResponse on success."""
    state = EngineState()
    mock_classifier = MagicMock()
    mock_classifier.predict.return_value = ClassificationResult(
        result={"intent": "support"},
        latency_ms=15.2,
    )
    state.set_ready(mock_classifier, "cpu")
    monkeypatch.setattr("decide.api.routes.predict.get_engine_state", lambda: state)

    payload = PredictInputSchema(
        text="Help with refund",
        tasks={"intent": ["support", "billing"]},
    )
    mock_bg = MagicMock()
    mock_key = APIKey(id=1, name="test", hashed_key="h", is_active=True)

    res = predict_intent(payload=payload, background_tasks=mock_bg, current_key=mock_key)

    assert isinstance(res, PredictResponse)
    assert res.result == {"intent": "support"}
    mock_classifier.predict.assert_called_once_with(
        "Help with refund",
        {"intent": ["support", "billing"]},
    )


def test_security_and_latency_middleware():
    """Verify SecurityAndLatencyMiddleware attaches latency and security headers."""
    app = FastAPI()
    setup_middleware_and_exceptions(app)

    @app.get("/ping")
    def ping():
        return {"pong": True}

    client = TestClient(app)
    resp = client.get("/ping")

    assert resp.status_code == 200
    assert resp.json() == {"pong": True}
    assert "X-Response-Time" in resp.headers
    assert resp.headers["X-Response-Time"].endswith("ms")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_inference_exception_global_handler():
    """Verify InferenceException is caught by global handler and returned as 500 JSON."""
    app = FastAPI()
    setup_middleware_and_exceptions(app)

    @app.get("/trigger-inference-error")
    def trigger():
        raise InferenceException("CUDA core dump error")

    client = TestClient(app)
    resp = client.get("/trigger-inference-error")

    assert resp.status_code == 500
    data = resp.json()
    assert "detail" in data
    assert "Model inference failed: CUDA core dump error" in data["detail"]
