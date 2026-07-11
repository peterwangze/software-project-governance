"""Git fact collection with explicit PASS/FAIL/UNKNOWN/BLOCKED semantics."""

from pathlib import Path
import re
from typing import Dict, Optional

from .context import RepositoryContext
from .model import CheckResult


REMOTE_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}\Z")
HEX_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")


def validate_remote_name(remote: object) -> Optional[str]:
    if not isinstance(remote, str) or not REMOTE_NAME_RE.fullmatch(remote):
        return None
    if remote.startswith("-") or ".." in remote or "//" in remote:
        return None
    return remote


def resolve_commit(context: RepositoryContext, value: str) -> CheckResult:
    rc, stdout, stderr = context.run_git("rev-parse", "--verify", f"{value}^{{commit}}")
    if rc == 124 or rc == 125:
        return CheckResult("UNKNOWN", [stderr or "git commit lookup unavailable"])
    if rc != 0 or not HEX_SHA_RE.fullmatch(stdout):
        return CheckResult("FAIL", [f"commit `{value}` cannot be resolved"])
    return CheckResult("PASS", facts={"commit": stdout})


def commit_adding_path(context: RepositoryContext, relative_path: str) -> CheckResult:
    rc, stdout, stderr = context.run_git(
        "log", "--diff-filter=A", "--format=%H", "--", relative_path
    )
    if rc == 124 or rc == 125:
        return CheckResult("UNKNOWN", [stderr or "git history unavailable"])
    commits = [line for line in stdout.splitlines() if HEX_SHA_RE.fullmatch(line)]
    if len(commits) != 1:
        return CheckResult(
            "FAIL",
            [f"expected exactly one commit adding `{relative_path}`, found {len(commits)}"],
            {"commits": commits},
        )
    return CheckResult("PASS", facts={"commit": commits[0]})


def is_shallow(context: RepositoryContext) -> bool:
    rc, stdout, _stderr = context.run_git("rev-parse", "--is-shallow-repository")
    return rc == 0 and stdout.lower() == "true"


def tag_facts(
    context: RepositoryContext,
    tag: str,
    expected_commit: str,
    remote: object = "origin",
) -> CheckResult:
    safe_remote = validate_remote_name(remote)
    if safe_remote is None:
        return CheckResult("BLOCKED", ["lineage remote must be a configured Git remote name"])

    local = resolve_commit(context, f"refs/tags/{tag}")
    if local.state != "PASS":
        state = "UNKNOWN" if local.state == "UNKNOWN" else "FAIL"
        issue = (
            f"local tag lookup for `{tag}` is unavailable"
            if state == "UNKNOWN"
            else f"local tag `{tag}` does not exist"
        )
        return CheckResult(state, [issue])
    local_commit = local.facts["commit"]
    issues = []
    if local_commit != expected_commit:
        issues.append(f"local tag `{tag}` points to {local_commit}, expected {expected_commit}")

    rc, _url, stderr = context.run_git("remote", "get-url", safe_remote)
    if rc == 124 or rc == 125:
        return CheckResult("UNKNOWN", [stderr or "remote identity lookup unavailable"])
    if rc != 0:
        return CheckResult("BLOCKED", [f"configured Git remote `{safe_remote}` was not found"])

    rc, output, stderr = context.run_git(
        "ls-remote", "--tags", safe_remote, f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"
    )
    if rc == 124 or rc == 125:
        return CheckResult("UNKNOWN", [f"remote tag lookup failed for `{safe_remote}`: no verified result"])
    if rc != 0:
        return CheckResult("UNKNOWN", [f"remote tag lookup failed for `{safe_remote}`"])

    refs: Dict[str, str] = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 2 and HEX_SHA_RE.fullmatch(parts[0]):
            refs[parts[1]] = parts[0]
    remote_commit = refs.get(f"refs/tags/{tag}^{{}}") or refs.get(f"refs/tags/{tag}")
    if not remote_commit:
        issues.append(f"remote `{safe_remote}` is missing tag `{tag}`")
    elif remote_commit != expected_commit:
        issues.append(f"remote tag `{safe_remote}/{tag}` points to {remote_commit}, expected {expected_commit}")

    return CheckResult(
        "FAIL" if issues else "PASS",
        issues,
        {
            "tag": tag,
            "remote": safe_remote,
            "local_tag_commit": local_commit,
            "remote_tag_commit": remote_commit,
        },
    )
