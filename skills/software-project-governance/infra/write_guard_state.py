"""FEAT-060 — write-guard violation persistent state machine + consumption
ledger (0.88.0 阶段 B1 · P1 — BLOCK 前置基座, WARN 姿态下落地).

Requirement sources (consumed, never re-stated):

  * DEC-224 (decision-log) — write-guard contract amendment: BLOCK upgrade
    must NOT carry the WARN-once-then-absorb pattern, and the hook window
    consumption right must become a ledger (双约束).
  * version-plan-0.88.0 §2 B1 (arch Q2 双约束钉住) — persistent violation
    records (violation_id/family/object_id/before_hash/after_hash/
    workflow_run_id/hook_identity/first_seen/occurrence/status/grant_id/
    consumption_event) + six rules + consumption/baseline-update multi-file
    operations through an ops-recoverable transaction.

What this module is: the durable layer UNDER the write-guard's face-5
reconciliation (verify_workflow.py). The guard keeps its WARN output
semantics byte-for-byte (DEC-224 pins the WARN posture for 0.88; BLOCK
escalation belongs to FEAT-064); what changes is that every WARN-class
observation now lands in a persistent state machine instead of living only
in the diff window that the next guard run absorbs.

Artifact: ``.governance/.write-guard-violations.json`` — a NEW guard-owned
artifact, same class as ``.write-guard-state.json`` (FEAT-057): it is the
guard's own state, NOT a repair; the guard still never modifies any managed
governance record. Writes happen ONLY on the guard CLI path
(``persist_state=True``); probe callers (contract-matrix representative
extraction, tests, aggregate reads) never touch it. A healthy host that
never produces violations never sees the file at all (zero footprint until
the first observation).

The six rules (version-plan B1) and where they live in this module:

  R1 观测≠接受      recording an observation never resolves it — a record is
                    created ``open`` and only a GRANTED consumption (R5)
                    moves it to ``consumed``; the baseline absorbing the
                    diff window (WARN posture) never touches violation
                    state (see also R2).
  R2 WARN 不改基线  WARN-posture口径: the WARN observation path holds ZERO
                    authority over violation state — the reconciliation
                    baseline write never mutates violation records, and
                    violation resolution happens only through the granted
                    consume transaction (which is the one place baseline
                    and ledger move together). The literal BLOCK-era rule
                    "a WARN must not itself advance the reconciliation
                    baseline" belongs to FEAT-064 (BLOCK activation);
                    FEAT-060 delivers the mechanism (consume transaction
                    owns the baseline write) so that flip is a policy
                    change, not a rewrite. Disclosed in the FEAT-060
                    result as a口径决策.
  R3 升级           same session + same violation + second INDEPENDENT
                    trigger (content changed → supersede chain) → the new
                    record carries ``escalated=True``. Session identity is
                    ``GOVERNANCE_SESSION_ID`` when provided; without it the
                    rule conservatively never fires (run-scoped identity —
                    under-escalation is safe, false escalation is not).
                    FEAT-064 wires the escalation to BLOCK.
  R4 跨会话保留     records persist across guard runs and sessions in the
                    ledger file; ``open`` records survive baseline
                    rebuilds and session restarts until consumed.
  R5 消费权预授予+  consumption rights are PRE-GRANTED to registered
     单次原子消费   consumers only (``CONSUMER_REGISTRY``); a grant is
                    single-use — the consume transaction burns it
                    atomically; forged identities (registry consumer
                    mismatch) and unregistered consumers are refused.
  R6 损坏不吸收     corrupted ledger → loud disclosure, the diff window is
                    NOT absorbed and the baseline is NOT advanced, violation
                    writes are refused — recovery is manual (restore the
                    ledger; deleting it loses durable state and is disclosed
                    as such, never silent).

Ops-recoverable transaction (DoD 6 pattern, governance_store precedent):
consumption bundles ledger finalize + baseline advance in ONE recoverable
transaction. Phase 1 journals the intent (``pending_txn`` with the full
baseline target + previous-baseline sha256) into the ledger; phase 2 writes
the baseline (atomic replace — crash leaves old-or-new, never half); phase 3
finalizes (violations → consumed, grant → used, pending cleared — atomic).
A crash anywhere leaves the journal as the only residue and the next guard
CLI run RESUMES by judging the world, never the log: world==target →
finalize only; world==previous → re-apply baseline then finalize; anything
else → loud manual-intervention disclosure, nothing advanced. No half
state is ever observable, no double-consume, no double baseline write.

Known v1 boundaries (disclosed, not silent):

  * object identity for ``*.ops.jsonl`` surfaces is the LINE INDEX (the
    established FEAT-057 displacement semantics — a mid-line insert shifts
    identities; inherited, not redefined here).
  * used grants and consumed records accumulate (audit trail); growth is
    the same class as ``governance-store-ops.json`` (registered BT-4
    neighborhood) — pruning is a later slice.
  * violations of NEW types (beyond ``unattributed_row_change``) are a
    FEAT-064 extension point; the state machine is type-agnostic.

Private-import justification (FIX-379 precedent): ``_TargetLock`` and
``_atomic_write_bytes`` are reused from ``governance_store`` — there must
be ONE cross-process lock and ONE atomic-write implementation, not a
second hand-rolled copy; both are generic utilities and the ledger lock
directory (``.governance/.governance-store-locks/``) is the one
governance_store already maintains.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

# Reused wholesale (see module docstring — single lock/atomic-write source).
from governance_store import StoreError, _TargetLock, _atomic_write_bytes

__all__ = [
    "CLI_CONSUMER",
    "CONSUMER_REGISTRY",
    "DETECTION_TYPE",
    "GUARD_CLI_IDENTITY",
    "LEDGER_FILE_NAME",
    "SCHEMA_VERSION",
    "SESSION_ENV",
    "STATUS_CONSUMED",
    "STATUS_OPEN",
    "STATUS_SUPERSEDED",
    "TOOL_ID",
    "advance_baseline_plain",
    "build_detection",
    "consume_violations",
    "eligible_open_violation_ids",
    "ensure_grant",
    "load_ledger",
    "new_run_id",
    "record_detections",
    "reconcile_violation_state",
    "resume_pending_txn",
    "state_json_text",
]

# ── constants ────────────────────────────────────────────────────────────────

LEDGER_FILE_NAME = ".write-guard-violations.json"
SCHEMA_VERSION = 1
TOOL_ID = "governance-write-guard/violation-state-machine"

#: Detection-side identity stamped on every record (which command observed
#: the violation). The post-commit hook (FEAT-017 Step 4b) runs the guard
#: CLI, so observations made from the hook carry the CLI identity; a future
#: invoker can override via ``GOVERNANCE_GUARD_INVOKER``.
GUARD_CLI_IDENTITY = "governance-write-guard/cli"
INVOKER_ENV = "GOVERNANCE_GUARD_INVOKER"

#: Consumption-right registry (R5): the closed set of consumers allowed to
#: hold grants and consume violations. Hooks never consume directly — the
#: post-commit hook consumes the reconciliation window THROUGH the guard
#: CLI identity (one consumption gate, one registry).
CLI_CONSUMER = GUARD_CLI_IDENTITY
CONSUMER_REGISTRY = {
    CLI_CONSUMER: (
        "governance-write-guard CLI path (persist_state=True); the "
        "post-commit hook consumes the reconciliation window through this "
        "identity — hooks never consume directly"
    ),
}

SESSION_ENV = "GOVERNANCE_SESSION_ID"

STATUS_OPEN = "open"
STATUS_CONSUMED = "consumed"
STATUS_SUPERSEDED = "superseded"
_VIOLATION_STATUSES = (STATUS_OPEN, STATUS_CONSUMED, STATUS_SUPERSEDED)

GRANT_ACTIVE = "active"
GRANT_USED = "used"

DETECTION_TYPE = "unattributed_row_change"
SNAPSHOT_MAX_CHARS = 160

_TXN_REQUIRED_KEYS = ("txn_id", "operation", "consumer", "grant_id",
                      "violation_ids", "baseline_target",
                      "baseline_target_sha256", "baseline_prev_sha256")


# ── small helpers ────────────────────────────────────────────────────────────


def _now_iso(now=None) -> str:
    moment = now if now is not None else datetime.now()
    return moment.replace(microsecond=0).isoformat()


def _digest32(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:32]


def _new_id(prefix: str, payload) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return prefix + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def new_run_id() -> str:
    """Fresh guard-run identity (workflow_run_id) for one CLI invocation."""
    return _new_id("run-", {"nonce": os.urandom(16).hex(),
                            "ts": _now_iso()})


def state_json_text(baseline_state) -> str:
    """THE serialization of the reconciliation baseline state file.

    Single source shared with verify_workflow's plain-advance write path —
    the resume sha256 comparisons judge these exact bytes (no second
    serializer, FIX-292 lesson).
    """
    return json.dumps(baseline_state, ensure_ascii=False, indent=2,
                      sort_keys=True) + "\n"


def advance_baseline_plain(state_path, state_text, *, timeout_seconds=10.0):
    """Plain (non-transactional) baseline advance — P1-1
    (review-FEAT-060-R0): holds the SAME state-file lock the consumption
    transaction and its resume hold, so a concurrent plain advance can no
    longer interleave into an in-flight transaction's critical section and
    push the world out of {target, prev} (which forced a fail-closed
    manual-intervention on resume — no data corruption, but avoidable).

    Returns ``(True, None)`` when written. Returns ``(False, detail)`` on
    lock contention — the caller discloses and defers (the diff window
    stays open; the next run re-advances — converge, never lose a window).
    Write failures (IOError/OSError/ValueError, incl. the existing
    unwritable-disclosure contract) PROPAGATE unchanged to the caller.
    Content note: two concurrent plain advances serialize on the lock and
    write content-equivalent baselines (both derive ``files`` from the
    same managed files; only ``updated_at`` differs), so last-writer-wins
    is a no-op semantically.
    """
    state_path = Path(state_path)
    try:
        with _TargetLock(state_path, timeout_seconds):
            state_path.write_text(state_text, encoding="utf-8")
    except StoreError as exc:
        return False, "lock busy: {0}".format(exc)
    return True, None


def _state_bytes(baseline_state) -> bytes:
    return state_json_text(baseline_state).encode("utf-8")


def _sha256_bytes(data):
    """Hex digest of file bytes; ``None`` encodes 'file absent' and never
    collides with any content digest."""
    if data is None:
        return None
    return hashlib.sha256(data).hexdigest()


def _issue(issue_type: str, detail: str, expected: str = "") -> dict:
    """Face-5 shaped issue dict (same projection as unattributed_row_change
    WARNs — consumed by the guard's generic issue printer unchanged)."""
    return {
        "type": issue_type,
        "file": ".governance/" + LEDGER_FILE_NAME,
        "line": None,
        "task_id": "",
        "detail": detail,
        "expected": expected,
    }


# ── ledger load / save ───────────────────────────────────────────────────────

#: Structural integrity floor for a violation record (P3,
#: review-FEAT-060-R0): the twelve canonical version-plan B1 fields must be
#: PRESENT on every record — a truncated/tampered record is ledger
#: corruption (R6: disclosed, never silently absorbed). This is a
#: presence/shape floor, not content semantics.
_VIOLATION_REQUIRED_FIELDS = (
    "violation_id", "family", "object_id", "before_hash", "after_hash",
    "workflow_run_id", "hook_identity", "first_seen", "occurrence",
    "status", "grant_id", "consumption_event",
)


def _validate_ledger(ledger) -> list:
    problems = []
    if not isinstance(ledger, dict):
        return ["ledger must be a JSON object"]
    if ledger.get("schema_version") != SCHEMA_VERSION \
            or ledger.get("tool") != TOOL_ID:
        problems.append(
            "schema mismatch — expected schema_version={0} tool={1!r}".format(
                SCHEMA_VERSION, TOOL_ID))
    violations = ledger.get("violations")
    if not isinstance(violations, dict):
        problems.append("'violations' must be an object")
    else:
        for vid, record in violations.items():
            if not isinstance(record, dict):
                problems.append("violation {0!r} must be an object".format(vid))
                continue
            missing = [field for field in _VIOLATION_REQUIRED_FIELDS
                       if field not in record]
            if missing:
                problems.append(
                    "violation {0!r} missing required fields: {1}".format(
                        vid, ", ".join(missing)))
                continue
            if record.get("violation_id") != vid:
                problems.append(
                    "violation {0!r} carries a mismatched violation_id "
                    "{1!r}".format(vid, record.get("violation_id")))
            if record.get("status") not in _VIOLATION_STATUSES:
                problems.append(
                    "violation {0!r} carries an unknown status {1!r}".format(
                        vid, record.get("status")))
            occurrence = record.get("occurrence")
            if isinstance(occurrence, bool) or not isinstance(occurrence,
                                                              int) \
                    or occurrence < 1:
                problems.append(
                    "violation {0!r} occurrence must be an int >= 1, got "
                    "{1!r}".format(vid, occurrence))
    grants = ledger.get("grants")
    if not isinstance(grants, dict):
        problems.append("'grants' must be an object")
    else:
        for gid, grant in grants.items():
            if not isinstance(grant, dict) \
                    or not isinstance(grant.get("consumer"), str) \
                    or grant.get("status") not in (GRANT_ACTIVE, GRANT_USED):
                problems.append(
                    "grant {0!r} is malformed or carries an unknown "
                    "status".format(gid))
    txn = ledger.get("pending_txn")
    if txn is not None:
        if not isinstance(txn, dict) \
                or any(key not in txn for key in _TXN_REQUIRED_KEYS) \
                or txn.get("operation") != "consume":
            problems.append("pending_txn is malformed")
    return problems


def load_ledger(governance_dir):
    """Load the violation ledger → ``(ledger, issue)``.

    ``(fresh skeleton, None)`` when absent (first run). A corrupt or
    foreign-schema ledger returns ``(None, issue)`` — R6: it is NEVER
    silently rebuilt (a rebuild would amnesty every open violation, which
    is exactly the absorption rule 6 forbids); recovery is manual.
    """
    path = Path(governance_dir) / LEDGER_FILE_NAME
    if not path.is_file():
        return {"schema_version": SCHEMA_VERSION, "tool": TOOL_ID,
                "updated_at": None, "violations": {}, "grants": {},
                "pending_txn": None}, None
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, IOError, OSError,
            ValueError) as exc:
        return None, _issue(
            "violation_ledger_unreadable",
            "违规台账不可读（{0}）——R6 台账损坏：本轮不吸收差异窗口、不前移基线、"
            "不写违规记录（响亮披露，不静默）；恢复 = 人工修复台账"
            "（删除将丢失未决违规持久状态——如实披露）".format(exc),
            "JSON object（schema_version={0}, violations/grants 键, "
            "pending_txn 可空）".format(SCHEMA_VERSION))
    problems = _validate_ledger(ledger)
    if problems:
        return None, _issue(
            "violation_ledger_unreadable",
            "违规台账 schema 不识别（{0}）——R6 台账损坏：本轮不吸收差异窗口、"
            "不前移基线、不写违规记录（响亮披露，不静默）；恢复 = 人工修复"
            "台账（删除将丢失未决违规持久状态——如实披露）".format(
                "; ".join(problems)),
            "schema_version={0} 的台账对象".format(SCHEMA_VERSION))
    return ledger, None


