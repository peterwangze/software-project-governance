#!/usr/bin/env python3
"""Read-only bootstrap aggregate — FEAT-033 (AUDIT-154 slice A-2, v0.84.0).

One command that answers "where am I and what is next" in a single output,
replacing the bootstrap protocol's multi-file reads + repeated verify calls
(AUDIT-154 measured 31 tool calls / 19 serial round-trips per session turn;
arch consultant P0: aggregating into one command is the precondition for
19 -> 2-4 serial steps).

Aggregated faces (single output, ≤2K token / ≤8KB projection):

* ``resolve``   — the resolve_entry envelope subset (dual-root authority,
                  DEC-096 / DEC-080; reused via import, never re-derived).
* ``migration`` — version-comparison FLAG only (active_version vs the
                  plan-tracker record). Never executes a migration.
* ``project`` / ``gates`` / ``tasks`` / ``risks`` / ``recent`` — a LEAN
                  status projection parsed line-wise from the hot governance
                  files. The regexes/table shapes deliberately MIRROR the
                  proven engine calibers (``parse_project_config`` /
                  ``parse_gate_status`` / ``parse_active_risks`` /
                  ``parse_recent_decisions`` and resolve_entry's plan-tracker
                  version regex) the same way resolve_entry mirrors the
                  engine — disclosed here so the two readers stay in sync by
                  review, not by import (see the R2 note below). R0 P0-1
                  lesson (0.84.0 R1): review-only sync demonstrably failed on
                  live-shaped files, so the table scanner now mirrors the
                  engine's ``_status_table_stream`` LINE FOR LINE
                  (separator-validated headers; blank lines tolerated INSIDE
                  a table, never terminators) and a bidirectional
                  differential test against the engine stream guards the
                  mirror (``SegmentedTableMirrorTests``).
* ``candidates``— the task-priority-analysis LIGHT path reused verbatim via
                  ``import task_priority`` (pure-stdlib peer leaf:
                  parse_task_dependencies + compute_unblocked_tasks). Empty
                  recommendations carry the structured ``empty_reason`` /
                  ``unblock_recommendation`` (REQ-110 / FIX-254) — never a
                  bare empty list.
* ``health``    — v1 contract: ``state="deferred"`` + ``pending_checks`` +
                  a ``check-governance`` next_action. NO health check has
                  run — this command never pretends it did (QR-4 禁「没查」
                  报「通过」).
* ``next_actions`` / ``deferred`` — derived guidance and the fail-safe
                  budget disclosure.

Budget + honesty contract:

* ``--budget-ms`` (default 3000): a monotonic wall-clock deadline checked
  between build phases. On exhaustion the command returns everything
  finished so far plus a ``deferred`` list naming each section that did not
  run (``reason: "budget_exhausted"``) — fail-safe, never a guessed pass.
* Read-only and idempotent: zero ``.governance`` writes, zero git writes,
  zero subprocess dispatch, no archive/migration invocation. Two runs over
  an unchanged tree produce identical payloads modulo the declared
  volatile fields (``generated_at`` / ``duration_ms``).

Boundary (same discipline as governance_cost.py / archguard_ratchet.py):
this module MUST NOT import ``verify_workflow`` (ArchGuard R2 — zero new
reverse edges; the engine only wires dispatch). Its own import face is
stdlib-only (ArchGuard R6 cold-import budget) plus the two engine-free
peer leaves ``resolve_entry`` and ``task_priority``.

Usage:
    python <plugin_home>/infra/verify_workflow.py governance-bootstrap \\
        [--budget-ms N] [--format json|text] [--profile lite|standard|strict]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

import resolve_entry  # peer leaf — the dual-root authority (DEC-096)
import task_priority  # peer leaf — pure dependency analysis (FIX-226)

REPORT_SCHEMA = "governance-bootstrap/1"
TASK_ID = "FEAT-033"

DEFAULT_BUDGET_MS = 3000
MAX_JSON_BYTES = 8192

#: v1 health contract — deferred, never faked (QR-4).
PENDING_CHECKS = ("check-governance", "verify")
HEALTH_NEXT_ACTION = (
    "run `python <plugin_home>/infra/verify_workflow.py check-governance "
    "--summary-only` — the v1 aggregate did NOT run health checks "
    "(FEAT-033 defers quick-scan wiring; FEAT-034 owns the protocol rework)")

#: Candidate / recency caps per --profile (v1: projection detail only).
PROFILE_CAPS = {
    "lite": {"candidates": 1, "recent": 0, "overview": False},
    "standard": {"candidates": 3, "recent": 3, "overview": True},
    "strict": {"candidates": 5, "recent": 5, "overview": True},
}

#: Mirror of resolve_entry._PLAN_TRACKER_VERSION_RE (documented mirror —
#: resolve_entry cannot be the importer here either; see module docstring).
_PLAN_TRACKER_VERSION_RE = re.compile(r"工作流版本[**:\s]+(\d+\.\d+\.\d+)")

_GATE_SECTION_PREFIX = "## Gate 状态跟踪"
_ID_TOKEN_RE = re.compile(r"^[A-Z]+-\d+$")

#: Engine-identical separator-row shape (``_status_table_stream``): the ONLY
#: table validator — a ``|`` row without a separator row below it is prose
#: with pipes (or a continuation data row), never a table header.
_SEPARATOR_ROW_RE = re.compile(r"^\|[\s:\-|]+\|$")


class _BudgetExhausted(Exception):
    """Internal control flow: the wall-clock deadline has passed."""


#: Projection cell clip — hot-file config cells can carry long prose (live
#: dogfood stage lines are paragraph-sized); the ≤2K-token projection keeps
#: the head and marks the cut (truncation is disclosed, never fabricated).
CLIP_LIMIT = 80

#: R0 P2-1: recent topic clip limit — same 60-char budget as the engine's
#: ``parse_recent_decisions``, but applied through the DISCLOSED ``_clip``
#: marker instead of the engine's silent ``[:60]`` (declared divergence:
#: this projection never truncates silently; the engine's own silent cut is
#: upstream debt).
RECENT_TOPIC_LIMIT = 60


def _clip(value, limit=CLIP_LIMIT):
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


# ── version comparison (migration flag — flag only, never execution) ────────


def _version_tuple(version):
    """Mirror of resolve_entry._version_tuple (best-effort semver tuple)."""
    try:
        parts = [int(p) for p in str(version).split(".")]
    except (TypeError, ValueError):
        return None
    if not parts:
        return None
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def migration_flag(plan_version, active_version):
    """Pure version-comparison flag (FEAT-033 contract: 标志不执行)."""
    plan_t = _version_tuple(plan_version)
    active_t = _version_tuple(active_version)
    base = {
        "plan_version": str(plan_version or "") or None,
        "active_version": str(active_version or "") or None,
    }
    if plan_t is None or active_t is None:
        base.update({"required": False, "status": "unknown"})
        return base
    if plan_t < active_t:
        base.update({"required": True, "status": "upgrade_available"})
    elif plan_t > active_t:
        base.update({"required": False, "status": "plan_ahead"})
    else:
        base.update({"required": False, "status": "up_to_date"})
    return base


# ── lean mirrors of the engine's hot-file readers (text-in, dict-out) ────────
#
# Every reader below takes the file TEXT (pure — no I/O) and mirrors one
# engine reader's caliber. Mirrors, not imports: importing the engine is the
# ArchGuard R2 red line, and resolve_entry already established the disclosed
# mirror discipline for exactly this situation.


def _section_lines(text, section_prefix):
    """Yield lines of a `## ` section (until the next `## ` heading)."""
    inside = False
    for line in text.split("\n"):
        stripped = line.strip()
        if inside and stripped.startswith("## "):
            return
        if not inside and stripped.startswith(section_prefix):
            inside = True
            continue
        if inside:
            yield line


def _table_rows(lines):
    """Split markdown table lines into cell lists (header + separator kept
    distinguishable: returns (header_cells | None, [data_cell_lists]))."""
    header = None
    rows = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.split("|")[1:-1]]
        if all(set(c) <= {"-", ":", " "} for c in cells):
            continue  # separator row
        if header is None:
            header = cells
            continue
        rows.append(cells)
    return header, rows


def parse_project_config(text):
    """Mirror of verify_workflow.parse_project_config (`## 项目配置`)."""
    config = {}
    for line in _section_lines(text, "## 项目配置"):
        m = re.match(r"- \*\*(.+?)\*\*:\s*(.+)", line)
        if m:
            config[m.group(1)] = m.group(2).strip()
    return config


def parse_overview_row(text):
    """Mirror of verify_workflow.parse_overview (first `## 项目总览` row)."""
    for line in _section_lines(text, "## 项目总览"):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        parts = [p.strip() for p in stripped.split("|")[1:-1]]
        if len(parts) >= 8 and parts[0] != "项目" and not all(
                set(p) <= {"-", " "} for p in parts):
            return {
                "project": parts[0], "current_stage": parts[1],
                "total": parts[2], "completed": parts[3],
                "blocked": parts[4], "risks": parts[5],
                "latest_gate": parts[6], "latest_retro": parts[7],
            }
    return {}


#: Bootstrap-local gate bucket contract (R0 P2-2) — the CLOSED vocabulary of
#: the domain's gate status word forms (engine ``parse_gate_status`` cells;
#: state names shared with checks/gate_domain), matched EXACTLY after a
#: whitespace/backtick/emphasis strip + lowercase. NOT a substring scan: a
#: future superset word form that merely CONTAINS one of these tokens (the
#: review's mis-bucket vector, e.g. a hypothetical "unpassed") falls through
#: to ``other`` instead of silently joining a bucket. The engine-side
#: predicate is not importable here (engine-free boundary — module
#: docstring), and checks/gate_domain's conservative interlock classifier
#: merges ``failed`` into ``pending`` — a different contract than this count
#: face — so the vocabulary mirror is declared here instead of imported.
_GATE_PASSED_STATES = frozenset((
    "passed", "passed-on-entry", "passed-with-conditions", "pass"))
_GATE_PENDING_STATES = frozenset(("pending",))
_GATE_FAILED_STATES = frozenset(("failed", "fail"))


def _gate_bucket(status_cell):
    """Bucket a gate status cell for the counts face (contract above)."""
    s = (status_cell or "").strip().lower().strip("`*").strip()
    if s in _GATE_PASSED_STATES:
        return "passed"
    if s in _GATE_PENDING_STATES:
        return "pending"
    if s in _GATE_FAILED_STATES:
        return "failed"
    return "other"


def parse_gate_summary(text):
    """Mirror of verify_workflow.parse_gate_status, aggregated to counts.

    The ≤2K-token projection carries counts + the first pending gate id —
    not the full table (the engine ``status`` command remains the full-face
    dependency).
    """
    counts = {"total": 0, "passed": 0, "pending": 0, "failed": 0, "other": 0}
    next_gate = None
    header, rows = _table_rows(_section_lines(text, _GATE_SECTION_PREFIX))
    if header is None:
        return dict(counts, next_gate=None)
    gate_idx, status_idx = 0, None
    for pos, name in enumerate(header):
        if name.lower() == "status" or name == "状态":
            status_idx = pos
            break
    if status_idx is None:
        status_idx = 2  # engine caliber: parts[2] is the status column
    for cells in rows:
        if len(cells) <= max(gate_idx, status_idx):
            continue
        counts["total"] += 1
        bucket = _gate_bucket(cells[status_idx])
        counts[bucket] += 1
        if next_gate is None and bucket == "pending":
            next_gate = cells[gate_idx]
    return dict(counts, next_gate=next_gate)


def parse_risk_summary(text, today=None):
    """Mirror of verify_workflow.parse_active_risks, aggregated to counts.

    Open predicate mirrors the risk domain's canonical judgement (checks/
    risk_domain.is_risk_status_open): a risk is open iff its 当前状态 cell
    is exactly ``打开`` — no parallel marker sets.
    """
    today = today or date.today()
    summary = {"open": 0, "escalation_overdue": 0, "escalation_soon": 0,
               "overdue_ids": []}
    for header, rows in _iter_positional_tables(text):
        if "编号" not in header or "当前状态" not in header:
            continue
        id_pos = header.index("编号")
        status_pos = header.index("当前状态")
        deadline_pos = header.index("截止日期") if "截止日期" in header else None
        width = max(p for p in (id_pos, status_pos, deadline_pos)
                    if p is not None)
        for cells in rows:
            if len(cells) <= width:
                continue
            if cells[status_pos].strip() != "打开":
                continue
            rid = cells[id_pos].strip()
            if not rid:
                continue
            summary["open"] += 1
            deadline = (cells[deadline_pos].strip()
                        if deadline_pos is not None else "")
            days_left = None
            if deadline:
                try:
                    days_left = (date.fromisoformat(deadline[:10]) - today).days
                except ValueError:
                    days_left = None
            if days_left is not None:
                if days_left < 0:
                    summary["escalation_overdue"] += 1
                    if len(summary["overdue_ids"]) < 3:
                        summary["overdue_ids"].append(rid)
                if days_left <= 3:
                    summary["escalation_soon"] += 1
    return summary


def parse_recent_decisions(text, limit=3):
    """Mirror of verify_workflow.parse_recent_decisions (date-ranked).

    FIX-270 R0 F2 caliber: document order is NOT time order; rows rank by
    their 日期 cell then the numeric ID suffix. A row with no parseable
    date sorts oldest — it cannot masquerade as "recent".

    R0 P2-1: the topic mirrors the engine's PER-ROW fallback (主题 cell,
    else the 决策内容 cell) and is clipped through the DISCLOSED ``_clip``
    marker — a declared divergence from the engine's silent ``[:60]`` (see
    ``RECENT_TOPIC_LIMIT``).
    """
    rows = []
    for header, rows_cells in _iter_positional_tables(text):
        if "编号" not in header:
            continue
        id_pos = header.index("编号")
        date_pos = header.index("日期") if "日期" in header else None
        topic_pos = header.index("主题") if "主题" in header else None
        content_pos = (header.index("决策内容")
                       if "决策内容" in header else None)
        if topic_pos is None and content_pos is None:
            continue
        width = max(p for p in (id_pos, date_pos, topic_pos, content_pos)
                    if p is not None)
        for cells in rows_cells:
            if len(cells) <= width:
                continue
            rid = cells[id_pos].strip()
            if not _ID_TOKEN_RE.match(rid):
                continue
            dtext = cells[date_pos].strip() if date_pos is not None else ""
            topic_cell = (cells[topic_pos].strip()
                          if topic_pos is not None else "")
            content_cell = (cells[content_pos].strip()
                            if content_pos is not None else "")
            rows.append({
                "id": rid,
                "date": dtext,
                "topic": _clip(topic_cell or content_cell,
                               RECENT_TOPIC_LIMIT),
            })

    def _sort_key(rec):
        parsed = None
        if rec["date"] and rec["date"] != "—":
            try:
                parsed = date.fromisoformat(rec["date"][:10])
            except ValueError:
                parsed = None
        m = _ID_TOKEN_RE.match(rec["id"])
        id_num = int(m.group(0).split("-")[1]) if m else 0
        if parsed is None:
            return (False, date.min, -1)  # 无日期 → 最旧，不可冒充"最近"
        return (True, parsed, id_num)

    rows.sort(key=_sort_key, reverse=True)
    return rows[:limit]


def _iter_positional_tables(text):
    """Yield (header_cell_list, [data_cell_lists]) per markdown table.

    R0 P0-1 fix: LINE-FOR-LINE mirror of the engine's
    ``_status_table_stream`` (verify_workflow.py). The previous local
    scanner diverged on live-shaped files — a blank line inside a table
    terminated it (every later row landed in a ghost table headed by a
    data row, then was dropped) and any leading ``|`` row became a header
    without a separator check. Mirrored semantics:

    * a table starts at a ``|`` row whose next NON-BLANK row is the
      ``---`` separator — a ``|`` row without a separator below is NOT a
      header (data rows can never masquerade as headers / ghost tables);
    * blank lines INSIDE a table are tolerated, never terminators (the
      live plan-tracker/risk-log insert them between sub-groups);
    * a non-``|`` line ends the table.

    Guarded against drift by the bidirectional differential test against
    the engine stream (``SegmentedTableMirrorTests``).
    """
    lines = text.split("\n")
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        if not line.startswith("|"):
            i += 1
            continue
        header = [c.strip() for c in line.split("|")[1:-1]]
        j = i + 1
        while j < n and not lines[j].strip():
            j += 1
        if j >= n or not _SEPARATOR_ROW_RE.match(lines[j].strip()):
            i += 1
            continue
        k = j + 1
        rows = []
        while k < n:
            r = lines[k].strip()
            if not r:
                k += 1
                continue
            if not r.startswith("|"):
                break
            if _SEPARATOR_ROW_RE.match(r):
                k += 1
                continue
            rows.append([c.strip() for c in r.split("|")[1:-1]])
            k += 1
        yield header, rows
        i = k


def plan_tracker_version(text):
    """Mirror of resolve_entry's plan-tracker version extraction."""
    m = _PLAN_TRACKER_VERSION_RE.search(text or "")
    return m.group(1) if m else None


