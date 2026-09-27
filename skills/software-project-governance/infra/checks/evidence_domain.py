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
    # FIX-390: DEC-168 machine row-family credential predicate (Check 18b
    # machine-attestation face) — consumed from verify_workflow by identity,
    # never re-stated here (FIX-292 single-shape-source lesson).
    "_row_has_governance_store_machine_credential",
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
    _resolve_shared()
    result = {
        "entries": [],
        "pass": True,
    }

    for entry in _current_release_impact_entries():
        desc = entry["description"]
        basis_text = entry.get("fact_basis", "")
        fact_match = FACT_BASIS_RE.search(desc)
        fact_source = "description"
        if fact_match is None and basis_text:
            fact_match = FACT_BASIS_RE.search(basis_text)
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

        speculative_match = UNGROUNDED_CLAIM_RE.search(desc)
        if speculative_match is None and basis_text:
            speculative_match = UNGROUNDED_CLAIM_RE.search(basis_text)
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


def check_evidence_binding_drift():
    """FEAT-068 / C-10: drift check on the machine-maintained faces.

    ADR-019 §2.2 (R0 correction) scopes this check to the machine-maintained
    faces ONLY (runtime + transition projection): a write bypassing their legal
    writers (loop_migration / process_gate_result chain) is intercepted, while
    legal human/protocol writes to the goal and evidence faces stay out of
    scope. ADR-019 §2.5 fixes the evidence binding four-tuple:
    (unit, 产物版本, 检查策略版本, 审查主体) — expressed here as the
    runtime's flow_units[].flow_unit_id / migration_plan_hash /
    gate_schema@digest / decomposition_confirmed markers.

    Arming: the check applies ONLY when ``.governance/flow-unit-runtime.json``
    exists (the runtime face loop_migration writes). Legacy hosts (no runtime,
    classic phase-gate) get ``applicable=False`` and zero issues — pre-switch
    the Gate table is not yet a machine face and must stay unpoliced
    (backward compatible: zero behavior change for existing hosts/fixtures).

    FAIL-grade faces (interception):
      - runtime_face_unreadable / runtime_face_invalid_json — corrupt face.
      - runtime_face_missing_machine_credential — a required legal-writer
        marker missing or malformed (schema_version, runtime_contract,
        workflow_model == "loop-engineering", migration_version, 64-hex
        migration_plan_hash, migration_timestamp, decomposition_confirmed is
        True, non-empty flow_units).
      - runtime_unit_corrupt — per-unit shape violation (duplicate
        flow_unit_id, empty derivation_reason / gate_state.gate_id, missing
        loop_state.fuse, dangling dependency).
      - evidence_binding_missing — runtime claims migration_version V but no
        ``MIGRATION-V`` row exists in evidence-log.md (the evidence-face half
        of the §2.5 binding is gone).

    WARN-grade faces (drift needing a legal re-sync via loop_migration, not an
    interception of a hand-edit):
      - unit_set_drift — runtime unit set differs from the plan re-derived
        from the current plan-tracker (legal plan-tracker edits make the
        runtime stale; ADR-019 §2.2: unit-set changes go through loop-migrate).
      - gate_schema_drift — runtime gate_schema digest differs from the
        current registry semantics (检查策略版本升级使既有认证失效, §2.5).

    Returns:
        dict with keys: applicable (bool), runtime_path (str or None),
        fail (list of {"type", "detail"}), warn (list of {"type", "detail"}),
        pass (bool — True iff applicable is False or fail is empty).
    """
    _resolve_shared()
    runtime_path = GOVERNANCE_DIR / "flow-unit-runtime.json"
    if not runtime_path.is_file():
        return {
            "applicable": False,
            "runtime_path": None,
            "fail": [],
            "warn": [],
            "pass": True,
        }
    fails = []
    warns = []
    try:
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fails.append({
            "type": "runtime_face_unreadable",
            "detail": (
                f"{runtime_path}: 机器维护面不可读/不可解析"
                f"（疑似绕过合法写入方直改或截断）: {exc}"
            ),
        })
        return {
            "applicable": True,
            "runtime_path": str(runtime_path),
            "fail": fails,
            "warn": warns,
            "pass": False,
        }
    if not isinstance(runtime, dict):
        fails.append({
            "type": "runtime_face_invalid_json",
            "detail": (
                f"{runtime_path}: 顶层必须是对象，实为 "
                f"{type(runtime).__name__}"
            ),
        })
        return {
            "applicable": True,
            "runtime_path": str(runtime_path),
            "fail": fails,
            "warn": warns,
            "pass": False,
        }

    # ── Face 1: machine-writer credential markers (§2.5 four-tuple) ─────
    schema_version = runtime.get("schema_version")
    runtime_contract = runtime.get("runtime_contract")
    workflow_model = runtime.get("workflow_model")
    migration_version = runtime.get("migration_version")
    migration_plan_hash = runtime.get("migration_plan_hash")
    migration_timestamp = runtime.get("migration_timestamp")
    decomposition_confirmed = runtime.get("decomposition_confirmed")
    flow_units = runtime.get("flow_units")
    gate_schema = runtime.get("gate_schema")

    if not (isinstance(schema_version, str) and schema_version.strip()):
        fails.append({
            "type": "runtime_face_missing_machine_credential",
            "detail": "schema_version 缺失或为空",
        })
    if not (isinstance(runtime_contract, str) and runtime_contract.strip()):
        fails.append({
            "type": "runtime_face_missing_machine_credential",
            "detail": "runtime_contract 缺失或为空",
        })
    if workflow_model != "loop-engineering":
        fails.append({
            "type": "runtime_face_missing_machine_credential",
            "detail": (
                f"workflow_model 必须为 loop-engineering，实为 "
                f"{workflow_model!r}"
            ),
        })
    if not (isinstance(migration_version, str) and migration_version.strip()):
        fails.append({
            "type": "runtime_face_missing_machine_credential",
            "detail": "migration_version 缺失或为空",
        })
        migration_version = None
    if not (isinstance(migration_plan_hash, str)
            and re.fullmatch(r"[0-9a-f]{64}", migration_plan_hash)):
        fails.append({
            "type": "runtime_face_missing_machine_credential",
            "detail": (
                f"migration_plan_hash 必须为 64 位小写十六进制"
                f"（产物版本绑定），实为 {migration_plan_hash!r}"
            ),
        })
    if not (isinstance(migration_timestamp, str)
            and migration_timestamp.strip()):
        fails.append({
            "type": "runtime_face_missing_machine_credential",
            "detail": "migration_timestamp 缺失或为空",
        })
    if decomposition_confirmed is not True:
        fails.append({
            "type": "runtime_face_missing_machine_credential",
            "detail": (
                f"decomposition_confirmed 必须为 true（审查主体确认），"
                f"实为 {decomposition_confirmed!r}"
            ),
        })
    if not (isinstance(flow_units, list) and flow_units):
        fails.append({
            "type": "runtime_face_missing_machine_credential",
            "detail": "flow_units 缺失或为空（unit 绑定缺失）",
        })
        flow_units = []

    # ── Face 2: per-unit referential integrity ──────────────────────────
    unit_ids = []
    for unit in flow_units:
        if not isinstance(unit, dict):
            fails.append({
                "type": "runtime_unit_corrupt",
                "detail": f"flow_units 元素不是对象: {unit!r}",
            })
            continue
        fuid = unit.get("flow_unit_id")
        if not (isinstance(fuid, str) and fuid.strip()):
            fails.append({
                "type": "runtime_unit_corrupt",
                "detail": f"flow_unit_id 缺失或为空: {unit!r}",
            })
            continue
        if fuid in unit_ids:
            fails.append({
                "type": "runtime_unit_corrupt",
                "detail": f"flow_unit_id 重复: {fuid}",
            })
        else:
            unit_ids.append(fuid)
        for field in ("unit_type", "derivation_reason"):
            value = unit.get(field)
            if not (isinstance(value, str) and value.strip()):
                fails.append({
                    "type": "runtime_unit_corrupt",
                    "detail": f"{fuid}: {field} 缺失或为空",
                })
        loop_state = unit.get("loop_state")
        if not isinstance(loop_state, dict) or not isinstance(
                loop_state.get("fuse"), dict):
            fails.append({
                "type": "runtime_unit_corrupt",
                "detail": f"{fuid}: loop_state.fuse 缺失",
            })
        gate_state = unit.get("gate_state")
        if (not isinstance(gate_state, dict)
                or not (isinstance(gate_state.get("gate_id"), str)
                        and gate_state["gate_id"].strip())):
            fails.append({
                "type": "runtime_unit_corrupt",
                "detail": f"{fuid}: gate_state.gate_id 缺失或为空",
            })
        if not (isinstance(unit.get("runtime_status"), str)
                and unit["runtime_status"].strip()):
            fails.append({
                "type": "runtime_unit_corrupt",
                "detail": f"{fuid}: runtime_status 缺失或为空",
            })
        deps = unit.get("dependencies")
        if not isinstance(deps, list) or not all(
                isinstance(dep, str) for dep in deps):
            fails.append({
                "type": "runtime_unit_corrupt",
                "detail": f"{fuid}: dependencies 必须为字符串列表",
            })

    id_set = set(unit_ids)
    for unit in flow_units:
        if not isinstance(unit, dict):
            continue
        deps = unit.get("dependencies")
        if not isinstance(deps, list):
            continue
        for dep in deps:
            if isinstance(dep, str) and dep not in id_set:
                fails.append({
                    "type": "runtime_unit_corrupt",
                    "detail": (
                        f"{unit.get('flow_unit_id')}: 悬空依赖 {dep!r}"
                        f"（不在 unit 集合内）"
                    ),
                })

    # ── Face 3: evidence-face half of the §2.5 binding ──────────────────
    if migration_version:
        evidence_path = GOVERNANCE_DIR / "evidence-log.md"
        migration_row_seen = False
        if evidence_path.is_file():
            try:
                content = evidence_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                content = None
            if content is not None:
                marker = re.compile(
                    r"^\|\s*MIGRATION-" + re.escape(migration_version) + r"\b"
                )
                migration_row_seen = any(
                    marker.match(line.strip()) for line in content.split("\n")
                )
        if not migration_row_seen:
            fails.append({
                "type": "evidence_binding_missing",
                "detail": (
                    f"运行态宣称 migration_version={migration_version}，"
                    f"但 evidence-log.md 无对应 MIGRATION 行"
                    f"（§2.5 证据绑定缺失——迁移/审查主体在证据层无留痕）"
                ),
            })

    # ── Face 4 (WARN): drift vs the legal writers' current outputs ──────
    # Lazy import: only armed hosts pay it; the module import graph stays
    # unchanged for every legacy host and fixture (backward compatible).
    from loop_migration_plan import (  # noqa: WPS433 (deliberate lazy import)
        _resolve_gate_schema,
        build_migration_plan,
    )
    try:
        plan_text = (GOVERNANCE_DIR / "plan-tracker.md").read_text(
            encoding="utf-8")
        plan = build_migration_plan(
            str(GOVERNANCE_DIR.parent), None,
            plan_tracker_text=plan_text,
        )
        runtime_ids = sorted(
            unit.get("flow_unit_id") for unit in flow_units
            if isinstance(unit, dict)
            and isinstance(unit.get("flow_unit_id"), str)
        )
        derived_ids = sorted(plan.unit_ids)
        if runtime_ids != derived_ids:
            warns.append({
                "type": "unit_set_drift",
                "detail": (
                    f"运行态 unit 集（{len(runtime_ids)}）与计划面重派生 "
                    f"unit 集（{len(derived_ids)}）不一致——计划面合法演化后"
                    f"运行态未同步；unit 集变更必须经 loop_migration 重新"
                    f"同步（ADR-019 §2.2）"
                ),
            })
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        warns.append({
            "type": "unit_set_drift",
            "detail": f"计划面重派生失败，无法比对 unit 集漂移: {exc}",
        })
    current_gate_schema = _resolve_gate_schema()
    if gate_schema is not None and gate_schema != current_gate_schema:
        warns.append({
            "type": "gate_schema_drift",
            "detail": (
                f"runtime gate_schema={gate_schema!r} 与当前 registry 语义 "
                f"{current_gate_schema!r} 不一致——检查策略版本升级使既有认证"
                f"失效（§2.5），需重新迁移认证"
            ),
        })

    return {
        "applicable": True,
        "runtime_path": str(runtime_path),
        "fail": fails,
        "warn": warns,
        "pass": not fails,
    }


