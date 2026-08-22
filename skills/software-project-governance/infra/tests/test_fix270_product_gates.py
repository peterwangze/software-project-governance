"""FIX-270 / 交付 B+C — check-governance 宿主提速（product-gates）+ mixed-root 修复测试（red→green）。

Deliverable under test:

B. 宿主场景（HOST_PROJECT_ROOT != PLUGIN_ROOT）默认跳过插件产品自检
   （Check 31 loop-runtime-claims + identity attestation、Check 28o/28p/28q
   ArchGuard、Check 11/12/28b 等以 PLUGIN_ROOT 为事实源的检查），新增
   ``--product-gates`` 显式开启；dogfood 场景（host==plugin）默认保留全部。
   判定标准：以「检查事实源根」切分（``_PLUGIN_PRODUCT_CHECK_IDS`` 声明表）。

C. mixed-root 修复：
   - Check 28s governance-data-size：事实源 = 宿主 .governance（schema 仍为插件资产）；
   - Check 25 untracked：git 事实源 = 宿主仓库（HOST_PROJECT_ROOT）；
   - Check 28c hot fact-source：插件项目期望断言（0.38.0 roadmap/REQ/RISK-033、
     1.0.0 依赖链）仅对「被治理对象=插件项目」成立；宿主场景降级/豁免。

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_fix270_product_gates.py -v
"""

import io
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw  # noqa: E402


def _args(**overrides):
    base = dict(
        fail_on_issues=False,
        summary_only=False,
        summary_level="standard",
        product_gates=False,
    )
    base.update(overrides)
    return types.SimpleNamespace(**base)


def _patch_roots(divergent=True, plugin_root=None, host_root=None):
    """Patch PLUGIN_ROOT / HOST_PROJECT_ROOT so product-gate divergence is testable."""
    plugin_root = Path(plugin_root) if plugin_root else Path(vw.ROOT)
    host_root = Path(host_root) if host_root else (
        Path(vw.ROOT) / ".fixture-divergent-host"
    )
    if not divergent:
        host_root = plugin_root
    return (
        mock.patch.object(vw, "PLUGIN_ROOT", plugin_root),
        mock.patch.object(vw, "HOST_PROJECT_ROOT", host_root),
    )


class ProductGateSemanticsTests(unittest.TestCase):
    """`--product-gates` 语义：dogfood 默认开；宿主默认关、flag 显式开。"""

    def test_dogfood_keeps_product_gates_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p1, p2 = _patch_roots(divergent=False, plugin_root=root, host_root=root)
            with p1, p2:
                self.assertFalse(vw._host_plugin_roots_divergent())
                self.assertTrue(vw._product_gate_active(_args()))

    def test_host_skips_product_gates_by_default_and_flag_enables(self):
        with tempfile.TemporaryDirectory() as td:
            plugin = Path(vw.ROOT)
            host = Path(td)
            p1, p2 = _patch_roots(divergent=True, plugin_root=plugin, host_root=host)
            with p1, p2:
                self.assertTrue(vw._host_plugin_roots_divergent())
                self.assertFalse(vw._product_gate_active(_args()))
                self.assertTrue(vw._product_gate_active(_args(product_gates=True)))


class GovernanceDataSizeHostRootTests(unittest.TestCase):
    """Check 28s mixed-root 修复：facts = 宿主 .governance（schema 仍为插件资产）。"""

    def test_size_reported_from_host_root_when_root_not_explicit(self):
        big = 300_000  # > 250KB error_bytes
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            gov.mkdir()
            (gov / "plan-tracker.md").write_bytes(b"x" * big)
            p = mock.patch.object(vw, "HOST_PROJECT_ROOT", Path(td))
            with p:
                result = vw.check_governance_data_size()
                self.assertFalse(result.get("error"))
                self.assertTrue(result.get("enabled"))
                target = [f for f in result["findings"]
                          if f["path"] == ".governance/plan-tracker.md"]
                self.assertTrue(target)
                # 关键断言：报出的字节数是宿主文件的真实尺寸（不是插件仓库的）
                self.assertEqual(target[0]["bytes"], big)
                self.assertEqual(target[0]["severity"], "ERROR")


class UntrackedFilesHostRootTests(unittest.TestCase):
    """Check 25 mixed-root 修复：git 事实源 = 宿主仓库。"""

    def test_untracked_git_runs_in_host_project_root(self):
        with tempfile.TemporaryDirectory() as td:
            host = Path(td)
            p1, p2 = _patch_roots(divergent=True, host_root=host)
            with p1, p2:
                captured = {}

                def fake_run(cmd, **kwargs):
                    captured.update(kwargs)
                    return types.SimpleNamespace(returncode=0, stdout="", stderr="")

                with mock.patch("subprocess.run", side_effect=fake_run):
                    vw.check_untracked_files()
                self.assertEqual(captured.get("cwd"), str(host))


