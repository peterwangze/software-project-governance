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
                    baseline" is DELIVERED by FEAT-064 as the per-surface
                    baseline clamp: while a BLOCK-active family's window is
                    open, that surface's baseline entry is held at its
                    previous snapshot (never absorbed — DEC-236 ① 翻转面
                   兑现); only the consumption transaction closes the
                    window and advances the baseline (bundled, atomic).
                    WARN-posture hosts (default) keep the pinned absorb
                    behavior byte-for-byte.
  R3 升级           same session + same violation + second INDEPENDENT
                    trigger (content changed → supersede chain) → the new
                    record carries ``escalated=True``. Session identity is
                    ``GOVERNANCE_SESSION_ID`` when provided (or the
                    guard CLI's explicit ``--session-id`` — FEAT-064 R3
                    wiring); without it the rule conservatively never
                    fires (run-scoped identity — under-escalation is safe,
                    false escalation is not). Since FEAT-064 (review
                    FEAT-060-R0 P2-2 定案 — option (a) 会话累计触发计数):
                    triggers are counted PER SESSION on the record
                    (``session_triggers``), so the A-B-A sequence x→y→x
                    escalates on x's second trigger — the B1 literal
                    "同会话第二次独立触发" semantics — instead of only the
                    immediately-adjacent-same-session case.
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

FEAT-064 family-posture layer (0.88.0 阶段 D1 — 分族 BLOCK 激活, delivered
here as the enforcement entity; verify_workflow.py keeps only thin wiring,
RISK-039 thin-entry discipline):

The DEC-224 five managed row families are enumerated against the FEAT-049
M0 writer-contract registry (contracts.py faces 1-5 — every family's
legitimate write path is a governed writer) and ruled PER FAMILY
(``FAMILY_RULING_DECLARATION`` — the deliverable 逐族裁定表, each entry
naming its writer and coverage rationale): evidence / review / decision /
ops_ledger declare BLOCK (writer coverage complete); task_status stays WARN
(建行/📋⏳ 激活面存在合法手工路径 — version-plan D1: 先补机录激活路径或入
豁免台账再 BLOCK, 0.89+ 出槽). The ruling is a DECLARATION, not the live
enforcement state: the guard ships all-WARN, and a family's BLOCK posture
activates ONLY through the guard-owned posture config
(``.governance/.write-guard-posture.json``, written exclusively by the
guard CLI's ``--activate-block`` management mode) — the real flip moment is
the Coordinator's decision (FEAT-064 红线: mechanism + tests delivered, the
上线翻转 not executed by the delivery session). Absent config = all-WARN =
byte-identical WARN-era behavior (zero footprint); a corrupt config fails
SAFE to all-WARN with a loud disclosure (never guessed, never silently
repaired).

Under an active BLOCK posture an uncredentialed row change in that family
is a BLOCK-class face issue (face 5 FAILs, guard exit 1 — the workflow is
blocked loudly; it can NOT stop the file from being modified — the guard is
write-AFTER, M-0 事实填充项③ wording kept honest), and the R2 flip holds
the offending surface's baseline at its previous snapshot (per-surface
clamp; mixed-surface baselines keep WARN-family windows absorbable). The
only sanctioned unlock = the writer remediation loop: re-apply the change
through the family's writer (machine credential) → the next guard run
consumes the violation through the ops-recoverable transaction, which
advances the clamped baseline atomically. A WARN-once-then-absorb path does
not exist under BLOCK (DEC-224 双约束).

break-glass channel (恢复专用 — 限定留痕): when the guard's own enforcement
blocks the repair of guard-adjacent damage, the Coordinator may open a
TIME-BOXED, COUNT-LIMITED, SCOPED window (``grant_break_glass`` — 对象
families / 操作者 authorized_by / 理由 reason / 有效期 ttl_hours / 次数
max_uses, one active window at a time, grant refused when no BLOCK posture
is active). While valid, BLOCK-class issues for the scoped families are
DOWNGRADED to loud WARN-class disclosures for guard runs (the face does not
FAIL from them; violations are still recorded open — nothing is amnestied),
and EVERY guard CLI persist-path run under the window records one use event
into the ledger (不可静默记录 — the audit write failing is itself loud).
Expiry/uses-exhaustion turns the window inert + loud; ``--break-clear``
moves the grant into ``break_glass_history`` (audit retained). This is the
B-12 rollback's channel (version-plan §3b F-11: 族级 flag 回 WARN 经 D1
break-glass 通道——guard 自指场景下同样适用, 不可静默); the deliberate
posture flag flip itself is the ``--activate-block``/``--deactivate-block``
management modes (deactivation demands reason + authorized-by — never
silent). Trust-model boundary, disclosed: the guard is a local CLI, so the
channel records WHO authorized and WHY — it cannot cryptographically
enforce identity (the same trust model every writer in this repo runs
under).

Known v1 boundaries (disclosed, not silent):

  * object identity for ``*.ops.jsonl`` surfaces is the LINE INDEX (the
    established FEAT-057 displacement semantics — a mid-line insert shifts
    identities; inherited, not redefined here).
  * used grants and consumed records accumulate (audit trail); growth is
    the same class as ``governance-store-ops.json`` (registered BT-4
    neighborhood) — pruning is a later slice.
  * violations of NEW types (beyond ``unattributed_row_change``) are a
    FEAT-064 extension point; the state machine is type-agnostic.
  * FEAT-064: the baseline CLAMP granularity is the SURFACE FILE (the
    baseline snapshot shape is per-file); the delivered ruling never mixes
    postures within one surface (evidence-log.md holds the two BLOCK
    families EVD+REVIEW), so the coarser clamp grain is unobservable today.
  * FEAT-064: break-glass windows soften the FACE (exit code / face
    status) only — the violation ledger keeps recording open violations
    and the baseline stays held while any scoped window is open; the
    window is a disclosure channel, not an amnesty.

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
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Reused wholesale (see module docstring — single lock/atomic-write source).
from governance_store import StoreError, _TargetLock, _atomic_write_bytes

