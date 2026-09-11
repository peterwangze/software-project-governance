"""FEAT-026 Slice-2 — quick-scan 选择器 + 四态契约 + shadow 通道（FX-195 §6 L251）。

载体纪律（FX-195 §255）：本模块是 ``infra/`` 独立模块，**不 import 巨石**
``verify_workflow.py``（R2 反向依赖禁令）。quick 的选择语义完全来自 FEAT-025
注册表（``quickscan_registry``）：其排除集 ≡ FIX-270 ``_PLUGIN_PRODUCT_CHECK_IDS``
（25 段，机器对账），因此巨石侧只需**接线**（``--quick``/``--shadow`` 旗标 +
product-gate 门控 + summary 分支）即可复用引擎既有的 ``[SKIP]`` 机制，
不新增第二套选择路径、不改任何检查体（ALT-2：同一引擎的选择策略）。

零 print / 零 I/O（§4.1 R4：渲染归 L5）：本模块只**返回文本**，由巨石侧打印。

四态契约（quickscan-evaluation §2.4，机器可判定）：

* ``PASS``          — 本轮实际执行该段且 issues=0；
* ``NOT_RUN(原因)`` — 模式政策 × 注册表把该段排除出本轮 quick 面（本轮零知识）；
* ``CACHED(时间戳)``— 复用最近一次 full 裁决（Slice-3 交付；Slice-2 计数恒 0 但必现）；
* ``UNDETERMINED(原因)`` — 注册表缺声明 / 输入未知 / 观察不可信 → 回退该段或回退 full。

硬约束（§2.4 L118-122）：

1. N 只累计「执行面 + 缓存复用面」的 issues；NOT_RUN/UNDETERMINED **不得**使 N
   归零或减少——全部实质段未执行时输出 ``N=unknown`` 而非 ``0``；
2. 四态计数必现于汇总行（``summary_line_contract_violations`` 机器守卫，QR-4）；
3. ``--fail-on-issues`` 语义不变（仅 N>0 触发 exit 1；not-run 不触发也不豁免）；
4. 默认路径（无 ``--quick``）字节等价——由巨石侧原文分支保证（``test_quickscan_
   selector`` 有对照测试）。

FIX-304 消费口径（验收④）：注册表守卫抛 ``ValueError``（重复 CheckID，§4.1 R5
零容忍）或 ``CompletenessReport.fail_closed`` 为真 ⇒ **观察/注册表不可信** ⇒
全段 ``UNDETERMINED(原因)`` + 回退 full（`args.quick` 被清除，跑满 70 段）；
判别字段是 ``fail_closed``（``fallback_target`` 仅是回退目标，非本次是否回退）。

shadow 通道（§4.1，机制与 harness；「≥3 会话/≥10 commit」累计证明随使用积累）：

* **S-A 干跑 shadow**：选择集 + 逐段排除原因 + 逐段声明指纹；机器判定
  ①选择集 ∪ 排除集 = 70 段无遗漏无重复 ②每个排除段有注册表声明 + 原因代码
  ③C3 待判定段全部落表；
* **S-B 执行 shadow**：quick 实际执行选择集后同会话再跑 full，逐段比对裁决
  （同输入同码）——任何不一致 = BLOCKING（暴露隐藏输入依赖）。

声明指纹口径（Slice-2 明确边界）：本切片给的是**声明指纹**（该段 ``input_deps``
声明元组的 sha256，零 I/O、确定性）；**输入内容指纹 + 缓存键**属 Slice-3
（§6 L252），不在本切片臆造。
"""

from __future__ import annotations

import hashlib
import io
import re
from contextlib import redirect_stdout
from dataclasses import dataclass

import quickscan_registry as qr

__all__ = [
    "REASON_CENSUS_UNTRUSTED",
    "REASON_NOT_QUICK",
    "REASON_NO_SECTION",
    "REASON_POLICY_MISMATCH",
    "REASON_REGISTRY_FAULT",
    "REASON_UNEXPECTED_SKIP",
    "SEGMENT_STATE_TOKENS",
    "STATE_CACHED",
    "STATE_FAILED",
    "STATE_NOT_RUN",
    "STATE_PASSED",
    "STATE_UNDETERMINED",
    "EngineObservation",
    "QuickReport",
    "SectionObservation",
    "SegmentState",
    "Selection",
    "ShadowReport",
    "declaration_fingerprint",
    "parse_engine_sections",
    "prepare_quick_args",
    "quick_report",
    "render_quick_output",
    "report_lines",
    "select",
    "selection_contract_violations",
    "shadow_compare",
    "shadow_dry_run_lines",
    "summary_line",
    "summary_line_contract_violations",
]

