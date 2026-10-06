"""Unit tests for decide.auth subsystem (Task 03 / Module 03)."""

from io import StringIO
from pathlib import Path
import pytest
from fastapi import HTTPException, Response, Request
from pydantic import ValidationError
from decide.auth.api_key import APIKeyCache, KeyCacheItem, verify_api_key, key_cache
from decide.auth.bootstrap import bootstrap_admin
from decide.auth.guardrails import PredictInputSchema
from decide.auth.session import (
    create_session_cookie,
    clear_session_cookie,
    get_session_user_id,
    get_current_admin,
    generate_csrf_token,
    verify_csrf_token,
    SESSION_COOKIE_NAME,
)
from decide.config import Settings
from decide.crypto import hash_password, verify_password, hash_api_key
from decide.db.repository import UserRepository, APIKeyRepository
from decide.db.session import get_engine, init_db, get_session_context


@pytest.fixture
def auth_db_session(tmp_path: Path):
    """Creates a temporary isolated SQLite database file and yields a session."""
    db_file = tmp_path / "test_auth.db"
    engine = get_engine(db_file)
    init_db(engine)

    with get_session_context(engine) as session:
        yield session


def test_guardrails_valid_payload():
    """Verify valid text and tasks payload passes schema validation."""
    payload = PredictInputSchema(
        text="My order arrived broken and I want a replacement immediately.",
        tasks={
            "intent": ["refund", "replacement", "tracking", "general_inquiry"],
            "urgency": ["low", "normal", "critical"],
        },
    )
    assert payload.text.startswith("My order")
    assert len(payload.tasks) == 2


def test_guardrails_text_length_limit():
    """Verify input text exceeding 8,000 characters is rejected."""
    long_text = "a" * 8001
    with pytest.raises(ValidationError):
        PredictInputSchema(text=long_text, tasks={"intent": ["support"]})


def test_guardrails_task_count_limit():
    """Verify requests exceeding 20 task categories are rejected."""
    too_many_tasks = {f"task_{i}": ["label_a", "label_b"] for i in range(21)}
    with pytest.raises(ValidationError):
        PredictInputSchema(text="sample", tasks=too_many_tasks)


def test_guardrails_labels_per_task_limit():
    """Verify tasks exceeding 50 candidate labels are rejected."""
    too_many_labels = {f"label_{i}" for i in range(51)}
    with pytest.raises(ValidationError):
        PredictInputSchema(text="sample", tasks={"category": list(too_many_labels)})


def test_guardrails_empty_tasks_rejected():
    """Verify empty task dictionaries or empty label lists are rejected."""
    with pytest.raises(ValidationError):
        PredictInputSchema(text="sample", tasks={})

    with pytest.raises(ValidationError):
        PredictInputSchema(text="sample", tasks={"intent": []})


def test_guardrails_duplicate_labels_rejected():
    """Verify duplicate candidate labels in a task are rejected."""
    with pytest.raises(ValidationError):
        PredictInputSchema(text="sample", tasks={"intent": ["refund", "refund"]})


def test_guardrails_label_length_limits():
    """Verify excessively long task names or labels (>100 chars) are rejected."""
    long_label = "a" * 101
    with pytest.raises(ValidationError):
        PredictInputSchema(text="sample", tasks={"intent": [long_label]})

    long_task = "t" * 101
    with pytest.raises(ValidationError):
        PredictInputSchema(text="sample", tasks={long_task: ["support"]})


def test_bootstrap_admin_auto_generation(auth_db_session, monkeypatch):
    """Verify bootstrap creates admin with random password when unset and outputs banner."""
    captured_stdout = StringIO()
    monkeypatch.setattr("sys.stdout", captured_stdout)

    settings = Settings(admin_password=None, admin_username="admin")
    pwd = bootstrap_admin(auth_db_session, settings)

    assert pwd is not None
    assert len(pwd) == 24

    admin = UserRepository.get_by_username(auth_db_session, "admin")
    assert admin is not None
    assert verify_password(pwd, admin.password_hash) is True

    output = captured_stdout.getvalue()
    assert "DECIDE APPLIANCE BOOTSTRAP" in output
    assert pwd in output


def test_bootstrap_admin_provided_password(auth_db_session):
    """Verify bootstrap uses explicit ADMIN_PASSWORD when provided."""
    settings = Settings(admin_password="ExplicitPassword99!", admin_username="admin")
    pwd = bootstrap_admin(auth_db_session, settings)

    assert pwd is None  # not auto-generated
    admin = UserRepository.get_by_username(auth_db_session, "admin")
    assert admin is not None
    assert verify_password("ExplicitPassword99!", admin.password_hash) is True


def test_bootstrap_admin_existing_untouched(auth_db_session):
    """Verify subsequent boots without FORCE_ADMIN_RESET leave password untouched."""
    s1 = Settings(admin_password="InitialPassword1", admin_username="admin")
    bootstrap_admin(auth_db_session, s1)

    s2 = Settings(admin_password="DifferentPassword2", admin_username="admin", force_admin_reset=False)
    bootstrap_admin(auth_db_session, s2)

    admin = UserRepository.get_by_username(auth_db_session, "admin")
    assert verify_password("InitialPassword1", admin.password_hash) is True
    assert verify_password("DifferentPassword2", admin.password_hash) is False


