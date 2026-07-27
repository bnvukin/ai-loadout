"""Run install self-tests — validates the package without mutating the user's system."""

from __future__ import annotations

import os
import shutil
import socket
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

CheckFn = Callable[[], dict]


def _check(name: str, fn: CheckFn) -> dict:
    try:
        detail = fn()
        if isinstance(detail, dict):
            ok = bool(detail.get("ok", True))
            row = {"name": name, "ok": ok, **detail}
        else:
            row = {"name": name, "ok": True, "detail": str(detail)}
    except Exception as exc:
        row = {"name": name, "ok": False, "detail": str(exc)}
    if "detail" not in row and row.get("ok"):
        row["detail"] = "ok"
    return row


def _check_imports() -> dict:
    import ai_loadout.cli  # noqa: F401
    from ai_loadout import __version__

    parts = __version__.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return {"ok": False, "detail": f"unexpected version format: {__version__}"}
    return {"ok": True, "detail": __version__, "version": __version__}


def _check_cli_parser() -> dict:
    from ai_loadout.cli import build_parser

    parser = build_parser()
    subs: list[str] = []
    for action in parser._actions:
        if getattr(action, "choices", None):
            subs = list(action.choices.keys())
            break
    required = {"scan", "health", "doctor", "dashboard", "self-test"}
    missing = required - set(subs)
    if missing:
        return {"ok": False, "detail": f"missing subcommands: {sorted(missing)}"}
    return {"ok": True, "detail": f"{len(subs)} subcommands registered"}


def _check_dashboard_static() -> dict:
    from ai_loadout.dashboard.assets import static_dir

    root = static_dir()
    for name in ("index.html", "app.js", "style.css"):
        if not (root / name).is_file():
            return {"ok": False, "detail": f"missing {name} under {root}"}
    return {"ok": True, "detail": str(root)}


def _check_dashboard_app() -> dict:
    from ai_loadout.core.state import StateStore
    from ai_loadout.dashboard.server import create_app

    app = create_app(StateStore(autosave=False))
    routes = {getattr(r, "path", None) for r in app.routes}
    if "/api/version" not in routes:
        return {"ok": False, "detail": "create_app missing /api/version route"}
    return {"ok": True, "detail": "FastAPI app constructed"}


def _check_dashboard_testclient() -> dict:
    from fastapi.testclient import TestClient

    from ai_loadout.core.state import StateStore
    from ai_loadout.dashboard.server import create_app

    client = TestClient(create_app(StateStore(autosave=False)))
    root = client.get("/")
    if root.status_code != 200:
        return {"ok": False, "detail": f"GET / returned {root.status_code}"}
    js = client.get("/static/app.js")
    if js.status_code != 200 or len(js.content) < 100:
        return {"ok": False, "detail": f"GET /static/app.js returned {js.status_code}"}
    ver = client.get("/api/version").json()
    return {"ok": True, "detail": f"HTTP routes OK (version {ver.get('version')})"}


def _free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _check_dashboard_bind_http(host: str = "127.0.0.1", timeout: float = 15.0) -> dict:
    try:
        import uvicorn
    except ImportError:
        return {"ok": False, "detail": "uvicorn not installed (pip install ai-loadout[dashboard])"}

    from ai_loadout.core.state import StateStore
    from ai_loadout.dashboard.server import create_app

    port = _free_port(host)
    config = uvicorn.Config(
        create_app(StateStore(autosave=False)),
        host=host,
        port=port,
        log_level="error",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="loadout-self-test-http", daemon=True)
    thread.start()

    base = f"http://{host}:{port}"
    deadline = time.monotonic() + timeout
    last_error = "server did not start"
    try:
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(base + "/", timeout=1.0) as resp:
                    if resp.getcode() >= 400:
                        last_error = f"GET / HTTP {resp.getcode()}"
                        time.sleep(0.1)
                        continue
                with urllib.request.urlopen(base + "/static/app.js", timeout=1.0) as resp:
                    body = resp.read()
                    if len(body) < 100:
                        return {"ok": False, "detail": "GET /static/app.js body too small"}
                return {"ok": True, "detail": f"bound {base} (GET / + /static/app.js)"}
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = str(exc)
                time.sleep(0.15)
        return {"ok": False, "detail": last_error}
    finally:
        server.should_exit = True
        thread.join(timeout=5.0)


