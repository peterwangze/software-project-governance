#!/usr/bin/env python3
"""
Loop-health Check — FX-192 (0.65.0 loop-engineering, slice 5).

Implements ADR §9.5:
  Part 1 (BLOCKING): active PausePoint missing velocity_cost_justification → FAIL
  Part 2 (ADVISORY): measured cost > 3× bound for 3 consecutive iterations → warning
                     (promotable to FAIL via ``velocity_check_blocking`` flag,
                     default False)
  DORA bridge (§3.6): deployment frequency / change failure rate advisory metrics

Reads PausePoint declarations from loop-engineering-registry.json (via loop_engine).
Reads flow-unit-runtime.json via deferred verify_workflow import (_vw pattern).

Outputs evidence type: LOOP-HEALTH-{flow_unit_id}-velocity

**Advisory-only status (0.65.0):** this is a STANDALONE CLI
(``check-loop-health``). It is NOT wired into Check 28 (check-governance) and
MUST NOT appear as a blocking sub-item of that gate. ``check_loop_health``
never raises on corrupt/missing inputs. Missing or invalid registry authority
produces a blocking Part 1 finding, while absent runtime data remains an empty
Part 2/DORA result.
"""

import json
from pathlib import Path

# loop_engine is a peer module (no import cycle).
from loop_engine import load_loop_registry, get_pause_point

# ─── Fixed anchors ─────────────────────────────────────────────
PLUGIN_HOME = Path(__file__).resolve().parent.parent

# ─── Deferred verify_workflow import (avoid import cycle) ──────
_VW_CACHE = None


def _vw():
    """Lazy accessor for verify_workflow (deferred to avoid the import cycle).

    loop_health.py MUST NOT import verify_workflow at module top level — that
    would create a cycle (verify_workflow imports this module's check via the
    thin entry). We resolve verify_workflow lazily on first runtime read.
    """
    global _VW_CACHE
    if _VW_CACHE is None:
        import verify_workflow  # noqa: WPS433 deferred import
        _VW_CACHE = verify_workflow
    return _VW_CACHE


def _load_runtime(root=None):
    """Load flow-unit-runtime.json via verify_workflow's loader.

    Returns the parsed dict, or ``None`` if the file is missing or unreadable.
    Never raises — callers rely on a graceful "no data" response.
    """
    try:
        vw = _vw()
        path = vw._flow_unit_runtime_path(root)
    except Exception:  # pragma: no cover - defensive (vw loader shape changed)
        return None
    if path is None or not Path(path).exists():
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Part 1 — BLOCKING: active PausePoint must justify its velocity cost
# (ADR §9.5 part 2 / DEC-097 part 2). Reads the registry ONLY — no runtime.
# ═══════════════════════════════════════════════════════════════════════════


