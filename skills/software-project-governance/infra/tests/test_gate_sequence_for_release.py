"""FIX-266 / REQ-145.4 — Check 37 gate-sequence-for-release tests (red→green).

Deliverable under test (design audit-145-watchdog-design-0.76.0.md §3.4,
test plan §5.3 — 8 cases, plus the FIX-266 acceptance-item extras:

1. ``check_gate_sequence_for_release(gates=None, published_tags=None,
   profile=None, lineage_mode="candidate")`` in
   ``infra/checks/gate_domain.py``: signal table G-s1 (published tag
   predates a ``passed`` prerelease gate → FAIL) / G-s2 (published tag
   exists with a ``pending`` prerelease gate → conservative FAIL) / G-s3
   (no git-visible tag but release gate passed with pending prereleases →
   fail-safe WARN); result contract ``{verdict, reason, violations,
   warnings, stats}``; verdict ∈ PASS / WARN / FAIL / no-verdict; NEVER
   raises.
2. Row-order derivation (DEC-153 ①): release gate = FIRST row whose
   阶段转换 cell contains「发布」; prerelease set = non-release rows read
   BEFORE it — no hard-coded gate ids, so standard/11 (tv G8) and
   lightweight/7 (router G5 — where G6 发布→运营 also contains「发布」)
   both derive correctly.
3. History exemption (DEC-153 ②): lineage_mode="candidate" → G-s1/G-s2
   FAIL; "released" → the SAME findings WARN-disclosed, never FAIL.
4. passed-on-entry (DEC-153 ④): treated as non-pending; all-on-entry
   prereleases → PASS; strong interlock applies only with ``passed`` rows.
5. Multiple tags: only the highest-semver (latest candidate) is judged.
6. BR-4 wiring: ``released_history_version`` roadmap probe; the embedded
   call inside ``check_release_readiness`` takes the lineage mode;
   ``cmd_check_release`` auto-promotes unpublished--version-aware runs to
   "released" for already-published versions.
7. git unavailable / degraded → G-s3 fail-safe WARN (never FAIL).
8. Numbering (F9): Check 37 block sits between Check 36 and the summary.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_gate_sequence_for_release.py -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw  # noqa: E402
from checks import gate_domain as gd  # noqa: E402


# ── Fixtures ────────────────────────────────────────────────────────────

def _gate(gate, transition, status, date="", evidence=""):
    return {"gate": gate, "transition": transition, "status": status,
            "date": date, "evidence": evidence}


def _tv_standard_gates(g6="pending", g7="pending", g8="pending",
                       on_entry="passed-on-entry"):
    """standard/11 gate table (tv style): release gate = G8 (→ 版本发布)."""
    return [
        _gate("G1", "→ 调研", on_entry, "2026-08-19", "DEC-001"),
        _gate("G2", "→ 技术选型", on_entry, "2026-08-19", "DEC-002"),
        _gate("G3", "→ 环境搭建", on_entry, "2026-08-19", "DEC-003"),
        _gate("G4", "→ 架构设计", on_entry, "2026-08-19", "DEC-004"),
        _gate("G5", "→ 开发实现", on_entry, "2026-08-19", "DEC-005"),
        _gate("G6", "→ 测试", g6),
        _gate("G7", "→ 防护网与CI/CD", g7),
        _gate("G8", "→ 版本发布", g8),
        _gate("G9", "→ 运营", "pending"),
        _gate("G10", "→ 维护", "pending"),
        _gate("G11", "→ 下一轮", "pending"),
    ]


def _router_lightweight_gates():
    """lightweight/7 gate table (router style): FIRST「发布」row is G5
    (CI→发布); G6 (发布→运营) also contains 「发布」 but is not the
    release gate — row-order derivation must pick G5."""
    return [
        _gate("G1", "立项→调研", "passed-on-entry", "2026-08-18", "EV-001"),
        _gate("G2", "调研+选型→设计", "passed-on-entry", "2026-08-18", "EV-001"),
        _gate("G3", "设计→开发", "passed-on-entry", "2026-08-18", "EV-001"),
        _gate("G4", "开发+测试→CI", "pending"),
        _gate("G5", "CI→发布", "pending"),
        _gate("G6", "发布→运营", "pending"),
        _gate("G7", "运营→维护", "pending"),
    ]


def _tag(name, date):
    return {"tag": name, "date": date}


# ── Signal table: G-s2 (pending) / G-s1 (dates) / G-s3 (no tag) ─────────

class Check37SignalTableTests(unittest.TestCase):
    """Rule table fixtures over injectable gate rows + published tags."""

    def test_g_s2_tv_style_pending_gate_with_tag_fails(self):
        """Design #1: standard — G6/G7 pending + tag v1.6.3 → FAIL (G-s2,
        conservative: ordering unprovable)."""
        r = vw.check_gate_sequence_for_release(
            gates=_tv_standard_gates(),
            published_tags=[_tag("v1.6.3", "2026-08-25")])
        self.assertEqual(r["verdict"], "FAIL")
        self.assertEqual([v["rule"] for v in r["violations"]], ["G-s2"])
        v = r["violations"][0]
        self.assertEqual(v["tag"], "v1.6.3")
        self.assertIn("G6", v["pending_gates"])
        self.assertIn("G7", v["pending_gates"])
        self.assertEqual(r["stats"]["release_gate"], "G8")
        self.assertEqual(r["stats"]["prerelease_pending"], 2)
        self.assertEqual(r["stats"]["latest_tag"], "v1.6.3")

    def test_g_s2_router_lightweight_fails(self):
        """Design #2: lightweight — G4 pending + tag v0.2.1 → FAIL; the
        release gate derives to G5 (first「发布」row), NOT G6."""
        r = vw.check_gate_sequence_for_release(
            gates=_router_lightweight_gates(),
            published_tags=[_tag("v0.2.1", "2026-08-25")])
        self.assertEqual(r["verdict"], "FAIL")
        self.assertEqual(r["violations"][0]["rule"], "G-s2")
        self.assertEqual(r["stats"]["release_gate"], "G5")
        self.assertEqual(r["stats"]["release_gate_transition"], "CI→发布")
        self.assertEqual(r["stats"]["prerelease_gates"], 4)
        self.assertEqual(r["stats"]["prerelease_pending"], 1)

    def test_g_s2_released_mode_warns_not_fails(self):
        """History exemption (DEC-153 ②): the SAME tv-style fixture in
        released mode → WARN disclosure, no FAIL violation."""
        r = vw.check_gate_sequence_for_release(
            gates=_tv_standard_gates(),
            published_tags=[_tag("v1.6.3", "2026-08-25")],
            lineage_mode="released")
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["violations"], [])
        self.assertEqual([w["rule"] for w in r["warnings"]], ["G-s2"])
        self.assertIn("released mode", r["warnings"][0]["reason"])
        self.assertEqual(r["stats"]["lineage_mode"], "released")

    def test_g_s1_tag_predates_passed_gate_fails(self):
        """Design G-s1 (dates): G6 passed 2026-08-20, tag released
        2026-08-10 → the release happened BEFORE the gate passed (bypass)."""
        gates = _tv_standard_gates(g6="passed", g7="passed",
                                   g8="pending")
        gates[5]["date"] = "2026-08-20"   # G6 passed date
        gates[6]["date"] = "2026-08-21"   # G7 passed date
        r = vw.check_gate_sequence_for_release(
            gates=gates,
            published_tags=[_tag("v1.6.3", "2026-08-10")])
        self.assertEqual(r["verdict"], "FAIL")
        self.assertEqual(r["violations"][0]["rule"], "G-s1")
        self.assertEqual(r["stats"]["prerelease_pending"], 0)
        self.assertEqual(r["stats"]["prerelease_passed"], 2)

    def test_g_s1_tag_after_passed_gate_passes(self):
        """G-s1 compliance: tag released 2026-08-25, gates passed
        2026-08-20/21 → gates passed BEFORE the release → PASS."""
        gates = _tv_standard_gates(g6="passed", g7="passed",
                                   g8="pending")
        gates[5]["date"] = "2026-08-20"
        gates[6]["date"] = "2026-08-21"
        r = vw.check_gate_sequence_for_release(
            gates=gates,
            published_tags=[_tag("v1.6.3", "2026-08-25")])
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["warnings"], [])

    def test_g_s1_passed_without_date_conservative_fails(self):
        """Passed gate with NO date + tag: ordering unprovable → the
        strong interlock (DEC-153 ④) requires proof of pass-before-release,
        so the absence of a date is NOT a pass; conservative FAIL (candidate)."""
        gates = _tv_standard_gates(g6="passed", g7="passed-on-entry")
        r = vw.check_gate_sequence_for_release(
            gates=gates,
            published_tags=[_tag("v1.6.3", "2026-08-25")])
        self.assertEqual(r["verdict"], "FAIL")
        self.assertEqual(r["violations"][0]["rule"], "G-s1")

    def test_g_s1_released_mode_warns_not_fails(self):
        """G-s1 history disclosure: same predate fixture in released mode
        → WARN, never FAIL (DEC-153 ②)."""
        gates = _tv_standard_gates(g6="passed", g7="passed",
                                   g8="pending")
        gates[5]["date"] = "2026-08-20"
        gates[6]["date"] = "2026-08-21"
        r = vw.check_gate_sequence_for_release(
            gates=gates,
            published_tags=[_tag("v1.6.3", "2026-08-10")],
            lineage_mode="released")
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["violations"], [])
        self.assertEqual([w["rule"] for w in r["warnings"]], ["G-s1"])

    def test_g_s3_git_unavailable_warns(self):
        """Design #4 / git-unavailable degradation: no published tag from
        git (None) + release gate declared passed + pending prerelease →
        G-s3 WARN (fail-safe, never FAIL); the release-gate-passed claim is
        disclosed instead."""
        gates = _tv_standard_gates(g6="pending", g7="pending",
                                   g8="passed")
        with mock.patch.object(gd, "_git_published_tags",
                               return_value=None):
            r = vw.check_gate_sequence_for_release(gates=gates)
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["violations"], [])
        self.assertEqual([w["rule"] for w in r["warnings"]], ["G-s3"])
        self.assertEqual(r["stats"]["git_available"], False)

    def test_no_tag_and_release_gate_pending_passes(self):
        """Design 误报面: no git tag AND gate table self-consistent (release
        gate pending) → PASS — no release action to interlock."""
        r = vw.check_gate_sequence_for_release(
            gates=_tv_standard_gates(),
            published_tags=[])
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["warnings"], [])

    def test_no_tag_all_prerelease_clean_passes(self):
        """Design #3: all prereleases passed (no pending, no tag) → PASS."""
        gates = _tv_standard_gates(g6="passed", g7="passed", g8="pending")
        gates[5]["date"] = "2026-08-20"
        gates[6]["date"] = "2026-08-21"
        r = vw.check_gate_sequence_for_release(
            gates=gates, published_tags=[])
        self.assertEqual(r["verdict"], "PASS")

    def test_s3_warn_upgrades_to_s2_fail_with_tag(self):
        """Design #8 (progressive pair): same gate table without a tag
        (git-blind) → G-s3 WARN; after a tag appears → G-s2 FAIL."""
        gates = _tv_standard_gates(g6="pending", g7="pending",
                                   g8="passed")
        with mock.patch.object(gd, "_git_published_tags",
                               return_value=None):
            r1 = vw.check_gate_sequence_for_release(gates=gates)
        self.assertEqual(r1["verdict"], "WARN")
        self.assertEqual(r1["warnings"][0]["rule"], "G-s3")
        r2 = vw.check_gate_sequence_for_release(
            gates=gates, published_tags=[_tag("v1.6.3", "2026-08-25")],
            lineage_mode="candidate")
        self.assertEqual(r2["verdict"], "FAIL")
        self.assertEqual(r2["violations"][0]["rule"], "G-s2")


