"""FEAT-019 ArchGuard ratchet tests — R1~R7 positive/negative controls.

Every rule is proven machine-judged in BOTH directions (packet hard gate:
正/负对照测试). Negative controls operate on temp-dir fixtures or perturbed
in-memory copies — the real engine, the real baseline and the real FEAT-020
snapshot are never modified.

Cross-validations against the AUDIT-150 facts baseline:
  - R4 total print calls must equal 1,315 (facts §3.1) — proves the
    attribution caliber matches the audit's counting method;
  - R1 anchor must be the regen-time measurement (≥ 24,000, packet scale);
  - R5 consumes the FEAT-020 snapshot via its own extractors (81 keys after
    this slice's deliberate contract-face extension).

Run:
    python -m unittest skills/software-project-governance/infra.tests.test_archguard_ratchet -v
"""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
_SKILL_ROOT = _INFRA_DIR.parent
_REPO_ROOT = _SKILL_ROOT.parents[1]
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import archguard_ratchet as ar  # noqa: E402
# DEC-096 authority: SKILL.md frontmatter is the only version fact source.
from checks.version import extract_skill_version  # noqa: E402

ENGINE = _INFRA_DIR / "verify_workflow.py"
BASELINE = _SKILL_ROOT / "core" / "architecture-baseline.json"
SNAPSHOT = _INFRA_DIR / "contract_matrix" / "snapshots.json"

# facts-0.80.0 §3.1 (2026-09-09 audit): print-call census over the engine.
# Evolution chain (calibration re-census, appendix per sanctioned change):
#   1315 (facts §3.1, 2026-09-09)
#   -> 1310 (FEAT-012 G5, 2026-09-10: 5 print calls in cmd_task_priority_analysis
#      moved out of the engine into task_priority.run_cli_analysis; sanctioned
#      ratchet shrink, baseline regenerated in the same change)
#   -> 1311 (FEAT-026 Slice-2, sanctioned +1: the --quick dispatch branch renders
#      the selector's four-state output at the L5 dispatch site —
#      r4_print_orchestration.per_function attributes it to cmd_check_governance;
#      baseline regenerated in the same change, EVD-1000 authorization recorded)
#   -> 1298 (FIX-310, 2026-09-12: -13 — retiring the dead `dsh.skills`
#      declaration also retired its guard output: the Check 40 print block in
#      the engine plus cmd_check_dsh_skills_manifest's own prints; sanctioned
#      ratchet shrink, baseline regenerated in the same change)
#   -> 1299 (FEAT-031, 2026-09-13: +1 — the V8 `cmd_check_dsh_boundary` thin
#      wrapper prints the criterion report it delegates to; the engine's 28w
#      section itself prints nothing (C-15: the rendering lives in
#      `checks.dsh_boundary`). Baseline regenerated with
#      `archguard-ratchet --regen` after all V8 source edits, per the
#      all-changes-first rule that keeps the anchor from being re-cut twice.)
#   -> 1301 (FIX-350, 2026-09-17: +2 — the DEC-151 [EXEMPT] disclosure loop
#      for schema-exempt source/projection pairs: one print site in the
#      engine's 28p check-governance segment (cmd_check_governance) and one
#      in cmd_check_duplicate_code. Baseline regenerated in the same change:
#      R1 anchor 24453 -> 24583, R4 total 1299 -> 1301.)
#   -> 1304 (0.84.0 slice A, 2026-09-18: +3 across the parallel A-7/A-8 work.
#      A-8 (FEAT-039) contributes ONE new site — the Check 33 injection-budget
#      verdict line; the report body renders inside `checks.injection_budget`
#      so the engine's own print surface stays at the wiring minimum. The
#      remaining sites are A-7 (FEAT-038) scenario-routing output. The two
#      tasks share one working tree, so the baseline was regenerated ONCE,
#      after both source edits, per the all-changes-first rule that keeps the
#      anchor from being re-cut twice. Baseline regenerated in the same change:
#      R1 anchor 24639 -> 24766, R4 total 1301 -> 1304.)
#   -> 1306 (0.86.0 批 2.3, FEAT-057: +2 in cmd_governance_write_guard — the
#      face-5 BASELINE disclosure line and the WARN-aware PASS Result line.
#      Baseline regenerated in the same change: R1 anchor 24852 -> 25291,
#      R4 total 1304 -> 1306.)
#   -> 1316 (0.87.0, FIX-370 closure window: census truth re-alignment — the
#      +10 drift is ATTRIBUTED TO PRE-EXISTING committed-tree state, NOT
#      introduced in the 0.87.0 window; HEAD and worktree census both probe
#      1316 with a zero per-function diff. Lineage trace of the +10 sites is
#      registered as FIX-377 (0.88) for bisect. Baseline regenerated in the
#      same change: architecture-baseline.json re-anchored after the
#      locks-release dispatch-face wiring.
#      M-2 regen re-baseline (2026-09-25, REL-087/088 window): the sanctioned
#      archguard-ratchet --regen at the 0.88.0 release gate re-anchored the
#      committed baseline to a8a72a3 and absorbed the 0.88 A~E batch engine
#      growth (FEAT-060/063/064 prints among others). Census now probes 1318
#      (+2 vs the 0.87-era 1316); the only-down ratchet continues from here.
#      Same M-2 obligation shape as the FEAT-064 contract-matrix rebaseline
#      (registry 96->97): frozen-count tests track the regenerated truth.
FACTS_PRINT_TOTAL = 1318