def _check_velocity_justification(plugin_home=None):
    """Part 1 (BLOCKING) — every active PausePoint needs a non-empty justification.

    Iterates PausePoint declarations from loop-engineering-registry.json. For
    each PausePoint whose ``active`` flag is true, verifies that
    ``velocity_cost_justification`` is a non-empty string. Missing/blank
    justification on an active PP is a protocol violation (DEC-097 part 2).

    Fail-closed: a missing, corrupt, or structurally invalid registry produces
    a blocking authority finding. Optional runtime absence is handled
    separately and does not affect this authority check.

    Args:
        plugin_home: Optional plugin-home override forwarded to the loader.

    Returns:
        list of finding dicts, one per violating PausePoint:
        ``{"severity": "FAIL", "pause_point": pp_id, "message": ...}``.
    """
    findings = []
    data, issues = load_loop_registry(plugin_home)
    for issue in issues:
        if issue:
            findings.append({
                "severity": "FAIL",
                "pause_point": "registry-authority",
                "message": (
                    "Loop registry authority unavailable or invalid: {0}"
                ).format(issue),
            })
    if not isinstance(data, dict):
        if findings:
            return findings
        return [{
            "severity": "FAIL",
            "pause_point": "registry-authority",
            "message": (
                "Loop registry authority unavailable or invalid: "
                "loop-engineering registry root must be an object"
            ),
        }]
    pause_points = data.get("pause_points")
    if not isinstance(pause_points, dict):
        return [{
            "severity": "FAIL",
            "pause_point": "registry-authority",
            "message": (
                "Loop registry authority invalid: pause_points must be an object"
            ),
        }]
    if not pause_points:
        return [{
            "severity": "FAIL",
            "pause_point": "registry-authority",
            "message": (
                "Loop registry authority invalid: pause_points must not be empty"
            ),
        }]
    for pp_id, entry in pause_points.items():
        if not isinstance(entry, dict):
            findings.append({
                "severity": "FAIL",
                "pause_point": "registry-authority",
                "message": (
                    "Loop registry authority invalid: pause_points entry {0} "
                    "must be an object"
                ).format(pp_id),
            })
            continue
        if "active" not in entry or not isinstance(entry.get("active"), bool):
            findings.append({
                "severity": "FAIL",
                "pause_point": "registry-authority",
                "message": (
                    "Loop registry authority invalid: pause_points entry {0} "
                    "must declare active as a boolean"
                ).format(pp_id),
            })
            continue
        # Only ACTIVE PausePoints are subject to the justification rule.
        if not entry["active"]:
            continue
        justification = entry.get("velocity_cost_justification")
        if not isinstance(justification, str) or not justification.strip():
            findings.append({
                "severity": "FAIL",
                "pause_point": pp_id,
                "message": (
                    "PP {0} active but velocity_cost_justification missing — "
                    "protocol violation (DEC-097 part 2)"
                ).format(pp_id),
            })
    return findings


# ═══════════════════════════════════════════════════════════════════════════
# Part 2 — ADVISORY: sustained measured-cost exceedance over the declared bound.
# (ADR §9.5 part 2). Needs runtime.json; no-op when runtime data is absent.
# ═══════════════════════════════════════════════════════════════════════════


def _check_velocity_exceedance(
    runtime_data,
    n_multiplier=3,
    m_iterations=3,
    blocking=False,
):
    """Part 2 (ADVISORY) — flag PausePoints whose measured cost blew past 3× bound.

    Rule (ADR §9.5 part 2): if measured ``velocity_cost_ms`` exceeds
    ``n_multiplier`` × declared bound for ``m_iterations`` CONSECUTIVE
    iterations, emit a finding. Severity defaults to ``"ADVISORY"`` but is
    promoted to ``"FAIL"`` when ``blocking=True`` (``velocity_check_blocking``).

    Graceful absence: when runtime_data is ``None`` or carries no per-iteration
    measured-cost samples (the current 0.65.0 state — ``velocity_cost_ms`` is
    null in the registry), this function returns ``[]``. Advisory rules MUST
    NOT fire on missing data.

    Expected runtime shape (per PausePoint), all optional::

        "velocity_history": {
            "PP-X": {
                "declared_bound_ms": 2000,
                "measured_ms": [7000, 7200, 7100]   # per-iteration samples
            }
        }

    Args:
        runtime_data: Parsed flow-unit-runtime.json (or ``None``).
        n_multiplier: Multiplier threshold (default 3 → 3×).
        m_iterations: Consecutive-iteration count required to flag (default 3).
        blocking: When True, promote severity from ADVISORY to FAIL.

    Returns:
        list of finding dicts.
    """
    findings = []
    if not isinstance(runtime_data, dict):
        return findings
    history = runtime_data.get("velocity_history")
    if not isinstance(history, dict):
        return findings

    severity = "FAIL" if blocking else "ADVISORY"
    for pp_id, rec in history.items():
        if not isinstance(rec, dict):
            continue
        bound = rec.get("declared_bound_ms")
        measured = rec.get("measured_ms")
        # Need a numeric bound and a list of numeric samples to evaluate.
        try:
            bound_val = float(bound) if bound is not None else None
        except (TypeError, ValueError):
            bound_val = None
        if bound_val is None or not isinstance(measured, list) or not measured:
            continue
        # Count the trailing run of consecutive samples exceeding the threshold.
        threshold = n_multiplier * bound_val
        consecutive = 0
        for sample in measured:
            try:
                value = float(sample)
            except (TypeError, ValueError):
                # A non-numeric sample breaks the consecutive run.
                consecutive = 0
                continue
            if value > threshold:
                consecutive += 1
            else:
                consecutive = 0
        if consecutive >= m_iterations:
            findings.append({
                "severity": severity,
                "pause_point": pp_id,
                "message": (
                    "PP {0} measured velocity_cost_ms exceeded {1}x declared "
                    "bound for {2} consecutive iterations"
                ).format(pp_id, n_multiplier, consecutive),
            })
    return findings


