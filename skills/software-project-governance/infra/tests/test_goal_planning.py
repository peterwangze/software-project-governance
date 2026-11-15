"""Isolated CLI regressions for goal-scoped P1 planning."""

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


class GoalPlanningTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.gov = self.root / ".governance"
        self.gov.mkdir()
        self.goal_id = "goal-replay"
        self.intent = "Restore the normal player journey before adding content."
        self.contract = {
            "schema_version": 1, "goal_id": self.goal_id, "artifact": "dist.html",
            "release_version": "0.1.0", "entrypoint": "/", "producer": "developer",
            "verifier": "independent-qa",
            "criteria": {"menu": "Menu returns to player control", "save": "Save resumes the journey"},
        }
        contract_bytes = self.write_json(self.root / CONTRACT, self.contract)
        self.contract_sha256 = hashlib.sha256(contract_bytes).hexdigest()
        self.artifact = self.root / "dist.html"
        self.artifact.write_bytes(b"<html>candidate</html>")
        evidence = self.root / "journey.log"
        evidence.write_bytes(b"Observed normal controls after traversing the menu.\n")
        self.proof = {
            "evidence": evidence.name,
            "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
        }

    @staticmethod
    def write_json(path, data):
        raw = json.dumps(data).encode("utf-8")
        path.write_bytes(raw)
        return raw

    def run_cli(self, *args, expected_code=0):
        env = os.environ.copy()
        env.pop("GOVERNANCE_GOAL_BRIDGE", None)
        env["PYTHONIOENCODING"] = "utf-8"
        done = subprocess.run(
            [sys.executable, str(_INFRA / "verify_workflow.py"), "--project-root", str(self.root), *args],
            capture_output=True, encoding="utf-8", env=env, timeout=30,
        )
        self.assertEqual(expected_code, done.returncode, done.stdout + done.stderr)
        return json.loads(done.stdout)

    def bridge(self, action, *args, expected_code=0):
        return self.run_cli("goal-bridge", "--action", action, "--goal", self.goal_id, *args,
                            expected_code=expected_code)

    def plan(self, *args, expected_code=0):
        return self.run_cli("next-candidates", "--goal", self.goal_id, *args, expected_code=expected_code)

    def bind_and_record(self, rounds=1, *args):
        self.bridge("bind-intent", "--intent", self.intent)
        self.bridge("record", "--rounds", str(rounds), *args)

    def receipt(self, **statuses):
        results = {}
        for criterion, status in statuses.items():
            results[criterion] = {"status": status}
            if status in ("FAIL", "PASS"):
                results[criterion].update(self.proof)
        self.write_json(self.root / RECEIPT, {
            "schema_version": 1, "contract_sha256": self.contract_sha256,
            "artifact_sha256": artifact_sha256(self.artifact),
            "entrypoint": self.contract["entrypoint"], "verifier": self.contract["verifier"],
            "results": results,
        })

    def task_rows(self, *rows):
        header = (
            "# Fixture\n\n### 优先级一览\n"
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
        )
        (self.gov / "plan-tracker.md").write_text(header + "\n".join(rows) + "\n", encoding="utf-8")

    def link(self, action, *criteria, rounds=None, digest=None):
        link = {
            "goal_id": self.goal_id, "contract_sha256": digest or self.contract_sha256,
            "criteria": list(criteria), "action": action,
        }
        if rounds is not None:
            link["estimated_rounds"] = rounds
        return {"goal_link": link}

    def packets(self, **links):
        self.write_json(self.gov / "execution-packets.json", {"packets": {
            task_id.replace("_", "-"): value for task_id, value in links.items()
        }})

    def test_live_declared_gaps_rank_before_truncation_and_exclude_blocked(self):
        self.bind_and_record()
        self.receipt(menu="FAIL", save="NOT_RUN")
        self.task_rows(
            "| P0 | FEAT-800 | unrelated content | — | 0.1.0 | ⏳ 待执行 |",
            "| P0 | FIX-800 | blocked repair | FIX-799 | 0.1.0 | ⏳ 待执行 |",
            "| P1 | FIX-802 | verify pending 〔机器信号〕 | — | 0.1.0 | ⏳ 待执行 |",
            "| P1 | FIX-803 | redundant verify | — | 0.1.0 | ⏳ 待执行 |",
            "| P1 | FIX-804 | repair gap 〔用户点名〕 | — | 0.1.0 | ⏳ 待执行 |",
            "| P1 | FIX-805 | stale link | — | 0.1.0 | ⏳ 待执行 |",
        )
        self.packets(
            FIX_800=self.link("repair", "menu"), FIX_802=self.link("verify", "save"),
            FIX_803=self.link("verify", "menu"), FIX_804=self.link("repair", "menu"),
            FIX_805=self.link("verify", "save", digest="0" * 64),
        )
        snapshot = self.gov / "loop-exit-candidates.json"
        sentinel = self.write_json(snapshot, {"recommended_top_n": [{"task_id": "FEAT-800"}]})
        goal_state = self.gov / "goal-bridge" / f"{self.goal_id}.json"
        before = goal_state.read_bytes()
        plan = self.plan("--top-n", "1")
        self.assertEqual("READY", plan["state"])
        self.assertEqual(self.intent, plan["original_intent"])
        self.assertEqual("unknown", plan["budget_signal"])
        self.assertEqual(["cost", "tokens", "wall_clock"], plan["unmeasured_dimensions"])
        self.assertEqual({"menu": "repair", "save": "verify"}, plan["criterion_gaps"])
        self.assertEqual(["FIX-804"], [item["task_id"] for item in plan["recommended_top_n"]])
        self.assertEqual("user-named", plan["recommended_top_n"][0]["demand_source"])
        self.assertIn("FIX-800: blocked by FIX-799", plan["diagnostics"])
        self.assertTrue(any(note.startswith("FIX-805:") for note in plan["diagnostics"]))
        self.assertEqual(plan, self.plan("--top-n", "1"))
        self.assertEqual(before, goal_state.read_bytes())
        self.assertEqual(sentinel, snapshot.read_bytes())
        self.assertEqual({"recommended_top_n": [{"task_id": "FEAT-800"}]}, self.run_cli("next-candidates"))
        self.assertEqual("ERROR", self.plan("--write", expected_code=2)["state"])

        archive = self.gov / "archive"
        archive.mkdir()
        (archive / "index.md").write_text(
            "## Task 索引\n\n| Task ID | 状态 | 版本 | 归档文件 |\n"
            "| --- | --- | --- | --- |\n"
            "| FIX-799 | 已完成 (2026-11-15) | 0.1.0 | archive/tasks/old.md |\n",
            encoding="utf-8",
        )
        self.assertEqual("FIX-800", self.plan("--top-n", "1")["recommended_top_n"][0]["task_id"])

    def test_stale_product_requests_verification_instead_of_repair(self):
        self.bind_and_record()
        self.receipt(menu="FAIL", save="PASS")
        self.task_rows(
            "| P0 | FIX-801 | repair | — | 0.1.0 | ⏳ 待执行 |",
            "| P1 | FIX-802 | verify | — | 0.1.0 | ⏳ 待执行 |",
        )
        self.packets(FIX_801=self.link("repair", "menu"), FIX_802=self.link("verify", "menu", "save"))
        self.artifact.write_bytes(b"<html>new candidate</html>")
        plan = self.plan()
        self.assertEqual({"menu": "verify", "save": "verify"}, plan["criterion_gaps"])
        self.assertEqual(["FIX-802"], [entry["task_id"] for entry in plan["recommended_top_n"]])
        self.assertTrue(any("artifact SHA-256 mismatch" in item for item in plan["diagnostics"]))

    def test_warning_prefers_small_work_and_holds_overlapping_live_criterion(self):
        self.bind_and_record(38, "--task", "FIX-805")
        self.receipt(menu="FAIL", save="NOT_RUN")
        self.task_rows(
            "| P0 | FIX-801 | estimate exactly reaches danger | — | 0.1.0 | ⏳ 待执行 |",
            "| P0 | FIX-802 | unestimated | — | 0.1.0 | ⏳ 待执行 |",
            "| P1 | FIX-804 | short repair | — | 0.1.0 | ⏳ 待执行 |",
            "| P1 | FIX-805 | recover longer work | — | 0.1.0 | ⏳ 待执行 |",
            "| P1 | FIX-806 | verify independent save gap | — | 0.1.0 | ⏳ 待执行 |",
            "| P1 | FIX-807 | active repair | — | 0.1.0 | 🚧 进行中 |",
        )
        self.packets(
            FIX_801=self.link("repair", "menu", rounds=4), FIX_802=self.link("repair", "menu"),
            FIX_804=self.link("repair", "menu", rounds=1), FIX_805=self.link("repair", "menu", rounds=3),
            FIX_806=self.link("verify", "save", rounds=2), FIX_807=self.link("repair", "menu", rounds=1),
        )
        plan = self.plan()
        self.assertEqual("WARNING", plan["budget_state"])
        self.assertEqual(["FIX-804", "FIX-806", "FIX-805"],
                         [entry["task_id"] for entry in plan["recommended_top_n"]])
        self.assertEqual("resume", plan["recommended_top_n"][-1]["mode"])

        self.write_json(self.gov / "agent-locks.json", {"active_tasks": {"FIX-807": {
            "spawned_at": "2026-11-15T15:00:00Z", "coordinator_session": "previous", "target_files": [],
        }}, "file_locks": {}})
        plan = self.plan()
        self.assertEqual(["FIX-807"], plan["in_flight"])
        self.assertEqual(["FIX-806"], [entry["task_id"] for entry in plan["recommended_top_n"]])

    def test_restart_preserves_hold_and_bound_contract_after_budget_extension(self):
        self.bind_and_record(42)
        draining = self.plan()
        self.assertEqual("HOLD", draining["state"])
        self.assertEqual("DRAINING", draining["goal_state"])
        self.assertIn("in-flight", draining["diagnostics"][0])
        self.bridge("record", "--in-flight", "--rounds", "42")
        pending = self.plan()
        self.assertEqual("CHECKPOINTED", pending["goal_state"])
        self.assertFalse(pending["checkpoint_materialized"])
        self.assertIn("materialize", pending["diagnostics"][0])

        self.bridge("checkpoint", "--task", "FIX-804", "--obligations", "menu-fix,independent-replay")
        self.bridge("record", "--rounds", "0", expected_code=2)
        before = self.plan()
        self.assertEqual("HOLD", before["state"])
        self.assertEqual("CHECKPOINTED", before["goal_state"])
        self.assertTrue(before["checkpoint_materialized"])
        self.assertIn("authorized scope ruling", before["diagnostics"][0])
        self.assertEqual(42, before["zones"]["rounds"]["used"])
        self.assertEqual(["menu-fix", "independent-replay"],
                         [entry["obligation_id"] for entry in before["obligations"]])
        self.assertEqual(before, self.plan())

        self.bridge("ruling", "--decision", "extend-budget", "--authorized-by", "user",
                    "--new-limit", "rounds=120")
        contract_path = self.root / CONTRACT
        contract_path.write_bytes(contract_path.read_bytes() + b"\n")
        changed = self.plan()
        self.assertEqual("CONTRACT_CHANGED", changed["state"])
        self.assertEqual("RUNNING", changed["goal_state"])
        self.assertEqual(self.contract_sha256, changed["contract_sha256"])
        self.assertEqual(42, changed["zones"]["rounds"]["used"])

    def test_completion_advice_requires_bound_intent_and_budget(self):
        self.receipt(menu="PASS", save="PASS")
        self.assertEqual("AWAIT_INTENT", self.plan()["state"])
        self.bridge("bind-intent", "--intent", self.intent)
        self.assertEqual("AWAIT_BUDGET", self.plan()["state"])
        self.bridge("record", "--rounds", "1")
        plan = self.plan()
        self.assertEqual("CHECK_COMPLETION", plan["state"])
        self.assertEqual([], plan["recommended_top_n"])
        self.assertIn("existing authorization", plan["diagnostics"][0])


if __name__ == "__main__":
    unittest.main()
