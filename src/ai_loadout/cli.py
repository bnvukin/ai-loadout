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


def cmd_scan(args: argparse.Namespace) -> int:
    """Layer 1 - read-only machine scan; writes the result into the digital twin."""

    from .core.state import load_state
    from .detect.system import scan, summarize

    store = load_state()
    hw = scan(store)
    if args.json:
        _print_json(store.snapshot())
        return 0
    print(BANNER)
    for line in summarize(hw):
        print(line)
    if hw.warnings:
        print("\nNotes:")
        for warning in hw.warnings:
            print(f"  ! {warning}")
    print("\nSaved to the digital twin.  Next:  loadout plan   ·   loadout dashboard")
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

    p_scan = sub.add_parser("scan", help="detect this machine (Layer 1, read-only)")
    p_scan.set_defaults(func=cmd_scan)

    # Registered fully in later batches; discoverable now so `--help` lists them.
    for name, hint in (
        ("plan", "Installation planning lands with profiles/capabilities."),
        ("health", "Health checks land with the health module."),
        ("models", "Model recommendations land with the models module."),
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
