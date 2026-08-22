"""Unit tests for task_priority.py — FIX-226 (0.71.0).

These tests are the load-bearing verification for the task dependency / priority
analysis tool. The single most important properties proven here:

  - **Parse correctness** — a sample plan-tracker priority table parses to the
    correct ``TaskDep`` list (ID, priority, status, dependencies, version).
  - **Task-family vs cross-entity** — RISK-/DEC-/REVIEW- refs in the ``依赖``
    cell are NOT counted as blocking dependencies (FIX-171 precedent). Only
    task-family IDs (FIX/REL/AUDIT/REQ/...) block.
  - **Status semantics** — ✅ = completed; any other emoji (⏳/🔴/🚧/⛔/⏸) =
    active, and active tasks block their dependents.
  - **Third-class status filter** — only ⏳ (pending) rows and rows WITHOUT a
    leading status marker may enter Unblocked / Recommended next; ⛔/⏸/🔴/🚧
    terminal rows are excluded even when dependency-satisfied (FIX-237.2 /
    ADR-017 §4.4 P1-3).
  - **Unblocked** — a not-completed task whose ALL task-family deps are
    completed (or which has none) is unblocked / ready to work.
  - **Blocked** — a not-completed task with ≥1 incomplete task-family dep is
    blocked, and the report lists the specific blocking deps.
  - **Recommended next** — the highest-priority unblocked task, tie-broken by
    target version then task ID, is the top pick.
  - **Cycle detection** — a dependency cycle (A→B→A) is detected and reported
    without infinite-looping; the report still produces best-effort analysis.
    A cycle is a WARNING (``cycle_warning`` flag + WARN banner), never an
    ERROR exit (FIX-237.2 cycle tolerance).
  - **Robustness** — the parser survives the malformed real-world rows:
    duplicated leading ``**P0**`` cells, free-prose 闭环路径 cells containing
    literal ``|``, ``—`` empty deps, and blank lines inside a table.

ALL tests use in-memory fixture strings — the real ``.governance/`` is NEVER
touched. The pure-module contract (no file I/O in compute) is what makes this
possible.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_task_priority.py -v
"""

import os
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

# Make the infra/ directory importable when run standalone or via pytest.
_INFRA = Path(__file__).resolve().parent.parent
if str(_INFRA) not in sys.path:
    sys.path.insert(0, str(_INFRA))

from task_priority import (  # noqa: E402  (import after sys.path setup)
    BlockedTask,
    PriorityReport,
    TaskDep,
    _MAX_ROOT_WALK_DEPTH,
    _ROOT_KIND_CYCLE,
    _is_task_family_id,
    _version_tuple,
    _walk_blocker_roots,
    compute_unblocked_tasks,
    format_report,
    parse_task_dependencies,
)


# ─── Fixture: a compact priority table exercising every interesting case ──────
#
# Layout (7-col, matches the live plan-tracker header):
#   | 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
#
# Cases covered (IDs use realistic PREFIX-NNN shape so the bare-ID regex matches):
#   FIX-101 DONE-A   : ✅ completed, no deps                  → completed
#   FIX-102 DONE-B   : ✅ completed, depended-on by READY     → completed (unblocks READY)
#   FIX-103 READY    : ⏳ pending, single dep on DONE-B (✅)   → unblocked (dep satisfied)
#   FIX-104 NODEPS   : ⏳ pending, — deps                     → unblocked (no deps)
#   FIX-105 BLOCKER  : 🔴 blocked-marker row (no task deps itself) → NOT
#                                              unblocked (third-class status filter: 🔴 leading marker
#                                              = non-executable candidate, ADR-017 §4.4 P1-3). Still
#                                              acts as a blocking SOURCE for FIX-106/FIX-109.
#   FIX-106 READY2   : ⏳ pending, dep on FIX-105 (🔴)        → blocked (FIX-105 not completed)
#   FIX-107 XENTITY  : ⏳ pending, ONLY cross-entity refs      → unblocked (cross-entity never blocks)
#   FIX-108 MIXED    : ⏳ pending, one ✅ task dep + RISK ref   → unblocked (task dep done, RISK ignored)
#   FIX-109 MIXEDBLK : ⏳ pending, one 🔴 task dep + RISK ref   → blocked (by FIX-105 only)
_SAMPLE_TABLE = """\
# Plan Tracker

Some prose preamble that is not a table.

### 优先级一览

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| **P1** | FIX-101 | done task no deps | — | 0.1.0 | closed | ✅ 完成 (2026-01-01) |
| **P0** | FIX-102 | done task depended on | — | 0.1.0 | closed | ✅ 已交付 |

| **P0** | FIX-103 | pending single completed dep | FIX-102✅ | 0.2.0 | open | ⏳ 待执行 |
| **P2** | FIX-104 | pending no deps | — | 0.3.0 | open | ⏳ 待执行 |
| **P2** | FIX-105 | active blocking source | — | 0.2.0 | open | 🔴 阻塞 |
| **P1** | FIX-106 | pending dep on active task | FIX-105 | 0.2.0 | open | ⏳ 待执行 |
| **P1** | FIX-107 | only cross-entity refs | RISK-039, DEC-090 | 0.4.0 | open | ⏳ 待执行 |
| **P2** | FIX-108 | done task dep + risk ref | FIX-102✅, RISK-039 | 0.4.0 | open | ⏳ 待执行 |
| **P2** | FIX-109 | active task dep + risk ref | FIX-105, RISK-039 | 0.4.0 | open | ⏳ 待执行 |

### 其他章节

Not a table anymore.
"""

# Human-readable aliases for the fixture task IDs (for test readability).
_DONE_A = "FIX-101"
_DONE_B = "FIX-102"
_READY = "FIX-103"
_NODEPS = "FIX-104"
_PEND_DEP = "FIX-105"
_READY2 = "FIX-106"
_XENTITY = "FIX-107"
_MIXED = "FIX-108"
_MIXEDBLK = "FIX-109"


class TestParseTaskDependencies(unittest.TestCase):
    """parse_task_dependencies — table → list[TaskDep]."""

    def test_parse_returns_one_task_per_data_row(self):
        tasks = parse_task_dependencies(_SAMPLE_TABLE)
        ids = {t.task_id for t in tasks}
        self.assertEqual(ids, {
            "FIX-101", "FIX-102", "FIX-103", "FIX-104", "FIX-105",
            "FIX-106", "FIX-107", "FIX-108", "FIX-109",
        })

    def test_parse_priority_strips_markdown_bold(self):
        tasks = {t.task_id: t for t in parse_task_dependencies(_SAMPLE_TABLE)}
        self.assertEqual(tasks["FIX-101"].priority, "P1")
        self.assertEqual(tasks["FIX-102"].priority, "P0")
        self.assertEqual(tasks["FIX-104"].priority, "P2")

    def test_parse_status_preserved_raw(self):
        tasks = {t.task_id: t for t in parse_task_dependencies(_SAMPLE_TABLE)}
        # Status is the raw cell — interpretation is via is_completed().
        self.assertIn("✅", tasks["FIX-101"].status)
        self.assertIn("⏳", tasks["FIX-103"].status)
        self.assertIn("🔴", tasks["FIX-105"].status)

    def test_parse_target_version_extracted(self):
        tasks = {t.task_id: t for t in parse_task_dependencies(_SAMPLE_TABLE)}
        self.assertEqual(tasks["FIX-101"].target_version, "0.1.0")
        self.assertEqual(tasks["FIX-103"].target_version, "0.2.0")

    def test_parse_dependencies_split_by_comma(self):
        tasks = {t.task_id: t for t in parse_task_dependencies(_SAMPLE_TABLE)}
        # FIX-102✅ — the trailing ✅ marker is stripped, leaving DONE-B.
        self.assertEqual(tasks["FIX-103"].dependencies, ("FIX-102",))
        # Multiple task-family deps.
        self.assertEqual(tasks["FIX-108"].dependencies, ("FIX-102",))

    def test_parse_em_dash_means_no_deps(self):
        tasks = {t.task_id: t for t in parse_task_dependencies(_SAMPLE_TABLE)}
        self.assertEqual(tasks["FIX-104"].dependencies, ())
        self.assertEqual(tasks["FIX-101"].dependencies, ())

    def test_parse_blank_lines_inside_table_are_tolerated(self):
        # The sample has a blank line between DONE-B and READY; both must parse.
        tasks = parse_task_dependencies(_SAMPLE_TABLE)
        ids = {t.task_id for t in tasks}
        self.assertIn("FIX-102", ids)
        self.assertIn("FIX-103", ids)

    def test_parse_ignores_non_table_prose(self):
        # The "Some prose preamble" line and "Not a table anymore." must NOT
        # produce tasks, and must not crash the parser.
        tasks = parse_task_dependencies(_SAMPLE_TABLE)
        for t in tasks:
            self.assertRegex(t.task_id, r"^[A-Z]+-\d+$|^[A-Z]+$")


class TestTaskFamilyClassification(unittest.TestCase):
    """_is_task_family_id — FIX-171 precedent (mirrored from archive.py)."""

    def test_task_family_prefixes_classify_true(self):
        for tid in ("FIX-226", "REL-063", "AUDIT-141", "REQ-082", "SYSGAP-047",
                    "FEAT-002", "VAL-008", "DOC-001", "TD-014", "MAINT-003",
                    "DESIGN-001", "DIAG-005", "FMT-002", "CLEANUP-001"):
            self.assertTrue(_is_task_family_id(tid), f"{tid} should be task-family")

    def test_cross_entity_prefixes_classify_false(self):
        for tid in ("RISK-039", "DEC-090", "REVIEW-FIX-155", "EVD-630",
                    "TIER-001", "CONSTRAINT-001", "TOOL-001", "ADR-009"):
            self.assertFalse(_is_task_family_id(tid), f"{tid} should be cross-entity")

    def test_review_prefixed_ref_does_not_leak_inner_task_id(self):
        # REVIEW-FIX-155 is a single cross-entity record; the parser must NOT
        # extract "FIX-155" from it as a task-family dependency. This is the
        # load-bearing regex fix (negative lookbehind for [-A-Z]).
        tf, ce = _parse_deps_helper("REVIEW-FIX-155, REVIEW-REL-047")
        self.assertNotIn("FIX-155", tf)
        self.assertNotIn("REL-047", tf)
        # Critically: neither the inner task ID nor the REVIEW token blocks.
        for blocking in (*tf, *ce):
            self.assertNotIn("FIX-155", blocking)
            self.assertNotIn("REL-047", blocking)