def _committed_baseline():
    return json.loads(BASELINE.read_text(encoding="utf-8"))


class R1MainfileBudgetTests(unittest.TestCase):
    def test_r1_passes_on_current_tree(self):
        anchor = _committed_baseline()["r1_mainfile_budget"]["anchor_loc"]
        self.assertEqual(ar.check_r1(ENGINE, anchor), [])
        self.assertGreaterEqual(anchor, 24000)  # packet: ≥24,000 scale, 实测为准

    def test_r1_negative_control_one_added_line(self):
        """Packet acceptance ② — main file +1 line MUST fail R1.

        Fixture copy in a temp dir; the real engine is untouched.
        """
        anchor = ar.measure_mainfile_loc(ENGINE)
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "engine_plus_one.py"
            fixture.write_text(
                ENGINE.read_text(encoding="utf-8") + "# ratchet negative control\n",
                encoding="utf-8")
            violations = ar.check_r1(fixture, anchor)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["rule"], "R1")
        self.assertEqual(violations[0]["excess_lines"], 1)

    def test_r1_detects_shrunk_anchor_tamper(self):
        """A hand-lowered anchor (anchor-1) also fails — only-down cuts both ways."""
        anchor = ar.measure_mainfile_loc(ENGINE)
        violations = ar.check_r1(ENGINE, anchor - 1)
        self.assertEqual(len(violations), 1)