# ── 四态 token（§2.4 摘出行 token：PASS / NOT_RUN(原因) / CACHED(ts) / UNDETERMINED(原因)）
STATE_PASSED = "PASS"
STATE_FAILED = "FAILED"
STATE_NOT_RUN = "NOT_RUN"
STATE_CACHED = "CACHED"
STATE_UNDETERMINED = "UNDETERMINED"

SEGMENT_STATE_TOKENS = (
    STATE_PASSED,
    STATE_FAILED,
    STATE_NOT_RUN,
    STATE_CACHED,
    STATE_UNDETERMINED,
)

# quick 输出的 issue 摘要行上限（FIX-278 G1 输出预算口径：摘要不得邀请 full 追查）
_DIGEST_CAP = 3

# UNDETERMINED 原因码（§2.4 L110：注册表缺该段声明 / 输入未知 / 观察不可信）
REASON_CENSUS_UNTRUSTED = "CENSUS_UNTRUSTED"
REASON_REGISTRY_FAULT = "REGISTRY_FAULT"
REASON_NO_SECTION = "NO_SECTION_IN_OUTPUT"
REASON_UNEXPECTED_SKIP = "UNEXPECTED_SKIP"
REASON_POLICY_MISMATCH = "POLICY_OBSERVATION_MISMATCH"
REASON_NOT_QUICK = "not-quick"  # NOT_RUN 的 token 前缀（原因码来自注册表）

_ENGINE_SUMMARY = "（引擎输出）"  # 判定依据标签：观察来自引擎捕获文本

# ── 引擎输出解析锚（与引擎同款稳定契约行；本模块不 import 引擎）────────────
_BANNER_RE = re.compile(r"┌─\s*Check\s+([0-9]+[a-z]*)\s*:")
_RESULT_RE = re.compile(r"Result:\s*ISSUES FOUND\s*[—\-–]\s*(\d+)\s*issue\(s\)")
_RESULT_PASS_RE = re.compile(r"Result:\s*PASSED\s*[—\-–]\s*0\s+issues found")
_SKIP_TOKEN = "[SKIP]"
_SKIP_ID_RE = re.compile(r"Check\s+([0-9]+[a-z]*)\b")
_ISSUE_TOKENS = ("[BLOCKING]", "[ERROR]", "[FAIL]", "[WARN]", "[ADVISORY]")

# ── §2.4 汇总行契约（机器守卫用）────────────────────────────────────────────
_QUICK_SUMMARY_RE = re.compile(
    r"^Governance: (?P<n>\d+ issues \(quick\)|N=unknown \(quick\)) \| "
    r"(?P<passed>\d+) passed / (?P<failed>\d+) failed / (?P<not_run>\d+) not-run / "
    r"(?P<cached>\d+) cache-reused / (?P<undet>\d+) undetermined \| .+$",
)
_SUMMARY_COUNT_FIELDS = ("passed", "failed", "not-run", "cache-reused", "undetermined")
SUMMARY_TAIL_ACTION = "run `check-governance` (full) for the {n} not-run segments"


@dataclass(frozen=True)
class SectionObservation:
    """One ``┌─ Check <id>: …┐`` section of the captured engine output."""

    executed: bool
    skipped: bool
    issue_tokens: tuple
    issue_lines: int

    @property
    def has_issues(self):
        return self.issue_lines > 0


@dataclass(frozen=True)
class EngineObservation:
    """Parsed engine output: the ``Result:`` count + per-check sections."""

    issues: int
    degraded: bool
    sections: dict
    issue_items: tuple

    def section(self, check_id):
        return self.sections.get(check_id)


@dataclass(frozen=True)
class SegmentState:
    """One segment's four-state verdict (§2.4)."""

    check_id: str
    state: str
    reason: str
    issues: int
    evidence: str

    @property
    def token(self):
        """§2.4 摘出行 token：``PASS`` / ``NOT_RUN(原因)`` / ``UNDETERMINED(原因)``."""
        if self.state in (STATE_NOT_RUN, STATE_UNDETERMINED, STATE_CACHED):
            return f"{self.state}({self.reason})"
        return self.state


