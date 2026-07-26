"""Runs detection/analysis tasks against the digital twin, off the request thread.

The dashboard never blocks: a POST kicks off an orchestration, which runs the relevant
layer functions in a background thread. Each function already updates the ``StateStore``
and publishes events, so the browser sees progress live over the WebSocket. This same
orchestrator is where install/repair steps will plug in later -- today it drives the
read-only scans (machine, deps, runtimes, config, health).
"""

from __future__ import annotations

import threading
import time

from ..core.events import EventLevel
from ..core.state import StateStore

# Ordered so later tasks can rely on earlier ones (health reads what scan/deps found).
DEFAULT_TASKS: tuple[str, ...] = ("scan", "deps", "runtimes", "config", "health")


class Orchestrator:
    """Sequences read-only detection tasks in a single background worker."""

    def __init__(self, store: StateStore) -> None:
        self.store = store
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._status: dict[str, dict] = {name: {"status": "idle"} for name in DEFAULT_TASKS}
        # Phase 2: mutating actions (install/upgrade/pull/repair) run on their own worker
        # so a long install can't block a scan and vice-versa.
        self._action_thread: threading.Thread | None = None
        self._current_action: str | None = None
        self._action_log: dict[str, dict] = {}

    # -- task table -------------------------------------------------------------------
    def _fn(self, name: str):
        store = self.store
        if name == "scan":
            from ..detect.system import scan

            return lambda: scan(store)
        if name == "deps":
            from ..deps.detect import detect_all

            return lambda: detect_all(store)
        if name == "runtimes":
            from ..runtimes.detect import detect_all

            return lambda: detect_all(store)
        if name == "config":
            from ..config.discover import discover_all

            return lambda: discover_all(store)
        if name == "health":
            from ..health.checker import check

            return lambda: check(store)
        return None

    # -- status -----------------------------------------------------------------------
    def is_running(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def status(self) -> dict:
        with self._lock:
            return {
                "running": self.is_running(),
                "tasks": {name: dict(state) for name, state in self._status.items()},
                "action_running": self.action_running(),
                "current_action": self._current_action,
            }

    # -- background actions (Phase 2) -------------------------------------------------
    def action_running(self) -> bool:
        return self._action_thread is not None and self._action_thread.is_alive()

    def launch_action(self, action_id: str, fn) -> dict:
        """Run a mutating action in the background (one at a time). Returns immediately.

        ``fn`` is a zero-arg callable (already bound to the store) that performs the work
        and publishes its own progress/state events; the browser follows over the socket.
        """

        with self._lock:
            if self.action_running():
                return {"started": False, "busy": True, "current_action": self._current_action}
            self._current_action = action_id

            def _wrap() -> None:
                try:
                    result = fn()
                    outcome = {"status": "done", "result": result, "finished": time.time()}
                except Exception as exc:  # never let a worker crash take down the app
                    self.store.bus.error(f"Action failed: {exc}", source="action", target=action_id)
                    outcome = {"status": "error", "error": str(exc), "finished": time.time()}
                with self._lock:
                    self._action_log[action_id] = outcome
                    self._current_action = None

            self._action_thread = threading.Thread(target=_wrap, name="loadout-action", daemon=True)
            self._action_thread.start()
        return {"started": True, "action": action_id}

    def last_action(self, action_id: str) -> dict | None:
        with self._lock:
            return self._action_log.get(action_id)

    # -- execution --------------------------------------------------------------------
    def start(self, names: list[str] | None = None) -> dict:
        """Kick off an orchestration in the background (no-op if one is already running)."""

        with self._lock:
            if self.is_running():
                return self.status()
            selected = list(names or DEFAULT_TASKS)
            self._thread = threading.Thread(
                target=self.run_blocking, args=(selected,), name="loadout-orchestrator", daemon=True
            )
            self._thread.start()
        return self.status()

    def run_blocking(self, names: list[str] | None = None) -> dict:
        """Run the selected tasks inline (used by ``start`` and by tests)."""

        bus = self.store.bus
        selected = list(names or DEFAULT_TASKS)
        bus.publish(
            EventLevel.INFO,
            "Scan started",
            kind="step",
            source="orchestrator",
            target="orchestrator",
            tasks=selected,
        )
        for name in selected:
            fn = self._fn(name)
            if fn is None:
                continue
            with self._lock:
                self._status[name] = {"status": "running", "started": time.time()}
            bus.publish(
                EventLevel.INFO, f"{name}: running", kind="progress", target=name, status="running"
            )
            try:
                fn()
                result = {"status": "done", "finished": time.time()}
                bus.publish(
                    EventLevel.SUCCESS, f"{name}: done", kind="progress", target=name, status="done"
                )
            except Exception as exc:  # detection must never crash the worker
                result = {"status": "error", "error": str(exc), "finished": time.time()}
                bus.publish(
                    EventLevel.ERROR,
                    f"{name} failed: {exc}",
                    kind="progress",
                    target=name,
                    status="error",
                )
            with self._lock:
                self._status[name] = result
        bus.publish(
            EventLevel.SUCCESS,
            "Scan complete",
            kind="step",
            source="orchestrator",
            target="orchestrator",
        )
        return self.status()
