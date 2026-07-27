# Backup policy

## What is backed up today

### Config file saves (implemented)

When you save a config file from the dashboard (or via `apply_edit()` in
`src/ai_loadout/config/edit.py`):

1. If the file already exists, Loadout copies it to  
   `~/.ai-loadout/backups/<original-name>.<YYYYMMDD-HHMMSS>.bak`
2. The new content is written atomically (temp file + `os.replace`).

This applies to all registered Config Center targets (Continue, VS Code/Cursor settings,
Git, Docker, npm, pip, shell profile, Hugging Face token, …).

**Restore:** manual — copy the `.bak` file back over the original path, or use a global
snapshot restore from the dashboard / `loadout restore <id> --confirm RESTORE`.

### Global config snapshots (implemented — Layer 17)

`loadout backup` (or the dashboard **Create backup** button) copies every discovered Config
Center file into `~/.ai-loadout/backups/<YYYYMMDD-HHMMSS>/` plus a `manifest.json` recording
PATH entries and env key names (values redacted). **Restore** overwrites originals and
requires typing `RESTORE` in the dashboard (or `--confirm RESTORE` on the CLI).

### Install / upgrade actions

Install logs record **what ran** (`~/.ai-loadout/logs/install.log`) but do **not** snapshot
system state or uninstall packages automatically. Undoing an install is manual (use the
package manager or vendor uninstaller).

## What is NOT backed up today

- Scheduled / automatic snapshots.
- Automatic rollback of failed installs.
- System environment variable restore (manifest records keys only; OS env is not overwritten).

## Recommendations

- Before confirming a large install or config edit on an important machine, keep your own
  backup (system restore point, dotfiles repo, etc.).
- Inspect `~/.ai-loadout/backups/` after editing sensitive files.

See [confirmation-policy.md](./confirmation-policy.md).
