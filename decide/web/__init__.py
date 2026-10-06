"""Administrative Web GUI engine for decide."""

from decide.web.routes.auth import router as web_auth_router
from decide.web.routes.dashboard import router as web_dashboard_router
from decide.web.routes.playground import router as web_playground_router

__all__ = [
    "web_auth_router",
    "web_dashboard_router",
    "web_playground_router",
]
