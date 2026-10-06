# LLD-05: REST API & Middleware Subsystem

## 1. Overview & Protocol Specification

The REST API exposes public health probes and secured classification endpoints conforming strictly to PRD Section 7.

---

## 2. Endpoint Contracts

### 2.1 Health Probe (`GET /health`)
- **Authentication:** None (Public)
- **Response Codes:**
  - `200 OK` (when model is loaded and DB is responsive)
  - `503 Service Unavailable` (while model is loading)
- **Response Schema (`HealthResponse`):**
  ```json
  {
    "status": "healthy",
    "model_loaded": true,
    "device": "cuda:0"
  }
  ```

### 2.2 Text Classification (`POST /predict`)
- **Authentication:** Header `X-API-Key: <secret_key>` (mandatory)
- **Status Codes:**
  - `200 OK`: Valid request with prediction results.
  - `401 Unauthorized`: Missing `X-API-Key` header.
  - `403 Forbidden`: Invalid or revoked key.
  - `422 Unprocessable Entity`: Input bounds violated (> 8000 chars, > 20 tasks, malformed JSON).
  - `500 Internal Server Error`: Unhandled model failure.

#### Request Schema (`PredictRequest`)
```python
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List

class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)
    tasks: Dict[str, List[str]]

    @field_validator("tasks")
    @classmethod
    def validate_task_limits(cls, v: Dict[str, List[str]]):
        if not v or len(v) > 20:
            raise ValueError("Tasks must contain between 1 and 20 task entries.")
        for task, labels in v.items():
            if not labels or len(labels) > 50:
                raise ValueError(f"Task '{task}' must contain between 1 and 50 labels.")
        return v
```

#### Response Schema (`PredictResponse`)
```python
class PredictResponse(BaseModel):
    result: Dict[str, str]
```

---

## 3. Asynchronous Telemetry Architecture

When `POST /predict` executes successfully:
1. Model prediction is computed and formatted.
2. An asynchronous task `update_last_used_at(key_id)` is dispatched to FastAPI's `BackgroundTasks`.
3. The HTTP response is returned immediately to the client without waiting for SQLite write I/O.
4. The background task opens a short-lived SQLite session via `get_session_context()` and updates `last_used_at = datetime.utcnow()`.

---

## 4. Middleware & Standardized Error Handling

### 4.1 Latency & Security Headers Middleware
Applied to all responses:
- `X-Response-Time`: Duration of request execution in milliseconds (e.g. `24.50ms`).
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`

### 4.2 Error Representation
All error responses conform to a unified format:
```json
{
  "detail": "Error description message"
}
```
Or structured error format for programmatic clients.
