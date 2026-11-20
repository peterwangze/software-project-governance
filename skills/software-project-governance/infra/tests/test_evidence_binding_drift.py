"""Goal-layer product contract activation and sensitive action checks."""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw  # noqa: E402
import checks.evidence_domain as ed  # noqa: E402


VALID_CONTRACT = {
    "user": "AI-assisted product owner using the governance workflow for release planning",
    "job_to_be_done": "Keep AI coding work tied to explicit user outcomes before implementation starts",
    "non_goals": [
        "Do not expand the task into unrelated release automation changes",
        "Do not treat evidence-log updates as a substitute for user-visible quality",
    ],
    "success_metrics": [
        "User-visible acceptance scenario is captured for the active task before code changes continue",
        "Runnable E2E validation command passes and proves the acceptance scenario is still satisfied",
    ],
    "competitive_baseline": "Mature software teams require explicit acceptance criteria and validation before implementation closure",
    "done_definition": [
        "Product success evidence is recorded with concrete facts",
        "Independent review confirms the user outcome is not replaced by process completion",
    ],
}

_DEMO_TASK_ID = "FIX-099"



def _plan_tracker_text(goal_face=True, with_active_task=True):
    """Minimal host plan-tracker: goal face + one active P1 task row."""
    lines = [
        "# Plan Tracker — demo-host",
        "## 项目配置",
        "- workflow_model: classic-phase-gate",
    ]
    if goal_face:
        lines += [
            "## 项目总览",
            "",
            "| 项目 | 当前阶段 |",
            "| --- | --- |",
            "| demo-host | 维护与演进 |",
        ]
    if with_active_task:
        lines += [
            "## 当前活跃事项",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            "| **P1** | {0} | Demo unit for RB-2 gate fixtures | - | 0.90.0 "
            "| fixture | 📋 待启动 |".format(_DEMO_TASK_ID),
        ]
    return "\n".join(lines) + "\n"


def _seed_gov(gov_dir, plan_text=None, evidence_text=None):
    """Create the .governance dir and write the plan/evidence faces."""
    gov_dir.mkdir(parents=True, exist_ok=True)
    (gov_dir / "plan-tracker.md").write_text(
        plan_text if plan_text is not None else _plan_tracker_text(),
        encoding="utf-8")
    (gov_dir / "evidence-log.md").write_text(
        evidence_text if evidence_text is not None else "# Evidence Log\n",
        encoding="utf-8")
    return gov_dir


class _HostFixture:
    """A temp host with a .governance/ dir; patches the vw faces on enter."""

    def __init__(self, tmp, plan_text=None, plan_bytes=None,
                 evidence_text=None, runtime=None, packets=None):
        self.root = Path(tmp)
        self.gov = self.root / ".governance"
        _seed_gov(self.gov,
                  plan_text=plan_text, evidence_text=evidence_text)
        if plan_bytes is not None:
            (self.gov / "plan-tracker.md").write_bytes(plan_bytes)
        if runtime is not None:
            (self.gov / "flow-unit-runtime.json").write_text(
                json.dumps(runtime, ensure_ascii=False, indent=2),
                encoding="utf-8")
        if packets is not None:
            (self.gov / "execution-packets.json").write_text(
                json.dumps({"version": 1, "packets": packets},
                           ensure_ascii=False),
                encoding="utf-8")

    def __enter__(self):
        self._patches = [
            mock.patch.object(vw, "GOVERNANCE_DIR", self.gov),
            mock.patch.object(vw, "SAMPLE_PATH",
                              self.gov / "plan-tracker.md"),
            mock.patch.object(vw, "EXECUTION_PACKET_PATH",
                              self.gov / "execution-packets.json"),
        ]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *exc_info):
        for p in reversed(self._patches):
            p.stop()
        return False


def _fail_types(block):
    return [issue["type"] for issue in block.get("fail", [])]


def _warn_types(block):
    return [issue["type"] for issue in block.get("warn", [])]


# ═══════════════════════════════════════════════════════════════════════════
# The eight C-10 branches (R0 F-1) + renderer
# ═══════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════
# R0 F-2 — MIGRATION version-prefix boundary
# ═══════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════
# E-6 — MIGRATION_VERSION stamp compatibility surface
# ═══════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════
# ADR-RB-2 — two-face goal-layer contract gate (factory WARN form)
# ═══════════════════════════════════════════════════════════════════════════


