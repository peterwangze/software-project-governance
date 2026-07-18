"""FIX-197 fail-closed semantic claim-gate tests."""

import argparse
import hashlib
import io
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
import tracemalloc
import unicodedata
import unittest
from datetime import datetime, timedelta, timezone
from collections import Counter
from pathlib import Path, PurePosixPath
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_INFRA = _HERE.parent
if str(_INFRA) not in sys.path:
    sys.path.insert(0, str(_INFRA))

import checks.loop_runtime_claims as lrc  # noqa: E402
from checks.loop_runtime_claims import (  # noqa: E402
    ClaimScanContext,
    ScanLimits,
    _content_digest,
    _policy_digest,
    _recheck_inventory,
    _safe_join,
    _safe_relative,
    enumerate_candidates,
    scan_loop_runtime_claims,
)


ACTIVE_RULES = [
    {"claim_class": name, "claim_id": claim_id, "status": "forbidden_current"}
    for name, claim_id in lrc.REQUIRED_RULES.items()
]

FIX215_TIMING_SCHEMA = "fix215.scanner-timing-report.v1"
FIX215_TIMING_KEYS = {
    "schema_version", "fixture_only", "subject_sha", "command_sha256", "host_identity",
    "started_at", "ended_at", "elapsed_seconds", "raw_exit", "test_count", "skip_count",
    "legacy_limit_seconds", "legacy_evidence_rejected", "limit_seconds_exclusive",
    "semantic_verdict", "timing_verdict", "verdict",
}
FIX215_MUTABLE_PATHS = (
    "skills/software-project-governance/core/loop-runtime-claim-allowlist.json",
    "skills/software-project-governance/core/loop-runtime-claim-authority.json",
    "skills/software-project-governance/infra/checks/loop_runtime_claims.py",
    "skills/software-project-governance/infra/tests/test_loop_runtime_claims.py",
    "skills/software-project-governance/core/task-gate-model.md",
    "project/e2e-test-project/skills/software-project-governance/core/task-gate-model.md",
)
_FIX215_TIMING_ROOTS = None


def _canonical_json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def _parse_utc(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("UTC timestamp must end in Z")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo != timezone.utc:
        raise ValueError("UTC timestamp required")
    return parsed


def _validate_fix215_timing_report(report, *, expected_subject, expected_command_sha256,
                                   expected_host_identity, now=None):
    codes = []
    if not isinstance(report, dict):
        return ["TYPE_DRIFT"]
    missing = FIX215_TIMING_KEYS - set(report)
    unknown = set(report) - FIX215_TIMING_KEYS
    if missing:
        codes.append("SCHEMA_MISSING")
    if unknown:
        codes.append("SCHEMA_UNKNOWN")
    if report.get("schema_version") != FIX215_TIMING_SCHEMA:
        codes.append("SCHEMA_VERSION_DRIFT")
    if report.get("fixture_only") is not False:
        codes.append("FIXTURE_ONLY_FORBIDDEN")
    if report.get("subject_sha") != expected_subject:
        codes.append("SUBJECT_MISMATCH")
    if report.get("command_sha256") != expected_command_sha256:
        codes.append("COMMAND_MISMATCH")
    if report.get("host_identity") != expected_host_identity:
        codes.append("HOST_MISMATCH")
    raw_exit = report.get("raw_exit")
    test_count = report.get("test_count")
    skip_count = report.get("skip_count")
    elapsed = report.get("elapsed_seconds")
    if isinstance(raw_exit, bool) or not isinstance(raw_exit, int):
        codes.append("TYPE_DRIFT")
    elif raw_exit != 0:
        codes.append("SCANNER_NONZERO")
    if isinstance(test_count, bool) or not isinstance(test_count, int):
        codes.append("TYPE_DRIFT")
    elif test_count <= 0:
        codes.append("TESTS_INCOMPLETE")
    if isinstance(skip_count, bool) or not isinstance(skip_count, int):
        codes.append("TYPE_DRIFT")
    elif skip_count != 0:
        codes.append("UNEXPECTED_SKIP")
    if report.get("legacy_limit_seconds") != 5.0 or report.get("legacy_evidence_rejected") is not True:
        codes.append("LEGACY_EVIDENCE_NOT_REJECTED")
    if report.get("limit_seconds_exclusive") != 8.0:
        codes.append("TIMING_LIMIT_DRIFT")
    if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)):
        codes.append("TYPE_DRIFT")
    elif elapsed < 0 or elapsed >= 8.0:
        codes.append("TIMING_LIMIT_EXCEEDED")
    semantic = report.get("semantic_verdict")
    if semantic == "UNKNOWN":
        codes.append("SEMANTIC_UNKNOWN")
    elif semantic != "PASS":
        codes.append("SEMANTIC_NOT_PASS")
    if report.get("timing_verdict") != "PASS":
        codes.append("TIMING_NOT_PASS")
    if report.get("verdict") != "PASS":
        codes.append("VERDICT_NOT_PASS")
    try:
        started = _parse_utc(report.get("started_at"))
        ended = _parse_utc(report.get("ended_at"))
        current = now or datetime.now(timezone.utc)
        if started > ended or ended > current + timedelta(seconds=5):
            codes.append("TIME_ORDER_INVALID")
        if current - ended > timedelta(minutes=5):
            codes.append("STALE_EVIDENCE")
        if isinstance(elapsed, (int, float)) and not isinstance(elapsed, bool):
            if abs((ended - started).total_seconds() - elapsed) > 0.25:
                codes.append("ELAPSED_MISMATCH")
    except (TypeError, ValueError):
        codes.append("TIME_INVALID")
    return list(dict.fromkeys(codes))