class HotFactSourceHostScopeTests(unittest.TestCase):
    """Check 28c 宿主场景降级/豁免：插件项目专属期望不再 FAIL 宿主数据。"""

    def _host_style_plan(self):
        # 宿主风格：无 0.38.0 roadmap、无 FIX-082~087、无 ### 1.0.0 依赖链
        return (
            "# 宿主计划\n\n"
            "## 项目配置\n\n"
            "- **项目名称**: 云视TV\n"
            "- **工作流版本**: 0.75.0\n\n"
            "## 项目总览\n\n"
            "| 项目 | 当前阶段 | 总任务数 | 已完成 | 阻塞中 | 关键风险数 | 最近 Gate 结论 | 最近复盘日期 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| 云视TV | 开发 (6/11) | 3 | 2 | 0 | 1 | G5 通过（接入） | — |\n\n"
            "## 当前活跃事项\n\n"
            "| 优先级 | ID | 任务项 | 依赖 | 目标版本 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| P1 | TASK-001 | 任务 | — | 1.6.0 | 已完成 |\n\n"
            "## 版本规划\n\n"
            "| 版本 | 状态 | 预计日期 | 核心范围 | 包含任务 | 关键交付物 |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| 1.6.0 | 规划 | 2026-09 | 优化 | TASK-001 | — |\n\n"
            "## 需求跟踪矩阵\n\n"
            "| 需求 | 任务 | 状态 |\n"
            "| --- | --- | --- |\n"
            "| REQ-001 | TASK-001 | 已交付 |\n\n"
            "## 变更控制\n\n"
            "快速通道：仅 .governance/ 治理记录修改可快速处理，不强制入账。\n"
        )

    def test_host_scope_skips_plugin_project_expectations(self):
        with tempfile.TemporaryDirectory() as td:
            plan = Path(td) / "plan-tracker.md"
            plan.write_text(self._host_style_plan(), encoding="utf-8")
            host = Path(td)
            p1, p2 = _patch_roots(divergent=True, host_root=host)
            with p1, p2:
                issues = vw.check_hot_fact_source_consistency(plan)
                # 插件项目专属期望（0.38.0 roadmap / FIX-082~087 / REQ-070~074 /
                # RISK-033 / REL-013 / ### 1.0.0 依赖链）不得再 FAIL 宿主数据
                plugin_scope_tokens = (
                    "0.38.0", "FIX-082", "REQ-070", "RISK-033", "REL-013",
                    "1.0.0 依赖链", "dependency chain",
                )
                for issue in issues:
                    for token in plugin_scope_tokens:
                        self.assertNotIn(token, issue)


class EngineProductGateTests(unittest.TestCase):
    """引擎级：宿主模式下产品自检默认跳过；--product-gates 显式开启。"""

    def _run_engine(self, divergent=True, product_gates=False):
        """在宿主模式（divergent）下运行引擎；product 检查函数被打桩为 raiser。"""
        stub = types.SimpleNamespace(
            verdict="PASS", issues=[], phase="staged_index",
            findings=[], inventory=types.SimpleNamespace(
                candidate_count=0, inventory_sha256="x"),
            parsed_candidates=0,
        )
        with tempfile.TemporaryDirectory() as td:
            host = Path(td)
            with mock.patch.object(vw, "scan_loop_runtime_claims",
                                   side_effect=AssertionError("product check ran: Check 31 claims")):
                with mock.patch.object(vw, "_run_identity_attestation_fixture_only",
                                       side_effect=AssertionError("product check ran: attestation")):
                    with mock.patch.object(vw, "check_architecture_health",
                                           side_effect=AssertionError("product check ran: Check 28o")):
                        with mock.patch.object(vw, "check_manifest_consistency",
                                               side_effect=AssertionError("product check ran: Check 11")):
                            with mock.patch.object(vw, "check_cross_references",
                                                   side_effect=AssertionError("product check ran: Check 12")):
                                with mock.patch.object(vw, "check_projection_sync",
                                                       side_effect=AssertionError("product check ran: Check 28b")):
                                    p1, p2 = _patch_roots(
                                        divergent=divergent,
                                        plugin_root=Path(vw.ROOT),
                                        host_root=host,
                                    )
                                    with p1, p2:
                                        buf = io.StringIO()
                                        with redirect_stdout(buf):
                                            vw._run_full_engine_checks(
                                                _args(product_gates=product_gates)
                                            )
                                    return buf.getvalue()

    def test_host_mode_skips_product_checks_by_default(self):
        output = self._run_engine(divergent=True, product_gates=False)
        self.assertIn("[SKIP] product self-check", output)

    def test_host_mode_product_gates_flag_enables_product_checks(self):
        with self.assertRaises(AssertionError):
            self._run_engine(divergent=True, product_gates=True)


if __name__ == "__main__":
    unittest.main()
