"""Regression tests for decision archival attribution — FIX-312.

Bug (R2 F-R2-01 family, live 2026-09-16): ``_entry_version_for_archive``
attributed a decision row to the FIRST referenced task found in
``task_versions`` via a WHOLE-LINE scan. A NEW decision that merely
REFERENCED a historical archived task was therefore attributed to that old
version and migrated out of the hot decision-log while the tasks it actually
governed were still active. Live case: DEC-187 (2026-09-12,
关联任务 = ``FIX-310, RISK-050, FEAT-010, FIX-307, FIX-308, FIX-309``) — at
mis-archive time only FEAT-010 (v0.77.0) was archived while FIX-310/307/308/
309 were hot — so the whole-line first-hit picked FEAT-010@v0.77.0 and the
row was archived into the v0.1.0-0.78.1 range (DEC-188 records the restore:
「本行 2026-09-12 于归档迁移中被误归档…已回迁热文件」).

Fix semantics (FIX-312):
  1. governing refs come ONLY from the 关联任务 (related tasks) column —
     prose mentions in 背景/决策内容 are context, not governing refs;
  2. a decision migrates ONLY when EVERY task-family ref in that column is
     archived (no active/unarchived governing ref);
  3. the attributed version is the NEWEST archived governing version (max,
     not first-hit);
  4. anything unprovable (no related column, too-short row, no task-family
     refs) stays hot — conservative fail-closed.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))


# Canonical decision-log header (11 columns, mirrors the live file).
_DECISION_HEADER = (
    "| 编号 | 日期 | 主题 | 背景 | 决策内容 | 备选方案 | 选择原因 "
    "| 影响范围 | 决策人 | 关联任务 | 后续动作 |"
)
_DECISION_SEPARATOR = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"


def _dec_row(dec_id, date, subject, background, related, followup="—"):
    """One canonical-shape decision row (11 data cells)."""
    return (
        f"| {dec_id} | {date} | {subject} | {background} | 决策内容 | 备选 "
        f"| 原因 | 影响 | 用户 + Coordinator | {related} | {followup} |"
    )


# The live DEC-187 governing shape (trimmed cells, REAL related column and
# REAL prose-reference structure): the 背景 cell mentions FIX-310/FEAT-010,
# the related column lists the governing tasks incl. cross-entity RISK-050.
_DEC187_ROW = _dec_row(
    "DEC-187", "2026-09-12",
    "**架构不变量 I-1/I-2/I-3**（用户裁定；FIX-310 原设计作废）",
    "用户连续两问暴露 FIX-310 的整个设计建立在一条虚构需求上——该需求系 "
    "FEAT-010 引入、FIX-307 加固的自我施加约束。",
    "FIX-310, RISK-050, FEAT-010, FIX-307, FIX-308, FIX-309",
    "FIX-310 按零侵入重做设计；【2026-09-12 DEC-188 澄清】")


class DecisionAttributionTests(unittest.TestCase):
    """_migrate_decisions FIX-312 attribution semantics (tmp gov dirs)."""

    def setUp(self):
        import archive  # noqa: F401  (module-level sys.path injection applies)
        self.archive = archive
        self.tempdir = tempfile.TemporaryDirectory(prefix="spg-fix312-")
        self.root = Path(self.tempdir.name)
        self.gov = self.root / ".governance"
        self.gov.mkdir(parents=True, exist_ok=True)
        self.addCleanup(self.tempdir.cleanup)

    def _write_decision_log(self, rows, header=True):
        lines = ["# 决策记录", ""]
        if header:
            lines += [_DECISION_HEADER, _DECISION_SEPARATOR]
        lines += rows
        (self.gov / "decision-log.md").write_text(
            "\n".join(lines) + "\n", encoding="utf-8")

    def _migrate(self, task_versions, dry_run=False, explain_out=None):
        with patch.object(self.archive, "ROOT", self.root), \
                patch.object(self.archive, "PLUGIN_ROOT", self.root):
            return self.archive._migrate_decisions(
                "0.1.0", "0.80.0", task_versions,
                dry_run=dry_run, explain_out=explain_out)

    # ── THE regression: new decision referencing an archived task ─────────

    def test_new_decision_referencing_archived_task_is_retained(self):
        """DEC-187 morning-state (2026-09-16 实证): only FEAT-010@0.77.0 is
        archived; the governing FIX-310/307/308/309 are still hot. The row
        MUST stay hot (pre-fix it was attributed v0.77.0 and migrated)."""
        self._write_decision_log([_DEC187_ROW])
        task_versions = {"FEAT-010": "0.77.0"}
        explain = []
        count = self._migrate(task_versions, explain_out=explain)
        self.assertEqual(count, 0, "new decision referencing an old archived "
                                    "task must NOT migrate")
        kept = (self.gov / "decision-log.md").read_text(encoding="utf-8")
        self.assertIn("DEC-187", kept)
        self.assertFalse(
            (self.gov / "archive" / "decisions").exists(),
            "nothing should be written to the decisions archive")
        reasons = {r["id"]: r["reason"] for r in explain}
        self.assertEqual(reasons.get("DEC-187"), "retained_active_task_ref")

    def test_legacy_whole_line_attribution_is_the_documented_bug(self):
        """Documents the pre-fix mechanism: the legacy whole-line helper DID
        return FEAT-010's v0.77.0 for the DEC-187 row (first archived hit).
        The decision path no longer uses it (kept for the risk path)."""
        task_versions = {"FEAT-010": "0.77.0"}
        with patch.object(self.archive, "ROOT", self.root), \
                patch.object(self.archive, "PLUGIN_ROOT", self.root):
            self.assertEqual(
                self.archive._entry_version_for_archive(
                    _DEC187_ROW, task_versions),
                "0.77.0")

    # ── Closure state: all governing refs archived → migrate at NEWEST ────

    def test_all_governing_refs_archived_migrates_at_newest_version(self):
        """Once EVERY governing task is archived, the decision migrates —
        attributed to the NEWEST archived governing version (0.80.0), not
        the first whole-line hit (0.77.0)."""
        self._write_decision_log([_DEC187_ROW])
        task_versions = {
            "FEAT-010": "0.77.0",
            "FIX-307": "0.80.0", "FIX-308": "0.80.0",
            "FIX-309": "0.80.0", "FIX-310": "0.80.0",
        }
        count = self._migrate(task_versions)
        self.assertEqual(count, 1)
        kept = (self.gov / "decision-log.md").read_text(encoding="utf-8")
        self.assertNotIn("DEC-187", kept)
        archived = (
            self.gov / "archive" / "decisions"
            / "decisions-v0.1.0-0.80.0.md").read_text(encoding="utf-8")
        self.assertIn("## DEC-187:", archived)
        self.assertIn("归档版本: v0.80.0", archived)
        self.assertNotIn("归档版本: v0.77.0", archived)

    # ── Governing refs = 关联任务 column ONLY ─────────────────────────────

    def test_prose_reference_alone_never_migrates(self):
        """A decision whose 背景 mentions an archived task but whose
        关联任务 cell carries no task-family ref stays hot: prose mentions
        are context, not governing refs (the F-R2-01 root cause)."""
        row = _dec_row(
            "DEC-290", "2026-09-16", "新决策",
            "历史背景：承接 FEAT-010 的约束遗产。", "—")
        self._write_decision_log([row])
        explain = []
        count = self._migrate({"FEAT-010": "0.77.0"}, explain_out=explain)
        self.assertEqual(count, 0)
        reasons = {r["id"]: r["reason"] for r in explain}
        self.assertEqual(reasons.get("DEC-290"), "no_task_family_ref")
        self.assertIn("DEC-290",
                      (self.gov / "decision-log.md").read_text(encoding="utf-8"))

    def test_cross_entity_only_related_cell_stays_hot(self):
        row = _dec_row(
            "DEC-291", "2026-09-16", "新决策", "背景",
            "RISK-050, DEC-187, REVIEW-FIX-310")
        self._write_decision_log([row])
        explain = []
        count = self._migrate({"FEAT-010": "0.77.0"}, explain_out=explain)
        self.assertEqual(count, 0)
        reasons = {r["id"]: r["reason"] for r in explain}
        self.assertEqual(reasons.get("DEC-291"), "no_task_family_ref")

    # ── Column detection + structural robustness ──────────────────────────

    def test_headerless_rows_use_canonical_second_to_last_column(self):
        """test_archive.py fixtures write rows WITHOUT a header: the related
        column falls back to the canonical second-to-last cell (关联任务 is
        second-to-last in the 11-col decision schema)."""
        legacy_row = (
            "| DEC-001 | 2026-05-01 | Old decision | ctx | decision | alt "
            "| reason | impact | owner | FIX-084, REL-013 | scope |")
        self._write_decision_log([legacy_row], header=False)
        count = self._migrate(
            {"FIX-084": "0.38.0", "REL-013": "0.38.0"})
        self.assertEqual(count, 1,
                         "legacy fixture shape must still migrate (all refs "
                         "archived)")

    def test_ragged_row_is_reported_unknown_structure(self):
        """A structurally untrusted row (fewer cells than the schema) is
        retained fail-closed and lands in the unknown_structure bucket."""
        ragged = "| DEC-292 | 2026-09-16 | 短行 | 背景 | 决策 |"
        self._write_decision_log([_DEC187_ROW, ragged])
        task_versions = {
            "FEAT-010": "0.77.0", "FIX-307": "0.80.0", "FIX-308": "0.80.0",
            "FIX-309": "0.80.0", "FIX-310": "0.80.0"}
        explain = []
        count = self._migrate(task_versions, dry_run=True, explain_out=explain)
        # Dry-run: DEC-187 would archive (1), DEC-292 is unknown structure.
        self.assertEqual(count, 1)
        stats = self.archive._finalize_explain(explain)
        self.assertEqual(stats["unknown_structure"], 1)
        self.assertIn("DEC-292", stats["unknown_ids"])

    def test_dry_run_reports_would_archive_without_writing(self):
        self._write_decision_log([_DEC187_ROW])
        task_versions = {"FEAT-010": "0.77.0"}
        explain = []
        count = self._migrate(task_versions, dry_run=True, explain_out=explain)
        self.assertEqual(count, 0)
        kept = (self.gov / "decision-log.md").read_text(encoding="utf-8")
        self.assertIn("DEC-187", kept)
        reasons = {r["id"]: r["reason"] for r in explain}
        self.assertEqual(reasons.get("DEC-187"), "retained_active_task_ref")


class RiskPathUnchangedTests(unittest.TestCase):
    """FIX-312 scope guard: the risk path keeps the legacy first-hit helper
    (risks have the _is_risk_closed gate; only the decision attribution was
    re-judged in this fix)."""

    def test_entry_version_helper_still_resolves_first_hit(self):
        import archive
        line = "| RISK-001 | 2026-04-01 | desc | x | 已关闭 | m | d | t | n | FIX-084, REL-013 | — |"
        self.assertEqual(
            archive._entry_version_for_archive(
                line, {"REL-013": "0.38.0", "FIX-084": "0.38.0"}),
            "0.38.0")


class Fix342DefensiveSurfaceTests(unittest.TestCase):
    """FIX-342 — review-FIX-341-312-CODE-R0 defensive-surface gaps.

    P2-2: the headerless fallback trusted ``data_cells[-2]`` for ragged
    4≤cells<11 rows — a title/ctx-cell archived ref could be misread as the
    governing ref (R0 probe: headerless 6-cell row → would_archive). The
    fallback now requires the canonical 11-column schema and fails closed
    (decision_row_too_short) otherwise.

    P3-2: ``_decision_related_column_index`` scanned the WHOLE file, so a
    body narrative table carrying an exact 「关联任务」 cell could shadow the
    real header (live data never triggers — header is at file top). The scan
    is now limited to the header area (before the first separator row).
    """

    def setUp(self):
        import archive  # noqa: F401  (module-level sys.path injection applies)
        self.archive = archive
        self.tempdir = tempfile.TemporaryDirectory(prefix="spg-fix342-")
        self.root = Path(self.tempdir.name)
        self.gov = self.root / ".governance"
        self.gov.mkdir(parents=True, exist_ok=True)
        self.addCleanup(self.tempdir.cleanup)

    def _write_decision_log(self, rows, header=False):
        lines = ["# 决策记录", ""]
        if header:
            lines += [_DECISION_HEADER, _DECISION_SEPARATOR]
        lines += rows
        (self.gov / "decision-log.md").write_text(
            "\n".join(lines) + "\n", encoding="utf-8")

    def _migrate(self, task_versions, dry_run=False, explain_out=None):
        with patch.object(self.archive, "ROOT", self.root), \
                patch.object(self.archive, "PLUGIN_ROOT", self.root):
            return self.archive._migrate_decisions(
                "0.1.0", "0.80.0", task_versions,
                dry_run=dry_run, explain_out=explain_out)

    # ── P2-2: headerless fallback requires the canonical column count ────

    def test_headerless_short_row_fails_closed_too_short(self):
        """R0 P2-2 probe (red→green): a headerless 6-cell row whose 5th cell
        carries an archived task ref must NOT treat that cell as the
        governing 关联任务 column (pre-fix: would_archive v0.77.0)."""
        short = "| DEC-300 | 2026-09-16 | 标题 | 背景 | FIX-084 | 范围 |"
        self._write_decision_log([short])
        explain = []
        count = self._migrate(
            {"FIX-084": "0.77.0"}, dry_run=True, explain_out=explain)
        self.assertEqual(count, 0,
                         "a structurally short headerless row must not "
                         "migrate (fail-closed)")
        reasons = {r["id"]: r["reason"] for r in explain}
        self.assertEqual(reasons.get("DEC-300"), "decision_row_too_short")

    def test_headerless_noncanonical_lengths_fail_closed(self):
        """Boundary: the fallback accepts ONLY the canonical 11 columns —
        4/6/10/12-cell headerless rows are all decision_row_too_short."""
        for cell_count, label in ((4, "min-boundary"), (6, "ragged"),
                                  (10, "one-short"), (12, "one-over")):
            dec_id = "DEC-{0}".format(310 + cell_count)
            parts = ([dec_id, "2026-09-16"]
                     + ["c{0}".format(i) for i in range(3, cell_count + 1)])
            parts[-2] = "FIX-084"  # a wrong fallback would misread this cell
            row = "| " + " | ".join(parts) + " |"
            with self.subTest(cells=cell_count, label=label):
                self._write_decision_log([row])
                explain = []
                count = self._migrate(
                    {"FIX-084": "0.77.0"}, dry_run=True, explain_out=explain)
                self.assertEqual(count, 0)
                reasons = {r["id"]: r["reason"] for r in explain}
                self.assertEqual(
                    reasons.get(dec_id), "decision_row_too_short")

    def test_headerless_canonical_row_still_migrates(self):
        """Zero-flip guard: the canonical 11-column headerless row keeps the
        fallback semantics (mirrors the test_archive.py legacy fixtures)."""
        legacy_row = (
            "| DEC-001 | 2026-05-01 | Old decision | ctx | decision | alt "
            "| reason | impact | owner | FIX-084, REL-013 | scope |")
        self._write_decision_log([legacy_row])
        count = self._migrate(
            {"FIX-084": "0.38.0", "REL-013": "0.38.0"}, dry_run=True)
        self.assertEqual(count, 1, "canonical headerless row must still "
                                   "migrate (all refs archived)")

    # ── P3-2: header-area-limited column scan ────────────────────────────

    def test_body_table_never_answers_when_header_area_has_none(self):
        """R0 P3-2 mechanism (red→green): when the header area declares no
        「关联任务」 cell, a body narrative table carrying one must NOT
        answer — the scan stops at the first separator row and returns None
        (the caller then uses the canonical fallback)."""
        lines = [
            "# 决策记录",
            "",
            "| 编号 | 日期 | 主题 |",       # legacy 3-col header area
            "| --- | --- |",
            "| DEC-001 | 2026-05-01 | 旧决策 |",
            "",
            "## 附录：字段说明", "",
            "| 字段 | 说明 |",
            "| --- | --- |",
            "| 关联任务 | governing refs 列 |",
        ]
        self.assertIsNone(self.archive._decision_related_column_index(lines))

    def test_header_still_found_and_body_decoy_ignored(self):
        """Zero-flip guard: the real header (first table, before the first
        separator) still answers, and a later narrative table cannot
        shadow it."""
        lines = [
            "# 决策记录",
            "",
            _DECISION_HEADER,
            _DECISION_SEPARATOR,
            "| DEC-187 | 2026-09-12 | 主题 | 背景 | 决策 | 备选 | 原因 "
            "| 影响 | 决策人 | FIX-310 | 后续 |",
            "",
            "## 附录：字段说明", "",
            "| 字段 | 关联任务 |",
            "| --- | --- |",
            "| 注 | 见上 |",
        ]
        self.assertEqual(
            self.archive._decision_related_column_index(lines), 9)


if __name__ == "__main__":
    unittest.main()
