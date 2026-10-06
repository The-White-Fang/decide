# SUBTASK-6.4: Interactive Playground

## Parent Task
[TASK-06: Admin Web GUI Portal](file:///home/abhishek/decide/tasks/06-admin-web-gui/index.md)

## Target Code Path
`decide/web/routes/playground.py`

## Objective
Implement interactive model testing playground at `/admin/playground` allowing administrators to test live intent routing and classification queries directly in the browser with real-time JSON response and latency tracking.

## Functional Requirements
1. **Playground Interface (`GET /admin/playground`):**
   - Protected by `get_current_admin`.
   - Text input area for sample text (pre-filled with example from PRD: `"My order arrived broken and I want a replacement immediately."`).
   - JSON / Key-Value editor for task categories and candidate labels (pre-filled with sample tasks: `intent`, `urgency`).
   - "Test Predict" submit button powered by HTMX (`hx-post="/admin/playground/test"`, `hx-target="#playground-result"`).
   - Dynamic loading spinner while inference is executing.
2. **Execution Endpoint (`POST /admin/playground/test`):**
   - Validates JSON format of tasks and text input length.
   - Invokes `MultiTaskClassifier.predict()` via internal in-memory engine bindings.
   - Measures end-to-end inference latency.
   - Returns HTML partial `partials/playground_result.html` containing:
     - Formatted syntax-highlighted JSON result (`{"result": {"intent": "replacement", "urgency": "critical"}}`).
     - Badge displaying execution latency (e.g. `18.4 ms` on GPU / `85.2 ms` on CPU).
     - Error banner if JSON schema is malformed.

## Interface & Schema
```python
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse
from decide.auth.session import get_current_admin
from decide.db.models import User

router = APIRouter(prefix="/admin/playground")

@router.get("", response_class=HTMLResponse)
def playground_page(
    request: Request,
    current_admin: User = Depends(get_current_admin)
): ...

@router.post("/test", response_class=HTMLResponse)
def playground_test(
    request: Request,
    text: str = Form(...),
    tasks_json: str = Form(...),
    current_admin: User = Depends(get_current_admin)
): ...
```

## Acceptance Criteria
- [x] Playground loads pre-populated with PRD example text and tasks.
- [x] Submitting executes prediction without full page reload.
- [x] Output displays structured JSON result alongside model latency in milliseconds.
- [x] Handles invalid JSON inputs with friendly error messages instead of 500 error pages.

