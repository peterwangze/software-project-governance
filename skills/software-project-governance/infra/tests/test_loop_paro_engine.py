"""Tests for the persistent PARO state machine + CAS writer (FEAT-005, ADR-014 §3).

These tests are the load-bearing verification for FEAT-005:

  - **Legal transitions**: each of the 6 forward + 3 terminal transitions
    succeeds via :func:`apply_transition` and produces the correct §3.2 side
    effects (agent_phase, loop_count±, gate_state, fuse, cas_version).
  - **Illegal transitions rejected**: plan→observe (skip act), act→plan
    (reverse), observe→act (reverse), etc.
  - **CAS conflict**: two concurrent writes to the same unit (the second write
    simulated by committing a transition between the first writer's read and
    write) → the second fails with ``STATUS_CONFLICT``.
  - **CAS atomicity**: temp-file + ``os.replace`` → the file is either old or
    new, never partial/torn.
  - **cas_version monotonic**: each transition increments by exactly 1.
  - **Activation**: entry→plan sets ``cas_version = 0``, ``loop_count = 0``,
    ``fuse.tripped = false``.
  - **Restart recovery**: write state, "restart" (re-read), verify recovered
    state matches; state-ahead-of-log case (no log → trust state).
  - **Validator extension**: active unit without cas_version → FAIL; dormant
    without cas_version → PASS; cas_version as bool → FAIL.
  - **Unification preserved**: every transition keeps
    ``last_gate_result == gate_state.last_result``.
  - **Threading test (CAS correctness)**: multiple threads
    :func:`apply_transition` the same unit → exactly ONE succeeds per
    cas_version, the rest get CONFLICT — no lost updates.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_loop_paro_engine.py -v
"""

import copy
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import loop_paro_engine as paro  # noqa: E402
from checks import flow_unit_runtime_v2  # noqa: E402

# A valid 64-lowercase-hex SHA-256 placeholder (shape-correct).
_VALID_PLAN_HASH = "a" * 64

# A canonical small fuse for the Inner tier (registry: FUSE-INNER-DEFAULT = 5).
# Tests use max_rounds=3 to keep the iterate/escalate boundary crisp.
_TEST_MAX_ROUNDS = 3


# ═══════════════════════════════════════════════════════════════════════════
# Payload builders (mirror the shapes in test_flow_unit_runtime_v2.py)
# ═══════════════════════════════════════════════════════════════════════════


def _dormant_loop_state():
    """A canonical 9-field DORMANT loop_state (as migration writes them)."""
    return {
        "active_loop": False,
        "active_loop_tier": None,
        "loop_count": 0,
        "last_loop_type": None,
        "agent_phase": "plan",
        "iteration_within_inner": 0,
        "pause_points_active": [],
        "last_gate_result": None,
        "fuse": {"max_rounds": _TEST_MAX_ROUNDS, "tripped": False},
    }


def _active_loop_state(agent_phase="plan", loop_count=0, cas_version=0,
                       last_gate_result=None, fuse_tripped=False,
                       tier="inner", max_rounds=_TEST_MAX_ROUNDS):
    """A canonical ACTIVE loop_state WITH cas_version (FEAT-005 field)."""
    return {
        "active_loop": True,
        "active_loop_tier": tier,
        "loop_count": loop_count,
        "last_loop_type": None,
        "agent_phase": agent_phase,
        "iteration_within_inner": loop_count,
        "pause_points_active": [],
        "last_gate_result": last_gate_result,
        "fuse": {"max_rounds": max_rounds, "tripped": fuse_tripped},
        "cas_version": cas_version,
    }


def _valid_gate_state(status="pending", gate_id="G5", last_result=None):
    return {
        "status": status,
        "gate_id": gate_id,
        "last_result": last_result,
        "evidence_refs": [],
    }


def _valid_unit(unit_id="shitu.story.Skeleton", runtime_status="dormant",
                loop_state=None, gate_state=None):
    """A valid v2 flow unit. Defaults to a dormant (pre-activation) unit."""
    if loop_state is None:
        loop_state = _dormant_loop_state()
    if gate_state is None:
        gate_state = _valid_gate_state(last_result=loop_state.get("last_gate_result"))
    return {
        "flow_unit_id": unit_id,
        "title": "Skeleton story unit",
        "unit_type": "story",
        "project_type": "game-narrative",
        "derivation_reason": "dotted-id:" + unit_id,
        "loop_state": loop_state,
        "gate_state": gate_state,
        "runtime_status": runtime_status,
        "dependencies": [],
        "blockers": [],
    }


def _valid_payload(units=None):
    """A valid v2 runtime payload (passes both the 0.67.0 and FEAT-005 validators)."""
    if units is None:
        units = [_valid_unit()]
    return {
        "schema_version": "2.0",
        "runtime_contract": "loop-runtime-contract/v2",
        "runtime_scope": "loop-engineering-runtime",
        "workflow_model": "loop-engineering",
        "contract_source": "loop-runtime-contract-v2",
        "migration_version": "0.67.0",
        "migration_plan_hash": _VALID_PLAN_HASH,
        "migration_timestamp": "2026-07-23T00:00:00Z",
        "decomposition_confirmed": True,
        "flow_units": units,
        "no_overclaim_boundary": [
            "Loop Runtime Contract v2 does not activate execution engine.",
            "RISK-037 remains open until 0.68.0 execution engine and 0.69.0 external validation.",
            "RISK-042 remains open until 0.69.0 external validation (VAL-008/VAL-009).",
        ],
    }


def _write_payload(tmpdir, payload):
    """Write ``payload`` to ``flow-unit-runtime.json`` under ``tmpdir``; return Path."""
    runtime_path = Path(tmpdir) / "flow-unit-runtime.json"
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    return runtime_path


