"""Evidence ledger checks, structured provenance, and goal-contract readiness."""

import re
import json
from datetime import date, datetime
from pathlib import Path

GOVERNANCE_CONTEXT_EVIDENCE_UNFINISHED_MARKERS = (
    "进行中",
    "未完成",
    "carry-over",
    "next action",
    "resume",
    "阻塞",
    "blocked",
    "待确认",
    "待处理",
    "待启动",
    "pending",
    "in progress",
)

GOVERNANCE_CONTEXT_EVIDENCE_CLOSED_MARKERS = (
    "已完成",
    "完成",
    "闭环",
    "已关闭",
    "关闭",
    "approved",
    "closed",
    "resolved",
)

GOVERNANCE_CONTEXT_EVIDENCE_TASK_HEADERS = (
    "对应任务",
    "任务id",
    "任务 id",
    "关联任务",
    "task id",
)

GOVERNANCE_CONTEXT_EVIDENCE_STATE_HEADERS = (
    "状态",
    "备注",
    "证据类型",
    "status",
    "note",
    "remark",
    "type",
)


def _governance_directory():
    from resolve_entry import current_host_root
    return Path(current_host_root()) / ".governance"


def _task_reference_source():
    from governance_archive_data import expand_task_ids
    return _governance_directory() / "evidence-log.md", expand_task_ids


def _evidence_archive_reader():
    from governance_archive_data import GovernanceDataSource
    return GovernanceDataSource(_governance_directory())


def _context_projection():
    from plan_task_selection import _governance_table_cells, _normalize_priority
    from project_context import _context_task, _extract_task_title_from_line
    from resolve_entry import package_context_file
    return (package_context_file, _context_task, _extract_task_title_from_line,
            _governance_table_cells, _normalize_priority, GOVERNANCE_CONTEXT_EVIDENCE_TASK_HEADERS)


def _state_headers():
    return GOVERNANCE_CONTEXT_EVIDENCE_STATE_HEADERS


def _closed_markers():
    return GOVERNANCE_CONTEXT_EVIDENCE_CLOSED_MARKERS


def _unfinished_markers():
    return GOVERNANCE_CONTEXT_EVIDENCE_UNFINISHED_MARKERS


FACT_BASIS_RE = re.compile(
    r'事实依据[:：]\s*(.+?)(?:\s*(?:目标对齐[:：]|用户影响[:：]|范围[:：]|依赖[:：]|架构影响[:：]|$))'
)

UNGROUNDED_CLAIM_RE = re.compile(
    r"(?:我\s*)?(?:假设|猜测|推测|估计)|(?:大概|应该|可能)(?:已经|是|可以|完成|存在)|编造|幻觉"
)


def _grounding_inputs():
    from plan_impact import release_impact_entries_for
    return (lambda: release_impact_entries_for(_governance_directory(), requires_impact_evidence),
            FACT_BASIS_RE, UNGROUNDED_CLAIM_RE)


def _structured_inputs():
    from plan_impact import release_impact_entries_for
    from write_guard_records import _row_has_governance_store_machine_credential
    return (lambda: release_impact_entries_for(_governance_directory(), requires_impact_evidence),
            _row_has_governance_store_machine_credential)


def _goal_inputs():
    from delivery_contract_checks import validate_default_product_success_contract
    from execution_packet_checks import _load_execution_packets
    from plan_status import _status_is_completed_cell
    from plan_task_selection import _active_execution_packet_tasks, parse_current_active_tasks

    directory = _governance_directory()

    def active_tasks():
        return _active_execution_packet_tasks(status_is_completed_cell=_status_is_completed_cell,
                                              parse_current_active_tasks=lambda: parse_current_active_tasks(
                                                  plan_path=directory / "plan-tracker.md"))

    def load_packets(path):
        return _load_execution_packets(path, packet_path_now=lambda: directory / "execution-packets.json")

    return directory, active_tasks, load_packets, validate_default_product_success_contract


def _resolve_shared():
    """Expose the current shared contract validator for the historical explicit hook."""
    global _validate_product_success_contract
    _, _, _, _validate_product_success_contract = _goal_inputs()


def _evidence_header_index(header, header_markers):
    for idx, cell in enumerate(header or []):
        normalized = re.sub(r"\s+", " ", cell.strip().lower())
        compact = normalized.replace(" ", "")
        for marker in header_markers:
            marker_lower = marker.lower()
            marker_compact = marker_lower.replace(" ", "")
            if marker_lower in normalized or marker_compact in compact:
                return idx
    return None


def _extract_evidence_task_id(task_cell):
    task_ids = re.findall(r"\b([A-Z]+-\d+)\b", task_cell or "")
    for task_id in task_ids:
        if not task_id.startswith("EVD-"):
            return task_id
    return None