# ═══════════════════════════════════════════════════════════════════════════
# DORA bridge (§3.6) — deployment frequency / change failure rate advisory.
# Needs runtime.json; returns empty metrics when runtime data is absent.
#
# DEPRECATED in 0.69.0 (ADR-015 §7.3). This is the AUDIT-133-forbidden proxy:
# ``deployment_frequency = release_gate_passes`` (release count as deployment
# frequency) and ``change_failure_rate = fuse_trips / total_loops`` (fuse ratio
# as CFR, with total LOOPS not completed UNITS in the denominator). It is NOT
# deleted in 0.69.0 (two-release deprecation: demoted here, removed in 0.70.0)
# — deletion would be a behavior change to ``check-loop-health`` output that
# downstream readers may parse. The honest replacement is
# :mod:`infra.loop_telemetry` (``compute_metrics``), surfaced via the advisory
# ``telemetry`` key below. Do NOT consume ``dora_metrics_legacy_proxy`` for new
# logic; consume ``telemetry.dora`` instead.
# ═══════════════════════════════════════════════════════════════════════════


def _dora_metrics_legacy_proxy(runtime_data):
    """[DEPRECATED 0.69.0; removed in 0.70.0] Compute the legacy DORA proxy.

    This is the AUDIT-133-forbidden proxy FEAT-008 (ADR-015) replaces. It is
    retained verbatim (behavior-identical to the pre-0.69.0
    ``_compute_dora_metrics``) so existing ``check-loop-health`` consumers that
    read the ``dora_metrics_legacy_proxy`` key keep working for one release
    cycle. New consumers MUST use :mod:`loop_telemetry.compute_metrics`
    instead, surfaced on this envelope under the ``telemetry`` key.

    The honesty defects this function carries (and that the telemetry module
    corrects):

      - ``deployment_frequency`` is set to ``release_gate_passes`` — a RELEASE
        count, not a unit-completion (loop_exit) count. Telemetry's
        ``deployment_frequency`` counts ``loop_exit`` events and is labeled
        "unit-completion frequency".
      - ``change_failure_rate`` = ``fuse_trips / total_loops`` — denominator is
        total LOOPS, not completed UNITS. A unit that iterates 5x then exits is
        one success, not 5. Telemetry's CFR denominator is terminal-event
        units. Returning ``None`` on /0 instead of an explicit ``unknown``
        status collapses "no data" with "zero failures".

    Derives, when the data is present:
      - ``change_failure_rate``: fraction of loops that tripped a fuse
        (e.g. 2 fuse trips out of 5 completed loops → 0.4).
      - ``deployment_frequency``: count of release-gate (G9 / PP-Release-Gate)
        passes recorded, per the window the runtime exposes (advisory raw
        count; callers may normalize per unit time).
      - ``total_loops`` / ``fuse_trips`` / ``release_gate_passes``: raw counts.

    Graceful absence: returns ``{}`` when runtime_data is missing or lacks the
    relevant fields. DORA metrics are advisory and MUST NOT crash on absent
    data.

    Expected runtime shape (all optional)::

        "dora": {
            "total_loops": 5,
            "fuse_trips": 2,
            "release_gate_passes": 1
        }

    Args:
        runtime_data: Parsed flow-unit-runtime.json (or ``None``).

    Returns:
        dict of computed metrics. Empty dict when no data is available.
    """
    if not isinstance(runtime_data, dict):
        return {}
    dora = runtime_data.get("dora")
    if not isinstance(dora, dict):
        return {}

    def _safe_int(key):
        try:
            return int(dora.get(key))
        except (TypeError, ValueError):
            return 0

    total_loops = _safe_int("total_loops")
    fuse_trips = _safe_int("fuse_trips")
    release_passes = _safe_int("release_gate_passes")

    metrics = {
        "total_loops": total_loops,
        "fuse_trips": fuse_trips,
        "release_gate_passes": release_passes,
        "deployment_frequency": release_passes,
    }
    # change_failure_rate = fuse trips / total loops (guard /0).
    if total_loops > 0:
        metrics["change_failure_rate"] = round(fuse_trips / total_loops, 4)
    else:
        metrics["change_failure_rate"] = None
    return metrics


