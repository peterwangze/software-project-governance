"""Tests for the Loop Runtime Contract v2 validator (FEAT-002, ADR-013 / 0.67.0).

These tests are the load-bearing verification for FEAT-002:

  - ``test_valid_payload_passes`` — a well-formed v2 payload (per ADR §3.2/3.3/3.4)
    PASSES the v2 validator. This is the positive case.
  - The ``test_*_fails`` cases are the negative coverage: each removes or
    corrupts one load-bearing field and asserts validation FAILS with a
    specific error. Fail-closed: no silent pass.
  - ``test_routing_*`` — the version router in ``flow_unit_runtime.py``
    dispatches ``schema_version`` "1.0" → v1 (unchanged), "2.0" → v2, unknown
    → fail.
  - ``test_contract_drift_registry_loop_state_fields`` — the drift test: the
    registry's ``agent_intrinsic_loop.loop_state_fields`` MUST equal the
    contract's ``loop_state_fields`` (ADR §3.6/§3.7). Fails on drift.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_flow_unit_runtime_v2.py -v
"""

import copy
import json
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import loop_engine  # noqa: E402
from checks import flow_unit_runtime  # noqa: E402
from checks import flow_unit_runtime_v2  # noqa: E402

PLUGIN_HOME = _INFRA_DIR.parent  # skills/software-project-governance/
CONTRACT_PATH = PLUGIN_HOME / "core" / "loop-runtime-contract.json"
REGISTRY_PATH = PLUGIN_HOME / "core" / "loop-engineering-registry.json"

# A valid 64-lowercase-hex SHA-256 (deterministic — not a real plan hash, just
# a shape-correct placeholder; the FEAT-003 re-derivation parity check is the
# planner's responsibility, not the FEAT-002 validator's).
_VALID_PLAN_HASH = "a" * 64


def _active_loop_state(tier="middle"):
    """Return a valid 9-field loop_state for an ACTIVE unit (FEAT-004 initial)."""
    return {
        "active_loop": True,
        "active_loop_tier": tier,
        "loop_count": 0,
        "last_loop_type": None,
        "agent_phase": "plan",
        "iteration_within_inner": 0,
        "pause_points_active": [],
        "last_gate_result": None,
        "fuse": {"max_rounds": 3, "tripped": False},
    }


def _valid_gate_state(status="pending", gate_id="G5", last_result=None):
    """Return a valid gate_state. last_result MUST match loop_state.last_gate_result."""
    return {
        "status": status,
        "gate_id": gate_id,
        "last_result": last_result,
        "evidence_refs": [],
    }


def _valid_unit(unit_id="shitu.story.Skeleton", runtime_status="active", tier="middle"):
    """Return a valid v2 flow unit per ADR §3.3/3.4.

    The unification invariant (last_gate_result == gate_state.last_result) and
    the runtime_status ⇔ active_loop implication are both satisfied here.
    """
    last_gate_result = None
    loop_state = _active_loop_state(tier=tier)
    if runtime_status == "dormant":
        loop_state = {
            "active_loop": False,
            "active_loop_tier": None,
            "loop_count": 0,
            "last_loop_type": None,
            "agent_phase": "plan",
            "iteration_within_inner": 0,
            "pause_points_active": [],
            "last_gate_result": last_gate_result,
            "fuse": {"max_rounds": 3, "tripped": False},
        }
    return {
        "flow_unit_id": unit_id,
        "title": "Skeleton story unit",
        "unit_type": "story",
        "project_type": "game-narrative",
        "derivation_reason": "dotted-id:shitu.story.Skeleton",
        "loop_state": loop_state,
        "gate_state": _valid_gate_state(last_result=last_gate_result),
        "runtime_status": runtime_status,
        "dependencies": [],
        "blockers": [],
    }


def _valid_payload(units=None):
    """Return a valid v2 runtime payload per ADR §3.2.

    All top-level fields present, decomposition_confirmed true, boundary tokens
    present, non-empty flow_units.
    """
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


