"""FIX-268 / REQ-145.2 — Check 35 snapshot-freshness tests (red→green).

Deliverable under test (design audit-145-watchdog-design-0.76.0.md §3.2,
test plan §5.1 — 10 cases, plus acceptance-item extras):

1. ``check_snapshot_freshness(plan_content=None, snapshot_text=None,
   evidence_mtime=None, commit_date=None)`` in
   ``infra/checks/snapshot_domain.py``: signal table S1a (unparseable
   session_date → WARN) / S1b (snapshot < latest .governance/ commit →
   WARN, gradual) / S1c (AND double threshold age ≥ 7d AND lag ≥ 10 commits
   → FAIL) / S1d (no snapshot → no-verdict); result contract
   ``{verdict, reason, violations, warnings, stats}``, verdict ∈
   PASS / WARN / FAIL / no-verdict, NEVER raises.
2. Baseline semantics: latest ``.governance/`` commit date from the host
   git (FIX-270 facts root); untracked/unversioned ``.governance/`` →
   secondary plan-tracker/evidence-log mtime baseline (fail-safe WARN;
   FAIL impossible); snapshot predating the ``.governance/`` history
   (adoption edge) → WARN, never FAIL; multi-snapshot text judges the
   LATEST ``session_date`` only (parallel-session 误报面 ③).
3. Consistency: the ``**session_date**`` regex used here is the proven
   ``FIX_105_SNAPSHOT_DATE_RE`` — declared identical mirror of
   resolve_entry.py ``_SNAPSHOT_DATE_RE``; the test pins the equality.
4. Numbering (F9): Check 35 block sits between Check 34 and Check 36 in
   ``cmd_check_governance``; FIX-265's ``test_check36`` F-9 assertion is
   updated (see test_risk_mitigation_closure.py).
5. Orthogonality: Check 28c (vs latest published release) / Check 34
   (recommendation closure) / Check 35 (vs latest governance commit) —
   same-frame triggers stay independent, no swallowing (design §5.1 #10).

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_snapshot_freshness.py -v
"""

import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import resolve_entry  # noqa: E402
import verify_workflow as vw  # noqa: E402
from checks import snapshot_domain as sd  # noqa: E402


# ── Fixtures ────────────────────────────────────────────────────────────

def _snap(session_date="2026-08-23", extra=""):
    return (
        "# 会话快照\n\n"
        "- **session_id**: 20260823-test-session\n"
        "- **session_date**: {0}\n"
        "- **agent**: test\n\n"
        "## 当前状态\n\n{1}".format(session_date, extra)
    )


_ISO = date.today().isoformat()


def _iso(d):
    return d.isoformat()


# ── Signal table: S1a / S1b / S1c / S1d ────────────────────────────────

