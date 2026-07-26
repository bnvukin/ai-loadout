<#
.SYNOPSIS
  Loadout bootstrapper for Windows. The "one command" that gets you from a bare machine
  to the Loadout dashboard: ensure Python exists, install Loadout, then scan.

.DESCRIPTION
  Safe by design:
    * Installs only from official sources (winget for Python; pip/GitHub for Loadout).
    * Prints every action before running it.
    * `-DryRun` shows what it would do and changes nothing.
    * Never touches employer accounts, tools, or identity -- personal use only.

.EXAMPLE
  # Preview
  ./bootstrap.ps1 -DryRun

.EXAMPLE
  # Install and open the dashboard
  ./bootstrap.ps1 -Dashboard
#>
[CmdletBinding()]
param(
  [switch]$DryRun,
  [switch]$Dashboard,
  [string]$Source = "git+https://github.com/bnvukin/ai-loadout"
)

$ErrorActionPreference = "Stop"

function Info($msg) { Write-Host "[loadout] $msg" -ForegroundColor Cyan }
function Warn($msg) { Write-Host "[loadout] $msg" -ForegroundColor Yellow }
function Run($desc, $cmd) {
  Info $desc
  Write-Host "         > $cmd" -ForegroundColor DarkGray
  if (-not $DryRun) { Invoke-Expression $cmd }
}

function Get-Python {
  foreach ($exe in @("python", "python3", "py")) {
    $found = Get-Command $exe -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
  }
  return $null
}

Info "Loadout bootstrapper (Windows)"
if ($DryRun) { Warn "DRY RUN - nothing will be installed." }

# 1) Ensure Python 3.9+
$python = Get-Python
if (-not $python) {
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    Run "Python not found - installing via winget" `
        "winget install --id Python.Python.3.12 -e --source winget"
    $python = Get-Python
    if (-not $python -and -not $DryRun) {
      Warn "Python installed but not on PATH yet. Open a NEW terminal and re-run."
      exit 1
    }
  }
  else {
    Warn "Python not found and winget is unavailable."
    Warn "Install Python 3.9+ from https://www.python.org/downloads/ then re-run."
    exit 1
  }
}
Info "Using Python: $python"

# 2) Install Loadout (with the dashboard extra) into the user site.
$pkg = "ai-loadout[dashboard] @ $Source"
Run "Installing Loadout" "& `"$python`" -m pip install --user --upgrade `"$pkg`""

# 3) First scan (and optionally the dashboard).
Run "Scanning this machine" "& `"$python`" -m ai_loadout scan"
if ($Dashboard) {
  Run "Starting the dashboard at http://127.0.0.1:8421" "& `"$python`" -m ai_loadout dashboard"
}
else {
  Info "Done. Next:  python -m ai_loadout dashboard    (live UI at http://127.0.0.1:8421)"
}
