"""Execute the bounded native validation commands for a candidate plugin release."""

from project_paths import package_root as _package_root
import locale
import os
import subprocess
import sys


# Provenance: 0.91.0 M calibration-session machine records (DEC-264(2)) —
# full bounded suite 1554.78 s in a single measurement (pwsh-167 M-1 run:
# 4351P/1F/1S/540 subtests; M-2 dual-source runs pwsh-170/171: 4359P/0F/1S/
# 527). Single observation, so it serves as the p50 proxy (n=1, disclosed).
# New budget = p50 x 1.5 = ceil(1554.78 x 1.5) = ceil(2332.17) = 2333 s.
# Inverse check at calibration time: halved (1166.5 s) it stays RED against
# the observed run (1554.78 s), so the budget still bites. Same-session
# targeted corroboration (2026-09-28, this repo): bounded-command
# representative subset (release/upgrade-gate/smoke/hook classes, exit 0)
# single run 15.844 s; static TestLoader count 948 methods — the full-suite
# machine-record anchor above remains the calibration basis. The
# SPG_RELEASE_GATE_TIMEOUT env override (FIX-234) keeps priority.
_RELEASE_GATE_TIMEOUT_DEFAULT = 2333


_RELEASE_GATE_TIMEOUT_ENV = "SPG_RELEASE_GATE_TIMEOUT"


def _resolve_release_gate_timeout(raw, *, release_gate_timeout_default=_RELEASE_GATE_TIMEOUT_DEFAULT):
    """FIX-234: resolve the release-gate timeout from an env-var value.

    Returns the value when it is a positive integer, otherwise the module
    default (_RELEASE_GATE_TIMEOUT_DEFAULT — 180 s in the FIX-234 era,
    recalibrated to 2333 s by FIX-400; provenance lives on the constant).
    Invalid values fall back instead of crashing the gate; that
    fallback-not-crash contract is unchanged by the recalibration.
    """
    raw = (raw or "").strip()
    if not raw:
        return release_gate_timeout_default
    try:
        value = int(raw)
    except ValueError:
        return release_gate_timeout_default
    return value if value > 0 else release_gate_timeout_default


def _run_release_validation_command(label, command, timeout=None, *, package_root=None,
                                    release_gate_timeout_env=_RELEASE_GATE_TIMEOUT_ENV,
                                    resolve_release_gate_timeout=_resolve_release_gate_timeout):
    """Run one release validation command and normalize its result.

    timeout: explicit seconds; when None (default) the
    SPG_RELEASE_GATE_TIMEOUT env var (integer seconds, FIX-234) is honored,
    falling back to the module default for absent/invalid values.
    """
    if timeout is None:
        timeout = resolve_release_gate_timeout(
            os.environ.get(release_gate_timeout_env, "")
        )
    try:
        completed = subprocess.run(
            command,
            cwd=str(package_root if package_root is not None else _package_root()),
            capture_output=True,
            text=True,
            encoding=locale.getpreferredencoding(False),
            errors="replace",
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        return {
            "label": label,
            "pass": False,
            "exit_code": None,
            "issue": f"{label}: command did not complete: {exc}",
            "command": " ".join(str(part) for part in command),
        }

    output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
    issue = None if completed.returncode == 0 else (
        f"{label}: exit={completed.returncode}; "
        f"output={output[-500:] if output else '<empty>'}"
    )
    return {
        "label": label,
        "pass": completed.returncode == 0,
        "exit_code": completed.returncode,
        "issue": issue,
        "command": " ".join(str(part) for part in command),
    }


def run_release_execution_gates(runner=_run_release_validation_command, timeout=None, *, package_root=None):
    """Run command-backed release gates that must be green before publishing.

    timeout: optional explicit seconds forwarded to the runner. When omitted,
    the runner resolves its own timeout (SPG_RELEASE_GATE_TIMEOUT env var,
    module default — FIX-234, recalibrated by FIX-400). Custom two-arg
    runners keep working unchanged.
    """
    package_root = package_root if package_root is not None else _package_root()
    verify_script = package_root / "skills/software-project-governance/infra/verify_workflow.py"
    commands = [
        ("verify", [sys.executable, str(verify_script), "verify"]),
        ("governance health", [sys.executable, str(verify_script), "check-governance", "--fail-on-issues"]),
        ("e2e check", [sys.executable, str(verify_script), "e2e-check"]),
        ("unit tests", [sys.executable, "-m", "unittest", "skills/software-project-governance/infra/tests/test_verify_workflow.py", "-v"]),
    ]
    if timeout is None:
        return [runner(label, command) for label, command in commands]
    return [runner(label, command, timeout=timeout) for label, command in commands]