class Check35SignalTableTests(unittest.TestCase):
    """Rule table fixtures over injectable snapshot text + git facts."""

    def test_s1b_snapshot_older_than_commit_warns(self):
        """Design #1: session_date < latest .governance/ commit → WARN (S1b),
        gradual start — never FAIL on the single axis alone."""
        r = vw.check_snapshot_freshness(
            snapshot_text=_snap("2026-08-01"), commit_date="2026-08-10")
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["violations"], [])
        w = [x for x in r["warnings"] if x["rule"] == "S1b"]
        self.assertEqual(len(w), 1)
        self.assertEqual(w[0]["session_date"], "2026-08-01")
        self.assertEqual(w[0]["commit_date"], "2026-08-10")
        self.assertEqual(r["stats"]["baseline_kind"], "git")

    def test_s1c_fail_both_thresholds(self):
        """Design #2: (age ≥ 7d AND lag ≥ 10 commits) → FAIL (S1c, AND)."""
        snapshot_dt = date.today() - timedelta(days=20)
        # History predates the snapshot (today-30), then 12 .governance/
        # commits dated AFTER the snapshot (today-15 … today-4).
        dates = ([date.today() - timedelta(days=30)]
                 + [date.today() - timedelta(days=15 - i) for i in range(12)])
        with mock.patch.object(sd, "_git_governance_facts",
                               return_value={"tracked": True, "dates": dates}):
            r = vw.check_snapshot_freshness(snapshot_text=_snap(_iso(snapshot_dt)))
        self.assertEqual(r["verdict"], "FAIL")
        self.assertEqual(len(r["violations"]), 1)
        v = r["violations"][0]
        self.assertEqual(v["rule"], "S1c")
        self.assertEqual(v["lag_commits"], 12)
        self.assertEqual(v["age_days"], 20)
        self.assertEqual(r["stats"]["lag_commits"], 12)
        # Reason carries the AND thresholds + the measured facts.
        self.assertIn("≥ 7", v["reason"])
        self.assertIn("≥ 10", v["reason"])

    def test_pass_snapshot_equal_commit(self):
        """Design #3: session_date == latest commit date → PASS."""
        r = vw.check_snapshot_freshness(
            snapshot_text=_snap("2026-08-23"), commit_date="2026-08-23")
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["stats"]["commit_date"], "2026-08-23")

    def test_pass_snapshot_newer_than_commit(self):
        """session_date > latest commit date (fresh) → PASS."""
        r = vw.check_snapshot_freshness(
            snapshot_text=_snap("2026-08-23"), commit_date="2026-08-21")
        self.assertEqual(r["verdict"], "PASS")

    def test_s1a_missing_session_date_warns(self):
        """Design #4: snapshot exists but session_date missing/unparseable
        → WARN (fail-safe; format drift must never FAIL)."""
        for text in ("# 会话快照\n\n- **session_id**: 20260823-x\n",
                     _snap().replace("2026-08-23", "2026-99-99")):
            r = vw.check_snapshot_freshness(snapshot_text=text)
            self.assertEqual(r["verdict"], "WARN", f"text={text!r}")
            self.assertEqual(r["violations"], [])
            self.assertEqual(r["stats"]["session_dates_seen"], 0)

    def test_s1d_no_snapshot_no_verdict(self):
        """Design #5: no snapshot at all (file missing / no injection)
        → no-verdict (nothing to judge), silently undecidable."""
        with mock.patch.object(vw, "SESSION_SNAPSHOT_PATH",
                               Path("Z:/definitely-missing/session-snapshot.md")):
            r = vw.check_snapshot_freshness()
        self.assertEqual(r["verdict"], "no-verdict")
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["violations"], [])
        self.assertFalse(r["stats"]["snapshot_found"])

    def test_empty_snapshot_text_is_present_but_undated(self):
        """Boundary of the S1a/S1d split: an empty snapshot text IS a present
        snapshot without a session_date → S1a WARN (not no-verdict); only a
        missing file / None injection is S1d."""
        r = vw.check_snapshot_freshness(snapshot_text="")
        self.assertEqual(r["verdict"], "WARN")
        self.assertTrue(r["stats"]["snapshot_found"])

    def test_tv_router_style_old_snapshot_warns_never_no_verdict(self):
        """Design #6 / §7.1: tv/router-style snapshot with a long commit
        stretch behind it → WARN (S1b), NEVER no-verdict (F2: no calendar
        exemption; the compare baseline is commit lag). Constructed below
        the AND thresholds (age 4d < 7d) so the verdict stays WARN."""
        snapshot_dt = date.today() - timedelta(days=4)
        # .governance history predates the snapshot (first = today-5d), then
        # 11 commits sit strictly after it — lag ≥ 10, age < 7 → WARN.
        dates = ([date.today() - timedelta(days=5)]
                 + [date.today() - timedelta(days=3)] * 5
                 + [date.today()] * 6)
        dates.sort()
        with mock.patch.object(sd, "_git_governance_facts",
                               return_value={"tracked": True, "dates": dates}):
            r = vw.check_snapshot_freshness(snapshot_text=_snap(_iso(snapshot_dt)))
        self.assertEqual(r["verdict"], "WARN")
        self.assertNotEqual(r["verdict"], "no-verdict")
        self.assertEqual([w["rule"] for w in r["warnings"]], ["S1b"])
        self.assertEqual(r["stats"]["lag_commits"], 11)


# ── AND double threshold: single-axis hits stay WARN (F5) ───────────────

