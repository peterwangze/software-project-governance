"""Review-domain checks — extracted from verify_workflow.py in 0.70.0.

Scope (DEC-083 Phase 5c / ADR-016 / FEAT-009): the agent-team-review
protocol checks — Check 18 (agent-team review), Check 18b (governance-review
fallback policy), Check 21 (review spawn gap), Check 21b (review coverage),
Check 22 (review debt), Check 29 (M5 runtime triggers + static M5
compliance), and Check 30 (review closure state machine), plus their
review-only helpers and constants (including the review-domain
`PRODUCT_CODE_PATTERNS`, `DEGRADED_FUSE_THRESHOLD`, and
`FIX173_NAMING_NORMALIZATION_DATE`).

This is the largest of the three Phase 5 domains because 0.63.0 (FIX-173/174)
added Check 29 (M5) and Check 30 (closure) plus hardened Check 21. Per ADR-016
§3.3, the function-local `PRODUCT_CODE_PATTERNS` copies at the original L13216
/ L13304 / L13634 move inside their parent functions (no change — they are
local), and the module-level L13842 duplicate moves here as the review-domain
copy (the L11166 commit-scope copy stays in verify_workflow.py).

Functions with cross-domain callers (`_is_review_evidence`,
`_is_audit_or_review_type`, `_generic_reviewer_cells`,
`_evidence_task_type_index`) STAY in verify_workflow.py and are reached via
the deferred accessor — they are not duplicated here (ADR-016 §3.3 / §4.3
KEEP rule).

Shared helpers and constants still defined in verify_workflow.py
(`EVIDENCE_PATH`, `GOVERNANCE_DIR`, `ROOT`, `SAMPLE_PATH`, `expand_task_ids`,
`parse_completed_task_ids`, `_is_plugin_path`, `_is_audit_or_review_type`,
`_task_priority_from_table_parts`, `_parse_iso_date`,
`_evidence_task_type_index`) are reached through a deferred module reference
rather than a top-level import, so verify_workflow.py can import this module
at module load time without an import cycle.

NOTE: `PRODUCT_CODE_PATTERNS` is OWNED by this module (the review-domain copy
moves here per ADR-016 §3.3 — the commit-scope copy at the original v_w
L11166 stays in verify_workflow.py). It is therefore NOT in `_SHARED_NAMES`;
moved review functions reference it as a bare module-level name and it
resolves to the constant defined in this module.

See docs/architecture/ADR-016-verify-phase5-extraction-0.70.0.md for the
design and the line-number baseline used during extraction.
"""

import re
import json
import sys
from pathlib import Path
from datetime import date

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
    "ROOT",
    "SAMPLE_PATH",
    "expand_task_ids",
    "parse_completed_task_ids",
    "_is_plugin_path",
    "_is_audit_or_review_type",
    "_task_priority_from_table_parts",
    "_parse_iso_date",
    "_evidence_task_type_index",
)


def _resolve_shared():
    """Refresh this module's globals with shared names from verify_workflow.

    Re-fetches on EVERY call (not cached) so test-time monkey-patching of
    verify_workflow attributes (e.g. `patch.object(vw, "EVIDENCE_PATH", ...)`,
    `patch.object(vw, "SAMPLE_PATH", ...)`, or swapping `_is_plugin_path`)
    propagates into this module's bare-name lookups. The cost is negligible:
    these checks run once per CLI invocation, not in a hot loop, and `getattr`
    on a cached module reference is cheap. This mirrors how checks.manifest
    re-resolves `ROOT = _root()` inside each function body (Phase 1 precedent).
    """
    vw = _vw()
    g = globals()
    for _name in _SHARED_NAMES:
        g[_name] = getattr(vw, _name)
    # REVIEW_FALLBACK_POLICY_{REQUIRED,OPTIONAL}_FILES are derived from ROOT,
    # which is now resolved. They cannot be defined at module load time
    # (ROOT is unavailable then), so re-populate them on every call.
    g["REVIEW_FALLBACK_POLICY_REQUIRED_FILES"] = [g["ROOT"] / "commands/governance-review.md"]
    g["REVIEW_FALLBACK_POLICY_OPTIONAL_FILES"] = [
        g["ROOT"] / "project/e2e-test-project/commands/governance-review.md",
    ]


# ── Domain constants and functions (moved verbatim from verify_workflow.py) ──

def check_m5_compliance():
    """Check M5 AskUserQuestion compliance -- static anti-pattern detection (enhanced).

    Detects:
    1. Actionable inline-question instructions in active project entry files:
       a line must both contain question-like text and teach the agent to ask
       the user inline.  Historical governance records, plugin source files,
       fixtures, and ordinary checklists are excluded.
    2. Option-list patterns without AskUserQuestion:
       - Matches (1) / (a) style options + "选择" context, but no "AskUserQuestion"
       - Detects source files that instruct agents to output choice menus as text
    3. Bootstrap coverage: governance-init.md template contains AskUserQuestion rule
    4. Interaction boundary: interaction-boundary.md exists and references AskUserQuestion
    5. Bootstrap template contains M5 pre-output guard (SELF-CHECK item 4)

    This CANNOT detect runtime M5 violations (actual inline questions in conversation).
    It catches the ROOT CAUSE: source files that teach or allow agents to use inline text.
    """
    _resolve_shared()
    issues = []
    skills_dir = ROOT / "skills" / "software-project-governance"

    # -- Check 1: Actionable inline question instructions in active entry files --
    import glob as _glob
    inline_patterns_cn = ["吗？", "？", "要不要", "是否", "确认吗", "需要我", "你想"]
    inline_patterns_en = ["Should I", "Do you want"]
    ask_action_re = re.compile(
        r"(询问用户|问用户|向用户提问|直接问|输出.*[？?]|回复.*[？?]|ask the user|"
        r"inline question|text question)",
        re.IGNORECASE,
    )
    benign_context_re = re.compile(
        r"(SELF-CHECK|自查|检查|检测|是否包含|是否到达|是否已经|是否知道|"
        r"是否有|是否已|是否可|是否受|是否支持|表头|"
        r"checklist|coverage|PASS|WARN|FAIL)"
    )

    scan_files = []
    # Active user/project entry files only. Historical governance records,
    # archive data, and e2e/plugin fixtures are not M5 teaching surfaces.
    for pattern in ["AGENTS.md", "CLAUDE.md", ".governance/CLAUDE.md", "docs/**/*.md"]:
        for f in _glob.glob(str(ROOT / pattern), recursive=True):
            scan_files.append(Path(f))

    seen_paths = set()
    scan_files_dedup = []
    for f in scan_files:
        if str(f) not in seen_paths:
            seen_paths.add(str(f))
            scan_files_dedup.append(f)
    scan_files = scan_files_dedup

    # FIX-054: Filter out plugin scope directories to avoid false positives
    # from legitimate checklists in plugin SKILL.md files (e.g., checklist items
    # with Chinese question marks like "是否评估了至少 2 个候选方案?").
    # PLUGIN_SCOPE_DIRS is synced with cleanup.py.
    scan_files = [
        f for f in scan_files
        if not _is_plugin_path(str(f.relative_to(ROOT)))
        and "/archive/" not in str(f.relative_to(ROOT)).replace("\\", "/")
        and not str(f.relative_to(ROOT)).replace("\\", "/").startswith("project/e2e-test-project/")
    ]

    for md_file in scan_files:
        if not md_file.is_file():
            continue
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue
        rel_path = str(md_file.relative_to(ROOT)).replace("\\", "/")

        for i, line in enumerate(content.splitlines(), 1):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            if "AskUserQuestion" in line:
                continue

            for kw in inline_patterns_cn:
                if kw in line_stripped:
                    if not ask_action_re.search(line_stripped):
                        continue
                    if benign_context_re.search(line_stripped):
                        continue
                    issues.append({
                        "type": "m5_inline_question_cn",
                        "file": rel_path,
                        "line": i,
                        "text": line_stripped[:120],
                        "severity": "BLOCKING",
                        "pattern": kw,
                        "fix": "MUST use AskUserQuestion tool instead of inline text questions (M5.1)"
                    })
                    break

            for kw in inline_patterns_en:
                if kw.lower() in line_stripped.lower():
                    if not ask_action_re.search(line_stripped):
                        continue
                    if benign_context_re.search(line_stripped):
                        continue
                    issues.append({
                        "type": "m5_inline_question_en",
                        "file": rel_path,
                        "line": i,
                        "text": line_stripped[:120],
                        "severity": "WARNING",
                        "pattern": kw,
                        "fix": "MUST use AskUserQuestion tool instead of inline text questions (M5.1)"
                    })
                    break

    # -- Check 1b: Option-list patterns without AskUserQuestion --
    option_list_re = re.compile(r'([(][1-9][0-9]*[)]|[(][a-z][)])')
    for md_file in scan_files:
        if not md_file.is_file():
            continue
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue
        rel_path = str(md_file.relative_to(ROOT)).replace("\\", "/")

        has_option_list = bool(option_list_re.search(content))
        has_choice_context = any(kw in content for kw in ("选择", "choose", "select", "选项"))
        has_askuserquestion = "AskUserQuestion" in content

        if has_option_list and has_choice_context and not has_askuserquestion:
            for i, line in enumerate(content.splitlines(), 1):
                if option_list_re.search(line) and any(
                    kw in line for kw in ("选择", "choose", "select", "选项")
                ):
                    issues.append({
                        "type": "m5_option_list_no_auq",
                        "file": rel_path,
                        "line": i,
                        "text": line.strip()[:120],
                        "severity": "BLOCKING",
                        "fix": "Option list detected with choice context but no AskUserQuestion - agent may output inline choice menus (M5 violation)"
                    })
                    break

    # Check 2: Bootstrap template (governance-init.md) contains AskUserQuestion rule
    bootstrap_template = ROOT / "commands" / "governance-init.md"
    if bootstrap_template.is_file():
        content = bootstrap_template.read_text(encoding="utf-8")
        if "AskUserQuestion" not in content:
            issues.append({
                "type": "m5_bootstrap_missing",
                "file": "commands/governance-init.md",
                "line": 0,
                "text": "Bootstrap template does not contain AskUserQuestion rule",
                "severity": "WARNING",
                "fix": "Add M5 AskUserQuestion rule to governance-init.md bootstrap template"
            })
    else:
        issues.append({
            "type": "m5_bootstrap_missing",
            "file": "commands/governance-init.md",
            "line": 0,
            "text": "governance-init.md not found",
            "severity": "ERROR",
            "fix": "Create governance-init.md with bootstrap template"
        })

    # Check 3: interaction-boundary.md exists and references AskUserQuestion
    ib_file = skills_dir / "references" / "interaction-boundary.md"
    if ib_file.is_file():
        content = ib_file.read_text(encoding="utf-8")
        if "AskUserQuestion" not in content:
            issues.append({
                "type": "m5_ib_missing",
                "file": str(ib_file.relative_to(ROOT)),
                "line": 0,
                "text": "interaction-boundary.md does not reference AskUserQuestion",
                "severity": "ERROR",
                "fix": "Add AskUserQuestion binding to interaction types in interaction-boundary.md"
            })
    else:
        issues.append({
            "type": "m5_ib_missing",
            "file": "skills/software-project-governance/references/interaction-boundary.md",
            "line": 0,
            "text": "interaction-boundary.md not found",
            "severity": "ERROR",
            "fix": "Create interaction-boundary.md with AskUserQuestion binding rules"
        })

    # Check 4: Bootstrap template (governance-init.md) contains M5 pre-output guard
    if bootstrap_template.is_file():
        content = bootstrap_template.read_text(encoding="utf-8")
        m5_selfcheck_patterns = [
            "我即将输出的文本是否包含向用户提问的问句",
            "M5.1",
            "AskUserQuestion",
        ]
        has_selfcheck_item4 = all(p in content for p in m5_selfcheck_patterns)
        if not has_selfcheck_item4:
            issues.append({
                "type": "m5_selfcheck_missing",
                "file": "commands/governance-init.md",
                "line": 0,
                "text": "Bootstrap template missing M5 pre-output guard. Without this, agent's natural conversational patterns can produce M5.1 violations.",
                "severity": "BLOCKING",
                "fix": "Add SELF-CHECK to governance-init.md bootstrap template"
            })
    else:
        issues.append({
            "type": "m5_selfcheck_missing",
            "file": "commands/governance-init.md",
            "line": 0,
            "text": "Bootstrap template not found",
            "severity": "BLOCKING",
            "fix": "Create governance-init.md with SELF-CHECK in bootstrap template"
        })

    return {"issues": issues, "total_checks": 5}


