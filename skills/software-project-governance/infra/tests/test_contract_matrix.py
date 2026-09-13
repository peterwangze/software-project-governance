"""FEAT-020 contract-matrix characterization tests (design §8.1/§10).

Protection-net semantics: the current implementation MUST match the frozen
snapshot (``contract_matrix/snapshots.json``) on all four faces — CLI
dispatch keys, Check ID segments, Result dict shapes, governance-write-guard
output pin. Any mismatch is a FAIL: a contract-surface change must be made
explicitly via ``generator.py --regen`` and explained in review (the zero-
regression proof baseline for AUDIT-150 REFACTOR-contract-matrix-freeze).

The snapshot extraction is fully programmatic (AST/regex over the engine
plus live runs); no engine inventory is hand-copied into this file. The
task-mandated freeze counts (80 CLI keys / 70 Check segments) are asserted
as freeze-point values — drift means a deliberate contract change.

Run:
    python -m unittest discover -s skills/software-project-governance/infra/tests -p "test_contract_matrix.py" -v
"""

import copy
import json
import re
import sys
import unittest
from functools import lru_cache
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

from contract_matrix import generator as cmg  # noqa: E402

# Freeze-point counts mandated by the FEAT-020 packet (实测值——冻结基线,
# not hand-copied inventories: the lists themselves come from extraction).
# FEAT-019 (2026-09-10) deliberately extended the CLI face with the
# archguard-ratchet fatal gate: 80→81 keys / 77→78 handlers, snapshot
# regenerated via generator.py --regen in the same change (the documented
# contract-change path; review covers both files).
# FEAT-013 (2026-09-10) extended the CLI face with the agent-locks-acquire
# dispatch-lock write API (RISK-046 root fix): 81→82 keys / 78→79 handlers,
# snapshot regenerated via generator.py --regen in the same change.
# The DSH preset schema-compat guard extended BOTH faces in the same change
# (the documented contract-change path): 82→83 keys / 79→80 handlers for the
# new `check-dsh-preset-compat` subcommand, and 70→71 check segments for the
# new Check 28v — a shipped preset composition row is now validated against
# the INSTALLED dsh's own Config schemas; snapshot regenerated via
# generator.py --regen in the same change (review covers both files).
# FIX-310: deliberate contract change — the retired `dsh.skills` guard
# (Check 40 + its CLI key) left the frozen faces; snapshot regenerated via
# `contract_matrix/generator.py --regen`.
# FEAT-031 (0.81.0 slice V8): 82→84 keys (`check-dsh-boundary` + `dsh-doctor`)
# and 70→71 check segments (Check 28w / `checks.dsh_boundary`); the snapshot was
# regenerated with `contract_matrix/generator.py --regen` in the same change —
# the documented contract-change path, review covering both files.
FROZEN_CLI_KEY_COUNT = 84
FROZEN_CHECK_SEGMENT_COUNT = 71


@lru_cache(maxsize=1)
def _current_faces():
    """One real extraction per test process (determinism proven separately)."""
    return cmg.extract_contract_faces()


@lru_cache(maxsize=1)
def _stored_snapshot():
    return cmg.load_snapshot()


