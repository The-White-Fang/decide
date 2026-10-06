# SUBTASK-5.2: Predict Inference Route

## Parent Task
[TASK-05: REST API Controller](file:///home/abhishek/decide/tasks/05-rest-api-controller/index.md)

## Target Code Path
`decide/api/routes/predict.py`

## Objective
Implement secured high-performance REST endpoint `POST /predict` supporting single-pass multi-task classification with header authentication, input validation, background telemetry logging, and standardized response schemas.

## Functional Requirements
1. **Endpoint Contract (PRD Section 7.2):**
   - Path: `POST /predict`
   - Header: `X-API-Key: <secret_key>` (mandatory)
2. **Request Validation:**
   - Request Body:
     ```json
     {
       "text": "My order arrived broken and I want a replacement immediately.",
       "tasks": {
         "intent": ["refund", "replacement", "tracking", "general_inquiry"],
         "urgency": ["low", "normal", "critical"]
       }
     }
     ```
   - Input guardrails: Max 8,000 characters text, max 20 tasks, max 50 labels per task.
   - Return HTTP 422 for schema or constraint violations.
3. **Authentication & Authorization:**
   - Evaluated via `verify_api_key` dependency.
   - Return HTTP 401 if header is omitted.
   - Return HTTP 403 if key is revoked, invalid, or malformed.
4. **Model Execution & Response:**
   - Forward validated payload to `MultiTaskClassifier.predict()`.
   - Return HTTP 200 with result payload:
     ```json
     {
       "result": {
         "intent": "replacement",
         "urgency": "critical"
       }
     }
     ```
5. **Telemetry & Error Handling:**
   - Update `last_used_at` asynchronously via `BackgroundTasks`.
   - Wrap unhandled model inference failures and return HTTP 500.

## Interface & Schema
```python
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from decide.auth.api_key import verify_api_key
from decide.auth.guardrails import PredictInputSchema
from decide.db.models import APIKey

class PredictResponse(BaseModel):
    result: dict[str, str]

router = APIRouter()

@router.post("/predict", response_model=PredictResponse)
async def predict_intent(
    payload: PredictInputSchema,
    background_tasks: BackgroundTasks,
    current_key: APIKey = Depends(verify_api_key),
) -> PredictResponse:
    ...
```

## Acceptance Criteria
- [x] Matches PRD §7.2 request and response contracts exactly.
- [x] Header `X-API-Key` enforced on all requests.
- [x] Valid requests return 200 with mapped label dictionary.
- [x] Missing header produces 401 Unauthorized; invalid/revoked keys produce 403 Forbidden.
- [x] Malformed payload or length violations produce 422 Unprocessable Entity.
- [x] Key usage timestamp is updated asynchronously without adding latency to the response.

