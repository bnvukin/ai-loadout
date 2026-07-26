"""Inspect environment variables and PATH -- the other half of the Config Center.

A lot of "why is my AI setup broken?" comes down to env vars (``OLLAMA_HOST``,
``CUDA_PATH``, proxy settings) or a messy ``PATH`` (missing dirs, duplicates, a stale
Python shadowing the real one). This module reports both, redacting anything secret.
"""

from __future__ import annotations

import os

from .redact import looks_secret, mask

# AI-relevant environment variables worth surfacing, grouped loosely by concern.
KEY_ENV_VARS: tuple[str, ...] = (
    # local runtimes
    "OLLAMA_HOST",
    "OLLAMA_MODELS",
    "OLLAMA_KEEP_ALIVE",
    "LM_STUDIO_HOME",
    # model hubs / caches
    "HF_HOME",
    "HF_TOKEN",
    "HUGGINGFACE_TOKEN",
    "TRANSFORMERS_CACHE",
    # provider credentials (always redacted)
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "MISTRAL_API_KEY",
    # gpu / build
    "CUDA_PATH",
    "CUDA_HOME",
    "LD_LIBRARY_PATH",
    # python / node
    "PYTHONPATH",
    "VIRTUAL_ENV",
    "CONDA_PREFIX",
    "NODE_OPTIONS",
    "NPM_CONFIG_PREFIX",
    # docker / network
    "DOCKER_HOST",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
)


def _windows() -> bool:
    return os.name == "nt"


def inspect_env(names: tuple[str, ...] = KEY_ENV_VARS, environ: dict | None = None) -> list[dict]:
    """Report presence + (redacted) value for each interesting env var."""

    env = os.environ if environ is None else environ
    out: list[dict] = []
    for name in names:
        raw = env.get(name)
        present = raw is not None and raw != ""
        secret = looks_secret(name)
        if not present:
            value = None
        elif secret:
            value = mask(raw)
        else:
            value = raw
        out.append({"name": name, "present": present, "secret": secret, "value": value})
    return out


def inspect_all_env(environ: dict | None = None) -> list[dict]:
    """Report *every* environment variable (sorted), redacting anything secret.

    The curated :func:`inspect_env` answers "are my AI vars set?"; this answers the user's
    ask to just see everything so they can judge relevance themselves. Secret-looking names
    are masked so the list is safe to screenshot.
    """

    env = os.environ if environ is None else environ
    known = set(KEY_ENV_VARS)
    out: list[dict] = []
    for name in sorted(env.keys(), key=str.lower):
        raw = env.get(name, "")
        secret = looks_secret(name)
        out.append(
            {
                "name": name,
                "present": raw != "",
                "secret": secret,
                "value": mask(raw) if (secret and raw) else raw,
                "known": name in known,
            }
        )
    return out


def path_entries(environ: dict | None = None) -> list[dict]:
    """Split PATH into entries and flag missing directories + duplicates."""

    env = os.environ if environ is None else environ
    raw = env.get("PATH", "")
    entries = [e for e in raw.split(os.pathsep) if e.strip()]
    seen: set[str] = set()
    out: list[dict] = []
    for entry in entries:
        norm = os.path.normpath(entry)
        key = norm.lower() if _windows() else norm
        out.append(
            {
                "path": entry,
                "exists": os.path.isdir(entry),
                "duplicate": key in seen,
            }
        )
        seen.add(key)
    return out


def path_summary(environ: dict | None = None) -> dict:
    entries = path_entries(environ)
    missing = [e["path"] for e in entries if not e["exists"]]
    duplicates = [e["path"] for e in entries if e["duplicate"]]
    return {
        "count": len(entries),
        "missing": missing,
        "duplicates": duplicates,
        "entries": entries,
    }
