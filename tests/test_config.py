import os

import pytest

from ai_loadout.config import discover, edit, env, redact
from ai_loadout.core.lifecycle import Category
from ai_loadout.core.state import StateStore


# -- redaction --------------------------------------------------------------------------
def test_looks_secret_matches_credential_names():
    assert redact.looks_secret("OPENAI_API_KEY")
    assert redact.looks_secret("anthropic_token")
    assert redact.looks_secret("db_password")
    assert not redact.looks_secret("OLLAMA_HOST")
    assert not redact.looks_secret("PYTHONPATH")


def test_mask_keeps_only_edges():
    masked = redact.mask("sk-abcdefghijklmnop")
    assert masked.startswith("sk")
    assert "abcdefgh" not in masked
    assert redact.mask("tiny") == "***"
    assert redact.mask("") == ""


def test_redact_text_masks_json_and_known_tokens():
    text = '{\n  "apiKey": "sk-1234567890abcdefghij",\n  "model": "llama3"\n}'
    out, changed = redact.redact_text(text)
    assert changed is True
    assert "sk-1234567890abcdefghij" not in out
    assert "llama3" in out  # non-secret values survive


def test_redact_text_no_secret_is_unchanged():
    text = '{"model": "llama3", "temperature": 0.2}'
    out, changed = redact.redact_text(text)
    assert changed is False
    assert out == text


# -- env / PATH -------------------------------------------------------------------------
def test_inspect_env_redacts_secrets_and_reports_presence():
    fake = {"OLLAMA_HOST": "127.0.0.1:11434", "OPENAI_API_KEY": "sk-supersecretvalue123"}
    rows = {r["name"]: r for r in env.inspect_env(environ=fake)}
    assert rows["OLLAMA_HOST"]["present"] and rows["OLLAMA_HOST"]["value"] == "127.0.0.1:11434"
    assert rows["OPENAI_API_KEY"]["secret"] is True
    assert "supersecret" not in rows["OPENAI_API_KEY"]["value"]
    assert rows["CUDA_PATH"]["present"] is False and rows["CUDA_PATH"]["value"] is None


def test_inspect_all_env_returns_full_non_secret_values():
    long_val = "segment/" + ("x" * 480)
    fake = {"LOADOUT_LONG_PATH": long_val, "HF_TOKEN": "hf_abcdefghijklmnop1234567890"}
    rows = {r["name"]: r for r in env.inspect_all_env(environ=fake)}
    assert rows["LOADOUT_LONG_PATH"]["value"] == long_val
    assert len(rows["LOADOUT_LONG_PATH"]["value"]) == len(long_val)
    assert rows["HF_TOKEN"]["secret"] is True
    assert "abcdefgh" not in rows["HF_TOKEN"]["value"]


def test_path_summary_flags_missing_and_duplicates(tmp_path):
    real = str(tmp_path)
    missing = str(tmp_path / "does-not-exist")
    raw = os.pathsep.join([real, missing, real])  # real appears twice
    summary = env.path_summary(environ={"PATH": raw})
    assert summary["count"] == 3
    assert missing in summary["missing"]
    assert len(summary["duplicates"]) == 1


# -- discovery --------------------------------------------------------------------------
@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    ph = {
        "home": str(home),
        "appdata": str(home / "AppData" / "Roaming"),
        "localappdata": str(home / "AppData" / "Local"),
        "xdg_config": str(home / ".config"),
        "documents": str(home / "Documents"),
    }
    monkeypatch.setattr(discover, "_placeholders", lambda: ph)
    return home


def test_discover_one_picks_existing_candidate(fake_home):
    (fake_home / ".continue").mkdir()
    (fake_home / ".continue" / "config.json").write_text('{"models": []}', encoding="utf-8")
    from ai_loadout.config.registry import by_key

    cf = discover.discover_one(by_key("continue"), "linux")
    assert cf.exists is True
    assert cf.path.endswith("config.json")
    assert cf.size_bytes and cf.size_bytes > 0


def test_discover_all_records_existing_configs_in_twin(fake_home):
    (fake_home / ".gitconfig").write_text("[user]\n  name = Test\n", encoding="utf-8")
    store = StateStore(autosave=False)
    from ai_loadout.core.models import Hardware

    store.set_hardware(Hardware(os_family="linux"))
    results = discover.discover_all(store)
    assert any(cf.key == "git" and cf.exists for cf in results)
    comp = store.get_component("config:git")
    assert comp is not None and comp.category == Category.CONFIG


def test_read_config_redacts_secret_file(fake_home):
    (fake_home / ".docker").mkdir()
    (fake_home / ".docker" / "config.json").write_text(
        '{"auths": {"registry": {"auth": "c2VjcmV0OnRva2VuMTIzNDU2Nzg5"}}}', encoding="utf-8"
    )
    result = discover.read_config("docker", family="linux")
    assert result["exists"] is True
    assert result["redacted"] is True
    assert "c2VjcmV0OnRva2VuMTIzNDU2Nzg5" not in result["content"]


def test_read_config_unknown_key():
    result = discover.read_config("nope")
    assert result["exists"] is False and "error" in result


# -- editing (backup + trust gate) ------------------------------------------------------
def test_apply_edit_safe_creates_and_backs_up(fake_home):
    result = edit.apply_edit("continue", '{"models": [{"title": "local"}]}')
    assert result["created"] is True
    written = discover.read_config("continue", family="linux", redact=False)
    assert "local" in written["content"]


def test_apply_edit_advanced_requires_confirmation(fake_home):
    (fake_home / ".gitconfig").write_text("[user]\n  name = Old\n", encoding="utf-8")
    with pytest.raises(edit.EditError):
        edit.apply_edit("git", "[user]\n  name = New\n")
    result = edit.apply_edit("git", "[user]\n  name = New\n", confirm="CONFIRM")
    assert result["backup"] is not None
    assert os.path.isfile(result["backup"])
    now = discover.read_config("git", family="linux")
    assert "New" in now["content"]
