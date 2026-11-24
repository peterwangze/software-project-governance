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
  2. **否定语境窗口** — the eight characters on each side of a hit
     distinguish a local prohibition, a rule quotation or a pool exit from
     an actual deferral. Table cells and clause boundaries limit the match.
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
the reverse. No I/O lives here: ledger appends (writes) stay with the
engine, while ledger reads live in the shared leaf
``provenance_domain.read_deferred_ledger_events`` (FEAT-083), which
reuses this module's pure parsers via a function-local import.
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
# Rule quotations may precede or follow the hit (DEC-301). An equals sign
# connects the hit to a judgement; assignments of status or priority do not.
# Original marker inventory is public; "=" requires a rule predicate.
NEGATIVE_CONTEXT_MARKERS = ("废除", "禁止", "违规", "=", "不得")
NEGATIVE_CONTEXT_WINDOW_CHARS = 8
_CLAUSE_EDGE = re.compile(r"[|，,。;；!?！？：:、\r\n]")
_QUOTES_AND_SPACE = " \t`'\"‘’“”「」『』"
_OBJECT = r"(?:[把将](?:其|(?:该|此|本|新增|新发现)?(?:问题|事项|任务|缺陷|项)))?"
_DENIAL = re.compile(
    r"(?:废除|禁止|不得|不要|不能|不可|不应|不必|无需|避免|防止|防范|预防|谨防|(?:^|\s)防|"
    r"拒绝|并非|不是|非|不再|不)" + _OBJECT
    + r"(?:再|继续|采用|作为|进行|列入|纳入|放入|转入|进入|加入)*$")
_RULE_JUDGEMENT = re.compile(
    r"^(?:(?:状态|做法|行为)\s*|[=＝]\s*|被|已|是|属(?:于)?|视为|判为)"
    r"(?:废除|禁止|违规|不得采用)")
_QUOTE_PAIRS = (("「", "」"), ("『", "』"), ("“", "”"), ("‘", "’"),
                ('"', '"'), ("'", "'"), ("`", "`"))
_RULE_REFERENCE = re.compile(r"^(?:的)?(?:规则引用|规则原文)")
_RULE_CITATION = re.compile(r"(?:DEC-\d+|ADR-\d+|规则|制度)(?:[(（]\d+[)）])?[ \t]*$")
_CLOSED_GAP = re.compile(r"^(?:会计|制度|规则|登记)?(?:缺口|漏洞)(?:已经|已)?"
                         r"(?:修复|闭合|闭环|补齐|消除)(?=$|[，,。;；|）)\s])")
_POOL_EXIT = re.compile(r"(?:退出|移出|转出|移除|清空|关闭|清理完|撤出)(?:了)?$")
_POOL_RESULT = re.compile(r"^(?:(?:已经|已)(?:清空|清理完|处理完|移除|退役|关闭)|"
                          r"(?:中|内)?(?:的)?(?:事项|任务|条目)(?:均已|已|全部)(?:办结|完成))")
_FROM_POOL = re.compile(r"(?:自|从)$")
_REMOVED = re.compile(r"^(?:中|内)?(?:移出|移除|剔除|删除|撤出)")
# A record citation needs both a reference verb and its object. A bare
# numbered pool item may equally well be the destination of a new deferral.
_CITE = re.compile(r"(?:引用|引|据|参照|参见|详见|参阅|查阅)$")
_CITED_RECORD = re.compile(r"^(?:行|记录|条目|原文)(?:为准|为据|所载|所示|[()（）]|$)")
_POOL_ITEM = re.compile(r"[ \t]*[#＃][0-9]+[ \t]*")
_SOURCE_NOTE = re.compile(r"(?:首票|末票|第[一二三四五六七八九十0-9]+票|来源|出处)[(（]$")
_FINISHED_NOTE = re.compile(r"(?:收官|办结|完成|闭环)[(（]$")
_REFERENCE_DETAIL = re.compile(r"^(?:P[0-9]+\s*(?:优先)?\s*)?(?=[)）—–]|$)")
_SETTLED_ITEM = re.compile(r"^(?:清账|办结|闭环)(?=[)）—–]|$)")
_ALREADY_SETTLED = re.compile(r"^(?:已经|已)(?:清账|办结|闭环)(?=[)）—–]|$)")
_TICKET_NOTE = re.compile(r"^[(（][A-Z]{2,8}-[0-9]")
_PAST_PERIOD = r"(?:上|前|上次|前次|上一|前一)(?:轮|次|版|会话)"
_PAST_SOURCE = re.compile(_PAST_PERIOD + "$")
_SOURCE_TITLE = re.compile(r"^[『「“《]")
_SOURCE_LOCATION = re.compile(r"(?:§\s*|快照\s*|snapshot\s+)v?\d+(?:\.\d+){1,2}\s*$")
_SNAPSHOT_LABEL = re.compile(r"(?:^|" + _CLAUSE_EDGE.pattern + r")[ \t]*(?:(?:[a-z]+-)?snapshot|快照)"
                             r"[ \t]+carry[- ]over[ \t]*$", re.IGNORECASE)