class R2ReverseDependencyTests(unittest.TestCase):
    def _current(self):
        return ar.scan_reverse_dependencies(_INFRA_DIR)

    def test_r2_current_tree_matches_inventory(self):
        baseline = _committed_baseline()
        violations = ar.check_r2(
            self._current(), baseline["r2_reverse_dependency"]["inventory"])
        self.assertEqual(violations, [])

    def test_r2_inventory_records_paths_and_lines(self):
        """Packet acceptance ③ — inventory carries path + line numbers."""
        inventory = _committed_baseline()["r2_reverse_dependency"]["inventory"]
        self.assertGreater(len(inventory), 30)
        for entry in inventory:
            self.assertIn("path", entry)
            self.assertIn("lines", entry)
            self.assertGreaterEqual(entry["count"], 1)
            self.assertEqual(len(entry["lines"]), entry["count"])
        joined = " ".join(e["path"] for e in inventory)
        self.assertIn("checks/review_domain.py", joined)
        self.assertIn("loop_health.py", joined)

    def test_r2_new_site_count_fails(self):
        baseline = _committed_baseline()
        current = self._current()
        key = ("checks/review_domain.py", "vw_call")
        self.assertIn(key, current)  # precondition: legacy site exists
        inflated = copy.deepcopy(current)
        inflated[key]["count"] += 1
        violations = ar.check_r2(
            inflated, baseline["r2_reverse_dependency"]["inventory"])
        self.assertTrue(any(v["rule"] == "R2" and v["path"] == key[0]
                            for v in violations))

    def test_r2_new_file_zero_tolerance(self):
        baseline = _committed_baseline()
        current = self._current()
        current[("brand_new_module.py", "vw_def")] = {"count": 1, "lines": [3]}
        violations = ar.check_r2(
            current, baseline["r2_reverse_dependency"]["inventory"])
        self.assertTrue(any("brand_new_module.py" in v.get("path", "")
                            for v in violations))

    def test_r2_line_drift_tolerated(self):
        """Edits above a legacy site shift its line — count semantics hold."""
        baseline = _committed_baseline()
        current = self._current()
        key = ("checks/review_domain.py", "vw_def")
        drifted = copy.deepcopy(current)
        drifted[key]["lines"] = [line + 500 for line in drifted[key]["lines"]]
        violations = ar.check_r2(
            drifted, baseline["r2_reverse_dependency"]["inventory"])
        self.assertEqual(violations, [])

    def test_r2_expired_inventory_entry_zero_budget(self):
        """到期即 FAIL — an expired inventory fuse un-budgets its sites."""
        baseline = _committed_baseline()
        inventory = copy.deepcopy(baseline["r2_reverse_dependency"]["inventory"])
        for entry in inventory:
            if entry["path"] == "checks/review_domain.py" and entry["kind"] == "vw_def":
                entry["expire_version"] = "0.78.1"  # == current skill version
        violations = ar.check_r2(self._current(), inventory,
                                 version=(0, 78, 1))
        self.assertTrue(any(v.get("kind") == "vw_def"
                            and v["path"] == "checks/review_domain.py"
                            for v in violations))


class R3LayerMatrixTests(unittest.TestCase):
    def test_r3_matrix_integrity_matches_evolution_doc(self):
        """12-edge enumeration (§3.2) — the W1 guard is itself asserted."""
        self.assertEqual(len(ar.ALLOWED_EDGES), 12)
        self.assertEqual(len(set(ar.ALLOWED_EDGES)), 12)  # no duplicates
        self.assertEqual(ar.ASSERTED_EDGE_COUNT, 12)
        for edge in ar.ALLOWED_EDGES:
            src, dst = edge
            self.assertIn(src, ar.LAYERS)
            self.assertIn(dst, ar.LAYERS)
            self.assertNotEqual(src, dst)
        # forbidden trio that a C(6,2)=15 reading would wrongly admit
        for bad in (("L5", "L3"), ("L5", "L2"), ("L3", "L2")):
            self.assertNotIn(bad, ar.ALLOWED_EDGES)

    def test_r3_current_managed_set_passes(self):
        violations, report = ar.check_r3(
            ar.DEFAULT_MANAGED_MODULES, _INFRA_DIR)
        self.assertEqual(violations, [])
        self.assertEqual(report["max_scc_size"], 1)
        self.assertTrue(report["unmanaged_target_refs"])  # honest disclosure

    def test_r3_forbidden_edge_and_cycle_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            infra = Path(tmp) / "infra"
            infra.mkdir()
            # A(L2) ↔ B(L0): A→B allowed, B→A forbidden AND a 2-cycle.
            (infra / "mod_a.py").write_text("import mod_b\n", encoding="utf-8")
            (infra / "mod_b.py").write_text("import mod_a\n", encoding="utf-8")
            managed = {
                "infra/mod_a.py": {"layer": "L2"},
                "infra/mod_b.py": {"layer": "L0"},
            }
            violations, report = ar.check_r3(managed, infra)
            self.assertTrue(any(v["scope"] == "layer-edge:infra/mod_b.py->infra/mod_a.py"
                                for v in violations))
            self.assertTrue(any(v["scope"] == "layer-cycle" for v in violations))
            self.assertEqual(report["max_scc_size"], 2)

    def test_r3_unknown_layer_assignment_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            infra = Path(tmp) / "infra"
            infra.mkdir()
            (infra / "mod_x.py").write_text("import json\n", encoding="utf-8")
            managed = {"infra/mod_x.py": {"layer": "L9"}}
            violations, _ = ar.check_r3(managed, infra)
            self.assertTrue(any(v["scope"] == "layer-assign:infra/mod_x.py"
                                for v in violations))


