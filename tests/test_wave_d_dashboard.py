"""Tests for Wave D dashboard endpoints."""

from __future__ import annotations

from ai_loadout.core.models import Hardware
from ai_loadout.core.state import StateStore
from ai_loadout.dashboard.orchestrator import Orchestrator

pytest = __import__("pytest")
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from ai_loadout.dashboard.server import create_app  # noqa: E402


def _store() -> StateStore:
    store = StateStore(autosave=False)
    store.set_hardware(Hardware(os_family="linux", ram_total_gb=8.0))
    return store


def test_api_wave_d_endpoints(monkeypatch):
    monkeypatch.setattr(
        "ai_loadout.offline.connectivity.check_connectivity",
        lambda **k: {"online": True, "probe": "mock", "latency_ms": 1, "reason": None},
    )
    client = TestClient(create_app(_store()))
    assert client.get("/api/connectivity").json()["online"] is True
    assert client.get("/api/connections").json()["total"] >= 5
    profiles = client.get("/api/profiles").json()["profiles"]
    assert len(profiles) >= 1
    plan = client.get("/api/profiles/minimal/plan").json()
    assert plan["profile"] == "minimal"
    dry = client.post("/api/profiles/minimal/install", json={}).json()
    assert dry["dry_run"] is True
    tel = client.get("/api/telemetry").json()
    assert tel["enabled"] is False
    mon = client.get("/api/monitor").json()
    assert mon["settings"]["monitor_enabled"] is False


def test_monitor_toggle(monkeypatch, tmp_path):
    monkeypatch.setenv("LOADOUT_HOME", str(tmp_path))
    from ai_loadout.core.settings import reset_settings_cache

    reset_settings_cache()
    orch = Orchestrator(_store())
    app = create_app(_store(), orchestrator=orch)
    client = TestClient(app)
    off = client.post("/api/monitor", json={"enabled": False, "interval": 120}).json()
    assert off["monitor"]["enabled"] is False
    on = client.post("/api/monitor", json={"enabled": True, "interval": 120}).json()
    assert on["ok"] is True
    orch.configure_monitor(enabled=False)
