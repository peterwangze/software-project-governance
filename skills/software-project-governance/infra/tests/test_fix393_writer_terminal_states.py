"""FIX-393 — writer-terminal (committed) recognition across the three parsers.

Writer contract (authoritative status source, 0.86.0 M0 batch-1):

  - ``infra/contracts.py`` ``TASK_STATES`` / ``TASK_TRANSITIONS`` —
    ``committed`` is the ONLY state with an empty legal-transition tuple
    (the terminal state); ``completed`` is NOT terminal (completed ->
    committed is legal, which is why the existing ✅ word-form handling is
    left untouched by this fix).
  - ``infra/task_row_update.py`` — the governed write path. Its status
    vocabulary is the ordered mutually-exclusive marker chain
    (``_STATE_MARKER_CHAIN``, first hit wins over the status cell) and every
    writer flip appends the ops receipt anchor ``〔op-<32hex>〕`` to the
    status cell (DoD 9 machine provenance).

Live bug this locks down (0.88.0 delivered tickets, plan-tracker 2026-09-25):
the writer flipped FEAT-060/061/062/063/064, FIX-384/385 and REL-086~089 to
``committed`` (ledger: ``completed -> committed``), but the three status
parsers (task_priority / verify_workflow.parse_current_active_tasks family /
archive) only recognized the hand-written-era ✅/word-forms, so delivered
tickets were re-recommended (FEAT-060/REL-086/REL-087) and their dependents
mis-blocked (FEAT-061/064/063/385).

Terminal criterion under test (display-prefix text is NEVER authoritative):
    writer-terminal  ⟺  chain first-hit == "committed"  AND  ops anchor present
A cell that merely SAYS "committed" without the anchor was not written by the
governed writer (B-1 hand-edit class) — it stays active / un-archivable.

All tests use in-memory fixture strings shaped from the LIVE plan-tracker
cells; the real ``.governance/`` is never touched.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_fix393_writer_terminal_states.py -v
"""

import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import task_row_update as tru  # noqa: E402
import task_priority as tp  # noqa: E402
import archive as archive_mod  # noqa: E402
import verify_workflow as vw  # noqa: E402
from contracts import TASK_STATES, TASK_TRANSITIONS  # noqa: E402


# ── Live status-cell shapes (plan-tracker 2026-09-25, verbatim forms) ───────

ANCHOR_FEAT060 = "op-1fa546084f264d86ba0a8b4aa55995d1"
ANCHOR_REL086 = "op-cf8f6d882e6145cb83410c11bf96e6d4"
ANCHOR_REL087 = "op-60f89205d9e2491e871818e538d39b04"
ANCHOR_TRIAGE = "op-c8517aad1e134c7ab78f1efbdccec8fd"

# committed 已 lock 待派发 — the 0.88 阶段 B1~E6 batch form (FEAT-060/061/
# 062/064/063, FIX-384/385). Anchor mid-cell is a REAL live shape: FEAT-061's
# cell carries a second 〔R0 …〕 narrative bracket AFTER the anchor.
COMMITTED_LOCKED_ANCHORED = (
    "committed 已 lock 待派发 (2026-09-23——0.88 阶段 B1) 〔" + ANCHOR_FEAT060 + "〕"
)
COMMITTED_LOCKED_ANCHORED_MIDCELL = (
    "committed 已 lock 待派发 (2026-09-23——0.88 阶段 C1) 〔" + ANCHOR_FEAT060
    + "〕〔R0 NEEDS_CHANGE/2→R1 APPROVED_WITH_NOTES/0；commit 61618a5〕"
)
# committed 已发布 — the release-closure form (REL-086). The live cell's
# parenthetical narrative carries the released version literal; it is
# elided here (DEC-213 static-pin discipline) — the load-bearing form is
# the committed token + 已发布 wording + ops anchor, which the recognition
# keys on.
COMMITTED_RELEASED_ANCHORED = (
    "committed 已发布 (2026-09-25——发布闭环) 〔" + ANCHOR_REL086 + "〕"
)
# committed 审查中 WITH the writer anchor — live REL-087; ledger authority
# (completed -> committed, "Landed (M-1 candidate)") outranks the stale
# display narrative 审查中.
COMMITTED_REVIEWING_ANCHORED = (
    "committed 审查中 (2026-09-25——check-version-consistency 全过；"
    "Code Reviewer 派发中) 〔" + ANCHOR_REL087 + "〕"
)
# committed 审查中 WITHOUT the anchor — display-prefix text only; the
# governed writer never wrote it → NOT terminal (negative case).
COMMITTED_REVIEWING_NO_ANCHOR = "committed 审查中 (2026-09-26——审查派发中)"
COMMITTED_RELEASED_NO_ANCHOR = "committed 已发布 (2026-09-26——发布闭环)"
# Non-committed live shapes that MUST keep their current verdicts.
TRIAGED_ANCHORED = "🆕 已 triage 待排期 (2026-09-25——0.89 M-0 立项) 〔" + ANCHOR_TRIAGE + "〕"
IN_PROGRESS = "🔄 进行中 (2026-09-26)"
PENDING = "⏳ 待执行"
COMPLETED_DOGFOOD = "✅ 完成 (2026-06-30)"
UNKNOWN_TOKEN = "🧪 未知token形态 (2026-09-26)"
MIXED_CHAIN_REOPENED = "✅ 已发布 (2026-09-20) → 🔄 reopened (2026-09-21)"


