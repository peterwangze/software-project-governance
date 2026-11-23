"""Parse Markdown and reconcile the hot governance ledgers with snapshots."""
import re
from datetime import datetime
from pathlib import Path
from typing import NamedTuple


_TASK_ID_IN_REF_RE = re.compile(r"\b([A-Z]+-\d+)\b")


# Standalone task-ID table cell (e.g. ``FIX-222`` / ``**REL-070**``). Single
# definition shared by parse_current_active_tasks and the FEAT-011
# governance-write-guard task-row scanner — no second shape source (FIX-292
# semantic dual-source lesson).
_TASK_ID_CELL_RE = re.compile(r"^(?:\*\*)?[A-Z]+-\d+(?:\*\*)?$")

# Date-cell content shape (FIX-374): ``YYYY-MM-DD`` / ``YYYY/MM/DD`` as
# written by the LIVE evidence-log convention. Sole consumer: the evidence
# format check in check_protocol_compliance — for an ambiguous 9-cell row,
# a date-shaped cells[6] proves the historical Date cell is present
# (genuine historical row); any other value contradicts the historical
# Date semantics and marks the row as a truncated LIVE row (Date cell
# lost). FIX-382 adds a second probe in that truncated face: a date-shaped
# cells[7] proves the real Date cell survived at its shifted LIVE offset
# (trailing Gate/Notes cell lost — not a missing Date). Real-data basis
# (production-parser census 2026-09-24, FIX-382): all 12 live 9-cell
# historical rows in .governance/evidence-log.md carry a date-shaped
# cells[6] and a non-date cells[7] — zero incidence on the historical
# face of either probe (literal-pipe grep counts 11 rows: parser-protected
# pipes (code-span/JSON-string/bracket-depth) bias — review-FIX-374 F-1
# count question resolved).
_EVIDENCE_DATE_SHAPE_RE = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$")


class HotFactPolicy(NamedTuple):
    """Release markers and patterns used by a single hot-ledger reconciliation."""

    readiness_version: str
    requirements: dict
    snapshot_release_version: re.Pattern
    plan_workflow_version: re.Pattern
    snapshot_version: re.Pattern
    snapshot_date: re.Pattern
    release_blockers: list


def _markdown_has_heading(content, level, title):
    return re.search(rf"^{'#' * level}\s+{re.escape(title)}\s*$", content, re.MULTILINE) is not None


def _markdown_section(content, heading):
    lines = content.splitlines()
    start = None
    level = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped == heading:
            start = idx + 1
            level = len(stripped) - len(stripped.lstrip("#"))
            break
    if start is None:
        return ""

    end = len(lines)
    heading_pattern = re.compile(r"^(#{1,%d})\s+" % level)
    for idx in range(start, len(lines)):
        if heading_pattern.match(lines[idx].strip()):
            end = idx
            break
    return "\n".join(lines[start:end])


def _markdown_section_by_prefix(content, heading_prefix):
    lines = content.splitlines()
    for line_no, line in enumerate(lines):
        stripped = line.strip()
        if stripped == heading_prefix:
            return _markdown_section(content, heading_prefix)
        if stripped.startswith(heading_prefix):
            level = len(stripped) - len(stripped.lstrip("#"))
            start = line_no + 1
            end = len(lines)
            heading_pattern = re.compile(r"^(#{1,%d})\s+" % level)
            for idx in range(start, len(lines)):
                if heading_pattern.match(lines[idx].strip()):
                    end = idx
                    break
            return "\n".join(lines[start:end])
    return ""


def _markdown_table_cells(line):
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _normalize_agent_token(token):
    token = re.sub(r"[`*]", "", token)
    token = re.sub(r"[（(][^）)]*[）)]", "", token)
    return token.strip()


