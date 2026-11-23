"""Inspect governance write shapes and coordinate reconciled state through the governed writers."""

import json
import os
from dataclasses import dataclass
from collections.abc import Callable


@dataclass(frozen=True)
class StructureChecks:
    """Existing validators for the plan, evidence, locks and execution packet schemas."""

    plan: Callable
    evidence: Callable
    locks: Callable
    load_packets: Callable
    packet_fields: Callable


def _markdown_face(path, filename, issue_type, validate):
    if not path.is_file():
        return {"status": "SKIPPED", "issues": []}
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        issues = [{
            "type": issue_type, "file": ".governance/" + filename,
            "line": None, "task_id": "", "detail": f"{filename} unreadable: {exc}",
            "expected": "",
        }]
    else:
        issues = validate(content)
    return {"status": "FAIL" if issues else "PASS", "issues": issues}


def _lock_face(governance_dir, check_locks):
    locks_path = governance_dir / "agent-locks.json"
    if locks_path.is_file():
        locks_issues = check_locks()
        return {
            "status": "FAIL" if locks_issues else "PASS",
            "issues": [
                {
                    "type": "agent_locks_{0}".format(issue.get("type", "issue")),
                    "file": ".governance/agent-locks.json",
                    "line": None,
                    "task_id": "",
                    "detail": str(issue.get("detail", "")),
                    "expected": "Check 26 schema（active_tasks 条目: "
                                "spawned_at/coordinator_session/target_files；"
                                "file_locks 条目: locked_by/locked_at/"
                                "ttl_seconds/ttl_reason；可选 expected_new: "
                                "bool——FEAT-013 预创建文件声明）",
                }
                for issue in locks_issues
            ],
        }
    return {"status": "SKIPPED", "issues": []}


def _packet_face(governance_dir, checks):
    packet_path = governance_dir / "execution-packets.json"
    if packet_path.is_file():
        packets, load_error = checks.load_packets(packet_path)
        if load_error:
            return {
                "status": "FAIL",
                "issues": [{
                    "type": "execution_packets_structure",
                    "file": ".governance/execution-packets.json",
                    "line": None,
                    "task_id": "",
                    "detail": "execution-packets.json 结构错误: {0}".format(
                        load_error),
                    "expected": "JSON object（可选 packets 键 → task_id → "
                                "packet object）",
                }],
            }
        else:
            issues = []
            for task_id, packet in packets.items():
                for field_issue in checks.packet_fields(packet):
                    issues.append({
                        "type": "execution_packets_field",
                        "file": ".governance/execution-packets.json",
                        "line": None,
                        "task_id": task_id,
                        "detail": "packet {0}: {1}".format(
                            task_id, field_issue),
                        "expected": "EXECUTION_PACKET_REQUIRED_FIELDS 六字段"
                                    "（task_id/goal/allowed_change_scope/"
                                    "required_evidence/next_commands/"
                                    "done_definition）",
                    })
            return {
                "status": "FAIL" if issues else "PASS",
                "issues": issues,
            }
    return {"status": "SKIPPED", "issues": []}


def _pin_face(plugin_root, pin_ledger):
    try:
        pin_issues, pin_status = pin_ledger.exemption_face_issues(plugin_root)
    except Exception as _pin_exc:  # noqa: BLE001 — guard faces never raise
        pin_issues, pin_status = [{
            "type": "pin_ledger_face_error", "line": None,
            "detail": "face probe raised: {0}".format(_pin_exc),
        }], "FAIL"
    return {
        "status": pin_status,
        "issues": [
            {
                "type": issue.get("type", "pin_ledger_issue"),
                "file": pin_ledger.LEDGER_REL,
                "line": issue.get("line"),
                "task_id": "",
                "detail": issue.get("detail", ""),
                "expected": "STATIC_PIN_EXEMPTIONS 条目 (int line, str token, "
                            "reason)；新行经 pins register/re-anchor 机写"
                            "（provenance 注释）或属 FIX-462 交付 amnesty",
            }
            for issue in pin_issues
        ],
    }


def _append_deferred_ledger(governance_dir, ledger_name, entries, row_face):
    try:
        from checks import loop_gate_processor as _lgp
        from datetime import date as _d
        _today = _d.today().isoformat()
        _records = list(entries)
        _records.append(_lgp.observation_face_record(
            row_face.get("deferred_observation")
            or {"rows_judged": 0, "hits": 0, "fired": 0,
                "detector_errors": 0},
            _today))
        _ledger_path = governance_dir / ledger_name
        with _ledger_path.open("a", encoding="utf-8") as _fh:
            for _entry in _records:
                _fh.write(json.dumps(
                    _entry, ensure_ascii=False) + "\n")
    except (IOError, OSError, ValueError) as exc:
        row_face["issues"].append({
            "type": "deferred_ledger_unwritable",
            "file": ".governance/" + ledger_name,
            "line": None,
            "task_id": "",
            "detail": "M2 观察期台账写入失败（{0}）——本轮检测不入账，"
                      "响亮披露不静默（FEAT-081 B4 / RT-5：台账是"
                      "WARN→FAIL 翻转前误报率报告的数据容器）".format(exc),
            "expected": "可写的 .governance 目录",
        })


