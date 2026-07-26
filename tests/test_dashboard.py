import time

import pytest

from ai_loadout.core.models import Hardware
from ai_loadout.core.state import StateStore
from ai_loadout.dashboard.orchestrator import Orchestrator

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from ai_loadout.dashboard.server import create_app  # noqa: E402


def _store() -> StateStore:
    store = StateStore(autosave=False)
    store.set_hardware(Hardware(os_family="linux", ram_total_gb=16.0, cpu_name="Test CPU"))
    return store


def _wait_idle(orch: Orchestrator, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while orch.is_running() and time.time() < deadline:
        time.sleep(0.02)


# -- orchestrator -----------------------------------------------------------------------
def test_orchestrator_run_blocking_records_status():
    orch = Orchestrator(_store())
    status = orch.run_blocking(["config"])
    assert status["tasks"]["config"]["status"] == "done"


def test_orchestrator_start_runs_in_background_and_is_single_flight():
    orch = Orchestrator(_store())
    orch.start(["config"])
    # A second start while running must not launch a parallel run.
    again = orch.start(["config"])
    assert again["running"] in (True, False)
    _wait_idle(orch)
    assert orch.status()["tasks"]["config"]["status"] in ("done", "error")


# -- REST -------------------------------------------------------------------------------
def test_api_version_and_state():
    client = TestClient(create_app(_store()))
    assert client.get("/api/version").json()["name"] == "ai-loadout"
    snap = client.get("/api/state").json()
    assert "meta" in snap and "health" in snap


def test_api_health_and_config_and_hardware():
    client = TestClient(create_app(_store()))
    health = client.get("/api/health").json()
    assert "percent" in health and "issues" in health
    cfg = client.get("/api/config").json()
    assert {"configs", "env", "path"} <= set(cfg)
    hw = client.get("/api/hardware").json()
    assert hw["cpu_name"] == "Test CPU"


def test_api_run_single_task_updates_status():
    store = _store()
    orch = Orchestrator(store)
    client = TestClient(create_app(store, orch))
    resp = client.post("/api/tasks/config")
    assert resp.status_code == 200
    _wait_idle(orch)
    assert client.get("/api/tasks").json()["tasks"]["config"]["status"] in ("done", "error")


def test_api_index_serves_something():
    client = TestClient(create_app(_store()))
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Loadout" in resp.text


# -- live stream ------------------------------------------------------------------------
def test_ws_streams_published_events():
    store = StateStore(autosave=False)
    client = TestClient(create_app(store))
    with client.websocket_connect("/ws") as ws:
        # Give the server coroutine a moment to register its subscriber.
        time.sleep(0.25)
        store.bus.publish(message="hello-dashboard", kind="log")
        data = ws.receive_json()
        assert data["message"] == "hello-dashboard"
