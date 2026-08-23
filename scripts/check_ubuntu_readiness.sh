#!/usr/bin/env bash
# Read-only Ubuntu readiness verification for Arctura Finney operations.
# This script never creates wallets, signs transactions, registers a subnet,
# or writes any cloud configuration.

set -u -o pipefail

REPO_DIR="${1:-$HOME/arctura-base-subnet}"
FAILURES=0

pass() { printf '[PASS] %s\n' "$1"; }
warn() { printf '[WARN] %s\n' "$1"; }
fail() { printf '[FAIL] %s\n' "$1"; FAILURES=$((FAILURES + 1)); }

require_command() {
  local command="$1"
  if command -v "$command" >/dev/null 2>&1; then
    pass "$command available: $(command -v "$command")"
  else
    fail "$command is missing"
  fi
}

printf '%s\n' 'ARCTURA UBUNTU READINESS CHECK'
printf 'Repository: %s\n' "$REPO_DIR"
printf 'Timestamp: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ -d "$REPO_DIR" ]]; then
  pass 'repository directory present'
else
  fail 'repository directory missing'
fi

for command in python3 git docker btcli; do
  require_command "$command"
done

if command -v gh >/dev/null 2>&1; then
  if gh auth status >/dev/null 2>&1; then
    pass 'GitHub CLI authentication available'
  else
    warn 'GitHub CLI is installed but not authenticated; automated vulnerability issues are disabled'
  fi
else
  warn 'GitHub CLI missing; automated vulnerability issues are disabled'
fi

if command -v docker >/dev/null 2>&1; then
  if docker compose version >/dev/null 2>&1; then
    pass 'Docker Compose v2 available'
  else
    fail 'Docker Compose v2 unavailable'
  fi
fi

if [[ -f "$REPO_DIR/.env" ]]; then
  permissions="$(stat -c '%a' "$REPO_DIR/.env" 2>/dev/null || printf 'unknown')"
  if [[ "$permissions" == "600" || "$permissions" == "640" ]]; then
    pass ".env present with restrictive permissions ($permissions)"
  else
    warn ".env present with permissions $permissions; review before launch"
  fi
else
  warn '.env is absent; deployment configuration is not yet staged'
fi

if [[ -d "$HOME/.bittensor/wallets" ]]; then
  pass 'Bittensor wallet directory present (wallet contents not inspected)'
else
  warn 'Bittensor wallet directory absent or unavailable'
fi

for log_name in burn_cost.log validator.log; do
  if [[ -f "$REPO_DIR/$log_name" ]]; then
    age_minutes=$(( ($(date +%s) - $(stat -c %Y "$REPO_DIR/$log_name")) / 60 ))
    if (( age_minutes <= 1440 )); then
      pass "$log_name present and refreshed within 24h"
    else
      warn "$log_name is older than 24h"
    fi
  else
    warn "$log_name not found; configure the operational log path after cloud resume"
  fi
done

if [[ "$FAILURES" -gt 0 ]]; then
  printf 'Readiness result: BLOCKED (%s critical prerequisite(s) missing).\n' "$FAILURES"
  exit 1
fi

printf '%s\n' 'Readiness result: baseline checks complete. No transaction or signing action was performed.'