@dataclass(frozen=True)
class Selection:
    """Quick selection: policy face + registry completeness guard verdict."""

    chosen: tuple
    not_quick: tuple
    reasons: dict
    fail_closed: bool
    undeclared: tuple
    observed: tuple
    untrusted: str

    @property
    def selected_count(self):
        return len(self.chosen)

    @property
    def not_run_count(self):
        return len(self.not_quick)

    @property
    def quick_available(self):
        """Quick may run only when the registry guard is green and no fault was seen."""
        return not self.fail_closed and not self.untrusted


@dataclass(frozen=True)
class QuickReport:
    """Four-state report over all 70 registry segments (PASS/FAILED/NOT_RUN/CACHED/UNDET)."""

    segments: tuple
    issues: int
    issues_unknown: bool
    mode: str
    notices: tuple
    violations: tuple
    digest: tuple = ()

    def count(self, state):
        return len([s for s in self.segments if s.state == state])

    @property
    def passed(self):
        return self.count(STATE_PASSED)

    @property
    def failed(self):
        return self.count(STATE_FAILED)

    @property
    def not_run(self):
        return self.count(STATE_NOT_RUN)

    @property
    def cached(self):
        return self.count(STATE_CACHED)

    @property
    def undetermined(self):
        return self.count(STATE_UNDETERMINED)

    @property
    def substantive(self):
        """Segments that yielded knowledge this run (= N's admissible base, §2.4 硬约束 1)."""
        return self.passed + self.failed + self.cached

    @property
    def ok(self):
        return not self.violations

    def lines(self):
        return report_lines(self)


@dataclass(frozen=True)
class ShadowReport:
    """S-B execution-shadow comparison: per-segment verdict equality over the chosen set."""

    compared: tuple
    mismatches: tuple
    missing_full: tuple

    @property
    def ok(self):
        return not self.mismatches and not self.missing_full

    @property
    def blocking(self):
        """§4.1 S-B: any verdict mismatch is BLOCKING (hidden input dependency)."""
        return tuple(self.mismatches)


# ── 选择（注册表消费 + 完整性守卫；FIX-304 口径映射）────────────────────────
def select(observed_ids=None, declared_ids=None):
    """Quick selection + registry completeness guard (QR-1 / §4.1 S-A ①②③).

    ``observed_ids=None`` → the registry performs its live engine census; a
    duplicate CheckID (FIX-304 F-3/G-1, §4.1 R5 零容忍) raises ``ValueError``
    and is reported as ``untrusted`` (⇒ callers MUST fall back to full).
    """
    untrusted = ""
    fail_closed = False
    undeclared = ()
    observed = ()
    try:
        guard = qr.guard_completeness(observed_ids=observed_ids, declared_ids=declared_ids)
    except ValueError as exc:  # FIX-304: duplicate census / registry fault → untrusted
        untrusted = f"{REASON_CENSUS_UNTRUSTED}: {exc}"
    else:
        fail_closed = bool(guard.fail_closed)
        undeclared = tuple(guard.undeclared)
        observed = tuple(guard.observed)
    chosen = tuple(qr.quick_face_ids())
    not_quick = tuple(qr.excluded_ids())
    reasons = {check_id: qr.exclusion_reason_code(check_id) for check_id in not_quick}
    return Selection(
        chosen=chosen,
        not_quick=not_quick,
        reasons=reasons,
        fail_closed=fail_closed,
        undeclared=undeclared,
        observed=observed,
        untrusted=untrusted,
    )


