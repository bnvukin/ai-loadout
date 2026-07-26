"""Human-language "why does this matter?" for every component.

The dashboard shows this next to any non-green item so the user knows the *impact* of it
being missing/outdated and *what it unlocks* before deciding to install. Data first: a
curated table keyed by component key, with a sensible fallback to the registry ``note``.
"""

from __future__ import annotations

from ..deps.registry import by_key as dep_by_key
from ..runtimes.registry import by_key as runtime_by_key

# key -> (impact if missing/outdated, what it unlocks, external docs link)
_ADVICE: dict[str, tuple[str, str, str]] = {
    "git": (
        "Without Git you cannot clone repos, install tools from source, or track your work.",
        "Version control + installing many AI tools that ship via Git.",
        "https://git-scm.com/downloads",
    ),
    "python": (
        "Most AI tooling, MCP servers, and ML libraries are Python-based and won't run.",
        "Running AI apps, notebooks, FastAPI backends, and MCP servers.",
        "https://www.python.org/downloads/",
    ),
    "node": (
        "Node-based agent CLIs (Claude Code, Codex, Gemini) and web UIs won't install/run.",
        "JavaScript/TypeScript tooling and most coding-agent CLIs.",
        "https://nodejs.org/en/download",
    ),
    "npm": (
        "npm ships with Node; if it's missing/old, global CLI installs will fail.",
        "Installing global agent CLIs and JS packages.",
        "https://docs.npmjs.com/",
    ),
    "pnpm": (
        "Optional. Faster, disk-efficient package manager; nice-to-have, not required.",
        "Faster JS installs for monorepos.",
        "https://pnpm.io/installation",
    ),
    "uv": (
        "Optional but recommended: dramatically faster Python installs and venvs.",
        "Fast, reproducible Python environments.",
        "https://docs.astral.sh/uv/",
    ),
    "docker": (
        "Containerized AI stacks (Open WebUI, vLLM, databases) can't run without Docker.",
        "One-command AI stacks and isolated, reproducible services.",
        "https://docs.docker.com/get-docker/",
    ),
    "powershell": (
        "PowerShell 7+ is recommended; 5.1 works but lacks newer features some scripts use.",
        "Cross-platform scripting and better terminal tooling on Windows.",
        "https://learn.microsoft.com/powershell/scripting/install/installing-powershell",
    ),
    "wsl": (
        "Optional. Many Linux-first AI toolchains run best under WSL on Windows.",
        "Running Linux AI tooling natively on Windows.",
        "https://learn.microsoft.com/windows/wsl/install",
    ),
    "cuda": (
        "Without the CUDA toolkit, GPU-accelerated inference/training may fall back to CPU.",
        "Fast GPU inference and building GPU-accelerated wheels.",
        "https://developer.nvidia.com/cuda-downloads",
    ),
    "vsbuildtools": (
        "Some Python packages compile native code; without build tools those installs fail.",
        "Compiling native Python wheels on Windows.",
        "https://visualstudio.microsoft.com/visual-cpp-build-tools/",
    ),
    "ollama": (
        "Ollama is Loadout's default local-model runtime; without it you can't pull/run models.",
        "Running local LLMs fully offline.",
        "https://ollama.com/download",
    ),
    "vscode": (
        "VS Code is the recommended editor for the Continue AI assistant and extensions.",
        "AI-assisted coding with Continue/Copilot and rich tooling.",
        "https://code.visualstudio.com/download",
    ),
    "continue": (
        "Continue is the in-editor AI assistant Loadout auto-configures for your local models.",
        "Chat + autocomplete in VS Code backed by your local models.",
        "https://docs.continue.dev/",
    ),
    "open-webui": (
        "Optional. A friendly web chat UI in front of your local models.",
        "Browser chat for Ollama models.",
        "https://docs.openwebui.com/",
    ),
    "claude-code": (
        "Optional coding agent (needs an Anthropic login).",
        "Terminal coding agent from Anthropic.",
        "https://docs.anthropic.com/en/docs/claude-code",
    ),
    "codex-cli": (
        "Optional coding agent (needs an OpenAI login).",
        "Terminal coding agent from OpenAI.",
        "https://github.com/openai/codex",
    ),
    "gemini-cli": (
        "Optional coding agent (needs a Google login).",
        "Terminal coding agent from Google.",
        "https://github.com/google-gemini/gemini-cli",
    ),
}


def component_advice(key: str) -> dict:
    """Return {impact, needed_for, link, note, optional} for a component key."""

    dep = dep_by_key(key)
    runtime = runtime_by_key(key)
    note = (dep.note if dep else "") or (runtime.note if runtime else "")
    optional = dep.optional if dep else (runtime.optional if runtime else True)

    impact, needed_for, link = _ADVICE.get(key, ("", "", ""))
    if not impact:
        # Fall back to the registry note so we always say *something* useful.
        impact = note or "Recommended for a complete AI workstation."
        needed_for = note or ""
    return {
        "key": key,
        "impact": impact,
        "needed_for": needed_for,
        "link": link,
        "note": note,
        "optional": optional,
    }
