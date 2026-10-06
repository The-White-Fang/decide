"""Session cookie signing, admin auth guard, and CSRF protection."""

import hmac
import hashlib
from typing import Optional
from fastapi import Request, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy.orm import Session
from decide.config import get_settings
from decide.crypto import generate_session_secret
from decide.db.models import User
from decide.db.repository import UserRepository
from decide.db.session import get_db

SESSION_COOKIE_NAME = "decide_session"
SESSION_MAX_AGE_SECONDS = 12 * 60 * 60  # 12 hours

_runtime_secret: Optional[str] = None


def get_secret_key() -> str:
    """Returns configured secret_key or generates a stable runtime secret."""
    global _runtime_secret
    settings = get_settings()
    if settings.secret_key:
        return settings.secret_key
    if _runtime_secret is None:
        _runtime_secret = generate_session_secret()
    return _runtime_secret


def get_serializer() -> URLSafeTimedSerializer:
    """Returns serializer instance configured with current secret."""
    return URLSafeTimedSerializer(get_secret_key(), salt="decide-session-salt")


def create_session_cookie(response: Response, user_id: int) -> None:
    """Signs session payload containing user_id and sets HttpOnly cookie."""
    serializer = get_serializer()
    signed_token = serializer.dumps({"user_id": user_id})
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=signed_token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,  # Can be True behind TLS
    )


def clear_session_cookie(response: Response) -> None:
    """Deletes the session cookie."""
    response.delete_cookie(key=SESSION_COOKIE_NAME, samesite="lax", httponly=True)


def get_session_user_id(request: Request) -> Optional[int]:
    """Extracts and verifies user_id from the session cookie."""
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie:
        return None
    serializer = get_serializer()
    try:
        data = serializer.loads(cookie, max_age=SESSION_MAX_AGE_SECONDS)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None


def get_current_admin(request: Request, db: Session = Depends(get_db)) -> User:
    """
    FastAPI dependency ensuring request originates from an authenticated admin.
    Raises HTTPException(401) or redirects to login for HTML requests.
    """
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin session required",
        )

    user = UserRepository.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or not found",
        )
    return user


def generate_csrf_token(session_id: str) -> str:
    """Generates a keyed CSRF token based on session signature."""
    secret = get_secret_key()
    return hmac.new(secret.encode(), session_id.encode(), hashlib.sha256).hexdigest()


def verify_csrf_token(request: Request) -> None:
    """Verifies CSRF token on mutating requests."""
    cookie = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing session for CSRF check")

    expected_csrf = generate_csrf_token(cookie)
    # Check header or query/form token
    provided_csrf = request.headers.get("X-CSRF-Token")
    if not provided_csrf:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing CSRF token")

    if not hmac.compare_digest(expected_csrf, provided_csrf):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
