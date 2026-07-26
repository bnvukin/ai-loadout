"""Curated "loadouts": opinionated toolchains for a kind of user (Layer 18).

A profile is just a named bundle of dependency keys, runtime keys, and candidate model
keys (in priority order). The planner reconciles a profile against the current digital
twin to decide what actually needs installing. Capabilities are smaller add-ons the user
can toggle on top of (or instead of) a profile.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Profile:
    key: str
    name: str
    description: str
    deps: tuple[str, ...] = ()  # dependency keys (see deps.registry)
    runtimes: tuple[str, ...] = ()  # runtime keys (see runtimes.registry)
    models: tuple[str, ...] = field(default_factory=tuple)  # catalog keys, best-first
    capabilities: tuple[str, ...] = ()


PROFILES: list[Profile] = [
    Profile(
        "minimal",
        "Minimal",
        "The essentials to code against a local model.",
        deps=("git", "python"),
        runtimes=("vscode", "ollama", "continue"),
        models=("llama3.2-3b", "phi3.5", "gemma3-4b"),
        capabilities=("local-llm",),
    ),
    Profile(
        "student",
        "Student / Learner",
        "Learn AI dev cheaply: local models, an editor, and an assistant.",
        deps=("git", "python"),
        runtimes=("vscode", "ollama", "continue"),
        models=("gemma3-4b", "llama3.2-3b", "phi3.5"),
        capabilities=("local-llm",),
    ),
    Profile(
        "web-ai-dev",
        "Web + AI Developer",
        "Build AI-powered web apps (Node + Python + local coding model).",
        deps=("git", "python", "node"),
        runtimes=("vscode", "ollama", "continue"),
        models=("qwen2.5-coder-7b", "gemma3-4b", "llama3.2-3b"),
        capabilities=("local-llm",),
    ),
    Profile(
        "agentic-coder",
        "Agentic Coder",
        "Terminal coding agents plus a strong local coding model.",
        deps=("git", "python", "node"),
        runtimes=("vscode", "ollama", "continue", "claude-code", "codex-cli"),
        models=("qwen2.5-coder-7b", "deepseek-coder-v2-16b", "gemma3-4b"),
        capabilities=("local-llm", "coding-agents"),
    ),
    Profile(
        "ai-research",
        "AI Research",
        "Explore models with a web UI and containers; GPU-aware.",
        deps=("git", "python", "node", "docker", "cuda"),
        runtimes=("vscode", "ollama", "continue", "open-webui"),
        models=("qwen3-14b", "qwen3-8b", "gemma3-4b"),
        capabilities=("local-llm", "containers", "web-ui", "gpu"),
    ),
    Profile(
        "ml-engineer",
        "ML Engineer",
        "Full toolchain: containers, GPU build tools, fast Python, strong models.",
        deps=("git", "python", "node", "uv", "docker", "cuda"),
        runtimes=("vscode", "ollama", "continue", "open-webui"),
        models=("deepseek-coder-v2-16b", "qwen3-14b", "qwen2.5-coder-7b"),
        capabilities=("local-llm", "containers", "web-ui", "gpu"),
    ),
]


# Add-on capabilities that inject extra requirements onto any profile (or stand alone).
CAPABILITY_REQUIREMENTS: dict[str, dict[str, tuple[str, ...]]] = {
    "local-llm": {"runtimes": ("ollama", "continue")},
    "coding-agents": {"runtimes": ("claude-code", "codex-cli", "gemini-cli")},
    "containers": {"deps": ("docker",)},
    "web-ui": {"deps": ("docker",), "runtimes": ("open-webui",)},
    "gpu": {"deps": ("cuda",)},
    "node": {"deps": ("node",)},
}


def by_key(key: str) -> Profile | None:
    for profile in PROFILES:
        if profile.key == key:
            return profile
    return None


def profile_keys() -> list[str]:
    return [p.key for p in PROFILES]
