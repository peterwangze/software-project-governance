#!/usr/bin/env python3
"""M2 discovery-closure loop gate processor — ADR-021 §3.2.1 (FEAT-081 B4).

NAMING NOTE (acceptance 5, FEAT-081): the ``loop`` in this module's name
is the **discovery→closure loop** of ADR-021 M2 / DEC-286(6) 「发现即闭环」
(the governance contract), NOT the Loop-engineering PARO runtime of
ADR-014/FEAT-006 — that domain lives in ``infra/loop_gate_processor.py``
(a different package level; imports are package-qualified so the two never
shadow). Nothing here activates, schedules or orchestrates any runtime:
this module is a deterministic word-set detector plus ledger bookkeeping.

The three pieces (ADR-021 §3.2.1, spec-literal):

  1. **face-5 词集** — ``DEFERRED_LITERAL_WORDS`` + ``DEFERRED_PATTERN_WORDS``
     (first-version word set, tunable from ledger data — RT-5);
  2. **否定语境窗口** — a hit whose preceding 8 characters contain one of
     废除/禁止/违规/=/不得 does NOT fire (quoting a rule while negating it
     ≠ performing the behavior; this window is the double-insurance layer
     over the family exemptions, ADR §3.2.1 fourth element);
  3. **三键台账** — every word-set hit on an in-scope added row is bucketed
     by ``命中词 × 行族 × 否定语境命中(bool)`` in the guard-owned
     observation ledger; the bucket summary is the false-positive-rate
     report data the WARN→FAIL flip decision owes before entering
     decision-log (RT-5: 给「数据回流调词集」一个容器).

Row-family scope (ADR §3.2.1, D3 豁免清单): ``evidence`` (EVD- rows) and
``task_status`` (plan-tracker task rows) are judged; ``decision`` (DEC-
rows), ``review`` (REVIEW- machine rows) and ``ops_ledger`` receipts are
exempt — a DEC quoting 「登记待以后」 records a governance fact, it does
not perform the behavior.

Posture (ADR §3.2.1 姿态): **WARN first, 渐进 FAIL** — the flip goes
through decision-log with the ledger-derived false-positive report, never
silently. ``DEFERRED_REGISTRATION_POSTURE`` is that first-version posture
constant; a detector-side error is fail-closed *disclosure* (the engine
emits a loud WARN-class issue, never a silent skip — ADR §2.4 L4).

SKIP 语义分态 (CR-R1-2, FEAT-081): ``classify_observation_face`` keeps the
two SKIP kinds distinguishable and attributed — ``vacuum`` (nothing to
observe: no problems raised, no deferrals, no anomaly) versus
``orchestration_fallback`` (the detection/collection orchestration could
not do its job — ledger unreadable/corrupt, row-family read failure); a
fallback is disclosed, never reported as a measured vacuum, and any
deferred signal suppresses SKIP entirely (the rate-zeroing path).

Purity contract (provenance_domain discipline): stdlib only; this module
NEVER imports ``verify_workflow`` — the engine consumes the domain, never
the reverse. All I/O (ledger file read/append) stays with the engine.
"""

from __future__ import annotations

import json
import re

__all__ = [
    "DEFERRED_REGISTRATION_ISSUE_TYPE",
    "DEFERRED_REGISTRATION_POSTURE",
    "DEFERRED_LITERAL_WORDS",
    "DEFERRED_PATTERN_WORDS",
    "NEGATIVE_CONTEXT_MARKERS",
    "NEGATIVE_CONTEXT_WINDOW_CHARS",
    "FAMILY_EVIDENCE",
    "FAMILY_TASK_STATUS",
    "DEFERRED_SCOPED_FAMILIES",
    "DEFERRED_EXEMPT_FAMILIES",
    "SKIP_VACUUM",
    "SKIP_ORCHESTRATION_FALLBACK",
    "LEDGER_SCHEMA_VERSION",
    "family_for_row",
    "scan_deferred_hits",
    "judge_deferred_row",
    "render_issue_detail",
    "DEFERRED_ISSUE_EXPECTED",
    "build_ledger_entry",
    "parse_ledger_line",
    "ledger_bucket",
    "deferred_events_from_entries",
    "observation_face_record",
    "classify_observation_face",
    "summarize_ledger_buckets",
]

# Issue vocabulary consumed by the face-5 generic rendering.
DEFERRED_REGISTRATION_ISSUE_TYPE = "deferred_registration"
# 渐进 FAIL first version = WARN（翻转经 decision-log + 台账误报率报告，
# ADR §3.2.1 姿态——与本常量同 commit 调整姿态即静默翻转，禁止）。
DEFERRED_REGISTRATION_POSTURE = "warn"

