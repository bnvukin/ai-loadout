"""Turn a profile (+ capabilities) into an ordered, dry-run install plan.

The planner is **read-only**: it reconciles what a profile *wants* against what the
digital twin *already has*, and emits a list of steps (install / upgrade / pull / skip /
manual) with the exact command that would run under the machine's package manager.
Nothing is executed here -- that is the orchestrator's job, gated by explicit consent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.lifecycle import PRESENT_STATES, ComponentState
from ..core.state import StateStore
from ..deps import registry as deps_registry
from ..deps.managers import available_managers, preferred_manager
from ..models import catalog as model_catalog
from ..profiles.registry import CAPABILITY_REQUIREMENTS, Profile
from ..profiles.registry import by_key as profile_by_key
from ..runtimes import registry as rt_registry
from ..util import proc

# Stable ordering so a plan reads like a sensible install sequence.
_DEP_ORDER = [
    "git",
    "python",
    "node",
    "npm",
    "pnpm",
    "uv",
    "docker",
    "powershell",
    "wsl",
    "cuda",
    "vsbuildtools",
    "winget",
    "choco",
    "brew",
]
_RT_ORDER = [
    "ollama",
    "vscode",
    "continue",
    "cursor",
    "open-webui",
    "lmstudio",
    "anythingllm",
    "claude-code",
    "codex-cli",
    "gemini-cli",
    "opencode",
]

_CMD_TEMPLATES = {
    "winget": "winget install --id {id} -e --source winget",
    "choco": "choco install {id} -y",
    "scoop": "scoop install {id}",
    "brew": "brew install {id}",
    "apt": "sudo apt-get install -y {id}",
    "dnf": "sudo dnf install -y {id}",
    "pacman": "sudo pacman -S --noconfirm {id}",
    "npm": "npm install -g {id}",
    "pip": "pip install {id}",
}


@dataclass
class PlanStep:
    key: str
    name: str
    kind: str  # dependency | runtime | model
    action: str  # install | upgrade | pull | skip | manual
    reason: str = ""
    manager: str | None = None
    command: str | None = None
    current_state: str = "missing"
    optional: bool = False

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "name": self.name,
            "kind": self.kind,
            "action": self.action,
            "reason": self.reason,
            "manager": self.manager,
            "command": self.command,
            "current_state": self.current_state,
            "optional": self.optional,
        }


@dataclass
class InstallPlan:
    profile: str | None
    capabilities: list[str] = field(default_factory=list)
    steps: list[PlanStep] = field(default_factory=list)

    def summary(self) -> dict:
        counts: dict[str, int] = {}
        for step in self.steps:
            counts[step.action] = counts.get(step.action, 0) + 1
        return counts

    def to_dict(self) -> dict:
        return {
            "profile": self.profile,
            "capabilities": list(self.capabilities),
            "summary": self.summary(),
            "steps": [s.to_dict() for s in self.steps],
        }


def _family(store: StateStore) -> str:
    if store.hardware and store.hardware.os_family:
        return store.hardware.os_family
    from ..detect.system import os_family

    return os_family()


def _cmd(manager: str | None, pkg_id: str | None) -> str | None:
    if not manager or not pkg_id:
        return None
    template = _CMD_TEMPLATES.get(manager)
    return template.format(id=pkg_id) if template else None


def _merge_requirements(profile: Profile | None, capabilities: list[str]) -> dict[str, list[str]]:
    deps: list[str] = list(profile.deps) if profile else []
    runtimes: list[str] = list(profile.runtimes) if profile else []
    models: list[str] = list(profile.models) if profile else []
    for cap in capabilities:
        req = CAPABILITY_REQUIREMENTS.get(cap, {})
        for key in req.get("deps", ()):  # keep order, avoid dupes
            if key not in deps:
                deps.append(key)
        for key in req.get("runtimes", ()):
            if key not in runtimes:
                runtimes.append(key)
    deps.sort(key=lambda k: _DEP_ORDER.index(k) if k in _DEP_ORDER else 999)
    runtimes.sort(key=lambda k: _RT_ORDER.index(k) if k in _RT_ORDER else 999)
    return {"deps": deps, "runtimes": runtimes, "models": models}


def _action_for_state(state: ComponentState | None) -> str:
    if state is None or state in (ComponentState.MISSING, ComponentState.UNKNOWN):
        return "install"
    if state == ComponentState.NEEDS_UPDATE:
        return "upgrade"
    if state in PRESENT_STATES:
        return "skip"
    return "install"


def _dep_step(store: StateStore, key: str, family: str, managers: list[str]) -> PlanStep | None:
    dep = deps_registry.by_key(key)
    if dep is None or not dep.applies_to(family):
        return None
    comp = store.get_component(key)
    state = comp.state if comp else None
    action = _action_for_state(state)
    step = PlanStep(
        key=key,
        name=dep.name,
        kind="dependency",
        action=action,
        current_state=str(state) if state else "missing",
        optional=dep.optional,
    )
    if action in ("install", "upgrade"):
        manager = preferred_manager(family) if managers else None
        pkg_id = dep.install_id(manager) if manager else None
        if dep.special or not pkg_id:
            step.action = "manual"
            step.reason = dep.note or "Install manually (no package id for this manager)."
        else:
            step.manager = manager
            step.command = _cmd(manager, pkg_id)
            step.reason = "Missing" if action == "install" else "Update available"
    else:
        step.reason = "Already present"
    return step


def _pick_runtime_manager(
    runtime, family: str, managers: list[str]
) -> tuple[str | None, str | None]:
    native = preferred_manager(family)
    order = [native, "npm", "pip", "brew", "winget", "choco"]
    for manager in order:
        if not manager or manager not in managers:
            continue
        pkg_id = runtime.install_id(manager)
        if pkg_id:
            return manager, pkg_id
    # npm/pip ids are usable whenever node/python exist even if not "package managers".
    for manager in ("npm", "pip"):
        pkg_id = runtime.install_id(manager)
        if pkg_id and proc.which(manager):
            return manager, pkg_id
    return None, None


def _runtime_step(store: StateStore, key: str, family: str, managers: list[str]) -> PlanStep | None:
    runtime = rt_registry.by_key(key)
    if runtime is None:
        return None
    comp = store.get_component(key)
    state = comp.state if comp else None
    action = _action_for_state(state)
    step = PlanStep(
        key=key,
        name=runtime.name,
        kind="runtime",
        action=action,
        current_state=str(state) if state else "missing",
        optional=runtime.optional,
    )
    if action in ("install", "upgrade"):
        manager, pkg_id = _pick_runtime_manager(runtime, family, managers)
        if not pkg_id:
            step.action = "manual"
            step.reason = runtime.note or "Install from the vendor (no package id known)."
        else:
            step.manager = manager
            step.command = _cmd(manager, pkg_id)
            step.reason = "Missing" if action == "install" else "Update available"
    else:
        step.reason = "Already present"
    return step


def _installed_model_tags(store: StateStore) -> set[str]:
    tags = set()
    for m in store.models():
        tags.add(m.name)
        tags.add(m.name.split(":")[0])
    return tags


def _pick_model(store: StateStore, candidates: list[str]) -> str | None:
    """Choose the best-fitting candidate model for this machine (best-first list)."""

    if not candidates:
        return None
    fit_by_key: dict[str, str] = {}
    if store.hardware:
        from ..models.recommend import recommend

        for rec in recommend(store.hardware):
            fit_by_key[rec.spec.key] = rec.fit
    for key in candidates:
        if fit_by_key.get(key, "fits") in ("fits", "tight"):
            return key
    return candidates[-1]  # nothing fits comfortably -> smallest/last candidate


def _model_step(store: StateStore, key: str) -> PlanStep | None:
    spec = model_catalog.by_key(key)
    if spec is None:
        return None
    installed = _installed_model_tags(store)
    present = spec.tag in installed or spec.tag.split(":")[0] in installed
    step = PlanStep(
        key=key,
        name=spec.name,
        kind="model",
        action="skip" if present else "pull",
        current_state="downloaded" if present else "missing",
        optional=False,
    )
    if present:
        step.reason = "Already downloaded"
    else:
        step.command = f"ollama pull {spec.tag}"
        step.manager = "ollama"
        step.reason = spec.best_for
    return step


def build_plan(
    store: StateStore,
    profile_key: str | None = None,
    capabilities: list[str] | None = None,
    *,
    include_models: bool = True,
) -> InstallPlan:
    profile = profile_by_key(profile_key) if profile_key else None
    caps = list(capabilities or [])
    if profile:
        caps = list(dict.fromkeys([*profile.capabilities, *caps]))
    family = _family(store)
    managers = available_managers()
    reqs = _merge_requirements(profile, caps)

    steps: list[PlanStep] = []
    for key in reqs["deps"]:
        step = _dep_step(store, key, family, managers)
        if step:
            steps.append(step)
    for key in reqs["runtimes"]:
        step = _runtime_step(store, key, family, managers)
        if step:
            steps.append(step)
    if include_models and reqs["models"]:
        chosen = _pick_model(store, reqs["models"])
        if chosen:
            step = _model_step(store, chosen)
            if step:
                steps.append(step)

    return InstallPlan(profile=profile.key if profile else None, capabilities=caps, steps=steps)


def build_plan_from_scratch(
    store: StateStore,
    profile_key: str | None = None,
    capabilities: list[str] | None = None,
    *,
    include_models: bool = True,
) -> InstallPlan:
    """Ensure the twin has been detected once, then build the plan against real state."""

    if not store.components():
        from ..deps.detect import detect_all as detect_deps
        from ..detect.system import scan
        from ..runtimes.detect import detect_all as detect_runtimes

        if store.hardware is None:
            scan(store)
        detect_deps(store)
        detect_runtimes(store)
    return build_plan(store, profile_key, capabilities, include_models=include_models)
