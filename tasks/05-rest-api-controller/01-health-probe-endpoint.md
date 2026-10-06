# SUBTASK-5.1: Health & Readiness Probe

## Parent Task
[TASK-05: REST API Controller](file:///home/abhishek/decide/tasks/05-rest-api-controller/index.md)

## Target Code Path
`decide/api/routes/health.py`

## Objective
Implement public, unauthenticated health and readiness probe endpoint `GET /health` to enable container orchestrator monitoring, Docker healthchecks, and Kubernetes readiness checks.

## Functional Requirements
1. **Endpoint Contract (PRD Section 7.1):**
   - Path: `GET /health`
   - Authentication: None (Public)
2. **Readiness Evaluation:**
   - Retrieve `EngineState` from `decide.engine.lifecycle`.
   - If model is loaded (`is_loaded == True`):
     - Return HTTP 200 with schema:
       ```json
       {
         "status": "healthy",
         "model_loaded": true,
         "device": "cuda:0"
       }
       ```
   - If model is still initializing (`is_loaded == False`):
     - Return HTTP 503 Service Unavailable with schema:
       ```json
       {
         "status": "initializing",
         "model_loaded": false,
         "device": "unknown"
       }
       ```
3. **Database Liveness Verification:**
   - Run lightweight `SELECT 1` on SQLite session to ensure database filesystem is writable and responsive.

## Interface & Schema
```python
from fastapi import APIRouter, Response, status
from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    device: str

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
def health_check(response: Response) -> HealthResponse:
    ...
```

## Acceptance Criteria
- [x] Returns HTTP 200 when engine is loaded and database responds.
- [x] Returns HTTP 503 during engine bootstrap.
- [x] Response matches exact schema defined in PRD Section 7.1.
- [x] Does not require `X-API-Key` or session credentials.