class SnapshotFileTests(unittest.TestCase):
    """Snapshot artifact integrity: UTF-8 JSON, schema, metadata, ordering."""

    def setUp(self):
        self.raw_bytes = cmg.SNAPSHOT_PATH.read_bytes()
        # CRLF-tolerant: *.json is eol=lf-locked by .gitattributes, but the
        # ordering contract is about content — normalize any exotic checkout.
        self.text = self.raw_bytes.decode("utf-8").replace("\r\n", "\n")
        self.data = json.loads(self.text)

    def test_snapshot_schema_and_task(self):
        self.assertEqual(self.data["schema"], cmg.SNAPSHOT_SCHEMA)
        self.assertEqual(self.data["task"], "FEAT-020")

    def test_snapshot_uses_stable_canonical_ordering(self):
        """Regeneration is diff-friendly: file bytes == canonical dump."""
        canonical = json.dumps(
            self.data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        self.assertEqual(self.text, canonical,
                         "snapshots.json must be written with "
                         "sort_keys=True stable ordering")

    def test_generation_metadata_present(self):
        meta = self.data["generated"]
        self.assertIn("timestamp_utc", meta)
        self.assertRegex(
            meta["timestamp_utc"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        self.assertTrue(
            meta["git_head"] == "unknown"
            or re.fullmatch(r"[0-9a-f]{40}", meta["git_head"]),
            f"git_head must be a commit hex sha or 'unknown', "
            f"got {meta['git_head']!r}")
        self.assertRegex(meta["python"]["family"], r"^\d+\.\d+$")
        self.assertIn("platform", meta["python"])

    def test_faces_top_level_complete(self):
        faces = self.data["faces"]
        self.assertEqual(
            set(faces),
            {"cli_dispatch", "check_segments", "result_shapes",
             "guard_output_pin"})


class FreezePointTests(unittest.TestCase):
    """S6 freeze-point declaration + S4 dual-end interpreter pins."""

    def test_freeze_point_residual_waves_recorded(self):
        stored = _stored_snapshot()["freeze_point"]
        self.assertEqual(stored, cmg.FREEZE_POINT)
        self.assertEqual(stored["version_status"], "0.79.0 未 released")
        self.assertEqual(stored["residual_waves"]["0.79.0 收尾"],
                         ["FEAT-012", "FEAT-013", "FX-195"])
        self.assertEqual(stored["residual_waves"]["0.80.0 P0 余项"],
                         ["FEAT-018", "FEAT-019", "FIX-301", "AUDIT-152",
                          "DOC-003"])

    def test_dual_platform_python_family_pins_recorded(self):
        pins = _stored_snapshot()["python_family_pins"]
        families = {pin["family"] for pin in pins}
        self.assertEqual(families, {"3.14", "3.11"},
                         "S4 双端解释器族钉：Windows 本地 3.14 + ubuntu CI 3.11")

    def test_running_interpreter_family_is_pinned(self):
        """Generation and comparison must use the same interpreter family."""
        running = f"{sys.version_info.major}.{sys.version_info.minor}"
        pins = {pin["family"] for pin in
                _stored_snapshot()["python_family_pins"]}
        self.assertIn(
            running, pins,
            f"interpreter family {running} is not pinned "
            f"({sorted(pins)}). Per S4 the comparison must run in a pinned "
            f"family — regenerate the snapshot on this family and extend "
            f"the pin deliberately if this is a new supported platform.")


class CliDispatchFaceTests(unittest.TestCase):
    """Face 1 — engine dispatch keys vs frozen snapshot."""

    def test_keys_match_snapshot(self):
        current = cmg.extract_cli_dispatch()
        stored = _stored_snapshot()["faces"]["cli_dispatch"]
        self.assertEqual(current, stored,
                         "CLI dispatch contract drifted — regenerate "
                         "deliberately and explain the change")

    def test_freeze_point_counts(self):
        stored = _stored_snapshot()["faces"]["cli_dispatch"]
        self.assertEqual(stored["key_count"], FROZEN_CLI_KEY_COUNT)
        self.assertEqual(stored["key_count"], len(stored["keys"]))
        self.assertEqual(
            stored["key_count"] - len(stored["alias_groups"]),
            stored["handler_count"])

    def test_structural_sanity(self):
        stored = _stored_snapshot()["faces"]["cli_dispatch"]
        keys = stored["keys"]
        self.assertEqual(len(keys), len(set(keys)), "duplicate dispatch keys")
        self.assertEqual(keys, sorted(keys))
        for handler, group in stored["alias_groups"].items():
            self.assertGreaterEqual(
                len(group), 2,
                f"alias group {handler} must have ≥2 keys")
            for key in group:
                self.assertIn(key, keys)


class CheckSegmentsFaceTests(unittest.TestCase):
    """Face 2 — Check ID segment list vs frozen snapshot."""

    def test_segments_match_snapshot(self):
        current = cmg.extract_check_segments()
        stored = _stored_snapshot()["faces"]["check_segments"]
        self.assertEqual(current, stored,
                         "Check segment contract drifted — regenerate "
                         "deliberately and explain the change")

    def test_freeze_point_count(self):
        stored = _stored_snapshot()["faces"]["check_segments"]
        self.assertEqual(stored["count"], FROZEN_CHECK_SEGMENT_COUNT)
        self.assertEqual(stored["count"], len(stored["ids"]))
        self.assertEqual(stored["count"], len(stored["titles"]))
        self.assertEqual(len(stored["ids"]), len(set(stored["ids"])))

    def test_segments_canonically_sorted(self):
        ids = _stored_snapshot()["faces"]["check_segments"]["ids"]
        self.assertEqual(ids, sorted(ids, key=cmg._segment_sort_key))


class ResultShapesFaceTests(unittest.TestCase):
    """Face 3 — representative Result dict shapes vs frozen snapshot."""

    def test_shapes_match_snapshot(self):
        current = cmg.extract_result_shapes()
        stored = _stored_snapshot()["faces"]["result_shapes"]
        self.assertEqual(
            sorted(current), sorted(stored),
            "representative Result constructor set drifted")
        for name in current:
            self.assertEqual(
                current[name], stored[name],
                f"Result dict shape of {name} drifted — key surface or "
                f"type signature changed; regenerate deliberately")

    def test_covers_all_representative_constructors(self):
        stored = _stored_snapshot()["faces"]["result_shapes"]
        self.assertEqual(sorted(stored), sorted(cmg.REPRESENTATIVE_RESULT_CALLS))
        for name in cmg.REPRESENTATIVE_RESULT_CALLS:
            self.assertTrue(callable(getattr(cmg.vw, name, None)),
                            f"{name} must remain invocable on the engine")


class GuardOutputPinTests(unittest.TestCase):
    """Face 4 — governance-write-guard output contract (FEAT-017 R0 F-2 收编).

    The pin is derived from REAL subprocess runs against three deterministic
    temp-dir fixtures (empty host / malformed tracker / well-formed tracker)
    — zero real-environment contact, exit codes and lines are deterministic.
    """

    @lru_cache(maxsize=1)
    def _runs(self):
        pass_fixture, fail_fixture, wellformed = cmg._ensure_guard_fixtures()
        return {
            "pass": cmg.run_guard(pass_fixture),
            "fail": cmg.run_guard(fail_fixture),
            "wellformed": cmg.run_guard(wellformed),
        }

    def test_derived_pin_matches_snapshot(self):
        current = cmg.derive_guard_output_pin()
        stored = _stored_snapshot()["faces"]["guard_output_pin"]
        self.assertEqual(current, stored,
                         "guard output contract drifted — hook panels "
                         "consume this surface; regenerate deliberately")

    def test_pin_covers_result_line_format_and_issue_prefix(self):
        stored = _stored_snapshot()["faces"]["guard_output_pin"]
        self.assertEqual(stored["issue_line_prefix"], "    - ")
        self.assertTrue(stored["issue_line_regex"].startswith("^    - "))
        self.assertTrue(stored["expected_line_prefix"].startswith(
            "      期望列形: "))
        self.assertTrue(stored["result_pass_line"].startswith("Result: PASS"))
        self.assertTrue(stored["result_fail_prefix"].startswith(
            "Result: FAIL"))

    def test_fresh_outputs_conform_to_pinned_format(self):
        pin = _stored_snapshot()["faces"]["guard_output_pin"]
        face_re = re.compile(pin["face_line_regex"])
        fail_re = re.compile(pin["result_fail_regex"])
        runs = self._runs()
        for scenario in ("pass", "fail", "wellformed"):
            lines = [ln for ln in runs[scenario]["stdout"].splitlines()
                     if ln.strip()]
            self.assertIn(pin["header_line"], lines,
                          f"{scenario}: guard header line missing")
            face_lines = [ln for ln in lines if face_re.match(ln)]
            self.assertGreaterEqual(
                len(face_lines), 4,
                f"{scenario}: fewer than 4 face lines match pinned format")
            if scenario == "fail":
                issue_lines = [ln for ln in lines
                               if ln.startswith(pin["issue_line_prefix"])]
                expected_lines = [ln for ln in lines if ln.startswith(
                    pin["expected_line_prefix"])]
                self.assertGreaterEqual(len(issue_lines), 1)
                self.assertGreaterEqual(len(expected_lines), 1)
                for line in issue_lines:
                    self.assertRegex(line, pin["issue_line_regex"])
                self.assertTrue(
                    any(fail_re.match(ln) for ln in lines),
                    "FAIL Result line must match pinned format")
            else:
                self.assertIn(pin["result_pass_line"], lines,
                              f"{scenario}: PASS Result line drifted")

    def test_exit_codes_pinned(self):
        pin = _stored_snapshot()["faces"]["guard_output_pin"]
        runs = self._runs()
        self.assertEqual(runs["pass"]["exit_code"],
                         pin["exit_codes"]["pass_fixture"])
        self.assertEqual(runs["fail"]["exit_code"],
                         pin["exit_codes"]["fail_fixture"])
        self.assertEqual(runs["wellformed"]["exit_code"],
                         pin["exit_codes"]["wellformed_fixture"])


class DeterminismSelfCheckTests(unittest.TestCase):
    """Acceptance ② — two consecutive extractions produce zero difference."""

    def test_two_consecutive_extractions_are_identical(self):
        first = cmg.extract_contract_faces()
        second = cmg.extract_contract_faces()
        first_bytes = json.dumps(first, ensure_ascii=False, sort_keys=True)
        second_bytes = json.dumps(second, ensure_ascii=False, sort_keys=True)
        self.assertEqual(first, second)
        self.assertEqual(first_bytes, second_bytes)

    def test_full_harness_check_reports_zero_drift(self):
        """The --check differential harness is green against the snapshot."""
        drifts = cmg.check_against_snapshot()
        self.assertEqual(drifts, [])


class RedGreenProtectionTests(unittest.TestCase):
    """Hard-gate demo — snapshot perturbation MUST be detected as drift.

    The perturbations below operate on an in-memory deepcopy of the stored
    faces (the real snapshot file is never modified). Each case proves the
    FAIL direction of the protection net: if the engine (or snapshot) drifts
    in any face, ``diff_faces`` reports it and the characterization tests
    above turn red. Unperturbed faces report zero drift (green direction).
    """

    def _stored_faces(self):
        return copy.deepcopy(_stored_snapshot()["faces"])

    def test_perturbation_added_cli_key_is_detected(self):
        faces = self._stored_faces()
        faces["cli_dispatch"]["keys"] = sorted(
            faces["cli_dispatch"]["keys"] + ["check-imaginary-face"])
        faces["cli_dispatch"]["key_count"] += 1
        drifts = cmg.diff_faces(_current_faces(), faces)
        self.assertTrue(any("check-imaginary-face" in d for d in drifts),
                        f"added-key drift not reported: {drifts}")

    def test_perturbation_removed_check_segment_is_detected(self):
        faces = self._stored_faces()
        removed = faces["check_segments"]["ids"].pop()
        faces["check_segments"]["count"] -= 1
        drifts = cmg.diff_faces(_current_faces(), faces)
        self.assertTrue(any(removed in d for d in drifts),
                        f"removed-segment drift not reported: {drifts}")

    def test_perturbation_mutated_result_shape_is_detected(self):
        faces = self._stored_faces()
        faces["result_shapes"]["check_risk_staleness"]["$dict"][
            "total_open"] = "float"
        drifts = cmg.diff_faces(_current_faces(), faces)
        self.assertTrue(
            any("result_shapes.check_risk_staleness" in d for d in drifts),
            f"shape drift not reported: {drifts}")

    def test_perturbed_guard_result_line_is_detected(self):
        faces = self._stored_faces()
        faces["guard_output_pin"]["result_pass_line"] += "X"
        drifts = cmg.diff_faces(_current_faces(), faces)
        self.assertTrue(
            any("guard_output_pin.result_pass_line" in d for d in drifts),
            f"guard pin drift not reported: {drifts}")

    def test_unperturbed_faces_report_zero_drift(self):
        drifts = cmg.diff_faces(_current_faces(), self._stored_faces())
        self.assertEqual(drifts, [])


class GoldenSamplesSidecarTests(unittest.TestCase):
    """Acceptance ③ — human-review sidecar exists with ≥5 real samples."""

    def test_sidecar_exists_utf8_with_five_samples(self):
        # *.txt has no eol policy (.gitattributes locks only *.py/*.json) —
        # a Windows checkout may hand this file CRLF endings; normalize.
        text = cmg.GOLDEN_PATH.read_bytes().decode("utf-8").replace(
            "\r\n", "\n")
        sections = re.findall(r"^### .+$", text, re.MULTILINE)
        self.assertGreaterEqual(len(sections), 5)
        self.assertEqual(len(re.findall(r"^exit_code: \d+$", text,
                                        re.MULTILINE)), len(sections))


if __name__ == "__main__":
    unittest.main()
