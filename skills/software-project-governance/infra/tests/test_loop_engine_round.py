"""Unit tests for the FX-189 loop_engine additions (0.65.0 slice 2).

These tests are the load-bearing verification for the stateless round
derivation + fuse generalization + loop_state activation added by FX-189.

The two SACRED tests are:

  - ``test_derive_round_stateless_no_accumulation`` — calls ``derive_round``
    N times in sequence against the same fixture and asserts every call
    returns the same value. Catches an in-memory counter that accumulates
    across calls.
  - ``test_derive_round_parallel_safe`` — calls ``derive_round`` from N
    concurrent threads against the same fixture and asserts both return the
    same value and neither raises. This is the direct proof of ADR §8.2
    "parallel-safe by construction." An implementation using a shared mutable
    counter would diverge or race here.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_loop_engine_round.py -v
or:
    python -m unittest skills.software-project-governance.infra.tests.test_loop_engine_round -v
"""

import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import loop_engine  # noqa: E402

PLUGIN_HOME = _INFRA_DIR.parent  # skills/software-project-governance/


# ─── Shared fixtures ─────────────────────────────────────────────────────────
# A flow unit id with a dotted shape (defensive: the regex must re.escape the
# dots so they aren't interpreted as "any char" — a buggy unescaped pattern
# would also match e.g. "gameXchapterY03").
FLOW_UNIT_ID = "game.chapter.03"
TIER = "inner"

FIXTURE_R1_R2 = (
    "G6 BLOCKED — game.chapter.03 inner loop iteration\n"
    "LOOP-game.chapter.03-inner-R1 evidence: chunk1 incomplete\n"
    "LOOP-game.chapter.03-inner-R2 evidence: chunk2 addressed\n"
)
FIXTURE_R1_R2_R3 = FIXTURE_R1_R2 + "LOOP-game.chapter.03-inner-R3 evidence: chunk3 rework\n"

FIXTURE_NO_MATCH = (
    "G6 APPROVED\n"
    "some unrelated log line mentioning R1 but no LOOP- anchor\n"
    "LOOP-other.unit-inner-R1  # different flow unit, must NOT match\n"
    "LOOP-game.chapter.03-middle-R1  # different tier, must NOT match\n"
)


class DeriveRoundTests(unittest.TestCase):
    # ─── Basic derivation ────────────────────────────────────────────────────
    def test_derive_round_returns_max(self):
        """With R1 and R2 present, derive_round returns 2 (the max)."""
        self.assertEqual(
            loop_engine.derive_round(FLOW_UNIT_ID, TIER, FIXTURE_R1_R2),
            2,
        )

    def test_derive_round_adding_R3(self):
        """Adding R3 to the fixture bumps the derived round to 3."""
        self.assertEqual(
            loop_engine.derive_round(FLOW_UNIT_ID, TIER, FIXTURE_R1_R2_R3),
            3,
        )

    # ─── SACRED: stateless / no accumulation ─────────────────────────────────
    def test_derive_round_stateless_no_accumulation(self):
        """SACRED — N sequential calls against the same fixture MUST all agree.

        A buggy implementation that mutated a module-level counter (e.g.
        incrementing on each call) would see the returned value drift upward
        across these N calls. This test fails on such an implementation.
        """
        fixture = FIXTURE_R1_R2  # expected answer is 2 for every call
        expected = 2
        results = [
            loop_engine.derive_round(FLOW_UNIT_ID, TIER, fixture)
            for _ in range(10)
        ]
        self.assertTrue(
            all(r == expected for r in results),
            f"derive_round accumulated state across calls: {results}",
        )

    def test_derive_round_parallel_safe(self):
        """SACRED (load-bearing) — concurrent threads MUST agree and not raise.

        This is the direct proof of ADR §8.2 "parallel-safe by construction."
        A shared mutable counter (the canonical wrong implementation) would
        diverge across threads or raise under contention. We assert every
        thread returns the same correct value (2) with no exception.
        """
        fixture = FIXTURE_R1_R2  # expected answer is 2
        expected = 2
        n_workers = 16

        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = [
                pool.submit(loop_engine.derive_round, FLOW_UNIT_ID, TIER, fixture)
                for _ in range(n_workers)
            ]
            results = [f.result() for f in futures]  # .result() re-raises any error

        self.assertEqual(len(results), n_workers)
        self.assertTrue(
            all(r == expected for r in results),
            f"derive_round diverged under concurrency: {results}",
        )

    # ─── No-match + fail-closed ──────────────────────────────────────────────
    def test_derive_round_no_match_returns_zero(self):
        """Evidence with no matching LOOP rows returns 0 (fail-safe default)."""
        self.assertEqual(
            loop_engine.derive_round(FLOW_UNIT_ID, TIER, FIXTURE_NO_MATCH),
            0,
        )

    def test_derive_round_accepts_list_of_rows(self):
        """derive_round must accept a list of evidence rows, not just a string."""
        rows = [
            "LOOP-game.chapter.03-inner-R1 first",
            "unrelated line",
            "LOOP-game.chapter.03-inner-R2 second",
        ]
        self.assertEqual(loop_engine.derive_round(FLOW_UNIT_ID, TIER, rows), 2)


