"""FEAT-014 / RISK-049 ① — README adapter claim→evidence level mapping tests.

RISK-049 closure standard (1) (risk-log L49): adapter-面 user-facing claims
must carry a machine-checkable claim→evidence level mapping —
live-session / isolation / static three levels + a README check extension.
The defect class (RISK-049 ②): README claims ("安装后 /governance 可用")
exceeded the actually-verified range with no machine constraint.

Marker contract: 〔<level>: <detail>〕 — live-session/isolation details MUST
carry an ISO verification date; static is the explicit no-execution-evidence
label (date optional). Registry claims (the dsh user-availability surface)
MUST carry ≥1 marker on the claim line.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_readme_evidence_levels.py -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw  # noqa: E402


def _write_readme(text):
    td = tempfile.mkdtemp(prefix="feat014_")
    path = Path(td) / "README.md"
    path.write_text(text, encoding="utf-8")
    return path


class ClaimEvidenceLevelCheckTests(unittest.TestCase):
    """FEAT-014: unannotated claims detected / valid annotations pass /
    marker integrity (live-session & isolation require ISO dates)."""

    def test_unannotated_claim_detected_warn(self):
        """红→绿核心：注册 claim 行无等级标注 → WARN（claim_id 定位）。"""
        path = _write_readme(
            "# README\n\n"
            "1. 治理 skills 与 `/governance` 命令投影在该 profile 的"
            "**每个会话**中可用；\n"
        )
        r = vw.check_readme_claim_evidence_levels(readme_path=path)
        self.assertEqual(r["verdict"], "WARN")
        unannotated = [w for w in r["warnings"] if w["rule"] == "UNANNOTATED"]
        self.assertTrue(unannotated, r["warnings"])
        self.assertEqual(unannotated[0]["claim_id"], "dsh-session-projection")
        self.assertEqual(r["stats"]["claims_checked"], 1)
        self.assertEqual(r["stats"]["claims_annotated"], 0)

    def test_annotated_claims_pass(self):
        """合法三级标注全过：四注册 claim 各带有效 marker → PASS。"""
        path = _write_readme(
            "# README\n"
            "load in every session of that profile "
            "〔isolation: 2026-09-05 dsh 0.1.2-rc.1 isolated DSH_HOME〕\n"
            "appears in the preset roster "
            "〔isolation: 2026-09-05 discoverPresets healthy〕\n"
            "用户输入 `/governance` 即加载统一治理入口 "
            "〔live-session: 2026-07-08 real dsh session 0.1.0-rc.6〕\n"
            "Both forms were re-verified this way "
            "〔isolation: 2026-09-05 Windows-only〕〔static: github: form "
            "not executed — packaging semantics by reasoning, RISK-049〕\n"
        )
        r = vw.check_readme_claim_evidence_levels(readme_path=path)
        self.assertEqual(r["warnings"], [], r["warnings"])
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["stats"]["claims_checked"], 4)
        self.assertEqual(r["stats"]["claims_annotated"], 4)
        self.assertEqual(r["stats"]["levels"]["static"], 1)

    def test_live_session_marker_requires_date(self):
        """完整性：live-session marker 无 ISO 日期 → INTEGRITY WARN。"""
        path = _write_readme(
            "用户输入 `/governance` 即加载统一治理入口"
            "〔live-session: 用户活体会话——未记日期〕\n"
        )
        r = vw.check_readme_claim_evidence_levels(readme_path=path)
        integrity = [w for w in r["warnings"] if w["rule"] == "INTEGRITY"]
        self.assertTrue(integrity, r["warnings"])
        self.assertIn("live-session", integrity[0]["reason"])
        # claim 行本身有 marker → 不出 UNANNOTATED。
        self.assertFalse(
            [w for w in r["warnings"] if w["rule"] == "UNANNOTATED"])

    def test_isolation_marker_requires_date(self):
        """完整性：isolation marker 无日期 → INTEGRITY WARN（static 豁免）。"""
        path = _write_readme(
            "load in every session of that profile 〔isolation: 隔离复验〕\n")
        r = vw.check_readme_claim_evidence_levels(readme_path=path)
        integrity = [w for w in r["warnings"] if w["rule"] == "INTEGRITY"]
        self.assertTrue(integrity, r["warnings"])

    def test_static_marker_without_date_is_allowed(self):
        """static = 显式无执行证据标注——日期非必需（RISK-049：允许无执行
        证据但 MUST 显式标注）。"""
        path = _write_readme(
            "Both forms were re-verified this way "
            "〔isolation: 2026-09-05〕〔static: github: 未执行安装验证〕\n")
        r = vw.check_readme_claim_evidence_levels(readme_path=path)
        self.assertEqual(r["warnings"], [], r["warnings"])
        self.assertEqual(r["verdict"], "PASS")

    def test_bogus_level_marker_does_not_satisfy_claim(self):
        """未知等级词不构成合法 marker → claim 仍判 UNANNOTATED。"""
        path = _write_readme(
            "直接出现在预设选择器中〔probably: 也许验证过〕\n")
        r = vw.check_readme_claim_evidence_levels(readme_path=path)
        unannotated = [w for w in r["warnings"] if w["rule"] == "UNANNOTATED"]
        self.assertTrue(unannotated, r["warnings"])
        self.assertEqual(unannotated[0]["claim_id"], "dsh-preset-roster")

    def test_missing_readme_is_no_verdict(self):
        result_dir = Path(tempfile.mkdtemp(prefix="feat014_none_"))
        r = vw.check_readme_claim_evidence_levels(
            readme_path=result_dir / "README.md")
        self.assertEqual(r["verdict"], "no-verdict")
        self.assertEqual(r["warnings"], [])


class RealReadmeBaselineTests(unittest.TestCase):
    """对当前仓库 README 实测（FEAT-014 交付后 = 全标注 → PASS）。

    本测试在 README 标注落地前为红（未标注 claim 检出）——即 RISK-049
    关闭标准的基线输入；标注落地后锁定 PASS（后续新增 dsh claim 未标注
    即回归红）。
    """

    def test_real_repo_readme_claims_all_annotated(self):
        r = vw.check_readme_claim_evidence_levels()
        self.assertEqual(
            r["warnings"], [],
            "unannotated/invalid claims: {0}".format(r["warnings"]))
        self.assertGreaterEqual(r["stats"]["claims_checked"], 4)
        self.assertEqual(r["verdict"], "PASS")


if __name__ == "__main__":
    unittest.main()