class V2ValidatorPositiveTests(unittest.TestCase):
    """The positive case: a well-formed v2 payload PASSES."""

    def test_valid_payload_passes(self):
        """A v2 payload with all §3.2/3.3/3.4 fields correct passes validation."""
        payload = _valid_payload()
        result = flow_unit_runtime_v2.validate_flow_unit_runtime_v2_payload(payload)
        self.assertTrue(
            result["valid"],
            f"valid payload should pass; got errors: {result['errors']}",
        )
        self.assertEqual(result["errors"], [])

    def test_valid_payload_list_style_empty(self):
        """The list-style core returns an empty list for a valid payload."""
        payload = _valid_payload()
        failures = flow_unit_runtime_v2.validate_flow_unit_runtime_payload_v2(payload)
        self.assertEqual(failures, [], f"valid payload should produce no failures: {failures}")

    def test_valid_payload_with_two_distinct_units_passes(self):
        """REL-059 dual-unit: two units with different gate/phase both pass."""
        unit_a = _valid_unit(unit_id="app.module.auth", tier="inner")
        unit_a["loop_state"]["agent_phase"] = "act"
        unit_a["gate_state"]["gate_id"] = "G6"
        unit_a["gate_state"]["status"] = "in-progress"
        unit_b = _valid_unit(unit_id="app.module.db", tier="middle")
        unit_b["loop_state"]["agent_phase"] = "plan"
        unit_b["gate_state"]["gate_id"] = "G5"
        unit_b["gate_state"]["status"] = "pending"
        payload = _valid_payload(units=[unit_a, unit_b])
        result = flow_unit_runtime_v2.validate_flow_unit_runtime_v2_payload(payload)
        self.assertTrue(result["valid"], f"two-unit payload should pass: {result['errors']}")


