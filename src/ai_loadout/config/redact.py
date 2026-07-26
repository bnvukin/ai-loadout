"""Best-effort secret redaction for config files and environment variables.

Security-first: the Config Center reads real files and env vars, so anything that
smells like a credential is masked *before* it can reach a log, the dashboard, or the
terminal. This is deliberately conservative -- it over-masks rather than risk leaking.
"""

from __future__ import annotations

import re

# Substrings in a key/variable name that mark its value as sensitive.
_SECRET_HINT = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|passwd|pwd|auth(?:orization)?|bearer|"
    r"client[_-]?secret|access[_-]?key|private[_-]?key|credential|session|cookie)"
)

# ``key: value`` / ``key = value`` pairs whose key looks sensitive (JSON, INI, YAML, env).
_KV = re.compile(
    r"""(?ix)
    (                                   # group 1: key + separator (kept)
      ["']?[\w.\-]*
      (?:api[_-]?key|secret|token|password|passwd|pwd|auth|bearer|credential|
         access[_-]?key|private[_-]?key|cookie)
      [\w.\-]* ["']?
      \s* [:=] \s*
    )
    ( "[^"\n]*" | '[^'\n]*' | [^\s,}\n]+ )   # group 2: value (masked)
    """
)

# Standalone high-entropy secrets that show up without an obvious key.
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]{12,}")
_KNOWN_TOKENS = re.compile(
    r"\b(?:sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9\-]{10,}|"
    r"hf_[A-Za-z0-9]{16,}|AIza[A-Za-z0-9_\-]{20,})\b"
)

_MASK = "***redacted***"


def looks_secret(name: str) -> bool:
    """True if a variable/key *name* implies its value is a credential."""

    return bool(_SECRET_HINT.search(name or ""))


def mask(value: str) -> str:
    """Mask a value while keeping just enough to recognise it (never the middle)."""

    v = (value or "").strip().strip("\"'")
    if not v:
        return ""
    if len(v) <= 6:
        return "***"
    return f"{v[:2]}***{v[-2:]}  ({len(v)} chars)"


def _mask_kv(match: re.Match) -> str:
    return match.group(1) + _MASK


def redact_text(text: str) -> tuple[str, bool]:
    """Redact secret-looking values in arbitrary config text.

    Returns ``(redacted_text, changed)`` so callers can flag when masking happened.
    """

    if not text:
        return text, False
    redacted = _KV.sub(_mask_kv, text)
    redacted = _BEARER.sub("Bearer " + _MASK, redacted)
    redacted = _KNOWN_TOKENS.sub(_MASK, redacted)
    return redacted, redacted != text
