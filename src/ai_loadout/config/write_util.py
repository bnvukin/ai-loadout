"""Atomic config writes with automatic backup."""

from __future__ import annotations

import os
from pathlib import Path

from .edit import backup_file


def write_text_atomic(path: str | Path, content: str) -> dict:
    """Back up an existing file, then write *content* atomically."""

    dest = Path(path)
    backup = None
    if dest.is_file():
        backup = backup_file(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".loadout-tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, dest)
    return {
        "path": str(dest),
        "backup": str(backup) if backup else None,
        "created": backup is None,
    }
