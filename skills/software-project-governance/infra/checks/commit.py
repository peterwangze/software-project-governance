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