def test_bootstrap_admin_force_reset(auth_db_session):
    """Verify FORCE_ADMIN_RESET updates existing admin password."""
    # First boot
    s1 = Settings(admin_password="InitialPassword1", admin_username="admin")
    bootstrap_admin(auth_db_session, s1)

    # Second boot with FORCE_ADMIN_RESET
    s2 = Settings(admin_password="NewResetPassword2", admin_username="admin", force_admin_reset=True)
    bootstrap_admin(auth_db_session, s2)

    admin = UserRepository.get_by_username(auth_db_session, "admin")
    assert verify_password("NewResetPassword2", admin.password_hash) is True


def test_api_key_cache_operations():
    """Verify APIKeyCache set, get, invalidate, and clear methods."""
    cache = APIKeyCache()
    item = KeyCacheItem(key_id=1, is_active=True, name="Test", hashed_key="h1")

    assert cache.get("h1") is None
    cache.set("h1", item)

    fetched = cache.get("h1")
    assert fetched is not None
    assert fetched.key_id == 1

    cache.invalidate("h1")
    assert cache.get("h1") is None

    cache.set("h2", item)
    cache.clear()
    assert cache.get("h2") is None


def test_api_key_auth_dependency(auth_db_session):
    """Verify verify_api_key dependency behavior for missing, invalid, and valid keys."""
    # 1. Missing header
    with pytest.raises(HTTPException) as exc:
        verify_api_key(x_api_key=None, db=auth_db_session)
    assert exc.value.status_code == 401

    # 2. Invalid format
    with pytest.raises(HTTPException) as exc:
        verify_api_key(x_api_key="invalid_format_key", db=auth_db_session)
    assert exc.value.status_code == 403

    # 3. Valid key in database
    user = UserRepository.create(auth_db_session, "key_user", "hash")
    raw_key = "dec_1234567890abcdef1234567890abcdef"
    hashed = hash_api_key(raw_key)
    key_record = APIKeyRepository.create(
        auth_db_session,
        user_id=user.id,
        name="Valid Key",
        key_prefix="dec_123456",
        hashed_key=hashed,
    )

    key_cache.clear()
    auth_key = verify_api_key(x_api_key=raw_key, db=auth_db_session)
    assert auth_key.id == key_record.id

    # Second call hits cache
    cached_key = verify_api_key(x_api_key=raw_key, db=auth_db_session)
    assert cached_key.id == key_record.id

    # 4. Revoked key
    APIKeyRepository.revoke(auth_db_session, key_record.id)
    key_cache.invalidate(hashed)

    with pytest.raises(HTTPException) as exc:
        verify_api_key(x_api_key=raw_key, db=auth_db_session)
    assert exc.value.status_code == 403


def test_session_cookie_and_csrf_lifecycle(auth_db_session):
    """Verify session cookie issuance, verification, user extraction, and CSRF guard."""
    user = UserRepository.create(auth_db_session, "session_admin", "hash")

    # Issue session cookie on response
    response = Response()
    create_session_cookie(response, user.id)

    # Extract set-cookie value
    cookie_header = response.headers.get("set-cookie")
    assert cookie_header is not None
    assert SESSION_COOKIE_NAME in cookie_header
    assert "HttpOnly" in cookie_header
    assert "SameSite=lax" in cookie_header or "samesite=lax" in cookie_header.lower()

    # Parse cookie value
    raw_cookie_val = cookie_header.split(";")[0].split("=")[1]

    # Mock Request with cookie
    scope = {
        "type": "http",
        "headers": [(b"cookie", f"{SESSION_COOKIE_NAME}={raw_cookie_val}".encode())],
    }
    request = Request(scope)

    # Verify session user ID
    user_id = get_session_user_id(request)
    assert user_id == user.id

    # Verify get_current_admin dependency
    current_admin = get_current_admin(request, db=auth_db_session)
    assert current_admin.id == user.id

    # Test CSRF Token generation and verification
    csrf_token = generate_csrf_token(raw_cookie_val)

    # Request with valid CSRF header
    scope_with_csrf = {
        "type": "http",
        "headers": [
            (b"cookie", f"{SESSION_COOKIE_NAME}={raw_cookie_val}".encode()),
            (b"x-csrf-token", csrf_token.encode()),
        ],
    }
    req_valid_csrf = Request(scope_with_csrf)
    verify_csrf_token(req_valid_csrf)  # should not raise

    # Request with invalid CSRF header
    scope_bad_csrf = {
        "type": "http",
        "headers": [
            (b"cookie", f"{SESSION_COOKIE_NAME}={raw_cookie_val}".encode()),
            (b"x-csrf-token", b"bad_token"),
        ],
    }
    with pytest.raises(HTTPException) as exc:
        verify_csrf_token(Request(scope_bad_csrf))
    assert exc.value.status_code == 403


def test_session_cookie_corrupted_or_expired():
    """Verify corrupted session cookie returns None."""
    scope = {
        "type": "http",
        "headers": [(b"cookie", f"{SESSION_COOKIE_NAME}=corrupted_tampered_payload".encode())],
    }
    request = Request(scope)
    assert get_session_user_id(request) is None
