"""Layer 20 — opt-in, privacy-first telemetry (local-only; no transmission)."""

from __future__ import annotations

import json
import platform
import time
from pathlib import Path

from ..core import paths
from ..core.settings import load_settings

# Whitelisted fields only — never paths, usernames, secrets, or hostnames.
ALLOWED_EVENT_FIELDS = frozenset(
    {
        "ts",
        "event",
        "os_family",
        "layer",
        "count",
        "duration_ms",
        "version",
    }
)

ALLOWED_PREVIEW_FIELDS = frozenset(
    {
        "os_family",
        "python_version",
        "loadout_version",
        "layers_used",
        "event_counts",
    }
)


def _events_file() -> Path:
    paths.ensure_dirs()
    return paths.telemetry_dir() / "events.jsonl"


def is_enabled() -> bool:
    return bool(load_settings().get("telemetry_enabled", False))


def _sanitize(payload: dict) -> dict:
    clean: dict = {}
    for key, value in payload.items():
        if key not in ALLOWED_EVENT_FIELDS:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            clean[key] = value
        elif isinstance(value, list):
            clean[key] = [v for v in value if isinstance(v, (str, int, float))]
    return clean


def record_event(event: str, **fields) -> dict | None:
    """Append one anonymized event when telemetry is enabled; otherwise no-op."""

    if not is_enabled():
        return None

    from .. import __version__

    payload = _sanitize(
        {
            "ts": time.time(),
            "event": event,
            "os_family": platform.system().lower(),
            "version": __version__,
            **fields,
        }
    )
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    try:
        with _events_file().open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        return None
    return payload


def list_events(limit: int = 200) -> list[dict]:
    path = _events_file()
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[dict] = []
    for line in lines[-limit:]:
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                out.append(row)
        except ValueError:
            continue
    return out


def preview_payload() -> dict:
    """Show exactly what anonymous aggregate stats would be collected."""

    from .. import __version__

    events = list_events(limit=500)
    layers: set[str] = set()
    counts: dict[str, int] = {}
    for ev in events:
        name = str(ev.get("event", "unknown"))
        counts[name] = counts.get(name, 0) + 1
        layer = ev.get("layer")
        if layer:
            layers.add(str(layer))

    sample = {
        "os_family": platform.system().lower(),
        "python_version": platform.python_version(),
        "loadout_version": __version__,
        "layers_used": sorted(layers),
        "event_counts": counts,
    }
    return {
        "enabled": is_enabled(),
        "transmission": False,
        "storage": str(_events_file()),
        "sample": {k: sample[k] for k in ALLOWED_PREVIEW_FIELDS if k in sample},
        "note": (
            "Telemetry is opt-in and disabled by default. Events are stored locally only; "
            "no transmission endpoint is implemented."
        ),
    }


def status() -> dict:
    settings = load_settings()
    preview = preview_payload()
    return {
        "enabled": bool(settings.get("telemetry_enabled", False)),
        "transmission": False,
        "event_count": len(list_events(limit=10_000)),
        "storage": preview.get("storage"),
        "sample": preview.get("sample"),
        "note": preview.get("note"),
    }
