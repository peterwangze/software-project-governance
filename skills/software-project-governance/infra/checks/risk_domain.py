"""Risk-domain checks — extracted from verify_workflow.py in 0.70.0.

Scope (DEC-083 Phase 5b / ADR-016 / FEAT-009): the risk-staleness check
(Check 2) and risk-escalation check (Check 8), plus their risk-only parsing
helpers (`parse_open_risks`, `_parse_context_open_risks`).

This module owns the risk check domain. Shared helpers and constants still
defined in verify_workflow.py (`RISK_PATH`, `_context_file`, `_context_task`,
`_governance_table_cells`) are reached through a deferred module reference
rather than a top-level import, so verify_workflow.py can import this module
at module load time without an import cycle.

Functions with cross-domain callers (`_risk_status_is_closed` is used by the
release-blockers check; `_check_risk_has_closed` is used by gate auto-judge)
STAY in verify_workflow.py and are reached via the deferred accessor — they
are not duplicated here (ADR-016 §3.2 / §4.3 KEEP rule).

See docs/architecture/ADR-016-verify-phase5-extraction-0.70.0.md for the
design and the line-number baseline used during extraction.
"""

import re
from datetime import date, datetime

# ── Shared-helper access (deferred to avoid import cycle) ──────────
# Same deferred-_vw() pattern as checks.manifest (Phase 1) and
# checks.capability_registry (Phase 2). The shared names are resolved lazily
# on the first call into this module (after verify_workflow has finished
# loading) and cached in this module's globals for subsequent calls, so the
# moved function bodies can reference them by bare name unchanged.

_VW_CACHE = None


def _vw():
    """Return the verify_workflow module (imported lazily, cached).

    Cached so repeated calls reuse the same module reference (REVIEW-FIX-153
    P2, same pattern as checks.manifest / checks.capability_registry).
    """
    global _VW_CACHE
    if _VW_CACHE is None:
        import verify_workflow  # noqa: WPS433 (deferred import on purpose)
        _VW_CACHE = verify_workflow
    return _VW_CACHE


# Shared names this domain reaches back into verify_workflow for. Refreshed
# on every call into `_resolve_shared()` (NOT cached) so test-time monkey-
# patching of verify_workflow attributes propagates, and so the moved
# function bodies can reference them by bare name (byte-identical bodies,
# per ADR-016 §5.3 "no behavioral change").
_SHARED_NAMES = (
    "RISK_PATH",
    "_context_file",
    "_context_task",
    "_governance_table_cells",
)


def _resolve_shared():
    """Refresh this module's globals with shared names from verify_workflow.

    Re-fetches on EVERY call (not cached) so test-time monkey-patching of
    verify_workflow attributes (e.g. `patch.object(vw, "RISK_PATH", ...)`)
    propagates into this module's bare-name lookups. The cost is negligible:
    these checks run once per CLI invocation, not in a hot loop, and `getattr`
    on a cached module reference is cheap. This mirrors how checks.manifest
    re-resolves `ROOT = _root()` inside each function body (Phase 1 precedent).
    """
    vw = _vw()
    g = globals()
    for _name in _SHARED_NAMES:
        g[_name] = getattr(vw, _name)


# ── Domain constants and functions (moved verbatim from verify_workflow.py) ──

# Canonical "open risk" predicate for the risk domain (FIX-270 R0 F3).
# The whole domain (parse_open_risks / check_risk_staleness / check_risk_escalation
# — and the status fast path's parse_active_risks) shares ONE judgement: a risk
# is active/open iff its 当前状态 cell is exactly ``打开``. Non-open states
# (缓解完成 / 已关闭 / resolved / 降级 / 已接受…) are the risk state-machine's
# closed or in-flight terminal states and MUST NOT be counted as open — no
# parallel marker sets.
def is_risk_status_open(status):
    """Return True iff the risk status cell is the domain-canonical ``打开``."""
    return (status or "").strip() == "打开"


def _parse_context_open_risks(root):
    _resolve_shared()
    risk_path = _context_file(root, ".governance/risk-log.md")
    if not risk_path.is_file():
        return []
    risks = []
    for line in risk_path.read_text(encoding="utf-8").split("\n"):
        stripped = line.strip()
        if not stripped.startswith("| RISK-"):
            continue
        cells = _governance_table_cells(stripped)
        if len(cells) < 9:
            continue
        status = cells[8]
        if not is_risk_status_open(status):
            continue
        risks.append(_context_task(
            cells[0],
            cells[2] if len(cells) > 2 else cells[0],
            status,
            ".governance/risk-log.md",
            stripped,
            kind="risk",
        ))
    return risks


def parse_open_risks():
    """Return list of (risk_id, date_str) for open risks."""
    _resolve_shared()
    if not RISK_PATH.is_file():
        return []
    content = RISK_PATH.read_text(encoding="utf-8")
    risks = []
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| RISK-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 10:
            risk_id = parts[1]
            date_str = parts[2]
            status = parts[9]
            if is_risk_status_open(status):
                risks.append((risk_id, date_str))
    return risks


def check_risk_staleness():
    """Check for open risks older than 7 days."""
    _resolve_shared()
    risks = parse_open_risks()
    today = date.today()
    stale = []
    fresh = []
    for risk_id, date_str in risks:
        try:
            risk_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            age = (today - risk_date).days
            if age > 7:
                stale.append((risk_id, date_str, age))
            else:
                fresh.append((risk_id, date_str, age))
        except ValueError:
            stale.append((risk_id, date_str, -1))
    return {
        "total_open": len(risks),
        "stale": stale,
        "fresh": fresh,
    }


def check_risk_escalation():
    """Check for open risks whose escalation deadline has passed.

    Per AUDIT-045: risk-log defines Owner + escalation deadline + mitigation action,
    but when the deadline passes, nothing enforces the escalation.
    This function detects open risks with passed deadlines — the external validation
    counterpart to the risk escalation MUST rule.

    Returns: dict with escalated risks list and summary stats.
    """
    _resolve_shared()
    if not RISK_PATH.is_file():
        return {
            "escalated": [],
            "total_open": 0,
        }

    content = RISK_PATH.read_text(encoding="utf-8")
    today = date.today()
    escalated = []
    all_open = []

    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| RISK-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 13:
            continue

        risk_id = parts[1]
        date_str = parts[2]          # 日期
        status = parts[9]            # 当前状态
        deadline_str = parts[11]     # 截止日期

        if not is_risk_status_open(status):
            continue

        all_open.append(risk_id)

        if not deadline_str or deadline_str == "":
            continue

        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            if today > deadline:
                escalated.append({
                    "risk_id": risk_id,
                    "created": date_str,
                    "deadline": deadline_str,
                    "days_overdue": (today - deadline).days,
                })
        except ValueError:
            continue

    return {
        "escalated": escalated,
        "total_open": len(all_open),
        "escalation_count": len(escalated),
    }


