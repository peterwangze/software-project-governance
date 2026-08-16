"""Unit tests for infra/change_triage.py + Check 32 — FIX-237.4 / ADR-017 §4.4.

Covers the mandatory change-control triage for product-code task intake:

  - Four-step analysis: dependency (task-priority-analysis snapshot with
    unknown-dep fail-closed + cycle detection), priority determination
    (P0/P1/P2 with in-flight + version-chain context), conflict check
    (same-file overlap with in-flight tasks), version adaptation
    (target version vs current / planned-next).
  - Machine triage record (`.governance/change-triage/{TASK_ID}.json`
    containing the tool-output snapshot) + evidence-log row.
  - Fail-closed intake: unknown task-family dep / invalid priority / empty
    files / stale version / invalid task id produce NO record.
  - Check 32 (checks.triage_domain.check_change_triage): CLI wiring, record
    validity, and post-normalization product-code tasks without a triage
    record are FAIL; historical and quick-lane (.governance/-only) tasks are
    exempt.
  - CLI subprocess: `change-triage` runs the four steps and writes the
    record; fail-closed inputs exit 2.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_change_triage.py -v
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import change_triage as ct  # noqa: E402
from checks import triage_domain as td  # noqa: E402


# ─── Fixtures ────────────────────────────────────────────────────────────────
#
# Compact plan-tracker with a version roadmap (0.73.0 released, 0.74.0
# planned) and a 7-col priority table:
#   FIX-100 : ✅ completed, no deps                        → completed
#   FIX-101 : ⏳ pending, no deps                          → unblocked
#   FIX-102 : ⏳ pending, dep on FIX-100 (✅)               → in-flight product task
_FIXTURE_TRACKER = """\
# Plan Tracker

## 版本规划

### 版本路线图

| 版本 | 状态 | 预计日期 | 核心范围 |
|------|------|---------|---------|
| **0.73.0** | **已发布** | 2026-08-02 | baseline |
| **0.74.0** | **规划** | 2026-08+ | FIX-237/238 |

### 优先级一览

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| **P1** | FIX-100 | done task | — | 0.72.0 | closed | ✅ 完成 |
| **P2** | FIX-101 | pending no deps | — | 0.73.0 | open | ⏳ 待执行 |
| **P1** | FIX-102 | in-flight product task | FIX-100✅ | 0.73.0 | open | ⏳ 待执行 |
"""


# Fixture (FIX-250 P3-1 / FIX-248 R0): a roadmap table followed by several
# non-roadmap tables (优先级一览 / 检查项 / 里程碑 / 需求ID). The parser must
# STOP at the first non-version row after the roadmap table — these trailing
# tables must never leak into version_chain.
_FIXTURE_ROADMAP_WITH_TRAILING_TABLES = """\
# Plan Tracker

## 版本规划

### 版本路线图

| 版本 | 状态 | 预计日期 | 核心范围 |
|------|------|---------|---------|
| **0.66.1** | **已发布** | 2026-06-01 | baseline |
| **0.66.2** | **规划** | 2026-06+ | fix |
| **0.73.0** | **已发布** | 2026-08-02 | baseline |
| **0.74.0** | **规划** | 2026-08+ | FIX-237/238 |

### 优先级一览

| 优先级 | ID | 事项 | 依赖 |
|--------|----|------|------|
| P1 | FIX-100 | done | — |
| P2 | FIX-101 | pending | — |

### 检查项

| 检查项 | 结果 |
|--------|------|
| lint | ✅ |
| coverage | ✅ |

### 里程碑

| 里程碑 | 日期 |
|--------|------|
| M1 | 2026-08 |

### 需求ID

