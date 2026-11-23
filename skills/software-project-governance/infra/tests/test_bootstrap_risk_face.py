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

FIX-422 additions (2026-10-03 evidence chain):
* deadline caliber — a 截止日期 cell participates in the overdue/soon
  judgment ONLY as a PURE ISO date; re-review-stream cells (multi-date
  prose, the RISK-044/047/048 live shapes) yield NO signal — never a
  fabricated overdue — while pure past dates still report honestly
  (``DeadlinePureIsoDateTests``);
* closed-family annotated forms — ``**已缓解**``/``**降级**``/``**已收窄**``
  + parenthetical date are closed head tokens now (the RISK-026/027/048/
  061 quartet leaves the unknown face; ``ClosedAnnotatedFormsTests``).

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
from unittest.mock import patch

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
            # FIX-422 — the live annotated closed forms (bold head token +
            # space/full-width parenthetical + date annotation): the
            # RISK-026/027/048/061 quartet that bucketed ``unknown`` and
            # inflated the open face before FIX-422.
            "**已缓解** (2026-09-28 FIX-401 收窄——监测口径落地)",
            "**降级** (2026-05-05)",
            "**已收窄**（2026-05-12 RISK-026 复评）",
        )
        for cell in cases:
            self.assertEqual(ba._risk_status_bucket(cell), "closed", cell)

    def test_unknown_forms(self):
        # Nothing outside the vocabulary is guessed into a bucket.
        # (FIX-422 moved the annotated closed forms above into the closed
        # family; what remains here is genuinely unclassifiable.)
        cases = (
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
            # FIX-422 annotated closed forms join the closed family.
            _risk_row("RISK-805", "**已缓解** (2026-09-28 FIX-401 收窄…)"),
            _risk_row("RISK-806", "**降级** (2026-05-05)"),
            _risk_row("RISK-807", "**已收窄**（2026-05-12 复评）"),
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
            _risk_row("RISK-815", "已接受（DEC-149）"),   # unknown → counted
            _risk_row("RISK-816", "已关闭"),
            _risk_row("RISK-817", "**已关闭** (2026-05-05)"),
            _risk_row("RISK-818", "缓解完成"),
            # FIX-422: the annotated closed form is closed now, not unknown.
            _risk_row("RISK-819", "**降级** (2026-05-05)"),
        ])
        summary = ba.parse_risk_summary(text, today=_TODAY)
        # 4 vocabulary-open rows + 1 unknown row (fail-closed count);
        # the annotated closed row (RISK-819) never counts.
        self.assertEqual(summary["open"], 5)
        self.assertEqual(summary["unknown_count"], 1)
        self.assertEqual(len(summary["unknown_statuses"]), 1)
        self.assertEqual(summary["unknown_statuses"][0]["id"], "RISK-815")
        self.assertIn("已接受", summary["unknown_statuses"][0]["status"])


class UnknownDisclosureTests(unittest.TestCase):
    """Unknown tokens: counted + disclosed, bounded, never guessed."""

    def test_disclosure_list_is_bounded_count_carries_truth(self):
        rows = [_risk_row("RISK-82%d" % i, "已接受（DEC-149）")
                for i in range(7)]
        summary = ba.parse_risk_summary(_risk_log(rows), today=_TODAY)
        self.assertEqual(summary["open"], 7)
        self.assertEqual(summary["unknown_count"], 7)
        self.assertEqual(len(summary["unknown_statuses"]),
                         ba._RISK_UNKNOWN_DISCLOSURE_CAP)

    def test_unknown_status_cells_are_clipped(self):
        long_status = "已接受 (" + "冗" * 120 + ")"
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
        # (FIX-422 note: the annotated closed forms ARE vocabulary now, so
        # the genuinely-unclassifiable token here is 已接受.)
        summary = ba.parse_risk_summary(
            _risk_log([_shifted_risk_row("RISK-843", "已接受（DEC-149）")]),
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
            # FIX-422: the downgraded annotated form is CLOSED now — it
            # leaves the open face and the unknown face entirely.
            _risk_row("RISK-856", "**降级** (2026-05-05)"),
            _risk_row("RISK-857", "**已关闭** (2026-05-05)"),
            _risk_row("RISK-858", "缓解完成"),
        ])
        summary = ba.parse_risk_summary(text, today=_TODAY)
        # Non-closed rows: 851 852 853 854 855 = 5 (none unknown anymore).
        self.assertEqual(summary["open"], 5)
        self.assertEqual(summary["unknown_count"], 0)
        # Only the aligned open row carries a parseable past deadline.
        self.assertEqual(summary["escalation_overdue"], 1)
        self.assertEqual(summary["overdue_ids"], ["RISK-851"])


