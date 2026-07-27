"""Deep-merge helpers — fill gaps without clobbering user values."""

from __future__ import annotations

import json
import re


def strip_jsonc(text: str) -> str:
    """Remove ``//`` and ``/* */`` comments so JSONC parses as JSON."""

    if not text:
        return text
    out = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    out = re.sub(r"(^|[^:])//.*?$", r"\1", out, flags=re.MULTILINE)
    return out


def load_json_file(text: str) -> dict:
    """Parse JSON or JSONC text into a dict (empty dict on blank input)."""

    cleaned = strip_jsonc(text.strip())
    if not cleaned:
        return {}
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object at the root")
    return data


def merge_fill_gaps(existing: dict, recommended: dict) -> dict:
    """Return *existing* with missing keys from *recommended* filled in (recursive for dicts)."""

    result = dict(existing)
    for key, value in recommended.items():
        if key not in result:
            result[key] = value
        elif isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_fill_gaps(result[key], value)
    return result


def diff_keys(before: dict, after: dict, prefix: str = "") -> list[str]:
    """List dot-paths of keys added or changed in *after* vs *before*."""

    added: list[str] = []
    for key, value in after.items():
        path = f"{prefix}.{key}" if prefix else key
        if key not in before:
            added.append(path)
        elif isinstance(value, dict) and isinstance(before.get(key), dict):
            added.extend(diff_keys(before[key], value, path))
        elif before.get(key) != value:
            added.append(path)
    return added


def dump_json_pretty(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