# ── SYSGAP-035: Agent Team Review Check (Check 19) ────────────────

DEGRADED_REVIEW_MARKERS = (
    "不构成独立审查",
    "不得计入审查通过",
    "不得解锁",
)
REVIEWER_ROLE_MARKERS = (
    "Reviewer",
    "审查 Agent",
    "审查Agent",
    "审查人",
    "复审",
)
SELF_REVIEW_AUTHOR_MARKERS = (
    "Coordinator",
    "Developer",
    "Governance Developer",
)


def _review_text_is_degraded(text):
    """Return True when a review-like row is only degraded/runtime evidence."""
    _resolve_shared()
    if "DEGRADED_EVIDENCE" in text:
        return True
    return all(marker in text for marker in DEGRADED_REVIEW_MARKERS)


def _review_text_has_reviewer_marker(text):
    _resolve_shared()
    return any(marker in text for marker in REVIEWER_ROLE_MARKERS)


def _review_entry_skip_reason(author, description, file_location, notes=""):
    """Classify review-like evidence that must not count as independent review."""
    _resolve_shared()
    combined = " ".join([author, description, file_location, notes])
    if _review_text_is_degraded(combined):
        return "degraded evidence does not count as independent review"

    if (
        any(marker in author for marker in SELF_REVIEW_AUTHOR_MARKERS)
        and "Reviewer" not in author
        and "审查" not in author
    ):
        return "self-review evidence does not count as independent review"

    if not _review_text_has_reviewer_marker(combined):
        return "review evidence lacks independent reviewer marker"

    return ""


def _parse_review_coverage_details(evidence_path=None, review_dir=None):
    """Parse independent review coverage and ignored review-like entries."""
    _resolve_shared()
    covered = {}
    ignored = []
    evidence_path = Path(evidence_path) if evidence_path is not None else EVIDENCE_PATH
    review_dir = Path(review_dir) if review_dir is not None else evidence_path.parent

    if not evidence_path.is_file():
        return covered, ignored

    evidence_content = evidence_path.read_text(encoding="utf-8")

    def add_coverage(source, raw_text):
        for match in re.finditer(r"([A-Z]+-\d+(?:~\d+)?)", raw_text):
            raw = match.group(1)
            for inner_id in expand_task_ids(raw):
                if not inner_id.startswith("REVIEW-"):
                    covered.setdefault(inner_id, []).append(source)

    # 1. Scan evidence-log for REVIEW evidence entries.
    for line in evidence_content.split("\n"):
        line = line.strip()
        if not (line.startswith("| EVD-") or line.startswith("| REVIEW-")):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 8:
            continue
        evd_id = parts[1]
        raw_ids = parts[2]
        evd_type = parts[4] if len(parts) > 4 else ""
        description = parts[5] if len(parts) > 5 else ""
        file_location = parts[6] if len(parts) > 6 else ""
        author = parts[7] if len(parts) > 7 else ""
        notes = " ".join(parts[8:])

        # REVIEW evidence: task ID starts with REVIEW- or type is Code Review/审查.
        is_review_entry = (
            evd_id.startswith("REVIEW-")
            or raw_ids.startswith("REVIEW-")
            or evd_type == "Code Review"
            or evd_type == "审查"
            or "审查" in evd_type
        )
        if not is_review_entry:
            continue

        skip_reason = _review_entry_skip_reason(author, description, file_location, notes)
        if skip_reason:
            ignored.append({"source": evd_id, "reason": skip_reason, "task_ids": raw_ids})
            continue

        for inner_id in expand_task_ids(raw_ids) if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids) else []:
            if not inner_id.startswith("REVIEW-"):
                covered.setdefault(inner_id, []).append(evd_id)

        if raw_ids.startswith("REVIEW-"):
            # Extract covered task IDs from REVIEW- prefix.
            add_coverage(evd_id, raw_ids[len("REVIEW-"):])

        # Check description and file_location for task references.
        add_coverage(evd_id, description + " " + file_location)

    # 2. Scan review-*.md files for task references.
    if review_dir.is_dir():
        for review_file in review_dir.glob("review-*.md"):
            try:
                content = review_file.read_text(encoding="utf-8")
                skip_reason = _review_entry_skip_reason("", content, review_file.name)
                if skip_reason:
                    ignored.append({
                        "source": review_file.name,
                        "reason": skip_reason,
                        "task_ids": "",
                    })
                    continue
                add_coverage(review_file.name, content)
            except (IOError, OSError):
                pass

    return covered, ignored


def _parse_review_covered_tasks(evidence_path=None, review_dir=None):
    """Parse evidence-log and review-*.md files to find all tasks covered by reviews.

    Returns dict: task_id -> list of review sources (evidence IDs or file names).
    """
    _resolve_shared()
    covered, _ = _parse_review_coverage_details(evidence_path=evidence_path, review_dir=review_dir)
    return covered


def check_agent_team_review():
    """SYSGAP-035: Check 19 — Agent Team review completeness.

    For completed tasks involving product code changes, verify that an
    independent code review was performed. Review evidence is identified
    by REVIEW-prefixed task IDs in evidence-log or review-*.md files
    in .governance/.

    Product code detection: evidence file locations outside .governance/
    (skills/, agents/, infra/, commands/, adapters/, .claude-plugin/,
    .codex-plugin/, .agents/, project/).

    Returns dict with total_tasks, reviewed, unreviewed, review_gap_tasks, pass.
    """
    _resolve_shared()
    PRODUCT_CODE_PATTERNS = [
        "skills/", "agents/", "infra/", "commands/",
        "adapters/", ".claude-plugin/", ".codex-plugin/", ".agents/",
        "project/",
    ]

    result = {
        "total_tasks": 0,
        "reviewed": 0,
        "unreviewed": 0,
        "review_gap_tasks": [],
        "ignored_review_entries": [],
        "pass": True,
    }

    completed = parse_completed_task_ids()
    if not completed:
        return result

    # Read evidence-log
    if not EVIDENCE_PATH.is_file():
        return result
    evidence_content = EVIDENCE_PATH.read_text(encoding="utf-8")

    # Build map: task_id -> list of evidence metadata
    task_file_locations = {}
    for line in evidence_content.split("\n"):
        line = line.strip()
        if not line.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 8:
            continue
        raw_ids = parts[2]
        evd_type = parts[4] if len(parts) > 4 else ""
        file_location = parts[6] if len(parts) > 6 else ""
        for tid in expand_task_ids(raw_ids) if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids) else []:
            task_file_locations.setdefault(tid, []).append({
                "file_location": file_location,
                "evd_type": evd_type,
            })

    # Build review coverage map. Degraded runtime evidence and self-review rows
    # are retained as ignored diagnostics, but never unlock completed product work.
    review_covered, ignored_reviews = _parse_review_coverage_details()
    result["ignored_review_entries"] = ignored_reviews

    for task_id in sorted(completed):
        entries = task_file_locations.get(task_id, [])
        if not entries:
            continue

        is_product_code = any(
            any(pat in e["file_location"] for pat in PRODUCT_CODE_PATTERNS)
            and not _is_audit_or_review_type(e["evd_type"])
            for e in entries
        )
        if not is_product_code:
            continue

        result["total_tasks"] += 1
        if task_id in review_covered:
            result["reviewed"] += 1
        else:
            result["unreviewed"] += 1
            result["review_gap_tasks"].append(task_id)

    result["pass"] = result["unreviewed"] == 0
    return result


# ── SYSGAP-042: Review Debt Check (Check 21) ─────────────────────

# FIX-174 (DEC-094): Check 21 strengthening — review_spawn_gap + degraded fuse.
# Three-source cross check (M7.4 step 4.5b DIFF-GATED spawn guard):
#   Source A: git diff product-code paths (PRODUCT_CODE_PATTERNS below)
#   Source B: SKILL.md § Agent dispatch routing table "后置审查 Agent(s)" column
#   Source C: evidence-log REVIEW-{task_id} APPROVED coverage
# FAIL: A∧B∧¬C  (product code diff + routing requires post-review + no APPROVED review)
# FAIL: same task_id degraded count ≥ 3 (DEC-094 §3.3 + step 4.6 fuse)

ROUTING_FILE_CANDIDATES = [
    "skills/software-project-governance/references/methodology-routing.md",
    "skills/software-project-governance/SKILL.md",
]

# Markers that mark a REVIEW evidence row as "degraded mode" (DEC-090 three-word set).
DEGRADED_MARKERS = ("degraded", "coordinator-降级", "sod-降级")

