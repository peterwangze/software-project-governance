"""Governance cost observability — FEAT-032 (AUDIT-154 slice A-1, v0.84.0).

Turns DSH session traces (``session.v3.jsonl.zstd``) into machine-readable
governance cost metrics, promoted from the verified research scripts
(``project/research/dsh-trace-analysis/`` — EVD-1071) into this formal
module; the research scripts remain as thin deprecated pointers to HERE.

Metrics (all raw event-timestamp deltas — no estimation, no smoothing;
calibration per AUDIT-154 report §4):

* TTFA per turn — first ``user/message`` → first ``ask_user_question``
  ``tool/call`` (null when the turn never asks).
* Time-to-substantive-work — first ``ask_user_question`` → first tool
  call whose name is NOT in ``GOVERNANCE_TOOL_NAMES`` (endpoint
  ``first_work_tool``), falling back to the turn end (endpoint
  ``turn_end``).
* Governance token breakdown — ``usage{inputTokens, cacheReadTokens,
  outputTokens}`` summed per turn / session / scan. These are CUMULATIVE
  request volumes (audit §4.1), never context residency.
* Tool duration distribution per name (count / total / max / avg).
* LLM time vs tool time shares — ``llm_ms`` = sum over steps of (first
  ``assistant/message`` time − ``step/start`` time); ``tool_ms`` = sum of
  paired ``tool/call``→``tool/result`` deltas; the remainder is reported
  as a labeled arithmetic residual (``other_residual_ms``), never
  attributed to a single cause (audit §4.3/§4.4). ``ask_user_question``
  call→result suspension (user wait) is reported separately.

Event-model facts the parser relies on (all verified against real traces,
EVD-1071): ``user/message`` carries NO ``turn`` field and is attributed to
the current turn by event order (audit report §2); a ``user/message``
before the first ``turn/start`` is counted as
``user_messages_before_first_turn`` and attached to no turn; tool calls
pair through ``tool/result.data.message.source.callId``.

Boundary (audit §6 确定性工具原则): this module is read-only, stdlib-only
at import time, and lazily imports ``zstandard`` — a missing zstandard is
a fail-closed error (exit 1), never a silent empty report. No
``verify_workflow`` import (ArchGuard R2); the engine only wires dispatch
(same pattern as ``archguard_ratchet``).

Usage:
    python skills/software-project-governance/infra/verify_workflow.py \
        governance-cost-report --sessions-root <dir> --format json
    --sessions-root defaults to the ``DSH_SESSIONS_ROOT`` environment
    variable; when neither is present the command fails closed (exit 2)
    with an explicit hint — user paths are never hardcoded.
"""

from __future__ import annotations

import argparse
import datetime
import io
import json
import os
import sys
import time
from pathlib import Path

REPORT_SCHEMA = "governance-cost-report/1"
TASK_ID = "FEAT-032"

#: The interaction gate the whole workflow is measured against.
ASK_TOOL = "ask_user_question"

#: Name-based governance-tool classification (declared, reviewable, and
#: deliberately minimal): ask_user_question is the user-interaction gate,
#: skill is the skill-injection loader at the head of the bootstrap chain
#: (audit report §3.3). Generic tools (read/pwsh/...) cannot be classified
#: by name and therefore count as work-tool candidates — disclosed in
#: ``CALIBRATION`` rather than guessed at.
GOVERNANCE_TOOL_NAMES = frozenset({"ask_user_question", "skill"})

#: Head length of the first user message kept for governance-turn detection
#: (same caliber as the EVD-1071 research scripts).
_USER_TEXT_HEAD = 800

_SESSION_FILENAME = "session.v3.jsonl.zstd"

#: Lazy zstandard holder. ``_MISSING`` = not yet imported; ``None`` = the
#: import failed (fail-closed on next use). Never import at module top:
#: the engine's cold-import face (ArchGuard R6) must stay stdlib-only.
_MISSING = object()
_ZSTD_MODULE = _MISSING
_ZSTD_IMPORT_ERROR = None


class GovernanceCostError(Exception):
    """Fail-closed error for the governance-cost-report command."""


def _get_zstd():
    """Lazily import zstandard; raise a clear error when unavailable."""
    global _ZSTD_MODULE, _ZSTD_IMPORT_ERROR
    if _ZSTD_MODULE is _MISSING:
        try:
            import zstandard as _zstd  # noqa: PLC0415 (deliberate lazy import)
        except ImportError as exc:
            _ZSTD_MODULE = None
            _ZSTD_IMPORT_ERROR = exc
        else:
            _ZSTD_MODULE = _zstd
    if _ZSTD_MODULE is None:
        detail = f" (import error: {_ZSTD_IMPORT_ERROR})" if _ZSTD_IMPORT_ERROR else ""
        raise GovernanceCostError(
            "zstandard 未安装：governance-cost-report 需要 zstandard 解压 DSH "
            "会话轨迹（session.v3.jsonl.zstd）。fail-closed——不静默降级。"
            f"请先安装：pip install zstandard{detail}")
    return _ZSTD_MODULE


def _decompress_bytes(blob):
    """Decompress one zstd session blob to raw bytes (fast scanner input)."""
    zstd = _get_zstd()
    reader = zstd.ZstdDecompressor().stream_reader(io.BytesIO(blob))
    return reader.read()


def _parse_jsonl_lines(text):
    """Parse JSONL text tolerantly; returns (events, corrupt_line_count)."""
    events = []
    corrupt = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except Exception:
            corrupt += 1
    return events, corrupt


