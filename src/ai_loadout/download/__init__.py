"""Layer 5 — Resumable HTTP downloads with integrity verification."""

from __future__ import annotations

from .manager import DownloadError, download_file, plan_download

__all__ = ["DownloadError", "plan_download", "download_file"]
