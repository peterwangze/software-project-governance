"""Tests for the gate/review terminal processor (FEAT-006, ADR-014 §4).

These tests are the load-bearing verification for FEAT-006 — the production
gate back-edge/round/fuse/escalation chain (the AUDIT-133 "call sites = 0" fix).

Coverage (ADR-014 §8.3 + the task's required cases):

  - **Gate passed → exit**: ``process_gate_result`` with a passed result →
    ``decision="exit"``, ``gate_state.status="passed"``.
  - **Gate failed → iterate (back-edge)**: failed with ``loop_count < max_rounds``
    → ``decision="iterate"``, ``agent_phase="plan"``, ``loop_count++``.
  - **Gate failed → fuse trip**: failed with ``loop_count >= max_rounds`` →
    ``decision="escalate"``, ``fuse.tripped=true``, ``runtime_status=blocked``,
    escalation payload present.
  - **Back-edge atomicity**: ``reflect→plan`` + ``loop_count++`` + last-result
    update + round-evidence row in ONE CAS write (cas_version increments by
    exactly 1, all mutations present together).
  - **Round counting consistency**: ``derive_round(evidence_log) ==
    loop_state.loop_count`` after every back-edge.
  - **loop_fuse_check purity + cases**: returns tripped+blocked units; empty
    when no tripped fuses; does not return passed/resolved units; PURE READ
    (no mutation).
  - **System-level block**: ``loop_fuse_check`` integrated into the release
    gate → tripped fuse produces a gate issue (the "不依赖 Coordinator 自觉"
    guarantee).
  - **G1 escalate-directly**: G1 gate fail → escalate (not iterate).
  - **CAS conflict**: concurrent ``process_gate_result`` on the same unit →
    one succeeds, the other CONFLICT.
  - **Unification**: ``last_gate_result == gate_state.last_result`` after every
    ``process_gate_result``.
  - **v1 payload is a no-op**: a v1 (schema_version != "2.0") payload returns
    without mutating.
  - **End-to-end REL-060 chain**: gate fail → back-edge → round → fuse →
    escalation → system block (the single integration proof).

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_loop_gate_processor.py -v
"""

import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_INFRA_DIR))

import loop_engine  # noqa: E402  (pure: derive_round cross-check)
import loop_gate_processor as gp  # noqa: E402
import loop_paro_engine as paro  # noqa: E402
from checks import flow_unit_runtime_v2  # noqa: E402

# Reuse the FEAT-005 fixture builders so the v2 payload shapes stay in sync
# with the canonical FEAT-005 test suite (single source of truth for the shape).
from tests.test_loop_paro_engine import (  # noqa: E402
    _VALID_PLAN_HASH,
    _TEST_MAX_ROUNDS,
    _dormant_loop_state,
    _active_loop_state,
    _valid_gate_state,
    _valid_unit,
    _valid_payload,
    _write_payload,
    _activated_payload,
)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _drive_to_reflect(unit_id, runtime_path):
    """Drive an activated unit plan→act→observe→reflect (the forward chain).

    Uses the FEAT-005 CAS writer directly so the unit reaches the reflect node
    where ``process_gate_result`` consumes a gate result. Each step must commit.
    """
    for to_phase, event in [
        ("act", {"reason": "plan accepted"}),
        ("observe", {"reason": "action complete"}),
        ("reflect", {"gate_result": "NEEDS_CHANGE", "reason": "review recorded"}),
    ]:
        r = paro.apply_transition(unit_id, to_phase, event, runtime_file=runtime_path)
        assert r.success, "forward {0} failed: {1}".format(to_phase, r.reason)


def _unit_on_disk(unit_id, runtime_path):
    """Return the unit dict for ``unit_id`` read fresh from disk."""
    payload = json.loads(Path(runtime_path).read_text(encoding="utf-8"))
    for u in payload["flow_units"]:
        if u["flow_unit_id"] == unit_id:
            return u
    raise AssertionError("unit {0!r} not on disk".format(unit_id))


def _new_reflect_unit(tmpdir, unit_id="shitu.story.Skeleton", tier="inner",
                      max_rounds=_TEST_MAX_ROUNDS, loop_count=0):
    """Build an activated unit, drive it to reflect, return (runtime_path, cas_before_gate).

    ``cas_before_gate`` is the cas_version at the reflect node (before any gate
    result is processed) — used to assert the back-edge bumps it by exactly 1.
    """
    payload = _activated_payload(unit_id=unit_id, tier=tier, max_rounds=max_rounds)
    runtime_path = _write_payload(tmpdir, payload)
    _drive_to_reflect(unit_id, runtime_path)
    cas_before = _unit_on_disk(unit_id, runtime_path)["loop_state"]["cas_version"]
    return runtime_path, cas_before


# ═══════════════════════════════════════════════════════════════════════════
# 1. Gate passed → exit
# ═══════════════════════════════════════════════════════════════════════════


