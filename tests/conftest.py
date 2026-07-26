"""Shared pytest fixtures.

Every test runs against a throwaway ``LOADOUT_HOME`` so nothing touches the real
machine's ``~/.ai-loadout`` directory and tests stay hermetic and parallel-safe.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def loadout_home(tmp_path, monkeypatch):
    home = tmp_path / "loadout-home"
    monkeypatch.setenv("LOADOUT_HOME", str(home))
    return home
