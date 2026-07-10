"""Unit tests for loop_health.py — FX-192 (0.65.0 loop-engineering, slice 5).

These tests are the load-bearing verification for the loop-health Check
(ADR §9.5), split across the three sub-checks:

  - **Part 1 (BLOCKING)** — active PausePoint missing velocity_cost_justification
    → FAIL finding. Tests 1-3 cover active-missing / active-present / inactive.
  - **Part 2 (ADVISORY)** — measured cost > 3× bound for 3 consecutive
    iterations → advisory (promotable to FAIL). Tests 4-6 cover the exceedance,
    the below-threshold boundary, and the blocking promotion.
  - **DORA bridge (§3.6)** — change failure rate / deployment frequency.
    Test 7 covers the fuse-trip fraction computation.
  - **Graceful absence** — Test 8 proves no crash when runtime.json is missing.
  - **Dogfood compliance** — Test 9 is the integration guard: the REAL
    loop-engineering-registry.json must PASS Part 1 (all 5 active PPs carry a
    justification). This is the proof that the dogfood registry is compliant.

Part 1 tests use temporary registries (via ``tempfile``) so they never touch
the real ``core/loop-engineering-registry.json``. Part 2 / DORA tests pass
in-memory runtime dicts (no file IO needed).

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_loop_health.py -v
or:
    python -m unittest skills.software-project-governance.infra.tests.test_loop_health -v
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
# Part 2 — ADVISORY: sustained measured-cost exceedance
# ═══════════════════════════════════════════════════════════════════════════


class Part2VelocityExceedanceTests(unittest.TestCase):
    """ADR §9.5 part 2 — measured > 3× bound for 3 consecutive iterations."""

    def test_part2_advisory_on_exceedance_3x_3iter(self):
        """Test 4: 3 consecutive samples above 3× bound → ADVISORY finding."""
        runtime = {
            "velocity_history": {
                "PP-X": {
                    "declared_bound_ms": 1000,
                    # 7000, 7200, 7100 all > 3000 (3× bound) → 3 consecutive.
                    "measured_ms": [7000, 7200, 7100],
                },
            },
        }
        findings = lh._check_velocity_exceedance(runtime)
        self.assertEqual(len(findings), 1, f"expected 1 advisory, got {findings}")
        self.assertEqual(findings[0]["severity"], "ADVISORY")
        self.assertEqual(findings[0]["pause_point"], "PP-X")

    def test_part2_no_flag_below_threshold(self):
        """Test 5: boundary — only 2 iterations OR only 2× → no flag."""
        with self.subTest(case="only-2-consecutive"):
            # 3 samples but the last breaks the run (≤ 3× bound) → run resets to 0.
            runtime = {
                "velocity_history": {
                    "PP-Y": {
                        "declared_bound_ms": 1000,
                        # 3500 (>3×), 3600 (>3×), then 2000 (≤3×) breaks run.
                        "measured_ms": [3500, 3600, 2000],
                    },
                },
            }
            self.assertEqual(lh._check_velocity_exceedance(runtime), [])

        with self.subTest(case="only-2x-not-3x"):
            # 3 samples but all at 2× bound (< 3× threshold) → never exceeds.
            runtime = {
                "velocity_history": {
                    "PP-Z": {
                        "declared_bound_ms": 1000,
                        "measured_ms": [2000, 2000, 2000],
                    },
                },
            }
            self.assertEqual(lh._check_velocity_exceedance(runtime), [])

    def test_part2_blocking_flag_promotes_to_fail(self):
        """Test 6: velocity_check_blocking=True promotes ADVISORY → FAIL."""
        runtime = {
            "velocity_history": {
                "PP-X": {
                    "declared_bound_ms": 1000,
                    "measured_ms": [7000, 7200, 7100],
                },
            },
        }
        findings = lh._check_velocity_exceedance(runtime, blocking=True)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["severity"], "FAIL",
            f"blocking flag must promote to FAIL, got {findings[0]['severity']}",
        )


# ═══════════════════════════════════════════════════════════════════════════
# DORA bridge (§3.6) — change failure rate / deployment frequency
# ═══════════════════════════════════════════════════════════════════════════


class DoraMetricsTests(unittest.TestCase):
    """ADR §3.6 — DORA-bridge advisory metrics computed from runtime data."""

    def test_dora_change_failure_rate(self):
        """Test 7: 2 fuse trips out of 5 loops → CFR = 0.4 reported."""
        runtime = {
            "dora": {
                "total_loops": 5,
                "fuse_trips": 2,
                "release_gate_passes": 3,
            },
        }
        metrics = lh._compute_dora_metrics(runtime)
        self.assertEqual(metrics["total_loops"], 5)
        self.assertEqual(metrics["fuse_trips"], 2)
        self.assertEqual(metrics["release_gate_passes"], 3)
        self.assertEqual(metrics["deployment_frequency"], 3)
        self.assertAlmostEqual(metrics["change_failure_rate"], 0.4)


# ═══════════════════════════════════════════════════════════════════════════
# Graceful absence — runtime.json missing never crashes
# ═══════════════════════════════════════════════════════════════════════════


class GracefulAbsenceTests(unittest.TestCase):
    """No runtime.json → Part 2 + DORA return empty; Part 1 still runs."""

    def test_no_runtime_data_no_crash(self):
        """Test 8: absent runtime.json → Part 2/DORA no-op, Part 1 runs fine."""
        with tempfile.TemporaryDirectory() as td:
            home = _write_registry(Path(td), {"PP-Active-OK": _PP_ACTIVE_OK})
            # _load_runtime with a target that has no .governance/ → None.
            result = lh.check_loop_health(
                target=str(Path(td)),
                plugin_home=home,
            )

        findings = result["findings"]
        # Part 1 ran (registry-only) and found no violations.
        self.assertEqual(
            [f for f in findings if f["severity"] == "FAIL"], [],
            f"compliant registry must yield no FAILs: {findings}",
        )
        # Part 2 (needs runtime) produced no findings — no crash.
        self.assertEqual(
            [f for f in findings if f["severity"] == "ADVISORY"], [],
            f"absent runtime must yield no advisory findings: {findings}",
        )
        # DORA returned an empty dict (no runtime data).
        self.assertEqual(result["dora_metrics"], {})
        # Summary counts are sane.
        self.assertEqual(result["summary"]["blocking_count"], 0)
        self.assertEqual(result["summary"]["advisory_count"], 0)

    def test_part2_none_runtime_returns_empty(self):
        """Passing None runtime to Part 2 directly → empty findings."""
        self.assertEqual(lh._check_velocity_exceedance(None), [])

    def test_dora_none_runtime_returns_empty(self):
        """Passing None runtime to DORA directly → empty metrics."""
        self.assertEqual(lh._compute_dora_metrics(None), {})


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
    """The top-level envelope composes Part 1 + Part 2 + DORA + summary."""

    def test_envelope_shape_and_keys(self):
        """The result envelope exposes findings / dora_metrics / summary / boundary."""
        with tempfile.TemporaryDirectory() as td:
            home = _write_registry(Path(td), {"PP-Active-OK": _PP_ACTIVE_OK})
            result = lh.check_loop_health(
                target=str(Path(td)),
                plugin_home=home,
            )

        for key in ("findings", "dora_metrics", "summary", "no_overclaim_boundary"):
            self.assertIn(key, result, f"envelope missing key: {key}")
        self.assertIsInstance(result["findings"], list)
        self.assertIsInstance(result["dora_metrics"], dict)
        self.assertIn("blocking_count", result["summary"])
        self.assertIn("advisory_count", result["summary"])
        self.assertIsInstance(result["no_overclaim_boundary"], str)

    def test_envelope_fail_closed_on_corrupt_registry(self):
        """A corrupt registry path → fail-closed, never raises (empty Part 1)."""
        # Point plugin_home at a temp dir with NO registry → loader returns None.
        with tempfile.TemporaryDirectory() as td:
            result = lh.check_loop_health(
                target=str(Path(td)),
                plugin_home=str(Path(td)),  # no core/loop-engineering-registry.json
            )
        # Part 1 fail-closed → no findings; Part 2/DORA no runtime → empty.
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["summary"]["blocking_count"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
