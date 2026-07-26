"""Tiny version extraction + comparison, tolerant of the messy strings tools emit.

Examples it handles: ``git version 2.43.0``, ``v24.15.0``, ``Docker version 27.1.1,
build 63125853``, ``Python 3.12.10``, ``Cuda compilation tools, release 12.4, V12.4.131``.
"""

from __future__ import annotations

import re

_VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?(?:\.(\d+))?")


def extract_version(text: str) -> str | None:
    """Return the first ``x.y[.z]`` version found in ``text``, or ``None``."""

    if not text:
        return None
    # Prefer a version that follows the word "release"/"version"/"v" when present,
    # but fall back to the first version-looking token anywhere.
    for anchor in (r"release\s+", r"version\s+v?", r"\bv"):
        m = re.search(anchor + r"(\d+\.\d+(?:\.\d+){0,2})", text, re.IGNORECASE)
        if m:
            return m.group(1)
    m = _VERSION_RE.search(text)
    return m.group(0) if m else None


def version_tuple(version: str | None) -> tuple[int, ...]:
    if not version:
        return ()
    parts = re.findall(r"\d+", version)
    return tuple(int(p) for p in parts)


def is_older(current: str | None, minimum: str | None) -> bool:
    """True if ``current`` is strictly older than ``minimum`` (missing current => True)."""

    if not minimum:
        return False
    if not current:
        return True
    a = version_tuple(current)
    b = version_tuple(minimum)
    length = max(len(a), len(b))
    a += (0,) * (length - len(a))
    b += (0,) * (length - len(b))
    return a < b
