"""Unit tests for loop_engine.rollup_loop_state — FX-193 (0.65.0 slice 6).

These tests are the load-bearing verification for the plan-tracker rollup
view (RISK-037 criterion 2). The single most important property proven here:

  - **Per-unit, not global** — :func:`TestRollupPerUnit.test_rollup_reports_per_unit_not_global`
    and :func:`TestNoGlobalStageInvariant.test_rollup_no_global_stage_invariant`
    prove the rollup returns one entry PER flow unit (each with its own
    tier/count) and that the result dict carries NO field that collapses
    multiple units into a single stage. ``no_global_stage`` is ALWAYS True.
    This is the RISK-037 criterion 2 executable test.

  - **Summary by tier** — :func:`TestRollupSummary.test_rollup_summary_by_tier`
    proves the ``by_tier`` counter buckets units correctly.

  - **Graceful absence** — :func:`TestRollupAbsence.test_rollup_no_runtime_returns_empty`
    proves no crash when runtime.json is absent (pre-migration); the rollup
    returns empty units and ``runtime_found=False``.

  - **Dormant units** — :func:`TestRollupDormant.test_rollup_dormant_units_handled`
    proves units with ``active_loop: false`` are included with tier=None and
    loop_count=0, not dropped.

ALL tests use ``tempfile.TemporaryDirectory`` — the real ``.governance/`` is
NEVER touched.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_loop_rollup.py -v
or:
    python -m unittest skills.software-project-governance.infra.tests.test_loop_rollup -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import loop_engine as le  # noqa: E402

# Runtime.json is written to {root}/.governance/flow-unit-runtime.json, which
# matches verify_workflow.FLOW_UNIT_RUNTIME_STATE_REL.
_RUNTIME_REL = Path(".governance/flow-unit-runtime.json")


# ─── Fixtures ───────────────────────────────────────────────────────────────


def _write_runtime(root, runtime_dict):
    """Write a flow-unit-runtime.json into root/.governance/.

    Returns ``root`` (suitable to pass as ``target`` to ``rollup_loop_state``).
    """
    gov = root / ".governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "flow-unit-runtime.json").write_text(
        json.dumps(runtime_dict, indent=2), encoding="utf-8"
    )
    return root


def _make_runtime(units, **extra):
    """Build a minimal flow-unit-runtime.json dict with the given flow_units."""
    runtime = {"workflow_model": "loop-engineering", "flow_units": units}
    runtime.update(extra)
    return runtime


def _unit(flow_unit_id, unit_type="chapter", loop_state=None):
    """Build a single flow-unit entry."""
    unit = {"flow_unit_id": flow_unit_id, "unit_type": unit_type}
    if loop_state is not None:
        unit["loop_state"] = loop_state
    return unit


# ─── Shared loop_state shapes ───────────────────────────────────────────────


def _active_state(tier, loop_count, agent_phase="act",
                  last_gate_result="NEEDS_CHANGE", fuse_tripped=False):
    """An ACTIVATED loop_state (FX-189 5-field shape)."""
    return {
        "active_loop": True,
        "active_loop_tier": tier,
        "loop_count": loop_count,
        "last_loop_type": tier,
        "agent_phase": agent_phase,
        "iteration_within_inner": loop_count,
        "pause_points_active": [],
        "last_gate_result": last_gate_result,
        "fuse": {"max_rounds": 3, "tripped": fuse_tripped},
    }


def _dormant_state(loop_count=0):
    """A DORMANT loop_state (3-field shape, active_loop false)."""
    return {
        "active_loop": False,
        "loop_count": loop_count,
        "last_loop_type": None,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Test 1 — LOAD-BEARING: rollup reports per-unit, NOT one global stage
# ═══════════════════════════════════════════════════════════════════════════


class TestRollupPerUnit(unittest.TestCase):
    """RISK-037 criterion 2 — the rollup decomposes by flow unit, not globally."""

    def test_rollup_reports_per_unit_not_global(self):
        """Test 1 (LOAD-BEARING): 3 units at different tiers → 3 separate entries.

        One released/inner, one middle, one outer. The rollup MUST return 3
        distinct unit entries, each carrying its OWN tier and loop_count.
        ``no_global_stage`` MUST be True. The result MUST NOT contain any
        field that collapses the three units into a single stage.
        """
        units = [
            _unit("demo.chapter.01", loop_state=_active_state("inner", 2)),
            _unit("demo.chapter.02", loop_state=_active_state("middle", 1)),
            _unit("demo.chapter.03", loop_state=_active_state("outer", 1)),
        ]
        with tempfile.TemporaryDirectory() as td:
            root = _write_runtime(Path(td), _make_runtime(units))
            result = le.rollup_loop_state(root=str(root))

        # Three separate per-unit entries.
        unit_entries = result["units"]
        self.assertEqual(len(unit_entries), 3,
                         f"expected 3 per-unit entries, got {len(unit_entries)}")

        # Each entry carries its OWN tier — they are NOT collapsed.
        tiers = sorted(u["active_loop_tier"] for u in unit_entries)
        self.assertEqual(tiers, ["inner", "middle", "outer"],
                         f"per-unit tiers must be distinct, got {tiers}")

        # Each entry carries its OWN loop_count — they are NOT collapsed.
        counts = sorted(u["loop_count"] for u in unit_entries)
        self.assertEqual(counts, [1, 1, 2],
                         f"per-unit loop_counts must be distinct, got {counts}")

        # flow_unit_ids are distinct — one row per unit.
        ids = [u["flow_unit_id"] for u in unit_entries]
        self.assertEqual(len(set(ids)), 3, f"unit ids must be unique, got {ids}")

        # LOAD-BEARING: no global stage field anywhere.
        self.assertTrue(result["no_global_stage"],
                        "no_global_stage MUST be True")

        # Explicit: no key in the top-level result represents ONE stage for all.
        forbidden_global_keys = ("current_stage", "global_stage",
                                 "single_stage", "stage")
        for bad_key in forbidden_global_keys:
            self.assertNotIn(bad_key, result,
                             f"rollup must not expose global-stage key "
                             f"'{bad_key}': {result}")


# ═══════════════════════════════════════════════════════════════════════════
# Test 2 — summary.by_tier counts each tier correctly
# ═══════════════════════════════════════════════════════════════════════════


class TestRollupSummary(unittest.TestCase):
    """The summary.by_tier counter buckets active units per tier."""

    def test_rollup_summary_by_tier(self):
        """Test 2: inner/middle/outer units → by_tier counts each correctly."""
        units = [
            _unit("demo.chapter.01", loop_state=_active_state("inner", 1)),
            _unit("demo.chapter.02", loop_state=_active_state("middle", 1)),
            _unit("demo.chapter.03", loop_state=_active_state("outer", 1)),
        ]
        with tempfile.TemporaryDirectory() as td:
            root = _write_runtime(Path(td), _make_runtime(units))
            result = le.rollup_loop_state(root=str(root))

        summary = result["summary"]
        self.assertEqual(summary["total_units"], 3)
        self.assertEqual(summary["active_loops"], 3)
        by_tier = summary["by_tier"]
        # One active unit in each of inner/middle/outer; setup stays 0.
        self.assertEqual(by_tier["setup"], 0)
        self.assertEqual(by_tier["inner"], 1)
        self.assertEqual(by_tier["middle"], 1)
        self.assertEqual(by_tier["outer"], 1)


# ═══════════════════════════════════════════════════════════════════════════
# Test 3 — no runtime.json → empty units, runtime_found False, no crash
# ═══════════════════════════════════════════════════════════════════════════


class TestRollupAbsence(unittest.TestCase):
    """Pre-migration (no runtime.json) → graceful empty rollup, no crash."""

    def test_rollup_no_runtime_returns_empty(self):
        """Test 3: absent runtime.json → empty units, runtime_found=False.

        Must NOT raise. The message explains the project is not yet migrated.
        """
        with tempfile.TemporaryDirectory() as td:
            # No .governance/flow-unit-runtime.json written at all.
            result = le.rollup_loop_state(root=str(Path(td)))

        self.assertEqual(result["units"], [])
        self.assertFalse(result["runtime_found"])
        # Empty summary still present and well-formed.
        self.assertEqual(result["summary"]["total_units"], 0)
        self.assertEqual(result["summary"]["active_loops"], 0)
        # LOAD-BEARING: invariant holds even when empty.
        self.assertTrue(result["no_global_stage"])
        # Message explains the pre-migration state.
        self.assertIn("message", result)
        self.assertIn("not yet migrated", result["message"])


# ═══════════════════════════════════════════════════════════════════════════
# Test 4 — dormant units (active_loop false) are included, tier=None, count=0
# ═══════════════════════════════════════════════════════════════════════════


class TestRollupDormant(unittest.TestCase):
    """Dormant units (active_loop: false) are surfaced, not dropped."""

    def test_rollup_dormant_units_handled(self):
        """Test 4: dormant units → included with tier=None, loop_count=0.

        A dormant unit (active_loop false) MUST appear in the rollup (so the
        view shows ALL units), but with ``active_loop_tier=None`` and
        ``loop_count=0`` (the inactive state), and it MUST NOT be counted in
        ``active_loops`` or ``by_tier``.
        """
        units = [
            _unit("demo.chapter.01", loop_state=_active_state("inner", 2)),
            _unit("demo.chapter.02", loop_state=_dormant_state()),
        ]
        with tempfile.TemporaryDirectory() as td:
            root = _write_runtime(Path(td), _make_runtime(units))
            result = le.rollup_loop_state(root=str(root))

        unit_entries = result["units"]
        self.assertEqual(len(unit_entries), 2,
                         "dormant units must be INCLUDED in the rollup")

        # Find the dormant unit by id.
        dormant = next(
            u for u in unit_entries if u["flow_unit_id"] == "demo.chapter.02"
        )
        self.assertIsNone(dormant["active_loop_tier"],
                          f"dormant unit tier must be None, got "
                          f"{dormant['active_loop_tier']}")
        self.assertEqual(dormant["loop_count"], 0,
                         f"dormant unit loop_count must be 0, got "
                         f"{dormant['loop_count']}")

        # Only ONE active loop (the inner one); the dormant one does not count.
        self.assertEqual(result["summary"]["active_loops"], 1)
        # by_tier only counts the inner unit.
        self.assertEqual(result["summary"]["by_tier"]["inner"], 1)
        self.assertEqual(result["summary"]["by_tier"]["middle"], 0)


# ═══════════════════════════════════════════════════════════════════════════
# Test 5 — LOAD-BEARING: no_global_stage invariant (RISK-037 criterion 2)
# ═══════════════════════════════════════════════════════════════════════════


class TestNoGlobalStageInvariant(unittest.TestCase):
    """The result dict MUST NOT contain any single-stage-for-all-units field.

    This is the RISK-037 criterion 2 executable test: the rollup is a
    per-unit decomposition by construction, and that property is asserted
    explicitly here so a regression (someone adding a ``current_stage`` /
    ``global_stage`` / ``single_stage`` convenience field) would fail fast.
    """

    # Any key that would represent ONE stage for all units is forbidden.
    _FORBIDDEN_GLOBAL_KEYS = (
        "current_stage", "global_stage", "single_stage",
        "stage", "phase", "当前阶段", "current_loop",
    )

    def test_rollup_no_global_stage_invariant(self):
        """Test 5 (LOAD-BEARING): result has no global-stage field, ever.

        Checked against the populated case (3 units) AND the empty case
        (no runtime), because the invariant must hold in ALL states — even
        when the rollup is empty.
        """
        # ── Case A: populated rollup (3 units at different tiers) ──
        units = [
            _unit("demo.chapter.01", loop_state=_active_state("inner", 2)),
            _unit("demo.chapter.02", loop_state=_active_state("middle", 1)),
            _unit("demo.chapter.03", loop_state=_active_state("outer", 1)),
        ]
        with tempfile.TemporaryDirectory() as td:
            root = _write_runtime(Path(td), _make_runtime(units))
            result_populated = le.rollup_loop_state(root=str(root))

        self.assertTrue(result_populated["no_global_stage"],
                        "no_global_stage must be True when populated")
        for bad_key in self._FORBIDDEN_GLOBAL_KEYS:
            self.assertNotIn(
                bad_key, result_populated,
                f"populated rollup must not expose global-stage key "
                f"'{bad_key}': {result_populated}",
            )
        # And the summary sub-dict must not smuggle in a global stage either.
        for bad_key in self._FORBIDDEN_GLOBAL_KEYS:
            self.assertNotIn(
                bad_key, result_populated["summary"],
                f"summary must not expose global-stage key "
                f"'{bad_key}': {result_populated['summary']}",
            )

        # ── Case B: empty rollup (no runtime.json) — invariant still holds ──
        with tempfile.TemporaryDirectory() as td:
            result_empty = le.rollup_loop_state(root=str(Path(td)))

        self.assertTrue(result_empty["no_global_stage"],
                        "no_global_stage must be True even when empty")
        for bad_key in self._FORBIDDEN_GLOBAL_KEYS:
            self.assertNotIn(
                bad_key, result_empty,
                f"empty rollup must not expose global-stage key "
                f"'{bad_key}': {result_empty}",
            )

        # ── Case C: every per-unit entry is INDEPENDENT (no shared stage) ──
        # The per-unit entries carry their own tier; none of them carries a
        # global-stage field either.
        for entry in result_populated["units"]:
            for bad_key in self._FORBIDDEN_GLOBAL_KEYS:
                self.assertNotIn(
                    bad_key, entry,
                    f"per-unit entry must not carry global-stage key "
                    f"'{bad_key}': {entry}",
                )


# ═══════════════════════════════════════════════════════════════════════════
# Bonus regression — corrupt runtime.json fails closed (never raises)
# ═══════════════════════════════════════════════════════════════════════════


class TestRollupFailClosed(unittest.TestCase):
    """A corrupt runtime.json → safe defaults, never raises."""

    def test_corrupt_runtime_returns_not_found(self):
        """Corrupt (invalid JSON) runtime.json → runtime_found=False, no raise."""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            gov.mkdir(parents=True, exist_ok=True)
            (gov / "flow-unit-runtime.json").write_text(
                "{not valid json", encoding="utf-8"
            )
            # Must NOT raise — fail-closed.
            result = le.rollup_loop_state(root=str(Path(td)))

        self.assertFalse(result["runtime_found"])
        self.assertEqual(result["units"], [])
        self.assertTrue(result["no_global_stage"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
