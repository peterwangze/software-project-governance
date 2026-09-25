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

FEAT-011 G3 扩展 — Coordinator 直写路径写时结构守卫
（``governance-write-guard`` 子命令）：change-triage 机器写入有 G3 守卫，
但 Coordinator 直写 ``.governance/``（plan-tracker 任务行 / evidence-log
追加行 / agent-locks / execution-packets）无写时校验——结构缺陷静默入库
（活体：AUDIT-149 §4 M1 四行 FIX-222/223/224/279 长期被判活跃；agent-locks
14 条 Check 26 schema 违规；execution-packets 字段违规两起）。扩展契约：
（1）守卫 = 检查器——零 ``.governance`` 写入、零自动修复（remediation 指明
    行号与期望形状，修复动作留给写入者）；
（2）复用既有判定权威源（``_governance_table_cells`` / Check 26
    ``check_agent_locks_format`` / Check 18c ``_validate_execution_packet`` /
    DEC-168 行族列数契约 / ``change_triage._TASK_ID_RE``），不自建第二套
    形状定义；
（3）既有 change-triage 守卫行为零变化（扩展而非重写）。

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_triage_write_guard.py -v
"""

import io
import json
import os
import sys
import tempfile
import threading
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
import write_guard_state as wgs  # noqa: E402  (FEAT-060 state machine entity)
import governance_store as gstore  # noqa: E402  (FEAT-064 composition face)
import decision_repository as drepo  # noqa: E402  (FEAT-064 composition face)

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

    def test_write_guard_non_utf8_record_returns_structured_issue_not_raise(self):
        """FIX-333 R0 F-1 反相（写后校验 record 面）：刚写入的 triage record
        为 GBK 字节时 ``read_text(encoding="utf-8")`` 抛 ``UnicodeDecodeError``
        （``ValueError`` 子类），旧捕获面 ``except OSError`` 接不住 ⇒ 异常从
        写后校验本体逸出，与 docstring「Never raises」（L22185）不符
        （REVIEW-FIX-333-CODE-R0 §六 F-1 独立扫描实证）。修复后契约：结构化
        issue（"triage record unreadable after write"）而非异常。GBK 副本写
        ``tempfile`` 临时目录（%TEMP%），不触碰 ``.governance/``。
        """
        with tempfile.TemporaryDirectory() as td:
            evidence = Path(td) / "evidence-log.md"
            evidence.write_text(
                _evidence_row_10() + _triage_row("TRIAGE-FIX-333", 10),
                encoding="utf-8")
            record = Path(td) / "FIX-333.json"
            record.write_bytes(json.dumps(
                {"schema_version": 1, "task_id": "FIX-333",
                 "note": "非UTF-8反相样本"},
                ensure_ascii=False).encode("gbk"))
            issues = vw._triage_write_structure_guard(evidence, record)
        self.assertEqual(len(issues), 1, issues)
        self.assertIn("triage record unreadable after write", issues[0])
        self.assertIn("codec", issues[0], issues)

    def test_write_guard_non_utf8_evidence_returns_structured_issue_not_raise(self):
        """FIX-333 R0 F-1 反相（写后校验 evidence-log 面，与面2 读同一文件）：
        evidence-log 为 GBK 字节时 ``except (IOError, OSError)`` 接不住
        ``UnicodeDecodeError`` ⇒ 异常逸出（同一「Never raises」契约缺口，
        泛化收口不做单点修复）。修复后契约：结构化 issue（"evidence-log
        unreadable after write"）而非异常。GBK 副本写 ``tempfile`` 临时
        目录（%TEMP%）。
        """
        with tempfile.TemporaryDirectory() as td:
            evidence = Path(td) / "evidence-log.md"
            evidence.write_bytes(
                (_evidence_row_10() + _triage_row("TRIAGE-FIX-333", 10)
                 ).encode("gbk"))
            record = Path(td) / "FIX-333.json"
            record.write_text('{"schema_version": 1, "ok": true}',
                              encoding="utf-8")
            issues = vw._triage_write_structure_guard(evidence, record,
                                                      record_id="TRIAGE-FIX-333")
        self.assertEqual(len(issues), 1, issues)
        self.assertIn("evidence-log unreadable after write", issues[0])
        self.assertIn("codec", issues[0], issues)

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


# ─── FEAT-011 G3 扩展 — governance-write-guard（Coordinator 直写路径） ────

_GUARD_TRACKER_CLEAN = """\
# Plan Tracker

## 当前活跃事项

| 优先级 | 任务ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|--------|------|------|---------|---------|------|
| **P1** | FIX-301 | clean seven-column row | — | 0.79.0 | path | ⏳ 待执行 (2026-09-09) |
| **P2** | REL-070 | legit status-continuation row | — | 0.77.0 | path | ⏳ 版本规划中 (2026-08-24) | → ✅ 已发布 (2026-08-25)——live REL-070 shape |
| **P1** | FIX-278 | legit eight-column row | — | 0.78.0 | path | 🔄 已 lock 待派发 (2026-08-25) | → ✅ 完成 (2026-08-26)——live FIX-278 shape |
"""

_GUARD_TRACKER_M1 = """\
# Plan Tracker

## 当前活跃事项