def _evidence_state_cells(cells, header):
    state_headers = _state_headers()
    state_indices = []
    if header:
        for idx, cell in enumerate(header):
            normalized = re.sub(r"\s+", " ", cell.strip().lower())
            compact = normalized.replace(" ", "")
            if any(
                marker.lower() in normalized or marker.lower().replace(" ", "") in compact
                for marker in state_headers
            ):
                state_indices.append(idx)
    else:
        # Canonical evidence rows are:
        # 编号 | 对应任务 ID | 阶段 | 证据类型 | ... | 关联 Gate | 备注
        state_indices.extend(idx for idx in (3, 9, 10) if idx < len(cells))
    return [cells[idx] for idx in state_indices if idx < len(cells)]


def _is_closed_evidence_state(text):
    closed_markers = _closed_markers()
    lowered = (text or "").lower()
    if "未完成" in lowered:
        return False
    return any(marker in lowered for marker in closed_markers)


def _is_active_evidence_state(text):
    unfinished_markers = _unfinished_markers()
    lowered = (text or "").lower()
    return any(marker.lower() in lowered for marker in unfinished_markers)


def _parse_evidence_context_tasks(root):
    (context_file, context_task, task_title, table_cells, normalize_priority, task_headers) = _context_projection()
    evidence_path = context_file(root, ".governance/evidence-log.md")
    if not evidence_path.is_file():
        return []
    tasks = []
    header = []
    for line in evidence_path.read_text(encoding="utf-8").split("\n"):
        stripped = line.strip()
        if not stripped or "---" in stripped:
            continue
        if not stripped.startswith("|"):
            continue
        cells = table_cells(stripped)
        if not cells:
            continue
        if cells[0] in {"编号", "Evidence ID"} or any("对应任务" in cell or "Task ID" in cell for cell in cells):
            header = cells
            continue
        task_idx = _evidence_header_index(header, task_headers)
        if task_idx is None and len(cells) > 1 and re.match(r"^EVD-\d+\b", cells[0]):
            task_idx = 1
        if task_idx is None or task_idx >= len(cells):
            continue
        task_id = _extract_evidence_task_id(cells[task_idx])
        if not task_id:
            continue
        state_cells = _evidence_state_cells(cells, header)
        state_text = " | ".join(state_cells)
        if any(_is_closed_evidence_state(cell) for cell in state_cells):
            continue
        if not any(_is_active_evidence_state(cell) for cell in state_cells):
            continue
        lowered = state_text.lower()
        status = "unfinished evidence fact"
        if any(marker in lowered for marker in ("阻塞", "blocked", "待确认")):
            status = "blocked evidence fact"
        elif any(marker in lowered for marker in ("carry-over", "resume", "next action")):
            status = "carry-over evidence fact"
        tasks.append(context_task(
            task_id,
            task_title(stripped, task_id),
            status,
            ".governance/evidence-log.md",
            stripped,
            priority=normalize_priority(stripped),
        ))
    return tasks


def parse_evidence_task_ids():
    """Return set of task IDs that have evidence entries (range-expanded)."""
    evidence_path, expand_task_ids = _task_reference_source()
    content = evidence_path.read_text(encoding="utf-8")
    task_ids = set()
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            raw_ids = parts[2]
            if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids):
                task_ids |= expand_task_ids(raw_ids)
    return task_ids


def parse_evidence_task_map():
    """Return dict mapping task_id -> list of evidence IDs (range-expanded)."""
    evidence_path, expand_task_ids = _task_reference_source()
    content = evidence_path.read_text(encoding="utf-8")
    task_map = {}
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            evd_id = parts[1]
            raw_ids = parts[2]
            if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids):
                for task_id in expand_task_ids(raw_ids):
                    task_map.setdefault(task_id, []).append(evd_id)
    return task_map


def _hot_task_shape_warnings(sample_path):
    """FIX-480 fail-closed: task-like rows NO supported header shape
    recognizes must WARN (NOT_RUN), never a silent 0-completed PASS.

    A "task-like row" is a table row carrying a bare ``PREFIX-NNN`` cell
    whose prefix is NOT a cross-entity record (RISK/DEC/REVIEW/EVD/…, by
    identity from task_priority's ``_CROSS_ENTITY_PREFIXES`` — never
    restated) and not ``REQ`` (the requirement matrix is not a task table;
    same ruling as the commit-msg FIX-282 P2-1 tightening). An unknown
    host prefix DOES count — an upgrade-path task table must not silently
    degrade back to the false PASS. The parse itself goes through the
    single source (``task_priority.parse_task_dependencies``); a tracker
    whose task-like rows ALL parse needs no warning (a TRUE 0 stays a
    PASS).
    """
    warnings = []
    path = Path(sample_path)
    if not path.is_file():
        return warnings
    content = path.read_text(encoding="utf-8")
    try:
        from task_priority import (  # noqa: WPS433 (deferred, mirrors verify_workflow's TPA call style)
            _CROSS_ENTITY_PREFIXES,
            parse_task_dependencies,
        )
        parsed = parse_task_dependencies(content)
    except Exception as exc:  # unreadable/unparsable — surface, never hide
        return ["task_table_parse_failed: {0}: {1}".format(
            type(exc).__name__, exc)]
    if parsed:
        return warnings
    task_like = 0
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        for cell in stripped.strip("|").split("|"):
            m = re.match(r"^([A-Z]+)-\d+$", cell.strip().strip("*"))
            if (m and m.group(1) not in _CROSS_ENTITY_PREFIXES
                    and m.group(1) != "REQ"):
                task_like += 1
                break
    if task_like:
        warnings.append(
            "task_table_shape_unrecognized: {0} task-like row(s) present "
            "but 0 parsed — supported shapes: 0.99 compact "
            "「| 优先级 | ID | … |」 and 0.54 id-first "
            "「| ID | … | 状态 | 优先级 | … |」; the completed-count face "
            "is NOT_RUN (fail-closed), not PASS".format(task_like))
    return warnings


