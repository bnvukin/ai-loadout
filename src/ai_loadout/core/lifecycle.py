"""The single component lifecycle shared by every managed thing in Loadout.

Git, Python, Docker, Ollama, VS Code, a local model, a config file -- they all move
through the same states, which is what lets the dashboard render everything uniformly.
"""

from __future__ import annotations

from enum import Enum


class ComponentState(str, Enum):
    """Lifecycle state of a managed component.

    The "happy path" reads: MISSING -> INSTALLING -> INSTALLED -> CONFIGURING ->
    CONFIGURED -> VERIFYING -> VERIFIED -> (BENCHMARKING -> BENCHMARKED) -> HEALTHY,
    with NEEDS_UPDATE / REPAIRING / FAILED as off-ramps.
    """

    UNKNOWN = "unknown"
    MISSING = "missing"
    DETECTED = "detected"
    INSTALLING = "installing"
    INSTALLED = "installed"
    CONFIGURING = "configuring"
    CONFIGURED = "configured"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    BENCHMARKING = "benchmarking"
    BENCHMARKED = "benchmarked"
    HEALTHY = "healthy"
    NEEDS_UPDATE = "needs_update"
    REPAIRING = "repairing"
    FAILED = "failed"
    DISABLED = "disabled"

    def __str__(self) -> str:  # keep JSON/logs clean ("healthy", not "ComponentState.HEALTHY")
        return self.value


# States that mean the component is present and usable.
PRESENT_STATES = frozenset(
    {
        ComponentState.DETECTED,
        ComponentState.INSTALLED,
        ComponentState.CONFIGURED,
        ComponentState.VERIFIED,
        ComponentState.BENCHMARKED,
        ComponentState.HEALTHY,
        ComponentState.NEEDS_UPDATE,
    }
)

# States that represent work in progress (dashboard shows a spinner).
BUSY_STATES = frozenset(
    {
        ComponentState.INSTALLING,
        ComponentState.CONFIGURING,
        ComponentState.VERIFYING,
        ComponentState.BENCHMARKING,
        ComponentState.REPAIRING,
    }
)


class Health(str, Enum):
    """Traffic-light health used across cards and the dependency graph."""

    GREEN = "green"  # healthy
    YELLOW = "yellow"  # degraded / needs attention (e.g. a dependency is unhealthy)
    RED = "red"  # broken / failed
    GRAY = "gray"  # unknown / not applicable / not installed

    def __str__(self) -> str:
        return self.value


# Score used to compute an overall health percentage.
HEALTH_SCORE = {Health.GREEN: 1.0, Health.YELLOW: 0.5, Health.RED: 0.0, Health.GRAY: None}


class TrustLevel(str, Enum):
    """How dangerous it is to edit a config/target -- drives the confirmation UX."""

    SAFE = "safe"  # 🟢 editable immediately (theme, temperature, extensions)
    ADVANCED = "advanced"  # 🟡 confirmation required (PATH, env vars, Docker, CUDA)
    EXPERT = "expert"  # 🔴 type EDIT to continue (registry, hosts, certs)

    def __str__(self) -> str:
        return self.value


class Category(str, Enum):
    """Grouping used by the dashboard and Config Center filters."""

    HARDWARE = "hardware"
    OS = "os"
    DEPENDENCY = "dependency"
    RUNTIME = "runtime"
    EDITOR = "editor"
    MODEL = "model"
    CONFIG = "config"
    SERVICE = "service"
    CONNECTION = "connection"

    def __str__(self) -> str:
        return self.value


def state_to_health(state: ComponentState) -> Health:
    """A sensible default mapping from lifecycle state to a traffic light.

    Individual components can override this (e.g. a health check may set YELLOW even
    though the component is INSTALLED), but this keeps the common case one line.
    """

    if state in (ComponentState.HEALTHY, ComponentState.VERIFIED, ComponentState.BENCHMARKED):
        return Health.GREEN
    if state in (ComponentState.NEEDS_UPDATE,):
        return Health.YELLOW
    if state in (ComponentState.FAILED,):
        return Health.RED
    if state in (ComponentState.MISSING, ComponentState.UNKNOWN, ComponentState.DISABLED):
        return Health.GRAY
    if state in BUSY_STATES:
        return Health.YELLOW
    # DETECTED / INSTALLED / CONFIGURED -> present but not yet verified
    return Health.GREEN
