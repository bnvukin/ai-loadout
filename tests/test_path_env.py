"""Tests for Windows PATH refresh from the registry."""

import os
import sys

import pytest

from ai_loadout.util import path_env

# The registry read and ``%VAR%`` expansion are genuinely Windows-only (posix
# ``os.pathsep`` is ``:``, which also splits drive letters like ``C:\...``, and
# ``os.path.expandvars`` only expands ``%VAR%`` on Windows). The Windows CI leg
# exercises these; elsewhere ``refresh_process_path`` is a no-op anyway.
windows_only = pytest.mark.skipif(
    sys.platform != "win32", reason="exercises Windows-only registry PATH behavior"
)


def test_refresh_process_path_noop_on_non_windows(monkeypatch):
    # Route the platform check through the helper -- never mutate the global ``os.name``,
    # which would corrupt shutil/pathlib for the rest of the suite (and crash pytest 3.9).
    monkeypatch.setattr(path_env, "_is_windows", lambda: False)
    env = {"PATH": "/usr/bin"}
    assert path_env.refresh_process_path(env) is False
    assert env["PATH"] == "/usr/bin"


def test_merge_path_dedupes_case_insensitive():
    # Pure dedup logic -- separator-free segments so it holds on any os.pathsep.
    sep = os.pathsep
    primary = sep.join([r"\Tools", r"\bin"])
    secondary = sep.join([r"\tools", r"\new"])
    merged = path_env._merge_path(primary, secondary, case_insensitive=True)
    entries = [e.lower() for e in merged.split(sep)]
    assert entries.count(r"\tools") == 1
    assert r"\new" in entries


@windows_only
def test_refresh_process_path_appends_registry_entries(monkeypatch):
    monkeypatch.setattr(path_env, "_is_windows", lambda: True)

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


@windows_only
def test_refresh_finds_tools_after_stale_unexpanded_path(monkeypatch):
    monkeypatch.setattr(path_env, "_is_windows", lambda: True)
    winget_pnpm = (
        r"C:\Users\me\AppData\Local\Microsoft\WinGet\Packages"
        r"\pnpm.pnpm_Microsoft.Winget.Source_8wekyb3d8bbwe"
    )

    def fake_read(root, subkey):
        if "Session Manager" in subkey:
            return r"C:\Windows\System32"
        return winget_pnpm

    monkeypatch.setattr(path_env, "_read_reg_path", fake_read)

    # A stale, unexpanded PATH (literal %USERPROFILE%) never resolves the winget tool.
    sep = os.pathsep
    env = {
        "PATH": sep.join([r"C:\Windows\System32", r"%USERPROFILE%\AppData\Local\pnpm"]),
        "USERPROFILE": r"C:\Users\me",
        "LOCALAPPDATA": r"C:\Users\me\AppData\Local",
    }
    assert winget_pnpm.lower() not in env["PATH"].lower()
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