# ── passed-on-entry exemption (DEC-153 ④) ──────────────────────────────

class Check37OnEntryExemptionTests(unittest.TestCase):
    """on-entry onboarding carries no real timeline — no interlock claim."""

    def test_all_on_entry_with_tag_passes(self):
        """Design #5: ALL prereleases passed-on-entry + published tag →
        PASS (the repo's own dogfood gate table shape: G1-G7 on-entry,
        v0.75.0 released — must never FAIL the self-check)."""
        r = vw.check_gate_sequence_for_release(
            gates=_tv_standard_gates(g6="passed-on-entry",
                                     g7="passed-on-entry",
                                     g8="passed-on-entry"),
            published_tags=[_tag("v0.75.0", "2026-08-21")])
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["stats"]["prerelease_on_entry"], 7)

    def test_mixed_passed_and_on_entry_judged_on_passed_only(self):
        """Mix: G6 passed (date < tag) + G7 on-entry + tag → PASS — the
        on-entry rows are ignored; only the passed row is interlocked."""
        gates = _tv_standard_gates(g6="passed", g7="passed-on-entry")
        gates[5]["date"] = "2026-08-20"
        r = vw.check_gate_sequence_for_release(
            gates=gates,
            published_tags=[_tag("v1.6.3", "2026-08-25")])
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["stats"]["prerelease_passed"], 1)
        self.assertEqual(r["stats"]["prerelease_on_entry"], 6)

    def test_backticked_status_cells_normalized(self):
        """tv-style markdown emphasis (`` `passed-on-entry` `` / `` `pending` ``)
        is stripped before classification — an on-entry gate must never be
        misread as pending (live tv fixture shape)."""
        gates = _tv_standard_gates(g6="`pending`", g7="`pending`",
                                   g8="`pending`",
                                   on_entry="`passed-on-entry`")
        r = vw.check_gate_sequence_for_release(
            gates=gates,
            published_tags=[_tag("v1.6.3", "2026-08-23")])
        self.assertEqual(r["verdict"], "FAIL")           # G6/G7 pending → G-s2
        self.assertEqual(r["violations"][0]["rule"], "G-s2")
        self.assertEqual(r["stats"]["prerelease_on_entry"], 5)
        self.assertEqual(r["stats"]["prerelease_pending"], 2)
        r2 = vw.check_gate_sequence_for_release(
            gates=gates, published_tags=[])
        self.assertEqual(r2["stats"]["prerelease_on_entry"], 5)


