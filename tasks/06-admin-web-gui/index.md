# TASK-06: Admin Web GUI Portal

## Overview
This task encompasses building the built-in administrative Web GUI using server-rendered Jinja2 templates, HTMX for dynamic interactions, and locally bundled Tailwind CSS. It enables visual key lifecycle management, revocation, and an interactive model testing playground with zero runtime Node.js dependency.

## Module Architecture & Subtasks

| Subtask ID | Title | Target File | Description |
| :--- | :--- | :--- | :--- |
| **SUBTASK-6.1** | [Template Engine & Local Assets](file:///home/abhishek/decide/tasks/06-admin-web-gui/01-template-engine-and-local-assets.md) | `decide/web/templates/*`<br/>`decide/web/static/*` | Jinja2 templates, base layout, navigation, local bundled Tailwind CSS, and local HTMX bundle. |
| **SUBTASK-6.2** | [Admin Auth & Login Routes](file:///home/abhishek/decide/tasks/06-admin-web-gui/02-admin-auth-and-login-routes.md) | `decide/web/routes/auth.py` | Form login (`GET/POST /admin/login`), session cookie issuance, CSRF tokens, and logout. |
| **SUBTASK-6.3** | [Dashboard & Key Management HTMX](file:///home/abhishek/decide/tasks/06-admin-web-gui/03-dashboard-and-key-management-htmx.md) | `decide/web/routes/dashboard.py` | Key table display, dynamic issuance modal with copy-to-clipboard, instant HTMX key revocation. |
| **SUBTASK-6.4** | [Interactive Model Playground](file:///home/abhishek/decide/tasks/06-admin-web-gui/04-interactive-playground.md) | `decide/web/routes/playground.py` | Live `/admin/playground` interface with text input, JSON task/label editor, internal test predict execution, latency badge. |

## Key Dependencies
- `jinja2`
- HTMX (bundled locally in static folder)
- Tailwind CSS (bundled minified CSS in static folder)
- Zero external CDN dependencies, fully functional offline

## Acceptance Criteria
- [x] Complete admin portal functions with zero internet access.
- [x] Key creation returns the unhashed secret only once inside a modal with clipboard copy button.
- [x] Revocation executes via HTMX and updates the status badge without full page refresh.
- [x] Playground executes predictions and displays model inference latency.