def _writer_committed_row(task_id, op_id, from_state="dev"):
    """A REAL writer product: flip a row to committed via the governed writer."""
    base_row = (
        "| **P1** | {0} | fixture title | — | 0.89.0 | 产品代码 | 🔄 进行中 |"
        .format(task_id)
    )
    if from_state != "dev":
        base_row = base_row.replace("🔄 进行中",
                                    tru.STATE_CANONICAL_MARKERS[from_state])
    return tru.build_candidate_row(
        base_row, from_state=from_state, to_state="committed",
        operation_id=op_id)


class TestWriterContractAuthority(unittest.TestCase):
    """The parsers' judgment is pinned to the writer contract, machine-checked."""

    def test_committed_is_the_only_contract_terminal_state(self):
        """contracts.TASK_TRANSITIONS: only committed has an empty out-edge set.

        This is the semantic the three parsers encode; completed is NOT
        terminal (completed -> committed is legal), which is why the
        existing ✅ handling is untouched by FIX-393.
        """
        terminal = [s for s in TASK_STATES if not TASK_TRANSITIONS[s]]
        self.assertEqual(terminal, ["committed"])

    def test_task_priority_mirror_equals_writer_chain(self):
        self.assertEqual(
            [(name, p.pattern) for name, p in tp._WRITER_STATE_MARKER_CHAIN],
            [(name, p.pattern) for name, p in tru._STATE_MARKER_CHAIN])

    def test_archive_mirror_equals_writer_chain(self):
        self.assertEqual(
            [(name, p.pattern) for name, p in
             archive_mod._WRITER_STATE_MARKER_CHAIN],
            [(name, p.pattern) for name, p in tru._STATE_MARKER_CHAIN])

    def test_verify_workflow_reuses_writer_chain_by_identity(self):
        """verify_workflow imports task_row_update already — it must consume
        the writer's chain object itself (identity, zero drift by design)."""
        self.assertIs(vw._WRITER_STATE_MARKER_CHAIN, tru._STATE_MARKER_CHAIN)

    def test_anchor_regexes_match_real_writer_output(self):
        """All three anchor regexes detect the anchor the writer ACTUALLY
        appends (build_candidate_row product), including the mid-cell live
        shape FEAT-061 carries (anchor followed by a narrative bracket)."""
        row = _writer_committed_row("FIX-9901", ANCHOR_FEAT060)
        self.assertIn("〔" + ANCHOR_FEAT060 + "〕", row)
        # STATUS_CELL_OP_SUFFIX_PATTERN is CELL-scoped (end-anchored) —
        # assert it on the writer's own status cell, not on the whole row.
        status_cell = row.split("|")[-2].strip()
        self.assertRegex(status_cell, tru.STATUS_CELL_OP_SUFFIX_PATTERN)
        for anchor_re in (tp._WRITER_OP_ANCHOR_RE,
                          archive_mod._WRITER_OP_ANCHOR_RE,
                          vw._WRITER_OP_ANCHOR_RE):
            self.assertRegex(row, anchor_re)
        self.assertRegex(COMMITTED_LOCKED_ANCHORED_MIDCELL,
                         tp._WRITER_OP_ANCHOR_RE)


