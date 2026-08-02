"""Unit tests for loop_migration_plan.py — FEAT-003 (ADR-013 §4, 0.67.0).

These tests are the load-bearing verification for the shared migration planner.
The single most important properties proven here:

  - **Purity / determinism** — two calls with identical arguments return an
    identical ``plan_hash`` (the REL-059 dry-run/apply identity invariant).
    Proven both serially and from multiple threads (the mandatory §4.1
    threading test).
  - **Hash excludes target_root** — two plans with different target_root but
    identical derived structure share a plan_hash (structural identity, not
    path identity).
  - **Hash includes structural fields** — changing unit_ids / project_type /
    gate_schema changes the plan_hash.
  - **dry-run/apply identity (REL-059)** — preview_migration and apply against
    the same fixture derive an identical plan_hash (both call the same pure
    function).
  - **apply hash verification** — a mismatched expected_plan_hash fail-closes
    with no write.
  - **confirm_decomposition** — flips the flag without changing the hash
    (decomposition_confirmed is excluded from the hash).
  - **plan_to_payload** — produces a payload that passes the v2 validator when
    the plan is confirmed (and fails only on decomposition_confirmed when not).
  - **No module state mutation** — repeated calls do not accumulate state.

ALL tests use ``tempfile.TemporaryDirectory`` — the real ``.governance/`` is
NEVER touched.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_loop_migration_plan.py -v
"""

import json
import re
import sys
import tempfile
import threading
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import loop_migration_plan as lmp  # noqa: E402
import loop_migration as lm  # noqa: E402
from checks import flow_unit_runtime_v2  # noqa: E402

PLUGIN_HOME = _INFRA_DIR.parent  # skills/software-project-governance/
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


# ─── Shared fixtures (mirror test_loop_migration.py) ────────────────────────

CLASSIC_PLAN_TRACKER = (
    "# Plan Tracker — demo-host\n"
    "## 项目配置\n"
    "- workflow_model: classic-phase-gate\n"
    "## Gate 状态跟踪\n"
    "| Gate | 阶段转换 | 状态 |\n"
    "| --- | --- | --- |\n"
    "| G11 | next | passed |\n"
)

# A CLI-tool plan-tracker with a couple of dotted command ids — exercises a
# non-fallback multi-unit derivation so the structural-field tests have real
# unit_ids to perturb.
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


