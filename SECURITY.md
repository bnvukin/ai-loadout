# Security Policy

Loadout modifies developer machines — installing software, editing configuration files,
and (with explicit confirmation) running package managers that may change `PATH` and
installed applications. We take that responsibility seriously.

## Supported versions

| Version | Supported |
|---------|-----------|
| `main` branch (0.1.x alpha) | ✅ active development |
| Older tags / forks | ❓ best-effort only |

Loadout is in **alpha**. Pin to a commit or tag if you need reproducibility.

## Design principles (current vs planned)

- **Official sources.** Install commands target official package managers and vendor IDs
  (winget, Chocolatey, Homebrew, apt, npm, pip, Ollama, …). Unofficial mirrors are not
  used in command templates.
- **Verify before trust (planned).** Layer 14 (checksum/signature verification) is **not
  implemented yet**. Do not assume installers are checksum-verified today.
- **Read-only by default.** CLI commands do not mutate the system. Dashboard mutations
  require confirmation; config saves use trust levels (see
  [docs/confirmation-policy.md](./docs/confirmation-policy.md)).
- **Reversible config edits.** Existing config files are backed up to `~/.ai-loadout/backups/`
  before overwrite (`src/ai_loadout/config/edit.py`).
- **No exfiltration.** Loadout does not transmit your inventory, configs, or secrets to
  maintainers. See [PRIVACY.md](./PRIVACY.md). Telemetry is **not present** (Layer 20
  planned as opt-in only).

## Reporting a vulnerability

Please **do not** open a public issue for a security vulnerability.

1. Use GitHub **Private vulnerability reporting**: Repository → **Security** → **Report a
   vulnerability**.
2. Or open a minimal public issue asking a maintainer to contact you privately.

Include:

- Description and impact
- Steps to reproduce
- Affected version / commit
- Suggested fix (if any)

**Never include secrets** (API keys, tokens, passwords, private URLs) in public issues,
PRs, or discussion threads.

We will acknowledge your report as quickly as we can and keep you updated on remediation.

## Safe disclosure

We appreciate responsible disclosure. We ask that you give us reasonable time to address
issues before public disclosure.

## Related documents

- [DISCLAIMER.md](./DISCLAIMER.md)
- [PRIVACY.md](./PRIVACY.md)
- [docs/confirmation-policy.md](./docs/confirmation-policy.md)
- [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)
