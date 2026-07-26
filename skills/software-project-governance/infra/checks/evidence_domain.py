"""Evidence-domain checks — extracted from verify_workflow.py in 0.70.0.

Scope (DEC-083 Phase 5a / ADR-016 / FEAT-009): the evidence-completeness,
evidence-quality, structured-evidence, and fact-grounding checks (Checks 1,
1b, 6, 6b), plus their evidence-only parsing helpers.

This module owns the evidence check domain. Shared helpers and constants that
are still defined in verify_workflow.py (path resolution, evidence-log path
constants, header-marker constant sets, `expand_task_ids`,
`GovernanceDataSource`, the structured-fact JSON helpers, and the context-task
parsers) are reached through a deferred module reference rather than a
top-level import, so that verify_workflow.py can import this module at module
load time without creating an import cycle. When the common-helpers domain
(`checks/_shared.py`) is extracted in a later release, these references will
be retargeted to that module.

Functions with cross-domain callers (e.g. `_count_evidence_rows`,
`_evidence_task_type_index`, `_iter_archive_aware_evidence_units`,
`_check_evidence_mentions`, `_evidence_closes_fix_069_while_req_open`) STAY in
verify_workflow.py and are reached via the deferred accessor — they are not
duplicated here (ADR-016 §3.1 / §4.3 KEEP rule).

See docs/architecture/ADR-016-verify-phase5-extraction-0.70.0.md for the
design and the line-number baseline used during extraction.
"""

import re
import json
from datetime import date, datetime

# ── Shared-helper access (deferred to avoid import cycle) ──────────
# Same deferred-_vw() pattern as checks.manifest (Phase 1) and
# checks.capability_registry (Phase 2). The shared names are resolved lazily
# on the first call into this module (after verify_workflow has finished
# loading) and cached in this module's globals for subsequent calls, so the
# moved function bodies can reference them by bare name unchanged.

_VW_CACHE = None


def _vw():
    """Return the verify_workflow module (imported lazily, cached).

    Cached so repeated calls reuse the same module reference (REVIEW-FIX-153
    P2, same pattern as checks.manifest / checks.capability_registry).
    """
    global _VW_CACHE
    if _VW_CACHE is None:
        import verify_workflow  # noqa: WPS433 (deferred import on purpose)
        _VW_CACHE = verify_workflow
    return _VW_CACHE


# Shared names this domain reaches back into verify_workflow for. Refreshed
# on every call into `_resolve_shared()` (NOT cached) so test-time monkey-
# patching of verify_workflow attributes propagates, and so the moved
# function bodies can reference them by bare name (byte-identical bodies,
# per ADR-016 §5.3 "no behavioral change").
_SHARED_NAMES = (
    "EVIDENCE_PATH",
    "GOVERNANCE_DIR",
    "FACT_BASIS_RE",
    "UNGROUNDED_CLAIM_RE",
    "GOVERNANCE_CONTEXT_EVIDENCE_STATE_HEADERS",
    "GOVERNANCE_CONTEXT_EVIDENCE_CLOSED_MARKERS",
    "GOVERNANCE_CONTEXT_EVIDENCE_UNFINISHED_MARKERS",
    "GOVERNANCE_CONTEXT_EVIDENCE_TASK_HEADERS",
    "GovernanceDataSource",
    "expand_task_ids",
    "_context_file",
    "_context_task",
    "_extract_task_title_from_line",
    "_governance_table_cells",
    "_normalize_priority",
    "_current_release_impact_entries",
    "_extract_structured_fact_json",
    "_validate_structured_fact_payload",
)


def _resolve_shared():
    """Refresh this module's globals with shared names from verify_workflow.

    Re-fetches on EVERY call (not cached) so test-time monkey-patching of
    verify_workflow attributes (e.g. `patch.object(vw, "EVIDENCE_PATH", ...)`,
    swapping in `GovernanceDataSource`, or editing header-marker constant
    sets) propagates into this module's bare-name lookups. The cost is
    negligible: these checks run once per CLI invocation, not in a hot loop,
    and `getattr` on a cached module reference is cheap. This mirrors how
    checks.manifest re-resolves `ROOT = _root()` inside each function body
    (Phase 1 precedent).
    """
    vw = _vw()
    g = globals()
    for _name in _SHARED_NAMES:
        g[_name] = getattr(vw, _name)


# ── Domain constants and functions (moved verbatim from verify_workflow.py) ──

def _evidence_header_index(header, header_markers):
    _resolve_shared()
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
    _resolve_shared()
    task_ids = re.findall(r"\b([A-Z]+-\d+)\b", task_cell or "")
    for task_id in task_ids:
        if not task_id.startswith("EVD-"):
            return task_id
    return None


