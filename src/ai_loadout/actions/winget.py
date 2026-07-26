"""Interpret winget exit codes and output for install/upgrade recovery.

winget often exits non-zero when a package is already present or when an upgrade
target was never installed via winget (e.g. PowerShell 5.1 built into Windows).
The action runner uses these helpers to fall back to install or treat the run as
success when the machine state is already satisfied.
"""

from __future__ import annotations

# APPINSTALLER_CLI_ERROR_UPDATE_NOT_APPLICABLE (signed / unsigned on Windows).
_WINGET_UPDATE_NOT_APPLICABLE = -1978335189
_WINGET_UPDATE_NOT_APPLICABLE_U = _WINGET_UPDATE_NOT_APPLICABLE & 0xFFFFFFFF

_ALREADY_SATISFIED_MARKERS = (
    "already installed",
    "no available upgrade found",
    "no available upgrade.",
    "no newer package versions are available",
    "no newer package versions",
    "package already installed",
)

_UPGRADE_NOT_INSTALLED_MARKERS = (
    "no installed package found matching input criteria",
    "no installed package found matching the input criteria",
)


def _normalize_code(code: int) -> tuple[int, int]:
    return code, code & 0xFFFFFFFF


def winget_upgrade_not_installed(output: str) -> bool:
    """True when winget upgrade failed because the package is not winget-managed."""

    lower = (output or "").lower()
    return any(marker in lower for marker in _UPGRADE_NOT_INSTALLED_MARKERS)


def winget_already_satisfied(code: int, output: str) -> bool:
    """True when winget output/code means the desired state is already met."""

    signed, unsigned = _normalize_code(code)
    if signed in (_WINGET_UPDATE_NOT_APPLICABLE, 0):
        pass
    elif unsigned == _WINGET_UPDATE_NOT_APPLICABLE_U:
        pass
    elif code != 0:
        # Non-zero without a known benign code — still check the text below.
        pass

    lower = (output or "").lower()
    if any(marker in lower for marker in _ALREADY_SATISFIED_MARKERS):
        return True

    return signed == _WINGET_UPDATE_NOT_APPLICABLE or unsigned == _WINGET_UPDATE_NOT_APPLICABLE_U