# ── candidates: the task-priority-analysis light path (reused verbatim) ─────


def _candidate_items(report, cap):
    items = []
    for task in list(report.recommended_next)[:cap]:
        items.append({
            "task_id": task.task_id,
            "priority": task.priority,
            "status": _clip(task.status, 40),
            "target_version": _clip(task.target_version, 20),
            "deps_satisfied": True,
            "reason": "dependency-satisfied; ranked by "
                      "task-priority-analysis (priority, target version)",
        })
    return items


def _candidate_empty(report):
    """Structured empty-reason face (REQ-110 — never a bare empty list)."""
    out = {"items": [], "source": "task-priority-analysis(light)"}
    if report.empty_reason:
        reason = dict(report.empty_reason)
        for key in ("message", "nearest_action"):
            if reason.get(key):
                reason[key] = _clip(reason[key], 160)
        out["empty_reason"] = reason
    if report.unblock_recommendation is not None:
        rec = report.unblock_recommendation
        out["unblock_recommendation"] = {
            "root_task_id": rec.root_task_id,
            "root_kind": rec.root_kind,
            "downstream_count": rec.downstream_count,
            "reason": _clip(rec.reason, 160),
        }
    if report.cycle_warning:
        out["cycle_warning"] = True
    return out


def candidates_face(plan_text, cap):
    """Run the light tpa path and shape the candidates projection."""
    tasks = task_priority.parse_task_dependencies(plan_text)
    report = task_priority.compute_unblocked_tasks(tasks)
    face = _candidate_empty(report)
    face["items"] = _candidate_items(report, cap)
    face["analysis"] = {
        "total": report.total,
        "completed": len(report.completed),
        "unblocked": len(report.unblocked),
        "blocked": len(report.blocked),
        "non_executable": len(report.non_executable),
    }
    return face, report