def _activated_payload(unit_id="shitu.story.Skeleton", tier="inner",
                       max_rounds=_TEST_MAX_ROUNDS):
    """A payload with one unit already ACTIVATED (entry→plan done, cas_version=0)."""
    unit = _valid_unit(
        unit_id=unit_id,
        runtime_status="active",
        loop_state=_active_loop_state(agent_phase="plan", loop_count=0, cas_version=0,
                                      tier=tier, max_rounds=max_rounds),
    )
    return _valid_payload(units=[unit])


# ═══════════════════════════════════════════════════════════════════════════
# 1. Pure validator: legal + illegal transitions (no I/O)
# ═══════════════════════════════════════════════════════════════════════════


class PureValidatorLegalTransitionsTests(unittest.TestCase):
    """validate_transition accepts all 6 forward + 3 terminal transitions."""

    def test_entry_to_plan_activation(self):
        legal, reason = paro.validate_transition(None, "plan", {})
        self.assertTrue(legal, reason)
        self.assertEqual(reason, "phase_enter")

    def test_entry_aliases_accepted(self):
        for src in ("(entry)", "entry", ""):
            legal, _ = paro.validate_transition(src, "plan", {})
            self.assertTrue(legal, "entry alias {0!r} should activate".format(src))

    def test_plan_to_act(self):
        legal, reason = paro.validate_transition("plan", "act", {"reason": "accepted"})
        self.assertTrue(legal)
        self.assertEqual(reason, "phase_transition")

    def test_act_to_observe(self):
        legal, reason = paro.validate_transition("act", "observe", {})
        self.assertTrue(legal)
        self.assertEqual(reason, "phase_transition")

    def test_observe_to_reflect(self):
        legal, reason = paro.validate_transition("observe", "reflect",
                                                 {"gate_result": "NEEDS_CHANGE"})
        self.assertTrue(legal)
        self.assertIn("gate_result", reason)

    def test_reflect_to_plan_iterate_under_fuse(self):
        # loop_count (2) <= max_rounds (3) → iterate legal.
        legal, reason = paro.validate_transition(
            "reflect", "plan",
            {"gate_result": "NEEDS_CHANGE", "loop_count": 2, "max_rounds": 3},
        )
        self.assertTrue(legal)
        self.assertIn("back_edge", reason)

    def test_reflect_to_plan_iterate_at_max_is_still_legal(self):
        # §3.3 rule 2: round == max is STILL iterate (matching fuse_decision).
        legal, _ = paro.validate_transition(
            "reflect", "plan",
            {"gate_result": "NEEDS_CHANGE", "loop_count": 3, "max_rounds": 3},
        )
        self.assertTrue(legal, "loop_count == max_rounds must still iterate")

    def test_reflect_to_exit_gate_passed(self):
        legal, reason = paro.validate_transition(
            "reflect", "exit", {"gate_result": "APPROVED"},
        )
        self.assertTrue(legal)
        self.assertIn("loop_exit", reason)

    def test_reflect_to_escalate_fuse_trip(self):
        # loop_count (6) > max_rounds (5) → escalate.
        legal, reason = paro.validate_transition(
            "reflect", "escalate",
            {"gate_result": "NEEDS_CHANGE", "loop_count": 6, "max_rounds": 5},
        )
        self.assertTrue(legal)
        self.assertIn("fuse_trip", reason)

    def test_any_phase_to_withdrawn(self):
        for frm in ("plan", "act", "observe", "reflect"):
            legal, reason = paro.validate_transition(frm, "withdrawn", {})
            self.assertTrue(legal, "{0}→withdrawn should be legal".format(frm))
            self.assertEqual(reason, "unit_withdrawn")


class PureValidatorIllegalTransitionsTests(unittest.TestCase):
    """validate_transition rejects all illegal transitions (fail-closed)."""

    def test_plan_to_observe_skips_act(self):
        legal, reason = paro.validate_transition("plan", "observe", {})
        self.assertFalse(legal)
        self.assertIn("skip", reason.lower() + reason)  # message mentions the jump

    def test_act_to_plan_reverse(self):
        legal, reason = paro.validate_transition("act", "plan", {})
        self.assertFalse(legal)

    def test_observe_to_act_reverse(self):
        legal, _ = paro.validate_transition("observe", "act", {})
        self.assertFalse(legal)

    def test_reflect_to_observe_reverse(self):
        legal, _ = paro.validate_transition("reflect", "observe", {})
        self.assertFalse(legal)

    def test_plan_to_reflect_big_skip(self):
        legal, _ = paro.validate_transition("plan", "reflect", {})
        self.assertFalse(legal)

    def test_same_phase_noop(self):
        legal, _ = paro.validate_transition("act", "act", {})
        self.assertFalse(legal)

    def test_entry_to_non_plan_rejected(self):
        legal, _ = paro.validate_transition(None, "act", {})
        self.assertFalse(legal)

    def test_reflect_to_exit_requires_passed_gate(self):
        # A failed gate result cannot drive reflect→exit.
        legal, reason = paro.validate_transition(
            "reflect", "exit", {"gate_result": "NEEDS_CHANGE"},
        )
        self.assertFalse(legal)
        self.assertIn("PASSED", reason)

    def test_reflect_to_plan_rejects_when_fuse_exhausted(self):
        # loop_count (6) > max_rounds (5): iterate is illegal; must escalate.
        legal, reason = paro.validate_transition(
            "reflect", "plan",
            {"gate_result": "NEEDS_CHANGE", "loop_count": 6, "max_rounds": 5},
        )
        self.assertFalse(legal)
        self.assertIn("fuse", reason.lower())

    def test_reflect_to_escalate_rejects_when_fuse_not_exhausted(self):
        legal, _ = paro.validate_transition(
            "reflect", "escalate",
            {"gate_result": "NEEDS_CHANGE", "loop_count": 1, "max_rounds": 5},
        )
        self.assertFalse(legal)

    def test_reflect_iterate_rejects_passed_gate(self):
        # A passed gate cannot drive iterate (use exit).
        legal, _ = paro.validate_transition(
            "reflect", "plan",
            {"gate_result": "APPROVED", "loop_count": 1, "max_rounds": 5},
        )
        self.assertFalse(legal)

    def test_reflect_iterate_requires_fuse_facts(self):
        # Missing loop_count/max_rounds → fail-closed rejection.
        legal, reason = paro.validate_transition(
            "reflect", "plan", {"gate_result": "NEEDS_CHANGE"},
        )
        self.assertFalse(legal)
        self.assertIn("loop_count", reason)

    def test_unknown_from_phase(self):
        legal, _ = paro.validate_transition("garbage", "act", {})
        self.assertFalse(legal)

    def test_unknown_to_phase(self):
        legal, _ = paro.validate_transition("plan", "garbage", {})
        self.assertFalse(legal)


