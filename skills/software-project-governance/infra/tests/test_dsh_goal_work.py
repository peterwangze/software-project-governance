"""Stable native work packages are guidance for verified delivery gaps."""

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

from delivery_acceptance import CONTRACT, RECEIPT, artifact_sha256  # noqa: E402
from dsh_goal_work import WORK_PACKAGES, read_work_packages  # noqa: E402
from goal_bridge import bind_intent, record_execution  # noqa: E402
from goal_planning import plan_goal_candidates  # noqa: E402


class GoalWorkTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.gov = self.root / ".governance"
        self.gov.mkdir()
        self.goal = "goal-native-work"
        self.session = "native-work-session"
        self.intent = "复现正常入口，修复菜单与读档，再交付生产构建。"
        self.intent_hash = self.sha(self.intent.encode("utf-8"))
        self.criteria = {"menu": "Menu returns to player control", "save": "Save restores a journey"}
        self.contract = {"release_version": "1.0", "artifact": "product.zip", "entrypoint": "/",
                         "producer": "builder", "verifier": "independent-review", "criteria": self.criteria}
        self.reproduce = {"id": "reproduce-journey", "action": "verify", "method": "exercise-entrypoint",
                          "criteria": ["menu", "save"], "estimated_rounds": 1,
                          "instruction": "Start from the main menu, open the handbook, press Esc, and walk again."}
        self.build = {"id": "production-build", "action": "verify", "method": "build-release",
                      "criteria": ["menu", "save"], "estimated_rounds": 3,
                      "instruction": "Run npm run build from the product folder and preserve the production output."}
        self.repair = {"id": "repair-recovery", "action": "repair", "method": "repair-criterion",
                       "criteria": ["save"], "estimated_rounds": 1,
                       "instruction": "Repair the independently reproduced failure in loading a saved journey."}
        self.sidecar = {"schema_version": 1, "intent_sha256": self.intent_hash,
                        "work_packages": [self.reproduce, self.build, self.repair]}
        self.write_json(self.root / WORK_PACKAGES, self.sidecar)
        env = patch.dict(os.environ, {"GOVERNANCE_GOAL_BRIDGE": "1-on", "GOVERNANCE_GOAL_BRIDGE_DISABLED": ""})
        env.start()
        self.addCleanup(env.stop)

    @staticmethod
    def sha(payload):
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def write_json(path, data):
        path.write_text(json.dumps(data), encoding="utf-8")

    def work(self):
        return read_work_packages(self.root, self.intent_hash, self.criteria)

    def bind(self):
        self.write_json(self.root / CONTRACT, {**self.contract, "schema_version": 1, "goal_id": self.goal})
        result = bind_intent(self.goal, intent=self.intent, governance_dir=self.gov)
        self.assertFalse(result.get("error"), result)
        self.measure(1)
        return result["contract_sha256"]

    def measure(self, rounds):
        result = record_execution(self.goal, rounds=rounds, governance_dir=self.gov)
        self.assertFalse(result.get("error"), result)

    def plan(self, packets=None, **kwargs):
        loader = (lambda: ({}, "missing execution packets")) if packets is None else lambda: (packets, "")
        return plan_goal_candidates(self.root, self.goal, load_packets=loader, work_packages=self.work()[0], **kwargs)

    def receipt(self, **statuses):
        artifact = self.root / self.contract["artifact"]
        artifact.write_bytes(b"candidate bytes")
        evidence = self.root / "independent-observation.log"
        evidence.write_bytes(b"Browser reviewer exercised and recorded the normal entry point.")
        self.write_json(self.root / RECEIPT, {
            "schema_version": 1, "contract_sha256": self.sha((self.root / CONTRACT).read_bytes()),
            "artifact_sha256": artifact_sha256(artifact), "entrypoint": self.contract["entrypoint"],
            "verifier": self.contract["verifier"], "results": {
                key: {"status": status, "evidence": evidence.name, "evidence_sha256": self.sha(evidence.read_bytes())}
                for key, status in statuses.items()
            },
        })

    def native(self, expected_status, expected_code, **updated_request):
        request = {"schema_version": 1, "action": "admit", "goal_id": self.goal, "session_id": self.session,
                   "revision": 1, "objective": self.intent, "max_rounds": 12, "usage": {"rounds": 1},
                   **updated_request}
        done = subprocess.run([sys.executable, str(_INFRA / "dsh_goal_native.py"),
                               "--project-root", str(self.root)], input=json.dumps(request).encode("utf-8"),
                              capture_output=True, timeout=20)
        self.assertEqual(0, done.returncode, done.stderr)
        response = json.loads(done.stdout)
        self.assertEqual((expected_status, expected_code), (response["status"], response["code"]), response)
        return response

    def test_sidecar_is_optional_and_scoped_to_exact_intent(self):
        self.assertEqual((self.reproduce, self.build, self.repair), self.work()[0])
        self.assertEqual(self.sha((self.root / WORK_PACKAGES).read_bytes()), self.work()[1])
        with self.assertRaisesRegex(ValueError, "intent SHA-256"):
            read_work_packages(self.root, self.sha(self.intent.strip("。").encode("utf-8")), self.criteria)
        (self.root / WORK_PACKAGES).unlink()
        self.assertEqual(((), None), self.work())

    def test_invalid_work_package_is_refused_before_use(self):
        cases = ({"id": "bad/task"}, {"action": "dispatch"}, {"method": "shell"}, {"criteria": ["unrelated"]},
                 {"criteria": ["save", "save"]}, {"estimated_rounds": 0}, {"estimated_rounds": True},
                 {"instruction": "line one\nline two"}, {"instruction": "x" * 513})
        for fields in cases:
            with self.subTest(fields=list(fields)):
                self.write_json(self.root / WORK_PACKAGES, {**self.sidecar, "work_packages": [{**self.reproduce, **fields}]})
                with self.assertRaises(ValueError):
                    self.work()
        self.write_json(self.root / WORK_PACKAGES, {**self.sidecar, "work_packages": [self.reproduce] * 2})
        with self.assertRaisesRegex(ValueError, "IDs must be distinct"):
            self.work()

    def test_matching_work_appears_in_declared_order_without_legacy_queue(self):
        self.bind()
        plan = self.plan()
        self.assertEqual("READY", plan["state"])
        self.assertEqual([self.reproduce, self.build], plan["work_packages"])
        self.assertEqual([], plan["recommended_top_n"])
        self.assertEqual([self.reproduce], self.plan(top_n=1)["work_packages"])
        self.assertEqual([self.reproduce, self.build], self.plan({"FIX-001": {}})["work_packages"])

    def test_receipt_gaps_distinguish_verified_failure_from_missing_or_stale_evidence(self):
        self.bind()
        self.receipt(menu="PASS", save="FAIL")
        self.assertEqual([self.repair], self.plan()["work_packages"])
        (self.root / self.contract["artifact"]).write_bytes(b"changed candidate bytes")
        self.assertEqual([self.reproduce, self.build], self.plan()["work_packages"])
        self.receipt(menu="PASS", save="PASS")
        plan = self.plan()
        self.assertEqual([], plan["work_packages"])
        self.assertEqual("CHECK_COMPLETION", plan["state"])

    def test_active_goal_links_and_warning_budget_filter_work(self):
        digest = self.bind()
        self.receipt(menu="PASS", save="FAIL")
        locks = self.gov / "agent-locks.json"
        self.write_json(locks, {"active_tasks": {"FIX-008": {"coordinator_session": "worker-session",
                                                          "spawned_at": "now", "target_files": []}}, "file_locks": {}})
        active = {"FIX-008": {"goal_link": {"goal_id": self.goal, "contract_sha256": digest,
                                           "action": "repair", "criteria": ["save"]}}}
        plan = self.plan(active)
        self.assertEqual("WAIT_ACTIVE", plan["state"])
        self.assertEqual([], plan["work_packages"])
        self.assertEqual(["FIX-008"], plan["in_flight"])
        self.assertEqual([], self.plan()["work_packages"])
        locks.unlink()
        (self.root / RECEIPT).unlink()
        self.measure(40)
        self.assertEqual([self.reproduce], self.plan()["work_packages"])
        self.measure(42)
        self.assertEqual([], self.plan()["work_packages"])

    def test_real_leaf_keeps_work_after_restart_and_packet_rewrite_and_holds_profile_drift(self):
        self.write_json(self.gov / "dsh-goal.json", {
            "schema_version": 1, "intent_sha256": self.intent_hash,
            "budget": {"max_rounds": 12, "max_seconds": 100, "max_tokens": 1000}, "contract": self.contract,
        })
        first = self.native("ALLOW", "ADMITTED")
        self.assertEqual([self.reproduce, self.build], first["plan"]["work_packages"])
        self.write_json(self.gov / "execution-packets.json", {"packets": {"FIX-001": {"legacy": "replacement"}}})
        next_process = self.native("ALLOW", "ADMITTED", revision=2)
        self.assertEqual(first["plan"]["work_packages"], next_process["plan"]["work_packages"])
        self.write_json(self.root / WORK_PACKAGES, {**self.sidecar, "work_packages": [self.build, self.reproduce]})
        self.native("HOLD", "PROFILE_CHANGED", revision=2)
        (self.root / WORK_PACKAGES).unlink()
        self.native("HOLD", "PROFILE_CHANGED", revision=2)


if __name__ == "__main__":
    unittest.main()