__all__ = [
    "BREAK_GLASS_ALL",
    "CLI_CONSUMER",
    "CONSUMER_REGISTRY",
    "DETECTION_TYPE",
    "FAMILY_DECISION",
    "FAMILY_EVIDENCE",
    "FAMILY_OPS_LEDGER",
    "FAMILY_REVIEW",
    "FAMILY_RULING_DECLARATION",
    "FAMILY_TASK_STATUS",
    "FAMILY_VOCABULARY",
    "GUARD_CLI_IDENTITY",
    "LEDGER_FILE_NAME",
    "POSTURES",
    "POSTURE_BLOCK",
    "POSTURE_CONFIG_FILE_NAME",
    "POSTURE_WARN",
    "SCHEMA_VERSION",
    "SESSION_ENV",
    "STATUS_CONSUMED",
    "STATUS_OPEN",
    "STATUS_SUPERSEDED",
    "TOOL_ID",
    "activate_family_postures",
    "advance_baseline_plain",
    "blocked_surfaces",
    "build_detection",
    "canonical_family",
    "clamp_baseline_target",
    "clear_break_glass",
    "consume_violations",
    "eligible_open_violation_ids",
    "ensure_grant",
    "grant_break_glass",
    "load_family_postures",
    "load_ledger",
    "new_run_id",
    "read_previous_baseline",
    "record_break_glass_use",
    "record_detections",
    "reconcile_violation_state",
    "resume_pending_txn",
    "run_guard_management_cli",
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

# ── FEAT-064 constants: family postures + break-glass ───────────────────────

#: Enforcement postures (closed vocabulary). WARN = loud disclosure, exit
#: unchanged (the DEC-224-pinned 0.86.0 behavior); BLOCK = the face FAILs
#: and the guard exits 1 for that family's uncredentialed row changes.
POSTURE_WARN = "warn"
POSTURE_BLOCK = "block"
POSTURES = (POSTURE_WARN, POSTURE_BLOCK)

#: The DEC-224 five managed row families (canonical ids). The face-5
#: SURFACE is the file; the FAMILY is the finer DEC-224 grain —
#: ``evidence-log.md`` carries TWO families (EVD rows and REVIEW rows),
#: disambiguated by the row-key prefix (the same authority the credential
#: judge uses). An unknown surface maps to ``None`` → WARN (safe default).
FAMILY_EVIDENCE = "evidence"
FAMILY_REVIEW = "review"
FAMILY_DECISION = "decision"
FAMILY_TASK_STATUS = "task_status"
FAMILY_OPS_LEDGER = "ops_ledger"
FAMILY_VOCABULARY = (FAMILY_EVIDENCE, FAMILY_REVIEW, FAMILY_DECISION,
                     FAMILY_TASK_STATUS, FAMILY_OPS_LEDGER)

#: Guard-owned posture config (written ONLY by the guard CLI management
#: modes; absent = all-WARN = byte-identical WARN-era behavior).
POSTURE_CONFIG_FILE_NAME = ".write-guard-posture.json"
POSTURE_CONFIG_TOOL = "governance-write-guard/family-posture-config"
POSTURE_CONFIG_SCHEMA_VERSION = 1

#: break-glass scope token meaning "every BLOCK-active family".
BREAK_GLASS_ALL = "*"

#: Default window shape (限定留痕: 有效期/次数 defaults — both overridable
#: at grant time, both bounded).
BREAK_GLASS_DEFAULT_TTL_HOURS = 24.0
BREAK_GLASS_DEFAULT_MAX_USES = 3

_BREAK_GLASS_REQUIRED_KEYS = ("grant_id", "reason", "authorized_by",
                              "families", "issued_at", "expires_at",
                              "max_uses", "uses")

#: 逐族裁定表 (FEAT-064 deliverable — version-plan D1: 枚举基线 = FEAT-049
#: 写入器契约注册表, DEC-224 五族全覆盖含 ops 台账族去向显式声明). Each
#: entry names the ruling, the wave, the writer whose machine credential is
#: the family's credential authority, and the coverage rationale. This is
#: the DECLARED ruling (audit/documentation face); the LIVE posture is the
#: posture config artifact (absent = all-WARN).
FAMILY_RULING_DECLARATION = {
    FAMILY_EVIDENCE: {
        "target": POSTURE_BLOCK,
        "wave": "D1",
        "writer": "governance_store evidence-append"
                  "（机器写入：governance-store 标记）",
        "rationale": "合法写路径全部经写入器（DEC-224：治理行写入转机录路径；"
                     "FEAT-049 M0 writer 契约五面覆盖 evidence-append）——"
                     "无合法手工面 → BLOCK",
    },
    FAMILY_REVIEW: {
        "target": POSTURE_BLOCK,
        "wave": "D1",
        "writer": "review-record CLI（REVIEW_MACHINE_ROW_MARKER，"
                  "Check 30c V7 权威）",
        "rationale": "审查结论必机录（M7.4；禁手写 REVIEW 行）——写入器覆盖"
                     "完备 → BLOCK",
    },
    FAMILY_DECISION: {
        "target": POSTURE_BLOCK,
        "wave": "D1",
        "writer": "governance_store decision-append（FEAT-061 双后端路由："
                  "MD 权威行携标记；JSON 权威经 md 投影逐字重放行）",
        "rationale": "双后端安全性论证：MD_ACTIVE 行由 decision-append 追加"
                     "（携标记）；JSON_ACTIVE 下 decision-log.md 为派生投影，"
                     "render_markdown 逐字重放记录行（行摘要恒等 → 对账零 "
                     "diff）；迁移/回滚路径全部走写入器（组合测试 F-5 ②）"
                     "→ BLOCK",
    },
    FAMILY_TASK_STATUS: {
        "target": POSTURE_WARN,
        "wave": "deferred（0.89+ 出槽——version-plan §6）",
        "writer": "task_row_update（〔op-…〕 状态锚）",
        "rationale": "写入器覆盖不完备：📋/⏳ 停放格的建行/激活面存在合法"
                     "手工路径（version-plan D1 行声明实证）——后置，先补"
                     "机录激活路径或入豁免台账再 BLOCK",
    },
    FAMILY_OPS_LEDGER: {
        "target": POSTURE_BLOCK,
        "wave": "D1",
        "writer": "task_row_update receipt 追加（operation_id 凭证锚）",
        "rationale": "receipt 台账仅由 task_row_update 写入器追加（append-only"
                     "，合法追加恒在尾部——行索引身份不漂移）；无合法手工面 → "
                     "DEC-224 五族去向显式声明：纳入 BLOCK",
    },
}


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
    # FEAT-064 shape floor for the break-glass section (absent = fine —
    # FEAT-060-era ledgers stay valid; present-but-malformed = corruption).
    break_glass = ledger.get("break_glass")
    if break_glass is not None:
        if not isinstance(break_glass, dict) \
                or any(key not in break_glass
                       for key in _BREAK_GLASS_REQUIRED_KEYS) \
                or not isinstance(break_glass.get("uses"), list):
            problems.append("break_glass is malformed")
    history = ledger.get("break_glass_history")
    if history is not None:
        if not isinstance(history, list) or any(
                not isinstance(entry, dict) for entry in history):
            problems.append(
                "break_glass_history must be a list of objects")
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
        # FEAT-064 P2-2 定案 (review-FEAT-060-R0): per-session trigger
        # counter — the escalation rule counts INDEPENDENT triggers per
        # session on the record, so the A-B-A sequence x→y→x escalates on
        # x's second trigger (B1 字面语义). Without a session identity the
        # counter stays empty (conservative — 宁可漏升不可误升).
        "session_triggers": ({session_id: 1}
                             if session_id is not None else {}),
        "escalated": False,
        "escalated_at": None,
        "notes": "",
    }
    if existing is not None:
        # Independent re-trigger (content changed) — R3 + supersede chain:
        # the old generation is superseded, the new one carries the
        # occurrence counter and the escalation verdict.
        session_triggers = dict(existing.get("session_triggers") or {})
        if session_id is not None:
            session_triggers[session_id] = int(
                session_triggers.get(session_id, 0)) + 1
        record["session_triggers"] = session_triggers
        session_repeat = (
            session_id is not None
            and session_triggers.get(session_id, 0) >= 2)
        record["occurrence"] = int(existing.get("occurrence", 1)) + 1
        record["escalated"] = bool(existing.get("escalated")) or session_repeat
        if session_repeat:
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


