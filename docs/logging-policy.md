# Logging policy

All logging today is **local to your machine**.

## Install and action logs (implemented)

| Location | Contents |
|----------|----------|
| `~/.ai-loadout/logs/install.log` | Timestamped lines for each confirmed install/upgrade/repair/pull command and its stdout (`src/ai_loadout/actions/runner.py`) |
| Dashboard **Activity** view | Live event stream from the orchestrator and action engine |
| `/api/events` | JSON API for the same bounded event history |

Action output is also streamed over the dashboard WebSocket (with HTTP polling fallback).

## Structured snapshots & diagnostics (implemented — Layer 15)

| Location | Contents |
|----------|----------|
| `~/.ai-loadout/logs/system.json` | Machine + component snapshot (env values redacted) |
| `~/.ai-loadout/diagnostics/diagnostics-*.zip` | Bundle of logs, `state.json`, `system.json`, `versions.json` (redacted) |
| `loadout diagnostics` / dashboard **Download diagnostics** | Creates the zip on demand |

## Digital twin state

`~/.ai-loadout/state.json` persists the detected component graph (versions, health, paths).
It may reference install paths and versions but should not contain raw secrets if you have
not stored them in tracked fields.

## Secret handling in logs and UI

- Config **display** and env inspection use redaction (`src/ai_loadout/config/redact.py`,
  `src/ai_loadout/config/env.py`).
- **Diagnostics bundles** redact secrets before writing the zip.
- **Install logs** capture raw command output from winget, apt, Ollama, etc. — those tools
  may print paths or warnings; they should not include your API keys unless a tool prints
  them. Review `install.log` before sharing.
- The config **editor** shows unredacted content for files marked `secret=True` so edits
  are accurate.

## Planned (not implemented)

- **Layer 12 — Benchmark:** `benchmark.log` for inference/disk timings.
- Central log shipping or remote aggregation — **not planned** without explicit opt-in.

See [PRIVACY.md](../PRIVACY.md).
