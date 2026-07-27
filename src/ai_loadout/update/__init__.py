"""Layer 16 — Update checks for Loadout and managed components."""

from __future__ import annotations

from .report import build_update_report
from .self_check import check_self_update

__all__ = ["check_self_update", "build_update_report"]
