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
    env = {
        "PATH": r"C:\Windows\System32",
        "USERPROFILE": r"C:\Users\me",
        "LOCALAPPDATA": r"C:\Users\me\AppData\Local",
    }
    assert path_env.refresh_process_path(env) is True
    parts = env["PATH"].split(os.pathsep)
    assert r"C:\Program Files\System" in parts
    assert r"C:\Users\me\AppData\Local\pnpm" in parts


def test_refresh_finds_tools_after_stale_unexpanded_path(monkeypatch):
    import shutil

    monkeypatch.setattr(path_env.sys, "platform", "win32")
    monkeypatch.setattr(path_env.os, "name", "nt")
    winget_pnpm = (
        r"C:\Users\me\AppData\Local\Microsoft\WinGet\Packages"
        r"\pnpm.pnpm_Microsoft.Winget.Source_8wekyb3d8bbwe"
    )

    def fake_read(root, subkey):
        if "Session Manager" in subkey:
            return r"C:\Windows\System32"
        return winget_pnpm

    monkeypatch.setattr(path_env, "_read_reg_path", fake_read)

    env = {
        "PATH": r"C:\Windows\System32;%USERPROFILE%\AppData\Local\Microsoft\WindowsApps",
        "USERPROFILE": r"C:\Users\me",
        "LOCALAPPDATA": r"C:\Users\me\AppData\Local",
        "PATHEXT": ".EXE;.CMD;.BAT;.COM",
    }
    assert shutil.which("pnpm", path=env["PATH"]) is None
    assert path_env.refresh_process_path(env) is True
    assert winget_pnpm.lower() in env["PATH"].lower()


def test_detect_one_refreshes_path_on_windows(monkeypatch):
    from ai_loadout.deps import detect
    from ai_loadout.deps.registry import by_key

    called = {"n": 0}

    def fake_refresh():
        called["n"] += 1
        return False

    monkeypatch.setattr("ai_loadout.util.path_env.refresh_process_path", fake_refresh)
    monkeypatch.setattr(detect, "available_managers", lambda *a, **k: [])
    detect.detect_one(
        by_key("git"), "windows", which_fn=lambda n: None, run_fn=lambda *a, **k: None
    )
    assert called["n"] >= 1
