"""Authentication routes for admin login and logout."""

from pathlib import Path
from fastapi import APIRouter, Request, Form, Depends, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from decide.auth.session import create_session_cookie, clear_session_cookie, get_session_user_id
from decide.crypto import verify_password
from decide.db.repository import UserRepository
from decide.db.session import get_db

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/admin")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Renders the admin login form."""
    if get_session_user_id(request) is not None:
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Validates admin credentials and issues signed session cookie."""
    user = UserRepository.get_by_username(db, username.strip())
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Invalid username or password."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    redirect = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    create_session_cookie(redirect, user.id)
    return redirect


@router.post("/logout")
def logout():
    """Clears session cookie and redirects back to login."""
    redirect = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    clear_session_cookie(redirect)
    return redirect