def task_stats_face(report):
    """Task stats derived from the SAME light parse (one fact read)."""
    in_progress = 0
    p0_pending = 0
    for task in list(report.completed) + list(report.unblocked) \
            + [b.task for b in report.blocked] + list(report.non_executable):
        status = task.status or ""
        if ("进行中" in status) or status.strip().startswith("🔄"):
            in_progress += 1
        if task.priority == "P0" and not task.is_completed():
            p0_pending += 1
    return {
        "total": report.total,
        "completed": len(report.completed),
        "unblocked": len(report.unblocked),
        "blocked": len(report.blocked),
        "non_executable": len(report.non_executable),
        "in_progress": in_progress,
        "p0_pending": p0_pending,
        "source": "plan-tracker task tables (task-priority light parse)",
    }


# ── orchestration (the only I/O-bearing path: the cmd entry below) ──────────


@dataclass
class _Builder:
    """Phase orchestrator with the wall-clock budget check between phases."""

    plan_text: str = ""
    report: object = None
    payload: dict = field(default_factory=dict)
    deferred: list = field(default_factory=list)
    deadline: float = 0.0

    def check_budget(self, section):
        if time.monotonic() >= self.deadline:
            self.deferred.append({"section": section,
                                  "reason": "budget_exhausted"})
            raise _BudgetExhausted()


