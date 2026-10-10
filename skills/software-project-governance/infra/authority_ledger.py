#!/usr/bin/env python3
"""FEAT-093 — the authority ledger: task identity contract + event log.

0.98「可信有界执行内核」首票 (DEC-330).  The RPG long-haul session measured
the failure this module closes (report §3.2, ``docs/requirements/
analysis-rpg-longhaul-capability-session-f3f46901-0.97.0.md``):

  * 5 groups of FEAT ids carrying TWO DIFFERENT task semantics under one id
    (same id, silently re-meaning across sessions);
  * 22 zombie「未开始」rows — plan rows whose execution reality had moved on
    with zero reconciliation;
  * plan/execution dual tracks with NO reconciliation between them.

Design (execution-packet FEAT-093 assumption_record — binding):

  * **Physical carrier** — one JSONL append-only event log
    (``.governance/authority-ledger/events.jsonl``) plus a REBUILDABLE
    snapshot cache (``.governance/authority-ledger/snapshot.json``).  No
    external database dependency.
  * **Identity contract (写入侧执法)** — a task id's semantic anchor (the
    declared title of its ``事项`` cell) is registered at first write.  A
    later write of the SAME id with a DIFFERENT anchor is REFUSED and the
    attempt is appended as an ``identity_conflict_rejected`` audit event.
    The whole batch is checked against a simulated fold (intra-batch
    included, R0 P1-1); state events and supersedes referencing
    UNREGISTERED identities are likewise refused (no orphan events, no
    phantom lineage).  Changing semantics requires a NEW task (or a
    versioned id) plus a ``task_superseded`` event recording the
    replacement relationship — 原 ID 静默换义 is structurally impossible
    through this writer.
  * **Transactional writer** — a batch of events is validated ENTIRELY
    before any byte is appended (validation atomicity), then appended in
    one single sequential write with a seq + sha256 chain (integrity), then
    the snapshot cache is atomically refreshed.  A torn tail (crash
    mid-append) is detected on load and the writer refuses further appends
    until adjudicated (fail-closed, never silently folded).
  * **plan-tracker as projection** — the hot zone (task tables + Gate
    summary + risk rows) is DEMOTED to a derivable projection: one command
    rebuilds the projection from the ledger and proves the rebuild with an
    item-by-item counts comparison (tasks / gates / risks, zero loss).
    Adoption is progressive behind a session/project switch (dual-write
    first, read-side switch later) — default OFF keeps the legacy path
    byte-identical (``switch_state``).

Boundary discipline (same as task_row_update / governance_store /
bootstrap_aggregate — the governance_cost pattern): this module is
stdlib-only at import time, MUST NOT import ``verify_workflow`` (ArchGuard
R2 — the engine only wires dispatch), and reaches the proven table-parse
calibers by FUNCTION-LOCAL import of the engine-free peer leaf
``bootstrap_aggregate`` (``_iter_positional_tables`` /
``_gate_bucket`` / risk bucketing) — importing the live implementation
instead of mirroring it is the anti-drift choice (the R0 P0-1 lesson:
review-only mirrors demonstrably drift).

Public entry points::

    main(argv)                 self-contained CLI (``python authority_ledger.py``)
    cmd_authority_ledger(args) engine dispatch face (Namespace, no re-parse)
    add_arguments(parser)      module-owned option fact source
    LedgerWriter               the transactional writer
    migrate(...)               historical-data migration (dry-run first)
    rebuild_projection(...)    ledger → hot-zone projection rebuild + counts proof
    switch_state(...)          the progressive-adoption switch resolver

Usage::

    python <plugin_home>/infra/verify_workflow.py authority-ledger status
    python <plugin_home>/infra/verify_workflow.py authority-ledger migrate --dry-run
    python <plugin_home>/infra/verify_workflow.py authority-ledger rebuild [--write]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

LEDGER_SCHEMA = "authority-ledger/1"
TASK_ID = "FEAT-093"
WRITER_ID = "authority_ledger/1"

#: Physical carrier (execution-packet assumption_record: JSONL event log +
#: rebuildable snapshot under ``.governance/``; no external database).
LEDGER_DIRNAME = "authority-ledger"
EVENTS_FILENAME = "events.jsonl"
SNAPSHOT_FILENAME = "snapshot.json"

#: The hash-chain genesis (prev_hash of the first event).
GENESIS_HASH = "0" * 64

#: Closed event-kind vocabulary.  Task identity/state + review/recheck/
#: goal-budget core-state families (schema coverage per acceptance ①) +
#: the audit kinds (migration-time dual semantics, write-side rejection,
#: migration and rebuild bookkeeping).
EVENT_KINDS = frozenset((
    # task core state
    "task_registered",
    "task_state_changed",
    "task_superseded",
    # review / recheck-obligation / goal-budget core state (schema level;
    # deep review binding is FEAT-094's boundary, not this ticket's)
    "review_recorded",
    "recheck_obligation_registered",
    "recheck_obligation_cleared",
    "goal_budget_recorded",
    # gate / risk hot-zone state
    "gate_recorded",
    "gate_state_changed",
    "risk_recorded",
    "risk_state_changed",
    # audit trail
    "historical_identity_conflict",   # migration-time dual semantics, flagged
    "identity_conflict_rejected",     # write-side rejection (attempt kept)
    "historical_migrated",            # one migration batch summary
    "projection_rebuilt",             # one rebuild outcome summary
))

#: Required payload fields per kind (closed schema; extra fields ride along
#: untouched — the required set is the machine-checkable minimum).
REQUIRED_FIELDS = {
    "task_registered": ("task_id", "semantic_anchor", "anchor_fingerprint"),
    "task_state_changed": ("task_id", "from_state", "to_state"),
    "task_superseded": ("old_task_id", "new_task_id", "reason"),
    "review_recorded": ("review_id", "task_id", "verdict"),
    "recheck_obligation_registered": ("task_id",),
    "recheck_obligation_cleared": ("task_id",),
    "goal_budget_recorded": ("goal_id",),
    "gate_recorded": ("gate_id", "status"),
    "gate_state_changed": ("gate_id", "from_status", "to_status"),
    "risk_recorded": ("risk_id", "status"),
    "risk_state_changed": ("risk_id", "from_status", "to_status"),
    "historical_identity_conflict": ("task_id", "existing_anchor",
                                     "attempted_anchor"),
    "identity_conflict_rejected": ("task_id", "existing_anchor",
                                   "attempted_anchor"),
    "historical_migrated": ("source", "counts"),
    "projection_rebuilt": ("counts",),
}

#: ── the progressive-adoption switch (FEAT-093 assumption_record: 写路径
#: 先双写后读切换；default OFF = legacy path byte-identical) ─────────────
SWITCH_ENV = "GOVERNANCE_AUTHORITY_LEDGER"
SWITCH_PLAN_TRACKER_KEY = "authority_ledger"
CONFIG_SECTION_PREFIX = "## 项目配置"
SWITCH_SOURCE_ENV = "env"
SWITCH_SOURCE_PLAN_TRACKER = "plan-tracker"
SWITCH_SOURCE_DEFAULT = "default"
SWITCH_STATE_ON = "on"
SWITCH_STATE_OFF = "off"
SWITCH_STATE_INVALID = "invalid"
SWITCH_ON_TOKENS = frozenset(("1", "true", "yes", "on", "projection"))
SWITCH_OFF_TOKENS = frozenset(("0", "false", "no", "off", "legacy"))
SWITCH_DEFAULT_STATE = SWITCH_STATE_OFF
SWITCH_INVALID_VALUE_LIMIT = 32

#: Task-id shape (PREFIX-NNN family — task_priority's ``_ID_TOKEN`` caliber).
_TASK_ID_RE = re.compile(r"^[A-Z]+-\d+$")

#: The semantic anchor: the DECLARED TITLE of the 事项 cell.  Live shapes
#: wrap the title in the first ``**...**`` bold span; rows without bold use
#: the cell's leading clause.  The anchor deliberately EXCLUDES status
#: decorations, appended narrative (post-``——`` detail) and provenance
#: suffixes — those evolve legitimately without changing task semantics.
_BOLD_SPAN_RE = re.compile(r"\*\*(.+?)\*\*")
_ANCHOR_FALLBACK_CUTS = ("——", "：", ":", "；", ";")
_ANCHOR_CLIP = 120

#: Status snapshot clip (raw cells are paragraph-sized; the ledger stores
#: the bucket + a clipped witness, never the whole narrative).
_STATUS_CLIP = 80


class LedgerError(RuntimeError):
    """Base refusal/error (fail-closed, structured)."""


class LedgerIntegrityError(LedgerError):
    """The event log's seq/hash chain is broken — appends are refused."""


