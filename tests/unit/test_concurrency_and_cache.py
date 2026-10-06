"""Concurrency, cache eviction, middleware latency fidelity, and dynamic DB repository tests."""

import asyncio
import concurrent.futures
from datetime import datetime, timedelta
from pathlib import Path
import time
import uuid
import pytest
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.testclient import TestClient

from decide.api.middleware import setup_middleware_and_exceptions
from decide.auth.api_key import APIKeyCache, KeyCacheItem, verify_api_key, key_cache
from decide.auth.session import (
    create_session_cookie,
    get_session_user_id,
    generate_csrf_token,
    verify_csrf_token,
    SESSION_COOKIE_NAME,
)
from decide.crypto import generate_api_key, hash_api_key
from decide.db.models import APIKey
from decide.db.repository import APIKeyRepository, UserRepository
from decide.db.session import get_engine, init_db, get_session_context


@pytest.fixture
def isolated_db_session(tmp_path: Path):
    """Creates an isolated temporary SQLite database session for testing."""
    db_file = tmp_path / "test_concurrency.db"
    engine = get_engine(db_file)
    init_db(engine)
    with get_session_context(engine) as session:
        yield session


class TestAPIKeyCacheConcurrency:
    """Stress tests verifying APIKeyCache thread-safety and dynamic state management."""

    def test_concurrent_multithreaded_cache_access(self):
        """Verify APIKeyCache withstands concurrent gets, sets, and invalidations across 20 threads."""
        cache = APIKeyCache()
        num_threads = 20
        iterations_per_thread = 200

        keys = [f"hash_{i}" for i in range(50)]
        for k in keys:
            cache.set(k, KeyCacheItem(key_id=1, is_active=True, name=k, hashed_key=k))

        errors = []

        def worker_task(thread_id: int):
            try:
                for j in range(iterations_per_thread):
                    target_key = keys[(thread_id + j) % len(keys)]
                    op = j % 3
                    if op == 0:
                        _ = cache.get(target_key)
                    elif op == 1:
                        cache.set(target_key, KeyCacheItem(key_id=thread_id, is_active=True, name="t", hashed_key=target_key))
                    else:
                        cache.invalidate(target_key)
            except Exception as e:
                errors.append(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_task, t) for t in range(num_threads)]
            concurrent.futures.wait(futures)

        assert len(errors) == 0, f"Thread-safety errors encountered: {errors}"

    def test_dynamic_invalidation_immediate_rejection(self, isolated_db_session):
        """Verify that revoking a key and invalidating cache immediately causes 403 Forbidden."""
        user = UserRepository.create(isolated_db_session, "test_admin", "hash")
        raw_key = generate_api_key()
        hashed = hash_api_key(raw_key)

        key_record = APIKeyRepository.create(
            isolated_db_session,
            user_id=user.id,
            name="Dynamic Invalidation Key",
            key_prefix=raw_key[:10],
            hashed_key=hashed,
        )

        key_cache.clear()

        # Step 1: First request verifies and warms cache
        auth_key = verify_api_key(x_api_key=raw_key, db=isolated_db_session)
        assert auth_key.id == key_record.id

        # Cached item exists
        cached_item = key_cache.get(hashed)
        assert cached_item is not None
        assert cached_item.is_active is True

        # Step 2: Revoke in DB and invalidate cache
        APIKeyRepository.revoke(isolated_db_session, key_record.id)
        key_cache.invalidate(hashed)

        assert key_cache.get(hashed) is None

        # Step 3: Immediate subsequent call must reject with 403
        with pytest.raises(HTTPException) as exc:
            verify_api_key(x_api_key=raw_key, db=isolated_db_session)
        assert exc.value.status_code == 403
        assert "invalid, expired, or revoked" in exc.value.detail


class TestMiddlewareLatencyFidelity:
    """Verify SecurityAndLatencyMiddleware tracks actual dynamic elapsed time."""

    def test_dynamic_elapsed_latency_tracking(self):
        """Verify X-Response-Time measures real execution time and varies with endpoint delay."""
        app = FastAPI()
        setup_middleware_and_exceptions(app)

        @app.get("/fast")
        def fast_endpoint():
            return {"status": "ok"}

        @app.get("/delayed-30ms")
        def delayed_30():
            time.sleep(0.030)
            return {"status": "ok"}

        @app.get("/delayed-70ms")
        def delayed_70():
            time.sleep(0.070)
            return {"status": "ok"}

        client = TestClient(app)

        # Fast request
        resp_fast = client.get("/fast")
        assert resp_fast.status_code == 200
        assert "X-Response-Time" in resp_fast.headers
        val_fast = float(resp_fast.headers["X-Response-Time"].replace("ms", ""))

        # 30ms delayed request
        resp_30 = client.get("/delayed-30ms")
        assert resp_30.status_code == 200
        val_30 = float(resp_30.headers["X-Response-Time"].replace("ms", ""))
        assert val_30 >= 29.0, f"Expected >= 29.0ms, got {val_30}ms"

        # 70ms delayed request
        resp_70 = client.get("/delayed-70ms")
        assert resp_70.status_code == 200
        val_70 = float(resp_70.headers["X-Response-Time"].replace("ms", ""))
        assert val_70 >= 69.0, f"Expected >= 69.0ms, got {val_70}ms"

        # Monotonicity check: longer delay yields strictly longer X-Response-Time
        assert val_70 > val_30 > val_fast