class V2ValidatorNegativeTests(unittest.TestCase):
    """Negative coverage: each load-bearing violation FAILS validation."""

    def _assert_fails(self, payload, needle):
        """Assert the payload fails and that some error mentions ``needle``."""
        result = flow_unit_runtime_v2.validate_flow_unit_runtime_v2_payload(payload)
        self.assertFalse(
            result["valid"],
            f"payload should FAIL but passed (looking for `{needle}`)",
        )
        joined = " ".join(result["errors"])
        self.assertIn(
            needle, joined,
            f"expected an error mentioning `{needle}`; got: {result['errors']}",
        )

    # ── Top-level envelope ───────────────────────────────────────────────────

    def test_missing_required_top_level_field_fails(self):
        payload = _valid_payload()
        del payload["migration_timestamp"]
        self._assert_fails(payload, "missing required top-level field `migration_timestamp`")

    def test_schema_version_not_2_but_contract_v2_fails(self):
        """Belt-and-braces: schema_version != '2.0' with runtime_contract v2 fails."""
        payload = _valid_payload()
        payload["schema_version"] = "1.0"  # wrong version for a v2 contract payload
        self._assert_fails(payload, "schema_version must be 2.0")

    def test_workflow_model_not_loop_engineering_fails(self):
        payload = _valid_payload()
        payload["workflow_model"] = "classic-phase-gate"
        self._assert_fails(payload, "workflow_model must be loop-engineering")

    def test_decomposition_confirmed_false_fails(self):
        payload = _valid_payload()
        payload["decomposition_confirmed"] = False
        self._assert_fails(payload, "decomposition_confirmed must be true")

    def test_runtime_contract_wrong_fails(self):
        payload = _valid_payload()
        payload["runtime_contract"] = "something-else/v3"
        self._assert_fails(payload, "runtime_contract must be loop-runtime-contract/v2")

    def test_contract_source_wrong_fails(self):
        payload = _valid_payload()
        payload["contract_source"] = "wrong-source"
        self._assert_fails(payload, "contract_source must be loop-runtime-contract-v2")

    def test_migration_plan_hash_bad_shape_fails(self):
        payload = _valid_payload()
        payload["migration_plan_hash"] = "not-a-hash"
        self._assert_fails(payload, "migration_plan_hash must be a 64-lowercase-hex")

    def test_runtime_scope_wrong_fails(self):
        payload = _valid_payload()
        payload["runtime_scope"] = "runtime-visibility-only"
        self._assert_fails(payload, "runtime_scope must be loop-engineering-runtime")

    # ── no_overclaim_boundary ────────────────────────────────────────────────

    def test_missing_no_overclaim_boundary_token_fails(self):
        payload = _valid_payload()
        # Drop the token that contains "does not activate execution engine".
        payload["no_overclaim_boundary"] = [
            "RISK-037 remains open.",
            "RISK-042 remains open.",
        ]
        self._assert_fails(payload, "does not activate execution engine")

    def test_missing_risk037_token_fails(self):
        payload = _valid_payload()
        payload["no_overclaim_boundary"] = [
            "does not activate execution engine.",
            "RISK-042 remains open.",
        ]
        self._assert_fails(payload, "RISK-037 remains open")

    def test_no_overclaim_boundary_not_list_fails(self):
        payload = _valid_payload()
        payload["no_overclaim_boundary"] = "not a list"
        self._assert_fails(payload, "no_overclaim_boundary must be a non-empty string list")

    # ── flow_units ───────────────────────────────────────────────────────────

    def test_empty_flow_units_fails(self):
        payload = _valid_payload(units=[])
        self._assert_fails(payload, "flow_units must be a non-empty list")

    def test_missing_required_per_unit_field_fails(self):
        payload = _valid_payload()
        del payload["flow_units"][0]["derivation_reason"]
        self._assert_fails(payload, "missing required field `derivation_reason`")

    def test_duplicate_flow_unit_id_fails(self):
        unit = _valid_unit(unit_id="dup.id")
        payload = _valid_payload(units=[copy.deepcopy(unit), copy.deepcopy(unit)])
        self._assert_fails(payload, "duplicate flow_unit_id `dup.id`")

    def test_invalid_runtime_status_enum_fails(self):
        payload = _valid_payload()
        payload["flow_units"][0]["runtime_status"] = "running"  # not in enum
        self._assert_fails(payload, "runtime_status must be one of")

    def test_invalid_gate_status_enum_fails(self):
        payload = _valid_payload()
        payload["flow_units"][0]["gate_state"]["status"] = "released"  # classic vocab, not v2
        self._assert_fails(payload, "gate_state.status must be one of")

    def test_invalid_agent_phase_enum_fails(self):
        payload = _valid_payload()
        payload["flow_units"][0]["loop_state"]["agent_phase"] = "deploy"
        self._assert_fails(payload, "agent_phase must be one of")

    def test_missing_loop_state_field_fails(self):
        payload = _valid_payload()
        del payload["flow_units"][0]["loop_state"]["fuse"]
        self._assert_fails(payload, "loop_state missing field `fuse`")

    def test_missing_gate_state_field_fails(self):
        payload = _valid_payload()
        del payload["flow_units"][0]["gate_state"]["evidence_refs"]
        self._assert_fails(payload, "gate_state missing field `evidence_refs`")

    # ── FEAT-002 unification invariant ───────────────────────────────────────

    def test_last_gate_result_not_equal_gate_state_last_result_fails(self):
        """The unification invariant: loop_state.last_gate_result must equal gate_state.last_result."""
        payload = _valid_payload()
        # Set the two to different non-null values.
        payload["flow_units"][0]["loop_state"]["last_gate_result"] = "passed"
        payload["flow_units"][0]["gate_state"]["last_result"] = "failed"
        self._assert_fails(payload, "last_gate_result must equal")

    # ── FEAT-004 runtime_status ⇔ active_loop bidirectional implication ──────

    def test_runtime_status_active_but_active_loop_false_fails(self):
        payload = _valid_payload()
        unit = payload["flow_units"][0]
        unit["runtime_status"] = "active"
        unit["loop_state"]["active_loop"] = False  # contradicts active
        self._assert_fails(payload, "runtime_status 'active' requires loop_state.active_loop true")

    def test_runtime_status_dormant_but_active_loop_true_fails(self):
        payload = _valid_payload()
        unit = payload["flow_units"][0]
        unit["runtime_status"] = "dormant"
        # active_loop true contradicts dormant (keep tier valid to isolate the implication)
        unit["loop_state"]["active_loop"] = True
        self._assert_fails(payload, "runtime_status 'dormant' requires loop_state.active_loop false")

    def test_example_fixture_reason_cannot_be_active(self):
        """AUDIT-133 guard: example-fixture provenance must not be active."""
        payload = _valid_payload()
        unit = payload["flow_units"][0]
        unit["derivation_reason"] = "example-fixture"
        unit["runtime_status"] = "active"  # contradicts the example-fixture rule
        self._assert_fails(payload, "example-fixture")

    # ── Fail-closed on schema authority ──────────────────────────────────────

    def test_validator_fail_closed_on_missing_schema(self):
        """If the contract schema cannot be loaded, validation fails closed."""
        payload = _valid_payload()
        # Point plugin_home at an empty temp dir → contract schema missing.
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            result = flow_unit_runtime_v2.validate_flow_unit_runtime_v2_payload(
                payload, plugin_home=Path(tmpdir),
            )
        self.assertFalse(result["valid"], "missing schema must fail closed")
        self.assertTrue(
            any("cannot load v2 contract schema" in e for e in result["errors"]),
            f"expected schema-load failure; got: {result['errors']}",
        )

    def test_non_dict_root_fails(self):
        result = flow_unit_runtime_v2.validate_flow_unit_runtime_v2_payload("not a dict")
        self.assertFalse(result["valid"])
        self.assertTrue(any("must be an object" in e for e in result["errors"]))


