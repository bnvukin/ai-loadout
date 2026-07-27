"""Local installer/asset cache under ``~/.ai-loadout/cache/``."""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

from ..core import paths

MANIFEST_NAME = "manifest.json"


def cache_dir() -> Path:
    paths.ensure_dirs()
    root = paths.cache_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _manifest_path() -> Path:
    return cache_dir() / MANIFEST_NAME


def _load_manifest() -> dict:
    mp = _manifest_path()
    if not mp.is_file():
        return {"entries": {}}
    try:
        data = json.loads(mp.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("entries"), dict):
            return data
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    return {"entries": {}}


def _save_manifest(data: dict) -> None:
    _manifest_path().write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _cache_filename(url: str) -> str:
    parsed = urlparse(url)
    base = unquote(Path(parsed.path).name) or "asset.bin"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return f"{digest}-{base}"


def lookup_cache(url: str) -> dict | None:
    """Return cache hit metadata + path, or ``None`` on miss."""

    manifest = _load_manifest()
    entry = manifest.get("entries", {}).get(url)
    if not entry:
        return None
    cached_path = Path(entry.get("path", ""))
    if not cached_path.is_file():
        return None
    return {
        "url": url,
        "path": str(cached_path),
        "bytes": entry.get("bytes"),
        "cached_at": entry.get("cached_at"),
        "sha256": entry.get("sha256"),
    }


def record_in_cache(url: str, source: str | Path, *, sha256: str | None = None) -> dict:
    """Copy *source* into the cache and update the manifest."""

    src = Path(source)
    if not src.is_file():
        raise FileNotFoundError(str(src))

    dest = cache_dir() / _cache_filename(url)
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)

    manifest = _load_manifest()
    manifest.setdefault("entries", {})[url] = {
        "path": str(dest),
        "bytes": dest.stat().st_size,
        "cached_at": time.time(),
        "sha256": sha256,
    }
    _save_manifest(manifest)
    return lookup_cache(url) or {"url": url, "path": str(dest)}


def list_cache() -> list[dict]:
    manifest = _load_manifest()
    out: list[dict] = []
    for url, entry in sorted(manifest.get("entries", {}).items()):
        path = Path(entry.get("path", ""))
        if path.is_file():
            out.append(
                {
                    "url": url,
                    "path": str(path),
                    "bytes": entry.get("bytes", path.stat().st_size),
                    "cached_at": entry.get("cached_at"),
                    "sha256": entry.get("sha256"),
                }
            )
    return out
