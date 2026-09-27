"""FIX-397④ — bootstrap risks-face caliber regression tests.

The bootstrap risks face (``bootstrap_aggregate.parse_risk_summary``) must
count the risk-log's NON-CLOSED rows — the FIX-397④ charter caliber — not
the engine's exact-``打开`` active-set predicate. The pre-fix mirror
undercounted the live risk-log in two independent ways (bootstrap reported
4 vs 18 actual non-closed rows on 2026-09-27):

* annotated status forms ("打开（登记观察）", "**缓解中（…）**",
  "**已关闭** (2026-05-05)") failed the exact match;
* 8 shape-drifted rows (live RISK-052~059) carry their ``打开`` one column
  LEFT of the header position (full width, semantically shifted), so the
  positional exact match read the mitigation prose and skipped the row.

This suite pins the closed vocabulary (open / closed / unknown buckets),
the fail-closed unknown disposition (counted as open + disclosed, never
guessed or silently absorbed), the unique-vocabulary-anchor fallback for
shape-drifted rows, the exact-count face (all closed → 0, mixed → exact),
and the end-to-end ``governance-bootstrap`` JSON face.

Fixtures are synthetic risk-log texts and temporary ``.governance/`` trees
— the host project's live governance data is never read or written here.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_bootstrap_risk_face.py -q
    python -m unittest discover -s skills/software-project-governance/infra/tests -p "test_bootstrap_risk_face.py" -v
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import bootstrap_aggregate as ba  # noqa: E402

#: Clock-free deadline design: overdue rows pinned around 2026-09-10, far
#: rows at 2099 — open counts stay clock-independent (same discipline as
#: test_bootstrap_aggregate.SegmentedTableMirrorTests).
_TODAY = date(2026, 9, 10)

_RISK_HEADER = ("| 编号 | 日期 | 风险/阻塞描述 | 所属阶段 | 触发条件 | 影响 "
                "| 严重级别 | Owner | 当前状态 | 缓解动作 | 截止日期 | 关联任务 "
                "| 备注 |")
_RISK_SEPARATOR = ("|------|------|--------------|---------|---------|"
                   "------|---------|-------|---------|---------|---------|"
                   "---------|------|")


def _risk_row(rid, status, deadline="—", mitigation="观察"):
    """An ALIGNED 13-cell risk row (status lands on the header position)."""
    return ("| %s | 2026-09-01 | 风险描述 | 维护 | 触发条件 | 影响描述 | 高 "
            "| Claude | %s | %s | %s | TASK-1 | 备注 |"
            % (rid, status, mitigation, deadline))


def _shifted_risk_row(rid, status="打开"):
    """The live RISK-052~059 shape: 13 cells, semantically shifted.

    The 影响 cell is missing before the status column and a filler cell
    rides after the tail, so the row keeps FULL width (13 cells — invisible
    to any ragged-width guard) but every cell from 影响 left-shifts one
    position: the status lands at index 7, NOT the header's index 8, and
    the positional read sees the mitigation prose ("缓解：…").
    """
    return ("| %s | 2026-09-01 | 风险描述 | 维护 | 触发条件 | 高 | Claude "
            "| %s | 缓解：落地动作说明 | 凭证文档 | — | — | — |"
            % (rid, status))


def _risk_log(rows):
    return ("# 风险记录\n\n## 活跃风险\n\n%s\n%s\n%s\n"
            % (_RISK_HEADER, _RISK_SEPARATOR, "\n".join(rows)))


_PLAN_TRACKER = """# 项目计划跟踪

## 项目配置

- **项目名称**: 风险口径夹具项目
- **Profile**: standard
- **触发模式**: always-on
- **操作权限模式**: default-confirm
- **工作流版本**: 0.0.0
- **当前阶段**: 维护（maintenance）