# ═══════════════════════════════════════════════════════════════════════════
# Main entry — composes Part 1 + Part 2 + DORA into one result envelope.
# ═══════════════════════════════════════════════════════════════════════════


def _resolve_event_log_path(root=None):
    """Resolve the loop-event-log.jsonl path for the same host root as runtime.

    Mirrors :func:`verify_workflow._flow_unit_runtime_path`'s root resolution so
    the advisory telemetry reads the SAME host's event log the runtime came
    from (RISK-040: HOST_PROJECT_ROOT, never PLUGIN_HOME). Returns a Path or
    None when verify_workflow's loader is unavailable. Never raises.
    """
    try:
        vw = _vw()
        base = vw._flow_unit_runtime_path(root).parent  # <root>/.governance/
    except Exception:  # pragma: no cover - defensive (vw loader shape changed)
        return None
    return Path(base) / "loop-event-log.jsonl"


def _compute_advisory_telemetry(root=None, window="30d"):
    """Compute the advisory telemetry envelope (FEAT-008, ADR-015 §7.2).

    Reads ``loop-event-log.jsonl`` via :func:`loop_event_log.read_events` and
    computes :func:`loop_telemetry.compute_metrics`. This is ADVISORY only — it
    appears in ``check-loop-health`` output but has no FAIL severity and cannot
    block a release/gate. Wrapped in try/except so an absent/corrupt log or any
    unexpected error yields ``{"status": "unavailable", ...}`` rather than a
    crash (FIX-196 fail-closed discipline on authority is preserved separately
    by Part 1; telemetry absence is NOT an authority failure).

    Args:
        root: host project root (path or str). Defaults to verify_workflow ROOT.
        window: the telemetry window (default ``"30d"``).

    Returns:
        dict with the telemetry report's flow/dora/scope_note, or
        ``{"status": "unavailable", "reason": ...}`` on any failure.
    """
    try:
        from loop_event_log import read_events
        from loop_telemetry import compute_metrics
        log_path = _resolve_event_log_path(root)
        if log_path is None or not Path(log_path).is_file():
            return {
                "status": "unavailable",
                "reason": "event log absent or unreadable",
            }
        events = read_events(log_path=log_path)
        report = compute_metrics(events, window=window)
        return {
            "status": "available",
            "flow": report.flow,
            "dora": report.dora,
            "scope_note": report.scope_note,
            "window": report.window,
            "diagnostics": report.diagnostics,
        }
    except Exception as exc:  # pragma: no cover - defensive; telemetry is advisory
        return {
            "status": "unavailable",
            "reason": "telemetry computation error: {0}".format(exc),
        }


