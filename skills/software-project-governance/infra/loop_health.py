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
# ═══════════════════════════════════════════════════════════════════════════


def _compute_dora_metrics(runtime_data):
    """Compute advisory DORA-bridge metrics from runtime data (ADR §3.6).

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

    Advisory-only in 0.65.0: the ``velocity_check_blocking`` flag defaults to
    ``False`` (Part 2 findings are ADVISORY). It is NOT wired into Check 28.

    Never raises: corrupt/missing registry yields a blocking authority finding;
    missing runtime yields safe empty Part 2/DORA results.

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
          - ``dora_metrics``: computed DORA metrics (may be empty).
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
    dora_metrics = _compute_dora_metrics(runtime_data)

    blocking_count = sum(1 for f in findings if f.get("severity") == "FAIL")
    advisory_count = sum(1 for f in findings if f.get("severity") != "FAIL")

    return {
        "findings": findings,
        "dora_metrics": dora_metrics,
        "summary": {
            "blocking_count": blocking_count,
            "advisory_count": advisory_count,
        },
        "no_overclaim_boundary": (
            "Loop-health Check is advisory-only in 0.65.0; Part 1 (velocity "
            "justification) is the only blocking rule; Part 2 (exceedance) and "
            "DORA metrics require runtime data and fire only when present. "
            "Standalone CLI — NOT a sub-item of Check 28."
        ),
    }


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
    dora = result.get("dora_metrics") or {}
    if dora:
        cfr = dora.get("change_failure_rate")
        cfr_disp = "n/a" if cfr is None else "{0:.2f}".format(cfr)
        print("  DORA: deployments={0} fuse_trips={1} CFR={2}".format(
            dora.get("release_gate_passes", 0),
            dora.get("fuse_trips", 0),
            cfr_disp,
        ))
    print()
    if args.fail_on_issues and summary.get("blocking_count", 0) > 0:
        raise SystemExit(1)
