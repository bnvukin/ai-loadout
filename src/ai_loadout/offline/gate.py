"""Gate network-only actions when offline."""

from __future__ import annotations

from typing import Callable

from .connectivity import check_connectivity

NETWORK_ACTIONS = frozenset(
    {
        "download",
        "pull",
        "model_pull",
        "install",
        "upgrade",
        "self_update",
        "pypi_check",
        "extension_install",
    }
)


def offline_block(
    action: str,
    *,
    connectivity_fn: Callable[..., dict] | None = None,
) -> dict | None:
    """Return an error dict when *action* needs network and we are offline; else ``None``."""

    if action not in NETWORK_ACTIONS:
        return None
    probe = connectivity_fn or check_connectivity
    status = probe()
    if status.get("online"):
        return None
    reason = status.get("reason") or "no connectivity"
    return {
        "ok": False,
        "offline": True,
        "blocked": True,
        "action": action,
        "reason": f"Offline — {action} requires network ({reason})",
        "connectivity": status,
    }