# ═══════════════════════════════════════════════════════════════════════════
# 2. apply_transition: end-to-end legal transitions with side effects
# ═══════════════════════════════════════════════════════════════════════════


class ApplyTransitionSideEffectsTests(unittest.TestCase):
    """Each legal transition commits and produces the correct §3.2 side effects."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="paro_test_")
        self.runtime_path = _write_payload(self.tmpdir, _activated_payload())
        self.unit_id = "shitu.story.Skeleton"

    def _unit_on_disk(self):
        payload = json.loads(self.runtime_path.read_text(encoding="utf-8"))
        for u in payload["flow_units"]:
            if u["flow_unit_id"] == self.unit_id:
                return u
        raise AssertionError("unit not on disk")

    def test_plan_to_act_advances_phase_and_bumps_cas(self):
        r = paro.apply_transition(self.unit_id, "act", {"reason": "plan accepted"},
                                  runtime_file=self.runtime_path)
        self.assertTrue(r.success, r.reason)
        self.assertEqual(r.event_type, "phase_transition")
        self.assertEqual(r.from_cas_version, 0)
        self.assertEqual(r.new_cas_version, 1)
        u = self._unit_on_disk()
        self.assertEqual(u["loop_state"]["agent_phase"], "act")
        self.assertEqual(u["loop_state"]["cas_version"], 1)

    def test_full_forward_chain_plan_act_observe_reflect(self):
        prev_cas = 0
        for to_phase, event in [
            ("act", {"reason": "accepted"}),
            ("observe", {"reason": "done"}),
            ("reflect", {"gate_result": "NEEDS_CHANGE", "reason": "review"}),
        ]:
            r = paro.apply_transition(self.unit_id, to_phase, event,
                                      runtime_file=self.runtime_path)
            self.assertTrue(r.success, "{0}: {1}".format(to_phase, r.reason))
            self.assertEqual(r.new_cas_version, prev_cas + 1)
            prev_cas = r.new_cas_version
        u = self._unit_on_disk()
        self.assertEqual(u["loop_state"]["agent_phase"], "reflect")
        self.assertEqual(u["loop_state"]["cas_version"], 3)

    def test_back_edge_increments_loop_count(self):
        # Drive to reflect with loop_count=0.
        for to_phase in ("act", "observe"):
            self.assertTrue(paro.apply_transition(
                self.unit_id, to_phase, {}, runtime_file=self.runtime_path).success)
        r = paro.apply_transition(self.unit_id, "reflect",
                                  {"gate_result": "NEEDS_CHANGE"},
                                  runtime_file=self.runtime_path)
        self.assertTrue(r.success)
        # Now reflect→plan (iterate): loop_count 0→1.
        r2 = paro.apply_transition(self.unit_id, "plan",
                                   {"gate_result": "NEEDS_CHANGE"},
                                   runtime_file=self.runtime_path)
        self.assertTrue(r2.success, r2.reason)
        self.assertEqual(r2.event_type, "back_edge+gate_result")
        u = self._unit_on_disk()
        self.assertEqual(u["loop_state"]["agent_phase"], "plan")
        self.assertEqual(u["loop_state"]["loop_count"], 1)

    def test_exit_terminal_sets_gate_passed(self):
        for to_phase in ("act", "observe", "reflect"):
            paro.apply_transition(self.unit_id, to_phase,
                                  {"gate_result": "NEEDS_CHANGE"},
                                  runtime_file=self.runtime_path)
        r = paro.apply_transition(self.unit_id, "exit",
                                  {"gate_result": "APPROVED"},
                                  runtime_file=self.runtime_path)
        self.assertTrue(r.success, r.reason)
        u = self._unit_on_disk()
        self.assertEqual(u["gate_state"]["status"], "passed")

    def test_escalate_terminal_trips_fuse_and_blocks(self):
        # Set up a unit already at loop_count == max_rounds so escalate is legal.
        unit = _valid_unit(
            unit_id=self.unit_id, runtime_status="active",
            loop_state=_active_loop_state(
                agent_phase="reflect", loop_count=_TEST_MAX_ROUNDS + 1,
                cas_version=2, last_gate_result="NEEDS_CHANGE",
                tier="inner", max_rounds=_TEST_MAX_ROUNDS),
            gate_state=_valid_gate_state(status="failed", last_result="NEEDS_CHANGE"),
        )
        self.runtime_path = _write_payload(self.tmpdir, _valid_payload(units=[unit]))
        r = paro.apply_transition(self.unit_id, "escalate",
                                  {"gate_result": "NEEDS_CHANGE"},
                                  runtime_file=self.runtime_path)
        self.assertTrue(r.success, r.reason)
        self.assertEqual(r.event_type, "fuse_trip+gate_result")
        u = self._unit_on_disk()
        self.assertTrue(u["loop_state"]["fuse"]["tripped"])
        self.assertEqual(u["runtime_status"], "blocked")
        self.assertEqual(u["gate_state"]["status"], "blocked")

    def test_withdraw_sets_runtime_status_withdrawn(self):
        r = paro.apply_transition(self.unit_id, "withdrawn", {},
                                  runtime_file=self.runtime_path)
        self.assertTrue(r.success, r.reason)
        u = self._unit_on_disk()
        self.assertEqual(u["runtime_status"], "withdrawn")
        self.assertEqual(u["gate_state"]["status"], "withdrawn")


# ═══════════════════════════════════════════════════════════════════════════
# 3. Illegal transitions via apply_transition (no state mutation)
# ═══════════════════════════════════════════════════════════════════════════


class ApplyTransitionIllegalTests(unittest.TestCase):
    """Illegal transitions return STATUS_ILLEGAL and write nothing."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="paro_test_")
        self.runtime_path = _write_payload(self.tmpdir, _activated_payload())
        self.unit_id = "shitu.story.Skeleton"

    def _cas_on_disk(self):
        u = None
        payload = json.loads(self.runtime_path.read_text(encoding="utf-8"))
        for x in payload["flow_units"]:
            if x["flow_unit_id"] == self.unit_id:
                u = x
        return u["loop_state"]["cas_version"]

    def test_skip_act_rejected_no_mutation(self):
        before = self._cas_on_disk()
        r = paro.apply_transition(self.unit_id, "observe", {},
                                  runtime_file=self.runtime_path)
        self.assertEqual(r.status, paro.STATUS_ILLEGAL)
        self.assertEqual(self._cas_on_disk(), before, "illegal transition must not bump cas")

    def test_reverse_act_to_plan_rejected(self):
        paro.apply_transition(self.unit_id, "act", {}, runtime_file=self.runtime_path)
        before = self._cas_on_disk()
        r = paro.apply_transition(self.unit_id, "plan", {}, runtime_file=self.runtime_path)
        self.assertEqual(r.status, paro.STATUS_ILLEGAL)
        self.assertEqual(self._cas_on_disk(), before)

    def test_not_activated_unit_rejected(self):
        # A dormant unit (no cas_version) cannot transition via apply_transition.
        dormant = _valid_payload(units=[_valid_unit(runtime_status="dormant")])
        path = _write_payload(self.tmpdir, dormant)
        r = paro.apply_transition("shitu.story.Skeleton", "act", {}, runtime_file=path)
        self.assertEqual(r.status, paro.STATUS_ILLEGAL)
        self.assertIn("activate_unit", r.reason)

    def test_missing_unit_rejected_as_error(self):
        r = paro.apply_transition("no.such.unit", "act", {}, runtime_file=self.runtime_path)
        self.assertEqual(r.status, paro.STATUS_ERROR)