# Fuse threshold (DEC-094 §3.3 + behavior-protocol.md M7.4 step 4.6 degraded limit).
DEGRADED_FUSE_THRESHOLD = 3


def _parse_routing_post_review_table():
    """Parse the "后置审查 Agent(s)" column from the routing table.

    Returns dict: task_type -> post_review_agents_string (raw cell value, stripped).
    Reads methodology-routing.md first (authoritative method-layer table), then
    SKILL.md § Agent dispatch routing as fallback. Em-dash "—" cells are preserved
    verbatim so callers can distinguish "no post review" (—) from absent rows.
    """
    _resolve_shared()
    table = {}
    for rel in ROUTING_FILE_CANDIDATES:
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (IOError, OSError):
            continue
        # Detect header row that contains "后置审查" so we locate the column index.
        lines = content.splitlines()
        header_idx = None
        post_col = None
        type_col = 0
        for i, line in enumerate(lines):
            if "|" not in line or "后置审查" not in line:
                continue
            cells = [c.strip() for c in line.split("|")]
            # Locate the "后置审查" cell index and the "任务类型" cell index.
            for j, cell in enumerate(cells):
                if "后置审查" in cell:
                    post_col = j
                if "任务类型" in cell:
                    type_col = j
            if post_col is not None:
                header_idx = i
                break
        if header_idx is None or post_col is None:
            continue
        for line in lines[header_idx + 1:]:
            stripped = line.strip()
            if not stripped.startswith("|") or "---" in stripped:
                # blank line or separator row ends this table block
                if stripped and not stripped.startswith("|"):
                    break
                continue
            cells = [c.strip() for c in line.split("|")]
            if len(cells) <= max(type_col, post_col):
                continue
            task_type = cells[type_col]
            post_agents = cells[post_col]
            if not task_type or task_type.startswith("---"):
                continue
            # First file wins per task_type (methodology-routing.md is authoritative).
            table.setdefault(task_type, post_agents)
    return table


def _routing_post_review_for_task_type(task_type, routing_table=None):
    """Return the post-review Agent(s) cell for a task type, or '' if unknown.

    The routing table is matched by substring containment (the plan-tracker
    task type strings are free-form, e.g. "新功能开发" may appear as the exact
    row label, while "治理基础设施/工作流本体修改" is one row). We pick the
    longest routing-table key that is contained in the task_type (or vice-versa)
    so multi-keyword types resolve correctly.
    """
    _resolve_shared()
    if routing_table is None:
        routing_table = _parse_routing_post_review_table()
    if not task_type:
        return ""
    best_key = None
    for key in routing_table:
        if not key:
            continue
        if key == task_type:
            best_key = key
            break
        if key and (key in task_type or task_type in key):
            if best_key is None or len(key) > len(best_key):
                best_key = key
    if best_key is None:
        return ""
    return routing_table[best_key]


def _is_post_review_exempt(post_review_cell):
    """Return True iff the routing cell marks this task type as no-post-review.

    Exempt cells are em-dash "—" (possibly with surrounding whitespace) or empty.
    """
    _resolve_shared()
    if not post_review_cell:
        return True
    cell = post_review_cell.strip()
    # em-dash variants (—, --, -) and the literal "无" marker
    return cell in ("—", "--", "-", "无", "—（无）") or cell.startswith("—")


def _count_degraded_reviews_for_task(task_id, evidence_content):
    """Count REVIEW evidence rows for task_id that are tagged degraded.

    A REVIEW row is counted as degraded ONLY when a degraded marker
    (DEC-090 three-word set) appears as a structural tag — i.e. in the
    author / notes / conclusion metadata columns or as an explicit tag like
    `degraded:` / `[degraded]` / `(coordinator-降级)` — NOT when the marker
    merely appears inside the free-text description column (parts[5]).

    This avoids false positives where a legitimately APPROVED independent
    review's description happens to discuss product runtime wording such as
    "degraded / blocked / environment-dependent".

    Per behavior-protocol.md M7.4 step 4.6 degraded limit + DEC-090.
    """
    _resolve_shared()
    count = 0
    # Explicit-tag patterns: marker used as a structural label, not prose.
    explicit_tag_re = re.compile(
        r"(?:degraded|coordinator-降级|sod-降级)\s*[:：\]\)]"
        r"|\[(?:degraded|coordinator-降级|sod-降级)\]"
        r"|\((?:degraded|coordinator-降级|sod-降级)\)",
        re.IGNORECASE,
    )
    for line in evidence_content.split("\n"):
        line = line.strip()
        if not (line.startswith("| REVIEW-") or line.startswith("| EVD-")):
            continue
        # Must reference this task (raw ids column or description mentions REVIEW-{task_id})
        if task_id not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 8:
            continue
        # description column is parts[5] — excluded from marker scan to avoid
        # prose false positives. Scan author (parts[7]) + tail notes (parts[9+]).
        metadata = " ".join(parts[7:8]) + " " + " ".join(parts[9:])
        tail = " ".join(parts[8:])
        is_degraded = False
        if explicit_tag_re.search(tail):
            is_degraded = True
        elif any(marker in metadata for marker in DEGRADED_MARKERS):
            is_degraded = True
        if is_degraded:
            count += 1
    return count


def check_review_debt():
    """SYSGAP-042: Check 21 — Review debt.

    Check all product-code tasks for review debt: tasks that have execution
    evidence in evidence-log but lack corresponding review evidence.

    Product code detection: evidence file locations outside .governance/
    (skills/, agents/, infra/, commands/, adapters/, .claude-plugin/,
    .codex-plugin/, .agents/, project/).

    Returns dict with total_tasks, review_debt_count, review_debt_tasks, pass.
    """
    _resolve_shared()
    PRODUCT_CODE_PATTERNS = [
        "skills/", "agents/", "infra/", "commands/",
        "adapters/", ".claude-plugin/", ".codex-plugin/", ".agents/",
        "project/",
    ]

    result = {
        "total_tasks": 0,
        "review_debt_count": 0,
        "review_debt_tasks": [],
        # FIX-174 (DEC-094): spawn-gap & degraded-fuse violations (subset of
        # review_debt_tasks; tracked separately so callers can show distinct
        # diagnostic reasons).
        "spawn_gap_tasks": [],
        "degraded_fuse_tasks": [],
        "pass": True,
    }

    if not SAMPLE_PATH.is_file():
        return result

    # 1. Parse all tasks from plan-tracker tracking tables
    plan_content = SAMPLE_PATH.read_text(encoding="utf-8")
    all_task_ids = set()
    for line in plan_content.split("\n"):
        line_stripped = line.strip()
        if not line_stripped.startswith("| ") or "---" in line_stripped:
            continue
        m = re.search(r"\|\s*(?:\*\*)?([A-Z]+-\d+)(?:\*\*)?\s*\|", line_stripped)
        if not m:
            continue
        all_task_ids.add(m.group(1))

    if not all_task_ids:
        return result

    # 2. Build evidence map: task_id -> list of (evd_id, evd_type, file_location)
    if not EVIDENCE_PATH.is_file():
        return result
    evidence_content = EVIDENCE_PATH.read_text(encoding="utf-8")

    task_evidence = {}  # task_id -> [{evd_id, evd_type, file_location, description}]
    for line in evidence_content.split("\n"):
        line = line.strip()
        if not line.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 8:
            continue
        evd_id = parts[1]
        raw_ids = parts[2]
        evd_type = parts[4] if len(parts) > 4 else ""
        description = parts[5] if len(parts) > 5 else ""
        file_location = parts[6] if len(parts) > 6 else ""

        covered_ids = expand_task_ids(raw_ids) if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids) else set()
        for tid in covered_ids:
            task_evidence.setdefault(tid, []).append({
                "evd_id": evd_id,
                "evd_type": evd_type,
                "file_location": file_location,
                "description": description,
            })

    # 3. Build review coverage map (same logic as _parse_review_covered_tasks)
    review_covered = _parse_review_covered_tasks()

    # 4. For each product-code task: check if it has execution evidence but no review evidence
    for task_id in sorted(all_task_ids):
        entries = task_evidence.get(task_id, [])
        if not entries:
            continue

        # Determine if this task touched product code
        is_product_code = any(
            any(pat in e["file_location"] for pat in PRODUCT_CODE_PATTERNS)
            and not _is_audit_or_review_type(e["evd_type"])
            for e in entries
        )
        if not is_product_code:
            continue

        result["total_tasks"] += 1

        # FIX-174 (DEC-094): degraded-fuse check — even tasks WITH review
        # coverage must FAIL when the same task_id accumulated ≥ 3 degraded
        # REVIEW rows (DEC-090 three-marker set, behavior-protocol M7.4 step
        # 4.6 degraded limit). Count is derived from evidence-log only.
        degraded_count = _count_degraded_reviews_for_task(task_id, evidence_content)
        if degraded_count >= DEGRADED_FUSE_THRESHOLD:
            result["degraded_fuse_tasks"].append(task_id)

        # Check for review evidence
        if task_id in review_covered:
            # Has review — no debt. But degraded-fuse violations above still
            # contribute to the FAIL verdict via degraded_fuse_tasks.
            continue  # Has review — no debt

        # No review evidence found — this is review debt.
        # For product-code tasks the routing table (methodology-routing.md /
        # SKILL.md § Agent dispatch routing) always mandates a non-— post
        # review agent (every product-code row has Code Reviewer / Design
        # Reviewer / etc.), so the absence of REVIEW coverage is exactly the
        # M7.4 step 4.5b DIFF-GATED spawn-gap violation (source A∧B∧¬C).
        result["review_debt_count"] += 1
        result["review_debt_tasks"].append(task_id)
        result["spawn_gap_tasks"].append(task_id)

    result["pass"] = (
        result["review_debt_count"] == 0
        and len(result["degraded_fuse_tasks"]) == 0
    )
    return result


