"""Execute a mutating action (install / upgrade / model pull) and keep the twin honest.

Flow for every action:
1. Build the concrete argv (``commands.build_command``) -- refuse if we can't.
2. Flip the component to a *busy* lifecycle state so the UI shows a spinner.
3. Stream stdout line-by-line: each line becomes a ``log`` event **and** is appended to
   ``install.log`` so there is a durable record.
4. Re-detect the single component afterwards so its badge reflects reality (green when it
   worked), or mark it FAILED/RED with the tail of the output as the error.

Nothing here runs unless ``dry_run`` is False. A dry run returns the exact command that
*would* run, which is what the dashboard shows before the user confirms.
"""

from __future__ import annotations

import subprocess
import threading
from datetime import datetime, timezone

from ..core import paths
from ..core.lifecycle import ComponentState, Health
from ..core.models import ModelEntry
from .commands import ActionCommand, build_command

# Generous ceilings -- real installs and model pulls are slow; we still want a hard stop.
_TIMEOUTS = {"install": 2400, "upgrade": 2400, "pull": 5400}
_MAX_TAIL = 40  # lines of output kept as the error summary on failure


def _log(line: str) -> None:
    """Append a timestamped line to install.log (best-effort)."""

    try:
        paths.ensure_dirs()
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with open(paths.install_log(), "a", encoding="utf-8") as fh:
            fh.write(f"{stamp}  {line}\n")
    except Exception:
        pass


def preview(key: str, kind: str, action: str, family: str | None = None) -> dict:
    """Return the command that would run, without executing anything."""

    return build_command(key, kind, action, family=family).to_dict()


def run_action(
    store,
    key: str,
    kind: str,
    action: str,
    *,
    dry_run: bool = False,
    family: str | None = None,
    timeout: int | None = None,
) -> dict:
    """Run (or preview) an install/upgrade/pull for one component or model."""

    cmd = build_command(key, kind, action, family=family)
    result = cmd.to_dict()
    result["ran"] = False
    result["success"] = False
    result["exit_code"] = None

    if not cmd.ok:
        store.bus.warning(f"Cannot {action} {cmd.name}: {cmd.reason}", source="action", target=key)
        result["error"] = cmd.reason
        return result

    if dry_run:
        store.bus.info(f"Dry run -- would execute: {cmd.display}", source="action", target=key)
        return result

    if cmd.kind == "model":
        return _run_model_pull(store, cmd, result, timeout)
    return _run_component(store, cmd, result, timeout)


def _run_component(store, cmd: ActionCommand, result: dict, timeout: int | None) -> dict:
    busy = ComponentState.INSTALLING  # upgrades still surface as "installing" work
    store.update_component(cmd.key, name=cmd.name, state=busy, detail=f"{cmd.action}ing...")
    store.bus.info(
        f"Starting {cmd.action}: {cmd.display}", source="action", target=cmd.key, kind="step"
    )

    success, code, tail = _execute_with_recovery(store, cmd, timeout)
    result["ran"] = True
    result["exit_code"] = code

    if success:
        fresh = rescan_component(store, cmd.key)
        result["success"] = True
        result["component"] = fresh
        store.bus.success(f"{cmd.name} {cmd.action} complete", source="action", target=cmd.key)
    else:
        err = tail or f"exited with code {code}"
        store.update_component(
            cmd.key,
            state=ComponentState.FAILED,
            health=Health.RED,
            detail=f"{cmd.action} failed",
            error=err,
        )
        store.bus.error(f"{cmd.name} {cmd.action} failed ({code})", source="action", target=cmd.key)
        result["error"] = err
    return result


def _family_from_store(store) -> str | None:
    return store.hardware.os_family if store.hardware else None


def _execute_with_recovery(store, cmd: ActionCommand, timeout: int | None) -> tuple[bool, int, str]:
    """Run ``cmd`` with winget upgrade→install fallback and already-satisfied detection."""

    from . import winget as winget_outcomes

    code, tail = _stream(store, cmd, timeout)
    output = tail or ""

    if (
        code != 0
        and cmd.action == "upgrade"
        and cmd.manager == "winget"
        and winget_outcomes.winget_upgrade_not_installed(output)
    ):
        install_cmd = build_command(cmd.key, cmd.kind, "install", family=_family_from_store(store))
        if install_cmd.ok:
            store.bus.info(
                f"No winget upgrade target — falling back to install: {install_cmd.display}",
                source="action",
                target=cmd.key,
            )
            code, install_tail = _stream(store, install_cmd, timeout)
            output = "\n".join(part for part in (output, install_tail) if part).strip()
            tail = install_tail or tail

    if winget_outcomes.winget_already_satisfied(code, output):
        return True, 0, output
    return code == 0, code, tail or output