| 需求ID | 状态 |
|--------|------|
| REQ-001 | 完成 |
| REQ-002 | 规划 |
"""


def _record(task_id="FIX-102", files=None, priority="P1"):
    return {
        "schema_version": 1,
        "task_id": task_id,
        "priority": priority,
        "target_version": "0.73.0",
        "depends_on": ["FIX-100"],
        "files": files or ["skills/software-project-governance/infra/x.py"],
        "analysis": {
            "dependency": {"unknown_deps": [], "blocked_by": []},
            "priority_context": {"proposed": priority},
            "conflicts": [],
            "version": {"ok": True, "issues": []},
        },
        "snapshot": {
            "tool": "task-priority-analysis",
            "module_version": "0.71.0",
            "report_json": {"total": 3, "cycle_warning": False},
            "report_text": "# Task Priority Analysis\\n",
        },
    }


def _governance_dir(tmpdir):
    gov = Path(tmpdir) / ".governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "evidence-log.md").write_text(
        "# Evidence Log\n\n", encoding="utf-8")
    return gov


class DependencyAnalysisTests(unittest.TestCase):
    """Step a — task-priority-analysis snapshot + fail-closed dependency rules."""

    def test_split_dep_ids_drops_cross_entity_refs(self):
        self.assertEqual(
            ct.split_dep_ids("RISK-039, DEC-090; FIX-100, REVIEW-FIX-100"),
            ["FIX-100"],
        )

    def test_unknown_task_family_dep_fails_closed(self):
        analysis = ct.run_dependency_analysis(_FIXTURE_TRACKER, ["FIX-999"])
        self.assertEqual(analysis["unknown_deps"], ["FIX-999"])

    def test_blocked_by_incomplete_dep(self):
        analysis = ct.run_dependency_analysis(_FIXTURE_TRACKER, ["FIX-102"])
        self.assertIn("FIX-102", analysis["blocked_by"])
        self.assertEqual(analysis["unknown_deps"], [])

    def test_snapshot_carries_tool_output_json_and_text(self):
        analysis = ct.run_dependency_analysis(_FIXTURE_TRACKER, [])
        snap = analysis["snapshot"]
        self.assertEqual(snap["tool"], "task-priority-analysis")
        self.assertIn("cycle_warning", snap["report_json"])
        self.assertIn("Unblocked", snap["report_text"])

    def test_existing_cycle_surfaces_as_warning(self):
        tracker = _FIXTURE_TRACKER.replace(
            "| **P1** | FIX-102 | in-flight product task | FIX-100✅ |",
            "| **P1** | FIX-102 | in-flight product task | FIX-101 |",
        )
        tracker = tracker.replace(
            "| **P2** | FIX-101 | pending no deps | — |",
            "| **P2** | FIX-101 | pending no deps | FIX-102 |",
        )
        analysis = ct.run_dependency_analysis(tracker, [])
        self.assertTrue(analysis["cycle_warning"])
        self.assertTrue(analysis["cycles"])

    def test_new_task_that_would_create_cycle_is_detected(self):
        # FIX-102 depends on FIX-100; triaging FIX-100 with dep FIX-102
        # would close the loop FIX-100 -> FIX-102 -> FIX-100.
        analysis = ct.run_dependency_analysis(
            _FIXTURE_TRACKER, ["FIX-102"], task_id="FIX-100")
        self.assertTrue(analysis["new_task_cycle"])


class PriorityAndVersionTests(unittest.TestCase):
    """Steps b + d — priority determination and version adaptation."""

    def test_priority_context_counts_in_flight_and_parses_chain(self):
        ctx = ct.analyze_priority_context(_FIXTURE_TRACKER, "P2")
        self.assertEqual(ctx["proposed"], "P2")
        self.assertEqual(ctx["in_flight"]["P1"], 1)  # FIX-102
        self.assertEqual(ctx["in_flight"]["P2"], 1)  # FIX-101
        self.assertEqual(ctx["version_chain"][1]["version"], "0.74.0")

    def test_priority_context_rejects_invalid_priority(self):
        with self.assertRaises(ValueError):
            ct.analyze_priority_context(_FIXTURE_TRACKER, "P3")

    def test_parse_version_chain_strips_markdown(self):
        chain = ct.parse_version_chain(_FIXTURE_TRACKER)
        self.assertEqual(chain[0]["version"], "0.73.0")
        self.assertIn("已发布", chain[0]["status"])
        self.assertEqual(chain[1]["status"].strip(), "规划")

    def test_parse_version_chain_stops_at_trailing_non_version_tables(self):
        """FIX-250 (FIX-248 R0 P3-1): the roadmap table ends at the first
        non-version row — trailing tables (优先级一览/检查项/里程碑/需求ID)
        must not leak into version_chain."""
        chain = ct.parse_version_chain(_FIXTURE_ROADMAP_WITH_TRAILING_TABLES)
        versions = [row["version"] for row in chain]
        self.assertEqual(versions, ["0.66.1", "0.66.2", "0.73.0", "0.74.0"])
        for row in chain:
            self.assertRegex(row["version"], r"^\d+\.\d+")

    def test_version_older_than_current_is_error(self):
        result = ct.validate_version(
            "0.73.0", current_version="0.74.0",
            version_chain=[{"version": "0.74.0", "status": "规划"}])
        self.assertFalse(result["ok"])
        self.assertTrue(any("低于当前版本" in i for i in result["issues"]))

    def test_version_matching_planned_next_ok(self):
        result = ct.validate_version(
            "0.73.0", current_version="0.72.0",
            version_chain=[{"version": "0.73.0", "status": "规划"}])
        self.assertTrue(result["ok"])
        self.assertEqual(result["planned_next"], "0.73.0")

    def test_invalid_version_format_is_error(self):
        result = ct.validate_version(
            "not-a-version", current_version="0.72.0", version_chain=[])
        self.assertFalse(result["ok"])

    def test_unversioned_is_allowed(self):
        result = ct.validate_version(
            "未规划版本", current_version="0.72.0", version_chain=[])
        self.assertTrue(result["ok"])


class ConflictCheckTests(unittest.TestCase):
    """Step c — same-file conflict with in-flight tasks."""

    def test_overlap_with_in_flight_record_is_conflict(self):
        conflicts = ct.check_conflicts(
            ["skills/software-project-governance/infra/x.py"],
            [_record(files=["skills/software-project-governance/infra/x.py"])],
            completed_ids={"FIX-100"},
        )
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["task_id"], "FIX-102")

    def test_completed_task_record_is_not_conflict(self):
        conflicts = ct.check_conflicts(
            ["skills/software-project-governance/infra/x.py"],
            [_record(task_id="FIX-100",
                     files=["skills/software-project-governance/infra/x.py"])],
            completed_ids={"FIX-100"},
        )
        self.assertEqual(conflicts, [])

    def test_no_overlap_no_conflict(self):
        conflicts = ct.check_conflicts(
            ["skills/software-project-governance/infra/other.py"],
            [_record()],
            completed_ids=set(),
        )
        self.assertEqual(conflicts, [])


class TriageRecordTests(unittest.TestCase):
    """Machine triage record + evidence row + fail-closed intake."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="ct_")
        self.gov = _governance_dir(self.tmpdir)

    def _run(self, **overrides):
        kwargs = {
            "task_id": "FIX-103",
            "title": "new product task",
            "priority": "P2",
            "target_version": "0.73.0",
            "depends_on": ["FIX-100"],
            "files": ["skills/software-project-governance/infra/x.py"],
            "reason": "TDD fixture",
            "plan_tracker_text": _FIXTURE_TRACKER,
            "current_version": "0.72.0",
            "governance_dir": self.gov,
        }
        kwargs.update(overrides)
        return ct.run_triage(**kwargs)

    def test_happy_path_writes_record_with_snapshot_and_evidence_row(self):
        summary = self._run()
        self.assertFalse(summary.get("error"), summary)
        record_path = self.gov / "change-triage" / "FIX-103.json"
        self.assertTrue(record_path.is_file())
        record = json.loads(record_path.read_text(encoding="utf-8"))
        self.assertEqual(record["schema_version"], ct.TRIAGE_SCHEMA_VERSION)
        self.assertEqual(record["task_id"], "FIX-103")
        self.assertEqual(record["snapshot"]["tool"], "task-priority-analysis")
        self.assertIn("report_json", record["snapshot"])
        self.assertIn("report_text", record["snapshot"])
        self.assertEqual(record["analysis"]["dependency"]["unknown_deps"], [])
        self.assertEqual(record["analysis"]["priority_context"]["proposed"], "P2")
        evidence = (self.gov / "evidence-log.md").read_text(encoding="utf-8")
        self.assertIn("TRIAGE-FIX-103", evidence)
        self.assertIn("| FIX-103 |", evidence)
        self.assertIn("TRIAGED", evidence)

    def test_unknown_dep_fails_closed_no_record_no_evidence(self):
        summary = self._run(depends_on=["FIX-999"])
        self.assertIn("error", summary)
        self.assertFalse((self.gov / "change-triage" / "FIX-103.json").exists())
        evidence = (self.gov / "evidence-log.md").read_text(encoding="utf-8")
        self.assertNotIn("TRIAGE-FIX-103", evidence)

    def test_invalid_priority_fails_closed(self):
        summary = self._run(priority="P3")
        self.assertIn("error", summary)
        self.assertFalse((self.gov / "change-triage" / "FIX-103.json").exists())

    def test_empty_files_fails_closed(self):
        summary = self._run(files=[])
        self.assertIn("error", summary)
        self.assertFalse((self.gov / "change-triage" / "FIX-103.json").exists())

    def test_stale_version_fails_closed(self):
        summary = self._run(target_version="0.71.0")
        self.assertIn("error", summary)
        self.assertFalse((self.gov / "change-triage" / "FIX-103.json").exists())

    def test_invalid_task_id_fails_closed(self):
        summary = self._run(task_id="not-an-id")
        self.assertIn("error", summary)
        self.assertFalse((self.gov / "change-triage" / "not-an-id.json").exists())

    def test_new_task_cycle_fails_closed(self):
        summary = self._run(task_id="FIX-100", depends_on=["FIX-102"])
        self.assertIn("error", summary)
        self.assertFalse((self.gov / "change-triage" / "FIX-100.json").exists())

    def test_conflict_does_not_block_record_but_is_reported(self):
        record = _record(files=["skills/software-project-governance/infra/x.py"])
        record["task_id"] = "FIX-102"
        (self.gov / "change-triage").mkdir(exist_ok=True)
        (self.gov / "change-triage" / "FIX-102.json").write_text(
            json.dumps(record, ensure_ascii=False), encoding="utf-8")
        summary = self._run(files=["skills/software-project-governance/infra/x.py"])
        self.assertFalse(summary.get("error"), summary)
        self.assertEqual(summary["analysis"]["conflicts"][0]["task_id"], "FIX-102")

    def test_evidence_append_failure_rolls_back_record(self):
        """P2-2 (FIX-247): if the evidence-row append fails after the record
        write, the just-written record is rolled back — no half-written
        triage (record without evidence row) is left behind."""
        bad_evidence = self.gov / "no-such-dir" / "evidence-log.md"
        summary = self._run(evidence_path=bad_evidence)
        self.assertIn("error", summary)
        self.assertIn("cannot append evidence row", summary["error"])
        self.assertFalse((self.gov / "change-triage" / "FIX-103.json").exists())

    def test_re_triage_same_task_id_rejected(self):
        """P3-1 (FIX-247): re-triaging an already-recorded task id is
        rejected (fail-closed) — no record overwrite, no duplicate
        evidence row."""
        first = self._run()
        self.assertFalse(first.get("error"), first)
        second = self._run()
        self.assertIn("error", second)
        self.assertIn("already has a triage record", second["error"])
        evidence = (self.gov / "evidence-log.md").read_text(encoding="utf-8")
        self.assertEqual(evidence.count("TRIAGE-FIX-103"), 1)

    def test_re_triage_beats_unknown_dependency(self):
        """P3-3 (FIX-249): the re-triage guard runs BEFORE the pure
        dependency/priority/version analysis, so a duplicate task id that
        also carries an unknown dependency is rejected as a re-triage (not
        as an unknown dependency) — correct error priority, fail-closed."""
        first = self._run()
        self.assertFalse(first.get("error"), first)
        second = self._run(depends_on=["FIX-999"])
        self.assertIn("error", second)
        self.assertIn("already has a triage record", second["error"])
        self.assertNotIn("unknown", second["error"].lower())

    def test_re_triage_malformed_record_rejected_not_overwritten(self):
        """P3-4 (FIX-249): the re-triage guard checks the record file's
        existence directly, so an unparseable (malformed) record file is
        still rejected — it is never silently overwritten by a re-triage."""
        rec_dir = self.gov / "change-triage"
        rec_dir.mkdir(parents=True, exist_ok=True)
        malformed = "this is not valid json {"
        (rec_dir / "FIX-999.json").write_text(malformed, encoding="utf-8")
        summary = self._run(task_id="FIX-999")
        self.assertIn("error", summary)
        self.assertIn("already has a triage record", summary["error"])
        self.assertEqual(
            (rec_dir / "FIX-999.json").read_text(encoding="utf-8"), malformed)


