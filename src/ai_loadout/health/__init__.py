"""Layers 10 & 13 - health check and AI doctor.

``check`` inspects the digital twin (plus a few live probes) and returns actionable
issues. ``doctor`` turns each issue into a plain-language explanation with a suggested fix,
a "why it matters", and whether a restart is needed.
"""

from .checker import HealthIssue, HealthReport, check
from .doctor import explain

__all__ = ["HealthIssue", "HealthReport", "check", "explain"]
