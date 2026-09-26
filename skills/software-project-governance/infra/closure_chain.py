#!/usr/bin/env python3
"""closure-chain — the pure sequence orchestrator for one standard closure
(M3 vertical slice, version-plan-0.86.0 §2 batch 2.1/2.2, FEAT-056).

Design sources (quoted constraints, not re-derived here):

  * arch round-2 §2 — forward recovery (断点续传/幂等重入), NO cross-git/push
    rollback; the recovery rule table (evidence 已写 tracker 未更新 → 复用原
    evidence ID 续; commit 成功状态未落盘 → 核验目标不重复提交; push 凭据失效
    → blocked+诊断等凭据修复; push 结果不明 → 先核远端再决定); the
    persistence checklist (closure_id / 输入摘要 / 已完成步骤及产物 ID /
    失败原因重试条件 / 外部动作结果不明标 UNKNOWN); the self-reference trap
    (「push 成功的状态记录」不入其描述的 commit — closure 运行状态与业务记录
    分离); the event carrier ruling (复用既有 loop 事件协议/持久化机器,
    不默认塞同一日志文件 — 独立 closure 日志分域).
  * arch round-3 BT-9 — chaos kill semantics: 子进程写入器 + 父进程测试控制
    器 + 命名故障点; no TTY, no SIGKILL constant (Popen.kill() cross-platform);
    hard-terminate vs raise-exception are SEPARATE test classes; kill ≠ 掉电/
    存储故障持久性保证; **the injection interface lives in internal test
    entry points only and is never exposed on the production CLI**.
  * BT-7 (evolution §5) — the chain engine itself carries ZERO business
    logic: a chain is a declared step sequence, each step invoking an
    existing governed CLI (task-row-update / evidence-append /
    decision-append / locks-amend ...).  The kill-switch (DoD 8) is the
    fallback to the per-step M7.4 protocol: every step's command runs
    standalone; engine removal degrades to atomic CLIs, never to hand
    edits.
  * evolution §2.1 — effect-based resume (查世界不信日志): resume probes the
    world (row flipped? evidence present? lock shrunk?) BEFORE re-running a
    step; the log is audit + recovery context, never the truth source.
  * contracts m0-r1 (read-only) — EXECUTION_RESULTS (succeeded/failed/
    unknown), ERROR_CODE_DISPOSITIONS, SchemaVersionWindow, operation-id
    form, IDEMPOTENCY_MODEL = "effect_based".

What this module IS:

  * a declarative chain runner: step kinds ``cli`` (governed writer CLI),
    ``external`` (declared outside-the-chain action, used by fixtures/tests
    only in 0.86.0 — commit/push stay OUT of the production standard chain),
    ``summary`` (engine-computed ready-to-commit endpoint);
  * a closure event journal on its OWN domain file
    (``<root>/.governance/closure-events.jsonl``) built on the
    ``loop_event_log`` module machine — append/read/monotonicity are the
    reused primitives (zero second implementation of the persistence
    machine); the closure event types/fields are domain-owned per the
    round-2 carving (类型/schema 版本/closure_id/顺序号 分域);
  * effect probes (a small closed, read-only set) that let resume check the
    world first: task row state (via the writer's own ``--inspect``),
    operation-marker anchor in a target file, lock TTL ceiling (agent-locks
    parse), git object existence / HEAD message (argv-list git, no shell),
    generic read-only command exit;
  * a ready-to-commit summary endpoint + ``--finalize`` explicit gate —
    git operations are NOT chain steps (权限语义不焊死进软件); ``--finalize``
    only VERIFIES the operator's commit exists (read-only) and records the
    fact; the closure journal artifacts are reported as ``do_not_stage``
    for the commit the summary describes (self-reference constraint).

What this module is NOT:

  * not a writer — it never parses or writes plan-tracker/evidence/decision
    content; every governed effect goes through the batch-1 writer CLIs as
    subprocesses;
  * not wired into the engine dispatch — standalone CLI only (``python
    closure_chain.py ...``), mirroring the writers' pre-FEAT-055 posture;
    engine wiring is a later-slice decision (frozen face stays untouched);
  * not a crash-durability oracle — BT-9 chaos tests prove kill+resume at
    protocol boundaries; they do NOT derive power-loss/storage-failure
    guarantees (round-3 verbatim).

Reliability posture (DoD, evolution §4, items 0-9): untrusted-input argv
substitution (lists only, no shell), pre-execution full spec validation,
deterministic per-step operation ids (stable across resume → writer-level
replay idempotency), loop_event_log append/re-read machine, dry-run +
structured results, resume/reconcile recovery (no hand-editable half
state), guard tests (concurrent resume, crash points, CJK payload, repeated
execution, torn journal line), progressive adoption (standalone opt-in,
kill-switch to per-step CLIs), machine provenance on every event
(``actor = "closure-chain/0.86.0-batch2"``).

Supported platforms (DoD 3): Windows NTFS + POSIX — persistence reuses
loop_event_log's append discipline (explicit UTF-8, single-write atomic
line, cross-process lock file); the run lock mirrors the
governance-store lockfile discipline (bounded acquire, hard refusal).

Fault injection (round-3 BT-9, TEST-ONLY — internal entry points): the
runner consults the ``CLOSURE_CHAIN_TEST_FAULT_POINTS`` environment
variable at named protocol-boundary fault points
(``post-step-effect:<step_id>``, ``post-finalize-verify``,
``post-generations-preread`` — the FEAT-063 takeover window between the
lock-out pre-read and the generations lock).  When set (by
the chaos test's parent controller, never by the production CLI), the child
process writes a handshake marker file and pauses until the parent kills
it (Popen.kill) or releases it.  No CLI flag exposes this surface.

Registered gap (honest disclosure, ticket FEAT-056 design point 5): the
governance_store has NO ``locks-release`` command; the standard chain's
lock step is carried by ``locks-amend`` TTL shrink (every lock owned by the
task shrunk to a small ceiling).  Actual lock-entry removal/removal of
active_tasks remains a registered gap for a later slice — reported in the
chain output, never silently assumed.

Single-flight assumption (FEAT-056 R0 P3-4 disclosure, updated FEAT-063):
the per-closure run lock makes ONE closure id safe against concurrent
resumes, but it does NOT arbitrate two DIFFERENT closures driving the SAME
task in parallel — both would legitimately flip the same task row / append
their own evidence rows (evolution §6② registered 0.87 open question).
FEAT-063's execution-generation fence closes this shape FOR TASKS BOUND BY
A TAKEOVER RECORD (a non-holder closure refuses at the write-side entry/
step checks before any effect); for UNBOUND tasks (no record) the guardrail
still does not exist — operators MUST run one closure per task at a time
(单 closure 单飞), the chain neither detects nor prevents the
parallel-siblings shape there.

Release-window bootstrap (FIX-383, version-plan-0.88.0 §2 B2 — rollback
§8 #7 ⑩拆票之一): the release chain (M-1~M-8) depends on checkers/writers
whose OWN state can sit in an intermediate condition across a version
switch — the guard reconciliation baseline not re-generated, a
violation-ledger line-index drift (账本行号漂移), a guard state file whose
schema the current code no longer reads, or a pending FEAT-060 consumption
transaction.  The ``release-window-bootstrap`` built-in chain converges
exactly that world through ONE governed recovery action (verify_workflow
``write-guard-bootstrap`` — guard-owned artifacts only, zero
governance-record writes), reusing the FEAT-060 three-branch world-judged
transaction resume and the effect-based resume machinery above: the
step's read-only ``--check-only`` probe decides reconcile-vs-execute at
every run/resume boundary (查世界不信日志), so a mid-switch interruption
re-enters with zero manual repair; unjudgeable states halt loudly and are
never silently absorbed.

Cancellation vertical slice (FEAT-062, version-plan-0.88.0 §2 E1 — arch
Q5 minimal slice, rollback-0.86.0 §8 #5 清偿):

  ``cancel_closure`` / the ``cancel`` subcommand terminate a non-finalized
  closure with the restricted entry → CAS → writer-registered op →
  terminal semantics → own-locks-only release → reconciliation sequence:

  1. **Restricted entry** (限定入口): the closure must exist and sit in a
     cancellable state (``CANCELLABLE_STATUSES`` = running / blocked /
     awaiting-world-check / ready); ``finalized`` is an immutable
     terminal; an explicit ``authorized_by`` + single-line ``reason`` are
     required (the decision record needs both; newlines and raw ``|`` are
     refused at the zero-write gate — a pipe would make the DEC row
     deterministically unwritable and the leg permanently pending,
     review-FEAT-062-R0 F-1); steps whose effects are
     UNDETERMINED (``step_unknown`` / dangling ``step_started`` crash
     window) refuse — resume first to converge, then cancel; any
     external-step terminal event refuses (有副作用明确拒绝 — the outside
     effect needs human adjudication, the minimal slice never cancels
     across one).
  2. **CAS**: the per-closure run lock (the SAME lock run/finalize take)
     is the linearization point — a cancel racing finalize yields exactly
     ONE terminal event, the loser refuses; an optional
     ``--expect-status`` optimistic CAS refuses with ``revision_conflict``
     + the observed status (caller re-judges); the terminal append is one
     seq-continuous journal event under the lock. An in-flight chain holds
     the run lock → the cancel refuses ``lock_contention`` (retryable,
     zero changes) — the 在途写冲突 gate.
  3. **Cancellation op registration**: the DEC row is appended THROUGH the
     governed writer CLI (``governance_store decision-append``) — never a
     hand edit (FEAT-064 BLOCK family compliance: the decision row
     family's legal write path is the writer). The per-closure
     deterministic operation ids (``cancel_operation_id``) are the
     idempotency keys; the writer's pending→ok pipeline registers the
     cancellation ops in the ops ledger (可审计).
  4. **DEC/EVD/task terminal semantics** (终态语义): the DEC row records
     authorization + reason; EVD rows appended by the closure REMAIN
     (append-only audit, never erased); the task row is NOT modified by a
     cancellation — its current world state is disclosed read-only in the
     report (completed governed steps are retained effects, disclosed not
     reverted; a revert is a separate governed decision, out of the
     minimal slice).
  5. **Own locks only** (仅释放自有锁 — ARCH-09 same-type per DEC-237
     C1-ARCH-09): a FRESH world read of agent-locks.json decides whether
     the task still holds locks; release goes through the governed
     ``locks-release`` CLI (task-scoped: it removes the task's active
     entry and ONLY file locks whose ``locked_by == task``), so a lock
     whose ownership changed is never released by a stale cancel — a
     stale owner's cancel refuses without releasing the newer owner's
     state, exactly the decision_migration.cancel precedent.
  6. **Reconciliation** (closure 结果 + ops 对账): after the terminal
     event the report re-reads the journal, the ops ledger (read-only,
     fail-safe) and the locks world and reports per-leg states + a
     ``consistent`` verdict.

  Ordering discipline (中断恢复): the terminal journal event lands FIRST
  (one CAS append), then the two writer legs run with deterministic
  per-closure operation ids; a crash/refusal between legs leaves the
  closure terminal and the leg pending — re-running the SAME cancel
  command replays/applies the pending leg at the writer (same id + same
  payload → original result) and reconverges with zero manual repair.
  A replay cancel converges with the RECORDED intent from the journal
  (fresh CLI args are ignored, never re-recorded — the first
  authorization stands; review-FEAT-062-R0 F-5 wording). Resume of a
  cancelled closure is refused (terminal semantics); ``finalize`` of a
  cancelled closure is refused.

  F-5④ combination obligation (version-plan §3): the cancel's
  locks-release leg vs the write-guard's exclusive consumption right
  (FEAT-060/064) is exercised concurrently in the test suite — the cancel
  never touches the violations ledger (consumption stays the registered
  guard CLI's exclusive right), both writers serialize through the shared
  governance-store lock discipline, and both terminal states land exactly
  once.

  Reopen with attempt lineage + execution-generation fencing (FEAT-063,
  version-plan-0.88.0 §2 E2 — rollback-0.86.0 §8 #5 清偿后半):

  **Reopen (重开)**: ``reopen_closure`` / the ``reopen`` subcommand mints a
  successor closure for a TERMINAL closure (``REOPENABLE_STATUSES`` =
  cancelled / finalized) and records the lineage WITHOUT touching any
  original record (append-only audit — the original journal only GAINS
  one event):

  1. the original stays terminal (cancelled stays cancelled, finalized
     stays finalized — reopen never un-terminates; resume of the original
     keeps refusing; a reopen racing cancel/finalize serializes on the
     SAME per-closure run lock — the CAS point);
  2. the successor id is minted fresh; the ORIGINAL journal receives one
     seq-continuous ``closure_reopened`` event (successor id + attempt
     number + authorized_by + reason + prior_status); original records
     are zero-erased (审计链完整);
  3. SINGLE-SUCCESSOR lineage: a second ``reopen`` of the same closure
     refuses (``cross_record_violation``) naming the recorded successor —
     forking the attempt chain would corrupt the numbering; reopen the
     successor's terminal state instead (the chain deepens: attempt N+1);
  4. the successor binds the recorded linkage by running with
     ``--reopen-of <original>``: the run adopts the RECORDED successor id
     (a different ``--closure-id`` refuses — recorded intent stands, fresh
     ids never fork) and injects ``reopen_of``/``reopen_attempt`` into the
     chain inputs, so the successor's ``closure_started`` carries the
     back-link and the inputs digest binds it (a resume carries the same
     flag; conflicting fresh ``--input reopen_*`` values refuse);
  5. authorization discipline is the cancel gate's: ``authorized_by`` +
     ``reason`` required, single-line, no raw ``|`` (FEAT-062 zero-write
     field rules, shared helper).

  **Execution generation / fencing token (异常接管)** — FEAT-061 epoch
  fencing same-type, ARCH-09 owner-token discipline:
  ``takeover_execution`` / the ``takeover`` subcommand promotes the
  task's execution generation in ``.governance/closure-generations.json``
  (closure-domain sidecar; writer-family atomic replace — mkstemp +
  fsync + os.replace + dir fsync — under the generations lock, the
  promotion serialized against the prior holder's run lock AND
  re-validated in-lock: a prior holder that changed between the lock-out
  pre-read and the lock refuses ``lock_contention`` retryable with ZERO
  writes — the acquired run lock belonged to a former holder and the
  real one may be mid-flight, review-FEAT-063-R0 P0-1):
  generation N+1 binds ``--new-holder`` (a closure id). The WRITE SIDE
  enforces the fence (旧执行者恢复后不能继续提交 — 旧代际的写入被拒):

  * ``_run_locked`` re-checks the fence at entry AND before every
    executable step (the FEAT-061 in-lock revalidation shape: entry
    check + write-point re-check); ``finalize`` checks too;
  * a stale generation's run refuses ``revision_conflict`` (structured,
    ZERO effects — no probe, no subprocess, no bookkeeping) and records
    ONE idempotent ``closure_fenced`` audit event; a stale generation's
    ``finalize`` refuses the same way;
  * a stale generation's ``cancel`` still records its terminal + DEC row
    (termination is not submission) but its locks-release leg SKIPS
    (``skipped_fenced``) — a stale owner's cancel never releases the
    newer holder's dispatch locks (ARCH-09 same-type);
  * unbound tasks (no record) are unfenced — zero behavior change,
    backward compatible; an UNREADABLE record fails CLOSED (the
    authority is unjudgeable — repair or remove the sidecar to restore a
    judgeable world); ``--dry-run`` is a read-only proof and never
    fences.

  **Heartbeat semantics (如实 — the honest boundary)**: heartbeat timeout
  does NOT constitute a stop proof (心跳超时不构成停止证明). FEAT-044's
  round-heartbeat mechanism is E3, NOT this slice — this gate never
  reads any heartbeat/TTL as evidence of executor death. Takeover
  requires BOTH (a) explicit human authorization (``authorized_by`` +
  ``reason``, recorded) and (b) the prior holder's run lock being free
  (an in-flight chain refuses ``lock_contention``, retryable). Neither
  condition PROVES the prior executor is dead — they make the human's
  takeover decision explicit and serialize it against an in-flight run;
  the write-side fence is what actually protects the world if the
  judgment is wrong (the stale executor refuses loudly instead of
  writing). Under the run-lock discipline a mid-run fence is unreachable
  via the takeover path (the promotion holds the prior holder's run
  lock); the per-step re-check defends the out-of-band-edit residual and
  keeps the fence true at every write boundary.

  Journal version-aware reader (FIX-391 — REL-089 condition-③ closure
  ticket, DEC-241 附带裁定: the rollback runbook gate becomes CODE):

  The reader knows its own judgment surface — the closed event-type enum
  (``CLOSURE_EVENT_TYPES``) and the envelope schema window. A closure
  whose RAW journal carries an event type or ``schema_version`` outside
  that surface belongs to a NEWER writer; resuming/finalizing it from the
  kept (partial) view is exactly the measured misread vector — a newer
  writer's terminal looks like «active» here and the next append collides
  with an occupied seq. The gate:

    * PREFLIGHT over the COMPLETE raw journal BEFORE any recovery side
      effect (arch ① 预检模式 — «discover the unknown event halfway
      through» is not safe): every journal-consuming WRITE entry —
      run/resume (the ticket MUST), finalize, and the same-vector
      append/derive entries cancel + reopen — refuses ZERO-WRITE first
      (a conflicted journal never gains so much as an idempotent
      closure_fenced audit event from a reader that cannot judge it);
    * the refusal is a structured ``schema_violation`` payload naming
      the unknown types / foreign schema versions (machine-readable
      ``unknown_event_types`` / ``foreign_schema_versions`` lists — the
      per-closure inventory the runbook used to compile by hand);
    * READS stay fail-safe (读 fail-safe、写 fail-closed): status and the
      derivation faces keep disclosing via ``journal_problems`` and never
      gate on the conflict;
    * the writer carries an ANTI-OCCUPATION backstop (ticket
      acceptance — 碰撞向量被写入器侧防占用检查消除): an append whose
      target seq is already occupied in the raw journal raises — the
      collision is machine-impossible even for a path that forgets the
      gate;
    * the forged-tombstone discipline stands (DEC-241): no reader ever
      FABRICATES a known-type tombstone to defend an older reader (P1 /
      append-only) — a tombstone-shaped UNKNOWN event is simply refused:
      never honored as a terminal, never resumed across;
    * backward-compat matrix (tests, 红绿逐格): historical 8-type
      journals and current journals read/complete unchanged (the
      standard chain's lock-leg resume/finalize is NOT falsely
      rejected — arch ③ positive), unknown-type and out-of-window-schema
      journals refuse zero-write (arch ③ negative);
    * lock ownership (arch ②, pinned by tests): the per-closure run-lock
      FILE is never deleted and its byte-range lease is per-fd — after a
      new instance re-acquires the lock, a stale instance's release
      cannot disturb the new holder's lease (dispatch-lock ownership is
      pinned by the cancel locks-release tests: ownership-changed locks
      + skipped_fenced).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from contracts import (  # L0 — consumed read-only, frozen at revision m0-r1
    ERROR_CODE_DISPOSITIONS,
    RESULT_OK,
    SchemaVersionWindow,
    new_operation_id,
    require_operation_id,
)
import loop_event_log  # module machine — append/read/monotonicity REUSED

__all__ = [
    "CANCELLABLE_STATUSES",
    "CLOSURE_EVENT_LOG_FILENAME",
    "CLOSURE_GENERATIONS_FILENAME",
    "CLOSURE_ID_PATTERN",
    "CLOSURE_SCHEMA_VERSION",
    "CLOSURE_TEST_FAULT_ENV",
    "PROBE_KINDS",
    "RELEASE_WINDOW_BOOTSTRAP",
    "REOPENABLE_STATUSES",
    "STEP_KINDS",
    "STANDARD_TICKET_CLOSURE",
    "WRITER_ID",
    "ExecutionFenced",
    "cancel_closure",
    "cancel_operation_id",
    "finalize_closure",
    "main",
    "new_closure_id",
    "reopen_closure",
    "require_closure_id",
    "run_chain",
    "step_operation_id",
    "takeover_execution",
]

WRITER_ID = "closure_chain/0.86.0-batch2"
"""Machine provenance actor stamped on every closure event."""

CLOSURE_SCHEMA_VERSION = 1
"""Closure record-family schema version (journal envelopes + status)."""

CLOSURE_SCHEMA_WINDOW = SchemaVersionWindow(minimum=1, current=1)
"""Face-4 carrier: refuse foreign/newer closure schemas, never guess."""

CLOSURE_ID_PATTERN = r"closure-[0-9a-f]{32}"
"""Closure id form: ``closure-`` + one uuid4 hex (operation-id discipline)."""

_CLOSURE_ID_RE = re.compile(r"^" + CLOSURE_ID_PATTERN + r"$")

CLOSURE_EVENT_LOG_FILENAME = "closure-events.jsonl"
"""Independent closure journal (round-2 §2: 分域文件, 不混入 loop 日志)."""

CLOSURE_LOCK_DIRNAME = "closure-locks"
"""Run-lock directory under ``.governance/`` (governance-store precedent)."""

INFRA_DIR = Path(__file__).resolve().parent

STEP_KINDS: Tuple[str, ...] = ("cli", "external", "summary")
"""Closed step kinds. ``external`` steps exist for declared outside-the-chain
actions; the 0.86.0 production standard chain contains NONE (commit/push 留
链外) — the kind is exercised by the chaos fixtures only."""

PROBE_KINDS: Tuple[str, ...] = (
    "task_row_state",     # writer --inspect: row state == expected?
    "text_anchor",        # operation marker present in target file?
    "lock_ttl_le",        # every lock owned by task shrunk to <= ceiling?
    "git_object_exists",  # git cat-file -e <sha> (read-only, argv-list)
    "git_head_message",   # git log -1 --format=%s contains expected text
    "command_exit",       # generic read-only world-check command exits 0
)
"""Closed effect-probe set. Every probe is READ-ONLY; probes decide
completion (effect-based resume), the journal only audits it."""

CLOSURE_EVENT_TYPES = frozenset({
    "closure_started",    # chain opened (inputs digest bound)
    "step_started",       # step subprocess launched
    "step_completed",     # step effect landed + bookkeeping written
    "step_failed",        # structured refusal/failure (code + disposition)
    "step_unknown",       # external action result unknown (execution=unknown)
    "step_reconciled",    # world probe found the effect; anchor reused
    "closure_ready",      # ready-to-commit summary emitted (finalize pending)
    "closure_finalized",  # --finalize verified the operator commit
    "closure_cancelled",  # FEAT-062 cancellation gate: immutable terminal
    "closure_reopened",   # FEAT-063 reopen: successor lineage recorded
    "closure_fenced",     # FEAT-063 fencing: stale generation refused
})
"""Closed closure event-type enum (domain-owned per round-2 §2 carving)."""

CLOSURE_REQUIRED_FIELDS = (
    "event_id", "timestamp", "unit_id", "event_type", "cas_version",
    "from_version", "actor",
)
"""Required envelope fields — the loop_event_log §5.1 discipline; closure
events are BUILT with loop_event_log.build_event (all fields present) and
validated against this closure-owned tuple (the PARO phase fields are
carried as None by build_event and are not semantically meaningful here)."""

CLOSURE_TEST_FAULT_ENV = "CLOSURE_CHAIN_TEST_FAULT_POINTS"
"""Test-only injection channel (BT-9). Value: JSON
``{"handshake_dir": "<dir>", "points": ["post-step-effect:<step>", ...]}``.
NEVER set by the production CLI; no command-line flag exposes it."""

CANCELLABLE_STATUSES: Tuple[str, ...] = (
    "running", "blocked", "awaiting-world-check", "ready")
"""Closure states a cancellation may terminate (FEAT-062 restricted
entry). ``finalized``/``cancelled`` are immutable terminals — never in
this set; a closure whose step effects are undetermined or which carries
external-step effects is refused by cancel_closure regardless."""

REOPENABLE_STATUSES: Tuple[str, ...] = ("cancelled", "finalized")
"""Closure states a reopen may succeed on (FEAT-063 重开 — 已取消/已完成):
ONLY the two immutable terminals. Reopen never un-terminates the original
— it mints a linked successor; a non-terminal closure needs no reopen
(it can simply resume)."""

CLOSURE_GENERATIONS_FILENAME = "closure-generations.json"
"""Per-task execution-generation record (FEAT-063 takeover fencing) under
``.governance/`` — closure-domain sidecar, same ownership discipline as
the closure journal (never a locks-family or guard-family file)."""

_CANCEL_DECISION_SLOT = "decision"
_CANCEL_LOCKS_SLOT = "locks"
"""Deterministic per-closure cancellation-op slots (idempotency keys for
the two writer legs — the DEC registration and the own-locks release)."""

_CANCEL_LEG_DONE_STATES = ("done", "done_replayed")
"""Leg states that count as converged in the reconciliation verdict."""

_LOCK_STALE_NOTE = "lock file left in place (loop_event_log precedent)"


# ═══════════════════════════════════════════════════════════════════════════
# Identity + deterministic operation ids
# ═══════════════════════════════════════════════════════════════════════════


def new_closure_id() -> str:
    """Fresh closure id (``closure-`` + uuid4 hex — contract form discipline)."""
    return "closure-" + uuid.uuid4().hex


def require_closure_id(where: str, value: Any) -> str:
    """Fail-closed closure-id form check."""
    if not isinstance(value, str) or not _CLOSURE_ID_RE.match(value):
        raise ValueError(
            "{0}: closure id {1!r} does not match {2!r} (generate via "
            "new_closure_id())".format(where, value, CLOSURE_ID_PATTERN))
    return value


def step_operation_id(closure_id: str, step_id: str) -> str:
    """Deterministic per-step operation id — STABLE across resume.

    ``op-`` + first 32 hex of sha256(``closure_id|step_id``).  Stability is
    the resume backbone: a re-run after a crash carries the SAME operation
    id to the writer, so the writer's own effect-based replay protocol (same
    id + same payload → original result, never re-execute) closes the
    duplicate-execution window.  The form satisfies
    ``contracts.require_operation_id``.
    """
    require_closure_id("step_operation_id: closure_id", closure_id)
    if not isinstance(step_id, str) or not re.match(
            r"^[a-z0-9][a-z0-9-]{0,63}$", step_id):
        raise ValueError(
            "step_operation_id: step id {0!r} must match ^[a-z0-9][a-z0-9-]"
            "{{0,63}}$".format(step_id))
    digest = hashlib.sha256(
        "{0}|{1}".format(closure_id, step_id).encode("utf-8")).hexdigest()
    return "op-" + digest[:32]


def cancel_operation_id(closure_id: str, slot: str) -> str:
    """Deterministic per-closure cancellation-op id (FEAT-062 idempotency
    key, ``slot`` ∈ {decision, locks}) — STABLE across cancel retries, so
    a converged retry replays at the writer (same id + same payload →
    original result, never a second row/second release). Same derivation
    discipline as :func:`step_operation_id`."""
    if slot not in (_CANCEL_DECISION_SLOT, _CANCEL_LOCKS_SLOT):
        raise ValueError(
            "cancel_operation_id: slot {0!r} not in {1!r}".format(
                slot, (_CANCEL_DECISION_SLOT, _CANCEL_LOCKS_SLOT)))
    return step_operation_id(closure_id, "cancel-" + slot)


# ═══════════════════════════════════════════════════════════════════════════
# Paths
# ═══════════════════════════════════════════════════════════════════════════


def default_event_log_path(root: Optional[Path] = None) -> Path:
    """The closure journal path: ``<root>/.governance/closure-events.jsonl``.

    Independent domain file — the loop engine's ``loop-event-log.jsonl`` is
    never touched (round-2 §2: 不默认塞同一日志文件).
    """
    base = Path(root) if root is not None else Path.cwd()
    return base / ".governance" / CLOSURE_EVENT_LOG_FILENAME


def _closure_lock_dir(root: Optional[Path] = None) -> Path:
    base = Path(root) if root is not None else Path.cwd()
    return base / ".governance" / CLOSURE_LOCK_DIRNAME


# ═══════════════════════════════════════════════════════════════════════════
# Closure event journal — loop_event_log machine, closure-owned envelope
# ═══════════════════════════════════════════════════════════════════════════


def _validate_closure_event(event: Any) -> List[str]:
    """Closure-envelope validation — the §5.1 discipline, closure-owned enum.

    The persistence machine (atomic single-line append, cross-process lock,
    fail-safe reader, seq monotonicity) is loop_event_log's, reused verbatim.
    The envelope check mirrors ``loop_event_log.validate_event``'s pipeline
    (required fields → closed enum → int sanity) against the closure enum:
    the PARO 14-type enum is intentionally NOT reused (round-2 §2 — the
    independent closure log carries its own 类型/顺序号), so delegating to
    the PARO validator would mis-reject every closure event.
    """
    errors: List[str] = []
    if not isinstance(event, dict):
        return ["closure event is not a dict (got {0})".format(
            type(event).__name__)]
    for name in CLOSURE_REQUIRED_FIELDS:
        if name not in event:
            errors.append("missing required field {0!r}".format(name))
    event_type = event.get("event_type")
    if isinstance(event_type, str) and event_type not in CLOSURE_EVENT_TYPES:
        errors.append(
            "unknown closure event_type {0!r} (closed enum of {1} types)"
            .format(event_type, len(CLOSURE_EVENT_TYPES)))
    for vfield in ("cas_version", "from_version"):
        v = event.get(vfield)
        if v is not None and not (isinstance(v, int)
                                  and not isinstance(v, bool)):
            errors.append(
                "{0!r} must be an integer (not bool) when present (got {1!r})"
                .format(vfield, v))
    return errors


def _append_closure_event(log_path: Path, closure_id: str, event_type: str,
                          seq: int, prev_seq: Optional[int],
                          payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build (loop_event_log.build_event) + append (loop_event_log.append_event)
    one closure event. Returns the envelope that was written."""
    envelope = loop_event_log.build_event(
        closure_id, event_type,
        cas_version=seq, from_version=prev_seq,
        actor=WRITER_ID,
        payload=dict(payload or {}))
    envelope["schema_version"] = CLOSURE_SCHEMA_VERSION
    errors = _validate_closure_event(envelope)
    if errors:  # pragma: no cover - construction is internally controlled
        raise ValueError(
            "closure event construction invalid: {0}".format(errors))
    # FIX-391 writer-side ANTI-OCCUPATION backstop (ticket acceptance —
    # 碰撞向量被写入器侧防占用检查消除): the target seq must be UNOCCUPIED
    # in the RAW journal. The fail-safe reader drops unknown-type lines,
    # so a kept-view next-seq can collide with an already-occupied one
    # (the measured rollback corruption vector: kept=[1,2] → next=3 while
    # raw 3 is occupied). The entry preflight refuses conflicted journals
    # before any append; this backstop makes the collision itself
    # machine-impossible even for a path that forgets the gate.
    # Occupancy counts TRUE integer seqs only — a corrupted bool stamp
    # (True == 1 in Python) must not falsely occupy seq 1.
    occupied = {ev.get("cas_version")
                for ev in loop_event_log.read_events(
                    log_path=log_path, unit_id=closure_id)
                if isinstance(ev, dict)
                and isinstance(ev.get("cas_version"), int)
                and not isinstance(ev.get("cas_version"), bool)}
    if seq in occupied:
        raise ValueError(
            "closure {0}: append refused — journal seq {1} is already "
            "occupied in the raw journal (FIX-391 anti-occupation "
            "backstop; the reader view that produced this seq is stale "
            "or truncated — reload the journal, never double-append)"
            .format(closure_id, seq))
    loop_event_log.append_event(envelope, log_path=log_path)
    return envelope