def _generic_reviewer_cells(content):
    hits = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        for cell in _markdown_table_cells(line):
            cleaned = _normalize_agent_token(cell)
            parts = [
                _normalize_agent_token(part)
                for part in re.split(r"\s*(?:,|，|、|\+|/|或|和)\s*", cleaned)
            ]
            if any(part in ("Reviewer", "Reviewer Agent") for part in parts):
                hits.append(line_no)
                break
    return hits


def _normalize_markdown_cell(cell):
    return re.sub(r"[`*]", "", cell).strip()


def _find_table_row_by_first_cell(content, first_cell):
    for line in content.splitlines():
        cells = _markdown_table_cells(line)
        if cells and _normalize_markdown_cell(cells[0]) == first_cell:
            return cells
    return []


def _find_table_rows_with_cell(content, target_cell):
    rows = []
    for line in content.splitlines():
        cells = _markdown_table_cells(line)
        if any(_normalize_markdown_cell(cell) == target_cell for cell in cells):
            rows.append(cells)
    return rows


def _status_cell_is_delivered(status):
    return "✅" in status or "已交付" in status or "已完成" in status


def _hot_status_cell_is_delivered(status, *, status_clean_cell, status_is_writer_committed_cell):
    """Delivered test for Check 28c task rows (FIX-395): the legacy
    ✅/已交付/已完成 word forms (:func:`_status_cell_is_delivered` — S_old,
    byte-for-byte) OR the FIX-393 writer-terminal predicate consumed BY
    IDENTITY (:func:`_status_is_writer_committed_cell` — the governed
    writer's own chain ``task_row_update._STATE_MARKER_CHAIN`` + the ops
    receipt anchor; never a fourth mirror). A writer-committed terminal
    cell (「committed … 〔op-<32hex>〕」) carries none of the legacy
    literals, so the legacy read alone judged the delivered 0.88.0 release
    chain (REL-087/088/089) NOT delivered → released_face=False → the
    roadmap missing-task/overstate pseudo-FAIL cluster (census 20,
    2026-09-26). Guarded directions preserved: active dev/triaged cells
    keep the open verdict even when writer-anchored (every writer write
    carries an anchor — the chain FIRST-HIT must be ``committed``);
    hand-written 「committed」 without the anchor (B-1 class) and unknown
    tokens are never guessed terminal (未知不猜). Check 18/18b's narrower
    FIX-390 three-state exemption face (:func:`_hot_status_completion_state`)
    is untouched — two faces, two predicates, one FIX-393 authority.
    """
    if _status_cell_is_delivered(status):
        return True
    return status_is_writer_committed_cell(status_clean_cell(status))


def _contains_fix_token_or_range(content, fix_id):
    if fix_id in content:
        return True
    match = re.match(r"FIX-(\d{3})$", fix_id)
    if not match:
        return False
    fix_num = int(match.group(1))
    for start, end in re.findall(r"FIX-(\d{3})\s*[~～-]\s*(\d{3})", content):
        if int(start) <= fix_num <= int(end):
            return True
    return False

# FIX-339 (DEC-195 a): 0.38.0-era version anchors removed — the active anchor
# derives from plan-tracker 工作流版本; the face follows its REL delivery state.
FIX_087_READINESS_VERSION = ".".join(["1", "0", "0"])

FIX_087_REQ_TASKS = {
    "REQ-070": ["FIX-082", "FIX-085"],
    "REQ-071": ["FIX-083"],
    "REQ-072": ["FIX-084"],
    "REQ-073": ["FIX-086"],
    "REQ-074": ["FIX-087"],
}