def _evidence_state_cells(cells, header):
    _resolve_shared()
    state_indices = []
    if header:
        for idx, cell in enumerate(header):
            normalized = re.sub(r"\s+", " ", cell.strip().lower())
            compact = normalized.replace(" ", "")
            if any(
                marker.lower() in normalized or marker.lower().replace(" ", "") in compact
                for marker in GOVERNANCE_CONTEXT_EVIDENCE_STATE_HEADERS
            ):
                state_indices.append(idx)
    else:
        # Canonical evidence rows are:
        # 编号 | 对应任务 ID | 阶段 | 证据类型 | ... | 关联 Gate | 备注
        state_indices.extend(idx for idx in (3, 9, 10) if idx < len(cells))
    return [cells[idx] for idx in state_indices if idx < len(cells)]


def _is_closed_evidence_state(text):
    _resolve_shared()
    lowered = (text or "").lower()
    if "未完成" in lowered:
        return False
    return any(marker in lowered for marker in GOVERNANCE_CONTEXT_EVIDENCE_CLOSED_MARKERS)


def _is_active_evidence_state(text):
    _resolve_shared()
    lowered = (text or "").lower()
    return any(marker.lower() in lowered for marker in GOVERNANCE_CONTEXT_EVIDENCE_UNFINISHED_MARKERS)


def _parse_evidence_context_tasks(root):
    _resolve_shared()
    evidence_path = _context_file(root, ".governance/evidence-log.md")
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
        cells = _governance_table_cells(stripped)
        if not cells:
            continue
        if cells[0] in {"编号", "Evidence ID"} or any("对应任务" in cell or "Task ID" in cell for cell in cells):
            header = cells
            continue
        task_idx = _evidence_header_index(header, GOVERNANCE_CONTEXT_EVIDENCE_TASK_HEADERS)
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
        tasks.append(_context_task(
            task_id,
            _extract_task_title_from_line(stripped, task_id),
            status,
            ".governance/evidence-log.md",
            stripped,
            priority=_normalize_priority(stripped),
        ))
    return tasks


def parse_evidence_task_ids():
    """Return set of task IDs that have evidence entries (range-expanded)."""
    _resolve_shared()
    content = EVIDENCE_PATH.read_text(encoding="utf-8")
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
    _resolve_shared()
    content = EVIDENCE_PATH.read_text(encoding="utf-8")
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


def check_evidence_completeness():
    """Check that every completed task has at least one evidence entry.

    Uses GovernanceDataSource to transparently aggregate hot files + archive
    files. Falls back to single-file mode when archive/ directory does not
    exist (backward compatible).
    """
    _resolve_shared()
    ds = GovernanceDataSource()
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
        "evidenced_count": len(matched),
        "missing_evidence": sorted(current_missing),
        "historical_missing_evidence": sorted(historical_missing),
    }


def check_evidence_quality():
    """Check evidence quality: session context references, circular refs, empty output claims."""
    _resolve_shared()
    evidence_path = GOVERNANCE_DIR / "evidence-log.md"
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


def check_fact_grounding():
    """FIX-080: Check current product-code evidence is grounded in facts."""
    _resolve_shared()
    result = {
        "entries": [],
        "pass": True,
    }

    for entry in _current_release_impact_entries():
        desc = entry["description"]
        fact_match = FACT_BASIS_RE.search(desc)
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

        speculative_match = UNGROUNDED_CLAIM_RE.search(desc)
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
            "status": status,
            "issues": issues,
        })

    return result


def check_structured_evidence():
    """FIX-083: Check current product-code evidence has machine-readable facts."""
    _resolve_shared()
    result = {
        "entries": [],
        "pass": True,
    }

    for entry in _current_release_impact_entries():
        desc = entry["description"]
        raw_json = _extract_structured_fact_json(desc)
        issues = []
        status = "PASS"
        payload = None

        if not raw_json:
            issues.append("缺少 结构化事实: JSON")
        else:
            try:
                payload = json.loads(raw_json)
                issues.extend(_validate_structured_fact_payload(payload))
            except json.JSONDecodeError as exc:
                issues.append(f"结构化事实 JSON 解析失败: {exc.msg}")

        if issues:
            status = "FAIL"
            result["pass"] = False

        result["entries"].append({
            "task_id": entry["task_id"],
            "evd_id": entry["evd_id"],
            "has_structured_fact": bool(raw_json),
            "status": status,
            "issues": issues,
            "commands": len(payload.get("commands", [])) if isinstance(payload, dict) and isinstance(payload.get("commands"), list) else 0,
            "files_changed": len(payload.get("files_changed", [])) if isinstance(payload, dict) and isinstance(payload.get("files_changed"), list) else 0,
        })

    return result