def _host_identity(project_root):
    project_root = Path(project_root)
    source_records = []
    codes = []
    try:
        resolved_root = project_root.resolve(strict=True)
    except OSError:
        resolved_root = project_root.resolve()
        codes.append("HOST_SOURCE_MISSING")
    for relative_path in lrc.HOT_PATHS:
        target = project_root / relative_path
        try:
            resolved = target.resolve(strict=True)
            resolved.relative_to(resolved_root)
            if target.is_symlink() or not resolved.is_file():
                raise OSError("host source is not a safe regular file")
            raw = resolved.read_bytes()
            source_records.append({
                "path": relative_path,
                "raw_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            })
        except (OSError, ValueError):
            source_records.append({"path": relative_path, "state": "UNAVAILABLE"})
            codes.append("HOST_SOURCE_MISSING")
    facts = {
        "machine": platform.machine(),
        "node": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "host_sources": source_records,
    }
    identity = hashlib.sha256(_canonical_json_bytes(facts)[:-1]).hexdigest()
    return identity, list(dict.fromkeys(codes))


def _real_repository_roots():
    if _FIX215_TIMING_ROOTS is None:
        product_root = _INFRA.parents[2]
        project_root = product_root
    else:
        product_root, project_root = _FIX215_TIMING_ROOTS
    product_root = Path(product_root)
    project_root = Path(project_root)
    return (
        product_root,
        product_root / "skills/software-project-governance",
        project_root,
    )


def _command_sha256(tokens):
    return hashlib.sha256(_canonical_json_bytes(list(tokens))[:-1]).hexdigest()


def _fix215_parser():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--fix215-qa-timing", action="store_true", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--product-root", required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--scan-mode", choices=("product_release", "installed_host"), required=True)
    parser.add_argument("--limit-seconds-exclusive", type=float, required=True)
    parser.add_argument("--reject-legacy-limit-seconds", type=float, required=True)
    parser.add_argument("--require-tests-complete", action="store_true")
    parser.add_argument("--require-skip-count", type=int, required=True)
    parser.add_argument("--write-report", required=True)
    return parser


def _emit_fix215_gate(codes):
    print(json.dumps({
        "schema_version": "fix215.scanner-timing-gate.v1",
        "gate_codes": list(codes),
        "verdict": "FAIL",
    }, sort_keys=True, separators=(",", ":")), file=sys.stderr)


def _subject_candidate_oids(product_root, subject):
    listed = subprocess.run(
        ["git", "ls-tree", "-r", "-z", subject, "--", "docs", "project", "skills"],
        cwd=product_root, capture_output=True,
    )
    if listed.returncode != 0:
        return None, ["SUBJECT_INPUT_INVENTORY_UNKNOWN"]
    object_ids = {}
    try:
        records = [record for record in listed.stdout.split(b"\0") if record]
        for record in records:
            metadata, encoded_path = record.split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split()
            path = unicodedata.normalize("NFC", encoded_path.decode("utf-8"))
            if PurePosixPath(path).suffix.lower() not in lrc.SUPPORTED_EXTENSIONS:
                continue
            if object_type != "blob" or mode not in {"100644", "100755"} or path in object_ids:
                return None, ["SUBJECT_INPUT_INVENTORY_MISMATCH"]
            object_ids[path] = object_id
    except (UnicodeDecodeError, ValueError):
        return None, ["SUBJECT_INPUT_INVENTORY_UNKNOWN"]
    return object_ids, []


def _verify_exact_subject_candidate_closure(product_root, subject):
    expected, expected_codes = _subject_candidate_oids(product_root, subject)
    if expected_codes:
        return expected_codes
    plugin_home = product_root / "skills/software-project-governance"
    inventory, inventory_findings = enumerate_candidates(
        ClaimScanContext(product_root, plugin_home, None, "product_release"), ScanLimits()
    )
    if inventory_findings:
        return ["SUBJECT_INPUT_INVENTORY_MISMATCH"]
    actual = {
        candidate.normalized_path: candidate.raw
        for candidate in inventory.files
        if candidate.root_owner == "product_root"
    }
    canonical_path = FIX215_MUTABLE_PATHS[4]
    projection_path = FIX215_MUTABLE_PATHS[5]
    if expected is None or canonical_path not in expected:
        return ["SUBJECT_INPUT_INVENTORY_MISMATCH"]
    if projection_path in expected or projection_path not in actual:
        return ["SUBJECT_INPUT_INVENTORY_MISMATCH"]
    if set(actual) != set(expected) | {projection_path}:
        return ["SUBJECT_INPUT_INVENTORY_MISMATCH"]
    tracked_diff = subprocess.run(
        [
            "git", "diff", "--quiet", "--no-ext-diff", subject, "--",
            "docs", "project", "skills",
        ],
        cwd=product_root, capture_output=True,
    )
    if tracked_diff.returncode == 1:
        return ["SUBJECT_INPUT_INVENTORY_MISMATCH"]
    if tracked_diff.returncode != 0:
        return ["SUBJECT_INPUT_INVENTORY_UNKNOWN"]
    if actual[projection_path] != actual[canonical_path]:
        return ["SUBJECT_PROJECTION_MISMATCH"]
    if actual[canonical_path].count(b"IDENTITY_ATTESTATION_PENDING") != 1:
        return ["IDENTITY_PENDING_DRIFT"]
    return []


def _resolve_clean_fix215_subject(product_root, requested):
    if not isinstance(requested, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", requested):
        return None, ["SUBJECT_FORMAT_INVALID"]
    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", f"{requested}^{{commit}}"], cwd=product_root,
        capture_output=True, text=True, encoding="utf-8",
    )
    if resolved.returncode != 0:
        return None, ["SUBJECT_UNRESOLVED"]
    subject = resolved.stdout.strip().lower()
    if subject != requested:
        return None, ["SUBJECT_MISMATCH"]
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=product_root,
        capture_output=True, text=True, encoding="utf-8",
    )
    if head.returncode != 0 or head.stdout.strip().lower() != subject:
        return None, ["SUBJECT_NOT_HEAD"]
    closure_codes = _verify_exact_subject_candidate_closure(product_root, subject)
    if closure_codes:
        return None, closure_codes
    return subject, []


def _run_fix215_suite(product_root, project_root):
    global _FIX215_TIMING_ROOTS
    prior_roots = _FIX215_TIMING_ROOTS
    _FIX215_TIMING_ROOTS = (Path(product_root), Path(project_root))
    try:
        stream = io.StringIO()
        suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
        result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
        return result, stream.getvalue()
    finally:
        _FIX215_TIMING_ROOTS = prior_roots


def _fix215_invocation(args, subject, product_root, project_root, report_path):
    return [
        "python", "-X", "utf8",
        "skills/software-project-governance/infra/tests/test_loop_runtime_claims.py",
        "--fix215-qa-timing", "--subject", subject,
        "--product-root", str(product_root), "--project-root", str(project_root),
        "--scan-mode", args.scan_mode,
        "--limit-seconds-exclusive", "8.0",
        "--reject-legacy-limit-seconds", "5.0",
        "--require-tests-complete", "--require-skip-count", "0",
        "--write-report", str(report_path),
    ]


def _write_fix215_provisional_failure(
        args, report_path, product_root, project_root, host_identity, codes):
    observed_at = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    invocation = _fix215_invocation(args, args.subject, product_root, project_root, report_path)
    report = {
        "schema_version": FIX215_TIMING_SCHEMA,
        "fixture_only": False,
        "subject_sha": args.subject,
        "command_sha256": _command_sha256(invocation),
        "host_identity": host_identity,
        "started_at": observed_at,
        "ended_at": observed_at,
        "elapsed_seconds": 0.0,
        "raw_exit": 3,
        "test_count": 0,
        "skip_count": 0,
        "legacy_limit_seconds": 5.0,
        "legacy_evidence_rejected": True,
        "limit_seconds_exclusive": 8.0,
        "semantic_verdict": "UNKNOWN",
        "timing_verdict": "UNKNOWN",
        "verdict": "FAIL",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(_canonical_json_bytes(report))
    _emit_fix215_gate(codes)


def _fix215_timing_main(argv):
    args = _fix215_parser().parse_args(argv)
    product_root = Path(args.product_root).resolve()
    project_root = Path(args.project_root).resolve()
    report_path = Path(args.write_report).resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    try:
        report_path.relative_to(temp_root)
    except ValueError:
        _emit_fix215_gate(["REPORT_PATH_NOT_VERIFIED_TEMP"])
        return 2
    if args.limit_seconds_exclusive != 8.0 or args.reject_legacy_limit_seconds != 5.0:
        _emit_fix215_gate(["TIMING_LIMIT_DRIFT"])
        return 2
    if not args.require_tests_complete or args.require_skip_count != 0:
        _emit_fix215_gate(["TEST_COMPLETENESS_CONTRACT_DRIFT"])
        return 2
    host_identity, host_codes = _host_identity(project_root)
    if host_codes:
        _write_fix215_provisional_failure(
            args, report_path, product_root, project_root, host_identity, host_codes
        )
        return 3
    subject, subject_codes = _resolve_clean_fix215_subject(product_root, args.subject)
    if subject_codes:
        _write_fix215_provisional_failure(
            args, report_path, product_root, project_root, host_identity, subject_codes
        )
        return 3
    result, transcript = _run_fix215_suite(product_root, project_root)
    skip_count = len(result.skipped)
    if not result.wasSuccessful() or result.testsRun <= 0 or skip_count != args.require_skip_count:
        _emit_fix215_gate([
            "TESTS_INCOMPLETE" if not result.wasSuccessful() or result.testsRun <= 0 else "UNEXPECTED_SKIP"
        ])
        print(transcript, file=sys.stderr)
        return 4
    pre_scan_codes = _verify_exact_subject_candidate_closure(product_root, subject)
    if pre_scan_codes:
        _write_fix215_provisional_failure(
            args, report_path, product_root, project_root, host_identity, pre_scan_codes
        )
        return 3
    scanner_command = [
        sys.executable,
        "skills/software-project-governance/infra/verify_workflow.py",
        "check-loop-runtime-claims",
        "--product-root", str(product_root),
        "--project-root", str(project_root),
        "--scan-mode", args.scan_mode,
        "--fail-on-issues",
    ]
    invocation = _fix215_invocation(args, subject, product_root, project_root, report_path)
    started_at = datetime.now(timezone.utc)
    started = time.perf_counter()
    completed = subprocess.run(
        scanner_command, cwd=product_root, capture_output=True, text=True, encoding="utf-8"
    )
    elapsed = time.perf_counter() - started
    ended_at = datetime.now(timezone.utc)
    try:
        scanner_payload = json.loads(completed.stdout)
        semantic_verdict = scanner_payload.get(
            "semantic_verdict", scanner_payload.get("verdict", "UNKNOWN")
        )
    except (json.JSONDecodeError, AttributeError):
        semantic_verdict = "UNKNOWN"
    timing_verdict = "PASS" if elapsed < args.limit_seconds_exclusive else "FAIL"
    verdict = "PASS" if completed.returncode == 0 and semantic_verdict == "PASS" and timing_verdict == "PASS" else "FAIL"
    report = {
        "schema_version": FIX215_TIMING_SCHEMA,
        "fixture_only": False,
        "subject_sha": subject,
        "command_sha256": _command_sha256(invocation),
        "host_identity": host_identity,
        "started_at": started_at.isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "ended_at": ended_at.isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "elapsed_seconds": elapsed,
        "raw_exit": completed.returncode,
        "test_count": result.testsRun,
        "skip_count": skip_count,
        "legacy_limit_seconds": 5.0,
        "legacy_evidence_rejected": True,
        "limit_seconds_exclusive": 8.0,
        "semantic_verdict": semantic_verdict,
        "timing_verdict": timing_verdict,
        "verdict": verdict,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(_canonical_json_bytes(report))
    final_closure_codes = _verify_exact_subject_candidate_closure(product_root, subject)
    final_host_identity, final_host_codes = _host_identity(project_root)
    codes = list(final_closure_codes)
    if final_closure_codes:
        report["verdict"] = "FAIL"
        report_path.write_bytes(_canonical_json_bytes(report))
    if final_host_codes or final_host_identity != host_identity:
        report["verdict"] = "FAIL"
        codes.append("HOST_SOURCE_CHANGED")
        report_path.write_bytes(_canonical_json_bytes(report))
    codes.extend(_validate_fix215_timing_report(
        report, expected_subject=subject, expected_command_sha256=_command_sha256(invocation),
        expected_host_identity=host_identity, now=ended_at,
    ))
    if codes:
        _emit_fix215_gate(codes)
        return 5
    print(report_path)
    return 0


def _fix215_cli_or_unittest():
    if "--fix215-qa-timing" in sys.argv[1:]:
        return _fix215_timing_main(sys.argv[1:])
    program = unittest.main(exit=False)
    return 0 if program.result.wasSuccessful() else 1


class LoopRuntimeClaimTests(unittest.TestCase):
    def _roots(self):
        stack = tempfile.TemporaryDirectory()
        root = Path(stack.name)
        product, plugin, host = root / "product", root / "plugin", root / "host"
        for directory in (product / "docs", product / "project", product / "skills", plugin / "core"):
            directory.mkdir(parents=True, exist_ok=True)
        gov = host / ".governance"
        gov.mkdir(parents=True)
        source_line = "| TEST-AUTHORITY | fixed |"
        for name in ("plan-tracker.md", "session-snapshot.md", "evidence-log.md", "risk-log.md"):
            (gov / name).write_text(source_line + "\n", encoding="utf-8")
        historical = "Loop " + "runtime was active in 0.65.0."
        notice = {
            "schema_version": "1.0", "notice_id": "NOTICE-1", "effective_version": "0.66.1",
            "supersedes_claim_ids": ["HIST-1"],
            "authority_ids": ["AUDIT-133", "EVD-707", "DEC-104"],
            "classification": {
                "runtime_activation": "NOT_MET", "migration_validity": "NOT_MET",
                "criteria_2_3_4_5_6": "PARTIAL", "criterion_7": "NOT_PROVEN",
                "criterion_8": "MET-NARROW", "capability": "experimental_scaffolding",
            },
            "open_risks": ["RISK-037", "RISK-042"],
        }
        history_path = product / "docs/history.md"
        history_path.write_text(
            historical + "\n\n<!-- loop-runtime-superseding:"
            + json.dumps(notice, separators=(",", ":")) + " -->\n",
            encoding="utf-8",
        )
        policy = {
            "schema_version": "1.0", "notice_schema_version": "1.0",
            "required_paths": [{"root_owner": "product_root", "path": "docs/history.md", "required": True}],
            "historical_claims": [{
                "normalized_relative_path": "docs/history.md", "claim_id": "HIST-1",
                "notice_id": "NOTICE-1", "locator": {"kind": "line", "line_number": 1, "ordinal": 1},
                "locator_sha256": hashlib.sha256(historical.encode()).hexdigest(),
                "claim_payload": historical,
                "claim_payload_sha256": hashlib.sha256(historical.encode()).hexdigest(),
                "occurrence_count": 1, "superseding_mode": "same_file",
            }],
            "active_surface_rules": json.loads(json.dumps(ACTIVE_RULES)),
            "planned_targets": [{
                "claim_id": "PLAN-1",
                "claim_classes": [
                    "persisted_back_edge", "flow_unit_loop_count", "tier_fuse",
                    "paro_transition", "automatic_escalation",
                ],
            }],
        }
        authority = {
            "schema_version": "1.0", "effective_version": "0.66.1",
            "capability": "experimental_scaffolding", "runtime_activation": "NOT_MET",
            "migration_validity": "NOT_MET", "criteria_2_3_4_5_6": "PARTIAL",
            "criterion_7": "NOT_PROVEN", "criterion_8": "MET-NARROW",
            "identity_attestation": "IDENTITY_ATTESTATION_PENDING",
            "authority_ids": ["AUDIT-133", "EVD-707", "DEC-104"],
            "open_risks": ["RISK-037", "RISK-042"], "policy_sha256": _policy_digest(policy),
            "source_records": [{
                "record_id": "TEST-AUTHORITY", "path": ".governance/plan-tracker.md",
                "line_prefix": "| TEST-AUTHORITY |",
                "sha256": hashlib.sha256(source_line.encode()).hexdigest(),
            }],
        }
        contract_patches = (
            patch.object(lrc, "REQUIRED_PATHS", {"product_root:docs/history.md"}),
            patch.object(lrc, "REQUIRED_HISTORICAL_IDS", {"HIST-1"}),
            patch.object(lrc, "REQUIRED_PLANNED_TARGETS", {"PLAN-1": frozenset(policy["planned_targets"][0]["claim_classes"])}),
            patch.object(lrc, "REQUIRED_SOURCE_IDS", {"TEST-AUTHORITY"}),
            patch.object(lrc, "REQUIRED_SOURCE_RECORDS", {
                "TEST-AUTHORITY": (".governance/plan-tracker.md", "| TEST-AUTHORITY |", hashlib.sha256(source_line.encode()).hexdigest()),
            }),
            patch.object(lrc, "REQUIRED_POLICY_SHA256", _policy_digest(policy)),
        )
        for contract_patch in contract_patches:
            contract_patch.start()
            self.addCleanup(contract_patch.stop)
        (plugin / "core/loop-runtime-claim-allowlist.json").write_text(json.dumps(policy), encoding="utf-8")
        (plugin / "core/loop-runtime-claim-authority.json").write_text(json.dumps(authority), encoding="utf-8")
        return stack, product, plugin, host, policy, authority

    def _scan(self, product, plugin, host, **kwargs):
        return scan_loop_runtime_claims(
            ClaimScanContext(product, plugin, host, kwargs.pop("mode", "product_release")),
            limits=kwargs.pop("limits", None),
        )

    def _write_controls(self, plugin, policy, authority):
        authority["policy_sha256"] = _policy_digest(policy)
        (plugin / "core/loop-runtime-claim-allowlist.json").write_text(json.dumps(policy), encoding="utf-8")
        (plugin / "core/loop-runtime-claim-authority.json").write_text(json.dumps(authority), encoding="utf-8")

    def test_clean_complete_inventory_passes(self):
        stack, product, plugin, host, _, _ = self._roots()
        self.addCleanup(stack.cleanup)
        (product / "docs/readme.md").write_text("Loop runtime is not active.\n", encoding="utf-8")
        report = self._scan(product, plugin, host)
        self.assertEqual("PASS", report.verdict, report.findings)
        self.assertEqual(report.inventory.inventory_sha256, report.final_inventory_sha256)
        self.assertEqual(report.inventory.candidate_count, report.parsed_candidates)

    def test_empty_control_sets_and_source_records_block(self):
        for key in ("required_paths", "historical_claims", "active_surface_rules"):
            with self.subTest(key=key):
                stack, product, plugin, host, policy, authority = self._roots()
                try:
                    policy[key] = []
                    self._write_controls(plugin, policy, authority)
                    report = self._scan(product, plugin, host)
                    self.assertIn("POLICY_REQUIRED_SET_EMPTY", {f.code for f in report.findings})
                finally:
                    stack.cleanup()
        stack, product, plugin, host, policy, authority = self._roots()
        self.addCleanup(stack.cleanup)
        authority["source_records"] = []
        self._write_controls(plugin, policy, authority)
        self.assertIn("AUTHORITY_SOURCE_RECORDS_EMPTY", {f.code for f in self._scan(product, plugin, host).findings})

    def test_policy_cannot_self_authorize_by_resigning_controls(self):
        stack, product, plugin, host, policy, authority = self._roots()
        self.addCleanup(stack.cleanup)
        policy["required_paths"] = []
        self._write_controls(plugin, policy, authority)
        codes = {f.code for f in self._scan(product, plugin, host).findings}
        self.assertIn("POLICY_CONTRACT_DIGEST_DRIFT", codes)
        self.assertIn("POLICY_REQUIRED_SET_EMPTY", codes)

        stack2, product2, plugin2, host2, policy2, authority2 = self._roots()
        self.addCleanup(stack2.cleanup)
        policy2["active_surface_rules"][0]["status"] = "allowed_current"
        self._write_controls(plugin2, policy2, authority2)
        codes = {f.code for f in self._scan(product2, plugin2, host2).findings}
        self.assertIn("POLICY_CONTRACT_DIGEST_DRIFT", codes)
        self.assertIn("ALLOWED_CURRENT_FORBIDDEN", codes)

    def test_historical_adjacent_affirmative_is_not_owned(self):
        stack, product, plugin, host, _, _ = self._roots()
        self.addCleanup(stack.cleanup)
        path = product / "docs/history.md"
        path.write_text(path.read_text(encoding="utf-8") + "Loop runtime is active and complete.\n", encoding="utf-8")
        report = self._scan(product, plugin, host)
        self.assertIn("UNSUPPORTED_AFFIRMATIVE", {f.code for f in report.findings})
        self.assertEqual(1, report.historical_matches)

    def test_markdown_comment_python_assignment_and_free_planned_block(self):
        stack, product, plugin, host, _, _ = self._roots()
        self.addCleanup(stack.cleanup)
        (product / "docs/comment.md").write_text(
            "<!-- Loop runtime is active and complete. -->\nLoop runtime is planned and active.\n", encoding="utf-8"
        )
        (product / "skills/claim.py").write_text(
            'def test_claim():\n    claim = "Loop runtime is active and complete."\n    return claim\n', encoding="utf-8"
        )
        report = self._scan(product, plugin, host)
        blocked = [f for f in report.findings if f.code in {
            "UNSUPPORTED_AFFIRMATIVE", "UNKNOWN_STATE_PREDICATE", "AMBIGUOUS_SEMANTIC_UNIT",
        }]
        self.assertGreaterEqual(len(blocked), 3)

    def test_structured_marker_requires_adjacent_owned_claim(self):
        stack, product, plugin, host, _, _ = self._roots()
        self.addCleanup(stack.cleanup)
        marker = '<!-- loop-runtime-target:{"claim_id":"PLAN-1","target_version":"0.68.0","status":"planned_not_active"} -->\n'
        path = product / "docs/planned.md"
        path.write_text(marker + "Persisted back-edge is enabled.\n", encoding="utf-8")
        self.assertEqual("PASS", self._scan(product, plugin, host).verdict)
        path.write_text(marker + "\n\nPersisted back-edge is enabled.\n", encoding="utf-8")
        report = self._scan(product, plugin, host)
        self.assertTrue({"PLANNED_MARKER_NOT_ADJACENT", "UNSUPPORTED_AFFIRMATIVE"} & {f.code for f in report.findings})

    def test_all_claim_classes_block_when_current_affirmative(self):
        samples = (
            "Loop runtime is active.", "Loop engineering migration is valid.",
            "Persisted back-edge is enabled.", "Flow-unit loop_count is implemented.",
            "Middle fuse is active.", "PARO transition is enabled.",
            "Loop automatic escalation is implemented.",
            "Loop is the only active model.", "Classic lifecycle is superseded.",
            "Global stage is eliminated.", "Criteria 2-8 are complete.",
            "RISK-042 is closed.", "Loop Engineering 1.0.0 is production-ready.",
        )
        for index, sample in enumerate(samples):
            with self.subTest(index=index):
                stack, product, plugin, host, _, _ = self._roots()
                try:
                    (product / "docs/claim.md").write_text(sample + "\n", encoding="utf-8")
                    self.assertIn("UNSUPPORTED_AFFIRMATIVE", {f.code for f in self._scan(product, plugin, host).findings})
                finally:
                    stack.cleanup()

    def test_unknown_loop_scheduler_orchestration_and_operational_claims_block(self):
        samples = (
            "Loop scheduler is operational.",
            "Loop orchestration is enabled.",
            "The Loop dispatch lane is operational.",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                stack, product, plugin, host, _, _ = self._roots()
                try:
                    (product / "docs/claim.md").write_text(sample + "\n", encoding="utf-8")
                    self.assertIn("UNCLASSIFIED_SURFACE", {f.code for f in self._scan(product, plugin, host).findings})
                finally:
                    stack.cleanup()

    def test_free_example_ellipsis_regex_name_and_unproven_test_local_do_not_bypass(self):
        stack, product, plugin, host, _, _ = self._roots()
        self.addCleanup(stack.cleanup)
        (product / "docs/example.md").write_text(
            "Example: Loop runtime is active.\n\n```text\nLoop scheduler is operational...\n```\n",
            encoding="utf-8",
        )
        (product / "skills/claim.py").write_text(
            'CLAIM_RE = "Loop orchestration is enabled."\n\n'
            'def test_claim():\n    claim = "Loop runtime is active."\n    consume(claim)\n',
            encoding="utf-8",
        )
        blocked = [
            finding for finding in self._scan(product, plugin, host).findings
            if finding.code in {
                "UNSUPPORTED_AFFIRMATIVE", "UNCLASSIFIED_SURFACE", "AMBIGUOUS_SEMANTIC_UNIT",
            }
        ]
        self.assertGreaterEqual(len(blocked), 4)

    def test_three_language_unclassified_assertions_block(self):
        writers = (
            ("docs/new.md", "Loop runtime is active and complete.\n"),
            ("skills/new.py", '"""Loop runtime is active and complete."""\n'),
            ("project/new.json", json.dumps({"runtime_activation": True})),
        )
        for rel, content in writers:
            with self.subTest(rel=rel):
                stack, product, plugin, host, _, _ = self._roots()
                try:
                    path = product / rel
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                    self.assertIn("UNSUPPORTED_AFFIRMATIVE", {f.code for f in self._scan(product, plugin, host).findings})
                finally:
                    stack.cleanup()

    def test_notice_orphan_duplicate_occurrence_and_digest_block(self):
        stack, product, plugin, host, policy, authority = self._roots()
        self.addCleanup(stack.cleanup)
        path = product / "docs/history.md"
        path.write_text(path.read_text(encoding="utf-8") + '<!-- loop-runtime-superseding:{"notice_id":"ORPHAN"} -->\n', encoding="utf-8")
        self.assertIn("NOTICE_ORPHAN", {f.code for f in self._scan(product, plugin, host).findings})
        policy["historical_claims"][0]["occurrence_count"] = 2
        self._write_controls(plugin, policy, authority)
        self.assertIn("CLAIM_OCCURRENCE_DRIFT", {f.code for f in self._scan(product, plugin, host).findings})
        policy["historical_claims"][0]["claim_payload_sha256"] = "0" * 64
        self._write_controls(plugin, policy, authority)
        self.assertIn("CLAIM_PAYLOAD_DIGEST_DRIFT", {f.code for f in self._scan(product, plugin, host).findings})

    def test_notice_classification_is_exact_and_rejects_met_or_extra_fields(self):
        stack, product, plugin, host, _, _ = self._roots()
        self.addCleanup(stack.cleanup)
        path = product / "docs/history.md"
        text = path.read_text(encoding="utf-8").replace('"runtime_activation":"NOT_MET"', '"runtime_activation":"MET"')
        path.write_text(text, encoding="utf-8")
        self.assertIn("NOTICE_BINDING_DRIFT", {f.code for f in self._scan(product, plugin, host).findings})
        path.write_text(text.replace('"open_risks":', '"contradiction":"runtime active","open_risks":'), encoding="utf-8")
        self.assertIn("NOTICE_BINDING_DRIFT", {f.code for f in self._scan(product, plugin, host).findings})

    def test_marker_claim_id_and_subject_must_match_policy_ownership(self):
        stack, product, plugin, host, _, _ = self._roots()
        self.addCleanup(stack.cleanup)
        path = product / "docs/planned.md"
        path.write_text(
            '<!-- loop-runtime-target:{"claim_id":"UNKNOWN","target_version":"0.68.0","status":"planned_not_active"} -->\n'
            'Persisted back-edge is enabled.\n',
            encoding="utf-8",
        )
        self.assertIn("PLANNED_MARKER_UNKNOWN_CLAIM", {f.code for f in self._scan(product, plugin, host).findings})
        path.write_text(
            '<!-- loop-runtime-target:{"claim_id":"PLAN-1","target_version":"0.68.0","status":"planned_not_active"} -->\n'
            'Loop runtime is active.\n',
            encoding="utf-8",
        )
        self.assertIn("PLANNED_MARKER_SUBJECT_MISMATCH", {f.code for f in self._scan(product, plugin, host).findings})

    def test_historical_ownership_requires_exact_payload_not_adjacent_substring(self):
        stack, product, plugin, host, policy, authority = self._roots()
        self.addCleanup(stack.cleanup)
        original = policy["historical_claims"][0]["claim_payload"]
        expanded = original + " Extra locator text"
        path = product / "docs/history.md"
        text = path.read_text(encoding="utf-8").replace(original, expanded, 1)
        path.write_text(text, encoding="utf-8")
        entry = policy["historical_claims"][0]
        entry["claim_payload"] = expanded
        entry["claim_payload_sha256"] = hashlib.sha256(expanded.encode()).hexdigest()
        entry["locator_sha256"] = hashlib.sha256(expanded.encode()).hexdigest()
        with patch.object(lrc, "REQUIRED_POLICY_SHA256", _policy_digest(policy)):
            self._write_controls(plugin, policy, authority)
            report = self._scan(product, plugin, host)
        self.assertEqual(0, report.historical_matches)
        self.assertIn("UNSUPPORTED_AFFIRMATIVE", {f.code for f in report.findings})

    def test_absolute_traversal_alias_paths_block(self):
        for value in ("C:/escape.md", "/escape.md", "../escape.md", "docs/../escape.md", "docs\\x.md"):
            with self.subTest(value=value):
                self.assertIsNotNone(_safe_relative(value)[1])

    def test_enumerated_bytes_are_immutable_and_final_recheck_detects_change(self):
        stack, product, plugin, host, _, _ = self._roots()
        self.addCleanup(stack.cleanup)
        inventory, findings = enumerate_candidates(ClaimScanContext(product, plugin, host), ScanLimits())
        self.assertFalse(findings)
        target = product / "docs/history.md"
        target.write_text(target.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")
        _, recheck = _recheck_inventory(ClaimScanContext(product, plugin, host), inventory, ScanLimits())
        self.assertTrue({"INVENTORY_CONTENT_CHANGED", "INVENTORY_RAW_BYTES_CHANGED"} & {f.code for f in recheck})

    def test_final_recheck_detects_new_and_deleted_candidates(self):
        stack, product, plugin, host, _, _ = self._roots()
        self.addCleanup(stack.cleanup)
        context = ClaimScanContext(product, plugin, host)
        inventory, findings = enumerate_candidates(context, ScanLimits())
        self.assertFalse(findings)
        (product / "docs/new.md").write_text("ordinary text\n", encoding="utf-8")
        _, recheck = _recheck_inventory(context, inventory, ScanLimits())
        self.assertIn("INVENTORY_PATH_SET_CHANGED", {f.code for f in recheck})

        inventory, findings = enumerate_candidates(context, ScanLimits())
        self.assertFalse(findings)
        (product / "docs/new.md").unlink()
        _, recheck = _recheck_inventory(context, inventory, ScanLimits())
        self.assertIn("INVENTORY_PATH_SET_CHANGED", {f.code for f in recheck})

    def test_canonical_content_digest_normalizes_bom_newlines_and_nfc(self):
        lf = "café\n".encode("utf-8")
        bom_crlf = b"\xef\xbb\xbf" + "café\r\n".encode("utf-8")
        nfd = "cafe\u0301\n".encode("utf-8")
        first, _ = _content_digest(lf, "product_root", "docs/x.md")
        second, _ = _content_digest(bom_crlf, "product_root", "docs/x.md")
        third, _ = _content_digest(nfd, "product_root", "docs/x.md")
        self.assertEqual(first, second)
        self.assertEqual(first, third)

    def test_intermediate_symlink_or_junction_segment_is_rejected(self):
        stack, product, _, _, _, _ = self._roots()
        self.addCleanup(stack.cleanup)
        target = product.parent / "outside"
        target.mkdir()
        (target / "claim.md").write_text("ordinary text\n", encoding="utf-8")
        alias = product / "docs/alias"
        try:
            os.symlink(target, alias, target_is_directory=True)
        except OSError as exc:
            if os.name != "nt":
                self.fail(f"directory symlink unavailable: {exc}")
            completed = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(alias), str(target)],
                capture_output=True, text=True,
            )
            self.assertEqual(0, completed.returncode, completed.stderr or completed.stdout)
        _, error = _safe_join(product, "docs/alias/claim.md")
        self.assertIsNotNone(error)

    def test_intermediate_windows_junction_segment_is_rejected(self):
        if os.name != "nt":
            self.assertNotEqual("nt", os.name)
            return
        stack, product, _, _, _, _ = self._roots()
        self.addCleanup(stack.cleanup)
        target = product.parent / "junction-target"
        target.mkdir()
        (target / "claim.md").write_text("ordinary text\n", encoding="utf-8")
        alias = product / "docs/junction"
        completed = subprocess.run(["cmd", "/c", "mklink", "/J", str(alias), str(target)], capture_output=True, text=True)
        self.assertEqual(0, completed.returncode, completed.stderr or completed.stdout)
        try:
            _, error = _safe_join(product, "docs/junction/claim.md")
            self.assertIsNotNone(error)
        finally:
            os.rmdir(alias)

    def test_installed_host_semantic_scan_does_not_authorize_uninitialized_identity(self):
        stack, product, plugin, host, _, _ = self._roots()
        self.addCleanup(stack.cleanup)
        report = self._scan(product, plugin, host, mode="installed_host")
        self.assertEqual("PASS", report.verdict, report.findings)
        empty_host = host.parent / "empty-host"
        empty_host.mkdir()
        report = self._scan(product, plugin, empty_host, mode="installed_host")
        self.assertEqual("PASS", report.verdict, report.findings)
        self.assertEqual("UNINITIALIZED", report.host_state)

    def test_parse_and_budget_errors_are_typed(self):
        stack, product, plugin, host, _, _ = self._roots()
        self.addCleanup(stack.cleanup)
        (product / "skills/bad.py").write_text("def broken(:\n", encoding="utf-8")
        self.assertIn("PARSE_ERROR", {f.code for f in self._scan(product, plugin, host).findings})
        (product / "skills/bad.py").write_text("x = 1\n", encoding="utf-8")
        self.assertIn("CANDIDATE_BUDGET_EXCEEDED", {
            f.code for f in self._scan(product, plugin, host, limits=ScanLimits(max_candidates=0)).findings
        })

    def test_real_repository_inventory_complete_and_within_budget(self):
        product_root, plugin, project_root = _real_repository_roots()
        context = ClaimScanContext(product_root, plugin, project_root, "product_release")
        report = scan_loop_runtime_claims(context)
        tracemalloc.start()
        memory_report = scan_loop_runtime_claims(context)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.assertEqual("PASS", report.verdict, report.findings[:5])
        self.assertEqual(report.inventory.candidate_count, report.parsed_candidates)
        self.assertEqual(report.inventory.inventory_sha256, report.final_inventory_sha256)
        self.assertLess(peak, 256 * 1024 * 1024)
        self.assertEqual("PASS", memory_report.verdict)


# The exact 46 units diagnosed by MAINTENANCE-FIX-197-R1.  This is a
# classification ledger, not a final-verdict-only assertion.
FORMER_46_GOLDEN = (
    (".governance/evidence-log.md", "table:198:5:3", "NEGATIVE_NONCLAIM", "markdown_table_cell"),
    ("docs/architecture/ADR-011-loop-runtime-claim-correction.md", "fence:106:107:1", "NEGATIVE_NONCLAIM", "fence:html"),
    ("docs/architecture/ADR-011-loop-runtime-claim-correction.md", "clause:247:1", "STRUCTURAL_DATA", "paragraph"),
    ("docs/architecture/ADR-011-loop-runtime-claim-correction.md", "clause:446:3", "NEGATIVE_NONCLAIM", "paragraph"),
    ("docs/release/feature-flags-0.65.0.md", "clause:36:2", "NEGATIVE_NONCLAIM", "paragraph"),
    ("docs/release/release-checklist-0.65.0.md", "clause:59:1", "NEGATIVE_NONCLAIM", "paragraph"),
    ("docs/requirements/loop-engineering-architecture-0.65.0-proposed.md", "clause:808:1", "PLANNED_NOT_ACTIVE", "paragraph"),
    ("docs/requirements/loop-engineering-implementation-breakdown-0.65.0.md", "clause:470:1", "NEGATIVE_NONCLAIM", "paragraph"),
    ("skills/code-review/SKILL.md", "clause:14:3", "NEGATIVE_NONCLAIM", "paragraph"),
    ("skills/code-review/SKILL.md", "clause:19:1", "PLANNED_NOT_ACTIVE", "paragraph"),
    ("skills/design-review/SKILL.md", "clause:14:3", "NEGATIVE_NONCLAIM", "paragraph"),
    ("skills/design-review/SKILL.md", "clause:19:1", "PLANNED_NOT_ACTIVE", "paragraph"),
    ("skills/release-review/SKILL.md", "clause:14:3", "NEGATIVE_NONCLAIM", "paragraph"),
    ("skills/release-review/SKILL.md", "clause:19:1", "PLANNED_NOT_ACTIVE", "paragraph"),
    ("skills/requirement-review/SKILL.md", "clause:14:3", "NEGATIVE_NONCLAIM", "paragraph"),
    ("skills/requirement-review/SKILL.md", "clause:19:1", "PLANNED_NOT_ACTIVE", "paragraph"),
    ("skills/retro-review/SKILL.md", "clause:14:3", "NEGATIVE_NONCLAIM", "paragraph"),
    ("skills/retro-review/SKILL.md", "clause:19:1", "PLANNED_NOT_ACTIVE", "paragraph"),
    ("skills/software-project-governance/core/loop-runtime-claim-allowlist.json", "json:/historical_claims/4/claim_payload", "STRUCTURAL_DATA", "json_schema_role"),
    ("skills/software-project-governance/core/loop-runtime-claim-allowlist.json", "json:/active_surface_rules/5/claim_id", "STRUCTURAL_DATA", "json_schema_role"),
    ("skills/software-project-governance/infra/checks/loop_runtime_claims.py", "ast:string:39:28:1", "STRUCTURAL_DATA", "regex_source"),
    ("skills/software-project-governance/infra/loop_engine.py", "ast:string:314:4:1", "NEGATIVE_NONCLAIM", "docstring"),
    ("skills/software-project-governance/infra/tests/test_loop_runtime_claims.py", "ast:string:93:54:1", "NEGATIVE_NONCLAIM", "test_assignment_escaping_or_ambiguous"),
    ("skills/software-project-governance/infra/tests/test_loop_runtime_claims.py", "ast:string:94:12:1", "NEGATIVE_NONCLAIM", "test_assignment_escaping_or_ambiguous"),
    ("skills/software-project-governance/infra/tests/test_loop_runtime_claims.py", "ast:string:134:48:1", "STRUCTURAL_DATA", "test_local_non_escaping"),
    ("skills/software-project-governance/infra/tests/test_loop_runtime_claims.py", "ast:string:187:12:1", "STRUCTURAL_DATA", "test_local_non_escaping"),
    ("skills/software-project-governance/infra/tests/test_loop_runtime_claims.py", "ast:string:190:12:1", "STRUCTURAL_DATA", "test_local_non_escaping"),
    ("skills/software-project-governance/infra/tests/test_loop_runtime_claims.py", "ast:string:209:12:1", "STRUCTURAL_DATA", "test_local_non_escaping"),
    ("skills/software-project-governance/infra/tests/test_loop_runtime_claims.py", "ast:string:209:39:1", "STRUCTURAL_DATA", "test_local_non_escaping"),
    ("skills/software-project-governance/infra/tests/test_loop_runtime_claims.py", "ast:string:210:12:1", "STRUCTURAL_DATA", "test_local_non_escaping"),
    ("skills/software-project-governance/infra/tests/test_loop_runtime_claims.py", "ast:string:210:47:1", "STRUCTURAL_DATA", "test_local_non_escaping"),
    ("skills/software-project-governance/infra/tests/test_loop_runtime_claims.py", "ast:string:211:12:1", "STRUCTURAL_DATA", "test_local_non_escaping"),
    ("skills/software-project-governance/infra/tests/test_loop_runtime_claims.py", "ast:string:211:38:1", "STRUCTURAL_DATA", "test_local_non_escaping"),
    ("skills/software-project-governance/infra/tests/test_loop_runtime_claims.py", "ast:string:212:12:1", "STRUCTURAL_DATA", "test_local_non_escaping"),
    ("skills/software-project-governance/infra/tests/test_loop_runtime_claims.py", "ast:string:178:59:1", "STRUCTURAL_DATA", "test_local_non_escaping"),
    ("skills/software-project-governance/infra/tests/test_loop_runtime_claims.py", "ast:string:201:33:1", "STRUCTURAL_DATA", "test_local_non_escaping"),
    ("skills/software-project-governance/infra/tests/test_loop_runtime_claims.py", "ast:string:203:33:1", "STRUCTURAL_DATA", "test_local_non_escaping"),
    ("skills/software-project-governance/infra/tests/test_loop_runtime_claims.py", "ast:string:261:28:1", "STRUCTURAL_DATA", "test_local_non_escaping"),
    ("skills/software-project-governance/references/loop-role-mapping.md", "clause:5:3", "NEGATIVE_NONCLAIM", "paragraph"),
    ("skills/software-project-governance/references/loop-role-mapping.md", "clause:11:2", "NEGATIVE_NONCLAIM", "paragraph"),
    ("skills/software-project-governance/references/loop-role-mapping.md", "clause:14:1", "PLANNED_NOT_ACTIVE", "paragraph"),
    ("skills/software-project-governance/references/loop-role-mapping.md", "clause:42:2", "NEGATIVE_NONCLAIM", "list_item"),
    ("skills/tech-review/SKILL.md", "clause:14:3", "NEGATIVE_NONCLAIM", "paragraph"),
    ("skills/tech-review/SKILL.md", "clause:19:1", "PLANNED_NOT_ACTIVE", "paragraph"),
    ("skills/test-review/SKILL.md", "clause:14:3", "NEGATIVE_NONCLAIM", "paragraph"),
    ("skills/test-review/SKILL.md", "clause:19:1", "PLANNED_NOT_ACTIVE", "paragraph"),
)


class LoopRuntimePerformanceAndGoldenTests(unittest.TestCase):
    def test_former_46_locator_ledger(self):
        import checks.loop_runtime_claims as lrc

        product_root, plugin, project_root = _real_repository_roots()
        policy = json.loads((plugin / "core/loop-runtime-claim-allowlist.json").read_text(encoding="utf-8"))
        units = []
        for path in sorted({item[0] for item in FORMER_46_GOLDEN}):
            owner = "host_root" if path.startswith(".governance/") else "product_root"
            target = (project_root if owner == "host_root" else product_root) / path
            raw = target.read_bytes()
            candidate = lrc.Candidate(
                owner, path, target, lrc.SUPPORTED_EXTENSIONS[target.suffix], raw, len(raw),
                lrc._content_digest(raw, owner, path)[0],
            )
            extracted, error = lrc.extract_semantic_units(candidate)
            self.assertIsNone(error, path)
            units.extend(extracted)
        bindings, errors = lrc._bind_planned_markers(units, policy)
        self.assertFalse(errors)
        actual = Counter(
            (unit.normalized_path, *lrc._classify(unit, policy, bindings.get(index, ""))[:1], unit.provenance)
            for index, unit in enumerate(units)
        )
        expected = Counter(
            (path, state, provenance)
            for path, _locator, state, provenance in FORMER_46_GOLDEN
        )
        self.assertEqual(46, len(FORMER_46_GOLDEN))
        for (path, state, provenance), count in expected.items():
            acceptable = {state}
            if state == "NEGATIVE_NONCLAIM":
                acceptable.add("STRUCTURAL_DATA")
            observed = sum(actual[(path, candidate_state, provenance)] for candidate_state in acceptable)
            self.assertGreaterEqual(observed, count, (path, state, provenance))

    def test_python_extractor_builds_parent_map_in_one_explicit_traversal(self):
        import checks.loop_runtime_claims as lrc
        from unittest.mock import patch

        raw = b'def test_x():\n    values = ("a", "b", "c")\n    return 1\n'
        candidate = lrc.Candidate("product_root", "skills/x.py", Path("x.py"), "python", raw,
                                  len(raw), hashlib.sha256(raw).hexdigest())
        original = lrc.ast.walk
        with patch.object(lrc.ast, "walk", wraps=original) as spy:
            units, error = lrc.extract_semantic_units(candidate)
        self.assertIsNone(error)
        self.assertTrue(units)
        self.assertEqual(0, spy.call_count)

    def test_python_provenance_index_operation_count_is_linear(self):
        import checks.loop_runtime_claims as lrc

        measurements = []
        for size in (1000, 2000, 4000):
            tree = lrc.ast.parse("\n".join(f'VALUE_{index} = "fixture-{index}"' for index in range(size)))
            nodes = list(lrc.ast.walk(tree))
            parents = {}
            for parent in nodes:
                for child in lrc.ast.iter_child_nodes(parent):
                    parents[child] = parent
            index = lrc._build_python_provenance_index(nodes, parents)
            self.assertGreaterEqual(index.operation_count, len(nodes))
            measurements.append((len(nodes), index.operation_count))
        for previous, current in zip(measurements, measurements[1:]):
            node_ratio = current[0] / previous[0]
            operation_ratio = current[1] / previous[1]
            self.assertAlmostEqual(node_ratio, operation_ratio, places=9)

    def test_subject_free_units_do_not_run_predicate_regex(self):
        import checks.loop_runtime_claims as lrc
        from unittest.mock import patch

        with patch.object(lrc, "_predicate_spans", wraps=lrc._predicate_spans) as spy:
            self.assertEqual((), lrc._relations("ordinary project documentation"))
        spy.assert_not_called()

    def test_three_run_performance_identity_and_median(self):
        import checks.loop_runtime_claims as lrc
        import statistics

        product_root, plugin, project_root = _real_repository_roots()
        context = lrc.ClaimScanContext(product_root, plugin, project_root, "product_release")
        elapsed = []
        identities = []
        finding_snapshots = []
        for _ in range(3):
            started = time.perf_counter()
            report = lrc.scan_loop_runtime_claims(context)
            elapsed.append(time.perf_counter() - started)
            identities.append((report.verdict, report.inventory.candidate_count, report.semantic_units,
                               tuple(sorted(report.state_totals.items())), len(report.classification_ledger),
                               report.inventory.inventory_sha256, report.final_inventory_sha256))
            finding_snapshots.append([(finding.code, finding.normalized_path) for finding in report.findings[:10]])
        self.assertEqual(1, len(set(identities)))
        self.assertEqual("PASS", identities[0][0], finding_snapshots[0])
        self.assertLess(statistics.median(elapsed), 8.0)

    def test_structured_removal_or_planned_binding_is_negative_not_ambiguous(self):
        import checks.loop_runtime_claims as lrc

        raw = (
            "Every generic persisted back-edge, flow-unit `loop_count`, tier fuse, automatic escalation, "
            "and PARO transition statement is removed or bound to a `0.68.0/planned_not_active` marker.\n"
        ).encode("utf-8")
        candidate = lrc.Candidate(
            "product_root", "docs/containment.md", Path("containment.md"), "markdown", raw,
            len(raw), hashlib.sha256(raw).hexdigest(),
        )
        units, error = lrc.extract_semantic_units(candidate)
        self.assertIsNone(error)
        states = {lrc._classify(unit, {"historical_claims": [], "active_surface_rules": ACTIVE_RULES})[0]
                  for unit in units if unit.relations}
        self.assertEqual({"NEGATIVE_NONCLAIM"}, states)

    def test_each_review_skill_unconditional_runtime_overclaim_blocks(self):
        skill_paths = (
            "skills/code-review/SKILL.md",
            "skills/design-review/SKILL.md",
            "skills/release-review/SKILL.md",
            "skills/requirement-review/SKILL.md",
            "skills/retro-review/SKILL.md",
            "skills/tech-review/SKILL.md",
            "skills/test-review/SKILL.md",
        )
        for relative_path in skill_paths:
            with self.subTest(relative_path=relative_path):
                fixture = LoopRuntimeClaimTests()
                stack, product, plugin, host, _, _ = fixture._roots()
                try:
                    target = product / relative_path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("Loop runtime is active and complete.\n", encoding="utf-8")
                    report = scan_loop_runtime_claims(
                        ClaimScanContext(product, plugin, host, "product_release")
                    )
                    findings = [
                        finding for finding in report.findings
                        if finding.normalized_path == relative_path
                    ]
                    self.assertIn("UNSUPPORTED_AFFIRMATIVE", {finding.code for finding in findings})
                finally:
                    stack.cleanup()
                    fixture.doCleanups()


ACCT_V1_MD_BYTES = (
    b'{"context_chain":[],"kind":"md_heading","language":"markdown","locator":{"end_column":14,"end_line":0,"pointer":null,"role":null,"start_column":0,"start_line":0,"type":"source_span"},"normalized_path":"golden/ACCT-V1-MD-01.md","normalized_payload":"Loop runtime","ordinal":0,"root_owner":"product_root"}\n'
    b'{"context_chain":[{"index":null,"kind":"md_heading","level":1,"name":null,"payload":"Loop runtime","pointer":null}],"kind":"md_list_item","language":"markdown","locator":{"end_column":20,"end_line":1,"pointer":null,"role":null,"start_column":0,"start_line":1,"type":"source_span"},"normalized_path":"golden/ACCT-V1-MD-01.md","normalized_payload":"state: frobnicated","ordinal":1,"root_owner":"product_root"}\n'
)
ACCT_V1_JSON_BYTES = (
    b'{"context_chain":[],"kind":"json_key","language":"json","locator":{"end_column":null,"end_line":null,"pointer":"/loop_runtime","role":"key","start_column":null,"start_line":null,"type":"json_pointer"},"normalized_path":"golden/ACCT-V1-JSON-01.json","normalized_payload":"loop_runtime","ordinal":0,"root_owner":"product_root"}\n'
    b'{"context_chain":[{"index":null,"kind":"json_key","level":null,"name":null,"payload":"loop_runtime","pointer":"/loop_runtime"}],"kind":"json_key","language":"json","locator":{"end_column":null,"end_line":null,"pointer":"/loop_runtime/state","role":"key","start_column":null,"start_line":null,"type":"json_pointer"},"normalized_path":"golden/ACCT-V1-JSON-01.json","normalized_payload":"state","ordinal":1,"root_owner":"product_root"}\n'
    b'{"context_chain":[{"index":null,"kind":"json_key","level":null,"name":null,"payload":"loop_runtime","pointer":"/loop_runtime"},{"index":null,"kind":"json_key","level":null,"name":null,"payload":"state","pointer":"/loop_runtime/state"}],"kind":"json_string","language":"json","locator":{"end_column":null,"end_line":null,"pointer":"/loop_runtime/state","role":"value","start_column":null,"start_line":null,"type":"json_pointer"},"normalized_path":"golden/ACCT-V1-JSON-01.json","normalized_payload":"frobnicated","ordinal":2,"root_owner":"product_root"}\n'
)
ACCT_V1_PY_BYTES = (
    b'{"context_chain":[{"index":null,"kind":"binding","level":null,"name":"loop","payload":null,"pointer":null}],"kind":"py_string","language":"python","locator":{"end_column":20,"end_line":0,"pointer":null,"role":null,"start_column":7,"start_line":0,"type":"source_span"},"normalized_path":"golden/ACCT-V1-PY-01.py","normalized_payload":"frobnicated","ordinal":0,"root_owner":"product_root"}\n'
    b'{"context_chain":[{"index":null,"kind":"call","level":null,"name":"emit","payload":null,"pointer":null},{"index":0,"kind":"parameter_index","level":null,"name":null,"payload":null,"pointer":null}],"kind":"py_string","language":"python","locator":{"end_column":12,"end_line":1,"pointer":null,"role":null,"start_column":5,"start_line":1,"type":"source_span"},"normalized_path":"golden/ACCT-V1-PY-01.py","normalized_payload":"ready","ordinal":1,"root_owner":"product_root"}\n'
)


class LoopRuntimeFix199ContractTests(unittest.TestCase):
    def _candidate(self, path, language, payload):
        raw = payload.encode("utf-8")
        return lrc.Candidate(
            "product_root", path, Path(path), language, raw, len(raw),
            lrc._content_digest(raw, "product_root", path)[0],
        )

    def test_accounting_v1_literal_golden_vectors(self):
        vectors = (
            ("golden/ACCT-V1-MD-01.md", "markdown", "# Loop runtime\n- state: frobnicated\n",
             ACCT_V1_MD_BYTES, "5ce9ad09d7cc4b418da7b1cedd64448b92d998e209f438e6fbe15463c4755b43"),
            ("golden/ACCT-V1-JSON-01.json", "json", '{"loop_runtime":{"state":"frobnicated"}}',
             ACCT_V1_JSON_BYTES, "8b06455b9e738669066c77c29e53263a38cb8fc35d1065e939b370bfddd258bb"),
            ("golden/ACCT-V1-PY-01.py", "python", 'loop = "frobnicated"\nemit("ready")\n',
             ACCT_V1_PY_BYTES, "10a22c5e617b6b9e4ac55b22c9a0602a78f3405e7c40fdf04aae2e0129bf92d0"),
        )
        for path, language, payload, expected, digest in vectors:
            with self.subTest(path=path):
                records, finding = lrc._account_candidate(self._candidate(path, language, payload))
                self.assertIsNone(finding)
                serialized = lrc._serialize_accounting_records(records)
                self.assertEqual(expected, serialized)
                self.assertEqual(digest, hashlib.sha256(serialized).hexdigest())

    def test_accounting_v1_duplicate_json_key_is_typed_and_emits_nothing(self):
        candidate = self._candidate("golden/ACCT-V1-ERR-01.json", "json", '{"loop":1,"loop":2}')
        records, finding = lrc._account_candidate(candidate)
        self.assertEqual([], records)
        self.assertEqual("ACCOUNTING_JSON_DUPLICATE_KEY", finding.code)
        self.assertEqual(hashlib.sha256(b"").hexdigest(), hashlib.sha256(lrc._serialize_accounting_records(records)).hexdigest())

    def test_r1_markdown_ancestry_continuation_and_ambiguous_boundaries(self):
        for payload in ("```\n", "| ... | ... |\n| --- | --- |\n| a | b |\n", "|  |  |\n| --- | --- |\n| a | b |\n"):
            with self.subTest(payload=payload):
                records, finding = lrc._account_candidate(self._candidate("docs/boundary.md", "markdown", payload))
                self.assertEqual([], records)
                self.assertEqual("ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY", finding.code)

        fixture = LoopRuntimeClaimTests()
        stack, product, plugin, host, _, _ = fixture._roots()
        self.addCleanup(stack.cleanup)
        self.addCleanup(fixture.doCleanups)
        variants = {
            "docs/nested.md": "- Loop controller\n  - state: frobnicated\n",
            "docs/continuation.md": "- Loop controller\n  state: frobnicated\n",
        }
        for relative_path, payload in variants.items():
            with self.subTest(relative_path=relative_path):
                target = product / relative_path
                target.write_text(payload, encoding="utf-8")
                report = fixture._scan(product, plugin, host)
                codes = {item.code for item in report.findings if item.normalized_path == relative_path}
                self.assertIn("UNKNOWN_STATE_PREDICATE", codes)
                target.unlink()

    def test_r1_python_escape_forms_are_exactly_ambiguous(self):
        fixture = LoopRuntimeClaimTests()
        stack, product, plugin, host, _, _ = fixture._roots()
        self.addCleanup(stack.cleanup)
        self.addCleanup(fixture.doCleanups)
        variants = {
            "return": 'def helper():\n    return "Loop controller is online."\n',
            "yield": 'def helper():\n    yield "Loop controller is online."\n',
            "outer_mutation": 'OUT = []\ndef helper():\n    OUT.append("Loop controller is online.")\n',
            "alias": 'def helper():\n    value = "Loop controller is online."\n    alias = value\n    emit(alias)\n',
            "closure": 'def outer():\n    value = "Loop controller is online."\n    def inner():\n        return value\n    return inner\n',
            "global": 'def helper():\n    global EXPORTED\n    EXPORTED = "Loop controller is online."\n',
            "unknown_call": 'def helper():\n    emit("Loop controller is online.")\n',
            "incomplete_mapping": 'def helper(value):\n    emit(value)\nhelper("Loop controller is online.")\n',
        }
        for name, payload in variants.items():
            with self.subTest(name=name):
                relative_path = f"skills/{name}.py"
                target = product / relative_path
                target.write_text(payload, encoding="utf-8")
                report = fixture._scan(product, plugin, host)
                codes = {item.code for item in report.findings if item.normalized_path == relative_path}
                self.assertIn("AMBIGUOUS_SEMANTIC_UNIT", codes)
                target.unlink()

    def test_r1_json_ordered_ancestor_state_relations(self):
        fixture = LoopRuntimeClaimTests()
        stack, product, plugin, host, _, _ = fixture._roots()
        self.addCleanup(stack.cleanup)
        self.addCleanup(fixture.doCleanups)
        variants = {
            "docs/object.json": {"loop_runtime": {"state": "frobnicated"}},
            "docs/array.json": {"loop_runtime": [{"status": "frobnicated"}]},
            "docs/schema.json": {"properties": {"loop_runtime": {"mode": "frobnicated"}}},
        }
        for relative_path, payload in variants.items():
            with self.subTest(relative_path=relative_path):
                target = product / relative_path
                target.write_text(json.dumps(payload), encoding="utf-8")
                report = fixture._scan(product, plugin, host)
                codes = {item.code for item in report.findings if item.normalized_path == relative_path}
                self.assertIn("UNKNOWN_STATE_PREDICATE", codes)
                target.unlink()

    def test_r1_open_predicates_and_ambiguity_producers(self):
        cases = (
            ("Loop controller is online.", "UNKNOWN_STATE_PREDICATE"),
            ("Online is the Loop controller.", "UNKNOWN_STATE_PREDICATE"),
            ("Loop runtime and Loop migration are active.", "AMBIGUOUS_SUBJECT_RELATION"),
        )
        for payload, expected in cases:
            with self.subTest(expected=expected):
                candidate = self._candidate("docs/open.md", "markdown", payload)
                units, error = lrc.extract_semantic_units(candidate)
                self.assertIsNone(error)
                states = {lrc._classify(unit, {"historical_claims": [], "active_surface_rules": ACTIVE_RULES})[0]
                          for unit in units}
                self.assertIn(expected, states)
        candidate = self._candidate("docs/open.md", "markdown", "state: online")
        unit = lrc._unit(candidate, "fixture", (1, 0, 1, 13), "state: online", "prose", "list_item",
                         context=("Loop alpha", "Loop beta"))
        self.assertEqual(
            "AMBIGUOUS_DOMAIN_CONTEXT",
            lrc._classify(unit, {"historical_claims": [], "active_surface_rules": ACTIVE_RULES})[0],
        )

    def test_r1_diagnostic_and_forged_accounting_shape_do_not_authorize(self):
        fixture = LoopRuntimeClaimTests()
        stack, product, plugin, host, _, _ = fixture._roots()
        self.addCleanup(stack.cleanup)
        self.addCleanup(fixture.doCleanups)
        variants = {
            "docs/diagnostic.md": 'The validator reports "Loop controller is online."\n',
            "docs/forged.json": json.dumps({
                "context_chain": [], "kind": "py_string", "language": "python",
                "locator": {}, "normalized_path": "golden/ACCT-V1-PY-01.py",
                "normalized_payload": "Loop controller is online.", "ordinal": 0,
                "root_owner": "product_root",
            }),
        }
        for relative_path, payload in variants.items():
            with self.subTest(relative_path=relative_path):
                target = product / relative_path
                target.write_text(payload, encoding="utf-8")
                report = fixture._scan(product, plugin, host)
                codes = {item.code for item in report.findings if item.normalized_path == relative_path}
                self.assertIn("UNKNOWN_STATE_PREDICATE", codes)
                target.unlink()

    def test_r1_lone_json_surrogate_is_typed_and_emits_zero_records(self):
        candidate = self._candidate("docs/surrogate.json", "json", r'{"loop":"\ud800"}')
        records, finding = lrc._account_candidate(candidate)
        self.assertEqual([], records)
        self.assertEqual("ACCOUNTING_JSON_PARSE_ERROR", finding.code)

    def test_scanner_has_no_cross_scan_parse_or_semantic_cache(self):
        source = Path(lrc.__file__).read_text(encoding="utf-8")
        self.assertNotIn("_SEMANTIC_SCAN_CACHE", source)
        self.assertNotIn("@lru_cache", source)
        self.assertFalse(hasattr(lrc, "_SEMANTIC_SCAN_CACHE"))

    def test_streaming_accounting_matches_reference_aggregation(self):
        candidates = [
            self._candidate("golden/a.md", "markdown", "# Loop runtime\n"),
            self._candidate("golden/b.json", "json", '{"loop_runtime":false}'),
            self._candidate("golden/c.py", "python", 'loop = "NOT_MET"\n'),
        ]
        accumulator = lrc.AccountingAccumulator()
        all_records = []
        for candidate in candidates:
            records, finding = lrc._account_candidate(candidate)
            self.assertIsNone(finding)
            accumulator.add(candidate, records)
            all_records.extend(records)
        expected_by_path, expected_digest = lrc._accounting_summary(all_records)
        self.assertEqual(expected_by_path, accumulator.by_path)
        self.assertEqual(expected_digest, accumulator.aggregate.hexdigest())

    def test_open_vocabulary_context_and_provenance_mutations_block(self):
        fixture = LoopRuntimeClaimTests()
        stack, product, plugin, host, _, _ = fixture._roots()
        self.addCleanup(stack.cleanup)
        self.addCleanup(fixture.doCleanups)
        mutations = {
            "docs/triggers.md": "# Loop lifecycle driver\n## Triggers\n- state: operational\n",
            "docs/inline.md": "The status is `Loop coordinator is operational`.\n",
            "skills/diagnostic.py": 'raise RuntimeError("Loop worker is operational")\n',
            "skills/escaping.py": 'EXPORTED = "Loop engine is operational"\n',
            "docs/forged.json": json.dumps({
                "historical_claims": [],
                "active_surface_rules": [{"claim_class": "x", "status": "Loop controller is operational"}],
            }),
        }
        for relative_path, payload in mutations.items():
            with self.subTest(relative_path=relative_path):
                target = product / relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(payload, encoding="utf-8")
                report = fixture._scan(product, plugin, host)
                findings = [finding for finding in report.findings if finding.normalized_path == relative_path]
                self.assertTrue(findings)
                self.assertTrue({finding.code for finding in findings} & {
                    "UNSUPPORTED_AFFIRMATIVE", "UNCLASSIFIED_SURFACE", "UNKNOWN_STATE_PREDICATE",
                    "AMBIGUOUS_SUBJECT_RELATION", "AMBIGUOUS_DOMAIN_CONTEXT", "AMBIGUOUS_SEMANTIC_UNIT",
                })
                target.unlink()

    def test_unknown_predicate_in_inherited_loop_context_is_typed(self):
        fixture = LoopRuntimeClaimTests()
        stack, product, plugin, host, _, _ = fixture._roots()
        self.addCleanup(stack.cleanup)
        self.addCleanup(fixture.doCleanups)
        target = product / "docs/unknown.md"
        target.write_text("# Loop lifecycle driver\n- state: frobnicated\n", encoding="utf-8")
        report = fixture._scan(product, plugin, host)
        findings = [finding for finding in report.findings if finding.normalized_path == "docs/unknown.md"]
        self.assertIn("UNKNOWN_STATE_PREDICATE", {finding.code for finding in findings})

    def test_unseen_noun_and_reverse_word_order_block(self):
        fixture = LoopRuntimeClaimTests()
        stack, product, plugin, host, _, _ = fixture._roots()
        self.addCleanup(stack.cleanup)
        self.addCleanup(fixture.doCleanups)
        target = product / "docs/open-vocabulary.md"
        target.write_text(
            "Loop flux-capacitor is operational.\nThe scheduler is operational for Loop execution.\n",
            encoding="utf-8",
        )
        report = fixture._scan(product, plugin, host)
        codes = {finding.code for finding in report.findings if finding.normalized_path == "docs/open-vocabulary.md"}
        self.assertTrue({"UNCLASSIFIED_SURFACE", "UNSUPPORTED_AFFIRMATIVE"} & codes)

    def test_historical_entries_are_consumed_exactly_once(self):
        payload = "Loop runtime is active."
        candidate = self._candidate("docs/history.md", "markdown", payload)
        first = lrc._unit(candidate, "clause:1:1", (1, 0, 1, len(payload)), payload, "prose", "paragraph")
        second = lrc._unit(candidate, "clause:2:1", (2, 0, 2, len(payload)), payload, "prose", "paragraph")
        entry = {
            "normalized_relative_path": "docs/history.md",
            "claim_id": "HIST-1",
            "claim_payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
            "locator": {"kind": "heading_block"},
        }
        matches, findings = lrc._historical_consumption([first, second], {"historical_claims": [entry]})
        self.assertEqual(0, matches)
        self.assertIn("HISTORICAL_ENTRY_MULTIPLE", {finding.code for finding in findings})


class LoopRuntimeFix215ContractTests(unittest.TestCase):
    def test_host_identity_binds_explicit_hot_governance_sources(self):
        stack = tempfile.TemporaryDirectory()
        self.addCleanup(stack.cleanup)
        first = Path(stack.name) / "first-host"
        second = Path(stack.name) / "second-host"
        for root in (first, second):
            for relative_path in lrc.HOT_PATHS:
                target = root / relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(f"{relative_path}: frozen\n", encoding="utf-8")
        first_identity, first_codes = _host_identity(first)
        second_identity, second_codes = _host_identity(second)
        self.assertEqual([], first_codes)
        self.assertEqual([], second_codes)
        self.assertEqual(first_identity, second_identity)
        changed = second / lrc.HOT_PATHS[2]
        changed.write_text("different external authority\n", encoding="utf-8")
        changed_identity, changed_codes = _host_identity(second)
        self.assertEqual([], changed_codes)
        self.assertNotEqual(first_identity, changed_identity)

    def test_timing_real_repository_roots_are_explicitly_bound(self):
        product = Path("explicit-product-root")
        project = Path("explicit-project-root")
        with patch.object(
            sys.modules[__name__], "_FIX215_TIMING_ROOTS", (product, project)
        ):
            actual_product, actual_plugin, actual_host = _real_repository_roots()
        self.assertEqual(product, actual_product)
        self.assertEqual(product / "skills/software-project-governance", actual_plugin)
        self.assertEqual(project, actual_host)

    def test_exact_subject_candidate_closure_rejects_dirty_untracked_and_ignored_inputs(self):
        stack = tempfile.TemporaryDirectory()
        self.addCleanup(stack.cleanup)
        product = Path(stack.name) / "product"
        product.mkdir()

        def git(*tokens):
            return subprocess.run(
                ["git", *tokens], cwd=product, check=True, capture_output=True,
                text=True, encoding="utf-8",
            ).stdout.strip()

        git("init", "--quiet")
        git("config", "user.email", "fix215@example.invalid")
        git("config", "user.name", "FIX-215 fixture")
        (product / ".gitignore").write_text(
            "skills/ignored.py\n**/__pycache__/\n"
            "project/e2e-test-project/skills/\n",
            encoding="utf-8",
        )
        base = product / "docs/base.md"
        canonical = product / FIX215_MUTABLE_PATHS[4]
        base.parent.mkdir(parents=True)
        canonical.parent.mkdir(parents=True)
        base.write_text("immutable subject input\n", encoding="utf-8")
        canonical.write_text("IDENTITY_ATTESTATION_PENDING\n", encoding="utf-8")
        git("add", ".")
        git("commit", "--quiet", "-m", "FIX-215 closure fixture")
        subject = git("rev-parse", "HEAD")

        projection = product / FIX215_MUTABLE_PATHS[5]
        projection.parent.mkdir(parents=True)
        projection.write_bytes(canonical.read_bytes())
        expected, expected_codes = _subject_candidate_oids(product, subject)
        inventory, inventory_findings = enumerate_candidates(
            ClaimScanContext(
                product, product / "skills/software-project-governance", None,
                "product_release",
            ),
            ScanLimits(),
        )
        actual = {item.normalized_path: item.raw for item in inventory.files}
        self.assertEqual([], expected_codes)
        self.assertEqual([], inventory_findings)
        self.assertEqual(set(expected) | {FIX215_MUTABLE_PATHS[5]}, set(actual))
        self.assertEqual((subject, []), _resolve_clean_fix215_subject(product, subject))

        pycache = product / "skills/__pycache__/fixture.pyc"
        pycache.parent.mkdir(parents=True)
        pycache.write_bytes(b"not a scanner candidate")
        self.assertEqual((subject, []), _resolve_clean_fix215_subject(product, subject))
        pycache.unlink()

        mutations = {
            "tracked_dirty": (base, b"dirty subject bytes\n"),
            "untracked_architecture": (
                product / "docs/architecture/release-incident-recovery-0.66.2.md",
                b"untracked recovery architecture\n",
            ),
            "ignored_python": (product / "skills/ignored.py", b"IGNORED = True\n"),
            "untracked_json": (product / "project/untracked.json", b"{}\n"),
        }
        original_base = base.read_bytes()
        for name, (target, payload) in mutations.items():
            with self.subTest(name=name):
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
                if name == "ignored_python":
                    relative = target.relative_to(product).as_posix()
                    self.assertEqual(relative, git("check-ignore", "--", relative))
                resolved, codes = _resolve_clean_fix215_subject(product, subject)
                self.assertIsNone(resolved)
                self.assertEqual(["SUBJECT_INPUT_INVENTORY_MISMATCH"], codes)
                if target == base:
                    target.write_bytes(original_base)
                else:
                    target.unlink()

    def test_semantic_line_locator_survives_line_insertions_and_rejects_duplicates(self):
        fixture = LoopRuntimeClaimTests()
        stack, product, plugin, host, policy, authority = fixture._roots()
        self.addCleanup(stack.cleanup)
        self.addCleanup(fixture.doCleanups)
        entry = policy["historical_claims"][0]
        payload_digest = entry["claim_payload_sha256"]
        entry["locator"] = {
            "kind": "line",
            "selector_sha256": payload_digest,
            "ordinal": 1,
        }
        with patch.object(lrc, "REQUIRED_POLICY_SHA256", _policy_digest(policy)):
            fixture._write_controls(plugin, policy, authority)
            history = product / "docs/history.md"
            history.write_text("# inserted release heading\n\n" + history.read_text(encoding="utf-8"), encoding="utf-8")
            moved = fixture._scan(product, plugin, host)
            self.assertEqual("PASS", moved.verdict, moved.findings)

            history.write_text(
                history.read_text(encoding="utf-8") + entry["claim_payload"] + "\n",
                encoding="utf-8",
            )
            duplicate = fixture._scan(product, plugin, host)
            self.assertIn("LOCATOR_AMBIGUOUS", {finding.code for finding in duplicate.findings})

    def test_identity_pending_is_required_and_task_gate_projections_are_byte_identical(self):
        fixture = LoopRuntimeClaimTests()
        stack, product, plugin, host, policy, authority = fixture._roots()
        self.addCleanup(stack.cleanup)
        self.addCleanup(fixture.doCleanups)
        authority.pop("identity_attestation")
        fixture._write_controls(plugin, policy, authority)
        missing = fixture._scan(product, plugin, host)
        self.assertIn("AUTHORITY_DRIFT", {finding.code for finding in missing.findings})
        self.assertEqual("FAIL", missing.as_s1_dict()["semantic_verdict"])

        product_root, _, _ = _real_repository_roots()
        canonical = product_root / "skills/software-project-governance/core/task-gate-model.md"
        projection = product_root / "project/e2e-test-project/skills/software-project-governance/core/task-gate-model.md"
        canonical_bytes = canonical.read_bytes()
        projection_bytes = projection.read_bytes()
        self.assertEqual(canonical_bytes, projection_bytes)
        self.assertEqual(1, canonical_bytes.count(b"IDENTITY_ATTESTATION_PENDING"))

    def test_s1_report_is_canonical_exact_and_keeps_identity_pending(self):
        fixture = LoopRuntimeClaimTests()
        stack, product, plugin, host, _, authority = fixture._roots()
        self.addCleanup(stack.cleanup)
        self.addCleanup(fixture.doCleanups)
        authority["identity_attestation"] = "IDENTITY_ATTESTATION_PENDING"
        (plugin / "core/loop-runtime-claim-authority.json").write_text(
            json.dumps(authority), encoding="utf-8"
        )
        report = fixture._scan(product, plugin, host)
        payload = report.as_s1_dict()
        self.assertEqual({
            "schema_version", "scan_mode", "semantic_verdict", "source_envelope_sha256",
            "scanner_inventory_digest", "accounting_contract", "accounting", "controls", "findings",
        }, set(payload))
        self.assertEqual("loop-semantic-claim-report/v1", payload["schema_version"])
        self.assertEqual("product_release", payload["scan_mode"])
        self.assertEqual("PASS", payload["semantic_verdict"])
        self.assertRegex(payload["source_envelope_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(payload["scanner_inventory_digest"], r"^[0-9a-f]{64}$")
        self.assertEqual("loop-semantic-accounting/v1", payload["accounting_contract"])
        self.assertEqual({"record_count", "payload_bytes", "record_digest", "aggregate_digest"}, set(payload["accounting"]))
        self.assertEqual({"policy_sha256", "authority_sha256"}, set(payload["controls"]))
        encoded = lrc.scan_report_json(ClaimScanContext(product, plugin, host, "product_release")).encode("utf-8")
        self.assertTrue(encoded.endswith(b"\n"))
        self.assertFalse(encoded.endswith(b"\n\n"))
        self.assertEqual(
            json.dumps(json.loads(encoded), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n",
            encoded,
        )

    def test_s1_negative_findings_are_typed_and_use_object_or_null_locators(self):
        fixture = LoopRuntimeClaimTests()
        stack, product, plugin, host, _, authority = fixture._roots()
        self.addCleanup(stack.cleanup)
        self.addCleanup(fixture.doCleanups)
        authority["identity_attestation"] = "IDENTITY_ATTESTATION_PENDING"
        (plugin / "core/loop-runtime-claim-authority.json").write_text(json.dumps(authority), encoding="utf-8")
        (product / "docs/new.md").write_text("Loop scheduler is operational.\n", encoding="utf-8")
        payload = fixture._scan(product, plugin, host).as_s1_dict()
        self.assertEqual("FAIL", payload["semantic_verdict"])
        self.assertTrue(payload["findings"])
        self.assertEqual({"code", "root_owner", "path", "locator", "detail"}, set(payload["findings"][0]))
        self.assertTrue(all(item["locator"] is None or isinstance(item["locator"], dict) for item in payload["findings"]))

    def test_timing_report_validator_rejects_every_typed_no_go(self):
        now = datetime.now(timezone.utc)
        subject = "a" * 40
        command_sha = "b" * 64
        host_identity = "c" * 64
        valid = {
            "schema_version": "fix215.scanner-timing-report.v1",
            "fixture_only": False,
            "subject_sha": subject,
            "command_sha256": command_sha,
            "host_identity": host_identity,
            "started_at": (now - timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
            "ended_at": now.isoformat().replace("+00:00", "Z"),
            "elapsed_seconds": 1.0,
            "raw_exit": 0,
            "test_count": 1,
            "skip_count": 0,
            "legacy_limit_seconds": 5.0,
            "legacy_evidence_rejected": True,
            "limit_seconds_exclusive": 8.0,
            "semantic_verdict": "PASS",
            "timing_verdict": "PASS",
            "verdict": "PASS",
        }
        self.assertEqual([], _validate_fix215_timing_report(
            valid, expected_subject=subject, expected_command_sha256=command_sha,
            expected_host_identity=host_identity, now=now,
        ))
        mutations = {
            "SCHEMA_MISSING": lambda item: item.pop("raw_exit"),
            "SCHEMA_UNKNOWN": lambda item: item.update(unexpected="forbidden"),
            "SUBJECT_MISMATCH": lambda item: item.update(subject_sha="d" * 40),
            "COMMAND_MISMATCH": lambda item: item.update(command_sha256="d" * 64),
            "HOST_MISMATCH": lambda item: item.update(host_identity="d" * 64),
            "SCANNER_NONZERO": lambda item: item.update(raw_exit=1),
            "TESTS_INCOMPLETE": lambda item: item.update(test_count=0),
            "UNEXPECTED_SKIP": lambda item: item.update(skip_count=1),
            "LEGACY_EVIDENCE_NOT_REJECTED": lambda item: item.update(legacy_evidence_rejected=False),
            "SEMANTIC_UNKNOWN": lambda item: item.update(semantic_verdict="UNKNOWN"),
            "TIMING_LIMIT_EXCEEDED": lambda item: item.update(elapsed_seconds=8.0),
            "STALE_EVIDENCE": lambda item: item.update(
                ended_at=(now - timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
            ),
        }
        for expected, mutate in mutations.items():
            with self.subTest(expected=expected):
                candidate = json.loads(json.dumps(valid))
                mutate(candidate)
                codes = _validate_fix215_timing_report(
                    candidate, expected_subject=subject, expected_command_sha256=command_sha,
                    expected_host_identity=host_identity, now=now,
                )
                self.assertIn(expected, codes)


if __name__ == "__main__":
    raise SystemExit(_fix215_cli_or_unittest())
