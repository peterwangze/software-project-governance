"""FEAT-061 — decision-log storage separation, first table (0.88.0 阶段 C1 · P1).

Six-layer Repository boundary (DEC-237 / version-plan 0.88.0 C1 — 防止
over-engineering 的逻辑分层; code volume stays small, the DEPENDENCY
direction is what is pinned):

    Layer 1  DecisionRepository   — THIS MODULE (read adapter: stable-ID
                                    query/enum + one consistent snapshot
                                    identity ``read_snapshot()``)
    Layer 2  Decision 写入服务     — governance_store.decision_append
                                    (validation/idempotency/CAS/ops resume;
                                    routes between backends through the
                                    authority state below)
    Layer 3  存储适配器            — THIS MODULE (md/json codecs, physical
                                    read/write, conditional commit)
    Layer 4  Projector            — decision_migration (authoritative
                                    snapshot → md one-way regeneration)
    Layer 5  Migration Controller — decision_migration (freeze/manifest/
                                    activate/rollback orchestration)
    Layer 6  独立校验工具          — decision_migration_verify (migration/
                                    recovery proof — MUST NOT be used to
                                    prove the new Repository correct; it
                                    mirrors the PRE-cutover md parser)

Requirement sources (consumed, never re-stated):

  * DEC-237 (decision-log, machine op-b13202de) — arch 复核 10 条 C1-ARCH
    补丁条款 + 10 用例最低崩溃并发验收集 + 独立性三规则.
  * version-plan-0.88.0 §1 (假绿对冲/独立性三条) + §2 C1 七步路径.
  * FEAT-060 (write_guard_state.py) — the ops-recoverable transaction
    pattern (journal → apply → finalize, resume by judging the WORLD, not
    the log) reused here for every migration linearization.

What THIS module owns (C1-ARCH-01/02 + ③④⑤ codec face):

  * The persisted authority state machine
    (``MD_ACTIVE → CUTOVER_FROZEN → JSON_ACTIVE → ROLLBACK_FROZEN →
    (rollback) MD_ACTIVE``) over ``.governance/.decision-store-state.json``
    — the SINGLE persisted authority marker (backend / epoch / generation /
    manifest_digest / migration_id / owner_token).  A MISSING state file is
    the initial world: ``MD_ACTIVE`` epoch 0 — zero footprint for a host
    that never migrates (FEAT-060 artifact precedent).
  * Epoch fencing: every mutating path validates ``expected_epoch`` against
    the authority marker before it acts; stale-epoch callers are refused,
    never auto-migrated (C1-ARCH-01: 所有追加/resume/repair/取消恢复路径
    epoch fencing; 提交判定不明确时禁自动回滚或继续写入 — an unknown or
    malformed marker refuses fail-closed with ``manual_intervention``).
  * Storage codecs: the md document model (every candidate line classified
    — record / table header / separator / non-table content / UNRESOLVED;
    unresolved lines are reported, never silently absorbed — C1-ARCH-05)
    and the JSON store format (``decision-store.json`` v1: verbatim cells
    + row_raw for byte-faithful projection/rollback; duplicate IDs refused
    before aggregation; unknown top-level keys refused — no lossy
    normalization).
  * The read adapter ``read_snapshot()``: one consistent snapshot identity
    over whichever backend the authority marker names (records + backend +
    epoch + generation + schema_version + content_digest).
  * The md projection encode used by the Layer-4 projector and by the
    post-commit projection attempt of the JSON write path, plus the
    persisted projection checkpoint (C1-ARCH-06: 权威提交结果与投影结果
    分开持久表达).

Lock order discipline (extends the governance_store order; every path in
the FEAT-061 family acquires in exactly this order, so nesting cannot
deadlock):

    decision-store.json → decision-log.md → .decision-store-state.json
    → governance-store-ops.json

Private-import justification (write_guard_state precedent): ``_TargetLock``
/ ``_atomic_write_bytes`` / ``_split_row`` / ``_render_row`` /
``_line_ending_of`` / ``_hot_id_numbers`` are reused from
``governance_store`` — there must be ONE cross-process lock, ONE atomic
write, and ONE md row splitter, not second hand-rolled copies.  The import
is safe in both directions: governance_store imports THIS module only
lazily (inside ``decision_append``), never at module level.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path

# Reused wholesale (see module docstring — single lock/atomic-write/parser
# source discipline; the FEAT-060 private-import precedent).
from governance_store import (
    StoreError,
    _TargetLock,
    _atomic_write_bytes,
    _hot_id_numbers,
    _line_ending_of,
    _render_row,
    _split_row,
)

__all__ = [
    "AUTHORITY_STATE_FILE",
    "JSON_STORE_FILE",
    "LEGAL_TRANSITIONS",
    "MIGRATION_ROOT_NAME",
    "MD_FILE_NAME",
    "PROJECTION_CHECKPOINT_FILE",
    "STATE_CUTOVER_FROZEN",
    "STATE_JSON_ACTIVE",
    "STATE_MD_ACTIVE",
    "STATE_ROLLBACK_FROZEN",
    "STORE_FORMAT",
    "STORE_SCHEMA_VERSION",
    "build_store_from_document",
    "classify_md_document",
    "initial_authority",
    "load_authority",
    "load_json_store",
    "load_projection_checkpoint",
    "next_decision_id",
    "read_snapshot",
    "render_markdown",
    "render_record_row",
    "write_authority_transition",
    "write_projection_checkpoint",
]

# ── constants ────────────────────────────────────────────────────────────────

MD_FILE_NAME = "decision-log.md"
JSON_STORE_FILE = "decision-store.json"
AUTHORITY_STATE_FILE = ".decision-store-state.json"
MIGRATION_ROOT_NAME = ".decision-migration"
PROJECTION_CHECKPOINT_FILE = "projection-checkpoint.json"

STORE_FORMAT = "decision-store"
STORE_SCHEMA_VERSION = 1

DEC_PREFIX = "DEC-"

STATE_MD_ACTIVE = "MD_ACTIVE"
STATE_CUTOVER_FROZEN = "CUTOVER_FROZEN"
STATE_JSON_ACTIVE = "JSON_ACTIVE"
STATE_ROLLBACK_FROZEN = "ROLLBACK_FROZEN"

#: C1-ARCH-01 — the complete legal transition table of the persisted state
#: machine.  Any other transition (including skipping states, re-entering
#: the same state, or moving backwards outside this table) is refused as
#: ``illegal_transition`` — the state file is the only place a backend
#: switch becomes real, so the table is deliberately minimal.
LEGAL_TRANSITIONS = frozenset({
    (STATE_MD_ACTIVE, STATE_CUTOVER_FROZEN),
    (STATE_CUTOVER_FROZEN, STATE_JSON_ACTIVE),
    (STATE_CUTOVER_FROZEN, STATE_MD_ACTIVE),          # freeze abort
    (STATE_JSON_ACTIVE, STATE_ROLLBACK_FROZEN),
    (STATE_ROLLBACK_FROZEN, STATE_MD_ACTIVE),         # rollback completes
    (STATE_ROLLBACK_FROZEN, STATE_JSON_ACTIVE),       # rollback abort
})

#: Backend each state serves reads/writes from (the authority marker's
#: ``backend`` field must always equal this mapping — a mismatch is a
#: malformed marker).
STATE_BACKENDS = {
    STATE_MD_ACTIVE: "md",
    STATE_CUTOVER_FROZEN: "md",
    STATE_JSON_ACTIVE: "json",
    STATE_ROLLBACK_FROZEN: "json",
}

#: States in which appends are structurally rejected (C1-ARCH-02: 冻结完成
#: = 新写入被拒绝 — the frozen states ARE the write-rejection mechanism;
#: the write service refuses on these before touching any file).
FROZEN_STATES = frozenset({STATE_CUTOVER_FROZEN, STATE_ROLLBACK_FROZEN})

#: The JSON store's top-level keys (v1).  Unknown keys are REFUSED, never
#: guessed (SchemaVersionWindow discipline; C1-ARCH-05 有损规范化阻断).
#: ``duplicate_acceptances`` is optional and only legal when it records an
#: explicit per-id acceptance for every duplicated id (the real hot file
#: carries legitimate 勘正 pairs like DEC-194 + DEC-194〔勘〕 — they are
#: carried verbatim, NEVER aggregated silently).
_STORE_TOP_KEYS = frozenset({
    "format", "schema_version", "records", "items",
    "duplicate_acceptances",
})

_RECORD_KEYS = frozenset({
    "id", "shape", "cells", "row_raw", "source_line", "provenance",
})

#: Line-classification buckets of the md document model (C1-ARCH-05: every
#: candidate line has a source position and a parse destination).
CLASS_RECORD = "record"
CLASS_TABLE_HEADER = "table_header"
CLASS_TABLE_SEPARATOR = "table_separator"
CLASS_CONTENT = "content"
CLASS_UNRESOLVED = "unresolved"

_SHAPE_LIVE5 = "live5"        # 编号|日期|决策人|决策内容|依据 (hot convention)
_SHAPE_LEGACY11 = "legacy11"  # 编号|日期|主题|背景|决策内容|备选方案|选择原因
#                              # |影响范围|决策人|关联任务|后续动作 (legacy batch)
_SHAPE_VARIANT = "variant"    # DEC-anchored but neither known shape —
#                              # migration proceeds ONLY with an explicit
#                              # per-ID acceptance (cells kept verbatim)

_LIVE5_COLUMNS = 5
_LEGACY11_COLUMNS = 11

#: Record anchor — the ENGINE's row-anchored semantics
#: (``^\s*\|?\s*DEC-(\d+)\b`` caliber): the first cell must START with the
#: canonical id, a trailing annotation (the real hot file carries 勘正
#: markers like ``DEC-194 〔勘〕``) keeps the row a record with the
#: canonical id; ``row_raw`` and ``cells`` stay verbatim.
_DEC_ANCHOR_RE = re.compile(r"^(DEC-\d+)\b")


def _fail(payload):
    raise StoreError(payload)


def _now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── authority state machine (C1-ARCH-01) ─────────────────────────────────────


def _authority_path(governance_dir: Path) -> Path:
    return Path(governance_dir) / AUTHORITY_STATE_FILE


def initial_authority() -> dict:
    """The world when the marker file is absent: md is authoritative,
    epoch 0, generation 0, no migration in flight."""
    return {
        "present": False,
        "state": STATE_MD_ACTIVE,
        "backend": "md",
        "epoch": 0,
        "generation": 0,
        "manifest_digest": None,
        "migration_id": None,
        "owner_token": None,
        "content_digest": None,
        "frozen": None,
        "history": [],
    }


#: The authority marker's known top-level keys (REVIEW-FEAT-061-CODE-R0
#: P2 whitelist): unknown keys mean a malformed/tampered marker — refused
#: fail-closed, never carried (the marker is the single authority source;
#: an unvalidated extra key would silently redefine authority semantics).
_AUTHORITY_TOP_KEYS = frozenset({
    "schema_version", "state", "backend", "epoch", "generation",
    "manifest_digest", "migration_id", "owner_token", "content_digest",
    "frozen", "updated_at", "history",
})


def _validate_authority_document(doc, path: Path) -> dict:
    """Fail-closed marker validation — an unknown state NEVER passes
    (C1-ARCH-01; crash/concurrency case ⑩'s "unknown states don't pass")."""
    if not isinstance(doc, dict):
        _fail({
            "code": "manual_intervention",
            "detail": f"{path}: authority marker must be a JSON object — "
                      f"refusing fail-closed (unknown authority state is "
                      f"never guessed)",
        })
    unknown_keys = set(doc) - _AUTHORITY_TOP_KEYS
    if unknown_keys:
        _fail({
            "code": "manual_intervention",
            "detail": f"{path}: unknown authority marker keys "
                      f"{sorted(unknown_keys)} — refusing fail-closed "
                      f"(the marker is the single authority source; "
                      f"unknown keys are never carried)",
        })
    state = doc.get("state")
    if state not in STATE_BACKENDS:
        _fail({
            "code": "manual_intervention",
            "detail": f"{path}: authority state {state!r} is unknown "
                      f"(closed set: {sorted(STATE_BACKENDS)}) — refusing "
                      f"fail-closed; repair the marker manually",
        })
    epoch = doc.get("epoch")
    if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
        _fail({
            "code": "manual_intervention",
            "detail": f"{path}: authority epoch must be an int >= 0",
        })
    generation = doc.get("generation")
    if isinstance(generation, bool) or not isinstance(generation, int) \
            or generation < 0:
        _fail({
            "code": "manual_intervention",
            "detail": f"{path}: authority generation must be an int >= 0",
        })
    backend = doc.get("backend")
    if backend != STATE_BACKENDS[state]:
        _fail({
            "code": "manual_intervention",
            "detail": f"{path}: backend {backend!r} does not match state "
                      f"{state!r} (expected {STATE_BACKENDS[state]!r})",
        })
    if not isinstance(doc.get("history"), list):
        _fail({
            "code": "manual_intervention",
            "detail": f"{path}: authority history must be a list",
        })
    return doc


def load_authority(governance_dir, *, expected_epoch=None) -> dict:
    """Load the persisted authority marker (absent = initial md world).

    ``expected_epoch`` implements epoch fencing: a caller working from a
    stale snapshot is refused ``epoch_conflict`` with the observed epoch,
    never silently migrated (C1-ARCH-01).
    """
    path = _authority_path(governance_dir)
    if not path.is_file():
        authority = initial_authority()
    else:
        raw = path.read_bytes()
        try:
            doc = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            _fail({
                "code": "manual_intervention",
                "detail": f"{path} is not valid UTF-8 JSON ({exc}) — "
                          f"refusing fail-closed (corrupt authority marker)",
            })
        authority = dict(_validate_authority_document(doc, path))
        authority["present"] = True
    if expected_epoch is not None:
        if not isinstance(expected_epoch, int) or isinstance(expected_epoch,
                                                             bool):
            _fail({
                "code": "schema_violation",
                "detail": "expected_epoch must be an int",
            })
        if authority["epoch"] != expected_epoch:
            _fail({
                "code": "revision_conflict",
                "detail": f"authority epoch moved: expected "
                          f"{expected_epoch}, observed {authority['epoch']} "
                          f"(state {authority['state']}) — re-read the "
                          f"authority marker and re-judge",
                "observed_epoch": authority["epoch"],
            })
    return authority


def write_authority_transition(governance_dir, *, from_state, to_state,
                               expected_epoch, mutate=None,
                               owner_token=None, timeout_seconds=10.0):
    """The single linearization point of every authority change.

    Validates the transition against :data:`LEGAL_TRANSITIONS`, fences on
    ``expected_epoch`` (CAS over the state file under its own lock), and
    applies ``mutate(doc) -> doc`` for the caller's payload fields (freeze
    record, migration id, digest…).  The atomic replace of the marker file
    IS the moment the backend switch becomes real (C1-ARCH-01 唯一切换
    线性化点).

    Lock order: callers that already hold the md or json target lock keep
    holding it — the state-file lock is acquired INSIDE those (documented
    global order in the module docstring).
    """
    governance_dir = Path(governance_dir)
    if (from_state, to_state) not in LEGAL_TRANSITIONS:
        _fail({
            "code": "illegal_transition",
            "detail": f"authority transition {from_state} → {to_state} is "
                      f"not in the legal transition table "
                      f"({sorted(LEGAL_TRANSITIONS)})",
        })
    path = _authority_path(governance_dir)
    with _TargetLock(path, timeout_seconds):
        current = load_authority(governance_dir)
        if current["state"] != from_state:
            _fail({
                "code": "illegal_transition",
                "detail": f"authority state is {current['state']}, expected "
                          f"{from_state} — refusing to transition",
                "observed_state": current["state"],
            })
        if current["epoch"] != expected_epoch:
            _fail({
                "code": "revision_conflict",
                "detail": f"authority epoch moved: expected "
                          f"{expected_epoch}, observed {current['epoch']} "
                          f"— re-read and re-judge",
                "observed_epoch": current["epoch"],
            })
        doc = {
            "schema_version": STORE_SCHEMA_VERSION,
            "state": to_state,
            "backend": STATE_BACKENDS[to_state],
            "epoch": current["epoch"] + 1,
            "generation": current["generation"],
            "manifest_digest": current.get("manifest_digest"),
            "migration_id": current.get("migration_id"),
            "owner_token": owner_token,
            "content_digest": current.get("content_digest"),
            "frozen": current.get("frozen"),
            "updated_at": _now_iso(),
            "history": list(current.get("history", [])) + [{
                "from": from_state,
                "to": to_state,
                "epoch": current["epoch"] + 1,
                "migration_id": current.get("migration_id"),
                "at": _now_iso(),
            }],
        }
        if mutate is not None:
            doc = mutate(doc)
        _validate_authority_document(doc, path)
        _atomic_write_bytes(
            path, (json.dumps(doc, ensure_ascii=False, indent=2)
                   + "\n").encode("utf-8"))
        doc["present"] = True
        return doc


def authority_json_path(governance_dir) -> Path:
    return Path(governance_dir) / JSON_STORE_FILE


def migration_root(governance_dir) -> Path:
    return Path(governance_dir) / MIGRATION_ROOT_NAME


# ── md document model (C1-ARCH-05 codec face) ────────────────────────────────


def _record_shape(cells) -> str:
    if len(cells) == _LIVE5_COLUMNS:
        return _SHAPE_LIVE5
    if len(cells) == _LEGACY11_COLUMNS:
        return _SHAPE_LEGACY11
    return _SHAPE_VARIANT


def _live5_provenance(cells):
    """Extract the machine provenance marker from a live5 依据 cell."""
    basis = cells[4] if len(cells) > 4 else ""
    marker_token = "governance-store decision-append "
    if marker_token in basis:
        tail = basis.split(marker_token, 1)[1]
        op_id = tail.split("；", 1)[0].split(";", 1)[0].split("）", 1)[0] \
            .split(")", 1)[0].strip()
        if op_id:
            return {"op_id": op_id, "marker": marker_token + op_id}
    return None


def classify_md_document(text: str) -> list:
    """Classify EVERY line of the md decision log (C1-ARCH-05).

    Returns a list of items in document order:

    * ``{"kind": "content", "line_no": N, "text": …}`` — headings, blank
      lines, prose (preserved verbatim).
    * ``{"kind": "table_header"|"table_separator", …}`` — the table's own
      scaffolding rows (preserved verbatim).
    * ``{"kind": "record", "line_no": N, "id": "DEC-n", "shape": …,
      "cells": [verbatim split], "row_raw": <exact line>, "provenance":
      …}`` — a DEC-anchored row of a known or variant shape.
    * ``{"kind": "unresolved", "line_no": N, "text": …, "reason": …}`` —
      a line the classifier cannot explain; the MIGRATION treats any
      unresolved line as a blocker (fail-closed), the classification
      itself only reports.
    """
    items = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("|"):
            items.append({"kind": CLASS_CONTENT, "line_no": line_no,
                          "text": line})
            continue
        cells = _split_row(line)
        record_id = None
        if cells:
            match = _DEC_ANCHOR_RE.match(cells[0])
            if match:
                record_id = match.group(1)
        separator = bool(cells) and all(
            set(cell) <= set("-: ") and cell for cell in cells)
        if not cells:
            items.append({"kind": CLASS_UNRESOLVED, "line_no": line_no,
                          "text": line, "reason": "pipe row splits to zero "
                          "cells"})
        elif separator:
            items.append({"kind": CLASS_TABLE_SEPARATOR, "line_no": line_no,
                          "text": line, "cells": cells})
        elif record_id is not None:
            shape = _record_shape(cells)
            items.append({
                "kind": CLASS_RECORD,
                "line_no": line_no,
                "id": record_id,
                "shape": shape,
                "cells": cells,
                "row_raw": line,
                "provenance": (_live5_provenance(cells)
                               if shape == _SHAPE_LIVE5 else None),
            })
        elif all(not cell for cell in cells):
            items.append({"kind": CLASS_UNRESOLVED, "line_no": line_no,
                          "text": line, "reason": "pipe row with only "
                          "empty cells"})
        else:
            first_cell = cells[0]
            if "编号" in first_cell or "id" == first_cell.lower():
                items.append({"kind": CLASS_TABLE_HEADER,
                              "line_no": line_no, "text": line,
                              "cells": cells})
            else:
                items.append({
                    "kind": CLASS_UNRESOLVED, "line_no": line_no,
                    "text": line,
                    "reason": f"pipe row without a {DEC_PREFIX} anchor and "
                              f"without a header signature "
                              f"(first cell {first_cell!r})",
                })
    return items


def build_store_from_document(items, *, variant_acceptances=None,
                              duplicate_acceptances=None) -> dict:
    """Build the JSON store model from classified items (shadow migration).

    ``variant_acceptances`` maps ``DEC-n`` → an explicit acceptance note;
    a variant row WITHOUT an acceptance refuses (C1-ARCH-05: 未解释行阻断;
    acceptance is recorded in the migration manifest, never silent).
    ``duplicate_acceptances`` maps a duplicated ``DEC-n`` → a note; a
    duplicated id WITHOUT an acceptance refuses BEFORE any aggregation
    (C1-ARCH-05 重复 ID 聚合前拒绝) — with one, both rows are carried
    verbatim and the acceptance is persisted IN the store.  Cells and
    ``row_raw`` are kept VERBATIM — the conversion is a pure format
    change, no normalization, no history corrections (C1 step ④).
    """
    variant_acceptances = dict(variant_acceptances or {})
    duplicate_acceptances = dict(duplicate_acceptances or {})
    records = []
    items_out = []
    seen_ids = {}
    duplicates = {}
    for item in items:
        if item["kind"] != CLASS_RECORD:
            if item["kind"] == CLASS_UNRESOLVED:
                _fail({
                    "code": "schema_violation",
                    "detail": f"line {item['line_no']} is unresolved and "
                              f"blocks the migration: {item['reason']} "
                              f"(text: {item['text'][:120]!r}) — resolve or "
                              f"explicitly exclude it in the source first "
                              f"(C1-ARCH-05: unresolved lines block)",
                })
            items_out.append({
                "kind": item["kind"],
                "text": item.get("text", ""),
            })
            continue
        dec_id = item["id"]
        if dec_id in seen_ids:
            acceptance = duplicate_acceptances.get(dec_id)
            if acceptance is None:
                _fail({
                    "code": "cross_record_violation",
                    "detail": f"duplicate record id {dec_id} (lines "
                              f"{seen_ids[dec_id]} and {item['line_no']}) — "
                              f"aggregating duplicates is refused "
                              f"(C1-ARCH-05); pass an explicit "
                              f"--accept-duplicate note to carry BOTH rows "
                              f"verbatim",
                })
            duplicates[dec_id] = acceptance
        seen_ids[dec_id] = item["line_no"]
        shape = item["shape"]
        acceptance = None
        if shape == _SHAPE_VARIANT:
            acceptance = variant_acceptances.get(dec_id)
            if acceptance is None:
                _fail({
                    "code": "schema_violation",
                    "detail": f"line {item['line_no']} is a {dec_id} "
                              f"variant row ({len(item['cells'])} cells) — "
                              f"migration refuses without an explicit "
                              f"per-ID acceptance (cells stay verbatim; "
                              f"acceptances are recorded in the migration "
                              f"manifest)",
                })
        cells = item["cells"]
        record = {
            "id": dec_id,
            "shape": shape,
            "cells": cells,
            "row_raw": item["row_raw"],
            "source_line": item["line_no"],
            "provenance": item.get("provenance"),
        }
        if shape == _SHAPE_LIVE5:
            record["date"] = cells[1]
            record["decider"] = cells[2]
            record["content"] = cells[3]
            record["basis"] = cells[4]
        elif shape == _SHAPE_LEGACY11:
            record["date"] = cells[1]
            record["decider"] = cells[8]
            record["content"] = cells[4]
        else:
            record["date"] = cells[1] if len(cells) > 1 else ""
            acceptance_note = acceptance
            record["variant_acceptance"] = acceptance_note
        records.append(record)
        items_out.append({"kind": CLASS_RECORD, "id": dec_id})
    return {
        "format": STORE_FORMAT,
        "schema_version": STORE_SCHEMA_VERSION,
        "records": records,
        "items": items_out,
        **({"duplicate_acceptances": duplicates} if duplicates else {}),
    }


def render_record_row(record) -> str:
    """Render one record as a md row.  Migration-carried records replay
    ``row_raw`` VERBATIM (byte-faithful projection/rollback); only NEW
    records (no ``row_raw`` — appended under JSON authority) are rendered
    from cells via the one writer row renderer."""
    row_raw = record.get("row_raw")
    if row_raw is not None:
        return row_raw
    return _render_row(record["cells"])


def render_markdown(store, *, trailing_newline=True) -> str:
    """Render the store back to md (the md codec's encode direction).

    Item order is preserved; records replay verbatim; NEW records render
    from cells.  Record resolution is POSITIONAL (the records list pairs
    with the record items in order) — a by-id dict would silently collapse
    duplicate-id 勘正 pairs onto their last occurrence and lose a row in
    the projection (caught by the independent reverse check in the real
    rehearsal; fixed here so the codec never needs that safety net).
    A positional mismatch refuses instead of rendering a wrong record.

    The original line ending is NOT reconstructed here — callers own
    line-ending policy (the projection writer uses the target file's
    existing ending, mirroring the append pipeline).
    """
    records_iter = iter(store["records"])
    lines = []
    for item in store["items"]:
        if item["kind"] == CLASS_RECORD:
            record = next(records_iter, None)
            if record is None or record.get("id") != item.get("id"):
                _fail({
                    "code": "manual_intervention",
                    "detail": f"store items/records correspondence broken "
                              f"at record item {item.get('id')!r} — "
                              f"refusing to render (positional pairing is "
                              f"the duplicate-safe resolution)",
                })
            lines.append(render_record_row(record))
        else:
            lines.append(item["text"])
    text = "\n".join(lines)
    if trailing_newline and text and not text.endswith("\n"):
        text += "\n"
    return text


def load_json_store(path: Path, *, expected_digest=None) -> dict:
    """Load and validate the JSON store fail-closed (C1-ARCH-05 codec).

    Refuses: non-JSON, wrong ``format``, out-of-window ``schema_version``,
    unknown top-level keys, non-record-shaped entries, duplicate ids,
    records without verbatim cells.  ``expected_digest`` pins the bytes.
    """
    path = Path(path)
    raw = path.read_bytes()
    if expected_digest is not None \
            and _sha256_hex(raw) != expected_digest:
        _fail({
            "code": "manual_intervention",
            "detail": f"{path}: store digest mismatch (expected "
                      f"{expected_digest}) — the store changed under a "
                      f"pinned identity; refusing fail-closed",
        })
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        _fail({
            "code": "manual_intervention",
            "detail": f"{path} is not valid UTF-8 JSON ({exc}) — refusing "
                      f"fail-closed",
        })
    if not isinstance(doc, dict):
        _fail({
            "code": "manual_intervention",
            "detail": f"{path}: store root must be a JSON object",
        })
    if doc.get("format") != STORE_FORMAT:
        _fail({
            "code": "schema_version_unsupported",
            "detail": f"{path}: store format {doc.get('format')!r} is not "
                      f"{STORE_FORMAT!r} — refusing (an old tool reading a "
                      f"new format must refuse explicitly, never misread)",
        })
    version = doc.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int) \
            or version != STORE_SCHEMA_VERSION:
        _fail({
            "code": "schema_version_unsupported",
            "detail": f"{path}: store schema_version {version!r} outside "
                      f"supported window [{STORE_SCHEMA_VERSION}, "
                      f"{STORE_SCHEMA_VERSION}] — a newer-than-known store "
                      f"MUST be rejected, never guessed or downgraded",
        })
    unknown = set(doc) - _STORE_TOP_KEYS
    if unknown:
        _fail({
            "code": "schema_violation",
            "detail": f"{path}: unknown store keys {sorted(unknown)} — "
                      f"refusing (unknown fields are never silently "
                      f"carried or dropped)",
        })
    records = doc.get("records")
    if not isinstance(records, list):
        _fail({
            "code": "manual_intervention",
            "detail": f"{path}: store records must be a list",
        })
    items = doc.get("items")
    if not isinstance(items, list):
        _fail({
            "code": "manual_intervention",
            "detail": f"{path}: store items must be a list",
        })
    seen = {}
    duplicate_acceptances = doc.get("duplicate_acceptances") or {}
    if not isinstance(duplicate_acceptances, dict) or any(
            not isinstance(v, str) or not v
            for v in duplicate_acceptances.values()):
        _fail({
            "code": "schema_violation",
            "detail": f"{path}: duplicate_acceptances must map ids to "
                      f"non-empty acceptance notes",
        })
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            _fail({
                "code": "manual_intervention",
                "detail": f"{path}: record[{index}] must be an object",
            })
        unknown_record = set(record) - _RECORD_KEYS - {
            "date", "decider", "content", "basis", "variant_acceptance",
        }
        if unknown_record:
            _fail({
                "code": "schema_violation",
                "detail": f"{path}: record[{index}] has unknown keys "
                          f"{sorted(unknown_record)}",
            })
        dec_id = record.get("id")
        if not isinstance(dec_id, str) or not dec_id.startswith(DEC_PREFIX):
            _fail({
                "code": "schema_violation",
                "detail": f"{path}: record[{index}].id {dec_id!r} is not a "
                          f"{DEC_PREFIX}nnn id",
            })
        if dec_id in seen:
            if dec_id not in duplicate_acceptances:
                _fail({
                    "code": "cross_record_violation",
                    "detail": f"{path}: duplicate record id {dec_id} "
                              f"without a recorded acceptance — refusing "
                              f"(records are keyed by stable id; a "
                              f"duplicate requires an explicit, persisted "
                              f"acceptance note)",
                })
        seen[dec_id] = index
        cells = record.get("cells")
        if not isinstance(cells, list) or not cells \
                or not all(isinstance(cell, str) for cell in cells):
            _fail({
                "code": "manual_intervention",
                "detail": f"{path}: record {dec_id} cells must be a "
                          f"non-empty list of strings",
            })
        if not isinstance(record.get("row_raw"), str):
            _fail({
                "code": "manual_intervention",
                "detail": f"{path}: record {dec_id} is missing verbatim "
                          f"row_raw — projection/rollback fidelity would "
                          f"be lost; refusing",
            })
    return doc