## 0.0.0 task 表

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| P1 | TASK-1 | 夹具任务 | — | 0.0.0 | tests | ⏳ 待执行 |
"""


class RiskStatusBucketContractTests(unittest.TestCase):
    """The closed vocabulary: domain word forms keep their buckets.

    Prefix semantics is the declared design (live cells append bold markers
    and dated/parenthetical annotations to the head token) — these tests
    pin it so a future vocabulary edit is a conscious act.
    """

    def test_open_family_forms(self):
        cases = (
            "打开",
            "打开（登记观察）",
            "`打开`",
            "**打开**",
            "缓解中",
            "**缓解中（2026-09-08 M-0 复评转——DEC-177 ②）**"
            "〔原：已接受（DEC-149）——2026-08-26 检查点复核通过（维持）〕",
        )
        for cell in cases:
            self.assertEqual(ba._risk_status_bucket(cell), "open", cell)

    def test_closed_family_forms(self):
        cases = (
            "已关闭",
            "**已关闭** (2026-05-05)",
            "**关闭（2026-09-19 复评——REL-080 收口）**〔原：打开（已接受）〕",
            "缓解完成",
            "缓解完成（含遗留观察）",
        )
        for cell in cases:
            self.assertEqual(ba._risk_status_bucket(cell), "closed", cell)

    def test_unknown_forms(self):
        # Nothing outside the vocabulary is guessed into a bucket.
        cases = (
            "**降级** (2026-05-05)",
            "已接受",
            "",
            "缓解：报告内嵌 generated_at 时点元数据",
        )
        for cell in cases:
            self.assertEqual(ba._risk_status_bucket(cell), "unknown", cell)

    def test_open_boundary_pins(self):
        # 缓解中 beats 缓解完成 prefix confusion: "缓解中完成" is NOT a
        # thing in the domain, but if it appears the open-family head token
        # wins (declared prefix semantics, pinned here).
        self.assertEqual(ba._risk_status_bucket("缓解中完成"), "open")
        self.assertEqual(ba._risk_status_bucket("缓解完成"), "closed")


class AllClosedYieldsZeroTests(unittest.TestCase):
    """验收 ③a: every row in a closed family → open = 0."""

    def test_all_closed_rows_count_zero(self):
        text = _risk_log([
            _risk_row("RISK-801", "已关闭"),
            _risk_row("RISK-802", "**已关闭** (2026-05-05)"),
            _risk_row("RISK-803", "缓解完成"),
            _risk_row("RISK-804", "**关闭（2026-09-19 复评——收口）**〔原：打开〕"),
        ])
        summary = ba.parse_risk_summary(text, today=_TODAY)
        self.assertEqual(summary["open"], 0)
        self.assertEqual(summary["unknown_count"], 0)
        self.assertEqual(summary["unknown_statuses"], [])
        self.assertEqual(summary["escalation_overdue"], 0)
        self.assertEqual(summary["escalation_soon"], 0)


class MixedStatusExactCountTests(unittest.TestCase):
    """验收 ③b: mixed live-shaped statuses → the exact non-closed count."""

    def test_mixed_statuses_exact_count(self):
        text = _risk_log([
            _risk_row("RISK-811", "打开"),
            _risk_row("RISK-812", "打开（登记观察）"),
            _risk_row("RISK-813", "缓解中"),
            _risk_row("RISK-814",
                      "**缓解中（2026-09-08 M-0 复评转——DEC-177 ②）**"
                      "〔原：已接受（DEC-149）〕"),
            _risk_row("RISK-815", "**降级** (2026-05-05)"),   # unknown → counted
            _risk_row("RISK-816", "已关闭"),
            _risk_row("RISK-817", "**已关闭** (2026-05-05)"),
            _risk_row("RISK-818", "缓解完成"),
        ])
        summary = ba.parse_risk_summary(text, today=_TODAY)
        # 4 vocabulary-open rows + 1 unknown row (fail-closed count).
        self.assertEqual(summary["open"], 5)
        self.assertEqual(summary["unknown_count"], 1)
        self.assertEqual(len(summary["unknown_statuses"]), 1)
        self.assertEqual(summary["unknown_statuses"][0]["id"], "RISK-815")
        self.assertIn("降级", summary["unknown_statuses"][0]["status"])


class UnknownDisclosureTests(unittest.TestCase):
    """Unknown tokens: counted + disclosed, bounded, never guessed."""

    def test_disclosure_list_is_bounded_count_carries_truth(self):
        rows = [_risk_row("RISK-82%d" % i, "**降级** (2026-05-05)")
                for i in range(7)]
        summary = ba.parse_risk_summary(_risk_log(rows), today=_TODAY)
        self.assertEqual(summary["open"], 7)
        self.assertEqual(summary["unknown_count"], 7)
        self.assertEqual(len(summary["unknown_statuses"]),
                         ba._RISK_UNKNOWN_DISCLOSURE_CAP)

    def test_unknown_status_cells_are_clipped(self):
        long_status = "**降级** (" + "冗" * 120 + ")"
        summary = ba.parse_risk_summary(
            _risk_log([_risk_row("RISK-830", long_status)]), today=_TODAY)
        self.assertEqual(summary["unknown_count"], 1)
        cell = summary["unknown_statuses"][0]["status"]
        self.assertLessEqual(len(cell), 41)  # 40-char clip + ellipsis
        self.assertTrue(cell.endswith("…"))

    def test_text_face_discloses_unknown_rows(self):
        payload = {"risks": {"open": 2, "escalation_overdue": 0,
                             "escalation_soon": 0, "overdue_ids": [],
                             "unknown_count": 1,
                             "unknown_statuses": [
                                 {"id": "RISK-815", "status": "**降级**"}]}}
        text = ba.format_text(payload)
        self.assertTrue(any("risks-unknown" in ln and "RISK-815" in ln
                            for ln in text.split("\n")))

    def test_text_face_has_no_unknown_line_when_zero(self):
        payload = {"risks": {"open": 1, "escalation_overdue": 0,
                             "escalation_soon": 0, "overdue_ids": [],
                             "unknown_count": 0, "unknown_statuses": []}}
        text = ba.format_text(payload)
        self.assertFalse(any("risks-unknown" in ln
                             for ln in text.split("\n")))


class ShiftedRowAnchorTests(unittest.TestCase):
    """The live RISK-052~059 failure mode: full-width, semantically shifted
    rows — unique vocabulary anchor recovers them; ambiguity never guesses."""

    def test_shifted_open_row_is_counted_via_unique_anchor(self):
        summary = ba.parse_risk_summary(
            _risk_log([_shifted_risk_row("RISK-841")]), today=_TODAY)
        self.assertEqual(summary["open"], 1)
        self.assertEqual(summary["unknown_count"], 0)

    def test_shifted_row_with_real_date_yields_no_fabricated_overdue(self):
        # The anchored row's DEADLINE stays positional (cells[10] reads the
        # filler "—" on the shifted shape) → no escalation signal — the
        # fail-safe direction (recency is never fabricated from prose).
        summary = ba.parse_risk_summary(
            _risk_log([_shifted_risk_row("RISK-842")]), today=_TODAY)
        self.assertEqual(summary["escalation_overdue"], 0)
        self.assertEqual(summary["escalation_soon"], 0)
        self.assertEqual(summary["overdue_ids"], [])

    def test_shifted_unknown_row_stays_unknown_and_counted(self):
        # A shifted row whose true status is itself outside the vocabulary:
        # the anchor scan finds no vocabulary cell → unknown → counted.
        summary = ba.parse_risk_summary(
            _risk_log([_shifted_risk_row("RISK-843", "**降级** (2026-05-05)")]),
            today=_TODAY)
        self.assertEqual(summary["open"], 1)
        self.assertEqual(summary["unknown_count"], 1)
        self.assertEqual(summary["unknown_statuses"][0]["id"], "RISK-843")

    def test_ambiguous_row_is_not_guessed(self):
        # Positional cell unknown + TWO vocabulary cells elsewhere → the
        # anchor is ambiguous → unknown (counted + disclosed), never a
        # coin flip between open and closed.
        row = ("| RISK-844 | 2026-09-01 | 风险描述 | 维护 | 触发条件 | 影响描述 "
               "| 高 | Claude | 已接受 | 缓解中落地动作 | 2099-01-01 | TASK-1 "
               "| 已关闭态备注 |")
        summary = ba.parse_risk_summary(_risk_log([row]), today=_TODAY)
        self.assertEqual(summary["open"], 1)
        self.assertEqual(summary["unknown_count"], 1)
        self.assertEqual(summary["unknown_statuses"][0]["id"], "RISK-844")

    def test_positional_known_cell_is_never_overridden(self):
        # An aligned CLOSED row whose mitigation prose starts with an open
        # head token: positional-first wins (no anchor scan runs) → the row
        # stays closed and contributes nothing.
        summary = ba.parse_risk_summary(
            _risk_log([_risk_row("RISK-845", "已关闭",
                                 mitigation="缓解中收尾事项")]),
            today=_TODAY)
        self.assertEqual(summary["open"], 0)
        self.assertEqual(summary["unknown_count"], 0)

    def test_live_mixed_shape_exact_face(self):
        # The live 2026-09-27 risk-log shape in miniature: aligned opens,
        # annotated forms, shifted rows, bold closed rows, downgraded rows.
        text = _risk_log([
            _risk_row("RISK-851", "打开", deadline="2026-09-05"),
            _shifted_risk_row("RISK-852"),
            _shifted_risk_row("RISK-853"),
            _risk_row("RISK-854", "打开（登记观察）"),
            _risk_row("RISK-855",
                      "**缓解中（2026-09-08 M-0 复评转）**〔原：已接受〕"),
            _risk_row("RISK-856", "**降级** (2026-05-05)"),
            _risk_row("RISK-857", "**已关闭** (2026-05-05)"),
            _risk_row("RISK-858", "缓解完成"),
        ])
        summary = ba.parse_risk_summary(text, today=_TODAY)
        # Non-closed rows: 851 852 853 854 855 856 = 6 (one unknown).
        self.assertEqual(summary["open"], 6)
        self.assertEqual(summary["unknown_count"], 1)
        # Only the aligned open row carries a parseable past deadline.
        self.assertEqual(summary["escalation_overdue"], 1)
        self.assertEqual(summary["overdue_ids"], ["RISK-851"])


class CaliberSupersetPropertyTests(unittest.TestCase):
    """On clean aligned fixtures (plain tokens, no annotations, no drift)
    the new caliber agrees exactly with the legacy exact-``打开`` count —
    the divergence only ever ADDS rows the legacy predicate dropped."""

    def test_agrees_with_exact_open_on_clean_fixture(self):
        rows = [
            _risk_row("RISK-861", "打开", deadline="2026-09-05"),
            _risk_row("RISK-862", "打开", deadline="2099-01-01"),
            _risk_row("RISK-863", "已关闭"),
            _risk_row("RISK-864", "缓解完成"),
            _risk_row("RISK-865", "打开"),
        ]
        text = _risk_log(rows)
        summary = ba.parse_risk_summary(text, today=_TODAY)
        exact_open = sum(
            1 for _, rws in ba._iter_positional_tables(text)
            for cells in rws if cells[8].strip() == "打开")
        self.assertEqual(summary["open"], exact_open)
        self.assertEqual(summary["open"], 3)
        self.assertEqual(summary["unknown_count"], 0)


class EndToEndBootstrapFaceTests(unittest.TestCase):
    """验收 ②/③ through the real cmd entry on a synthetic tree."""

    def test_bootstrap_json_face_carries_nonclosed_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            gov = Path(tmp) / ".governance"
            gov.mkdir(parents=True)
            (gov / "plan-tracker.md").write_text(
                _PLAN_TRACKER, encoding="utf-8")
            (gov / "risk-log.md").write_text(
                _risk_log([
                    _risk_row("RISK-871", "打开"),
                    _shifted_risk_row("RISK-872"),
                    _risk_row("RISK-873", "打开（登记观察）"),
                    _risk_row("RISK-874", "**降级** (2026-05-05)"),
                    _risk_row("RISK-875", "已关闭"),
                    _risk_row("RISK-876", "缓解完成"),
                ]), encoding="utf-8")
            args = ba.build_arg_parser().parse_args(
                ["--project-root", tmp, "--format", "json"])
            buf = io.StringIO()
            with redirect_stdout(buf):
                ba.cmd_governance_bootstrap(args)
            payload = json.loads(buf.getvalue())
        risks = payload["risks"]
        # Non-closed rows: 871 872 873 874 = 4 (one unknown).
        self.assertEqual(risks["open"], 4)
        self.assertEqual(risks["unknown_count"], 1)
        self.assertEqual(risks["unknown_statuses"][0]["id"], "RISK-874")
        # The JSON face keeps its pre-fix contract keys (additive change).
        for key in ("open", "escalation_overdue", "escalation_soon",
                    "overdue_ids"):
            self.assertIn(key, risks)


if __name__ == "__main__":
    unittest.main()
