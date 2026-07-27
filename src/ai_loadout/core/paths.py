"""Where Loadout keeps its per-machine data (the digital-twin state, logs, backups).

None of this is committed to git -- it describes the specific machine Loadout runs on.
The location can be overridden with the ``LOADOUT_HOME`` environment variable, which is
also what the test suite uses to stay hermetic.
"""

from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    """Root directory for Loadout's per-machine data (default: ``~/.ai-loadout``)."""

    override = os.environ.get("LOADOUT_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".ai-loadout"


def logs_dir() -> Path:
    return data_dir() / "logs"


def backups_dir() -> Path:
    return data_dir() / "backups"


def runs_dir() -> Path:
    """Stored install/benchmark sessions (for the timeline + replay)."""

    return data_dir() / "runs"


def state_file() -> Path:
    return data_dir() / "state.json"


def install_log() -> Path:
    return logs_dir() / "install.log"


def benchmark_log() -> Path:
    return logs_dir() / "benchmark.log"


def system_log() -> Path:
    return logs_dir() / "system.json"


def diagnostics_dir() -> Path:
    return data_dir() / "diagnostics"


def ensure_dirs() -> None:
    """Create the data directories if they do not exist yet."""

    for directory in (data_dir(), logs_dir(), backups_dir(), runs_dir(), diagnostics_dir()):
        directory.mkdir(parents=True, exist_ok=True)
