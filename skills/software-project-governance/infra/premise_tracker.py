"""FIX-463 — decision-premise invalidator (DEC-368② class, structural close).

A governance decision can rest on an observable premise ("hook bypasses
stay rare", "this defect class does not recur").  Until FIX-463 nothing
measured the premise: a decision kept its ranking-suppression authority
forever, even after the premise measurably collapsed (live case: three
documented ``--no-verify`` hook bypasses — EVD-2145 / EVD-2148③ — eroding
DEC-368②'s "pausing FIX-444/445 is safe" premise).

This module owns the premise lifecycle end to end:

  * DECLARATION — ``decision-append --premise-observable OBS
    --premise-threshold N`` stamps the premise into the decision row's
    machine marker tail (``premise={observable:bypass_count,threshold:2}``).
    The decision-log stays append-only; :func:`parse_decision_premise`
    reads the declaration back out of the row text.
  * COUNTING — ``premise count`` appends replayable events to
    ``.governance/premise-events.jsonl``.  ``--source auto`` recomputes the
    observable from its machine source (bypass_count: evidence-log row scan;
    recurrence_count: pin-ledger provenance rows in checks/version.py);
    ``--source ref`` records a referenced observation (red_ci_hours: manual
    ``gh:run=…,hours=…`` refs — CI has no gh; fail-closed honesty beats a
    half-probe).  Every event carries op-id / source / refs / total.
  * RE-REVIEW — ``premise review`` appends a ``premise_reviewed`` event;
    aggregation only counts events AFTER the latest review (the review is
    the natural counter baseline reset — history is never rewritten).
  * VERDICT — :func:`premise_status` is a pure function
    (declarations x events) -> collapsed set.  A collapsed decision loses
    its ranking-suppression authority: task_priority surfaces it as an
    active-defect item ("premise collapsed — re-review required") and
    check-governance warns until the user re-reviews (the re-review right
    stays with the user — the writer only records the event).

Writer contract (governance_store family): op-id receipts, effect-based
idempotency (same refs+total = ``idempotent_noop``, zero bytes written),
``_TargetLock`` + atomic write, exit 0 ok / 2 refusal / 3 retryable.
The engine wires dispatch only (governance_cost pattern); stdlib-only at
import time.  No ``.governance`` writes outside the events file.

Run:
    python infra/verify_workflow.py premise count --help
"""

from __future__ import annotations

import argparse
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

TASK_ID = "FIX-463"
SCHEMA = "premise-tracker/1"

EVENTS_FILE_NAME = "premise-events.jsonl"
DECISION_LOG_NAME = "decision-log.md"
EVIDENCE_LOG_NAME = "evidence-log.md"
VERSION_PY_REL = "skills/software-project-governance/infra/checks/version.py"

OBSERVABLES = ("bypass_count", "recurrence_count", "red_ci_hours")

#: The declaration tail the decision-append writer stamps inside the row's
#: machine marker: ``…；schema v1；premise={observable:bypass_count,threshold:2}``
PREMISE_TAIL = "premise={{observable:{observable},threshold:{threshold}}}"
PREMISE_TAIL_RE = re.compile(
    r"premise=\{observable:([a-z_]+),threshold:(\d+)\}")

_BYPASS_ROW_RE = re.compile(r"--no-verify")
#: Row context: a bypass-disclosure row is HOOK context (the emergency
#: channel is the commit-msg hook's). Prose mentions without hook context
#: (EVD-928/EVD-1187 class — "不再被迫 --no-verify" normative statements)
#: are not events.
_BYPASS_HOOK_RE = re.compile(r"hook", re.IGNORECASE)
#: Negation window: an occurrence preceded (within 8 chars) by a negation
#: ("不再被迫 --no-verify", "暂态未 --no-verify") is normative prose or an
#: anti-event statement, not an event disclosure (live calibration:
#: evidence-log L1727 "…暂态未 --no-verify…" documents NOT bypassing).
_BYPASS_NEGATED_RE = re.compile(r"(不|无|未|没|避免|禁).{0,8}--no-verify")
#: Enumeration intensifier INSIDE a bypass-disclosure row: "两次拦截" means
#: the row documents TWO events (EVD-2148③: M-7 + M-5b), so the row
#: contributes max(1, parsed count).  EVD-2145 documents one (e254584).
_BYPASS_ENUM_RE = re.compile(r"([一两二三四五六七八九]|\d+)\s*次")
_ENUM_WORDS = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5,
               "六": 6, "七": 7, "八": 8, "九": 9}