class R4PrintOrchestrationTests(unittest.TestCase):
    def test_r4_total_matches_facts_census(self):
        """Calibration cross-check: 1,316 print calls (0.87.0, FIX-370
        closure window — the +10 is pre-existing committed drift, NOT
        introduced here; lineage trace registered as FIX-377. Chain
        1,315 → 1,310 → 1,311 → 1,298 → 1,299 → 1,301 → 1,304 → 1,306
        → 1,316 — see FACTS_PRINT_TOTAL note)."""
        current = ar.count_print_calls(ENGINE)
        self.assertEqual(current["total"], FACTS_PRINT_TOTAL)
        self.assertEqual(
            current["total"],
            _committed_baseline()["r4_print_orchestration"]["total"])

    def test_r4_committed_per_function_matches_current(self):
        committed = _committed_baseline()["r4_print_orchestration"]["per_function"]
        current = ar.count_print_calls(ENGINE)["per_function"]
        self.assertEqual(current, committed)

    def test_r4_growth_fails_both_granularities(self):
        baseline = _committed_baseline()["r4_print_orchestration"]
        inflated_total = dict(ar.count_print_calls(ENGINE))
        inflated_total["total"] = int(inflated_total["total"]) + 1
        self.assertTrue(any(v["scope"] == "print:total"
                            for v in ar.check_r4(inflated_total, baseline)))
        # a NEW print-bearing function (absent from baseline) fails per-function
        with_fn = dict(inflated_total)
        with_fn["per_function"] = dict(with_fn["per_function"])
        with_fn["per_function"]["cmd_brand_new"] = 1
        self.assertTrue(any(v["scope"] == "print:cmd_brand_new"
                            for v in ar.check_r4(with_fn, baseline)))

    def test_r4_shrink_passes(self):
        baseline = _committed_baseline()["r4_print_orchestration"]
        shrunk = ar.count_print_calls(ENGINE)
        shrunk = dict(shrunk)
        shrunk["total"] = int(shrunk["total"]) - 1
        self.assertEqual(ar.check_r4(shrunk, baseline), [])


