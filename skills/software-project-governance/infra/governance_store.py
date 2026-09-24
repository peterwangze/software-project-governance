"""FEAT-046 — governed writer family for the machine-record store (batch 1).

Three command families over the same governed-write pipeline (version-plan
0.86.0 §2 批 1 / boundary-audit B-3 + B-5 + B-2):

    locks-extend     TTL 延展 for existing ``agent-locks.json`` entries
    locks-amend      field/file amendments for existing dispatch locks
    locks-release    task-anchored release: the active_tasks entry AND every
                     file lock owned by the task (FIX-370 / B-10)
    evidence-append  machine EVD row append into ``evidence-log.md``
    decision-append  machine DEC row append into ``decision-log.md``

(locks-extend / locks-amend / locks-release are one family over the same
acquire-pipeline schema; evidence-append / decision-append share the append
pipeline.)

Root causes closed here (0.86.0-boundary-audit.md):

  * B-3 — ``acquire_dispatch_locks`` covers acquisition only; every TTL
    extension / file addition was a hand edit of ``agent-locks.json``
    (4 live schema incidents in the 2026-09-19 session).  Both commands
    here reuse the ACQUIRE pipeline's schema semantics (Check 26 field
    shape ``locked_by`` / ``locked_at`` / ``ttl_seconds`` / ``ttl_reason``,
    optional ``expected_new``) — no second schema is defined.
  * B-5 — every hand-written EVD row was an unschema'd structural
    operation (×415 legacy column-drift WARN baseline).  ``evidence-append``
    enforces the skeleton mechanically and stays OUT of content semantics
    (W-4): no keyword / whitelist / opinion scanning — the narrative is the
    caller's judgment (J10); only the mechanical skeleton is judged.
  * B-2 — decision rows had no writer at all (one truncation incident,
    FIX-312 exposure).  ``decision-append`` is the minimal governed append.

Contract consumption (M0 frozen revision ``m0-r1``, READ-ONLY — the change
rule in ``infra/fixtures/m0/manifest.json`` applies to any extension):

  * face 1  ``operation_id`` — ``new_operation_id`` / ``require_operation_id``
    / ``decide_operation_replay`` power the retry protocol;
  * face 3  ``ERROR_CODE_DISPOSITIONS`` — every refusal reports a closed
    error code + disposition class;
  * face 4  ``SchemaVersionWindow`` — rows carry ``schema v1``; unknown
    newer schemas are refused, never guessed;
  * face 5  ``WriterResult`` / ``EvidenceRef`` / ``EVIDENCE_REF_KINDS`` /
    ``REFERENCE_VALIDATION_STATES`` / ``IDEMPOTENCY_MODEL`` — structured
    results and the typed reference machine-check.
    ``reference_validation`` is deliberately SEPARATE from any verdict
    (arch round-2 §3): this CLI reports resolvability only; whether
    evidence is SUFFICIENT stays a human/LLM verdict and is never derived
    from file existence.

DoD ten items (0.86.0-architecture-evolution.md §4, items 0–9) mapping:

  0 model output untrusted — every string argument is type/shape checked;
    ``git_object`` values are form-validated before any subprocess; URL
    refs are syntax-checked and NEVER fetched (no network).
  1 pre-write full validation — the candidate row is fully built and
    validated (shape + IDs + refs + cross-record ID continuity) before the
    target is opened for writing.
  2 idempotency/conflict — same operation_id + same payload returns the
    recorded result (replay, never re-append); same id + different payload
    is refused (``operation_id_conflict``).  Idempotency is effect-based
    (查世界不信日志, ``IDEMPOTENCY_MODEL``): appends recover by locating the
    operation marker in the target file (world, not log); locks resume by
    comparing the world against the recorded target/baseline state.
  3 reliable persistence — explicit UTF-8 (no BOM), same-directory temp
    file + ``os.replace`` (atomic), original line endings and the original
    byte prefix preserved.
  4 post-write reread — the same validator re-parses the written row (no
    second schema definition) and the pre-write byte prefix is compared
    (a mismatch is disclosed, never auto-restored).
  5 dry-run + structured results — ``--dry-run`` renders the exact row and
    the full validation result while writing NOTHING; refusals carry the
    closed code + disposition (validation / conflict / retryable / manual).
  6 recovery — a crash between the target write and the ledger write is
    recovered by the effect-based replay above; locks operations record a
    pending-effects ledger entry (target + baseline) so a re-run either
    completes, re-applies from an unchanged baseline, or refuses as
    ``manual_intervention`` — never double-applies.
  7 guard tests — column-shape refusal / per-kind missing-ref refusal /
    same-op replay / concurrent appends (threading) / GBK + CJK payload /
    markdown pipe special characters / legacy ×415 rows untouched.
  8 progressive adoption — this module is opt-in: nothing in the engine
    routes through it, and the fallback is the pre-existing path (direct
    CLI / manual edit), not a schema relaxation.
  9 machine provenance — every machine-written row self-identifies
    (``机器写入：governance-store <command> <operation_id>`` marker in the
    basis cell; actor cell ``governance-store``).

Registration face (组合根装配 — wired by FEAT-055, 0.86.0 batch 2.0): the
four writer commands are now engine-dispatched (`registry._COMMANDS` +
verify_workflow main(); FEAT-020 frozen face re-baselined 88 → 95 keys in
the same change).  The module keeps its own composition root (``COMMANDS`` +
:func:`main`) so ``python governance_store.py <command> …`` keeps working —
both paths share one option fact source (``add_*_arguments``) and one
Namespace executor (``cmd_*``, FEAT-047 P2-1 caliber — no argv re-parse).

Batch-2.0 disclosure obligations discharged here (review-FEAT-046-CODE-R0
P3-2/P3-3, FEAT-055):

  * **Stale-lock takeover (P3-2)** — a lockfile older than
    ``_LOCK_STALE_SECONDS`` (600s) is unlinked and taken over by the next
    acquirer.  Reachable only when one holder is pathologically slow (>600s
    for a single-file atomic write); the disclosed cost is a transient
    mutual-exclusion erosion (a stale holder that eventually finishes will
    not unlink its successor's lock — it no longer owns ``_acquired``).
  * **New .governance artifacts have no check coverage (P3-2)** —
    ``governance-store-ops.json`` (the operation ledger) and
    ``.governance-store-locks/`` (the lockfile dir) are read/written only by
    this module; no verify_workflow check guards them yet.  Unbounded ledger
    growth is registered as BT-4 (evolution §5); a structural check is a
    later-slice candidate, not silently assumed.
  * **governance_id matching is mention-level (P3-3)** —
    ``_validate_governance_id`` searches hot files and the archive with a
    ``\b``-delimited substring match, NOT row-anchored: a typo'd mention in
    prose is enough to report ``resolvable``.  Under the resolvability-only
    contract this cannot fabricate a verdict (validation ≠ sufficiency),
    and row-anchored matching is deferred deliberately — tightening it
    would change the resolvable face of existing legitimate references.

×415 legacy policy (arch round-2 §3): legacy rows are a legacy batch —
read-safety only; this writer constrains NEW rows and never rewrites or
re-judges existing content.

Zero injection surface: subprocess use is one argv-list ``git rev-parse
--verify`` on a form-validated value; no shell, no network, no templated
commands.  Cells containing a raw ``|`` or a newline are REFUSED (they
would change the column shape); the refusal message documents the two
safe spellings (inline-code span, full-width ｜).
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
import threading
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

from contracts import (  # L0 — consumed read-only, never redefined
    ERROR_CODE_DISPOSITIONS,
    EVIDENCE_REF_KINDS,
    ContractViolation,
    EvidenceRef,
    IDEMPOTENCY_MODEL,
    REFERENCE_VALIDATION_STATES,
    RESULT_OK,
    SchemaVersionWindow,
    WriterResult,
    decide_operation_replay,
    new_operation_id,
    require_input_fingerprint,
    require_operation_id,
)
# FIX-379 item-2: the authoritative task-family vocabulary (single source;
# change_triage mirrors it verbatim — see the source's own comment).  The
# underscore name is imported deliberately: growing task_priority a public
# accessor is out of this ticket's file surface, and a third hand-copy of
# the list here would re-create the drift the alignment removes.
from task_priority import _TASK_FAMILY_PREFIXES as _TASK_FAMILY_PREFIXES_SOURCE

__all__ = [
    "COMMANDS",
    "DEC_COLUMNS",
    "EVIDENCE_COLUMNS",
    "LEDGER_FILE_NAME",
    "SCHEMA_VERSION",
    "SCHEMA_WINDOW",
    "build_parser",
    "decision_append",
    "evidence_append",
    "locks_amend",
    "locks_extend",
    "locks_load",
    "locks_release",
    "main",
]

# ── constants ────────────────────────────────────────────────────────────────

GOVERNANCE_DIR_NAME = ".governance"
LOCKS_FILE_NAME = "agent-locks.json"
EVIDENCE_FILE_NAME = "evidence-log.md"
DECISION_FILE_NAME = "decision-log.md"
LEDGER_FILE_NAME = "governance-store-ops.json"
LOCK_DIR_NAME = ".governance-store-locks"
ARCHIVE_DIR_NAME = "archive"

SCHEMA_VERSION = 1
SCHEMA_WINDOW = SchemaVersionWindow(minimum=1, current=1)

#: The 10-column machine-row standard (DEC-168 row-family authority; the
#: TRIAGE family shape — id | task_ref | type | description | basis |
#: artifacts | actor | date | gate | conclusion).
EVIDENCE_COLUMNS = 10

#: The live decision-log row shape (DEC-147…DEC-221 hot-file convention):
#: 编号 | 日期 | 决策人 | 决策内容 | 依据.  The file's 11-column header is a
#: legacy projection; live hot rows are 5 cells and Check 13/14 do not read
#: decision rows by position — this writer follows the live shape.
DEC_COLUMNS = 5

#: Mandatory non-empty decision cells: 编号 / 日期 / 决策人 / 决策内容.
DEC_MANDATORY_CELLS = 4

EVD_ROW_PREFIX = "EVD-"
DEC_ROW_PREFIX = "DEC-"

#: Engine-mirrored skeleton regexes (verify_workflow.py Check 16/18 caliber).
#: Mirrored verbatim so write-time validation and the post-write engine
#: checks agree — a row accepted here cannot add engine findings.
_GOAL_ALIGNMENT_RE = re.compile(
    r"目标对齐[:：]\s*(.+?)(?:\s*(?:用户影响[:：]|范围[:：]|依赖[:：]|架构影响[:：]|$))")
_FACT_BASIS_RE = re.compile(
    r"事实依据[:：]\s*(.+?)(?:\s*(?:目标对齐[:：]|用户影响[:：]|范围[:：]|依赖[:：]|架构影响[:：]|$))")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TASK_ID_RE = re.compile(r"^[A-Z]+-\d+$")
_GIT_OBJECT_RE = re.compile(r"^[0-9a-f]{7,40}$|^HEAD(?:~[0-9]+)?$")

#: governance_id → the hot file (+ archive) whose rows carry that family.
#:
#: FIX-379 item-2 (0.86.0 M-2 量测边缘观察 #2) — vocabulary alignment to a
#: single source.  Two layers with different purposes used to drift apart:
#:   * TASK families (rows live in plan-tracker.md) — DERIVED from
#:     ``task_priority._TASK_FAMILY_PREFIXES`` (imported above), the
#:     authoritative task-family vocabulary that change_triage mirrors.
#:     Every triageable task id is therefore addressable as a
#:     ``governance_id`` evidence ref (mention-level search in
#:     plan-tracker.md), closing the "triage books the ticket but the ref
#:     machine-check rejects its family" gap for the 13 task prefixes the
#:     previous hand-copied map omitted (FMT/DIAG/MAINT/TD/DESIGN/
#:     CLEANUP/PRINCIPLE/TASK/RESEARCH/ACCEPT/INIT/PLAN/DOC).  Additive
#:     only: no previously resolvable ref changes meaning — a ref to an
#:     id genuinely absent from the tracker still reports unresolvable.
#:   * RECORD families (rows live in the other hot files) — kept
#:     explicit: these are record registries, not task ids, and are
#:     deliberately NOT part of the task-family vocabulary.
#: Ad-hoc prefixes outside BOTH layers (the M-2 ``MES-001`` incident)
#: remain unknown-family refusals.  The triage-side entry gate itself
#: (shape-only ``PREFIX-NNN`` validation in change_triage.py, both the
#: triage-record and the agent-locks-acquire paths) is unchanged —
#: constraining it to the task-family vocabulary is a behavior change
#: that belongs to its own triaged ticket (out of this one's file
#: surface), see the proposed follow-up in the FIX-379 result.
_PLAN_TRACKER_ID_FAMILIES = {
    family: ("plan-tracker.md",)
    for family in sorted(_TASK_FAMILY_PREFIXES_SOURCE)
}
_RECORD_ID_FAMILIES = {
    "DEC": ("decision-log.md",),
    "EVD": ("evidence-log.md",),
    "RISK": ("risk-log.md",),
    "REVIEW": ("evidence-log.md",),
    "RECO": ("evidence-log.md",),
    "TRIAGE": ("evidence-log.md",),
}
_GOVERNANCE_ID_FAMILIES = {**_RECORD_ID_FAMILIES, **_PLAN_TRACKER_ID_FAMILIES}

#: CLI aliases for the contract kinds (documented shorthand, normalized to
#: the frozen enum — the contract spelling is what gets stored).
_KIND_ALIASES = {
    "url_syntax": "url",
    "human_note": "human_observation",
}

_LOCK_STALE_SECONDS = 600
_LOCK_POLL_SECONDS = 0.05

_INPROC_GUARD = threading.Lock()
_INPROC_LOCKS: dict = {}


class StoreError(Exception):
    """Internal carrier for a structured writer refusal (never shown raw)."""

    def __init__(self, payload):
        super().__init__(payload.get("detail", "governance-store error"))
        self.payload = payload


# ── small fail-closed helpers ────────────────────────────────────────────────


def _require_text(where, value):
    if not isinstance(value, str) or not value.strip():
        raise StoreError({
            "code": "schema_violation",
            "detail": f"{where}: expected a non-empty string, got {value!r}",
        })
    return value


def _require_int(where, value, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise StoreError({
            "code": "schema_violation",
            "detail": f"{where}: expected an int >= {minimum}, got {value!r}",
        })
    return value


def _require_date(where, value):
    text = _require_text(where, value)
    if not _DATE_RE.match(text):
        raise StoreError({
            "code": "schema_violation",
            "detail": f"{where}: expected an ISO date YYYY-MM-DD, got "
                      f"{text!r}",
        })
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        raise StoreError({
            "code": "schema_violation",
            "detail": f"{where}: {text!r} is not a real calendar date",
        })
    return text


def _fingerprint(payload) -> str:
    """SHA-256 hex of the canonical normalized input (writer-stable)."""
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _result_dict(result: WriterResult, **extra) -> dict:
    data = {
        "operation_id": result.operation_id,
        "code": result.code,
        "new_revision": result.new_revision,
        "observed_revision": result.observed_revision,
        "execution": result.execution,
        "detail": result.detail,
    }
    data.update(extra)
    return data


def _error_result(operation_id, code, detail, observed_revision=None) -> dict:
    """Build the structured refusal (closed code + disposition class)."""
    result = WriterResult(
        operation_id=operation_id,
        code=code,
        observed_revision=observed_revision,
        detail=detail,
    )
    return _result_dict(
        result,
        disposition=ERROR_CODE_DISPOSITIONS[code],
        error=True,
    )


def _ok_result(operation_id, new_revision, detail=None, **extra) -> dict:
    result = WriterResult(
        operation_id=operation_id,
        code=RESULT_OK,
        new_revision=new_revision,
        execution="succeeded",
        detail=detail,
    )
    return _result_dict(result, error=False, **extra)


def _refuse(payload):
    raise StoreError(payload)


def _returns_payload(fn):
    """Public API boundary: refusals come back as structured payload dicts
    (the acquire-pipeline convention — ``acquire_dispatch_locks`` never
    raises); internal helpers keep raising for control flow."""

    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except StoreError as exc:
            payload = exc.payload
            payload.setdefault("error", True)
            payload.setdefault(
                "disposition",
                ERROR_CODE_DISPOSITIONS.get(payload.get("code")))
            return payload

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        _refuse({
            "code": "manual_intervention",
            "detail": f"cannot read {path}: {exc}",
        })


def _decode_utf8(path: Path, data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        _refuse({
            "code": "manual_intervention",
            "detail": f"{path} is not valid UTF-8 ({exc}) — refusing to "
                      f"touch it (FIX-278: governance files are UTF-8; fix "
                      f"the file encoding first)",
        })


def _line_ending_of(data: bytes) -> str:
    return "\r\n" if data.endswith(b"\r\n") else "\n"


def _fsync_dir(path: Path) -> None:
    """Best-effort directory fsync after a replace (POSIX crash
    durability nicety; Windows disallows opening directories — swallowed).
    """
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


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Same-directory temp file + fsync + os.replace + dir fsync (DoD 3)."""
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        _fsync_dir(path.parent)
    except BaseException:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def _split_row(line: str):
    """Split a markdown table row ignoring pipes inside inline code spans.

    Same semantics as the engine's Check-14 splitter (code-span aware, no
    backslash-escape support): the leading/trailing empty parts of the
    ``| … |`` form are dropped and cell text is stripped.
    """
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    cells = []
    buf = []
    in_code = False
    end = len(stripped) - 1 if stripped.endswith("|") else len(stripped)
    i = 1
    while i < end:
        ch = stripped[i]
        if ch == "`":
            in_code = not in_code
            buf.append(ch)
        elif ch == "|" and not in_code:
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    cells.append("".join(buf).strip())
    return cells


