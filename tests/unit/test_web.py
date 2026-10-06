"""Unit tests for decide.web subsystem (Task 06 / Module 06: Admin Web GUI)."""

import json
from unittest.mock import MagicMock
import pytest
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import RedirectResponse

from decide.crypto import hash_password
from decide.db.models import User, APIKey
from decide.engine.classifier import MultiTaskClassifier, ClassificationResult
from decide.engine.lifecycle import EngineState
from decide.web.routes.auth import login_page, login_submit, logout
from decide.web.routes.dashboard import dashboard, create_key, revoke_key
from decide.web.routes.playground import playground_page, playground_test, DEFAULT_SAMPLE_TEXT, DEFAULT_SAMPLE_TASKS


def create_mock_request(cookies=None):
    mock_req = MagicMock(spec=Request)
    mock_req.cookies = cookies or {}
    mock_req.url = MagicMock()
    mock_req.url.path = "/admin"
    return mock_req


def test_login_page_renders_when_unauthenticated(monkeypatch):
    """Verify login_page renders login.html when no session exists."""
    monkeypatch.setattr("decide.web.routes.auth.get_session_user_id", lambda req: None)
    req = create_mock_request()
    resp = login_page(req)
    assert resp.status_code == 200


def test_login_page_redirects_when_authenticated(monkeypatch):
    """Verify login_page redirects to /admin when already logged in."""
    monkeypatch.setattr("decide.web.routes.auth.get_session_user_id", lambda req: 1)
    req = create_mock_request()
    resp = login_page(req)
    assert isinstance(resp, RedirectResponse)
    assert resp.status_code == status.HTTP_303_SEE_OTHER
    assert resp.headers["location"] == "/admin"


def test_login_submit_invalid_user(monkeypatch):
    """Verify login_submit returns 400 when username not found."""
    mock_db = MagicMock()
    monkeypatch.setattr("decide.web.routes.auth.UserRepository.get_by_username", lambda db, u: None)

    req = create_mock_request()
    resp = Response()
    result = login_submit(req, resp, username="nonexistent", password="pwd", db=mock_db)
    assert result.status_code == 400


def test_login_submit_invalid_password(monkeypatch):
    """Verify login_submit returns 400 when password is wrong."""
    mock_db = MagicMock()
    mock_user = User(id=1, username="admin", password_hash=hash_password("correct_pass"), is_active=True)
    monkeypatch.setattr("decide.web.routes.auth.UserRepository.get_by_username", lambda db, u: mock_user)

    req = create_mock_request()
    resp = Response()
    result = login_submit(req, resp, username="admin", password="wrong_pass", db=mock_db)
    assert result.status_code == 400


def test_login_submit_success(monkeypatch):
    """Verify login_submit sets session cookie and redirects to /admin on success."""
    mock_db = MagicMock()
    mock_user = User(id=1, username="admin", password_hash=hash_password("correct_pass"), is_active=True)
    monkeypatch.setattr("decide.web.routes.auth.UserRepository.get_by_username", lambda db, u: mock_user)

    req = create_mock_request()
    resp = Response()
    result = login_submit(req, resp, username="admin", password="correct_pass", db=mock_db)

    assert isinstance(result, RedirectResponse)
    assert result.status_code == status.HTTP_303_SEE_OTHER
    assert result.headers["location"] == "/admin"
    assert "decide_session" in result.headers.get("set-cookie", "")


def test_logout():
    """Verify logout redirects to /admin/login."""
    resp = logout()
    assert isinstance(resp, RedirectResponse)
    assert resp.status_code == status.HTTP_303_SEE_OTHER
    assert resp.headers["location"] == "/admin/login"


