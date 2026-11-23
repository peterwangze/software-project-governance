"""Check completion evidence against machine recommendation snapshots and run priority analysis."""

import re
from datetime import date


REQ108_RECOMMENDATION_DATE = date(2026, 8, 22)
RECO_ROW_MARKER = "task-priority-analysis 机器写入完成必推荐调用快照"
_LEGACY_SNAPSHOT_MARKER = "完成必推荐调用快照"
_RECO_TASK_ID_RE = re.compile(r"^[A-Z]+-\d+$")
_SNAPSHOT_REF_RE = re.compile(r"(?:RECO-[A-Z]+-\d+|EVD-\d+)")


def _recommendation_snapshot_row_text(task_id, report, date_str):
    """FIX-262 row text — thin alias; canonical home is
    task_priority.recommendation_snapshot_row_text (moved there by FEAT-012
    G5 so the writer, duplicate detector and row schema live in one module;
    alias kept for existing engine/test consumers)."""
    from task_priority import recommendation_snapshot_row_text
    return recommendation_snapshot_row_text(task_id, report, date_str)


def _write_recommendation_snapshot(task_id, report, evidence_path=None, *, inputs):
    """FIX-262 append — thin alias; canonical home is
    task_priority.write_recommendation_snapshot (FEAT-012 G5). Supplies the
    rebinding-aware EVIDENCE_PATH default the pure module cannot know."""
    from task_priority import write_recommendation_snapshot
    return write_recommendation_snapshot(
        task_id, report,
        evidence_path if evidence_path is not None else inputs.evidence_path)


