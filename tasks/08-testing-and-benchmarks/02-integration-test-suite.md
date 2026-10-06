# SUBTASK-8.2: Integration Test Suite

## Parent Task
[TASK-08: Testing, Quality Assurance & Benchmarks](file:///home/abhishek/decide/tasks/08-testing-and-benchmarks/index.md)

## Target Code Path
`tests/integration/`

## Objective
Implement end-to-end integration tests using FastAPI's `TestClient` (or `httpx.AsyncClient`) to validate API endpoints, error handling, session cookies, and admin GUI workflows.

## Functional Requirements
1. **Health Probe Tests (`test_health_route.py`):**
   - Assert `GET /health` returns 200 OK with `status`, `model_loaded`, and `device` fields.
   - Assert `GET /health` works without any `X-API-Key` or session cookies.
2. **Inference Predict Tests (`test_predict_route.py`):**
   - Issue request without `X-API-Key` -> Assert 401 Unauthorized.
   - Issue request with invalid key -> Assert 403 Forbidden.
   - Issue request with revoked key (`is_active = False`) -> Assert 403 Forbidden.
   - Issue request with text > 8000 characters -> Assert 422 Unprocessable Entity.
   - Issue request with > 20 tasks -> Assert 422 Unprocessable Entity.
   - Issue request with valid key and valid payload -> Assert 200 OK and check `result` structure.
   - Assert `last_used_at` timestamp was updated for the key.
3. **Admin Web GUI Workflow Tests (`test_admin_gui.py`):**
   - Access `/admin` without session -> Assert redirect to `/admin/login`.
   - Submit invalid login form -> Assert error message rendered on login page.
   - Submit valid login credentials -> Assert redirect to `/admin` and session cookie set.
   - Submit HTMX key generation form -> Assert modal returned with new key and raw secret displayed.
   - Submit HTMX key revocation request -> Assert updated row returned with revoked badge.
   - Submit playground test form -> Assert inference executed and result rendered.

## Interface & Schema
```python
import pytest
from fastapi.testclient import TestClient
from decide.main import app

client = TestClient(app)

def test_predict_auth_contract():
    # Missing key
    resp = client.post("/predict", json={"text": "hello", "tasks": {"a": ["b"]}})
    assert resp.status_code == 401

    # Invalid key
    resp = client.post(
        "/predict",
        headers={"X-API-Key": "dec_invalidkey123456789012345678"},
        json={"text": "hello", "tasks": {"a": ["b"]}}
    )
    assert resp.status_code == 403
```

## Acceptance Criteria
- [x] Validates all HTTP status codes (200, 401, 403, 422, 500) defined in PRD Section 7.
- [x] Confirms admin session cookie and CSRF protections behave as specified.
- [x] All routes execute with mocked or live model without regression.