# ── FEAT-064: family posture layer (分族 BLOCK 激活) ─────────────────────────


def canonical_family(surface, object_id):
    """Face-5 surface + row key → DEC-224 canonical family id (None for an
    unknown surface — the caller treats None as WARN, the safe default).

    The evidence-log disambiguation reuses the credential judge's authority:
    a row key prefixed ``REVIEW-`` is the review family, everything else in
    evidence-log.md is the evidence family (same prefix discipline as
    ``_row_family_credential_ok`` — no second shape source).
    """
    surface = str(surface or "")
    if surface == "evidence-log.md":
        return (FAMILY_REVIEW
                if str(object_id or "").startswith("REVIEW-")
                else FAMILY_EVIDENCE)
    if surface == "decision-log.md":
        return FAMILY_DECISION
    if surface == "plan-tracker.md":
        return FAMILY_TASK_STATUS
    if surface.endswith(".ops.jsonl"):
        return FAMILY_OPS_LEDGER
    return None


def _posture_issue(issue_type, detail):
    """Face-5 shaped issue dict for the posture layer (consumed by the
    guard's generic issue printer unchanged; never posture='block' — the
    posture layer's own anomalies are WARN-class disclosures)."""
    return {
        "type": issue_type,
        "file": ".governance/" + POSTURE_CONFIG_FILE_NAME,
        "line": None,
        "task_id": "",
        "detail": detail,
        "expected": "JSON object（schema_version={0}, tool={1!r}, "
                    "postures 键⊆{2}）".format(POSTURE_CONFIG_SCHEMA_VERSION,
                                               POSTURE_CONFIG_TOOL,
                                               list(FAMILY_VOCABULARY)),
    }


def _management_refusal(error, detail):
    return {"ok": False, "error": error, "detail": detail}


