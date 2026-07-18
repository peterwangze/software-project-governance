"""FIX-216 independent three-root identity and aggregate acceptance tests."""

from __future__ import annotations

import ast
import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path


_HERE = Path(__file__).resolve().parent
_INFRA = _HERE.parent
if str(_INFRA) not in sys.path:
    sys.path.insert(0, str(_INFRA))

from checks import loop_runtime_claim_attestation as lra
from checks import loop_runtime_claims as lrc


EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
I1_FIELDS = {
    "schema_version", "phase", "scan_mode", "subject", "bindings",
    "source_envelope_sha256", "required_paths_digest", "accounting_contract",
    "accounting", "identity_verdict", "created_at",
}


def _git(repo: Path, *args: str, input_bytes: bytes | None = None) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args], input=input_bytes,
        capture_output=True, check=True,
    )
    return completed.stdout.decode("utf-8", errors="strict").strip()


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


class ExplicitSourceFixture:
    def __init__(self, root: Path):
        self.root = root
        self.repo = root / "repo"
        self.host = root / "host"
        self.snapshot_a = root / "artifacts" / "snapshot-a"
        self.snapshot_b = root / "artifacts" / "snapshot-b"
        self.repo.mkdir()
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "user.name", "FIX-216 Fixture")
        _git(self.repo, "config", "user.email", "fix216@example.invalid")
        _write(self.repo / "docs" / "claim.md", b"# Loop runtime\n\nnot active\n")
        _write(
            self.repo / "skills" / "software-project-governance" / "core" /
            "loop-runtime-claim-allowlist.json",
            b'{"required_paths":[]}\n',
        )
        _write(
            self.repo / "skills" / "software-project-governance" / "core" /
            "loop-runtime-claim-authority.json",
            b'{"identity_attestation":"IDENTITY_ATTESTATION_PENDING",'
            b'"source_records":[{"path":".governance/decision-log.md"}]}\n',
        )
        for name in ("plan-tracker.md", "session-snapshot.md", "evidence-log.md", "risk-log.md"):
            _write(self.host / ".governance" / name, f"# {name}\n".encode())
        _write(self.host / ".governance" / "decision-log.md", b"# decision-log.md\n")
        _git(self.repo, "add", "--all")

    def attest_index(self, *, snapshot: Path | None = None) -> dict:
        return lra.attest_explicit_sources(
            product_git_repo=self.repo,
            product_git_ref=":index",
            product_prefix="",
            plugin_git_repo=self.repo,
            plugin_git_ref=":index",
            plugin_prefix="skills/software-project-governance",
            host_root=self.host,
            snapshot_dir=snapshot or self.snapshot_a,
            required_paths=(
                ("product_root", "docs/claim.md"),
                ("plugin_home", "core/loop-runtime-claim-allowlist.json"),
                ("host_root", ".governance/plan-tracker.md"),
            ),
            phase="staged_index",
            subject={"kind": "index", "sha": None},
            created_at="2026-07-18T00:00:00Z",
        )

    def commit(self) -> str:
        _git(self.repo, "commit", "-qm", "fixture")
        return _git(self.repo, "rev-parse", "HEAD")

    def commit_same_tree(self) -> str:
        _git(self.repo, "commit", "--allow-empty", "-qm", "same tree, new commit")
        return _git(self.repo, "rev-parse", "HEAD")

    def candidate_envelope(self, *, product_ref: str, subject_sha: str,
                           snapshot: Path, plugin_ref: str | None = None) -> dict:
        return {
            "product_git_repo": self.repo,
            "product_git_ref": product_ref,
            "product_prefix": "",
            "plugin_git_repo": self.repo,
            "plugin_git_ref": plugin_ref or product_ref,
            "plugin_prefix": "skills/software-project-governance",
            "host_root": self.host,
            "snapshot_dir": snapshot,
            "required_paths": (
                ("product_root", "docs/claim.md"),
                ("plugin_home", "core/loop-runtime-claim-allowlist.json"),
                ("host_root", ".governance/plan-tracker.md"),
            ),
            "phase": "candidate_commit",
            "subject": {"kind": "commit", "sha": subject_sha},
            "created_at": "2026-07-18T00:00:01Z",
        }

    def attest_commit(self, commit: str, *, snapshot: Path | None = None) -> dict:
        return lra.attest_explicit_sources(
            product_git_repo=self.repo,
            product_git_ref=commit,
            product_prefix="",
            plugin_git_repo=self.repo,
            plugin_git_ref=commit,
            plugin_prefix="skills/software-project-governance",
            host_root=self.host,
            snapshot_dir=snapshot or self.snapshot_b,
            required_paths=(
                ("product_root", "docs/claim.md"),
                ("plugin_home", "core/loop-runtime-claim-allowlist.json"),
                ("host_root", ".governance/plan-tracker.md"),
            ),
            phase="candidate_commit",
            subject={"kind": "commit", "sha": commit},
            created_at="2026-07-18T00:00:01Z",
        )


