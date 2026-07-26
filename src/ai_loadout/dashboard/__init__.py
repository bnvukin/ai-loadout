"""The live dashboard: FastAPI + WebSocket over the digital twin.

``create_app`` builds the API (read routes + a scan trigger + a live event stream) and
``serve`` runs it with uvicorn. The web stack is an optional extra
(``pip install ai-loadout[dashboard]``) so the core CLI stays dependency-light.
"""

from .orchestrator import DEFAULT_TASKS, Orchestrator

__all__ = ["DEFAULT_TASKS", "Orchestrator", "create_app", "serve"]


def __getattr__(name: str):
    # Lazily expose create_app/serve so importing this package never requires FastAPI.
    if name == "create_app":
        from .server import create_app

        return create_app
    if name == "serve":
        from .run import serve

        return serve
    raise AttributeError(name)
