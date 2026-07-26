"""A real scan of whatever machine runs the tests (CI included).

We assert only on things that must be true everywhere, so the test is stable across
Windows/macOS/Linux runners with or without a GPU or internet.
"""

from ai_loadout.core.state import StateStore
from ai_loadout.detect.system import os_family, scan, scan_hardware


def test_os_family_is_known():
    assert os_family() in {"windows", "macos", "linux"}


def test_scan_hardware_returns_plausible_values():
    hw = scan_hardware()
    assert hw.os_family in {"windows", "macos", "linux"}
    assert hw.arch  # non-empty
    assert hw.cpu_name  # non-empty
    assert (hw.cpu_cores_logical or 0) >= 1
    assert (hw.ram_total_gb or 0) > 0
    # gpus is a list (possibly empty on CI); disks likely non-empty
    assert isinstance(hw.gpus, list)


def test_scan_populates_digital_twin(loadout_home):
    store = StateStore(autosave=False)
    scan(store)
    keys = {c.key for c in store.components()}
    assert {"os", "cpu", "ram", "disk", "gpu", "internet"}.issubset(keys)
    # After a scan there should be an overall health reading that isn't the empty default
    health = store.overall_health()
    assert health["total"] >= 6
