"""task-row-update — the single governed write path for plan-tracker task rows.

Batch-1 ticket 1 of version-plan-0.86.0 §2 (FEAT-051, formerly FEAT-042R —
the ``R`` suffix violated PREFIX-NNN so the number was re-sequenced).  This is
the termination surface of boundary-audit B-1: the recurring hand-edited row
incidents (3+1 confirmed during REL-082 planning, 7 by the end of the
planning session) are replaced by one CLI that is the *only* supported way to
flip a task row's state, machine-anchored by task id instead of a human
counting pipe characters.

Consumes the m0-r1 frozen contract (``infra/contracts.py``) **read-only**:
the seven TASK_STATES, the 11-edge TASK_TRANSITIONS table, the three-valued
operation-replay decision, the WriterRequest/WriterResult CAS shapes and the
closed error-code enum.  This module never mutates contract objects — pinned
by ``test_contract_objects_are_consumed_read_only``.

Design sources (quoted, not re-derived here):

  * arch round-2 §1 — the five-step write flow (LLM submits → CLI takes the
    short-term lock → re-read + re-validate (CAS / lock ownership / legality)
    → compute + atomic replace → release and return new revision + result
    code); CAS and the short-term lock are *combined*, not alternatives.
  * arch round-3 P1-1 — M0 freezes the cross-ticket interface, not the
    writer's internal details; per-writer calibration lives here.
  * evolution §4 — the nine-item machine-writer DoD this module implements.

Public entry points:

    main(argv)          CLI handler (self-contained; ``python task_row_update.py
                        ...`` works, and the dotted path ``task_row_update.main``
                        is the composition-root assembly point in the
                        governance_cost / bootstrap_aggregate pattern)
    cmd_task_row_update(args)
                        engine dispatch face (wired by the batch-2.0
                        integration slice, FEAT-055): consumes the engine's
                        parsed Namespace, no argv re-parse
    add_arguments(parser)
                        module-owned option fact source (single definition
                        shared by ``main`` and the engine subparser)
    execute_update(...) library entry (the five-step flow, returns WriterResult)
    inspect_target(...) read-only observation surface (CAS expectation source)

Registering the subcommand follows the engine-wires-dispatch-only pattern
(governance_cost, bootstrap_aggregate): this module contains zero ``import
verify_workflow`` (ArchGuard R2), is stdlib-only at import time plus the L0
``contracts`` leaf, and exposes a dotted-path handler a composition root can
assemble on demand.  The engine dispatch row itself lives outside this
ticket's frozen two-file surface and is wired by the batch-2.0 integration
slice (disclosed in the delivery report, never silently assumed).

operation_id scope declaration (P3 carry-over from FEAT-049 review R0 —
batch-2.0 obligation discharged here, in prose, because the frozen
WriterRequest shape cannot grow fields inside an implementation ticket):

  * **Generation scope: global** (contract face 1) — ids are minted via
    :func:`contracts.new_operation_id` (``op-`` + uuid4 hex); nothing here
    narrows or renames that form.
  * **Resolution scope: the target file's ledger.**  Replay/conflict
    adjudication consults the sidecar ledger bound to the file being written
    (``<target>.ops.jsonl``).  Under the "one canonical source per table —
    never dual masters" invariant (arch round-2 §6) the takeover range of
    0.86.0 is a single governed table with one ledger instance, so the
    per-file resolution scope is the *only* scope in which a retried
    operation can legitimately arrive.  A global cross-ledger duplicate index
    is deliberately out of scope here — it belongs to the batch-2.1 closure
    event-log slice, which already owns a durable operation journal.  A
    duplicate id arriving at a *different* ledger resolves to ``execute``
    there (each ledger only knows its own history); this boundary is
    disclosed rather than hidden.

schema_version carrier declaration (P3 carry-over — batch-2.0 obligation):

  The frozen WriterRequest has no ``schema_version`` field and this ticket
  must not grow contract shapes.  The carrier is therefore **CLI-side**:
  ``--schema-version`` (default 1) is validated against
  ``SCHEMA_VERSION_WINDOW`` (:class:`contracts.SchemaVersionWindow`) — a
  version outside ``[minimum, current]`` is refused with
  ``schema_version_unsupported`` (旧 CLI 遇新 schema 拒写), and the accepted
  value is stamped onto every receipt row in the ledger.  The record-family
  schema versioned here is "markdown pipe-table task row, status column =
  last cell, STATE_MARKERS vocabulary, v1".  If batch 2.0 needs the field on
  WriterRequest itself, that is a contract change (propose → re-baseline M0 →
  identify affected tickets → re-run acceptance), never an edit here.

Idempotency is effect-based (``contracts.IDEMPOTENCY_MODEL``): the ledger is
consulted for *adjudication*, but the world is re-read under the lock for
*truth*.  A retried operation whose receipt was lost (crash between the
atomic replace and the ledger append — the one effect-first window, disclosed
in ``RECOVERY`` below) is NOT silently re-executed: the state-level CAS sees
the row already at the target state and refuses with ``revision_conflict``,
pointing at the out-of-band reconciliation.  The log alone never decides what
happened.

Machine provenance marking (DoD 9): every flipped row carries its operation
id appended to the status cell (`` 〔op-<32hex>〕``), so the written line is
self-identifying on its face, and every write additionally produces a
structured receipt row in the ledger (task_id / operation_id / before-after
states / timestamp / row + file fingerprints) — the structural-join anchor.
Enforcement posture is **WARN** (per the ticket: this ticket only *produces*
the credential; the join/enforcement check surface lands in batch 2.3).

Supported platforms for reliable persistence (DoD 3): Windows NTFS and
POSIX — temp file is created in the target's own directory (same volume, so
``os.replace`` is atomic there), UTF-8 **without** BOM, and the original
file's line-ending style (LF vs CRLF) is preserved byte-for-byte on every
untouched line.

Recovery (``RECOVERY``, DoD 6):

  * Before the atomic replace, any failure leaves the target file untouched
    and the temp file is removed in a ``finally`` block — no half-written
    target is ever observable, and stale ``*.tmp`` siblings from an earlier
    hard kill are swept at the start of the next run.
  * ``os.replace`` is the commit point.  After it, the target is complete.
  * The one effect-first window: crash after the replace but before the
    ledger append.  The world has the effect, the ledger lacks the receipt.
    Recovery is effect-based and manual-adjudicated, never automatic
    re-execution: retrying the same operation id hits the state-level CAS
    (row already at target) → ``revision_conflict`` with detail
    ``effect_present_without_receipt`` — reconcile the row content against
    the request fingerprint by hand, then record the adjudication.  This
    module deliberately does not auto-forge the missing receipt (a writer
    that fabricates its own audit trail is worse than an honest gap).
  * The lock file itself is left in place (loop_event_log precedent) to avoid
    a create/delete race; only its byte-range lease is transient.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from contracts import (  # L0 — consumed read-only, frozen at revision m0-r1
    ERROR_CODE_DISPOSITIONS,
    EvidenceRef,
    RESULT_OK,
    SchemaVersionWindow,
    TASK_STATES,
    WriterRequest,
    WriterResult,
    decide_operation_replay,
    new_operation_id,
    require_operation_id,
    require_task_transition,
)

__all__ = [
    "DEFAULT_SCHEMA_VERSION",
    "REFRESH_ACTION",
    "SCHEMA_VERSION_WINDOW",
    "STATE_CANONICAL_MARKERS",
    "STALE_PROGRESS_PHRASES",
    "TASK_ROW_UPDATE_RESULT_CODES",
    "WRITER_ID",
    "ExitCode",
    "LockContention",
    "canonical_input_fingerprint",
    "build_candidate_row",
    "detect_row_state",
    "execute_refresh",
    "execute_update",
    "find_stale_progress_phrases",
    "inspect_target",
    "locate_task_row",
    "main",
    "refresh_candidate_row",
    "revision_of",
]

WRITER_ID = "task_row_update/0.86.0-batch1"
"""Writer identity stamped on every receipt (machine-provenance anchor)."""

RECEIPT_RECORD_KIND = "task_row_update"
"""Ledger ``record_kind`` — the structural-join face consumed (batch 2.3)."""

SCHEMA_VERSION_WINDOW = SchemaVersionWindow(minimum=1, current=1)
"""Compatibility window over the record-family schema (face 4 carrier).

Record family v1 = markdown pipe-table task row, status column is the last
cell, STATE_MARKERS vocabulary.  Anything above ``current`` is refused (旧
CLI 遇新 schema 拒写); ``minimum`` only moves when v1 is genuinely retired.
"""

DEFAULT_SCHEMA_VERSION = SCHEMA_VERSION_WINDOW.current
"""Schema version assumed when the caller does not pass --schema-version."""

STATUS_CELL_OP_SUFFIX_PATTERN = re.compile(r"\s*〔op-[0-9a-f]{32}〕\s*$")
"""Machine-provenance suffix already present on a previously written row."""

_OP_ANCHOR_RE = re.compile(r"〔op-[0-9a-f]{32}〕")
"""Search-anywhere locator for the ops receipt anchor (FIX-394).

