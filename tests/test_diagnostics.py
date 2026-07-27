"""Tests for Layer 15 — diagnostics bundles."""

from __future__ import annotations

import json
import zipfile

from ai_loadout.config.redact import mask
from ai_loadout.core import paths
from ai_loadout.core.models import Hardware
from ai_loadout.core.state import StateStore
from ai_loadout.diagnostics.bundle import create_diagnostics_bundle
from ai_loadout.diagnostics.system import write_system_snapshot


def _store() -> StateStore:
    store = StateStore(autosave=False)
    store.set_hardware(Hardware(os_family="linux", ram_total_gb=8.0, cpu_name="Test"))
    return store


def test_system_snapshot_written(loadout_home):
    store = _store()
    dest = write_system_snapshot(store)
    assert dest == paths.system_log()
    payload = json.loads(dest.read_text(encoding="utf-8"))
    assert payload["schema"] == 1
    assert payload["hardware"]["cpu_name"] == "Test"
    assert "env" in payload


def test_diagnostics_bundle_members_and_redaction(loadout_home, monkeypatch):
    store = _store()
    paths.ensure_dirs()
    paths.install_log().write_text(
        "OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456\nplain line\n",
        encoding="utf-8",
    )
    store.save()

    monkeypatch.setenv("OPENAI_API_KEY", "sk-abcdefghijklmnopqrstuvwxyz123456")
    result = create_diagnostics_bundle(store)
    zip_path = paths.diagnostics_dir() / result["filename"]
    assert zip_path.is_file()
    assert {"state.json", "system.json", "install.log", "versions.json"} <= set(result["members"])

    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        assert "system.json" in names
        system = json.loads(archive.read("system.json"))
        for row in system["env"]:
            if row["name"] == "OPENAI_API_KEY" and row["present"]:
                assert row["value"] == mask("sk-abcdefghijklmnopqrstuvwxyz123456")
        log_text = archive.read("install.log").decode("utf-8")
        assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in log_text
        assert "***redacted***" in log_text or "OPENAI_API_KEY" in log_text


def test_diagnostics_cli_json(capsys, loadout_home):
    from ai_loadout.cli import main

    rc = main(["--json", "diagnostics"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["members"]
    assert payload["path"].endswith(".zip")
