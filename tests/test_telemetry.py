"""Tests for Layer 20 — opt-in telemetry."""

from __future__ import annotations

import json

import pytest

from ai_loadout.core.settings import reset_settings_cache, save_settings
from ai_loadout.telemetry.collector import list_events, preview_payload, record_event, status


@pytest.fixture
def telemetry_home(tmp_path, monkeypatch):
    monkeypatch.setenv("LOADOUT_HOME", str(tmp_path))
    reset_settings_cache()
    save_settings({"telemetry_enabled": False})
    yield tmp_path
    reset_settings_cache()


def test_default_disabled_no_events(telemetry_home):
    assert status()["enabled"] is False
    assert record_event("scan_complete", layer="scan") is None
    assert list_events() == []


def test_enabled_records_whitelisted_fields_only(telemetry_home):
    save_settings({"telemetry_enabled": True})
    reset_settings_cache()
    payload = record_event("layer_used", layer="offline", count=1)
    assert payload is not None
    assert "path" not in payload
    assert "hostname" not in payload
    assert payload["event"] == "layer_used"
    assert payload["layer"] == "offline"

    raw = (telemetry_home / "telemetry" / "events.jsonl").read_text(encoding="utf-8")
    assert "C:\\Users" not in raw
    assert "sk-" not in raw


def test_disable_stops_collection(telemetry_home):
    save_settings({"telemetry_enabled": True})
    reset_settings_cache()
    record_event("a")
    save_settings({"telemetry_enabled": False})
    reset_settings_cache()
    assert record_event("b") is None
    events = list_events()
    assert len(events) == 1


def test_preview_payload_no_secrets(telemetry_home):
    preview = preview_payload()
    assert preview["transmission"] is False
    sample = json.dumps(preview.get("sample", {}))
    assert "api_key" not in sample.lower()
    assert "password" not in sample.lower()
