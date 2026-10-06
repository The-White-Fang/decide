"""Input boundary limits and Denial-of-Service guardrails."""

from typing import Dict, List
from pydantic import BaseModel, Field, field_validator
from decide.config import get_settings


class PredictInputSchema(BaseModel):
    """Input payload validation schema for POST /predict."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="Text to analyze and classify; capped at 8,000 characters",
    )
    tasks: Dict[str, List[str]] = Field(
        ...,
        description="Mapping of task categories to candidate label lists",
    )

    @field_validator("tasks")
    @classmethod
    def validate_task_limits(cls, v: Dict[str, List[str]]) -> Dict[str, List[str]]:
        settings = get_settings()

        if not v or len(v) == 0:
            raise ValueError("Tasks dictionary must contain at least one task.")

        if len(v) > settings.max_task_count:
            raise ValueError(f"Task count ({len(v)}) exceeds maximum allowed ({settings.max_task_count}).")

        for task_name, labels in v.items():
            if not isinstance(task_name, str) or not task_name.strip():
                raise ValueError("Task names must be non-empty strings.")
            if len(task_name) > 100:
                raise ValueError(f"Task name '{task_name}' exceeds 100 characters.")

            if not labels or len(labels) == 0:
                raise ValueError(f"Task '{task_name}' must have at least one candidate label.")

            if len(labels) > settings.max_labels_per_task:
                raise ValueError(
                    f"Task '{task_name}' has {len(labels)} labels, exceeding maximum of {settings.max_labels_per_task}."
                )

            seen_labels = set()
            for label in labels:
                if not isinstance(label, str) or not label.strip():
                    raise ValueError(f"Labels in task '{task_name}' must be non-empty strings.")
                if len(label) > 100:
                    raise ValueError(f"Label in task '{task_name}' exceeds maximum length of 100 characters.")
                cleaned = label.strip()
                if cleaned in seen_labels:
                    raise ValueError(f"Duplicate label '{cleaned}' in task '{task_name}'.")
                seen_labels.add(cleaned)

        return v
