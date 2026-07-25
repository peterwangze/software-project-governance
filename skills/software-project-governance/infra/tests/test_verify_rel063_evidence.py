"""Unit tests for verify_rel063_evidence.py — REL-063 evidence gate (C2/C3/C5/R1/R2/R7).

Architecture authority: docs/architecture/release-incident-recovery-0.66.2.md
sections 6.1 (canonical JSON), 6.2 (evidence/authority/topology/verdict), and
6.3 (rehearsal). Every negative fixture corresponds to a named gate in those
sections: missing/duplicate/type/unknown field, wrong digest/subject/role/
result/time/path, self-review, four-record producer/subject forge, provisional
T/tag present, remote UNKNOWN, and reused provisional root.

Run:
    python -m unittest discover -s skills/software-project-governance/infra/tests -p test_verify_rel063_evidence.py -v
"""

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

_HERE = Path(__file__).resolve().parent
_RELEASE_DIR = _HERE.parent / "release"
if str(_RELEASE_DIR) not in sys.path:
    sys.path.insert(0, str(_RELEASE_DIR))

import verify_rel063_evidence as v
from verify_rel063_evidence import EvidenceError, GitCtx, canonical_json_bytes, canonical_digest


# ---------------------------------------------------------------------------
# Canonical JSON / digest helpers.
# ---------------------------------------------------------------------------

def write_canonical(path: Path, payload: Mapping[str, Any]) -> str:
    raw = canonical_json_bytes(payload)
    path.write_bytes(raw)
    return sha256(raw).hexdigest()


def make_primary(artifact_id: str, subject_sha: str, *, result: str | None = None,
                 producer_id: str | None = None, release_authorized: bool | None = None,
                 generated_at: str = "2026-07-18T02:00:00Z") -> Dict[str, Any]:
    kind = v.EVIDENCE_KIND_BY_ARTIFACT[artifact_id]
    role = v.ROLE_BY_KIND[kind]
    task = v.TASK_BY_ARTIFACT[artifact_id]
    if result is None:
        result = "PASS" if kind == "qa" or kind == "exact_c_qa" else "APPROVED"
    if producer_id is None:
        producer_id = f"/root/{artifact_id.lower().replace('-', '_')}_producer"
    if release_authorized is None:
        release_authorized = (kind == "release_review")
    return {
        "schema_version": v.PRIMARY_SCHEMA_VERSION,
        "task_id": task,
        "evidence_kind": kind,
        "producer_role": role,
        "producer_id": producer_id,
        "result": result,
        "unresolved_blockers": 0,
        "subject_sha": subject_sha,
        "generated_at": generated_at,
        "release_authorized": release_authorized,
    }


def make_sidecar(artifact_id: str, primary: Mapping[str, Any], primary_path: str,
                 primary_digest: str) -> Dict[str, Any]:
    return {
        "schema_version": v.SIDECAR_SCHEMA_VERSION,
        "report_path": primary_path,
        "report_sha256": primary_digest,
        "task_id": primary["task_id"],
        "evidence_kind": primary["evidence_kind"],
        "producer_role": primary["producer_role"],
        "producer_id": primary["producer_id"],
        "result": primary["result"],
        "unresolved_blockers": primary["unresolved_blockers"],
        "subject_sha": primary["subject_sha"],
        "generated_at": primary["generated_at"],
        "release_authorized": primary["release_authorized"],
    }


def make_authority(developers: Mapping[str, str], release_producer_id: str = "/root/rel063_producer",
                   producer_overrides: Mapping[str, str] | None = None) -> Dict[str, Any]:
    artifacts: List[Dict[str, Any]] = []
    overrides = producer_overrides or {}
    for aid in v.NINE_ARTIFACT_IDS:
        kind = v.EVIDENCE_KIND_BY_ARTIFACT[aid]
        role = v.ROLE_BY_KIND[kind]
        producer_id = overrides.get(aid, f"/root/{aid.lower().replace('-', '_')}_producer")
        symbol = "C" if aid.startswith("exact-C") or aid == "release-review" else f"S{aid[4:7]}"
        if aid.startswith("exact-C") or aid == "release-review":
            symbol = "C"
        artifacts.append({
            "artifact_id": aid,
            "task_id": v.TASK_BY_ARTIFACT[aid],
            "evidence_kind": kind,
            "producer_role": role,
            "producer_id": producer_id,
            "receipt_id": f"rcpt-{aid}",
            "subject_symbol": symbol,
            "primary_path": v.ARTIFACT_PRIMARY_PATH[aid],
            "sidecar_path": v.ARTIFACT_SIDECAR_PATH[aid],
        })
    return {
        "schema_version": v.AUTHORITY_SCHEMA_VERSION,
        "frozen_at": "2026-07-18T01:00:00Z",
        "coordinator_id": "/root/coordinator",
        "developers": dict(developers),
        "release_producer_id": release_producer_id,
        "artifacts": artifacts,
    }


def make_receipts(authority: Mapping[str, Any]) -> Dict[str, Any]:
    receipts = []
    for entry in authority["artifacts"]:
        receipts.append({
            "receipt_id": entry["receipt_id"],
            "artifact_id": entry["artifact_id"],
            "task_id": entry["task_id"],
            "assigned_role": entry["producer_role"],
            "producer_id": entry["producer_id"],
            "dispatched_at": "2026-07-18T00:30:00Z",
        })
    return {
        "schema_version": v.ORCHESTRATION_SCHEMA_VERSION,
        "generated_at": "2026-07-18T00:45:00Z",
        "receipts": receipts,
    }


SLICE_SHAS = {
    "S215": "d3fc6503b90b70e519f8c3062cd7bc7c7df35a7a",
    "S216": "2d7ae98f14d80e8191a54c971daa57dea122420d",
    "S217": "22488058f80228f714367231ee2d030948f0ca2e",
}
# Map a slice task (FIX-215/216/217) to its accepted subject symbol.
SLICE_SYMBOL_BY_TASK = {"FIX-215": "S215", "FIX-216": "S216", "FIX-217": "S217"}
PARENT_SHAS = {
    "S215": "6a78b12000000000000000000000000000000000",
    "S216": SLICE_SHAS["S215"],
    "S217": SLICE_SHAS["S216"],
}
CANDIDATE_SHA = "c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0"


def make_subjects(include_c: bool = False, candidate_sha: str = CANDIDATE_SHA,
                  path_set_sha: str = "a" * 64) -> Dict[str, Any]:
    subjects: Dict[str, Any] = {}
    for symbol in ("S215", "S216", "S217"):
        subjects[symbol] = {
            "sha": SLICE_SHAS[symbol],
            "created_at": "2026-07-18T01:30:00Z",
            "owner": f"/root/fix{symbol[1:]}_dev",
            "parents": [PARENT_SHAS[symbol]],
            "path_set_sha256": path_set_sha,
        }
    subjects["T"] = None
    if include_c:
        subjects["C"] = {
            "sha": candidate_sha,
            "created_at": "2026-07-18T10:00:00Z",
            "owner": "/root/rel063_producer",
            "parents": [SLICE_SHAS["S217"]],
            "path_set_sha256": path_set_sha,
        }
    return subjects


def make_attempts() -> List[Dict[str, Any]]:
    out = []
    for task, sha, parent, code_digest, qa_digest in [
        ("FIX-215", SLICE_SHAS["S215"], PARENT_SHAS["S215"], "c1" * 32, "a1" * 32),
        ("FIX-216", SLICE_SHAS["S216"], PARENT_SHAS["S216"], "c2" * 32, "a2" * 32),
        ("FIX-217", SLICE_SHAS["S217"], PARENT_SHAS["S217"], "c3" * 32, "a3" * 32),
    ]:
        out.append({
            "task_id": task, "attempt_no": 1, "sha": sha, "parent_sha": parent,
            "created_at": "2026-07-18T01:00:00Z", "terminal_result": "ACCEPTED",
            "code_report_sha256": code_digest, "qa_report_sha256": qa_digest,
        })
    return out


def make_topology(include_c: bool = False, phase: str = "provisional",
                  candidate_sha: str = CANDIDATE_SHA) -> Dict[str, Any]:
    return {
        "schema_version": v.TOPOLOGY_SCHEMA_VERSION,
        "phase": phase,
        "observed_at": "2026-07-18T09:00:00Z",
        "subjects": make_subjects(include_c=include_c, candidate_sha=candidate_sha),
        "attempts": make_attempts(),
    }


def make_rehearsal_primary(candidate_sha: str = CANDIDATE_SHA,
                           generated_at: str = "2026-07-18T11:00:00Z") -> Dict[str, Any]:
    return {
        "schema_version": v.REHEARSAL_PRIMARY_SCHEMA_VERSION,
        "producer_role": "QA",
        "producer_id": "/root/rel063_rehearsal_qa",
        "subject_sha": candidate_sha,
        "tag_type": "annotated",
        "fixture": "positive",
        "result": "PASS",
        "raw_exit": 0,
        "writes": 0,
        "workspace_identity": "UNCHANGED",
        "real_origin_invocations": 0,
        "sequential_fallbacks": 0,
        "precondition_sha256": "0a" * 32,
        "a_master_sha": "1b" * 20,
        "a_tag_object_sha": "2c" * 20,
        "a_tag_peel_sha": CANDIDATE_SHA,
        "abort_absent": True,
        "fallback_sha": "3d" * 20,
        "rto_seconds": 30,
        "generated_at": generated_at,
    }


