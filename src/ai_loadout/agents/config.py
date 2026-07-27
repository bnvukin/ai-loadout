"""Agent CLI detection, MCP starter config, and workspace scaffolding."""

from __future__ import annotations

import json
from pathlib import Path

from ..config.merge import dump_json_pretty, load_json_file, merge_fill_gaps
from ..config.write_util import write_text_atomic
from ..util import proc

AGENT_KEYS = ("claude-code", "codex-cli", "gemini-cli", "opencode")

STARTER_MCP: dict = {
    "mcpServers": {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "{workspace}"],
            "env": {},
        },
    }
}

SCAFFOLD_DIRS: tuple[str, ...] = (
    ".cursor/rules",
    ".cursor/memory",
    "prompts",
    "memory",
)


def _detect_agents(store=None) -> list[dict]:
    found: list[dict] = []
    if store is not None:
        for key in AGENT_KEYS:
            comp = store.get_component(key)
            if comp and str(comp.state) != "missing":
                found.append(
                    {
                        "key": key,
                        "name": comp.name,
                        "version": comp.version,
                        "path": comp.path,
                    }
                )
        return found
    for key in AGENT_KEYS:
        from ..runtimes.registry import by_key

        rt = by_key(key)
        if rt and rt.command and proc.which(rt.command):
            found.append({"key": key, "name": rt.name, "command": rt.command})
    return found


def _mcp_path(home: Path | None = None) -> Path:
    home = home or Path.home()
    return home / ".cursor" / "mcp.json"


def _load_mcp(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return load_json_file(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def build_mcp_config(workspace: str = ".") -> dict:
    cfg = json.loads(json.dumps(STARTER_MCP))  # deep copy
    for _name, server in cfg.get("mcpServers", {}).items():
        args = server.get("args") or []
        server["args"] = [a.replace("{workspace}", workspace) for a in args]
    return cfg


def scaffold_plan(home: Path | None = None) -> list[dict]:
    home = home or Path.home()
    plan: list[dict] = []
    for rel in SCAFFOLD_DIRS:
        target = home / rel
        plan.append(
            {
                "path": str(target),
                "exists": target.is_dir(),
                "action": "skip" if target.is_dir() else "create",
            }
        )
    return plan


def preview(store=None, home: Path | None = None, workspace: str = ".") -> dict:
    home = home or Path.home()
    mcp_path = _mcp_path(home)
    generated = build_mcp_config(workspace)
    existing = _load_mcp(mcp_path)
    merged = merge_fill_gaps(existing, generated)
    folders = scaffold_plan(home)

    return {
        "ok": True,
        "agents": _detect_agents(store),
        "mcp_path": str(mcp_path),
        "mcp_exists": mcp_path.is_file(),
        "merged_mcp": merged,
        "mcp_content": dump_json_pretty(merged),
        "folders": folders,
        "note": "MCP config uses npx; requires Node.js on PATH. No credentials are written.",
    }


def apply(store=None, home: Path | None = None, workspace: str = ".") -> dict:
    plan = preview(store, home, workspace)
    if not plan.get("ok"):
        return plan

    mcp_path = Path(plan["mcp_path"])
    mcp_path.parent.mkdir(parents=True, exist_ok=True)
    mcp_result = write_text_atomic(mcp_path, plan["mcp_content"])

    created: list[str] = []
    for item in plan["folders"]:
        if item["action"] != "create":
            continue
        p = Path(item["path"])
        p.mkdir(parents=True, exist_ok=True)
        created.append(str(p))

    readme = Path(home or Path.home()) / ".cursor" / "rules" / "loadout-starter.md"
    if not readme.is_file():
        readme.parent.mkdir(parents=True, exist_ok=True)
        readme.write_text(
            "# Agent rules (starter)\n\n"
            "Add project-specific instructions here. Loadout created this folder — edit freely.\n",
            encoding="utf-8",
        )
        created.append(str(readme))

    if store is not None:
        store.bus.info("Agent/MCP scaffold applied", kind="config", target="agents")

    return {
        "ok": True,
        "mcp": mcp_result,
        "folders_created": created,
        **plan,
    }
