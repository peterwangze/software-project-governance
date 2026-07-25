"""Unit tests for FEAT-004 decomposition confirmation + canonical initial state.

FEAT-004 (ADR-013 §5, 0.67.0) makes ``confirm_decomposition`` a real gate and
fills in the canonical per-unit initial state in ``plan_to_payload``. The
load-bearing properties proven here:

  - **confirm_decomposition (full set)** — flips the flag, hash UNCHANGED
    (decomposition_confirmed is excluded; same units).
  - **confirm_decomposition (subset)** — filtered units, RECOMPUTED hash
    (different from full-set hash).
  - **confirm_decomposition validation** — duplicate IDs, unknown dependency,
    empty unit set, empty derivation_reason all fail.
  - **plan_to_payload from a CONFIRMED plan** — passes the v2 validator
    COMPLETELY (zero issues).
  - **plan_to_payload from an UNCONFIRMED plan** — fails v2 only on
    decomposition_confirmed (FEAT-003 containment, re-confirmed).
  - **canonical initial state** — gate_state initialized (status=pending,
    gate_id set, last_result=null, evidence_refs=[]), runtime_status explicit,
    active_loop matches runtime_status.
  - **example-fixture reason** — pairs with runtime_status dormant (not active).
  - **apply path** — confirm_decomposition is called before write; unconfirmed
    plan now SUCCEEDS (apply confirms internally) and writes a v2-valid
    runtime.json; a bad candidate/approved set fail-closes with no write.
  - **operator-confirmed subset apply** — only the approved units are written.

ALL tests use ``tempfile.TemporaryDirectory`` — the real ``.governance/`` is
NEVER touched.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_loop_decomposition.py -v
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

import loop_migration as lm  # noqa: E402
import loop_migration_plan as lmp  # noqa: E402
from checks import flow_unit_runtime_v2  # noqa: E402

PLUGIN_HOME = _INFRA_DIR.parent  # skills/software-project-governance/


# ─── Shared fixtures (mirror test_loop_migration_plan.py) ────────────────────

CLASSIC_PLAN_TRACKER = (
    "# Plan Tracker — demo-host\n"
    "## 项目配置\n"
    "- workflow_model: classic-phase-gate\n"
    "## Gate 状态跟踪\n"
    "| Gate | 阶段转换 | 状态 |\n"
    "| --- | --- | --- |\n"
    "| G11 | next | passed |\n"
)

# A CLI-tool plan-tracker with three dotted command ids — exercises a real
# multi-unit derivation so the subset-filter tests have >1 unit to work with.
CLI_PLAN_TRACKER = (
    "# Plan Tracker — my-cli\n"
    "- workflow_model: classic-phase-gate\n"
    "## 任务\n"
    "- mycli.command.init — bootstrap\n"
    "- mycli.command.build — compile\n"
    "- mycli.command.deploy — ship\n"
)

CLASSIC_EVIDENCE_LOG = (
    "| 编号 | 事项 | 说明 |\n"
    "| --- | --- | --- |\n"
    "| EVD-001 | init | seeded evidence log |\n"
)


def _write_host(host_root, plan_text=None, evidence_text=None):
    """Write a minimal classic .governance/ into host_root."""
    gov = host_root / ".governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "plan-tracker.md").write_text(
        plan_text if plan_text is not None else CLASSIC_PLAN_TRACKER,
        encoding="utf-8",
    )
    (gov / "evidence-log.md").write_text(
        evidence_text if evidence_text is not None else CLASSIC_EVIDENCE_LOG,
        encoding="utf-8",
    )


def _build_cli_plan(host_root):
    """Build a multi-unit cli-tool plan against host_root (no writes)."""
    return lmp.build_migration_plan(str(host_root), "cli-tool")


# ═══════════════════════════════════════════════════════════════════════════
# confirm_decomposition — full-set vs subset hash semantics (ADR §5.2)
# ═══════════════════════════════════════════════════════════════════════════


class TestConfirmDecompositionHashSemantics(unittest.TestCase):
    """ADR §5.2 / §4.2: full-set confirm keeps the hash; subset confirm
    recomputes it (the confirmed set is the load-bearing structure)."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.host = Path(self.tmpdir.name)
        _write_host(self.host, plan_text=CLI_PLAN_TRACKER)
        self.plan = _build_cli_plan(self.host)
        # Precondition: the fixture really derives multiple units.
        self.assertGreaterEqual(self.plan.unit_count, 2,
                                "CLI fixture must derive >=2 units for subset tests")

    def test_confirm_full_set_keeps_hash_unchanged(self):
        """approved_unit_ids=None confirms the whole derived set; the hash is
        unchanged (decomposition_confirmed is excluded from the hash, ADR §4.2,
        and the unit set is identical)."""
        confirmed = lmp.confirm_decomposition(self.plan)  # approved_unit_ids=None
        self.assertTrue(confirmed.decomposition_confirmed)
        self.assertFalse(self.plan.decomposition_confirmed)
        self.assertEqual(confirmed.plan_hash, self.plan.plan_hash,
                         "full-set confirm must NOT change the plan_hash")
        # Units are identical (same ids, same order, same count).
        self.assertEqual(confirmed.unit_ids, self.plan.unit_ids)
        self.assertEqual(confirmed.unit_count, self.plan.unit_count)

    def test_confirm_subset_recomputes_a_different_hash(self):
        """approved_unit_ids (a proper subset) filters the units and RECOMPUTES
        the hash — the confirmed structure differs from the candidate set."""
        subset = list(self.plan.unit_ids[:2])
        confirmed = lmp.confirm_decomposition(self.plan, approved_unit_ids=subset)
        self.assertTrue(confirmed.decomposition_confirmed)
        self.assertEqual(confirmed.unit_count, 2)
        self.assertEqual(list(confirmed.unit_ids), subset)
        self.assertNotEqual(confirmed.plan_hash, self.plan.plan_hash,
                            "subset confirm MUST recompute a different plan_hash")

    def test_confirm_subset_hash_is_reproducible(self):
        """The recomputed subset hash is deterministic: confirming the same
        subset twice yields the same confirmed hash (REL-059 identity for the
        CONFIRMED plan)."""
        subset = list(self.plan.unit_ids[:2])
        c1 = lmp.confirm_decomposition(self.plan, approved_unit_ids=subset)
        c2 = lmp.confirm_decomposition(self.plan, approved_unit_ids=subset)
        self.assertEqual(c1.plan_hash, c2.plan_hash)
        self.assertEqual(c1, c2)

    def test_confirm_subset_matches_compute_plan_hash(self):
        """The subset-confirmed hash equals a direct compute_plan_hash call
        over the confirmed ids (the recomputation is the canonical formula)."""
        subset = list(self.plan.unit_ids[:2])
        confirmed = lmp.confirm_decomposition(self.plan, approved_unit_ids=subset)
        direct = lmp.compute_plan_hash(
            contract_id=self.plan.contract_id, project_id=self.plan.project_id,
            project_type=self.plan.project_type, schema_version=self.plan.schema_version,
            unit_count=2, unit_ids=tuple(subset),
            workflow_model_new=self.plan.workflow_model_new,
            gate_schema=self.plan.gate_schema,
        )
        self.assertEqual(confirmed.plan_hash, direct)

    def test_confirm_returns_new_frozen_instance(self):
        """confirm_decomposition returns a NEW dataclass; the original is
        untouched (frozen + immutability, ADR §4.1)."""
        confirmed = lmp.confirm_decomposition(self.plan)
        self.assertIsNot(self.plan, confirmed)
        self.assertFalse(self.plan.decomposition_confirmed)
        with self.assertRaises(Exception):
            self.plan.decomposition_confirmed = True  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════