class FuseDecisionTests(unittest.TestCase):
    # ─── Boundary semantics ──────────────────────────────────────────────────
    def test_fuse_decision_iterate_at_max(self):
        """Boundary: tier=middle (max=3), round derived as 3 -> iterate.

        round == max is STILL iterate (one more allowed). Only round > max
        escalates.
        """
        fixture = (
            "LOOP-game.chapter.03-middle-R1\n"
            "LOOP-game.chapter.03-middle-R2\n"
            "LOOP-game.chapter.03-middle-R3\n"
        )
        verdict = loop_engine.fuse_decision(
            FLOW_UNIT_ID, "middle", fixture, PLUGIN_HOME
        )
        self.assertEqual(verdict["current_round"], 3)
        self.assertEqual(verdict["max_rounds"], 3)
        self.assertEqual(verdict["decision"], "iterate")

    def test_fuse_decision_escalate_over_max(self):
        """Boundary: tier=middle (max=3), round derived as 4 -> escalate."""
        fixture = (
            "LOOP-game.chapter.03-middle-R1\n"
            "LOOP-game.chapter.03-middle-R2\n"
            "LOOP-game.chapter.03-middle-R3\n"
            "LOOP-game.chapter.03-middle-R4\n"
        )
        verdict = loop_engine.fuse_decision(
            FLOW_UNIT_ID, "middle", fixture, PLUGIN_HOME
        )
        self.assertEqual(verdict["current_round"], 4)
        self.assertEqual(verdict["max_rounds"], 3)
        self.assertEqual(verdict["decision"], "escalate")

    def test_fuse_decision_each_tier_max_rounds(self):
        """Each tier maps to the ADR-declared max_rounds via its default fuse."""
        # setup=2, inner=5, middle=3, outer=2
        cases = [
            ("setup", 2),
            ("inner", 5),
            ("middle", 3),
            ("outer", 2),
        ]
        for tier, expected_max in cases:
            verdict = loop_engine.fuse_decision(
                FLOW_UNIT_ID, tier, "", PLUGIN_HOME
            )
            self.assertEqual(
                verdict["max_rounds"],
                expected_max,
                f"tier {tier}: max_rounds mismatch",
            )
            # current_round is 0 (empty evidence), so decision is iterate.
            self.assertEqual(verdict["current_round"], 0)
            self.assertEqual(verdict["decision"], "iterate")

    def test_fuse_decision_fail_closed_on_missing_fuse(self):
        """A nonexistent plugin_home (no registry) yields escalate (fail-closed)."""
        with self.subTest(stage="missing-registry"):
            verdict = loop_engine.fuse_decision(
                FLOW_UNIT_ID, "inner", FIXTURE_R1_R2, plugin_home="/no/such/home"
            )
            self.assertEqual(verdict["decision"], "escalate")
            self.assertEqual(verdict["max_rounds"], -1)
            self.assertIn("issue", verdict)


class EscalationPayloadTests(unittest.TestCase):
    def test_escalation_payload_exactly_four_options(self):
        """MUST have exactly 4 options — no 'reluctant APPROVED at round N+1' path."""
        payload = loop_engine.escalation_payload(
            FLOW_UNIT_ID, "inner", 6, "BLOCKED", 5
        )
        self.assertIn("question", payload)
        self.assertIn("options", payload)
        options = payload["options"]
        self.assertEqual(len(options), 4, "exactly four options (C5 preserved)")
        labels = [opt["label"] for opt in options]
        # Verbatim labels per spec (M7.4 §4.6 C3/C4 translated to loop tier).
        self.assertEqual(
            labels,
            [
                "Human arbitration",
                "Split the unit / reduce scope",
                "Accept degraded",
                "Withdraw the unit",
            ],
        )
        # Each option must carry a non-empty description.
        for opt in options:
            self.assertIn("description", opt)
            self.assertTrue(opt["description"].strip())
        # Negative guard: the forbidden 5th path must NOT appear.
        self.assertFalse(
            any("APPROVED" in label.upper() for label in labels),
            "forbidden 'reluctant APPROVED' 5th path present",
        )

    def test_escalation_payload_question_contains_context(self):
        """The question string embeds round/max/last_result for the human."""
        payload = loop_engine.escalation_payload(
            FLOW_UNIT_ID, "middle", 4, "NEEDS_CHANGE", 3
        )
        q = payload["question"]
        self.assertIn("middle", q)
        self.assertIn(FLOW_UNIT_ID, q)
        self.assertIn("round 4", q)
        self.assertIn("max 3", q)
        self.assertIn("NEEDS_CHANGE", q)


