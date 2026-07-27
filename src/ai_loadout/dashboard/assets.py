"""Resolve dashboard static asset paths (wheel-safe)."""

from __future__ import annotations

from pathlib import Path


def static_dir() -> Path:
    """Return the filesystem directory containing the dashboard SPA bundle."""

    root = Path(__file__).resolve().parent / "static"
    if (root / "index.html").is_file():
        return root
    raise FileNotFoundError(
        "Dashboard static bundle missing from the installed package. "
        "Reinstall with: pip install ai-loadout[dashboard]"
    )
