"""Read-only self-update check against PyPI (with offline fallback)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Callable

from .. import __version__
from ..deps.version import is_older

PYPI_JSON = "https://pypi.org/pypi/ai-loadout/json"
CHANGELOG_URL = "https://github.com/bnvukin/ai-loadout/blob/main/CHANGELOG.md"
DEFAULT_TIMEOUT = 8

UrlOpenFn = Callable[..., object]


def _fetch_json(
    url: str, *, timeout: int = DEFAULT_TIMEOUT, urlopen_fn: UrlOpenFn | None = None
) -> dict:
    opener = urlopen_fn or urllib.request.urlopen
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with opener(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)


def parse_pypi_latest(payload: dict) -> str:
    """Extract the latest version string from a PyPI project JSON payload."""

    info = payload.get("info") or {}
    version = info.get("version")
    if not version:
        raise ValueError("missing info.version in PyPI payload")
    return str(version)


def check_self_update(
    *,
    timeout: int = DEFAULT_TIMEOUT,
    urlopen_fn: UrlOpenFn | None = None,
) -> dict:
    """Compare installed Loadout version to PyPI latest."""

    base = {
        "current": __version__,
        "latest": None,
        "update_available": False,
        "source": "pypi",
        "changelog_url": CHANGELOG_URL,
        "offline": False,
        "rollback_hint": f"pip install ai-loadout=={__version__}",
    }
    try:
        payload = _fetch_json(PYPI_JSON, timeout=timeout, urlopen_fn=urlopen_fn)
        latest = parse_pypi_latest(payload)
        base["latest"] = latest
        base["update_available"] = is_older(__version__, latest)
        base["upgrade_hint"] = "pip install --upgrade ai-loadout"
        if base["update_available"]:
            base["rollback_hint"] = f"pip install ai-loadout=={__version__}"
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        ValueError,
        OSError,
    ) as exc:
        base["offline"] = True
        base["error"] = str(exc)
    return base