def _advance_baseline(governance_dir, filename, next_state, row_face, detections, records_index,
                     persist_state, session_id, encode_baseline):
    baseline_in_txn = False
    skip_baseline = False
    advance_target = next_state
    if persist_state:
        import write_guard_state  # deferred — heavy peer module
        run_id = write_guard_state.new_run_id()
        # The posture config is loaded again here for the state-machine
        # step (the face judge loaded its own copy inside
        # _reconcile_row_families — a second read-only load, same file,
        # no lock contention; its anomaly issue is already disclosed
        # through the face).
        family_postures, _posture_issue = (
            write_guard_state.load_family_postures(governance_dir))
        sm_result = write_guard_state.reconcile_violation_state(
            governance_dir,
            state_path=governance_dir / filename,
            detections=detections or [],
            records_index=records_index or {},
            baseline_target=next_state,
            run_id=run_id,
            session_id=session_id
            if session_id is not None
            else os.environ.get(
                write_guard_state.SESSION_ENV) or None,
            family_postures=family_postures)
        for sm_issue in sm_result["issues"]:
            row_face["issues"].append(sm_issue)
        baseline_in_txn = sm_result["baseline_written_by_txn"]
        skip_baseline = sm_result["skip_baseline_advance"]
        if not skip_baseline:
            advance_target = (sm_result.get("baseline_target_effective")
                              or next_state)
        # FEAT-064 break-glass audit — one use event per CLI persist
        # run under a valid window; a recording failure is loud, never
        # silent (不可静默记录).
        _use_recorded, use_issue = write_guard_state.record_break_glass_use(
            governance_dir, run_id=run_id)
        if use_issue is not None:
            row_face["issues"].append(use_issue)
    if not baseline_in_txn and not skip_baseline:
        state_path = governance_dir / filename
        try:
            # P1-1 (review-FEAT-060-R0): the plain advance runs under
            # the SAME state-file lock the consume transaction and its
            # resume hold — a concurrent CLI run can no longer
            # interleave a (timestamp-divergent) baseline write into an
            # in-flight transaction's {target, prev} world.
            advanced, lock_detail = (
                write_guard_state.advance_baseline_plain(
                    state_path, encode_baseline(advance_target)))
        except (IOError, OSError, ValueError) as exc:
            row_face["issues"].append({
                "type": "row_family_state_unwritable",
                "file": ".governance/" + filename,
                "line": None,
                "task_id": "",
                "detail": "对账状态基线写入失败（{0}）——下一轮将以同一基线"
                          "重复披露同一差异窗口（响亮披露，不静默）".format(exc),
                "expected": "可写的 .governance 目录",
            })
        else:
            if not advanced:
                row_face["issues"].append({
                    "type": "row_family_state_lock_busy",
                    "file": ".governance/" + filename,
                    "line": None,
                    "task_id": "",
                    "detail": "对账状态基线推进让行（{0}）——本轮不前移基线，"
                              "差异窗口保持开放、复跑照常重推（响亮披露，"
                              "不静默）".format(lock_detail),
                    "expected": "状态基线文件锁空闲",
                })


