"""Runtime configuration management using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration for decide microservice."""

    # Admin bootstrap credentials
    admin_username: str = Field(
        default="admin",
        description="Username for the primary administrative account",
    )
    admin_password: Optional[str] = Field(
        default=None,
        description="Password for admin; auto-generated and logged to stdout if unset",
    )
    force_admin_reset: bool = Field(
        default=False,
        description="If true, overrides existing admin password on container start",
    )

    # Persistence
    database_path: Path = Field(
        default=Path("/data/decide.db"),
        description="Absolute path to SQLite database inside container",
    )

    # Session & Security
    secret_key: Optional[str] = Field(
        default=None,
        description="Secret key for signing admin session cookies; auto-generated if unset",
    )

    # Compute & Serving
    device: Literal["auto", "cpu", "cuda"] = Field(
        default="auto",
        description="Device target: auto, cpu, or cuda",
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Port on which the FastAPI application listens",
    )
    workers: int = Field(
        default=1,
        ge=1,
        le=32,
        description="Uvicorn worker count (keep at 1 for PyTorch VRAM safety)",
    )

    # Denial of Service & Guardrail Constants (PRD Section 10)
    max_input_text_length: int = Field(
        default=8000,
        gt=0,
        description="Maximum character limit enforced on input text",
    )
    max_task_count: int = Field(
        default=20,
        gt=0,
        description="Maximum task schemas per classification request",
    )
    max_labels_per_task: int = Field(
        default=50,
        gt=0,
        description="Maximum candidate labels per task",
    )

    # Model Settings
    model_checkpoint: str = Field(
        default="fastino/GLiNER2.5-Decide",
        description="Hugging Face model checkpoint repository identifier",
    )
    cache_dir: Path = Field(
        default=Path("/root/.cache/huggingface/"),
        description="Path to local Hugging Face model cache",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_path", mode="before")
    @classmethod
    def parse_database_path(cls, v: str | Path) -> Path:
        return Path(v)

    @field_validator("cache_dir", mode="before")
    @classmethod
    def parse_cache_dir(cls, v: str | Path) -> Path:
        return Path(v)

    def ensure_db_dir(self) -> Path:
        """Ensures the parent directory for database_path exists."""
        db_dir = self.database_path.parent
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Returns a singleton cached instance of application settings."""
    return Settings()