def make_rehearsal_sidecar(primary: Mapping[str, Any], primary_path: str,
                           primary_digest: str) -> Dict[str, Any]:
    return {
        "schema_version": v.REHEARSAL_SIDECAR_SCHEMA_VERSION,
        "report_path": primary_path,
        "report_sha256": primary_digest,
        "receipt_id": "rcpt-rehearsal",
        "producer_role": primary["producer_role"],
        "producer_id": primary["producer_id"],
        "subject_sha": primary["subject_sha"],
        "result": primary["result"],
        "generated_at": primary["generated_at"],
    }


class AuthorityTree:
    """Builds a synthetic .governance authority tree on disk for hermetic tests."""

    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.root = tmp

    def write_authority(self, authority: Mapping[str, Any]) -> None:
        path = self.root / ".governance/review-authority/REL-063/authority-input.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        write_canonical(path, authority)

    def write_receipts(self, receipts: Mapping[str, Any]) -> None:
        path = self.root / ".governance/review-authority/REL-063/orchestration-receipts.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        write_canonical(path, receipts)

    def write_topology(self, topology: Mapping[str, Any]) -> None:
        path = self.root / ".governance/review-authority/REL-063/topology-record.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        write_canonical(path, topology)

    def write_artifact(self, artifact_id: str, primary: Mapping[str, Any],
                       sidecar: Mapping[str, Any] | None = None) -> str:
        primary_path = self.root / v.ARTIFACT_PRIMARY_PATH[artifact_id]
        primary_path.parent.mkdir(parents=True, exist_ok=True)
        digest = write_canonical(primary_path, primary)
        if sidecar is None:
            sidecar = make_sidecar(artifact_id, primary, v.ARTIFACT_PRIMARY_PATH[artifact_id], digest)
        sidecar_path = self.root / v.ARTIFACT_SIDECAR_PATH[artifact_id]
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        write_canonical(sidecar_path, sidecar)
        return digest

    def write_rehearsal(self, primary: Mapping[str, Any],
                        sidecar: Mapping[str, Any] | None = None) -> str:
        primary_path = self.root / ".governance/primary-review-evidence/REL-063/atomic-rehearsal.json"
        primary_path.parent.mkdir(parents=True, exist_ok=True)
        digest = write_canonical(primary_path, primary)
        if sidecar is None:
            sidecar = make_rehearsal_sidecar(primary, ".governance/primary-review-evidence/REL-063/atomic-rehearsal.json", digest)
        sidecar_path = self.root / ".governance/review-evidence/REL-063/atomic-rehearsal.json"
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        write_canonical(sidecar_path, sidecar)
        return digest

    def remove_artifact(self, artifact_id: str) -> None:
        for rel in (v.ARTIFACT_PRIMARY_PATH[artifact_id], v.ARTIFACT_SIDECAR_PATH[artifact_id]):
            p = self.root / rel
            if p.exists():
                p.unlink()

    def ctx(self, git_runner=None) -> GitCtx:
        return GitCtx(root=self.root, git=git_runner or _NoTagGit())


class _NoTagGit:
    """Fake Git runner: slice commits resolve with linear ancestry, no tags, no remote tags.

    The fake also models the transitive ancestor relation derived from its
    `parents` map (used by `git merge-base --is-ancestor`) and a per-(parent,child)
    path-delta map (used by the slice-chain path-set guard's `git diff
    --name-only parent..child`). Subclasses override `parents`/`diff_paths` to
    model the R0+accepted-child compensation topology.
    """

    def __init__(self) -> None:
        self.parents = {
            SLICE_SHAS["S215"]: [PARENT_SHAS["S215"]],
            SLICE_SHAS["S216"]: [SLICE_SHAS["S215"]],
            SLICE_SHAS["S217"]: [SLICE_SHAS["S216"]],
        }
        # Map "parent..child" -> list of changed paths. Default empty (direct
        # parent chains have an empty delta here; subclasses populate it for
        # R0->accepted-child modeling and the path-set guard).
        self.diff_paths: Dict[str, List[str]] = {}

    def _ancestors(self, commit: str) -> set:
        """Transitive closure of ancestors (excluding the commit itself)."""
        seen: set = set()
        stack = list(self.parents.get(commit, []))
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(self.parents.get(current, []))
        return seen

    def __call__(self, args: Sequence[str], root: Path, timeout: int) -> Tuple[int, str, str]:
        joined = " ".join(args)
        args = list(args)
        # rev-parse --verify <value>^{commit}
        if args[:2] == ["rev-parse", "--verify"] and len(args) >= 3:
            value = args[2]
            resolved = _resolve_symbol(value)
            if resolved:
                return 0, resolved, ""
            return 128, "", f"unknown ref {value}"
        # show -s --format=%P <commit>
        if args[:3] == ["show", "-s", "--format=%P"] and len(args) >= 4:
            commit = args[3]
            parents = self.parents.get(commit, [])
            return 0, " ".join(parents), ""
        # merge-base --is-ancestor <ancestor> <descendant>
        # ctx.run("merge-base","--is-ancestor",a,b) -> args has length 4.
        if args[:2] == ["merge-base", "--is-ancestor"] and len(args) >= 4:
            ancestor = args[-2]
            descendant = args[-1]
            if ancestor == descendant or ancestor in self._ancestors(descendant):
                return 0, "", ""
            return 1, "", ""
        # diff --name-only [parent..child | --cached ...]
        if args[:2] == ["diff", "--name-only"]:
            if "--cached" in args:
                return 0, "", ""
            spec = args[-1]
            if ".." in spec:
                return 0, "\n".join(self.diff_paths.get(spec, [])), ""
            return 0, "", ""
        # ls-remote --exit-code: always ABSENT (no remote tags/master)
        if args[:2] == ["ls-remote", "--exit-code"]:
            return 2, "", ""
        # rev-parse tag verification: absent
        if args[:3] == ["rev-parse", "--verify", "--quiet"]:
            return 1, "", ""
        # cat-file -t: absent
        if args[:2] == ["cat-file", "-t"]:
            return 128, "", "absent"
        return 1, "", f"unhandled git call: {joined}"


