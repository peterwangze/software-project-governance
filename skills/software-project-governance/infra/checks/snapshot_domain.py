"""Snapshot-domain check — extracted for FIX-268 in 0.76.0.

Scope (design audit-145-watchdog-design-0.76.0.md §3.2 / REQ-145.2): the
snapshot-freshness watchdog (`check_snapshot_freshness`, Check 35). The
AUDIT-145 blind spot this closes: the session snapshot can drift silently
behind the governance baseline — tv (08-19/85 commits) and router (08-21/41
commits) carried month-old snapshots while .governance/ kept moving. The
watchdog is a CONTENT+timeline assertion: the snapshot's session_date must
not fall behind the latest .governance/ commit.

This module owns the snapshot check domain. Shared helpers and constants
still defined in verify_workflow.py (``SESSION_SNAPSHOT_PATH``,
``HOST_PROJECT_ROOT``, ``SAMPLE_PATH``, ``EVIDENCE_PATH``,
``FIX_105_SNAPSHOT_DATE_RE``) are reached through a deferred module
reference rather than a top-level import, so verify_workflow.py can import
this module at module load time without an import cycle — the same
deferred-``_vw()`` pattern as checks.risk_domain / checks.manifest /
checks.capability_registry.

Design orthogonality: Check 28c (`_snapshot_fact_source_issues`) compares
the snapshot date vs the latest PUBLISHED RELEASE date; Check 34 compares
the snapshot's recommendation section vs evidence rows; Check 35 compares
the snapshot's session_date vs the latest .governance/ COMMIT date. Three
independent questions — no shared judgement, no swallowing (design §3.2
"与 Check 34/Check 28c 的关系").

See docs/architecture/ADR-016-verify-phase5-extraction-0.70.0.md for the
domain-extraction design precedent.
"""

import subprocess
from datetime import date, datetime
from pathlib import Path

# ── Shared-helper access (deferred to avoid import cycle) ──────────
# Same deferred-_vw() pattern as checks.risk_domain (Phase 5b). The shared
# names are resolved lazily on the first call into this module (after
# verify_workflow has finished loading) and cached in this module's globals,
# so moved function bodies can reference them by bare name unchanged.

_VW_CACHE = None


def _vw():
    """Return the verify_workflow module (imported lazily, cached)."""
    global _VW_CACHE
    if _VW_CACHE is None:
        import verify_workflow  # noqa: WPS433 (deferred import on purpose)
        _VW_CACHE = verify_workflow
    return _VW_CACHE


# Shared names this domain reaches back into verify_workflow for. Refreshed
# on every call into `_resolve_shared()` (NOT cached) so test-time monkey-
# patching of verify_workflow attributes propagates.
_SHARED_NAMES = (
    "SESSION_SNAPSHOT_PATH",  # live snapshot read (host .governance/)
    "HOST_PROJECT_ROOT",      # git facts root (FIX-270 mixed-root fix)
    "SAMPLE_PATH",            # plan-tracker (live mtime secondary baseline)
    "EVIDENCE_PATH",          # evidence-log (live mtime secondary baseline)
    "FIX_105_SNAPSHOT_DATE_RE",  # proven **session_date** regex (design §3.2)
)


def _resolve_shared():
    """Refresh this module's globals with shared names from verify_workflow."""
    vw = _vw()
    g = globals()
    for _name in _SHARED_NAMES:
        g[_name] = getattr(vw, _name)


# ── Domain constants ────────────────────────────────────────────────

# S1c AND double threshold (design §3.2): FAIL only when the snapshot is
# BOTH at least this many days old AND at least this many .governance/ commits
# behind. AND avoids mis-FAILing low-frequency projects (design 误报面 ② / F5).
SNAPSHOT_STALE_DAYS = 7
SNAPSHOT_STALE_COMMITS = 10

_GIT_TIMEOUT = 15  # mirrors checks.projection._tracked_target_files (15s)


# ── Git facts ──────────────────────────────────────────────────────