class DeadlinePureIsoDateTests(unittest.TestCase):
    """FIX-422 缺陷① — the deadline cell participates in the overdue/soon
    judgment ONLY as a PURE ISO date.

    The live risk-log's 截止日期 column has been repurposed as free-text
    re-review streams (several historical dates + narrative). The pre-fix
    ``deadline[:10]`` read grabbed the FIRST historical date out of that
    prose and fabricated overdue escalations: RISK-044 read 2026-08-26
    (-38d), RISK-047/048 read 2026-09-30 (-3d), all on 2026-10-03. The
    fix's fail-safe direction: a non-pure cell yields NO deadline signal —
    never a fabricated overdue — while a pure PAST date still reports
    honestly (the fix must not swallow real escalations either).
    """

    #: The RISK-044 deadline cell verbatim (2026-10-03 deep-inspection
    #: evidence chain): re-review stream, four dates, long narrative.
    _REVIEW_STREAM = (
        "2026-08-26 检查点通过；**2026-09-08 正式复评执行（M-0，DEC-177 ②）："
        "已接受→缓解中**（4 样本墙钟…）；**2026-10-02 复评（逾期升级线处置——"
        "维持缓解中）**；下次复评 2026-10-31（0.94 立项窗）")

    def test_risk044_review_stream_yields_no_fabricated_overdue(self):
        summary = ba.parse_risk_summary(
            _risk_log([_risk_row("RISK-044", "缓解中",
                                 deadline=self._REVIEW_STREAM)]),
            today=date(2026, 10, 3))
        self.assertEqual(summary["open"], 1)
        self.assertEqual(summary["escalation_overdue"], 0)
        self.assertEqual(summary["escalation_soon"], 0)
        self.assertEqual(summary["overdue_ids"], [])

    def test_risk047048_first_date_stream_yields_no_signal(self):
        # The RISK-047/048 family: prose whose HEAD is a past date — the
        # exact shape the pre-fix [:10] read parsed into a fake -3d.
        stream = "2026-09-30 复评流水（RISK-047/048 实况族）：维持缓解中，下次 2026-10-31"
        summary = ba.parse_risk_summary(
            _risk_log([_risk_row("RISK-047", "缓解中", deadline=stream),
                       _risk_row("RISK-048", "打开", deadline=stream)]),
            today=date(2026, 10, 3))
        self.assertEqual(summary["open"], 2)
        self.assertEqual(summary["escalation_overdue"], 0)
        self.assertEqual(summary["escalation_soon"], 0)

    def test_pure_future_deadline_computes_by_calendar(self):
        # Pure 2026-10-31: the calendar decides — no signal a week out,
        # soon inside the 3-day window, overdue the day after.
        for today, overdue, soon in (
                (date(2026, 10, 20), 0, 0),   # +11d
                (date(2026, 10, 29), 0, 1),   # +2d
                (date(2026, 10, 31), 0, 1),   # 0d
                (date(2026, 11, 1), 1, 1),    # -1d
        ):
            with self.subTest(today=today):
                summary = ba.parse_risk_summary(
                    _risk_log([_risk_row("RISK-090", "打开",
                                         deadline="2026-10-31")]),
                    today=today)
                self.assertEqual(summary["escalation_overdue"], overdue)
                self.assertEqual(summary["escalation_soon"], soon)

    def test_pure_past_deadline_still_reports_overdue_honestly(self):
        # The regression guard for over-correction: a PURE past date is a
        # real escalation and must NOT be silenced by the fix.
        summary = ba.parse_risk_summary(
            _risk_log([_risk_row("RISK-091", "打开",
                                 deadline="2026-09-30")]),
            today=date(2026, 10, 3))
        self.assertEqual(summary["escalation_overdue"], 1)
        self.assertEqual(summary["overdue_ids"], ["RISK-091"])

    def test_filler_and_malformed_cells_stay_signal_free(self):
        for cell in ("—", "", "2026-02-30", "2026-13-01", "2026/10/31",
                     "大约 2026-10-31"):
            with self.subTest(cell=cell):
                summary = ba.parse_risk_summary(
                    _risk_log([_risk_row("RISK-092", "打开",
                                         deadline=cell)]),
                    today=date(2026, 10, 3))
                self.assertEqual(summary["escalation_overdue"], 0, cell)
                self.assertEqual(summary["escalation_soon"], 0, cell)


