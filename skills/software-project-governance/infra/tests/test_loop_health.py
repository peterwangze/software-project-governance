"""Check pause-point authority and the separation from event observations."""

import argparse
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import loop_health as lh  # noqa: E402
import loop_engine  # noqa: E402

PLUGIN_HOME = _INFRA_DIR.parent  # skills/software-project-governance/
REAL_LOOP_REGISTRY = PLUGIN_HOME / "core" / "loop-engineering-registry.json"


# ─── Registry fixtures ───────────────────────────────────────────────────────

def _make_registry(pause_points):
    """Build a minimal loop-engineering registry dict with the given pause points.

    ``pause_points`` is a dict of {pp_id: entry}. Other top-level keys required
    by the schema are filled with empty/placeholder values — only pause_points
    is exercised by Part 1.
    """
    return {
        "$schema": "https://example.com/software-project-governance/loop-engineering-registry-v1.json",
        "schema_version": "1.0",
        "workflow_version": "0.65.0",
        "pause_points": pause_points,
    }


def _write_registry(host_root, pause_points):
    """Write a loop-engineering-registry.json into host_root/core/.

    Returns the host_root (suitable to pass as ``plugin_home``).
    """
    core = host_root / "core"
    core.mkdir(parents=True, exist_ok=True)
    (core / "loop-engineering-registry.json").write_text(
        json.dumps(_make_registry(pause_points), indent=2), encoding="utf-8"
    )
    return host_root


def _write_raw_registry(host_root, content):
    """Write an exact registry payload for authority-negative tests."""
    core = host_root / "core"
    core.mkdir(parents=True, exist_ok=True)
    path = core / "loop-engineering-registry.json"
    path.write_text(content, encoding="utf-8")
    return host_root


# A PP that is active AND justified (compliant).
_PP_ACTIVE_OK = {
    "location": "between plan and act phases",
    "trigger": "scope-change",
    "velocity_cost_ms": None,
    "velocity_cost_justification": "Plan approval prevents expensive rework.",
    "active": True,
}

# A PP that is active but MISSING justification (violation).
_PP_ACTIVE_NO_JUST = {
    "location": "between implement and review",
    "trigger": "before review",
    "velocity_cost_ms": None,
    "velocity_cost_justification": "",   # blank → violation
    "active": True,
}

# A PP that is INACTIVE with missing justification — must NOT be flagged.
_PP_INACTIVE_NO_JUST = {
    "location": "dormant checkpoint",
    "trigger": "never",
    "velocity_cost_ms": None,
    "velocity_cost_justification": None,  # missing, but PP is inactive
    "active": False,
}


# ═══════════════════════════════════════════════════════════════════════════
# Part 1 — BLOCKING: velocity-cost justification on active PausePoints
# ═══════════════════════════════════════════════════════════════════════════