class RoutingTests(unittest.TestCase):
    """The version router in flow_unit_runtime.py dispatches on schema_version."""

    def test_schema_version_1_routes_to_v1_unchanged(self):
        """A v1 payload routes to the byte-frozen v1 validator (unchanged)."""
        # A minimal v1 payload: schema_version 1.0, workflow_model classic. The
        # v1 validator requires many classic fields, so this incomplete payload
        # produces v1-specific failures (proving it routed to v1, not v2).
        v1_payload = {"schema_version": "1.0", "workflow_model": "classic-phase-gate"}
        failures = flow_unit_runtime.validate_flow_unit_runtime_payload_dispatch(v1_payload)
        self.assertTrue(
            len(failures) > 0,
            "v1 payload should produce v1 failures (it lacks classic fields)",
        )
        # v1-specific failure: runtime_scope must be runtime-visibility-only.
        joined = " ".join(failures)
        self.assertIn("runtime_scope must be runtime-visibility-only", joined)

    def test_schema_version_2_routes_to_v2(self):
        """A v2 payload routes to the v2 validator."""
        payload = _valid_payload()
        failures = flow_unit_runtime.validate_flow_unit_runtime_payload_dispatch(payload)
        self.assertEqual(
            failures, [],
            f"valid v2 payload routed through the dispatcher should pass: {failures}",
        )

    def test_schema_version_2_invalid_routes_to_v2_and_fails(self):
        """An invalid v2 payload routes to v2 and fails there (not v1)."""
        payload = _valid_payload()
        del payload["migration_timestamp"]  # missing top-level field
        failures = flow_unit_runtime.validate_flow_unit_runtime_payload_dispatch(payload)
        # v2-specific failure wording, proving it routed to v2.
        joined = " ".join(failures)
        self.assertIn("missing required top-level field `migration_timestamp`", joined)

    def test_absent_schema_version_routes_to_v1(self):
        """Absent schema_version is treated as v1 (legacy visibility payloads)."""
        v1_payload = {"workflow_model": "classic-phase-gate"}  # no schema_version
        failures = flow_unit_runtime.validate_flow_unit_runtime_payload_dispatch(v1_payload)
        joined = " ".join(failures)
        # Routed to v1: it complains about schema_version must be 1.0 (v1 wording).
        self.assertIn("schema_version must be 1.0", joined)

    def test_unknown_schema_version_fails_closed(self):
        """An unknown schema_version fails closed (not silently routed)."""
        payload = _valid_payload()
        payload["schema_version"] = "9.9"
        failures = flow_unit_runtime.validate_flow_unit_runtime_payload_dispatch(payload)
        self.assertEqual(len(failures), 1)
        self.assertIn("unsupported schema_version", failures[0])
        self.assertIn("9.9", failures[0])

    def test_v2_payload_still_rejected_by_raw_v1_validator(self):
        """The v1 validator (called directly) still rejects loop-engineering.

        This proves the v1 containment is preserved: a v2/loop-engineering
        payload presented to the byte-frozen v1 validator fails on
        workflow_model (the AUDIT-133 containment boundary).
        """
        payload = _valid_payload()
        # Call the v1 validator DIRECTLY (not via the dispatcher) to prove it
        # is unchanged and still rejects loop-engineering.
        failures = flow_unit_runtime.validate_flow_unit_runtime_payload(payload)
        joined = " ".join(failures)
        self.assertIn(
            "workflow_model must be classic-phase-gate or dynamic-flow-gate", joined,
            "the byte-frozen v1 validator must still reject loop-engineering",
        )


