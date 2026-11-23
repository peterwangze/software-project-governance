"""Read release provenance from host governance history and Git lineage."""

from checks.commit import check_release_lineage as _inspect_lineage
from pathlib import Path
from project_paths import default_host_root
import os
import re
import subprocess


def _provenance_rows_from_report(report):
    """Map a task_priority.PriorityReport to provenance_domain row dicts.

    Bucket vocabulary parity is the contract (module docstring of
    provenance_domain): recommended_next → recommended, non_executable →
    non_executable, blocked → blocked, completed → completed.
    """
    def _row(task, bucket):
        return {
            "task_id": task.task_id,
            "demand_source": task.demand_source,
            "bucket": bucket,
            "priority": task.priority,
            "target_version": task.target_version,
        }

    rows = []
    for task in getattr(report, "recommended_next", None) or []:
        rows.append(_row(task, "recommended"))
    for task in getattr(report, "non_executable", None) or []:
        rows.append(_row(task, "non_executable"))
    for blocked in getattr(report, "blocked", None) or []:
        task = getattr(blocked, "task", None) or blocked
        rows.append(_row(task, "blocked"))
    for task in getattr(report, "completed", None) or []:
        rows.append(_row(task, "completed"))
    return rows


def _provenance_rows_for_governance(tracker_path=None, governance_dir=None, *, read_governance_dir=None,
                                    plan_path=None, provenance_rows_from_report=_provenance_rows_from_report):
    """Live provenance rows: parse → demand-source resolve → report → rows.

    The same orchestration run_cli_analysis uses (L2514-2520): parse the
    plan-tracker, resolve demand sources against the triage records +
    revision streams, then compute the bucketed report.
    """
    import task_priority as tpa
    gov = Path(governance_dir) if governance_dir else read_governance_dir
    if gov is None:
        gov = default_host_root() / ".governance"
    path = Path(tracker_path) if tracker_path else (plan_path if plan_path is not None else gov / "plan-tracker.md")
    if not path.is_file():
        return []
    try:
        resolved, _lag_warnings = tpa._resolve_row_demand_sources(
            tpa.parse_task_dependencies(path), gov)
        report = tpa.compute_unblocked_tasks(
            resolved,
            archive_completed_ids=tpa.read_archive_index_completed_ids(gov))
    except Exception:
        return []
    return provenance_rows_from_report(report)


def _collect_session_closure_events(governance_dir, today, *, read_governance_dir):
    """FEAT-083: thin delegation to the shared collection leaf.

    The W(session) collection core (the evidence/risk row arms, the
    deferred-ledger arm, the window note) lives in
    ``checks.provenance_domain.collect_session_closure_events`` — engine
    (Check 42) and bootstrap (the behavior.session_closure sub-face) both
    consume that ONE source; the FEAT-082 bootstrap mirror is retired
    (zero second implementation — review-FEAT-082-CODE-R0 §6.3). The
    legacy signature is preserved (Check 42 + the FEAT-080/081 test call
    sites unchanged), including the ``governance_dir=None →
    GOVERNANCE_DIR`` default the leaf cannot own (it must stay
    engine-global-free); the delegation import is FUNCTION-LOCAL so the
    frozen cold-import face (ArchGuard R6) is untouched.
    """
    from checks.provenance_domain import collect_session_closure_events
    return collect_session_closure_events(
        governance_dir if governance_dir else read_governance_dir, today=today)


GIT_LINEAGE_TIMEOUT_SECONDS = 15


GIT_REMOTE_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}\Z")


def _run_git_lineage(args, root=None, *, host_project_root=None, git_lineage_timeout_seconds=GIT_LINEAGE_TIMEOUT_SECONDS):
    root = Path(root or host_project_root or default_host_root())
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=git_lineage_timeout_seconds,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return 124, "", f"git command timed out after {git_lineage_timeout_seconds}s"
    except OSError as exc:
        return 125, "", f"git command could not be started ({type(exc).__name__})"
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _validated_git_remote_name(remote, *, git_remote_name_re=GIT_REMOTE_NAME_RE):
    """Return a safe Git remote name; URLs, options, and control/whitespace input are rejected."""
    if not isinstance(remote, str) or not git_remote_name_re.fullmatch(remote):
        return None
    if ".." in remote or "//" in remote:
        return None
    return remote


def check_release_lineage(version, mode="candidate", release_commit=None, remote="origin", root=None, *,
                          host_project_root=None, git_lineage_timeout_seconds=GIT_LINEAGE_TIMEOUT_SECONDS,
                          run_git_lineage=_run_git_lineage, inspect_lineage=_inspect_lineage):
    """Delegate release lineage checks while preserving the 0.65.3 API."""
    return inspect_lineage(
        version,
        mode=mode,
        release_commit=release_commit,
        remote=remote,
        root=Path(root or host_project_root or default_host_root()),
        git=lambda args, git_root, _timeout: run_git_lineage(args, git_root),
        timeout=git_lineage_timeout_seconds,
    )