class Check35AndThresholdTests(unittest.TestCase):
    """S1c AND (design 误报面 ②): days-only or commits-only → WARN, not FAIL."""

    def test_days_over_but_commits_under_stays_warn(self):
        """Design #7: age ≥7d but lag <10 (low-frequency project) → WARN."""
        snapshot_dt = date.today() - timedelta(days=10)
        # History both before (today-12) and after (3 commits) the snapshot.
        dates = [date.today() - timedelta(days=12),
                 date.today() - timedelta(days=9),
                 date.today() - timedelta(days=8),
                 date.today() - timedelta(days=7)]
        with mock.patch.object(sd, "_git_governance_facts",
                               return_value={"tracked": True, "dates": dates}):
            r = vw.check_snapshot_freshness(snapshot_text=_snap(_iso(snapshot_dt)))
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["violations"], [])
        self.assertEqual([w["rule"] for w in r["warnings"]], ["S1b"])
        self.assertEqual(r["stats"]["age_days"], 10)
        self.assertEqual(r["stats"]["lag_commits"], 3)

    def test_commits_over_but_days_under_stays_warn(self):
        """Mirror: lag ≥10 but age <7 (burst of commits since a recent
        snapshot) → WARN, not FAIL."""
        snapshot_dt = date.today() - timedelta(days=2)
        # History both before (today-3) and after (10 commits) the snapshot.
        dates = ([date.today() - timedelta(days=3)]
                 + [date.today() - timedelta(days=1)]
                 + [date.today()] * 9)
        with mock.patch.object(sd, "_git_governance_facts",
                               return_value={"tracked": True, "dates": dates}):
            r = vw.check_snapshot_freshness(snapshot_text=_snap(_iso(snapshot_dt)))
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["violations"], [])
        self.assertEqual([w["rule"] for w in r["warnings"]], ["S1b"])
        self.assertEqual(r["stats"]["lag_commits"], 10)


# ── Baseline degradation: untracked / no-git / mtime / adoption edge ────

class Check35BaselineDegradationTests(unittest.TestCase):
    """Fail-safe paths: no .governance/ commit baseline → mtime secondary
    baseline with the FAIL verdict impossible (design 误报面 ①/④)."""

    def test_untracked_governance_stale_snapshot_warn_not_fail(self):
        """git 无 commit（.governance/ 未跟踪）→ 快照陈旧命中 S1b 形状但
        降级 WARN；即使 age ≥7d 也不可能 FAIL（无 commit 基准不可强判）。"""
        snapshot_dt = date.today() - timedelta(days=10)
        mtime = date.today() - timedelta(days=3)
        with mock.patch.object(sd, "_git_governance_facts",
                               return_value={"tracked": False, "dates": []}):
            r = vw.check_snapshot_freshness(
                snapshot_text=_snap(_iso(snapshot_dt)),
                evidence_mtime=_iso(mtime))
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["stats"]["baseline_kind"], "mtime")
        self.assertEqual(r["stats"]["mtime_date"], _iso(mtime))

    def test_untracked_governance_fresh_snapshot_mtime_pass(self):
        """同一基线退化下新快照 → PASS（mtime 次级基准不误报）。"""
        snapshot_dt = date.today()
        with mock.patch.object(sd, "_git_governance_facts",
                               return_value={"tracked": False, "dates": []}):
            r = vw.check_snapshot_freshness(
                snapshot_text=_snap(_iso(snapshot_dt)),
                evidence_mtime=_iso(date.today()))
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["stats"]["baseline_kind"], "mtime")

    def test_no_baseline_at_all_failsafe_warn(self):
        """git 不可用且无 mtime 可用 → fail-safe WARN（绝不为 no-verdict
        静默放过，也绝不误报 FAIL）。"""
        with mock.patch.object(sd, "_git_governance_facts",
                               return_value=None), \
             mock.patch.object(vw, "SAMPLE_PATH",
                               Path("Z:/missing/plan-tracker.md")), \
             mock.patch.object(vw, "EVIDENCE_PATH",
                               Path("Z:/missing/evidence-log.md")):
            r = vw.check_snapshot_freshness(snapshot_text=_snap("2026-08-01"))
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["stats"]["baseline_kind"], "none")

    def test_snapshot_predates_governance_history_warn_not_fail(self):
        """误报面 ④: snapshot earlier than the FIRST .governance/ commit —
        adoption edge; even with age ≥7d and lag ≥10 → WARN (edge), never FAIL."""
        snapshot_dt = date.today() - timedelta(days=20)
        # All 12 commits sit AFTER the snapshot (governance history started
        # after the snapshot date): first = today-17d, last = today-6d.
        dates = [date.today() - timedelta(days=17 - i) for i in range(12)]
        dates.sort()
        with mock.patch.object(sd, "_git_governance_facts",
                               return_value={"tracked": True, "dates": dates}):
            r = vw.check_snapshot_freshness(snapshot_text=_snap(_iso(snapshot_dt)))
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["violations"], [])
        self.assertEqual([w["rule"] for w in r["warnings"]], ["edge"])
        self.assertEqual(r["stats"]["first_commit_date"], dates[0].isoformat())
        self.assertEqual(r["stats"]["lag_commits"], 12)
        self.assertEqual(r["stats"]["age_days"], 20)