# FIX-399: the date cell may carry a decorated suffix inside the same bold
# run (real roadmap shapes: `**2026-09-27（M-0 … GO→发布同日）**`), so the
# capture no longer requires the closing `**` to sit flush after the date —
# any non-`*` run up to the closing `**` is tolerated.
# FIX-421: the STATUS cell drifted the same way (real 0.93.x shapes:
# `**已发布 2026-09-30 REL-096（tag …，ledger 双 PASS）**`) — a bold run
# OPENING with 已发布 plus a decorated tail, no longer the exact literal
# `**已发布**`. The tail is tolerated with the same non-`*` rule (pure
# `**已发布**` stays the empty-tail case); the version/date capture groups
# and the FIX-399 last-date semantics are unchanged.
FIX_105_SNAPSHOT_RELEASE_VERSION_RE = re.compile(r"\|\s*\*\*(0\.\d+(?:\.\d+)?)\*\*\s*\|\s*\*\*已发布[^*]*\*\*\s*\|\s*\*\*((?:\d{4}-\d{2}-\d{2})[^*]*)\*\*")

# FIX-339 F-03 registration (REVIEW-FIX-339-CODE-R0): two 工作流版本 parsers
# coexist on purpose. This strict pattern serves the snapshot face and the
# real session-snapshot.md format (closed `**工作流版本:**` bold run). The hot
# face (check_hot_fact_source_consistency) needs a looser inline pattern
# because the real plan-tracker line is `- **工作流版本: 0.81.0（**已发布…`
# (unclosed bold). Not unified until the data format is normalized: feeding
# the loose pattern to the snapshot face would change its parsing there.
FIX_105_PLAN_WORKFLOW_VERSION_RE = re.compile(r"\*\*工作流版本\*\*:\s*([0-9]+(?:\.[0-9]+){2})")

FIX_105_SNAPSHOT_VERSION_RE = re.compile(r"\*\*工作流版本\*\*:\s*([0-9]+(?:\.[0-9]+){2})")

FIX_105_SNAPSHOT_DATE_RE = re.compile(r"\*\*session_date\*\*:\s*(\d{4}-\d{2}-\d{2})")

def snapshot_date_pattern():
    return FIX_105_SNAPSHOT_DATE_RE


FIX_105_READINESS_RELEASE_BLOCKERS = ["REL-018", "REL-019"]


def _version_row_text(plan_content, version):
    row = _find_table_row_by_first_cell(plan_content, version)
    return " | ".join(row) if row else ""


def _task_statuses_for_hot_source(plan_content, task_id, version=None):
    statuses = []
    for cells in _find_table_rows_with_cell(plan_content, task_id):
        normalized = [_normalize_markdown_cell(cell) for cell in cells]
        if len(normalized) >= 2 and normalized[1] == task_id:
            if version and len(normalized) >= 5 and normalized[4] != version:
                continue
            statuses.append(cells[-1])
    return statuses


def _hot_task_is_delivered(plan_content, task_id, version=None, *, is_delivered):
    statuses = _task_statuses_for_hot_source(plan_content, task_id, version=version)
    # FIX-395: writer-committed terminal cells count delivered (FIX-393
    # criteria by identity) — S_new ⊇ S_old, guarded shapes unchanged.
    return bool(statuses) and any(is_delivered(status) for status in statuses)


def _hot_task_is_open(plan_content, task_id, version=None, *, is_delivered):
    statuses = _task_statuses_for_hot_source(plan_content, task_id, version=version)
    # FIX-395: mirror of _hot_task_is_delivered — a writer-committed row no
    # longer counts open; dev/triaged rows (anchored or not) still do.
    return bool(statuses) and any(not is_delivered(status) for status in statuses)