# ═══════════════════════════════════════════════════════════════════════════
# 4. CAS conflict + atomicity + monotonicity
# ═══════════════════════════════════════════════════════════════════════════


class CASConflictTests(unittest.TestCase):
    """Two concurrent writes to the same unit → second fails with CONFLICT."""

    def test_concurrent_write_to_same_unit_yields_conflict(self):
        tmpdir = tempfile.mkdtemp(prefix="paro_test_")
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"

        # Simulate the §3.3 race precisely: another writer advanced this unit's
        # cas_version on disk (here, by one transition) BETWEEN our conceptual
        # read and write. We isolate the CAS check by bumping ONLY cas_version
        # on disk (leaving agent_phase at "plan") so the proposed plan→act
        # transition is still LEGAL — the only thing that can stop it is the CAS
        # version mismatch. This is exactly the §3.3.4 re-read check.
        payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        for u in payload["flow_units"]:
            if u["flow_unit_id"] == unit_id:
                u["loop_state"]["cas_version"] = 1  # simulate another commit
        runtime_path.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8",
        )

        # Now apply_transition reads cas=1, computes a plan→act that would
        # commit at cas=2, but the on-disk file is still cas=1 from the writer's
        # READ perspective at the start of the call. To force the conflict we
        # bump the on-disk version AGAIN inside the call's window by using a
        # side_effects hook that mutates the on-disk cas_version before the
        # commit. This deterministically reproduces "another writer committed
        # between our read and write".
        def rival_writer(new_unit, event):
            # Simulate a rival committing during our compute window.
            rival_payload = json.loads(runtime_path.read_text(encoding="utf-8"))
            for ru in rival_payload["flow_units"]:
                if ru["flow_unit_id"] == unit_id:
                    ru["loop_state"]["cas_version"] = (
                        ru["loop_state"].get("cas_version", 1) + 1
                    )
            runtime_path.write_text(
                json.dumps(rival_payload, ensure_ascii=False, sort_keys=True, indent=2),
                encoding="utf-8",
            )
            return new_unit

        r = paro.apply_transition(unit_id, "act", {"reason": "B"},
                                  runtime_file=runtime_path,
                                  side_effects=rival_writer)
        self.assertEqual(r.status, paro.STATUS_CONFLICT, r.reason)
        self.assertIn("CAS conflict", r.reason)
        self.assertIn("cas_version", r.reason)

    def test_conflict_then_retry_succeeds_at_higher_version(self):
        tmpdir = tempfile.mkdtemp(prefix="paro_test_")
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"

        # First writer commits plan→act.
        paro.apply_transition(unit_id, "act", {}, runtime_file=runtime_path)
        # A retried transition with max_retries re-reads fresh state and commits.
        r = paro.apply_transition(unit_id, "observe", {},
                                  runtime_file=runtime_path, max_retries=2)
        self.assertTrue(r.success, r.reason)
        self.assertEqual(r.new_cas_version, 2)


