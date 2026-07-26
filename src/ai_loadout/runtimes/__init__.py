"""Layer 3 - AI runtimes and editors.

Detect (and later install/configure) Ollama, VS Code + extensions, Continue, the agent
CLIs (Claude Code, Codex, Gemini), Open WebUI, LM Studio, AnythingLLM, Cursor, ...
"""

from .detect import detect_all, detect_one
from .registry import RUNTIMES, Runtime, platform_runtimes

__all__ = ["RUNTIMES", "Runtime", "detect_all", "detect_one", "platform_runtimes"]
