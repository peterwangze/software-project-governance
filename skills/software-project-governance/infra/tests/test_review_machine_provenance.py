"""FIX-260 / REQ-107 — Check 30c review machine-provenance tests (red→green).

Covers ADR-017 R1 finding N1 (realized here): REVIEW evidence rows / review
files without the review-record CLI machine marker → WARN (gradual: escalate
to FAIL later), and NEEDS_CHANGE records lacking the machine ``next_round``
revisit field → WARN. Also locks the end-to-end contract: whatever
``review_record.write_review_record`` produces MUST pass Check 30c.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_review_machine_provenance.py -v
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

import review_record  # noqa: E402
import verify_workflow as vw  # noqa: E402


# Handwritten row shape mirrors the live evidence-log table contract
# (columns: | id | task_ref | type | description | basis | artifacts |
#  actor | date | gate | conclusion |).
HANDWRITTEN_ROW = (
    "| REVIEW-FIX-300-R0 | FIX-300 | 产品代码 | Code Review R0（独立 Reviewer，"
    "2026-09-01）：NEEDS_CHANGE | 事实依据：diff 逐行 | r0.patch | Code Reviewer | "
    "2026-09-01 | G11 | NEEDS_CHANGE |"
)
MACHINE_ROW_MARKER = "review-record CLI 机器写入"


class Check30cFixtureTests(unittest.TestCase):
    """FIX-260 REQ-107 four-signal fixtures: (a) WARN / (b) PASS / (c) WARN."""

    def _machine_row(self, task="FIX-301", result="APPROVED"):
        return (
            "| REVIEW-{t}-R0 | {t} | 治理记录 | review-record CLI 机器写入 review 结论记录"
            "（round 0） | 事实依据：review-record 输出摘要（机器写入） | r.md; "
            "review-{t}-R0.md | rv | 2026-09-01 | G11 | {r} |".format(t=task, r=result)
        )

    def _machine_file(self, task="FIX-301", result="APPROVED"):
        text = [
            "# Review Record (machine-written by review-record)",
            "",
            "- task: {0}".format(task),
            "- round: R0",
            "- date: 2026-09-01",
            "- reviewer: rv",
            "- report: r.md",
            "- wiring: pending",
            "",
            "**审查结论**: **{0}**".format(result),
        ]
        if result == "NEEDS_CHANGE":
            text += ["", "## 复审必达（NEEDS_CHANGE）", "",
                     "- next_round: REVIEW-{0}-R1".format(task),
                     "- prev_report: r.md"]
        text.append("")
        return "\n".join(text)

    def test_a_handwritten_row_fails_v7(self):
        """Fixture (a): handwritten REVIEW row (dated, no CLI marker) →
        FAIL/V7 (FEAT-089 / DEC-146 ② escalation: WARN → FAIL since 0.97.0)."""
        r = vw.check_review_machine_provenance(review_rows=[HANDWRITTEN_ROW])
        self.assertEqual(r["verdict"], "FAIL")
        rules = {v["rule"] for v in r["violations"]}
        self.assertIn("V7", rules)
        v7 = [v for v in r["violations"] if v["rule"] == "V7"]
        self.assertEqual(v7[0]["task_id"], "FIX-300")

    def test_b_machine_records_pass(self):
        """Fixture (b): CLI-marker row + machine-written file → PASS, no WARN."""
        r = vw.check_review_machine_provenance(
            review_rows=[self._machine_row()],
            review_files={"review-FIX-301-R0.md": self._machine_file()},
        )
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["verdict"], "PASS")

    def test_c1_needs_change_row_without_file_fails_v8(self):
        """Fixture (c) form 1: NEEDS_CHANGE row, no machine file → FAIL/V8
        (FEAT-089 escalation — V8 findings moved to violations)."""
        r = vw.check_review_machine_provenance(
            review_rows=[self._machine_row(result="NEEDS_CHANGE")],
            review_files={},
        )
        rules = {v["rule"] for v in r["violations"]}
        self.assertIn("V8", rules)

    def test_c2_needs_change_file_without_next_round_fails_v8(self):
        """Fixture (c) form 2: NEEDS_CHANGE file lacking next_round → FAIL/V8
        (FEAT-089 escalation)."""
        body = self._machine_file(result="NEEDS_CHANGE").replace(
            "- next_round: REVIEW-FIX-301-R1\n", "")
        r = vw.check_review_machine_provenance(
            review_rows=[],
            review_files={"review-FIX-301-R0.md": body},
        )
        rules = {v["rule"] for v in r["violations"]}
        self.assertIn("V8", rules)
        v8 = [v for v in r["violations"] if v["rule"] == "V8"]
        self.assertEqual(v8[0]["task_id"], "FIX-301")

    def test_pre_effective_date_rows_are_legacy_not_judged(self):
        """Rows/files dated before the effective date are legacy → no WARN."""
        old_row = HANDWRITTEN_ROW.replace("2026-09-01", "2026-08-01")
        old_file = self._machine_file().replace(
            "2026-09-01", "2026-08-01").replace(
            "# Review Record (machine-written by review-record)", "# Review")
        r = vw.check_review_machine_provenance(
            review_rows=[old_row, HANDWRITTEN_ROW.replace("2026-09-01", "2026-08-21")],
            review_files={"review-FIX-301-R0.md": old_file},
        )
        self.assertEqual(r["warnings"], [])
        # Nothing dated on/after the effective date → nothing judged.
        self.assertEqual(r["verdict"], "no-verdict")

    def test_undated_records_now_warn_v6d(self):
        """FEAT-089 / DEC-146 ② (V6d tightening): records without a parseable
        date are no longer silently un-judged — each undated REVIEW record is
        a V6d WARN (never counted in all_issues; the escalation's WARN tier)."""
        undated_row = HANDWRITTEN_ROW.replace("2026-09-01", "")
        undated_file = self._machine_file().replace("- date: 2026-09-01", "- date: ?")
        r = vw.check_review_machine_provenance(
            review_rows=[undated_row],
            review_files={"review-FIX-301-R0.md": undated_file},
        )
        self.assertEqual(r["verdict"], "WARN")
        rules = {w["rule"] for w in r["warnings"]}
        self.assertEqual(rules, {"V6d"}, r["warnings"])
        self.assertEqual(r["stats"]["rows_undated"], 1)
        self.assertEqual(r["stats"]["files_undated"], 1)
        self.assertEqual(r["violations"], [])

    def test_empty_corpus_is_no_verdict(self):
        r = vw.check_review_machine_provenance(review_rows=[], review_files={})
        self.assertEqual(r["verdict"], "no-verdict")

    def test_legacy_v_named_files_skipped(self):
        """review-{id}-v*.md legacy files are Check 30's legacy channel — skip."""
        r = vw.check_review_machine_provenance(
            review_rows=[],
            review_files={"review-FIX-301-v2.md": "# 手写旧格式\n审查结论: APPROVED"},
        )
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["stats"]["files_legacy_skipped"], 1)


