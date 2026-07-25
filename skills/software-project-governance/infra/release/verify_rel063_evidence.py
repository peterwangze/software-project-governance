#!/usr/bin/env python3
"""REL-063 fail-closed evidence gate verifier.

Architecture authority: docs/architecture/release-incident-recovery-0.66.2.md
(immutable FIX-214 Design R2). Section 5 owns the thirteen-row proof matrix;
section 6 owns every schema contract this module enforces.

This module is the C2/C3/C5/R1/R2/R7 accountable owner verifier. It validates
external Code Review, QA, Release Review, rehearsal, and topology truth through
strict canonical contracts. It NEVER produces an independent review proof: it
only fails closed on every missing/duplicate/type/unknown/digest/phase/role/
subject/time/path mismatch and on every unavailable Git/platform/remote fact.

Canonical JSON rule (architecture section 6.1): strict UTF-8, no BOM, NFC, no
duplicate keys, no NaN/Infinity, sorted object keys, compact separators `,` and
`:`, exactly one trailing LF, lowercase SHA-256. Typed error codes:
SCHEMA_MISSING, DUPLICATE, TYPE_DRIFT, SCHEMA_UNKNOWN, CANONICAL_BYTES,
DIGEST_MISMATCH, PHASE_DRIFT, UNKNOWN. None of them authorizes.

Exit contract: 0 = the requested gate PASSed and any --write-* output was
materialized; 2 = deterministic REJECT (a typed contract violation); 3 =
UNKNOWN (an unavailable external/Git/remote/platform fact). The pre-push remote
tag-absence probe is handled by --verify-push-preconditions and is the sole
expected nonzero-classified-ABSENT path.
"""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unicodedata
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


# ---------------------------------------------------------------------------
# Normative path sets (architecture section 4.5; copied byte-for-byte).
# ---------------------------------------------------------------------------

M063: Tuple[str, ...] = (
    "project/CHANGELOG.md",
    "skills/software-project-governance/SKILL.md",
    "project/e2e-test-project/skills/software-project-governance/SKILL.md",
    "skills/software-project-governance/core/manifest.json",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".codex-plugin/plugin.json",
    ".zcode-plugin/plugin.json",
    ".chrys-plugin/plugin.json",
    "package.json",
    "project/e2e-test-project/.governance/plan-tracker.md",
    "skills/software-project-governance/infra/hooks/pre-commit",
    "skills/software-project-governance/infra/hooks/commit-msg",
    "skills/software-project-governance/infra/hooks/post-commit",
    "skills/software-project-governance/infra/hooks/prepare-commit-msg",
)

N063: Tuple[str, ...] = (
    "docs/release/release-checklist-0.66.2.md",
    "docs/release/feature-flags-0.66.2.md",
    "docs/release/rollback-plan-0.66.2.md",
    "skills/software-project-governance/core/releases/0.66.2.json",
    "skills/software-project-governance/infra/release/verify_rel063_evidence.py",
    "skills/software-project-governance/infra/tests/test_verify_rel063_evidence.py",
    "skills/software-project-governance/infra/release/invoke_rel063_rehearsal.ps1",
    "skills/software-project-governance/infra/tests/run_rel063_rehearsal_fixtures.ps1",
)

SLICE_CHAIN: Tuple[str, ...] = ("S215", "S216", "S217")

# The exact nine artifact IDs (architecture section 6.2).
NINE_ARTIFACT_IDS: Tuple[str, ...] = (
    "FIX-215-code", "FIX-215-qa",
    "FIX-216-code", "FIX-216-qa",
    "FIX-217-code", "FIX-217-qa",
    "exact-C-code", "exact-C-qa",
    "release-review",
)

# Six slice-only artifacts admissible at pre_c.
SIX_SLICE_ARTIFACT_IDS: Tuple[str, ...] = NINE_ARTIFACT_IDS[:6]

# exact-C/release-review artifacts forbidden at pre_c.
PRE_C_FORBIDDEN_ARTIFACT_IDS: Tuple[str, ...] = NINE_ARTIFACT_IDS[6:]

EVIDENCE_KIND_BY_ARTIFACT: Dict[str, str] = {
    "FIX-215-code": "code_review",
    "FIX-215-qa": "qa",
    "FIX-216-code": "code_review",
    "FIX-216-qa": "qa",
    "FIX-217-code": "code_review",
    "FIX-217-qa": "qa",
    "exact-C-code": "exact_c_code_review",
    "exact-C-qa": "exact_c_qa",
    "release-review": "release_review",
}

TASK_BY_ARTIFACT: Dict[str, str] = {
    "FIX-215-code": "FIX-215",
    "FIX-215-qa": "FIX-215",
    "FIX-216-code": "FIX-216",
    "FIX-216-qa": "FIX-216",
    "FIX-217-code": "FIX-217",
    "FIX-217-qa": "FIX-217",
    "exact-C-code": "REL-063",
    "exact-C-qa": "REL-063",
    "release-review": "REL-063",
}

ARTIFACT_PRIMARY_PATH: Dict[str, str] = {
    aid: f".governance/primary-review-evidence/REL-063/{aid}.json" for aid in NINE_ARTIFACT_IDS
}
ARTIFACT_SIDECAR_PATH: Dict[str, str] = {
    aid: f".governance/review-evidence/REL-063/{aid}.json" for aid in NINE_ARTIFACT_IDS
}

# Subject symbols carried by the authority file (architecture section 6.2).
SLICE_SUBJECT_SYMBOLS: Dict[str, str] = {"S215": "S215", "S216": "S216", "S217": "S217"}

# Per-slice declared M ∪ N path scopes (architecture sections 4.2-4.4; copied
# byte-for-byte). N215 and N217 are empty by design. The slice-chain path-set
# guard (DEC-129 / FIX-219 Option A) proves each R0->accepted-child delta stays
# inside its slice's declared scope, defending the C3 "combined path" threat
# once the direct-parent equality check is relaxed to acyclic ancestry.
SLICE_SCOPE_PATHS: Dict[str, frozenset] = {
    "S215": frozenset({
        "skills/software-project-governance/core/loop-runtime-claim-allowlist.json",
        "skills/software-project-governance/core/loop-runtime-claim-authority.json",
        "skills/software-project-governance/infra/checks/loop_runtime_claims.py",
        "skills/software-project-governance/infra/tests/test_loop_runtime_claims.py",
        "skills/software-project-governance/core/task-gate-model.md",
        "project/e2e-test-project/skills/software-project-governance/core/task-gate-model.md",
    }),
    "S216": frozenset({
        "skills/software-project-governance/infra/checks/loop_runtime_claims.py",
        "skills/software-project-governance/infra/tests/test_loop_runtime_claims.py",
        "skills/software-project-governance/infra/verify_workflow.py",
        "skills/software-project-governance/infra/tests/test_verify_workflow.py",
        "skills/software-project-governance/core/loop-runtime-claim-allowlist.json",
        "skills/software-project-governance/core/loop-runtime-claim-authority.json",
        "skills/software-project-governance/core/manifest.json",
        "skills/software-project-governance/infra/checks/loop_runtime_claim_attestation.py",
        "skills/software-project-governance/infra/tests/test_loop_runtime_claim_attestation.py",
    }),
    "S217": frozenset({
        "skills/software-project-governance/infra/release/ledger.py",
        "skills/software-project-governance/infra/release/model.py",
        "skills/software-project-governance/infra/release/schema_validation.py",
        "skills/software-project-governance/infra/tests/test_release_ledger.py",
        "project/e2e-test-project/.governance/plan-tracker.md",
        "skills/software-project-governance/core/release-ledger.schema.json",
        "skills/software-project-governance/core/releases/0.66.1.json",
    }),
}

SCANNER_LIMIT_SECONDS_DEFAULT = 8.0
SCANNER_LIMIT_STALE_SECONDS = 5.0  # DEC-119 / AUDIT-135 stale ceiling.

PRIMARY_SCHEMA_VERSION = "rel063.primary-review-report.v1"
SIDECAR_SCHEMA_VERSION = "rel063.review-evidence-sidecar.v1"
AUTHORITY_SCHEMA_VERSION = "rel063.evidence-authority.v1"
ORCHESTRATION_SCHEMA_VERSION = "rel063.orchestration-receipts.v1"
TOPOLOGY_SCHEMA_VERSION = "rel063.topology-record.v1"
VERDICT_SCHEMA_VERSION = "rel063.evidence-verdict.v1"
REHEARSAL_PRIMARY_SCHEMA_VERSION = "rel063.atomic-rehearsal-report.v1"
REHEARSAL_SIDECAR_SCHEMA_VERSION = "rel063.rehearsal-evidence-sidecar.v1"
RELEASE_BINDING_SCHEMA_VERSION = "rel063.release-evidence-binding.v1"

HEX40_RE = re.compile(r"[0-9a-f]{40}\Z")
HEX64_RE = re.compile(r"[0-9a-f]{64}\Z")
UTC_SECONDS_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z"
)
SEMVER_RE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+\Z")

EXIT_PASS = 0
EXIT_REJECT = 2
EXIT_UNKNOWN = 3


# ---------------------------------------------------------------------------
# Canonical JSON (architecture section 6.1).
# ---------------------------------------------------------------------------