class IndependentAttestorTests(unittest.TestCase):
    def test_module_has_no_scanner_import_or_enumerator_reference(self):
        source_path = _INFRA / "checks" / "loop_runtime_claim_attestation.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported = []
        called = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    called.append(node.func.attr)
        joined = "\n".join(imported)
        self.assertNotIn("loop_runtime_claims", joined)
        self.assertFalse({"enumerate_candidates", "_account_candidate"} & set(called))

    def test_index_report_is_exact_canonical_i1_schema(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = ExplicitSourceFixture(Path(td))
            report = fixture.attest_index()
        self.assertEqual(I1_FIELDS, set(report))
        self.assertEqual("loop-identity-attestation/v1", report["schema_version"])
        self.assertEqual("staged_index", report["phase"])
        self.assertEqual({"kind": "index", "sha": None}, report["subject"])
        self.assertEqual("PASS", report["identity_verdict"])
        self.assertEqual({"product_root", "plugin_home", "host_root"}, set(report["bindings"]))
        self.assertTrue(lra.is_canonical_json(lra.canonical_json_bytes(report)))
        self.assertNotIn("fixture_only", report)
        self.assertNotIn("release_authorized", report)

    def test_canonical_json_accepts_finite_measurements_but_rejects_nan(self):
        self.assertEqual(b'{"time_seconds":1.25}\n', lra.canonical_json_bytes({"time_seconds": 1.25}))
        with self.assertRaisesRegex(lra.IdentityAttestationError, "TYPE_DRIFT"):
            lra.canonical_json_bytes({"time_seconds": float("nan")})

    def test_verified_fixture_index_to_commit_is_the_only_legal_transition(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = ExplicitSourceFixture(Path(td))
            index = fixture.attest_index()
            commit = fixture.commit()
            final = fixture.attest_commit(commit)
            result = lra.compare_identity_attestations(
                index, final, fixture_only=True, verified_fixture_commit=commit,
            )
        self.assertEqual("PASS", result["verdict"])
        self.assertTrue(result["fixture_only"])
        self.assertFalse(result["release_authorized"])
        self.assertFalse(result["authorized"])
        self.assertEqual([], result["issues"])

        with tempfile.TemporaryDirectory() as td:
            fixture = ExplicitSourceFixture(Path(td))
            external = Path(td) / "external-plugin"
            external.mkdir()
            _git(external, "init", "-q")
            _git(external, "config", "user.name", "FIX-216 External Plugin")
            _git(external, "config", "user.email", "fix216-plugin@example.invalid")
            plugin_source = fixture.repo / "skills" / "software-project-governance"
            for source in plugin_source.rglob("*"):
                if source.is_file():
                    _write(external / source.relative_to(plugin_source), source.read_bytes())
            _git(external, "add", "--all")
            _git(external, "commit", "-qm", "external plugin")
            plugin_tree = _git(external, "rev-parse", "HEAD^{tree}")

            def attest(product_ref: str, phase: str, subject: dict, snapshot: Path) -> dict:
                return lra.attest_explicit_sources(
                    product_git_repo=fixture.repo, product_git_ref=product_ref, product_prefix="",
                    plugin_git_repo=external, plugin_git_ref=plugin_tree, plugin_prefix="",
                    host_root=fixture.host, snapshot_dir=snapshot,
                    required_paths=(("plugin_home", "core/loop-runtime-claim-allowlist.json"),),
                    phase=phase, subject=subject, created_at="2026-07-18T00:00:00Z",
                )

            index = attest(":index", "staged_index", {"kind": "index", "sha": None},
                           fixture.snapshot_a)
            commit = fixture.commit()
            final = attest(commit, "candidate_commit", {"kind": "commit", "sha": commit},
                           fixture.snapshot_b)
            result = lra.compare_identity_attestations(
                index, final, fixture_only=True, verified_fixture_commit=commit,
            )
        self.assertEqual("PASS", result["verdict"])
        self.assertEqual(plugin_tree, index["bindings"]["plugin_home"]["selected_tree_oid"])

    def test_candidate_leaf_rejects_same_tree_different_subject_commit(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = ExplicitSourceFixture(Path(td))
            commit_a = fixture.commit()
            commit_b = fixture.commit_same_tree()
            tree_a = _git(fixture.repo, "rev-parse", f"{commit_a}^{{tree}}")
            tree_b = _git(fixture.repo, "rev-parse", f"{commit_b}^{{tree}}")
            self.assertNotEqual(commit_a, commit_b)
            self.assertEqual(tree_a, tree_b)

            forged = fixture.candidate_envelope(
                product_ref=commit_a, subject_sha=commit_b,
                snapshot=fixture.root / "artifacts" / "leaf-forged",
            )
            with self.assertRaisesRegex(lra.IdentityAttestationError, "SUBJECT_MISMATCH"):
                lra.attest_explicit_sources(**forged)

            exact = lra.attest_explicit_sources(**fixture.candidate_envelope(
                product_ref=commit_a, subject_sha=commit_a,
                snapshot=fixture.root / "artifacts" / "leaf-exact",
            ))
            self.assertEqual({"kind": "commit", "sha": commit_a}, exact["subject"])

            product_tree = fixture.candidate_envelope(
                product_ref=tree_a, subject_sha=commit_a, plugin_ref=commit_a,
                snapshot=fixture.root / "artifacts" / "product-tree",
            )
            with self.assertRaisesRegex(lra.IdentityAttestationError, "ROOT_SOURCE_UNAVAILABLE"):
                lra.attest_explicit_sources(**product_tree)

    def test_architecture_entry_rejects_same_tree_different_subject_commit(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = ExplicitSourceFixture(Path(td))
            commit_a = fixture.commit()
            commit_b = fixture.commit_same_tree()
            self.assertEqual(
                _git(fixture.repo, "rev-parse", f"{commit_a}^{{tree}}"),
                _git(fixture.repo, "rev-parse", f"{commit_b}^{{tree}}"),
            )
            forged = fixture.candidate_envelope(
                product_ref=commit_a, subject_sha=commit_b,
                snapshot=fixture.root / "artifacts" / "entry-forged",
            )
            with self.assertRaisesRegex(lra.IdentityAttestationError, "SUBJECT_MISMATCH"):
                lra.attest_loop_runtime_identity(None, forged)

    def test_transition_never_accepts_same_tree_substituted_subject(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = ExplicitSourceFixture(Path(td))
            staged = fixture.attest_index()
            commit_a = fixture.commit()
            commit_b = fixture.commit_same_tree()
            self.assertEqual(
                _git(fixture.repo, "rev-parse", f"{commit_a}^{{tree}}"),
                _git(fixture.repo, "rev-parse", f"{commit_b}^{{tree}}"),
            )
            forged_envelope = fixture.candidate_envelope(
                product_ref=commit_a, subject_sha=commit_b,
                snapshot=fixture.root / "artifacts" / "transition-forged",
            )
            try:
                forged = lra.attest_explicit_sources(**forged_envelope)
            except lra.IdentityAttestationError as exc:
                self.assertEqual("SUBJECT_MISMATCH", exc.code)
            else:
                result = lra.compare_identity_attestations(
                    staged, forged, fixture_only=True, verified_fixture_commit=commit_b,
                )
                self.assertEqual("FAIL", result["verdict"])
                self.assertIn("SUBJECT_MISMATCH", result["issues"])

            exact = lra.attest_explicit_sources(**fixture.candidate_envelope(
                product_ref=commit_a, subject_sha=commit_a,
                snapshot=fixture.root / "artifacts" / "transition-exact",
            ))
            substituted = lra.compare_identity_attestations(
                staged, exact, fixture_only=True, verified_fixture_commit=commit_b,
            )
            self.assertEqual("FAIL", substituted["verdict"])
            self.assertIn("FIXTURE_COMMIT_UNVERIFIED", substituted["issues"])
            accepted = lra.compare_identity_attestations(
                staged, exact, fixture_only=True, verified_fixture_commit=commit_a,
            )
            self.assertEqual("PASS", accepted["verdict"])

    def test_stale_index_attestation_is_rejected_after_staged_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = ExplicitSourceFixture(Path(td))
            index = fixture.attest_index()
            _write(fixture.repo / "docs" / "claim.md", b"# changed\n")
            _git(fixture.repo, "add", "docs/claim.md")
            commit = fixture.commit()
            final = fixture.attest_commit(commit)
            result = lra.compare_identity_attestations(
                index, final, fixture_only=True, verified_fixture_commit=commit,
            )
        self.assertEqual("FAIL", result["verdict"])
        self.assertIn("CANDIDATE_ATTESTATION_STALE", result["issues"])

    def test_missing_required_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = ExplicitSourceFixture(Path(td))
            with self.assertRaisesRegex(lra.IdentityAttestationError, "REQUIRED_ROOT_UNAVAILABLE"):
                lra.attest_explicit_sources(
                    product_git_repo=fixture.repo, product_git_ref=":index", product_prefix="",
                    plugin_git_repo=fixture.repo, plugin_git_ref=":index",
                    plugin_prefix="skills/software-project-governance",
                    host_root=fixture.host, snapshot_dir=fixture.snapshot_a,
                    required_paths=(("product_root", "missing.md"),),
                    phase="staged_index", subject={"kind": "index", "sha": None},
                )

    def test_alias_and_reparse_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = ExplicitSourceFixture(Path(td))
            with self.assertRaisesRegex(lra.IdentityAttestationError, "ROOT_SOURCE_AMBIGUOUS"):
                lra.attest_explicit_sources(
                    product_git_repo=fixture.repo, product_git_ref=":index", product_prefix="docs/../docs",
                    plugin_git_repo=fixture.repo, plugin_git_ref=":index",
                    plugin_prefix="skills/software-project-governance",
                    host_root=fixture.host, snapshot_dir=fixture.snapshot_a,
                    required_paths=(), phase="staged_index", subject={"kind": "index", "sha": None},
                )
            if hasattr(os, "symlink"):
                alias = Path(td) / "host-alias"
                try:
                    os.symlink(fixture.host, alias, target_is_directory=True)
                except OSError:
                    return
                with self.assertRaisesRegex(lra.IdentityAttestationError, "ROOT_SOURCE_AMBIGUOUS"):
                    lra.attest_explicit_sources(
                        product_git_repo=fixture.repo, product_git_ref=":index", product_prefix="",
                        plugin_git_repo=fixture.repo, plugin_git_ref=":index",
                        plugin_prefix="skills/software-project-governance",
                        host_root=alias, snapshot_dir=fixture.snapshot_a,
                        required_paths=(), phase="staged_index", subject={"kind": "index", "sha": None},
                    )
            with self.assertRaisesRegex(lra.IdentityAttestationError, "ROOT_SOURCE_AMBIGUOUS"):
                fixture.attest_index(snapshot=fixture.host / "nested-snapshot")
            with self.assertRaisesRegex(lra.IdentityAttestationError, "ROOT_SOURCE_AMBIGUOUS"):
                fixture.attest_index(snapshot=fixture.repo / "nested-snapshot")

    def test_hardlink_and_nonregular_host_entries_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = ExplicitSourceFixture(Path(td))
            source = fixture.host / ".governance" / "plan-tracker.md"
            hardlink = fixture.host / ".governance" / "hardlink.md"
            try:
                os.link(source, hardlink)
            except OSError:
                self.skipTest("hardlinks unavailable")
            with self.assertRaisesRegex(lra.IdentityAttestationError, "ROOT_SOURCE_AMBIGUOUS"):
                fixture.attest_index()

    def test_nonregular_required_host_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = ExplicitSourceFixture(Path(td))
            target = fixture.host / ".governance" / "risk-log.md"
            target.unlink()
            target.mkdir()
            with self.assertRaisesRegex(lra.IdentityAttestationError, "REQUIRED_PATH_NOT_REGULAR"):
                fixture.attest_index()

    def test_missing_root_is_unknown_not_pass(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = ExplicitSourceFixture(Path(td))
            with self.assertRaisesRegex(lra.IdentityAttestationError, "ROOT_SOURCE_UNAVAILABLE"):
                lra.attest_explicit_sources(
                    product_git_repo=fixture.repo / "missing", product_git_ref=":index",
                    product_prefix="", plugin_git_repo=fixture.repo, plugin_git_ref=":index",
                    plugin_prefix="skills/software-project-governance",
                    host_root=fixture.host, snapshot_dir=fixture.snapshot_a,
                    required_paths=(), phase="staged_index",
                    subject={"kind": "index", "sha": None},
                )

    def test_unknown_i1_field_and_version_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = ExplicitSourceFixture(Path(td))
            report = fixture.attest_index()
        report["alias"] = "forged"
        with self.assertRaisesRegex(lra.IdentityAttestationError, "SCHEMA_UNKNOWN"):
            lra.validate_identity_attestation(report)
        report.pop("alias")
        report["schema_version"] = "loop-identity-attestation/v2"
        with self.assertRaisesRegex(lra.IdentityAttestationError, "SCHEMA_UNKNOWN"):
            lra.validate_identity_attestation(report)
        report["schema_version"] = "loop-identity-attestation/v1"
        nested = copy.deepcopy(report)
        nested["bindings"]["product_root"]["repository_identity"]["alias"] = "forged"
        with self.assertRaisesRegex(lra.IdentityAttestationError, "SCHEMA_UNKNOWN"):
            lra.validate_identity_attestation(nested)
        wrong_type = copy.deepcopy(report)
        wrong_type["accounting"]["record_count"] = True
        with self.assertRaisesRegex(lra.IdentityAttestationError, "TYPE_DRIFT"):
            lra.validate_identity_attestation(wrong_type)
        digest_drift = copy.deepcopy(report)
        digest_drift["bindings"]["host_root"]["manifest_digest"] = "0" * 64
        with self.assertRaisesRegex(lra.IdentityAttestationError, "DIGEST_MISMATCH"):
            lra.validate_identity_attestation(digest_drift)

    def test_every_non_index_to_commit_transition_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = ExplicitSourceFixture(Path(td))
            index = fixture.attest_index()
            commit = fixture.commit()
            final = fixture.attest_commit(commit)
            result = lra.compare_identity_attestations(
                final, final, fixture_only=True, verified_fixture_commit=commit,
            )
        self.assertEqual("FAIL", result["verdict"])
        self.assertIn("CANDIDATE_SOURCE_BINDING_MISMATCH", result["issues"])

    def test_accounting_or_source_inequality_never_authorizes(self):
        with tempfile.TemporaryDirectory() as td:
            fixture = ExplicitSourceFixture(Path(td))
            identity = fixture.attest_index()
        semantic = {
            "schema_version": "loop-semantic-claim-report/v1", "semantic_verdict": "PASS",
            "source_envelope_sha256": identity["source_envelope_sha256"],
            "accounting_contract": "loop-semantic-accounting/v1",
            "accounting": dict(identity["accounting"]),
        }
        semantic["accounting"]["record_count"] += 1
        aggregate = lra.aggregate_claim_reports(
            semantic, identity, fixture_only=True, performance_budget_status="REVIEWED",
        )
        self.assertEqual("FAIL", aggregate["verdict"])
        self.assertFalse(aggregate["authorized"])
        self.assertIn("INDEPENDENT_ACCOUNTING_MISMATCH", aggregate["issues"])

    def test_installed_not_applicable_never_authorizes(self):
        semantic = {
            "schema_version": "loop-semantic-claim-report/v1",
            "semantic_verdict": "NOT_APPLICABLE",
            "source_envelope_sha256": EMPTY_SHA256,
            "accounting_contract": "loop-semantic-accounting/v1",
            "accounting": {"record_count": 0, "payload_bytes": 0,
                           "record_digest": EMPTY_SHA256, "aggregate_digest": EMPTY_SHA256},
        }
        identity = {key: None for key in I1_FIELDS}
        identity.update({
            "schema_version": "loop-identity-attestation/v1",
            "identity_verdict": "NOT_APPLICABLE",
            "source_envelope_sha256": EMPTY_SHA256,
            "accounting_contract": "loop-semantic-accounting/v1",
            "accounting": semantic["accounting"],
        })
        aggregate = lra.aggregate_claim_reports(
            semantic, identity, fixture_only=True, performance_budget_status="PENDING",
        )
        self.assertEqual("NOT_APPLICABLE", aggregate["verdict"])
        self.assertFalse(aggregate["authorized"])
        self.assertFalse(aggregate["release_authorized"])

    def test_unknown_unequal_and_pending_are_non_authorizing(self):
        semantic = {
            "schema_version": "loop-semantic-claim-report/v1", "semantic_verdict": "PASS",
            "source_envelope_sha256": "a" * 64,
            "accounting_contract": "loop-semantic-accounting/v1",
            "accounting": {"record_count": 1, "payload_bytes": 1,
                           "record_digest": "b" * 64, "aggregate_digest": "c" * 64},
        }
        identity = {
            "schema_version": "loop-identity-attestation/v1", "identity_verdict": "UNKNOWN",
            "source_envelope_sha256": "d" * 64,
            "accounting_contract": "loop-semantic-accounting/v1",
            "accounting": semantic["accounting"],
            **{key: None for key in I1_FIELDS - {
                "schema_version", "identity_verdict", "source_envelope_sha256",
                "accounting_contract", "accounting",
            }},
        }
        aggregate = lra.aggregate_claim_reports(
            semantic, identity, fixture_only=True, performance_budget_status="PENDING",
        )
        self.assertEqual("UNKNOWN", aggregate["verdict"])
        self.assertFalse(aggregate["authorized"])
        self.assertIn("SOURCE_ENVELOPE_MISMATCH", aggregate["issues"])
        self.assertIn("PERFORMANCE_BUDGET_PENDING", aggregate["issues"])

    def test_fixture_evidence_cannot_be_promoted_to_release(self):
        with self.assertRaisesRegex(lra.IdentityAttestationError, "FIXTURE_RELEASE_FORBIDDEN"):
            lra.compare_identity_attestations(
                {}, {}, fixture_only=True, verified_fixture_commit="a" * 40,
                release_authorized=True,
            )


def _fixture_required_paths(repo: Path, commit: str) -> tuple[tuple[str, str], ...]:
    with tempfile.TemporaryDirectory(prefix="fix216-poc-policy-") as td:
        plugin = lrc.materialize_loop_runtime_git_root(
            repo, commit, "skills/software-project-governance", Path(td) / "plugin"
        )
        policy = json.loads(
            (plugin / "core/loop-runtime-claim-allowlist.json").read_text(encoding="utf-8")
        )
    rows = policy.get("required_paths")
    if not isinstance(rows, list):
        raise lra.IdentityAttestationError("SCHEMA_MISSING", "required_paths")
    return tuple((row["root_owner"], row["path"]) for row in rows)


def _process_tree_rss() -> int:
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss + sum(
            child.memory_info().rss for child in process.children(recursive=True)
            if child.is_running()
        )
    except Exception:
        return 0


def _measure(operation) -> tuple[float, int, int, str, dict | None]:
    stop = threading.Event()
    peak = [_process_tree_rss()]

    def sample() -> None:
        while not stop.wait(0.005):
            peak[0] = max(peak[0], _process_tree_rss())

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    started = time.perf_counter()
    try:
        payload = operation()
        exit_code, verdict = 0, "PASS"
    except Exception as exc:
        payload = {"error": f"{type(exc).__name__}: {exc}"}
        exit_code, verdict = 1, "FAIL"
    elapsed = time.perf_counter() - started
    stop.set()
    sampler.join(timeout=1)
    peak[0] = max(peak[0], _process_tree_rss())
    return elapsed, peak[0], exit_code, verdict, payload


def _poc_stage(repo: Path, commit: str, required_paths: tuple[tuple[str, str], ...],
               stage: str) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"fix216-poc-{stage}-") as td:
        root = Path(td)

        def scanner() -> dict:
            product = lrc.materialize_loop_runtime_git_root(repo, commit, "", root / "product")
            plugin = lrc.materialize_loop_runtime_git_root(
                repo, commit, "skills/software-project-governance", root / "plugin"
            )
            report = lrc.scan_loop_runtime_claims(lrc.ClaimScanContext(
                product, plugin, repo, "product_release"
            ))
            payload = report.as_s1_dict()
            if report.verdict != "PASS" or report.skipped_candidates or report.truncated_candidates:
                raise RuntimeError(
                    f"scanner={report.verdict};skip={report.skipped_candidates};"
                    f"truncate={report.truncated_candidates}"
                )
            return {"report": payload, "skip_count": 0,
                    "source_envelope_sha256": payload["source_envelope_sha256"]}

        def attestor() -> dict:
            report = lra.attest_explicit_sources(
                product_git_repo=repo, product_git_ref=commit, product_prefix="",
                plugin_git_repo=repo, plugin_git_ref=commit,
                plugin_prefix="skills/software-project-governance",
                host_root=repo, snapshot_dir=root / "snapshot",
                required_paths=required_paths, phase="candidate_commit",
                subject={"kind": "commit", "sha": commit},
            )
            if report["identity_verdict"] != "PASS":
                raise RuntimeError(report["identity_verdict"])
            return {"report": report, "skip_count": 0,
                    "source_envelope_sha256": report["source_envelope_sha256"]}

        if stage == "scanner":
            return scanner()
        if stage == "attestor":
            return attestor()
        if stage != "aggregate":
            raise ValueError(stage)
        scanner_payload = scanner()
        identity_payload = attestor()
        aggregate = lra.aggregate_claim_reports(
            scanner_payload["report"], identity_payload["report"],
            fixture_only=True, performance_budget_status="PENDING",
        )
        blocking = [issue for issue in aggregate["issues"] if issue != "PERFORMANCE_BUDGET_PENDING"]
        if aggregate["verdict"] != "PASS" or blocking or aggregate["authorized"]:
            raise RuntimeError(f"aggregate={aggregate['verdict']};issues={blocking}")
        return {"report": aggregate, "skip_count": 0,
                "source_envelope_sha256": aggregate["source_envelope_sha256"]}


def _poc_row(run_no: int, measured: tuple[float, int, int, str, dict | None]) -> dict:
    elapsed, peak, exit_code, verdict, payload = measured
    source = payload.get("source_envelope_sha256", EMPTY_SHA256) if isinstance(payload, dict) else EMPTY_SHA256
    skip_count = payload.get("skip_count", 0) if isinstance(payload, dict) else 0
    return {
        "run_no": run_no,
        "time_seconds": round(elapsed, 9),
        "peak_rss_bytes": int(peak),
        "raw_exit": exit_code,
        "skip_count": skip_count,
        "source_envelope_sha256": source,
        "verdict": verdict,
    }


def _run_fix216_poc(args: argparse.Namespace) -> int:
    if not args.fixture_only or args.release_authorized.lower() != "false":
        raise lra.IdentityAttestationError("FIXTURE_RELEASE_FORBIDDEN")
    if args.warmups != 1 or args.runs != 5:
        raise lra.IdentityAttestationError("SCHEMA_UNKNOWN", "PoC requires 1 warmup and 5 runs")
    stage_names = args.stages.split(",")
    if stage_names != ["scanner", "attestor", "aggregate"]:
        raise lra.IdentityAttestationError("SCHEMA_UNKNOWN", "stage order")
    if args.cache_policy != "cold-isolated":
        raise lra.IdentityAttestationError("SCHEMA_UNKNOWN", "cache policy")
    repo = Path(args.fixture_repo).resolve(strict=True)
    commit = _git(repo, "rev-parse", "--verify", f"{args.fixture_commit}^{{commit}}")
    if commit != args.fixture_commit:
        raise lra.IdentityAttestationError("FIXTURE_COMMIT_UNVERIFIED", commit)
    required_paths = _fixture_required_paths(repo, commit)
    warmup = _poc_row(0, _measure(lambda: _poc_stage(repo, commit, required_paths, "aggregate")))
    stages = []
    for stage in stage_names:
        rows = [
            _poc_row(run_no, _measure(lambda stage=stage: _poc_stage(
                repo, commit, required_paths, stage
            )))
            for run_no in range(1, args.runs + 1)
        ]
        stages.append({"stage": stage, "rows": rows})
    all_rows = [warmup, *(row for stage in stages for row in stage["rows"])]
    envelopes = {row["source_envelope_sha256"] for row in all_rows}
    source_envelope = next(iter(envelopes)) if len(envelopes) == 1 else EMPTY_SHA256
    report = {
        "schema_version": "fix216.identity-poc-report.v1",
        "fixture_only": True,
        "release_authorized": False,
        "authorized": False,
        "performance_budget_status": "PENDING",
        "subject_sha": args.subject,
        "fixture_commit_sha": commit,
        "source_envelope_sha256": source_envelope,
        "cache_policy": "cold-isolated",
        "warmups": 1,
        "warmup": warmup,
        "stages": stages,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    output = Path(args.write_report)
    if output.exists():
        raise lra.IdentityAttestationError("CANDIDATE_ATTESTATION_STALE", str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(lra.canonical_json_bytes(report))
    valid = (
        len(envelopes) == 1 and source_envelope != EMPTY_SHA256
        and all(row["raw_exit"] == 0 and row["skip_count"] == args.require_skip_count
                and row["verdict"] == "PASS" for row in all_rows)
    )
    print(json.dumps({
        "schema_version": report["schema_version"], "verdict": "PASS" if valid else "FAIL",
        "fixture_only": True, "release_authorized": False, "authorized": False,
        "performance_budget_status": "PENDING", "report_sha256": hashlib.sha256(
            lra.canonical_json_bytes(report)
        ).hexdigest(),
    }, sort_keys=True, separators=(",", ":")))
    return 0 if valid else 1


def _parse_required_bool(value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise lra.IdentityAttestationError("TYPE_DRIFT", value)


def _validate_fix216_poc(args: argparse.Namespace) -> int:
    raw = Path(args.validate_fix216_poc).read_bytes()
    if not lra.is_canonical_json(raw):
        raise lra.IdentityAttestationError("CANONICAL_BYTES")
    report = json.loads(raw.decode("utf-8"))
    expected_fields = {
        "schema_version", "fixture_only", "release_authorized", "authorized",
        "performance_budget_status", "subject_sha", "fixture_commit_sha",
        "source_envelope_sha256", "cache_policy", "warmups", "warmup", "stages",
        "generated_at",
    }
    if set(report) != expected_fields or report.get("schema_version") != "fix216.identity-poc-report.v1":
        raise lra.IdentityAttestationError("SCHEMA_UNKNOWN", "PoC report")
    expected_stages = args.require_stages.split(",")
    checks = [
        report["subject_sha"] == args.require_subject,
        report["fixture_only"] is _parse_required_bool(args.require_fixture_only),
        report["release_authorized"] is _parse_required_bool(args.require_release_authorized),
        report["authorized"] is False,
        report["performance_budget_status"] == "PENDING",
        report["warmups"] == args.require_warmups == 1,
        [item.get("stage") for item in report["stages"]] == expected_stages,
        all(len(item.get("rows", [])) == args.require_runs for item in report["stages"]),
        report["cache_policy"] == "cold-isolated",
    ]
    all_rows = [report["warmup"], *(row for item in report["stages"] for row in item["rows"])]
    row_fields = {"run_no", "time_seconds", "peak_rss_bytes", "raw_exit", "skip_count",
                  "source_envelope_sha256", "verdict"}
    checks.extend([
        all(set(row) == row_fields for row in all_rows),
        all(row["raw_exit"] == 0 and row["skip_count"] == args.require_skip_count
            and row["verdict"] == "PASS" and row["time_seconds"] > 0
            and isinstance(row["peak_rss_bytes"], int) and row["peak_rss_bytes"] >= 0
            for row in all_rows),
        len({row["source_envelope_sha256"] for row in all_rows}) == 1,
        report["source_envelope_sha256"] == all_rows[0]["source_envelope_sha256"],
    ])
    valid = all(checks)
    print(json.dumps({
        "schema_version": "fix216.identity-poc-validation.v1",
        "verdict": "PASS" if valid else "FAIL", "fixture_only": report["fixture_only"],
        "release_authorized": report["release_authorized"], "authorized": False,
        "performance_budget_status": "PENDING",
    }, sort_keys=True, separators=(",", ":")))
    return 0 if valid else 1


def _poc_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fix216-poc", action="store_true")
    mode.add_argument("--validate-fix216-poc")
    parser.add_argument("--subject")
    parser.add_argument("--fixture-repo")
    parser.add_argument("--fixture-commit")
    parser.add_argument("--fixture-only", action="store_true")
    parser.add_argument("--release-authorized", default="false")
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--stages", default="scanner,attestor,aggregate")
    parser.add_argument("--cache-policy", default="cold-isolated")
    parser.add_argument("--require-same-source-envelope", action="store_true")
    parser.add_argument("--require-skip-count", type=int, default=0)
    parser.add_argument("--write-report")
    parser.add_argument("--require-subject")
    parser.add_argument("--require-fixture-only", default="true")
    parser.add_argument("--require-release-authorized", default="false")
    parser.add_argument("--require-warmups", type=int, default=1)
    parser.add_argument("--require-runs", type=int, default=5)
    parser.add_argument("--require-stages", default="scanner,attestor,aggregate")
    return parser


if __name__ == "__main__":
    if "--fix216-poc" in sys.argv or "--validate-fix216-poc" in sys.argv:
        try:
            parsed = _poc_parser().parse_args()
            if parsed.fix216_poc:
                required = (parsed.subject, parsed.fixture_repo, parsed.fixture_commit, parsed.write_report)
                if not all(required):
                    raise lra.IdentityAttestationError("SCHEMA_MISSING", "PoC arguments")
                raise SystemExit(_run_fix216_poc(parsed))
            raise SystemExit(_validate_fix216_poc(parsed))
        except lra.IdentityAttestationError as exc:
            print(json.dumps({"verdict": "FAIL", "issues": [exc.code], "detail": exc.detail},
                             sort_keys=True, separators=(",", ":")))
            raise SystemExit(1)
    unittest.main()
