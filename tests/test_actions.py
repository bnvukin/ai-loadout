"""Tests for the Phase 2 action engine: command building, streaming runner, repairs."""

from __future__ import annotations

import importlib
import sys

import pytest

import ai_loadout.actions.advice as advice
import ai_loadout.actions.commands as commands
import ai_loadout.actions.runner as runner
from ai_loadout.actions.commands import ActionCommand
from ai_loadout.core.lifecycle import ComponentState, Health
from ai_loadout.core.models import Hardware
from ai_loadout.core.state import StateStore

# The package __init__ exports a `repair` *function*, which shadows the `repair`
# submodule via attribute traversal; load the module explicitly for monkeypatching.
repair = importlib.import_module("ai_loadout.actions.repair")


@pytest.fixture
def winget_env(monkeypatch):
    monkeypatch.setattr(commands, "available_managers", lambda *a, **k: ["winget"])
    monkeypatch.setattr(commands, "preferred_manager", lambda *a, **k: "winget")


def _store():
    store = StateStore(autosave=False)
    store.set_hardware(Hardware(os_family="windows", ram_total_gb=16.0))
    return store


# -- command building -------------------------------------------------------------------
def test_install_command_dependency(winget_env):
    cmd = commands.build_command("git", "dependency", "install", family="windows")
    assert cmd.ok and cmd.manager == "winget"
    assert cmd.display == (
        "winget install --id Git.Git -e --source winget "
        "--accept-package-agreements --accept-source-agreements"
    )
    assert cmd.needs_admin is True


def test_upgrade_command_dependency(winget_env):
    cmd = commands.build_command("git", "dependency", "upgrade", family="windows")
    assert cmd.ok and cmd.action == "upgrade"
    assert cmd.display.startswith("winget upgrade --id Git.Git")


def test_special_powershell_is_installable(winget_env):
    # PowerShell carries a winget id, so needs_update must be resolvable (not "manual").
    cmd = commands.build_command("powershell", "dependency", "upgrade", family="windows")
    assert cmd.ok
    assert "Microsoft.PowerShell" in cmd.display


def test_special_wsl_is_manual(winget_env):
    cmd = commands.build_command("wsl", "dependency", "install", family="windows")
    assert cmd.ok is False
    assert "manual" in cmd.reason.lower()


def test_unknown_dependency(winget_env):
    cmd = commands.build_command("does-not-exist", "dependency", "install", family="windows")
    assert cmd.ok is False


def test_model_pull_command(monkeypatch):
    monkeypatch.setattr(
        commands.shutil, "which", lambda n: "/usr/bin/ollama" if n == "ollama" else None
    )
    cmd = commands.build_command("llama3.2-3b", "model", "pull")
    assert cmd.ok and cmd.kind == "model"
    assert cmd.display == "ollama pull llama3.2:3b"
    assert cmd.argv == ["/usr/bin/ollama", "pull", "llama3.2:3b"]


def test_model_pull_requires_ollama(monkeypatch):
    monkeypatch.setattr(commands.shutil, "which", lambda n: None)
    cmd = commands.build_command("llama3.2-3b", "model", "pull")
    assert cmd.ok is False and "Ollama" in cmd.reason


# -- dry run / preview ------------------------------------------------------------------
def test_dry_run_does_not_execute(winget_env, monkeypatch):
    store = _store()
    called = {"n": 0}
    monkeypatch.setattr(runner, "_stream", lambda *a, **k: called.__setitem__("n", 1))
    result = runner.run_action(store, "git", "dependency", "install", dry_run=True)
    assert result["ran"] is False
    assert called["n"] == 0


def test_preview_returns_command(winget_env):
    result = runner.preview("git", "dependency", "install", family="windows")
    assert result["display"].startswith("winget install")


# -- streaming executor (hermetic, uses the current Python) -----------------------------
def test_stream_captures_output_and_logs(monkeypatch):
    from ai_loadout.core import paths

    store = _store()
    events = []
    store.bus.subscribe(lambda e: events.append(e))
    cmd = ActionCommand(
        key="probe",
        name="probe",
        kind="dependency",
        action="install",
        argv=[sys.executable, "-c", "print('line-one'); print('line-two')"],
        display="python probe",
    )
    code, tail = runner._stream(store, cmd, timeout=30)
    assert code == 0
    assert "line-one" in tail and "line-two" in tail
    progress = [e for e in events if e.kind == "progress"]
    assert any("line-one" in e.message for e in progress)
    assert paths.install_log().exists()
    assert "python probe" in paths.install_log().read_text(encoding="utf-8")