def save_ledger(governance_dir, ledger) -> None:
    ledger = dict(ledger)
    ledger["updated_at"] = _now_iso()
    payload = (json.dumps(ledger, ensure_ascii=False, indent=2,
                          sort_keys=True) + "\n").encode("utf-8")
    _atomic_write_bytes(Path(governance_dir) / LEDGER_FILE_NAME, payload)


# ── detection records (R1 dedupe / R3 escalation) ────────────────────────────


def build_detection(family, family_kind, object_id, rel_path, line, row_text,
                    after_hash, before_hash=None) -> dict:
    """One face-5 offending-row observation → detection dict (pre-ledger)."""
    return {
        "type": DETECTION_TYPE,
        "family": family,
        "family_kind": family_kind,
        "object_id": object_id,
        "file": rel_path,
        "line": line,
        "snapshot": (row_text or "")[:SNAPSHOT_MAX_CHARS],
        "after_hash": after_hash,
        "before_hash": before_hash,
    }


def _open_record_for(ledger, family, object_id):
    for record in ledger["violations"].values():
        if record.get("status") == STATUS_OPEN \
                and record.get("family") == family \
                and record.get("object_id") == object_id:
            return record
    return None


def _record_violation(ledger, detection, *, run_id, session_id,
                      hook_identity, now):
    """Merge one detection into the ledger (mutates). Returns the
    violation_id of a NEW record, or None for a deduped repeat (R1)."""
    existing = _open_record_for(ledger, detection["family"],
                                detection["object_id"])
    stamp = _now_iso(now)
    if existing is not None \
            and existing.get("after_hash") == detection["after_hash"]:
        # R1 重复 — same violation re-observed (identical content): NOT
        # recorded again, and the stored record is not rewritten either
        # (pure dedupe — the observation is absorbed, the record keeps its
        # original provenance).
        return None
    record = {
        # version-plan B1 canonical twelve:
        "violation_id": _new_id("WV-", {
            "family": detection["family"],
            "object_id": detection["object_id"],
            "after_hash": detection["after_hash"],
            "run": run_id,
            "at": stamp,
        }),
        "family": detection["family"],
        "object_id": detection["object_id"],
        "before_hash": detection["before_hash"],
        "after_hash": detection["after_hash"],
        "workflow_run_id": run_id,
        "hook_identity": hook_identity,
        "first_seen": stamp,
        "occurrence": 1,
        "status": STATUS_OPEN,
        "grant_id": None,
        "consumption_event": None,
        # addressing / task-prompt field union (type/file/line/snapshot/
        # session/consumer-time/notes):
        "type": detection["type"],
        "family_kind": detection["family_kind"],
        "file": detection["file"],
        "line": detection["line"],
        "snapshot": detection["snapshot"],
        "session_id": session_id,
        "last_session_id": session_id,
        "last_seen": stamp,
        "escalated": False,
        "escalated_at": None,
        "notes": "",
    }
    if existing is not None:
        # Independent re-trigger (content changed) — R3 + supersede chain:
        # the old generation is superseded, the new one carries the
        # occurrence counter and the escalation verdict.
        same_session = (
            session_id is not None
            and session_id == existing.get("last_session_id"))
        record["occurrence"] = int(existing.get("occurrence", 1)) + 1
        record["escalated"] = bool(existing.get("escalated")) or same_session
        if same_session:
            record["escalated_at"] = stamp
        elif existing.get("escalated_at"):
            record["escalated_at"] = existing.get("escalated_at")
        record["notes"] = "supersedes {0}（同会话同违规独立再触发——内容变更）".format(
            existing["violation_id"])
        existing["status"] = STATUS_SUPERSEDED
        existing["notes"] = ((existing.get("notes") + "; ")
                             if existing.get("notes") else "") \
            + "superseded by {0}".format(record["violation_id"])
    ledger["violations"][record["violation_id"]] = record
    return record["violation_id"]