def _parse_deps_helper(cell):
    """Tiny helper: run the private dependency-cell parser, return (tf, ce)."""
    from task_priority import _parse_dependency_cell
    return _parse_dependency_cell(cell)


class TestStatusSemantics(unittest.TestCase):
    """✅ = completed; everything else = active."""

    def test_checkmark_emoji_is_completed(self):
        tasks = {t.task_id: t for t in parse_task_dependencies(_SAMPLE_TABLE)}
        self.assertTrue(tasks["FIX-101"].is_completed())
        self.assertTrue(tasks["FIX-102"].is_completed())

    def test_pending_emoji_is_active(self):
        tasks = {t.task_id: t for t in parse_task_dependencies(_SAMPLE_TABLE)}
        self.assertFalse(tasks["FIX-103"].is_completed())
        self.assertFalse(tasks["FIX-104"].is_completed())

    def test_blocked_emoji_is_active(self):
        tasks = {t.task_id: t for t in parse_task_dependencies(_SAMPLE_TABLE)}
        # 🔴 = blocked status → active (not done).
        self.assertFalse(tasks["FIX-105"].is_completed())


class TestComputeUnblocked(unittest.TestCase):
    """compute_unblocked_tasks — DAG classification."""

    def setUp(self):
        self.tasks = parse_task_dependencies(_SAMPLE_TABLE)
        self.by_id = {t.task_id: t for t in self.tasks}
        self.report = compute_unblocked_tasks(self.tasks)

    def test_completed_classification(self):
        completed_ids = {t.task_id for t in self.report.completed}
        self.assertEqual(completed_ids, {"FIX-101", "FIX-102"})

    def test_unblocked_includes_no_deps_and_satisfied_deps(self):
        unblocked_ids = {t.task_id for t in self.report.unblocked}
        # Unblocked (not completed + all task-family deps satisfied or none
        # + status candidate-eligible):
        #   FIX-103 (dep FIX-102 ✅), FIX-104 (no deps), FIX-107 (only
        #     cross-entity refs), FIX-108 (FIX-102 ✅ + RISK ignored).
        # FIX-105 (🔴) is NOT unblocked — the third-class status filter
        # excludes it even though its dependencies are satisfied.
        self.assertEqual(unblocked_ids, {"FIX-103", "FIX-104", "FIX-107", "FIX-108"})

    def test_blocked_lists_specific_blocking_deps(self):
        blocked_by_id = {bt.task.task_id: bt for bt in self.report.blocked}
        # READY2 blocked by FIX-105 (🔴 active) only.
        self.assertIn("FIX-106", blocked_by_id)
        self.assertEqual(set(blocked_by_id["FIX-106"].blocking_dependencies), {"FIX-105"})
        # MIXEDBLK blocked by FIX-105 (the task-family dep); RISK-039 NOT a blocker.
        self.assertIn("FIX-109", blocked_by_id)
        self.assertEqual(set(blocked_by_id["FIX-109"].blocking_dependencies), {"FIX-105"})
        self.assertNotIn("RISK-039", blocked_by_id["FIX-109"].blocking_dependencies)

    def test_cross_entity_refs_do_not_block(self):
        # XENTITY depends ONLY on RISK-039 + DEC-090 → unblocked (not blocked).
        unblocked_ids = {t.task_id for t in self.report.unblocked}
        blocked_ids = {bt.task.task_id for bt in self.report.blocked}
        self.assertIn("FIX-107", unblocked_ids)
        self.assertNotIn("FIX-107", blocked_ids)

    def test_total_count(self):
        self.assertEqual(self.report.total, 9)

    def test_no_cycles_in_acyclic_fixture(self):
        self.assertEqual(self.report.cycles, [])

    def test_dependency_graph_built(self):
        # Graph maps task_id → its task-family dependency tuple.
        g = self.report.dependency_graph
        self.assertEqual(set(g["FIX-103"]), {"FIX-102"})
        self.assertEqual(set(g["FIX-104"]), set())
        # Cross-entity refs are NOT in the graph (only task-family).
        self.assertNotIn("RISK-039", g["FIX-107"])
        self.assertEqual(g["FIX-107"], ())


class TestRecommendedNext(unittest.TestCase):
    """recommended_next — priority then version then ID ordering."""

    def test_recommended_next_sorted_by_priority(self):
        report = compute_unblocked_tasks(parse_task_dependencies(_SAMPLE_TABLE))
        # Unblocked set: FIX-103(P0,0.2.0), FIX-104(P2,0.3.0),
        #                FIX-107(P1,0.4.0), FIX-108(P2,0.4.0).
        # FIX-105 (🔴) is filtered out by the third-class status filter.
        # Sorted by priority then version: P0→FIX-103; P1→FIX-107;
        #   P2→FIX-104(0.3.0) < FIX-108(0.4.0).
        ids = [t.task_id for t in report.recommended_next]
        self.assertEqual(ids, ["FIX-103", "FIX-107", "FIX-104", "FIX-108"])

    def test_top_pick_is_first(self):
        report = compute_unblocked_tasks(parse_task_dependencies(_SAMPLE_TABLE))
        self.assertEqual(report.recommended_next[0].task_id, "FIX-103")

    def test_recommended_next_excludes_completed_and_blocked(self):
        report = compute_unblocked_tasks(parse_task_dependencies(_SAMPLE_TABLE))
        ids = {t.task_id for t in report.recommended_next}
        # Completed tasks are not recommended.
        self.assertNotIn("FIX-101", ids)
        self.assertNotIn("FIX-102", ids)
        # Blocked tasks are not recommended.
        self.assertNotIn("FIX-106", ids)
        self.assertNotIn("FIX-109", ids)

    def test_priority_p0_beats_p1_beats_p2(self):
        # Direct unit test of the sort key across priorities.
        p0 = TaskDep("A", "P0", "⏳", (), (), "0.1.0")
        p1 = TaskDep("B", "P1", "⏳", (), (), "0.1.0")
        p2 = TaskDep("C", "P2", "⏳", (), (), "0.1.0")
        report = compute_unblocked_tasks([p0, p1, p2])
        ids = [t.task_id for t in report.recommended_next]
        self.assertEqual(ids, ["A", "B", "C"])

    def test_version_tiebreak_within_same_priority(self):
        # Same priority P0; lower version first.
        v_later = TaskDep("A", "P0", "⏳", (), (), "0.5.0")
        v_earlier = TaskDep("B", "P0", "⏳", (), (), "0.2.0")
        report = compute_unblocked_tasks([v_later, v_earlier])
        ids = [t.task_id for t in report.recommended_next]
        self.assertEqual(ids, ["B", "A"])

    def test_no_priority_sorts_last(self):
        # P9 (no priority / —) must sort after real P0/P1/P2.
        p9 = TaskDep("Z", "P9", "⏳", (), (), "0.1.0")
        p2 = TaskDep("A", "P2", "⏳", (), (), "0.1.0")
        report = compute_unblocked_tasks([p9, p2])
        ids = [t.task_id for t in report.recommended_next]
        self.assertEqual(ids, ["A", "Z"])


class TestEmptyAndSatisfiedDeps(unittest.TestCase):
    """Spec-named cases: empty deps → unblocked; dep on completed → unblocked."""

    def test_empty_deps_em_dash_is_unblocked(self):
        tasks = parse_task_dependencies(_SAMPLE_TABLE)
        report = compute_unblocked_tasks(tasks)
        unblocked_ids = {t.task_id for t in report.unblocked}
        self.assertIn("FIX-104", unblocked_ids)  # deps = —

    def test_dep_on_completed_task_is_unblocked(self):
        tasks = parse_task_dependencies(_SAMPLE_TABLE)
        report = compute_unblocked_tasks(tasks)
        unblocked_ids = {t.task_id for t in report.unblocked}
        self.assertIn("FIX-103", unblocked_ids)  # dep DONE-B is ✅

    def test_dep_on_pending_task_is_blocked(self):
        tasks = parse_task_dependencies(_SAMPLE_TABLE)
        report = compute_unblocked_tasks(tasks)
        blocked_ids = {bt.task.task_id for bt in report.blocked}
        self.assertIn("FIX-106", blocked_ids)  # dep FIX-105 is 🔴

    def test_dep_on_unknown_task_family_id_blocks_fail_closed(self):
        # A task-family dep that is MISSING from the table cannot be proven
        # complete → it blocks (fail-closed, FIX-171 conservative default).
        t = TaskDep("CHILD", "P0", "⏳", ("MISSING-FIX",), (), "0.1.0")
        report = compute_unblocked_tasks([t])
        self.assertEqual(len(report.blocked), 1)
        self.assertEqual(report.blocked[0].blocking_dependencies, ("MISSING-FIX",))
        self.assertEqual(report.unblocked, [])

    def test_empty_input_yields_empty_report(self):
        report = compute_unblocked_tasks([])
        self.assertEqual(report.total, 0)
        self.assertEqual(report.completed, [])
        self.assertEqual(report.unblocked, [])
        self.assertEqual(report.blocked, [])
        self.assertEqual(report.recommended_next, [])
        self.assertEqual(report.cycles, [])


