"""Refresh the process PATH from the OS environment (Windows registry).

Long-running processes (e.g. the dashboard) inherit PATH at launch. winget and
other installers append directories to the user/machine PATH in the registry, but
the running process never sees them until restart. ``shutil.which`` also does
*not* expand ``%VAR%`` inside individual PATH entries, so a stale process can
keep literal ``%USERPROFILE%\\...`` segments that never resolve.
"""

from __future__ import annotations

import os
import sys


def _is_windows() -> bool:
    """Windows check, indirected so tests can flip it without mutating global ``os``.

    Patching ``os.name`` globally corrupts ``shutil.which`` / ``pathlib`` for every
    other test in the process (and crashes pytest on 3.9), so detection code routes
    its platform check through here instead.
    """

    return os.name == "nt" or sys.platform == "win32"


def refresh_process_path(environ: dict | None = None) -> bool:
    """Rebuild ``PATH`` from the registry (expanded) plus process-only extras.

    Returns ``True`` when ``PATH`` changed. No-op on non-Windows platforms.
    """

    if not _is_windows():
        return False

    env = os.environ if environ is None else environ
    canonical = _windows_path_from_registry(env)
    merged = _merge_path(canonical, _expand_path_string(env.get("PATH", ""), env))
    if merged != env.get("PATH", ""):
        env["PATH"] = merged
        return True
    return False


def _windows_path_from_registry(env: dict) -> str:
    # Root hives are addressed by name so this function never imports ``winreg``
    # itself -- only ``_read_reg_path`` does, and tests mock that. That keeps the
    # module importable and this path exercisable on non-Windows CI.
    machine = _read_reg_path(
        "HKLM", r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
    )
    user = _read_reg_path("HKCU", "Environment")
    raw = os.pathsep.join(part for part in (machine, user) if part)
    return _expand_path_string(raw, env)


def _expand_path_string(raw: str, env: dict) -> str:
    """Expand ``%VAR%`` in each PATH segment."""

    parts: list[str] = []
    backup = None
    if env is not os.environ:
        backup = dict(os.environ)
        os.environ.update({k: str(v) for k, v in env.items()})
    try:
        for entry in raw.split(os.pathsep):
            entry = entry.strip()
            if not entry:
                continue
            parts.append(os.path.expandvars(entry))
    finally:
        if backup is not None:
            os.environ.clear()
            os.environ.update(backup)
    return os.pathsep.join(parts)


def _read_reg_path(root: str, subkey: str) -> str:
    import winreg

    hives = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}
    try:
        with winreg.OpenKey(hives[root], subkey) as key:
            value, _ = winreg.QueryValueEx(key, "Path")
    except OSError:
        return ""
    return value if isinstance(value, str) else ""


def _merge_path(primary: str, secondary: str, *, case_insensitive: bool | None = None) -> str:
    """Merge PATH strings; ``primary`` entries win order, ``secondary`` adds missing dirs.

    Dedup is case-insensitive on Windows by default; callers/tests can force it.
    """

    if case_insensitive is None:
        case_insensitive = _is_windows()

    parts: list[str] = []
    seen: set[str] = set()

    for raw in (primary, secondary):
        for entry in raw.split(os.pathsep):
            entry = entry.strip()
            if not entry:
                continue
            key = entry.lower() if case_insensitive else entry
            if key in seen:
                continue
            seen.add(key)
            parts.append(entry)
    return os.pathsep.join(parts)
