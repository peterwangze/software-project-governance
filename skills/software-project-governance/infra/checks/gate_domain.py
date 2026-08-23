"""Gate-sequence-for-release check — extracted for FIX-266 in 0.76.0.

Scope (design audit-145-watchdog-design-0.76.0.md §3.4 / REQ-145.4): the
gate↔release interlock watchdog (`check_gate_sequence_for_release`,
Check 37). The AUDIT-145 blind spot this closes (G9): a project can push a
release tag while the gates that must precede the release are still
pending — tv (G6/G7/G8 pending while v1.6.x tags exist) and router
(G4-G7 pending while v0.2.1 exists) both did exactly that.

The check is embedded in ``check_release_readiness`` (the release-side
interlock) and also runs as a standalone Check 37 block in
``cmd_check_governance`` (the health-side disclosure).

Judgement (DEC-153 — the FIX-266 semantic ruling):
  * Release-gate identification: the FIRST row (read order) whose 阶段转换
    (transition) cell contains「发布」— row-order derivation, never a
    hard-coded gate id, so both standard (11 gates, G8→版本发布) and
    lightweight (7 gates, G5→CI→发布) profiles derive the same way.
  * Prerelease gates: all non-release rows read BEFORE the release gate.
  * G-s1  FAIL — a published tag exists whose date is EARLIER than a
      prerelease gate marked ``passed`` (or the passed gate has no date):
      the release happened before/while that gate was pending — the
      interlock was bypassed. (Physical semantics: release EARLIER than
      gate pass = bypass. Direction discussed in the FIX-266 report — the
      design §3.4 table wording is ambiguous, the implemented rule is the
      bypass semantics above.)
  * G-s2  FAIL — a published tag exists and any prerelease gate is
      ``pending``: conservative — a pending prerelease gate cannot prove
      ordering, so an existing release tag is by definition a bypass.
  * G-s3  WARN  — no published tag detectable from git (no semver tag or
      git unavailable), yet the release gate is marked passed while
      prerelease gates are pending: fail-safe WARN (a git-blind run must
      never FAIL; the release-gate-passed claim is disclosed instead).
  * 历史豁免 (DEC-153 ②): ``lineage_mode`` distinguishes the run state.
      candidate — the current release candidate → G-s1/G-s2 FAIL.
      released   — an already-published history check → SAME findings are
      WARN-disclosed, never FAIL (diagnostic §7.2 asks for "don't AGAIN",
      not for retroactive debt noise from tv/router history).
  * passed-on-entry (DEC-153 ④): treated as NON-pending — an on-entry
      onboarding has no real timeline to judge. Strong interlock applies
      only when at least one prerelease gate is ``passed`` (not on-entry);
      all-on-entry prerelease → PASS.
  * Multiple tags: only the LATEST candidate (highest semver) is judged;
      stale tags never trigger (design 误报面).
  * git unavailable → G-s3-only degradation (never FAIL, WARN cap).

This module owns the gate check domain. Shared helpers and constants still
defined in verify_workflow.py (``HOST_PROJECT_ROOT``, ``SAMPLE_PATH``,
``parse_gate_status``) are reached through a deferred module reference
rather than a top-level import, so verify_workflow.py can import this
module at module load time without an import cycle — the same deferred
``_vw()`` pattern as checks.risk_domain / checks.snapshot_domain.

Orthogonality: this check does NOT replace Check 23 (profile/gate row
count), the check-gate-consistency evidence checks, or the existing
``check_release_readiness`` semantics — it is a new content dimension
(gate ORDER vs RELEASE facts) embedded as one more release sub-check.
"""

import re
import subprocess
from datetime import date, datetime
from pathlib import Path

# ── Shared-helper access (deferred to avoid import cycle) ──────────
# Same deferred-_vw() pattern as checks.risk_domain (Phase 5b) and
# checks.snapshot_domain (FIX-268). The shared names are resolved lazily on
# the first call into this module (after verify_workflow has finished
# loading) and cached in this module's globals, so moved function bodies can
# reference them by bare name unchanged.

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
    "HOST_PROJECT_ROOT",   # git facts root (FIX-270 mixed-root fix — never ROOT)
    "SAMPLE_PATH",         # plan-tracker (live parse_gate_status source)
    "parse_gate_status",   # proven gate-table parser (verify_workflow.py:7182)
)