class TestRB2ActivationPrecondition(unittest.TestCase):
    """Face ① — host-activation precondition (ADR-019 §4 RB-2 mitigation):
    at least one unit's product_success_contract is non-TO_BE_DEFINED AND
    traceable to the plan-tracker goal face. Factory form: WARN-grade."""

    def _packets(self, contract):
        return {
            _DEMO_TASK_ID: {
                "task_id": _DEMO_TASK_ID,
                "product_success_contract": contract,
            },
        }

    def test_precondition_met_on_filled_contract(self):
        # Positive sample: filled contract + goal face → precondition met,
        # zero WARN (the real repo must render exactly this shape).
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(goal_face=True),
                    packets=self._packets(VALID_CONTRACT)):
                readiness = ed.check_goal_layer_contract_readiness()
        self.assertTrue(readiness["plan_tracker_goal_face"])
        self.assertEqual(readiness["contract_ready_units"], [_DEMO_TASK_ID])
        self.assertTrue(readiness["precondition_met"])
        self.assertEqual(readiness["warn"], [])

    def test_precondition_rejects_placeholder_contract_host(self):
        # Negative sample: the REAL TO_BE_DEFINED template (via
        # build_execution_packet) must NOT satisfy the precondition.
        template = vw.build_execution_packet({
            "task_id": _DEMO_TASK_ID,
            "title": "Demo unit",
            "priority": "P1",
            "status": "📋 待启动",
        }, contracts=["product_success_contract"])["product_success_contract"]
        self.assertIn("TO_BE_DEFINED", template["user"])  # template sanity
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(goal_face=True),
                    packets=self._packets(template)):
                readiness = ed.check_goal_layer_contract_readiness()
        self.assertFalse(readiness["precondition_met"])  # the 拒绝/WARN 判据
        self.assertFalse(readiness["contract_ready_units"])
        self.assertTrue(readiness["warn"])
        self.assertTrue(any("占位" in w or "TO_BE_DEFINED" in w
                            for w in readiness["warn"]),
                        readiness["warn"])

    def test_precondition_warns_when_goal_face_missing(self):
        # Traceability half: no goal face in the plan-tracker → the contract
        # cannot be traced to plan-tracker success criteria → WARN.
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(goal_face=False),
                    packets=self._packets(VALID_CONTRACT)):
                readiness = ed.check_goal_layer_contract_readiness()
        self.assertFalse(readiness["plan_tracker_goal_face"])
        self.assertFalse(readiness["precondition_met"])
        self.assertTrue(any("成功标准" in w for w in readiness["warn"]),
                        readiness["warn"])

    def test_precondition_gap_state_judges_na_without_warn(self):
        # FIX-431 正例: 发布间隙态（无活跃 P0/P1 unit——任务表全完成）无判定
        # 对象 → face① 判 N/A，不发「无活跃 P0/P1 unit」WARN（旧实现在此发
        # WARN 且计入渲染块三条之一）。
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(with_active_task=False),
                    packets={}):
                readiness = ed.check_goal_layer_contract_readiness()
        self.assertFalse(readiness["active_units"])
        self.assertFalse(readiness["precondition_met"])
        self.assertEqual(readiness["warn"], [])  # 间隙态零 WARN

    def test_precondition_gap_state_na_even_without_goal_face(self):
        # 间隙态无判定对象优先于 goal_face 追溯检查——goal_face 缺失 WARN
        # 只在有活跃 unit 的运行期有意义（运行期形态由
        # test_precondition_warns_when_goal_face_missing 守护，零变化）。
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(
                        goal_face=False, with_active_task=False),
                    packets={}):
                readiness = ed.check_goal_layer_contract_readiness()
        self.assertFalse(readiness["active_units"])
        self.assertFalse(readiness["precondition_met"])
        self.assertEqual(readiness["warn"], [])

    def test_precondition_gap_state_still_discloses_unreadable_packets(self):
        # 间隙态改判 N/A 不吞评估完整性异常：execution packets 不可读仍 WARN
        # （fail-open 披露保持——FIX-431 只重判「无活跃 unit」的判定结论，
        # 不隐藏异常；安全语义不回退）。
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(with_active_task=False),
                    packets=None):  # 不写 packets 文件 → load_error
                readiness = ed.check_goal_layer_contract_readiness()
        self.assertFalse(readiness["active_units"])
        self.assertFalse(readiness["precondition_met"])
        self.assertTrue(any("不可读" in w for w in readiness["warn"]),
                        readiness["warn"])

    def test_precondition_active_unit_without_contract_still_warns(self):
        # FIX-431 负例: 有活跃 P0/P1 unit 但无 contract → 现行为 WARN 全保持
        # （间隙态 N/A 不得外溢到运行期判定链）。
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(goal_face=True),
                    packets={}):  # 活跃任务存在、无对应 packet
                readiness = ed.check_goal_layer_contract_readiness()
        self.assertTrue(readiness["active_units"])
        self.assertFalse(readiness["precondition_met"])
        self.assertTrue(any("穿透" in w or "TO_BE_DEFINED" in w
                            for w in readiness["warn"]),
                        readiness["warn"])