def check_evidence_completeness():
    """Check that every completed task has at least one evidence entry.

    Uses GovernanceDataSource to transparently aggregate hot files + archive
    files. Falls back to single-file mode when archive/ directory does not
    exist (backward compatible).

    FIX-480: returns ``completed_ids`` (the counted IDs — the four consumer
    faces share one parse source) and ``parse_warnings`` — when the hot
    plan-tracker carries task-like rows that no supported header shape
    recognizes, the completed-count face is NOT_RUN and the warning says so
    (the python_game 0.54-era host previously got a silent
    ``Completed tasks: 0`` PASS for 34 completed tasks).
    """
    ds = _evidence_archive_reader()
    completed_entries = ds.get_all_completed_task_entries()
    completed = {entry["id"] for entry in completed_entries}
    evidenced = ds.get_all_evidence_task_ids()
    missing = completed - evidenced
    hot_completed = {
        entry["id"] for entry in completed_entries
        if entry.get("source") == "hot"
    }
    current_missing = missing & hot_completed
    historical_missing = missing - current_missing
    matched = completed & evidenced
    return {
        "completed_count": len(completed),
        "completed_ids": sorted(completed),
        "evidenced_count": len(matched),
        "missing_evidence": sorted(current_missing),
        "historical_missing_evidence": sorted(historical_missing),
        "parse_warnings": _hot_task_shape_warnings(
            getattr(ds, "sample_path", None)),
    }


def check_evidence_quality():
    """Check evidence quality: session context references, circular refs, empty output claims."""
    governance_dir = _governance_directory()
    evidence_path = governance_dir / "evidence-log.md"
    issues = {
        "session_context": [],      # 会话上下文 references
        "circular_refs": [],        # 循环引用
        "empty_output": [],         # 空输出声明
    }

    if not evidence_path.is_file():
        return issues

    content = evidence_path.read_text(encoding="utf-8")
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        # Skip header rows and separator rows
        if not line.startswith("| EVD-"):
            continue

        parts = line.split("|")
        if len(parts) < 8:
            continue

        evd_id = parts[1].strip()
        evidence_location = parts[6].strip() if len(parts) > 6 else ""

        # Check 1: 会话上下文 references (non-persistent)
        if "会话上下文" in evidence_location:
            issues["session_context"].append(f"{evd_id} (line {i}): evidence location = '{evidence_location}'")

        # Check 2: Circular references — evidence referencing itself
        if f"详见 {evd_id}" in line or f"see {evd_id}" in line.lower():
            issues["circular_refs"].append(f"{evd_id} (line {i}): self-referencing — '{evd_id}' in content")

        # Check 3: Empty or placeholder output claims
        if evidence_location in ("待补", "会话上下文", "详见 EVD-070 完整内容", ""):
            if evidence_location == "":
                issues["empty_output"].append(f"{evd_id} (line {i}): empty evidence location")
            elif evidence_location == "待补":
                issues["empty_output"].append(f"{evd_id} (line {i}): evidence location = '待补'")
            elif evidence_location.startswith("详见 EVD-"):
                pass  # Already caught by Check 2

    return issues


def emit_evidence_completeness(result):
    """Print Check 1 findings and count current gaps and parse warnings."""
    issue_count = 0
    print(f"│  Completed tasks: {result['completed_count']}")
    # FIX-480 fail-closed: an unrecognized task-table shape makes the
    # completed-count face NOT_RUN — WARN, never a silent 0-completed PASS.
    for _shape_warn in result.get("parse_warnings", []):
        issue_count += 1
        print(f"│  [WARN] {_shape_warn}")
    print(f"│  Tasks with evidence: {result['evidenced_count']}")
    missing = result["missing_evidence"]
    if missing:
        issue_count += len(missing)
        print(f"│  [WARN] {len(missing)} completed task(s) without evidence:")
        for tid in missing:
            print(f"│    - {tid}")
    else:
        print(f"│  [PASS] All completed tasks have evidence entries.")
    historical_missing = result.get("historical_missing_evidence", [])
    if historical_missing:
        print(f"│  [INFO] {len(historical_missing)} archived completed task(s) without hot evidence "
              f"(historical residue):")
        for tid in historical_missing[:10]:
            print(f"│    - {tid}")
        if len(historical_missing) > 10:
            print(f"│    ... and {len(historical_missing) - 10} more")
    return issue_count


