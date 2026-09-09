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
        """活体金丝雀（真实 plan-tracker）：M1 签名命中集合 ⊆ 已知 M1 四行
        （FIX-222/223/224/279——FIX-293 将修数据，本守卫只检不改）。"""
        if not vw.SAMPLE_PATH.is_file():
            self.skipTest("no live plan-tracker under the host governance dir")
        result = vw.check_governance_write_shapes()
        flagged = {i["task_id"] for i in result["plan_tracker"]["issues"]}
        self.assertTrue(flagged.issubset(_KNOWN_M1_IDS), flagged)
        self.assertTrue(flagged, "live M1 four rows must be flagged (FEAT-011 "
                                 "acceptance: audit-149 §4 M1 live evidence)")


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


if __name__ == "__main__":
    unittest.main()