# ── Multiple tags: latest candidate only ────────────────────────────────

class Check37LatestTagTests(unittest.TestCase):
    """Design 误报面: multiple version tags judge ONLY the latest candidate."""

    def test_latest_semver_tag_is_judged(self):
        """v1.6.0 (old) and v1.6.3 (latest): stats expose v1.6.3."""
        gates = _tv_standard_gates(g6="passed", g7="passed", g8="pending")
        gates[5]["date"] = "2026-08-12"
        gates[6]["date"] = "2026-08-13"
        r = vw.check_gate_sequence_for_release(
            gates=gates,
            published_tags=[_tag("v1.5.0", "2026-08-01"),
                            _tag("v1.6.3", "2026-08-15")])
        # v1.6.3 (08-15) is on/after the passed dates (08-12/13) → PASS;
        # the OLD v1.6.0-style tag would have failed — it is not judged.
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["stats"]["latest_tag"], "v1.6.3")

    def test_v_prefix_and_bare_semver_normalized(self):
        """Both ``vX.Y.Z`` and ``X.Y.Z`` shapes are accepted; the highest
        semver wins regardless of prefix."""
        gates = _tv_standard_gates(g6="pending", g7="pending", g8="pending")
        r = vw.check_gate_sequence_for_release(
            gates=gates,
            published_tags=[_tag("v0.9.9", "2026-01-01"),
                            _tag("1.0.0", "2026-02-01")])
        self.assertEqual(r["stats"]["latest_tag"], "1.0.0")
        self.assertEqual(r["verdict"], "FAIL")  # pending gates + tag