class CASAtomicityTests(unittest.TestCase):
    """The file is either old or new, never partial/torn."""

    def test_write_produces_valid_json_either_old_or_new(self):
        tmpdir = tempfile.mkdtemp(prefix="paro_test_")
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"

        # Capture the pre-write bytes.
        before = runtime_path.read_bytes()
        # Apply a transition.
        paro.apply_transition(unit_id, "act", {}, runtime_file=runtime_path)
        after = runtime_path.read_bytes()

        # Both snapshots must be valid JSON (atomic replace → no torn state).
        json.loads(before.decode("utf-8"))
        json.loads(after.decode("utf-8"))
        # And the two must differ (the transition committed).
        self.assertNotEqual(before, after)

    def test_no_tmp_file_left_behind(self):
        tmpdir = tempfile.mkdtemp(prefix="paro_test_")
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"
        paro.apply_transition(unit_id, "act", {}, runtime_file=runtime_path)
        leftovers = [p for p in Path(tmpdir).iterdir() if p.suffix == ".tmp"]
        self.assertEqual(leftovers, [], "no .tmp file should remain after atomic commit")


class CASMonotonicityTests(unittest.TestCase):
    """Each transition increments cas_version by exactly 1."""

    def test_monotonic_increment_across_chain(self):
        tmpdir = tempfile.mkdtemp(prefix="paro_test_")
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"
        expected = 0
        for to_phase, event in [
            ("act", {}),
            ("observe", {}),
            ("reflect", {"gate_result": "NEEDS_CHANGE"}),
            ("plan", {"gate_result": "NEEDS_CHANGE"}),  # back-edge
        ]:
            r = paro.apply_transition(unit_id, to_phase, event, runtime_file=runtime_path)
            self.assertTrue(r.success, "{0}: {1}".format(to_phase, r.reason))
            expected += 1
            self.assertEqual(r.new_cas_version, expected)
            self.assertEqual(r.new_cas_version, r.from_cas_version + 1)


# ═══════════════════════════════════════════════════════════════════════════
# 5. Activation (entry→plan)
# ═══════════════════════════════════════════════════════════════════════════


class ActivationTests(unittest.TestCase):
    """activate_unit performs the (entry)→plan transition (cas_version=0)."""

    def test_activation_sets_initial_state(self):
        tmpdir = tempfile.mkdtemp(prefix="paro_test_")
        # Start from a dormant unit (as migration writes them).
        dormant = _valid_payload(units=[_valid_unit(runtime_status="dormant")])
        runtime_path = _write_payload(tmpdir, dormant)
        unit_id = "shitu.story.Skeleton"

        r = paro.activate_unit(unit_id, runtime_file=runtime_path,
                               tier="inner", fuse_max_rounds=5)
        self.assertTrue(r.success, r.reason)
        self.assertEqual(r.new_cas_version, 0)
        self.assertEqual(r.event_type, "phase_enter")

        payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        u = [x for x in payload["flow_units"] if x["flow_unit_id"] == unit_id][0]
        ls = u["loop_state"]
        self.assertEqual(ls["agent_phase"], "plan")
        self.assertEqual(ls["loop_count"], 0)
        self.assertEqual(ls["cas_version"], 0)
        self.assertFalse(ls["fuse"]["tripped"])
        self.assertEqual(ls["fuse"]["max_rounds"], 5)
        self.assertEqual(ls["active_loop_tier"], "inner")
        self.assertTrue(ls["active_loop"])
        self.assertEqual(u["runtime_status"], "active")

    def test_double_activation_is_conflict(self):
        tmpdir = tempfile.mkdtemp(prefix="paro_test_")
        runtime_path = _write_payload(tmpdir, _activated_payload())  # already cas=0
        unit_id = "shitu.story.Skeleton"
        r = paro.activate_unit(unit_id, runtime_file=runtime_path,
                               tier="inner", fuse_max_rounds=5)
        self.assertEqual(r.status, paro.STATUS_CONFLICT)
        self.assertIn("already activated", r.reason)


# ═══════════════════════════════════════════════════════════════════════════
# 6. Restart recovery
# ═══════════════════════════════════════════════════════════════════════════