_POOL_ACTION = r"(?:登记|放入|转入|存入|纳入|列入|存放|加入|移入|进入|推入|入)"
_POOL_DESTINATION = re.compile(_POOL_ACTION + r"\s*(?:v?\d+(?:\.\d+){1,2}\s*|" + _PAST_PERIOD + r")?$")
_CHANNEL_ACTION = re.compile(_POOL_ACTION + r"|留待|待后续")
_DISPLAY_VERB = r"(?:展示|呈现|显示)"
_DISPLAY_PREFIX = re.compile(_DISPLAY_VERB + r"$")
_DISPLAY_CHANNEL = re.compile(r"^(?:经|由)(.{1,8}?)" + _DISPLAY_VERB)
_PLANNING_RESULT = re.compile(r"^(?:规划|排期|计划)(?:已经|已)?(?:获得|形成|完成|生效)")
_INVENTORY = re.compile(r"^\s*(?:为空|(?:[0-9]{1,3}\s*项\s*)?盘点(?:去重|结果|来源|源[=＝]))")
_VISIBLE_RESULT = re.compile(r"^(?:(?:[与及和](?:推荐|任务|优先级)?(?:排序|清单|列表))|构成|成员|状态)?"
                             r"(?:一次|同时|全部|均|已|在账){0,2}(?:可见|可查|透明化)")
_MEMBERS = re.compile(r"[ \t]*([=＝])?[ \t]*[A-Z]{2,8}-[0-9]{1,6}"
                      r"(?:[/~～–-](?:[A-Z]{2,8}-)?[0-9]{1,6}){0,4}")
_MEMBER_STATUS = re.compile(r"^[ \t]*(?:[0-9一二三四五六七八九十]+(?:个)?(?:任务|条目|项))?"
                            r"(?:全部|均|都|已)[ \t]*(?:unblocked\b|就绪|可执行|完成|无阻塞)", re.IGNORECASE)
_PLAN_SOURCE = re.compile(r"(?:规划|盘点|清单|快照)[（(—–-]+$")
_UNREALIZED = re.compile(r"(?:未能|尚未|未|不再|不能|不得|禁止|并非|不是|不|没有|"
                         r"取消了?|解除了?|撤销了?|拟|计划|准备|待|将要|将|须|需|应|要)(?:立即|直接|继续)?"
                         + _OBJECT + "$")


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


def _affirmed_prefix(pattern, before):
    match = pattern.search(before)
    return match is not None and not _UNREALIZED.search(before[:match.start()])


def _pool_item_note(before, detail):
    if detail is None:
        return False
    detail = _CLAUSE_EDGE.split(detail)[0]
    if not before.strip() and _TICKET_NOTE.match(detail):
        return True
    if _REFERENCE_DETAIL.match(detail):
        return bool(_CITE.search(before) or _SOURCE_NOTE.search(before))
    settled = _SETTLED_ITEM.match(detail)
    if settled:
        # A closed parenthetical can list several completed tickets separated by semicolons.
        return _affirmed_prefix(_FINISHED_NOTE, before) or (
            not before.strip() and detail[settled.end():].startswith((")", "）")))
    return bool(_ALREADY_SETTLED.match(detail))


def _member_facts(text, end, before, window):
    # Only the structured member list consumes this extra span; free prose
    # on either side remains subject to the ordinary clause and window bounds.
    members = _MEMBERS.match(text, end, end + 4 * window)
    if not members:
        return False
    detail = _CLAUSE_EDGE.split(text[members.end():members.end() + 2 * window])[0]
    if members[1]:
        return bool(_MEMBER_STATUS.match(detail))
    return bool(_PLAN_SOURCE.search(before) and detail.lstrip().startswith(("✅", "+", "）", ")")))


