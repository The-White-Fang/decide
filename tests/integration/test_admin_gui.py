"""Integration tests for Admin Web GUI portal (Module 06: Admin Web GUI)."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from decide.auth.api_key import key_cache
from decide.crypto import hash_password
from decide.db.repository import UserRepository, APIKeyRepository
from decide.db.session import get_engine, init_db, get_session_context, get_db
from decide.engine.classifier import MultiTaskClassifier
from decide.engine.lifecycle import get_engine_state
from decide.main import app


class MockExtractor:
    def extract(self, text, tasks):
        return {"intent": "refund"}


@pytest.fixture
def gui_client(tmp_path: Path):
    db_file = tmp_path / "gui_test.db"
    engine = get_engine(db_file)
    init_db(engine)

    # Seed admin user
    with get_session_context(engine) as s:
        UserRepository.create(s, "admin", hash_password("AdminPassword123!"))

    # Set up engine
    classifier = MultiTaskClassifier(extractor=MockExtractor(), device="cpu")
    get_engine_state().set_ready(classifier, "cpu")

    def override_get_db():
        with get_session_context(engine) as s:
            yield s

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield {"client": client, "engine": engine}

    app.dependency_overrides.clear()
    key_cache.clear()


def test_dashboard_unauthorized_access(gui_client):
    client = gui_client["client"]
    resp = client.get("/admin", follow_redirects=False)
    # Should require session and reject with 401
    assert resp.status_code == 401


def test_login_flow(gui_client):
    client = gui_client["client"]

    # 1. View login page
    resp = client.get("/admin/login")
    assert resp.status_code == 200
    assert "Sign In to decide" in resp.text

    # 2. Failed login
    bad_resp = client.post("/admin/login", data={"username": "admin", "password": "WrongPassword"})
    assert bad_resp.status_code == 400
    assert "Invalid username or password" in bad_resp.text

    # 3. Successful login
    login_resp = client.post(
        "/admin/login",
        data={"username": "admin", "password": "AdminPassword123!"},
        follow_redirects=False,
    )
    assert login_resp.status_code == 303
    assert "decide_session" in login_resp.cookies


def test_dashboard_and_key_management_flow(gui_client):
    client = gui_client["client"]

    # Login
    client.post("/admin/login", data={"username": "admin", "password": "AdminPassword123!"})

    # Access dashboard
    dash_resp = client.get("/admin")
    assert dash_resp.status_code == 200
    assert "API Key Management" in dash_resp.text

    # Create new key via HTMX
    create_resp = client.post("/admin/keys", data={"name": "Production Router Key"})
    assert create_resp.status_code == 200
    assert "API Key Successfully Issued" in create_resp.text
    assert "dec_" in create_resp.text
    assert "This secret key will <strong>NEVER</strong> be displayed again" in create_resp.text

    # Check dashboard now shows the key
    dash_updated = client.get("/admin")
    assert "Production Router Key" in dash_updated.text
    assert "Active" in dash_updated.text

    # Revoke key
    engine = gui_client["engine"]
    with get_session_context(engine) as s:
        key_record = APIKeyRepository.list_all(s)[0]
        key_id = key_record.id

    revoke_resp = client.post(f"/admin/keys/{key_id}/revoke")
    assert revoke_resp.status_code == 200
    assert "Revoked" in revoke_resp.text


def test_playground_flow(gui_client):
    client = gui_client["client"]

    # Login
    client.post("/admin/login", data={"username": "admin", "password": "AdminPassword123!"})

    # Access playground
    pg_resp = client.get("/admin/playground")
    assert pg_resp.status_code == 200
    assert "Interactive Playground" in pg_resp.text

    # Submit prediction test
    test_resp = client.post(
        "/admin/playground/test",
        data={
            "text": "I need a refund for my order.",
            "tasks_json": '{"intent": ["refund", "replacement"]}',
        },
    )
    assert test_resp.status_code == 200
    assert "refund" in test_resp.text
    assert "ms" in test_resp.text


def test_logout_flow(gui_client):
    client = gui_client["client"]

    # Login
    client.post("/admin/login", data={"username": "admin", "password": "AdminPassword123!"})

    # Logout
    logout_resp = client.post("/admin/logout", follow_redirects=False)
    assert logout_resp.status_code == 303
    assert logout_resp.headers["location"] == "/admin/login"

    # Dashboard should now be unauthorized
    assert client.get("/admin").status_code == 401