def record_detections(governance_dir, detections, *, run_id,
                      session_id=None, hook_identity=None, now=None,
                      timeout_seconds=10.0):
    """Record face-5 detections into the ledger (CLI path only).

    Returns ``(issues, changed)``. Corrupt ledger → ``([issue], False)``
    and ZERO writes (R6). A recording run PRE-GRANTS the consumption right
    for the registered CLI consumer (R5 预授予) whenever it creates records.
    """
    governance_dir = Path(governance_dir)
    if not detections:
        return [], False
    if hook_identity is None:
        hook_identity = os.environ.get(INVOKER_ENV) or GUARD_CLI_IDENTITY
    with _TargetLock(governance_dir / LEDGER_FILE_NAME, timeout_seconds):
        ledger, load_issue = load_ledger(governance_dir)
        if load_issue is not None:
            return [load_issue], False
        changed = False
        for detection in detections:
            if _record_violation(ledger, detection, run_id=run_id,
                                 session_id=session_id,
                                 hook_identity=hook_identity,
                                 now=now) is not None:
                changed = True
        if changed:
            _ensure_grant_locked(ledger, consumer=CLI_CONSUMER,
                                 run_id=run_id, now=now)
            save_ledger(governance_dir, ledger)
    return [], changed


# ── consumption-right grants (R5) ────────────────────────────────────────────