class TestRB2SensitiveActionGate(unittest.TestCase):
    """Face ② — contract-missing gate judge: missing → WARN, sensitive
    action (发布/翻转类) → BLOCK judge. Factory: BLOCK is demoted to WARN
    (enforcement off — 真阻断属授权票域, B-12/B-13 precedent)."""

    def test_judge_factory_demotes_block_to_warn_but_keeps_judge(self):
        readiness = {"precondition_met": False}
        j = ed.judge_rb2_contract_gate("release 0.90.0 (发布)", readiness)
        self.assertTrue(j["sensitive"])
        self.assertEqual(j["raw_verdict"], "BLOCK")   # 阻断判据可观测
        self.assertEqual(j["verdict"], "WARN")        # factory 不拦截
        self.assertIn("warn-only", j["enforcement"])

    def test_judge_enforced_flip_blocks_sensitive_action(self):
        readiness = {"precondition_met": False}
        with mock.patch.object(ed, "RB2_SENSITIVE_BLOCK_ENFORCED", True):
            j = ed.judge_rb2_contract_gate("授权票翻转 authorization-flip",
                                           readiness)
        self.assertEqual(j["raw_verdict"], "BLOCK")
        self.assertEqual(j["verdict"], "BLOCK")       # 授权票翻转后真阻断
        self.assertEqual(j["enforcement"], "enforced")

    def test_judge_nonsensitive_contract_missing_warns_not_blocks(self):
        readiness = {"precondition_met": False}
        j = ed.judge_rb2_contract_gate("check-governance", readiness)
        self.assertFalse(j["sensitive"])
        self.assertEqual(j["raw_verdict"], "WARN")
        self.assertEqual(j["verdict"], "WARN")        # 非敏感→WARN 不阻断

    def test_judge_ready_contract_passes_sensitive_action(self):
        readiness = {"precondition_met": True}
        j = ed.judge_rb2_contract_gate("release 0.90.0", readiness)
        self.assertTrue(j["sensitive"])
        self.assertEqual(j["verdict"], "PASS")        # 契约在→放行

    def test_judge_defaults_to_live_host_readiness(self):
        # No readiness passed → the judge consults the REAL host faces.
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(goal_face=True)):
                j = ed.judge_rb2_contract_gate("release 0.90.0")
        # No packets file → contract readiness unmet → would-block family.
        self.assertFalse(j["contract_ready"])

    def test_judge_gap_state_na_for_sensitive_and_nonsensitive(self):
        # FIX-431 正例: 间隙态（无活跃 P0/P1 unit）无判定语境——demo 契约缺
        # 失 WARN/BLOCK 只在有活跃 unit 的运行期才有意义 → sensitive 与
        # non-sensitive 都判 N/A（verdict 与 raw_verdict 同值，不发 WARN）。
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(with_active_task=False),
                    packets={}):
                readiness = ed.check_goal_layer_contract_readiness()
                j_sensitive = ed.judge_rb2_contract_gate(
                    "release 0.90.0 (发布)", readiness)
                j_plain = ed.judge_rb2_contract_gate(
                    "check-governance", readiness)
        self.assertTrue(j_sensitive["sensitive"])
        self.assertFalse(j_plain["sensitive"])
        for j in (j_sensitive, j_plain):
            self.assertEqual(j["raw_verdict"], "N/A")
            self.assertEqual(j["verdict"], "N/A")

    def test_judge_gap_state_na_survives_enforced_flip(self):
        # 边界守护: enforcement 翻转机制（B-12/B-13 授权票域）零触碰——间隙
        # 态无判定对象，翻转后 sensitive action 仍判 N/A 而非 BLOCK。
        readiness = {"precondition_met": False, "active_units": False}
        with mock.patch.object(ed, "RB2_SENSITIVE_BLOCK_ENFORCED", True):
            j = ed.judge_rb2_contract_gate("授权票翻转 authorization-flip",
                                           readiness)
        self.assertEqual(j["raw_verdict"], "N/A")
        self.assertEqual(j["verdict"], "N/A")
        self.assertEqual(j["enforcement"], "enforced")

    def test_judge_handbuilt_readiness_keeps_runtime_semantics(self):
        # 向后兼容: 直接调用方 hand-built readiness（缺 active_units 键）按
        # 运行期处理——WARN/BLOCK 判定链零变化（既有契约，FIX-431 不外溢）。
        readiness = {"precondition_met": False}
        j = ed.judge_rb2_contract_gate("release 0.90.0 (发布)", readiness)
        self.assertEqual(j["raw_verdict"], "BLOCK")
        self.assertEqual(j["verdict"], "WARN")