# ── Multi-snapshot / parallel sessions ─────────────────────────────────

class Check35MultiSnapshotTests(unittest.TestCase):
    """误报面 ③: judge the LATEST session only (session_id/date max)."""

    def test_multiple_session_dates_latest_wins(self):
        """Two session_date occurrences → the latest is judged (the older
        would be WARN; the latest equals the commit → PASS)."""
        old = _iso(date.today() - timedelta(days=10))
        new = _iso(date.today() - timedelta(days=2))
        text = _snap(old) + "# 旧快照片段\n" + _snap(new)
        r = vw.check_snapshot_freshness(snapshot_text=text, commit_date=new)
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["stats"]["session_dates_seen"], 2)
        self.assertEqual(r["stats"]["session_date"], new)

    def test_mixed_parseable_and_broken_dates(self):
        """One parseable + one unparseable session_date → parseable wins."""
        text = _snap("2026-08-10") + "\n- **session_date**: 2026-99-99\n"
        r = vw.check_snapshot_freshness(snapshot_text=text, commit_date="2026-08-20")
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["stats"]["session_dates_seen"], 1)
        self.assertEqual(r["stats"]["session_date"], "2026-08-10")


# ── Regex consistency with resolve_entry (design §3.2) ─────────────────

class Check35RegexConsistencyTests(unittest.TestCase):
    """The task's '一致正则' gate: resolve_entry declares its snapshot date
    regex as the mirror of verify_workflow's proven pattern — pin it."""

    def test_session_date_regex_identical_to_resolve_entry(self):
        """The task's '一致正则' gate: resolve_entry declares its snapshot
        date regex as the mirror of verify_workflow's proven pattern —
        pin the equality so future drift is caught, not silently diverged."""
        self.assertEqual(
            resolve_entry._SNAPSHOT_DATE_RE.pattern,
            vw.FIX_105_SNAPSHOT_DATE_RE.pattern)

    def test_check_uses_the_shared_proven_regex(self):
        """The check's extraction behaves exactly like the shared regex on
        a canonical line and a drifted (non-ISO) line."""
        self.assertEqual(
            vw.FIX_105_SNAPSHOT_DATE_RE.findall(
                "- **session_date**: 2026-08-23"),
            ["2026-08-23"])
        self.assertEqual(
            vw.FIX_105_SNAPSHOT_DATE_RE.findall(
                "- **session_date**: 2026/08/23"),
            [])

# ── Live mode with patched paths (design #8) ────────────────────────────

class Check35LiveModeTests(unittest.TestCase):
    """Live read paths: SESSION_SNAPSHOT_PATH + git facts drive the check."""

    def test_live_mode_reads_patched_paths_fresh(self):
        today_iso = _ISO
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            gov.mkdir()
            (gov / "session-snapshot.md").write_text(
                _snap(today_iso), encoding="utf-8")
            with mock.patch.object(vw, "SESSION_SNAPSHOT_PATH",
                                   gov / "session-snapshot.md"), \
                 mock.patch.object(sd, "_git_governance_facts",
                                   return_value={"tracked": True,
                                                 "dates": [date.today()]}):
                r = vw.check_snapshot_freshness()
        self.assertEqual(r["verdict"], "PASS")
        self.assertTrue(r["stats"]["snapshot_found"])

    def test_live_mode_reads_patched_paths_stale(self):
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            gov.mkdir()
            snap_dt = date.today() - timedelta(days=5)
            (gov / "session-snapshot.md").write_text(
                _snap(_iso(snap_dt)), encoding="utf-8")
            # History predates the snapshot (today-6d); latest commit today.
            with mock.patch.object(vw, "SESSION_SNAPSHOT_PATH",
                                   gov / "session-snapshot.md"), \
                 mock.patch.object(sd, "_git_governance_facts",
                                   return_value={"tracked": True,
                                                 "dates": [date.today() - timedelta(days=6),
                                                           date.today()]}):
                r = vw.check_snapshot_freshness()
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual([w["rule"] for w in r["warnings"]], ["S1b"])