# confirm_decomposition — candidate-set validation (ADR §5.2 step 1)
# ═══════════════════════════════════════════════════════════════════════════


class TestConfirmDecompositionValidation(unittest.TestCase):
    """ADR §5.2: confirm validates the candidate set; any violation raises
    ValueError (matches the planner's error style)."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.host = Path(self.tmpdir.name)
        _write_host(self.host, plan_text=CLI_PLAN_TRACKER)
        self.plan = _build_cli_plan(self.host)

    def test_duplicate_candidate_ids_fail(self):
        """A plan whose units contain a duplicate flow_unit_id fails."""
        u0 = self.plan.units[0]
        dup_units = self.plan.units + (u0,)  # append the same unit again
        bad_plan = lmp.MigrationPlan(  # type: ignore[call-arg]
            schema_version=self.plan.schema_version,
            contract_id=self.plan.contract_id,
            target_root=self.plan.target_root,
            project_type=self.plan.project_type,
            project_id=self.plan.project_id,
            workflow_model_prior=self.plan.workflow_model_prior,
            workflow_model_new=self.plan.workflow_model_new,
            unit_ids=tuple(u.flow_unit_id for u in dup_units),
            unit_count=len(dup_units),
            units=dup_units,
            gate_schema=self.plan.gate_schema,
            decomposition_confirmed=False,
            plan_hash=self.plan.plan_hash,
        )
        with self.assertRaises(ValueError) as cm:
            lmp.confirm_decomposition(bad_plan)
        self.assertIn("duplicate", str(cm.exception).lower())

    def test_unknown_dependency_fails(self):
        """A unit whose dependencies reference an id not in the candidate set
        fails (no dangling edges in the confirmed plan)."""
        bad_unit = lmp._dc_replace(self.plan.units[0], dependencies=("nope.not.real",))
        bad_plan = lmp._dc_replace(self.plan, units=(bad_unit,))
        with self.assertRaises(ValueError) as cm:
            lmp.confirm_decomposition(bad_plan)
        self.assertIn("unknown dependency", str(cm.exception).lower())

    def test_empty_unit_set_fails(self):
        """A plan with zero units fails (at least one unit is required)."""
        empty_plan = lmp._dc_replace(
            self.plan, units=(), unit_ids=(), unit_count=0,
        )
        with self.assertRaises(ValueError) as cm:
            lmp.confirm_decomposition(empty_plan)
        self.assertIn("empty", str(cm.exception).lower())

    def test_empty_derivation_reason_fails(self):
        """A unit with an empty derivation_reason fails (the v2 validator
        requires non-empty; confirm is the gate that enforces it)."""
        bad_unit = lmp._dc_replace(self.plan.units[0], derivation_reason="")
        bad_plan = lmp._dc_replace(self.plan, units=(bad_unit,))
        with self.assertRaises(ValueError) as cm:
            lmp.confirm_decomposition(bad_plan)
        self.assertIn("derivation_reason", str(cm.exception).lower())

    def test_whitespace_derivation_reason_fails(self):
        """A whitespace-only derivation_reason is treated as empty."""
        bad_unit = lmp._dc_replace(self.plan.units[0], derivation_reason="   ")
        bad_plan = lmp._dc_replace(self.plan, units=(bad_unit,))
        with self.assertRaises(ValueError):
            lmp.confirm_decomposition(bad_plan)

    def test_unknown_approved_unit_id_fails(self):
        """approved_unit_ids referencing an id the planner never derived fails
        (the operator cannot approve units that are not candidates)."""
        with self.assertRaises(ValueError) as cm:
            lmp.confirm_decomposition(self.plan, approved_unit_ids=["does.not.exist"])
        self.assertIn("unknown", str(cm.exception).lower())

    def test_empty_approved_unit_ids_fails(self):
        """An empty approved_unit_ids list fails (explicit empty ≠ None)."""
        with self.assertRaises(ValueError) as cm:
            lmp.confirm_decomposition(self.plan, approved_unit_ids=[])
        self.assertIn("empty", str(cm.exception).lower())

    def test_duplicate_approved_unit_ids_fail(self):
        """A duplicate in approved_unit_ids fails (operator cannot approve a
        unit twice)."""
        uid = self.plan.unit_ids[0]
        with self.assertRaises(ValueError) as cm:
            lmp.confirm_decomposition(self.plan, approved_unit_ids=[uid, uid])
        self.assertIn("duplicate", str(cm.exception).lower())


# ═══════════════════════════════════════════════════════════════════════════
# confirm_decomposition — subset filtering correctness (ADR §5.2 step 2)
# ═══════════════════════════════════════════════════════════════════════════


class TestConfirmDecompositionSubsetFiltering(unittest.TestCase):
    """ADR §5.2: approved_unit_ids filters units to EXACTLY those ids (in
    operator order) and filters dependencies to the remaining set."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.host = Path(self.tmpdir.name)
        _write_host(self.host, plan_text=CLI_PLAN_TRACKER)
        self.plan = _build_cli_plan(self.host)

    def test_subset_keeps_exactly_the_approved_ids(self):
        subset = list(self.plan.unit_ids[:2])
        confirmed = lmp.confirm_decomposition(self.plan, approved_unit_ids=subset)
        self.assertEqual(set(confirmed.unit_ids), set(subset))
        self.assertEqual(confirmed.unit_count, 2)
        # Operator order is preserved.
        self.assertEqual(list(confirmed.unit_ids), subset)

    def test_subset_filters_dependencies_to_remaining_set(self):
        """A dependency that points at a dropped unit is removed (no dangling
        edge in the confirmed plan)."""
        ids = list(self.plan.unit_ids)
        # Give unit[0] a dependency on unit[2]; then approve only [0,1].
        u0_with_dep = lmp._dc_replace(self.plan.units[0], dependencies=(ids[2],))
        plan_with_dep = lmp._dc_replace(
            self.plan,
            units=(u0_with_dep,) + tuple(self.plan.units[1:]),
        )
        confirmed = lmp.confirm_decomposition(
            plan_with_dep, approved_unit_ids=[ids[0], ids[1]],
        )
        approved_unit = next(u for u in confirmed.units if u.flow_unit_id == ids[0])
        self.assertNotIn(
            ids[2], approved_unit.dependencies,
            "dependency on a dropped unit must be filtered out",
        )

    def test_subset_preserves_dependencies_within_remaining_set(self):
        """A dependency that points at a KEPT unit is preserved."""
        ids = list(self.plan.unit_ids)
        u0_with_dep = lmp._dc_replace(self.plan.units[0], dependencies=(ids[1],))
        plan_with_dep = lmp._dc_replace(
            self.plan,
            units=(u0_with_dep,) + tuple(self.plan.units[1:]),
        )
        confirmed = lmp.confirm_decomposition(
            plan_with_dep, approved_unit_ids=[ids[0], ids[1]],
        )
        approved_unit = next(u for u in confirmed.units if u.flow_unit_id == ids[0])
        self.assertIn(ids[1], approved_unit.dependencies)


