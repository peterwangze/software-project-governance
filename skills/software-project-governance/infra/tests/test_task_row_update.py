"""Tests for infra/task_row_update.py — the governed task-row writer CLI.

Batch-1 ticket 1 (FEAT-051) guard suite.  Covers the DoD nine (evolution
§4): pre-write validation, the idempotency/conflict protocol (replay vs
same-id-different-payload), reliable persistence (atomic replace, UTF-8 no
BOM, LF/CRLF preservation), write-after re-read via the same parsing schema,
dry-run + structured result codes, the crash-point recovery path (temp
cleanup, effect-first window), negative-control guard tests (ambiguous
anchor / missing row / GBK-Chinese fidelity / special characters / repeated
execution / concurrency / legacy unknown-state rows), progressive rollout
(--dry-run + --inspect) and machine provenance marking.

Red-trio required by the ticket acceptance (each asserts the refusal, never
a silent pass):
  * illegal transition refused           → test_illegal_transition_refused
  * CAS conflict returns observed_revision
        → test_state_cas_conflict_reports_observed_revision
        → test_content_cas_conflict_reports_observed_revision
  * same-operation replay is idempotent  → test_same_operation_id_replays

Concurrency proof follows the threading CAS precedent
(test_loop_paro_engine.py §9, LOAD-BEARING): N threads, one barrier, exactly
one winner, no lost update.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_task_row_update.py -v
"""

import contextlib
import importlib
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import contracts  # noqa: E402  (L0, consumed read-only)
import task_row_update as tru  # noqa: E402

OP_A = "op-" + "a" * 32
OP_B = "op-" + "b" * 32

# A realistic row-shape sample mirroring the live tracker's task table
# (multi-column, narrative cells, Chinese text, evidence ids, machine words
# like "review" inside narrative cells that must NOT impersonate a state).
_ROW_FEAT049 = (
    "| **P1** | FEAT-049 | **批 0 / M0 契约冻结与验收基座**（扩展 contracts "
    "五面契约〔operation_id/状态迁移含 UNKNOWN 与 NOT_EVALUABLE/错误码/schema "
    "版本/写入器最小 I/O〕+ fixtures + 契约测试；review 链双审 APPROVED） | "
    "TRIAGE-FEAT-049（机录 2026-09-19）；REL-082；DEC-221 | 0.86.0 | 产品代码"
    "（Governance Developer → Code Reviewer）。验收 = 契约测试通过冻结 "
    "revision + 零回归 + 零注入面 | ✅ 完成 (2026-09-19)——EVD-1105"
    "（commit 27eeea0）；REVIEW-FEAT-049-R0 = APPROVED_WITH_NOTES/0；"
    "revision m0-r1 冻结；批 1 解锁 |")

_ROW_FEAT051_DEV = (
    "| **P1** | FEAT-051 | **批 1 票 1：task-row-update 写入器 CLI**（B-1 根"
    "——7 次手工行编辑事故的终结面；消费 contracts m0-r1 只读） | "
    "TRIAGE-FEAT-051（机录 2026-09-19）；REL-082；FEAT-049 | 0.86.0 | 产品"
    "代码（Governance Developer → Code Reviewer）。验收 = 新测试全绿 + "
    "verify 全量 PASSED + archguard R1~R7 PASS | 🔄 M-0 ✅ (2026-09-19)"
    "——双半面产出 + R0 定向复审通过；批 1 启动 |")

_ROW_REL081 = (
    "| **P1** | REL-081 | **0.85.0 版本规划与发布**（DEC-215② 授权——M-0 规划"
    "：Release 半面 + Analyst 半面；候选池 8 项两批制提案） | DEC-215②；"
    "RISK-054~058 | 0.85.0 | 版本规划/任务排布（Release + Analyst → 双审 → "
    "用户 M-0 裁定）。验收 = 双审 APPROVED + 用户裁定 semver/范围 | "
    "🔄 M-0 ✅ (2026-09-19)——双半面产出 + R1 双 APPROVED_WITH_NOTES/0 机录；"
    "批 1 执行中 |")

_HEADER = "| 优先级 | ID | 描述 | 依据 | 版本 | 执行面与验收 | 状态 |"
_SEPARATOR = "| --- | --- | --- | --- | --- | --- | --- |"


def _table(*rows, eol="\n"):
    """A minimal-but-realistic tracker-shaped table (every line ends in
    the caller's line ending)."""
    body = eol.join([_HEADER, _SEPARATOR] + list(rows))
    return body + eol


