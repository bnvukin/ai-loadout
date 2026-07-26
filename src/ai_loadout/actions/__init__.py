"""Phase 2 -- the action engine: build, run, and repair.

This package turns the read-only advisor into something that can *act*: it builds the
exact command for an install/upgrade/model-pull, runs it while streaming output to the
event bus and ``install.log``, re-detects the component afterwards, and offers one-click
repairs for common health issues. All mutating calls default to explicit, logged runs --
nothing here executes without a caller asking for it.
"""

from __future__ import annotations

from .advice import component_advice
from .commands import ActionCommand, build_command
from .repair import REPAIR_ACTIONS, repair
from .runner import preview, refresh_local_models, rescan_component, run_action

__all__ = [
    "ActionCommand",
    "build_command",
    "preview",
    "run_action",
    "rescan_component",
    "refresh_local_models",
    "repair",
    "REPAIR_ACTIONS",
    "component_advice",
]