def _render_row(cells) -> str:
    return "| " + " | ".join(cells) + " |"


def _normalize_path(path) -> str:
    return str(path or "").replace("\\", "/").strip()


# ── cross-process lock (stdlib, Windows + POSIX) ─────────────────────────────


def _inproc_mutex(key: str) -> threading.Lock:
    with _INPROC_GUARD:
        lock = _INPROC_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _INPROC_LOCKS[key] = lock
        return lock


class _TargetLock:
    """O_EXCL lockfile + in-process mutex; contention is retryable.

    Lock order discipline: the record target first, then the ledger —
    every code path acquires them in that order, so nesting cannot
    deadlock.

    Stale-takeover semantics (P3-2 disclosure, batch-2.0 FEAT-055): a
    lockfile whose mtime is older than ``_LOCK_STALE_SECONDS`` (600s) is
    unlinked by :meth:`_stale` and the acquire loop retries, so a crashed or
    pathologically slow holder does not wedge the target forever.  The
    disclosed boundary (review-FEAT-046-CODE-R0 P3-2, verified): the takeover
    keys on the lockfile PATH, not on ownership — a slow holder A that
    resumes after its stale lock was taken over still holds
    ``_acquired=True``, so its ``__exit__`` will unlink the SUCCESSOR's
    active lockfile, opening a transient mutual-exclusion erosion window
    (a third acquirer can then create a fresh lock while the successor is
    still inside).  Unreachable by a healthy single-file atomic write
    (<600s); the takeover exists as crash recovery, not a scheduling
    feature, and fixing the ownership gap belongs to a lock-surface slice,
    not to wiring.
    """

    def __init__(self, target: Path, timeout_seconds: float = 10.0):
        lock_dir = target.parent / LOCK_DIR_NAME
        lock_dir.mkdir(parents=True, exist_ok=True)
        self.path = lock_dir / (target.name + ".lock")
        self.timeout_seconds = timeout_seconds
        self._inproc = _inproc_mutex(str(self.path))
        self._acquired = False

    def __enter__(self):
        self._inproc.acquire()
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode("ascii"))
                os.close(fd)
                self._acquired = True
                return self
            except FileExistsError:
                if self._stale():
                    continue
                if time.monotonic() >= deadline:
                    self._inproc.release()
                    _refuse({
                        "code": "lock_contention",
                        "detail": f"target lock busy: {self.path} — retry "
                                  f"the same operation (transient, "
                                  f"disposition retryable)",
                    })
                time.sleep(_LOCK_POLL_SECONDS)

    def _stale(self) -> bool:
        try:
            age = time.time() - self.path.stat().st_mtime
        except OSError:
            return False
        if age > _LOCK_STALE_SECONDS:
            try:
                self.path.unlink()
            except OSError:
                pass
            return True
        return False

    def __exit__(self, *exc_info):
        if self._acquired:
            try:
                self.path.unlink()
            except OSError:
                pass
        self._inproc.release()
        return False


# ── operation ledger ─────────────────────────────────────────────────────────


def _ledger_path(governance_dir: Path) -> Path:
    return Path(governance_dir) / LEDGER_FILE_NAME