class ClosedAnnotatedFormsTests(unittest.TestCase):
    """FIX-422 缺陷③ — bold head token + space/full-width parenthetical +
    date annotation are CLOSED family forms.

    Live 2026-10-03 evidence: unknown_count=4 (RISK-026/027/048/061), all
    of them annotated closed forms (已缓解/降级/已收窄+括号日期) that the
    pre-fix closed vocabulary missed — counted as open AND disclosed,
    inflating the open face and burying genuinely unclassifiable rows.
    After FIX-422 the quartet reads closed and unknown goes to zero.
    """

    def test_live_annotated_closed_forms_bucket_closed(self):
        cases = (
            "**已缓解** (2026-09-28 FIX-401 收窄——监测口径落地)",
            "**降级** (2026-05-05)",
            "**已收窄**（2026-05-12 RISK-026 复评）",
            "**已关闭** (2026-05-05)",
        )
        for cell in cases:
            self.assertEqual(ba._risk_status_bucket(cell), "closed", cell)

    def test_live_unknown_quartet_counts_closed_unknown_zero(self):
        # The four live rows (RISK-026/027/048/061 shapes) — closed, and
        # the unknown face is EMPTY for them (验收 ③: unknown 归零).
        text = _risk_log([
            _risk_row("RISK-026", "**已收窄**（2026-05-12 复评——FIX-401）"),
            _risk_row("RISK-027", "**降级** (2026-05-05)"),
            _risk_row("RISK-048", "**已缓解** (2026-09-28 FIX-401 收窄…)"),
            _risk_row("RISK-061", "**已缓解** (2026-08-30)"),
        ])
        summary = ba.parse_risk_summary(text, today=_TODAY)
        self.assertEqual(summary["open"], 0)
        self.assertEqual(summary["unknown_count"], 0)
        self.assertEqual(summary["unknown_statuses"], [])

    def test_open_family_not_shadowed_by_new_tokens(self):
        # The new closed tokens are prefix-distinct from the open family:
        # 缓解中 (open) vs 已缓解 (closed) never shadow each other.
        self.assertEqual(ba._risk_status_bucket("缓解中"), "open")
        self.assertEqual(ba._risk_status_bucket("**缓解中（复评）**"), "open")
        self.assertEqual(ba._risk_status_bucket("已缓解"), "closed")

    def test_genuinely_unknown_stays_unknown_fail_closed(self):
        # The fail-closed disposition is unchanged: vocabulary outsiders
        # (已接受 etc.) still count as open + disclosed.
        summary = ba.parse_risk_summary(
            _risk_log([_risk_row("RISK-093", "已接受（DEC-149）")]),
            today=_TODAY)
        self.assertEqual(summary["open"], 1)
        self.assertEqual(summary["unknown_count"], 1)


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
                    # FIX-422: the annotated downgraded form counts closed
                    # through the real cmd entry too.
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
        # Non-closed rows: 871 872 873 = 3 (the downgraded row closed).
        self.assertEqual(risks["open"], 3)
        self.assertEqual(risks["unknown_count"], 0)
        self.assertEqual(risks["unknown_statuses"], [])
        # The JSON face keeps its pre-fix contract keys (additive change).
        for key in ("open", "escalation_overdue", "escalation_soon",
                    "overdue_ids"):
            self.assertIn(key, risks)