def check_governance_write_shapes(governance_dir, plan_path, plugin_root, *, checks, pin_ledger, reconcile,
                                  state_filename, deferred_filename, encode_baseline,
                                  persist_state=False, session_id=None, deferred_ledger=False):
    """FEAT-011 G3 extension — structural write guard over the Coordinator's
    direct-write ``.governance`` artifacts.

    FIX-278 G3 put a write-time guard on the change-triage CLI's machine
    writes; the Coordinator's DIRECT writes (plan-tracker task rows,
    evidence-log appends, agent-locks, execution-packets) had no write-time
    structural check, so shape defects entered silently (live evidence:
    AUDIT-149 §4 M1 four rows judged active for weeks; 14 Check 26
    agent-locks schema violations; execution-packets field violations).
    This guard extends the SAME G3 discipline to that path — one command
    after a direct write:

      1. plan-tracker task rows — AUDIT-149 §4 M1 ragged-row signatures
         (:func:`_plan_tracker_task_row_issues`);
      2. evidence-log machine families (TRIAGE/RECO) — DEC-168 row-family
         column contract + writer ID format
         (:func:`_evidence_machine_row_issues`);
      3. agent-locks.json — Check 26 schema, reused wholesale via
         :func:`check_agent_locks_format` (no second schema definition);
      4. execution-packets.json — structural face only: JSON/root shape via
         :func:`_load_execution_packets` + per-packet required fields via
         the ``EXECUTION_PACKET_REQUIRED_FIELDS`` table
         (:func:`_execution_packet_field_issues`). Semantic packet checks
         (scope breadth, evidence wording) stay in Check 18c — a write
         guard judges STRUCTURE, not task semantics;
      5. row-family reconciliation (FEAT-057) — provenance of row-level
         CHANGES in the managed families (EVD/DEC/REVIEW rows, plan-tracker
         task-row status cells, ``*.ops.jsonl`` receipts) against the
         ``.write-guard-state.json`` baseline
         (:func:`_reconcile_row_families`). FEAT-064 posture: the shipped
         default is all-WARN (loud disclosure, the face never FAILs);
         families activated BLOCK through the guard CLI's management mode
         turn their uncredentialed changes into BLOCK-class issues (face
         FAILs, exit 1) and hold their baseline until the writer
         remediation loop closes the window through the consumption
         transaction. The baseline state file is a guard-owned ARTIFACT,
         not a repair — together with the FEAT-060 violation ledger it is
         the only thing this guard ever writes, and only when
         ``persist_state=True`` (the CLI path); probe callers
         (contract-matrix representative extraction, aggregate reads,
         tests) stay read-only and never consume the reconciliation
         window. FEAT-060: CLI-path observations additionally persist into
         the violation state machine (infra/write_guard_state.py — six
         rules, consumption-right ledger, ops-recoverable consume
         transaction).
      6. pin-exemption ledger (FIX-462 / DEC-220) — structural FAIL on an
         unreadable/malformed ``STATIC_PIN_EXEMPTIONS`` and WARN-class
         hand-edit alarm for entries outside the delivery amnesty that
         carry no ``pins`` provenance comment
         (:func:`pin_ledger.exemption_face_issues`); probe callers are
         read-only over the plugin-tree ledger.

    ``session_id`` (FEAT-064 R3 wiring): explicit session identity for the
    violation state machine's same-session escalation rule — overrides the
    ``GOVERNANCE_SESSION_ID`` environment variable when provided; probes
    and tests that leave it unset keep the env fallback.

    ``deferred_ledger`` (FEAT-081 B4 / ADR-021 §3.2.1): append the M2
    deferred-registration observation ledger
    (``.governance/.write-guard-deferred-ledger.jsonl`` — three-key
    buckets 命中词×行族×否定语境, plus one per-run observation-face record
    carrying the CR-R1-2 SKIP 分态 attribution). Guard CLI face only —
    the internal persist path (release-bootstrap converge) and every
    probe keep the rel089 compatibility contract (converge writes only
    the two FEAT-057/060 guard artifacts). Requires ``persist_state``;
    a write failure is a loud WARN-class disclosure, never silent.

    Contract: CHECK-ONLY for governance records — reads the artifacts,
    never repairs or rewrites them (issue messages carry line numbers and
    the expected shape, the fix belongs to the writer). Absent files
    SKIP their face (a host not using packets is not a breach); unreadable
    files (incl. non-UTF-8, FIX-333) FAIL fail-closed on faces 1-4 (face 5
    discloses an unreadable surface as WARN and skips that surface). The
    change-triage write guard's behavior is untouched (extension, not
    rewrite).

    Returns a dict ``{plan_tracker, evidence_log, agent_locks,
    execution_packets, row_families}``, each ``{"status":
    PASS|FAIL|SKIPPED, "issues": …}`` (face 5 additionally carries
    ``baselined``). Never raises.
    """
    result = {
        "plan_tracker": _markdown_face(plan_path, "plan-tracker.md", "plan_tracker_unreadable", checks.plan),
        "evidence_log": _markdown_face(governance_dir / "evidence-log.md", "evidence-log.md",
                                       "evidence_log_unreadable", checks.evidence),
        "agent_locks": _lock_face(governance_dir, checks.locks),
        "execution_packets": _packet_face(governance_dir, checks),
        "row_families": {"status": "SKIPPED", "issues": [], "baselined": []},
    }
    result["pin_ledger"] = _pin_face(plugin_root, pin_ledger)
    detections = [] if persist_state else None
    records_index = {} if persist_state else None
    deferred_entries = [] if persist_state and deferred_ledger else None
    row_face, next_state = reconcile(
        governance_dir, persist_state=persist_state, detections_out=detections,
        records_index_out=records_index, deferred_out=deferred_entries,
    )
    if deferred_entries is not None:
        _append_deferred_ledger(governance_dir, deferred_filename, deferred_entries, row_face)
    if next_state is not None:
        _advance_baseline(governance_dir, state_filename, next_state, row_face, detections,
                          records_index, persist_state, session_id, encode_baseline)
    result["row_families"] = row_face
    return result
