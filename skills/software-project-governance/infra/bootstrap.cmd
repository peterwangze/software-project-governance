@echo off
rem bootstrap.cmd - vendor entry bootstrap (FIX-238.1/238.3, ADR-017 2)
rem
rem Locates resolve_entry.py next to this script and runs it with a bounded
rem timeout. Timeout and classification are delegated to the cross-platform
rem thin wrapper `verify_workflow.py resolve-entry` (SPG_RESOLVE_TIMEOUT,
rem default 15s). Hosts without AGENTS.md/CLAUDE.md can still call this
rem script directly (documented in commands/governance.md).
rem
rem Exit codes (shared contract with bootstrap.sh and resolve-entry):
rem   0  success - envelope JSON on stdout
rem   1  resolve_entry exited non-zero (other failure)
rem   2  python not found
rem   3  resolve_entry.py not found
rem   4  timeout (SPG_RESOLVE_TIMEOUT, default 15s)
rem   5  store stub (resolve_entry.py exists but is not the canonical resolver)

setlocal
set "SCRIPT_DIR=%~dp0"

if defined SPG_BOOTSTRAP_PYTHON (
    set "PY=%SPG_BOOTSTRAP_PYTHON%"
) else (
    set "PY=python"
)

"%PY%" -c "import sys" >nul 2>&1
if errorlevel 1 (
    echo spg-bootstrap-error: python-missing - "%PY%" not found on PATH 1>&2
    exit /b 2
)

if not exist "%SCRIPT_DIR%resolve_entry.py" (
    echo spg-bootstrap-error: file-not-found - resolve_entry.py missing at "%SCRIPT_DIR%resolve_entry.py" 1>&2
    exit /b 3
)

findstr /C:"Deterministic /governance entry resolver (FX-130)" "%SCRIPT_DIR%resolve_entry.py" >nul 2>&1
if errorlevel 1 (
    echo spg-bootstrap-error: store-stub - resolve_entry.py is not the canonical resolver ^(missing FX-130 marker^); reinstall the plugin 1>&2
    exit /b 5
)

if not exist "%SCRIPT_DIR%verify_workflow.py" (
    echo spg-bootstrap-error: file-not-found - verify_workflow.py missing at "%SCRIPT_DIR%verify_workflow.py" 1>&2
    exit /b 3
)

"%PY%" "%SCRIPT_DIR%verify_workflow.py" resolve-entry --project-root "%CD%"
exit /b %errorlevel%
