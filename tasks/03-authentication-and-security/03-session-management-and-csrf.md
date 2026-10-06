# SUBTASK-3.3: Session Management & CSRF Guard

## Parent Task
[TASK-03: Authentication & Security Guard](file:///home/abhishek/decide/tasks/03-authentication-and-security/index.md)

## Target Code Path
`decide/auth/session.py`

## Objective
Implement session cookie signing, authentication guard dependencies for `/admin/*` routes, and CSRF token protection for mutating web dashboard endpoints.

## Functional Requirements
1. **Session Cookie Security (PRD Section 6.3 & 10):**
   - Cookie Name: `decide_session`
   - Signed using `settings.secret_key` via `itsdangerous.URLSafeTimedSerializer`.
   - Security attributes: `HttpOnly=True`, `SameSite="lax"`, `Secure=True` (or False if running plain HTTP in development/local test).
   - Session duration: 12 hours (configurable).
2. **Admin Auth Guard Dependency:**
   - Dependency `get_current_admin(request: Request, db: Session = Depends(get_db)) -> User`.
   - Reads `decide_session` cookie; verifies signature and expiration.
   - If missing or invalid: For HTML requests, redirect to `/admin/login`; for HTMX/API requests, return HTTP 401.
3. **CSRF Protection (PRD Section 10):**
   - Generate per-session CSRF token stored in session payload or cookie.
   - For mutating admin requests (`POST`, `PUT`, `DELETE`):
     - Inspect request headers (e.g. `X-CSRF-Token` or form field `csrf_token`).
     - Reject request with HTTP 403 if CSRF token is invalid or missing.
   - Inject CSRF token into template contexts.

## Interface & Schema
```python
from fastapi import Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from decide.db.models import User

def create_session_cookie(response, user_id: int, secret_key: str) -> None: ...
def clear_session_cookie(response) -> None: ...
def get_current_admin(request: Request, db: Session = Depends(get_db)) -> User: ...
def verify_csrf_token(request: Request) -> None: ...
def generate_csrf_token(user_id: int, secret_key: str) -> str: ...
```

## Acceptance Criteria
- [ ] Admin dashboard and playground require a valid session cookie; unauthorized requests redirect to `/admin/login`.
- [ ] Session cookie is marked `HttpOnly` and `SameSite=Lax`.
- [ ] Mutating routes without valid CSRF token return 403 Forbidden.
- [ ] Logging out clears the session cookie cleanly.
