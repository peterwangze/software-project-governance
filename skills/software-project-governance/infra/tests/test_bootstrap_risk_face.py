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


if __name__ == "__main__":
    unittest.main()
