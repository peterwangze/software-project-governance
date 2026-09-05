"""Tests for infra/review_record.py — Wiring A thin CLI (FIX-236.1, ADR-017 §3).

Covers: machine review-record persistence (review-{id}-R{n}.md + evidence-log
row), Check 30 parseability of machine-written rows, the review→unit/gate
registry mapping (missing → WARN skip, explicit → wired), best-effort
degradation when process_gate_result fails, and the NEEDS_CHANGE "复审必达"
structured fields (next_round=R{n+1}).

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_review_record.py -v
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import loop_paro_engine as paro  # noqa: E402
import review_record  # noqa: E402
import verify_workflow as vw  # noqa: E402
from tests.test_loop_paro_engine import _activated_payload, _write_payload  # noqa: E402


def _new_reflect_unit(tmpdir, unit_id="shitu.story.Skeleton"):
    """Activated unit driven to the reflect node (same shape as gp tests)."""
    payload = _activated_payload(unit_id=unit_id, tier="inner", max_rounds=5)
    runtime_path = _write_payload(tmpdir, payload)
    for to_phase, event in [
        ("act", {"reason": "plan accepted"}),
        ("observe", {"reason": "action complete"}),
        ("reflect", {"gate_result": "NEEDS_CHANGE", "reason": "review recorded"}),
    ]:
        r = paro.apply_transition(unit_id, to_phase, event, runtime_file=runtime_path)
        assert r.success, "forward {0} failed: {1}".format(to_phase, r.reason)
    return runtime_path


class ReviewRecordPersistenceTests(unittest.TestCase):
    """Machine-written review records: file + evidence row + Check 30 parseability."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="rr_")
        self.root = Path(self.tmpdir)
        (self.root / ".governance").mkdir()

    def _write(self, **overrides):
        kwargs = {
            "task_id": "FIX-236",
            "round_n": 0,
            "result": "APPROVED",
            "report_path": str(self.root / "report.md"),
            "reviewer": "Code Reviewer Noether",
            "root": self.root,
        }
        kwargs.update(overrides)
        return review_record.write_review_record(**kwargs)

    def test_approved_writes_file_and_evidence_row(self):
        summary = self._write()
        self.assertFalse(summary.get("error"))
        review_file = self.root / ".governance" / "review-FIX-236-R0.md"
        self.assertTrue(review_file.is_file())
        content = review_file.read_text(encoding="utf-8")
        self.assertIn("**审查结论**: **APPROVED**", content)
        ev = (self.root / ".governance" / "evidence-log.md").read_text(encoding="utf-8")
        self.assertIn("REVIEW-FIX-236-R0", ev)
        self.assertIn("| FIX-236 |", ev)
        self.assertIn("APPROVED", ev)

    def test_approved_with_notes_writes_blocker_token(self):
        summary = self._write(result="APPROVED_WITH_NOTES")
        self.assertFalse(summary.get("error"))
        ev = (self.root / ".governance" / "evidence-log.md").read_text(encoding="utf-8")
        self.assertIn("unresolved_blockers=0", ev)
        self.assertEqual(summary["review_id"], "REVIEW-FIX-236-R0")

    def test_needs_change_emits_revisit_required_fields(self):
        summary = self._write(result="NEEDS_CHANGE")
        self.assertTrue(summary["revisit_required"])
        self.assertEqual(summary["next_round"], "REVIEW-FIX-236-R1")
        self.assertEqual(summary["prev_report"], str(self.root / "report.md"))
        content = (self.root / ".governance" / "review-FIX-236-R0.md").read_text(
            encoding="utf-8")
        self.assertIn("复审必达", content)
        self.assertIn("next_round", content)

    def test_check30_live_scan_passes_on_machine_row(self):
        self._write()
        gov = self.root / ".governance"
        with mock.patch.object(vw, "SAMPLE_PATH", gov / "plan-tracker.md"), \
             mock.patch.object(vw, "EVIDENCE_PATH", gov / "evidence-log.md"), \
             mock.patch.object(vw, "GOVERNANCE_DIR", gov):
            result = vw.check_review_closure()
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["violations"], [])

    def test_invalid_result_fails_closed(self):
        summary = self._write(result="MAYBE")
        self.assertIn("error", summary)
        self.assertFalse((self.root / ".governance" / "review-FIX-236-R0.md").exists())

    def test_round_continuity_r0_then_r1_passes_check30(self):
        self._write(result="NEEDS_CHANGE")
        self._write(task_id="FIX-236", round_n=1, result="APPROVED")
        gov = self.root / ".governance"
        (gov / "plan-tracker.md").write_text(
            "# 项目配置\n\n### 优先级一览\n"
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| P1 | FIX-236 | review-record fixture | — | 0.73.0 | ✅ 完成 |\n",
            encoding="utf-8",
        )
        with mock.patch.object(vw, "SAMPLE_PATH", gov / "plan-tracker.md"), \
             mock.patch.object(vw, "EVIDENCE_PATH", gov / "evidence-log.md"), \
             mock.patch.object(vw, "GOVERNANCE_DIR", gov):
            result = vw.check_review_closure()
        self.assertEqual(result["verdict"], "PASS", result["reason"])


