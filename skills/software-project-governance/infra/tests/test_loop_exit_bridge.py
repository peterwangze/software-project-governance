"""Tests for infra/loop_exit_bridge.py — loop_exit → next-unit 推荐桥 (FIX-236.3).

Covers: consuming loop_exit events into next-unit candidates (top-N +
dependency-resolution reasons), candidate JSON write/read round-trip, the
refresh entry that reads plan-tracker + event log and persists a snapshot,
and cycle tolerance (WARN, not ERROR).

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_loop_exit_bridge.py -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import loop_exit_bridge as bridge  # noqa: E402


PLAN_TEXT = """# 测试项目

## 项目配置

### 优先级一览
| 优先级 | ID | 事项 | 依赖 | 目标版本 | 状态 |
| --- | --- | --- | --- | --- | --- |
| P1 | FIX-300 | task 300 | FIX-200✅ | 0.73.0 | ⏳ 待执行 |
| P1 | FIX-301 | task 301 | — | 0.73.0 | ⏳ 待执行 |
| P1 | FIX-302 | task 302 | FIX-300 | 0.73.0 | ⏳ 待执行 |
| P1 | FIX-200 | task 200 | — | 0.73.0 | ✅ 完成 |
"""

EXIT_EVENTS = [
    {"event_type": "gate_result", "unit_id": "u1", "gate_id": "G6",
     "cas_version": 2, "actor": "code-reviewer-agent"},
    {"event_type": "loop_exit", "unit_id": "u1", "gate_id": "G6", "tier": "inner",
     "cas_version": 3, "actor": "code-reviewer-agent"},
    {"event_type": "back_edge", "unit_id": "u2", "gate_id": "G6",
     "cas_version": 1, "actor": "code-reviewer-agent"},
]


class BuildCandidatesTests(unittest.TestCase):
    """Pure build path: events → unblocked top-N with reasons."""

    def test_consumes_exit_events_and_recommends_unblocked(self):
        report = bridge.build_candidates(PLAN_TEXT, EXIT_EVENTS, top_n=2)
        self.assertEqual(report["exit_events_consumed"], 1)
        ids = [c["task_id"] for c in report["recommended_top_n"]]
        self.assertIn("FIX-301", ids)
        self.assertIn("FIX-300", ids)
        self.assertNotIn("FIX-302", ids)  # blocked by FIX-300 (⏳)
        self.assertFalse(report["cycle_warning"])

    def test_reason_mentions_satisfied_dependency(self):
        report = bridge.build_candidates(PLAN_TEXT, EXIT_EVENTS, top_n=2)
        by_id = {c["task_id"]: c for c in report["recommended_top_n"]}
        self.assertIn("FIX-200", by_id["FIX-300"]["reason"])

    def test_top_n_truncation(self):
        report = bridge.build_candidates(PLAN_TEXT, EXIT_EVENTS, top_n=1)
        self.assertEqual(len(report["recommended_top_n"]), 1)
        self.assertGreaterEqual(len(report["unblocked"]), 2)

    def test_cycle_tolerance(self):
        text = (PLAN_TEXT
                .replace("FIX-200✅", "FIX-301")
                .replace("| P1 | FIX-301 | task 301 | — |",
                         "| P1 | FIX-301 | task 301 | FIX-300 |"))
        report = bridge.build_candidates(text, [], top_n=2)
        self.assertTrue(report["cycle_warning"])
        self.assertIsInstance(report["cycles"], list)
        self.assertTrue(report["cycles"])
        # Best-effort: the report still carries unblocked candidates.
        self.assertIn("recommended_top_n", report)

    def test_write_read_roundtrip(self):
        report = bridge.build_candidates(PLAN_TEXT, EXIT_EVENTS, top_n=1)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "candidates.json"
            bridge.write_candidates(report, path)
            loaded = bridge.read_candidates(path)
        self.assertEqual(loaded["exit_events_consumed"], 1)
        self.assertEqual(
            loaded["recommended_top_n"][0]["task_id"],
            report["recommended_top_n"][0]["task_id"],
        )

    def test_refresh_writes_snapshot_under_governance(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / ".governance"
            gov.mkdir()
            (gov / "plan-tracker.md").write_text(PLAN_TEXT, encoding="utf-8")
            (gov / "loop-event-log.jsonl").write_text(
                "".join(json.dumps(e) + "\n" for e in EXIT_EVENTS),
                encoding="utf-8",
            )
            report = bridge.refresh_candidates(root, top_n=2)
            self.assertEqual(report["exit_events_consumed"], 1)
            snapshot = gov / bridge.CANDIDATES_FILENAME
            self.assertTrue(snapshot.is_file())
            loaded = bridge.read_candidates(snapshot)
            self.assertEqual(loaded["recommended_top_n"], report["recommended_top_n"])

    def test_dependency_reason_distinguishes_unknown_status(self):
        # P2-3: a dependency whose status is unknown must NOT be reported as
        # "dependencies satisfied (none pending)".
        from task_priority import TaskDep
        task = TaskDep(task_id="FIX-310", priority="P1", status="⏳ 待执行",
                       dependencies=("FIX-400",))
        reason = bridge._dependency_reasons(task, {})
        self.assertIn("unknown status", reason)
        self.assertIn("FIX-400", reason)
        self.assertNotIn("none pending", reason)

    def test_dependency_reason_reports_satisfied_and_pending(self):
        from task_priority import TaskDep
        task = TaskDep(task_id="FIX-310", priority="P1", status="⏳ 待执行",
                       dependencies=("FIX-400", "FIX-401"))
        reason = bridge._dependency_reasons(task, {"FIX-400": True, "FIX-401": False})
        self.assertIn("dependencies satisfied: FIX-400", reason)
        self.assertIn("pending: FIX-401", reason)


# FIX-254 / REQ-110 — unblocked=0 plan: the bridge (next-candidates read end)
# must not emit a bare empty recommendation. It carries the blocked-chain
# unblock fallback + structured empty reason alongside the (empty) top-N.
ALL_BLOCKED_PLAN_TEXT = """# 测试项目（全阻塞）