class TestCycleDetection(unittest.TestCase):
    """Cycle detection — A→B→A must be reported, not infinite-loop."""

    def test_simple_two_node_cycle_detected(self):
        a = TaskDep("FIX-A", "P0", "⏳", ("FIX-B",), (), "0.1.0")
        b = TaskDep("FIX-B", "P0", "⏳", ("FIX-A",), (), "0.1.0")
        report = compute_unblocked_tasks([a, b])
        self.assertTrue(len(report.cycles) >= 1, "at least one cycle must be detected")
        # The cycle must close back to its start node.
        joined = " ".join(" ".join(c) for c in report.cycles)
        self.assertIn("FIX-A", joined)
        self.assertIn("FIX-B", joined)

    def test_three_node_cycle_detected(self):
        a = TaskDep("A", "P0", "⏳", ("B",), (), "0.1.0")
        b = TaskDep("B", "P0", "⏳", ("C",), (), "0.1.0")
        c = TaskDep("C", "P0", "⏳", ("A",), (), "0.1.0")
        report = compute_unblocked_tasks([a, b, c])
        self.assertTrue(len(report.cycles) >= 1)

    def test_self_dependency_is_a_cycle(self):
        # A task that depends on itself is a 1-cycle.
        a = TaskDep("A", "P0", "⏳", ("A",), (), "0.1.0")
        report = compute_unblocked_tasks([a])
        self.assertTrue(any("A" in cycle for cycle in report.cycles))

    def test_cycle_does_not_infinite_loop(self):
        # The load-bearing safety property: cycle detection terminates.
        a = TaskDep("A", "P0", "⏳", ("B",), (), "0.1.0")
        b = TaskDep("B", "P0", "⏳", ("C",), (), "0.1.0")
        c = TaskDep("C", "P0", "⏳", ("A",), (), "0.1.0")
        # If this returns at all, the DFS terminated (no infinite loop).
        report = compute_unblocked_tasks([a, b, c])
        self.assertIsInstance(report, PriorityReport)

    def test_acyclic_graph_has_no_cycles(self):
        a = TaskDep("A", "P0", "⏳", (), (), "0.1.0")
        b = TaskDep("B", "P0", "⏳", ("A",), (), "0.1.0")
        c = TaskDep("C", "P0", "⏳", ("B",), (), "0.1.0")
        report = compute_unblocked_tasks([a, b, c])
        self.assertEqual(report.cycles, [])


class TestParserRobustness(unittest.TestCase):
    """Robustness against real plan-tracker malformations."""

    def test_duplicated_leading_priority_cell(self):
        # Live lines 174-176 have | **P0** | **P0** | FIX-222 | ... |
        table = """\
| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| **P0** | **P0** | FIX-222 | dup priority row | AUDIT-139✅ | 0.71.0 | some closure | ✅ 完成 (2026-07-26) | |
"""
        tasks = parse_task_dependencies(table)
        self.assertEqual(len(tasks), 1)
        t = tasks[0]
        self.assertEqual(t.task_id, "FIX-222")
        self.assertEqual(t.priority, "P0")
        self.assertEqual(t.dependencies, ("AUDIT-139",))
        self.assertEqual(t.target_version, "0.71.0")
        self.assertTrue(t.is_completed())

    def test_prose_closure_path_with_literal_pipe(self):
        # The 闭环路径 cell frequently contains unescaped | (e.g. "| RISK-" 行).
        # Status must still be read from the LAST cell, not shifted into prose.
        table = """\
| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| **P0** | FIX-176 | desc | DEC-090, RISK-039 | 未规划版本 | closure with | RISK- row inside it | ✅ 完成 (2026-07-05) |
"""
        tasks = parse_task_dependencies(table)
        self.assertEqual(len(tasks), 1)
        t = tasks[0]
        self.assertEqual(t.task_id, "FIX-176")
        # DEC-090 is cross-entity (DEC prefix) → NOT in dependencies.
        self.assertEqual(t.dependencies, ())
        self.assertIn("DEC-090", t.cross_entity_refs)
        self.assertIn("RISK-039", t.cross_entity_refs)
        # Status correctly read as completed despite the prose pipe.
        self.assertTrue(t.is_completed())

    def test_status_emoji_variants_all_completed(self):
        # ✅ 已交付 / ✅ 已发布 / ✅ 完成 / ✅ ACCEPTED all mean completed.
        for status in ("✅ 已交付", "✅ 已发布 (2026-07-25)", "✅ 完成 (2026-06-30)",
                       "✅ ACCEPTED / 0 blocker", "✅ 代码完成 (2026-07-24)"):
            table = (
                "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
                "|---|---|---|---|---|---|---|\n"
                f"| **P0** | T-001 | x | — | 0.1.0 | c | {status} |\n"
            )
            tasks = parse_task_dependencies(table)
            self.assertTrue(tasks[0].is_completed(), f"status {status!r} should be completed")

    def test_active_emoji_variants_all_active(self):
        for status in ("⏳ 待执行", "🔴 blocked", "🚧 in progress", "⛔ BLOCKED",
                       "⏸ paused", "⏸ SPLIT_TO FIX-199/FIX-200"):
            table = (
                "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
                "|---|---|---|---|---|---|---|\n"
                f"| **P0** | T-001 | x | — | 0.1.0 | c | {status} |\n"
            )
            tasks = parse_task_dependencies(table)
            self.assertFalse(tasks[0].is_completed(), f"status {status!r} should be active")

    def test_dependency_cell_with_glued_checkmark(self):
        # "FIX-155✅, FIX-156✅" — the ✅ is a dep-state hint glued to the ID.
        tf, ce = _parse_deps_helper("FIX-155✅, FIX-156✅, RISK-039")
        self.assertEqual(tf, ("FIX-155", "FIX-156"))
        self.assertEqual(ce, ("RISK-039",))

    def test_dependency_cell_with_prose_around_ids(self):
        # Real cells embed IDs in prose: "DEC-085/086/087(授权沿用)".
        tf, ce = _parse_deps_helper("DEC-088, DEC-085/086/087(授权沿用), RISK-039")
        # DEC-088 is captured; the /086/087 bare numbers are not (no PREFIX-).
        self.assertIn("DEC-088", ce)
        self.assertIn("DEC-085", ce)
        self.assertIn("RISK-039", ce)
        self.assertEqual(tf, ())

    def test_multiple_priority_tables_are_both_parsed(self):
        # The live plan-tracker has two priority tables (优先级一览 + 已归档版本).
        table = """\
### 优先级一览

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| **P0** | FIX-100 | active | — | 0.1.0 | c | ⏳ 待执行 |

### 已归档版本 task

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| — | FIX-082 | archived | AUDIT-102 | 0.38.0 | c | ✅ 已交付 |
"""
        tasks = parse_task_dependencies(table)
        ids = {t.task_id for t in tasks}
        self.assertEqual(ids, {"FIX-100", "FIX-082"})

    def test_duplicate_task_id_keeps_first_occurrence(self):
        # Same ID appearing twice → first occurrence wins (de-duplication).
        table = """\
| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| **P0** | FIX-500 | first | — | 0.1.0 | c | ⏳ 待执行 |
| **P0** | FIX-500 | second | — | 0.9.0 | c | ✅ 完成 |
"""
        tasks = parse_task_dependencies(table)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].target_version, "0.1.0")
        self.assertFalse(tasks[0].is_completed())


# ─── Fixture: headerless 「最近完成」 sub-section table (FIX-251) ─────────────
#
# The live plan-tracker's ``### 最近完成（本会话提交窗口）`` sub-section
# (plan-tracker.md L217-224) is a 优先级|ID|事项|依赖|目标版本|闭环路径|状态 task
# table WITHOUT a header row and WITHOUT a separator row — the first ``|``
# line directly after the heading is already a data row. FIX-251: the parser
# must recognize this shape so the window's task IDs (FIX-244~249, REL-067)
# are visible to dependency analysis (previously change-triage reported them
# as unknown-dep fail-closed).
#
# FIX-252 F1 (Reviewer P3-1): the fixture was completed from 3/7 to the full
# 7-row live window, aligned to live order (FIX-244/245/246/REL-067/247/248/249,
# REL-067 in the middle at position 4 — NOT last) and live fields.
_SAMPLE_RECENT_WINDOW_TABLE = """\
# Plan Tracker

Some prose preamble.

### 最近完成（本会话提交窗口）

| **P2** | FIX-244 | archive --project-root fail-closed 校验 | FIX-242, FIX-243 | 未规划版本 | product code | ✅ 完成 (2026-08-06) |
| **P2** | FIX-245 | verify_workflow --project-root fail-closed 对齐 | FIX-187, FIX-244 | 未规划版本 | product code | ✅ 完成 (2026-08-06) |
| **P2** | FIX-246 | FIX-242/244/245 遗留观察项清理 | FIX-242, FIX-244, FIX-245 | 未规划版本 | product code | ✅ 完成 (2026-08-07) |

| **P1** | REL-067 | 发布 0.74.0——五修复链打包 | FIX-242✅, FIX-243✅, FIX-244✅, FIX-245✅, FIX-246✅ | 0.74.0 | release mgmt | ✅ 已发布 (2026-08-13) |
| **P2** | FIX-247 | 观察项债务包——FIX-237/238 遗留处置 | FIX-237✅, FIX-238✅ | 未规划版本 | debt pack | ✅ 完成 (2026-08-16) |
| **P2** | FIX-248 | CLI 测试 fixture 版本对齐 | FIX-247✅ | 未规划版本 | debt pack | ✅ 完成 (2026-08-16) |
| **P2** | FIX-249 | 观察项债务包——FIX-247 R0 处置 | FIX-247✅, REVIEW-FIX-247-CODE-R0 | 未规划版本 | debt pack | ✅ 完成 (2026-08-16) |
> 历史提交窗口已归档。
"""


