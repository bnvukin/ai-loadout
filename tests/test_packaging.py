"""Packaging smoke tests — dashboard static assets ship in the wheel."""

from __future__ import annotations

from ai_loadout import __version__
from ai_loadout.dashboard.assets import static_dir
from ai_loadout.dashboard.server import STATIC_DIR, create_app


def test_version_is_semver_like():
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_dashboard_static_bundle_present():
    root = static_dir()
    assert root.is_dir()
    assert (root / "index.html").is_file()
    assert (root / "app.js").is_file()
    assert (root / "style.css").is_file()
    assert STATIC_DIR == root


def test_create_app_serves_static_routes():
    client = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(create_app())
    assert client.get("/api/version").json()["version"] == __version__
    js = client.get("/static/app.js")
    assert js.status_code == 200
    assert len(js.content) > 100