# ── byte-level fast scanner (performance face: <5s at ~300 files) ───────────
#
# ~95% of decompressed trace bytes ride in three event types whose full
# JSON payload we do NOT need (assistant/message: only envelope time + turn +
# usage; tool/result: only envelope time + source callId; tool/call: only
# envelope time + turn + callId + name). json.loads on all lines costs ~10s
# at the 0.83.0 corpus size; the fast paths below extract the needed fields
# from the raw bytes and fall back to a full json.loads of the line on ANY
# doubt — so the parsed event stream (and every metric) is identical to the
# full-parse path by construction. Envelope fields (type/time/turn/callId/
# name) always precede message content in the harness serialization, so the
# FIRST marker occurrence is the envelope's own; content-embedded usage
# lookalikes are rejected by arithmetic validation (totalTokens must equal
# in+out+cacheRead) and the scan continues to the next occurrence.
# corrupt_lines_skipped caliber: non-blank lines that cannot be interpreted
# as events — no envelope type marker AND unparseable JSON (or a needed-type
# line failing both fast path and full parse). Lines carrying a valid
# envelope marker of an unneeded type (request/header, agent/inbox/spliced,
# ...) are skipped without parsing; truncation inside them is not counted
# because no metric depends on them.

_FAST_ASSISTANT = b"assistant/message"
_FAST_TOOL_RESULT = b"tool/result"
_FAST_TOOL_CALL = b"tool/call"

#: Needed types that take the full-parse route (their full payload IS the
#: metric input): session header/title, turn and step envelopes, user text.
_FULL_PARSE_TYPES = frozenset((
    b"session", b"session/title", b"turn/start", b"turn/end",
    b"step/start", b"step/end", b"user/message",
))
_TYPE_MARKER = b'"type":"'
_TIME_MARKER = b'"time":'
_TURN_MARKER = b'"data":{"turn":'
_USAGE_MARKER = b'"usage":{'
_CALLID_MARKER = b'"callId":"'
_NAME_MARKER = b'"name":"'
_USAGE_KEYS = ("inputTokens", "outputTokens", "cacheReadTokens", "totalTokens")


def _line_type(line):
    """Return the envelope type bytes of a JSONL line (None if absent)."""
    i = line.find(_TYPE_MARKER)
    if i < 0:
        return None
    start = i + len(_TYPE_MARKER)
    j = line.find(b'"', start)
    if j < 0:
        return None
    return line[start:j]


def _int_after(line, marker):
    """Digits immediately following ``marker`` as int (None if absent)."""
    i = line.find(marker)
    if i < 0:
        return None
    start = i + len(marker)
    j = start
    while j < len(line) and 0x30 <= line[j] <= 0x39:
        j += 1
    if j == start:
        return None
    return int(line[start:j])


def _extract_usage(line, from_pos=0):
    """Extract a plausible ``usage`` object at/after ``from_pos``.

    A candidate object is trusted only when its arithmetic closes
    (totalTokens == input+output+cacheRead, audit §4.1 shape), so
    content-embedded lookalikes fall through to the next occurrence or the
    full-parse fallback. Returns (usage_dict, next_search_pos) or (None, -1).
    """
    i = line.find(_USAGE_MARKER, from_pos)
    if i < 0:
        return None, -1
    depth = 0
    j = i + len(_USAGE_MARKER) - 1  # at the opening brace
    while j < len(line):
        b_ = line[j]
        if b_ == 0x7B:  # '{'
            depth += 1
        elif b_ == 0x7D:  # '}'
            depth -= 1
            if depth == 0:
                break
        j += 1
    if j >= len(line):
        return None, -1
    try:
        usage = json.loads(line[i + len(_USAGE_MARKER) - 1:j + 1])
    except Exception:
        return None, -1
    if not isinstance(usage, dict):
        return _extract_usage(line, j + 1)
    if any(k in usage for k in _USAGE_KEYS):
        total = usage.get("totalTokens")
        parts = (usage.get("inputTokens") or 0,
                 usage.get("outputTokens") or 0,
                 usage.get("cacheReadTokens") or 0)
        if isinstance(total, int) and total != sum(parts):
            return _extract_usage(line, j + 1)  # lookalike — keep scanning
    return usage, j + 1


def _fast_assistant_event(line):
    """Fast path for assistant/message: {time, turn, usage} or None."""
    time_ms = _int_after(line, _TIME_MARKER)
    if time_ms is None:
        return None
    turn = _int_after(line, _TURN_MARKER)
    usage, _ = _extract_usage(line)
    if turn is None or usage is None:
        return None
    return {"type": "assistant/message", "time": time_ms,
            "data": {"turn": turn, "usage": usage}}


def _fast_tool_call_event(line):
    """Fast path for tool/call: {time, turn, callId, name} or None."""
    time_ms = _int_after(line, _TIME_MARKER)
    if time_ms is None:
        return None
    turn = _int_after(line, _TURN_MARKER)
    if turn is None:
        return None
    i = line.find(_CALLID_MARKER)
    if i < 0:
        return None
    start = i + len(_CALLID_MARKER)
    j = line.find(b'"', start)
    if j < 0:
        return None
    call_id = line[start:j].decode("utf-8", errors="replace")
    n = line.find(_NAME_MARKER, j)
    if n < 0:
        return None
    n_start = n + len(_NAME_MARKER)
    n_end = line.find(b'"', n_start)
    if n_end < 0:
        return None
    name = line[n_start:n_end].decode("utf-8", errors="replace")
    return {"type": "tool/call", "time": time_ms,
            "data": {"turn": turn, "callId": call_id, "name": name}}