class TestTaskPriorityWriterTerminal(unittest.TestCase):
    """task_priority: delivered tickets leave recommendations and stop blocking."""

    def _report(self, rows_text):
        text = (
            "# 当前项目样例\n\n## 当前活跃事项\n\n### 优先级一览\n\n"
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            + rows_text
        )
        return tp.compute_unblocked_tasks(tp.parse_task_dependencies(text))

    def _row(self, priority, task_id, deps, status):
        return "| {0} | {1} | fixture {1} | {2} | 0.89.0 | 产品代码 | {3} |\n".format(
            priority, task_id, deps or "—", status)

    def test_delivered_committed_rows_are_completed_not_candidates(self):
        report = self._report(
            self._row("**P1**", "FEAT-9001", "—", COMMITTED_LOCKED_ANCHORED)
            + self._row("**P1**", "REL-9002", "—", COMMITTED_RELEASED_ANCHORED)
            + self._row("**P1**", "REL-9003", "—", COMMITTED_REVIEWING_ANCHORED))
        completed_ids = {t.task_id for t in report.completed}
        self.assertIn("FEAT-9001", completed_ids)
        self.assertIn("REL-9002", completed_ids)
        self.assertIn("REL-9003", completed_ids)
        recommended_ids = [t.task_id for t in report.recommended_next]
        self.assertNotIn("FEAT-9001", recommended_ids)
        self.assertNotIn("REL-9002", recommended_ids)
        self.assertNotIn("REL-9003", recommended_ids)
        unblocked_ids = [t.task_id for t in report.unblocked]
        self.assertNotIn("FEAT-9001", unblocked_ids)

    def test_dependents_of_delivered_rows_are_not_blocked(self):
        """The live FEAT-061/064/063/385 mis-block shape: a dependent whose
        only blocker is a committed-delivered row is unblocked (and itself
        delivered-shaped → completed bucket, never a recommendation)."""
        report = self._report(
            self._row("**P1**", "FEAT-9001", "—", COMMITTED_LOCKED_ANCHORED)
            + self._row("**P2**", "FIX-9005", "FEAT-9001",
                        COMMITTED_LOCKED_ANCHORED))
        blocked_ids = [bt.task.task_id for bt in report.blocked]
        self.assertEqual(blocked_ids, [])

    def test_nonterminal_committed_reviewing_without_anchor_stays_active(self):
        """Negative case: 「committed 审查中」 display prefix without the ops
        anchor is NOT terminal — the row still candidates AND still blocks
        its dependents."""
        report = self._report(
            self._row("**P1**", "FIX-9004", "—", COMMITTED_REVIEWING_NO_ANCHOR)
            + self._row("**P2**", "FIX-9006", "FIX-9004", PENDING))
        recommended_ids = [t.task_id for t in report.recommended_next]
        self.assertIn("FIX-9004", recommended_ids)
        blocked = {bt.task.task_id: tuple(bt.blocking_dependencies)
                   for bt in report.blocked}
        self.assertEqual(blocked.get("FIX-9006"), ("FIX-9004",))

    def test_active_and_triaged_rows_still_participate(self):
        """Negative cases: 🔄 进行中 / 🆕 已 triage (with writer anchor from
        the triage machine record) stay non-terminal — they candidate and
        block, exactly as before FIX-393."""
        report = self._report(
            self._row("**P1**", "FEAT-9006", "—", IN_PROGRESS)
            + self._row("**P1**", "FIX-9007", "—", TRIAGED_ANCHORED))
        recommended_ids = [t.task_id for t in report.recommended_next]
        self.assertIn("FEAT-9006", recommended_ids)
        self.assertIn("FIX-9007", recommended_ids)

    def test_unknown_token_is_never_guessed_terminal(self):
        report = self._report(self._row("**P2**", "FIX-9008", "—", UNKNOWN_TOKEN))
        recommended_ids = [t.task_id for t in report.recommended_next]
        self.assertIn("FIX-9008", recommended_ids)

    def test_predicate_matrix(self):
        self.assertTrue(tp._status_is_writer_committed(COMMITTED_LOCKED_ANCHORED))
        self.assertTrue(tp._status_is_writer_committed(
            COMMITTED_LOCKED_ANCHORED_MIDCELL))
        self.assertTrue(tp._status_is_writer_committed(COMMITTED_RELEASED_ANCHORED))
        self.assertTrue(tp._status_is_writer_committed(COMMITTED_REVIEWING_ANCHORED))
        self.assertFalse(tp._status_is_writer_committed(COMMITTED_REVIEWING_NO_ANCHOR))
        self.assertFalse(tp._status_is_writer_committed(COMMITTED_RELEASED_NO_ANCHOR))
        self.assertFalse(tp._status_is_writer_committed(TRIAGED_ANCHORED))
        self.assertFalse(tp._status_is_writer_committed(IN_PROGRESS))
        self.assertFalse(tp._status_is_writer_committed(PENDING))
        self.assertFalse(tp._status_is_writer_committed(COMPLETED_DOGFOOD))
        self.assertFalse(tp._status_is_writer_committed(UNKNOWN_TOKEN))
        self.assertFalse(tp._status_is_writer_committed(""))
        # Existing completed verdict is unchanged (✅ word-form family).
        self.assertTrue(tp.TaskDep(
            task_id="FIX-9009", priority="P1",
            status=COMPLETED_DOGFOOD).is_completed())

    def test_real_writer_product_end_to_end(self):
        """A row actually flipped by the governed writer is terminal in the
        dependency analysis (the alignment the fix guarantees)."""
        row = _writer_committed_row("FEAT-9010", ANCHOR_FEAT060)
        report = self._report(
            row + "\n" + self._row("**P2**", "FIX-9011", "FEAT-9010", PENDING))
        completed_ids = {t.task_id for t in report.completed}
        self.assertIn("FEAT-9010", completed_ids)
        self.assertEqual([bt.task.task_id for bt in report.blocked], [])


