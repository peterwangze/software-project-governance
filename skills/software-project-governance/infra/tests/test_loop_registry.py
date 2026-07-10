"""Unit tests for loop_engine.py — FX-188 (0.65.0 loop-engineering, slice 1).

These tests are the load-bearing verification for the loop-engineering
registry declaration layer:

  - ``test_g1_g11_all_have_loop_gate_semantics`` is the FAIL-on-buggy guard.
    It cross-checks the REAL lifecycle-registry.json gate ids against the
    loop_gate_semantics in loop-engineering-registry.json. If a future gate
    is added to lifecycle-registry.json without a matching loop semantic,
    this test fails — the registry must annotate every gate.
  - The remaining tests cover fail-closed loading, pause-point
    velocity-cost justification, the release-to-design-replan back-edge
    conjuncts, and fuse max_rounds parity with the ADR.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_loop_registry.py -v
or:
    python -m unittest skills.software-project-governance.infra.tests.test_loop_registry -v
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

import loop_engine  # noqa: E402

PLUGIN_HOME = _INFRA_DIR.parent  # skills/software-project-governance/
LIFECYCLE_REGISTRY = PLUGIN_HOME / "core" / "lifecycle-registry.json"


def _load_lifecycle_gate_ids():
    """Read the real lifecycle-registry.json and extract G1-G11 gate ids."""
    with open(LIFECYCLE_REGISTRY, encoding="utf-8") as fh:
        data = json.load(fh)
    gate_checks = data["gate_execution_registry"]["gate_checks"]
    return [entry["gate_id"] for entry in gate_checks]


class LoopRegistryTests(unittest.TestCase):
    # ─── Load-bearing cross-check: every lifecycle gate has a loop semantic ─
    def test_g1_g11_all_have_loop_gate_semantics(self):
        """Every gate in lifecycle-registry.json MUST have a loop_gate_semantics entry.

        This is the FAIL-on-buggy guard. If lifecycle-registry.json declares a
        gate (G1-G11) that loop-engineering-registry.json fails to annotate,
        loop topology is incomplete and this test fails.
        """
        data, issues = loop_engine.load_loop_registry(PLUGIN_HOME)
        self.assertIsNotNone(data, f"loop registry failed to load: {issues}")
        semantics = data.get("loop_gate_semantics")
        self.assertIsInstance(semantics, list, "loop_gate_semantics must be a list")
        annotated = {entry.get("gate_id") for entry in semantics if isinstance(entry, dict)}

        lifecycle_gate_ids = _load_lifecycle_gate_ids()
        # Sanity: the lifecycle registry really does declare G1-G11.
        self.assertEqual(
            lifecycle_gate_ids,
            ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10", "G11"],
            "lifecycle-registry.json gate order/content drifted; update this test deliberately",
        )

        missing = [gid for gid in lifecycle_gate_ids if gid not in annotated]
        self.assertFalse(
            missing,
            f"loop_gate_semantics missing entries for gates: {missing}",
        )

    def test_loop_gate_semantics_field_values_for_each_gate(self):
        """Each loop_gate_semantics entry must carry the required declaration fields."""
        data, issues = loop_engine.load_loop_registry(PLUGIN_HOME)
        self.assertIsNotNone(data, f"loop registry failed to load: {issues}")
        required_fields = {"gate_id", "loop_role", "enclosing_loop", "on_fail", "fuse_ref"}
        for entry in data["loop_gate_semantics"]:
            missing = required_fields - set(entry)
            self.assertFalse(missing, f"{entry.get('gate_id')}: missing fields {missing}")

    def test_get_loop_gate_semantics_lookup(self):
        g6 = loop_engine.get_loop_gate_semantics("G6", PLUGIN_HOME)
        self.assertIsNotNone(g6)
        self.assertEqual(g6["gate_id"], "G6")
        self.assertEqual(g6["loop_role"], "loop-body")
        self.assertEqual(g6["enclosing_loop"], "inner")
        self.assertEqual(g6["fuse_ref"], "FUSE-INNER-DEFAULT")
        # Unknown gate id is None (fail-closed).
        self.assertIsNone(loop_engine.get_loop_gate_semantics("G99", PLUGIN_HOME))

    # ─── Pause points ───────────────────────────────────────────────────────
    def test_pause_points_have_velocity_justification(self):
        """Every PausePoint MUST carry a non-empty velocity_cost_justification."""
        data, issues = loop_engine.load_loop_registry(PLUGIN_HOME)
        self.assertIsNotNone(data, f"loop registry failed to load: {issues}")
        pause_points = data.get("pause_points")
        self.assertIsInstance(pause_points, dict, "pause_points must be an object")
        self.assertGreaterEqual(len(pause_points), 5, "expected at least the 5 ADR pause points")
        for pp_id, pp in pause_points.items():
            self.assertIsInstance(pp, dict, f"{pp_id} must be an object")
            justification = pp.get("velocity_cost_justification")
            self.assertIsInstance(
                justification, str,
                f"{pp_id}: velocity_cost_justification must be a string",
            )
            self.assertTrue(
                justification.strip(),
                f"{pp_id}: velocity_cost_justification must be non-empty",
            )

    def test_get_pause_point_lookup(self):
        pp = loop_engine.get_pause_point("PP-Fuse-Escalate", PLUGIN_HOME)
        self.assertIsNotNone(pp)
        self.assertTrue(pp["active"])
        self.assertIsNone(loop_engine.get_pause_point("PP-Does-Not-Exist", PLUGIN_HOME))

    # ─── Back-edge conjuncts ────────────────────────────────────────────────
    def test_release_to_design_replan_back_edge(self):
        """The release-to-design-replan back-edge must declare all three conjuncts
        and have auto_fire=False (no automatic Middle-loop restart)."""
        data, issues = loop_engine.load_loop_registry(PLUGIN_HOME)
        self.assertIsNotNone(data, f"loop registry failed to load: {issues}")
        back_edges = data.get("back_edges")
        self.assertIsInstance(back_edges, dict, "back_edges must be an object")
        edge = back_edges.get("release-to-design-replan")
        self.assertIsInstance(edge, dict, "release-to-design-replan back-edge missing")

        self.assertEqual(edge["from_stage"], "release")
        self.assertEqual(edge["to_stage"], "architecture")
        self.assertEqual(edge["auto_fire"], False, "back-edge must NOT auto-fire")

        trigger = edge.get("trigger")
        self.assertIsInstance(trigger, dict, "trigger must be an object")
        conjuncts = trigger.get("requires_all_of")
        self.assertIsInstance(conjuncts, list, "requires_all_of must be a list")
        self.assertEqual(len(conjuncts), 3, "exactly three conjuncts required")

        # Each conjunct must reference a gate or pause_point.
        refs = []
        for conjunct in conjuncts:
            self.assertIsInstance(conjunct, dict)
            if "gate" in conjunct:
                refs.append(("gate", conjunct["gate"]))
            if "pause_point" in conjunct:
                refs.append(("pause_point", conjunct["pause_point"]))
        ref_keys = {value for _kind, value in refs}
        self.assertIn("G9", ref_keys, "G9 fail conjunct required")
        self.assertIn("G5", ref_keys, "G5 concurrence conjunct required")
        self.assertIn(
            "PP-Fuse-Escalate", ref_keys,
            "PP-Fuse-Escalate human-approval conjunct required",
        )

    # ─── Fail-closed loader ─────────────────────────────────────────────────
    def test_loader_fail_closed_on_corrupt_json(self):
        """A corrupt JSON file must yield (None, [diagnostic]) and never raise."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_home = Path(tmpdir)
            core_dir = plugin_home / "core"
            core_dir.mkdir(parents=True)
            registry_path = core_dir / "loop-engineering-registry.json"
            registry_path.write_text("{ this is :: not valid JSON ]]", encoding="utf-8")

            data, issues = loop_engine.load_loop_registry(plugin_home)
            self.assertIsNone(data, "corrupt JSON must return None data")
            self.assertIsInstance(issues, list)
            self.assertGreaterEqual(len(issues), 1, "corrupt JSON must produce a diagnostic")
            self.assertTrue(
                any("invalid JSON" in str(issue) for issue in issues),
                f"diagnostic should mention invalid JSON: {issues}",
            )

    def test_loader_fail_closed_on_missing_file(self):
        """A missing registry file must yield (None, [diagnostic]) and never raise."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_home = Path(tmpdir)
            # Note: deliberately do NOT create core/loop-engineering-registry.json
            data, issues = loop_engine.load_loop_registry(plugin_home)
            self.assertIsNone(data, "missing file must return None data")
            self.assertIsInstance(issues, list)
            self.assertGreaterEqual(len(issues), 1, "missing file must produce a diagnostic")
            self.assertTrue(
                any("missing" in str(issue) for issue in issues),
                f"diagnostic should mention missing: {issues}",
            )

    # ─── Fuse values parity with the ADR ────────────────────────────────────
    def test_fuse_values_match_adr(self):
        """Fuse max_rounds must match ADR §4: setup=2, inner=5, middle=3, outer=2."""
        self.assertEqual(loop_engine.get_fuse("FUSE-SETUP-DEFAULT", PLUGIN_HOME)["max_rounds"], 2)
        self.assertEqual(loop_engine.get_fuse("FUSE-INNER-DEFAULT", PLUGIN_HOME)["max_rounds"], 5)
        self.assertEqual(loop_engine.get_fuse("FUSE-MIDDLE-DEFAULT", PLUGIN_HOME)["max_rounds"], 3)
        self.assertEqual(loop_engine.get_fuse("FUSE-OUTER-DEFAULT", PLUGIN_HOME)["max_rounds"], 2)

    def test_fuse_escalation_exits_declared(self):
        for fuse_id, expected_exit in (
            ("FUSE-SETUP-DEFAULT", "initiation-re-scope"),
            ("FUSE-INNER-DEFAULT", "askuser-escalation"),
            ("FUSE-MIDDLE-DEFAULT", "askuser-escalation"),
            ("FUSE-OUTER-DEFAULT", "strategy-review"),
        ):
            fuse = loop_engine.get_fuse(fuse_id, PLUGIN_HOME)
            self.assertIsNotNone(fuse, f"{fuse_id} missing")
            self.assertEqual(fuse["escalation_exit"], expected_exit)
            self.assertEqual(fuse["loop_tier"], fuse_id.split("-")[1].lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
