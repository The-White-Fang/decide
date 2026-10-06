# SUBTASK-6.3: Dashboard & Key Management HTMX

## Parent Task
[TASK-06: Admin Web GUI Portal](file:///home/abhishek/decide/tasks/06-admin-web-gui/index.md)

## Target Code Path
`decide/web/routes/dashboard.py`

## Objective
Implement administrative dashboard (`GET /admin`) and HTMX endpoints for listing API keys, issuing new labeled keys with one-time display modals, and immediate asynchronous key revocation.

## Functional Requirements
1. **Admin Dashboard (`GET /admin`):**
   - Protected by `get_current_admin` dependency.
   - Query all registered API keys via `APIKeyRepository.list_all(db)`.
   - Render `dashboard.html` with:
     - Header summary stats (Total keys, Active keys, Revoked keys).
     - Table columns: Key Name/Label, Prefix (e.g. `dec_k9fJ2m...`), Created Date, Last Used Timestamp, Status Badge (Active = Green, Revoked = Red), Actions.
     - "Create New API Key" trigger button opening modal.
2. **Issue New API Key (`POST /admin/keys`):**
   - HTMX form submission containing key name/label (e.g., "Customer Support Router").
   - Generate raw key via `generate_api_key()` (`dec_<32_random_alphanumeric_characters>`).
   - Extract first 10 characters as `key_prefix`.
   - Compute SHA-256 hex digest `hashed_key`.
   - Insert record into SQLite via `APIKeyRepository.create()`.
   - Render `partials/key_modal.html` containing:
     - Prominent warning: *"This secret will NEVER be displayed again. Copy it now."*
     - Readonly input field with raw key.
     - Clipboard copy utility button (`navigator.clipboard.writeText(...)`).
     - HTMX out-of-band swap (`hx-swap-oob="beforeend:#keys-table-body"`) appending the new key row to the dashboard table.
3. **Instant Key Revocation (`POST /admin/keys/{key_id}/revoke`):**
   - Triggered asynchronously by "Revoke" button via `hx-post="/admin/keys/{{ key.id }}/revoke"`.
   - Calls `APIKeyRepository.revoke(db, key_id)`.
   - Invalidates in-memory auth cache via `APIKeyCache.invalidate()`.
   - Returns updated `partials/key_row.html` with status badge changed to "Revoked" and action disabled.

## Interface & Schema
```python
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from decide.auth.session import get_current_admin
from decide.db.session import get_db
from decide.db.models import User

router = APIRouter(prefix="/admin")

@router.get("", response_class=HTMLResponse)
def dashboard(
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
): ...

@router.post("/keys", response_class=HTMLResponse)
def create_key(
    request: Request,
    name: str = Form(...),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
): ...

@router.post("/keys/{key_id}/revoke", response_class=HTMLResponse)
def revoke_key(
    request: Request,
    key_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
): ...
```

## Acceptance Criteria
- [x] Displays all keys sorted by creation date descending.
- [x] Raw key secret is displayed exactly once in modal; is never retrievable or stored in database.
- [x] Clipboard copy button provides instant feedback to user.
- [x] Revocation updates table row in-place via HTMX without full page refresh.
- [x] Revoked key cannot be used for inference immediately.

