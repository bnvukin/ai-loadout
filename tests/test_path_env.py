"""Tests for Windows PATH refresh from the registry."""

import os

from ai_loadout.util import path_env


def test_refresh_process_path_noop_on_non_windows(monkeypatch):
    monkeypatch.setattr(path_env.sys, "platform", "linux")
    monkeypatch.setattr(path_env.os, "name", "posix")
    env = {"PATH": "/usr/bin"}
    assert path_env.refresh_process_path(env) is False
    assert env["PATH"] == "/usr/bin"


def test_merge_path_dedupes_case_insensitive_on_windows():
    merged = path_env._merge_path(r"C:\Tools;A:\bin", r"c:\tools;B:\new")
    assert merged.lower().count("c:\\tools") == 1
    assert "B:\\new" in merged or "b:\\new" in merged.lower()


def test_refresh_process_path_appends_registry_entries(monkeypatch):
    monkeypatch.setattr(path_env.sys, "platform", "win32")
    monkeypatch.setattr(path_env.os, "name", "nt")

    def fake_read(root, subkey):
        if "Session Manager" in subkey:
            return r"C:\Program Files\System"
        return r"C:\Users\me\AppData\Local\pnpm"

    monkeypatch.setattr(path_env, "_read_reg_path", fake_read)
    env = {"PATH": r"C:\Windows\System32"}
    assert path_env.refresh_process_path(env) is True
    parts = env["PATH"].split(os.pathsep)
    assert r"C:\Windows\System32" in parts
    assert r"C:\Program Files\System" in parts
    assert r"C:\Users\me\AppData\Local\pnpm" in parts
