"""Tests for profile batch install pillar."""

from __future__ import annotations

from ai_loadout.core.lifecycle import ComponentState, Health
from ai_loadout.core.models import Component, Hardware
from ai_loadout.core.state import StateStore
from ai_loadout.plan.planner import build_plan
from ai_loadout.plan.profile_install import profile_plan, run_profile_install


def _store() -> StateStore:
    store = StateStore(autosave=False)
    store.set_hardware(Hardware(os_family="linux", ram_total_gb=16.0))
    store.upsert_component(
        Component(
            key="git",
            name="Git",
            category="dependency",
            state=ComponentState.DETECTED,
            health=Health.GREEN,
            version="2.40",
        )
    )
    return store


def test_profile_plan_generation():
    plan = profile_plan(_store(), "minimal")
    assert plan["profile"] == "minimal"
    assert any(s["key"] == "git" and s["action"] == "skip" for s in plan["steps"])


def test_profile_install_dry_run():
    result = run_profile_install(_store(), "minimal", dry_run=True)
    assert result["dry_run"] is True
    assert result["steps"]


def test_profile_install_blocked_offline(monkeypatch):
    monkeypatch.setattr(
        "ai_loadout.plan.profile_install.offline_block",
        lambda action: {"ok": False, "offline": True, "reason": "offline"},
    )
    store = _store()
    # Force an install step by marking python missing
    store.upsert_component(
        Component(
            key="python",
            name="Python",
            category="dependency",
            state=ComponentState.MISSING,
            health=Health.RED,
        )
    )
    plan = build_plan(store, "minimal")
    assert any(s.action == "install" for s in plan.steps)
    result = run_profile_install(store, "minimal", dry_run=False)
    assert result["blocked_offline"] is True
