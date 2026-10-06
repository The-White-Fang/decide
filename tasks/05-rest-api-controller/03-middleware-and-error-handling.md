# SUBTASK-5.3: Middleware & Error Handling

## Parent Task
[TASK-05: REST API Controller](file:///home/abhishek/decide/tasks/05-rest-api-controller/index.md)

## Target Code Path
`decide/api/middleware.py`

## Objective
Implement global HTTP exception handling, request latency logging middleware, and uniform error serialization across all API and GUI routes.

## Functional Requirements
1. **Uniform Error Serialization:**
   - Ensure all REST endpoints return standardized JSON errors:
     ```json
     {
       "error": {
         "code": 403,
         "message": "Key is invalid, expired, or revoked."
       }
     }
     ```
   - Provide custom exception handlers for:
     - `HTTPException`
     - `RequestValidationError` (HTTP 422)
     - `InferenceException` (HTTP 500)
     - Uncaught generic exceptions (`Exception` -> HTTP 500)
2. **Timing & Latency Middleware:**
   - Measure request execution time in milliseconds.
   - Attach `X-Response-Time: <ms>ms` header to every HTTP response.
   - Emit structured logs with method, path, status, and duration.
3. **Security Headers Middleware:**
   - Add `X-Content-Type-Options: nosniff`.
   - Add `X-Frame-Options: DENY`.
   - Add `Referrer-Policy: strict-origin-when-cross-origin`.

## Interface & Schema
```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import time

def setup_middleware_and_exceptions(app: FastAPI) -> None:
    @app.middleware("http")
    async def add_process_time_and_security_headers(request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = (time.perf_counter() - start_time) * 1000
        response.headers["X-Response-Time"] = f"{process_time:.2f}ms"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        ...
```

## Acceptance Criteria
- [x] Header `X-Response-Time` present on all responses.
- [x] Error responses return structured, helpful JSON without leaking sensitive stack traces.
- [x] Security headers prevent MIME-sniffing and clickjacking.