def _ensure_grant_locked(ledger, *, consumer, run_id, now):
    """Issue (or reuse) the active grant for a registered consumer.
    Returns ``(grant_id, created)``; ``(None, False)`` for an unregistered
    consumer — grants cannot be minted for identities outside the
    registry."""
    if consumer not in CONSUMER_REGISTRY:
        return None, False
    for gid, grant in ledger["grants"].items():
        if grant.get("consumer") == consumer \
                and grant.get("status") == GRANT_ACTIVE:
            return gid, False
    stamp = _now_iso(now)
    grant_id = _new_id("grant-", {"consumer": consumer, "run": run_id,
                                  "at": stamp})
    ledger["grants"][grant_id] = {
        "consumer": consumer,
        "issued_at": stamp,
        "issued_by_run": run_id,
        "status": GRANT_ACTIVE,
    }
    return grant_id, True


def ensure_grant(governance_dir, *, consumer, run_id, now=None,
                 timeout_seconds=10.0):
    """Public pre-grant step → ``(grant_id, issues)`` (R5 预授予)."""
    governance_dir = Path(governance_dir)
    with _TargetLock(governance_dir / LEDGER_FILE_NAME, timeout_seconds):
        ledger, load_issue = load_ledger(governance_dir)
        if load_issue is not None:
            return None, [load_issue]
        grant_id, created = _ensure_grant_locked(
            ledger, consumer=consumer, run_id=run_id, now=now)
        if grant_id is None:
            return None, [_issue(
                "unregistered_consumer",
                "consumer {0!r} 未登记消费权——不能预授予也不能消费（R5：仅"
                "注册消费者可持权）".format(consumer),
                "CONSUMER_REGISTRY 内的消费者身份")]
        if created:
            save_ledger(governance_dir, ledger)
        return grant_id, []


