"""Change-control triage domain — Check 32 (FIX-237.4 / ADR-017 §4.4).

Enforcement layer for the mandatory change-control triage of product-code
task intake:

  - **CLI wiring**: the ``change-triage`` command MUST stay registered in
    verify_workflow.py's argparse subparsers AND commands dispatch dict
    (AST scan — a regression that silently removes the gate FAILs).
  - **Record validity**: every ``.governance/change-triage/*.json`` record
    MUST carry the four-step analysis (dependency / priority / conflicts /
    version) plus the ``task-priority-analysis`` snapshot.
  - **No-record → FAIL**: a product-code task whose earliest evidence-log
    date is on/after :data:`TRIAGE_NORMALIZATION_DATE` and which has NO
    triage record FAILs the check (fail-closed). Completed tasks, historical
    tasks (earliest evidence before the normalization date) and quick-lane
    tasks (evidence only under ``.governance/`` — FIX-228 boundary) are
    exempt.

The date-based exemption mirrors the FIX-174 / FIX-233 precedent
(``FIX173_NAMING_NORMALIZATION_DATE``): tasks created before the feature
ship date cannot retroactively produce triage records, so only
post-normalization activity is enforced. :data:`TRIAGE_NORMALIZATION_DATE`
is pinned to the 0.73.0 ship window and MUST be bumped by REL-066 to the
actual 0.73.0 release date.

Known limitation (documented in ADR-017 §4.4): a task with NO evidence rows
yet cannot be dated, so it is exempt from the Check-32 scan — the CLI
fail-closed gate (change-triage MUST run before the task row is created) is
the primary enforcement for that window.

Check 39 (FIX-274 / F-03, M7.7 R1 downstream consumer): a triage record
with ``analysis.side_effect.requires_r1 == true`` whose task is marked
completed MUST carry R1 留痕 evidence in the evidence-log (one-of-three
fact: isolation redirect / backup + verification / per-item user
authorization). Missing evidence → WARN during the DEC-159 observation
window. **Tightening condition (explicit registration)**: WARN is the
0.77.x observation-window severity; the check escalates to FAIL after 2
consecutive 0.77.x releases close with zero r1-evidence violations, and
that escalation flip MUST be recorded as a decision-log entry when made.
**Evidence discrimination (review-FIX-274-CODE-R0 P1-1 后)**: machine
metadata rows (TRIAGE-/RECO-/REVIEW- id prefixes) are excluded — their
fixed templates embed "命令输出 JSON 快照见 change-triage/{id}.json" —
and group (b) 备份 is AND-combined with 校验/一致性/核对, so a bare
快照 (JSON-snapshot template or completion-recommendation snapshot)
never satisfies R1(b); keywords are matched against the descriptive
cells (cells[3:7]) only.

See docs/architecture/ADR-017-loop-wiring-and-task-planning-0.73.0.md §4.4.
"""

import ast
import json
import re
from datetime import date
from pathlib import Path

from task_priority import parse_task_dependencies


# Check-32 normalization boundary: tasks whose earliest evidence-log row is
# on/after this date MUST have a triage record. Pinned to the 0.73.0 ship
# window; REL-066 MUST bump it to the actual release date.
TRIAGE_NORMALIZATION_DATE = date(2026, 8, 3)

# Record contract (change_triage.TRIAGE_SCHEMA_VERSION == 1).
RECORD_REQUIRED_FIELDS = (
    "schema_version",
    "task_id",
    "priority",
    "target_version",
    "depends_on",
    "files",
    "analysis",
    "snapshot",
)
ANALYSIS_STEPS = ("dependency", "priority_context", "conflicts", "version")

# Product-code evidence location markers (FIX-228 boundary: quick lane =
# .governance/-only governance records). Mirrors the check_agent_activation
# product-code pattern list.
TRIAGE_PRODUCT_CODE_PATTERNS = (
    "skills/",
    "agents/",
    "infra/",
    "commands/",
    "adapters/",
    "project/",
    ".claude-plugin/",
    ".codex-plugin/",
    ".zcode-plugin/",
    ".chrys-plugin/",
    ".agents/",
)

_ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def _verify_workflow_path(root: Path) -> Path:
    """Locate verify_workflow.py under the plugin root."""
    candidates = (
        root / "skills/software-project-governance/infra/verify_workflow.py",
        root / "infra/verify_workflow.py",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def check_triage_wiring(verify_path) -> dict:
    """AST scan: ``change-triage`` registered in argparse + commands dict.

    Only real AST structure counts (``add_parser("change-triage", ...)``
    call and a ``"change-triage": cmd_*`` key in the commands dispatch
    dict), so docstring mentions cannot cause a false positive.

    Returns:
        dict ``{"registered", "argparse", "dispatch", "reason"}``.
    """
    path = Path(verify_path)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        return {
            "registered": False, "argparse": False, "dispatch": False,
            "reason": "cannot parse {0}: {1}".format(path, exc),
        }
    argparse_registered = False
    dispatch_registered = False
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_parser"):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and arg.value == "change-triage":
                    argparse_registered = True
        elif isinstance(node, ast.Dict):
            for key in node.keys:
                if (isinstance(key, ast.Constant)
                        and key.value == "change-triage"):
                    dispatch_registered = True
    registered = argparse_registered and dispatch_registered
    return {
        "registered": registered,
        "argparse": argparse_registered,
        "dispatch": dispatch_registered,
        "reason": (
            "change-triage registered (argparse + dispatch)"
            if registered else (
                "change-triage wiring missing — argparse={0}, "
                "dispatch={1}".format(argparse_registered,
                                      dispatch_registered))
        ),
    }


def validate_triage_record(record: dict) -> list:
    """Validate one triage record against the four-step contract.

    Returns:
        list of issue strings (empty = valid).
    """
    issues = []
    for field in RECORD_REQUIRED_FIELDS:
        if field not in record:
            issues.append("record missing required field {0!r}".format(field))
    if "priority" in record and record.get("priority") not in ("P0", "P1", "P2"):
        issues.append("record priority {0!r} not in P0/P1/P2".format(
            record.get("priority")))
    analysis = record.get("analysis")
    if not isinstance(analysis, dict):
        issues.append("record analysis must be an object")
        analysis = {}
    for step in ANALYSIS_STEPS:
        if step not in analysis:
            issues.append("record analysis missing step {0!r}".format(step))
    dependency = analysis.get("dependency")
    if isinstance(dependency, dict) and dependency.get("unknown_deps"):
        issues.append("record dependency analysis contains unknown deps: "
                      "{0}".format(", ".join(dependency["unknown_deps"])))
    snapshot = record.get("snapshot")
    if not isinstance(snapshot, dict):
        issues.append("record snapshot must be an object")
    else:
        if snapshot.get("tool") != "task-priority-analysis":
            issues.append("record snapshot.tool must be "
                          "'task-priority-analysis' (got {0!r})".format(
                              snapshot.get("tool")))
        if not snapshot.get("report_json"):
            issues.append("record snapshot.report_json is empty")
        if not snapshot.get("report_text"):
            issues.append("record snapshot.report_text is empty")
    return issues


def _evidence_dates_by_task(evidence_text: str, task_id: str) -> list:
    """Earliest date set for one task across evidence-log rows.

    R0 P1-1 (fail-open fix): ONLY the evidence date column (8th column,
    ``cells[7]``) is scanned. Description/basis/artifact cells routinely
    embed dates (e.g. ``"自 2026-07-14（FIX-201）起"``) — scanning every
    cell made ``earliest[0]`` land before TRIAGE_NORMALIZATION_DATE and
    silently exempted post-normalization product-code tasks from the
    no-record enforcement. Rows without a date column are skipped.
    """
    dates = []
    for line in str(evidence_text or "").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 8:
            continue
        if task_id not in cells[1]:
            continue
        match = _ISO_DATE_RE.search(cells[7])
        if match:
            try:
                dates.append(date.fromisoformat(match.group(1)))
            except ValueError:
                continue
    return sorted(dates)


def _evidence_has_product_code(evidence_text: str, task_id: str) -> bool:
    """True when any evidence row for the task carries a product-code path."""
    for line in str(evidence_text or "").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 7:
            continue
        if task_id not in cells[1]:
            continue
        blob = " ".join(cells[3:7])
        if any(pattern in blob for pattern in TRIAGE_PRODUCT_CODE_PATTERNS):
            return True
    return False


def check_change_triage(root=None, governance_dir=None,
                        verify_path=None) -> dict:
    """Check 32 — change-control triage enforcement (FIX-237.4).

    Args:
        root: host project root (defaults to the shared ROOT via
            verify_workflow when None).
        governance_dir: explicit ``.governance`` dir override (tests).
        verify_path: explicit verify_workflow.py path for the wiring scan
            (defaults to the plugin-root path).

    Returns:
        dict ``{"verdict", "issues", "wiring", "records_checked",
        "records_invalid", "tasks_without_record", "tasks_exempt"}``.
        Never raises.
    """
    issues = []
    if governance_dir is None:
        try:
            import verify_workflow as _vw
            governance_dir = _vw.GOVERNANCE_DIR
        except Exception:  # noqa: BLE001 — degrade to missing-dir scan
            governance_dir = None
    if root is None:
        try:
            import verify_workflow as _vw
            root = _vw.ROOT
        except Exception:  # noqa: BLE001
            root = Path(governance_dir).parent if governance_dir else Path.cwd()
    root = Path(root)
    if verify_path is None:
        verify_path = _verify_workflow_path(root)

    # 1. CLI wiring (the gate must stay registered).
    wiring = check_triage_wiring(verify_path)
    if not wiring["registered"]:
        issues.append("change-triage CLI wiring missing: {0}".format(
            wiring["reason"]))

    # 2. Record validity.
    rec_dir = Path(governance_dir) / "change-triage" \
        if governance_dir else None
    records = []
    records_checked = 0
    records_invalid = 0
    if rec_dir is not None and rec_dir.is_dir():
        for path in sorted(rec_dir.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                records_invalid += 1
                issues.append("triage record {0} unparseable: {1}".format(
                    path.name, exc))
                continue
            records.append(record)
            records_checked += 1
            for issue in validate_triage_record(record):
                records_invalid += 1
                issues.append("triage record {0}: {1}".format(
                    path.name, issue))

    # 3. No-record → FAIL for post-normalization product-code tasks.
    tasks_without_record = []
    tasks_exempt = 0
    plan_path = Path(governance_dir) / "plan-tracker.md" \
        if governance_dir else None
    evidence_path = Path(governance_dir) / "evidence-log.md" \
        if governance_dir else None
    recorded_ids = {str(r.get("task_id", "")) for r in records}
    if plan_path is not None and plan_path.is_file():
        try:
            tasks = parse_task_dependencies(
                plan_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — never raise from a check
            tasks = []
        evidence_text = ""
        if evidence_path is not None and evidence_path.is_file():
            try:
                evidence_text = evidence_path.read_text(encoding="utf-8")
            except OSError:
                evidence_text = ""
        for task in tasks:
            if task.is_completed():
                continue
            if task.task_id in recorded_ids:
                continue
            earliest = _evidence_dates_by_task(evidence_text, task.task_id)
            if not earliest:
                tasks_exempt += 1  # undatable — CLI gate is primary
                continue
            if earliest[0] < TRIAGE_NORMALIZATION_DATE:
                tasks_exempt += 1  # historical task (pre-feature)
                continue
            if not _evidence_has_product_code(evidence_text, task.task_id):
                tasks_exempt += 1  # quick lane (.governance/-only)
                continue
            tasks_without_record.append(task.task_id)

    if tasks_without_record:
        issues.append(
            "product-code task(s) with post-normalization evidence but no "
            "triage record: {0} (MUST run change-triage before creating "
            "the task — FIX-237.4 fail-closed)".format(
                ", ".join(sorted(tasks_without_record))))

    return {
        "verdict": "PASS" if not issues else "FAIL",
        "issues": issues,
        "wiring": wiring,
        "records_checked": records_checked,
        "records_invalid": records_invalid,
        "tasks_without_record": sorted(tasks_without_record),
        "tasks_exempt": tasks_exempt,
    }


# ── Check 39 (FIX-274 / F-03): requires_r1 completion gate ─────────────
#
# The R1 flag produced by change-triage step-e (FIX-271 R2) gets its first
# machine downstream consumer here: R1 is only as strong as the evidence
# that the one-of-three fact actually happened by the time the task is
# called complete (R0 BC-2: WARN alone does not survive Coordinator
# inattention).
#
# DEC-159 progressive strategy — tightening condition (explicit): missing
# evidence is WARN throughout the 0.77.x observation window; the check
# escalates to FAIL after 2 consecutive 0.77.x releases close with zero
# r1-evidence violations (escalation flip = decision-log entry).

# R1 one-of-three evidence keyword groups (M7.7 R1 (a)/(b)/(c)). An
# evidence-log row for the task matching ANY group counts as the R1
# 留痕 fact. Existence-only keyword match — the check never tries to
# prove the fact semantically (that boundary stays with human review).
R1_EVIDENCE_KEYWORD_GROUPS = (
    # (a) isolation — env-var redirect to a temp dir
    ("隔离环境", "环境变量重定向", "重定向至临时目录"),
    # (b) backup — full snapshot AND post-operation consistency check.
    #     AND-combined below: a backup word alone must NOT satisfy — the
    #     completion-recommendation rows ("调用快照记入 evidence-log") and
    #     TRIAGE metadata rows ("命令输出 JSON 快照见 change-triage/…")
    #     legitimately contain 快照 without claiming an R1(b) backup
    #     (review-FIX-274-CODE-R0 P1-1).
    ("备份", "快照"),
    # (c) per-item user authorization via ask_user_question
    ("逐项授权", "用户授权", "用户显式授权"),
)

# Group (b) verification half: the backup/snapshot word MUST appear
# together with at least one of these to count as R1(b) "完整备份 +
# 操作后一致性校验" (AND-combination in :func:`_r1_evidence_rows`).
R1_EVIDENCE_B_VERIFY_KEYWORDS = ("校验", "一致性", "核对")

# Evidence rows that are machine metadata, never R1-evidence carriers:
# change-control triage / review-machine / completion-recommendation rows.
R1_EVIDENCE_METADATA_PREFIXES = ("TRIAGE-", "RECO-", "REVIEW-")


def _r1_evidence_rows(evidence_text: str, task_id: str) -> list:
    """Evidence rows for one task that carry an R1 one-of-three keyword.

    Row/column convention mirrors :func:`_evidence_has_product_code`: the
    task id MUST appear in the second column (``cells[1]``) and keywords
    are matched against the descriptive cells (``cells[3:7]``) only — never
    the whole row. Machine metadata rows (TRIAGE-/RECO-/REVIEW- id
    prefixes) are skipped: their fixed templates embed "命令输出 JSON
    快照见 change-triage/{id}.json", which would otherwise hit the group
    (b) 快照 keyword (review-FIX-274-CODE-R0 P1-1); a backup word alone
    likewise never satisfies (b) — it is AND-combined with
    :data:`R1_EVIDENCE_B_VERIFY_KEYWORDS`.
    """
    hits = []
    for line in str(evidence_text or "").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3 or task_id not in cells[1]:
            continue
        if cells[0].startswith(R1_EVIDENCE_METADATA_PREFIXES):
            continue
        if len(cells) < 7:
            # too short to carry the descriptive cells (convention cells[3:7])
            continue
        blob = " ".join(cells[3:7])
        for idx, group in enumerate(R1_EVIDENCE_KEYWORD_GROUPS):
            if not any(k in blob for k in group):
                continue
            # idx 1 = group (b): 备份/快照 AND 校验/一致性/核对.
            if idx == 1 and not any(
                    v in blob for v in R1_EVIDENCE_B_VERIFY_KEYWORDS):
                continue
            hits.append(line)
            break
    return hits


def check_r1_completion_gate(root=None, governance_dir=None) -> dict:
    """Check 39 — requires_r1 completion gate (FIX-274 F-03 / M7.7 R1).

    For every triage record with ``analysis.side_effect.requires_r1 ==
    true``: when the task is marked completed in the plan-tracker, the
    evidence-log MUST contain an R1 留痕 row for that task (one-of-three
    keyword fact per :data:`R1_EVIDENCE_KEYWORD_GROUPS`). Missing → WARN
    (DEC-159 observation window; tightening condition registered in the
    module docstring — escalation to FAIL after 2 consecutive
    violation-free 0.77.x releases).

    Scope notes:
      - Unlanded records (task not in plan-tracker yet) and incomplete
        tasks are skipped — the gate fires only at completion marking.
      - Record validity is Check 32's domain; unparseable records are
        skipped here.
      - Pre-FIX-271 records without ``side_effect`` are naturally out of
        scope (no flag → not judged), so no date exemption is needed.

    Returns:
        dict ``{"verdict" ∈ {"PASS", "WARN", "no-verdict"}, "reason",
        "warnings": [{"rule", "task_id", "reason"}], "stats"}``. Never
        raises. WARN never increments the check-governance issue count
        during the observation window (Check 30c convention).
    """
    result = {
        "verdict": "no-verdict",
        "reason": "",
        "warnings": [],
        "stats": {
            "records_scanned": 0,
            "r1_records": 0,
            "tasks_judged": 0,
            "tasks_skipped_incomplete": 0,
            "tasks_skipped_unlanded": 0,
            "pass": 0,
            "warn": 0,
        },
    }
    stats = result["stats"]
    if governance_dir is None:
        try:
            import verify_workflow as _vw
            governance_dir = _vw.GOVERNANCE_DIR
        except Exception:  # noqa: BLE001 — degrade to no-verdict
            governance_dir = None
    if root is None:
        try:
            import verify_workflow as _vw
            root = _vw.ROOT
        except Exception:  # noqa: BLE001
            root = Path(governance_dir).parent if governance_dir else Path.cwd()
    gov = Path(governance_dir) if governance_dir else None
    if gov is None or not gov.is_dir():
        result["reason"] = "no .governance dir — nothing to judge"
        return result

    # 1. Collect requires_r1 task ids from triage records.
    r1_task_ids = []
    rec_dir = gov / "change-triage"
    if rec_dir.is_dir():
        for path in sorted(rec_dir.glob("*.json")):
            stats["records_scanned"] += 1
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue  # record validity is Check 32's domain
            side_effect = (record.get("analysis") or {}).get("side_effect")
            if (isinstance(side_effect, dict)
                    and side_effect.get("requires_r1") is True):
                r1_task_ids.append(str(record.get("task_id") or path.stem))
    r1_task_ids = sorted(dict.fromkeys(r1_task_ids))
    stats["r1_records"] = len(r1_task_ids)
    if not r1_task_ids:
        result["verdict"] = "PASS"
        result["reason"] = ("no requires_r1 triage records — "
                            "completion gate vacuous")
        return result

    # 2. Plan-tracker task states (unreadable → no-verdict, fail-safe).
    plan_path = gov / "plan-tracker.md"
    if not plan_path.is_file():
        result["reason"] = "plan-tracker missing — cannot judge completion"
        return result
    try:
        tasks = parse_task_dependencies(
            plan_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — never raise from a check
        result["reason"] = "plan-tracker unparseable — cannot judge completion"
        return result
    task_by_id = {task.task_id: task for task in tasks}

    # 3. Evidence text (missing log = no evidence anywhere).
    evidence_text = ""
    evidence_path = gov / "evidence-log.md"
    if evidence_path.is_file():
        try:
            evidence_text = evidence_path.read_text(encoding="utf-8")
        except OSError:
            evidence_text = ""

    # 4. Judge each r1 task.
    for task_id in r1_task_ids:
        task = task_by_id.get(task_id)
        if task is None:
            stats["tasks_skipped_unlanded"] += 1
            continue
        if not task.is_completed():
            stats["tasks_skipped_incomplete"] += 1
            continue
        stats["tasks_judged"] += 1
        if _r1_evidence_rows(evidence_text, task_id):
            stats["pass"] += 1
        else:
            stats["warn"] += 1
            result["warnings"].append({
                "rule": "r1-evidence",
                "task_id": task_id,
                "reason": (
                    "completed with analysis.side_effect.requires_r1=true "
                    "but no R1 留痕 evidence row found (one-of-three: "
                    "isolation redirect / backup + verification / "
                    "per-item user authorization — M7.7 R1, FIX-274 "
                    "observation-window WARN)"
                ),
            })

    if result["warnings"]:
        result["verdict"] = "WARN"
        result["reason"] = (
            "{0} completed requires_r1 task(s) missing R1 evidence "
            "(WARN — 0.77.x observation window; escalates to FAIL after "
            "2 consecutive violation-free 0.77.x releases per "
            "DEC-159)".format(len(result["warnings"])))
    else:
        result["verdict"] = "PASS"
        result["reason"] = (
            "{0} requires_r1 task(s) judged; all carry R1 留痕 "
            "evidence".format(stats["tasks_judged"]))
    return result


__all__ = [
    "TRIAGE_NORMALIZATION_DATE",
    "check_triage_wiring",
    "validate_triage_record",
    "check_change_triage",
    "R1_EVIDENCE_KEYWORD_GROUPS",
    "check_r1_completion_gate",
]
