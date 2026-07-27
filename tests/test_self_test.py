"""Tests for loadout self-test (install confidence checks)."""

from __future__ import annotations

from ai_loadout.self_test.runner import run_self_test


def _offline_probe(**_kwargs):
    return {"online": False, "probe": "mock", "latency_ms": 0, "reason": "mock offline"}


def test_self_test_passes_hermetic(monkeypatch, tmp_path):
    monkeypatch.setenv("LOADOUT_HOME", str(tmp_path / "home"))
    result = run_self_test(
        bind_http=False,
        use_temp_home=True,
        skip_default_home=True,
        connectivity_fn=_offline_probe,
    )
    assert result["ok"] is True
    assert result["failed"] == 0
    names = {c["name"] for c in result["checks"]}
    assert "imports_and_version" in names
    assert "dashboard_static_assets" in names
    assert "machine_scan" in names
    assert "offline_probe" in names


def test_self_test_json_via_cli(capsys):
    from ai_loadout.cli import main

    rc = main(["--json", "self-test"])
    out = capsys.readouterr().out
    assert rc == 0
    import json

    payload = json.loads(out)
    assert payload.get("ok") is True
    assert payload.get("total", 0) >= 8


def test_doctor_self_test_alias(capsys):
    from ai_loadout.cli import main

    rc = main(["doctor", "--self-test"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Self-test PASSED" in out


def test_self_test_fails_on_bad_version(monkeypatch, tmp_path):
    monkeypatch.setenv("LOADOUT_HOME", str(tmp_path / "home"))

    import ai_loadout

    real = ai_loadout.__version__
    monkeypatch.setattr(ai_loadout, "__version__", "not-semver")
    try:
        result = run_self_test(
            skip_default_home=True,
            connectivity_fn=_offline_probe,
        )
        assert result["ok"] is False
        failed = {c["name"] for c in result["checks"] if not c["ok"]}
        assert "imports_and_version" in failed
    finally:
        monkeypatch.setattr(ai_loadout, "__version__", real)


def test_self_test_cli_subcommands_registered():
    from ai_loadout.cli import build_parser

    parser = build_parser()
    subs = []
    for action in parser._actions:
        if getattr(action, "choices", None):
            subs = list(action.choices.keys())
            break
    assert "self-test" in subs