def _load_closure_events(log_path: Path,
                         closure_id: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Read + validate one closure's events (fail-safe reader reused).

    Returns (events, problems). Malformed lines are skipped by the reused
    reader (torn-line resilience); events failing the closure envelope or
    the reused seq-monotonicity pipeline are reported as problems — resume
    proceeds on the world probes, never on the journal alone.
    """
    raw = loop_event_log.read_events(log_path=log_path, unit_id=closure_id)
    events: List[Dict[str, Any]] = []
    problems: List[str] = []
    for ev in raw:
        errs = _validate_closure_event(ev)
        if errs:
            problems.extend(errs)
            continue
        events.append(ev)
    # Reused monotonicity pipeline: seq → cas_version, prev seq →
    # from_version (strictly +1 per closure).
    problems.extend(loop_event_log.check_cas_monotonicity(events))
    return events, problems


def _next_seq(events: List[Dict[str, Any]]) -> Tuple[int, Optional[int]]:
    if not events:
        return 1, None
    last = events[-1].get("cas_version")
    last_int = last if isinstance(last, int) and not isinstance(last, bool) \
        else 0
    return last_int + 1, last_int


def _journal_version_conflict(log_path: Path,
                              closure_id: str) -> Optional[Dict[str, Any]]:
    """FIX-391 version-aware PREFLIGHT (REL-089 condition-③ closure) —
    classify the closure's COMPLETE raw journal BEFORE any recovery side
    effect (arch ① 预检模式: «discover the unknown event halfway through»
    is not safe — the classification is done up front, over every raw
    line, while the caller is still zero-write).

    ``None`` = every raw event is judgeable in this reader's judgment
    surface (closed event-type enum + envelope schema window). Otherwise
    a zero-write structured ``schema_violation`` refusal: the journal
    carries event type(s) or envelope ``schema_version``(s) this reader
    does not know — the closure's semantics belong to a NEWER writer, and
    resuming/finalizing it from the kept (partial) view is exactly the
    measured misread vector (a newer terminal looks «active», the next
    append collides with an occupied seq). Every journal-consuming WRITE
    entry (run/resume, finalize, cancel, reopen) calls this FIRST; reads
    stay fail-safe — status/derive faces keep disclosing via
    ``journal_problems`` and never gate on the conflict
    (读 fail-safe、写 fail-closed).
    """
    raw = loop_event_log.read_events(log_path=log_path, unit_id=closure_id)
    unknown_types: List[str] = []
    foreign_versions: List[int] = []
    for ev in raw:
        if not isinstance(ev, dict):
            continue
        event_type = ev.get("event_type")
        if isinstance(event_type, str) \
                and event_type not in CLOSURE_EVENT_TYPES \
                and event_type not in unknown_types:
            unknown_types.append(event_type)
        version = ev.get("schema_version")
        # Totality over UNTRUSTED raw journal data: a plain range check
        # instead of CLOSURE_SCHEMA_WINDOW.supports() — the frozen
        # contract helper requires a POSITIVE int and would raise on a
        # hand-written 0/negative stamp, and the preflight must refuse,
        # never crash, on any raw envelope bytes.
        if isinstance(version, int) and not isinstance(version, bool) \
                and not (CLOSURE_SCHEMA_WINDOW.minimum <= version
                         <= CLOSURE_SCHEMA_WINDOW.current) \
                and version not in foreign_versions:
            foreign_versions.append(version)
    if not unknown_types and not foreign_versions:
        return None
    details: List[str] = []
    if unknown_types:
        details.append(
            "unknown event type(s) {0} outside this reader's closed "
            "vocabulary of {1} types".format(unknown_types,
                                             len(CLOSURE_EVENT_TYPES)))
    if foreign_versions:
        details.append(
            "envelope schema_version(s) {0} outside the supported window "
            "[{1},{2}]".format(foreign_versions,
                               CLOSURE_SCHEMA_WINDOW.minimum,
                               CLOSURE_SCHEMA_WINDOW.current))
    return {
        "closure_id": closure_id, "error": True,
        "code": "schema_violation", "disposition": "validation",
        "detail": (
            "closure {0}: journal version conflict (FIX-391 version-aware "
            "reader) — raw journal carries {1}; the closure's semantics "
            "belong to a NEWER writer — resume/finalize/terminal entries "
            "refused with ZERO writes (机器门禁替代回退运行手册). Recovery: "
            "drive the closure from the writer version that owns those "
            "event types, or adjudicate it manually".format(
                closure_id, "; ".join(details))),
        "unknown_event_types": sorted(unknown_types),
        "foreign_schema_versions": sorted(foreign_versions),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Chain spec — declarative, fail-closed parsing (zero business logic)
# ═══════════════════════════════════════════════════════════════════════════

_STEP_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_PLACEHOLDER_RE = re.compile(r"\{([a-z_]+(?::[a-z0-9_-]+)?)\}")


@dataclass(frozen=True)
class StepSpec:
    """One declared step. A chain is a sequence of these; the engine owns
    no step semantics — only the declaration interpreter."""

    step_id: str
    kind: str                       # cli | external | summary
    argv: Tuple[str, ...] = ()      # template; placeholders resolved at run
    probe: Dict[str, Any] = field(default_factory=dict)
    world_check: Tuple[str, ...] = ()  # read-only resolution command (argv)
    blocked_exit_codes: Tuple[int, ...] = ()  # external: → blocked/manual
    timeout_seconds: float = 120.0  # external subprocess timeout → UNKNOWN
    dry_run_flag: Optional[str] = "--dry-run"  # None = writer has no dry-run
    description: str = ""

    def __post_init__(self) -> None:
        if not re.match(_STEP_ID_RE.pattern, self.step_id):
            raise ValueError(
                "StepSpec.step_id {0!r} must match {1!r}".format(
                    self.step_id, _STEP_ID_RE.pattern))
        if self.kind not in STEP_KINDS:
            raise ValueError(
                "StepSpec.kind {0!r} not in closed set {1}".format(
                    self.kind, STEP_KINDS))
        if self.kind == "summary":
            if self.argv:
                raise ValueError(
                    "StepSpec {0!r}: summary steps are engine-computed and "
                    "carry no argv".format(self.step_id))
            return
        if not self.argv or not all(
                isinstance(a, str) and a for a in self.argv):
            raise ValueError(
                "StepSpec {0!r}: argv must be a non-empty list of non-empty "
                "strings (argv-list discipline — no shell, no concatenation)"
                .format(self.step_id))
        if self.kind == "external":
            for flag in ("{task}", "{op:", "{input:"):
                if flag in " ".join(self.argv):
                    raise ValueError(
                        "StepSpec {0!r}: external step argv must not embed "
                        "governed placeholders ({1}...) — external actions "
                        "stay outside the governed write path".format(
                            self.step_id, flag.strip("{}")))
        if self.probe:
            unknown = {self.probe.get("kind")} - set(PROBE_KINDS)
            if unknown:
                raise ValueError(
                    "StepSpec {0!r}: probe kind {1!r} not in closed set {2}"
                    .format(self.step_id, unknown.pop(), PROBE_KINDS))
        if self.world_check and not all(
                isinstance(a, str) and a for a in self.world_check):
            raise ValueError(
                "StepSpec {0!r}: world_check must be an argv list of "
                "non-empty strings".format(self.step_id))
        if self.blocked_exit_codes and not all(
                isinstance(c, int) and not isinstance(c, bool) and c > 0
                for c in self.blocked_exit_codes):
            raise ValueError(
                "StepSpec {0!r}: blocked_exit_codes must be positive ints"
                .format(self.step_id))


@dataclass(frozen=True)
class ChainSpec:
    """A declared chain: id + ordered steps + declared required inputs."""

    chain_id: str
    steps: Tuple[StepSpec, ...]
    required_inputs: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not re.match(r"^[a-z0-9][a-z0-9-]{0,63}$", self.chain_id):
            raise ValueError(
                "ChainSpec.chain_id {0!r} is not a kebab-case id".format(
                    self.chain_id))
        if not self.steps:
            raise ValueError("ChainSpec: a chain needs at least one step")
        ids = [s.step_id for s in self.steps]
        if len(set(ids)) != len(ids):
            raise ValueError(
                "ChainSpec: duplicate step ids {0}".format(
                    sorted({i for i in ids if ids.count(i) > 1})))
        if self.steps[-1].kind != "summary":
            raise ValueError(
                "ChainSpec: the last step must be the ready-to-commit "
                "summary (chain endpoint, round-2 §2)")
        for spec in self.steps[:-1]:
            if spec.kind == "summary":
                raise ValueError(
                    "ChainSpec: summary step {0!r} must be the last step"
                    .format(spec.step_id))


def parse_chain_spec(data: Any) -> ChainSpec:
    """Parse + fully validate a chain spec dict (fail-closed, pre-execution —
    DoD 1: the whole spec validates before any step runs)."""
    if not isinstance(data, dict):
        raise ValueError("chain spec must be a JSON object")
    for key in ("chain_id", "steps"):
        if key not in data:
            raise ValueError("chain spec missing {0!r}".format(key))
    steps = []
    for index, raw in enumerate(data["steps"]):
        if not isinstance(raw, dict):
            raise ValueError("steps[{0}] must be an object".format(index))
        kwargs = dict(raw)
        kwargs["argv"] = tuple(kwargs.get("argv") or ())
        kwargs["world_check"] = tuple(kwargs.get("world_check") or ())
        kwargs["blocked_exit_codes"] = tuple(
            kwargs.get("blocked_exit_codes") or ())
        kwargs["probe"] = dict(kwargs.get("probe") or {})
        steps.append(StepSpec(step_id=kwargs.pop("step_id"),
                              kind=kwargs.pop("kind"), **kwargs))
    required = tuple(data.get("required_inputs") or ())
    if not all(isinstance(r, str) and r for r in required):
        raise ValueError("required_inputs must be a list of names")
    return ChainSpec(chain_id=data["chain_id"], steps=tuple(steps),
                     required_inputs=required)


# ── the one high-frequency standard chain (FEAT-056 design point 5) ────────

STANDARD_TICKET_CLOSURE: Dict[str, Any] = {
    "chain_id": "standard-ticket-closure",
    "required_inputs": [
        "evd_type", "evd_description", "evd_basis", "evd_artifacts",
    ],
    "steps": [
        {
            "step_id": "flip-completed",
            "kind": "cli",
            "description": "task-row-update: review 通过 → ✅ 完成"
                           "（approved→completed, TASK_TRANSITIONS 合法边）",
            "argv": [
                "{python}", "{tru_cli}",
                "--task", "{task}",
                "--from", "{input:from_state}",
                "--to", "completed",
                "--reason", "closure {closure_id}: review 通过收口"
                            "（标准链 flip 步, machine via task-row-update）",
                "--operation-id", "{op:flip-completed}",
                "--file", "{input:tracker_file}",
                "--json",
            ],
            "probe": {
                "kind": "task_row_state",
                "file": "{input:tracker_file}",
                "task": "{task}",
                "expect": "completed",
            },
            "dry_run_flag": "--dry-run",
        },
        {
            "step_id": "append-evidence",
            "kind": "cli",
            "description": "evidence-append: 结构化 EVD 行（operation 标记"
                           "为 effect 锚点）",
            "argv": [
                "{python}", "{gs_cli}",
                "--project-root", "{root}",
                "evidence-append",
                "--task", "{task}",
                "--type", "{input:evd_type}",
                "--description", "{input:evd_description}",
                "--basis", "{input:evd_basis}",
                "--artifacts", "{input:evd_artifacts}",
                "--refs", "governance_id:{task}",
                "--operation-id", "{op:append-evidence}"
            ],
            "probe": {
                "kind": "text_anchor",
                "file": "{gov}/evidence-log.md",
                "pattern": "{op:append-evidence}",
            },
            "dry_run_flag": "--dry-run",
        },
        {
            "step_id": "shrink-locks",
            "kind": "cli",
            "description": "locks-amend TTL 收缩（locks-release 缺口承载——"
                           "governance_store 无 release 命令, 如实披露）",
            "argv": [
                "{python}", "{gs_cli}",
                "--project-root", "{root}",
                "locks-amend",
                "--task", "{task}",
                "--ttl-seconds", "{input:lock_ttl}",
                "--reason", "closure {closure_id}: 收口收缩该任务全部锁 TTL"
                            "（locks-release 登记缺口, 本步为最近 Governed 效果）",
                "--operation-id", "{op:shrink-locks}"
            ],
            "probe": {
                "kind": "lock_ttl_le",
                "task": "{task}",
                "ttl_max": "{input:lock_ttl}",
            },
            "dry_run_flag": None,  # locks-amend has no --dry-run (disclosed)
        },
        {
            "step_id": "ready-to-commit",
            "kind": "summary",
            "description": "链终点: ready-to-commit 摘要 + commit message"
                           " 建议；git 操作不在链内, --finalize 显式门记录",
        },
    ],
}
"""The standard ticket-closure chain (review 通过后的票收口链):
task-row-update（翻转 ✅）→ evidence-append（EVD 行）→ locks-amend TTL 收缩
（locks-release 缺口承载, 如实披露）→ ready-to-commit 摘要。零业务逻辑:
每步只是既有写入器 CLI 的 argv 声明; kill-switch = 任一步的 argv 可独立执行。"""

_REQUIRED_INPUT_DEFAULTS: Dict[str, str] = {
    "from_state": "approved",
    "tracker_file": ".governance/plan-tracker.md",
    "lock_ttl": "60",
}

_PATH_LIKE_INPUTS: Tuple[str, ...] = ("tracker_file",)
"""Inputs resolved against the project root (absolute-path discipline for
step subprocesses)."""


# ── the release-window bootstrap chain (FIX-383, 0.88.0 阶段 B2) ────────────

RELEASE_WINDOW_BOOTSTRAP: Dict[str, Any] = {
    "chain_id": "release-window-bootstrap",
    "required_inputs": [],
    "steps": [
        {
            "step_id": "write-guard-converge",
            "kind": "cli",
            "description": "verify_workflow write-guard-bootstrap（FIX-383）:"
                           "守卫自身状态工件收敛——对账基线 regen/推进 + "
                           "FEAT-060 消费事务三分支查世界 resume + 违规重检测/"
                           "资格消费（守卫只写自身工件，治理记录零写入）",
            "argv": [
                "{python}", "{vw_cli}",
                "--project-root", "{root}",
                "write-guard-bootstrap",
            ],
            "probe": {
                "kind": "command_exit",
                "argv": [
                    "{python}", "{vw_cli}",
                    "--project-root", "{root}",
                    "write-guard-bootstrap", "--check-only",
                ],
            },
            "dry_run_flag": None,  # verify_workflow has no --dry-run face;
            # resolution is parse-level (--help), disclosed — locks-amend
            # precedent.
        },
        {
            "step_id": "bootstrap-ready",
            "kind": "summary",
            "description": "链终点: 发版窗口守卫状态收敛 ready-to-commit 摘要"
                           "（M-1~M-8 检查/写入器中间态已收敛，可安全续推）",
        },
    ],
}
"""The release-window bootstrap chain (FIX-383 — 发版管线自举): the
version-switch intermediate states of the release chain's DEPENDENT
checkers/writers (guard baseline not re-generated / violation-ledger
line-index drift / unreadable guard state schema / pending FEAT-060
consumption transaction) converge on re-entry with zero manual repair.
Effect-based at every boundary: the ``--check-only`` read-only probe (exit
0 = converged) reconciles an already-converged world without re-running
the writer; a not-converged world executes the ONE governed recovery
action (``write-guard-bootstrap`` converge mode — guard-owned artifacts
only)."""

# ═══════════════════════════════════════════════════════════════════════════
# Template resolution (untrusted input → argv list, never a shell line)
# ═══════════════════════════════════════════════════════════════════════════


def _template_mapping(closure_id: str, task: str, inputs: Dict[str, str],
                      root: Path) -> Dict[str, str]:
    gov = root / ".governance"
    mapping = {
        "python": sys.executable,
        "tru_cli": str(INFRA_DIR / "task_row_update.py"),
        "gs_cli": str(INFRA_DIR / "governance_store.py"),
        "vw_cli": str(INFRA_DIR / "verify_workflow.py"),
        "root": str(root),
        "gov": str(gov),
        "task": task,
        "closure_id": closure_id,
    }
    for key, value in inputs.items():
        mapping["input:" + key] = value
    return mapping


def resolve_template(argv: Tuple[str, ...], mapping: Dict[str, str],
                     closure_id: str) -> Tuple[str, ...]:
    """Substitute ``{placeholders}`` in a declared argv (DoD 0: model output
    is untrusted input — every element stays ONE argv element; no shell,
    no quoting, no concatenation). ``{op:<step-id>}`` resolves for ANY
    declared step id via the deterministic per-step derivation; unknown
    placeholders fail closed."""
    resolved: List[str] = []

    def _sub(text: str) -> str:
        def repl(match: "re.Match[str]") -> str:
            name = match.group(1)
            if name not in mapping:
                if name.startswith("op:"):
                    return step_operation_id(closure_id, name[3:])
                raise ValueError(
                    "closure {0}: unknown placeholder {{{1}}} in declared "
                    "argv".format(closure_id, name))
            return mapping[name]
        return _PLACEHOLDER_RE.sub(repl, text)

    for element in argv:
        value = _sub(element)
        if not value:
            raise ValueError(
                "closure {0}: placeholder substitution produced an empty "
                "argv element from {1!r}".format(closure_id, element))
        resolved.append(value)
    return tuple(resolved)


def _inputs_digest(inputs: Dict[str, str]) -> str:
    canonical = json.dumps(dict(sorted(inputs.items())), ensure_ascii=False,
                           sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════
# Effect probes — closed, read-only set (effect-based resume: 查世界)
# ═══════════════════════════════════════════════════════════════════════════


def _run_probe(probe: Dict[str, Any], mapping: Dict[str, str],
               closure_id: str) -> Dict[str, Any]:
    """Execute one declared probe. Returns
    ``{kind, satisfied, detail, anchor}``.  Every branch is READ-ONLY.

    Timing semantics (FIX-379 item-4): a probe result is a PRE-PROBE —
    the world is sampled BEFORE the step's effect exists (or before a
    resume decides) purely to gate execution/reconciliation.  Callers
    must never read a ``satisfied`` value as a post-execution
    verification; the chain re-probes on every run/resume boundary.
    """
    kind = probe.get("kind")
    if kind not in PROBE_KINDS:
        raise ValueError(
            "closure {0}: probe kind {1!r} not in closed set".format(
                closure_id, kind))

    def _resolved(key: str) -> str:
        raw = probe.get(key)
        if raw is None:
            raise ValueError(
                "closure {0}: probe {1!r} missing {2!r}".format(
                    closure_id, kind, key))
        out = resolve_template((raw,), mapping, closure_id)[0]
        return out

    if kind == "task_row_state":
        target = Path(_resolved("file"))
        task = _resolved("task")
        expect = _resolved("expect")
        argv = [sys.executable, str(INFRA_DIR / "task_row_update.py"),
                "--task", task, "--inspect", "--file", str(target), "--json"]
        proc = subprocess.run(argv, capture_output=True, text=True,
              encoding="utf-8", errors="replace", timeout=60, check=False)
        try:
            payload = json.loads(proc.stdout.strip() or "{}")
        except ValueError:
            return {"kind": kind, "satisfied": False,
                    "detail": "inspect output not JSON (exit {0})".format(
                        proc.returncode), "anchor": None}
        state = payload.get("state")
        found = bool(payload.get("found"))
        satisfied = found and state == expect
        return {"kind": kind, "satisfied": satisfied,
                "detail": "row state={0!r} (expect {1!r})".format(
                    state, expect) if found else "row not found",
                "anchor": payload.get("state")}

    if kind == "text_anchor":
        target = Path(_resolved("file"))
        pattern = _resolved("pattern")
        if not target.is_file():
            return {"kind": kind, "satisfied": False,
                    "detail": "target absent: {0}".format(target),
                    "anchor": None}
        try:
            text = target.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError) as exc:
            return {"kind": kind, "satisfied": False,
                    "detail": "target unreadable: {0}".format(exc),
                    "anchor": None}
        marker_index = text.find(pattern)
        if marker_index < 0:
            return {"kind": kind, "satisfied": False,
                    "detail": "anchor {0!r} not present".format(pattern[:18])
                              + "…", "anchor": None}
        line_start = text.rfind("\n", 0, marker_index) + 1
        line_end = text.find("\n", marker_index)
        line = text[line_start:line_end if line_end >= 0 else len(text)]
        return {"kind": kind, "satisfied": True,
                "detail": "anchor present (row reused, no re-append)",
                "anchor": line.strip()[:400]}

    if kind == "lock_ttl_le":
        locks_file = Path(mapping["gov"]) / "agent-locks.json"
        task = _resolved("task")
        ceiling = int(_resolved("ttl_max"))
        if not locks_file.is_file():
            return {"kind": kind, "satisfied": True,
                    "detail": "no agent-locks.json — nothing to release",
                    "anchor": "zero_locks"}
        try:
            data = json.loads(locks_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return {"kind": kind, "satisfied": False,
                    "detail": "agent-locks.json unreadable: {0}".format(exc),
                    "anchor": None}
        file_locks = data.get("file_locks") if isinstance(data, dict) else {}
        owned = {path: entry for path, entry in
                 (file_locks or {}).items()
                 if isinstance(entry, dict)
                 and entry.get("locked_by") == task}
        if not owned:
            return {"kind": kind, "satisfied": True,
                    "detail": "task holds no locks — release trivially "
                              "satisfied",
                    "anchor": "zero_locks"}
        over = {p: e.get("ttl_seconds") for p, e in owned.items()
                if not (isinstance(e.get("ttl_seconds"), int)
                        and e.get("ttl_seconds") <= ceiling)}
        satisfied = not over
        return {"kind": kind, "satisfied": satisfied,
                "detail": ("all {0} lock(s) ≤ {1}s".format(len(owned), ceiling)
                           if satisfied else
                           "locks above ceiling: {0}".format(over)),
                "anchor": json.dumps({p: e.get("ttl_seconds")
                                      for p, e in owned.items()},
                                     ensure_ascii=False, sort_keys=True)}

    if kind == "git_object_exists":
        repo = _resolved("repo")
        sha = _resolved("sha")
        if not re.match(r"^[0-9a-f]{7,40}$", sha):
            return {"kind": kind, "satisfied": False,
                    "detail": "malformed sha {0!r}".format(sha[:12]),
                    "anchor": None}
        proc = subprocess.run(
            ["git", "-C", repo, "cat-file", "-e", sha + "^{commit}"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=60, check=False)
        return {"kind": kind, "satisfied": proc.returncode == 0,
                "detail": ("commit {0} present".format(sha[:12])
                           if proc.returncode == 0 else
                           "commit {0} absent (git exit {1})".format(
                               sha[:12], proc.returncode)),
                "anchor": sha if proc.returncode == 0 else None}

    if kind == "git_head_message":
        repo = _resolved("repo")
        expect = _resolved("expect")
        proc = subprocess.run(
            ["git", "-C", repo, "log", "-1", "--format=%H %s"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=60, check=False)
        if proc.returncode != 0:
            return {"kind": kind, "satisfied": False,
                    "detail": "git log failed (exit {0})".format(
                        proc.returncode), "anchor": None}
        out = (proc.stdout or "").strip()
        satisfied = expect in out
        return {"kind": kind, "satisfied": satisfied,
                "detail": ("HEAD matches declared message" if satisfied
                           else "HEAD message mismatch: {0!r}".format(
                               out[:80])),
                "anchor": out.split(" ", 1)[0] if out else None}

    if kind == "command_exit":
        argv = resolve_template(tuple(probe.get("argv") or ()), mapping,
                                closure_id)
        if not argv:
            raise ValueError(
                "closure {0}: command_exit probe needs argv".format(
                    closure_id))
        try:
            proc = subprocess.run(list(argv), capture_output=True,
                  text=True, encoding="utf-8", errors="replace",
                  timeout=120, check=False)
        except subprocess.TimeoutExpired:
            return {"kind": kind, "satisfied": False,
                    "detail": "world-check command timed out", "anchor": None}
        return {"kind": kind, "satisfied": proc.returncode == 0,
                "detail": "world-check exit {0}".format(proc.returncode),
                "anchor": (proc.stdout or "").strip()[:200] or None}

    raise ValueError("unreachable probe kind")  # pragma: no cover


# ═══════════════════════════════════════════════════════════════════════════
# Run lock — short-term closure lock (governance-store lockfile discipline)
# ═══════════════════════════════════════════════════════════════════════════


class LockContention(Exception):
    """The closure run lock is held by another resume process (retryable)."""

    def __init__(self, lock_path: Path) -> None:
        super().__init__(
            "closure run lock busy: {0} (another resume is running; retry "
            "as lock_contention)".format(lock_path))
        self.lock_path = lock_path


class ExecutionFenced(Exception):
    """The closure's task execution generation has moved on (FEAT-063
    takeover fencing) — this executor is a STALE generation and its
    writes are refused at the write side (旧代际写入被拒). Carries the
    structured refusal payload (``revision_conflict`` family, FEAT-061
    epoch-fencing same-type); never a bare traceback."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        self.payload = payload
        super().__init__(payload.get("detail") or "execution fenced")


