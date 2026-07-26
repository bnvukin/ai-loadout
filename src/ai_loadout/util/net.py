"""Tiny network helpers (used to detect locally-running services like Ollama)."""

from __future__ import annotations

import socket


def port_open(host: str, port: int, timeout: float = 0.75) -> bool:
    """True if a TCP connection to ``host:port`` succeeds quickly."""

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
