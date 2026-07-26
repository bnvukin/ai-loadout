"""FastAPI app for the live dashboard: a thin, read-mostly view over the digital twin.

Design notes:

* Every GET reads straight from the ``StateStore`` (the single source of truth) so the
  API and the CLI can never disagree.
* Mutating routes (``/api/scan``) only *start* background work via the orchestrator and
  return immediately; progress arrives over the WebSocket.
* ``/ws`` bridges the synchronous :class:`EventBus` to asyncio: a subscriber pushes each
  event onto an ``asyncio.Queue`` via ``call_soon_threadsafe`` (publishes come from the
  orchestrator's worker thread), and the socket drains the queue. Clients dedupe by
  event ``id`` since a late subscriber also receives buffered history.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .. import __version__
from ..core.state import StateStore, load_state
from .orchestrator import Orchestrator

STATIC_DIR = Path(__file__).parent / "static"


def create_app(store: StateStore | None = None, orchestrator: Orchestrator | None = None):
    """Build the FastAPI application. ``store``/``orchestrator`` are injectable for tests."""

    store = store or load_state()
    orch = orchestrator or Orchestrator(store)

    app = FastAPI(title="Loadout Dashboard", version=__version__)
    app.state.store = store
    app.state.orchestrator = orch

    # -- read APIs --------------------------------------------------------------------
    @app.get("/api/version")
    def version() -> dict:
        return {"name": "ai-loadout", "version": __version__}

    @app.get("/api/state")
    def state() -> dict:
        return store.snapshot()

    @app.get("/api/health")
    def health() -> dict:
        from ..health.checker import check

        return check(store).to_dict()

    @app.get("/api/hardware")
    def hardware() -> dict:
        return store.hardware.to_dict() if store.hardware else {}

    @app.get("/api/components")
    def components() -> dict:
        return {"components": [c.to_dict() for c in store.components()]}

    @app.get("/api/models")
    def models() -> dict:
        from ..models.recommend import recommend_for_store

        recs = recommend_for_store(store)
        return {
            "installed": [m.to_dict() for m in store.models()],
            "recommendations": [r.to_dict() for r in recs],
        }

    @app.get("/api/config")
    def config() -> dict:
        from ..config.discover import discover_all
        from ..config.env import inspect_env, path_summary

        return {
            "configs": [cf.to_dict() for cf in discover_all(store)],
            "env": inspect_env(),
            "path": path_summary(),
        }

    @app.get("/api/config/{key}")
    def config_show(key: str) -> dict:
        from ..config.discover import read_config

        return read_config(key)

    @app.get("/api/events")
    def events(after: int = 0) -> dict:
        return {
            "events": [e.to_dict() for e in store.bus.history(after)],
            "last": store.bus.last_id(),
        }

    # -- actions ----------------------------------------------------------------------
    @app.post("/api/scan")
    def scan() -> dict:
        return orch.start()

    @app.post("/api/tasks/{name}")
    def run_task(name: str) -> dict:
        return orch.start([name])

    @app.get("/api/tasks")
    def tasks() -> dict:
        return orch.status()

    # -- live stream ------------------------------------------------------------------
    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        await websocket.accept()
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def on_event(event) -> None:
            try:
                loop.call_soon_threadsafe(queue.put_nowait, event.to_dict())
            except RuntimeError:
                pass  # loop is shutting down

        unsubscribe = store.bus.subscribe(on_event)
        try:
            for past in store.bus.history():
                await websocket.send_json(past)
            while True:
                await websocket.send_json(await queue.get())
        except (WebSocketDisconnect, RuntimeError):
            pass
        except Exception:
            pass
        finally:
            unsubscribe()

    # -- static SPA -------------------------------------------------------------------
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def index():
        index_html = STATIC_DIR / "index.html"
        if index_html.exists():
            return FileResponse(str(index_html))
        return HTMLResponse(
            "<h1>Loadout</h1><p>Dashboard UI is served from the static bundle "
            "(added in the frontend batch). The API is live under <code>/api</code>.</p>"
        )

    return app
