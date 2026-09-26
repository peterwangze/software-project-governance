"""FIX-394 — terminal-row text refresh: progress-suffix refresh on flip +
one-shot alignment tool face for the 13 stale terminal rows (0.88 batch B~E +
release chain).

Problem being fixed (live plan-tracker 2026-09-25/26, ops-ledger-verified):
the writer flipped the 0.88 delivered batch to ``committed`` (terminal), but
the status column still carries the PRE-flip mid-flight progress wording —
「committed 已 lock 待派发 (…)」「committed 审查中 (…)」「committed 开发中
(…)」「committed 收尾中 (…)」 — because the narrative was appended after the
flip and no mechanism ever refreshed it. FIX-393 taught the three parsers to
see through the stale wording (chain-first committed + ops anchor is the
authoritative terminal signal); FIX-394 fixes the TEXT itself:

  ① Runtime mechanism — when the writer lands a state token
     (``build_candidate_row``), stale mid-flight progress phrases in the
     status cell are refreshed: a terminal flip (to ``committed``) clears
     ALL stale progress phrases; a non-terminal flip clears only phrases
     whose narrated phase differs from the target state (the row's own
     phase wording survives, narrative inside parentheses is never touched).
  ② Alignment tool face — ``--refresh-suffix``: a one-shot machine-recorded
     alignment channel for rows ALREADY at the writer terminal state (no
     legal transition exists to re-run): stale progress wording cleared,
     committed token + ops anchor + parenthetical narrative + post-anchor
     brackets preserved, receipt appended, idempotent.

Refresh semantics boundary (deliberate, test-pinned):
  CLEARED — only the closed stale-progress phrase vocabulary
  (:data:`task_row_update.STALE_PROGRESS_PHRASES`), outside parentheses,
  before the ops anchor.
  PRESERVED — the committed token itself, the date/narrative parentheses,
  the ops anchor (re-anchored to the new operation id), any brackets AFTER
  the anchor (FEAT-061's 〔R0 …〕 review-round narrative), every other
  column, and the cell's padding whitespace.

Live-cell fixtures below mirror the real rows (shapes verbatim; id/hash
literals are fixture-local per the DEC-213 static-pin discipline).

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_fix394_progress_suffix_refresh.py -v
"""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import task_row_update as tru  # noqa: E402
import task_priority as tp  # noqa: E402
import archive as archive_mod  # noqa: E402
import verify_workflow as vw  # noqa: E402
from contracts import TASK_STATES, TASK_TRANSITIONS  # noqa: E402

OP_A = "op-" + "a" * 32
OP_B = "op-" + "b" * 32
OP_C = "op-" + "c" * 32

_HEADER = "| 优先级 | ID | 描述 | 依据 | 版本 | 执行面与验收 | 状态 |"
_SEPARATOR = "| --- | --- | --- | --- | --- | --- | --- |"

# ── Live status-cell shapes (0.88 batch B~E + release chain) ────────────────

# committed 已 lock 待派发 — FEAT-060/FIX-383/FEAT-061/FEAT-062/FEAT-064/
# FEAT-063/FEAT-044/FIX-384/FIX-385 (9 rows).
LIVE_LOCKED = (
    "committed 已 lock 待派发 (2026-09-23——0.88 阶段 B1) 〔" + OP_A + "〕")
# committed 审查中 — REL-087.
LIVE_REVIEWING = (
    "committed 审查中 (2026-09-25——check-version-consistency 全过；"
    "Code Reviewer 派发中) 〔" + OP_B + "〕")
# committed 开发中 — REL-088 (parenthetical narrative carries its own 〔…〕
# bracket — the anchor locator must never key on the first 〔).
LIVE_DEVING = (
    "committed 开发中 (2026-09-25——并行派发〔docs/release 文件族独立〕) 〔"
    + OP_C + "〕")
# committed 收尾中 — REL-089.
LIVE_WRAPPING = (
    "committed 收尾中 (2026-09-25——4119P/0F+两新文件+rollback §8 落位；"
    "commit 待重试〔hook 入账拦截已补行〕) 〔" + OP_C + "〕")
# Anchor followed by a narrative bracket — FEAT-061's real shape.
LIVE_MIDCELL_NARRATIVE = (
    "committed 已 lock 待派发 (2026-09-23——0.88 阶段 C1) 〔" + OP_A + "〕"
    "〔R0 NEEDS_CHANGE/2→R1 APPROVED_WITH_NOTES/0；commit 61618a5〕")