def _load_ledger(governance_dir: Path):
    path = _ledger_path(governance_dir)
    if not path.is_file():
        return {"schema_version": SCHEMA_VERSION, "operations": {}}
    try:
        loaded = json.loads(_decode_utf8(path, _read_bytes(path)))
    except ValueError as exc:
        _refuse({
            "code": "manual_intervention",
            "detail": f"{path} is not valid JSON ({exc}) — refusing to "
                      f"operate fail-closed; repair or remove the ledger",
        })
    if (not isinstance(loaded, dict)
            or not isinstance(loaded.get("operations"), dict)):
        _refuse({
            "code": "manual_intervention",
            "detail": f"{path} must be an object with an 'operations' "
                      f"object — refusing fail-closed",
        })
    for op_id, entry in loaded["operations"].items():
        if not isinstance(entry, dict) or entry.get("status") not in (
                "ok", "pending"):
            _refuse({
                "code": "manual_intervention",
                "detail": f"{path}: ledger entry {op_id!r} is malformed — "
                          f"refusing fail-closed",
            })
        try:
            require_input_fingerprint(
                f"{path}: entry {op_id!r}",
                entry.get("input_fingerprint"))
        except ContractViolation as exc:
            # A tampered/truncated fingerprint would make
            # decide_operation_replay treat the op as unseen ("execute")
            # and double-apply a locks mutation — fail closed instead.
            _refuse({
                "code": "manual_intervention",
                "detail": f"{path}: ledger entry {op_id!r} carries an "
                          f"invalid input_fingerprint ({exc}) — refusing "
                          f"fail-closed; repair or remove the ledger entry",
            })
    return loaded


def _ledger_transaction(governance_dir: Path, mutate, timeout_seconds=10.0):
    """Read-mutate-write the ledger under the ledger lock (lock order:
    callers already hold their record-target lock; ledger is innermost)."""
    with _TargetLock(_ledger_path(governance_dir), timeout_seconds):
        ledger = _load_ledger(governance_dir)
        result = mutate(ledger)
        _atomic_write_bytes(
            _ledger_path(governance_dir),
            (json.dumps(ledger, ensure_ascii=False, indent=2)
             + "\n").encode("utf-8"))
        return result


def _replay_payload(entry: dict, source="ledger") -> dict:
    stored = entry["result"]
    result = WriterResult(
        operation_id=stored["operation_id"],
        code=stored["code"],
        new_revision=stored.get("new_revision"),
        observed_revision=stored.get("observed_revision"),
        execution=stored.get("execution"),
        detail=stored.get("detail"),
    )
    return _result_dict(
        result,
        disposition=ERROR_CODE_DISPOSITIONS.get(result.code),
        error=result.code != RESULT_OK,
        replayed=True,
        replay_source=source,
    )


def _ledger_entry(op_id, command, task_id, fingerprint, *, status, revision,
                  now, pending_effects=None, baseline_effects=None):
    timestamp = now.replace(microsecond=0).isoformat()
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "task_id": task_id,
        "input_fingerprint": fingerprint,
        "status": status,
        "result": {"operation_id": op_id, "code": RESULT_OK,
                   "new_revision": revision, "observed_revision": None,
                   "execution": "succeeded" if status == "ok" else None,
                   "detail": None},
        "pending_effects": pending_effects,
        "baseline_effects": baseline_effects,
        "recorded_at": timestamp,
        "updated_at": timestamp,
    }


# ── shared append pipeline (B-5 / B-2) ───────────────────────────────────────


def _append_context(governance_dir, repo_root, file_name):
    governance_dir = Path(governance_dir)
    target = governance_dir / file_name
    if not target.is_file():
        _refuse({
            "code": "manual_intervention",
            "detail": f"{target} does not exist — governance hot files are "
                      f"created by governance init, never by an append",
        })
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    return governance_dir, target, root