_PIN_PROVENANCE_RE = re.compile(
    r"#\s*pins\s+(register|re-anchor)\s+op-[0-9a-f]{32}\b")

_DEC_ROW_RE = re.compile(r"^\|\s*(DEC-\d+)\s*\|")


def new_operation_id() -> str:
    return "op-" + uuid.uuid4().hex


# ── pure read faces ─────────────────────────────────────────────────────────


def parse_decision_premise(row_text: str):
    """Return ``{"observable": …, "threshold": …}`` or None (no declaration).

    The declaration lives in the machine marker tail; the row text is read
    verbatim (decision_repository keeps cells byte-faithful, so scanning the
    whole raw line is the single-source read).
    """
    if not row_text:
        return None
    match = PREMISE_TAIL_RE.search(row_text)
    if not match:
        return None
    observable, threshold = match.group(1), int(match.group(2))
    if observable not in OBSERVABLES or threshold < 1:
        return None
    return {"observable": observable, "threshold": threshold}


def collect_premise_declarations(decision_log_text: str):
    """Scan decision-log rows -> ``{dec_id: {"observable","threshold","line"}}``."""
    declarations = {}
    for lineno, line in enumerate(
            (decision_log_text or "").splitlines(), start=1):
        if not _DEC_ROW_RE.match(line):
            continue
        premise = parse_decision_premise(line)
        if premise is not None:
            dec_id = _DEC_ROW_RE.match(line).group(1)
            premise = dict(premise, line=lineno)
            declarations[dec_id] = premise
    return declarations


def count_hook_bypasses(evidence_log_text: str):
    """Replayable bypass counter over the evidence log (auto source).

    Deterministic rule (calibrated on the live tree 2026-10-24, documented
    for re-audit): a row is a bypass-disclosure row iff it contains
    ``--no-verify`` in HOOK context and the occurrence is not inside a
    negation window ("不再被迫 --no-verify" is normative prose, not an
    event).  Each qualifying row contributes ``max(1, enumerated count)``
    — an explicit ``N 次 / 两次`` intensifier in the SAME row means the row
    documents N events (EVD-2148③: "在 M-7/M-5b 两次拦截" -> 2).

    Known ambiguity, disclosed: a row that re-references an ALREADY
    disclosed bypass (EVD-2146 re-anchors e254584) still counts +1 — the
    auto source is an UPPER bound with a documented ±1 cross-reference
    error.  Live tree: EVD-2145 (1) + EVD-2146 (1, cross-ref) +
    EVD-2148③ (2) = 4 ≥ the three documented events (e254584, M-7, M-5b).
    The error direction is toward EARLIER collapse — a re-review surfacing
    is a bounded, honest cost; a silently rotting premise is the
    unbounded one (DEC-368② class).  Consumers assert against the
    documented EVENT FLOOR (>= 3), never against the raw row count.
    """
    rows = []
    for lineno, line in enumerate(
            (evidence_log_text or "").splitlines(), start=1):
        if not _BYPASS_ROW_RE.search(line):
            continue
        if not _BYPASS_HOOK_RE.search(line):
            continue
        if _BYPASS_NEGATED_RE.search(line):
            continue
        contribution = 1
        for enum_match in _BYPASS_ENUM_RE.finditer(line):
            token = enum_match.group(1)
            parsed = _ENUM_WORDS.get(token)
            if parsed is None:
                try:
                    parsed = int(token)
                except ValueError:
                    parsed = 0
            if parsed > contribution:
                contribution = parsed
        rows.append((lineno, contribution))
    return {"count": sum(c for _l, c in rows), "rows": rows}


