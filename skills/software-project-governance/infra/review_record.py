"""Review-record writer + Wiring A (FIX-236.1 / ADR-017 §3.2, §3.4).

The **single machine-written review-conclusion persistence path** (P1-1
anchor): ``review-record`` CLI (verify_workflow.py thin entry) delegates here.
It writes ``review-{id}-R{n}.md`` + an evidence-log row in the Check 30
(V1~V5) parseable contract, and then, when a review→unit/gate mapping
resolves, invokes :func:`loop_gate_processor.process_gate_result` as Wiring A
(thin call, ADR-014 §6.1).

Behavior contract (ADR-017 §3.4):

  - **Machine write**: review file + evidence row are written FIRST and
    independently of the loop state machine. A wiring failure (CAS conflict /
    lock / exception) must NEVER block the review record — it is recorded as a
    ``degraded`` marker in the wiring summary.
  - **Mapping is data, not logic**: review role → gate_id is a module-level
    registry-side table (:data:`REVIEW_GATE_MAPPING`, documented defaults for
    the ADR-014 §6.1 examples). When no mapping resolves (or no flow-unit id),
    wiring is SKIPPED with a WARN reason — the review record still lands.
  - **复审必达**: a NEEDS_CHANGE record carries the structured revisit fields
    ``next_round=REVIEW-{id}-R{n+1}`` + ``prev_report`` so Check 30 V6 and the
    Coordinator can verify / spawn the R+1 revisit.
  - **审查结论必机录 (FIX-260 / REQ-107)**: calling this CLI is a MUST for
    every Reviewer conclusion (behavior-protocol.md M7.4 step 4.6 C8; the
    M1.2 fast lane no longer exempts handwritten REVIEW rows). Check 30c
    (``check_review_machine_provenance``) WARNs on REVIEW rows/files dated
    on/after 2026-08-22 that lack the machine markers emitted here — the
    gradual-FAIL escalation path is registered in the FIX-260 decision log.
  - **loop_exit → next-unit bridge**: when the wiring outcome is ``exit``,
    :func:`loop_exit_bridge.refresh_candidates` is invoked best-effort so the
    next-unit candidate snapshot stays fresh (FIX-236.3 consumer).

This module is product code (Governance Developer domain) and stays
import-cycle-free: it imports loop_gate_processor (peer) and loop_exit_bridge
(peer, pure) lazily inside the exit-refresh path.
"""

import re
from datetime import date
from pathlib import Path

from loop_gate_processor import process_gate_result  # noqa: F401 (re-exported)


# Registry-side mapping data (not logic): review role → default gate_id.
# Only the ADR-014 §6.1 documented mappings are declared; other roles require
# explicit --unit/--gate (mapping-missing → WARN skip). Promoted to
# core/loop-engineering-registry.json in a later phase.
REVIEW_GATE_MAPPING = {
    "CODE": "G6",      # code-review → G6 (inner-loop exit)
    "DESIGN": "G5",    # design-review → G5 (middle-loop entry)
    "RELEASE": "G9",   # release-review → G9 (middle-loop exit)
}

# Wiring B data (FIX-236.2 / ADR-017 §3.4): gate-engine verdict → review
# conclusion. Lives here (registry-side data), NOT in verify_workflow.py —
# the auto_judge_gate wiring is a thin call over this mapping. "needs_human"
# is deliberately absent: no verdict is rendered, so no wiring happens.
GATE_VERDICT_TO_RESULT = {
    "passed": "APPROVED",
    "passed-with-conditions": "APPROVED_WITH_NOTES",
    "blocked": "NEEDS_CHANGE",
}

_ROLE_TOKEN_RE = re.compile(r"(?:^|[_-])(CODE|DESIGN|RELEASE)(?:[_-]|$)")
_TASK_ID_RE = re.compile(r"^[A-Z]+-\d+$")
_RESULT_RE = re.compile(
    r"^(APPROVED|APPROVED_WITH_NOTES|NEEDS_CHANGE|BLOCKED)$", re.IGNORECASE)