def _scan_archive_ids(governance_dir: Path, prefix: str):
    """Collect ``PREFIX-<n>`` numbers from the archive tree (collision)."""
    numbers = set()
    archive = governance_dir / ARCHIVE_DIR_NAME
    if not archive.is_dir():
        return numbers
    pattern = re.compile(r"\b" + re.escape(prefix) + r"(\d+)\b")
    for path in archive.rglob("*.md"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        numbers.update(int(match) for match in pattern.findall(text))
    return numbers


def _hot_id_numbers(text: str, prefix: str):
    """Row-anchored hot-file ID scan (markdown rows start with ``| ``)."""
    pattern = re.compile(r"^\s*\|?\s*" + re.escape(prefix) + r"(\d+)\b",
                         re.M)
    return [int(match) for match in pattern.findall(text)]


def _next_row_id(governance_dir: Path, text: str, prefix: str):
    """max(hot) + 1 with a hot∪archive collision refusal (Check 13 caliber:
    appending max+1 can only shrink existing gaps, never create one, and a
    collision with an archived id is refused instead of duplicated)."""
    numbers = _hot_id_numbers(text, prefix)
    next_number = (max(numbers) + 1) if numbers else 1
    candidate = f"{prefix}{next_number}"
    if next_number in _scan_archive_ids(governance_dir, prefix) \
            or candidate in text:
        _refuse({
            "code": "cross_record_violation",
            "detail": f"next id {candidate} collides with an existing "
                      f"record (hot text or archive) — ID continuity would "
                      f"break; resolve the collision manually",
        })
    return candidate


def _validate_row_shape(row_text, *, expected_columns, mandatory):
    """The ONE row validator — used pre-write and post-write (DoD 1/4)."""
    if "\n" in row_text.strip():
        _refuse({
            "code": "schema_violation",
            "detail": "rendered row spans multiple lines — a newline got "
                      "into a cell",
        })
    cells = _split_row(row_text)
    if len(cells) != expected_columns:
        _refuse({
            "code": "schema_violation",
            "detail": f"row has {len(cells)} columns, expected "
                      f"{expected_columns} — a raw '|' outside an inline "
                      f"code span changes the shape; reword, use the "
                      f"full-width ｜, or wrap the segment in backticks",
        })
    for index in range(mandatory):
        if not cells[index]:
            _refuse({
                "code": "schema_violation",
                "detail": f"mandatory cell {index + 1}/{expected_columns} "
                          f"is empty",
            })
    return cells


def _cells_no_newline(where, cells):
    for index, cell in enumerate(cells):
        if "\n" in cell or "\r" in cell:
            _refuse({
                "code": "schema_violation",
                "detail": f"{where}[{index}]: newline in cell — a row is a "
                          f"single line; reword the payload",
            })


def _post_write_append_check(target, original, row_text, op_id, marker,
                             validator):
    """DoD 4 — re-read; prefix comparison + SAME validator (no second schema).

    A prefix mismatch means a concurrent writer changed the file between our
    read and the replace — disclosed, never auto-restored (arch round-2 §5:
    恢复受版本检查保护).
    """
    current = _read_bytes(target)
    if not current.startswith(original):
        _refuse({
            "code": "manual_intervention",
            "detail": f"post-write reread: {target} byte prefix changed "
                      f"(concurrent write?) — DISCLOSING, not restoring; "
                      f"verify the file before further writes "
                      f"(operation {op_id})",
        })
    text = _decode_utf8(target, current)
    if marker not in text:
        _refuse({
            "code": "manual_intervention",
            "detail": f"post-write reread: appended row (operation "
                      f"{op_id}) not found in {target}",
        })
    appended_line = row_text.strip()
    if appended_line not in text:
        _refuse({
            "code": "manual_intervention",
            "detail": f"post-write reread: row text mismatch in {target}",
        })
    validator(appended_line, op_id)


def _append_row_bytes(original: bytes, row_text: str) -> bytes:
    ending = _line_ending_of(original)
    prefix_newline = b"" if original.endswith(b"\n") else b"\n"
    return original + prefix_newline + (row_text + ending).encode("utf-8")


def _dry_run_append(target, row_builder, *, validator, op_id,
                    fingerprint, checked_refs):
    """DoD 5 — full parse + validation, ZERO writes (no lock, no ledger).

    The row is built through the SAME collision-checked id assignment as a
    real write (``row_builder`` calls ``_next_row_id``), so a dry-run PASS
    predicts the real write on the id-continuity leg too (P2-1).
    """
    text = _decode_utf8(target, _read_bytes(target))
    row_text = row_builder(text)
    validator(row_text, op_id)
    return {
        "dry_run": True,
        "operation_id": op_id,
        "input_fingerprint": fingerprint,
        "next_id": _split_row(row_text)[0],
        "row": row_text,
        "refs": checked_refs,
        "target": str(target),
        "bytes_written": 0,
        "code": RESULT_OK,
        "error": False,
    }


# ── typed reference machine-check (arch round-2 §3) ──────────────────────────


def _parse_refs(raw) -> list:
    """Parse ``kind:value`` pairs (CLI aliases normalized to contract kinds)."""
    if raw in (None, ""):
        return []
    if not isinstance(raw, (list, tuple)):
        _refuse({
            "code": "schema_violation",
            "detail": "--refs must be a list of kind:value strings",
        })
    refs = []
    for index, item in enumerate(raw):
        text = _require_text(f"--refs[{index}]", item)
        kind, separator, value = text.partition(":")
        if not separator or not value.strip():
            _refuse({
                "code": "schema_violation",
                "detail": f"--refs[{index}]: expected kind:value, got "
                          f"{text!r}",
            })
        kind = _KIND_ALIASES.get(kind.strip(), kind.strip())
        try:
            refs.append(EvidenceRef(kind=kind, value=value.strip()))
        except ContractViolation as exc:
            _refuse({
                "code": "schema_violation",
                "detail": f"--refs[{index}]: contract violation — {exc}",
            })
    return refs


def _validate_ref(ref: EvidenceRef, repo_root: Path, governance_dir: Path):
    """Machine-check one typed reference → (state, detail).

    Resolvability ONLY (never a sufficiency verdict); URL refs are never
    fetched; ``git_object`` is form-checked before any subprocess and the
    subprocess is one argv-list git rev-parse (no shell).
    """
    kind, value = ref.kind, ref.value
    if kind == "repo_file":
        # P3-4 (review-FEAT-046-CODE-R0; batch-2.0 read-side tightening,
        # FEAT-055): the value must resolve INSIDE the repo root — an
        # absolute path or a ``..``-prefixed escape used to pass a bare
        # existence test against anything the process can see.  Still a
        # read-only check (``is_file``); an escaping path now reports
        # unresolvable, which the caller refuses on (cross_record_violation).
        candidate = repo_root / value.replace("\\", "/")
        try:
            resolved = candidate.resolve()
            inside = resolved.is_relative_to(Path(repo_root).resolve())
        except (ValueError, OSError):
            inside = False
        if not inside:
            return ("unresolvable",
                    f"path escapes the repo root: {value}")
        if resolved.is_file():
            return "resolvable", "path exists"
        return "unresolvable", f"path does not exist: {value}"
    if kind == "git_object":
        if not _GIT_OBJECT_RE.match(value):
            return ("unresolvable",
                    "expected 7-40 hex chars or HEAD/~N form")
        try:
            proc = subprocess.run(
                ["git", "-C", str(repo_root), "rev-parse", "--quiet",
                 "--verify", value],
                capture_output=True, timeout=15)
        except (OSError, subprocess.SubprocessError):
            return ("not_yet_verifiable",
                    "git unavailable — resolvability not decided")
        if proc.returncode == 0:
            return "resolvable", "object parses"
        return "unresolvable", "git rev-parse could not verify the object"
    if kind == "governance_id":
        return _validate_governance_id(value, governance_dir)
    if kind == "url":
        parts = urllib.parse.urlsplit(value)
        if (parts.scheme in ("http", "https") and parts.netloc
                and all(ch.isprintable() and not ch.isspace()
                        for ch in value)):
            return ("resolvable",
                    "URL syntax valid (not fetched — no network by design)")
        return "unresolvable", "URL must be an absolute http(s) URL"
    if kind == "human_observation":
        # Content non-empty is the only mechanical face (already enforced by
        # EvidenceRef); the state is machine-stamped not_yet_verifiable so
        # the row cannot pretend a machine verification happened.
        return ("not_yet_verifiable",
                "human observation — machine-unchecked by design")
    _refuse({
        "code": "schema_violation",
        "detail": f"unknown evidence reference kind {kind!r} "
                  f"(closed enum {EVIDENCE_REF_KINDS})",
    })


def _validate_governance_id(value, governance_dir: Path):
    """Mention-level hot+archive search → (state, detail).

    P3-3 disclosure (batch-2.0 FEAT-055): the match is a ``\\b``-delimited
    substring search over whole files, NOT row-anchored — a mention in prose
    is enough to report ``resolvable`` (asymmetric with the row-anchored
    ``_hot_id_numbers`` used for ID allocation).  Under the
    resolvability-only contract this cannot fabricate a sufficiency verdict;
    row-anchored tightening would change the resolvable face of existing
    legitimate references and is therefore deferred deliberately.
    """
    match = re.match(r"^([A-Z]+)-(\d+)$", value)
    if match is None:
        return "unresolvable", "expected FAMILY-NUMBER form (e.g. DEC-221)"
    family = match.group(1)
    files = _GOVERNANCE_ID_FAMILIES.get(family)
    if files is None:
        return ("unresolvable",
                f"unknown governance id family {family!r} "
                f"(known: {sorted(_GOVERNANCE_ID_FAMILIES)})")
    pattern = re.compile(r"\b" + re.escape(value) + r"\b")
    for name in files:
        path = governance_dir / name
        if path.is_file() and pattern.search(
                _decode_utf8(path, _read_bytes(path))):
            return "resolvable", f"found in {name}"
    archive = governance_dir / ARCHIVE_DIR_NAME
    if archive.is_dir():
        for path in archive.rglob("*.md"):
            try:
                if pattern.search(path.read_text(
                        encoding="utf-8", errors="replace")):
                    return "resolvable", f"found in archive: {path.name}"
            except OSError:
                continue
    return "unresolvable", f"{value} not found in {files} or archive"


def _validate_refs(refs, repo_root, governance_dir):
    checked = []
    for ref in refs:
        state, detail = _validate_ref(ref, repo_root, governance_dir)
        if state not in REFERENCE_VALIDATION_STATES:
            _refuse({
                "code": "schema_violation",
                "detail": f"reference validation state {state!r} is outside "
                          f"the frozen three-state enum "
                          f"{REFERENCE_VALIDATION_STATES} — contract drift",
            })
        if state == "unresolvable":
            _refuse({
                "code": "cross_record_violation",
                "detail": f"reference {ref.kind}:{ref.value} is "
                          f"unresolvable ({detail}) — fix or drop the ref "
                          f"(per-kind refusal: machine-checkable kinds must "
                          f"resolve; url is syntax-only; human observation "
                          f"is never machine-refused)",
            })
        checked.append({"kind": ref.kind, "value": ref.value,
                        "validation": state, "detail": detail})
    return checked


# ── evidence-append (B-5) ────────────────────────────────────────────────────


def _build_evidence_row(*, evd_id, task_id, evd_type, description, basis,
                        artifacts, actor, date_str, gate, conclusion, refs,
                        op_id):
    marker = (f"（机器写入：governance-store evidence-append {op_id}；"
              f"schema v{SCHEMA_VERSION}）")
    basis_cell = f"事实依据：{basis} {marker}".strip()
    refs_cell = artifacts
    if refs:
        rendered = "; ".join(
            f"refs[{item['kind']}:{item['value']}={item['validation']}]"
            for item in refs)
        refs_cell = f"{artifacts}；{rendered}" if artifacts else rendered
    cells = [evd_id, task_id, evd_type, description, basis_cell, refs_cell,
             actor, date_str, gate, conclusion]
    _cells_no_newline("evidence cell", cells)
    row_text = _render_row(cells)
    _validate_row_shape(row_text, expected_columns=EVIDENCE_COLUMNS,
                        mandatory=EVIDENCE_COLUMNS)
    return row_text, cells


def _validate_evidence_content(cells):
    """Skeleton-only content checks (W-4: NO semantic scanning beyond the
    two mirrored engine skeleton rules)."""
    goal = _GOAL_ALIGNMENT_RE.search(cells[3])
    if goal is None:
        _refuse({
            "code": "schema_violation",
            "detail": "description lacks a 目标对齐： field (Check 16 "
                      "skeleton) — the goal-alignment passage is part of "
                      "the mandatory row skeleton",
        })
    goal_text = goal.group(1).strip()
    if len(goal_text) < 30:
        _refuse({
            "code": "schema_violation",
            "detail": f"目标对齐 passage is {len(goal_text)} chars, "
                      f"needs >= 30 (Check 16 mirrored rule)",
        })
    basis_payload = _FACT_BASIS_RE.search(cells[4])
    if basis_payload is None or not basis_payload.group(1).strip():
        _refuse({
            "code": "schema_violation",
            "detail": "basis cell must carry a non-empty 事实依据： payload",
        })


def _evidence_row_validator(row_text, op_id):
    cells = _validate_row_shape(row_text, expected_columns=EVIDENCE_COLUMNS,
                                mandatory=EVIDENCE_COLUMNS)
    _validate_evidence_content(cells)
    if f"evidence-append {op_id}" not in row_text:
        _refuse({
            "code": "manual_intervention",
            "detail": "row lost its machine provenance marker",
        })


@_returns_payload
def evidence_append(*, task_id, evd_type, description, basis, artifacts="",
                    actor="governance-store", date=None, gate="G11",
                    conclusion="✅ 完成", refs=(), governance_dir,
                    repo_root=None, operation_id=None, dry_run=False,
                    now=None, expected_revision=None, timeout_seconds=10.0):
    """B-5: append one machine EVD row — skeleton hard-validated.

    Mechanical skeleton only: ID continuity (max hot + 1, archive collision
    refused), ISO date, 10-column shape with all cells non-empty, 目标对齐
    ≥ 30 chars, non-empty 事实依据 basis, typed ``--refs`` machine-checked
    per kind with the ``reference_validation`` state recorded IN the row.
    """
    now = now if now is not None else datetime.now()
    op_id = require_operation_id("evidence_append", operation_id) \
        if operation_id else new_operation_id()
    task_id = _require_text("--task", task_id)
    if not _TASK_ID_RE.match(task_id):
        _refuse({
            "code": "schema_violation",
            "detail": f"task id {task_id!r} must match PREFIX-NNN",
        })
    evd_type = _require_text("--type", evd_type)
    description = _require_text("--description", description)
    basis = _require_text("--basis", basis)
    actor = _require_text("--actor", actor)
    gate = _require_text("--gate", gate)
    conclusion = _require_text("--conclusion", conclusion)
    date_str = _require_date("--date", date) if date \
        else now.date().isoformat()
    if expected_revision is not None:
        _require_int("--expected-revision", expected_revision)
    SCHEMA_WINDOW.require_supported("evidence_append", SCHEMA_VERSION)
    typed_refs = _parse_refs(list(refs))
    governance_dir, target, root = _append_context(
        governance_dir, repo_root, EVIDENCE_FILE_NAME)
    checked_refs = _validate_refs(typed_refs, root, governance_dir)
    fingerprint = _fingerprint({
        "command": "evidence-append", "task": task_id, "type": evd_type,
        "description": description, "basis": basis, "artifacts": artifacts,
        "actor": actor, "date": date_str, "gate": gate,
        "conclusion": conclusion,
        "refs": [{"kind": r.kind, "value": r.value} for r in typed_refs],
    })
    marker = f"governance-store evidence-append {op_id}"

    def build(text):
        row, _cells = _build_evidence_row(
            evd_id=_next_row_id(governance_dir, text, EVD_ROW_PREFIX),
            task_id=task_id,
            evd_type=evd_type, description=description, basis=basis,
            artifacts=artifacts, actor=actor, date_str=date_str, gate=gate,
            conclusion=conclusion, refs=checked_refs, op_id=op_id)
        return row

    if dry_run:
        return _dry_run_append(
            target, build,
            validator=_evidence_row_validator, op_id=op_id,
            fingerprint=fingerprint, checked_refs=checked_refs)

    with _TargetLock(target, timeout_seconds):
        original = _read_bytes(target)
        if not original.strip():
            # An empty hot file is a degenerate world (the init template
            # carries a header): refuse at entry — an empty world also
            # cannot back the CAS observed-revision channel (observed 0
            # violates the positive-int invariant).
            _refuse({
                "code": "schema_violation",
                "detail": f"{target} is empty — not a valid governance hot "
                          f"file; refuse to append (create it via "
                          f"governance init first)",
            })
        if expected_revision is not None \
                and expected_revision != len(original):
            _refuse(_error_result(
                op_id, "revision_conflict",
                f"expected revision {expected_revision} != observed "
                f"{len(original)} — re-read the target and re-judge",
                observed_revision=len(original)))
        text = _decode_utf8(target, original)
        ledger = _load_ledger(governance_dir)
        existing = ledger["operations"].get(op_id)
        if existing is not None:
            decision = decide_operation_replay(
                existing.get("input_fingerprint"), fingerprint)
            if decision == "replay":
                return _replay_payload(existing)
            _refuse(_error_result(
                op_id, "operation_id_conflict",
                "operation id already recorded with a DIFFERENT payload — "
                "mint a new operation id (a stored result is never reused "
                "for a different payload)",
                observed_revision=len(original)))
        # Ledger miss: the world decides (查世界不信日志). A row carrying
        # this operation marker is a crashed prior attempt — recover,
        # never re-append.
        if marker in text:
            _recover_append(
                governance_dir, op_id, "evidence-append", task_id,
                fingerprint, marker, len(original), now)
            return _replay_payload(
                {"result": {"operation_id": op_id, "code": RESULT_OK,
                            "new_revision": len(original),
                            "observed_revision": None,
                            "execution": "succeeded", "detail": None}},
                source="world_recovery")
        evd_id = _next_row_id(governance_dir, text, EVD_ROW_PREFIX)
        row_text, _cells = _build_evidence_row(
            evd_id=evd_id, task_id=task_id, evd_type=evd_type,
            description=description, basis=basis, artifacts=artifacts,
            actor=actor, date_str=date_str, gate=gate, conclusion=conclusion,
            refs=checked_refs, op_id=op_id)
        new_bytes = _append_row_bytes(original, row_text)
        _atomic_write_bytes(target, new_bytes)
        _post_write_append_check(
            target, original, row_text, op_id, marker,
            validator=_evidence_row_validator)
        revision = len(_read_bytes(target))

        def record(operation_ledger):
            operation_ledger["operations"][op_id] = _ledger_entry(
                op_id, "evidence-append", task_id, fingerprint,
                status="ok", revision=revision, now=now)

        _ledger_transaction(governance_dir, record, timeout_seconds)
        return _ok_result(
            op_id, revision, detail=f"appended {evd_id} to {target}",
            row_id=evd_id, command="evidence-append",
            idempotency_model=IDEMPOTENCY_MODEL)


def _recover_append(governance_dir, op_id, command, task_id, fingerprint,
                    marker, revision, now):
    """Crash recovery: the row is in the world, the ledger missed it —
    record the operation as done (idempotent, no re-append)."""

    def record(operation_ledger):
        if op_id in operation_ledger["operations"]:
            return
        operation_ledger["operations"][op_id] = _ledger_entry(
            op_id, command, task_id, fingerprint, status="ok",
            revision=revision, now=now)
        operation_ledger["operations"][op_id]["result"]["detail"] = (
            f"recovered from world state (marker present)")

    _ledger_transaction(governance_dir, record)


# ── decision-append (B-2) ────────────────────────────────────────────────────


def _build_decision_row(*, dec_id, date_str, decider, content, basis, op_id):
    marker = (f"（机器写入：governance-store decision-append {op_id}；"
              f"schema v{SCHEMA_VERSION}）")
    basis_cell = f"{basis} {marker}".strip() if basis else marker
    cells = [dec_id, date_str, decider, content, basis_cell]
    _cells_no_newline("decision cell", cells)
    row_text = _render_row(cells)
    _validate_row_shape(row_text, expected_columns=DEC_COLUMNS,
                        mandatory=DEC_MANDATORY_CELLS)
    return row_text


def _decision_row_validator(row_text, op_id):
    cells = _validate_row_shape(row_text, expected_columns=DEC_COLUMNS,
                                mandatory=DEC_MANDATORY_CELLS)
    if not _DATE_RE.match(cells[1]):
        _refuse({
            "code": "schema_violation",
            "detail": f"decision date cell {cells[1]!r} is not ISO "
                      f"YYYY-MM-DD",
        })
    if f"decision-append {op_id}" not in row_text:
        _refuse({
            "code": "manual_intervention",
            "detail": "row lost its machine provenance marker",
        })


@_returns_payload
def decision_append(*, decider, content, basis="", date=None,
                    governance_dir, repo_root=None, operation_id=None,
                    dry_run=False, now=None, expected_revision=None,
                    timeout_seconds=10.0):
    """B-2: append one machine DEC row (ID 连续 / 日期 / 决策者 / 内容).

    The live hot-file row shape is 5 cells (DEC-147…DEC-221 convention);
    the four mandatory cells 编号/日期/决策人/决策内容 must be non-empty; the
    trailing 依据 cell is present and carries the machine provenance
    marker.  Appends at end-of-file — the live convention for new rows.
    """
    now = now if now is not None else datetime.now()
    op_id = require_operation_id("decision_append", operation_id) \
        if operation_id else new_operation_id()
    decider = _require_text("--decider", decider)
    content = _require_text("--content", content)
    if basis is None:
        basis = ""
    if not isinstance(basis, str):
        _refuse({
            "code": "schema_violation",
            "detail": f"--basis must be a string, got "
                      f"{type(basis).__name__}",
        })
    date_str = _require_date("--date", date) if date \
        else now.date().isoformat()
    if expected_revision is not None:
        _require_int("--expected-revision", expected_revision)
    SCHEMA_WINDOW.require_supported("decision_append", SCHEMA_VERSION)
    governance_dir, target, _root = _append_context(
        governance_dir, repo_root, DECISION_FILE_NAME)
    fingerprint = _fingerprint({
        "command": "decision-append", "decider": decider,
        "content": content, "basis": basis, "date": date_str,
    })
    marker = f"governance-store decision-append {op_id}"

    def build(text):
        return _build_decision_row(
            dec_id=_next_row_id(governance_dir, text, DEC_ROW_PREFIX),
            date_str=date_str,
            decider=decider, content=content, basis=basis, op_id=op_id)

    if dry_run:
        return _dry_run_append(
            target, build,
            validator=_decision_row_validator, op_id=op_id,
            fingerprint=fingerprint, checked_refs=[])

    with _TargetLock(target, timeout_seconds):
        original = _read_bytes(target)
        if not original.strip():
            # An empty hot file is a degenerate world (the init template
            # carries a header): refuse at entry — an empty world also
            # cannot back the CAS observed-revision channel (observed 0
            # violates the positive-int invariant).
            _refuse({
                "code": "schema_violation",
                "detail": f"{target} is empty — not a valid governance hot "
                          f"file; refuse to append (create it via "
                          f"governance init first)",
            })
        if expected_revision is not None \
                and expected_revision != len(original):
            _refuse(_error_result(
                op_id, "revision_conflict",
                f"expected revision {expected_revision} != observed "
                f"{len(original)} — re-read the target and re-judge",
                observed_revision=len(original)))
        text = _decode_utf8(target, original)
        ledger = _load_ledger(governance_dir)
        existing = ledger["operations"].get(op_id)
        if existing is not None:
            decision = decide_operation_replay(
                existing.get("input_fingerprint"), fingerprint)
            if decision == "replay":
                return _replay_payload(existing)
            _refuse(_error_result(
                op_id, "operation_id_conflict",
                "operation id already recorded with a DIFFERENT payload — "
                "mint a new operation id",
                observed_revision=len(original)))
        if marker in text:
            _recover_append(
                governance_dir, op_id, "decision-append", "", fingerprint,
                marker, len(original), now)
            return _replay_payload(
                {"result": {"operation_id": op_id, "code": RESULT_OK,
                            "new_revision": len(original),
                            "observed_revision": None,
                            "execution": "succeeded", "detail": None}},
                source="world_recovery")
        dec_id = _next_row_id(governance_dir, text, DEC_ROW_PREFIX)
        row_text = _build_decision_row(
            dec_id=dec_id, date_str=date_str, decider=decider,
            content=content, basis=basis, op_id=op_id)
        new_bytes = _append_row_bytes(original, row_text)
        _atomic_write_bytes(target, new_bytes)
        _post_write_append_check(
            target, original, row_text, op_id, marker,
            validator=_decision_row_validator)
        revision = len(_read_bytes(target))

        def record(operation_ledger):
            operation_ledger["operations"][op_id] = _ledger_entry(
                op_id, "decision-append", "", fingerprint, status="ok",
                revision=revision, now=now)

        _ledger_transaction(governance_dir, record, timeout_seconds)
        return _ok_result(
            op_id, revision, detail=f"appended {dec_id} to {target}",
            row_id=dec_id, command="decision-append",
            idempotency_model=IDEMPOTENCY_MODEL)


# ── agent-locks pipeline (acquire-pipeline schema reuse — B-3) ───────────────


def _validate_locks_schema(data):
    """Mirror of the Check 26 validator — the same fields the acquire
    pipeline writes are the fields required here (no second schema)."""
    issues = []
    for task_id, entry in data["active_tasks"].items():
        if not isinstance(entry, dict):
            issues.append(f"active_tasks[{task_id}] must be a dict")
            continue
        for key in ("spawned_at", "coordinator_session", "target_files"):
            if key not in entry:
                issues.append(f"active_tasks[{task_id}] missing '{key}'")
        if "target_files" in entry and not isinstance(
                entry["target_files"], list):
            issues.append(
                f"active_tasks[{task_id}].target_files must be a list")
    for file_path, entry in data["file_locks"].items():
        if not isinstance(entry, dict):
            issues.append(f"file_locks[{file_path}] must be a dict")
            continue
        for key in ("locked_by", "locked_at", "ttl_seconds", "ttl_reason"):
            if key not in entry:
                issues.append(f"file_locks[{file_path}] missing '{key}'")
        if "ttl_seconds" in entry and not isinstance(
                entry["ttl_seconds"], (int, float)):
            issues.append(
                f"file_locks[{file_path}].ttl_seconds must be a number")
        if "expected_new" in entry and not isinstance(
                entry["expected_new"], bool):
            issues.append(
                f"file_locks[{file_path}].expected_new must be a boolean")
    return issues


def locks_load(governance_dir, locks_path=None):
    """Load agent-locks.json with acquire-pipeline fail-closed sanity."""
    path = Path(locks_path) if locks_path is not None \
        else Path(governance_dir) / LOCKS_FILE_NAME
    raw = _read_bytes(path)
    if not raw.strip():
        _refuse({
            "code": "manual_intervention",
            "detail": f"{path} is empty — refusing fail-closed",
        })
    try:
        loaded = json.loads(_decode_utf8(path, raw))
    except ValueError as exc:
        _refuse({
            "code": "manual_intervention",
            "detail": f"{path} is not valid JSON ({exc}) — refusing to "
                      f"merge fail-closed; fix the file first",
        })
    if not isinstance(loaded, dict):
        _refuse({
            "code": "manual_intervention",
            "detail": f"{path} root must be a JSON object",
        })
    data = {"active_tasks": {}, "file_locks": {}}
    for key in ("active_tasks", "file_locks"):
        value = loaded.get(key, {})
        if not isinstance(value, dict):
            _refuse({
                "code": "manual_intervention",
                "detail": f"{path} '{key}' must be a JSON object",
            })
        data[key] = dict(value)
    issues = _validate_locks_schema(data)
    if issues:
        _refuse({
            "code": "manual_intervention",
            "detail": f"{path} violates the Check 26 schema: "
                      + "; ".join(issues),
        })
    return path, data


def _locks_common(task_id):
    task_id = _require_text("--task", task_id)
    if not _TASK_ID_RE.match(task_id):
        _refuse({
            "code": "schema_violation",
            "detail": f"task id {task_id!r} must match PREFIX-NNN",
        })
    return task_id


def _locks_ttl_args(ttl_seconds, extend_by, *, required):
    if ttl_seconds is not None and extend_by is not None:
        _refuse({
            "code": "schema_violation",
            "detail": "--ttl-seconds (absolute) and --extend-by (delta) "
                      "are mutually exclusive",
        })
    if required and ttl_seconds is None and extend_by is None:
        _refuse({
            "code": "schema_violation",
            "detail": "exactly one of --ttl-seconds (absolute) or "
                      "--extend-by (delta) is required",
        })
    if ttl_seconds is not None:
        _require_int("--ttl-seconds", ttl_seconds)
    if extend_by is not None:
        _require_int("--extend-by", extend_by)


def _snapshot_lock_fields(data, file_paths):
    snapshot = {}
    for file_path in file_paths:
        entry = data["file_locks"].get(file_path)
        if isinstance(entry, dict):
            snapshot[file_path] = {
                key: entry[key] for key in
                ("locked_by", "locked_at", "ttl_seconds", "ttl_reason",
                 "expected_new") if key in entry}
    return snapshot


def _state_matches(data, state) -> bool:
    """Effect-based world judgment: does the live locks data equal ``state``?

    An empty per-file snapshot means "file not locked" (the baseline of an
    amend --add-file, the target of a release); ``active_tasks`` list
    fields compare as lists.  A ``None`` active_tasks field is release's
    absence marker: the keyed entry must be GONE (extend/amend never
    record ``None``, so their recorded states are judged unchanged).
    """
    if not isinstance(state, dict) or not state:
        return False
    for file_path, fields in (state.get("file_locks") or {}).items():
        entry = data["file_locks"].get(file_path)
        if not fields:
            if entry is not None:
                return False
            continue
        if not isinstance(entry, dict):
            return False
        for key, value in fields.items():
            if entry.get(key) != value:
                return False
    for task_id, fields in (state.get("active_tasks") or {}).items():
        entry = data["active_tasks"].get(task_id)
        if fields is None:
            if entry is not None:
                return False
            continue
        if not isinstance(entry, dict):
            return False
        for key, value in fields.items():
            if list(entry.get(key, [])) != list(value):
                return False
    return True


def _locks_execute(governance_dir, op_id, fingerprint, task_id, mutator,
                   effects_of, *, command, now, timeout_seconds,
                   holds_lock=None):
    """Shared locks apply: world-judged resume → apply → verify → ok.

    The ledger records target AND baseline state; a re-run judges the world
    (never the log): world==target → complete; world==baseline (crash
    before apply) → re-apply the deterministic mutator and complete;
    anything else → manual_intervention.  No double-apply, no half state.

    ``holds_lock`` (locks-release, FIX-370): a predicate over the live
    data replacing the family default ownership guard for NEW operations —
    the guard still runs AFTER the replay/resume legs, so a replay of a
    completed release stays a success no-op.  ``None`` keeps the default:
    the task must hold an active_tasks entry.
    """
    ledger = _load_ledger(governance_dir)
    existing = ledger["operations"].get(op_id)
    path, data = locks_load(governance_dir)
    if existing is not None:
        decision = decide_operation_replay(
            existing.get("input_fingerprint"), fingerprint)
        if decision == "conflict":
            _refuse(_error_result(
                op_id, "operation_id_conflict",
                "operation id already recorded with a DIFFERENT payload — "
                "mint a new operation id",
                observed_revision=len(_read_bytes(path))))
        if existing.get("status") == "ok":
            return _replay_payload(existing)
        if _state_matches(data, existing.get("pending_effects")):
            return _complete_pending(governance_dir, op_id, existing,
                                     source="resume")
        if _state_matches(data, existing.get("baseline_effects")):
            error = mutator(data, task_id)
            if error:
                _refuse(_error_result(op_id, *error))
            return _apply_locks(
                governance_dir, path, data, op_id, existing, now,
                timeout_seconds)
        _refuse(_error_result(
            op_id, "manual_intervention",
            "pending locks operation diverged from BOTH its recorded "
            "target and baseline state — re-judge manually (the ledger is "
            "never trusted over the world)"))

    if holds_lock is not None:
        if not holds_lock(data):
            _refuse(_error_result(
                op_id, "cross_record_violation",
                f"task {task_id} holds no dispatch lock (no active_tasks "
                f"entry, no file locks) — nothing to release"))
    elif task_id not in data["active_tasks"]:
        _refuse(_error_result(
            op_id, "cross_record_violation",
            f"task {task_id} holds no active dispatch lock — acquire "
            f"first (agent-locks-acquire)"))
    baseline = effects_of(data)
    error = mutator(data, task_id)
    if error:
        _refuse(_error_result(op_id, *error))
    issues = _validate_locks_schema(data)
    if issues:
        _refuse(_error_result(
            op_id, "schema_violation",
            "candidate agent-locks.json violates the Check 26 schema: "
            + "; ".join(issues)))
    target_state = effects_of(data)
    entry = _ledger_entry(
        op_id, command, task_id, fingerprint, status="pending",
        revision=None, now=now, pending_effects=target_state,
        baseline_effects=baseline)

    def stage(operation_ledger):
        operation_ledger["operations"][op_id] = entry

    _ledger_transaction(governance_dir, stage, timeout_seconds)
    return _apply_locks(governance_dir, path, data, op_id, entry, now,
                        timeout_seconds)


def _apply_locks(governance_dir, path, data, op_id, entry, now,
                 timeout_seconds):
    payload = (json.dumps(data, ensure_ascii=False, indent=4)
               + "\n").encode("utf-8")
    _atomic_write_bytes(path, payload)
    reread = _read_bytes(path)
    try:
        final_data = json.loads(_decode_utf8(path, reread))
    except ValueError as exc:
        _refuse(_error_result(
            op_id, "manual_intervention",
            f"post-write reread failed: {path} is not valid JSON ({exc}) — "
            f"the pending ledger entry records the operation; re-run the "
            f"same command to resume (effect-based)"))
    final_issues = _validate_locks_schema(final_data)
    if final_issues:
        _refuse(_error_result(
            op_id, "manual_intervention",
            "post-write reread violates the Check 26 schema: "
            + "; ".join(final_issues)))
    return _complete_pending(governance_dir, op_id, entry,
                             source="apply", revision=len(reread),
                             now=now, timeout_seconds=timeout_seconds)


def _complete_pending(governance_dir, op_id, entry, *, source,
                      revision=None, now=None, timeout_seconds=10.0):
    if revision is None:
        revision = len(_read_bytes(
            Path(governance_dir) / LOCKS_FILE_NAME))
    now = now if now is not None else datetime.now()

    def complete(operation_ledger):
        stored = operation_ledger["operations"].get(op_id)
        if stored is None:
            stored = entry
            operation_ledger["operations"][op_id] = stored
        stored["status"] = "ok"
        stored["result"]["execution"] = "succeeded"
        stored["result"]["new_revision"] = revision
        stored["pending_effects"] = None
        stored["baseline_effects"] = None
        stored["updated_at"] = now.replace(microsecond=0).isoformat()

    _ledger_transaction(governance_dir, complete, timeout_seconds)
    return _replay_payload(
        {"result": {"operation_id": op_id, "code": RESULT_OK,
                    "new_revision": revision, "observed_revision": None,
                    "execution": "succeeded", "detail": None}},
        source=source)


@_returns_payload
def locks_extend(*, task_id, files, ttl_seconds=None, extend_by=None,
                 reason, governance_dir, repo_root=None, operation_id=None,
                 now=None, timeout_seconds=10.0):
    """B-3: extend the TTL of existing file locks held by ``task_id``.

    The acquire pipeline's schema semantics are reused verbatim: the entry
    keeps ``locked_by`` / ``locked_at``; only ``ttl_seconds`` grows and
    ``ttl_reason`` records WHY (the 4 manual-append schema incidents of
    2026-09-19 are the incident class this command closes).
    """
    now = now if now is not None else datetime.now()
    op_id = require_operation_id("locks_extend", operation_id) \
        if operation_id else new_operation_id()
    SCHEMA_WINDOW.require_supported("locks_extend", SCHEMA_VERSION)
    task_id = _locks_common(task_id)
    _require_text("--reason", reason)
    _locks_ttl_args(ttl_seconds, extend_by, required=True)
    lock_files = sorted({_normalize_path(f) for f in (files or []) if f})
    if not lock_files:
        _refuse({
            "code": "schema_violation",
            "detail": "--files is required and must be non-empty",
        })
    governance_dir = Path(governance_dir)
    fingerprint = _fingerprint({
        "command": "locks-extend", "task": task_id, "files": lock_files,
        "ttl_seconds": ttl_seconds, "extend_by": extend_by, "reason": reason,
    })

    def mutate(data, owner):
        for file_path in lock_files:
            entry = data["file_locks"].get(file_path)
            if not isinstance(entry, dict):
                return ("cross_record_violation",
                        f"file {file_path} is not locked — nothing to "
                        f"extend")
            if entry.get("locked_by") != owner:
                return ("cross_record_violation",
                        f"file {file_path} is locked by "
                        f"{entry.get('locked_by')!r}, not {owner}")
            entry["ttl_seconds"] = (
                entry["ttl_seconds"] + extend_by
                if extend_by is not None else ttl_seconds)
            if entry["ttl_seconds"] <= 0:
                return ("schema_violation",
                        f"resulting ttl_seconds {entry['ttl_seconds']} for "
                        f"{file_path} is not positive")
            entry["ttl_reason"] = f"extend: {reason}"
        return None

    def effects_of(data):
        return {"file_locks": _snapshot_lock_fields(data, lock_files)}

    with _TargetLock(governance_dir / LOCKS_FILE_NAME, timeout_seconds):
        return _locks_execute(
            governance_dir, op_id, fingerprint, task_id, mutate, effects_of,
            command="locks-extend", now=now, timeout_seconds=timeout_seconds)


def _task_reference_entry(data, task_id):
    """The task's first own file-lock entry — TTL baseline for an add."""
    for entry in data["file_locks"].values():
        if isinstance(entry, dict) and entry.get("locked_by") == task_id:
            return entry
    return {"ttl_seconds": 14400}


@_returns_payload
def locks_amend(*, task_id, add_file=None, expected_new=False,
                ttl_seconds=None, extend_by=None, reason,
                governance_dir, repo_root=None, operation_id=None,
                now=None, timeout_seconds=10.0):
    """B-3: amend an existing dispatch lock — add a file or fix TTL fields.

    ``--add-file`` appends the target to the task's ``active_tasks``
    ``target_files``/``files`` lists AND writes a schema-correct
    ``file_locks`` entry (``locked_by``/``locked_at``/``ttl_seconds``/
    ``ttl_reason``, ``expected_new`` when declared) — the same shape the
    acquire pipeline writes, closing the hand-append incident class.
    """
    now = now if now is not None else datetime.now()
    op_id = require_operation_id("locks_amend", operation_id) \
        if operation_id else new_operation_id()
    SCHEMA_WINDOW.require_supported("locks_amend", SCHEMA_VERSION)
    task_id = _locks_common(task_id)
    _require_text("--reason", reason)
    if not add_file and ttl_seconds is None and extend_by is None:
        _refuse({
            "code": "schema_violation",
            "detail": "nothing to amend — give --add-file and/or exactly "
                      "one of --ttl-seconds / --extend-by",
        })
    _locks_ttl_args(ttl_seconds, extend_by, required=False)
    if expected_new and not add_file:
        _refuse({
            "code": "schema_violation",
            "detail": "--expected-new requires --add-file",
        })
    governance_dir = Path(governance_dir)
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    normalized_add = _normalize_path(add_file) if add_file else None
    if normalized_add and not expected_new \
            and not (root / normalized_add).is_file():
        _refuse({
            "code": "cross_record_violation",
            "detail": f"add-file target {normalized_add} does not exist — "
                      f"declare --expected-new for a to-be-created file "
                      f"(RISK-046 pre-write path rule)",
        })
    fingerprint = _fingerprint({
        "command": "locks-amend", "task": task_id, "add_file": normalized_add,
        "expected_new": bool(expected_new), "ttl_seconds": ttl_seconds,
        "extend_by": extend_by, "reason": reason,
    })

    def mutate(data, owner):
        active = data["active_tasks"][owner]
        if normalized_add:
            existing = data["file_locks"].get(normalized_add)
            if isinstance(existing, dict) \
                    and existing.get("locked_by") != owner:
                return ("cross_record_violation",
                        f"file {normalized_add} is already locked by "
                        f"{existing.get('locked_by')!r} — serialize per "
                        f"M7.6")
            if not isinstance(existing, dict):
                entry = {
                    "locked_by": owner,
                    "locked_at": now.replace(microsecond=0).isoformat(),
                    "ttl_seconds": _task_reference_entry(data, owner)[
                        "ttl_seconds"],
                    "ttl_reason": reason,
                }
                if expected_new:
                    entry["expected_new"] = True
                data["file_locks"][normalized_add] = entry
            for key in ("target_files", "files"):
                listing = active.setdefault(key, [])
                if normalized_add not in listing:
                    listing.append(normalized_add)
        if ttl_seconds is not None or extend_by is not None:
            owned = [f for f, e in data["file_locks"].items()
                     if isinstance(e, dict) and e.get("locked_by") == owner]
            if not owned:
                return ("cross_record_violation",
                        f"task {owner} holds no file locks to retune")
            for file_path in owned:
                entry = data["file_locks"][file_path]
                entry["ttl_seconds"] = (
                    entry["ttl_seconds"] + extend_by
                    if extend_by is not None else ttl_seconds)
                if entry["ttl_seconds"] <= 0:
                    return ("schema_violation",
                            f"resulting ttl_seconds for {file_path} is not "
                            f"positive")
                entry["ttl_reason"] = f"amend: {reason}"
        return None

    def effects_of(data):
        state = {"file_locks": {}}
        if normalized_add:
            state["file_locks"][normalized_add] = _snapshot_lock_fields(
                data, [normalized_add]).get(normalized_add, {})
            owner_entry = data["active_tasks"].get(task_id, {})
            state["active_tasks"] = {
                task_id: {key: list(owner_entry.get(key, []))
                          for key in ("target_files", "files")}}
        else:
            owned = [f for f, e in data["file_locks"].items()
                     if isinstance(e, dict)
                     and e.get("locked_by") == task_id]
            state["file_locks"] = _snapshot_lock_fields(data, owned)
        return state

    with _TargetLock(governance_dir / LOCKS_FILE_NAME, timeout_seconds):
        return _locks_execute(
            governance_dir, op_id, fingerprint, task_id, mutate, effects_of,
            command="locks-amend", now=now, timeout_seconds=timeout_seconds)


def _pending_released_files(governance_dir, op_id, fingerprint):
    """FIX-375 边缘③ + F-1 (REVIEW-FIX-370 F-1): the release recovery
    legs' audit source.  BOTH cross-crash recovery legs complete the
    release WITHOUT running ``effects_of`` — the resume leg (world already
    at the recorded target) and the re-apply leg (world at baseline →
    re-apply → complete with source="apply") — so the caller's
    ``owned_files`` stays empty by construction and the fresh-apply stamp
    condition never fires on either.  The pending entry carried the exact
    list in its registered ``pending_effects`` (B-10 登记先行), but
    ``_complete_pending`` nulls the effects in the same transaction that
    marks the entry ok — the list must therefore be captured BEFORE the
    pipeline completes the entry.  This is a read-only pre-read of the
    caller's own operation id, guarded by command AND input fingerprint so
    a foreign or mutated entry can never feed the audit stamp (a mismatch
    is simply not stamped — the pipeline itself refuses it independently)."""
    entry = _load_ledger(governance_dir)["operations"].get(op_id)
    if not isinstance(entry, dict) or entry.get("status") != "pending":
        return []
    if entry.get("command") != "locks-release" \
            or entry.get("input_fingerprint") != fingerprint:
        return []
    effects = entry.get("pending_effects")
    if not isinstance(effects, dict) \
            or not isinstance(effects.get("file_locks"), dict):
        return []
    return sorted(effects["file_locks"])


@_returns_payload
def locks_release(*, task_id, governance_dir, repo_root=None,
                  operation_id=None, now=None, timeout_seconds=10.0):
    """FIX-370 / version-plan 0.87.0 §5 B-10: release a task's dispatch
    locks — the task-anchored true deletion the family lacked.

    One atomic write removes the task's ``active_tasks`` entry AND every
    ``file_locks`` entry with ``locked_by == task_id``.  The governed
    pipeline records the pending ledger entry (target + baseline effects —
    the released file list with their prior fields) BEFORE the locks file
    is written back (B-10 先登记后删除), so a crash in between leaves the
    effect-based resume path, never a half state.  A re-run with the same
    ``operation_id`` after a completed release replays as a success no-op.

    Fail-closed: a task holding NEITHER an active_tasks entry NOR any file
    lock is refused with zero writes (nothing to release).  The
    orchestrator's shrink-locks step (TTL 收缩) semantics are deliberately
    untouched — this is deletion with audit, not shrinkage.
    """
    now = now if now is not None else datetime.now()
    op_id = require_operation_id("locks_release", operation_id) \
        if operation_id else new_operation_id()
    SCHEMA_WINDOW.require_supported("locks_release", SCHEMA_VERSION)
    task_id = _locks_common(task_id)
    governance_dir = Path(governance_dir)
    fingerprint = _fingerprint({
        "command": "locks-release", "task": task_id,
    })
    # FIX-375 边缘③: capture the recovery legs' audit list BEFORE the
    # pipeline completes the pending entry (completion nulls the recorded
    # effects); a fresh operation reads an empty ledger and gets [].

    def holds_lock(data):
        if task_id in data["active_tasks"]:
            return True
        return any(isinstance(entry, dict)
                   and entry.get("locked_by") == task_id
                   for entry in data["file_locks"].values())

    def mutate(data, owner):
        data["active_tasks"].pop(owner, None)
        for file_path in [f for f, e in data["file_locks"].items()
                          if isinstance(e, dict)
                          and e.get("locked_by") == owner]:
            del data["file_locks"][file_path]
        return None

    owned_files = []

    def effects_of(data):
        if not owned_files:
            # first (baseline) call fixes the released file list; the
            # target call then snapshots the SAME keys — each now absent
            # (an empty snapshot means "not locked" per _state_matches)
            owned_files.extend(sorted(
                f for f, e in data["file_locks"].items()
                if isinstance(e, dict) and e.get("locked_by") == task_id))
        state = {"file_locks": {
            f: _snapshot_lock_fields(data, [f]).get(f, {})
            for f in owned_files}}
        entry = data["active_tasks"].get(task_id)
        if isinstance(entry, dict):
            state["active_tasks"] = {
                task_id: {key: list(entry.get(key, []))
                          for key in ("target_files", "files")}}
        else:
            state["active_tasks"] = {task_id: None}  # absence marker
        return state

    with _TargetLock(governance_dir / LOCKS_FILE_NAME, timeout_seconds):
        # F-4 (review R0): the pre-read sits UNDER the target lock — a
        # same-op-id concurrent re-run can no longer slip between the
        # pending registration and the locks write — and still BEFORE the
        # pipeline call (completion nulls the recorded effects, so the
        # capture must precede it; read-only, no ledger lock taken).
        resume_released = _pending_released_files(governance_dir, op_id,
                                                  fingerprint)
        payload = _locks_execute(
            governance_dir, op_id, fingerprint, task_id, mutate, effects_of,
            command="locks-release", now=now, timeout_seconds=timeout_seconds,
            holds_lock=holds_lock)
    stamped_files = None
    if payload.get("replay_source") == "apply" and owned_files:
        # B-10 留痕: the shared pipeline drops effect payloads on the ok
        # row (family convention); for a DELETION the released file list
        # is the audit record, so the completed entry is stamped with it.
        # Fresh apply leg: the list is the effects_of closure's live
        # capture (the "ledger" replay re-judges an already-applied world
        # where owned_files is empty by construction).  The pending row
        # already carried the full detail BEFORE the locks write (登记先
        # 行); this stamp only persists it past completion.
        stamped_files = list(owned_files)
    elif payload.get("replay_source") == "apply" \
            and not owned_files and resume_released:
        # F-1 (review R0 / REVIEW-FIX-370 F-1, 探针⑤): the re-apply
        # recovery leg (world == recorded baseline → the pipeline re-applies
        # the mutator and completes with source="apply") never runs
        # effects_of either, so owned_files is empty by construction and
        # the fresh-apply branch above short-circuits — this leg takes its
        # list from the SAME pre-read capture (登记先行).  A fresh apply
        # reads resume_released == [] and never enters this branch.
        stamped_files = list(resume_released)
    elif payload.get("replay_source") == "resume" and resume_released:
        # FIX-375 边缘③ (REVIEW-FIX-370 F-1): the resume leg (world ==
        # recorded target) completes WITHOUT running effects_of — same
        # empty owned_files, same pre-read audit source.  With the re-apply
        # branch above, the released-file audit is identical across ALL
        # THREE completion legs (fresh apply / re-apply / resume).
        stamped_files = list(resume_released)
    if stamped_files is not None:
        def stamp(operation_ledger):
            stored = operation_ledger["operations"].get(op_id)
            if stored is not None and stored.get("status") == "ok":
                stored["released_files"] = stamped_files

        _ledger_transaction(governance_dir, stamp, timeout_seconds)
    return payload


# ── composition root (组合根装配 — module-owned, engine untouched) ───────────


def _split_cli_list(raw):
    """Split a CLI list on BOTH documented separators (``--files``): ``;``
    is normalized to ``,`` first (same convention as change_triage's
    ``_split``), then the result splits on the comma."""
    return [item.strip()
            for item in str(raw or "").replace(";", ",").split(",")
            if item.strip()]


def _split_refs_list(raw):
    """Split ``--refs`` on ``;`` ONLY — a ref value (e.g. a URL) may
    legitimately contain a comma, so the comma is never a ref separator."""
    return [item.strip() for item in str(raw or "").split(";")
            if item.strip()]


def _run(fn, kwargs):
    try:
        return fn(**kwargs)
    except StoreError as exc:
        return exc.payload
    except ContractViolation as exc:
        # FIX-375 边缘②: a malformed --operation-id (contracts face 1,
        # require_operation_id) raised ContractViolation straight through
        # the writers' @_returns_payload (which converts StoreError only)
        # and the CLI printed a bare traceback.  The dispatch face renders
        # the closed-code refusal instead — raw-dict shape, the same
        # convention as the writers' own _refuse({"code": "schema_violation",
        # ...}) refusals (WriterResult would re-validate operation_id, so
        # _error_result is unusable for a refusal about an INVALID id).
        # Library callers are NOT routed through here: a direct import
        # caller keeps the ContractViolation semantics unchanged.
        return {
            "code": "schema_violation",
            "detail": str(exc),
            "disposition": ERROR_CODE_DISPOSITIONS["schema_violation"],
            "error": True,
        }


def _emit(payload) -> int:
    """Print the JSON payload and translate ``error``/``disposition`` to
    the process exit code: 0 ok / 2 refusal / 3 retryable.

    FIX-379 item-3 (0.86.0 M-2 量测边缘观察 #3): this family's scale is
    THREE-valued by design — conflict-class results (revision_conflict,
    operation_id_conflict) and validation/manual refusals all share exit
    2 on purpose.  The FEAT-051 task_row_update family owns a six-value
    scale (3 validation / 4 conflict / 6 manual) whose disposition
    classes stay distinct at the process boundary; this FEAT-046 family's
    refusal GRANULARITY lives in the JSON ``code``/``disposition`` fields,
    which is what structured callers (the closure-chain CLI steps, the
    engine dispatch) consume.  Re-scaling here would be a behavior change
    for every caller migrated by FIX-375 to read exit codes (its
    canonical per-family table lives at the verify_workflow.py dispatch
    comment) — differences stay DOCUMENTED, not silently unified.
    """
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload.get("error"):
        return 3 if payload.get("disposition") == "retryable" else 2
    return 0


def add_locks_extend_arguments(parser: argparse.ArgumentParser) -> None:
    """Module-owned option fact source for ``locks-extend`` (single
    definition shared by ``build_parser`` and the engine subparser —
    batch-2.0 wiring FEAT-055, FEAT-047 P2-1 caliber)."""
    parser.add_argument("--task", required=True)
    parser.add_argument("--files", required=True,
                        help="semicolon/comma-separated locked paths to extend")
    parser.add_argument("--ttl-seconds", type=int, default=None,
                        help="absolute new TTL value")
    parser.add_argument("--extend-by", type=int, default=None,
                        help="add seconds to the current TTL")
    parser.add_argument("--reason", required=True)
    parser.add_argument("--operation-id", default="")
    parser.add_argument("--timeout", type=float, default=10.0)


def add_locks_amend_arguments(parser: argparse.ArgumentParser) -> None:
    """Option fact source for ``locks-amend`` (see
    :func:`add_locks_extend_arguments`)."""
    parser.add_argument("--task", required=True)
    parser.add_argument("--add-file", default="")
    parser.add_argument("--expected-new", action="store_true")
    parser.add_argument("--ttl-seconds", type=int, default=None)
    parser.add_argument("--extend-by", type=int, default=None)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--operation-id", default="")
    parser.add_argument("--timeout", type=float, default=10.0)


def add_locks_release_arguments(parser: argparse.ArgumentParser) -> None:
    """Option fact source for ``locks-release`` (see
    :func:`add_locks_extend_arguments`)."""
    parser.add_argument("--task", required=True,
                        help="dispatch task whose locks are released")
    parser.add_argument("--operation-id", default="",
                        help="replay: a released task re-released with the "
                             "same operation id is a success no-op")
    parser.add_argument("--timeout", type=float, default=10.0)


def add_evidence_append_arguments(parser: argparse.ArgumentParser) -> None:
    """Option fact source for ``evidence-append`` (see
    :func:`add_locks_extend_arguments`)."""
    parser.add_argument("--task", required=True)
    parser.add_argument("--type", dest="evd_type", required=True)
    parser.add_argument("--description", required=True,
                        help="description cell; must carry 目标对齐： >= 30 chars")
    parser.add_argument("--basis", required=True,
                        help="factual basis (after 事实依据：)")
    parser.add_argument("--artifacts", required=True,
                        help="artifacts cell (all 10 row cells must be non-empty)")
    parser.add_argument("--actor", default="governance-store")
    parser.add_argument("--date", default="")
    parser.add_argument("--gate", default="G11")
    parser.add_argument("--conclusion", default="✅ 完成")
    parser.add_argument("--refs", default="",
                        help="semicolon-separated kind:value refs "
                             "(repo_file|git_object|governance_id|url|"
                             "human_observation; aliases url_syntax/human_note)")
    parser.add_argument("--operation-id", default="")
    parser.add_argument("--expected-revision", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=float, default=10.0)


def add_decision_append_arguments(parser: argparse.ArgumentParser) -> None:
    """Option fact source for ``decision-append`` (see
    :func:`add_locks_extend_arguments`)."""
    parser.add_argument("--decider", required=True)
    parser.add_argument("--content", required=True)
    parser.add_argument("--basis", default="")
    parser.add_argument("--date", default="")
    parser.add_argument("--operation-id", default="")
    parser.add_argument("--expected-revision", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=float, default=10.0)


def build_parser():
    """The module-owned composition root (see module docstring: the frozen
    engine dispatch face is not grown by a batch-1 implementation ticket)."""
    parser = argparse.ArgumentParser(
        prog="governance_store.py",
        description="FEAT-046 governed writer family (locks/evidence/"
                    "decision) — operation_id + atomic write + structured "
                    "results")
    parser.add_argument("--project-root", default=".",
                        help="Host project root (default: cwd); the "
                             "governance dir is <root>/.governance")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("locks-extend", help="extend file-lock TTLs")
    add_locks_extend_arguments(p)

    p = sub.add_parser("locks-amend", help="amend a dispatch lock")
    add_locks_amend_arguments(p)

    p = sub.add_parser(
        "locks-release",
        help="release a task's dispatch locks (active entry + file locks)")
    add_locks_release_arguments(p)

    p = sub.add_parser("evidence-append", help="append one EVD row")
    add_evidence_append_arguments(p)

    p = sub.add_parser("decision-append", help="append one DEC row")
    add_decision_append_arguments(p)
    return parser


COMMANDS = {
    "locks-extend": locks_extend,
    "locks-amend": locks_amend,
    "locks-release": locks_release,
    "evidence-append": evidence_append,
    "decision-append": decision_append,
}


def _configure_stdio() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — best-effort console hygiene
        pass


def _governance_dir_from(args) -> Path:
    """The governance dir for a parsed Namespace: the engine dispatch face
    reads the engine-resolved ``project_root``; the self-contained CLI reads
    its own ``--project-root`` (default cwd)."""
    return Path(getattr(args, "project_root", ".") or ".") \
        / GOVERNANCE_DIR_NAME


def cmd_locks_extend(args) -> int:
    """Engine dispatch face (batch-2.0 wiring, FEAT-055): consume the
    engine's parsed Namespace directly — no argv re-parse (FEAT-047 P2-1
    caliber)."""
    _configure_stdio()
    payload = _run(locks_extend, dict(
        task_id=args.task,
        files=_split_cli_list(args.files),
        ttl_seconds=args.ttl_seconds, extend_by=args.extend_by,
        reason=args.reason, governance_dir=_governance_dir_from(args),
        operation_id=args.operation_id or None,
        timeout_seconds=args.timeout))
    return _emit(payload)


def cmd_locks_amend(args) -> int:
    """Engine dispatch face (see :func:`cmd_locks_extend`)."""
    _configure_stdio()
    payload = _run(locks_amend, dict(
        task_id=args.task, add_file=args.add_file or None,
        expected_new=args.expected_new,
        ttl_seconds=args.ttl_seconds, extend_by=args.extend_by,
        reason=args.reason, governance_dir=_governance_dir_from(args),
        operation_id=args.operation_id or None,
        timeout_seconds=args.timeout))
    return _emit(payload)


def cmd_locks_release(args) -> int:
    """Engine dispatch face (see :func:`cmd_locks_extend`)."""
    _configure_stdio()
    payload = _run(locks_release, dict(
        task_id=args.task,
        governance_dir=_governance_dir_from(args),
        operation_id=args.operation_id or None,
        timeout_seconds=args.timeout))
    return _emit(payload)


def cmd_evidence_append(args) -> int:
    """Engine dispatch face (see :func:`cmd_locks_extend`)."""
    _configure_stdio()
    payload = _run(evidence_append, dict(
        task_id=args.task, evd_type=args.evd_type,
        description=args.description, basis=args.basis,
        artifacts=args.artifacts, actor=args.actor,
        date=args.date or None, gate=args.gate,
        conclusion=args.conclusion,
        refs=_split_refs_list(args.refs),
        governance_dir=_governance_dir_from(args),
        operation_id=args.operation_id or None,
        dry_run=args.dry_run,
        expected_revision=args.expected_revision,
        timeout_seconds=args.timeout))
    return _emit(payload)


def cmd_decision_append(args) -> int:
    """Engine dispatch face (see :func:`cmd_locks_extend`)."""
    _configure_stdio()
    payload = _run(decision_append, dict(
        decider=args.decider, content=args.content,
        basis=args.basis, date=args.date or None,
        governance_dir=_governance_dir_from(args),
        operation_id=args.operation_id or None,
        dry_run=args.dry_run,
        expected_revision=args.expected_revision,
        timeout_seconds=args.timeout))
    return _emit(payload)


_CLI_HANDLERS = {
    "locks-extend": cmd_locks_extend,
    "locks-amend": cmd_locks_amend,
    "locks-release": cmd_locks_release,
    "evidence-append": cmd_evidence_append,
    "decision-append": cmd_decision_append,
}


def main(argv=None) -> int:
    """CLI entry — JSON summary on stdout, exit 0 ok / 2 refusal / 3 retry.

    Exit-code rationale (FIX-379 item-3): this family collapses all
    refusal dispositions (validation / conflict / manual) onto exit 2 and
    keeps only the retryable split on 3 — the fine-grained closed code is
    always in the JSON payload.  The task_row_update family uses a
    six-value scale (2 usage / 3 validation / 4 conflict / 5 retryable /
    6 manual); per-family scales intentionally differ and are tabulated
    at the verify_workflow.py dispatch comment (FIX-375 F-2/F-3)."""
    _configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    return _CLI_HANDLERS[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