class _RunLock:
    """Exclusive cross-process closure run lock with BOUNDED acquire and a
    hard refusal (never the best-effort-unlocked fallback — a double-running
    resume is exactly the duplicate-execution window this ticket closes).
    Mirrors governance_store's ``_TargetLock`` contract on a per-closure
    lock file under ``.governance/closure-locks/``."""

    def __init__(self, lock_path: Path, timeout_seconds: float = 10.0) -> None:
        self.lock_path = lock_path
        self.timeout_seconds = timeout_seconds
        self._fd: Optional[int] = None

    def __enter__(self) -> "_RunLock":
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self.lock_path), os.O_RDWR | os.O_CREAT, 0o644)
        deadline = time.monotonic() + self.timeout_seconds
        delay = 0.005
        while True:
            if self._try_lock(fd):
                self._fd = fd
                return self
            if time.monotonic() >= deadline:
                os.close(fd)
                raise LockContention(self.lock_path)
            time.sleep(delay)
            delay = min(delay * 1.4, 0.2)

    @staticmethod
    def _try_lock(fd: int) -> bool:
        if os.name == "nt":
            import msvcrt
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                return True
            except OSError:
                return False
        try:
            import fcntl
        except ImportError:  # pragma: no cover - non-POSIX, non-Windows
            return True
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            return False

    def __exit__(self, *exc: Any) -> None:
        if self._fd is not None:
            if os.name == "nt":
                import msvcrt
                try:
                    msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:
                try:
                    import fcntl
                    fcntl.flock(self._fd, fcntl.LOCK_UN)
                except (OSError, ImportError):
                    pass
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        # The lock FILE stays in place (loop_event_log precedent — avoids a
        # create/delete race); only the byte-range lease is transient.