def emit_evidence_quality(result):
    """Print Check 4 reference findings and return their issue count."""
    issue_count = 0
    if result["session_context"]:
        issue_count += len(result["session_context"])
        print(f"│  [WARN] {len(result['session_context'])} evidence with '会话上下文' reference:")
        for item in result["session_context"]:
            print(f"│    - {item}")
    else:
        print(f"│  [PASS] No '会话上下文' references found.")
    if result["circular_refs"]:
        issue_count += len(result["circular_refs"])
        print(f"│  [WARN] {len(result['circular_refs'])} circular reference(s):")
        for item in result["circular_refs"]:
            print(f"│    - {item}")
    else:
        print(f"│  [PASS] No circular references found.")
    if result["empty_output"]:
        issue_count += len(result["empty_output"])
        print(f"│  [WARN] {len(result['empty_output'])} empty/incomplete evidence location(s):")
        for item in result["empty_output"]:
            print(f"│    - {item}")
    else:
        print(f"│  [PASS] No empty evidence locations found.")
    return issue_count


def check_fact_grounding():
    """FIX-080: Check current product-code evidence is grounded in facts.

    FIX-390 (DEC-241 消解): the fact judgment reads the structured basis
    column (parts[5]) as the fallback surface. The DEC-168 machine
    row-family contract (``governance_store._build_evidence_row``) lands the
    fact basis in that independent column, so contract-compliant machine rows
    no longer false-FAIL on a description-only read (live: EVD-1140/EVD-1164,
    the DEC-241 2×2 exception face). The description column keeps priority —
    hand-era rows are judged exactly as before (向后兼容).

    The ungrounded-claim scan covers BOTH surfaces: whatever text carries
    the fact basis is held to the same grounding standard (不误放行).
    """
    current_entries, fact_basis, ungrounded_claim = _grounding_inputs()
    result = {
        "entries": [],
        "pass": True,
    }

    for entry in current_entries():
        desc = entry["description"]
        basis_text = entry.get("fact_basis", "")
        fact_match = fact_basis.search(desc)
        fact_source = "description"
        if fact_match is None and basis_text:
            fact_match = fact_basis.search(basis_text)
            fact_source = "basis-column"
        fact_text = fact_match.group(1).strip() if fact_match else ""
        fact_len = len(fact_text)
        issues = []
        status = "PASS"

        if not fact_text:
            issues.append("缺少 事实依据: 字段")
            status = "FAIL"
            result["pass"] = False
        elif fact_len < 20:
            issues.append("事实依据: 过短，需指向具体文件/命令/日志/测试输出")
            status = "FAIL"
            result["pass"] = False

        speculative_match = ungrounded_claim.search(desc)
        if speculative_match is None and basis_text:
            speculative_match = ungrounded_claim.search(basis_text)
        if speculative_match:
            issues.append(f"含未落地推断词: {speculative_match.group(0)}")
            status = "FAIL"
            result["pass"] = False

        result["entries"].append({
            "task_id": entry["task_id"],
            "evd_id": entry["evd_id"],
            "has_fact_basis": bool(fact_text),
            "fact_len": fact_len,
            "fact_text": fact_text[:80] + ("..." if fact_len > 80 else ""),
            "fact_source": fact_source,
            "status": status,
            "issues": issues,
        })

    return result


def _is_product_code_location(file_location):
    from checks.review_domain import PRODUCT_CODE_PATTERNS
    return any(pattern in file_location for pattern in PRODUCT_CODE_PATTERNS)


def _is_review_evidence(raw_ids, evd_type):
    return (
        raw_ids.startswith("REVIEW-")
        or evd_type in ("Code Review", "代码审查", "审查")
        or "审查" in evd_type
    )


# FEAT-104: forensic (investigation-only) evidence markers — anchored at the
# head of the evd_type field ONLY (explicit "[取证]"/"[forensics]"/"取证:"
# tags, or 取证/调查/诊断/对账/复盘 followed by a delimiter, a report/minutes
# suffix word, or end-of-field). Mid-prose matches are deliberately NOT
# forensic: free-text guessing must not hide implementation rows from review
# debt ("修复并附调查记录" / "诊断脚本实现" stay implementation).
_FORENSIC_HEAD_RE = re.compile(
    r"(?:\[(?:取证|forensics)\]|(?:取证|forensics)\s*[:：]"
    r"|(?:取证|调查|诊断|对账|复盘)"
    r"(?=$|[\s：:、，,）)】\]—\-]|报告|会议|纪要|记录))",
    re.IGNORECASE,
)