def check_loop_health(
    target=None,
    velocity_check_blocking=False,
    plugin_home=None,
):
    """Run the loop-health Check (ADR §9.5).

    Composes three sub-checks into one result envelope:
      1. Part 1 (BLOCKING) — active PP velocity justification, registry-only.
      2. Part 2 (ADVISORY) — sustained measured-cost exceedance, runtime-only.
      3. DORA bridge — deployment frequency / change failure rate, runtime-only.
         [DEPRECATED 0.69.0 as ``dora_metrics_legacy_proxy``; see §7.3. The
         honest DORA metrics are the advisory ``telemetry`` key (FEAT-008).]

    Advisory-only in 0.65.0: the ``velocity_check_blocking`` flag defaults to
    ``False`` (Part 2 findings are ADVISORY). It is NOT wired into Check 28.

    The ``telemetry`` key (0.69.0) is ADVISORY and non-blocking — it gives
    visibility into the honest flow/DORA metrics without making telemetry a
    gate (ADR-015 §7.2). The legacy ``dora_metrics_legacy_proxy`` key is
    preserved for one release cycle (removed in 0.70.0, ADR-015 §7.3).

    Never raises: corrupt/missing registry yields a blocking authority finding;
    missing runtime yields safe empty Part 2/DORA results; missing/unreadable
    event log yields ``telemetry={"status":"unavailable"}``.

    Args:
        target: Optional host project root (path or str). Used to locate
            ``flow-unit-runtime.json`` via verify_workflow's loader. Defaults
            to the verify_workflow ROOT.
        velocity_check_blocking: When True, promote Part 2 findings from
            ADVISORY to FAIL (default False).
        plugin_home: Optional plugin-home override for registry reads.

    Returns:
        dict with:
          - ``findings``: list of finding dicts (severity / pause_point / message).
          - ``dora_metrics_legacy_proxy``: the DEPRECATED legacy DORA proxy
            (AUDIT-133-forbidden; kept for one release cycle). Carries a
            ``deprecated`` flag + ``deprecation_note``.
          - ``telemetry``: the ADVISORY honest telemetry (FEAT-008); never
            blocks; ``{"status":"unavailable"}`` on absent event log.
          - ``summary``: ``{"blocking_count", "advisory_count"}``.
          - ``no_overclaim_boundary``: human-readable scope statement.
    """
    # Part 1 — registry only (never needs runtime).
    findings = list(_check_velocity_justification(plugin_home))

    # Part 2 + DORA — runtime only; tolerate absence.
    runtime_data = _load_runtime(target)
    findings.extend(
        _check_velocity_exceedance(
            runtime_data, blocking=velocity_check_blocking
        )
    )
    # Legacy DORA proxy — DEPRECATED (ADR-015 §7.3). The try/except reports the
    # deprecation in-place of the fabricated values when the proxy raises, so a
    # consumer reading ``dora_metrics_legacy_proxy`` never sees the proxy's
    # numbers presented as authoritative DORA. The honest metrics are in the
    # advisory ``telemetry`` key below.
    try:
        legacy_proxy = _dora_metrics_legacy_proxy(runtime_data)
        legacy_deprecated = True
        legacy_note = (
            "DEPRECATED in 0.69.0; removed in 0.70.0. Replaced by telemetry.dora "
            "(loop_telemetry.compute_metrics). The values here are the "
            "AUDIT-133-forbidden proxy (release count as deployment frequency; "
            "fuse_trips/total_loops as CFR with LOOPS not UNITS in the "
            "denominator). Use telemetry.dora for honest metrics."
        )
    except Exception as exc:  # pragma: no cover - defensive
        legacy_proxy = {}
        legacy_deprecated = True
        legacy_note = (
            "legacy DORA proxy deprecated, use loop-telemetry (compute_metrics); "
            "proxy raised: {0}".format(exc)
        )
    dora_metrics_legacy_proxy = {
        "metrics": legacy_proxy,
        "deprecated": legacy_deprecated,
        "deprecation_note": legacy_note,
    }

    # Advisory telemetry (FEAT-008, ADR-015 §7.2) — honest metrics from the
    # event log. Non-blocking; never fails the health check.
    telemetry = _compute_advisory_telemetry(root=target)

    blocking_count = sum(1 for f in findings if f.get("severity") == "FAIL")
    advisory_count = sum(1 for f in findings if f.get("severity") != "FAIL")

    return {
        "findings": findings,
        "dora_metrics_legacy_proxy": dora_metrics_legacy_proxy,
        "telemetry": telemetry,
        "summary": {
            "blocking_count": blocking_count,
            "advisory_count": advisory_count,
        },
        "no_overclaim_boundary": (
            "Loop-health Check is advisory-only in 0.65.0; Part 1 (velocity "
            "justification) is the only blocking rule; Part 2 (exceedance) and "
            "DORA metrics require runtime data and fire only when present. "
            "Standalone CLI — NOT a sub-item of Check 28. The 0.69.0 "
            "``telemetry`` key is advisory honest metrics (FEAT-008); "
            "``dora_metrics_legacy_proxy`` is deprecated."
        ),
    }


