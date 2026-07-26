"""Layer 1 - Machine validation.

Detects OS, CPU, RAM, GPU/VRAM, disk, internet, admin rights and virtualization *before*
anything gets installed, so Loadout can say "your machine can run X but not Y" up front
instead of failing halfway through.

The heavy lifting for parsing tool output lives in :mod:`.parsers` (unit-tested); this
module gathers the live values and writes them into the digital twin.
"""

from __future__ import annotations

import os
import platform
import socket

from ..core.lifecycle import Category, ComponentState, Health
from ..core.models import Component, Disk, Gpu, Hardware
from ..util import proc
from . import parsers

try:  # psutil is a core dependency, but stay defensive
    import psutil
except Exception:  # pragma: no cover
    psutil = None  # type: ignore


def os_family() -> str:
    system = platform.system().lower()
    if system.startswith("win"):
        return "windows"
    if system == "darwin":
        return "macos"
    if system == "linux":
        return "linux"
    return system or "unknown"


def _cpu_name(family: str) -> str:
    try:
        if family == "windows":
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            value, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            if value:
                return value.strip()
        elif family == "linux":
            try:
                with open("/proc/cpuinfo", encoding="utf-8") as fh:
                    name = parsers.parse_linux_cpu_model(fh.read())
                if name:
                    return name
            except OSError:
                pass
        elif family == "macos":
            result = proc.run(["sysctl", "-n", "machdep.cpu.brand_string"], timeout=5)
            if result.ok and result.out.strip():
                return result.out.strip()
    except Exception:
        pass
    # Fallbacks that work everywhere
    return platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "") or "Unknown CPU"


def _detect_gpus(family: str) -> list[Gpu]:
    # 1) nvidia-smi is the gold standard for NVIDIA VRAM
    if proc.which("nvidia-smi"):
        query = proc.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free,driver_version",
                "--format=csv,noheader,nounits",
            ],
            timeout=10,
        )
        gpus = parsers.parse_nvidia_smi_query(query.out) if query.ok else []
        if gpus:
            plain = proc.run(["nvidia-smi"], timeout=10)
            cuda = parsers.parse_nvidia_cuda_version(plain.out) if plain.ok else None
            if cuda:
                for gpu in gpus:
                    gpu.cuda = cuda
            return gpus

    # 2) Optional pynvml
    try:  # pragma: no cover - depends on optional dep + hardware
        import pynvml

        pynvml.nvmlInit()
        out: list[Gpu] = []
        for i in range(pynvml.nvmlDeviceGetCount()):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            name = name.decode() if isinstance(name, bytes) else name
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            out.append(
                Gpu(
                    name=name,
                    vendor="nvidia",
                    vram_total_gb=parsers.bytes_to_gb(mem.total),
                    vram_free_gb=parsers.bytes_to_gb(mem.free),
                )
            )
        pynvml.nvmlShutdown()
        if out:
            return out
    except Exception:
        pass

    # 3) OS-specific fallbacks (name only, VRAM often unavailable/unreliable)
    if family == "windows":
        ps = proc.powershell(
            "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
            timeout=15,
        )
        if ps.ok:
            return parsers.parse_windows_gpu_cim(ps.out)
    elif family == "macos":
        sp = proc.run(["system_profiler", "SPDisplaysDataType"], timeout=15)
        if sp.ok:
            return parsers.parse_macos_gpu_profiler(sp.out)
    elif family == "linux":
        lspci = proc.run(["sh", "-c", "lspci | grep -i vga"], timeout=10)
        if lspci.ok:
            gpus = []
            for line in lspci.out.splitlines():
                _, _, name = line.partition(":")
                name = name.strip()
                if name:
                    gpus.append(Gpu(name=name, vendor=parsers.vendor_from_name(name)))
            return gpus
    return []


def _is_admin(family: str) -> bool | None:
    try:
        if family == "windows":
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
        return os.geteuid() == 0  # type: ignore[attr-defined]
    except Exception:
        return None


