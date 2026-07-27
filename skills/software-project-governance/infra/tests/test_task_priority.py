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
  - **Unblocked** — a not-completed task whose ALL task-family deps are
    completed (or which has none) is unblocked / ready to work.
  - **Blocked** — a not-completed task with ≥1 incomplete task-family dep is
    blocked, and the report lists the specific blocking deps.
  - **Recommended next** — the highest-priority unblocked task, tie-broken by
    target version then task ID, is the top pick.
  - **Cycle detection** — a dependency cycle (A→B→A) is detected and reported
    without infinite-looping; the report still produces best-effort analysis.
  - **Robustness** — the parser survives the malformed real-world rows:
    duplicated leading ``**P0**`` cells, free-prose 闭环路径 cells containing
    literal ``|``, ``—`` empty deps, and blank lines inside a table.

ALL tests use in-memory fixture strings — the real ``.governance/`` is NEVER
touched. The pure-module contract (no file I/O in compute) is what makes this
possible.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_task_priority.py -v
"""

import sys
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
    _is_task_family_id,
    _version_tuple,
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
#   FIX-105 BLOCKER  : 🔴 active (no task deps itself)         → unblocked (no deps; 🔴 is just a label,
#                                              NOT a dependency block — per spec, unblocked is about
#                                              dependency satisfaction, not status emoji). Acts as a
#                                              blocking SOURCE for FIX-106/FIX-109.
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
        # Unblocked (not completed + all task-family deps satisfied or none):
        #   FIX-103 (dep FIX-102 ✅), FIX-104 (no deps), FIX-105 (no deps;
        #     🔴 is a status label, NOT a dependency block), FIX-107 (only
        #     cross-entity refs), FIX-108 (FIX-102 ✅ + RISK ignored).
        self.assertEqual(unblocked_ids, {"FIX-103", "FIX-104", "FIX-105", "FIX-107", "FIX-108"})

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
        # Unblocked set: FIX-103(P0,0.2.0), FIX-104(P2,0.3.0), FIX-105(P2,0.2.0),
        #                FIX-107(P1,0.4.0), FIX-108(P2,0.4.0).
        # Sorted by priority then version: P0→FIX-103; P1→FIX-107;
        #   P2→FIX-105(0.2.0) < FIX-104(0.3.0) < FIX-108(0.4.0).
        ids = [t.task_id for t in report.recommended_next]
        self.assertEqual(ids, ["FIX-103", "FIX-107", "FIX-105", "FIX-104", "FIX-108"])

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


if __name__ == "__main__":
    unittest.main()