def _build_payload(host_root, envelope, budget_ms, profile, started):
    caps = PROFILE_CAPS[profile]
    payload = {
        "schema": REPORT_SCHEMA,
        "task": TASK_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds").replace("+00:00", "Z"),
        "budget_ms": budget_ms,
        "profile": profile,
        "resolve": {
            "plugin_home": envelope["plugin_home"],
            "host_project_root": envelope["host_project_root"],
            "active_version": envelope["active_version"],
            "scenario_hint": envelope["scenario_hint"],
            "resolved_root_ok": envelope["resolved_root_ok"],
            "governance_initialized": envelope["governance_initialized"],
            "snapshot_exists": envelope["snapshot_exists"],
            "snapshot_fresh": envelope["snapshot_fresh"],
            "hooks_installed": envelope["hooks_installed"],
            "diagnostic": envelope["diagnostic"],
        },
    }

    gov_dir = host_root / ".governance"
    plan_path = gov_dir / "plan-tracker.md"
    builder = _Builder(deadline=started + budget_ms / 1000.0)

    if not envelope["governance_initialized"]:
        payload["notes"] = [
            ".governance/plan-tracker.md not found — governance faces are "
            "absent (not failed); run /governance to initialize or onboard."]
        payload["health"] = _health_face()
        payload["next_actions"] = [
            "运行 /governance 初始化或接入项目治理（当前 .governance/ 缺失）"]
        payload["deferred"] = []
        payload["duration_ms"] = int((time.monotonic() - started) * 1000)
        return payload

    plan_text = _read_text(plan_path)

    try:
        builder.check_budget("project")
        config = parse_project_config(plan_text)
        project = {
            "name": _clip(config.get("项目名称") or "N/A"),
            "stage": _clip(config.get("当前阶段", "")),
            "profile": _clip(config.get("Profile", "")),
            "trigger_mode": _clip(config.get("触发模式", "")),
            "permission_mode": _clip(config.get("操作权限模式")
                                     or config.get("permission_mode", "")),
            "workflow_version": _clip(config.get("工作流版本", "")),
        }
        if caps["overview"]:
            project["overview"] = parse_overview_row(plan_text)
        if project["name"] == "N/A" and project.get("overview", {}).get(
                "project"):
            # engine _status_project_name caliber: config name first,
            # overview row as fallback.
            project["name"] = _clip(project["overview"]["project"])
        payload["project"] = project

        builder.check_budget("gates")
        payload["gates"] = parse_gate_summary(plan_text)

        builder.check_budget("tasks")
        face, report = candidates_face(
            plan_text, caps["candidates"])
        payload["tasks"] = task_stats_face(report)
        builder.report = report

        builder.check_budget("risks")
        risk_text = _read_text(gov_dir / "risk-log.md")
        payload["risks"] = parse_risk_summary(risk_text)

        builder.check_budget("migration")
        payload["migration"] = migration_flag(
            plan_tracker_version(plan_text), envelope["active_version"])

        if caps["recent"]:
            builder.check_budget("recent")
            decision_text = _read_text(gov_dir / "decision-log.md")
            payload["recent"] = {
                "decisions": parse_recent_decisions(decision_text,
                                                    limit=caps["recent"]),
            }

        builder.check_budget("candidates")
        payload["candidates"] = face
    except _BudgetExhausted:
        pass

    payload["health"] = _health_face()
    payload["next_actions"] = _next_actions(payload, envelope)
    payload["deferred"] = builder.deferred
    payload["duration_ms"] = int((time.monotonic() - started) * 1000)
    return payload


