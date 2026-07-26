"""Pure parsers for AI-runtime tool output (unit-tested against fixtures)."""

from __future__ import annotations

import re


def parse_ollama_list(text: str) -> list[dict]:
    """Parse ``ollama list`` into ``[{name, size_gb}]``.

    Sample::

        NAME            ID              SIZE      MODIFIED
        qwen3:8b        abc123          5.2 GB    2 days ago
        llama3.2:3b     def456          2.0 GB    5 days ago
    """

    models: list[dict] = []
    for i, raw in enumerate(text.splitlines()):
        line = raw.rstrip()
        if not line.strip():
            continue
        if i == 0 and line.upper().startswith("NAME"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        name = parts[0]
        size_gb = None
        m = re.search(r"([\d.]+)\s*(GB|MB)", line, re.IGNORECASE)
        if m:
            value = float(m.group(1))
            size_gb = round(value / 1024, 2) if m.group(2).upper() == "MB" else round(value, 2)
        models.append({"name": name, "size_gb": size_gb})
    return models


def parse_code_extensions(text: str) -> list[dict]:
    """Parse ``code --list-extensions --show-versions`` (``publisher.name@version``)."""

    exts: list[dict] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or "." not in line:
            continue
        if "@" in line:
            ext_id, _, version = line.partition("@")
        else:
            ext_id, version = line, None
        exts.append({"id": ext_id, "version": version or None})
    return exts


def parse_code_version(text: str) -> str | None:
    """First line of ``code --version`` is the version."""

    for line in text.splitlines():
        line = line.strip()
        if re.match(r"^\d+\.\d+", line):
            return line
    return None
