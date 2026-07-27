"""The AI Doctor: symptom -> human explanation, fix, why it matters, restart scope.

Kept as data so it is easy to review and extend. ``explain`` renders one issue; the
checker attaches these to the issues it finds.
"""

from __future__ import annotations

# key -> template. {ctx} placeholders are filled from the issue context.
EXPLANATIONS: dict[str, dict] = {
    "ollama-not-running": {
        "title": "Ollama is installed but not responding",
        "explanation": (
            "The Ollama binary is installed but nothing is listening on port 11434, so "
            "apps that expect a local model server (Continue, Open WebUI, your agents) "
            "will fail to connect."
        ),
        "fix": "Start the Ollama server: run `ollama serve` (or launch the Ollama app).",
        "why": "Local inference and any tool pointed at http://localhost:11434 depend on it.",
        "restart": "none",
        "fixable": True,
    },
    "docker-not-running": {
        "title": "Docker is installed but the daemon isn't running",
        "explanation": (
            "Docker is present but `docker info` failed, so containerized stacks "
            "(Open WebUI, vLLM, databases) can't start."
        ),
        "fix": "Start Docker Desktop (or `sudo systemctl start docker` on Linux).",
        "why": "Any container-based part of your stack needs the daemon up.",
        "restart": "docker",
        "fixable": True,
    },
    "disk-low": {
        "title": "Low free disk space",
        "explanation": (
            "Only {free} GB is free on your primary drive. Model downloads are several GB "
            "each and may fail or leave partial files."
        ),
        "fix": "Free up space or point OLLAMA_MODELS to a larger drive.",
        "why": "Downloads and caches need headroom; a full disk breaks installs.",
        "restart": "none",
        "fixable": False,
    },
    "offline": {
        "title": "No internet connection detected",
        "explanation": (
            "Loadout couldn't reach the internet, so it can't download tools or models. "
            "Everything already installed still works offline."
        ),
        "fix": "Reconnect to a network, then re-run the scan.",
        "why": "Installing/updating anything new requires connectivity.",
        "restart": "none",
        "fixable": False,
    },
    "update-available": {
        "title": "{name}: update available",
        "explanation": "{name} {version} is older than the recommended {min_version}.",
        "fix": "Update {name} (Loadout can do this from the Components page).",
        "why": "Newer versions bring fixes and compatibility with current tooling.",
        "restart": "none",
        "fixable": True,
    },
    "cpu-only": {
        "title": "No discrete GPU: inference will be CPU-bound",
        "explanation": (
            "No usable GPU was detected, so models run on the CPU. That's fine for small "
            "models but larger ones will be slow."
        ),
        "fix": "Prefer the models Loadout marks as 'Fastest' for your machine.",
        "why": "Right-sizing the model keeps responses snappy on CPU-only machines.",
        "restart": "none",
        "fixable": False,
    },
    "missing-recommended": {
        "title": "{name} is recommended but not installed",
        "explanation": "{name} is part of a healthy AI workstation and isn't installed yet.",
        "fix": "Install {name} from the plan or the Components page.",
        "why": "{note}",
        "restart": "none",
        "fixable": True,
    },
    "path-duplicates": {
        "title": "Duplicate PATH entries detected",
        "explanation": (
            "Your PATH contains {count} duplicate entries. This can slow down tool lookup "
            "and confuse which binary runs first."
        ),
        "fix": "Run the PATH dedupe repair (backs up your PATH first).",
        "why": "A clean PATH helps Loadout and your shell find the right tools.",
        "restart": "terminal",
        "fixable": True,
    },
}


def explain(key: str, context: dict | None = None) -> dict:
    """Return a rendered explanation dict for an issue key."""

    context = context or {}
    template = EXPLANATIONS.get(key)
    if not template:
        return {
            "title": context.get("title", key),
            "explanation": context.get("detail", ""),
            "fix": "",
            "why": "",
            "restart": "none",
            "fixable": False,
        }

    def fmt(value: str) -> str:
        try:
            return value.format(**context)
        except (KeyError, IndexError):
            return value

    return {
        "title": fmt(template["title"]),
        "explanation": fmt(template["explanation"]),
        "fix": fmt(template["fix"]),
        "why": fmt(template["why"]),
        "restart": template["restart"],
        "fixable": template["fixable"],
    }
