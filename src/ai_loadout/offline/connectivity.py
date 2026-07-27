"""Fast, timeout-guarded connectivity probe (injectable for tests)."""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from typing import Callable

# Official host used for a lightweight reachability check (no auth, widely available).
DEFAULT_PROBE_URL = "https://pypi.org/simple/"
DEFAULT_TIMEOUT = 3.0

UrlOpenFn = Callable[..., object]


def check_connectivity(
    *,
    url: str = DEFAULT_PROBE_URL,
    timeout: float = DEFAULT_TIMEOUT,
    urlopen_fn: UrlOpenFn | None = None,
) -> dict:
    """Return ``online`` status without hanging when the network is down."""

    opener = urlopen_fn or urllib.request.urlopen
    started = time.monotonic()
    try:
        req = urllib.request.Request(url, method="HEAD")
        with opener(req, timeout=timeout) as response:
            code = getattr(response, "status", None) or response.getcode()
        latency_ms = int((time.monotonic() - started) * 1000)
        online = code is not None and int(code) < 500
        return {
            "online": online,
            "probe": url,
            "latency_ms": latency_ms,
            "reason": None if online else f"probe returned HTTP {code}",
        }
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        OSError,
        ValueError,
    ) as exc:
        return {
            "online": False,
            "probe": url,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "reason": str(exc),
        }


def is_online(**kwargs) -> bool:
    return bool(check_connectivity(**kwargs).get("online"))
