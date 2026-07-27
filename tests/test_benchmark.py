"""Tests for Layer 12 — benchmark."""

from __future__ import annotations

import json

from ai_loadout.benchmark.runner import (
    benchmark_cpu,
    benchmark_disk,
    latest_benchmark,
    run_benchmark,
)
from ai_loadout.benchmark.tier import recommend_tier, throughput_mbps
from ai_loadout.core.models import Hardware
from ai_loadout.core.state import StateStore


def test_throughput_mbps_math():
    assert throughput_mbps(1024 * 1024, 1.0) == 1.0
    assert throughput_mbps(0, 1.0) == 0.0


def test_recommend_tier_heuristic():
    entry = recommend_tier(
        cpu_score=100_000,
        disk_write_mbps=30,
        disk_read_mbps=25,
        ram_gb=8,
        vram_gb=0,
    )
    assert entry["tier"] in ("minimal", "entry", "mid", "workstation")
    workstation = recommend_tier(
        cpu_score=3_000_000,
        disk_write_mbps=300,
        disk_read_mbps=250,
        ram_gb=64,
        vram_gb=16,
        tokens_per_sec=50,
    )
    assert workstation["tier"] == "workstation"


def test_benchmark_cpu_and_disk_fast(tmp_path):
    cpu = benchmark_cpu(iterations=1000)
    assert cpu["score"] > 0
    disk = benchmark_disk(tmp_path, size_bytes=4096)
    assert disk["write_mbps"] >= 0
    assert disk["verified"] is True


def test_run_benchmark_persists(loadout_home):
    store = StateStore(autosave=False)
    store.set_hardware(Hardware(os_family="linux", ram_total_gb=16.0))
    result = run_benchmark(store, fast=True, urlopen_fn=_offline_ollama)
    assert result["tier"]["tier"]
    assert result["path"].endswith(".json")
    latest = latest_benchmark()
    assert latest is not None
    assert latest["cpu"]["score"] == result["cpu"]["score"]


def _offline_ollama(*_a, **_k):
    import urllib.error

    raise urllib.error.URLError("no ollama")


def test_benchmark_cli_json(capsys, loadout_home):
    from ai_loadout.cli import main

    rc = main(["--json", "benchmark"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert "tier" in payload and "cpu" in payload
