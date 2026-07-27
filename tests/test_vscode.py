"""Tests for Layer 6 — VS Code configuration."""

from __future__ import annotations

import json

from ai_loadout.config.merge import merge_fill_gaps
from ai_loadout.vscode.extensions import RECOMMENDED_EXTENSIONS, extension_install_command
from ai_loadout.vscode.settings import RECOMMENDED_SETTINGS


def test_merge_settings_preserves_user_keys():
    existing = {"editor.tabSize": 4, "my.custom": True}
    merged = merge_fill_gaps(existing, RECOMMENDED_SETTINGS)
    assert merged["editor.tabSize"] == 4
    assert merged["my.custom"] is True
    assert merged["editor.formatOnSave"] is True


def test_extension_install_command_argv():
    cmd = extension_install_command("Continue.continue", code_exe="/usr/bin/code")
    assert cmd["ok"] is True
    assert "Continue.continue" in cmd["argv"]
    assert cmd["display"].startswith("/usr/bin/code")


def test_extension_install_command_no_code():
    extension_install_command("x.y", code_exe=None)
    cmd2 = extension_install_command("x.y", code_exe="/nonexistent/code")
    assert cmd2["ok"] is True
    assert cmd2["argv"][0] == "/nonexistent/code"


def test_vscode_preview_and_apply(tmp_path, monkeypatch):
    home = tmp_path / "home"
    user = home / "AppData" / "Roaming" / "Code" / "User"
    user.mkdir(parents=True)
    settings = user / "settings.json"
    settings.write_text('{"editor.tabSize": 4}\n', encoding="utf-8")

    def fake_ph():
        return {
            "home": str(home),
            "appdata": str(home / "AppData" / "Roaming"),
            "localappdata": str(home / "AppData" / "Local"),
            "xdg_config": str(home / ".config"),
            "documents": str(home / "Documents"),
        }

    monkeypatch.setattr("ai_loadout.vscode.paths._placeholders", fake_ph)
    from ai_loadout.vscode.config import apply, preview

    monkeypatch.setattr(
        "ai_loadout.vscode.config.settings_path", lambda editor="vscode", family=None: settings
    )
    monkeypatch.setattr(
        "ai_loadout.vscode.config.user_dir", lambda editor="vscode", family=None: user
    )
    monkeypatch.setattr("ai_loadout.vscode.config.detect_editor", lambda _s=None: "vscode")

    prev = preview(editor="vscode")
    assert prev["ok"] is True
    assert prev["exists"] is True
    assert "editor.formatOnSave" in prev["merged_settings"]

    result = apply(editor="vscode")
    assert result["ok"] is True
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert data["editor.tabSize"] == 4
    assert data["editor.formatOnSave"] is True


def test_vscode_cli_preview(capsys):
    from ai_loadout.cli import main

    rc = main(["--json", "vscode"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload.get("ok") is True
    assert len(payload.get("extensions", [])) == len(RECOMMENDED_EXTENSIONS)