def _fast_tool_result_event(line):
    """Fast path for tool/result: {time, source callId} or None."""
    time_ms = _int_after(line, _TIME_MARKER)
    i = line.find(_CALLID_MARKER)
    if time_ms is None or i < 0:
        return None
    start = i + len(_CALLID_MARKER)
    j = line.find(b'"', start)
    if j < 0:
        return None
    call_id = line[start:j].decode("utf-8", errors="replace")
    return {"type": "tool/result", "time": time_ms,
            "data": {"message": {"source": {"callId": call_id}}}}


def _events_from_bytes(raw):
    """Byte-level tolerant JSONL scan; returns (events, corrupt_line_count).

    Semantics match a full json.loads scan: blank lines are skipped, lines
    whose JSON cannot be parsed are counted as corrupt, valid non-event
    JSON is ignored — while the two heavy event types bypass full parsing
    through validated field extraction (full parse on any doubt).
    """
    events = []
    corrupt = 0
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        event = None
        line_type = _line_type(line)
        if line_type == _FAST_ASSISTANT:
            event = _fast_assistant_event(line)
        elif line_type == _FAST_TOOL_RESULT:
            event = _fast_tool_result_event(line)
        elif line_type == _FAST_TOOL_CALL:
            event = _fast_tool_call_event(line)
        elif line_type in _FULL_PARSE_TYPES:
            pass  # metric input — full parse below
        elif line_type is not None:
            # Valid envelope of an unneeded type (request/header,
            # agent/inbox/spliced, ...) — skipped without parsing; see the
            # corrupt_lines_skipped caliber note above.
            continue
        if event is not None:
            events.append(event)
            continue
        # Full-parse path: markerless lines (corruption classification) and
        # any fast-path doubt on a needed type (identical outcome, slower).
        try:
            parsed = json.loads(line)
        except Exception:
            corrupt += 1
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
    return events, corrupt


def _text_of(data):
    """Concatenate text parts of a user/message content array."""
    parts = []
    for chunk in (data.get("content") or []):
        if isinstance(chunk, dict) and chunk.get("type") == "text":
            parts.append(chunk.get("text") or "")
    return "\n".join(parts)


def _is_governance_turn(user_head):
    """Same governance-turn detection caliber as EVD-1071 (report §3.1)."""
    head = (user_head or "").strip()
    if not head:
        return False
    return (head.startswith("/governance")
            or 'name="governance"' in head
            or '<skill_content name="governance"' in head)


def _new_turn():
    return {
        "start_ms": None,
        "end_ms": None,
        "steps": 0,
        "first_user_ms": None,
        "first_user_head": "",
        "ask_times": [],
        "ask_suspended_ms": 0,
        "tool_calls": [],
        "in_tok": 0,
        "cache_tok": 0,
        "out_tok": 0,
        "llm_ms": 0,
        "tool_ms": 0,
        "unfinished": 0,
    }


def parse_session(events):
    """Walk one session's events; returns the raw per-turn record dict."""
    cwd = ""
    title = ""
    turns = {}
    current_turn = None
    pending_calls = {}
    open_steps = []
    orphans = 0

    for ev in events:
        if not isinstance(ev, dict):
            continue
        etype = ev.get("type")
        data = ev.get("data") or {}
        ts = ev.get("time")
        if etype == "session":
            if not cwd:
                cwd = data.get("cwd") or ""
            continue
        if etype == "session/title":
            title = data.get("title") or title
            continue

        turn_field = data.get("turn") if isinstance(data, dict) else None
        if turn_field is not None:
            current_turn = turn_field
        rec = turns.get(turn_field if turn_field is not None else current_turn)
        if rec is None and turn_field is not None:
            rec = turns.setdefault(turn_field, _new_turn())

        if etype == "turn/start":
            if rec is not None and rec["start_ms"] is None:
                rec["start_ms"] = ts
        elif etype == "turn/end":
            if rec is not None:
                rec["end_ms"] = ts
        elif etype == "user/message":
            if current_turn is None:
                orphans += 1
                continue
            rec = turns.setdefault(current_turn, _new_turn())
            text = _text_of(data if isinstance(data, dict) else {})
            if rec["first_user_ms"] is None:
                rec["first_user_ms"] = ts
                rec["first_user_head"] = text[:_USER_TEXT_HEAD]
        elif etype == "step/start":
            if current_turn is not None:
                turns.setdefault(current_turn, _new_turn())
            open_steps.append({
                "turn": turn_field if turn_field is not None else current_turn,
                "start": ts,
                "first_assistant": None,
            })
            if current_turn is not None:
                turns[current_turn]["steps"] += 1
        elif etype == "step/end":
            if open_steps:
                step = open_steps.pop()
                fa = step["first_assistant"]
                if fa is not None and step["start"] is not None:
                    owner = turns.get(step["turn"])
                    if owner is not None:
                        owner["llm_ms"] += fa - step["start"]
        elif etype == "assistant/message":
            if rec is not None:
                usage = data.get("usage") or (data.get("message") or {}).get(
                    "usage") or {}
                rec["in_tok"] += usage.get("inputTokens") or 0
                rec["cache_tok"] += usage.get("cacheReadTokens") or 0
                rec["out_tok"] += usage.get("outputTokens") or 0
            if open_steps and open_steps[-1]["first_assistant"] is None:
                owner_turn = turn_field if turn_field is not None else current_turn
                if open_steps[-1]["turn"] == owner_turn:
                    open_steps[-1]["first_assistant"] = ts
        elif etype == "tool/call":
            call_id = data.get("callId")
            if call_id is not None:
                pending_calls[call_id] = {
                    "turn": turn_field if turn_field is not None else current_turn,
                    "name": data.get("name"),
                    "t_call": ts,
                }
        elif etype == "tool/result":
            message = data.get("message") or {}
            source = message.get("source") or {}
            call_id = source.get("callId") or data.get("callId")
            call = pending_calls.pop(call_id, None) if call_id is not None else None
            if call is None:
                continue
            dur = (ts - call["t_call"]) if (ts is not None and call["t_call"] is not None) else 0
            owner = turns.get(call["turn"])
            if owner is not None:
                owner["tool_calls"].append({
                    "name": call["name"],
                    "t_call": call["t_call"],
                    "dur_ms": dur,
                })
                owner["tool_ms"] += dur
                if call["name"] == ASK_TOOL:
                    owner["ask_times"].append(call["t_call"])
                    owner["ask_suspended_ms"] += dur

    for turn_id, rec in turns.items():
        rec["unfinished"] = sum(
            1 for call in pending_calls.values() if call["turn"] == turn_id)

    return {
        "cwd": cwd,
        "title": title,
        "turns": turns,
        "orphans": orphans,
    }