# ═══════════════════════════════════════════════════════════════════════════
# plan_to_payload — confirmed vs unconfirmed vs canonical initial state (§5.3)
# ═══════════════════════════════════════════════════════════════════════════


class TestPlanToPayloadConfirmedVsUnconfirmed(unittest.TestCase):
    """ADR §5.3: a CONFIRMED plan yields a v2 payload that PASSES the validator
    completely; an UNCONFIRMED plan fails ONLY on decomposition_confirmed."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.host = Path(self.tmpdir.name)
        _write_host(self.host, plan_text=CLI_PLAN_TRACKER)
        self.plan = _build_cli_plan(self.host)

    def test_confirmed_plan_payload_passes_v2_completely(self):
        """The single most important FEAT-004 property: a confirmed plan's
        payload passes the v2 validator with ZERO issues."""
        confirmed = lmp.confirm_decomposition(self.plan)
        payload = lmp.plan_to_payload(confirmed)
        issues = flow_unit_runtime_v2.validate_flow_unit_runtime_payload_v2(payload)
        self.assertEqual(
            issues, [],
            f"confirmed plan payload must pass v2 COMPLETELY; got {issues}",
        )

    def test_confirmed_subset_payload_passes_v2_completely(self):
        """A subset-confirmed plan also yields a v2-valid payload."""
        subset = list(self.plan.unit_ids[:2])
        confirmed = lmp.confirm_decomposition(self.plan, approved_unit_ids=subset)
        payload = lmp.plan_to_payload(confirmed)
        issues = flow_unit_runtime_v2.validate_flow_unit_runtime_payload_v2(payload)
        self.assertEqual(issues, [], f"subset-confirmed payload must pass v2; got {issues}")

    def test_unconfirmed_plan_payload_fails_only_on_decomposition(self):
        """FEAT-003 containment (re-confirmed in FEAT-004): an unconfirmed plan
        yields a payload whose ONLY v2 failure is decomposition_confirmed."""
        payload = lmp.plan_to_payload(self.plan)
        issues = flow_unit_runtime_v2.validate_flow_unit_runtime_payload_v2(payload)
        self.assertEqual(len(issues), 1,
                         f"unconfirmed plan should fail ONLY on decomposition; got {issues}")
        self.assertIn("decomposition_confirmed must be true", issues[0])

    def test_payload_decomposition_confirmed_reflects_plan(self):
        """payload['decomposition_confirmed'] mirrors the plan's flag."""
        payload_unconfirmed = lmp.plan_to_payload(self.plan)
        self.assertFalse(payload_unconfirmed["decomposition_confirmed"])
        confirmed = lmp.confirm_decomposition(self.plan)
        payload_confirmed = lmp.plan_to_payload(confirmed)
        self.assertTrue(payload_confirmed["decomposition_confirmed"])