def _detect_role(task_id, report_path):
    """Best-effort review-role detection from the task id / report filename.

    Returns an upper-case role token (e.g. ``CODE``) or None. Only used when
    the caller did not pass an explicit ``--unit``/``--gate``; the mapping is
    registry-side data, so an undetected role is NOT an error.
    """
    blob = " ".join([task_id or "", Path(report_path).name if report_path else ""])
    m = _ROLE_TOKEN_RE.search(blob.upper())
    return m.group(1) if m else None


def resolve_wiring(task_id, report_path=None, *, unit_id=None, gate_id=None):
    """Resolve the review→unit/gate wiring (data-driven, never raises).

    Explicit ``unit_id`` + ``gate_id`` win. Otherwise the role token (from
    task id / report filename) is looked up in :data:`REVIEW_GATE_MAPPING`.

    Returns a dict: ``{"resolved": bool, "unit_id": ..., "gate_id": ...,
    "role": ..., "reason": str}``. ``resolved=False`` → the caller skips the
    wiring with a WARN (the review record still lands).
    """
    if unit_id and gate_id:
        return {
            "resolved": True,
            "unit_id": unit_id,
            "gate_id": gate_id,
            "role": _detect_role(task_id, report_path),
            "reason": "explicit --unit/--gate",
        }
    role = _detect_role(task_id, report_path)
    if not role:
        return {
            "resolved": False,
            "unit_id": None,
            "gate_id": None,
            "role": None,
            "reason": (
                "no review→gate mapping resolved (role token not found in "
                "task id / report path; registry data missing — pass "
                "--unit/--gate to wire)"
            ),
        }
    gate_id = REVIEW_GATE_MAPPING.get(role)
    if not gate_id:
        return {
            "resolved": False,
            "unit_id": None,
            "gate_id": None,
            "role": role,
            "reason": (
                "no review→gate mapping for role {0!r} (registry data missing "
                "— pass --unit/--gate to wire)".format(role)
            ),
        }
    if not unit_id:
        return {
            "resolved": False,
            "unit_id": None,
            "gate_id": gate_id,
            "role": role,
            "reason": (
                "role {0!r} maps to gate {1} but no flow-unit id is available "
                "(pass --unit or register a unit mapping)".format(role, gate_id)
            ),
        }
    return {
        "resolved": True,
        "unit_id": unit_id,
        "gate_id": gate_id,
        "role": role,
        "reason": "registry role→gate mapping",
    }


def wiring_summary(outcome):
    """Normalize a :class:`GateOutcome` into the wiring summary dict shape.

    P2-1 (Code Review R1): ``wired`` reflects whether the CAS write actually
    committed (``outcome.success``), NOT merely that process_gate_result was
    invoked. A v1/classic no-op (status=illegal) or a missing-runtime error
    (status=error) is therefore NOT ``wired`` — the status/reason are still
    preserved for diagnosis.
    """
    return {
        "wired": bool(outcome.success),
        "degraded": False,
        "decision": outcome.decision,
        "status": outcome.status,
        "reason": outcome.reason,
        "loop_count": outcome.new_loop_count,
    }


