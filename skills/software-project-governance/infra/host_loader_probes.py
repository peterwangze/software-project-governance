"""Run the isolated DSH preset-session smoke and evaluate its release-gate verdict."""

from dataclasses import dataclass
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys


@dataclass(frozen=True)
class SmokeMarkers:
    concurrent_writes: re.Pattern
    home_writes: re.Pattern
    passed: re.Pattern


DSH_SMOKE_REAL_HOME_WRITES_RE = re.compile(
    r"\[SMOKE\]\s*real-home writes\s*:\s*(\d+)")


DSH_SMOKE_ATTRIBUTED_CONCURRENT_WRITES_RE = re.compile(
    r"\[SMOKE\]\s*attributed concurrent writes\s*:\s*(\d+)")


DSH_SMOKE_RESULT_PASS_RE = re.compile(r"\[SMOKE\]\s*Result:\s*PASS")


def check_dsh_preset_smoke(root=None, timeout=120, *, plugin_root=None, markers=None):
    """FEAT-015 / RISK-049 ②: run the isolated preset-session smoke gate.

    ``root`` overrides the package root (test seam); it defaults to
    PLUGIN_ROOT, where ``adapters/dsh/launch.py`` lives. Returns
    the verdict, reason, launcher exit code, output and isolation witness.

    FIX-442: keep launcher attribution separate from smoke-owned writes.
    """
    if plugin_root is None:
        plugin_root = Path(__file__).resolve().parents[3]
    if markers is None:
        markers = SmokeMarkers(
            concurrent_writes=DSH_SMOKE_ATTRIBUTED_CONCURRENT_WRITES_RE,
            home_writes=DSH_SMOKE_REAL_HOME_WRITES_RE, passed=DSH_SMOKE_RESULT_PASS_RE,
        )
    package_root = Path(root) if root is not None else plugin_root
    launcher = package_root / "adapters" / "dsh" / "launch.py"
    result = {
        "verdict": "FAIL",
        "reason": "",
        "exit_code": None,
        "details": [],
        "isolation": {
            "temp_home": None,
            "real_home_writes": None,
            "attributed_concurrent_writes": None,
        },
    }
    if not launcher.is_file():
        result["reason"] = f"dsh launcher missing: {launcher.as_posix()}"
        return result

    from dsh_temp import make_private_dir
    try:
        temp_home = make_private_dir("spg-dsh-smoke-")
    except OSError as exc:
        result["reason"] = f"could not create private DSH smoke directory: {exc}"
        return result
    result["isolation"]["temp_home"] = temp_home.as_posix()
    env = os.environ.copy()
    env["DSH_HOME"] = str(temp_home)
    try:
        proc = subprocess.run(
            [sys.executable, str(launcher), "--smoke"],
            cwd=str(package_root),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        result["reason"] = f"smoke timed out after {timeout}s"
        return result
    except OSError as exc:
        result["reason"] = f"smoke could not start: {exc}"
        return result
    finally:
        shutil.rmtree(temp_home, ignore_errors=True)

    result["exit_code"] = proc.returncode
    output = (proc.stdout or "") + (proc.stderr or "")
    result["details"] = [
        line.strip() for line in output.splitlines() if line.strip()]
    writes = markers.home_writes.search(output)
    if writes:
        result["isolation"]["real_home_writes"] = int(writes.group(1))
    attributed = markers.concurrent_writes.search(output)
    if attributed:
        result["isolation"]["attributed_concurrent_writes"] = int(
            attributed.group(1))

    if proc.returncode == 0 and markers.passed.search(output):
        if result["isolation"]["real_home_writes"] not in (0, None):
            result["reason"] = (
                "smoke reported real-home writes="
                f"{result['isolation']['real_home_writes']} — refusing to "
                "accept the run as PASS")
            return result
        result["verdict"] = "PASS"
        # FIX-442: the reason must stay truthful when the launcher excluded
        # concurrent-session writes — the smoke touched nothing, but the
        # real home DID change during the window, and that is disclosed
        # here instead of the blanket "real ~/.dsh untouched" claim.
        reason = (
            "isolated preset-session smoke PASSED (skill catalog + "
            "/governance gesture resolved; real ~/.dsh untouched by the "
            "smoke")
        attributed_count = result["isolation"]["attributed_concurrent_writes"]
        if attributed_count:
            reason += (
                f"; {attributed_count} write-face change(s) attributed to "
                "a concurrent active session and excluded (time-window + "
                "entry-semantics dual factor, FIX-442)")
        result["reason"] = reason + ")"
        return result

    if proc.returncode == 2 and re.search(
            r"^\[SMOKE\] Result: NOT_RUN \(exit 2\) HOST_PLANE_ABSENT:", output, re.MULTILINE):
        result["verdict"] = "NOT_RUN"
        result["reason"] = "no installed DSH host plane for the isolated upgrade smoke"
        return result

    diagnostics = [
        detail for detail in result["details"]
        if "[FAIL]" in detail or "[REFUSED]" in detail or "FAIL:" in detail
    ]
    result["reason"] = (
        f"smoke exit {proc.returncode}"
        + (f": {diagnostics[0]}" if diagnostics else "")
    )
    return result


DSH_UPGRADE_REGRESSION_LABEL = "dsh preset-session smoke (isolated upgrade regression)"


def run_dsh_upgrade_regression_gates(
        smoke_runner, *, plugin_root, dsh_upgrade_regression_label, release_gate_timeout_env,
        resolve_release_gate_timeout, check_dsh_preset_smoke,
):
    """FEAT-016 / RISK-049 ③: run the dsh upgrade regression command set.

    Composition (minimal, per triage): the FEAT-015 isolated preset-session
    smoke — preset install + skill-catalog load under a temp DSH_HOME. Each
    result matches the release execution-gate result shape (label / pass /
    exit_code / issue / command) so check_release_readiness renders it like
    any other gate. ``smoke_runner`` is a test seam; production always uses
    check_dsh_preset_smoke (reuse only — never a reimplementation).

    Returns ``{"results": [...], "issues": [...], "isolation":
    {"temp_dsh_home", "real_home_writes", "mechanism"}}``.
    """
    if smoke_runner is None:
        smoke_runner = check_dsh_preset_smoke
    timeout = resolve_release_gate_timeout(
        os.environ.get(release_gate_timeout_env, ""))
    smoke = smoke_runner(timeout=timeout)
    launcher = plugin_root / "adapters" / "dsh" / "launch.py"
    passed = smoke["verdict"] == "PASS"
    gate = {
        "label": dsh_upgrade_regression_label,
        "pass": passed,
        "exit_code": smoke["exit_code"],
        "issue": None if passed else (
            f"{dsh_upgrade_regression_label}: {smoke['reason']}"),
        "command": (
            f"{sys.executable} {launcher.as_posix()} --smoke"
            " (temp DSH_HOME redirection, real home zero-write)"),
    }
    isolation = {
        "temp_dsh_home": smoke["isolation"].get("temp_home"),
        "real_home_writes": smoke["isolation"].get("real_home_writes"),
        "mechanism": (
            "env redirection to a temp DSH_HOME (M7.7 (a)); the launcher "
            "fingerprints the real home and the smoke refuses PASS on any "
            "real-home write (FEAT-015 real-home-writes detection)"),
    }
    return {
        "results": [gate],
        "issues": [gate["issue"]] if gate["issue"] else [],
        "isolation": isolation,
    }


def cmd_check_dsh_preset_smoke(args, *, smoke=None):
    """Run the isolated DSH preset-session smoke gate (FEAT-015)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from checks.dsh_smoke import emit_cli_result

    if smoke is None:
        smoke = _doctor_smoke if _doctor_smoke is not None else check_dsh_preset_smoke
    status = emit_cli_result(smoke())
    if status and getattr(args, "fail_on_issues", False):
        sys.exit(status)


def _installed_channel_check(root):
    from exploration_evidence import check_exploration_channels
    return check_exploration_channels(root)


# Independent doctor and registry consumers use the installed domain implementations.
_doctor_smoke = None
_doctor_channels = _installed_channel_check
_workflow_command = None


def bind_workflow_dsh(*, smoke, channels, command):
    """Honor live overrides when the workflow engine is present in this process."""
    global _doctor_smoke, _doctor_channels, _workflow_command
    _doctor_smoke = smoke
    _doctor_channels = channels
    _workflow_command = command


def effective_command(name, native):
    if _workflow_command is None:
        return native
    return _workflow_command(name, native)


def doctor_smoke(root, timeout=120):
    if _doctor_smoke is None:
        return check_dsh_preset_smoke(root, timeout=timeout)
    return _doctor_smoke(timeout=timeout)


def doctor_channels(root):
    return _doctor_channels(root)