def count_pin_recurrences(version_py_text: str):
    """Replayable recurrence counter: machine-written pin-ledger events."""
    lines = (version_py_text or "").splitlines()
    rows = [(lineno, line.strip())
            for lineno, line in enumerate(lines, start=1)
            if _PIN_PROVENANCE_RE.search(line)]
    return {"count": len(rows), "rows": rows}


def load_events(governance_dir):
    """Parse premise-events.jsonl; fail-closed on a malformed line."""
    path = Path(governance_dir) / EVENTS_FILE_NAME
    if not path.is_file():
        return []
    events = []
    for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "{0}:{1}: malformed premise event: {2}".format(
                    EVENTS_FILE_NAME, lineno, exc.msg)) from exc
        if not isinstance(event, dict) or "operation_id" not in event \
                or "type" not in event:
            raise ValueError(
                "{0}:{1}: premise event missing operation_id/type".format(
                    EVENTS_FILE_NAME, lineno))
        events.append(event)
    return events


def premise_status(declarations, events):
    """Pure verdict: which declared premises have collapsed.

    Aggregation per decision: count events of type ``count`` for the
    decision's observable that occur AFTER the latest ``premise_reviewed``
    event for that decision (a review resets the counter baseline — the
    natural append-only semantics; history is never rewritten).  A decision
    with no events stands at total 0.
    """
    detail = {}
    for dec_id, premise in (declarations or {}).items():
        own = [e for e in (events or []) if e.get("decision_id") == dec_id]
        reviews = [e for e in own if e.get("type") == "premise_reviewed"]
        last_review_seq = max(
            (e.get("sequence", 0) for e in reviews), default=0)
        counts = [
            e for e in own
            if e.get("type") == "count"
            and e.get("observable") == premise["observable"]
            and e.get("sequence", 0) > last_review_seq
        ]
        total = counts[-1].get("total", 0) if counts else 0
        # `total` is authoritative (auto sources snapshot the recomputed
        # value); ref sources carry the observed total in the event itself.
        collapsed = total >= premise["threshold"]
        detail[dec_id] = {
            "observable": premise["observable"],
            "threshold": premise["threshold"],
            "total": total,
            "collapsed": collapsed,
            "reviewed": bool(reviews),
            "last_event_refs": counts[-1].get("refs", "") if counts else "",
        }
    return {
        "collapsed": sorted(d for d, x in detail.items() if x["collapsed"]),
        "detail": detail,
    }


# ── governed writer (events append) ─────────────────────────────────────────


def _events_path(governance_dir):
    return Path(governance_dir) / EVENTS_FILE_NAME


def _next_sequence(events):
    return max((e.get("sequence", 0) for e in events), default=0) + 1


