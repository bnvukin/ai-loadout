"""Detect installed dependencies and decide what to do about each one.

The ``which_fn`` / ``run_fn`` parameters are injectable so the decision logic can be
unit-tested with simulated tool output (no real tools required).
"""

from __future__ import annotations

import os

from ..core.lifecycle import Category, ComponentState, Health
from ..core.models import Component
from ..util import proc
from .managers import available_managers, preferred_manager
from .registry import Dependency, platform_dependencies
from .version import extract_version, is_older

# decision -> (state, health)
_DECISIONS = {
    "skip": (ComponentState.DETECTED, Health.GREEN),  # present & recent enough
    "upgrade": (ComponentState.NEEDS_UPDATE, Health.YELLOW),
    "install": (ComponentState.MISSING, Health.GRAY),
    "manual": (ComponentState.MISSING, Health.GRAY),  # missing & no known installer
}


def _probe_version(dep: Dependency, exe: str, run_fn) -> str | None:
    result = run_fn([exe, *dep.version_args], timeout=12)
    if not result.found:
        return None
    return extract_version(result.text)


def _detect_generic(dep: Dependency, which_fn, run_fn) -> tuple[str | None, str | None]:
    """Return (path, version) using ``which`` + a version probe."""

    exe = which_fn(dep.probe_command())
    if not exe:
        return None, None
    return exe, _probe_version(dep, exe, run_fn)


def _detect_powershell(which_fn, run_fn) -> tuple[str | None, str | None]:
    for exe_name in ("pwsh", "powershell"):
        exe = which_fn(exe_name)
        if not exe:
            continue
        result = run_fn(
            [
                exe,
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "$PSVersionTable.PSVersion.ToString()",
            ],
            timeout=15,
        )
        if result.found:
            return exe, extract_version(result.text)
    return None, None


def _detect_wsl(which_fn) -> tuple[str | None, str | None]:
    # wsl.exe emits UTF-16, so we avoid parsing its version and just record presence.
    exe = which_fn("wsl")
    return (exe, None) if exe else (None, None)


def _detect_cuda(which_fn, run_fn, hardware) -> tuple[str | None, str | None]:
    exe, version = _detect_generic_named("nvcc", ("--version",), which_fn, run_fn)
    if exe:
        return exe, version
    # Fall back to the CUDA version nvidia-smi reports (driver-level runtime).
    if hardware is not None:
        for gpu in hardware.gpus:
            if gpu.cuda:
                return "nvidia-smi", gpu.cuda
    return None, None


def _detect_generic_named(name, version_args, which_fn, run_fn):
    exe = which_fn(name)
    if not exe:
        return None, None
    result = run_fn([exe, *version_args], timeout=12)
    return exe, (extract_version(result.text) if result.found else None)


def _detect_vsbuildtools(run_fn) -> tuple[str | None, str | None]:
    program_files = os.environ.get("ProgramFiles(x86)") or os.environ.get("ProgramFiles", "")
    if not program_files:
        return None, None
    vswhere = os.path.join(program_files, "Microsoft Visual Studio", "Installer", "vswhere.exe")
    if not os.path.exists(vswhere):
        return None, None
    result = run_fn(
        [
            vswhere,
            "-products",
            "*",
            "-requires",
            "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "-property",
            "catalog_productDisplayVersion",
        ],
        timeout=15,
    )
    if result.found and result.out.strip():
        return vswhere, extract_version(result.out)
    return None, None


def _decide(dep: Dependency, path: str | None, version: str | None, managers: list[str]) -> str:
    if path is None:
        # Missing. Can we install it?
        can_install = any(dep.install_id(m) for m in managers) or dep.special in {"wsl"}
        return "install" if can_install else "manual"
    if dep.min_version and is_older(version, dep.min_version):
        return "upgrade"
    return "skip"


def detect_one(
    dep: Dependency,
    family: str,
    managers: list[str] | None = None,
    hardware=None,
    which_fn=proc.which,
    run_fn=proc.run,
) -> dict:
    """Detect a single dependency and return a result dict (no state mutation)."""

    from ..util.path_env import refresh_process_path

    refresh_process_path()
    managers = managers if managers is not None else available_managers(which_fn)

    if dep.special == "powershell":
        path, version = _detect_powershell(which_fn, run_fn)
    elif dep.special == "wsl":
        path, version = _detect_wsl(which_fn)
    elif dep.special == "cuda":
        path, version = _detect_cuda(which_fn, run_fn, hardware)
    elif dep.special == "vsbuildtools":
        path, version = _detect_vsbuildtools(run_fn)
    else:
        path, version = _detect_generic(dep, which_fn, run_fn)

    decision = _decide(dep, path, version, managers)
    state, health = _DECISIONS[decision]

    # Optional-but-missing tools shouldn't drag health down (stay gray, not red).
    detail = ""
    if decision == "skip":
        detail = "installed"
    elif decision == "upgrade":
        detail = f"update available (>= {dep.min_version} recommended)"
    elif decision == "install":
        mgr = next((m for m in managers if dep.install_id(m)), None) or preferred_manager(
            family, which_fn
        )
        detail = f"not installed (installable via {mgr})" if mgr else "not installed"
    else:
        detail = "not installed (manual setup)" if dep.special != "wsl" else "not installed"

    actions = []
    if decision == "install":
        actions = ["install"]
    elif decision == "upgrade":
        actions = ["update"]

    return {
        "key": dep.key,
        "name": dep.name,
        "version": version,
        "path": path,
        "decision": decision,
        "state": state,
        "health": health,
        "detail": detail,
        "actions": actions,
        "optional": dep.optional,
    }


def detect_all(store, which_fn=proc.which, run_fn=proc.run) -> list[dict]:
    """Detect every applicable dependency and write components into the digital twin."""

    from ..util.path_env import refresh_process_path

    refresh_process_path()
    family = store.hardware.os_family if store.hardware else _current_family()
    hardware = store.hardware
    managers = available_managers(which_fn)
    store.bus.info(
        f"Checking dependencies (managers: {', '.join(managers) or 'none'})", source="deps"
    )

    results = []
    for dep in platform_dependencies(family):
        result = detect_one(dep, family, managers, hardware, which_fn, run_fn)
        results.append(result)
        store.upsert_component(
            Component(
                key=dep.key,
                name=dep.name,
                category=Category.DEPENDENCY,
                state=result["state"],
                health=result["health"],
                version=result["version"],
                path=result["path"],
                detail=result["detail"],
                actions=result["actions"],
                optional=dep.optional,
            )
        )
    installed = sum(1 for r in results if r["decision"] in ("skip", "upgrade"))
    store.bus.success(f"Dependency check complete: {installed} present", source="deps")
    return results


def _current_family() -> str:
    from ..detect.system import os_family

    return os_family()