def load_family_postures(governance_dir):
    """Load the guard-owned posture config → ``(postures, issue)``.

    ``(dict(), None)`` when absent — the all-WARN default (zero footprint,
    byte-identical WARN-era behavior). A corrupt or foreign-schema config
    returns ``(dict(), issue)`` and the guard fails SAFE to all-WARN: a
    broken config must never silently activate BLOCK (false enforcement),
    and never silently deactivate an intended BLOCK either — the loud
    disclosure names the recovery (re-run the activation CLI after fixing
    or deleting the file), so a downgrade attempt cannot pass in silence.
    """
    path = Path(governance_dir) / POSTURE_CONFIG_FILE_NAME
    if not path.is_file():
        return {}, None
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, IOError, OSError,
            ValueError) as exc:
        return {}, _posture_issue(
            "write_guard_posture_config_unreadable",
            "写守卫姿态配置不可读（{0}）——按全 WARN 姿态运行（fail-safe，"
            "响亮披露，不静默）；恢复 = 修复或删除该文件后经 "
            "governance-write-guard --activate-block 重新激活".format(exc))
    problems = []
    if not isinstance(config, dict) \
            or config.get("schema_version") != POSTURE_CONFIG_SCHEMA_VERSION \
            or config.get("tool") != POSTURE_CONFIG_TOOL:
        problems.append(
            "schema mismatch — expected schema_version={0} tool={1!r}".format(
                POSTURE_CONFIG_SCHEMA_VERSION, POSTURE_CONFIG_TOOL))
    postures_cfg = config.get("postures") if isinstance(config, dict) else None
    if not isinstance(postures_cfg, dict):
        problems.append("'postures' must be an object")
    else:
        for family, posture in postures_cfg.items():
            if family not in FAMILY_VOCABULARY:
                problems.append("unknown family {0!r}".format(family))
            elif posture not in POSTURES:
                problems.append(
                    "unknown posture {0!r} for family {1!r}".format(
                        posture, family))
    if problems:
        return {}, _posture_issue(
            "write_guard_posture_config_unreadable",
            "写守卫姿态配置 schema 不识别（{0}）——按全 WARN 姿态运行"
            "（fail-safe，响亮披露，不静默）；恢复 = 修复或删除该文件后经 "
            "governance-write-guard --activate-block 重新激活".format(
                "; ".join(problems)))
    return dict(postures_cfg), None


def activate_family_postures(governance_dir, *, families, posture, reason,
                             authorized_by, now=None):
    """Write/merge the family posture config (guard-owned artifact).

    Returns ``(payload, refusal)``. Fail-closed refusals: empty
    reason/authorized_by (deactivation — the B-12 rollback — is itself a
    governed, non-silent act), unknown family, illegal posture value, and
    an unreadable EXISTING config (never blindly overwrite what cannot be
    parsed). The config keeps an append-only ``history`` of posture
    changes (at/by/reason/set) so every flag flip is auditable.
    """
    families = [str(f).strip() for f in (families or []) if str(f).strip()]
    reason = str(reason or "").strip()
    authorized_by = str(authorized_by or "").strip()
    if posture not in POSTURES:
        return None, _management_refusal(
            "schema_violation",
            "posture must be one of {0}, got {1!r}".format(
                list(POSTURES), posture))
    if not families:
        return None, _management_refusal(
            "schema_violation",
            "families must name at least one managed family {0}".format(
                list(FAMILY_VOCABULARY)))
    unknown = [f for f in families if f not in FAMILY_VOCABULARY]
    if unknown:
        return None, _management_refusal(
            "unknown_family",
            "unknown managed families {0} — closed vocabulary {1}".format(
                unknown, list(FAMILY_VOCABULARY)))
    if not reason:
        return None, _management_refusal(
            "schema_violation",
            "reason is required — a posture change without a recorded why "
            "would be a silent enforcement flip (FEAT-064 限定留痕)")
    if not authorized_by:
        return None, _management_refusal(
            "schema_violation",
            "authorized-by is required — the posture flip records WHO "
            "authorized it (FEAT-064 限定留痕)")
    governance_dir = Path(governance_dir)
    existing_postures, existing_issue = load_family_postures(governance_dir)
    if existing_issue is not None:
        return None, _management_refusal(
            "posture_config_unreadable",
            "existing posture config is unreadable/unrecognized — refusing "
            "to blind-write over it (fix or delete "
            "{0} first)".format(POSTURE_CONFIG_FILE_NAME))
    path = governance_dir / POSTURE_CONFIG_FILE_NAME
    raw = None
    if path.is_file():
        raw = json.loads(path.read_text(encoding="utf-8"))
    history = list((raw or {}).get("history") or [])
    stamp = _now_iso(now)
    change = {"at": stamp, "by": authorized_by, "reason": reason,
              "set": {f: posture for f in families}}
    history.append(change)
    merged = dict(existing_postures)
    for family in families:
        merged[family] = posture
    config = {
        "schema_version": POSTURE_CONFIG_SCHEMA_VERSION,
        "tool": POSTURE_CONFIG_TOOL,
        "updated_at": stamp,
        "updated_by": authorized_by,
        "reason": reason,
        "postures": merged,
        "history": history,
    }
    payload = (json.dumps(config, ensure_ascii=False, indent=2,
                          sort_keys=True) + "\n").encode("utf-8")
    _atomic_write_bytes(path, payload)
    return {"changed": families, "posture": posture,
            "postures": merged, "path": str(path)}, None


# ── FEAT-064: break-glass channel (恢复专用, 限定留痕) ───────────────────────


def _break_glass_validity(grant, *, now):
    """Validity judgment of one break-glass grant → ``(active, why)``."""
    if not isinstance(grant, dict):
        return False, "malformed grant"
    uses = grant.get("uses")
    if not isinstance(uses, list):
        return False, "malformed uses"
    max_uses = grant.get("max_uses")
    if isinstance(max_uses, bool) or not isinstance(max_uses, int):
        return False, "malformed max_uses"
    if len(uses) >= max_uses:
        return False, "uses exhausted ({0}/{1})".format(len(uses), max_uses)
    expires_at = grant.get("expires_at")
    if not isinstance(expires_at, str):
        return False, "malformed expires_at"
    try:
        expiry = datetime.fromisoformat(expires_at)
    except ValueError:
        return False, "malformed expires_at"
    if now >= expiry:
        return False, "expired at {0}".format(expires_at)
    return True, None


