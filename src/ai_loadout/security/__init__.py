"""Layer 14 — Security and integrity verification.

Official-source allowlisting, SHA256 checksum helpers, and a trust-posture report that
explains how each installable component is sourced (package manager vs direct download).
"""

from __future__ import annotations

from .checksum import compute_sha256, verify_sha256
from .posture import build_trust_posture
from .sources import is_official_source

__all__ = [
    "compute_sha256",
    "verify_sha256",
    "is_official_source",
    "build_trust_posture",
]