class GatePassedExitTests(unittest.TestCase):
    """A passed gate result drives loop_exit; gate_state.status=passed."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="gp_pass_")
        self.unit_id = "shitu.story.Skeleton"

    def test_approved_drives_exit(self):
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id)
        o = gp.process_gate_result(
            self.unit_id, "G6", "APPROVED",
            evidence_ref="review-code-Skeleton-R1.md", actor="code-reviewer-agent",
            runtime_file=runtime_path,
        )
        self.assertTrue(o.success, o.reason)
        self.assertEqual(o.decision, gp.DECISION_EXIT)
        self.assertFalse(o.fuse_tripped)
        self.assertIsNone(o.escalation_payload)
        u = _unit_on_disk(self.unit_id, runtime_path)
        self.assertEqual(u["gate_state"]["status"], "passed")

    def test_approved_with_notes_also_passes(self):
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id)
        o = gp.process_gate_result(
            self.unit_id, "G6", "APPROVED_WITH_NOTES",
            evidence_ref="review-R1.md", actor="code-reviewer-agent",
            runtime_file=runtime_path,
        )
        self.assertEqual(o.decision, gp.DECISION_EXIT)
        u = _unit_on_disk(self.unit_id, runtime_path)
        self.assertEqual(u["gate_state"]["status"], "passed")

    def test_passed_does_not_increment_loop_count(self):
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, tier="inner")
        before = _unit_on_disk(self.unit_id, runtime_path)["loop_state"]["loop_count"]
        gp.process_gate_result(
            self.unit_id, "G6", "APPROVED",
            evidence_ref="r", actor="cr", runtime_file=runtime_path,
        )
        after = _unit_on_disk(self.unit_id, runtime_path)["loop_state"]["loop_count"]
        self.assertEqual(after, before, "exit must not increment loop_count")

    def test_exit_emits_gate_result_and_loop_exit_events(self):
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id)
        o = gp.process_gate_result(
            self.unit_id, "G6", "APPROVED",
            evidence_ref="r", actor="cr", runtime_file=runtime_path,
        )
        types = [e["event_type"] for e in o.events]
        self.assertIn("gate_result", types)
        self.assertIn("loop_exit", types)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Gate failed → iterate (back-edge)
# ═══════════════════════════════════════════════════════════════════════════


class GateFailedIterateTests(unittest.TestCase):
    """A failed gate result with loop_count < max_rounds drives the back-edge."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="gp_iter_")
        self.unit_id = "shitu.story.Skeleton"

    def test_failed_drives_back_edge_to_plan(self):
        # loop_count=0, max_rounds=3 → 0 < 3 → iterate.
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, max_rounds=3)
        o = gp.process_gate_result(
            self.unit_id, "G6", "NEEDS_CHANGE",
            evidence_ref="review-R1.md", actor="code-reviewer-agent",
            runtime_file=runtime_path,
        )
        self.assertTrue(o.success, o.reason)
        self.assertEqual(o.decision, gp.DECISION_ITERATE)
        self.assertEqual(o.new_agent_phase, "plan")
        self.assertEqual(o.new_loop_count, 1)
        self.assertFalse(o.fuse_tripped)
        u = _unit_on_disk(self.unit_id, runtime_path)
        self.assertEqual(u["loop_state"]["agent_phase"], "plan")
        self.assertEqual(u["loop_state"]["loop_count"], 1)

    def test_iterate_increments_loop_count_by_exactly_one(self):
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, max_rounds=5)
        gp.process_gate_result(
            self.unit_id, "G6", "NEEDS_CHANGE",
            evidence_ref="r", actor="cr", runtime_file=runtime_path,
        )
        u = _unit_on_disk(self.unit_id, runtime_path)
        self.assertEqual(u["loop_state"]["loop_count"], 1)
        # Second iterate (drive back to reflect, fail again).
        _drive_to_reflect(self.unit_id, runtime_path)
        gp.process_gate_result(
            self.unit_id, "G6", "NEEDS_CHANGE",
            evidence_ref="r2", actor="cr", runtime_file=runtime_path,
        )
        u = _unit_on_disk(self.unit_id, runtime_path)
        self.assertEqual(u["loop_state"]["loop_count"], 2)

    def test_iterate_at_loop_count_eq_max_still_iterates(self):
        # §3.3 rule 2 / C5: round == max is STILL iterate (one more allowed).
        # Build a unit already at loop_count == max_rounds sitting at reflect.
        unit = _valid_unit(
            unit_id=self.unit_id, runtime_status="active",
            loop_state=_active_loop_state(
                agent_phase="reflect", loop_count=3, cas_version=2,
                last_gate_result="NEEDS_CHANGE", tier="inner", max_rounds=3),
            gate_state=_valid_gate_state(status="failed", last_result="NEEDS_CHANGE"),
        )
        runtime_path = _write_payload(self.tmpdir, _valid_payload(units=[unit]))
        o = gp.process_gate_result(
            self.unit_id, "G6", "NEEDS_CHANGE",
            evidence_ref="r", actor="cr", runtime_file=runtime_path,
        )
        self.assertTrue(o.success, o.reason)
        self.assertEqual(o.decision, gp.DECISION_ITERATE, "loop_count==max must iterate")
        self.assertEqual(o.new_loop_count, 4)

    def test_iterate_emits_gate_result_and_back_edge_events(self):
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, max_rounds=5)
        o = gp.process_gate_result(
            self.unit_id, "G6", "NEEDS_CHANGE",
            evidence_ref="r", actor="cr", runtime_file=runtime_path,
        )
        types = [e["event_type"] for e in o.events]
        self.assertIn("gate_result", types)
        self.assertIn("back_edge", types)
        # The back_edge event carries the new loop count + tier.
        be = next(e for e in o.events if e["event_type"] == "back_edge")
        self.assertEqual(be["payload"]["new_loop_count"], 1)
        self.assertEqual(be["payload"]["tier"], "inner")


