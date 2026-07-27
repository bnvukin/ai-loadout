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
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
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
    def config_show(key: str, raw: int = 0) -> dict:
        # raw=1 returns unredacted content for editing (localhost-only tool). The editor
        # must save exactly what it loaded, so we can't hand it masked secrets.
        from ..config.discover import read_config

        return read_config(key, redact=(raw == 0))

    @app.get("/api/env")
    def env() -> dict:
        from ..config.env import inspect_all_env, inspect_env, path_summary

        return {"known": inspect_env(), "all": inspect_all_env(), "path": path_summary()}

    @app.get("/api/security")
    def security_report() -> dict:
        from ..security.posture import build_trust_posture

        return build_trust_posture(store)

    @app.post("/api/diagnostics")
    def diagnostics_bundle() -> dict:
        from ..diagnostics.bundle import create_diagnostics_bundle

        return create_diagnostics_bundle(store)

    @app.get("/api/diagnostics/{filename}")
    def diagnostics_download(filename: str):
        from ..core import paths

        safe = Path(filename).name
        if not safe.startswith("diagnostics-") or not safe.endswith(".zip"):
            raise HTTPException(status_code=404, detail="not found")
        target = paths.diagnostics_dir() / safe
        if not target.is_file():
            raise HTTPException(status_code=404, detail="not found")
        return FileResponse(str(target), filename=safe, media_type="application/zip")

    @app.get("/api/backups")
    def backups_list() -> dict:
        from ..backup.snapshot import list_snapshots

        return {"snapshots": list_snapshots()}

    @app.get("/api/updates")
    def updates_report() -> dict:
        from ..update.report import build_update_report

        return build_update_report(store)

    @app.get("/api/download/plan")
    def download_plan(url: str, dest: str = "") -> dict:
        from ..download.manager import plan_download

        return plan_download(url, dest=dest or None)

    @app.post("/api/download")
    def download_start(payload: Optional[dict] = None) -> dict:
        from ..download.manager import download_with_bus, plan_download

        payload = payload or {}
        url = payload.get("url")
        if not url:
            raise HTTPException(status_code=400, detail="url is required")
        plan = plan_download(url, dest=payload.get("dest"), expected_sha256=payload.get("sha256"))
        if not plan["ok"]:
            raise HTTPException(status_code=400, detail=plan.get("reason") or "blocked")
        if payload.get("dry_run") or not payload.get("confirm"):
            return {"dry_run": True, "plan": plan}
        started = orch.launch_action(
            f"download:{url}",
            lambda: download_with_bus(
                store,
                url,
                dest=payload.get("dest"),
                expected_sha256=payload.get("sha256"),
            ),
        )
        return {"dry_run": False, "plan": plan, **started}

    @app.get("/api/benchmark/latest")
    def benchmark_latest() -> dict:
        from ..benchmark.runner import latest_benchmark

        result = latest_benchmark()
        return {"benchmark": result}

    @app.post("/api/benchmark")
    def benchmark_run(payload: Optional[dict] = None) -> dict:
        from ..benchmark.runner import run_benchmark

        payload = payload or {}
        fast = not payload.get("full")
        started = orch.launch_action(
            "benchmark",
            lambda: run_benchmark(store, fast=fast, bus=store.bus),
        )
        return started

    @app.post("/api/backups")
    def backups_create() -> dict:
        from ..backup.snapshot import create_snapshot

        result = create_snapshot(store)
        store.bus.info(
            "Config snapshot created",
            kind="backup",
            target=result["id"],
        )
        return result

    @app.post("/api/backups/{snapshot_id}/restore")
    def backups_restore(snapshot_id: str, payload: Optional[dict] = None) -> dict:
        from ..backup.snapshot import RESTORE_CONFIRM, RestoreError, restore_snapshot

        payload = payload or {}
        try:
            result = restore_snapshot(snapshot_id, confirm=payload.get("confirm"))
        except RestoreError as exc:
            raise HTTPException(
                status_code=400,
                detail={"error": str(exc), "required": RESTORE_CONFIRM},
            ) from exc
        store.bus.warning(
            f"Restored snapshot {snapshot_id}",
            kind="backup",
            target=snapshot_id,
        )
        return result

    @app.get("/api/events")
    def events(after: int = 0) -> dict:
        return {
            "events": [e.to_dict() for e in store.bus.history(after)],
            "last": store.bus.last_id(),
        }

    # -- read-only detection tasks ----------------------------------------------------
    @app.post("/api/scan")
    def scan() -> dict:
        return orch.start()

    @app.post("/api/tasks/{name}")
    def run_task(name: str) -> dict:
        return orch.start([name])

    @app.get("/api/tasks")
    def tasks() -> dict:
        return orch.status()

    # -- Phase 2: mutating actions ----------------------------------------------------
    def _kind_for(key: str) -> str:
        from ..deps.registry import by_key as dep_by_key

        return "dependency" if dep_by_key(key) else "runtime"

    def _run_or_preview(key: str, kind: str, action: str, payload: dict) -> dict:
        from ..actions.runner import preview, run_action

        command = preview(key, kind, action)
        # A real run needs explicit confirm; anything else returns the dry-run command.
        if payload.get("dry_run") or not payload.get("confirm"):
            return {"dry_run": True, "command": command}
        started = orch.launch_action(
            f"{action}:{key}", lambda: run_action(store, key, kind, action)
        )
        return {"dry_run": False, "command": command, **started}

    @app.get("/api/component/{key}/advice")
    def component_advice_ep(key: str) -> dict:
        from ..actions.advice import component_advice
        from ..actions.runner import preview

        kind = _kind_for(key)
        return {
            "advice": component_advice(key),
            "install": preview(key, kind, "install"),
            "upgrade": preview(key, kind, "upgrade"),
        }

    @app.post("/api/component/{key}/install")
    def component_install(key: str, payload: Optional[dict] = None) -> dict:
        return _run_or_preview(key, _kind_for(key), "install", payload or {})

    @app.post("/api/component/{key}/upgrade")
    def component_upgrade(key: str, payload: Optional[dict] = None) -> dict:
        return _run_or_preview(key, _kind_for(key), "upgrade", payload or {})

    @app.post("/api/component/{key}/rescan")
    def component_rescan(key: str) -> dict:
        from ..actions.runner import rescan_component

        return {"component": rescan_component(store, key)}

    @app.post("/api/models/{key}/pull")
    def model_pull(key: str, payload: Optional[dict] = None) -> dict:
        from ..actions.runner import preview, run_action

        command = preview(key, "model", "pull")
        payload = payload or {}
        if payload.get("dry_run") or not payload.get("confirm"):
            return {"dry_run": True, "command": command}
        started = orch.launch_action(f"pull:{key}", lambda: run_action(store, key, "model", "pull"))
        return {"dry_run": False, "command": command, **started}

    @app.post("/api/models/refresh")
    def models_refresh() -> dict:
        from ..actions.runner import refresh_local_models

        return {"models": refresh_local_models(store)}

    @app.post("/api/repair")
    def do_repair(payload: Optional[dict] = None) -> dict:
        from ..actions.repair import repair as run_repair

        payload = payload or {}
        action = payload.get("action")
        target = payload.get("target")
        if not action:
            raise HTTPException(status_code=400, detail="action is required")
        if payload.get("dry_run"):
            return run_repair(store, action, target, dry_run=True)
        return orch.launch_action(
            f"repair:{action}:{target or ''}", lambda: run_repair(store, action, target)
        )

    @app.post("/api/config/{key}")
    def config_save(key: str, payload: Optional[dict] = None) -> dict:
        from ..config.edit import CONFIRM_TOKENS, EditError, apply_edit
        from ..config.registry import by_key as cfg_by_key

        payload = payload or {}
        content = payload.get("content")
        if content is None:
            raise HTTPException(status_code=400, detail="content is required")
        try:
            return apply_edit(key, content, confirm=payload.get("confirm"))
        except EditError as exc:
            target = cfg_by_key(key)
            required = CONFIRM_TOKENS.get(target.trust) if target else None
            raise HTTPException(
                status_code=400,
                detail={
                    "error": str(exc),
                    "required": required,
                    "trust": str(target.trust) if target else None,
                },
            ) from exc

    # -- live stream ------------------------------------------------------------------
    async def _safe_send_json(websocket: WebSocket, payload: dict) -> bool:
        """Send one JSON frame; return False if the socket is gone (don't kill the handler)."""

        try:
            await websocket.send_json(payload)
            return True
        except (WebSocketDisconnect, RuntimeError):
            raise
        except Exception:
            return False

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
            # Rapid-fire history replay can drop the connection before any frame is
            # delivered; yield between sends so the transport can flush each message.
            for past in store.bus.history():
                if not await _safe_send_json(websocket, past.to_dict()):
                    return
                await asyncio.sleep(0)
            while True:
                payload = await queue.get()
                if not await _safe_send_json(websocket, payload):
                    break
        except (WebSocketDisconnect, RuntimeError):
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