# ── 三件套之一：词集（首个版本，可随台账数据调优——RT-5）──────────────────
DEFERRED_LITERAL_WORDS = (
    "待以后", "后续处理", "后续完善", "待后续", "留待", "择期",
    "登记待", "待收尾", "留池", "候选池", "下版处理", "延后处理",
)
# Regex-shaped words (ADR §3.2.1 词集末项: the retired 候选池 practice
# residue — 0.9[4-9] pools named after future versions).
DEFERRED_PATTERN_WORDS = (re.compile(r"0\.9[4-9]\s*池"),)

# ── 三件套之二：否定语境窗口（规范级第四判定要素）────────────────────────
# Spec ambiguity resolution (FEAT-081, disclosed in the task return): the
# ADR §3.2.1 text says 「命中词前 8 个字符」, but its own acceptance
# criterion 3 REQUIRES 「'登记待以后'=违规」-shaped rows to yield ZERO
# issues — a preceding-only window cannot exempt that suffix-judgment
# shape (the ``=`` follows the hit). Both directions are therefore judged:
# a marker within 8 chars immediately BEFORE or immediately AFTER the hit
# span exempts (recorded as negative_context_hit either way — the ledger
# bucket keeps the data the WARN→FAIL flip review needs to tighten this).
NEGATIVE_CONTEXT_MARKERS = ("废除", "禁止", "违规", "=", "不得")
NEGATIVE_CONTEXT_WINDOW_CHARS = 8

# ── 行族范围与豁免（D3 豁免清单）──────────────────────────────────────────
FAMILY_EVIDENCE = "evidence"
FAMILY_TASK_STATUS = "task_status"
DEFERRED_SCOPED_FAMILIES = (FAMILY_EVIDENCE, FAMILY_TASK_STATUS)
DEFERRED_EXEMPT_FAMILIES = ("decision", "review", "ops_ledger")

# ── SKIP 分态归因键（CR-R1-2：两类 SKIP 必须可区分、可追溯）────────────────
SKIP_VACUUM = "vacuum"
SKIP_ORCHESTRATION_FALLBACK = "orchestration_fallback"

LEDGER_SCHEMA_VERSION = 1

DEFERRED_ISSUE_EXPECTED = (
    "受管新增行不含「登记待以后」语义（DEC-286(6) 发现即闭环：触发点闭环，"
    "付不起闭环成本的动作不开始；规则引用请落 decision/review 豁免行族或用"
    "否定语境——ADR-021 §3.2.1）")


def family_for_row(surface, row_key):
    """Map a face-5 record to its deferred-detection family.

    ``evidence-log.md`` rows split by prefix (``EVD-`` → evidence,
    ``REVIEW-`` → review-exempt); ``plan-tracker.md`` task rows are
    task_status; ``decision-log.md`` → decision-exempt; ``*.ops.jsonl``
    receipts → ops_ledger-exempt. Unknown surfaces → None (not managed,
    not judged). Pure; never raises.
    """
    surface_text = str(surface or "")
    if surface_text == "evidence-log.md":
        key = str(row_key or "")
        if key.startswith("EVD-"):
            return FAMILY_EVIDENCE
        if key.startswith("REVIEW-"):
            return "review"
        return None
    if surface_text == "plan-tracker.md":
        return FAMILY_TASK_STATUS
    if surface_text == "decision-log.md":
        return "decision"
    if surface_text.endswith(".ops.jsonl"):
        return "ops_ledger"
    return None


def scan_deferred_hits(row_text):
    """Every word-set hit on the row → tuple of hit dicts.

    Each hit: ``{"word", "start", "end", "negative_context_hit"}`` where
    ``negative_context_hit`` is True when a negation marker sits in the
    exemption window — within ``NEGATIVE_CONTEXT_WINDOW_CHARS`` characters
    immediately BEFORE **or AFTER** the hit span (bidirectional arm per
    the ADR's own acceptance criterion 3; see the constant block note).
    Overlapping literal hits (「登记待以后」 hits both 登记待 and 待以后)
    are all reported: the ledger buckets per word, and per-word counts are
    the tuning data. Pure; never raises.
    """
    text = str(row_text or "")
    spans = []
    for word in DEFERRED_LITERAL_WORDS:
        start = text.find(word)
        while start >= 0:
            spans.append((start, start + len(word), word))
            start = text.find(word, start + 1)
    for pattern in DEFERRED_PATTERN_WORDS:
        for match in pattern.finditer(text):
            spans.append((match.start(), match.end(), match.group(0)))
    spans.sort()
    window = NEGATIVE_CONTEXT_WINDOW_CHARS
    hits = []
    for start, end, word in spans:
        before = text[max(0, start - window):start]
        after = text[end:end + window]
        negated = any(
            marker in before or marker in after
            for marker in NEGATIVE_CONTEXT_MARKERS)
        hits.append({
            "word": word,
            "start": start,
            "end": end,
            "negative_context_hit": negated,
        })
    return tuple(hits)


