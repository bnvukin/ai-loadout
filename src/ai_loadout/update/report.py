"""Unified update report: Loadout self-update + component upgrades."""

from __future__ import annotations

from ..core.lifecycle import ComponentState, Health
from ..deps.registry import by_key as dep_by_key
from .self_check import check_self_update


def _component_entry(comp) -> dict:
    dep = dep_by_key(comp.key)
    minimum = dep.min_version if dep else None
    return {
        "key": comp.key,
        "name": comp.name,
        "category": comp.category,
        "current": comp.version,
        "minimum": minimum,
        "state": str(comp.state),
        "health": str(comp.health),
        "action": "upgrade",
    }


def build_update_report(store, *, self_check_fn=None) -> dict:
    """Return self-update status and components that need an upgrade."""

    self_info = check_self_update() if self_check_fn is None else self_check_fn()

    upgrades = []
    for comp in store.components():
        if comp.state == ComponentState.NEEDS_UPDATE:
            upgrades.append(_component_entry(comp))
            continue
        if comp.health == Health.YELLOW and comp.state != ComponentState.MISSING:
            upgrades.append(_component_entry(comp))

    return {
        "self": self_info,
        "components": upgrades,
        "summary": {
            "self_update": self_info.get("update_available", False),
            "component_updates": len(upgrades),
        },
        "rollback": {
            "loadout": self_info.get("rollback_hint"),
            "config_per_file": "Copy a `.bak` from ~/.ai-loadout/backups/ over the original",
            "config_snapshot": "Dashboard → Config Center → Restore (type RESTORE)",
        },
    }
