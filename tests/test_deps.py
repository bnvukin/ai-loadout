from ai_loadout.core.state import StateStore
from ai_loadout.deps import registry
from ai_loadout.deps.detect import detect_all, detect_one
from ai_loadout.deps.managers import available_managers, preferred_manager
from ai_loadout.deps.version import extract_version, is_older, version_tuple
from ai_loadout.util.proc import RunResult


# ---- version parsing ----------------------------------------------------------------
def test_extract_version_from_messy_strings():
    assert extract_version("git version 2.43.0") == "2.43.0"
    assert extract_version("v24.15.0") == "24.15.0"
    assert extract_version("Docker version 27.1.1, build 63125853") == "27.1.1"
    assert extract_version("Python 3.12.10") == "3.12.10"
    assert extract_version("Cuda compilation tools, release 12.4, V12.4.131") == "12.4"
    assert extract_version("no version here") is None


def test_version_compare():
    assert version_tuple("3.12.10") == (3, 12, 10)
    assert is_older("3.8.0", "3.9") is True
    assert is_older("3.12.10", "3.9") is False
    assert is_older(None, "3.9") is True
    assert is_older("1.0", None) is False


# ---- decision logic with simulated tools --------------------------------------------
def _fake_env(installed: dict):
    """installed maps exe-name -> version string (or None to mean 'present, no version')."""

    def which(name):
        return f"/usr/bin/{name}" if name in installed else None

    def run(cmd, timeout=15, **kw):
        exe = cmd[0].split("/")[-1]
        if exe in installed and installed[exe]:
            return RunResult(True, 0, f"{exe} version {installed[exe]}", "")
        if exe in installed:
            return RunResult(True, 0, "", "")
        return RunResult(False, 127, "", "not found", found=False)

    return which, run


def test_detect_missing_tool_is_install_when_installable():
    which, run = _fake_env({})  # nothing installed
    git = registry.by_key("git")
    result = detect_one(git, "windows", managers=["winget"], which_fn=which, run_fn=run)
    assert result["decision"] == "install"
    assert "install" in result["actions"]


def test_detect_missing_tool_is_manual_without_installer():
    which, run = _fake_env({})
    npm = registry.by_key("npm")  # npm has no package-manager install id
    result = detect_one(npm, "windows", managers=["winget"], which_fn=which, run_fn=run)
    assert result["decision"] == "manual"


def test_detect_old_version_is_upgrade():
    which, run = _fake_env({"python": "3.8.0"})
    python = registry.by_key("python")
    result = detect_one(python, "linux", managers=["apt"], which_fn=which, run_fn=run)
    assert result["decision"] == "upgrade"
    assert result["version"] == "3.8.0"


def test_detect_recent_version_is_skip():
    which, run = _fake_env({"python": "3.12.10"})
    python = registry.by_key("python")
    result = detect_one(python, "linux", managers=["apt"], which_fn=which, run_fn=run)
    assert result["decision"] == "skip"
    assert result["state"].value == "detected"


# ---- managers -----------------------------------------------------------------------
def test_available_and_preferred_managers():
    which = lambda name: "/usr/bin/brew" if name == "brew" else None  # noqa: E731
    assert available_managers(which) == ["brew"]
    assert preferred_manager("macos", which) == "brew"
    assert preferred_manager("windows", which) is None


def test_registry_platform_filtering_and_unique_keys():
    keys = [d.key for d in registry.DEPENDENCIES]
    assert len(keys) == len(set(keys))
    win = {d.key for d in registry.platform_dependencies("windows")}
    linux = {d.key for d in registry.platform_dependencies("linux")}
    assert "winget" in win and "winget" not in linux
    assert "brew" in linux and "brew" not in win


# ---- real detection on the test machine ---------------------------------------------
def test_detect_all_on_real_machine(loadout_home):
    store = StateStore(autosave=False)
    from ai_loadout.detect.system import scan

    scan(store)
    results = detect_all(store)
    by_key = {r["key"]: r for r in results}
    # Python is running these tests, so it must be detected as present.
    assert "python" in by_key
    assert by_key["python"]["decision"] in ("skip", "upgrade")
    # Every result carries a decision + a component in the twin
    assert store.get_component("git") is not None