def _pool_note(text, start, end, window):
    # Read at most two ordinary windows for a qualified noun or a display
    # channel. An actual entry into this pool takes precedence over its label.
    before = _CLAUSE_EDGE.split(text[max(0, start - 2 * window):start])[-1]
    after = _CLAUSE_EDGE.split(text[end:end + 2 * window])[0]
    if _POOL_DESTINATION.search(before.rstrip()):
        return False
    if (_PLANNING_RESULT.match(after) or _INVENTORY.match(after) or _VISIBLE_RESULT.match(after)
            or _DISPLAY_PREFIX.search(before.rstrip()) or _member_facts(text, end, before, window)):
        return True
    channel = _DISPLAY_CHANNEL.match(after)
    if channel and not _CHANNEL_ACTION.search(channel.group(1)):
        return True
    if _PAST_SOURCE.search(before) and _SOURCE_TITLE.match(after):
        return True
    if _SOURCE_LOCATION.search(before) and (_SOURCE_TITLE.match(after) or after.startswith(("线索", "记录"))):
        return True
    if before.endswith(("快照", "snapshot")) and after.startswith(("叙述", "原文", "记录")):
        return True
    if not after.strip() and before.rstrip().lower().endswith(("carry-over", "carry over")):
        return bool(_SNAPSHOT_LABEL.search(text, max(0, start - 4 * window), start))
    before = before[-window:].rstrip(_QUOTES_AND_SPACE)
    if _CITE.search(before) and _CITED_RECORD.match(after[:window]):
        return True
    item = _POOL_ITEM.match(text, end, end + window)
    return bool(item and _pool_item_note(before, text[item.end():item.end() + window]))


def _exempt_context(before, after, expression):
    before = _CLAUSE_EDGE.split(before)[-1]
    after = _CLAUSE_EDGE.split(after)[0]
    # A quoted action can include an object after the hit, as in 「留待复核」=违规.
    for opening, closing in _QUOTE_PAIRS:
        left, has_opening, prefix = before.rpartition(opening)
        body, has_closing, suffix = after.partition(closing)
        if has_opening and has_closing and closing not in prefix and opening not in body:
            if opening == closing and left.count(opening) % 2:
                continue
            if _RULE_JUDGEMENT.match(suffix.lstrip()):
                return True
    before = before.rstrip(_QUOTES_AND_SPACE)
    after = after.lstrip(_QUOTES_AND_SPACE)
    if _RULE_REFERENCE.match(after) or _RULE_JUDGEMENT.match(after):
        return True
    if _affirmed_prefix(_DENIAL, before):
        return True
    if "池" in expression:
        return bool(_affirmed_prefix(_POOL_EXIT, before)
                    or _POOL_RESULT.match(after)
                    or (_affirmed_prefix(_FROM_POOL, before) and _REMOVED.match(after)))
    return False


def _quoted_rule_repair(text, start, end, window):
    # Match the complete quoted expression, including overlapping ledger words.
    before = text[max(0, start - 2 * window):start]
    after = text[end:end + 2 * window]
    if not before or not after or not _RULE_CITATION.search(before[:-1]):
        return False
    return (before[-1], after[0]) in _QUOTE_PAIRS and bool(_CLOSED_GAP.match(after[1:]))


def _overlapping_spans(spans):
    """Keep every ledger hit, but resolve the shared phrase's grammatical edges."""
    index = 0
    while index < len(spans):
        first = index
        end = spans[index][1]
        index += 1
        while index < len(spans) and spans[index][0] < end:
            end = max(end, spans[index][1])
            index += 1
        yield spans[first:index], end


def scan_deferred_hits(row_text):
    """Every word-set hit on the row → tuple of hit dicts.

    Each hit: ``{"word", "start", "end", "negative_context_hit"}`` where
    ``negative_context_hit`` is True when a negation marker sits in the
    eight-character window and governs this hit. Ordinary assignments
    and unrelated neighbouring clauses leave the hit active.
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
    for group, phrase_end in _overlapping_spans(spans):
        phrase_start = group[0][0]
        phrase = text[phrase_start:phrase_end]
        note = (_quoted_rule_repair(text, phrase_start, phrase_end, window)
                or "池" in phrase and _pool_note(text, phrase_start, phrase_end, window))
        for start, end, word in group:
            before = text[max(0, start - window):phrase_start]
            after = text[phrase_end:end + window]
            hits.append({
                "word": word,
                "start": start,
                "end": end,
                "negative_context_hit": note or _exempt_context(before, after, phrase),
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