# ── consumption eligibility ──────────────────────────────────────────────────


def eligible_open_violation_ids(ledger, records_index):
    """Open violations whose object no longer reproduces → ``[violation_id]``.

    ``records_index`` maps surface → ``{"kind": "text"|"ops"|"unreadable",
    "by_key": {object_id: [{"digest", "credentialed"}, …]}}`` for THIS run.
    Eligible = the object is gone from its surface, or every current
    instance carries its machine credential (remediated). Unreadable
    surfaces keep their violations open (fail-safe — never consume what
    cannot be judged).
    """
    eligible = []
    for vid, record in ledger["violations"].items():
        if record.get("status") != STATUS_OPEN:
            continue
        surface = (records_index or {}).get(record.get("family"))
        if surface is None:
            # Surface absent this run (file removed) — the object cannot
            # reproduce anymore.
            eligible.append(vid)
            continue
        if surface.get("kind") == "unreadable":
            continue
        instances = (surface.get("by_key") or {}).get(
            record.get("object_id"), [])
        if not instances or all(
                instance.get("credentialed") for instance in instances):
            eligible.append(vid)
    return eligible


# ── ops-recoverable consumption transaction ──────────────────────────────────


def _finalize_txn(governance_dir, ledger, txn, now) -> None:
    """Phase 3 — mark consumed + burn the grant + clear the journal
    (single atomic ledger write)."""
    stamp = _now_iso(now)
    for vid in txn["violation_ids"]:
        record = ledger["violations"].get(vid)
        if record is None:
            continue
        record["status"] = STATUS_CONSUMED
        record["hook_identity"] = txn["consumer"]
        record["grant_id"] = txn["grant_id"]
        record["consumption_event"] = {
            "txn_id": txn["txn_id"],
            "consumer": txn["consumer"],
            "grant_id": txn["grant_id"],
            "at": stamp,
            "baseline_updated": True,
        }
    grant = ledger["grants"].get(txn["grant_id"])
    if grant is not None:
        grant["status"] = GRANT_USED
    ledger["pending_txn"] = None
    save_ledger(governance_dir, ledger)


