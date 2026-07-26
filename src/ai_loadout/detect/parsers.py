"""Pure parsers for tool output.

Kept separate from live gathering so they can be unit-tested against captured samples in
``tests/fixtures/`` without needing the real hardware/tools present.
"""

from __future__ import annotations

import re

from ..core.models import Gpu


def bytes_to_gb(n: float | int | None) -> float | None:
    if n is None:
        return None
    return round(float(n) / (1024**3), 1)


def mib_to_gb(mib: float | int | None) -> float | None:
    if mib is None:
        return None
    return round(float(mib) / 1024.0, 1)


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def vendor_from_name(name: str) -> str:
    low = name.lower()
    if (
        "nvidia" in low
        or "geforce" in low
        or "rtx" in low
        or "gtx" in low
        or "quadro" in low
        or "tesla" in low
    ):
        return "nvidia"
    if "radeon" in low or "amd" in low or "rx " in low:
        return "amd"
    if "intel" in low or "arc" in low or "iris" in low or "uhd" in low:
        return "intel"
    if "apple" in low or "m1" in low or "m2" in low or "m3" in low or "m4" in low:
        return "apple"
    return "unknown"


def parse_nvidia_smi_query(text: str) -> list[Gpu]:
    """Parse ``nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version
    --format=csv,noheader,nounits`` (values in MiB)."""

    gpus: list[Gpu] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if not parts or not parts[0]:
            continue
        total = _to_float(parts[1]) if len(parts) > 1 else None
        free = _to_float(parts[2]) if len(parts) > 2 else None
        driver = parts[3] if len(parts) > 3 and parts[3] else None
        gpus.append(
            Gpu(
                name=parts[0],
                vendor="nvidia",
                vram_total_gb=mib_to_gb(total),
                vram_free_gb=mib_to_gb(free),
                driver=driver,
            )
        )
    return gpus


def parse_nvidia_cuda_version(text: str) -> str | None:
    """Extract the ``CUDA Version: 12.4`` string from plain ``nvidia-smi`` output."""

    m = re.search(r"CUDA Version:\s*([0-9.]+)", text)
    return m.group(1) if m else None


def parse_linux_cpu_model(cpuinfo: str) -> str | None:
    for line in cpuinfo.splitlines():
        if line.lower().startswith("model name"):
            _, _, value = line.partition(":")
            return value.strip() or None
    return None


def parse_windows_gpu_cim(text: str) -> list[Gpu]:
    """Parse newline-separated GPU names from a PowerShell CIM query fallback.

    We ask PowerShell for one adapter name per line; VRAM from ``AdapterRAM`` is
    unreliable (capped at 4 GiB for large cards) so we deliberately leave it unknown here
    and rely on nvidia-smi for accurate VRAM.
    """

    gpus: list[Gpu] = []
    for line in text.splitlines():
        name = line.strip()
        if not name or name.lower() in {"name", "----"}:
            continue
        gpus.append(Gpu(name=name, vendor=vendor_from_name(name)))
    return gpus


def parse_macos_gpu_profiler(text: str) -> list[Gpu]:
    """Parse ``system_profiler SPDisplaysDataType`` for chipset names and VRAM."""

    gpus: list[Gpu] = []
    current_name: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        m = re.match(r"Chipset Model:\s*(.+)$", line)
        if m:
            current_name = m.group(1).strip()
            gpus.append(Gpu(name=current_name, vendor=vendor_from_name(current_name)))
            continue
        vm = re.match(r"VRAM.*:\s*([0-9]+)\s*(MB|GB)", line)
        if vm and gpus:
            value = float(vm.group(1))
            gpus[-1].vram_total_gb = round(value / 1024.0, 1) if vm.group(2) == "MB" else value
    return gpus


def normalize_arch(machine: str) -> str:
    low = machine.lower()
    if low in {"amd64", "x86_64", "x64"}:
        return "x86_64"
    if low in {"arm64", "aarch64"}:
        return "arm64"
    if low in {"x86", "i386", "i686"}:
        return "x86"
    return machine or "unknown"
