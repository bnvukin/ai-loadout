# End-to-end validation runbook

Loadout has **automated** fresh-install checks in CI (build wheel → clean venv →
`loadout self-test --bind-http` on Windows, macOS, and Linux). This runbook is for
**manual** validation on a real disposable VM — especially the **mutating** paths CI
does not fully exercise (winget/brew/apt installs, multi-GB model pulls, UAC prompts).

## What CI proves vs what this runbook adds

| Area | CI (`.github/workflows/ci.yml`) | Manual VM runbook |
|------|--------------------------------|-------------------|
| Wheel builds and passes `twine check` | ✅ ubuntu | Optional local verify |
| Clean venv `pip install` + entry points | ✅ 3 OS matrix | ✅ |
| `loadout self-test` (imports, static, scan, probes) | ✅ 3 OS | ✅ |
| Ephemeral HTTP bind `GET /` + `/static/app.js` | ✅ `--bind-http` | ✅ browser optional |
| Real winget/brew/apt install + PATH refresh | ❌ | ✅ recommended |
| Multi-GB `ollama pull` | ❌ | ✅ optional |
| Dashboard confirm + backup + rescan green | ❌ | ✅ recommended |

---

## Prerequisites

- A **fresh** VM (Windows 11, macOS, or Ubuntu) with network access
- Python 3.9+ **or** use the bootstrap script (installs Python for you)
- No prior Loadout install

---

## Path A — Bootstrap (recommended on bare machines)

### Windows

```powershell
git clone https://github.com/bnvukin/ai-loadout.git
cd ai-loadout
./bootstrap.ps1 -Dashboard
```

Expected: winget installs Python (if missing), pip installs Loadout with `[dashboard]`,
first scan runs, browser opens `http://localhost:8421`.

### macOS / Linux

```bash
git clone https://github.com/bnvukin/ai-loadout.git
cd ai-loadout
./bootstrap.sh --dashboard
```

---

## Path B — PyPI install (after first release)

```bash
pip install ai-loadout[dashboard]
loadout --version          # Loadout 0.1.0
loadout self-test
loadout self-test --bind-http   # optional: real port bind smoke
loadout dashboard
```

---

## Path C — Local wheel (pre-release verify)

```bash
python -m pip install build
python -m build
pip install dist/ai_loadout-*.whl[dashboard]
loadout self-test --bind-http
```

---

## Self-test checklist

Run:

```bash
loadout self-test
```

Expected output (all **PASS**):

```
  [PASS] imports_and_version       0.1.0
  [PASS] cli_subcommands           N subcommands registered
  [PASS] dashboard_static_assets   .../ai_loadout/dashboard/static
  [PASS] dashboard_app_import      FastAPI app constructed
  [PASS] dashboard_http_testclient HTTP routes OK (version 0.1.0)
  [PASS] loadout_home_writable     writable under ...
  [PASS] default_home_writable     ~/.ai-loadout
  [PASS] machine_scan              Windows/macOS/Linux, X GB RAM
  [PASS] security_posture          N components scored
  [PASS] connections_probe         0/N connected (or higher if keys set)
  [PASS] offline_probe             online=True|False

Self-test PASSED
```

Exit code **0**. Any **FAIL** → exit **1** (do not ship).

JSON gate:

```bash
loadout self-test --json | jq .ok
# true
```

---

## Dashboard smoke (manual)

1. `loadout dashboard` → opens `http://localhost:8421`
2. Confirm Overview loads (health ring, machine summary)
3. Click **Rescan** → task chips progress → complete
4. Open **Config Center** → files list loads (redacted)
5. Open **Connections** → providers show present/absent (no secret values)
6. Open **Settings & Privacy** → telemetry **off** by default

---

## Mutating path (optional but recommended)

Exercises install engine, backup, and rescan — **only on a disposable VM**.

1. Dashboard → **Components** → pick one small missing tool (e.g. `uv` or `git` if absent)
2. Click **Install** → confirm modal shows exact command
3. Confirm → watch streaming action log
4. On success, component badge turns **green** after rescan
5. **Config Center** → edit a SAFE file → save → verify backup under `~/.ai-loadout/backups/`

Optional model pull (large download):

1. Dashboard → **Models** → install a small model (e.g. `llama3.2:1b` if available)
2. Confirm → wait for pull to finish
3. **Refresh** → model shows installed

---

## Sign-off checklist

- [ ] `loadout self-test` all PASS on this OS
- [ ] `loadout self-test --bind-http` PASS (or CI green for this OS)
- [ ] Dashboard loads SPA (HTML + JS + CSS)
- [ ] Rescan completes without crash
- [ ] (Optional) One real install + backup verified
- [ ] (Optional) One model pull completed

Record OS version, Loadout version, and date in your notes when signing off.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Dashboard static bundle missing` | Installed without wheel / broken install | `pip install ai-loadout[dashboard]` |
| `uvicorn not installed` | Missing `[dashboard]` extra | Same |
| Self-test `dashboard_http_bind` fails | Port/firewall | Retry; check antivirus on Windows |
| Install succeeds but stays grey | Stale PATH | Dashboard → rescan component; restart dashboard |
| winget install fails | Needs elevation | Run elevated shell or install manually |

See [RELEASING.md](../RELEASING.md) for maintainer publish steps and [docs/e2e-validation.md](./e2e-validation.md) for VM validation.