def declaration_fingerprint(check_id):
    """声明指纹 = 该段 ``input_deps`` 声明元组的 sha256（Slice-2 口径，零 I/O）。

    输入**内容**指纹与缓存键属 Slice-3（§6 L252）——本切片不臆造其语义。
    """
    spec = qr.segment(check_id)
    payload = "\x1f".join((spec.check_id, spec.domain, *spec.input_deps, *spec.modes))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def selection_contract_violations(selection):
    """S-A 机器判定（§4.1 L161 ①②③）——任一不满足即返回可读违规文本。"""
    violations = []
    chosen, not_quick = set(selection.chosen), set(selection.not_quick)
    declared = set(qr.registry_ids())
    if chosen & not_quick:
        violations.append(f"① 选择集与排除集相交：{sorted(chosen & not_quick)}")
    if chosen | not_quick != declared:
        missing = sorted(declared - (chosen | not_quick))
        extra = sorted((chosen | not_quick) - declared)
        violations.append(f"① 选择集 ∪ 排除集 ≠ 注册表全集（missing={missing} extra={extra}）")
    if len(selection.chosen) != len(list(selection.chosen)) or len(set(selection.chosen)) != len(selection.chosen):
        violations.append("① 选择集含重复段号")
    for check_id in selection.not_quick:
        code = selection.reasons.get(check_id)
        if code not in qr.EXCLUSION_REASON_CODES:
            violations.append(f"② 排除段 {check_id} 无注册表原因代码（got={code!r}）")
    for check_id in qr.C3_ADJUDICATED_SEGMENTS:
        if check_id not in declared:
            violations.append(f"③ C3 待判定段 {check_id} 未落表")
    return tuple(violations)


# ── 引擎输出解析（只解析捕获文本；不 import 引擎）──────────────────────────
def _parse_issue_count(engine_output):
    """``(N, degraded)`` from the engine's stable ``Result:`` lines (parse contract)."""
    match = _RESULT_RE.search(engine_output)
    if match:
        return int(match.group(1)), False
    if _RESULT_PASS_RE.search(engine_output):
        return 0, False
    return 0, True


def _is_skip_declaration(line):
    """True when the marker is the line's OWN leading token (``│  [SKIP] …``).

    A mere substring hit is not enough: check bodies quote ``[SKIP]`` in prose
    (e.g. an evidence line reading ``[PASS] FEAT-016 … [SKIP] …``), and treating
    such a quote as a skip declaration would falsely mark a healthy segment as
    skipped (real-run finding on Check 17, FIX-…/FEAT-026).
    """
    return line.lstrip("│ \t").startswith(_SKIP_TOKEN)


def parse_engine_sections(engine_output):
    """Parse captured engine stdout into ``EngineObservation`` (§2.4 knowledge states)."""
    issues, degraded = _parse_issue_count(engine_output)
    states = {}
    issue_items = []
    current = None
    for line in engine_output.splitlines():
        banner = _BANNER_RE.search(line)
        if banner:
            current = banner.group(1)
            if current not in states:
                states[current] = SectionObservation(
                    executed=False, skipped=False, issue_tokens=(), issue_lines=0)
            continue
        if current is None:
            continue
        if _is_skip_declaration(line):
            # A skip declaration belongs to the section that declares it: the
            # generic product-gate line belongs to the enclosing banner, while a
            # line naming a *different* Check id (e.g. 30b, which prints no
            # banner of its own) belongs to that id — attributing it to the
            # enclosing section would falsely mark a healthy segment as skipped.
            named = _SKIP_ID_RE.search(line)
            target = named.group(1) if (named and named.group(1) != current) else current
            previous = states.get(target) or SectionObservation(
                executed=False, skipped=False, issue_tokens=(), issue_lines=0)
            states[target] = SectionObservation(
                executed=previous.executed, skipped=True,
                issue_tokens=previous.issue_tokens, issue_lines=previous.issue_lines)
            continue
        matched = None
        for token in _ISSUE_TOKENS:
            idx = line.find(token)
            if idx >= 0:
                matched = (token, line[idx + len(token):].strip())
                break
        previous = states[current]
        if matched is not None:
            token, detail = matched
            states[current] = SectionObservation(
                executed=True,
                skipped=previous.skipped,
                issue_tokens=tuple(dict.fromkeys(previous.issue_tokens + (token,))),
                issue_lines=previous.issue_lines + 1,
            )
            issue_items.append((current, token, detail))
            continue
        if line.strip() and not previous.executed and not previous.skipped:
            states[current] = SectionObservation(
                executed=True, skipped=False,
                issue_tokens=previous.issue_tokens, issue_lines=previous.issue_lines)
    return EngineObservation(issues=issues, degraded=degraded, sections=states,
                             issue_items=tuple(issue_items))


