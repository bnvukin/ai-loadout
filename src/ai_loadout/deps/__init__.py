"""Layer 2 - Dependency manager.

Detect the developer toolchain (Git, Python, Node, uv, Docker, WSL, package managers,
CUDA, ...), compare versions against a recommended minimum, and decide per tool whether to
skip / upgrade / install -- instead of blindly reinstalling.
"""

from .detect import detect_all, detect_one
from .managers import available_managers
from .registry import DEPENDENCIES, Dependency, platform_dependencies

__all__ = [
    "DEPENDENCIES",
    "Dependency",
    "available_managers",
    "detect_all",
    "detect_one",
    "platform_dependencies",
]