# ── Row-order derivation (DEC-153 ①) ───────────────────────────────────

class Check37RowOrderTests(unittest.TestCase):
    """standard/11 and lightweight/7 derive the release gate by row order."""

    def test_standard_11_derives_g8(self):
        r = vw.check_gate_sequence_for_release(
            gates=_tv_standard_gates(g6="passed", g7="passed", g8="pending"),
            published_tags=[])
        self.assertEqual(r["stats"]["release_gate"], "G8")
        self.assertEqual(r["stats"]["prerelease_gates"], 7)
        self.assertIn("G8", r["reason"])

    def test_lightweight_7_derives_g5_not_g6(self):
        """Router table: G5 (CI→发布) is the release gate; G6 (发布→运营)
        also contains「发布」 but sits AFTER G5 and must not be chosen."""
        r = vw.check_gate_sequence_for_release(
            gates=_router_lightweight_gates(), published_tags=[])
        self.assertEqual(r["stats"]["release_gate"], "G5")
        self.assertEqual(r["stats"]["prerelease_gates"], 4)

    def test_strict_and_standard_share_the_11_row_judgement(self):
        """Design #7: strict(11) and standard(11) run the same row-order
        judgement; profile records in stats only, never hard-codes ids."""
        gates = _tv_standard_gates(g6="pending", g7="pending", g8="pending")
        r1 = vw.check_gate_sequence_for_release(
            gates=gates, published_tags=[_tag("v1.6.3", "2026-08-25")],
            profile="standard")
        r2 = vw.check_gate_sequence_for_release(
            gates=gates, published_tags=[_tag("v1.6.3", "2026-08-25")],
            profile="strict")
        self.assertEqual(r1["verdict"], r2["verdict"])
        self.assertEqual(r1["stats"]["profile"], "standard")
        self.assertEqual(r2["stats"]["profile"], "strict")
        self.assertEqual(r1["violations"][0]["rule"],
                         r2["violations"][0]["rule"])

    def test_no_release_gate_no_verdict(self):
        """No「发布」transition row → no-verdict (nothing to interlock)."""
        gates = [_gate("G1", "→ 调研", "passed"),
                 _gate("G2", "→ 技术选型", "passed")]
        r = vw.check_gate_sequence_for_release(
            gates=gates, published_tags=[_tag("v1.0.0", "2026-08-25")])
        self.assertEqual(r["verdict"], "no-verdict")
        self.assertEqual(r["violations"], [])

    def test_no_prerelease_gates_passes(self):
        """Release gate is the FIRST row → no prereleases → PASS."""
        gates = [_gate("G1", "→ 版本发布", "passed"),
                 _gate("G2", "→ 运营", "pending")]
        r = vw.check_gate_sequence_for_release(
            gates=gates, published_tags=[_tag("v1.0.0", "2026-08-25")])
        self.assertEqual(r["verdict"], "PASS")


# ── BR-4 wiring: released_history_version + embedded call ───────────────