## 项目配置

### 优先级一览
| 优先级 | ID | 事项 | 依赖 | 目标版本 | 状态 |
| --- | --- | --- | --- | --- | --- |
| P1 | FIX-200 | done dep | — | 0.73.0 | ✅ 完成 |
| P0 | FIX-205 | held head (deps satisfied) | FIX-200✅ | 0.73.0 | ⛔ BLOCKED_ENV |
| P0 | FIX-207 | blocked child | FIX-205 | 0.73.0 | ⏳ 待执行 |
| P0 | FIX-208 | blocked grandchild | FIX-207 | 0.73.0 | ⏳ 待执行 |
| P1 | FIX-210 | unknown-dep child | FIX-299 | 0.73.0 | ⏳ 待执行 |
"""


class EmptyRecommendationFallbackTests(unittest.TestCase):
    """REQ-110 / FIX-254 — unblocked=0 next-candidates fallback shape."""

    def test_all_blocked_plan_emits_unblock_fallback_not_bare_empty(self):
        report = bridge.build_candidates(ALL_BLOCKED_PLAN_TEXT, EXIT_EVENTS, top_n=3)
        self.assertEqual(report["recommended_top_n"], [])
        fb = report["recommended_fallback"]
        self.assertIsNotNone(fb)
        self.assertEqual(fb["unblock_target"], "FIX-205")
        self.assertEqual(fb["kind"], "non_executable_status")
        self.assertIn("FIX-207", fb["downstream"])
        self.assertIn("FIX-208", fb["downstream"])
        self.assertEqual(fb["downstream_count"], 2)
        self.assertTrue(fb["reason"])
        er = report["empty_reason"]
        self.assertIsNotNone(er)
        self.assertEqual(er["kind"], "all_blocked")
        self.assertEqual(er["blocked"], 3)
        self.assertTrue(er["nearest_action"])

    def test_all_blocked_fallback_survives_snapshot_roundtrip(self):
        report = bridge.build_candidates(ALL_BLOCKED_PLAN_TEXT, [], top_n=3)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "candidates.json"
            bridge.write_candidates(report, path)
            loaded = bridge.read_candidates(path)
        self.assertEqual(loaded["recommended_fallback"], report["recommended_fallback"])
        self.assertEqual(loaded["empty_reason"], report["empty_reason"])

    def test_normal_plan_has_null_fallback_and_reason(self):
        report = bridge.build_candidates(PLAN_TEXT, EXIT_EVENTS, top_n=2)
        self.assertTrue(report["recommended_top_n"])
        self.assertIsNone(report["recommended_fallback"])
        self.assertIsNone(report["empty_reason"])

    def test_parse_error_report_has_null_fallback_and_structured_error(self):
        # A str that looks like a path but names no file raises inside the
        # compute path; the bridge must never raise — it returns a structured
        # parse_error report with an explicit null fallback (not a bare empty
        # list with no explanation).
        report = bridge.build_candidates("D:/no/such/dir/plan-tracker.md", [])
        self.assertIn("parse_error", report)
        self.assertEqual(report["recommended_top_n"], [])
        self.assertIsNone(report["recommended_fallback"])
        self.assertIn("empty_reason", report)
        self.assertIsNone(report["empty_reason"])


if __name__ == "__main__":
    unittest.main()
