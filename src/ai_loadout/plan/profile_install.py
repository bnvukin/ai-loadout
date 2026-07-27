"""Run an entire profile install plan sequentially with streaming progress."""

from __future__ import annotations

from ..actions.runner import run_action
from ..offline.gate import offline_block
from .planner import build_plan_from_scratch


def profile_plan(store, profile_key: str) -> dict:
    plan = build_plan_from_scratch(store, profile_key)
    return plan.to_dict()


def run_profile_install(
    store,
    profile_key: str,
    *,
    dry_run: bool = False,
) -> dict:
    """Execute install/upgrade/pull steps from a profile plan (skips manual/skip)."""

    plan = build_plan_from_scratch(store, profile_key)
    steps_out: list[dict] = []
    blocked_offline = False

    for step in plan.steps:
        row = step.to_dict()
        if step.action in ("skip", "manual"):
            row["result"] = {"ok": True, "skipped": True, "reason": step.reason}
            steps_out.append(row)
            continue

        if step.action == "pull":
            block = offline_block("pull")
            if block:
                blocked_offline = True
                row["result"] = block
                steps_out.append(row)
                continue
            if dry_run:
                row["result"] = {"ok": True, "dry_run": True, "command": step.command}
                steps_out.append(row)
                continue
            result = run_action(store, step.key, "model", "pull")
            row["result"] = result
            steps_out.append(row)
            if not result.get("success"):
                break
            continue

        if step.action in ("install", "upgrade"):
            block = offline_block("install")
            if block:
                blocked_offline = True
                row["result"] = block
                steps_out.append(row)
                continue
            if dry_run:
                row["result"] = {"ok": True, "dry_run": True, "command": step.command}
                steps_out.append(row)
                continue
            result = run_action(store, step.key, step.kind, step.action)
            row["result"] = result
            steps_out.append(row)
            if not result.get("success"):
                break

    return {
        "ok": not blocked_offline
        and all(
            s.get("result", {}).get("success")
            or s.get("result", {}).get("skipped")
            or s.get("result", {}).get("dry_run")
            for s in steps_out
        ),
        "profile": profile_key,
        "dry_run": dry_run,
        "steps": steps_out,
        "summary": plan.summary(),
        "blocked_offline": blocked_offline,
    }