def append_event(governance_dir, event, *, timeout_seconds=10.0):
    """Append one event under the governance_store lock + atomic write.

    Effect-based idempotency, two layers: (a) same operation_id already on
    file -> replay receipt, zero bytes; (b) a ``count`` event with the same
    (decision_id, observable, source, refs, total) already on file ->
    ``idempotent_noop`` receipt, zero bytes.  Refusal exit scale matches the
    governance_store family (0 ok / 2 refusal / 3 retryable), surfaced as
    ``(payload, exit_code)``.
    """
    # governance_store private-import precedent (decision_repository L90):
    # ONE cross-process lock, ONE atomic write — no second hand-rolled copy.
    from governance_store import StoreError, _TargetLock, _atomic_write_bytes

    governance_dir = Path(governance_dir)
    path = _events_path(governance_dir)
    now = datetime.now()
    op_id = event.get("operation_id") or new_operation_id()
    receipt = {"schema": SCHEMA, "command": "premise " + str(event.get("type")),
               "task": TASK_ID, "operation_id": op_id}

    def refuse(detail, code="refused"):
        receipt.update({"code": code, "error": True, "detail": detail})
        return receipt, 2

    if event.get("type") not in ("count", "premise_reviewed"):
        return refuse("event type must be 'count' or 'premise_reviewed'")
    if not str(event.get("decision_id") or "").startswith("DEC-"):
        return refuse("decision_id must be a DEC-xxx reference")
    if event["type"] == "count":
        if event.get("observable") not in OBSERVABLES:
            return refuse("observable must be one of {0}".format(
                ", ".join(OBSERVABLES)))
        total = event.get("total")
        if not isinstance(total, int) or isinstance(total, bool) or total < 0:
            return refuse("total must be a non-negative integer")
        if event.get("source") == "ref" and not str(event.get("refs") or "").strip():
            return refuse("source=ref requires --refs (replayable evidence)")

    try:
        with _TargetLock(path, timeout_seconds):
            events = load_events(governance_dir)
            existing_ops = {e.get("operation_id") for e in events}
            if op_id in existing_ops:
                receipt.update({"code": "ok", "error": False,
                                "effect": "replay"})
                return receipt, 0
            if event["type"] == "count":
                duplicate = any(
                    e.get("type") == "count"
                    and e.get("decision_id") == event["decision_id"]
                    and e.get("observable") == event["observable"]
                    and e.get("source") == event["source"]
                    and e.get("refs") == event.get("refs")
                    and e.get("total") == event["total"]
                    for e in events)
                if duplicate:
                    receipt.update({"code": "ok", "error": False,
                                    "effect": "idempotent_noop",
                                    "detail": "identical count already on file"})
                    return receipt, 0
            record = dict(event)
            record["operation_id"] = op_id
            record["sequence"] = _next_sequence(events)
            record.setdefault("observed_at", now.isoformat(timespec="seconds"))
            line = json.dumps(record, ensure_ascii=False) + "\n"
            original = path.read_text(encoding="utf-8") if path.is_file() else ""
            _atomic_write_bytes(path, (original + line).encode("utf-8"))
            # Post-write check: the event parses back.
            reloaded = load_events(governance_dir)
            if record not in reloaded:
                _atomic_write_bytes(path, original.encode("utf-8"))
                return refuse("post-write verification failed; rolled back")
            receipt.update({"code": "ok", "error": False, "effect": "written",
                            "sequence": record["sequence"]})
            return receipt, 0
    except StoreError as exc:
        receipt.update({"code": "retryable", "error": True,
                        "detail": "lock/IO: {0}".format(exc)})
        return receipt, 3


# ── CLI (engine wires dispatch only) ────────────────────────────────────────


def _repo_root_from(governance_dir):
    return Path(governance_dir).resolve().parent


def _auto_total(governance_dir, observable):
    """Recompute an auto observable; returns (total, refs) or (None, error)."""
    root = _repo_root_from(governance_dir)
    if observable == "bypass_count":
        evidence = root / ".governance" / EVIDENCE_LOG_NAME
        if not evidence.is_file():
            return None, "evidence-log.md not found under the governance dir"
        result = count_hook_bypasses(evidence.read_text(encoding="utf-8"))
        rows = "; ".join("L{0}(+{1})".format(l, c) for l, c in result["rows"])
        return result["count"], rows or "no rows"
    if observable == "recurrence_count":
        version_py = root / VERSION_PY_REL
        if not version_py.is_file():
            return None, "checks/version.py not found under the project root"
        result = count_pin_recurrences(version_py.read_text(encoding="utf-8"))
        return result["count"], "{0} provenance rows".format(result["count"])
    return None, ("observable {0} has no auto source — use --source ref "
                  "with --refs (CI has no gh probe; 0.100 candidate)".format(
                      observable))


def add_count_arguments(parser):
    parser.add_argument("--decision", required=True,
                        help="the DEC-xxx id whose premise is being counted")
    parser.add_argument("--observable", required=True, choices=OBSERVABLES)
    parser.add_argument("--source", default="auto", choices=("auto", "ref"))
    parser.add_argument("--refs", default="",
                        help="replayable evidence refs (required for --source ref)")
    parser.add_argument("--total", type=int, default=None,
                        help="observed total (ref source; auto recomputes)")
    parser.add_argument("--dry-run", action="store_true")


