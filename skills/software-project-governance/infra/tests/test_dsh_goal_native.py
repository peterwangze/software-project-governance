"""The real DSH JSON leaf with separate processes and disposable projects."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_INFRA = Path(__file__).resolve().parent.parent
if str(_INFRA) not in sys.path:
    sys.path.insert(0, str(_INFRA))

from delivery_acceptance import CONTRACT, RECEIPT, artifact_sha256  # noqa: E402
from dsh_goal_native import MAX_REQUEST, PROFILE  # noqa: E402


class NativeGoalTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.gov = self.root / ".governance"
        self.gov.mkdir()
        self.env = os.environ.copy()
        for switch in ("GOVERNANCE_GOAL_BRIDGE", "GOVERNANCE_GOAL_BRIDGE_DISABLED"):
            self.env.pop(switch, None)
        self.objective = "完成真实用户旅程。\n  保留原始空格。 "
        self.request = {"schema_version": 1, "action": "admit", "session_id": "native-session",
                        "goal_id": "native-goal-83", "revision": 1, "objective": self.objective,
                        "max_rounds": 10, "usage": {"rounds": 0}}
        self.budget = {"max_rounds": 10, "max_tokens": 1_000, "max_seconds": 60}
        self.template = {"release_version": "1.0", "artifact": "product.txt", "entrypoint": "/",
                         "producer": "builder", "verifier": "independent-qa",
                         "criteria": {"journey": "The user can complete the main journey"}}
        self.profile = {"schema_version": 1, "intent_sha256": self.sha(self.objective.encode("utf-8")),
                        "budget": self.budget, "contract": self.template}
        self.state_path = self.gov / "goal-bridge" / (self.request["goal_id"] + ".json")
        self.write_json(self.root / PROFILE, self.profile)

    @staticmethod
    def sha(payload):
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def write_json(path, data):
        path.write_text(json.dumps(data), encoding="utf-8")

    def subprocess(self, script, *args, input=None, exit_code=0):
        result = subprocess.run([sys.executable, str(_INFRA / script), *args], input=input,
                                capture_output=True, env=self.env, timeout=15)
        self.assertEqual(exit_code, result.returncode, result.stdout + result.stderr)
        self.assertEqual(b"", result.stderr)
        if input is not None:
            self.assertEqual(1, len(result.stdout.splitlines()))
            self.assertNotIn(self.objective.strip(), result.stdout.decode("utf-8"))
        return json.loads(result.stdout)

    def native(self, status, code, **updates):
        request = {**self.request, **updates}
        result = self.subprocess("dsh_goal_native.py", "--project-root", str(self.root),
                                 input=json.dumps(request).encode("utf-8"))
        self.assertEqual((status, code), (result["status"], result["code"]))
        for key in ("goal_id", "session_id", "revision"):
            self.assertEqual(request[key], result[key])
        return result

    def bridge(self, action, *args, exit_code=0):
        return self.subprocess("goal_bridge.py", "--project-root", str(self.root), "goal-bridge", "--goal",
                               self.request["goal_id"], "--action", action, *args, exit_code=exit_code)

    def state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def receipt(self, status="PASS"):
        artifact = self.root / self.template["artifact"]
        artifact.write_bytes(b"Product candidate")
        evidence = self.root / "journey.log"
        evidence.write_bytes(b"Independent reviewer followed the documented entry point.\n")
        self.write_json(self.root / RECEIPT, {
            "schema_version": 1, "contract_sha256": self.sha((self.root / CONTRACT).read_bytes()),
            "artifact_sha256": artifact_sha256(artifact), "entrypoint": self.template["entrypoint"],
            "verifier": self.template["verifier"], "results": {"journey": {
                "status": status, "evidence": "journey.log", "evidence_sha256": self.sha(evidence.read_bytes()),
            }},
        })

    def direct_repair(self):
        preflight = tempfile.TemporaryDirectory()
        self.addCleanup(preflight.cleanup)
        protected = Path(preflight.name).resolve()
        canary = protected / "canary"
        package = {"id": "repair-journey", "action": "repair", "criteria": ["journey"],
                   "method": "repair-criterion", "estimated_rounds": 1,
                   "instruction": "Repair the witnessed journey, then rerun its player entrypoint."}
        work = self.gov / "dsh-goal-work.json"
        intent = self.profile["intent_sha256"]
        self.write_json(work, {"schema_version": 1, "intent_sha256": intent, "work_packages": [package]})
        profile_bytes = (json.dumps({**self.profile, "work_sha256": self.sha(work.read_bytes())},
                                    sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
        product, repro = b"Original behavior\n", b"Original browser repro\n"
        for workspace in (self.root, canary):
            (workspace / "game").mkdir(parents=True)
            (workspace / "game/main.txt").write_bytes(product)
            (workspace / "repro.txt").write_bytes(repro)
        source = json.dumps({"main.txt": self.sha(product)}, sort_keys=True,
                            ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        receipt = protected / "preflight.json"
        both = {"mode": "workspace-write", "status": "PASS", "enforcement": "partial"}
        preflight_receipt = {
            "schema_version": 1, "session_id": "test-preflight", "workspace": str(canary),
            "recipe_sha256": "a" * 64, "status": "PASS",
            "browser": {**both, "code": "BROWSER_EXECUTED", "journey": "FAIL", "exit_code": 1},
            "build": {**both, "code": "BUILD_EXECUTED", "exit_code": 0, "artifact_sha256": "b" * 64},
        }
        self.write_json(receipt, preflight_receipt)
        return {
            "workspace": str(self.root.resolve()), "sessionId": self.request["session_id"],
            "intentSha256": intent, "criterionId": "journey", "workPackageId": package["id"],
            "receipt": str(receipt), "receiptSha256": self.sha(receipt.read_bytes()),
            "preflightWorkspace": str(canary), "preflightSessionId": "test-preflight",
            "recipeSha256": "a" * 64, "sourceSha256": self.sha(source), "sourceRoot": "game",
            "reproducer": "repro.txt", "reproducerSha256": self.sha(repro),
            "profileSha256": self.sha(profile_bytes),
        }

    def test_unconfigured_is_write_free_and_completion_cannot_bootstrap(self):
        self.native("HOLD", "NATIVE_BINDING_REQUIRED", action="complete")
        (self.root / PROFILE).unlink()
        self.native("NOT_CONFIGURED", "NO_PROFILE")
        self.native("NOT_CONFIGURED", "NO_PROFILE", action="complete")
        self.assertEqual([], list(self.gov.iterdir()))

    def test_invalid_transport_emits_one_json_without_echo(self):
        message = json.dumps(self.request).encode("utf-8")
        cases = (message + b"{}", b'{"schema_version":1,"schema_version":1}', b" " * (MAX_REQUEST + 1),
                 json.dumps({**self.request, "usage": {"rounds": False}}).encode("utf-8"),
                 json.dumps({**self.request, "goal_id": "../escape"}).encode("utf-8"))
        for raw in cases:
            with self.subTest(size=len(raw)):
                verdict = self.subprocess("dsh_goal_native.py", "--project-root", str(self.root), input=raw, exit_code=2)
                self.assertEqual({"schema_version": 1, "status": "HOLD", "code": "INVALID_REQUEST"}, verdict)
        self.assertFalse((self.root / CONTRACT).exists())

    def test_first_admit_freezes_exact_intent_scope_and_contract(self):
        self.native("HOLD", "INTENT_MISMATCH", objective=self.objective.strip())
        self.native("HOLD", "ROUND_LIMIT_MISMATCH", max_rounds=12)
        self.assertFalse((self.root / CONTRACT).exists())
        admitted = self.native("ALLOW", "ADMITTED", usage={"rounds": 2})
        self.assertEqual(self.objective, self.state()["original_intent"])
        self.assertEqual(["tokens", "wall_clock"], admitted["budget"]["unmeasured_dimensions"])
        raw = (self.root / CONTRACT).read_bytes()
        self.assertEqual({**self.template, "schema_version": 1, "goal_id": self.request["goal_id"]}, json.loads(raw))
        self.assertEqual(self.sha(raw), admitted["contract_sha256"])
        self.native("HOLD", "SCOPE_MISMATCH", session_id="other-native-session", revision=9)
        self.native("ALLOW", "ADMITTED", revision=3, usage={"rounds": 3, "tokens": 15})
        self.native("HOLD", "STALE_REVISION", action="complete", revision=2)
        self.native("ALLOW", "ADMITTED", revision=3, usage={"rounds": 1})
        self.assertEqual(3, self.state()["native_dsh"]["revision"])
        self.assertEqual(3, self.state()["budget_consumption"]["rounds"]["used"])
        (self.root / PROFILE).unlink()
        self.native("HOLD", "CONFIG_MISSING", revision=3)

    def test_conflicting_contract_is_preserved_and_bound_contract_bytes_cannot_drift(self):
        self.write_json(self.root / CONTRACT, {**self.template, "schema_version": 1, "goal_id": "other"})
        before = (self.root / CONTRACT).read_bytes()
        self.native("HOLD", "CONTRACT_CHANGED")
        self.assertEqual(before, (self.root / CONTRACT).read_bytes())
        self.assertFalse(self.state_path.exists())
        (self.root / CONTRACT).unlink()
        self.native("ALLOW", "ADMITTED")
        self.receipt()
        amended = (self.root / CONTRACT).read_bytes() + b"\n"
        (self.root / CONTRACT).write_bytes(amended)
        self.native("HOLD", "CONTRACT_CHANGED", action="complete")
        self.assertEqual(amended, (self.root / CONTRACT).read_bytes())

    def test_p0_blocks_missing_failure_and_tampering_then_accepts_matching_receipt(self):
        self.native("ALLOW", "ADMITTED")
        self.native("HOLD", "DELIVERY_ACCEPTANCE_FAILED", action="complete")
        self.receipt("FAIL")
        self.native("HOLD", "DELIVERY_ACCEPTANCE_FAILED", action="complete")
        self.receipt()
        result = self.native("ALLOW", "DELIVERY_ACCEPTED", action="complete")
        self.assertEqual("PASS", result["acceptance_state"])
        self.assertEqual(["tokens", "wall_clock"], result["budget"]["unmeasured_dimensions"])
        (self.root / self.template["artifact"]).write_bytes(b"Changed after independent check")
        self.native("HOLD", "DELIVERY_ACCEPTANCE_FAILED", action="complete")

    def test_measured_budget_checkpoints_and_manual_ruling_preserves_scope(self):
        self.native("ALLOW", "ADMITTED", usage={"rounds": 5, "tokens": 700})
        self.receipt()
        verdict = self.native("HOLD", "BUDGET_LIMIT_REACHED", action="complete", revision=2,
                              usage={"rounds": 6, "seconds": 60})
        self.assertEqual("CHECKPOINTED", verdict["goal_state"])
        self.assertTrue(verdict["checkpoint_materialized"])
        self.native("HOLD", "AUTHORIZED_RESUME_REQUIRED", revision=3)
        self.bridge("ruling", "--decision", "extend-budget", "--authorized-by", "fixture user",
                    "--new-limit", "rounds=12,wall_clock=90")
        self.assertEqual(3, self.state()["native_dsh"]["revision"])
        self.native("HOLD", "ROUND_LIMIT_MISMATCH", revision=4)
        self.native("ALLOW", "DELIVERY_ACCEPTED", action="complete", revision=4, max_rounds=12,
                    usage={"rounds": 7, "seconds": 61})
        self.budget["max_rounds"] = 12
        self.write_json(self.root / PROFILE, self.profile)
        self.native("HOLD", "PROFILE_CHANGED", revision=4, max_rounds=12)

    def test_tree_stop_requires_current_proved_limit_and_tail_before_resuming(self):
        self.native("ALLOW", "ADMITTED", usage={"rounds": 1, "tokens": 600, "seconds": 5})
        self.bridge("checkpoint", "--obligations", "verify-before-delivery")
        self.bridge("ruling", "--decision", "continue", "--authorized-by", "fixture user")
        observation = {"sessions": 2, "open_steps": 1, "missing_sessions": 0,
                       "missing_usage": 0, "flush_failures": 0}
        tree = {"id": "ab" * 16, "observation": observation}
        before = self.state_path.read_bytes()
        self.native("HOLD", "TREE_BUDGET_NOT_REACHED", action="tree-stop", tree=tree,
                    usage={"rounds": 1, "tokens": 999, "seconds": 59})
        self.native("HOLD", "STALE_REVISION", action="tree-stop", tree=tree, revision=2,
                    usage={"rounds": 1, "tokens": 1_025, "seconds": 59})
        self.assertEqual(before, self.state_path.read_bytes())
        stopped = self.native("HOLD", "TREE_BUDGET_STOPPED", action="tree-stop", tree=tree,
                              usage={"rounds": 1, "tokens": 1_025, "seconds": 59})
        self.assertEqual("CHECKPOINTED", stopped["goal_state"])
        self.assertEqual("PENDING", stopped["tree_stop"]["status"])
        self.assertEqual(["tokens"], stopped["tree_stop"]["dimensions"])
        self.assertTrue(stopped["checkpoint_materialized"])
        self.assertEqual(1, stopped["open_obligations"])
        self.native("HOLD", "AUTHORIZED_RESUME_REQUIRED", revision=2)
        self.bridge("ruling", "--decision", "extend-budget", "--authorized-by", "fixture user",
                    "--new-limit", "tokens=1800", exit_code=2)
        tail = {**tree, "observation": {**observation, "open_steps": 0, "missing_usage": 1}}
        measured = {"rounds": 1, "tokens": 1_063, "seconds": 60}
        self.native("HOLD", "TREE_STOP_MISMATCH", action="tree-settle", tree={**tail, "id": "12" * 16},
                    usage=measured)
        settled = self.native("HOLD", "TREE_TAIL_RECORDED", action="tree-settle", tree=tail, usage=measured)
        self.assertEqual("INCOMPLETE", settled["tree_stop"]["status"])
        self.assertEqual(1_063, settled["budget"]["zones"]["tokens"]["used"])
        self.assertEqual([{"obligation_id": "verify-before-delivery"}], self.state()["obligations"])
        before = self.state_path.read_bytes()
        self.native("HOLD", "TREE_TAIL_RECORDED", action="tree-settle", tree=tail, usage=measured)
        self.assertEqual(before, self.state_path.read_bytes())
        self.bridge("ruling", "--decision", "extend-budget", "--authorized-by", "fixture user",
                    "--new-limit", "tokens=1800,wall_clock=90")
        self.native("ALLOW", "ADMITTED", revision=3)

    def test_open_obligations_and_goal_linked_locks_prevent_completion(self):
        self.native("ALLOW", "ADMITTED")
        self.receipt()
        locks = self.gov / "agent-locks.json"
        self.write_json(locks, {"active_tasks": {"FIX-434": {"coordinator_session": "other-session",
                                                          "spawned_at": "now", "target_files": []}},
                                "file_locks": {}})
        self.write_json(self.gov / "execution-packets.json", {"packets": {"FIX-434": {"goal_link": {
            "goal_id": self.request["goal_id"],
        }}}})
        self.native("HOLD", "ACTIVE_GOAL_WORK", action="complete")
        locks.unlink()
        obligations = [{"obligation_id": "handoff-check"}]
        self.bridge("checkpoint", "--obligations", "handoff-check")
        refused = self.bridge("checkpoint", "--clear-obligations", exit_code=2)
        self.assertEqual("scope_ruling_required", refused["code"])
        self.bridge("ruling", "--decision", "continue", "--authorized-by", "fixture user")
        result = self.native("HOLD", "OPEN_OBLIGATIONS", action="complete", revision=2)
        self.assertEqual(1, result["open_obligations"])
        self.assertNotIn("handoff-check", json.dumps(result))
        self.assertEqual(obligations, self.state()["obligations"])
        self.bridge("checkpoint", "--clear-obligations")
        self.assertEqual([], self.state()["obligations"])
        self.native("HOLD", "AUTHORIZED_RESUME_REQUIRED", action="complete", revision=2)
        self.bridge("ruling", "--decision", "continue", "--authorized-by", "fixture user")
        self.receipt("FAIL")
        self.native("HOLD", "DELIVERY_ACCEPTANCE_FAILED", action="complete", revision=2)
        self.receipt()
        self.native("ALLOW", "DELIVERY_ACCEPTED", action="complete", revision=2)

    def test_native_plan_changes_with_verified_gaps_and_warning_budget(self):
        admitted = self.native("ALLOW", "ADMITTED")
        self.receipt("FAIL")
        (self.gov / "plan-tracker.md").write_text(
            "# Fixture\n\n### 优先级一览\n"
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 状态 |\n| --- | --- | --- | --- | --- | --- |\n"
            "| P0 | FIX-434 | repair journey | — | 1.0 | ⏳ 待执行 |\n"
            "| P1 | FIX-435 | small repair | — | 1.0 | ⏳ 待执行 |\n",
            encoding="utf-8",
        )
        common = {"goal_id": self.request["goal_id"], "contract_sha256": admitted["contract_sha256"],
                  "criteria": ["journey"], "action": "repair"}
        self.write_json(self.gov / "execution-packets.json", {"packets": {
            "FIX-434": {"goal_link": {**common, "estimated_rounds": 3}},
            "FIX-435": {"goal_link": {**common, "estimated_rounds": 1}},
        }})
        normal = self.native("ALLOW", "ADMITTED", usage={"rounds": 2})["plan"]
        self.assertEqual({"journey": "repair"}, normal["criterion_gaps"])
        self.assertEqual("FIX-434", normal["recommendations"][0]["task_id"])
        warning = self.native("ALLOW", "ADMITTED", usage={"rounds": 8})["plan"]
        self.assertEqual(["FIX-435"], [task["task_id"] for task in warning["recommendations"]])

    def test_direct_repair_binds_first_failure_and_completion_still_needs_independent_receipt(self):
        hint = self.direct_repair()
        (self.root / "game/dist").mkdir()
        (self.root / "game/dist/old-output").write_text("excluded", encoding="utf-8")
        first = self.native("ALLOW", "ADMITTED", direct_repair=hint)
        self.assertTrue(first["direct_repair_attested"])
        self.assertTrue(first["plan"]["direct_repair"])
        self.assertEqual({"journey": "repair"}, first["plan"]["criterion_gaps"])
        self.assertEqual([hint["workPackageId"]], [item["id"] for item in first["plan"]["work_packages"]])
        self.assertFalse((self.gov / "plan-tracker.md").exists())

        (self.root / "game/main.txt").write_text("Actual repair", encoding="utf-8")
        claim = {**hint, "contractSha256": first["contract_sha256"]}
        follow = self.native("ALLOW", "ADMITTED", direct_repair=claim)
        self.assertTrue(follow["plan"]["direct_repair"])
        fresh_host = self.native("ALLOW", "ADMITTED", direct_repair=hint)
        self.assertNotIn("direct_repair", fresh_host["plan"])
        self.assertNotIn("direct_repair_attested", fresh_host)

        self.native("HOLD", "DELIVERY_ACCEPTANCE_FAILED", action="complete")
        self.receipt()
        plan = self.native("ALLOW", "ADMITTED", direct_repair=claim)["plan"]
        self.assertEqual("CHECK_COMPLETION", plan["state"])
        self.assertNotIn("direct_repair", plan)
        self.native("ALLOW", "DELIVERY_ACCEPTED", action="complete")

    def test_invalid_direct_repair_evidence_keeps_ordinary_admission(self):
        hint = self.direct_repair()
        for update in ({"sessionId": "wrong-session"}, {"sourceSha256": "b" * 64},
                       {"profileSha256": "c" * 64}, {"preflightWorkspace": str(self.root.resolve())},
                       {"receiptSha256": "d" * 64}, {"workPackageId": "wrong-package"}):
            with self.subTest(update=update):
                verdict = self.native("ALLOW", "ADMITTED", direct_repair={**hint, **update})
                self.assertEqual("DIRECT_REPAIR_EVIDENCE_INVALID", verdict["direct_repair_code"])
                self.assertNotIn("direct_repair", verdict["plan"])
                self.state_path.unlink()
                (self.root / CONTRACT).unlink()

        path = Path(hint["receipt"])
        evidence = json.loads(path.read_text(encoding="utf-8"))
        evidence["browser"]["journey"] = "PASS"
        self.write_json(path, evidence)
        verdict = self.native("ALLOW", "ADMITTED", direct_repair={**hint, "receiptSha256": self.sha(path.read_bytes())})
        self.assertEqual("DIRECT_REPAIR_EVIDENCE_INVALID", verdict["direct_repair_code"])
        self.assertNotIn("direct_repair", verdict["plan"])


if __name__ == "__main__":
    unittest.main()