def _hot_task_ids_for_version(plan_content, version, *, is_delivered):
    """FIX-339: data-derived task facts for the active version anchor.

    Returns ``(task_ids, release_delivered, release_declared)`` where
    ``task_ids`` are task-pattern rows whose cells mention ``version`` as a
    standalone token — the target-version cell, a ``X.Y.Z 或后续`` target
    form, or the 事项 cell when the target column carries a date/gate
    reference (REVIEW-FIX-339-CODE-R0 F-01/F-05; real REL-077 row shape) —
    and the release flags describe REL rows *for that version*.

    FIX-339 (REVIEW-FIX-339-CODE-R1 F-R1-01): recognition keeps any-cell
    recall, but a REL row only feeds the release flags when it belongs to
    ``version`` — its target-version cell names the anchor (exact or
    ``X.Y.Z 或后续`` form) or its 事项 cell opens with the ``发布 <anchor>``
    header form. A bare anchor mention in any other cell (narrative,
    dependency, status) never lifts the released face.

    FIX-395 (version-row mapping semantics — documented, NOT changed): a
    task whose target cell names a NEWER version still joins ``task_ids``
    when its narrative mentions the anchor (the bump-source form
    「V→V+1」, e.g. the live REL-091 row) — existing FIX-339 any-cell
    recall, deliberately recall-first. The membership only bites through
    the roadmap enumeration demand, which runs ONLY while ``version`` is
    unreleased (``not released_face``); once the release face lifts — now
    writer-committed-aware via :func:`_hot_status_cell_is_delivered` — the
    enumeration loop is skipped and a swept V+1-target task can no longer
    FAIL the V roadmap row.
    """
    ids, release_delivered, release_declared = [], False, False
    version_token_re = re.compile(r"(?<![\d.])" + re.escape(version) + r"(?![\d.])")
    release_item_re = re.compile(r"[*\s]*发布\s*" + version_token_re.pattern)
    for line in plan_content.splitlines():
        cells = _markdown_table_cells(line)
        normalized = [_normalize_markdown_cell(cell) for cell in cells]
        if len(normalized) < 5 or not re.fullmatch(r"(?:FIX|REL|AUDIT)-\d{3}", normalized[1]):
            continue
        if not any(version_token_re.search(cell) for cell in normalized):
            continue
        if normalized[1] not in ids:
            ids.append(normalized[1])
        if normalized[1].startswith("REL-") and (
            version_token_re.search(normalized[4]) or release_item_re.match(normalized[2])
        ):
            release_declared = True
            release_delivered = release_delivered or is_delivered(cells[-1])
    return ids, release_delivered, release_declared


def _line_mentions_completed_range_as_pending(line, completed_task_ids):
    pending_markers = ["待实施", "待启动", "未完成", "待闭环"]
    if not any(marker in line for marker in pending_markers):
        return ""
    for task_id in completed_task_ids:
        if _contains_fix_token_or_range(line, task_id):
            return task_id
    return ""


def _extract_task_ids(text):
    return sorted(set(re.findall(r"\b(?:FIX|REL|AUDIT)-\d{3}\b", text)))


def _parse_iso_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _latest_published_release_fact(plan_content, *, policy):
    latest = None
    for version, date_cell in policy.snapshot_release_version.findall(plan_content):
        # FIX-399: a decorated cell may narrate several dates (real 0.89.0
        # shape: 立项 2026-09-25 … 发布 2026-09-26). A 已发布 row feeds the
        # latest-published-by-date comparison, so its key must be its release
        # time point — taken as the LAST date in the cell (the release closes
        # the milestone narrative), not the initiation date it opens with.
        # Limitation: this assumes the cell narrates dates in chronological
        # order with the release last; a labelled (发布:) date extraction
        # would need a roadmap format normalization first.
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", date_cell)
        if not dates:
            continue
        release_date = _parse_iso_date(dates[-1])
        if release_date is None:
            continue
        fact = {"version": version, "date": release_date, "date_text": dates[-1]}
        if latest is None or release_date > latest["date"]:
            latest = fact
    return latest