def test_run_action_success_updates_twin(winget_env, monkeypatch):
    store = _store()
    monkeypatch.setattr(runner, "_stream", lambda *a, **k: (0, ""))
    monkeypatch.setattr(
        runner,
        "rescan_component",
        lambda s, key: {"key": key, "state": "detected", "health": "green"},
    )
    result = runner.run_action(store, "git", "dependency", "install")
    assert result["success"] is True
    assert result["component"]["health"] == "green"


def test_run_action_failure_marks_failed(winget_env, monkeypatch):
    store = _store()
    monkeypatch.setattr(runner, "_stream", lambda *a, **k: (1, "boom"))
    result = runner.run_action(store, "git", "dependency", "install")
    assert result["success"] is False and result["error"] == "boom"
    comp = store.get_component("git")
    assert comp.state == ComponentState.FAILED and comp.health == Health.RED


def test_run_action_winget_already_installed_counts_as_success(winget_env, monkeypatch):
    store = _store()
    output = "Found an existing package already installed.\nNo available upgrade found."
    monkeypatch.setattr(runner, "_stream", lambda *a, **k: (2316632107, output))
    monkeypatch.setattr(
        runner,
        "rescan_component",
        lambda s, key: {"key": key, "state": "detected", "health": "green"},
    )
    result = runner.run_action(store, "pnpm", "dependency", "install")
    assert result["success"] is True
    assert result["exit_code"] == 0


def test_run_action_upgrade_falls_back_to_install(winget_env, monkeypatch):
    store = _store()
    calls = []

    def fake_stream(s, cmd, timeout=None):
        calls.append(cmd.action)
        if cmd.action == "upgrade":
            return 1, "No installed package found matching input criteria."
        return 0, "Successfully installed"

    monkeypatch.setattr(runner, "_stream", fake_stream)
    monkeypatch.setattr(
        runner,
        "rescan_component",
        lambda s, key: {"key": key, "state": "detected", "health": "green"},
    )
    result = runner.run_action(store, "powershell", "dependency", "upgrade")
    assert result["success"] is True
    assert calls == ["upgrade", "install"]


# -- rescan -----------------------------------------------------------------------------
def test_rescan_component_dependency(monkeypatch):
    store = _store()
    from ai_loadout.deps import detect as deps_detect

    def fake_detect_one(dep, family, *a, **k):
        return {
            "key": dep.key,
            "name": dep.name,
            "version": "2.99",
            "path": "/usr/bin/git",
            "decision": "skip",
            "state": ComponentState.DETECTED,
            "health": Health.GREEN,
            "detail": "installed",
            "actions": [],
            "optional": dep.optional,
        }

    monkeypatch.setattr(deps_detect, "detect_one", fake_detect_one)
    result = runner.rescan_component(store, "git")
    assert result["health"] == "green"
    assert store.get_component("git").version == "2.99"


def test_rescan_unknown_key_returns_none():
    store = _store()
    assert runner.rescan_component(store, "totally-unknown") is None


# -- repair -----------------------------------------------------------------------------
def test_repair_start_ollama_already_running(monkeypatch):
    store = _store()
    monkeypatch.setattr(repair.shutil, "which", lambda n: "/usr/bin/ollama")
    monkeypatch.setattr(repair.net, "port_open", lambda *a, **k: True)
    res = repair.repair(store, "start-ollama")
    assert res["ok"] is True and res.get("already") is True


def test_repair_start_ollama_missing(monkeypatch):
    store = _store()
    monkeypatch.setattr(repair.shutil, "which", lambda n: None)
    res = repair.repair(store, "start-ollama")
    assert res["ok"] is False


def test_repair_install_delegates(monkeypatch, winget_env):
    store = _store()
    monkeypatch.setattr(runner, "_stream", lambda *a, **k: (0, ""))
    monkeypatch.setattr(runner, "rescan_component", lambda s, key: {"key": key, "health": "green"})
    res = repair.repair(store, "install", target="git")
    assert res["ok"] is True and res["action"] == "install"


def test_repair_unknown_action():
    store = _store()
    res = repair.repair(store, "nonsense")
    assert res["ok"] is False


# -- advice -----------------------------------------------------------------------------
def test_advice_known_component():
    info = advice.component_advice("docker")
    assert info["impact"] and info["link"].startswith("http")
    assert info["optional"] is True


def test_advice_falls_back_to_note():
    info = advice.component_advice("git")
    assert info["impact"]
    assert info["optional"] is False
