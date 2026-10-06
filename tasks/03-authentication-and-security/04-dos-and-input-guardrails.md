# SUBTASK-3.4: DoS Guardrails & Input Limits

## Parent Task
[TASK-03: Authentication & Security Guard](file:///home/abhishek/decide/tasks/03-authentication-and-security/index.md)

## Target Code Path
`decide/auth/guardrails.py`

## Objective
Enforce resource exhaustion safeguards, input length validation, and task complexity bounds to mitigate Denial of Service (DoS) attacks as specified in PRD Section 10.

## Functional Requirements
1. **Input Text Length Enforcement (PRD Section 10):**
   - Maximum character limit of 8,000 characters per request on `text`.
   - Requests exceeding 8,000 characters immediately abort with HTTP 422 Unprocessable Entity and message: `"Input text exceeds maximum allowed length of 8,000 characters"`.
2. **Task Schema Complexity Limits:**
   - Maximum tasks per request: 20 tasks.
   - Maximum candidate labels per task: 50 labels.
   - Tasks with 0 candidate labels or duplicate labels are rejected with HTTP 422.
3. **Payload Sanitization & Anti-ReDoS:**
   - Validate task and label strings for valid non-empty, non-whitespace characters and reasonable length (e.g. max 100 characters per label).
4. **Timing Attack Protections:**
   - Enforce constant-time hash comparisons for all authentication checks (`hmac.compare_digest`).

## Interface & Schema
```python
from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator
from decide.config import get_settings

class PredictInputSchema(BaseModel):
    text: str = Field(..., min_length=1, max_length=8000)
    tasks: dict[str, list[str]]

    @field_validator("tasks")
    @classmethod
    def validate_tasks(cls, v: dict[str, list[str]]) -> dict[str, list[str]]:
        settings = get_settings()
        if len(v) == 0:
            raise ValueError("At least one task must be specified.")
        if len(v) > settings.max_task_count:
            raise ValueError(f"Task count exceeds limit of {settings.max_task_count}.")
        for task_name, labels in v.items():
            if len(labels) == 0:
                raise ValueError(f"Task '{task_name}' must have at least one candidate label.")
            if len(labels) > settings.max_labels_per_task:
                raise ValueError(f"Task '{task_name}' exceeds maximum of {settings.max_labels_per_task} labels.")
        return v
```

## Acceptance Criteria
- [ ] Text payload with > 8,000 characters returns HTTP 422.
- [ ] Tasks dictionary with > 20 tasks returns HTTP 422.
- [ ] Any task with > 50 labels returns HTTP 422.
- [ ] Valid requests pass without performance degradation.
