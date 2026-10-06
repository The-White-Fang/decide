# SUBTASK-4.3: Engine Lifecycle & Warmup

## Parent Task
[TASK-04: Model Execution Engine](file:///home/abhishek/decide/tasks/04-model-inference-engine/index.md)

## Target Code Path
`decide/engine/lifecycle.py`

## Objective
Manage model loading during application startup via FastAPI lifespan events, execute dummy inference to warm up JIT/PyTorch kernels, and maintain a global engine state registry for readiness probes.

## Functional Requirements
1. **Engine State Registry:**
   - Singleton or state container storing:
     - `is_loaded: bool`
     - `device_name: str` (e.g. `"cuda:0"`, `"cpu"`)
     - `classifier: Optional[MultiTaskClassifier]`
     - `load_time_seconds: float`
2. **Warmup Cycle:**
   - Perform a dummy single-token inference during startup to eliminate first-request cold-start latency spikes.
3. **Lifespan Context Manager:**
   - FastAPI lifespan hook:
     - Load model asynchronously or synchronously on startup.
     - Warm up classifier.
     - Set `is_loaded = True`.
     - On shutdown, clear GPU VRAM cache (`torch.cuda.empty_cache()` if available).
4. **Readiness Probe Contract (PRD Section 2.2 & 7.1):**
   - Provide an accessor `get_engine_state()` consumed by `GET /health`.

## Interface & Schema
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

class EngineState:
    is_loaded: bool = False
    device_name: str = "unknown"
    classifier: Optional[MultiTaskClassifier] = None
    load_time_seconds: float = 0.0

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load model, warm up, mark ready
    ...
    yield
    # Shutdown: Clean up resources
    ...

def get_engine_state() -> EngineState: ...
```

## Acceptance Criteria
- [x] Container startup completes model loading and warmup within < 12 seconds KPI.
- [x] `get_engine_state().is_loaded` transitions from `False` to `True` only after full warmup.
- [x] Shutdown safely releases CUDA resources.

