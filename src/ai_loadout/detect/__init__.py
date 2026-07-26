"""Detection layers.

* :mod:`ai_loadout.detect.system` — Layer 1, machine validation (OS/CPU/RAM/GPU/disk...).
* :mod:`ai_loadout.detect.parsers` — pure functions that parse tool output (unit-tested).
"""

from .system import scan_hardware

__all__ = ["scan_hardware"]