class RecoveryTests(unittest.TestCase):
    """recover_state re-reads the state file (read-based, not replay-based)."""

    def test_recovery_without_event_log_trusts_state_file(self):
        tmpdir = tempfile.mkdtemp(prefix="paro_test_")
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"
        # Drive the unit forward to a known state.
        for to_phase, ev in [("act", {}), ("observe", {}),
                             ("reflect", {"gate_result": "NEEDS_CHANGE"})]:
            paro.apply_transition(unit_id, to_phase, ev, runtime_file=runtime_path)

        # "Restart" — call recover_state (no event log).
        result = paro.recover_state(runtime_path)
        self.assertTrue(result.runtime_found)
        self.assertEqual(result.conflicts, [])
        state = result.units[unit_id]
        self.assertEqual(state["agent_phase"], "reflect")
        self.assertEqual(state["cas_version"], 3)
        self.assertEqual(state["loop_count"], 0)
        self.assertFalse(state["fuse_tripped"])

    def test_recovery_missing_file_returns_not_found(self):
        result = paro.recover_state(Path(tempfile.mkdtemp(prefix="paro_test_")) / "nope.json")
        self.assertFalse(result.runtime_found)
        self.assertEqual(result.units, {})

    def test_recovery_state_ahead_of_log_synthesizes_event(self):
        tmpdir = tempfile.mkdtemp(prefix="paro_test_")
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"
        paro.apply_transition(unit_id, "act", {}, runtime_file=runtime_path)  # cas 0→1

        # Event log is BEHIND the state file (last event cas=0; on-disk cas=1).
        event_log = [
            {"unit_id": unit_id, "event_type": "phase_enter", "to_phase": "plan",
             "cas_version": 0},
        ]
        result = paro.recover_state(runtime_path, event_log=event_log)
        self.assertEqual(result.conflicts, [])
        # A synthetic phase_recovery event should be recorded for FEAT-007.
        synth = [e for e in result.synthetic_events if e["unit_id"] == unit_id]
        self.assertTrue(synth, "state-ahead-of-log should synthesize a recovery event")

    def test_recovery_log_ahead_of_state_fail_closes_unit(self):
        tmpdir = tempfile.mkdtemp(prefix="paro_test_")
        runtime_path = _write_payload(tmpdir, _activated_payload())  # on-disk cas=0
        unit_id = "shitu.story.Skeleton"

        # Event log is AHEAD of the state file (last event cas=2; on-disk cas=0).
        # This is the DANGEROUS case — the unit must be fail-closed to blocked.
        event_log = [
            {"unit_id": unit_id, "event_type": "phase_enter", "to_phase": "plan",
             "cas_version": 0},
            {"unit_id": unit_id, "event_type": "phase_transition", "from_phase": "plan",
             "to_phase": "act", "cas_version": 1},
            {"unit_id": unit_id, "event_type": "phase_transition", "from_phase": "act",
             "to_phase": "observe", "cas_version": 2},
        ]
        result = paro.recover_state(runtime_path, event_log=event_log)
        self.assertIn(unit_id, result.conflicts)
        self.assertEqual(result.units[unit_id]["runtime_status"], "blocked")
        self.assertEqual(result.units[unit_id]["recovery_status"], paro.RECOVERY_CONFLICT)


# ═══════════════════════════════════════════════════════════════════════════
# 7. Unification invariant preserved across transitions
# ═══════════════════════════════════════════════════════════════════════════