def _wire_to_loop(task_id, round_n, result, review_file, reviewer, report_path,
                  unit_id, gate_id, root, runtime_file, plugin_home):
    """Wiring A (ADR-017 §3.4): thin process_gate_result invocation, best-effort.

    Thin delegation (ADR-014 §6 principle). Never raises; every failure mode
    (mapping missing / process_gate_result error / exception) is reported in
    the returned dict and must NOT block the review record.
    """
    evidence_ref = review_file.name if review_file is not None else (
        "review-{0}-R{1}.md".format(task_id, round_n))
    actor = reviewer or "review-record"
    mapping = resolve_wiring(task_id, report_path,
                             unit_id=unit_id, gate_id=gate_id)
    if not mapping["resolved"]:
        return {
            "wired": False,
            "degraded": False,
            "unit_id": mapping["unit_id"],
            "gate_id": mapping["gate_id"],
            "reason": mapping["reason"],
        }
    try:
        outcome = process_gate_result(
            mapping["unit_id"], mapping["gate_id"], result,
            evidence_ref=evidence_ref, actor=actor,
            root=root, runtime_file=runtime_file, plugin_home=plugin_home,
        )
        summary = wiring_summary(outcome)
        summary["unit_id"] = mapping["unit_id"]
        summary["gate_id"] = mapping["gate_id"]
        return summary
    except Exception as exc:  # noqa: BLE001 — best-effort degrade, never raise
        return {
            "wired": False,
            "degraded": True,
            "unit_id": mapping["unit_id"],
            "gate_id": mapping["gate_id"],
            "reason": "process_gate_result raised: {0}".format(exc),
        }


def _review_file_text(task_id, round_n, result, reviewer, report_path,
                      date_str, wiring_note):
    """Machine-written review record markdown (Check 30 file-scan parseable)."""
    lines = [
        "# Review Record (machine-written by review-record)",
        "",
        "- task: {0}".format(task_id),
        "- round: R{0}".format(round_n),
        "- date: {0}".format(date_str),
        "- reviewer: {0}".format(reviewer or "unknown"),
        "- report: {0}".format(report_path),
        "- wiring: {0}".format(wiring_note),
        "",
        "**审查结论**: **{0}**".format(result),
    ]
    if result == "APPROVED_WITH_NOTES":
        lines.append("")
        lines.append("unresolved_blockers=0")
    if result == "NEEDS_CHANGE":
        lines.append("")
        lines.append("## 复审必达（NEEDS_CHANGE）")
        lines.append("")
        lines.append("- next_round: REVIEW-{0}-R{1}".format(task_id, round_n + 1))
        lines.append("- prev_report: {0}".format(report_path))
    lines.append("")
    return "\n".join(lines)


def _evidence_row(task_id, round_n, result, reviewer, report_path,
                  review_file_name, date_str):
    """Evidence-log row in the Check 30 live-scan contract.

    Column shape mirrors existing rows: | id | task_ref | type | description |
    basis | artifacts | actor | date | gate | conclusion [| blocker token].
    The description intentionally carries NO ISO date and NO conclusion token
    so the live collector's first-match scan lands on the real columns.
    """
    cells = [
        "REVIEW-{0}-R{1}".format(task_id, round_n),
        task_id,
        "治理记录",
        "review-record CLI 机器写入 review 结论记录（round {0}）".format(round_n),
        "事实依据：review-record 输出摘要（机器写入）",
        "{0}; {1}".format(report_path, review_file_name),
        reviewer or "unknown",
        date_str,
        "G11",
        result,
    ]
    if result == "APPROVED_WITH_NOTES":
        cells.append("unresolved_blockers=0")
    return "| " + " | ".join(cells) + " |\n"


