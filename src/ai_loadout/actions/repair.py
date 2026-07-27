"""Layer 11 - one-click repairs for the issues the health check surfaces.

Every ``fix_action`` a :class:`~ai_loadout.health.checker.HealthIssue` can carry maps to a
handler here. ``install`` / ``update`` delegate to the install runner; service issues
(``start-ollama`` / ``start-docker``) are handled directly. Handlers are conservative:
they never elevate privileges silently and they re-check the live signal afterwards so the
dashboard can flip the badge green (or explain why it could not).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

from ..core.lifecycle import ComponentState, Health
from ..util import net
from .runner import run_action

# fix_action -> (component key it repairs, human label)
REPAIR_ACTIONS = {
    "start-ollama": "Start the Ollama server",
    "start-docker": "Start Docker Desktop",
    "install": "Install the component",
    "update": "Update the component",
    "path-dedupe": "Remove duplicate PATH entries",
    "fix-loadout-perms": "Fix Loadout data directory permissions",
}


def _spawn_detached(argv: list[str]) -> None:
    """Launch a long-lived background process that outlives this call."""

    kwargs: dict = {}
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(
        argv,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        **kwargs,
    )


def repair(store, action: str, target: str | None = None, *, dry_run: bool = False) -> dict:
    """Run a repair by ``fix_action`` id. Returns a result dict."""

    if action in ("install", "update"):
        return _repair_via_install(store, action, target, dry_run)
    if action == "start-ollama":
        return _start_ollama(store, dry_run)
    if action == "start-docker":
        return _start_docker(store, dry_run)
    if action == "path-dedupe":
        from ..config.path_repair import apply_path_dedupe

        return apply_path_dedupe(store, dry_run=dry_run)
    if action == "fix-loadout-perms":
        from ..config.path_repair import fix_loadout_permissions

        return fix_loadout_permissions(store, dry_run=dry_run)
    return {"ok": False, "action": action, "error": f"No repair handler for '{action}'."}


def _repair_via_install(store, action: str, target: str | None, dry_run: bool) -> dict:
    if not target:
        return {"ok": False, "action": action, "error": "No component given to repair."}
    from ..deps import registry as deps_registry

    kind = "dependency" if deps_registry.by_key(target) else "runtime"
    verb = "upgrade" if action == "update" else "install"
    res = run_action(store, target, kind, verb, dry_run=dry_run)
    res["ok"] = bool(res.get("success") or dry_run)
    res["action"] = action
    return res


def _start_ollama(store, dry_run: bool) -> dict:
    ollama = shutil.which("ollama")
    display = f"{ollama or 'ollama'} serve"
    if not ollama:
        return {
            "ok": False,
            "action": "start-ollama",
            "display": display,
            "error": "Ollama is not installed. Install it first.",
        }
    if dry_run:
        store.bus.info(f"Dry run -- would run: {display}", source="repair", target="ollama")
        return {"ok": True, "action": "start-ollama", "display": display, "ran": False}

    if net.port_open("127.0.0.1", 11434):
        store.bus.info("Ollama server already running", source="repair", target="ollama")
        return {"ok": True, "action": "start-ollama", "already": True, "ran": False}

    store.update_component("ollama", state=ComponentState.REPAIRING, detail="starting server...")
    store.bus.info(
        "Starting Ollama server (ollama serve)...", source="repair", target="ollama", kind="step"
    )
    try:
        _spawn_detached([ollama, "serve"])
    except Exception as exc:
        store.bus.error(f"Failed to start Ollama: {exc}", source="repair", target="ollama")
        return {"ok": False, "action": "start-ollama", "error": str(exc)}

    ok = _wait_for_port("127.0.0.1", 11434, timeout=20)
    if ok:
        store.update_component(
            "ollama", state=ComponentState.DETECTED, health=Health.GREEN, detail="running"
        )
        store.bus.success("Ollama server is up", source="repair", target="ollama")
    else:
        store.bus.warning("Ollama did not open its port in time", source="repair", target="ollama")
    return {"ok": ok, "action": "start-ollama", "ran": True, "display": display}


def _start_docker(store, dry_run: bool) -> dict:
    """Best-effort start of Docker Desktop / daemon (guided when we can't automate it)."""

    launcher = _docker_desktop_path()
    if dry_run:
        return {
            "ok": True,
            "action": "start-docker",
            "ran": False,
            "display": launcher or "start Docker Desktop",
        }
    if launcher:
        store.update_component(
            "docker", state=ComponentState.REPAIRING, detail="starting daemon..."
        )
        store.bus.info("Launching Docker Desktop...", source="repair", target="docker", kind="step")
        try:
            _spawn_detached([launcher])
        except Exception as exc:
            return {"ok": False, "action": "start-docker", "error": str(exc)}
        ok = _wait_for_docker(store, timeout=60)
        return {
            "ok": ok,
            "action": "start-docker",
            "ran": True,
            "guidance": None if ok else "Docker is still starting -- give it a moment.",
        }
    # No launcher we recognize: return actionable guidance instead of failing silently.
    return {
        "ok": False,
        "action": "start-docker",
        "ran": False,
        "guidance": "Open Docker Desktop manually (or run `sudo systemctl start docker` on Linux), "
        "then re-run the health check.",
    }


def _docker_desktop_path() -> str | None:
    if os.name == "nt":
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),):
            candidate = Path(base) / "Docker" / "Docker" / "Docker Desktop.exe"
            if candidate.exists():
                return str(candidate)
        return None
    mac = Path("/Applications/Docker.app")
    if mac.exists():
        return "open"  # `open -a Docker` handled by caller? simplified: not auto-launched
    return None


def _wait_for_port(host: str, port: int, timeout: int) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if net.port_open(host, port):
            return True
        time.sleep(1)
    return False


def _wait_for_docker(store, timeout: int) -> bool:
    from ..util import proc

    docker = shutil.which("docker")
    if not docker:
        return False
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.run([docker, "info"], timeout=8).ok:
            store.update_component(
                "docker", state=ComponentState.DETECTED, health=Health.GREEN, detail="running"
            )
            return True
        time.sleep(3)
    return False
