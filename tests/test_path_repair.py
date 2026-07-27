"""Tests for PATH dedupe repair."""

from __future__ import annotations

import os

from ai_loadout.config.path_repair import analyze_path_dedupe, dedupe_path_string


def test_dedupe_preserves_order_cross_platform():
    sep = os.pathsep
    raw = sep.join([r"C:\bin", r"C:\tools", r"c:\bin", r"D:\x"])
    out = dedupe_path_string(raw, case_insensitive=True)
    parts = out.split(sep)
    assert parts[0].lower() == r"c:\bin"
    assert parts[1].lower() == r"c:\tools"
    assert len(parts) == 3


def test_analyze_path_dedupe_detects_duplicates():
    sep = os.pathsep
    env = {"PATH": sep.join(["/usr/bin", "/usr/bin", "/opt/bin"])}
    analysis = analyze_path_dedupe(env)
    assert analysis["changed"] is True
    assert analysis["removed"] == 1


def test_apply_path_dedupe_dry_run():
    from ai_loadout.config.path_repair import apply_path_dedupe

    sep = os.pathsep
    env = {"PATH": sep.join(["/a", "/a", "/b"])}
    result = apply_path_dedupe(dry_run=True, environ=env)
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["analysis"]["changed"] is True