class UnificationInvariantTests(unittest.TestCase):
    """Every transition keeps loop_state.last_gate_result == gate_state.last_result."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="paro_test_")
        self.runtime_path = _write_payload(self.tmpdir, _activated_payload())
        self.unit_id = "shitu.story.Skeleton"

    def _unit(self):
        payload = json.loads(self.runtime_path.read_text(encoding="utf-8"))
        return [x for x in payload["flow_units"] if x["flow_unit_id"] == self.unit_id][0]

    def test_unification_holds_after_gate_bearing_transitions(self):
        for to_phase, ev in [("act", {}), ("observe", {}),
                             ("reflect", {"gate_result": "NEEDS_CHANGE"}),
                             ("plan", {"gate_result": "NEEDS_CHANGE"})]:
            r = paro.apply_transition(self.unit_id, to_phase, ev,
                                      runtime_file=self.runtime_path)
            self.assertTrue(r.success, "{0}: {1}".format(to_phase, r.reason))
            u = self._unit()
            ls = u["loop_state"]
            gs = u["gate_state"]
            self.assertEqual(
                ls["last_gate_result"], gs["last_result"],
                "unification broken after {0}: ls={1!r} gs={2!r}".format(
                    to_phase, ls["last_gate_result"], gs["last_result"]),
            )

    def test_exit_and_escalate_keep_unification(self):
        # Drive to reflect, then exit (passed).
        for to_phase, ev in [("act", {}), ("observe", {}),
                             ("reflect", {"gate_result": "NEEDS_CHANGE"})]:
            paro.apply_transition(self.unit_id, to_phase, ev,
                                  runtime_file=self.runtime_path)
        # Reset to a fresh reflect unit for the escalate case.
        unit = _valid_unit(
            unit_id=self.unit_id, runtime_status="active",
            loop_state=_active_loop_state(
                agent_phase="reflect", loop_count=_TEST_MAX_ROUNDS + 1,
                cas_version=2, last_gate_result="NEEDS_CHANGE",
                tier="inner", max_rounds=_TEST_MAX_ROUNDS),
            gate_state=_valid_gate_state(status="failed", last_result="NEEDS_CHANGE"),
        )
        path = _write_payload(self.tmpdir, _valid_payload(units=[unit]))
        r = paro.apply_transition(self.unit_id, "escalate",
                                  {"gate_result": "NEEDS_CHANGE"}, runtime_file=path)
        self.assertTrue(r.success)
        payload = json.loads(path.read_text(encoding="utf-8"))
        u = [x for x in payload["flow_units"] if x["flow_unit_id"] == self.unit_id][0]
        self.assertEqual(u["loop_state"]["last_gate_result"], u["gate_state"]["last_result"])


# ═══════════════════════════════════════════════════════════════════════════
# 8. Validator extension (additive)
# ═══════════════════════════════════════════════════════════════════════════


class ValidatorExtensionTests(unittest.TestCase):
    """validate_loop_runtime_v2_with_transitions enforces cas_version rules."""

    def _failures(self, payload, event_log=None):
        return flow_unit_runtime_v2.validate_loop_runtime_v2_with_transitions(
            payload, event_log=event_log,
        )

    def test_valid_active_unit_with_cas_version_passes(self):
        self.assertEqual(self._failures(_activated_payload()), [])

    def test_active_unit_without_cas_version_fails(self):
        payload = _activated_payload()
        # Strip cas_version from the active unit.
        del payload["flow_units"][0]["loop_state"]["cas_version"]
        failures = self._failures(payload)
        self.assertTrue(any("cas_version" in f and "required" in f for f in failures),
                        "expected cas_version-required failure; got: {0}".format(failures))

    def test_dormant_unit_without_cas_version_passes(self):
        # Dormant units may omit cas_version (write-once at migration).
        payload = _valid_payload(units=[_valid_unit(runtime_status="dormant")])
        self.assertEqual(self._failures(payload), [],
                         "dormant unit without cas_version should pass FEAT-005 extension")

    def test_cas_version_as_bool_fails(self):
        payload = _activated_payload()
        payload["flow_units"][0]["loop_state"]["cas_version"] = True
        failures = self._failures(payload)
        self.assertTrue(any("non-negative integer" in f and "not bool" in f for f in failures),
                        "expected cas_version-not-bool failure; got: {0}".format(failures))

    def test_cas_version_negative_fails(self):
        payload = _activated_payload()
        payload["flow_units"][0]["loop_state"]["cas_version"] = -1
        failures = self._failures(payload)
        self.assertTrue(any("non-negative integer" in f for f in failures))

    def test_without_event_log_skips_consistency_check(self):
        # An event_log=None must NOT add any transition/monotonicity failures
        # even if a (hypothetical) log would be inconsistent.
        payload = _activated_payload()
        self.assertEqual(self._failures(payload, event_log=None), [])

    def test_event_log_monotonicity_violation_detected(self):
        payload = _activated_payload()
        unit_id = payload["flow_units"][0]["flow_unit_id"]
        # cas_version jumps 0 → 5 (skips 1,2,3,4): monotonicity violation.
        event_log = [
            {"unit_id": unit_id, "to_phase": "plan", "cas_version": 0},
            {"unit_id": unit_id, "from_phase": "plan", "to_phase": "act", "cas_version": 5},
        ]
        failures = self._failures(payload, event_log=event_log)
        self.assertTrue(any("monotonic" in f for f in failures),
                        "expected monotonicity failure; got: {0}".format(failures))

    def test_event_log_illegal_transition_detected(self):
        payload = _activated_payload()
        unit_id = payload["flow_units"][0]["flow_unit_id"]
        # plan → observe is an illegal skip in the event log.
        event_log = [
            {"unit_id": unit_id, "to_phase": "plan", "cas_version": 0},
            {"unit_id": unit_id, "from_phase": "plan", "to_phase": "observe",
             "cas_version": 1},
        ]
        failures = self._failures(payload, event_log=event_log)
        self.assertTrue(any("illegal phase transition" in f for f in failures),
                        "expected illegal-transition failure; got: {0}".format(failures))

    def test_event_log_legal_replay_passes(self):
        payload = _activated_payload()
        unit_id = payload["flow_units"][0]["flow_unit_id"]
        event_log = [
            {"unit_id": unit_id, "to_phase": "plan", "cas_version": 0},
            {"unit_id": unit_id, "from_phase": "plan", "to_phase": "act", "cas_version": 1},
            {"unit_id": unit_id, "from_phase": "act", "to_phase": "observe", "cas_version": 2},
            {"unit_id": unit_id, "from_phase": "observe", "to_phase": "reflect",
             "cas_version": 3, "gate_result": "NEEDS_CHANGE"},
            {"unit_id": unit_id, "from_phase": "reflect", "to_phase": "plan",
             "cas_version": 4, "gate_result": "NEEDS_CHANGE",
             "loop_count": 0, "max_rounds": _TEST_MAX_ROUNDS},
        ]
        failures = self._failures(payload, event_log=event_log)
        self.assertEqual(failures, [], "legal replay should pass; got: {0}".format(failures))

    def test_0670_validator_still_runs_as_base(self):
        """The additive function still surfaces 0.67.0 failures (e.g. bad enum)."""
        payload = _activated_payload()
        payload["schema_version"] = "1.0"  # 0.67.0 base rejects this.
        failures = self._failures(payload)
        self.assertTrue(any("schema_version must be 2.0" in f for f in failures))


# ═══════════════════════════════════════════════════════════════════════════
# 9. Threading test — CAS correctness (no lost updates) [LOAD-BEARING]
# ═══════════════════════════════════════════════════════════════════════════


class ThreadingCASTests(unittest.TestCase):
    """Multiple threads apply_transition to the same unit → no lost updates.

    This is the LOAD-BEARING proof that the CAS mechanism is correct under
    concurrency (ADR-014 §3.5: "Two processes that both read cas_version=7 and
    both try to write: the second's write sees on-disk cas_version=8 ... and
    fails the conflict check ... No lost updates").

    Setup: N threads each try to advance a unit from plan→act. Because all N
    read cas=0 but only ONE can commit at cas=1 (the on-disk version check
    fails for the other N-1 after the first commit), the outcome is exactly:
      - exactly ONE thread gets STATUS_SUCCESS with new_cas_version=1;
      - the other N-1 get STATUS_CONFLICT;
      - the on-disk cas_version is exactly 1 (no lost update, no double bump).
    """

    def test_many_threads_one_success_rest_conflict(self):
        tmpdir = tempfile.mkdtemp(prefix="paro_thread_")
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"

        N = 12
        results = [None] * N
        barrier = threading.Barrier(N)

        def worker(idx):
            barrier.wait()  # release all threads simultaneously
            results[idx] = paro.apply_transition(
                unit_id, "act", {"reason": "thread-{0}".format(idx)},
                runtime_file=runtime_path,
            )

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        # All threads must have completed.
        self.assertEqual(results.count(None), 0, "a thread did not record a result")

        statuses = [r.status for r in results]
        successes = [r for r in results if r.status == paro.STATUS_SUCCESS]
        conflicts = [r for r in results if r.status == paro.STATUS_CONFLICT]

        self.assertEqual(len(successes), 1,
                         "exactly ONE thread must succeed; got {0} (statuses={1})".format(
                             len(successes), statuses))
        self.assertEqual(successes[0].new_cas_version, 1)
        self.assertEqual(len(conflicts), N - 1,
                         "the other {0} threads must CONFLICT; got {1}".format(
                             N - 1, len(conflicts)))

        # The on-disk version must be exactly 1 (one commit, no lost update,
        # no double-counted bump).
        payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        u = [x for x in payload["flow_units"] if x["flow_unit_id"] == unit_id][0]
        self.assertEqual(u["loop_state"]["cas_version"], 1,
                         "on-disk cas_version must be exactly 1 (no lost update)")
        self.assertEqual(u["loop_state"]["agent_phase"], "act")

    def test_distinct_transitions_under_contention_commit_each_once(self):
        """A serial chain driven under thread contention commits each step exactly once.

        Three threads concurrently attempt to advance the unit through
        plan→act→observe→reflect. Because the CAS lock serializes the critical
        sections and each ``apply_transition`` re-reads fresh state, the chain
        advances monotonically — cas_versions 1, 2, 3 are each committed exactly
        once, with no lost update and no double-application. Workers whose
        assigned transition was already committed by a faster peer observe
        ILLEGAL (their source phase has moved past) and bail cleanly.

        This is the load-bearing no-lost-update proof for DISTINCT transitions:
        the final on-disk state is ``reflect`` at ``cas_version == 3`` and the
        set of committed cas_versions is exactly ``{1, 2, 3}``.
        """
        tmpdir = tempfile.mkdtemp(prefix="paro_thread_")
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"

        # Each worker tries ONE specific transition, retrying on CONFLICT and
        # on transient ILLEGAL (its source phase hasn't been reached yet). It
        # gives up cleanly once the unit's phase has advanced PAST its target
        # (a faster peer already committed that step).
        plan = [
            ("act", {}),
            ("observe", {}),
            ("reflect", {"gate_result": "NEEDS_CHANGE"}),
        ]
        committed_versions = []
        versions_lock = threading.Lock()
        start_barrier = threading.Barrier(len(plan))

        def worker(to_phase, ev):
            import time
            order = {"plan": 0, "act": 1, "observe": 2, "reflect": 3}
            target_rank = order.get(to_phase, -1)
            start_barrier.wait()
            for _ in range(400):
                r = paro.apply_transition(unit_id, to_phase, ev,
                                          runtime_file=runtime_path,
                                          max_retries=8)
                if r.success:
                    with versions_lock:
                        committed_versions.append(r.new_cas_version)
                    return
                # Re-read the current phase to decide whether our target has
                # been overshot by a faster peer (permanent — bail) or whether
                # the ILLEGAL/CONFLICT/ERROR is transient (retry). ERROR can
                # surface on Windows when a concurrent read/write collides on
                # a file handle; it is transient under our CAS lock.
                try:
                    payload = json.loads(runtime_path.read_text(encoding="utf-8"))
                    cur = None
                    for u in payload.get("flow_units", []):
                        if u.get("flow_unit_id") == unit_id:
                            ls = u.get("loop_state") or {}
                            cur = ls.get("agent_phase")
                except (json.JSONDecodeError, OSError):
                    cur = None
                if cur is not None and order.get(cur, -1) >= target_rank:
                    return  # our target phase already reached/overshot: done.
                time.sleep(0.001)

        threads = [
            threading.Thread(target=worker, args=(to_phase, ev))
            for to_phase, ev in plan
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        # The load-bearing assertions: each of the three cas_versions committed
        # exactly once (no lost update, no double-application), and the final
        # on-disk state is the terminal phase of the chain.
        self.assertEqual(
            sorted(committed_versions), [1, 2, 3],
            "committed cas_versions must be exactly [1,2,3]; got {0}".format(
                sorted(committed_versions)),
        )
        payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        u = [x for x in payload["flow_units"] if x["flow_unit_id"] == unit_id][0]
        self.assertEqual(u["loop_state"]["agent_phase"], "reflect")
        self.assertEqual(u["loop_state"]["cas_version"], 3)


# ═══════════════════════════════════════════════════════════════════════════
# 10. side_effects callback hook (the FEAT-006 extension point)
# ═══════════════════════════════════════════════════════════════════════════


class SideEffectsHookTests(unittest.TestCase):
    """The side_effects callable lets FEAT-006 augment the committed unit."""

    def test_side_effects_callback_applied_and_cas_still_bumped(self):
        tmpdir = tempfile.mkdtemp(prefix="paro_test_")
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"

        def add_evidence(new_unit, event):
            new_unit["gate_state"]["evidence_refs"] = ["EV-001"]
            return new_unit

        r = paro.apply_transition(unit_id, "act", {"reason": "x"},
                                  runtime_file=runtime_path,
                                  side_effects=add_evidence)
        self.assertTrue(r.success)
        payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        u = [x for x in payload["flow_units"] if x["flow_unit_id"] == unit_id][0]
        self.assertEqual(u["gate_state"]["evidence_refs"], ["EV-001"])
        self.assertEqual(u["loop_state"]["cas_version"], 1)

    def test_side_effects_callback_raising_aborts_no_mutation(self):
        tmpdir = tempfile.mkdtemp(prefix="paro_test_")
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"
        before = runtime_path.read_bytes()

        def boom(new_unit, event):
            raise RuntimeError("intentional")

        r = paro.apply_transition(unit_id, "act", {}, runtime_file=runtime_path,
                                  side_effects=boom)
        self.assertEqual(r.status, paro.STATUS_ERROR)
        self.assertIn("intentional", r.reason)
        # No mutation committed.
        self.assertEqual(runtime_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
