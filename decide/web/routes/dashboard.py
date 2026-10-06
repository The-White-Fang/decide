"""Admin dashboard and HTMX key lifecycle management."""

from pathlib import Path
from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from decide.auth.api_key import key_cache
from decide.auth.session import get_current_admin
from decide.crypto import generate_api_key, extract_key_prefix, hash_api_key
from decide.db.models import User
from decide.db.repository import APIKeyRepository
from decide.db.session import get_db

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/admin")


@router.get("", response_class=HTMLResponse)
def dashboard(
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Renders the admin dashboard with keys table and stats."""
    keys = APIKeyRepository.list_all(db)
    active_count = sum(1 for k in keys if k.is_active)
    revoked_count = len(keys) - active_count

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "admin": current_admin,
            "keys": keys,
            "active_count": active_count,
            "revoked_count": revoked_count,
        },
    )


@router.post("/keys", response_class=HTMLResponse)
def create_key(
    request: Request,
    name: str = Form(...),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Issues a new API key.
    Generates dec_<32_random_chars>, computes prefix and SHA-256 hash.
    Returns partial modal with raw key for one-time display.
    """
    raw_key = generate_api_key()
    prefix = extract_key_prefix(raw_key)
    hashed = hash_api_key(raw_key)

    api_key = APIKeyRepository.create(
        db,
        user_id=current_admin.id,
        name=name.strip(),
        key_prefix=prefix,
        hashed_key=hashed,
    )

    return templates.TemplateResponse(
        request=request,
        name="partials/key_modal.html",
        context={
            "raw_key": raw_key,
            "api_key": api_key,
        },
    )


@router.post("/keys/{key_id}/revoke", response_class=HTMLResponse)
def revoke_key(
    request: Request,
    key_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Revokes an active API key and invalidates cache."""
    api_key = APIKeyRepository.revoke(db, key_id)
    if not api_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")

    key_cache.invalidate(api_key.hashed_key)

    return templates.TemplateResponse(
        request=request,
        name="partials/key_row.html",
        context={
            "key": api_key,
        },
    )