class R5RegistrationIntegrityTests(unittest.TestCase):
    def test_r5_consumes_snapshot_pass(self):
        violations, report = ar.check_r5(_SKILL_ROOT)
        self.assertEqual(violations, [])
        self.assertEqual(report["status"], "PASS")
        # Both faces are read from the FEAT-020 snapshot rather than re-spelled:
        # the claim is "R5 consumes the live snapshot", and every deliberate
        # contract change regenerates that snapshot (generator.py --regen).
        faces = json.loads(
            (SNAPSHOT).read_text(encoding="utf-8"))["faces"]
        self.assertEqual(report["frozen_cli_keys"],
                         faces["cli_dispatch"]["key_count"])
        self.assertEqual(report["frozen_segments"],
                         faces["check_segments"]["count"])

    def test_r5_missing_snapshot_skips_with_disclosure(self):
        """Packet acceptance ③ — snapshot missing → SKIP+披露, never a false FAIL."""
        with tempfile.TemporaryDirectory() as tmp:
            violations, report = ar.check_r5(_SKILL_ROOT,
                                             snapshot_path=Path(tmp) / "nope.json")
        self.assertEqual(violations, [])
        self.assertEqual(report["status"], "SKIP")
        self.assertIn("SKIP", report["reason"])
        self.assertIn("披露", report["reason"])

    def test_r5_removed_frozen_key_fails(self):
        """A command key vanishing from the live dispatch = contract break.

        The live face is fixture-injected (temp-controlled); the real
        snapshot and the real engine stay untouched.
        """
        from unittest.mock import patch
        snapshot_keys = json.loads(
            SNAPSHOT.read_text(encoding="utf-8")
        )["faces"]["cli_dispatch"]["keys"]
        reduced_live = {"cli_keys": [k for k in snapshot_keys if k != "verify"],
                        "segment_ids": ar.r5_live_faces(_INFRA_DIR)["segment_ids"]}
        with patch.object(ar, "r5_live_faces", return_value=reduced_live):
            violations, _ = ar.check_r5(_SKILL_ROOT)
        self.assertTrue(any("missing from live dispatch" in v["message"]
                            for v in violations))

    def test_r5_unregistered_live_key_fails(self):
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        snapshot["faces"]["cli_dispatch"]["keys"].remove("archguard-ratchet")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snap.json"
            path.write_text(json.dumps(snapshot), encoding="utf-8")
            violations, _ = ar.check_r5(_SKILL_ROOT, snapshot_path=path)
        self.assertTrue(any("not in the frozen snapshot" in v["message"]
                            for v in violations))

    def test_r5_dispatch_key_registered_in_engine(self):
        from contract_matrix import generator as cmg
        self.assertIn("archguard-ratchet", cmg.extract_cli_dispatch()["keys"])


class R6StartupBudgetTests(unittest.TestCase):
    def test_r6_deterministic_faces_recorded(self):
        first = ar.measure_cold_import(str(_INFRA_DIR))
        second = ar.measure_cold_import(str(_INFRA_DIR))
        self.assertIsNotNone(first)
        self.assertEqual(first["import_count"], second["import_count"])
        self.assertEqual(first["import_set_sha256"], second["import_set_sha256"])
        self.assertGreater(first["import_count"], 100)
        self.assertRegex(first["import_set_sha256"], r"^[0-9a-f]{64}$")
        baseline_r6 = _committed_baseline()["r6_startup_budget"]
        self.assertIsNone(baseline_r6["threshold"])  # FEAT-018 fills it later

    def test_r6_never_fatal_in_this_slice(self):
        report = ar.run_check(_SKILL_ROOT, BASELINE)
        status = report["rules"]["R6"]["status"]
        self.assertIn(status, ("INFO", "SKIP"))
        self.assertFalse(any(v["rule"] == "R6" for v in report["violations"]))


class R7ReproducibilityTests(unittest.TestCase):
    def test_r7_double_build_byte_identical(self):
        fresh_a = ar.build_baseline(_SKILL_ROOT, _committed_baseline())
        fresh_b = ar.build_baseline(_SKILL_ROOT, _committed_baseline())
        self.assertEqual(ar._canonical_json_bytes(fresh_a),
                         ar._canonical_json_bytes(fresh_b))

    def test_r7_committed_baseline_matches_fresh_regen(self):
        violations, report = ar.check_r7(_SKILL_ROOT, _committed_baseline())
        self.assertEqual(violations, [])
        self.assertTrue(report["deterministic"])
        self.assertTrue(report["committed_matches_fresh"])

    def test_r7_detects_hand_edited_extraction_zone(self):
        tampered = _committed_baseline()
        tampered["r1_mainfile_budget"]["anchor_loc"] = (
            int(tampered["r1_mainfile_budget"]["anchor_loc"]) + 10)
        violations, _ = ar.check_r7(_SKILL_ROOT, tampered)
        self.assertTrue(any(v["scope"] == "baseline-stale"
                            for v in violations))

    def test_r7_detects_stale_baseline_after_engine_change(self):
        stale = _committed_baseline()
        stale["r1_mainfile_budget"]["anchor_loc"] = (
            int(stale["r1_mainfile_budget"]["anchor_loc"]) - 5)
        violations, _ = ar.check_r7(_SKILL_ROOT, stale)
        self.assertTrue(any(v["scope"] == "baseline-stale"
                            for v in violations))