def judge_deferred_row(surface, row_key, row_text):
    """Judge ONE added/changed face-5 record against the word set.

    Returns None when the row's family is out of scope (exempt or
    unmanaged) or no word hits; otherwise::

        {"family": str, "row_key": str, "hits": [hit, ...],
         "fired": bool, "fired_words": [str, ...]}

    ``fired`` is False when EVERY hit was exempted by the negative-context
    window (rule-quoting shape). Pure; never raises.
    """
    family = family_for_row(surface, row_key)
    if family is None or family not in DEFERRED_SCOPED_FAMILIES:
        return None
    hits = scan_deferred_hits(row_text)
    if not hits:
        return None
    fired_words = []
    for hit in hits:
        if not hit["negative_context_hit"] and hit["word"] not in fired_words:
            fired_words.append(hit["word"])
    return {
        "family": family,
        "row_key": str(row_key or ""),
        "hits": list(hits),
        "fired": bool(fired_words),
        "fired_words": fired_words,
    }


def render_issue_detail(judgement):
    """Render the deferred_registration issue detail line (pure).

    Wording lives with the word set so future ledger-driven tuning changes
    one file (this one), not the engine.
    """
    words = "、".join(judgement["fired_words"]) or "?"
    return (
        "deferred_registration: 新增 {0} 行 `{1}` 命中「登记待以后」词集"
        "（{2}）——DEC-286(6) 发现即闭环：触发点闭环，「登记待以后」状态废除；"
        "观察期 WARN（渐进 FAIL 翻转经 decision-log + 台账误报率报告，"
        "ADR-021 §3.2.1）".format(
            judgement["family"], judgement["row_key"], words))


def build_ledger_entry(date_str, surface, family, row_key, line, hit_word,
                       negative_context_hit):
    """Build ONE three-key ledger entry (a single word hit on a row).

    ``fired`` is derived (not passed) so it can never disagree with the
    exemption flag: fired ⇔ not negative_context_hit. Pure.
    """
    return {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "kind": "deferred_hit",
        "date": str(date_str or ""),
        "surface": str(surface or ""),
        "family": str(family or ""),
        "row_key": str(row_key or ""),
        "line": line,
        "hit_word": str(hit_word or ""),
        "negative_context_hit": bool(negative_context_hit),
        "fired": not bool(negative_context_hit),
    }


def parse_ledger_line(line):
    """Parse one ledger JSONL line → ``(entry, error)``.

    ``error`` is a non-empty string on malformed JSON, a non-dict root, or
    a foreign/wrong-schema entry — the caller reports a read anomaly
    (fail-closed disclosure, never a silent skip). Accepted kinds:
    ``deferred_hit`` and ``observation_face``. Never raises.
    """
    text = str(line or "").strip()
    if not text:
        return None, "empty line"
    try:
        data = json.loads(text)
    except (ValueError, TypeError) as exc:
        return None, "invalid JSON: {0}".format(exc)
    if not isinstance(data, dict):
        return None, "non-object line"
    if data.get("schema_version") != LEDGER_SCHEMA_VERSION:
        return None, "unknown schema_version: {0!r}".format(
            data.get("schema_version"))
    kind = data.get("kind")
    if kind not in ("deferred_hit", "observation_face"):
        return None, "unknown kind: {0!r}".format(kind)
    if not isinstance(data.get("date"), str) or not data.get("date"):
        return None, "missing date"
    return data, None


def ledger_bucket(entry):
    """The three-key bucket of a deferred_hit entry: (命中词, 行族,
    否定语境命中). Pure."""
    return (str(entry.get("hit_word", "")),
            str(entry.get("family", "")),
            bool(entry.get("negative_context_hit")))


def deferred_events_from_entries(entries, today):
    """Fired deferred_hit entries dated ``today`` → Check 42 events.

    One ``{"id": row_key, "kind": "deferred_registration"}`` event per
    FIRED entry (exempted and other-day entries are ledger data, not
    violations — the 违规前置 counts detections, not quotes). Pure.
    """
    events = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("kind") != "deferred_hit":
            continue
        if entry.get("date") != today:
            continue
        if not entry.get("fired"):
            continue
        events.append({
            "id": str(entry.get("row_key", "")),
            "kind": DEFERRED_REGISTRATION_ISSUE_TYPE,
        })
    return events