# ═══════════════════════════════════════════════════════════════════════════
# 3. Gate failed → fuse trip
# ═══════════════════════════════════════════════════════════════════════════


class GateFailedFuseTripTests(unittest.TestCase):
    """A failed gate result with loop_count > max_rounds trips the fuse."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="gp_fuse_")
        self.unit_id = "shitu.story.Skeleton"

    def test_fuse_trips_at_loop_count_gt_max(self):
        # loop_count=4 > max_rounds=3 → fuse trip on this failure.
        unit = _valid_unit(
            unit_id=self.unit_id, runtime_status="active",
            loop_state=_active_loop_state(
                agent_phase="reflect", loop_count=4, cas_version=2,
                last_gate_result="NEEDS_CHANGE", tier="inner", max_rounds=3),
            gate_state=_valid_gate_state(status="failed", last_result="NEEDS_CHANGE"),
        )
        runtime_path = _write_payload(self.tmpdir, _valid_payload(units=[unit]))
        o = gp.process_gate_result(
            self.unit_id, "G6", "NEEDS_CHANGE",
            evidence_ref="review-Rfinal.md", actor="code-reviewer-agent",
            runtime_file=runtime_path,
        )
        self.assertTrue(o.success, o.reason)
        self.assertEqual(o.decision, gp.DECISION_ESCALATE)
        self.assertTrue(o.fuse_tripped)
        self.assertIsNotNone(o.escalation_payload)
        # 4 escalation options (the sacred M7.4 §4.6 C3/C4 set).
        self.assertEqual(len(o.escalation_payload["options"]), 4)
        u = _unit_on_disk(self.unit_id, runtime_path)
        self.assertTrue(u["loop_state"]["fuse"]["tripped"])
        self.assertEqual(u["runtime_status"], "blocked")
        self.assertEqual(u["gate_state"]["status"], "blocked")

    def test_fuse_trip_emits_gate_result_and_fuse_trip_events(self):
        unit = _valid_unit(
            unit_id=self.unit_id, runtime_status="active",
            loop_state=_active_loop_state(
                agent_phase="reflect", loop_count=4, cas_version=2,
                last_gate_result="NEEDS_CHANGE", tier="inner", max_rounds=3),
            gate_state=_valid_gate_state(status="failed", last_result="NEEDS_CHANGE"),
        )
        runtime_path = _write_payload(self.tmpdir, _valid_payload(units=[unit]))
        o = gp.process_gate_result(
            self.unit_id, "G6", "NEEDS_CHANGE",
            evidence_ref="r", actor="cr", runtime_file=runtime_path,
        )
        types = [e["event_type"] for e in o.events]
        self.assertIn("gate_result", types)
        self.assertIn("fuse_trip", types)
        ft = next(e for e in o.events if e["event_type"] == "fuse_trip")
        self.assertEqual(ft["payload"]["max_rounds"], 3)


# ═══════════════════════════════════════════════════════════════════════════
# 4. Back-edge atomicity
# ═══════════════════════════════════════════════════════════════════════════


class BackEdgeAtomicityTests(unittest.TestCase):
    """The back-edge (reflect→plan + loop_count++ + last-result + round row) is ONE CAS write."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="gp_atomic_")
        self.unit_id = "shitu.story.Skeleton"

    def test_back_edge_bumps_cas_version_by_exactly_one(self):
        runtime_path, cas_before = _new_reflect_unit(
            self.tmpdir, self.unit_id, max_rounds=5)
        o = gp.process_gate_result(
            self.unit_id, "G6", "NEEDS_CHANGE",
            evidence_ref="r", actor="cr", runtime_file=runtime_path,
        )
        self.assertTrue(o.success)
        self.assertEqual(o.cas_version, cas_before + 1,
                         "back-edge must bump cas_version by exactly 1")
        u = _unit_on_disk(self.unit_id, runtime_path)
        self.assertEqual(u["loop_state"]["cas_version"], cas_before + 1)

    def test_back_edge_all_mutations_present_together(self):
        # A reader sees ALL of: agent_phase=plan, loop_count+1, last_result set,
        # evidence_ref appended, round-evidence row — never a partial subset.
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, max_rounds=5)
        gp.process_gate_result(
            self.unit_id, "G6", "NEEDS_CHANGE",
            evidence_ref="review-atomic.md", actor="cr",
            runtime_file=runtime_path,
        )
        u = _unit_on_disk(self.unit_id, runtime_path)
        ls = u["loop_state"]
        gs = u["gate_state"]
        # All four mutations present.
        self.assertEqual(ls["agent_phase"], "plan")
        self.assertEqual(ls["loop_count"], 1)
        self.assertEqual(ls["last_gate_result"], "NEEDS_CHANGE")
        self.assertEqual(gs["last_result"], "NEEDS_CHANGE")
        self.assertIn("review-atomic.md", gs["evidence_refs"])
        # The round-evidence row (§4.3 dual representation).
        self.assertIn("LOOP-shitu.story.Skeleton-inner-R1",
                      ls.get("round_evidence", []))


# ═══════════════════════════════════════════════════════════════════════════
# 5. Round counting consistency (derive_round == loop_count)
# ═══════════════════════════════════════════════════════════════════════════