class ReviewRecordWiringTests(unittest.TestCase):
    """Wiring A: mapping resolution, explicit unit/gate wiring, best-effort degrade."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="rrw_")
        self.root = Path(self.tmpdir)
        (self.root / ".governance").mkdir()

    def test_mapping_missing_skips_wiring_with_warn_but_writes(self):
        summary = review_record.write_review_record(
            task_id="FIX-236", round_n=0, result="APPROVED",
            report_path=str(self.root / "report.md"), root=self.root,
        )
        self.assertFalse(summary["wiring"]["wired"])
        self.assertIn("mapping", summary["wiring"]["reason"].lower())
        self.assertTrue((self.root / ".governance" / "review-FIX-236-R0.md").is_file())

    def test_role_mapped_but_unit_missing_skips_with_warn(self):
        summary = review_record.write_review_record(
            task_id="FIX-236", round_n=0, result="APPROVED",
            report_path=str(self.root / "review-FIX-236-CODE-R0.md"), root=self.root,
        )
        self.assertFalse(summary["wiring"]["wired"])
        self.assertIn("unit", summary["wiring"]["reason"].lower())
        self.assertIn("G6", summary["wiring"]["reason"])

    def test_explicit_unit_gate_wires_approved_to_exit(self):
        unit_id = "shitu.story.Skeleton"
        runtime_path = _new_reflect_unit(self.tmpdir, unit_id)
        summary = review_record.write_review_record(
            task_id="FIX-236", round_n=0, result="APPROVED",
            report_path=str(self.root / "report.md"), root=self.root,
            unit_id=unit_id, gate_id="G6", runtime_file=runtime_path,
        )
        wiring = summary["wiring"]
        self.assertTrue(wiring["wired"])
        self.assertEqual(wiring["decision"], "exit")
        self.assertEqual(wiring["status"], "success")
        payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        unit = [u for u in payload["flow_units"] if u["flow_unit_id"] == unit_id][0]
        self.assertEqual(unit["gate_state"]["status"], "passed")

    def test_explicit_unit_gate_needs_change_drives_iterate(self):
        unit_id = "shitu.story.Skeleton"
        runtime_path = _new_reflect_unit(self.tmpdir, unit_id)
        summary = review_record.write_review_record(
            task_id="FIX-236", round_n=0, result="NEEDS_CHANGE",
            report_path=str(self.root / "report.md"), root=self.root,
            unit_id=unit_id, gate_id="G6", runtime_file=runtime_path,
        )
        wiring = summary["wiring"]
        self.assertTrue(wiring["wired"])
        self.assertEqual(wiring["decision"], "iterate")
        self.assertEqual(wiring["status"], "success")

    def test_wiring_exception_degrades_without_blocking(self):
        unit_id = "shitu.story.Skeleton"
        _new_reflect_unit(self.tmpdir, unit_id)
        with mock.patch(
            "review_record.process_gate_result",
            side_effect=RuntimeError("CAS lock conflict"),
        ):
            summary = review_record.write_review_record(
                task_id="FIX-236", round_n=0, result="APPROVED",
                report_path=str(self.root / "report.md"), root=self.root,
                unit_id=unit_id, gate_id="G6",
            )
        self.assertTrue(summary["wiring"]["degraded"])
        self.assertFalse(summary["wiring"]["wired"])
        self.assertTrue((self.root / ".governance" / "review-FIX-236-R0.md").is_file())
        self.assertIn(
            "REVIEW-FIX-236-R0",
            (self.root / ".governance" / "evidence-log.md").read_text(encoding="utf-8"),
        )

    def test_wiring_v1_noop_outcome_is_not_wired(self):
        # P2-1: process_gate_result returns status="illegal" for v1/classic
        # payloads (no-op, ADR-014 §6.5) — the wiring must NOT report wired.
        unit_id = "shitu.story.Skeleton"
        runtime = self.root / ".governance" / "flow-unit-runtime.json"
        runtime.write_text(json.dumps({"schema_version": "1.0"}), encoding="utf-8")
        summary = review_record.write_review_record(
            task_id="FIX-236", round_n=0, result="APPROVED",
            report_path=str(self.root / "report.md"), root=self.root,
            unit_id=unit_id, gate_id="G6", runtime_file=runtime,
        )
        wiring = summary["wiring"]
        self.assertFalse(wiring["wired"])
        self.assertEqual(wiring["status"], "illegal")
        self.assertFalse(wiring["degraded"])

    def test_wiring_missing_runtime_outcome_is_not_wired(self):
        # P2-1: runtime file missing → outcome status="error" — not wired,
        # but the record still lands and the status is preserved.
        summary = review_record.write_review_record(
            task_id="FIX-236", round_n=0, result="APPROVED",
            report_path=str(self.root / "report.md"), root=self.root,
            unit_id="shitu.story.Skeleton", gate_id="G6",
        )
        wiring = summary["wiring"]
        self.assertFalse(wiring["wired"])
        self.assertEqual(wiring["status"], "error")
        self.assertTrue((self.root / ".governance" / "review-FIX-236-R0.md").is_file())

    def test_gate_verdict_mapping_is_registry_data(self):
        # P2-2: the verdict→conclusion mapping lives in review_record (data),
        # not hardcoded in verify_workflow.
        self.assertEqual(review_record.GATE_VERDICT_TO_RESULT["passed"], "APPROVED")
        self.assertEqual(
            review_record.GATE_VERDICT_TO_RESULT["passed-with-conditions"],
            "APPROVED_WITH_NOTES",
        )
        self.assertEqual(review_record.GATE_VERDICT_TO_RESULT["blocked"], "NEEDS_CHANGE")
        self.assertNotIn("needs_human", review_record.GATE_VERDICT_TO_RESULT)


class ReviewRecordCliTests(unittest.TestCase):
    """CLI integration: verify_workflow review-record (thin entry)."""

    def test_cli_writes_record_in_fixture_project_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".governance").mkdir()
            report = root / "report.md"
            report.write_text("# report\n**审查结论**: **APPROVED**\n", encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(_INFRA_DIR / "verify_workflow.py"),
                 "review-record", "--project-root", str(root),
                 "--task", "FIX-236", "--round", "0", "--result", "APPROVED",
                 "--report", str(report), "--reviewer", "Code Reviewer Noether"],
                capture_output=True, text=True, encoding="utf-8", timeout=60,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["review_id"], "REVIEW-FIX-236-R0")
            self.assertTrue((root / ".governance" / "review-FIX-236-R0.md").is_file())
            self.assertIn(
                "REVIEW-FIX-236-R0",
                (root / ".governance" / "evidence-log.md").read_text(encoding="utf-8"),
            )


class ReviewRecordOverwriteGuardTests(unittest.TestCase):
    """FIX-289⑤ — 同 task+round 记录存在性守卫（P7 数据破坏防护）.

    Bug contract (FIX-281⑤ defect, REL-073 same-number overwrite near-miss):
    ``write_review_record`` used to overwrite an existing
    ``review-{task}-R{n}.md`` silently. Guard contract:

    - default → reject with an error dict (fail-closed: no file overwrite,
      no evidence row appended, existing record byte-identical);
    - ``force=True`` → deliberate overwrite WITH an audit trail: the previous
      record is backed up beside the record
      (``review-{task}-R{n}.pre-<ts>.md``), the new record carries a
      ``force_overwrite`` marker naming the backup, and the summary reports
      both.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="rro_")
        self.root = Path(self.tmpdir)
        (self.root / ".governance").mkdir()
        self.gov = self.root / ".governance"
        self.review_file = self.gov / "review-FIX-236-R0.md"
        self.evidence_log = self.gov / "evidence-log.md"

    def _write(self, **overrides):
        kwargs = {
            "task_id": "FIX-236",
            "round_n": 0,
            "result": "APPROVED",
            "report_path": str(self.root / "report.md"),
            "reviewer": "Code Reviewer Noether",
            "root": self.root,
        }
        kwargs.update(overrides)
        return review_record.write_review_record(**kwargs)

    def _review_row_count(self):
        return self.evidence_log.read_text(encoding="utf-8").count(
            "| REVIEW-FIX-236-R0 |")

    def test_duplicate_task_round_rejected_by_default_without_overwrite(self):
        first = self._write()
        self.assertFalse(first.get("error"))
        original = self.review_file.read_text(encoding="utf-8")
        self.assertIn("**审查结论**: **APPROVED**", original)
        # Same task+round again — must NOT silently replace the record.
        second = self._write(result="NEEDS_CHANGE")
        self.assertIn("error", second)
        self.assertEqual(
            self.review_file.read_text(encoding="utf-8"), original,
            "existing task+round record was overwritten")
        self.assertIn("APPROVED", original)
        # The rejected write must not leak a duplicate evidence row.
        self.assertEqual(self._review_row_count(), 1)

    def test_rejection_error_names_record_and_force_escape_hatch(self):
        self._write()
        second = self._write()
        self.assertIn("error", second)
        self.assertIn(str(self.review_file), second["error"])
        self.assertIn("force", second["error"])

    def test_force_overwrites_with_backup_and_marker(self):
        self._write()
        original = self.review_file.read_text(encoding="utf-8")
        summary = self._write(result="NEEDS_CHANGE", force=True)
        self.assertFalse(summary.get("error"))
        self.assertTrue(summary["force_overwrite"])
        backup = Path(summary["previous_record_backup"])
        self.assertTrue(backup.is_file())
        # 留痕 1: the previous record is preserved byte-for-byte.
        self.assertEqual(backup.read_text(encoding="utf-8"), original)
        new_text = self.review_file.read_text(encoding="utf-8")
        self.assertIn("**审查结论**: **NEEDS_CHANGE**", new_text)
        # 留痕 2: the new record marks the overwrite and names the backup.
        self.assertIn("force_overwrite", new_text)
        self.assertIn(backup.name, new_text)

    def test_force_chain_preserves_every_previous_record(self):
        self._write()
        v1 = self.review_file.read_text(encoding="utf-8")
        first = self._write(result="NEEDS_CHANGE", force=True)
        self.assertFalse(first.get("error"))
        v2 = self.review_file.read_text(encoding="utf-8")
        second = self._write(result="APPROVED", force=True)
        self.assertFalse(second.get("error"))
        backups = sorted(self.gov.glob("review-FIX-236-R0.pre-*.md"))
        self.assertEqual(len(backups), 2)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), v1)
        self.assertEqual(backups[1].read_text(encoding="utf-8"), v2)
        self.assertIn("**审查结论**: **APPROVED**",
                      self.review_file.read_text(encoding="utf-8"))

    def test_force_on_fresh_record_is_plain_write(self):
        summary = self._write(force=True)
        self.assertFalse(summary.get("error"))
        self.assertNotIn("force_overwrite", summary)
        self.assertNotIn("force_overwrite",
                         self.review_file.read_text(encoding="utf-8"))
        self.assertEqual(
            len(list(self.gov.glob("review-FIX-236-R0.pre-*.md"))), 0)

    def test_cli_duplicate_round_fails_closed_exit_2(self):
        # The review-record thin entry never passes force — a duplicate
        # task+round must exit 2 (fail-closed) without touching the record.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".governance").mkdir()
            report = root / "report.md"
            report.write_text("# report\n", encoding="utf-8")
            base_cmd = [sys.executable, str(_INFRA_DIR / "verify_workflow.py"),
                        "review-record", "--project-root", str(root),
                        "--task", "FIX-236", "--round", "0",
                        "--report", str(report)]
            first = subprocess.run(base_cmd + ["--result", "APPROVED"],
                                   capture_output=True, text=True,
                                   encoding="utf-8", timeout=60)
            self.assertEqual(first.returncode, 0, first.stderr)
            before = (root / ".governance" / "review-FIX-236-R0.md").read_text(
                encoding="utf-8")
            second = subprocess.run(base_cmd + ["--result", "NEEDS_CHANGE"],
                                    capture_output=True, text=True,
                                    encoding="utf-8", timeout=60)
            self.assertEqual(second.returncode, 2)
            self.assertIn("error", second.stdout)
            self.assertEqual(
                (root / ".governance" / "review-FIX-236-R0.md").read_text(
                    encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
