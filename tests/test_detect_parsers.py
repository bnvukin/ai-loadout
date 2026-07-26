from pathlib import Path

from ai_loadout.detect import parsers

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_bytes_and_mib_conversions():
    assert parsers.bytes_to_gb(32 * 1024**3) == 32.0
    assert parsers.bytes_to_gb(None) is None
    assert parsers.mib_to_gb(12282) == 12.0  # ~12 GB
    assert parsers.mib_to_gb(None) is None


def test_vendor_from_name():
    assert parsers.vendor_from_name("NVIDIA GeForce RTX 4070") == "nvidia"
    assert parsers.vendor_from_name("AMD Radeon RX 6800") == "amd"
    assert parsers.vendor_from_name("Intel(R) UHD Graphics 770") == "intel"
    assert parsers.vendor_from_name("Apple M3 Pro") == "apple"
    assert parsers.vendor_from_name("Some Mystery GPU") == "unknown"


def test_parse_nvidia_smi_query():
    gpus = parsers.parse_nvidia_smi_query(_read("nvidia_smi_query.csv"))
    assert len(gpus) == 2
    assert gpus[0].name == "NVIDIA GeForce RTX 4070"
    assert gpus[0].vram_total_gb == 12.0
    assert gpus[0].vram_free_gb == 11.2
    assert gpus[0].driver == "550.54.15"
    assert gpus[0].vendor == "nvidia"


def test_parse_nvidia_cuda_version():
    assert parsers.parse_nvidia_cuda_version(_read("nvidia_smi.txt")) == "12.4"
    assert parsers.parse_nvidia_cuda_version("no cuda here") is None


def test_parse_windows_gpu_cim():
    gpus = parsers.parse_windows_gpu_cim(_read("windows_gpu_cim.txt"))
    assert [g.name for g in gpus] == ["NVIDIA GeForce RTX 4070", "Intel(R) UHD Graphics 770"]
    assert gpus[0].vendor == "nvidia"
    assert gpus[1].vendor == "intel"


def test_parse_macos_gpu_profiler():
    gpus = parsers.parse_macos_gpu_profiler(_read("macos_system_profiler.txt"))
    names = [g.name for g in gpus]
    assert "Apple M3 Pro" in names
    amd = next(g for g in gpus if "Radeon" in g.name)
    assert amd.vram_total_gb == 8.0  # 8192 MB -> 8 GB


def test_parse_linux_cpu_model():
    model = parsers.parse_linux_cpu_model(_read("linux_cpuinfo.txt"))
    assert model == "Intel(R) Core(TM) i7-10750H CPU @ 2.60GHz"


def test_normalize_arch():
    assert parsers.normalize_arch("AMD64") == "x86_64"
    assert parsers.normalize_arch("x86_64") == "x86_64"
    assert parsers.normalize_arch("arm64") == "arm64"
    assert parsers.normalize_arch("aarch64") == "arm64"
