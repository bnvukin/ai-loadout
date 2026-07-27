"""Provider/service connection guidance (present/absent only — never secret values)."""

from __future__ import annotations

from ..config.env import inspect_env

CONNECTIONS: tuple[dict, ...] = (
    {
        "key": "openai",
        "name": "OpenAI",
        "env_vars": ("OPENAI_API_KEY",),
        "docs_url": "https://platform.openai.com/api-keys",
        "setup_hint": "Set OPENAI_API_KEY in your environment or shell profile.",
        "unlocks": ("Continue cloud models", "OpenAI-compatible API clients"),
    },
    {
        "key": "anthropic",
        "name": "Anthropic",
        "env_vars": ("ANTHROPIC_API_KEY",),
        "docs_url": "https://console.anthropic.com/settings/keys",
        "setup_hint": "Set ANTHROPIC_API_KEY in your environment.",
        "unlocks": ("Claude models in Continue", "Anthropic SDK"),
    },
    {
        "key": "google",
        "name": "Google Gemini",
        "env_vars": ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
        "docs_url": "https://aistudio.google.com/app/apikey",
        "setup_hint": "Set GOOGLE_API_KEY or GEMINI_API_KEY.",
        "unlocks": ("Gemini models", "Google AI SDK"),
    },
    {
        "key": "github",
        "name": "GitHub",
        "env_vars": ("GITHUB_TOKEN", "GH_TOKEN"),
        "docs_url": "https://github.com/settings/tokens",
        "setup_hint": "Set GITHUB_TOKEN or GH_TOKEN for CLI/API access.",
        "unlocks": ("GitHub Copilot CLI", "Private repo access", "gh CLI auth"),
    },
    {
        "key": "openrouter",
        "name": "OpenRouter",
        "env_vars": ("OPENROUTER_API_KEY",),
        "docs_url": "https://openrouter.ai/keys",
        "setup_hint": "Set OPENROUTER_API_KEY for multi-model routing.",
        "unlocks": ("Unified model API", "Continue OpenRouter provider"),
    },
    {
        "key": "huggingface",
        "name": "Hugging Face",
        "env_vars": ("HF_TOKEN", "HUGGINGFACE_TOKEN"),
        "docs_url": "https://huggingface.co/settings/tokens",
        "setup_hint": "Set HF_TOKEN or HUGGINGFACE_TOKEN.",
        "unlocks": ("Private/gated models", "Hub downloads", "Inference API"),
    },
    {
        "key": "groq",
        "name": "Groq",
        "env_vars": ("GROQ_API_KEY",),
        "docs_url": "https://console.groq.com/keys",
        "setup_hint": "Set GROQ_API_KEY for fast inference APIs.",
        "unlocks": ("Groq-hosted models", "Low-latency API"),
    },
)


def build_connections_report(environ: dict | None = None) -> dict:
    env_rows = {r["name"]: r for r in inspect_env(environ=environ)}
    items: list[dict] = []
    for conn in CONNECTIONS:
        present = any(env_rows.get(name, {}).get("present") for name in conn["env_vars"])
        items.append(
            {
                "key": conn["key"],
                "name": conn["name"],
                "present": present,
                "env_vars": list(conn["env_vars"]),
                "docs_url": conn["docs_url"],
                "setup_hint": conn["setup_hint"],
                "unlocks": list(conn["unlocks"]),
            }
        )
    connected = sum(1 for i in items if i["present"])
    return {
        "connections": items,
        "connected_count": connected,
        "total": len(items),
        "note": "Presence only — secret values are never shown.",
    }