def _run_model_pull(store, cmd: ActionCommand, result: dict, timeout: int | None) -> dict:
    store.upsert_model(
        ModelEntry(
            name=cmd.display.replace("ollama pull ", ""),
            provider="ollama",
            downloaded=False,
            detail="downloading...",
        )
    )
    store.bus.info(
        f"Pulling model: {cmd.display}", source="action", target=f"model:{cmd.key}", kind="step"
    )
    code, tail = _stream(store, cmd, timeout)
    result["ran"] = True
    result["exit_code"] = code
    if code == 0:
        result["success"] = True
        refresh_local_models(store)
        store.bus.success(f"Model {cmd.name} ready", source="action", target=f"model:{cmd.key}")
    else:
        store.bus.error(f"Model pull failed ({code})", source="action", target=f"model:{cmd.key}")
        result["error"] = tail or f"exited with code {code}"
    return result


def _stream(store, cmd: ActionCommand, timeout: int | None):
    """Run argv, stream stdout as events + install.log, return (exit_code, tail_text)."""

    timeout = timeout or _TIMEOUTS.get(cmd.action, 1800)
    _log(f"$ {cmd.display}")
    tail: list[str] = []
    try:
        proc = subprocess.Popen(
            cmd.argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except FileNotFoundError:
        _log(f"! executable not found: {cmd.argv[0]}")
        return 127, f"Executable not found: {cmd.argv[0]}"
    except Exception as exc:  # pragma: no cover - defensive
        _log(f"! failed to start: {exc}")
        return 1, str(exc)

    killed = {"v": False}

    def _kill() -> None:
        killed["v"] = True
        try:
            proc.kill()
        except Exception:
            pass

    watchdog = threading.Timer(timeout, _kill)
    watchdog.start()
    try:
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.rstrip("\n")
            if not line:
                continue
            _log(line)
            tail.append(line)
            if len(tail) > _MAX_TAIL:
                tail.pop(0)
            store.bus.publish(
                "info",
                line,
                source="action",
                kind="progress",
                target=cmd.key,
            )
        code = proc.wait()
    finally:
        watchdog.cancel()

    if killed["v"]:
        return 124, f"Timed out after {timeout}s"
    return code, "\n".join(tail[-8:])


def rescan_component(store, key: str) -> dict | None:
    """Re-detect a single dependency/runtime and update the twin. Returns its dict."""

    from ..deps import detect as deps_detect
    from ..deps import registry as deps_registry
    from ..runtimes import detect as rt_detect
    from ..runtimes import registry as rt_registry
    from ..util.path_env import refresh_process_path

    refresh_process_path()
    family = store.hardware.os_family if store.hardware else None
    dep = deps_registry.by_key(key)
    if dep is not None:
        res = deps_detect.detect_one(dep, family or "unknown")
        _upsert_from_dep(store, dep, res)
        comp = store.get_component(key)
        if comp:
            store.bus.publish(
                "info",
                f"{comp.name} rescanned: {comp.health}",
                source="loadout",
                kind="state",
                target=key,
                health=str(comp.health),
            )
            return comp.to_dict()
        return None

    runtime = rt_registry.by_key(key)
    if runtime is not None:
        from ..deps.managers import available_managers

        res = rt_detect.detect_one(runtime, available_managers())
        _upsert_from_runtime(store, runtime, res)
        comp = store.get_component(key)
        if comp:
            store.bus.publish(
                "info",
                f"{comp.name} rescanned: {comp.health}",
                source="loadout",
                kind="state",
                target=key,
                health=str(comp.health),
            )
            return comp.to_dict()
        return None
    return None


def _upsert_from_dep(store, dep, res) -> None:
    from ..core.lifecycle import Category
    from ..core.models import Component

    store.upsert_component(
        Component(
            key=dep.key,
            name=dep.name,
            category=Category.DEPENDENCY,
            state=res["state"],
            health=res["health"],
            version=res["version"],
            path=res["path"],
            detail=res["detail"],
            actions=res["actions"],
            optional=dep.optional,
        )
    )


def _upsert_from_runtime(store, runtime, res) -> None:
    from ..core.lifecycle import Category
    from ..core.models import Component

    category = {
        "runtime": Category.RUNTIME,
        "editor": Category.EDITOR,
        "connection": Category.CONNECTION,
    }.get(runtime.category, Category.RUNTIME)
    store.upsert_component(
        Component(
            key=runtime.key,
            name=runtime.name,
            category=category,
            state=res["state"],
            health=res["health"],
            version=res["version"],
            path=res["path"],
            detail=res["detail"],
            actions=res["actions"],
            optional=runtime.optional,
        )
    )
    for model in res.get("models", []):
        store.upsert_model(
            ModelEntry(
                name=model["name"],
                provider="ollama",
                size_gb=model.get("size_gb"),
                downloaded=True,
                detail="installed locally",
            )
        )


def refresh_local_models(store) -> list[dict]:
    """Ask Ollama what is installed locally and reconcile the twin's model list."""

    import shutil

    from ..runtimes.parsers import parse_ollama_list
    from ..util import proc

    ollama = shutil.which("ollama")
    if not ollama:
        return []
    listing = proc.run([ollama, "list"], timeout=10)
    if not listing.ok:
        return []
    models = parse_ollama_list(listing.out)
    for model in models:
        store.upsert_model(
            ModelEntry(
                name=model["name"],
                provider="ollama",
                size_gb=model.get("size_gb"),
                downloaded=True,
                detail="installed locally",
            )
        )
    return models
