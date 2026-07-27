"""Run a bounded, non-destructive benchmark and persist results."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

from ..core import paths
from ..core.state import load_state
from .tier import recommend_tier, throughput_mbps

RunFn = Callable[..., object]


def benchmark_cpu(*, iterations: int = 10_000) -> dict:
    """Quick integer loop — higher score is faster."""

    start = time.perf_counter()
    total = 0
    for i in range(iterations):
        total += (i * i) % 997
    elapsed = time.perf_counter() - start
    score = int(iterations / elapsed) if elapsed > 0 else 0
    return {
        "iterations": iterations,
        "seconds": round(elapsed, 4),
        "score": score,
        "checksum": total,
    }


def benchmark_disk(
    directory: Path,
    *,
    size_bytes: int = 64 * 1024,
) -> dict:
    """Sequential write/read of a temp file; returns throughput in MB/s."""

    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f".loadout-bench-{os.getpid()}.tmp"
    payload = os.urandom(size_bytes)
    try:
        start = time.perf_counter()
        target.write_bytes(payload)
        write_s = time.perf_counter() - start

        start = time.perf_counter()
        read_back = target.read_bytes()
        read_s = time.perf_counter() - start
    finally:
        target.unlink(missing_ok=True)

    ok = read_back == payload
    return {
        "size_bytes": size_bytes,
        "write_mbps": throughput_mbps(size_bytes, write_s),
        "read_mbps": throughput_mbps(size_bytes, read_s),
        "verified": ok,
    }


def try_ollama_inference(
    *,
    urlopen_fn: RunFn | None = None,
    timeout: int = 15,
) -> dict:
    """Micro inference via local Ollama HTTP API; skipped when unavailable."""

    opener = urlopen_fn or urllib.request.urlopen
    body = json.dumps(
        {
            "model": "llama3.2:1b",
            "prompt": "Say hi in one word.",
            "stream": False,
            "options": {"num_predict": 8},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        start = time.perf_counter()
        with opener(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
        elapsed = time.perf_counter() - start
        payload = json.loads(raw)
        eval_count = int(payload.get("eval_count") or 0)
        if eval_count <= 0 or elapsed <= 0:
            return {"skipped": True, "reason": "no token count from Ollama"}
        tps = round(eval_count / elapsed, 1)
        return {
            "skipped": False,
            "model": payload.get("model") or "llama3.2:1b",
            "tokens_per_sec": tps,
            "seconds": round(elapsed, 3),
        }
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        return {"skipped": True, "reason": str(exc)}


def _hardware_snapshot(store) -> dict:
    hw = store.hardware
    if hw is None:
        return {"ram_gb": 0.0, "vram_gb": 0.0, "gpus": []}
    return {
        "ram_gb": hw.ram_total_gb or 0.0,
        "vram_gb": hw.total_vram_gb(),
        "gpus": [g.to_dict() for g in hw.gpus],
        "cpu_name": hw.cpu_name,
    }


def run_benchmark(
    store=None,
    *,
    fast: bool = True,
    bus=None,
    urlopen_fn: RunFn | None = None,
) -> dict:
    """Run a bounded benchmark, write logs, and return structured results."""

    store = store or load_state()
    paths.ensure_dirs()
    bench_dir = paths.logs_dir() / "benchmarks"
    bench_dir.mkdir(parents=True, exist_ok=True)

    cpu_iters = 10_000 if fast else 100_000
    disk_size = 64 * 1024 if fast else 512 * 1024

    def _log(message: str) -> None:
        if bus is not None:
            bus.info(message, kind="log", target="benchmark", source="benchmark")

    _log("Benchmark: CPU")
    cpu = benchmark_cpu(iterations=cpu_iters)
    _log("Benchmark: disk")
    disk = benchmark_disk(bench_dir, size_bytes=disk_size)
    hw = _hardware_snapshot(store)
    _log("Benchmark: inference probe")
    inference = try_ollama_inference(urlopen_fn=urlopen_fn)

    tps = None if inference.get("skipped") else inference.get("tokens_per_sec")
    tier = recommend_tier(
        cpu_score=float(cpu["score"]),
        disk_write_mbps=float(disk["write_mbps"]),
        disk_read_mbps=float(disk["read_mbps"]),
        ram_gb=float(hw["ram_gb"]),
        vram_gb=float(hw["vram_gb"]),
        tokens_per_sec=tps,
    )

    result = {
        "schema": 1,
        "timestamp": time.time(),
        "fast": fast,
        "cpu": cpu,
        "disk": disk,
        "hardware": hw,
        "inference": inference,
        "tier": tier,
    }

    stamp = time.strftime("%Y%m%d-%H%M%S")
    json_path = paths.logs_dir() / f"benchmark-{stamp}.json"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    _append_benchmark_log(result, json_path)
    _log(f"Benchmark complete — tier: {tier['tier']}")
    return {"path": str(json_path), **result}


def _append_benchmark_log(result: dict, json_path: Path) -> None:
    try:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = (
            f"{stamp}  tier={result['tier']['tier']}  cpu={result['cpu']['score']}  "
            f"disk_w={result['disk']['write_mbps']}MB/s  "
            f"disk_r={result['disk']['read_mbps']}MB/s  file={json_path.name}\n"
        )
        with paths.benchmark_log().open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        pass


def latest_benchmark() -> dict | None:
    """Return the newest ``benchmark-*.json`` snapshot, if any."""

    root = paths.logs_dir()
    if not root.is_dir():
        return None
    files = sorted(root.glob("benchmark-*.json"), reverse=True)
    if not files:
        return None
    try:
        return json.loads(files[0].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
