"""Streaming SHA256 helpers and a small table of known-good hashes for direct downloads."""

from __future__ import annotations

import hashlib
from pathlib import Path

# ``label`` -> expected SHA256 hex (lowercase) for files we fetch directly.
# Populated only where a vendor publishes a stable hash (e.g. bootstrap installers).
KNOWN_HASHES: dict[str, dict[str, str]] = {
    # Example entry — bootstrap uses winget today; reserved for future direct downloads.
    # "python-3.12.8-amd64.exe": {
    #     "url": "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe",
    #     "sha256": "...",
    # },
}


def compute_sha256(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Compute the SHA256 hex digest of a file, reading in chunks."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        while True:
            block = fh.read(chunk_size)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def verify_sha256(path: str | Path, expected: str) -> bool:
    """Return True when the file digest matches ``expected`` (case-insensitive)."""

    if not expected:
        return False
    try:
        actual = compute_sha256(path)
    except OSError:
        return False
    return actual.lower() == expected.strip().lower()