# ═══════════════════════════════════════════════════════════════════════════
# Fault injection — internal test entry ONLY (round-3 BT-9)
# ═══════════════════════════════════════════════════════════════════════════


def _fault_config() -> Optional[Dict[str, Any]]:
    raw = os.environ.get(CLOSURE_TEST_FAULT_ENV)
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _maybe_fault(point: str) -> bool:
    """TEST-ONLY handshake at a named protocol-boundary fault point.

    Returns True when the point fired (marker written + parent released or
    kill budget elapsed). Production runs never set the env var, so this is
    a boolean check away from the hot path and exposes no CLI surface.
    """
    config = _fault_config()
    if not config or point not in (config.get("points") or []):
        return False
    handshake_dir = Path(config.get("handshake_dir") or ".")
    handshake_dir.mkdir(parents=True, exist_ok=True)
    marker = handshake_dir / (re.sub(r"[^a-z0-9-]", "__", point)
                              + ".reached")
    marker.write_text(
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        encoding="utf-8")
    release = marker.with_suffix(".release")
    deadline = time.monotonic() + 120.0
    while time.monotonic() < deadline and not release.exists():
        time.sleep(0.05)
    return True


# ═══════════════════════════════════════════════════════════════════════════
# Step execution
# ═══════════════════════════════════════════════════════════════════════════


def _run_subprocess(argv: List[str], timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True,
                          encoding="utf-8", errors="replace",
                          timeout=timeout, check=False)


def _refusal_from_cli_output(stdout_text: str,
                             exit_code: int) -> Dict[str, Any]:
    """Extract a structured refusal from a writer CLI's JSON payload.

    FIX-379 item-1 (0.86.0 M-2 量测边缘观察 #1): the governed-writer CLIs
    emit TWO payload shapes on refusal —
      * task_row_update nests under ``result``/``refusal`` (mode-annotated
        top level), while
      * the governance_store family (``_run`` → ``_emit``) prints the
        refusal dict at TOP LEVEL (flat ``code``/``detail``/``error``).
    The extraction previously read only the nested shapes, so every
    governance_store refusal degraded to the ``manual_intervention``
    fallback with an EMPTY ``detail`` — the writer's real closed code and
    remediation text were dropped from the ``step_failed`` envelope (the
    M-2 B-group run measured ``payload.detail == ""`` with only the exit
    code preserved).  A top-level dict that itself carries a ``code`` key
    is now recognized as the third source; nested shapes keep priority so
    existing payloads extract unchanged.
    """
    try:
        payload = json.loads(stdout_text.strip() or "{}")
    except ValueError:
        return {"code": "manual_intervention",
                "detail": "writer exit {0} with non-JSON output".format(
                    exit_code)}
    result = payload.get("result") if isinstance(payload, dict) else None
    refusal = payload.get("refusal") if isinstance(payload, dict) else None
    source = refusal or result or (
        payload if isinstance(payload, dict) and payload.get("code")
        else {})
    code = source.get("code") or (
        RESULT_OK if exit_code == 0 else "manual_intervention")
    disposition = ERROR_CODE_DISPOSITIONS.get(code, "manual")
    detail = source.get("detail") or source.get("error") or ""
    if not isinstance(detail, str):
        # The flat governance_store shape carries ``error`` as a BOOLEAN
        # flag, not a message — a missing detail must stay "" (never leak
        # ``True`` into the audit text).
        detail = ""
    return {"code": code, "disposition": disposition,
            "detail": detail,
            "observed_revision": source.get("observed_revision"),
            "exit_code": exit_code}


def _execute_cli_step(step: StepSpec, argv: Tuple[str, ...], seq: int,
                      prev_seq: Optional[int], log_path: Path,
                      closure_id: str) -> Dict[str, Any]:
    """Run one governed-writer step. The WRITER owns idempotency/replay;
    a structured refusal stops the chain (blocked) with the closed code +
    disposition carried verbatim.

    FEAT-056 R0 P2-1 (review-FEAT-056-CODE-R0): a subprocess timeout is a
    HARD KILL — the writer's commit point (its atomic replace) may have
    landed before the kill, so the step's result is UNKNOWN, exactly like
    the external step (:func:`_execute_external_step`). The event is
    ``step_unknown`` (``execution: "unknown"``) and the chain halts with
    ``awaiting-world-check`` — resume then recovers via BOTH legs
    (review-FEAT-057-CODE-R0 P1-1, 方案 c): effect LANDED → the step's own
    read-only probe reconciles with the original anchor (no re-run);
    effect NOT landed → the probe miss releases the step for re-execution,
    safe under the writer's effect-based replay / state-level CAS (the
    pre-P2-1 timeout behavior; CLI steps that declare no ``world_check``
    gate on their probe, not on the chain-level ``--world-check`` flag).
    The old blocked/``manual_intervention`` classification mislabeled a
    recoverable crash window as manual work and distorted the audit trail
    — correctness was never at risk (writer replay + probes are safely
    isomorphic), the classification was.
    """
    _append_closure_event(log_path, closure_id, "step_started", seq,
                          prev_seq,
                          {"step_id": step.step_id, "kind": step.kind})
    _maybe_fault("pre-step:" + step.step_id)
    try:
        proc = _run_subprocess(list(argv), step.timeout_seconds)
    except subprocess.TimeoutExpired:
        # subprocess.run already killed the child on timeout (it kills then
        # reaps); the governed effect MAY have landed before the kill —
        # UNKNOWN, same taxonomy as the external step.
        return {"halt": "awaiting-world-check", "seq": seq + 1,
                "last_seq": seq,
                "event": ("step_unknown", {
                    "step_id": step.step_id,
                    "execution": "unknown",
                    "detail": "writer subprocess timed out after {0}s — "
                              "result unknown (hard-kill crash window); "
                              "resume reconciles via the step probe before "
                              "any re-run".format(step.timeout_seconds),
                })}
    fired = _maybe_fault("post-step-effect:" + step.step_id)
    if proc.returncode == 0:
        out = proc.stdout.strip()
        try:
            payload = json.loads(out or "{}")
        except ValueError:
            payload = {}
        result = payload.get("result") or payload
        return {"halt": None, "seq": seq + 1, "last_seq": seq,
                "event": ("step_completed", {
                    "step_id": step.step_id,
                    "operation_id": step_operation_id(closure_id,
                                                      step.step_id),
                    "execution": "succeeded",
                    "artifact": (result.get("row_id")
                                 or result.get("new_revision")
                                 or result.get("detail") or "ok"),
                    "fault_fired": fired,
                })}
    refusal = _refusal_from_cli_output(proc.stdout, proc.returncode)
    return {"halt": "blocked", "seq": seq + 1, "last_seq": seq,
            "event": ("step_failed", dict(
                {"step_id": step.step_id}, **refusal))}