| 优先级 | 任务ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|--------|------|------|---------|---------|------|
| **P0** | **P0** | FIX-222 | AUDIT-139✅ | 0.71.0 | closure | ✅ 完成 (2026-07-26) | |
| **P1** | FIX-279 | G3 write-guard 列数契约修正 | TRIAGE-FIX-279 | 0.78.0 | closure | ✅ 完成 (2026-08-26)——narrative | |
"""

_KNOWN_M1_IDS = {"FIX-222", "FIX-223", "FIX-224", "FIX-279"}


def _machine_evidence_fixture():
    """TRIAGE/RECO 机器行族（各 10 列，DEC-168 行族标准）+ EVD 手工混合行。

    EVD 9/10/11 列混合是 documented legacy（FIX-279 测试组同型）——guard
    对手工行族不做列数强制（既有 Check 14 WARN 域），仅校验机器行族。
    """
    triage = _triage_row("TRIAGE-FIX-278", 10)
    triage2 = _triage_row("TRIAGE-REL-071", 10)
    reco_cells = ["RECO-FIX-262", "FIX-262", "推荐记录", "描述", "事实依据：x",
                  "artifact", "actor", "2026-08-26", "G11", "PASS"]
    reco = "| " + " | ".join(reco_cells) + " |\n"
    return _evidence_row_9("EVD-800") + _evidence_row_10("EVD-801") + triage \
        + triage2 + reco


def _legal_locks():
    return {
        "active_tasks": {
            "FEAT-011": {
                "spawned_at": "2026-09-09T10:00:00+00:00",
                "coordinator_session": "session-x",
                "target_files": ["skills/software-project-governance/infra/verify_workflow.py"],
            },
        },
        "file_locks": {
            "skills/software-project-governance/infra/verify_workflow.py": {
                "locked_by": "FEAT-011",
                "locked_at": "2026-09-09T10:00:00+00:00",
                "ttl_seconds": 600,
                "ttl_reason": "serial file lock",
            },
        },
    }


def _legal_packet(task_id="FIX-301"):
    return {
        "task_id": task_id,
        "goal": "实现 X",
        "allowed_change_scope": ["skills/software-project-governance/infra/x.py"],
        "required_evidence": ["事实依据 + 结构化事实：测试输出"],
        "next_commands": ["python -m pytest"],
        "done_definition": ["Code Review APPROVED"],
    }


class GovernanceWriteGuardPlanTrackerTests(unittest.TestCase):
    """FEAT-011 面 1：plan-tracker 任务表行形状（AUDIT-149 §4 M1 签名）。

    M1 缺陷 = ragged 行两签名（AUDIT-149 L97-106 活体）：
    (a) 重复优先级列——任务 ID 前出现 >1 个优先级 token（`| **P0** | **P0** |`）；
    (b) 行尾空单元格——末单元格为空（`… | ✅ 完成 | |` → cells[-1]="" →
        状态列被判空 → 长期误判活跃）。
    列形权威 = 既有解析器（``_governance_table_cells`` + ``_normalize_priority``
    + 任务 ID cell 识别），不自建第二套形状定义（FIX-292 语义二源教训）。
    """

    def _issues(self, tracker_text):
        with tempfile.TemporaryDirectory() as td:
            tracker = Path(td) / "plan-tracker.md"
            tracker.write_text(tracker_text, encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", Path(td)):
                result = vw.check_governance_write_shapes()
        return result["plan_tracker"]["issues"]

    def test_duplicate_priority_column_flagged_with_line_and_shape(self):
        """M1-a（FIX-222/223/224 形状）：重复优先级列 → FAIL + 行号 + 期望列形。"""
        issues = self._issues(_GUARD_TRACKER_M1)
        dup = [i for i in issues
               if i["type"] == "plan_tracker_duplicate_priority_cell"]
        self.assertEqual(len(dup), 1, issues)
        self.assertEqual(dup[0]["line"], 7)
        self.assertEqual(dup[0]["task_id"], "FIX-222")
        # 期望列形随 issue 携带（CLI 打印为「期望列形: …」——行号 + 期望形状）
        self.assertIn("| 优先级 |", dup[0].get("expected", ""))
        self.assertIn("状态", dup[0]["expected"])

    def test_trailing_empty_status_cell_flagged_with_line_and_shape(self):
        """M1-b（FIX-279 形状）：行尾空单元格 → FAIL + 行号 + 期望列形。"""
        issues = self._issues(_GUARD_TRACKER_M1)
        trail = [i for i in issues
                 if i["type"] == "plan_tracker_trailing_empty_status"]
        self.assertEqual(len(trail), 2, issues)
        self.assertEqual({t["task_id"] for t in trail},
                         {"FIX-222", "FIX-279"})
        self.assertEqual(trail[0]["line"], 7)
        self.assertEqual(trail[1]["line"], 8)

    def test_clean_rows_and_legit_continuation_rows_pass(self):
        """规范行 + 活体合法变形（REL-070 十列状态续写 / FIX-278 八列）→
        零误报——「三例活体 0 误报」解除前置观察的依据不得出现新误报。"""
        self.assertEqual(self._issues(_GUARD_TRACKER_CLEAN), [])

    def test_live_plan_tracker_flags_only_known_m1_rows(self):
        """活体金丝雀（真实 plan-tracker）：M1 命中集合 ⊆ 已知 M1 四行
        （FIX-222/223/224/279——FIX-293 已修数据，本守卫只检不改），且任何
        非零命中即红（零命中是 live 数据的当前事实，不是「无证据」）。

        FIX-330 收口（承接 REVIEW-FIX-328-CODE-R0 F-1~F-5）：FIX-293 目标达成后
        （FIX-222/223/224 归档迁出、FIX-279 行形归一——EVD-963 记 FAIL 7 →
        PASS/exit 0），live 数据零命中是**数据已治愈**的**可断言事实**。故取
        (b) 零命中断言（授权文档 ``docs/requirements/test-baseline-0.80.0.md``
        §4-F2 修复候选原文 ``assertEqual(set(), flagged)``），弃 FIX-328 的 (a)
        条件 skip——取舍理由：
          1. 与授权候选一致（(a) 的 ``skipTest`` 是 FIX-328 自创形态）；
          2. 零命中可断言，skip 只能表达「无证据」——(a) 把「数据健康」与
             「金丝雀失效」写成同一终态；
          3. ``skipTest`` 无红相，会掩盖守卫整体失效（F-1 面）；(b) 下零命中是
             硬断言：集合外新签名与已知四行重现都立即红。

        判据顺序（三条互不遮蔽，各覆盖独立场景）：
          ① 面级 fail-closed 门禁——plan-tracker 不可读时守卫返回 status=FAIL +
             issue.task_id 哨兵 ``""``（verify_workflow.py 22415-22426），该状态
             **不是「零命中」**，必须先于命中集合判据暴露（否则只取 task_id 会把
             不可读报成「``{''}`` 不是已知集合子集」的失真措辞）。审查方建议的
             ``assertEqual(status, "PASS")`` 与 ③ 在守卫现契约下是**同一谓词**
             （``status==FAIL ⟺ issues 非空 ⟺ flagged 非空``，见 22429-22432），
             两者同置必产生一枚「可达即恒真」死断言（F-3 口径；后置还会被 ② 抢占
             而永不触发），故取哨兵形态：不可读场景必红且诊断直指
             ``plan_tracker_unreadable`` + OS 错误，与 ②③ 并存时三判据全活。
          ② 无条件核心防护：不得出现已知 M1 四行之外的新误报（subset 判据）。
          ③ 零命中事实：live 数据不得再出现任何 M1 命中（已知 ID 重现 = 数据回退）。

        原「live M1 four rows must be flagged」断言（F-3 死代码，可达即恒真）已删；
        其「live evidence 必须存在」义务由两处承接——合成样本用例
        （test_duplicate_priority_column_flagged_with_line_and_shape /
        test_trailing_empty_status_cell_flagged_with_line_and_shape）钉住守卫
        **命中能力**，③ 钉住 live 面**零命中**终态。

        术语边界（F-5）：名称沿用 FIX-328 前史（FEAT-011 born-red 窗口内 live 确有
        M1 四行，「flags」当时是真实承诺），零命中下只兑现 ``only``（②：命中若存在
        必属已知四行）；``flags`` 的存在性预设不再兑现，其回归信号由 ③ 承接（任何
        命中即红）。改名会牵动 ``infra/tests/env_failure_classification.json`` 的
        unittest 全名键与 ``docs/**`` 引用，超出本任务改动面，故保留名称并在此显式
        披露语义边界（名称弱于行为 = 欠声称，非过度声称）。

        直接证据：归档文件 ``.governance/archive/tasks/v0.1.0~v0.78.0.md``
        L131-133 三行**字面任务行**（FIX-222/223/224；``archive/index.md``
        L391-393 仅为位置目录）。
        """
        if not vw.SAMPLE_PATH.is_file():
            self.skipTest("no live plan-tracker under the host governance dir")
        result = vw.check_governance_write_shapes()
        face = result["plan_tracker"]
        flagged = {i["task_id"] for i in face["issues"]}
        # ① 面级 fail-closed 门禁：哨兵 ""（plan-tracker 不可读）不是「零命中」，
        #    须先于命中集合判据暴露——否则只取 task_id 会把不可读报成
        #    「{''} 不是已知集合子集」的失真措辞。
        self.assertNotIn("", flagged, face)
        # ② 无条件核心防护：不得出现已知 M1 四行之外的新误报
        self.assertTrue(flagged.issubset(_KNOWN_M1_IDS), flagged)
        # ③ 零命中事实（F-2(b)）：FIX-222/223/224 已归档迁出（archive/tasks/
        #    v0.1.0~v0.78.0.md L131-133 字面任务行）、FIX-279 行形归一
        #    （FIX-293/EVD-963）；任何 M1 命中重现即红。
        self.assertEqual(
            set(), flagged,
            "live plan-tracker 零命中契约被破坏：FIX-222/223/224 应已归档迁出"
            "（archive/tasks/v0.1.0~v0.78.0.md L131-133，index.md L391-393 定位）、"
            "FIX-279 行形应已归一（FIX-293/EVD-963）——先按 M1 签名修复数据，"
            "再复核本契约",
        )

    def test_non_utf8_plan_tracker_returns_structured_issue_not_raise(self):
        """FIX-333 反相（面 1，非 UTF-8 边界）：活体面文件为 GBK 字节时
        ``read_text(encoding="utf-8")`` 抛 ``UnicodeDecodeError``（``ValueError``
        子类），旧捕获面 ``except (IOError, OSError)`` 接不住 ⇒ 异常从公共入口
        ``check_governance_write_shapes()`` 逸出，与其 docstring「Never raises」
        不符（FIX-330 §8-④ 实证的既有边界）。修复后契约：面级 fail-closed——
        返回结构化 ``plan_tracker_unreadable`` issue（哨兵 ``task_id: ""``）
        而非抛异常。GBK 副本一律写 ``tempfile`` 临时目录（%TEMP%），不触碰
        ``.governance/``。
        """
        gbk_tracker = (
            "# Plan Tracker\n\n## 当前活跃事项\n\n"
            "| 优先级 | 任务ID | 事项 |\n|---|---|---|\n"
            "| **P1** | FIX-333 | 非UTF-8反相样本 |\n"
        ).encode("gbk")
        with tempfile.TemporaryDirectory() as td:
            tracker = Path(td) / "plan-tracker.md"
            tracker.write_bytes(gbk_tracker)
            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", Path(td)):
                result = vw.check_governance_write_shapes()
        face = result["plan_tracker"]
        self.assertEqual(face["status"], "FAIL", face)
        self.assertEqual(len(face["issues"]), 1, face)
        issue = face["issues"][0]
        self.assertEqual(issue["type"], "plan_tracker_unreadable")
        self.assertEqual(issue["task_id"], "")
        self.assertIn("codec", issue["detail"], issue)


class GovernanceWriteGuardEvidenceLogTests(unittest.TestCase):
    """FEAT-011 面 2：evidence-log 机器行族（TRIAGE/RECO）列数与 ID 列格式。

    列数权威 = 行族自身首行（DEC-168 行族权威 / FIX-279 write-guard 列契约
    的全文件扩展）；ID 格式权威 = ``change_triage`` 写入器契约
    （``TRIAGE-{TASK_ID}``，TASK_ID 匹配 ``_TASK_ID_RE``）。
    """

    def _issues(self, evidence_text):
        with tempfile.TemporaryDirectory() as td:
            evidence = Path(td) / "evidence-log.md"
            evidence.write_text(evidence_text, encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", Path(td) / "none.md"), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", Path(td)):
                result = vw.check_governance_write_shapes()
        return result["evidence_log"]["issues"]

    def test_machine_family_rows_pass(self):
        """合法 TRIAGE/RECO 机器行（10 列 + 规范 ID）→ 0 issue。"""
        self.assertEqual(self._issues(_machine_evidence_fixture()), [])

    def test_triage_column_break_flagged(self):
        """TRIAGE 行族标准 10 列 vs 9 列破坏行 → FAIL（行族列数契约）。"""
        issues = self._issues(_machine_evidence_fixture()
                              + _triage_row("TRIAGE-FIX-299", 9))
        col = [i for i in issues
               if i["type"] == "evidence_machine_col_mismatch"]
        self.assertEqual(len(col), 1, issues)
        self.assertEqual(col[0]["task_id"], "TRIAGE-FIX-299")

    def test_triage_malformed_id_flagged(self):
        """ID 列格式破坏（``TRIAGE-FIX29``——任务 ID 无连字符）→ FAIL。"""
        row = "| TRIAGE-FIX29 | FIX-299 | 变更控制 | 描述 | 依据 | 产物 | " \
              "change-triage | 2026-09-09 | G11 | TRIAGED |\n"
        issues = self._issues(_machine_evidence_fixture() + row)
        fmt = [i for i in issues if i["type"] == "evidence_machine_id_format"]
        self.assertEqual(len(fmt), 1, issues)
        self.assertIn("TRIAGE-FIX29", fmt[0]["detail"])

    def test_legacy_evd_manual_mix_not_flagged(self):
        """EVD 手工行族 9/10/11 列 documented 混合 → 不做列数强制（0 误报；
        该域归 Check 14 evidence_col_mismatch WARN）。"""
        text = (_evidence_row_9("EVD-800") + _evidence_row_10("EVD-801")
                + _evidence_row_10("EVD-802", "FIX-100") .replace(
                    "| EVD-802 |", "| EVD-802 | extra |", 1))
        self.assertEqual(self._issues(text), [])

    def test_non_utf8_evidence_log_returns_structured_issue_not_raise(self):
        """FIX-333 反相（面 2，同型捕获面缺陷）：evidence-log 为 GBK 字节
        → 返回结构化 ``evidence_log_unreadable`` issue 而非异常逸出（面 2
        与面 1 同为 ``except (IOError, OSError)``，非 UTF-8 时
        ``UnicodeDecodeError`` 不被捕获——同一「Never raises」契约缺口，
        泛化收口不做单点修复）。GBK 副本写 ``tempfile`` 临时目录（%TEMP%）。
        """
        gbk_evidence = (
            "| TRIAGE-FIX-333 | FIX-333 | 变更控制 | 描述样本 | 依据样本 | "
            "产物样本 | change-triage | 2026-09-17 | G11 | TRIAGED |\n"
        ).encode("gbk")
        with tempfile.TemporaryDirectory() as td:
            evidence = Path(td) / "evidence-log.md"
            evidence.write_bytes(gbk_evidence)
            with mock.patch.object(vw, "SAMPLE_PATH", Path(td) / "none.md"), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", Path(td)):
                result = vw.check_governance_write_shapes()
        face = result["evidence_log"]
        self.assertEqual(face["status"], "FAIL", face)
        self.assertEqual(len(face["issues"]), 1, face)
        self.assertEqual(face["issues"][0]["type"], "evidence_log_unreadable")
        self.assertIn("codec", face["issues"][0]["detail"], face)


class GovernanceWriteGuardLocksAndPacketsTests(unittest.TestCase):
    """FEAT-011 面 3/4：agent-locks（Check 26 schema 复用）+ execution-packets
    （Check 18c 字段表 ``EXECUTION_PACKET_REQUIRED_FIELDS`` 复用）。"""

    def _result(self, gov, locks=None, packets=None):
        gov.mkdir(parents=True, exist_ok=True)
        tracker = gov / "plan-tracker.md"
        tracker.write_text(_GUARD_TRACKER_CLEAN, encoding="utf-8")
        evidence = gov / "evidence-log.md"
        evidence.write_text(_machine_evidence_fixture(), encoding="utf-8")
        if locks is not None:
            (gov / "agent-locks.json").write_text(
                json.dumps(locks), encoding="utf-8")
        if packets is not None:
            (gov / "execution-packets.json").write_text(
                json.dumps({"packets": packets}), encoding="utf-8")
        with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
             mock.patch.object(vw, "GOVERNANCE_DIR", gov):
            return vw.check_governance_write_shapes()

    def test_agent_locks_legal_passes(self):
        """合法锁文件（Check 26 全字段）→ PASS。"""
        with tempfile.TemporaryDirectory() as td:
            result = self._result(Path(td), locks=_legal_locks(),
                                  packets={"FIX-301": _legal_packet()})
        self.assertEqual(result["agent_locks"]["issues"], [])
        self.assertEqual(result["execution_packets"]["issues"], [])

    def test_agent_locks_missing_spawned_at_flagged(self):
        """active_tasks 缺 ``spawned_at``（本会话 14 条违规同型）→ FAIL
        （复用 Check 26 check_agent_locks_format，不建第二套 schema）。"""
        locks = _legal_locks()
        del locks["active_tasks"]["FEAT-011"]["spawned_at"]
        with tempfile.TemporaryDirectory() as td:
            result = self._result(Path(td), locks=locks,
                                  packets={"FIX-301": _legal_packet()})
        self.assertTrue(result["agent_locks"]["issues"])
        self.assertIn("spawned_at",
                      " ".join(i["detail"] for i in
                               result["agent_locks"]["issues"]))

    def test_agent_locks_absent_skipped_not_failed(self):
        """agent-locks.json 缺席（宿主未启用锁文件）→ SKIPPED 而非 FAIL
        （R0 F-2：与面 1/2/4 的 ``is_file()`` 门控 SKIP 语义对称——
        「产物缺席，非缺陷」；result 初始 ``"SKIPPED"`` 值不再不可达）。"""
        with tempfile.TemporaryDirectory() as td:
            result = self._result(Path(td), packets={"FIX-301": _legal_packet()})
        self.assertEqual(result["agent_locks"]["status"], "SKIPPED")
        self.assertEqual(result["agent_locks"]["issues"], [])

    def test_execution_packet_missing_goal_flagged(self):
        """packet 缺 ``goal`` 字段 → FAIL（EXECUTION_PACKET_REQUIRED_FIELDS）。"""
        packet = _legal_packet()
        del packet["goal"]
        with tempfile.TemporaryDirectory() as td:
            result = self._result(Path(td), locks=_legal_locks(),
                                  packets={"FIX-301": packet})
        details = " ".join(i["detail"] for i in
                           result["execution_packets"]["issues"])
        self.assertIn("goal", details)

    def test_execution_packets_absent_skipped_not_failed(self):
        """execution-packets.json 缺席（宿主未启用）→ SKIPPED 而非 FAIL。"""
        with tempfile.TemporaryDirectory() as td:
            result = self._result(Path(td), locks=_legal_locks())
        self.assertEqual(result["execution_packets"]["status"], "SKIPPED")

    def test_non_utf8_locks_and_packets_fail_closed_not_raise(self):
        """FIX-333 反相（面 3/4，helper 捕获面）：agent-locks.json 与
        execution-packets.json 为 GBK 字节时，helper 内层只捕
        ``json.JSONDecodeError`` / ``IOError``，``UnicodeDecodeError`` 既逸出
        helper 亦逸出公共入口。修复后：两面各返回结构化 FAIL issue——锁面
        复用既有 ``invalid_json`` 分支（write-guard 投影为
        ``agent_locks_invalid_json``）、包面走既有 ``load_error`` 结构——
        而非抛异常（「Never raises」契约覆盖全部四面的泛化收口）。
        GBK 副本写 ``tempfile`` 临时目录（%TEMP%）。
        """
        locks = _legal_locks()
        locks["active_tasks"]["FEAT-011"]["ttl_reason"] = "串行文件锁"
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            (gov / "agent-locks.json").write_bytes(
                json.dumps(locks, ensure_ascii=False).encode("gbk"))
            (gov / "execution-packets.json").write_bytes(
                json.dumps({"packets": {"FIX-301": _legal_packet()}},
                           ensure_ascii=False).encode("gbk"))
            tracker = gov / "plan-tracker.md"
            tracker.write_text(_GUARD_TRACKER_CLEAN, encoding="utf-8")
            (gov / "evidence-log.md").write_text(
                _machine_evidence_fixture(), encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov):
                result = vw.check_governance_write_shapes()
        self.assertEqual(result["agent_locks"]["status"], "FAIL")
        self.assertTrue(result["agent_locks"]["issues"],
                        result["agent_locks"])
        self.assertEqual(result["execution_packets"]["status"], "FAIL")
        self.assertIn("invalid JSON",
                      " ".join(i["detail"]
                               for i in result["execution_packets"]["issues"]),
                      result["execution_packets"])

    def test_lock_consistency_non_utf8_skips_without_raise(self):
        """FIX-333 R0 F-2 反相（Check 26 一致性路径，与面3 读同一
        agent-locks.json）：文件为 GBK 字节时 ``check_agent_lock_consistency``
        的 ``except (json.JSONDecodeError, IOError)`` 接不住
        ``UnicodeDecodeError`` ⇒ 异常逸出（本应 skipped 的 WARN 级检查变
        crash）。修复后契约：结构化 skipped 结论而非异常（format 检查经
        FIX-333 面收口已先行返回 invalid_json，不 raise）。GBK 副本写
        ``tempfile`` 临时目录（%TEMP%）。
        """
        locks = _legal_locks()
        locks["active_tasks"]["FEAT-011"]["ttl_reason"] = "串行文件锁"
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            (gov / "agent-locks.json").write_bytes(
                json.dumps(locks, ensure_ascii=False).encode("gbk"))
            with mock.patch.object(vw, "GOVERNANCE_DIR", gov):
                result = vw.check_agent_lock_consistency()
        self.assertIn("unparseable", result["skipped"] or "", result)
        self.assertTrue(
            any("invalid_json" in i["type"] for i in result["issues"]),
            result["issues"])


class ExecutionPacketNonDictEarlyReturnTests(unittest.TestCase):
    """FEAT-011 R0 F-1 回归 — ``_validate_execution_packet`` 非 dict 早退。

    R0 F-1（P1，review-FEAT-011-CODE-R0.md §4）：Check 18c 的
    ``_validate_execution_packet`` 委托 ``_execution_packet_field_issues``
    后丢失 HEAD 的非 dict 早退——非 dict 非 null 包（str/list/int 实证）到达
    ``packet.get("task_id")`` 抛 ``AttributeError``，可经
    ``check_execution_packets``（Check 18c）使 check-governance 整体崩溃。
    HEAD 语义（``git show HEAD`` 实证）：早退返回 ``["packet must be object"]``。
    """

    def test_non_dict_packet_returns_head_semantics_without_crash(self):
        """str/list/int 三型探针 → 无异常 + ``["packet must be object"]``
        （HEAD 行为恒等）；Check 18c 对含畸形包的 execution-packets.json
        不崩溃——结构化 FAIL entry 而非 traceback。"""
        task = {"task_id": "FIX-301"}
        for packet in ("not-a-dict", ["not", "a", "dict"], 42):
            self.assertEqual(
                vw._validate_execution_packet(task, packet),
                ["packet must be object"], packet)
        with tempfile.TemporaryDirectory() as td:
            packets_path = Path(td) / "execution-packets.json"
            packets_path.write_text(
                json.dumps({"packets": {"FIX-301": "not-a-dict"}}),
                encoding="utf-8")
            tracker = Path(td) / "plan-tracker.md"
            tracker.write_text(_GUARD_TRACKER_CLEAN, encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", tracker):
                result = vw.check_execution_packets(packets_path)
        self.assertFalse(result["pass"])
        self.assertEqual(
            result["entries"],
            [{"task_id": "FIX-301", "status": "FAIL",
              "issues": ["packet must be object"]}])


class GovernanceWriteGuardCmdAndSafetyTests(unittest.TestCase):
    """CLI 接线（exit code）+ 非破坏性硬约束（守卫零写入）。"""

    def _clean_gov(self, td):
        gov = Path(td)
        result = GovernanceWriteGuardLocksAndPacketsTests()._result(
            gov, locks=_legal_locks(), packets={"FIX-301": _legal_packet()})
        assert result["plan_tracker"]["issues"] == []
        return gov

    def test_cmd_exits_one_on_issues(self):
        """任一面 FAIL → SystemExit 1（守卫语义：结构性缺陷不得静默）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            gov.mkdir(parents=True, exist_ok=True)
            tracker = gov / "plan-tracker.md"
            tracker.write_text(_GUARD_TRACKER_M1, encoding="utf-8")
            (gov / "evidence-log.md").write_text(
                _machine_evidence_fixture(), encoding="utf-8")
            (gov / "agent-locks.json").write_text(
                json.dumps(_legal_locks()), encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov), \
                 mock.patch("sys.stdout", new_callable=lambda: io.StringIO()):
                with self.assertRaises(SystemExit) as ctx:
                    vw.cmd_governance_write_guard(types.SimpleNamespace())
            self.assertEqual(ctx.exception.code, 1)

    def test_cmd_clean_exits_zero(self):
        """全 PASS → 正常返回（无 SystemExit）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._clean_gov(td)
            tracker = gov / "plan-tracker.md"
            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov), \
                 mock.patch("sys.stdout", new_callable=lambda: io.StringIO()):
                vw.cmd_governance_write_guard(types.SimpleNamespace())

    def test_guard_writes_nothing(self):
        """非破坏性硬门槛：守卫运行后 .governance 目标文件字节不变
        （check-only——除 stdout 外零写入、零自动修复）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._clean_gov(td)
            before = {
                p.name: p.read_bytes()
                for p in gov.iterdir() if p.is_file()
            }
            tracker = gov / "plan-tracker.md"
            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov):
                vw.check_governance_write_shapes()
            after = {
                p.name: p.read_bytes()
                for p in gov.iterdir() if p.is_file()
            }
            self.assertEqual(before, after)


class RowFamilyReconciliationTests(unittest.TestCase):
    """FEAT-057 面 5：受管行族对账（EVD/DEC/REVIEW 行 + 任务状态列 +
    ``*.ops.jsonl`` receipt 台账）。

    判据（票面验收）：
    - amnesty 首跑基线——首见受管面建立 ``.write-guard-state.json`` 基线，
      存量行属历史事实不追溯（零 WARN）；
    - 正例——机器标记行变更（governance-store 标记 / task_row_update
      ``〔op-…〕`` 锚 / receipt ``operation_id``）零 WARN；
    - 负例——裸行变更 WARN 响亮 + 可指引（detail 携写入器指引；
      WARN 姿态 face 恒 PASS——BLOCK 升级留 0.87）；
    - 状态基线仅在 CLI 路径（``persist_state=True``）落盘；probe 调用
      零写入（contract-matrix representative 提取不触真实 .governance）。
    """

    # ── fixtures ─────────────────────────────────────────────────────────

    _EVD_SEED = (
        "| EVD-8001 | FEAT-057 | 产品代码 | seed 旧行（amnesty 样本） | "
        "事实依据：存量行 | actor | 2026-09-19 | G11 | ✅ 完成 |\n")
    _EVD_SEED2 = (
        "| EVD-8002 | FEAT-057 | 产品代码 | seed 第二行 | "
        "事实依据：存量行 | actor | 2026-09-19 | G11 | ✅ 完成 |\n")
    _DEC_SEED = (
        "| DEC-223 | 2026-09-19 | coordinator | seed 决策行 | "
        "依据：存量 |\n")
    _REVIEW_SEED = (
        "| REVIEW-FEAT-057-R0 | FEAT-057 | 治理记录 | seed 审查行 | "
        "事实依据：存量 | reviewer | 2026-09-19 | G11 | APPROVED |\n")
    _TRACKER_SEED = (
        "| 优先级 | 任务ID | 标题 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
        "|---|---|---|---|---|---|---|\n"
        "| **P1** | FEAT-057 | 行族对账夹具票 | — | 0.86.0 | closure | "
        "🔄 进行中 (2026-09-19) |\n")
    _OPS_SEED = '{"operation_id": "op-' + "0" * 32 + \
        '", "record_kind": "task_row_update"}\n'

    def _seed_gov(self, td):
        gov = Path(td)
        (gov / "evidence-log.md").write_text(
            self._EVD_SEED + self._EVD_SEED2 + self._REVIEW_SEED,
            encoding="utf-8")
        (gov / "decision-log.md").write_text(self._DEC_SEED,
                                             encoding="utf-8")
        (gov / "plan-tracker.md").write_text(self._TRACKER_SEED,
                                             encoding="utf-8")
        (gov / "plan-tracker.md.ops.jsonl").write_text(self._OPS_SEED,
                                                       encoding="utf-8")
        return gov

    def _run_guard(self, gov, persist_state=False):
        tracker = gov / "plan-tracker.md"
        with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
             mock.patch.object(vw, "GOVERNANCE_DIR", gov):
            return vw.check_governance_write_shapes(
                persist_state=persist_state)

    def _row_family_issues(self, result):
        return [i for i in result["row_families"]["issues"]
                if i["type"] == "unattributed_row_change"]

    # ── amnesty 首跑基线 ─────────────────────────────────────────────────

    def test_first_run_establishes_baseline_zero_warn(self):
        """首跑建立状态基线：存量手写行零 WARN（amnesty），基线文件落盘。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed_gov(td)
            result = self._run_guard(gov, persist_state=True)
            face = result["row_families"]
            self.assertEqual(face["status"], "PASS", face)
            self.assertEqual(self._row_family_issues(result), [], face)
            self.assertEqual(
                sorted(face["baselined"]),
                [".governance/decision-log.md",
                 ".governance/evidence-log.md",
                 ".governance/plan-tracker.md",
                 ".governance/plan-tracker.md.ops.jsonl"], face)
            state_path = gov / ".write-guard-state.json"
            self.assertTrue(state_path.is_file())
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertIn("evidence-log.md", state["files"])

    def test_probe_mode_never_persists_state(self):
        """probe 调用（persist_state=False，contract-matrix representative
        同路径）零写入——状态基线文件不出现。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed_gov(td)
            result = self._run_guard(gov, persist_state=False)
            self.assertEqual(result["row_families"]["status"], "PASS")
            self.assertFalse(
                (gov / ".write-guard-state.json").is_file())

    # ── 正例：机器标记行变更零 WARN ─────────────────────────────────────

    def test_machine_marked_row_changes_stay_silent(self):
        """基线后全部受管面以机器凭证变更 → 零 WARN（凭证判定权威 =
        governance_store 标记 / task_row_update 〔op-…〕 锚 / receipt
        operation_id）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed_gov(td)
            self._run_guard(gov, persist_state=True)
            op = "op-" + "a" * 32
            (gov / "evidence-log.md").write_text(
                self._EVD_SEED + self._EVD_SEED2 + self._REVIEW_SEED
                + "| EVD-8003 | FEAT-057 | 产品代码 | 机器追加行 | "
                  "事实依据：x（机器写入：governance-store evidence-append "
                  "{0}；schema v1） | governance-store | 2026-09-20 | G11 "
                  "| PASS |\n".format(op)
                + "| REVIEW-FEAT-057-R1 | FEAT-057 | 治理记录 | "
                  "review-record CLI 机器写入 review 结论记录（round 1） | "
                  "事实依据：review-record 输出摘要（机器写入） | r.md | "
                  "reviewer | 2026-09-20 | G11 | APPROVED |\n",
                encoding="utf-8")
            (gov / "decision-log.md").write_text(
                self._DEC_SEED
                + "| DEC-224 | 2026-09-20 | coordinator | 机器决策行 | "
                  "依据：y（机器写入：governance-store decision-append "
                  "{0}；schema v1）\n".format(op),
                encoding="utf-8")
            (gov / "plan-tracker.md").write_text(
                self._TRACKER_SEED.replace(
                    "🔄 进行中 (2026-09-19)",
                    "✅ 完成 (2026-09-20)〔{0}〕".format(op)),
                encoding="utf-8")
            with (gov / "plan-tracker.md.ops.jsonl").open(
                    "a", encoding="utf-8") as fh:
                fh.write('{"operation_id": "' + op
                         + '", "record_kind": "task_row_update"}\n')
            result = self._run_guard(gov, persist_state=True)
            self.assertEqual(self._row_family_issues(result), [], result)
            self.assertEqual(result["row_families"]["status"], "PASS")

    # ── 负例：裸行变更 WARN 响亮 + 可指引 ───────────────────────────────

    def test_bare_row_changes_warn_loudly_with_writer_guidance(self):
        """基线后五面裸行变更 → 各一条 unattributed_row_change WARN；face
        恒 PASS（WARN 姿态——响亮披露不阻断）；detail 携写入器指引。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed_gov(td)
            self._run_guard(gov, persist_state=True)
            (gov / "evidence-log.md").write_text(
                self._EVD_SEED + self._EVD_SEED2 + self._REVIEW_SEED
                + "| EVD-8003 | FEAT-057 | 产品代码 | 裸追加行 | "
                  "事实依据：手写无凭证 | someone | 2026-09-20 | G11 | "
                  "PASS |\n"
                + "| REVIEW-FEAT-057-R1 | FEAT-057 | 治理记录 | 裸审查行 | "
                  "事实依据：手写无凭证 | someone | 2026-09-20 | G11 | "
                  "APPROVED |\n",
                encoding="utf-8")
            (gov / "decision-log.md").write_text(
                self._DEC_SEED
                + "| DEC-224 | 2026-09-20 | coordinator | 裸决策行 | "
                  "依据：手写无凭证\n",
                encoding="utf-8")
            (gov / "plan-tracker.md").write_text(
                self._TRACKER_SEED.replace(
                    "🔄 进行中 (2026-09-19)", "✅ 完成 (2026-09-20)"),
                encoding="utf-8")
            with (gov / "plan-tracker.md.ops.jsonl").open(
                    "a", encoding="utf-8") as fh:
                fh.write("hand-edited ledger line without receipt\n")
            result = self._run_guard(gov, persist_state=True)
            face = result["row_families"]
            issues = self._row_family_issues(result)
            self.assertEqual(len(issues), 5, face)
            self.assertEqual(face["status"], "PASS")  # WARN 姿态：不 FAIL
            by_key = {i["task_id"]: i for i in issues}
            self.assertEqual(
                {i["file"] for i in issues},
                {".governance/evidence-log.md",
                 ".governance/decision-log.md",
                 ".governance/plan-tracker.md",
                 ".governance/plan-tracker.md.ops.jsonl"}, issues)
            for row_id in ("EVD-8003", "REVIEW-FEAT-057-R1", "DEC-224",
                           "FEAT-057"):
                self.assertIn(row_id, by_key, issues)
                self.assertIn("unattributed row change",
                              by_key[row_id]["detail"])
                self.assertIn("WARN 姿态 0.86.0", by_key[row_id]["detail"])
                # FEAT-064 wording: the mechanism is delivered (default
                # all-WARN), the posture is viewable via --show-posture.
                self.assertIn("分族 BLOCK 机制已交付未激活",
                              by_key[row_id]["detail"])
                self.assertTrue(by_key[row_id]["line"], issues)
            self.assertIn("use governance_store", by_key["EVD-8003"]["detail"])
            self.assertIn("use task_row_update",
                          by_key["FEAT-057"]["detail"])
            self.assertIn("receipt 行携 operation_id",
                          by_key["2"]["detail"])  # ops 行按行号键

    def test_untouched_rows_amnestied_only_changed_row_warns(self):
        """基线后仅改写一行（无凭证）→ 恰一条 WARN 且锚定该行；
        未触碰的存量行零打扰。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed_gov(td)
            self._run_guard(gov, persist_state=True)
            (gov / "evidence-log.md").write_text(
                self._EVD_SEED.replace("seed 旧行（amnesty 样本）",
                                       "改写行（无凭证手改）")
                + self._EVD_SEED2 + self._REVIEW_SEED,
                encoding="utf-8")
            result = self._run_guard(gov, persist_state=True)
            issues = self._row_family_issues(result)
            self.assertEqual(len(issues), 1, result)
            self.assertEqual(issues[0]["task_id"], "EVD-8001", issues)

    # ── 状态基线异常面 ───────────────────────────────────────────────────

    def test_ops_ledger_midline_insert_pins_displacement_semantics(self):
        """P3-1（review-FEAT-057-CODE-R0）：ops 台账行号键控下中部插行——
        裸插行恰一条 WARN（行号锚定插入位），被位移的原 receipt 行（键
        位移但凭证仍命中）零误报。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed_gov(td)
            self._run_guard(gov, persist_state=True)
            ledger = gov / "plan-tracker.md.ops.jsonl"
            lines = ledger.read_text(encoding="utf-8").splitlines(keepends=True)
            self.assertEqual(len(lines), 1, lines)
            # 裸行插在原 receipt 之前：原行位移至键 2（凭证仍命中→不误报），
            # 裸行占键 1（无凭证→恰一 WARN）
            ledger.write_text(
                "bare midline hand edit\n" + lines[0], encoding="utf-8")
            result = self._run_guard(gov, persist_state=True)
            issues = self._row_family_issues(result)
            self.assertEqual(len(issues), 1, result)
            self.assertEqual(issues[0]["task_id"], "1", issues)
            self.assertEqual(issues[0]["line"], 1, issues)

    def test_state_unwritable_disclosed_not_crash(self):
        """P3-4（review-FEAT-057-CODE-R0）：状态基线写入失败 → WARN 级
        row_family_state_unwritable 披露（face 恒 PASS、不崩溃），既有
        基线文件原样保留。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed_gov(td)
            self._run_guard(gov, persist_state=True)
            state_path = gov / ".write-guard-state.json"
            before = state_path.read_bytes()

            def boom(self_path, *args, **kwargs):
                raise OSError("disk full (simulated)")

            with mock.patch.object(Path, "write_text", boom):
                result = self._run_guard(gov, persist_state=True)
            face = result["row_families"]
            kinds = [i["type"] for i in face["issues"]]
            self.assertIn("row_family_state_unwritable", kinds, face)
            self.assertIn("disk full", face["issues"][-1]["detail"], face)
            self.assertEqual(face["status"], "PASS")  # WARN 姿态不 FAIL
            self.assertEqual(state_path.read_bytes(), before)  # 基线未被破坏

    def test_corrupt_state_rebuilds_with_loud_disclosure(self):
        """状态基线损坏 → WARN 级 row_family_state_unreadable + 按首跑重建
        （响亮披露，不静默）；重建后状态文件恢复为合法 JSON。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed_gov(td)
            self._run_guard(gov, persist_state=True)
            (gov / ".write-guard-state.json").write_text(
                "{not valid json", encoding="utf-8")
            result = self._run_guard(gov, persist_state=True)
            face = result["row_families"]
            kinds = [i["type"] for i in face["issues"]]
            self.assertIn("row_family_state_unreadable", kinds, face)
            self.assertEqual(face["status"], "PASS")
            state = json.loads(
                (gov / ".write-guard-state.json")
                .read_text(encoding="utf-8"))
            self.assertIn("evidence-log.md", state["files"])

    # ── 凭证权威绑定（防标记漂移——第二形状源防线） ─────────────────────

    def test_marker_authorities_bound_to_real_writer_output(self):
        """凭证判据绑定真实写入器产物：governance_store 实建行含守卫
        前缀常量；task_row_update 状态锚模式为写入器自有常量——任一漂移
        本测试先红。"""
        from governance_store import _build_decision_row, _build_evidence_row
        evd_text, _cells = _build_evidence_row(
            evd_id="EVD-9500", task_id="FEAT-057", evd_type="产品代码",
            description="绑定探针", basis="b", artifacts="a", actor="t",
            date_str="2026-09-20", gate="G11", conclusion="PASS", refs=[],
            op_id="op-" + "a" * 32)
        self.assertIn(vw._GOVERNANCE_STORE_MARKER_PREFIX, evd_text)
        dec_text = _build_decision_row(
            dec_id="DEC-9000", date_str="2026-09-20", decider="t",
            content="绑定探针", basis="b", op_id="op-" + "b" * 32)
        self.assertIn(vw._GOVERNANCE_STORE_MARKER_PREFIX, dec_text)
        from task_row_update import STATUS_CELL_OP_SUFFIX_PATTERN
        anchored = "✅ 完成 (2026-09-20)〔op-" + "c" * 32 + "〕"
        self.assertTrue(STATUS_CELL_OP_SUFFIX_PATTERN.search(anchored))
        self.assertFalse(STATUS_CELL_OP_SUFFIX_PATTERN.search(
            anchored + "（后缀手改）"))


# ─── FEAT-060 — write-guard 违规持久状态机 + hook 消费权台账 ────────────────

def _detect(family="evidence-log.md", object_id="EVD-9001", after=None,
            before=None, kind="text", line=9, text="| EVD-9001 | bare |"):
    """Detection-dict builder (write_guard_state.build_detection 委托)."""
    return wgs.build_detection(
        family, kind, object_id, ".governance/" + family, line, text,
        after if after is not None else "a" * 32, before)


def _baseline_target(files=None):
    """Minimal realistic reconciliation-baseline target (state file shape)."""
    return {
        "schema_version": 1,
        "tool": "governance-write-guard/row-family-reconciliation",
        "updated_at": "2026-09-24T00:00:00",
        "files": files if files is not None else {},
    }


class WriteGuardViolationStateMachineTests(unittest.TestCase):
    """FEAT-060 六规则红绿测试 + ops 事务性 + CLI 集成
    （DEC-224 双约束 + version-plan-0.88.0 §2 B1 arch Q2 定案；实现实体
    ``infra/write_guard_state.py``，本类只测行为契约）。

    规则 → 测试映射（每规则红绿判据——红相 = 违反规则的实现必挂的断言，
    绿相 = 合规路径的行为断言）：
      R1 观测≠接受 / 重复      ``test_rule1_*`` —— 记录即 open、消费是唯一
                               终态；同内容重复观测零新增记录且零改写（纯
                               去重）；内容变更 = 独立再触发 → supersede 链。
      R2 WARN 不改基线         ``test_rule2_*`` —— 基线写入对违规记录零权力
                               （任何经基线路径改写违规状态即挂）。字面
                               「WARN 不前移对账基线」为 FEAT-064 BLOCK
                               翻转面（WARN 姿态下吸收窗口是既有行为，
                               DEC-224 钉住）——口径披露见模块 docstring。
      R3 同会话二次独立触发升级 ``test_rule3_*`` —— 同会话 escalated=True +
                               escalated_at；跨会话/无会话身份 False（保守
                               退化：宁可漏升不可误升）。
      R4 跨会话保留            ``test_rule4_*`` —— 新会话新 run 后记录仍
                               open 且 first_seen 不变；对账基线文件重建
                               （丢失）也不丢未决违规。
      R5 预授予+单次原子消费   ``test_rule5_*`` —— 有效授权单次消费绿；
                               同授权二次消费 / 伪造 hook / 未登记 hook /
                               未授权确保全拒（红相）。
      R6 台账损坏不吸收不前移  ``test_rule6_*`` —— 损坏 → 响亮披露 + 基线
                               冻结 + 零写入；修复后窗口重开重录（收敛）。
    事务性（消费后崩溃 / 基线写崩）：``test_consume_crash_*`` —— 异常注入
    模拟中途 kill → journal 残留 + 世界判定恢复，无半状态；恢复分目标态
    （仅收尾）与前像态（重放基线写）两支 + 分歧拒绝支。并发：
    ``test_concurrent_recordings_serialize``。
    """

    # ── fixtures ─────────────────────────────────────────────────────────

    def _state_path(self, gov):
        return Path(gov) / ".write-guard-state.json"

    def _ledger_path(self, gov):
        return Path(gov) / wgs.LEDGER_FILE_NAME

    def _load(self, gov):
        return json.loads(self._ledger_path(gov).read_text(encoding="utf-8"))

    def _record(self, gov, detection, *, run_id="run-test", session=None):
        issues, changed = wgs.record_detections(
            gov, [detection], run_id=run_id, session_id=session,
            hook_identity=wgs.GUARD_CLI_IDENTITY)
        self.assertEqual(issues, [])
        return changed

    def _open_records(self, ledger):
        return [r for r in ledger["violations"].values()
                if r["status"] == "open"]

    def _ensure_grant(self, gov):
        grant_id, issues = wgs.ensure_grant(
            gov, consumer=wgs.CLI_CONSUMER, run_id="run-test")
        self.assertEqual(issues, [])
        self.assertTrue(grant_id)
        return grant_id

    # ── R1 观测≠接受 / 重复 ──────────────────────────────────────────────

    def test_rule1_observation_is_not_acceptance(self):
        """R1 绿：记录即 open（消费事件/授权均空）；红相判据：重复观测不
        改变状态——未消费前违规不可能自行翻转（消费是唯一终态）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            detection = _detect(after="a" * 32)
            self._record(gov, detection)
            record = next(iter(self._load(gov)["violations"].values()))
            self.assertEqual(record["status"], "open")
            self.assertIsNone(record["consumption_event"])
            self.assertIsNone(record["grant_id"])
            self._record(gov, detection)  # 重复观测
            record = next(iter(self._load(gov)["violations"].values()))
            self.assertEqual(record["status"], "open")
            self.assertIsNone(record["consumption_event"])

    def test_rule1_same_violation_not_duplicated(self):
        """R1 重复：同违规（同对象同内容）重复检测 → 恰一条记录、occurrence
        不变、且为纯去重（零改写——changed=False）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            detection = _detect(after="a" * 32)
            self._record(gov, detection)
            changed = self._record(gov, detection)
            self.assertFalse(changed)
            ledger = self._load(gov)
            self.assertEqual(len(ledger["violations"]), 1)
            record = next(iter(ledger["violations"].values()))
            self.assertEqual(record["occurrence"], 1)

    def test_rule1_independent_trigger_supersedes_with_occurrence(self):
        """R1 独立再触发（同对象内容变更）→ 旧代 superseded、新代 open、
        occurrence=2、before_hash 链接旧内容（审计链）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            self._record(gov, _detect(after="a" * 32))
            self._record(gov, _detect(after="b" * 32, before="a" * 32))
            by_status = {}
            for record in self._load(gov)["violations"].values():
                by_status.setdefault(record["status"], []).append(record)
            self.assertEqual(len(by_status.get("superseded", [])), 1)
            self.assertEqual(len(by_status.get("open", [])), 1)
            new = by_status["open"][0]
            self.assertEqual(new["occurrence"], 2)
            self.assertEqual(new["before_hash"], "a" * 32)
            self.assertIn("supersedes", new["notes"])

    # ── R2 WARN 不改基线（基线对违规状态零权力） ─────────────────────────

    def test_rule2_baseline_advance_never_touches_violation_state(self):
        """R2：WARN 姿态基线照常推进（吸收差异窗口——既有行为），但基线
        写入对违规记录零权力——台账字节级不变、记录保持 open（任何经基线
        路径消费/改写违规的实现即挂）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            self._record(gov, _detect(after="a" * 32))
            before = self._load(gov)
            self._state_path(gov).write_text(
                wgs.state_json_text(_baseline_target()), encoding="utf-8")
            self.assertEqual(self._load(gov), before)
            record = next(iter(before["violations"].values()))
            self.assertEqual(record["status"], "open")

    # ── R3 同会话二次独立触发升级 ────────────────────────────────────────

    def test_rule3_same_session_second_trigger_escalates(self):
        """R3 绿：同会话同违规第二次独立触发 → escalated=True +
        escalated_at + occurrence=2。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            self._record(gov, _detect(after="a" * 32), session="session-x")
            self._record(gov, _detect(after="b" * 32), session="session-x")
            open_records = self._open_records(self._load(gov))
            self.assertEqual(len(open_records), 1)
            self.assertTrue(open_records[0]["escalated"])
            self.assertTrue(open_records[0]["escalated_at"])
            self.assertEqual(open_records[0]["occurrence"], 2)

    def test_rule3_cross_session_trigger_does_not_escalate(self):
        """R3 红相判据（升级边界）：不同会话的独立再触发不升级（跨会话
        累积是 R4 的持久性语义，不是升级信号）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            self._record(gov, _detect(after="a" * 32), session="session-x")
            self._record(gov, _detect(after="b" * 32), session="session-y")
            open_records = self._open_records(self._load(gov))
            self.assertEqual(len(open_records), 1)
            self.assertFalse(open_records[0]["escalated"])

    def test_rule3_unknown_session_never_escalates(self):
        """R3 保守退化：会话身份不可用（None）时宁可漏升不可误升——
        CLI 未注入 GOVERNANCE_SESSION_ID 的现实路径零误报升级。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            self._record(gov, _detect(after="a" * 32), session=None)
            self._record(gov, _detect(after="b" * 32), session=None)
            open_records = self._open_records(self._load(gov))
            self.assertEqual(len(open_records), 1)
            self.assertFalse(open_records[0]["escalated"])

    # ── R4 跨会话保留 ────────────────────────────────────────────────────

    def test_rule4_violations_persist_across_sessions(self):
        """R4：新会话新 run 重载台账 → 记录仍 open、first_seen 不变
        （台账是文件态，不随进程/会话消失；对象在场且未 Remediation 时
        完整状态机步进不消费——消费资格要求凭证或缺席）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            self._record(gov, _detect(after="a" * 32),
                         run_id="run-1", session="session-1")
            first_seen = next(iter(
                self._load(gov)["violations"].values()))["first_seen"]
            # 会话重启：全新 run/会话——完整状态机步进（检测/消费判定照跑）
            wgs.reconcile_violation_state(
                gov, state_path=self._state_path(gov), detections=[],
                records_index={"evidence-log.md": {
                    "kind": "text",
                    "by_key": {"EVD-9001": [
                        {"digest": "a" * 32, "credentialed": False}]}}},
                baseline_target=_baseline_target(),
                run_id="run-2", session_id="session-2")
            record = next(iter(self._load(gov)["violations"].values()))
            self.assertEqual(record["status"], "open")
            self.assertEqual(record["first_seen"], first_seen)

    def test_rule4_open_records_survive_state_baseline_rebuild(self):
        """R4 加强：对账基线文件重建（损坏重建路径——amnesty 重首见）不丢
        未决违规——台账独立于基线存续。"""
        with tempfile.TemporaryDirectory() as td:
            gov = RowFamilyReconciliationTests()._seed_gov(td)
            tracker = gov / "plan-tracker.md"
            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov):
                vw.check_governance_write_shapes(persist_state=True)
                (gov / "evidence-log.md").write_text(
                    RowFamilyReconciliationTests._EVD_SEED
                    + RowFamilyReconciliationTests._EVD_SEED2
                    + RowFamilyReconciliationTests._REVIEW_SEED
                    + "| EVD-8003 | FEAT-060 | bare | d | b | a | actor | "
                      "2026-09-24 | G11 | PASS |\n",
                    encoding="utf-8")
                vw.check_governance_write_shapes(persist_state=True)
                self.assertEqual(len(self._open_records(self._load(gov))), 1)
                # 基线文件重建（等价损坏重建后的首跑形态）
                (self._state_path(gov)).unlink()
                vw.check_governance_write_shapes(persist_state=True)
            self.assertEqual(len(self._open_records(self._load(gov))), 1)

    # ── R5 hook 消费权预授予 + 单次原子消费 ──────────────────────────────

    def test_rule5_granted_consumption_is_single_use(self):
        """R5 绿：预授予 → 单次原子消费成功（record consumed +
        consumption_event + grant used + pending 清空）；红相：同一授权的
        第二次消费被拒（grant_used），第二个违规保持 open。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            self._record(gov, _detect(object_id="EVD-9001",
                                      after="a" * 32))
            self._record(gov, _detect(object_id="EVD-9002",
                                      after="b" * 32))
            grant_id = self._ensure_grant(gov)
            ledger = self._load(gov)
            vids = sorted(ledger["violations"])
            payload = wgs.consume_violations(
                gov, self._state_path(gov), consumer=wgs.CLI_CONSUMER,
                grant_id=grant_id, violation_ids=[vids[0]],
                baseline_target=_baseline_target(), run_id="run-test")
            self.assertTrue(payload["ok"], payload)
            self.assertEqual(payload["consumed"], [vids[0]])
            record = self._load(gov)["violations"][vids[0]]
            self.assertEqual(record["status"], "consumed")
            self.assertEqual(record["consumption_event"]["consumer"],
                             wgs.CLI_CONSUMER)
            self.assertEqual(record["consumption_event"]["grant_id"],
                             grant_id)
            self.assertEqual(self._load(gov)["grants"][grant_id]["status"],
                             "used")
            self.assertIsNone(self._load(gov)["pending_txn"])
            # 红相：单次授权已燃——第二次消费被拒，第二个违规不动
            refused = wgs.consume_violations(
                gov, self._state_path(gov), consumer=wgs.CLI_CONSUMER,
                grant_id=grant_id, violation_ids=[vids[1]],
                baseline_target=_baseline_target(), run_id="run-test")
            self.assertFalse(refused["ok"])
            self.assertEqual(refused["error"], "grant_used")
            self.assertEqual(
                self._load(gov)["violations"][vids[1]]["status"], "open")
            self.assertIsNone(self._load(gov)["pending_txn"])  # 拒前零残留

    def test_rule5_forged_hook_identity_refused(self):
        """R5 伪造 hook（两腿）：①冒用注册身份 + 伪造授权 token →
        unknown_grant；②授权 token 属另一消费者（手工伪造台账样本——即
        伪造者的实际形态）→ forged_consumer。两腿均零残留（授权未燃、违规
        open、无 pending）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            self._record(gov, _detect(after="a" * 32))
            grant_id = self._ensure_grant(gov)
            vid = next(iter(self._load(gov)["violations"]))
            # 腿①：冒用注册身份 + 不存在的授权
            forged_token = wgs.consume_violations(
                gov, self._state_path(gov), consumer=wgs.CLI_CONSUMER,
                grant_id="grant-" + "f" * 32, violation_ids=[vid],
                baseline_target=_baseline_target(), run_id="run-test")
            self.assertFalse(forged_token["ok"])
            self.assertEqual(forged_token["error"], "unknown_grant")
            # 腿②：token 属他人（伪造者手工植入的台账样本）
            ledger = self._load(gov)
            ledger["grants"]["grant-" + "e" * 32] = {
                "consumer": "some-other-registered-consumer",
                "issued_at": "2026-09-24T00:00:00",
                "issued_by_run": "run-forged", "status": "active"}
            self._ledger_path(gov).write_text(
                json.dumps(ledger), encoding="utf-8")
            forged_id = wgs.consume_violations(
                gov, self._state_path(gov), consumer=wgs.CLI_CONSUMER,
                grant_id="grant-" + "e" * 32, violation_ids=[vid],
                baseline_target=_baseline_target(), run_id="run-test")
            self.assertFalse(forged_id["ok"])
            self.assertEqual(forged_id["error"], "forged_consumer")
            ledger = self._load(gov)
            self.assertEqual(ledger["violations"][vid]["status"], "open")
            self.assertEqual(ledger["grants"][grant_id]["status"], "active")
            self.assertIsNone(ledger["pending_txn"])

    def test_rule5_unregistered_hook_refused(self):
        """R5 无权 hook：未登记消费者既不能获得预授予（ensure_grant 拒绝）
        也不能消费（consume 拒绝）——消费权闭集在注册表，不在调用方。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            self._record(gov, _detect(after="a" * 32))
            vid = next(iter(self._load(gov)["violations"]))
            grant_id, issues = wgs.ensure_grant(
                gov, consumer="rogue-hook", run_id="run-test")
            self.assertIsNone(grant_id)
            self.assertEqual(issues[0]["type"], "unregistered_consumer")
            refused = wgs.consume_violations(
                gov, self._state_path(gov), consumer="rogue-hook",
                grant_id="grant-" + "0" * 32, violation_ids=[vid],
                baseline_target=_baseline_target(), run_id="run-test")
            self.assertFalse(refused["ok"])
            self.assertEqual(refused["error"], "unregistered_consumer")
            self.assertEqual(
                self._load(gov)["violations"][vid]["status"], "open")

    # ── R6 台账损坏时不吸收不前移 ────────────────────────────────────────

    def test_rule6_corrupted_ledger_no_absorb_no_advance(self):
        """R6：台账损坏 → 响亮披露 + 基线冻结（新裸变更也不吸收——下一轮
        可重录）+ 零写入（损坏字节原样）；face 恒 PASS（WARN 姿态）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = RowFamilyReconciliationTests()._seed_gov(td)
            tracker = gov / "plan-tracker.md"
            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov):
                vw.check_governance_write_shapes(persist_state=True)
                (gov / "evidence-log.md").write_text(
                    RowFamilyReconciliationTests._EVD_SEED
                    + RowFamilyReconciliationTests._EVD_SEED2
                    + RowFamilyReconciliationTests._REVIEW_SEED
                    + "| EVD-8003 | FEAT-060 | bare | d | b | a | actor | "
                      "2026-09-24 | G11 | PASS |\n",
                    encoding="utf-8")
                self._ledger_path(gov).write_text("{not valid json",
                                                  encoding="utf-8")
                state_before = self._state_path(gov).read_bytes()
                ledger_before = self._ledger_path(gov).read_bytes()
                result = vw.check_governance_write_shapes(persist_state=True)
            face = result["row_families"]
            self.assertEqual(face["status"], "PASS")  # WARN 姿态不 FAIL
            kinds = [i["type"] for i in face["issues"]]
            self.assertIn("violation_ledger_unreadable", kinds)
            self.assertEqual(self._state_path(gov).read_bytes(),
                             state_before)   # 不前移（不吸收）
            self.assertEqual(self._ledger_path(gov).read_bytes(),
                             ledger_before)  # 零写入

    def test_rule6_repaired_ledger_reopens_window_and_converges(self):
        """R6 恢复腿：人工修复台账（重建空台账）后 → 冻结窗口重开 →
        违规重新检测入账（收敛到一致状态）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = RowFamilyReconciliationTests()._seed_gov(td)
            tracker = gov / "plan-tracker.md"
            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov):
                vw.check_governance_write_shapes(persist_state=True)
                (gov / "evidence-log.md").write_text(
                    RowFamilyReconciliationTests._EVD_SEED
                    + RowFamilyReconciliationTests._EVD_SEED2
                    + RowFamilyReconciliationTests._REVIEW_SEED
                    + "| EVD-8003 | FEAT-060 | bare | d | b | a | actor | "
                      "2026-09-24 | G11 | PASS |\n",
                    encoding="utf-8")
                self._ledger_path(gov).write_text("{not valid json",
                                                  encoding="utf-8")
                vw.check_governance_write_shapes(persist_state=True)
                # 人工修复：空合法台账（删除=丢失持久状态，已在披露中言明）
                self._ledger_path(gov).write_text(
                    json.dumps({"schema_version": 1, "tool": wgs.TOOL_ID,
                                "updated_at": None, "violations": {},
                                "grants": {}, "pending_txn": None}),
                    encoding="utf-8")
                vw.check_governance_write_shapes(persist_state=True)
            self.assertEqual(len(self._open_records(self._load(gov))), 1)

    def test_ledger_validation_requires_canonical_fields(self):
        """P3（review-FEAT-060-R0）：记录缺规范字段（截断/篡改形态）→
        load_ledger 判损坏（R6 fail-closed，指名缺失字段），不再仅凭
        status 放行；十二规范字段在场时校验通过（其余测试隐式覆盖）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            self._record(gov, _detect(after="a" * 32))
            ledger = self._load(gov)
            vid = next(iter(ledger["violations"]))
            del ledger["violations"][vid]["occurrence"]
            self._ledger_path(gov).write_text(json.dumps(ledger),
                                              encoding="utf-8")
            loaded, issue = wgs.load_ledger(gov)
            self.assertIsNone(loaded)
            self.assertEqual(issue["type"], "violation_ledger_unreadable")
            self.assertIn("occurrence", issue["detail"])

    # ── ops 可恢复事务：消费后崩溃 / 基线写崩 ────────────────────────────

    def _seed_two_violations_with_state(self, gov):
        """Baseline state file on disk + two open violations + a grant."""
        self._state_path(gov).write_text(
            wgs.state_json_text(_baseline_target(
                {"evidence-log.md": {"sha256": "old", "rows": {}}})),
            encoding="utf-8")
        self._record(gov, _detect(object_id="EVD-9001", after="a" * 32),
                     run_id="run-1")
        self._record(gov, _detect(object_id="EVD-9002", after="b" * 32),
                     run_id="run-1")
        return self._ensure_grant(gov), sorted(self._load(gov)["violations"])

    def test_consume_crash_during_baseline_write_recovers(self):
        """消费事务在基线写入步崩溃（kill 模拟——异常注入）：残留 = 仅
        journal（pending_txn），违规仍 open、授权仍 active、基线保持旧字节
        ——无半状态；重跑恢复（世界=事务前像 → 重放基线写 → 收尾）→
        consumed + 授权燃尽 + 基线 = 事务目标，无二次应用。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            grant_id, vids = self._seed_two_violations_with_state(gov)
            state_before = self._state_path(gov).read_bytes()
            target = _baseline_target({"evidence-log.md": {
                "sha256": "new", "rows": {}}})
            real_write = wgs._atomic_write_bytes
            calls = {"n": 0}

            def flaky_write(path, data):
                calls["n"] += 1
                if calls["n"] == 2:  # call 1 = journal, call 2 = baseline
                    raise OSError("simulated crash: baseline write killed")
                return real_write(path, data)

            with mock.patch.object(wgs, "_atomic_write_bytes", flaky_write):
                with self.assertRaises(OSError):
                    wgs.consume_violations(
                        gov, self._state_path(gov),
                        consumer=wgs.CLI_CONSUMER, grant_id=grant_id,
                        violation_ids=[vids[0]],
                        baseline_target=target, run_id="run-test")
            # 残留 = 仅 journal；世界无半状态
            ledger = self._load(gov)
            self.assertIsNotNone(ledger["pending_txn"])
            self.assertEqual(ledger["pending_txn"]["baseline_target"],
                             target)
            self.assertEqual(ledger["violations"][vids[0]]["status"],
                             "open")
            self.assertEqual(ledger["grants"][grant_id]["status"], "active")
            self.assertEqual(self._state_path(gov).read_bytes(),
                             state_before)
            # 恢复：世界=事务前像 → 重放基线写 → 收尾（日志不凌驾世界）
            issues, completed, consumed = wgs.resume_pending_txn(
                gov, self._state_path(gov))
            self.assertEqual(issues, [])
            self.assertTrue(completed)
            self.assertEqual(consumed, [vids[0]])
            self.assertEqual(
                self._state_path(gov).read_bytes(),
                wgs.state_json_text(target).encode("utf-8"))
            ledger = self._load(gov)
            self.assertEqual(ledger["violations"][vids[0]]["status"],
                             "consumed")
            self.assertEqual(ledger["grants"][grant_id]["status"], "used")
            self.assertIsNone(ledger["pending_txn"])

    def test_consume_crash_during_finalize_recovers(self):
        """消费事务在收尾步崩溃（基线已写、台账未收尾）：残留 = journal +
        基线已在目标态；重跑恢复走「世界=目标 → 仅收尾」支——基线零二次
        写（字节恒等）、违规 consumed、授权燃尽。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            grant_id, vids = self._seed_two_violations_with_state(gov)
            target = _baseline_target({"evidence-log.md": {
                "sha256": "new", "rows": {}}})
            real_save = wgs.save_ledger
            calls = {"n": 0}

            def flaky_save(gdir, ledger):
                calls["n"] += 1
                if calls["n"] == 2:  # call 1 = journal, call 2 = finalize
                    raise OSError("simulated crash: finalize killed")
                return real_save(gdir, ledger)

            with mock.patch.object(wgs, "save_ledger", flaky_save):
                with self.assertRaises(OSError):
                    wgs.consume_violations(
                        gov, self._state_path(gov),
                        consumer=wgs.CLI_CONSUMER, grant_id=grant_id,
                        violation_ids=[vids[0]],
                        baseline_target=target, run_id="run-test")
            # 残留：基线已在目标态（phase 2 完成）、journal 在、违规仍 open
            self.assertEqual(
                self._state_path(gov).read_bytes(),
                wgs.state_json_text(target).encode("utf-8"))
            self.assertIsNotNone(self._load(gov)["pending_txn"])
            self.assertEqual(self._load(gov)["violations"][vids[0]]["status"],
                             "open")
            baseline_at_crash = self._state_path(gov).read_bytes()
            issues, completed, consumed = wgs.resume_pending_txn(
                gov, self._state_path(gov))
            self.assertEqual(issues, [])
            self.assertTrue(completed)
            self.assertEqual(consumed, [vids[0]])
            self.assertEqual(self._state_path(gov).read_bytes(),
                             baseline_at_crash)  # 零二次基线写
            ledger = self._load(gov)
            self.assertEqual(ledger["violations"][vids[0]]["status"],
                             "consumed")
            self.assertIsNone(ledger["pending_txn"])

    def test_resume_diverged_world_refuses_to_advance(self):
        """恢复第三支（fail-safe）：世界既非事务目标也非事务前像 → 响亮
        披露 violation_txn_diverged、拒绝推进（不吸收不前移不写违规）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            grant_id, vids = self._seed_two_violations_with_state(gov)
            real_write = wgs._atomic_write_bytes
            calls = {"n": 0}

            def flaky_write(path, data):
                calls["n"] += 1
                if calls["n"] == 2:
                    raise OSError("simulated crash: baseline write killed")
                return real_write(path, data)

            with mock.patch.object(wgs, "_atomic_write_bytes",
                                   flaky_write):
                with self.assertRaises(OSError):
                    wgs.consume_violations(
                        gov, self._state_path(gov),
                        consumer=wgs.CLI_CONSUMER, grant_id=grant_id,
                        violation_ids=[vids[0]],
                        baseline_target=_baseline_target(
                            {"evidence-log.md": {"sha256": "new",
                                                 "rows": {}}}),
                        run_id="run-test")
            diverged = b'{"diverged": "world moved on"}'
            self._state_path(gov).write_bytes(diverged)
            issues, completed, consumed = wgs.resume_pending_txn(
                gov, self._state_path(gov))
            self.assertFalse(completed)
            self.assertEqual(consumed, [])
            self.assertEqual(issues[0]["type"], "violation_txn_diverged")
            self.assertEqual(self._state_path(gov).read_bytes(), diverged)
            self.assertEqual(self._load(gov)["violations"][vids[0]]["status"],
                             "open")
            self.assertIsNotNone(self._load(gov)["pending_txn"])

    # ── 并发 ─────────────────────────────────────────────────────────────

    def test_plain_advance_defers_when_state_lock_held(self):
        """P1-1（review-FEAT-060-R0）锁覆盖证明：状态文件锁被他进程持有时，
        plain 推进让行（返回 False + lock busy）且零写入——修复前 plain 路径
        无锁、会直接写字节（红相判据）；锁释放后照常推进（绿相）。模拟他进程
        持锁 = 手工创建 O_EXCL 锁文件（同进程 _TargetLock 经 inproc 互斥天然
        串行，StoreError 竞争面只在跨进程）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            state_path = self._state_path(gov)
            state_path.write_text(
                wgs.state_json_text(_baseline_target()), encoding="utf-8")
            before = state_path.read_bytes()
            other = _baseline_target({"evidence-log.md": {
                "sha256": "x", "rows": {}}})
            lock_dir = gov / ".governance-store-locks"
            lock_dir.mkdir(exist_ok=True)
            lock_file = lock_dir / ".write-guard-state.json.lock"
            lock_file.write_text("999999", encoding="utf-8")  # 他进程持锁
            advanced, detail = wgs.advance_baseline_plain(
                state_path, wgs.state_json_text(other), timeout_seconds=0.3)
            self.assertFalse(advanced)
            self.assertIn("lock busy", detail)
            self.assertEqual(state_path.read_bytes(), before)  # 零写入
            lock_file.unlink()  # 他进程完成 → 锁空闲
            advanced, detail = wgs.advance_baseline_plain(
                state_path, wgs.state_json_text(other))
            self.assertTrue(advanced, detail)
            self.assertIsNone(detail)
            # 文本层比较（write_text 在 Windows 做 \n→os.linesep 翻译，与
            # 既有 plain 路径一致；txn sha 比对两侧同法计算，不受影响）
            self.assertEqual(state_path.read_text(encoding="utf-8"),
                             wgs.state_json_text(other))

    def test_concurrent_resume_and_reconcile_stay_coherent(self):
        """P1-1 并发不变量：崩溃残留的在途事务 × 并发第二进程形态的完整
        reconcile 步（resume→记录→消费→plain 推进全流程）→ 无 diverged
        披露、pending 收敛为 None、事务违规 consumed、基线终态 = 某一完整
        目标字节（共锁下两路各自完整推进，last-writer-wins 语义等价——
        两路的 files 内容同源，仅 updated_at 异）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            grant_id, vids = self._seed_two_violations_with_state(gov)
            target_a = _baseline_target({"evidence-log.md": {
                "sha256": "new", "rows": {}}})
            real_write = wgs._atomic_write_bytes
            calls = {"n": 0}

            def flaky_write(path, data):
                calls["n"] += 1
                if calls["n"] == 2:
                    raise OSError("simulated crash: baseline write killed")
                return real_write(path, data)

            with mock.patch.object(wgs, "_atomic_write_bytes", flaky_write):
                with self.assertRaises(OSError):
                    wgs.consume_violations(
                        gov, self._state_path(gov),
                        consumer=wgs.CLI_CONSUMER, grant_id=grant_id,
                        violation_ids=[vids[0]],
                        baseline_target=target_a, run_id="run-crash")
            target_b = _baseline_target({"evidence-log.md": {
                "sha256": "new2", "rows": {}}})
            results = {}

            def resume_leg():
                results["resume"] = wgs.resume_pending_txn(
                    gov, self._state_path(gov))

            def reconcile_leg():
                results["reconcile"] = wgs.reconcile_violation_state(
                    gov, state_path=self._state_path(gov), detections=[],
                    records_index={}, baseline_target=target_b,
                    run_id="run-b")

            threads = [threading.Thread(target=resume_leg),
                       threading.Thread(target=reconcile_leg)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            resume_issues = results["resume"][0]
            reconcile_issues = results["reconcile"]["issues"]
            diverged = [i for i in resume_issues + reconcile_issues
                        if i["type"] == "violation_txn_diverged"]
            self.assertEqual(diverged, [], (resume_issues, reconcile_issues))
            ledger = self._load(gov)
            self.assertIsNone(ledger["pending_txn"])
            self.assertEqual(ledger["violations"][vids[0]]["status"],
                             "consumed")
            final = self._state_path(gov).read_bytes()
            self.assertIn(final, (
                wgs.state_json_text(target_a).encode("utf-8"),
                wgs.state_json_text(target_b).encode("utf-8")))

    def test_concurrent_recordings_serialize(self):
        """并发：多线程同时记录不同违规 → 全部落账、台账为合法 JSON、零
        异常（_TargetLock 串行化——同进程 inproc 互斥 + O_EXCL 锁文件）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            errors = []

            def worker(i):
                try:
                    issues, _changed = wgs.record_detections(
                        gov,
                        [_detect(object_id="EVD-90%02d" % i,
                                 after=("%02d" % i) * 16)],
                        run_id="run-%d" % i)
                    if issues:
                        errors.append(issues)
                except BaseException as exc:  # pragma: no cover — 诊断面
                    errors.append(exc)

            threads = [threading.Thread(target=worker, args=(i,))
                       for i in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(errors, [])
            ledger = self._load(gov)
            self.assertEqual(len(ledger["violations"]), 4)

    # ── 消费资格判定（消费门核心） ───────────────────────────────────────

    def test_eligibility_requires_credential_or_absence(self):
        """消费资格：对象在场且无凭证 → 不资格（保持 open）；对象已带凭证
        / 对象消失 / 受管面整体消失 → 资格；面不可读 → 不资格（fail-safe，
        不消费判不了的东西）。"""
        ledger = {"schema_version": 1, "tool": wgs.TOOL_ID,
                  "updated_at": None, "violations": {
                      "WV-1": {"status": "open", "family": "evidence-log.md",
                               "object_id": "EVD-1"}},
                  "grants": {}, "pending_txn": None}
        # 在场无凭证 → 不资格
        index = {"evidence-log.md": {"kind": "text", "by_key": {
            "EVD-1": [{"digest": "x", "credentialed": False}]}}}
        self.assertEqual(wgs.eligible_open_violation_ids(ledger, index), [])
        # 在场带凭证 → 资格
        index["evidence-log.md"]["by_key"]["EVD-1"] = [
            {"digest": "x", "credentialed": True}]
        self.assertEqual(wgs.eligible_open_violation_ids(ledger, index),
                         ["WV-1"])
        # 对象消失 / 受管面整体消失 → 资格
        self.assertEqual(wgs.eligible_open_violation_ids(
            ledger, {"evidence-log.md": {"kind": "text", "by_key": {}}}),
            ["WV-1"])
        self.assertEqual(wgs.eligible_open_violation_ids(ledger, {}),
                         ["WV-1"])
        # 面不可读 → 不资格
        self.assertEqual(wgs.eligible_open_violation_ids(
            ledger, {"evidence-log.md": {"kind": "unreadable"}}), [])

    # ── CLI 集成（WARN 姿态输出零变化 + 记录/消费闭环 + 会话升级） ───────

    _BARE_ROW = ("| EVD-8003 | FEAT-060 | bare | d | b | a | actor | "
                 "2026-09-24 | G11 | PASS |\n")

    def _seed_and_record(self, gov):
        """amnesty 基线 + 裸变更首次 guard run → 违规入账（返回 open record
        与检测轮 face 结果——该轮即 WARN 判定面）。"""
        RowFamilyReconciliationTests()._seed_gov(gov)
        tracker = gov / "plan-tracker.md"
        with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
             mock.patch.object(vw, "GOVERNANCE_DIR", gov):
            vw.check_governance_write_shapes(persist_state=True)
            (gov / "evidence-log.md").write_text(
                RowFamilyReconciliationTests._EVD_SEED
                + RowFamilyReconciliationTests._EVD_SEED2
                + RowFamilyReconciliationTests._REVIEW_SEED
                + self._BARE_ROW,
                encoding="utf-8")
            detect_result = vw.check_governance_write_shapes(
                persist_state=True)
        open_records = self._open_records(self._load(gov))
        self.assertEqual(len(open_records), 1)
        return open_records[0], detect_result

    def test_cli_records_violation_with_unchanged_warn_output(self):
        """CLI 集成：裸变更 → 检测轮 WARN 判定面字节不变
        （unattributed_row_change 措辞/字段原样、face 恒 PASS），底下多出
        持久 open 记录（12 规范字段全在）；CLI stdout 零新增行（不含
        violation/ledger 字样）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            record, detect_result = self._seed_and_record(gov)
            for key in ("violation_id", "family", "object_id", "before_hash",
                        "after_hash", "workflow_run_id", "hook_identity",
                        "first_seen", "occurrence", "status", "grant_id",
                        "consumption_event"):
                self.assertIn(key, record)
            self.assertEqual(record["type"], "unattributed_row_change")
            self.assertEqual(record["object_id"], "EVD-8003")
            self.assertEqual(record["hook_identity"], wgs.GUARD_CLI_IDENTITY)
            face = detect_result["row_families"]
            self.assertEqual(face["status"], "PASS")
            warn = [i for i in face["issues"]
                    if i["type"] == "unattributed_row_change"]
            self.assertEqual(len(warn), 1)  # 判定面照常（记录不改变披露）
            self.assertIn("WARN 姿态 0.86.0", warn[0]["detail"])
            self.assertIn("分族 BLOCK 机制已交付未激活", warn[0]["detail"])
            self.assertIn("unattributed row change", warn[0]["detail"])
            buf = io.StringIO()
            tracker = gov / "plan-tracker.md"
            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov), \
                 mock.patch("sys.stdout", buf):
                vw.cmd_governance_write_guard(types.SimpleNamespace())
            self.assertNotIn("violation", buf.getvalue())
            self.assertNotIn("ledger", buf.getvalue())

    def test_cli_remediation_consumes_granted(self):
        """CLI 集成：补救（行获得机器凭证）→ 下一轮 guard 消费（granted、
        原子）→ 零 WARN、record consumed、授权燃尽。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            record, _detect_result = self._seed_and_record(gov)
            (gov / "evidence-log.md").write_text(
                RowFamilyReconciliationTests._EVD_SEED
                + RowFamilyReconciliationTests._EVD_SEED2
                + RowFamilyReconciliationTests._REVIEW_SEED
                + "| EVD-8003 | FEAT-060 | fixed | b（机器写入："
                  "governance-store evidence-append op-" + "a" * 32
                + "；schema v1） | a | governance-store | 2026-09-24 | G11 "
                  "| PASS |\n",
                encoding="utf-8")
            tracker = gov / "plan-tracker.md"
            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov):
                result = vw.check_governance_write_shapes(
                    persist_state=True)
            face = result["row_families"]
            self.assertEqual(
                [i for i in face["issues"]
                 if i["type"] == "unattributed_row_change"], [])
            ledger = self._load(gov)
            consumed = ledger["violations"][record["violation_id"]]
            self.assertEqual(consumed["status"], "consumed")
            self.assertEqual(consumed["consumption_event"]["consumer"],
                             wgs.CLI_CONSUMER)
            self.assertTrue(ledger["grants"])
            self.assertTrue(
                all(g["status"] == "used"
                    for g in ledger["grants"].values()))
            self.assertIsNone(ledger["pending_txn"])

    def test_cli_env_session_escalates_second_trigger(self):
        """CLI 集成（R3 接线）：GOVERNANCE_SESSION_ID 注入后，同会话内同一
        对象第二次独立触发 → 新代记录 occurrence=2 + escalated=True。"""
        with tempfile.TemporaryDirectory() as td:
            gov = RowFamilyReconciliationTests()._seed_gov(td)
            tracker = gov / "plan-tracker.md"
            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov), \
                 mock.patch.dict(os.environ,
                                 {wgs.SESSION_ENV: "session-x"}):
                vw.check_governance_write_shapes(persist_state=True)
                (gov / "evidence-log.md").write_text(
                    RowFamilyReconciliationTests._EVD_SEED
                    + RowFamilyReconciliationTests._EVD_SEED2
                    + RowFamilyReconciliationTests._REVIEW_SEED
                    + self._BARE_ROW,
                    encoding="utf-8")
                vw.check_governance_write_shapes(persist_state=True)
                (gov / "evidence-log.md").write_text(
                    RowFamilyReconciliationTests._EVD_SEED
                    + RowFamilyReconciliationTests._EVD_SEED2
                    + RowFamilyReconciliationTests._REVIEW_SEED
                    + self._BARE_ROW.replace("| bare |", "| bare-again |"),
                    encoding="utf-8")
                vw.check_governance_write_shapes(persist_state=True)
            open_records = self._open_records(self._load(gov))
            self.assertEqual(len(open_records), 1)
            self.assertEqual(open_records[0]["occurrence"], 2)
            self.assertTrue(open_records[0]["escalated"])
            self.assertEqual(open_records[0]["session_id"], "session-x")

    def test_probe_never_writes_violation_ledger(self):
        """probe 路径（persist_state=False）：有裸变更在场也零写入——不建
        台账、不动基线（对账窗口零消费，contract-matrix 同路径）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = RowFamilyReconciliationTests()._seed_gov(td)
            tracker = gov / "plan-tracker.md"
            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov):
                vw.check_governance_write_shapes(persist_state=True)
                (gov / "evidence-log.md").write_text(
                    RowFamilyReconciliationTests._EVD_SEED
                    + RowFamilyReconciliationTests._EVD_SEED2
                    + RowFamilyReconciliationTests._REVIEW_SEED
                    + self._BARE_ROW,
                    encoding="utf-8")
                vw.check_governance_write_shapes(persist_state=False)
            self.assertFalse(self._ledger_path(gov).is_file())

    def test_state_serializer_is_single_source(self):
        """FIX-292 纪律：引擎 plain-advance 写基线与事务 resume 比对用的是
        同一序列化器（verify_workflow 委托 write_guard_state.state_json_text
        ——第二序列化器即漂移）。"""
        target = _baseline_target({"evidence-log.md": {"sha256": "x",
                                                       "rows": {}}})
        self.assertEqual(vw._write_guard_state_json(target),
                         wgs.state_json_text(target))


# ─── FEAT-064 — write-guard 分族 BLOCK 激活（0.88.0 阶段 D1 · P1）───────────
# （fixture 复用直接引用 RowFamilyReconciliationTests——模块级别名会让
#   pytest 把同一 TestCase 收集两遍）


def _activate(gov, families, posture="block"):
    """Test posture activation (the guard CLI management path's entity)."""
    payload, refusal = wgs.activate_family_postures(
        Path(gov), families=families, posture=posture,
        reason="FEAT-064 测试激活", authorized_by="test-coordinator")
    assert refusal is None, refusal
    return payload


def _guard_run(gov, persist_state=True, **kwargs):
    """One guard run against a temp governance dir (CLI-path parity)."""
    gov = Path(gov)
    tracker = gov / "plan-tracker.md"
    with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
         mock.patch.object(vw, "GOVERNANCE_DIR", gov):
        return vw.check_governance_write_shapes(
            persist_state=persist_state, **kwargs)


def _ledger(gov):
    return json.loads(
        (Path(gov) / wgs.LEDGER_FILE_NAME).read_text(encoding="utf-8"))


def _baseline_state(gov):
    return json.loads(
        (Path(gov) / ".write-guard-state.json").read_text(encoding="utf-8"))


def _row_issues(result):
    return [i for i in result["row_families"]["issues"]
            if i["type"] == "unattributed_row_change"]


def _block_issues(result):
    return [i for i in _row_issues(result) if i.get("posture") == "block"]


def _mg_args(**kwargs):
    """Namespace for the guard CLI management modes."""
    defaults = dict(activate_block=None, deactivate_block=None,
                    show_posture=False, break_grant=False, break_clear=False,
                    break_show=False, families="", reason="",
                    authorized_by="", ttl_hours=None, max_uses=None,
                    session_id=None)
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


class WriteGuardFamilyBlockPostureTests(unittest.TestCase):
    """FEAT-064 分族 BLOCK 机制：逐族姿态 / R2 BLOCK 翻转（基线钳制）/
    补救闭环 / fail-safe / 激活校验。默认全 WARN 时行为字节恒等（74 基线
    锚）——机制交付但真实翻转（上线动作）由 Coordinator 裁定执行。
    """

    def test_default_posture_all_warn_face_never_fails(self):
        """零回归锚：无姿态配置（默认全 WARN）→ 裸变更照旧 WARN、face 恒
        PASS、行为与 FEAT-060 时代字节同源（issue 文本含 FEAT-064 指引）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = RowFamilyReconciliationTests()._seed_gov(td)
            _guard_run(gov)
            (gov / "evidence-log.md").write_text(
                RowFamilyReconciliationTests._EVD_SEED + RowFamilyReconciliationTests._EVD_SEED2 + RowFamilyReconciliationTests._REVIEW_SEED
                + "| EVD-8003 | FEAT-064 | bare | d | b | a | actor | "
                  "2026-09-25 | G11 | PASS |\n",
                encoding="utf-8")
            result = _guard_run(gov)
            self.assertEqual(result["row_families"]["status"], "PASS")
            self.assertFalse((gov / wgs.POSTURE_CONFIG_FILE_NAME).is_file())
            issues = _row_issues(result)
            self.assertEqual(len(issues), 1)
            self.assertNotIn("posture", issues[0])

    def test_block_active_family_fails_face_and_warn_family_stays(self):
        """BLOCK 族裸变更 → face FAIL（issue 携 posture=block）；同轮
        task_status（WARN 族）裸变更仍为 WARN 披露——逐族姿态隔离。"""
        with tempfile.TemporaryDirectory() as td:
            gov = RowFamilyReconciliationTests()._seed_gov(td)
            _activate(gov, ["evidence"])
            _guard_run(gov)
            (gov / "evidence-log.md").write_text(
                RowFamilyReconciliationTests._EVD_SEED + RowFamilyReconciliationTests._EVD_SEED2 + RowFamilyReconciliationTests._REVIEW_SEED
                + "| EVD-8003 | FEAT-064 | bare | d | b | a | actor | "
                  "2026-09-25 | G11 | PASS |\n",
                encoding="utf-8")
            (gov / "plan-tracker.md").write_text(
                RowFamilyReconciliationTests._TRACKER_SEED.replace(
                    "🔄 进行中 (2026-09-19)", "✅ 完成 (2026-09-25)"),
                encoding="utf-8")
            result = _guard_run(gov)
            self.assertEqual(result["row_families"]["status"], "FAIL")
            blocks = _block_issues(result)
            self.assertEqual(len(blocks), 1)
            self.assertEqual(blocks[0]["task_id"], "EVD-8003")
            self.assertIn("BLOCK 姿态", blocks[0]["detail"])
            self.assertIn("FEAT-064", blocks[0]["detail"])
            warns = [i for i in _row_issues(result)
                     if i.get("posture") != "block"]
            self.assertEqual(len(warns), 1)
            self.assertEqual(warns[0]["task_id"], "FEAT-057")  # tracker row

    def test_block_window_not_absorbed_across_repeats(self):
        """场景① 重复运行：BLOCK 窗口逐轮重燃（不吸收——DEC-224 R2 翻转）；
        被阻塞面基线保持前像；重复观测纯去重（单条 open 记录）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = RowFamilyReconciliationTests()._seed_gov(td)
            _activate(gov, ["evidence"])
            _guard_run(gov)
            amnesty_evidence = _baseline_state(gov)["files"][
                "evidence-log.md"]
            (gov / "evidence-log.md").write_text(
                RowFamilyReconciliationTests._EVD_SEED + RowFamilyReconciliationTests._EVD_SEED2 + RowFamilyReconciliationTests._REVIEW_SEED
                + "| EVD-8003 | FEAT-064 | bare | d | b | a | actor | "
                  "2026-09-25 | G11 | PASS |\n",
                encoding="utf-8")
            first = _guard_run(gov)
            self.assertEqual(first["row_families"]["status"], "FAIL")
            self.assertEqual(len(self._open(gov)), 1)
            second = _guard_run(gov)
            self.assertEqual(second["row_families"]["status"], "FAIL")
            self.assertEqual(len(self._open(gov)), 1)  # R1 纯去重
            held = _baseline_state(gov)["files"]["evidence-log.md"]
            self.assertEqual(held, amnesty_evidence)  # 前像保持（不吸收）

    def _open(self, gov):
        return [r for r in _ledger(gov)["violations"].values()
                if r["status"] == "open"]

    def test_block_surface_held_while_warn_surface_absorbs(self):
        """R2 翻转的面粒度：BLOCK 面基线保持前像；同轮 WARN 面（任务状态列）
        窗口照旧吸收（DEC-224 钉住的 WARN 行为不变）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = RowFamilyReconciliationTests()._seed_gov(td)
            _activate(gov, ["evidence"])
            _guard_run(gov)
            amnesty = _baseline_state(gov)["files"]
            (gov / "evidence-log.md").write_text(
                RowFamilyReconciliationTests._EVD_SEED + RowFamilyReconciliationTests._EVD_SEED2 + RowFamilyReconciliationTests._REVIEW_SEED
                + "| EVD-8003 | FEAT-064 | bare | d | b | a | actor | "
                  "2026-09-25 | G11 | PASS |\n",
                encoding="utf-8")
            (gov / "plan-tracker.md").write_text(
                RowFamilyReconciliationTests._TRACKER_SEED.replace(
                    "🔄 进行中 (2026-09-19)", "✅ 完成 (2026-09-25)"),
                encoding="utf-8")
            _guard_run(gov)
            after = _baseline_state(gov)["files"]
            self.assertEqual(after["evidence-log.md"],
                             amnesty["evidence-log.md"])  # held
            self.assertNotEqual(after["plan-tracker.md"],
                                amnesty["plan-tracker.md"])  # absorbed

    def test_writer_remediation_consumes_and_unblocks(self):
        """补救闭环：写入器补机器凭证 → 复跑自动消费（事务）→ 面回 PASS、
        基线随事务收口（消费与基线更新同动——FEAT-060 机制在 BLOCK 下唯一
        合法解锁路径）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = RowFamilyReconciliationTests()._seed_gov(td)
            _activate(gov, ["evidence"])
            _guard_run(gov)
            (gov / "evidence-log.md").write_text(
                RowFamilyReconciliationTests._EVD_SEED + RowFamilyReconciliationTests._EVD_SEED2 + RowFamilyReconciliationTests._REVIEW_SEED
                + "| EVD-8003 | FEAT-064 | bare | d | b | a | actor | "
                  "2026-09-25 | G11 | PASS |\n",
                encoding="utf-8")
            blocked = _guard_run(gov)
            self.assertEqual(blocked["row_families"]["status"], "FAIL")
            violation_id = self._open(gov)[0]["violation_id"]
            (gov / "evidence-log.md").write_text(
                RowFamilyReconciliationTests._EVD_SEED + RowFamilyReconciliationTests._EVD_SEED2 + RowFamilyReconciliationTests._REVIEW_SEED
                + "| EVD-8003 | FEAT-064 | fixed | b（机器写入："
                  "governance-store evidence-append op-" + "a" * 32
                + "；schema v1） | a | governance-store | 2026-09-25 | G11 "
                  "| PASS |\n",
                encoding="utf-8")
            healed = _guard_run(gov)
            self.assertEqual(healed["row_families"]["status"], "PASS")
            record = _ledger(gov)["violations"][violation_id]
            self.assertEqual(record["status"], "consumed")
            self.assertEqual(
                _baseline_state(gov)["files"]["evidence-log.md"]["sha256"],
                __import__("hashlib").sha256(
                    (gov / "evidence-log.md").read_text(
                        encoding="utf-8").encode("utf-8")).hexdigest())

    def test_baseline_rebuild_withholds_blocked_surface(self):
        """基线重建边缘：BLOCK 族 open 违规在场且无前像条目 → fresh amnesty
        条目被扣留（block_window_baseline_hold 响亮披露）——重建不静默吸收
        未决窗口。"""
        with tempfile.TemporaryDirectory() as td:
            gov = RowFamilyReconciliationTests()._seed_gov(td)
            _activate(gov, ["evidence"])
            _guard_run(gov)
            (gov / "evidence-log.md").write_text(
                RowFamilyReconciliationTests._EVD_SEED + RowFamilyReconciliationTests._EVD_SEED2 + RowFamilyReconciliationTests._REVIEW_SEED
                + "| EVD-8003 | FEAT-064 | bare | d | b | a | actor | "
                  "2026-09-25 | G11 | PASS |\n",
                encoding="utf-8")
            _guard_run(gov)
            self.assertEqual(len(self._open(gov)), 1)
            (gov / ".write-guard-state.json").unlink()  # 基线重建（人工面）
            result = _guard_run(gov)
            holds = [i for i in result["row_families"]["issues"]
                     if i["type"] == "block_window_baseline_hold"]
            self.assertEqual(len(holds), 1)
            self.assertNotIn("evidence-log.md",
                             _baseline_state(gov)["files"])  # 扣留
            self.assertEqual(len(self._open(gov)), 1)  # 违规不丢（R4）

    def test_posture_config_corrupt_fails_safe_to_warn(self):
        """姿态配置损坏 → fail-safe 全 WARN + 响亮披露（不猜测、不静默）；
        恢复指引在场。"""
        with tempfile.TemporaryDirectory() as td:
            gov = RowFamilyReconciliationTests()._seed_gov(td)
            (gov / wgs.POSTURE_CONFIG_FILE_NAME).write_text(
                "{not json", encoding="utf-8")
            _guard_run(gov)
            (gov / "evidence-log.md").write_text(
                RowFamilyReconciliationTests._EVD_SEED + RowFamilyReconciliationTests._EVD_SEED2 + RowFamilyReconciliationTests._REVIEW_SEED
                + "| EVD-8003 | FEAT-064 | bare | d | b | a | actor | "
                  "2026-09-25 | G11 | PASS |\n",
                encoding="utf-8")
            result = _guard_run(gov)
            self.assertEqual(result["row_families"]["status"], "PASS")
            disclosed = [i for i in result["row_families"]["issues"]
                         if i["type"] == "write_guard_posture_config_unreadable"]
            self.assertEqual(len(disclosed), 1)
            self.assertIn("全 WARN", disclosed[0]["detail"])

    def test_activation_fail_closed_refusals(self):
        """激活/回退 fail-closed：空理由 / 空授权人 / 未知 family / 损坏
        既有配置全拒（姿态翻转不可静默）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = RowFamilyReconciliationTests()._seed_gov(td)
            cases = [
                ({"families": ["evidence"], "posture": "block",
                  "reason": "", "authorized_by": "c"}, "schema_violation"),
                ({"families": ["evidence"], "posture": "block",
                  "reason": "r", "authorized_by": ""}, "schema_violation"),
                ({"families": ["nope"], "posture": "block",
                  "reason": "r", "authorized_by": "c"}, "unknown_family"),
            ]
            for kwargs, code in cases:
                _payload, refusal = wgs.activate_family_postures(
                    Path(gov), **kwargs)
                self.assertEqual(refusal["error"], code)
            self.assertFalse(
                (gov / wgs.POSTURE_CONFIG_FILE_NAME).is_file())
            _activate(gov, ["evidence"])
            (gov / wgs.POSTURE_CONFIG_FILE_NAME).write_text(
                "corrupt", encoding="utf-8")
            _payload, refusal = wgs.activate_family_postures(
                Path(gov), families=["review"], posture="block",
                reason="r", authorized_by="c")
            self.assertEqual(refusal["error"], "posture_config_unreadable")


class WriteGuardBlockScenarioTests(unittest.TestCase):
    """FEAT-064 七场景 BLOCK 姿态验收（version-plan D1——与 FEAT-060 六规则
    同源扩展，BLOCK 下行为先见差异）。场景① 在分族姿态类覆盖；本类覆盖
    ②并发 / ③消费后崩溃 / ④基线写崩 / ⑤会话重启 / ⑥伪造 hook / ⑦无权 hook。
    """

    def _seed_blocked(self, gov):
        """amnesty → BLOCK 激活 → 裸变更一轮（open 违规 + 窗口在场）。"""
        gov = RowFamilyReconciliationTests()._seed_gov(gov)
        _activate(gov, ["evidence"])
        _guard_run(gov)
        (gov / "evidence-log.md").write_text(
            RowFamilyReconciliationTests._EVD_SEED + RowFamilyReconciliationTests._EVD_SEED2 + RowFamilyReconciliationTests._REVIEW_SEED
            + "| EVD-8003 | FEAT-064 | bare | d | b | a | actor | "
              "2026-09-25 | G11 | PASS |\n",
            encoding="utf-8")
        result = _guard_run(gov)
        self.assertEqual(result["row_families"]["status"], "FAIL")
        return gov

    def _open(self, gov):
        return [r for r in _ledger(gov)["violations"].values()
                if r["status"] == "open"]

    def test_scenario2_concurrent_block_runs_serialize(self):
        """场景② 并发：两次 guard CLI 并发（BLOCK 激活）→ 判定面双双 FAIL、
        单条 open 记录（串行去重）、无 diverged、基线一致保持前像。
        （补丁在主线程统一施加——mock.patch 的模块全局改写在跨线程交错
        捕获 original 时会互相泄漏，FIX-387 canary 实证。）"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed_blocked(Path(td))
            tracker = gov / "plan-tracker.md"
            results = {}

            def worker(tag):
                results[tag] = vw.check_governance_write_shapes(
                    persist_state=True)

            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov):
                threads = [threading.Thread(target=worker, args=("a",)),
                           threading.Thread(target=worker, args=("b",))]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
            for tag in ("a", "b"):
                self.assertEqual(results[tag]["row_families"]["status"],
                                 "FAIL", tag)
                self.assertEqual(len(_block_issues(results[tag])), 1, tag)
                diverged = [i for i in results[tag]["row_families"]["issues"]
                            if i["type"] == "violation_txn_diverged"]
                self.assertEqual(diverged, [], tag)
            self.assertEqual(len(self._open(gov)), 1)

    def test_scenario3_consume_crash_resume_under_block(self):
        """场景③ 消费后崩溃：补救后消费事务 phase-2 崩溃 → 仅 journal 残留
        （无半状态）→ 复跑 resume 查世界收敛（consumed、面回 PASS）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed_blocked(Path(td))
            violation_id = self._open(gov)[0]["violation_id"]
            (gov / "evidence-log.md").write_text(
                RowFamilyReconciliationTests._EVD_SEED + RowFamilyReconciliationTests._EVD_SEED2 + RowFamilyReconciliationTests._REVIEW_SEED
                + "| EVD-8003 | FEAT-064 | fixed | b（机器写入："
                  "governance-store evidence-append op-" + "a" * 32
                + "；schema v1） | a | governance-store | 2026-09-25 | G11 "
                  "| PASS |\n",
                encoding="utf-8")
            real_write = wgs._atomic_write_bytes

            def crash_state_write(path, data):
                if str(path).endswith(".write-guard-state.json"):
                    raise OSError("simulated crash: baseline write killed")
                return real_write(path, data)

            with mock.patch.object(wgs, "_atomic_write_bytes",
                                   crash_state_write):
                with self.assertRaises(OSError):
                    _guard_run(gov)
            self.assertIsNotNone(_ledger(gov).get("pending_txn"))
            healed = _guard_run(gov)
            diverged = [i for i in healed["row_families"]["issues"]
                        if i["type"] == "violation_txn_diverged"]
            self.assertEqual(diverged, [])
            self.assertEqual(healed["row_families"]["status"], "PASS")
            self.assertEqual(_ledger(gov)["violations"][violation_id]
                             ["status"], "consumed")

    def test_scenario4_baseline_write_crash_holds_window(self):
        """场景④ 基线写崩：plain 推进失败 → 响亮披露 + 窗口保持开放
        （BLOCK 下基线未推进 → 复跑窗口重燃，先见差异 = WARN 时代 face
        恒 PASS，BLOCK 下 face FAIL）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed_blocked(Path(td))

            def crash(path, state_text, timeout_seconds=10.0):
                raise OSError("disk full (simulated)")

            with mock.patch.object(wgs, "advance_baseline_plain", crash):
                result = _guard_run(gov)
            unwritable = [i for i in result["row_families"]["issues"]
                          if i["type"] == "row_family_state_unwritable"]
            self.assertEqual(len(unwritable), 1)
            self.assertEqual(result["row_families"]["status"], "FAIL")
            again = _guard_run(gov)
            self.assertEqual(again["row_families"]["status"], "FAIL")
            self.assertEqual(len(self._open(gov)), 1)

    def test_scenario5_session_restart_keeps_window_open(self):
        """场景⑤ 会话重启：无会话身份的新一轮（跨会话保留 R4）→ BLOCK
        窗口照旧重燃（基线保持前像），记录去重不重记。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed_blocked(Path(td))
            record_before = self._open(gov)[0]
            result = _guard_run(gov)  # 新 run id、无 session——重启形态
            self.assertEqual(result["row_families"]["status"], "FAIL")
            record_after = self._open(gov)[0]
            self.assertEqual(record_after["violation_id"],
                             record_before["violation_id"])
            self.assertEqual(record_after["occurrence"], 1)

    def test_scenario6_7_forged_and_unauthorized_cannot_lift_block(self):
        """场景⑥⑦ 伪造/无权 hook：未登记消费者与伪造身份的消费全拒
        （R5 红相）→ 违规保持 open、BLOCK 面持续 FAIL——无旁路。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed_blocked(Path(td))
            violation_id = self._open(gov)[0]["violation_id"]
            state_path = Path(gov) / ".write-guard-state.json"
            baseline_target = _baseline_target({"evidence-log.md": {
                "sha256": "x", "rows": {}}})
            # ⑦ 无权（未登记）消费者
            refused = wgs.consume_violations(
                Path(gov), state_path, consumer="unregistered/hook",
                grant_id="grant-x", violation_ids=[violation_id],
                baseline_target=baseline_target, run_id="run-x")
            self.assertFalse(refused["ok"])
            self.assertEqual(refused["error"], "unregistered_consumer")
            # ⑥ 伪造身份（授权 token 属他人——伪造者手工植入的台账样本，
            # FEAT-060 R5 腿② 同型）
            ledger = _ledger(gov)
            ledger["grants"]["grant-" + "e" * 32] = {
                "consumer": "some-other-registered-consumer",
                "issued_at": "2026-09-25T00:00:00",
                "issued_by_run": "run-forged", "status": "active"}
            (Path(gov) / wgs.LEDGER_FILE_NAME).write_text(
                json.dumps(ledger, ensure_ascii=False, indent=2,
                           sort_keys=True) + "\n", encoding="utf-8")
            forged = wgs.consume_violations(
                Path(gov), state_path, consumer=wgs.CLI_CONSUMER,
                grant_id="grant-" + "e" * 32, violation_ids=[violation_id],
                baseline_target=baseline_target, run_id="run-x")
            self.assertFalse(forged["ok"])
            self.assertEqual(forged["error"], "forged_consumer")
            result = _guard_run(gov)
            self.assertEqual(result["row_families"]["status"], "FAIL")
            self.assertEqual(self._open(gov)[0]["violation_id"],
                             violation_id)


class WriteGuardBreakGlassTests(unittest.TestCase):
    """FEAT-064 break-glass 恢复通道：限定留痕（对象/操作者/理由/有效期/
    次数）、不可静默记录、范围化降级、失效惰化、清理入史、fail-closed
    拒绝梯。"""

    def _seed_blocked(self, gov):
        gov = RowFamilyReconciliationTests()._seed_gov(gov)
        _activate(gov, ["evidence", "decision"])
        _guard_run(gov)
        (gov / "evidence-log.md").write_text(
            RowFamilyReconciliationTests._EVD_SEED + RowFamilyReconciliationTests._EVD_SEED2 + RowFamilyReconciliationTests._REVIEW_SEED
            + "| EVD-8003 | FEAT-064 | bare | d | b | a | actor | "
              "2026-09-25 | G11 | PASS |\n",
            encoding="utf-8")
        (gov / "decision-log.md").write_text(
            RowFamilyReconciliationTests._DEC_SEED
            + "| DEC-224 | 2026-09-25 | coordinator | 裸决策行 | "
              "依据：手写无凭证\n",
            encoding="utf-8")
        result = _guard_run(gov)
        self.assertEqual(result["row_families"]["status"], "FAIL")
        return gov

    def _open(self, gov):
        return [r for r in _ledger(gov)["violations"].values()
                if r["status"] == "open"]

    def test_grant_requires_block_active_and_full_audit(self):
        with tempfile.TemporaryDirectory() as td:
            gov = RowFamilyReconciliationTests()._seed_gov(td)
            grant, refusal = wgs.grant_break_glass(
                Path(gov), reason="r", authorized_by="c")
            self.assertIsNone(grant)
            self.assertEqual(refusal["error"], "no_block_active")
            _activate(gov, ["evidence"])
            grant, refusal = wgs.grant_break_glass(
                Path(gov), reason="", authorized_by="c")
            self.assertEqual(refusal["error"], "schema_violation")
            grant, refusal = wgs.grant_break_glass(
                Path(gov), reason="r", authorized_by="")
            self.assertEqual(refusal["error"], "schema_violation")
            grant, refusal = wgs.grant_break_glass(
                Path(gov), reason="r", authorized_by="c",
                families=["nope"])
            self.assertEqual(refusal["error"], "unknown_family")
            grant, refusal = wgs.grant_break_glass(
                Path(gov), reason="修复 guard 自身损坏", authorized_by="c")
            self.assertIsNone(refusal)
            self.assertEqual(grant["families"], [wgs.BREAK_GLASS_ALL])
            stored = _ledger(gov)["break_glass"]
            self.assertEqual(stored["grant_id"], grant["grant_id"])
            self.assertEqual(stored["uses"], [])
            second, refusal = wgs.grant_break_glass(
                Path(gov), reason="r", authorized_by="c")
            self.assertEqual(refusal["error"], "break_glass_active")

    def test_scope_limited_downgrade(self):
        """范围化降级：窗口只软化了 scoped 族的 BLOCK（evidence）；范围外
        （decision）BLOCK 照旧 FAIL——窗口是披露通道，不是全局钥匙。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed_blocked(Path(td))
            wgs.grant_break_glass(
                Path(gov), reason="修复", authorized_by="coord",
                families=["evidence"])
            result = _guard_run(gov)
            self.assertEqual(result["row_families"]["status"], "FAIL")
            blocks = _block_issues(result)
            self.assertEqual([i["task_id"] for i in blocks], ["DEC-224"])
            downgraded = [i for i in _row_issues(result)
                          if i["task_id"] == "EVD-8003"]
            self.assertEqual(len(downgraded), 1)
            self.assertNotIn("posture", downgraded[0])
            self.assertEqual(len(_ledger(gov)["break_glass"]["uses"]), 1)

    def test_use_audit_exhaustion_and_expiry(self):
        """次数/有效期：每次 CLI 运行记 use（不可静默）；用满即惰化 + 响亮
        披露；过期同惰化。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed_blocked(Path(td))
            grant, _ = wgs.grant_break_glass(
                Path(gov), reason="修复", authorized_by="coord",
                max_uses=1, ttl_hours=1.0)
            first = _guard_run(gov)
            self.assertEqual(first["row_families"]["status"], "PASS")
            inert = [i for i in first["row_families"]["issues"]
                     if i["type"] == "break_glass_inert"]
            self.assertEqual(inert, [])
            second = _guard_run(gov)
            self.assertEqual(second["row_families"]["status"], "FAIL")
            inert = [i for i in second["row_families"]["issues"]
                     if i["type"] == "break_glass_inert"]
            self.assertEqual(len(inert), 1)
            self.assertEqual(_block_issues(second)[0]["task_id"],
                             "EVD-8003")
            # 过期支：重置 uses 后把 expires_at 拨到过去
            ledger = _ledger(gov)
            ledger["break_glass"]["uses"] = []
            ledger["break_glass"]["expires_at"] = "2000-01-01T00:00:00"
            (Path(gov) / wgs.LEDGER_FILE_NAME).write_text(
                json.dumps(ledger, ensure_ascii=False, indent=2,
                           sort_keys=True) + "\n", encoding="utf-8")
            third = _guard_run(gov)
            self.assertEqual(third["row_families"]["status"], "FAIL")
            inert = [i for i in third["row_families"]["issues"]
                     if i["type"] == "break_glass_inert"]
            self.assertEqual(len(inert), 1)
            self.assertIn("expired", inert[0]["detail"])

    def test_clear_moves_grant_to_history(self):
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed_blocked(Path(td))
            grant, _ = wgs.grant_break_glass(
                Path(gov), reason="修复", authorized_by="coord")
            _guard_run(gov)
            _payload, refusal = wgs.clear_break_glass(
                Path(gov), cleared_by="", reason="done")
            self.assertEqual(refusal["error"], "schema_violation")
            payload, refusal = wgs.clear_break_glass(
                Path(gov), cleared_by="coord", reason="修复完成")
            self.assertIsNone(refusal)
            self.assertEqual(payload["cleared"], grant["grant_id"])
            ledger = _ledger(gov)
            self.assertIsNone(ledger["break_glass"])
            self.assertEqual(len(ledger["break_glass_history"]), 1)
            self.assertEqual(
                ledger["break_glass_history"][0]["clear_reason"], "修复完成")
            result = _guard_run(gov)
            self.assertEqual(result["row_families"]["status"], "FAIL")
            # 窗口清理后两个 BLOCK 族（evidence + decision）窗口全部重燃
            self.assertEqual(len(_block_issues(result)), 2)

    def test_management_cli_modes(self):
        """管理模式 CLI：激活/回退/show/break-grant/clear 愉快路径 +
        拒绝路径（exit 2 + stderr 结构化拒绝）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = RowFamilyReconciliationTests()._seed_gov(td)
            args = _mg_args(activate_block="evidence,decision",
                            reason="D1 翻转", authorized_by="coord")
            buf, err = io.StringIO(), io.StringIO()
            with mock.patch("sys.stdout", buf), \
                 mock.patch("sys.stderr", err):
                code = wgs.run_guard_management_cli("activate_block", args,
                                                    governance_dir=gov)
            self.assertEqual(code, 0)
            self.assertIn("BLOCK 已激活", buf.getvalue())
            self.assertTrue(
                (Path(gov) / wgs.POSTURE_CONFIG_FILE_NAME).is_file())
            with mock.patch("sys.stdout", buf), \
                 mock.patch("sys.stderr", err):
                code = wgs.run_guard_management_cli("show_posture",
                                                    _mg_args(),
                                                    governance_dir=gov)
            self.assertEqual(code, 0)
            self.assertIn("task_status", buf.getvalue())
            args = _mg_args(deactivate_block="evidence",
                            reason="B-12 回退演练", authorized_by="coord")
            with mock.patch("sys.stdout", buf), \
                 mock.patch("sys.stderr", err):
                code = wgs.run_guard_management_cli("deactivate_block", args,
                                                    governance_dir=gov)
            self.assertEqual(code, 0)
            postures, _issue = wgs.load_family_postures(Path(gov))
            self.assertEqual(postures["evidence"], "warn")
            self.assertEqual(postures["decision"], "block")
            args = _mg_args(break_grant=True, reason="x",
                            authorized_by="c")
            buf, err = io.StringIO(), io.StringIO()
            with mock.patch("sys.stdout", buf), \
                 mock.patch("sys.stderr", err):
                code = wgs.run_guard_management_cli("break_grant", args,
                                                    governance_dir=gov)
            self.assertEqual(code, 0)
            self.assertIn("限定留痕", buf.getvalue())
            args = _mg_args(break_grant=True, reason="", authorized_by="c")
            buf, err = io.StringIO(), io.StringIO()
            with mock.patch("sys.stdout", buf), \
                 mock.patch("sys.stderr", err):
                code = wgs.run_guard_management_cli("break_grant", args,
                                                    governance_dir=gov)
            self.assertEqual(code, 2)
            self.assertIn("[REFUSED]", err.getvalue())


class WriteGuardLegacyHandoverTests(unittest.TestCase):
    """FEAT-060 R0 遗留三件的 FEAT-064 兑现面：P2-1 hook_identity 消费不
    覆写（检测侧溯源保留）/ P2-2 A-B-A 会话序升级定案（会话累计触发计数）
    / GOVERNANCE_SESSION_ID→--session-id 接线（显式身份优先）。"""

    def test_hook_identity_preserved_through_consumption(self):
        """P2-1 红相钉住：消费收尾不得覆写 hook_identity（检测侧身份 =
        INVOKER_ENV 覆写形态；消费方身份只活在 consumption_event）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = RowFamilyReconciliationTests()._seed_gov(td)
            _guard_run(gov)
            (gov / "evidence-log.md").write_text(
                RowFamilyReconciliationTests._EVD_SEED + RowFamilyReconciliationTests._EVD_SEED2 + RowFamilyReconciliationTests._REVIEW_SEED
                + "| EVD-8003 | FEAT-064 | bare | d | b | a | actor | "
                  "2026-09-25 | G11 | PASS |\n",
                encoding="utf-8")
            with mock.patch.dict(
                    os.environ,
                    {wgs.INVOKER_ENV: "governance-write-guard/test-hook"}):
                _guard_run(gov)
            record = [r for r in _ledger(gov)["violations"].values()
                      if r["status"] == "open"][0]
            self.assertEqual(record["hook_identity"],
                             "governance-write-guard/test-hook")
            (gov / "evidence-log.md").write_text(
                RowFamilyReconciliationTests._EVD_SEED + RowFamilyReconciliationTests._EVD_SEED2 + RowFamilyReconciliationTests._REVIEW_SEED
                + "| EVD-8003 | FEAT-064 | fixed | b（机器写入："
                  "governance-store evidence-append op-" + "a" * 32
                + "；schema v1） | a | governance-store | 2026-09-25 | G11 "
                  "| PASS |\n",
                encoding="utf-8")
            _guard_run(gov)
            consumed = _ledger(gov)["violations"][record["violation_id"]]
            self.assertEqual(consumed["status"], "consumed")
            self.assertEqual(consumed["hook_identity"],
                             "governance-write-guard/test-hook")
            self.assertEqual(consumed["consumption_event"]["consumer"],
                             wgs.CLI_CONSUMER)

    def test_aba_session_sequence_escalates(self):
        """P2-2 定案 (a) 会话累计触发计数：x→y→x 序列中会话 x 的第二次独立
        触发升级（B1 字面语义——review-FEAT-060-R0 P2-2 缺口闭合）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            wgs.record_detections(
                gov, [_detect(object_id="EVD-9101", after="a" * 32)],
                run_id="run-1", session_id="x")
            wgs.record_detections(
                gov, [_detect(object_id="EVD-9101", after="b" * 32,
                              before="a" * 32)],
                run_id="run-2", session_id="y")
            wgs.record_detections(
                gov, [_detect(object_id="EVD-9101", after="c" * 32,
                              before="b" * 32)],
                run_id="run-3", session_id="x")
            open_records = [r for r in _ledger(gov)["violations"].values()
                            if r["status"] == "open"]
            self.assertEqual(len(open_records), 1)
            record = open_records[0]
            self.assertEqual(record["occurrence"], 3)
            self.assertTrue(record["escalated"])
            self.assertEqual(record["session_triggers"], {"x": 2, "y": 1})
            self.assertIsNotNone(record["escalated_at"])

    def test_alternating_sessions_without_repeat_do_not_escalate(self):
        """保守半边：x→y 各自首次触发不升级（宁可漏升不可误升）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td)
            wgs.record_detections(
                gov, [_detect(object_id="EVD-9102", after="a" * 32)],
                run_id="run-1", session_id="x")
            wgs.record_detections(
                gov, [_detect(object_id="EVD-9102", after="b" * 32,
                              before="a" * 32)],
                run_id="run-2", session_id="y")
            record = [r for r in _ledger(gov)["violations"].values()
                      if r["status"] == "open"][0]
            self.assertFalse(record["escalated"])
            self.assertEqual(record["session_triggers"], {"x": 1, "y": 1})

    def test_session_id_argument_overrides_env(self):
        """R3 接线：显式 --session-id 优先于 GOVERNANCE_SESSION_ID；同一
        显式身份下的第二次独立触发升级。"""
        with tempfile.TemporaryDirectory() as td:
            gov = RowFamilyReconciliationTests()._seed_gov(td)
            with mock.patch.dict(os.environ,
                                 {wgs.SESSION_ENV: "env-session"}):
                _guard_run(gov)
                (gov / "evidence-log.md").write_text(
                    RowFamilyReconciliationTests._EVD_SEED + RowFamilyReconciliationTests._EVD_SEED2 + RowFamilyReconciliationTests._REVIEW_SEED
                    + "| EVD-8003 | FEAT-064 | bare | d | b | a | actor | "
                      "2026-09-25 | G11 | PASS |\n",
                    encoding="utf-8")
                _guard_run(gov, session_id="arg-session")
                record = [r for r in _ledger(gov)["violations"].values()
                          if r["status"] == "open"][0]
                self.assertEqual(record["session_id"], "arg-session")
                (gov / "evidence-log.md").write_text(
                    RowFamilyReconciliationTests._EVD_SEED + RowFamilyReconciliationTests._EVD_SEED2 + RowFamilyReconciliationTests._REVIEW_SEED
                    + "| EVD-8003 | FEAT-064 | bare-2 | d | b | a | actor "
                      "| 2026-09-25 | G11 | PASS |\n",
                    encoding="utf-8")
                _guard_run(gov, session_id="arg-session")
            record = [r for r in _ledger(gov)["violations"].values()
                      if r["status"] == "open"][0]
            self.assertEqual(record["session_triggers"]["arg-session"], 2)
            self.assertTrue(record["escalated"])


class Feat061CompositionBlockTests(unittest.TestCase):
    """F-5 ② 组合测试：FEAT-064 BLOCK 激活后 FEAT-061 决策写入路径全部走
    写入器（零手工写入）——md 权威腿 / JSON 权威腿（含逐次追加 md 投影）/
    迁移投影逐字重放三腿在 decision 族 BLOCK 姿态下零 unattributed 检测。
    """

    _DEC_MD_SEED = (
        "# 当前项目决策记录\n\n"
        + "| DEC-223 | 2026-09-19 | coordinator | seed 决策行 | "
          "依据：存量 |\n")

    def _seed(self, td):
        gov = Path(td)
        (gov / "decision-log.md").write_text(self._DEC_MD_SEED,
                                             encoding="utf-8")
        _activate(gov, ["decision"])
        result = _guard_run(gov)
        self.assertEqual(result["row_families"]["status"], "PASS")
        return gov

    def _assert_zero_decision_detections(self, result):
        self.assertEqual(
            [i for i in _row_issues(result)
             if i["task_id"].startswith("DEC-")], [],
            result["row_families"]["issues"])
        self.assertEqual(result["row_families"]["status"], "PASS")

    def test_md_backend_append_zero_block_detections(self):
        """md 权威腿：decision_append（携机器标记）→ BLOCK 姿态下零检测。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed(td)
            appended = gstore.decision_append(
                decider="Coordinator", content="FEAT-064 组合测试决策行",
                governance_dir=Path(gov))
            self.assertEqual(appended["code"], "ok")
            result = _guard_run(gov)
            self._assert_zero_decision_detections(result)

    def test_json_backend_append_and_projection_zero_block_detections(self):
        """JSON 权威腿：store + authority JSON_ACTIVE → decision_append 走
        JSON 腿（逐次追加 md 投影）→ 投影行携机器标记 → BLOCK 下零检测。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed(td)
            items = drepo.classify_md_document(
                (gov / "decision-log.md").read_text(encoding="utf-8"))
            store = drepo.build_store_from_document(items)
            (gov / drepo.JSON_STORE_FILE).write_text(
                json.dumps(store, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
            drepo.write_authority_transition(
                gov, from_state=drepo.STATE_MD_ACTIVE,
                to_state=drepo.STATE_CUTOVER_FROZEN, expected_epoch=0,
                owner_token="tok-comp")
            drepo.write_authority_transition(
                gov, from_state=drepo.STATE_CUTOVER_FROZEN,
                to_state=drepo.STATE_JSON_ACTIVE, expected_epoch=1,
                owner_token="tok-comp")
            appended = gstore.decision_append(
                decider="Coordinator", content="FEAT-064 JSON 腿决策行",
                governance_dir=Path(gov))
            self.assertEqual(appended["code"], "ok")
            projected = (gov / "decision-log.md").read_text(
                encoding="utf-8")
            self.assertIn("FEAT-064 JSON 腿决策行", projected)
            self.assertIn("机器写入：governance-store decision-append",
                          projected)
            result = _guard_run(gov)
            self._assert_zero_decision_detections(result)

    def test_projection_render_replay_is_digest_identical(self):
        """迁移投影腿：store 逐字重放（render_markdown）→ 行摘要恒等 →
        BLOCK 姿态下整表重写零 diff（零手工写入组合义务的格式转换面）。"""
        with tempfile.TemporaryDirectory() as td:
            gov = self._seed(td)
            original = (gov / "decision-log.md").read_text(
                encoding="utf-8")
            items = drepo.classify_md_document(original)
            store = drepo.build_store_from_document(items)
            rendered = drepo.render_markdown(store)
            original_rows = {vw._write_guard_row_digest(line.strip())
                             for line in original.split("\n")
                             if line.strip().startswith("| DEC-")}
            rendered_rows = {vw._write_guard_row_digest(line.strip())
                             for line in rendered.split("\n")
                             if line.strip().startswith("| DEC-")}
            self.assertEqual(original_rows, rendered_rows)
            (gov / "decision-log.md").write_text(rendered,
                                                 encoding="utf-8")
            result = _guard_run(gov)
            self._assert_zero_decision_detections(result)


if __name__ == "__main__":
    unittest.main()
