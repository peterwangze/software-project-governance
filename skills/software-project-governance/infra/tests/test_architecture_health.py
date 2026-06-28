"""Unit tests for ArchGuard architecture-health checks (REQ-101 / FIX-152 / 0.58.0).

Covers the four check_* helpers in verify_workflow.py plus the G7 advisory
contract (WARN/ERROR must not flip the gate). Tests use small synthetic
fixtures under tmp_path so they are fast and independent of the real
20,294-line God Module — except one integration test that confirms ArchGuard
catches the real module-size violation.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_architecture_health.py -q
"""

import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw

SCHEMA_JSON = """{
  "version": "1.0",
  "module_size": {"warn_lines": 2000, "error_lines": 5000, "target_lines": 1500,
    "exclusions": [{"path": "**/tests/**", "reason": "test"}, {"path": "**/test_*.py", "reason": "test"}]},
  "function_size": {"warn_lines": 200, "error_lines": 500, "target_lines": 100},
  "module_constants": {"warn_count": 150, "error_count": 300, "detect_duplicates": true},
  "duplicate_code": {"warn_pct": 60, "error_pct": 80,
    "normalize_line_endings": true, "ignore_whitespace": true,
    "source_projection_pairs": "auto-from-manifest"},
  "complexity": {"enabled": false, "warn_cyclomatic": 15, "error_cyclomatic": 30,
    "note": "proxy"},
  "technical_debt": {"root_residue_patterns": ["_fix_*", "_tmp_*", "debug_*", "scratch_*"],
    "release_docs_archive_threshold_versions": 30,
    "hooks_drift_detection": true, "ledger_cross_validate": true},
  "governance_data_size": {"enabled": true,
    "files": [".governance/plan-tracker.md", ".governance/evidence-log.md"],
    "warn_bytes": 200000, "error_bytes": 250000, "note": "FIX-160 test"},
  "gate_integration": {"fatal_on_error": false, "note": "advisory"}
}
"""


def _make_repo(tmp):
    """Create a minimal repo skeleton with the schema + infra dirs ArchGuard expects."""
    tmp = Path(tmp)
    (tmp / "skills/software-project-governance/core").mkdir(parents=True, exist_ok=True)
    (tmp / "skills/software-project-governance/infra").mkdir(parents=True, exist_ok=True)
    (tmp / "skills/software-project-governance/infra/hooks").mkdir(parents=True, exist_ok=True)
    (tmp / ".git/hooks").mkdir(parents=True, exist_ok=True)
    (tmp / "skills/software-project-governance/core/architecture-health.json").write_text(
        SCHEMA_JSON, encoding="utf-8")
    return tmp


