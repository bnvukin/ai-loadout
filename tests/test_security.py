"""Tests for Layer 14 — security / integrity."""

from __future__ import annotations

import json

from ai_loadout.security.checksum import compute_sha256, verify_sha256
from ai_loadout.security.posture import build_trust_posture
from ai_loadout.security.sources import is_official_source


def test_is_official_source_accepts_vendor_hosts():
    assert is_official_source("https://github.com/bnvukin/ai-loadout/releases")
    assert is_official_source("https://pypi.org/simple/pip/")
    assert is_official_source("https://www.python.org/downloads/")
    assert is_official_source("git+https://github.com/bnvukin/ai-loadout")


def test_is_official_source_rejects_unknown_mirrors():
    assert not is_official_source("")
    assert not is_official_source("ftp://evil.example/tool.exe")
    assert not is_official_source("https://random-mirror.example/installer.exe")
    assert not is_official_source("not-a-url")


def test_sha256_pass_fail_and_tamper(tmp_path):
    target = tmp_path / "payload.bin"
    target.write_bytes(b"hello-loadout")
    digest = compute_sha256(target)
    assert verify_sha256(target, digest)
    assert not verify_sha256(target, "0" * 64)
    target.write_bytes(b"tampered")
    assert not verify_sha256(target, digest)


def test_trust_posture_shape():
    report = build_trust_posture()
    assert "summary" in report and "components" in report
    assert report["summary"]["total"] == len(report["components"])
    assert report["summary"]["total"] > 0
    sample = report["components"][0]
    assert {"key", "name", "method", "integrity", "install_ids"} <= set(sample.keys())


def test_security_cli_json(capsys):
    from ai_loadout.cli import main

    rc = main(["--json", "security"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert payload["policy"]["url_allowlist"] is True
