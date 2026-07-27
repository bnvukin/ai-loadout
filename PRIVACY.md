# Privacy Policy

Loadout is **local-first**. It runs on your machine and does not operate a central cloud
service that collects your personal data.

## What Loadout does NOT collect today

- No account registration or login through Loadout.
- No analytics, crash reporting, or usage telemetry (**telemetry is not implemented**;
  Layer 20 is planned as strictly opt-in if ever added).
- No transmission of your files, environment variables, API keys, or machine inventory to
  Loadout maintainers.

Network access occurs only when **you** trigger actions that need it (e.g. `winget install`,
`ollama pull`, package manager metadata). Those requests go to the relevant vendors, not to
a Loadout server.

## What is stored locally

Under `~/.ai-loadout/` (override with `LOADOUT_HOME`):

| Path | Purpose |
|------|---------|
| `state.json` | Digital twin — detected components, health, versions |
| `logs/install.log` | Timestamped log of confirmed install/upgrade/repair commands |
| `logs/benchmark.log` | Reserved for benchmarks (**Layer 12 — planned**) |
| `backups/` | Timestamped copies of config files before dashboard edits |
| `runs/` | Reserved for install/benchmark session replay (**partial / planned**) |

The dashboard also keeps a bounded **in-memory event history** (WebSocket + `/api/events`)
for the current session; it is not sent off-machine.

## Secrets and redaction

- Config Center **read** views redact secret-looking keys and known token patterns
  (`src/ai_loadout/config/redact.py`).
- Environment variables whose names look like credentials are **masked** in the dashboard
  and API (`src/ai_loadout/config/env.py`).
- **Editing** a secret-bearing config file in the dashboard shows full content so you can
  save accurately — treat the editor as sensitive.

API keys and tokens remain **under your control**. Loadout does not upload them.

## Third-party services

When you install or use Git, Ollama, Docker, cloud LLM APIs, Hugging Face, etc., those
services have their own privacy policies. Loadout is not responsible for their handling of
your data.

## Telemetry (planned)

If telemetry is ever added (Layer 20), it will be:

- **Opt-in only** (off by default).
- **Anonymous aggregate** statistics only (no file paths, no env vars, no keys).
- Documented in this file and in [CHANGELOG.md](./CHANGELOG.md) before release.

Until then: **no telemetry**.

## Contact

Privacy questions: open a GitHub issue on [bnvukin/ai-loadout](https://github.com/bnvukin/ai-loadout)
or see [SECURITY.md](./SECURITY.md) for sensitive reports.