class Check30cCliContractTests(unittest.TestCase):
    """End-to-end: review-record CLI output MUST satisfy Check 30c (REQ-107 §2)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="rr260_")
        self.root = Path(self.tmpdir)
        (self.root / ".governance").mkdir()

    def _record(self, result):
        return review_record.write_review_record(
            task_id="FIX-302",
            round_n=0,
            result=result,
            report_path=str(self.root / "report.md"),
            reviewer="Code Reviewer",
            root=self.root,
        )

    def _check(self):
        gov = self.root / ".governance"
        rows = [
            line for line in
            (gov / "evidence-log.md").read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("|")
        ]
        files = {}
        for rf in gov.glob("review-*.md"):
            files[rf.name] = rf.read_text(encoding="utf-8")
        return vw.check_review_machine_provenance(
            review_rows=rows, review_files=files)

    def test_cli_approved_output_passes_check30c(self):
        summary = self._record("APPROVED")
        self.assertFalse(summary.get("error"))
        r = self._check()
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["verdict"], "PASS")

    def test_cli_needs_change_output_carries_revisit_contract(self):
        summary = self._record("NEEDS_CHANGE")
        self.assertEqual(summary["next_round"], "REVIEW-FIX-302-R1")
        self.assertEqual(summary["prev_report"], str(self.root / "report.md"))
        r = self._check()
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["verdict"], "PASS")

    def test_live_scan_mode_reads_patched_paths(self):
        """Live mode (no fixtures) reads EVIDENCE_PATH / GOVERNANCE_DIR."""
        self._record("NEEDS_CHANGE")
        gov = self.root / ".governance"
        (gov / "plan-tracker.md").write_text("# plan\n", encoding="utf-8")
        with mock.patch.object(vw, "EVIDENCE_PATH", gov / "evidence-log.md"), \
             mock.patch.object(vw, "GOVERNANCE_DIR", gov), \
             mock.patch.object(vw, "SAMPLE_PATH", gov / "plan-tracker.md"):
            r = vw.check_review_machine_provenance()
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["verdict"], "PASS")


class InjectionAnchorExtensionTests(unittest.TestCase):
    """FIX-260: persona carries the 4th contract line; Check 33 anchor extended."""

    def test_persona_carries_review_record_contract(self):
        text = (
            vw.ROOT / "agent-presets/governance/agent.cordis.yml.template"
        ).read_text(encoding="utf-8")
        self.assertIn("审查结论必机录", text)
        self.assertIn("review-record", text)

    def test_injection_contract_anchors_include_review_record(self):
        self.assertIn(
            "review-record",
            vw.INJECTION_CONTRACT_ANCHORS["agent-presets/governance/agent.cordis.yml.template"],
        )
        # Real repo must satisfy the extended anchor set (Check 33 stays green).
        result = vw.check_injection_contract()
        self.assertEqual(result["issues"], [])

    def test_persona_contract_block_stays_within_budget(self):
        """FIX-253/FIX-274 budget: persona contract block ≤ 2.5KB.

        Originally 1.5KB (FIX-253, release-checklist-0.75.0); raised to
        2.5KB by FIX-274 / DEC-161 (2026-08-23) — M7.7 behavior-contract
        injection requires the headroom (audit P1-1 disposition; the M7.4
        contract-block budget was left unchanged, this budget covers the
        whole 关键行为契约→Git hooks block).
        """
        text = (
            vw.ROOT / "agent-presets/governance/agent.cordis.yml.template"
        ).read_text(encoding="utf-8")
        start = text.index("关键行为契约")
        end = text.index("Git hooks", start)
        block = text[start:end]
        self.assertLessEqual(len(block.encode("utf-8")), 2560,
                             "persona contract block exceeds the 2.5KB budget "
                             "(DEC-161 raise)")

    def test_skill_contract_section_stays_within_budget(self):
        """FIX-253/FIX-274 budget: entry SKILL 关键行为契约 section ≤ 4KB.

        DEC-144 set a 2KB hard cap for this section; raised to 2.5KB by
        FIX-274 / DEC-162 (2026-08-23, four-clause era); raised to 3.0KB
        by DEC-295(2) (2026-09-29, six-clause era — the B1a injection of
        clauses 5/6 (DEC-286(7)/DEC-291) added 448B of PERMANENT contract
        text; measured 2866 after the DEC-295-mandated intro slimming,
        +206B headroom); raised to 4.0KB by FEAT-090/FEAT-091
        (2026-10-09, nine-clause era — contract items 7/8/9 (M7.8:
        parallel-first dispatch / health-check eventization / hot-path
        single-source) + the FEAT-091 delta-revisit injection-face note
        on item 1; items landed in one-line trigger form (契约 v2:
        明细按需 — full text in behavior-protocol.md M7.8); measured 3686,
        +410B headroom — review-FEAT-090/091/092-R0 correction: the original
        3621/+475 reading predated the intro-line 九条 rewording (+65B)).
        Guard mirrors the persona-block test above (the
        persona budget stays at 2.5KB — different surface). DEC 回执由
        Coordinator 收口入 decision-log（本票 Developer 不写 .governance/）。
        """
        text = (
            vw.ROOT / "skills/software-project-governance/SKILL.md"
        ).read_text(encoding="utf-8")
        start = text.index("关键行为契约")
        end = text.index("产品代码 vs 治理记录边界", start)
        block = text[start:end]
        self.assertLessEqual(len(block.encode("utf-8")), 4096,
                             "SKILL 关键行为契约 section exceeds the 4.0KB "
                             "budget (FEAT-090/091 nine-clause era raise)")


class MachineRowClassificationTests(unittest.TestCase):
    """FIX-291 / FIX-281⑧：Check 30c 行分类（router 实证 10→13 递增）。

    缺陷机制（本仓 live 复现，2026-09-09 实测 35 WARN 中 27 行为误报）：

      · 行级 V7/V8 以全行 finditer 匹配 REVIEW- id——EVD-/RECO- 行的
        description **提及** REVIEW id（如「REVIEW-FIX-260-R0 已机录」）
        即被判为 review 行 → 新增交付行必然新增 WARN（无分类升级路径）；
      · V8 复审义务判定只看引用文件内 next_round 字段——同 task+round
        多角色机录（release R0 NEEDS_CHANGE + design R0 AWN 覆盖同号文件，
        live REL-070 实例）时字段已被终写覆盖，而 R+1 记录实际存在
        → 复审义务已履行仍入 WARN。

    修复 = 白名单/溯源分类：V7/V8 行级判定锚定 ID 列（REVIEW- 前缀），
    非 review 行（EVD-/RECO-/TRIAGE- 等）显式分类计数不入 WARN；
    R+1 轮记录存在时复审义务溯源为已履行（V8 豁免）。边界：现行
    手写 REVIEW- 行（无 marker） dated ≥ 生效日仍 WARN——不得放宽。
    """

    @staticmethod
    def _machine_row(task, round_n, result, date="2026-09-01"):
        return (
            "| REVIEW-{t}-R{n} | {t} | 治理记录 | review-record CLI 机器写入 "
            "review 结论记录（round {n}） | 事实依据：review-record 输出摘要"
            "（机器写入） | r.md; review-{t}-R{n}.md | rv | {d} | G11 | "
            "{r} |".format(t=task, n=round_n, r=result, d=date)
        )

    @staticmethod
    def _machine_file_text(task, round_n, result, date="2026-09-01",
                           include_next_round=True):
        lines = [
            "# Review Record (machine-written by review-record)",
            "",
            "- task: {0}".format(task),
            "- round: R{0}".format(round_n),
            "- date: {0}".format(date),
            "- reviewer: rv",
            "- report: r.md",
            "- wiring: pending",
            "",
            "**审查结论**: **{0}**".format(result),
        ]
        if result == "NEEDS_CHANGE" and include_next_round:
            lines += ["", "## 复审必达（NEEDS_CHANGE）", "",
                      "- next_round: REVIEW-{0}-R{1}".format(task, round_n + 1),
                      "- prev_report: r.md"]
        lines.append("")
        return "\n".join(lines)

    def test_evd_row_mentioning_review_id_is_not_judged(self):
        """EVD- 行（ID 列非 REVIEW-）description 提及 REVIEW id → 不入
        WARN，显式分类计数（红→绿：现行全行 finditer 判 V7）。
        FEAT-089: review_files={} 隔离 live 文件面（V6d 收紧后 undated
        live 文件会漏入 fixture 面）。"""
        row = (
            "| EVD-FIX-310 | FIX-310 | 产品代码 | 交付完成"
            "（REVIEW-FIX-310-R0 APPROVED_WITH_NOTES/0；审查链闭环） | "
            "事实依据：diff 逐行 | patch | Coordinator | 2026-09-01 | "
            "G11 | 完成 |"
        )
        r = vw.check_review_machine_provenance(review_rows=[row],
                                               review_files={})
        self.assertEqual(r["warnings"], [], r["warnings"])
        self.assertEqual(r["stats"].get("rows_non_review"), 1)

    def test_reco_machine_row_mentioning_review_id_is_not_judged(self):
        """RECO- 机器行（task-priority-analysis 产出）提及 REVIEW id →
        不入 WARN（红→绿——router「合法机器行新增即入 WARN」机制）。"""
        row = (
            "| RECO-FIX-311 | FIX-311 | 治理记录 | task-priority-analysis "
            "机器写入完成必推荐调用快照（trigger FIX-311；"
            "REVIEW-FIX-311-R0 已机录） | 事实依据：机器写入 | snapshot | "
            "Coordinator | 2026-09-01 | G11 | DONE |"
        )
        r = vw.check_review_machine_provenance(review_rows=[row],
                                               review_files={})
        self.assertEqual(r["warnings"], [], r["warnings"])
        self.assertEqual(r["stats"].get("rows_non_review"), 1)

    def test_row_id_cell_bold_markdown_still_anchors(self):
        """ID 列携带 markdown 修饰（**REVIEW-…**）仍锚定为 review 行。"""
        row = (
            "| **REVIEW-FIX-312-R0** | FIX-312 | 产品代码 | 手写审查记录 | "
            "依据 | patch | Code Reviewer | 2026-09-01 | G11 | "
            "APPROVED_WITH_NOTES |"
        )
        r = vw.check_review_machine_provenance(review_rows=[row])
        self.assertTrue(
            [v for v in r["violations"] if v["rule"] == "V7"], r["violations"])

    def test_needs_change_row_with_next_round_record_no_v8(self):
        """V8 溯源豁免：R0=NEEDS_CHANGE 机录行 + 同号文件被后续 R0 终写
        覆盖（无 next_round 字段）+ R1 机录行存在 → 复审义务已履行 →
        不入 WARN（红→绿——live REL-070 同型）。"""
        rows = [
            self._machine_row("FIX-313", 0, "NEEDS_CHANGE"),
            self._machine_row("FIX-313", 1, "APPROVED_WITH_NOTES"),
        ]
        files = {
            "review-FIX-313-R0.md": self._machine_file_text(
                "FIX-313", 0, "APPROVED_WITH_NOTES"),
            "review-FIX-313-R1.md": self._machine_file_text(
                "FIX-313", 1, "APPROVED_WITH_NOTES"),
        }
        r = vw.check_review_machine_provenance(review_rows=rows,
                                               review_files=files)
        self.assertEqual(r["warnings"], [], r["warnings"])

    def test_needs_change_row_without_next_round_record_still_fails_v8(self):
        """边界：R0=NEEDS_CHANGE 机录行 + 无 next_round 字段 + R1 记录
        不存在 → V8 FAIL 保持（复审义务未溯源——不得放宽；FEAT-089
        升级为 FAIL tier）。"""
        rows = [self._machine_row("FIX-314", 0, "NEEDS_CHANGE")]
        files = {
            "review-FIX-314-R0.md": self._machine_file_text(
                "FIX-314", 0, "APPROVED_WITH_NOTES"),
        }
        r = vw.check_review_machine_provenance(review_rows=rows,
                                               review_files=files)
        v8 = [v for v in r["violations"] if v["rule"] == "V8"]
        self.assertTrue(v8, r["violations"])

    def test_needs_change_file_with_next_round_record_no_v8(self):
        """V8 溯源豁免（文件级）：NEEDS_CHANGE 机录文件缺 next_round 字段
        但 R+1 行存在 → 不入 WARN（红→绿）。"""
        rows = [self._machine_row("FIX-315", 1, "APPROVED_WITH_NOTES")]
        files = {
            "review-FIX-315-R0.md": self._machine_file_text(
                "FIX-315", 0, "NEEDS_CHANGE", include_next_round=False),
        }
        r = vw.check_review_machine_provenance(review_rows=rows,
                                               review_files=files)
        self.assertEqual(r["warnings"], [], r["warnings"])

    def test_handwritten_review_row_still_fails_v7(self):
        """边界：现行手写 REVIEW- 行（ID 列 REVIEW-、dated ≥ 生效日、无
        marker、无豁免命中）→ V7 FAIL 保持（现行格式违规不得放宽）。"""
        r = vw.check_review_machine_provenance(review_rows=[HANDWRITTEN_ROW])
        self.assertEqual(r["verdict"], "FAIL")
        self.assertTrue(
            [v for v in r["violations"] if v["rule"] == "V7"
             and v["task_id"] == "FIX-300"], r["violations"])


class ReworkR1DischargeScopeTests(unittest.TestCase):
    """FIX-291 R1 返工（review-FIX-291-DESIGN-R0 P2-2 + CODE-R0 P3-3）：
    V8 R+1 溯源豁免从存在性判定收紧为「有效且时序合法的 R+1 记录」。

    P2-2：豁免须校验 R+1 记录日期 ≥ R+0（NEEDS_CHANGE）记录日期——早于
    NEEDS_CHANGE 写入的同号历史轮（task+round 命名冲突）不得豁免现行复审
    义务；conclusion=UNKNOWN 的 R+1 记录不可溯源为「有效复审」——不豁免。
    """

    @staticmethod
    def _machine_row(task, round_n, result, date="2026-09-01",
                     conclusion_cell=None):
        return (
            "| REVIEW-{t}-R{n} | {t} | 治理记录 | review-record CLI 机器写入 "
            "review 结论记录（round {n}） | 事实依据：review-record 输出摘要"
            "（机器写入） | r.md; review-{t}-R{n}.md | rv | {d} | G11 | "
            "{c} |".format(t=task, n=round_n,
                           c=conclusion_cell if conclusion_cell is not None
                           else result, d=date)
        )

    @staticmethod
    def _machine_file_text(task, round_n, result, date="2026-09-01"):
        lines = [
            "# Review Record (machine-written by review-record)",
            "",
            "- task: {0}".format(task),
            "- round: R{0}".format(round_n),
            "- date: {0}".format(date),
            "- reviewer: rv",
            "- report: r.md",
            "- wiring: pending",
            "",
            "**审查结论**: **{0}**".format(result),
        ]
        lines.append("")
        return "\n".join(lines)

    def test_older_next_round_record_does_not_discharge_v8(self):
        """红→绿：R+1 记录 dated 2026-08-01 早于 R0 NEEDS_CHANGE
        （2026-09-05）——同号历史轮命名冲突形态 → 不豁免，V8 FAIL。"""
        rows = [
            self._machine_row("FIX-320", 0, "NEEDS_CHANGE",
                              date="2026-09-05"),
            self._machine_row("FIX-320", 1, "APPROVED_WITH_NOTES",
                              date="2026-08-01"),
        ]
        files = {
            "review-FIX-320-R0.md": self._machine_file_text(
                "FIX-320", 0, "APPROVED_WITH_NOTES", date="2026-09-05"),
            "review-FIX-320-R1.md": self._machine_file_text(
                "FIX-320", 1, "APPROVED_WITH_NOTES", date="2026-08-01"),
        }
        r = vw.check_review_machine_provenance(review_rows=rows,
                                               review_files=files)
        v8 = [v for v in r["violations"] if v["rule"] == "V8"]
        self.assertTrue(v8, r["violations"])

    def test_unknown_conclusion_next_round_does_not_discharge_v8(self):
        """红→绿：R+1 记录 conclusion 不可解析（空结论列 → UNKNOWN）→
        非有效复审记录 → 不豁免，V8 FAIL。"""
        rows = [
            self._machine_row("FIX-321", 0, "NEEDS_CHANGE",
                              date="2026-09-01"),
            self._machine_row("FIX-321", 1, "", date="2026-09-02",
                              conclusion_cell=""),
        ]
        files = {
            "review-FIX-321-R0.md": self._machine_file_text(
                "FIX-321", 0, "APPROVED_WITH_NOTES"),
        }
        r = vw.check_review_machine_provenance(review_rows=rows,
                                               review_files=files)
        v8 = [v for v in r["violations"] if v["rule"] == "V8"]
        self.assertTrue(v8, r["violations"])

    def test_dated_valid_next_round_still_discharges_v8(self):
        """绿保持（回归锚定）：R+1 记录 dated ≥ R0 且结论有效 → 豁免
        保持（live REL-070 形态）。"""
        rows = [
            self._machine_row("FIX-322", 0, "NEEDS_CHANGE",
                              date="2026-09-01"),
            self._machine_row("FIX-322", 1, "APPROVED_WITH_NOTES",
                              date="2026-09-02"),
        ]
        files = {
            "review-FIX-322-R0.md": self._machine_file_text(
                "FIX-322", 0, "APPROVED_WITH_NOTES"),
            "review-FIX-322-R1.md": self._machine_file_text(
                "FIX-322", 1, "APPROVED_WITH_NOTES", date="2026-09-02"),
        }
        r = vw.check_review_machine_provenance(review_rows=rows,
                                               review_files=files)
        self.assertEqual(r["warnings"], [], r["warnings"])

    def test_file_level_discharge_also_checks_date_order(self):
        """文件级豁免同步收紧：R0=NEEDS_CHANGE 文件缺 next_round + 更早
        的 R1 文件（2026-08-01 < R0 2026-09-05）→ V8 FAIL。"""
        rows = []
        files = {
            "review-FIX-323-R0.md": self._machine_file_text(
                "FIX-323", 0, "NEEDS_CHANGE", date="2026-09-05"),
            "review-FIX-323-R1.md": self._machine_file_text(
                "FIX-323", 1, "APPROVED_WITH_NOTES", date="2026-08-01"),
        }
        r = vw.check_review_machine_provenance(review_rows=rows,
                                               review_files=files)
        v8 = [v for v in r["violations"] if v["rule"] == "V8"]
        self.assertTrue(v8, r["violations"])


class ReworkR2IndexSemanticsTests(unittest.TestCase):
    """FIX-291 R2 返工（review-FIX-291-CODE-R1 P3-5 ≡ DESIGN-R1 P3-R1-b）：
    ``known_rounds`` 合并语义解耦——max-date + OR-valid 的归并边角。

    复合误放行形态：R+1 的唯一**有效**记录 dated 早于 base，同轮另有较新
    的 UNKNOWN 记录——归并后 (date=最新, valid=True) 通过豁免，但任一
    单记录自身均不满足「有效 ∧ dated ≥ base」。修复 = 逐记录精确判定
    （exists record: valid ∧ date ≥ base_date）。
    """

    @staticmethod
    def _machine_row(task, round_n, result, date="2026-09-01",
                     conclusion_cell=None):
        return (
            "| REVIEW-{t}-R{n} | {t} | 治理记录 | review-record CLI 机器写入 "
            "review 结论记录（round {n}） | 事实依据：review-record 输出摘要"
            "（机器写入） | r.md; review-{t}-R{n}.md | rv | {d} | G11 | "
            "{c} |".format(t=task, n=round_n,
                           c=conclusion_cell if conclusion_cell is not None
                           else result, d=date)
        )

    @staticmethod
    def _machine_file_text(task, round_n, result, date="2026-09-01"):
        lines = [
            "# Review Record (machine-written by review-record)",
            "",
            "- task: {0}".format(task),
            "- round: R{0}".format(round_n),
            "- date: {0}".format(date),
            "- reviewer: rv",
            "- report: r.md",
            "- wiring: pending",
            "",
            "**审查结论**: **{0}**".format(result),
        ]
        lines.append("")
        return "\n".join(lines)

    def test_composite_valid_old_plus_unknown_new_not_discharged(self):
        """红→绿：R+1 有效记录 dated 2026-08-01（< base 2026-09-05）+
        同轮较新 UNKNOWN 记录（2026-09-10）——归并式误放行，逐记录式
        拒绝 → V8 FAIL。"""
        rows = [
            self._machine_row("FIX-330", 0, "NEEDS_CHANGE",
                              date="2026-09-05"),
            # 唯一有效 R+1 记录，但早于 base。
            self._machine_row("FIX-330", 1, "APPROVED_WITH_NOTES",
                              date="2026-08-01"),
            # 较新的同轮记录，但结论不可解析。
            self._machine_row("FIX-330", 1, "", date="2026-09-10",
                              conclusion_cell=""),
        ]
        files = {
            "review-FIX-330-R0.md": self._machine_file_text(
                "FIX-330", 0, "APPROVED_WITH_NOTES", date="2026-09-05"),
        }
        r = vw.check_review_machine_provenance(review_rows=rows,
                                               review_files=files)
        v8 = [v for v in r["violations"] if v["rule"] == "V8"]
        self.assertTrue(v8, r["violations"])

    def test_single_valid_dated_record_still_discharges(self):
        """绿保持：单条有效且 dated ≥ base 的 R+1 记录 → 豁免（逐记录式
        与归并式同判——回归锚定）。"""
        rows = [
            self._machine_row("FIX-331", 0, "NEEDS_CHANGE",
                              date="2026-09-01"),
            self._machine_row("FIX-331", 1, "APPROVED_WITH_NOTES",
                              date="2026-09-02"),
        ]
        files = {
            "review-FIX-331-R0.md": self._machine_file_text(
                "FIX-331", 0, "APPROVED_WITH_NOTES"),
        }
        r = vw.check_review_machine_provenance(review_rows=rows,
                                               review_files=files)
        self.assertEqual(r["warnings"], [], r["warnings"])


class Check30cFailEscalationTests(unittest.TestCase):
    """FEAT-089 / DEC-146 ② —— Check 30c WARN→FAIL 升级批语义锁定。

    DEC-146 ②（archive/decisions L73）三动作的本票兑现：

      1. FAIL 升级——dated-on/after-生效日 无机器标记的 REVIEW 记录
         （V7）与缺 next_round 的 NEEDS_CHANGE 记录（V8）从 WARN 升级
         为 FAIL（violations，计入 all_issues）；单向棘轮不回退。
      2. V6d 收紧——「无日期记录不判」口径收紧为「无日期即 WARN」
         （V6d finding：无法证明是生效日前的记录一律 WARN，不判 FAIL
         ——日期未知不构成机器来源违规的确定性事实）。
      3. DEC 豁免清单——REVIEW-FIX-256/258-CODE-R0（2026-08-22 生效日
         当日残留手写行，DEC-321 预登记首批入册）经清单登记豁免：
         不回写不改写历史行、不走 review-record 补录（DEC-321 禁补录
         ——补录将伪化持久化时点并使覆盖率提前达 100%）。

    升级条件判定面（DEC-146 ②：覆盖率 100% × ≥2 发布版本）在
    stats["escalation"] 显式可复算（coverage_raw / coverage_exemption_
    honored / releases_since_effective_date / condition_met）。
    """

    # 形态镜像 live 手写行（evidence-log ID cell 原文，2026-08-22）：
    # V7 判定从 ID cell 提取的规范化 task id = "FIX-256"（ROLE 段不进
    # 匹配键——record_id 仅作人读锚）。结论列镜像 live 原文
    # （unresolved_blockers=0 —— APPROVED_WITH_NOTES 族，无 V8 面）。
    EXEMPT_ROW_FX256 = (
        "| REVIEW-FIX-256-CODE-R0 | FIX-256 | 产品代码 | Code Review R0"
        "（独立 Reviewer，2026-08-22）：APPROVED_WITH_NOTES | 事实依据："
        "diff 逐行 | r0.md | Code Reviewer | 2026-08-22 | G11 | "
        "APPROVED_WITH_NOTES | unresolved_blockers=0 |"
    )
    EXEMPT_ROW_FX258 = (
        "| REVIEW-FIX-258-CODE-R0 | FIX-258 | 产品代码 | Code Review R0"
        "（独立 Reviewer，2026-08-22）：APPROVED_WITH_NOTES | 事实依据："
        "diff 逐行 | r0.md | Code Reviewer | 2026-08-22 | G11 | "
        "APPROVED_WITH_NOTES | unresolved_blockers=0 |"
    )

    # ── 1. 豁免命中：清单登记行被吸收，不产生 finding ──────────────────

    def test_exempted_row_absorbed_no_violation(self):
        """豁免命中：FIX-256 手写行（2026-08-22，无 marker）→ 无 V7
        finding，计入 stats.rows_exempted（exemption-honored 覆盖率）。"""
        r = vw.check_review_machine_provenance(
            review_rows=[self.EXEMPT_ROW_FX256], review_files={})
        self.assertEqual(r["violations"], [], r["violations"])
        self.assertEqual(r["warnings"], [], r["warnings"])
        self.assertEqual(r["stats"]["rows_exempted"], 1)
        self.assertEqual(r["verdict"], "PASS")

    def test_both_exempted_rows_absorbed(self):
        """DEC-321 首批入册两行（FIX-256/258-CODE-R0）全部命中。"""
        r = vw.check_review_machine_provenance(
            review_rows=[self.EXEMPT_ROW_FX256, self.EXEMPT_ROW_FX258],
            review_files={})
        self.assertEqual(r["violations"], [], r["violations"])
        self.assertEqual(r["stats"]["rows_exempted"], 2)

    # ── 2. 豁免未命中：键不匹配即 FAIL（豁免不是模糊赦免） ─────────────

    def test_exemption_miss_wrong_date_fails(self):
        """日期不匹配（2026-08-23 ≠ 登记日 2026-08-22）→ V7 FAIL——
        豁免按 (task, date) 精确匹配，不得吸收其他日期的同任务行。"""
        row = self.EXEMPT_ROW_FX256.replace("2026-08-22", "2026-08-23")
        r = vw.check_review_machine_provenance(review_rows=[row],
                                               review_files={})
        v7 = [v for v in r["violations"] if v["rule"] == "V7"]
        self.assertTrue(v7, r["violations"])
        self.assertEqual(r["stats"]["rows_exempted"], 0)
        self.assertEqual(r["verdict"], "FAIL")

    def test_exemption_miss_wrong_task_fails(self):
        """任务不匹配（FIX-999 ≠ FIX-256/258）→ V7 FAIL。"""
        row = self.EXEMPT_ROW_FX256.replace("FIX-256", "FIX-999")
        r = vw.check_review_machine_provenance(review_rows=[row],
                                               review_files={})
        v7 = [v for v in r["violations"] if v["rule"] == "V7"]
        self.assertTrue(v7, r["violations"])

    def test_exemption_miss_machine_row_not_consumed(self):
        """机器行不消耗豁免额度（豁免只吸收 non-machine 判定）。"""
        machine_fx256 = self.EXEMPT_ROW_FX256.replace(
            "Code Review R0（独立 Reviewer，2026-08-22）：APPROVED_WITH_NOTES",
            "review-record CLI 机器写入 review 结论记录（round 0）")
        r = vw.check_review_machine_provenance(
            review_rows=[machine_fx256, self.EXEMPT_ROW_FX256],
            review_files={})
        self.assertEqual(r["violations"], [], r["violations"])
        self.assertEqual(r["stats"]["rows_machine"], 1)
        self.assertEqual(r["stats"]["rows_exempted"], 1)

    # ── 3. V6d 收紧：无日期即 WARN（不判 FAIL） ─────────────────────────

    def test_undated_row_warns_not_fails(self):
        """无日期 REVIEW 行 → V6d WARN（非 FAIL——日期未知不是机器来源
        违规的确定性事实；WARN 不计入 all_issues）。"""
        undated = HANDWRITTEN_ROW.replace("2026-09-01", "")
        r = vw.check_review_machine_provenance(review_rows=[undated])
        self.assertEqual(r["verdict"], "WARN")
        rules = {w["rule"] for w in r["warnings"]}
        self.assertEqual(rules, {"V6d"})
        self.assertEqual(r["violations"], [])

    def test_undated_file_warns_v6d(self):
        """无日期 CLI 命名 review 文件 → V6d WARN（同一收紧口径）。"""
        body = self._undated_file_body()
        r = vw.check_review_machine_provenance(
            review_rows=[],
            review_files={"review-FIX-500-R0.md": body})
        self.assertEqual(r["verdict"], "WARN")
        rules = {w["rule"] for w in r["warnings"]}
        self.assertEqual(rules, {"V6d"})
        self.assertEqual(r["stats"]["files_undated"], 1)
        self.assertEqual(r["violations"], [])

    @staticmethod
    def _undated_file_body():
        return (
            "# Review Record (machine-written by review-record)\n"
            "\n"
            "- task: FIX-500\n"
            "- round: R0\n"
            "- date: ?\n"
            "- reviewer: rv\n"
            "- report: r.md\n"
            "- wiring: pending\n"
            "\n"
            "**审查结论**: **APPROVED**\n"
        )

    # ── 4. 升级判定面：100% × ≥2 发布版本显式可复算 ────────────────────

    def test_escalation_stats_recomputable(self):
        """stats["escalation"] 携带可复算判定面：coverage_raw /
        coverage_exemption_honored（分子分母显式）/ releases_since_
        effective_date / condition_met（100% ∧ ≥2）。"""
        r = vw.check_review_machine_provenance(
            review_rows=[self.EXEMPT_ROW_FX256], review_files={})
        esc = r["stats"]["escalation"]
        self.assertTrue(esc["active"])
        self.assertEqual(esc["effective_date"], "2026-08-22")
        # exemption-honored 覆盖率 = (machine + exempted) / judged = 1/1。
        honored = esc["coverage_exemption_honored"]
        self.assertEqual(honored["numerator"], 1)
        self.assertEqual(honored["denominator"], 1)
        self.assertEqual(honored["pct"], 100.0)
        # raw 覆盖率不含豁免（0/1）。
        self.assertEqual(esc["coverage_raw"]["numerator"], 0)
        self.assertEqual(esc["coverage_raw"]["denominator"], 1)
        self.assertGreaterEqual(esc["releases_since_effective_date"], 2)
        self.assertTrue(esc["condition_met"])

    def test_released_versions_since_injectable(self):
        """release-ledger 计数可注入复算（临时 ledger fixture：生效日
        后 2 个 released 版本 → 2；生效日前的 released 不计；非 released
        不计；withdrawn 不计）。"""
        import json as _json
        with tempfile.TemporaryDirectory(prefix="r089_") as td:
            ledger = Path(td)
            (ledger / "0.10.0.json").write_text(_json.dumps({
                "version": "0.10.0", "lifecycle_state": "released",
                "effective_state": {"lifecycle_state": "released",
                                    "withdrawn": False},
                "events": [{"type": "candidate_to_released",
                            "recorded_at": "2026-09-01T00:00:00Z"}],
            }), encoding="utf-8")
            (ledger / "0.11.0.json").write_text(_json.dumps({
                "version": "0.11.0", "lifecycle_state": "released",
                "effective_state": {"lifecycle_state": "released",
                                    "withdrawn": False},
                "events": [{"type": "candidate_to_released",
                            "recorded_at": "2026-09-15T00:00:00Z"}],
            }), encoding="utf-8")
            # 生效日前 released → 不计。
            (ledger / "0.09.0.json").write_text(_json.dumps({
                "version": "0.09.0", "lifecycle_state": "released",
                "effective_state": {"lifecycle_state": "released",
                                    "withdrawn": False},
                "events": [{"type": "candidate_to_released",
                            "recorded_at": "2026-08-01T00:00:00Z"}],
            }), encoding="utf-8")
            # candidate（未 released）→ 不计。
            (ledger / "0.12.0.json").write_text(_json.dumps({
                "version": "0.12.0", "lifecycle_state": "candidate",
                "effective_state": {"lifecycle_state": "candidate",
                                    "withdrawn": False},
                "events": [{"type": "declared_candidate",
                            "recorded_at": "2026-09-20T00:00:00Z"}],
            }), encoding="utf-8")
            # withdrawn → 不计。
            (ledger / "0.13.0.json").write_text(_json.dumps({
                "version": "0.13.0", "lifecycle_state": "released",
                "effective_state": {"lifecycle_state": "released",
                                    "withdrawn": True},
                "events": [{"type": "candidate_to_released",
                            "recorded_at": "2026-09-25T00:00:00Z"}],
            }), encoding="utf-8")
            from checks.review_domain import _released_versions_since
            n = _released_versions_since(
                __import__("checks.review_domain", fromlist=["x"])
                .REQ107_MACHINE_PROVENANCE_DATE,
                releases_dir=ledger)
            self.assertEqual(n, 2)

    def test_condition_unmet_when_coverage_below_100(self):
        """覆盖率 <100%（未豁免手写行在库）→ condition_met=False（判定
        面如实反映，FAIL 由该行自身的 V7 violation 承载）。"""
        r = vw.check_review_machine_provenance(review_rows=[HANDWRITTEN_ROW],
                                               review_files={})
        esc = r["stats"]["escalation"]
        self.assertEqual(esc["coverage_exemption_honored"]["pct"], 0.0)
        self.assertFalse(esc["condition_met"])
        self.assertEqual(r["verdict"], "FAIL")

    # ── 5. DEC-146 ④：不可伪造 JSON 侧记录（change-triage 式） ─────────

    def test_side_record_verifies_live_registry(self):
        """侧记录（infra/checks/review_exemptions_30c.json）的
        exemptions_sha256 与 exception_registry 清单 canonical hash 一致
        → stats.escalation.side_record.verified=True，无 finding。"""
        r = vw.check_review_machine_provenance(
            review_rows=[self.EXEMPT_ROW_FX256], review_files={})
        self.assertTrue(r["stats"]["escalation"]["side_record"]["verified"])
        self.assertEqual(r["violations"], [])

    def test_side_record_hash_mismatch_fails_closed(self):
        """fail-closed：豁免清单被篡改（mock 追加条目）→ 清单 hash 与
        侧记录不一致 → EXEMPTION-SIDE-RECORD violation（FAIL）——清单
        漂移不可静默生效（DEC-146 ④ 侧记录的执法点）。"""
        import exception_registry
        tampered = list(exception_registry.REVIEW_PROVENANCE_EXEMPTIONS) + [{
            "id": "EXEMPT-30C-FAKE", "check": "30c",
            "record_id": "REVIEW-FIX-666-CODE-R0", "task_id": "FIX-666",
            "record_date": "2026-09-30", "rule": "V7", "face": "row",
            "approved_by": "forged", "registered_in": "forged",
            "note": "tamper probe",
        }]
        with mock.patch.object(exception_registry,
                               "REVIEW_PROVENANCE_EXEMPTIONS", tampered):
            r = vw.check_review_machine_provenance(review_rows=[])
        sr = [v for v in r["violations"]
              if v["rule"] == "EXEMPTION-SIDE-RECORD"]
        self.assertTrue(sr, r["violations"])
        self.assertEqual(r["verdict"], "FAIL")
        self.assertFalse(r["stats"]["escalation"]["side_record"]["verified"])

    def test_exempted_rows_require_registry_marker_shape(self):
        """豁免条目结构契约：每条必含 id/task_id/record_date/rule/face/
        approved_by/registered_in（结构漂移在 exception_registry 侧
        fail-closed——清单加载即校验）。"""
        import exception_registry
        for entry in exception_registry.REVIEW_PROVENANCE_EXEMPTIONS:
            for field in ("id", "record_id", "task_id", "record_date",
                          "rule", "face", "approved_by", "registered_in"):
                self.assertIn(field, entry, entry)
            self.assertEqual(entry["task_id"], "FIX-256"
                             if "FIX-256" in entry["record_id"]
                             else "FIX-258")
            self.assertEqual(entry["record_date"], "2026-08-22")
        self.assertEqual(
            len(exception_registry.REVIEW_PROVENANCE_EXEMPTIONS), 2)


if __name__ == "__main__":
    unittest.main()
