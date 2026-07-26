"""Loadout - turn any machine into a production-ready AI development workstation.

Loadout treats your machine as a *digital twin*: every tool (Git, Python,
Docker, Ollama, VS Code, local models, configs, environment variables ...) is a
component that moves through a single lifecycle -- Detected -> Installed ->
Configured -> Verified -> Benchmarked -> Healthy -> Needs Update -> Repairing.

The dashboard is just a live view of that state model, and every action
(install, configure, repair, download) updates the state first so the UI stays
consistent.
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