def percentile(values, q):
    """Deterministic linear-interpolation percentile (None on empty)."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = (len(ordered) - 1) * q
    lo = int(idx)
    hi = min(lo + 1, len(ordered) - 1)
    frac = idx - lo
    return ordered[lo] + (ordered[hi] - ordered[lo]) * frac


def turn_metrics(turn_id, rec):
    """Derive the per-turn metric record (raw deltas + labeled residual)."""
    total = None
    if rec["start_ms"] is not None and rec["end_ms"] is not None:
        total = rec["end_ms"] - rec["start_ms"]

    ttfa = None
    time_to_work = None
    endpoint = "none"
    if rec["first_user_ms"] is not None and rec["ask_times"]:
        first_ask = min(rec["ask_times"])
        ttfa = first_ask - rec["first_user_ms"]
        for call in sorted(rec["tool_calls"], key=lambda c: c["t_call"] or 0):
            if call["name"] in GOVERNANCE_TOOL_NAMES:
                continue
            if call["t_call"] is not None and call["t_call"] >= first_ask:
                time_to_work = call["t_call"] - first_ask
                endpoint = "first_work_tool"
                break
        if time_to_work is None and total is not None and rec["end_ms"] >= first_ask:
            time_to_work = rec["end_ms"] - first_ask
            endpoint = "turn_end"

    residual = None
    if total is not None:
        residual = total - rec["llm_ms"] - rec["tool_ms"]

    return {
        "turn": turn_id,
        "start_ms": rec["start_ms"],
        "end_ms": rec["end_ms"],
        "total_ms": total,
        "steps": rec["steps"],
        "tool_calls": len(rec["tool_calls"]),
        "unfinished_tool_calls": rec["unfinished"],
        "ttfa_ms": ttfa,
        "time_to_work_ms": time_to_work,
        "work_endpoint": endpoint,
        "in_tok": rec["in_tok"],
        "cache_tok": rec["cache_tok"],
        "out_tok": rec["out_tok"],
        "llm_ms": rec["llm_ms"],
        "tool_ms": rec["tool_ms"],
        "other_residual_ms": residual,
        "ask_suspended_ms": rec["ask_suspended_ms"],
        "is_governance_turn": _is_governance_turn(rec["first_user_head"]),
    }


def _bucket_stats(values):
    return {
        "count": len(values),
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "max": max(values) if values else None,
    }


def _summarize(session_metrics):
    """Aggregate per-turn metric records into the totals block."""
    tokens = {
        "in": sum(t["in_tok"] for t in session_metrics),
        "cache_read": sum(t["cache_tok"] for t in session_metrics),
        "out": sum(t["out_tok"] for t in session_metrics),
    }
    total_ms = sum(t["total_ms"] for t in session_metrics if t["total_ms"] is not None)
    llm_ms = sum(t["llm_ms"] for t in session_metrics)
    tool_ms = sum(t["tool_ms"] for t in session_metrics)
    residual_ms = sum(t["other_residual_ms"] for t in session_metrics
                      if t["other_residual_ms"] is not None)
    shares = {"llm_pct": 0.0, "tool_pct": 0.0, "other_pct": 0.0}
    if total_ms > 0:
        shares = {
            "llm_pct": round(llm_ms / total_ms * 100, 1),
            "tool_pct": round(tool_ms / total_ms * 100, 1),
            "other_pct": round(residual_ms / total_ms * 100, 1),
        }
    ttfa_values = [t["ttfa_ms"] for t in session_metrics if t["ttfa_ms"] is not None]
    work_values = [t["time_to_work_ms"] for t in session_metrics
                   if t["time_to_work_ms"] is not None]
    return {
        "turns": len(session_metrics),
        "turns_with_ttfa": len(ttfa_values),
        "tokens": tokens,
        "time": {
            "total_ms": total_ms,
            "llm_ms": llm_ms,
            "tool_ms": tool_ms,
            "other_residual_ms": residual_ms,
            "ask_suspended_ms": sum(t["ask_suspended_ms"] for t in session_metrics),
        },
        "shares": shares,
        "ttfa_ms": _bucket_stats(ttfa_values),
        "time_to_work_ms": dict(
            _bucket_stats(work_values),
            endpoint_first_work_tool=sum(
                1 for t in session_metrics if t["work_endpoint"] == "first_work_tool"),
            endpoint_turn_end=sum(
                1 for t in session_metrics if t["work_endpoint"] == "turn_end"),
        ),
    }


def _tool_distribution(sessions):
    """Per-name tool aggregation from session-level raw tool-call lists."""
    tools = {}
    for session_record in sessions:
        for call in session_record["_raw_tool_calls"]:
            bucket = tools.setdefault(call["name"], {
                "count": 0, "total_ms": 0, "max_ms": 0})
            bucket["count"] += 1
            bucket["total_ms"] += call["dur_ms"]
            bucket["max_ms"] = max(bucket["max_ms"], call["dur_ms"])
    for bucket in tools.values():
        bucket["avg_ms"] = round(bucket["total_ms"] / bucket["count"], 1)
    return tools


def _cwd_fallback_from_session_path(rel_path):
    """Derive a workspace identifier from the session file's ancestors.

    RISK-050 (dsh upstream internal-face coupling — FIX-356): dsh v3
    session events carry no structured cwd/workspace field (real corpus,
    EVD-1088: 344/344 files have ``data={}``), so the only reliable
    workspace carrier is dsh's internal session-directory naming
    convention — the workspace directory under the sessions root is
    wrapped as ``--<workspace-id>--`` with the workspace path's
    separators normalized to ``-`` (e.g.
    ``--D-AI-agent-claude-coding-project_management_workflow--``). THIS
    function is the single point that encodes that convention: it
    inspects ancestor directory NAMES as plain strings and returns the
    unwrapped inner identifier — a filter-matching token, NOT a
    filesystem path (never reconstructed into a traversable path).
    Returns "" when no encoded ancestor exists; sessions whose event
    ``cwd`` is present never reach this fallback.

    ``rel_path`` is the session file path RELATIVE to the sessions root,
    so the ancestor walk stops at the root and never borrows names from
    outside the scanned corpus.
    """
    for parent in Path(rel_path).parents:
        name = parent.name
        if len(name) > 4 and name.startswith("--") and name.endswith("--"):
            return name[2:-2]
    return ""


def scan_sessions(sessions_root, workspace=None):
    """Scan a sessions root (read-only) and assemble the full report."""
    root = Path(sessions_root)
    started = time.monotonic()
    files = sorted(root.rglob(_SESSION_FILENAME))

    sessions = []
    files_failed = 0
    files_parsed = 0
    corrupt_lines = 0
    orphans = 0
    unfinished = 0

    for path in files:
        try:
            raw = _decompress_bytes(path.read_bytes())
        except GovernanceCostError:
            raise
        except Exception:
            files_failed += 1
            continue
        events, corrupt = _events_from_bytes(raw)
        corrupt_lines += corrupt
        files_parsed += 1
        rel_path = path.relative_to(root)
        parsed = parse_session(events)
        cwd = parsed["cwd"]
        if not cwd:
            # FIX-356: real v3 session events carry no cwd (data={}) — fall
            # back to the encoded workspace directory name (RISK-050, see
            # _cwd_fallback_from_session_path). Event cwd wins when present.
            cwd = _cwd_fallback_from_session_path(rel_path)
        if workspace is not None and workspace not in cwd:
            continue
        orphans += parsed["orphans"]

        turn_records = []
        session_raw_calls = []
        for turn_id, rec in parsed["turns"].items():
            turn_records.append(turn_metrics(turn_id, rec))
            session_raw_calls.extend(rec["tool_calls"])
        unfinished += sum(t["unfinished_tool_calls"] for t in turn_records)
        sessions.append({
            "file": rel_path.as_posix(),
            "cwd": cwd,
            "title": parsed["title"],
            "totals": _summarize(turn_records),
            "turns": turn_records,
            "_raw_tool_calls": session_raw_calls,
        })

    all_turns = [t for s in sessions for t in s["turns"]]
    totals = _summarize(all_turns)
    totals["tools"] = _tool_distribution(sessions)
    for session_record in sessions:
        del session_record["_raw_tool_calls"]

    report = {
        "schema": REPORT_SCHEMA,
        "task": TASK_ID,
        "generated_at": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "sessions_root": str(root),
        "workspace_filter": workspace,
        "scan": {
            "files_found": len(files),
            "files_parsed": files_parsed,
            "files_failed": files_failed,
            "corrupt_lines_skipped": corrupt_lines,
            "user_messages_before_first_turn": orphans,
            "unfinished_tool_calls": unfinished,
            "duration_ms": int((time.monotonic() - started) * 1000),
        },
        "calibration": CALIBRATION,
        "totals": totals,
        "sessions": sessions,
    }
    return report


#: Measurement-caliber disclosures (AUDIT-154 report §4 — machine-readable
#: so every report carries its own semantics).
CALIBRATION = {
    "tokens": (
        "inputTokens/cacheReadTokens/outputTokens are cumulative request "
        "volumes (audit §4.1), not context residency."),
    "llm_window_ms": (
        "sum over steps of (first assistant/message time - step/start time); "
        "raw two-timestamp deltas — TTFT vs decode NOT separable (the trace "
        "model has no first-token event); reported as one window."),
    "tool_time_ms": (
        "sum of paired tool/call->tool/result timestamp deltas; executions "
        "happen inside steps after the assistant message, so the llm window "
        "and tool time do not overlap by construction."),
    "other_residual_ms": (
        "turn total - llm - tool: a labeled arithmetic residual (harness "
        "gaps, uninstrumented waits) — never attributed to a single cause "
        "(audit §4.3/§4.4)."),
    "user_wait": (
        "ask_user_question call->result suspension (user think time) is "
        "inside turn totals and reported separately as ask_suspended_ms."),
    "ttfa": (
        "raw event-timestamp deltas — 按事件时间戳原始值报告，不加工不推算 "
        "(audit §4.3)."),
    "governance_tools": (
        "name-based classification, deliberately minimal: "
        + ", ".join(sorted(GOVERNANCE_TOOL_NAMES))
        + " — generic tools (read/pwsh/...) cannot be classified by name "
        "and count as work-tool candidates."),
    "sessions_cwd": (
        "dual-source: the session event's ``cwd`` wins when present; when "
        "it is absent this field carries a token unwrapped from the encoded "
        "ancestor directory name (--<id>--), empty when no encoded ancestor "
        "exists — a --workspace substring filter token, NOT a filesystem "
        "path."),
}

# ── RISK-055 acceptance face (FEAT-040 one-click re-verification path) ──────
#
# DEC-207① folded FEAT-034's numeric acceptance (TTFA p50 ≤ 25s / p95 ≤ 45s)
# into FEAT-040 and registered it as RISK-055: the trajectory re-verification
# has to run AFTER new sessions execute the reworked protocol, so the
# measurement itself cannot happen inside the FEAT-040 session. What CAN and
# MUST land here is the path: one command, the threshold constants in code
# (not in prose), the paired TTFA + TTW report, and an explicit PENDING verdict
# when the sample is still too small — never a green light borrowed from an
# unchanged baseline. Measuring a mechanism that has not run yet and calling
# it "verified" is exactly the honest-measurement failure AUDIT-154 named.

TTFA_ACCEPTANCE_TASK = "RISK-055"
TTFA_ACCEPTANCE_P50_MS = 25000
TTFA_ACCEPTANCE_P95_MS = 45000
#: Below this sample size the face reports PENDING instead of a verdict: two
#: turns cannot support a p95, and a p50 from one turn is an anecdote.
TTFA_ACCEPTANCE_MIN_TURNS = 3
TTFA_ACCEPTANCE_SOURCE = (
    "DEC-207① (FEAT-034 验收尾巴并入 FEAT-040；成对 TTFA+TTW；"
    "DEC-205 下界声明；同 EVD-1073/RISK-052 快照口径)")
TTFA_ACCEPTANCE_SCOPE = (
    "all turns carrying a measured TTFA — the same population as "
    "`totals.ttfa_ms`, so the number is directly comparable with the "
    "EVD-1073 / RISK-052 baseline. TTW is reported PAIRED per turn "
    "(first ask → first non-governance tool | turn end) because TTFA alone "
    "can be bought by asking sooner.")
#: Per-turn rows are capped so a large scan cannot balloon the report; the
#: worst offenders are the ones worth eyeballing.
TTFA_ACCEPTANCE_ROW_LIMIT = 20


def ttfa_acceptance(report):
    """RISK-055: TTFA/TTW acceptance verdict over a scanned report.

    Reads only the aggregate the scan already produced (no second pass over
    the traces), so the paired numbers come from the SAME snapshot as every
    other figure in the report — the caliber DEC-207① requires.
    """
    rows = []
    sessions = 0
    governance_turns = 0
    for session in report.get("sessions") or []:
        session_hit = False
        for turn in session.get("turns") or []:
            if turn.get("ttfa_ms") is None:
                continue
            session_hit = True
            if turn.get("is_governance_turn"):
                governance_turns += 1
            rows.append({
                "session": session.get("file"),
                "cwd": session.get("cwd"),
                "turn": turn.get("turn"),
                "ttfa_ms": turn.get("ttfa_ms"),
                "time_to_work_ms": turn.get("time_to_work_ms"),
                "work_endpoint": turn.get("work_endpoint"),
                "is_governance_turn": bool(turn.get("is_governance_turn")),
            })
        if session_hit:
            sessions += 1

    ttfa_values = [row["ttfa_ms"] for row in rows]
    ttw_values = [row["time_to_work_ms"] for row in rows
                  if row["time_to_work_ms"] is not None]
    ttfa_stats = _bucket_stats(ttfa_values)
    ttw_stats = _bucket_stats(ttw_values)

    if len(ttfa_values) < TTFA_ACCEPTANCE_MIN_TURNS:
        verdict = "PENDING"
        reason = (
            "sample too small: %d turn(s) carry a measured TTFA, need >= %d — "
            "run new sessions under the reworked protocol, then re-run this "
            "command (a verdict derived from the unchanged baseline would be "
            "a borrowed green light)"
            % (len(ttfa_values), TTFA_ACCEPTANCE_MIN_TURNS))
    else:
        over = []
        if ttfa_stats["p50"] > TTFA_ACCEPTANCE_P50_MS:
            over.append("p50 %s > %s" % (_fmt_ms(ttfa_stats["p50"]),
                                         _fmt_ms(TTFA_ACCEPTANCE_P50_MS)))
        if ttfa_stats["p95"] > TTFA_ACCEPTANCE_P95_MS:
            over.append("p95 %s > %s" % (_fmt_ms(ttfa_stats["p95"]),
                                         _fmt_ms(TTFA_ACCEPTANCE_P95_MS)))
        if over:
            verdict = "FAIL"
            reason = "TTFA acceptance exceeded: " + "; ".join(over)
        else:
            verdict = "PASS"
            reason = ("TTFA p50 %s <= %s and p95 %s <= %s over %d measured "
                      "turn(s)"
                      % (_fmt_ms(ttfa_stats["p50"]),
                         _fmt_ms(TTFA_ACCEPTANCE_P50_MS),
                         _fmt_ms(ttfa_stats["p95"]),
                         _fmt_ms(TTFA_ACCEPTANCE_P95_MS), len(ttfa_values)))

    worst = sorted(rows, key=lambda row: -(row["ttfa_ms"] or 0))
    return {
        "task": TTFA_ACCEPTANCE_TASK,
        "source": TTFA_ACCEPTANCE_SOURCE,
        "scope": TTFA_ACCEPTANCE_SCOPE,
        "thresholds_ms": {"p50": TTFA_ACCEPTANCE_P50_MS,
                          "p95": TTFA_ACCEPTANCE_P95_MS,
                          "min_turns": TTFA_ACCEPTANCE_MIN_TURNS},
        "samples": {"turns_with_ttfa": len(ttfa_values),
                    "sessions_with_ttfa": sessions,
                    "governance_turns": governance_turns},
        "ttfa_ms": ttfa_stats,
        "time_to_work_ms": ttw_stats,
        "paired_rows": worst[:TTFA_ACCEPTANCE_ROW_LIMIT],
        "paired_rows_truncated": max(0, len(worst) - TTFA_ACCEPTANCE_ROW_LIMIT),
        "verdict": verdict,
        "reason": reason,
    }


def format_ttfa_acceptance(result):
    """The paired TTFA + TTW acceptance block (RISK-055 template)."""
    lines = [
        "",
        "=== RISK-055 TTFA/TTW Acceptance (FEAT-040 re-verification path) ===",
        "task: %s | thresholds: TTFA p50 <= %s, p95 <= %s | min sample %d"
        % (result["task"], _fmt_ms(result["thresholds_ms"]["p50"]),
           _fmt_ms(result["thresholds_ms"]["p95"]),
           result["thresholds_ms"]["min_turns"]),
        "source: %s" % result["source"],
        "scope:  %s" % result["scope"],
        "samples: %d turn(s) with TTFA across %d session(s) "
        "(%d governance-turn(s))"
        % (result["samples"]["turns_with_ttfa"],
           result["samples"]["sessions_with_ttfa"],
           result["samples"]["governance_turns"]),
        "TTFA  : p50=%s p95=%s max=%s"
        % (_fmt_ms(result["ttfa_ms"]["p50"]), _fmt_ms(result["ttfa_ms"]["p95"]),
           _fmt_ms(result["ttfa_ms"]["max"])),
        "TTW   : p50=%s p95=%s max=%s (paired with the TTFA rows below)"
        % (_fmt_ms(result["time_to_work_ms"]["p50"]),
           _fmt_ms(result["time_to_work_ms"]["p95"]),
           _fmt_ms(result["time_to_work_ms"]["max"])),
    ]
    rows = result.get("paired_rows") or []
    if rows:
        lines.append("paired rows (worst TTFA first):")
        lines.append("  %-34s %-6s %-10s %-10s %-16s %s"
                     % ("session", "turn", "TTFA", "TTW", "endpoint", "gov"))
        for row in rows:
            lines.append("  %-34s %-6s %-10s %-10s %-16s %s"
                         % ((row["session"] or "-")[-34:], row["turn"],
                            _fmt_ms(row["ttfa_ms"]),
                            _fmt_ms(row["time_to_work_ms"]),
                            row["work_endpoint"] or "-",
                            "yes" if row["is_governance_turn"] else "no"))
        if result.get("paired_rows_truncated"):
            lines.append("  ... and %d more row(s)"
                         % result["paired_rows_truncated"])
    else:
        lines.append("paired rows: none — no turn in the scan carries a "
                     "measured TTFA (first ask_user_question)")
    lines.append("verdict: %s — %s" % (result["verdict"], result["reason"]))
    lines.append("")
    return "\n".join(lines)


def _fmt_ms(ms):
    if ms is None:
        return "-"
    seconds = ms / 1000.0
    if seconds < 60:
        return f"{seconds:.1f}s"
    return f"{int(seconds // 60)}m{seconds % 60:.0f}s"


def _fmt_tok(n):
    if n is None:
        return "-"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1000:
        return f"{n / 1000:.1f}K"
    return str(n)


def format_text(report):
    """Human-readable summary of a report dict (aggregate + top rows)."""
    scan = report["scan"]
    totals = report["totals"]
    lines = []
    lines.append("=== Governance Cost Report (FEAT-032 — schema %s) ==="
                 % REPORT_SCHEMA)
    lines.append("sessions_root: %s" % report["sessions_root"])
    lines.append("workspace filter: %s" % (report["workspace_filter"] or "-"))
    lines.append(
        "files scanned: %d (parsed %d, failed %d; corrupt lines skipped %d)"
        % (scan["files_found"], scan["files_parsed"], scan["files_failed"],
           scan["corrupt_lines_skipped"]))
    lines.append("scan wall time: %s" % _fmt_ms(scan["duration_ms"]))
    lines.append("")
    lines.append("-- Totals (%d sessions, %d turns; %d with TTFA) --"
                 % (len(report["sessions"]), totals["turns"],
                    totals["turns_with_ttfa"]))
    time_blk = totals["time"]
    shares = totals["shares"]
    lines.append(
        "turn wall time: %s  (llm %s%% | tools %s%% | other/residual %s%%)"
        % (_fmt_ms(time_blk["total_ms"]), shares["llm_pct"],
           shares["tool_pct"], shares["other_pct"]))
    lines.append(
        "  llm=%s  tool=%s  other(residual: harness gaps + uninstrumented waits)=%s"
        % (_fmt_ms(time_blk["llm_ms"]), _fmt_ms(time_blk["tool_ms"]),
           _fmt_ms(time_blk["other_residual_ms"])))
    lines.append(
        "ask_user_question suspension (user wait): total %s"
        % _fmt_ms(time_blk["ask_suspended_ms"]))
    tokens = totals["tokens"]
    lines.append(
        "tokens (cumulative request volume — audit §4.1): in=%s cache_read=%s out=%s"
        % (_fmt_tok(tokens["in"]), _fmt_tok(tokens["cache_read"]),
           _fmt_tok(tokens["out"])))
    ttfa = totals["ttfa_ms"]
    lines.append(
        "TTFA (user message → first ask_user_question): measured %d turns — "
        "p50=%s p95=%s max=%s"
        % (ttfa["count"], _fmt_ms(ttfa["p50"]), _fmt_ms(ttfa["p95"]),
           _fmt_ms(ttfa["max"])))
    work = totals["time_to_work_ms"]
    lines.append(
        "time-to-work (first ask → first non-governance tool | turn end): "
        "measured %d — p50=%s p95=%s max=%s (endpoints: first_work_tool=%d, "
        "turn_end=%d)"
        % (work["count"], _fmt_ms(work["p50"]), _fmt_ms(work["p95"]),
           _fmt_ms(work["max"]), work["endpoint_first_work_tool"],
           work["endpoint_turn_end"]))
    tools = totals.get("tools") or {}
    if tools:
        lines.append("top tools by total duration:")
        ranked = sorted(tools.items(), key=lambda kv: -kv[1]["total_ms"])
        for name, bucket in ranked[:15]:
            lines.append(
                "  %-24s x%-5d total %-10s max %-9s avg %.1fs"
                % (name, bucket["count"], _fmt_ms(bucket["total_ms"]),
                   _fmt_ms(bucket["max_ms"]), bucket["avg_ms"] / 1000.0))
    sessions = sorted(
        report["sessions"],
        key=lambda s: -(s["totals"]["time"]["total_ms"] or 0))
    if sessions:
        lines.append("")
        lines.append("-- Sessions (top %d by turn wall time) --"
                     % min(20, len(sessions)))
        for s in sessions[:20]:
            st = s["totals"]
            lines.append(
                "  %-10s turns=%-4d in=%-8s out=%-7s ttfa_p50=%-8s  %s / %r"
                % (_fmt_ms(st["time"]["total_ms"]), st["turns"],
                   _fmt_tok(st["tokens"]["in"]), _fmt_tok(st["tokens"]["out"]),
                   _fmt_ms(st["ttfa_ms"]["p50"]),
                   (s["cwd"].replace("\\", "/").rstrip("/").split("/")[-1]
                    or "-"),
                   s["title"][:40]))
    lines.append("")
    return "\n".join(lines)


def add_arguments(parser):
    """Register the subcommand's arguments (single source for engine+tests)."""
    parser.add_argument(
        "--sessions-root", default=None,
        help="Directory containing **/session.v3.jsonl.zstd traces. "
             "Defaults to the DSH_SESSIONS_ROOT environment variable; "
             "when neither is present the command fails closed (exit 2) — "
             "user paths are never hardcoded.")
    parser.add_argument(
        "--workspace", default=None,
        help="Only include sessions whose recorded cwd contains this "
             "substring (applied before aggregation).")
    parser.add_argument(
        "--format", choices=("json", "text"), default="text",
        help="Machine-readable JSON report or human-readable summary "
             "(default: text).")
    parser.add_argument(
        "--ttfa-acceptance", action="store_true",
        help="Append the RISK-055 TTFA/TTW acceptance block (paired report + "
             "PASS/FAIL/PENDING verdict against TTFA p50<=25s / p95<=45s). "
             "Same snapshot as the rest of the report — this is the one-click "
             "re-verification path (DEC-207①).")