def grant_break_glass(governance_dir, *, reason, authorized_by,
                      families=None, ttl_hours=BREAK_GLASS_DEFAULT_TTL_HOURS,
                      max_uses=BREAK_GLASS_DEFAULT_MAX_USES, now=None,
                      timeout_seconds=10.0):
    """Open the recovery break-glass window (written into the violation
    ledger's ``break_glass`` section — the ledger is the audit store).

    Returns ``(grant, refusal)``. Refusals (fail-closed): empty
    reason/authorized_by; unknown scope family; non-positive ttl / max_uses;
    a window already active (one at a time); the ledger corrupt; no family
    currently BLOCK-active (限定何时可用 — a bypass with nothing to bypass
    is refused, the channel exists for guard-self-repair, not as a
    standing key); lock contention.
    """
    reason = str(reason or "").strip()
    authorized_by = str(authorized_by or "").strip()
    if not reason:
        return None, _management_refusal(
            "schema_violation",
            "reason is required — a break-glass window without a recorded "
            "why would be a silent bypass (限定留痕)")
    if not authorized_by:
        return None, _management_refusal(
            "schema_violation",
            "authorized-by is required — the window records WHO authorized "
            "it (限定留痕)")
    scope = [str(f).strip() for f in (families or [BREAK_GLASS_ALL])
             if str(f).strip()]
    if not scope:
        return None, _management_refusal(
            "schema_violation", "families scope must not be empty")
    unknown = [f for f in scope
               if f != BREAK_GLASS_ALL and f not in FAMILY_VOCABULARY]
    if unknown:
        return None, _management_refusal(
            "unknown_family",
            "unknown break-glass scope families {0} — closed vocabulary "
            "{1} (or {2!r} for every BLOCK-active family)".format(
                unknown, list(FAMILY_VOCABULARY), BREAK_GLASS_ALL))
    if isinstance(ttl_hours, bool) or not isinstance(ttl_hours, (int, float)) \
            or ttl_hours <= 0:
        return None, _management_refusal(
            "schema_violation",
            "ttl-hours must be a positive number, got {0!r}".format(
                ttl_hours))
    if isinstance(max_uses, bool) or not isinstance(max_uses, int) \
            or max_uses < 1:
        return None, _management_refusal(
            "schema_violation",
            "max-uses must be a positive int, got {0!r}".format(max_uses))
    governance_dir = Path(governance_dir)
    now = now if now is not None else datetime.now()
    postures, posture_issue = load_family_postures(governance_dir)
    if posture_issue is not None:
        return None, _management_refusal(
            "posture_config_unreadable",
            "posture config unreadable — the BLOCK-active set cannot be "
            "judged (fix the config first)")
    if not any(p == POSTURE_BLOCK for p in postures.values()):
        return None, _management_refusal(
            "no_block_active",
            "no family is BLOCK-active — the break-glass channel exists "
            "for BLOCK enforcement repair, there is nothing to bypass")
    stamp = _now_iso(now)
    grant = {
        "grant_id": _new_id("bg-", {"by": authorized_by, "at": stamp}),
        "reason": reason,
        "authorized_by": authorized_by,
        "families": scope,
        "issued_at": stamp,
        "expires_at": (now + timedelta(hours=ttl_hours))
        .replace(microsecond=0).isoformat(),
        "max_uses": max_uses,
        "uses": [],
    }
    try:
        with _TargetLock(governance_dir / LEDGER_FILE_NAME, timeout_seconds):
            ledger, load_issue = load_ledger(governance_dir)
            if load_issue is not None:
                return None, _management_refusal(
                    "ledger_corrupt",
                    "violation ledger unreadable — the audit store cannot "
                    "hold the grant (R6: repair the ledger first)")
            if isinstance(ledger.get("break_glass"), dict):
                return None, _management_refusal(
                    "break_glass_active",
                    "a break-glass window is already active ({0}) — one "
                    "window at a time; clear it first".format(
                        ledger["break_glass"].get("grant_id")))
            ledger["break_glass"] = grant
            save_ledger(governance_dir, ledger)
    except StoreError as exc:
        return None, _management_refusal(
            "ledger_lock_busy", "ledger lock busy: {0}".format(exc))
    return dict(grant), None


def active_break_glass_families(governance_dir, *, postures, now=None):
    """Valid break-glass scope → ``(honored_families, issue)``.

    ``honored`` = the BLOCK-active families the valid window covers (the
    ``*`` token expands to every currently BLOCK-active family). An inert
    window (expired / uses exhausted) returns an EMPTY honored set plus a
    loud stale-disclosure issue — the block stands and the staleness is
    named. A corrupt ledger returns an empty set WITHOUT its own issue
    (the ledger corruption is already disclosed upstream; fail-closed —
    an unverifiable grant is never honored).
    """
    governance_dir = Path(governance_dir)
    ledger, load_issue = load_ledger(governance_dir)
    if load_issue is not None:
        return frozenset(), None
    grant = ledger.get("break_glass")
    if not isinstance(grant, dict):
        return frozenset(), None
    valid, why = _break_glass_validity(grant, now=now or datetime.now())
    if not valid:
        return frozenset(), _issue(
            "break_glass_inert",
            "break-glass 窗口已失效（{0}）——本轮按 BLOCK 姿态执行；清理 = "
            "governance-write-guard --break-clear（响亮披露，不静默）".format(
                why),
            "有效窗口或经 --break-clear 清理后的无窗口状态")
    scope = grant.get("families") or []
    block_active = {family for family, posture in (postures or {}).items()
                    if posture == POSTURE_BLOCK}
    if BREAK_GLASS_ALL in scope:
        honored = block_active
    else:
        honored = block_active.intersection(scope)
    return frozenset(honored), None


