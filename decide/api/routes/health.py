"""Public health check and container readiness probe."""

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from decide.db.session import get_session_context
from decide.engine.lifecycle import get_engine_state

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    device: str


@router.get("/health", response_model=HealthResponse)
def health_probe(response: Response) -> HealthResponse:
    """
    Public health check endpoint.
    Returns 200 OK when model is loaded and DB is responsive, or 503 when initializing or degraded.
    """
    state = get_engine_state()

    db_healthy = True
    try:
        with get_session_context() as session:
            session.execute(text("SELECT 1"))
    except Exception:
        db_healthy = False

    if state.is_loaded and db_healthy:
        return HealthResponse(
            status="healthy",
            model_loaded=True,
            device=state.device_name,
        )
    elif not state.is_loaded:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(
            status="initializing",
            model_loaded=False,
            device=state.device_name,
        )
    else:
        # Model is loaded, but DB check failed
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(
            status="degraded",
            model_loaded=True,
            device=state.device_name,
        )

