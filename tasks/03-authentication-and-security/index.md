# TASK-03: Authentication & Security Guard

## Overview
This task implements authentication, authorization, session management, and denial-of-service protections for `decide`. It includes zero-touch administrator bootstrap, high-speed cached API key validation, session cookies, and request guardrails.

## Module Architecture & Subtasks

| Subtask ID | Title | Target File | Description |
| :--- | :--- | :--- | :--- |
| **SUBTASK-3.1** | [Admin Seeding & Bootstrap](file:///home/abhishek/decide/tasks/03-authentication-and-security/01-admin-seeding-and-bootstrap.md) | `decide/auth/bootstrap.py` | Automated administrator account creation on container boot, password generation, and password reset handling. |
| **SUBTASK-3.2** | [API Key Auth & In-Memory Cache](file:///home/abhishek/decide/tasks/03-authentication-and-security/02-api-key-auth-and-caching.md) | `decide/auth/api_key.py` | `X-API-Key` validation interceptor, SHA-256 matching, LRU/in-memory cache for < 1ms auth, background telemetry. |
| **SUBTASK-3.3** | [Session Management & CSRF Guard](file:///home/abhishek/decide/tasks/03-authentication-and-security/03-session-management-and-csrf.md) | `decide/auth/session.py` | Admin session cookie signing (`HttpOnly`, `SameSite=Lax`), login state verification, and CSRF token validation. |
| **SUBTASK-3.4** | [DoS Guardrails & Input Limits](file:///home/abhishek/decide/tasks/03-authentication-and-security/04-dos-and-input-guardrails.md) | `decide/auth/guardrails.py` | Boundary enforcement: text length (8,000 chars), max tasks (20), max labels (50), timing-attack protections. |

## Key Dependencies
- `bcrypt`
- `itsdangerous` / `PyJWT` / session crypto
- Python standard library (`hashlib`, `hmac`, `secrets`)

## Status
**Completed** (All 15 auth unit tests and integration tests passing)

## Acceptance Criteria
- [x] Admin user is seeded automatically if `users` table is empty.
- [x] Generated password is printed to stdout in a highlighted banner if `ADMIN_PASSWORD` was unset.
- [x] In-memory key caching achieves < 1ms auth overhead.
- [x] Mutating admin routes require valid CSRF token.
- [x] Inputs exceeding 8,000 characters or 20 tasks return HTTP 422.