``STATUS_CELL_OP_SUFFIX_PATTERN`` is end-anchored (the flip path strips the
tail anchor before re-appending); live terminal rows may carry narrative
brackets AFTER the anchor (FEAT-061's 〔R0 …〕 group), so the refresh surface
locates the anchor anywhere inside the cell and never assumes it is last.
"""

_OPEN_PAREN_CHARS = "(（"
_CLOSE_PAREN_CHARS = ")）"

REFRESH_ACTION = "suffix_refresh"
"""Receipt ``action`` discriminator for a FIX-394 suffix-alignment write.

Flip receipts carry no ``action`` key (existing ledger rows unchanged); a
refresh receipt is marked so the ops ledger can distinguish a state flip
from a terminal-row text alignment at a glance.
"""

# ── Stale progress-suffix vocabulary (FIX-394) ──────────────────────────────


STALE_PROGRESS_PHRASES: Tuple[Tuple[str, str], ...] = (
    # (word-form, the chain phase it narrates).
    ("已 lock 待派发", "committed"),
    ("审查中", "review"),
    ("待审查", "review"),
    ("已审查", "approved"),
    ("开发中", "dev"),
    ("收尾中", "dev"),
    ("进行中", "dev"),
)
"""Closed vocabulary of STALE mid-flight progress wording (FIX-394).

Facts, not guesses: the four live 0.88 wordings the 13 stale terminal rows
carry (「已 lock 待派发」×9、「审查中」REL-087、「开发中」REL-088、「收尾中」
REL-089) plus the chain phases' own word-forms a flip may leave behind
(「待审查/审查中」review、「已审查」approved、「进行中/开发中/收尾中」dev).

Semantic boundary (deliberate): terminal-state narrative words — 「已发布」
(REL-086's legitimate release narrative), 「已完成」, 「完成」, 「已交付」 —
are NEVER in this vocabulary; the refresh clears stale PROGRESS wording, it
does not erase legitimate history.  Bare English state tokens (``dev``/
``review``/…) are also deliberately excluded: no live row carries them, and
a free-text token scan is exactly the B-1 hazard this writer exists to
avoid.  Extending the vocabulary is a deliberate, test-pinned change.
"""

_STALE_PHRASE_RES: Tuple[Tuple[str, str, "re.Pattern[str]"], ...] = tuple(
    (phrase, phase, re.compile(r"[ ]*" + re.escape(phrase) + r"(?=[ ]|$)"))
    for phrase, phase in STALE_PROGRESS_PHRASES
)
"""Compiled per-phrase deleters: leading spaces + phrase, requiring a
trailing space or end-of-segment (so the separator AFTER the phrase
survives and neighbours never concatenate)."""

# ── Status-marker vocabulary (writer-owned calibration; M0 froze the state
#    enum, not the markdown word-forms this table maps them onto) ───────────


STATE_CANONICAL_MARKERS: Dict[str, str] = {
    "triaged": "triaged",
    "dev": "🔄 进行中",
    "review": "review",
    "approved": "approved",
    "completed": "✅ 完成",
    "committed": "committed",
    "blocked": "⛔ BLOCKED",
}
"""Canonical word-form written when a row enters each state.

``dev``/``completed``/``blocked`` mirror the dominant word-forms already live
in the tracker's task table (``🔄 进行中`` / ``✅ 完成`` / ``⛔ BLOCKED``);
the remaining five have no established emoji form in the corpus, so they use
the plain state name rather than an invented decoration (WARN posture — the
structural join in batch 2.3 consumes receipts, not word-forms).
"""

# Detection is an *ordered, mutually-exclusive* chain over the status cell
# only (never the whole row — narrative cells legitimately contain words like
# "review"), anchored on the highest-specificity markers observed in the live
# table.  First hit wins; a cell matching nothing resolves to "unknown" and
# the write refuses fail-closed (schema_violation) instead of guessing.
# Every canonical marker in STATE_CANONICAL_MARKERS is detectable by its own
# state's pattern — the flip's post-splice re-check re-runs this chain on the
# candidate row, so a word-form the chain cannot see back must not exist.
_STATE_MARKER_CHAIN: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    ("completed", re.compile(r"✅\s*完成")),
    ("blocked", re.compile(r"⛔|BLOCKED")),
    ("dev", re.compile(r"🔄|进行中")),
    ("committed", re.compile(r"\bcommitted\b|已提交")),
    ("approved", re.compile(r"\bapproved\b|已审查")),
    ("review", re.compile(r"\breview\b|待审查|审查中")),
    ("triaged", re.compile(r"\btriaged\b|已\s*triage")),
)

_TABLE_SEPARATOR_ROW = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")
_RECORD_FAMILY_ID_COLUMN = 2
"""Record-family schema v1: the task id lives in visual column 2.

Anchoring by the ID *column* — never by a free-text token scan — is the
mechanical form of the B-1 lesson: narrative and reference cells routinely
mention the same id (``TRIAGE-FEAT-049``, dependency lists like
``；FEAT-049``), and a whole-row match would let a *different* row's
reference hijack the flip.  Index 2 (not 1) because a pipe-table row starts
with ``|``, so ``split("|")`` yields a leading empty element: ``['',
' **P1** ', ' FEAT-049 ', …]``.  A row whose id sits elsewhere is simply
not anchored (cross_record_violation with that fact disclosed — extending
the family to other layouts is a deliberate schema change, not a fallback
guess).
"""


class LockContention(RuntimeError):
    """The short-term write lock could not be acquired within the budget.

    Never downgraded to an unlocked write: the READ→COMPARE→WRITE critical
    section of a state flip has no single-write-call backstop (unlike the
    loop event log's line append), so the write is refused as
    ``lock_contention`` (retryable) and the caller retries the SAME operation.
    """


# ── Revision (aggregate content version for the CAS face) ───────────────────


def revision_of(content: str) -> int:
    """Aggregate revision of a whole file's content (arch round-2 §1).

    The tracker is one shared file, so a per-task revision number cannot
    express concurrency; the round-2 remedy for shared files is "lock-
    protected re-read + an aggregate version".  The aggregate here is the
    leading 64 bits of the SHA-256 of the exact on-disk text — deterministic,
    dependency-free, and it changes whenever (and only when) any byte of the
    file changes, which is precisely the CAS semantics WriterRequest expects.
    """
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def canonical_input_fingerprint(
    *,
    operation_id: str,
    task_id: str,
    from_state: str,
    to_state: str,
    reason: str,
    evidence_refs: Tuple[EvidenceRef, ...],
    schema_version: int,
    action: Optional[str] = None,
) -> str:
    """SHA-256 of the writer's canonical normalized input (contract face 1).

    Deliberately covers only the *request semantics* (id, task, transition,
    reason, refs, schema version) — never the observed file content, so a
    genuine retry of the same request hashes identically even though the
    world moved underneath it (that divergence is what CAS adjudicates, not
    the fingerprint).

    ``action`` (FIX-394): ``None`` (a state flip) keeps the payload — and
    therefore every fingerprint already on record — byte-identical to the
    pre-FIX-394 form; a suffix refresh stamps ``action=REFRESH_ACTION`` so
    a flip and an alignment can never collide on the same operation id.
    """
    payload = {
        "operation_id": operation_id,
        "task_id": task_id,
        "from": from_state,
        "to": to_state,
        "reason": reason,
        "evidence_refs": [[ref.kind, ref.value] for ref in evidence_refs],
        "schema_version": schema_version,
        "record_kind": RECEIPT_RECORD_KIND,
    }
    if action is not None:
        payload["action"] = action
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ── Row parsing / state detection (record-family schema v1) ─────────────────


def _status_cell(cells: List[str]) -> Optional[Tuple[int, str]]:
    """Return (index, text) of the status cell — the last non-empty cell."""
    for index in range(len(cells) - 1, -1, -1):
        text = cells[index].strip()
        if text:
            return index, text
    return None


def detect_row_state(line: str) -> Optional[str]:
    """Detect the governed task state of one table row (schema v1 chain).

    Scans **only the status cell** (last non-empty pipe-delimited cell) so
    narrative text elsewhere in the row can never impersonate a state.  The
    marker chain is mutually exclusive by construction — first hit wins; a
    cell that matches nothing yields ``None`` (unknown) and callers refuse
    fail-closed rather than guessing.  Separator/header rows report ``None``.
    """
    stripped = line.strip()
    if not stripped.startswith("|") or _TABLE_SEPARATOR_ROW.match(stripped):
        return None
    cells = stripped.split("|")
    located = _status_cell(cells)
    if located is None:
        return None
    cell_text = located[1]
    for state, pattern in _STATE_MARKER_CHAIN:
        if pattern.search(cell_text):
            return state
    return None


def locate_task_row(text: str, task_id: str) -> Tuple[int, str]:
    """Anchor the unique task row by its ID column — B-1 made mechanical.

    A row is a candidate iff its ID cell (schema v1: cell index 1, stripped
    of ``**`` bold markers) equals ``task_id`` exactly and the row carries a
    parseable status cell.  Returns ``(0-based line index, line text with
    its original line ending stripped)``.  Zero matches or **more than one**
    match raise ``ValueError``: an unresolvable or ambiguous anchor is a
    cross-record violation (the writer refuses to guess which row the caller
    meant — that guess is exactly what the hand-edit incidents were).
    """
    hits: List[Tuple[int, str]] = []
    for index, line in enumerate(text.splitlines()):
        if "|" not in line:
            continue
        stripped = line.strip()
        if stripped.startswith("|") and not _TABLE_SEPARATOR_ROW.match(stripped):
            cells = stripped.split("|")
            if len(cells) > _RECORD_FAMILY_ID_COLUMN:
                id_cell = cells[_RECORD_FAMILY_ID_COLUMN].strip().strip("*")
                # Anchoring is ID-column equality ONLY; whether the row's
                # status cell parses is the execute path's concern (a legacy
                # word-form reports schema_violation there, which is more
                # precise than pretending the row does not exist).
                if id_cell == task_id:
                    hits.append((index, line.rstrip("\r\n")))
    if not hits:
        raise ValueError(
            "locate_task_row: no task row anchored for task_id={0!r} "
            "(cross_record_violation: the governed table contains no row "
            "whose ID column equals this id; ids mentioned in narrative or "
            "reference cells never anchor)".format(task_id))
    if len(hits) > 1:
        raise ValueError(
            "locate_task_row: ambiguous anchor for task_id={0!r} — {1} "
            "candidate rows at (0-based) lines {2}; refusing to guess "
            "(cross_record_violation: B-1 root cause made mechanical)".format(
                task_id, len(hits), [h[0] for h in hits]))
    index, line = hits[0]
    return index, line.rstrip("\r\n")


def _cell_parts(raw: str) -> Tuple[str, str, str]:
    """Split a raw table cell into ``(leading padding, core, trailing
    padding)`` — the P1-1 write-side discipline: detection reads the
    stripped core, writes splice into the raw cell so padding bytes never
    move."""
    lead = len(raw) - len(raw.lstrip())
    trail = len(raw) - len(raw.rstrip())
    core = raw[lead:len(raw) - trail]
    return raw[:lead], core, raw[len(raw) - trail:]


# ── Stale progress-suffix refresh core (FIX-394) ────────────────────────────


def _paren_depth_before(text: str, pos: int) -> int:
    """Parenthesis depth at ``pos`` — half/full-width pairs both count."""
    depth = 0
    for ch in text[:pos]:
        if ch in _OPEN_PAREN_CHARS:
            depth += 1
        elif ch in _CLOSE_PAREN_CHARS:
            if depth > 0:
                depth -= 1
    return depth


def _refresh_stale_phrases(
    text: str, to_state: str,
) -> Tuple[str, Tuple[str, ...]]:
    """Delete stale progress phrases from paren-free spans of ``text``.

    A terminal flip (``to_state == 'committed'``) clears EVERY stale
    progress phrase — a terminal row has no in-flight progress left; a
    non-terminal flip clears only phrases narrating a phase other than the
    target state, so the row's own phase wording (the narrative chain)
    survives.  Text inside parentheses — date/narrative brackets — is never
    touched, and deletion spans never merge neighbouring words (the
    deleter consumes the leading spaces and requires a trailing space or
    segment end, so the separator after the phrase survives).

    Returns ``(refreshed_text, removed_phrases)``; ``removed_phrases`` is
    empty when nothing matched (zero-change detection for the caller).
    """
    if to_state == "committed":
        deleters = _STALE_PHRASE_RES
    else:
        deleters = tuple(d for d in _STALE_PHRASE_RES if d[1] != to_state)
    matches = []  # (start, end, phrase) — phrase kept for the receipt face
    for phrase, _phase, rx in deleters:
        for match in rx.finditer(text):
            if _paren_depth_before(text, match.start()) == 0:
                matches.append((match.start(), match.end(), phrase))
    if not matches:
        return text, ()
    matches.sort(key=lambda m: (m[0], -m[1]))
    parts: List[str] = []
    removed: List[str] = []
    cursor = 0
    for start, end, phrase in matches:
        if start < cursor:  # shadowed by a longer prior match
            continue
        parts.append(text[cursor:start])
        cursor = end
        if phrase not in removed:
            removed.append(phrase)
    parts.append(text[cursor:])
    return "".join(parts), tuple(removed)


def find_stale_progress_phrases(
    cell_core: str, *, target_state: str,
) -> Tuple[str, ...]:
    """Read-only detection: which stale progress phrases does the cell
    carry (paren-free spans before the ops anchor only)?  Zero matches =
    the row is already aligned (the alignment surface's no-op criterion).
    """
    anchor = _OP_ANCHOR_RE.search(cell_core)
    scan = cell_core if anchor is None else cell_core[:anchor.start()]
    found: List[str] = []
    if target_state == "committed":
        deleters = _STALE_PHRASE_RES
    else:
        deleters = tuple(d for d in _STALE_PHRASE_RES
                         if d[1] != target_state)
    for phrase, _phase, rx in deleters:
        for match in rx.finditer(scan):
            if _paren_depth_before(scan, match.start()) == 0:
                found.append(phrase)
                break
    return tuple(found)


def _refresh_progress_prefix(
    core: str, to_state: str,
) -> Tuple[str, Tuple[str, ...]]:
    """Refresh the stale progress suffix of one status-cell core (FIX-394).

    Scope: BEFORE the ops anchor only.  The anchor itself and any narrative
    brackets after it (FEAT-061's 〔R0 …〕 group) pass through untouched; a
    first-hop flip (no anchor yet) treats the whole core as the prefix.
    Returns ``(refreshed_core, removed_phrases)``.
    """
    anchor = _OP_ANCHOR_RE.search(core)
    if anchor is None:
        return _refresh_stale_phrases(core, to_state)
    refreshed, removed = _refresh_stale_phrases(
        core[:anchor.start()], to_state)
    return refreshed + core[anchor.start():], removed


def build_candidate_row(
    line: str,
    *,
    from_state: str,
    to_state: str,
    operation_id: str,
) -> str:
    """COMPUTE step: the flipped row (marker swap + provenance suffix).

    Only the status cell is touched: the detected ``from_state`` word-form is
    replaced by the canonical ``to_state`` marker, and the operation id is
    appended inside the status cell as ``〔op-<32hex>〕`` (DoD 9 — the written
    line identifies its writer on its face).  Every other character of the
    row — narrative, dates, evidence ids, escaped pipes, **and the cell's
    own padding whitespace** — is preserved byte-for-byte, so the row-level
    diff is minimal and joinable (P1-1, review-FEAT-051-CODE-R0: the
    detection helpers return a stripped cell for *reading*; every *write*
    below is spliced into the raw cell at computed offsets so padding
    whitespace survives untouched).

    Replacement is anchored, never guessed, and self-verifying:

      1. the canonical ``from_state`` marker is swapped verbatim when present
         (the dominant live word-forms, e.g. ``🔄 进行中`` → ``review``);
      2. otherwise the exact span the detection chain matched (a synonym
         form such as the compound ``🔄 M-0 ✅ …``) is swapped, leaving the
         surrounding narrative intact;
      3. the candidate row is then re-checked through the SAME detection
         chain: it must resolve to ``to_state`` — any residual ``from_state``
         word-form (a second marker, a parenthetical echo) is an ambiguous
         splice and refuses fail-closed rather than writing a row the next
         reader cannot parse.
    """
    current = detect_row_state(line)
    if current is None:
        raise ValueError(
            "build_candidate_row: status cell of the anchored row does not "
            "match any known state marker (schema_violation: record-family "
            "v1 vocabulary; legacy/free-form rows need manual triage)")
    if current != from_state:
        raise ValueError(
            "build_candidate_row: row state {0!r} != requested from_state "
            "{1!r} (state-level CAS failure)".format(current, from_state))
    cells = line.split("|")
    located = _status_cell(cells)
    if located is None:  # pragma: no cover - detect_row_state found a cell
        raise ValueError("build_candidate_row: status cell vanished")
    cell_index = located[0]
    _lead, core, _trail = _cell_parts(cells[cell_index])
    replacement = STATE_CANONICAL_MARKERS[to_state]
    canonical = STATE_CANONICAL_MARKERS[from_state]
    if canonical in core:
        new_core = core.replace(canonical, replacement, 1)
    else:
        # Synonym form: swap exactly the span the chain matched.
        pattern = dict(_STATE_MARKER_CHAIN)[from_state]
        match = pattern.search(core)
        if match is None:  # pragma: no cover - detection just matched it
            raise ValueError(
                "build_candidate_row: detected marker for {0!r} vanished "
                "before the splice (schema_violation)".format(from_state))
        new_core = core[:match.start()] + replacement + core[match.end():]
    # FIX-394: refresh the stale progress suffix as the new token lands —
    # a terminal flip leaves NO mid-flight wording behind; a non-terminal
    # flip keeps the row's own phase wording.  Runs BEFORE the post-splice
    # re-check so the chain re-reads the final candidate.
    new_core, _stale_removed = _refresh_progress_prefix(new_core, to_state)
    candidate_cells = list(cells)
    lead, _core, trail = _cell_parts(cells[cell_index])
    candidate_cells[cell_index] = lead + new_core + trail
    candidate_line = "|".join(candidate_cells)
    # Post-splice re-check through the SAME chain: the candidate must read
    # unambiguously as the target state (residual from-forms refuse).
    reread = detect_row_state(candidate_line)
    if reread != to_state:
        raise ValueError(
            "build_candidate_row: post-splice re-check read {0!r}, expected "
            "{1!r} — ambiguous splice (a residual {2!r} word-form remains in "
            "the status cell); refusing to write a row the next reader "
            "cannot parse (schema_violation: reconcile by hand or extend "
            "the vocabulary deliberately)".format(reread, to_state,
                                                  from_state))
    # Machine provenance: one op suffix per row, idempotent per operation.
    # Spliced between the content and the original trailing padding — the
    # padding bytes themselves never move.
    lead, core, trail = _cell_parts(candidate_cells[cell_index])
    base = STATUS_CELL_OP_SUFFIX_PATTERN.sub("", core).rstrip()
    candidate_cells[cell_index] = (
        lead + base + " 〔" + operation_id + "〕" + trail)
    return "|".join(candidate_cells)


# ── Ledger (operation receipts — the structural-join anchor) ────────────────


def _ledger_path_for(target: Path) -> Path:
    return target.parent / (target.name + ".ops.jsonl")


def _read_receipts(ledger: Path) -> List[Dict[str, Any]]:
    """Parse receipt rows; torn/malformed lines are skipped (append-only
    reader precedent, loop_event_log口径). Never raises."""
    if not ledger.is_file():
        return []
    try:
        text = ledger.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    receipts: List[Dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) \
                and row.get("record_kind") == RECEIPT_RECORD_KIND:
            receipts.append(row)
    return receipts


def _replayable_result_face(stored: Optional[Dict[str, Any]]) \
        -> Optional[Dict[str, Any]]:
    """Validate the stored receipt's writer_result face before a replay
    rebuild (P2-2, review-FEAT-051-CODE-R0).

    Returns the face dict when it can lawfully reconstruct a WriterResult
    (``code='ok'`` + a positive-int ``new_revision`` + a contract-legal
    ``execution``), otherwise ``None`` — the caller refuses with
    ``manual_intervention`` instead of tripping the frozen WriterResult
    constructor on a degenerate ledger row (hand-edited, older-format, or
    torn-then-partially-recovered receipt).
    """
    if not stored:
        return None
    prior = stored.get("writer_result")
    if not isinstance(prior, dict):
        return None
    revision = prior.get("new_revision")
    if (prior.get("code") != RESULT_OK
            or isinstance(revision, bool)
            or not isinstance(revision, int) or revision < 1
            or prior.get("execution") not in ("succeeded", "unknown")):
        return None
    return prior


def _append_receipt(ledger: Path, receipt: Dict[str, Any]) -> None:
    """Append one receipt as a single JSON line (UTF-8, LF-terminated).

    Called under the target's write lock, which serializes the composite
    action (atomic replace + ledger append) against all writers of the same
    target — the lock, not the ledger, is the mutual-exclusion surface.
    """
    ledger.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n"
    with open(ledger, "a", encoding="utf-8", newline="") as handle:
        handle.write(line)


# ── Short-term write lock (arch round-2 §1: CAS + lock combined) ────────────


def _write_lock(target: Path, *, attempts: int = 40, base_delay: float = 0.005):
    """Exclusive short-term lock over the target's read-compare-write section.

    Companion ``<target>.lock`` file, byte-0 lease: ``msvcrt.locking`` with
    bounded ``LK_NBLCK`` retry on Windows, ``fcntl.flock(LOCK_EX)`` on POSIX
    (the loop_event_log precedent).  **Fail-closed**: an exhausted budget
    raises :class:`LockContention` — this writer never degrades to an
    unlocked write, because a row flip has no line-append backstop to fall
    back on.
    """
    lock_path = Path(str(target) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    if os.name == "nt":
        import msvcrt
        import time

        @contextlib.contextmanager
        def _win_lock():
            fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
            acquired = False
            try:
                for attempt in range(attempts):
                    try:
                        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                        acquired = True
                        break
                    except OSError:
                        if attempt == attempts - 1:
                            break
                        time.sleep(base_delay * (1.4 ** min(attempt, 10)))
                if not acquired:
                    raise LockContention(
                        "write lock busy after {0} attempts: {1}".format(
                            attempts, lock_path))
                yield
            finally:
                if acquired:
                    try:
                        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                    except OSError:
                        pass
                try:
                    os.close(fd)
                except OSError:
                    pass

        return _win_lock()

    try:
        import fcntl
    except ImportError:  # pragma: no cover - POSIX always has fcntl
        raise LockContention(
            "no fcntl available and platform is not Windows — refusing an "
            "unlocked write (fail-closed)")

    @contextlib.contextmanager
    def _posix_lock():
        handle = open(lock_path, "a+", encoding="utf-8")
        acquired = False
        try:
            # P3 (review-FEAT-051-CODE-R0): bounded non-blocking retry with
            # the same backoff curve as the Windows branch — no unbounded
            # blocking, a busy lock surfaces as LockContention (retryable).
            import time
            for attempt in range(attempts):
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX
                                | fcntl.LOCK_NB)
                    acquired = True
                    break
                except OSError:
                    if attempt == attempts - 1:
                        break
                    time.sleep(base_delay * (1.4 ** min(attempt, 10)))
            if not acquired:
                raise LockContention(
                    "write lock busy after {0} attempts: {1}".format(
                        attempts, lock_path))
            yield
        finally:
            if acquired:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
            handle.close()

    return _posix_lock()


# ── Atomic persistence (DoD 3 — same-volume temp + atomic replace) ─────────


def _sweep_stale_temps(target: Path) -> None:
    """Remove ``<target>.*.tmp`` debris from an earlier hard kill (RECOVERY).

    Only exact-prefix siblings of THIS target are swept — never a directory
    walk, never another file's temp.
    """
    prefix = target.name + "."
    try:
        entries = list(target.parent.iterdir())
    except OSError:
        return
    for entry in entries:
        if entry.name.startswith(prefix) and entry.name.endswith(".tmp"):
            try:
                entry.unlink()
            except OSError:
                pass  # a concurrent writer owns it; its own finally cleans up


def _atomic_write(target: Path, content: str) -> None:
    """Write ``content`` and atomically replace ``target`` (the commit point).

    UTF-8 without BOM; ``newline=""`` so the exact LF/CRLF bytes already
    present in ``content`` are preserved (no translation in either
    direction).  Temp lives in the target's directory (same filesystem →
    ``os.replace`` atomic).  Any failure before the replace removes the temp
    and re-raises; the target is never observed half-written.  After the
    replace the parent directory is fsync'd (P3, review-FEAT-051-CODE-R0):
    the durability nicety that persists the rename's directory entry on
    POSIX; on Windows/NTFS the attempt is best-effort (the journal handles
    metadata durability) and an unsupported directory fsync is swallowed.
    """
    fd, tmp_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=target.name + ".", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(tmp_path), str(target))
        try:
            dir_fd = os.open(str(target.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass  # best-effort durability (platform-dependent support)
    except BaseException:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def _read_file_text(target: Path) -> str:
    """Read the target explicitly as UTF-8 (FIX-278 caliber: never a bare
    platform-decoded read). Raises OSError/UnicodeDecodeError to the caller,
    which maps them to manual/validation result codes."""
    with open(target, "r", encoding="utf-8", newline="") as handle:
        return handle.read()


# ── The five-step write flow (arch round-2 §1) ──────────────────────────────


def execute_update(
    *,
    target: Path,
    task_id: str,
    from_state: str,
    to_state: str,
    reason: str,
    evidence_refs: Tuple[EvidenceRef, ...] = (),
    operation_id: Optional[str] = None,
    expected_revision: Optional[int] = None,
    schema_version: int = DEFAULT_SCHEMA_VERSION,
    ledger: Optional[Path] = None,
    now_fn=None,
) -> WriterResult:
    """One governed row flip: the five-step flow, returning a WriterResult.

    Step mapping (arch round-2 §1 → implementation):

      1. **LLM submits** — the caller supplied task id / transition intent /
         reason / typed evidence refs (validated into WriterRequest below).
      2. **CLI takes the short-term lock** — :func:`_write_lock` over the
         target; exhaustion raises :class:`LockContention` →
         ``lock_contention`` (retryable), never an unlocked write.
      3. **Re-read + re-validate** — under the lock: replay adjudication
         (ledger + fingerprint → execute/replay/conflict), transition
         legality (contract TASK_TRANSITIONS via
         :func:`contracts.require_task_transition`), row anchoring by id,
         state-level CAS (detected row state must equal ``from_state``) and
         the optional content-level CAS (``expected_revision`` against the
         freshly observed aggregate revision).
      4. **Compute + atomic replace** — :func:`build_candidate_row` (marker
         swap + provenance suffix), full-content reassembly preserving every
         other byte and the file's line-ending style, then
         :func:`_atomic_write` (commit point).
      5. **Release + return new revision + result code** — receipt appended
         to the ledger under the same lock, write-after re-read self-check
         against the same parsing schema, lock released, WriterResult
         (``ok``, new aggregate revision, execution ``succeeded``).

    Fails closed before any external action on validation/conflict/retryable
    codes (``execution`` stays ``None`` per the frozen WriterResult law);
    ``manual_intervention`` is reserved for post-commit I/O damage where the
    world already changed.
    """
    if now_fn is None:
        def now_fn():
            return datetime.now(timezone.utc)

    ledger_path = ledger if ledger is not None else _ledger_path_for(target)

    # P2-1 (review-FEAT-051-CODE-R0): a malformed caller-supplied operation
    # id is refused as a structured schema violation BEFORE anything else —
    # a WriterResult cannot legally carry the malformed id either (the
    # contract validates that face too), so the refusal travels under a
    # freshly minted id with the contract's reason verbatim in the detail.
    if operation_id is not None:
        try:
            require_operation_id("operation_id", operation_id)
        except ValueError as exc:
            return WriterResult(
                operation_id=new_operation_id(),
                code="schema_violation",
                detail="malformed operation id refused (pass --operation-id "
                       "as 'op-' + 32 hex, or omit it to mint one): {0}"
                       .format(exc))

    # Pre-lock fail-fast on pure contract checks (no world state consulted):
    # argument schema, transition legality, replay-decision viability.
    task_id = task_id.strip()
    if not task_id:
        return _validation_result(
            operation_id, "schema_violation", "task_id must be non-empty")
    if from_state not in TASK_STATES:
        return _validation_result(
            operation_id, "schema_violation",
            "from_state {0!r} not in TASK_STATES {1}".format(
                from_state, TASK_STATES))
    if to_state not in TASK_STATES:
        return _validation_result(
            operation_id, "schema_violation",
            "to_state {0!r} not in TASK_STATES {1}".format(
                to_state, TASK_STATES))
    try:
        require_task_transition(from_state, to_state)
    except ValueError as exc:
        return _validation_result(
            operation_id, "illegal_transition", str(exc))
    if not SCHEMA_VERSION_WINDOW.supports(schema_version):
        return _validation_result(
            operation_id, "schema_version_unsupported",
            "schema version {0} outside supported window {1}-{2} "
            "(record family: markdown task-row table v1)".format(
                schema_version,
                SCHEMA_VERSION_WINDOW.minimum,
                SCHEMA_VERSION_WINDOW.current))
    if operation_id is None:
        operation_id = new_operation_id()
    fingerprint = canonical_input_fingerprint(
        operation_id=operation_id,
        task_id=task_id,
        from_state=from_state,
        to_state=to_state,
        reason=reason,
        evidence_refs=evidence_refs,
        schema_version=schema_version,
    )
    try:
        # WriterRequest construction is itself a fail-closed contract gate
        # (shapes, enums, id/fingerprint forms) — consumed read-only.
        request = WriterRequest(
            task_id=task_id,
            expected_revision=expected_revision if expected_revision is not None else 1,
            target_state=to_state,
            operation_id=operation_id,
            input_fingerprint=fingerprint,
            evidence_refs=evidence_refs,
        )
    except ValueError as exc:
        return _validation_result(operation_id, "schema_violation", str(exc))

    try:
        text = _read_file_text(target)
    except FileNotFoundError:
        return _validation_result(
            operation_id, "cross_record_violation",
            "target file not found: {0}".format(target))
    except (OSError, UnicodeDecodeError) as exc:
        return WriterResult(
            operation_id=operation_id, code="manual_intervention",
            detail="target unreadable ({0}): {1}".format(
                type(exc).__name__, exc))

    try:
        lock = _write_lock(target)
    except LockContention as exc:
        return WriterResult(
            operation_id=operation_id, code="lock_contention",
            detail=str(exc))
    with lock:
        # Step 3 re-reads the world UNDER the lock (the pre-lock read above
        # was advisory; this one is the truth the write is judged against).
        try:
            text = _read_file_text(target)
        except (OSError, UnicodeDecodeError) as exc:
            return WriterResult(
                operation_id=operation_id, code="manual_intervention",
                detail="target unreadable under lock ({0}): {1}".format(
                    type(exc).__name__, exc))
        observed = revision_of(text)

        # P2-3 (review-FEAT-051-CODE-R0): replay adjudication happens UNDER
        # the lock, matching the documented step order ("re-read + re-validate
        # under the lock").  A concurrent retrier that lost the lock race
        # now finds the winner's receipt on record and replays the original
        # result — instead of the out-of-lock version's misleading
        # effect_present_without_receipt conflict for a receipt that was in
        # fact on record.
        receipts = _read_receipts(ledger_path)
        stored = next(
            (r for r in receipts if r.get("operation_id") == operation_id),
            None)
        stored_fp = stored.get("input_fingerprint") if stored else None
        try:
            decision = decide_operation_replay(stored_fp, fingerprint)
        except ValueError as exc:
            return _validation_result(operation_id, "schema_violation",
                                      str(exc))

        if decision == "replay":
            # Same id + same payload → return the ORIGINAL result (round-2
            # §1); the world is not touched a second time.  P2-2: a
            # degenerate stored face (hand-edited / legacy / torn receipt)
            # degrades to a manual refusal instead of tripping the frozen
            # WriterResult constructor on an unlawful payload.
            prior = _replayable_result_face(stored)
            if prior is None:
                return WriterResult(
                    operation_id=operation_id, code="manual_intervention",
                    detail="stored receipt for operation {0} is degenerate "
                           "(missing or invalid writer_result face) — "
                           "adjudicate the ledger by hand; nothing was "
                           "re-executed or written".format(operation_id))
            return WriterResult(
                operation_id=operation_id,
                code=RESULT_OK,
                new_revision=prior["new_revision"],
                observed_revision=prior.get("observed_revision"),
                execution=prior["execution"],
                detail="replay of operation {0} (original result returned, "
                       "nothing re-executed)".format(operation_id),
            )
        if decision == "conflict":
            return WriterResult(
                operation_id=operation_id, code="operation_id_conflict",
                observed_revision=observed,
                detail="operation id {0} already recorded with a different "
                       "input fingerprint — mint a new operation id; a "
                       "stored result is never reused for a different "
                       "payload".format(operation_id),
            )

        if expected_revision is not None and observed != expected_revision:
            return WriterResult(
                operation_id=operation_id, code="revision_conflict",
                observed_revision=observed,
                detail="content-level CAS: expected_revision {0} != "
                       "observed {1} — re-judge against the current file "
                       "(arch round-2 §1: a CAS conflict never auto-rebases)"
                       .format(expected_revision, observed))

        try:
            row_index, row_line = locate_task_row(text, task_id)
        except ValueError as exc:
            return _validation_result(
                operation_id, "cross_record_violation", str(exc))
        current = detect_row_state(row_line)
        if current is None:
            return _validation_result(
                operation_id, "schema_violation",
                "anchored row's status cell matches no known state marker "
                "(record-family v1; legacy rows need manual triage)")
        if current != from_state:
            detail = ("state-level CAS: row is {0!r}, request expects "
                      "{1!r}".format(current, from_state))
            if current == to_state:
                detail += (
                    "; target state already reached with no receipt on "
                    "record (effect_present_without_receipt — effect-based "
                    "reconciliation required: verify the row against the "
                    "request fingerprint, then adjudicate; never "
                    "auto-re-execute)")
            return WriterResult(
                operation_id=operation_id, code="revision_conflict",
                observed_revision=observed, detail=detail)

        # Step 4: compute the candidate, then atomically commit it.
        try:
            candidate_row = build_candidate_row(
                row_line, from_state=from_state, to_state=to_state,
                operation_id=operation_id)
        except ValueError as exc:
            return _validation_result(operation_id, "schema_violation",
                                      str(exc))
        lines = text.splitlines(keepends=True)
        original_ending = row_line_ending(lines[row_index])
        lines[row_index] = candidate_row + original_ending
        new_text = "".join(lines)
        new_revision = revision_of(new_text)

        _sweep_stale_temps(target)
        try:
            _atomic_write(target, new_text)
        except OSError as exc:
            return WriterResult(
                operation_id=operation_id, code="manual_intervention",
                detail="atomic replace failed, target untouched ({0}): {1}"
                       .format(type(exc).__name__, exc))

        # Receipt under the same lock: replace + ledger-append serialize as
        # one composite action against every writer of this target.
        timestamp = now_fn().isoformat()
        receipt = {
            "record_kind": RECEIPT_RECORD_KIND,
            "schema_version": schema_version,
            "writer": WRITER_ID,
            "operation_id": operation_id,
            "task_id": task_id,
            "from_state": from_state,
            "to_state": to_state,
            "reason": reason,
            "timestamp": timestamp,
            "target_file": str(target),
            "revision_before": observed,
            "revision_after": new_revision,
            "row_before_sha256": hashlib.sha256(
                row_line.encode("utf-8")).hexdigest(),
            "row_after_sha256": hashlib.sha256(
                candidate_row.encode("utf-8")).hexdigest(),
            "input_fingerprint": fingerprint,
            "evidence_refs": [
                {"kind": ref.kind, "value": ref.value,
                 "validation": ref.validation}
                for ref in request.evidence_refs
            ],
            "writer_result": {
                "code": RESULT_OK,
                "new_revision": new_revision,
                "observed_revision": None,
                "execution": "succeeded",
            },
            "enforcement": "WARN",
        }
        try:
            _append_receipt(ledger_path, receipt)
        except OSError as exc:
            # Effect committed, receipt lost — the honest gap (RECOVERY).
            # The frozen WriterResult law bars new_revision on an error
            # code, so the committed revision is disclosed in prose and the
            # caller adjudicates effect-based (never auto-re-executed).
            return WriterResult(
                operation_id=operation_id, code="manual_intervention",
                execution="succeeded",
                detail="row committed (revision {0}) but receipt append "
                       "failed ({1}: {2}) — effect_present_without_receipt; "
                       "adjudicate before further writes".format(
                           new_revision, type(exc).__name__, exc))

        # Step 5: write-after re-read self-check with the SAME parsing
        # schema (never a second definition), then release + report.
        try:
            reread = _read_file_text(target)
        except (OSError, UnicodeDecodeError) as exc:
            return WriterResult(
                operation_id=operation_id, code="manual_intervention",
                execution="succeeded",
                detail="committed (revision {0}) but post-write re-read "
                       "failed ({1}: {2}) — adjudicate".format(
                           new_revision, type(exc).__name__, exc))
        if reread != new_text:
            return WriterResult(
                operation_id=operation_id, code="manual_intervention",
                execution="succeeded",
                detail="post-write self-check mismatch after committing "
                       "revision {0}: on-disk content differs from the "
                       "committed candidate — concurrent writer suspected; "
                       "adjudicate".format(new_revision))
        try:
            _, reread_row = locate_task_row(reread, task_id)
            reread_state = detect_row_state(reread_row)
        except ValueError:
            reread_state = None
        if reread_state != to_state:
            return WriterResult(
                operation_id=operation_id, code="manual_intervention",
                execution="succeeded",
                detail="post-write self-check after committing revision "
                       "{0}: re-read row state {1!r} != target {2!r} — "
                       "adjudicate".format(new_revision, reread_state,
                                           to_state))

        return WriterResult(
            operation_id=operation_id, code=RESULT_OK,
            new_revision=new_revision, execution="succeeded",
            detail="row {0}: {1} -> {2} (receipt {3})".format(
                task_id, from_state, to_state, operation_id),
        )


def refresh_candidate_row(line: str, *, operation_id: str) -> str:
    """FIX-394 alignment COMPUTE step: refresh one committed terminal row.

    The one-shot alignment surface for rows that are ALREADY at the writer
    terminal state — ``committed`` has an empty legal-transition tuple, so
    no flip can ever re-run on them; their stale mid-flight wording can
    only be fixed in place.  The refresh is surgical and self-verifying:

      1. the row must DETECT as ``committed`` (chain-first, the same
         detection chain the flip path uses) — any other state is refused:
         non-terminal rows change state through the governed flip path;
      2. the status cell must carry EXACTLY ONE ops receipt anchor — an
         unanchored 「committed …」 display prefix was never written by the
         governed writer (the B-1 hand-edit class) and is never re-anchored;
      3. stale progress phrases are cleared from the paren-free span
         before the anchor (:func:`_refresh_progress_prefix`); the
         committed token, the date/narrative parentheses, the anchor's
         position and any brackets after it all survive;
      4. the anchor is re-stamped to THIS operation's id (the row always
         names its most recent writer operation — same discipline as a
         flip); the post-refresh row must STILL detect as ``committed``.

    Every other cell, the cell padding and the line ending are preserved
    byte-for-byte by construction (the same splice discipline as
    :func:`build_candidate_row`).
    """
    current = detect_row_state(line)
    if current is None:
        raise ValueError(
            "refresh_candidate_row: status cell of the anchored row does "
            "not match any known state marker (schema_violation: "
            "record-family v1 vocabulary)")
    if current != "committed":
        raise ValueError(
            "refresh_candidate_row: row is {0!r}, not the terminal state "
            "'committed' — non-terminal rows change state through the "
            "governed flip path, never through the alignment surface "
            "(schema_violation)".format(current))
    cells = line.split("|")
    located = _status_cell(cells)
    if located is None:  # pragma: no cover - detect_row_state found a cell
        raise ValueError("refresh_candidate_row: status cell vanished")
    cell_index = located[0]
    _lead, core, _trail = _cell_parts(cells[cell_index])
    anchors = list(_OP_ANCHOR_RE.finditer(core))
    if not anchors:
        raise ValueError(
            "refresh_candidate_row: the committed row carries no ops "
            "receipt anchor 〔op-<32hex>〕 — a cell the governed writer "
            "never wrote is never re-anchored (B-1 hand-edit class; "
            "schema_violation: reconcile by hand)")
    if len(anchors) > 1:
        raise ValueError(
            "refresh_candidate_row: ambiguous — {0} ops anchors on one "
            "status cell; refusing to guess which operation owns the row "
            "(schema_violation: reconcile by hand)".format(len(anchors)))
    refreshed_core, _removed = _refresh_progress_prefix(core, "committed")
    anchor_at = _OP_ANCHOR_RE.search(refreshed_core)
    if anchor_at is None:  # pragma: no cover - the anchor span is preserved
        raise ValueError(
            "refresh_candidate_row: ops anchor lost during refresh "
            "(schema_violation)")
    refreshed_core = (
        refreshed_core[:anchor_at.start()] + "〔" + operation_id + "〕"
        + refreshed_core[anchor_at.end():])
    candidate_cells = list(cells)
    lead, _core, trail = _cell_parts(cells[cell_index])
    candidate_cells[cell_index] = lead + refreshed_core + trail
    candidate = "|".join(candidate_cells)
    # FIX-393 collaboration guard: the refreshed row must STILL satisfy
    # the writer-terminal criterion the three parsers key on.
    reread = detect_row_state(candidate)
    if reread != "committed":
        raise ValueError(
            "refresh_candidate_row: post-refresh re-check read {0!r}, "
            "expected 'committed' — refusing to write a row the parsers "
            "would no longer recognise as terminal (schema_violation)"
            .format(reread))
    return candidate


def execute_refresh(
    *,
    target: Path,
    task_id: str,
    reason: str,
    evidence_refs: Tuple[EvidenceRef, ...] = (),
    operation_id: Optional[str] = None,
    expected_revision: Optional[int] = None,
    schema_version: int = DEFAULT_SCHEMA_VERSION,
    ledger: Optional[Path] = None,
    now_fn=None,
) -> WriterResult:
    """One governed suffix-alignment write (FIX-394), five-step flow.

    The alignment twin of :func:`execute_update`: same lock/CAS/replay/
    atomic-replace/receipt discipline, but the target row is already at the
    terminal state, so there is no transition to validate — the pre-flight
    instead proves the row IS terminal (chain-first ``committed`` + exactly
    one ops anchor) and carries at least one stale progress phrase.  A row
    with nothing stale resolves to ``ok`` with nothing written and no
    receipt (an honest no-effect operation records no effect); a retried
    operation id replays the original result exactly like a flip.

    The receipt carries ``action=REFRESH_ACTION`` and the removed phrase
    list, so the ops ledger can audit exactly what wording the alignment
    cleared.
    """
    if now_fn is None:
        def now_fn():
            return datetime.now(timezone.utc)

    ledger_path = ledger if ledger is not None else _ledger_path_for(target)

    if operation_id is not None:
        try:
            require_operation_id("operation_id", operation_id)
        except ValueError as exc:
            return WriterResult(
                operation_id=new_operation_id(),
                code="schema_violation",
                detail="malformed operation id refused (pass --operation-id "
                       "as 'op-' + 32 hex, or omit it to mint one): {0}"
                       .format(exc))
    task_id = task_id.strip()
    if not task_id:
        return _validation_result(
            operation_id, "schema_violation", "task_id must be non-empty")
    if not SCHEMA_VERSION_WINDOW.supports(schema_version):
        return _validation_result(
            operation_id, "schema_version_unsupported",
            "schema version {0} outside supported window {1}-{2} "
            "(record family: markdown task-row table v1)".format(
                schema_version,
                SCHEMA_VERSION_WINDOW.minimum,
                SCHEMA_VERSION_WINDOW.current))
    if operation_id is None:
        operation_id = new_operation_id()
    fingerprint = canonical_input_fingerprint(
        operation_id=operation_id,
        task_id=task_id,
        from_state="committed",
        to_state="committed",
        reason=reason,
        evidence_refs=evidence_refs,
        schema_version=schema_version,
        action=REFRESH_ACTION,
    )
    try:
        request = WriterRequest(
            task_id=task_id,
            expected_revision=expected_revision if expected_revision is not None else 1,
            target_state="committed",
            operation_id=operation_id,
            input_fingerprint=fingerprint,
            evidence_refs=evidence_refs,
        )
    except ValueError as exc:
        return _validation_result(operation_id, "schema_violation", str(exc))

    try:
        text = _read_file_text(target)
    except FileNotFoundError:
        return _validation_result(
            operation_id, "cross_record_violation",
            "target file not found: {0}".format(target))
    except (OSError, UnicodeDecodeError) as exc:
        return WriterResult(
            operation_id=operation_id, code="manual_intervention",
            detail="target unreadable ({0}): {1}".format(
                type(exc).__name__, exc))

    try:
        lock = _write_lock(target)
    except LockContention as exc:
        return WriterResult(
            operation_id=operation_id, code="lock_contention",
            detail=str(exc))
    with lock:
        try:
            text = _read_file_text(target)
        except (OSError, UnicodeDecodeError) as exc:
            return WriterResult(
                operation_id=operation_id, code="manual_intervention",
                detail="target unreadable under lock ({0}): {1}".format(
                    type(exc).__name__, exc))
        observed = revision_of(text)

        receipts = _read_receipts(ledger_path)
        stored = next(
            (r for r in receipts if r.get("operation_id") == operation_id),
            None)
        stored_fp = stored.get("input_fingerprint") if stored else None
        try:
            decision = decide_operation_replay(stored_fp, fingerprint)
        except ValueError as exc:
            return _validation_result(operation_id, "schema_violation",
                                      str(exc))
        if decision == "replay":
            prior = _replayable_result_face(stored)
            if prior is None:
                return WriterResult(
                    operation_id=operation_id, code="manual_intervention",
                    detail="stored receipt for operation {0} is degenerate "
                           "(missing or invalid writer_result face) — "
                           "adjudicate the ledger by hand; nothing was "
                           "re-executed or written".format(operation_id))
            return WriterResult(
                operation_id=operation_id,
                code=RESULT_OK,
                new_revision=prior["new_revision"],
                observed_revision=prior.get("observed_revision"),
                execution=prior["execution"],
                detail="replay of operation {0} (original result returned, "
                       "nothing re-executed)".format(operation_id),
            )
        if decision == "conflict":
            return WriterResult(
                operation_id=operation_id, code="operation_id_conflict",
                observed_revision=observed,
                detail="operation id {0} already recorded with a different "
                       "input fingerprint — mint a new operation id; a "
                       "stored result is never reused for a different "
                       "payload".format(operation_id),
            )

        if expected_revision is not None and observed != expected_revision:
            return WriterResult(
                operation_id=operation_id, code="revision_conflict",
                observed_revision=observed,
                detail="content-level CAS: expected_revision {0} != "
                       "observed {1} — re-judge against the current file"
                       .format(expected_revision, observed))

        try:
            row_index, row_line = locate_task_row(text, task_id)
        except ValueError as exc:
            return _validation_result(
                operation_id, "cross_record_violation", str(exc))
        current = detect_row_state(row_line)
        if current is None:
            return _validation_result(
                operation_id, "schema_violation",
                "anchored row's status cell matches no known state marker "
                "(record-family v1; legacy rows need manual triage)")
        if current != "committed":
            return _validation_result(
                operation_id, "schema_violation",
                "row is {0!r}, not the terminal state 'committed' — the "
                "alignment surface only refreshes terminal rows; "
                "non-terminal rows change state through the governed flip "
                "path".format(current))
        try:
            cells = row_line.split("|")
            cell_index = _status_cell(cells)[0]
            cell_core = _cell_parts(cells[cell_index])[1]
        except (IndexError, TypeError):  # pragma: no cover - detected above
            return _validation_result(
                operation_id, "schema_violation",
                "anchored row's status cell vanished (schema_violation)")
        # F-1 (review-FIX-394-CODE-R0): the anchor-count gate precedes the
        # stale detection — an ambiguous multi-anchor cell is refused even
        # when it carries no stale wording, in the SAME classification the
        # dry-run face reports (check order aligned with _dry_run_refresh);
        # the no-op short-circuit below must never launder a cell this
        # surface cannot unambiguously re-anchor.
        anchor_count = len(_OP_ANCHOR_RE.findall(cell_core))
        if anchor_count == 0:
            return _validation_result(
                operation_id, "schema_violation",
                "the committed row carries no ops receipt anchor "
                "〔op-<32hex>〕 — a cell the governed writer never wrote "
                "is never re-anchored (B-1 hand-edit class; "
                "schema_violation)")
        if anchor_count > 1:
            return _validation_result(
                operation_id, "schema_violation",
                "ambiguous — {0} ops anchors on one status cell; refusing "
                "to guess which operation owns the row "
                "(schema_violation: reconcile by hand)".format(anchor_count))
        stale = find_stale_progress_phrases(
            cell_core, target_state="committed")
        if not stale:
            return WriterResult(
                operation_id=operation_id, code=RESULT_OK,
                new_revision=observed, observed_revision=observed,
                execution="succeeded",
                detail="suffix refresh: row {0} is already aligned (no "
                       "stale progress wording before the ops anchor) — "
                       "nothing written, no receipt".format(task_id),
            )
        try:
            candidate_row = refresh_candidate_row(
                row_line, operation_id=operation_id)
        except ValueError as exc:
            return _validation_result(operation_id, "schema_violation",
                                      str(exc))
        lines = text.splitlines(keepends=True)
        original_ending = row_line_ending(lines[row_index])
        lines[row_index] = candidate_row + original_ending
        new_text = "".join(lines)
        new_revision = revision_of(new_text)

        _sweep_stale_temps(target)
        try:
            _atomic_write(target, new_text)
        except OSError as exc:
            return WriterResult(
                operation_id=operation_id, code="manual_intervention",
                detail="atomic replace failed, target untouched ({0}): {1}"
                       .format(type(exc).__name__, exc))

        timestamp = now_fn().isoformat()
        receipt = {
            "record_kind": RECEIPT_RECORD_KIND,
            "action": REFRESH_ACTION,
            "schema_version": schema_version,
            "writer": WRITER_ID,
            "operation_id": operation_id,
            "task_id": task_id,
            "from_state": "committed",
            "to_state": "committed",
            "reason": reason,
            "stale_phrases_removed": list(stale),
            "timestamp": timestamp,
            "target_file": str(target),
            "revision_before": observed,
            "revision_after": new_revision,
            "row_before_sha256": hashlib.sha256(
                row_line.encode("utf-8")).hexdigest(),
            "row_after_sha256": hashlib.sha256(
                candidate_row.encode("utf-8")).hexdigest(),
            "input_fingerprint": fingerprint,
            "evidence_refs": [
                {"kind": ref.kind, "value": ref.value,
                 "validation": ref.validation}
                for ref in request.evidence_refs
            ],
            "writer_result": {
                "code": RESULT_OK,
                "new_revision": new_revision,
                "observed_revision": None,
                "execution": "succeeded",
            },
            "enforcement": "WARN",
        }
        try:
            _append_receipt(ledger_path, receipt)
        except OSError as exc:
            return WriterResult(
                operation_id=operation_id, code="manual_intervention",
                execution="succeeded",
                detail="row committed (revision {0}) but receipt append "
                       "failed ({1}: {2}) — effect_present_without_receipt; "
                       "adjudicate before further writes".format(
                           new_revision, type(exc).__name__, exc))

        # Write-after re-read self-check: same parsing schema, plus the
        # alignment-specific invariants (still terminal, still exactly one
        # anchor, no stale wording survived).
        try:
            reread = _read_file_text(target)
        except (OSError, UnicodeDecodeError) as exc:
            return WriterResult(
                operation_id=operation_id, code="manual_intervention",
                execution="succeeded",
                detail="committed (revision {0}) but post-write re-read "
                       "failed ({1}: {2}) — adjudicate".format(
                           new_revision, type(exc).__name__, exc))
        if reread != new_text:
            return WriterResult(
                operation_id=operation_id, code="manual_intervention",
                execution="succeeded",
                detail="post-write self-check mismatch after committing "
                       "revision {0}: on-disk content differs from the "
                       "committed candidate — concurrent writer suspected; "
                       "adjudicate".format(new_revision))
        try:
            _, reread_row = locate_task_row(reread, task_id)
            reread_state = detect_row_state(reread_row)
            reread_cells = reread_row.split("|")
            reread_core = _cell_parts(
                reread_cells[_status_cell(reread_cells)[0]])[1]
            reread_stale = find_stale_progress_phrases(
                reread_core, target_state="committed")
            reread_anchor_count = len(_OP_ANCHOR_RE.findall(reread_core))
        except ValueError:
            reread_state, reread_stale, reread_anchor_count = None, (), 0
        if (reread_state != "committed" or reread_stale
                or reread_anchor_count != 1):
            return WriterResult(
                operation_id=operation_id, code="manual_intervention",
                execution="succeeded",
                detail="post-write self-check after committing revision "
                       "{0}: refreshed row invariants violated (state "
                       "{1!r}, stale {2}, anchors {3}) — adjudicate"
                       .format(new_revision, reread_state, reread_stale,
                               reread_anchor_count))

        return WriterResult(
            operation_id=operation_id, code=RESULT_OK,
            new_revision=new_revision, execution="succeeded",
            detail="suffix refresh: row {0} aligned ({1} removed; receipt "
                   "{2})".format(task_id, "、".join(stale), operation_id),
        )


def row_line_ending(line_with_ending: str) -> str:
    """Extract the original line ending of a splitlines(keepends=True) row."""
    for ending in ("\r\n", "\n", "\r"):
        if line_with_ending.endswith(ending):
            return ending
    return ""  # last line without a trailing newline stays that way


def _validation_result(
    operation_id: Optional[str], code: str, detail: str,
) -> WriterResult:
    """A pre-execution rejection: nothing ran, nothing was locked."""
    return WriterResult(
        operation_id=operation_id or new_operation_id(),
        code=code, detail=detail,
    )


# ── Observation surface (the CAS expectation source) ────────────────────────


def inspect_target(
    *,
    target: Path,
    task_id: str,
    ledger: Optional[Path] = None,
) -> Dict[str, Any]:
    """Read-only observation: anchor, detected state, aggregate revision.

    This is where a caller obtains ``expected_revision`` for the content
    CAS.  Reads nothing but the target and (for context) the receipt count;
    writes nothing, locks nothing.
    """
    ledger_path = ledger if ledger is not None else _ledger_path_for(target)
    report: Dict[str, Any] = {
        "mode": "inspect",
        "target_file": str(target),
        "task_id": task_id,
        "found": False,
        "observed_revision": None,
    }
    try:
        text = _read_file_text(target)
    except FileNotFoundError:
        report["error"] = "target file not found: {0}".format(target)
        return report
    except (OSError, UnicodeDecodeError) as exc:
        report["error"] = "target unreadable ({0}): {1}".format(
            type(exc).__name__, exc)
        return report
    report["observed_revision"] = revision_of(text)
    try:
        _, row_line = locate_task_row(text, task_id)
    except ValueError as exc:
        report["error"] = str(exc)
        return report
    report["found"] = True
    report["state"] = detect_row_state(row_line)
    report["row_sha256"] = hashlib.sha256(
        row_line.encode("utf-8")).hexdigest()
    report["receipts_on_record"] = sum(
        1 for r in _read_receipts(ledger_path)
        if r.get("task_id") == task_id)
    return report


# ── CLI (the composition-root assembly point) ───────────────────────────────


class ExitCode:
    """Structured exit codes (DoD 5: the four dispositions stay distinct)."""

    OK = 0
    USAGE = 2
    VALIDATION = 3
    CONFLICT = 4
    RETRYABLE = 5
    MANUAL = 6
    # A replay is a success (the original result was returned unchanged) —
    # declared here so the whole structured-code table lives in one place.
    REPLAY = 0


TASK_ROW_UPDATE_RESULT_CODES = {
    RESULT_OK: ExitCode.OK,
    "schema_violation": ExitCode.VALIDATION,
    "cross_record_violation": ExitCode.VALIDATION,
    "illegal_transition": ExitCode.VALIDATION,
    "schema_version_unsupported": ExitCode.VALIDATION,
    "revision_conflict": ExitCode.CONFLICT,
    "operation_id_conflict": ExitCode.CONFLICT,
    "lock_contention": ExitCode.RETRYABLE,
    "manual_intervention": ExitCode.MANUAL,
}
"""Result code → process exit code.  Every entry is the closed contract
enum mapped to its disposition class, so callers can branch on
校验失败/冲突/可重试/需介入 without parsing prose.  (``replay`` is not a
table row: a replayed operation IS code ``'ok'`` — its original result is
returned verbatim and ``main`` merely reads the provenance note from the
detail; there is no separate replay exit code to map.)"""


def _disposition_exit_code(code: str) -> int:
    if code == RESULT_OK:
        return ExitCode.OK
    return TASK_ROW_UPDATE_RESULT_CODES.get(code, ExitCode.MANUAL)


def _parse_refs(pairs: Optional[List[str]]) -> Tuple[EvidenceRef, ...]:
    """Rehydrate ``kind=value`` strings into typed EvidenceRefs (explicitly
    typed — the FEAT-049 writer responsibility).  Unknown kinds and
    malformed pairs fail closed as schema violations."""
    if not pairs:
        return ()
    refs: List[EvidenceRef] = []
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(
                "--refs entry {0!r}: expected 'kind=value' with kind one of "
                "the contract's evidence reference kinds".format(pair))
        kind, _, value = pair.partition("=")
        kind, value = kind.strip(), value.strip()
        try:
            refs.append(EvidenceRef(kind=kind, value=value))
        except ValueError as exc:
            raise ValueError("--refs entry {0!r}: {1}".format(pair, exc))
    return tuple(refs)


def _emit(payload: Dict[str, Any], as_json: bool) -> None:
    # Output-side UTF-8 discipline (FIX-278's write-side sibling): a Windows
    # console defaults to a legacy codepage (GBK), which cannot encode the
    # state markers this writer prints (✅/🔄/⛔).  Reconfigure stdout to
    # UTF-8 before printing; a stream without reconfigure keeps its behavior
    # (in-memory capture in tests already accepts any unicode).
    for stream in (sys.stdout,):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (OSError, ValueError):  # pragma: no cover - exotic streams
                pass
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    mode = payload.get("mode", "")
    if mode == "dry-run":
        preview = payload.get("preview") or {}
        print("dry-run: would_execute={0} writes_performed={1}".format(
            payload.get("would_execute"), payload.get("writes_performed")))
        if preview.get("row_after") is not None:
            print("  row_before: {0}".format(preview.get("row_before")))
            print("  row_after:  {0}".format(preview.get("row_after")))
        if payload.get("refusal"):
            print("  refusal: {0}".format(payload["refusal"]))
        return
    if mode == "inspect":
        for key in ("task_id", "found", "state", "observed_revision",
                    "receipts_on_record"):
            if key in payload:
                print("{0}: {1}".format(key, payload[key]))
        if payload.get("error"):
            print("error: {0}".format(payload["error"]))
        return
    result = payload.get("result", {})
    print("operation: {0}".format(result.get("operation_id")))
    print("code: {0}".format(result.get("code")))
    if result.get("new_revision") is not None:
        print("new_revision: {0}".format(result.get("new_revision")))
    if result.get("observed_revision") is not None:
        print("observed_revision: {0}".format(result.get("observed_revision")))
    if result.get("detail"):
        print("detail: {0}".format(result.get("detail")))


def _dry_run(
    *,
    target: Path,
    task_id: str,
    from_state: str,
    to_state: str,
    reason: str,
    refs: Tuple[EvidenceRef, ...],
    operation_id: str,
    schema_version: int,
) -> Dict[str, Any]:
    """Full pre-flight with ZERO writes and ZERO locks (validation-only).

    The preview mirrors the execute path's checks in order and reports the
    candidate row; its ``preview_result.code`` is a *preview* verdict, not a
    WriterResult — a dry run executed nothing, so the contract's
    ``ok ⇒ execution`` invariant must not be laundered into a fake success.
    """
    payload: Dict[str, Any] = {
        "mode": "dry-run",
        "writes_performed": 0,
        "lock_acquired": False,
    }
    try:
        text = _read_file_text(target)
    except FileNotFoundError:
        payload["would_execute"] = False
        payload["refusal"] = {
            "code": "cross_record_violation",
            "detail": "target file not found: {0}".format(target)}
        return payload
    except (OSError, UnicodeDecodeError) as exc:
        payload["would_execute"] = False
        payload["refusal"] = {
            "code": "manual_intervention",
            "detail": "target unreadable ({0}): {1}".format(
                type(exc).__name__, exc)}
        return payload
    payload["observed_revision"] = revision_of(text)

    refusal: Optional[Dict[str, str]] = None
    if from_state not in TASK_STATES or to_state not in TASK_STATES:
        refusal = {"code": "schema_violation",
                   "detail": "from/to must both be members of TASK_STATES"}
    elif SCHEMA_VERSION_WINDOW.supports(schema_version) is False:
        refusal = {"code": "schema_version_unsupported",
                   "detail": "schema version {0} outside window {1}-{2}"
                             .format(schema_version,
                                     SCHEMA_VERSION_WINDOW.minimum,
                                     SCHEMA_VERSION_WINDOW.current)}
    else:
        try:
            require_task_transition(from_state, to_state)
        except ValueError as exc:
            refusal = {"code": "illegal_transition", "detail": str(exc)}
    if refusal is None:
        try:
            row_index, row_line = locate_task_row(text, task_id)
            current = detect_row_state(row_line)
            if current is None:
                refusal = {"code": "schema_violation",
                           "detail": "status cell matches no known state "
                                     "marker (record-family v1)"}
            elif current != from_state:
                refusal = {"code": "revision_conflict",
                           "detail": "state-level CAS: row is {0!r}, "
                                     "request expects {1!r}".format(
                                         current, from_state)}
            else:
                candidate = build_candidate_row(
                    row_line, from_state=from_state, to_state=to_state,
                    operation_id=operation_id)
                payload["preview"] = {
                    "row_index_0based": row_index,
                    "row_before": row_line,
                    "row_after": candidate,
                }
        except ValueError as exc:
            refusal = {"code": "cross_record_violation", "detail": str(exc)}
    payload["would_execute"] = refusal is None
    if refusal is not None:
        payload["refusal"] = refusal
    else:
        payload["preview_result"] = {
            "operation_id": operation_id,
            "code": RESULT_OK,
            "dry_run": True,
            "detail": "preview only — no lock taken, nothing written; the "
                      "execute path re-validates everything under the lock",
        }
    return payload


def _dry_run_refresh(
    *,
    target: Path,
    task_id: str,
    reason: str,
    operation_id: str,
    schema_version: int,
    expected_revision: Optional[int] = None,
) -> Dict[str, Any]:
    """FIX-394 alignment pre-flight with ZERO writes and ZERO locks.

    Mirrors :func:`execute_refresh`'s checks in order (the same preview
    discipline as the flip path's ``_dry_run``): a preview verdict is NOT a
    WriterResult — the execute path re-validates everything under the lock.
    A row with nothing stale previews ``row_after == row_before`` (the
    honest zero-change face the execute path resolves as a no-op).
    """
    payload: Dict[str, Any] = {
        "mode": "dry-run",
        "writes_performed": 0,
        "lock_acquired": False,
    }
    try:
        text = _read_file_text(target)
    except FileNotFoundError:
        payload["would_execute"] = False
        payload["refusal"] = {
            "code": "cross_record_violation",
            "detail": "target file not found: {0}".format(target)}
        return payload
    except (OSError, UnicodeDecodeError) as exc:
        payload["would_execute"] = False
        payload["refusal"] = {
            "code": "manual_intervention",
            "detail": "target unreadable ({0}): {1}".format(
                type(exc).__name__, exc)}
        return payload
    payload["observed_revision"] = revision_of(text)

    refusal: Optional[Dict[str, str]] = None
    if not SCHEMA_VERSION_WINDOW.supports(schema_version):
        refusal = {"code": "schema_version_unsupported",
                   "detail": "schema version {0} outside window {1}-{2}"
                             .format(schema_version,
                                     SCHEMA_VERSION_WINDOW.minimum,
                                     SCHEMA_VERSION_WINDOW.current)}
    elif (expected_revision is not None
            and payload["observed_revision"] != expected_revision):
        refusal = {"code": "revision_conflict",
                   "detail": "content-level CAS: expected_revision {0} != "
                             "observed {1}".format(
                                 expected_revision,
                                 payload["observed_revision"])}
    if refusal is None:
        try:
            row_index, row_line = locate_task_row(text, task_id)
            current = detect_row_state(row_line)
            if current is None:
                refusal = {"code": "schema_violation",
                           "detail": "status cell matches no known state "
                                     "marker (record-family v1)"}
            elif current != "committed":
                refusal = {"code": "schema_violation",
                           "detail": "row is {0!r}, not the terminal "
                                     "state 'committed' — the alignment "
                                     "surface only refreshes terminal "
                                     "rows".format(current)}
            else:
                cells = row_line.split("|")
                cell_core = _cell_parts(
                    cells[_status_cell(cells)[0]])[1]
                anchor_count = len(_OP_ANCHOR_RE.findall(cell_core))
                if anchor_count == 0:
                    refusal = {"code": "schema_violation",
                               "detail": "the committed row carries no "
                                         "ops receipt anchor 〔op-<32hex>〕 "
                                         "(B-1 hand-edit class; never "
                                         "re-anchored)"}
                elif anchor_count > 1:
                    refusal = {"code": "schema_violation",
                               "detail": "ambiguous — {0} ops anchors on "
                                         "one status cell".format(
                                             anchor_count)}
                else:
                    stale = find_stale_progress_phrases(
                        cell_core, target_state="committed")
                    if stale:
                        candidate = refresh_candidate_row(
                            row_line, operation_id=operation_id)
                    else:
                        # Already aligned: the execute path is an honest
                        # no-op (no re-anchor, no write, no receipt) — the
                        # preview mirrors that exactly instead of showing
                        # an anchor swap that would never happen.
                        candidate = row_line
                    payload["preview"] = {
                        "row_index_0based": row_index,
                        "row_before": row_line,
                        "row_after": candidate,
                        "stale_phrases_found": list(stale),
                        "already_aligned": not stale,
                    }
        except ValueError as exc:
            refusal = {"code": "cross_record_violation", "detail": str(exc)}
    payload["would_execute"] = refusal is None
    if refusal is not None:
        payload["refusal"] = refusal
    else:
        payload["preview_result"] = {
            "operation_id": operation_id,
            "code": RESULT_OK,
            "dry_run": True,
            "detail": "preview only — no lock taken, nothing written; the "
                      "execute path re-validates everything under the lock",
        }
    return payload


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """The module-owned option fact source (single source of truth).

    The engine's ``task-row-update`` subparser calls this same face when it
    wires dispatch (batch-2.0 integration, FEAT-055 — governance_cost
    pattern), so every option is defined exactly once and an engine
    Namespace can flow straight into the executor without an argv
    round-trip (FEAT-047 P2-1 caliber). ``main`` stays self-contained on
    top of it.
    """
    parser.add_argument("--task", required=True,
                        help="Task id to anchor (ID column, exact match; an "
                             "ambiguous anchor is refused, never guessed)")
    parser.add_argument("--from", dest="from_state", default=None,
                        choices=list(TASK_STATES),
                        help="Expected current state (state-level CAS; "
                             "required for --dry-run and execute)")
    parser.add_argument("--to", dest="to_state", default=None,
                        choices=list(TASK_STATES),
                        help="Target state — a legal TASK_TRANSITIONS "
                             "successor; required for --dry-run and execute")
    parser.add_argument("--reason", default=None,
                        help="Human-readable reason recorded on the receipt; "
                             "required for --dry-run and execute")
    parser.add_argument("--refs", action="append", default=[],
                        metavar="KIND=VALUE",
                        help="Typed evidence reference (e.g. "
                             "repo_file=path/to/file); repeatable")
    parser.add_argument("--operation-id", default=None,
                        help="Operation id for retry/idempotency (op- + 32 "
                             "hex); minted fresh when omitted — pass the "
                             "SAME id to retry an operation, a NEW id for a "
                             "different intent")
    parser.add_argument("--expected-revision", type=int, default=None,
                        help="Content-level CAS expectation (from --inspect "
                             "observed_revision); omitted = rely on the "
                             "short-term lock + state-level CAS")
    parser.add_argument("--schema-version", type=int,
                        default=DEFAULT_SCHEMA_VERSION,
                        help="Record-family schema version (default %(default)s; "
                             "outside the supported window the write is "
                             "refused)")
    parser.add_argument("--file", default=os.path.join(
                            ".governance", "plan-tracker.md"),
                        help="Governed table file (default: "
                             "%(default)s)")
    parser.add_argument("--ledger", default=None,
                        help="Operation-receipt ledger (default: "
                             "<file>.ops.jsonl sidecar)")
    parser.add_argument("--inspect", action="store_true",
                        help="Read-only observation: anchor, state, "
                             "observed_revision (the CAS expectation source)")
    parser.add_argument("--refresh-suffix", action="store_true",
                        help="FIX-394 alignment surface: refresh a "
                             "writer-committed TERMINAL row's status cell "
                             "(clear stale mid-flight progress wording, "
                             "re-anchor to this operation, receipt). "
                             "Refuses non-terminal or unanchored rows; "
                             "--from/--to do not apply (terminal rows "
                             "have no outgoing legal transition)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Full pre-flight, zero writes, zero locks; "
                             "prints the candidate row (progressive rollout: "
                             "pair with --inspect to rehearse a transition "
                             "before executing it)")
    parser.add_argument("--json", action="store_true",
                        help="Machine-readable JSON output (default posture "
                             "of the writer; text rendering is the courtesy "
                             "view)")
    parser.add_argument("--text", dest="json", action="store_false",
                        help="Human-readable rendering instead of JSON")
    parser.set_defaults(json=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="task-row-update",
        description=(
            "Governed single write path for plan-tracker task-row state "
            "flips (FEAT-051, contracts m0-r1 consumer). Refuses anything "
            "the frozen transition table, CAS or replay protocol rejects."))
    add_arguments(parser)
    return parser


def _execute(args: argparse.Namespace,
             parser: argparse.ArgumentParser) -> int:
    """Shared executor behind ``main`` and the engine dispatch face.

    ``parser`` is used only for usage-level refusals (``parser.error`` keeps
    the argparse exit-2 + usage-text contract identical on both paths).
    """
    target = Path(args.file)
    ledger = Path(args.ledger) if args.ledger else None

    try:
        refs = _parse_refs(args.refs)
    except ValueError as exc:
        payload = {
            "mode": "result",
            "result": {"operation_id": None, "code": "schema_violation",
                       "detail": str(exc)},
        }
        _emit(payload, args.json)
        return ExitCode.VALIDATION

    if args.inspect:
        report = inspect_target(target=target, task_id=args.task,
                                ledger=ledger)
        _emit({"mode": "inspect", **report}, args.json)
        return ExitCode.OK if report.get("found") else ExitCode.VALIDATION

    # FIX-394 alignment surface: terminal-row suffix refresh.  --from/--to
    # do not apply (committed has no outgoing legal transition) — a usage-
    # level refusal keeps the flag combinations honest.  Everything else
    # (CAS, operation id, schema version, ledger, dry-run) behaves exactly
    # like the flip path.
    if args.refresh_suffix:
        if args.from_state is not None or args.to_state is not None:
            parser.error(
                "--refresh-suffix is the terminal-row alignment surface: "
                "--from/--to do not apply (the terminal state has no "
                "outgoing legal transition); pass --task and --reason "
                "only")
        if args.reason is None:
            parser.error("--reason is required for --refresh-suffix")
        if args.operation_id is not None:
            try:
                require_operation_id("operation_id", args.operation_id)
            except ValueError as exc:
                _emit({"mode": "result", "result": {
                    "operation_id": None, "code": "schema_violation",
                    "detail": "malformed operation id refused (pass "
                              "--operation-id as 'op-' + 32 hex, or omit "
                              "it to mint one): {0}".format(exc),
                }}, args.json)
                return ExitCode.VALIDATION
        operation_id = args.operation_id or new_operation_id()
        if args.dry_run:
            payload = _dry_run_refresh(
                target=target, task_id=args.task, reason=args.reason,
                operation_id=operation_id,
                schema_version=args.schema_version,
                expected_revision=args.expected_revision)
            _emit({"mode": "dry-run", **payload}, args.json)
            return ExitCode.OK if payload["would_execute"] \
                else _disposition_exit_code(payload["refusal"]["code"])
        result = execute_refresh(
            target=target, task_id=args.task, reason=args.reason,
            evidence_refs=refs, operation_id=args.operation_id,
            expected_revision=args.expected_revision,
            schema_version=args.schema_version, ledger=ledger)
        replayed = (result.detail or "").startswith("replay of operation")
        result_face = {
            "operation_id": result.operation_id,
            "code": result.code,
            "action": REFRESH_ACTION,
            "new_revision": result.new_revision,
            "observed_revision": result.observed_revision,
            "execution": result.execution,
            "detail": result.detail,
        }
        if result.code == RESULT_OK and not replayed \
                and "already aligned" in (result.detail or ""):
            result_face["changed"] = False
        _emit({"mode": "result", "result": result_face}, args.json)
        if result.code == RESULT_OK:
            return ExitCode.REPLAY if replayed else ExitCode.OK
        return _disposition_exit_code(result.code)

    # Both remaining modes (dry-run, execute) need the full transition
    # triple; a missing member is a usage-level schema refusal.
    missing = [name for name, value in (
        ("--from", args.from_state), ("--to", args.to_state),
        ("--reason", args.reason)) if value is None]
    if missing:
        parser.error(
            "{0} are required for --dry-run/execute (use --inspect for a "
            "read-only observation)".format(", ".join(missing)))

    if args.dry_run:
        # Same operation-id pre-check as the execute path: a preview must
        # never carry a suffix the contract would refuse on execution.
        if args.operation_id is not None:
            try:
                require_operation_id("operation_id", args.operation_id)
            except ValueError as exc:
                _emit({"mode": "result", "result": {
                    "operation_id": None, "code": "schema_violation",
                    "detail": "malformed operation id refused (pass "
                              "--operation-id as 'op-' + 32 hex, or omit "
                              "it to mint one): {0}".format(exc),
                }}, args.json)
                return ExitCode.VALIDATION
        operation_id = args.operation_id or new_operation_id()
        payload = _dry_run(
            target=target, task_id=args.task, from_state=args.from_state,
            to_state=args.to_state, reason=args.reason, refs=refs,
            operation_id=operation_id, schema_version=args.schema_version)
        _emit({"mode": "dry-run", **payload}, args.json)
        return ExitCode.OK if payload["would_execute"] \
            else _disposition_exit_code(payload["refusal"]["code"])

    result = execute_update(
        target=target, task_id=args.task, from_state=args.from_state,
        to_state=args.to_state, reason=args.reason, evidence_refs=refs,
        operation_id=args.operation_id,
        expected_revision=args.expected_revision,
        schema_version=args.schema_version, ledger=ledger)
    replayed = (result.detail or "").startswith("replay of operation")
    _emit({"mode": "result", "result": {
        "operation_id": result.operation_id,
        "code": result.code,
        "new_revision": result.new_revision,
        "observed_revision": result.observed_revision,
        "execution": result.execution,
        "detail": result.detail,
    }}, args.json)
    if result.code == RESULT_OK:
        return ExitCode.REPLAY if replayed else ExitCode.OK
    return _disposition_exit_code(result.code)


def main(argv=None) -> int:
    """CLI handler — also the dotted-path assembly point for a composition
    root (``task_row_update.main``).  Self-contained: ``python
    task_row_update.py ...`` runs the same code path."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    return _execute(args, parser)


def cmd_task_row_update(args) -> int:
    """Engine dispatch face (batch-2.0 integration wiring, FEAT-055).

    Consumes the engine's already-parsed Namespace — the same attribute
    surface ``main`` produces after ``parse_args`` — and runs the identical
    executor; there is no Namespace→argv→main re-parse (FEAT-047 P2-1
    caliber).
    """
    return _execute(args, _build_parser())


# ``ExitCode.REPLAY`` is declared with the structured-code table above.


if __name__ == "__main__":  # pragma: no cover - direct invocation seam
    sys.exit(main())