# ── Orthogonality: 28c / 34 / 35 same-frame, no swallowing ──────────────

class Check35OrthogonalityTests(unittest.TestCase):
    """Design §5.1 #9/#10: the three checks ask three independent questions;
    same-frame triggers stay independently presented."""

    PLAN = (
        "**工作流版本**: 0.76.0\n\n"
        "## 版本规划\n\n"
        "| 版本 | 状态 | 日期 |\n"
        "| --- | --- | --- |\n"
        "| **0.76.0** | **已发布** | **2026-08-22** |\n"
    )
    COMPLETION_ROW = (
        "| EVD-FIX-300 | FIX-300 | 产品代码 | FIX-300 完成（2026-08-22）。"
        "完成即推荐 | 事实依据：测试输出 | a.py | Developer | 2026-08-22 | "
        "G11 | ✅ 完成 |"
    )

    def _write_same_frame(self):
        """Build a tempdir fixture and return (tracker_path, snap_text,
        plan_content): live plan-tracker + session-snapshot pair carrying
        the SAME stale snapshot (drifts on all three axes)."""
        td = tempfile.TemporaryDirectory()
        gov = Path(td.name) / ".governance"
        gov.mkdir()
        tracker = gov / "plan-tracker.md"
        tracker.write_text(self.PLAN, encoding="utf-8")
        snap_text = _snap("2026-08-01", extra=self.PLAN)
        (gov / "session-snapshot.md").write_text(snap_text, encoding="utf-8")
        return td, tracker, snap_text, tracker.read_text(encoding="utf-8")

    def test_orthogonal_independent_judgements(self):
        """Same stale snapshot: 28c sees release-fact drift, 34 sees
        completion S1, 35 sees commit lag — each judges on its own axis."""
        td, tracker, snap_text, plan_content = self._write_same_frame()
        try:
            issues_28c = vw._snapshot_fact_source_issues(plan_content, tracker)
            r34 = vw.check_completion_recommendation(
                evidence_rows=[self.COMPLETION_ROW], snapshot_text=snap_text)
            r35 = vw.check_snapshot_freshness(
                snapshot_text=snap_text, commit_date="2026-08-10")
        finally:
            td.cleanup()
        self.assertTrue(issues_28c)
        self.assertTrue(any("older than latest published release" in i
                            for i in issues_28c))
        self.assertEqual(r34["verdict"], "FAIL")   # S1: completion w/o snapshot
        self.assertEqual([v["rule"] for v in r34["violations"]], ["S1"])
        self.assertEqual(r35["verdict"], "WARN")   # S1b: snapshot < commit
        self.assertEqual([w["rule"] for w in r35["warnings"]], ["S1b"])

    def test_28c_34_35_same_frame_all_fire_no_swallow(self):
        """Design #10: with a snapshot that drifts on ALL three axes, every
        check surfaces its own finding — none swallows another (the
        same-frame fixture reproduces the §5.1 #10 combination)."""
        td, tracker, snap_text, plan_content = self._write_same_frame()
        try:
            snap_text34 = snap_text + (
                "\n## 下次会话优先级\n\n"
                "- FIX-301 下一次做；FIX-302 依赖\n")
            issues_28c = vw._snapshot_fact_source_issues(plan_content, tracker)
            r34 = vw.check_completion_recommendation(
                evidence_rows=[self.COMPLETION_ROW], snapshot_text=snap_text34)
            r35 = vw.check_snapshot_freshness(
                snapshot_text=snap_text34, commit_date="2026-08-10")
        finally:
            td.cleanup()
        self.assertTrue(issues_28c)
        self.assertEqual(r34["verdict"], "FAIL")   # S1 (violation) wins over S2
        self.assertIn("S1", [v["rule"] for v in r34["violations"]])
        self.assertIn("S2", [w["rule"] for w in r34["warnings"]])
        self.assertEqual(r35["verdict"], "WARN")