class TestVerifyWorkflowWriterTerminal(unittest.TestCase):
    """parse_current_active_tasks family: the authoritative terminal predicate."""

    def test_completed_cell_matrix(self):
        # Writer-terminal committed rows → completed.
        for cell in (COMMITTED_LOCKED_ANCHORED, COMMITTED_LOCKED_ANCHORED_MIDCELL,
                     COMMITTED_RELEASED_ANCHORED, COMMITTED_REVIEWING_ANCHORED):
            self.assertTrue(vw._status_is_completed_cell(cell), cell)
        # Display-prefix committed WITHOUT the anchor → still active.
        for cell in (COMMITTED_REVIEWING_NO_ANCHOR, COMMITTED_RELEASED_NO_ANCHOR):
            self.assertFalse(vw._status_is_completed_cell(cell), cell)
        # Non-committed live shapes keep their verdicts.
        self.assertFalse(vw._status_is_completed_cell(TRIAGED_ANCHORED))
        self.assertFalse(vw._status_is_completed_cell(IN_PROGRESS))
        self.assertFalse(vw._status_is_completed_cell(PENDING))
        self.assertFalse(vw._status_is_completed_cell(UNKNOWN_TOKEN))
        self.assertFalse(vw._status_is_completed_cell(MIXED_CHAIN_REOPENED))
        # Pre-existing dogfood conventions unchanged (regression pins).
        self.assertTrue(vw._status_is_completed_cell(COMPLETED_DOGFOOD))
        self.assertTrue(vw._status_is_completed_cell("已完成"))
        self.assertTrue(vw._status_is_completed_cell("已发布"))
        self.assertTrue(vw._status_is_completed_cell(
            "🔄 进行中 (…) → ✅ 完成 (2026-09-01)"))
        self.assertFalse(vw._status_is_completed_cell("未完成"))
        self.assertFalse(vw._status_is_completed_cell(""))
        # Conservative narrative guard inherited: a committed cell carrying
        # an explicit 未完成 narrative stays ACTIVE.
        self.assertFalse(vw._status_is_completed_cell(
            "committed 已发布 (2026-09-25) 〔" + ANCHOR_REL086 + "〕——验收未完成"))

    def test_incomplete_task_status_mirror(self):
        self.assertFalse(vw._is_incomplete_task_status(COMMITTED_LOCKED_ANCHORED))
        self.assertFalse(vw._is_incomplete_task_status(COMMITTED_RELEASED_ANCHORED))
        self.assertFalse(vw._is_incomplete_task_status(COMMITTED_REVIEWING_ANCHORED))
        self.assertTrue(vw._is_incomplete_task_status(COMMITTED_REVIEWING_NO_ANCHOR))
        self.assertTrue(vw._is_incomplete_task_status(TRIAGED_ANCHORED))
        self.assertTrue(vw._is_incomplete_task_status(IN_PROGRESS))

    def test_active_execution_packet_tasks_excludes_delivered_rows(self):
        """The parse_current_active_tasks consumer family (execution-packet
        Check 18c feed / resume state) stops counting delivered committed
        rows as active. Evidence-entry criteria are NOT touched here."""
        tracker = (
            "# 当前项目样例\n\n## 当前活跃事项\n\n"
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            "| **P1** | FEAT-9101 | t | — | 8.8.8 | 产品代码 | "
            + COMMITTED_LOCKED_ANCHORED + " |\n"
            "| **P1** | FIX-9102 | t | — | 0.89.0 | 产品代码 | "
            + TRIAGED_ANCHORED + " |\n"
            "| **P1** | FIX-9103 | t | — | 0.89.0 | 产品代码 | "
            + COMMITTED_REVIEWING_NO_ANCHOR + " |\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "plan-tracker.md"
            sample.write_text(tracker, encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sample):
                active = vw._active_execution_packet_tasks()
        active_ids = [t["task_id"] for t in active]
        self.assertNotIn("FEAT-9101", active_ids)
        self.assertIn("FIX-9102", active_ids)
        self.assertIn("FIX-9103", active_ids)


class TestArchiveWriterTerminal(unittest.TestCase):
    """archive: committed-delivered rows are archivable; unanchored forms are not."""

    def test_archivable_matrix(self):
        # Writer-terminal committed rows → archivable.
        for cell in (COMMITTED_LOCKED_ANCHORED, COMMITTED_LOCKED_ANCHORED_MIDCELL,
                     COMMITTED_RELEASED_ANCHORED, COMMITTED_REVIEWING_ANCHORED):
            self.assertTrue(archive_mod._task_status_is_archivable(cell), cell)
        # Display-prefix committed WITHOUT the anchor → not archivable
        # (fail-closed: a hand-edited cell is never guessed terminal).
        for cell in (COMMITTED_REVIEWING_NO_ANCHOR, COMMITTED_RELEASED_NO_ANCHOR,
                     "已提交 (2026-09-26)"):
            self.assertFalse(archive_mod._task_status_is_archivable(cell), cell)
        # Open shapes keep their verdicts.
        for cell in (TRIAGED_ANCHORED, IN_PROGRESS, PENDING, "⏳ 待启动 (依赖 FIX-157)",
                     "未完成", "TO_BE_DEFINED"):
            self.assertFalse(archive_mod._task_status_is_archivable(cell), cell)
        # Legacy closed word-forms unchanged (regression pins).
        for cell in ("✅ 已完成", "✅ 已发布", "已交付", "调查完成", "✅ 已撤回/失效"):
            self.assertTrue(archive_mod._task_status_is_archivable(cell), cell)

    def test_priority_table_scan_sees_committed_row_as_archivable(self):
        content = (
            "### 优先级一览\n\n"
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            "| **P1** | FEAT-9201 | t | — | 9.9.9 | 产品代码 | "
            + COMMITTED_LOCKED_ANCHORED + " |\n"
        )
        tasks = archive_mod._parse_priority_table_tasks(content)
        self.assertEqual(len(tasks), 1)
        self.assertTrue(archive_mod._task_status_is_archivable(tasks[0][4]))
        versions = archive_mod._parse_completed_task_versions(content)
        self.assertEqual(versions, {"FEAT-9201": "9.9.9"})


if __name__ == "__main__":
    unittest.main()