def _is_audit_or_review_type(evd_type):
    """Non-implementation evidence: audit/review rows (FIX-174) plus forensic
    investigation-only rows (FEAT-104) never constitute execution evidence
    for review-debt / review-coverage judgments (activity ≠ delivery)."""
    return (any(token in evd_type for token in ("审查", "审视", "审计", "Review"))
            or bool(evd_type and _FORENSIC_HEAD_RE.match(evd_type.strip())))


def requires_impact_evidence(task_id, evd_type, file_location, *, active=True):
    """Impact and product delivery receipts share Check 18b; research has its own evidence."""
    if evd_type == "影响分析":
        return True
    product = evd_type in {"产品代码", "实现", "修复", "修复闭环", "开发", "代码"} or _is_product_code_location(file_location)
    return active and product and not _is_review_evidence(task_id, evd_type) and not _is_audit_or_review_type(evd_type)


SECRET_FIELD_RE = re.compile(r"(?:api[_-]?key|token|secret|password|passwd)", re.IGNORECASE)
SECRET_ASSIGNMENT_RE = re.compile(
    r"['\"]?(?:api[_-]?key|token|secret|password|passwd)['\"]?\s*[:=]\s*['\"]?[^\s,'\"}]+",
    re.IGNORECASE,
)


_STRUCTURED_FACT_MARKER = re.compile(r"结构化事实[:：][\s`]*")


def read_structured_fact(text):
    """Locate and decode a marked object, skipping prose labels before a real payload."""
    fallback = (None, None, None)
    for marker in _STRUCTURED_FACT_MARKER.finditer(text):
        start = marker.end()
        if not text.startswith("{", start):
            if fallback[0] is None:
                fallback = (slice(start, len(text)), None, "结构化事实必须是 JSON object")
            continue
        try:
            payload, size = json.JSONDecoder().raw_decode(text[start:])
        except ValueError as exc:
            return slice(start, len(text)), None, f"结构化事实 JSON 解析失败: {exc}"
        return slice(start, start + size), payload, None
    return fallback


def _extract_structured_fact_json(description):
    span, _, _ = read_structured_fact(description)
    return description[span].strip() if span is not None else ""


def structured_fact_result(description, basis, *, machine_attested):
    """Only rows without a declared JSON payload can use the machine receipt alone."""
    for field in (description, basis):
        span, payload, error = read_structured_fact(field)
        if span is not None:
            issues = [error] if error else _validate_structured_fact_payload(payload)
            return True, payload, issues
    return False, None, [] if machine_attested else ["缺少 结构化事实: JSON"]


def _contains_secret_like(value):
    """Return True when structured evidence appears to carry a raw secret."""
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if SECRET_FIELD_RE.search(key_text):
                if child not in (None, "", "<redacted>", "REDACTED", "***", "***REDACTED***"):
                    return True
            if _contains_secret_like(child):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_secret_like(item) for item in value)
    if isinstance(value, str):
        return bool(SECRET_ASSIGNMENT_RE.search(value))
    return False


def _validate_structured_fact_payload(payload):
    issues = []
    if not isinstance(payload, dict):
        return ["结构化事实必须是 JSON object"]

    commands = payload.get("commands")
    if not isinstance(commands, list) or not commands:
        issues.append("commands 必须是非空数组")
    else:
        for index, command in enumerate(commands, start=1):
            if not isinstance(command, dict):
                issues.append(f"commands[{index}] 必须是 object")
                continue
            cmd = command.get("cmd")
            exit_code = command.get("exit_code")
            summary = command.get("summary")
            if not isinstance(cmd, str) or not cmd.strip():
                issues.append(f"commands[{index}].cmd 必须是非空字符串")
            if type(exit_code) is not int:
                issues.append(f"commands[{index}].exit_code 必须是整数")
            if not isinstance(summary, str) or len(summary.strip()) < 5:
                issues.append(f"commands[{index}].summary 必须说明输出摘要")
            log_path = command.get("log_path")
            if log_path is not None and not isinstance(log_path, str):
                issues.append(f"commands[{index}].log_path 必须是字符串")

    files_changed = payload.get("files_changed")
    if not isinstance(files_changed, list) or not files_changed or not all(isinstance(item, str) and item for item in files_changed):
        issues.append("files_changed 必须是非空字符串数组")

    diff_summary = payload.get("diff_summary")
    if not isinstance(diff_summary, str) or len(diff_summary.strip()) < 10:
        issues.append("diff_summary 必须说明文件 diff 摘要")

    review = payload.get("review")
    if not isinstance(review, dict):
        issues.append("review 必须是 object")
    else:
        from checks.review_domain import _normalize_review_conclusion

        applicability = review.get("applicability")
        conclusion = review.get("conclusion")
        if applicability == "NOT_REQUIRED":
            if conclusion is not None:
                issues.append("不适用审查只声明 applicability，不同时声明结论")
            reason = review.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                issues.append("review.reason 必须说明不适用原因")
        else:
            if applicability not in (None, "REQUIRED"):
                issues.append("review.applicability 必须是 REQUIRED 或 NOT_REQUIRED")
            # Historical receipts used NOT_REQUIRED as the conclusion.
            legacy_not_required = applicability is None and conclusion == "NOT_REQUIRED"
            if not _normalize_review_conclusion(conclusion) and not legacy_not_required:
                issues.append("review.conclusion 必须是正式审查状态或历史 NOT_REQUIRED")
            reviewer = review.get("reviewer")
            if not isinstance(reviewer, str) or not reviewer.strip():
                issues.append("review.reviewer 必须是非空字符串")

    if _contains_secret_like(payload):
        issues.append("结构化事实疑似包含 secret/token/password 明文")
    return issues


