"""Layer 10 - health check.

Inspects the digital twin and a few live signals, then produces a list of actionable
issues (each enriched by the AI Doctor). Pure enough to unit-test: the live probes are
injectable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.lifecycle import ComponentState
from ..deps.registry import by_key as dep_by_key
from ..runtimes.registry import by_key as runtime_by_key
from ..util import net, proc
from .doctor import explain


@dataclass
class HealthIssue:
    key: str
    severity: str  # info | warning | error
    component: str | None
    title: str
    explanation: str
    fix: str
    why: str
    restart: str
    fixable: bool
    fix_action: str | None = None

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "severity": self.severity,
            "component": self.component,
            "title": self.title,
            "explanation": self.explanation,
            "fix": self.fix,
            "why": self.why,
            "restart": self.restart,
            "fixable": self.fixable,
            "fix_action": self.fix_action,
        }


@dataclass
class HealthReport:
    percent: int
    status: str
    issues: list[HealthIssue] = field(default_factory=list)
    counts: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "percent": self.percent,
            "status": self.status,
            "counts": self.counts,
            "issues": [i.to_dict() for i in self.issues],
        }


def _issue(key: str, severity: str, component: str | None, context: dict, fix_action: str | None):
    exp = explain(key, context)
    return HealthIssue(
        key=key,
        severity=severity,
        component=component,
        title=exp["title"],
        explanation=exp["explanation"],
        fix=exp["fix"],
        why=exp["why"],
        restart=exp["restart"],
        fixable=exp["fixable"],
        fix_action=fix_action,
    )


def check(store, port_open=net.port_open, run_fn=proc.run) -> HealthReport:
    """Run the health check against the current twin + live probes."""

    store.bus.info("Running health check...", source="health")
    issues: list[HealthIssue] = []
    hw = store.hardware

    # Hardware-derived signals
    if hw is not None:
        if hw.primary_disk_free_gb is not None and hw.primary_disk_free_gb < 20:
            issues.append(
                _issue(
                    "disk-low",
                    "error" if hw.primary_disk_free_gb < 5 else "warning",
                    "disk",
                    {"free": hw.primary_disk_free_gb},
                    None,
                )
            )
        if hw.internet is False:
            issues.append(_issue("offline", "warning", "internet", {}, None))
        if not hw.has_gpu():
            issues.append(_issue("cpu-only", "info", "gpu", {}, None))

    # Ollama installed but server not running
    ollama = store.get_component("ollama")
    if ollama and ollama.state != ComponentState.MISSING:
        if not port_open("127.0.0.1", 11434):
            issues.append(_issue("ollama-not-running", "warning", "ollama", {}, "start-ollama"))

    # Docker installed but daemon down
    docker = store.get_component("docker")
    if docker and docker.state != ComponentState.MISSING and docker.path:
        info = run_fn([docker.path, "info"], timeout=8)
        if not info.ok:
            issues.append(_issue("docker-not-running", "warning", "docker", {}, "start-docker"))

    # Out-of-date dependencies
    for comp in store.components():
        if comp.state == ComponentState.NEEDS_UPDATE:
            dep = dep_by_key(comp.key)
            issues.append(
                _issue(
                    "update-available",
                    "info",
                    comp.key,
                    {
                        "name": comp.name,
                        "version": comp.version or "?",
                        "min_version": (dep.min_version if dep else "latest"),
                    },
                    "update",
                )
            )

    # Recommended-but-missing runtimes (only the non-optional ones)
    for comp in store.components():
        if comp.state == ComponentState.MISSING:
            rt = runtime_by_key(comp.key)
            if rt and not rt.optional:
                issues.append(
                    _issue(
                        "missing-recommended",
                        "warning",
                        comp.key,
                        {"name": comp.name, "note": rt.note or "Recommended for AI workstations."},
                        "install",
                    )
                )

    # PATH hygiene
    from ..config.env import path_summary

    ps = path_summary()
    if ps.get("duplicates"):
        issues.append(
            _issue(
                "path-duplicates",
                "info",
                "path",
                {"count": len(ps["duplicates"])},
                "path-dedupe",
            )
        )

    health = store.overall_health()
    # Nudge the reported percentage down a touch if there are error-level issues.
    percent = health["percent"]
    if any(i.severity == "error" for i in issues):
        percent = min(percent, 60)
    store.bus.success(f"Health check complete: {len(issues)} issue(s)", source="health")
    return HealthReport(
        percent=percent, status=health["status"], issues=issues, counts=health["counts"]
    )


def health_from_scratch(store) -> HealthReport:
    """Ensure the twin is populated (scan if empty), then run the health check."""

    if store.hardware is None or not store.components():
        from ..deps.detect import detect_all as detect_deps
        from ..detect.system import scan
        from ..runtimes.detect import detect_all as detect_runtimes

        scan(store)
        detect_deps(store)
        detect_runtimes(store)
    return check(store)