# The target-form reference (REL-086): committed + legitimate release
# narrative — NOT a stale mid-flight phrase; refresh must be a no-op here.
LIVE_RELEASED_REFERENCE = (
    "committed 已发布 (2026-09-25——发布闭环) 〔" + OP_B + "〕")

LIVE_STALE_SHAPES = (LIVE_LOCKED, LIVE_REVIEWING, LIVE_DEVING, LIVE_WRAPPING)


def _row(priority, task_id, status):
    return ("| {0} | {1} | fixture {1} | — | 0.89.0 | 产品代码 | {2} |"
            .format(priority, task_id, status))


def _table(*rows, eol="\n"):
    return eol.join([_HEADER, _SEPARATOR] + list(rows)) + eol


def _cell_text(row_line):
    """The raw status cell (stripped) of a row line."""
    cells = row_line.strip().split("|")
    return cells[tru._status_cell(cells)[0]].strip()


class _TrackerFixture(unittest.TestCase):
    """Temp governed table + ledger with CLI/library helpers."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="fix394_"))
        self.target = self.tmpdir / "plan-tracker.md"
        self.ledger = self.tmpdir / "plan-tracker.md.ops.jsonl"

    def tearDown(self):
        for entry in sorted(self.tmpdir.rglob("*"), reverse=True):
            try:
                if entry.is_file() or entry.is_symlink():
                    entry.unlink()
                else:
                    entry.rmdir()
            except OSError:
                pass
        try:
            self.tmpdir.rmdir()
        except OSError:
            pass

    def write_table(self, text):
        self.target.write_text(text, encoding="utf-8", newline="")
        return text

    def read_text(self):
        return self.target.read_text(encoding="utf-8")

    def status_cell_of(self, task_id):
        """The raw status cell (last non-empty cell) of the anchored row."""
        _, line = tru.locate_task_row(self.read_text(), task_id)
        return _cell_text(line)

    def run_cli(self, *args):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = tru.main(list(args))
        out = buffer.getvalue()
        try:
            payload = json.loads(out.strip() or "{}")
        except ValueError:
            payload = {"_raw": out}
        return code, payload


class TestStaleVocabulary(unittest.TestCase):
    """The closed stale-progress phrase vocabulary (facts, not guesses)."""

    def test_vocabulary_is_closed_and_phase_annotated(self):
        phrases = [p for p, _ in tru.STALE_PROGRESS_PHRASES]
        # The four LIVE mid-flight wordings (the ticket names them) are in.
        for phrase in ("已 lock 待派发", "审查中", "开发中", "收尾中"):
            self.assertIn(phrase, phrases)
        # Chain mid-flight word-forms the writer itself may leave behind.
        for phrase in ("待审查", "已审查", "进行中"):
            self.assertIn(phrase, phrases)
        # Terminal-state narrative words are NEVER in the vocabulary — the
        # refresh must not erase legitimate history (REL-086 已发布).
        for taboo in ("已发布", "已完成", "完成", "已交付"):
            self.assertNotIn(taboo, phrases)
        # Every phrase is annotated with a TASK_STATES member.
        for _, phase in tru.STALE_PROGRESS_PHRASES:
            self.assertIn(phase, TASK_STATES)

    def test_committed_is_the_only_terminal_state(self):
        self.assertEqual(
            [s for s in TASK_STATES if not TASK_TRANSITIONS[s]],
            ["committed"])


class TestRuntimeSuffixRefreshOnFlip(_TrackerFixture):
    """① The flip path refreshes the progress suffix as it lands a token."""

    def _flip(self, status_cell, from_state, to_state, op_id=OP_B):
        line = _row("**P1**", "FIX-9001", status_cell)
        return tru.build_candidate_row(
            line, from_state=from_state, to_state=to_state,
            operation_id=op_id)

    def test_review_to_approved_clears_stale_review_wording(self):
        out = _cell_text(self._flip(
            "review 审查中 (2026-09-25——Reviewer 派发中)", "review",
            "approved"))
        self.assertTrue(out.startswith("approved"), out)
        self.assertNotIn("审查中", out)
        self.assertNotIn("review", out)
        self.assertIn("(2026-09-25——Reviewer 派发中)", out)
        self.assertRegex(out, tru.STATUS_CELL_OP_SUFFIX_PATTERN)

    def test_terminal_flip_clears_all_stale_progress_phrases(self):
        out = _cell_text(self._flip(
            "✅ 完成 已 lock 待派发 审查中 (2026-09-26)", "completed",
            "committed"))
        self.assertTrue(out.startswith("committed"), out)
        for stale in ("已 lock 待派发", "审查中", "开发中", "收尾中",
                      "待审查", "已审查", "进行中"):
            self.assertNotIn(stale, out)
        self.assertIn("(2026-09-26)", out)
        self.assertRegex(out, tru.STATUS_CELL_OP_SUFFIX_PATTERN)

    def test_nonterminal_flip_keeps_target_phase_wording(self):
        # review→dev is a legal transition (rework); 「开发中」 narrates the
        # target dev phase → survives the refresh (narrative chain intact).
        out = _cell_text(self._flip(
            "review 开发中 (2026-09-26——回退返工)", "review", "dev"))
        self.assertTrue(out.startswith(tru.STATE_CANONICAL_MARKERS["dev"]),
                        out)
        self.assertIn("开发中", out)
        self.assertNotIn("审查中", out)

    def test_nonterminal_flip_keeps_parenthetical_narrative_verbatim(self):
        out = _cell_text(self._flip(
            "🔄 进行中 (2026-09-26——M-0 完成，进入 review 准备)", "dev",
            "review"))
        self.assertTrue(out.startswith("review"), out)
        self.assertIn("(2026-09-26——M-0 完成，进入 review 准备)", out)

    def test_other_columns_are_byte_identical(self):
        line = _row("**P1**", "FIX-9002",
                    "review 审查中 (2026-09-25——派发中) 〔" + OP_A + "〕")
        out = tru.build_candidate_row(
            line, from_state="review", to_state="approved",
            operation_id=OP_B)
        old_cells = line.strip().split("|")
        new_cells = out.strip().split("|")
        self.assertEqual(len(old_cells), len(new_cells))
        status_idx = tru._status_cell(old_cells)[0]
        for i, (a, b) in enumerate(zip(old_cells, new_cells)):
            if i != status_idx:
                self.assertEqual(a, b, "column {0} mutated".format(i))

    def test_flip_replay_is_byte_idempotent(self):
        self.write_table(_table(
            _row("**P1**", "FIX-9003",
                 "review 审查中 (2026-09-25——派发中)")))
        first = tru.execute_update(
            target=self.target, task_id="FIX-9003", from_state="review",
            to_state="approved", reason="r0", operation_id=OP_A)
        self.assertEqual(first.code, "ok")
        before = self.read_text()
        second = tru.execute_update(
            target=self.target, task_id="FIX-9003", from_state="review",
            to_state="approved", reason="r0", operation_id=OP_A)
        self.assertEqual(second.code, "ok")
        self.assertEqual(self.read_text(), before,
                         "replay mutated the file")
        self.assertIn("replay of operation", second.detail)

    def test_full_chain_lands_clean_committed_token(self):
        # dev→review→approved→completed→committed: every hop through the
        # real writer; the final row carries committed + anchor and NONE of
        # the mid-flight wordings.
        self.write_table(_table(
            _row("**P2**", "FIX-9004", "🔄 进行中 (2026-09-26)")))
        hops = (("dev", "review"), ("review", "approved"),
                ("approved", "completed"), ("completed", "committed"))
        for i, (frm, to) in enumerate(hops):
            result = tru.execute_update(
                target=self.target, task_id="FIX-9004", from_state=frm,
                to_state=to, reason="hop {0}".format(i),
                operation_id="op-{0:032x}".format(i + 1))
            self.assertEqual(result.code, "ok", result.detail)
        cell = self.status_cell_of("FIX-9004")
        self.assertTrue(cell.startswith("committed"), cell)
        for stale in ("审查中", "待审查", "已审查", "开发中", "收尾中",
                      "进行中"):
            self.assertNotIn(stale, cell)
        self.assertRegex(cell, tru.STATUS_CELL_OP_SUFFIX_PATTERN)


class TestRefreshAlignmentTool(_TrackerFixture):
    """② --refresh-suffix: the one-shot alignment channel for stale
    terminal rows (the 13-row batch)."""

    def _refresh(self, task_id, status_cell, op_id=OP_B, reason=None,
                 **kwargs):
        self.write_table(_table(_row("**P1**", task_id, status_cell)))
        return tru.execute_refresh(
            target=self.target, task_id=task_id,
            reason=reason or "FIX-394 13-row suffix alignment",
            operation_id=op_id, ledger=self.ledger, **kwargs)

    def test_live_stale_shapes_are_refreshed(self):
        for i, (task_id, cell) in enumerate((
                ("FIX-9101", LIVE_LOCKED),
                ("REL-9102", LIVE_REVIEWING),
                ("REL-9103", LIVE_DEVING),
                ("REL-9104", LIVE_WRAPPING))):
            op_id = "op-{0:032x}".format(i + 1)
            with self.subTest(cell=cell):
                result = self._refresh(task_id, cell, op_id=op_id)
                self.assertEqual(result.code, "ok", result.detail)
                out = self.status_cell_of(task_id)
                self.assertTrue(out.startswith("committed"), out)
                for stale in ("已 lock 待派发", "审查中", "开发中",
                              "收尾中"):
                    self.assertNotIn(stale, out)
                # The date/narrative parentheses survive.
                self.assertIn("(2026-09-2", out)
                # Exactly one ops anchor, and it is the NEW operation id.
                self.assertEqual(out.count("〔op-"), 1)
                self.assertIn("〔" + op_id + "〕", out)

    def test_post_anchor_narrative_bracket_is_preserved(self):
        result = self._refresh("FEAT-9105", LIVE_MIDCELL_NARRATIVE)
        self.assertEqual(result.code, "ok", result.detail)
        out = self.status_cell_of("FEAT-9105")
        self.assertNotIn("已 lock 待派发", out)
        self.assertIn("〔R0 NEEDS_CHANGE/2→R1 APPROVED_WITH_NOTES/0；"
                      "commit 61618a5〕", out)
        self.assertEqual(out.count("〔op-"), 1)

    def test_already_aligned_reference_row_is_a_zero_change_noop(self):
        """REL-086 target form: committed + legitimate release narrative —
        nothing stale → ok, NO write, NO receipt."""
        self.write_table(_table(
            _row("**P1**", "REL-9106", LIVE_RELEASED_REFERENCE)))
        before = self.read_text()
        result = tru.execute_refresh(
            target=self.target, task_id="REL-9106", reason="align",
            operation_id=OP_C, ledger=self.ledger)
        self.assertEqual(result.code, "ok", result.detail)
        self.assertEqual(self.read_text(), before, "zero-change wrote")
        self.assertFalse(self.ledger.is_file(),
                         "zero-change appended a receipt")

    def test_receipt_is_recorded_with_refresh_action(self):
        result = self._refresh("FIX-9107", LIVE_LOCKED)
        self.assertEqual(result.code, "ok")
        receipts = [json.loads(line) for line in
                    self.ledger.read_text(encoding="utf-8").splitlines()
                    if line.strip()]
        self.assertEqual(len(receipts), 1)
        receipt = receipts[0]
        self.assertEqual(receipt["record_kind"], tru.RECEIPT_RECORD_KIND)
        self.assertEqual(receipt.get("action"), tru.REFRESH_ACTION)
        self.assertEqual(receipt["task_id"], "FIX-9107")
        self.assertEqual(receipt["from_state"], "committed")
        self.assertEqual(receipt["to_state"], "committed")
        self.assertNotEqual(receipt["row_before_sha256"],
                            receipt["row_after_sha256"])

    def test_same_operation_id_replays_without_reexecution(self):
        result1 = self._refresh("FIX-9108", LIVE_LOCKED, op_id=OP_A,
                                reason="align")
        self.assertEqual(result1.code, "ok")
        after_first = self.read_text()
        result2 = tru.execute_refresh(
            target=self.target, task_id="FIX-9108", reason="align",
            operation_id=OP_A, ledger=self.ledger)
        self.assertEqual(result2.code, "ok")
        self.assertEqual(self.read_text(), after_first)
        self.assertIn("replay of operation", result2.detail)

    def test_second_refresh_with_new_id_is_zero_change(self):
        self._refresh("FIX-9109", LIVE_REVIEWING, op_id=OP_A)
        after_first = self.read_text()
        receipts_after_first = self.ledger.read_text(
            encoding="utf-8").count("\n")
        result = tru.execute_refresh(
            target=self.target, task_id="FIX-9109", reason="align again",
            operation_id=OP_B, ledger=self.ledger)
        self.assertEqual(result.code, "ok", result.detail)
        self.assertEqual(self.read_text(), after_first)
        self.assertEqual(
            self.ledger.read_text(encoding="utf-8").count("\n"),
            receipts_after_first, "zero-change appended a receipt")

    def test_non_terminal_rows_are_refused_fail_closed(self):
        for task_id, cell in (("FIX-9110", "🔄 进行中 (2026-09-26)"),
                              ("FIX-9111", "review 审查中 (2026-09-26)"),
                              ("FIX-9112", "⏳ 待执行")):
            with self.subTest(cell=cell):
                result = self._refresh(task_id, cell)
                self.assertEqual(result.code, "schema_violation")

    def test_committed_display_prefix_without_anchor_is_refused(self):
        """A hand-edited 「committed 审查中」 with NO ops anchor was never
        written by the governed writer — the alignment tool refuses it
        (B-1 class, fail-closed) instead of laundering the row."""
        result = self._refresh(
            "FIX-9113", "committed 审查中 (2026-09-26——审查派发中)")
        self.assertEqual(result.code, "schema_violation")

    def test_double_anchor_row_is_refused_on_both_paths_identically(self):
        """F-1 (review-FIX-394-CODE-R0): a multi-anchor committed row is
        refused by BOTH faces with the SAME schema_violation classification
        — even with NO stale wording before the anchors (the execute path's
        no-op short-circuit must never launder a cell the surface cannot
        unambiguously re-anchor; check order aligned with the dry-run
        face)."""
        double_anchored = ("committed 已交付 (2026-09-26) 〔" + OP_A + "〕〔"
                           + OP_B + "〕")
        self.write_table(_table(_row("**P1**", "FIX-9140", double_anchored)))
        before = self.read_text()
        # Execute face: refused, nothing written, no receipt.
        result = tru.execute_refresh(
            target=self.target, task_id="FIX-9140", reason="align",
            operation_id=OP_C, ledger=self.ledger)
        self.assertEqual(result.code, "schema_violation", result.detail)
        self.assertEqual(self.read_text(), before)
        self.assertFalse(self.ledger.is_file())
        # Dry-run face: the SAME refusal classification, exit 3.
        code, payload = self.run_cli(
            "--task", "FIX-9140", "--refresh-suffix", "--dry-run",
            "--reason", "align", "--file", str(self.target), "--json")
        self.assertEqual(code, tru.ExitCode.VALIDATION)
        self.assertEqual(payload["refusal"]["code"], "schema_violation")
        self.assertIn("ops anchors", payload["refusal"]["detail"])

    def test_content_cas_conflict_writes_nothing(self):
        self.write_table(_table(_row("**P1**", "FIX-9114", LIVE_LOCKED)))
        stale_revision = tru.inspect_target(
            target=self.target, task_id="FIX-9114")["observed_revision"]
        # The world moves underneath the caller.
        self.write_table(_table(
            _row("**P1**", "FIX-9114", LIVE_LOCKED),
            _row("**P2**", "FIX-9115", LIVE_REVIEWING)))
        result = tru.execute_refresh(
            target=self.target, task_id="FIX-9114", reason="align",
            operation_id=OP_A, expected_revision=stale_revision,
            ledger=self.ledger)
        self.assertEqual(result.code, "revision_conflict")
        self.assertIsNotNone(result.observed_revision)
        # Untouched: the stale wording is still on disk, no receipt.
        self.assertIn("已 lock 待派发", self.status_cell_of("FIX-9114"))
        self.assertFalse(self.ledger.is_file())

    def test_dry_run_previews_without_writing(self):
        self.write_table(_table(_row("**P1**", "FIX-9116", LIVE_LOCKED)))
        before = self.read_text()
        code, payload = self.run_cli(
            "--task", "FIX-9116", "--refresh-suffix", "--dry-run",
            "--reason", "align", "--file", str(self.target), "--json")
        self.assertEqual(code, tru.ExitCode.OK)
        self.assertEqual(payload["mode"], "dry-run")
        self.assertTrue(payload["would_execute"])
        self.assertEqual(payload["writes_performed"], 0)
        self.assertIn("已 lock 待派发", payload["preview"]["row_before"])
        self.assertNotIn("已 lock 待派发",
                         payload["preview"]["row_after"])
        self.assertEqual(self.read_text(), before)

    def test_dry_run_already_aligned_row_previews_zero_change(self):
        """An already-aligned row (the REL-086 reference form) previews
        row_after == row_before — mirroring the execute path's honest
        no-op — instead of showing an anchor swap that never happens."""
        self.write_table(_table(
            _row("**P1**", "REL-9116", LIVE_RELEASED_REFERENCE)))
        before = self.read_text()
        code, payload = self.run_cli(
            "--task", "REL-9116", "--refresh-suffix", "--dry-run",
            "--reason", "align", "--file", str(self.target), "--json")
        self.assertEqual(code, tru.ExitCode.OK)
        self.assertTrue(payload["would_execute"])
        preview = payload["preview"]
        self.assertEqual(preview["row_before"], preview["row_after"])
        self.assertEqual(preview["stale_phrases_found"], [])
        self.assertTrue(preview["already_aligned"])
        self.assertEqual(self.read_text(), before)

    def test_cli_end_to_end_refresh(self):
        self.write_table(_table(_row("**P1**", "FIX-9117", LIVE_LOCKED)))
        code, payload = self.run_cli(
            "--task", "FIX-9117", "--refresh-suffix",
            "--reason", "FIX-394 13-row alignment",
            "--file", str(self.target), "--json")
        self.assertEqual(code, tru.ExitCode.OK, payload)
        self.assertEqual(payload["result"]["code"], "ok")
        self.assertEqual(payload["result"]["action"], "suffix_refresh")
        out = self.status_cell_of("FIX-9117")
        self.assertTrue(out.startswith("committed"))
        self.assertNotIn("已 lock 待派发", out)

    def test_cli_rejects_refresh_with_transition_flags(self):
        self.write_table(_table(_row("**P1**", "FIX-9118", LIVE_LOCKED)))
        buffer = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with redirect_stdout(buffer), redirect_stderr(buffer):
                tru.main(["--task", "FIX-9118", "--refresh-suffix",
                          "--from", "committed", "--to", "committed",
                          "--reason", "x", "--file", str(self.target)])
        self.assertEqual(ctx.exception.code, 2)  # argparse usage contract

    def test_padding_whitespace_never_moves(self):
        line = ("| **P1** | FIX-9119 | t | — | 0.89.0 | 产品代码 |   "
                + LIVE_LOCKED + "   |")
        out = tru.refresh_candidate_row(line, operation_id=OP_B)
        old_cells = line.strip().split("|")
        new_cells = out.strip().split("|")
        idx = tru._status_cell(old_cells)[0]
        self.assertTrue(new_cells[idx].startswith("   committed "))
        self.assertTrue(new_cells[idx].endswith("   "))


class TestComposerClosureCheck1(_TrackerFixture):
    """组合① 前置自检 (FIX-393 × FIX-394 closed loop): writer-committed →
    suffix refresh → all three parsers read the SAME terminal verdict."""

    def _full_writer_chain_to_committed(self, task_id):
        """A REAL writer product: four legal hops to the terminal state."""
        self.write_table(_table(
            _row("**P1**", task_id, "🔄 进行中 (2026-09-26)")))
        hops = (("dev", "review"), ("review", "approved"),
                ("approved", "completed"), ("completed", "committed"))
        for i, (frm, to) in enumerate(hops):
            result = tru.execute_update(
                target=self.target, task_id=task_id, from_state=frm,
                to_state=to, reason="composer hop {0}".format(i),
                operation_id="op-{0:032x}".format(i + 1),
                ledger=self.ledger)
            self.assertEqual(result.code, "ok", result.detail)

    def _age_into_live_088_shape(self, task_id, flip_op_id):
        """Simulate the 0.88 history: mid-flight wording appended AFTER the
        writer's flip (the exact staleness the 13 rows carry)."""
        text = self.read_text()
        _, line = tru.locate_task_row(text, task_id)
        aged = line.replace(
            "committed (2026-09-26) 〔" + flip_op_id + "〕",
            "committed 已 lock 待派发 (2026-09-26——0.88 阶段 B1) 〔"
            + flip_op_id + "〕")
        self.assertNotEqual(aged, line, "aging surgery did not apply")
        self.write_table(text.replace(line, aged))

    def test_refreshed_row_reads_identically_across_three_parsers(self):
        task_id = "FEAT-9120"
        self._full_writer_chain_to_committed(task_id)
        self._age_into_live_088_shape(task_id, "op-{0:032x}".format(4))
        cell_before = self.status_cell_of(task_id)
        self.assertIn("已 lock 待派发", cell_before)
        # FIX-393 already sees through the stale wording:
        self.assertTrue(tp._status_is_writer_committed(cell_before))
        # …but the TEXT is stale → align it.
        result = tru.execute_refresh(
            target=self.target, task_id=task_id, reason="align",
            operation_id=OP_A, ledger=self.ledger)
        self.assertEqual(result.code, "ok", result.detail)
        cell = self.status_cell_of(task_id)

        # (a) writer face: chain-first committed + anchor, still terminal.
        self.assertEqual(tru.detect_row_state(
            tru.locate_task_row(self.read_text(), task_id)[1]),
            "committed")
        report = tru.inspect_target(target=self.target, task_id=task_id,
                                    ledger=self.ledger)
        self.assertTrue(report["found"])
        self.assertEqual(report["state"], "committed")

        # (b) task_priority face: completed bucket, never recommended.
        report_tp = tp.compute_unblocked_tasks(
            tp.parse_task_dependencies(
                _table(_row("**P1**", task_id, cell))))
        self.assertIn(task_id, {t.task_id for t in report_tp.completed})
        self.assertNotIn(task_id,
                         [t.task_id for t in report_tp.recommended_next])
        self.assertTrue(tp._status_is_writer_committed(cell))

        # (c) verify_workflow face (parse_current_active_tasks family).
        self.assertTrue(vw._status_is_completed_cell(cell))
        self.assertTrue(vw._status_is_writer_committed_cell(cell))
        self.assertFalse(vw._is_incomplete_task_status(cell))

        # (d) archive face.
        self.assertTrue(archive_mod._task_status_is_archivable(cell))

        # (e) no stale wording survived anywhere.
        self.assertNotIn("已 lock 待派发", cell)

    def test_closure_probe_face_reads_refreshed_row_as_committed(self):
        """The closure_chain ``task_row_state`` probe consumes the writer's
        --inspect CLI — the exact probe path must report committed on a
        refreshed row (closure leg alignment, acceptance #4)."""
        task_id = "FEAT-9122"
        self._full_writer_chain_to_committed(task_id)
        self._age_into_live_088_shape(task_id, "op-{0:032x}".format(4))
        result = tru.execute_refresh(
            target=self.target, task_id=task_id, reason="align",
            operation_id=OP_A, ledger=self.ledger)
        self.assertEqual(result.code, "ok", result.detail)
        code, payload = self.run_cli(
            "--task", task_id, "--inspect", "--file", str(self.target),
            "--json")
        self.assertEqual(code, tru.ExitCode.OK)
        self.assertTrue(payload["found"])
        self.assertEqual(payload["state"], "committed")