def _apply_baseline_and_finalize(governance_dir, state_path, ledger, txn,
                                 now) -> None:
    """Phases 2+3 of the consumption transaction (journal already durable).

    Phase 2 writes the baseline (atomic replace — a crash here leaves the
    OLD or the NEW baseline, never a half file; the journal drives the
    resume). Phase 3 finalizes the ledger. Idempotent: a world already at
    the target skips the rewrite (resume-after-phase-2-crash path).
    """
    current = state_path.read_bytes() if state_path.is_file() else None
    if _sha256_bytes(current) != txn.get("baseline_target_sha256"):
        _atomic_write_bytes(state_path, _state_bytes(txn["baseline_target"]))
    _finalize_txn(governance_dir, ledger, txn, now)


def consume_violations(governance_dir, state_path, *, consumer, grant_id,
                       violation_ids, baseline_target, run_id, now=None,
                       timeout_seconds=10.0):
    """Consume open violations + advance the baseline in ONE recoverable
    transaction (R5 单次原子消费; ops 事务性).

    Refusals (structured, closed vocabulary) happen BEFORE the journal
    write — a refused call leaves zero residue. After the journal write a
    crash is recovered by :func:`resume_pending_txn` on the next run, never
    by re-executing here.
    """
    governance_dir = Path(governance_dir)
    now = now if now is not None else datetime.now()

    def refuse(code, detail):
        return {"ok": False, "error": code, "detail": detail,
                "consumed": []}

    if consumer not in CONSUMER_REGISTRY:
        return refuse(
            "unregistered_consumer",
            "consumer {0!r} is not in the consumption-right registry — "
            "unregistered hooks cannot consume (R5)".format(consumer))
    if not violation_ids:
        return refuse("schema_violation",
                      "violation_ids must be non-empty")
    if baseline_target is None:
        return refuse(
            "schema_violation",
            "baseline_target is required — consumption and baseline "
            "update share one recoverable transaction")
    with _TargetLock(state_path, timeout_seconds):
        with _TargetLock(governance_dir / LEDGER_FILE_NAME,
                         timeout_seconds):
            ledger, load_issue = load_ledger(governance_dir)
            if load_issue is not None:
                return refuse("ledger_corrupt", load_issue["detail"])
            if ledger.get("pending_txn"):
                return refuse(
                    "pending_transaction",
                    "a pending consumption transaction exists — resume it "
                    "first (re-run the guard CLI; the journal drives "
                    "recovery, the log is never trusted over the world)")
            grant = ledger["grants"].get(grant_id)
            if grant is None:
                return refuse(
                    "unknown_grant",
                    "grant {0!r} does not exist — consumption rights are "
                    "pre-granted tokens, not caller assertions (R5)".format(
                        grant_id))
            if grant.get("status") != GRANT_ACTIVE:
                return refuse(
                    "grant_used",
                    "grant {0!r} is not active ({1}) — grants are "
                    "single-use; a new grant is pre-granted by a later "
                    "recording run (R5)".format(grant_id,
                                                grant.get("status")))
            if grant.get("consumer") != consumer:
                return refuse(
                    "forged_consumer",
                    "grant {0!r} was issued to {1!r}, not {2!r} — forged "
                    "hook identity refused (R5)".format(grant_id,
                                                        grant.get("consumer"),
                                                        consumer))
            for vid in violation_ids:
                record = ledger["violations"].get(vid)
                if record is None:
                    return refuse(
                        "unknown_violation",
                        "violation {0!r} does not exist".format(vid))
                if record.get("status") != STATUS_OPEN:
                    return refuse(
                        "not_open",
                        "violation {0} has status {1!r} — only open "
                        "violations can be consumed (R1: observation is "
                        "not acceptance, consumption is the only "
                        "resolution)".format(vid, record.get("status")))
            prev_bytes = state_path.read_bytes() \
                if state_path.is_file() else None
            stamp = _now_iso(now)
            txn = {
                "txn_id": _new_id("txn-", {
                    "consumer": consumer, "grant": grant_id,
                    "violations": sorted(violation_ids), "at": stamp}),
                "operation": "consume",
                "consumer": consumer,
                "grant_id": grant_id,
                "violation_ids": sorted(violation_ids),
                "baseline_target": baseline_target,
                "baseline_target_sha256": _sha256_bytes(
                    _state_bytes(baseline_target)),
                "baseline_prev_sha256": _sha256_bytes(prev_bytes),
                "recorded_at": stamp,
            }
            # Phase 1 — durable journal (the ONLY residue a later crash
            # may leave).
            ledger["pending_txn"] = txn
            save_ledger(governance_dir, ledger)
            _apply_baseline_and_finalize(governance_dir, state_path,
                                         ledger, txn, now)
            return {"ok": True, "error": None,
                    "txn_id": txn["txn_id"], "grant_id": grant_id,
                    "consumed": list(txn["violation_ids"]),
                    "baseline_updated": True}