class ActivateLoopStateTests(unittest.TestCase):
    def test_activate_loop_state_populates_five_new_fields(self):
        """Activating a dormant loop_state populates the 5 new fields + fuse."""
        flow_unit = {
            "flow_unit_id": FLOW_UNIT_ID,
            "loop_state": {
                "active_loop": False,
                "loop_count": 0,
                "last_loop_type": None,
            },
        }
        activated = loop_engine.activate_loop_state(
            flow_unit,
            "inner",
            agent_phase="act",
            pause_points_active=["PP-Fuse-Escalate"],
            last_gate_result="NEEDS_CHANGE",
            plugin_home=PLUGIN_HOME,
        )
        ls = activated["loop_state"]

        # active_loop forced True.
        self.assertTrue(ls["active_loop"])
        # The 5 new fields must all be present.
        for field in (
            "active_loop_tier",
            "agent_phase",
            "iteration_within_inner",
            "pause_points_active",
            "last_gate_result",
            "fuse",  # nested new object (ADR §8)
        ):
            self.assertIn(field, ls, f"new loop_state field missing: {field}")

        self.assertEqual(ls["active_loop_tier"], "inner")
        self.assertEqual(ls["agent_phase"], "act")
        self.assertEqual(ls["pause_points_active"], ["PP-Fuse-Escalate"])
        self.assertEqual(ls["last_gate_result"], "NEEDS_CHANGE")
        # fuse carries the tier's max_rounds from the registry (inner=5).
        self.assertEqual(ls["fuse"]["max_rounds"], 5)
        self.assertEqual(ls["fuse"]["tripped"], False)

    def test_activate_loop_state_does_not_mutate_input(self):
        """activate_loop_state is functional — it returns a NEW dict."""
        flow_unit = {
            "flow_unit_id": FLOW_UNIT_ID,
            "loop_state": {
                "active_loop": False,
                "loop_count": 0,
                "last_loop_type": None,
            },
            "title": "Chapter 3",
        }
        # Snapshot the input before the call.
        original_loop_state = dict(flow_unit["loop_state"])
        original_top = {k: (dict(v) if isinstance(v, dict) else v) for k, v in flow_unit.items()}

        activated = loop_engine.activate_loop_state(
            flow_unit, "inner", plugin_home=PLUGIN_HOME
        )

        # The returned object is a different dict...
        self.assertIsNot(activated, flow_unit)
        self.assertIsNot(activated["loop_state"], flow_unit["loop_state"])
        # ...and the ORIGINAL input is byte-for-byte unchanged.
        self.assertEqual(flow_unit["loop_state"], original_loop_state)
        self.assertEqual(
            {k: (dict(v) if isinstance(v, dict) else v) for k, v in flow_unit.items()},
            original_top,
        )
        self.assertFalse(flow_unit["loop_state"]["active_loop"], "input must stay dormant")
        self.assertEqual(activated["title"], "Chapter 3", "non-loop_state fields preserved")

    def test_activate_loop_state_derives_round_from_evidence(self):
        """When evidence is supplied, loop_count / iteration_within_inner are derived."""
        flow_unit = {"flow_unit_id": FLOW_UNIT_ID, "loop_state": {}}
        activated = loop_engine.activate_loop_state(
            flow_unit, "inner", evidence_log=FIXTURE_R1_R2, plugin_home=PLUGIN_HOME
        )
        ls = activated["loop_state"]
        self.assertEqual(ls["loop_count"], 2)
        self.assertEqual(ls["iteration_within_inner"], 2)
        # inner max=5, round 2 <= 5 -> not tripped.
        self.assertFalse(ls["fuse"]["tripped"])

    def test_activate_loop_state_marks_tripped_on_escalation(self):
        """When the derived round exceeds max_rounds, fuse.tripped becomes True."""
        flow_unit = {"flow_unit_id": FLOW_UNIT_ID, "loop_state": {}}
        # middle max=3; supply evidence up to R4 to force escalation.
        fixture = (
            "LOOP-game.chapter.03-middle-R1\n"
            "LOOP-game.chapter.03-middle-R2\n"
            "LOOP-game.chapter.03-middle-R3\n"
            "LOOP-game.chapter.03-middle-R4\n"
        )
        activated = loop_engine.activate_loop_state(
            flow_unit, "middle", evidence_log=fixture, plugin_home=PLUGIN_HOME
        )
        ls = activated["loop_state"]
        self.assertEqual(ls["loop_count"], 4)
        self.assertEqual(ls["fuse"]["max_rounds"], 3)
        self.assertTrue(ls["fuse"]["tripped"])

    def test_activate_loop_state_preserves_last_loop_type(self):
        """An existing last_loop_type is preserved through activation."""
        flow_unit = {
            "flow_unit_id": FLOW_UNIT_ID,
            "loop_state": {"last_loop_type": "build-fix"},
        }
        activated = loop_engine.activate_loop_state(
            flow_unit, "inner", plugin_home=PLUGIN_HOME
        )
        self.assertEqual(activated["loop_state"]["last_loop_type"], "build-fix")

    def test_activate_loop_state_default_pause_points_empty(self):
        """Omitting pause_points_active yields an empty list, not None."""
        flow_unit = {"flow_unit_id": FLOW_UNIT_ID}
        activated = loop_engine.activate_loop_state(
            flow_unit, "inner", plugin_home=PLUGIN_HOME
        )
        self.assertEqual(activated["loop_state"]["pause_points_active"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