class TestSessionAndCSRFSecurityAdversarial:
    """Verify session cookie verification and CSRF token defenses against tampering."""

    def test_session_cookie_bit_tampering(self, isolated_db_session):
        """Verify modifying any character of the signed session cookie invalidates it."""
        user = UserRepository.create(isolated_db_session, "session_user", "hash")

        response = Response()
        create_session_cookie(response, user.id)
        cookie_header = response.headers.get("set-cookie")
        raw_cookie = cookie_header.split(";")[0].split("=")[1]

        # Tamper 1 character at various positions
        tampered_cookies = [
            raw_cookie[:-1] + ("x" if raw_cookie[-1] != "x" else "y"),
            "x" + raw_cookie[1:],
            raw_cookie[:10] + "z" + raw_cookie[11:],
            raw_cookie.split(".")[0] if "." in raw_cookie else raw_cookie + "extra",
        ]

        for tampered in tampered_cookies:
            req = Request({
                "type": "http",
                "headers": [(b"cookie", f"{SESSION_COOKIE_NAME}={tampered}".encode())],
            })
            assert get_session_user_id(req) is None, f"Tampered cookie was accepted: {tampered}"

    def test_csrf_token_adversarial_isolation(self):
        """Verify CSRF token is cryptographically bound to its session and cannot be spoofed or transferred."""
        cookie_a = "session_cookie_user_a_secret_123"
        cookie_b = "session_cookie_user_b_secret_456"

        csrf_a = generate_csrf_token(cookie_a)
        csrf_b = generate_csrf_token(cookie_b)

        assert csrf_a != csrf_b

        # Valid token with matching cookie
        req_valid = Request({
            "type": "http",
            "headers": [
                (b"cookie", f"{SESSION_COOKIE_NAME}={cookie_a}".encode()),
                (b"x-csrf-token", csrf_a.encode()),
            ],
        })
        verify_csrf_token(req_valid)  # Must not raise

        # User B's token used with User A's session cookie (Cross-Session attack)
        req_stolen = Request({
            "type": "http",
            "headers": [
                (b"cookie", f"{SESSION_COOKIE_NAME}={cookie_a}".encode()),
                (b"x-csrf-token", csrf_b.encode()),
            ],
        })
        with pytest.raises(HTTPException) as exc:
            verify_csrf_token(req_stolen)
        assert exc.value.status_code == 403

        # Tampered CSRF token (1 character flip)
        tampered_csrf = csrf_a[:-1] + ("0" if csrf_a[-1] != "0" else "1")
        req_tampered = Request({
            "type": "http",
            "headers": [
                (b"cookie", f"{SESSION_COOKIE_NAME}={cookie_a}".encode()),
                (b"x-csrf-token", tampered_csrf.encode()),
            ],
        })
        with pytest.raises(HTTPException) as exc:
            verify_csrf_token(req_tampered)
        assert exc.value.status_code == 403


class TestDBRepositoryDynamicFiltering:
    """Verify database repositories dynamically filter and do not return hardcoded collections."""

    def test_api_key_repository_user_filtering(self, isolated_db_session):
        """Verify APIKeyRepository.list_all strictly filters by user_id and respects isolation."""
        user1 = UserRepository.create(isolated_db_session, "user1", "hash1")
        user2 = UserRepository.create(isolated_db_session, "user2", "hash2")

        # Create 3 keys for user1
        k1_1 = APIKeyRepository.create(isolated_db_session, user1.id, "u1_k1", "dec_111111", "hash1_1")
        k1_2 = APIKeyRepository.create(isolated_db_session, user1.id, "u1_k2", "dec_111112", "hash1_2")
        k1_3 = APIKeyRepository.create(isolated_db_session, user1.id, "u1_k3", "dec_111113", "hash1_3")

        # Create 2 keys for user2
        k2_1 = APIKeyRepository.create(isolated_db_session, user2.id, "u2_k1", "dec_222221", "hash2_1")
        k2_2 = APIKeyRepository.create(isolated_db_session, user2.id, "u2_k2", "dec_222222", "hash2_2")

        # Query user1 keys
        user1_keys = APIKeyRepository.list_all(isolated_db_session, user_id=user1.id)
        assert len(user1_keys) == 3
        assert {k.id for k in user1_keys} == {k1_1.id, k1_2.id, k1_3.id}

        # Query user2 keys
        user2_keys = APIKeyRepository.list_all(isolated_db_session, user_id=user2.id)
        assert len(user2_keys) == 2
        assert {k.id for k in user2_keys} == {k2_1.id, k2_2.id}

        # Query non-existent user keys
        empty_keys = APIKeyRepository.list_all(isolated_db_session, user_id=99999)
        assert len(empty_keys) == 0

        # Query all keys
        all_keys = APIKeyRepository.list_all(isolated_db_session)
        assert len(all_keys) == 5

    def test_api_key_update_last_used_isolation(self, isolated_db_session):
        """Verify update_last_used updates only the specific key and persists exact timestamp."""
        user = UserRepository.create(isolated_db_session, "user_audit", "hash")
        k1 = APIKeyRepository.create(isolated_db_session, user.id, "k1", "dec_k11111", "hash_k1")
        k2 = APIKeyRepository.create(isolated_db_session, user.id, "k2", "dec_k22222", "hash_k2")

        assert k1.last_used_at is None
        assert k2.last_used_at is None

        # Update k1 only with a specific timestamp
        target_time = datetime(2026, 5, 20, 14, 30, 0)
        APIKeyRepository.update_last_used(isolated_db_session, k1.id, when=target_time)

        # Refresh objects
        isolated_db_session.expire_all()
        refreshed_k1 = APIKeyRepository.get_by_id(isolated_db_session, k1.id)
        refreshed_k2 = APIKeyRepository.get_by_id(isolated_db_session, k2.id)

        assert refreshed_k1.last_used_at == target_time
        # k2 must remain untouched
        assert refreshed_k2.last_used_at is None
