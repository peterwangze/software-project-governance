"""Unit tests for infra/change_triage.py + Check 32 — FIX-237.4 / ADR-017 §4.4.

Covers the mandatory change-control triage for product-code task intake:

  - Four-step analysis: dependency (task-priority-analysis snapshot with
    unknown-dep fail-closed + cycle detection), priority determination
    (P0/P1/P2 with in-flight + version-chain context), conflict check
    (same-file overlap with in-flight tasks), version adaptation
    (target version vs current / planned-next).
  - Fifth step (FIX-271 / AUDIT-146 §7.2 R2): execution side-effect
    declaration — outside-repo side-effect signals in files / rationale /
    acceptance MUST be declared (``--side-effects``); user-real-environment
    signals auto-attach the R1 (one-of-three) review condition; undeclared
    detectable side effects record a WARN issue (advisory, never silent).
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
  - FEAT-013 (RISK-046 root cause): dispatch-lock write API
    (acquire_dispatch_locks + agent-locks-acquire CLI) — pre-write path
    existence validation, expected_new pre-created-file exemption,
    same-day change-triage files cross-check (WARN-disclosed mismatch),
    Check 26 optional-boolean expected_new schema sync + FEAT-011 write
    guard consumption.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_change_triage.py -v
"""

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import change_triage as ct  # noqa: E402
from checks import triage_domain as td  # noqa: E402


# ─── Fixtures ────────────────────────────────────────────────────────────────
#
# Compact plan-tracker with a version roadmap (0.73.0/0.74.0 released,
# 0.75.0 planned) and a 7-col priority table:
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
| **0.74.0** | **已发布** | 2026-08+ | FIX-237/238 |
| **0.75.0** | **规划** | 2026-08+ | FIX-253/254 |

### 优先级一览

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| **P1** | FIX-100 | done task | — | 0.72.0 | closed | ✅ 完成 |
| **P2** | FIX-101 | pending no deps | — | 0.73.0 | open | ⏳ 待执行 |
| **P1** | FIX-102 | in-flight product task | FIX-100✅ | 0.73.0 | open | ⏳ 待执行 |
"""


# Fixture (FIX-251): the headerless ``### 最近完成（本会话提交窗口）`` window —
# a 7-col task table with NO header row, exactly like the live plan-tracker.
# A triage dependency that resolves to one of these window tasks must NOT be
# rejected as unknown-dep (fail-closed) once the parser sees the window.
_FIXTURE_TRACKER_WITH_WINDOW = _FIXTURE_TRACKER + """\
### 最近完成（本会话提交窗口）

| **P2** | FIX-244 | archive --project-root fail-closed 校验 | FIX-242, FIX-243 | 未规划版本 | product code | ✅ 完成 (2026-08-06) |
| **P2** | FIX-247 | 观察项债务包——FIX-237/238 遗留处置 | FIX-237✅, FIX-238✅ | 未规划版本 | product code | ✅ 完成 (2026-08-16) |
> 历史提交窗口已归档。
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
| **0.74.0** | **已发布** | 2026-08+ | FIX-237/238 |
| **0.75.0** | **规划** | 2026-08+ | FIX-253/254 |

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

    def test_dep_on_recent_window_task_is_not_unknown(self):
        """FIX-251: a dependency that resolves to a task inside the headerless
        「最近完成」 window sub-section must NOT be reported as unknown (it was
        before — the window table was invisible to the parser) and, being a
        completed task, must not block the new triage either."""
        analysis = ct.run_dependency_analysis(
            _FIXTURE_TRACKER_WITH_WINDOW, ["FIX-247"])
        self.assertEqual(analysis["unknown_deps"], [])
        self.assertNotIn("FIX-247", analysis["blocked_by"])
        # The window task is now part of the same DAG as the priority table.
        self.assertIn("FIX-247", analysis["snapshot"]["report_json"]["completed"])

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


class ArchiveResolvedDepTests(unittest.TestCase):
    """FIX-341 — hot-miss dependency IDs resolve via the archive index.

    The archived-completed ID set is INJECTED (pure analysis, no I/O here);
    :func:`ct.run_triage` owns the index read. Fail-closed baseline: without
    the set (or on an index miss) the dep stays unknown.
    """

    def test_archived_completed_dep_resolves_not_unknown(self):
        analysis = ct.run_dependency_analysis(
            _FIXTURE_TRACKER, ["REL-076"],
            archive_completed_ids=frozenset({"REL-076"}))
        self.assertEqual(analysis["unknown_deps"], [])
        self.assertEqual(analysis["blocked_by"], [])
        self.assertEqual(analysis["archive_resolved_deps"], ["REL-076"])

    def test_index_miss_still_unknown_fail_closed(self):
        analysis = ct.run_dependency_analysis(
            _FIXTURE_TRACKER, ["FIX-171"],
            archive_completed_ids=frozenset({"REL-076"}))
        self.assertEqual(analysis["unknown_deps"], ["FIX-171"])
        self.assertEqual(analysis["archive_resolved_deps"], [])

    def test_no_archive_arg_keeps_baseline(self):
        analysis = ct.run_dependency_analysis(_FIXTURE_TRACKER, ["FIX-999"])
        self.assertEqual(analysis["unknown_deps"], ["FIX-999"])
        self.assertEqual(analysis["archive_resolved_deps"], [])

    def test_hot_incomplete_dep_still_blocks_even_if_archived_set_has_it(self):
        # A hot non-✅ row is authoritative: the archive set only resolves
        # IDs with NO hot row.
        analysis = ct.run_dependency_analysis(
            _FIXTURE_TRACKER, ["FIX-102"],
            archive_completed_ids=frozenset({"FIX-102"}))
        self.assertIn("FIX-102", analysis["blocked_by"])
        self.assertEqual(analysis["archive_resolved_deps"], [])


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
        self.assertEqual(chain[2]["version"], "0.75.0")
        self.assertEqual(chain[2]["status"].strip(), "规划")

    def test_parse_version_chain_stops_at_trailing_non_version_tables(self):
        """FIX-250 (FIX-248 R0 P3-1): the roadmap table ends at the first
        non-version row — trailing tables (优先级一览/检查项/里程碑/需求ID)
        must not leak into version_chain."""
        chain = ct.parse_version_chain(_FIXTURE_ROADMAP_WITH_TRAILING_TABLES)
        versions = [row["version"] for row in chain]
        self.assertEqual(
            versions, ["0.66.1", "0.66.2", "0.73.0", "0.74.0", "0.75.0"])
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