def record_break_glass_use(governance_dir, *, run_id, now=None,
                           timeout_seconds=10.0):
    """One audit event per guard CLI persist-path run under a valid window
    (不可静默记录). Returns ``(recorded, issue)``: no window / inert window
    → ``(False, None)`` (the staleness is disclosed by the face judge);
    ledger corrupt → ``(False, None)`` (already loud upstream — and a
    corrupt audit store fail-closes the honor path anyway); lock busy →
    ``(False, issue)`` (the audit gap is itself loud, never silent).
    """
    governance_dir = Path(governance_dir)
    now = now if now is not None else datetime.now()
    try:
        with _TargetLock(governance_dir / LEDGER_FILE_NAME, timeout_seconds):
            ledger, load_issue = load_ledger(governance_dir)
            if load_issue is not None:
                return False, None
            grant = ledger.get("break_glass")
            if not isinstance(grant, dict):
                return False, None
            valid, _why = _break_glass_validity(grant, now=now)
            if not valid:
                return False, None
            uses = grant.setdefault("uses", [])
            uses.append({"at": _now_iso(now), "run_id": run_id})
            save_ledger(governance_dir, ledger)
            return True, None
    except StoreError as exc:
        return False, _issue(
            "break_glass_use_unrecorded",
            "break-glass use 审计事件写入失败（{0}）——窗口审计不完整（响亮"
            "披露，不静默）；复跑本命令补记，收敛后 --break-clear 清理".format(
                exc),
            "可写的违规台账")


def clear_break_glass(governance_dir, *, cleared_by, reason, now=None,
                      timeout_seconds=10.0):
    """Clear the active window — the grant (with its use events) moves to
    ``break_glass_history`` (audit retained). Returns ``(payload,
    refusal)``; refusals: empty cleared_by/reason, no active window,
    corrupt ledger, lock contention."""
    cleared_by = str(cleared_by or "").strip()
    reason = str(reason or "").strip()
    if not cleared_by:
        return None, _management_refusal(
            "schema_violation",
            "authorized-by is required to clear a window (audit)")
    if not reason:
        return None, _management_refusal(
            "schema_violation",
            "reason is required to clear a window (audit)")
    governance_dir = Path(governance_dir)
    stamp = _now_iso(now)
    try:
        with _TargetLock(governance_dir / LEDGER_FILE_NAME, timeout_seconds):
            ledger, load_issue = load_ledger(governance_dir)
            if load_issue is not None:
                return None, _management_refusal(
                    "ledger_corrupt",
                    "violation ledger unreadable (R6: repair first)")
            grant = ledger.get("break_glass")
            if not isinstance(grant, dict):
                return None, _management_refusal(
                    "no_active_break_glass", "no active break-glass window")
            cleared = dict(grant)
            cleared["cleared_at"] = stamp
            cleared["cleared_by"] = cleared_by
            cleared["clear_reason"] = reason
            history = list(ledger.get("break_glass_history") or [])
            history.append(cleared)
            ledger["break_glass_history"] = history
            ledger["break_glass"] = None
            save_ledger(governance_dir, ledger)
    except StoreError as exc:
        return None, _management_refusal(
            "ledger_lock_busy", "ledger lock busy: {0}".format(exc))
    return {"cleared": cleared.get("grant_id"),
            "uses_recorded": len(cleared.get("uses") or [])}, None


# ── FEAT-064: per-surface baseline clamp (R2 BLOCK 翻转面) ───────────────────


def read_previous_baseline(state_path):
    """The CURRENT state-file content = the previous baseline snapshot (read
    before any write — the clamp reverts blocked surfaces to it). Unreadable
    → ``None`` (the clamp then WITHHOLDS blocked surfaces' fresh entries —
    loud, never guessed)."""
    path = Path(state_path)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, IOError, OSError,
            ValueError):
        return None


def blocked_surfaces(ledger, *, detections, eligible_ids, family_postures):
    """Surfaces whose baseline must NOT advance this run (the R2 BLOCK
    flip): a surface is blocked when it carries (a) a fresh BLOCK-family
    detection this run, or (b) an open NON-eligible BLOCK-family violation.
    An ELIGIBLE violation's surface stays unblocked — the consumption
    transaction carries that surface's CURRENT snapshot (the remediated
    credentialed row enters the baseline bundled with the consume)."""
    postures = family_postures or {}
    eligible = set(eligible_ids or ())
    blocked = set()
    for vid, record in (ledger.get("violations") or {}).items():
        if record.get("status") != STATUS_OPEN or vid in eligible:
            continue
        family = canonical_family(record.get("family"),
                                  record.get("object_id"))
        if family is not None and postures.get(family) == POSTURE_BLOCK:
            blocked.add(record.get("family"))
    for detection in detections or []:
        family = canonical_family(detection.get("family"),
                                  detection.get("object_id"))
        if family is not None and postures.get(family) == POSTURE_BLOCK:
            blocked.add(detection.get("family"))
    return blocked


