"""Discover and safely read the config files in :mod:`registry`.

Discovery is **read-only**: it resolves per-OS path templates, notes which files exist,
and (on demand) reads their contents with secrets redacted. Existing files are recorded
in the digital twin as ``Category.CONFIG`` components so the dashboard/Config Center can
list them alongside everything else. Editing lives in :mod:`edit` and is gated by trust.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ..core.events import EventLevel
from ..core.lifecycle import Category, ComponentState, Health
from ..core.models import Component
from ..core.state import StateStore
from .redact import redact_text
from .registry import CONFIG_TARGETS, ConfigTarget, by_key, targets_for

# Never read more than this into memory -- config files should be small.
MAX_READ_BYTES = 256 * 1024


@dataclass
class ConfigFile:
    key: str
    name: str
    owner: str
    fmt: str
    trust: str
    description: str
    path: str | None  # best resolved path (first existing, else first candidate)
    exists: bool
    size_bytes: int | None
    secret: bool
    candidates: list[str]

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "owner": self.owner,
            "fmt": self.fmt,
            "trust": self.trust,
            "description": self.description,
            "path": self.path,
            "exists": self.exists,
            "size_bytes": self.size_bytes,
            "secret": self.secret,
            "candidates": list(self.candidates),
        }


def _placeholders() -> dict[str, str]:
    home = Path.home()
    return {
        "home": str(home),
        "appdata": os.environ.get("APPDATA") or str(home / "AppData" / "Roaming"),
        "localappdata": os.environ.get("LOCALAPPDATA") or str(home / "AppData" / "Local"),
        "xdg_config": os.environ.get("XDG_CONFIG_HOME") or str(home / ".config"),
        "documents": str(home / "Documents"),
    }


def _resolve(template: str, ph: dict[str, str]) -> str:
    resolved = template
    for name, value in ph.items():
        resolved = resolved.replace("{" + name + "}", value)
    resolved = os.path.expandvars(os.path.expanduser(resolved))
    return os.path.normpath(resolved)


def _family(store: StateStore | None) -> str:
    if store is not None and store.hardware and store.hardware.os_family:
        return store.hardware.os_family
    from ..detect.system import os_family

    return os_family()


def discover_one(target: ConfigTarget, family: str) -> ConfigFile:
    ph = _placeholders()
    candidates = [_resolve(t, ph) for t in target.paths_for(family)]
    chosen = next((c for c in candidates if os.path.isfile(c)), None)
    exists = chosen is not None
    path = chosen or (candidates[0] if candidates else None)
    size = None
    if exists and path:
        try:
            size = os.path.getsize(path)
        except OSError:
            size = None
    return ConfigFile(
        key=target.key,
        name=target.name,
        owner=target.owner,
        fmt=target.fmt,
        trust=str(target.trust),
        description=target.description,
        path=path,
        exists=exists,
        size_bytes=size,
        secret=target.secret,
        candidates=candidates,
    )


def discover_all(store: StateStore | None = None) -> list[ConfigFile]:
    """Resolve every applicable config target; record existing ones in the twin."""

    family = _family(store)
    results = [discover_one(t, family) for t in targets_for(family)]
    if store is not None:
        for cf in results:
            if not cf.exists:
                continue
            store.upsert_component(
                Component(
                    key=f"config:{cf.key}",
                    name=cf.name,
                    category=Category.CONFIG,
                    state=ComponentState.CONFIGURED,
                    health=Health.GREEN,
                    path=cf.path,
                    detail=cf.description,
                    optional=True,
                )
            )
        found = sum(1 for cf in results if cf.exists)
        store.bus.publish(
            EventLevel.INFO,
            f"Config Center: found {found} config file(s)",
            kind="config",
            target="config",
        )
    return results


def read_config(key: str, family: str | None = None, *, redact: bool = True) -> dict:
    """Read a config file's text (secrets redacted by default).

    Returns a dict with ``exists``, ``path``, ``content``, ``redacted`` and ``truncated``.
    Never raises for the common not-found / permission / binary cases.
    """

    target = by_key(key)
    if target is None:
        return {"error": f"unknown config target: {key}", "exists": False}
    fam = family or _family(None)
    cf = discover_one(target, fam)
    if not cf.exists or not cf.path:
        return {"key": key, "exists": False, "path": cf.path, "content": None}

    try:
        with open(cf.path, encoding="utf-8", errors="replace") as fh:
            raw = fh.read(MAX_READ_BYTES + 1)
    except OSError as exc:
        return {"key": key, "exists": True, "path": cf.path, "error": str(exc)}

    truncated = len(raw) > MAX_READ_BYTES
    content = raw[:MAX_READ_BYTES]
    changed = False
    if redact:
        content, changed = redact_text(content)
    return {
        "key": key,
        "exists": True,
        "path": cf.path,
        "content": content,
        "redacted": bool(redact and (changed or target.secret)),
        "truncated": truncated,
        "trust": str(target.trust),
    }


def known_keys() -> list[str]:
    return [t.key for t in CONFIG_TARGETS]
