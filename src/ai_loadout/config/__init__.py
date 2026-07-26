"""Config Center - discover, read (redacted), and safely edit the configs that matter.

A unified view over the scattered files and environment variables that decide how an AI
workstation behaves: Continue/VS Code/Cursor settings, Git, Docker, npm/pip, shell
profiles, plus the AI-relevant env vars and PATH. Reads are redacted and read-only;
edits go through :mod:`edit`, are always backed up, and are gated by a trust level.
"""

from .discover import ConfigFile, discover_all, discover_one, read_config
from .edit import EditError, apply_edit, backup_file
from .env import inspect_env, path_summary
from .registry import CONFIG_TARGETS, ConfigTarget

__all__ = [
    "CONFIG_TARGETS",
    "ConfigFile",
    "ConfigTarget",
    "EditError",
    "apply_edit",
    "backup_file",
    "discover_all",
    "discover_one",
    "inspect_env",
    "path_summary",
    "read_config",
]
