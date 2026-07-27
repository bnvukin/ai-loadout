"""Build Continue config from detected runtimes/models (no embedded secrets)."""

from __future__ import annotations

from pathlib import Path

from ..config.env import inspect_env
from ..config.merge import merge_fill_gaps
from ..util import yaml_simple

# Continue config.yaml schema used by Continue extension v1.x (stable YAML format).
CONTINUE_SCHEMA = "v1"
CONTINUE_FORMAT = "config.yaml"


def _continue_config_path(home: Path | None = None) -> Path:
    home = home or Path.home()
    yaml_path = home / ".continue" / "config.yaml"
    json_path = home / ".continue" / "config.json"
    if json_path.is_file() and not yaml_path.is_file():
        return json_path
    return yaml_path


def _ollama_models(store) -> list[str]:
    names: list[str] = []
    if store is None:
        return names
    for model in store.models():
        if model.provider == "ollama" or model.name:
            names.append(model.name.split(":")[0] if ":" in model.name else model.name)
    return names


def _provider_models_from_env() -> list[dict]:
    """Cloud providers referenced via env vars — never embed secret values."""

    rows = {r["name"]: r for r in inspect_env()}
    providers: list[dict] = []

    if rows.get("OPENAI_API_KEY", {}).get("present"):
        providers.append(
            {
                "title": "OpenAI (env)",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "apiKey": "${env:OPENAI_API_KEY}",
            }
        )
    if rows.get("ANTHROPIC_API_KEY", {}).get("present"):
        providers.append(
            {
                "title": "Anthropic (env)",
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-latest",
                "apiKey": "${env:ANTHROPIC_API_KEY}",
            }
        )
    if rows.get("GOOGLE_API_KEY", {}).get("present") or rows.get("GEMINI_API_KEY", {}).get(
        "present"
    ):
        providers.append(
            {
                "title": "Google Gemini (env)",
                "provider": "gemini",
                "model": "gemini-1.5-flash",
                "apiKey": "${env:GOOGLE_API_KEY}",
            }
        )
    return providers


def build_config_dict(store=None) -> dict:
    """Structured Continue config — secrets as env placeholders only."""

    models: list[dict] = []
    for tag in _ollama_models(store):
        models.append(
            {
                "title": f"Ollama {tag}",
                "provider": "ollama",
                "model": tag,
            }
        )
    if not models:
        models.append(
            {
                "title": "Ollama (default)",
                "provider": "ollama",
                "model": "llama3.2",
            }
        )
    models.extend(_provider_models_from_env())

    return {
        "name": "Loadout Assistant",
        "schema": CONTINUE_SCHEMA,
        "models": models,
        "tabAutocompleteModel": models[0] if models else {},
        "allowAnonymousTelemetry": False,
    }


def _load_existing(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return yaml_simple.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _render(config: dict, path: Path) -> str:
    if path.suffix == ".json":
        import json

        return json.dumps(config, indent=2, ensure_ascii=False) + "\n"
    return yaml_simple.dumps(config)


def preview(store=None, home: Path | None = None) -> dict:
    path = _continue_config_path(home)
    generated = build_config_dict(store)
    existing = _load_existing(path)
    merged = merge_fill_gaps(existing, generated)
    # Preserve user models: append generated ollama entries not already present
    if "models" in existing and isinstance(existing["models"], list):
        existing_titles = {m.get("title") for m in existing["models"] if isinstance(m, dict)}
        extra = [m for m in generated.get("models", []) if m.get("title") not in existing_titles]
        merged_models = list(existing["models"]) + extra
        merged["models"] = merged_models

    content = _render(merged, path)
    return {
        "ok": True,
        "path": str(path),
        "format": CONTINUE_FORMAT if path.suffix == ".yaml" else "config.json",
        "schema": CONTINUE_SCHEMA,
        "exists": path.is_file(),
        "merged": merged,
        "content": content,
        "detected_ollama_models": _ollama_models(store),
        "env_providers": len(_provider_models_from_env()),
        "note": "API keys use ${env:VAR} placeholders — never written literally.",
    }


def apply(store=None, home: Path | None = None) -> dict:
    from ..config.write_util import write_text_atomic

    plan = preview(store, home)
    if not plan.get("ok"):
        return plan
    path = Path(plan["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    result = write_text_atomic(path, plan["content"])
    if store is not None:
        store.bus.info("Continue config applied", kind="config", target="continue")
    return {"ok": True, "path": str(path), "backup": result.get("backup"), **plan}