def resume_pending_txn(governance_dir, state_path, *, now=None,
                       timeout_seconds=10.0):
    """World-judged resume of a pending consumption transaction.

    Returns ``(issues, completed, consumed_ids)``. Judge the world, never
    the log (governance_store DoD-2/6 pattern): world==target → finalize;
    world==previous → re-apply baseline then finalize; anything else →
    loud manual-intervention disclosure, NOTHING advanced.
    """
    governance_dir = Path(governance_dir)
    now = now if now is not None else datetime.now()
    with _TargetLock(state_path, timeout_seconds):
        with _TargetLock(governance_dir / LEDGER_FILE_NAME,
                         timeout_seconds):
            ledger, load_issue = load_ledger(governance_dir)
            if load_issue is not None:
                return [load_issue], False, []
            txn = ledger.get("pending_txn")
            if not txn:
                return [], False, []
            current = state_path.read_bytes() \
                if state_path.is_file() else None
            current_sha = _sha256_bytes(current)
            if current_sha == txn.get("baseline_target_sha256"):
                _finalize_txn(governance_dir, ledger, txn, now)
                return [], True, list(txn["violation_ids"])
            if current_sha == txn.get("baseline_prev_sha256"):
                _atomic_write_bytes(state_path,
                                    _state_bytes(txn["baseline_target"]))
                _finalize_txn(governance_dir, ledger, txn, now)
                return [], True, list(txn["violation_ids"])
            return [_issue(
                "violation_txn_diverged",
                "待完成消费事务（{0}）与世界状态不一致——当前基线既非事务目标"
                "也非事务前像。拒绝推进（不吸收不前移不写违规），人工复核后"
                "处置；台账绝不凌驾世界（幂等模型：查世界不信日志）".format(
                    txn.get("txn_id")),
                "基线 = 事务目标或事务前像之一")], False, []