# ── 四态裁决 ───────────────────────────────────────────────────────────────
def segment_states(observation, selection=None, cached_ids=()):
    """Classify every registry segment into one of the four states (§2.4)."""
    selection = select() if selection is None else selection
    cached = set(cached_ids)
    states = []
    for check_id in qr.registry_ids():
        section = observation.section(check_id)
        if check_id in cached:
            states.append(SegmentState(check_id, STATE_CACHED, "full-run-reuse",
                                       0, "cache(Slice-3)"))
            continue
        if check_id in selection.not_quick:
            code = selection.reasons.get(check_id) or "UNKNOWN"
            if section is None or section.skipped:
                states.append(SegmentState(check_id, STATE_NOT_RUN, code, 0, "registry+policy"))
            else:
                states.append(SegmentState(
                    check_id, STATE_UNDETERMINED, REASON_POLICY_MISMATCH, section.issue_lines,
                    "policy says not-quick but the engine executed it"))
            continue
        if section is None:
            states.append(SegmentState(
                check_id, STATE_UNDETERMINED, REASON_NO_SECTION, 0, "absent from engine output"))
            continue
        if section.skipped:
            states.append(SegmentState(
                check_id, STATE_UNDETERMINED, REASON_UNEXPECTED_SKIP, 0,
                "quick-face segment reported [SKIP]"))
            continue
        state = STATE_FAILED if section.has_issues else STATE_PASSED
        states.append(SegmentState(check_id, state, "", section.issue_lines, _ENGINE_SUMMARY))
    return tuple(states)


def quick_report(engine_output, cached_ids=(), selection=None, mode="quick"):
    """Build the four-state report for a captured engine run (§2.4 + QR-4 guard).

    ``mode="quick"`` → the policy face was applied; ``mode="full-fallback"`` →
    quick was requested but unavailable (untrusted registry / fail-closed guard),
    so the run was full: every segment is reported by what the engine actually
    did, and the fallback reason rides in ``notices``.
    """
    if selection is None:
        selection = select()
    if selection.untrusted or selection.fail_closed:
        if selection.untrusted:
            reason, extra = REASON_CENSUS_UNTRUSTED, selection.untrusted
        else:
            reason = qr.REASON_UNDECLARED_SEGMENT
            extra = f"undeclared={list(selection.undeclared)}" if selection.undeclared else ""
        notices = (f"[FALLBACK] quick unavailable — UNDETERMINED({reason})"
                   + (f": {extra}" if extra else "")
                   + f"; {qr.MODE_FULL_FALLBACK} run authoritative this invocation",)
        return _fallback_report(engine_output, selection, notices, reason)
    observation = parse_engine_sections(engine_output)
    segments = segment_states(observation, selection=selection, cached_ids=cached_ids)
    substantive = len([s for s in segments
                       if s.state in (STATE_PASSED, STATE_FAILED, STATE_CACHED)])
    unknown = substantive == 0 or observation.degraded
    issues = None if unknown else observation.issues
    violations = []
    if observation.degraded:
        violations.append("引擎输出缺 `Result:` 锚行（parse degraded）→ N=unknown")
    if not unknown and observation.issues < 0:
        violations.append(f"负 issues 计数: {observation.issues}")
    report = QuickReport(
        segments=segments, issues=issues, issues_unknown=unknown, mode=mode,
        notices=(), violations=tuple(violations),
        digest=_issue_digest_lines(observation),
    )
    line_violations = summary_line_contract_violations(summary_line(report))
    if line_violations:
        report = QuickReport(
            segments=segments, issues=issues, issues_unknown=unknown, mode=mode,
            notices=(), violations=tuple(violations) + line_violations,
            digest=report.digest,
        )
    return report


def _fallback_report(engine_output, selection, notices, reason):
    """Full-fallback run: report what the engine actually did + the fallback notice."""
    observation = parse_engine_sections(engine_output)
    segments = []
    for check_id in qr.registry_ids():
        section = observation.section(check_id)
        if section is None:
            segments.append(SegmentState(check_id, STATE_UNDETERMINED, reason, 0, notices[0]))
        elif section.skipped:
            segments.append(SegmentState(
                check_id, STATE_UNDETERMINED, reason, 0, "engine reported [SKIP]"))
        else:
            state = STATE_FAILED if section.has_issues else STATE_PASSED
            segments.append(SegmentState(check_id, state, "", section.issue_lines, _ENGINE_SUMMARY))
    substantive = len([s for s in segments if s.state in (STATE_PASSED, STATE_FAILED)])
    unknown = substantive == 0 or observation.degraded
    return QuickReport(
        segments=tuple(segments),
        issues=None if unknown else observation.issues,
        issues_unknown=unknown,
        mode="full-fallback",
        notices=tuple(notices),
        violations=(),
        digest=_issue_digest_lines(observation),
    )