# ── read adapter (Layer 1 — DecisionRepository) ──────────────────────────────


def read_snapshot(governance_dir, *, expected_epoch=None,
                  timeout_seconds=10.0) -> dict:
    """One consistent snapshot of the decision records (Layer 1 face).

    Returns ``{backend, state, epoch, generation, schema_version,
    content_digest, records, record_count, snapshot_digest}``.  The read
    happens under the active backend's target lock, so the identity fields
    and the records come from ONE world.  ``content_digest`` is the sha256
    of the authoritative artifact's bytes; ``snapshot_digest`` binds the
    whole snapshot (identity + canonical record list) for downstream
    freshness comparisons.

    Frozen states read the CURRENT backend artifact (md during
    CUTOVER_FROZEN, json during ROLLBACK_FROZEN) — reads never block on a
    freeze, writes do.
    """
    governance_dir = Path(governance_dir)
    authority = load_authority(governance_dir, expected_epoch=expected_epoch)
    backend = authority["backend"]
    if backend == "md":
        target = governance_dir / MD_FILE_NAME
        with _TargetLock(target, timeout_seconds):
            raw = target.read_bytes()
            authority = load_authority(governance_dir,
                                       expected_epoch=authority["epoch"])
            if authority["backend"] != "md":
                _fail({
                    "code": "revision_conflict",
                    "detail": "authority backend flipped while reading the "
                              "md snapshot — re-read",
                })
            text = raw.decode("utf-8")
            items = classify_md_document(text)
            records = [
                {
                    "id": item["id"],
                    "shape": item["shape"],
                    "cells": item["cells"],
                    "date": (item["cells"][1]
                             if len(item["cells"]) > 1 else ""),
                    "decider": (item["cells"][2]
                                if item["shape"] == _SHAPE_LIVE5
                                and len(item["cells"]) > 2 else
                                (item["cells"][8]
                                 if item["shape"] == _SHAPE_LEGACY11
                                 and len(item["cells"]) > 8 else "")),
                    "content": (item["cells"][3]
                                if item["shape"] == _SHAPE_LIVE5
                                and len(item["cells"]) > 3 else
                                (item["cells"][4]
                                 if item["shape"] == _SHAPE_LEGACY11
                                 and len(item["cells"]) > 4 else "")),
                    "provenance": item.get("provenance"),
                }
                for item in items if item["kind"] == CLASS_RECORD
            ]
            content_digest = _sha256_hex(raw)
    else:
        target = governance_dir / JSON_STORE_FILE
        with _TargetLock(target, timeout_seconds):
            raw = target.read_bytes()
            authority = load_authority(governance_dir,
                                       expected_epoch=authority["epoch"])
            if authority["backend"] != "json":
                _fail({
                    "code": "revision_conflict",
                    "detail": "authority backend flipped while reading the "
                              "json snapshot — re-read",
                })
            store = load_json_store(target)
            records = [
                {
                    "id": record["id"],
                    "shape": record["shape"],
                    "cells": record["cells"],
                    "date": record.get("date", ""),
                    "decider": record.get("decider", ""),
                    "content": record.get("content", ""),
                    "provenance": record.get("provenance"),
                }
                for record in store["records"]
            ]
            content_digest = _sha256_hex(raw)
    snapshot_digest = _sha256_hex(json.dumps(
        {
            "backend": backend,
            "state": authority["state"],
            "epoch": authority["epoch"],
            "generation": authority["generation"],
            "content_digest": content_digest,
            "record_ids": [record["id"] for record in records],
        },
        ensure_ascii=False, sort_keys=True).encode("utf-8"))
    return {
        "backend": backend,
        "state": authority["state"],
        "epoch": authority["epoch"],
        "generation": authority["generation"],
        "schema_version": STORE_SCHEMA_VERSION,
        "content_digest": content_digest,
        "snapshot_digest": snapshot_digest,
        "records": records,
        "record_count": len(records),
    }