class TestHeaderlessRecentWindowTable(unittest.TestCase):
    """FIX-251 — headerless task sub-section (最近完成) must be parsed.

    The live plan-tracker's ``### 最近完成（本会话提交窗口）`` window is a full
    7-col task table that lacks the header row (``| 优先级 | ID | ... |``) and
    separator row. Before FIX-251 the parse state machine never entered
    ``in_table`` for it (only a ``| 优先级 | ID |`` header row triggers entry),
    so the window's task IDs were invisible to dependency analysis and
    change-triage reported unknown-dep on them fail-closed. These tests pin
    the headerless-shape recognition: a ``|`` row directly after a heading
    that carries a bare task ID cell AND a status cell is treated as a
    headerless task table with the column layout inferred from the canonical
    7-col shape.
    """

    def test_window_task_ids_are_parsed(self):
        tasks = parse_task_dependencies(_SAMPLE_RECENT_WINDOW_TABLE)
        ids = {t.task_id for t in tasks}
        self.assertEqual(ids, {
            "FIX-244", "FIX-245", "FIX-246", "REL-067",
            "FIX-247", "FIX-248", "FIX-249",
        })

    def test_window_fields_are_correct(self):
        tasks = {t.task_id: t for t in parse_task_dependencies(_SAMPLE_RECENT_WINDOW_TABLE)}
        t244 = tasks["FIX-244"]
        self.assertEqual(t244.priority, "P2")
        self.assertEqual(t244.dependencies, ("FIX-242", "FIX-243"))
        self.assertEqual(t244.target_version, "未规划版本")
        self.assertTrue(t244.is_completed())

        t245 = tasks["FIX-245"]
        self.assertEqual(t245.priority, "P2")
        self.assertEqual(t245.dependencies, ("FIX-187", "FIX-244"))
        self.assertTrue(t245.is_completed())

        t246 = tasks["FIX-246"]
        self.assertEqual(t246.priority, "P2")
        self.assertEqual(t246.dependencies, ("FIX-242", "FIX-244", "FIX-245"))
        self.assertTrue(t246.is_completed())

        rel = tasks["REL-067"]
        self.assertEqual(rel.priority, "P1")
        # ✅ glued to the dependency IDs is a dep-state hint — stripped, IDs kept.
        self.assertEqual(rel.dependencies,
                         ("FIX-242", "FIX-243", "FIX-244", "FIX-245", "FIX-246"))
        self.assertEqual(rel.target_version, "0.74.0")
        self.assertTrue(rel.is_completed())

        t247 = tasks["FIX-247"]
        self.assertEqual(t247.priority, "P2")
        self.assertEqual(t247.dependencies, ("FIX-237", "FIX-238"))
        self.assertTrue(t247.is_completed())

        t248 = tasks["FIX-248"]
        self.assertEqual(t248.priority, "P2")
        self.assertEqual(t248.dependencies, ("FIX-247",))
        self.assertTrue(t248.is_completed())

        t249 = tasks["FIX-249"]
        self.assertEqual(t249.priority, "P2")
        # REVIEW-FIX-247-CODE-R0 is a single cross-entity record — its inner
        # FIX-247 is NOT extracted (negative lookbehind blocks [-A-Z] before the
        # ID), so it contributes NO task dep and NO extractable ref token.
        self.assertEqual(t249.dependencies, ("FIX-247",))
        self.assertEqual(t249.cross_entity_refs, ())
        self.assertTrue(t249.is_completed())

    def test_window_table_ends_at_non_table_line(self):
        # The trailing "> 已归档" blockquote ends the headerless table; a
        # subsequent header-driven table (已归档版本 task pointer) parses
        # normally AFTER the window without leaking rows into it.
        table = _SAMPLE_RECENT_WINDOW_TABLE + """\
### 已归档版本 task

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| — | FIX-082 | archived pointer | AUDIT-102 | 0.38.0 | archive | ✅ 已交付 |
"""
        ids = {t.task_id for t in parse_task_dependencies(table)}
        self.assertEqual(ids, {
            "FIX-244", "FIX-245", "FIX-246", "REL-067",
            "FIX-247", "FIX-248", "FIX-249", "FIX-082",
        })
        self.assertEqual(len(parse_task_dependencies(table)), 8)

    def test_prose_between_heading_and_table_blocks_headerless_parse(self):
        # Guard for the 需求跟踪矩阵 class of false positive: a table that is
        # NOT directly after a heading (prose in between) must NOT be read as
        # a headerless task table — even when its rows carry REQ-* ID cells
        # (task-family prefix) and emoji status cells (📋 etc.).
        table = """\
# Plan Tracker

## 需求跟踪矩阵

需求跟踪回答"这个任务服务于哪个用户需求"——从立项的 PR/FAQ 到开发的 task 全程可追溯。

| 需求ID | 需求描述 | 来源 | 优先级 | 关联任务 | 当前状态 | 验证方式 |
|--------|---------|------|--------|---------|---------|---------|
| REQ-002 | 用户能在 5 分钟内完成初始化 | PR/FAQ: 新用户立即可用 | P0 | MAINT-012, AUDIT-003, FIX-001 | ⚠️ 部分 | 外部验证 |
| REQ-014 | Task-Gate 模型——plan-tracker 数据结构改造 | AUDIT-052 | P0 | AUDIT-057 | 📋 降级到 1.0.0 | — |
"""
        tasks = parse_task_dependencies(table)
        self.assertEqual(tasks, [])


class TestLiveCombinationOrder(unittest.TestCase):
    """FIX-252 F2 (Reviewer P3-2) — explicitly pin the LIVE real combination order.

    FIX-251 only locked the reverse order (window → blockquote → 标题 →
    已归档表). The live plan-tracker's actual order is the OTHER way round for
    the active window: a **header-driven** 优先级表 (``| 优先级 | ID | … |``) is
    followed by a ``###`` heading and then a **headerless** window table. This
    class locks that exact order so the state machine's transitions (header
    → heading arms ``after_heading`` → headerless recognition) cannot regress
    the coexistence of both tables' tasks.
    """

    _TABLE = """\
# Plan Tracker

### 优先级一览

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| **P0** | FIX-301 | header-driven active | — | 0.5.0 | open | ⏳ 待执行 |

### 最近完成（本会话提交窗口）

| **P2** | FIX-302 | headerless window completed | — | 未规划版本 | product | ✅ 完成 (2026-08-16) |
"""

    def test_header_table_then_heading_then_headerless_both_parsed(self):
        tasks = parse_task_dependencies(self._TABLE)
        ids = {t.task_id for t in tasks}
        # Both the header-driven table and the headerless window table must be
        # present (the live order, not just the reverse already locked).
        self.assertIn("FIX-301", ids)
        self.assertIn("FIX-302", ids)
        self.assertEqual(ids, {"FIX-301", "FIX-302"})

    def test_header_table_status_preserved_in_combination(self):
        tasks = {t.task_id: t for t in parse_task_dependencies(self._TABLE)}
        self.assertEqual(tasks["FIX-301"].priority, "P0")
        self.assertFalse(tasks["FIX-301"].is_completed())
        self.assertTrue(tasks["FIX-302"].is_completed())


class TestCoerceTextPathAmbiguity(unittest.TestCase):
    """FIX-252 O1 — ``_coerce_text`` str path / text ambiguity.

    Red-to-green root behavior: a caller who passes a **str-form path** to
    :func:`parse_task_dependencies` (e.g.
    ``parse_task_dependencies('D:\\\\...\\\\plan-tracker.md')``) previously got a
    silent ``total 0`` — the string was treated as document text, no table was
    found. These tests pin that (1) a str path to an existing ``.md`` file with
    a priority table now returns that table's tasks, (2) pure-text str input is
    unchanged (no regression on the existing text fixtures), (3) a str that
    looks like a path but names no existing file raises a clear error (rather
    than a silent 0), and (4) ``Path`` object input is unchanged.
    """

    def _write_temp_file(self, text, suffix=".md"):
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        self.addCleanup(lambda: os.remove(path))
        return path

    def test_str_path_to_existing_md_reads_task_table(self):
        # A str path (not a Path object) to an .md containing a priority table
        # must be READ as a file — previously returned total 0.
        path = self._write_temp_file(_SAMPLE_TABLE)
        tasks = parse_task_dependencies(str(Path(path)))
        ids = {t.task_id for t in tasks}
        self.assertIn("FIX-101", ids)  # red before fix: total 0 → empty set
        self.assertEqual(len(tasks), 9)

    def test_plain_text_str_input_unchanged(self):
        # Passing raw markdown text as str remains the text channel (existing
        # _SAMPLE_TABLE usage) — zero regression.
        tasks = parse_task_dependencies(_SAMPLE_TABLE)
        self.assertEqual(len(tasks), 9)

    def test_path_object_input_unchanged(self):
        # Path object input still reads the file — zero regression.
        path = self._write_temp_file(_SAMPLE_TABLE)
        tasks = parse_task_dependencies(Path(path))
        self.assertEqual(len(tasks), 9)

    def test_str_path_like_but_missing_file_raises_value_error(self):
        # A str that looks like a path (contains separator / ends .md) but does
        # not name an existing file must fail clearly, not silent total 0.
        missing = str(Path(tempfile.gettempdir()) / "no-such-plan-tracker-file.md")
        with self.assertRaises(ValueError):
            parse_task_dependencies(missing)

    def test_text_containing_forward_slash_not_treated_as_path(self):
        # Ordinary markdown text containing '/' (prose / table separators) must
        # NOT be mis-detected as a path — it stays the text channel.
        text = "## a/b path-like value but it is prose text\n\nnot a real file."
        tasks = parse_task_dependencies(text)
        self.assertEqual(tasks, [])

    def test_empty_string_is_text_not_path(self):
        # FIX-252 R0 P1-1: Path("") normalizes to Path("."), whose exists() is
        # True in a real cwd → the pre-guard heuristic mis-classified "" as a
        # path → open(".") raised IsADirectoryError/PermissionError. An empty
        # string must stay on the text channel and parse to [] (the pre-O1
        # behavior), not crash uncategorized.
        tasks = parse_task_dependencies("")
        self.assertEqual(tasks, [])

    def test_multiline_str_never_treated_as_path(self):
        # FIX-252 R0 P1-1: a real path can never contain "\n" — any multi-line
        # value is by definition document text. A multi-line str whose first
        # line carries a drive prefix / .md suffix must NOT raise a spurious
        # ValueError; it stays the text channel.
        text = "C:/x/y.md\nrest of the document"
        tasks = parse_task_dependencies(text)
        self.assertEqual(tasks, [])

    def test_single_line_md_suffix_with_separator_raises_documented_ambiguity(self):
        # FIX-252 R0 P3-3: pins the documented ambiguity — a SINGLE-line str
        # that ends in a document suffix and contains a path separator is
        # interpreted as a path (prefer path), and a missing file raises
        # ValueError (documented, not silent).
        missing = str(Path("nonexistent/nested/dir") / "doc.md")
        with self.assertRaises(ValueError):
            parse_task_dependencies(missing)


