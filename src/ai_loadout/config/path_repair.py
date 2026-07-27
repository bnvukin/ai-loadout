"""PATH dedupe and Loadout directory permission repairs."""

from __future__ import annotations

import os
import stat
import time
from pathlib import Path

from ..config.env import path_summary
from ..core import paths
from ..util.path_env import _is_windows


def dedupe_path_string(path_string: str, *, case_insensitive: bool | None = None) -> str:
    """Remove duplicate PATH segments preserving first-seen order."""

    if case_insensitive is None:
        case_insensitive = _is_windows()

    parts: list[str] = []
    seen: set[str] = set()
    for entry in path_string.split(os.pathsep):
        entry = entry.strip()
        if not entry:
            continue
        key = entry.lower() if case_insensitive else entry
        if key in seen:
            continue
        seen.add(key)
        parts.append(entry)
    return os.pathsep.join(parts)


def analyze_path_dedupe(environ: dict | None = None) -> dict:
    env = os.environ if environ is None else environ
    current = env.get("PATH", "")
    summary = path_summary(env)
    deduped = dedupe_path_string(current)
    before = [p for p in current.split(os.pathsep) if p.strip()]
    after = [p for p in deduped.split(os.pathsep) if p.strip()]
    return {
        "current_count": len(before),
        "deduped_count": len(after),
        "duplicates": summary.get("duplicates", []),
        "missing": summary.get("missing", []),
        "removed": max(0, len(before) - len(after)),
        "changed": deduped != current,
        "deduped_path": deduped,
    }


def _backup_path_snapshot(label: str, path_value: str) -> str:
    paths.ensure_dirs()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = paths.backups_dir() / f"path-{label}-{stamp}.txt"
    dest.write_text(path_value + "\n", encoding="utf-8")
    return str(dest)


def _write_windows_user_path(deduped: str) -> dict:
    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Environment",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, deduped)
    os.environ["PATH"] = deduped
    return {"registry": "HKCU\\Environment\\Path", "applied": True}


def apply_path_dedupe(store=None, *, dry_run: bool = False, environ: dict | None = None) -> dict:
    """Backup + dedupe PATH (Windows HKCU write; other OSes refresh process PATH only)."""

    env = os.environ if environ is None else environ
    analysis = analyze_path_dedupe(env)
    if not analysis["changed"]:
        return {"ok": True, "action": "path-dedupe", "changed": False, "analysis": analysis}

    backup = _backup_path_snapshot("before", env.get("PATH", ""))
    display = f"Deduplicate PATH ({analysis['removed']} duplicate entries removed)"
    if dry_run:
        return {
            "ok": True,
            "action": "path-dedupe",
            "dry_run": True,
            "display": display,
            "backup": backup,
            "analysis": analysis,
        }

    deduped = analysis["deduped_path"]
    applied: dict = {"process": True}
    guidance = None
    if _is_windows():
        try:
            applied = _write_windows_user_path(deduped)
        except OSError as exc:
            return {"ok": False, "action": "path-dedupe", "error": str(exc), "analysis": analysis}
    else:
        env["PATH"] = deduped
        guidance = (
            "Process PATH updated. Persist in your shell profile (~/.bashrc, ~/.zshrc) "
            "if you want this permanent."
        )

    if store is not None:
        store.bus.success("PATH deduplicated", source="repair", target="path")

    return {
        "ok": True,
        "action": "path-dedupe",
        "changed": True,
        "backup": backup,
        "analysis": analysis,
        "applied": applied,
        "guidance": guidance,
    }


def analyze_loadout_permissions() -> dict:
    paths.ensure_dirs()
    targets = [
        paths.data_dir(),
        paths.logs_dir(),
        paths.backups_dir(),
        paths.cache_dir(),
        paths.telemetry_dir(),
    ]
    issues: list[dict] = []
    for target in targets:
        if not target.exists():
            issues.append({"path": str(target), "issue": "missing"})
            continue
        if not os.access(target, os.W_OK):
            issues.append({"path": str(target), "issue": "not_writable"})
    return {"ok": len(issues) == 0, "issues": issues}


def fix_loadout_permissions(store=None, *, dry_run: bool = False) -> dict:
    analysis = analyze_loadout_permissions()
    if analysis["ok"]:
        return {"ok": True, "action": "fix-loadout-perms", "fixed": [], "analysis": analysis}

    if dry_run:
        return {
            "ok": True,
            "action": "fix-loadout-perms",
            "dry_run": True,
            "would_fix": [i["path"] for i in analysis["issues"]],
            "analysis": analysis,
        }

    fixed: list[str] = []
    for item in analysis["issues"]:
        target = Path(item["path"])
        target.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.chmod(target, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
            else:
                os.chmod(target, 0o755)
            fixed.append(str(target))
        except OSError:
            continue

    if store is not None and fixed:
        store.bus.success(
            "Loadout directory permissions repaired", source="repair", target="loadout"
        )

    return {"ok": bool(fixed), "action": "fix-loadout-perms", "fixed": fixed, "analysis": analysis}