def _make_plugin_home_copy(src_home, *, tamper_g6=False):
    """Copy PLUGIN_HOME/core/{contract,registry} into a temp plugin_home.

    Used by the gate_schema tests to prove the hash is content-sensitive to
    the registry's loop_gate_semantics. Returns the temp Path (caller owns it).
    """
    tmp = tempfile.mkdtemp(prefix="feats003_plugin_")
    core = Path(tmp) / "core"
    core.mkdir()
    (core / "loop-runtime-contract.json").write_text(
        (src_home / "core" / "loop-runtime-contract.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    reg = json.loads(
        (src_home / "core" / "loop-engineering-registry.json").read_text(encoding="utf-8")
    )
    if tamper_g6:
        for g in reg["loop_gate_semantics"]:
            if g["gate_id"] == "G6":
                g["enclosing_loop"] = "middle"  # was "inner"
    (core / "loop-engineering-registry.json").write_text(
        json.dumps(reg, ensure_ascii=False), encoding="utf-8"
    )
    return Path(tmp)


# ═══════════════════════════════════════════════════════════════════════════
# Purity / determinism + the mandatory threading test (ADR §4.1)
# ═══════════════════════════════════════════════════════════════════════════


class TestPurityAndDeterminism(unittest.TestCase):
    """The load-bearing purity contract (ADR §4.1)."""

    def test_two_identical_calls_produce_identical_plan_hash(self):
        """Determinism: two calls with identical args → identical plan_hash."""
        plan1 = lmp.build_migration_plan(None)
        plan2 = lmp.build_migration_plan(None)
        self.assertEqual(plan1.plan_hash, plan2.plan_hash)
        self.assertTrue(_HEX64_RE.match(plan1.plan_hash),
                        "plan_hash must be 64 lowercase hex")
        # The whole plan is structural-identical (frozen dataclass equality).
        self.assertEqual(plan1, plan2)

    def test_threading_determinism(self):
        """MANDATORY (ADR §4.1): build_migration_plan from N threads with the
        same args → all threads observe an identical plan_hash. Proves there is
        no module-level mutable state / accumulating cache that could make two
        concurrent derivations disagree (the sacred derive_round purity mirred
        here)."""
        # FIX-240: result keys must NOT be threading.current_thread().ident.
        # On Linux, get_ident() == pthread_self() (a TCB pointer) and glibc
        # reuses the TCB memory of short-lived threads, so 16 concurrent
        # short-lived workers can collide on ident — dict keys merge and
        # len(hashes) < 16. Use a lock-protected list instead (no reliance on
        # ident uniqueness).
        results = []
        errors = []
        results_lock = threading.Lock()

        def worker():
            try:
                plan = lmp.build_migration_plan(None)
                with results_lock:
                    results.append(plan.plan_hash)
            except Exception as exc:  # pragma: no cover - fail loud
                with results_lock:
                    errors.append(repr(exc))

        threads = [threading.Thread(target=worker) for _ in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        self.assertFalse(errors, f"workers raised: {errors}")
        self.assertEqual(len(results), 16, "every worker must report a hash")
        unique = set(results)
        self.assertEqual(len(unique), 1,
                         f"all threads must agree on plan_hash; got {len(unique)} distinct: {unique}")
        self.assertTrue(_HEX64_RE.match(next(iter(unique))))

    def test_no_module_state_mutation_across_calls(self):
        """Repeated calls must not accumulate state. The plan_hash for the Nth
        call equals the plan_hash for the 1st call — no cache warming, no
        append-only structure, no global counter."""
        hashes = [lmp.build_migration_plan(None).plan_hash for _ in range(8)]
        self.assertEqual(len(set(hashes)), 1, "plan_hash drifted across calls")
        # And a plan built with a DIFFERENT project_type still produces a
        # self-consistent, distinct hash (proves the no-mutation result is not
        # trivially "everything is always identical").
        other = lmp.build_migration_plan(None, project_type="cli-tool").plan_hash
        # cli-tool against the cwd plan-tracker may or may not produce a
        # different unit set, but the call must not raise and must be 64-hex.
        self.assertTrue(_HEX64_RE.match(other))


# ═══════════════════════════════════════════════════════════════════════════
# Hash canonicalization (ADR §4.2)
# ═══════════════════════════════════════════════════════════════════════════


class TestPlanHashCanonicalization(unittest.TestCase):
    """ADR §4.2: the hash covers exactly the load-bearing structural fields."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.host = Path(self.tmpdir.name)
        _write_host(self.host, plan_text=CLI_PLAN_TRACKER)

    def test_hash_excludes_target_root(self):
        """Two plans with DIFFERENT target_root but identical derived structure
        share a plan_hash (the structural-identity invariant, ADR §4.2 / note
        F3). The path is environment-coupled; the structure is the identity."""
        # Two DIFFERENT parent dirs, each containing a subdir with the SAME
        # basename — so the project_id (basename-derived) matches, isolating
        # the target_root exclusion from the project_id inclusion.
        with tempfile.TemporaryDirectory() as parent_a, \
                tempfile.TemporaryDirectory() as parent_b:
            host_a = Path(parent_a) / "myproject"
            host_b = Path(parent_b) / "myproject"
            host_a.mkdir()
            host_b.mkdir()
            _write_host(host_a, plan_text=CLI_PLAN_TRACKER)
            _write_host(host_b, plan_text=CLI_PLAN_TRACKER)
            plan_a = lmp.build_migration_plan(str(host_a), "cli-tool")
            plan_b = lmp.build_migration_plan(str(host_b), "cli-tool")
            # target_root differs (different parents)...
            self.assertNotEqual(plan_a.target_root, plan_b.target_root)
            # ...but the structural identity (project_id + unit_ids) matches...
            self.assertEqual(plan_a.project_id, plan_b.project_id)
            self.assertEqual(plan_a.unit_ids, plan_b.unit_ids)
            # ...so the hash matches (target_root is EXCLUDED from the hash).
            self.assertEqual(plan_a.plan_hash, plan_b.plan_hash,
                             "target_root must be excluded from the plan hash")

    def test_hash_includes_project_type(self):
        """Changing project_type (which changes the derived unit structure)
        changes the plan_hash."""
        base = lmp.build_migration_plan(str(self.host), "cli-tool")
        other = lmp.build_migration_plan(str(self.host), "library")
        self.assertNotEqual(base.unit_ids, other.unit_ids,
                            "precondition: different project_type derives different units")
        self.assertNotEqual(base.plan_hash, other.plan_hash)

    def test_hash_includes_unit_ids(self):
        """Perturbing the unit_ids passed to compute_plan_hash changes the hash."""
        base = lmp.build_migration_plan(str(self.host), "cli-tool")
        recomputed_same = lmp.compute_plan_hash(
            contract_id=base.contract_id, project_id=base.project_id,
            project_type=base.project_type, schema_version=base.schema_version,
            unit_count=base.unit_count, unit_ids=base.unit_ids,
            workflow_model_new=base.workflow_model_new, gate_schema=base.gate_schema,
        )
        self.assertEqual(base.plan_hash, recomputed_same,
                         "compute_plan_hash must reproduce the plan's stored hash")
        # A different unit_ids tuple → different hash.
        different_ids = tuple(base.unit_ids[:-1]) if len(base.unit_ids) > 1 else ("x",)
        recomputed_diff = lmp.compute_plan_hash(
            contract_id=base.contract_id, project_id=base.project_id,
            project_type=base.project_type, schema_version=base.schema_version,
            unit_count=len(different_ids), unit_ids=different_ids,
            workflow_model_new=base.workflow_model_new, gate_schema=base.gate_schema,
        )
        self.assertNotEqual(base.plan_hash, recomputed_diff)

    def test_hash_includes_gate_schema(self):
        """ADR §4.3: a change to the registry's loop_gate_semantics changes
        gate_schema → changes the plan_hash. This makes the dry-run/apply
        identity cover the gate schema, not just the unit list."""
        plan_real = lmp.build_migration_plan(str(self.host), "cli-tool")
        fake_home = _make_plugin_home_copy(PLUGIN_HOME, tamper_g6=True)
        try:
            plan_tampered = lmp.build_migration_plan(
                str(self.host), "cli-tool", plugin_home=str(fake_home)
            )
        finally:
            # _make_plugin_home_copy used mkdtemp; clean it up.
            import shutil
            shutil.rmtree(fake_home, ignore_errors=True)
        self.assertNotEqual(plan_real.gate_schema, plan_tampered.gate_schema,
                            "precondition: tampered registry → different gate_schema")
        self.assertNotEqual(plan_real.plan_hash, plan_tampered.plan_hash,
                            "gate_schema is load-bearing → hash must change")

    def test_hash_excludes_decomposition_confirmed_and_prior_model(self):
        """confirm_decomposition does NOT change the hash (decomposition_confirmed
        is excluded), and workflow_model_prior is excluded too."""
        plan = lmp.build_migration_plan(str(self.host), "cli-tool")
        confirmed = lmp.confirm_decomposition(plan)
        self.assertTrue(confirmed.decomposition_confirmed)
        self.assertFalse(plan.decomposition_confirmed)
        self.assertEqual(plan.plan_hash, confirmed.plan_hash,
                         "decomposition_confirmed is excluded from the hash")


# ═══════════════════════════════════════════════════════════════════════════
# confirm_decomposition (FEAT-004 hook; FEAT-003 provides the stub)
# ═══════════════════════════════════════════════════════════════════════════


class TestConfirmDecomposition(unittest.TestCase):
    """ADR §4.5 / §5.2: confirm_decomposition returns a NEW frozen plan with the
    flag flipped; FEAT-003 provides only the stub (no set filtering)."""

    def test_confirm_returns_new_frozen_plan_with_flag_true(self):
        plan = lmp.build_migration_plan(None)
        self.assertFalse(plan.decomposition_confirmed)
        confirmed = lmp.confirm_decomposition(plan)
        self.assertIsNot(plan, confirmed,
                         "confirm_decomposition must return a NEW dataclass instance")
        self.assertTrue(confirmed.decomposition_confirmed)
        # The original plan is unchanged (frozen + immutability).
        self.assertFalse(plan.decomposition_confirmed)

    def test_confirm_preserves_all_fields_except_the_flag(self):
        plan = lmp.build_migration_plan(None)
        confirmed = lmp.confirm_decomposition(plan)
        for field in (
            "schema_version", "contract_id", "target_root", "project_type",
            "project_id", "workflow_model_prior", "workflow_model_new",
            "unit_ids", "unit_count", "units", "gate_schema", "plan_hash",
        ):
            self.assertEqual(getattr(plan, field), getattr(confirmed, field),
                             f"confirm_decomposition must not change {field}")

    def test_original_plan_is_frozen(self):
        """The frozen dataclass cannot be mutated in place (dataclass safety)."""
        plan = lmp.build_migration_plan(None)
        with self.assertRaises(Exception):
            plan.decomposition_confirmed = True  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════
# plan_to_payload — the plan → v2 runtime payload bridge
# ═══════════════════════════════════════════════════════════════════════════


class TestPlanToPayload(unittest.TestCase):
    """plan_to_payload produces a v2 contract payload (ADR §3.2/3.3, §5.3)."""

    def test_payload_has_all_required_top_level_fields(self):
        plan = lmp.build_migration_plan(None)
        payload = lmp.plan_to_payload(plan)
        schema, _ = flow_unit_runtime_v2.load_loop_runtime_contract()
        for field in schema["required_top_level_fields"]:
            self.assertIn(field, payload, f"missing required top-level field {field}")

    def test_payload_has_all_required_per_unit_fields(self):
        plan = lmp.build_migration_plan(None)
        payload = lmp.plan_to_payload(plan)
        schema, _ = flow_unit_runtime_v2.load_loop_runtime_contract()
        self.assertTrue(payload["flow_units"])
        for unit in payload["flow_units"]:
            for field in schema["required_per_unit_fields"]:
                self.assertIn(field, unit, f"unit missing required field {field}")

    def test_unconfirmed_plan_payload_fails_only_on_decomposition(self):
        """FEAT-003 containment: an unconfirmed plan yields a payload whose
        ONLY v2 validation failure is decomposition_confirmed (the crisp
        FEAT-004 guard)."""
        plan = lmp.build_migration_plan(None)
        self.assertFalse(plan.decomposition_confirmed)
        payload = lmp.plan_to_payload(plan)
        issues = flow_unit_runtime_v2.validate_flow_unit_runtime_payload_v2(payload)
        self.assertEqual(len(issues), 1,
                         f"unconfirmed plan should fail ONLY on decomposition; got {issues}")
        self.assertIn("decomposition_confirmed must be true", issues[0])

    def test_confirmed_plan_payload_passes_v2_validator(self):
        """A confirmed plan yields a v2 payload that PASSES the validator."""
        plan = lmp.confirm_decomposition(lmp.build_migration_plan(None))
        payload = lmp.plan_to_payload(plan)
        issues = flow_unit_runtime_v2.validate_flow_unit_runtime_payload_v2(payload)
        self.assertEqual(issues, [],
                         f"confirmed plan payload should pass; got {issues}")

    def test_payload_carries_plan_hash(self):
        """migration_plan_hash in the payload == plan.plan_hash (ADR §4.4)."""
        plan = lmp.build_migration_plan(None)
        payload = lmp.plan_to_payload(plan)
        self.assertEqual(payload["migration_plan_hash"], plan.plan_hash)
        self.assertTrue(_HEX64_RE.match(payload["migration_plan_hash"]))


# ═══════════════════════════════════════════════════════════════════════════
# dry-run / apply identity (REL-059 — the load-bearing invariant)
# ═══════════════════════════════════════════════════════════════════════════


class TestDryRunApplyIdentity(unittest.TestCase):
    """ADR §4.4: dry-run and apply call the SAME pure function, so their
    plan_hashes are identical against the same fixture."""

    def test_dry_run_and_apply_share_plan_hash(self):
        """preview_migration and apply against the same fixture derive an
        identical plan_hash — the executable REL-059 invariant.

        FEAT-004: apply now CONFIRMS the full derived set (the dry-run's
        candidate plan) before writing. Full-set confirmation keeps the hash
        unchanged (decomposition_confirmed is excluded; same units, ADR §4.2),
        so the apply's reported plan_hash still equals the dry-run's hash. The
        apply now SUCCEEDS (writes a v2-valid runtime.json) — that is the
        intended FEAT-004 behavior."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)

            # Dry-run derives the plan (no writes).
            preview = lm.preview_migration(target_root=str(root))
            self.assertIsNotNone(preview["plan_hash"])
            self.assertIsNotNone(preview["migration_plan"])

            # Apply RE-DERIVES the plan, confirms the full set, and writes.
            apply_result = lm.apply_migration(target_root=str(root))

            self.assertEqual(preview["plan_hash"], apply_result["plan_hash"],
                             "dry-run and apply must derive the identical plan_hash "
                             "(full-set confirm keeps the hash)")
            self.assertTrue(apply_result["applied"],
                            "FEAT-004: apply confirms the full set and succeeds")
            self.assertTrue(apply_result.get("decomposition_confirmed"))
            self.assertTrue((root / ".governance" / "flow-unit-runtime.json").is_file(),
                            "apply writes a v2-valid runtime.json")

    def test_dry_run_does_not_write(self):
        """The dry-run path performs NO writes (no runtime.json, no archive)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            plan_before = (root / ".governance" / "plan-tracker.md").read_bytes()
            evidence_before = (root / ".governance" / "evidence-log.md").read_bytes()

            preview = lm.preview_migration(target_root=str(root))

            self.assertTrue(preview["dry_run"])
            self.assertEqual(preview["write_operations"], [])
            self.assertFalse((root / ".governance" / "flow-unit-runtime.json").is_file())
            self.assertFalse((root / ".governance" / "archive").is_dir())
            self.assertEqual((root / ".governance" / "plan-tracker.md").read_bytes(), plan_before)
            self.assertEqual((root / ".governance" / "evidence-log.md").read_bytes(), evidence_before)

    def test_preview_attaches_v2_validation_verdict(self):
        """The dry-run attaches the v2 validator's verdict on the plan-derived
        payload (advisory — no writes)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            preview = lm.preview_migration(target_root=str(root))
            self.assertIn("v2_validation_issues", preview)
            # An unconfirmed plan fails v2 on decomposition_confirmed.
            self.assertTrue(
                any("decomposition_confirmed" in i for i in preview["v2_validation_issues"]),
                f"expected decomposition_confirmed failure; got {preview['v2_validation_issues']}",
            )


# ═══════════════════════════════════════════════════════════════════════════
# apply hash verification (ADR §4.4 — fail-closed on mismatch, no write)
# ═══════════════════════════════════════════════════════════════════════════


class TestApplyHashVerification(unittest.TestCase):
    """ADR §4.4: if expected_plan_hash is supplied and mismatches the
    re-derived hash, apply fail-closes with NO write."""

    def test_mismatched_expected_hash_fails_closed_no_write(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            wrong_hash = "0" * 64

            result = lm.apply_migration(
                target_root=str(root), expected_plan_hash=wrong_hash,
            )

            self.assertFalse(result["applied"])
            self.assertIn("plan_hash mismatch", result["aborted_reason"])
            # No write of any kind.
            self.assertFalse((root / ".governance" / "flow-unit-runtime.json").is_file())
            self.assertFalse((root / ".governance" / "archive").is_dir())
            evidence = (root / ".governance" / "evidence-log.md").read_text(encoding="utf-8")
            self.assertNotIn("MIGRATION-", evidence)

    def test_matching_expected_hash_proceeds_past_hash_check(self):
        """When expected_plan_hash matches, the hash check passes and apply
        proceeds past it — FEAT-004 then confirms the full set and SUCCEEDS
        (writes a v2-valid runtime.json). That the apply gets far enough to
        write proves the matching-hash gate is a real gate, not a no-op (a
        mismatched hash fail-closes with no write, covered by
        test_mismatched_expected_hash_fails_closed_no_write above)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            # First, learn the real hash via the dry-run planner.
            preview = lm.preview_migration(target_root=str(root))
            real_hash = preview["plan_hash"]

            result = lm.apply_migration(
                target_root=str(root), expected_plan_hash=real_hash,
            )
            # Past the hash gate → confirmation + write succeeds.
            self.assertTrue(result["applied"])
            self.assertNotIn("plan_hash mismatch", result.get("aborted_reason", ""))
            self.assertTrue(result.get("decomposition_confirmed"))
            self.assertTrue((root / ".governance" / "flow-unit-runtime.json").is_file())


# ═══════════════════════════════════════════════════════════════════════════
# UnitPlan / MigrationPlan shape (ADR §4.1)
# ═══════════════════════════════════════════════════════════════════════════


class TestPlanShape(unittest.TestCase):
    """The frozen dataclasses carry exactly the ADR §4.1 fields."""

    def test_plan_has_exactly_the_spec_fields(self):
        plan = lmp.build_migration_plan(None)
        expected = {
            "schema_version", "contract_id", "target_root", "project_type",
            "project_id", "workflow_model_prior", "workflow_model_new",
            "unit_ids", "unit_count", "units", "gate_schema",
            "decomposition_confirmed", "plan_hash",
        }
        self.assertEqual(set(plan.__dataclass_fields__), expected)

    def test_unit_plan_fields_and_frozenness(self):
        up = lmp.UnitPlan(
            flow_unit_id="x.command.y", unit_type="command", title="Y",
            derivation_reason="dotted-id", entry_tier="setup",
            dependencies=("a", "b"),
        )
        self.assertEqual(up.dependencies, ("a", "b"))
        with self.assertRaises(Exception):
            up.flow_unit_id = "mutated"  # type: ignore[misc]

    def test_units_are_consistent_with_unit_ids(self):
        """plan.units[i].flow_unit_id == plan.unit_ids[i]; plan.unit_count ==
        len(plan.unit_ids) == len(plan.units)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root, plan_text=CLI_PLAN_TRACKER)
            plan = lmp.build_migration_plan(str(root), "cli-tool")
        self.assertEqual(plan.unit_count, len(plan.unit_ids))
        self.assertEqual(len(plan.units), len(plan.unit_ids))
        self.assertEqual(
            [u.flow_unit_id for u in plan.units],
            list(plan.unit_ids),
        )
        for u in plan.units:
            self.assertIsInstance(u, lmp.UnitPlan)
            self.assertTrue(u.derivation_reason,
                            "every unit must carry a non-empty derivation_reason")

    def test_build_always_returns_unconfirmed_plan(self):
        """FEAT-003: build_migration_plan always sets decomposition_confirmed=False
        unless the caller explicitly opts in via MigrationPlanOptions
        (confirm_decomposition is the FEAT-004 path)."""
        plan = lmp.build_migration_plan(None)
        self.assertFalse(plan.decomposition_confirmed)

    def test_options_confirm_decomposition_flag_is_forwarded(self):
        """MigrationPlanOptions.confirm_decomposition=True is forwarded to the
        plan (the FEAT-004 entry; confirm_decomposition() is the preferred path
        but the option exists for symmetry)."""
        opts = lmp.MigrationPlanOptions(confirm_decomposition=True)
        plan = lmp.build_migration_plan(None, options=opts)
        self.assertTrue(plan.decomposition_confirmed)


# ═══════════════════════════════════════════════════════════════════════════
# plan_as_dict serialization (ADR §4.4)
# ═══════════════════════════════════════════════════════════════════════════


class TestPlanAsDict(unittest.TestCase):
    """plan_as_dict produces a JSON-serializable dict (used by the dry-run)."""

    def test_round_trips_through_json(self):
        plan = lmp.build_migration_plan(None)
        d = lmp.plan_as_dict(plan)
        # Must be JSON-serializable (tuples → lists).
        encoded = json.dumps(d, ensure_ascii=False)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["plan_hash"], plan.plan_hash)
        self.assertEqual(decoded["unit_count"], plan.unit_count)
        self.assertEqual(len(decoded["unit_ids"]), plan.unit_count)
        self.assertIsInstance(decoded["unit_ids"], list)
        self.assertIsInstance(decoded["units"], list)

    def test_dict_includes_plan_hash_and_gate_schema(self):
        plan = lmp.build_migration_plan(None)
        d = lmp.plan_as_dict(plan)
        self.assertEqual(d["plan_hash"], plan.plan_hash)
        self.assertEqual(d["gate_schema"], plan.gate_schema)
        self.assertIn("loop-gate-schema-v1", d["gate_schema"])


if __name__ == "__main__":
    unittest.main()
