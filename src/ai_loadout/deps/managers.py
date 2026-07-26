"""Which OS package managers are usable on this machine.

Loadout prefers the platform's native manager (winget / Homebrew / apt ...) so installs
come from official, signed sources rather than ad-hoc downloads.
"""

from __future__ import annotations

from ..util import proc

# manager key -> executable to probe
_MANAGERS = {
    "winget": "winget",
    "choco": "choco",
    "scoop": "scoop",
    "brew": "brew",
    "apt": "apt-get",
    "dnf": "dnf",
    "pacman": "pacman",
}

# Which managers make sense per OS family (used to pick a default).
PREFERRED = {
    "windows": ["winget", "choco", "scoop"],
    "macos": ["brew"],
    "linux": ["apt", "dnf", "pacman", "brew"],
}


def available_managers(which_fn=proc.which) -> list[str]:
    """Return the package managers present on PATH."""

    found = []
    for key, exe in _MANAGERS.items():
        if which_fn(exe):
            found.append(key)
    return found


def preferred_manager(family: str, which_fn=proc.which) -> str | None:
    """The best available manager for this OS, or ``None`` if none is installed."""

    present = set(available_managers(which_fn))
    for key in PREFERRED.get(family, []):
        if key in present:
            return key
    return None
