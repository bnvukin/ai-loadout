"""Offline status report for CLI and dashboard."""

from __future__ import annotations

from typing import Callable

from .cache import list_cache
from .connectivity import check_connectivity

OFFLINE_CAPABILITIES = (
    "Machine scan and health check",
    "Config discovery and preview (VS Code, Continue, agents)",
    "Backup and restore snapshots",
    "Benchmark (local CPU/disk; inference needs Ollama locally)",
    "Diagnostics bundle",
    "Cached installer reuse (when present in ~/.ai-loadout/cache/)",
)

NETWORK_ONLY = (
    "Direct downloads (unless cached)",
    "Model pulls (ollama pull)",
    "PyPI self-update check",
    "Live version probes",
)


def build_offline_report(*, connectivity_fn: Callable[..., dict] | None = None) -> dict:
    probe = connectivity_fn or check_connectivity
    connectivity = probe()
    cache = list_cache()
    return {
        "online": connectivity.get("online", False),
        "connectivity": connectivity,
        "cache_count": len(cache),
        "cache_entries": cache,
        "works_offline": list(OFFLINE_CAPABILITIES),
        "needs_network": list(NETWORK_ONLY),
        "note": (
            "Loadout degrades gracefully offline. Network actions are blocked with a clear "
            "reason instead of hanging."
        ),
    }