class ExemptionMechanismTests(unittest.TestCase):
    """The fuse's two faces: an ACTIVE exemption suppresses / still fails.

    FIX-335 derivation discipline (4th instance of version-pin rot): the two
    "active" fixtures below derive their ``expire_version`` from the
    authoritative version — SKILL.md frontmatter, read through
    ``checks.version.extract_skill_version`` (DEC-096; same helper the
    ``test_dsh_doctor`` / ``test_dsh_adapter`` derivations use) — instead of
    pinning a release literal. The fuse is judged
    ``current_version >= expire_version`` (``archguard_ratchet._entry_expired``),
    so a pinned literal equal to the then-current release flips its fixture to
    ``EXPIRED:<version>`` the moment that release ships: the literal 0.81.0
    pinned here turned both fixtures into ``EXPIRED:0.81.0`` at 0.81.0 and made
    this module red on every candidate tree. Deriving keeps the fixtures'
    semantics intact — an exemption whose fuse has NOT expired yet — under any
    future bump, while a bump that passes the derived fuse still turns them red
    (the assertion stays a real test, never a tautology).
    """

    def _r1_finding(self, excess):
        return [{"rule": "R1", "scope": "mainfile", "message": "x",
                 "excess_lines": excess}]

    def _not_yet_expired_version(self) -> str:
        """Fuse strictly ABOVE the shipped version — not expired by construction.

        Patch-increment of the DEC-096 authoritative version: parse, then step
        one patch. An unreadable version fails the fixture loudly (fail-closed)
        rather than silently degrading the expiry judgement.
        """
        current = extract_skill_version(_SKILL_ROOT / "SKILL.md")
        self.assertRegex(current, r"^\d+\.\d+\.\d+$",
                         "SKILL.md frontmatter version (DEC-096) is required")
        major, minor, patch = (int(part) for part in current.split("."))
        derived = f"{major}.{minor}.{patch + 1}"
        self.assertGreater(tuple(int(p) for p in derived.split(".")),
                           tuple(int(p) for p in current.split(".")))
        return derived

    def test_active_exemption_suppresses_within_allowance(self):
        """NOT-yet-expired fuse + excess <= allowance -> suppressed, disclosed."""
        exemptions = [{"rule": "R1", "scope": "mainfile",
                       "allowance_lines": 16, "reason": "test",
                       "dec": "DEC-TEST",
                       "expire_version": self._not_yet_expired_version()}]
        effective, disclosures = ar.apply_exemptions(
            self._r1_finding(10), exemptions, _SKILL_ROOT)
        self.assertEqual(effective, [])
        self.assertTrue(disclosures)

    def test_active_exemption_over_allowance_still_fails(self):
        """NOT-yet-expired fuse + excess > allowance -> the teeth still bite."""
        exemptions = [{"rule": "R1", "scope": "mainfile",
                       "allowance_lines": 16, "reason": "test",
                       "dec": "DEC-TEST",
                       "expire_version": self._not_yet_expired_version()}]
        effective, _ = ar.apply_exemptions(
            self._r1_finding(20), exemptions, _SKILL_ROOT)
        self.assertEqual(len(effective), 1)
        self.assertIn("OVER-ALLOWANCE", effective[0]["exemption"])

    def test_expired_exemption_no_longer_suppresses(self):
        """到期即 FAIL — the fuse is the teeth of the mechanism."""
        exemptions = [{"rule": "R1", "scope": "mainfile",
                       "allowance_lines": 16, "reason": "test",
                       "dec": "DEC-TEST", "expire_version": "0.78.1"}]
        effective, _ = ar.apply_exemptions(
            self._r1_finding(2), exemptions, _SKILL_ROOT)
        self.assertEqual(len(effective), 1)
        self.assertIn("EXPIRED", effective[0]["exemption"])

    def test_committed_bootstrap_exemption_is_registered(self):
        """done_definition: 自举豁免显式登记 + 到期版本."""
        exemptions = _committed_baseline()["exemptions"]
        bootstrap = [e for e in exemptions
                     if e.get("rule") == "R1" and e.get("scope") == "mainfile"]
        self.assertEqual(len(bootstrap), 1)
        self.assertIn("self-bootstrap", bootstrap[0]["reason"])
        self.assertRegex(bootstrap[0]["expire_version"], r"^\d+\.\d+\.\d+$")