class TestFormatReport(unittest.TestCase):
    """format_report — markdown output shape."""

    def test_format_includes_summary_counts(self):
        report = compute_unblocked_tasks(parse_task_dependencies(_SAMPLE_TABLE))
        out = format_report(report)
        self.assertIn("Task Priority Analysis", out)
        self.assertIn("Total:", out)
        self.assertIn("completed", out)
        self.assertIn("unblocked", out)
        self.assertIn("blocked", out)

    def test_format_includes_recommended_next_section(self):
        report = compute_unblocked_tasks(parse_task_dependencies(_SAMPLE_TABLE))
        out = format_report(report)
        self.assertIn("Recommended next", out)
        self.assertIn("Top pick", out)
        # Top pick is FIX-103 (P0, dep FIX-102 satisfied).
        self.assertIn("`FIX-103`", out)

    def test_format_lists_blocked_with_blockers(self):
        report = compute_unblocked_tasks(parse_task_dependencies(_SAMPLE_TABLE))
        out = format_report(report)
        self.assertIn("Blocked", out)
        # FIX-106 is blocked by FIX-105 (the active task-family dep).
        self.assertIn("`FIX-106`", out)
        self.assertIn("FIX-105", out)  # the blocking dep shown

    def test_format_cycle_banner_when_cycles_present(self):
        a = TaskDep("FIX-A", "P0", "⏳", ("FIX-B",), (), "0.1.0")
        b = TaskDep("FIX-B", "P0", "⏳", ("FIX-A",), (), "0.1.0")
        report = compute_unblocked_tasks([a, b])
        out = format_report(report)
        self.assertIn("CYCLE", out)

    def test_format_no_cycle_banner_when_acyclic(self):
        report = compute_unblocked_tasks(parse_task_dependencies(_SAMPLE_TABLE))
        out = format_report(report)
        self.assertNotIn("CYCLE", out)

    def test_format_empty_report_does_not_crash(self):
        out = format_report(compute_unblocked_tasks([]))
        self.assertIn("Task Priority Analysis", out)
        self.assertIn("No unblocked tasks", out)


class TestVersionTuple(unittest.TestCase):
    """_version_tuple — sort-key helper."""

    def test_parse_semver(self):
        self.assertEqual(_version_tuple("0.71.0"), (0, 71, 0))

    def test_extract_from_parenthetical(self):
        # "0.66.2（暂定）" → (0, 66, 2)
        self.assertEqual(_version_tuple("0.66.2（暂定）"), (0, 66, 2))

    def test_em_dash_sorts_last(self):
        em = _version_tuple("—")
        real = _version_tuple("0.1.0")
        self.assertGreater(em, real)

    def test_unversioned_sorts_last(self):
        unv = _version_tuple("未规划版本")
        real = _version_tuple("0.1.0")
        self.assertGreater(unv, real)


class TestPurityContract(unittest.TestCase):
    """The compute path must hold no module-level mutable state."""

    def test_repeated_calls_are_deterministic(self):
        t1 = parse_task_dependencies(_SAMPLE_TABLE)
        r1 = compute_unblocked_tasks(t1)
        t2 = parse_task_dependencies(_SAMPLE_TABLE)
        r2 = compute_unblocked_tasks(t2)
        self.assertEqual([t.task_id for t in r1.recommended_next],
                         [t.task_id for t in r2.recommended_next])
        self.assertEqual(r1.total, r2.total)

    def test_module_imports_only_stdlib(self):
        # Inspect the module's globals — every loaded module must be stdlib.
        import task_priority as tp
        allowed = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()
        # Always-allowed: the module itself + dataclasses (stdlib).
        allowed |= {"task_priority", "dataclasses", "re", "unicodedata"}
        # What matters: no third-party imports sneaked in. Walk sys.modules
        # entries the module pulled in via its own imports (best-effort).
        for name in ("re", "unicodedata", "dataclasses"):
            self.assertIn(name, sys.modules)


# ─── Fixture: third-class status filter named cases (FIX-237.2 / ADR-017) ────
#
# Every non-control row has NO dependencies (—) so the ONLY reason it is not
# unblocked is the third-class status filter: rows whose status leading marker
# is ⛔/⏸/🔴/🚧 are non-executable candidates even when dependency-satisfied.
# Named cases mirror the live plan-tracker rows that previously polluted the
# Unblocked list (AUDIT-142 diagnosis R0 实测, ADR-017 §4.4 P1-3):
#   SYSGAP-046 (🚧 historical in-progress terminal), FIX-197 (⏸ SPLIT_TO),
#   REL-058 (⛔ BLOCKED), AUDIT-136 (⛔ BLOCKED_REVIEW_FUSE),
#   FIX-203 (⛔ BLOCKED_PERFORMANCE), FIX-105 (🔴 blocked).
# Controls: FIX-777 (⏳ pending → eligible), FIX-778 (✅ completed → excluded
# via _status_is_completed, never reaches the candidate filter).
_NON_EXECUTABLE_TABLE = """\
# Non-executable status fixtures

### 优先级一览

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| **P1** | SYSGAP-046 | historical in-progress terminal (named case) | — | 0.65.3 | closed | 🚧 前向门禁完成，历史处置待 DEC (2026-07-11) |
| **P0** | FIX-197 | split/held terminal (named case) | — | 0.66.1 | closed | ⏸ SPLIT_TO FIX-199/FIX-200 (2026-07-13) |
| **P0** | REL-058 | blocked release incident (named case) | — | 0.66.1 | closed | ⛔ BLOCKED — release incident (2026-07-17) |
| **P0** | AUDIT-136 | blocked review fuse (named case) | — | 0.66.2（暂定） | closed | ⛔ BLOCKED_REVIEW_FUSE——已拆分至 AUDIT-137/138 |
| **P1** | FIX-203 | blocked performance terminal | — | 0.66.1 | closed | ⛔ BLOCKED_PERFORMANCE |
| **P2** | FIX-105 | 🔴 blocked-marker row | — | 0.2.0 | open | 🔴 阻塞 |
| **P0** | FIX-777 | pending control row | — | 0.3.0 | open | ⏳ 待执行 |
| **P2** | FIX-778 | completed control row | — | 0.1.0 | closed | ✅ 完成 (2026-01-01) |
"""


class TestThirdClassStatusFilter(unittest.TestCase):
    """Third-class status filter — ⛔/⏸/🔴/🚧 rows never enter unblocked / next.

    FIX-237.2 / ADR-017 §4.4 P1-3: dependency satisfaction alone no longer
    makes a row an executable candidate. The status leading marker must be ⏳
    (pending/active) or absent (unmarked plain-text status). Terminal /
    non-executable markers (⛔ blocked, ⏸ split/held, 🔴 blocked, 🚧 historical
    in-progress) are excluded even when dependency-satisfied.
    """

    def setUp(self):
        self.tasks = parse_task_dependencies(_NON_EXECUTABLE_TABLE)
        self.report = compute_unblocked_tasks(self.tasks)
        self.unblocked_ids = {t.task_id for t in self.report.unblocked}
        self.recommended_ids = [t.task_id for t in self.report.recommended_next]
        self.excluded_ids = {t.task_id for t in self.report.non_executable}
        self.completed_ids = {t.task_id for t in self.report.completed}

    def test_named_non_executable_rows_excluded_from_unblocked(self):
        for tid in ("SYSGAP-046", "FIX-197", "REL-058", "AUDIT-136", "FIX-203", "FIX-105"):
            self.assertNotIn(tid, self.unblocked_ids, f"{tid} must not be unblocked")

    def test_named_non_executable_rows_excluded_from_recommended(self):
        for tid in ("SYSGAP-046", "FIX-197", "REL-058", "AUDIT-136", "FIX-203", "FIX-105"):
            self.assertNotIn(tid, self.recommended_ids, f"{tid} must not be recommended")

    def test_only_pending_control_is_unblocked(self):
        self.assertEqual(self.unblocked_ids, {"FIX-777"})
        self.assertEqual(self.recommended_ids, ["FIX-777"])

    def test_non_executable_bucket_reports_excluded_rows(self):
        self.assertEqual(self.excluded_ids, {"SYSGAP-046", "FIX-197", "REL-058", "AUDIT-136", "FIX-203", "FIX-105"})

    def test_pending_row_still_eligible(self):
        self.assertIn("FIX-777", self.unblocked_ids)
        self.assertIn("FIX-777", self.recommended_ids)

    def test_completed_row_still_excluded_by_is_completed(self):
        self.assertIn("FIX-778", self.completed_ids)
        self.assertNotIn("FIX-778", self.unblocked_ids)
        self.assertNotIn("FIX-778", self.recommended_ids)
        self.assertNotIn("FIX-778", self.excluded_ids)

    def test_unmarked_plain_status_is_eligible(self):
        # A status cell with no leading emoji marker (plain text) is eligible.
        t = TaskDep("FIX-780", "P0", "待执行", (), (), "0.1.0")
        report = compute_unblocked_tasks([t])
        self.assertEqual([x.task_id for x in report.unblocked], ["FIX-780"])
        self.assertEqual(report.non_executable, [])
        self.assertEqual(report.recommended_next[0].task_id, "FIX-780")

    def test_marked_blocked_row_with_blocking_deps_remains_blocked(self):
        # A ⛔ row whose task-family dep is unknown cannot be proven complete →
        # it stays in the Blocked list (dependency fact); blocked takes
        # precedence over the non-executable bucket.
        t = TaskDep("REL-900", "P0", "⛔ BLOCKED_BY FIX-999", ("FIX-999",), (), "0.1.0")
        report = compute_unblocked_tasks([t])
        self.assertEqual(len(report.blocked), 1)
        self.assertEqual(report.blocked[0].task.task_id, "REL-900")
        self.assertEqual(report.non_executable, [])
        self.assertEqual(report.unblocked, [])

    def test_clipboard_queued_marker_is_non_candidate(self):
        # 📋 待启动 (queued-not-executable) — a leading marker that is not ⏳
        # is non-candidate even with no dependencies (FIX-237.3 P3-2).
        t = TaskDep("FIX-781", "P0", "📋 待启动", (), (), "0.1.0")
        report = compute_unblocked_tasks([t])
        self.assertEqual([x.task_id for x in report.non_executable], ["FIX-781"])
        self.assertEqual(report.unblocked, [])

    def test_stop_marker_is_non_candidate(self):
        # 🛑 stopped — a leading marker that is not ⏳ is non-candidate
        # (FIX-237.3 P3-2).
        t = TaskDep("FIX-782", "P0", "🛑 停止", (), (), "0.1.0")
        report = compute_unblocked_tasks([t])
        self.assertEqual([x.task_id for x in report.non_executable], ["FIX-782"])
        self.assertEqual(report.unblocked, [])

    def test_empty_status_cell_is_eligible(self):
        # Empty status cell → no leading marker → eligible (dependency
        # analysis decides; FIX-237.3 P3-2).
        t = TaskDep("FIX-783", "P0", "", (), (), "0.1.0")
        report = compute_unblocked_tasks([t])
        self.assertEqual([x.task_id for x in report.unblocked], ["FIX-783"])
        self.assertEqual(report.non_executable, [])

    def test_format_excluded_section_lists_filtered_rows(self):
        out = format_report(self.report)
        self.assertIn("Excluded (non-executable status)", out)
        self.assertIn("`REL-058`", out)
        self.assertIn("`SYSGAP-046`", out)
        # The Unblocked section itself must not contain the filtered rows.
        unblocked_section = out.split("## Unblocked (ready to work)", 1)[1].split("## Excluded (non-executable status)", 1)[0]
        self.assertNotIn("REL-058", unblocked_section)
        self.assertNotIn("FIX-197", unblocked_section)
        self.assertIn("`FIX-777`", unblocked_section)