# ── identity primitives ─────────────────────────────────────────────────────


def semantic_anchor(subject_cell: str) -> str:
    """Extract the semantic anchor (declared title) from a 事项 cell.

    First ``**bold**`` span when present; otherwise the leading clause cut
    at the first em-dash/colon/semicolon, clipped to ``_ANCHOR_CLIP``.
    Whitespace is normalized away — the anchor is a semantic key, not a
    byte form.
    """
    text = (subject_cell or "").strip()
    if not text:
        return ""
    m = _BOLD_SPAN_RE.search(text)
    if m:
        anchor = m.group(1).strip()
    else:
        anchor = text
        for cut in _ANCHOR_FALLBACK_CUTS:
            pos = anchor.find(cut)
            if pos > 0:
                anchor = anchor[:pos]
        anchor = anchor.strip()
    if len(anchor) > _ANCHOR_CLIP:
        anchor = anchor[:_ANCHOR_CLIP]
    return anchor


def anchor_fingerprint(anchor: str) -> str:
    """Stable fingerprint of a semantic anchor (whitespace-insensitive)."""
    normalized = re.sub(r"\s+", "", anchor or "")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _clip(text, limit=_STATUS_CLIP):
    value = str(text or "")
    return value if len(value) <= limit else value[:limit] + "…"


def _now_iso(now_fn=None):
    fn = now_fn or (lambda: datetime.now(timezone.utc))
    return fn().isoformat()


def new_event_id() -> str:
    return "evt-" + uuid.uuid4().hex


def new_transaction_id() -> str:
    return "txn-" + uuid.uuid4().hex


# ── physical carrier ────────────────────────────────────────────────────────


def ledger_paths(governance_dir):
    """(ledger_dir, events_path, snapshot_path) for a governance dir."""
    base = Path(governance_dir)
    return (base / LEDGER_DIRNAME,
            base / LEDGER_DIRNAME / EVENTS_FILENAME,
            base / LEDGER_DIRNAME / SNAPSHOT_FILENAME)


