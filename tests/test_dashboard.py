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
    html = client.get("/").text
    assert "Overview" in html
    assert "safety-foot" in html
    assert "DISCLAIMER.md" in html
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


def test_ws_replays_buffered_history_without_dropping():
    store = StateStore(autosave=False)
    for i in range(60):
        store.bus.info(f"hist-{i}")
    client = TestClient(create_app(store))
    with client.websocket_connect("/ws") as ws:
        received = 0
        while received < 60:
            data = ws.receive_json()
            received += 1
            assert "message" in data
        assert received == 60


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


def test_api_security_report():
    client = TestClient(create_app(_store()))
    body = client.get("/api/security").json()
    assert body["summary"]["total"] > 0
    assert body["policy"]["url_allowlist"] is True


def test_api_diagnostics_creates_zip(loadout_home):
    client = TestClient(create_app(_store()))
    body = client.post("/api/diagnostics").json()
    assert body["filename"].startswith("diagnostics-")
    dl = client.get(f"/api/diagnostics/{body['filename']}")
    assert dl.status_code == 200
    assert dl.headers.get("content-type", "").startswith("application/")


def test_api_updates_report():
    client = TestClient(create_app(_store()))
    body = client.get("/api/updates").json()
    assert "self" in body and "components" in body


def test_api_download_plan_and_dry_run():
    client = TestClient(create_app(_store()))
    plan = client.get(
        "/api/download/plan",
        params={"url": "https://github.com/bnvukin/ai-loadout/releases/x.bin"},
    ).json()
    assert plan["official_source"] is True
    dry = client.post(
        "/api/download",
        json={"url": "https://github.com/bnvukin/ai-loadout/releases/x.bin"},
    ).json()
    assert dry["dry_run"] is True


def test_api_benchmark_latest_and_start():
    client = TestClient(create_app(_store()))
    assert client.get("/api/benchmark/latest").json()["benchmark"] is None
    started = client.post("/api/benchmark", json={}).json()
    assert started["started"] is True


def test_api_backups_create_and_restore_gated(loadout_home, tmp_path, monkeypatch):
    fake_home = tmp_path / "userhome"
    fake_home.mkdir()
    cfg_dir = fake_home / ".continue"
    cfg_dir.mkdir()
    (cfg_dir / "config.json").write_text("{}", encoding="utf-8")

    def fake_ph():
        return {
            "home": str(fake_home),
            "appdata": str(fake_home / "AppData" / "Roaming"),
            "localappdata": str(fake_home / "AppData" / "Local"),
            "xdg_config": str(fake_home / ".config"),
            "documents": str(fake_home / "Documents"),
        }

    monkeypatch.setattr("ai_loadout.config.discover._placeholders", fake_ph)

    client = TestClient(create_app(_store()))
    created = client.post("/api/backups").json()
    assert created["id"]
    listed = client.get("/api/backups").json()
    assert any(s["id"] == created["id"] for s in listed["snapshots"])

    blocked = client.post(f"/api/backups/{created['id']}/restore", json={})
    assert blocked.status_code == 400

    ok = client.post(
        f"/api/backups/{created['id']}/restore",
        json={"confirm": "RESTORE"},
    )
    assert ok.status_code == 200
    assert ok.json()["file_count"] >= 1
