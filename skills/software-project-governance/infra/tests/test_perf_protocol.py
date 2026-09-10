"""FEAT-018 perf-protocol tests — pure-function faces + injected slow paths.

Every slow path (real subprocess sampling: status / check-governance /
importtime probes) is *injected* via ``unittest.mock.patch`` on this
module's own functions — the repo precedent is
``test_archguard_ratchet.R5StartupBudgetTests`` patching
``ar.r5_live_faces``. No real sampling runs here: the unit face stays
fast and deterministic; the real dual baseline is produced by the CLI
run recorded in the FEAT-018 evidence row.

Cross-validations against the upstream anchors:
  - tolerance initial values come from evolution §9.5 item 5
    (median rel ≤10%, P95 rel ≤25% — hypothesis, to calibrate);
  - the R6 threshold fill must stay key-compatible with
    ``core/architecture-baseline.json`` ``r6_startup_budget.threshold``
    (currently ``null`` — FEAT-018 fills it; advisory until then);
  - load class is a first-class covariate (AUDIT-151 / RISK-048:
    serial-exclusive vs parallel-observed must never be conflated).

Run:
    python -m unittest skills/software-project-governance/infra.tests.test_perf_protocol -v
"""

import json
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
_SKILL_ROOT = _INFRA_DIR.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import perf_protocol as pp  # noqa: E402

ENGINE = _INFRA_DIR / "verify_workflow.py"
TOLERANCE_FILE = _SKILL_ROOT / "core" / "perf-tolerance.json"

# Real CPython 3.x ``-X importtime`` stderr shape (header line + data rows
# with ``self | cumulative | indent module``). One malformed row proves the
# parser's disclosed tolerance.
IMPORTTIME_SAMPLE = (
    "import time: self [us] | cumulative | imported package\n"
    "       1710 |     27761 |   io\n"
    "        151 |      1184 |     abc\n"
    "  bad line without pipes\n"
    "       6169 |      6169 | encodings\n"
    "        148 |       148 |     _codecs\n"
)


