"""FIX-390 — Check 18/18b structured-status judgment (DEC-241 resolution).

Background (DEC-241 / REL-089 report §②, docs/release/rel-089-m3-precondition-report.md):
the 0.88.0 release window registered a formal 2×2 exception — Check 18 (Fact
Grounding) and Check 18b (Structured Evidence) false-FAIL on the machine-
recorded evidence rows EVD-1140 (FIX-375) and EVD-1164 (REL-087). Root cause
(NOT a data defect — human review tri-recorded in the REL-089 report):

  1. The DEC-168 machine row-family contract (``governance_store.
     _build_evidence_row``) puts the fact basis in the INDEPENDENT basis
     column (parts[5], the ``--basis`` channel standard landing spot), while
     the Check 18/18b strict-judgment path only searched the description
     column (parts[4]).
  2. The hot-tracker exemption predicate was the narrow ✅-prefix display
     read (FIX-376 F-3 deliberate conservative divergence), so a task row
     flipped by the governed writer to its ONLY terminal state
     (``committed`` + ops receipt anchor, FIX-393 criterion) never exempted
     — display text and judgment were coupled.

FIX-390 decouples them — three-state structured completion read + basis
column + machine credential marker:

  - state ``committed``  : writer-terminal + 〔op-<32hex>〕 anchor
    (``_status_is_writer_committed_cell`` consumed BY IDENTITY — FIX-393
    authority, never re-stated here) → completed → exempt (ledger disclosed);
  - state ``legacy``     : ✅-led hand-era terminal (FIX-371/DEC-227
    semantics preserved byte-for-byte — S_new ⊇ S_old invariant);
  - state unknown        : EVERYTHING else (mixed chains not led by ✅,
    triaged/dev cells with anchors, hand-written 「committed」 without the
    anchor, unknown tokens) → NOT exempt — 未知不猜 (fail-closed, guarded).

And the fact judgment reads the structured surfaces: Check 18 falls back to
the basis column (parts[5]); Check 18b accepts the DEC-168 machine credential
(``机器写入：governance-store evidence-append op-<32hex>`` — the write-guard
face-2/5-policed writer prefix, consumed never re-stated) as the machine
attestation when (and only when) no structured-fact JSON exists.

Live-shape fidelity: the EVD-1140/EVD-1164 fixtures below carry the real
column layout, the real op receipt anchors (REL-089 report 复核记录 1/2) and
the load-bearing cell text of the live rows in .governance/evidence-log.md
(full narrative elided — DEC-213 static-pin discipline; the judgment keys on
the shapes, not the prose).

All tests use in-memory fixture strings; the real ``.governance/`` is never
touched.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_fix390_structured_status_judgment.py -v
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

import governance_store as gs  # noqa: E402
import task_row_update as tru  # noqa: E402
import verify_workflow as vw  # noqa: E402


# ── Live anchors (REL-089 report 复核记录 1/2 + live plan-tracker cells) ────

ANCHOR_EVD1140 = "op-0aff7f5b21044ce094b389e23a310dc9"
ANCHOR_EVD1164 = "op-4328347bc92a4afd9d82171a7eb6ecff"
ANCHOR_FEAT060 = "op-1fa546084f264d86ba0a8b4aa55995d1"
ANCHOR_TRIAGE = "op-c8517aad1e134c7ab78f1efbdccec8fd"

# Hot-tracker status-cell shapes (live forms, plan-tracker 2026-09-25/26).
ST_WRITER_COMMITTED = (
    "committed (2026-09-25——check-version-consistency/verify 全量全过；"
    "Code Reviewer 派发中) 〔" + ANCHOR_EVD1164 + "〕"
)
ST_WRITER_COMMITTED_MIDCELL_NARRATIVE = (
    "committed 已 lock 待派发 (2026-09-23——0.88 阶段 C1) 〔" + ANCHOR_FEAT060
    + "〕〔R0 NEEDS_CHANGE/2→R1 APPROVED_WITH_NOTES/0；commit 61618a5〕"
)
ST_LEGACY_CHECK = "✅ 完成 (2026-09-23——REVIEW-R0 APPROVED_WITH_NOTES/0)"
ST_LEGACY_DELIVERED = "✅ 已交付 (2026-09-20——数据勘正回填)"
# Everything below MUST stay guarded (未知不猜 — fail-closed).
ST_HAND_COMMITTED_NO_ANCHOR = "committed 审查中 (2026-09-26——审查派发中)"
ST_TRIAGED_ANCHORED = "🆕 已 triage 待排期 (2026-09-25——0.89 M-0 立项) 〔" + ANCHOR_TRIAGE + "〕"
ST_IN_PROGRESS_ANCHORED = "🆕 🔄 进行中 待排期 (2026-09-25——0.89 M-0 立项) 〔" + ANCHOR_TRIAGE + "〕"
ST_MIXED_CHAIN_TRAILING_CHECK = (
    "🔄 已 lock 待派发 (2026-09-23——0.88 阶段 A1) → ✅ 完成 (2026-09-24——R1 APPROVED/0 终态)"
)
# ✅-LED chains are exempt by the legacy prefix read (FIX-371 semantics —
# the reopened tail does not un-exempt a ✅-leading cell; pre-existing
# documented FIX-376 residual, preserved byte-for-byte by FIX-390).
ST_MIXED_CHAIN_REOPENED = "✅ 已发布 (2026-09-20) → 🔄 reopened (2026-09-21)"
ST_UNKNOWN_TOKEN = "🧪 未知token形态 (2026-09-26)"

# FIX-375/REL-087 live status cells: the mixed-chain cell keeps FIX-375
# GUARDED (FIX-376 F-3 conservative divergence preserved by design — the
# EVD-1140 row must turn green ON MERITS, not via exemption), while REL-087's
# writer-committed cell is terminal (EVD-1164 exempts).
ST_FIX375_LIVE = ST_MIXED_CHAIN_TRAILING_CHECK
ST_REL087_LIVE = ST_WRITER_COMMITTED


def _machine_evidence_row(evd_id, task_id, description, basis, op_id,
                          evd_type="产品代码",
                          file_location="skills/software-project-governance/infra/verify_workflow.py",
                          author="GovernanceDeveloper", date_str="2026-09-24",
                          gate="G11", notes="完成"):
    """Evidence row in the DEC-168 machine row-family layout.

    Mirrors ``governance_store._build_evidence_row``: the basis cell is
    ``事实依据：<basis> <marker>`` — the fact basis AND the machine
    credential marker land in the independent basis column (parts[5]),
    while the description column (parts[4]) carries 目标对齐/用户影响 only.
    """
    marker = ("（机器写入：governance-store evidence-append " + op_id
              + "；schema v1）")
    return (
        "| " + evd_id + " | " + task_id + " | " + evd_type + " | "
        + description + " | 事实依据：" + basis + " " + marker + " | "
        + file_location + " | " + author + " | " + date_str + " | " + gate
        + " | " + notes + " |"
    )


def _hand_evidence_row(evd_id, task_id, description, basis="",
                       evd_type="实现",
                       file_location="skills/software-project-governance/infra/verify_workflow.py",
                       author="Developer", date_str="2026-05-02",
                       gate="G11", notes="PASS"):
    """Hand-era evidence row (basis column present but may be empty)."""
    return (
        "| " + evd_id + " | " + task_id + " | " + evd_type + " | "
        + description + " | " + basis + " | " + file_location + " | "
        + author + " | " + date_str + " | " + gate + " | " + notes + " |"
    )


GOAL_IMPACT_DESC = (
    "writer 族三边缘收口主修复：引擎分发返回码透传+畸形 operation-id 结构化"
    "拒绝+resume 审计补章。（目标对齐：writer 族假绿退出码与裸 traceback 是"
    "结构化操作链路可观测性缺口，收口后失败不再静默，与过程自动质量不低质"
    "一致。用户影响：获得=失败退出码可被编排器感知；感知=脚本可依赖退出码；"
    "体验变化=正向；迁移指南=依赖旧 exit 0 行为的调用方需改读退出码）"
)

EVD1140_BASIS = ("test_governance_store.py 100 passed 零回归；"
                 "test_verify_workflow+registry 1001 绿；红绿四联探针")
EVD1164_DESC = (
    "M-1 版本 bump：SKILL.md 权威锚先 bump→release-projection 28 面"
    "收敛→双根 entry sync→CHANGELOG 版本段→static-pin 消解。（目标对齐："
    "全仓版本锚一致且豁免账本零 stale，发布链 M-1 门槛达成。用户影响："
    "获得=版本候选就绪+完整 CHANGELOG；感知=版本面更新；体验变化=正向；"
    "迁移指南=行为变更见 CHANGELOG 升级说明义务节）"
)
EVD1164_BASIS = ("check-version-consistency PASSED；verify 全量 PASSED exit 0；"
                 "static_version_pins 25P+release_projection 4P 精确；"
                 "manifest 886+cross-refs 727 PASS")


class Fix390FixtureBase(unittest.TestCase):
    """Shared plan-tracker/evidence-log fixture assembly."""

    def _setup(self, tmpdir, hot_rows, evidence_rows, release_line_tasks):
        """Write fixture plan-tracker + evidence-log; returns (sp, ep).

        hot_rows: list of (task_id, status_cell) — rendered into the
        当前活跃事项 hot table (status = last cell, live layout).
        release_line_tasks: task ids mentioned in the 版本规划 进行中 row
        (the _current_release_task_ids read).
        """
        root = Path(tmpdir)
        gov = root / ".governance"
        gov.mkdir(parents=True, exist_ok=True)
        sp = gov / "plan-tracker.md"
        ep = gov / "evidence-log.md"
        tracker = [
            "# 计划跟踪",
            "## 项目配置",
            "- **项目目标**: 提供一套完整的软件项目治理工作流插件",
            "## 当前活跃事项",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
        ]
        for index, (task_id, status_cell) in enumerate(hot_rows, 1):
            tracker.append(
                "| **P1** | {0} | fixture 事项 {1} | — | 0.89.0 | tests | {2} |"
                .format(task_id, index, status_cell)
            )
        tracker += [
            # Live trackers end 当前活跃事项 with the 最近完成 subsection —
            # the section boundary _plan_hot_tracker_task_statuses and
            # parse_current_active_tasks both stop at (without it, the
            # 版本规划 rows below would leak into the hot-status scan).
            "### 最近完成",
            "（fixture：无）",
            "## 版本规划",
            "| 版本 | 状态 | 预计日期 | 核心范围 | 包含 Tier/Layer | 关键交付物 |",
            "| 0.89.0 | 进行中 | 2026-10-01 | fix390 面 | "
            + "、".join(release_line_tasks) + " | delivery |",
        ]
        sp.write_text("\n".join(tracker), encoding="utf-8")
        ep.write_text("\n".join(evidence_rows), encoding="utf-8")
        return sp, ep


class ThreeStateExemptionTests(Fix390FixtureBase):
    """Acceptance ①: committed / ✅ / unknown 三态在 Check 18/18b 判定（豁免
    面 = Check 16/17/18/18b 共享的入集路径）中各得其所。"""

    EXEMPTED_SHAPES = (
        ("writer-committed+anchor", ST_WRITER_COMMITTED),
        ("writer-committed midcell narrative", ST_WRITER_COMMITTED_MIDCELL_NARRATIVE),
        ("legacy ✅ 完成", ST_LEGACY_CHECK),
        ("legacy ✅ 已交付", ST_LEGACY_DELIVERED),
        ("legacy ✅-led chain (reopened tail)", ST_MIXED_CHAIN_REOPENED),
    )
    GUARDED_SHAPES = (
        ("hand committed no anchor", ST_HAND_COMMITTED_NO_ANCHOR),
        ("triaged+anchor", ST_TRIAGED_ANCHORED),
        ("in-progress+anchor", ST_IN_PROGRESS_ANCHORED),
        ("mixed chain trailing ✅", ST_MIXED_CHAIN_TRAILING_CHECK),
        ("unknown token", ST_UNKNOWN_TOKEN),
        ("empty status", ""),
    )

    def _entries_and_ledger(self, tmpdir, status_cell, task_id="FIX-910"):
        sp, ep = self._setup(
            tmpdir,
            hot_rows=[(task_id, status_cell)],
            evidence_rows=[_machine_evidence_row(
                "EVD-910", task_id, GOAL_IMPACT_DESC, EVD1140_BASIS,
                ANCHOR_EVD1140)],
            release_line_tasks=[task_id],
        )
        with patch.object(vw, "SAMPLE_PATH", sp), \
             patch.object(vw, "EVIDENCE_PATH", ep):
            return vw.parse_impact_analysis_entries_with_exemptions()

    def test_committed_and_legacy_shapes_are_exempt(self):
        """committed（写入器终态+锚）与 ✅（legacy 完成态）均按完成处理。"""
        for label, status_cell in self.EXEMPTED_SHAPES:
            with self.subTest(shape=label):
                with tempfile.TemporaryDirectory() as td:
                    entries, exempted = self._entries_and_ledger(td, status_cell)
                self.assertEqual(entries, [],
                                 "exempted row must leave the entry set")
                self.assertEqual(len(exempted), 1)
                self.assertEqual(exempted[0]["task_id"], "FIX-910")
                self.assertEqual(exempted[0]["evd_id"], "EVD-910")
                # Ledger disclosure carries the real status cell (auditable).
                self.assertEqual(exempted[0]["status"], status_cell)

    def test_unknown_shapes_stay_guarded_unknown_is_never_guessed(self):
        """未知不猜：无锚 committed / triaged / 进行中 / 混合链 / 未知 token
        全部保持 guarded（零豁免），行按事实 merits 判定。"""
        for label, status_cell in self.GUARDED_SHAPES:
            with self.subTest(shape=label):
                with tempfile.TemporaryDirectory() as td:
                    entries, exempted = self._entries_and_ledger(td, status_cell)
                self.assertEqual(len(entries), 1,
                                 "guarded row stays in the strict entry set")
                self.assertEqual(entries[0]["task_id"], "FIX-910")
                self.assertEqual(exempted, [])

    def test_exempted_ledger_still_discloses_legacy_rows(self):
        """既有 ✅ 豁免语义零误伤：FIX-371 ledger 记录形态不变（evd/task/status）。"""
        with tempfile.TemporaryDirectory() as td:
            _, exempted = self._entries_and_ledger(td, ST_LEGACY_CHECK,
                                                   task_id="FIX-911")
        self.assertEqual(
            exempted,
            [{"evd_id": "EVD-910", "task_id": "FIX-911",
              "status": ST_LEGACY_CHECK}],
        )

    def test_s_new_is_superset_of_s_old_over_shape_matrix(self):
        """S_new ⊇ S_old（FIX-382 静默集不变量同型义务）：旧 ✅-前缀豁免集
        是新三态豁免集的子集；扩张面恰为 writer-committed 形态。"""
        shapes = [cell for _, cell in self.EXEMPTED_SHAPES] + \
                 [cell for _, cell in self.GUARDED_SHAPES]
        old_exempt = set()
        new_exempt = set()
        for index, cell in enumerate(shapes):
            # Old predicate (FIX-376 F-3 narrow read): ✅ display prefix.
            if cell.startswith(vw._COMPLETED_STATUS_PREFIX):
                old_exempt.add(index)
            # New predicate (FIX-390 three-state read).
            if vw._hot_status_completion_state(cell):
                new_exempt.add(index)
        self.assertTrue(old_exempt <= new_exempt,
                        "S_new ⊇ S_old invariant violated")
        # Old face: the three ✅-led shapes only (writer-committed cells were
        # NEVER exempt before FIX-390 — the DEC-241 false-FAIL root).
        self.assertEqual(old_exempt, {2, 3, 4})
        # New face: the two writer-committed shapes join; nothing drops.
        self.assertEqual(new_exempt, {0, 1, 2, 3, 4})

    def test_writer_identity_binding_real_writer_product_exempts(self):
        """判据按身份复用 FIX-393：真实写入器产品行（task_row_update 构建）
        豁免；同一行剥掉 ops 锚（B-1 手改类）后回到 guarded。"""
        op_id = "op-" + "b" * 32
        base_row = ("| **P1** | FIX-912 | fixture title | — | 0.89.0 | "
                    "产品代码 | 🔄 进行中 |")
        written = tru.build_candidate_row(
            base_row, from_state="dev", to_state="committed",
            operation_id=op_id)
        cells = [c.strip() for c in written.strip().split("|")]
        status_cell = cells[-2]
        self.assertTrue(vw._status_is_writer_committed_cell(
            vw._status_clean_cell(status_cell)))
        self.assertEqual(vw._hot_status_completion_state(status_cell),
                         "committed")
        # Anchor stripped → display text alone is NEVER terminal (未知不猜).
        stripped = status_cell.replace("〔" + op_id + "〕", "").strip()
        self.assertEqual(vw._hot_status_completion_state(stripped), "")

    def test_live_fix375_row_stays_guarded_and_rel087_row_exempts(self):
        """活体定位：FIX-375 混合链（→ ✅ 完成，非 ✅ 领头）保持 guarded；
        REL-087 writer-committed 终态豁免——与热表 2026-09-25 实格一致。"""
        self.assertEqual(vw._hot_status_completion_state(ST_FIX375_LIVE), "")
        self.assertEqual(vw._hot_status_completion_state(ST_REL087_LIVE),
                         "committed")


class BasisColumnAndMachineCredentialTests(Fix390FixtureBase):
    """Acceptance ②: 0.88 例外两行红→绿活体（merits 路径——任务行保持
    guarded 时，事实判定读结构化面而非显示前缀）。"""

    def _run_checks(self, tmpdir, evidence_rows, hot_rows, release_tasks):
        sp, ep = self._setup(tmpdir, hot_rows=hot_rows,
                             evidence_rows=evidence_rows,
                             release_line_tasks=release_tasks)
        with patch.object(vw, "SAMPLE_PATH", sp), \
             patch.object(vw, "EVIDENCE_PATH", ep):
            return vw.check_fact_grounding(), vw.check_structured_evidence()

    def test_evd1140_live_shape_fact_grounding_green_via_basis_column(self):
        """EVD-1140（FIX-375）形态：basis 落独立列 parts[5]（DEC-168 契约
        标准落点）→ Check 18 改读 basis 列后 PASS（修复前假 FAIL）。"""
        with tempfile.TemporaryDirectory() as td:
            fg, _ = self._run_checks(
                td,
                evidence_rows=[_machine_evidence_row(
                    "EVD-1140", "FIX-375", GOAL_IMPACT_DESC, EVD1140_BASIS,
                    ANCHOR_EVD1140)],
                hot_rows=[("FIX-375", ST_FIX375_LIVE)],
                release_tasks=["FIX-375"],
            )
        self.assertTrue(fg["pass"])
        self.assertEqual(len(fg["entries"]), 1)
        entry = fg["entries"][0]
        self.assertEqual(entry["status"], "PASS")
        self.assertTrue(entry["has_fact_basis"])
        self.assertGreaterEqual(entry["fact_len"], 20)
        self.assertEqual(entry["fact_source"], "basis-column")

    def test_evd1140_live_shape_structured_evidence_green_via_credential(self):
        """EVD-1140 形态 Check 18b：无 JSON，但 DEC-168 机器凭证 marker
        （governance-store evidence-append op-<32hex>）→ machine-attested
        PASS（修复前假 FAIL）。"""
        with tempfile.TemporaryDirectory() as td:
            _, se = self._run_checks(
                td,
                evidence_rows=[_machine_evidence_row(
                    "EVD-1140", "FIX-375", GOAL_IMPACT_DESC, EVD1140_BASIS,
                    ANCHOR_EVD1140)],
                hot_rows=[("FIX-375", ST_FIX375_LIVE)],
                release_tasks=["FIX-375"],
            )
        self.assertTrue(se["pass"])
        entry = se["entries"][0]
        self.assertEqual(entry["status"], "PASS")
        self.assertTrue(entry["machine_attested"])
        self.assertFalse(entry["has_structured_fact"])
        self.assertEqual(entry["commands"], 0)
        self.assertEqual(entry["files_changed"], 0)

    def test_both_dec241_exception_rows_green_in_one_strict_run(self):
        """2×2 活体消解：EVD-1140+EVD-1164 同窗严格判定（任务行按实格：
        FIX-375 混合链 guarded、REL-087 writer-committed 豁免）——Check 18
        与 18b 全 PASS、pass=True、豁免仅 REL-087 一行且台账披露。"""
        with tempfile.TemporaryDirectory() as td:
            fg, se = self._run_checks(
                td,
                evidence_rows=[
                    _machine_evidence_row(
                        "EVD-1140", "FIX-375", GOAL_IMPACT_DESC,
                        EVD1140_BASIS, ANCHOR_EVD1140,
                        date_str="2026-09-24"),
                    _machine_evidence_row(
                        "EVD-1164", "REL-087", EVD1164_DESC, EVD1164_BASIS,
                        ANCHOR_EVD1164, date_str="2026-09-25"),
                ],
                hot_rows=[("FIX-375", ST_FIX375_LIVE),
                          ("REL-087", ST_REL087_LIVE)],
                release_tasks=["FIX-375", "REL-087"],
            )
        self.assertTrue(fg["pass"])
        self.assertTrue(se["pass"])
        self.assertEqual([e["status"] for e in fg["entries"]], ["PASS"])
        self.assertEqual(fg["entries"][0]["evd_id"], "EVD-1140")
        self.assertEqual(fg["entries"][0]["fact_source"], "basis-column")
        self.assertEqual([e["status"] for e in se["entries"]], ["PASS"])
        self.assertTrue(se["entries"][0]["machine_attested"])

    def test_machine_credential_with_malformed_op_id_is_not_attested(self):
        """未知不猜：marker 形存而 op 锚畸形（短/非 hex）→ 不构成机器凭证，
        Check 18b 维持 FAIL（伪造/残缺凭证不放行）。"""
        with tempfile.TemporaryDirectory() as td:
            _, se = self._run_checks(
                td,
                evidence_rows=[_machine_evidence_row(
                    "EVD-913", "FIX-913", GOAL_IMPACT_DESC, EVD1140_BASIS,
                    "op-0aff7f5b")],
                hot_rows=[("FIX-913", ST_IN_PROGRESS_ANCHORED)],
                release_tasks=["FIX-913"],
            )
        self.assertFalse(se["pass"])
        self.assertEqual(se["entries"][0]["status"], "FAIL")
        self.assertIn("缺少 结构化事实", se["entries"][0]["issues"][0])
        self.assertFalse(se["entries"][0]["machine_attested"])

    def test_hand_row_without_json_still_fails_18b(self):
        """既有严检语义零误伤：手写行（无 marker、无 JSON）→ 18b 维持
        FAIL——JSON 义务不为无凭证行松动。"""
        with tempfile.TemporaryDirectory() as td:
            _, se = self._run_checks(
                td,
                evidence_rows=[_hand_evidence_row(
                    "EVD-914", "FIX-914",
                    "事实依据: files and tests. 目标对齐: 结构化证据让治理"
                    "闭环更可信，事实链可机器检查。 用户影响: 获得=plugin "
                    "update, 感知=check-governance, 体验变化=正向, 迁移指南"
                    "=不需要")],
                hot_rows=[("FIX-914", ST_IN_PROGRESS_ANCHORED)],
                release_tasks=["FIX-914"],
            )
        self.assertFalse(se["pass"])
        self.assertIn("缺少 结构化事实", se["entries"][0]["issues"][0])
        self.assertFalse(se["entries"][0]["machine_attested"])

    def test_description_fact_takes_precedence_over_basis_column(self):
        """description 携带 事实依据 时的既有判定不变（source=description；
        basis 列仅为回退面——向后兼容）。"""
        desc = ("事实依据: verify_workflow.py check_fact_grounding "
                "implementation and FactGroundingTests PASS. 目标对齐: 提升"
                "治理工作流证据可信度，避免无事实闭环。 用户影响: 获得=plugin "
                "update, 感知=CHANGELOG, 体验变化=否, 迁移指南=不需要")
        with tempfile.TemporaryDirectory() as td:
            fg, _ = self._run_checks(
                td,
                evidence_rows=[_hand_evidence_row(
                    "EVD-915", "FIX-915", desc,
                    basis="basis 列文本：补充事实，不参与首选判定面")],
                hot_rows=[("FIX-915", ST_IN_PROGRESS_ANCHORED)],
                release_tasks=["FIX-915"],
            )
        self.assertTrue(fg["pass"])
        self.assertEqual(fg["entries"][0]["fact_source"], "description")

    def test_speculation_terms_in_basis_column_are_rejected(self):
        """不误放行：basis 列供事实时，未落地推断词扫描覆盖 basis 面。"""
        basis = ("test_governance_store.py 100 passed 零回归；"
                 "我猜测这个已经完成")
        with tempfile.TemporaryDirectory() as td:
            fg, _ = self._run_checks(
                td,
                evidence_rows=[_machine_evidence_row(
                    "EVD-916", "FIX-916", GOAL_IMPACT_DESC, basis,
                    ANCHOR_EVD1140)],
                hot_rows=[("FIX-916", ST_IN_PROGRESS_ANCHORED)],
                release_tasks=["FIX-916"],
            )
        self.assertFalse(fg["pass"])
        self.assertIn("含未落地推断词", fg["entries"][0]["issues"][0])

    def test_legacy_empty_basis_row_still_fails_check18(self):
        """既有严检语义零误伤：手写行 basis 列为空且 description 无 事实
        依据 → Check 18 维持 FAIL（原始 FIX-080 回归面）。"""
        with tempfile.TemporaryDirectory() as td:
            fg, _ = self._run_checks(
                td,
                evidence_rows=[_hand_evidence_row(
                    "EVD-917", "FIX-917",
                    "目标对齐: 提升治理工作流证据可信度，避免无事实闭环。 "
                    "用户影响: 获得=plugin update, 感知=CHANGELOG, 体验变化"
                    "=否, 迁移指南=不需要")],
                hot_rows=[("FIX-917", ST_IN_PROGRESS_ANCHORED)],
                release_tasks=["FIX-917"],
            )
        self.assertFalse(fg["pass"])
        self.assertIn("缺少 事实依据", fg["entries"][0]["issues"][0])


class MachineCredentialAuthorityBindingTests(unittest.TestCase):
    """凭证形状权威绑定（FIX-292 语义单源教训）：Check 18b 消费的 credential
    RE 必须命中真实写入器产品行——漂移即测试红。"""

    def test_credential_re_matches_really_built_evidence_row(self):
        op_id = "op-" + "a" * 32
        row_text, cells = gs._build_evidence_row(
            evd_id="EVD-918", task_id="FIX-918", evd_type="产品代码",
            description=GOAL_IMPACT_DESC, basis=EVD1140_BASIS,
            artifacts="x.py", actor="GovernanceDeveloper",
            date_str="2026-09-24", gate="G11", conclusion="完成", refs=[],
            op_id=op_id)
        self.assertEqual(len(cells), gs.EVIDENCE_COLUMNS)
        self.assertRegex(row_text, vw._EVIDENCE_MACHINE_CREDENTIAL_RE)

    def test_credential_re_rejects_malformed_and_foreign_markers(self):
        self.assertIsNone(
            vw._EVIDENCE_MACHINE_CREDENTIAL_RE.search(
                "（机器写入：governance-store evidence-append op-12345；schema v1）"))
        self.assertIsNone(
            vw._EVIDENCE_MACHINE_CREDENTIAL_RE.search(
                "（机器写入：governance-store decision-append op-" + "a" * 32 + "；schema v1）"))
        self.assertIsNone(
            vw._EVIDENCE_MACHINE_CREDENTIAL_RE.search(
                "机器写入：某个其它写入器 evidence-append op-" + "a" * 32))


class StructuredFactJsonStillWinsTests(Fix390FixtureBase):
    """既有 JSON 路径零回归：description 携带合法 JSON 时 18b 判定与载荷
    统计面保持原样（commands/files_changed 计数、违规拒绝）。"""

    def _payload_json(self):
        payload = {
            "commands": [{
                "cmd": "python skills/software-project-governance/infra/"
                       "verify_workflow.py check-governance --fail-on-issues",
                "exit_code": 0,
                "summary": "Governance health passed with zero issues.",
                "log_path": "terminal output",
            }],
            "files_changed": [
                "skills/software-project-governance/infra/verify_workflow.py",
                "skills/software-project-governance/infra/checks/evidence_domain.py",
            ],
            "diff_summary": "FIX-390 structured-status judgment surfaces.",
            "review": {"conclusion": "APPROVED", "reviewer": "Code Reviewer"},
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def test_valid_description_json_machine_attested_false(self):
        desc = ("事实依据: structured evidence validation was implemented "
                "and tested. 结构化事实: " + self._payload_json() +
                " 目标对齐: 结构化证据让治理闭环从自然语言叙述变成可机器检查"
                "的事实链。 用户影响: 获得=plugin update, 感知=check-"
                "governance, 体验变化=正向, 迁移指南=不需要")
        with tempfile.TemporaryDirectory() as td:
            sp, ep = self._setup(
                td,
                hot_rows=[("FIX-919", ST_IN_PROGRESS_ANCHORED)],
                evidence_rows=[_machine_evidence_row(
                    "EVD-919", "FIX-919", desc, EVD1140_BASIS,
                    ANCHOR_EVD1140)],
                release_line_tasks=["FIX-919"],
            )
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                se = vw.check_structured_evidence()
        self.assertTrue(se["pass"])
        entry = se["entries"][0]
        self.assertEqual(entry["status"], "PASS")
        self.assertTrue(entry["has_structured_fact"])
        self.assertFalse(entry["machine_attested"])
        self.assertEqual(entry["commands"], 1)
        self.assertEqual(entry["files_changed"], 2)

    def test_invalid_description_json_not_rescued_by_credential(self):
        """JSON 存在但载荷违规时，机器凭证不为其开脱（严格面优先）。"""
        payload = {
            "commands": [{"cmd": "x", "exit_code": "zero",
                          "summary": "ok"}],
            "files_changed": ["a.py"],
            "diff_summary": "short",
            "review": {"conclusion": "APPROVED", "reviewer": "R"},
        }
        desc = ("事实依据: implemented and tested. 结构化事实: "
                + json.dumps(payload, ensure_ascii=False,
                             separators=(",", ":"))
                + " 目标对齐: 结构化证据让治理闭环从自然语言叙述变成可机器检"
                "查的事实链。 用户影响: 获得=plugin update, 感知=check-"
                "governance, 体验变化=正向, 迁移指南=不需要")
        with tempfile.TemporaryDirectory() as td:
            sp, ep = self._setup(
                td,
                hot_rows=[("FIX-920", ST_IN_PROGRESS_ANCHORED)],
                evidence_rows=[_machine_evidence_row(
                    "EVD-920", "FIX-920", desc, EVD1140_BASIS,
                    ANCHOR_EVD1140)],
                release_line_tasks=["FIX-920"],
            )
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                se = vw.check_structured_evidence()
        self.assertFalse(se["pass"])
        self.assertEqual(se["entries"][0]["status"], "FAIL")
        self.assertFalse(se["entries"][0]["machine_attested"])


if __name__ == "__main__":
    unittest.main()
