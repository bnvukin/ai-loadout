"""Command-line entry point for Loadout.

Subcommands are added as each layer lands. Today: ``version`` and ``info`` (read the
persisted digital twin). ``scan``, ``plan``, ``health``, ``models`` and ``dashboard``
are wired up in their respective modules.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from . import __version__

BANNER = r"""
  _                    _             _
 | |    ___  __ _  __| | ___  _   _| |_
 | |   / _ \/ _` |/ _` |/ _ \| | | | __|
 | |__| (_) | (_| | (_| | (_) | |_| | |_
 |_____\___/ \__,_|\__,_|\___/ \__,_|\__|
 turn any machine into an AI workstation
"""


def _print_json(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def cmd_version(args: argparse.Namespace) -> int:
    if args.json:
        _print_json({"name": "ai-loadout", "version": __version__})
    else:
        print(f"Loadout {__version__}")
    return 0


_DECISION_SYMBOL = {
    "skip": "[ ok    ]",
    "upgrade": "[ update]",
    "install": "[missing]",
    "manual": "[missing]",
}


def _render_deps(results: list) -> None:
    print("\nToolchain:")
    for r in results:
        symbol = _DECISION_SYMBOL.get(r["decision"], "[  ?   ]")
        version = r["version"] or ""
        opt = "  (optional)" if r.get("optional") and r["decision"] in ("install", "manual") else ""
        print(f"  {symbol} {r['name']:<26} {version:<12} {r['detail']}{opt}")


def _render_runtimes(results: list) -> None:
    print("\nAI runtimes:")
    for r in results:
        present = str(r["state"]) != "missing"
        symbol = "[ ok    ]" if present else "[missing]"
        version = r["version"] or ""
        opt = "  (optional)" if r.get("optional") and not present else ""
        print(f"  {symbol} {r['name']:<26} {version:<12} {r['detail']}{opt}")


def cmd_scan(args: argparse.Namespace) -> int:
    """Layers 1-2 - read-only machine + toolchain scan; writes into the digital twin."""

    from .core.state import load_state
    from .deps.detect import detect_all
    from .detect.system import scan, summarize
    from .runtimes.detect import detect_all as detect_runtimes

    store = load_state()
    hw = scan(store)
    dep_results = detect_all(store)
    rt_results = detect_runtimes(store)
    if args.json:
        _print_json(store.snapshot())
        return 0
    print(BANNER)
    for line in summarize(hw):
        print(line)
    _render_deps(dep_results)
    _render_runtimes(rt_results)
    if hw.warnings:
        print("\nNotes:")
        for warning in hw.warnings:
            print(f"  ! {warning}")
    print("\nSaved to the digital twin.  Next:  loadout models   |   loadout dashboard")
    return 0


def cmd_runtimes(args: argparse.Namespace) -> int:
    """Layer 3 - detect installed AI runtimes, editors and agent CLIs."""

    from .core.state import load_state
    from .runtimes.detect import detect_all as detect_runtimes

    store = load_state()
    if store.hardware is None:
        from .detect.system import scan

        scan(store)
    results = detect_runtimes(store)
    if args.json:
        _print_json({"runtimes": results, "models": [m.to_dict() for m in store.models()]})
        return 0
    _render_runtimes(results)
    if store.models():
        print("\nLocal models:")
        for m in store.models():
            size = f"{m.size_gb} GB" if m.size_gb else ""
            print(f"  - {m.name:<28} {size}")
    return 0


def cmd_deps(args: argparse.Namespace) -> int:
    """Layer 2 - detect the developer toolchain and decide skip/upgrade/install."""

    from .core.state import load_state
    from .deps.detect import detect_all
    from .deps.managers import available_managers

    store = load_state()
    if store.hardware is None:
        from .detect.system import scan

        scan(store)
    results = detect_all(store)
    if args.json:
        _print_json({"managers": available_managers(), "dependencies": results})
        return 0
    print(f"Package managers available: {', '.join(available_managers()) or 'none'}")
    _render_deps(results)
    return 0


def cmd_models(args: argparse.Namespace) -> int:
    """Layer 4 - hardware-aware model recommendations as a comparison table."""

    from .core.state import load_state
    from .models.recommend import recommend_for_store, stars, why

    store = load_state()
    recs = recommend_for_store(store)
    if args.json:
        _print_json(
            {
                "hardware": store.hardware.to_dict() if store.hardware else None,
                "recommendations": [r.to_dict() for r in recs],
            }
        )
        return 0

    print(BANNER)
    header = (
        f"{'Model':<22} {'Best for':<22} {'Code':<5} {'Reason':<6} "
        f"{'Speed':<6} {'RAM':>5} {'tok/s':>6}  {'Fit':<8} Label"
    )
    print(header)
    print("-" * len(header))
    for r in recs:
        ram = f"{int(r.spec.min_ram_gb)}G"
        print(
            f"{r.spec.name:<22.22} {r.spec.best_for:<22.22} {stars(r.spec.coding):<5} "
            f"{stars(r.spec.reasoning):<6} {stars(r.effective_speed):<6} {ram:>5} "
            f"{r.tokens_per_sec:>6}  {r.fit:<8} {r.labels[0] if r.labels else ''}"
        )
    best = next((r for r in recs if r.fit != "too_big"), None)
    if best and store.hardware:
        print("\nWhy this pick:")
        print("  " + why(store.hardware, best))
    print("\n(Ratings: */ ..... out of 5. 'Fit' is for THIS machine's RAM/VRAM.)")
    return 0


_SEVERITY_SYMBOL = {"error": "[X]", "warning": "[!]", "info": "[i]"}


def cmd_health(args: argparse.Namespace) -> int:
    """Layer 10 - run a health check and list actionable issues."""

    from .core.state import load_state
    from .health.checker import health_from_scratch

    store = load_state()
    report = health_from_scratch(store)
    if args.json:
        _print_json(report.to_dict())
        return 0
    print(BANNER)
    print(f"Overall health: {report.percent}%  ({report.status})")
    counts = report.counts
    print(
        f"Components: {counts.get('green', 0)} healthy, {counts.get('yellow', 0)} attention, "
        f"{counts.get('red', 0)} broken, {counts.get('gray', 0)} not installed"
    )
    if not report.issues:
        print("\nEverything looks good. No issues found.")
        return 0
    print(f"\n{len(report.issues)} issue(s):")
    for issue in report.issues:
        symbol = _SEVERITY_SYMBOL.get(issue.severity, "[?]")
        fixable = "  (fixable)" if issue.fixable else ""
        print(f"  {symbol} {issue.title}{fixable}")
        print(f"       -> {issue.fix}")
    print("\nRun 'loadout doctor' for full explanations.")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Layer 13 - explain each issue in plain language (what/why/fix/restart)."""

    if getattr(args, "self_test", False):
        return cmd_self_test(args)

    from .core.state import load_state
    from .health.checker import health_from_scratch

    store = load_state()
    report = health_from_scratch(store)
    if args.json:
        _print_json(report.to_dict())
        return 0
    print(BANNER)
    if not report.issues:
        print("AI Doctor: no problems detected. Your workstation looks healthy.")
        return 0
    for issue in report.issues:
        symbol = _SEVERITY_SYMBOL.get(issue.severity, "[?]")
        print(f"\n{symbol} {issue.title}")
        print(f"   What:    {issue.explanation}")
        print(f"   Fix:     {issue.fix}")
        if issue.why:
            print(f"   Why:     {issue.why}")
        if issue.restart and issue.restart != "none":
            print(f"   Restart: {issue.restart}")
    return 0


_TRUST_TAG = {"safe": "[safe]", "advanced": "[adv!]", "expert": "[EXP!]"}


def _render_config_list(configs: list) -> None:
    print("\nConfig files:")
    for cf in configs:
        tag = _TRUST_TAG.get(cf["trust"], "[?]")
        mark = "[ ok    ]" if cf["exists"] else "[absent ]"
        secret = "  (secrets redacted)" if cf["secret"] and cf["exists"] else ""
        print(f"  {mark} {tag} {cf['name']:<22} {cf['path'] or ''}{secret}")


def _render_env(rows: list) -> None:
    present = [r for r in rows if r["present"]]
    print(f"\nEnvironment variables ({len(present)} of {len(rows)} set):")
    for r in present:
        value = r["value"] if r["value"] is not None else ""
        print(f"  {r['name']:<22} = {value}")


def _render_path(summary: dict) -> None:
    print(f"\nPATH: {summary['count']} entries", end="")
    extras = []
    if summary["missing"]:
        extras.append(f"{len(summary['missing'])} missing")
    if summary["duplicates"]:
        extras.append(f"{len(summary['duplicates'])} duplicate")
    print(f"  ({', '.join(extras)})" if extras else "  (all present, no duplicates)")
    for entry in summary["entries"]:
        flags = []
        if not entry["exists"]:
            flags.append("MISSING")
        if entry["duplicate"]:
            flags.append("DUP")
        suffix = f"   <- {', '.join(flags)}" if flags else ""
        print(f"    {entry['path']}{suffix}")


def cmd_config(args: argparse.Namespace) -> int:
    """Config Center - discover configs, inspect env vars and PATH (read-only)."""

    from .config.discover import discover_all, read_config
    from .config.env import inspect_env, path_summary
    from .core.state import load_state

    store = load_state()

    if args.show:
        result = read_config(args.show)
        if args.json:
            _print_json(result)
            return 0
        if not result.get("exists"):
            print(f"'{args.show}': not found ({result.get('path') or 'no known path'}).")
            return 1
        if "error" in result:
            print(f"Could not read '{args.show}': {result['error']}")
            return 1
        note = "  (secrets redacted)" if result.get("redacted") else ""
        print(f"# {result['path']}{note}\n")
        print(result["content"])
        if result.get("truncated"):
            print("\n... (truncated)")
        return 0

    configs = [cf.to_dict() for cf in discover_all(store)]
    env_rows = inspect_env()
    path = path_summary()

    if args.json:
        _print_json({"configs": configs, "env": env_rows, "path": path})
        return 0
    if args.env:
        _render_env(env_rows)
        return 0
    if args.path:
        _render_path(path)
        return 0

    print(BANNER)
    _render_config_list(configs)
    _render_env(env_rows)
    _render_path(path)
    print("\nView one file:  loadout config --show <key>   (secrets are always redacted)")
    return 0


_ACTION_SYMBOL = {
    "install": "[install]",
    "upgrade": "[upgrade]",
    "pull": "[ pull  ]",
    "skip": "[ have  ]",
    "manual": "[manual ]",
}


def cmd_plan(args: argparse.Namespace) -> int:
    """Layer 18 - build a dry-run install plan for a profile (+capabilities)."""

    from .core.state import load_state
    from .plan.planner import build_plan_from_scratch
    from .profiles.registry import PROFILES

    if args.list:
        print(BANNER)
        print("Available profiles (loadouts):\n")
        for p in PROFILES:
            print(f"  {p.key:<15} {p.name}")
            print(f"  {'':<15} {p.description}")
            print(f"  {'':<15} caps: {', '.join(p.capabilities) or '-'}\n")
        print("Use:  loadout plan --profile <key> [--capabilities a,b] [--no-models]")
        return 0

    if not args.profile and not args.capabilities:
        print("Pick a profile or capabilities. See:  loadout plan --list")
        return 2

    store = load_state()
    caps = [c.strip() for c in (args.capabilities or "").split(",") if c.strip()]
    plan = build_plan_from_scratch(store, args.profile, caps, include_models=not args.no_models)
    if args.json:
        _print_json(plan.to_dict())
        return 0

    print(BANNER)
    title = plan.profile or "custom"
    print(f"Install plan for profile: {title}")
    if plan.capabilities:
        print(f"Capabilities: {', '.join(plan.capabilities)}")
    print()
    for step in plan.steps:
        symbol = _ACTION_SYMBOL.get(step.action, "[   ?   ]")
        opt = "  (optional)" if step.optional and step.action in ("install", "manual") else ""
        print(f"  {symbol} {step.name:<26} {step.reason}{opt}")
        if step.command:
            print(f"            $ {step.command}")
    summary = plan.summary()
    parts = [f"{v} to {k}" for k, v in summary.items() if k != "skip"]
    have = summary.get("skip", 0)
    print(f"\nSummary: {', '.join(parts) or 'nothing to do'} ({have} already present).")
    print("This is a dry run. Nothing was installed.")
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    """Serve the live dashboard (FastAPI + WebSocket over the digital twin)."""

    from .dashboard.run import serve

    return serve(host=args.host, port=args.port, open_browser=not args.no_browser)


def cmd_security(args: argparse.Namespace) -> int:
    """Layer 14 - print the trust / integrity posture (read-only)."""

    from .core.state import load_state
    from .security.posture import build_trust_posture

    store = load_state()
    report = build_trust_posture(store)
    if args.json:
        _print_json(report)
        return 0
    print(BANNER)
    s = report["summary"]
    mgr = report.get("preferred_manager") or "none"
    print(f"Platform: {report['platform']}  |  preferred manager: {mgr}")
    print(
        f"Installable components: {s['total']} total — "
        f"{s['package_manager']} via package manager, "
        f"{s['manual']} manual, {s['detect_only']} detect-only"
    )
    print("\nComponent integrity:")
    for c in report["components"]:
        via = c["manager"] or c["method"]
        print(f"  {c['name']:<24} {via:<18} {c['integrity']}")
    print("\nPolicy: official URL allowlist active; SHA256 for direct downloads when used.")
    return 0


def cmd_diagnostics(args: argparse.Namespace) -> int:
    """Layer 15 - bundle logs + state into a redacted diagnostics zip (read-only)."""

    from .core.state import load_state
    from .diagnostics.bundle import create_diagnostics_bundle

    store = load_state()
    result = create_diagnostics_bundle(store)
    if args.json:
        _print_json(result)
        return 0
    print(BANNER)
    print(f"Diagnostics bundle: {result['path']}")
    print(f"Members ({len(result['members'])}): {', '.join(result['members'])}")
    print("Secrets and API keys are redacted. Share only with people you trust.")
    return 0


def cmd_backup(args: argparse.Namespace) -> int:
    """Layer 17 - create or list global config snapshots (read-only)."""

    from .backup.snapshot import create_snapshot, list_snapshots

    if args.list:
        snaps = list_snapshots()
        if args.json:
            _print_json({"snapshots": snaps})
            return 0
        print(BANNER)
        if not snaps:
            print("No global snapshots yet. Run:  loadout backup")
            return 0
        print("Global config snapshots:\n")
        for s in snaps:
            ts = s.get("timestamp")
            when = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)) if ts else "?"
            print(f"  {s['id']}  ({s['file_count']} files)  {when}")
        return 0

    from .core.state import load_state

    store = load_state()
    result = create_snapshot(store)
    if args.json:
        _print_json(result)
        return 0
    print(BANNER)
    print(f"Snapshot created: {result['id']}  ({result['file_count']} files)")
    print(f"Location: {result['path']}")
    print("Restore from the dashboard (requires typing RESTORE).")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    """Layer 17 - restore a global snapshot (destructive; requires --confirm RESTORE)."""

    from .backup.snapshot import RestoreError, restore_snapshot

    if not args.id:
        print("Usage:  loadout restore <snapshot-id> --confirm RESTORE")
        return 2
    try:
        result = restore_snapshot(args.id, confirm=args.confirm)
    except RestoreError as exc:
        print(f"Restore blocked: {exc}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(result)
        return 0
    print(BANNER)
    print(f"Restored snapshot {result['id']} ({result['file_count']} files).")
    for item in result["restored"]:
        print(f"  - {item['key']}: {item['path']}")
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    """Layer 5 - dry-run direct download plan (official-source check)."""

    from .download.manager import plan_download

    plan = plan_download(args.url, dest=args.dest, expected_sha256=args.sha256)
    if args.json:
        _print_json(plan)
        return 0 if plan["ok"] else 1
    print(BANNER)
    if not plan["ok"]:
        print(f"Blocked: {plan['reason']}")
        return 1
    print(f"URL:     {plan['url']}  (official source)")
    print(f"Save to: {plan['dest']}")
    if plan["resume_bytes"]:
        print(f"Resume:  {plan['resume_bytes']} bytes already in .part file")
    if plan["verify_sha256"]:
        print(f"SHA256:  {plan['verify_sha256']}")
    print("\nThis is a dry run. Run the download from the dashboard after confirming.")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    """Layer 16 - check for Loadout + component updates (read-only)."""

    from .core.state import load_state
    from .update.report import build_update_report

    store = load_state()
    report = build_update_report(store)
    if args.json:
        _print_json(report)
        return 0
    print(BANNER)
    self_info = report["self"]
    print(f"Loadout: {self_info['current']}", end="")
    if self_info.get("offline"):
        print("  (could not reach PyPI — offline or blocked)")
    elif self_info.get("update_available"):
        print(f"  ->  {self_info['latest']} available")
        print(f"  Upgrade: {self_info.get('upgrade_hint', 'pip install --upgrade ai-loadout')}")
    else:
        latest = self_info.get("latest") or "?"
        print(f"  (latest on PyPI: {latest})")
    comps = report["components"]
    if not comps:
        print("\nNo component upgrades detected. Run `loadout scan` if the twin is stale.")
    else:
        print(f"\n{len(comps)} component(s) can be upgraded:")
        for c in comps:
            print(
                f"  {c['name']:<22} {c.get('current') or 'missing':<12} (min {c.get('minimum') or '?'})"
            )
    print(f"\nRollback Loadout: {report['rollback']['loadout']}")
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    """Layer 12 - run a bounded local benchmark (non-destructive)."""

    from .benchmark.runner import latest_benchmark, run_benchmark
    from .core.state import load_state

    if args.latest:
        result = latest_benchmark()
        if result is None:
            print("No benchmark on record yet. Run:  loadout benchmark")
            return 1
        if args.json:
            _print_json(result)
            return 0
        print(BANNER)
        print(f"Latest benchmark (tier: {result['tier']['tier']})")
        print(f"  CPU score:   {result['cpu']['score']}")
        print(f"  Disk write:  {result['disk']['write_mbps']} MB/s")
        print(f"  Disk read:   {result['disk']['read_mbps']} MB/s")
        inf = result.get("inference") or {}
        if inf.get("skipped"):
            print(f"  Inference:   skipped ({inf.get('reason', 'n/a')})")
        else:
            print(f"  Inference:   {inf.get('tokens_per_sec')} tok/s")
        return 0

    store = load_state()
    result = run_benchmark(store, fast=not args.full, bus=None)
    if args.json:
        _print_json(result)
        return 0
    print(BANNER)
    print(f"Benchmark complete — recommended tier: {result['tier']['tier']}")
    print(f"  {result['tier']['label']}")
    print(f"  CPU score:   {result['cpu']['score']}")
    print(
        f"  Disk write:  {result['disk']['write_mbps']} MB/s  read: {result['disk']['read_mbps']} MB/s"
    )
    print(f"  Saved:       {result['path']}")
    return 0


def cmd_vscode(args: argparse.Namespace) -> int:
    """Layer 6 - preview VS Code / Cursor settings merge (read-only)."""

    from .core.state import load_state
    from .vscode.config import preview

    store = load_state()
    result = preview(store, editor=args.editor)
    if args.json:
        _print_json(result)
        return 0 if result.get("ok") else 1
    print(BANNER)
    if not result.get("ok"):
        print(result.get("reason", "preview failed"))
        return 1
    print(f"Editor: {result['editor']}  |  path: {result['settings_path']}")
    print(f"Keys to add/merge: {', '.join(result['keys_added']) or 'none (already set)'}")
    print(f"\nRecommended extensions ({len(result['extensions'])}):")
    for ext in result["extensions"]:
        opt = " (optional)" if ext.get("optional") else ""
        print(f"  - {ext['id']:<40} {ext['name']}{opt}")
    print("\nApply from the dashboard (backs up settings.json first).")
    return 0


def cmd_continue(args: argparse.Namespace) -> int:
    """Layer 7 - preview Continue config generation (read-only)."""

    from .continue_cfg.builder import preview
    from .core.state import load_state

    store = load_state()
    result = preview(store)
    if args.json:
        _print_json(result)
        return 0 if result.get("ok") else 1
    print(BANNER)
    print(f"Format: {result.get('format')} schema {result.get('schema')}")
    print(f"Path:   {result.get('path')}")
    print(result.get("note", ""))
    print("\n--- preview ---\n")
    print(result.get("content", ""))
    return 0


def cmd_agents(args: argparse.Namespace) -> int:
    """Layer 8 - preview agent/MCP scaffold (read-only)."""

    from .agents.config import preview
    from .core.state import load_state

    store = load_state()
    result = preview(store)
    if args.json:
        _print_json(result)
        return 0 if result.get("ok") else 1
    print(BANNER)
    print(f"Detected agents: {len(result.get('agents', []))}")
    for a in result.get("agents", []):
        print(f"  - {a.get('name')} ({a.get('key')})")
    print(f"\nMCP config: {result.get('mcp_path')}")
    print(result.get("note", ""))
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    """Layer 9 - scaffold a project template into a new directory."""

    from .templates.registry import list_templates, preview_template, scaffold_template

    if args.list:
        items = list_templates()
        if args.json:
            _print_json({"templates": items})
            return 0
        print(BANNER)
        for t in items:
            print(f"  {t['key']:<15} {t['name']} ({t['files']} files)")
            print(f"  {'':<15} {t['description']}\n")
        return 0

    if not args.template or not args.name:
        print("Usage:  loadout new <template> <name> [--dir PATH] [--force]")
        print("        loadout new --list")
        return 2

    if args.preview:
        result = preview_template(args.template, args.name)
        if args.json:
            _print_json(result)
            return 0 if result.get("ok") else 1
        print(BANNER)
        for f in result.get("files", []):
            print(f"  {f['path']}  ({f['bytes']} bytes)")
        return 0

    target = args.dir or args.name
    result = scaffold_template(args.template, args.name, target, force=args.force)
    if args.json:
        _print_json(result)
        return 0 if result.get("ok") else 1
    if not result.get("ok"):
        print(result.get("reason", "scaffold failed"), file=sys.stderr)
        return 1
    print(BANNER)
    print(f"Created {result['file_count']} file(s) in {result['target']}")
    for path in result.get("written", []):
        print(f"  - {path}")
    return 0


def cmd_offline(args: argparse.Namespace) -> int:
    """Layer 19 - connectivity + offline capabilities report (read-only)."""

    from .offline.report import build_offline_report

    report = build_offline_report()
    if args.json:
        _print_json(report)
        return 0
    print(BANNER)
    online = report.get("online")
    print(f"Connectivity: {'online' if online else 'offline'}")
    conn = report.get("connectivity", {})
    if conn.get("reason"):
        print(f"  Reason: {conn['reason']}")
    print(f"Cache entries: {report.get('cache_count', 0)}")
    print("\nWorks offline:")
    for item in report.get("works_offline", []):
        print(f"  - {item}")
    print("\nNeeds network:")
    for item in report.get("needs_network", []):
        print(f"  - {item}")
    return 0


def cmd_self_test(args: argparse.Namespace) -> int:
    """Wave F - validate the install end-to-end (read-only / self-cleaning)."""

    from .self_test.runner import run_self_test

    result = run_self_test(bind_http=getattr(args, "bind_http", False))
    if args.json:
        _print_json(result)
        return 0 if result.get("ok") else 1
    print(BANNER)
    print("Loadout self-test — install confidence check\n")
    for row in result.get("checks", []):
        mark = "PASS" if row.get("ok") else "FAIL"
        print(f"  [{mark}] {row['name']:<28} {row.get('detail', '')}")
    print(f"\n{result.get('passed', 0)}/{result.get('total', 0)} passed")
    if not result.get("ok"):
        print("\nSelf-test FAILED — fix the items above before relying on this install.")
        return 1
    print("\nSelf-test PASSED — package, CLI, dashboard, and core probes look good.")
    return 0


def cmd_telemetry(args: argparse.Namespace) -> int:
    """Layer 20 - telemetry opt-in status (read-only)."""

    from .telemetry.collector import preview_payload, status

    result = preview_payload() if args.preview else status()
    if args.json:
        _print_json(result)
        return 0
    print(BANNER)
    print(f"Telemetry: {'enabled' if result.get('enabled') else 'disabled (default)'}")
    print(f"Transmission: {'none (local-only)' if not result.get('transmission') else 'yes'}")
    print(result.get("note", ""))
    if args.preview and result.get("sample"):
        print("\nSample payload fields:")
        for key, value in result["sample"].items():
            print(f"  {key}: {value}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show the last persisted digital-twin snapshot without rescanning."""

    from .core.state import load_state

    store = load_state()
    snap = store.snapshot()
    if args.json:
        _print_json(snap)
        return 0

    health = snap["health"]
    print(BANNER)
    print(f"Overall health: {health['percent']}%  ({health['status']})")
    hw = snap.get("hardware")
    if hw:
        print(
            f"Machine: {hw.get('os_name', '?')} | {hw.get('cpu_name', '?')} | "
            f"{hw.get('ram_total_gb', '?')} GB RAM | VRAM {hw.get('total_vram_gb', 0)} GB"
        )
    else:
        print("No machine scan on record yet. Run: loadout scan")
    comps = snap.get("components", [])
    if comps:
        print(f"\nComponents ({len(comps)}):")
        for c in comps:
            print(f"  [{c['health']:<6}] {c['name']:<18} {c['state']:<12} {c.get('version') or ''}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="loadout",
        description="Turn any machine into a production-ready AI development workstation.",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable JSON output")
    parser.add_argument("--version", action="version", version=f"Loadout {__version__}")

    sub = parser.add_subparsers(dest="command")

    p_version = sub.add_parser("version", help="print the Loadout version")
    p_version.set_defaults(func=cmd_version)

    p_info = sub.add_parser("info", help="show the last persisted machine snapshot")
    p_info.set_defaults(func=cmd_info)

    p_scan = sub.add_parser("scan", help="detect machine + toolchain (Layers 1-2, read-only)")
    p_scan.set_defaults(func=cmd_scan)

    p_deps = sub.add_parser("deps", help="detect the developer toolchain (Layer 2)")
    p_deps.set_defaults(func=cmd_deps)

    p_runtimes = sub.add_parser("runtimes", help="detect AI runtimes & editors (Layer 3)")
    p_runtimes.set_defaults(func=cmd_runtimes)

    p_models = sub.add_parser("models", help="hardware-aware model recommendations (Layer 4)")
    p_models.set_defaults(func=cmd_models)

    p_health = sub.add_parser("health", help="run a health check (Layer 10)")
    p_health.set_defaults(func=cmd_health)

    p_doctor = sub.add_parser("doctor", help="explain issues in plain language (Layer 13)")
    p_doctor.add_argument(
        "--self-test",
        action="store_true",
        help="run install confidence checks instead of issue explanations",
    )
    p_doctor.set_defaults(func=cmd_doctor)

    p_config = sub.add_parser("config", help="Config Center: discover configs, env vars, PATH")
    p_config.add_argument("--show", metavar="KEY", help="print one config file (secrets redacted)")
    p_config.add_argument("--env", action="store_true", help="show AI-relevant env vars only")
    p_config.add_argument("--path", action="store_true", help="show PATH entries + issues only")
    p_config.set_defaults(func=cmd_config)

    p_dash = sub.add_parser("dashboard", help="serve the live dashboard (needs [dashboard] extra)")
    p_dash.add_argument("--host", default="127.0.0.1", help="bind host (default: 127.0.0.1)")
    p_dash.add_argument("--port", type=int, default=8421, help="bind port (default: 8421)")
    p_dash.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    p_dash.set_defaults(func=cmd_dashboard)

    p_plan = sub.add_parser("plan", help="dry-run install plan for a profile (Layer 18)")
    p_plan.add_argument("--profile", help="profile key (see --list)")
    p_plan.add_argument("--capabilities", help="comma-separated add-ons, e.g. containers,gpu")
    p_plan.add_argument("--no-models", action="store_true", help="skip model download steps")
    p_plan.add_argument("--list", action="store_true", help="list available profiles")
    p_plan.set_defaults(func=cmd_plan)

    p_security = sub.add_parser("security", help="trust / integrity posture (Layer 14)")
    p_security.set_defaults(func=cmd_security)

    p_diag = sub.add_parser("diagnostics", help="bundle redacted logs + state (Layer 15)")
    p_diag.set_defaults(func=cmd_diagnostics)

    p_backup = sub.add_parser("backup", help="create/list global config snapshots (Layer 17)")
    p_backup.add_argument("--list", action="store_true", help="list existing snapshots")
    p_backup.set_defaults(func=cmd_backup)

    p_restore = sub.add_parser("restore", help="restore a snapshot (destructive; Layer 17)")
    p_restore.add_argument("id", nargs="?", help="snapshot id (timestamp folder name)")
    p_restore.add_argument(
        "--confirm",
        metavar="TOKEN",
        help="must be RESTORE to proceed",
    )
    p_restore.set_defaults(func=cmd_restore)

    p_download = sub.add_parser("download", help="dry-run direct download plan (Layer 5)")
    p_download.add_argument("url", help="HTTPS URL on an official host")
    p_download.add_argument("--dest", help="optional destination path")
    p_download.add_argument("--sha256", help="expected SHA256 hex digest")
    p_download.set_defaults(func=cmd_download)

    p_update = sub.add_parser("update", help="check for updates (Layer 16, read-only)")
    p_update.add_argument("--check", action="store_true", help="check Loadout + components")
    p_update.set_defaults(func=cmd_update)

    p_bench = sub.add_parser("benchmark", help="run local benchmark (Layer 12)")
    p_bench.add_argument("--latest", action="store_true", help="show last saved result")
    p_bench.add_argument("--full", action="store_true", help="longer CPU/disk sample")
    p_bench.set_defaults(func=cmd_benchmark)

    p_vscode = sub.add_parser("vscode", help="preview VS Code settings merge (Layer 6)")
    p_vscode.add_argument("--preview", action="store_true", help="show merged settings")
    p_vscode.add_argument("--editor", choices=("vscode", "cursor"), default=None)
    p_vscode.set_defaults(func=cmd_vscode)

    p_continue = sub.add_parser("continue", help="preview Continue config (Layer 7)")
    p_continue.add_argument("--preview", action="store_true", help="show generated config")
    p_continue.set_defaults(func=cmd_continue)

    p_agents = sub.add_parser("agents", help="preview agent/MCP scaffold (Layer 8)")
    p_agents.add_argument("--preview", action="store_true", help="show MCP + folders plan")
    p_agents.set_defaults(func=cmd_agents)

    p_new = sub.add_parser("new", help="scaffold a project template (Layer 9)")
    p_new.add_argument("template", nargs="?", help="template key (see --list)")
    p_new.add_argument("name", nargs="?", help="project name")
    p_new.add_argument("--dir", help="target directory (default: ./<name>)")
    p_new.add_argument("--list", action="store_true", help="list templates")
    p_new.add_argument("--preview", action="store_true", help="show file list only")
    p_new.add_argument("--force", action="store_true", help="overwrite existing files")
    p_new.set_defaults(func=cmd_new)

    p_offline = sub.add_parser("offline", help="connectivity + offline cache report (Layer 19)")
    p_offline.set_defaults(func=cmd_offline)

    p_telemetry = sub.add_parser("telemetry", help="telemetry opt-in status (Layer 20)")
    p_telemetry.add_argument("--status", action="store_true", help="show telemetry status")
    p_telemetry.add_argument("--preview", action="store_true", help="preview collected fields")
    p_telemetry.set_defaults(func=cmd_telemetry)

    p_self = sub.add_parser("self-test", help="validate install (imports, dashboard, scan)")
    p_self.add_argument(
        "--bind-http",
        action="store_true",
        help="bind an ephemeral port and GET / + /static/app.js (e2e smoke)",
    )
    p_self.set_defaults(func=cmd_self_test)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