class PercentileStatsTests(unittest.TestCase):
    def test_median_and_percentile_known_values(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertEqual(pp.median(values), 3.0)
        # Linear interpolation on rank = (n-1)*p/100 = 3.8 → 4*0.2 + 5*0.8.
        self.assertAlmostEqual(pp.percentile(values, 95), 4.8)
        self.assertEqual(pp.percentile(values, 0), 1.0)
        self.assertEqual(pp.percentile(values, 50), 3.0)

    def test_percentile_interpolates_between_ranks(self):
        # rank = (4-1)*0.95 = 2.85 → between 30 and 40: 30*0.15 + 40*0.85
        values = [10.0, 20.0, 30.0, 40.0]
        self.assertAlmostEqual(pp.percentile(values, 95), 38.5)
        # Documented degenerate calibers: single sample = itself.
        self.assertEqual(pp.percentile([7.0], 95), 7.0)

    def test_summarize_samples_shape(self):
        stats = pp.summarize_samples([0.5, 0.6, 0.7, 0.8, 2.0])
        self.assertEqual(stats["n"], 5)
        self.assertEqual(stats["min"], 0.5)
        self.assertEqual(stats["max"], 2.0)
        self.assertEqual(stats["median"], 0.7)  # statistics.median: middle value
        self.assertAlmostEqual(stats["p95"], 1.76)  # rank 3.8 → 0.8*0.2+2.0*0.8

    def test_split_cold_warm(self):
        cold, warm = pp.split_cold_warm([9.9, 1.0, 1.1, 1.2])
        self.assertEqual(cold, 9.9)
        self.assertEqual(warm, [1.0, 1.1, 1.2])
        # §9.5 caliber: cold = first run of this command in this session;
        # single-sample degenerate case keeps cold, empty warm.
        cold2, warm2 = pp.split_cold_warm([4.2])
        self.assertEqual(cold2, 4.2)
        self.assertEqual(warm2, [])


class ImporttimeParseTests(unittest.TestCase):
    def test_parse_importtime_cpython_format(self):
        segments = pp.parse_importtime(IMPORTTIME_SAMPLE)
        self.assertEqual(len(segments), 4)
        by_name = {s["module"]: s for s in segments}
        self.assertEqual(by_name["io"]["self_us"], 1710)
        self.assertEqual(by_name["io"]["cumulative_us"], 27761)
        self.assertEqual(by_name["_codecs"]["depth"], 2)

    def test_import_totals_and_top_n(self):
        segments = pp.parse_importtime(IMPORTTIME_SAMPLE)
        totals = pp.import_totals(segments)
        self.assertEqual(totals["import_events"], 4)
        self.assertEqual(totals["self_total_us"], 1710 + 151 + 6169 + 148)
        top = pp.top_imports(segments, 2)
        self.assertEqual([t["module"] for t in top], ["encodings", "io"])
        self.assertEqual(top[0]["self_us"], 6169)

    def test_parse_importtime_malformed_rows_disclosed(self):
        segments = skipped = None
        segments, skipped = pp.parse_importtime(
            IMPORTTIME_SAMPLE, return_skipped=True)
        self.assertEqual(len(segments), 4)
        self.assertEqual(skipped, 2)  # header + pipe-less row, disclosed


class ToleranceTests(unittest.TestCase):
    def test_judge_tolerance_within_band_passes(self):
        verdict = pp.judge_tolerance(
            observed_s=0.62, baseline_s=0.60, metric="median",
            median_rel=0.10, p95_rel=0.25, abs_floor_s=0.05)
        # band = max(0.60*0.10, 0.05) = 0.06 ≥ delta 0.02 → PASS
        self.assertEqual(verdict["verdict"], "PASS")
        self.assertAlmostEqual(verdict["allowed_band_s"], 0.06)

    def test_judge_tolerance_relative_breach_fails(self):
        verdict = pp.judge_tolerance(
            observed_s=0.70, baseline_s=0.60, metric="median",
            median_rel=0.10, p95_rel=0.25, abs_floor_s=0.05)
        self.assertEqual(verdict["verdict"], "FAIL")
        self.assertGreater(verdict["delta_s"], verdict["allowed_band_s"])

    def test_judge_tolerance_p95_uses_p95_rel(self):
        verdict = pp.judge_tolerance(
            observed_s=0.80, baseline_s=0.60, metric="p95",
            median_rel=0.10, p95_rel=0.25, abs_floor_s=0.05)
        # band = max(0.60*0.25, 0.05) = 0.15 ≥ delta 0.20 → FAIL
        self.assertEqual(verdict["verdict"], "FAIL")

    def test_judge_tolerance_abs_floor_dominates_small_baseline(self):
        # Tiny baseline: 0.20*0.10 = 0.02 < floor 0.05 → the absolute floor
        # widens the band so jitter on small numbers cannot fake a FAIL.
        verdict = pp.judge_tolerance(
            observed_s=0.24, baseline_s=0.20, metric="median",
            median_rel=0.10, p95_rel=0.25, abs_floor_s=0.05)
        self.assertEqual(verdict["verdict"], "PASS")
        self.assertAlmostEqual(verdict["allowed_band_s"], 0.05)

    def test_committed_tolerance_table_valid_and_r6_aligned(self):
        """Acceptance ③ — the committed table validates and its R6 fill is
        key-compatible with architecture-baseline.json's threshold face."""
        data = json.loads(TOLERANCE_FILE.read_text(encoding="utf-8"))
        errors = pp.validate_tolerance_table(data)
        self.assertEqual(errors, [])
        fill = data["r6_threshold_fill"]
        for key in ("wall_ms_rel_median", "wall_ms_rel_p95",
                    "abs_floor_s", "import_count_max_delta"):
            self.assertIn(key, fill)
        self.assertLessEqual(fill["wall_ms_rel_median"], 0.10)  # §9.5 item 5
        self.assertLessEqual(fill["wall_ms_rel_p95"], 0.25)
        status_entry = data["commands"]["status"]["loads"]["serial-exclusive"]
        self.assertAlmostEqual(status_entry["median_rel"], 0.10)
        self.assertAlmostEqual(status_entry["p95_rel"], 0.25)
        # Load covariate is first-class (AUDIT-151 lesson).
        self.assertIn("parallel-observed",
                      data["commands"]["status"]["loads"])


class ReportSchemaTests(unittest.TestCase):
    def _fake_command_results(self):
        segments = pp.parse_importtime(IMPORTTIME_SAMPLE)
        return {
            "status": {
                "argv": [sys.executable, "-B", str(ENGINE), "status"],
                "samples_s": [1.20, 0.55, 0.56, 0.57, 0.58],
                "importtime_segments": segments,
                "sys_modules_probe": {"import_count": 196,
                                      "import_set_sha256": "a" * 64,
                                      "wall_ms": 1024.0},
            },
        }

    def test_build_and_validate_report_schema(self):
        report = pp.build_report(
            repeat=5, load_class="serial-exclusive", load_note="test",
            command_results=self._fake_command_results(),
            sample_order=["status"] * 5,
            tolerance_ref=str(TOLERANCE_FILE))
        errors = pp.validate_report(report)
        self.assertEqual(errors, [])
        cmd = report["commands"]["status"]
        self.assertEqual(cmd["cold_s"], 1.20)
        self.assertEqual(cmd["warm_s"], [0.55, 0.56, 0.57, 0.58])
        self.assertAlmostEqual(cmd["wall"]["warm_median"], 0.565)
        dec = cmd["decomposition"]
        self.assertAlmostEqual(
            dec["import_self_total_s"],
            (1710 + 151 + 6169 + 148) / 1_000_000.0)
        self.assertGreater(dec["non_import_residual_s"], 0.0)

    def test_validate_report_catches_missing_environment_keys(self):
        report = pp.build_report(
            repeat=5, load_class="serial-exclusive", load_note="t",
            command_results=self._fake_command_results(),
            sample_order=["status"] * 5)
        del report["environment"]["load_class"]
        self.assertTrue(pp.validate_report(report))

    def test_baseline_verdicts_via_judge(self):
        # Both sides report-commands-shaped (CLI data-flow contract).
        verdicts = pp.compare_against_baseline(
            {"status": {"wall": {"warm_median": 0.56, "warm_p95": 0.60}}},
            {"status": {"wall": {"warm_median": 0.50, "warm_p95": 0.60}}},
            {"status": {"median_rel": 0.10, "p95_rel": 0.25,
                        "abs_floor_s": 0.05}})
        self.assertEqual(verdicts["status"]["median"]["verdict"], "FAIL")
        self.assertEqual(verdicts["status"]["p95"]["verdict"], "PASS")


class SlowPathInjectionTests(unittest.TestCase):
    """Slow paths are injected (repo precedent: patch own functions)."""

    def test_sample_command_uses_injected_runner(self):
        calls = []

        def fake_run(argv, importtime=False):
            calls.append((tuple(argv), importtime))
            return {"wall_s": 0.5, "returncode": 0, "stdout_tail": ""}

        def fake_probe(argv_prefix):
            return pp.parse_importtime(IMPORTTIME_SAMPLE)

        def fake_modules(infra_dir):
            return {"import_count": 196,
                    "import_set_sha256": "b" * 64, "wall_ms": 900.0}

        with patch.object(pp, "run_command_once", side_effect=fake_run), \
                patch.object(pp, "probe_importtime", side_effect=fake_probe), \
                patch.object(pp, "probe_sys_modules",
                             side_effect=fake_modules):
            result = pp.sample_command("status", repeat=3)
        self.assertEqual(len(calls), 3)          # 3 pure wall samples…
        self.assertFalse(any(it for _, it in calls))  # …none with importtime
        self.assertEqual(result["samples_s"], [0.5, 0.5, 0.5])
        self.assertEqual(
            result["sys_modules_probe"]["import_count"], 196)
        self.assertEqual(result["importtime_segments"][0]["self_us"], 1710)


class CliPlanTests(unittest.TestCase):
    def test_sample_arg_dual_semantics(self):
        # Execution packet acceptance command: --sample status,summary
        cmds, repeat = pp.parse_sample_arg("status,summary")
        self.assertEqual(cmds, ["status", "summary"])
        self.assertIsNone(repeat)
        # Task brief caliber: --sample N (default 5)
        cmds2, repeat2 = pp.parse_sample_arg("5")
        self.assertIsNone(cmds2)
        self.assertEqual(repeat2, 5)
        with self.assertRaises(ValueError):
            pp.parse_sample_arg("status,bogus")  # unknown command key

    def test_resolve_plan_defaults(self):
        cmds, repeat = pp.resolve_plan(None, None)
        self.assertEqual(cmds, ["status", "summary"])
        self.assertEqual(repeat, 5)
        cmds3, repeat3 = pp.resolve_plan("5", None)
        self.assertEqual(cmds3, ["status", "summary"])
        self.assertEqual(repeat3, 5)
        with self.assertRaises(ValueError):
            pp.resolve_plan("2", None)  # §9.5: ≥5 interleaved rounds

    def test_registered_commands_reference_engine(self):
        self.assertTrue(ENGINE.exists())
        self.assertIn("status", pp.COMMANDS)
        self.assertIn("summary", pp.COMMANDS)
        self.assertTrue(any("check-governance" in a and "--summary-only" in a
                            for a in (pp.COMMANDS["summary"],)))


if __name__ == "__main__":
    unittest.main()
