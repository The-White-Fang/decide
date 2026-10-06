# TASK-05: REST API Controller

## Overview
This task implements the public and secured REST API endpoints for `decide` using FastAPI. It covers health and readiness probes, the high-throughput `POST /predict` inference route, serialization schemas, error handling, and middleware telemetry.

## Module Architecture & Subtasks

| Subtask ID | Title | Target File | Description |
| :--- | :--- | :--- | :--- |
| **SUBTASK-5.1** | [Health & Readiness Probe](file:///home/abhishek/decide/tasks/05-rest-api-controller/01-health-probe-endpoint.md) | `decide/api/routes/health.py` | Public `GET /health` endpoint returning system health, model readiness, and device status. |
| **SUBTASK-5.2** | [Predict Inference Route](file:///home/abhishek/decide/tasks/05-rest-api-controller/02-predict-endpoint.md) | `decide/api/routes/predict.py` | Secured `POST /predict` endpoint with header auth, request validation, background usage tracking, and response formatting. |
| **SUBTASK-5.3** | [Middleware & Error Handling](file:///home/abhishek/decide/tasks/05-rest-api-controller/03-middleware-and-error-handling.md) | `decide/api/middleware.py` | Exception handlers (401, 403, 422, 500), request latency logger, and CORS/header sanitization. |

## Key Dependencies
- `fastapi`
- `pydantic`
- `uvicorn`

## API Contract Specifications (PRD Section 7)
- `GET /health` -> 200 OK or 503 Service Unavailable
- `POST /predict` -> 200 OK, 401 Unauthorized, 403 Forbidden, 422 Unprocessable Entity, 500 Internal Server Error

## Acceptance Criteria
- [x] Public `GET /health` reports 200 OK when engine is loaded and DB is responsive, or 503 during startup/degraded state.
- [x] Secured `POST /predict` enforces header authentication, input guardrails, and asynchronous key telemetry.
- [x] Middleware injects `X-Response-Time` and baseline security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`).
- [x] Exception handling catches inference errors and formats structured, secure JSON error responses.

