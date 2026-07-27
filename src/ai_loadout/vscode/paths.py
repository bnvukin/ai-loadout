"""Resolve VS Code / Cursor user config directories per OS."""

from __future__ import annotations

from pathlib import Path

from ..config.discover import _family, _placeholders, _resolve
from ..config.registry import by_key


def editor_family(family: str | None = None) -> str:
    if family:
        return family
    return _family(None)


def settings_path(editor: str = "vscode", family: str | None = None) -> Path | None:
    """Return the settings.json path for *editor* (``vscode`` or ``cursor``)."""

    key = "vscode-settings" if editor == "vscode" else "cursor-settings"
    target = by_key(key)
    if target is None:
        return None
    fam = editor_family(family)
    ph = _placeholders()
    templates = target.paths_for(fam)
    if not templates:
        return None
    return Path(_resolve(templates[0], ph))


def user_dir(editor: str = "vscode", family: str | None = None) -> Path | None:
    path = settings_path(editor, family)
    return path.parent if path else None


def detect_editor(store=None) -> str:
    """Prefer VS Code when installed, else Cursor, else vscode as default target."""

    if store is not None:
        for key in ("vscode", "cursor"):
            comp = store.get_component(key)
            if comp and str(comp.state) != "missing":
                return key
    return "vscode"
