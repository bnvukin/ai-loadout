"""Registry of AI runtimes / editors / agent CLIs Loadout detects and can install."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Runtime:
    key: str
    name: str
    category: str = "runtime"  # runtime | editor | connection
    command: str | None = None  # CLI on PATH, if any
    version_args: tuple[str, ...] = ("--version",)
    config_dir: str | None = None  # directory under the user's home that implies presence
    port: int | None = None  # local port that implies a running server
    winget: str | None = None
    choco: str | None = None
    brew: str | None = None
    npm: str | None = None
    pip: str | None = None
    optional: bool = True
    special: str | None = None  # "ollama" | "vscode"
    note: str = ""

    def applies_to(self, family: str) -> bool:  # noqa: ARG002 - all runtimes are cross-platform today
        return True

    def install_id(self, manager: str) -> str | None:
        return getattr(self, manager, None)


RUNTIMES: list[Runtime] = [
    Runtime(
        "ollama",
        "Ollama",
        "runtime",
        command="ollama",
        port=11434,
        special="ollama",
        winget="Ollama.Ollama",
        brew="ollama",
        optional=False,
        note="Local model runtime. Loadout's default backend for offline models.",
    ),
    Runtime(
        "vscode",
        "VS Code",
        "editor",
        command="code",
        special="vscode",
        winget="Microsoft.VisualStudioCode",
        choco="vscode",
        brew="visual-studio-code",
        optional=False,
    ),
    Runtime(
        "continue",
        "Continue",
        "runtime",
        config_dir=".continue",
        note="VS Code AI assistant. Config is auto-generated in Layer 7.",
    ),
    Runtime(
        "cursor",
        "Cursor",
        "editor",
        command="cursor",
        config_dir=".cursor",
    ),
    Runtime(
        "open-webui",
        "Open WebUI",
        "runtime",
        command="open-webui",
        port=8080,
        pip="open-webui",
        note="Web chat UI for local models (often run via Docker).",
    ),
    Runtime("lmstudio", "LM Studio", "runtime", command="lms", note="Desktop local-model app."),
    Runtime(
        "anythingllm",
        "AnythingLLM",
        "runtime",
        command="anythingllm",
        note="Local RAG/desktop app.",
    ),
    Runtime(
        "claude-code",
        "Claude Code",
        "connection",
        command="claude",
        npm="@anthropic-ai/claude-code",
        note="Anthropic coding agent (needs login).",
    ),
    Runtime(
        "codex-cli",
        "Codex CLI",
        "connection",
        command="codex",
        npm="@openai/codex",
        note="OpenAI coding agent (needs login).",
    ),
    Runtime(
        "gemini-cli",
        "Gemini CLI",
        "connection",
        command="gemini",
        npm="@google/gemini-cli",
        note="Google coding agent (needs login).",
    ),
    Runtime(
        "opencode",
        "OpenCode",
        "connection",
        command="opencode",
        note="Open-source terminal coding agent.",
    ),
]


def platform_runtimes(family: str) -> list[Runtime]:
    return [r for r in RUNTIMES if r.applies_to(family)]


def by_key(key: str) -> Runtime | None:
    for runtime in RUNTIMES:
        if runtime.key == key:
            return runtime
    return None
