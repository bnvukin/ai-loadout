#!/usr/bin/env bash
# Loadout bootstrapper for macOS / Linux. The "one command" that gets you from a bare
# machine to the Loadout dashboard: ensure Python exists, install Loadout, then scan.
#
# Safe by design:
#   * Installs only from official sources (system pkg manager for Python; pip/GitHub).
#   * Prints every action before running it.
#   * --dry-run shows what it would do and changes nothing.
#   * Never touches employer accounts, tools, or identity -- personal use only.
#
# Usage:
#   ./bootstrap.sh --dry-run          # preview
#   ./bootstrap.sh --dashboard        # install and open the dashboard
set -euo pipefail

DRY_RUN=0
DASHBOARD=0
SOURCE="git+https://github.com/bnvukin/ai-loadout"

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --dashboard) DASHBOARD=1 ;;
    --source=*) SOURCE="${arg#*=}" ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "[loadout] unknown option: $arg" >&2; exit 2 ;;
  esac
done

info() { printf '\033[36m[loadout]\033[0m %s\n' "$1"; }
warn() { printf '\033[33m[loadout]\033[0m %s\n' "$1"; }
run() {
  info "$1"
  printf '         $ %s\n' "$2"
  [ "$DRY_RUN" -eq 1 ] || eval "$2"
}

find_python() {
  for exe in python3 python; do
    if command -v "$exe" >/dev/null 2>&1; then echo "$exe"; return 0; fi
  done
  return 1
}

info "Loadout bootstrapper ($(uname -s))"
[ "$DRY_RUN" -eq 1 ] && warn "DRY RUN - nothing will be installed."

# 1) Ensure Python 3.9+
if ! PYTHON="$(find_python)"; then
  if command -v brew >/dev/null 2>&1; then
    run "Python not found - installing via Homebrew" "brew install python"
  elif command -v apt-get >/dev/null 2>&1; then
    run "Python not found - installing via apt" "sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv"
  elif command -v dnf >/dev/null 2>&1; then
    run "Python not found - installing via dnf" "sudo dnf install -y python3 python3-pip"
  else
    warn "Python not found and no known package manager available."
    warn "Install Python 3.9+ from https://www.python.org/downloads/ then re-run."
    exit 1
  fi
  PYTHON="$(find_python)" || { warn "Python still not on PATH. Open a new shell and re-run."; exit 1; }
fi
info "Using Python: $PYTHON"

# 2) Install Loadout (with the dashboard extra) into the user site.
run "Installing Loadout" "\"$PYTHON\" -m pip install --user --upgrade \"ai-loadout[dashboard] @ $SOURCE\""

# 3) First scan (and optionally the dashboard).
run "Scanning this machine" "\"$PYTHON\" -m ai_loadout scan"
if [ "$DASHBOARD" -eq 1 ]; then
  run "Starting the dashboard at http://127.0.0.1:8421" "\"$PYTHON\" -m ai_loadout dashboard"
else
  info "Done. Next:  $PYTHON -m ai_loadout dashboard    (live UI at http://127.0.0.1:8421)"
fi