# ── Result contract + no-raise + numbering ─────────────────────────────

class Check35ContractTests(unittest.TestCase):
    """Result shape, never-raise contract, numbering (F9), export."""

    def test_result_contract_shape(self):
        r = vw.check_snapshot_freshness(snapshot_text=_snap(),
                                        commit_date="2026-08-23")
        self.assertEqual(
            set(r.keys()),
            {"verdict", "reason", "violations", "warnings", "stats"})
        self.assertIn(r["verdict"], ("PASS", "WARN", "FAIL", "no-verdict"))
        for key in ("snapshot_found", "session_dates_seen", "session_date",
                    "baseline_kind", "commit_date", "first_commit_date",
                    "mtime_date", "lag_commits", "age_days",
                    "warn_count", "violation_count"):
            self.assertIn(key, r["stats"], f"stats.{key} missing")

    def test_never_raises_on_garbage_inputs(self):
        """Never raise: garbage text, broken dates, None/odd injection types,
        missing baseline — every path returns the contract dict."""
        with mock.patch.object(vw, "SESSION_SNAPSHOT_PATH",
                               Path("Z:/definitely-missing/snapshot.md")), \
             mock.patch.object(vw, "SAMPLE_PATH",
                               Path("Z:/missing/plan-tracker.md")), \
             mock.patch.object(vw, "EVIDENCE_PATH",
                               Path("Z:/missing/evidence-log.md")), \
             mock.patch.object(sd, "_git_governance_facts", return_value=None):
            inputs = [
                dict(snapshot_text="random gibberish \u00ff \u2027 \u4e71\u7801"),
                dict(snapshot_text="\n" * 50),
                dict(snapshot_text=None),
                dict(snapshot_text=_snap(), commit_date="not-a-date"),
                dict(snapshot_text=_snap(), commit_date=12345),
                dict(snapshot_text=_snap("2026-08-23"), evidence_mtime=999.5),
                dict(snapshot_text=_snap("2026-08-23"), plan_content="garbage"),
                dict(snapshot_text=_snap("2026-08-23"), commit_date=None),
                dict(snapshot_text=12345),               # P1-2: non-str int
                dict(snapshot_text=["2026-08-01"]),      # P1-2: non-str list
                dict(snapshot_text=b"# snapshot bytes"),  # P1-2: non-str bytes
            ]
            for kwargs in inputs:
                r = vw.check_snapshot_freshness(**kwargs)
                self.assertIn(
                    r["verdict"], ("PASS", "WARN", "FAIL", "no-verdict"),
                    f"kwargs={kwargs}")
                self.assertIsInstance(r["violations"], list)
                self.assertIsInstance(r["warnings"], list)

    def test_check35_block_position_and_numbering(self):
        """Check 35 block exists, numbered, between Check 34 and Check 36."""
        src = (_INFRA_DIR / "verify_workflow.py").read_text(encoding="utf-8")
        block35 = "┌─ Check 35: Snapshot Freshness (FIX-268)"
        self.assertIn(block35, src)
        self.assertLess(src.index("┌─ Check 34"), src.index(block35))
        self.assertLess(src.index(block35),
                        src.index("┌─ Check 36: Risk Mitigation Closure"))

    def test_check35_exported_and_function_lives_in_snapshot_domain(self):
        domain = (_INFRA_DIR / "checks" / "snapshot_domain.py").read_text(
            encoding="utf-8")
        self.assertIn("def check_snapshot_freshness", domain)
        self.assertIn("def _git_governance_facts", domain)
        self.assertTrue(hasattr(vw, "check_snapshot_freshness"))

    def test_check35_import_export_placed_with_domain_imports(self):
        """Thin re-export sits with the other domain import blocks (no
        import cycle / no late function re-binding)."""
        src = (_INFRA_DIR / "verify_workflow.py").read_text(encoding="utf-8")
        self.assertIn("from checks.snapshot_domain import (", src)
        idx_import = src.index("from checks.snapshot_domain import (")
        idx_block = src.index("┌─ Check 35")
        self.assertLess(idx_import, idx_block)


