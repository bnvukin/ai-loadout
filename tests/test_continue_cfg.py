"""Tests for Layer 7 — Continue configuration."""

from __future__ import annotations

import json

from ai_loadout.continue_cfg.builder import CONTINUE_SCHEMA, build_config_dict, preview
from ai_loadout.core.models import Hardware, ModelEntry
from ai_loadout.core.state import StateStore


def test_build_config_no_secret_literals():
    store = StateStore(autosave=False)
    store.set_hardware(Hardware(os_family="linux", ram_total_gb=8.0))
    cfg = build_config_dict(store)
    raw = json.dumps(cfg)
    assert "sk-" not in raw
    assert "apiKey" not in raw or "${env:" in raw


def test_preview_from_mocked_models(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    cont = home / ".continue"
    cont.mkdir()
    existing = cont / "config.yaml"
    existing.write_text("name: My Custom\nmodels: []\n", encoding="utf-8")

    monkeypatch.setattr(
        "ai_loadout.continue_cfg.builder._continue_config_path", lambda _h=None: existing
    )

    store = StateStore(autosave=False)
    store.upsert_model(ModelEntry(name="llama3.2", provider="ollama", size_gb=2.0))

    result = preview(store, home=home)
    assert result["ok"] is True
    assert result["schema"] == CONTINUE_SCHEMA
    assert "llama3.2" in result["content"]
    assert "sk-" not in result["content"]


def test_continue_cli_json(capsys):
    from ai_loadout.cli import main

    rc = main(["--json", "continue"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["schema"] == "v1"