def add_review_arguments(parser):
    parser.add_argument("--decision", required=True)
    parser.add_argument("--note", default="")
    parser.add_argument("--dry-run", action="store_true")


def add_status_arguments(parser):
    parser.add_argument("--decision", default=None,
                        help="restrict the status output to one DEC id")


def add_arguments(premise_parser):
    sub = premise_parser.add_subparsers(dest="premise_command",
                                        metavar="{count,review,status}")
    cnt = sub.add_parser(
        "count", help="append a replayable premise count event "
                      "(--source auto recomputes; effect-idempotent; --dry-run)")
    add_count_arguments(cnt)
    rev = sub.add_parser(
        "review", help="record the user's premise re-review "
                       "(resets the counter baseline; the right stays with the user)")
    add_review_arguments(rev)
    sta = sub.add_parser(
        "status", help="read-only verdict: which declared premises have collapsed")
    add_status_arguments(sta)


def cmd_premise(args):
    governance_dir = _resolve_governance_dir(args)
    command = getattr(args, "premise_command", None)
    if command == "count":
        return _cli_count(args, governance_dir)
    if command == "review":
        return _cli_review(args, governance_dir)
    if command == "status":
        return _cli_status(args, governance_dir)
    receipt = {"schema": SCHEMA, "command": "premise", "task": TASK_ID,
               "code": "refused", "error": True,
               "detail": "missing premise subcommand (count|review|status)"}
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 2


def _resolve_governance_dir(args):
    explicit = getattr(args, "project_root", None)
    root = Path(explicit).resolve() if explicit else Path.cwd()
    return root / ".governance"


def _cli_count(args, governance_dir):
    if args.source == "auto":
        total, refs = _auto_total(governance_dir, args.observable)
        if total is None:
            print(json.dumps({"schema": SCHEMA, "command": "premise count",
                              "task": TASK_ID, "code": "refused", "error": True,
                              "detail": refs}, ensure_ascii=False, indent=2))
            return 2
    else:
        total, refs = args.total, args.refs
    event = {"type": "count", "decision_id": args.decision,
             "observable": args.observable, "source": args.source,
             "refs": refs, "total": total}
    if getattr(args, "dry_run", False):
        print(json.dumps({"schema": SCHEMA, "command": "premise count",
                          "task": TASK_ID, "code": "ok", "error": False,
                          "effect": "dry_run", "event": event},
                         ensure_ascii=False, indent=2))
        return 0
    receipt, code = append_event(governance_dir, event)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return code


def _cli_review(args, governance_dir):
    event = {"type": "premise_reviewed", "decision_id": args.decision,
             "note": args.note}
    if getattr(args, "dry_run", False):
        print(json.dumps({"schema": SCHEMA, "command": "premise review",
                          "task": TASK_ID, "code": "ok", "error": False,
                          "effect": "dry_run", "event": event},
                         ensure_ascii=False, indent=2))
        return 0
    receipt, code = append_event(governance_dir, event)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return code


def _cli_status(args, governance_dir):
    decision_log = Path(governance_dir) / DECISION_LOG_NAME
    declarations = collect_premise_declarations(
        decision_log.read_text(encoding="utf-8")
        if decision_log.is_file() else "")
    try:
        events = load_events(governance_dir)
    except ValueError as exc:
        print(json.dumps({"schema": SCHEMA, "command": "premise status",
                          "task": TASK_ID, "code": "refused", "error": True,
                          "detail": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    status = premise_status(declarations, events)
    if getattr(args, "decision", None):
        status = {"collapsed": [d for d in status["collapsed"]
                                if d == args.decision],
                  "detail": {d: x for d, x in status["detail"].items()
                             if d == args.decision}}
    print(json.dumps({"schema": SCHEMA, "command": "premise status",
                      "task": TASK_ID, "code": "ok", "error": False,
                      **status}, ensure_ascii=False, indent=2))
    return 0