def next_decision_id(records, *, archive_numbers=None) -> str:
    """max(hot) + 1 with archive-collision refusal (Check 13 caliber —
    the same ID-continuity rule the md writer enforces, backend-neutral)."""
    numbers = []
    for record in records:
        dec_id = record["id"]
        if dec_id.startswith(DEC_PREFIX) and dec_id[len(DEC_PREFIX):] \
                .isdigit():
            numbers.append(int(dec_id[len(DEC_PREFIX):]))
    next_number = (max(numbers) + 1) if numbers else 1
    candidate = f"{DEC_PREFIX}{next_number}"
    if next_number in set(archive_numbers or ()):
        _fail({
            "code": "cross_record_violation",
            "detail": f"next id {candidate} collides with an archived "
                      f"record — ID continuity would break; resolve the "
                      f"collision manually",
        })
    return candidate


# ── projection checkpoint (C1-ARCH-06 persistence face) ─────────────────────


def _checkpoint_path(governance_dir) -> Path:
    return migration_root(governance_dir) / PROJECTION_CHECKPOINT_FILE


def load_projection_checkpoint(governance_dir) -> dict:
    """Load the persisted projection checkpoint (absent = no projection
    debt recorded).  The checkpoint is the SEPARATE durable expression of
    projection state — the authority commit result never lives here
    (C1-ARCH-06: 权威提交结果与投影结果分开持久表达)."""
    path = _checkpoint_path(governance_dir)
    if not path.is_file():
        return {"present": False, "status": "no_checkpoint"}
    try:
        doc = json.loads(path.read_bytes().decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        _fail({
            "code": "manual_intervention",
            "detail": f"{path} is not valid UTF-8 JSON ({exc}) — projection "
                      f"checkpoint unreadable is a loud failure, never "
                      f"absorbed",
        })
    if not isinstance(doc, dict) or "status" not in doc:
        _fail({
            "code": "manual_intervention",
            "detail": f"{path}: projection checkpoint malformed",
        })
    doc["present"] = True
    return doc


def write_projection_checkpoint(governance_dir, payload: dict) -> dict:
    """Persist the projection checkpoint (atomic; created on demand)."""
    path = _checkpoint_path(governance_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = dict(payload)
    doc.setdefault("updated_at", _now_iso())
    _atomic_write_bytes(
        path, (json.dumps(doc, ensure_ascii=False, indent=2)
               + "\n").encode("utf-8"))
    doc["present"] = True
    return doc


def project_store_to_markdown(governance_dir, *, reason, timeout_seconds=10.0,
                              json_lock_held=False):
    """The md projection attempt of the CURRENT json store (Layer 3 encode
    + checkpoint persistence; the migration-time Layer-4 regeneration with
    fencing lives in decision_migration).

    Under the json lock the store bytes are captured (the fixed snapshot
    identity), rendered to md, and written to ``decision-log.md`` under
    the md lock.  ``json_lock_held=True`` lets the JSON write service call
    this INSIDE its own append critical section (``_TargetLock`` is not
    reentrant — the caller proves ownership by holding the lock); the md
    lock is still acquired here, keeping the documented order
    json → md.  The checkpoint records input digest, rendered digest, and
    outcome — ``fresh`` or ``pending`` with the failure detail.  A late
    projection whose captured snapshot is no longer current refuses
    ``stale_projection`` (crash/concurrency case ⑤) instead of writing an
    overwriting render.
    """
    governance_dir = Path(governance_dir)
    json_target = governance_dir / JSON_STORE_FILE
    md_target = governance_dir / MD_FILE_NAME
    if json_lock_held:
        store_raw = json_target.read_bytes()
    else:
        with _TargetLock(json_target, timeout_seconds):
            store_raw = json_target.read_bytes()
    input_digest = _sha256_hex(store_raw)
    store = load_json_store(json_target)
    rendered = render_markdown(store)
    with _TargetLock(md_target, timeout_seconds):
        current_store_raw = json_target.read_bytes()
        if _sha256_hex(current_store_raw) != input_digest:
            # Crash/concurrency case ⑤ (旧投影任务晚于新投影任务完成):
            # the captured snapshot is no longer the world — refusing to
            # overwrite md with a stale render; the checkpoint records the
            # pending debt and the repair path re-projects.
            _fail({
                "code": "revision_conflict",
                "detail": "stale_projection: the store changed while this "
                          f"projection was in flight (captured "
                          f"{input_digest[:12]}…) — refusing to overwrite "
                          f"the md projection with a stale render; the "
                          f"repair path re-projects from the current store",
            })
        current_md = md_target.read_bytes()
        md_ending = _line_ending_of(current_md)
        body = rendered.replace("\n", md_ending) if md_ending != "\n" \
            else rendered
        if not body.endswith(md_ending):
            body += md_ending
        try:
            _atomic_write_bytes(md_target, body.encode("utf-8"))
        except OSError as exc:
            checkpoint = write_projection_checkpoint(governance_dir, {
                "status": "pending",
                "input_store_digest": input_digest,
                "reason": reason,
                "attempts": 1,
                "last_error": f"md write failed: {exc}",
            })
            return {"status": "pending", "checkpoint": checkpoint,
                    "md_digest": None}
        rendered_digest = _sha256_hex(body.encode("utf-8"))
        checkpoint = write_projection_checkpoint(governance_dir, {
            "status": "fresh",
            "input_store_digest": input_digest,
            "md_digest": rendered_digest,
            "reason": reason,
        })
        return {"status": "fresh", "checkpoint": checkpoint,
                "md_digest": rendered_digest,
                "input_store_digest": input_digest}


def projection_freshness(governance_dir, *, timeout_seconds=10.0) -> dict:
    """The freshness gate (C1-ARCH-06: 投影缺失或过期时发布阻断).

    ``fresh``      — md bytes re-render from the current store exactly.
    ``stale``      — md exists but diverges from the current store render
                     (publish must NOT consume it).
    ``no_store``   — md backend world (gate not applicable → fresh-by-
                     definition for the md world; the cutover ticket wires
                     the publish face).
    ``missing``    — json authority without any md projection artifact.
    ``corrupt``    — store or checkpoint unreadable — loud, never absorbed.
    """
    governance_dir = Path(governance_dir)
    authority = load_authority(governance_dir)
    if authority["backend"] != "json":
        return {"status": "no_store", "backend": authority["backend"],
                "state": authority["state"]}
    json_target = governance_dir / JSON_STORE_FILE
    md_target = governance_dir / MD_FILE_NAME
    if not json_target.is_file():
        return {"status": "corrupt", "detail": "json authority without a "
                "store file"}
    try:
        with _TargetLock(json_target, timeout_seconds):
            store_raw = json_target.read_bytes()
            store = load_json_store(json_target)
            rendered = render_markdown(store)
    except StoreError as exc:
        return {"status": "corrupt", "detail": exc.payload.get("detail")}
    if not md_target.is_file():
        return {"status": "missing", "detail": "json authority without a "
                "md projection"}
    md_raw = md_target.read_bytes()
    md_text = md_raw.decode("utf-8")
    expected = render_markdown(store)
    # Compare content modulo line endings (the projection owns ending
    # policy; the gate judges CONTENT freshness).
    normalized_md = md_text.replace("\r\n", "\n").rstrip("\n")
    normalized_expected = expected.rstrip("\n")
    if normalized_md == normalized_expected:
        return {"status": "fresh", "store_digest": _sha256_hex(store_raw),
                "md_digest": _sha256_hex(md_raw)}
    return {
        "status": "stale",
        "store_digest": _sha256_hex(store_raw),
        "md_digest": _sha256_hex(md_raw),
        "detail": "md projection diverges from the authoritative store — "
                  "publish must not consume stale evidence "
                  "(C1-ARCH-06 freshness gate)",
    }
