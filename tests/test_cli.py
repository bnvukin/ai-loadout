import json

from ai_loadout.cli import main


def test_version_plain(capsys):
    rc = main(["version"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Loadout" in out


def test_version_json(capsys):
    rc = main(["--json", "version"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["name"] == "ai-loadout"
    assert payload["version"]


def test_info_without_state_is_graceful(capsys, loadout_home):
    rc = main(["info"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "No machine scan on record yet" in out


def test_no_command_prints_help(capsys):
    rc = main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "usage" in out.lower()