def _execute_external_step(step: StepSpec, argv: Tuple[str, ...], seq: int,
                           prev_seq: Optional[int], log_path: Path,
                           closure_id: str) -> Dict[str, Any]:
    """Run one declared external action (fixtures/tests only in 0.86.0).

    Timeout → the result is UNKNOWN (contracts.EXECUTION_RESULTS): the
    action MAY have landed — never blindly re-run; report the suggested
    read-only world check and halt. A declared blocked exit code → blocked
    + repair diagnostic. These are the round-3 two failure CLASSES:
    raise-equivalent (structured refusal) is distinct from hard kill (the
    parent-controller chaos tests)."""
    _append_closure_event(log_path, closure_id, "step_started", seq,
                          prev_seq,
                          {"step_id": step.step_id, "kind": step.kind})
    _maybe_fault("pre-step:" + step.step_id)
    try:
        proc = _run_subprocess(list(argv), step.timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        # subprocess.run already killed the child on timeout (it kills then
        # reaps); the effect MAY have landed before the timeout — UNKNOWN.
        return {"halt": "awaiting-world-check", "seq": seq + 1,
                "last_seq": seq,
                "event": ("step_unknown", {
                    "step_id": step.step_id,
                    "execution": "unknown",
                    "detail": "external action timed out after {0}s — "
                              "result unknown; check the world before any "
                              "re-run".format(step.timeout_seconds),
                    "suggested_world_check": list(step.world_check),
                })}
    fired = _maybe_fault("post-step-effect:" + step.step_id)
    if proc.returncode == 0:
        return {"halt": None, "seq": seq + 1, "last_seq": seq,
                "event": ("step_completed", {
                    "step_id": step.step_id,
                    "execution": "succeeded",
                    "fault_fired": fired,
                })}
    if proc.returncode in step.blocked_exit_codes:
        return {"halt": "blocked", "seq": seq + 1, "last_seq": seq,
                "event": ("step_failed", {
                    "step_id": step.step_id,
                    "code": "manual_intervention",
                    "disposition": "manual",
                    "detail": "external action refused (exit {0}; declared "
                              "blocked class) — repair the external world, "
                              "then resume; suggested world check: {1}"
                              .format(proc.returncode,
                                      " ".join(step.world_check) or "n/a"),
                    "stderr_tail": (proc.stderr or "")[-400:],
                })}
    return {"halt": "blocked", "seq": seq + 1, "last_seq": seq,
            "event": ("step_failed", {
                "step_id": step.step_id,
                "code": "manual_intervention",
                "disposition": "manual",
                "detail": "external action failed (exit {0})".format(
                    proc.returncode),
                "stderr_tail": (proc.stderr or "")[-400:],
            })}


_CHAIN_SUMMARY_SUBJECTS: Dict[str, str] = {
    "standard-ticket-closure":
        "{0}: review 通过收口（closure-chain 标准链）",
    "release-window-bootstrap":
        "{0}: 发版窗口守卫状态自举收敛（closure-chain 自举链, FIX-383）",
}
"""Per-chain default commit subject (``commit_subject`` input overrides)."""

_CHAIN_SUMMARY_BODIES: Dict[str, str] = {
    "standard-ticket-closure":
        "(FEAT-056 standard ticket closure)\n"
        "Task row flipped via task-row-update; evidence appended via\n"
        "evidence-append; dispatch-lock TTLs shrunk via locks-amend\n"
        "(locks-release remains a registered gap — TTL shrink is the\n"
        "governed stand-in, disclosed not silent).",
    "release-window-bootstrap":
        "(FIX-383 release-window bootstrap)\n"
        "Write-guard own-state artifacts converged via verify_workflow\n"
        "write-guard-bootstrap: baseline re-gen/advance + FEAT-060\n"
        "pending-transaction three-branch world-judged resume + violation\n"
        "re-detection/eligible consumption. Guard-owned artifacts only —\n"
        "zero governance-record writes; unjudgeable states stay loud.",
}
"""Per-chain commit-message body. Unknown chain ids fall back to the
standard text (custom --spec chains keep their pre-FIX-383 output)."""

_CHAIN_OWN_STATE_ARTIFACTS: Dict[str, Tuple[str, ...]] = {
    "release-window-bootstrap": (
        ".governance/.write-guard-state.json",
        ".governance/.write-guard-violations.json",
        ".governance/.governance-store-locks/",
    ),
}
"""Per-chain ``do_not_stage`` extensions (FEAT-056 R0 P3-1 class): the
write-guard's own state artifacts are post-commit bookkeeping of the
release window, exactly like the closure journal — they must NOT be
staged into the commit the summary describes."""


def _summary_payload(spec: ChainSpec, closure_id: str, task: str,
                     inputs: Dict[str, str]) -> Dict[str, Any]:
    """The ready-to-commit endpoint payload (round-2 §2: 链终点输出
    ready-to-commit 摘要 + message 建议; git 操作不在链内).

    FIX-383: the message body is chain-aware (a per-chain table keyed by
    ``chain_id``) — the standard chain's bytes are unchanged (its table
    entry IS the previous literal), unknown chain ids keep the standard
    text as the fallback (custom --spec chains see the same output as
    before), and the bootstrap chain describes what actually converged.
    """
    subject = inputs.get("commit_subject") or (
        _CHAIN_SUMMARY_SUBJECTS.get(spec.chain_id)
        or _CHAIN_SUMMARY_SUBJECTS["standard-ticket-closure"]
    ).format(task)
    body = (_CHAIN_SUMMARY_BODIES.get(spec.chain_id)
            or _CHAIN_SUMMARY_BODIES["standard-ticket-closure"])
    message = (
        "{0}\n\n"
        "Closure: {1}\n"
        "Chain: {2} {3}\n"
        "Completion gate: closure-chain --finalize --closure-id {1}\n"
        "--commit-sha <sha-of-this-commit>".format(
            subject, closure_id, spec.chain_id, body))
    return {
        "ready": True,
        "commit_message_suggestion": message,
        # 自指约束（round-2 §2）: the closure journal + run locks are
        # post-commit bookkeeping — they must NOT be staged into the commit
        # this summary describes. FEAT-056 R0 P3-1: the journal's
        # cross-process lock COMPANION FILE is produced by
        # ``loop_event_log._cross_process_lock`` on every real run and
        # belongs to the same do-not-stage class.
        "do_not_stage": [
            ".governance/closure-events.jsonl",
            ".governance/closure-events.jsonl.lock",
            ".governance/closure-locks/",
        ] + list(_CHAIN_OWN_STATE_ARTIFACTS.get(spec.chain_id, ())),
        "finalize_command": None,  # filled after the operator commits
    }


# ═══════════════════════════════════════════════════════════════════════════
# Chain runner
# ═══════════════════════════════════════════════════════════════════════════


def _step_world_state(events: List[Dict[str, Any]]) -> Dict[str, str]:
    """Derive per-step last status from the journal (audit; the world probes
    remain the truth source).

    A dangling ``step_started`` (no terminal event) is the hard-kill crash
    window: for an EXTERNAL step the action's RESULT is unknown (round-2
    持久化清单 — 外部动作结果不明标 UNKNOWN), so resume gates on the
    declared world check instead of blindly re-executing; for a CLI step
    the crash window stays undecided (``"started"``) — the read-only probe
    plus the writer's own effect-based replay protocol decide safely.
    (FEAT-056 R0 P2-1: an explicit subprocess TIMEOUT records
    ``step_unknown`` for BOTH kinds — only the dangling-``started`` window
    keeps the kind distinction.)
    """
    last: Dict[str, Tuple[str, str]] = {}
    for ev in events:
        payload = ev.get("payload") or {}
        step_id = payload.get("step_id")
        event_type = ev.get("event_type")
        if step_id and event_type in ("step_started", "step_completed",
                                      "step_failed", "step_unknown",
                                      "step_reconciled"):
            last[step_id] = (event_type, payload.get("kind") or "")
    state: Dict[str, str] = {}
    for step_id, (event_type, kind) in last.items():
        if event_type in ("step_completed", "step_reconciled"):
            state[step_id] = "completed"
        elif event_type == "step_failed":
            state[step_id] = "failed"
        elif event_type == "step_unknown":
            state[step_id] = "unknown"
        else:  # dangling step_started — the crash window
            state[step_id] = "unknown" if kind == "external" else "started"
    return state


def run_chain(spec: ChainSpec, *, root: Path, task: str,
              inputs: Dict[str, str], closure_id: Optional[str] = None,
              dry_run: bool = False, world_check: bool = False,
              lock_timeout: float = 10.0,
              reopen_of: Optional[str] = None) -> Dict[str, Any]:
    """Execute (or resume) a declared chain. Effect-based at every boundary:

    1. resume probes the WORLD per step before executing (row flipped?
       evidence anchor present? locks shrunk?) — the journal is audit, the
       world is truth (查世界不信日志);
    2. a completed effect without bookkeeping (the crash window) is
       reconciled with its ORIGINAL anchor reused, never re-executed;
    3. external UNKNOWN halts with a suggested read-only world check —
       the check runs only when ``world_check`` is explicitly enabled
       (远端查询动作建议非自动执行);
    4. ``dry_run`` writes NOTHING (no journal append, no lock, no step) —
       probes + writer dry-runs prove every step resolvable;
    5. ``reopen_of`` binds the RECORDED reopen linkage (FEAT-063): the
       referenced closure's ``closure_reopened`` event names the successor
       id + attempt — the run adopts the recorded successor (a different
       ``closure_id`` refuses; a fresh id never forks the lineage) and
       injects ``reopen_of``/``reopen_attempt`` into the inputs so the
       digest and the successor's ``closure_started`` carry the back-link.
       A stale execution generation (task fenced to another holder)
       refuses at the entry/step write-side checks (``ExecutionFenced``).
    """
    root = Path(root)
    if not isinstance(task, str) or not task.strip():
        raise ValueError("run_chain: task id required")
    task = task.strip()
    inputs = dict(inputs) if inputs else {}
    if reopen_of is not None:
        linkage = _resolve_reopen_linkage(root, reopen_of, closure_id)
        closure_id = linkage["successor_closure_id"]
        for reserved, value in (("reopen_of", reopen_of),
                                ("reopen_attempt",
                                 str(linkage["reopen_attempt"]))):
            existing = inputs.get(reserved)
            if existing is not None and existing != value:
                raise ValueError(
                    "run_chain: conflicting fresh {0!r} input {1!r} — the "
                    "recorded reopen linkage stands (recorded intent; "
                    "drop the conflicting --input)".format(
                        reserved, existing))
            inputs[reserved] = value
    closure_id = require_closure_id(
        "run_chain: closure_id", closure_id or new_closure_id())
    merged_inputs: Dict[str, str] = dict(_REQUIRED_INPUT_DEFAULTS)
    for key, value in inputs.items():
        if not isinstance(key, str) or not isinstance(value, str) or not key:
            raise ValueError(
                "run_chain: inputs must be a str→str dict (got {0!r})"
                .format((key, value)))
        merged_inputs[key] = value
    missing = [k for k in spec.required_inputs if not merged_inputs.get(k)]
    if missing:
        raise ValueError(
            "run_chain: missing required inputs {0}".format(missing))
    # Path-like inputs are resolved against root so every step subprocess
    # gets an ABSOLUTE path (subprocess cwd independence).
    for path_key in _PATH_LIKE_INPUTS:
        value = merged_inputs.get(path_key)
        if value and not os.path.isabs(value):
            merged_inputs[path_key] = str(root / value)
    log_path = default_event_log_path(root)
    mapping = _template_mapping(closure_id, task, merged_inputs, root)
    digest = _inputs_digest(merged_inputs)

    if dry_run:
        return _dry_run_plan(spec, closure_id, task, mapping, merged_inputs,
                             root, log_path)

    lock_path = _closure_lock_dir(root) / (closure_id + ".lock")
    with _RunLock(lock_path, lock_timeout):
        return _run_locked(spec, closure_id, task, merged_inputs, mapping,
                           digest, root, log_path, world_check)


def _run_locked(spec: ChainSpec, closure_id: str, task: str,
                inputs: Dict[str, str], mapping: Dict[str, str],
                digest: str, root: Path, log_path: Path,
                world_check: bool) -> Dict[str, Any]:
    # FIX-391 version-aware preflight (arch ①): classify the COMPLETE raw
    # journal BEFORE any recovery side effect — including the idempotent
    # closure_fenced audit append and the fresh-start closure_started
    # append below. A journal this reader cannot fully judge (newer
    # writer's event types / out-of-window schema) refuses zero-write.
    conflict = _journal_version_conflict(log_path, closure_id)
    if conflict is not None:
        raise ValueError(conflict["detail"])
    events, problems = _load_closure_events(log_path, closure_id)
    started = next((e for e in events
                    if e.get("event_type") == "closure_started"), None)
    resumed = started is not None
    if any(e.get("event_type") == "closure_cancelled" for e in events):
        # FEAT-062 terminal semantics: a cancelled closure is not
        # resumable — the world it was converging has been abandoned;
        # re-running the cancel command converges pending cancellation
        # legs instead.
        raise ValueError(
            "closure {0}: CANCELLED (terminal) — resume refused "
            "(FEAT-062 终态语义; re-run the cancel command to converge "
            "pending cancellation effects, or start a new closure)"
            .format(closure_id))
    if resumed and (started.get("payload") or {}).get("inputs_digest") \
            not in (None, digest):
        raise ValueError(
            "closure {0}: resume inputs digest mismatch — this closure was "
            "started with different inputs (closure identity is "
            "immutable; start a new closure instead)".format(closure_id))
    # FEAT-063 write-side fence (entry check): a task whose execution
    # generation is held by another closure refuses THIS executor before
    # ANY write — a fresh start records nothing at all (zero-write), a
    # resume records one idempotent closure_fenced audit event first.
    fence = _execution_fence_refusal(root, task, closure_id)
    if fence is not None:
        if resumed:
            _record_fenced_event(root, log_path, closure_id, fence)
        raise ExecutionFenced(fence)
    seq, prev_seq = _next_seq(events)
    if not resumed:
        _append_closure_event(
            log_path, closure_id, "closure_started", seq, prev_seq, {
                "chain_id": spec.chain_id,
                "task": task,
                "inputs_digest": digest,
                "inputs": dict(sorted(inputs.items())),
                "code_revision": _git_head(root),
            })
        seq, prev_seq = seq + 1, seq
    events, _ = _load_closure_events(log_path, closure_id)
    step_state = _step_world_state(events)
    report_steps: List[Dict[str, Any]] = []
    halt: Optional[str] = None
    for step in spec.steps:
        info: Dict[str, Any] = {"step_id": step.step_id,
                                "kind": step.kind}
        if halt:
            info["status"] = "pending"
            info["note"] = "chain halted at an earlier step"
            report_steps.append(info)
            continue
        # FEAT-063 write-side fence (per-step re-check — the FEAT-061
        # in-lock revalidation shape): every governed write boundary
        # (subprocess spawn / summary emission) re-verifies the execution
        # generation. Under the run-lock discipline a mid-run fence is
        # unreachable via the takeover path (the promotion holds this
        # closure's run lock); this re-check defends the out-of-band-edit
        # residual and keeps the fence true at every write boundary.
        fence = _execution_fence_refusal(root, task, closure_id)
        if fence is not None:
            _record_fenced_event(root, log_path, closure_id, fence)
            raise ExecutionFenced(fence)
        if step.kind == "summary":
            ready_present = any(
                e.get("event_type") == "closure_ready" for e in events)
            if ready_present:
                # Idempotent endpoint: a re-run re-emits nothing (the
                # duplicate-append invariant covers audit noise too).
                info["status"] = "completed"
                info["note"] = "closure_ready already recorded"
                report_steps.append(info)
                continue
            payload = _summary_payload(spec, closure_id, task, inputs)
            payload["finalize_command"] = (
                "python {0} finalize --closure-id {1} --commit-sha <sha>"
                .format(Path(__file__).name, closure_id))
            _append_closure_event(
                log_path, closure_id, "closure_ready", seq, prev_seq,
                {"step_id": step.step_id, "summary": payload})
            seq, prev_seq = seq + 1, seq
            info["status"] = "completed"
            info["summary"] = payload
            report_steps.append(info)
            continue
        # effect probe first — the world decides (resume + fresh alike)
        # FIX-379 item-4 (0.86.0 M-2 量测边缘观察 #4): this is the
        # PRE-PROBE — the PRE-EXECUTION world observation that decides
        # reconcile-vs-execute.  A ``satisfied=false`` recorded on a
        # flip/append step's report/journal payload therefore means "the
        # effect was not yet in the world when the step started" — it is
        # the execution-decision INPUT, never a post-execution
        # verification.  The probe is NOT re-run after the step executes:
        # completion is recorded by ``step_completed`` + the writer's
        # receipt, and a later resume re-probes the world afresh (查世界
        # 不信日志).  Reading the payload as "the effect failed
        # verification" is the registered misreading this note prevents.
        probe_result = (_run_probe(step.probe, mapping, closure_id)
                        if step.probe else
                        {"kind": None, "satisfied": False,
                         "detail": "no probe declared", "anchor": None})
        info["probe"] = {k: probe_result[k] for k in
                         ("kind", "satisfied", "detail")}
        if step_state.get(step.step_id) == "completed":
            info["status"] = "completed"
            info["note"] = "bookkeeping present; probe confirms effect"
            report_steps.append(info)
            continue
        if probe_result.get("satisfied"):
            # effect present without (or ahead of) bookkeeping — the crash
            # window: reconcile with the ORIGINAL anchor, never re-execute.
            _append_closure_event(
                log_path, closure_id, "step_reconciled", seq, prev_seq, {
                    "step_id": step.step_id,
                    "probe": probe_result.get("kind"),
                    "anchor": probe_result.get("anchor"),
                    "detail": probe_result.get("detail"),
                })
            seq, prev_seq = seq + 1, seq
            info["status"] = "reconciled"
            info["anchor"] = probe_result.get("anchor")
            report_steps.append(info)
            continue
        # UNKNOWN step: world check FIRST, and only when enabled — with one
        # CLI-specific recovery leg (review-FEAT-057-CODE-R0 P1-1, 方案 c):
        unknown_state = step_state.get(step.step_id) == "unknown"
        if unknown_state and step.kind == "cli" and not step.world_check:
            # A CLI step's own read-only probe IS its world check, and it
            # already ran above. This branch is the NOT-landed leg (the
            # landed leg reconciled at the probe branch): the governed
            # effect is not in the world, so the recovery is re-execution —
            # safe because the writer's effect-based replay / state-level
            # CAS carries idempotency (deterministic per-step operation
            # id), exactly the pre-P2-1 timeout behavior. Halting here
            # would strand standard-chain steps (which declare no
            # world_check) forever in awaiting-world-check with a literal
            # "n/a" remediation, and honoring the old suggestion
            # (--world-check) would crash on the empty command_exit argv.
            # CLI probes are read-only world queries (no external side
            # effects), so releasing the step keeps the round-2 gate's
            # purpose (never blindly re-run an action whose result is
            # unknown) without the dead end: for a CLI writer the result is
            # KNOWN to be "not in the world" precisely because its probe
            # missed.
            pass  # fall through to re-execution (skip the unknown gate)
        elif unknown_state:
            if not world_check:
                info["status"] = "unknown"
                info["note"] = (
                    "result unknown; suggested read-only world check (run "
                    "resume with --world-check to execute it): {0}".format(
                        " ".join(step.world_check) or "n/a"))
                report_steps.append(info)
                halt = "awaiting-world-check"
                continue
            wc_probe = {"kind": "command_exit", "argv": list(
                resolve_template(step.world_check, mapping, closure_id))}
            wc_result = _run_probe(wc_probe, mapping, closure_id)
            info["world_check"] = {k: wc_result[k] for k in
                                   ("satisfied", "detail")}
            if wc_result.get("satisfied"):
                _append_closure_event(
                    log_path, closure_id, "step_reconciled", seq, prev_seq, {
                        "step_id": step.step_id,
                        "probe": "command_exit",
                        "anchor": wc_result.get("anchor"),
                        "detail": "world check resolved the UNKNOWN: effect "
                                  "present, no re-run",
                    })
                seq, prev_seq = seq + 1, seq
                info["status"] = "reconciled"
                info["anchor"] = wc_result.get("anchor")
                report_steps.append(info)
                continue
        argv = resolve_template(step.argv, mapping, closure_id)
        if step.kind == "cli":
            outcome = _execute_cli_step(step, argv, seq, prev_seq, log_path,
                                        closure_id)
        else:
            outcome = _execute_external_step(step, argv, seq, prev_seq,
                                             log_path, closure_id)
        event_type, event_payload = outcome.pop("event")
        # outcome["seq"] = the terminal event's seq (started consumed the
        # incoming seq); outcome["last_seq"] = the started event's seq.
        _append_closure_event(log_path, closure_id, event_type,
                              outcome["seq"], outcome["last_seq"],
                              event_payload)
        seq = outcome["seq"] + 1
        prev_seq = outcome["seq"]
        info["status"] = ("completed"
                          if event_type == "step_completed" else
                          "unknown" if event_type == "step_unknown" else
                          "failed")
        info["detail"] = event_payload.get("detail")
        info["code"] = event_payload.get("code")
        report_steps.append(info)
        if outcome.get("halt"):
            halt = outcome["halt"]

    events, problems_after = _load_closure_events(log_path, closure_id)
    problems = sorted(set(problems) | set(problems_after))
    finalized = any(e.get("event_type") == "closure_finalized"
                    for e in events)
    if halt == "blocked":
        status = "blocked"
    elif halt == "awaiting-world-check":
        status = "awaiting-world-check"
    elif any(e.get("event_type") == "closure_ready" for e in events):
        status = "finalized" if finalized else "ready"
    else:
        status = "running"
    return {
        "closure_id": closure_id,
        "chain_id": spec.chain_id,
        "task": task,
        "status": status,
        "halt": halt,
        "resumed": resumed,
        "steps": report_steps,
        "events_appended": seq - 1,
        "journal": str(log_path),
        "journal_problems": problems,
    }


def _dry_run_plan(spec: ChainSpec, closure_id: str, task: str,
                  mapping: Dict[str, str], inputs: Dict[str, str],
                  root: Path, log_path: Path) -> Dict[str, Any]:
    """Zero-write resolution proof (DoD 5): probes run read-only, writer
    dry-runs where the writer supports them, parse-level (--help)
    resolution where it does not (disclosed per step). No journal append,
    no run lock — NOTHING is written."""
    steps_report: List[Dict[str, Any]] = []
    all_resolvable = True
    for step in spec.steps:
        info: Dict[str, Any] = {"step_id": step.step_id,
                                "kind": step.kind}
        if step.kind == "summary":
            info["status"] = "resolvable"
            info["summary_preview"] = _summary_payload(spec, closure_id,
                                                       task, inputs)
            steps_report.append(info)
            continue
        argv = resolve_template(step.argv, mapping, closure_id)
        info["argv_resolved"] = list(argv)
        info["operation_id"] = step_operation_id(closure_id, step.step_id)
        if step.probe:
            probe_result = _run_probe(step.probe, mapping, closure_id)
            info["probe"] = {k: probe_result[k] for k in
                             ("kind", "satisfied", "detail", "anchor")}
        if step.dry_run_flag:
            dry_argv = list(argv)
            if step.dry_run_flag not in dry_argv:
                dry_argv.append(step.dry_run_flag)
            try:
                proc = _run_subprocess(dry_argv, step.timeout_seconds)
                info["writer_dry_run"] = {
                    "mode": "writer_dry_run",
                    "exit_code": proc.returncode,
                    "payload": _safe_json(proc.stdout),
                }
                if proc.returncode != 0:
                    all_resolvable = False
                    info["status"] = "resolved_refusal"
                    info["note"] = ("writer fully parsed+validated the step "
                                    "and issued a structured refusal — the "
                                    "chain would stop here, zero writes")
                else:
                    info["status"] = "resolvable"
            except subprocess.TimeoutExpired:
                all_resolvable = False
                info["status"] = "resolution_timeout"
        else:
            # Writer has no dry-run face (locks-amend): parse-level
            # resolution via the subcommand's own argparse (--help exits 0
            # through the real parser). Disclosed, never presented as a
            # writer dry-run.
            help_argv = list(argv)
            if "--help" not in help_argv:
                help_argv.append("--help")
            try:
                proc = _run_subprocess(help_argv, 30.0)
                info["writer_dry_run"] = {
                    "mode": "parse_level_help",
                    "exit_code": proc.returncode,
                    "note": "writer has no --dry-run face; resolution is "
                            "parse-level only (disclosed gap)",
                }
                info["status"] = ("resolvable" if proc.returncode == 0
                                  else "resolution_failed")
                if proc.returncode != 0:
                    all_resolvable = False
            except subprocess.TimeoutExpired:
                all_resolvable = False
                info["status"] = "resolution_timeout"
        steps_report.append(info)
    return {
        "closure_id": closure_id,
        "chain_id": spec.chain_id,
        "task": task,
        "mode": "dry-run",
        "writes_performed": 0,
        "all_steps_resolvable": all_resolvable,
        "steps": steps_report,
        "journal": str(log_path),
        "journal_touched": False,
    }


def _safe_json(text: str) -> Any:
    try:
        return json.loads(text.strip() or "{}")
    except ValueError:
        return {"_raw": text[-400:]}


def _git_head(root: Path) -> Optional[str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (proc.stdout or "").strip() or None


# ═══════════════════════════════════════════════════════════════════════════
# Finalize gate + status
# ═══════════════════════════════════════════════════════════════════════════


def finalize_closure(root: Path, closure_id: str, commit_sha: str) \
        -> Dict[str, Any]:
    """The explicit completion gate (round-2 §2: ``--finalize`` 显式门记录
    完成). VERIFIES ONLY (read-only probe) that the operator's commit
    exists, then records ``closure_finalized`` — the chain never runs git
    to create anything, and the finalized record lands AFTER the commit it
    describes (self-reference constraint holds structurally)."""
    root = Path(root)
    closure_id = require_closure_id("finalize: closure_id", closure_id)
    if not isinstance(commit_sha, str) \
            or not re.match(r"^[0-9a-f]{7,40}$", commit_sha):
        return {"closure_id": closure_id, "error": True,
                "code": "schema_violation", "disposition": "validation",
                "detail": "commit sha must be 7-40 hex chars"}
    log_path = default_event_log_path(root)
    lock_path = _closure_lock_dir(root) / (closure_id + ".lock")
    with _RunLock(lock_path, 10.0):
        # FIX-391 version-aware preflight (arch ①): before even the
        # idempotent closure_fenced audit write below — a conflicted
        # journal never gains an event from a reader that cannot judge it.
        conflict = _journal_version_conflict(log_path, closure_id)
        if conflict is not None:
            return conflict
        events, problems = _load_closure_events(log_path, closure_id)
        started = next((e for e in events
                        if e.get("event_type") == "closure_started"), None)
        if started is None:
            return {"closure_id": closure_id, "error": True,
                    "code": "cross_record_violation",
                    "disposition": "validation",
                    "detail": "closure {0} has no journal — nothing to "
                              "finalize".format(closure_id)}
        if any(e.get("event_type") == "closure_finalized" for e in events):
            prior = next(e for e in events
                         if e.get("event_type") == "closure_finalized")
            return {"closure_id": closure_id, "error": False,
                    "status": "finalized", "replayed": True,
                    "commit_sha": (prior.get("payload") or {}).get(
                        "commit_sha")}
        if any(e.get("event_type") == "closure_cancelled" for e in events):
            # FEAT-062 terminal semantics: the two terminals never cross —
            # a cancelled closure cannot be finalized after the fact.
            return {"closure_id": closure_id, "error": True,
                    "code": "cross_record_violation",
                    "disposition": "validation",
                    "detail": "closure {0} is CANCELLED (immutable "
                              "terminal) — finalize refused".format(
                                  closure_id)}
        # FEAT-063 write-side fence: a stale generation's finalize would
        # record a completion submitted by an executor whose generation has
        # moved on — refused (旧代际写入被拒), one idempotent audit event.
        started_task = (started.get("payload") or {}).get("task")
        fence = _execution_fence_refusal(
            root, started_task if isinstance(started_task, str) else "",
            closure_id)
        if fence is not None:
            _record_fenced_event(root, log_path, closure_id, fence)
            return fence
        probe = _run_probe(
            {"kind": "git_object_exists", "repo": str(root),
             "sha": commit_sha},
            {"gov": root / ".governance"}, closure_id)
        if not probe.get("satisfied"):
            return {"closure_id": closure_id, "error": True,
                    "code": "manual_intervention",
                    "disposition": "manual",
                    "detail": "commit {0} not found in {1} — verify the "
                              "sha (typo?) or make the commit first; "
                              "nothing recorded"
                              .format(commit_sha[:12], root)}
        _maybe_fault("post-finalize-verify")
        seq, prev_seq = _next_seq(events)
        _append_closure_event(
            log_path, closure_id, "closure_finalized", seq, prev_seq,
            {"commit_sha": commit_sha, "verified": True,
             "detail": "explicit finalize gate: commit verified in the "
                       "world, recorded after the fact (自指约束: 本记录"
                       "不入其描述的 commit)"})
        return {"closure_id": closure_id, "error": False,
                "status": "finalized", "replayed": False,
                "commit_sha": commit_sha, "journal_problems": problems}


def closure_status(root: Path, closure_id: str) -> Dict[str, Any]:
    """Structured status read (the journal's regular read face)."""
    root = Path(root)
    closure_id = require_closure_id("status: closure_id", closure_id)
    log_path = default_event_log_path(root)
    events, problems = _load_closure_events(log_path, closure_id)
    if not events:
        return {"closure_id": closure_id, "found": False,
                "journal": str(log_path)}
    started = next((e for e in events
                    if e.get("event_type") == "closure_started"), None)
    step_state = _step_world_state(events)
    finalized = any(e.get("event_type") == "closure_finalized" for e in events)
    cancelled = next((e for e in events
                      if e.get("event_type") == "closure_cancelled"), None)
    reopened = next((e for e in events
                     if e.get("event_type") == "closure_reopened"), None)
    fenced = next((e for e in events
                   if e.get("event_type") == "closure_fenced"), None)
    ready = any(e.get("event_type") == "closure_ready" for e in events)
    unknown_steps = [s for s, v in step_state.items() if v == "unknown"]
    failed_steps = [s for s, v in step_state.items() if v == "failed"]
    if cancelled is not None:
        status = "cancelled"
    elif finalized:
        status = "finalized"
    elif failed_steps:
        status = "blocked"
    elif unknown_steps:
        status = "awaiting-world-check"
    elif ready:
        status = "ready"
    else:
        status = "running"
    started_payload = (started or {}).get("payload") or {}
    started_inputs = started_payload.get("inputs") or {}
    return {
        "closure_id": closure_id,
        "found": True,
        "status": status,
        "task": started_payload.get("task"),
        "chain_id": started_payload.get("chain_id"),
        "started_at": (started or {}).get("timestamp"),
        "cancellation": (None if cancelled is None else {
            "authorized_by": (cancelled.get("payload") or {}).get(
                "authorized_by"),
            "reason": (cancelled.get("payload") or {}).get("reason"),
            "cancelled_at": cancelled.get("timestamp"),
        }),
        # FEAT-063 disclosures: the reopen lineage (both directions) and
        # the fencing audit — pure disclosure, never part of the derived
        # status (the terminals stay terminal; cancel stays available).
        "reopen": (None if reopened is None else {
            "successor_closure_id": (reopened.get("payload") or {}).get(
                "successor_closure_id"),
            "reopen_attempt": (reopened.get("payload") or {}).get(
                "reopen_attempt"),
            "prior_status": (reopened.get("payload") or {}).get(
                "prior_status"),
            "authorized_by": (reopened.get("payload") or {}).get(
                "authorized_by"),
            "reason": (reopened.get("payload") or {}).get("reason"),
            "reopened_at": reopened.get("timestamp"),
        }),
        "reopen_lineage": (None if not started_inputs.get("reopen_of") else {
            "reopen_of": started_inputs.get("reopen_of"),
            "reopen_attempt": started_inputs.get("reopen_attempt"),
        }),
        "fenced": (None if fenced is None else {
            "observed_generation": (fenced.get("payload") or {}).get(
                "observed_generation"),
            "observed_holder": (fenced.get("payload") or {}).get(
                "observed_holder"),
            "fenced_at": fenced.get("timestamp"),
        }),
        "steps": step_state,
        "event_count": len(events),
        "journal": str(log_path),
        "journal_problems": problems,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Cancellation gate (FEAT-062 — arch Q5 minimal vertical slice)
# ═══════════════════════════════════════════════════════════════════════════


def _cancel_refusal(closure_id: str, code: str, detail: str) -> Dict[str, Any]:
    """Structured zero-write refusal (closed M0 error-code vocabulary)."""
    return {"closure_id": closure_id, "error": True, "code": code,
            "disposition": ERROR_CODE_DISPOSITIONS.get(code, "manual"),
            "detail": detail}


def _registered_field_refusal(closure_id: str,
                              fields: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """FEAT-062 entry discipline shared by cancel / reopen / takeover
    (FEAT-063): every registered authorization field is a non-empty
    single line without the writer's row delimiter. Zero-write structured
    refusals; ``|`` is refused because a raw pipe makes the DEC row
    deterministically unwritable and the leg permanently pending
    (review-FEAT-062-R0 F-1)."""
    for label, value in fields.items():
        if not isinstance(value, str) or not value.strip():
            return _cancel_refusal(
                closure_id, "schema_violation",
                "{0} is required (明确授权者/原因 — a registered "
                "authorization record needs it)".format(label))
        if "\n" in value or "\r" in value:
            return _cancel_refusal(
                closure_id, "schema_violation",
                "{0} must be a single line (writer row cells "
                "cannot carry newlines)".format(label))
        if "|" in value:
            return _cancel_refusal(
                closure_id, "schema_violation",
                "{0} must not contain '|' (writer table-row cell "
                "delimiter — a raw pipe makes the decision row "
                "deterministically unwritable and the cancellation leg "
                "permanently pending)".format(label))
    return None


def _cancelled_event(events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return next((e for e in events
                 if e.get("event_type") == "closure_cancelled"), None)


def _step_kinds(events: List[Dict[str, Any]]) -> Dict[str, str]:
    """{step_id: declared kind} from the journal's step_started events."""
    kinds: Dict[str, str] = {}
    for ev in events:
        payload = ev.get("payload") or {}
        step_id = payload.get("step_id")
        if step_id and ev.get("event_type") == "step_started":
            kinds[step_id] = payload.get("kind") or ""
    return kinds


def _derived_status(events: List[Dict[str, Any]],
                    step_state: Dict[str, str]) -> str:
    """The closure's derived status — the same derivation closure_status
    uses (cancelled > finalized > blocked > awaiting-world-check > ready >
    running); the CAS face compares against THIS, the world-derived value
    (查世界不信日志 — the journal is the audit, the derivation the state)."""
    if any(e.get("event_type") == "closure_cancelled" for e in events):
        return "cancelled"
    if any(e.get("event_type") == "closure_finalized" for e in events):
        return "finalized"
    if any(v == "failed" for v in step_state.values()):
        return "blocked"
    if any(v == "unknown" for v in step_state.values()):
        return "awaiting-world-check"
    if any(e.get("event_type") == "closure_ready" for e in events):
        return "ready"
    return "running"


def _read_locks_world(governance_dir: Path, task: str) -> Dict[str, Any]:
    """FRESH read-only ownership snapshot of agent-locks.json (查世界不信
    日志 — the ARCH-09 ownership check reads the world AT the decision
    moment, never a remembered state)."""
    locks_file = Path(governance_dir) / "agent-locks.json"
    world: Dict[str, Any] = {"readable": True, "file": str(locks_file),
                             "held_files": [], "active_task_entry": False,
                             "other_lock_count": 0}
    if not locks_file.is_file():
        return world
    try:
        data = json.loads(locks_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        world["readable"] = False
        world["error"] = str(exc)
        return world
    file_locks = data.get("file_locks") if isinstance(data, dict) else {}
    for path, entry in (file_locks or {}).items():
        if isinstance(entry, dict) and entry.get("locked_by") == task:
            world["held_files"].append(path)
        else:
            world["other_lock_count"] += 1
    active = data.get("active_tasks") if isinstance(data, dict) else {}
    world["active_task_entry"] = (isinstance(active, dict)
                                  and task in active)
    return world


def _inspect_task_row(root: Path, task: str, tracker: str) -> Dict[str, Any]:
    """Read-only task-row disclosure for the cancel report (取消不修改任
    务行 — the row's current world state is reported, never rewritten)."""
    target = Path(tracker)
    if not target.is_file():
        target = Path(root) / ".governance" / "plan-tracker.md"
    if not target.is_file():
        return {"found": False, "state": None, "detail": "tracker absent"}
    argv = [sys.executable, str(INFRA_DIR / "task_row_update.py"),
            "--task", task, "--inspect", "--file", str(target), "--json"]
    proc = _run_subprocess(argv, 60.0)
    try:
        payload = json.loads((proc.stdout or "").strip() or "{}")
    except ValueError:
        return {"found": False, "state": None,
                "detail": "inspect output not JSON (exit {0})".format(
                    proc.returncode)}
    if not payload.get("found"):
        return {"found": False, "state": None, "detail": "row not found"}
    return {"found": True, "state": payload.get("state"),
            "detail": "current world state (disclosed, not modified by "
                      "the cancellation)"}


def _run_writer_cli(argv: List[str], timeout: float) -> Dict[str, Any]:
    """Run one governed writer CLI and return its flat JSON payload. A
    subprocess timeout is UNKNOWN (the effect MAY have landed) — the
    deterministic operation id makes the caller's retry a writer-level
    replay, so the payload reports retryable and the retry converges."""
    try:
        proc = _run_subprocess(argv, timeout)
    except subprocess.TimeoutExpired:
        return {"error": True, "code": "lock_contention",
                "disposition": "retryable",
                "detail": "writer subprocess timed out after {0}s — "
                          "result unknown (hard-kill crash window); the "
                          "deterministic operation id makes the retry a "
                          "writer replay".format(timeout)}
    try:
        payload = json.loads((proc.stdout or "").strip() or "{}")
    except ValueError:
        return {"error": True, "code": "manual_intervention",
                "disposition": "manual",
                "detail": "writer exit {0} with non-JSON output: {1!r}"
                          .format(proc.returncode,
                                  (proc.stdout or "")[-200:])}
    if isinstance(payload, dict):
        payload.setdefault("exit_code", proc.returncode)
        return payload
    return {"error": True, "code": "manual_intervention",
            "disposition": "manual",
            "detail": "writer returned a non-dict payload"}


_CANCEL_DEC_CONTENT = (
    "closure {closure_id} 取消（FEAT-062 cancellation gate）：任务 {task} 的 "
    "{chain_id} 链在 {observed_status} 状态由授权者 {authorized_by} 终态取消。"
    "原因：{reason}。保留效果：链内已完成 governed 步骤的落盘效果不回滚"
    "（EVD 行/任务行翻转按 append-only 审计保留）；本取消不修改任务行。")
_CANCEL_DEC_BASIS = (
    "事实依据：closure journal closure_cancelled 事件"
    "（.governance/closure-events.jsonl, unit {closure_id}）"
    "+ arch Q5 纵切 + rollback-0.86.0 §8 #5")
"""Deterministic DEC-row templates — EVERY substitution comes from the
recorded terminal event, so a converged retry produces a byte-identical
payload and the writer's same-id replay fires (volatile world reads live
in the REPORT, never in the registered row)."""


def _cancel_decision_leg(root: Path, closure_id: str, task: str,
                         chain_id: str, authorized_by: str, reason: str,
                         observed_status: str, cancelled_at: str,
                         writer_timeout: float) -> Dict[str, Any]:
    """Cancellation-op registration leg (FEAT-062 point 3): the DEC row is
    appended THROUGH the governed writer CLI (``governance_store
    decision-append``) — never a hand edit; FEAT-064 BLOCK compliance for
    the decision row family. The deterministic per-closure operation id is
    the idempotency key; the writer's pending→ok pipeline registers the op
    in the ops ledger (可审计). A leg refusal NEVER undoes the terminal
    event — it stays pending for the converged retry."""
    op_id = cancel_operation_id(closure_id, _CANCEL_DECISION_SLOT)
    content = _CANCEL_DEC_CONTENT.format(
        closure_id=closure_id, task=task, chain_id=chain_id,
        observed_status=observed_status, authorized_by=authorized_by,
        reason=reason)
    basis = _CANCEL_DEC_BASIS.format(closure_id=closure_id)
    argv = [sys.executable, str(INFRA_DIR / "governance_store.py"),
            "--project-root", str(root), "decision-append",
            "--decider", authorized_by, "--content", content,
            "--basis", basis, "--date", cancelled_at[:10],
            "--operation-id", op_id, "--timeout", str(writer_timeout)]
    payload = _run_writer_cli(argv, writer_timeout + 30.0)
    leg = {"state": "pending", "operation_id": op_id,
           "code": payload.get("code"), "detail": payload.get("detail"),
           "replayed": bool(payload.get("replayed"))}
    if not payload.get("error"):
        leg["state"] = "done_replayed" if payload.get("replayed") else "done"
    return leg


def _cancel_locks_leg(root: Path, closure_id: str, task: str,
                      writer_timeout: float) -> Dict[str, Any]:
    """Own-locks-only release leg (FEAT-062 point 5; ARCH-09 same-type per
    DEC-237 C1-ARCH-09): a FRESH world read decides whether the task still
    holds dispatch locks; the release goes through the governed
    ``locks-release`` CLI — task-scoped by the writer itself (the task's
    active entry + ONLY file locks whose ``locked_by == task``), so a lock
    whose ownership changed is never released by this cancel. No locks →
    no op (the DEC leg carries the cancellation's ops registration).

    FEAT-063 fencing (ARCH-09 owner-token discipline): when the task's
    execution generation is held by ANOTHER closure, this cancel is a
    stale generation's cancel — it records the termination (the terminal +
    DEC leg above) but SKIPS the release (``skipped_fenced``): a stale
    owner's cancel never releases the newer holder's dispatch locks."""
    fence = _execution_fence_refusal(root, task, closure_id)
    if fence is not None:
        return {"state": "skipped_fenced", "operation_id": None,
                "code": fence.get("code"),
                "detail": "task execution generation {0} is held by "
                          "closure {1} — a stale generation's cancel "
                          "never releases the newer holder's dispatch "
                          "locks (FEAT-063 takeover fencing; ARCH-09 "
                          "same-type)".format(
                              fence.get("observed_generation"),
                              fence.get("observed_holder")),
                "world_before": None, "world_after": None}
    gov = Path(root) / ".governance"
    world = _read_locks_world(gov, task)
    if not world["readable"]:
        return {"state": "pending", "operation_id": None, "code": None,
                "detail": "agent-locks.json unreadable ({0}) — release "
                          "leg pending".format(world.get("error")),
                "world_before": world, "world_after": None}
    if not world["held_files"] and not world["active_task_entry"]:
        return {"state": "skipped_no_locks", "operation_id": None,
                "code": None,
                "detail": "task holds no dispatch locks — nothing to "
                          "release, no locks op registered",
                "world_before": world, "world_after": world}
    op_id = cancel_operation_id(closure_id, _CANCEL_LOCKS_SLOT)
    argv = [sys.executable, str(INFRA_DIR / "governance_store.py"),
            "--project-root", str(root), "locks-release",
            "--task", task, "--operation-id", op_id,
            "--timeout", str(writer_timeout)]
    payload = _run_writer_cli(argv, writer_timeout + 30.0)
    world_after = _read_locks_world(gov, task)
    leg = {"operation_id": op_id, "code": payload.get("code"),
           "detail": payload.get("detail"),
           "replayed": bool(payload.get("replayed")),
           "world_before": world, "world_after": world_after}
    if not payload.get("error") and not world_after["held_files"] \
            and not world_after["active_task_entry"]:
        # the locks family's _complete_pending marks EVERY ok completion
        # replayed=True (source="apply" for a fresh apply — the effect-based
        # pipeline convention); the leg discriminator is replay_source:
        # "ledger" = a true writer replay, any other source converged THIS
        # run.
        leg["state"] = ("done_replayed"
                        if payload.get("replay_source") == "ledger"
                        else "done")
    else:
        leg["state"] = "pending"
    return leg


def _cancel_reconciliation(root: Path, task: str, dec_leg: Dict[str, Any],
                           locks_leg: Dict[str, Any],
                           events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """closure 结果 + ops 对账 (FEAT-062 point 6): re-read the journal
    terminal (review-FEAT-062-R0 F-4: the terminal presence is MEASURED
    from the re-read journal, not hardcoded — the re-read events are the
    post-leg world), the ops ledger (read-only, fail-safe) and the locks
    world; the WORLD is the truth (查世界不信台账) — a ledger ``ok``
    without the world marker is inconsistent, never silently absorbed."""
    gov = Path(root) / ".governance"
    ledger_ops: Dict[str, Any] = {}
    ledger_path = gov / "governance-store-ops.json"
    if ledger_path.is_file():
        try:
            data = json.loads(ledger_path.read_text(encoding="utf-8"))
            operations = data.get("operations") or {}
            for op_id in (dec_leg.get("operation_id"),
                          locks_leg.get("operation_id")):
                if op_id:
                    ledger_ops[op_id] = (operations.get(op_id) or {}) \
                        .get("status")
        except (OSError, ValueError) as exc:
            ledger_ops["_error"] = "ops ledger unreadable: {0}".format(exc)
    dec_op = dec_leg.get("operation_id")
    dec_path = gov / "decision-log.md"
    dec_in_world = False
    if dec_op and dec_path.is_file():
        try:
            dec_in_world = ("decision-append " + dec_op) \
                in dec_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            dec_in_world = False
    world = _read_locks_world(gov, task)
    locks_world_clear = (
        locks_leg.get("state") in ("skipped_no_locks", "skipped_fenced")
        or (world["readable"] and not world["held_files"]
            and not world["active_task_entry"]))
    legs_done = (
        dec_leg.get("state") in _CANCEL_LEG_DONE_STATES
        and locks_leg.get("state")
        in _CANCEL_LEG_DONE_STATES
        + ("skipped_no_locks", "skipped_fenced"))
    consistent = bool(legs_done and dec_in_world and locks_world_clear)
    return {"journal_terminal": any(
                e.get("event_type") == "closure_cancelled" for e in events),
            "decision_row_in_world": dec_in_world,
            "ops_ledger": ledger_ops,
            "locks_world_clear": locks_world_clear,
            "consistent": consistent,
            "retry_hint": (None if consistent else
                           "re-run the SAME cancel command — the "
                           "deterministic operation ids make the retry "
                           "replay/apply at the writers and converge the "
                           "pending leg (exit 3 signals this state)")}


def _cancel_locked(root: Path, closure_id: str, authorized_by: str,
                   reason: str, expected_status: Optional[str],
                   log_path: Path, writer_timeout: float) -> Dict[str, Any]:
    # FIX-391 version-aware preflight: a cancel derives the status from
    # the journal and then appends the terminal + releases dispatch locks
    # — a newer writer's terminal in an unknown type would be misread as
    # «active» and re-terminated. Refuse zero-write first (the
    # append/derive face of the same version-misread vector).
    conflict = _journal_version_conflict(log_path, closure_id)
    if conflict is not None:
        return conflict
    events, problems = _load_closure_events(log_path, closure_id)
    started = next((e for e in events
                    if e.get("event_type") == "closure_started"), None)
    if started is None:
        return _cancel_refusal(
            closure_id, "cross_record_violation",
            "closure {0} has no journal — nothing to cancel".format(
                closure_id))
    started_payload = started.get("payload") or {}
    task = started_payload.get("task")
    chain_id = started_payload.get("chain_id") or "unknown"
    if not isinstance(task, str) or not task:
        return _cancel_refusal(
            closure_id, "cross_record_violation",
            "closure {0} journal carries no task id — refusing to cancel"
            .format(closure_id))
    prior = _cancelled_event(events)
    step_state = _step_world_state(events)
    derived = _derived_status(events, step_state)
    if prior is None:
        # ── restricted entry (限定入口) — every gate here is zero-write ──
        if any(e.get("event_type") == "closure_finalized" for e in events):
            return _cancel_refusal(
                closure_id, "cross_record_violation",
                "closure {0} is FINALIZED (immutable terminal) — "
                "cancellation refused (不可取消状态)".format(closure_id))
        kinds = _step_kinds(events)
        external_terminal = sorted(
            s for s, state in step_state.items()
            if kinds.get(s) == "external"
            and state in ("completed", "failed", "unknown"))
        if external_terminal:
            return _cancel_refusal(
                closure_id, "manual_intervention",
                "closure {0} carries external-step effects {1} — the "
                "outside action needs human adjudication before any "
                "cancellation (有副作用明确拒绝; zero changes made)"
                .format(closure_id, external_terminal))
        undetermined = sorted(
            s for s, state in step_state.items()
            if state in ("unknown", "started"))
        if undetermined:
            return _cancel_refusal(
                closure_id, "manual_intervention",
                "closure {0} has undetermined step effects {1} (crash "
                "window / UNKNOWN) — resume first to converge the world, "
                "then cancel (zero changes made)".format(
                    closure_id, undetermined))
        if expected_status is not None and derived != expected_status:
            refusal = _cancel_refusal(
                closure_id, "revision_conflict",
                "CAS mismatch: expected status {0!r} but the closure is "
                "now {1!r} — re-judge from the observed state (零状态变化)"
                .format(expected_status, derived))
            refusal["observed_status"] = derived
            return refusal
        # ── the CAS terminal append (one seq-continuous event, under the
        #    run lock — the same lock run/finalize take) ──
        locks_world = _read_locks_world(Path(root) / ".governance", task)
        seq, prev_seq = _next_seq(events)
        envelope = _append_closure_event(
            log_path, closure_id, "closure_cancelled", seq, prev_seq, {
                "task": task,
                "chain_id": chain_id,
                "authorized_by": authorized_by,
                "reason": reason,
                "observed_status": derived,
                "expected_status": expected_status,
                "locks_held": bool(locks_world["held_files"]
                                   or locks_world["active_task_entry"]),
                "locks_files": list(locks_world["held_files"]),
                "code_revision": _git_head(root),
            })
        intent = {"authorized_by": authorized_by, "reason": reason,
                  "observed_status": derived,
                  "cancelled_at": envelope["timestamp"]}
    else:
        # replay: converge with the RECORDED intent — the first
        # authorization stands; fresh CLI args are never re-recorded
        prior_payload = prior.get("payload") or {}
        intent = {"authorized_by": prior_payload.get("authorized_by") or "",
                  "reason": prior_payload.get("reason") or "",
                  "observed_status": prior_payload.get("observed_status")
                  or "",
                  "cancelled_at": prior.get("timestamp") or ""}
    # ── writer legs (deterministic ids; a refusal stays pending — the
    #    terminal event is NOT undone, the retry converges) ──
    dec_leg = _cancel_decision_leg(
        root, closure_id, task, chain_id, intent["authorized_by"],
        intent["reason"], intent["observed_status"],
        intent["cancelled_at"], writer_timeout)
    locks_leg = _cancel_locks_leg(root, closure_id, task, writer_timeout)
    # ── world disclosures + reconciliation ──
    events, problems_after = _load_closure_events(log_path, closure_id)
    problems = sorted(set(problems) | set(problems_after))
    step_state = _step_world_state(events)
    completed_steps = sorted(s for s, state in step_state.items()
                             if state == "completed")
    tracker = (started_payload.get("inputs") or {}).get("tracker_file") \
        or ".governance/plan-tracker.md"
    return {
        "closure_id": closure_id,
        "task": task,
        "chain_id": chain_id,
        "status": "cancelled",
        "replayed": prior is not None,
        "authorized_by": intent["authorized_by"],
        "reason": intent["reason"],
        "observed_status": intent["observed_status"],
        "cancelled_at": intent["cancelled_at"],
        "operation_ids": {"decision": dec_leg.get("operation_id"),
                          "locks": locks_leg.get("operation_id")},
        "legs": {"decision": dec_leg, "locks": locks_leg},
        "retained_effects": {
            "completed_steps": completed_steps,
            "task_row": _inspect_task_row(root, task, tracker),
            "note": "governed effects already landed stay (append-only "
                    "audit); the task row is disclosed, not modified",
        },
        "reconciliation": _cancel_reconciliation(root, task, dec_leg,
                                                 locks_leg, events),
        "journal": str(log_path),
        "journal_problems": problems,
    }


def cancel_closure(root: Path, closure_id: str, *, authorized_by: str,
                   reason: str, expected_status: Optional[str] = None,
                   lock_timeout: float = 10.0,
                   writer_timeout: float = 30.0) -> Dict[str, Any]:
    """FEAT-062 cancellation gate — terminate a non-finalized closure.

    Restricted entry → CAS terminal append → writer-registered DEC row +
    own-locks-only release → reconciliation. See the module docstring
    section "Cancellation vertical slice" for the full design contract
    (arch Q5 / rollback-0.86.0 §8 #5 / DEC-237 C1-ARCH-09 same-type /
    FEAT-064 BLOCK compliance). Zero-write refusals carry a closed M0
    code; ``lock_contention`` (在途写冲突 — an in-flight chain holds the
    run lock) is retryable with zero changes made."""
    root = Path(root)
    closure_id = require_closure_id("cancel: closure_id", closure_id)
    field_refusal = _registered_field_refusal(
        closure_id, {"authorized_by": authorized_by, "reason": reason})
    if field_refusal is not None:
        return field_refusal
    if expected_status is not None \
            and expected_status not in CANCELLABLE_STATUSES:
        return _cancel_refusal(
            closure_id, "schema_violation",
            "cancel expected status {0!r} not in the cancellable set {1}"
            .format(expected_status, CANCELLABLE_STATUSES))
    log_path = default_event_log_path(root)
    lock_path = _closure_lock_dir(root) / (closure_id + ".lock")
    try:
        with _RunLock(lock_path, lock_timeout):
            return _cancel_locked(root, closure_id, authorized_by, reason,
                                  expected_status, log_path,
                                  writer_timeout)
    except LockContention as exc:
        return {"closure_id": closure_id, "error": True,
                "code": "lock_contention", "disposition": "retryable",
                "detail": "{0} (在途写冲突: an in-flight chain/finalize "
                          "holds the closure run lock — the cancellation "
                          "made ZERO changes; retry after the chain "
                          "halts)".format(exc)}


# ═══════════════════════════════════════════════════════════════════════════
# Execution generation / takeover fencing (FEAT-063 — FEAT-061 epoch
# fencing same-type, ARCH-09 owner-token discipline)
# ═══════════════════════════════════════════════════════════════════════════


def _generations_path(root: Path) -> Path:
    """The per-task execution-generation record:
    ``<root>/.governance/closure-generations.json``."""
    return Path(root) / ".governance" / CLOSURE_GENERATIONS_FILENAME


def _generations_lock_path(root: Path) -> Path:
    """Cross-process lock for the generations record (closure-locks
    precedent: the lock FILE stays; only the byte-range lease is
    transient)."""
    return _closure_lock_dir(root) / "generations.lock"


def _load_execution_generations(
        root: Path) -> Tuple[Dict[str, Any], Optional[str]]:
    """Read the generations record (fail-safe). Missing file → an EMPTY
    map (unfenced world — zero behavior change for tasks nobody took
    over). Unreadable/corrupt → ``( {}, error )`` — the caller judges:
    the fence refuses fail-closed (the authority is unjudgeable), the
    takeover refuses manual_intervention."""
    path = _generations_path(root)
    if not path.is_file():
        return {}, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {}, "closure-generations.json unreadable: {0}".format(exc)
    if not isinstance(data, dict) or not isinstance(
            data.get("tasks") or {}, dict):
        return {}, ("closure-generations.json has an invalid shape "
                    "(expected an object with a tasks object)")
    return data, None


def _fsync_dir(path: Path) -> None:
    """Best-effort directory fsync after a replace (POSIX crash-durability
    nicety; Windows disallows opening directories — swallowed). The
    governance_store writer-family shape, mirrored locally (the chain
    never imports the writer module — kill-switch dependency direction)."""
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _write_execution_generations(root: Path, data: Dict[str, Any]) -> None:
    """Atomic replace of the generations record — writer-family reliable
    persistence discipline (review-FEAT-063-R0 P2-3): same-directory
    mkstemp temp + fsync + os.replace + best-effort dir fsync. Callers
    hold ``_generations_lock_path`` — the serialization point."""
    path = _generations_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(data)
    payload.setdefault("schema_version", 1)
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2)
               + "\n").encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(tmp_path), str(path))
        _fsync_dir(path.parent)
    except BaseException:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def _execution_fence_refusal(root: Path, task: str,
                             closure_id: str) -> Optional[Dict[str, Any]]:
    """The write-side fence probe (FEAT-063): ``None`` = unfenced (the
    task carries no record, or THIS closure IS the current holder); a
    dict = structured ``revision_conflict`` refusal (FEAT-061 epoch-
    fencing same-type: the world's generation moved past this executor).
    An UNREADABLE record refuses fail-closed for every task — the fence
    authority is unjudgeable and the module never writes through an
    unjudgeable authority check."""
    data, error = _load_execution_generations(root)
    if error:
        return {"closure_id": closure_id, "task": task, "error": True,
                "code": "revision_conflict", "disposition": "conflict",
                "observed_generation": None, "observed_holder": None,
                "detail": "execution generation record unreadable ({0}) — "
                          "the write-side fence cannot be verified; "
                          "refusing fail-closed (repair or remove "
                          ".governance/{1} to restore a judgeable world)"
                          .format(error, CLOSURE_GENERATIONS_FILENAME)}
    record = (data.get("tasks") or {}).get(task) \
        if isinstance(data.get("tasks"), dict) else None
    if not isinstance(record, dict):
        return None
    holder = record.get("holder_closure_id")
    if holder == closure_id:
        return None
    return {"closure_id": closure_id, "task": task, "error": True,
            "code": "revision_conflict", "disposition": "conflict",
            "observed_generation": record.get("generation"),
            "observed_holder": holder,
            "detail": "execution generation fenced: task {0} current "
                      "generation {1!r} is held by closure {2!r} — this "
                      "closure {3} is a stale generation; its run/step/"
                      "finalize writes are refused at the write side "
                      "(FEAT-063 takeover fencing, 旧代际写入被拒). "
                      "Recovery: the current holder drives the task; to "
                      "re-bind this closure run takeover --task {0} "
                      "--new-holder {3} (explicit authorization required "
                      "— a heartbeat timeout is never a stop proof)"
                      .format(task, record.get("generation"), holder,
                              closure_id)}


def _record_fenced_event(root: Path, log_path: Path, closure_id: str,
                         fence: Dict[str, Any]) -> None:
    """ONE idempotent ``closure_fenced`` audit event per closure — the
    journal records WHY this executor stopped participating (the fence is
    a fact, not an event stream; repeated refusals re-record nothing)."""
    events, _problems = _load_closure_events(log_path, closure_id)
    if any(e.get("event_type") == "closure_fenced" for e in events):
        return
    seq, prev_seq = _next_seq(events)
    _append_closure_event(
        log_path, closure_id, "closure_fenced", seq, prev_seq, {
            "task": fence.get("task"),
            "observed_generation": fence.get("observed_generation"),
            "observed_holder": fence.get("observed_holder"),
            "detail": (fence.get("detail") or "")[:400],
            "code_revision": _git_head(root),
        })


def takeover_execution(root: Path, task: str, new_holder: str, *,
                       authorized_by: str, reason: str,
                       lock_timeout: float = 10.0) -> Dict[str, Any]:
    """FEAT-063 异常接管 — promote the task's execution generation and
    bind a new holder closure (the fencing token's write side).

    Gates (zero-write refusals): task id + ``--new-holder`` closure-id
    form; ``authorized_by``/``reason`` (the FEAT-062 field discipline —
    explicit HUMAN authorization). The promotion serializes on (a) the
    generations record lock and (b) the PRIOR holder's per-closure run
    lock — an in-flight chain refuses ``lock_contention`` (retryable,
    zero changes), so a takeover never fences a run that is mid-flight.
    The in-lock re-read re-validates the prior holder against the world
    (review-FEAT-063-R0 P0-1): a holder that changed between the lock-out
    pre-read and the lock means the acquired run lock belonged to a
    FORMER holder — refuse ``lock_contention`` retryable with zero
    writes (no in-lock lock-swapping loop; the retry re-judges).

    Heartbeat semantics (如实): heartbeat timeout is NOT a stop proof
    (心跳超时不构成停止证明). This gate never reads any heartbeat/TTL as
    evidence of executor death — FEAT-044's round-heartbeat mechanism is
    E3, not this slice. The two conditions above make the human's
    takeover decision explicit and serialized; neither PROVES the prior
    executor is dead. If the judgment is wrong, the write-side fence
    protects the world: the "dead" executor's next run/step/finalize
    refuses ``revision_conflict`` loudly (and can be re-bound with
    another takeover) instead of writing through.

    First takeover on a task (no record): binds generation 1 with no
    prior holder — nothing is fenced yet, the world only gains the
    authority record. An unreadable record refuses manual_intervention
    (unjudgeable authority)."""
    root = Path(root)
    if not isinstance(task, str) or not task.strip():
        return {"error": True, "code": "schema_violation",
                "disposition": "validation",
                "detail": "task id is required (接管按任务绑定)"}
    task = task.strip()
    new_holder = require_closure_id("takeover: new_holder", new_holder)
    field_refusal = _registered_field_refusal(
        new_holder, {"authorized_by": authorized_by, "reason": reason})
    if field_refusal is not None:
        return field_refusal
    data, error = _load_execution_generations(root)
    if error:
        return {"task": task, "new_holder": new_holder, "error": True,
                "code": "manual_intervention",
                "disposition": "manual",
                "detail": "{0} — the execution-generation authority is "
                          "unjudgeable; takeover refused (repair or "
                          "remove the record first)".format(error)}
    record = (data.get("tasks") or {}).get(task)
    if isinstance(record, dict) \
            and record.get("holder_closure_id") == new_holder:
        return {"task": task, "new_holder": new_holder, "error": True,
                "code": "schema_violation",
                "disposition": "validation",
                "detail": "closure {0} already holds task {1}'s "
                          "execution generation (generation {2!r}) — "
                          "no takeover needed".format(
                              new_holder, task, record.get("generation"))}
    prior_holder = record.get("holder_closure_id") \
        if isinstance(record, dict) else None
    # TEST-ONLY fault point (BT-9 channel, never a CLI face): pauses AFTER
    # the lock-out pre-read captured prior_holder and BEFORE the
    # generations lock — the deterministic window for the P0-1 TOCTOU
    # red-state injection (a concurrent promotion lands in this gap).
    _maybe_fault("post-generations-preread")
    generations_lock = _RunLock(_generations_lock_path(root), lock_timeout)
    try:
        generations_lock.__enter__()
    except LockContention as exc:
        return {"task": task, "new_holder": new_holder, "error": True,
                "code": "lock_contention", "disposition": "retryable",
                "detail": "{0} (another takeover holds the generations "
                          "record lock — retry)".format(exc)}
    old_holder_lock = None
    try:
        if prior_holder is not None:
            # serialize the promotion against the prior holder's run —
            # an in-flight chain holds this lock (lock_contention,
            # retryable): a takeover never fences a mid-flight run.
            old_holder_lock = _RunLock(
                _closure_lock_dir(root) / (prior_holder + ".lock"),
                lock_timeout)
            try:
                old_holder_lock.__enter__()
            except LockContention as exc:
                return {"task": task, "new_holder": new_holder,
                        "error": True, "code": "lock_contention",
                        "disposition": "retryable",
                        "detail": "{0} (在途写冲突: the prior holder's "
                                  "chain is in flight — no heartbeat/"
                                  "staleness reading proves it dead; "
                                  "wait for the run to halt or resolve "
                                  "it out-of-band, then retry)".format(
                                      exc)}
        data, error = _load_execution_generations(root)
        if error:
            return {"task": task, "new_holder": new_holder, "error": True,
                    "code": "manual_intervention",
                    "disposition": "manual",
                    "detail": "{0} — re-judge after repairing the "
                              "record".format(error)}
        tasks = data.setdefault("tasks", {})
        current = tasks.get(task)
        observed_holder = current.get("holder_closure_id") \
            if isinstance(current, dict) else None
        if observed_holder == new_holder:
            return {"task": task, "new_holder": new_holder,
                    "error": True, "code": "schema_violation",
                    "disposition": "validation",
                    "detail": "closure {0} already holds task {1}'s "
                              "execution generation (generation "
                              "{2!r}) — no takeover needed".format(
                                  new_holder, task,
                                  current.get("generation")
                                  if isinstance(current, dict) else None)}
        if observed_holder != prior_holder:
            # P0-1 (review-FEAT-063-R0): the world moved between the
            # lock-out pre-read and the generations lock — the run lock we
            # acquired belongs to a FORMER holder, and the REAL prior
            # holder may be mid-flight. Promoting now would fence a
            # possibly-in-flight run, violating the lock_contention
            # invariant (a takeover never fences a mid-flight run). ZERO
            # writes; the retry re-judges from the current world. No
            # in-lock lock-swapping loop — swapping to the newly observed
            # id would just relocate the same race one step further.
            return {"task": task, "new_holder": new_holder,
                    "error": True, "code": "lock_contention",
                    "disposition": "retryable",
                    "detail": "prior holder changed between the pre-read "
                              "({0!r}) and the generations lock ({1!r}) — "
                              "the acquired run lock belongs to a former "
                              "holder; the promotion made ZERO changes "
                              "(re-run the takeover against the current "
                              "world; retryable)".format(
                                  prior_holder, observed_holder)}
        prior_generation = current.get("generation") \
            if isinstance(current, dict) else None
        generation = (prior_generation + 1) \
            if isinstance(prior_generation, int) \
            and not isinstance(prior_generation, bool) else 1
        promoted_at = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        tasks[task] = {
            "generation": generation,
            "holder_closure_id": new_holder,
            "prior_holder_closure_id": prior_holder,
            "prior_generation": prior_generation,
            "promoted_by": authorized_by,
            "promoted_at": promoted_at,
            "reason": reason,
        }
        _write_execution_generations(root, data)
    finally:
        if old_holder_lock is not None:
            old_holder_lock.__exit__(None, None, None)
        generations_lock.__exit__(None, None, None)
    return {"task": task, "generation": generation,
            "holder_closure_id": new_holder,
            "prior_holder_closure_id": prior_holder,
            "prior_generation": prior_generation,
            "promoted_by": authorized_by, "reason": reason,
            "promoted_at": promoted_at,
            "generations_file": str(_generations_path(root)),
            "fence_note": "the prior holder's subsequent run/step/"
                          "finalize writes are refused at the write side "
                          "(revision_conflict); heartbeat timeout is "
                          "not a stop proof — this takeover stands on "
                          "the recorded authorization above"}


# ═══════════════════════════════════════════════════════════════════════════
# Reopen with attempt lineage (FEAT-063 — append-only, single-successor)
# ═══════════════════════════════════════════════════════════════════════════


def _resolve_reopen_linkage(root: Path, reopen_of: str,
                            expected_successor: Optional[str]) \
        -> Dict[str, Any]:
    """Bind a successor run to the RECORDED reopen linkage (FEAT-063):
    the referenced closure's ``closure_reopened`` event is the only source
    of the successor id + attempt (recorded intent — fresh ids/args never
    fork the lineage). Raises ValueError (zero-write refusals)."""
    reopen_of = require_closure_id("run_chain: reopen_of", reopen_of)
    events, _problems = _load_closure_events(
        default_event_log_path(root), reopen_of)
    if not any(e.get("event_type") == "closure_started" for e in events):
        raise ValueError(
            "reopen_of closure {0} has no journal — nothing to reopen "
            "(--reopen-of binds a RECORDED reopen linkage; run the "
            "reopen command first)".format(reopen_of))
    event = next((e for e in events
                  if e.get("event_type") == "closure_reopened"), None)
    if event is None:
        raise ValueError(
            "reopen_of closure {0} carries no closure_reopened event — "
            "run `reopen --closure-id {0}` first; --reopen-of never "
            "mints a successor".format(reopen_of))
    payload = event.get("payload") or {}
    successor = require_closure_id("reopen linkage successor",
                                   payload.get("successor_closure_id"))
    attempt = payload.get("reopen_attempt")
    if not isinstance(attempt, int) or isinstance(attempt, bool) \
            or attempt < 2:
        raise ValueError(
            "reopen linkage event of closure {0} carries an invalid "
            "reopen_attempt {1!r}".format(reopen_of, attempt))
    if expected_successor is not None and expected_successor != successor:
        raise ValueError(
            "reopen linkage mismatch: closure {0} recorded successor {1} "
            "but closure id {2!r} was given — the recorded linkage stands "
            "(single-successor lineage; a fresh id would fork the attempt "
            "chain)".format(reopen_of, successor, expected_successor))
    return {"successor_closure_id": successor, "reopen_attempt": attempt,
            "prior_status": payload.get("prior_status"),
            "authorized_by": payload.get("authorized_by")}


def _reopen_locked(root: Path, closure_id: str, authorized_by: str,
                   reason: str, log_path: Path) -> Dict[str, Any]:
    # FIX-391 version-aware preflight: reopen derives the terminal status
    # from the journal and mints the attempt lineage — a partial view
    # must never fork the lineage. Refuse zero-write first.
    conflict = _journal_version_conflict(log_path, closure_id)
    if conflict is not None:
        return conflict
    events, problems = _load_closure_events(log_path, closure_id)
    started = next((e for e in events
                    if e.get("event_type") == "closure_started"), None)
    if started is None:
        return _cancel_refusal(
            closure_id, "cross_record_violation",
            "closure {0} has no journal — nothing to reopen".format(
                closure_id))
    started_payload = started.get("payload") or {}
    task = started_payload.get("task")
    chain_id = started_payload.get("chain_id") or "unknown"
    if not isinstance(task, str) or not task:
        return _cancel_refusal(
            closure_id, "cross_record_violation",
            "closure {0} journal carries no task id — refusing to reopen"
            .format(closure_id))
    prior = next((e for e in events
                  if e.get("event_type") == "closure_reopened"), None)
    if prior is not None:
        prior_payload = prior.get("payload") or {}
        return _cancel_refusal(
            closure_id, "cross_record_violation",
            "closure {0} was already reopened as {1} (attempt {2!r}) — "
            "reopen THAT closure's terminal state instead; a second "
            "successor would fork the attempt chain (single-successor "
            "lineage, FEAT-063)".format(
                closure_id, prior_payload.get("successor_closure_id"),
                prior_payload.get("reopen_attempt")))
    step_state = _step_world_state(events)
    derived = _derived_status(events, step_state)
    if derived not in REOPENABLE_STATUSES:
        return _cancel_refusal(
            closure_id, "cross_record_violation",
            "closure {0} is {1!r} — reopen requires a TERMINAL closure "
            "(cancelled|finalized); a non-terminal closure simply "
            "resumes, and a cancelled one re-converges via its cancel "
            "command".format(closure_id, derived))
    try:
        own_attempt = int((started_payload.get("inputs") or {})
                          .get("reopen_attempt"))
    except (TypeError, ValueError):
        own_attempt = 1
    if own_attempt < 1:
        own_attempt = 1
    successor = new_closure_id()
    successor_attempt = own_attempt + 1
    seq, prev_seq = _next_seq(events)
    _append_closure_event(
        log_path, closure_id, "closure_reopened", seq, prev_seq, {
            "task": task,
            "chain_id": chain_id,
            "successor_closure_id": successor,
            "reopen_attempt": successor_attempt,
            "prior_status": derived,
            "authorized_by": authorized_by,
            "reason": reason,
            "code_revision": _git_head(root),
        })
    original_inputs = dict(started_payload.get("inputs") or {})
    run_inputs = {key: value for key, value in sorted(original_inputs.items())
                  if key not in ("reopen_of", "reopen_attempt")}
    run_argv = [sys.executable, str(Path(__file__).resolve()),
                "--project-root", str(root), "run", "--task", task,
                "--closure-id", successor, "--reopen-of", closure_id]
    if chain_id in _BUILTIN_CHAINS:
        run_argv += ["--chain", chain_id]
    for key, value in run_inputs.items():
        run_argv += ["--input", "{0}={1}".format(key, value)]
    run_note = ("the successor binds the recorded linkage via "
                "--reopen-of (adopted successor id + injected "
                "reopen_of/reopen_attempt inputs; resume carries the "
                "same flag — inputs-digest identity)")
    if chain_id not in _BUILTIN_CHAINS:
        run_note += ("; the original chain {0!r} is not a built-in — "
                     "pass the same --spec file".format(chain_id))
    return {
        "closure_id": closure_id,
        "task": task,
        "chain_id": chain_id,
        "status": "reopened",
        "successor_closure_id": successor,
        "reopen_attempt": successor_attempt,
        "prior_status": derived,
        "authorized_by": authorized_by,
        "reason": reason,
        "original_records_preserved": True,
        "run_argv": run_argv,
        "run_note": run_note,
        "journal": str(log_path),
        "journal_problems": problems,
    }


def reopen_closure(root: Path, closure_id: str, *, authorized_by: str,
                   reason: str, lock_timeout: float = 10.0) -> Dict[str, Any]:
    """FEAT-063 重开 — mint a successor attempt for a TERMINAL closure
    (cancelled / finalized) and record the lineage WITHOUT touching any
    original record (append-only audit; 原记录零擦除):

    * the original stays terminal — resume of it keeps refusing, its
      events are never rewritten, the journal only GAINS one
      seq-continuous ``closure_reopened`` event (successor id + attempt
      number + authorization), appended under the SAME per-closure run
      lock run/finalize/cancel take (CAS with any concurrent terminal
      action);
    * SINGLE-SUCCESSOR lineage: a second reopen refuses naming the
      recorded successor (a fork would corrupt the attempt numbering);
      the chain deepens by reopening the successor's terminal state;
    * the successor binds the recorded linkage via
      ``run --reopen-of <original>`` (see :func:`run_chain`) — the
      successor's ``closure_started`` carries the back-link and the
      digest binds it;
    * authorization discipline = the cancel gate's (shared helper);
      zero-write structured refusals carry closed M0 codes."""
    root = Path(root)
    closure_id = require_closure_id("reopen: closure_id", closure_id)
    field_refusal = _registered_field_refusal(
        closure_id, {"authorized_by": authorized_by, "reason": reason})
    if field_refusal is not None:
        return field_refusal
    log_path = default_event_log_path(root)
    lock_path = _closure_lock_dir(root) / (closure_id + ".lock")
    try:
        with _RunLock(lock_path, lock_timeout):
            return _reopen_locked(root, closure_id, authorized_by, reason,
                                  log_path)
    except LockContention as exc:
        return {"closure_id": closure_id, "error": True,
                "code": "lock_contention", "disposition": "retryable",
                "detail": "{0} (在途写冲突: an in-flight chain/finalize/"
                          "cancel holds the closure run lock — the "
                          "reopen made ZERO changes; retry after it "
                          "halts)".format(exc)}


# ═══════════════════════════════════════════════════════════════════════════
# CLI — composition root (standalone; engine dispatch wiring is NOT in scope)
# ═══════════════════════════════════════════════════════════════════════════


def _configure_stdio() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — best-effort console hygiene
        pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="closure_chain.py",
        description="FEAT-056 closure-chain orchestrator (M3 vertical "
                    "slice) — pure sequence runner over governed writer "
                    "CLIs; effect-based resume; commit/push stay outside "
                    "the chain",
        epilog=(
            "Exit-code scale (this CLI): 0 = run ready/finalized (or "
            "status/finalize/cancel/reopen/takeover ok); 2 = blocked / "
            "awaiting-world-check / validation refusal / usage error / "
            "stale-generation fence refusal (revision_conflict); "
            "3 = retryable lock contention, or a cancelled closure with "
            "a pending convergence leg (re-run the same cancel command).  "
            "FIX-379 item-3 (0.86.0 M-2 observation #3): "
            "per-family exit SCALES DIFFER across the governed-writer "
            "CLIs this chain invokes (governance_store: 0 ok / 2 refusal "
            "/ 3 retryable; task_row_update: 0 ok / 2 usage / 3 "
            "validation / 4 conflict / 5 retryable / 6 manual) — the "
            "canonical four-family table lives at the verify_workflow.py "
            "dispatch comment (FIX-375 F-2/F-3).  The chain itself does "
            "NOT branch CLI-step failures on writer exit codes: a "
            "non-zero writer exit is decoded from the writer's structured "
            "JSON payload (code/disposition/detail), and only EXTERNAL "
            "steps branch on their declared blocked_exit_codes."))
    parser.add_argument("--project-root", default=".",
                        help="Host project root (default: cwd)")
    parser.add_argument("--schema-version", type=int,
                        default=CLOSURE_SCHEMA_VERSION,
                        help="Closure record-family schema version (v1)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run", help="run/resume a declared chain")
    p.add_argument("--chain", default="standard-ticket-closure",
                   help="Built-in chain id (default: standard-ticket-"
                        "closure); a --spec file overrides")
    p.add_argument("--spec", default=None,
                   help="Path to a chain-spec JSON file (declarative)")
    p.add_argument("--task", required=True, help="Task id this closure "
                "closes")
    p.add_argument("--closure-id", default=None,
                   help="Resume an existing closure (default: mint one)")
    p.add_argument("--input", action="append", default=[], metavar="K=V",
                   help="Chain input (repeatable)")
    p.add_argument("--dry-run", action="store_true",
                   help="Zero-write resolution proof: probes + writer "
                        "dry-runs only")
    p.add_argument("--world-check", action="store_true",
                   help="Allow read-only world-check commands when resuming "
                        "an UNKNOWN external step (default: suggested "
                        "only, never auto-run)")
    p.add_argument("--reopen-of", default=None, dest="reopen_of",
                   help="FEAT-063: bind this run to the RECORDED reopen "
                        "linkage of the referenced closure (adopts the "
                        "recorded successor id + attempt; a different "
                        "--closure-id refuses)")
    p.add_argument("--lock-timeout", type=float, default=10.0)
    # FEAT-056 R0 P3-⑥: the vestigial always-true ``--json`` flag was
    # removed — every subcommand prints a JSON payload unconditionally (the
    # structured-output contract); the flag documented nothing and gated
    # nothing. (CLI-face note: callers still passing ``--json`` get the
    # standard argparse unrecognized-argument error — the flag was a no-op,
    # so dropping it changes no behavior for correct callers.)

    p = sub.add_parser("status", help="structured closure status")
    p.add_argument("--closure-id", required=True)

    p = sub.add_parser("finalize", help="explicit completion gate "
                       "(verifies the operator commit, records the fact)")
    p.add_argument("--closure-id", required=True)
    p.add_argument("--commit-sha", required=True)

    p = sub.add_parser("cancel", help="FEAT-062 cancellation gate: "
                       "terminate a non-finalized closure (restricted "
                       "entry + CAS terminal + writer-registered DEC op "
                       "+ own-locks-only release + ops reconciliation)")
    p.add_argument("--closure-id", required=True)
    p.add_argument("--authorized-by", required=True,
                   help="explicit authorizer recorded in the cancellation "
                        "decision row (明确授权者)")
    p.add_argument("--reason", required=True,
                   help="single-line cancellation reason (decisions "
                        "recorded need a reason)")
    p.add_argument("--expect-status", default=None,
                   choices=list(CANCELLABLE_STATUSES),
                   help="CAS: refuse unless the derived status still "
                        "equals this (revision_conflict returns the "
                        "observed status)")
    p.add_argument("--lock-timeout", type=float, default=10.0)
    p.add_argument("--writer-timeout", type=float, default=30.0,
                   help="per-writer-CLI lock timeout (the DEC/locks legs "
                        "pass it through; a timed-out leg is pending — "
                        "re-run converges)")

    p = sub.add_parser("reopen", help="FEAT-063 重开: mint a linked "
                       "successor attempt for a TERMINAL closure "
                       "(cancelled/finalized) — original records are "
                       "never erased (append-only lineage; single-"
                       "successor; bind the successor with run "
                       "--reopen-of)")
    p.add_argument("--closure-id", required=True)
    p.add_argument("--authorized-by", required=True,
                   help="explicit authorizer recorded in the reopen "
                        "lineage event (明确授权者)")
    p.add_argument("--reason", required=True,
                   help="single-line reopen reason")
    p.add_argument("--lock-timeout", type=float, default=10.0)

    p = sub.add_parser("takeover", help="FEAT-063 异常接管: promote the "
                       "task's execution generation and bind a new holder "
                       "closure (write-side fencing — the prior holder's "
                       "writes are refused afterwards; heartbeat timeout "
                       "is NEVER a stop proof, explicit authorization "
                       "required)")
    p.add_argument("--task", required=True)
    p.add_argument("--new-holder", required=True, dest="new_holder",
                   help="closure id of the new executor (fencing-token "
                        "holder)")
    p.add_argument("--authorized-by", required=True,
                   help="explicit human authorizer recorded in the "
                        "generation record (明确授权者 — heartbeat "
                        "timeout is not a stop proof)")
    p.add_argument("--reason", required=True,
                   help="single-line takeover reason (the stronger "
                        "evidence / human authorization behind the "
                        "takeover judgment)")
    p.add_argument("--lock-timeout", type=float, default=10.0)
    return parser


def _parse_inputs(pairs: List[str]) -> Dict[str, str]:
    inputs: Dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError("--input {0!r}: expected K=V".format(pair))
        key, _, value = pair.partition("=")
        key, value = key.strip(), value
        if not key:
            raise ValueError("--input {0!r}: empty key".format(pair))
        inputs[key] = value
    return inputs


_BUILTIN_CHAINS: Dict[str, Dict[str, Any]] = {
    "standard-ticket-closure": STANDARD_TICKET_CLOSURE,
    "release-window-bootstrap": RELEASE_WINDOW_BOOTSTRAP,
}
"""Closed built-in chain registry (``--chain``); a --spec file overrides."""


def _builtin_spec(chain_id: str) -> Dict[str, Any]:
    template = _BUILTIN_CHAINS.get(chain_id)
    if template is None:
        raise ValueError(
            "unknown built-in chain {0!r} (available: {1!r})".format(
                chain_id, sorted(_BUILTIN_CHAINS)))
    return json.loads(json.dumps(template))  # deep copy


def cmd_run(args: argparse.Namespace) -> int:
    _configure_stdio()
    CLOSURE_SCHEMA_WINDOW.require_supported("closure_chain", 
                                            args.schema_version)
    if args.spec:
        spec_data = json.loads(
            Path(args.spec).read_text(encoding="utf-8"))
    else:
        spec_data = _builtin_spec(args.chain)
    spec = parse_chain_spec(spec_data)
    try:
        payload = run_chain(
            spec, root=Path(args.project_root), task=args.task,
            inputs=_parse_inputs(args.input),
            closure_id=args.closure_id, dry_run=args.dry_run,
            world_check=args.world_check, lock_timeout=args.lock_timeout,
            reopen_of=args.reopen_of)
    except LockContention as exc:
        payload = {"error": True, "code": "lock_contention",
                   "disposition": "retryable", "detail": str(exc)}
    except ExecutionFenced as exc:
        # FEAT-063: a stale execution generation is a structured
        # revision_conflict refusal (never a bare traceback)
        payload = exc.payload
    except ValueError as exc:
        payload = {"error": True, "code": "schema_violation",
                   "disposition": "validation", "detail": str(exc)}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload.get("error"):
        return 3 if payload.get("disposition") == "retryable" else 2
    if payload.get("status") in ("blocked", "awaiting-world-check"):
        # a halted chain is a structured non-zero stop (the caller branches
        # on the status/code, never on prose); retryable contention is 3
        return 2
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    _configure_stdio()
    try:
        payload = closure_status(Path(args.project_root), args.closure_id)
    except ValueError as exc:
        payload = {"error": True, "code": "schema_violation",
                   "disposition": "validation", "detail": str(exc)}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 2 if payload.get("error") else 0


def cmd_finalize(args: argparse.Namespace) -> int:
    _configure_stdio()
    try:
        payload = finalize_closure(Path(args.project_root), args.closure_id,
                                   args.commit_sha)
    except LockContention as exc:
        # review-FEAT-062-R0 F-2: a cancel holding the run lock (writer
        # legs in flight) exhausts finalize's lock budget — structured
        # retryable refusal, never a bare traceback.
        payload = {"closure_id": args.closure_id, "error": True,
                   "code": "lock_contention", "disposition": "retryable",
                   "detail": str(exc)}
    except ValueError as exc:
        # review-FEAT-062-R0 F-3: a malformed closure id is a closed-code
        # validation refusal, same convention as cmd_run.
        payload = {"closure_id": args.closure_id, "error": True,
                   "code": "schema_violation", "disposition": "validation",
                   "detail": str(exc)}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload.get("error"):
        return 3 if payload.get("disposition") == "retryable" else 2
    return 0


def cmd_cancel(args: argparse.Namespace) -> int:
    _configure_stdio()
    try:
        payload = cancel_closure(
            Path(args.project_root), args.closure_id,
            authorized_by=args.authorized_by, reason=args.reason,
            expected_status=args.expect_status,
            lock_timeout=args.lock_timeout,
            writer_timeout=args.writer_timeout)
    except ValueError as exc:
        # review-FEAT-062-R0 F-3: a malformed closure id is a closed-code
        # validation refusal (LockContention is already structured inside
        # cancel_closure), same convention as cmd_run.
        payload = {"closure_id": args.closure_id, "error": True,
                   "code": "schema_violation", "disposition": "validation",
                   "detail": str(exc)}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload.get("error"):
        return 3 if payload.get("disposition") == "retryable" else 2
    if not (payload.get("reconciliation") or {}).get("consistent", False):
        # terminal recorded, a convergence leg is pending — re-run the
        # SAME command (deterministic operation ids make the retry a
        # writer replay/apply that converges)
        return 3
    return 0


def cmd_reopen(args: argparse.Namespace) -> int:
    _configure_stdio()
    try:
        payload = reopen_closure(
            Path(args.project_root), args.closure_id,
            authorized_by=args.authorized_by, reason=args.reason,
            lock_timeout=args.lock_timeout)
    except ValueError as exc:
        # malformed closure id → closed-code validation refusal, same
        # convention as cmd_cancel (FEAT-062-R0 F-3 class)
        payload = {"closure_id": args.closure_id, "error": True,
                   "code": "schema_violation", "disposition": "validation",
                   "detail": str(exc)}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload.get("error"):
        return 3 if payload.get("disposition") == "retryable" else 2
    return 0


def cmd_takeover(args: argparse.Namespace) -> int:
    _configure_stdio()
    try:
        payload = takeover_execution(
            Path(args.project_root), args.task, args.new_holder,
            authorized_by=args.authorized_by, reason=args.reason,
            lock_timeout=args.lock_timeout)
    except ValueError as exc:
        # malformed --new-holder closure id → closed-code validation
        # refusal, same convention as cmd_cancel
        payload = {"error": True, "code": "schema_violation",
                   "disposition": "validation", "detail": str(exc)}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload.get("error"):
        return 3 if payload.get("disposition") == "retryable" else 2
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {"run": cmd_run, "status": cmd_status,
                "finalize": cmd_finalize, "cancel": cmd_cancel,
                "reopen": cmd_reopen, "takeover": cmd_takeover}
    return handlers[args.command](args)


if __name__ == "__main__":  # pragma: no cover - direct invocation seam
    sys.exit(main())
