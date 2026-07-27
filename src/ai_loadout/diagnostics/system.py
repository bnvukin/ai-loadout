"""Write a redacted ``system.json`` machine snapshot under ``~/.ai-loadout/logs/``."""

from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

from .. import __version__
from ..config.env import inspect_env, path_summary
from ..core import paths
from ..deps.managers import available_managers
from ..detect.system import os_family


def write_system_snapshot(store=None) -> Path:
    """Capture machine + component state (secrets redacted) to ``logs/system.json``."""

    from ..core.state import load_state

    store = store or load_state()
    paths.ensure_dirs()

    payload = {
        "schema": 1,
        "timestamp": time.time(),
        "loadout_version": __version__,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python_version": sys.version.split()[0],
            "python_executable": sys.executable,
            "family": (
                store.hardware.os_family
                if store is not None and store.hardware and store.hardware.os_family
                else os_family()
            ),
        },
        "managers": available_managers(),
        "hardware": store.hardware.to_dict() if store.hardware else None,
        "components": [c.to_dict() for c in store.components()],
        "env": inspect_env(),
        "path": path_summary(),
    }
    dest = paths.system_log()
    dest.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return dest