def _resolve_symbol(value: str) -> str | None:
    # Strip peel suffixes (^{commit}, ^{}, ^commit) for symbol lookup.
    base = value
    for suffix in ("^{commit}", "^{tag}", "^{}", "^commit"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    symbols = {**SLICE_SHAS, "C": CANDIDATE_SHA}
    if base in symbols:
        return symbols[base]
    if base in symbols.values():
        return base
    # Accept any well-formed 40-hex SHA (synthetic commit identities).
    import re
    if re.fullmatch(r"[0-9a-f]{40}", base):
        return base
    return None


class FakeGitWithCandidate(_NoTagGit):
    """Extends _NoTagGit to model candidate C sole-parent B and path-set diffs."""

    def __init__(self, *, c_paths: Sequence[str], t_paths: Sequence[str] | None = None,
                 c_parent: str = SLICE_SHAS["S217"], c_sha: str = CANDIDATE_SHA,
                 t_sha: str = "d" * 40, parents: Mapping[str, List[str]] | None = None) -> None:
        self.c_paths = list(c_paths)
        self.t_paths = list(t_paths) if t_paths is not None else None
        self.c_parent = c_parent
        self.c_sha = c_sha
        self.t_sha = t_sha
        self.parents = dict(parents or {CANDIDATE_SHA: [SLICE_SHAS["S217"]], t_sha: [c_sha]})
        for sym, sha in SLICE_SHAS.items():
            if sym == "S215":
                self.parents.setdefault(sha, [PARENT_SHAS["S215"]])
            else:
                self.parents.setdefault(sha, [SLICE_SHAS["S215"] if sym == "S216" else SLICE_SHAS["S216"]])
        self.staged: List[str] = []
        # Per-(parent,child) delta map; empty by default (direct-parent slice
        # chains and candidate/transition cases handled above). New ancestry
        # tests inject entries here to model R0->accepted-child deltas.
        self.diff_paths: Dict[str, List[str]] = {}

    def __call__(self, args: Sequence[str], root: Path, timeout: int) -> Tuple[int, str, str]:
        args = list(args)
        if args[:3] == ["show", "-s", "--format=%P"] and len(args) >= 4:
            commit = args[3]
            parents = self.parents.get(commit, [])
            return 0, " ".join(parents), ""
        if args[:2] == ["diff", "--name-only"]:
            # diff --name-only parent..child  OR  diff --cached --name-only [...]
            if "--cached" in args:
                return 0, "\n".join(self.staged), ""
            # parent..child
            spec = args[-1]
            if ".." in spec:
                # Honor any explicitly injected per-(parent,child) delta first
                # (used by slice-chain path-set-guard tests).
                if spec in self.diff_paths:
                    return 0, "\n".join(self.diff_paths[spec]), ""
                parent, child = spec.split("..", 1)
                if child == self.c_sha and parent == self.c_parent:
                    return 0, "\n".join(self.c_paths), ""
                if self.t_paths is not None and child == self.t_sha:
                    return 0, "\n".join(self.t_paths), ""
            return 0, "", ""
        return super().__call__(args, root, timeout)


# ---------------------------------------------------------------------------
# Canonical JSON rule (section 6.1).
# ---------------------------------------------------------------------------

class CanonicalJsonTests(unittest.TestCase):
    def test_sorted_compact_nfc_trailing_lf(self):
        raw = canonical_json_bytes({"b": 1, "a": "é"})
        self.assertTrue(raw.endswith(b"\n"))
        self.assertEqual(raw.decode("utf-8"), '{"a":"é","b":1}\n')

    def test_bom_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.json"
            p.write_bytes(b'\xef\xbb\xbf{"a":1}\n')
            with self.assertRaises(EvidenceError) as cm:
                v.load_canonical(p)
            self.assertEqual(cm.exception.code, "CANONICAL_BYTES")

    def test_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.json"
            p.write_bytes(b'{"a":1,"a":2}\n')
            with self.assertRaises(EvidenceError) as cm:
                v.load_canonical(p)
            self.assertEqual(cm.exception.code, "DUPLICATE")

    def test_nan_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.json"
            p.write_bytes(b'{"a":NaN}\n')
            with self.assertRaises(EvidenceError) as cm:
                v.load_canonical(p)
            self.assertEqual(cm.exception.code, "TYPE_DRIFT")

    def test_non_canonical_bytes_rejected(self):
        # Non-sorted keys, extra whitespace -> must fail canonical roundtrip.
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.json"
            p.write_bytes(b'{"b": 1, "a": 2}\n')
            with self.assertRaises(EvidenceError) as cm:
                v.load_canonical(p)
            self.assertEqual(cm.exception.code, "CANONICAL_BYTES")

    def test_missing_trailing_lf_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.json"
            p.write_bytes(b'{"a":1}')
            with self.assertRaises(EvidenceError) as cm:
                v.load_canonical(p)
            self.assertEqual(cm.exception.code, "CANONICAL_BYTES")


# ---------------------------------------------------------------------------
# Primary/sidecar validation (section 6.2 E1).
# ---------------------------------------------------------------------------

class PrimaryReportTests(unittest.TestCase):
    def test_valid_primary_passes(self):
        primary = make_primary("FIX-215-code", SLICE_SHAS["S215"])
        result = v.validate_primary_report(primary, "FIX-215-code")
        self.assertEqual(result["result"], "APPROVED")

    def test_missing_required_field(self):
        primary = make_primary("FIX-215-code", SLICE_SHAS["S215"])
        del primary["subject_sha"]
        with self.assertRaises(EvidenceError) as cm:
            v.validate_primary_report(primary, "FIX-215-code")
        self.assertEqual(cm.exception.code, "SCHEMA_MISSING")

    def test_unknown_field_rejected(self):
        primary = make_primary("FIX-215-code", SLICE_SHAS["S215"])
        primary["extra"] = "x"
        with self.assertRaises(EvidenceError) as cm:
            v.validate_primary_report(primary, "FIX-215-code")
        self.assertEqual(cm.exception.code, "SCHEMA_UNKNOWN")

    def test_wrong_task_id_rejected(self):
        primary = make_primary("FIX-215-code", SLICE_SHAS["S215"])
        primary["task_id"] = "FIX-216"
        with self.assertRaises(EvidenceError) as cm:
            v.validate_primary_report(primary, "FIX-215-code")
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_wrong_evidence_kind_rejected(self):
        primary = make_primary("FIX-215-code", SLICE_SHAS["S215"])
        primary["evidence_kind"] = "qa"
        with self.assertRaises(EvidenceError) as cm:
            v.validate_primary_report(primary, "FIX-215-code")
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_wrong_producer_role_rejected(self):
        primary = make_primary("FIX-215-qa", SLICE_SHAS["S215"])
        primary["producer_role"] = "Code Reviewer"
        with self.assertRaises(EvidenceError) as cm:
            v.validate_primary_report(primary, "FIX-215-qa")
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_wrong_result_rejected(self):
        primary = make_primary("FIX-215-code", SLICE_SHAS["S215"])
        primary["result"] = "PASS"  # code_review must be APPROVED/APPROVED_WITH_NOTES
        with self.assertRaises(EvidenceError) as cm:
            v.validate_primary_report(primary, "FIX-215-code")
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_unresolved_blockers_nonzero_rejected(self):
        primary = make_primary("FIX-215-code", SLICE_SHAS["S215"])
        primary["unresolved_blockers"] = 1
        with self.assertRaises(EvidenceError) as cm:
            v.validate_primary_report(primary, "FIX-215-code")
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_blockers_bool_rejected_as_type_drift(self):
        primary = make_primary("FIX-215-code", SLICE_SHAS["S215"])
        primary["unresolved_blockers"] = True
        with self.assertRaises(EvidenceError) as cm:
            v.validate_primary_report(primary, "FIX-215-code")
        self.assertEqual(cm.exception.code, "TYPE_DRIFT")

    def test_bad_subject_sha_rejected(self):
        primary = make_primary("FIX-215-code", SLICE_SHAS["S215"])
        primary["subject_sha"] = "XYZ"
        with self.assertRaises(EvidenceError) as cm:
            v.validate_primary_report(primary, "FIX-215-code")
        self.assertEqual(cm.exception.code, "TYPE_DRIFT")

    def test_subject_sha_mismatch_rejected(self):
        primary = make_primary("FIX-215-code", SLICE_SHAS["S215"])
        with self.assertRaises(EvidenceError) as cm:
            v.validate_primary_report(primary, "FIX-215-code", expected_subject_sha="b" * 40)
        self.assertEqual(cm.exception.code, "DIGEST_MISMATCH")

    def test_release_authorized_true_for_non_release_review_rejected(self):
        primary = make_primary("FIX-215-code", SLICE_SHAS["S215"])
        primary["release_authorized"] = True
        with self.assertRaises(EvidenceError) as cm:
            v.validate_primary_report(primary, "FIX-215-code")
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_release_authorized_false_for_release_review_rejected(self):
        primary = make_primary("release-review", CANDIDATE_SHA, release_authorized=False)
        with self.assertRaises(EvidenceError) as cm:
            v.validate_primary_report(primary, "release-review")
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_bad_generated_at_rejected(self):
        primary = make_primary("FIX-215-code", SLICE_SHAS["S215"])
        primary["generated_at"] = "2026-07-18T02:01:38"  # missing Z
        with self.assertRaises(EvidenceError) as cm:
            v.validate_primary_report(primary, "FIX-215-code")
        self.assertEqual(cm.exception.code, "TYPE_DRIFT")

    def test_non_nfc_string_rejected(self):
        primary = make_primary("FIX-215-code", SLICE_SHAS["S215"])
        primary["producer_id"] = "é"  # precomposed, but force a non-NFC variant
        primary["producer_id"] = "e\u0301"  # decomposed NFD -> not NFC
        with self.assertRaises(EvidenceError) as cm:
            v.validate_primary_report(primary, "FIX-215-code")
        self.assertEqual(cm.exception.code, "CANONICAL_BYTES")


class SidecarTests(unittest.TestCase):
    def test_valid_sidecar_passes(self):
        primary = make_primary("FIX-215-code", SLICE_SHAS["S215"])
        sidecar = make_sidecar("FIX-215-code", primary, v.ARTIFACT_PRIMARY_PATH["FIX-215-code"], "d" * 64)
        v.validate_sidecar(sidecar, primary, "FIX-215-code", v.ARTIFACT_PRIMARY_PATH["FIX-215-code"])

    def test_report_path_is_independent_of_primary_path(self):
        # report_path points at the markdown review report, not the primary
        # JSON; validate_sidecar accepts any canonical repo-relative string.
        primary = make_primary("FIX-215-code", SLICE_SHAS["S215"])
        sidecar = make_sidecar("FIX-215-code", primary, v.ARTIFACT_PRIMARY_PATH["FIX-215-code"], "d" * 64)
        sidecar["report_path"] = ".governance/review-FIX-215-CODE-R1.md"
        # validate_sidecar does not bind report_path == primary_path; that is a
        # load-time file-existence/digest concern in load_artifact_pair.
        v.validate_sidecar(sidecar, primary, "FIX-215-code", v.ARTIFACT_PRIMARY_PATH["FIX-215-code"])

    def test_repeated_field_drift_rejected(self):
        primary = make_primary("FIX-215-code", SLICE_SHAS["S215"])
        sidecar = make_sidecar("FIX-215-code", primary, v.ARTIFACT_PRIMARY_PATH["FIX-215-code"], "d" * 64)
        sidecar["result"] = "PASS"  # drift from primary APPROVED
        with self.assertRaises(EvidenceError) as cm:
            v.validate_sidecar(sidecar, primary, "FIX-215-code", v.ARTIFACT_PRIMARY_PATH["FIX-215-code"])
        self.assertEqual(cm.exception.code, "DIGEST_MISMATCH")

    def test_bad_report_sha256_rejected(self):
        primary = make_primary("FIX-215-code", SLICE_SHAS["S215"])
        sidecar = make_sidecar("FIX-215-code", primary, v.ARTIFACT_PRIMARY_PATH["FIX-215-code"], "d" * 64)
        sidecar["report_sha256"] = "ZZ"
        with self.assertRaises(EvidenceError) as cm:
            v.validate_sidecar(sidecar, primary, "FIX-215-code", v.ARTIFACT_PRIMARY_PATH["FIX-215-code"])
        self.assertEqual(cm.exception.code, "TYPE_DRIFT")


# ---------------------------------------------------------------------------
# Authority / orchestration / topology (section 6.2).
# ---------------------------------------------------------------------------

class AuthorityTests(unittest.TestCase):
    def test_valid_authority_passes(self):
        authority = make_authority({"FIX-215": "/root/fix215_dev", "FIX-216": "/root/fix216_dev", "FIX-217": "/root/fix217_dev"})
        v.validate_authority_input(authority)

    def test_missing_developer_key_rejected(self):
        authority = make_authority({"FIX-215": "/root/fix215_dev", "FIX-216": "/root/fix216_dev"})
        with self.assertRaises(EvidenceError) as cm:
            v.validate_authority_input(authority)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_wrong_artifact_count_rejected(self):
        authority = make_authority({"FIX-215": "a", "FIX-216": "b", "FIX-217": "c"})
        authority["artifacts"] = authority["artifacts"][:8]
        with self.assertRaises(EvidenceError) as cm:
            v.validate_authority_input(authority)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_duplicate_artifact_id_rejected(self):
        authority = make_authority({"FIX-215": "a", "FIX-216": "b", "FIX-217": "c"})
        authority["artifacts"][8]["artifact_id"] = authority["artifacts"][0]["artifact_id"]
        with self.assertRaises(EvidenceError) as cm:
            v.validate_authority_input(authority)
        self.assertEqual(cm.exception.code, "DUPLICATE")

    def test_wrong_primary_path_rejected(self):
        authority = make_authority({"FIX-215": "a", "FIX-216": "b", "FIX-217": "c"})
        authority["artifacts"][0]["primary_path"] = "wrong"
        with self.assertRaises(EvidenceError) as cm:
            v.validate_authority_input(authority)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")


class TopologyTests(unittest.TestCase):
    def test_valid_provisional_topology_passes(self):
        topology = make_topology(include_c=False, phase="provisional")
        ctx = GitCtx(root=Path(tempfile.mkdtemp()), git=_NoTagGit())
        v.validate_topology(topology, ctx, expected_subjects={"S215", "S216", "S217"})

    def test_provisional_with_c_present_rejected_by_pre_c(self):
        # pre_c requires no C in subjects; this is enforced by run_pre_c, but
        # validate_topology itself accepts C. Test the driver-level guard below.
        topology = make_topology(include_c=True, phase="provisional")
        ctx = GitCtx(root=Path(tempfile.mkdtemp()), git=_NoTagGit())
        # validate_topology accepts C presence; the pre_c driver rejects it.
        v.validate_topology(topology, ctx, expected_subjects={"S215", "S216", "S217", "C"})

    def test_provisional_t_not_null_rejected(self):
        topology = make_topology(phase="provisional")
        topology["subjects"]["T"] = {"sha": "d" * 40, "created_at": "2026-07-18T01:00:00Z",
                                     "owner": "x", "parents": [CANDIDATE_SHA], "path_set_sha256": "a" * 64}
        ctx = GitCtx(root=Path(tempfile.mkdtemp()), git=_NoTagGit())
        v.validate_topology(topology, ctx, expected_subjects={"S215", "S216", "S217"})
        # The provisional T-not-null guard lives in run_pre_c (see PhaseDriverTests).

    def test_missing_subject_rejected(self):
        topology = make_topology(phase="provisional")
        del topology["subjects"]["S217"]
        ctx = GitCtx(root=Path(tempfile.mkdtemp()), git=_NoTagGit())
        with self.assertRaises(EvidenceError) as cm:
            v.validate_topology(topology, ctx, expected_subjects={"S215", "S216", "S217"})
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_duplicate_attempt_no_rejected(self):
        topology = make_topology(phase="provisional")
        topology["attempts"].append(dict(topology["attempts"][0]))
        ctx = GitCtx(root=Path(tempfile.mkdtemp()), git=_NoTagGit())
        with self.assertRaises(EvidenceError) as cm:
            v.validate_topology(topology, ctx, expected_subjects={"S215", "S216", "S217"})
        self.assertEqual(cm.exception.code, "DUPLICATE")

    def test_wrong_phase_rejected(self):
        # load_topology_record enforces the expected_phase contract.
        tmp = Path(tempfile.mkdtemp())
        authority_dir = tmp / ".governance/review-authority/REL-063"
        authority_dir.mkdir(parents=True)
        write_canonical(authority_dir / "topology-record.json", make_topology(phase="provisional"))
        ctx = GitCtx(root=tmp, git=_NoTagGit())
        with self.assertRaises(EvidenceError) as cm:
            v.load_topology_record(ctx, expected_phase="full")
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_two_accepted_attempts_for_one_slice_rejected(self):
        topology = make_topology(phase="provisional")
        # Add a second ACCEPTED attempt for FIX-215.
        dup = dict(topology["attempts"][0])
        dup["attempt_no"] = 2
        topology["attempts"].append(dup)
        # Re-sort by (task_id, attempt_no)
        topology["attempts"].sort(key=lambda a: (a["task_id"], a["attempt_no"]))
        ctx = GitCtx(root=Path(tempfile.mkdtemp()), git=_NoTagGit())
        with self.assertRaises(EvidenceError) as cm:
            v.validate_topology(topology, ctx, expected_subjects={"S215", "S216", "S217"})
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_attempts_unordered_rejected(self):
        topology = make_topology(phase="provisional")
        topology["attempts"].reverse()
        ctx = GitCtx(root=Path(tempfile.mkdtemp()), git=_NoTagGit())
        with self.assertRaises(EvidenceError) as cm:
            v.validate_topology(topology, ctx, expected_subjects={"S215", "S216", "S217"})
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")


# ---------------------------------------------------------------------------
# Slice chain ancestry (C3 / R1).
# ---------------------------------------------------------------------------

class SliceChainTests(unittest.TestCase):
    def test_valid_linear_chain_passes(self):
        topology = make_topology(phase="provisional")
        ctx = GitCtx(root=Path(tempfile.mkdtemp()), git=_NoTagGit())
        v.validate_slice_chain(ctx, topology, ["S215", "S216", "S217"])

    def test_wrong_parent_rejected(self):
        topology = make_topology(phase="provisional")
        # Break S216 Git ancestry: model S216's direct parent as a commit that
        # is NOT a descendant of S215, so `merge-base --is-ancestor S215 S216`
        # returns false. The topology `parents` field is recorded but no longer
        # equality-checked; the rejection now comes from the Git ancestry query.
        topology["subjects"]["S216"]["parents"] = ["0" * 40]
        git = _NoTagGit()
        git.parents[SLICE_SHAS["S216"]] = ["0" * 40]
        ctx = GitCtx(root=Path(tempfile.mkdtemp()), git=git)
        with self.assertRaises(EvidenceError) as cm:
            v.validate_slice_chain(ctx, topology, ["S215", "S216", "S217"])
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_wrong_chain_spec_rejected(self):
        topology = make_topology(phase="provisional")
        ctx = GitCtx(root=Path(tempfile.mkdtemp()), git=_NoTagGit())
        # The parser rejects anything other than S215,S216,S217 at the CLI; here
        # we validate the ancestry directly with a reordered chain.
        with self.assertRaises(EvidenceError):
            v.validate_slice_chain(ctx, topology, ["S216", "S215", "S217"])


# ---------------------------------------------------------------------------
# Acyclic-ancestry slice chain (DEC-129 / FIX-219 Option A).
# ---------------------------------------------------------------------------

# R0 compensation commit SHAs used by the ancestry tests. Each R0 sits between
# an accepted slice and the next accepted slice (the documented compensation-
# retry topology). S215 has no R0 in front of it for these fixtures.
R0_216_SHA = "19b2a17000000000000000000000000000000000"
R0_217_SHA = "d2df3b66000000000000000000000000000000000"


def _ancestry_git(*, extra_parents: Mapping[str, List[str]] | None = None,
                  diff_paths: Mapping[str, List[str]] | None = None,
                  drop_s216_ancestor: bool = False) -> _NoTagGit:
    """Build a _NoTagGit modeling the real R0+accepted-child compensation chain.

    Topology modeled:
        S215 (parent=incident head) <- accepted
        R0_216 (parent=S215) ; S216 (parent=R0_216) <- accepted
        R0_217 (parent=S216) ; S217 (parent=R0_217) <- accepted

    This makes S215 an ancestor of S216 and S217 (transitively), exactly as the
    real Git history in the investigation report confirms. Set
    `drop_s216_ancestor=True` to detach S216 from S215 (negative-ancestry case).
    """
    git = _NoTagGit()
    parents = {
        SLICE_SHAS["S215"]: [PARENT_SHAS["S215"]],
        R0_216_SHA: [SLICE_SHAS["S215"]],
        SLICE_SHAS["S216"]: [R0_216_SHA],
        R0_217_SHA: [SLICE_SHAS["S216"]],
        SLICE_SHAS["S217"]: [R0_217_SHA],
    }
    if drop_s216_ancestor:
        # Detach S216 so it does NOT descend from S215.
        parents[SLICE_SHAS["S216"]] = ["0" * 40]
    if extra_parents:
        parents.update(extra_parents)
    git.parents = parents
    git.diff_paths = dict(diff_paths or {})
    return git


def _ancestry_topology(*, s216_parents: List[str] | None = None,
                       s217_parents: List[str] | None = None) -> Dict[str, Any]:
    """Build a provisional topology whose subjects declare the R0 parents
    (the documented compensation record-fidelity shape)."""
    topology = make_topology(phase="provisional")
    topology["subjects"]["S216"]["parents"] = list(s216_parents or [R0_216_SHA])
    topology["subjects"]["S217"]["parents"] = list(s217_parents or [R0_217_SHA])
    return topology


class AncestrySliceChainTests(unittest.TestCase):
    """DEC-129 / FIX-219 Option A: acyclic ancestry + path-set guard.

    These tests model the real R0+accepted-child compensation topology and
    verify (1) it now PASSES, (2) out-of-scope R0 deltas are rejected by the
    new path-set guard, (3) the four C3 threats (combined path, wrong parent,
    reused subject, no ancestry) remain caught, and (4) the old direct-parent
    chain still passes (backward compatibility / strict generalization).
    """

    def test_r0_plus_accepted_child_passes(self):
        # Real compensation pattern: each accepted child's direct parent is its
        # R0, and each R0 descends from the prior accepted slice. The R0->child
        # deltas are strict subsets of each slice's M-union-N scope.
        topology = _ancestry_topology()
        git = _ancestry_git(diff_paths={
            f"{R0_216_SHA}..{SLICE_SHAS['S216']}": [
                "skills/software-project-governance/infra/checks/loop_runtime_claim_attestation.py",
                "skills/software-project-governance/infra/tests/test_loop_runtime_claim_attestation.py",
            ],
            f"{R0_217_SHA}..{SLICE_SHAS['S217']}": [
                "skills/software-project-governance/infra/release/ledger.py",
                "skills/software-project-governance/infra/tests/test_release_ledger.py",
            ],
        })
        ctx = GitCtx(root=Path(tempfile.mkdtemp()), git=git)
        v.validate_slice_chain(ctx, topology, ["S215", "S216", "S217"])

    def test_r0_delta_out_of_scope_rejected(self):
        # The S216 R0->accepted-child delta includes a path outside M216-union-N216.
        topology = _ancestry_topology()
        git = _ancestry_git(diff_paths={
            f"{R0_216_SHA}..{SLICE_SHAS['S216']}": [
                "skills/software-project-governance/infra/checks/loop_runtime_claim_attestation.py",
                "skills/software-project-governance/infra/release/ledger.py",  # belongs to M217, not S216
            ],
            f"{R0_217_SHA}..{SLICE_SHAS['S217']}": [
                "skills/software-project-governance/infra/release/ledger.py",
            ],
        })
        ctx = GitCtx(root=Path(tempfile.mkdtemp()), git=git)
        with self.assertRaises(EvidenceError) as cm:
            v.validate_slice_chain(ctx, topology, ["S215", "S216", "S217"])
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")
        self.assertIn("outside declared slice scope", cm.exception.detail)

    def test_r0_delta_in_scope_passes(self):
        # Strict subset (not the full M-union-N) still passes.
        topology = _ancestry_topology()
        git = _ancestry_git(diff_paths={
            f"{R0_216_SHA}..{SLICE_SHAS['S216']}": [
                "skills/software-project-governance/infra/tests/test_loop_runtime_claim_attestation.py",
            ],
            f"{R0_217_SHA}..{SLICE_SHAS['S217']}": [
                "skills/software-project-governance/infra/release/model.py",
            ],
        })
        ctx = GitCtx(root=Path(tempfile.mkdtemp()), git=git)
        v.validate_slice_chain(ctx, topology, ["S215", "S216", "S217"])

    def test_no_ancestry_rejected(self):
        # S216 does NOT descend from S215 (merge-base --is-ancestor returns 1).
        # The R0->child delta is in-scope, so only the ancestry check rejects.
        topology = _ancestry_topology()
        git = _ancestry_git(
            drop_s216_ancestor=True,
            diff_paths={
                f"{'0'*40}..{SLICE_SHAS['S216']}": [
                    "skills/software-project-governance/infra/checks/loop_runtime_claim_attestation.py",
                ],
                f"{R0_217_SHA}..{SLICE_SHAS['S217']}": [
                    "skills/software-project-governance/infra/release/ledger.py",
                ],
            },
        )
        # R0_217 still descends from S216 in the parents map, so the only break
        # is the S215->S216 ancestry edge.
        ctx = GitCtx(root=Path(tempfile.mkdtemp()), git=git)
        with self.assertRaises(EvidenceError) as cm:
            v.validate_slice_chain(ctx, topology, ["S215", "S216", "S217"])
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")
        self.assertIn("is not an ancestor", cm.exception.detail)

    def test_reused_subject_rejected(self):
        # A back-edge: S216's ancestry includes itself (cycle). Model S216's
        # parent chain so that S216 is its own ancestor (reused-subject / cycle).
        topology = _ancestry_topology()
        git = _ancestry_git()
        # Make S216 a parent of itself transitively: point R0_216 back at S216.
        git.parents[R0_216_SHA] = [SLICE_SHAS["S216"]]
        git.diff_paths = {
            f"{R0_216_SHA}..{SLICE_SHAS['S216']}": [
                "skills/software-project-governance/infra/checks/loop_runtime_claim_attestation.py",
            ],
            f"{R0_217_SHA}..{SLICE_SHAS['S217']}": [
                "skills/software-project-governance/infra/release/ledger.py",
            ],
        }
        ctx = GitCtx(root=Path(tempfile.mkdtemp()), git=git)
        with self.assertRaises(EvidenceError) as cm:
            v.validate_slice_chain(ctx, topology, ["S215", "S216", "S217"])
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_direct_parent_chain_still_passes(self):
        # Backward compatibility: the old-style direct-parent chain (no R0)
        # still passes. _NoTagGit() models exactly this linear chain, and the
        # direct-parent->child delta defaults to empty (a subset of any scope).
        topology = make_topology(phase="provisional")
        ctx = GitCtx(root=Path(tempfile.mkdtemp()), git=_NoTagGit())
        v.validate_slice_chain(ctx, topology, ["S215", "S216", "S217"])

    def test_path_set_guard_catches_combined_path_threat(self):
        # Cross-slice contamination: S216's R0 introduces a path from S217's
        # scope (ledger.py), smuggling another slice's work. Ancestry holds, so
        # only the path-set guard catches this C3 "combined path" threat.
        topology = _ancestry_topology()
        git = _ancestry_git(diff_paths={
            f"{R0_216_SHA}..{SLICE_SHAS['S216']}": [
                "skills/software-project-governance/infra/checks/loop_runtime_claim_attestation.py",
                "skills/software-project-governance/infra/release/ledger.py",  # S217 scope, not S216
                "skills/software-project-governance/infra/tests/test_release_ledger.py",  # S217 scope
            ],
            f"{R0_217_SHA}..{SLICE_SHAS['S217']}": [
                "skills/software-project-governance/infra/release/ledger.py",
            ],
        })
        ctx = GitCtx(root=Path(tempfile.mkdtemp()), git=git)
        with self.assertRaises(EvidenceError) as cm:
            v.validate_slice_chain(ctx, topology, ["S215", "S216", "S217"])
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")
        self.assertIn("outside declared slice scope", cm.exception.detail)


# ---------------------------------------------------------------------------
# Distinct role sets (R2: self-review / four-record forge).
# ---------------------------------------------------------------------------

class DistinctRoleSetsTests(unittest.TestCase):
    def _build_loaded(self, producer_map: Mapping[str, str]) -> Dict[str, Dict[str, Any]]:
        loaded: Dict[str, Dict[str, Any]] = {}
        for aid in v.NINE_ARTIFACT_IDS:
            primary = make_primary(aid, CANDIDATE_SHA, producer_id=producer_map[aid])
            loaded[aid] = {"primary": primary}
        return loaded

    def test_distinct_roles_pass(self):
        producers = {aid: f"/root/{aid}" for aid in v.NINE_ARTIFACT_IDS}
        loaded = self._build_loaded(producers)
        authority = make_authority({"FIX-215": "/root/d215", "FIX-216": "/root/d216", "FIX-217": "/root/d217"},
                                   producer_overrides=producers)
        validated = v.validate_authority_input(authority)
        roles = v.validate_distinct_role_sets(loaded, validated)
        # 3 slice code reviewers + 1 exact-C-code reviewer = 4 Code Reviewer producers.
        self.assertEqual(len(roles["code_reviewers"]), 4)
        # 3 slice QA + 1 exact-C-qa = 4 QA producers.
        self.assertEqual(len(roles["qa"]), 4)
        self.assertEqual(len(roles["release_reviewers"]), 1)
        # All role sets mutually disjoint.
        self.assertFalse(set(roles["code_reviewers"]) & set(roles["qa"]))
        self.assertFalse(set(roles["release_reviewers"]) & (set(roles["code_reviewers"]) | set(roles["qa"])))

    def test_self_review_cr_equals_qa_rejected(self):
        producers = {aid: f"/root/{aid}" for aid in v.NINE_ARTIFACT_IDS}
        producers["FIX-215-qa"] = producers["FIX-215-code"]  # CR == QA
        loaded = self._build_loaded(producers)
        authority = make_authority({"FIX-215": "/root/d215", "FIX-216": "/root/d216", "FIX-217": "/root/d217"},
                                   producer_overrides=producers)
        validated = v.validate_authority_input(authority)
        with self.assertRaises(EvidenceError) as cm:
            v.validate_distinct_role_sets(loaded, validated)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_release_reviewer_overlap_rejected(self):
        producers = {aid: f"/root/{aid}" for aid in v.NINE_ARTIFACT_IDS}
        producers["release-review"] = producers["FIX-215-code"]  # RR overlaps CR
        loaded = self._build_loaded(producers)
        authority = make_authority({"FIX-215": "/root/d215", "FIX-216": "/root/d216", "FIX-217": "/root/d217"},
                                   producer_overrides=producers)
        validated = v.validate_authority_input(authority)
        with self.assertRaises(EvidenceError) as cm:
            v.validate_distinct_role_sets(loaded, validated)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_developer_is_reviewer_rejected(self):
        producers = {aid: f"/root/{aid}" for aid in v.NINE_ARTIFACT_IDS}
        loaded = self._build_loaded(producers)
        authority = make_authority({"FIX-215": producers["FIX-215-code"], "FIX-216": "/root/d216", "FIX-217": "/root/d217"},
                                   producer_overrides=producers)
        validated = v.validate_authority_input(authority)
        with self.assertRaises(EvidenceError) as cm:
            v.validate_distinct_role_sets(loaded, validated)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_producer_diverges_from_authority_rejected(self):
        producers = {aid: f"/root/{aid}" for aid in v.NINE_ARTIFACT_IDS}
        loaded = self._build_loaded(producers)
        # Authority pins a different producer for FIX-215-code.
        authority_producers = dict(producers)
        authority_producers["FIX-215-code"] = "/root/different"
        authority = make_authority({"FIX-215": "/root/d215", "FIX-216": "/root/d216", "FIX-217": "/root/d217"},
                                   producer_overrides=authority_producers)
        validated = v.validate_authority_input(authority)
        with self.assertRaises(EvidenceError) as cm:
            v.validate_distinct_role_sets(loaded, validated)
        self.assertEqual(cm.exception.code, "DIGEST_MISMATCH")


# ---------------------------------------------------------------------------
# FIX-213 supersession + scanner limit (C5).
# ---------------------------------------------------------------------------

class Fix213SupersessionTests(unittest.TestCase):
    def test_eight_second_ceiling_passes(self):
        loaded = {aid: {"primary": make_primary(aid, SLICE_SHAS["S215"])} for aid in v.SIX_SLICE_ARTIFACT_IDS}
        result = v.validate_fix213_supersession(loaded, 8.0)
        self.assertEqual(result["scanner_limit_seconds"], 8.0)

    def test_non_eight_second_ceiling_rejected(self):
        loaded = {aid: {"primary": make_primary(aid, SLICE_SHAS["S215"])} for aid in v.SIX_SLICE_ARTIFACT_IDS}
        with self.assertRaises(EvidenceError) as cm:
            v.validate_fix213_supersession(loaded, 7.0)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_stale_five_second_ceiling_rejected(self):
        loaded = {aid: {"primary": make_primary(aid, SLICE_SHAS["S215"])} for aid in v.SIX_SLICE_ARTIFACT_IDS}
        with self.assertRaises(EvidenceError) as cm:
            v.validate_fix213_supersession(loaded, 5.0)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_missing_slice_artifact_rejected(self):
        loaded = {aid: {"primary": make_primary(aid, SLICE_SHAS["S215"])} for aid in v.SIX_SLICE_ARTIFACT_IDS[:5]}
        with self.assertRaises(EvidenceError) as cm:
            v.validate_fix213_supersession(loaded, 8.0)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")


# ---------------------------------------------------------------------------
# Rehearsal report (R7 / section 6.3).
# ---------------------------------------------------------------------------

class RehearsalTests(unittest.TestCase):
    def test_valid_rehearsal_passes(self):
        primary = make_rehearsal_primary()
        v.validate_rehearsal_primary(primary, CANDIDATE_SHA)

    def test_non_annotated_tag_rejected(self):
        primary = make_rehearsal_primary()
        primary["tag_type"] = "lightweight"
        with self.assertRaises(EvidenceError) as cm:
            v.validate_rehearsal_primary(primary, CANDIDATE_SHA)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_workspace_drift_rejected(self):
        primary = make_rehearsal_primary()
        primary["workspace_identity"] = "CHANGED"
        with self.assertRaises(EvidenceError) as cm:
            v.validate_rehearsal_primary(primary, CANDIDATE_SHA)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_rto_breach_rejected(self):
        primary = make_rehearsal_primary()
        primary["rto_seconds"] = 901
        with self.assertRaises(EvidenceError) as cm:
            v.validate_rehearsal_primary(primary, CANDIDATE_SHA)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_sequential_fallback_rejected(self):
        primary = make_rehearsal_primary()
        primary["sequential_fallbacks"] = 1
        with self.assertRaises(EvidenceError) as cm:
            v.validate_rehearsal_primary(primary, CANDIDATE_SHA)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_subject_sha_mismatch_rejected(self):
        primary = make_rehearsal_primary()
        with self.assertRaises(EvidenceError) as cm:
            v.validate_rehearsal_primary(primary, "e" * 40)
        self.assertEqual(cm.exception.code, "DIGEST_MISMATCH")


# ---------------------------------------------------------------------------
# Path-set resolution and assertions.
# ---------------------------------------------------------------------------

class PathSetTests(unittest.TestCase):
    def test_m063_n063_union_is_23(self):
        resolved = v.resolve_path_set("M063,N063")
        self.assertEqual(len(resolved), 23)

    def test_m063_is_15(self):
        self.assertEqual(len(v.resolve_path_set("M063")), 15)

    def test_n063_is_8(self):
        self.assertEqual(len(v.resolve_path_set("N063")), 8)

    def test_assert_path_set_extra_rejected(self):
        expected = ["a", "b"]
        with self.assertRaises(EvidenceError) as cm:
            v.assert_path_set(["a", "b", "c"], expected, 2, "test")
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_assert_path_set_missing_rejected(self):
        expected = ["a", "b"]
        with self.assertRaises(EvidenceError) as cm:
            v.assert_path_set(["a"], expected, 2, "test")
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_assert_path_set_exact_passes(self):
        expected = ["a", "b"]
        v.assert_path_set(["a", "b"], expected, 2, "test")


# ---------------------------------------------------------------------------
# Candidate manifest recovery_evidence binding (section 6.5).
# ---------------------------------------------------------------------------

class CandidateManifestTests(unittest.TestCase):
    def test_candidate_manifest_has_recovery_evidence_phase_candidate(self):
        recovery = v.build_candidate_recovery_evidence(
            subjects={"S215": {"sha": SLICE_SHAS["S215"]}},
            reports={"FIX-215-code": {"primary_sha256": "a" * 64}},
            artifact_blobs={"FIX-215-code": ".governance/primary-review-evidence/REL-063/FIX-215-code.json"},
            provisional_root="b" * 64,
            frozen_at="2026-07-18T01:00:00Z",
        )
        manifest = v.candidate_manifest(recovery)
        self.assertEqual(manifest["version"], "0.66.2")
        self.assertEqual(manifest["lifecycle_state"], "candidate")
        self.assertEqual(manifest["recovery_evidence"]["phase"], "candidate")
        self.assertIsNone(manifest["recovery_evidence"]["rehearsal_sha256"])
        self.assertIsNone(manifest["recovery_evidence"]["full_root"])
        self.assertEqual(manifest["recovery_evidence"]["schema_version"], v.RELEASE_BINDING_SCHEMA_VERSION)

    def test_candidate_manifest_is_canonical(self):
        recovery = v.build_candidate_recovery_evidence(
            subjects={"S215": {"sha": SLICE_SHAS["S215"]}}, reports={},
            artifact_blobs={}, provisional_root="b" * 64, frozen_at="2026-07-18T01:00:00Z",
        )
        manifest = v.candidate_manifest(recovery)
        raw = canonical_json_bytes(manifest)
        # Roundtrip must be stable.
        self.assertEqual(raw, canonical_json_bytes(json.loads(raw.decode("utf-8"))))

    def test_candidate_manifest_excludes_c_self_reference(self):
        recovery = v.build_candidate_recovery_evidence(
            subjects={"S215": {"sha": SLICE_SHAS["S215"]}}, reports={},
            artifact_blobs={}, provisional_root="b" * 64, frozen_at="2026-07-18T01:00:00Z",
        )
        manifest = v.candidate_manifest(recovery)
        # Candidate subjects must be only S215/S216/S217 — never C.
        self.assertNotIn("C", manifest["recovery_evidence"]["subjects"])


# ---------------------------------------------------------------------------
# End-to-end phase drivers via synthetic authority tree.
# ---------------------------------------------------------------------------

class PreCDriverTests(unittest.TestCase):
    def _setup(self) -> Tuple[AuthorityTree, FakeGitWithCandidate]:
        tmp = Path(tempfile.mkdtemp())
        tree = AuthorityTree(tmp)
        developers = {"FIX-215": "/root/fix215_dev", "FIX-216": "/root/fix216_dev", "FIX-217": "/root/fix217_dev"}
        producers = {aid: f"/root/{aid}_prod" for aid in v.NINE_ARTIFACT_IDS}
        authority = make_authority(developers, producer_overrides=producers)
        receipts = make_receipts(authority)
        topology = make_topology(phase="provisional")
        tree.write_authority(authority)
        tree.write_receipts(receipts)
        tree.write_topology(topology)
        for aid in v.SIX_SLICE_ARTIFACT_IDS:
            symbol = SLICE_SYMBOL_BY_TASK[v.TASK_BY_ARTIFACT[aid]]
            tree.write_artifact(aid, make_primary(aid, SLICE_SHAS[symbol], producer_id=producers[aid]))
        git = FakeGitWithCandidate(c_paths=[])
        return tree, git

    def test_pre_c_passes_and_writes_candidate_manifest(self):
        tree, git = self._setup()
        ctx = tree.ctx(git)
        out_manifest = tree.root / "skills/software-project-governance/core/releases/0.66.2.json"
        args = _NS(phase="pre_c", require_slice_chain="S215,S216,S217",
                   require_artifacts=",".join(v.SIX_SLICE_ARTIFACT_IDS),
                   require_artifact_count=6,
                   forbid_artifacts=",".join(v.PRE_C_FORBIDDEN_ARTIFACT_IDS),
                   require_transition_absent=True,
                   require_local_tag_absent=["v0.66.2"],
                   require_remote_tag_absent=["origin:v0.66.2"],
                   write_candidate_manifest=str(out_manifest))
        rc = v.run_pre_c(ctx, args)
        self.assertEqual(rc, v.EXIT_PASS)
        self.assertTrue(out_manifest.exists())
        manifest = json.loads(out_manifest.read_bytes())
        self.assertEqual(manifest["lifecycle_state"], "candidate")
        self.assertEqual(manifest["recovery_evidence"]["phase"], "candidate")

    def test_pre_c_rejects_exact_c_evidence_present(self):
        tree, git = self._setup()
        # Create an exact-C evidence file — forbidden at pre_c.
        tree.write_artifact("exact-C-code", make_primary("exact-C-code", CANDIDATE_SHA))
        ctx = tree.ctx(git)
        args = _NS(phase="pre_c", require_slice_chain="S215,S216,S217",
                   require_artifacts=",".join(v.SIX_SLICE_ARTIFACT_IDS),
                   require_artifact_count=6,
                   forbid_artifacts=",".join(v.PRE_C_FORBIDDEN_ARTIFACT_IDS),
                   require_transition_absent=True)
        with self.assertRaises(EvidenceError) as cm:
            v.run_pre_c(ctx, args)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_pre_c_rejects_local_tag_present(self):
        tree, _ = self._setup()
        git = FakeGitWithCandidate(c_paths=[])
        git_tag = _LocalTagPresentGit()
        ctx = tree.ctx(git_tag)
        args = _NS(phase="pre_c", require_slice_chain="S215,S216,S217",
                   require_artifacts=",".join(v.SIX_SLICE_ARTIFACT_IDS),
                   require_artifact_count=6,
                   forbid_artifacts=",".join(v.PRE_C_FORBIDDEN_ARTIFACT_IDS),
                   require_transition_absent=True,
                   require_local_tag_absent=["v0.66.2"])
        with self.assertRaises(EvidenceError) as cm:
            v.run_pre_c(ctx, args)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_pre_c_rejects_missing_authority(self):
        tree, git = self._setup()
        # Remove the authority file.
        (tree.root / ".governance/review-authority/REL-063/authority-input.json").unlink()
        ctx = tree.ctx(git)
        args = _NS(phase="pre_c", require_slice_chain="S215,S216,S217",
                   require_artifacts=",".join(v.SIX_SLICE_ARTIFACT_IDS),
                   require_artifact_count=6,
                   forbid_artifacts=",".join(v.PRE_C_FORBIDDEN_ARTIFACT_IDS),
                   require_transition_absent=True)
        with self.assertRaises(EvidenceError) as cm:
            v.run_pre_c(ctx, args)
        self.assertEqual(cm.exception.code, "UNKNOWN")


class _LocalTagPresentGit(_NoTagGit):
    def __call__(self, args, root, timeout):
        args = list(args)
        if args[:3] == ["rev-parse", "--verify", "--quiet"] and len(args) >= 4 and "refs/tags/v0.66.2" in args[3]:
            return 0, "d" * 40, ""
        return super().__call__(args, root, timeout)


class StagedAndTopologyTests(unittest.TestCase):
    def test_assert_staged_path_set_23_passes(self):
        tmp = Path(tempfile.mkdtemp())
        git = FakeGitWithCandidate(c_paths=[])
        git.staged = list(v.M063) + list(v.N063)
        ctx = GitCtx(root=tmp, git=git)
        # Also need diff --cached <base> to return the same set.
        git_diff = _StagedDiffGit(git.staged)
        ctx2 = GitCtx(root=tmp, git=git_diff)
        args = _NS(assert_staged_path_set="M063,N063", base=SLICE_SHAS["S217"], require_path_count=23)
        rc = v.run_assert_staged(ctx2, args)
        self.assertEqual(rc, v.EXIT_PASS)

    def test_assert_staged_extra_path_rejected(self):
        tmp = Path(tempfile.mkdtemp())
        staged = list(v.M063) + list(v.N063) + ["forbidden/path.md"]
        git = _StagedDiffGit(staged)
        ctx = GitCtx(root=tmp, git=git)
        args = _NS(assert_staged_path_set="M063,N063", base=SLICE_SHAS["S217"], require_path_count=23)
        with self.assertRaises(EvidenceError) as cm:
            v.run_assert_staged(ctx, args)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_assert_candidate_topology_23_paths_passes(self):
        tmp = Path(tempfile.mkdtemp())
        c_paths = list(v.M063) + list(v.N063)
        git = FakeGitWithCandidate(c_paths=c_paths)
        ctx = GitCtx(root=tmp, git=git)
        args = _NS(assert_candidate_topology=True, candidate=CANDIDATE_SHA,
                   parent=SLICE_SHAS["S217"], require_path_set="M063,N063", require_path_count=23)
        rc = v.run_assert_candidate_topology(ctx, args)
        self.assertEqual(rc, v.EXIT_PASS)

    def test_assert_candidate_topology_wrong_parent_rejected(self):
        tmp = Path(tempfile.mkdtemp())
        c_paths = list(v.M063) + list(v.N063)
        git = FakeGitWithCandidate(c_paths=c_paths, parents={CANDIDATE_SHA: ["0" * 40]})
        ctx = GitCtx(root=tmp, git=git)
        args = _NS(assert_candidate_topology=True, candidate=CANDIDATE_SHA,
                   parent=SLICE_SHAS["S217"], require_path_set="M063,N063", require_path_count=23)
        with self.assertRaises(EvidenceError) as cm:
            v.run_assert_candidate_topology(ctx, args)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_assert_candidate_topology_wrong_count_rejected(self):
        tmp = Path(tempfile.mkdtemp())
        # Only 22 paths.
        c_paths = (list(v.M063) + list(v.N063))[:22]
        git = FakeGitWithCandidate(c_paths=c_paths)
        ctx = GitCtx(root=tmp, git=git)
        args = _NS(assert_candidate_topology=True, candidate=CANDIDATE_SHA,
                   parent=SLICE_SHAS["S217"], require_path_set="M063,N063", require_path_count=23)
        with self.assertRaises(EvidenceError) as cm:
            v.run_assert_candidate_topology(ctx, args)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_assert_transition_topology_one_path_passes(self):
        tmp = Path(tempfile.mkdtemp())
        t_sha = "7e" * 20
        git = FakeGitWithCandidate(c_paths=[], t_paths=["skills/software-project-governance/core/releases/0.66.2.json"],
                                   t_sha=t_sha)
        # Write an empty manifest so forbid-self-reference byte scan succeeds.
        (tmp / "skills/software-project-governance/core/releases").mkdir(parents=True, exist_ok=True)
        (tmp / "skills/software-project-governance/core/releases/0.66.2.json").write_bytes(b'{"version":"0.66.2"}\n')
        ctx = GitCtx(root=tmp, git=git)
        args = _NS(assert_transition_topology=True, transition=t_sha, parent=CANDIDATE_SHA,
                   require_path_set="skills/software-project-governance/core/releases/0.66.2.json",
                   require_path_count=1, forbid_self_reference=True)
        rc = v.run_assert_transition_topology(ctx, args)
        self.assertEqual(rc, v.EXIT_PASS)


class _StagedDiffGit:
    def __init__(self, staged: Sequence[str]) -> None:
        self.staged = list(staged)

    def __call__(self, args, root, timeout):
        args = list(args)
        if args[:1] == ["diff"] and "--cached" in args:
            return 0, "\n".join(self.staged), ""
        if args[:2] == ["rev-parse", "--verify"] and len(args) >= 3:
            resolved = _resolve_symbol(args[2])
            if resolved:
                return 0, resolved, ""
            return 128, "", f"unknown ref {args[2]}"
        return 1, "", "unhandled"


class NS:
    """A simple namespace for argparse-free driver invocation."""

    def __init__(self, **kwargs: Any) -> None:
        self.__dict__.update(kwargs)

    def __getattr__(self, name: str) -> Any:
        # Return sensible defaults for unspecified optional flags.
        if name in ("require_release_review", "require_rehearsal", "require_distinct_role_sets",
                    "require_fix213_supersession", "require_transition_authorized",
                    "require_fresh_topology", "require_fresh_platform", "reject_provisional_cache",
                    "require_all_nine", "require_transition_absent", "require_no_rollback_trigger",
                    "require_full_manifest_pre_t", "forbid_self_reference", "quiet"):
            return False
        if name in ("require_local_tag_absent", "require_remote_tag_absent",
                    "require_local_tag", "require_remote_tag", "require_tag_absent"):
            return []
        if name in ("scanner_limit_seconds", "observe_seconds"):
            return None
        if name in ("write_full_manifest", "write_candidate_manifest", "write_observation",
                    "write_precondition", "write_report", "candidate", "transition",
                    "require_release_authorized", "parent"):
            return None
        raise AttributeError(name)


def _NS(**kwargs: Any) -> NS:
    return NS(**kwargs)


class CandidateDriverTests(unittest.TestCase):
    def _setup(self) -> Tuple[AuthorityTree, FakeGitWithCandidate]:
        tmp = Path(tempfile.mkdtemp())
        tree = AuthorityTree(tmp)
        developers = {"FIX-215": "/root/fix215_dev", "FIX-216": "/root/fix216_dev", "FIX-217": "/root/fix217_dev"}
        producers = {aid: f"/root/{aid}_prod" for aid in v.NINE_ARTIFACT_IDS}
        authority = make_authority(developers, producer_overrides=producers)
        receipts = make_receipts(authority)
        topology = make_topology(include_c=True, phase="provisional")
        tree.write_authority(authority)
        tree.write_receipts(receipts)
        tree.write_topology(topology)
        for aid in v.SIX_SLICE_ARTIFACT_IDS:
            symbol = SLICE_SYMBOL_BY_TASK[v.TASK_BY_ARTIFACT[aid]]
            tree.write_artifact(aid, make_primary(aid, SLICE_SHAS[symbol], producer_id=producers[aid]))
        tree.write_artifact("exact-C-code", make_primary("exact-C-code", CANDIDATE_SHA, producer_id=producers["exact-C-code"]))
        tree.write_artifact("exact-C-qa", make_primary("exact-C-qa", CANDIDATE_SHA, producer_id=producers["exact-C-qa"]))
        tree.write_artifact("release-review", make_primary("release-review", CANDIDATE_SHA, producer_id=producers["release-review"],
                                                            generated_at="2026-07-18T12:00:00Z"))
        tree.write_rehearsal(make_rehearsal_primary())
        git = FakeGitWithCandidate(c_paths=[])
        return tree, git

    def test_candidate_phase_passes_with_rehearsal_and_review(self):
        tree, git = self._setup()
        ctx = tree.ctx(git)
        args = _NS(phase="candidate", candidate=CANDIDATE_SHA,
                   require_slice_chain="S215,S216,S217",
                   require_all_nine=True, require_rehearsal=True, require_release_review=True,
                   require_distinct_role_sets=True, require_fix213_supersession=True,
                   scanner_limit_seconds=8.0, require_transition_authorized=True,
                   require_release_authorized="false")
        rc = v.run_candidate(ctx, args)
        self.assertEqual(rc, v.EXIT_PASS)

    def test_candidate_rejects_release_authorized_true(self):
        tree, git = self._setup()
        ctx = tree.ctx(git)
        args = _NS(phase="candidate", candidate=CANDIDATE_SHA,
                   require_slice_chain="S215,S216,S217",
                   require_all_nine=True, require_rehearsal=True, require_release_review=True,
                   require_distinct_role_sets=True, require_fix213_supersession=True,
                   scanner_limit_seconds=8.0, require_transition_authorized=True,
                   require_release_authorized="true")
        with self.assertRaises(EvidenceError) as cm:
            v.run_candidate(ctx, args)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")

    def test_candidate_rejects_review_before_rehearsal(self):
        tree, git = self._setup()
        producers = {aid: f"/root/{aid}_prod" for aid in v.NINE_ARTIFACT_IDS}
        # Move release-review generated_at before rehearsal generated_at.
        rr = make_primary("release-review", CANDIDATE_SHA, generated_at="2026-07-18T10:00:00Z",
                          producer_id=producers["release-review"])
        tree.write_artifact("release-review", rr)
        ctx = tree.ctx(git)
        args = _NS(phase="candidate", candidate=CANDIDATE_SHA,
                   require_slice_chain="S215,S216,S217",
                   require_all_nine=True, require_rehearsal=True, require_release_review=True,
                   require_distinct_role_sets=True, require_fix213_supersession=True,
                   scanner_limit_seconds=8.0, require_transition_authorized=True,
                   require_release_authorized="false")
        with self.assertRaises(EvidenceError) as cm:
            v.run_candidate(ctx, args)
        self.assertEqual(cm.exception.code, "PHASE_DRIFT")


class CliRoutingTests(unittest.TestCase):
    def test_flat_phase_form_detected(self):
        self.assertTrue(v._is_flat_phase_form(["--phase", "pre_c", "--candidate", "x"]))
        self.assertFalse(v._is_flat_phase_form(["phase-pre_c"]))

    def test_main_returns_reject_on_unknown_phase_flag(self):
        # Missing required --phase should fail with SystemExit from argparse.
        with self.assertRaises(SystemExit):
            v.main(["--phase", "bogus"])

    def test_flat_assert_selectors_detected_without_phase(self):
        # The exact_commands contract invokes --assert-staged-path-set,
        # --assert-candidate-topology, and --assert-transition-topology as
        # leading --flags WITHOUT a --phase token. These must route to the
        # flat parser, not the subcommand parser (regression: previously the
        # first value was rejected as an invalid subcommand choice).
        self.assertTrue(v._is_flat_phase_form(
            ["--assert-staged-path-set", "M063,N063", "--base", "B", "--require-path-count", "23"]))
        self.assertTrue(v._is_flat_phase_form(
            ["--assert-candidate-topology", "--candidate", "C", "--parent", "B",
             "--require-path-set", "M063,N063", "--require-path-count", "23"]))
        self.assertTrue(v._is_flat_phase_form(
            ["--assert-transition-topology", "--transition", "T", "--parent", "C",
             "--require-path-set", "skills/software-project-governance/core/releases/0.66.2.json",
             "--require-path-count", "1", "--forbid-self-reference"]))

    def test_flat_tag_and_push_selectors_detected_without_phase(self):
        # --verify-local-tag, --verify-push-preconditions, and
        # --verify-atomic-push-result are leading --flags without --phase.
        self.assertTrue(v._is_flat_phase_form(
            ["--verify-local-tag", "--tag", "v0.66.2", "--expected-type", "annotated",
             "--expected-peel", "T"]))
        self.assertTrue(v._is_flat_phase_form(
            ["--verify-push-preconditions", "--remote", "origin", "--expected-master", "B",
             "--require-tag-absent", "v0.66.2", "--expected-local-tag-peel", "T",
             "--write-precondition", "out.json"]))
        self.assertTrue(v._is_flat_phase_form(
            ["--verify-atomic-push-result", "--precondition", "p.json",
             "--expected-pre-master", "B", "--expected-master", "T", "--tag", "v0.66.2",
             "--expected-tag-type", "annotated", "--expected-tag-peel", "T",
             "--remote", "origin", "--forbid-partial", "--forbid-sequential-fallback",
             "--unsupported-is-no-go"]))

    def test_flat_completion_unittests_selector_detected_without_phase(self):
        self.assertTrue(v._is_flat_phase_form(
            ["--run-completion-unittests", "--test-root", "tests", "--pattern", "test_*.py"]))

    def test_subcommand_tokens_still_route_to_subcommand_parser(self):
        # Bare subcommand tokens (no leading --) must NOT be treated as flat.
        for token in ("assert-staged-path-set", "assert-candidate-topology",
                      "verify-local-tag", "run-completion-unittests", "phase-pre_c"):
            self.assertFalse(v._is_flat_phase_form([token, "--base", "B"]))

    def test_assert_staged_flat_routes_to_driver_not_subcommand_error(self):
        # Regression: the flat --assert-staged-path-set form used to be
        # rejected by the subcommand parser as "invalid choice: 'M063,N063'".
        # It must now reach the staged-path driver (fail closed with a nonzero
        # evidence exit) rather than argparse SystemExit. In an empty temp
        # repo the git fact query is UNKNOWN, but the key contract is that the
        # flat flag was parsed and dispatched, not rejected by argparse.
        with tempfile.TemporaryDirectory() as tmp:
            rc = v.main(["--repo-root", tmp, "--assert-staged-path-set", "M063,N063",
                         "--base", "B", "--require-path-count", "23"])
        self.assertNotEqual(rc, v.EXIT_PASS)
        self.assertIn(rc, (v.EXIT_REJECT, v.EXIT_UNKNOWN))


if __name__ == "__main__":
    unittest.main()