class TestCycleWarning(unittest.TestCase):
    """Cycle tolerance — cycles are a WARN, not an ERROR (FIX-237.2).

    The dependency graph may still contain a cycle (or a future one); the
    report must keep the cycle list for visibility but expose a
    ``cycle_warning`` flag and format a WARNING banner — the analysis output
    is best-effort and must not be blocked by the cycle.
    """

    def test_cycle_warning_flag_set_when_cycles_present(self):
        a = TaskDep("FIX-A", "P0", "⏳", ("FIX-B",), (), "0.1.0")
        b = TaskDep("FIX-B", "P0", "⏳", ("FIX-A",), (), "0.1.0")
        report = compute_unblocked_tasks([a, b])
        self.assertTrue(report.cycle_warning)
        self.assertTrue(len(report.cycles) >= 1)

    def test_cycle_warning_flag_false_when_acyclic(self):
        report = compute_unblocked_tasks(parse_task_dependencies(_SAMPLE_TABLE))
        self.assertFalse(report.cycle_warning)

    def test_cycle_banner_is_warning_not_error(self):
        a = TaskDep("FIX-A", "P0", "⏳", ("FIX-B",), (), "0.1.0")
        b = TaskDep("FIX-B", "P0", "⏳", ("FIX-A",), (), "0.1.0")
        out = format_report(compute_unblocked_tasks([a, b]))
        self.assertIn("CYCLE DETECTED (WARNING)", out)
        self.assertNotIn("(ERROR)", out)
        # The cycle members are still listed (visibility preserved).
        self.assertIn("FIX-A", out)
        self.assertIn("FIX-B", out)

    def test_cycle_does_not_block_best_effort_unblocked(self):
        a = TaskDep("FIX-A", "P0", "⏳", ("FIX-B",), (), "0.1.0")
        b = TaskDep("FIX-B", "P0", "⏳", ("FIX-A",), (), "0.1.0")
        c = TaskDep("FIX-C", "P1", "⏳", (), (), "0.2.0")
        report = compute_unblocked_tasks([a, b, c])
        self.assertTrue(report.cycle_warning)
        unblocked_ids = {t.task_id for t in report.unblocked}
        self.assertIn("FIX-C", unblocked_ids)


class TestBackwardCompatibility(unittest.TestCase):
    """New report fields must not break existing consumers (FIX-237.2)."""

    def test_new_fields_default_on_plain_constructor(self):
        report = PriorityReport()
        self.assertEqual(report.non_executable, [])
        self.assertFalse(report.cycle_warning)

    def test_old_style_keyword_constructor_still_works(self):
        report = PriorityReport(
            completed=[], blocked=[], unblocked=[], recommended_next=[],
            total=0, dependency_graph={}, cycles=[],
        )
        self.assertEqual(report.non_executable, [])
        self.assertFalse(report.cycle_warning)


# ─── Fixture: unblocked=0 (all-blocked) — REQ-110 empty-recommendation fallback ──
#
# FIX-254 / REQ-110: the live-data shape (total=131+ / unblocked=0 →
# recommended_next 恒空，任务完成后的推荐交互退化为机械枚举) reduced to a
# minimal fixture. One completed dep, one dependency-satisfied head held by a
# terminal status marker (⛔) with a two-task blocked chain hanging off it, and
# one unknown-dependency chain. The ⛔ head is the highest-value unblock entry
# (2 downstream tasks vs the unknown chain's 1).
_ALL_BLOCKED_TABLE = """\
# Plan Tracker

### 优先级一览

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| **P1** | FIX-200 | completed dep | — | 0.1.0 | closed | ✅ 完成 (2026-01-01) |
| **P0** | FIX-205 | held head (deps satisfied) | FIX-200✅ | 0.2.0 | open | ⛔ BLOCKED_ENVIRONMENT |
| **P0** | FIX-207 | blocked child | FIX-205 | 0.2.0 | open | ⏳ 待执行 |
| **P0** | FIX-208 | blocked grandchild | FIX-207 | 0.2.0 | open | ⏳ 待执行 |
| **P1** | FIX-210 | unknown-dep child | FIX-299 | 0.3.0 | open | ⏳ 待执行 |
"""