class Check37Br4WiringTests(unittest.TestCase):
    """BR-4 / DEC-153 ②③: already-published version checks run the gate
    interlock in released mode (WARN), never mis-FAIL history."""

    ROADMAP = (
        "## 版本规划\n\n"
        "| 版本 | 状态 | 预计日期 |\n"
        "| --- | --- | --- |\n"
        "| 0.74.0 | 已发布 | 2026-08-21 |\n"
        "| 0.76.0 | 规划 | 2026-08-22 |\n"
    )

    def _write_roadmap(self, text):
        td = tempfile.TemporaryDirectory()
        gov = Path(td.name) / ".governance"
        gov.mkdir()
        tracker = gov / "plan-tracker.md"
        tracker.write_text(text, encoding="utf-8")
        return td, tracker

    def test_released_history_version_true_for_published(self):
        td, tracker = self._write_roadmap(self.ROADMAP)
        try:
            with mock.patch.object(vw, "SAMPLE_PATH", tracker):
                self.assertTrue(vw.released_history_version("0.74.0"))
        finally:
            td.cleanup()

    def test_released_history_version_false_for_planned(self):
        td, tracker = self._write_roadmap(self.ROADMAP)
        try:
            with mock.patch.object(vw, "SAMPLE_PATH", tracker):
                self.assertFalse(vw.released_history_version("0.76.0"))
                self.assertFalse(vw.released_history_version("9.9.9"))
        finally:
            td.cleanup()

    def test_released_history_version_withdrawn_status_true(self):
        td, tracker = self._write_roadmap(
            "## 版本规划\n\n"
            "| 版本 | 状态 | 预计日期 |\n"
            "| --- | --- | --- |\n"
            "| 0.54.2 | 已撤回/失效 | 2026-06-01 |\n")
        try:
            with mock.patch.object(vw, "SAMPLE_PATH", tracker):
                self.assertTrue(vw.released_history_version("0.54.2"))
        finally:
            td.cleanup()

    def test_released_history_version_degrades_false(self):
        """Parse failure / missing file / non-str → False (fail-safe:
        candidate stays the default — BR-4 never turns a hiccup into a
        verdict change)."""
        with mock.patch.object(vw, "SAMPLE_PATH",
                               Path("Z:/missing/plan-tracker.md")):
            self.assertFalse(vw.released_history_version("0.74.0"))
        self.assertFalse(vw.released_history_version(None))
        self.assertFalse(vw.released_history_version(""))
        self.assertFalse(vw.released_history_version(12345))

    def test_embedded_call_uses_lineage_mode_by_default(self):
        """check_release_readiness forwards lineage_mode to the embedded
        gate check when gate_sequence_lineage_mode is not given."""
        with mock.patch.object(vw, "check_gate_sequence_for_release",
                               return_value={"verdict": "PASS", "reason": "",
                                             "violations": [], "warnings": [],
                                             "stats": {"lineage_mode": "candidate",
                                                       "latest_tag": None,
                                                       "prerelease_pending": 0}}
                               ) as m_gs:
            vw.check_release_readiness(lineage_mode="candidate")
        self.assertEqual(m_gs.call_args.kwargs["lineage_mode"], "candidate")

    def test_embedded_call_respects_gate_sequence_lineage_mode(self):
        """Explicit gate_sequence_lineage_mode (BR-4 path) overrides the
        run's lineage_mode for the embedded gate check only."""
        with mock.patch.object(vw, "check_gate_sequence_for_release",
                               return_value={"verdict": "PASS", "reason": "",
                                             "violations": [], "warnings": [],
                                             "stats": {"lineage_mode": "released",
                                                       "latest_tag": None,
                                                       "prerelease_pending": 0}}
                               ) as m_gs:
            vw.check_release_readiness(
                lineage_mode="candidate",
                gate_sequence_lineage_mode="released")
        self.assertEqual(m_gs.call_args.kwargs["lineage_mode"], "released")

    def test_embedded_gate_fail_counts_into_issues(self):
        """Gate-sequence violations surface as release issues (so the
        release check FAILs on a candidate bypass), while WARNs surface in
        details only (no new FAIL surface for history disclosure)."""
        gate_result = {
            "verdict": "FAIL", "reason": "bypass",
            "violations": [{"rule": "G-s2", "reason": "tag v1.6.3 bypassed G6"}],
            "warnings": [],
            "stats": {"lineage_mode": "candidate", "latest_tag": "v1.6.3",
                      "prerelease_pending": 1},
        }
        with mock.patch.object(vw, "check_gate_sequence_for_release",
                               return_value=gate_result):
            r = vw.check_release_readiness()
        self.assertTrue(any("gate sequence:" in i for i in r["issues"]))
        # The details block carries the structured verdict for the CLI.
        self.assertEqual(r["details"]["gate_sequence_for_release"]["verdict"],
                         "FAIL")
        self.assertFalse(r["details"]["gate_sequence_for_release"]["pass"])

    def test_cmd_check_release_auto_released_for_published_version(self):
        """BR-4: no --lineage-mode + roadmap-published --version → the gate
        interlock gets "released" while the lineage check stays candidate."""
        import argparse
        with mock.patch.object(vw, "check_release_readiness",
                               return_value={"details": {}, "issues": [],
                                             "pass": True}) as m_rr, \
             mock.patch.object(vw, "released_history_version",
                               return_value=True), \
             mock.patch.object(vw, "scan_loop_runtime_claims",
                               return_value=None), \
             mock.patch.object(vw, "_loop_runtime_claim_gate_detail",
                               return_value={"issues": [], "pass": True}), \
             mock.patch.object(vw.sys, "exit"):
            args = argparse.Namespace(
                version="0.74.0", lineage_mode=None,
                skip_execution_gates=False, runtime_adapters=False,
                release_commit=None, lineage_remote="origin")
            vw.cmd_check_release(args)
        kwargs = m_rr.call_args.kwargs
        self.assertEqual(kwargs["lineage_mode"], "candidate")
        self.assertEqual(kwargs["gate_sequence_lineage_mode"], "released")

    def test_cmd_check_release_explicit_released_passthrough(self):
        """Explicit --lineage-mode released always wins (no auto probe)."""
        import argparse
        with mock.patch.object(vw, "check_release_readiness",
                               return_value={"details": {}, "issues": [],
                                             "pass": True}) as m_rr, \
             mock.patch.object(vw, "released_history_version",
                               return_value=False), \
             mock.patch.object(vw, "scan_loop_runtime_claims",
                               return_value=None), \
             mock.patch.object(vw, "_loop_runtime_claim_gate_detail",
                               return_value={"issues": [], "pass": True}), \
             mock.patch.object(vw.sys, "exit"):
            args = argparse.Namespace(
                version="0.74.0", lineage_mode="released",
                skip_execution_gates=False, runtime_adapters=False,
                release_commit="abc123", lineage_remote="origin")
            vw.cmd_check_release(args)
        kwargs = m_rr.call_args.kwargs
        self.assertEqual(kwargs["lineage_mode"], "released")
        self.assertEqual(kwargs["gate_sequence_lineage_mode"], "released")