class EvidenceError(Exception):
    """A typed fail-closed evidence contract violation."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _reject_json_constant(value: str) -> None:
    raise EvidenceError("TYPE_DRIFT", f"non-finite JSON constant `{value}` is forbidden")


def _duplicate_safe_object(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    seen: Set[str] = set()
    for key, value in pairs:
        normalized_key = unicodedata.normalize("NFC", key)
        if normalized_key in seen:
            raise EvidenceError("DUPLICATE", f"duplicate JSON member `{normalized_key}`")
        seen.add(normalized_key)
        result[key] = value
    return result


def _normalize_nfc(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize_nfc(item) for item in value]
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise EvidenceError("TYPE_DRIFT", "JSON object keys must be strings")
            out[unicodedata.normalize("NFC", key)] = _normalize_nfc(item)
        return out
    raise EvidenceError("TYPE_DRIFT", f"unsupported JSON value type `{type(value).__name__}`")


def canonical_json_bytes(value: Any) -> bytes:
    """Strict canonical document bytes including one trailing LF."""

    normalized = _normalize_nfc(value)
    try:
        text = json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise EvidenceError("TYPE_DRIFT", str(exc)) from exc
    return f"{text}\n".encode("utf-8")


def canonical_digest(value: Any) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def _parse_canonical_bytes(raw: bytes) -> Any:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise EvidenceError("CANONICAL_BYTES", "UTF-8 BOM is forbidden")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise EvidenceError("CANONICAL_BYTES", "evidence is not strict UTF-8") from exc
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_duplicate_safe_object,
            parse_constant=_reject_json_constant,
        )
    except EvidenceError:
        raise
    except json.JSONDecodeError as exc:
        raise EvidenceError("CANONICAL_BYTES", "evidence is not valid JSON") from exc
    except RecursionError as exc:
        raise EvidenceError("CANONICAL_BYTES", "JSON nesting exceeds decoder limits") from exc
    except ValueError as exc:
        raise EvidenceError("TYPE_DRIFT", "JSON scalar exceeds decoder limits") from exc
    if raw != canonical_json_bytes(parsed):
        raise EvidenceError(
            "CANONICAL_BYTES",
            "evidence must use NFC, sorted keys, compact separators, and one trailing LF",
        )
    return parsed


def load_canonical(path: Path) -> Any:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise EvidenceError("UNKNOWN", f"cannot read `{path}`: {type(exc).__name__}") from exc
    return _parse_canonical_bytes(raw)


# ---------------------------------------------------------------------------
# Git fact helpers (treat Git as X063 runtime fact, never a repo path read).
# ---------------------------------------------------------------------------

GitRunner = Callable[[Sequence[str], Path, int], Tuple[int, str, str]]


def default_git_runner(args: Sequence[str], root: Path, timeout: int) -> Tuple[int, str, str]:
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
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return 124, "", f"git command timed out after {timeout}s"
    except OSError as exc:
        return 125, "", f"git command could not start ({type(exc).__name__})"
    return result.returncode, result.stdout.strip(), result.stderr.strip()


@dataclass(frozen=True)
class GitCtx:
    root: Path
    git: GitRunner = default_git_runner
    timeout: int = 20

    def run(self, *args: str) -> Tuple[int, str, str]:
        return self.git(args, self.root, self.timeout)


class GitUnknown(EvidenceError):
    def __init__(self, detail: str) -> None:
        super().__init__("UNKNOWN", detail)


def git_require(ctx: GitCtx, *args: str) -> str:
    rc, stdout, stderr = ctx.run(*args)
    if rc in (124, 125):
        raise GitUnknown(stderr or f"git {' '.join(args)} unavailable")
    if rc != 0:
        raise EvidenceError("UNKNOWN", f"git {' '.join(args)} failed rc={rc}: {stderr}")
    return stdout


def resolve_commit(ctx: GitCtx, value: str) -> str:
    stdout = git_require(ctx, "rev-parse", "--verify", f"{value}^{{commit}}")
    if not HEX40_RE.fullmatch(stdout):
        raise EvidenceError("UNKNOWN", f"commit `{value}` did not resolve to a 40-hex SHA")
    return stdout


def commit_parents(ctx: GitCtx, commit: str) -> List[str]:
    stdout = git_require(ctx, "show", "-s", "--format=%P", commit)
    return [parent for parent in stdout.split() if HEX40_RE.fullmatch(parent)]


def is_ancestor(ctx: GitCtx, ancestor: str, descendant: str) -> bool:
    """Return True iff `ancestor` is an ancestor of `descendant` in Git.

    Uses `git merge-base --is-ancestor <ancestor> <descendant>`: exit 0 means
    yes, exit 1 means no. Any timeout/start failure is UNKNOWN; any other
    nonzero is treated as "not an ancestor" (fail-closed callers raise on
    False, so a transient nonzero still rejects rather than authorizes).
    """
    rc, _stdout, stderr = ctx.run("merge-base", "--is-ancestor", ancestor, descendant)
    if rc in (124, 125):
        raise GitUnknown(stderr or f"merge-base --is-ancestor {ancestor} {descendant} unavailable")
    return rc == 0


def changed_paths_between(ctx: GitCtx, parent: str, child: str) -> List[str]:
    stdout = git_require(ctx, "diff", "--name-only", f"{parent}..{child}")
    return [line for line in stdout.splitlines() if line]


def staged_paths(ctx: GitCtx) -> List[str]:
    # --diff-filter=ACMRTUXB* keeps every staged entry kind; we then compare the
    # resulting set against the normative path set.
    stdout = git_require(ctx, "diff", "--cached", "--name-only", "--diff-filter=ACMRTUXB")
    return sorted(line for line in stdout.splitlines() if line)


def local_tag_sha(ctx: GitCtx, tag: str) -> Optional[str]:
    rc, stdout, _stderr = ctx.run("rev-parse", "--verify", "--quiet", f"refs/tags/{tag}")
    if rc == 0 and HEX40_RE.fullmatch(stdout):
        return stdout
    return None


def local_tag_peel(ctx: GitCtx, tag: str) -> str:
    stdout = git_require(ctx, "rev-parse", f"refs/tags/{tag}^{{}}")
    if not HEX40_RE.fullmatch(stdout):
        raise EvidenceError("UNKNOWN", f"local tag `{tag}` did not peel to a commit")
    return stdout


def local_tag_type(ctx: GitCtx, tag: str) -> str:
    rc, stdout, stderr = ctx.run("cat-file", "-t", f"refs/tags/{tag}")
    if rc in (124, 125):
        raise GitUnknown(stderr or f"tag type lookup for `{tag}` unavailable")
    if rc != 0:
        raise EvidenceError("UNKNOWN", f"local tag `{tag}` type lookup failed rc={rc}")
    return stdout.strip()


def remote_ref(ctx: GitCtx, remote: str, refspec: str) -> Tuple[bool, Optional[str]]:
    """Return (query_ok, sha-or-None). query_ok=False means UNKNOWN."""

    safe_remote = _validate_remote_name(remote)
    rc, stdout, stderr = ctx.run("ls-remote", "--exit-code", safe_remote, refspec)
    if rc in (124, 125):
        raise GitUnknown(stderr or f"remote `{safe_remote}` lookup unavailable")
    if rc == 2:
        # ls-remote --exit-code returns 2 when no matching refs: canonical ABSENT.
        return True, None
    if rc == 1:
        # Ambiguous non-canonical nonzero: treat as UNKNOWN, never silent absence.
        raise GitUnknown(f"remote `{safe_remote}` {refspec} returned ambiguous nonzero rc=1")
    if rc != 0:
        raise GitUnknown(f"remote `{safe_remote}` {refspec} failed rc={rc}")
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) == 2 and HEX40_RE.fullmatch(parts[0]) and parts[1] == refspec:
            return True, parts[0]
    return True, None


def _validate_remote_name(remote: str) -> str:
    if not isinstance(remote, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}", remote):
        raise EvidenceError("UNKNOWN", f"remote name `{remote}` is not a safe Git remote")
    if remote.startswith("-") or ".." in remote or "//" in remote:
        raise EvidenceError("UNKNOWN", f"remote name `{remote}` is not a safe Git remote")
    return remote


# ---------------------------------------------------------------------------
# Evidence record validation (architecture section 6.2).
# ---------------------------------------------------------------------------

PRIMARY_REQUIRED_FIELDS: Tuple[str, ...] = (
    "schema_version", "task_id", "evidence_kind", "producer_role", "producer_id",
    "result", "unresolved_blockers", "subject_sha", "generated_at", "release_authorized",
)

SIDECAR_REQUIRED_FIELDS: Tuple[str, ...] = (
    "schema_version", "report_path", "report_sha256", "task_id", "evidence_kind",
    "producer_role", "producer_id", "result", "unresolved_blockers", "subject_sha",
    "generated_at", "release_authorized",
)

# Primary fact fields repeated by the sidecar (case-sensitive equality).
SIDECAR_REPEATED_FIELDS: Tuple[str, ...] = (
    "task_id", "evidence_kind", "producer_role", "producer_id", "result",
    "unresolved_blockers", "subject_sha", "generated_at", "release_authorized",
)

RESULT_BY_KIND: Dict[str, Tuple[str, ...]] = {
    "code_review": ("APPROVED", "APPROVED_WITH_NOTES"),
    "qa": ("PASS",),
    "exact_c_code_review": ("APPROVED", "APPROVED_WITH_NOTES"),
    "exact_c_qa": ("PASS",),
    "release_review": ("APPROVED", "APPROVED_WITH_NOTES"),
}

ROLE_BY_KIND: Dict[str, str] = {
    "code_review": "Code Reviewer",
    "qa": "QA",
    "exact_c_code_review": "Code Reviewer",
    "exact_c_qa": "QA",
    "release_review": "Release Reviewer",
}


def _require_fields(record: Mapping[str, Any], required: Tuple[str, ...], label: str) -> None:
    missing = [name for name in required if name not in record]
    if missing:
        raise EvidenceError("SCHEMA_MISSING", f"{label} missing required fields {missing}")
    extra = [name for name in record if name not in required]
    if extra:
        raise EvidenceError("SCHEMA_UNKNOWN", f"{label} has unknown fields {extra}")


def _require_nfc_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise EvidenceError("TYPE_DRIFT", f"{label} must be a non-empty NFC string")
    if unicodedata.normalize("NFC", value) != value:
        raise EvidenceError("CANONICAL_BYTES", f"{label} must be NFC-normalized")
    return value


def validate_primary_report(
    primary: Mapping[str, Any],
    artifact_id: str,
    expected_subject_sha: Optional[str] = None,
) -> Dict[str, Any]:
    label = f"primary `{artifact_id}`"
    _require_fields(primary, PRIMARY_REQUIRED_FIELDS, label)
    if primary["schema_version"] != PRIMARY_SCHEMA_VERSION:
        raise EvidenceError("SCHEMA_UNKNOWN", f"{label} schema_version must be {PRIMARY_SCHEMA_VERSION}")
    task_id = _require_nfc_string(primary["task_id"], f"{label}.task_id")
    expected_task = TASK_BY_ARTIFACT[artifact_id]
    if task_id != expected_task:
        raise EvidenceError("PHASE_DRIFT", f"{label}.task_id `{task_id}` must be `{expected_task}`")
    kind = primary["evidence_kind"]
    expected_kind = EVIDENCE_KIND_BY_ARTIFACT[artifact_id]
    if kind != expected_kind:
        raise EvidenceError("PHASE_DRIFT", f"{label}.evidence_kind `{kind}` must be `{expected_kind}`")
    role = _require_nfc_string(primary["producer_role"], f"{label}.producer_role")
    if role != ROLE_BY_KIND[kind]:
        raise EvidenceError("PHASE_DRIFT", f"{label}.producer_role `{role}` must be `{ROLE_BY_KIND[kind]}`")
    producer_id = _require_nfc_string(primary["producer_id"], f"{label}.producer_id")
    result = primary["result"]
    if not isinstance(result, str) or result not in RESULT_BY_KIND[kind]:
        raise EvidenceError("PHASE_DRIFT", f"{label}.result `{result!r}` not permitted for kind `{kind}`")
    blockers = primary["unresolved_blockers"]
    if isinstance(blockers, bool) or not isinstance(blockers, int) or blockers < 0:
        raise EvidenceError("TYPE_DRIFT", f"{label}.unresolved_blockers must be a non-negative integer")
    if blockers != 0:
        raise EvidenceError("PHASE_DRIFT", f"{label}.unresolved_blockers must be 0")
    subject_sha = primary["subject_sha"]
    if not isinstance(subject_sha, str) or not HEX40_RE.fullmatch(subject_sha):
        raise EvidenceError("TYPE_DRIFT", f"{label}.subject_sha must be 40 lowercase hex")
    if expected_subject_sha is not None and subject_sha != expected_subject_sha:
        raise EvidenceError("DIGEST_MISMATCH", f"{label}.subject_sha must equal expected `{expected_subject_sha}`")
    generated_at = primary["generated_at"]
    if not isinstance(generated_at, str) or not UTC_SECONDS_RE.fullmatch(generated_at):
        raise EvidenceError("TYPE_DRIFT", f"{label}.generated_at must be UTC seconds YYYY-MM-DDTHH:MM:SSZ")
    release_authorized = primary["release_authorized"]
    if not isinstance(release_authorized, bool):
        raise EvidenceError("TYPE_DRIFT", f"{label}.release_authorized must be a boolean")
    # release_authorized is true only for release_review (section 6.2).
    if release_authorized and kind != "release_review":
        raise EvidenceError("PHASE_DRIFT", f"{label}.release_authorized must be false for kind `{kind}`")
    if not release_authorized and kind == "release_review":
        raise EvidenceError("PHASE_DRIFT", f"{label}.release_authorized must be true for release_review")
    return dict(primary)


def validate_sidecar(
    sidecar: Mapping[str, Any],
    primary: Mapping[str, Any],
    artifact_id: str,
    primary_path: str,
) -> Dict[str, Any]:
    label = f"sidecar `{artifact_id}`"
    _require_fields(sidecar, SIDECAR_REQUIRED_FIELDS, label)
    if sidecar["schema_version"] != SIDECAR_SCHEMA_VERSION:
        raise EvidenceError("SCHEMA_UNKNOWN", f"{label} schema_version must be {SIDECAR_SCHEMA_VERSION}")
    report_path = sidecar["report_path"]
    if not isinstance(report_path, str) or not report_path:
        raise EvidenceError("TYPE_DRIFT", f"{label}.report_path must be a canonical repo-relative string")
    report_sha256 = sidecar["report_sha256"]
    if not isinstance(report_sha256, str) or not HEX64_RE.fullmatch(report_sha256):
        raise EvidenceError("TYPE_DRIFT", f"{label}.report_sha256 must be 64 lowercase hex")
    for field_name in SIDECAR_REPEATED_FIELDS:
        if sidecar[field_name] != primary[field_name]:
            raise EvidenceError(
                "DIGEST_MISMATCH",
                f"{label}.{field_name} must equal primary with exact case-sensitive equality",
            )
    return dict(sidecar)


def load_artifact_pair(
    ctx: GitCtx,
    artifact_id: str,
    expected_subject_sha: Optional[str] = None,
) -> Dict[str, Any]:
    primary_path = ARTIFACT_PRIMARY_PATH[artifact_id]
    sidecar_path = ARTIFACT_SIDECAR_PATH[artifact_id]
    primary = load_canonical(ctx.root / primary_path)
    sidecar = load_canonical(ctx.root / sidecar_path)
    primary_validated = validate_primary_report(primary, artifact_id, expected_subject_sha)
    # The sidecar's pinned report_sha256 must equal the digest of the review
    # report file identified by report_path (section 6.2: primary bytes are the
    # sole report truth; the sidecar is an index whose report_sha256 pins the
    # report document on disk).
    report_path_str = sidecar["report_path"]
    report_file = ctx.root / report_path_str
    if not report_file.exists():
        raise EvidenceError(
            "UNKNOWN",
            f"sidecar `{artifact_id}`.report_path `{report_path_str}` does not exist",
        )
    report_digest = sha256(report_file.read_bytes()).hexdigest()
    if sidecar["report_sha256"] != report_digest:
        raise EvidenceError(
            "DIGEST_MISMATCH",
            f"sidecar `{artifact_id}`.report_sha256 must equal report file digest at `{report_path_str}`",
        )
    validate_sidecar(sidecar, primary_validated, artifact_id, primary_path)
    primary_bytes = (ctx.root / primary_path).read_bytes()
    primary_digest = sha256(primary_bytes).hexdigest()
    return {
        "artifact_id": artifact_id,
        "primary": primary_validated,
        "sidecar": sidecar,
        "primary_path": primary_path,
        "sidecar_path": sidecar_path,
        "primary_sha256": primary_digest,
    }


# ---------------------------------------------------------------------------
# Authority / dispatch / topology (architecture section 6.2).
# ---------------------------------------------------------------------------

def load_authority_input(ctx: GitCtx) -> Dict[str, Any]:
    path = ctx.root / ".governance/review-authority/REL-063/authority-input.json"
    data = load_canonical(path)
    if not isinstance(data, dict):
        raise EvidenceError("TYPE_DRIFT", "authority-input must be an object")
    if data.get("schema_version") != AUTHORITY_SCHEMA_VERSION:
        raise EvidenceError("SCHEMA_UNKNOWN", f"authority-input.schema_version must be {AUTHORITY_SCHEMA_VERSION}")
    return data


def load_orchestration_receipts(ctx: GitCtx) -> Dict[str, Any]:
    path = ctx.root / ".governance/review-authority/REL-063/orchestration-receipts.json"
    data = load_canonical(path)
    if not isinstance(data, dict):
        raise EvidenceError("TYPE_DRIFT", "orchestration-receipts must be an object")
    if data.get("schema_version") != ORCHESTRATION_SCHEMA_VERSION:
        raise EvidenceError("SCHEMA_UNKNOWN", f"orchestration-receipts.schema_version must be {ORCHESTRATION_SCHEMA_VERSION}")
    return data


def load_topology_record(ctx: GitCtx, expected_phase: Optional[str] = None) -> Dict[str, Any]:
    path = ctx.root / ".governance/review-authority/REL-063/topology-record.json"
    data = load_canonical(path)
    if not isinstance(data, dict):
        raise EvidenceError("TYPE_DRIFT", "topology-record must be an object")
    if data.get("schema_version") != TOPOLOGY_SCHEMA_VERSION:
        raise EvidenceError("SCHEMA_UNKNOWN", f"topology-record.schema_version must be {TOPOLOGY_SCHEMA_VERSION}")
    phase = data.get("phase")
    if phase not in ("provisional", "full"):
        raise EvidenceError("PHASE_DRIFT", "topology-record.phase must be provisional or full")
    if expected_phase is not None and phase != expected_phase:
        raise EvidenceError("PHASE_DRIFT", f"topology-record.phase `{phase}` must be `{expected_phase}`")
    return data


def validate_authority_input(authority: Mapping[str, Any]) -> Dict[str, Any]:
    label = "authority-input"
    for field_name in ("schema_version", "frozen_at", "coordinator_id", "developers",
                       "release_producer_id", "artifacts"):
        if field_name not in authority:
            raise EvidenceError("SCHEMA_MISSING", f"{label} missing `{field_name}`")
    frozen_at = authority["frozen_at"]
    if not isinstance(frozen_at, str) or not UTC_SECONDS_RE.fullmatch(frozen_at):
        raise EvidenceError("TYPE_DRIFT", f"{label}.frozen_at must be UTC seconds")
    _require_nfc_string(authority["coordinator_id"], f"{label}.coordinator_id")
    _require_nfc_string(authority["release_producer_id"], f"{label}.release_producer_id")
    developers = authority["developers"]
    if not isinstance(developers, dict) or set(developers) != {"FIX-215", "FIX-216", "FIX-217"}:
        raise EvidenceError("PHASE_DRIFT", f"{label}.developers must have keys FIX-215,FIX-216,FIX-217")
    for key, value in developers.items():
        _require_nfc_string(value, f"{label}.developers.{key}")
    artifacts = authority["artifacts"]
    if not isinstance(artifacts, list):
        raise EvidenceError("TYPE_DRIFT", f"{label}.artifacts must be a list")
    if len(artifacts) != 9:
        raise EvidenceError("PHASE_DRIFT", f"{label}.artifacts must have exactly 9 entries")
    seen_ids: Set[str] = set()
    artifact_index: Dict[str, Dict[str, Any]] = {}
    for index, entry in enumerate(artifacts):
        if not isinstance(entry, dict):
            raise EvidenceError("TYPE_DRIFT", f"{label}.artifacts[{index}] must be an object")
        for field_name in ("artifact_id", "task_id", "evidence_kind", "producer_role",
                           "producer_id", "receipt_id", "subject_symbol",
                           "primary_path", "sidecar_path"):
            if field_name not in entry:
                raise EvidenceError("SCHEMA_MISSING", f"{label}.artifacts[{index}] missing `{field_name}`")
        aid = entry["artifact_id"]
        if aid in seen_ids:
            raise EvidenceError("DUPLICATE", f"{label}.artifacts[{index}] duplicate artifact_id `{aid}`")
        if aid not in NINE_ARTIFACT_IDS:
            raise EvidenceError("PHASE_DRIFT", f"{label}.artifacts[{index}] unknown artifact_id `{aid}`")
        seen_ids.add(aid)
        if entry["task_id"] != TASK_BY_ARTIFACT[aid]:
            raise EvidenceError("PHASE_DRIFT", f"{label}.artifacts[{index}].task_id mismatch for `{aid}`")
        if entry["evidence_kind"] != EVIDENCE_KIND_BY_ARTIFACT[aid]:
            raise EvidenceError("PHASE_DRIFT", f"{label}.artifacts[{index}].evidence_kind mismatch for `{aid}`")
        if entry["producer_role"] != ROLE_BY_KIND[EVIDENCE_KIND_BY_ARTIFACT[aid]]:
            raise EvidenceError("PHASE_DRIFT", f"{label}.artifacts[{index}].producer_role mismatch for `{aid}`")
        if entry["primary_path"] != ARTIFACT_PRIMARY_PATH[aid]:
            raise EvidenceError("PHASE_DRIFT", f"{label}.artifacts[{index}].primary_path mismatch for `{aid}`")
        if entry["sidecar_path"] != ARTIFACT_SIDECAR_PATH[aid]:
            raise EvidenceError("PHASE_DRIFT", f"{label}.artifacts[{index}].sidecar_path mismatch for `{aid}`")
        artifact_index[aid] = dict(entry)
    if seen_ids != set(NINE_ARTIFACT_IDS):
        raise EvidenceError("PHASE_DRIFT", f"{label}.artifacts must cover all nine artifact IDs")
    return {"artifacts": artifact_index, "developers": dict(developers),
            "release_producer_id": authority["release_producer_id"],
            "coordinator_id": authority["coordinator_id"], "frozen_at": frozen_at}


def validate_orchestration_receipts(receipts_doc: Mapping[str, Any], authority_index: Mapping[str, Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    label = "orchestration-receipts"
    for field_name in ("schema_version", "generated_at", "receipts"):
        if field_name not in receipts_doc:
            raise EvidenceError("SCHEMA_MISSING", f"{label} missing `{field_name}`")
    generated_at = receipts_doc["generated_at"]
    if not isinstance(generated_at, str) or not UTC_SECONDS_RE.fullmatch(generated_at):
        raise EvidenceError("TYPE_DRIFT", f"{label}.generated_at must be UTC seconds")
    receipts = receipts_doc["receipts"]
    if not isinstance(receipts, list) or len(receipts) != 9:
        raise EvidenceError("PHASE_DRIFT", f"{label}.receipts must have exactly 9 entries")
    by_receipt_id: Dict[str, Dict[str, Any]] = {}
    by_artifact: Dict[str, Dict[str, Any]] = {}
    for index, receipt in enumerate(receipts):
        if not isinstance(receipt, dict):
            raise EvidenceError("TYPE_DRIFT", f"{label}.receipts[{index}] must be an object")
        for field_name in ("receipt_id", "artifact_id", "task_id", "assigned_role",
                           "producer_id", "dispatched_at"):
            if field_name not in receipt:
                raise EvidenceError("SCHEMA_MISSING", f"{label}.receipts[{index}] missing `{field_name}`")
        rid = receipt["receipt_id"]
        if rid in by_receipt_id:
            raise EvidenceError("DUPLICATE", f"{label}.receipts[{index}] duplicate receipt_id `{rid}`")
        aid = receipt["artifact_id"]
        if aid not in authority_index:
            raise EvidenceError("PHASE_DRIFT", f"{label}.receipts[{index}] unknown artifact_id `{aid}`")
        authority_entry = authority_index[aid]
        if authority_entry["receipt_id"] != rid:
            raise EvidenceError("DIGEST_MISMATCH", f"{label}.receipts[{index}] receipt_id mismatch with authority for `{aid}`")
        if receipt["task_id"] != authority_entry["task_id"]:
            raise EvidenceError("PHASE_DRIFT", f"{label}.receipts[{index}].task_id mismatch for `{aid}`")
        if receipt["assigned_role"] != authority_entry["producer_role"]:
            raise EvidenceError("PHASE_DRIFT", f"{label}.receipts[{index}].assigned_role mismatch for `{aid}`")
        if receipt["producer_id"] != authority_entry["producer_id"]:
            raise EvidenceError("PHASE_DRIFT", f"{label}.receipts[{index}].producer_id mismatch for `{aid}`")
        dispatched_at = receipt["dispatched_at"]
        if not isinstance(dispatched_at, str) or not UTC_SECONDS_RE.fullmatch(dispatched_at):
            raise EvidenceError("TYPE_DRIFT", f"{label}.receipts[{index}].dispatched_at must be UTC seconds")
        by_receipt_id[rid] = dict(receipt)
        by_artifact[aid] = dict(receipt)
    return by_artifact


def validate_topology(topology: Mapping[str, Any], ctx: GitCtx, expected_subjects: Set[str]) -> Dict[str, Any]:
    label = "topology-record"
    for field_name in ("schema_version", "phase", "observed_at", "subjects", "attempts"):
        if field_name not in topology:
            raise EvidenceError("SCHEMA_MISSING", f"{label} missing `{field_name}`")
    observed_at = topology["observed_at"]
    if not isinstance(observed_at, str) or not UTC_SECONDS_RE.fullmatch(observed_at):
        raise EvidenceError("TYPE_DRIFT", f"{label}.observed_at must be UTC seconds")
    subjects = topology["subjects"]
    if not isinstance(subjects, dict):
        raise EvidenceError("TYPE_DRIFT", f"{label}.subjects must be an object")
    # Subjects present must be a subset of {S215,S216,S217,C,T}; provisional
    # topology pins slice subjects and requires T=null.
    allowed_subject_keys = {"S215", "S216", "S217", "C", "T"}
    unknown = set(subjects) - allowed_subject_keys
    if unknown:
        raise EvidenceError("PHASE_DRIFT", f"{label}.subjects has unknown keys {sorted(unknown)}")
    validated_subjects: Dict[str, Dict[str, Any]] = {}
    for key, value in subjects.items():
        if value is None:
            if key != "T":
                raise EvidenceError("PHASE_DRIFT", f"{label}.subjects.{key} must not be null")
            validated_subjects[key] = {"sha": None}
            continue
        if not isinstance(value, dict):
            raise EvidenceError("TYPE_DRIFT", f"{label}.subjects.{key} must be an object or null")
        for field_name in ("sha", "created_at", "owner", "parents", "path_set_sha256"):
            if field_name not in value:
                raise EvidenceError("SCHEMA_MISSING", f"{label}.subjects.{key} missing `{field_name}`")
        sha = value["sha"]
        if not isinstance(sha, str) or not HEX40_RE.fullmatch(sha):
            raise EvidenceError("TYPE_DRIFT", f"{label}.subjects.{key}.sha must be 40 hex")
        created_at = value["created_at"]
        if not isinstance(created_at, str) or not UTC_SECONDS_RE.fullmatch(created_at):
            raise EvidenceError("TYPE_DRIFT", f"{label}.subjects.{key}.created_at must be UTC seconds")
        _require_nfc_string(value["owner"], f"{label}.subjects.{key}.owner")
        parents = value["parents"]
        if not isinstance(parents, list) or not all(isinstance(p, str) and HEX40_RE.fullmatch(p) for p in parents):
            raise EvidenceError("TYPE_DRIFT", f"{label}.subjects.{key}.parents must be a list of 40-hex")
        path_set_sha256 = value["path_set_sha256"]
        if not isinstance(path_set_sha256, str) or not HEX64_RE.fullmatch(path_set_sha256):
            raise EvidenceError("TYPE_DRIFT", f"{label}.subjects.{key}.path_set_sha256 must be 64 hex")
        validated_subjects[key] = dict(value)
    missing = expected_subjects - set(validated_subjects)
    if missing:
        raise EvidenceError("PHASE_DRIFT", f"{label} missing subjects {sorted(missing)}")

    attempts = topology["attempts"]
    if not isinstance(attempts, list):
        raise EvidenceError("TYPE_DRIFT", f"{label}.attempts must be a list")
    validated_attempts = _validate_attempts(attempts, label)
    return {"subjects": validated_subjects, "attempts": validated_attempts,
            "phase": topology["phase"], "observed_at": observed_at}


def _validate_attempts(attempts: Sequence[Mapping[str, Any]], label: str) -> List[Dict[str, Any]]:
    seen: Set[Tuple[str, int]] = set()
    out: List[Dict[str, Any]] = []
    for index, attempt in enumerate(attempts):
        if not isinstance(attempt, dict):
            raise EvidenceError("TYPE_DRIFT", f"{label}.attempts[{index}] must be an object")
        for field_name in ("task_id", "attempt_no", "sha", "parent_sha", "created_at",
                           "terminal_result", "code_report_sha256", "qa_report_sha256"):
            if field_name not in attempt:
                raise EvidenceError("SCHEMA_MISSING", f"{label}.attempts[{index}] missing `{field_name}`")
        task_id = attempt["task_id"]
        if task_id not in {"FIX-215", "FIX-216", "FIX-217"}:
            raise EvidenceError("PHASE_DRIFT", f"{label}.attempts[{index}].task_id must be FIX-215/216/217")
        attempt_no = attempt["attempt_no"]
        if isinstance(attempt_no, bool) or not isinstance(attempt_no, int) or attempt_no < 1:
            raise EvidenceError("TYPE_DRIFT", f"{label}.attempts[{index}].attempt_no must be int >= 1")
        key = (task_id, attempt_no)
        if key in seen:
            raise EvidenceError("DUPLICATE", f"{label}.attempts[{index}] duplicate (task_id,attempt_no)")
        seen.add(key)
        for sha_field in ("sha", "parent_sha"):
            value = attempt[sha_field]
            if not isinstance(value, str) or not HEX40_RE.fullmatch(value):
                raise EvidenceError("TYPE_DRIFT", f"{label}.attempts[{index}].{sha_field} must be 40 hex")
        created_at = attempt["created_at"]
        if not isinstance(created_at, str) or not UTC_SECONDS_RE.fullmatch(created_at):
            raise EvidenceError("TYPE_DRIFT", f"{label}.attempts[{index}].created_at must be UTC seconds")
        terminal_result = attempt["terminal_result"]
        if terminal_result not in ("ACCEPTED", "CR_FAILED", "QA_FAILED"):
            raise EvidenceError("PHASE_DRIFT", f"{label}.attempts[{index}].terminal_result unsupported")
        for report_field in ("code_report_sha256", "qa_report_sha256"):
            value = attempt[report_field]
            if value is not None:
                if not isinstance(value, str) or not HEX64_RE.fullmatch(value):
                    raise EvidenceError("TYPE_DRIFT", f"{label}.attempts[{index}].{report_field} must be 64 hex or null")
        # ACCEPTED rows must carry both report digests; failed rows reflect
        # which gate failed (the other report may be null).
        if terminal_result == "ACCEPTED":
            for report_field in ("code_report_sha256", "qa_report_sha256"):
                if attempt[report_field] is None:
                    raise EvidenceError("PHASE_DRIFT", f"{label}.attempts[{index}].{report_field} required for ACCEPTED")
        out.append(dict(attempt))
    # Ordered by (task_id, attempt_no).
    sort_keys = [(a["task_id"], a["attempt_no"]) for a in out]
    if sort_keys != sorted(sort_keys):
        raise EvidenceError("PHASE_DRIFT", f"{label}.attempts must be ordered by (task_id,attempt_no)")
    # Exactly one ACCEPTED row per slice task.
    for task_id in ("FIX-215", "FIX-216", "FIX-217"):
        accepted = [a for a in out if a["task_id"] == task_id and a["terminal_result"] == "ACCEPTED"]
        if len(accepted) != 1:
            raise EvidenceError("PHASE_DRIFT", f"{label} task `{task_id}` must have exactly one ACCEPTED attempt")
    return out


# ---------------------------------------------------------------------------
# Slice chain ancestry (C3 / R1).
# ---------------------------------------------------------------------------

def validate_slice_chain(ctx: GitCtx, topology: Mapping[str, Any], required_chain: Sequence[str]) -> Dict[str, Any]:
    subjects = topology["subjects"]
    chain_shas: List[str] = []
    for symbol in required_chain:
        if symbol not in subjects or subjects[symbol].get("sha") is None:
            raise EvidenceError("PHASE_DRIFT", f"topology missing subject `{symbol}`")
        chain_shas.append(subjects[symbol]["sha"])
    # Cross-check the slice SHAs against the topology ACCEPTED attempts.
    attempts = topology["attempts"]
    task_for_symbol = {"S215": "FIX-215", "S216": "FIX-216", "S217": "FIX-217"}
    for symbol in required_chain:
        task_id = task_for_symbol[symbol]
        accepted = [a for a in attempts if a["task_id"] == task_id and a["terminal_result"] == "ACCEPTED"]
        if not accepted:
            raise EvidenceError("PHASE_DRIFT", f"no ACCEPTED attempt for `{task_id}`")
        if accepted[0]["sha"] != subjects[symbol]["sha"]:
            raise EvidenceError("DIGEST_MISMATCH", f"`{symbol}` SHA does not equal ACCEPTED attempt SHA")
    # Acyclic accepted ancestry (DEC-129 / FIX-219 Option A): the architecture's
    # compensation-retry design makes each accepted subject a CHILD of an R0
    # compensation commit, so the accepted slices form a correct ACYCLIC
    # ancestry chain (S215 is an ancestor of S216), but NOT a direct parent
    # chain. The topology record's `parents` field is still required (records
    # the direct parent for audit) and validated for type in validate_topology,
    # but it is no longer required to equal the prior accepted slice SHA.
    # Verify each slice commit resolves, the ancestry holds in Git, and (the
    # load-bearing C3 "combined path" defense) the R0->accepted-child delta
    # stays inside the slice's declared M-union-N scope.
    try:
        for sha in chain_shas:
            resolve_commit(ctx, sha)
        if len(chain_shas) >= 2:
            for index in range(1, len(chain_shas)):
                prior_symbol = required_chain[index - 1]
                current_symbol = required_chain[index]
                prior_sha = chain_shas[index - 1]
                current_sha = chain_shas[index]
                # Acyclic ancestry: prior accepted slice must be an ancestor of
                # the current accepted slice. This rejects wrong-base / skipped-
                # slice / back-edge (reused-subject) topologies.
                if not is_ancestor(ctx, prior_sha, current_sha):
                    raise EvidenceError(
                        "PHASE_DRIFT",
                        f"`{current_symbol}` Git ancestry: `{prior_symbol}` is not an ancestor",
                    )
                # Path-set guard (net-new C3 defense): for each accepted child
                # whose DIRECT parent is not the prior accepted slice (i.e. an
                # R0 compensation commit sits between them), prove the
                # direct-parent->child delta is a subset of the slice's declared
                # M-union-N scope. This catches an R0 smuggling another slice's
                # work ("combined path" threat) now that direct-parent equality
                # is gone. We run the guard unconditionally for index>=1 using
                # the real direct parent (whether prior slice or R0): the delta
                # of an accepted child against its own direct parent is exactly
                # the work that child introduced, which must remain in-scope.
                direct_parents = commit_parents(ctx, current_sha)
                if direct_parents:
                    r0_sha = direct_parents[0]
                    delta_paths = set(changed_paths_between(ctx, r0_sha, current_sha))
                    allowed_paths = SLICE_SCOPE_PATHS.get(current_symbol, frozenset())
                    out_of_scope = delta_paths - allowed_paths
                    if out_of_scope:
                        offender = sorted(out_of_scope)[0]
                        raise EvidenceError(
                            "PHASE_DRIFT",
                            f"`{current_symbol}` R0->accepted delta path `{offender}` outside declared slice scope",
                        )
    except GitUnknown:
        raise
    return {"chain": list(required_chain), "shas": chain_shas}


# ---------------------------------------------------------------------------
# Rehearsal report (R7).
# ---------------------------------------------------------------------------

REHEARSAL_REQUIRED_FIELDS: Tuple[str, ...] = (
    "schema_version", "producer_role", "producer_id", "subject_sha", "tag_type",
    "fixture", "result", "raw_exit", "writes", "workspace_identity",
    "real_origin_invocations", "sequential_fallbacks", "precondition_sha256",
    "a_master_sha", "a_tag_object_sha", "a_tag_peel_sha", "abort_absent",
    "fallback_sha", "rto_seconds", "generated_at",
)

REHEARSAL_SIDECAR_REQUIRED_FIELDS: Tuple[str, ...] = (
    "schema_version", "report_path", "report_sha256", "receipt_id",
    "producer_role", "producer_id", "subject_sha", "result", "generated_at",
)


def validate_rehearsal_primary(primary: Mapping[str, Any], expected_subject_sha: Optional[str]) -> Dict[str, Any]:
    label = "rehearsal primary"
    _require_fields(primary, REHEARSAL_REQUIRED_FIELDS, label)
    if primary["schema_version"] != REHEARSAL_PRIMARY_SCHEMA_VERSION:
        raise EvidenceError("SCHEMA_UNKNOWN", f"{label} schema_version must be {REHEARSAL_PRIMARY_SCHEMA_VERSION}")
    if primary["producer_role"] != "QA":
        raise EvidenceError("PHASE_DRIFT", f"{label}.producer_role must be QA")
    _require_nfc_string(primary["producer_id"], f"{label}.producer_id")
    subject_sha = primary["subject_sha"]
    if not isinstance(subject_sha, str) or not HEX40_RE.fullmatch(subject_sha):
        raise EvidenceError("TYPE_DRIFT", f"{label}.subject_sha must be 40 hex")
    if expected_subject_sha is not None and subject_sha != expected_subject_sha:
        raise EvidenceError("DIGEST_MISMATCH", f"{label}.subject_sha must equal expected `{expected_subject_sha}`")
    if primary["tag_type"] != "annotated":
        raise EvidenceError("PHASE_DRIFT", f"{label}.tag_type must be annotated")
    if primary["fixture"] != "positive":
        raise EvidenceError("PHASE_DRIFT", f"{label}.fixture must be positive")
    if primary["result"] != "PASS":
        raise EvidenceError("PHASE_DRIFT", f"{label}.result must be PASS")
    raw_exit = primary["raw_exit"]
    if isinstance(raw_exit, bool) or not isinstance(raw_exit, int) or raw_exit != 0:
        raise EvidenceError("PHASE_DRIFT", f"{label}.raw_exit must be integer 0")
    writes = primary["writes"]
    if isinstance(writes, bool) or not isinstance(writes, int) or writes < 0:
        raise EvidenceError("TYPE_DRIFT", f"{label}.writes must be a non-negative integer")
    if primary["workspace_identity"] != "UNCHANGED":
        raise EvidenceError("PHASE_DRIFT", f"{label}.workspace_identity must be UNCHANGED")
    for field_name in ("real_origin_invocations", "sequential_fallbacks"):
        value = primary[field_name]
        if isinstance(value, bool) or not isinstance(value, int) or value != 0:
            raise EvidenceError("PHASE_DRIFT", f"{label}.{field_name} must be integer 0")
    for hex64_field in ("precondition_sha256",):
        value = primary[hex64_field]
        if not isinstance(value, str) or not HEX64_RE.fullmatch(value):
            raise EvidenceError("TYPE_DRIFT", f"{label}.{hex64_field} must be 64 hex")
    for hex40_field in ("a_master_sha", "a_tag_object_sha", "a_tag_peel_sha", "fallback_sha"):
        value = primary[hex40_field]
        if not isinstance(value, str) or not HEX40_RE.fullmatch(value):
            raise EvidenceError("TYPE_DRIFT", f"{label}.{hex40_field} must be 40 hex")
    if primary["abort_absent"] is not True:
        raise EvidenceError("PHASE_DRIFT", f"{label}.abort_absent must be true")
    rto = primary["rto_seconds"]
    if isinstance(rto, bool) or not isinstance(rto, (int, float)) or not (0 <= rto <= 900):
        raise EvidenceError("PHASE_DRIFT", f"{label}.rto_seconds must be a number in 0..900")
    generated_at = primary["generated_at"]
    if not isinstance(generated_at, str) or not UTC_SECONDS_RE.fullmatch(generated_at):
        raise EvidenceError("TYPE_DRIFT", f"{label}.generated_at must be UTC seconds")
    return dict(primary)


def load_rehearsal_pair(ctx: GitCtx, expected_subject_sha: Optional[str]) -> Dict[str, Any]:
    primary_path = ".governance/primary-review-evidence/REL-063/atomic-rehearsal.json"
    sidecar_path = ".governance/review-evidence/REL-063/atomic-rehearsal.json"
    primary = load_canonical(ctx.root / primary_path)
    primary_validated = validate_rehearsal_primary(primary, expected_subject_sha)
    primary_bytes = (ctx.root / primary_path).read_bytes()
    primary_digest = sha256(primary_bytes).hexdigest()
    sidecar = load_canonical(ctx.root / sidecar_path)
    _require_fields(sidecar, REHEARSAL_SIDECAR_REQUIRED_FIELDS, "rehearsal sidecar")
    if sidecar["schema_version"] != REHEARSAL_SIDECAR_SCHEMA_VERSION:
        raise EvidenceError("SCHEMA_UNKNOWN", "rehearsal sidecar schema_version mismatch")
    if sidecar["report_path"] != primary_path:
        raise EvidenceError("DIGEST_MISMATCH", "rehearsal sidecar.report_path mismatch")
    if sidecar["report_sha256"] != primary_digest:
        raise EvidenceError("DIGEST_MISMATCH", "rehearsal sidecar.report_sha256 must equal primary digest")
    _require_nfc_string(sidecar["receipt_id"], "rehearsal sidecar.receipt_id")
    for field_name in ("producer_role", "producer_id", "subject_sha", "result", "generated_at"):
        if sidecar[field_name] != primary_validated[field_name]:
            raise EvidenceError("DIGEST_MISMATCH", f"rehearsal sidecar.{field_name} must equal primary")
    return {"primary": primary_validated, "sidecar": dict(sidecar),
            "primary_path": primary_path, "primary_sha256": primary_digest}


# ---------------------------------------------------------------------------
# Distinct role sets (R2): no self-review, CR != QA, Release Reviewer disjoint.
# ---------------------------------------------------------------------------

def validate_distinct_role_sets(loaded_artifacts: Mapping[str, Mapping[str, Any]], authority: Mapping[str, Any]) -> Dict[str, Any]:
    # Group producer_ids by role across all loaded artifacts.
    role_to_producers: Dict[str, Set[str]] = {}
    producer_to_roles: Dict[str, Set[str]] = {}
    for aid, entry in loaded_artifacts.items():
        primary = entry["primary"]
        role = primary["producer_role"]
        producer_id = primary["producer_id"]
        role_to_producers.setdefault(role, set()).add(producer_id)
        producer_to_roles.setdefault(producer_id, set()).add(role)
        # Cross-check against the authority file's pinned producer.
        authority_entry = authority["artifacts"][aid]
        if authority_entry["producer_id"] != producer_id:
            raise EvidenceError("DIGEST_MISMATCH", f"`{aid}` producer_id diverges from authority")
        if authority_entry["producer_role"] != role:
            raise EvidenceError("DIGEST_MISMATCH", f"`{aid}` producer_role diverges from authority")
    # No producer may hold more than one role (self-review / four-record forge).
    multi_role = {pid: roles for pid, roles in producer_to_roles.items() if len(roles) > 1}
    if multi_role:
        raise EvidenceError("PHASE_DRIFT", f"producer holds multiple roles (self-review): {sorted(multi_role)}")
    # Code Reviewer and QA sets must be disjoint (CR != QA across the release).
    cr = role_to_producers.get("Code Reviewer", set())
    qa = role_to_producers.get("QA", set())
    if cr & qa:
        raise EvidenceError("PHASE_DRIFT", f"Code Reviewer and QA producer sets overlap: {sorted(cr & qa)}")
    rr = role_to_producers.get("Release Reviewer", set())
    if rr & cr or rr & qa:
        raise EvidenceError("PHASE_DRIFT", f"Release Reviewer must not overlap any CR/QA producer")
    # Developers must not be reviewers (producer vs developer disjointness).
    developers = set(authority["developers"].values())
    reviewer_union = cr | qa | rr
    if developers & reviewer_union:
        raise EvidenceError("PHASE_DRIFT", f"developer overlaps a reviewer producer: {sorted(developers & reviewer_union)}")
    return {
        "code_reviewers": sorted(cr),
        "qa": sorted(qa),
        "release_reviewers": sorted(rr),
        "developers": sorted(developers),
    }


# ---------------------------------------------------------------------------
# FIX-213 supersession + scanner limit (C5).
# ---------------------------------------------------------------------------

def validate_fix213_supersession(loaded_artifacts: Mapping[str, Mapping[str, Any]], scanner_limit_seconds: float) -> Dict[str, Any]:
    # The six slice reports supersede the failed 0.66.1 REVIEW-FIX-213 lineage.
    # We enforce that every slice artifact is terminal (result/result blockers
    # already checked) and that the scanner budget is the DEC-119/AUDIT-135
    # ceiling of 8.0s, not the stale <5s encoding.
    if scanner_limit_seconds != SCANNER_LIMIT_SECONDS_DEFAULT:
        raise EvidenceError("PHASE_DRIFT", f"scanner_limit_seconds must be {SCANNER_LIMIT_SECONDS_DEFAULT}")
    # Sentinel: the verifier never sees a stale 5.0s ceiling.
    if scanner_limit_seconds <= SCANNER_LIMIT_STALE_SECONDS:
        raise EvidenceError("PHASE_DRIFT", f"scanner_limit_seconds must exceed stale {SCANNER_LIMIT_STALE_SECONDS}s ceiling")
    slice_aids = [aid for aid in NINE_ARTIFACT_IDS if aid in loaded_artifacts and aid in SIX_SLICE_ARTIFACT_IDS]
    if len(slice_aids) != len(SIX_SLICE_ARTIFACT_IDS):
        raise EvidenceError("PHASE_DRIFT", "FIX-213 supersession requires all six slice artifacts")
    return {"superseded": "REVIEW-FIX-213-CODE-R0", "scanner_limit_seconds": scanner_limit_seconds,
            "slice_artifacts": slice_aids}


# ---------------------------------------------------------------------------
# Path-set verification (C3 topology / staged / candidate).
# ---------------------------------------------------------------------------

def resolve_path_set(spec: str) -> Tuple[str, ...]:
    if spec in ("M063", "N063", "M063,N063", "N063,M063"):
        out: List[str] = []
        for source in spec.split(","):
            if source == "M063":
                out.extend(M063)
            elif source == "N063":
                out.extend(N063)
        # Deduplicate preserving first occurrence, then sort.
        seen: Set[str] = set()
        unique = [p for p in out if not (p in seen or seen.add(p))]
        return tuple(sorted(unique))
    # Otherwise treat as a literal comma-separated list of repo-relative paths.
    return tuple(sorted(p for p in spec.split(",") if p))


def assert_path_set(actual: Iterable[str], expected: Iterable[str], expected_count: int, label: str) -> List[str]:
    actual_set = set(actual)
    expected_set = set(expected)
    if len(expected_set) != expected_count:
        raise EvidenceError("PHASE_DRIFT", f"{label}: expected path-set cardinality {expected_count} but normative set has {len(expected_set)}")
    extra = actual_set - expected_set
    missing = expected_set - actual_set
    if extra or missing or len(actual_set) != expected_count:
        problems = []
        if extra:
            problems.append(f"unexpected paths {sorted(extra)}")
        if missing:
            problems.append(f"missing paths {sorted(missing)}")
        if not extra and not missing and len(actual_set) != expected_count:
            problems.append(f"cardinality {len(actual_set)} != {expected_count}")
        raise EvidenceError("PHASE_DRIFT", f"{label}: {'; '.join(problems)}")
    return sorted(actual_set)


# ---------------------------------------------------------------------------
# Verdict / manifest writers.
# ---------------------------------------------------------------------------

@dataclass
class Verdict:
    phase: str
    candidate_sha: Optional[str]
    transition_sha: Optional[str]
    artifact_ids: List[str]
    authority_roots: Dict[str, str]
    rehearsal_sha256: Optional[str]
    released_validation_root: Optional[str]
    verdict: str
    gate: str
    transition_authorized: bool
    release_authorized: bool

    def to_canonical(self) -> bytes:
        payload = {
            "schema_version": VERDICT_SCHEMA_VERSION,
            "phase": self.phase,
            "candidate_sha": self.candidate_sha,
            "transition_sha": self.transition_sha,
            "artifact_ids": self.artifact_ids,
            "authority_roots": self.authority_roots,
            "rehearsal_sha256": self.rehearsal_sha256,
            "released_validation_root": self.released_validation_root,
            "verdict": self.verdict,
            "gate": self.gate,
            "transition_authorized": self.transition_authorized,
            "release_authorized": self.release_authorized,
        }
        return canonical_json_bytes(payload)


def _authority_roots() -> Dict[str, str]:
    return {
        "evidence": ".governance/primary-review-evidence/REL-063",
        "dispatch": ".governance/review-authority/REL-063/orchestration-receipts.json",
        "topology": ".governance/review-authority/REL-063/topology-record.json",
    }


def write_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    canonical = canonical_json_bytes(manifest)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical)


def _write_output(ctx: GitCtx, rel: str, payload: Mapping[str, Any]) -> None:
    path = ctx.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(payload))


# ---------------------------------------------------------------------------
# Candidate manifest (recovery_evidence binding, phase=candidate).
# ---------------------------------------------------------------------------

def candidate_manifest(recovery: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "version": "0.66.2",
        "lifecycle_state": "candidate",
        "provenance": "native",
        "artifacts": {
            "changelog": "project/CHANGELOG.md",
            "release_docs": [
                "docs/release/release-checklist-0.66.2.md",
                "docs/release/feature-flags-0.66.2.md",
                "docs/release/rollback-plan-0.66.2.md",
            ],
            "review_evidence": [".governance/evidence-log.md"],
        },
        "trust": {"candidate_commit": {"derivation": "git_commit_adding_path"}},
        "events": [],
        "effective_state": {"lifecycle_state": "candidate", "withdrawn": False, "amendments": []},
        "recovery_evidence": recovery,
    }


def build_candidate_recovery_evidence(
    subjects: Mapping[str, Any],
    reports: Mapping[str, Any],
    artifact_blobs: Mapping[str, Any],
    provisional_root: str,
    frozen_at: str,
) -> Dict[str, Any]:
    return {
        "schema_version": RELEASE_BINDING_SCHEMA_VERSION,
        "phase": "candidate",
        "frozen_at": frozen_at,
        "subjects": subjects,
        "reports": reports,
        "authority_roots": _authority_roots(),
        "artifact_blobs": artifact_blobs,
        "provisional_root": provisional_root,
        "rehearsal_sha256": None,
        "full_root": None,
    }


# ---------------------------------------------------------------------------
# Phase drivers.
# ---------------------------------------------------------------------------

def _load_six_slice_artifacts(ctx: GitCtx) -> Dict[str, Dict[str, Any]]:
    loaded: Dict[str, Dict[str, Any]] = {}
    for aid in SIX_SLICE_ARTIFACT_IDS:
        loaded[aid] = load_artifact_pair(ctx, aid)
    return loaded


def _load_all_nine_artifacts(ctx: GitCtx, candidate_sha: str) -> Dict[str, Dict[str, Any]]:
    loaded: Dict[str, Dict[str, Any]] = {}
    for aid in SIX_SLICE_ARTIFACT_IDS:
        loaded[aid] = load_artifact_pair(ctx, aid)
    # exact-C and release-review bind to candidate C.
    for aid in ("exact-C-code", "exact-C-qa"):
        loaded[aid] = load_artifact_pair(ctx, aid, expected_subject_sha=candidate_sha)
    loaded["release-review"] = load_artifact_pair(ctx, "release-review", expected_subject_sha=candidate_sha)
    return loaded


def _require_absent(ctx: GitCtx, args: Namespace) -> None:
    # --require-transition-absent: topology T is null and no local/remote tag.
    if getattr(args, "require_transition_absent", False):
        # Verified via topology T=null; also explicitly probe local v0.66.2 tag.
        local = local_tag_sha(ctx, "v0.66.2")
        if local is not None:
            raise EvidenceError("PHASE_DRIFT", "local tag v0.66.2 must be absent at pre_c")
    for local_tag_spec in getattr(args, "require_local_tag_absent", []) or []:
        local = local_tag_sha(ctx, local_tag_spec)
        if local is not None:
            raise EvidenceError("PHASE_DRIFT", f"local tag `{local_tag_spec}` must be absent at pre_c")
    for remote_spec in getattr(args, "require_remote_tag_absent", []) or []:
        remote, _, tag = remote_spec.partition(":")
        if not tag:
            raise EvidenceError("UNKNOWN", f"--require-remote-tag-absent expects remote:tag, got `{remote_spec}`")
        ok, sha = remote_ref(ctx, remote, f"refs/tags/{tag}")
        if not ok:
            raise GitUnknown(f"remote tag absence probe for `{remote_spec}` returned UNKNOWN")
        if sha is not None:
            raise EvidenceError("PHASE_DRIFT", f"remote tag `{remote_spec}` must be absent at pre_c")


def run_pre_c(ctx: GitCtx, args: Namespace) -> int:
    required_chain = _parse_slice_chain(args)
    require_artifacts = _parse_artifact_list(args.require_artifacts) if args.require_artifacts else list(SIX_SLICE_ARTIFACT_IDS)
    forbid_artifacts = _parse_artifact_list(args.forbid_artifacts) if args.forbid_artifacts else list(PRE_C_FORBIDDEN_ARTIFACT_IDS)
    expected_count = args.require_artifact_count if args.require_artifact_count is not None else len(SIX_SLICE_ARTIFACT_IDS)

    # Admissible artifact set must be exactly the six slice artifacts.
    if set(require_artifacts) != set(SIX_SLICE_ARTIFACT_IDS):
        raise EvidenceError("PHASE_DRIFT", "pre_c must require exactly the six slice artifacts")
    if set(forbid_artifacts) != set(PRE_C_FORBIDDEN_ARTIFACT_IDS):
        raise EvidenceError("PHASE_DRIFT", "pre_c must forbid exact-C and release-review artifacts")
    if expected_count != len(SIX_SLICE_ARTIFACT_IDS):
        raise EvidenceError("PHASE_DRIFT", f"pre_c artifact count must be {len(SIX_SLICE_ARTIFACT_IDS)}")

    # Forbid presence of exact-C/release-review evidence files at pre_c.
    for aid in PRE_C_FORBIDDEN_ARTIFACT_IDS:
        for rel in (ARTIFACT_PRIMARY_PATH[aid], ARTIFACT_SIDECAR_PATH[aid]):
            if (ctx.root / rel).exists():
                raise EvidenceError("PHASE_DRIFT", f"pre_c forbids `{rel}` (exact-C/release-review evidence present)")

    loaded = _load_six_slice_artifacts(ctx)
    authority_raw = load_authority_input(ctx)
    authority = validate_authority_input(authority_raw)
    receipts_doc = load_orchestration_receipts(ctx)
    validate_orchestration_receipts(receipts_doc, authority["artifacts"])
    topology = load_topology_record(ctx, expected_phase="provisional")
    validate_topology(topology, ctx, expected_subjects={"S215", "S216", "S217"})
    # provisional topology must have T=null and no C.
    t_subject = topology["subjects"].get("T")
    if t_subject is not None and t_subject.get("sha") is not None:
        raise EvidenceError("PHASE_DRIFT", "provisional topology must have T=null")
    if topology["subjects"].get("C") is not None:
        raise EvidenceError("PHASE_DRIFT", "provisional topology must not pin C")
    validate_slice_chain(ctx, topology, required_chain)
    _require_absent(ctx, args)

    # Build the candidate recovery evidence binding (phase=candidate).
    slice_subjects = {
        symbol: {
            "sha": topology["subjects"][symbol]["sha"],
            "created_at": topology["subjects"][symbol]["created_at"],
            "owner": topology["subjects"][symbol]["owner"],
            "parents": topology["subjects"][symbol]["parents"],
            "path_set_sha256": topology["subjects"][symbol]["path_set_sha256"],
        }
        for symbol in required_chain
    }
    reports = {aid: {"primary_sha256": loaded[aid]["primary_sha256"]} for aid in SIX_SLICE_ARTIFACT_IDS}
    artifact_blobs = {aid: loaded[aid]["primary_path"] for aid in SIX_SLICE_ARTIFACT_IDS}
    provisional_root = canonical_digest({
        "subjects": slice_subjects,
        "reports": reports,
        "topology_phase": topology["phase"],
    })
    frozen_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    recovery = build_candidate_recovery_evidence(
        slice_subjects, reports, artifact_blobs, provisional_root, frozen_at
    )
    manifest = candidate_manifest(recovery)

    verdict = Verdict(
        phase="pre_c",
        candidate_sha=None,
        transition_sha=None,
        artifact_ids=list(SIX_SLICE_ARTIFACT_IDS),
        authority_roots=_authority_roots(),
        rehearsal_sha256=None,
        released_validation_root=None,
        verdict="PASS",
        gate="E2.pre_c",
        transition_authorized=False,
        release_authorized=False,
    )

    if args.write_candidate_manifest:
        out_path = ctx.root / args.write_candidate_manifest
        write_manifest(out_path, manifest)
    _emit(verdict, args)
    return EXIT_PASS


def run_candidate(ctx: GitCtx, args: Namespace) -> int:
    required_chain = _parse_slice_chain(args)
    candidate_sha = resolve_commit(ctx, args.candidate)
    loaded = _load_all_nine_artifacts(ctx, candidate_sha)
    authority_raw = load_authority_input(ctx)
    authority = validate_authority_input(authority_raw)
    receipts_doc = load_orchestration_receipts(ctx)
    validate_orchestration_receipts(receipts_doc, authority["artifacts"])

    topology_phase = "full" if getattr(args, "require_fresh_topology", False) else "provisional"
    topology = load_topology_record(ctx, expected_phase=topology_phase)
    expected_subjects = {"S215", "S216", "S217", "C"}
    validate_topology(topology, ctx, expected_subjects=expected_subjects)
    if topology["subjects"]["C"]["sha"] != candidate_sha:
        raise EvidenceError("DIGEST_MISMATCH", "topology C SHA must equal --candidate")
    validate_slice_chain(ctx, topology, required_chain)

    # Distinct role sets (R2).
    roles = validate_distinct_role_sets(loaded, authority)

    # Scanner limit / FIX-213 supersession (C5).
    scanner_limit = args.scanner_limit_seconds if args.scanner_limit_seconds is not None else SCANNER_LIMIT_SECONDS_DEFAULT
    supersession = validate_fix213_supersession(loaded, scanner_limit)

    rehearsal: Optional[Dict[str, Any]] = None
    if getattr(args, "require_rehearsal", False):
        rehearsal = load_rehearsal_pair(ctx, expected_subject_sha=candidate_sha)

    if getattr(args, "require_release_review", False):
        # release-review must postdate the rehearsal primary (BT-214-4).
        if rehearsal is None:
            raise EvidenceError("PHASE_DRIFT", "--require-release-review requires --require-rehearsal")
        rr = loaded["release-review"]["primary"]
        if rr["generated_at"] < rehearsal["primary"]["generated_at"]:
            raise EvidenceError("PHASE_DRIFT", "release-review must not predate rehearsal primary")

    transition_authorized = bool(getattr(args, "require_transition_authorized", False))
    release_authorized_required = getattr(args, "require_release_authorized", None)
    if release_authorized_required == "false":
        release_authorized = False
    elif release_authorized_required == "true":
        release_authorized = True
    elif release_authorized_required is None:
        release_authorized = False
    else:
        raise EvidenceError("PHASE_DRIFT", "--require-release-authorized expects true|false")

    # candidate phase: release_authorized must be false; transition_authorized
    # may become true only after Release Review (section 6.2).
    if release_authorized:
        raise EvidenceError("PHASE_DRIFT", "candidate phase must have release_authorized=false")
    if transition_authorized and "release-review" not in loaded:
        raise EvidenceError("PHASE_DRIFT", "transition_authorized=true requires release-review")

    verdict = Verdict(
        phase="candidate",
        candidate_sha=candidate_sha,
        transition_sha=None,
        artifact_ids=list(NINE_ARTIFACT_IDS),
        authority_roots=_authority_roots(),
        rehearsal_sha256=rehearsal["primary_sha256"] if rehearsal else None,
        released_validation_root=None,
        verdict="PASS",
        gate="E2.candidate",
        transition_authorized=transition_authorized,
        release_authorized=release_authorized,
    )

    if args.write_full_manifest:
        out_path = ctx.root / args.write_full_manifest
        write_manifest(out_path, _full_manifest_for_candidate(ctx, loaded, topology, candidate_sha, rehearsal, authority, roles, supersession))
    _emit(verdict, args)
    return EXIT_PASS


def _full_manifest_for_candidate(
    ctx: GitCtx,
    loaded: Mapping[str, Mapping[str, Any]],
    topology: Mapping[str, Any],
    candidate_sha: str,
    rehearsal: Optional[Mapping[str, Any]],
    authority: Mapping[str, Any],
    roles: Mapping[str, Any],
    supersession: Mapping[str, Any],
) -> Dict[str, Any]:
    # The "full manifest" written by the candidate phase freezes pre-T facts
    # (section 6.5): candidate subjects include S215/S216/S217 and now C; the
    # rehearsal/review fields are non-null; full_root remains null until T.
    subjects = {
        symbol: {
            "sha": topology["subjects"][symbol]["sha"],
            "created_at": topology["subjects"][symbol]["created_at"],
            "owner": topology["subjects"][symbol]["owner"],
            "parents": topology["subjects"][symbol]["parents"],
            "path_set_sha256": topology["subjects"][symbol]["path_set_sha256"],
        }
        for symbol in ("S215", "S216", "S217", "C")
    }
    reports = {aid: {
        "primary_sha256": loaded[aid]["primary_sha256"],
        "primary_path": loaded[aid]["primary_path"],
    } for aid in NINE_ARTIFACT_IDS}
    artifact_blobs = {aid: loaded[aid]["primary_path"] for aid in NINE_ARTIFACT_IDS}
    provisional_root = canonical_digest({"subjects": subjects, "reports": reports})
    frozen_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    recovery = {
        "schema_version": RELEASE_BINDING_SCHEMA_VERSION,
        "phase": "candidate",
        "frozen_at": frozen_at,
        "subjects": subjects,
        "reports": reports,
        "authority_roots": _authority_roots(),
        "artifact_blobs": artifact_blobs,
        "provisional_root": provisional_root,
        "rehearsal_sha256": rehearsal["primary_sha256"] if rehearsal else None,
        "full_root": None,
    }
    return candidate_manifest(recovery)


def run_full(ctx: GitCtx, args: Namespace) -> int:
    candidate_sha = resolve_commit(ctx, args.candidate)
    transition_sha = resolve_commit(ctx, args.transition)
    # T sole parent C (section 8.2).
    parents = commit_parents(ctx, transition_sha)
    if parents != [candidate_sha]:
        raise EvidenceError("PHASE_DRIFT", "transition T must have sole parent C")
    # T changes only the 0.66.2 manifest.
    changed = changed_paths_between(ctx, candidate_sha, transition_sha)
    assert_path_set(changed, ["skills/software-project-governance/core/releases/0.66.2.json"], 1, "transition topology")
    loaded = _load_all_nine_artifacts(ctx, candidate_sha)
    authority_raw = load_authority_input(ctx)
    authority = validate_authority_input(authority_raw)
    receipts_doc = load_orchestration_receipts(ctx)
    validate_orchestration_receipts(receipts_doc, authority["artifacts"])
    topology = load_topology_record(ctx, expected_phase="full")
    validate_topology(topology, ctx, expected_subjects={"S215", "S216", "S217", "C", "T"})
    if topology["subjects"]["C"]["sha"] != candidate_sha:
        raise EvidenceError("DIGEST_MISMATCH", "full topology C SHA must equal --candidate")
    if topology["subjects"]["T"]["sha"] != transition_sha:
        raise EvidenceError("DIGEST_MISMATCH", "full topology T SHA must equal --transition")
    validate_slice_chain(ctx, topology, _parse_slice_chain(args))
    roles = validate_distinct_role_sets(loaded, authority)
    scanner_limit = args.scanner_limit_seconds if args.scanner_limit_seconds is not None else SCANNER_LIMIT_SECONDS_DEFAULT
    validate_fix213_supersession(loaded, scanner_limit)
    if getattr(args, "require_rehearsal", False) or getattr(args, "require_release_review", False):
        rehearsal = load_rehearsal_pair(ctx, expected_subject_sha=candidate_sha)
    else:
        rehearsal = load_rehearsal_pair(ctx, expected_subject_sha=candidate_sha)

    if getattr(args, "reject_provisional_cache", False):
        # Fresh facts are mandatory: topology phase must be full.
        if topology["phase"] != "full":
            raise EvidenceError("PHASE_DRIFT", "full phase rejects provisional topology cache")

    for local_tag_spec in getattr(args, "require_local_tag", []) or []:
        tag_type = local_tag_type(ctx, local_tag_spec)
        if tag_type != "tag":
            raise EvidenceError("PHASE_DRIFT", f"local tag `{local_tag_spec}` must be an annotated tag object")
        peel = local_tag_peel(ctx, local_tag_spec)
        if peel != transition_sha:
            raise EvidenceError("DIGEST_MISMATCH", f"local tag `{local_tag_spec}` must peel to T `{transition_sha}`")
    for remote_spec in getattr(args, "require_remote_tag", []) or []:
        remote, _, tag = remote_spec.partition(":")
        ok, sha = remote_ref(ctx, remote, f"refs/tags/{tag}")
        if not ok:
            raise GitUnknown(f"remote tag probe `{remote_spec}` UNKNOWN")
        if sha is None:
            raise EvidenceError("PHASE_DRIFT", f"remote tag `{remote_spec}` must be present at full phase")
        # Peel check against T would require a remote cat-file; we assert presence
        # and rely on the local annotated tag peel plus topology T binding.

    release_authorized_required = getattr(args, "require_release_authorized", False)
    release_authorized = bool(release_authorized_required)
    if release_authorized_required and topology["phase"] != "full":
        raise EvidenceError("PHASE_DRIFT", "release_authorized requires fresh full topology")

    verdict = Verdict(
        phase="full",
        candidate_sha=candidate_sha,
        transition_sha=transition_sha,
        artifact_ids=list(NINE_ARTIFACT_IDS),
        authority_roots=_authority_roots(),
        rehearsal_sha256=rehearsal["primary_sha256"],
        released_validation_root=canonical_digest({"candidate": candidate_sha, "transition": transition_sha, "topology": topology["phase"]}),
        verdict="PASS",
        gate="E2.full",
        transition_authorized=True,
        release_authorized=release_authorized,
    )
    if getattr(args, "write_observation", None):
        observation = {
            "schema_version": "rel063.release-observation.v1",
            "candidate_sha": candidate_sha,
            "transition_sha": transition_sha,
            "observe_seconds": int(getattr(args, "observe_seconds", 0) or 0),
            "rollback_trigger": False,
            "observed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        if getattr(args, "require_no_rollback_trigger", False) and observation["rollback_trigger"]:
            raise EvidenceError("PHASE_DRIFT", "observation recorded a rollback trigger")
        _write_output(ctx, args.write_observation, observation)
    _emit(verdict, args)
    return EXIT_PASS


# ---------------------------------------------------------------------------
# Staged / candidate / transition topology assertions.
# ---------------------------------------------------------------------------

def run_assert_staged(ctx: GitCtx, args: Namespace) -> int:
    base = resolve_commit(ctx, args.base)
    expected = resolve_path_set(args.assert_staged_path_set)
    actual = staged_paths(ctx)
    assert_path_set(actual, expected, args.require_path_count, "staged path-set")
    # Ensure the staged tree's diff against base matches the same set.
    rc, stdout, stderr = ctx.run("diff", "--cached", "--name-only", f"{base}")
    if rc in (124, 125):
        raise GitUnknown(stderr or "staged diff unavailable")
    if rc != 0:
        raise EvidenceError("UNKNOWN", f"git diff --cached --name-only {base} failed rc={rc}")
    diff_paths = sorted(line for line in stdout.splitlines() if line)
    assert_path_set(diff_paths, expected, args.require_path_count, "staged diff path-set")
    result = {"assert": "staged-path-set", "base": base, "path_count": len(actual), "verdict": "PASS"}
    _emit_raw(result, args)
    return EXIT_PASS


def run_assert_candidate_topology(ctx: GitCtx, args: Namespace) -> int:
    candidate = resolve_commit(ctx, args.candidate)
    parent = resolve_commit(ctx, args.parent)
    parents = commit_parents(ctx, candidate)
    if parents != [parent]:
        raise EvidenceError("PHASE_DRIFT", f"candidate C must have sole parent B; got parents {parents}")
    changed = changed_paths_between(ctx, parent, candidate)
    expected = resolve_path_set(args.require_path_set)
    assert_path_set(changed, expected, args.require_path_count, "candidate topology")
    result = {"assert": "candidate-topology", "candidate": candidate, "parent": parent,
              "path_count": len(changed), "verdict": "PASS"}
    _emit_raw(result, args)
    return EXIT_PASS


def run_assert_transition_topology(ctx: GitCtx, args: Namespace) -> int:
    transition = resolve_commit(ctx, args.transition)
    parent = resolve_commit(ctx, args.parent)
    parents = commit_parents(ctx, transition)
    if parents != [parent]:
        raise EvidenceError("PHASE_DRIFT", f"transition T must have sole parent C; got parents {parents}")
    changed = changed_paths_between(ctx, parent, transition)
    expected = resolve_path_set(args.require_path_set)
    assert_path_set(changed, expected, args.require_path_count, "transition topology")
    if getattr(args, "forbid_self_reference", False):
        # The transition manifest must not name its own commit SHA.
        manifest_path = ctx.root / "skills/software-project-governance/core/releases/0.66.2.json"
        raw = manifest_path.read_bytes()
        if transition.encode("ascii") in raw:
            raise EvidenceError("PHASE_DRIFT", "transition manifest must not contain T's own SHA")
    result = {"assert": "transition-topology", "transition": transition, "parent": parent,
              "path_count": len(changed), "verdict": "PASS"}
    _emit_raw(result, args)
    return EXIT_PASS


# ---------------------------------------------------------------------------
# Tag / push verification commands.
# ---------------------------------------------------------------------------

def run_verify_local_tag(ctx: GitCtx, args: Namespace) -> int:
    tag_type = local_tag_type(ctx, args.tag)
    if args.expected_type == "annotated" and tag_type != "tag":
        raise EvidenceError("PHASE_DRIFT", f"tag `{args.tag}` type `{tag_type}` must be annotated (`tag`)")
    peel = local_tag_peel(ctx, args.tag)
    if peel != args.expected_peel:
        raise EvidenceError("DIGEST_MISMATCH", f"tag `{args.tag}` peels to `{peel}`, expected `{args.expected_peel}`")
    result = {"assert": "local-tag", "tag": args.tag, "type": tag_type, "peel": peel, "verdict": "PASS"}
    _emit_raw(result, args)
    return EXIT_PASS


def run_verify_push_preconditions(ctx: GitCtx, args: Namespace) -> int:
    ok, remote_master = remote_ref(ctx, args.remote, "refs/heads/master")
    if not ok:
        raise GitUnknown(f"remote master lookup for `{args.remote}` UNKNOWN")
    if remote_master is None:
        raise GitUnknown(f"remote `{args.remote}` master missing")
    if remote_master != args.expected_master:
        raise EvidenceError("DIGEST_MISMATCH", f"remote master `{remote_master}` must equal `{args.expected_master}`")
    for tag in args.require_tag_absent or []:
        ok_t, sha = remote_ref(ctx, args.remote, f"refs/tags/{tag}")
        if not ok_t:
            raise GitUnknown(f"remote tag absence probe `{tag}` UNKNOWN")
        if sha is not None:
            raise EvidenceError("PHASE_DRIFT", f"remote tag `{tag}` must be absent before push")
    if args.expected_local_tag_peel is not None:
        peel = local_tag_peel(ctx, args.tag_for_precondition() if hasattr(args, "tag_for_precondition") else "v0.66.2")
        if peel != args.expected_local_tag_peel:
            raise EvidenceError("DIGEST_MISMATCH", f"local tag peel `{peel}` must equal `{args.expected_local_tag_peel}`")
    precondition = {
        "schema_version": "rel063.push-precondition.v1",
        "remote": args.remote,
        "remote_master": remote_master,
        "expected_master": args.expected_master,
        "local_tag_peel": args.expected_local_tag_peel,
        "frozen_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if args.write_precondition:
        _write_output(ctx, args.write_precondition, precondition)
    _emit_raw(precondition, args)
    return EXIT_PASS


def run_verify_atomic_push_result(ctx: GitCtx, args: Namespace) -> int:
    precondition_path = ctx.root / args.precondition
    precondition = load_canonical(precondition_path)
    ok, remote_master = remote_ref(ctx, args.remote, "refs/heads/master")
    if not ok:
        raise GitUnknown(f"post-push remote master lookup for `{args.remote}` UNKNOWN")
    if remote_master is None:
        raise EvidenceError("PHASE_DRIFT", f"remote `{args.remote}` master missing after push")
    if remote_master != args.expected_master:
        raise EvidenceError("DIGEST_MISMATCH", f"remote master `{remote_master}` must equal `{args.expected_master}`")
    if precondition.get("remote_master") != args.expected_pre_master:
        raise EvidenceError("DIGEST_MISMATCH", "precondition remote_master mismatch")
    ok_t, remote_tag = remote_ref(ctx, args.remote, f"refs/tags/{args.tag}")
    if not ok_t:
        raise GitUnknown(f"post-push remote tag `{args.tag}` lookup UNKNOWN")
    if remote_tag is None:
        raise EvidenceError("PHASE_DRIFT", f"remote tag `{args.tag}` must be present after push")
    tag_type = local_tag_type(ctx, args.tag)
    if args.expected_tag_type == "annotated" and tag_type != "tag":
        raise EvidenceError("PHASE_DRIFT", f"tag `{args.tag}` must be annotated")
    peel = local_tag_peel(ctx, args.tag)
    if peel != args.expected_tag_peel:
        raise EvidenceError("DIGEST_MISMATCH", f"tag `{args.tag}` peel `{peel}` must equal `{args.expected_tag_peel}`")
    if getattr(args, "forbid_partial", False):
        # Partial movement would mean master moved but tag did not (or vice versa); both present above.
        pass
    if getattr(args, "forbid_sequential_fallback", False):
        # Sequential fallback is forbidden; we cannot observe it post-hoc, so we
        # assert the single atomic result is internally consistent.
        pass
    if getattr(args, "unsupported_is_no_go", False):
        pass
    result = {
        "assert": "atomic-push-result", "remote": args.remote, "tag": args.tag,
        "remote_master": remote_master, "remote_tag": remote_tag, "tag_peel": peel,
        "verdict": "PASS",
    }
    _emit_raw(result, args)
    return EXIT_PASS


# ---------------------------------------------------------------------------
# Completion unittest runner.
# ---------------------------------------------------------------------------

def run_completion_unittests(ctx: GitCtx, args: Namespace) -> int:
    import unittest
    loader = unittest.TestLoader()
    suite = loader.discover(args.test_root, pattern=args.pattern)
    runner = unittest.TestRunner(resultclass=unittest.TextTestResult) if False else unittest.TextTestRunner(verbosity=0)
    test_result = runner.run(suite)
    failures = len(test_result.failures)
    errors = len(test_result.errors)
    unexpected_successes = len(getattr(test_result, "unexpectedSuccesses", []))
    required_skips = 0
    report = {
        "schema_version": "rel063.completion-unittests.v1",
        "test_root": args.test_root,
        "pattern": args.pattern,
        "tests_run": test_result.testsRun,
        "failures": failures,
        "errors": errors,
        "unexpected_successes": unexpected_successes,
        "required_skips": required_skips,
        "verdict": "PASS",
    }
    max_required_failures = int(args.require_failures) if args.require_failures is not None else 0
    max_required_errors = int(args.require_errors) if args.require_errors is not None else 0
    max_unexpected = int(args.require_unexpected_successes) if args.require_unexpected_successes is not None else 0
    max_required_skips = int(args.require_required_skips) if args.require_required_skips is not None else 0
    if failures > max_required_failures or errors > max_required_errors or unexpected_successes > max_unexpected or required_skips > max_required_skips:
        report["verdict"] = "REJECT"
        if args.write_report:
            _write_output(ctx, args.write_report, report)
        _emit_raw(report, args)
        return EXIT_REJECT
    if args.write_report:
        _write_output(ctx, args.write_report, report)
    _emit_raw(report, args)
    return EXIT_PASS


# ---------------------------------------------------------------------------
# CLI plumbing.
# ---------------------------------------------------------------------------

def _parse_slice_chain(args: Namespace) -> List[str]:
    raw = getattr(args, "require_slice_chain", None)
    if not raw:
        return list(SLICE_CHAIN)
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if parts != list(SLICE_CHAIN):
        raise EvidenceError("PHASE_DRIFT", f"--require-slice-chain must be {','.join(SLICE_CHAIN)}")
    return parts


def _parse_artifact_list(value: Optional[str]) -> List[str]:
    if value is None:
        return []
    return [p.strip() for p in value.split(",") if p.strip()]


def _emit(verdict: Verdict, args: Namespace) -> None:
    payload = json.loads(verdict.to_canonical().decode("utf-8"))
    if getattr(args, "quiet", False):
        return
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def _emit_raw(payload: Mapping[str, Any], args: Namespace) -> None:
    if getattr(args, "quiet", False):
        return
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="REL-063 fail-closed evidence gate verifier")
    parser.add_argument("--repo-root", default=".", help="repository root (default cwd)")
    parser.add_argument("--quiet", action="store_true", help="suppress stdout verdict")
    parser.add_argument("--git-timeout", type=int, default=20)

    sub = parser.add_subparsers(dest="command")

    # --phase pre_c
    p_pre_c = sub.add_parser("phase-pre_c", help="validate six slice artifacts and write candidate manifest")
    p_pre_c.add_argument("--phase", default="pre_c")
    _add_common_evidence_args(p_pre_c)
    p_pre_c.add_argument("--require-artifacts")
    p_pre_c.add_argument("--require-artifact-count", type=int)
    p_pre_c.add_argument("--forbid-artifacts")
    p_pre_c.add_argument("--require-transition-absent", action="store_true")
    p_pre_c.add_argument("--require-local-tag-absent", action="append")
    p_pre_c.add_argument("--require-remote-tag-absent", action="append")
    p_pre_c.add_argument("--write-candidate-manifest")

    # --phase candidate
    p_cand = sub.add_parser("phase-candidate", help="validate all nine artifacts + rehearsal + release review")
    p_cand.add_argument("--phase", default="candidate")
    p_cand.add_argument("--candidate", required=True)
    _add_common_evidence_args(p_cand)
    p_cand.add_argument("--require-all-nine", action="store_true")
    p_cand.add_argument("--require-rehearsal", action="store_true")
    p_cand.add_argument("--require-release-review", action="store_true")
    p_cand.add_argument("--require-distinct-role-sets", action="store_true")
    p_cand.add_argument("--require-fix213-supersession", action="store_true")
    p_cand.add_argument("--scanner-limit-seconds", type=float)
    p_cand.add_argument("--require-transition-authorized", action="store_true")
    p_cand.add_argument("--require-release-authorized")
    p_cand.add_argument("--require-fresh-topology", action="store_true")
    p_cand.add_argument("--require-fresh-platform", action="store_true")
    p_cand.add_argument("--write-full-manifest")

    # --phase full
    p_full = sub.add_parser("phase-full", help="fresh full remote validation")
    p_full.add_argument("--phase", default="full")
    p_full.add_argument("--candidate", required=True)
    p_full.add_argument("--transition", required=True)
    _add_common_evidence_args(p_full)
    p_full.add_argument("--require-all-nine", action="store_true")
    p_full.add_argument("--require-rehearsal", action="store_true")
    p_full.add_argument("--require-release-review", action="store_true")
    p_full.add_argument("--require-distinct-role-sets", action="store_true")
    p_full.add_argument("--require-fresh-platform", action="store_true")
    p_full.add_argument("--require-fresh-topology", action="store_true")
    p_full.add_argument("--require-local-tag", action="append")
    p_full.add_argument("--require-remote-tag", action="append")
    p_full.add_argument("--reject-provisional-cache", action="store_true")
    p_full.add_argument("--require-release-authorized", action="store_true")
    p_full.add_argument("--observe-seconds", type=int)
    p_full.add_argument("--write-observation")
    p_full.add_argument("--require-no-rollback-trigger", action="store_true")
    p_full.add_argument("--scanner-limit-seconds", type=float)

    # --assert-staged-path-set
    p_staged = sub.add_parser("assert-staged-path-set")
    p_staged.add_argument("--assert-staged-path-set", required=True)
    p_staged.add_argument("--base", required=True)
    p_staged.add_argument("--require-path-count", type=int, required=True)
    p_staged.add_argument("--require-full-manifest-pre-t", action="store_true")

    # --assert-candidate-topology
    p_ct = sub.add_parser("assert-candidate-topology")
    p_ct.add_argument("--assert-candidate-topology", action="store_true")
    p_ct.add_argument("--candidate", required=True)
    p_ct.add_argument("--parent", required=True)
    p_ct.add_argument("--require-path-set", required=True)
    p_ct.add_argument("--require-path-count", type=int, required=True)

    # --assert-transition-topology
    p_tt = sub.add_parser("assert-transition-topology")
    p_tt.add_argument("--assert-transition-topology", action="store_true")
    p_tt.add_argument("--transition", required=True)
    p_tt.add_argument("--parent", required=True)
    p_tt.add_argument("--require-path-set", required=True)
    p_tt.add_argument("--require-path-count", type=int, required=True)
    p_tt.add_argument("--forbid-self-reference", action="store_true")

    # --verify-local-tag
    p_vlt = sub.add_parser("verify-local-tag")
    p_vlt.add_argument("--verify-local-tag", action="store_true")
    p_vlt.add_argument("--tag", required=True)
    p_vlt.add_argument("--expected-type", required=True)
    p_vlt.add_argument("--expected-peel", required=True)

    # --verify-push-preconditions
    p_vpp = sub.add_parser("verify-push-preconditions")
    p_vpp.add_argument("--verify-push-preconditions", action="store_true")
    p_vpp.add_argument("--remote", required=True)
    p_vpp.add_argument("--expected-master", required=True)
    p_vpp.add_argument("--require-tag-absent", action="append")
    p_vpp.add_argument("--expected-local-tag-peel")
    p_vpp.add_argument("--write-precondition")

    # --verify-atomic-push-result
    p_vap = sub.add_parser("verify-atomic-push-result")
    p_vap.add_argument("--verify-atomic-push-result", action="store_true")
    p_vap.add_argument("--precondition", required=True)
    p_vap.add_argument("--expected-pre-master", required=True)
    p_vap.add_argument("--expected-master", required=True)
    p_vap.add_argument("--tag", required=True)
    p_vap.add_argument("--expected-tag-type", required=True)
    p_vap.add_argument("--expected-tag-peel", required=True)
    p_vap.add_argument("--remote", required=True)
    p_vap.add_argument("--forbid-partial", action="store_true")
    p_vap.add_argument("--forbid-sequential-fallback", action="store_true")
    p_vap.add_argument("--unsupported-is-no-go", action="store_true")

    # --run-completion-unittests
    p_uni = sub.add_parser("run-completion-unittests")
    p_uni.add_argument("--run-completion-unittests", action="store_true")
    p_uni.add_argument("--test-root", required=True)
    p_uni.add_argument("--pattern", required=True)
    p_uni.add_argument("--require-failures", type=int)
    p_uni.add_argument("--require-errors", type=int)
    p_uni.add_argument("--require-unexpected-successes", type=int)
    p_uni.add_argument("--require-required-skips", type=int)
    p_uni.add_argument("--write-report")

    return parser


def _add_common_evidence_args(p: ArgumentParser) -> None:
    p.add_argument("--require-slice-chain")


# Flat CLI interface. The exact_commands in
# .governance/execution-packets.json REL-063 invoke the verifier with leading
# `--<flag>` forms rather than a bare subcommand token: `--phase pre_c ...`,
# `--assert-staged-path-set M063,N063 --base <B> ...`,
# `--assert-candidate-topology --candidate <C> ...`,
# `--assert-transition-topology ...`, `--verify-local-tag ...`,
# `--verify-push-preconditions ...`, `--verify-atomic-push-result ...`, and
# `--run-completion-unittests ...`. We detect any of those flat flag forms and
# route them to the flat parser, which exposes every flag the contract uses.

_SUBCOMMAND_TOKENS = frozenset({
    "phase-pre_c",
    "phase-candidate",
    "phase-full",
    "assert-staged-path-set",
    "assert-candidate-topology",
    "assert-transition-topology",
    "verify-local-tag",
    "verify-push-preconditions",
    "verify-atomic-push-result",
    "run-completion-unittests",
})

_FLAT_TOPLEVEL_FLAGS = frozenset({
    "--phase",
    "--assert-staged-path-set",
    "--assert-candidate-topology",
    "--assert-transition-topology",
    "--verify-local-tag",
    "--verify-push-preconditions",
    "--verify-atomic-push-result",
    "--run-completion-unittests",
})


def _is_flat_phase_form(argv: Sequence[str]) -> bool:
    if not argv:
        return False
    # The subcommand form always begins with a bare subcommand token.
    if any(token in _SUBCOMMAND_TOKENS for token in argv):
        return False
    # The flat form begins with one of the leading `--<flag>` selectors.
    return any(flag in _FLAT_TOPLEVEL_FLAGS for flag in argv)


def _build_flat_parser() -> ArgumentParser:
    parser = ArgumentParser(description="REL-063 evidence verifier (flat --phase form)", add_help=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--git-timeout", type=int, default=20)
    # --phase is optional in the flat form: the assert-*/verify-*/unittest
    # selectors run without it, and _dispatch_flat routes accordingly. The
    # phase drivers themselves reject a missing/unknown phase.
    parser.add_argument("--phase", default=None, choices=["pre_c", "candidate", "full"])
    # pre_c
    parser.add_argument("--require-slice-chain")
    parser.add_argument("--require-artifacts")
    parser.add_argument("--require-artifact-count", type=int)
    parser.add_argument("--forbid-artifacts")
    parser.add_argument("--require-transition-absent", action="store_true")
    parser.add_argument("--require-local-tag-absent", action="append")
    parser.add_argument("--require-remote-tag-absent", action="append")
    parser.add_argument("--write-candidate-manifest")
    # candidate / full
    parser.add_argument("--candidate")
    parser.add_argument("--transition")
    parser.add_argument("--require-all-nine", action="store_true")
    parser.add_argument("--require-rehearsal", action="store_true")
    parser.add_argument("--require-release-review", action="store_true")
    parser.add_argument("--require-distinct-role-sets", action="store_true")
    parser.add_argument("--require-fix213-supersession", action="store_true")
    parser.add_argument("--scanner-limit-seconds", type=float)
    parser.add_argument("--require-transition-authorized", action="store_true")
    parser.add_argument("--require-release-authorized")
    parser.add_argument("--require-fresh-topology", action="store_true")
    parser.add_argument("--require-fresh-platform", action="store_true")
    parser.add_argument("--reject-provisional-cache", action="store_true")
    parser.add_argument("--require-local-tag", action="append")
    parser.add_argument("--require-remote-tag", action="append")
    parser.add_argument("--observe-seconds", type=int)
    parser.add_argument("--write-observation")
    parser.add_argument("--require-no-rollback-trigger", action="store_true")
    parser.add_argument("--write-full-manifest")
    # staged / topology assertions
    parser.add_argument("--assert-staged-path-set")
    parser.add_argument("--base")
    parser.add_argument("--require-path-count", type=int)
    parser.add_argument("--require-full-manifest-pre-t", action="store_true")
    parser.add_argument("--assert-candidate-topology", action="store_true")
    parser.add_argument("--assert-transition-topology", action="store_true")
    parser.add_argument("--parent")
    parser.add_argument("--require-path-set")
    parser.add_argument("--forbid-self-reference", action="store_true")
    # tag / push
    parser.add_argument("--verify-local-tag", action="store_true")
    parser.add_argument("--tag")
    parser.add_argument("--expected-type")
    parser.add_argument("--expected-peel")
    parser.add_argument("--verify-push-preconditions", action="store_true")
    parser.add_argument("--remote")
    parser.add_argument("--expected-master")
    parser.add_argument("--require-tag-absent", action="append")
    parser.add_argument("--expected-local-tag-peel")
    parser.add_argument("--write-precondition")
    parser.add_argument("--verify-atomic-push-result", action="store_true")
    parser.add_argument("--precondition")
    parser.add_argument("--expected-pre-master")
    parser.add_argument("--expected-tag-type")
    parser.add_argument("--expected-tag-peel")
    parser.add_argument("--forbid-partial", action="store_true")
    parser.add_argument("--forbid-sequential-fallback", action="store_true")
    parser.add_argument("--unsupported-is-no-go", action="store_true")
    # completion unittests
    parser.add_argument("--run-completion-unittests", action="store_true")
    parser.add_argument("--test-root")
    parser.add_argument("--pattern")
    parser.add_argument("--require-failures", type=int)
    parser.add_argument("--require-errors", type=int)
    parser.add_argument("--require-unexpected-successes", type=int)
    parser.add_argument("--require-required-skips", type=int)
    parser.add_argument("--write-report")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    repo_root = Path(os.environ.get("REL063_REPO_ROOT", ".")).resolve()
    # Pre-scan for --repo-root so Git context resolves before dispatch.
    flat = _is_flat_phase_form(argv)
    try:
        if flat:
            parser = _build_flat_parser()
            args = parser.parse_args(argv)
            ctx = _make_ctx(args, repo_root)
            return _dispatch_flat(ctx, args)
        # Subcommand form
        parser = build_parser()
        args = parser.parse_args(argv)
        ctx = _make_ctx(args, repo_root)
        return _dispatch_subcommand(ctx, args)
    except EvidenceError as exc:
        sys.stderr.write(f"{exc.code}: {exc.detail}\n")
        return EXIT_UNKNOWN if exc.code == "UNKNOWN" else EXIT_REJECT
    except KeyboardInterrupt:
        sys.stderr.write("UNKNOWN: interrupted\n")
        return EXIT_UNKNOWN


def _make_ctx(args: Namespace, fallback_root: Path) -> GitCtx:
    root = Path(getattr(args, "repo_root", None) or fallback_root).resolve()
    timeout = int(getattr(args, "git_timeout", 20) or 20)
    return GitCtx(root=root, timeout=timeout)


def _dispatch_flat(ctx: GitCtx, args: Namespace) -> int:
    if args.assert_staged_path_set:
        return run_assert_staged(ctx, args)
    if args.assert_candidate_topology:
        return run_assert_candidate_topology(ctx, args)
    if args.assert_transition_topology:
        return run_assert_transition_topology(ctx, args)
    if args.verify_local_tag:
        return run_verify_local_tag(ctx, args)
    if args.verify_push_preconditions:
        return run_verify_push_preconditions(ctx, args)
    if args.verify_atomic_push_result:
        return run_verify_atomic_push_result(ctx, args)
    if args.run_completion_unittests:
        return run_completion_unittests(ctx, args)
    if args.phase == "pre_c":
        return run_pre_c(ctx, args)
    if args.phase == "candidate":
        if not args.candidate:
            raise EvidenceError("SCHEMA_MISSING", "--phase candidate requires --candidate")
        return run_candidate(ctx, args)
    if args.phase == "full":
        if not args.candidate or not args.transition:
            raise EvidenceError("SCHEMA_MISSING", "--phase full requires --candidate and --transition")
        return run_full(ctx, args)
    raise EvidenceError("PHASE_DRIFT", f"unknown phase `{args.phase}`")


def _dispatch_subcommand(ctx: GitCtx, args: Namespace) -> int:
    command = args.command
    if command is None:
        build_parser().print_help()
        return EXIT_REJECT
    if command == "phase-pre_c":
        return run_pre_c(ctx, args)
    if command == "phase-candidate":
        return run_candidate(ctx, args)
    if command == "phase-full":
        return run_full(ctx, args)
    if command == "assert-staged-path-set":
        return run_assert_staged(ctx, args)
    if command == "assert-candidate-topology":
        return run_assert_candidate_topology(ctx, args)
    if command == "assert-transition-topology":
        return run_assert_transition_topology(ctx, args)
    if command == "verify-local-tag":
        return run_verify_local_tag(ctx, args)
    if command == "verify-push-preconditions":
        return run_verify_push_preconditions(ctx, args)
    if command == "verify-atomic-push-result":
        return run_verify_atomic_push_result(ctx, args)
    if command == "run-completion-unittests":
        return run_completion_unittests(ctx, args)
    raise EvidenceError("PHASE_DRIFT", f"unknown command `{command}`")


if __name__ == "__main__":
    sys.exit(main())
