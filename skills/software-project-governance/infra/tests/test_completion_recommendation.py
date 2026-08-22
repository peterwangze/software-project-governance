"""FIX-262 / REQ-108 — completion-recommendation machine-closure tests (red→green).

Two deliverables under test:

1. ``task-priority-analysis --evidence-task {id}`` machine-writes a
   recommendation snapshot row (``RECO-{task}``, marker
   ``task-priority-analysis 机器写入``) into the evidence log — the
   review-record/change-triage unforgeable-machine-record pattern applied to
   the M7.4 step 6 completion recommendation.
2. Check 34 ``check_completion_recommendation``: completed ACTIVE tasks
   (product-code completion rows dated on/after the effective date) without
   an associated snapshot row → FAIL (S1); session-snapshot "下次会话优先级"
   section with entries but no snapshot ID reference → WARN (S2); referenced
   snapshot IDs missing from the evidence log → FAIL (S3 dangling).

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_completion_recommendation.py -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw  # noqa: E402
from task_priority import (  # noqa: E402
    PriorityReport,
    compute_unblocked_tasks,
    parse_task_dependencies,
)


# Effective date mirrors the FIX-260 Check 30c pattern: records dated BEFORE
# it are legacy and never judged (145 completed tasks have no snapshot rows).
EFFECTIVE = "2026-08-22"
PRE = "2026-08-21"

COMPLETION_ROW = (
    "| EVD-FIX-300 | FIX-300 | 产品代码 | FIX-300 完成（2026-08-22，"
    "Developer→Code Reviewer R0 APPROVED）。实现细节…… | 事实依据：测试输出 | "
    "a.py; b.py | Developer | {date} | G11 | ✅ 完成 |"
)
LEGACY_SNAPSHOT_ROW = (
    "| EVD-899 | FIX-300 | 验证 | 完成必推荐调用快照（M7.4 step 6，"
    "FIX-300 完成触发，2026-08-22）。task-priority-analysis 输出：141 tasks"
    " / 137 completed / 0 unblocked | 事实依据：命令输出 | - | Coordinator | "
    "{date} | G11 | N/A |"
)
MACHINE_SNAPSHOT_ROW = (
    "| RECO-FIX-300 | FIX-300 | 治理记录 | task-priority-analysis 机器写入"
    "完成必推荐调用快照（trigger FIX-300，M7.4 step 6 / FIX-262） | "
    "事实依据：task-priority-analysis 输出摘要（机器写入） | 141 tasks/137 "
    "completed/0 unblocked/4 blocked | Coordinator | {date} | G11 | N/A |"
)
# Non-completion noise rows that MUST NOT be treated as completions.
REVIEW_ROW = (
    "| REVIEW-FIX-300-R0 | FIX-300 | 产品代码 | Code Review R0：APPROVED "
    "| 事实依据：diff | r.patch | Reviewer | {date} | G11 | APPROVED |"
)
TRIAGE_ROW = (
    "| TRIAGE-FIX-300 | FIX-300 | 治理记录 | change-triage CLI 机器写入 "
    "| 事实依据：change-triage | - | Coordinator | {date} | G11 | N/A |"
)


def _row(template, date=EFFECTIVE):
    return template.format(date=date)


class Check34FixtureTests(unittest.TestCase):
    """S1/S2/S3 rule fixtures over injectable rows + snapshot text."""

    def test_s1_completion_without_snapshot_fails(self):
        """Core acceptance signal 3: completion row, no snapshot → FAIL/S1."""
        r = vw.check_completion_recommendation(
            evidence_rows=[_row(COMPLETION_ROW)])
        self.assertEqual(r["verdict"], "FAIL")
        s1 = [v for v in r["violations"] if v["rule"] == "S1"]
        self.assertEqual(s1[0]["task_id"], "FIX-300")

    def test_s1_machine_snapshot_row_satisfies(self):
        """Machine RECO-{task} row → PASS."""
        r = vw.check_completion_recommendation(
            evidence_rows=[_row(COMPLETION_ROW), _row(MACHINE_SNAPSHOT_ROW)])
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["verdict"], "PASS")

    def test_s1_legacy_snapshot_row_satisfies(self):
        """Legacy free-text snapshot row (marker + 完成触发) → PASS."""
        r = vw.check_completion_recommendation(
            evidence_rows=[_row(COMPLETION_ROW), _row(LEGACY_SNAPSHOT_ROW)])
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["verdict"], "PASS")

    def test_s1_legacy_association_via_description_trigger(self):
        """EVD-898 pattern: snapshot row's task_ref is another id, the
        association lives in the description（"FIX-300 完成触发"）→ counts."""
        other_ref = _row(LEGACY_SNAPSHOT_ROW).replace(
            "| EVD-899 | FIX-300 |", "| EVD-898 | VAL-010 |", 1)
        r = vw.check_completion_recommendation(
            evidence_rows=[_row(COMPLETION_ROW), other_ref])
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["verdict"], "PASS")

    def test_pre_effective_completions_are_legacy(self):
        """Completions dated before the effective date are never judged."""
        r = vw.check_completion_recommendation(
            evidence_rows=[_row(COMPLETION_ROW, date=PRE)])
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["verdict"], "no-verdict")

    def test_review_and_triage_rows_are_not_completions(self):
        """REVIEW-/TRIAGE- prefixed product-code rows must not require
        snapshots (only EVD- completion rows do)."""
        r = vw.check_completion_recommendation(
            evidence_rows=[_row(REVIEW_ROW), _row(TRIAGE_ROW)])
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["verdict"], "no-verdict")

    def test_multi_task_ref_completion_requires_each(self):
        """EVD-903 pattern: task_ref 'FIX-300, FIX-301' — both tasks are
        completions; a snapshot covering only one → FAIL for the other."""
        completion_both = _row(COMPLETION_ROW).replace(
            "| EVD-FIX-300 | FIX-300 |", "| EVD-903 | FIX-300, FIX-301 |", 1)
        r = vw.check_completion_recommendation(
            evidence_rows=[completion_both, _row(MACHINE_SNAPSHOT_ROW)])
        self.assertEqual(r["verdict"], "FAIL")
        s1 = [v for v in r["violations"] if v["rule"] == "S1"]
        self.assertEqual({v["task_id"] for v in s1}, {"FIX-301"})

    def test_s2_snapshot_section_without_reference_warns(self):
        """Signal 4: 下次会话优先级 has entries but no snapshot ID → WARN."""
        snapshot = "## 下次会话优先级\n- 候选A：继续推进\n- 候选B：观察项\n"
        r = vw.check_completion_recommendation(
            evidence_rows=[_row(COMPLETION_ROW), _row(MACHINE_SNAPSHOT_ROW)],
            snapshot_text=snapshot)
        self.assertEqual(r["verdict"], "WARN")
        self.assertIn("S2", {w["rule"] for w in r["warnings"]})

    def test_s2_snapshot_section_with_reference_passes(self):
        snapshot = ("## 下次会话优先级\n- 候选A（依据 RECO-FIX-300）\n")
        r = vw.check_completion_recommendation(
            evidence_rows=[_row(COMPLETION_ROW), _row(MACHINE_SNAPSHOT_ROW)],
            snapshot_text=snapshot)
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["verdict"], "PASS")

    def test_s2_empty_snapshot_section_not_judged(self):
        snapshot = "## 下次会话优先级\n\n## 用户偏好设置\n- none\n"
        r = vw.check_completion_recommendation(
            evidence_rows=[_row(COMPLETION_ROW), _row(MACHINE_SNAPSHOT_ROW)],
            snapshot_text=snapshot)
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["verdict"], "PASS")

    def test_s3_dangling_reference_fails(self):
        """Referenced snapshot ID absent from evidence-log → FAIL/S3."""
        snapshot = "## 下次会话优先级\n- 候选A（依据 RECO-FIX-999）\n"
        r = vw.check_completion_recommendation(
            evidence_rows=[_row(COMPLETION_ROW), _row(MACHINE_SNAPSHOT_ROW)],
            snapshot_text=snapshot)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("S3", {v["rule"] for v in r["violations"]})

    def test_s3_evd_reference_form_accepted(self):
        """Legacy EVD-{n} snapshot references are valid derivation anchors."""
        snapshot = "## 下次会话优先级\n- 候选A（依据 EVD-899）\n"
        rows = [_row(COMPLETION_ROW), _row(LEGACY_SNAPSHOT_ROW)]
        r = vw.check_completion_recommendation(
            evidence_rows=rows, snapshot_text=snapshot)
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["verdict"], "PASS")

    def test_live_mode_reads_patched_paths(self):
        """Live mode (no fixtures) reads EVIDENCE_PATH/SESSION_SNAPSHOT_PATH."""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            gov.mkdir()
            (gov / "evidence-log.md").write_text(
                _row(COMPLETION_ROW) + "\n", encoding="utf-8")
            (gov / "session-snapshot.md").write_text(
                "# 会话快照\n## 下次会话优先级\n- x\n", encoding="utf-8")
            with mock.patch.object(vw, "EVIDENCE_PATH",
                                   gov / "evidence-log.md"), \
                 mock.patch.object(vw, "SESSION_SNAPSHOT_PATH",
                                   gov / "session-snapshot.md"):
                r = vw.check_completion_recommendation()
            self.assertEqual(r["verdict"], "FAIL")  # S1: no snapshot row
            self.assertEqual(r["stats"]["completions_judged"], 1)


class RecommendationSnapshotWriteTests(unittest.TestCase):
    """--evidence-task machine row writer (row text shape + I/O)."""

    def _report(self):
        fixture = (
            "# plan\n\n### 优先级一览\n\n"
            "| 任务 | 优先级 | 状态 | 依赖 | 版本 |\n"
            "|---|---|---|---|---|\n"
            "| FIX-300 | P0 | ✅ 完成 |  | 0.75.0 |\n"
            "| FIX-301 | P1 | ⏳ 进行中 | FIX-300 | 0.75.0 |\n"
        )
        return compute_unblocked_tasks(parse_task_dependencies(fixture))

    def test_row_text_shape(self):
        text = vw._recommendation_snapshot_row_text("FIX-300", self._report(),
                                                    "2026-08-22")
        self.assertTrue(text.startswith("| RECO-FIX-300 | FIX-300 |"))
        self.assertIn("task-priority-analysis 机器写入完成必推荐调用快照", text)
        self.assertIn("事实依据：task-priority-analysis 输出摘要（机器写入）", text)
        self.assertIn("2026-08-22", text)
        self.assertEqual(len([c for c in text.split("|")]) - 2, 10)
        self.assertTrue(text.endswith("|\n"))

    def test_write_appends_row_and_returns_summary(self):
        with tempfile.TemporaryDirectory() as td:
            ev = Path(td) / "evidence-log.md"
            ev.write_text("| header |\n", encoding="utf-8")
            summary = vw._write_recommendation_snapshot(
                "FIX-300", self._report(), evidence_path=ev)
            self.assertEqual(summary["row_id"], "RECO-FIX-300")
            self.assertTrue(summary["written"])
            content = ev.read_text(encoding="utf-8")
            self.assertIn("RECO-FIX-300", content)
            self.assertIn("task-priority-analysis 机器写入", content)

    def test_write_fail_closed_on_bad_task_id(self):
        with tempfile.TemporaryDirectory() as td:
            ev = Path(td) / "evidence-log.md"
            ev.write_text("| header |\n", encoding="utf-8")
            summary = vw._write_recommendation_snapshot(
                "not-a-task", self._report(), evidence_path=ev)
            self.assertIn("error", summary)
            self.assertNotIn("RECO-", ev.read_text(encoding="utf-8"))


class ContractPinningTests(unittest.TestCase):
    """Protocol/spec surfaces carry the machine-write + derivation rules."""

    def test_behavior_protocol_step6a_carries_machine_write_rule(self):
        text = (_INFRA_DIR.parent / "references" / "behavior-protocol.md"
                ).read_text(encoding="utf-8")
        self.assertIn("--evidence-task", text)
        self.assertIn("RECO-", text)

    def test_governance_md_snapshot_spec_carries_derivation_rule(self):
        text = (_INFRA_DIR.parent.parent.parent / "commands" / "governance.md"
                ).read_text(encoding="utf-8")
        self.assertIn("下次会话优先级", text)
        self.assertIn("RECO-", text)


if __name__ == "__main__":
    unittest.main()