# ── Live mode: git facts root = HOST_PROJECT_ROOT (FIX-270) ─────────────

class Check37LiveModeTests(unittest.TestCase):
    """Live tags come from the host facts root; git unavailable → None."""

    def test_live_tags_resolved_from_host_project_root(self):
        """The git facts root passed to _git_published_tags is
        HOST_PROJECT_ROOT (FIX-270 mixed-root semantics — never ROOT)."""
        tags = [_tag("v1.6.3", "2026-08-25")]
        gates = _tv_standard_gates(g6="passed", g7="passed", g8="pending")
        gates[5]["date"] = "2026-08-20"
        gates[6]["date"] = "2026-08-21"
        with mock.patch.object(gd, "_git_published_tags",
                               return_value=tags) as m_git:
            r = vw.check_gate_sequence_for_release(gates=gates)
        # Live injection: no published_tags arg → the check reaches git
        # through _git_published_tags(HOST_PROJECT_ROOT) and judges PASS
        # (v1.6.3 after 08-20/21 passed dates).
        self.assertEqual(m_git.call_args.args[0], vw.HOST_PROJECT_ROOT)
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["stats"]["latest_tag"], "v1.6.3")

    def test_git_unavailable_returns_none(self):
        """No .git → None (caller degrades to G-s3 fail-safe WARN)."""
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(gd._git_published_tags(Path(td)))
        self.assertIsNone(gd._git_published_tags(None))

    def test_live_runs_on_dogfood_shapes_pass(self):
        """Dogfood self-check shape: G1-G7 on-entry + G8 on-entry + real
        repo tags → PASS (the repo has v0.75.0 and an all-on-entry table)."""
        r = vw.check_gate_sequence_for_release(
            gates=_tv_standard_gates(g6="passed-on-entry",
                                     g7="passed-on-entry",
                                     g8="passed-on-entry"),
            published_tags=[_tag("v0.75.0", "2026-08-21")])
        self.assertEqual(r["verdict"], "PASS")


# ── Contract: shape, never-raise, numbering, export ─────────────────────

