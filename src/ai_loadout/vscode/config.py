"""VS Code / Cursor configuration preview and apply."""

from __future__ import annotations

import json
from pathlib import Path

from ..config.merge import diff_keys, dump_json_pretty, load_json_file, merge_fill_gaps
from ..config.write_util import write_text_atomic
from .extensions import RECOMMENDED_EXTENSIONS, all_install_commands
from .paths import detect_editor, settings_path, user_dir
from .settings import OPTIONAL_KEYBINDINGS, OPTIONAL_TASKS, RECOMMENDED_SETTINGS


def _read_settings(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return load_json_file(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def _keybindings_path(user: Path) -> Path:
    return user / "keybindings.json"


def _tasks_path(user: Path) -> Path:
    return user / "tasks.json"


def preview(store=None, editor: str | None = None) -> dict:
    """Return merged settings preview without writing."""

    editor = editor or detect_editor(store)
    sp = settings_path(editor)
    if sp is None:
        return {"ok": False, "reason": f"no settings path for {editor}"}

    existing = _read_settings(sp)
    merged = merge_fill_gaps(existing, RECOMMENDED_SETTINGS)
    added = diff_keys(existing, merged)

    user = user_dir(editor)
    kb_exists = user and _keybindings_path(user).is_file()
    tasks_exists = user and _tasks_path(user).is_file()

    return {
        "ok": True,
        "editor": editor,
        "settings_path": str(sp),
        "exists": sp.is_file(),
        "merged_settings": merged,
        "settings_content": dump_json_pretty(merged),
        "keys_added": added,
        "extensions": list(RECOMMENDED_EXTENSIONS),
        "install_commands": all_install_commands(),
        "optional_keybindings": OPTIONAL_KEYBINDINGS,
        "optional_tasks": OPTIONAL_TASKS,
        "keybindings_exists": bool(kb_exists),
        "tasks_exists": bool(tasks_exists),
    }


def apply(store=None, editor: str | None = None, *, include_optional: bool = False) -> dict:
    """Backup + merge-write settings.json (and optional keybindings/tasks)."""

    plan = preview(store, editor)
    if not plan.get("ok"):
        return plan

    sp = Path(plan["settings_path"])
    result = write_text_atomic(sp, plan["settings_content"])
    written = {"settings": result}

    user = user_dir(plan["editor"])
    if include_optional and user:
        kb = _keybindings_path(user)
        if not kb.is_file():
            content = json.dumps([OPTIONAL_KEYBINDINGS], indent=2) + "\n"
            written["keybindings"] = write_text_atomic(kb, content)
        tasks = _tasks_path(user)
        if not tasks.is_file():
            written["tasks"] = write_text_atomic(tasks, dump_json_pretty(OPTIONAL_TASKS))

    if store is not None:
        store.bus.info(
            f"VS Code settings applied ({plan['editor']})",
            kind="config",
            target="vscode",
        )

    return {
        "ok": True,
        "editor": plan["editor"],
        "written": written,
        "keys_added": plan["keys_added"],
    }