def check_structured_evidence():
    """FIX-083: Check current product-code evidence has machine-readable facts.

    FIX-390 (DEC-241 消解): a DEC-168 machine row-family row carries its
    structured provenance in the writer's own credential marker
    (``机器写入：governance-store evidence-append op-<32hex>`` — the ops
    receipt whose operation_id/fingerprint live in the ops ledger, policed
    by governance-write-guard faces 2/5). When no structured-fact JSON is
    present, that credential attests the row instead — contract-compliant
    machine rows no longer false-FAIL (live: EVD-1140/EVD-1164). The JSON
    path keeps priority and full payload validation; a malformed op id or a
    foreign writer's marker never attests, and hand-written rows without
    either keep the strict FAIL (向后兼容；未知不猜).
    """
    current_entries, has_machine_credential = _structured_inputs()
    result = {
        "entries": [],
        "pass": True,
    }

    for entry in current_entries():
        desc = entry["description"]
        basis_text = entry.get("fact_basis", "")
        credential = has_machine_credential(entry.get("raw_line", ""))
        has_fact, payload, issues = structured_fact_result(desc, basis_text, machine_attested=credential)
        status = "PASS"

        if issues:
            status = "FAIL"
            result["pass"] = False

        result["entries"].append({
            "task_id": entry["task_id"],
            "evd_id": entry["evd_id"],
            "has_structured_fact": has_fact,
            "machine_attested": credential and not has_fact,
            "status": status,
            "issues": issues,
            "commands": len(payload.get("commands", [])) if isinstance(payload, dict) and isinstance(payload.get("commands"), list) else 0,
            "files_changed": len(payload.get("files_changed", [])) if isinstance(payload, dict) and isinstance(payload.get("files_changed"), list) else 0,
        })

    return result


# ═══════════════════════════════════════════════════════════════════════════
# ADR-RB-2 goal-layer contract gate (FEAT-069 — ADR-019 §6 step 4 precursor)
# ═══════════════════════════════════════════════════════════════════════════
# The two RB-2 residual faces (ADR-019 §4 RB-2 mitigation; hand-over recorded
# in docs/verification/loop-migration-fullchain-0.90.0.md §6.2):
#   ① host-activation precondition — at least one unit's
#     product_success_contract is NOT a TO_BE_DEFINED placeholder and is
#     traceable to the plan-tracker goal face;
#   ② sensitive-action gate — contract missing → WARN; sensitive action
#     (release/flip family) → BLOCK judge.
#
# Factory form (B-12/B-13 precedent: 机制先行 + 出厂 WARN + 翻转留授权票):
# both faces ship WARN-grade. The BLOCK verdict is COMPUTED and observable
# but NOT enforced until RB2_SENSITIVE_BLOCK_ENFORCED is flipped by the
# family authorization ticket (ADR-019 §6 step 4: 每票执行 §2.4 权威署名
# 切换；真阻断属授权票域). The goal faces live in this domain module; the
# engine only wires the render call (God Module budget discipline, Check 3b
# precedent).
#
# FIX-431 — 发布间隙态改判 N/A: 「无活跃 P0/P1 unit」（任务表全完成）的
# 间隙态无判定对象/无判定语境——face① 激活前置与 face② demo actions 均判
# N/A（不发 WARN）。契约缺失 WARN（含 goal_face 追溯面）只在有活跃 unit 的
# 运行期才有意义；有活跃 unit 的现行为判定链（PASS/WARN/BLOCK）与
# enforcement 翻转机制（出厂 False，B-12/B-13 授权票域）零变化。间隙态
# 下 execution packets 不可读的评估完整性 WARN 仍保留（异常不隐藏）。

# Activation switch — factory OFF. Flip to True ONLY via the family
# authorization ticket (ADR-019 §4 RB-2 / §6 step 4; B-12/B-13 precedent).
# Callers that flip it MUST treat judge verdict "BLOCK" as an abort of the
# sensitive action.
RB2_SENSITIVE_BLOCK_ENFORCED = False

# Sensitive action family (ADR-019 §2.6: 发布/外部副作用/授权翻转 — this gate
# covers the release/flip family). Matched against the action label.
RB2_SENSITIVE_ACTION_RE = re.compile(
    r"(?:\brelease\b|\bpublish\b|\bdeploy\b|\bflip\b|发布|上线|部署|翻转|"
    r"授权票|authorization[ -]ticket|registry[ -]flip)",
    re.IGNORECASE,
)

