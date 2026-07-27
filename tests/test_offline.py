"""Tests for Layer 19 — offline support."""

from __future__ import annotations

import os

from ai_loadout.offline.cache import list_cache, lookup_cache, record_in_cache
from ai_loadout.offline.connectivity import check_connectivity
from ai_loadout.offline.gate import offline_block
from ai_loadout.offline.report import build_offline_report


def test_connectivity_online_mocked():
    class Resp:
        status = 200

        def getcode(self):
            return 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    result = check_connectivity(urlopen_fn=lambda *a, **k: Resp())
    assert result["online"] is True
    assert result["reason"] is None


def test_connectivity_offline_mocked():
    import urllib.error

    def boom(*a, **k):
        raise urllib.error.URLError("network down")

    result = check_connectivity(urlopen_fn=boom)
    assert result["online"] is False
    assert "network down" in result["reason"]


def test_offline_gate_blocks_download():
    block = offline_block("download", connectivity_fn=lambda: {"online": False, "reason": "x"})
    assert block is not None
    assert block["offline"] is True
    assert "download" in block["reason"]


def test_offline_gate_allows_when_online():
    assert offline_block("download", connectivity_fn=lambda: {"online": True}) is None


def test_cache_hit_and_miss(tmp_path, monkeypatch):
    monkeypatch.setenv("LOADOUT_HOME", str(tmp_path))
    assert lookup_cache("https://example.com/a.bin") is None
    src = tmp_path / "asset.bin"
    src.write_bytes(b"hello")
    record_in_cache("https://example.com/a.bin", src)
    hit = lookup_cache("https://example.com/a.bin")
    assert hit is not None
    assert os.path.isfile(hit["path"])
    assert len(list_cache()) == 1


def test_offline_report_shape():
    report = build_offline_report(connectivity_fn=lambda: {"online": False, "reason": "mock"})
    assert report["online"] is False
    assert "works_offline" in report
    assert "needs_network" in report