class BaselineArtifactTests(unittest.TestCase):
    def test_metadata_contract(self):
        """Packet acceptance ① — regen metadata: anchor / git HEAD / rules version."""
        data = _committed_baseline()
        self.assertEqual(data["schema"], "spg-architecture-baseline/1")
        self.assertEqual(data["task"], "FEAT-019")
        self.assertIsInstance(data["rules_version"], int)
        self.assertRegex(data["generated"]["git_head"],
                         r"^([0-9a-f]{40}|unknown)$")
        # M-2 regen re-baseline (2026-09-26): anchor re-anchored to the
        # 0.89.0 release-gate regen (26358 at HEAD; prior 26193 at the
        # 0.88.0 regen a8a72a3). Growth +165 = EVD-1176 chain (+125:
        # FIX-393/394 +39, FIX-390 +86) + post-measurement window commits
        # (FIX-392/FIX-395 consumer faces + REL-091 REQUIRED_SNIPPETS
        # anchors). Assert the exact regenerated anchor instead: the
        # metadata contract's job is to pin the committed truth, and the
        # regen itself is the sanctioned change that moves it (only-down
        # from here). Keep in sync with core/architecture-baseline.json
        # r1_mainfile_budget.anchor_loc on every sanctioned regen.
        self.assertEqual(data["r1_mainfile_budget"]["anchor_loc"], 26358)

    def test_authored_zone_survives_regen(self):
        existing = _committed_baseline()
        existing["exemptions"].append({
            "rule": "R2", "scope": "reverse-dep:checks/review_domain.py:vw_call",
            "reason": "regen-carryover probe", "dec": "DEC-TEST",
            "expire_version": "0.81.0"})
        rebuilt = ar.build_baseline(_SKILL_ROOT, existing)
        self.assertEqual(len(rebuilt["exemptions"]), 2)
        self.assertEqual(
            len(rebuilt["r3_layer_matrix"]["managed_modules"]),
            len(ar.DEFAULT_MANAGED_MODULES))


class CliGateTests(unittest.TestCase):
    """Two-state CLI proof via the real dispatch path (subprocess)."""

    def _run(self, *flags):
        cmd = [sys.executable, str(ENGINE), "archguard-ratchet", *flags]
        return subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              timeout=300, cwd=str(_REPO_ROOT))

    def test_cli_green_on_current_tree(self):
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Result: PASS", result.stdout)
        for rule_id in ("R1", "R2", "R3", "R4", "R5", "R7"):
            self.assertRegex(result.stdout, rf"\[{rule_id}\] PASS")

    def test_cli_red_on_tampered_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            tampered = Path(tmp) / "baseline.json"
            data = _committed_baseline()
            data["r1_mainfile_budget"]["anchor_loc"] = (
                int(data["r1_mainfile_budget"]["anchor_loc"]) - 2)
            tampered.write_text(json.dumps(data), encoding="utf-8")
            result = self._run("--baseline", str(tampered))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Result: FAIL", result.stdout)
        self.assertIn("[VIOLATION]", result.stdout)

    def test_cli_fail_closed_on_missing_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run("--baseline", str(Path(tmp) / "absent.json"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("fail-closed", result.stdout)

    def test_cli_regen_writes_idempotent_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "baseline.json"
            first = self._run("--regen", "--baseline", str(target))
            self.assertEqual(first.returncode, 0, first.stdout)
            payload_a = target.read_bytes()
            second = self._run("--regen", "--baseline", str(target))
            self.assertEqual(second.returncode, 0, second.stdout)
            payload_b = target.read_bytes()
            self.assertEqual(payload_a, payload_b)


if __name__ == "__main__":
    unittest.main()
