# SUBTASK-6.2: Admin Auth & Login Routes

## Parent Task
[TASK-06: Admin Web GUI Portal](file:///home/abhishek/decide/tasks/06-admin-web-gui/index.md)

## Target Code Path
`decide/web/routes/auth.py`

## Objective
Implement authentication web routes for administrator login, form submission, credential verification, session cookie attachment, and logout handling.

## Functional Requirements
1. **Login Page (`GET /admin/login`):**
   - If user already has a valid session cookie, redirect to `/admin`.
   - Render `login.html` containing username input, password input, CSRF token, and submit button.
2. **Login Submission (`POST /admin/login`):**
   - Extract `username` and `password` from form data.
   - Verify credentials via `UserRepository.get_by_username()` and `verify_password()`.
   - On invalid credentials: Re-render `login.html` with error message (`"Invalid username or password"`) and HTTP 400.
   - On success: Create signed session cookie (`HttpOnly=True`, `SameSite="lax"`), set on response, and redirect (HTTP 303 See Other) to `/admin`.
3. **Logout Route (`POST /admin/logout`):**
   - Clear session cookie from response.
   - Redirect to `/admin/login`.

## Interface & Schema
```python
from fastapi import APIRouter, Request, Form, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from decide.db.session import get_db

router = APIRouter(prefix="/admin")

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request): ...

@router.post("/login")
def login_submit(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
): ...

@router.post("/logout")
def logout(response: Response): ...
```

## Acceptance Criteria
- [x] Correct admin credentials authenticate and establish a session cookie.
- [x] Incorrect credentials show clear error notification without crashing.
- [x] Unauthenticated access to `/admin` redirects to `/admin/login`.
- [x] Logout deletes the session cookie and returns user to login page.