def clamp_baseline_target(baseline_target, previous_baseline, blocked):
    """Revert each blocked surface's baseline entry to its previous snapshot
    (the window stays open — 不吸收不前移); a blocked surface with NO
    previous entry (baseline-rebuild edge) has its fresh entry WITHHELD so
    the re-amnesty cannot silently absorb an open window (each run then
    re-discloses the amnesty loudly until the window closes). No blocked
    surfaces → the target returned unchanged (byte-identical WARN path)."""
    if not blocked:
        return baseline_target
    files = dict((baseline_target or {}).get("files") or {})
    prev_files = dict((previous_baseline or {}).get("files") or {})
    for surface in blocked:
        prev_entry = prev_files.get(surface)
        if isinstance(prev_entry, dict) and "rows" in prev_entry:
            files[surface] = prev_entry
        else:
            files.pop(surface, None)
    clamped = dict(baseline_target or {})
    clamped["files"] = files
    return clamped


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
    (single atomic ledger write).

    P2-1 (review-FEAT-060-R0, fixed in FEAT-064): ``hook_identity`` is the
    DETECTION-side identity (which command observed the violation) and is
    deliberately NOT overwritten at consumption — the consumer identity
    already lives in ``consumption_event.consumer``; overwriting it would
    destroy the observation provenance the moment a non-default invoker
    (``GOVERNANCE_GUARD_INVOKER``) records a violation.
    """
    stamp = _now_iso(now)
    for vid in txn["violation_ids"]:
        record = ledger["violations"].get(vid)
        if record is None:
            continue
        record["status"] = STATUS_CONSUMED
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
                              family_postures=None, timeout_seconds=10.0):
    """One guard CLI run's violation-state-machine step (FEAT-060; FEAT-064
    posture-aware).

    Order: resume pending transaction → record detections (dedupe /
    supersede / escalate) → compute the per-surface baseline clamp (FEAT-064
    R2 flip: BLOCK-active families' open windows hold their surface's
    baseline at the previous snapshot — the WARN-once-then-absorb path does
    not exist under BLOCK) → consume eligible open violations through the
    recoverable transaction (bundling the CLAMPED baseline target). Returns
    ``{"issues", "consumed", "baseline_written_by_txn",
    "skip_baseline_advance", "baseline_target_effective"}``:

    * ``baseline_written_by_txn`` — the transaction already wrote THIS
      run's (clamped) baseline; the caller must not write it again.
    * ``skip_baseline_advance`` — R6 (corrupt ledger) or diverged
      transaction: the caller must NOT advance the baseline this run
      (不吸收不前移) and the window stays open for the next run.
    * ``baseline_target_effective`` — the baseline the caller's plain
      advance must write (the clamped target when surfaces are blocked;
      otherwise the original target — byte-identical to the FEAT-060
      behavior when no BLOCK posture is active).

    WARN posture is preserved by construction: with the default all-WARN
    posture the clamp is inert (blocked = ∅ → effective == original), this
    step only appends WARN-class issues to face 5 and never changes the
    face status or the guard exit code.
    """
    governance_dir = Path(governance_dir)
    result = {"issues": [], "consumed": [],
              "baseline_written_by_txn": False,
              "skip_baseline_advance": False,
              "baseline_target_effective": None}
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
    # FEAT-064 R2 flip — per-surface baseline clamp under BLOCK posture.
    blocked = blocked_surfaces(ledger, detections=detections or [],
                               eligible_ids=eligible,
                               family_postures=family_postures)
    effective_target = baseline_target
    if blocked:
        previous = read_previous_baseline(state_path)
        effective_target = clamp_baseline_target(baseline_target, previous,
                                                 blocked)
        withheld = [surface for surface in sorted(blocked)
                    if surface not in (effective_target.get("files") or {})]
        for surface in withheld:
            # A blocked surface with no previous baseline entry: the fresh
            # (re-)amnesty entry is WITHHELD — disclosed every run until
            # the window closes (never a silent absorb).
            result["issues"].append(_issue(
                "block_window_baseline_hold",
                "面 {0} 存在未闭合 BLOCK 族违规且无前像基线条目——本轮拒绝"
                "写入其新建基线条目（amnesty 扣留，防止基线重建静默吸收未决"
                "窗口）；补救 = 写入器补机器凭证 → 复跑自动消费".format(
                    surface),
                "窗口闭合后基线条目随消费事务落位"))
    result["baseline_target_effective"] = effective_target
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
        baseline_target=effective_target, run_id=run_id, now=now,
        timeout_seconds=timeout_seconds)
    if payload.get("ok"):
        result["consumed"].extend(payload["consumed"])
        result["baseline_written_by_txn"] = True
    else:
        # Refusal happened before the journal write — zero residue; the
        # baseline advance proceeds per posture (WARN: absorb as pinned;
        # BLOCK: blocked surfaces hold their previous snapshot) and the
        # open violations stay open (R1).
        result["issues"].append(_issue(
            "violation_consumption_refused",
            "消费事务被拒（{0}）——{1}；违规保持 open，基线推进按姿态执行"
            "（WARN：照常吸收；BLOCK：被阻塞面保持前像——不吸收不前移）"
            "（本条为响亮披露，不阻断）".format(
                payload.get("error"), payload.get("detail")),
            "注册消费者 + 有效单次授权 + open 违规"))
    return result


# ── FEAT-064: guard CLI management modes (posture + break-glass) ─────────────


def _split_families(text):
    """Comma/semicolon family list → cleaned list (empty entries dropped)."""
    return [part.strip() for part in str(text or "").replace(";", ",").split(",")
            if part.strip()]


def _management_report_lines(action, payload, governance_dir, now=None):
    """Human-readable management-mode report (the leaf module owns the
    rendering — the engine's print budget does not grow: the
    bootstrap_aggregate/governance_cost precedent)."""
    lines = ["=== Write-guard family postures (FEAT-064 分族 BLOCK 激活) ==="]
    if action in ("activate_block", "deactivate_block"):
        lines.append(
            "  {0}: {1} → {2}".format(
                "BLOCK 激活" if action == "activate_block" else "回退 WARN",
                ", ".join(payload["changed"]), payload["posture"]))
        lines.append("  配置工件: {0}".format(payload["path"]))
    elif action == "break_grant":
        lines.append("  break-glass 窗口已授予（限定留痕——不可静默）:")
        lines.append("    grant: {0}".format(payload.get("grant_id")))
        lines.append("    操作者: {0}".format(payload.get("authorized_by")))
        lines.append("    理由: {0}".format(payload.get("reason")))
        lines.append("    范围: {0}".format(payload.get("families")))
        lines.append("    有效期至: {0}".format(payload.get("expires_at")))
        lines.append("    次数上限: {0}".format(payload.get("max_uses")))
    elif action == "break_clear":
        lines.append("  break-glass 窗口已清理（审计入 break_glass_history）:")
        lines.append("    grant: {0}".format(payload.get("cleared")))
        lines.append("    use 事件: {0}".format(payload.get("uses_recorded")))
    lines.append("  当前有效姿态 (裁定表 = FAMILY_RULING_DECLARATION——"
                 "枚举基线 FEAT-049 写入器契约注册表):")
    postures, issue = load_family_postures(governance_dir)
    for family in FAMILY_VOCABULARY:
        ruling = FAMILY_RULING_DECLARATION[family]
        active = postures.get(family, POSTURE_WARN)
        marker = "  ← BLOCK 已激活" if active == POSTURE_BLOCK else ""
        lines.append("    {0:<12} 裁定={1:<5} 现值={2:<5}{3}  [{4}]".format(
            family, ruling["target"], active, marker, ruling["wave"]))
    if issue is not None:
        lines.append("  [!] {0}".format(issue["detail"]))
    ledger, _ledger_issue = load_ledger(governance_dir)
    grant = ledger.get("break_glass") if isinstance(ledger, dict) else None
    if isinstance(grant, dict):
        valid, why = _break_glass_validity(
            grant, now=now if now is not None else datetime.now())
        lines.append(
            "  break-glass: {0}（{1}; uses {2}/{3}）".format(
                grant.get("grant_id"),
                "有效" if valid else "已失效: {0}".format(why),
                len(grant.get("uses") or []), grant.get("max_uses")))
    else:
        lines.append("  break-glass: 无活动窗口")
    return lines


def run_guard_management_cli(action, args, *, governance_dir, now=None):
    """The governance-write-guard CLI's family-posture management modes
    (FEAT-064): ``activate_block`` / ``deactivate_block`` /
    ``show_posture`` / ``break_grant`` / ``break_clear`` / ``break_show``.

    Prints its own report (leaf-module precedent — the engine's print
    budget does not grow) and returns the process exit code: 0 = done,
    2 = fail-closed refusal (structured error on stderr, callers branch on
    the code, never on prose).
    """
    governance_dir = Path(governance_dir)
    payload = None
    refusal = None
    if action in ("activate_block", "deactivate_block"):
        families = _split_families(
            getattr(args, action, "") or getattr(args, "families", ""))
        payload, refusal = activate_family_postures(
            governance_dir, families=families,
            posture=POSTURE_BLOCK if action == "activate_block"
            else POSTURE_WARN,
            reason=getattr(args, "reason", ""),
            authorized_by=getattr(args, "authorized_by", ""), now=now)
    elif action == "show_posture":
        refusal = None
    elif action == "break_grant":
        payload, refusal = grant_break_glass(
            governance_dir,
            reason=getattr(args, "reason", ""),
            authorized_by=getattr(args, "authorized_by", ""),
            families=_split_families(getattr(args, "families", "")) or None,
            ttl_hours=(getattr(args, "ttl_hours", None)
                       if getattr(args, "ttl_hours", None) is not None
                       else BREAK_GLASS_DEFAULT_TTL_HOURS),
            max_uses=(getattr(args, "max_uses", None)
                      if getattr(args, "max_uses", None) is not None
                      else BREAK_GLASS_DEFAULT_MAX_USES),
            now=now)
    elif action == "break_clear":
        payload, refusal = clear_break_glass(
            governance_dir,
            cleared_by=getattr(args, "authorized_by", ""),
            reason=getattr(args, "reason", ""), now=now)
    elif action == "break_show":
        refusal = None
    else:
        refusal = _management_refusal("unknown_action",
                                      "unknown management action {0!r}"
                                      .format(action))
    if refusal is not None:
        print("[REFUSED] write-guard {0}: {1} ({2})".format(
            action, refusal.get("detail"), refusal.get("error")),
            file=sys.stderr)
        return 2
    for line in _management_report_lines(action, payload or {},
                                         governance_dir, now=now):
        print(line)
    if action == "break_show":
        ledger, _issue = load_ledger(governance_dir)
        grant = ledger.get("break_glass") if isinstance(ledger, dict) else None
        if isinstance(grant, dict):
            print("  活动窗口: {0}".format(json.dumps(
                grant, ensure_ascii=False, sort_keys=True)))
        else:
            print("  活动窗口: 无")
        history = (ledger or {}).get("break_glass_history") or []
        print("  历史窗口: {0} 条".format(len(history)))
    return 0