class RiskReaderAgreementTests(unittest.TestCase):
    """Every public reader sees the same IDs, even without a usable date."""

    def read_faces(self, content):
        import authority_ledger as ledger
        import verify_workflow as vw

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / ".governance/risk-log.md"
            path.parent.mkdir()
            if content is not None:
                path.write_text(content, encoding="utf-8")
            with patch.object(vw, "RISK_PATH", path):
                summary = ba.parse_risk_summary(content, include_rows=True)
                rows = vw.parse_active_risks()
                opened = vw.parse_open_risks()
                context = vw._parse_context_open_risks(root)
                aging = vw.check_risk_staleness()
                escalation = vw.check_risk_escalation()
        ids = [row["id"] for row in summary["rows"]]
        migration = ledger.parse_hot_zone("", content)
        self.assertEqual(ids, [row["risk_id"] for row in migration["risk_rows"]
                               if row["bucket"] != "closed"])
        self.assertEqual(summary["unknown_count"], migration["counts"]["risks"]["unknown"])
        self.assertEqual(ids, [row["id"] for row in rows])
        self.assertEqual(ids, [risk_id for risk_id, _ in opened])
        self.assertEqual(ids, [row["task_id"] for row in context])
        self.assertEqual(len(ids), aging["total_open"])
        self.assertEqual(len(ids), escalation["total_open"])
        self.assertEqual(summary["invalid_deadline"], len(escalation["invalid_deadline_ids"]))
        self.assertEqual(summary["no_deadline"], len(escalation["no_deadline_ids"]))
        self.assertEqual(summary["escalation_overdue"], escalation["escalation_count"])
        return rows, summary, aging, escalation

    def test_unknown_data_and_registered_age_are_independent_of_escalation(self):
        rows, summary, aging, escalation = self.read_faces(_risk_log([
            _risk_row("RISK-101", "缓解中", "2000-01-02").replace("2026-09-01", "登记待核"),
            _risk_row("RISK-102", "打开（条件观察）").replace("2026-09-01", "2000-01-01"),
            # Even an unambiguous mention of closure in mitigation is not a status.
            _risk_row("RISK-103", "待研判", "2000-03-01 复评", mitigation="已关闭旧单"),
            _risk_row("RISK-104", "已接受", "2026-02-30"),
            _risk_row("RISK-105", "resolved", "2000-01-01"),
            _risk_row("RISK-106", "**已关闭**", "2000-01-01"),
            _risk_row("RISK-107", "打开", "2099-01-01"),
        ]))
        by_id = {row["id"]: row for row in rows}
        self.assertEqual(list(by_id), ["RISK-101", "RISK-102", "RISK-103", "RISK-104", "RISK-107"])
        self.assertEqual(aging["unknown_registration"], [("RISK-101", "登记待核")])
        self.assertEqual(aging["unknown_status_ids"], ["RISK-103", "RISK-104"])
        self.assertIn("RISK-102", [item[0] for item in aging["stale"]])
        self.assertEqual(summary["unknown_count"], 2)
        self.assertEqual(escalation["no_deadline_ids"], ["RISK-102"])
        self.assertEqual(escalation["invalid_deadline_ids"], ["RISK-103", "RISK-104"])
        self.assertEqual([r["risk_id"] for r in escalation["escalated"]], ["RISK-101"])
        self.assertIsNone(by_id["RISK-103"]["deadline_date"])
        self.assertFalse(by_id["RISK-103"]["escalation_soon"])
        self.assertFalse(by_id["RISK-107"]["escalation_overdue"])

    def test_shifted_fields_reordered_headers_and_truncated_rows(self):
        text = _risk_log([_shifted_risk_row("RISK-108"),
                          _shifted_risk_row("RISK-109", "待研判")])
        text += ("\n## 历史格式\n| 当前状态 | 编号 | 负责人 | 风险描述 | 截止日期 |\n"
                 "|---|---|---|---|---|\n| 缓解中 | RISK-110 | QA | A\\|B | 2099-01-01 |\n"
                 "| 未判定 | RISK-111 | QA |")
        rows, _, aging, escalation = self.read_faces(text)
        self.assertEqual([(r["id"], r["owner"]) for r in rows],
                         [("RISK-108", "Claude"), ("RISK-109", "Claude"),
                          ("RISK-110", "QA"), ("RISK-111", "QA")])
        self.assertEqual(rows[0]["severity"], "高")
        self.assertEqual(rows[1]["status"], "待研判")
        self.assertEqual(rows[2]["description"], r"A\|B")
        self.assertEqual(aging["unknown_status_ids"], ["RISK-109", "RISK-111"])
        self.assertEqual(escalation["invalid_deadline_ids"], ["RISK-111"])

    def test_adjacent_risk_tables_keep_their_headers_and_real_rows(self):
        import authority_ledger as ledger
        from risk_rows import iter_risk_rows

        first = "| 编号 | 当前状态 | 截止日期 |\n|---|---|---|\n| RISK-101 | 打开 | — |"
        for header, row in [
            ("| 编号 | 当前状态 | 截止日期 |", "| RISK-102 | 已关闭 | 2000-01-01 |"),
            ("| 当前状态 | 编号 | 截止日期 |", "| 已关闭 | RISK-102 | 2000-01-01 |"),
        ]:
            with self.subTest(header=header):
                content = f"{first}\n\n{header}\n|---|---|---|\n{row}"
                expected = [("RISK-101", "打开"), ("RISK-102", "已关闭")]
                self.assertEqual([(r.id, r.status) for r in iter_risk_rows(content)], expected)
                rows, summary, _, _ = self.read_faces(content)
                self.assertEqual([(r["id"], r["status"]) for r in rows], expected[:1])
                self.assertEqual((summary["open"], summary["unknown_count"]), (1, 0))
                ml = ledger.parse_hot_zone("", content)
                self.assertEqual([(r["risk_id"], r["status"]) for r in ml["risk_rows"]],
                                 expected)
                self.assertEqual(ml["counts"]["risks"],
                                 {"rows": 2, "open": 1, "closed": 1, "unknown": 0})

    def test_missing_deadline_column_and_short_row_are_unjudgeable(self):
        content = ("| 编号 | 当前状态 |\n|---|---|\n| RISK-113 | 打开 |\n\n"
                   "| 编号 | 当前状态 | 截止日期 |\n|---|---|---|\n"
                   "| RISK-114 | 缓解中 |\n\n| RISK-115 | 打开 | |\n"
                   "| RISK-116 | 打开（条件观察） | — |")
        rows, summary, _, escalation = self.read_faces(content)
        self.assertEqual([(r["id"], r["deadline_kind"]) for r in rows],
                         [("RISK-113", "invalid"), ("RISK-114", "invalid"),
                          ("RISK-115", "none"), ("RISK-116", "none")])
        self.assertEqual(escalation["invalid_deadline_ids"], ["RISK-113", "RISK-114"])
        self.assertEqual(escalation["no_deadline_ids"], ["RISK-115", "RISK-116"])
        self.assertEqual((summary["escalation_soon"], summary["escalation_overdue"]), (0, 0))

    def test_optional_border_pipes_independently_on_header_delimiter_and_body(self):
        from itertools import product

        header = "编号|日期|风险描述|阶段|触发|影响|严重级别|负责人|当前状态"
        separator = "|".join([":--:"] * 9)
        row = r"RISK-101|2026-01-01|C:\logs\a\|b\\|阶段|触发|影响|中|QA|打开"
        borders = (("", ""), ("|", ""), ("", "|"), ("|", "|"))
        for choices in product(borders, repeat=3):
            text = "\n".join(left + middle + right for (left, right), middle
                             in zip(choices, (header, separator, row)))
            with self.subTest(borders=choices):
                rows, summary, _, escalation = self.read_faces(text)
                self.assertEqual([(r["id"], r["description"], r["status"]) for r in rows],
                                 [("RISK-101", r"C:\logs\a\|b\\", "打开")])
                self.assertEqual(summary["unknown_count"], 0)
                self.assertEqual(escalation["invalid_deadline_ids"], ["RISK-101"])

        for left, right in borders:
            with self.subTest(headerless=(left, right)):
                rows, _, _, _ = self.read_faces(left + row + right)
                self.assertEqual([(r["id"], r["status"]) for r in rows], [("RISK-101", "打开")])

    def test_terminal_escaped_pipe_and_explicit_empty_or_absent_deadline(self):
        text = ("编号 | 当前状态 | 截止日期 | 风险描述\n"
                ":-- | --: | --- | ---\n"
                r"RISK-101 | 缓解中 | 2000-01-02 | A\|" "\n"
                r"RISK-102 | 打开 | | literal\\" "\n"
                "RISK-103 | 打开")
        rows, _, _, escalation = self.read_faces(text)
        self.assertEqual([(r["id"], r["description"], r["deadline_kind"]) for r in rows],
                         [("RISK-101", r"A\|", "dated"), ("RISK-102", r"literal\\", "none"),
                          ("RISK-103", "", "invalid")])
        self.assertEqual(escalation["no_deadline_ids"], ["RISK-102"])
        self.assertEqual(escalation["invalid_deadline_ids"], ["RISK-103"])

    def test_headers_need_an_adjacent_delimiter_matching_every_column(self):
        for broken in ("---|---", "---|---|oops", "---|---|", "---|---|---|---",
                       "\n---|---|---"):
            with self.subTest(broken=broken):
                text = "编号|当前状态|截止日期\n" + broken + "\nRISK-101|打开|2000-01-01"
                rows, _, _, _ = self.read_faces(text)
                self.assertEqual(rows, [])

    def test_adjacent_tables_without_blank_use_new_header_and_ignore_prose(self):
        import authority_ledger as ledger

        text = ("编号|当前状态|截止日期\n---|---|---\nRISK-101|打开|2000-01-01\n"
                "当前状态|截止日期|编号\n:---|:---:|---:\n已关闭|—|RISK-102\n"
                "这是一个有竖线的注释|x|y\n不是表格的另一个段落\nRISK-103|打开|—")
        rows, _, _, _ = self.read_faces(text)
        self.assertEqual([r["id"] for r in rows], ["RISK-101"])
        self.assertEqual([(r["risk_id"], r["status"]) for r in ledger.parse_hot_zone("", text)["risk_rows"]],
                         [("RISK-101", "打开"), ("RISK-102", "已关闭")])

    def test_fenced_examples_and_paragraphs_do_not_register_risks(self):
        example = "编号|当前状态\n---|---\nRISK-901|打开\n"
        content = ("文字包含 \\| 和 |。\n````markdown\n" + example + "```\n" + example
                   + "````\n\n" + "编号|当前状态\n---|---\nRISK-101|打开")
        rows, _, _, _ = self.read_faces(content)
        self.assertEqual([r["id"] for r in rows], ["RISK-101"])

    def test_reordered_columns_do_not_apply_historical_shift_to_unknown_status(self):
        content = ("编号|风险描述|日期|影响|触发条件|严重级别|所属阶段|Owner|当前状态\n"
                   + "|".join(["---"] * 9)
                   + "\nRISK-101|说明|2026-01-01|说明|事件|高|维护|已关闭|缓解：待另行判读")
        rows, summary, _, _ = self.read_faces(content)
        self.assertEqual([(r["owner"], r["status"]) for r in rows],
                         [("已关闭", "缓解：待另行判读")])
        self.assertEqual(summary["unknown_count"], 1)

    def test_legacy_decorated_ids_and_blank_header_gap_keep_fields_and_original_row(self):
        import authority_ledger as ledger
        import risk_rows

        header = "| **编号** | `当前状态` | 日期 | 严重级别 | **Owner** | 风险/阻塞描述 | 截止日期 |"
        separator = "|---|---|---|---|---|---|---|"
        for gap in ("\n", "\n\n", "\n  \n\n"):
            for decorated_id in ("RISK-101", "**RISK-101**", "`RISK-101`"):
                with self.subTest(gap=repr(gap), risk_id=decorated_id):
                    line = (f"| {decorated_id} | **打开** | `2000-01-01` | **高** | `QA` "
                            "| 需**核验** | **2000-01-04** |")
                    content = header + gap + separator + "\n" + line
                    rows, summary, aging, escalation = self.read_faces(content)
                    status = rows[0]
                    self.assertEqual((status["id"], status["opened_date"], status["severity"],
                                      status["owner"], status["description"], status["status"],
                                      status["deadline"], status["deadline_date"]),
                                     ("RISK-101", "2000-01-01", "高", "QA", "需核验", "打开",
                                      "2000-01-04", "2000-01-04"))
                    self.assertEqual(aging["unknown_registration"], [])
                    self.assertEqual(summary["overdue_ids"], ["RISK-101"])
                    self.assertEqual([e["risk_id"] for e in escalation["escalated"]], ["RISK-101"])
                    self.assertEqual(summary["rows"][0]["status"], "**打开**")
                    self.assertEqual(ledger.parse_hot_zone("", content)["risk_rows"],
                                     [{"risk_id": "RISK-101", "status": "**打开**", "bucket": "open"}])
                    self.assertEqual(next(risk_rows.iter_risk_rows(content)).raw_line, line)
                    self.assertEqual(next(risk_rows.iter_positional_tables(content))[0][0], "**编号**")

    def test_mixed_date_remains_unjudgeable_even_with_markdown_decoration(self):
        content = ("| 编号 | 日期 | 当前状态 | 截止日期 |\n|---|---|---|---|\n"
                   "| `RISK-101` | **不可判** | `未判读` | **2000-01-04 至 2001-02-03** |\n"
                   "| **RISK-102** | 2000-01-01 | 打开 | `—` |")
        rows, summary, aging, escalation = self.read_faces(content)
        self.assertIsNone(rows[0]["deadline_date"])
        self.assertEqual(rows[0]["deadline"], "2000-01-04 至 2001-02-03")
        self.assertEqual(summary["unknown_count"], 1)
        self.assertEqual(aging["unknown_status_ids"], ["RISK-101"])
        self.assertEqual(aging["unknown_registration"], [("RISK-101", "**不可判**")])
        self.assertEqual(escalation["invalid_deadline_ids"], ["RISK-101"])
        self.assertEqual(escalation["no_deadline_ids"], ["RISK-102"])

    def test_legacy_leading_bordered_header_with_gap_keeps_last_field(self):
        text = ("| 编号 | 当前状态 | 日期\n\n|---|---|---|\n"
                "| `RISK-101` | 打开 | 2000-01-01")
        rows, _, aging, _ = self.read_faces(text)
        self.assertEqual([(r["id"], r["opened_date"]) for r in rows],
                         [("RISK-101", "2000-01-01")])
        self.assertEqual(aging["total_open"], 1)

    def test_empty_and_headerless_legacy_files(self):
        for content in (None, "", _risk_log([])):
            with self.subTest(content=content):
                rows, _, _, escalation = self.read_faces(content)
                self.assertEqual(rows, [])
                self.assertEqual(escalation["escalation_count"], 0)
        rows, _, _, _ = self.read_faces(_risk_row("RISK-112", "打开"))
        self.assertEqual([r["id"] for r in rows], ["RISK-112"])


if __name__ == "__main__":
    unittest.main()
