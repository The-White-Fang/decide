"""Interactive model testing playground."""

import json
from pathlib import Path
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from decide.auth.session import get_current_admin
from decide.db.models import User
from decide.engine.lifecycle import get_engine_state

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(prefix="/admin/playground")

DEFAULT_SAMPLE_TEXT = "My order arrived broken and I want a replacement immediately."
DEFAULT_SAMPLE_TASKS = json.dumps(
    {
        "intent": ["refund", "replacement", "tracking", "general_inquiry"],
        "urgency": ["low", "normal", "critical"],
    },
    indent=2,
)


@router.get("", response_class=HTMLResponse)
def playground_page(
    request: Request,
    current_admin: User = Depends(get_current_admin),
):
    """Renders the interactive testing playground."""
    return templates.TemplateResponse(
        request=request,
        name="playground.html",
        context={
            "admin": current_admin,
            "sample_text": DEFAULT_SAMPLE_TEXT,
            "sample_tasks": DEFAULT_SAMPLE_TASKS,
        },
    )


@router.post("/test", response_class=HTMLResponse)
def playground_test(
    request: Request,
    text: str = Form(...),
    tasks_json: str = Form(...),
    current_admin: User = Depends(get_current_admin),
):
    """Executes live prediction against in-memory model and returns HTML result partial."""
    try:
        parsed_tasks = json.loads(tasks_json)
        if not isinstance(parsed_tasks, dict):
            raise ValueError("Tasks must be a JSON object mapping task names to label lists.")
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="partials/playground_result.html",
            context={
                "error": f"Invalid JSON schema: {str(e)}",
                "result": None,
                "latency_ms": 0.0,
            },
        )

    state = get_engine_state()
    if not state.is_loaded or state.classifier is None:
        return templates.TemplateResponse(
            request=request,
            name="partials/playground_result.html",
            context={
                "error": "Model is not loaded or initializing. Please verify container status.",
                "result": None,
                "latency_ms": 0.0,
            },
        )

    try:
        prediction = state.classifier.predict(text, parsed_tasks)
        return templates.TemplateResponse(
            request=request,
            name="partials/playground_result.html",
            context={
                "error": None,
                "result": json.dumps(prediction["result"], indent=2),
                "latency_ms": prediction["latency_ms"],
                "device": state.device_name,
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="partials/playground_result.html",
            context={
                "error": f"Prediction failed: {str(e)}",
                "result": None,
                "latency_ms": 0.0,
            },
        )
