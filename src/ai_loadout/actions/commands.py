"""Build the concrete argv for a mutating action (install / upgrade / pull).

Everything here returns an :class:`ActionCommand` (an ``argv`` list plus metadata) --
nothing is executed. The runner decides whether to actually run it. Keeping command
construction separate makes it unit-testable and keeps the "what would run" contract
identical between the dry-run planner and the real executor.
"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass, field

from ..deps import registry as deps_registry
from ..deps.managers import available_managers, preferred_manager
from ..models import catalog as model_catalog
from ..runtimes import registry as rt_registry

# Package-manager templates as argv (no shell). ``{id}`` is substituted per package.
_INSTALL = {
    "winget": [
        "winget",
        "install",
        "--id",
        "{id}",
        "-e",
        "--source",
        "winget",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ],
    "choco": ["choco", "install", "{id}", "-y"],
    "scoop": ["scoop", "install", "{id}"],
    "brew": ["brew", "install", "{id}"],
    "apt": ["sudo", "apt-get", "install", "-y", "{id}"],
    "dnf": ["sudo", "dnf", "install", "-y", "{id}"],
    "pacman": ["sudo", "pacman", "-S", "--noconfirm", "{id}"],
    "npm": ["npm", "install", "-g", "{id}"],
    "pip": [sys.executable, "-m", "pip", "install", "{id}"],
}
_UPGRADE = {
    "winget": [
        "winget",
        "upgrade",
        "--id",
        "{id}",
        "-e",
        "--source",
        "winget",
        "--accept-package-agreements",
        "--accept-source-agreements",
    ],
    "choco": ["choco", "upgrade", "{id}", "-y"],
    "scoop": ["scoop", "update", "{id}"],
    "brew": ["brew", "upgrade", "{id}"],
    "apt": ["sudo", "apt-get", "install", "-y", "--only-upgrade", "{id}"],
    "dnf": ["sudo", "dnf", "upgrade", "-y", "{id}"],
    "pacman": ["sudo", "pacman", "-S", "--noconfirm", "{id}"],
    "npm": ["npm", "install", "-g", "{id}"],
    "pip": [sys.executable, "-m", "pip", "install", "--upgrade", "{id}"],
}

# Managers that typically need elevation for a machine-wide install.
_ELEVATED = {"winget", "choco", "apt", "dnf", "pacman"}


@dataclass
class ActionCommand:
    key: str
    name: str
    kind: str  # dependency | runtime | model
    action: str  # install | upgrade | pull
    manager: str | None = None
    argv: list[str] = field(default_factory=list)
    display: str = ""  # human-readable command
    needs_admin: bool = False
    ok: bool = True
    reason: str = ""  # why we can't build a command, when ok is False

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "kind": self.kind,
            "action": self.action,
            "manager": self.manager,
            "argv": list(self.argv),
            "display": self.display,
            "needs_admin": self.needs_admin,
            "ok": self.ok,
            "reason": self.reason,
        }


def _normalize_argv(argv: list[str]) -> list[str]:
    """Make argv runnable with ``shell=False`` across platforms.

    On Windows many managers are ``.cmd``/``.bat`` shims (npm, choco, sometimes scoop)
    which ``CreateProcess`` cannot launch directly, so we resolve and wrap them with
    ``cmd /c``. Real ``.exe`` tools (winget) are used as-is.
    """

    if not argv:
        return argv
    exe = argv[0]
    resolved = shutil.which(exe) or exe
    if os.name == "nt" and resolved.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", resolved, *argv[1:]]
    return [resolved, *argv[1:]]


def _render(template: list[str], pkg_id: str) -> list[str]:
    return [part.replace("{id}", pkg_id) for part in template]


def _pick_manager_for(install_id_fn, available: list[str], family: str, order: list[str]):
    for manager in order:
        if manager in available and install_id_fn(manager):
            return manager, install_id_fn(manager)
    # npm/pip work whenever their tool is present, even if not "package managers".
    for manager in ("npm", "pip"):
        if install_id_fn(manager) and (shutil.which(manager) or manager == "pip"):
            return manager, install_id_fn(manager)
    return None, None


def build_command(key: str, kind: str, action: str, family: str | None = None) -> ActionCommand:
    """Build an :class:`ActionCommand` for a component/model + action."""

    if kind == "model" or action == "pull":
        return _model_command(key)

    available = available_managers()
    fam = family or _current_family()
    templates = _UPGRADE if action == "upgrade" else _INSTALL

    if kind == "dependency":
        dep = deps_registry.by_key(key)
        if dep is None:
            return ActionCommand(key, key, kind, action, ok=False, reason="unknown dependency")
        native = preferred_manager(fam)
        order = [native] if native else []
        order += [
            m
            for m in ("winget", "choco", "scoop", "brew", "apt", "dnf", "pacman")
            if m not in order
        ]
        manager, pkg_id = _pick_manager_for(dep.install_id, available, fam, order)
        name = dep.name
        # wsl/cuda carry no package id, so they fall through to the "manual" branch below;
        # PowerShell / Build Tools do have a winget id and are installable.
        if dep.special in {"wsl", "cuda"} and not pkg_id:
            return ActionCommand(
                key,
                name,
                kind,
                action,
                ok=False,
                reason=f"{name} needs manual setup -- see the linked docs.",
            )
    else:  # runtime / editor / connection
        runtime = rt_registry.by_key(key)
        if runtime is None:
            return ActionCommand(key, key, kind, action, ok=False, reason="unknown runtime")
        native = preferred_manager(fam)
        order = [native] if native else []
        order += [m for m in ("winget", "choco", "brew", "npm", "pip") if m not in order]
        manager, pkg_id = _pick_manager_for(runtime.install_id, available, fam, order)
        name = runtime.name

    if not manager or not pkg_id:
        return ActionCommand(
            key,
            name,
            kind,
            action,
            ok=False,
            reason="No package id for an available manager -- install manually.",
        )

    template = templates.get(manager)
    if not template:
        return ActionCommand(
            key, name, kind, action, ok=False, reason=f"No {action} template for {manager}."
        )
    argv = _normalize_argv(_render(template, pkg_id))
    display = " ".join(_render(template, pkg_id))
    return ActionCommand(
        key=key,
        name=name,
        kind=kind,
        action=action,
        manager=manager,
        argv=argv,
        display=display,
        needs_admin=manager in _ELEVATED,
    )


def _model_command(key: str) -> ActionCommand:
    spec = model_catalog.by_key(key)
    # Allow passing a raw ollama tag too (e.g. "llama3.1:8b").
    tag = spec.tag if spec else key
    name = spec.name if spec else key
    ollama = shutil.which("ollama")
    if not ollama:
        return ActionCommand(
            key,
            name,
            "model",
            "pull",
            ok=False,
            reason="Ollama is not installed -- install it first.",
        )
    return ActionCommand(
        key=key,
        name=name,
        kind="model",
        action="pull",
        manager="ollama",
        argv=[ollama, "pull", tag],
        display=f"ollama pull {tag}",
    )


def _current_family() -> str:
    from ..detect.system import os_family

    return os_family()