class ContractDriftTests(unittest.TestCase):
    """The drift test: registry loop_state_fields == contract loop_state_fields.

    ADR §3.6/§3.7: ``loop-engineering-registry.json``'s
    ``agent_intrinsic_loop.loop_state_fields`` list is verified EQUAL to the
    contract schema's ``loop_state_fields`` list by this drift test. If either
    drifts, the test fails. The registry is checked for field-list PARITY, not
    loaded as a runtime schema (per Design Review F5).
    """

    def test_contract_schema_loads(self):
        """The contract schema is valid JSON and loads."""
        self.assertTrue(CONTRACT_PATH.exists(), f"{CONTRACT_PATH} must exist")
        with open(CONTRACT_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["schema_version"], "2.0")
        self.assertEqual(data["contract_id"], "loop-runtime-contract/v2")

    def test_contract_drift_registry_loop_state_fields(self):
        """Registry agent_intrinsic_loop.loop_state_fields == contract loop_state_fields.

        LOAD-BEARING DRIFT TEST (ADR §3.6). The registry declares the 9 FX-189
        loop_state fields; the contract declares the same 9. If either side
        adds/removes/reorders a field, this test fails — the two cannot silently
        diverge. This is the executable binding that makes the registry the
        5th "consumer" of the contract (by parity, not runtime load).
        """
        registry_data, registry_issues = loop_engine.load_loop_registry(PLUGIN_HOME)
        self.assertIsNotNone(
            registry_data, f"registry failed to load: {registry_issues}",
        )
        registry_fields = registry_data["agent_intrinsic_loop"]["loop_state_fields"]

        with open(CONTRACT_PATH, encoding="utf-8") as fh:
            contract_data = json.load(fh)
        contract_fields = contract_data["loop_state_fields"]

        self.assertEqual(
            contract_fields, registry_fields,
            (
                "DRIFT DETECTED: loop-runtime-contract.json loop_state_fields "
                "differs from loop-engineering-registry.json "
                "agent_intrinsic_loop.loop_state_fields. The contract and the "
                "registry MUST declare the same 9 FX-189 fields.\n"
                f"  contract: {contract_fields}\n"
                f"  registry: {registry_fields}"
            ),
        )

        # Sanity: the list really is the 9 FX-189 fields.
        self.assertEqual(
            len(contract_fields), 9,
            f"expected 9 loop_state_fields; got {len(contract_fields)}: {contract_fields}",
        )

    def test_contract_required_per_unit_fields_complete(self):
        """The contract declares the exact 10 per-unit fields from ADR §3.3."""
        with open(CONTRACT_PATH, encoding="utf-8") as fh:
            contract_data = json.load(fh)
        expected = [
            "flow_unit_id", "title", "unit_type", "project_type",
            "derivation_reason", "loop_state", "gate_state", "runtime_status",
            "dependencies", "blockers",
        ]
        self.assertEqual(contract_data["required_per_unit_fields"], expected)

    def test_contract_required_top_level_fields_complete(self):
        """The contract declares the exact 11 top-level fields from ADR §3.2."""
        with open(CONTRACT_PATH, encoding="utf-8") as fh:
            contract_data = json.load(fh)
        expected = [
            "schema_version", "runtime_contract", "runtime_scope",
            "workflow_model", "contract_source", "migration_version",
            "migration_plan_hash", "migration_timestamp",
            "decomposition_confirmed", "flow_units", "no_overclaim_boundary",
        ]
        self.assertEqual(contract_data["required_top_level_fields"], expected)

    def test_contract_enums_match_adr(self):
        """The contract's allowed enums match ADR §3.4/§3.5."""
        with open(CONTRACT_PATH, encoding="utf-8") as fh:
            contract_data = json.load(fh)
        self.assertEqual(
            contract_data["allowed_gate_statuses"],
            ["pending", "in-progress", "passed", "failed", "blocked", "escalated", "withdrawn"],
        )
        self.assertEqual(
            contract_data["allowed_runtime_statuses"],
            ["active", "dormant", "blocked", "withdrawn"],
        )
        self.assertEqual(
            contract_data["allowed_loop_tiers"],
            ["setup", "inner", "middle", "outer"],
        )
        self.assertEqual(
            contract_data["allowed_agent_phases"],
            ["plan", "act", "observe", "reflect"],
        )

    def test_contract_mandatory_boundary_tokens_present(self):
        """The contract declares the 3 mandatory 0.67.0 boundary tokens."""
        with open(CONTRACT_PATH, encoding="utf-8") as fh:
            contract_data = json.load(fh)
        tokens = contract_data["no_overclaim_boundary_mandatory_tokens"]
        self.assertIn("does not activate execution engine", tokens)
        self.assertIn("RISK-037 remains open", tokens)
        self.assertIn("RISK-042 remains open", tokens)


if __name__ == "__main__":
    unittest.main(verbosity=2)