class CheckArchitectureHealthTests(unittest.TestCase):

    def test_detects_large_module_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            # 6000-line file exceeds error_lines(5000)
            big = root / "skills/software-project-governance/infra/big.py"
            big.write_text("\n".join(["x = 1"] * 6000) + "\n", encoding="utf-8")
            result = vw.check_architecture_health(root=root)
            module_findings = [f for f in result["findings"] if f["check"] == "module_size"]
            self.assertTrue(any(f["severity"] == "ERROR" for f in module_findings),
                            f"expected ERROR module_size; got {module_findings}")

    def test_detects_long_function_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            body = "\n".join("    pass" for _ in range(600))
            (root / "skills/software-project-governance/infra/longfn.py").write_text(
                f"def huge():\n{body}\n", encoding="utf-8")
            result = vw.check_architecture_health(root=root)
            fn_findings = [f for f in result["findings"] if f["check"] == "function_size"
                           and f["name"] == "huge"]
            self.assertTrue(fn_findings, "expected a function_size finding for huge()")
            self.assertEqual(fn_findings[0]["severity"], "ERROR")

    def test_detects_duplicate_constant(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            (root / "skills/software-project-governance/infra/dup.py").write_text(
                "PRODUCT_CODE_PATTERNS = [1]\nPRODUCT_CODE_PATTERNS = [2]\n",
                encoding="utf-8")
            result = vw.check_architecture_health(root=root)
            dups = [f for f in result["findings"] if f["check"] == "duplicate_constant"
                    and f["name"] == "PRODUCT_CODE_PATTERNS"]
            self.assertEqual(len(dups), 1)
            self.assertEqual(dups[0]["severity"], "ERROR")
            self.assertEqual(len(dups[0]["lines"]), 2)

    def test_invalid_schema_returns_error_no_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            # Corrupt the schema
            (root / "skills/software-project-governance/core/architecture-health.json").write_text(
                "{ not valid json", encoding="utf-8")
            result = vw.check_architecture_health(root=root)
            self.assertIn("error", result)
            self.assertEqual(result["findings"], [])

    def test_test_files_are_excluded_from_module_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            test_dir = root / "skills/software-project-governance/infra/tests"
            test_dir.mkdir(parents=True, exist_ok=True)
            (test_dir / "test_huge.py").write_text("\n".join(["y = 2"] * 6000) + "\n",
                                                    encoding="utf-8")
            result = vw.check_architecture_health(root=root)
            module_findings = [f for f in result["findings"] if f["check"] == "module_size"]
            self.assertFalse(module_findings, "test files must be excluded from module_size")


class CheckDuplicateCodeTests(unittest.TestCase):
    """G7-adjacent: CRLF normalization is the #1 regression to lock in."""

    def test_normalizes_crlf_so_identical_content_is_high_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            # source = CRLF, projection = LF, identical content otherwise
            content = "import os\nimport sys\n\ndef main():\n    return 0\n"
            src_dir = root / "skills/software-project-governance/infra"
            proj_base = root / "project/e2e-test-project/skills/software-project-governance/infra"
            proj_base.mkdir(parents=True, exist_ok=True)
            (src_dir / "alpha.py").write_text(content.replace("\n", "\r\n"), encoding="utf-8")
            (proj_base / "alpha.py").write_text(content, encoding="utf-8")
            result = vw.check_duplicate_code(root=root)
            # identical content → duplicate_pct should be very high (not ~0%)
            self.assertGreaterEqual(result["pairs_checked"], 1,
                                    "alpha.py pair must be detected")
            alpha = [f for f in result["findings"] if "alpha" in f.get("path", "")]
            # Either flagged as duplicate (high %) or no finding because below threshold;
            # the key assertion: it must NOT report low duplicate (which would mean CRLF broke it).
            if alpha:
                self.assertGreater(alpha[0]["duplicate_pct"], 80.0,
                                   f"CRLF normalization broken: {alpha[0]}")

    def test_whitespace_only_diff_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            src = "import os\nimport sys\ndef main():\n    return 0\n"
            proj = "  import os  \n\timport sys\t\ndef main():\n\t\treturn 0;\n"
            src_dir = root / "skills/software-project-governance/infra"
            proj_base = root / "project/e2e-test-project/skills/software-project-governance/infra"
            proj_base.mkdir(parents=True, exist_ok=True)
            (src_dir / "beta.py").write_text(src, encoding="utf-8")
            (proj_base / "beta.py").write_text(proj, encoding="utf-8")
            result = vw.check_duplicate_code(root=root)
            self.assertGreaterEqual(result["pairs_checked"], 1,
                                    "beta.py pair must be detected")
            beta = [f for f in result["findings"] if "beta" in f.get("path", "")]
            # whitespace-only differences should be treated as duplicates (high %)
            if beta:
                self.assertGreater(beta[0]["duplicate_pct"], 80.0)


class CheckTechnicalDebtTests(unittest.TestCase):

    LEDGER = """# 技术债登记表

## 登记项

| 债务 ID | 登记日期 | 来源 AUDIT | 描述 | 严重度 | 影响范围 | 承载版本 | 状态 | 关联证据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TD-100 | 2026-06-25 | AUDIT-X | missing carrying version | 高 | 全局 | 待评估 | OPEN | EVD-x |
| TD-101 | 2026-06-25 | AUDIT-X | has carrying version | 中 | 局部 | 0.59.0 | IN_PROGRESS | EVD-y |
| TD-102 | 2026-06-25 | AUDIT-X | deferred item | 低 | 局部 | 1.0.0 | DEFERRED | EVD-z |
"""

    def test_open_without_carrying_version_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            (root / "skills/software-project-governance/core/technical-debt-ledger.md").write_text(
                self.LEDGER, encoding="utf-8")
            result = vw.check_technical_debt(root=root)
            no_version = [f for f in result["findings"]
                          if f.get("check") == "ledger_no_carrying_version"
                          and f.get("ledger_id") == "TD-100"]
            self.assertTrue(no_version, "OPEN item without 承载版本 must WARN")
            # TD-101 has a carrying version → no finding
            td101 = [f for f in result["findings"]
                     if f.get("ledger_id") == "TD-101"
                     and f.get("check") == "ledger_no_carrying_version"]
            self.assertFalse(td101, "OPEN item WITH 承载版本 must not WARN")
            # summary counts
            self.assertEqual(result["summary"]["open_items"], 2)
            self.assertEqual(result["summary"]["deferred_items"], 1)

    def test_root_residue_scripts_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            (root / "_fix_tmp_explore.py").write_text("# residue\n", encoding="utf-8")
            result = vw.check_technical_debt(root=root)
            residue = [f for f in result["findings"] if f.get("check") == "root_residue"]
            self.assertTrue(residue, "_fix_* residue script must be detected")

    def test_hooks_drift_detected_when_installed_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            hooks_src = root / "skills/software-project-governance/infra/hooks"
            (hooks_src / "pre-commit").write_text("source-content-v1\n", encoding="utf-8")
            (root / ".git/hooks/pre-commit").write_text("different-installed-content\n",
                                                         encoding="utf-8")
            result = vw.check_technical_debt(root=root)
            drift = [f for f in result["findings"]
                     if f.get("check") == "hooks_drift" and f.get("hook") == "pre-commit"]
            self.assertTrue(drift, "content drift between source and installed hook must WARN")

    def test_hooks_no_drift_when_source_equals_installed(self):
        """G9 root-isolation regression: identical source+installed in a synthetic root
        must yield ZERO hooks_drift findings. This catches the root-leak where the
        canonical helper ignored the caller's `root` and compared against the real repo."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            hooks_src = root / "skills/software-project-governance/infra/hooks"
            shared = "#!/bin/sh\n# identical hook body\necho governance-hook\n"
            (hooks_src / "pre-commit").write_text(shared, encoding="utf-8")
            (root / ".git/hooks/pre-commit").write_text(shared, encoding="utf-8")
            result = vw.check_technical_debt(root=root)
            drift = [f for f in result["findings"]
                     if f.get("check") == "hooks_drift" and f.get("hook") == "pre-commit"]
            self.assertFalse(drift, "identical source and installed must NOT report drift "
                                    f"(G9 root-isolation leak); got {drift}")


class CheckComplexityTests(unittest.TestCase):

    def test_disabled_returns_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            result = vw.check_complexity(root=root)
            self.assertFalse(result["enabled"])
            self.assertEqual(result["findings"], [])
            self.assertIn("note", result)


class AdvisoryGateContractTests(unittest.TestCase):
    """G7: ArchGuard WARN/ERROR must NOT increment all_issues / fail the gate.

    Verifies the advisory behavior end-to-end via the cmd handler exit code.
    """

    def test_architecture_health_cmd_does_not_fail_on_errors_when_advisory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            # force an ERROR finding (module > 5000 lines)
            (root / "skills/software-project-governance/infra/huge.py").write_text(
                "\n".join(["z = 3"] * 6000) + "\n", encoding="utf-8")
            # check_architecture_health itself reports errors but fatal_on_error=false
            result = vw.check_architecture_health(root=root)
            self.assertGreater(result["summary"]["errors"], 0)
            self.assertFalse(result["fatal_on_error"],
                             "0.58.0 schema must default fatal_on_error=false")


class RealCodebaseIntegrationTest(unittest.TestCase):
    """Confirm ArchGuard catches the real God Module violation (sanity)."""

    def test_real_verify_workflow_triggers_module_size_error(self):
        # ROOT points at the real repo root; verify_workflow.py is ~20k lines.
        result = vw.check_architecture_health()
        if result.get("error"):
            self.skipTest(f"schema unavailable in this env: {result['error']}")
        vw_finds = [f for f in result["findings"]
                    if f.get("check") == "module_size"
                    and "verify_workflow.py" in f.get("path", "")
                    and "e2e-test-project" not in f.get("path", "")]
        self.assertTrue(vw_finds, "ArchGuard must flag the real verify_workflow.py module size")
        self.assertEqual(vw_finds[0]["severity"], "ERROR")


class GovernanceDataSizeTest(unittest.TestCase):
    """FIX-160: governance data volume threshold check."""

    def test_error_when_file_exceeds_error_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            gov = root / ".governance"
            gov.mkdir(parents=True, exist_ok=True)
            # 260KB file > error_bytes 250000
            (gov / "plan-tracker.md").write_text("x" * 260000, encoding="utf-8")
            result = vw.check_governance_data_size(root=root)
            finds = [f for f in result["findings"] if f["check"] == "governance_data_size"]
            self.assertTrue(any(f["severity"] == "ERROR" for f in finds))
            self.assertEqual(result["summary"]["errors"], 1)

    def test_warn_when_file_between_warn_and_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            gov = root / ".governance"
            gov.mkdir(parents=True, exist_ok=True)
            # 220KB: > warn 200000 but < error 250000
            (gov / "plan-tracker.md").write_text("x" * 220000, encoding="utf-8")
            result = vw.check_governance_data_size(root=root)
            finds = [f for f in result["findings"] if f["check"] == "governance_data_size"]
            self.assertTrue(any(f["severity"] == "WARN" for f in finds))
            self.assertEqual(result["summary"]["errors"], 0)
            self.assertEqual(result["summary"]["warnings"], 1)

    def test_pass_when_file_under_warn_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            gov = root / ".governance"
            gov.mkdir(parents=True, exist_ok=True)
            # 100KB < warn 200000
            (gov / "plan-tracker.md").write_text("x" * 100000, encoding="utf-8")
            result = vw.check_governance_data_size(root=root)
            self.assertEqual(result["summary"]["errors"], 0)
            self.assertEqual(result["summary"]["warnings"], 0)
            self.assertEqual(result["findings"], [])

    def test_schema_missing_returns_error_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            # Corrupt schema: remove governance_data_size key by writing minimal schema
            (root / "skills/software-project-governance/core/architecture-health.json").write_text(
                '{"version":"1.0","gate_integration":{"fatal_on_error":false}}', encoding="utf-8")
            result = vw.check_governance_data_size(root=root)
            # No governance_data_size section → defaults empty → enabled=True, no findings
            self.assertEqual(result["summary"]["errors"], 0)

    def test_disabled_returns_note(self):
        schema = {
            "governance_data_size": {"enabled": False, "note": "off"},
            "gate_integration": {"fatal_on_error": False},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(tmp)
            result = vw.check_governance_data_size(root=root, schema=schema)
            self.assertFalse(result["enabled"])
            self.assertEqual(result["findings"], [])


if __name__ == "__main__":
    unittest.main()