class TestCanonicalInitialState(unittest.TestCase):
    """ADR §5.3: each unit's initial loop_state / gate_state / runtime_status
    is set to the canonical dormant-activation shape."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.host = Path(self.tmpdir.name)
        _write_host(self.host, plan_text=CLI_PLAN_TRACKER)
        self.plan = _build_cli_plan(self.host)
        self.confirmed = lmp.confirm_decomposition(self.plan)
        self.payload = lmp.plan_to_payload(self.confirmed)

    def test_runtime_status_is_explicit_dormant(self):
        """runtime_status is explicit and equals 'dormant' (execution engine is
        0.68.0; units are confirmed but not yet executing)."""
        for unit in self.payload["flow_units"]:
            self.assertEqual(unit["runtime_status"], "dormant")

    def test_active_loop_matches_runtime_status(self):
        """runtime_status⇔active_loop implication: dormant → active_loop:false."""
        for unit in self.payload["flow_units"]:
            ls = unit["loop_state"]
            self.assertEqual(unit["runtime_status"], "dormant")
            self.assertIs(ls["active_loop"], False)

    def test_gate_state_initialized_canonically(self):
        """gate_state: status=pending, gate_id set (entry gate for the tier),
        last_result=null, evidence_refs=[]."""
        for unit in self.payload["flow_units"]:
            gs = unit["gate_state"]
            self.assertEqual(gs["status"], "pending")
            self.assertIsInstance(gs["gate_id"], str)
            self.assertTrue(gs["gate_id"].strip(), "gate_id must be non-empty")
            self.assertIsNone(gs["last_result"])
            self.assertEqual(gs["evidence_refs"], [])

    def test_gate_id_is_entry_gate_for_setup_tier(self):
        """Setup-tier units resolve to G1 (the loop-setup entry gate from the
        registry's loop_gate_semantics)."""
        for unit in self.payload["flow_units"]:
            # All derived units begin at the setup tier (build_migration_plan
            # sets entry_tier="setup"), so the entry gate is G1.
            self.assertEqual(unit["gate_state"]["gate_id"], "G1")

    def test_last_gate_result_unified_with_gate_state_last_result(self):
        """FEAT-002 unification: loop_state.last_gate_result ==
        gate_state.last_result (both null at activation)."""
        for unit in self.payload["flow_units"]:
            self.assertIsNone(unit["loop_state"]["last_gate_result"])
            self.assertIsNone(unit["gate_state"]["last_result"])
            self.assertEqual(
                unit["loop_state"]["last_gate_result"],
                unit["gate_state"]["last_result"],
            )

    def test_loop_state_has_all_nine_fields(self):
        """The 9-field FX-189 loop_state shape is fully populated (contract
        design-review note F1 — v2 requires all 9)."""
        schema, _ = flow_unit_runtime_v2.load_loop_runtime_contract()
        expected = set(schema["loop_state_fields"])
        for unit in self.payload["flow_units"]:
            self.assertEqual(set(unit["loop_state"].keys()), expected,
                             f"loop_state must have exactly the 9 fields; got {set(unit['loop_state'].keys())}")

    def test_derivation_reason_non_empty(self):
        """Every unit carries a non-empty derivation_reason."""
        for unit in self.payload["flow_units"]:
            self.assertIsInstance(unit["derivation_reason"], str)
            self.assertTrue(unit["derivation_reason"].strip())


class TestExampleFixtureReason(unittest.TestCase):
    """ADR §5.3 / AUDIT-133: a unit with derivation_reason 'example-fixture'
    must pair with runtime_status 'dormant' (never active). plan_to_payload
    always emits dormant, so the guard is satisfied by construction."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.host = Path(self.tmpdir.name)
        _write_host(self.host, plan_text=CLI_PLAN_TRACKER)
        self.plan = _build_cli_plan(self.host)

    def test_example_fixture_unit_is_dormant(self):
        """A unit whose derivation_reason is 'example-fixture' is emitted with
        runtime_status 'dormant' — the AUDIT-133 guard is satisfied."""
        ex_unit = lmp._dc_replace(self.plan.units[0], derivation_reason="example-fixture")
        plan_with_fixture = lmp._dc_replace(self.plan, units=(ex_unit,))
        confirmed = lmp.confirm_decomposition(plan_with_fixture)
        payload = lmp.plan_to_payload(confirmed)
        fixture_unit = payload["flow_units"][0]
        self.assertEqual(fixture_unit["derivation_reason"], "example-fixture")
        self.assertEqual(fixture_unit["runtime_status"], "dormant")
        self.assertIs(fixture_unit["loop_state"]["active_loop"], False)
        # And the resulting payload passes v2 completely (the AUDIT-133 guard
        # does not fire because the unit is dormant, not active).
        issues = flow_unit_runtime_v2.validate_flow_unit_runtime_payload_v2(payload)
        self.assertEqual(issues, [], f"example-fixture dormant payload must pass; got {issues}")

    def test_validator_rejects_example_fixture_active(self):
        """Belt-and-braces: the v2 validator itself rejects an example-fixture
        unit that is (incorrectly) active — proves the guard is real and that
        plan_to_payload's dormant emission is what satisfies it."""
        confirmed = lmp.confirm_decomposition(self.plan)
        payload = lmp.plan_to_payload(confirmed)
        payload["flow_units"][0]["derivation_reason"] = "example-fixture"
        payload["flow_units"][0]["runtime_status"] = "active"
        payload["flow_units"][0]["loop_state"]["active_loop"] = True
        issues = flow_unit_runtime_v2.validate_flow_unit_runtime_payload_v2(payload)
        self.assertTrue(
            any("example-fixture" in i and "dormant" in i for i in issues),
            f"expected AUDIT-133 example-fixture rejection; got {issues}",
        )


# ═══════════════════════════════════════════════════════════════════════════
# apply path integration (ADR §5.2 — confirm before plan_to_payload)
# ═══════════════════════════════════════════════════════════════════════════


class TestApplyConfirmIntegration(unittest.TestCase):
    """FEAT-004: apply_migration confirms the decomposition before writing. A
    valid candidate set now SUCCEEDS (writes a v2-valid runtime.json); a bad
    candidate/approved set fail-closes with NO write."""

    def test_apply_confirms_and_writes_v2_valid_runtime(self):
        """apply on a classic fixture now SUCCEEDS: it confirms internally,
        writes a runtime.json whose payload passes the v2 validator, creates a
        backup, and appends a MIGRATION row."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            runtime_path = root / ".governance" / "flow-unit-runtime.json"

            result = lm.apply_migration(target_root=str(root))

            self.assertTrue(result["applied"], f"apply failed: {result}")
            self.assertTrue(result.get("decomposition_confirmed"),
                            "result must report decomposition_confirmed=True")
            self.assertTrue(runtime_path.is_file(), "runtime.json must be written")
            runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
            self.assertTrue(runtime["decomposition_confirmed"])
            # The persisted payload passes the v2 validator completely.
            issues = flow_unit_runtime_v2.validate_flow_unit_runtime_payload_v2(runtime)
            self.assertEqual(issues, [],
                             f"persisted runtime must pass v2 completely; got {issues}")
            # Backup + evidence row.
            self.assertTrue(Path(result["backup_dir"]).is_dir())
            evidence = (root / ".governance" / "evidence-log.md").read_text(encoding="utf-8")
            self.assertIn("MIGRATION-", evidence)

    def test_apply_calls_confirm_before_write_on_bad_approved_set(self):
        """A bad approved_unit_ids (unknown id) fails-closed BEFORE any write:
        no backup dir, no runtime.json, no MIGRATION row."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            gov = root / ".governance"

            result = lm.apply_migration(
                target_root=str(root), approved_unit_ids=["does.not.exist"],
            )

            self.assertFalse(result["applied"])
            self.assertIn("confirmation failed", result["aborted_reason"])
            self.assertFalse((gov / "flow-unit-runtime.json").is_file())
            self.assertFalse((gov / "archive").is_dir())
            evidence = (gov / "evidence-log.md").read_text(encoding="utf-8")
            self.assertNotIn("MIGRATION-", evidence)

    def test_apply_preserves_existing_runtime_bytes_on_confirm_failure(self):
        """A confirmation failure must NOT touch a pre-existing runtime.json."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            runtime = root / ".governance" / "flow-unit-runtime.json"
            original = b'{"legacy":true}\r\n'
            runtime.write_bytes(original)

            result = lm.apply_migration(
                target_root=str(root), approved_unit_ids=[],
            )

            self.assertFalse(result["applied"])
            self.assertEqual(runtime.read_bytes(), original)
            self.assertFalse((root / ".governance" / "archive").exists())

    def test_apply_with_approved_subset_writes_only_those_units(self):
        """Operator-confirmed subset: apply with approved_unit_ids writes a
        runtime.json containing EXACTLY the approved units."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root, plan_text=CLI_PLAN_TRACKER)

            # Learn the candidate ids (multi-unit cli-tool derivation).
            plan = _build_cli_plan(root)
            self.assertGreaterEqual(plan.unit_count, 2)
            subset = list(plan.unit_ids[:2])

            result = lm.apply_migration(
                target_root=str(root), project_type="cli-tool",
                approved_unit_ids=subset,
            )

            self.assertTrue(result["applied"], f"subset apply failed: {result}")
            runtime = json.loads(
                (root / ".governance" / "flow-unit-runtime.json").read_text(encoding="utf-8")
            )
            written = [u["flow_unit_id"] for u in runtime["flow_units"]]
            self.assertEqual(set(written), set(subset))
            self.assertEqual(len(written), 2)
            # The persisted subset payload passes v2 completely.
            issues = flow_unit_runtime_v2.validate_flow_unit_runtime_payload_v2(runtime)
            self.assertEqual(issues, [], f"subset runtime must pass v2; got {issues}")

    def test_apply_full_set_reported_hash_matches_confirmed_full_hash(self):
        """The apply result's plan_hash (full set) equals the plan_hash a caller
        gets from confirm_decomposition(plan) with approved_unit_ids=None —
        proving apply confirms the full set and reports the confirmed hash."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            plan = lmp.build_migration_plan(str(root))
            expected_hash = lmp.confirm_decomposition(plan).plan_hash

            result = lm.apply_migration(target_root=str(root))

            self.assertTrue(result["applied"])
            self.assertEqual(result["plan_hash"], expected_hash)

    def test_apply_subset_reported_hash_matches_subset_confirmed_hash(self):
        """The apply result's plan_hash (subset) equals the plan_hash a caller
        gets from confirm_decomposition(plan, approved_unit_ids=subset) — the
        recomputed hash is reported consistently."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root, plan_text=CLI_PLAN_TRACKER)
            plan = lmp.build_migration_plan(str(root), "cli-tool")
            subset = list(plan.unit_ids[:2])
            expected_hash = lmp.confirm_decomposition(
                plan, approved_unit_ids=subset,
            ).plan_hash

            result = lm.apply_migration(
                target_root=str(root), project_type="cli-tool",
                approved_unit_ids=subset,
            )

            self.assertTrue(result["applied"])
            self.assertEqual(result["plan_hash"], expected_hash)


# ═══════════════════════════════════════════════════════════════════════════
# FIX-195 containment preserved (backup/commit/compensation unchanged)
# ═══════════════════════════════════════════════════════════════════════════


class TestFix195ContainmentPreserved(unittest.TestCase):
    """FEAT-004 inserts confirm_decomposition before plan_to_payload; the
    backup/commit/compensation scaffolding is UNCHANGED. Apply→rollback still
    restores plan-tracker + evidence-log byte-exact and removes runtime.json."""

    def test_apply_then_rollback_restores_byte_exact(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            plan_before = (root / ".governance" / "plan-tracker.md").read_bytes()
            evidence_before = (root / ".governance" / "evidence-log.md").read_bytes()

            apply_result = lm.apply_migration(target_root=str(root))
            self.assertTrue(apply_result["applied"])

            rollback_result = lm.rollback_migration(target_root=str(root))
            self.assertTrue(rollback_result["rolled_back"])

            self.assertEqual(
                (root / ".governance" / "plan-tracker.md").read_bytes(), plan_before,
                "plan-tracker must be restored byte-exact",
            )
            self.assertFalse((root / ".governance" / "flow-unit-runtime.json").is_file())
            evidence_after = (root / ".governance" / "evidence-log.md").read_text(encoding="utf-8")
            self.assertIn("ROLLBACK-", evidence_after)
            self.assertIn("EVD-001", evidence_after)
            # evidence-log restored + rollback appended: the MIGRATION row was
            # wiped by the restore, only ROLLBACK + original EVD remain.
            self.assertNotIn("MIGRATION-", evidence_after)


if __name__ == "__main__":
    unittest.main()