# ── P1 hardening (review-FIX-268-CODE-R0: P1-1 / P1-2) ───────────────────

class Check35P1HardeningTests(unittest.TestCase):
    """R0 P1 fixes, red→green:
    P1-1 — live read of a NON-UTF-8 session-snapshot.md must degrade via
    errors="replace" (resolve_entry._read_text_safe precedent), not raise
    UnicodeDecodeError (a ValueError subclass the IOError/OSError guard
    cannot catch) — the "never raises" contract.
    P1-2 — non-str injected snapshot_text (int/list/bytes) is the one
    unguarded injection parameter and would raise TypeError in the regex
    findall; it must degrade to S1a fail-safe WARN (DEC-152 ①: present but
    unparseable → WARN disclosure; only a missing file/None is no-verdict).
    """

    def test_p1_1_live_non_utf8_snapshot_degrades_not_raises(self):
        """Non-UTF-8 snapshot bytes: decode degrades with replacement chars;
        the ASCII session_date line stays parseable → normal judgement
        (deterministic via patched git facts), never an exception."""
        bad = b"# snapshot\n- **session_date**: 2026-08-01\n\xff\xfe invalid utf-8 tail\n"
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            gov.mkdir()
            snap = gov / "session-snapshot.md"
            snap.write_bytes(bad)
            with mock.patch.object(vw, "SESSION_SNAPSHOT_PATH", snap), \
                 mock.patch.object(sd, "_git_governance_facts",
                                   return_value={"tracked": True,
                                                 "dates": [date(2026, 8, 1),
                                                           date(2026, 8, 10)]}):
                r = vw.check_snapshot_freshness()
        self.assertEqual(r["verdict"], "WARN")          # S1b: 08-01 < 08-10
        self.assertEqual([w["rule"] for w in r["warnings"]], ["S1b"])
        self.assertEqual(r["stats"]["session_date"], "2026-08-01")

    def test_p1_1_live_non_utf8_snapshot_no_date_warns_s1a(self):
        """Non-UTF-8 bytes that also destroy the session_date line → S1a
        WARN (fail-safe), never raise."""
        bad = b"# snapshot\n- **session_id**: 20260823-x\n\xff\xfe totally broken\n"
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            gov.mkdir()
            snap = gov / "session-snapshot.md"
            snap.write_bytes(bad)
            with mock.patch.object(vw, "SESSION_SNAPSHOT_PATH", snap):
                r = vw.check_snapshot_freshness()
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["stats"]["session_dates_seen"], 0)
        self.assertEqual(r["stats"]["snapshot_found"], True)

    def test_p1_2_non_str_snapshot_text_warns_not_raises(self):
        """int / list / bytes injections → S1a fail-safe WARN (reason names
        the non-text type), never TypeError — DEC-152 ① shapes."""
        for bad in (12345, ["2026-08-01"], b"# snapshot bytes", {"date": "x"}):
            r = vw.check_snapshot_freshness(snapshot_text=bad)
            self.assertEqual(r["verdict"], "WARN", f"bad={bad!r}")
            self.assertIn("not text", r["reason"], f"bad={bad!r}")
            self.assertTrue(r["stats"]["snapshot_found"])
            self.assertEqual(r["stats"]["session_dates_seen"], 0)
            self.assertIsInstance(r["violations"], list)
            self.assertIsInstance(r["warnings"], list)

    def test_p1_2_non_str_live_never_returns_non_str_text(self):
        """Live read is always str (read_text); the non-str guard only ever
        fires on injection — assert the read path yields str content."""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            gov.mkdir()
            snap = gov / "session-snapshot.md"
            snap.write_text(_snap("2026-08-23"), encoding="utf-8")
            with mock.patch.object(vw, "SESSION_SNAPSHOT_PATH", snap), \
                 mock.patch.object(sd, "_git_governance_facts",
                                   return_value={"tracked": True,
                                                 "dates": [date(2026, 8, 23)]}):
                r = vw.check_snapshot_freshness()
        self.assertEqual(r["verdict"], "PASS")
        self.assertIn("fresh", r["reason"])


if __name__ == "__main__":
    unittest.main()
