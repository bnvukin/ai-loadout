"""Refresh the process PATH from the OS environment (Windows registry).

Long-running processes (e.g. the dashboard) inherit PATH at launch. winget and
other installers append directories to the user/machine PATH in the registry, but
the running process never sees them until restart. Reading the registry before
detection keeps ``shutil.which`` accurate without asking the user to reboot.
"""

from __future__ import annotations

import os
import sys


def refresh_process_path(environ: dict | None = None) -> bool:
    """Merge the latest Windows PATH from the registry into ``environ``.

    Returns ``True`` when ``PATH`` changed. No-op on non-Windows platforms.
    """

    if sys.platform != "win32" and os.name != "nt":
        return False

    import winreg

    env = os.environ if environ is None else environ

    machine = _read_reg_path(
        winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
    )
    user = _read_reg_path(winreg.HKEY_CURRENT_USER, "Environment")
    registry_raw = os.pathsep.join(part for part in (machine, user) if part)
    registry_path = os.path.expandvars(registry_raw) if registry_raw else ""

    current = env.get("PATH", "")
    merged = _merge_path(current, registry_path)
    if merged != current:
        env["PATH"] = merged
        return True
    return False


def _read_reg_path(root, subkey: str) -> str:
    import winreg

    try:
        with winreg.OpenKey(root, subkey) as key:
            value, _ = winreg.QueryValueEx(key, "Path")
    except OSError:
        return ""
    return value if isinstance(value, str) else ""


def _merge_path(current: str, extra: str) -> str:
    """Append ``extra`` entries not already present (case-insensitive on Windows)."""

    parts: list[str] = []
    seen: set[str] = set()

    for raw in (current, extra):
        for entry in raw.split(os.pathsep):
            entry = entry.strip()
            if not entry:
                continue
            key = entry.lower() if os.name == "nt" else entry
            if key in seen:
                continue
            seen.add(key)
            parts.append(entry)
    return os.pathsep.join(parts)
