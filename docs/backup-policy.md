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

**Restore:** manual — copy the `.bak` file back over the original path. There is no
one-click restore UI yet.

### Install / upgrade actions

Install logs record **what ran** (`~/.ai-loadout/logs/install.log`) but do **not** snapshot
system state or uninstall packages automatically. Undoing an install is manual (use the
package manager or vendor uninstaller).

## What is NOT backed up today

- Global "backup everything" or scheduled snapshots (**Layer 17 — planned**).
- Automatic rollback of failed installs.
- Registry or system PATH snapshots (PATH is **read/refreshed** for detection only;
  `src/ai_loadout/util/path_env.py`).

## Recommendations

- Before confirming a large install or config edit on an important machine, keep your own
  backup (system restore point, dotfiles repo, etc.).
- Inspect `~/.ai-loadout/backups/` after editing sensitive files.

See [confirmation-policy.md](./confirmation-policy.md).
