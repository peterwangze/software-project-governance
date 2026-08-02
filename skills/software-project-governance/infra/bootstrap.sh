#!/bin/bash
# bootstrap.sh — vendor entry bootstrap (FIX-238.1/238.3, ADR-017 §2)
#
# Locates resolve_entry.py next to this script, runs it with a bounded
# timeout and prints the JSON envelope on stdout. Hosts without
# AGENTS.md/CLAUDE.md can still call this script directly (the fallback
# invocation path is documented in commands/governance.md).
#
# Exit codes (shared contract with bootstrap.cmd and
# `verify_workflow.py resolve-entry`):
#   0  success — envelope JSON on stdout
#   1  resolve_entry exited non-zero (other failure)
#   2  python not found
#   3  resolve_entry.py not found
#   4  timeout (SPG_RESOLVE_TIMEOUT, default 15s)
#   5  store stub (resolve_entry.py exists but is not the canonical resolver)
#
# Timeout: SPG_RESOLVE_TIMEOUT (positive integer seconds; invalid -> 15s,
# FIX-234 precedent). Python override: SPG_BOOTSTRAP_PYTHON.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESOLVE_ENTRY="$SCRIPT_DIR/resolve_entry.py"
CANONICAL_MARKER="Deterministic /governance entry resolver (FX-130)"
SPG_BOOTSTRAP_PYTHON="${SPG_BOOTSTRAP_PYTHON:-python}"

# --- timeout resolution (invalid -> default, never crashes) ---
raw_timeout="${SPG_RESOLVE_TIMEOUT:-}"
timeout_seconds=15
if [ -n "$raw_timeout" ]; then
    case "$raw_timeout" in
        ''|*[!0-9]*)
            ;;
        *)
            if [ "$raw_timeout" -gt 0 ] 2>/dev/null; then
                timeout_seconds="$raw_timeout"
            fi
            ;;
    esac
fi

# --- classified fail-closed diagnostics ---
if ! command -v "$SPG_BOOTSTRAP_PYTHON" >/dev/null 2>&1; then
    echo "spg-bootstrap-error: python-missing — '$SPG_BOOTSTRAP_PYTHON' not found on PATH" >&2
    exit 2
fi
if [ ! -f "$RESOLVE_ENTRY" ]; then
    echo "spg-bootstrap-error: file-not-found — resolve_entry.py missing at $RESOLVE_ENTRY" >&2
    exit 3
fi
if ! grep -qF "$CANONICAL_MARKER" "$RESOLVE_ENTRY" 2>/dev/null; then
    echo "spg-bootstrap-error: store-stub — resolve_entry.py is not the canonical resolver (missing FX-130 marker); reinstall the plugin" >&2
    exit 5
fi

# --- bounded invocation ---
if command -v timeout >/dev/null 2>&1; then
    timeout "${timeout_seconds}s" "$SPG_BOOTSTRAP_PYTHON" "$RESOLVE_ENTRY" --json
    rc=$?
    if [ "$rc" -eq 124 ]; then
        echo "spg-bootstrap-error: timeout — resolve_entry did not finish within ${timeout_seconds}s (SPG_RESOLVE_TIMEOUT); raise the value or inspect the host" >&2
        exit 4
    fi
    exit "$rc"
fi

# POSIX fallback without coreutils `timeout`: stdlib subprocess timeout
# wrapper (same exit-code contract as the timeout(1) branch).
"$SPG_BOOTSTRAP_PYTHON" - "$timeout_seconds" "$RESOLVE_ENTRY" --json <<'PY'
import subprocess, sys
seconds = float(sys.argv[1])
command = sys.argv[2:]
try:
    proc = subprocess.run(command, timeout=seconds)
except subprocess.TimeoutExpired:
    sys.stderr.write(
        "spg-bootstrap-error: timeout — resolve_entry did not finish within %ss"
        " (SPG_RESOLVE_TIMEOUT); raise the value or inspect the host\n"
        % int(seconds)
    )
    sys.exit(4)
sys.exit(proc.returncode)
PY