def check_completion_recommendation(evidence_rows=None, snapshot_text=None, *, inputs):
    """FIX-262 / REQ-108: Check 34 — completion-recommendation closure.

    S1 (core, FAIL): a product-code COMPLETION evidence row (id ``EVD-*``,
    type ``产品代码``) dated on/after ``REQ108_RECOMMENDATION_DATE`` whose
    task has no associated recommendation-snapshot row. Association = a
    machine ``RECO-{task}`` row (marker ``task-priority-analysis 机器写入``)
    OR a legacy snapshot row (description marker ``完成必推荐调用快照``)
    whose task_ref column or “{task} 完成触发” description binds the task.

    S2 (WARN, gradual): the session-snapshot ``## 下次会话优先级`` section
    has entries but references no snapshot id (``RECO-*`` / ``EVD-*``) —
    the section is not verifiably derived from a snapshot (signal 4).

    S3 (FAIL): a referenced snapshot id does not exist in the evidence log
    (dangling derivation anchor).

    Returns ``{verdict, reason, violations, warnings, stats}``; verdict ∈
    PASS / WARN / FAIL / no-verdict. Never raises.
    """
    result = {
        "verdict": "no-verdict",
        "reason": "",
        "violations": [],
        "warnings": [],
        "stats": {"completions_judged": 0, "snapshots_machine": 0,
                  "snapshots_legacy": 0, "snapshot_section": "absent"},
    }

    rows = evidence_rows
    if rows is None:
        rows = []
        if inputs.evidence_path.is_file():
            try:
                content = inputs.evidence_path.read_text(encoding="utf-8")
            except (IOError, OSError):
                content = ""
            rows = [ln for ln in content.split("\n") if ln.strip().startswith("|")]

    if snapshot_text is None:
        snapshot_text = ""
        # Live snapshot read ONLY in full live mode (evidence_rows also None):
        # a rows-fixture run without an explicit snapshot_text means "no
        # snapshot section to judge", not "read the repo's live snapshot".
        if evidence_rows is None and inputs.snapshot_path.is_file():
            try:
                snapshot_text = inputs.snapshot_path.read_text(encoding="utf-8")
            except (IOError, OSError):
                snapshot_text = ""

    def _row_date(parts):
        for part in parts[3:]:
            if inputs.match(r"^\d{4}-\d{2}-\d{2}$", part):
                try:
                    return inputs.parse_date(part)
                except ValueError:
                    return None
        return None

    # Pass 1: collect snapshot associations + evidence ids.
    known_ids = set()
    assoc = set()  # task ids that have a snapshot association
    for raw in rows:
        parts = [p.strip() for p in str(raw or "").split("|")]
        if len(parts) < 5:
            continue
        row_id = parts[1]
        if row_id:
            known_ids.add(row_id)
        desc = parts[4] if len(parts) > 4 else ""
        is_machine = row_id.startswith("RECO-") and inputs.machine_marker in desc
        is_legacy = inputs.legacy_marker in desc
        if not (is_machine or is_legacy):
            continue
        if is_machine:
            result["stats"]["snapshots_machine"] += 1
        else:
            result["stats"]["snapshots_legacy"] += 1
        # task_ref column binding (parts[2]) — may carry "FIX-260, FIX-261".
        for tid in inputs.task_id_pattern.findall(parts[2] or ""):
            assoc.add(tid)
        # description trigger binding（"FIX-256 完成触发" — EVD-898 pattern).
        for tid in inputs.task_id_pattern.findall(desc):
            if "{0} 完成触发".format(tid) in desc:
                assoc.add(tid)
        # machine row id binding: RECO-{task}.
        if is_machine:
            m = inputs.match(r"^RECO-([A-Z]+-\d+)$", row_id)
            if m:
                assoc.add(m.group(1))

    # Pass 2: completion rows → S1.
    for raw in rows:
        parts = [p.strip() for p in str(raw or "").split("|")]
        if len(parts) < 5:
            continue
        row_id = parts[1]
        if not row_id.startswith("EVD-"):
            continue  # REVIEW-/TRIAGE-/RECO- rows are not completion rows.
        if (parts[3] if len(parts) > 3 else "") != "产品代码":
            continue
        row_date = _row_date(parts)
        if row_date is None or row_date < inputs.effective_date:
            continue
        result["stats"]["completions_judged"] += 1
        for tid in inputs.task_id_pattern.findall(parts[2] or ""):
            if tid not in assoc:
                result["violations"].append({
                    "rule": "S1",
                    "task_id": tid,
                    "reason": "completed product-code task {0} (evidence "
                              "{1}, {2}) has no recommendation-snapshot "
                              "row — M7.4 step 6 requires the "
                              "task-priority-analysis snapshot (machine "
                              "RECO row via --evidence-task, or a "
                              "完成必推荐调用快照 row)".format(
                                  tid, row_id, row_date.isoformat()),
                })

    # Signal 4: snapshot section derivation (S2/S3).
    section_lines = []
    in_section = False
    for line in (snapshot_text or "").split("\n"):
        if line.strip().startswith("## "):
            in_section = line.strip() == "## 下次会话优先级"
            continue
        if in_section and line.strip():
            section_lines.append(line.strip())
    if section_lines:
        result["stats"]["snapshot_section"] = "present"
        blob = "\n".join(section_lines)
        refs = set(inputs.snapshot_pattern.findall(blob))
        if not refs:
            result["warnings"].append({
                "rule": "S2",
                "task_id": "",
                "reason": "session-snapshot ## 下次会话优先级 has entries but "
                          "references no snapshot id (RECO-*/EVD-*) — not "
                          "verifiably derived from a recommendation snapshot "
                          "(REQ-108 signal 4; gradual WARN)",
            })
        else:
            dangling = sorted(r for r in refs if r not in known_ids)
            if dangling:
                result["violations"].append({
                    "rule": "S3",
                    "task_id": "",
                    "reason": "snapshot section references missing evidence "
                              "id(s): {0} — dangling derivation anchor".format(
                                  ", ".join(dangling)),
                })

    if result["violations"]:
        result["verdict"] = "FAIL"
        result["reason"] = "{0} completion-recommendation violation(s)".format(
            len(result["violations"]))
    elif result["warnings"]:
        result["verdict"] = "WARN"
        result["reason"] = "{0} derivation warning(s)".format(
            len(result["warnings"]))
    elif result["stats"]["completions_judged"] == 0:
        result["verdict"] = "no-verdict"
        result["reason"] = (
            "no product-code completion row dated on/after {0} — Check 34 "
            "has nothing to judge".format(
                inputs.effective_date.isoformat()))
    else:
        result["verdict"] = "PASS"
        result["reason"] = (
            "{0} completion(s) all carry recommendation snapshots".format(
                result["stats"]["completions_judged"]))
    return result