def _canonical_event(event: dict) -> str:
    return json.dumps(event, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def _event_hash(event: dict) -> str:
    """Hash of the event's canonical form EXCLUDING the ``hash`` field
    itself (build and verify share this one definition — a re-read event
    hashes identically to the built one)."""
    body = {key: value for key, value in event.items() if key != "hash"}
    return hashlib.sha256(
        _canonical_event(body).encode("utf-8")).hexdigest()


def _read_events_raw(events_path: Path):
    """(events, integrity) — validate JSON, seq monotonicity and the hash
    chain line by line.  A torn/corrupt tail is REPORTED (fail-closed for
    writes), never silently folded."""
    integrity = {"ok": True, "problems": [], "lines": 0, "last_seq": 0,
                 "last_event_hash": GENESIS_HASH}
    events = []
    if not events_path.is_file():
        return events, integrity
    text = events_path.read_text(encoding="utf-8", errors="strict")
    expected_seq = 1
    prev_hash = GENESIS_HASH
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        integrity["lines"] += 1
        try:
            event = json.loads(line)
        except ValueError as exc:
            integrity["ok"] = False
            integrity["problems"].append(
                "line {0}: not JSON ({1})".format(lineno, exc))
            break
        seq = event.get("seq")
        if seq != expected_seq:
            integrity["ok"] = False
            integrity["problems"].append(
                "line {0}: seq {1!r} != expected {2} (torn or reordered "
                "tail)".format(lineno, seq, expected_seq))
            break
        if event.get("prev_hash") != prev_hash:
            integrity["ok"] = False
            integrity["problems"].append(
                "line {0}: prev_hash breaks the chain".format(lineno))
            break
        if _event_hash(event) != event.get("hash"):
            integrity["ok"] = False
            integrity["problems"].append(
                "line {0}: hash mismatch (content rewritten?)".format(lineno))
            break
        events.append(event)
        expected_seq += 1
        prev_hash = event["hash"]
        integrity["last_seq"] = event["seq"]
        integrity["last_event_hash"] = event["hash"]
    return events, integrity


def _atomic_write(path: Path, content: str) -> None:
    """Same-directory temp + ``os.replace`` (UTF-8, no BOM, LF)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp-{0}".format(uuid.uuid4().hex[:8]))
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


# ── state fold (the rebuildable projection core) ────────────────────────────


#: Terminal TASK_STATES the writer renders with the ✅ marker family
#: (``✅ 完成`` / ``✅ committed`` — task_row_update.STATE_CANONICAL_MARKERS).
_TERMINAL_TASK_STATES = frozenset(("completed", "committed"))


def _task_completed_bucket(status_cell: str) -> str:
    """'completed' when the cell carries ✅ (task_priority's
    ``_status_is_completed`` caliber — disclosed mirror, the predicate is
    private on the peer leaf).  Applied to TABLE cells only."""
    return "completed" if "✅" in (status_cell or "") else "active"


def _task_state_bucket(state: str) -> str:
    """Bucket for a bare TASK_STATE enum name (the dual-write mirror's
    channel): terminal states bucket completed (the writer renders them
    with the ✅ marker), everything else active."""
    return "completed" if (state or "").strip().lower() in \
        _TERMINAL_TASK_STATES or "✅" in (state or "") else "active"


def fold_state(events):
    """Fold the event log into the authoritative state projection.

    Returns a dict with ``tasks`` / ``gates`` / ``risks`` maps,
    ``reviews`` / ``open_recheck_obligations`` / ``goal_budgets`` lists and
    ``counts`` (the canonical facets the zero-loss comparison consumes).
    """
    tasks = {}
    gates = {}
    risks = {}
    reviews = []
    recheck_open = {}
    goal_budgets = []
    conflict_keys = set()
    counts = {
        "tasks": {"registered": 0, "identity_conflict_rows": 0,
                  "identity_conflict_ids": set(), "superseded": 0},
        "gates": {"recorded": 0, "passed": 0, "pending": 0, "failed": 0,
                  "other": 0},
        "risks": {"recorded": 0, "open": 0, "closed": 0, "unknown": 0},
    }
    for event in events:
        kind = event.get("kind")
        payload = event.get("payload") or {}
        if kind == "task_registered":
            tid = payload["task_id"]
            if tid not in tasks:
                counts["tasks"]["registered"] += 1
            tasks[tid] = {
                "semantic_anchor": payload.get("semantic_anchor", ""),
                "anchor_fingerprint": payload.get("anchor_fingerprint", ""),
                "priority": payload.get("priority", ""),
                "target_version": payload.get("target_version", ""),
                "status": payload.get("status", ""),
                "status_bucket": payload.get("status_bucket", ""),
                "superseded_by": None,
                "registered_at": event.get("timestamp"),
                "registered_seq": event.get("seq"),
            }
        elif kind == "task_state_changed":
            tid = payload["task_id"]
            if tid in tasks:
                tasks[tid]["status"] = payload.get("to_state", "")
                tasks[tid]["status_bucket"] = payload.get(
                    "to_bucket", _task_state_bucket(
                        payload.get("to_state", "")))
        elif kind == "task_superseded":
            old = payload["old_task_id"]
            new = payload["new_task_id"]
            if old in tasks:
                tasks[old]["superseded_by"] = new
                counts["tasks"]["superseded"] += 1
            tasks[new] = {
                "semantic_anchor": payload.get("new_anchor", ""),
                "anchor_fingerprint": anchor_fingerprint(
                    payload.get("new_anchor", "")),
                "priority": payload.get("priority", ""),
                "target_version": payload.get("target_version", ""),
                "status": payload.get("status", ""),
                "status_bucket": payload.get("status_bucket", ""),
                "superseded_by": None,
                "registered_at": event.get("timestamp"),
                "registered_seq": event.get("seq"),
                "supersedes": old,
            }
            counts["tasks"]["registered"] += 1
        elif kind == "gate_recorded":
            gid = payload["gate_id"]
            bucket = _gate_bucket_of(payload.get("status", ""))
            if gid not in gates:
                counts["gates"]["recorded"] += 1
                if bucket in ("passed", "pending", "failed", "other"):
                    counts["gates"][bucket] += 1
            gates[gid] = {"status": payload.get("status", ""),
                          "bucket": bucket}
        elif kind == "gate_state_changed":
            gid = payload["gate_id"]
            if gid in gates:
                gates[gid]["status"] = payload.get("to_status", "")
                gates[gid]["bucket"] = _gate_bucket_of(
                    payload.get("to_status", ""))
        elif kind == "risk_recorded":
            rid = payload["risk_id"]
            bucket = payload.get("bucket", "unknown")
            if rid not in risks:
                counts["risks"]["recorded"] += 1
                if bucket in ("open", "closed", "unknown"):
                    counts["risks"][bucket] += 1
            risks[rid] = {"status": payload.get("status", ""),
                          "bucket": bucket}
        elif kind == "risk_state_changed":
            rid = payload["risk_id"]
            if rid in risks:
                risks[rid]["status"] = payload.get("to_status", "")
                risks[rid]["bucket"] = payload.get("to_bucket", "unknown")
        elif kind == "review_recorded":
            reviews.append(dict(payload,
                                _seq=event.get("seq")))
        elif kind == "recheck_obligation_registered":
            recheck_open[payload["task_id"]] = dict(
                payload, _seq=event.get("seq"))
        elif kind == "recheck_obligation_cleared":
            recheck_open.pop(payload["task_id"], None)
        elif kind == "goal_budget_recorded":
            goal_budgets.append(dict(payload, _seq=event.get("seq")))
        elif kind in ("historical_identity_conflict",
                      "identity_conflict_rejected"):
            counts["tasks"]["identity_conflict_rows"] += 1
            counts["tasks"]["identity_conflict_ids"].add(
                payload.get("task_id"))
            if kind == "historical_identity_conflict":
                # state-level dedup key — a migration re-run must not
                # re-flag an already-flagged historical conflict (write-
                # side REJECTIONS stay attempt-level: every refused write
                # is its own auditable fact).
                conflict_keys.add("{0}:{1}".format(
                    payload.get("task_id"),
                    payload.get("attempted_fingerprint",
                                anchor_fingerprint(
                                    payload.get("attempted_anchor", "")))))
    counts["tasks"]["identity_conflict_ids"] = sorted(
        tid for tid in counts["tasks"]["identity_conflict_ids"] if tid)
    return {
        "tasks": tasks,
        "gates": gates,
        "risks": risks,
        "reviews": reviews,
        "open_recheck_obligations": sorted(
            recheck_open.values(), key=lambda item: item.get("_seq", 0)),
        "goal_budgets": goal_budgets,
        "conflict_keys": conflict_keys,
        "counts": counts,
    }


def _gate_bucket_of(status_cell: str) -> str:
    """Gate bucket via the peer leaf's live caliber (function-local import
    — anti-drift; the engine-free boundary keeps this import off the
    cold-load face)."""
    from bootstrap_aggregate import _gate_bucket
    return _gate_bucket(status_cell)


# ── the transactional writer ────────────────────────────────────────────────


class LedgerWriter:
    """The single transactional write path into the authority ledger.

    Transaction semantics: a batch of events is validated ENTIRELY against
    the closed schema and the identity contract BEFORE any byte is
    appended; only then are all lines written in one sequential append and
    the snapshot cache atomically refreshed.  Rejections append NOTHING of
    the refused batch — only their own audit event
    (``identity_conflict_rejected``) when the refusal is an identity
    conflict (the attempt itself is the auditable fact).

    Concurrency posture (disclosed): appends are serialized per process by
    the seq+hash chain construction — two concurrent writers produce a
    chain break that the NEXT load detects and refuses (fail-closed
    disclosure, never silent loss).  True cross-process write isolation is
    FEAT-096's boundary, not this ticket's.
    """

    def __init__(self, governance_dir, *, actor=WRITER_ID, now_fn=None):
        self.governance_dir = Path(governance_dir)
        self.ledger_dir, self.events_path, self.snapshot_path = \
            ledger_paths(self.governance_dir)
        self.actor = actor
        self.now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self.events, self.integrity = _read_events_raw(self.events_path)
        self.state = fold_state(self.events)

    # ── integrity gate ──────────────────────────────────────────────────

    def _require_integrity(self):
        if not self.integrity["ok"]:
            raise LedgerIntegrityError(
                "event log integrity broken ({0}) — appends refused until "
                "adjudicated: {1}".format(
                    self.events_path,
                    "; ".join(self.integrity["problems"][:3])))

    # ── transaction machinery ───────────────────────────────────────────

    def _build_event(self, kind, payload, transaction_id, seq, prev_hash):
        event = {
            "seq": seq,
            "event_id": new_event_id(),
            "kind": kind,
            "transaction_id": transaction_id,
            "actor": self.actor,
            "timestamp": _now_iso(self.now_fn),
            "payload": payload,
            "prev_hash": prev_hash,
        }
        event["hash"] = _event_hash(event)
        return event

    @staticmethod
    def _validate_payload(kind, payload):
        if kind not in EVENT_KINDS:
            raise LedgerError(
                "unknown event kind {0!r} (closed vocabulary)".format(kind))
        if not isinstance(payload, dict):
            raise LedgerError(
                "payload for {0!r} must be a dict".format(kind))
        missing = [field for field in REQUIRED_FIELDS[kind]
                   if not payload.get(field)]
        if missing:
            raise LedgerError(
                "payload for {0!r} missing required field(s): {1}".format(
                    kind, ", ".join(missing)))

    def transact(self, batch):
        """Validate + append a batch of ``(kind, payload)`` pairs atomically
        (validation atomicity; one sequential append; snapshot refresh).

        The identity contract covers the WHOLE batch (R0 P1-1): the batch
        is validated against a SIMULATED FOLD of (current state + the
        batch itself), so events later in the batch see what earlier
        events in the SAME batch established.  An anchor conflict refuses
        the whole batch AND lands one ``identity_conflict_rejected`` audit
        event (the attempt is the auditable fact); phantom supersedes and
        orphan state events are refused at validation time.
        """
        self._require_integrity()
        if not isinstance(batch, (list, tuple)) or not batch:
            raise LedgerError("a transaction needs a non-empty event batch")
        for kind, payload in batch:
            self._validate_payload(kind, payload)
        # identity-contract pre-check over the WHOLE batch (simulated
        # fold): a violation refuses the ENTIRE batch before any byte is
        # appended.
        self._check_batch_identity(batch)
        transaction_id = new_transaction_id()
        seq = self.integrity["last_seq"]
        prev_hash = self.integrity["last_event_hash"]
        built = []
        for kind, payload in batch:
            seq += 1
            event = self._build_event(kind, payload, transaction_id,
                                      seq, prev_hash)
            prev_hash = event["hash"]
            built.append(event)
        blob = "".join(_canonical_event(event) + "\n" for event in built)
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        with open(self.events_path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(blob)
            fh.flush()
            os.fsync(fh.fileno())
        self.events.extend(built)
        self.integrity["last_seq"] = seq
        self.integrity["last_event_hash"] = prev_hash
        self.integrity["lines"] += len(built)
        # R0 P3-8 (disclosed posture): a FULL re-fold per transaction is
        # O(n)/write (O(n²) across a whole migration); measured well
        # inside budget at the guarded scale (rebuild <2s / txn <50ms —
        # the perf-guard test).  Incremental folding is deferred until
        # scale demands it, not before.
        self.state = fold_state(self.events)
        self._write_snapshot()
        return {
            "status": "recorded",
            "transaction_id": transaction_id,
            "event_count": len(built),
            "last_seq": seq,
            "last_event_hash": prev_hash,
        }

    def _write_snapshot(self):
        snapshot = build_snapshot(self.state, self.events, self.integrity)
        _atomic_write(self.snapshot_path, json.dumps(
            snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        return snapshot

    # ── identity contract ───────────────────────────────────────────────

    def _check_batch_identity(self, batch):
        """Identity-contract validation over the WHOLE batch (R0 P1-1).

        The check simulates the fold: it starts from the writer's current
        task identities and applies the batch's registrations and
        supersessions IN ORDER, so intra-batch events are validated
        against what earlier events in the SAME batch established — not
        just the pre-batch folded state.  Violations:

        * same id + different anchor (vs the folded state OR intra-batch)
          ⇒ the whole batch is refused and ONE ``identity_conflict_rejected``
          audit event lands (the attempt is the auditable fact — the same
          refusal semantics :meth:`record_task` documents);
        * ``task_superseded`` with an unregistered ``old_task_id`` (phantom
          lineage) or an already-registered ``new_task_id`` (folded state
          or earlier in this batch) ⇒ refused;
        * ``task_state_changed`` for an unregistered id (the orphan-state
          class: accepted-then-silently-dropped, R0 P2-1) ⇒ refused.
        """
        known = {
            tid: (task["anchor_fingerprint"], task["semantic_anchor"])
            for tid, task in self.state["tasks"].items()}
        for kind, payload in batch:
            if kind == "task_registered":
                tid = payload["task_id"]
                entry = known.get(tid)
                if entry is not None:
                    if entry[0] != payload["anchor_fingerprint"]:
                        self._refuse_identity_conflict(tid, entry[1],
                                                       payload)
                    continue  # same id + same anchor: idempotent shape
                known[tid] = (payload["anchor_fingerprint"],
                              payload.get("semantic_anchor", ""))
            elif kind == "task_superseded":
                old = payload["old_task_id"]
                new = payload["new_task_id"]
                if old not in known:
                    raise LedgerError(
                        "identity_contract: task_superseded references "
                        "unregistered old_task_id {0} — phantom supersede "
                        "refused (the old identity must exist; lineage "
                        "integrity)".format(old))
                if new in known:
                    raise LedgerError(
                        "identity_contract: supersede target {0} is "
                        "already registered (folded state or earlier in "
                        "this batch) — pick a fresh task id".format(new))
                known[new] = (anchor_fingerprint(
                    payload.get("new_anchor", "")),
                    payload.get("new_anchor", ""))
            elif kind == "task_state_changed":
                tid = payload["task_id"]
                if tid not in known:
                    raise LedgerError(
                        "identity_contract: task_state_changed for "
                        "unregistered task_id {0} — orphan state event "
                        "refused (register the identity first; "
                        "`migrate --write` seeds the history)".format(tid))

    def _refuse_identity_conflict(self, task_id, existing_anchor, payload):
        """Land the refusal's audit event, then raise — NO business event
        of the refused batch is appended (the attempt itself is the
        auditable fact, kept durably like every record_task refusal)."""
        audit = {
            "task_id": task_id,
            "existing_anchor": existing_anchor,
            "attempted_anchor": payload.get("semantic_anchor", ""),
            "attempted_fingerprint": payload.get("anchor_fingerprint", ""),
            "attempted_source": "transact",
        }
        self.transact([("identity_conflict_rejected", audit)])
        raise LedgerError(
            "identity_conflict: task {0} is registered with a different "
            "semantic anchor — 原 ID 静默换义 is refused; supersede "
            "instead (new task id / versioned id + task_superseded "
            "event)".format(task_id))

    def record_task(self, task_id, *, subject, priority="", target_version="",
                    status="", source="manual", allow_flag_conflict=False):
        """Register one task identity (idempotent on the same anchor).

        Returns a structured dict:
          ``registered``            — a new task_registered event landed;
          ``already_registered``    — same id + same anchor (idempotent);
          ``identity_conflict``     — REFUSED; the attempt was appended as
                                      an ``identity_conflict_rejected``
                                      audit event (nothing else written).
        """
        task_id = (task_id or "").strip()
        if not _TASK_ID_RE.match(task_id):
            return {"status": "refused", "code": "schema_violation",
                    "detail": "task_id {0!r} is not a PREFIX-NNN id".format(
                        task_id)}
        anchor = semantic_anchor(subject)
        if not anchor:
            return {"status": "refused", "code": "schema_violation",
                    "detail": "no semantic anchor in the subject cell"}
        payload = {
            "task_id": task_id,
            "semantic_anchor": anchor,
            "anchor_fingerprint": anchor_fingerprint(anchor),
            "priority": _clip(priority, 12),
            "target_version": _clip(target_version, 24),
            "status": _clip(status),
            "status_bucket": _task_completed_bucket(status),
            "source": source,
        }
        existing = self.state["tasks"].get(task_id)
        if existing is not None:
            if existing["anchor_fingerprint"] == payload["anchor_fingerprint"]:
                return {"status": "already_registered", "task_id": task_id,
                        "semantic_anchor": anchor}
            audit = {
                "task_id": task_id,
                "existing_anchor": existing["semantic_anchor"],
                "attempted_anchor": anchor,
                "attempted_fingerprint": payload["anchor_fingerprint"],
                "attempted_source": source,
            }
            if allow_flag_conflict:
                # migration path: keep the conflicting row as a FLAGGED
                # historical audit event (data preserved, disclosed) —
                # once per (task_id, attempted anchor); a re-run skips an
                # already-flagged pair (idempotent migration).
                key = "{0}:{1}".format(task_id,
                                       payload["anchor_fingerprint"])
                if key in self.state.get("conflict_keys", set()):
                    return {"status": "already_flagged", "task_id": task_id,
                            "semantic_anchor": anchor}
                outcome = self.transact(
                    [("historical_identity_conflict", audit)])
                return {"status": "flagged_historical_conflict",
                        "task_id": task_id, "audit": audit,
                        "transaction": outcome}
            outcome = self.transact(
                [("identity_conflict_rejected", audit)])
            return {"status": "refused", "code": "identity_conflict",
                    "task_id": task_id, "audit": audit,
                    "transaction": outcome}
        outcome = self.transact([("task_registered", payload)])
        return {"status": "registered", "task_id": task_id,
                "semantic_anchor": anchor, "transaction": outcome}

    def record_task_state_change(self, task_id, *, from_state, to_state,
                                 reason="", operation_id=None):
        """Record one task state transition (task_row_update's mirror).

        R0 P2-1: the task id must already be REGISTERED — a state event
        for an unknown identity is refused at the writer face (structured
        ``unknown_task_id``), never accepted and then silently dropped by
        the fold (the orphan-event class the drift face could only find
        AFTER the fact)."""
        task_id = (task_id or "").strip()
        if task_id not in self.state["tasks"]:
            return {"status": "refused", "code": "unknown_task_id",
                    "task_id": task_id,
                    "detail": "task {0} is not registered in the ledger — "
                              "register it first (`migrate --write` seeds "
                              "the history)".format(task_id)}
        payload = {
            "task_id": task_id,
            "from_state": _clip(from_state),
            "to_state": _clip(to_state),
            "to_bucket": _task_state_bucket(to_state),
            "reason": _clip(reason, 200),
        }
        if operation_id:
            payload["operation_id"] = operation_id
        outcome = self.transact([("task_state_changed", payload)])
        return {"status": "recorded", "transaction": outcome}

    def supersede_task(self, old_task_id, new_task_id, *, new_subject,
                       reason, mode="new_task", priority="",
                       target_version="", status=""):
        """The ONLY semantic-change path: register the replacement identity
        and record the replacement relationship.  The old id must be
        REGISTERED and the new id must be fresh (identity lineage — R0
        P2-2 refuses phantom supersedes)."""
        if not reason or not str(reason).strip():
            return {"status": "refused", "code": "schema_violation",
                    "detail": "superseding requires a reason"}
        anchor = semantic_anchor(new_subject)
        if not anchor:
            return {"status": "refused", "code": "schema_violation",
                    "detail": "no semantic anchor in the new subject cell"}
        payload = {
            "old_task_id": (old_task_id or "").strip(),
            "new_task_id": (new_task_id or "").strip(),
            "new_anchor": anchor,
            "reason": _clip(reason, 200),
            "mode": mode,
            "priority": _clip(priority, 12),
            "target_version": _clip(target_version, 24),
            "status": _clip(status),
            "status_bucket": _task_completed_bucket(status),
        }
        self._validate_payload("task_superseded", payload)
        if payload["new_task_id"] in self.state["tasks"]:
            return {"status": "refused", "code": "identity_conflict",
                    "detail": "new task id {0} is already registered".format(
                        payload["new_task_id"])}
        # R0 P2-2: the OLD identity must exist — a supersede referencing
        # an unregistered id is a phantom replacement (broken lineage).
        if payload["old_task_id"] not in self.state["tasks"]:
            return {"status": "refused", "code": "unknown_task_id",
                    "detail": "old task id {0} is not registered — "
                              "phantom supersede refused (lineage "
                              "integrity)".format(payload["old_task_id"])}
        outcome = self.transact([("task_superseded", payload)])
        return {"status": "superseded", "transaction": outcome}

    def record_event(self, kind, payload):
        """Generic single-event face for the schema-covered core-state
        families (review / recheck obligation / goal budget / gate / risk)."""
        outcome = self.transact([(kind, payload)])
        return {"status": "recorded", "transaction": outcome}


def build_snapshot(state, events, integrity):
    """The rebuildable snapshot cache (a projection of the log, never a
    second source of truth)."""
    return {
        "schema": LEDGER_SCHEMA,
        "writer": WRITER_ID,
        "event_count": len(events),
        "last_seq": integrity.get("last_seq", len(events)),
        "last_event_hash": integrity.get("last_event_hash", GENESIS_HASH),
        "built_at": _now_iso(),
        "counts": state["counts"],
        "state": {
            "tasks": state["tasks"],
            "gates": state["gates"],
            "risks": state["risks"],
        },
    }


# ── the progressive-adoption switch ─────────────────────────────────────────


def _config_section_text(plan_text):
    """Isolate the ``## 项目配置`` section (R0 P3-6 — the Gate parser's
    section-scope caliber): the adoption switch key is honored ONLY
    inside that section, so a ``- **authority_ledger**: …`` shaped line
    anywhere else (a quote, a code block, another section) can never
    flip the switch."""
    lines = []
    in_section = False
    for line in (plan_text or "").split("\n"):
        if line.startswith("## "):
            in_section = line.startswith(CONFIG_SECTION_PREFIX)
            continue
        if line.startswith("#"):
            in_section = False
            continue
        if in_section:
            lines.append(line)
    return "\n".join(lines)


def switch_state(plan_text=None, environ=None):
    """Resolve the adoption switch: env > plan-tracker > default(OFF).

    Fail-closed semantics mirror behavior_profile's caliber: an invalid
    token is REPORTED (``invalid``) BY THE ARM THAT SAW IT — no further
    arm is consulted, and :func:`switch_enabled` projects ``invalid`` to
    OFF.  A typo is never read as ``on`` (that would silently enable the
    write mirror) and never silently guessed as ``off`` either.  The
    plan-tracker key is honored ONLY inside the ``## 项目配置`` section
    (R0 P3-6 — the Gate parser's section-scope caliber).
    """
    environ = os.environ if environ is None else environ
    report = {"state": SWITCH_DEFAULT_STATE, "source": SWITCH_SOURCE_DEFAULT,
              "invalid": None}

    raw = (environ.get(SWITCH_ENV) or "").strip()
    if raw:
        low = raw.lower()
        if low in SWITCH_ON_TOKENS:
            return {**report, "state": SWITCH_STATE_ON,
                    "source": SWITCH_SOURCE_ENV}
        if low in SWITCH_OFF_TOKENS:
            return {**report, "state": SWITCH_STATE_OFF,
                    "source": SWITCH_SOURCE_ENV}
        return {**report, "state": SWITCH_STATE_INVALID,
                "source": SWITCH_SOURCE_ENV,
                "invalid": raw[:SWITCH_INVALID_VALUE_LIMIT]}

    if plan_text:
        for line in _config_section_text(plan_text).splitlines():
            stripped = line.strip()
            m = re.match(
                r"- \*\*{0}\*\*[::]\s*(\S+)".format(
                    re.escape(SWITCH_PLAN_TRACKER_KEY)), stripped)
            if m:
                token = m.group(1).strip().strip("`*").lower()
                if token in SWITCH_ON_TOKENS:
                    return {**report, "state": SWITCH_STATE_ON,
                            "source": SWITCH_SOURCE_PLAN_TRACKER}
                if token in SWITCH_OFF_TOKENS:
                    return {**report, "state": SWITCH_STATE_OFF,
                            "source": SWITCH_SOURCE_PLAN_TRACKER}
                return {**report, "state": SWITCH_STATE_INVALID,
                        "source": SWITCH_SOURCE_PLAN_TRACKER,
                        "invalid": token[:SWITCH_INVALID_VALUE_LIMIT]}
    return report


def switch_enabled(plan_text=None, environ=None):
    """Boolean projection of :func:`switch_state` (invalid ⇒ OFF — the
    fail-closed direction for a write-path switch)."""
    return switch_state(plan_text, environ)["state"] == SWITCH_STATE_ON


# ── hot-zone parsing (the projection SOURCE calibers) ───────────────────────


def _gate_section_text(plan_text):
    """Isolate the ``## Gate 状态跟踪`` section (bootstrap's
    ``_GATE_SECTION_PREFIX`` caliber — gate parsing is section-scoped so
    the V-Gate / 里程碑 tables can never masquerade as gate rows)."""
    lines = []
    in_section = False
    for line in (plan_text or "").split("\n"):
        if line.startswith("## "):
            in_section = line.startswith("## Gate 状态跟踪")
            continue
        if line.startswith("#"):
            in_section = False
            continue
        if in_section:
            lines.append(line)
    return "\n".join(lines)


def parse_hot_zone(plan_text, risk_text=""):
    """Parse the plan-tracker hot zone (task tables + Gate table) and the
    risk log into row inventories + canonical counts.

    Table calibers are SINGLE-SOURCED from the engine-free peer leaf
    ``bootstrap_aggregate`` (function-local import — the anti-drift
    choice): positional tables line-for-line mirror the engine's
    ``_status_table_stream``; gate/risk bucketing reuses the live
    implementations.  Gate parsing is section-scoped to ``## Gate 状态跟踪``
    (the bootstrap gate face's own caliber).
    """
    from bootstrap_aggregate import (_iter_positional_tables,
                                     _resolve_risk_status)

    task_rows = []
    gate_rows = []
    seen_ids = set()
    for header, rows in _iter_positional_tables(plan_text or ""):
        if len(header) >= 2 and header[0] == "优先级" and header[1] == "ID":
            id_pos = header.index("ID")
            subj_pos = header.index("事项") if "事项" in header else None
            prio_pos = 0
            ver_pos = header.index("目标版本") if "目标版本" in header \
                else None
            status_pos = header.index("状态") if "状态" in header else None
            width = max(p for p in (id_pos, subj_pos, prio_pos, ver_pos,
                                    status_pos) if p is not None)
            for cells in rows:
                if len(cells) <= width:
                    continue
                task_id = cells[id_pos].strip()
                if not _TASK_ID_RE.match(task_id):
                    continue
                subject = cells[subj_pos] if subj_pos is not None else ""
                status = cells[status_pos] if status_pos is not None else ""
                task_rows.append({
                    "task_id": task_id,
                    "priority": cells[prio_pos].strip(),
                    "subject": subject,
                    "target_version": cells[ver_pos].strip()
                    if ver_pos is not None else "",
                    "status": status,
                    "status_bucket": _task_completed_bucket(status),
                    "distinct": task_id not in seen_ids,
                })
                seen_ids.add(task_id)
    for header, rows in _iter_positional_tables(
            _gate_section_text(plan_text)):
        if "Gate" not in header or "状态" not in header:
            continue
        gate_pos = header.index("Gate")
        status_pos = header.index("状态")
        for cells in rows:
            if len(cells) <= max(gate_pos, status_pos):
                continue
            gate_id = cells[gate_pos].strip()
            if not gate_id:
                continue
            gate_rows.append({"gate_id": gate_id,
                              "status": cells[status_pos].strip(),
                              "bucket": _gate_bucket_of(
                                  cells[status_pos])})
    risk_rows = []
    for header, rows in _iter_positional_tables(risk_text or ""):
        if "编号" not in header or "当前状态" not in header:
            continue
        id_pos = header.index("编号")
        status_pos = header.index("当前状态")
        for cells in rows:
            if len(cells) <= max(id_pos, status_pos):
                continue
            rid = cells[id_pos].strip()
            if not rid:
                continue
            status, bucket = _resolve_risk_status(cells, status_pos)
            # bootstrap's count face skips closed rows; the LEDGER keeps
            # every row (zero-loss migration) and buckets it instead.
            risk_rows.append({"risk_id": rid, "status": status.strip(),
                              "bucket": bucket})
    return {
        "task_rows": task_rows,
        "gate_rows": gate_rows,
        "risk_rows": risk_rows,
        "counts": hot_zone_counts(task_rows, gate_rows, risk_rows),
    }


def hot_zone_counts(task_rows, gate_rows, risk_rows):
    """The canonical count facets shared by migration and rebuild (the
    item-by-item zero-loss comparison vocabulary)."""
    distinct = {row["task_id"] for row in task_rows}
    gates = {"rows": len(gate_rows), "passed": 0, "pending": 0, "failed": 0,
             "other": 0}
    for row in gate_rows:
        if row["bucket"] in gates:
            gates[row["bucket"]] += 1
    risks = {"rows": len(risk_rows), "open": 0, "closed": 0, "unknown": 0}
    for row in risk_rows:
        if row["bucket"] in risks:
            risks[row["bucket"]] += 1
    return {
        "tasks": {"rows": len(task_rows), "distinct_ids": len(distinct)},
        "gates": gates,
        "risks": risks,
    }


def _fold_counts_facets(state):
    """Ledger-side facets in the same vocabulary (for the comparison)."""
    counts = state["counts"]
    return {
        "tasks": {"registered": counts["tasks"]["registered"],
                  "identity_conflict_rows":
                      counts["tasks"]["identity_conflict_rows"]},
        "gates": {"recorded": counts["gates"]["recorded"],
                  "passed": counts["gates"]["passed"],
                  "pending": counts["gates"]["pending"],
                  "failed": counts["gates"]["failed"],
                  "other": counts["gates"]["other"]},
        "risks": {"recorded": counts["risks"]["recorded"],
                  "open": counts["risks"]["open"],
                  "closed": counts["risks"]["closed"],
                  "unknown": counts["risks"]["unknown"]},
    }


# ── migration (dry-run first, zero-loss proof) ──────────────────────────────


def migrate(governance_dir, *, plan_tracker=None, risk_log=None,
            dry_run=True, actor=WRITER_ID):
    """Register the existing hot-zone history into the ledger.

    Zero-loss contract: every parsed task row lands as exactly one of
    ``registered`` / ``same_anchor_duplicate`` / ``flagged conflict``;
    every gate/risk row lands as one ``*_recorded`` event.  The returned
    report carries the item-by-item counts comparison and FAILs loudly on
    any gap.  ``dry_run=True`` writes NOTHING (no events, no snapshot).
    """
    started = time.perf_counter()
    plan_path = Path(plan_tracker) if plan_tracker else \
        Path(governance_dir) / "plan-tracker.md"
    risk_path = Path(risk_log) if risk_log else \
        Path(governance_dir) / "risk-log.md"
    plan_text = plan_path.read_text(encoding="utf-8") \
        if plan_path.is_file() else ""
    risk_text = risk_path.read_text(encoding="utf-8") \
        if risk_path.is_file() else ""
    parsed = parse_hot_zone(plan_text, risk_text)

    plan = {"task_registered": 0, "same_anchor_duplicates": 0,
            "flagged_conflicts": 0, "gate_recorded": 0, "risk_recorded": 0}
    writer = LedgerWriter(governance_dir, actor=actor)
    if not writer.integrity["ok"]:
        return {"status": "FAIL", "code": "integrity_broken",
                "integrity": writer.integrity,
                "detail": "refusing to migrate onto a broken event log"}

    def _register_all(w):
        for row in parsed["task_rows"]:
            result = w.record_task(
                row["task_id"], subject=row["subject"],
                priority=row["priority"],
                target_version=row["target_version"],
                status=row["status"], source="migration",
                allow_flag_conflict=True)
            if result["status"] == "registered":
                plan["task_registered"] += 1
            elif result["status"] == "already_registered":
                plan["same_anchor_duplicates"] += 1
            elif result["status"] in ("flagged_historical_conflict",
                                      "already_flagged"):
                plan["flagged_conflicts"] += 1
            else:  # an unregistrable source row (e.g. empty anchor) —
                # surfaced as a structured FAIL by migrate (R0 P3-5).
                raise LedgerError(
                    "migration refused row {0}: {1}".format(
                        row["task_id"], result))
        for row in parsed["gate_rows"]:
            existing = w.state["gates"].get(row["gate_id"])
            if existing is not None and existing.get("status") == row["status"]:
                continue  # idempotent re-migration: same gate, same status
            w.record_event("gate_recorded", {
                "gate_id": row["gate_id"], "status": row["status"],
                "bucket": row["bucket"], "source": "migration"})
            plan["gate_recorded"] += 1
        for row in parsed["risk_rows"]:
            existing = w.state["risks"].get(row["risk_id"])
            if existing is not None and existing.get("bucket") == row["bucket"]:
                continue  # idempotent re-migration: same risk, same bucket
            w.record_event("risk_recorded", {
                "risk_id": row["risk_id"], "status": _clip(row["status"]),
                "bucket": row["bucket"], "source": "migration"})
            plan["risk_recorded"] += 1
        w.record_event("historical_migrated", {
            "source": "plan-tracker+risk-log",
            "counts": {"tasks": plan["task_registered"]
                       + plan["same_anchor_duplicates"]
                       + plan["flagged_conflicts"],
                       "gates": plan["gate_recorded"],
                       "risks": plan["risk_recorded"]},
            "dry_run": False,
        })

    if dry_run:
        # Full plan on a throwaway in-memory copy: run the same registration
        # sequence against a temp ledger dir so the counts proof is the REAL
        # fold, then discard it — the live ledger stays untouched.  Plain
        # default-mode mkdir (the FIX-404 lesson: mkdtemp's 0o700 dirs deny
        # writes under the UAC-filtered sandbox token).
        import shutil
        import tempfile
        tmp_base = Path(tempfile.gettempdir()) / (
            "feat093-migrate-dry-" + uuid.uuid4().hex[:12])
        tmp_base.mkdir()
        try:
            tmp_gov = tmp_base / ".governance"
            tmp_gov.mkdir()
            # R0 P3-3: seed the rehearsal ledger with the LIVE event log
            # (when one exists) so a RE-migration dry-run predicts live
            # counts — already-registered rows rehearse as same-anchor
            # duplicates exactly as the live write would class them.  A
            # first-migration dry-run has no live log and rehearses on an
            # empty ledger (the zero-loss proof semantics unchanged).
            if writer.events_path.is_file():
                tmp_ledger = tmp_gov / LEDGER_DIRNAME
                tmp_ledger.mkdir()
                shutil.copyfile(writer.events_path,
                                tmp_ledger / EVENTS_FILENAME)
            tmp_writer = LedgerWriter(tmp_gov, actor=actor)
            try:  # R0 P3-5: structured FAIL, never a traceback
                _register_all(tmp_writer)
            except LedgerError as exc:
                return _migration_row_refused(exc, dry_run=True)
            folded = hot_zone_counts(
                [{"task_id": t} for t in tmp_writer.state["tasks"]],
                [{"bucket": g["bucket"]} for g in
                 tmp_writer.state["gates"].values()],
                [{"bucket": r["bucket"]} for r in
                 tmp_writer.state["risks"].values()])
            folded["tasks"]["rows"] = plan["task_registered"] \
                + plan["same_anchor_duplicates"] + plan["flagged_conflicts"]
            ledger_ids = set(tmp_writer.state["tasks"])
        finally:
            shutil.rmtree(tmp_base, ignore_errors=True)
        report = _migration_report(parsed, plan, folded, started,
                                   dry_run=True, ledger_task_ids=ledger_ids)
        return report

    try:  # R0 P3-5: structured FAIL, never a traceback
        _register_all(writer)
    except LedgerError as exc:
        return _migration_row_refused(exc, dry_run=False)
    folded = hot_zone_counts(
        [{"task_id": t} for t in writer.state["tasks"]],
        [{"bucket": g["bucket"]} for g in writer.state["gates"].values()],
        [{"bucket": r["bucket"]} for r in writer.state["risks"].values()])
    folded["tasks"]["rows"] = plan["task_registered"] \
        + plan["same_anchor_duplicates"] + plan["flagged_conflicts"]
    return _migration_report(parsed, plan, folded, started, dry_run=False,
                             ledger_task_ids=set(writer.state["tasks"]))


def _migration_row_refused(exc, *, dry_run):
    """Structured FAIL for an unregistrable source row (R0 P3-5).

    The migration stops loudly WITHOUT a stack trace; events already
    appended by this run stay valid (the write path is per-row
    idempotent — fix the source row and re-run ``migrate --write``).
    """
    return {"status": "FAIL", "code": "schema_violation_row",
            "dry_run": dry_run, "detail": "{0}".format(exc)}


def _migration_report(parsed, plan, folded, started, *, dry_run,
                      ledger_task_ids):
    file_counts = parsed["counts"]
    file_task_ids = {row["task_id"] for row in parsed["task_rows"]}
    comparison = _compare_counts(
        file_counts, folded,
        file_task_ids=file_task_ids, ledger_task_ids=ledger_task_ids,
        row_accounting=True)
    balanced = all(item["equal"] for item in comparison)
    return {
        "status": "PASS" if balanced else "FAIL",
        "dry_run": dry_run,
        "wrote": {"events": 0 if dry_run else
                  plan["task_registered"] + plan["flagged_conflicts"]
                  + plan["gate_recorded"] + plan["risk_recorded"] + 1},
        "plan": plan,
        "counts_before": file_counts,
        "counts_after": folded,
        "comparison": comparison,
        "wall_ms": round((time.perf_counter() - started) * 1000, 1),
    }


def _compare_counts(before, after, *, file_task_ids=None,
                    ledger_task_ids=None, row_accounting=True):
    """Item-by-item comparison (the zero-loss proof vocabulary).

    ``before`` = parsed from the hot-zone files (rows / distinct ids /
    buckets); ``after`` = folded from the ledger.  Facets compare
    like-for-like:

    * ``tasks.distinct_ids`` / ``tasks.id_set`` — identity facets (always
      compared; the ledger models IDENTITIES, and same-anchor duplicate
      ROWS are intentionally collapsed by the identity model);
    * ``tasks.rows`` — row accounting (``row_accounting=True``: the
      migration face, where every parsed row is classed registered /
      same-anchor duplicate / flagged conflict);
    * gate/risk ``rows`` + per-bucket facets compare in both modes.
    """
    items = []

    def facet(name, left, right):
        items.append({"facet": name, "from_files": left,
                      "from_ledger": right, "equal": left == right})

    bt, bg, br = before["tasks"], before["gates"], before["risks"]
    at, ag, ar = after["tasks"], after["gates"], after["risks"]
    facet("tasks.distinct_ids", bt["distinct_ids"],
          at.get("distinct_ids", at.get("registered", 0)))
    if file_task_ids is not None and ledger_task_ids is not None:
        facet("tasks.id_set", sorted(file_task_ids),
              sorted(ledger_task_ids))
    if row_accounting:
        facet("tasks.rows", bt["rows"], at.get("rows",
                                               at.get("registered", 0)))
    facet("gates.rows", bg["rows"], ag.get("rows", ag.get("recorded", 0)))
    for bucket in ("passed", "pending", "failed", "other"):
        facet("gates.{0}".format(bucket), bg[bucket], ag.get(bucket, 0))
    facet("risks.rows", br["rows"], ar.get("rows", ar.get("recorded", 0)))
    for bucket in ("open", "closed", "unknown"):
        facet("risks.{0}".format(bucket), br[bucket], ar.get(bucket, 0))
    return items


# ── projection rebuild (ledger → hot zone, counts-identical proof) ──────────


def rebuild_projection(governance_dir, *, plan_tracker=None, risk_log=None,
                       write=False, actor=WRITER_ID):
    """Rebuild the hot-zone projection from the ledger + prove it.

    The materialized projection is the SNAPSHOT (the plan-tracker table
    remains the rendered narrative surface; its state cells are owned by
    task_row_update).  This command: folds the ledger, compares its state
    against the CURRENT hot-zone files item by item, rebuilds the snapshot
    (``write=True``) and appends a ``projection_rebuilt`` audit event
    carrying the counts.  PASS iff every facet matches.
    """
    started = time.perf_counter()
    plan_path = Path(plan_tracker) if plan_tracker else \
        Path(governance_dir) / "plan-tracker.md"
    risk_path = Path(risk_log) if risk_log else \
        Path(governance_dir) / "risk-log.md"
    plan_text = plan_path.read_text(encoding="utf-8") \
        if plan_path.is_file() else ""
    risk_text = risk_path.read_text(encoding="utf-8") \
        if risk_path.is_file() else ""
    parsed = parse_hot_zone(plan_text, risk_text)

    writer = LedgerWriter(governance_dir, actor=actor)
    if not writer.integrity["ok"]:
        return {"status": "FAIL", "code": "integrity_broken",
                "integrity": writer.integrity,
                "detail": "refusing to rebuild from a broken event log"}
    state = writer.state
    folded = hot_zone_counts(
        [{"task_id": tid} for tid in state["tasks"]],
        [{"bucket": gate["bucket"]} for gate in state["gates"].values()],
        [{"bucket": risk["bucket"]} for risk in state["risks"].values()])
    registered = state["counts"]["tasks"]["registered"]
    conflict_rows = state["counts"]["tasks"]["identity_conflict_rows"]
    # ledger-side rows = registered ids + one flagged row per historical
    # conflict (distinct_ids below is len(state tasks) — conflict ids are
    # always a SUBSET of registered ids, never additional ids).
    folded["tasks"]["rows"] = registered + conflict_rows

    # drift face: ledger task state vs the CURRENT table rows (advisory for
    # the later read-side switch; never silently repairs narrative rows).
    drift = []
    by_id = {}
    for row in parsed["task_rows"]:
        by_id.setdefault(row["task_id"], row)
    for tid, task in sorted(state["tasks"].items()):
        table_row = by_id.get(tid)
        if table_row is None:
            drift.append({"task_id": tid, "kind": "ledger_only"})
        elif table_row["status_bucket"] != task.get("status_bucket"):
            drift.append({"task_id": tid, "kind": "status_mismatch",
                          "ledger": task.get("status_bucket"),
                          "table": table_row["status_bucket"]})
    for tid in sorted(set(by_id) - set(state["tasks"])):
        drift.append({"task_id": tid, "kind": "table_only"})

    comparison = _compare_counts(
        parsed["counts"], folded,
        file_task_ids={row["task_id"] for row in parsed["task_rows"]},
        ledger_task_ids=set(state["tasks"]),
        row_accounting=False)
    balanced = all(item["equal"] for item in comparison)
    snapshot_face = {"written": False}
    if write:
        snapshot = writer._write_snapshot()
        outcome = writer.record_event("projection_rebuilt", {
            "counts": {"tasks_rows": folded["tasks"]["rows"],
                       "gates_rows": folded["gates"]["rows"],
                       "risks_rows": folded["risks"]["rows"]},
            "balanced": balanced,
        })
        snapshot_face = {"written": True,
                         "event_count": snapshot["event_count"],
                         "last_seq": snapshot["last_seq"],
                         "rebuild_event_seq": outcome["transaction"].get(
                             "last_seq")}
    return {
        "status": "PASS" if balanced else "FAIL",
        "write": write,
        "counts_before": parsed["counts"],
        "counts_after": folded,
        "comparison": comparison,
        "drift": drift[:50],
        "drift_count": len(drift),
        "snapshot": snapshot_face,
        "event_count": len(writer.events),
        "wall_ms": round((time.perf_counter() - started) * 1000, 1),
    }


# ── status face ─────────────────────────────────────────────────────────────


def status(governance_dir, *, plan_tracker=None):
    """Read-only ledger status: switch state, integrity, counts, snapshot
    freshness (the hot-zone projection health face)."""
    plan_path = Path(plan_tracker) if plan_tracker else \
        Path(governance_dir) / "plan-tracker.md"
    plan_text = plan_path.read_text(encoding="utf-8") \
        if plan_path.is_file() else ""
    ledger_dir, events_path, snapshot_path = ledger_paths(governance_dir)
    events, integrity = _read_events_raw(events_path)
    state = fold_state(events)
    snapshot_face = {"exists": snapshot_path.is_file()}
    if snapshot_path.is_file():
        try:
            snapshot = json.loads(
                snapshot_path.read_text(encoding="utf-8"))
            snapshot_face.update({
                "event_count": snapshot.get("event_count"),
                "last_seq": snapshot.get("last_seq"),
                "stale": snapshot.get("last_seq") != integrity["last_seq"],
            })
        except (ValueError, OSError) as exc:
            snapshot_face["error"] = "{0}: {1}".format(
                type(exc).__name__, exc)
    return {
        "schema": LEDGER_SCHEMA,
        "task_id": TASK_ID,
        "governance_dir": str(Path(governance_dir)),
        "ledger_dir": str(ledger_dir),
        "switch": switch_state(plan_text),
        "integrity": {"ok": integrity["ok"],
                      "problems": integrity["problems"][:5],
                      "lines": integrity["lines"],
                      "last_seq": integrity["last_seq"]},
        "counts": _fold_counts_facets(state),
        "open_recheck_obligations": len(
            state["open_recheck_obligations"]),
        "snapshot": snapshot_face,
    }


# ── CLI (module-owned option fact source + Namespace handler) ───────────────


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """The module-owned option fact source (single definition shared by
    ``main`` and the engine subparser — FEAT-047 P2-1 caliber)."""
    parser.add_argument(
        "action", choices=("status", "migrate", "rebuild"),
        help="status = read-only ledger face; migrate = register the "
             "existing hot-zone history (dry-run first!); rebuild = "
             "rebuild + prove the hot-zone projection from the ledger")
    parser.add_argument(
        "--governance-dir", default=os.path.join(".", ".governance"),
        help="Governance dir holding plan-tracker.md / risk-log.md / the "
             "authority-ledger/ carrier (default: %(default)s)")
    parser.add_argument(
        "--plan-tracker", default=None,
        help="Explicit plan-tracker path override (default: "
             "<governance-dir>/plan-tracker.md)")
    parser.add_argument(
        "--risk-log", default=None,
        help="Explicit risk-log path override (default: "
             "<governance-dir>/risk-log.md)")
    parser.add_argument(
        "--dry-run", dest="write", action="store_false",
        help="Explicit dry-run (the DEFAULT posture: plan + prove "
             "everything, write NOTHING)")
    parser.add_argument(
        "--write", dest="write", action="store_true",
        help="Execute the write (migrate: append events + snapshot; "
             "rebuild: rewrite the snapshot + append the audit event)")
    parser.set_defaults(write=False)
    parser.add_argument(
        "--text", dest="json", action="store_false", default=True,
        help="Human-readable rendering instead of JSON")


def _emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2,
                         default=str))
        return
    print("[{0}] {1}".format(
        payload.get("status", "INFO"),
        payload.get("schema", "authority-ledger")))
    for key in ("dry_run", "write", "wrote", "plan", "event_count",
                "wall_ms", "switch", "integrity", "snapshot", "drift_count",
                "code", "detail"):
        if key in payload:
            print("  {0}: {1}".format(key, json.dumps(
                payload[key], ensure_ascii=False, default=str)))
    comparison = payload.get("comparison") or []
    if comparison:
        print("  counts comparison (from_files == from_ledger):")
        for item in comparison:
            print("    [{0}] {1}: {2} vs {3}".format(
                "=" if item["equal"] else "X", item["facet"],
                item["from_files"], item["from_ledger"]))
    drift = payload.get("drift")
    if drift:
        print("  drift (first {0}):".format(len(drift)))
        for item in drift:
            print("    - {0}".format(json.dumps(
                item, ensure_ascii=False, default=str)))


def _cmd(governance_dir, action, *, plan_tracker, risk_log, write):
    if action == "status":
        return 0, status(governance_dir, plan_tracker=plan_tracker)
    if action == "migrate":
        result = migrate(governance_dir, plan_tracker=plan_tracker,
                         risk_log=risk_log, dry_run=not write)
    else:
        result = rebuild_projection(governance_dir,
                                    plan_tracker=plan_tracker,
                                    risk_log=risk_log, write=write)
    if result.get("status") == "FAIL":
        return 1, result
    return 0, result


def cmd_authority_ledger(args) -> int:
    """Engine dispatch face (the engine wires dispatch only — the
    governance_cost pattern; no argv re-parse)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    code, payload = _cmd(
        getattr(args, "governance_dir", os.path.join(".", ".governance")),
        getattr(args, "action", "status"),
        plan_tracker=getattr(args, "plan_tracker", None),
        risk_log=getattr(args, "risk_log", None),
        write=getattr(args, "write", False))
    _emit(payload, getattr(args, "json", True))
    return code


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="authority-ledger",
        description=(
            "FEAT-093 authority ledger: task identity contract + append-"
            "only event log + rebuildable plan-tracker projection. The "
            "writer refuses same-id-different-semantics registrations "
            "(identity_conflict) and keeps every attempt as an audit "
            "event."))
    add_arguments(parser)
    args = parser.parse_args(argv)
    return cmd_authority_ledger(args)


if __name__ == "__main__":  # pragma: no cover - direct invocation seam
    sys.exit(main())