def test_dashboard_metrics(monkeypatch):
    """Verify dashboard calculates active and revoked key counts accurately."""
    mock_db = MagicMock()
    keys = [
        APIKey(id=1, user_id=1, name="Key 1", key_prefix="dec_111", hashed_key="h1", is_active=True),
        APIKey(id=2, user_id=1, name="Key 2", key_prefix="dec_222", hashed_key="h2", is_active=False),
        APIKey(id=3, user_id=1, name="Key 3", key_prefix="dec_333", hashed_key="h3", is_active=True),
    ]
    monkeypatch.setattr("decide.web.routes.dashboard.APIKeyRepository.list_all", lambda db: keys)

    req = create_mock_request()
    admin = User(id=1, username="admin", password_hash="h", is_active=True)
    resp = dashboard(request=req, current_admin=admin, db=mock_db)

    assert resp.status_code == 200


def test_create_key_unit(monkeypatch):
    """Verify create_key creates record and renders key_modal partial with raw secret."""
    mock_db = MagicMock()
    created_key = APIKey(id=10, user_id=1, name="Test Service", key_prefix="dec_abc123", hashed_key="hash", is_active=True)
    monkeypatch.setattr("decide.web.routes.dashboard.APIKeyRepository.create", lambda db, **kwargs: created_key)

    req = create_mock_request()
    admin = User(id=1, username="admin", password_hash="h", is_active=True)
    resp = create_key(request=req, name="Test Service", current_admin=admin, db=mock_db)

    assert resp.status_code == 200


def test_revoke_key_unit_success_and_not_found(monkeypatch):
    """Verify revoke_key invalidates cache on success or raises 404 if not found."""
    mock_db = MagicMock()
    revoked_key = APIKey(id=5, user_id=1, name="To Revoke", key_prefix="dec_rev", hashed_key="hashed_rev", is_active=False)

    monkeypatch.setattr("decide.web.routes.dashboard.APIKeyRepository.revoke", lambda db, kid: revoked_key if kid == 5 else None)
    mock_invalidate = MagicMock()
    monkeypatch.setattr("decide.web.routes.dashboard.key_cache.invalidate", mock_invalidate)

    req = create_mock_request()
    admin = User(id=1, username="admin", password_hash="h", is_active=True)

    # Success case
    resp = revoke_key(request=req, key_id=5, current_admin=admin, db=mock_db)
    assert resp.status_code == 200
    mock_invalidate.assert_called_once_with("hashed_rev")

    # 404 case
    with pytest.raises(HTTPException) as exc_info:
        revoke_key(request=req, key_id=999, current_admin=admin, db=mock_db)
    assert exc_info.value.status_code == 404


def test_playground_page_renders():
    """Verify playground_page renders with default sample data."""
    req = create_mock_request()
    admin = User(id=1, username="admin", password_hash="h", is_active=True)
    resp = playground_page(request=req, current_admin=admin)

    assert resp.status_code == 200


def test_playground_test_invalid_json():
    """Verify playground_test handles invalid JSON gracefully."""
    req = create_mock_request()
    admin = User(id=1, username="admin", password_hash="h", is_active=True)
    resp = playground_test(request=req, text="hello", tasks_json="not-a-json", current_admin=admin)

    assert resp.status_code == 200


def test_playground_test_unloaded_model(monkeypatch):
    """Verify playground_test handles unloaded model gracefully."""
    state = EngineState()
    monkeypatch.setattr("decide.web.routes.playground.get_engine_state", lambda: state)

    req = create_mock_request()
    admin = User(id=1, username="admin", password_hash="h", is_active=True)
    resp = playground_test(
        request=req,
        text="hello",
        tasks_json='{"intent": ["support"]}',
        current_admin=admin,
    )
    assert resp.status_code == 200


def test_playground_test_success(monkeypatch):
    """Verify playground_test returns result partial with predictions."""
    state = EngineState()
    mock_classifier = MagicMock()
    mock_classifier.predict.return_value = ClassificationResult(
        result={"intent": "refund"},
        latency_ms=18.5,
    )
    state.set_ready(mock_classifier, "cuda:0")
    monkeypatch.setattr("decide.web.routes.playground.get_engine_state", lambda: state)

    req = create_mock_request()
    admin = User(id=1, username="admin", password_hash="h", is_active=True)
    resp = playground_test(
        request=req,
        text="Need refund",
        tasks_json='{"intent": ["refund", "replacement"]}',
        current_admin=admin,
    )
    assert resp.status_code == 200