class SideEffectAnalysisTests(unittest.TestCase):
    """Step e (FIX-271 / AUDIT-146 §7.2 R2) — pure analysis of execution
    side-effect signals in triage inputs (files / rationale / acceptance)."""

    def test_repo_files_and_clean_text_detect_nothing(self):
        result = ct.analyze_side_effects(
            files=["skills/software-project-governance/infra/x.py"],
            reason="TDD fixture", acceptance="单元测试通过")
        self.assertFalse(result["detected"])
        self.assertFalse(result["touches_real_env"])
        self.assertFalse(result["requires_r1"])
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["review_conditions"], [])

    def test_real_env_acceptance_wording_touches_real_env(self):
        """R5-banned unqualified wording（真实安装/真实环境）in acceptance
        MUST be classified as a user-real-environment side effect."""
        result = ct.analyze_side_effects(
            files=["skills/software-project-governance/infra/x.py"],
            acceptance="测试 profile 真实安装冒烟通过")
        self.assertTrue(result["touches_real_env"])
        self.assertTrue(result["requires_r1"])
        self.assertTrue(any("R1" in c for c in result["review_conditions"]))

    def test_isolated_smoke_wording_is_outside_repo_but_not_real_env(self):
        """R5 standard wording（隔离环境安装冒烟+临时目录重定向）is compliant:
        installer execution IS an outside-repo side effect (declaration
        required) but is NOT a user-real-environment touch (no R1)."""
        result = ct.analyze_side_effects(
            files=["skills/software-project-governance/infra/x.py"],
            acceptance="隔离环境安装冒烟（环境变量重定向至临时目录）通过")
        self.assertTrue(result["detected"])
        self.assertFalse(result["touches_real_env"])
        self.assertFalse(result["requires_r1"])

    def test_outside_repo_file_targets_detected(self):
        result = ct.analyze_side_effects(
            files=["skills/software-project-governance/infra/x.py",
                   "~/.dsh/config.json"],
            reason="r")
        self.assertTrue(result["detected"])
        self.assertTrue(result["touches_real_env"])
        self.assertTrue(any("仓库外" in b or "真实环境" in b
                            for b in result["blast_radius"]))

    def test_absolute_path_outside_repo_detected(self):
        result = ct.analyze_side_effects(
            files=["C:\\Users\\peter\\.dsh\\settings.json"], reason="r")
        self.assertTrue(result["detected"])
        self.assertTrue(result["touches_real_env"])

    def test_network_publish_wording_detected(self):
        result = ct.analyze_side_effects(
            files=["skills/software-project-governance/infra/x.py"],
            reason="完成后 npm publish 发布到 registry")
        self.assertTrue(result["detected"])

    def test_undeclared_detection_records_warn_issue(self):
        result = ct.analyze_side_effects(
            files=["skills/software-project-governance/infra/x.py"],
            acceptance="真实环境安装验证")
        self.assertTrue(any(i.startswith("WARN") for i in result["issues"]))

    def test_declared_side_effect_removes_undeclared_warn(self):
        result = ct.analyze_side_effects(
            files=["skills/software-project-governance/infra/x.py"],
            acceptance="真实环境安装验证",
            declared="安装器写入 $DSH_HOME 下 profile；爆炸半径=用户 DSH 配置目录")
        self.assertFalse(any("声明缺失" in i for i in result["issues"]))
        # Declaration satisfies the declaration duty — but a real-env touch
        # still auto-attaches the R1 review condition (R2 second clause).
        self.assertTrue(result["requires_r1"])

    # ─── FIX-273 (FIX-271 CODE R0 P2-1/P2-2/P3-2/P3-3) boundary cases ──────

    def test_dotdot_escape_file_target_detected(self):
        r"""P3-3: a `../` parent-escape file target (the `\.\.` regex branch)
        is an outside-repo side effect — NOT a user real-environment touch."""
        result = ct.analyze_side_effects(
            files=["../outside/config.json"], reason="r")
        self.assertTrue(result["detected"])
        self.assertFalse(result["touches_real_env"])
        self.assertFalse(result["requires_r1"])
        self.assertTrue(any("仓库外" in b for b in result["blast_radius"]))

    def test_single_backslash_root_path_detected(self):
        r"""P2-1: a single-backslash root path (`\server\share\x.json`,
        drive-relative root form) is an outside-repo file target. Both the
        raw form (the new `\\` branch) and the normalized form (`/server/...`,
        `/` branch) participate in the outside-repo judgement."""
        result = ct.analyze_side_effects(
            files=["\\server\\share\\config.json"], reason="r")
        self.assertTrue(result["detected"])
        self.assertFalse(result["touches_real_env"])
        self.assertTrue(any("仓库外" in b for b in result["blast_radius"]))

    def test_unc_path_detected_but_not_real_env(self):
        r"""P2-1: a UNC path (`\\server\share\x.json`) is an outside-repo
        target — but it is a network share, NOT the user's home tree, so
        the R1 review condition MUST NOT be attached."""
        result = ct.analyze_side_effects(
            files=["\\\\server\\share\\config.json"], reason="r")
        self.assertTrue(result["detected"])
        self.assertFalse(result["touches_real_env"])
        self.assertFalse(result["requires_r1"])
        self.assertEqual(result["review_conditions"], [])
        self.assertTrue(any("仓库外" in b for b in result["blast_radius"]))

    def test_percent_userprofile_file_target_detected(self):
        """P3-3: a `%USERPROFILE%` env-var FILE target is an outside-repo
        side effect AND a user real-environment touch (R1 condition)."""
        result = ct.analyze_side_effects(
            files=["%USERPROFILE%\\config.json"], reason="r")
        self.assertTrue(result["detected"])
        self.assertTrue(result["touches_real_env"])
        self.assertTrue(result["requires_r1"])
        self.assertTrue(any("真实环境" in b for b in result["blast_radius"]))

    def test_normalized_backslash_root_participates_in_judgement(self):
        r"""P2-1: the normalized path participates in the outside-repo
        judgement (the old code matched ONLY the raw string). `\Users\...`
        raw matches the new `\\` branch AND its normalized `/Users/...` hits
        the `/` branch — a dual check mirroring the existing real-env dual
        search, so no form of the same path escapes classification."""
        result = ct.analyze_side_effects(
            files=["\\Users\\peter\\config.json"], reason="r")
        self.assertTrue(result["detected"])
        self.assertTrue(result["touches_real_env"])
        self.assertTrue(any("真实环境" in b for b in result["blast_radius"]))

    def test_backslash_separated_repo_file_not_flagged(self):
        r"""P2-1 negative guard: a repo-internal file written with Windows
        separators (`skills\...\x.py`) normalizes to a repo-relative path and
        MUST NOT be classified as an outside-repo side effect."""
        result = ct.analyze_side_effects(
            files=["skills\\software-project-governance\\infra\\x.py"],
            reason="TDD fixture")
        self.assertFalse(result["detected"])
        self.assertFalse(result["touches_real_env"])

    def test_real_env_text_re_ignores_case(self):
        """P3-2: `_REAL_ENV_TEXT_RE` carries IGNORECASE (matching the
        file-side `_REAL_ENV_FILE_RE`) — lowercase env-var variants
        (`%userprofile%` / `$home`) still trigger; Windows env vars are
        case-insensitive."""
        result = ct.analyze_side_effects(
            files=["skills/software-project-governance/infra/x.py"],
            acceptance="校验 %userprofile% 重定向目标")
        self.assertTrue(result["touches_real_env"])
        self.assertTrue(result["requires_r1"])

    def test_negation_context_still_triggers_real_env(self):
        """P2-2 behavioral lock — the wording detector is context-blind by
        design: a negation/quote context (「禁止修改 %USERPROFILE%」) still
        triggers as a real-env touch (advisory over-trigger, never a silent
        miss). The limitation is documented in the `analyze_side_effects`
        docstring; behavior is intentionally unchanged (FIX-273 P2-2)."""
        result = ct.analyze_side_effects(
            files=["skills/software-project-governance/infra/x.py"],
            acceptance="禁止修改 %USERPROFILE% 下的任意文件")
        self.assertTrue(result["touches_real_env"])
        self.assertTrue(any(i.startswith("WARN") for i in result["issues"]))


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

    def test_archived_dep_resolves_via_governance_archive_index(self):
        """FIX-341 end-to-end: a dep with NO hot row but proven archived-
        completed by ``.governance/archive/index.md`` passes the intake
        (pre-fix it failed closed as an unknown dependency)."""
        arch = self.gov / "archive"
        arch.mkdir(parents=True, exist_ok=True)
        (arch / "index.md").write_text(
            "# 归档索引\n\n## Task 索引\n\n"
            "| Task ID | 状态 | 版本 | 归档文件 |\n"
            "|---------|------|------|---------|\n"
            "| REL-076 | 已完成 (2026-09-12) | 0.80.0 | archive/tasks/v.md |\n",
            encoding="utf-8")
        summary = self._run(depends_on=["REL-076"])
        self.assertFalse(summary.get("error"), summary)
        record = json.loads(
            (self.gov / "change-triage" / "FIX-103.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(record["analysis"]["dependency"]["unknown_deps"], [])
        self.assertEqual(
            record["analysis"]["dependency"]["archive_resolved_deps"],
            ["REL-076"])

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


class SideEffectStepTests(unittest.TestCase):
    """Step e integration (FIX-271 / AUDIT-146 §7.2 R2) — run_triage
    machine record carries ``analysis.side_effect`` as a purely additive
    field; the four existing steps keep byte-identical shapes (backward
    compatibility hard constraint)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="ctse_")
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

    def test_pure_repo_task_gets_clean_side_effect_step(self):
        summary = self._run()
        self.assertFalse(summary.get("error"), summary)
        se = summary["analysis"]["side_effect"]
        self.assertFalse(se["detected"])
        self.assertFalse(se["touches_real_env"])
        self.assertFalse(se["requires_r1"])
        self.assertEqual(se["issues"], [])
        record = json.loads(
            (self.gov / "change-triage" / "FIX-103.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(record["analysis"]["side_effect"], se)

    def test_real_env_acceptance_in_record_with_r1_condition(self):
        summary = self._run(acceptance="测试 profile 真实安装冒烟通过")
        self.assertFalse(summary.get("error"), summary)
        se = summary["analysis"]["side_effect"]
        self.assertTrue(se["touches_real_env"])
        self.assertTrue(se["requires_r1"])
        self.assertTrue(any("R1" in c for c in se["review_conditions"]))
        # Undeclared detectable side effect → WARN issue (never silent).
        self.assertTrue(any(i.startswith("WARN") for i in se["issues"]))

    def test_four_step_fields_unchanged_by_fifth_step(self):
        """Backward compatibility hard constraint: the four existing
        analysis steps keep their exact keys/shapes; side_effect is
        appended LAST so the serialized four-step prefix is unchanged."""
        summary = self._run()
        analysis = summary["analysis"]
        self.assertEqual(
            list(analysis.keys()),
            ["dependency", "priority_context", "conflicts", "version",
             "side_effect"])
        self.assertEqual(analysis["dependency"]["unknown_deps"], [])
        self.assertEqual(analysis["priority_context"]["proposed"], "P2")
        self.assertEqual(analysis["conflicts"], [])
        self.assertEqual(analysis["version"]["target"], "0.73.0")
        record = json.loads(
            (self.gov / "change-triage" / "FIX-103.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(record["schema_version"], 1)


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
    """CLI subprocess — four steps executable + fail-closed exits.

    FIX-256 (FIX-255 F-1): the CLI subprocess derives the planned-next
    fixture row from the REAL plugin SKILL.md frontmatter so no hardcoded
    version literal re-reds this suite on every release (the FIX-248/FIX-255
    recurrence). FIX-288 ⑨: the CLI's ``current_version`` fact source is the
    HOST plan-tracker roadmap's highest released row (project current
    version — two-layer semantics), never the plugin SKILL.md frontmatter;
    the fixture's released rows therefore pin the version base and the
    SKILL-derived ``--version`` target stays above it (valid) and equals the
    planned row (no mismatch WARN) at any future version with zero edits.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="ctcli_")
        self.root = Path(self.tmpdir)
        self.gov = _governance_dir(self.tmpdir)
        from checks.version import extract_skill_version

        self.planned = extract_skill_version(_INFRA_DIR.parent / "SKILL.md")
        self.assertTrue(self.planned, "SKILL.md frontmatter version is missing")
        tracker = _FIXTURE_TRACKER.replace(
            "| **0.75.0** | **规划** |",
            f"| **{self.planned}** | **规划** |")
        (self.gov / "plan-tracker.md").write_text(tracker, encoding="utf-8")

    def _run_cli(self, *extra):
        return subprocess.run(
            [sys.executable, str(_INFRA_DIR / "verify_workflow.py"),
             "change-triage", "--project-root", str(self.root)] + list(extra),
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )

    def test_cli_runs_four_steps_and_writes_record(self):
        done = self._run_cli(
            "--task", "FIX-103", "--title", "t", "--priority", "P2",
            "--version", self.planned, "--depends-on", "FIX-100",
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
            "--task", "FIX-103", "--priority", "P2",
            "--version", self.planned, "--depends-on", "FIX-999",
            "--files", "skills/software-project-governance/infra/x.py",
        )
        self.assertEqual(done.returncode, 2, done.stdout)
        self.assertFalse((self.gov / "change-triage" / "FIX-103.json").exists())

    def test_cli_side_effect_step_survives_warn_without_fail_closed(self):
        """FIX-271 R2: --acceptance with real-env wording surfaces the R1
        review condition + WARN issue in the JSON output and the record,
        but WARN is advisory — the CLI still exits 0 (record written)."""
        done = self._run_cli(
            "--task", "FIX-104", "--title", "t", "--priority", "P2",
            "--version", self.planned, "--depends-on", "FIX-100",
            "--files", "skills/software-project-governance/infra/x.py",
            "--reason", "r",
            "--acceptance", "测试 profile 真实安装冒烟通过",
        )
        self.assertEqual(done.returncode, 0, done.stderr + done.stdout)
        payload = json.loads(done.stdout)
        se = payload["analysis"]["side_effect"]
        self.assertTrue(se["touches_real_env"])
        self.assertTrue(any(i.startswith("WARN") for i in se["issues"]))
        record = json.loads(
            (self.gov / "change-triage" / "FIX-104.json")
            .read_text(encoding="utf-8"))
        self.assertTrue(record["analysis"]["side_effect"]["requires_r1"])

    def test_cli_side_effects_declaration_end_to_end(self):
        """P3-3 (FIX-273): `--side-effects` is passed end to end through the
        CLI — the declared string lands in ``side_effect.declared`` (both the
        JSON output and the machine record), the undeclared-WARN is
        suppressed, but a real-env touch still carries the R1 review
        condition (declaration duty ≠ R1 execution gate — FIX-271)."""
        declared = "安装器写入 $DSH_HOME 下 profile；爆炸半径=用户 DSH 配置目录"
        done = self._run_cli(
            "--task", "FIX-105", "--title", "t", "--priority", "P2",
            "--version", self.planned, "--depends-on", "FIX-100",
            "--files", "skills/software-project-governance/infra/x.py",
            "--reason", "r",
            "--acceptance", "真实环境安装验证",
            "--side-effects", declared,
        )
        self.assertEqual(done.returncode, 0, done.stderr + done.stdout)
        payload = json.loads(done.stdout)
        se = payload["analysis"]["side_effect"]
        self.assertEqual(se["declared"], declared)
        self.assertFalse(any("声明缺失" in i for i in se["issues"]))
        self.assertTrue(se["touches_real_env"])
        self.assertTrue(se["requires_r1"])
        record = json.loads(
            (self.gov / "change-triage" / "FIX-105.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(record["analysis"]["side_effect"]["declared"], declared)


# ─── FIX-288 ⑨ — version-adaptation fact source + planned-next selector ─────
#
# Two-layer version semantics (FIX-288): the WORKFLOW version (the plugin's
# own SKILL.md frontmatter) is NOT the PROJECT current version. The
# version-adaptation step must validate against the host plan-tracker
# roadmap's highest 「已发布」 row; the planned-next pick must be the lowest
# planned row ABOVE that current version (the pre-fix first-match selector
# recorded planned_next="0.66.2" — a stale 「补偿发布规划中」 row that precedes
# the released block in row order — on the live roadmap, with a false
# mismatch WARN). Router live recurrence: REL-002 intake rejected because a
# host target below the WORKFLOW version was fail-closed refused (EVO-004/
# EV-038 precedents).
_HOST_TRACKER_LIVE_SHAPE = """\
# Plan Tracker

## 版本规划

### 版本路线图

| 版本 | 状态 | 预计日期 | 核心范围 |
|------|------|---------|---------|
| **0.54.3** | **已撤回/失效** | — | withdrawn |
| **0.66.1** | **发布事故 / 不可信发布** | — | untrusted |
| **0.66.2** | **补偿发布规划中** | — | stale planned row (first-match bait) |
| **0.73.0** | **已发布** | 2026-08-02 | baseline |
| **0.74.0** | **已发布** | 2026-08+ | prev |
| **0.78.0** | **已发布** | 2026-08-26 | current release |
| **0.78.1** | **规划中** | 2026-08+ | next patch |

### 优先级一览

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| **P1** | FIX-100 | done task | — | 0.73.0 | closed | ✅ 完成 |
| **P2** | FIX-101 | pending no deps | — | 0.78.1 | open | ⏳ 待执行 |
"""

# A host project far behind the workflow version — the REL-002 shape.
_OLD_HOST_TRACKER = """\
# Plan Tracker

## 版本规划

### 版本路线图

| 版本 | 状态 | 预计日期 | 核心范围 |
|------|------|---------|---------|
| **0.9.0** | **已发布** | 2026-01-01 | baseline |
| **0.10.0** | **已发布** | 2026-02-01 | current release |
| **0.11.0** | **规划** | 2026-03+ | next |

### 优先级一览

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| **P1** | FIX-100 | done task | — | 0.9.0 | closed | ✅ 完成 |
| **P2** | FIX-101 | pending no deps | — | 0.10.0 | open | ⏳ 待执行 |
"""

# 无版本规划行宿主 — no roadmap at all.
_NO_ROADMAP_TRACKER = """\
# Plan Tracker

### 优先级一览

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| **P2** | FIX-101 | pending no deps | — | 未规划版本 | open | ⏳ 待执行 |
"""


class ProjectCurrentVersionTests(unittest.TestCase):
    """FIX-288 ⑨ — derive_project_current_version + planned-next selector."""

    def test_current_version_is_highest_released_roadmap_row(self):
        # Withdrawn (已撤回/失效) and untrusted (发布事故/不可信发布) rows are
        # NOT released fact — 0.54.3/0.66.1 must never become the base; the
        # stale planned 0.66.2 neither.
        self.assertEqual(
            ct.derive_project_current_version(_HOST_TRACKER_LIVE_SHAPE),
            "0.78.0")

    def test_old_host_derives_project_current_not_workflow_version(self):
        # The REL-002 recurrence shape: a host far behind the workflow
        # version derives ITS OWN current version (0.10.0), never the
        # plugin SKILL.md frontmatter version (0.78.0+).
        current = ct.derive_project_current_version(_OLD_HOST_TRACKER)
        self.assertEqual(current, "0.10.0")
        self.assertNotEqual(current, "0.78.0")

    def test_no_roadmap_host_derives_empty_current(self):
        # 无版本规划行宿主: no released row → "" → validate_version skips
        # the lower-bound comparison (triage proceeds normally).
        self.assertEqual(
            ct.derive_project_current_version(_NO_ROADMAP_TRACKER), "")

    def test_planned_next_is_lowest_above_current_not_first_match(self):
        # Pre-fix first-match bug: on the live-shaped roadmap the stale
        # 「0.66.2 补偿发布规划中」 row precedes the released block, so the
        # pre-fix code recorded planned_next="0.66.2" and emitted a false
        # mismatch WARN for the true next version 0.78.1.
        result = ct.validate_version(
            "0.78.1", current_version="0.78.0",
            version_chain=ct.parse_version_chain(_HOST_TRACKER_LIVE_SHAPE))
        self.assertTrue(result["ok"], result["issues"])
        self.assertEqual(result["planned_next"], "0.78.1")
        self.assertEqual(result["issues"], [])

    def test_planned_next_none_when_all_planned_below_current(self):
        # Every planned row at-or-below the current version → there is no
        # next planned version to mismatch → no advisory WARN.
        result = ct.validate_version(
            "0.79.0", current_version="0.78.0",
            version_chain=[{"version": "0.66.2", "status": "补偿发布规划中"}])
        self.assertTrue(result["ok"], result["issues"])
        self.assertIsNone(result["planned_next"])
        self.assertEqual(result["issues"], [])

    def test_unversioned_target_reports_true_planned_next(self):
        result = ct.validate_version(
            "未规划版本", current_version="0.78.0",
            version_chain=ct.parse_version_chain(_HOST_TRACKER_LIVE_SHAPE))
        self.assertTrue(result["ok"], result["issues"])
        self.assertEqual(result["planned_next"], "0.78.1")

    def test_run_triage_with_derived_current_accepts_target_above(self):
        # 入账路径 seam (exactly what the wired CLI does): derive the project
        # current version from the host tracker and triage the planned-next
        # target — pre-FIX-288 this shape was rejected with 「目标版本 …
        # 低于当前版本 <workflow-version>」.
        tmpdir = tempfile.mkdtemp(prefix="ctpcv_")
        gov = _governance_dir(tmpdir)
        summary = ct.run_triage(
            task_id="FIX-106", title="host next patch", priority="P2",
            target_version="0.11.0", depends_on=["FIX-100"],
            files=["skills/software-project-governance/infra/x.py"],
            reason="router REL-002 reproduction",
            plan_tracker_text=_OLD_HOST_TRACKER,
            current_version=ct.derive_project_current_version(
                _OLD_HOST_TRACKER),
            governance_dir=gov,
        )
        self.assertFalse(summary.get("error"), summary)
        record = json.loads(
            (gov / "change-triage" / "FIX-106.json").read_text(
                encoding="utf-8"))
        self.assertEqual(record["analysis"]["version"]["current"], "0.10.0")
        self.assertEqual(
            record["analysis"]["version"]["planned_next"], "0.11.0")

    def test_planned_next_cur_unknown_takes_lowest_not_first_match(self):
        # LP-1 (REVIEW-FIX-288-R0 P2-1): direct coverage of the cur=None
        # branch — no project current version derivable → the LOWEST planned
        # row wins regardless of roadmap row order (first-match regression
        # lock: 0.78.1 leads this fixture's row order and must NOT be picked).
        # NOTE (Coordinator V-A ruling 2026-08-28): expected value locks
        # CURRENT min-overall semantics; the residual mis-WARN for
        # released-less hosts is registered as backlog candidate (see
        # EVD-914) — if semantics change to max, this assertion must flip.
        result = ct.validate_version(
            "0.78.1", current_version="",
            version_chain=[{"version": "0.78.1", "status": "规划中"},
                           {"version": "0.66.2", "status": "补偿发布规划中"}])
        self.assertTrue(result["ok"], result["issues"])
        self.assertEqual(result["planned_next"], "0.66.2")


class ChangeTriageProjectVersionCliTests(unittest.TestCase):
    """FIX-288 ⑨ end to end — the CLI derives the PROJECT current version
    from the host plan-tracker roadmap (never the plugin SKILL.md
    frontmatter), so an old host can triage a target above ITS OWN current
    version. Pre-fix this exited 2 with 「目标版本 0.11.0 低于当前版本
    <workflow-version>」 and wrote NO record (router REL-002 live shape)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="ctclifix288_")
        self.root = Path(self.tmpdir)
        self.gov = _governance_dir(self.tmpdir)
        (self.gov / "plan-tracker.md").write_text(
            _OLD_HOST_TRACKER, encoding="utf-8")

    def _run_cli(self, *extra):
        return subprocess.run(
            [sys.executable, str(_INFRA_DIR / "verify_workflow.py"),
             "change-triage", "--project-root", str(self.root)] + list(extra),
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )

    def test_old_host_can_triage_target_above_project_current(self):
        done = self._run_cli(
            "--task", "FIX-107", "--title", "t", "--priority", "P2",
            "--version", "0.11.0", "--depends-on", "FIX-100",
            "--files", "skills/software-project-governance/infra/x.py",
            "--reason", "router REL-002 reproduction",
        )
        self.assertEqual(done.returncode, 0, done.stderr + done.stdout)
        payload = json.loads(done.stdout)
        self.assertEqual(payload["analysis"]["version"]["current"], "0.10.0")
        self.assertEqual(
            payload["analysis"]["version"]["planned_next"], "0.11.0")
        self.assertTrue(
            (self.gov / "change-triage" / "FIX-107.json").is_file())


# ─── FEAT-013 (RISK-046 root cause) — dispatch-lock write API ───────────────
#
# RISK-046: Coordinator dispatch locks were hand-assembled with no
# write-time validation — a typo'd / placeholder / not-yet-created path
# entered file_locks directly (FIX-288 live evidence: a lock on the
# nonexistent skills/change-triage/SKILL.md), and the lock file set could
# drift from the same-day change-triage record's files declaration with
# no cross-check. FEAT-013 lands the machine write API
# (change_triage.acquire_dispatch_locks + agent-locks-acquire CLI):
#
#   Face 1  pre-write path existence validation — a lock target that is
#           not an existing file is REJECTED (path + remediation hint);
#   Face 1b pre-created-file exemption — a file the task will create is
#           declared expected_new (persisted as ``expected_new: true`` on
#           the lock entry; optional field, absent on legacy locks);
#   Face 2  same-day change-triage files cross-check — mismatch is a
#           disclosed WARN (never blocking: triage precedes the lock and
#           the lock may legitimately carry dispatch-preauthorized
#           extensions); a match stays silent.
#
# Check 26 schema sync: ``expected_new`` is optional-boolean when present
# (backward compatibility hard gate: legacy locks without the field PASS),
# and the FEAT-011 write guard face 3 consumes the same schema wholesale.

_LOCK_NOW = datetime(2026, 9, 10, 20, 50, 0)  # fixed clock → today 2026-09-10


def _triage_record_for_lock(task_id="FIX-210", files=None,
                            created_at="2026-09-10"):
    return {
        "schema_version": 1,
        "task_id": task_id,
        "files": files or ["product/existing_a.py"],
        "created_at": created_at,
    }


class DispatchLockCrossCheckTests(unittest.TestCase):
    """Face 2 — cross_check_triage_files (pure set comparison)."""

    def test_same_day_match_returns_true_and_balanced(self):
        cc = ct.cross_check_triage_files(
            "FIX-210", ["product/existing_a.py"],
            [_triage_record_for_lock()], "2026-09-10")
        self.assertIsNotNone(cc)
        self.assertTrue(cc["matches"])
        self.assertEqual(cc["lock_only"], [])
        self.assertEqual(cc["triage_only"], [])

    def test_same_day_mismatch_lists_both_sides(self):
        cc = ct.cross_check_triage_files(
            "FIX-210",
            ["product/existing_a.py", "product/extra_lock.py"],
            [_triage_record_for_lock(
                files=["product/existing_a.py", "product/triage_only.py"])],
            "2026-09-10")
        self.assertFalse(cc["matches"])
        self.assertEqual(cc["lock_only"], ["product/extra_lock.py"])
        self.assertEqual(cc["triage_only"], ["product/triage_only.py"])

    def test_missing_or_other_day_record_returns_none(self):
        # No record at all → None (silent).
        self.assertIsNone(ct.cross_check_triage_files(
            "FIX-210", ["product/existing_a.py"], [], "2026-09-10"))
        # Record exists but created another day → None (同期=当日 only).
        self.assertIsNone(ct.cross_check_triage_files(
            "FIX-210", ["product/existing_a.py"],
            [_triage_record_for_lock(created_at="2026-09-01")],
            "2026-09-10"))
        # Another task's same-day record → None (task_id must match).
        self.assertIsNone(ct.cross_check_triage_files(
            "FIX-210", ["product/existing_a.py"],
            [_triage_record_for_lock(task_id="FIX-999")], "2026-09-10"))


class DispatchLockAcquireTests(unittest.TestCase):
    """Faces 1 + 1b + 2 through acquire_dispatch_locks (fail-closed)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="ctlock_")
        self.root = Path(self.tmpdir)
        self.gov = _governance_dir(self.tmpdir)
        (self.root / "product").mkdir(exist_ok=True)
        (self.root / "product" / "existing_a.py").write_text(
            "x = 1\n", encoding="utf-8")

    def _acquire(self, **overrides):
        kwargs = {
            "task_id": "FIX-210",
            "files": ["product/existing_a.py"],
            "governance_dir": self.gov,
            "repo_root": self.root,
            "now": _LOCK_NOW,
        }
        kwargs.update(overrides)
        return ct.acquire_dispatch_locks(**kwargs)

    def _locks_path(self):
        return self.gov / "agent-locks.json"

    def test_missing_path_rejected_no_write(self):
        """Face 1: a lock target that is not an existing file is rejected
        with the path + remediation hint; NOTHING is written."""
        summary = self._acquire(files=["product/ghost_typo.py"])
        self.assertIn("error", summary)
        self.assertIn("product/ghost_typo.py", summary["error"])
        self.assertIn("expected_new", summary["error"])
        self.assertFalse(self._locks_path().exists())

    def test_expected_new_exemption_persists_flag(self):
        """Face 1b: a declared pre-created target bypasses the existence
        check and persists ``expected_new: true``; the existing-file entry
        carries no expected_new key."""
        summary = self._acquire(
            files=["product/existing_a.py", "product/to_be_created.py"],
            expected_new=["product/to_be_created.py"])
        self.assertFalse(summary.get("error"), summary)
        data = json.loads(self._locks_path().read_text(encoding="utf-8"))
        self.assertTrue(
            data["file_locks"]["product/to_be_created.py"]["expected_new"])
        self.assertNotIn(
            "expected_new", data["file_locks"]["product/existing_a.py"])

    def test_expected_new_outside_files_rejected(self):
        summary = self._acquire(expected_new=["product/not_listed.py"])
        self.assertIn("error", summary)
        self.assertIn("subset", summary["error"])
        self.assertFalse(self._locks_path().exists())

    def test_happy_path_writes_full_schema_and_merges(self):
        """Normal path: Check 26 required fields on both entry kinds, and
        an unrelated task's pre-existing lock survives the merge."""
        other = {
            "active_tasks": {
                "FIX-001": {
                    "agent_role": "Developer",
                    "spawned_at": "2026-09-10T08:00:00",
                    "coordinator_session": "sess-other",
                    "target_files": ["product/other.py"],
                    "description": "other",
                    "acquired": "2026-09-10T08:00:00",
                    "files": ["product/other.py"],
                }},
            "file_locks": {
                "product/other.py": {
                    "locked_by": "FIX-001",
                    "locked_at": "2026-09-10T08:00:00",
                    "ttl_seconds": 3600,
                    "ttl_reason": "other",
                }},
        }
        self._locks_path().write_text(
            json.dumps(other, indent=4), encoding="utf-8")
        summary = self._acquire()
        self.assertFalse(summary.get("error"), summary)
        data = json.loads(self._locks_path().read_text(encoding="utf-8"))
        # Merge kept the other task's entries...
        self.assertIn("FIX-001", data["active_tasks"])
        self.assertIn("product/other.py", data["file_locks"])
        # ...and added this task's full-schema entries.
        self.assertIn("FIX-210", data["active_tasks"])
        entry = data["active_tasks"]["FIX-210"]
        for key in ("spawned_at", "coordinator_session", "target_files"):
            self.assertIn(key, entry)
        lock = data["file_locks"]["product/existing_a.py"]
        self.assertEqual(lock["locked_by"], "FIX-210")
        for key in ("locked_by", "locked_at", "ttl_seconds", "ttl_reason"):
            self.assertIn(key, lock)
        self.assertEqual(lock["locked_at"], "2026-09-10T20:50:00")

    def test_cross_check_match_no_warning(self):
        rec_dir = self.gov / "change-triage"
        rec_dir.mkdir(exist_ok=True)
        (rec_dir / "FIX-210.json").write_text(json.dumps(
            _triage_record_for_lock()), encoding="utf-8")
        summary = self._acquire()
        self.assertFalse(summary.get("error"), summary)
        self.assertEqual(summary["warnings"], [])
        self.assertTrue(summary["cross_check"]["matches"])

    def test_cross_check_mismatch_warns_but_writes(self):
        """Face 2: mismatch is WARN-disclosed and NON-blocking — the write
        still lands (triage precedes the lock; the lock may carry
        dispatch-preauthorized extensions — a human must SEE it, not be
        stopped by it). Both lock targets exist on disk (face 1 passes);
        only the declared SETS differ from the triage record."""
        (self.root / "product" / "lock_extra.py").write_text(
            "y = 2\n", encoding="utf-8")
        rec_dir = self.gov / "change-triage"
        rec_dir.mkdir(exist_ok=True)
        (rec_dir / "FIX-210.json").write_text(json.dumps(
            _triage_record_for_lock(
                files=["product/triage_says_this.py"])),
            encoding="utf-8")
        summary = self._acquire(files=[
            "product/existing_a.py", "product/lock_extra.py"])
        self.assertFalse(summary.get("error"), summary)
        self.assertEqual(len(summary["warnings"]), 1)
        self.assertIn("WARN", summary["warnings"][0])
        self.assertIn("product/lock_extra.py", summary["warnings"][0])
        self.assertIn("product/triage_says_this.py", summary["warnings"][0])
        self.assertTrue(self._locks_path().is_file())

    def test_duplicate_task_rejected(self):
        first = self._acquire()
        self.assertFalse(first.get("error"), first)
        second = self._acquire()
        self.assertIn("error", second)
        self.assertIn("already", second["error"])

    def test_conflicting_file_lock_by_other_task_rejected(self):
        self._locks_path().write_text(json.dumps({
            "active_tasks": {"FIX-001": {
                "spawned_at": "2026-09-10T08:00:00",
                "coordinator_session": "s", "target_files": [],
            }},
            "file_locks": {"product/existing_a.py": {
                "locked_by": "FIX-001",
                "locked_at": "2026-09-10T08:00:00",
                "ttl_seconds": 3600, "ttl_reason": "held",
            }},
        }), encoding="utf-8")
        summary = self._acquire()
        self.assertIn("error", summary)
        self.assertIn("FIX-001", summary["error"])
        # Fail-closed: the other task's lock file is left untouched.
        data = json.loads(self._locks_path().read_text(encoding="utf-8"))
        self.assertEqual(
            data["file_locks"]["product/existing_a.py"]["locked_by"],
            "FIX-001")

    def test_malformed_locks_file_rejected_unchanged(self):
        malformed = "this is not json {"
        self._locks_path().write_text(malformed, encoding="utf-8")
        summary = self._acquire()
        self.assertIn("error", summary)
        self.assertEqual(
            self._locks_path().read_text(encoding="utf-8"), malformed)


class AgentLocksCheck26SyncTests(unittest.TestCase):
    """Check 26 schema sync + FEAT-011 write-guard consumption face.

    ``expected_new`` is optional-boolean; legacy locks without the field
    keep PASSING (backward-compatibility hard gate). The write guard face
    3 reuses check_agent_locks_format wholesale, so the synced schema is
    consumed with no second definition.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="ct26_")
        self.gov = Path(self.tmpdir) / ".governance"
        self.gov.mkdir(parents=True)

    def _write_locks(self, expected_new=None):
        entry = {
            "locked_by": "FIX-210",
            "locked_at": "2026-09-10T20:50:00",
            "ttl_seconds": 14400,
            "ttl_reason": "test",
        }
        if expected_new is not None:
            entry["expected_new"] = expected_new
        (self.gov / "agent-locks.json").write_text(json.dumps({
            "active_tasks": {"FIX-210": {
                "agent_role": "Developer",
                "spawned_at": "2026-09-10T20:50:00",
                "coordinator_session": "s",
                "target_files": ["product/new_file.py"],
                "files": ["product/new_file.py"],
            }},
            "file_locks": {"product/new_file.py": entry},
        }), encoding="utf-8")

    def _format_issues(self):
        import verify_workflow as vw  # lazy: engine import stays local
        with patch.object(vw, "GOVERNANCE_DIR", self.gov):
            return vw.check_agent_locks_format()

    def test_legacy_lock_without_expected_new_still_passes(self):
        self._write_locks(expected_new=None)
        self.assertEqual(self._format_issues(), [])

    def test_expected_new_true_passes(self):
        self._write_locks(expected_new=True)
        self.assertEqual(self._format_issues(), [])

    def test_expected_new_non_bool_is_schema_violation(self):
        self._write_locks(expected_new="yes")
        issues = self._format_issues()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["type"], "schema_violation")
        self.assertIn("expected_new", issues[0]["detail"])

    def test_write_guard_face3_consumes_synced_schema(self):
        """FEAT-011 write guard face 3 (agent_locks) reuses Check 26 — a
        valid expected_new lock passes the guard; a malformed one FAILS
        (consumption verified, not assumed)."""
        import verify_workflow as vw
        self._write_locks(expected_new=True)
        with patch.object(vw, "GOVERNANCE_DIR", self.gov):
            result = vw.check_governance_write_shapes()
        self.assertEqual(result["agent_locks"]["status"], "PASS")
        self._write_locks(expected_new="yes")
        with patch.object(vw, "GOVERNANCE_DIR", self.gov):
            result = vw.check_governance_write_shapes()
        self.assertEqual(result["agent_locks"]["status"], "FAIL")
        self.assertIn("expected_new",
                      result["agent_locks"]["issues"][0]["detail"])


class AgentLocksAcquireCliTests(unittest.TestCase):
    """CLI end to end — agent-locks-acquire (FEAT-013 thin entry)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="ctlockcli_")
        self.root = Path(self.tmpdir)
        self.gov = _governance_dir(self.tmpdir)
        (self.root / "product").mkdir(exist_ok=True)
        (self.root / "product" / "existing_a.py").write_text(
            "x = 1\n", encoding="utf-8")

    def _run_cli(self, *extra):
        return subprocess.run(
            [sys.executable, str(_INFRA_DIR / "verify_workflow.py"),
             "agent-locks-acquire", "--project-root", str(self.root)]
            + list(extra),
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )

    def test_cli_rejects_missing_path_exit_2_no_write(self):
        """Live-shape refusal record: a nonexistent lock target exits 2
        fail-closed and writes no agent-locks.json. The refusal lands in
        the stdout JSON summary (house pattern — cmd_change_triage)."""
        done = self._run_cli(
            "--task", "FIX-210", "--files", "skills/typo/ghost.py",
            "--ttl-reason", "FEAT-013 refusal demo")
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertIn("skills/typo/ghost.py", done.stdout)
        self.assertIn("expected_new", done.stdout)
        self.assertFalse((self.gov / "agent-locks.json").exists())

    def test_cli_success_expected_new_and_warn_disclosure(self):
        rec_dir = self.gov / "change-triage"
        rec_dir.mkdir(exist_ok=True)
        (rec_dir / "FIX-211.json").write_text(json.dumps(
            _triage_record_for_lock(
                task_id="FIX-211", files=["product/existing_a.py"])),
            encoding="utf-8")
        done = self._run_cli(
            "--task", "FIX-211",
            "--files", "product/existing_a.py,product/to_be_created.py",
            "--expected-new", "product/to_be_created.py",
            "--role", "Developer", "--session", "sess-feat013",
            "--ttl-reason", "FEAT-013 CLI demo")
        self.assertEqual(done.returncode, 0, done.stderr + done.stdout)
        payload = json.loads(done.stdout)
        self.assertTrue(payload["written"])
        data = json.loads(
            (self.gov / "agent-locks.json").read_text(encoding="utf-8"))
        self.assertTrue(
            data["file_locks"]["product/to_be_created.py"]["expected_new"])
        # Same-day triage record matches on existing_a but the lock also
        # carries to_be_created → mismatch WARN disclosed on stderr.
        self.assertIn("WARN", done.stderr)
        self.assertIn("product/to_be_created.py", done.stderr)


if __name__ == "__main__":
    unittest.main()
