"""Recommended VS Code / Cursor settings for AI development."""

from __future__ import annotations

RECOMMENDED_SETTINGS: dict = {
    "editor.formatOnSave": True,
    "editor.tabSize": 2,
    "files.trimTrailingWhitespace": True,
    "python.analysis.typeCheckingMode": "basic",
    "python.terminal.activateEnvironment": True,
    "continue.telemetryEnabled": False,
    "git.autofetch": True,
    "terminal.integrated.defaultProfile.windows": "PowerShell",
}

OPTIONAL_KEYBINDINGS: dict = {
    "key": "ctrl+l",
    "command": "continue.focusContinueInput",
    "when": "editorTextFocus",
}

OPTIONAL_TASKS: dict = {
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Loadout: scan machine",
            "type": "shell",
            "command": "loadout scan",
            "problemMatcher": [],
        },
    ],
}
