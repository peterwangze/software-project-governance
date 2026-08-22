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

    def test_a_handwritten_row_warns_v7(self):
        """Fixture (a): handwritten REVIEW row (dated, no CLI marker) → WARN/V7."""
        r = vw.check_review_machine_provenance(review_rows=[HANDWRITTEN_ROW])
        self.assertEqual(r["verdict"], "WARN")
        rules = {w["rule"] for w in r["warnings"]}
        self.assertIn("V7", rules)
        v7 = [w for w in r["warnings"] if w["rule"] == "V7"]
        self.assertEqual(v7[0]["task_id"], "FIX-300")

    def test_b_machine_records_pass(self):
        """Fixture (b): CLI-marker row + machine-written file → PASS, no WARN."""
        r = vw.check_review_machine_provenance(
            review_rows=[self._machine_row()],
            review_files={"review-FIX-301-R0.md": self._machine_file()},
        )
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["verdict"], "PASS")

    def test_c1_needs_change_row_without_file_warns_v8(self):
        """Fixture (c) form 1: NEEDS_CHANGE row, no machine file → WARN/V8."""
        r = vw.check_review_machine_provenance(
            review_rows=[self._machine_row(result="NEEDS_CHANGE")],
            review_files={},
        )
        rules = {w["rule"] for w in r["warnings"]}
        self.assertIn("V8", rules)

    def test_c2_needs_change_file_without_next_round_warns_v8(self):
        """Fixture (c) form 2: NEEDS_CHANGE file lacking next_round → WARN/V8."""
        body = self._machine_file(result="NEEDS_CHANGE").replace(
            "- next_round: REVIEW-FIX-301-R1\n", "")
        r = vw.check_review_machine_provenance(
            review_rows=[],
            review_files={"review-FIX-301-R0.md": body},
        )
        rules = {w["rule"] for w in r["warnings"]}
        self.assertIn("V8", rules)
        v8 = [w for w in r["warnings"] if w["rule"] == "V8"]
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

    def test_undated_records_are_not_judged(self):
        """V6d-style: records without a parseable date are not judged."""
        undated_row = HANDWRITTEN_ROW.replace("2026-09-01", "")
        undated_file = self._machine_file().replace("- date: 2026-09-01", "- date: ?")
        r = vw.check_review_machine_provenance(
            review_rows=[undated_row],
            review_files={"review-FIX-301-R0.md": undated_file},
        )
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["stats"]["rows_undated"], 1)
        self.assertEqual(r["stats"]["files_undated"], 1)

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
            vw.ROOT / "adapters/dsh/agent.cordis.yml.template"
        ).read_text(encoding="utf-8")
        self.assertIn("审查结论必机录", text)
        self.assertIn("review-record", text)

    def test_injection_contract_anchors_include_review_record(self):
        self.assertIn(
            "review-record",
            vw.INJECTION_CONTRACT_ANCHORS["adapters/dsh/agent.cordis.yml.template"],
        )
        # Real repo must satisfy the extended anchor set (Check 33 stays green).
        result = vw.check_injection_contract()
        self.assertEqual(result["issues"], [])

    def test_persona_contract_block_stays_within_budget(self):
        """FIX-253 budget: persona contract block ≤ 1.5KB (release-checklist-0.75.0)."""
        text = (
            vw.ROOT / "adapters/dsh/agent.cordis.yml.template"
        ).read_text(encoding="utf-8")
        start = text.index("关键行为契约")
        end = text.index("Git hooks", start)
        block = text[start:end]
        self.assertLessEqual(len(block.encode("utf-8")), 1536,
                             "persona contract block exceeds the 1.5KB budget")


if __name__ == "__main__":
    unittest.main()
