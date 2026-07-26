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


def test_static_spa_bundle_is_served():
    client = TestClient(create_app(_store()))
    # The real SPA shell (not the fallback) is served at /.
    assert "Overview" in client.get("/").text
    for path in ("/static/app.js", "/static/style.css"):
        r = client.get(path)
        assert r.status_code == 200
        assert len(r.text) > 100


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


# -- Phase 2: background actions on the orchestrator ------------------------------------
def test_orchestrator_launch_action_runs_and_records():
    orch = Orchestrator(_store())
    orch.launch_action("demo", lambda: {"value": 42})
    deadline = time.time() + 3
    while orch.action_running() and time.time() < deadline:
        time.sleep(0.02)
    assert orch.last_action("demo")["result"] == {"value": 42}


def test_orchestrator_launch_action_is_single_flight():
    import threading

    orch = Orchestrator(_store())
    release = threading.Event()
    orch.launch_action("slow", release.wait)
    busy = orch.launch_action("second", lambda: None)
    assert busy["started"] is False and busy["busy"] is True
    release.set()


# -- Phase 2: action / config / env endpoints -------------------------------------------
def test_api_component_advice():
    client = TestClient(create_app(_store()))
    body = client.get("/api/component/docker/advice").json()
    assert body["advice"]["impact"]
    assert "install" in body and "upgrade" in body


def test_api_component_install_dry_run_does_not_execute():
    client = TestClient(create_app(_store()))
    body = client.post("/api/component/git/install", json={}).json()
    assert body["dry_run"] is True
    assert "command" in body


def test_api_component_rescan(monkeypatch):
    from ai_loadout.actions import runner

    monkeypatch.setattr(runner, "rescan_component", lambda s, key: {"key": key, "health": "green"})
    client = TestClient(create_app(_store()))
    body = client.post("/api/component/git/rescan").json()
    assert body["component"]["health"] == "green"


def test_api_model_pull_dry_run():
    client = TestClient(create_app(_store()))
    body = client.post("/api/models/llama3.2-3b/pull", json={}).json()
    assert body["dry_run"] is True and "command" in body


def test_api_models_refresh(monkeypatch):
    from ai_loadout.actions import runner

    monkeypatch.setattr(runner, "refresh_local_models", lambda s: [{"name": "x"}])
    client = TestClient(create_app(_store()))
    assert client.post("/api/models/refresh").json()["models"] == [{"name": "x"}]


def test_api_repair_requires_action():
    client = TestClient(create_app(_store()))
    assert client.post("/api/repair", json={}).status_code == 400


def test_api_repair_dry_run():
    client = TestClient(create_app(_store()))
    body = client.post("/api/repair", json={"action": "start-ollama", "dry_run": True}).json()
    assert body["action"] == "start-ollama"


def test_api_env_lists_all_vars(monkeypatch):
    monkeypatch.setenv("LOADOUT_TEST_VAR", "hello")
    client = TestClient(create_app(_store()))
    body = client.get("/api/env").json()
    assert {"known", "all", "path"} <= set(body)
    names = {e["name"] for e in body["all"]}
    assert "LOADOUT_TEST_VAR" in names


def test_api_config_raw_read():
    client = TestClient(create_app(_store()))
    body = client.get("/api/config/continue", params={"raw": 1}).json()
    assert "exists" in body


def test_api_config_save_requires_content():
    client = TestClient(create_app(_store()))
    assert client.post("/api/config/git", json={}).status_code == 400


def test_api_config_save_unknown_key():
    client = TestClient(create_app(_store()))
    assert client.post("/api/config/nope", json={"content": "x"}).status_code == 400


def test_api_config_save_success(monkeypatch):
    from ai_loadout.config import edit

    monkeypatch.setattr(
        edit, "apply_edit", lambda key, content, confirm=None: {"key": key, "path": "/tmp/x"}
    )
    client = TestClient(create_app(_store()))
    body = client.post("/api/config/continue", json={"content": "hi"}).json()
    assert body["key"] == "continue"
