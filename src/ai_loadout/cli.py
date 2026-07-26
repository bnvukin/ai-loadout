"""Command-line entry point for Loadout.

Subcommands are added as each layer lands. Today: ``version`` and ``info`` (read the
persisted digital twin). ``scan``, ``plan``, ``health``, ``models`` and ``dashboard``
are wired up in their respective modules.
"""

from __future__ import annotations

import argparse
import json
import sys

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


# Handlers registered by later layers can override these friendly stubs.
def _stub(name: str, hint: str):
    def handler(args: argparse.Namespace) -> int:
        print(f"`loadout {name}` is not available in this build yet.\n{hint}")
        return 2

    return handler


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

    # Registered fully in later batches; discoverable now so `--help` lists them.
    for name, hint in (
        ("plan", "Installation planning lands with profiles/capabilities."),
        ("health", "Health checks land with the health module."),
        ("dashboard", "The live dashboard lands with the dashboard module."),
    ):
        sp = sub.add_parser(name, help=f"[coming soon] {name}")
        sp.set_defaults(func=_stub(name, hint))

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