def write_review_record(
    *,
    task_id,
    round_n,
    result,
    report_path,
    reviewer=None,
    unit_id=None,
    gate_id=None,
    root=None,
    evidence_dir=None,
    runtime_file=None,
    plugin_home=None,
    actor=None,
):
    """Persist one review conclusion + Wire A (FIX-236.1).

    Args:
        task_id: task id of the reviewed artifact (e.g. ``FIX-236``).
        round_n: review round (0-based; R0 is the first review).
        result: ``APPROVED`` | ``APPROVED_WITH_NOTES`` | ``NEEDS_CHANGE`` |
            ``BLOCKED``.
        report_path: path of the reviewer's full report (embedded in the
            record and reused as prev_report for the R+1 revisit).
        reviewer: reviewer/agent name (also the loop actor when given).
        unit_id / gate_id: explicit flow-unit wiring (overrides the registry
            mapping).
        root: host project root — review file + evidence row land under
            ``<root>/.governance`` (RISK-040: never PLUGIN_HOME).
        evidence_dir: explicit governance dir override (tests); defaults to
            ``root/.governance``.
        runtime_file: explicit flow-unit-runtime.json path forwarded to the
            wiring (tests / hosts where the runtime is not under root).
        plugin_home: forwarded to registry reads in process_gate_result.
        actor: loop actor override (defaults to reviewer or "review-record").

    Returns:
        dict summary: review_id, review_file, evidence_row, wiring {...},
        revisit_required / next_round / prev_report (NEEDS_CHANGE only), and
        ``error`` (fail-closed) when inputs are invalid. Never raises.
    """
    # Input validation (fail-closed).
    if not _TASK_ID_RE.match(str(task_id or "")):
        return {"error": "task_id must match PREFIX-NNN (e.g. FIX-236)"}
    try:
        round_n = int(round_n)
    except (TypeError, ValueError):
        return {"error": "round_n must be an integer"}
    if round_n < 0:
        return {"error": "round_n must be >= 0"}
    result_norm = str(result or "").strip().upper()
    if not _RESULT_RE.match(result_norm):
        return {"error": (
            "result must be APPROVED | APPROVED_WITH_NOTES | NEEDS_CHANGE | "
            "BLOCKED (got {0!r})".format(result))}
    if not report_path:
        return {"error": "report_path is required"}

    # Resolve destinations.
    if evidence_dir is None:
        if root is None:
            return {"error": "root or evidence_dir is required"}
        evidence_dir = Path(root) / ".governance"
    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    review_id = "REVIEW-{0}-R{1}".format(task_id, round_n)
    review_file = evidence_dir / "review-{0}-R{1}.md".format(task_id, round_n)
    evidence_path = evidence_dir / "evidence-log.md"
    today = date.today().isoformat()

    # 1. Machine-write the review record (independent of the loop wiring).
    review_text = _review_file_text(
        task_id, round_n, result_norm, reviewer, report_path, today, "pending")
    try:
        review_file.write_text(review_text, encoding="utf-8")
    except OSError as exc:
        return {"error": "cannot write review file: {0}".format(exc)}

    row = _evidence_row(
        task_id, round_n, result_norm, reviewer, report_path,
        review_file.name, today)
    try:
        with evidence_path.open("a", encoding="utf-8") as fh:
            fh.write("\n" + row)
    except OSError as exc:
        return {"error": "cannot append evidence row: {0}".format(exc)}

    # 2. Wiring A (best-effort; never blocks the record).
    wiring = _wire_to_loop(
        task_id, round_n, result_norm, review_file, reviewer or actor,
        report_path,
        unit_id, gate_id, root, runtime_file, plugin_home)

    # 3. loop_exit → next-unit bridge (best-effort consumer).
    if wiring.get("wired") and wiring.get("decision") == "exit" and root is not None:
        try:
            from loop_exit_bridge import refresh_candidates  # deferred (peer)
            refresh_candidates(Path(root))
        except Exception:  # noqa: BLE001 — bridge refresh must never block
            pass

    summary = {
        "review_id": review_id,
        "task_id": task_id,
        "round": round_n,
        "result": result_norm,
        "review_file": str(review_file),
        "evidence_row_written": True,
        "wiring": wiring,
        "revisit_required": result_norm == "NEEDS_CHANGE",
    }
    if result_norm == "NEEDS_CHANGE":
        summary["next_round"] = "REVIEW-{0}-R{1}".format(task_id, round_n + 1)
        summary["prev_report"] = str(report_path)
    return summary


__all__ = [
    "REVIEW_GATE_MAPPING",
    "GATE_VERDICT_TO_RESULT",
    "resolve_wiring",
    "wiring_summary",
    "write_review_record",
    "process_gate_result",
]
