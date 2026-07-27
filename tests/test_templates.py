"""Tests for Layer 9 — project templates."""

from __future__ import annotations

from ai_loadout.templates.registry import list_templates, preview_template, scaffold_template


def test_list_templates():
    items = list_templates()
    assert len(items) >= 5
    keys = {t["key"] for t in items}
    assert "fastapi" in keys
    assert "mcp-server" in keys


def test_preview_file_set():
    prev = preview_template("fastapi", "Demo API")
    assert prev["ok"] is True
    assert prev["file_count"] >= 2
    paths = {f["path"] for f in prev["files"]}
    assert "main.py" in paths


def test_scaffold_into_empty_dir(tmp_path):
    target = tmp_path / "demo-api"
    result = scaffold_template("fastapi", "Demo API", target)
    assert result["ok"] is True
    assert (target / "main.py").is_file()
    assert "Demo API" in (target / "README.md").read_text(encoding="utf-8")


def test_scaffold_refuses_nonempty(tmp_path):
    target = tmp_path / "busy"
    target.mkdir()
    (target / "existing.txt").write_text("x", encoding="utf-8")
    result = scaffold_template("fastapi", "X", target)
    assert result["ok"] is False
    assert "force" in (result.get("reason") or "").lower()


def test_scaffold_force_overwrites(tmp_path):
    target = tmp_path / "busy"
    target.mkdir()
    (target / "main.py").write_text("old", encoding="utf-8")
    result = scaffold_template("fastapi", "Y", target, force=True)
    assert result["ok"] is True
    assert "FastAPI" in (target / "main.py").read_text(encoding="utf-8")


def test_new_cli_list(capsys):
    from ai_loadout.cli import main

    rc = main(["new", "--list"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "fastapi" in out.lower() or "FastAPI" in out