class RoundCountingConsistencyTests(unittest.TestCase):
    """derive_round(evidence_log) == loop_state.loop_count after every back-edge."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="gp_round_")
        self.unit_id = "shitu.story.Skeleton"

    def _assert_derive_round_matches(self, runtime_path, tier="inner"):
        u = _unit_on_disk(self.unit_id, runtime_path)
        rows = u["loop_state"].get("round_evidence", [])
        derived = loop_engine.derive_round(self.unit_id, tier, rows)
        self.assertEqual(
            derived, u["loop_state"]["loop_count"],
            "derive_round ({0}) != loop_state.loop_count ({1}) — dual representation diverged".format(
                derived, u["loop_state"]["loop_count"]))

    def test_consistency_holds_across_three_iterates(self):
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, max_rounds=5)
        for i in range(1, 4):
            gp.process_gate_result(
                self.unit_id, "G6", "NEEDS_CHANGE",
                evidence_ref="r{0}".format(i), actor="cr",
                runtime_file=runtime_path,
            )
            self._assert_derive_round_matches(runtime_path)
            if i < 3:
                _drive_to_reflect(self.unit_id, runtime_path)

    def test_consistency_holds_at_fuse_trip(self):
        # Drive iterates until the fuse trips, then assert consistency still holds
        # (the iterate that pushed loop_count past max wrote its row; the trip
        # does not write a new row, so derive_round and loop_count agree).
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, max_rounds=2)
        o = None
        # max_rounds=2 → iterates at counts 1, 2, 3; trip at count=3 > 2.
        for i in range(1, 5):
            o = gp.process_gate_result(
                self.unit_id, "G6", "NEEDS_CHANGE",
                evidence_ref="r{0}".format(i), actor="cr",
                runtime_file=runtime_path,
            )
            self._assert_derive_round_matches(runtime_path)
            if o.decision == gp.DECISION_ESCALATE:
                break
            _drive_to_reflect(self.unit_id, runtime_path)
        self.assertEqual(o.decision, gp.DECISION_ESCALATE)
        self.assertTrue(o.fuse_tripped)
        self._assert_derive_round_matches(runtime_path)


# ═══════════════════════════════════════════════════════════════════════════
# 6. loop_fuse_check — the §4.4 system-level block (PURE READ)
# ═══════════════════════════════════════════════════════════════════════════


class LoopFuseCheckTests(unittest.TestCase):
    """loop_fuse_check returns unresolved tripped fuses; PURE READ."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="gp_fusecheck_")
        self.unit_id = "shitu.story.Skeleton"

    def _payload_with_unit(self, unit):
        runtime_path = Path(self.tmpdir) / "flow-unit-runtime.json"
        runtime_path.write_text(
            json.dumps(_valid_payload(units=[unit]), ensure_ascii=False,
                       sort_keys=True, indent=2),
            encoding="utf-8")
        return runtime_path

    def test_empty_when_no_tripped_fuses(self):
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, max_rounds=5)
        self.assertEqual(gp.loop_fuse_check(runtime_file=runtime_path), [])

    def test_empty_when_runtime_missing(self):
        missing = Path(self.tmpdir) / "absent.json"
        self.assertEqual(gp.loop_fuse_check(runtime_file=missing), [])

    def test_returns_tripped_and_blocked_unit(self):
        unit = _valid_unit(
            unit_id=self.unit_id, runtime_status="blocked",
            loop_state=_active_loop_state(
                agent_phase="reflect", loop_count=6, cas_version=4,
                last_gate_result="NEEDS_CHANGE", tier="inner", max_rounds=5,
                fuse_tripped=True),
            gate_state=_valid_gate_state(status="blocked", last_result="NEEDS_CHANGE"),
        )
        runtime_path = self._payload_with_unit(unit)
        tripped = gp.loop_fuse_check(runtime_file=runtime_path)
        self.assertEqual(len(tripped), 1)
        self.assertEqual(tripped[0]["unit_id"], self.unit_id)
        self.assertEqual(tripped[0]["loop_count"], 6)
        self.assertEqual(tripped[0]["max_rounds"], 5)
        self.assertEqual(tripped[0]["tier"], "inner")
        self.assertEqual(tripped[0]["runtime_status"], "blocked")

    def test_returns_tripped_and_escalated_unit(self):
        # runtime_status="escalated" (post-human-action) is also unresolved.
        unit = _valid_unit(
            unit_id=self.unit_id, runtime_status="escalated",
            loop_state=_active_loop_state(
                agent_phase="reflect", loop_count=6, cas_version=4,
                last_gate_result="NEEDS_CHANGE", tier="inner", max_rounds=5,
                fuse_tripped=True),
            gate_state=_valid_gate_state(status="escalated", last_result="NEEDS_CHANGE"),
        )
        runtime_path = self._payload_with_unit(unit)
        tripped = gp.loop_fuse_check(runtime_file=runtime_path)
        self.assertEqual(len(tripped), 1)

    def test_does_not_return_resolved_withdrawn_unit(self):
        # A withdrawn unit (human resolved the escalation by withdrawing) is
        # resolved — it must NOT appear in the blocking set.
        unit = _valid_unit(
            unit_id=self.unit_id, runtime_status="withdrawn",
            loop_state=_active_loop_state(
                agent_phase="reflect", loop_count=6, cas_version=4,
                last_gate_result="NEEDS_CHANGE", tier="inner", max_rounds=5,
                fuse_tripped=True),
            gate_state=_valid_gate_state(status="withdrawn", last_result="NEEDS_CHANGE"),
        )
        runtime_path = self._payload_with_unit(unit)
        self.assertEqual(gp.loop_fuse_check(runtime_file=runtime_path), [])

    def test_does_not_return_passed_unit(self):
        # A passed unit (gate_state.status=passed, runtime active) has no tripped
        # fuse — not in the blocking set.
        unit = _valid_unit(
            unit_id=self.unit_id, runtime_status="active",
            loop_state=_active_loop_state(
                agent_phase="reflect", loop_count=1, cas_version=4,
                last_gate_result="APPROVED", tier="inner", max_rounds=5,
                fuse_tripped=False),
            gate_state=_valid_gate_state(status="passed", last_result="APPROVED"),
        )
        runtime_path = self._payload_with_unit(unit)
        self.assertEqual(gp.loop_fuse_check(runtime_file=runtime_path), [])

    def test_does_not_return_tripped_but_active_unit(self):
        # A unit that somehow has fuse.tripped=true but runtime_status="active"
        # (an inconsistent state) is NOT blocking per §4.4 (only blocked/
        # escalated are). This is defensive — process_gate_result never leaves
        # a unit in this state, but the read must not over-block.
        unit = _valid_unit(
            unit_id=self.unit_id, runtime_status="active",
            loop_state=_active_loop_state(
                agent_phase="reflect", loop_count=6, cas_version=4,
                last_gate_result="NEEDS_CHANGE", tier="inner", max_rounds=5,
                fuse_tripped=True),
            gate_state=_valid_gate_state(status="failed", last_result="NEEDS_CHANGE"),
        )
        runtime_path = self._payload_with_unit(unit)
        self.assertEqual(gp.loop_fuse_check(runtime_file=runtime_path), [])

    def test_pure_read_does_not_mutate(self):
        # loop_fuse_check MUST NOT mutate the runtime file. Capture the file's
        # bytes before and after; they must be byte-identical.
        unit = _valid_unit(
            unit_id=self.unit_id, runtime_status="blocked",
            loop_state=_active_loop_state(
                agent_phase="reflect", loop_count=6, cas_version=4,
                last_gate_result="NEEDS_CHANGE", tier="inner", max_rounds=5,
                fuse_tripped=True),
            gate_state=_valid_gate_state(status="blocked", last_result="NEEDS_CHANGE"),
        )
        runtime_path = self._payload_with_unit(unit)
        before = runtime_path.read_bytes()
        tripped = gp.loop_fuse_check(runtime_file=runtime_path)
        after = runtime_path.read_bytes()
        self.assertEqual(len(tripped), 1)
        self.assertEqual(before, after, "loop_fuse_check mutated the runtime file (not pure read)")

    def test_pure_read_does_not_mutate_across_multiple_calls(self):
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, max_rounds=5)
        before = runtime_path.read_bytes()
        for _ in range(5):
            gp.loop_fuse_check(runtime_file=runtime_path)
        self.assertEqual(runtime_path.read_bytes(), before)

    def test_v1_payload_returns_empty(self):
        # A v1 (schema_version != "2.0") payload has no per-unit fuse state.
        v1_path = Path(self.tmpdir) / "v1.json"
        v1_path.write_text(
            json.dumps({"schema_version": "1.0", "flow_units": []},
                       ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8")
        self.assertEqual(gp.loop_fuse_check(runtime_file=v1_path), [])


# ═══════════════════════════════════════════════════════════════════════════
# 7. System-level block — loop_fuse_check integrated into the release gate
# ═══════════════════════════════════════════════════════════════════════════


class SystemLevelFuseBlockTests(unittest.TestCase):
    """A tripped fuse produces a release-gate issue (不依赖 Coordinator 自觉).

    This tests the integration: the release gate calls loop_fuse_check and adds
    an issue per unresolved tripped fuse. We invoke the same helper the
    verify_workflow wiring uses (``_collect_loop_fuse_issues``) so the test
    exercises the real production path, not a re-implementation.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="gp_sysblock_")
        self.unit_id = "shitu.story.Skeleton"

    def test_tripped_fuse_produces_gate_issue(self):
        unit = _valid_unit(
            unit_id=self.unit_id, runtime_status="blocked",
            loop_state=_active_loop_state(
                agent_phase="reflect", loop_count=6, cas_version=4,
                last_gate_result="NEEDS_CHANGE", tier="inner", max_rounds=5,
                fuse_tripped=True),
            gate_state=_valid_gate_state(status="blocked", last_result="NEEDS_CHANGE"),
        )
        runtime_path = Path(self.tmpdir) / "flow-unit-runtime.json"
        runtime_path.write_text(
            json.dumps(_valid_payload(units=[unit]), ensure_ascii=False,
                       sort_keys=True, indent=2),
            encoding="utf-8")
        # The production wiring helper (re-exported from loop_gate_processor so
        # verify_workflow and this test share one implementation).
        issues = gp.collect_loop_fuse_issues(runtime_file=runtime_path)
        self.assertEqual(len(issues), 1)
        self.assertIn(self.unit_id, issues[0])
        self.assertIn("fuse", issues[0].lower())

    def test_no_tripped_fuse_produces_no_issue(self):
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, max_rounds=5)
        issues = gp.collect_loop_fuse_issues(runtime_file=runtime_path)
        self.assertEqual(issues, [])

    def test_resolved_fuse_produces_no_issue(self):
        unit = _valid_unit(
            unit_id=self.unit_id, runtime_status="withdrawn",
            loop_state=_active_loop_state(
                agent_phase="reflect", loop_count=6, cas_version=4,
                last_gate_result="NEEDS_CHANGE", tier="inner", max_rounds=5,
                fuse_tripped=True),
            gate_state=_valid_gate_state(status="withdrawn", last_result="NEEDS_CHANGE"),
        )
        runtime_path = Path(self.tmpdir) / "flow-unit-runtime.json"
        runtime_path.write_text(
            json.dumps(_valid_payload(units=[unit]), ensure_ascii=False,
                       sort_keys=True, indent=2),
            encoding="utf-8")
        self.assertEqual(gp.collect_loop_fuse_issues(runtime_file=runtime_path), [])


# ═══════════════════════════════════════════════════════════════════════════
# 8. G1 escalate-directly
# ═══════════════════════════════════════════════════════════════════════════


class G1EscalateDirectlyTests(unittest.TestCase):
    """G1 (on_fail=escalate-directly) fail → escalate, NOT iterate."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="gp_g1_")
        self.unit_id = "shitu.story.Skeleton"

    def test_g1_failed_escalates_directly(self):
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, max_rounds=5)
        o = gp.process_gate_result(
            self.unit_id, "G1", "NEEDS_CHANGE",
            evidence_ref="initiation-R1.md", actor="requirement-reviewer",
            runtime_file=runtime_path,
        )
        self.assertTrue(o.success, o.reason)
        self.assertEqual(o.decision, gp.DECISION_ESCALATE)
        # G1 escalate-directly is NOT a fuse trip (no round exhaustion).
        self.assertFalse(o.fuse_tripped)
        self.assertIsNone(o.escalation_payload)
        u = _unit_on_disk(self.unit_id, runtime_path)
        self.assertEqual(u["runtime_status"], "blocked")
        # The fuse is NOT tripped (this is an operator/direct escalate, not round exhaustion).
        self.assertFalse(u["loop_state"]["fuse"]["tripped"])

    def test_g1_does_not_increment_loop_count(self):
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, max_rounds=5)
        before = _unit_on_disk(self.unit_id, runtime_path)["loop_state"]["loop_count"]
        gp.process_gate_result(
            self.unit_id, "G1", "NEEDS_CHANGE",
            evidence_ref="r", actor="cr", runtime_file=runtime_path,
        )
        after = _unit_on_disk(self.unit_id, runtime_path)["loop_state"]["loop_count"]
        self.assertEqual(after, before, "G1 escalate-directly must not iterate")

    def test_g1_emits_unit_blocked_event(self):
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, max_rounds=5)
        o = gp.process_gate_result(
            self.unit_id, "G1", "NEEDS_CHANGE",
            evidence_ref="r", actor="cr", runtime_file=runtime_path,
        )
        types = [e["event_type"] for e in o.events]
        self.assertIn("unit_blocked", types)