def _build_arg_parser():
    parser = argparse.ArgumentParser(
        prog="governance-cost-report",
        description="Governance cost observability report (FEAT-032): "
                    "TTFA, time-to-substantive-work, token breakdown, tool "
                    "duration distribution, LLM vs tool time shares.")
    add_arguments(parser)
    return parser


def cmd_governance_cost_report(args):
    """CLI entry wired into verify_workflow.py's dispatch table."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    root = getattr(args, "sessions_root", None)
    if not root:
        root = (os.environ.get("DSH_SESSIONS_ROOT") or "").strip() or None
    if not root:
        print("ERROR: --sessions-root 未提供且环境变量 DSH_SESSIONS_ROOT 未设置"
              "——请显式传入 --sessions-root <dir>（不硬编码用户路径）。",
              file=sys.stderr)
        sys.exit(2)
    if not Path(root).is_dir():
        print("ERROR: sessions root 不存在或不是目录: %s" % root,
              file=sys.stderr)
        sys.exit(2)

    try:
        report = scan_sessions(root, workspace=getattr(args, "workspace", None))
    except GovernanceCostError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        sys.exit(1)

    fmt = getattr(args, "format", "text")
    acceptance = (ttfa_acceptance(report)
                  if getattr(args, "ttfa_acceptance", False) else None)
    if acceptance is not None:
        report["ttfa_acceptance"] = acceptance
    if fmt == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_text(report))
        if acceptance is not None:
            print(format_ttfa_acceptance(acceptance))
