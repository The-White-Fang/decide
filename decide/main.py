"""FastAPI application factory, lifespan, and router mounting for decide."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from decide.api.middleware import setup_middleware
from decide.api.routes.health import router as health_router
from decide.api.routes.predict import router as predict_router
from decide.engine.lifecycle import lifespan
from decide.web.routes.auth import router as web_auth_router
from decide.web.routes.dashboard import router as web_dashboard_router
from decide.web.routes.playground import router as web_playground_router

STATIC_DIR = Path(__file__).resolve().parent / "web" / "static"


def create_app() -> FastAPI:
    """Creates and configures the FastAPI application."""
    app = FastAPI(
        title="decide",
        description="Self-hosted inference microservice for GLiNER2.5-Decide with SQLite key management",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Middleware
    setup_middleware(app)

    # Mount static assets
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Mount REST API endpoints
    app.include_router(health_router)
    app.include_router(predict_router)

    # Mount Admin Web GUI endpoints
    app.include_router(web_auth_router)
    app.include_router(web_dashboard_router)
    app.include_router(web_playground_router)

    return app


app = create_app()
