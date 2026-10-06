"""Middleware for request latency profiling and security headers."""

import time
import logging
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from decide.engine.classifier import InferenceException

logger = logging.getLogger("decide.api")


class SecurityAndLatencyMiddleware(BaseHTTPMiddleware):
    """Measures request response latency and attaches baseline security headers."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


def setup_middleware_and_exceptions(app: FastAPI) -> None:
    """Configures global middlewares and domain exception handlers."""
    app.add_middleware(SecurityAndLatencyMiddleware)

    @app.exception_handler(InferenceException)
    async def inference_exception_handler(request: Request, exc: InferenceException):
        logger.error(f"Inference error during request to {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Model inference failed: {str(exc)}"},
        )


# Backward-compatible alias
setup_middleware = setup_middleware_and_exceptions

