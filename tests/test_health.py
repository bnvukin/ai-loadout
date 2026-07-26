from ai_loadout.core.lifecycle import Category, ComponentState
from ai_loadout.core.models import Component, Hardware
from ai_loadout.core.state import StateStore
from ai_loadout.health.checker import check
from ai_loadout.health.doctor import explain
from ai_loadout.util.proc import RunResult


def _store_with(hw=None, components=()):
    store = StateStore(autosave=False)
    if hw is not None:
        store.set_hardware(hw)
    for c in components:
        store.upsert_component(c)
    return store


def test_explain_renders_context():
    exp = explain("update-available", {"name": "Python", "version": "3.8.0", "min_version": "3.9"})
    assert "Python" in exp["title"]
    assert "3.8.0" in exp["explanation"]
    assert exp["fixable"] is True


def test_explain_unknown_key_is_safe():
    exp = explain("does-not-exist", {"title": "Custom"})
    assert exp["title"] == "Custom"
    assert exp["fixable"] is False


def test_ollama_not_running_flagged():
    store = _store_with(
        components=[
            Component(
                key="ollama",
                name="Ollama",
                category=Category.RUNTIME,
                state=ComponentState.DETECTED,
            )
        ]
    )
    report = check(store, port_open=lambda *a, **k: False)
    keys = {i.key for i in report.issues}
    assert "ollama-not-running" in keys
    issue = next(i for i in report.issues if i.key == "ollama-not-running")
    assert issue.fixable and issue.fix_action == "start-ollama"


def test_ollama_running_not_flagged():
    store = _store_with(
        components=[
            Component(
                key="ollama",
                name="Ollama",
                category=Category.RUNTIME,
                state=ComponentState.DETECTED,
            )
        ]
    )
    report = check(store, port_open=lambda *a, **k: True)
    assert "ollama-not-running" not in {i.key for i in report.issues}


def test_low_disk_and_offline_and_cpu_only():
    hw = Hardware(os_family="windows", ram_total_gb=16.0, primary_disk_free_gb=3.0, internet=False)
    store = _store_with(hw=hw)
    report = check(store, port_open=lambda *a, **k: True)
    keys = {i.key for i in report.issues}
    assert "disk-low" in keys
    assert "offline" in keys
    assert "cpu-only" in keys
    disk = next(i for i in report.issues if i.key == "disk-low")
    assert disk.severity == "error"  # < 5 GB


def test_update_available_issue_from_needs_update_component():
    store = _store_with(
        components=[
            Component(
                key="python", name="Python", state=ComponentState.NEEDS_UPDATE, version="3.8.0"
            )
        ]
    )
    report = check(store, port_open=lambda *a, **k: True)
    upd = [i for i in report.issues if i.key == "update-available"]
    assert upd and upd[0].fix_action == "update"


def test_docker_daemon_down_flagged():
    store = _store_with(
        components=[
            Component(
                key="docker",
                name="Docker",
                category=Category.RUNTIME,
                state=ComponentState.DETECTED,
                path="/usr/bin/docker",
            )
        ]
    )
    report = check(
        store,
        port_open=lambda *a, **k: True,
        run_fn=lambda *a, **k: RunResult(False, 1, "", "Cannot connect to the Docker daemon"),
    )
    assert "docker-not-running" in {i.key for i in report.issues}
