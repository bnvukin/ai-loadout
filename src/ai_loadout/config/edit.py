"""Safe, backup-first config edits gated by trust level.

The Config Center is read-only by default. When a mutation *is* requested, it must go
through here so that:

* the original file is copied into ``~/.ai-loadout/backups`` first (always reversible),
* the write is atomic (temp file + ``os.replace``),
* ``ADVANCED`` / ``EXPERT`` targets require an explicit confirmation token, mirroring the
  dashboard's "type EDIT to continue" gate.

This module is intentionally small and side-effect-light so it is easy to test; the CLI
does not expose it yet -- it is the foundation the dashboard's editor will build on.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from ..core import paths
from ..core.lifecycle import TrustLevel
from .registry import by_key

# Token a caller must pass to confirm a mutating edit at each trust level.
CONFIRM_TOKENS = {
    TrustLevel.SAFE: None,  # no confirmation needed
    TrustLevel.ADVANCED: "CONFIRM",
    TrustLevel.EXPERT: "EDIT",
}


class EditError(RuntimeError):
    """Raised when an edit is blocked (bad trust token, missing file, ...)."""


def backup_file(path: str | os.PathLike) -> Path:
    """Copy ``path`` into the backups dir with a timestamp; return the backup path."""

    src = Path(path)
    if not src.is_file():
        raise EditError(f"cannot back up (not a file): {src}")
    paths.ensure_dirs()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = paths.backups_dir() / f"{src.name}.{stamp}.bak"
    dest.write_bytes(src.read_bytes())
    return dest


def _required_token(trust: TrustLevel) -> str | None:
    return CONFIRM_TOKENS.get(trust)


def apply_edit(key: str, new_content: str, *, confirm: str | None = None) -> dict:
    """Write ``new_content`` to a known config target after backing it up.

    Enforces the trust gate: ``ADVANCED``/``EXPERT`` targets require the matching
    ``confirm`` token. Returns a small result dict describing what happened.
    """

    target = by_key(key)
    if target is None:
        raise EditError(f"unknown config target: {key}")

    required = _required_token(target.trust)
    if required is not None and confirm != required:
        raise EditError(
            f"'{target.name}' is {target.trust} -- pass confirm='{required}' to proceed"
        )

    from .discover import _family, discover_one

    cf = discover_one(target, _family(None))
    if not cf.path:
        raise EditError(f"no writable path for {key}")

    backup = None
    if cf.exists:
        backup = backup_file(cf.path)

    dest = Path(cf.path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".loadout-tmp")
    tmp.write_text(new_content, encoding="utf-8")
    os.replace(tmp, dest)

    return {
        "key": key,
        "path": str(dest),
        "backup": str(backup) if backup else None,
        "created": not cf.exists,
        "trust": str(target.trust),
    }
