"""Tests for Layer 8 — agents / MCP."""

from __future__ import annotations

import json

from ai_loadout.agents.config import apply, preview


def test_agents_preview_shape(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(
        "ai_loadout.agents.config._mcp_path", lambda _h=None: home / ".cursor" / "mcp.json"
    )

    result = preview(home=home)
    assert result["ok"] is True
    assert "mcpServers" in result["merged_mcp"]
    assert "filesystem" in result["merged_mcp"]["mcpServers"]
    assert len(result["folders"]) >= 1
    # no hardcoded secrets
    assert "sk-" not in result["mcp_content"]


def test_agents_apply_creates_folders(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    mcp = home / ".cursor" / "mcp.json"
    monkeypatch.setattr("ai_loadout.agents.config._mcp_path", lambda _h=None: mcp)

    result = apply(home=home)
    assert result["ok"] is True
    assert mcp.is_file()
    data = json.loads(mcp.read_text(encoding="utf-8"))
    assert "mcpServers" in data
    assert (home / ".cursor" / "rules").is_dir()


def test_agents_cli_json(capsys):
    from ai_loadout.cli import main

    rc = main(["--json", "agents"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert "agents" in payload
