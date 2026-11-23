"""Phase 6 commit and release-lineage checks."""

import re
from pathlib import Path
from typing import Optional

from release.context import RepositoryContext, run_git
from release.git_facts import tag_facts, validate_remote_name
from release.model import CheckResult


def check_release_lineage(
    version: Optional[str],
    mode: str = "candidate",
    release_commit: Optional[str] = None,
    remote: object = "origin",
    root: Optional[Path] = None,
    git=None,
    timeout: int = 15,
) -> dict:
    context = RepositoryContext(Path(root or Path.cwd()), git=git or run_git, timeout=timeout)
    safe_remote = validate_remote_name(remote)
    base = {
        "mode": mode,
        "version": version,
        "release_commit": release_commit,
        "remote": safe_remote,
        "tag": f"v{version}" if version else None,
    }
    issues = []
    if safe_remote is None:
        result = CheckResult("BLOCKED", ["lineage remote must be a configured Git remote name"], base)
        return result.as_dict()
    if mode not in {"candidate", "released"}:
        result = CheckResult("FAIL", [f"unsupported lineage mode `{mode}`; expected candidate or released"], base)
        return result.as_dict()
    if mode == "candidate":
        base["boundary"] = (
            "candidate mode intentionally does not require a tag before the release commit exists; "
            "rerun with --lineage-mode released --release-commit <commit> after tag creation and push"
        )
        return CheckResult("PASS", facts=base).as_dict()
    if not version:
        issues.append("released lineage mode requires --version")
    if not release_commit:
        issues.append("released lineage mode requires --release-commit")
    if issues:
        return CheckResult("FAIL", issues, base).as_dict()
    from release.git_facts import resolve_commit

    expected = resolve_commit(context, release_commit)
    if expected.state != "PASS":
        return CheckResult(expected.state, [f"release commit `{release_commit}` cannot be resolved"], base).as_dict()
    base["expected_commit"] = expected.facts["commit"]
    tagged = tag_facts(context, f"v{version}", expected.facts["commit"], safe_remote)
    base.update(tagged.facts)
    return CheckResult(tagged.state, tagged.issues, base).as_dict()


def github_merge_task_match(root, oid, subject, task_pattern):
    """Inherit the incoming task only for a content-preserving GitHub PR merge."""
    title = re.fullmatch(r"Merge pull request #[1-9][0-9]* from [A-Za-z0-9][A-Za-z0-9-]*/(\S+)", subject)
    if not title:
        return None

    def git(*args):
        return run_git(["--no-replace-objects", *args], root, timeout=15)

    branch = title.group(1)
    rc, validated_branch, _ = git("check-ref-format", "--branch", branch)
    if rc or validated_branch != branch:
        return None
    rc, metadata, _ = git("show", "-s", "--no-show-signature", "--format=%T %P", oid)
    fields = metadata.split()
    if rc or len(fields) != 3:
        return None
    tree, base, incoming = fields
    if git("merge-base", "--is-ancestor", base, incoming)[0] != 0:
        return None
    rc, tip, _ = git("show", "-s", "--no-show-signature", "--format=%T%x00%s", incoming)
    incoming_tree, separator, incoming_subject = tip.partition("\x00")
    if rc or not separator or tree != incoming_tree:
        return None
    return task_pattern.match(incoming_subject)


from datetime import date
from datetime import datetime


