"""FEAT-014 / FIX-270 — Check 28t product-gate attribution tests (red→green).

Code Review R0 finding F-2 (docs/reviews/review-FEAT-014-CODE-R0.md L42):
Check 28t's fact source is the *plugin package's own* README (verify_workflow
L19169 ``ROOT / "README.md"``), so by the FIX-270 rule ("每个检查的事实源根
必须等于被治理对象") it is a PLUGIN_PRODUCT check. In host mode
(HOST_PROJECT_ROOT != PLUGIN_ROOT) it must therefore be skipped by default and
re-enabled only by ``--product-gates`` — exactly like the neighbouring
28o/28p/28q/28r blocks (``if _product_gate_active(args):`` + else
``_print_product_gate_skipped(...)``).

Observed before the fix: 28p printed ``[SKIP] product self-check …roots
diverge`` while 28t ran in full (claims checked / Verdict: PASS).

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_feat014_check28t_product_gate.py -v
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


def _run_engine_host_mode(product_gates=False):
    """Run the full engine with divergent roots (host mode); return stdout.

    ``check_readme_claim_evidence_levels`` is stubbed with a raiser so that a
    leaked 28t run is unambiguous (and the test stays independent of the
    README content itself).
    """
    with tempfile.TemporaryDirectory() as td:
        p1 = mock.patch.object(vw, "PLUGIN_ROOT", Path(vw.ROOT))
        p2 = mock.patch.object(vw, "HOST_PROJECT_ROOT", Path(td))
        with p1, p2:
            with mock.patch.object(
                    vw, "check_readme_claim_evidence_levels",
                    side_effect=AssertionError(
                        "product check ran: Check 28t")):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    vw._run_full_engine_checks(_args(product_gates=product_gates))
    return buf.getvalue()


class Check28tProductGateTests(unittest.TestCase):
    """F-2: 28t is a plugin-product check → registered + gated like 28p/28q/28r."""

    def test_check28t_registered_in_product_gate_tables(self):
        """28t MUST be declared in both FIX-270 registry tables."""
        self.assertIn("Check 28t", vw._PLUGIN_PRODUCT_CHECK_IDS)
        self.assertIn("Check 28t", vw._PRODUCT_GATE_LABELS)

    def test_host_mode_skips_check28t_by_default(self):
        """宿主模式（product_gates=False）→ 28t 输出 [SKIP]，不运行检查。"""
        output = _run_engine_host_mode(product_gates=False)
        self.assertIn("Check 28t", output)
        self.assertIn("[SKIP] product self-check", output)
        # 28t 的完整运行标记不得出现
        self.assertNotIn("claims checked:", output)

    def test_host_mode_product_gates_flag_runs_check28t(self):
        """--product-gates 显式开启 → 28t 恢复运行（stub raiser 被触发）。"""
        with self.assertRaises(AssertionError) as ctx:
            _run_engine_host_mode(product_gates=True)
        self.assertIn("Check 28t", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
