# Confirmation & trust policy

Loadout separates **read-only inspection** from **mutating actions**. Nothing destructive
runs silently.

## CLI vs dashboard

| Surface | Mutations |
|---------|-----------|
| CLI (`loadout scan`, `plan`, `config --show`, …) | **Read-only** / dry-run |
| Dashboard (`loadout dashboard`) | Mutations only after **explicit confirm** in the UI |

Install/upgrade/repair/pull endpoints return a **dry-run command** unless the request body
includes `"confirm": true`.

## Component actions (install / upgrade / repair / pull)

- The dashboard shows the **exact command** (e.g. `winget install …`, `ollama pull …`)
  before you click Install/Update.
- Output streams to the action log and to `~/.ai-loadout/logs/install.log`.
- Windows installs may require **UAC / administrator** approval outside Loadout.
- winget "already installed" / upgrade-not-found cases are handled per
  `src/ai_loadout/actions/winget.py` (fallback or success when already satisfied).

These actions are **not** gated by SAFE/ADVANCED/EXPERT tokens — they use the **confirm
modal** only.

## Config file edits (trust levels)

Config targets in `src/ai_loadout/config/registry.py` carry a **trust level**. Tokens are
defined in `src/ai_loadout/config/edit.py` (`CONFIRM_TOKENS`):

| Level | Token | Dashboard behaviour |
|-------|-------|---------------------|
| 🟢 **SAFE** | *(none)* | Save immediately (Continue, VS Code/Cursor settings, pip config, …) |
| 🟡 **ADVANCED** | Type `CONFIRM` | Git config, Docker config, npmrc, shell profile (PATH), … |
| 🔴 **EXPERT** | Type `EDIT` | Hugging Face token file (and any future expert targets) |

Every save **backs up** the existing file to `~/.ai-loadout/backups/<filename>.<timestamp>.bak`
before writing (`backup_file()` in `edit.py`).

## Planned: registry / hosts / certificates

The lifecycle enum describes **EXPERT** as suitable for registry, hosts file, and
certificates. Loadout **does not edit the Windows registry or hosts file today**. If those
targets are added, they will require the `EDIT` token (or stronger) and be documented here
before release.

## Related layers (planned)

- **Layer 14 — Security:** checksum/signature verification before executing installers
  (**not implemented**).
- **Layer 17 — Backup / restore:** global backup/restore of all configs (**not implemented**;
  only per-file backup on save exists today).

See [backup-policy.md](./backup-policy.md) and [CHECKLIST.md](../CHECKLIST.md).
