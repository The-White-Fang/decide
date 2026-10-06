# SUBTASK-1.1: Environment & Settings Management

## Parent Task
[TASK-01: Core Configuration & Cryptographic Utilities](file:///home/abhishek/decide/tasks/01-core-configuration/index.md)

## Target Code Path
`decide/config.py`

## Objective
Implement a centralized, type-safe settings management module using Pydantic Settings to parse and validate runtime environment variables, apply defaults, and define global system constants.

## Functional Requirements
1. **Environment Variables Support (PRD Section 8):**
   - `ADMIN_USERNAME`: `str` (Default: `"admin"`)
   - `ADMIN_PASSWORD`: `Optional[str]` (Default: `None`. If unset, triggers auto-generation during bootstrap)
   - `FORCE_ADMIN_RESET`: `bool` (Default: `False`)
   - `DATABASE_PATH`: `Path` (Default: `"/data/decide.db"`)
   - `SECRET_KEY`: `Optional[str]` (Default: `None`. Auto-generated if unset)
   - `DEVICE`: `str` (Default: `"auto"`, allowed: `["auto", "cpu", "cuda"]`)
   - `PORT`: `int` (Default: `8000`)
   - `WORKERS`: `int` (Default: `1`, enforced default to 1 for PyTorch VRAM safety)
2. **Denial of Service & Guardrail Constants (PRD Section 10):**
   - `MAX_INPUT_TEXT_LENGTH`: `int = 8000` (Max character limit for input text)
   - `MAX_TASK_COUNT`: `int = 20` (Max classification task schemas per request)
   - `MAX_LABELS_PER_TASK`: `int = 50` (Max candidate labels per task)
3. **Model Configuration:**
   - `MODEL_CHECKPOINT`: `str = "fastino/GLiNER2.5-Decide"`
   - `CACHE_DIR`: `Path = Path("/root/.cache/huggingface/")`
4. **Directory Auto-Creation:**
   - Helper property to ensure the parent directory of `DATABASE_PATH` exists or is created automatically upon startup.

## Interface & Schema
```python
from pathlib import Path
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    admin_username: str = "admin"
    admin_password: Optional[str] = None
    force_admin_reset: bool = False
    database_path: Path = Path("/data/decide.db")
    secret_key: Optional[str] = None
    device: Literal["auto", "cpu", "cuda"] = "auto"
    port: int = 8000
    workers: int = 1

    # Security limits
    max_input_text_length: int = 8000
    max_task_count: int = 20
    max_labels_per_task: int = 50

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

def get_settings() -> Settings:
    ...
```

## Acceptance Criteria
- [ ] Loads variables seamlessly from OS environment and optional `.env` file.
- [ ] Validates `device` to be one of `"auto"`, `"cpu"`, or `"cuda"`.
- [ ] Enforces integer constraints on `port` and `workers`.
- [ ] Exposes singleton `get_settings()` with `@lru_cache`.