def _resolve_shared():
    """Refresh this module's globals with shared names from verify_workflow."""
    vw = _vw()
    g = globals()
    for _name in _SHARED_NAMES:
        g[_name] = getattr(vw, _name)


# ── Domain constants ────────────────────────────────────────────────

# Semver-shaped tag name (design §3.4 data source: ``^v?[0-9]+\.[0-9]+\.[0-9]+$``).
_RELEASE_TAG_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")

_GIT_TIMEOUT = 15  # mirrors snapshot_domain / checks.projection (15s)

# Release-gate marker in the 阶段转换 (transition) cell (design §3.4).
_RELEASE_TRANSITION_MARKER = "发布"

# Markdown emphasis to strip from table cells before matching (the tv
# project writes `` `passed-on-entry` `` — backticked status cells; the
# same normalize as change_triage.parse_version_chain's re.sub(r"[*`]")).
_MD_EMPHASIS_RE = re.compile(r"[*`_]")


def _strip_md(value):
    """Strip markdown emphasis from a table cell (never raises)."""
    return _MD_EMPHASIS_RE.sub("", str(value or ""))

# Roadmap terminal statuses that index an ALREADY-PUBLISHED (or withdrawn)
# version — BR-4 auto-released gate lineage for historical checks.
_RELEASED_HISTORY_STATUS_MARKERS = ("已发布", "已撤回", "失效", "不可信")


# ── Git facts ──────────────────────────────────────────────────────

