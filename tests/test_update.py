"""Tests for Layer 16 — update manager."""

from __future__ import annotations

import json

from ai_loadout.core.lifecycle import ComponentState, Health
from ai_loadout.core.models import Component, Hardware
from ai_loadout.core.state import StateStore
from ai_loadout.update.report import build_update_report
from ai_loadout.update.self_check import check_self_update, parse_pypi_latest


def test_parse_pypi_latest():
    payload = {"info": {"version": "0.2.0"}}
    assert parse_pypi_latest(payload) == "0.2.0"


def test_check_self_update_newer_available(monkeypatch):
    def fake_open(_req, timeout=8):
        body = json.dumps({"info": {"version": "99.0.0"}}).encode("utf-8")

        class R:
            def read(self):
                return body

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        return R()

    result = check_self_update(urlopen_fn=fake_open)
    assert result["latest"] == "99.0.0"
    assert result["update_available"] is True
    assert result["offline"] is False


def test_check_self_update_offline(monkeypatch):
    import urllib.error

    def boom(_req, timeout=8):
        raise urllib.error.URLError("offline")

    result = check_self_update(urlopen_fn=boom)
    assert result["offline"] is True
    assert result["latest"] is None
    assert "error" in result


def test_build_update_report_shape():
    store = StateStore(autosave=False)
    store.set_hardware(Hardware(os_family="linux", ram_total_gb=8.0))
    store.upsert_component(
        Component(
            key="git",
            name="Git",
            category="dependency",
            state=ComponentState.NEEDS_UPDATE,
            health=Health.YELLOW,
            version="2.20.0",
        )
    )

    def fake_self():
        return {"current": "0.1.0", "latest": "0.1.0", "update_available": False, "offline": False}

    report = build_update_report(store, self_check_fn=fake_self)
    assert report["summary"]["component_updates"] == 1
    assert report["components"][0]["key"] == "git"
    assert "rollback" in report


def test_update_cli_json(capsys):
    from ai_loadout.cli import main

    rc = main(["--json", "update"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert "self" in payload and "components" in payload