def _snapshot_fact_source_issues(plan_content, plan_tracker_path, *, policy, display_path):
    plan_version_match = policy.plan_workflow_version.search(plan_content)
    plan_version = plan_version_match.group(1) if plan_version_match else ""
    latest_release = _latest_published_release_fact(plan_content, policy=policy)

    snapshot_path = Path(plan_tracker_path).with_name("session-snapshot.md")
    if not snapshot_path.exists():
        return []

    snapshot_content = snapshot_path.read_text(encoding="utf-8")
    rel_snapshot = display_path(snapshot_path)
    issues = []

    snapshot_version_match = policy.snapshot_version.search(snapshot_content)
    snapshot_version = snapshot_version_match.group(1) if snapshot_version_match else ""
    if plan_version and snapshot_version and snapshot_version != plan_version:
        issues.append(f"{rel_snapshot}: session snapshot workflow version {snapshot_version} does not match plan-tracker {plan_version}")
    elif plan_version and not snapshot_version:
        issues.append(f"{rel_snapshot}: session snapshot missing workflow version")

    date_match = policy.snapshot_date.search(snapshot_content)
    snapshot_date = _parse_iso_date(date_match.group(1)) if date_match else None
    if latest_release and snapshot_date and snapshot_date < latest_release["date"]:
        issues.append(
            f"{rel_snapshot}: session snapshot date {date_match.group(1)} is older than latest published release "
            f"{latest_release['version']} ({latest_release['date_text']})"
        )
    elif latest_release and snapshot_date is None:
        issues.append(f"{rel_snapshot}: session snapshot missing parseable session_date")

    if latest_release and latest_release["version"] not in snapshot_content:
        issues.append(f"{rel_snapshot}: session snapshot missing latest published release {latest_release['version']}")

    return issues


def _hot_fact_source_plugin_scope(*, host_plugin_roots_divergent):
    """Check 28c plugin-project scope (FIX-270 mixed-root fix).

    The FIX-087-era expectations (0.38.0 roadmap row, FIX-082~087 active
    task table, REQ-070~074 requirement matrix, RISK-033 / REL-013 blocker
    chain, ``### 1.0.0 依赖链`` section) assert facts about the governed
    object being the plugin project itself. They may only run in dogfood
    mode (host root == plugin root); a host project (roots diverge) must not
    be FAILed on those expectations — generic section/snapshot consistency
    still applies there.
    """
    return not host_plugin_roots_divergent()