def cmd_task_priority_analysis(args, *, inputs):
    """Thin entry — delegates to infra/task_priority.py (FIX-226 / FEAT-012 G5).

    Reads .governance paths via HOST_PROJECT_ROOT (never PLUGIN_HOME;
    RISK-040 dual-root discipline) and delegates the WHOLE flow — parse →
    compute → format, the FIX-262 RECO snapshot append, cycle tolerance
    (FIX-237.3: default exit 0 + WARNING banner; ``--strict`` restores the
    fail-closed exit 1), and the FEAT-012 G5 same-session duplicate-run
    suppression (same-day + unchanged-tracker runs reuse the cached report
    「复用上次分析（--force 重跑）」; a duplicate same-day RECO row is not
    re-appended; FIRST-TIME closures are never suppressed — FIX-262 /
    REQ-108) — to the pure task_priority module. This entry is argparse
    glue only (RISK-039 thin-entry discipline + ArchGuard R1 main-file
    budget). Exits 2 on a missing plan-tracker or a parse error.
    """
    try:
        inputs.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from task_priority import run_cli_analysis
    code = run_cli_analysis(
        inputs.plan_path, inputs.governance_dir, inputs.evidence_path,
        evidence_task=getattr(args, "evidence_task", None),
        force=bool(getattr(args, "force", False)),
        strict=bool(getattr(args, "strict", False)),
    )
    if code:
        inputs.exit(code)


def cmd_next_candidates(args, *, inputs):
    """Read goal-scoped recommendations or the legacy loop_exit snapshot."""
    try:
        inputs.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    # Goal mode reads the live sources. The legacy path below may persist a
    # recommendation snapshot based on loop-exit events.
    if getattr(args, "goal", None) is not None:
        from goal_planning import run_goal_candidates
        return run_goal_candidates(args, project_root=inputs.host_root, load_packets=inputs.load_execution_packets)
    from loop_exit_bridge import (
        CANDIDATES_FILENAME,
        read_candidates,
        refresh_candidates,
    )
    snapshot = inputs.host_root / ".governance" / CANDIDATES_FILENAME
    report = None
    if not getattr(args, "refresh", False):
        report = read_candidates(snapshot)
    if report is None:
        report = refresh_candidates(
            inputs.host_root,
            top_n=getattr(args, "top_n", 3) or 3,
            candidate_path=snapshot if getattr(args, "write", False) else None,
        )
    # FIX-463: inject the collapsed-premise verdict (read-only; DEC-368②
    # class) — a collapsed decision must surface in the next-unit bridge
    # too, not only in the full TPA report. Additive key: consumers that
    # do not know it are unaffected.
    try:
        _dec_log = inputs.host_root / ".governance" / "decision-log.md"
        _decls = inputs.premise_tracker.collect_premise_declarations(
            _dec_log.read_text(encoding="utf-8")
            if _dec_log.is_file() else "")
        if _decls:
            _events = inputs.premise_tracker.load_events(
                inputs.host_root / ".governance")
            _status = inputs.premise_tracker.premise_status(_decls, _events)
            if isinstance(report, dict):
                report["collapsed_premises"] = [
                    dict(_status["detail"][d], decision_id=d)
                    for d in _status["collapsed"]]
    except (OSError, ValueError, TypeError):
        pass  # the bridge stays additive — never block the candidate read
    print(inputs.dumps(report, ensure_ascii=False, indent=2))