# ── 渲染（返回文本；打印归 L5）──────────────────────────────────────────────
def summary_line(report):
    """§2.4 汇总行（四态计数必现 + 回退指引）。"""
    if report.issues_unknown:
        head = "Governance: N=unknown (quick)"
    else:
        head = f"Governance: {report.issues} issues (quick)"
    counts = (
        f"{report.passed} passed / {report.failed} failed / {report.not_run} not-run / "
        f"{report.cached} cache-reused / {report.undetermined} undetermined"
    )
    tail = SUMMARY_TAIL_ACTION.format(n=report.not_run)
    return f"{head} | {counts} | {tail}"


def summary_line_contract_violations(line):
    """机器守卫：四态计数必现（§2.4 硬约束 2；QR-4 禁「没查」报「通过」）。"""
    if not line:
        return ("汇总行为空",)
    if not _QUICK_SUMMARY_RE.match(line):
        missing = [field for field in _SUMMARY_COUNT_FIELDS if field not in line]
        return (f"汇总行不符合 §2.4 契约（缺字段={missing}）: {line!r}",)
    return ()


def report_lines(report):
    """Summary line + bounded issue digest + state-grouped disclosure (+ notices).

    Per-segment states are exposed programmatically via ``report.segments``; the
    printed form groups NOT_RUN/UNDETERMINED/FAILED by segment with their reason
    codes so the disclosure stays bounded (FIX-278 G1 output budget) while every
    non-knowledge segment stays visible by id. At most ``_DIGEST_CAP`` issue
    digest lines are printed so the quick output never invites a full-check
    chase (FIX-278 G1 caliber); the full face stays available via
    ``check-governance``.
    """
    lines = [summary_line(report)]
    lines.extend(report.digest)
    for state in (STATE_NOT_RUN, STATE_UNDETERMINED, STATE_FAILED):
        members = [s for s in report.segments if s.state == state]
        if not members:
            continue
        pairs = ", ".join(f"{s.check_id}({s.reason})" if s.reason else s.check_id
                          for s in members)
        lines.append(f"[{state}] {len(members)} segment(s): {pairs}")
    for notice in report.notices:
        lines.append(notice)
    for violation in report.violations:
        lines.append(f"[CONTRACT-VIOLATION] {violation}")
    return tuple(lines)


def _issue_digest_lines(observation, cap=_DIGEST_CAP):
    """≤cap issue detail lines, FAIL-class first then WARN (bounded output)."""
    ordered = sorted(
        observation.issue_items,
        key=lambda item: (0 if item[1] in ("[BLOCKING]", "[ERROR]", "[FAIL]") else 1),
    )
    return tuple(f"{token} Check {check_id}: {detail}" if detail
                 else f"{token} Check {check_id}"
                 for check_id, token, detail in ordered[:cap])


# ── shadow 通道（S-A / S-B，§4.1）──────────────────────────────────────────
def shadow_dry_run_lines(selection):
    """S-A dry-run shadow: selection + per-segment exclusion reason + declaration指纹."""
    lines = [
        f"[S-A] dry-run shadow — chosen={selection.selected_count} "
        f"not-run={selection.not_run_count} "
        f"union={selection.selected_count + selection.not_run_count} "
        f"(registry={len(qr.registry_ids())})",
        "[S-A] chosen: " + ", ".join(selection.chosen),
    ]
    if selection.not_quick:
        lines.append("[S-A] not-run: " + ", ".join(
            f"{check_id}({selection.reasons.get(check_id)})" for check_id in selection.not_quick))
    lines.append("[S-A] fingerprints: " + ", ".join(
        f"{check_id}:{declaration_fingerprint(check_id)}" for check_id in selection.chosen[:5]) + " …")
    for violation in selection_contract_violations(selection):
        lines.append(f"[S-A-VIOLATION] {violation}")
    return tuple(lines)


