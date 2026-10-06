"""API routing and middleware subsystem."""

from decide.api.routes.health import router as health_router, HealthResponse
from decide.api.routes.predict import router as predict_router, PredictResponse
from decide.api.middleware import (
    SecurityAndLatencyMiddleware,
    setup_middleware,
    setup_middleware_and_exceptions,
)

__all__ = [
    "health_router",
    "predict_router",
    "HealthResponse",
    "PredictResponse",
    "SecurityAndLatencyMiddleware",
    "setup_middleware",
    "setup_middleware_and_exceptions",
]
