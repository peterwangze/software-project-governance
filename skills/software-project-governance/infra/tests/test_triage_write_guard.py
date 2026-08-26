"""FIX-278 G3 — change-triage write-time structure guard (Check 14 写时触发).

AUDIT-148 §4.2: reasoning-level 的 MAINT-017 入账后，plan-tracker 结构在
「无复核窗口」静默恶化（17:07 [PASS] → 08-26 17 issues, Check 14 structural
+ blocking）——任务入账/机器写入后没有结构合法性自动复核（Check 14 无写钩子）。
FIX-278 G3 落地为 change-triage CLI 机器写入后的 write guard：
（1）写入的证据行必须匹配 evidence-log 已确立的列数契约（Check 14
    ``evidence_col_mismatch`` 规则，按写入文件范围化）;
（2）写入的 triage 记录 JSON 必须可解析。
guard 失败 → ``change-triage`` 退出码 2（fail-closed：结构性破坏不得静默
引入）。

Scope 契约（write guard, not repo guard）：只判定本写入涉及的产物——
治理目录中既有结构问题不阻塞入账（fail-safe 到写入者自己的产物）。

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_triage_write_guard.py -v
"""

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw  # noqa: E402
import change_triage as ct  # noqa: E402

_FIXTURE_TRACKER = """\
# Plan Tracker

## 版本规划

### 版本路线图

| 版本 | 状态 | 预计日期 | 核心范围 |
|------|------|---------|---------|
| **0.77.0** | **已发布** | 2026-08-25 | baseline |
| **0.78.0** | **规划** | 2026-08+ | FIX-278 |

### 优先级一览

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| **P1** | FIX-100 | done task | — | 0.77.0 | closed | ✅ 完成 |
"""


def _evidence_row_10(evd_id="EVD-001", task="FIX-100"):
    cells = [evd_id, task, "开发", "实现", "依据", "产物", "actor",
             "2026-08-25", "G11", "PASS"]
    return "| " + " | ".join(cells) + " |\n"


def _triage_row(record_id, cols):
    """Build a ``| TRIAGE-... |`` row with exactly ``cols`` semantic cells."""
    tid = record_id
    if tid.upper().startswith("TRIAGE-"):
        tid = tid[len("TRIAGE-"):]
    cells = ["TRIAGE-" + tid]
    for i in range(1, cols):
        cells.append("c{0}".format(i))
    return "| " + " | ".join(cells) + " |\n"


def _evidence_row_9(evd_id="EVD-800", task="FIX-100"):
    """Real EVD row shape (9 cells — repo evidence-log first EVD row EVD-879).

    FIX-279: the EVD row family is a 9/10/11-col manual mix (first row 9
    cols), while the TRIAGE machine row family is uniformly 10 cols. The
    column contract must NOT be derived from the EVD family.
    """
    cells = [evd_id, task, "维护", "描述", "事实依据：x",
             "artifact", "actor", "2026-08-26", "✅ 完成"]
    return "| " + " | ".join(cells) + " |\n"


def _run_triage_into(gov_dir, records_dir=None, evidence_path=None):
    """Run ct.run_triage against a fresh fixture governance dir."""
    if evidence_path is None:
        evidence_path = Path(gov_dir) / "evidence-log.md"
        evidence_path.write_text(_evidence_row_10() + _evidence_row_10("EVD-002"),
                                 encoding="utf-8")
    return ct.run_triage(
        task_id="FIX-278",
        title="治理降噪第一批",
        priority="P1",
        target_version="0.78.0",
        depends_on="",
        files=["skills/software-project-governance/infra/x.py"],
        reason="write-guard fixture",
        plan_tracker_text=_FIXTURE_TRACKER,
        current_version="0.77.0",
        governance_dir=str(gov_dir),
        records_dir=records_dir,
        evidence_path=evidence_path,
    )


