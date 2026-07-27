"""Minimal YAML load/dump for Continue-style configs (no PyYAML dependency)."""

from __future__ import annotations

import json
from typing import Any


def loads(text: str) -> dict:
    """Parse JSON or a minimal YAML subset into a dict."""

    text = (text or "").strip()
    if not text:
        return {}
    if text.startswith("{"):
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    return _parse_yaml(text)


def dumps(data: dict) -> str:
    """Serialize a dict to YAML (Continue config subset)."""

    lines: list[str] = []
    for key, value in data.items():
        lines.extend(_dump_pair(key, value, 0))
    return "\n".join(lines) + "\n"


def _dump_pair(key: str, value: Any, indent: int) -> list[str]:
    pad = " " * indent
    if isinstance(value, dict):
        lines = [f"{pad}{key}:"]
        for sub_k, sub_v in value.items():
            lines.extend(_dump_pair(sub_k, sub_v, indent + 2))
        return lines
    if isinstance(value, list):
        lines = [f"{pad}{key}:"]
        for item in value:
            if isinstance(item, dict):
                first = True
                for ik, iv in item.items():
                    prefix = "  - " if first else "    "
                    lines.append(f"{pad}{prefix}{ik}: {_scalar(iv)}")
                    first = False
            else:
                lines.append(f"{pad}  - {_scalar(item)}")
        return lines
    return [f"{pad}{key}: {_scalar(value)}"]


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    if any(c in s for c in ":{}[]&*#?|-<>=!%@`"):
        return json.dumps(s)
    return s


def _parse_yaml(text: str) -> dict:
    root: dict = {}
    stack: list[tuple[int, dict]] = [(0, root)]
    list_keys: dict[str, list] = {}
    current_list_key: str | None = None

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip())
        line = raw_line.strip()
        while stack and indent < stack[-1][0]:
            stack.pop()
        container = stack[-1][1]

        if line.startswith("- "):
            if current_list_key is None:
                continue
            item_text = line[2:].strip()
            if ":" in item_text:
                ik, iv = item_text.split(":", 1)
                entry = {ik.strip(): _parse_value(iv.strip())}
            else:
                entry = _parse_value(item_text)
            lst = list_keys.setdefault(current_list_key, [])
            if isinstance(entry, dict) and lst and isinstance(lst[-1], dict):
                lst[-1].update(entry)
            else:
                lst.append(entry if isinstance(entry, dict) else {"value": entry})
            continue

        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        if not val:
            new: dict = {}
            container[key] = new
            stack.append((indent + 2, new))
            current_list_key = key
            list_keys[key] = []
            container[key] = list_keys[key]
        else:
            container[key] = _parse_value(val)
            current_list_key = None
    return root


def _parse_value(raw: str) -> Any:
    if raw in ("true", "True"):
        return True
    if raw in ("false", "False"):
        return False
    if raw in ("null", "~", ""):
        return None
    if raw.startswith('"') and raw.endswith('"'):
        return json.loads(raw)
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1]
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw
