"""``dsh_doctor`` — the staged diagnostic entry (S0–S7, exit codes, four switches).

FEAT-031 / 0.81.0 slice **V8**; design §5.1 (the entry spec), §5.2 (the stage
table), §5.5 (the upgrade rehearsal) and §7.4 (the machine-checked acceptance).

**What this suite is for.** The doctor's value is not that it prints stages, it
is that it stays *honest under damage*: a crashed stage must degrade to
``NOT_RUN`` without taking the report down, an offline run must not smuggle in a
host probe, and a rehearsal must not be able to green-light a no-op replay.
Each of those is a claim about behavior under a specific fault, so each is
tested by inducing that fault.

**Red lines honored here.** No test writes inside the repository.
``--record-evidence`` is exercised through a captured environment with both
``DSH_HOME`` and ``USERPROFILE`` redirected to a temporary directory, and every
rehearsal candidate is a temporary file mutated out of the recorded baseline
(the design's §5.5 [C] "synthetic mutation" path) — which is also why the
rehearsal reports must carry ``synthetic`` labelling.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock
from datetime import datetime, timezone
from pathlib import Path

_INFRA_DIR = Path(__file__).resolve().parent.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import dsh_doctor as doctor  # noqa: E402

_PACKAGE_ROOT = _INFRA_DIR.parents[2]
_BASELINE = _PACKAGE_ROOT / "adapters" / "dsh" / "fixtures" / "host-facts-0.1.5-rc.1.json"
_STAGE_IDS = [ident for ident, _ in doctor.STAGES]


def _repo_hashes() -> dict:
    """sha256 of every tracked-ish artifact under the package (isolation proof)."""
    import hashlib

    hashes = {}
    for root in ("adapters", "lib", "agent-presets", "skills/software-project-governance/infra"):
        for path in sorted((_PACKAGE_ROOT / root).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            hashes[path.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


class DoctorCase(unittest.TestCase):
    """Base: a report runner sealed against the runner's own environment.

    Every run gets a **rendered preset inside its own temporary home** unless the
    caller passes an explicit ``env``. That is what makes the suite reproducible:
    S1 judges whether a preset is installed, so a test that inherited the
    runner's real ``DSH_HOME`` would pass on a machine with a preset and fail on
    a clean one — a test defect, not a product one (FIX-316 F-8 class). The
    temporary home is only ever written by this suite, under ``%TEMP%``.
    """

    maxDiff = None

    def rendered_home(self):
        """A temporary dsh home carrying a preset this package's version claims."""
        cached = getattr(self, "_rendered_home", None)
        if cached is not None:
            return cached
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        home = Path(temp.name) / ".dsh"
        preset = home / ".agent-presets" / "governance"
        preset.mkdir(parents=True)
        version = doctor._package_version(_PACKAGE_ROOT)
        (preset / ".dsh-bundle-version").write_text(version, encoding="utf-8")
        (preset / "skill-root.txt").write_text(
            str(_PACKAGE_ROOT / "skills" / "software-project-governance"),
            encoding="utf-8")
        self._rendered_home = home
        return home

    def clean_home(self):
        """A temporary dsh home with *no* preset — the unrendered case."""
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        home = Path(temp.name) / ".dsh"
        home.mkdir(parents=True)
        return home

    def run_doctor(self, **kwargs):
        kwargs.setdefault("root", _PACKAGE_ROOT)
        kwargs.setdefault("offline", True)
        if "env" not in kwargs:
            kwargs["env"] = {"DSH_HOME": str(self.rendered_home())}
        return doctor.run_doctor(**kwargs)

    def stages_of(self, report):
        return {record["stage"]: record for record in report["stages"]}


# ══════════════════════════════════════════════════════════════════════════
# S0–S7 — every stage produces a record with the fixed field set
# ══════════════════════════════════════════════════════════════════════════


class StageRecordTests(DoctorCase):

    def test_every_stage_produces_a_record_with_the_fixed_field_set(self):
        report = self.run_doctor()
        self.assertEqual([record["stage"] for record in report["stages"]],
                         _STAGE_IDS)
        for record in report["stages"]:
            self.assertIn(record["verdict"], ("PASS", "FAIL", "NOT_RUN"))
            self.assertTrue(record["reason"], record["stage"])
            self.assertIsInstance(record["credible_face"], dict)
            self.assertIsInstance(record["evidence"], list)
            self.assertIsInstance(record["remediation"], list)
            for item in record["evidence"]:
                self.assertIn("kind", item)
                self.assertIn("ref", item)

    def test_the_report_carries_the_documented_top_level_shape(self):
        report = self.run_doctor()
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["command"], "dsh-doctor")
        self.assertIn(report["verdict"], ("PASS", "FAIL", "NOT_RUN"))
        self.assertIn("host", report)
        self.assertIn("generated_at", report)
        datetime.fromisoformat(report["generated_at"])

    def test_stage_selection_runs_only_the_named_stages(self):
        report = self.run_doctor(stages=["S4"])
        self.assertEqual([record["stage"] for record in report["stages"]], ["S4"])

    def test_an_unknown_stage_is_refused(self):
        with self.assertRaises(doctor.Refused):
            self.run_doctor(stages=["S9"])

    def test_s0_records_the_invocation_facts_and_is_not_run_by_design(self):
        report = self.run_doctor(env={"DSH_HOME": str(Path(tempfile.gettempdir()) / "spg-x")})
        s0 = self.stages_of(report)["S0"]
        self.assertEqual(s0["verdict"], "NOT_RUN")
        self.assertIn("record-only", s0["reason"])
        self.assertEqual(s0["credible_face"]["dsh_home"],
                         str(Path(tempfile.gettempdir()) / "spg-x"))

    def test_s0_fails_when_the_home_cannot_be_resolved_at_all(self):
        report = self.run_doctor(env={})
        s0 = self.stages_of(report)["S0"]
        self.assertEqual(s0["verdict"], "FAIL")
        self.assertIn("could not be resolved", s0["reason"])

    def test_s0_treats_a_whitespace_home_as_unset_per_the_contract(self):
        # G-06 / `host.env.write_side.blank_policy`: a whitespace value is
        # unset, never a literal-space path.
        home = str(Path(tempfile.gettempdir()) / "spg-fallback-home")
        report = self.run_doctor(env={"DSH_HOME": "   ", "HOME": home})
        s0 = self.stages_of(report)["S0"]
        self.assertEqual(s0["credible_face"]["dsh_home"], str(Path(home) / ".dsh"))
        self.assertTrue(any("whitespace" in note
                            for note in s0["credible_face"]["dsh_home_notes"]))

    def test_s5_is_not_run_and_names_the_authorisation_requirement(self):
        report = self.run_doctor()
        s5 = self.stages_of(report)["S5"]
        self.assertEqual(s5["verdict"], "NOT_RUN")
        self.assertIn("--allow-host-probe", s5["reason"])
        self.assertEqual(s5["credible_face"]["authorized"], False)
        self.assertTrue(s5["remediation"])

    def test_s5_stays_not_run_even_when_authorised_offline(self):
        report = self.run_doctor(allow_host_probe=True, offline=True)
        s5 = self.stages_of(report)["S5"]
        self.assertEqual(s5["verdict"], "NOT_RUN")
        self.assertIn("offline", s5["reason"])


# ══════════════════════════════════════════════════════════════════════════
# crash isolation (BT-2) and --selftest
# ══════════════════════════════════════════════════════════════════════════


class CrashIsolationTests(DoctorCase):

    def test_a_crashed_stage_degrades_to_not_run_and_the_rest_survive(self):
        report = self.run_doctor(inject={"S4": RuntimeError("boom")})
        records = self.stages_of(report)
        self.assertEqual(len(report["stages"]), len(_STAGE_IDS))
        crashed = records["S4"]
        self.assertEqual(crashed["verdict"], "NOT_RUN")
        self.assertIs(crashed["stage_error"], True)
        self.assertIn("stage crashed: RuntimeError: boom", crashed["reason"])
        self.assertNotIn("stage_error", records["S0"])

    def test_a_crash_does_not_make_the_top_level_verdict_green_by_itself(self):
        # A report in which *only* the crashed stage would have "passed" is the
        # failure mode: `stage_error` must keep the crash out of PASS.
        report = self.run_doctor(inject={ident: RuntimeError("boom")
                                         for ident in _STAGE_IDS})
        self.assertEqual(report["verdict"], "NOT_RUN")
        self.assertEqual(report["exit_code"], doctor.EXIT_OK)

    def test_selftest_exercises_every_stage_and_reports_ok(self):
        report = doctor.run_self_test(_PACKAGE_ROOT)
        self.assertTrue(report["ok"], report)
        self.assertEqual([case["stage"] for case in report["cases"]], _STAGE_IDS)
        for case in report["cases"]:
            self.assertTrue(case["ok"], case)
            self.assertEqual(case["stage_count"], len(_STAGE_IDS))
            self.assertEqual(case["crashed_verdict"], "NOT_RUN")
            self.assertIs(case["crashed_stage_error"], True)

    def test_selftest_cli_exits_zero_and_can_emit_json(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = doctor.main(["--selftest", "--json"])
        self.assertEqual(code, doctor.EXIT_OK)
        payload = json.loads(stream.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["verdict"], "PASS")


# ══════════════════════════════════════════════════════════════════════════
# exit codes
# ══════════════════════════════════════════════════════════════════════════


class ExitCodeTests(DoctorCase):

    def test_a_clean_offline_run_exits_zero(self):
        report = self.run_doctor(offline=True)
        self.assertEqual(report["exit_code"], doctor.EXIT_OK)
        self.assertNotEqual(report["verdict"], "FAIL")

    def test_a_clean_unrendered_home_fails_on_s1_and_exits_one(self):
        """The other half of the exit-code semantics, pinned without ambient state.

        S1 is a real judgment about the delivery plane: with no preset in the
        home it must FAIL, and the run must exit 1. Asserting *this* alongside
        the clean-home case is what keeps "exit 0" from being read as "offline
        always exits 0".
        """
        home = self.clean_home()
        report = self.run_doctor(offline=True, env={"DSH_HOME": str(home)})
        s1 = self.stages_of(report)["S1"]
        self.assertEqual(s1["verdict"], "FAIL")
        self.assertIn("does not exist", s1["reason"])
        self.assertEqual(report["verdict"], "FAIL")
        self.assertEqual(report["exit_code"], doctor.EXIT_FAIL)

    def test_one_failing_stage_maps_to_exit_one(self):
        report = self.run_doctor(offline=True, inject={"S1": RuntimeError("x")})
        self.assertNotEqual(report["exit_code"], doctor.EXIT_FAIL)  # NOT_RUN
        report = self._with_failing_stage()
        self.assertEqual(report["exit_code"], doctor.EXIT_FAIL)

    def _with_failing_stage(self):
        """A run with a genuinely FAILing stage, built without the real plane."""
        module = doctor.stage_s1_delivery

        def failing(ctx):
            outcome = module(ctx)
            outcome.verdict = "FAIL"
            outcome.reason = "injected failure"
            return outcome

        original = doctor._stage_runners
        try:
            doctor._stage_runners = lambda compat=None, smoke=None: {
                **original(compat, smoke), "S1": failing}
            return self.run_doctor(offline=True)
        finally:
            doctor._stage_runners = original

    def test_a_usage_error_is_refused_with_exit_two(self):
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream):
            code = doctor.main(["--rehearse", "x.json"])
        self.assertEqual(code, doctor.EXIT_REFUSED)
        self.assertIn("--against", stream.getvalue())

    def test_an_unreadable_rehearsal_fixture_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "absent.json"
            with self.assertRaises(doctor.Refused):
                doctor.rehearse(missing, _BASELINE)

    def test_a_non_object_fixture_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text("[1, 2, 3]", encoding="utf-8")
            with self.assertRaises(doctor.Refused):
                doctor.rehearse(bad, _BASELINE)


# ══════════════════════════════════════════════════════════════════════════
# --offline applicable domain (R1 N-3)
# ══════════════════════════════════════════════════════════════════════════


class OfflineDomainTests(DoctorCase):

    def test_offline_marks_the_subprocess_stages_not_run_with_their_reason(self):
        report = self.run_doctor(offline=True)
        records = self.stages_of(report)
        for ident in ("S2", "S4", "S6"):
            self.assertEqual(records[ident]["verdict"], "NOT_RUN", ident)
            self.assertIn("offline", records[ident]["reason"].lower(), ident)

    def test_offline_still_runs_the_file_level_stages(self):
        report = self.run_doctor(offline=True)
        records = self.stages_of(report)
        # S1 reads the preset plane, S3 the evidence + plane layout, S7 the
        # hooks: none of them needs a child process, so none may be skipped.
        for ident in ("S0", "S1", "S3", "S5", "S7"):
            self.assertIn(records[ident]["verdict"], ("PASS", "FAIL", "NOT_RUN"),
                          ident)
            self.assertNotIn("stage_error", records[ident], ident)

    def test_offline_never_compares_the_verdicts_and_says_why(self):
        report = self.run_doctor(offline=True)
        boundary = report["boundary"]
        self.assertFalse(boundary["compared"])
        self.assertIsNone(boundary["agrees"])
        self.assertIn("--offline", boundary["note"])
        self.assertIn("N-3", boundary["note"])

    def test_a_partial_run_does_not_compare_either(self):
        report = self.run_doctor(stages=["S4"])
        self.assertFalse(report["boundary"]["compared"])
        self.assertIn("partial run", report["boundary"]["note"])

    def test_offline_does_not_spawn_anything(self):
        # The strongest available offline proof: every stage that would need a
        # child process reports NOT_RUN, and the report carries no probe result.
        report = self.run_doctor(offline=True)
        for record in report["stages"]:
            if record["stage"] in ("S2", "S4", "S6"):
                self.assertEqual(record["verdict"], "NOT_RUN")
                self.assertEqual(record["credible_face"].get("js_render_sha256"),
                                 None if record["stage"] != "S4" else None)


# ══════════════════════════════════════════════════════════════════════════
# S2 — the projection (F-R1-06 / R0 BT-R-02)
# ══════════════════════════════════════════════════════════════════════════


class S2ProjectionTests(DoctorCase):

    COVERAGE = {
        "rows_enabled": 23,
        "rows_verified": 18,
        "rows_unverified": 5,
        "unreadable_compositions": 2,
        "unverified_reasons": {"NO_SCHEMA": 5},
    }

    def test_the_projection_carries_unreadable_compositions(self):
        projected = doctor._projected_coverage({"coverage": self.COVERAGE})
        self.assertEqual(projected["unreadable_compositions"], 2)
        self.assertEqual(sorted(projected), sorted(self.COVERAGE))

    def test_the_projection_is_a_copy_not_a_recomputation(self):
        source = {"coverage": dict(self.COVERAGE)}
        projected = doctor._projected_coverage(source)
        projected["rows_enabled"] = 999
        self.assertEqual(source["coverage"]["rows_enabled"], 23)

    def test_s2_reports_the_projected_coverage_in_its_credible_face(self):
        runner = lambda: {"verdict": "PASS", "reason": "ok", "issues": [],
                          "coverage": dict(self.COVERAGE)}
        report = self.run_doctor(offline=False, compat_runner=runner)
        s2 = self.stages_of(report)["S2"]
        self.assertEqual(s2["verdict"], "PASS")
        self.assertEqual(s2["credible_face"]["unreadable_compositions"], 2)
        self.assertIn("18 of 23", s2["reason"])
        self.assertIn("unreadable", s2["reason"])

    def test_s2_discloses_unverified_rows_without_turning_them_into_a_pass(self):
        runner = lambda: {"verdict": "PASS", "reason": "ok", "issues": [],
                          "coverage": dict(self.COVERAGE)}
        report = self.run_doctor(offline=False, compat_runner=runner)
        s2 = self.stages_of(report)["S2"]
        self.assertIn("NOT verified", s2["reason"])
        self.assertIn("NO_SCHEMA=5", s2["reason"])

    def test_s2_cites_the_check_it_projects(self):
        runner = lambda: {"verdict": "NOT_RUN", "reason": "no node",
                          "issues": [], "coverage": dict(self.COVERAGE)}
        report = self.run_doctor(offline=False, compat_runner=runner)
        s2 = self.stages_of(report)["S2"]
        self.assertEqual(s2["verdict"], "NOT_RUN")
        self.assertEqual(s2["evidence"][0]["kind"], "check")
        self.assertEqual(s2["evidence"][0]["ref"], "28v")

    def test_a_failing_compat_report_fails_the_stage(self):
        runner = lambda: {"verdict": "FAIL", "reason": "row rejected",
                          "issues": ["row persona: prefix required"],
                          "coverage": dict(self.COVERAGE)}
        report = self.run_doctor(offline=False, compat_runner=runner)
        s2 = self.stages_of(report)["S2"]
        self.assertEqual(s2["verdict"], "FAIL")
        self.assertEqual(s2["findings"], ["row persona: prefix required"])


# ══════════════════════════════════════════════════════════════════════════
# S3/S7 — consuming K-7 instead of recomputing it (R0 BT-R-02)
# ══════════════════════════════════════════════════════════════════════════


class SingleVerdictTests(DoctorCase):

    def test_s3_cites_k7_and_does_not_restate_the_evidence(self):
        report = self.run_doctor()
        s3 = self.stages_of(report)["S3"]
        refs = [item["ref"] for item in s3["evidence"]]
        self.assertIn("28w/K-7", refs)

    def test_s7_cites_k5_for_the_hook_path_expression(self):
        report = self.run_doctor()
        s7 = self.stages_of(report)["S7"]
        self.assertIn("28w/K-5", [item["ref"] for item in s7["evidence"]])

    def test_k12_compares_the_two_verdicts_when_every_stage_ran(self):
        report = self.run_doctor(offline=False, compat_runner=None,
                                 smoke_runner=lambda root: {
                                     "verdict": "NOT_RUN", "reason": "no node",
                                     "exit_code": None, "details": [],
                                     "isolation": {"real_home_writes": None}})
        boundary = report["boundary"]
        self.assertTrue(boundary["compared"])
        self.assertIsNotNone(boundary["agrees"])
        doctor_failed = report["verdict"] == "FAIL"
        boundary_failed = boundary["verdict"] == "FAIL"
        self.assertEqual(boundary["agrees"], doctor_failed == boundary_failed)

    def test_k12_disagreement_is_appended_as_a_fail_stage(self):
        module = doctor.stage_s1_delivery

        def failing(ctx):
            outcome = module(ctx)
            outcome.verdict = "FAIL"
            outcome.reason = "injected"
            return outcome

        original_runners = doctor._stage_runners
        original_boundary = doctor._load_boundary_module

        class FakeBoundary:
            CRITERIA = ()

            @staticmethod
            def check_dsh_boundary(root):
                return {"check": "28w", "verdict": "PASS", "criteria": [],
                        "issues": []}

            @staticmethod
            def failed(report):
                return []

            @staticmethod
            def rehearsal_findings(*args, **kwargs):
                return []

        try:
            doctor._stage_runners = lambda compat=None, smoke=None: {
                **original_runners(compat, smoke), "S1": failing}
            doctor._load_boundary_module = lambda: FakeBoundary
            report = self.run_doctor(offline=False)
        finally:
            doctor._stage_runners = original_runners
            doctor._load_boundary_module = original_boundary
        # The doctor failed while the (stubbed) boundary passed: FX-VERDICT-01.
        k12 = [record for record in report["stages"] if record["stage"] == "K-12"]
        self.assertEqual(len(k12), 1, report["stages"])
        self.assertEqual(k12[0]["verdict"], "FAIL")
        self.assertIn("verdict disagreement", k12[0]["reason"])
        self.assertEqual(report["verdict"], "FAIL")


# ══════════════════════════════════════════════════════════════════════════
# S6 — the isolated smoke projector + the environment-gated disclosure
# ══════════════════════════════════════════════════════════════════════════


class SmokeStageTests(DoctorCase):

    def test_s6_projects_the_smoke_result_and_qualifies_the_pass(self):
        report = self.run_doctor(
            offline=False,
            smoke_runner=lambda root: {
                "verdict": "PASS",
                "reason": "isolated preset-session smoke PASSED",
                "exit_code": 0, "details": [],
                "isolation": {"real_home_writes": 0}})
        s6 = self.stages_of(report)["S6"]
        self.assertEqual(s6["verdict"], "PASS")
        self.assertEqual(s6["credible_face"]["real_home_writes"], 0)
        self.assertIn("resolution-level only", s6["reason"])
        self.assertIn("NOT verified", s6["reason"])

    def test_s6_fails_when_the_smoke_fails(self):
        report = self.run_doctor(
            offline=False,
            smoke_runner=lambda root: {
                "verdict": "FAIL", "reason": "smoke exit 1: [FAIL] catalog",
                "exit_code": 1, "details": ["[FAIL] catalog missing"],
                "isolation": {"real_home_writes": 0}})
        s6 = self.stages_of(report)["S6"]
        self.assertEqual(s6["verdict"], "FAIL")
        self.assertIn("catalog missing", "\n".join(s6["findings"]))

    def test_s6_reports_a_raising_runner_as_a_fail_not_a_crash(self):
        def boom(root):
            raise RuntimeError("runner exploded")

        report = self.run_doctor(offline=False, smoke_runner=boom)
        s6 = self.stages_of(report)["S6"]
        self.assertEqual(s6["verdict"], "FAIL")
        self.assertNotIn("stage_error", s6)

    def test_the_environment_gated_faces_come_from_the_contract(self):
        report = self.run_doctor(offline=True)
        s6 = self.stages_of(report)["S6"]
        self.assertIn("unverified_due_to_env", s6["credible_face"])

    def test_run_isolated_smoke_dispatches_to_the_engine_implementation(self):
        seen = {}
        import verify_workflow

        original = verify_workflow.check_dsh_preset_smoke

        def fake(root=None, timeout=120):
            seen["called"] = True
            return {"verdict": "NOT_RUN", "reason": "stub", "exit_code": None,
                    "details": [], "isolation": {"real_home_writes": None}}

        verify_workflow.check_dsh_preset_smoke = fake
        try:
            result = doctor.run_isolated_smoke(_PACKAGE_ROOT)
        finally:
            verify_workflow.check_dsh_preset_smoke = original
        self.assertTrue(seen.get("called"))
        self.assertEqual(result["verdict"], "NOT_RUN")


# ══════════════════════════════════════════════════════════════════════════
# S1 — the preset delivery plane
# ══════════════════════════════════════════════════════════════════════════


class DeliveryStageTests(DoctorCase):

    def _home(self, version="9.9.9", marker=True, skill_root=True):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        home = Path(temp.name) / ".dsh"
        preset = home / ".agent-presets" / "governance"
        preset.mkdir(parents=True)
        if marker:
            (preset / ".dsh-bundle-version").write_text(version, encoding="utf-8")
        if skill_root:
            (preset / "skill-root.txt").write_text("x", encoding="utf-8")
        return home

    def test_a_missing_preset_directory_is_a_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self.run_doctor(env={"DSH_HOME": tmp})
        s1 = self.stages_of(report)["S1"]
        self.assertEqual(s1["verdict"], "FAIL")
        self.assertIn("does not exist", s1["reason"])

    def test_a_missing_version_marker_is_a_fail(self):
        home = self._home(marker=False)
        report = self.run_doctor(env={"DSH_HOME": str(home)})
        s1 = self.stages_of(report)["S1"]
        self.assertEqual(s1["verdict"], "FAIL")
        self.assertIn("version marker", s1["reason"])

    def test_a_stale_marker_version_is_a_fail(self):
        home = self._home(version="0.0.1")
        report = self.run_doctor(env={"DSH_HOME": str(home)})
        s1 = self.stages_of(report)["S1"]
        self.assertEqual(s1["verdict"], "FAIL")
        self.assertIn("stale", s1["reason"])

    def test_a_missing_skill_root_marker_is_a_fail(self):
        home = self._home(version=doctor._package_version(_PACKAGE_ROOT),
                          skill_root=False)
        report = self.run_doctor(env={"DSH_HOME": str(home)})
        s1 = self.stages_of(report)["S1"]
        self.assertEqual(s1["verdict"], "FAIL")
        self.assertIn("skill-root marker", s1["reason"])

    def test_a_complete_preset_passes_with_the_resolution_only_qualifier(self):
        home = self._home(version=doctor._package_version(_PACKAGE_ROOT))
        report = self.run_doctor(env={"DSH_HOME": str(home)})
        s1 = self.stages_of(report)["S1"]
        self.assertEqual(s1["verdict"], "PASS")
        self.assertIn("resolution-level only", s1["reason"])