class WriteStructureGuardUnitTests(unittest.TestCase):
    """Write-scoped structural validation over the written artifacts."""

    def test_clean_machine_write_passes_guard(self):
        """机器写入（record + evidence row）后 guard 0 问题（G3 写时触发绿灯；
        FIX-278 自身入账路径的契约）。"""
        with tempfile.TemporaryDirectory() as td:
            summary = _run_triage_into(td)
            self.assertTrue(summary["evidence_row_written"])
            issues = vw._triage_write_structure_guard(
                Path(td) / "evidence-log.md", summary["record_path"])
            self.assertEqual(issues, [])

    def test_guard_detects_column_break_in_written_evidence(self):
        """写入证据行列数与证据日志标准不一致 → guard 报 column-mismatch
        （Check 14 evidence_col_mismatch 规则——写时触发点拦截）。"""
        with tempfile.TemporaryDirectory() as td:
            evidence = Path(td) / "evidence-log.md"
            evidence.write_text(_evidence_row_10() + "| TRIAGE-FIX-278 | FIX-278 | 变更控制 |\n",
                                encoding="utf-8")
            record = Path(td) / "FIX-278.json"
            record.write_text('{"schema_version": 1}', encoding="utf-8")
            issues = vw._triage_write_structure_guard(evidence, record)
            self.assertEqual(len(issues), 1)
            self.assertIn("TRIAGE-FIX-278", issues[0])
            self.assertIn("columns", issues[0])

    def test_guard_detects_invalid_record_json(self):
        """写入的 triage 记录 JSON 不可解析 → guard 报错（写入原子性看护）。"""
        with tempfile.TemporaryDirectory() as td:
            evidence = Path(td) / "evidence-log.md"
            evidence.write_text(
                _evidence_row_10() + _triage_row("TRIAGE-FIX-278", 10),
                encoding="utf-8")
            record = Path(td) / "FIX-278.json"
            record.write_text("{not json", encoding="utf-8")
            issues = vw._triage_write_structure_guard(evidence, record)
            self.assertTrue(
                any("record JSON invalid" in i for i in issues), issues)

    def test_guard_scope_ignores_unrelated_preexisting_issues(self):
        """Write-guard 契约：只判定本写入产物——治理目录中既有的其它结构
        问题（如 plan-tracker 表格失衡）不阻塞机器入账（fail-safe 到写入
        者自己的产物）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            broken_tracker = gov / "plan-tracker.md"
            broken_tracker.write_text(
                "| A | B |\n|---|\n| only-two | cols | here | extra |\n",
                encoding="utf-8")
            summary = _run_triage_into(gov, records_dir=gov / "change-triage")
            issues = vw._triage_write_structure_guard(
                gov / "evidence-log.md", summary["record_path"])
            self.assertEqual(issues, [])

    def test_guard_validates_newly_written_row_when_prior_triage_exists(self):
        """P0-1 回归（false-pass 主场景）：既有合法 TRIAGE-OLD 行 + 刚写入
        的破坏行（列数错）→ guard MUST 报错（按写入行 ID 匹配，而非首个
        TRIAGE 行——G3 目标的常用路径不得失守）。"""
        with tempfile.TemporaryDirectory() as td:
            evidence = Path(td) / "evidence-log.md"
            evidence.write_text(
                _evidence_row_10("EVD-001")           # EVD 标准 10 列
                + _triage_row("TRIAGE-OLD", 10)       # 既有合法 TRIAGE 行
                + _triage_row("TRIAGE-FIX-278", 8),   # 刚写入的破坏行（缺列）
                encoding="utf-8")
            record = Path(td) / "change-triage" / "FIX-278.json"
            record.parent.mkdir()
            record.write_text('{"ok": true}', encoding="utf-8")
            issues = vw._triage_write_structure_guard(
                evidence, record, record_id="TRIAGE-FIX-278")
            self.assertEqual(len(issues), 1, issues)
            self.assertIn("TRIAGE-FIX-278", issues[0])

    def test_guard_blocks_write_when_first_triage_row_defines_family_standard(self):
        """FIX-279 契约再基线（原 P0-1 false-fail 场景）：首个（非本次写入）
        TRIAGE 行即行族标准——旧格式 8 列首行确立行族契约 8，刚写入的 10 列
        行与行族标准不符 → guard MUST 报错（行族标准权威于 EVD 首行；行 ID
        匹配保持）。FIX-278 时代以 EVD 首行（10 列）为标准放行——该错配正是
        FIX-279 根因（活体验证：合法 10 列机器行被 EVD 首行 9 列误报——
        TRIAGE-REL-071/TRIAGE-FIX-279 两次触发）。"""
        with tempfile.TemporaryDirectory() as td:
            evidence = Path(td) / "evidence-log.md"
            evidence.write_text(
                _evidence_row_10("EVD-001")
                + _triage_row("TRIAGE-OLD", 8)        # 首个非写入 TRIAGE 行
                                                      # = 行族标准 8 列
                + _triage_row("TRIAGE-FIX-278", 10),
                encoding="utf-8")
            record = Path(td) / "change-triage" / "FIX-278.json"
            record.parent.mkdir()
            record.write_text('{"ok": true}', encoding="utf-8")
            issues = vw._triage_write_structure_guard(
                evidence, record, record_id="TRIAGE-FIX-278")
            self.assertEqual(len(issues), 1, issues)
            self.assertIn("TRIAGE-FIX-278", issues[0])


class TriageFamilyColumnContractTests(unittest.TestCase):
    """FIX-279 — TRIAGE 行族列数契约：标准取行族自身，而非 EVD 首行。

    根因：guard 的 standard_cols 取自第一条 ``| EVD-`` 行（本仓 EVD 行=9/10/11
    混合列，首行 9 列），而写入的 TRIAGE 机器行=10 列——每次合法 change-triage
    入账必误报 fail-closed exit 2（活体验证：TRIAGE-REL-071 与 TRIAGE-FIX-279
    两次触发）。修复后标准取第一条非本次写入的 TRIAGE 行（行族标准），行族缺失
    fallback 到 EVD 基线，仍缺则跳过列数比较；行 ID 匹配与「写入行缺失显式
    报错」保持（P0-1 不得回退）。
    """

    def _write_fixture(self, td, written_cols):
        """9 列 EVD 基线 + 10 列 TRIAGE 行族 + 写入行（written_cols 列）。"""
        evidence = Path(td) / "evidence-log.md"
        written = _triage_row("TRIAGE-FIX-279", written_cols)
        evidence.write_text(
            _evidence_row_9("EVD-800", "FIX-100")
            + _triage_row("TRIAGE-OLD", 10)
            + written,
            encoding="utf-8")
        record = Path(td) / "change-triage" / "FIX-279.json"
        record.parent.mkdir()
        record.write_text('{"ok": true}', encoding="utf-8")
        return evidence, record

    def test_mixed_file_legal_triage_row_no_false_positive(self):
        """(a) 混合文件（9 列 EVD 行 + 10 列 TRIAGE 行族）——合法 TRIAGE 写入
        0 误报（FIX-279 主修复：EVD 首行不得作 TRIAGE 行族的列数标准）。"""
        with tempfile.TemporaryDirectory() as td:
            evidence, record = self._write_fixture(td, 10)
            issues = vw._triage_write_structure_guard(
                evidence, record, record_id="TRIAGE-FIX-279")
            self.assertEqual(issues, [])

    def test_mixed_file_broken_nine_col_write_reported(self):
        """(b) 破坏行（写入 9 列 TRIAGE 行）仍报错——行族标准 10 vs 写入 9。"""
        with tempfile.TemporaryDirectory() as td:
            evidence, record = self._write_fixture(td, 9)
            issues = vw._triage_write_structure_guard(
                evidence, record, record_id="TRIAGE-FIX-279")
            self.assertEqual(len(issues), 1, issues)
            self.assertIn("TRIAGE-FIX-279", issues[0])

    def test_mixed_file_broken_eleven_col_write_reported(self):
        """(b) 破坏行（写入 11 列 TRIAGE 行）仍报错——行族标准 10 vs 写入 11。"""
        with tempfile.TemporaryDirectory() as td:
            evidence, record = self._write_fixture(td, 11)
            issues = vw._triage_write_structure_guard(
                evidence, record, record_id="TRIAGE-FIX-279")
            self.assertEqual(len(issues), 1, issues)
            self.assertIn("TRIAGE-FIX-279", issues[0])

    def test_evd_baseline_fallback_when_triage_family_absent(self):
        """TRIAGE 行族缺失（旧库）→ fallback 到 EVD 基线：与基线一致的写入
        放行（9 列 EVD 基线 vs 9 列首写——兼容旧库契约）；破坏性首写不得以
        自身为标准（fallback 比较，见既有 test_guard_detects_column_break_
        in_written_evidence）。"""
        with tempfile.TemporaryDirectory() as td:
            evidence = Path(td) / "evidence-log.md"
            evidence.write_text(
                _evidence_row_9("EVD-800", "FIX-100")
                + _triage_row("TRIAGE-FIX-279", 9),
                encoding="utf-8")
            record = Path(td) / "change-triage" / "FIX-279.json"
            record.parent.mkdir()
            record.write_text('{"ok": true}', encoding="utf-8")
            issues = vw._triage_write_structure_guard(
                evidence, record, record_id="TRIAGE-FIX-279")
            self.assertEqual(issues, [])

    def test_no_family_rows_skips_column_comparison(self):
        """既无 TRIAGE 行族也无 EVD 行 → 跳过列数比较（仅 JSON/缺失行检查
        生效——「仍缺则跳过」契约）。"""
        with tempfile.TemporaryDirectory() as td:
            evidence = Path(td) / "evidence-log.md"
            evidence.write_text(_triage_row("TRIAGE-FIX-279", 3),
                                encoding="utf-8")
            record = Path(td) / "change-triage" / "FIX-279.json"
            record.parent.mkdir()
            record.write_text('{"ok": true}', encoding="utf-8")
            issues = vw._triage_write_structure_guard(
                evidence, record, record_id="TRIAGE-FIX-279")
            self.assertEqual(issues, [])

    def test_legacy_family_standard_accepts_matching_write(self):
        """行族权威：首行旧格式（8 列，≠EVD 9 列基线）确立行族标准 8；写入
        与行族标准一致（8 列）→ 放行（行族选定后 EVD 不参与比较——与自身
        行族一致的写入不被旧格式行阻塞）。"""
        with tempfile.TemporaryDirectory() as td:
            evidence = Path(td) / "evidence-log.md"
            evidence.write_text(
                _evidence_row_9("EVD-800", "FIX-100")
                + _triage_row("TRIAGE-OLD", 8)
                + _triage_row("TRIAGE-FIX-279", 8),
                encoding="utf-8")
            record = Path(td) / "change-triage" / "FIX-279.json"
            record.parent.mkdir()
            record.write_text('{"ok": true}', encoding="utf-8")
            issues = vw._triage_write_structure_guard(
                evidence, record, record_id="TRIAGE-FIX-279")
            self.assertEqual(issues, [])


class CmdChangeTriageWiringTests(unittest.TestCase):
    """cmd_change_triage 接线：成功路径调用 guard；guard 失败 → exit 2。"""

    def _args(self):
        return types.SimpleNamespace(
            task="FIX-278", title="t", priority="P1", version="0.78.0",
            depends_on="", files="skills/software-project-governance/infra/x.py",
            reason="r", acceptance="a", side_effects="")

    def test_guard_failure_exits_two(self):
        """写入产物结构破坏 → change-triage exit 2（fail-closed G3）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            evidence = gov / "evidence-log.md"
            evidence.write_text(
                _evidence_row_10() + "| TRIAGE-FIX-278 | FIX-278 | x |\n",
                encoding="utf-8")
            record = gov / "change-triage" / "FIX-278.json"
            record.parent.mkdir()
            record.write_text('{"ok": true}', encoding="utf-8")
            summary = {
                "task_id": "FIX-278",
                "record_path": str(record),
                "evidence_row_written": True,
                "record_id": "TRIAGE-FIX-278",
                "analysis": {},
                "snapshot": {},
            }
            tracker = gov / "plan-tracker.md"
            tracker.write_text(_FIXTURE_TRACKER, encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov), \
                 mock.patch.object(vw, "PLUGIN_ROOT",
                                   _INFRA_DIR.parents[1]), \
                 mock.patch("change_triage.run_triage",
                            return_value=summary) as m_run:
                with self.assertRaises(SystemExit) as ctx:
                    vw.cmd_change_triage(self._args())
                self.assertEqual(ctx.exception.code, 2)
            m_run.assert_called_once()

    def test_guard_clean_path_exits_zero(self):
        """写入产物结构合法 → 正常退出 0（guard 不误伤）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            evidence = gov / "evidence-log.md"
            evidence.write_text(
                _evidence_row_10() + _triage_row("TRIAGE-FIX-278", 10),
                encoding="utf-8")
            record = gov / "change-triage" / "FIX-278.json"
            record.parent.mkdir()
            record.write_text('{"ok": true}', encoding="utf-8")
            summary = {
                "task_id": "FIX-278",
                "record_path": str(record),
                "evidence_row_written": True,
                "record_id": "TRIAGE-FIX-278",
                "analysis": {},
                "snapshot": {},
            }
            tracker = gov / "plan-tracker.md"
            tracker.write_text(_FIXTURE_TRACKER, encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov), \
                 mock.patch.object(vw, "PLUGIN_ROOT",
                                   _INFRA_DIR.parents[1]), \
                 mock.patch("change_triage.run_triage",
                            return_value=summary):
                vw.cmd_change_triage(self._args())  # no SystemExit

    def test_error_path_exits_two_without_guard(self):
        """fail-closed 输入（run_triage 返回 error）→ exit 2，不进入 guard
        （既有语义保持——FIX-278 只追加成功路径 guard）。"""
        with mock.patch("change_triage.run_triage",
                        return_value={"error": "task_id must match"}):
            with self.assertRaises(SystemExit) as ctx:
                vw.cmd_change_triage(self._args())
            self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