# ═══════════════════════════════════════════════════════════════════════════
# 9. CAS conflict — concurrent process_gate_result on the same unit
# ═══════════════════════════════════════════════════════════════════════════


class CASConflictTests(unittest.TestCase):
    """Two concurrent process_gate_result calls on the same unit: one wins, one CONFLICTs."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="gp_cas_")
        self.unit_id = "shitu.story.Skeleton"

    def test_concurrent_calls_one_succeeds_one_conflicts(self):
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, max_rounds=5)
        results = []
        barrier = threading.Barrier(2)

        def worker():
            barrier.wait()  # release both threads simultaneously
            o = gp.process_gate_result(
                self.unit_id, "G6", "NEEDS_CHANGE",
                evidence_ref="r", actor="cr",
                runtime_file=runtime_path, max_retries=0,
            )
            results.append(o.status)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly one SUCCESS; the other CONFLICT (no lost updates). The unit's
        # cas_version advanced by exactly 1 (one commit), not 2.
        self.assertEqual(results.count(paro.STATUS_SUCCESS), 1, results)
        self.assertEqual(results.count(paro.STATUS_CONFLICT), 1, results)
        u = _unit_on_disk(self.unit_id, runtime_path)
        self.assertEqual(u["loop_state"]["loop_count"], 1,
                         "concurrent race must produce exactly one iterate")

    def test_conflict_does_not_mutate(self):
        # A CONFLICT writes nothing — the on-disk state is whatever the winner
        # committed. Verified above by loop_count==1; here we assert the loser's
        # outcome carries no committed cas_version.
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, max_rounds=5)
        outcomes = []
        barrier = threading.Barrier(2)

        def worker():
            barrier.wait()
            outcomes.append(gp.process_gate_result(
                self.unit_id, "G6", "NEEDS_CHANGE",
                evidence_ref="r", actor="cr",
                runtime_file=runtime_path, max_retries=0,
            ))

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        loser = next(o for o in outcomes if o.status == paro.STATUS_CONFLICT)
        self.assertIsNone(loser.cas_version, "CONFLICT must not report a committed cas_version")


# ═══════════════════════════════════════════════════════════════════════════
# 10. Unification invariant
# ═══════════════════════════════════════════════════════════════════════════


class UnificationInvariantTests(unittest.TestCase):
    """last_gate_result == gate_state.last_result after every process_gate_result."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="gp_unify_")
        self.unit_id = "shitu.story.Skeleton"

    def _assert_unified(self, runtime_path):
        u = _unit_on_disk(self.unit_id, runtime_path)
        self.assertEqual(
            u["loop_state"]["last_gate_result"], u["gate_state"]["last_result"],
            "unification violated: last_gate_result={0!r} gate.last_result={1!r}".format(
                u["loop_state"]["last_gate_result"], u["gate_state"]["last_result"]))

    def test_unification_holds_on_iterate(self):
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, max_rounds=5)
        gp.process_gate_result(
            self.unit_id, "G6", "NEEDS_CHANGE",
            evidence_ref="r", actor="cr", runtime_file=runtime_path,
        )
        self._assert_unified(runtime_path)

    def test_unification_holds_on_exit(self):
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, max_rounds=5)
        gp.process_gate_result(
            self.unit_id, "G6", "APPROVED",
            evidence_ref="r", actor="cr", runtime_file=runtime_path,
        )
        self._assert_unified(runtime_path)

    def test_unification_holds_on_fuse_trip(self):
        unit = _valid_unit(
            unit_id=self.unit_id, runtime_status="active",
            loop_state=_active_loop_state(
                agent_phase="reflect", loop_count=4, cas_version=2,
                last_gate_result="NEEDS_CHANGE", tier="inner", max_rounds=3),
            gate_state=_valid_gate_state(status="failed", last_result="NEEDS_CHANGE"),
        )
        runtime_path = _write_payload(self.tmpdir, _valid_payload(units=[unit]))
        gp.process_gate_result(
            self.unit_id, "G6", "NEEDS_CHANGE",
            evidence_ref="r", actor="cr", runtime_file=runtime_path,
        )
        self._assert_unified(runtime_path)

    def test_unification_holds_on_g1_escalate_directly(self):
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, max_rounds=5)
        gp.process_gate_result(
            self.unit_id, "G1", "NEEDS_CHANGE",
            evidence_ref="r", actor="cr", runtime_file=runtime_path,
        )
        self._assert_unified(runtime_path)