class Check37ContractTests(unittest.TestCase):
    """Result shape, never-raise contract, numbering (F9), domain export."""

    def test_result_contract_shape(self):
        r = vw.check_gate_sequence_for_release(
            gates=_tv_standard_gates(),
            published_tags=[_tag("v1.6.3", "2026-08-25")])
        self.assertEqual(
            set(r.keys()),
            {"verdict", "reason", "violations", "warnings", "stats"})
        self.assertIn(r["verdict"], ("PASS", "WARN", "FAIL", "no-verdict"))
        for key in ("gates_scanned", "release_gate", "prerelease_gates",
                    "prerelease_passed", "prerelease_on_entry",
                    "prerelease_pending", "latest_tag", "latest_tag_date",
                    "lineage_mode", "warn_count", "violation_count"):
            self.assertIn(key, r["stats"], f"stats.{key} missing")

    def test_never_raises_on_garbage_inputs(self):
        """Never raise: garbage gates, ragged rows, bad statuses, odd tag
        shapes, None injections — every path returns the contract dict."""
        with mock.patch.object(gd, "_git_published_tags", return_value=None):
            cases = [
                dict(gates=None, published_tags=None),
                dict(gates=None, published_tags=[]),
                dict(gates=None, published_tags=["not-a-version"]),
                dict(gates="not-a-list"),
                dict(gates=12345),
                dict(gates=[], published_tags=[_tag("v1.0.0", "2026-08-01")]),
                dict(gates=[{"gate": "G1"}], published_tags=[]),
                dict(gates=[_gate("G1", "→ 版本发布", "passed", "bad-date")],
                     published_tags=[_tag("v1.0.0", "not-a-date")]),
                dict(gates=[_gate("G1", "→ 版本发布", "passed")],
                     published_tags=["v1.0.0"]),
                dict(gates=_tv_standard_gates(), published_tags=None,
                     lineage_mode="bogus-mode"),
                dict(gates=_tv_standard_gates(), published_tags=[12345]),
                dict(gates=_tv_standard_gates(),
                     published_tags=[{"tag": None, "date": None}]),
            ]
            for kwargs in cases:
                r = vw.check_gate_sequence_for_release(**kwargs)
                self.assertIn(
                    r["verdict"], ("PASS", "WARN", "FAIL", "no-verdict"),
                    f"kwargs={kwargs!r} -> {r['verdict']}")
                self.assertIsInstance(r["violations"], list)
                self.assertIsInstance(r["warnings"], list)

    def test_missing_plan_tracker_degrades_no_verdict(self):
        """P2-1 (review-FIX-266-CODE-R0): gates=None live read of a MISSING
        host plan-tracker must not raise (parse_gate_status has no is_file
        guard) — fail-safe no-verdict with a plan-tracker-not-found reason
        (risk_domain.py:385-392 precedent)."""
        with mock.patch.object(vw, "SAMPLE_PATH",
                               Path("Z:/missing/plan-tracker.md")), \
             mock.patch.object(gd, "_git_published_tags", return_value=None):
            r = vw.check_gate_sequence_for_release()
        self.assertEqual(r["verdict"], "no-verdict")
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["stats"]["gates_scanned"], 0)
        self.assertIn("plan-tracker.md not found", r["reason"])

    def test_unreadable_plan_tracker_degrades_no_verdict(self):
        """P2-1 hardening: the live read branch also degrades when
        parse_gate_status raises (unreadable/decode error — UnicodeError
        is a ValueError subclass the IOError/OSError guard must be paired
        with; snapshot_domain P1-1 lesson)."""
        with tempfile.TemporaryDirectory() as td:
            tracker = Path(td) / "plan-tracker.md"
            tracker.write_text("# host\n", encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(vw, "parse_gate_status",
                                   side_effect=OSError("boom")), \
                 mock.patch.object(gd, "_git_published_tags",
                                   return_value=None):
                r = vw.check_gate_sequence_for_release(
                    published_tags=[_tag("v1.0.0", "2026-08-01")])
        self.assertEqual(r["verdict"], "no-verdict")
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["warnings"], [])
        self.assertIn("unreadable", r["reason"])

    def test_check37_block_position_and_numbering(self):
        """Check 37 block exists, numbered, between Check 36 and the summary."""
        src = (_INFRA_DIR / "verify_workflow.py").read_text(encoding="utf-8")
        block37 = "┌─ Check 37: Gate Sequence for Release (FIX-266)"
        self.assertIn(block37, src)
        self.assertLess(src.index("┌─ Check 36: Risk Mitigation Closure"),
                        src.index(block37))
        self.assertLess(src.index(block37),
                        src.index("┌─ Governance Health Summary"))

    def test_check37_exported_and_function_lives_in_gate_domain(self):
        domain = (_INFRA_DIR / "checks" / "gate_domain.py").read_text(
            encoding="utf-8")
        self.assertIn("def check_gate_sequence_for_release", domain)
        self.assertIn("def released_history_version", domain)
        self.assertIn("def _git_published_tags", domain)
        self.assertTrue(hasattr(vw, "check_gate_sequence_for_release"))
        self.assertTrue(hasattr(vw, "released_history_version"))

    def test_check37_import_export_placed_with_domain_imports(self):
        src = (_INFRA_DIR / "verify_workflow.py").read_text(encoding="utf-8")
        self.assertIn("from checks.gate_domain import (", src)
        idx_import = src.index("from checks.gate_domain import (")
        idx_block = src.index("┌─ Check 37")
        self.assertLess(idx_import, idx_block)

    def test_check36_37_35_no_interleaving(self):
        """Check 35 / 36 / 37 blocks appear in ascending order with no
        interleaving (each block ends before the next begins)."""
        src = (_INFRA_DIR / "verify_workflow.py").read_text(encoding="utf-8")
        markers = ["┌─ Check 35: Snapshot Freshness",
                   "┌─ Check 36: Risk Mitigation Closure",
                   "┌─ Check 37: Gate Sequence for Release"]
        idx = [src.index(m) for m in markers]
        self.assertEqual(idx, sorted(idx), "Check 35/36/37 out of order")