# plan-tracker goal-face markers — the goal-layer authority face a packet
# contract must trace to (ADR-019 §2.2: 目标层 = plan-tracker 成功标准 +
# execution packet product_success_contract). Any-of match; host trackers may
# use any of these headings.
RB2_PLAN_TRACKER_GOAL_FACE_MARKERS = (
    "## 项目总览",
    "## 成功标准",
    "## 项目目标",
)

# Demo action labels the renderer judges so both gate verdicts are
# observable on every Check 18d run (正负例: sensitive vs non-sensitive
# against the REAL host contract readiness).
_RB2_DEMO_SENSITIVE_ACTION = "release 0.90.0 (发布)"
_RB2_DEMO_NONSENSITIVE_ACTION = "check-governance"


def check_goal_layer_contract_readiness(packet_path=None):
    """ADR-RB-2 face ① — host-activation precondition (FEAT-069).

    Mitigation clause (ADR-019 §4 RB-2): host activation requires at least
    one unit whose ``product_success_contract`` is not a ``TO_BE_DEFINED``
    placeholder and is traceable to the plan-tracker goal face. The contract
    half reuses the Check 18d validator by identity; the traceability half
    reads the goal face from ``<GOVERNANCE_DIR>/plan-tracker.md``.

    Factory form: WARN-grade only — the precondition never fails the run;
    blocking enforcement belongs to the family authorization ticket (face ②).

    FIX-431 — 发布间隙态 N/A: with no active P0/P1 unit (release gap state,
    all task rows complete) the face has NO judgment object, so it judges
    N/A and emits no WARN: the「无活跃 P0/P1 unit」/ goal-face-missing /
    placeholder-contract WARNs only carry meaning in the active-unit
    runtime. An unreadable execution-packets face still WARNs (evaluation
    integrity is disclosed in every state — 异常不隐藏).

    Returns (never raises; unreadable faces degrade to WARN):
        {
          "applicable": True,
          "active_units": bool,       # False = 发布间隙态 (FIX-431)
          "plan_tracker_goal_face": bool,
          "units": [{task_id, contract_ready, issues}, ...],
          "contract_ready_units": [task_id, ...],
          "precondition_met": bool,   # goal face AND ≥1 contract-ready unit
          "warn": [detail strings],
        }
    """
    governance_dir, active_tasks, load_packets, validate_contract = _goal_inputs()
    tasks = active_tasks()
    packets, load_error = load_packets(packet_path)
    plan_text = None
    try:
        plan_text = (governance_dir / "plan-tracker.md").read_text(
            encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        plan_text = None
    from governance_readers import project_config
    goal = project_config(plan_text or "").get("项目目标", "").strip()
    goal_face = (bool(goal and not goal.startswith("<")) or
                 any(marker in (plan_text or "") for marker in RB2_PLAN_TRACKER_GOAL_FACE_MARKERS))

    units = []
    for task in tasks:
        task_id = task["task_id"]
        packet = packets.get(task_id) if isinstance(packets, dict) else None
        if packet is None:
            issues = ["missing execution packet"]
        else:
            issues = validate_contract(packet)
        units.append({
            "task_id": task_id,
            "contract_ready": not issues,
            "issues": issues,
        })
    contract_ready_units = [u["task_id"] for u in units if u["contract_ready"]]
    precondition_met = bool(goal_face and contract_ready_units)

    warns = []
    if load_error:
        warns.append(
            "ADR-RB-2 激活前置无法完整评估: execution packets 不可读（{0}）".format(
                load_error))
    if tasks:
        # 运行期（有活跃 P0/P1 unit）——判定链现行为零变化（FIX-431 边界）。
        if not goal_face:
            warns.append(
                "ADR-RB-2 宿主激活前置未满足: plan-tracker 无目标层面"
                "（{0} 任一）——契约无法追溯到 plan-tracker 成功标准".format(
                    "/".join(RB2_PLAN_TRACKER_GOAL_FACE_MARKERS)))
        if not contract_ready_units:
            warns.append(
                "ADR-RB-2 宿主激活前置未满足: 全部活跃 unit 的 product_success_contract"
                " 为占位/无效（TO_BE_DEFINED 占位符穿透目标层）: {0}".format(
                    "; ".join("{0}: {1}".format(u["task_id"], ", ".join(u["issues"]))
                              for u in units)))
    # 间隙态（无活跃 P0/P1 unit）→ face① 判 N/A：无判定对象，不发「无活跃
    # P0/P1 unit」WARN（FIX-431）；load_error 披露除外——评估完整性异常不隐藏。

    return {
        "applicable": True,
        "active_units": bool(tasks),
        "plan_tracker_goal_face": goal_face,
        "units": units,
        "contract_ready_units": contract_ready_units,
        "precondition_met": precondition_met,
        "warn": warns,
    }


def judge_rb2_contract_gate(action, readiness=None):
    """ADR-RB-2 face ② — contract-missing gate judge for one action label.

    Verdict table (judge-only; enforcement governed by
    RB2_SENSITIVE_BLOCK_ENFORCED):
      no active P0/P1 unit (gap state)  → N/A (FIX-431: 无判定语境)
      contract ready                   → PASS
      contract missing, non-sensitive  → WARN
      contract missing, sensitive      → BLOCK

    Factory demotion: with RB2_SENSITIVE_BLOCK_ENFORCED=False a BLOCK verdict
    is demoted to WARN (the blocked 判据 stays observable in ``raw_verdict``
    without intercepting the action — 授权票翻转前不阻断). After the family
    authorization ticket flips the flag, verdict "BLOCK" means the caller
    MUST abort the sensitive action. A gap-state N/A is never affected by
    the flip (no judgment object → nothing to enforce).

    Returns:
        {action, sensitive, contract_ready, raw_verdict, verdict, enforcement}
    """
    if readiness is None:
        readiness = check_goal_layer_contract_readiness()
    # FIX-431: 间隙态（无活跃 P0/P1 unit）无判定语境——契约缺失 WARN/BLOCK
    # 只在有活跃 unit 的运行期才有意义。Hand-built readiness 缺
    # ``active_units`` 键时按运行期处理（向后兼容：直接调用方零行为变化）。
    has_active_units = readiness.get("active_units", True)
    contract_ready = bool(readiness.get("precondition_met"))
    sensitive = bool(RB2_SENSITIVE_ACTION_RE.search(str(action or "")))
    if not has_active_units:
        raw_verdict = "N/A"
    elif contract_ready:
        raw_verdict = "PASS"
    elif sensitive:
        raw_verdict = "BLOCK"
    else:
        raw_verdict = "WARN"
    enforced = bool(RB2_SENSITIVE_BLOCK_ENFORCED)
    return {
        "action": str(action or ""),
        "sensitive": sensitive,
        "contract_ready": contract_ready,
        "raw_verdict": raw_verdict,
        "verdict": raw_verdict if (raw_verdict != "BLOCK" or enforced)
                   else "WARN",
        "enforcement": "enforced" if enforced
                       else "warn-only (factory; flip via family "
                            "authorization ticket)",
    }


def render_rb2_goal_contract_block():
    """Print the ADR-RB-2 two-face block after Check 18d (FEAT-069 wiring).

    WARN-grade companion of the Check 18d product-success-contract segment:
    face ① prints the host-activation precondition verdict; face ② prints
    the sensitive-action gate judge for a sensitive and a non-sensitive demo
    action evaluated against the REAL host readiness (正负例 observable per
    run). FIX-431: in the release gap state (no active P0/P1 unit) both
    faces print [N/A] instead of WARN — no judgment object / no judgment
    context. Prints only — never counts into check-governance issues
    (factory form; the authorization ticket owns the enforcement flip).
    """
    readiness = check_goal_layer_contract_readiness()
    print("\n┌─ Check 18d-RB2: Goal-Layer Contract Gate (ADR-RB-2/FEAT-069) ─┐")
    if readiness["precondition_met"]:
        print("│  Activation precondition: [PASS] goal-layer contract ready "
              "({0})".format(", ".join(readiness["contract_ready_units"])))
    elif not readiness.get("active_units", True):
        print("│  Activation precondition: [N/A] 发布间隙态——无活跃 P0/P1 "
              "unit，goal-contract 无判定对象（FIX-431；不发 WARN）")
    for reason in readiness["warn"]:
        print("│  Activation precondition: [WARN] {0}".format(reason))
    demo_judges = (
        ("sensitive demo action {0!r}".format(_RB2_DEMO_SENSITIVE_ACTION),
         judge_rb2_contract_gate(_RB2_DEMO_SENSITIVE_ACTION, readiness)),
        ("non-sensitive demo action {0!r}".format(
            _RB2_DEMO_NONSENSITIVE_ACTION),
         judge_rb2_contract_gate(_RB2_DEMO_NONSENSITIVE_ACTION, readiness)),
    )
    print("│  Sensitive-action gate judge (enforcement={0})".format(
        demo_judges[0][1]["enforcement"]))
    for label, judge in demo_judges:
        if judge["raw_verdict"] == "BLOCK":
            print("│    [WARN] (judge=BLOCK) {0}: contract missing → BLOCK "
                  "verdict; enforcement off（授权票翻转前不拦截）".format(label))
        elif judge["raw_verdict"] == "N/A":
            print("│    [N/A] {0}: 间隙态无活跃 unit——无判定语境（FIX-431；"
                  "不发 WARN）".format(label))
        elif judge["verdict"] == "WARN":
            print("│    [WARN] {0}: contract missing → WARN（非敏感，不阻断"
                  "）".format(label))
        else:
            print("│    [PASS] {0}: contract ready → gate open".format(label))
    print("└──────────────────────────────────────────────────────────┘")


