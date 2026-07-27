"""Tests for Layer 5 — download manager."""

from __future__ import annotations

import io
import urllib.error

import pytest

from ai_loadout.download.manager import DownloadError, download_file, plan_download


class _FakeHeaders(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class FakeResponse:
    def __init__(self, data: bytes, status: int = 200, headers=None):
        self._stream = io.BytesIO(data)
        self.status = status
        self._headers = _FakeHeaders(headers or {})

    def read(self, size=-1):
        return self._stream.read(size)

    def getcode(self):
        return self.status

    def info(self):
        return self._headers

    def close(self):
        pass


def test_plan_download_official_vs_blocked():
    ok = plan_download("https://github.com/bnvukin/ai-loadout/releases/download/v0.1.0/x.bin")
    assert ok["ok"] is True
    assert ok["official_source"] is True
    bad = plan_download("https://evil.example/malware.exe")
    assert bad["ok"] is False
    assert "allowlist" in (bad["reason"] or "").lower()


def test_download_success_and_checksum(tmp_path):
    payload = b"loadout-test-payload"
    import hashlib

    expected = hashlib.sha256(payload).hexdigest()
    dest = tmp_path / "tool.bin"

    def opener(_req, timeout=30):
        return FakeResponse(payload, 200, {"Content-Length": str(len(payload))})

    result = download_file(
        "https://github.com/bnvukin/ai-loadout/releases/download/v0.1.0/tool.bin",
        dest,
        expected_sha256=expected,
        urlopen_fn=opener,
    )
    assert result["ok"] is True
    assert dest.read_bytes() == payload


def test_download_checksum_rejects_tamper(tmp_path):
    payload = b"good"
    dest = tmp_path / "tool.bin"

    def opener(_req, timeout=30):
        return FakeResponse(payload, 200, {"Content-Length": str(len(payload))})

    with pytest.raises(DownloadError, match="checksum"):
        download_file(
            "https://github.com/bnvukin/ai-loadout/releases/download/v0.1.0/tool.bin",
            dest,
            expected_sha256="0" * 64,
            urlopen_fn=opener,
        )


def test_download_resume_appends_part(tmp_path):
    dest = tmp_path / "file.bin"
    part = dest.with_suffix(dest.suffix + ".part")
    part.write_bytes(b"PART")
    tail = b"-END"

    def urlopen_fn(req, timeout=30):
        assert req.get_header("Range") == "bytes=4-"
        return FakeResponse(tail, 206, {"Content-Range": "bytes 4-8/9"})

    result = download_file(
        "https://github.com/bnvukin/ai-loadout/releases/download/v0.1.0/file.bin",
        dest,
        urlopen_fn=urlopen_fn,
    )
    assert result["bytes"] == 8
    assert dest.read_bytes() == b"PART-END"


def test_download_retries_transient_failure(tmp_path, monkeypatch):
    dest = tmp_path / "retry.bin"
    payload = b"ok"
    attempts = {"n": 0}

    def urlopen_fn(_req, timeout=30):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise urllib.error.URLError("timeout")
        return FakeResponse(payload, 200, {"Content-Length": str(len(payload))})

    monkeypatch.setattr("ai_loadout.download.manager.time.sleep", lambda _s: None)
    download_file(
        "https://github.com/bnvukin/ai-loadout/releases/download/v0.1.0/retry.bin",
        dest,
        urlopen_fn=urlopen_fn,
        max_retries=3,
    )
    assert attempts["n"] == 2
    assert dest.read_bytes() == payload


def test_download_refuses_unofficial(tmp_path):
    with pytest.raises(DownloadError, match="allowlist"):
        download_file("https://mirror.evil.example/x.bin", tmp_path / "x.bin")