def check_review_spawn_gap(task_id, git_diff_paths, routing_post_review,
                           review_entries, evidence_degraded_count=0):
    """FIX-174 (DEC-094): pure three-source spawn-gap judge for fixture tests.

    Mirrors the M7.4 step 4.5b DIFF-GATED spawn guard logic in a side-effect-
    free form so AUDIT-128 fixtures (FIX21-*) can exercise the exact verdict
    without spinning up real plan-tracker / evidence-log / git state.

    Sources:
      A (git_diff_paths): iterable of repo-relative file paths touched.
      B (routing_post_review): raw routing-table cell value for this task type
         (e.g. "Code Reviewer" or "—"). Empty/— = exempt.
      C (review_entries): iterable of review entry dicts with a "conclusion"
         key. An APPROVED entry satisfies source C.
      evidence_degraded_count: number of degraded REVIEW rows already in the
         evidence-log for this task (drives the DEC-094 §3.3 fuse).

    Returns dict: {result, reason, source_a, source_b, source_c, degraded_count}
      result ∈ {"FAIL", "PASS"}
    """
    _resolve_shared()
    product_code_patterns = [
        "skills/", "agents/", "infra/", "commands/",
        "adapters/", ".claude-plugin/", ".codex-plugin/", ".agents/",
        "project/",
    ]
    # Governance-record paths that never trigger the spawn guard (exemptions).
    exempt_prefixes = (".governance/", "docs/", "project/CHANGELOG.md")

    # Source A: any touched path is product code (and not pure governance).
    def _is_product_code(p):
        norm = p.replace("\\", "/")
        if any(norm.startswith(ex) or ex in norm for ex in exempt_prefixes):
            return False
        return any(pat in norm for pat in product_code_patterns)

    source_a = any(_is_product_code(p) for p in (git_diff_paths or []))

    # Source B: routing table mandates a post-review agent (non-—, non-empty).
    source_b = not _is_post_review_exempt(routing_post_review)

    # Source C: at least one APPROVED review entry exists.
    source_c = any(
        str(e.get("conclusion", "")).strip().upper() == "APPROVED"
        for e in (review_entries or [])
    )

    degraded_count = int(evidence_degraded_count or 0)

    # DEC-094 §3.3 + step 4.6 degraded fuse: ≥ 3 degraded reviews → FAIL.
    if degraded_count >= DEGRADED_FUSE_THRESHOLD:
        return {
            "result": "FAIL",
            "reason": f"degraded count = {degraded_count} ≥ {DEGRADED_FUSE_THRESHOLD} "
                      f"— repeated degradation bypassing review, force FAIL",
            "source_a": source_a,
            "source_b": source_b,
            "source_c": source_c,
            "degraded_count": degraded_count,
        }

    # Three-source spawn gap: A ∧ B ∧ ¬C → FAIL.
    if source_a and source_b and not source_c:
        return {
            "result": "FAIL",
            "reason": "product-code diff + routing requires post-review + "
                      "no APPROVED REVIEW evidence = review_spawn_gap",
            "source_a": source_a,
            "source_b": source_b,
            "source_c": source_c,
            "degraded_count": degraded_count,
        }

    # Otherwise PASS. Pick the most informative PASS reason.
    if not source_a:
        reason = "source A not satisfied — no product-code diff (governance-only)"
    elif _is_post_review_exempt(routing_post_review):
        reason = "source B exempt — routing '后置审查 Agent(s)' cell is —"
    elif source_c:
        reason = "source C satisfied — APPROVED REVIEW evidence present"
    else:
        reason = "no spawn-gap violation"
    return {
        "result": "PASS",
        "reason": reason,
        "source_a": source_a,
        "source_b": source_b,
        "source_c": source_c,
        "degraded_count": degraded_count,
    }


# ── FIX-037: Review Coverage Check (Check 22) ──────────────────────

PRODUCT_CODE_PATTERNS = [
    "skills/", "agents/", "infra/", "commands/",
    "adapters/", ".claude-plugin/", ".codex-plugin/", ".agents/",
    "project/",
]


def check_review_coverage():
    """FIX-037: Check 22 — Review coverage for product code tasks.

    Counts product code tasks (excluding P2 priority) and verifies what
    fraction has review evidence. Uses _parse_review_covered_tasks() to
    determine which tasks have been independently reviewed.

    Returns dict with total_tasks, reviewed, unreviewed, unreviewed_tasks,
    coverage_pct, pass.
    """
    _resolve_shared()
    result = {
        "total_tasks": 0,
        "reviewed": 0,
        "unreviewed": 0,
        "unreviewed_tasks": [],
        "coverage_pct": 0.0,
        "pass": True,
    }

    if not SAMPLE_PATH.is_file():
        return result
    if not EVIDENCE_PATH.is_file():
        return result

    plan_content = SAMPLE_PATH.read_text(encoding="utf-8")

    # ── Parse task priorities from plan-tracker tracking tables ──
    task_priorities = {}          # task_id -> priority string (P0/P1/P2)
    all_task_ids = set()
    for line in plan_content.split("\n"):
        line_s = line.strip()
        if not line_s.startswith("| ") or "---" in line_s:
            continue
        m = re.search(r"\|\s*(?:\*\*)?([A-Z]+-\d+)(?:\*\*)?\s*\|", line_s)
        if not m:
            continue
        task_id = m.group(1)
        all_task_ids.add(task_id)
        parts = [p.strip() for p in line.split("|")]
        priority = _task_priority_from_table_parts(parts)
        if priority:
            task_priorities[task_id] = priority

    if not all_task_ids:
        return result

    # ── Build evidence map from evidence-log ──
    evidence_content = EVIDENCE_PATH.read_text(encoding="utf-8")
    task_file_locations = {}
    for line in evidence_content.split("\n"):
        line = line.strip()
        if not line.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 8:
            continue
        raw_ids = parts[2]
        evd_type = parts[4] if len(parts) > 4 else ""
        file_location = parts[6] if len(parts) > 6 else ""
        for tid in expand_task_ids(raw_ids) if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids) else []:
            task_file_locations.setdefault(tid, []).append({
                "file_location": file_location,
                "evd_type": evd_type,
            })

    # ── Build review coverage map ──
    review_covered = _parse_review_covered_tasks()

    # ── Count product-code tasks and check review coverage ──
    for task_id in sorted(all_task_ids):
        # Exclude P2 priority tasks
        priority = task_priorities.get(task_id, "")
        if priority == "P2":
            continue

        entries = task_file_locations.get(task_id, [])
        if not entries:
            continue

        is_product_code = any(
            any(pat in e["file_location"] for pat in PRODUCT_CODE_PATTERNS)
            and not _is_audit_or_review_type(e["evd_type"])
            for e in entries
        )
        if not is_product_code:
            continue

        result["total_tasks"] += 1
        if task_id in review_covered:
            result["reviewed"] += 1
        else:
            result["unreviewed"] += 1
            result["unreviewed_tasks"].append(task_id)

    if result["total_tasks"] > 0:
        result["coverage_pct"] = round((result["reviewed"] / result["total_tasks"]) * 100, 1)
    result["pass"] = result["unreviewed"] == 0
    return result


# ── FIX-061: governance-review Reviewer fallback policy ───────────
# NOTE: REVIEW_FALLBACK_POLICY_REQUIRED_FILES / _OPTIONAL_FILES are derived
# from ROOT, which is a deferred `_vw()`-resolved name (not available at
# module load time). They are populated by `_resolve_shared()` on first
# call into this module — see the special-case at the end of that function.
REVIEW_FALLBACK_POLICY_REQUIRED_FILES = []

REVIEW_FALLBACK_POLICY_OPTIONAL_FILES = []

_REVIEW_FALLBACK_FORBIDDEN_PATTERNS = [
    r"降级为\s*Coordinator\s*执行审查",
    r"Coordinator\s*执行审查",
    r"Coordinator\s*自行执行审查",
]

_REVIEW_FALLBACK_REQUIRED_SNIPPETS = [
    "REVIEW-ERR-003",
    "general-purpose",
    "Reviewer role prompt",
    "BLOCKED",
    "degraded evidence",
    "不构成独立审查",
    "不得解锁",
    "Coordinator MUST NOT",
]


def check_governance_review_fallback_policy(required_paths=None, optional_paths=None):
    """FIX-061: prevent Coordinator self-review fallback in /governance-review.

    REVIEW-ERR-003 must require Reviewer spawn/fallback first; if no Reviewer
    runtime is available, the command may only block or emit degraded evidence
    that cannot count as independent review or unlock delivery.
    """
    _resolve_shared()
    result = {
        "files_checked": 0,
        "optional_skipped": [],
        "issues": [],
        "pass": True,
    }
    required = list(
        REVIEW_FALLBACK_POLICY_REQUIRED_FILES if required_paths is None else required_paths
    )
    optional = list(
        REVIEW_FALLBACK_POLICY_OPTIONAL_FILES if optional_paths is None else optional_paths
    )

    def _path_label(path):
        if path.is_absolute():
            try:
                return path.relative_to(ROOT).as_posix()
            except ValueError:
                return path.as_posix()
        return str(path).replace("\\", "/")

    def _check_file(path, optional_file=False):
        rel = _path_label(path)
        if not path.is_file():
            if optional_file:
                result["optional_skipped"].append(rel)
                return
            result["issues"].append({
                "file": rel,
                "type": "missing_file",
                "detail": "governance-review command file not found",
            })
            return

        result["files_checked"] += 1
        content = path.read_text(encoding="utf-8")
        for pattern in _REVIEW_FALLBACK_FORBIDDEN_PATTERNS:
            if re.search(pattern, content):
                result["issues"].append({
                    "file": rel,
                    "type": "coordinator_self_review_fallback",
                    "detail": f"forbidden fallback pattern found: {pattern}",
                })

        for snippet in _REVIEW_FALLBACK_REQUIRED_SNIPPETS:
            if snippet not in content:
                result["issues"].append({
                    "file": rel,
                    "type": "missing_policy_marker",
                    "detail": f"missing required marker: {snippet}",
                })

    for path in required:
        _check_file(path, optional_file=False)
    for path in optional:
        _check_file(path, optional_file=True)

    result["pass"] = len(result["issues"]) == 0
    return result


# ── FIX-174 (DEC-094): Check 29 — M5 runtime triggers ─────────────
# Best-effort runtime scan for behavior-protocol.md M5.1b (RUNTIME-DETERMINISTIC
# triggers) + M5.4b (notification structure). Detects Coordinator outputs that
# end in a bare question or contain an option menu without an AskUserQuestion
# tool call. Falls back to "no-verdict" when no corpus source is available.

# M5.1b T1 question-word set (behavior-protocol.md L301). The protocol lists a
# non-exhaustive exemplar set; we widen it to common Coordinator bare-question
# phrasings so the deterministic T1 trigger has high recall on real outputs.
# FIX-174 R1 (P1-4): the set is tightened to remove wildcard-equivalent terms
# that matched nearly any Chinese sentence. "吗？"/"吗?" were dropped (any
# question ends in them — they are functionally the question mark itself, which
# T1 already gates on), as was "是不是" (also opens declarative sentences) and
# "可以吗"/"好吗？" (over-broad). T1 is a two-condition trigger — question-mark
# ending AND a set hit — so each retained word must carry discriminative signal
# beyond "is this a question".
M5_QUESTION_WORDS = (
    "要继续吗", "需要我", "要不要", "是否继续", "Shall I", "Should I",
    "Do you want", "要做我", "继续?", "继续？", "确认?", "确认？",
    "请问", "要不要我", "是否需要",
)