def _internet(timeout: float = 2.0) -> bool:
    for host, port in (("1.1.1.1", 443), ("8.8.8.8", 53)):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            continue
    return False


def _virtualization(family: str) -> bool | None:
    try:
        if family == "linux":
            with open("/proc/cpuinfo", encoding="utf-8") as fh:
                flags = fh.read().lower()
            if " vmx" in flags or "svm" in flags:
                return True
            return False
        if family == "windows":
            ps = proc.powershell(
                "(Get-CimInstance Win32_Processor | Select-Object -First 1)"
                ".VirtualizationFirmwareEnabled",
                timeout=15,
            )
            if ps.ok and ps.out.strip():
                return ps.out.strip().lower().startswith("true")
        if family == "macos":
            return True
    except Exception:
        pass
    return None


def scan_hardware() -> Hardware:
    """Gather a full :class:`Hardware` snapshot of the current machine."""

    family = os_family()
    hw = Hardware(
        os_name=f"{platform.system()} {platform.release()}".strip(),
        os_version=platform.version(),
        os_family=family,
        arch=parsers.normalize_arch(platform.machine()),
        cpu_name=_cpu_name(family),
        python_version=platform.python_version(),
    )

    if psutil is not None:
        try:
            hw.cpu_cores_logical = psutil.cpu_count(logical=True)
            hw.cpu_cores_physical = psutil.cpu_count(logical=False)
            vm = psutil.virtual_memory()
            hw.ram_total_gb = parsers.bytes_to_gb(vm.total)
            hw.ram_available_gb = parsers.bytes_to_gb(vm.available)
        except Exception:
            pass
        try:
            seen = set()
            for part in psutil.disk_partitions(all=False):
                if part.fstype == "" or part.device in seen:
                    continue
                seen.add(part.device)
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                except (PermissionError, OSError):
                    continue
                hw.disks.append(
                    Disk(
                        mount=part.mountpoint,
                        total_gb=parsers.bytes_to_gb(usage.total) or 0.0,
                        free_gb=parsers.bytes_to_gb(usage.free) or 0.0,
                    )
                )
        except Exception:
            pass
    else:  # pragma: no cover
        hw.cpu_cores_logical = os.cpu_count()

    # Primary disk free space (system drive)
    system_root = os.environ.get("SystemDrive", "C:") + "\\" if family == "windows" else "/"
    for disk in hw.disks:
        if disk.mount in (system_root, "/", "C:\\"):
            hw.primary_disk_free_gb = disk.free_gb
            break
    if hw.primary_disk_free_gb is None and hw.disks:
        hw.primary_disk_free_gb = hw.disks[0].free_gb

    hw.gpus = _detect_gpus(family)
    hw.is_admin = _is_admin(family)
    hw.internet = _internet()
    hw.virtualization = _virtualization(family)

    # Human-readable warnings surfaced in the UI
    if (hw.ram_total_gb or 0) and hw.ram_total_gb < 8:
        hw.warnings.append("Less than 8 GB RAM: only small models will run comfortably.")
    if (hw.primary_disk_free_gb or 0) and hw.primary_disk_free_gb < 20:
        hw.warnings.append("Less than 20 GB free disk: model downloads may not fit.")
    if hw.internet is False:
        hw.warnings.append("No internet detected: offline mode only until connectivity returns.")
    return hw


def _disk_health(free_gb: float | None) -> tuple[Health, str]:
    if free_gb is None:
        return Health.GRAY, "unknown"
    if free_gb < 5:
        return Health.RED, f"{free_gb} GB free (critically low)"
    if free_gb < 20:
        return Health.YELLOW, f"{free_gb} GB free (low)"
    return Health.GREEN, f"{free_gb} GB free"


