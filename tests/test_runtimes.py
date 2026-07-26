from pathlib import Path

from ai_loadout.core.state import StateStore
from ai_loadout.runtimes import registry
from ai_loadout.runtimes.detect import detect_all, detect_one
from ai_loadout.runtimes.parsers import (
    parse_code_extensions,
    parse_code_version,
    parse_ollama_list,
)
from ai_loadout.util.proc import RunResult

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ---- parsers ------------------------------------------------------------------------
def test_parse_ollama_list():
    models = parse_ollama_list(_read("ollama_list.txt"))
    names = [m["name"] for m in models]
    assert names == ["qwen3:8b", "llama3.2:3b", "nomic-embed-text"]
    assert models[0]["size_gb"] == 5.2
    assert models[2]["size_gb"] == round(274 / 1024, 2)  # MB -> GB


def test_parse_code_extensions_and_version():
    exts = parse_code_extensions(_read("code_extensions.txt"))
    ids = [e["id"] for e in exts]
    assert "continue.continue" in ids
    assert exts[0]["version"] == "1.0.14"
    assert parse_code_version("1.127.0\nabc123\nx64") == "1.127.0"


# ---- detection with simulated environment -------------------------------------------
def test_detect_ollama_present_lists_models(monkeypatch):
    def which(name):
        return "/usr/bin/ollama" if name == "ollama" else None

    def run(cmd, timeout=15, **kw):
        if cmd[:2] == ["ollama", "list"] or (cmd[0].endswith("ollama") and "list" in cmd):
            return RunResult(True, 0, _read("ollama_list.txt"), "")
        return RunResult(True, 0, "ollama version is 0.5.7", "")

    monkeypatch.setattr("ai_loadout.runtimes.detect.net.port_open", lambda *a, **k: True)
    ollama = registry.by_key("ollama")
    result = detect_one(ollama, managers=[], which_fn=which, run_fn=run)
    assert result["version"] == "0.5.7"
    assert len(result["models"]) == 3
    assert str(result["state"]) == "detected"


def test_detect_missing_runtime_offers_install(monkeypatch):
    monkeypatch.setattr("ai_loadout.runtimes.detect.net.port_open", lambda *a, **k: False)
    which = lambda name: None  # noqa: E731
    run = lambda *a, **k: RunResult(False, 127, "", "nf", found=False)  # noqa: E731
    result = detect_one(registry.by_key("ollama"), managers=["winget"], which_fn=which, run_fn=run)
    assert str(result["state"]) == "missing"
    assert "install" in result["actions"]


def test_detect_via_config_dir(tmp_path):
    (tmp_path / ".continue").mkdir()
    which = lambda name: None  # noqa: E731
    run = lambda *a, **k: RunResult(False, 127, "", "nf", found=False)  # noqa: E731
    result = detect_one(registry.by_key("continue"), which_fn=which, run_fn=run, home=tmp_path)
    assert str(result["state"]) == "configured"
    assert result["detail"] == "config found"


def test_detect_all_writes_components(loadout_home, monkeypatch):
    monkeypatch.setattr("ai_loadout.runtimes.detect.net.port_open", lambda *a, **k: False)
    store = StateStore(autosave=False)
    from ai_loadout.detect.system import scan

    scan(store)
    which = lambda name: None  # noqa: E731
    run = lambda *a, **k: RunResult(False, 127, "", "nf", found=False)  # noqa: E731
    results = detect_all(store, which_fn=which, run_fn=run, home=loadout_home)
    assert any(r["key"] == "ollama" for r in results)
    assert store.get_component("vscode") is not None