# M5.1b T2 option-menu markers. The protocol (behavior-protocol.md L305) names
# an explicit enumerated list — (1)/(2)/(a)/(b) — so the parenthesised-marker
# character class is restricted to digits 1-9 and letters a-d only. The earlier
# `[1-9a-z]` class over-matched: it accepted any single letter, e.g. the plural
# marker "(s)" in "Agent(s)", producing false-positive T2 hits on prose that
# merely mentions a parenthesised letter.
# Multi-line numbered-list markers ("1. ", circled ①) are retained but anchored
# to line starts so they only match genuine list items, not in-sentence "1.".
M5_OPTION_MENU_RE = re.compile(
    r"\(\s*[1-9]\s*\)|\(\s*[a-d]\s*\)|^\s*[1-9]\.\s|^\s*[①②③④⑤⑥⑦⑧⑨⑩]\s*",
    re.MULTILINE | re.IGNORECASE,
)
M5_CHOICE_CONTEXT_WORDS = ("选择", "choose", "select", "选项", "倾向", "方案")
# FIX-174 R1 (P0-1): T2 choice-context words must be co-located with the
# option-menu markers, not anywhere in the segment. We define "co-located" as
# within the same prose paragraph OR within a ±N-line window around each marker.
# This kills false positives where descriptive "(1)(2)(3)" enumerate bullets in
# one paragraph and an unrelated "选项" word appears dozens of lines away.
_M5_T2_PROXIMITY_LINES = 6

# M5.4b notification prefixes (N3).
M5_NOTIFICATION_PREFIXES = ("ℹ️", "📢", "> 注：", ">> 派发", ">注：", "> 注:", ">>派发")


def _strip_code_fences_and_tables(text):
    """Strip ``` fenced code blocks and | table rows from prose text.

    Returns a list of surviving prose lines (each a non-empty stripped line).
    Used by the M5 runtime scanner so question marks inside code/tables do
    not trip the T1 / T2 triggers (behavior-protocol.md M5.1b exemption zone).
    """
    _resolve_shared()
    prose_lines = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        # Toggle fenced-code state on ``` boundaries (allow leading whitespace).
        if stripped.startswith("```") or stripped == "```":
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # Skip 4-space indented code blocks.
        if line.startswith("    ") and stripped:
            continue
        # Skip markdown table rows.
        if stripped.startswith("|") and stripped.endswith("|"):
            continue
        if not stripped:
            continue
        prose_lines.append(line)
    return prose_lines


def _segment_final_prose(text):
    """Return the last non-empty prose paragraph (after stripping code/tables).

    A "paragraph" is the maximal run of surviving prose lines separated by the
    code/table/blank boundaries removed by _strip_code_fences_and_tables.
    The last paragraph is what M5.1b T1 inspects (final-segment question).
    """
    _resolve_shared()
    prose_lines = _strip_code_fences_and_tables(text)
    if not prose_lines:
        return ""
    # Group into paragraphs by adjacency in the ORIGINAL text. Simpler & robust:
    # treat contiguous surviving lines as one paragraph; the last group wins.
    paragraphs = []
    current = []
    # Re-walk original text to preserve adjacency.
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped == "```":
            in_fence = not in_fence
            if current:
                paragraphs.append("\n".join(current))
                current = []
            continue
        if in_fence:
            continue
        if line.startswith("    ") and stripped:
            if current:
                paragraphs.append("\n".join(current))
                current = []
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            if current:
                paragraphs.append("\n".join(current))
                current = []
            continue
        if not stripped:
            if current:
                paragraphs.append("\n".join(current))
                current = []
            continue
        current.append(line)
    if current:
        paragraphs.append("\n".join(current))
    if not paragraphs:
        return ""
    return paragraphs[-1]


def _t2_has_proximate_choice_context(prose_text):
    """FIX-174 R1 (P0-1): choice-context word must be co-located with an
    option-menu marker, not anywhere in the whole segment.

    Returns True iff at least one M5_OPTION_MENU_RE match has a
    M5_CHOICE_CONTEXT_WORDS hit on the SAME line as the marker OR within a
    ±_M5_T2_PROXIMITY_LINES line window. Rejects the "descriptive (1)(2)(3)
    bullets here + unrelated '选项' word dozens of lines away" false positive.

    We deliberately measure proximity in raw line distance rather than
    "same paragraph", because bullet-dense markdown produces very large
    paragraphs where a co-located word can sit 15+ lines from the marker.

    `prose_text` is the segment text with code fences/tables already stripped.
    """
    _resolve_shared()
    if not prose_text:
        return False
    lines = prose_text.splitlines()
    n_lines = len(lines)
    # Pre-compute the line index of each choice-context word occurrence.
    word_lines = []
    for w in M5_CHOICE_CONTEXT_WORDS:
        start = 0
        while True:
            idx = prose_text.find(w, start)
            if idx < 0:
                break
            word_lines.append(prose_text.count("\n", 0, idx))
            start = idx + len(w)
    if not word_lines:
        return False
    for m in M5_OPTION_MENU_RE.finditer(prose_text):
        match_line = prose_text.count("\n", 0, m.start())
        for wl in word_lines:
            if abs(wl - match_line) <= _M5_T2_PROXIMITY_LINES:
                return True
    return False


def check_m5_runtime_triggers(text=None, contains_askuserquestion=False,
                              corpus_sources=None):
    """FIX-174 (DEC-094): Check 29 — M5 runtime trigger scan.

    Implements behavior-protocol.md M5.1b (T1 bare-question / T2 option-menu
    triggers) and M5.4b (notification-prefix WARN). When `text` is supplied
    directly, scans that assistant-message segment. When `text` is None, the
    check reads corpus sources (evidence-log "事实依据" fields) and degrades to
    "no-verdict" when none are available (P1-b: do not FAIL in a corpus-less
    environment).

    FIX-178: session-snapshot.md is intentionally NOT scanned in auto-discovery
    mode. It is a post-hoc record file (the snapshot format spec mandates it be
    written at session end and may legitimately contain numbered step references
    and choice vocabulary in its structured fields — e.g. 下次会话优先级 ordered
    lists, 待确认决策 entries), not agent runtime output. Scanning it produced
    structural false positives — legitimate records (e.g. "第(1)(2)步…第(3)步"
    step references plus nearby "选择/方案/选项" words) read by the T2 heuristic
    as a runtime option menu with no AskUserQuestion. Auto-discovery now reads
    only evidence-log "事实依据" fields (genuine agent-output summaries).

    Args:
      text: optional assistant-message segment string to scan directly.
      contains_askuserquestion: whether the segment carried an AskUserQuestion
        tool call (True suppresses T1/T2 violations).
      corpus_sources: optional list of (source_label, segment_text, has_tool)
        tuples used when text is None.

    Returns dict: {verdict, reason, violations, warnings, scanned_segments}
      verdict ∈ {"FAIL", "PASS", "WARN", "no-verdict", "skip"}
    """
    _resolve_shared()
    result = {
        "verdict": "skip",
        "reason": "",
        "violations": [],
        "warnings": [],
        "scanned_segments": 0,
    }

    # Build the work list: [(label, segment, has_tool), ...].
    if text is not None:
        segments = [("inline", text, bool(contains_askuserquestion))]
    elif corpus_sources:
        segments = list(corpus_sources)
    else:
        # Discover corpus from governance runtime files (best-effort).
        # FIX-178: session-snapshot.md is deliberately excluded from
        # auto-discovery. It is a post-hoc RECORD file (the snapshot format spec
        # mandates it be written at session end; its structured fields may
        # legitimately contain numbered step references and choice vocabulary),
        # not agent runtime output. Scanning it produced structural false
        # positives — legitimate records (e.g. "第(1)(2)步…第(3)步" step
        # references + nearby "选择/方案/选项" vocabulary) tripped T2 because
        # the runtime heuristic cannot distinguish a recorded menu from a
        # runtime menu. Only evidence-log
        # "事实依据" fields (genuine agent-output summaries) are scanned.
        segments = []
        if EVIDENCE_PATH.is_file():
            try:
                ev = EVIDENCE_PATH.read_text(encoding="utf-8")
                # Extract "事实依据:" field text from evidence rows.
                fact_lines = [
                    line for line in ev.splitlines()
                    if "事实依据" in line or "事实:" in line
                ]
                if fact_lines:
                    segments.append(("evidence-log-facts", "\n".join(fact_lines), False))
            except (IOError, OSError):
                pass

    if not segments:
        # P1-b corpus-less degradation: no verdict, formal definition only.
        result["verdict"] = "no-verdict"
        result["reason"] = (
            "no corpus source available — M5 runtime scan degrades to no-verdict "
            "(behavior-protocol.md M5.1b/M5.4b formal definition applies but no "
            "assistant text to scan)"
        )
        return result

    violations = []
    warnings = []
    for label, segment_text, has_tool in segments:
        result["scanned_segments"] += 1
        if has_tool:
            # AskUserQuestion present in this segment → no M5.1b violation.
            continue
        if not segment_text or not segment_text.strip():
            continue

        final_para = _segment_final_prose(segment_text)
        final_para_stripped = final_para.strip()

        # T1: final prose segment ends with a question mark AND hits a question word.
        ends_with_question = bool(final_para_stripped) and final_para_stripped[-1] in ("？", "?")
        if ends_with_question and any(w in final_para_stripped for w in M5_QUESTION_WORDS):
            violations.append({
                "trigger": "T1",
                "source": label,
                "reason": "final prose segment ends with a question mark and hits "
                          "a question-word set entry, with no AskUserQuestion tool call",
            })
            continue

        # T2: option-menu markers + co-located choice-context words, no tool.
        # FIX-174 R1 (P0-1): "上下文含" (protocol M5.1b L306) means same-segment
        # AND near the marker, NOT anywhere in the whole segment. Whole-segment
        # matching produced false positives on descriptive "(1)(2)(3)" bullets
        # with an unrelated "选项" word far away (e.g. session-snapshot prose).
        full_prose = "\n".join(_strip_code_fences_and_tables(segment_text))
        has_option_menu = bool(M5_OPTION_MENU_RE.search(full_prose))
        has_choice_context = has_option_menu and _t2_has_proximate_choice_context(full_prose)
        if has_option_menu and has_choice_context:
            violations.append({
                "trigger": "T2",
                "source": label,
                "reason": "option-menu markers + choice-context words present "
                          "with no AskUserQuestion tool call",
            })
            continue

        # M5.4b: notification without prefix → WARN (only if no T1/T2 violation).
        if final_para_stripped:
            has_notification_prefix = any(
                final_para_stripped.startswith(p) for p in M5_NOTIFICATION_PREFIXES
            )
            if not has_notification_prefix:
                warnings.append({
                    "trigger": "M5.4b",
                    "source": label,
                    "reason": "prose segment lacks a notification prefix "
                              "(ℹ️ / 📢 / > 注： / >> 派发) — suspected untagged notification",
                })

    result["violations"] = violations
    result["warnings"] = warnings
    if violations:
        result["verdict"] = "FAIL"
        triggers = ", ".join(sorted({v["trigger"] for v in violations}))
        result["reason"] = (
            f"M5 runtime violation(s): {triggers} — bare question / option menu "
            f"without AskUserQuestion (behavior-protocol.md M5.1b)"
        )
    elif warnings:
        result["verdict"] = "WARN"
        result["reason"] = (
            f"{len(warnings)} M5.4b notification-prefix WARN(s) — not blocking"
        )
    else:
        result["verdict"] = "PASS"
        result["reason"] = (
            "no M5 runtime triggers fired — segments comply with M5.1b/M5.4b"
        )
    return result