def scan(store) -> Hardware:
    """Run a scan and write hardware + hardware "cards" into the digital twin."""

    store.bus.info("Scanning your workstation...", source="detect")
    hw = scan_hardware()
    store.set_hardware(hw)

    # OS card
    store.upsert_component(
        Component(
            key="os",
            name="Operating System",
            category=Category.OS,
            state=ComponentState.DETECTED,
            health=Health.GREEN,
            version=hw.os_name,
            detail=f"{hw.arch} · Python {hw.python_version}",
        )
    )
    # CPU card
    cores = hw.cpu_cores_logical or "?"
    store.upsert_component(
        Component(
            key="cpu",
            name="CPU",
            category=Category.HARDWARE,
            state=ComponentState.DETECTED,
            health=Health.GREEN,
            detail=f"{hw.cpu_name} · {cores} threads",
        )
    )
    # RAM card
    ram_health = Health.GREEN
    if (hw.ram_total_gb or 0) and hw.ram_total_gb < 8:
        ram_health = Health.YELLOW
    store.upsert_component(
        Component(
            key="ram",
            name="RAM",
            category=Category.HARDWARE,
            state=ComponentState.DETECTED,
            health=ram_health,
            detail=f"{hw.ram_total_gb} GB total · {hw.ram_available_gb} GB free",
        )
    )
    # Disk card
    disk_health, disk_detail = _disk_health(hw.primary_disk_free_gb)
    store.upsert_component(
        Component(
            key="disk",
            name="Disk",
            category=Category.HARDWARE,
            state=ComponentState.DETECTED,
            health=disk_health,
            detail=disk_detail,
        )
    )
    # GPU card
    if hw.gpus:
        primary = hw.gpus[0]
        vram = f"{primary.vram_total_gb} GB VRAM" if primary.vram_total_gb else "VRAM unknown"
        store.upsert_component(
            Component(
                key="gpu",
                name="GPU",
                category=Category.HARDWARE,
                state=ComponentState.DETECTED,
                health=Health.GREEN,
                version=primary.name,
                detail=f"{vram}" + (f" · CUDA {primary.cuda}" if primary.cuda else ""),
            )
        )
    else:
        store.upsert_component(
            Component(
                key="gpu",
                name="GPU",
                category=Category.HARDWARE,
                state=ComponentState.MISSING,
                health=Health.GRAY,
                detail="No discrete GPU detected · CPU inference only",
            )
        )
    # Internet card
    store.upsert_component(
        Component(
            key="internet",
            name="Internet",
            category=Category.SERVICE,
            state=ComponentState.DETECTED if hw.internet else ComponentState.MISSING,
            health=Health.GREEN if hw.internet else Health.YELLOW,
            detail="Connected" if hw.internet else "Offline",
        )
    )

    store.bus.success(
        f"Scan complete: {hw.os_name}, {hw.ram_total_gb} GB RAM, "
        f"{'GPU ' + hw.gpus[0].name if hw.gpus else 'no GPU'}",
        source="detect",
    )
    return hw


def summarize(hw: Hardware) -> list[str]:
    """A few human-readable lines for the CLI ``scan`` output."""

    lines = [
        f"OS         {hw.os_name} ({hw.arch})",
        f"CPU        {hw.cpu_name}  |  {hw.cpu_cores_physical or '?'} cores / {hw.cpu_cores_logical or '?'} threads",
        f"RAM        {hw.ram_total_gb} GB total  |  {hw.ram_available_gb} GB available",
        f"Disk       {hw.primary_disk_free_gb} GB free (primary)",
    ]
    if hw.gpus:
        for gpu in hw.gpus:
            vram = f"{gpu.vram_total_gb} GB VRAM" if gpu.vram_total_gb else "VRAM unknown"
            cuda = f"  |  CUDA {gpu.cuda}" if gpu.cuda else ""
            lines.append(f"GPU        {gpu.name}  |  {vram}{cuda}")
    else:
        lines.append("GPU        none detected (CPU inference only)")
    lines.append(f"Internet   {'connected' if hw.internet else 'offline'}")
    lines.append(
        f"Admin      {'yes' if hw.is_admin else ('no' if hw.is_admin is False else 'unknown')}"
    )
    if hw.virtualization is not None:
        lines.append(f"Virtualization {'enabled' if hw.virtualization else 'disabled'}")
    return lines