def render_evidence_binding_drift_block(all_issues):
    """Print the C-10 evidence-binding drift block; return the issue count.

    Engine-dispatch companion of :func:`check_evidence_binding_drift` — the
    check logic and its presentation live in this domain module so the
    verify_workflow engine only wires dispatch (checks.injection_budget
    precedent; R1 mainfile budget keeps verify_workflow.py line-neutral).
    FAIL entries count into all_issues; WARN entries print without counting.
    """
    block = check_evidence_binding_drift()
    print("\n┌─ Check 3b: C-10 Evidence Binding Drift (FEAT-068) ──┐")
    if not block.get("applicable"):
        print("│  [PASS] Machine faces absent (pre-switch host) — not applicable.")
    else:
        for issue in block.get("fail", []):
            all_issues += 1
            print(f"│  [FAIL] {issue['type']}: {issue['detail']}")
        for issue in block.get("warn", []):
            print(f"│  [WARN] {issue['type']}: {issue['detail']}")
        if block.get("pass"):
            print("│  [PASS] Machine-maintained faces match legal writers (C-10).")
    print("└──────────────────────────────────────────────────────┘")
    return all_issues


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
    _resolve_shared()
    result = {
        "entries": [],
        "pass": True,
    }

    for entry in _current_release_impact_entries():
        desc = entry["description"]
        basis_text = entry.get("fact_basis", "")
        raw_json = _extract_structured_fact_json(desc)
        if not raw_json and basis_text:
            raw_json = _extract_structured_fact_json(basis_text)
        # FIX-390: machine-attestation fallback — only when the row carries
        # NO structured-fact JSON anywhere (a present-but-invalid JSON is
        # judged on its own defects; the credential never rescues it).
        machine_attested = False
        if not raw_json:
            machine_attested = _row_has_governance_store_machine_credential(
                entry.get("raw_line", ""))
        issues = []
        status = "PASS"
        payload = None

        if raw_json:
            try:
                payload = json.loads(raw_json)
                issues.extend(_validate_structured_fact_payload(payload))
            except json.JSONDecodeError as exc:
                issues.append(f"结构化事实 JSON 解析失败: {exc.msg}")
        elif not machine_attested:
            issues.append("缺少 结构化事实: JSON")

        if issues:
            status = "FAIL"
            result["pass"] = False

        result["entries"].append({
            "task_id": entry["task_id"],
            "evd_id": entry["evd_id"],
            "has_structured_fact": bool(raw_json),
            "machine_attested": machine_attested,
            "status": status,
            "issues": issues,
            "commands": len(payload.get("commands", [])) if isinstance(payload, dict) and isinstance(payload.get("commands"), list) else 0,
            "files_changed": len(payload.get("files_changed", [])) if isinstance(payload, dict) and isinstance(payload.get("files_changed"), list) else 0,
        })

    return result