class TestEmptyRecommendationFallback(unittest.TestCase):
    """REQ-110 / FIX-254 — unblocked=0 must NOT degrade to a bare empty list.

    When no task is unblocked, the report must carry either a blocked-chain
    unblock recommendation (the head node of the highest-value chain + a
    dependency reason) or a structured empty reason (all_blocked /
    all_non_executable / no_active_tasks + nearest actionable step). A bare
    ``recommended_next: []`` with no explanation is the AUDIT-143 data-layer
    root cause of user-feedback 2a/2b and is forbidden.
    """

    def test_all_blocked_fixture_recommends_unblock_chain(self):
        report = compute_unblocked_tasks(parse_task_dependencies(_ALL_BLOCKED_TABLE))
        self.assertEqual(report.recommended_next, [])
        self.assertEqual(report.unblocked, [])
        rec = report.unblock_recommendation
        self.assertIsNotNone(rec)
        # FIX-205 (⛔ held, deps satisfied) heads the chain FIX-207→FIX-208 —
        # 2 downstream beats the unknown-dep chain FIX-299→FIX-210 (1).
        self.assertEqual(rec.root_task_id, "FIX-205")
        self.assertEqual(rec.root_kind, "non_executable_status")
        self.assertEqual(rec.downstream_task_ids, ("FIX-207", "FIX-208"))
        self.assertEqual(rec.downstream_count, 2)
        self.assertIn("FIX-205", rec.reason)
        self.assertIn("status", rec.reason)

    def test_all_blocked_fixture_structured_empty_reason(self):
        report = compute_unblocked_tasks(parse_task_dependencies(_ALL_BLOCKED_TABLE))
        er = report.empty_reason
        self.assertIsNotNone(er)
        self.assertEqual(er["kind"], "all_blocked")
        self.assertEqual(er["blocked"], 3)          # FIX-207, FIX-208, FIX-210
        self.assertEqual(er["non_executable"], 1)   # FIX-205
        self.assertEqual(er["completed"], 1)        # FIX-200
        self.assertIn("FIX-205", er["nearest_action"])

    def test_unblock_picks_highest_value_chain_over_priority(self):
        # Downstream count dominates: a P1 head unlocking 3 beats a P0 head
        # unlocking 1 (value = how much of the plan reopens).
        head_p1 = TaskDep("FIX-901", "P1", "⛔ HELD", (), (), "0.1.0")
        c1 = TaskDep("FIX-902", "P0", "⏳ 待执行", ("FIX-901",), (), "0.1.0")
        c2 = TaskDep("FIX-903", "P1", "⏳ 待执行", ("FIX-902",), (), "0.1.0")
        c3 = TaskDep("FIX-904", "P2", "⏳ 待执行", ("FIX-903",), (), "0.1.0")
        head_p0 = TaskDep("FIX-905", "P0", "⏸ HELD", (), (), "0.1.0")
        d1 = TaskDep("FIX-906", "P0", "⏳ 待执行", ("FIX-905",), (), "0.1.0")
        report = compute_unblocked_tasks([head_p1, c1, c2, c3, head_p0, d1])
        rec = report.unblock_recommendation
        self.assertIsNotNone(rec)
        self.assertEqual(rec.root_task_id, "FIX-901")
        self.assertEqual(rec.downstream_task_ids, ("FIX-902", "FIX-903", "FIX-904"))

    def test_unblock_equal_value_tiebreak_prefers_priority(self):
        # Equal downstream counts → higher-priority root wins.
        head_p1 = TaskDep("FIX-910", "P1", "⛔ HELD", (), (), "0.1.0")
        c1 = TaskDep("FIX-911", "P0", "⏳ 待执行", ("FIX-910",), (), "0.1.0")
        head_p0 = TaskDep("FIX-912", "P0", "⏸ HELD", (), (), "0.1.0")
        c2 = TaskDep("FIX-913", "P0", "⏳ 待执行", ("FIX-912",), (), "0.1.0")
        report = compute_unblocked_tasks([head_p1, c1, head_p0, c2])
        rec = report.unblock_recommendation
        self.assertIsNotNone(rec)
        self.assertEqual(rec.root_task_id, "FIX-912")

    def test_unknown_dependency_root_reported_with_reason(self):
        # A task-family dep missing from the table blocks fail-closed; the
        # fallback must surface it as a data-gap root, not stay silent.
        t = TaskDep("FIX-970", "P0", "⏳ 待执行", ("FIX-999",), (), "0.1.0")
        report = compute_unblocked_tasks([t])
        rec = report.unblock_recommendation
        self.assertIsNotNone(rec)
        self.assertEqual(rec.root_task_id, "FIX-999")
        self.assertEqual(rec.root_kind, "unknown_dependency")
        self.assertEqual(rec.downstream_task_ids, ("FIX-970",))
        self.assertIn("FIX-999", rec.reason)
        self.assertEqual(report.empty_reason["kind"], "all_blocked")

    def test_cycle_blocker_walk_terminates_with_cycle_root(self):
        # A↔B blocker cycle: the walk must terminate and classify the root as
        # a cycle (never a RecursionError / hang).
        a = TaskDep("FIX-940", "P0", "⏳ 待执行", ("FIX-941",), (), "0.1.0")
        b = TaskDep("FIX-941", "P0", "⏳ 待执行", ("FIX-940",), (), "0.1.0")
        c = TaskDep("FIX-942", "P0", "⏳ 待执行", ("FIX-940",), (), "0.1.0")
        report = compute_unblocked_tasks([a, b, c])
        rec = report.unblock_recommendation
        self.assertIsNotNone(rec)
        self.assertEqual(rec.root_kind, "cycle")
        self.assertEqual(rec.root_task_id, "FIX-940")
        self.assertEqual(set(rec.downstream_task_ids), {"FIX-940", "FIX-942"})

    def test_all_non_executable_yields_structured_reason_and_nearest_action(self):
        # Nothing is dependency-blocked; every active row is held by a
        # terminal status marker. There is NO blocked chain, so no chain
        # recommendation — kind = all_non_executable + a nearest action that
        # re-evaluates the highest-priority held row.
        low = TaskDep("FIX-920", "P2", "⛔ BLOCKED", (), (), "0.1.0")
        high = TaskDep("FIX-921", "P0", "⏸ SPLIT_TO FIX-922/FIX-923", (), (), "0.1.0")
        report = compute_unblocked_tasks([low, high])
        self.assertEqual(report.blocked, [])
        er = report.empty_reason
        self.assertIsNotNone(er)
        self.assertEqual(er["kind"], "all_non_executable")
        self.assertEqual(er["non_executable"], 2)
        # No chain → no unblock recommendation; the nearest action carries
        # the re-evaluation entry point instead.
        self.assertIsNone(report.unblock_recommendation)
        self.assertIn("FIX-921", er["nearest_action"])

    def test_no_active_tasks_yields_structured_reason(self):
        done_a = TaskDep("FIX-930", "P0", "✅ 完成", (), (), "0.1.0")
        done_b = TaskDep("FIX-931", "P1", "✅ 完成", (), (), "0.1.0")
        report = compute_unblocked_tasks([done_a, done_b])
        self.assertIsNone(report.unblock_recommendation)
        er = report.empty_reason
        self.assertIsNotNone(er)
        self.assertEqual(er["kind"], "no_active_tasks")
        self.assertTrue(er["nearest_action"])

    def test_empty_input_yields_no_active_tasks_reason(self):
        report = compute_unblocked_tasks([])
        self.assertIsNone(report.unblock_recommendation)
        self.assertEqual(report.empty_reason["kind"], "no_active_tasks")

    def test_fallback_dormant_when_unblocked_present(self):
        # Zero behavior change on the non-empty path (no scope creep).
        report = compute_unblocked_tasks(parse_task_dependencies(_SAMPLE_TABLE))
        self.assertTrue(report.recommended_next)
        self.assertIsNone(report.unblock_recommendation)
        self.assertIsNone(report.empty_reason)
        # Same for the third-class-filter fixture (FIX-777 is unblocked).
        report2 = compute_unblocked_tasks(parse_task_dependencies(_NON_EXECUTABLE_TABLE))
        self.assertTrue(report2.recommended_next)
        self.assertIsNone(report2.unblock_recommendation)
        self.assertIsNone(report2.empty_reason)

    def test_backward_compat_new_fields_default_none(self):
        report = PriorityReport()
        self.assertIsNone(report.unblock_recommendation)
        self.assertIsNone(report.empty_reason)
        legacy = PriorityReport(
            completed=[], blocked=[], unblocked=[], recommended_next=[],
            total=0, dependency_graph={}, cycles=[],
        )
        self.assertIsNone(legacy.unblock_recommendation)
        self.assertIsNone(legacy.empty_reason)

    # ── FIX-258 debt pack: F-3/F-4/F-6 coverage + F-2 compute-level ─────────
    # (遗留观察项 from review-FIX-254-CODE-R0.md §1)

    def test_diamond_shape_attributes_shared_root_not_cycle(self):
        # F-4: origin depends on B and C; both depend on the SAME held root
        # R. The per-branch ``path`` set must attribute both branches to the
        # shared root (set-deduped per origin) instead of misreading the
        # reconvergence as a cycle, and R's downstream must be the full
        # union {B, C, origin} (count 3 — diamond neither double-counts nor
        # loses the shared-root attribution).
        root = TaskDep("FIX-915", "P1", "⛔ HELD", (), (), "0.1.0")
        b = TaskDep("FIX-916", "P0", "⏳ 待执行", ("FIX-915",), (), "0.1.0")
        c = TaskDep("FIX-917", "P0", "⏳ 待执行", ("FIX-915",), (), "0.1.0")
        origin = TaskDep("FIX-918", "P0", "⏳ 待执行",
                         ("FIX-916", "FIX-917"), (), "0.1.0")
        report = compute_unblocked_tasks([root, b, c, origin])
        rec = report.unblock_recommendation
        self.assertIsNotNone(rec)
        self.assertEqual(rec.root_task_id, "FIX-915")
        self.assertEqual(rec.root_kind, "non_executable_status")
        self.assertEqual(rec.downstream_task_ids,
                         ("FIX-916", "FIX-917", "FIX-918"))
        self.assertEqual(rec.downstream_count, 3)

    def test_two_chains_converging_on_same_root_count_union(self):
        # F-4: two INDEPENDENT blocked chains converging on one root — the
        # root's downstream count is the union of both chains' origins (2,
        # set semantics: no double-count, no loss).
        root = TaskDep("FIX-925", "P1", "⛔ HELD", (), (), "0.1.0")
        a1 = TaskDep("FIX-926", "P0", "⏳ 待执行", ("FIX-925",), (), "0.1.0")
        b1 = TaskDep("FIX-927", "P2", "⏳ 待执行", ("FIX-925",), (), "0.1.0")
        report = compute_unblocked_tasks([root, a1, b1])
        rec = report.unblock_recommendation
        self.assertIsNotNone(rec)
        self.assertEqual(rec.root_task_id, "FIX-925")
        self.assertEqual(rec.downstream_count, 2)
        # Priority-ordered downstream: P0 FIX-926 before P2 FIX-927.
        self.assertEqual(rec.downstream_task_ids, ("FIX-926", "FIX-927"))

    def test_unblock_tiebreak_version_decisive_before_id(self):
        # F-6①: equal count + equal priority → LOWER target version wins —
        # version outranks ID (FIX-953's 0.2.0 beats FIX-951's 0.5.0 even
        # though FIX-951 is the smaller ID, so an ID-only tiebreak fails).
        r_late = TaskDep("FIX-951", "P0", "⛔ HELD", (), (), "0.5.0")
        d1 = TaskDep("FIX-952", "P0", "⏳ 待执行", ("FIX-951",), (), "0.1.0")
        r_early = TaskDep("FIX-953", "P0", "⏸ HELD", (), (), "0.2.0")
        d2 = TaskDep("FIX-954", "P0", "⏳ 待执行", ("FIX-953",), (), "0.1.0")
        report = compute_unblocked_tasks([r_late, d1, r_early, d2])
        self.assertEqual(report.unblock_recommendation.root_task_id, "FIX-953")

    def test_unblock_tiebreak_id_decisive_at_full_tie(self):
        # F-6①: count/priority/version all equal → smaller root ID wins
        # (the total-order endgame; deterministic regardless of dict order —
        # the smaller-ID root FIX-961 is listed AFTER FIX-962 here).
        r_b = TaskDep("FIX-962", "P1", "⛔ HELD", (), (), "0.1.0")
        d1 = TaskDep("FIX-963", "P0", "⏳ 待执行", ("FIX-962",), (), "0.1.0")
        r_a = TaskDep("FIX-961", "P1", "⏸ HELD", (), (), "0.1.0")
        d2 = TaskDep("FIX-964", "P0", "⏳ 待执行", ("FIX-961",), (), "0.1.0")
        report = compute_unblocked_tasks([r_b, d1, r_a, d2])
        self.assertEqual(report.unblock_recommendation.root_task_id, "FIX-961")

    def test_all_blocked_message_held_clause_when_non_executable_coexists(self):
        # F-6③: blocked + non_executable coexist → the all_blocked message
        # carries the "; N dependency-satisfied row(s) additionally held by
        # non-executable status markers" clause (N = 1: the ⛔ FIX-205 row).
        report = compute_unblocked_tasks(
            parse_task_dependencies(_ALL_BLOCKED_TABLE))
        er = report.empty_reason
        self.assertEqual(er["kind"], "all_blocked")
        self.assertIn(
            "; 1 dependency-satisfied row(s) additionally held "
            "by non-executable status markers", er["message"])

    def test_all_blocked_message_no_held_clause_without_non_executable(self):
        # F-6③ negative: blocked-only fixture (no held rows) → no clause.
        t = TaskDep("FIX-970", "P0", "⏳ 待执行", ("FIX-999",), (), "0.1.0")
        report = compute_unblocked_tasks([t])
        self.assertNotIn("additionally held",
                         report.empty_reason["message"])

    def test_multi_entry_cycle_downstream_count_declared_per_node(self):
        # F-3 (option b — DECLARED approximation, FIX-258): a multi-node
        # cycle entered from DIFFERENT members splits downstream attribution
        # per member. X↔Y with D1 entering via X and D2 via Y: each member
        # root carries itself + its own entrants (count 2), undercounting
        # the cycle's true unlock scope (X, Y, D1, D2 = 4). The pick is a
        # genuine cycle member and the action guidance ("resolve the
        # cycle") is correct — pinned here as DECLARED semantics (see the
        # approximation note on UnblockRecommendation), not a defect.
        x = TaskDep("FIX-980", "P0", "⏳ 待执行", ("FIX-981",), (), "0.1.0")
        y = TaskDep("FIX-981", "P0", "⏳ 待执行", ("FIX-980",), (), "0.1.0")
        d1 = TaskDep("FIX-982", "P0", "⏳ 待执行", ("FIX-980",), (), "0.1.0")
        d2 = TaskDep("FIX-983", "P0", "⏳ 待执行", ("FIX-981",), (), "0.1.0")
        report = compute_unblocked_tasks([x, y, d1, d2])
        rec = report.unblock_recommendation
        self.assertIsNotNone(rec)
        self.assertEqual(rec.root_kind, "cycle")
        # Deterministic total order: both member roots count 2 with equal
        # priority/version → smaller ID FIX-980 wins.
        self.assertEqual(rec.root_task_id, "FIX-980")
        self.assertEqual(rec.downstream_task_ids, ("FIX-980", "FIX-982"))
        # Per-member split (2); the cycle's full unlock scope is 4.
        self.assertEqual(rec.downstream_count, 2)

    def test_visit_budget_exhaustion_marks_reason_and_terminates(self):
        # F-2 (compute-level): a 15-layer binary diamond lattice makes the
        # origin's simple-path enumeration exponential (~2×(2^15−1) ≈ 65k
        # visits > the default per-walk budget). compute must terminate
        # promptly, still recommend (the held layer-14 roots win on
        # downstream count over the tiny truncated frontier roots), and the
        # recommendation reason must carry the observable truncation note.
        tasks = [TaskDep("FIX-800", "P0", "⏳ 待执行",
                         ("FIX-901", "FIX-902"), (), "0.1.0")]
        for i in range(14):  # layers 0..13, two nodes each
            deps = ((f"FIX-{901 + 2 * (i + 1)}", f"FIX-{902 + 2 * (i + 1)}")
                    if i < 13 else ("FIX-929", "FIX-930"))
            for s in (0, 1):
                tasks.append(TaskDep(f"FIX-{901 + 2 * i + s}", "P0",
                                     "⏳ 待执行", deps, (), "0.1.0"))
        tasks.append(TaskDep("FIX-929", "P0", "⛔ HELD", (), (), "0.1.0"))
        tasks.append(TaskDep("FIX-930", "P0", "⛔ HELD", (), (), "0.1.0"))
        report = compute_unblocked_tasks(tasks)  # returning == no hang/crash
        rec = report.unblock_recommendation
        self.assertIsNotNone(rec)
        self.assertIn(rec.root_task_id, {"FIX-929", "FIX-930"})
        self.assertEqual(rec.root_kind, "non_executable_status")
        self.assertIn("visit budget", rec.reason)
        self.assertIn("downstream attribution may be truncated", rec.reason)

    def test_depth_cap_long_chain_classifies_cycle_style_root(self):
        # F-6②: depth-cap boundary — a chain DEEPER than
        # _MAX_ROOT_WALK_DEPTH (200) must terminate via the depth guard and
        # classify the OVER-CAP node as a cycle-style root (defensive
        # semantics per R0 F-6②), never crash. Programmatic 202-link chain:
        # origin FIX-2999 → FIX-3000 (depth 0) → … → FIX-3201 (depth 201).
        chain = [f"FIX-{3000 + i}" for i in range(_MAX_ROOT_WALK_DEPTH + 2)]
        task_index = {tid: TaskDep(tid, "P0", "⏳ 待执行", (), (), "0.1.0")
                      for tid in chain}
        task_index["FIX-2999"] = TaskDep("FIX-2999", "P0", "⏳ 待执行",
                                         ("FIX-3000",), (), "0.1.0")
        blocked_map = {"FIX-2999": ("FIX-3000",)}
        for i in range(len(chain) - 1):
            blocked_map[chain[i]] = (chain[i + 1],)
        # Chain tail: a held root (⛔, no deps) — reachable only PAST the cap.
        task_index[chain[-1]] = TaskDep(chain[-1], "P0", "⛔ HELD",
                                        (), (), "0.1.0")
        roots: dict = {}
        exhausted = _walk_blocker_roots(
            "FIX-2999", blocked_map, task_index, roots)
        # The over-cap node (depth 201 > 200) is classified cycle-style and
        # attributed to the origin.
        self.assertEqual(roots.get((chain[-1], _ROOT_KIND_CYCLE)),
                         {"FIX-2999"})
        # The in-cap predecessor (depth 200 ≤ 200) is NOT a cycle root —
        # only the over-cap node flips to cycle-style classification.
        self.assertNotIn((chain[-2], _ROOT_KIND_CYCLE), roots)
        # Depth-cap termination is distinct from the F-2 visit budget: a
        # 202-link chain is far under _MAX_ROOT_WALK_VISITS.
        self.assertFalse(exhausted)


