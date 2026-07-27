"""Timestamped snapshots of Config Center files + PATH/env manifest."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from ..config.discover import discover_all
from ..config.env import inspect_env, path_summary
from ..core import paths
from ..core.state import load_state

RESTORE_CONFIRM = "RESTORE"
_MANIFEST = "manifest.json"
_FILES_DIR = "files"


class RestoreError(RuntimeError):
    """Raised when restore is blocked (missing snapshot, bad confirm token, ...)."""


def _snapshot_root(snapshot_id: str) -> Path:
    return paths.backups_dir() / snapshot_id


def create_snapshot(store=None) -> dict:
    """Copy discovered config files into ``~/.ai-loadout/backups/<ts>/``."""

    store = store or load_state()
    paths.ensure_dirs()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    root = _snapshot_root(stamp)
    files_dir = root / _FILES_DIR
    files_dir.mkdir(parents=True, exist_ok=False)

    copied: list[dict] = []
    for cf in discover_all(store):
        if not cf.exists or not cf.path:
            continue
        src = Path(cf.path)
        if not src.is_file():
            continue
        rel = cf.key + src.suffix
        dest = files_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied.append(
            {
                "key": cf.key,
                "name": cf.name,
                "source": str(src),
                "backup": str(dest.relative_to(root)),
            }
        )

    manifest = {
        "schema": 1,
        "id": stamp,
        "timestamp": time.time(),
        "files": copied,
        "path": path_summary(),
        "env_keys": [
            {"name": row["name"], "present": row["present"], "secret": row["secret"]}
            for row in inspect_env()
        ],
    }
    (root / _MANIFEST).write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    return {
        "id": stamp,
        "path": str(root),
        "file_count": len(copied),
        "manifest": manifest,
    }


def list_snapshots() -> list[dict]:
    """Return global snapshots (directories with ``manifest.json``), newest first."""

    paths.ensure_dirs()
    out: list[dict] = []
    root = paths.backups_dir()
    if not root.is_dir():
        return out
    for entry in sorted(root.iterdir(), reverse=True):
        if not entry.is_dir():
            continue
        manifest_path = entry / _MANIFEST
        if not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = {}
        out.append(
            {
                "id": entry.name,
                "path": str(entry),
                "timestamp": manifest.get("timestamp"),
                "file_count": len(manifest.get("files", [])),
            }
        )
    return out


def restore_snapshot(
    snapshot_id: str,
    *,
    confirm: str | None = None,
    restore_env: bool = False,
) -> dict:
    """Copy snapshot files back to their original paths (destructive overwrite).

    Requires ``confirm='RESTORE'``. Environment variables are recorded in the manifest
    but are **not** written back to the OS unless ``restore_env=True`` (not exposed in
    the dashboard — manifest is informational only by default).
    """

    if confirm != RESTORE_CONFIRM:
        raise RestoreError(f"restore is destructive — pass confirm='{RESTORE_CONFIRM}' to proceed")
    if restore_env:
        raise RestoreError("system environment restore is not implemented (manifest is read-only)")

    root = _snapshot_root(snapshot_id)
    manifest_path = root / _MANIFEST
    if not manifest_path.is_file():
        raise RestoreError(f"snapshot not found: {snapshot_id}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    restored: list[dict] = []
    for item in manifest.get("files", []):
        rel = item.get("backup")
        target = item.get("source")
        if not rel or not target:
            continue
        src = root / rel
        if not src.is_file():
            raise RestoreError(f"missing backup file in snapshot: {rel}")
        dest = Path(target)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        restored.append({"key": item.get("key"), "path": str(dest)})

    return {
        "id": snapshot_id,
        "restored": restored,
        "file_count": len(restored),
        "env_restored": False,
    }
