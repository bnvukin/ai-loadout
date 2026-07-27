"""Layer 6 — VS Code / Cursor configuration generation."""

from __future__ import annotations

from .config import apply, preview
from .extensions import extension_install_command

__all__ = ["preview", "apply", "extension_install_command"]
