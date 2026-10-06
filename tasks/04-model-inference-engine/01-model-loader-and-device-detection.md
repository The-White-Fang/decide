# SUBTASK-4.1: Model Loader & Device Detection

## Parent Task
[TASK-04: Model Execution Engine](file:///home/abhishek/decide/tasks/04-model-inference-engine/index.md)

## Target Code Path
`decide/engine/loader.py`

## Objective
Implement dynamic device detection (`auto`, `cuda`, `cpu`) and load the `fastino/GLiNER2.5-Decide` model from local disk weights using `gliner2.AutoExtractor` with offline execution guarantees.

## Functional Requirements
1. **Device Resolution (PRD Section 8):**
   - If `settings.device == "auto"`:
     - Check `torch.cuda.is_available()`.
     - If true, select `"cuda:0"` (or primary GPU).
     - Otherwise, select `"cpu"`.
   - If `settings.device == "cuda"`:
     - Raise a descriptive error if CUDA is not available, otherwise bind `"cuda:0"`.
   - If `settings.device == "cpu"`:
     - Bind `"cpu"`.
2. **Model Weight Resolution (PRD Section 9.2):**
   - Check local cache path (`/root/.cache/huggingface/` or configured cache dir).
   - Use `AutoExtractor.from_pretrained(model_name, local_files_only=..., cache_dir=...)`.
   - Set model to evaluation mode (`model.eval()`).
   - Move model to resolved target device.
3. **Singleton Worker Context:**
   - Single-process in-memory worker context per Uvicorn worker (keeping worker count at 1 for PyTorch VRAM safety).

## Interface & Schema
```python
from typing import Tuple, Any
import torch
from decide.config import Settings

def resolve_device(configured_device: str) -> torch.device:
    """Resolves 'auto', 'cuda', or 'cpu' to a torch.device instance."""
    ...

def load_gliner_model(
    checkpoint: str,
    device: torch.device,
    cache_dir: Optional[Path] = None,
    local_files_only: bool = False
) -> Any:
    """Loads GLiNER2.5 model and moves it to device."""
    ...
```

## Acceptance Criteria
- [x] Device auto-detects `cuda:0` when available and gracefully defaults to `cpu`.
- [x] Explicitly setting `DEVICE=cpu` forces CPU execution even if a GPU is present.
- [x] Successfully instantiates `AutoExtractor` from local pre-baked cache directory without external network calls.