def _git_governance_facts(host_root):
    """Return ``{"tracked": bool, "dates": [date, ...]}`` for ``.governance/``.

    ``None`` → git unavailable (no check run) or unusable. ``tracked=False``
    → ``.governance/`` is NOT tracked by the project git (gitignored /
    runtime-only — design 误报面 ①); the caller then has no commit baseline
    and falls back to the plan-tracker / evidence-log mtime secondary
    baseline (fail-safe WARN, never FAIL). ``dates`` = ascending commit
    dates (``git log --format=%cs -- .governance/``) of the tracked history.

    Never raises: any subprocess/parse failure degrades to ``None``.
    """
    try:
        if host_root is None:
            return None
        root = Path(host_root)
        if not (root / ".git").exists():
            return None
        tracked = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--", ".governance/"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=False, timeout=_GIT_TIMEOUT,
        )
        if tracked.returncode != 0:
            return None
        if not tracked.stdout.strip():
            # No .governance/ file is tracked — stale `git log` history is
            # not a baseline for the live governance facts (FIX-141 case:
            # the dogfood repo untracked its runtime records).
            return {"tracked": False, "dates": []}
        log = subprocess.run(
            ["git", "-C", str(root), "log", "--format=%cs", "--", ".governance/"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=False, timeout=_GIT_TIMEOUT,
        )
        if log.returncode != 0:
            return None
        dates = []
        for line in log.stdout.splitlines():
            try:
                dates.append(datetime.strptime(line.strip(), "%Y-%m-%d").date())
            except ValueError:
                continue  # unparseable commit-date row → skip (fail-safe)
        dates.sort()
        return {"tracked": True, "dates": dates}
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


# ── Parsing helpers ────────────────────────────────────────────────

def _parse_session_dates(text):
    """Return the parseable ``**session_date**`` dates in ``text`` (ascending).

    Uses the shared ``FIX_105_SNAPSHOT_DATE_RE`` — the proven regex declared
    by resolve_entry.py as its mirror (``_SNAPSHOT_DATE_RE``, identical
    pattern) — so the two scripts agree on what a session date is. Multiple
    occurrences are allowed (multi-snapshot / parallel sessions): the caller
    judges the LATEST one (design 误报面 ③).

    Defense in depth (P1-2): a non-str ``text`` returns ``[]`` — the regex
    would otherwise raise TypeError. The caller's pre-check already routes
    non-str input to S1a WARN; this guard protects every future call site.
    """
    _resolve_shared()
    if not isinstance(text, str):
        return []
    parsed = []
    for raw in FIX_105_SNAPSHOT_DATE_RE.findall(text):
        try:
            parsed.append(datetime.strptime(raw, "%Y-%m-%d").date())
        except ValueError:
            continue
    parsed.sort()
    return parsed


def _to_date(value):
    """Coerce ``None``/``date``/``datetime``/``"YYYY-MM-DD"`` → ``date|None``."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip()[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _live_mtime_baseline():
    """Return the newest plan-tracker/evidence-log mtime date, or None."""
    _resolve_shared()
    candidates = []
    for path in (SAMPLE_PATH, EVIDENCE_PATH):
        try:
            if path is not None and path.is_file():
                candidates.append(datetime.fromtimestamp(path.stat().st_mtime).date())
        except (OSError, ValueError):
            continue
    return max(candidates) if candidates else None


def _set_verdict(result, verdict, reason):
    result["stats"]["warn_count"] = len(result["warnings"])
    result["stats"]["violation_count"] = len(result["violations"])
    result["verdict"] = verdict
    result["reason"] = reason
    return result


# ── Check 35 ───────────────────────────────────────────────────────

def check_snapshot_freshness(plan_content=None, snapshot_text=None,
                             evidence_mtime=None, commit_date=None):
    """FIX-268 / REQ-145.2 (design audit-145-watchdog-design §3.2): Check 35.

    Session-snapshot freshness watchdog. The snapshot's ``session_date``
    must not fall behind the latest ``.governance/`` commit — a session
    snapshot that stays frozen while governance facts keep moving is the
    "zero-update" blind spot AUDIT-145 targets (tv/router 08-19/08-21
    cases).

    Signals (verdict ∈ PASS / WARN / FAIL / no-verdict; never raises):
      S1a  WARN — the snapshot exists but its ``session_date`` is missing or
          unparseable (fail-safe: format drift must never FAIL).
      S1b  WARN — snapshot date < latest .governance/ commit date (gradual
          start, DEC-146 progressive path).
      S1c  FAIL — S1b AND (age ≥ 7 days AND .governance/ commits after the
          snapshot ≥ 10): the AND double threshold keeps low-frequency
          projects (one axis hit only) at WARN (design 误报面 ②).
      S1d  no-verdict — no snapshot exists / nothing to judge.
      edge WARN — snapshot date predates the .governance/ git history
          (adoption edge, design 误报面 ④): weak baseline, never FAIL.
      no-baseline WARN — .governance/ is untracked / uncommitted (design
          误报面 ①) AND no plan-tracker/evidence-log mtime as secondary
          baseline: freshness unverifiable, fail-safe WARN.

    Baseline: ``git -C <host_root> log -1 --format=%cs -- .governance/`` —
    the latest tracked commit date (facts root = HOST_PROJECT_ROOT per the
    FIX-270 mixed-root fix). Untracked .governance/ (no ``git ls-files``
    match) → NO commit baseline → the plan-tracker / evidence-log file
    mtime becomes the secondary baseline; the FAIL verdict is then
    impossible (the would-be-FAIL is downgraded to WARN).

    Injection surface (all optional; default = live read):
      ``snapshot_text``  session-snapshot.md text (Check 34 injection mode).
      ``commit_date``    latest .governance/ commit date ("YYYY-MM-DD");
                          live mode derives it from git when absent.
      ``evidence_mtime`` secondary-baseline date ("YYYY-MM-DD" or date);
                          live mode derives plan-tracker/evidence-log mtimes.
      ``plan_content``   accepted for design-signature symmetry — Check 35
                          judges snapshot-vs-git-baseline only; the
                          plan-vs-snapshot fact question belongs to Check 28c
                          (orthogonal, §3.2).

    ``_git_governance_facts`` supplies the live commit-date list (also the
    lag count for S1c); tests patch it for deterministic fixtures.

    Returns ``{verdict, reason, violations, warnings, stats}``.
    """
    result = {
        "verdict": "no-verdict",
        "reason": "",
        "violations": [],
        "warnings": [],
        "stats": {
            "snapshot_found": False,
            "session_dates_seen": 0,
            "session_date": None,
            "baseline_kind": "none",  # git | mtime | none
            "commit_date": None,
            "first_commit_date": None,
            "mtime_date": None,
            "lag_commits": None,
            "age_days": None,
            "warn_count": 0,
            "violation_count": 0,
        },
    }
    _resolve_shared()

    # ── Resolve snapshot text (S1d: nothing to judge) ──
    text = snapshot_text
    if text is None:
        try:
            if not SESSION_SNAPSHOT_PATH.is_file():
                return _set_verdict(
                    result, "no-verdict",
                    "session-snapshot.md not found — no snapshot to judge")
            # P1-1 hardening: errors="replace" (resolve_entry._read_text_safe
            # precedent) — a non-UTF-8 snapshot must degrade to a WARN/judged
            # path via replacement chars, never raise UnicodeDecodeError
            # (UnicodeDecodeError is a ValueError, NOT caught by IOError/
            # OSError — the "never raises" contract would be broken).
            text = SESSION_SNAPSHOT_PATH.read_text(
                encoding="utf-8", errors="replace")
        except (IOError, OSError):
            return _set_verdict(
                result, "no-verdict",
                "session-snapshot.md unreadable — no snapshot to judge")
    result["stats"]["snapshot_found"] = True

    # P1-2 hardening (DEC-152 ①): a non-str injected snapshot content
    # (int / list / bytes …) is "present but unparseable" — S1a fail-safe
    # WARN, never a TypeError from the regex findall.
    if not isinstance(text, str):
        return _set_verdict(
            result, "WARN",
            "session snapshot content is not text ({0}) — no parseable "
            "**session_date** (fail-safe WARN, design S1a / DEC-152 ①)".format(
                type(text).__name__))

    # ── S1a: session_date parse (fail-safe WARN on drift) ──
    snap_dates = _parse_session_dates(text)
    result["stats"]["session_dates_seen"] = len(snap_dates)
    if not snap_dates:
        return _set_verdict(
            result, "WARN",
            "session snapshot has no parseable **session_date** (missing or "
            "format drift) — fail-safe WARN, nothing judged (design S1a)")
    # Multi-snapshot / parallel sessions: judge the LATEST only (design ③).
    session_dt = snap_dates[-1]
    age_days = (date.today() - session_dt).days
    result["stats"]["session_date"] = session_dt.isoformat()
    result["stats"]["age_days"] = age_days

    # ── Resolve the .governance commit baseline ──
    facts = None
    git_last = _to_date(commit_date)
    if git_last is None:
        facts = _git_governance_facts(HOST_PROJECT_ROOT)
        if facts and facts["tracked"] and facts["dates"]:
            git_last = facts["dates"][-1]

    if git_last is not None:
        result["stats"]["baseline_kind"] = "git"
        result["stats"]["commit_date"] = git_last.isoformat()
        first_dt = None
        if facts and facts["tracked"] and facts["dates"]:
            first_dt = facts["dates"][0]
            result["stats"]["first_commit_date"] = first_dt.isoformat()
            # "落后 commit 数" = .governance/ commits dated AFTER the snapshot.
            result["stats"]["lag_commits"] = sum(
                1 for d in facts["dates"] if d > session_dt)

        # Edge: snapshot predates the .governance history → weak baseline.
        if first_dt is not None and session_dt < first_dt:
            result["warnings"].append({
                "rule": "edge",
                "session_date": session_dt.isoformat(),
                "commit_date": git_last.isoformat(),
                "reason": (
                    "snapshot dated {0} predates the .governance/ git history "
                    "(first commit {1}) — adoption edge, no strong baseline; "
                    "fail-safe WARN, never FAIL".format(
                        session_dt.isoformat(), first_dt.isoformat())),
            })
            return _set_verdict(
                result, "WARN",
                "snapshot predates the .governance history — weak baseline "
                "(fail-safe WARN)")

        if session_dt < git_last:
            # S1b → S1c progressive (AND double threshold, design F5).
            lag = result["stats"]["lag_commits"]
            if (age_days >= SNAPSHOT_STALE_DAYS
                    and lag is not None
                    and lag >= SNAPSHOT_STALE_COMMITS):
                result["violations"].append({
                    "rule": "S1c",
                    "session_date": session_dt.isoformat(),
                    "commit_date": git_last.isoformat(),
                    "lag_commits": lag,
                    "age_days": age_days,
                    "reason": (
                        "session snapshot {0} is stale: .governance/ last "
                        "commit {1}, age {2} day(s) ≥ {3} AND {4} commit(s) "
                        "after the snapshot ≥ {5} — both thresholds exceeded "
                        "(design S1c AND)".format(
                            session_dt.isoformat(), git_last.isoformat(),
                            age_days, SNAPSHOT_STALE_DAYS, lag,
                            SNAPSHOT_STALE_COMMITS)),
                })
                return _set_verdict(
                    result, "FAIL",
                    "session snapshot {0} is stale — {1} day(s) old and {2} "
                    ".governance/ commit(s) behind".format(
                        session_dt.isoformat(), age_days, lag))
            result["warnings"].append({
                "rule": "S1b",
                "session_date": session_dt.isoformat(),
                "commit_date": git_last.isoformat(),
                "lag_commits": lag,
                "reason": (
                    "session snapshot dated {0} is older than the latest "
                    ".governance/ commit ({1}); age {2} day(s), lag {3} — "
                    "gradual WARN (design S1b); FAIL only when age ≥ {4} AND "
                    "commit lag ≥ {5}".format(
                        session_dt.isoformat(), git_last.isoformat(),
                        age_days, lag if lag is not None else "n/a",
                        SNAPSHOT_STALE_DAYS, SNAPSHOT_STALE_COMMITS)),
            })
            return _set_verdict(
                result, "WARN",
                "session snapshot {0} is behind the latest .governance/ "
                "commit ({1})".format(session_dt.isoformat(),
                                      git_last.isoformat()))
        # Snapshot >= latest commit → fresh.
        return _set_verdict(
            result, "PASS",
            "session snapshot {0} is fresh (on/after the latest "
            ".governance/ commit {1})".format(session_dt.isoformat(),
                                              git_last.isoformat()))

    # ── No git commit baseline → secondary mtime baseline (WARN cap) ──
    mtime_dt = _to_date(evidence_mtime)
    if mtime_dt is None:
        mtime_dt = _live_mtime_baseline()
    if mtime_dt is not None:
        result["stats"]["baseline_kind"] = "mtime"
        result["stats"]["mtime_date"] = mtime_dt.isoformat()
        if session_dt < mtime_dt:
            result["warnings"].append({
                "rule": "S1b",
                "session_date": session_dt.isoformat(),
                "mtime_date": mtime_dt.isoformat(),
                "reason": (
                    "session snapshot dated {0} is older than the governance "
                    "files' last modification ({1}); .governance/ has no "
                    "commit baseline (untracked/unversioned) — fail-safe WARN "
                    "(would-be FAIL downgraded, never FAIL)".format(
                        session_dt.isoformat(), mtime_dt.isoformat())),
            })
            return _set_verdict(
                result, "WARN",
                "snapshot {0} behind governance files mtime {1} — no commit "
                "baseline (fail-safe WARN)".format(session_dt.isoformat(),
                                                   mtime_dt.isoformat()))
        return _set_verdict(
            result, "PASS",
            "session snapshot {0} is fresh against the governance files "
            "mtime {1} (.governance/ has no commit baseline — weak baseline, "
            "fail-safe)".format(session_dt.isoformat(), mtime_dt.isoformat()))

    result["stats"]["baseline_kind"] = "none"
    return _set_verdict(
        result, "WARN",
        "no .governance/ commit baseline and no plan-tracker/evidence-log "
        "mtime baseline — snapshot freshness not verifiable (fail-safe WARN, "
        "never FAIL)")
