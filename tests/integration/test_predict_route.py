"""Integration tests for POST /predict endpoint (Module 05: REST API Controller)."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from decide.auth.api_key import key_cache
from decide.crypto import hash_api_key
from decide.db.repository import UserRepository, APIKeyRepository
from decide.db.session import get_engine, init_db, get_session_context, get_db
from decide.engine.classifier import MultiTaskClassifier
from decide.engine.lifecycle import get_engine_state
from decide.main import app


class MockExtractor:
    def extract(self, text, tasks):
        return {
            "intent": "replacement",
            "urgency": "critical",
        }


@pytest.fixture
def setup_integration_env(tmp_path: Path):
    """Sets up a test database and mocks the inference engine."""
    db_file = tmp_path / "predict_test.db"
    engine = get_engine(db_file)
    init_db(engine)

    # Seed test user and active key
    raw_key = "dec_integrationtestkey1234567890123"
    hashed = hash_api_key(raw_key)

    with get_session_context(engine) as session:
        user = UserRepository.create(session, "test_admin", "hash")
        key_record = APIKeyRepository.create(
            session,
            user_id=user.id,
            name="Integration Key",
            key_prefix="dec_integr",
            hashed_key=hashed,
        )
        key_id = key_record.id

    # Mock engine ready
    classifier = MultiTaskClassifier(extractor=MockExtractor(), device="cpu")
    get_engine_state().set_ready(classifier, "cpu")
    key_cache.clear()

    # Override get_db dependency
    def override_get_db():
        with get_session_context(engine) as s:
            yield s

    app.dependency_overrides[get_db] = override_get_db

    yield {
        "engine": engine,
        "raw_key": raw_key,
        "key_id": key_id,
        "client": TestClient(app),
    }

    app.dependency_overrides.clear()
    key_cache.clear()


def test_predict_missing_api_key(setup_integration_env):
    client = setup_integration_env["client"]
    resp = client.post(
        "/predict",
        json={"text": "hello", "tasks": {"intent": ["support"]}},
    )
    assert resp.status_code == 401
    assert "Missing X-API-Key" in resp.text


def test_predict_invalid_api_key(setup_integration_env):
    client = setup_integration_env["client"]
    resp = client.post(
        "/predict",
        headers={"X-API-Key": "dec_completelyinvalidkey1234567890"},
        json={"text": "hello", "tasks": {"intent": ["support"]}},
    )
    assert resp.status_code == 403


def test_predict_input_length_exceeded(setup_integration_env):
    client = setup_integration_env["client"]
    raw_key = setup_integration_env["raw_key"]
    resp = client.post(
        "/predict",
        headers={"X-API-Key": raw_key},
        json={"text": "x" * 8001, "tasks": {"intent": ["support"]}},
    )
    assert resp.status_code == 422


def test_predict_success_and_result_schema(setup_integration_env):
    client = setup_integration_env["client"]
    raw_key = setup_integration_env["raw_key"]
    payload = {
        "text": "My order arrived broken and I want a replacement immediately.",
        "tasks": {
            "intent": ["refund", "replacement", "tracking", "general_inquiry"],
            "urgency": ["low", "normal", "critical"],
        },
    }

    resp = client.post("/predict", headers={"X-API-Key": raw_key}, json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "result" in data
    assert data["result"]["intent"] == "replacement"
    assert data["result"]["urgency"] == "critical"
    assert "X-Response-Time" in resp.headers


def test_predict_revoked_key_rejection(setup_integration_env):
    client = setup_integration_env["client"]
    raw_key = setup_integration_env["raw_key"]
    key_id = setup_integration_env["key_id"]
    engine = setup_integration_env["engine"]

    # Revoke key
    with get_session_context(engine) as s:
        APIKeyRepository.revoke(s, key_id)
    key_cache.clear()

    resp = client.post(
        "/predict",
        headers={"X-API-Key": raw_key},
        json={"text": "hello", "tasks": {"intent": ["support"]}},
    )
    assert resp.status_code == 403