def _check_data_dir_writable(temp_home: Path) -> dict:
    from ai_loadout.core import paths

    paths.ensure_dirs()
    probe = paths.data_dir() / ".self-test-touch"
    probe.write_text("ok\n", encoding="utf-8")
    probe.unlink(missing_ok=True)
    if str(paths.data_dir()) != str(temp_home):
        return {"ok": False, "detail": f"LOADOUT_HOME mismatch: {paths.data_dir()}"}
    return {"ok": True, "detail": f"writable under {paths.data_dir()}"}


def _check_default_home_writable() -> dict:
    home = Path.home()
    loadout_home = home / ".ai-loadout"
    if not os.access(home, os.W_OK):
        return {"ok": False, "detail": f"home not writable: {home}"}
    try:
        loadout_home.mkdir(exist_ok=True)
        probe = loadout_home / ".self-test-touch"
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        return {"ok": False, "detail": str(exc)}
    return {"ok": True, "detail": str(loadout_home)}


def _check_scan(store) -> dict:
    from ai_loadout.detect.system import scan

    hw = scan(store)
    if hw is None or not hw.os_name:
        return {"ok": False, "detail": "scan returned no hardware"}
    return {
        "ok": True,
        "detail": f"{hw.os_name}, {hw.ram_total_gb} GB RAM",
        "os": hw.os_name,
    }


def _check_security(store) -> dict:
    from ai_loadout.security.posture import build_trust_posture

    report = build_trust_posture(store)
    if not isinstance(report, dict):
        return {"ok": False, "detail": "invalid posture response"}
    return {"ok": True, "detail": f"{len(report.get('components', []))} components scored"}


def _check_connections() -> dict:
    from ai_loadout.connections.registry import build_connections_report

    report = build_connections_report()
    total = report.get("total", 0)
    if total < 1:
        return {"ok": False, "detail": "no connections defined"}
    return {"ok": True, "detail": f"{report.get('connected_count', 0)}/{total} connected"}


def _check_offline_probe(connectivity_fn: Callable[..., dict] | None = None) -> dict:
    from ai_loadout.offline.connectivity import check_connectivity

    probe = connectivity_fn or check_connectivity
    result = probe(timeout=2.0)
    online = result.get("online")
    return {
        "ok": True,
        "detail": f"online={online}" if online is not None else "probe returned",
        "online": online,
    }


def run_self_test(
    *,
    bind_http: bool = False,
    use_temp_home: bool = True,
    skip_default_home: bool = False,
    connectivity_fn: Callable[..., dict] | None = None,
) -> dict:
    """Run all install confidence checks. Returns summary with ``ok`` and ``checks`` list."""

    from ai_loadout.core.state import StateStore

    temp_ctx = tempfile.TemporaryDirectory(prefix="loadout-self-test-")
    temp_home = Path(temp_ctx.name)
    prev_home = os.environ.get("LOADOUT_HOME")
    if use_temp_home:
        os.environ["LOADOUT_HOME"] = str(temp_home)

    checks: list[dict] = []
    try:
        checks.append(_check("imports_and_version", _check_imports))
        checks.append(_check("cli_subcommands", _check_cli_parser))
        checks.append(_check("dashboard_static_assets", _check_dashboard_static))
        checks.append(_check("dashboard_app_import", _check_dashboard_app))
        checks.append(_check("dashboard_http_testclient", _check_dashboard_testclient))
        if bind_http:
            checks.append(_check("dashboard_http_bind", lambda: _check_dashboard_bind_http()))
        if use_temp_home:
            checks.append(
                _check("loadout_home_writable", lambda: _check_data_dir_writable(temp_home))
            )
        if not skip_default_home:
            checks.append(_check("default_home_writable", _check_default_home_writable))

        store = StateStore(autosave=False)
        checks.append(_check("machine_scan", lambda: _check_scan(store)))
        checks.append(_check("security_posture", lambda: _check_security(store)))
        checks.append(_check("connections_probe", _check_connections))
        checks.append(_check("offline_probe", lambda: _check_offline_probe(connectivity_fn)))
    finally:
        if use_temp_home:
            if prev_home is None:
                os.environ.pop("LOADOUT_HOME", None)
            else:
                os.environ["LOADOUT_HOME"] = prev_home
            shutil.rmtree(temp_ctx.name, ignore_errors=True)

    passed = sum(1 for c in checks if c.get("ok"))
    failed = [c for c in checks if not c.get("ok")]
    return {
        "ok": len(failed) == 0,
        "passed": passed,
        "failed": len(failed),
        "total": len(checks),
        "checks": checks,
        "failures": [{"name": c["name"], "detail": c.get("detail")} for c in failed],
    }
