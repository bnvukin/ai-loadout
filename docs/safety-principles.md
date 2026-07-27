# Safety principles

These principles guide Loadout's design. Implementation status varies — see
[CHECKLIST.md](../CHECKLIST.md) for what is done vs planned.

## Safety principles

1. **Local-first** — your machine, your data; no Loadout cloud dependency.
2. **User in control** — mutating actions require explicit confirmation; CLI stays read-only.
3. **Confirm before risk** — command preview for installs; `CONFIRM` / `EDIT` tokens for
   sensitive config saves.
4. **Backups where practical** — timestamped per-file backup before config overwrites
   (`~/.ai-loadout/backups/`).
5. **Transparent logs** — install commands and output recorded in `install.log` and the
   dashboard event stream.
6. **No silent destructive actions** — no background installs without your confirm in the
   dashboard; orchestrator scans are detection-only.
7. **Secure defaults** — secrets redacted in read views; official package managers preferred
   in command templates (`src/ai_loadout/actions/commands.py`).
8. **Minimal core dependencies** — small auditable runtime (`psutil` only in core; dashboard
   extras separate).

## Project principles

1. **Digital twin** — one state model for CLI, dashboard, and future automation.
2. **Honest status** — README and docs match what is implemented; planned layers labeled.
3. **Cross-platform** — Windows-first, macOS/Linux supported in detection and planning.
4. **Testable** — parsers and planners tested with fixtures, not live toolchains.
5. **Reversible config edits** — backup-first writes; global snapshots + typed restore
   (Layer 17).
6. **Official sources** — installers built from winget/choco/brew/apt/npm/pip/Ollama IDs;
   trust posture report + URL allowlist + SHA256 for direct downloads (Layer 14).
7. **Integrity** — no hidden telemetry; opt-in only if ever added (Layer 20).
8. **Extensible layers** — each capability (deps, runtimes, health, config) plugs into the
   same component lifecycle.

## Related documents

- [confirmation-policy.md](./confirmation-policy.md)
- [backup-policy.md](./backup-policy.md)
- [logging-policy.md](./logging-policy.md)
- [PRIVACY.md](../PRIVACY.md)
- [DISCLAIMER.md](../DISCLAIMER.md)