def observation_face_record(observation, date_str):
    """Build the per-run observation-face ledger record (SKIP 分态归因).

    ``observation`` is the engine-tracked dict
    ``{"rows_judged", "hits", "fired", "detector_errors"}``;
    ``skip_kind`` attribution: detector errors → orchestration_fallback;
    otherwise vacuum (window ran, zero fired hits — including the
    nothing-to-judge run). Pure.
    """
    obs = observation if isinstance(observation, dict) else {}
    detector_errors = int(obs.get("detector_errors", 0) or 0)
    fired = int(obs.get("fired", 0) or 0)
    if detector_errors:
        skip_kind = SKIP_ORCHESTRATION_FALLBACK
        reason = ("检测器异常 ×{0}——编排异常兜底（fail-closed 披露，"
                  "ADR-021 §2.4 L4：检测失效不得静默）".format(detector_errors))
    elif fired:
        skip_kind = None  # fired hits — not a SKIP shape at all
        reason = "{0} fired deferred hit(s)".format(fired)
    else:
        skip_kind = SKIP_VACUUM
        rows = int(obs.get("rows_judged", 0) or 0)
        reason = ("检测编排运行、零命中（rows_judged={0}）——真空面："
                  "无观测义务".format(rows))
    return {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "kind": "observation_face",
        "date": str(date_str or ""),
        "skip_kind": skip_kind,
        "reason": reason,
        "rows_judged": int(obs.get("rows_judged", 0) or 0),
        "hits": int(obs.get("hits", 0) or 0),
        "fired": fired,
        "detector_errors": detector_errors,
    }


def classify_observation_face(problems_raised, deferred_detections, anomaly):
    """SKIP 语义分态 (CR-R1-2) → ``None`` or ``{"skip_kind", "reason"}``.

      - ``anomaly`` truthy → **orchestration_fallback** (the collection/
        detection orchestration could not measure — disclosed, never
        reported as a vacuum, never silently zero);
      - ``problems_raised == 0 ∧ deferred_detections == 0`` → **vacuum**
        (nothing to observe — 无观测义务);
      - otherwise ``None`` (a live observation face: normal rate judging,
        SKIP is not available — deferred>0 forces the rate-zeroing path).

    Pure; never raises.
    """
    if anomaly:
        reason = str(anomaly.get("reason", "")) if isinstance(
            anomaly, dict) else str(anomaly)
        kind = str(anomaly.get("kind", "")) if isinstance(
            anomaly, dict) else ""
        return {
            "skip_kind": SKIP_ORCHESTRATION_FALLBACK,
            "reason": (
                "编排异常兜底{0}：{1}——检测面数据缺失按降级披露（CR-R1-2 / "
                "ADR-021 §2.4：异常不隐藏，不与真空面混同）".format(
                    "（{0}）".format(kind) if kind else "", reason or "unspecified")),
        }
    if not problems_raised and not deferred_detections:
        return {
            "skip_kind": SKIP_VACUUM,
            "reason": "当日无新增问题行且无 deferred 检测——无观测义务",
        }
    return None


def summarize_ledger_buckets(entries):
    """误报率报告数据 (RT-5) — bucket counts + 否定语境豁免占比.

    Input: parsed deferred_hit entries (any dates — the report is the
    observation-period aggregate). Output::

        {"buckets": [{"hit_word", "family", "negative_context_hit",
                      "count"}], "total_hits", "exempted",
         "exemption_ratio"}

    The WARN→FAIL flip decision owes this report into evidence BEFORE the
    decision-log entry (ADR §3.2.1 观察期台账). Pure.
    """
    counts = {}
    total = 0
    exempted = 0
    for entry in entries or []:
        if not isinstance(entry, dict) or entry.get("kind") != "deferred_hit":
            continue
        key = ledger_bucket(entry)
        counts[key] = counts.get(key, 0) + 1
        total += 1
        if key[2]:
            exempted += 1
    buckets = [
        {"hit_word": word, "family": family,
         "negative_context_hit": negated, "count": count}
        for (word, family, negated), count in sorted(
            counts.items(), key=lambda item: (
                item[0][0], item[0][1], item[0][2]))
    ]
    return {
        "buckets": buckets,
        "total_hits": total,
        "exempted": exempted,
        "exemption_ratio": (exempted / total) if total else 0.0,
    }