class TestRB2RendererBlock(unittest.TestCase):
    """The renderer wiring face — WARN-grade output, never [FAIL]."""

    def test_renderer_positive_host_shows_pass(self):
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(goal_face=True),
                    packets={_DEMO_TASK_ID: {
                        "task_id": _DEMO_TASK_ID,
                        "product_success_contract": VALID_CONTRACT,
                    }}):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    ed.render_rb2_goal_contract_block()
        out = buf.getvalue()
        self.assertIn("Activation precondition: [PASS]", out)
        self.assertIn("gate open", out)
        self.assertNotIn("[FAIL]", out)  # factory WARN-only discipline

    def test_renderer_placeholder_host_shows_warn_and_block_judge(self):
        template = vw.build_execution_packet({
            "task_id": _DEMO_TASK_ID,
            "title": "Demo unit",
            "priority": "P1",
            "status": "📋 待启动",
        }, contracts=["product_success_contract"])["product_success_contract"]
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(goal_face=True),
                    packets={_DEMO_TASK_ID: {
                        "task_id": _DEMO_TASK_ID,
                        "product_success_contract": template,
                    }}):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    ed.render_rb2_goal_contract_block()
        out = buf.getvalue()
        self.assertIn("Activation precondition: [WARN]", out)
        self.assertIn("(judge=BLOCK)", out)   # 阻断判据可观测
        self.assertIn("enforcement=warn-only", out)
        self.assertNotIn("[FAIL]", out)

    def test_renderer_gap_state_shows_na_no_warn(self):
        # FIX-431 正例: 间隙态（无活跃 P0/P1）→ face① N/A + demo faces N/A，
        # 全块零 [WARN] 行（旧实现发三条 WARN：face① 一条 + demo 两条）。
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(with_active_task=False),
                    packets={}):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    ed.render_rb2_goal_contract_block()
        out = buf.getvalue()
        self.assertIn("Activation precondition: [N/A]", out)
        self.assertEqual(out.count("[N/A]"), 3)  # face① + 两条 demo
        self.assertNotIn("[WARN]", out)
        self.assertNotIn("[FAIL]", out)

    def test_renderer_active_unit_without_contract_keeps_warn(self):
        # FIX-431 负例: 有活跃 P0/P1 但无 contract → 现行为渲染零变化
        # （face① WARN + demo judge=BLOCK/WARN 全保持）。
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(goal_face=True),
                    packets={}):  # 活跃任务存在、无对应 packet
                buf = io.StringIO()
                with redirect_stdout(buf):
                    ed.render_rb2_goal_contract_block()
        out = buf.getvalue()
        self.assertIn("Activation precondition: [WARN]", out)
        self.assertIn("(judge=BLOCK)", out)
        self.assertIn("contract missing → WARN", out)
        self.assertNotIn("[N/A]", out)


if __name__ == "__main__":  # pragma: no cover - direct-run convenience
    unittest.main()