# ── FIX-174 (DEC-094): Check 30 — review closure state machine ────
# Validates behavior-protocol.md M7.4 step 4.6 review-closure state machine:
# V1 terminal-state legality, V2 round continuity, V3 fuse (MAX_ROUNDS=3),
# V4 APPROVED traceability. Backward-compat: bare REVIEW-{id} = R0.

REVIEW_MAX_ROUNDS = 3  # behavior-protocol.md M7.4 step 4.6 (C3) fuse.

# Terminal conclusions per M7.4 step 4.6 (C4): APPROVED_WITH_NOTES is an
# approved terminal state. NEEDS_CHANGE(S) remains an intermediate state.
_REVIEW_APPROVAL_CONCLUSIONS = ("APPROVED", "APPROVED_WITH_NOTES")
_REVIEW_TERMINAL_CONCLUSIONS = (*_REVIEW_APPROVAL_CONCLUSIONS, "BLOCKED")
_REVIEW_NON_TERMINAL_ALIASES = {"NEEDS_CHANGES": "NEEDS_CHANGE"}

_UNRESOLVED_BLOCKERS_KEY_RE = re.compile(
    r"(?<![A-Za-z0-9_])unresolved_blockers(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

_REVIEW_ID_RE = re.compile(r"^REVIEW-([A-Z]+-\d+)(?:-R(\d+))?$")
_LEGACY_REVIEW_FILE_RE = re.compile(r"^review-([A-Z]+-\d+)-v\d+\.md$", re.IGNORECASE)

# FIX-174 R1 (P0-2): date from which REVIEW-{id}-R{n} round-numbered naming
# became the enforced convention (FIX-173 normalized the evidence protocol,
# agent-communication-protocol.md L317-318). Sequences whose evidence predates
# this and mix bare REVIEW-{id} (R0) with R{n}-numbered rounds are historical
# naming residue, not a real round-continuity breach — V2 downgrades to WARN.
FIX173_NAMING_NORMALIZATION_DATE = date(2026, 7, 4)

# FIX-233: date from which review records are expected to comply with the
# FIX-174 closure state machine (V1 terminal legality + V5 machine-readable
# unresolved_blockers=0 token). The 0.66.1 incident chain (FIX-197/FIX-199/
# REL-058 etc., evidence 2026-07-11~17) produced terminal review rows that
# cannot be rewritten: BLOCKED escalation closures (V1) and
# APPROVED_WITH_NOTES prose conclusions without a structured token (V5).
# Their earliest evidence predates this date (the day after the last
# incident-chain evidence row, 2026-07-17; the chain was formally closed by
# the REL-063/REL-064 compensation releases on 2026-07-25, RISK-043/DEC-132),
# so V1/V5 downgrade to WARN for them — same judgment pattern as the V2
# FIX173_NAMING_NORMALIZATION_DATE exemption. The predicate is the TERMINAL
# round's evidence date (FIX-233 R1 P1-1): a mixed chain whose terminal round
# post-dates this date remains fully enforced, even when earlier rounds are
# historical residue.
FIX174_NORMALIZATION_DATE = date(2026, 7, 18)


def _normalize_review_conclusion(value):
    """Return a recognized review state, normalizing only plural NEEDS_CHANGE."""
    _resolve_shared()
    normalized = str(value or "").strip().upper()
    normalized = _REVIEW_NON_TERMINAL_ALIASES.get(normalized, normalized)
    if normalized in (*_REVIEW_TERMINAL_CONCLUSIONS, "NEEDS_CHANGE"):
        return normalized
    return ""


def _extract_review_conclusion_from_text(text):
    """Extract one explicit review conclusion; ambiguous/malformed text is UNKNOWN."""
    _resolve_shared()
    upper = str(text or "").upper()
    status_pattern = r"(APPROVED_WITH_NOTES|APPROVED|NEEDS_CHANGES?|BLOCKED)"
    explicit = re.findall(
        rf"(?:审查结论|评审结论|REVIEW CONCLUSION|CONCLUSION)\**\s*[:：]\s*\**\s*{status_pattern}(?![A-Z_])",
        upper,
    )
    candidates = explicit or re.findall(
        rf"(?<![A-Z_]){status_pattern}(?![A-Z_])",
        upper,
    )
    normalized = {_normalize_review_conclusion(candidate) for candidate in candidates}
    normalized.discard("")
    return normalized.pop() if len(normalized) == 1 else "UNKNOWN"


def _parse_unresolved_blockers_fields(fields):
    """Parse structured ``unresolved_blockers=<count>`` tokens.

    Each item is treated as an independent table column or report line.  The
    parser deliberately does not infer blocker state from prose such as
    ``blocking finding``.  Duplicate equal values are accepted; malformed
    tokens or differing duplicate values are fail-closed.
    """
    _resolve_shared()
    values = []
    invalid_tokens = []
    for raw_field in fields or []:
        field = str(raw_field or "")
        for key_match in _UNRESOLVED_BLOCKERS_KEY_RE.finditer(field):
            tail = field[key_match.end():]
            value_match = re.match(r"\s*=\s*([^\s,;|`*]+)", tail)
            if not value_match:
                invalid_tokens.append(field[key_match.start():].strip())
                continue
            raw_value = value_match.group(1)
            if not re.fullmatch(r"\d+", raw_value):
                invalid_tokens.append(
                    f"unresolved_blockers={raw_value}"
                )
                continue
            values.append(int(raw_value))

    if invalid_tokens:
        return {
            "status": "invalid",
            "value": None,
            "values": values,
            "invalid_tokens": invalid_tokens,
        }
    if not values:
        return {
            "status": "missing",
            "value": None,
            "values": [],
            "invalid_tokens": [],
        }
    if len(set(values)) != 1:
        return {
            "status": "conflict",
            "value": None,
            "values": values,
            "invalid_tokens": [],
        }
    return {
        "status": "valid",
        "value": values[0],
        "values": values,
        "invalid_tokens": [],
    }


def _merge_unresolved_blocker_evidence(left, right):
    """Merge blocker facts from duplicate evidence for the same round."""
    _resolve_shared()
    left = left or _parse_unresolved_blockers_fields([])
    right = right or _parse_unresolved_blockers_fields([])
    if left["status"] == "missing":
        return right
    if right["status"] == "missing":
        return left
    fields = [f"unresolved_blockers={value}" for value in left.get("values", [])]
    fields.extend(
        f"unresolved_blockers={value}" for value in right.get("values", [])
    )
    fields.extend(left.get("invalid_tokens", []))
    fields.extend(right.get("invalid_tokens", []))
    return _parse_unresolved_blockers_fields(fields)


def _entry_unresolved_blocker_evidence(entry):
    """Normalize fixture/live-entry blocker evidence into parser output."""
    _resolve_shared()
    evidence = entry.get("blocker_evidence")
    if isinstance(evidence, dict) and "status" in evidence:
        return evidence
    if "unresolved_blockers_fields" in entry:
        return _parse_unresolved_blockers_fields(
            entry.get("unresolved_blockers_fields")
        )
    if "unresolved_blockers" not in entry:
        return _parse_unresolved_blockers_fields([])
    raw = entry.get("unresolved_blockers")
    values = raw if isinstance(raw, (list, tuple)) else [raw]
    return _parse_unresolved_blockers_fields(
        [f"unresolved_blockers={value}" for value in values]
    )


def _normalize_review_round(raw_id):
    """Return (task_id, round) tuple for a REVIEW-{id}[-R{n}] identifier.

    Bare REVIEW-{id} → (id, 0). REVIEW-{id}-R{n} → (id, n).
    Returns (None, None) if the id does not match the canonical shape.
    """
    _resolve_shared()
    if not raw_id:
        return (None, None)
    m = _REVIEW_ID_RE.match(raw_id.strip())
    if not m:
        return (None, None)
    task_id = m.group(1)
    round_str = m.group(2)
    round_n = int(round_str) if round_str is not None else 0
    return (task_id, round_n)


def _build_review_sequence(review_entries, legacy_files=None):
    """Build per-task_id ordered review sequences from raw entry dicts.

    review_entries: iterable of dicts with at least {"id", "task_ref",
      "conclusion"}. id may be REVIEW-{id} or REVIEW-{id}-R{n}. An optional
      "date" field (ISO YYYY-MM-DD) records the evidence-row date so the V2
      historical-naming exemption (FIX-174 R1 P0-2) can tell pre-FIX-173
      residue from a real round-continuity breach.
    legacy_files: iterable of dicts {"file": "review-{id}-v*.md", "task_ref"}.
      These are tagged UNKNOWN (no round inference, P1-c backward compat).

    Returns dict: task_id -> {
        "rounds": {round_int: {"id":..., "conclusion":...}},
        "max_round": int,
        "has_unknown_legacy": bool,
        "naming_migrated": bool,   # FIX-174 R1 (P0-2): mixes bare REVIEW-{id}
                                   # (round 0) with R{n}-numbered rounds (n>=2)
        "min_evidence_date": date|None,
    }

    Each round dict also carries a "date" field (FIX-233 R1 P1-1): the latest
    evidence date observed for that round. The V1/V5 historical exemption
    judges the TERMINAL round's date, not the chain-wide min_evidence_date
    (which remains the predicate for the V2 naming-residue exemption).
    """
    _resolve_shared()
    sequences = {}
    for entry in review_entries or []:
        raw_id = entry.get("id", "")
        task_ref = entry.get("task_ref", "")
        raw_conclusion = str(entry.get("conclusion", "")).strip().upper()
        conclusion = _normalize_review_conclusion(raw_conclusion) or raw_conclusion or "UNKNOWN"
        blocker_evidence = _entry_unresolved_blocker_evidence(entry)
        entry_date = entry.get("date")
        parsed_date = None
        if entry_date:
            parsed = _parse_iso_date(entry_date) if isinstance(entry_date, str) else entry_date
            if parsed is not None:
                parsed_date = parsed
        task_id, round_n = _normalize_review_round(raw_id)
        if task_id is None:
            # Unparseable id — fall back to task_ref if present, round unknown.
            if not task_ref:
                continue
            seq = sequences.setdefault(task_ref, {"rounds": {}, "max_round": -1,
                                                  "has_unknown_legacy": True,
                                                  "naming_migrated": False,
                                                  "min_evidence_date": None})
            seq["has_unknown_legacy"] = True
            continue
        seq = sequences.setdefault(task_id, {"rounds": {}, "max_round": -1,
                                             "has_unknown_legacy": False,
                                             "naming_migrated": False,
                                             "min_evidence_date": None})
        if round_n in seq["rounds"]:
            # Duplicate round — keep the most-terminal conclusion.
            existing = seq["rounds"][round_n]["conclusion"]
            seq["rounds"][round_n]["blocker_evidence"] = (
                _merge_unresolved_blocker_evidence(
                    seq["rounds"][round_n].get("blocker_evidence"),
                    blocker_evidence,
                )
            )
            # FIX-233 R1 (P1-1): retain the round's evidence date — the LATEST
            # date observed for the round (fail-closed: a post-normalization
            # date must never be masked by an older duplicate entry).
            if parsed_date is not None:
                cur_date = seq["rounds"][round_n].get("date")
                if cur_date is None or parsed_date > cur_date:
                    seq["rounds"][round_n]["date"] = parsed_date
            if existing not in _REVIEW_TERMINAL_CONCLUSIONS and conclusion in _REVIEW_TERMINAL_CONCLUSIONS:
                seq["rounds"][round_n] = {"id": raw_id, "conclusion": conclusion,
                                          "blocker_evidence": seq["rounds"][round_n]["blocker_evidence"],
                                          "round_explicit": bool(_REVIEW_ID_RE.match(raw_id)
                                                                 and _REVIEW_ID_RE.match(raw_id).group(2)),
                                          "date": seq["rounds"][round_n].get("date")}
        else:
            m = _REVIEW_ID_RE.match(raw_id)
            round_explicit = bool(m and m.group(2) is not None)
            seq["rounds"][round_n] = {"id": raw_id, "conclusion": conclusion,
                                      "blocker_evidence": blocker_evidence,
                                      "round_explicit": round_explicit,
                                      "date": parsed_date}
        seq["max_round"] = max(seq["max_round"], round_n)
        # Track naming migration + earliest evidence date for the V2 historical
        # exemption (FIX-174 R1 P0-2). A round-0 entry is "bare" when its id
        # carried no explicit -R{n} suffix (the pre-FIX-173 convention).
        if parsed_date is not None:
            cur = seq["min_evidence_date"]
            if cur is None or parsed_date < cur:
                seq["min_evidence_date"] = parsed_date

    # naming_migrated: the sequence mixes a bare round-0 entry with at least
    # one R{n}-numbered round (n >= 2). That signature only arises when review
    # evidence straddles the FIX-173 naming normalization boundary.
    for seq in sequences.values():
        rounds = seq["rounds"]
        if 0 in rounds and any(r >= 2 for r in rounds):
            bare_r0 = not rounds[0].get("round_explicit", False)
            if bare_r0:
                seq["naming_migrated"] = True

    for lf in legacy_files or []:
        task_ref = lf.get("task_ref", "")
        if not task_ref:
            continue
        seq = sequences.setdefault(task_ref, {"rounds": {}, "max_round": -1,
                                              "has_unknown_legacy": False,
                                              "naming_migrated": False,
                                              "min_evidence_date": None})
        seq["has_unknown_legacy"] = True

    return sequences


def check_review_closure(review_sequence=None, plan_tracker_completed=None,
                         routing_table=None, legacy_files=None):
    """FIX-174 (DEC-094): Check 30 — review closure state-machine validation.

    Implements behavior-protocol.md M7.4 step 4.6 (C1-C7) + DEC-090 degraded
    fuse. Validates V1-V4 over an explicit review_sequence (fixture path) or,
    when called with no args, scans the live evidence-log + plan-tracker.

    Args (fixture path — preferred for AUDIT-128 tests):
      review_sequence: list of dicts {"id", "task_ref", "conclusion", ...}
      plan_tracker_completed: dict {task_id: True} marking tasks the plan
        tracker has marked "已完成" — needed for V1 broken-chain detection.
      routing_table: optional dict task_type -> post-review cell. When a task
        type is exempt (—) V1 NEEDS_CHANGE terminal is allowed.
      legacy_files: optional list of {"file","task_ref"} dicts for pre-R{n}
        review-{id}-v*.md files. Tagged UNKNOWN/WARN, no round inference.

    Returns dict: {verdict, reason, violations, warnings, tasks_checked}
      verdict ∈ {"FAIL", "PASS", "WARN", "no-verdict"}
    """
    _resolve_shared()
    result = {
        "verdict": "no-verdict",
        "reason": "",
        "violations": [],
        "warnings": [],
        "tasks_checked": 0,
    }

    if review_sequence is not None:
        sequences = _build_review_sequence(review_sequence,
                                           legacy_files=legacy_files)
        completed = set((plan_tracker_completed or {}).keys())
    else:
        # Live scan: gather REVIEW-{id}[-R{n}] evidence rows + review-*.md files.
        sequences, completed = _collect_live_review_sequences()

    if not sequences:
        result["verdict"] = "no-verdict"
        result["reason"] = (
            "no review evidence found — Check 30 has nothing to validate"
        )
        return result

    if routing_table is None:
        routing_table = _parse_routing_post_review_table()

    for task_id, seq in sorted(sequences.items()):
        result["tasks_checked"] += 1
        rounds = seq["rounds"]
        max_round = seq["max_round"]

        # Backward-compat legacy files → WARN only (P1-c).
        if seq.get("has_unknown_legacy") and not rounds:
            result["warnings"].append({
                "rule": "COMPAT",
                "task_id": task_id,
                "reason": "legacy review-{id}-v*.md file(s) present — round "
                          "inference skipped, tagged UNKNOWN",
            })
            continue

        if not rounds:
            continue

        # V2: round continuity — R0..R{max} must all exist (no skipped rounds).
        expected_rounds = set(range(0, max_round + 1))
        missing_rounds = expected_rounds - set(rounds.keys())
        if missing_rounds:
            # FIX-174 R1 (P0-2): historical-naming exemption. Sequences that
            # mix a bare REVIEW-{id} (round 0, pre-FIX-173 convention) with an
            # R{n}-numbered round (n >= 2) and whose evidence predates the
            # FIX-173 naming normalization are historical residue, not a real
            # round-continuity breach. Downgrade FAIL → WARN so CI is not
            # permanently red on legacy data (e.g. FIX-071: R0 2026-05-15 +
            # R2 2026-05-19, missing R1 from before the convention existed).
            naming_migrated = bool(seq.get("naming_migrated"))
            ev_date = seq.get("min_evidence_date")
            pre_normalization = (
                ev_date is not None and ev_date < FIX173_NAMING_NORMALIZATION_DATE
            )
            if naming_migrated and pre_normalization:
                result["warnings"].append({
                    "rule": "V2",
                    "task_id": task_id,
                    "reason": f"round continuity broken — missing R{sorted(missing_rounds)} "
                              f"— historical naming residue (bare REVIEW-{{id}} + R{{n}} mix, "
                              f"evidence pre-dates FIX-173 normalization {ev_date}); downgraded",
                })
                continue
            result["violations"].append({
                "rule": "V2",
                "task_id": task_id,
                "reason": f"round continuity broken — missing R{sorted(missing_rounds)}",
            })
            continue

        terminal = rounds[max_round]["conclusion"]

        # V3: fuse compliance (MAX_ROUNDS=3). Evaluated before V1 because a
        # fuse breach past MAX_ROUNDS is a more specific / actionable verdict
        # than the generic NEEDS_CHANGE-non-terminal signal (both apply, but
        # the fix is escalation to BLOCKED, not just re-spawning).
        if max_round > REVIEW_MAX_ROUNDS:
            if terminal == "NEEDS_CHANGE":
                result["violations"].append({
                    "rule": "V3",
                    "task_id": task_id,
                    "reason": f"round {max_round} > fuse {REVIEW_MAX_ROUNDS} and "
                              f"R{max_round}=NEEDS_CHANGE — must escalate to BLOCKED",
                })
                continue
            elif terminal in _REVIEW_APPROVAL_CONCLUSIONS:
                # C5: round>3 APPROVED only allowed with explicit "接受降级"
                # escalation decision. We cannot see escalation here, so WARN.
                result["warnings"].append({
                    "rule": "V3",
                    "task_id": task_id,
                    "reason": f"round {max_round} > fuse {REVIEW_MAX_ROUNDS} but "
                              f"R{max_round}=APPROVED — possible marginal pass, "
                              f"confirm escalation accepted degraded",
                })
                # fall through to V4 traceability check

        # V1: terminal state legality. The highest round's conclusion must be
        # an approved state or BLOCKED, UNLESS the task type is routing-exempt (—).
        is_exempt = _task_routing_exempt(task_id, routing_table)
        # FIX-233 (R1 P1-1): historical-rule exemption (same judgment pattern
        # as the V2 FIX173_NAMING_NORMALIZATION_DATE exemption). The predicate
        # is the TERMINAL round's evidence date — a chain whose terminal round
        # predates FIX174_NORMALIZATION_DATE is 0.66.1 incident-chain residue
        # (BLOCKED escalation closures and prose-only APPROVED_WITH_NOTES rows
        # cannot be rewritten): V1/V5 downgrade to WARN. Mixed chains whose
        # terminal round post-dates the normalization stay violations.
        ev_date = rounds[max_round].get("date")
        pre_normalization = (
            ev_date is not None and ev_date < FIX174_NORMALIZATION_DATE
        )
        if terminal == "BLOCKED":
            if pre_normalization:
                result["warnings"].append({
                    "rule": "V1",
                    "task_id": task_id,
                    "reason": f"R{max_round}=BLOCKED closes the chain for "
                              "escalation but is not an approval — historical "
                              f"pre-FIX-174 normalization escalation closure "
                              f"({ev_date}); downgraded",
                })
                continue
            result["violations"].append({
                "rule": "V1",
                "task_id": task_id,
                "reason": f"R{max_round}=BLOCKED closes the chain for escalation "
                          "but is not an approval",
            })
            continue
        if terminal not in _REVIEW_TERMINAL_CONCLUSIONS and not is_exempt:
            # NEEDS_CHANGE (or other) is not a legitimate terminal state.
            # If the plan-tracker marked this task completed → broken chain.
            if task_id in completed:
                result["violations"].append({
                    "rule": "V1",
                    "task_id": task_id,
                    "reason": f"R{max_round}={terminal} is non-terminal but task "
                              f"is marked completed — review chain broken",
                })
            else:
                # Task not yet completed: NEEDS_CHANGE mid-flight is fine.
                result["warnings"].append({
                    "rule": "V1",
                    "task_id": task_id,
                    "reason": f"R{max_round}={terminal} non-terminal — task not "
                              f"yet completed, re-spawn expected",
                })
            continue

        # V5: APPROVED_WITH_NOTES requires a machine-readable proof that no
        # unresolved blocking finding remains.  Prose is intentionally not
        # accepted; only the structured unresolved_blockers=0 token passes.
        if terminal == "APPROVED_WITH_NOTES":
            blocker_evidence = rounds[max_round].get("blocker_evidence") or {}
            blocker_status = blocker_evidence.get("status", "missing")
            blocker_value = blocker_evidence.get("value")
            # FIX-233: a historical row with NO structured token at all is a
            # pre-normalization prose conclusion → WARN. Rows that DID carry a
            # token (nonzero / invalid / conflict) stay violations — the
            # exemption only covers the missing-token (prose) case, fail-closed.
            if blocker_status == "missing" and pre_normalization:
                result["warnings"].append({
                    "rule": "V5",
                    "task_id": task_id,
                    "reason": f"R{max_round}=APPROVED_WITH_NOTES without a "
                              "structured unresolved_blockers=0 token — "
                              f"historical pre-FIX-174 normalization prose "
                              f"conclusion ({ev_date}); downgraded",
                })
                continue
            if blocker_status != "valid" or blocker_value != 0:
                detail = blocker_status
                if blocker_status == "valid":
                    detail = f"value={blocker_value}"
                elif blocker_evidence.get("values"):
                    detail = f"{blocker_status}, values={blocker_evidence['values']}"
                result["violations"].append({
                    "rule": "V5",
                    "task_id": task_id,
                    "reason": f"R{max_round}=APPROVED_WITH_NOTES requires exactly "
                              f"unresolved_blockers=0; got {detail}",
                })
                continue

        # V4: approval traceability — a terminal approval must have a real
        # R{n} approval entry (trivially true here since `terminal` came from
        # rounds[max_round]).
        if terminal in _REVIEW_APPROVAL_CONCLUSIONS:
            if rounds[max_round]["conclusion"] not in _REVIEW_APPROVAL_CONCLUSIONS:
                result["violations"].append({
                    "rule": "V4",
                    "task_id": task_id,
                    "reason": f"task marked APPROVED but R{max_round} conclusion "
                              f"is {rounds[max_round]['conclusion']}",
                })

    if result["violations"]:
        result["verdict"] = "FAIL"
        rules = ", ".join(sorted({v["rule"] for v in result["violations"]}))
        result["reason"] = (
            f"review-closure violations: {rules} — M7.4 step 4.6 state machine"
        )
    elif result["warnings"]:
        result["verdict"] = "WARN"
        result["reason"] = (
            f"{len(result['warnings'])} review-closure WARN(s) — non-blocking"
        )
    else:
        result["verdict"] = "PASS"
        result["reason"] = (
            "all review sequences comply with M7.4 step 4.6 closure state machine"
        )
    return result


def _task_routing_exempt(task_id, routing_table):
    """FIX-174 R1 (P0-3): heuristic — is this task's type routing-exempt (—)?

    The plan-tracker has no task-type column, so the routing cell cannot be
    looked up directly. We infer the task type from the evidence-log row
    (its type + description cells) and check whether any exempt task-type
    label — i.e. a routing-table key whose "后置审查 Agent(s)" cell is — —
    appears in that text. Pure review-type tasks (代码审查 / 设计审查 /
    需求审查 / 测试审查 / 发布审查 / 复盘审查 / 需求澄清 / 任务模糊 /
    性能优化 / 部署/运维) have no post-review agent, so a NEEDS_CHANGE
    terminal is legitimate (the review itself IS the deliverable).

    Returns True if the inferred task type matches an exempt routing key.
    """
    _resolve_shared()
    if not routing_table:
        return False
    # Collect the exempt routing keys (post-review cell == —).
    exempt_types = {t for t, cell in routing_table.items()
                    if _is_post_review_exempt(cell)}
    if not exempt_types:
        return False
    blob = _evidence_task_type_index().get(task_id, "")
    if not blob:
        return False
    for etype in exempt_types:
        if etype and etype.lower() in blob:
            return True
    return False


def _collect_live_review_sequences():
    """Scan evidence-log + .governance/review-*.md for review sequences.

    Returns (sequences_dict, completed_set).
    """
    _resolve_shared()
    review_entries = []
    legacy_files = []
    completed = set()

    # Plan-tracker: collect completed task ids.
    if SAMPLE_PATH.is_file():
        try:
            completed = parse_completed_task_ids()
        except Exception:
            completed = set()

    # Evidence-log: REVIEW-{id}[-R{n}] rows.
    if EVIDENCE_PATH.is_file():
        try:
            content = EVIDENCE_PATH.read_text(encoding="utf-8")
        except (IOError, OSError):
            content = ""
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            parts = [p.strip() for p in stripped.split("|")]
            if len(parts) < 8:
                continue
            evd_id = parts[1]
            raw_ids = parts[2]
            conclusion = ""
            # Conclusion often lives in notes / tail columns.
            for part in parts[3:]:
                conclusion = _normalize_review_conclusion(part)
                if conclusion:
                    break
            # FIX-174 R1 (P0-2): pull the row's ISO date so the V2 historical
            # exemption can tell pre-FIX-173 naming residue from a real breach.
            row_date = ""
            for part in parts[3:]:
                m_date = re.match(r"^(\d{4}-\d{2}-\d{2})$", part)
                if m_date:
                    row_date = m_date.group(1)
                    break
            # Match REVIEW-{id}[-R{n}] shape in evd_id or raw_ids.
            candidate_ids = []
            for cand in (evd_id, raw_ids):
                for m in re.finditer(r"REVIEW-[A-Z]+-\d+(?:-R\d+)?", cand):
                    candidate_ids.append(m.group(0))
            if not candidate_ids:
                continue
            for cid in candidate_ids:
                task_id, _round = _normalize_review_round(cid)
                if task_id is None:
                    continue
                review_entries.append({
                    "id": cid,
                    "task_ref": task_id,
                    "conclusion": conclusion or "UNKNOWN",
                    "blocker_evidence": _parse_unresolved_blockers_fields(parts[3:]),
                    "date": row_date,
                })

    # .governance/review-*.md files.
    gov_dir = GOVERNANCE_DIR
    if gov_dir.is_dir():
        for rf in gov_dir.glob("review-*.md"):
            name = rf.name
            m_legacy = _LEGACY_REVIEW_FILE_RE.match(name)
            if m_legacy:
                legacy_files.append({"file": name, "task_ref": m_legacy.group(1)})
                continue
            # New-format review-{id}-R{n}.md or review-{id}.md.
            m_new = re.match(r"^review-([A-Z]+-\d+)(?:-R(\d+))?\.md$", name, re.IGNORECASE)
            if not m_new:
                continue
            task_id = m_new.group(1)
            round_n = int(m_new.group(2)) if m_new.group(2) else 0
            # Read conclusion from file content.
            conclusion = "UNKNOWN"
            try:
                fc = rf.read_text(encoding="utf-8")
                conclusion = _extract_review_conclusion_from_text(fc)
                blocker_evidence = _parse_unresolved_blockers_fields(fc.splitlines())
            except (IOError, OSError):
                blocker_evidence = _parse_unresolved_blockers_fields([])
            cid = f"REVIEW-{task_id}-R{round_n}" if round_n else f"REVIEW-{task_id}"
            review_entries.append({
                "id": cid,
                "task_ref": task_id,
                "conclusion": conclusion,
                "blocker_evidence": blocker_evidence,
            })

    sequences = _build_review_sequence(review_entries, legacy_files=legacy_files)
    return sequences, completed


def cmd_check_review_debt(args):
    """Run Check 21: Review Debt independently."""
    _resolve_shared()
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    print("\n=== Check 21: Review Debt / Spawn Gap (SYSGAP-042 + FIX-174) ===")
    rd_result = check_review_debt()
    print(f"  Product-code tasks (all, with evidence): {rd_result['total_tasks']}")
    print(f"  Review debt (have execution evidence, no review): {rd_result['review_debt_count']}")
    if rd_result["review_debt_count"] > 0:
        print(f"  [FAIL] {rd_result['review_debt_count']} product-code task(s) with review debt:")
        for tid in rd_result["review_debt_tasks"]:
            print(f"    - {tid}")
    if rd_result.get("degraded_fuse_tasks"):
        print(f"  [FAIL] {len(rd_result['degraded_fuse_tasks'])} task(s) hit degraded-fuse "
              f"(≥{DEGRADED_FUSE_THRESHOLD} degraded reviews, M7.4 step 4.6):")
        for tid in rd_result["degraded_fuse_tasks"]:
            print(f"    - {tid}")
    if rd_result["review_debt_count"] == 0 and not rd_result.get("degraded_fuse_tasks"):
        if rd_result["total_tasks"] > 0:
            print(f"  [PASS] All product-code tasks have review evidence.")
        else:
            print(f"  [PASS] No product-code tasks to check.")
    print()
    has_fail = (
        rd_result["review_debt_count"] > 0
        or bool(rd_result.get("degraded_fuse_tasks"))
    )
    if args.fail_on_issues and has_fail:
        sys.exit(1)