# ═══════════════════════════════════════════════════════════════════════════
# 11. v1 payload is a no-op + edge cases
# ═══════════════════════════════════════════════════════════════════════════


class V1PayloadAndEdgeCaseTests(unittest.TestCase):
    """A v1 payload (schema_version != "2.0") is a no-op; dormant/error handling."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="gp_v1_")
        self.unit_id = "shitu.story.Skeleton"

    def test_v1_payload_is_noop(self):
        v1_path = Path(self.tmpdir) / "flow-unit-runtime.json"
        v1_path.write_text(
            json.dumps({
                "schema_version": "1.0", "runtime_contract": "legacy",
                "flow_units": [{
                    "flow_unit_id": self.unit_id, "runtime_status": "active",
                    "loop_state": {}, "gate_state": {},
                }],
            }, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8")
        before = v1_path.read_bytes()
        o = gp.process_gate_result(
            self.unit_id, "G6", "NEEDS_CHANGE",
            evidence_ref="r", actor="cr", runtime_file=v1_path,
        )
        self.assertNotEqual(o.status, paro.STATUS_SUCCESS)
        self.assertEqual(v1_path.read_bytes(), before, "v1 payload must not be mutated")

    def test_dormant_unit_rejected(self):
        # A dormant unit (runtime_status != "active") has no gate events.
        payload = _valid_payload(units=[
            _valid_unit(unit_id=self.unit_id, runtime_status="dormant",
                        loop_state=_dormant_loop_state())
        ])
        runtime_path = _write_payload(self.tmpdir, payload)
        o = gp.process_gate_result(
            self.unit_id, "G6", "NEEDS_CHANGE",
            evidence_ref="r", actor="cr", runtime_file=runtime_path,
        )
        self.assertNotEqual(o.status, paro.STATUS_SUCCESS)

    def test_missing_unit_rejected(self):
        payload = _valid_payload(units=[
            _valid_unit(unit_id="other.unit", runtime_status="active",
                        loop_state=_active_loop_state())
        ])
        runtime_path = _write_payload(self.tmpdir, payload)
        o = gp.process_gate_result(
            "absent.unit", "G6", "NEEDS_CHANGE",
            evidence_ref="r", actor="cr", runtime_file=runtime_path,
        )
        self.assertEqual(o.status, paro.STATUS_ERROR)

    def test_missing_runtime_file_rejected(self):
        missing = Path(self.tmpdir) / "absent.json"
        o = gp.process_gate_result(
            self.unit_id, "G6", "NEEDS_CHANGE",
            evidence_ref="r", actor="cr", runtime_file=missing,
        )
        self.assertEqual(o.status, paro.STATUS_ERROR)

    def test_unknown_gate_id_rejected(self):
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, max_rounds=5)
        o = gp.process_gate_result(
            self.unit_id, "G999", "NEEDS_CHANGE",
            evidence_ref="r", actor="cr", runtime_file=runtime_path,
        )
        self.assertNotEqual(o.status, paro.STATUS_SUCCESS)


# ═══════════════════════════════════════════════════════════════════════════
# 12. Registry semantics consumed (FEAT-006 reads the registry, not hard-coded)
# ═══════════════════════════════════════════════════════════════════════════


class RegistrySemanticsConsumedTests(unittest.TestCase):
    """process_gate_result reads loop_gate_semantics[gate_id] for tier/on_fail/fuse_ref."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="gp_registry_")
        self.unit_id = "shitu.story.Skeleton"

    def test_g6_uses_inner_tier_in_round_evidence(self):
        # G6 enclosing_loop=inner → the round-evidence row uses tier "inner".
        runtime_path, _ = _new_reflect_unit(self.tmpdir, self.unit_id, tier="inner",
                                            max_rounds=5)
        gp.process_gate_result(
            self.unit_id, "G6", "NEEDS_CHANGE",
            evidence_ref="r", actor="cr", runtime_file=runtime_path,
        )
        u = _unit_on_disk(self.unit_id, runtime_path)
        self.assertIn("LOOP-{0}-inner-R1".format(self.unit_id),
                      u["loop_state"].get("round_evidence", []))

    def test_gate_semantics_lookup_returns_tier_on_fail_fuse_ref(self):
        tier, on_fail, fuse_ref, issue = gp._gate_semantics("G6", None)
        self.assertIsNone(issue)
        self.assertEqual(tier, "inner")
        self.assertEqual(on_fail, "iterate-enclosing-loop")
        self.assertEqual(fuse_ref, "FUSE-INNER-DEFAULT")

    def test_g1_semantics_are_escalate_directly(self):
        tier, on_fail, fuse_ref, issue = gp._gate_semantics("G1", None)
        self.assertIsNone(issue)
        self.assertEqual(on_fail, "escalate-directly")
        self.assertEqual(fuse_ref, "none")


