"""Curated VS Code extension recommendations for AI development."""

from __future__ import annotations

from ..actions.commands import _normalize_argv
from ..util import proc

RECOMMENDED_EXTENSIONS: tuple[dict, ...] = (
    {
        "id": "Continue.continue",
        "name": "Continue",
        "reason": "Open-source AI code assistant (local + cloud models).",
    },
    {
        "id": "ms-python.python",
        "name": "Python",
        "reason": "Python language support for agents and FastAPI work.",
    },
    {
        "id": "ms-python.vscode-pylance",
        "name": "Pylance",
        "reason": "Fast Python type checking and IntelliSense.",
    },
    {
        "id": "ms-azuretools.vscode-docker",
        "name": "Docker",
        "reason": "Manage containers for Open WebUI, vLLM, and local stacks.",
    },
    {
        "id": "GitHub.copilot-chat",
        "name": "GitHub Copilot Chat",
        "reason": "Optional cloud assistant (requires GitHub login).",
        "optional": True,
    },
)


def extension_install_command(ext_id: str, code_exe: str | None = None) -> dict:
    """Build argv for ``code --install-extension <id>`` (no shell)."""

    exe = code_exe or proc.which("code") or proc.which("cursor")
    if not exe:
        return {
            "ok": False,
            "id": ext_id,
            "reason": "Neither 'code' nor 'cursor' CLI found on PATH",
            "argv": [],
            "display": "",
        }
    argv = _normalize_argv([exe, "--install-extension", ext_id, "--force"])
    return {
        "ok": True,
        "id": ext_id,
        "argv": argv,
        "display": " ".join(argv),
        "exe": exe,
    }


def all_install_commands(
    code_exe: str | None = None, *, include_optional: bool = False
) -> list[dict]:
    out: list[dict] = []
    for ext in RECOMMENDED_EXTENSIONS:
        if ext.get("optional") and not include_optional:
            continue
        cmd = extension_install_command(ext["id"], code_exe)
        cmd["name"] = ext["name"]
        cmd["reason"] = ext["reason"]
        out.append(cmd)
    return out


def run_extension_install(ext_id: str, store=None) -> dict:
    """Execute extension install via the action engine pattern (streamed log)."""

    from ..util import proc

    cmd = extension_install_command(ext_id)
    if not cmd["ok"]:
        if store is not None:
            store.bus.warning(cmd["reason"], kind="log", target="vscode")
        return cmd

    if store is not None:
        store.bus.info(f"Installing extension {ext_id}", kind="step", target="vscode")

    result = proc.run(cmd["argv"], timeout=600)
    ok = result.ok
    if store is not None:
        level = "success" if ok else "error"
        getattr(store.bus, level)(
            f"Extension {ext_id}: exit {result.code}",
            kind="log",
            target="vscode",
        )
    return {
        **cmd,
        "success": ok,
        "exit_code": result.code,
        "output": result.text[:2000],
    }