def _health_face():
    return {
        "state": "deferred",
        "reason": "v1 contract (FEAT-033): quick-scan four-state wiring is "
                  "deferred — no health check has been executed here",
        "pending_checks": list(PENDING_CHECKS),
        "next_action": HEALTH_NEXT_ACTION,
    }


def _next_actions(payload, envelope):
    actions = []
    if envelope["scenario_hint"] in ("A", "B"):
        actions.append("运行 /governance 完成初始化或接入（scenario %s）"
                       % envelope["scenario_hint"])
    migration = payload.get("migration") or {}
    if migration.get("required"):
        actions.append(
            "版本升级可用：active %s > plan-tracker %s — 走 /governance 升级"
            "流程（本命令只给标志，不执行迁移）"
            % (migration.get("active_version"), migration.get("plan_version")))
    risks = payload.get("risks") or {}
    if risks.get("escalation_overdue"):
        actions.append("处理逾期风险升级线：%s"
                       % ", ".join(risks.get("overdue_ids") or []))
    if (payload.get("health") or {}).get("state") == "deferred":
        actions.append("运行 check-governance 获取健康四态（本命令 v1 未接线）")
    candidates = payload.get("candidates") or {}
    if candidates.get("items"):
        top = candidates["items"][0]
        actions.append("从候选开始：%s（%s）"
                       % (top["task_id"], top["priority"]))
    elif candidates.get("empty_reason"):
        reason = candidates["empty_reason"]
        actions.append("无就绪候选：%s — %s"
                       % (reason.get("kind"),
                          reason.get("nearest_action") or reason.get(
                              "message", "")))
    hooks = (payload.get("resolve") or {}).get("hooks_installed") or {}
    if hooks and not all(hooks.values()):
        actions.append("安装治理 git hooks：cp <plugin_home>/infra/hooks/* "
                       ".git/hooks/")
    return actions[:5]


