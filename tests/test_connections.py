"""Tests for connections pillar."""

from __future__ import annotations

from ai_loadout.connections.registry import build_connections_report


def test_connections_present_absent_no_secret_values():
    env = {"OPENAI_API_KEY": "sk-secret-value", "GITHUB_TOKEN": ""}
    report = build_connections_report(environ=env)
    assert report["total"] >= 5
    openai = next(c for c in report["connections"] if c["key"] == "openai")
    github = next(c for c in report["connections"] if c["key"] == "github")
    assert openai["present"] is True
    assert github["present"] is False
    blob = str(report)
    assert "sk-secret" not in blob
