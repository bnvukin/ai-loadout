"""Tests for proc.which PATH refresh and where.exe fallback."""

from ai_loadout.util import path_env, proc


def test_which_refreshes_path_on_windows(monkeypatch):
    called = {"n": 0}

    def fake_refresh(environ=None):
        called["n"] += 1
        return True

    monkeypatch.setattr(proc, "_is_windows", lambda: True)
    monkeypatch.setattr(path_env, "refresh_process_path", fake_refresh)
    monkeypatch.setattr(proc.shutil, "which", lambda name: "/bin/git")
    assert proc.which("git") == "/bin/git"
    assert called["n"] == 1


def test_which_falls_back_to_where_on_windows(monkeypatch):
    monkeypatch.setattr(proc, "_is_windows", lambda: True)
    monkeypatch.setattr(path_env, "refresh_process_path", lambda environ=None: False)
    monkeypatch.setattr(proc.shutil, "which", lambda name: None)
    monkeypatch.setattr(
        proc,
        "run",
        lambda cmd, **k: proc.RunResult(True, 0, "C:\\Tools\\pnpm.exe\n", "", found=True),
    )
    assert proc.which("pnpm") == r"C:\Tools\pnpm.exe"