class _WriterFixture(unittest.TestCase):
    """Shared fixture: a temp governed table + CLI/library invocation helpers."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="tru_"))
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

    def run_cli(self, *args):
        """Run the CLI handler, capturing (exit_code, parsed JSON payload)."""
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = tru.main(list(args))
        raw = buffer.getvalue().strip()
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = None
        return code, payload, raw

    def flip(self, *, op=OP_A, task="FEAT-051", frm="dev", to="review",
             revision=None, target=None, ledger=None, reason="review round",
             refs=()):
        """Library-entry flip used by focused tests."""
        return tru.execute_update(
            target=target or self.target,
            task_id=task,
            from_state=frm,
            to_state=to,
            reason=reason,
            evidence_refs=refs,
            operation_id=op,
            expected_revision=revision,
            ledger=ledger or self.ledger,
        )


class BaselineTests(_WriterFixture):
    """Happy path + receipt/ledger/provenance contracts."""

    def test_legal_flip_end_to_end(self):
        self.write_table(_table(_ROW_FEAT049, _ROW_FEAT051_DEV))
        result = self.flip()
        self.assertEqual(result.code, "ok", result.detail)
        self.assertEqual(result.execution, "succeeded")
        self.assertIsInstance(result.new_revision, int)
        text = self.target.read_text(encoding="utf-8")
        status_cell = text.splitlines()[3].split("|")[-2]  # last non-empty cell
        self.assertIn("review", status_cell)
        # The flip is anchored to the ONE row; the untouched row is intact.
        self.assertIn("✅ 完成", text)
        # Machine provenance on the written line's face (DoD 9).
        self.assertIn("〔" + OP_A + "〕", text)
        # Receipt landed in the ledger (structural-join anchor).
        receipts = tru._read_receipts(self.ledger)
        self.assertEqual(len(receipts), 1)
        # Write-after self-check already ran inside execute; assert again
        # through the SAME parsing schema (never a second definition).
        _, row = tru.locate_task_row(text, "FEAT-051")
        self.assertEqual(tru.detect_row_state(row), "review")

    def test_receipt_join_anchor_fields(self):
        """The receipt carries every field the batch-2.3 join needs."""
        self.write_table(_table(_ROW_FEAT051_DEV))
        result = self.flip(
            refs=(contracts.EvidenceRef(kind="repo_file", value="docs/x.md"),))
        self.assertEqual(result.code, "ok")
        (receipt,) = tru._read_receipts(self.ledger)
        for key in ("record_kind", "schema_version", "writer",
                    "operation_id", "task_id", "from_state", "to_state",
                    "reason", "timestamp", "target_file", "revision_before",
                    "revision_after", "row_before_sha256",
                    "row_after_sha256", "input_fingerprint", "evidence_refs",
                    "enforcement"):
            self.assertIn(key, receipt, "receipt missing join field " + key)
        self.assertEqual(receipt["record_kind"], "task_row_update")
        self.assertEqual(receipt["task_id"], "FEAT-051")
        self.assertEqual(receipt["from_state"], "dev")
        self.assertEqual(receipt["to_state"], "review")
        self.assertEqual(receipt["enforcement"], "WARN")
        self.assertEqual(receipt["evidence_refs"],
                         [{"kind": "repo_file", "value": "docs/x.md",
                           "validation": None}])
        self.assertNotEqual(receipt["revision_before"],
                            receipt["revision_after"])
        self.assertNotEqual(receipt["row_before_sha256"],
                            receipt["row_after_sha256"])

    def test_status_cell_only_detection_ignores_narrative(self):
        """Narrative words (review/committed/BLOCKED) in earlier cells never
        impersonate a state — detection scans the status cell only."""
        row = ("| **P2** | FIX-001 | review committed BLOCKED narrative "
               "cell（含 review、committed、BLOCKED 词样的叙述 cell） | refs "
               "review | 0.86.0 | 执行面 review | 🔄 进行中——正常推进 |")
        self.assertEqual(tru.detect_row_state(row), "dev")
        self.write_table(_table(row))
        result = self.flip(task="FIX-001")
        self.assertEqual(result.code, "ok", result.detail)
        _, flipped = tru.locate_task_row(
            self.target.read_text(encoding="utf-8"), "FIX-001")
        self.assertEqual(tru.detect_row_state(flipped), "review")

    def test_wordform_vocabulary_matches_live_table(self):
        """The ordered marker chain reads the live word-forms: the compound
        '🔄 M-0 ✅' row is dev (not completed); '✅ 完成 …' is completed."""
        self.assertEqual(tru.detect_row_state(_ROW_FEAT051_DEV), "dev")
        self.assertEqual(tru.detect_row_state(_ROW_FEAT049), "completed")

    def test_composition_root_assembly_and_r2_cleanliness(self):
        """The dotted path a composition root declares ('task_row_update.main',
        the governance_cost/bootstrap_aggregate pattern) resolves on demand,
        and the module adds zero reverse dependencies (ArchGuard R2)."""
        module = importlib.import_module("task_row_update")
        module_part, _, attr = "task_row_update.main".rpartition(".")
        handler = getattr(importlib.import_module(module_part), attr)
        self.assertTrue(callable(handler))
        source = (_INFRA_DIR / "task_row_update.py").read_text(
            encoding="utf-8")
        self.assertNotIn("import verify_workflow", source)
        self.assertNotIn("from verify_workflow", source)
        self.assertNotIn("_vw()", source)

    def test_contract_objects_are_consumed_read_only(self):
        """Executing a flip must not mutate the frozen m0-r1 contract."""
        states_before = contracts.TASK_STATES
        transitions_before = contracts.TASK_TRANSITIONS
        dispositions_before = contracts.ERROR_CODE_DISPOSITIONS
        self.write_table(_table(_ROW_FEAT051_DEV))
        self.flip()
        self.assertIs(contracts.TASK_STATES, states_before)
        self.assertIs(contracts.TASK_TRANSITIONS, transitions_before)
        self.assertIs(contracts.ERROR_CODE_DISPOSITIONS, dispositions_before)
        self.assertEqual(
            contracts.TASK_TRANSITIONS["dev"], ("review", "blocked"))


class RedTrioTests(_WriterFixture):
    """The acceptance red-trio: each refusal is loud and structured."""

    def test_illegal_transition_refused(self):
        self.write_table(_table(_ROW_FEAT049))
        result = self.flip(task="FEAT-049", frm="completed", to="review")
        self.assertEqual(result.code, "illegal_transition")
        self.assertEqual(
            contracts.ERROR_CODE_DISPOSITIONS[result.code], "validation")
        self.assertIsNone(result.execution)
        self.assertIsNone(result.new_revision)
        # Nothing was written, no receipt exists.
        self.assertIn("✅ 完成", self.target.read_text(encoding="utf-8"))
        self.assertFalse(self.ledger.exists())

    def test_state_cas_conflict_reports_observed_revision(self):
        self.write_table(_table(_ROW_FEAT051_DEV))
        stale_expectation = tru.revision_of(
            self.target.read_text(encoding="utf-8"))
        result = self.flip(frm="review", to="approved",
                           revision=stale_expectation)
        self.assertEqual(result.code, "revision_conflict")
        self.assertEqual(
            contracts.ERROR_CODE_DISPOSITIONS[result.code], "conflict")
        self.assertIsNotNone(result.observed_revision)
        self.assertEqual(result.observed_revision, stale_expectation)
        self.assertIsNone(result.execution)
        self.assertFalse(self.ledger.exists())

    def test_content_cas_conflict_reports_observed_revision(self):
        self.write_table(_table(_ROW_FEAT051_DEV))
        before = tru.revision_of(self.target.read_text(encoding="utf-8"))
        self.flip()  # world moves: dev -> review
        after = tru.revision_of(self.target.read_text(encoding="utf-8"))
        self.assertNotEqual(before, after)
        # A stale caller (expected_revision = before, NEW operation id) must
        # be refused with the freshly observed revision, never auto-rebased.
        result = self.flip(op=OP_B, frm="review", to="approved",
                           revision=before)
        self.assertEqual(result.code, "revision_conflict")
        self.assertEqual(result.observed_revision, after)
        self.assertIn("never auto-rebases", result.detail)

    def test_same_operation_id_replays_idempotently(self):
        self.write_table(_table(_ROW_FEAT051_DEV))
        first = self.flip()
        self.assertEqual(first.code, "ok")
        text_after_first = self.target.read_text(encoding="utf-8")
        ledger_bytes_after_first = self.ledger.read_bytes()

        second = self.flip()  # SAME op id, SAME payload — a retry

        self.assertEqual(second.code, "ok")
        self.assertEqual(second.new_revision, first.new_revision)
        self.assertIn("replay of operation", second.detail)
        # The world was not touched a second time.
        self.assertEqual(self.target.read_text(encoding="utf-8"),
                         text_after_first)
        self.assertEqual(self.ledger.read_bytes(), ledger_bytes_after_first)

    def test_same_operation_id_different_payload_conflicts(self):
        self.write_table(_table(_ROW_FEAT051_DEV))
        self.flip(reason="original intent")
        result = self.flip(reason="a DIFFERENT intent, same id")
        self.assertEqual(result.code, "operation_id_conflict")
        self.assertEqual(
            contracts.ERROR_CODE_DISPOSITIONS[result.code], "conflict")
        self.assertIsNotNone(result.observed_revision)
        self.assertIn("mint a new operation id", result.detail)
        # Exactly one receipt stands; the refused payload wrote nothing.
        self.assertEqual(len(tru._read_receipts(self.ledger)), 1)

    def test_repeat_execution_with_new_op_refuses(self):
        """Repeating the flip under a NEW operation id hits the state-level
        CAS (the row is already at the target): refused, zero second write,
        the effect-first window is disclosed, never silently re-executed."""
        self.write_table(_table(_ROW_FEAT051_DEV))
        first = self.flip(op=OP_A)
        self.assertEqual(first.code, "ok")
        text_after_first = self.target.read_text(encoding="utf-8")
        second = self.flip(op=OP_B)
        self.assertEqual(second.code, "revision_conflict")
        self.assertIn("effect_present_without_receipt", second.detail)
        self.assertEqual(self.target.read_text(encoding="utf-8"),
                         text_after_first)
        self.assertEqual(len(tru._read_receipts(self.ledger)), 1)


class AnchorAndSchemaTests(_WriterFixture):
    """B-1 anchoring discipline + record-family schema guard rails."""

    def test_ambiguous_anchor_refused(self):
        """Two rows carrying the same task id → the writer refuses to guess
        (the hand-edit incident made mechanical)."""
        duplicate = _ROW_FEAT051_DEV.replace(
            "🔄 M-0 ✅", "🔄 进行中")  # both rows detect as dev
        self.write_table(_table(duplicate, _ROW_FEAT051_DEV))
        result = self.flip()
        self.assertEqual(result.code, "cross_record_violation")
        self.assertIn("ambiguous anchor", result.detail)
        self.assertIn("refusing to guess", result.detail)
        self.assertFalse(self.ledger.exists())

    def test_missing_task_row_refused(self):
        self.write_table(_table(_ROW_FEAT049))
        result = self.flip(task="FEAT-999")
        self.assertEqual(result.code, "cross_record_violation")
        self.assertIn("no task row anchored", result.detail)

    def test_word_boundary_anchoring(self):
        """FEAT-051 must not anchor FEAT-0512 / FEAT-051a rows."""
        sibling = _ROW_FEAT051_DEV.replace("FEAT-051 ", "FEAT-0512 ")
        self.write_table(_table(sibling))
        result = self.flip(task="FEAT-051")
        self.assertEqual(result.code, "cross_record_violation")

    def test_legacy_unknown_state_row_refused(self):
        """A legacy/free-form status cell matches nothing → fail-closed
        schema refusal with manual-triage guidance (never a guessed flip)."""
        legacy = _ROW_FEAT051_DEV.replace("🔄 M-0 ✅ (2026-09-19)——双半面产出 "
                                          "+ R0 定向复审通过；批 1 启动",
                                          "hand-edited 状态不明")
        self.write_table(_table(legacy))
        result = self.flip()
        self.assertEqual(result.code, "schema_violation")
        self.assertIn("manual triage", result.detail)
        self.assertFalse(self.ledger.exists())

    def test_synonym_form_refuses_ambiguous_splice(self):
        """A residual second word-form (parenthetical echo) makes the
        post-splice re-check ambiguous — the write refuses rather than
        producing a row the next reader cannot parse."""
        echo = _ROW_FEAT051_DEV.replace(
            "🔄 M-0 ✅", "🔄 进行中（备用：进行中）")
        self.write_table(_table(echo))
        result = self.flip()
        self.assertEqual(result.code, "schema_violation")
        self.assertIn("ambiguous splice", result.detail)
        self.assertFalse(self.ledger.exists())

    def test_compound_dev_form_flips_via_anchored_span(self):
        """The live compound word-form ('🔄 M-0 ✅ …', no canonical '🔄 进行中'
        on the row) flips by swapping exactly the matched span."""
        self.write_table(_table(_ROW_FEAT051_DEV))
        result = self.flip()
        self.assertEqual(result.code, "ok", result.detail)
        flipped = tru.locate_task_row(
            self.target.read_text(encoding="utf-8"), "FEAT-051")[1]
        self.assertEqual(tru.detect_row_state(flipped), "review")
        self.assertIn("review M-0 ✅ (2026-09-19)", flipped)

    def test_schema_version_window_refusal(self):
        self.write_table(_table(_ROW_FEAT051_DEV))
        result = tru.execute_update(
            target=self.target, task_id="FEAT-051", from_state="dev",
            to_state="review", reason="future schema", operation_id=OP_A,
            schema_version=2, ledger=self.ledger)
        self.assertEqual(result.code, "schema_version_unsupported")
        self.assertEqual(
            contracts.ERROR_CODE_DISPOSITIONS[result.code], "validation")
        self.assertFalse(self.ledger.exists())
        # And the window itself obeys the contract law (旧 CLI 遇新 schema 拒写).
        self.assertTrue(contracts.SchemaVersionWindow(1, 1).supports(1))
        self.assertFalse(contracts.SchemaVersionWindow(1, 1).supports(2))


class PersistenceTests(_WriterFixture):
    """DoD 3/6/7: byte-faithful persistence + crash-point recovery."""

    def test_chinese_content_byte_fidelity(self):
        """GBK guard: Chinese/full-width content survives byte-for-byte,
        UTF-8 without BOM, untouched lines untouched."""
        original = self.write_table(_table(
            _ROW_FEAT049, _ROW_FEAT051_DEV,
            "| **P3** | FIX-000 | 全角字符「表」·破折号——·箭头→ ·〔锚〕·表情🔄 | "
            "依据 | 0.86.0 | 执行面 | ⛔ BLOCKED——等待凭据修复 |"))
        result = self.flip()
        self.assertEqual(result.code, "ok", result.detail)
        raw = self.target.read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "BOM must not appear")
        reread = raw.decode("utf-8")  # raises on any mojibake-inducing damage
        self.assertIn("全角字符「表」·破折号——·箭头→ ·〔锚〕·表情🔄", reread)
        # Only the targeted row changed: every other line is byte-identical.
        before_lines = original.splitlines()
        after_lines = reread.splitlines()
        self.assertEqual(len(before_lines), len(after_lines))
        for index, (before, after) in enumerate(zip(before_lines, after_lines)):
            if index != 3:  # the FEAT-051 row
                self.assertEqual(before, after,
                                 "line {0} was disturbed".format(index))

    def test_special_characters_in_row_preserved(self):
        """Escaped pipes, backticks, HTML comments and bracket anchors in the
        row survive the flip; only the marker span + op suffix move."""
        row = ("| **P2** | FIX-002 | 含管道转义 `a\\|b` 与 HTML <!-- 注释 --> "
               "与反引号 `code` | refs | 0.86.0 | 执行面 | 🔄 进行中——处理中 |")
        self.write_table(_table(row))
        result = self.flip(task="FIX-002")
        self.assertEqual(result.code, "ok", result.detail)
        flipped = tru.locate_task_row(
            self.target.read_text(encoding="utf-8"), "FIX-002")[1]
        self.assertIn("a\\|b", flipped)
        self.assertIn("<!-- 注释 -->", flipped)
        self.assertIn("`code`", flipped)
        self.assertIn("〔" + OP_A + "〕", flipped)

    def test_crlf_line_endings_preserved(self):
        original = self.write_table(_table(_ROW_FEAT049, _ROW_FEAT051_DEV,
                                           eol="\r\n"))
        self.assertIn("\r\n", original)
        result = self.flip()
        self.assertEqual(result.code, "ok", result.detail)
        raw = self.target.read_bytes()
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""),
                         "a bare LF appeared in a CRLF file")
        self.assertEqual(raw.count(b"\r\n"), original.count("\r\n"))
        self.assertEqual(tru.detect_row_state(
            tru.locate_task_row(
                raw.decode("utf-8"), "FEAT-051")[1]), "review")

    def test_last_line_without_trailing_newline(self):
        self.write_table(_table(_ROW_FEAT049, eol="\n")
                         + _ROW_FEAT051_DEV)  # no trailing newline
        result = self.flip()
        self.assertEqual(result.code, "ok", result.detail)
        raw = self.target.read_text(encoding="utf-8")
        self.assertFalse(raw.endswith("\n"))
        self.assertEqual(tru.detect_row_state(
            tru.locate_task_row(raw, "FEAT-051")[1]), "review")

    def test_crash_point_leaves_no_temp_and_target_untouched(self):
        """Kill at the commit point (before os.replace): the target is
        untouched, the temp is cleaned, the failure is manual-class — the
        no-half-written-target invariant (DoD 6)."""
        self.write_table(_table(_ROW_FEAT051_DEV))
        before_bytes = self.target.read_bytes()
        with mock.patch.object(tru.os, "replace",
                               side_effect=OSError("injected crash")):
            result = self.flip()
        self.assertEqual(result.code, "manual_intervention")
        self.assertIn("target untouched", result.detail)
        self.assertEqual(self.target.read_bytes(), before_bytes)
        leftovers = [p.name for p in self.tmpdir.iterdir()
                     if p.name.endswith(".tmp")]
        self.assertEqual(leftovers, [],
                         "crash left temp debris: {0}".format(leftovers))

    def test_receipt_append_failure_disclosed_not_forged(self):
        """The effect-first window (commit done, receipt lost) is honestly
        reported as manual_intervention — the writer never fabricates its
        own audit trail."""
        self.write_table(_table(_ROW_FEAT051_DEV))
        with mock.patch.object(tru, "_append_receipt",
                               side_effect=OSError("disk full")):
            result = self.flip()
        self.assertEqual(result.code, "manual_intervention")
        self.assertEqual(result.execution, "succeeded")
        # Contract law: an error code never carries new_revision — the
        # committed revision is disclosed in prose for the adjudication.
        self.assertIsNone(result.new_revision)
        self.assertRegex(result.detail, r"revision \d+")
        self.assertIn("effect_present_without_receipt", result.detail)
        # The row IS committed (the effect happened).
        self.assertEqual(tru.detect_row_state(
            tru.locate_task_row(
                self.target.read_text(encoding="utf-8"),
                "FEAT-051")[1]), "review")

    def test_lock_contention_is_retryable_never_unlocked(self):
        """An exhausted lock budget refuses the write as lock_contention —
        this writer never degrades to an unlocked write."""
        self.write_table(_table(_ROW_FEAT051_DEV))
        with mock.patch.object(tru, "_write_lock",
                               side_effect=tru.LockContention("busy")):
            result = self.flip()
        self.assertEqual(result.code, "lock_contention")
        self.assertEqual(
            contracts.ERROR_CODE_DISPOSITIONS[result.code], "retryable")
        self.assertIsNone(result.execution)
        self.assertFalse(self.ledger.exists())


class ConcurrencyTests(_WriterFixture):
    """LOAD-BEARING: the CAS + lock combination under real concurrency
    (threading precedent, test_loop_paro_engine.py §9)."""

    def test_many_threads_one_winner_rest_conflict(self):
        self.write_table(_table(_ROW_FEAT049, _ROW_FEAT051_DEV))
        n = 12
        results = [None] * n
        barrier = threading.Barrier(n)

        def worker(index):
            barrier.wait()  # release all threads simultaneously
            results[index] = self.flip(
                op="op-{0:032x}".format(index), reason="thread-{0}".format(index))

        threads = [threading.Thread(target=worker, args=(i,))
                   for i in range(n)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)

        self.assertEqual(results.count(None), 0,
                         "a thread did not record a result")
        codes = [r.code for r in results]
        winners = [r for r in results if r.code == "ok"]
        losers = [r for r in results if r.code != "ok"]
        self.assertEqual(len(winners), 1,
                         "expected exactly one winner, got codes={0}".format(
                             codes))
        # Every loser is a CONFLICT-class refusal with the observed world —
        # never a silent loss, never a validation-class lie.
        for loser in losers:
            self.assertEqual(loser.code, "revision_conflict", codes)
            self.assertIsNotNone(loser.observed_revision)
        # No lost update / no double flip: the row is exactly at the target,
        # and the ledger carries exactly the winner's receipt.
        text = self.target.read_text(encoding="utf-8")
        _, row = tru.locate_task_row(text, "FEAT-051")
        self.assertEqual(tru.detect_row_state(row), "review")
        receipts = tru._read_receipts(self.ledger)
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["operation_id"], winners[0].operation_id)
        # The winner's new_revision matches a fresh observation of the file.
        self.assertEqual(winners[0].new_revision, tru.revision_of(text))


class ReviewR1FixTests(_WriterFixture):
    """review-FEAT-051-CODE-R0 fixes: P1-1 byte-minimal flip, P2-1 malformed
    operation id, P2-2 degenerate receipt, P2-3 in-lock replay adjudication."""

    def test_flip_row_minimal_byte_diff(self):
        """P1-1 negative control: a flip must not disturb any byte outside
        the state word-form span + the appended op suffix — cell padding
        whitespace included.  The pre-fix build stripped the status cell and
        silently swallowed the padding (full-width U+3000 is Unicode
        whitespace, so ``strip()`` ate it), violating the byte-for-byte
        invariant and DoD 3."""
        row = ("| **P2** | FIX-003 | 描述 cell | refs | 0.86.0 | 执行面 |"
               "  \u3000✅ 完成 (2026-09-19)——EVD 记录 \u3000 |")
        self.write_table(_table(row))
        result = self.flip(task="FIX-003", frm="completed", to="committed",
                           op=OP_A)
        self.assertEqual(result.code, "ok", result.detail)
        flipped = tru.locate_task_row(
            self.target.read_text(encoding="utf-8"), "FIX-003")[1]
        expected = ("| **P2** | FIX-003 | 描述 cell | refs | 0.86.0 | 执行面 |"
                    "  \u3000committed (2026-09-19)——EVD 记录 〔" + OP_A
                    + "〕 \u3000 |")
        self.assertEqual(flipped, expected,
                         "flip disturbed bytes outside the state span")

    def test_malformed_operation_id_structured_refusal(self):
        """P2-1: a malformed --operation-id is a structured schema refusal
        (exit 3), never an uncaught ContractViolation traceback."""
        self.write_table(_table(_ROW_FEAT051_DEV))
        code, payload, _raw = self.run_cli(
            "--task", "FEAT-051", "--from", "dev", "--to", "review",
            "--reason", "bad id", "--file", str(self.target),
            "--operation-id", "not-an-op-id")
        self.assertEqual(code, tru.ExitCode.VALIDATION)
        self.assertEqual(payload["result"]["code"], "schema_violation")
        self.assertIn("operation id", payload["result"]["detail"])
        self.assertFalse(self.ledger.exists())
        # Library entry obeys the same pre-check.
        result = tru.execute_update(
            target=self.target, task_id="FEAT-051", from_state="dev",
            to_state="review", reason="bad id", operation_id="BOGUS",
            ledger=self.ledger)
        self.assertEqual(result.code, "schema_violation")
        self.assertIsNone(result.execution)

    def test_degenerate_receipt_replay_refuses_manually(self):
        """P2-2: a stored receipt whose writer_result face is missing or
        malformed must NOT crash replay reconstruction with an uncaught
        ContractViolation — it degrades to manual_intervention (adjudicate
        the ledger) and writes nothing."""
        self.write_table(_table(_ROW_FEAT051_DEV))
        first = self.flip()
        self.assertEqual(first.code, "ok")
        # Corrupt the stored receipt's writer_result face on disk.
        receipts = tru._read_receipts(self.ledger)
        self.assertEqual(len(receipts), 1)
        receipts[0].pop("writer_result")
        lines = [json.dumps(r, ensure_ascii=False, sort_keys=True)
                 for r in receipts]
        self.ledger.write_text("\n".join(lines) + "\n",
                               encoding="utf-8", newline="")
        text_after_first = self.target.read_text(encoding="utf-8")
        result = self.flip()  # same op id, same payload → replay path
        self.assertEqual(result.code, "manual_intervention")
        self.assertIsNone(result.execution)
        self.assertIn("degenerate", result.detail)
        self.assertIn("adjudicate", result.detail)
        self.assertEqual(self.target.read_text(encoding="utf-8"),
                         text_after_first)

    def test_concurrent_same_operation_id_single_execute_rest_replay(self):
        """P2-3: replay adjudication happens UNDER the lock, so N threads
        retrying the SAME operation produce exactly one execute and N-1
        replays of the original result — never a misleading
        effect_present_without_receipt conflict for a receipt that is in
        fact on record."""
        self.write_table(_table(_ROW_FEAT049, _ROW_FEAT051_DEV))
        n = 8
        results = [None] * n
        barrier = threading.Barrier(n)

        def worker(index):
            barrier.wait()
            results[index] = self.flip(op=OP_A, reason="same-op thread")

        threads = [threading.Thread(target=worker, args=(i,))
                   for i in range(n)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)

        self.assertEqual(results.count(None), 0,
                         "a thread did not record a result")
        codes = [r.code for r in results]
        self.assertEqual(codes.count("ok"), n,
                         "every same-op retry must resolve to ok "
                         "(one execute + replays), got {0}".format(codes))
        # Exactly one receipt stands; the flip happened exactly once.
        receipts = tru._read_receipts(self.ledger)
        self.assertEqual(len(receipts), 1)
        replays = [r for r in results
                   if "replay of operation" in (r.detail or "")]
        self.assertGreaterEqual(len(replays), n - 1,
                                "losers must replay, not conflict")
        for direct in (r for r in results
                       if "replay of operation" not in (r.detail or "")):
            self.assertEqual(
                direct.new_revision,
                tru.revision_of(self.target.read_text(encoding="utf-8")))


class CliSurfaceTests(_WriterFixture):
    """Progressive rollout + structured result codes + typed refs."""

    def test_dry_run_performs_zero_writes(self):
        """The acceptance demo path: --dry-run parses the REAL table shape
        and previews the flip with zero bytes written, zero locks taken."""
        self.write_table(_table(_ROW_FEAT049, _ROW_FEAT051_DEV))
        before = self.target.read_bytes()
        code, payload, _raw = self.run_cli(
            "--task", "FEAT-051", "--from", "dev", "--to", "review",
            "--reason", "dry-run rehearsal", "--file", str(self.target),
            "--dry-run")
        self.assertEqual(code, tru.ExitCode.OK)
        self.assertTrue(payload["would_execute"])
        self.assertEqual(payload["writes_performed"], 0)
        self.assertFalse(payload["lock_acquired"])
        self.assertEqual(payload["preview"]["row_before"], _ROW_FEAT051_DEV)
        self.assertIn("review", payload["preview"]["row_after"])
        self.assertIn("〔" + payload["preview_result"]["operation_id"] + "〕",
                      payload["preview"]["row_after"])
        self.assertEqual(payload["preview_result"]["code"], "ok")
        self.assertTrue(payload["preview_result"]["dry_run"])
        self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse(self.ledger.exists())

    def test_dry_run_refusal_exit_codes(self):
        self.write_table(_table(_ROW_FEAT049))
        code, payload, _raw = self.run_cli(
            "--task", "FEAT-049", "--from", "completed", "--to", "review",
            "--reason", "illegal", "--file", str(self.target), "--dry-run")
        self.assertEqual(code, tru.ExitCode.VALIDATION)
        self.assertFalse(payload["would_execute"])
        self.assertEqual(payload["refusal"]["code"], "illegal_transition")

    def test_inspect_is_the_cas_expectation_source(self):
        self.write_table(_table(_ROW_FEAT051_DEV))
        code, payload, _raw = self.run_cli(
            "--task", "FEAT-051", "--inspect", "--file", str(self.target))
        self.assertEqual(code, tru.ExitCode.OK)
        self.assertTrue(payload["found"])
        self.assertEqual(payload["state"], "dev")
        expected = payload["observed_revision"]
        self.assertEqual(expected, tru.revision_of(
            self.target.read_text(encoding="utf-8")))
        # The observed revision is accepted by the content CAS on execute.
        result = self.flip(revision=expected)
        self.assertEqual(result.code, "ok", result.detail)

    def test_inspect_missing_task_is_validation_exit(self):
        self.write_table(_table(_ROW_FEAT051_DEV))
        code, payload, _raw = self.run_cli(
            "--task", "FEAT-999", "--inspect", "--file", str(self.target))
        self.assertEqual(code, tru.ExitCode.VALIDATION)
        self.assertFalse(payload["found"])

    def test_refs_typed_rehydration_and_rejection(self):
        """CLI 'kind=value' strings rehydrate into typed EvidenceRefs; an
        unknown kind fails closed as a schema violation (FEAT-049 writer
        responsibility: explicitly typed references)."""
        self.write_table(_table(_ROW_FEAT051_DEV))
        code, _payload, _raw = self.run_cli(
            "--task", "FEAT-051", "--from", "dev", "--to", "review",
            "--reason", "typed refs", "--file", str(self.target),
            "--refs", "repo_file=docs/planning/version-plan-0.86.0.md",
            "--refs", "governance_id=DEC-221")
        self.assertEqual(code, tru.ExitCode.OK)
        receipts = tru._read_receipts(self.ledger)
        kinds = [r["kind"] for r in receipts[0]["evidence_refs"]]
        self.assertEqual(kinds, ["repo_file", "governance_id"])

        code, payload, _raw = self.run_cli(
            "--task", "FEAT-051", "--from", "review", "--to", "approved",
            "--reason", "bad kind", "--file", str(self.target),
            "--refs", "not_a_kind=value")
        self.assertEqual(code, tru.ExitCode.VALIDATION)
        self.assertEqual(payload["result"]["code"], "schema_violation")

    def test_structured_exit_codes_match_dispositions(self):
        self.write_table(_table(_ROW_FEAT049, _ROW_FEAT051_DEV))
        # validation → 3
        code, payload, _raw = self.run_cli(
            "--task", "FEAT-049", "--from", "completed", "--to", "review",
            "--reason", "illegal", "--file", str(self.target))
        self.assertEqual(code, 3)
        self.assertEqual(payload["result"]["code"], "illegal_transition")
        # conflict → 4
        code, payload, _raw = self.run_cli(
            "--task", "FEAT-049", "--from", "dev", "--to", "review",
            "--reason", "wrong row state", "--file", str(self.target))
        self.assertEqual(code, 4)
        self.assertEqual(payload["result"]["code"], "revision_conflict")
        self.assertIsNotNone(payload["result"]["observed_revision"])
        # retryable → 5 (lock budget exhausted)
        with mock.patch.object(tru, "_write_lock",
                               side_effect=tru.LockContention("busy")):
            code, payload, _raw = self.run_cli(
                "--task", "FEAT-051", "--from", "dev", "--to", "review",
                "--reason", "busy", "--file", str(self.target))
        self.assertEqual(code, 5)
        self.assertEqual(payload["result"]["code"], "lock_contention")
        # success → 0
        code, payload, _raw = self.run_cli(
            "--task", "FEAT-051", "--from", "dev", "--to", "review",
            "--reason", "ship it", "--file", str(self.target))
        self.assertEqual(code, 0)
        self.assertEqual(payload["result"]["code"], "ok")

    def test_operation_id_minted_and_reusable_via_cli(self):
        self.write_table(_table(_ROW_FEAT051_DEV))
        code, first, _raw = self.run_cli(
            "--task", "FEAT-051", "--from", "dev", "--to", "review",
            "--reason", "mint", "--file", str(self.target))
        minted = first["result"]["operation_id"]
        self.assertRegex(minted, contracts.OPERATION_ID_PATTERN)
        # Retrying with the SAME minted id replays (exit 0, same revision).
        code, second, _raw = self.run_cli(
            "--task", "FEAT-051", "--from", "dev", "--to", "review",
            "--reason", "mint", "--file", str(self.target),
            "--operation-id", minted)
        self.assertEqual(code, 0)
        self.assertEqual(second["result"]["new_revision"],
                         first["result"]["new_revision"])
        self.assertIn("replay", second["result"]["detail"])

    def test_default_file_is_the_tracker_path(self):
        """Omitted --file targets the conventional tracker path relative to
        cwd (progressive rollout default); a missing file is a validation
        refusal, never a creation."""
        cwd = os.getcwd()
        os.chdir(self.tmpdir)
        try:
            code, payload, _raw = self.run_cli(
                "--task", "FEAT-051", "--from", "dev", "--to", "review",
                "--reason", "default path probe")
            self.assertEqual(code, tru.ExitCode.VALIDATION)
            self.assertEqual(payload["result"]["code"],
                             "cross_record_violation")
            self.assertIn("plan-tracker.md", payload["result"]["detail"])
        finally:
            os.chdir(cwd)

    def test_gbk_console_output_guard(self):
        """FIX-278's write-side sibling: a legacy-codepage console (GBK)
        must not crash the writer — the state markers (✅/🔄/⛔) are not
        GBK-encodable, so the writer reconfigures stdout to UTF-8 first.
        Found during the real-tracker dry-run acceptance demo."""
        raw_stream = io.BytesIO()
        gbk_stdout = io.TextIOWrapper(raw_stream, encoding="gbk",
                                      errors="strict")
        self.write_table(_table(_ROW_FEAT051_DEV))
        with mock.patch.object(tru.sys, "stdout", gbk_stdout):
            code = tru.main(["--task", "FEAT-051", "--from", "dev",
                             "--to", "review", "--reason", "gbk console",
                             "--file", str(self.target), "--dry-run"])
        gbk_stdout.flush()
        self.assertEqual(code, tru.ExitCode.OK)
        # The reconfigured stream emitted UTF-8 the machine can parse.
        payload = json.loads(raw_stream.getvalue().decode("utf-8"))
        self.assertTrue(payload["would_execute"])
        self.assertIn("review", payload["preview"]["row_after"])


class EngineDispatchFaceTests(_WriterFixture):
    """FEAT-055 (batch-2.0 wiring): the engine dispatch face consumes an
    engine-built Namespace directly — the same executor ``main`` runs, no
    Namespace→argv round-trip (FEAT-047 P2-1 caliber)."""

    def _engine_args(self, *extra):
        argv = ["--task", "FEAT-051", "--from", "dev", "--to", "review",
                "--reason", "engine dispatch", "--file", str(self.target)]
        return tru._build_parser().parse_args(list(argv) + list(extra))

    def test_cmd_handler_consumes_namespace_and_flips(self):
        self.write_table(_table(_ROW_FEAT049, _ROW_FEAT051_DEV))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = tru.cmd_task_row_update(self._engine_args())
        payload = json.loads(buffer.getvalue().strip())
        self.assertEqual(code, tru.ExitCode.OK)
        self.assertEqual(payload["result"]["code"], "ok")

    def test_cmd_handler_missing_triple_uses_usage_refusal(self):
        """An engine Namespace without --from/--to/--reason and without
        --inspect/--dry-run (e.g. a caller that only anchored --task) hits
        the identical usage-level refusal: exit 2 with the argparse usage
        text, exactly like the self-contained CLI."""
        self.write_table(_table(_ROW_FEAT051_DEV))
        args = tru._build_parser().parse_args(
            ["--task", "FEAT-051", "--file", str(self.target)])
        stderr = io.StringIO()
        with mock.patch.object(tru.sys, "stderr", stderr):
            with self.assertRaises(SystemExit) as caught:
                tru.cmd_task_row_update(args)
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("are required for --dry-run/execute",
                      stderr.getvalue())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
