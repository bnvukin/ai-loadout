"""Detect AI runtimes / editors / agent CLIs and write them into the digital twin.

Detection order per runtime: a CLI on PATH (+ version) > a running local port > a config
directory under the user's home. ``which_fn`` / ``run_fn`` / ``home`` are injectable so the
logic is unit-testable without the tools installed.
"""

from __future__ import annotations

from pathlib import Path

from ..core.lifecycle import Category, ComponentState, Health
from ..core.models import Component, ModelEntry
from ..deps.version import extract_version
from ..util import net, proc
from .parsers import parse_code_version, parse_ollama_list
from .registry import Runtime, platform_runtimes

_CATEGORY = {
    "runtime": Category.RUNTIME,
    "editor": Category.EDITOR,
    "connection": Category.CONNECTION,
}


def _installable(runtime: Runtime, managers) -> bool:
    for m in ("winget", "choco", "brew", "npm", "pip"):
        if runtime.install_id(m) and (m in managers or m in ("npm", "pip")):
            return True
    return False


def detect_one(
    runtime: Runtime,
    managers: list[str] | None = None,
    which_fn=proc.which,
    run_fn=proc.run,
    home: Path | None = None,
) -> dict:
    managers = managers or []
    home = home or Path.home()
    path = None
    version = None
    running = False
    models: list[dict] = []
    detail = ""

    if runtime.special == "ollama":
        path = which_fn("ollama")
        if path:
            res = run_fn([path, *runtime.version_args], timeout=6)
            version = extract_version(res.text) if res.found else None
            listing = run_fn([path, "list"], timeout=8)
            if listing.ok:
                models = parse_ollama_list(listing.out)
        running = net.port_open("127.0.0.1", runtime.port) if runtime.port else False
    elif runtime.special == "vscode":
        path = which_fn("code")
        if path:
            res = run_fn([path, "--version"], timeout=10)
            version = parse_code_version(res.text) if res.found else None
    else:
        if runtime.command:
            path = which_fn(runtime.command)
            if path:
                res = run_fn([path, *runtime.version_args], timeout=8)
                version = extract_version(res.text) if res.found else None
        if not path and runtime.port:
            running = net.port_open("127.0.0.1", runtime.port)

    config_present = bool(runtime.config_dir and (home / runtime.config_dir).exists())

    # Decide state
    if path or running:
        state = ComponentState.DETECTED
        health = Health.GREEN
        detail = "running" if running and not path else "installed"
    elif config_present:
        state = ComponentState.CONFIGURED
        health = Health.GREEN
        detail = "config found"
    else:
        state = ComponentState.MISSING
        health = Health.GRAY
        detail = "not installed"
        if _installable(runtime, managers):
            src = next(
                (m for m in ("winget", "brew", "choco", "npm", "pip") if runtime.install_id(m)),
                None,
            )
            detail = f"not installed (installable via {src})"

    actions = (
        ["install"] if state == ComponentState.MISSING and _installable(runtime, managers) else []
    )
    if runtime.category == "connection" and state != ComponentState.MISSING:
        actions = ["connect"]  # deferred credential flow

    return {
        "key": runtime.key,
        "name": runtime.name,
        "category": runtime.category,
        "version": version,
        "path": path,
        "running": running,
        "state": state,
        "health": health,
        "detail": detail,
        "actions": actions,
        "optional": runtime.optional,
        "models": models,
    }


def detect_all(store, which_fn=proc.which, run_fn=proc.run, home: Path | None = None) -> list[dict]:
    from ..deps.managers import available_managers

    family = store.hardware.os_family if store.hardware else "unknown"
    managers = available_managers(which_fn)
    store.bus.info("Detecting AI runtimes...", source="runtimes")

    results = []
    for runtime in platform_runtimes(family):
        result = detect_one(runtime, managers, which_fn, run_fn, home)
        results.append(result)
        store.upsert_component(
            Component(
                key=runtime.key,
                name=runtime.name,
                category=_CATEGORY.get(runtime.category, Category.RUNTIME),
                state=result["state"],
                health=result["health"],
                version=result["version"],
                path=result["path"],
                detail=result["detail"],
                actions=result["actions"],
                optional=runtime.optional,
            )
        )
        for model in result["models"]:
            store.upsert_model(
                ModelEntry(
                    name=model["name"],
                    provider="ollama",
                    size_gb=model.get("size_gb"),
                    downloaded=True,
                    detail="installed locally",
                )
            )

    present = sum(1 for r in results if r["state"] != ComponentState.MISSING)
    store.bus.success(f"Runtime detection complete: {present} present", source="runtimes")
    return results
