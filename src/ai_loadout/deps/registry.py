"""The registry of developer dependencies Loadout knows how to detect and install.

Each entry says how to probe for the tool, a recommended minimum version, which OS
families it applies to, and the package id under each package manager. Install ids only
mean "Loadout knows where to get it" -- nothing is installed without explicit consent.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Dependency:
    key: str
    name: str
    category: str = "dependency"
    command: str = ""  # executable to probe (defaults to key)
    version_args: tuple[str, ...] = ("--version",)
    min_version: str | None = None
    platforms: tuple[str, ...] = ()  # empty = all families
    winget: str | None = None
    choco: str | None = None
    brew: str | None = None
    apt: str | None = None
    optional: bool = False
    special: str | None = None  # "powershell" | "wsl" | "cuda" | "vsbuildtools"
    note: str = ""

    def probe_command(self) -> str:
        return self.command or self.key

    def applies_to(self, family: str) -> bool:
        return not self.platforms or family in self.platforms

    def install_id(self, manager: str) -> str | None:
        return getattr(self, manager, None)


DEPENDENCIES: list[Dependency] = [
    Dependency(
        "git",
        "Git",
        "vcs",
        min_version="2.30",
        winget="Git.Git",
        choco="git",
        brew="git",
        apt="git",
    ),
    Dependency(
        "python",
        "Python",
        "language",
        command="python",
        min_version="3.9",
        winget="Python.Python.3.12",
        choco="python",
        brew="python@3.12",
        apt="python3",
        note="Core language for most AI tooling and MCP servers.",
    ),
    Dependency(
        "node",
        "Node.js",
        "language",
        min_version="18.0",
        winget="OpenJS.NodeJS.LTS",
        choco="nodejs-lts",
        brew="node",
        apt="nodejs",
    ),
    Dependency("npm", "npm", "package-manager", min_version="9.0"),
    Dependency(
        "pnpm",
        "pnpm",
        "package-manager",
        optional=True,
        winget="pnpm.pnpm",
        choco="pnpm",
        brew="pnpm",
    ),
    Dependency(
        "uv",
        "uv",
        "package-manager",
        optional=True,
        winget="astral-sh.uv",
        brew="uv",
        note="Fast Python package/venv manager.",
    ),
    Dependency(
        "docker",
        "Docker",
        "container",
        command="docker",
        version_args=("--version",),
        winget="Docker.DockerDesktop",
        choco="docker-desktop",
        brew="docker",
        optional=True,
        note="Needed for containerized AI stacks (Open WebUI, vLLM, ...).",
    ),
    Dependency(
        "powershell",
        "PowerShell",
        "shell",
        platforms=("windows",),
        optional=True,
        min_version="7.0",
        winget="Microsoft.PowerShell",
        choco="powershell-core",
        special="powershell",
        note="PowerShell 7+ recommended (5.1 ships with Windows).",
    ),
    Dependency(
        "wsl",
        "WSL",
        "platform",
        platforms=("windows",),
        optional=True,
        special="wsl",
        note="Windows Subsystem for Linux (useful for many AI toolchains).",
    ),
    Dependency("winget", "winget", "package-manager", platforms=("windows",)),
    Dependency("choco", "Chocolatey", "package-manager", platforms=("windows",), optional=True),
    Dependency("brew", "Homebrew", "package-manager", platforms=("macos", "linux"), optional=True),
    Dependency(
        "cuda",
        "CUDA Toolkit",
        "gpu",
        command="nvcc",
        version_args=("--version",),
        optional=True,
        special="cuda",
        note="GPU acceleration for local inference/training.",
    ),
    Dependency(
        "vsbuildtools",
        "Visual Studio Build Tools",
        "compiler",
        platforms=("windows",),
        optional=True,
        special="vsbuildtools",
        winget="Microsoft.VisualStudio.2022.BuildTools",
        note="C/C++ build tools some Python wheels compile against.",
    ),
]


def platform_dependencies(family: str) -> list[Dependency]:
    return [d for d in DEPENDENCIES if d.applies_to(family)]


def by_key(key: str) -> Dependency | None:
    for dep in DEPENDENCIES:
        if dep.key == key:
            return dep
    return None
