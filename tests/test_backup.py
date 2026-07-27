"""Tests for Layer 17 — global backup / restore."""

from __future__ import annotations

import json

import pytest

from ai_loadout.backup.snapshot import (
    RESTORE_CONFIRM,
    RestoreError,
    create_snapshot,
    list_snapshots,
    restore_snapshot,
)
from ai_loadout.core import paths
from ai_loadout.core.models import Hardware
from ai_loadout.core.state import StateStore


def _store() -> StateStore:
    store = StateStore(autosave=False)
    store.set_hardware(Hardware(os_family="linux", ram_total_gb=8.0, cpu_name="Test"))
    return store


def test_create_list_restore_round_trip(loadout_home, tmp_path, monkeypatch):
    store = _store()
    fake_home = tmp_path / "userhome"
    fake_home.mkdir()
    cfg_dir = fake_home / ".continue"
    cfg_dir.mkdir()
    cfg_file = cfg_dir / "config.json"
    original = '{"models": [{"title": "local"}]}'
    cfg_file.write_text(original, encoding="utf-8")

    def fake_ph():
        return {
            "home": str(fake_home),
            "appdata": str(fake_home / "AppData" / "Roaming"),
            "localappdata": str(fake_home / "AppData" / "Local"),
            "xdg_config": str(fake_home / ".config"),
            "documents": str(fake_home / "Documents"),
        }

    monkeypatch.setattr("ai_loadout.config.discover._placeholders", fake_ph)

    created = create_snapshot(store)
    assert created["file_count"] >= 1
    snaps = list_snapshots()
    assert any(s["id"] == created["id"] for s in snaps)

    manifest_path = paths.backups_dir() / created["id"] / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["path"]["count"] >= 0
    assert any(e["name"] == "OPENAI_API_KEY" for e in manifest["env_keys"])

    cfg_file.write_text('{"models": [{"title": "changed"}]}', encoding="utf-8")

    with pytest.raises(RestoreError):
        restore_snapshot(created["id"])

    result = restore_snapshot(created["id"], confirm=RESTORE_CONFIRM)
    assert result["file_count"] >= 1
    assert cfg_file.read_text(encoding="utf-8") == original


def test_restore_requires_confirm_token(loadout_home):
    store = _store()
    created = create_snapshot(store)
    with pytest.raises(RestoreError, match="RESTORE"):
        restore_snapshot(created["id"], confirm="WRONG")


def test_backup_cli_list_and_create(capsys, loadout_home):
    from ai_loadout.cli import main

    rc = main(["backup"])
    assert rc == 0
    rc = main(["backup", "--list"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "snapshot" in out.lower() or "files" in out.lower()