class TestEmptyRecommendationFallbackFormat(unittest.TestCase):
    """format_report rendering of the REQ-110 fallback (no bare empty list)."""

    def test_format_all_blocked_renders_unblock_pick(self):
        out = format_report(
            compute_unblocked_tasks(parse_task_dependencies(_ALL_BLOCKED_TABLE)))
        self.assertIn("No unblocked tasks", out)
        self.assertIn("Unblock pick", out)
        self.assertIn("`FIX-205`", out)
        self.assertIn("status", out)
        self.assertIn("`FIX-207`", out)
        self.assertIn("`FIX-208`", out)
        self.assertIn("nearest action", out)
        self.assertIn("all_blocked", out)
        # The pre-FIX-254 bare fallback text must be gone in this branch.
        self.assertNotIn(
            "Every non-completed task is blocked or there are no active tasks", out)

    def test_format_all_non_executable_renders_structured_reason(self):
        low = TaskDep("FIX-920", "P2", "⛔ BLOCKED", (), (), "0.1.0")
        high = TaskDep("FIX-921", "P0", "⏸ HELD", (), (), "0.1.0")
        out = format_report(compute_unblocked_tasks([low, high]))
        self.assertIn("No unblocked tasks", out)
        self.assertIn("all_non_executable", out)
        self.assertIn("`FIX-921`", out)
        self.assertIn("nearest action", out)
        self.assertNotIn("Unblock pick", out)

    def test_format_no_active_tasks_renders_structured_reason(self):
        done = TaskDep("FIX-930", "P0", "✅ 完成", (), (), "0.1.0")
        out = format_report(compute_unblocked_tasks([done]))
        self.assertIn("No unblocked tasks", out)
        self.assertIn("no_active_tasks", out)
        self.assertIn("nearest action", out)
        self.assertNotIn("Unblock pick", out)

    def test_format_normal_table_has_no_fallback_markers(self):
        out = format_report(
            compute_unblocked_tasks(parse_task_dependencies(_SAMPLE_TABLE)))
        self.assertIn("Top pick", out)
        self.assertNotIn("Unblock pick", out)
        self.assertNotIn("nearest action", out)


# ─── CLI integration fixtures (FIX-237.3 P2-1) ──────────────────────────────
#
# These tables are written to a TEMPORARY project root (never the real
# .governance/) and read by ``verify_workflow.py task-priority-analysis
# --project-root <tmp>`` via subprocess.
_CYCLIC_CLI_TABLE = """\
# Priority fixture with a dependency cycle (FIX-237.3 CLI test)

### 优先级一览

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| **P0** | FIX-991 | cycle node a | FIX-992 | 0.1.0 | open | ⏳ 待执行 |
| **P0** | FIX-992 | cycle node b | FIX-991 | 0.1.0 | open | ⏳ 待执行 |
| **P1** | FIX-993 | independent task | — | 0.2.0 | open | ⏳ 待执行 |
"""

_ACYCLIC_CLI_TABLE = """\
# Priority fixture without a cycle (FIX-237.3 CLI test)

### 优先级一览

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| **P0** | FIX-991 | depends on b | FIX-992 | 0.1.0 | open | ⏳ 待执行 |
| **P0** | FIX-992 | leaf task | — | 0.1.0 | open | ⏳ 待执行 |
| **P1** | FIX-993 | independent task | — | 0.2.0 | open | ⏳ 待执行 |
"""


class TestTaskPriorityCliCycleTolerance(unittest.TestCase):
    """CLI integration — cycle tolerance (FIX-237.3 P2-1).

    These are subprocess-level integration tests: they run ``verify_workflow.py
    task-priority-analysis --project-root <temp>`` against a TEMPORARY fixture
    plan-tracker (the real ``.governance/`` is never touched). The CLI must
    exit 0 with a CYCLE DETECTED (WARNING) banner by default when the
    dependency graph contains a cycle, and exit 1 only under ``--strict``.
    """

    _CLI = Path(__file__).resolve().parent.parent / "verify_workflow.py"

    def _run_cli(self, project_root, extra=()):
        return subprocess.run(
            [sys.executable, str(self._CLI), "task-priority-analysis",
             "--project-root", str(project_root), *extra],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120,
        )

    def _write_fixture(self, table):
        tmp = tempfile.TemporaryDirectory(prefix="spg-tpa-cli-")
        gov = Path(tmp.name) / ".governance"
        gov.mkdir(parents=True, exist_ok=True)
        (gov / "plan-tracker.md").write_text(table, encoding="utf-8")
        self.addCleanup(tmp.cleanup)
        return tmp.name

    def test_cycle_defaults_to_exit_0_with_warning_banner(self):
        root = self._write_fixture(_CYCLIC_CLI_TABLE)
        proc = self._run_cli(root)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("CYCLE DETECTED (WARNING)", proc.stdout)
        self.assertNotIn("(ERROR)", proc.stdout)
        # Best-effort analysis still produced (independent task present).
        self.assertIn("`FIX-993`", proc.stdout)

    def test_cycle_strict_preserves_exit_1(self):
        root = self._write_fixture(_CYCLIC_CLI_TABLE)
        proc = self._run_cli(root, ("--strict",))
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("CYCLE DETECTED (WARNING)", proc.stdout)

    def test_acyclic_fixture_exits_0_without_banner(self):
        root = self._write_fixture(_ACYCLIC_CLI_TABLE)
        proc = self._run_cli(root)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotIn("CYCLE DETECTED", proc.stdout)


if __name__ == "__main__":
    unittest.main()