def _read_text(path):
    """UTF-8 read that never raises (missing/unreadable → empty text)."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# ── projection budget clamp (R0 P2-3: the ≤8KB promise gets a hard guard) ───


#: Emergency per-string ceiling for the last-resort clamp stage.
_EMERGENCY_CLIP = 120

_PROJECTION_CLAMP_NOTE = (
    "projection clamp (≤8KB output budget): %s — disclosed trim, all other "
    "content unchanged")


def _payload_bytes(payload):
    """Serialized size of the JSON face (the ≤8KB promise's unit)."""
    return len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def _clamp_strings(node, limit=_EMERGENCY_CLIP):
    """Recursive disclosed clip of every string leaf (deterministic walk)."""
    if isinstance(node, str):
        return _clip(node, limit)
    if isinstance(node, list):
        return [_clamp_strings(item, limit) for item in node]
    if isinstance(node, dict):
        return {key: _clamp_strings(value, limit)
                for key, value in node.items()}
    return node


def _enforce_projection_budget(payload, limit=MAX_JSON_BYTES):
    """Hard output-side clamp behind the ≤8KB projection promise (R0 P2-3).

    The build phases cap list lengths but not cell sizes: live overview rows
    carry KB-sized prose cells and ``resolve.diagnostic`` is a pass-through,
    so the serialized face was bounded only by hope. Deterministic staged
    trims, each disclosed in ``notes`` (a cut is never silent):

      ① ``resolve.diagnostic`` clipped to 200 chars;
      ② the ``project.overview`` row dropped (the live bloat source);
      ③ candidate items trimmed to the first;
      ④ emergency per-string clip (``_clamp_strings``) — bounds the payload
         unconditionally, so the function always terminates under the
         budget for any input shape.

    Idempotent: only content decides (never the clock) — two runs over an
    unchanged tree make the same trim decisions.
    """
    if _payload_bytes(payload) <= limit:
        return payload
    notes = list(payload.get("notes") or [])

    def over():
        return _payload_bytes(payload) > limit

    def disclose(detail):
        notes.append(_PROJECTION_CLAMP_NOTE % detail)
        payload["notes"] = notes

    resolve = dict(payload.get("resolve") or {})
    if resolve.get("diagnostic"):
        resolve["diagnostic"] = _clip(resolve["diagnostic"], 200)
        payload["resolve"] = resolve
        disclose("resolve.diagnostic clipped")
    if not over():
        return payload

    project = dict(payload.get("project") or {})
    if project.pop("overview", None) is not None:
        payload["project"] = project
        disclose("project.overview row dropped")
    if not over():
        return payload

    candidates = dict(payload.get("candidates") or {})
    items = candidates.get("items") or []
    if len(items) > 1:
        candidates["items"] = items[:1]
        payload["candidates"] = candidates
        disclose("candidates trimmed to the first item")
    if not over():
        return payload

    saved_notes = list(notes)
    payload.pop("notes", None)
    trimmed = _clamp_strings(payload)
    payload.clear()
    payload.update(trimmed)
    notes = saved_notes
    disclose("emergency per-string clip applied")
    return payload


# ── rendering ────────────────────────────────────────────────────────────────


def format_text(payload):
    """≤40-line human summary (the --format text face)."""
    resolve = payload.get("resolve") or {}
    project = payload.get("project") or {}
    gates = payload.get("gates") or {}
    tasks = payload.get("tasks") or {}
    risks = payload.get("risks") or {}
    candidates = payload.get("candidates") or {}
    migration = payload.get("migration") or {}
    lines = [
        "=== Governance Bootstrap (FEAT-033 — schema %s) ==="
        % REPORT_SCHEMA,
        "root: %s | scenario: %s | active=%s plan=%s (%s)"
        % (resolve.get("host_project_root"), resolve.get("scenario_hint"),
           resolve.get("active_version"), migration.get("plan_version"),
           migration.get("status", "unknown")),
        "project: %s | %s | profile=%s trigger=%s permission=%s"
        % (project.get("name"), project.get("stage"),
           project.get("profile"), project.get("trigger_mode"),
           project.get("permission_mode")),
        "gates: passed %s/%s (pending %s, failed %s); next %s"
        % (gates.get("passed"), gates.get("total"), gates.get("pending"),
           gates.get("failed"), gates.get("next_gate") or "—"),
        "tasks: total %s completed %s unblocked %s blocked %s "
        "(P0 pending %s)"
        % (tasks.get("total"), tasks.get("completed"),
           tasks.get("unblocked"), tasks.get("blocked"),
           tasks.get("p0_pending")),
        "risks: open %s (overdue %s, soon %s)"
        % (risks.get("open"), risks.get("escalation_overdue"),
           risks.get("escalation_soon")),
    ]
    items = candidates.get("items") or []
    if items:
        lines.append("candidates: %s"
                     % "; ".join("%s (%s, %s)" % (i["task_id"], i["priority"],
                                                  i["status"])
                                 for i in items))
    elif candidates.get("empty_reason"):
        lines.append("candidates: none — %s (%s)"
                     % (candidates["empty_reason"].get("kind"),
                        candidates["empty_reason"].get("message", "")))
    else:
        lines.append("candidates: n/a")
    for note in payload.get("notes") or []:
        lines.append("note: %s" % note)
    lines.append("health: %s — %s"
                 % ((payload.get("health") or {}).get("state"),
                    "run check-governance (v1 not wired)"))
    next_actions = payload.get("next_actions") or []
    if next_actions:
        lines.append("next:")
        for i, action in enumerate(next_actions, 1):
            lines.append("  %d. %s" % (i, action))
    deferred = payload.get("deferred") or []
    lines.append("duration: %sms | budget: %sms | deferred: %d section(s)"
                 % (payload.get("duration_ms"), payload.get("budget_ms"),
                    len(deferred)))
    for entry in deferred:
        lines.append("  deferred: %s (%s)"
                     % (entry["section"], entry["reason"]))
    return "\n".join(lines)


# ── CLI (the single I/O-bearing entry; engine wires dispatch only) ──────────


def add_arguments(parser):
    """Register the subcommand's arguments (single source for engine+tests)."""
    parser.add_argument(
        "--budget-ms", type=int, default=DEFAULT_BUDGET_MS,
        help="Wall-clock budget in ms (default %d). On exhaustion the "
             "finished sections are returned and `deferred` names the rest "
             "(fail-safe, never a guessed pass)." % DEFAULT_BUDGET_MS)
    parser.add_argument(
        "--format", choices=("json", "text"), default="json",
        help="Machine-readable JSON aggregate (default) or a ≤40-line "
             "text summary.")
    parser.add_argument(
        "--profile", choices=tuple(PROFILE_CAPS), default="standard",
        help="Projection detail level (v1: caps candidate/recency lists "
             "and drops the overview row on lite).")


def build_arg_parser():
    """Standalone parser mirroring the engine's wiring (tests + direct use)."""
    parser = argparse.ArgumentParser(
        prog="governance-bootstrap",
        description="Read-only bootstrap aggregate (FEAT-033): resolve "
                    "envelope + status projection + deferred health face + "
                    "light candidates in one output.")
    parser.add_argument(
        "--project-root", default=None,
        help="Host project root (default: cwd). Fail-closed when missing.")
    add_arguments(parser)
    return parser


def cmd_governance_bootstrap(args):
    """CLI entry wired into verify_workflow.py's dispatch table."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    started = time.monotonic()
    budget_ms = getattr(args, "budget_ms", DEFAULT_BUDGET_MS)
    if not isinstance(budget_ms, int) or budget_ms < 0:
        budget_ms = DEFAULT_BUDGET_MS
    profile = getattr(args, "profile", "standard")

    host_root = resolve_entry.resolve_host_root(
        getattr(args, "project_root", None))
    envelope = resolve_entry.resolve(host_root)

    if not envelope["resolved_root_ok"]:
        # DEC-080 / RISK-038 fail-closed: refuse to present governance state.
        payload = {
            "schema": REPORT_SCHEMA,
            "task": TASK_ID,
            "resolve": envelope,
            "health": _health_face(),
            "next_actions": ["先解决 HOST_PROJECT_ROOT 解析失败（见 diagnostic）"
                             "再重试 governance-bootstrap"],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        sys.exit(1)

    payload = _build_payload(Path(envelope["host_project_root"]), envelope,
                             budget_ms, profile, started)
    payload = _enforce_projection_budget(payload)

    if getattr(args, "format", "json") == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_text(payload))
