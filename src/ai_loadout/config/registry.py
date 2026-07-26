"""Registry of configuration targets the Config Center knows how to find and read.

Each :class:`ConfigTarget` describes a well-known config file (Continue, VS Code, Git,
Docker, shell profiles ...) with per-OS path templates and a :class:`TrustLevel` that
drives how dangerous it is to edit. Templates use ``{home}``, ``{appdata}``,
``{localappdata}``, ``{xdg_config}`` and ``{documents}`` placeholders resolved in
``discover.py``. We only list *documented* paths -- Loadout never invents locations.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.lifecycle import TrustLevel


@dataclass(frozen=True)
class ConfigTarget:
    key: str
    name: str
    owner: str  # component key this config belongs to (e.g. "continue", "vscode")
    fmt: str = "text"  # json | jsonc | yaml | toml | ini | text
    trust: TrustLevel = TrustLevel.SAFE
    description: str = ""
    windows: tuple[str, ...] = ()
    macos: tuple[str, ...] = ()
    linux: tuple[str, ...] = ()
    secret: bool = False  # whole file may contain credentials -> redact aggressively
    optional: bool = True
    note: str = ""

    def paths_for(self, family: str) -> tuple[str, ...]:
        return getattr(self, family, ()) or ()


# Curated, documented config locations. Order of templates = search priority.
CONFIG_TARGETS: list[ConfigTarget] = [
    ConfigTarget(
        "continue",
        "Continue config",
        owner="continue",
        fmt="json",
        trust=TrustLevel.SAFE,
        description="Continue (VS Code AI assistant) model + provider config.",
        windows=("{home}/.continue/config.yaml", "{home}/.continue/config.json"),
        macos=("{home}/.continue/config.yaml", "{home}/.continue/config.json"),
        linux=("{home}/.continue/config.yaml", "{home}/.continue/config.json"),
    ),
    ConfigTarget(
        "vscode-settings",
        "VS Code settings",
        owner="vscode",
        fmt="jsonc",
        trust=TrustLevel.SAFE,
        description="VS Code user settings (theme, extensions behaviour, telemetry).",
        windows=("{appdata}/Code/User/settings.json",),
        macos=("{home}/Library/Application Support/Code/User/settings.json",),
        linux=("{xdg_config}/Code/User/settings.json",),
    ),
    ConfigTarget(
        "cursor-settings",
        "Cursor settings",
        owner="cursor",
        fmt="jsonc",
        trust=TrustLevel.SAFE,
        description="Cursor editor user settings.",
        windows=("{appdata}/Cursor/User/settings.json",),
        macos=("{home}/Library/Application Support/Cursor/User/settings.json",),
        linux=("{xdg_config}/Cursor/User/settings.json",),
    ),
    ConfigTarget(
        "git",
        "Git global config",
        owner="git",
        fmt="ini",
        trust=TrustLevel.ADVANCED,
        description="Global Git identity, aliases, and signing settings.",
        windows=("{home}/.gitconfig",),
        macos=("{home}/.gitconfig",),
        linux=("{home}/.gitconfig",),
    ),
    ConfigTarget(
        "docker",
        "Docker CLI config",
        owner="docker",
        fmt="json",
        trust=TrustLevel.ADVANCED,
        description="Docker CLI config (may contain registry auth tokens).",
        secret=True,
        windows=("{home}/.docker/config.json",),
        macos=("{home}/.docker/config.json",),
        linux=("{home}/.docker/config.json",),
    ),
    ConfigTarget(
        "npm",
        "npm config (.npmrc)",
        owner="node",
        fmt="ini",
        trust=TrustLevel.ADVANCED,
        description="npm registry + auth tokens.",
        secret=True,
        windows=("{home}/.npmrc",),
        macos=("{home}/.npmrc",),
        linux=("{home}/.npmrc",),
    ),
    ConfigTarget(
        "pip",
        "pip config",
        owner="python",
        fmt="ini",
        trust=TrustLevel.SAFE,
        description="pip index URL and install defaults.",
        windows=("{appdata}/pip/pip.ini",),
        macos=("{home}/.config/pip/pip.conf",),
        linux=("{xdg_config}/pip/pip.conf",),
    ),
    ConfigTarget(
        "huggingface-token",
        "Hugging Face token",
        owner="huggingface",
        fmt="text",
        trust=TrustLevel.EXPERT,
        description="Hugging Face access token used to pull gated models.",
        secret=True,
        windows=("{home}/.cache/huggingface/token",),
        macos=("{home}/.cache/huggingface/token",),
        linux=("{home}/.cache/huggingface/token",),
    ),
    ConfigTarget(
        "shell-profile",
        "Shell profile (PATH)",
        owner="os",
        fmt="text",
        trust=TrustLevel.ADVANCED,
        description="Startup script where PATH and env vars are commonly set.",
        windows=(
            "{documents}/PowerShell/Microsoft.PowerShell_profile.ps1",
            "{documents}/WindowsPowerShell/Microsoft.PowerShell_profile.ps1",
        ),
        macos=("{home}/.zshrc", "{home}/.bash_profile", "{home}/.profile"),
        linux=("{home}/.bashrc", "{home}/.zshrc", "{home}/.profile"),
    ),
]


def targets_for(family: str) -> list[ConfigTarget]:
    return [t for t in CONFIG_TARGETS if t.paths_for(family)]


def by_key(key: str) -> ConfigTarget | None:
    for target in CONFIG_TARGETS:
        if target.key == key:
            return target
    return None