def _git_published_tags(host_root):
    """Return ``[{"tag": str, "date": "YYYY-MM-DD"|None}, ...]`` or ``None``.

    ``None`` → git unavailable (no .git / subprocess failure / timeout) —
    the caller degrades to the fail-safe G-s3 path (never FAIL). ``[]`` →
    git works but there is no semver-shaped tag. Tags come from
    ``git for-each-ref`` (creatordate, annotated tags carry the tagger
    date, lightweight tags the commit date). Never raises.
    """
    try:
        if host_root is None:
            return None
        root = Path(host_root)
        if not (root / ".git").exists():
            return None
        out = subprocess.run(
            ["git", "-C", str(root), "for-each-ref",
             "--sort=-creatordate",
             "--format=%(refname:short)|%(creatordate:short)",
             "refs/tags"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=False, timeout=_GIT_TIMEOUT,
        )
        if out.returncode != 0:
            return None
        tags = []
        for line in out.stdout.splitlines():
            parts = line.split("|")
            name = parts[0].strip() if parts else ""
            date_text = parts[1].strip() if len(parts) > 1 else ""
            if _RELEASE_TAG_RE.match(name):
                tags.append({"tag": name,
                             "date": date_text if _looks_like_date(date_text) else None})
        return tags
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _looks_like_date(value):
    """Return True iff ``value`` is (or parses as) a ``YYYY-MM-DD`` date."""
    return _to_date(value) is not None


# ── Parsing / normalization helpers ────────────────────────────────

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


def _normalize_gates(gates):
    """Return a row-order list of gate dicts (defensive normalization).

    ``gates=None`` → live ``parse_gate_status()`` (the host plan-tracker).
    Non-list input → ``[]`` (nothing to judge — fail-safe). Each dict keeps
    ``gate`` / ``transition`` / ``status`` / ``date`` / ``evidence`` keys;
    missing/odd values degrade to empty strings so later comparisons never
    raise on ragged input (tv Check-31 lesson).
    """
    rows = gates
    if rows is None:
        _resolve_shared()
        rows = parse_gate_status()
    if not isinstance(rows, list):
        return []
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        normalized.append({
            "gate": str(row.get("gate") or ""),
            "transition": str(row.get("transition") or ""),
            "status": str(row.get("status") or ""),
            "date": row.get("date"),
            "evidence": str(row.get("evidence") or ""),
        })
    return normalized


def _normalize_tags(published_tags):
    """Normalize injected tags to ``[{"tag", "date"}, ...]`` (never raises).

    Accepts ``None`` (caller decides live-vs-none), a list of dicts
    ``{"tag": str, "date": optional}``, or a list of plain strings
    (``"v1.6.0"`` — no date). Non-semver entries are dropped. Rows that are
    neither dicts nor strings are skipped.
    """
    if published_tags is None:
        return None
    if not isinstance(published_tags, list):
        return []
    tags = []
    for item in published_tags:
        if isinstance(item, dict):
            name = item.get("tag")
            if not isinstance(name, str):
                continue
            date_val = item.get("date")
            tags.append({"tag": name.strip(),
                         "date": _to_date(date_val).isoformat()
                         if _to_date(date_val) else None})
        elif isinstance(item, str):
            tags.append({"tag": item.strip(), "date": None})
    return tags


def _latest_candidate_tag(tags):
    """Return the HIGHEST-semver release tag (the latest candidate) or None.

    Stale older tags are never judged (design 误报面: multiple version tags
    judge only the latest candidate). Tie on same semver (vX.Y.Z and
    X.Y.Z) keeps the first seen. Non-semver entries are dropped.
    """
    if not tags:
        return None
    best = None
    best_key = None
    for item in tags:
        name = item.get("tag") if isinstance(item, dict) else str(item)
        m = _RELEASE_TAG_RE.match(name or "")
        if not m:
            continue
        key = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if best_key is None or key > best_key:
            best_key = key
            best = {"tag": name,
                    "date": item.get("date") if isinstance(item, dict) else None}
    return best


def _gate_state(status):
    """Canonical state class: ``passed`` | ``passed-on-entry`` | ``pending``.

    ``passed-with-conditions`` is a passed state (evidence recorded — the
    condition risk is gate-consistency's own question, not the interlock's).
    What is NOT passed / passed-on-entry (pending, empty, anything else)
    counts as pending in the conservative interlock — the check cannot
    prove the gate passed. Markdown emphasis (`` `passed-on-entry` `` —
    the tv project's table style) is stripped before classification.
    """
    s = _strip_md(status).strip().lower()
    if s in ("passed", "passed-with-conditions"):
        return "passed"
    if s == "passed-on-entry":
        return "passed-on-entry"
    return "pending"


def _set_verdict(result, verdict, reason):
    result["stats"]["warn_count"] = len(result["warnings"])
    result["stats"]["violation_count"] = len(result["violations"])
    result["verdict"] = verdict
    result["reason"] = reason
    return result


# ── Check 37 ───────────────────────────────────────────────────────

def check_gate_sequence_for_release(gates=None, published_tags=None,
                                    profile=None, lineage_mode="candidate"):
    """FIX-266 / REQ-145.4 (design audit-145-watchdog-design §3.4): Check 37.

    Gate↔release interlock watchdog. A release tag must not exist while any
    prerelease gate (rows before the release gate) is pending or was passed
    after the release happened.

    Signals (verdict ∈ PASS / WARN / FAIL / no-verdict; never raises):
      G-s1  FAIL — published tag exists AND its date is EARLIER than a
          ``passed`` prerelease gate's pass date (or that passed gate has no
          date): release bypassed the still-pending gate. candidate mode
          only; released mode downgrades the same finding to WARN.
      G-s2  FAIL — published tag exists AND any prerelease gate is
          ``pending`` (conservative: ordering unprovable). candidate mode
          FAIL; released mode WARN disclosure.
      G-s3  WARN  — no published tag detectable from git (git unavailable /
          no semver tag) AND the release gate is marked ``passed`` while
          prerelease gates are pending: fail-safe WARN, never FAIL.
      mixed WARN — tag exists but has no parseable date while a ``passed``
          prerelease gate has one: ordering unprovable, fail-safe WARN.
      PASS  — all prereleases are passed-on-entry (on-entry onboarding, no
          real timeline — DEC-153 ④); or no published tag and release gate
          not passed (gate table self-consistent); or tag date >= every
          passed prerelease date (gate passed before release).
      no-verdict — no release gate found (nothing to judge) / no prereleses
          to judge / unsafe input shape.

    Injection surface (all optional; default = live read):
      ``gates``          parse_gate_status()-shaped dict list (row order).
      ``published_tags`` ``[{"tag","date"}]`` (or str-list) — live mode
          derives from ``git for-each-ref`` on HOST_PROJECT_ROOT (FIX-270
          mixed-root fix: facts root, never ROOT).
      ``profile``        accepted for design-signature symmetry — recorded
          in stats only; judgement NEVER hard-codes gate ids per profile
          (standard 11 / lightweight 7 derived by row order).
      ``lineage_mode``   "candidate" (default — G-s1/G-s2 FAIL) or
          "released" (G-s1/G-s2 WARN disclosure, DEC-153 ②). Any other
          value degrades to candidate (fail-safe).

    Returns ``{verdict, reason, violations, warnings, stats}``.
    """
    result = {
        "verdict": "no-verdict",
        "reason": "",
        "violations": [],
        "warnings": [],
        "stats": {
            "gates_scanned": 0,
            "release_gate": None,
            "release_gate_transition": None,
            "prerelease_gates": 0,
            "prerelease_passed": 0,
            "prerelease_on_entry": 0,
            "prerelease_pending": 0,
            "latest_tag": None,
            "latest_tag_date": None,
            "git_available": None,   # True | False | None (git error/degraded)
            "lineage_mode": "candidate",
            "profile": profile,
            "warn_count": 0,
            "violation_count": 0,
        },
    }
    _resolve_shared()

    # ── Fail-safe mode normalization ──
    mode = str(lineage_mode or "candidate").strip().lower()
    if mode not in ("candidate", "released"):
        mode = "candidate"
    result["stats"]["lineage_mode"] = mode

    # ── Gate rows (row order) ──
    # P2-1 (review FIX-266-CODE-R0): the LIVE gate-table read must never
    # raise — a missing or unreadable host plan-tracker degrades to a
    # fail-safe no-verdict entry (risk_domain.py:385-392 precedent), never
    # a FileNotFoundError from parse_gate_status' unguarded read_text (the
    # UnicodeError guard covers the snapshot_domain P1-1 lesson: a non-UTF-8
    # decode is a ValueError subclass the IOError/OSError guard misses).
    rows = gates
    if rows is None:
        if not SAMPLE_PATH.is_file():
            return _set_verdict(
                result, "no-verdict",
                "plan-tracker.md not found — no gate table to judge "
                "(fail-safe no-verdict, P2-1)")
        try:
            rows = parse_gate_status()
        except (IOError, OSError, UnicodeError):
            return _set_verdict(
                result, "no-verdict",
                "plan-tracker.md unreadable — no gate table to judge "
                "(fail-safe no-verdict, P2-1)")
    rows = _normalize_gates(rows)
    result["stats"]["gates_scanned"] = len(rows)

    # ── Release-gate identification: FIRST row whose transition contains
    #    「发布」 (row-order derivation — DEC-153 ①; never a hard-coded id).
    release_idx = None
    release_gate = None
    for idx, row in enumerate(rows):
        if _RELEASE_TRANSITION_MARKER in _strip_md(row["transition"]):
            release_idx = idx
            release_gate = row
            break
    if release_idx is None:
        return _set_verdict(
            result, "no-verdict",
            "no release gate found — no 阶段转换 row contains 「发布」 "
            "(nothing to interlock)")
    result["stats"]["release_gate"] = release_gate["gate"]
    result["stats"]["release_gate_transition"] = release_gate["transition"]

    # ── Prerelease gates: every non-release row BEFORE the release gate ──
    prerelease = [row for row in rows[:release_idx]
                  if _RELEASE_TRANSITION_MARKER not in _strip_md(row["transition"])]
    result["stats"]["prerelease_gates"] = len(prerelease)
    if not prerelease:
        return _set_verdict(
            result, "PASS",
            "release gate {0} has no prerelease gates — no interlock "
            "requirement".format(release_gate["gate"]))

    pending_rows = [r for r in prerelease if _gate_state(r["status"]) == "pending"]
    passed_rows = [r for r in prerelease if _gate_state(r["status"]) == "passed"]
    onentry_rows = [r for r in prerelease
                    if _gate_state(r["status"]) == "passed-on-entry"]
    result["stats"]["prerelease_pending"] = len(pending_rows)
    result["stats"]["prerelease_passed"] = len(passed_rows)
    result["stats"]["prerelease_on_entry"] = len(onentry_rows)

    # ── Published tags (latest candidate only) ──
    injected = published_tags is not None
    tags = _normalize_tags(published_tags)
    if not injected:
        tags = _git_published_tags(HOST_PROJECT_ROOT)
        result["stats"]["git_available"] = tags is not None
    latest = _latest_candidate_tag(tags)
    if latest is not None:
        result["stats"]["latest_tag"] = latest["tag"]
        result["stats"]["latest_tag_date"] = latest["date"]

    # ── Judgement ──
    if latest is None:
        # No published tag detectable (git unavailable / no semver tag).
        # G-s3: only when git cannot confirm AND the release gate is marked
        # passed while prereleases are pending (fail-safe WARN).
        if not pending_rows:
            return _set_verdict(
                result, "PASS",
                "no published release tag and no pending prerelease gate — "
                "gate/release sequence self-consistent (release gate {0})"
                .format(release_gate["gate"]))
        release_passed = _gate_state(release_gate["status"]) == "passed"
        if release_passed:
            pending_names = ", ".join(r["gate"] for r in pending_rows)
            result["warnings"].append({
                "rule": "G-s3",
                "release_gate": release_gate["gate"],
                "pending_gates": pending_names,
                "reason": (
                    "release gate {0} is marked passed while prerelease "
                    "gate(s) {1} are pending, but no published release tag "
                    "is detectable from git — cannot confirm the bypass "
                    "(fail-safe WARN, never FAIL)".format(
                        release_gate["gate"], pending_names)),
            })
            return _set_verdict(
                result, "WARN",
                "release gate {0} passed with pending prerelease gate(s) "
                "{1} and no git-visible release tag (fail-safe WARN)"
                .format(release_gate["gate"], pending_names))
        return _set_verdict(
            result, "PASS",
            "no published release tag and release gate {0} not passed — "
            "no release action to interlock".format(release_gate["gate"]))

    # ── Published tag exists: interlock verdicts ──
    # G-s2 first (conservative, ordering unprovable).
    if pending_rows:
        pending_names = ", ".join(r["gate"] for r in pending_rows)
        finding = {
            "rule": "G-s2",
            "tag": latest["tag"],
            "pending_gates": pending_names,
            "reason": (
                "published release tag {0} exists while prerelease gate(s) "
                "{1} are pending — release bypassed pending gate(s) "
                "(G-s2 conservative: ordering unprovable)".format(
                    latest["tag"], pending_names)),
        }
        if mode == "released":
            finding["reason"] += (
                " [released mode: history disclosure only, no retroactive "
                "FAIL — DEC-153 ②]")
            result["warnings"].append(finding)
            return _set_verdict(
                result, "WARN",
                "published release tag {0} with pending prerelease gate(s) "
                "{1} — historical bypass disclosed (released mode, no FAIL)"
                .format(latest["tag"], pending_names))
        result["violations"].append(finding)
        return _set_verdict(
            result, "FAIL",
            "published release tag {0} bypassed pending gate(s) {1}"
            .format(latest["tag"], pending_names))

    # G-s1: strong-interlock rows (passed, not on-entry) vs tag date.
    # Physical semantics: a release dated BEFORE a gate's pass date (or a
    # passed gate with no date) proves the interlock was bypassed.
    if passed_rows:
        tag_dt = _to_date(latest["date"])
        if tag_dt is None:
            # Tag exists without a parseable date: ordering unprovable —
            # fail-safe WARN (never treat a date gap as a proven bypass).
            passed_names = ", ".join(r["gate"] for r in passed_rows)
            result["warnings"].append({
                "rule": "edge",
                "tag": latest["tag"],
                "passed_gates": passed_names,
                "reason": (
                    "published release tag {0} has no parseable date while "
                    "passed prerelease gate(s) {1} exist — ordering "
                    "unprovable (fail-safe WARN, never FAIL)".format(
                        latest["tag"], passed_names)),
            })
            return _set_verdict(
                result, "WARN",
                "release tag {0} date unknown against passed gate(s) {1} — "
                "ordering unprovable (fail-safe WARN)"
                .format(latest["tag"], passed_names))
        late_passed = [r for r in passed_rows
                       if (_to_date(r["date"]) is None
                           or tag_dt < _to_date(r["date"]))]
        if late_passed:
            names = ", ".join(
                "{0}({1})".format(r["gate"], _date_text(r["date"]))
                for r in late_passed)
            finding = {
                "rule": "G-s1",
                "tag": latest["tag"],
                "tag_date": latest["date"],
                "late_passed_gates": names,
                "reason": (
                    "published release tag {0} ({1}) predates or has no "
                    "proof against passed prerelease gate(s) {2} — release "
                    "bypassed a gate that was not yet passed at release "
                    "time".format(latest["tag"], latest["date"] or "n/a",
                                   names)),
            }
            if mode == "released":
                finding["reason"] += (
                    " [released mode: history disclosure only, no "
                    "retroactive FAIL — DEC-153 ②]")
                result["warnings"].append(finding)
                return _set_verdict(
                    result, "WARN",
                    "published release tag {0} predates passed gate(s) {1} "
                    "— historical bypass disclosed (released mode, no FAIL)"
                    .format(latest["tag"], names))
            result["violations"].append(finding)
            return _set_verdict(
                result, "FAIL",
                "published release tag {0} predates passed gate(s) {1} — "
                "release bypassed a gate that was not yet passed"
                .format(latest["tag"], names))
        return _set_verdict(
            result, "PASS",
            "published release tag {0} ({1}) is on/after every passed "
            "prerelease gate date — gates passed before the release"
            .format(latest["tag"], latest["date"] or "n/a"))

    # No pending, no passed: all passed-on-entry (or none) — DEC-153 ④.
    if onentry_rows:
        return _set_verdict(
            result, "PASS",
            "prerelease gate(s) all passed-on-entry ({0}) — on-entry "
            "onboarding has no real timeline to judge; strong interlock "
            "applies only when a gate is passed (DEC-153 ④)".format(
                ", ".join(r["gate"] for r in onentry_rows)))
    return _set_verdict(
        result, "PASS",
        "release tag {0} exists with no pending or passed prerelease gate "
        "— nothing to interlock".format(latest["tag"]))


def _date_text(value):
    """Render a gate date cell for messages (raw or None-safe)."""
    return str(value) if value else "no-date"


def released_history_version(version):
    """BR-4: True iff ``version`` is an already-published/withdrawn history.

    Parses the host plan-tracker roadmap (reusing change_triage's proven
    header-driven ``parse_version_chain`` — FIX-248 hardening applies) and
    returns True when the version row's status names a terminal release
    state (已发布 / 已撤回 / 失效 / 不可信). Never raises — any parse
    failure degrades to False (the caller keeps candidate semantics, which
    is the safe status-quo default).
    """
    if not version or not isinstance(version, str):
        return False
    try:
        _resolve_shared()
        from change_triage import parse_version_chain  # peer, stdlib-only
        if not SAMPLE_PATH.is_file():
            return False
        plan = SAMPLE_PATH.read_text(encoding="utf-8", errors="replace")
        for row in parse_version_chain(plan):
            if row.get("version") == version:
                status = str(row.get("status") or "")
                return any(marker in status
                           for marker in _RELEASED_HISTORY_STATUS_MARKERS)
    except Exception:
        # Fail-safe: candidate stays the default when the roadmap cannot be
        # parsed — BR-4 never turns a parse hiccup into a verdict change.
        pass
    return False