class ChangeTriageCheckTests(unittest.TestCase):
    """Check 32 — checks/triage_domain.check_change_triage."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="ct32_")
        self.root = Path(self.tmpdir)
        self.gov = _governance_dir(self.tmpdir)
        (self.gov / "plan-tracker.md").write_text(
            _FIXTURE_TRACKER, encoding="utf-8")

    def _evidence(self, task_id, date_str, artifacts):
        return ("| EVD-{n} | {task} | 实现 | execution | 事实依据 | {art} | "
                "Developer | {date} | G11 | ✅ |\n").format(
                    n=task_id.split("-")[-1], task=task_id,
                    art=artifacts, date=date_str)

    def _check(self):
        return td.check_change_triage(
            root=self.root, governance_dir=self.gov,
            verify_path=_INFRA_DIR / "verify_workflow.py")

    def test_wiring_registered_in_verify_workflow(self):
        result = self._check()
        self.assertTrue(result["wiring"]["registered"])

    def test_no_records_and_historical_tasks_passes(self):
        (self.gov / "evidence-log.md").write_text(
            "# Evidence Log\n\n" + self._evidence("FIX-102", "2026-07-01",
                                                  "skills/software-project-governance/infra/x.py"),
            encoding="utf-8")
        result = self._check()
        self.assertEqual(result["verdict"], "PASS", result["issues"])

    def test_post_normalization_product_task_without_record_fails(self):
        (self.gov / "evidence-log.md").write_text(
            "# Evidence Log\n\n" + self._evidence("FIX-102", "2026-08-05",
                                                  "skills/software-project-governance/infra/x.py"),
            encoding="utf-8")
        result = self._check()
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("FIX-102", result["tasks_without_record"])

    def test_description_embedded_early_date_does_not_bypass_enforcement(self):
        """R0 P1-1 regression: ONLY the date column (cells[7]) is the
        earliest-evidence authority; a date embedded in the description
        (e.g. "自 2026-07-14（FIX-201）起") must NOT exempt the task."""
        row = self._evidence("FIX-102", "2026-08-05",
                             "skills/software-project-governance/infra/x.py")
        row = row.replace("| 实现 | execution |",
                          "| 实现 | 自 2026-07-14（FIX-201）起 execution |")
        (self.gov / "evidence-log.md").write_text(
            "# Evidence Log\n\n" + row, encoding="utf-8")
        result = self._check()
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("FIX-102", result["tasks_without_record"])

    def test_quick_lane_governance_only_task_exempt(self):
        (self.gov / "evidence-log.md").write_text(
            "# Evidence Log\n\n" + self._evidence("FIX-102", "2026-08-05",
                                                  ".governance/plan-tracker.md"),
            encoding="utf-8")
        result = self._check()
        self.assertEqual(result["verdict"], "PASS", result["issues"])

    def test_completed_task_exempt_from_no_record(self):
        """P2-1 (FIX-247): a completed task is exempt from the no-record
        enforcement even with post-normalization product-code evidence —
        retroactive triage is impossible for already-closed tasks."""
        (self.gov / "evidence-log.md").write_text(
            "# Evidence Log\n\n" + self._evidence("FIX-100", "2026-08-05",
                                                  "skills/software-project-governance/infra/x.py"),
            encoding="utf-8")
        result = self._check()
        self.assertEqual(result["verdict"], "PASS", result["issues"])
        self.assertNotIn("FIX-100", result["tasks_without_record"])

    def test_product_task_with_valid_record_passes(self):
        (self.gov / "change-triage").mkdir(exist_ok=True)
        (self.gov / "change-triage" / "FIX-102.json").write_text(
            json.dumps(_record(), ensure_ascii=False), encoding="utf-8")
        (self.gov / "evidence-log.md").write_text(
            "# Evidence Log\n\n" + self._evidence("FIX-102", "2026-08-05",
                                                  "skills/software-project-governance/infra/x.py"),
            encoding="utf-8")
        result = self._check()
        self.assertEqual(result["verdict"], "PASS", result["issues"])

    def test_malformed_record_fails(self):
        (self.gov / "change-triage").mkdir(exist_ok=True)
        (self.gov / "change-triage" / "FIX-102.json").write_text(
            json.dumps({"task_id": "FIX-102"}), encoding="utf-8")
        result = self._check()
        self.assertEqual(result["verdict"], "FAIL")
        self.assertTrue(any("FIX-102.json" in i for i in result["issues"]))


class ChangeTriageCliTests(unittest.TestCase):
    """CLI subprocess — four steps executable + fail-closed exits."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="ctcli_")
        self.root = Path(self.tmpdir)
        self.gov = _governance_dir(self.tmpdir)
        (self.gov / "plan-tracker.md").write_text(
            _FIXTURE_TRACKER, encoding="utf-8")

    def _run_cli(self, *extra):
        return subprocess.run(
            [sys.executable, str(_INFRA_DIR / "verify_workflow.py"),
             "change-triage", "--project-root", str(self.root)] + list(extra),
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )

    def test_cli_runs_four_steps_and_writes_record(self):
        done = self._run_cli(
            "--task", "FIX-103", "--title", "t", "--priority", "P2",
            "--version", "0.74.0", "--depends-on", "FIX-100",
            "--files", "skills/software-project-governance/infra/x.py",
            "--reason", "r",
        )
        self.assertEqual(done.returncode, 0, done.stderr + done.stdout)
        payload = json.loads(done.stdout)
        self.assertTrue((self.gov / "change-triage" / "FIX-103.json").is_file())
        self.assertEqual(payload["analysis"]["dependency"]["unknown_deps"], [])
        self.assertEqual(payload["snapshot"]["tool"], "task-priority-analysis")

    def test_cli_fails_closed_on_unknown_dep(self):
        done = self._run_cli(
            "--task", "FIX-103", "--priority", "P2", "--version", "0.74.0",
            "--depends-on", "FIX-999",
            "--files", "skills/software-project-governance/infra/x.py",
        )
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertFalse((self.gov / "change-triage" / "FIX-103.json").exists())


if __name__ == "__main__":
    unittest.main()