# ── FIX-278 G2 (L-C): released-history exemption in candidate mode ─────

class Check37LegacyReleasedHistoryTests(unittest.TestCase):
    """FIX-278 G2 (L-C): a published tag whose roadmap version row names a
    terminal release state is a HISTORY FACT — audit-148 §3.1 router v0.2.1
    tag exists while G4 pending (接入前发布旁路). In health-side (candidate)
    mode it is WARN-disclosed (DEC-153 ② semantics), never a retroactive
    FAIL; an UNRELEASED roadmap row keeps candidate semantics (FAIL)."""

    _ROUTER_ROADMAP = (
        "## 版本规划\n\n"
        "| 版本 | 状态 | 预计日期 |\n"
        "| --- | --- | --- |\n"
        "| **v0.2.1** | **已发布（2026-08-22，REL-001）** | 2026-08-22 |\n"
        "| **v0.3.0** | **规划中** | 待定 |\n"
    )
    _ROUTER_ROADMAP_UNRELEASED = _ROUTER_ROADMAP.replace(
        "已发布（2026-08-22，REL-001）", "规划中（DEC-020 定稿）")

    def _run_with_roadmap(self, roadmap, tag="v0.2.1"):
        with tempfile.TemporaryDirectory() as td:
            tracker = Path(td) / "plan-tracker.md"
            tracker.write_text(roadmap, encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", tracker):
                return vw.check_gate_sequence_for_release(
                    gates=_router_lightweight_gates(),
                    published_tags=[_tag(tag, "2026-08-22")])

    def test_released_roadmap_version_exempts_g_s2(self):
        """v0.2.1 已发布（router 实况）+ G4 pending → WARN 披露（L-C 豁免），
        released_history_exempt=True，零违规。"""
        r = self._run_with_roadmap(self._ROUTER_ROADMAP)
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["violations"], [])
        self.assertEqual([w["rule"] for w in r["warnings"]], ["G-s2"])
        self.assertTrue(r["stats"]["released_history_exempt"])
        self.assertIn("historical", r["reason"])

    def test_unreleased_roadmap_version_stays_fail(self):
        """v0.2.1 规划中 → 保持 candidate FAIL（L-C fail-closed 边界）。"""
        r = self._run_with_roadmap(self._ROUTER_ROADMAP_UNRELEASED)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertEqual(r["violations"][0]["rule"], "G-s2")
        self.assertFalse(r["stats"]["released_history_exempt"])

    def test_bare_roadmap_row_still_matches_v_prefix_tag(self):
        """roadmap 行不带 v 前缀（0.2.1）仍匹配 v 前缀 tag（v0.2.1）——
        编辑器风格差异不改变 History 判定。"""
        roadmap = self._ROUTER_ROADMAP.replace("**v0.2.1**", "**0.2.1**")
        r = self._run_with_roadmap(roadmap)
        self.assertEqual(r["verdict"], "WARN")
        self.assertTrue(r["stats"]["released_history_exempt"])

    def test_lc_probe_is_guarded_not_except_swallowed(self):
        """P2-2（源守卫回归）：``released_history_version(latest["tag"])`` 必须
        置于显式 ``latest is not None`` 守卫之下，且不得用 try/except 包裹
        （该函数自身 Never-raises——若调用时抛错，那一定是真实 bug，不可被
        异常吞没；latest=None 路径是普通 ``is not None`` 防护，P3-5 冗余
        防御一并消除）。行为侧：无 tag → verdict PASS 且 released_history_exempt
        =False。"""
        src = (_INFRA_DIR / "checks" / "gate_domain.py").read_text(
            encoding="utf-8")
        call_idx = src.index("released_history_version(latest")
        window = src[max(0, call_idx - 300):call_idx + 40]
        self.assertIn("if latest is not None:", window,
                      "probe must be guarded by latest-is-not-None")
        self.assertIn("history_exempt = False", window)
        self.assertTrue(
            window.rindex("if latest is not None:") < call_idx,
            "guard must precede the dereference")
        # Behavior: no tag → candidate PASS, no exemption.
        r = vw.check_gate_sequence_for_release(
            gates=_tv_standard_gates(), published_tags=[])
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["stats"]["released_history_exempt"], False)


if __name__ == "__main__":
    unittest.main()