class Part1VelocityJustificationTests(unittest.TestCase):
    """ADR §9.5 part 1 — active PP must justify its velocity cost."""

    def test_part1_active_pp_missing_justification_fails(self):
        """Test 1: an active PP with blank justification → FAIL finding."""
        with tempfile.TemporaryDirectory() as td:
            home = _write_registry(Path(td), {
                "PP-Active-OK": _PP_ACTIVE_OK,
                "PP-Active-Missing": _PP_ACTIVE_NO_JUST,
            })
            findings = lh._check_velocity_justification(plugin_home=home)

        fails = [f for f in findings if f["severity"] == "FAIL"]
        self.assertEqual(len(fails), 1, f"expected 1 FAIL, got {findings}")
        self.assertEqual(fails[0]["pause_point"], "PP-Active-Missing")
        self.assertIn("DEC-097 part 2", fails[0]["message"])

    def test_part1_active_pp_with_justification_passes(self):
        """Test 2: all active PPs justified → no FAIL findings."""
        with tempfile.TemporaryDirectory() as td:
            home = _write_registry(Path(td), {
                "PP-A": _PP_ACTIVE_OK,
                "PP-B": dict(_PP_ACTIVE_OK, velocity_cost_justification="another reason"),
            })
            findings = lh._check_velocity_justification(plugin_home=home)

        fails = [f for f in findings if f["severity"] == "FAIL"]
        self.assertEqual(fails, [], f"expected no FAILs, got {findings}")

    def test_part1_inactive_pp_skipped(self):
        """Test 3: an inactive PP with missing justification is NOT flagged."""
        with tempfile.TemporaryDirectory() as td:
            home = _write_registry(Path(td), {
                "PP-Inactive": _PP_INACTIVE_NO_JUST,
                "PP-Active-OK": _PP_ACTIVE_OK,
            })
            findings = lh._check_velocity_justification(plugin_home=home)

        # Only active PPs are checked; the inactive one is skipped.
        flagged = [f["pause_point"] for f in findings]
        self.assertNotIn("PP-Inactive", flagged)
        self.assertEqual(
            [f for f in findings if f["severity"] == "FAIL"], [],
            f"inactive PP must not produce findings: {findings}",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Dogfood compliance — integration guard against the REAL registry
# ═══════════════════════════════════════════════════════════════════════════


class DogfoodRegistryTests(unittest.TestCase):
    """The REAL loop-engineering-registry.json must be Part-1 compliant."""

    def test_dogfood_registry_all_5_pps_pass_part1(self):
        """Test 9: load the REAL registry → all 5 active PPs are justified.

        This is the integration proof that the dogfood registry is compliant
        with ADR §9.5 part 1: every active PausePoint carries a non-empty
        velocity_cost_justification. If a future edit adds an active PP without
        justification, this test fails.
        """
        self.assertTrue(
            REAL_LOOP_REGISTRY.exists(),
            f"real registry missing at {REAL_LOOP_REGISTRY}",
        )
        findings = lh._check_velocity_justification(plugin_home=PLUGIN_HOME)

        # Cross-check: the registry really does declare 5 active PPs (so this
        # test is not vacuously passing on an empty registry).
        data, _issues = loop_engine.load_loop_registry(PLUGIN_HOME)
        active_pps = [
            pp_id for pp_id, entry in data["pause_points"].items()
            if isinstance(entry, dict) and entry.get("active", False)
        ]
        self.assertEqual(
            len(active_pps), 5,
            f"expected 5 active PPs in dogfood registry, got {active_pps}",
        )

        # All 5 active PPs must be justified → zero FAIL findings.
        self.assertEqual(
            findings, [],
            f"dogfood registry has unjustified active PPs: {findings}",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Envelope shape — check_loop_health composes all three sub-checks
# ═══════════════════════════════════════════════════════════════════════════


class CheckLoopHealthEnvelopeTests(unittest.TestCase):
    def test_unmeasured_runtime_counters_do_not_score_the_project(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_registry(root, {"PP": _PP_ACTIVE_OK})
            gov = root / ".governance"
            gov.mkdir()
            (gov / "flow-unit-runtime.json").write_text(json.dumps({
                "dora": {"release_gate_passes": 8, "fuse_trips": 5, "total_loops": 7},
                "velocity_history": {"PP": {"declared_bound_ms": 1, "measured_ms": [999] * 3}},
            }), encoding="utf-8")
            result = lh.check_loop_health(target=root, plugin_home=root)
        self.assertEqual({"findings", "telemetry", "summary"}, set(result))
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["telemetry"]["status"], "unknown")
        self.assertEqual(result["telemetry"]["flow"]["blocked_wait_time"]["value"], None)

    def test_envelope_fail_closed_on_missing_registry_authority(self):
        """A missing registry produces a blocking authority diagnostic."""
        with tempfile.TemporaryDirectory() as td:
            result = lh.check_loop_health(
                target=str(Path(td)),
                plugin_home=str(Path(td)),  # no core/loop-engineering-registry.json
            )
        self.assertGreater(result["summary"]["blocking_count"], 0)
        self.assertEqual(result["findings"][0]["severity"], "FAIL")
        self.assertEqual(result["findings"][0]["pause_point"], "registry-authority")
        self.assertIn(
            "missing loop-engineering registry", result["findings"][0]["message"]
        )

    def test_envelope_fail_closed_on_invalid_json_registry(self):
        """Invalid JSON authority is blocking and preserves its diagnostic."""
        with tempfile.TemporaryDirectory() as td:
            home = _write_raw_registry(Path(td), "{not-json")
            result = lh.check_loop_health(target=str(Path(td)), plugin_home=home)
        self.assertGreater(result["summary"]["blocking_count"], 0)
        self.assertIn("invalid JSON", result["findings"][0]["message"])

    def test_envelope_fail_closed_on_non_object_registry(self):
        """A valid JSON non-object cannot serve as registry authority."""
        with tempfile.TemporaryDirectory() as td:
            home = _write_raw_registry(Path(td), "[]")
            result = lh.check_loop_health(target=str(Path(td)), plugin_home=home)
        self.assertGreater(result["summary"]["blocking_count"], 0)
        self.assertIn("registry root must be an object", result["findings"][0]["message"])

    def test_envelope_fail_closed_on_invalid_pause_points(self):
        """The authority requires pause_points to be an object."""
        with tempfile.TemporaryDirectory() as td:
            home = _write_raw_registry(Path(td), json.dumps({"pause_points": []}))
            result = lh.check_loop_health(target=str(Path(td)), plugin_home=home)
        self.assertGreater(result["summary"]["blocking_count"], 0)
        self.assertIn("pause_points must be an object", result["findings"][0]["message"])

    def test_envelope_fail_closed_on_empty_pause_points(self):
        """An empty pause-point authority must not pass vacuously."""
        with tempfile.TemporaryDirectory() as td:
            home = _write_raw_registry(Path(td), json.dumps({"pause_points": {}}))
            result = lh.check_loop_health(target=str(Path(td)), plugin_home=home)
        self.assertGreater(result["summary"]["blocking_count"], 0)
        self.assertIn("pause_points must not be empty", result["findings"][0]["message"])

    def test_envelope_fail_closed_on_non_object_pause_point_entry(self):
        """Every pause_points member must be a structured authority entry."""
        with tempfile.TemporaryDirectory() as td:
            home = _write_raw_registry(
                Path(td), json.dumps({"pause_points": {"PP-Bad": "not-an-object"}})
            )
            result = lh.check_loop_health(target=str(Path(td)), plugin_home=home)
        self.assertGreater(result["summary"]["blocking_count"], 0)
        self.assertIn("entry PP-Bad must be an object", result["findings"][0]["message"])

    def test_envelope_fail_closed_when_loader_returns_data_and_issues(self):
        """Loader diagnostics remain blocking even when parsed data is usable."""
        registry = _make_registry({"PP-Active-OK": _PP_ACTIVE_OK})
        with patch.object(
            lh, "load_loop_registry", return_value=(registry, ["authority checksum mismatch"])
        ):
            result = lh.check_loop_health(plugin_home=PLUGIN_HOME)
        self.assertGreater(result["summary"]["blocking_count"], 0)
        self.assertIn("authority checksum mismatch", result["findings"][0]["message"])

    def test_envelope_fail_closed_on_pause_point_missing_active(self):
        """A PausePoint without an explicit active boolean is invalid authority."""
        entry = dict(_PP_ACTIVE_OK)
        entry.pop("active")
        with tempfile.TemporaryDirectory() as td:
            home = _write_registry(Path(td), {"PP-Missing-Active": entry})
            result = lh.check_loop_health(target=str(Path(td)), plugin_home=home)
        self.assertGreater(result["summary"]["blocking_count"], 0)
        self.assertIn("active as a boolean", result["findings"][0]["message"])

    def test_envelope_fail_closed_on_pause_point_string_active(self):
        """Truth-like strings cannot substitute for the authority's boolean field."""
        entry = dict(_PP_ACTIVE_OK, active="false")
        with tempfile.TemporaryDirectory() as td:
            home = _write_registry(Path(td), {"PP-String-Active": entry})
            result = lh.check_loop_health(target=str(Path(td)), plugin_home=home)
        self.assertGreater(result["summary"]["blocking_count"], 0)
        self.assertIn("active as a boolean", result["findings"][0]["message"])

    def test_cli_fail_on_issues_exits_nonzero_for_authority_failure(self):
        """The unchanged verify_workflow adapter consumes authority FAIL findings."""
        import verify_workflow as vw

        with tempfile.TemporaryDirectory() as td:
            args = argparse.Namespace(target=str(Path(td)), fail_on_issues=True)
            output = io.StringIO()
            with patch.object(loop_engine, "PLUGIN_HOME", Path(td)):
                with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
                    vw.cmd_check_loop_health(args)
        self.assertEqual(raised.exception.code, 1)
        self.assertIn("registry-authority", output.getvalue())
        self.assertIn("1 BLOCKING", output.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
