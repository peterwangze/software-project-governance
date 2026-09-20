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
(``post-step-effect:<step_id>``, ``post-finalize-verify``).  When set (by
the chaos test's parent controller, never by the production CLI), the child
process writes a handshake marker file and pauses until the parent kills
it (Popen.kill) or releases it.  No CLI flag exposes this surface.

Registered gap (honest disclosure, ticket FEAT-056 design point 5): the
governance_store has NO ``locks-release`` command; the standard chain's
lock step is carried by ``locks-amend`` TTL shrink (every lock owned by the
task shrunk to a small ceiling).  Actual lock-entry removal/removal of
active_tasks remains a registered gap for a later slice — reported in the
chain output, never silently assumed.

Single-flight assumption (FEAT-056 R0 P3-4 disclosure): the per-closure
run lock makes ONE closure id safe against concurrent resumes, but it does
NOT arbitrate two DIFFERENT closures driving the SAME task in parallel —
both would legitimately flip the same task row / append their own evidence
rows (evolution §6② registered 0.87 open question).  Until that护栏
exists, operators MUST run one closure per task at a time (单 closure
单飞); the chain neither detects nor prevents the parallel-siblings shape.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
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
    "CLOSURE_EVENT_LOG_FILENAME",
    "CLOSURE_ID_PATTERN",
    "CLOSURE_SCHEMA_VERSION",
    "CLOSURE_TEST_FAULT_ENV",
    "PROBE_KINDS",
    "STEP_KINDS",
    "STANDARD_TICKET_CLOSURE",
    "WRITER_ID",
    "finalize_closure",
    "main",
    "new_closure_id",
    "require_closure_id",
    "run_chain",
    "step_operation_id",
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
    ``{kind, satisfied, detail, anchor}``.  Every branch is READ-ONLY."""
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
    """Extract a structured refusal from a writer CLI's JSON payload."""
    try:
        payload = json.loads(stdout_text.strip() or "{}")
    except ValueError:
        return {"code": "manual_intervention",
                "detail": "writer exit {0} with non-JSON output".format(
                    exit_code)}
    result = payload.get("result") if isinstance(payload, dict) else None
    refusal = payload.get("refusal") if isinstance(payload, dict) else None
    source = refusal or result or {}
    code = source.get("code") or (
        RESULT_OK if exit_code == 0 else "manual_intervention")
    disposition = ERROR_CODE_DISPOSITIONS.get(code, "manual")
    return {"code": code, "disposition": disposition,
            "detail": source.get("detail") or source.get("error") or "",
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


def _summary_payload(spec: ChainSpec, closure_id: str, task: str,
                     inputs: Dict[str, str]) -> Dict[str, Any]:
    """The ready-to-commit endpoint payload (round-2 §2: 链终点输出
    ready-to-commit 摘要 + message 建议; git 操作不在链内)."""
    subject = inputs.get("commit_subject") or (
        "{0}: review 通过收口（closure-chain 标准链）".format(task))
    message = (
        "{0}\n\n"
        "Closure: {1}\n"
        "Chain: {2} (FEAT-056 standard ticket closure)\n"
        "Task row flipped via task-row-update; evidence appended via\n"
        "evidence-append; dispatch-lock TTLs shrunk via locks-amend\n"
        "(locks-release remains a registered gap — TTL shrink is the\n"
        "governed stand-in, disclosed not silent).\n"
        "Completion gate: closure-chain --finalize --closure-id {1}\n"
        "--commit-sha <sha-of-this-commit>".format(
            subject, closure_id, spec.chain_id))
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
        ],
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
              lock_timeout: float = 10.0) -> Dict[str, Any]:
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
       probes + writer dry-runs prove every step resolvable.
    """
    root = Path(root)
    if not isinstance(task, str) or not task.strip():
        raise ValueError("run_chain: task id required")
    task = task.strip()
    closure_id = require_closure_id(
        "run_chain: closure_id", closure_id or new_closure_id())
    merged_inputs: Dict[str, str] = dict(_REQUIRED_INPUT_DEFAULTS)
    for key, value in (inputs or {}).items():
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
    events, problems = _load_closure_events(log_path, closure_id)
    started = next((e for e in events
                    if e.get("event_type") == "closure_started"), None)
    resumed = started is not None
    if resumed and (started.get("payload") or {}).get("inputs_digest") \
            not in (None, digest):
        raise ValueError(
            "closure {0}: resume inputs digest mismatch — this closure was "
            "started with different inputs (closure identity is "
            "immutable; start a new closure instead)".format(closure_id))
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
        events, problems = _load_closure_events(log_path, closure_id)
        if not any(e.get("event_type") == "closure_started" for e in events):
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
    ready = any(e.get("event_type") == "closure_ready" for e in events)
    unknown_steps = [s for s, v in step_state.items() if v == "unknown"]
    failed_steps = [s for s, v in step_state.items() if v == "failed"]
    if finalized:
        status = "finalized"
    elif failed_steps:
        status = "blocked"
    elif unknown_steps:
        status = "awaiting-world-check"
    elif ready:
        status = "ready"
    else:
        status = "running"
    return {
        "closure_id": closure_id,
        "found": True,
        "status": status,
        "task": (started or {}).get("payload", {}).get("task"),
        "chain_id": (started or {}).get("payload", {}).get("chain_id"),
        "started_at": (started or {}).get("timestamp"),
        "steps": step_state,
        "event_count": len(events),
        "journal": str(log_path),
        "journal_problems": problems,
    }


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
                    "the chain")
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


def _builtin_spec(chain_id: str) -> Dict[str, Any]:
    data = json.loads(json.dumps(STANDARD_TICKET_CLOSURE))  # deep copy
    if data.get("chain_id") != chain_id:
        raise ValueError(
            "unknown built-in chain {0!r} (available: {1!r})".format(
                chain_id, data.get("chain_id")))
    return data


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
            world_check=args.world_check, lock_timeout=args.lock_timeout)
    except LockContention as exc:
        payload = {"error": True, "code": "lock_contention",
                   "disposition": "retryable", "detail": str(exc)}
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
    payload = finalize_closure(Path(args.project_root), args.closure_id,
                               args.commit_sha)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 2 if payload.get("error") else 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {"run": cmd_run, "status": cmd_status,
                "finalize": cmd_finalize}
    return handlers[args.command](args)


if __name__ == "__main__":  # pragma: no cover - direct invocation seam
    sys.exit(main())
