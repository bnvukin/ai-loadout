"""Official download / package-manager source allowlist.

Loadout installs through vendor package managers when possible; any direct download URL
must pass :func:`is_official_source` before we trust it.
"""

from __future__ import annotations

from urllib.parse import urlparse

# Hostnames (exact or suffix match) considered official vendor / registry mirrors.
_OFFICIAL_SUFFIXES: tuple[str, ...] = (
    "github.com",
    "githubusercontent.com",
    "python.org",
    "pypi.org",
    "pythonhosted.org",
    "npmjs.com",
    "npmjs.org",
    "registry.npmjs.org",
    "ollama.com",
    "docker.com",
    "microsoft.com",
    "visualstudio.com",
    "chocolatey.org",
    "brew.sh",
    "ubuntu.com",
    "debian.org",
    "huggingface.co",
    "anthropic.com",
    "openai.com",
    "google.com",
    "nodejs.org",
    "git-scm.com",
    "astral.sh",
    "anaconda.com",
    "conda-forge.org",
)

_OFFICIAL_EXACT: frozenset[str] = frozenset(
    {
        "files.pythonhosted.org",
        "pypi.python.org",
        "cdn.winget.microsoft.com",
        "community.chocolatey.org",
        "download.docker.com",
        "packages.microsoft.com",
    }
)

# Package managers Loadout delegates signature/hash verification to.
PACKAGE_MANAGERS: tuple[str, ...] = (
    "winget",
    "choco",
    "brew",
    "apt",
    "dnf",
    "pacman",
    "scoop",
    "npm",
    "pip",
)


def _normalize_url(url: str) -> str:
    u = (url or "").strip()
    if u.startswith("git+https://") or u.startswith("git+http://"):
        return u[4:]
    return u


def _host_allowed(host: str) -> bool:
    host = host.lower()
    if host in _OFFICIAL_EXACT:
        return True
    for suffix in _OFFICIAL_SUFFIXES:
        if host == suffix or host.endswith("." + suffix):
            return True
    return False


def is_official_source(url: str) -> bool:
    """Return True when ``url`` points at a known official vendor or registry host."""

    if not url or not str(url).strip():
        return False
    normalized = _normalize_url(str(url))
    try:
        parsed = urlparse(normalized)
    except ValueError:
        return False
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https", ""):
        return False
    host = parsed.hostname
    if not host:
        return False
    return _host_allowed(host)