# Backwards-compat alias for the pre-0.69.0 name (ADR-015 §7.3 keeps the
# function body behavior-identical; tests/consumers that referenced
# ``_compute_dora_metrics`` continue to work during the deprecation window).
_compute_dora_metrics = _dora_metrics_legacy_proxy


if __name__ == "__main__":  # pragma: no cover - manual CLI smoke
    import argparse

    parser = argparse.ArgumentParser(
        description="Loop-health Check (FX-192 / ADR §9.5)."
    )
    parser.add_argument(
        "--target", default=None,
        help="Host project root (defaults to verify_workflow ROOT).",
    )
    parser.add_argument(
        "--velocity-check-blocking", action="store_true",
        help="Promote Part 2 advisory findings to FAIL (default advisory).",
    )
    parser.add_argument(
        "--fail-on-issues", action="store_true",
        help="Exit non-zero if any blocking (FAIL) findings are present.",
    )
    args = parser.parse_args()
    result = check_loop_health(
        target=args.target,
        velocity_check_blocking=args.velocity_check_blocking,
    )
    print("\n=== Loop Health Check (velocity + latency) ===")
    for f in result.get("findings", [])[:25]:
        print("  [{0}] {1}: {2}".format(
            f.get("severity", "?"), f.get("pause_point", ""), f.get("message", "")
        ))
    summary = result.get("summary", {})
    print("\n  Result: {0} BLOCKING, {1} advisory".format(
        summary.get("blocking_count", 0), summary.get("advisory_count", 0)
    ))
    dora_legacy = result.get("dora_metrics_legacy_proxy") or {}
    dora = dora_legacy.get("metrics") or {}
    if dora:
        cfr = dora.get("change_failure_rate")
        cfr_disp = "n/a" if cfr is None else "{0:.2f}".format(cfr)
        print("  DORA [LEGACY PROXY, deprecated]: deployments={0} fuse_trips={1} CFR={2}".format(
            dora.get("release_gate_passes", 0),
            dora.get("fuse_trips", 0),
            cfr_disp,
        ))
    telemetry = result.get("telemetry") or {}
    if telemetry.get("status") == "available":
        td = telemetry.get("dora", {})
        cfr2 = td.get("change_failure_rate")
        cfr2_val = cfr2.value if hasattr(cfr2, "value") else None
        cfr2_disp = cfr2_val if cfr2_val is not None else "unknown"
        df = td.get("deployment_frequency")
        df_val = df.value if hasattr(df, "value") else None
        df_disp = df_val if df_val is not None else "unknown"
        print("  Telemetry [FEAT-008, honest]: unit-completions={0} CFR={1} window={2}".format(
            df_disp, cfr2_disp, telemetry.get("window"),
        ))
    print()
    if args.fail_on_issues and summary.get("blocking_count", 0) > 0:
        raise SystemExit(1)
