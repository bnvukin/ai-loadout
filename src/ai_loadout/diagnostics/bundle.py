"""Bundle logs + state into a timestamped ``diagnostics.zip`` (secrets redacted)."""

from __future__ import annotations

import json
import time
import zipfile

from .. import __version__
from ..config.redact import redact_text
from ..core import paths
from ..core.state import load_state
from .system import write_system_snapshot


def _tool_versions(store) -> dict:
    """Best-effort version strings from the digital twin (no subprocess side effects)."""

    versions: dict[str, str | None] = {"loadout": __version__}
    for comp in store.components():
        if comp.version:
            versions[comp.key] = comp.version
    return versions


def create_diagnostics_bundle(store=None) -> dict:
    """Create ``~/.ai-loadout/diagnostics/diagnostics-<ts>.zip`` and return metadata."""

    store = store or load_state()
    paths.ensure_dirs()
    paths.diagnostics_dir().mkdir(parents=True, exist_ok=True)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    zip_path = paths.diagnostics_dir() / f"diagnostics-{stamp}.zip"
    members: list[str] = []

    system_path = write_system_snapshot(store)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        state_path = paths.state_file()
        if state_path.is_file():
            archive.write(state_path, "state.json")
            members.append("state.json")

        archive.write(system_path, "system.json")
        members.append("system.json")

        for log_name in ("install.log", "benchmark.log"):
            log_path = paths.logs_dir() / log_name
            if log_path.is_file():
                raw = log_path.read_text(encoding="utf-8", errors="replace")
                redacted, _ = redact_text(raw)
                archive.writestr(log_name, redacted)
                members.append(log_name)

        versions = _tool_versions(store)
        archive.writestr("versions.json", json.dumps(versions, indent=2, default=str))
        members.append("versions.json")

    return {
        "path": str(zip_path),
        "filename": zip_path.name,
        "members": members,
        "timestamp": stamp,
        "size_bytes": zip_path.stat().st_size,
    }
