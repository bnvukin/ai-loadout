# Security Policy

Loadout modifies developer machines — installing software, editing configuration files,
and (with explicit confirmation) touching `PATH`, environment variables, and the Windows
registry. We take that responsibility seriously.

## Design principles

- **Official sources only.** Installers and models are fetched from official vendor URLs
  and package managers (winget, Chocolatey, Homebrew, apt, Ollama, ...). No unofficial
  mirrors.
- **Verify before trust.** Where a vendor publishes a checksum/signature, Loadout verifies
  it before executing an installer.
- **Read-only by default.** Configuration is shown read-only. Editing requires an explicit
  confirmation; expert-level targets (registry, hosts file, certificates) require typing
  `EDIT`.
- **Reversible.** Config edits are backed up first; changes can be restored.
- **No exfiltration.** Loadout does not transmit your data. Any future telemetry is strictly
  opt-in and anonymous.

## Reporting a vulnerability

Please **do not** open a public issue for a security vulnerability. Instead, use GitHub's
private vulnerability reporting on this repository (Security → "Report a vulnerability"),
or open a minimal issue asking a maintainer to contact you privately.

We will acknowledge your report as quickly as we can and keep you updated on the fix.
