"""Regression coverage for FEAT-114's product-level completion gate."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_INFRA = Path(__file__).resolve().parent.parent
if str(_INFRA) not in sys.path:
    sys.path.insert(0, str(_INFRA))

from delivery_acceptance import (  # noqa: E402
    CONTRACT,
    RECEIPT,
    artifact_sha256,
    evaluate_delivery_acceptance,
)


class DeliveryAcceptanceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.gov = self.root / ".governance"
        self.gov.mkdir()
        self.artifact = self.root / "dist"
        self.artifact.mkdir()
        (self.artifact / "index.html").write_bytes(b"<html>Working program</html>")
        self.evidence = self.root / "journey.log"
        self.evidence.write_bytes(b"Opened normal entry and observed expected result\n")
        self.contract = {
            "schema_version": 1,
            "release_version": "0.1.0",
            "goal_id": "delivery-goal",
            "artifact": "dist",
            "entrypoint": "/",
            "producer": "developer",
            "verifier": "independent-qa",
            "criteria": {"user-journey": "A user can reach the expected result"},
        }
        self.receipt = self.write_contract()
        self.write_receipt()

    def write_contract(self):
        raw = json.dumps(self.contract).encode("utf-8")
        (self.root / CONTRACT).write_bytes(raw)
        return {
            "schema_version": 1,
            "contract_sha256": hashlib.sha256(raw).hexdigest(),
            "artifact_sha256": artifact_sha256(self.artifact),
            "entrypoint": self.contract["entrypoint"],
            "verifier": self.contract["verifier"],
            "results": {"user-journey": {
                "status": "PASS",
                "evidence": "journey.log",
                "evidence_sha256": hashlib.sha256(self.evidence.read_bytes()).hexdigest(),
            }},
        }

    def write_receipt(self):
        (self.root / RECEIPT).write_bytes(json.dumps(self.receipt).encode("utf-8"))

    def evaluate(self, **kwargs):
        return evaluate_delivery_acceptance(self.root, release_version="0.1.0", **kwargs)

    def assert_failure(self, verdict, reason):
        self.assertEqual("FAIL", verdict["state"])
        self.assertFalse(verdict["pass"])
        self.assertIn(reason, "\n".join(verdict["issues"]))

    def test_matching_receipt_passes_and_binds_directory_contents(self):
        self.assertTrue(self.evaluate()["pass"])
        (self.artifact / "assets").mkdir()
        (self.artifact / "assets" / "tiles.png").write_bytes(b"new asset")
        self.assert_failure(self.evaluate(), "artifact SHA-256 mismatch")

    def test_normal_entry_and_target_are_required(self):
        self.receipt["entrypoint"] = "/?debugbattle"
        self.write_receipt()
        self.assert_failure(self.evaluate(), "entrypoint does not match")
        self.assert_failure(
            evaluate_delivery_acceptance(self.root, release_version="0.1.1"),
            "release_version must match",
        )
        self.assert_failure(self.evaluate(goal_id="another-goal"), "goal_id must match")

    def test_changed_contract_or_raw_evidence_refuses_old_receipt(self):
        self.evidence.write_bytes(b"overwritten after review")
        self.assert_failure(self.evaluate(), "evidence SHA-256 mismatch")
        contract = self.root / CONTRACT
        contract.write_bytes(contract.read_bytes() + b"\n")
        self.assert_failure(self.evaluate(), "contract_sha256 does not match")

    def test_missing_evidence_or_duplicate_keys_are_not_acceptance(self):
        self.evidence.unlink()
        self.assert_failure(self.evaluate(), "journey.log")
        (self.root / RECEIPT).write_bytes(b'{"schema_version":1,"schema_version":1}')
        self.assert_failure(self.evaluate(), "duplicate JSON property")

    def test_self_review_refuses_even_with_matching_values(self):
        self.contract["producer"] = self.contract["verifier"].upper()
        self.receipt = self.write_contract()
        self.write_receipt()
        self.assert_failure(self.evaluate(), "must be independent")

    def test_missing_extra_and_nonpassing_criteria_block(self):
        prior = self.receipt["results"]["user-journey"]
        cases = [
            ({}, "user-journey: missing result"),
            ({"user-journey": prior, "undeclared": prior}, "unexpected criterion 'undeclared'"),
            ({"user-journey": {**prior, "status": "FAIL", "detail": "froze on menu exit"}},
             "user-journey: FAIL — froze on menu exit"),
            ({"user-journey": {"status": "NOT_RUN"}}, "user-journey: NOT_RUN"),
            ({"user-journey": {"status": "BLOCKED"}}, "user-journey: BLOCKED"),
        ]
        for results, reason in cases:
            with self.subTest(reason=reason):
                self.receipt["results"] = results
                self.write_receipt()
                self.assert_failure(self.evaluate(), reason)

    def test_evidence_must_be_project_local_and_separate(self):
        for name in ("../journey.log", "C:/outside.log", "/outside.log", "journey.log:ads"):
            with self.subTest(name=name):
                self.receipt["results"]["user-journey"]["evidence"] = name
                self.write_receipt()
                self.assert_failure(self.evaluate(), "expected a project-relative POSIX path")
        self.receipt["results"]["user-journey"]["evidence"] = "dist/index.html"
        self.write_receipt()
        self.assert_failure(self.evaluate(), "evidence must be separate")

    def test_dangling_contract_symlink_is_not_a_legacy_project(self):
        contract = self.root / CONTRACT
        contract.unlink()
        try:
            contract.symlink_to(self.root / "missing.json")
        except OSError as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")
        self.assert_failure(self.evaluate(), "symlink or reparse point is not allowed")

    def test_hardlinked_artifact_is_not_independent_evidence(self):
        self.evidence.unlink()
        try:
            os.link(self.artifact / "index.html", self.evidence)
        except OSError as exc:
            self.skipTest(f"hardlink creation unavailable: {exc}")
        self.receipt["results"]["user-journey"]["evidence_sha256"] = hashlib.sha256(
            self.evidence.read_bytes()).hexdigest()
        self.write_receipt()
        self.assert_failure(self.evaluate(), "evidence file must not be hard-linked")

    def test_unconfigured_and_historical_skips_are_not_acceptance(self):
        historical = self.evaluate(released_history=True)
        self.assertEqual("NOT_APPLICABLE", historical["state"])
        self.assertTrue(historical["skipped"])
        self.assertFalse(historical["pass"])
        self.assertTrue(self.evaluate(released_history=True, required=True)["pass"])
        (self.root / CONTRACT).unlink()
        legacy = self.evaluate()
        self.assertEqual("NOT_CONFIGURED", legacy["state"])
        self.assertTrue(legacy["skipped"])
        self.assertFalse(legacy["pass"])
        self.assert_failure(self.evaluate(required=True, released_history=True), "missing")

    def test_goal_cli_returns_the_real_decision_without_touching_bridge_state(self):
        base = [
            sys.executable, str(_INFRA / "verify_workflow.py"), "--project-root", str(self.root),
            "goal-bridge", "--action", "check-completion", "--goal", "delivery-goal",
        ]
        ok = subprocess.run(base, capture_output=True, encoding="utf-8", check=False)
        self.assertEqual(0, ok.returncode, ok.stderr)
        self.assertEqual("PASS", json.loads(ok.stdout)["state"])
        (self.root / CONTRACT).unlink()
        refused = subprocess.run(base, capture_output=True, encoding="utf-8", check=False)
        self.assertEqual(2, refused.returncode, refused.stderr)
        self.assert_failure(json.loads(refused.stdout), "missing")
        self.assertFalse((self.gov / "goal-bridge").exists())

    def test_candidate_release_calls_gate_even_with_execution_checks_disabled(self):
        import verify_workflow

        (self.root / RECEIPT).unlink()
        with patch.object(verify_workflow, "HOST_PROJECT_ROOT", self.root):
            verdict = verify_workflow.check_release_readiness(
                version="0.1.0", run_execution_gates=False,
            )
        self.assert_failure(verdict["details"]["delivery_acceptance"], "delivery-receipt.json")
        self.assertFalse(verdict["pass"])
        self.assertTrue(any(issue.startswith("delivery acceptance:") for issue in verdict["issues"]))


if __name__ == "__main__":
    unittest.main()