def check_hot_fact_source_consistency(plan_tracker_path=None, *, policy, display_path, governance_dir,
                                      host_plugin_roots_divergent, is_delivered):
    """FIX-087: keep plan-tracker hot sections aligned across active release facts.

    FIX-270 (mixed-root): generic consistency (snapshot version/date vs
    plan-tracker + required hot sections) applies to every project. The
    plugin-project expectations (0.38.0 roadmap / FIX-082~087 / REQ-070~074 /
    RISK-033 / REL-013 / ``### 1.0.0 依赖链``) assert facts about the governed
    object being the plugin project and are enforced only in dogfood mode
    (see :func:`_hot_fact_source_plugin_scope`); host mode reports the
    downgrade honestly instead of FAILing host data.
    """
    plan_tracker_path = plan_tracker_path or governance_dir() / "plan-tracker.md"
    failures = []
    if not plan_tracker_path.is_file():
        return [f"{display_path(plan_tracker_path)}: plan-tracker unavailable"]
    plan_content = plan_tracker_path.read_text(encoding="utf-8")
    rel_plan = display_path(plan_tracker_path)
    _gov = governance_dir()
    if (
        "External Validation Temporary Project" in plan_content
        and "temporary external-project workspace" in plan_content
        and (_gov / "external-validation-target.json").is_file()
        and plan_tracker_path.resolve() == (_gov / "plan-tracker.md").resolve()
    ):
        print("[OK] hot fact-source consistency skipped for external validation temporary workspace")
        return []
    failures.extend(_snapshot_fact_source_issues(plan_content, plan_tracker_path,
                        policy=policy, display_path=display_path))

    plugin_scope = _hot_fact_source_plugin_scope(host_plugin_roots_divergent=host_plugin_roots_divergent)
    required_sections = [
        "## 项目配置",
        "## 当前活跃事项",
        "## 版本规划",
        "## 需求跟踪矩阵",
    ]
    if plugin_scope:
        required_sections.append("### 1.0.0 依赖链")
    sections = {heading: _markdown_section_by_prefix(plan_content, heading) for heading in required_sections}
    for heading, content in sections.items():
        if not content:
            failures.append(f"{rel_plan}: missing hot fact-source section {heading}")

    project_config = sections.get("## 项目配置", "")
    overview = _markdown_section_by_prefix(plan_content, "## 项目总览")
    active_items = sections.get("## 当前活跃事项", "")
    dependency_chain = sections.get("### 1.0.0 依赖链", "")

    # FIX-270: host mode → plugin-project expectations dormant (downgraded,
    # not FAILed); generic consistency above stays enforced.
    if not plugin_scope:
        return failures

    # Loose form (FIX-339 F-03): matches the real unclosed-bold 工作流版本
    # line; see the FIX_105_PLAN_WORKFLOW_VERSION_RE registration note above.
    version_match = re.search(r"\*\*工作流版本(?:\*\*)?:\s*([0-9]+(?:\.[0-9]+){2})", project_config)
    active_version = version_match.group(1) if version_match else ""
    if not active_version:
        failures.append(f"{rel_plan}: project config missing 工作流版本 (cannot derive active version anchor)")
    if active_version:
        active_row_text = _version_row_text(plan_content, active_version)
        version_task_ids, release_delivered, release_declared = _hot_task_ids_for_version(
            plan_content, active_version, is_delivered=is_delivered)
        # FIX-339 (REVIEW-FIX-339-CODE-R0 F-01): the released face must be
        # corroborated by a delivered REL row. The former
        # `not release_declared and roadmap self-claims 已发布` fallback is
        # removed — an uncorroborated self-claim now FAILs below instead of
        # silently upgrading the face.
        released_face = release_delivered
        if not active_row_text:
            failures.append(f"{rel_plan}: missing {active_version} roadmap row")
        elif released_face and "已发布" not in active_row_text:
            failures.append(f"{rel_plan}: {active_version} roadmap row must be 已发布 after its release task is delivered")
        elif not released_face and "已发布" in active_row_text:
            if release_declared:
                failures.append(f"{rel_plan}: {active_version} roadmap row must not claim 已发布 before its release task is delivered")
            else:
                failures.append(f"{rel_plan}: {active_version} roadmap row claims 已发布 but no delivered release task row corroborates it")
        if not any(version != active_version for version, _date_text in policy.snapshot_release_version.findall(plan_content)):
            failures.append(f"{rel_plan}: missing released roadmap row before {active_version}")
        if not released_face and re.search(re.escape(active_version) + r"[^。\n|]*已发布", project_config):
            failures.append(f"{rel_plan}: hot sections overstate {active_version} as released before its release task is delivered")
        if not released_face:
            if not version_task_ids:
                failures.append(f"{rel_plan}: active {active_version} task table has no task rows")
            for task_id in version_task_ids:
                if active_row_text and not _contains_fix_token_or_range(active_row_text, task_id):
                    failures.append(f"{rel_plan}: {active_version} roadmap row missing active task {task_id}")
        if dependency_chain:
            if policy.readiness_version not in dependency_chain:
                failures.append(f"{rel_plan}: {policy.readiness_version} dependency chain missing active blocker token {policy.readiness_version}")
            for token in ["RISK-033", "REL-013"]:
                if token in plan_content and token not in dependency_chain:
                    failures.append(f"{rel_plan}: {policy.readiness_version} dependency chain missing active blocker token {token}")
            for token in policy.release_blockers:
                if token in plan_content and token not in dependency_chain:
                    failures.append(f"{rel_plan}: {policy.readiness_version} dependency chain missing readiness release blocker token {token}")
            if released_face:
                risk033_lines = [line for line in dependency_chain.splitlines() if "RISK-033" in line]
                if risk033_lines and not any("已关闭" in line for line in risk033_lines):
                    failures.append(f"{rel_plan}: {policy.readiness_version} dependency chain still lacks RISK-033 closure after release")
            elif "不得打 1.0.0" not in dependency_chain and "不得推进 1.0.0" not in dependency_chain:
                failures.append(f"{rel_plan}: {policy.readiness_version} dependency chain missing blocking language for active release")
            # FIX-339 (REVIEW-FIX-339-CODE-R1 F-R1-05): completion lookups span
            # the task's own rows (version=None, same caliber as F-02 above) —
            # exact-anchor filtering silently no-oped these checks for
            # `或后续`/gate-reference target cells. Recall-only: this never
            # relaxes a completion judgment, it only restores recall.
            completed_active_tasks = [
                task_id for task_id in version_task_ids
                if _hot_task_is_delivered(plan_content, task_id, version=None, is_delivered=is_delivered)
            ]
            for line in dependency_chain.splitlines():
                stale_task = _line_mentions_completed_range_as_pending(line, completed_active_tasks)
                if stale_task:
                    failures.append(f"{rel_plan}: dependency chain line marks completed {stale_task} as pending: {line.strip()}")
        remaining_line = next(
            (line for line in overview.splitlines() if "RISK-033" in line and ("继续由" in line or "承载" in line)), ""
        )
        if released_face:
            if "RISK-033" in overview and "已关闭" not in overview:
                failures.append(f"{rel_plan}: project overview mentions RISK-033 after release but does not mark it closed")
        elif remaining_line:
            remaining_text = remaining_line.split("RISK-033", 1)[1] if "RISK-033" in remaining_line else remaining_line
            for task_id in _extract_task_ids(remaining_text):
                # FIX-339 (F-R1-05): version=None — see the stale-range note above.
                if _hot_task_is_delivered(plan_content, task_id, version=None,
                       is_delivered=is_delivered):
                    failures.append(f"{rel_plan}: project overview says completed {task_id} still carries RISK-033")
        elif "RISK-033" in overview and "FIX-087" not in overview:
            failures.append(f"{rel_plan}: project overview mentions RISK-033 but does not name remaining FIX-087")
        for req_id, task_ids in policy.requirements.items():
            req_row = _find_table_row_by_first_cell(plan_content, req_id)
            if not req_row:
                failures.append(f"{rel_plan}: requirement matrix missing {req_id}")
                continue
            if len(req_row) < 6:
                failures.append(f"{rel_plan}: requirement matrix {req_id} row has too few columns")
                continue
            req_status = req_row[5]
            linked = req_row[4] if len(req_row) > 4 else ""
            for task_id in task_ids:
                if task_id not in linked:
                    failures.append(f"{rel_plan}: requirement matrix {req_id} must reference {task_id}")
            # FIX-339 (REVIEW-FIX-339-CODE-R0 F-02): look at each linked task
            # row regardless of the active anchor — filtering by the active
            # version made REQ rows linked to other versions' tasks no-op.
            all_tasks_delivered = all(
                _hot_task_is_delivered(plan_content, task_id, version=None, is_delivered=is_delivered)
                for task_id in task_ids
            )
            any_task_open = any(
                _hot_task_is_open(plan_content, task_id, version=None, is_delivered=is_delivered)
                for task_id in task_ids
            )
            if all_tasks_delivered and not _status_cell_is_delivered(req_status):
                failures.append(f"{rel_plan}: requirement matrix {req_id} is not delivered while {', '.join(task_ids)} are complete")
            if any_task_open and _status_cell_is_delivered(req_status):
                failures.append(f"{rel_plan}: requirement matrix {req_id} is delivered while linked task remains open")

    for failure in failures:
        print(f"[FAIL] hot fact-source consistency: {failure}")
    if not failures:
        print("[OK] hot fact-source consistency synchronized")
    return failures
