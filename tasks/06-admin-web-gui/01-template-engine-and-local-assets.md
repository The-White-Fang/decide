# SUBTASK-6.1: Template Engine & Local Assets

## Parent Task
[TASK-06: Admin Web GUI Portal](file:///home/abhishek/decide/tasks/06-admin-web-gui/index.md)

## Target Code Path
`decide/web/templates/` and `decide/web/static/`

## Objective
Establish the server-side Jinja2 template rendering environment and bundle local static assets (Tailwind CSS stylesheet, HTMX script) so the application requires zero external CDN requests and zero runtime Node.js dependencies.

## Functional Requirements
1. **Local Static Assets (PRD Section 4 & 9.2):**
   - Place minified `htmx.min.js` in `decide/web/static/js/htmx.min.js`.
   - Place pre-compiled Tailwind CSS in `decide/web/static/css/tailwind.min.css`.
   - Mount static directory to `/static` in FastAPI (`app.mount("/static", StaticFiles(...))`).
   - Zero runtime reliance on CDNs (unpkg, cdnjs, Google Fonts).
2. **Base Template Layout (`base.html`):**
   - Semantic HTML5 structure with responsive viewport and title tags.
   - Clean, professional dark/light modern UI design.
   - Top navigation bar: Brand logo ("decide"), links to "Dashboard" (`/admin`) and "Playground" (`/admin/playground`), current username, and "Logout" button.
   - Toast / notification banner container for HTMX events.
   - Modal container for key generation dialog.
3. **Template Partials:**
   - `partials/key_row.html`: Table row for an API key with live HTMX revoke trigger.
   - `partials/key_modal.html`: Modal overlay showing the newly generated raw key with copy-to-clipboard button.
   - `partials/playground_result.html`: Inference JSON result and latency display pill.

## Interface & Schema
```python
from fastapi.templating import Jinja2Templates
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
```

## Acceptance Criteria
- [x] No outbound network calls are made when browsing the admin interface.
- [x] Tailwind styling and HTMX interactions work completely offline.
- [x] Responsive navigation and modal components render cleanly on desktop and mobile viewports.