def shadow_compare(quick_output, full_output, chosen_ids):
    """S-B execution shadow: per-segment verdict equality (§4.1 L162).

    Compares the quick execution's per-segment issue count against the full
    run's for the SAME segment ids; any mismatch or missing observation is
    BLOCKING (a hidden input dependency by definition).
    """
    quick = parse_engine_sections(quick_output)
    full = parse_engine_sections(full_output)
    compared, mismatches, missing = [], [], []
    for check_id in chosen_ids:
        q_section = quick.section(check_id)
        f_section = full.section(check_id)
        if q_section is None or f_section is None:
            missing.append(check_id)
            continue
        compared.append(check_id)
        if q_section.issue_lines != f_section.issue_lines or (
                set(q_section.issue_tokens) != set(f_section.issue_tokens)):
            mismatches.append(
                f"{check_id}: quick={q_section.issue_lines} issue(s)"
                f"{list(q_section.issue_tokens)} vs full={f_section.issue_lines} issue(s)"
                f"{list(f_section.issue_tokens)}")
    return ShadowReport(compared=tuple(compared), mismatches=tuple(mismatches),
                        missing_full=tuple(missing))


def shadow_lines(shadow):
    """S-B report lines (§4.1 L162 — 不一致 = BLOCKING)。"""
    lines = [
        f"[S-B] execution shadow — compared={len(shadow.compared)} segment(s) "
        f"mismatches={len(shadow.mismatches)}",
    ]
    if shadow.missing_full:
        lines.append(f"[S-B][BLOCKING] segment(s) without a full-run observation: "
                     f"{list(shadow.missing_full)}")
    for item in shadow.mismatches:
        lines.append(f"[S-B][BLOCKING] quick verdict ≠ full verdict — {item}")
    if shadow.ok:
        lines.append("[S-B] 选择集裁决 == full 裁决（零意外差异，本会话）")
    return tuple(lines)


# ── 巨石接线入口（wiring；选择/渲染逻辑均在本模块）──────────────────────────
def prepare_quick_args(args):
    """Wiring pre-flight: mark the quick request, fail closed to full when untrusted.

    Returns a notice text (``""`` when quick stays enabled). §2.4 + FIX-304: an
    untrusted observation (duplicate CheckID ``ValueError``) or a fail-closed
    registry guard ⇒ quick is disabled for this invocation and the engine runs
    the full face instead.
    """
    requested = bool(getattr(args, "quick", False) or getattr(args, "shadow", False))
    setattr(args, "quick_requested", requested)
    if not requested:
        return ""
    selection = select()
    if selection.untrusted:
        reason, detail = REASON_CENSUS_UNTRUSTED, selection.untrusted
    elif selection.fail_closed:
        reason = qr.REASON_UNDECLARED_SEGMENT
        detail = f"undeclared={list(selection.undeclared)}" if selection.undeclared else ""
    else:
        return ""
    setattr(args, "quick", False)
    setattr(args, "shadow", False)
    return (f"[FALLBACK] quick unavailable — UNDETERMINED({reason})"
            + (f": {detail}" if detail else "")
            + f"; running {qr.MODE_FULL_FALLBACK} (registry/observation untrusted)\n")


def render_quick_output(captured, args, engine_runner=None):
    """Render the ``--quick`` output text (four-state line + disclosure [+ shadow]).

    Called by the engine's dispatch wiring with its own captured stdout; the
    full pass for ``--shadow`` is delegated back through ``engine_runner`` so
    this module never imports the monolith (R2).
    """
    requested = bool(getattr(args, "quick_requested", False))
    mode = "quick" if requested else "full"
    out = []
    if mode == "quick":
        report = quick_report(captured)
        out.extend(report.lines())
        if bool(getattr(args, "shadow", False)) and engine_runner is not None:
            full_issues, full_text = _capture_full_run(args, engine_runner)
            selection = select()
            out.extend(shadow_dry_run_lines(selection))
            out.extend(shadow_lines(shadow_compare(captured, full_text, selection.chosen)))
            out.append(f"Governance: {full_issues} issues (full, shadow baseline — "
                       f"authoritative for this invocation)")
        return "\n".join(out) + "\n"
    report = quick_report(captured, mode="full")
    out.extend(report.lines())
    return "\n".join(out) + "\n"


def _capture_full_run(args, engine_runner):
    """Run the engine full face (``quick``/``shadow`` cleared) and capture stdout."""
    previous = (getattr(args, "quick", False), getattr(args, "shadow", False))
    buf = io.StringIO()
    try:
        setattr(args, "quick", False)
        setattr(args, "shadow", False)
        with redirect_stdout(buf):
            issues = engine_runner(args)
    finally:
        setattr(args, "quick", previous[0])
        setattr(args, "shadow", previous[1])
    return issues, buf.getvalue()