# ══════════════════════════════════════════════════════════════════════════
# S4 — render parity and its disclosure
# ══════════════════════════════════════════════════════════════════════════


class RenderStageTests(DoctorCase):

    def test_offline_reports_the_python_half_and_does_not_claim_parity(self):
        report = self.run_doctor(offline=True)
        s4 = self.stages_of(report)["S4"]
        self.assertEqual(s4["verdict"], "NOT_RUN")
        self.assertIn("parity is NOT verified", s4["reason"])
        self.assertIsNone(s4["credible_face"]["js_render_sha256"])

    def test_the_python_render_is_the_launchers_own_output(self):
        """The doctor's render *is* the launcher's own output — derived, not pinned.

        **Why this stopped being a literal hash** (FIX-334 / REVIEW-REL-077-RELEASE-R0
        F-01): the case used to assert one sha256 measured on 0.80.0
        (``00e0d330…3723``). That literal goes stale on **two** axes, and both are
        properties of the *tree*, not of the renderer: the persona version line is
        projected into ``agent-presets/governance/agent.cordis.yml.template`` at
        every version bump, and the render substitutes the **absolute** package
        root into ``__GOVERNANCE_REPO_ROOT__`` — so the literal also pinned the
        checkout path. A stale literal is a red test on a healthy tree, which is
        the "version-pin rot" defect class this release exists to remove; the pin
        was previously read as evidence about the *pristine* tree when in fact it
        could only ever be satisfied there.

        The claim is kept, in a form that cannot rot:

        * **parity** — a second, independent delivery path (a fresh interpreter
          importing the same ``launch.py``) must produce byte-identical text, so
          the doctor is still proven to *delegate* to the launcher's renderer
          rather than reimplement it (which is what the case name claims);
        * **derivation** — the rendered persona version line must carry the
          authoritative version, read from the ``SKILL.md`` frontmatter (the
          version's single source of truth), so a projection that lags the
          release is caught here instead of being masked by a literal somebody
          remembered to update;
        * **not a refused render** — ``render_composition()`` returns ``""`` when
          the template is missing, undecodable or leaves a ``__…__`` token
          behind, so an empty render must fail rather than compare equal to
          another empty render.
        """
        import hashlib
        import subprocess

        from checks.version import extract_skill_version

        launcher = _PACKAGE_ROOT / "adapters" / "dsh" / "launch.py"
        rendered = doctor._python_render(_PACKAGE_ROOT)
        self.assertTrue(rendered, "the launcher refused to render the template")

        # Parity: same tree, same run, a second path to the same renderer. The
        # child only imports and renders (no install, no write), and it is given
        # an isolated home anyway so no real ``$DSH_HOME`` is ever in scope.
        script = (
            "import hashlib, importlib.util, sys;"
            "spec = importlib.util.spec_from_file_location('_parity', sys.argv[1]);"
            "module = importlib.util.module_from_spec(spec);"
            "spec.loader.exec_module(module);"
            "sys.stdout.write(hashlib.sha256("
            "module.render_composition().encode('utf-8')).hexdigest())"
        )
        proc = subprocess.run(
            [sys.executable, "-c", script, str(launcher)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=120, cwd=str(_PACKAGE_ROOT),
            env={**os.environ, "DSH_HOME": str(self.clean_home())},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
            proc.stdout.strip(),
            "the doctor's render diverged from the launcher's own output")

        # Derivation: the render tracks the authoritative version rather than a
        # literal (FIX-253 precedent in `test_dsh_adapter`).
        version = extract_skill_version(
            _PACKAGE_ROOT / "skills" / "software-project-governance" / "SKILL.md")
        self.assertTrue(version, "SKILL.md frontmatter version is missing")
        self.assertIn(
            f"（v{version}）", rendered,
            "the rendered persona version line does not carry the authoritative version")

    def test_a_missing_template_is_a_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self.run_doctor(
                offline=True,
                root=_PACKAGE_ROOT,
                )
            _ = report  # the real template exists; the mutation is covered below
        with tempfile.TemporaryDirectory() as tmp:
            module = doctor.stage_s4_render
            original_read = doctor._read

            def read(path):
                return "" if str(path).endswith(".template") else original_read(path)

            doctor._read = read
            try:
                report = self.run_doctor(offline=True)
            finally:
                doctor._read = original_read
        s4 = self.stages_of(report)["S4"]
        self.assertEqual(s4["verdict"], "FAIL")
        self.assertIn("template missing", s4["reason"])


# ══════════════════════════════════════════════════════════════════════════
# --rehearse: K-13 preconditions, drift detection, synthetic labelling
# ══════════════════════════════════════════════════════════════════════════


class RehearsalTests(DoctorCase):

    def setUp(self):
        self.baseline = json.loads(_BASELINE.read_text(encoding="utf-8"))
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

    def candidate(self, mutate, name="candidate.json"):
        document = json.loads(json.dumps(self.baseline))
        document["captured_at"] = "2026-12-01T00:00:00+00:00"
        document["dsh_version"] = "0.2.0"
        document["synthetic"] = True
        mutate(document)
        path = Path(self.tempdir.name) / name
        path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        return path

    def test_a_same_version_pair_fails_as_a_no_op(self):
        # FX-REHEARSE-05: a no-op replay must never green-light an upgrade.
        path = self.candidate(lambda document: document.update(
            {"dsh_version": self.baseline["dsh_version"]}))
        report = doctor.rehearse(path, _BASELINE)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertTrue(any("rehearsal no-op" in item
                            for item in report["findings"]), report["findings"])

    def test_a_time_reversed_pair_fails(self):
        # FX-BASE-01: the candidate cannot predate its own baseline.
        path = self.candidate(lambda document: document.update(
            {"captured_at": "2000-01-01T00:00:00+00:00"}))
        report = doctor.rehearse(path, _BASELINE)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertTrue(any("time order" in item
                            for item in report["findings"]), report["findings"])

    def test_a_stale_baseline_is_evidence_stale_and_fails(self):
        # R1 N-6(c): a fixture past its TTL is a FAIL, not an advisory.
        with tempfile.TemporaryDirectory() as tmp:
            stale = Path(tmp) / "stale.json"
            document = json.loads(json.dumps(self.baseline))
            document["captured_at"] = "2000-01-01T00:00:00+00:00"
            document["dsh_version"] = "0.1.0"
            document["synthetic"] = False
            stale.write_text(json.dumps(document), encoding="utf-8")
            path = self.candidate(lambda document: None)
            report = doctor.rehearse(path, stale)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertTrue(any("[EVIDENCE-STALE]" in item
                            for item in report["findings"]), report["findings"])

    def test_removing_a_package_is_contract_drift(self):
        # FX-REHEARSE-01
        name = sorted(self.baseline["oracle_packages"])[0]
        path = self.candidate(
            lambda document: document["oracle_packages"].pop(name))
        report = doctor.rehearse(path, _BASELINE)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertTrue(any(item["kind"] == "contract"
                            and name in item["subject"] for item in report["drift"]))

    def test_removing_an_api_symbol_is_contract_drift(self):
        # FX-REHEARSE-02
        path = self.candidate(
            lambda document: document.update(
                {"api_symbols": document["api_symbols"][1:]}))
        report = doctor.rehearse(path, _BASELINE)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertTrue(any(item["kind"] == "contract"
                            and "api_symbol" in item["subject"]
                            for item in report["drift"]))

    def test_adding_a_required_key_is_behaviour_drift(self):
        # FX-REHEARSE-03
        def mutate(document):
            for row in document["rows"]:
                if row["row_id"] == "persona":
                    row["required_keys"] = ["prefix", "brandNewKey"]
        path = self.candidate(mutate)
        report = doctor.rehearse(path, _BASELINE)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertTrue(any("brandNewKey" in item["detail"]
                            for item in report["drift"]), report["drift"])

    def test_flipping_a_row_to_reject_is_behaviour_drift(self):
        # FX-REHEARSE-04
        def mutate(document):
            for row in document["rows"]:
                if row["row_id"] == "persona":
                    row["probe_result"] = "reject"
        path = self.candidate(mutate)
        report = doctor.rehearse(path, _BASELINE)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertTrue(any("REJECTED" in item["detail"]
                            for item in report["drift"]), report["drift"])

    def test_a_clean_pair_with_only_a_version_move_passes(self):
        path = self.candidate(lambda document: None)
        report = doctor.rehearse(path, _BASELINE)
        self.assertEqual(report["verdict"], "PASS", report["findings"])
        self.assertEqual(report["drift"], [])

    def test_synthetic_drift_is_labelled_and_cannot_claim_safety(self):
        path = self.candidate(
            lambda document: document["oracle_packages"].pop(
                sorted(document["oracle_packages"])[0]))
        report = doctor.rehearse(path, _BASELINE)
        self.assertTrue(all(item["synthetic"] for item in report["drift"]))
        self.assertTrue(report["synthetic_rows"])
        self.assertTrue(any("synthetic" in item for item in report["findings"]))

    def test_a_real_recorded_pair_reads_as_not_synthetic(self):
        path = self.candidate(lambda document: None)
        report = doctor.rehearse(path, _BASELINE)
        self.assertEqual(report["drift"], [])
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(record["synthetic"])
        self.assertFalse(self.baseline["synthetic"])

    def test_the_rehearsal_never_writes_inside_the_repository(self):
        before = _repo_hashes()
        path = self.candidate(
            lambda document: document["oracle_packages"].pop(
                sorted(document["oracle_packages"])[0]))
        doctor.rehearse(path, _BASELINE)
        after = _repo_hashes()
        self.assertEqual(before, after,
                         "the rehearsal mutated the repository")

    def test_the_rehearsal_cli_renders_findings_and_drift(self):
        path = self.candidate(
            lambda document: document["oracle_packages"].pop(
                sorted(document["oracle_packages"])[0]))
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = doctor.main(["--rehearse", str(path), "--against", str(_BASELINE)])
        self.assertEqual(code, doctor.EXIT_FAIL)
        output = stream.getvalue()
        self.assertIn("dsh-doctor --rehearse", output)
        self.assertIn("synthetic", output)

    def test_the_rehearsal_cli_is_clean_on_a_non_drift_pair(self):
        path = self.candidate(lambda document: None)
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = doctor.main(["--rehearse", str(path), "--against", str(_BASELINE)])
        self.assertEqual(code, doctor.EXIT_OK)
        self.assertIn("no drift", stream.getvalue())


# ══════════════════════════════════════════════════════════════════════════
# --record-evidence: isolation + the single writing path
# ══════════════════════════════════════════════════════════════════════════


class RecordEvidenceTests(DoctorCase):

    def test_record_evidence_writes_only_the_named_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            target = Path(tmp) / "out" / "host-facts.json"
            before = _repo_hashes()
            result = doctor.record_evidence(
                _PACKAGE_ROOT, out=target,
                env={"DSH_HOME": str(home), "USERPROFILE": str(home),
                     "HOME": str(home)})
            after = _repo_hashes()
            self.assertEqual(before, after,
                             "record-evidence touched the repository")
            self.assertTrue(target.is_file())
            self.assertEqual(result["out"], str(target))
            document = json.loads(target.read_text(encoding="utf-8"))
            self.assertIn("captured_at", document)
            self.assertIs(document["synthetic"], False)
            self.assertIn("plane", document)
            self.assertIn("rows", document)

    def test_record_evidence_records_unknown_facts_as_null_not_guesses(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            target = Path(tmp) / "host-facts.json"
            doctor.record_evidence(
                _PACKAGE_ROOT, out=target,
                env={"DSH_HOME": str(home), "USERPROFILE": str(home),
                     "HOME": str(home)})
            document = json.loads(target.read_text(encoding="utf-8"))
            # The plane probe is read-only and resolves whatever installation it
            # can find; what must *never* happen is a fabricated value. Every
            # recorded row therefore carries `source: recorded`, the probe
            # outcome is one of the measured states or null, and the version is
            # either the measured string or null — never a default.
            self.assertTrue(document["dsh_version"] is None
                            or isinstance(document["dsh_version"], str))
            self.assertEqual(len(document["rows"]), 29)
            for row in document["rows"]:
                self.assertEqual(row["source"], "recorded")
                self.assertIn(row["resolved"], (True, False, None))
                if row["resolved"] is None:
                    self.assertIsNone(row["probe_result"])
                    self.assertIsNone(row["module"])
                for key in ("accepted_keys", "required_keys"):
                    self.assertEqual(row[key], [],
                                     f"{row['row_id']}.{key} must not be invented")

    def test_the_shipped_baseline_is_shaped_like_a_recorded_factsheet(self):
        document = json.loads(_BASELINE.read_text(encoding="utf-8"))
        for field in doctor.FACTSHEET_REQUIRED_FIELDS:
            self.assertIn(field, document)
        self.assertIs(document["synthetic"], False)
        self.assertEqual(document["dsh_version"], "0.1.5-rc.1")
        self.assertEqual(len(document["rows"]), 29)

    def test_the_baseline_version_is_the_measured_one_not_a_hard_coded_one(self):
        # The fixture's own name carries the version, and the recorded version
        # must agree with it: a hand-edited version would break the arrangement.
        document = json.loads(_BASELINE.read_text(encoding="utf-8"))
        self.assertIn(document["dsh_version"], _BASELINE.name)


# ══════════════════════════════════════════════════════════════════════════
# the shared helpers
# ══════════════════════════════════════════════════════════════════════════


class HelperTests(DoctorCase):

    def test_version_tuple_orders_prereleases_below_releases(self):
        self.assertEqual(doctor._compare_versions(
            doctor._version_tuple("0.1.5-rc.1"),
            doctor._version_tuple("0.1.5")), -1)
        self.assertEqual(doctor._compare_versions(
            doctor._version_tuple("0.1.5"),
            doctor._version_tuple("0.2.0")), -1)
        self.assertEqual(doctor._compare_versions(
            doctor._version_tuple("0.2.0"),
            doctor._version_tuple("0.2.0")), 0)
        self.assertEqual(doctor._version_tuple("not-a-version"), ())

    def test_version_in_range_is_inclusive(self):
        self.assertTrue(doctor._version_in_range("0.1.5-rc.1", ["0.1.0", "0.2.0"]))
        self.assertTrue(doctor._version_in_range("0.1.0", ["0.1.0", "0.2.0"]))
        self.assertFalse(doctor._version_in_range("0.3.0", ["0.1.0", "0.2.0"]))
        self.assertFalse(doctor._version_in_range(None, ["0.1.0", "0.2.0"]))
        self.assertFalse(doctor._version_in_range("0.1.0", None))

    def test_render_report_prints_stage_lines_and_the_boundary_state(self):
        report = doctor.run_doctor(_PACKAGE_ROOT, offline=True)
        stream = io.StringIO()
        doctor.render_report(report, stream=stream)
        output = stream.getvalue()
        for ident in _STAGE_IDS:
            self.assertIn(f"{ident} ", output)
        self.assertIn("28w boundary", output)

    def test_the_engine_route_propagates_the_refused_code(self):
        """`verify_workflow.py dsh-doctor` must not swallow the exit code.

        The delegation is a thin wrapper, so the exit-code contract belongs to
        `dsh_doctor`; a wrapper that returned normally would report success for
        a refused run.
        """
        import verify_workflow

        class Args:
            json = False
            stage = None
            offline = False
            selftest = False
            record_evidence = False
            out = None
            rehearse = "candidate.json"
            against = None
            allow_host_probe = False
            fail_on_issues = False

        with self.assertRaises(SystemExit) as caught:
            verify_workflow.cmd_dsh_doctor(Args())
        self.assertEqual(caught.exception.code, doctor.EXIT_REFUSED)

    def test_the_engine_route_returns_zero_for_a_clean_offline_run(self):
        import verify_workflow

        class Args:
            json = True
            stage = None
            offline = True
            selftest = False
            record_evidence = False
            out = None
            rehearse = None
            against = None
            allow_host_probe = False
            fail_on_issues = False

        stream = io.StringIO()
        with unittest.mock.patch.dict(
                os.environ, {"DSH_HOME": str(self.rendered_home())}):
            with contextlib.redirect_stdout(stream):
                code = verify_workflow.cmd_dsh_doctor(Args())
        self.assertEqual(code, doctor.EXIT_OK)
        payload = json.loads(stream.getvalue())
        self.assertEqual(len(payload["stages"]), len(_STAGE_IDS))

    def test_the_json_cli_form_is_machine_readable(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = doctor.main(["--offline", "--json"])
        payload = json.loads(stream.getvalue())
        self.assertEqual(payload["command"], "dsh-doctor")
        self.assertEqual(payload["exit_code"], code)


# ══════════════════════════════════════════════════════════════════════════
# R0 rework (REVIEW-FEAT-031-CODE-R0): F-03 / F-06 / F-07
# ══════════════════════════════════════════════════════════════════════════


class OutTargetGuardTests(DoctorCase):
    """F-06 — `--out` must not be able to overwrite what it does not own."""

    def test_the_contract_is_refused(self):
        target = _PACKAGE_ROOT / "adapters" / "dsh" / "host-contract.json"
        self.assertTrue(target.is_file())
        before = target.read_bytes()
        with self.assertRaises(doctor.Refused) as caught:
            doctor.record_evidence(_PACKAGE_ROOT, out=target,
                                   env={"DSH_HOME": str(self.rendered_home())})
        self.assertIn("refuses the contract itself", str(caught.exception))
        self.assertEqual(target.read_bytes(), before,
                         "the refused run still touched the contract")

    def test_a_contract_copy_handed_to_out_is_refused(self):
        # The reviewer's exact probe: a *copy* of the contract is not the
        # contract path, and an existing file this command did not write is
        # never replaced — wherever it lives.
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "host-contract.json"
            shutil.copyfile(_PACKAGE_ROOT / "adapters" / "dsh" / "host-contract.json",
                            copy)
            with self.assertRaises(doctor.Refused) as caught:
                doctor._guard_out_target(copy, _PACKAGE_ROOT)
            self.assertIn("refuses to overwrite", str(caught.exception))
            with self.assertRaises(doctor.Refused):
                doctor.record_evidence(
                    _PACKAGE_ROOT, out=copy,
                    env={"DSH_HOME": str(self.rendered_home())})
            self.assertEqual(
                copy.read_bytes(),
                (_PACKAGE_ROOT / "adapters" / "dsh" / "host-contract.json").read_bytes())

    def test_an_in_package_target_that_is_not_a_factsheet_is_refused(self):
        for relative in ("package.json", "cordis.patch.yml",
                         "adapters/dsh/adapter-manifest.json"):
            target = _PACKAGE_ROOT / relative
            self.assertTrue(target.is_file(), relative)
            with self.assertRaises(doctor.Refused) as caught:
                doctor._guard_out_target(target, _PACKAGE_ROOT)
            message = str(caught.exception)
            self.assertIn("refuses", message, relative)
            self.assertIn(target.name, message, relative)

    def test_a_new_in_package_target_outside_the_fixture_directory_is_refused(self):
        # A path that does not exist yet still has to be a factsheet, and still
        # has to live under `adapters/dsh/fixtures/`.
        with self.assertRaises(doctor.Refused) as caught:
            doctor._guard_out_target(_PACKAGE_ROOT / "skills" / "x.json",
                                     _PACKAGE_ROOT)
        self.assertIn("inside the package", str(caught.exception))

    def test_a_factsheet_name_in_the_wrong_directory_is_refused(self):
        with self.assertRaises(doctor.Refused) as caught:
            doctor._guard_out_target(_PACKAGE_ROOT / "host-facts-0.0.0.json",
                                     _PACKAGE_ROOT)
        self.assertIn("adapters/dsh/fixtures", str(caught.exception))

    def test_a_resolved_dot_dot_detour_is_refused(self):
        detour = _PACKAGE_ROOT / "adapters" / "dsh" / "fixtures" / ".." / "host-contract.json"
        with self.assertRaises(doctor.Refused):
            doctor._guard_out_target(detour, _PACKAGE_ROOT)

    def test_the_owned_target_shape_is_allowed(self):
        doctor._guard_out_target(
            _PACKAGE_ROOT / "adapters" / "dsh" / "fixtures" / "host-facts-9.9.9.json",
            _PACKAGE_ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            doctor._guard_out_target(Path(tmp) / "anything.json", _PACKAGE_ROOT)

    def test_the_documented_default_target_passes_the_guard(self):
        # The default target is a factsheet under `adapters/dsh/fixtures/`; the
        # guard must not make the documented invocation impossible.
        default = (_PACKAGE_ROOT / "adapters" / "dsh" / "fixtures"
                   / "host-facts-0.1.5-rc.1.json")
        doctor._guard_out_target(default, _PACKAGE_ROOT)


class StageSubsetPreludeTests(DoctorCase):
    """F-07 — a `--stage` subset must not lose the home S0 resolves."""

    def test_a_subset_without_s0_runs_s0_as_a_disclosed_prelude(self):
        report = self.run_doctor(stages=["S1"])
        self.assertEqual([record["stage"] for record in report["stages"]], ["S1"])
        prelude = report["prelude"]
        self.assertEqual([item["stage"] for item in prelude], ["S0"])
        self.assertIn("DSH_HOME=", prelude[0]["reason"])
        self.assertIn("resolves ctx.dsh_home", prelude[0]["why"])

    def test_the_subset_no_longer_blames_the_home(self):
        report = self.run_doctor(stages=["S1"])
        s1 = self.stages_of(report)["S1"]
        self.assertNotIn("no resolved DSH_HOME", s1["reason"])
        self.assertEqual(s1["verdict"], "PASS", s1["reason"])

    def test_a_subset_that_includes_s0_has_no_prelude(self):
        report = self.run_doctor(stages=["S0", "S7"])
        self.assertEqual(report["prelude"], [])
        self.assertEqual([record["stage"] for record in report["stages"]],
                         ["S0", "S7"])

    def test_a_full_run_has_no_prelude(self):
        self.assertEqual(self.run_doctor()["prelude"], [])

    def test_the_prelude_reason_is_the_record_only_stage_reason(self):
        report = self.run_doctor(stages=["S4"])
        self.assertIn("record-only", report["prelude"][0]["reason"])


class RecordEvidenceRemediationTests(DoctorCase):
    """F-03 — the remediation must name the step that actually closes the gap."""

    def test_s3_remediation_does_not_promise_a_contract_write(self):
        home = self.rendered_home()
        # `_profile_planes` reports `$DSH_HOME/profiles/node_modules` when that
        # directory exists, which is the branch that carries the remediation.
        (home / "profiles" / "node_modules").mkdir(parents=True, exist_ok=True)
        report = self.run_doctor(offline=True, env={"DSH_HOME": str(home)})
        s3 = self.stages_of(report)["S3"]
        blob = json.dumps(s3["remediation"], ensure_ascii=False)
        self.assertIn("reviewed commit", blob)
        self.assertNotIn("`evidence.*` carries the measured version", blob)

    def test_the_boundary_remediation_matches_the_implementation(self):
        from checks import dsh_boundary

        subject = dsh_boundary.Subject(_PACKAGE_ROOT)
        criterion = dsh_boundary.k7_version_evidence(
            dsh_boundary.ContractFacts(subject), subject)
        self.assertEqual(criterion.verdict, "NOT_RUN")
        self.assertIn("maintainer", criterion.reason)
        self.assertNotIn("to make the TTL and version comparison available",
                         criterion.reason)

    def test_record_evidence_notes_state_what_the_command_actually_does(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "host-facts.json"
            doctor.record_evidence(
                _PACKAGE_ROOT, out=target,
                env={"DSH_HOME": str(Path(tmp) / "home"),
                     "USERPROFILE": str(Path(tmp) / "home")})
            document = json.loads(target.read_text(encoding="utf-8"))
        self.assertIn("only file this command writes", document["notes"])
        self.assertNotIn("redirected DSH_HOME", document["notes"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
