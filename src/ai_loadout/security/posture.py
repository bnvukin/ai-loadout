"""Trust posture report — how each installable component is sourced and verified."""

from __future__ import annotations

from ..deps.managers import preferred_manager
from ..deps.registry import DEPENDENCIES
from ..detect.system import os_family
from ..runtimes.registry import RUNTIMES
from .sources import PACKAGE_MANAGERS


def _install_methods(spec, family: str, manager: str | None) -> tuple[str, str | None, str]:
    """Return (method, manager, verification_note) for one registry entry."""

    if getattr(spec, "special", None) in ("wsl", "cuda", "vsbuildtools"):
        return "manual", None, "Requires manual/vendor installer guidance"
    for mgr in PACKAGE_MANAGERS:
        install_id = (
            spec.install_id(mgr) if hasattr(spec, "install_id") else getattr(spec, mgr, None)
        )
        if install_id and (manager is None or mgr == manager):
            if mgr in ("winget", "choco", "brew", "apt", "dnf", "pacman", "scoop"):
                return (
                    "package_manager",
                    mgr,
                    f"{mgr} verifies publisher signatures / package hashes",
                )
            if mgr == "npm":
                return "package_manager", "npm", "npm registry + package integrity metadata"
            if mgr == "pip":
                return (
                    "package_manager",
                    "pip",
                    "PyPI host verification; pip hash check when pinned",
                )
    if manager:
        install_id = spec.install_id(manager) if hasattr(spec, "install_id") else None
        if install_id:
            return "package_manager", manager, f"{manager} verifies package integrity"
    return "detect_only", None, "Detection only — no automated install path yet"


def _component_posture(
    key: str, name: str, category: str, spec, family: str, manager: str | None
) -> dict:
    method, via, note = _install_methods(spec, family, manager)
    install_ids = {}
    for mgr in PACKAGE_MANAGERS:
        iid = spec.install_id(mgr) if hasattr(spec, "install_id") else getattr(spec, mgr, None)
        if iid:
            install_ids[mgr] = iid
    return {
        "key": key,
        "name": name,
        "category": category,
        "method": method,
        "manager": via,
        "install_ids": install_ids,
        "integrity": note,
        "official_source": method == "package_manager" or method == "detect_only",
    }


def build_trust_posture(store=None) -> dict:
    """Summarise integrity posture for every installable dependency and runtime."""

    family = os_family()
    if store is not None and store.hardware and store.hardware.os_family:
        family = store.hardware.os_family
    manager = preferred_manager(family)

    components: list[dict] = []
    for dep in DEPENDENCIES:
        if not dep.applies_to(family):
            continue
        components.append(_component_posture(dep.key, dep.name, "dependency", dep, family, manager))
    for rt in RUNTIMES:
        if not rt.applies_to(family):
            continue
        components.append(_component_posture(rt.key, rt.name, "runtime", rt, family, manager))

    via_pm = sum(1 for c in components if c["method"] == "package_manager")
    manual = sum(1 for c in components if c["method"] == "manual")
    detect = sum(1 for c in components if c["method"] == "detect_only")

    return {
        "platform": family,
        "preferred_manager": manager,
        "summary": {
            "total": len(components),
            "package_manager": via_pm,
            "manual": manual,
            "detect_only": detect,
            "direct_download": 0,
        },
        "policy": {
            "url_allowlist": True,
            "sha256_for_direct_downloads": True,
            "package_managers_delegate_verification": True,
        },
        "components": components,
    }
