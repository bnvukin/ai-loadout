"""Run external commands safely.

Detection, dependency checks, and health probes all shell out to tools like
``nvidia-smi``, ``git``, ``winget``. This wrapper:

* never uses ``shell=True`` (arguments are always a list),
* never raises for the common "tool not installed" / timeout cases,
* returns a small structured result the callers can pattern-match on.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass


def _is_windows() -> bool:
    """Indirected so tests can flip it without mutating the global ``os.name``."""

    return os.name == "nt"


@dataclass
class RunResult:
    ok: bool
    code: int
    out: str
    err: str
    found: bool = True  # False when the executable itself was not found

    @property
    def text(self) -> str:
        """stdout, falling back to stderr (some tools print versions to stderr)."""

        return self.out if self.out.strip() else self.err


def which(name: str) -> str | None:
    """Absolute path to an executable on PATH, or ``None``.

    On Windows, refresh PATH from the registry first (long-running processes keep a
    stale PATH after winget installs) and fall back to ``where.exe`` when ``which``
    misses App Execution Aliases / ``.cmd`` shims.
    """

    if _is_windows():
        from .path_env import refresh_process_path

        refresh_process_path()
    hit = shutil.which(name)
    if hit:
        return hit
    if _is_windows():
        result = run(["where.exe", name], timeout=8)
        if result.found and result.out.strip():
            line = result.out.strip().splitlines()[0].strip()
            if line and not line.lower().startswith("info:"):
                return line
    return None


def run(
    cmd: list[str],
    timeout: float = 15.0,
    env: dict | None = None,
    cwd: str | None = None,
) -> RunResult:
    """Execute ``cmd`` and capture output. Best-effort, never raises."""

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=cwd,
            check=False,
        )
        return RunResult(
            proc.returncode == 0, proc.returncode, proc.stdout or "", proc.stderr or ""
        )
    except FileNotFoundError:
        return RunResult(False, 127, "", "executable not found", found=False)
    except PermissionError as exc:
        return RunResult(False, 126, "", f"permission denied: {exc}")
    except subprocess.TimeoutExpired:
        return RunResult(False, -1, "", f"timed out after {timeout}s")
    except OSError as exc:
        return RunResult(False, -1, "", str(exc))


def powershell(script: str, timeout: float = 20.0) -> RunResult:
    """Run a PowerShell one-liner on Windows (no profile, non-interactive)."""

    exe = which("pwsh") or which("powershell")
    if not exe:
        return RunResult(False, 127, "", "powershell not found", found=False)
    return run(
        [exe, "-NoProfile", "-NonInteractive", "-Command", script],
        timeout=timeout,
    )