def check_commit_task_references(limit=20, *, product_root):
    """Check that recent commit messages contain task ID references.

    Per M7.4 step 4 and M7.5 step 4, every commit message MUST contain
    a task ID as prefix (e.g., "AUDIT-044: description", "MAINT-028: description").
    This function is the external validation counterpart — it detects commits
    without task ID prefixes, which indicate untracked modifications.

    FIX-420 revert awareness: a revert of tracked work quotes the original
    subject (``Revert "FIX-397: ..."``), so the tracked-task evidence lives
    at the start of the quoted original subject, not at the message start.
    Such a commit counts as tracked, and ``task_id`` records the ORIGINAL
    task ID in plain machine-readable form (e.g. "FIX-397" — no decorated
    "(revert)" suffix, so downstream consumers can match it with the same
    ``[A-Z]+-\\d+`` caliber). Fail-closed boundary: ONLY a ``Revert "``
    prefix whose quoted original subject itself starts with a legal task
    ID counts as tracked — plain no-ID subjects and reverts of no-ID
    subjects remain reported as untracked.

    Returns: dict with commits list, issues list, and summary stats.
    """
    import subprocess
    try:
        result = subprocess.run(
            ["git", "-C", str(product_root), "log", f"--format=%H %s", f"-{limit}"],
            capture_output=True, text=True, timeout=10, encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            return {"error": f"git log failed: {result.stderr}", "commits": [], "issues": []}
    except FileNotFoundError:
        return {"error": "git command not found", "commits": [], "issues": []}
    except Exception as e:
        return {"error": str(e), "commits": [], "issues": []}

    commits = []
    issues = []
    # Match task ID prefix at start of commit message: "AUDIT-044: ..." or "MAINT-028: ..."
    task_id_pattern = re.compile(r"^([A-Z]+-\d+)")
    # FIX-420: revert subjects quote the original — `Revert "FIX-397: ..."`.
    revert_subject_pattern = re.compile(r'^Revert "([^"]*)"')

    if not result.stdout:
        return {"error": "git log returned empty output", "commits": [], "issues": []}

    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split(" ", 1)
        if len(parts) < 2:
            continue
        sha = parts[0][:7]
        message = parts[1]

        task_match = task_id_pattern.match(message)
        if task_match is None:
            # FIX-420: fall back to the quoted original subject of a revert.
            revert_match = revert_subject_pattern.match(message)
            if revert_match is not None:
                task_match = task_id_pattern.match(revert_match.group(1))
            else:
                # A GitHub-generated merge may have no ticket in its title.
                # Its incoming ticket applies only when Git proves that the
                # wrapper contributes no additional content or divergence.
                task_match = github_merge_task_match(product_root, parts[0], message, task_id_pattern)
        has_task_id = task_match is not None
        task_id = task_match.group(1) if has_task_id else None

        commit_info = {
            "sha": sha,
            "message": message,
            "has_task_id": has_task_id,
            "task_id": task_id,
        }
        commits.append(commit_info)

        if not has_task_id:
            issues.append(commit_info)

    return {
        "commits": commits,
        "issues": issues,
        "total_checked": len(commits),
        "without_task_id": len(issues),
    }

def check_task_deadline(*, plan_path, status_is_terminal_cell):
    """Check for non-completed tasks whose planned completion date has passed.

    Per AUDIT-048: plan-tracker has "计划完成" column for each task,
    but when the date passes with task still in "未开始" or "进行中",
    nothing detects or escalates it. This is the same pattern as risk escalation
    (AUDIT-045) — deadline fields exist but are not enforced.

    Returns: dict with overdue tasks list and summary stats.
    """
    content = plan_path.read_text(encoding="utf-8")
    today = date.today()
    overdue = []
    all_active = 0

    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| ") or "---" in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 15:
            continue

        task_id_match = re.match(r"([A-Z]+-\d+)", parts[1])
        if not task_id_match:
            continue

        task_id = task_id_match.group(1)
        status = parts[10] if len(parts) > 10 else ""
        priority = parts[11] if len(parts) > 11 else ""
        # Column mapping: 0=empty,1=ID,...,12=计划开始,13=计划完成,14=实际完成
        plan_complete_str = parts[13] if len(parts) > 13 else ""

        # Only check non-terminal tasks — FIX-479: shared terminal
        # predicate (_status_is_terminal_cell, same source as the DRI
        # face in check_protocol_compliance) normalizes emoji-prefixed
        # terminal shapes (「✅ 已完成」/「✅ committed」/「✅ 完成」/
        # 「⏳ ✅ committed」); the overdue semantics for genuinely active
        # rows (passed deadline → WARN) are unchanged.
        if status_is_terminal_cell(status):
            continue

        all_active += 1

        if not plan_complete_str or plan_complete_str == "":
            continue

        try:
            plan_complete = datetime.strptime(plan_complete_str, "%Y-%m-%d").date()
            if today > plan_complete:
                overdue.append({
                    "task_id": task_id,
                    "status": status,
                    "priority": priority,
                    "plan_complete": plan_complete_str,
                    "days_overdue": (today - plan_complete).days,
                })
        except ValueError:
            continue

    # Sort by priority then days overdue
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    overdue.sort(key=lambda t: (priority_order.get(t["priority"], 99), -t["days_overdue"]))

    return {
        "overdue": overdue,
        "total_active": all_active,
        "overdue_count": len(overdue),
    }

def check_commit_scope(limit=20, *, product_root):
    """Check recent commits for scope discipline violations:
    1. If commit message contains "顺带" / "also" / "顺便" keywords -> WARN
    2. Single commit touching > 15 files -> WARN (possible bulk commit)

    Multiple commits for the same task are normal for review/rework loops and
    are not a scope violation.
    """
    import subprocess

    try:
        # Get full commit log with stats
        result = subprocess.run(
            ["git", "-C", str(product_root), "log", f"--format=%H%x00%s", f"-{limit}",
             "--no-merges"],
            capture_output=True, text=True, timeout=10, encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            return {"error": f"git log failed: {result.stderr}", "issues": []}
    except FileNotFoundError:
        return {"error": "git command not found", "issues": []}
    except Exception as e:
        return {"error": str(e), "issues": []}

    if not result.stdout:
        return {"error": "git log returned empty output", "issues": []}

    issues = []
    duo_commits = []        # commits with "also"/"顺带"/"顺便"

    lines = result.stdout.strip().split("\n")
    for line in lines:
        if not line or "\x00" not in line:
            continue
        sha, message = line.split("\x00", 1)
        sha_short = sha[:7]

        # Check 1: "顺带"/"also"/"顺便" keywords
        if re.search(r"顺带|顺便|also\b", message, re.IGNORECASE):
            duo_commits.append({"sha": sha_short, "message": message[:100]})

        # Check 2: files touched > 15 (use git show --stat)
        try:
            stat_result = subprocess.run(
                ["git", "-C", str(product_root), "show", "--stat", "--format=", sha],
                capture_output=True, text=True, timeout=5, encoding="utf-8",
                errors="replace",
            )
            if stat_result.returncode == 0:
                # Count changed files from --stat output
                file_count = len([l for l in stat_result.stdout.split("\n")
                                 if l.strip() and "|" in l and not l.startswith(" ")])
                if file_count > 15:
                    issues.append({
                        "type": "bulk_commit",
                        "sha": sha_short,
                        "detail": f"{file_count} files changed in single commit",
                    })
        except (subprocess.TimeoutExpired, Exception):
            pass

    # Add duo keyword warnings
    for duo in duo_commits:
        issues.append({
            "type": "side_effect_warning",
            "sha": duo["sha"],
            "detail": f"Commit contains 'also/顺带/顺便': {duo['message']}",
        })

    return {
        "issues": issues,
        "total_checked": len(lines),
        "issue_count": len(issues),
    }