# ── CLI-path step driver ─────────────────────────────────────────────────────


def reconcile_violation_state(governance_dir, *, state_path, detections,
                              records_index, baseline_target, run_id,
                              session_id=None, now=None,
                              timeout_seconds=10.0):
    """One guard CLI run's violation-state-machine step (FEAT-060).

    Order: resume pending transaction → record detections (dedupe /
    supersede / escalate) → consume eligible open violations through the
    recoverable transaction (bundling THIS run's baseline target). Returns
    ``{"issues", "consumed", "baseline_written_by_txn",
    "skip_baseline_advance"}``:

    * ``baseline_written_by_txn`` — the transaction already wrote THIS
      run's baseline; the caller must not write it again.
    * ``skip_baseline_advance`` — R6 (corrupt ledger) or diverged
      transaction: the caller must NOT advance the baseline this run
      (不吸收不前移) and the window stays open for the next run.

    WARN posture is preserved by construction: this step only appends
    WARN-class issues to face 5 and never changes the face status or the
    guard exit code.
    """
    governance_dir = Path(governance_dir)
    result = {"issues": [], "consumed": [],
              "baseline_written_by_txn": False,
              "skip_baseline_advance": False}
    ledger, load_issue = load_ledger(governance_dir)
    if load_issue is not None:
        result["issues"].append(load_issue)
        result["skip_baseline_advance"] = True
        return result
    if ledger.get("pending_txn"):
        issues, completed, consumed = resume_pending_txn(
            governance_dir, state_path, now=now,
            timeout_seconds=timeout_seconds)
        result["issues"].extend(issues)
        if not completed:
            result["skip_baseline_advance"] = True
            return result
        result["consumed"].extend(consumed)
    if detections:
        record_issues, _changed = record_detections(
            governance_dir, detections, run_id=run_id,
            session_id=session_id, now=now,
            timeout_seconds=timeout_seconds)
        result["issues"].extend(record_issues)
        if any(issue["type"] == "violation_ledger_unreadable"
               for issue in record_issues):
            result["skip_baseline_advance"] = True
            return result
    ledger, load_issue = load_ledger(governance_dir)
    if load_issue is not None:
        result["issues"].append(load_issue)
        result["skip_baseline_advance"] = True
        return result
    eligible = eligible_open_violation_ids(ledger, records_index)
    if not eligible:
        return result
    grant_id, grant_issues = ensure_grant(
        governance_dir, consumer=CLI_CONSUMER, run_id=run_id, now=now,
        timeout_seconds=timeout_seconds)
    if grant_issues:
        result["issues"].extend(grant_issues)
        return result
    payload = consume_violations(
        governance_dir, state_path, consumer=CLI_CONSUMER,
        grant_id=grant_id, violation_ids=eligible,
        baseline_target=baseline_target, run_id=run_id, now=now,
        timeout_seconds=timeout_seconds)
    if payload.get("ok"):
        result["consumed"].extend(payload["consumed"])
        result["baseline_written_by_txn"] = True
    else:
        # Refusal happened before the journal write — zero residue; the
        # WARN-posture baseline advance proceeds unchanged and the open
        # violations stay open (R1).
        result["issues"].append(_issue(
            "violation_consumption_refused",
            "消费事务被拒（{0}）——{1}；违规保持 open，基线按 WARN 姿态照常"
            "推进（本条为响亮披露，不阻断）".format(
                payload.get("error"), payload.get("detail")),
            "注册消费者 + 有效单次授权 + open 违规"))
    return result