# ═══════════════════════════════════════════════════════════════════════════
# 13. End-to-end REL-060 chain (the single integration proof)
# ═══════════════════════════════════════════════════════════════════════════


class EndToEndRel060ChainTests(unittest.TestCase):
    """THE REL-060 integration test: gate fail → back-edge → round → fuse → escalation → system block.

    Fixture: an active unit at Inner tier with max_rounds=2. Drive consecutive
    failed gate results via process_gate_result. Assert: the first iterates
    produce back-edges (loop_count increments; agent_phase cycles reflect→plan);
    the final failure trips the fuse (fuse.tripped=true, runtime_status=blocked,
    fuse_trip event, escalation payload); the release-gate fuse check fails
    closed on the unresolved fuse; and derive_round == loop_count throughout.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="gp_e2e_")
        self.unit_id = "shitu.story.Skeleton"

    def test_end_to_end_gate_fail_to_escalation_and_system_block(self):
        runtime_path = _write_payload(
            self.tmpdir,
            _activated_payload(unit_id=self.unit_id, tier="inner", max_rounds=2))

        decisions = []
        for i in range(1, 6):
            _drive_to_reflect(self.unit_id, runtime_path)
            o = gp.process_gate_result(
                self.unit_id, "G6", "NEEDS_CHANGE",
                evidence_ref="review-R{0}.md".format(i), actor="code-reviewer-agent",
                runtime_file=runtime_path,
            )
            decisions.append(o.decision)
            # derive_round consistency after every transition.
            u = _unit_on_disk(self.unit_id, runtime_path)
            derived = loop_engine.derive_round(
                self.unit_id, "inner", u["loop_state"].get("round_evidence", []))
            self.assertEqual(derived, u["loop_state"]["loop_count"],
                             "round {0}: derive_round({1}) != loop_count({2})".format(
                                 i, derived, u["loop_state"]["loop_count"]))
            if o.decision == gp.DECISION_ESCALATE:
                # The fuse tripped — assert the full escalation state.
                self.assertTrue(o.fuse_tripped)
                self.assertIsNotNone(o.escalation_payload)
                self.assertEqual(u["runtime_status"], "blocked")
                self.assertTrue(u["loop_state"]["fuse"]["tripped"])
                break

        # Chain shape: iterates ... then escalate. With max_rounds=2 and the
        # FEAT-005 strict boundary (loop_count > max trips), iterates land at
        # counts 1, 2, 3 and the trip fires at count=3 (>2).
        self.assertIn(gp.DECISION_ITERATE, decisions)
        self.assertEqual(decisions[-1], gp.DECISION_ESCALATE,
                         "chain must end in escalate, got {0}".format(decisions))

        # ── System-level block: loop_fuse_check finds the unresolved fuse. ──
        tripped = gp.loop_fuse_check(runtime_file=runtime_path)
        self.assertEqual(len(tripped), 1)
        self.assertEqual(tripped[0]["unit_id"], self.unit_id)
        self.assertTrue(tripped[0]["loop_count"] > tripped[0]["max_rounds"])

        # ── The release-gate issue helper produces a per-unit FAIL issue. ───
        issues = gp.collect_loop_fuse_issues(runtime_file=runtime_path)
        self.assertEqual(len(issues), 1)
        self.assertIn(self.unit_id, issues[0])

        # ── Resolution clears the block: withdraw the unit, re-check. ───────
        payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        for u in payload["flow_units"]:
            if u["flow_unit_id"] == self.unit_id:
                u["runtime_status"] = "withdrawn"
                u["gate_state"]["status"] = "withdrawn"
        runtime_path.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8")
        self.assertEqual(gp.loop_fuse_check(runtime_file=runtime_path), [],
                         "resolved (withdrawn) fuse must not block")
        self.assertEqual(gp.collect_loop_fuse_issues(runtime_file=runtime_path), [])


if __name__ == "__main__":
    unittest.main()