class TestFix393GuardCollaboration(unittest.TestCase):
    """Acceptance #3: refreshed text MUST still satisfy the FIX-393
    writer-terminal criterion (guard assertions on every refreshed shape)."""

    def test_every_refreshed_live_shape_keeps_writer_terminal_verdict(self):
        for i, cell in enumerate(LIVE_STALE_SHAPES
                                 + (LIVE_MIDCELL_NARRATIVE,)):
            with self.subTest(shape=i):
                result = tru.refresh_candidate_row(
                    _row("**P1**", "FIX-9130", cell), operation_id=OP_B)
                out = _cell_text(result)
                self.assertTrue(tp._status_is_writer_committed(out))
                self.assertTrue(vw._status_is_writer_committed_cell(out))
                self.assertTrue(archive_mod._task_status_is_archivable(out))
                self.assertEqual(tru.detect_row_state(result), "committed")

    def test_reference_row_no_op_still_terminal(self):
        self.assertEqual(tru.detect_row_state(
            _row("**P1**", "FIX-9131", LIVE_RELEASED_REFERENCE)),
            "committed")
        self.assertTrue(tp._status_is_writer_committed(
            LIVE_RELEASED_REFERENCE))

    def test_writer_chain_mirror_still_pinned_to_task_row_update(self):
        """The FIX-393 sync guards must stay green next to the new face."""
        self.assertEqual(
            [(n, p.pattern) for n, p in tp._WRITER_STATE_MARKER_CHAIN],
            [(n, p.pattern) for n, p in tru._STATE_MARKER_CHAIN])
        self.assertIs(vw._WRITER_STATE_MARKER_CHAIN,
                      tru._STATE_MARKER_CHAIN)


if __name__ == "__main__":
    unittest.main()
