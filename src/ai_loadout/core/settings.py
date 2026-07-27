"""Loadout user settings persisted in ``~/.ai-loadout/config.json``."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from . import paths

DEFAULTS: dict = {
    "telemetry_enabled": False,
    "monitor_enabled": False,
    "monitor_interval_sec": 300,
}

_SETTINGS: dict | None = None


def _config_path() -> Path:
    return paths.config_file()


def load_settings(*, reload: bool = False) -> dict:
    """Return merged settings (defaults + on-disk file)."""

    global _SETTINGS
    if _SETTINGS is not None and not reload:
        return deepcopy(_SETTINGS)

    merged = deepcopy(DEFAULTS)
    cfg = _config_path()
    if cfg.is_file():
        try:
            raw = json.loads(cfg.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                merged.update(raw)
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    _SETTINGS = merged
    return deepcopy(_SETTINGS)


def save_settings(updates: dict) -> dict:
    """Merge *updates* into settings and persist."""

    global _SETTINGS
    current = load_settings(reload=True)
    for key, value in updates.items():
        if key in DEFAULTS:
            current[key] = value
    paths.ensure_dirs()
    _config_path().write_text(
        json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    _SETTINGS = current
    return deepcopy(current)


def reset_settings_cache() -> None:
    """Clear in-process cache (tests)."""

    global _SETTINGS
    _SETTINGS = None
