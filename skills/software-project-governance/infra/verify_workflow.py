from pathlib import Path
import sys
from resolve_entry import (extract_project_root_arg as _extract_project_root_arg,
                           validate_project_root as _validate_project_root)


def _apply_project_root_override(project_root):
    """Rebind host-governance fact paths to an explicit project root.

    This does not move plugin assets.  ``ROOT`` / ``PLUGIN_ROOT`` continue to
    identify the installed workflow package; only host facts under
    ``<project-root>/.governance`` are rebound.

    Fail-closed (FIX-245): an explicit root that is empty, does not exist,
    or is not a directory is a hard error — classified diagnostic on
    stderr + exit 2 (module CLI convention, same as the argparse/extraction
    errors; mirrors FIX-244 archive alignment). A nonexistent path must
    never silently rebind to a phantom root.
    """
    global HOST_PROJECT_ROOT, GOVERNANCE_DIR, EXECUTION_PACKET_PATH
    global SAMPLE_PATH, SESSION_SNAPSHOT_PATH, EVIDENCE_PATH, RISK_PATH
    global ARCHIVE_INDEX_PATH, ARCHIVE_TASKS_DIR, ARCHIVE_EVIDENCE_DIR
    global ARCHIVE_DECISIONS_DIR, ARCHIVE_RISKS_DIR

    host_root, error = _validate_project_root(project_root)
    if error is not None:
        display = "<empty>" if not project_root else str(project_root)
        print(
            f"verify_workflow: error: invalid-project-root — {display} ({error})",
            file=sys.stderr,
        )
        sys.exit(2)
    HOST_PROJECT_ROOT = host_root
    GOVERNANCE_DIR = HOST_PROJECT_ROOT / ".governance"
    EXECUTION_PACKET_PATH = GOVERNANCE_DIR / "execution-packets.json"

    if "SAMPLE_PATH" in globals():
        SAMPLE_PATH = GOVERNANCE_DIR / "plan-tracker.md"
    if "SESSION_SNAPSHOT_PATH" in globals():
        SESSION_SNAPSHOT_PATH = GOVERNANCE_DIR / "session-snapshot.md"
    if "EVIDENCE_PATH" in globals():
        EVIDENCE_PATH = GOVERNANCE_DIR / "evidence-log.md"
    if "RISK_PATH" in globals():
        RISK_PATH = GOVERNANCE_DIR / "risk-log.md"
    if "ARCHIVE_INDEX_PATH" in globals():
        ARCHIVE_INDEX_PATH = GOVERNANCE_DIR / "archive" / "index.md"
    if "ARCHIVE_TASKS_DIR" in globals():
        ARCHIVE_TASKS_DIR = GOVERNANCE_DIR / "archive" / "tasks"
    if "ARCHIVE_EVIDENCE_DIR" in globals():
        ARCHIVE_EVIDENCE_DIR = GOVERNANCE_DIR / "archive" / "evidence"
    if "ARCHIVE_DECISIONS_DIR" in globals():
        ARCHIVE_DECISIONS_DIR = GOVERNANCE_DIR / "archive" / "decisions"
    if "ARCHIVE_RISKS_DIR" in globals():
        ARCHIVE_RISKS_DIR = GOVERNANCE_DIR / "archive" / "risks"

    global _asset_governance_dir
    _asset_governance_dir = GOVERNANCE_DIR
    if "REQUIRED_FILES" in globals():
        REQUIRED_FILES.update(_asset_host_files(GOVERNANCE_DIR))


def _asset_host_files(governance_dir):
    return {
        "Governance Plan Tracker": governance_dir / "plan-tracker.md",
        "Governance Evidence Log": governance_dir / "evidence-log.md",
        "Governance Decision Log": governance_dir / "decision-log.md",
        "Governance Risk Log": governance_dir / "risk-log.md",
    }


def _dispatch_bootstrap_if_selected(argv):
    """Dispatch the standalone bootstrap handler before loading the workflow engine.
    Unrecognized arguments stay with the full parser, which owns global usage.
    """
    try:
        explicit, remaining = _extract_project_root_arg(argv)
    except ValueError:
        return  # main renders the historical extraction error
    if remaining[:1] != ["governance-bootstrap"]:
        return
    import argparse
    import registry
    from bootstrap_aggregate import add_arguments
    parser = argparse.ArgumentParser(prog="verify_workflow governance-bootstrap")
    add_arguments(parser)
    args, unknown = parser.parse_known_args(remaining[1:])
    if unknown:
        return
    args.command = remaining[0]
    args.project_root = explicit
    if explicit is not None:
        _apply_project_root_override(explicit)
        args._validated_host_root = HOST_PROJECT_ROOT
    sys.exit(registry.load_handler(args.command, parsed_args=True)(args))


# This leaf uses its own small parser and the same registered handler. Other
# invocations fall through to the complete CLI, including its diagnostics.
if __name__ == "__main__" and "governance-bootstrap" in sys.argv[1:]:
    _dispatch_bootstrap_if_selected(sys.argv[1:])

import io
from contextlib import redirect_stdout
from functools import cache as _cache
# When this file is run directly (`python verify_workflow.py ...`), it loads as
# the `__main__` module. The Phase 5 domain modules under checks/ (evidence,
# risk, review — and the older manifest/capability_registry modules) reach back
# into this module via a deferred `import verify_workflow` accessor (`_vw()`).
# Without this alias, that import would load a SECOND, independent copy of the
# file as module `verify_workflow`, so mutations applied to `__main__`'s globals
# (notably `_apply_project_root_override` rebinding EVIDENCE_PATH / SAMPLE_PATH
# / GOVERNANCE_DIR) would not be visible to the domain modules, and test/CLI
# runs that swap the project root would silently read the wrong governance
# tree. Aliasing `verify_workflow` to the already-loaded `__main__` makes the
# deferred accessor resolve to the same module object (Phase 5 / ADR-016).
if __name__ == "__main__" and "verify_workflow" not in sys.modules:
    sys.modules["verify_workflow"] = sys.modules[__name__]
import re
import argparse
import ast
import json
import locale
import os
import signal
import subprocess
import importlib.util
import shutil
import hashlib
import tempfile
import fnmatch
import time
import urllib.request
import webbrowser
from datetime import datetime, date


from checks import commit as commit_checks
from checks import projection as projection_checks
from checks import version as version_checks


from release.context import RepositoryContext
from release.ledger import validate_release_ledger
from release.projection import check_projections, write_projections
# FEAT-019: ArchGuard ratchet gate (fatal) — self-contained module; the
# engine only wires dispatch (bootstrap discipline, evolution doc §4).
from archguard_ratchet import cmd_archguard_ratchet
# FEAT-032 (AUDIT-154 slice A-1): governance cost observability —
# self-contained module; the engine only wires dispatch (same pattern as
# archguard_ratchet). zstandard is imported lazily inside the module so
# the engine's cold-import face stays stdlib-only.
import governance_cost
from governance_cost import cmd_governance_cost_report
# FEAT-033 (AUDIT-154 slice A-2): read-only bootstrap aggregate —
# self-contained module; the engine only wires dispatch (archguard_ratchet /
# governance_cost pattern). Imports resolve_entry + task_priority (both
# engine-free leaves); zero .governance writes / zero git writes / zero
# subprocess dispatch; the health face is v1-deferred (never faked).
import bootstrap_aggregate
from bootstrap_aggregate import cmd_governance_bootstrap
# FEAT-055 (0.86.0 batch 2.0): governed writer family dispatch wiring —
# task_row_update (FEAT-051), governance_store (FEAT-046) and
# baseline_metadata (FEAT-047) join the governance_cost / bootstrap_aggregate
# pattern: each is a self-contained module, stdlib-only at import time, the
# engine only wires dispatch, and every option fact source is the module's
# own add_arguments face consumed by a cmd_* Namespace handler (FEAT-047
# P2-1 caliber — no argv re-parse).
import task_row_update
from task_row_update import cmd_task_row_update
import governance_store
from contracts import DETERMINISTIC_SCAFFOLD_TYPES, QUALITY_BUDGET_DIMENSIONS
from governance_store import (cmd_decision_append, cmd_evidence_append,
                              cmd_locks_amend, cmd_locks_extend,
                              cmd_locks_release)
import baseline_metadata
from baseline_metadata import cmd_baseline_evaluate, cmd_baseline_register
# FIX-462 (0.99.x emergency window): pin_ledger — the machine writer for the
# STATIC_PIN_EXEMPTIONS ledger (DEC-220): stdlib-only, self-contained, the
# engine wires dispatch only (same pattern as the family above); it also
# serves write-guard face 6 (hand-edit alarm over the exemption ledger).
import pin_ledger
from pin_ledger import cmd_pins
# FIX-463 (0.99.x emergency window): premise_tracker — the decision-premise
# invalidator (count/review/status over .governance/premise-events.jsonl;
# DEC-368② class, structural close): stdlib-only, self-contained, the
# engine wires dispatch only (same pattern); also feeds the check-governance
# Decision Premise WARN face and the next-candidates collapsed injection.
import premise_tracker
from premise_tracker import cmd_premise
# FEAT-093 (0.98.0): the authority ledger — task identity contract +
# append-only event log + rebuildable plan-tracker projection (engine wires
# dispatch only; stdlib-only at import time, peer-leaf calibers imported
# function-locally — the governance_cost pattern).
import authority_ledger
from authority_ledger import cmd_authority_ledger
# FEAT-096 (0.98.0): execution isolation conservative surface — the
# four-piece set (write concurrency limit + under-review/being-written
# mutex + read-only review snapshots + lease reclaim with
# loss-of-authority verification). Self-contained stdlib-only module;
# the engine wires dispatch only (governance_cost pattern). Capability
# honesty: host worktree/sandbox isolation is UNVERIFIED (FEAT-095
# report §7 U1) — the delivered surface is CLI-level, disclosed.
import execution_isolation
from execution_isolation import (cmd_isolation_capability,
                                 cmd_isolation_lease_reclaim,
                                 cmd_isolation_snapshot,
                                 cmd_isolation_status,
                                 cmd_isolation_write)
# FEAT-097 (0.98.0): the goal↔budget bridge — state mapping
# (RUNNING→DRAINING→CHECKPOINTED→BLOCKED) + multi-dimension danger-zone
# collection (rounds/tokens/wall-clock/cost, any-dimension danger
# collects) + checkpoint artifacts (ledger/obligations/revision/
# rules_version/budget) + resume authorization (blocked 后禁未授权续跑).
# Self-contained stdlib-only module; the engine wires dispatch only
# (same pattern). Boundaries: no harness-goal replacement, no
# mid-session hot upgrade (DEC-330), no FEAT-095 enforcement face.
import goal_bridge
from goal_bridge import cmd_goal_bridge
# FEAT-095 (0.98.0): action-level enforcement — six boundaries × three
# layers (hard block / review-debt-budget throttle / stale-surface
# notice) as a strategy-TABLE + generic-executor module (table/executor
# separation: adding a boundary edits data, not executor code).
# Capability honesty: the delivered face is PROTOCOL+CLI only (research
# report docs/research/feat-095-harness-enforcement-capability-2026-10-10
# .md §7 U1-U7) — NO host-level interception claim.  The engine wires
# dispatch only (RISK-039 thin-entry discipline, same pattern).
import enforcement
from enforcement import cmd_enforcement_check

ROOT = Path(__file__).resolve().parents[3]
INTERACTION_BOUNDARY_PATH = ROOT / "skills/software-project-governance/references/interaction-boundary.md"
USER_INTERRUPTION_POLICY_TEMPLATE_PATH = ROOT / "skills/software-project-governance/core/templates/user-interruption-policy.md"


# ── Dual-root model (DEC-080 / RISK-038 / FIX-187) ─────────────────────────
# The plugin now installs under a per-version cache dir (e.g.
# .../software-project-governance/0.65.0/) that is NOT the host project.
# Deriving the governance facts root from ``__file__`` (the legacy
# ``ROOT = parents[3]``) therefore points at the plugin cache, where no
# ``.governance/`` exists — that is the 0.54.2/0.54.3 regression and the
# crash in check-governance Check 3.
#
#   PLUGIN_ROOT        — where the plugin's OWN assets live (skills/,
#                        core/, commands/, README.md, manifest.json).
#                        REQUIRED_FILES / GATES_PATH / LIFECYCLE_PATH /
#                        STAGE_SKILLS_ROOT are plugin assets and must
#                        resolve here. ``ROOT`` (parents[3]) is already
#                        this in a versioned install, so ROOT is kept as
#                        the plugin root for backward compatibility.
#
#   HOST_PROJECT_ROOT  — the project being governed; where the real
#                        .governance/ facts live (plan-tracker.md,
#                        evidence-log.md, session-snapshot.md,
#                        execution-packets.json). This MUST come from
#                        resolve_entry (cwd / --project-root), NEVER from
#                        __file__. On failure we fall back to the legacy
#                        parents[3] so dogfood mode (plugin-root ==
#                        host-root) keeps working.
def _resolve_plugin_root():
    """Deferred resolve of PLUGIN_ROOT via resolve_entry.PLUGIN_HOME.

    Falls back to the legacy ``parents[3]`` plugin root (== ROOT) when
    resolve_entry cannot be imported (e.g. minimal packaging), so the
    plugin always knows where its own assets are.
    """
    try:
        from resolve_entry import PLUGIN_HOME  # peer import (no cycle)
        return Path(PLUGIN_HOME).parent.parent  # parents[2] of infra/
    except Exception:
        return ROOT


def _resolve_host_root():
    """Deferred resolve of HOST_PROJECT_ROOT via resolve_entry.

    Priority mirrors resolve_entry.resolve_host_root: explicit cwd ->
    os.getcwd(). On any failure (resolve_entry missing, cwd unusable)
    we fall back to the legacy ``parents[3]`` so dogfood mode keeps
    working — this is the backward-compat path, not a security decision
    here (resolve_entry itself is fail-closed for the /governance entry).
    """
    try:
        from resolve_entry import resolve_host_root  # peer import (no cycle)
        host = resolve_host_root(None)
        if host is not None:
            return Path(host)
    except Exception:
        pass
    return ROOT


PLUGIN_ROOT = _resolve_plugin_root()
HOST_PROJECT_ROOT = _resolve_host_root()
from resolve_entry import bind_host_root as _bind_host_root
_bind_host_root(lambda: HOST_PROJECT_ROOT,
                snapshot_paths=lambda: (HOST_PROJECT_ROOT, SESSION_SNAPSHOT_PATH, SAMPLE_PATH, EVIDENCE_PATH),
                triage_roots=lambda: (ROOT, GOVERNANCE_DIR))

# Governance FACTS live in the host project, never in the plugin cache.
GOVERNANCE_DIR = HOST_PROJECT_ROOT / ".governance"
_asset_governance_dir = GOVERNANCE_DIR
EXECUTION_PACKET_PATH = GOVERNANCE_DIR / "execution-packets.json"


def _display_path(path, root=None):
    from project_paths import display_path
    return display_path(path, root or ROOT)


def _read_text_normalized(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


# ── PLUGIN_SCOPE_DIRS (keep in sync with cleanup.py) ─────────────
# Directories that constitute the plugin installation boundary.
# Check 10 (M5 compliance) skips these to avoid false positives from
# legitimate checklists in plugin SKILL.md files (FIX-054).
from checks.manifest import PLUGIN_SCOPE_DIRS


def _is_plugin_path(rel_path: str) -> bool:
    """Check if a relative path is inside a plugin scope directory.

    Plugin scope dirs (PLUGIN_SCOPE_DIRS) are matched as path components
    anywhere in the path, not just as a prefix.  This catches nested
    installations (e.g. project/e2e-test-project/skills/) and avoids
    false positives from legitimate checklists in plugin SKILL.md files.

    Semantics synced with cleanup.py _is_path_excluded() for directory
    patterns (FIX-054).
    """
    rel_path = rel_path.replace("\\", "/")
    segments = rel_path.split("/")
    for scope_dir in PLUGIN_SCOPE_DIRS:
        # Root-prefix match
        if rel_path == scope_dir or rel_path.startswith(scope_dir + "/"):
            return True
        # Nested as a path component (e.g. project/e2e-test-project/skills/...)
        if scope_dir in segments:
            return True
    return False


def _git_files(args):
    from project_paths import git_files
    return git_files(args, ROOT)


def _split_markdown_table_row(line):
    from governance_readers import markdown_table_cells
    return markdown_table_cells(line)


def lock_issue_is_blocking(issue):
    from plugin_assets import lock_issue_is_blocking as run
    return run(issue, blocking_lock_issue_types=_product_policy("BLOCKING_LOCK_ISSUE_TYPES"))


def structural_issue_is_blocking(issue):
    from plugin_assets import structural_issue_is_blocking as run
    return run(issue)


def blocking_structural_issues(issues):
    from plugin_assets import blocking_structural_issues as run
    return run(issues, structural_issue_is_blocking=structural_issue_is_blocking)


# ── Manifest domain (extracted to infra/checks/manifest.py in 0.59.0) ──
# DEC-083 Phase 1 / REQ-102: the manifest check domain (manifest.json
# canonical-set consistency, FIX-110 product-artifact guards, and
# cleanup-scope sync) now lives in checks.manifest. This module keeps a
# thin re-export so existing call sites (dispatch, Check 11 in cmd_verify,
# and the three registry domains that share _manifest_artifact_entries)
# keep working unchanged. When verify_workflow.py is run directly, the
# `infra/` directory is on sys.path[0], so `checks` resolves as a sibling
# subpackage.
from checks.manifest import (  # noqa: E402
    bind_manifest_access as _bind_manifest_access,
    _path_to_label,
    _manifest_product_file_entries,
    _manifest_artifact_entries,
    _manifest_requires_product_artifact_guards,
    scan_actual_files,
    scan_manifest_visible_files,
    build_required_files_from_manifest,
    expand_manifest_to_canonical_set,
    check_manifest_canonical_product_artifacts,
    check_manifest_cleanup_scope,
    check_repository_navigation,
    check_manifest_consistency,
    cmd_check_manifest_consistency,
)


if __name__ in ("verify_workflow", "__main__"):
    _bind_manifest_access(package_root=lambda: ROOT,
                          display_path=lambda path, root=None: _display_path(path, root),
                          git_files=lambda args: _git_files(args),
                          scope_dirs=lambda: PLUGIN_SCOPE_DIRS)


def _exception_note(check_id, artifact, severity=None, bytes_value=None):
    """FEAT-075 (DEC-278 单元二 item 4): annotation suffix for a finding —
    ``exception accepted (id, ref, expires)`` when an EFFECTIVE governance
    exception matches, empty otherwise (no registry → byte-identical
    pre-FEAT-075 output). Deferred import on purpose: the engine's frozen
    startup-import face (R6) must not grow. Annotation-only — never changes
    a severity, byte count, or summary (原始 FAIL 与真实字节数保留)."""
    from exception_registry import exception_note
    return exception_note(check_id, artifact, severity,
                          root=HOST_PROJECT_ROOT, bytes_value=bytes_value)


def _release_exception_block():
    """FEAT-075: the release-aggregate exception disclosure (None when no
    .governance/exceptions.json exists — inert wiring; the Coordinator
    registers the real exceptions after M-0). Deferred import (R6 face)."""
    from exception_registry import release_disclosure_block
    return release_disclosure_block(root=HOST_PROJECT_ROOT)


def _exception_registry_error_note():
    """FEAT-075 R0 F-2: one-line file-level registry-error disclosure (""
    when clean/absent). Both aggregation render paths attach it ONCE (first
    finding line) — a scope-matching but malformed exception never
    annotates silently. Deferred import (R6 face)."""
    from exception_registry import registry_error_note
    return registry_error_note(root=HOST_PROJECT_ROOT)

# ── Capability-registry domain (extracted to infra/checks/capability_registry.py in 0.61.1) ──
# DEC-083 Phase 2 / REQ-103: the capability-registry check domain (capability-
# registry.json schema validation, FIX-116) now lives in checks.capability_registry.
# Same registry-schema-check pattern as the manifest domain (Phase 1). Thin
# re-export keeps existing call sites (dispatch, Check 28k in cmd_check_governance)
# working unchanged.
from checks.capability_registry import (  # noqa: E402
    check_capability_registry,
    cmd_check_capability_registry,
    _capability_registry_text_values,
    _line_has_scoped_claim_negation,
    CAPABILITY_REGISTRY_ALLOWED_KINDS,
    CAPABILITY_REGISTRY_ALLOWED_STATUSES,
    CAPABILITY_REGISTRY_REQUIRED_FIELDS,
    CAPABILITY_REGISTRY_REQUIRED_KINDS,
    CAPABILITY_REGISTRY_BOUNDARY_TOKENS,
    CAPABILITY_REGISTRY_FORBIDDEN_OVERCLAIMS,
    CAPABILITY_REGISTRY_PATH,
)

# Evidence operations receive the CLI's configurable inputs at the composition point below.
from checks import evidence_domain as _evidence_domain
from checks.evidence_domain import (  # noqa: E402
    _evidence_header_index,
    _extract_evidence_task_id,
    _evidence_state_cells,
    _is_closed_evidence_state,
    _is_active_evidence_state,
    _parse_evidence_context_tasks,
    parse_evidence_task_ids,
    parse_evidence_task_map,
    check_evidence_completeness,
    check_evidence_quality,
    emit_evidence_completeness, emit_evidence_quality,
    check_fact_grounding,
    check_structured_evidence, requires_impact_evidence,
    _FORENSIC_HEAD_RE, _is_product_code_location, _is_review_evidence, _is_audit_or_review_type,
    SECRET_FIELD_RE, SECRET_ASSIGNMENT_RE, _contains_secret_like,
    _extract_structured_fact_json, _validate_structured_fact_payload,
    render_rb2_goal_contract_block,
)

# ── Risk domain (extracted to infra/checks/risk_domain.py in 0.70.0) ────────
# DEC-083 Phase 5b / ADR-016 / FEAT-009: the risk check domain (Checks 2 + 8
# plus risk-only parsing helpers) now lives in checks.risk_domain. Thin
# re-export keeps existing call sites (Check 2/8 blocks in
# cmd_check_governance and discover_governance_context) working unchanged.
from checks import risk_domain
from checks.risk_domain import (
    is_risk_status_open, emit_risk_staleness, emit_risk_escalation, emit_risk_mitigation_closure,
    _ARCHIVE_FAMILY_RANGE_RE, _ARCHIVE_RANGE_SPAN_CAP, _ARCHIVE_RESOLVED_STATUS, _resolve_shared,
)


def _parse_context_open_risks(root):
    return risk_domain._parse_context_open_risks(root, context_file=_context_file, context_task=_context_task)


def parse_open_risks():
    return risk_domain.parse_open_risks(risk_path=RISK_PATH)


def parse_active_risks(risk_content=None):
    return risk_domain.parse_active_risks(risk_content, risk_path=RISK_PATH)


def check_risk_staleness():
    return risk_domain.check_risk_staleness(risk_path=RISK_PATH)


def check_risk_escalation():
    return risk_domain.check_risk_escalation(risk_path=RISK_PATH)


def _default_task_status_map():
    return risk_domain._default_task_status_map(SAMPLE_PATH)


def check_risk_mitigation_closure(risk_content=None, task_status_map=None):
    return risk_domain.check_risk_mitigation_closure(risk_content, task_status_map, risk_path=RISK_PATH,
                                                    plan_path=SAMPLE_PATH, task_id_pattern=_TASK_ID_IN_REF_RE)


# ── Snapshot domain (new in 0.76.0) ──────────────────────────────────────
# FIX-268 / REQ-145.2 (design §3.2): the snapshot-freshness watchdog
# (Check 35). New domain module checks/snapshot_domain.py mirrors the
# risk_domain pattern: deferred _vw() shared accessor, no import cycle.
def check_snapshot_freshness(plan_content=None, snapshot_text=None, evidence_mtime=None, commit_date=None):
    from checks.snapshot_domain import check_snapshot_freshness as check
    return check(plan_content, snapshot_text, evidence_mtime, commit_date, host_root=HOST_PROJECT_ROOT,
                 snapshot_path=SESSION_SNAPSHOT_PATH, plan_path=SAMPLE_PATH, evidence_path=EVIDENCE_PATH,
                 session_date_pattern=FIX_105_SNAPSHOT_DATE_RE)

# ── Gate domain (new in 0.76.0) ────────────────────────────────────
# FIX-266 / REQ-145.4 (design §3.4): the gate↔release interlock watchdog
# (Check 37). New domain module checks/gate_domain.py mirrors the
# snapshot_domain pattern: deferred _vw() shared accessor, no import cycle.
# The module also carries released_history_version() — the BR-4 auto-
# released helper for cmd_check_release's already-published-version checks.
from checks.gate_domain import release_unit_issues


# ── CI domain (new in 0.76.0) ──────────────────────────────────────
# FIX-267 / REQ-145.5 (design §3.5): the CI-evidence watchdog
# (Check 38). New domain module checks/ci_domain.py mirrors the
# gate_domain pattern: deferred _vw() shared accessor, no import cycle.
# Scope per DEC-154 ②: carrier existence + git remote only (no deep
# workflow/job/run inspection in 0.76.0); facts root = HOST_PROJECT_ROOT
# (FIX-270 mixed-root semantics — never the plugin ROOT).
from checks.ci_domain import (  # noqa: E402
    bind_ci_facts as _bind_ci_facts,
    check_ci_evidence,  # FIX-267 / REQ-145.5 (Check 38)
)

if __name__ in ("verify_workflow", "__main__"):
    _bind_ci_facts(lambda: (HOST_PROJECT_ROOT, SAMPLE_PATH))


# ── Review domain (extracted to infra/checks/review_domain.py in 0.70.0) ────
# DEC-083 Phase 5c / ADR-016 / FEAT-009: the agent-team-review protocol
# domain (Checks 18, 18b, 21, 21b, 22, 29, 30 plus their review-only helpers
# and constants — including the review-domain PRODUCT_CODE_PATTERNS,
# DEGRADED_FUSE_THRESHOLD, and FIX173_NAMING_NORMALIZATION_DATE) now lives in
# checks.review_domain. Thin re-export keeps existing call sites (Check
# 18/18b/21/21b/22/29/30 blocks in cmd_check_governance, the
# `check-review-debt` argparse subcommand, and the FIX-18*/FIX-21*/FIX-29*/
# FIX-30* test suites) working unchanged. Cross-domain helpers
# (_is_review_evidence, _is_audit_or_review_type, _generic_reviewer_cells,
# _evidence_task_type_index) stay here and are reached via `_vw()`.
from checks.review_domain import (  # noqa: E402
    DEGRADED_REVIEW_MARKERS,
    REVIEWER_ROLE_MARKERS,
    SELF_REVIEW_AUTHOR_MARKERS,
    ROUTING_FILE_CANDIDATES,
    DEGRADED_MARKERS,
    DEGRADED_FUSE_THRESHOLD,
    PRODUCT_CODE_PATTERNS,
    REVIEW_FALLBACK_POLICY_REQUIRED_FILES,
    REVIEW_FALLBACK_POLICY_OPTIONAL_FILES,
    _REVIEW_FALLBACK_FORBIDDEN_PATTERNS,
    _REVIEW_FALLBACK_REQUIRED_SNIPPETS,
    M5_QUESTION_WORDS,
    M5_OPTION_MENU_RE,
    M5_CHOICE_CONTEXT_WORDS,
    _M5_T2_PROXIMITY_LINES,
    M5_NOTIFICATION_PREFIXES,
    REVIEW_MAX_ROUNDS,
    _REVIEW_APPROVAL_CONCLUSIONS,
    _REVIEW_TERMINAL_CONCLUSIONS,
    _REVIEW_NON_TERMINAL_ALIASES,
    _UNRESOLVED_BLOCKERS_KEY_RE,
    _REVIEW_ID_RE,
    _LEGACY_REVIEW_FILE_RE,
    FIX173_NAMING_NORMALIZATION_DATE,
    _review_text_is_degraded,
    _review_text_has_reviewer_marker,
    _review_entry_skip_reason,
    _parse_review_coverage_details,
    _parse_review_covered_tasks,
    check_agent_team_review,
    _parse_routing_post_review_table,
    _routing_post_review_for_task_type,
    _is_post_review_exempt,
    _count_degraded_reviews_for_task,
    check_review_debt,
    check_review_spawn_gap,
    check_review_coverage,
    check_governance_review_fallback_policy,
    _strip_code_fences_and_tables,
    _segment_final_prose,
    _t2_has_proximate_choice_context,
    check_m5_runtime_triggers,
    _normalize_review_conclusion,
    _extract_review_conclusion_from_text,
    _parse_unresolved_blockers_fields,
    _merge_unresolved_blocker_evidence,
    _entry_unresolved_blocker_evidence,
    _normalize_review_round,
    _review_chain_attribution,
    _build_review_sequence,
    check_review_closure,
    _task_routing_exempt,
    _collect_live_review_sequences,
    REQ107_MACHINE_PROVENANCE_DATE,
    REVIEW_MACHINE_ROW_MARKER,
    REVIEW_MACHINE_FILE_MARKER,
    check_review_machine_provenance,
    check_loop_wiring_call_sites,
    check_m5_compliance,
    cmd_check_review_debt,
)


# ── Change-control triage domain (checks/triage_domain.py in 0.73.0) ────────
# FIX-237.4 / ADR-017 §4.4: Check 32 — mandatory change-control triage for
# product-code task intake (CLI wiring + record validity + no-record FAIL).
def check_change_triage(root=None, governance_dir=None, verify_path=None):
    from checks.triage_domain import check_change_triage as check
    return check(ROOT if root is None else root, GOVERNANCE_DIR if governance_dir is None else governance_dir,
                 verify_path)


def check_r1_completion_gate(root=None, governance_dir=None):
    from checks.triage_domain import check_r1_completion_gate as check
    return check(ROOT if root is None else root, GOVERNANCE_DIR if governance_dir is None else governance_dir)


# ── Existing verification functions ──────────────────────────────

def check_files():
    from plugin_assets import check_files as inspect_files
    return inspect_files(package_root_now=lambda: ROOT, build_required_files_from_manifest=build_required_files_from_manifest,
                         fallback_files=lambda: (_product_policy("REQUIRED_FILES"),
                                                 _product_policy("OPTIONAL_PROJECTION_FILES")))


def check_snippets():
    from plugin_assets import check_snippets as run
    return run(package_root=ROOT, required_snippets=_product_policy("REQUIRED_SNIPPETS"), display_path=_display_path)


_HOST_POLICY_OWNERS = {
    **dict.fromkeys(('_MARKDOWN_BOLD_SPAN_RE', '_TOO_BROAD_SCOPE_PHRASE_RE'), 'execution_packet_checks'),
    **dict.fromkeys(('_COMPLETED_STATUS_PREFIX', '_HOT_STATUS_STATE_COMMITTED', '_HOT_STATUS_STATE_LEGACY',
                     '_NONACTIVE_SUBSECTION_MARKERS'), 'plan_task_selection'),
    **dict.fromkeys((
        'GOVERNANCE_CONTEXT_EVIDENCE_UNFINISHED_MARKERS',
        'GOVERNANCE_CONTEXT_EVIDENCE_CLOSED_MARKERS',
        'GOVERNANCE_CONTEXT_EVIDENCE_TASK_HEADERS',
        'GOVERNANCE_CONTEXT_EVIDENCE_STATE_HEADERS',
    ), 'checks.evidence_domain'),
    **dict.fromkeys((
        '_GOVERNANCE_STORE_MARKER_PREFIX',
        '_EVIDENCE_MACHINE_CREDENTIAL_RE',
    ), 'write_guard_records'),
    **dict.fromkeys((
        'PRODUCT_SUCCESS_CONTRACT_REQUIRED_FIELDS',
        'PRODUCT_SUCCESS_PLACEHOLDER_RE',
        'PRODUCT_SUCCESS_PROCESS_ONLY_RE',
        'PRODUCT_SUCCESS_USER_OUTCOME_RE',
        'PRODUCT_SUCCESS_RUNNABLE_RE',
    ), 'delivery_contract_checks'),
    **dict.fromkeys((
        '_W7_TERMINAL_MARKERS',
        '_W7_ACTIVE_MARKERS',
        '_W7_TERMINAL_DATE_RE',
        '_WRITER_OP_ANCHOR_RE',
    ), 'plan_status'),
    **dict.fromkeys((
        'EXTERNAL_PROJECT_NATIVE_ENTRY_FILES', 'EXTERNAL_PROJECT_NATIVE_ENTRY_PATTERNS',
        'EXTERNAL_PROJECT_REQUIRED_INSTALLED_HOOKS', 'EXTERNAL_PROJECT_VALIDATION_BOUNDARY',
        'EXTERNAL_PROJECT_VALIDATION_COMMANDS',
    ), 'external_project_policy'),
    **dict.fromkeys((
        'ADAPTER_REQUIRED_KEYS', 'ADAPTER_RUNTIME_CAPABILITY_POLICY', 'MAINSTREAM_AGENT_ADAPTERS',
        'RUNTIME_CAPABILITY_KEYS', 'RUNTIME_CAPABILITY_STATUSES',
    ), 'adapter_contracts'),
    **dict.fromkeys((
        'FIRST_SESSION_MEASUREMENT_ALLOWED_STATUSES', 'FIRST_SESSION_MEASUREMENT_PATH',
        'RUNTIME_MATRIX_AGENT_IDS', 'RUNTIME_MATRIX_RESEARCH_ONLY_IDS', 'RUNTIME_READINESS_MATRIX_PATH',
    ), 'adapter_readiness'),
    **dict.fromkeys((
        'CHANNEL_ANCHOR_DATE_STRICT_RE', 'CHANNEL_DATE_ANCHOR_ADAPTERS', 'CHANNEL_EVIDENCE_DATE_RE',
        'CHANNEL_EVIDENCE_STALE_DAYS', 'CONSULT_DRAW_MARKER', 'EXPLORATION_CHANNEL_KEYS',
        'EXPLORATION_CHANNEL_STATUSES', 'EXPLORATION_SAMPLE_REPORTS', 'QUOTE_SYNC_ADAPTER_MANIFESTS',
    ), 'exploration_evidence'),
    **dict.fromkeys((
        'GOVERNANCE_PACKS_PATH', 'GOVERNANCE_PACK_BOUNDARY_TOKENS', 'GOVERNANCE_PACK_FORBIDDEN_OVERCLAIMS',
        'GOVERNANCE_PACK_IDS', 'GOVERNANCE_PACK_KNOWN_CHECKS', 'GOVERNANCE_PACK_PROFILE_IDS',
        'GOVERNANCE_PACK_RELEASE_BOUNDARY_PATH', 'GOVERNANCE_PACK_RELEASE_BOUNDARY_TOKENS',
        'GOVERNANCE_PACK_REQUIRED_FIELDS', 'GOVERNANCE_PACK_STATUS_BOUNDARY_TOKENS',
        'GOVERNANCE_PACK_STATUS_DOC_PATHS', 'GOVERNANCE_PACK_STATUS_FORBIDDEN_OVERCLAIMS',
        'README_PACK_GUIDANCE_REQUIRED_TOKENS',
    ), 'host_governance_packs'),
    **dict.fromkeys((
        'DSH_SMOKE_ATTRIBUTED_CONCURRENT_WRITES_RE', 'DSH_SMOKE_REAL_HOME_WRITES_RE',
        'DSH_SMOKE_RESULT_PASS_RE', 'DSH_UPGRADE_REGRESSION_LABEL',
    ), 'host_loader_probes'),
    **dict.fromkeys((
        'ADAPTER_CLAIM_REGISTRY', 'EVIDENCE_LEVEL_MARKER_RE', 'MAINSTREAM_AGENT_LOADING_ADAPTERS',
        'MAINSTREAM_AGENT_LOADING_BOUNDARY_TOKENS', 'MAINSTREAM_AGENT_LOADING_DOC_PATH',
        'MAINSTREAM_AGENT_LOADING_FORBIDDEN_CLAIM_TERMS', 'MAINSTREAM_AGENT_LOADING_FORBIDDEN_OVERCLAIMS',
        'MAINSTREAM_AGENT_LOADING_README_TOKENS', 'MAINSTREAM_AGENT_LOADING_REQUIRED_DOCS',
        'MAINSTREAM_AGENT_LOADING_REQUIREMENTS_TOKENS', 'MAINSTREAM_AGENT_LOADING_TIER1',
        'MAINSTREAM_AGENT_LOADING_TIER2',
    ), 'host_loading_claims'),
    **dict.fromkeys((
        '_KNOWN_VERIFY_FAILURE_SIGNATURES',
    ), 'product_fixture_validation'),
    **dict.fromkeys((
        'GEMINI_API_KEY_ENV_VARS', 'GEMINI_AUTH_REMEDIATION', 'GEMINI_GCA_CONFIG_ENV_VARS',
        'GEMINI_GCA_CREDENTIAL_ENV_VARS', 'GEMINI_VERTEX_CONFIG_ENV_VARS',
        'GEMINI_VERTEX_CREDENTIAL_ENV_VARS', 'OPENCODE_LEGAL_DEEPSEEK_MODELS',
        'OPENCODE_PROVIDER_MODEL_REMEDIATION',
    ), 'runtime_preflight'),
    **dict.fromkeys((
        'ACTIVE_AGENT_ROLES', 'LOOP_ROLE_SKILL_CONTRACTS', 'NAMED_REVIEWER_ROLES',
    ), 'team_activation'),
}


_PRODUCT_POLICY_OWNERS = {
    "probe_quality_tools": "release.quality",
    "ARCHGUARD_DEFAULT_ROOT_RESIDUE": "architecture_diagnostics",
    "ARCHGUARD_HOOKS_REL": "architecture_diagnostics",
    "ARCHGUARD_LEDGER_REL": "architecture_diagnostics",
    "ARCHGUARD_SCHEMA_REL": "architecture_diagnostics",
    "BLOCKING_LOCK_ISSUE_TYPES": "plugin_assets",
    "GIT_LINEAGE_TIMEOUT_SECONDS": "release_provenance",
    "GIT_REMOTE_NAME_RE": "release_provenance",
    "INJECTION_CONTRACT_ANCHORS": "repository_projection",
    "INJECTION_CONTRACT_STAGED_ANCHORS": "repository_projection",
    "OPTIONAL_PROJECTION_FILES": "plugin_assets",
    "PLATFORM_ENTRY_FILES": "plugin_assets",
    "PROJECTION_SNIPPETS": "plugin_assets",
    "PROJECTION_SYNC_PATTERNS": "repository_projection",
    "REQUIRED_FILES": "plugin_assets",
    "REQUIRED_SNIPPETS": "plugin_assets",
    "VERSION_LINE_ANCHOR": "repository_projection",
    "WORKFLOW_SNIPPETS": "plugin_assets",
    "_RELEASE_GATE_TIMEOUT_DEFAULT": "release_execution",
    "_RELEASE_GATE_TIMEOUT_ENV": "release_execution",
}


_DELETED_POLICIES = set()


def __getattr__(name):
    """Load the historical public policy or archive class on first access."""
    if name == "GovernanceDataSource":
        return _archive_reader_class()
    owner = _HOST_POLICY_OWNERS.get(name) or _PRODUCT_POLICY_OWNERS.get(name)
    if owner is None or name in _DELETED_POLICIES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(owner), name)
    if name == "REQUIRED_FILES":
        value = dict(value)
        value.update(_asset_host_files(_asset_governance_dir))
    globals()[name] = value
    return value


def __dir__():
    policies = (_HOST_POLICY_OWNERS.keys() | _PRODUCT_POLICY_OWNERS.keys()) - _DELETED_POLICIES
    return sorted(globals().keys() | policies | {"GovernanceDataSource"})


class _WorkflowModule(type(sys)):
    def __delattr__(self, name):
        # These were real module attributes before the owners became lazy. Deleting
        # one before the first read must work without importing that owner.
        if name in _HOST_POLICY_OWNERS or name in _PRODUCT_POLICY_OWNERS:
            if name in self.__dict__ or name in _DELETED_POLICIES:
                super().__delattr__(name)
            _DELETED_POLICIES.add(name)
        else:
            super().__delattr__(name)


def _host_policy(name):
    """Read the current legacy binding, including changes made by programmatic callers."""
    try:
        return globals()[name]
    except KeyError:
        if name in _DELETED_POLICIES:
            raise NameError(f"name '{name}' is not defined") from None
        return __getattr__(name)


_product_policy = _host_policy


def check_loop_role_skill_consistency(root=None):
    from team_activation import check_loop_role_skill_consistency as run
    return run(
        root, package_root=ROOT, lifecycle_registry_gates=LIFECYCLE_REGISTRY_GATES,
        loop_role_skill_contracts=_host_policy('LOOP_ROLE_SKILL_CONTRACTS'), display_path=_display_path,
        markdown_section_by_prefix=_markdown_section_by_prefix, read_text_normalized=_read_text_normalized,
    )


from hot_governance_facts import (
    _markdown_has_heading, _markdown_section, _markdown_section_by_prefix, _markdown_table_cells,
    _normalize_agent_token, _generic_reviewer_cells, _normalize_markdown_cell,
    _find_table_row_by_first_cell, _find_table_rows_with_cell, _status_cell_is_delivered,
)


def _hot_status_cell_is_delivered(status):
    from hot_governance_facts import _hot_status_cell_is_delivered as run
    return run(status, status_clean_cell=_status_clean_cell,
               status_is_writer_committed_cell=_status_is_writer_committed_cell)


from hot_governance_facts import (
    _contains_fix_token_or_range, FIX_087_READINESS_VERSION,
)
from hot_governance_facts import (
    FIX_087_REQ_TASKS, FIX_105_SNAPSHOT_RELEASE_VERSION_RE,
)
from hot_governance_facts import FIX_105_PLAN_WORKFLOW_VERSION_RE
from hot_governance_facts import FIX_105_SNAPSHOT_VERSION_RE
from hot_governance_facts import FIX_105_SNAPSHOT_DATE_RE
from hot_governance_facts import (
    FIX_105_READINESS_RELEASE_BLOCKERS, _version_row_text, _task_statuses_for_hot_source,
)


def _hot_task_is_delivered(plan_content, task_id, version=None):
    from hot_governance_facts import _hot_task_is_delivered as run
    return run(plan_content, task_id, version,
               is_delivered=lambda cell: _hot_status_cell_is_delivered(cell))


def _hot_task_is_open(plan_content, task_id, version=None):
    from hot_governance_facts import _hot_task_is_open as run
    return run(plan_content, task_id, version,
               is_delivered=lambda cell: _hot_status_cell_is_delivered(cell))


def _hot_task_ids_for_version(plan_content, version):
    from hot_governance_facts import _hot_task_ids_for_version as run
    return run(plan_content, version,
               is_delivered=lambda cell: _hot_status_cell_is_delivered(cell))


from hot_governance_facts import (
    _line_mentions_completed_range_as_pending, _extract_task_ids, _parse_iso_date,
)


def _latest_published_release_fact(plan_content):
    from hot_governance_facts import _latest_published_release_fact as run
    return run(plan_content, policy=_hot_fact_policy())


def _hot_fact_policy():
    from hot_governance_facts import HotFactPolicy
    return HotFactPolicy(FIX_087_READINESS_VERSION, FIX_087_REQ_TASKS, FIX_105_SNAPSHOT_RELEASE_VERSION_RE,
                         FIX_105_PLAN_WORKFLOW_VERSION_RE, FIX_105_SNAPSHOT_VERSION_RE,
                         FIX_105_SNAPSHOT_DATE_RE, FIX_105_READINESS_RELEASE_BLOCKERS)


def _snapshot_fact_source_issues(plan_content, plan_tracker_path):
    from hot_governance_facts import _snapshot_fact_source_issues as run
    return run(plan_content, plan_tracker_path, policy=_hot_fact_policy(), display_path=_display_path)


def _hot_fact_source_plugin_scope():
    from hot_governance_facts import _hot_fact_source_plugin_scope as run
    return run(host_plugin_roots_divergent=_host_plugin_roots_divergent)


def check_hot_fact_source_consistency(plan_tracker_path=None):
    from hot_governance_facts import check_hot_fact_source_consistency as run
    return run(plan_tracker_path, policy=_hot_fact_policy(), display_path=_display_path,
               governance_dir=_governance_dir, host_plugin_roots_divergent=_host_plugin_roots_divergent,
               is_delivered=lambda cell: _hot_status_cell_is_delivered(cell))


def _load_adapter_manifest(adapter_dir):
    from adapter_readiness import _load_adapter_manifest as run
    return run(adapter_dir, display_path=_display_path)


def _run_version_command(command):
    from runtime_preflight import _run_version_command as run
    return run(command, package_root=ROOT)


LIFECYCLE_REGISTRY_PATH = ROOT / "skills/software-project-governance/core/lifecycle-registry.json"
LIFECYCLE_REGISTRY_ACTIVE_MODE = "classic-phase-gate"
LIFECYCLE_REGISTRY_DYNAMIC_MODE = "dynamic-flow-gate"
FLOW_UNIT_RUNTIME_STATE_REL = Path(".governance/flow-unit-runtime.json")
LIFECYCLE_REGISTRY_GATES = [f"G{i}" for i in range(1, 12)]
LIFECYCLE_REGISTRY_STAGE_IDS = [
    "initiation",
    "research",
    "selection",
    "infrastructure",
    "architecture",
    "development",
    "testing",
    "ci-cd",
    "release",
    "operations",
    "maintenance",
]
LIFECYCLE_REGISTRY_REQUIRED_PROJECT_TYPES = {
    "game",
    "web-app",
    "mobile-app",
    "library",
    "cli-tool",
    "ai-agent-plugin",
    "internal-script",
}
LIFECYCLE_REGISTRY_REQUIRED_PRESET_FIELDS = {
    "profile_intensity_boundary",
    "default_packs",
    "quality_budget",
    "acceptance_templates",
    "release_checks",
    "gate_policy",
    "gate_standards",
}
LIFECYCLE_REGISTRY_GATE_POLICY_REQUIRED_FIELDS = {
    "can_skip_stages",
    "can_merge_stages",
    "stage_skip_requires",
    "blocked_dependency_rule",
    "sibling_completion_rule",
}
LIFECYCLE_REGISTRY_REQUIRED_GAME_STANDARDS = {
    "chapter",
    "level",
    "asset",
    "narrative",
    "playability",
}
LIFECYCLE_REGISTRY_REQUIRED_LIBRARY_STANDARDS = {
    "api",
    "semver",
    "docs",
    "downstream-tests",
}
LIFECYCLE_REGISTRY_RISK_CLAIMS = [
    ("risk-036 closed", re.compile(r"\brisk-036\b[^\n.;|]{0,48}\bclosed\b")),
    ("risk-036 closed", re.compile(r"\bclosed\b[^\n.;|]{0,48}\brisk-036\b")),
    ("risk-036 closure achieved", re.compile(r"\brisk-036\b[^\n.;|]{0,48}\bclosure\s+achieved\b")),
    ("risk-037 closed", re.compile(r"\brisk-037\b[^\n.;|]{0,48}\bclosed\b")),
    ("risk-037 closed", re.compile(r"\bclosed\b[^\n.;|]{0,48}\brisk-037\b")),
    ("risk-037 closure achieved", re.compile(r"\brisk-037\b[^\n.;|]{0,48}\bclosure\s+achieved\b")),
    ("1.0.0 production-ready", re.compile(r"\b1\.0\.0\s+production-ready\b")),
]
LIFECYCLE_REGISTRY_FORBIDDEN_OVERCLAIMS = [
    (
        "declarative gate engine active",
        re.compile(r"\bdeclarative\s+gate\s+engine\s+(?:is\s+)?active\b"),
    ),
    (
        "declarative gate engine active",
        re.compile(r"\bdeclarative\s+gate\s+engine\s+activated\b"),
    ),
    (
        "declarative gate engine active",
        re.compile(r"\b(?:activate|activates|activated|activating)\s+(?:the\s+)?declarative\s+gate\s+engine\b"),
    ),
    (
        "dynamic-flow-gate default",
        re.compile(r"\bdynamic-flow-gate\s+(?:is\s+)?(?:now\s+)?(?:the\s+)?default(?:\s+lifecycle\s+mode)?\b"),
    ),
    (
        "dynamic-flow-gate default",
        re.compile(r"\b(?:make|makes|made|making)\s+dynamic-flow-gate\s+(?:the\s+)?default(?:\s+lifecycle\s+mode)?\b"),
    ),
    (
        "dynamic-flow-gate default",
        re.compile(r"\bdefault\s+lifecycle\s+mode\s+(?:is\s+|now\s+)?dynamic-flow-gate\b"),
    ),
]
GATE_EXECUTION_REGISTRY_REQUIRED_FIELDS = {
    "status", "execution_scope", "automation_commands_are_metadata_only", "gate_checks",
}
GATE_EXECUTION_REQUIRED_FIELDS = {
    "gate_id",
    "required_artifacts",
    "checks",
    "evidence_query",
    "automation_command",
    "human_confirmation_policy",
    "severity",
    "project_type_overrides",
}
GATE_EXECUTION_CHECK_REQUIRED_FIELDS = {
    "check_id",
    "label",
    "executor",
    "severity",
}
GATE_EXECUTION_ALLOWED_SEVERITIES = {"critical", "high", "medium", "low"}
GATE_EXECUTION_ALLOWED_EXECUTORS = {
    "function",
    "file_exists",
    "snippet_in_file",
    "completed_ratio",
    "research_doc_count",
    "constant_result",
    "evidence_mentions",
}
GATE_EXECUTION_ALLOWED_FUNCTIONS = {
    "check_quantifiable_metrics",
    "check_scope_boundary",
    "check_stakeholders",
    "check_out_of_scope",
    "check_all_required_files_exist",
    "check_g10_real_operation_data",
    "check_g10_feedback_archived_classified",
    "check_g10_issue_list_severity_status",
    "check_g10_executable_optimization_items",
    "check_g11_retro_complete",
    "check_g11_rules_templates_backfilled",
    "check_g11_next_round_direction",
    "check_risk_has_closed",
    "check_version_consistency_heuristic",
}
GOVERNANCE_CONTEXT_REQUIRED_FIELDS = [
    "status",
    "detected_item",
    "source_facts",
    "blocker_state",
    "next_action",
    "auto_continue",
    "interrupt_boundary",
]
GOVERNANCE_CONTEXT_SNAPSHOT_SECTIONS = {
    "遗留任务",
    "Carry-over tasks",
    "Carry over tasks",
    "Unfinished / deferred",
    "未完成 / 已延期",
    "下次会话优先级",
    "Next priorities",
    "Next session priorities",
}
GOVERNANCE_CONTEXT_BLOCKED_MARKERS = ("blocked", "阻塞", "卡住", "等待", "待确认")
CAPABILITY_CONTEXT_REQUIRED_FIELDS = [
    "scenario",
    "host_id",
    "available_capabilities",
    "selected_capability",
    "source_facts",
    "rejected_alternatives",
    "degradation",
    "side_effect_boundary",
    "validation_command",
    "review_requirement",
    "no_overclaim_boundary",
]
CAPABILITY_CONTEXT_ALLOWED_STATUSES = {
    "AVAILABLE",
    "BLOCKED",
    "DEGRADED",
    "NOT_SUPPORTED",
    "NOT_FOUND",
    "RESEARCH_ONLY",
}
CAPABILITY_CONTEXT_DEGRADED_STATUSES = {"BLOCKED", "DEGRADED", "NOT_SUPPORTED", "NOT_FOUND"}
CAPABILITY_CONTEXT_DOC_PATH = Path("docs/requirements/capability-discovery-orchestration-0.45.0.md")
CAPABILITY_CONTEXT_TOOLS_PATH = Path("skills/software-project-governance/infra/TOOLS.md")
CAPABILITY_CONTEXT_NO_OVERCLAIM_TOKENS = [
    "automatic global best-tool selection",
    "catalog entry",
    "runtime PASS",
    "diagnostic selection trace",
]
# CAPABILITY_REGISTRY_* constants moved to checks/capability_registry.py in 0.61.1
# (DEC-083 Phase 2 / REQ-103) and re-exported via the top-level import above so
# existing references (including test fixtures) keep working unchanged.
HOST_CAPABILITY_CONTEXT_REQUIRED_FIELDS = [
    "scenario",
    "host_id",
    "benchmark_kind",
    "source_facts",
    "restricted_scenarios",
    "side_effect_boundary",
    "validation_command",
    "review_requirement",
    "no_overclaim_boundary",
]
HOST_CAPABILITY_CONTEXT_SCENARIOS = {
    "no_network",
    "no_plugin_install",
    "no_mcp",
    "no_browser",
    "no_sub_agent",
    "local_skill_only",
    "codex_cli_blocked",
    "gemini_auth_blocked",
}
HOST_CAPABILITY_CONTEXT_REQUIRED_SCENARIO_FIELDS = [
    "scenario_id",
    "constraint",
    "preferred_capability",
    "selected_capability",
    "degradation_boundary",
    "validation_command",
    "source_facts",
    "no_overclaim_boundary",
]
HOST_CAPABILITY_CONTEXT_ALLOWED_STATUSES = {
    "PASS",
    "AVAILABLE",
    "BLOCKED",
    "DEGRADED",
    "NOT_SUPPORTED",
    "NOT_FOUND",
    "RESEARCH_ONLY",
}
HOST_CAPABILITY_CONTEXT_UNAVAILABLE_STATUSES = {
    "BLOCKED",
    "DEGRADED",
    "NOT_SUPPORTED",
    "NOT_FOUND",
    "RESEARCH_ONLY",
}
HOST_CAPABILITY_CONTEXT_BOUNDARY_TOKENS = [
    "benchmark/diagnostic",
    "not external execution",
    "not Desktop marketplace E2E PASS",
    "blocked capability is not runtime PASS",
    "catalog fact is not runtime PASS",
    "Do not claim automatic best-tool selection.",
    "Do not claim universal plugin availability.",
]
HOST_CAPABILITY_CONTEXT_FORBIDDEN_OVERCLAIMS = [
    "blocked capability runtime pass",
    "blocked capability is runtime pass",
    "blocked capability is available",
    "degraded capability runtime pass",
    "catalog fact runtime pass",
    "catalog fact is runtime pass",
    "codex desktop marketplace-management e2e pass",
    "desktop marketplace e2e pass",
    "officially approved",
    "official approval granted",
    "marketplace approved",
    "marketplace approval granted",
    "external execution",
    "successful external execution",
    "automatic best-tool selection",
    "automatically selects the best tool",
    "universal plugin availability",
    "universal plugin available",
    "universal plugins available",
    "1.0.0 production-ready",
]
HOST_CAPABILITY_CONTEXT_REQUIRED_BLOCKED_FACTS = {
    "codex_cli_blocked": "restricted benchmark scenario: Codex CLI blocked",
    "gemini_auth_blocked": "restricted benchmark scenario: Gemini auth blocked",
}


def _parse_markdown_table_rows(content, section_title=None):
    from adapter_readiness import _parse_markdown_table_rows as run
    return run(content, section_title)


def _matrix_status_for_manifest(manifest):
    from adapter_readiness import _matrix_status_for_manifest as run
    return run(manifest)


def check_runtime_readiness_matrix(root=None):
    from adapter_readiness import check_runtime_readiness_matrix as run, ReadinessPlatforms
    return run(
        root, package_root=ROOT, display_path=_display_path, load_adapter_manifest=_load_adapter_manifest,
        matrix_status_for_manifest=_matrix_status_for_manifest,
        parse_markdown_table_rows=_parse_markdown_table_rows,
        platforms=ReadinessPlatforms(
            mainstream_agent_adapters=_host_policy('MAINSTREAM_AGENT_ADAPTERS'),
            agent_ids=_host_policy('RUNTIME_MATRIX_AGENT_IDS'),
            research_only_ids=_host_policy('RUNTIME_MATRIX_RESEARCH_ONLY_IDS'),
        ),
    )


def check_first_session_measurement(root=None):
    from adapter_readiness import check_first_session_measurement as run
    return run(
        root, package_root=ROOT,
        first_session_measurement_allowed_statuses=_host_policy('FIRST_SESSION_MEASUREMENT_ALLOWED_STATUSES'),
        display_path=_display_path, parse_markdown_table_rows=_parse_markdown_table_rows,
    )


def _governance_pack_text_values(value):
    from host_governance_packs import _governance_pack_text_values as run
    return run(value, governance_pack_text_values=_governance_pack_text_values)


def _governance_pack_file_path(entry):
    from host_governance_packs import _governance_pack_file_path as run
    return run(entry)


def _is_valid_string_list(value):
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)


# _capability_registry_text_values + check_capability_registry moved to
# checks/capability_registry.py in 0.61.1 (DEC-083 Phase 2 / REQ-103) and
# re-exported via the top-level import.


def _lifecycle_registry_text_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _lifecycle_registry_text_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _lifecycle_registry_text_values(item)


def _load_lifecycle_registry(root=None):
    root = root or ROOT
    registry_path = root / "skills/software-project-governance/core/lifecycle-registry.json"
    display = _display_path(registry_path, root)
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [f"{display}: missing lifecycle registry"]
    except json.JSONDecodeError as exc:
        return None, [f"{display}: invalid JSON: {exc}"]
    except (ValueError, OSError, RecursionError) as exc:
        return None, [f"{display}: unreadable lifecycle registry: {exc}"]
    if not isinstance(registry, dict):
        return None, [f"{display}: lifecycle registry root must be an object"]
    return registry, []


def _lifecycle_registry_manifest_issues(root, registry_path, display):
    manifest_path = root / "skills/software-project-governance/core/manifest.json"
    if not manifest_path.exists():
        return [f"{display}: core/manifest.json is required to make the lifecycle registry a canonical product artifact"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{_display_path(manifest_path, root)}: invalid JSON: {exc}"]
    artifact_entries = _manifest_artifact_entries(manifest)
    registry_artifacts = [
        entry for entry in artifact_entries
        if isinstance(entry, dict)
        and entry.get("id") == "lifecycle-registry"
        and entry.get("path") == "skills/software-project-governance/core/lifecycle-registry.json"
    ]
    if not registry_artifacts:
        return [f"{display}: core/manifest.json must declare lifecycle-registry as a canonical product artifact"]
    return []


def _gate_execution_check_definition_issues(check, check_label):
    failures = []
    if not isinstance(check, dict):
        return [f"{check_label} must be an object"]
    missing_check_fields = sorted(GATE_EXECUTION_CHECK_REQUIRED_FIELDS - set(check))
    for field in missing_check_fields:
        failures.append(f"{check_label}: missing required field `{field}`")
    if not isinstance(check.get("check_id"), str) or not check.get("check_id", "").strip():
        failures.append(f"{check_label}.check_id must be a non-empty string")
    if not isinstance(check.get("label"), str) or not check.get("label", "").strip():
        failures.append(f"{check_label}.label must be a non-empty string")
    executor = check.get("executor")
    if executor not in GATE_EXECUTION_ALLOWED_EXECUTORS:
        failures.append(f"{check_label}.executor has unknown value `{executor}`")
    if check.get("severity") not in GATE_EXECUTION_ALLOWED_SEVERITIES:
        failures.append(f"{check_label}.severity must be one of {sorted(GATE_EXECUTION_ALLOWED_SEVERITIES)}")
    if executor == "function" and check.get("function") not in GATE_EXECUTION_ALLOWED_FUNCTIONS:
        failures.append(f"{check_label}.function has unknown value `{check.get('function')}`")
    if executor in {"file_exists", "snippet_in_file"} and not isinstance(check.get("path"), str):
        failures.append(f"{check_label}.path must be declared for {executor}")
    if executor == "snippet_in_file" and not isinstance(check.get("snippet"), str):
        failures.append(f"{check_label}.snippet must be declared for snippet_in_file")
    if executor == "completed_ratio" and not isinstance(check.get("min_ratio"), (int, float)):
        failures.append(f"{check_label}.min_ratio must be numeric for completed_ratio")
    if executor == "research_doc_count" and not isinstance(check.get("min_count"), int):
        failures.append(f"{check_label}.min_count must be integer for research_doc_count")
    if executor == "constant_result":
        if check.get("result") not in {"PASS", "FAIL", "NEEDS_HUMAN"}:
            failures.append(f"{check_label}.result must be PASS/FAIL/NEEDS_HUMAN")
        if not isinstance(check.get("message"), str) or not check.get("message", "").strip():
            failures.append(f"{check_label}.message must be a non-empty string")
    if executor == "evidence_mentions" and not isinstance(check.get("keyword"), str):
        failures.append(f"{check_label}.keyword must be declared for evidence_mentions")
    return failures


def _check_gate_execution_registry(registry, display, gate_id_set, project_type_hooks):
    failures = []
    gate_execution_registry = registry.get("gate_execution_registry")
    if not isinstance(gate_execution_registry, dict):
        return [f"{display}: gate_execution_registry must be an object"]

    missing_fields = sorted(GATE_EXECUTION_REGISTRY_REQUIRED_FIELDS - set(gate_execution_registry))
    for field in missing_fields:
        failures.append(f"{display}: gate_execution_registry missing required field `{field}`")
    if gate_execution_registry.get("status") != "unit-scoped":
        failures.append(f"{display}: gate_execution_registry.status must be unit-scoped")
    if gate_execution_registry.get("execution_scope") != "flow-unit":
        failures.append(f"{display}: gate_execution_registry.execution_scope must be flow-unit")
    if gate_execution_registry.get("automation_commands_are_metadata_only") is not True:
        failures.append(f"{display}: gate_execution_registry.automation_commands_are_metadata_only must be true")
    gate_checks = gate_execution_registry.get("gate_checks")
    if not isinstance(gate_checks, list):
        failures.append(f"{display}: gate_execution_registry.gate_checks must be a list")
        gate_checks = []
    gate_ids = [item.get("gate_id") for item in gate_checks if isinstance(item, dict)]
    if not all(isinstance(gate, str) for gate in gate_ids) or set(gate_ids) != gate_id_set or len(gate_ids) != len(gate_id_set):
        failures.append(f"{display}: gate_checks must define each referenced gate exactly once")

    project_type_keys = set(project_type_hooks) if isinstance(project_type_hooks, dict) else set()
    for gate_entry in gate_checks:
        if not isinstance(gate_entry, dict):
            failures.append(f"{display}: gate_execution_registry.gate_checks entries must be objects")
            continue
        gate_id = gate_entry.get("gate_id", "<missing>")
        gate_label = f"{display}: gate_execution_registry.{gate_id}"
        missing = sorted(GATE_EXECUTION_REQUIRED_FIELDS - set(gate_entry))
        for field in missing:
            failures.append(f"{gate_label}: missing required field `{field}`")
        if gate_id not in gate_id_set:
            failures.append(f"{gate_label}: gate_id must reference gate_references")
        if not _is_valid_string_list(gate_entry.get("required_artifacts")):
            failures.append(f"{gate_label}.required_artifacts must be a non-empty string list")
        evidence = gate_entry.get("evidence_query")
        if (not isinstance(evidence, dict) or not evidence.get("source")
                or not _is_valid_string_list(evidence.get("fields"))):
            failures.append(f"{gate_label}.evidence_query must declare its source and evidence fields")
        automation_command = gate_entry.get("automation_command")
        if not isinstance(automation_command, dict):
            failures.append(f"{gate_label}.automation_command must be metadata object")
            automation_command = {}
        else:
            command_text = automation_command.get("command")
            if not isinstance(command_text, str) or not command_text.strip():
                failures.append(f"{gate_label}.automation_command.command must be a non-empty metadata string")
            if automation_command.get("execution_policy") != "metadata-only-not-executed-by-gate-judgment":
                failures.append(f"{gate_label}.automation_command.execution_policy must be metadata-only-not-executed-by-gate-judgment")
        human_policy = gate_entry.get("human_confirmation_policy")
        if not isinstance(human_policy, dict):
            failures.append(f"{gate_label}.human_confirmation_policy must be an object")
            human_policy = {}
        else:
            if "needs_human_when" not in human_policy:
                failures.append(f"{gate_label}.human_confirmation_policy missing `needs_human_when`")
            if not isinstance(human_policy.get("confirmation_required_for_override", False), bool):
                failures.append(f"{gate_label}.human_confirmation_policy.confirmation_required_for_override must be boolean")
        if gate_entry.get("severity") not in GATE_EXECUTION_ALLOWED_SEVERITIES:
            failures.append(f"{gate_label}.severity must be one of {sorted(GATE_EXECUTION_ALLOWED_SEVERITIES)}")

        checks = gate_entry.get("checks")
        if not isinstance(checks, list) or not checks:
            failures.append(f"{gate_label}.checks must be a non-empty list")
            checks = []
        seen_check_ids = []
        for check in checks:
            if not isinstance(check, dict):
                failures.append(f"{gate_label}.checks entries must be objects")
                continue
            check_id = check.get("check_id", "<missing>")
            seen_check_ids.append(check_id)
            check_label = f"{gate_label}.checks.{check_id}"
            failures.extend(_gate_execution_check_definition_issues(check, check_label))
        duplicate_checks = sorted({check_id for check_id in seen_check_ids if seen_check_ids.count(check_id) > 1})
        for check_id in duplicate_checks:
            failures.append(f"{gate_label}.checks duplicate check_id `{check_id}`")

        overrides = gate_entry.get("project_type_overrides")
        if not isinstance(overrides, dict):
            failures.append(f"{gate_label}.project_type_overrides must be an object")
            overrides = {}
        unknown_overrides = sorted(set(overrides) - project_type_keys)
        for project_type in unknown_overrides:
            failures.append(f"{gate_label}.project_type_overrides unknown project type `{project_type}`")
        for project_type, override in overrides.items():
            override_label = f"{gate_label}.project_type_overrides.{project_type}"
            if not isinstance(override, dict):
                failures.append(f"{override_label} must be an object")
                continue
            if "additional_required_artifacts" in override and not isinstance(override.get("additional_required_artifacts"), list):
                failures.append(f"{override_label}.additional_required_artifacts must be a string list")
            elif "additional_required_artifacts" in override and not _is_valid_string_list(override.get("additional_required_artifacts")):
                failures.append(f"{override_label}.additional_required_artifacts must be a non-empty string list")
            if "additional_checks" in override:
                additional_checks = override.get("additional_checks")
                if not isinstance(additional_checks, list):
                    failures.append(f"{override_label}.additional_checks must be a list")
                else:
                    for index, check in enumerate(additional_checks):
                        if not isinstance(check, dict):
                            failures.append(f"{override_label}.additional_checks entries must be objects")
                            continue
                        check_id = check.get("check_id", f"index_{index}")
                        failures.extend(_gate_execution_check_definition_issues(
                            check,
                            f"{override_label}.additional_checks.{check_id}",
                        ))
            if "severity_override" in override and override.get("severity_override") not in GATE_EXECUTION_ALLOWED_SEVERITIES:
                failures.append(f"{override_label}.severity_override must be one of {sorted(GATE_EXECUTION_ALLOWED_SEVERITIES)}")

    return failures


def _gate_execution_registry_contract_issues(registry, display):
    gate_references = registry.get("gate_references")
    if isinstance(gate_references, list):
        gate_id_set = {
            gate.get("gate_id")
            for gate in gate_references
            if isinstance(gate, dict) and isinstance(gate.get("gate_id"), str)
        }
    else:
        gate_id_set = set()
    project_type_hooks = registry.get("project_type_hooks")
    if not isinstance(project_type_hooks, dict):
        project_type_hooks = {}
    return _check_gate_execution_registry(registry, display, gate_id_set, project_type_hooks)


def check_lifecycle_registry(root=None, registry=None):
    """Resolve the active workflow, tier routes, local evidence contracts and project presets."""
    import loop_engine
    from loop_workflow import TIERS

    root = Path(root or ROOT)
    core = root / "skills/software-project-governance/core"
    path = core / "lifecycle-registry.json"
    display = _display_path(path, root)
    if registry is None:
        registry, issues = _load_lifecycle_registry(root)
        if issues:
            return issues

    failures = _lifecycle_registry_manifest_issues(root, path, display)
    if registry.get("workflow") != "software-project-governance" or registry.get("source_of_truth") is not True:
        failures.append(f"{display}: invalid workflow or source_of_truth")
    if registry.get("registry_mode") != "loop-unit-gates":
        failures.append(f"{display}: registry_mode must be loop-unit-gates")
    for key in ("active_lifecycle_mode", "default_lifecycle_mode"):
        if registry.get(key) != "loop-engineering":
            failures.append(f"{display}: {key} must be loop-engineering")
    activation = registry.get("runtime_activation")
    for key in ("flow_unit_status_runtime", "unit_scoped_gate_execution"):
        if not isinstance(activation, dict) or activation.get(key) is not True:
            failures.append(f"{display}: runtime_activation.{key} must be true")
    modes = registry.get("lifecycle_modes")
    if not isinstance(modes, list) or len(modes) != 1 or not isinstance(modes[0], dict):
        return failures + [f"{display}: exactly one executable lifecycle mode is required"]
    mode = modes[0]
    if (mode.get("id") != "loop-engineering" or mode.get("active") is not True
            or mode.get("default") is not True or mode.get("runtime_command") != "loop"):
        failures.append(f"{display}: lifecycle_modes must select the loop command")
    if mode.get("workflow_source") != "lifecycle.md" or not (core / "lifecycle.md").is_file():
        failures.append(f"{display}: missing lifecycle.md workflow source")
    policy = registry.get("loop_policy")
    if not isinstance(policy, dict) or policy.get("scope") != "per-flow-unit" or policy.get("runtime_activation") is not True:
        failures.append(f"{display}: loop_policy must activate per-flow-unit execution")
        policy = policy if isinstance(policy, dict) else {}
    if policy.get("read_command") != "loop status --unit <id> --json":
        failures.append(f"{display}: loop_policy.read_command must select the unit")
    if any(item.get("topology_source") != "loop-engineering-registry.json" for item in (mode, policy)):
        failures.append(f"{display}: workflow and policy must reference the runtime topology")
    topology, topology_issues = loop_engine.load_loop_registry(core.parent)
    failures.extend(topology_issues)
    topology = topology if isinstance(topology, dict) else {}
    if topology.get("registry_mode") != "native-loop-execution" or topology.get("workflow_model") != "loop-engineering":
        failures.append(f"{display}: runtime topology must declare native loop execution")
    paths = topology.get("iteration_paths")
    if not isinstance(paths, dict) or set(paths) != set(TIERS):
        failures.append(f"{display}: every executable tier needs an iteration path")
        paths = paths if isinstance(paths, dict) else {}
    gates = set(LIFECYCLE_REGISTRY_GATES)
    consumed = {"G1"}  # explicit one-time project decision at setup intake
    for tier, route in paths.items():
        if not _is_valid_string_list(route) or not set(route) <= gates or len(route) != len(set(route)):
            failures.append(f"{display}: {tier} has invalid or empty local gates")
        else:
            consumed.update(route)
    if gates != consumed:
        failures.append(f"{display}: unconsumed local gates: {sorted(gates - consumed)}")
    targets = topology.get("rework_targets")
    if not isinstance(targets, dict):
        failures.append(f"{display}: topology must declare rework targets")
    else:
        for gate, pair in targets.items():
            if (gate not in gates or not isinstance(pair, list) or len(pair) != 2
                    or not isinstance(pair[0], str) or not isinstance(paths.get(pair[0]), list)
                    or pair[1] not in paths[pair[0]]):
                failures.append(f"{display}: invalid rework target for {gate}")

    activities = registry.get("stage_vocabulary") or []
    activity_gates = {a["id"]: a.get("related_gate") for a in activities
                      if isinstance(a, dict) and isinstance(a.get("id"), str)}
    refs = registry.get("gate_references")
    if not isinstance(refs, list):
        return failures + [f"{display}: missing gate_references"]
    catalog = core / "stage-gates.md"
    headings = set(re.findall(r"^##\s+(G\d+)\b", _read_text_normalized(catalog), re.M)) if catalog.is_file() else set()
    gate_id_set = set()
    for ref in refs:
        if not isinstance(ref, dict) or not isinstance(ref.get("gate_id"), str):
            failures.append(f"{display}: invalid gate reference")
            continue
        gate = ref["gate_id"]
        if gate in gate_id_set or gate not in gates:
            failures.append(f"{display}: duplicate or unknown gate reference {gate}")
        gate_id_set.add(gate)
        if (not isinstance(ref.get("activity"), str) or activity_gates.get(ref["activity"]) != gate
                or ref.get("source") != f"skills/software-project-governance/core/stage-gates.md#{gate}"
                or gate not in headings):
            failures.append(f"{display}: {gate} must resolve to its activity and gate evidence catalog section")
    if gate_id_set != gates:
        failures.append(f"{display}: missing gate reference {sorted(gates - gate_id_set)}")
    project_type_hooks = registry.get("project_type_hooks")
    if not isinstance(project_type_hooks, dict):
        failures.append(f"{display}: project_type_hooks must be an object")
        project_type_hooks = {}
    missing_hook_project_types = sorted(LIFECYCLE_REGISTRY_REQUIRED_PROJECT_TYPES - set(project_type_hooks))
    if missing_hook_project_types:
        failures.append(f"{display}: missing project_type_hooks for {', '.join(missing_hook_project_types)}")

    project_type_gate_presets = registry.get("project_type_gate_presets")
    if not isinstance(project_type_gate_presets, dict):
        failures.append(f"{display}: project_type_gate_presets must be an object")
        project_type_gate_presets = {}
    missing_preset_project_types = sorted(LIFECYCLE_REGISTRY_REQUIRED_PROJECT_TYPES - set(project_type_gate_presets))
    if missing_preset_project_types:
        failures.append(f"{display}: missing project_type_gate_presets for {', '.join(missing_preset_project_types)}")
    if set(project_type_gate_presets) != set(project_type_hooks):
        failures.append(f"{display}: project_type_gate_presets keys must match project_type_hooks keys")

    failures.extend(_check_gate_execution_registry(registry, display, gate_id_set, project_type_hooks))

    for project_type, hooks in project_type_hooks.items():
        hook_label = f"{display}: project_type_hooks.{project_type}"
        if not isinstance(hooks, dict):
            failures.append(f"{hook_label} must be an object")
            continue
        unit_templates = hooks.get("unit_templates")
        if not _is_valid_string_list(unit_templates):
            failures.append(f"{hook_label}.unit_templates must be a non-empty string list")
            continue
        default_flow_unit_type = hooks.get("default_flow_unit_type")
        if default_flow_unit_type not in unit_templates:
            failures.append(
                f"{hook_label}.default_flow_unit_type must be included in unit_templates"
            )
    for project_type, preset in project_type_gate_presets.items():
        preset_label = f"{display}: project_type_gate_presets.{project_type}"
        hooks = project_type_hooks.get(project_type, {})
        if not isinstance(preset, dict):
            failures.append(f"{preset_label} must be an object")
            continue
        missing_fields = sorted(LIFECYCLE_REGISTRY_REQUIRED_PRESET_FIELDS - set(preset))
        for field in missing_fields:
            failures.append(f"{preset_label}: missing required field `{field}`")

        boundary_text = preset.get("profile_intensity_boundary")
        if not isinstance(boundary_text, str) or not boundary_text.strip():
            failures.append(f"{preset_label}.profile_intensity_boundary must be a non-empty string")
        else:
            lowered_boundary = boundary_text.lower()
            if "project type" not in lowered_boundary or "profile" not in lowered_boundary or "orthogonal" not in lowered_boundary:
                failures.append(
                    f"{preset_label}.profile_intensity_boundary must state project type and profile are orthogonal"
                )

        for field in ("default_packs", "acceptance_templates", "release_checks"):
            if not _is_valid_string_list(preset.get(field)):
                failures.append(f"{preset_label}.{field} must be a non-empty string list")
        if "governance-core" not in preset.get("default_packs", []):
            failures.append(f"{preset_label}.default_packs must include governance-core")

        quality_budget = preset.get("quality_budget")
        if not isinstance(quality_budget, dict) or not quality_budget:
            failures.append(f"{preset_label}.quality_budget must be a non-empty object")
        else:
            for key, value in quality_budget.items():
                if not isinstance(key, str) or not key.strip() or not isinstance(value, str) or not value.strip():
                    failures.append(f"{preset_label}.quality_budget entries must be non-empty strings")

        gate_policy = preset.get("gate_policy")
        if not isinstance(gate_policy, dict):
            failures.append(f"{preset_label}.gate_policy must be an object")
            gate_policy = {}
        for field in sorted(LIFECYCLE_REGISTRY_GATE_POLICY_REQUIRED_FIELDS):
            if field not in gate_policy:
                failures.append(f"{preset_label}.gate_policy missing `{field}`")
        if not isinstance(gate_policy.get("can_skip_stages", []), list):
            failures.append(f"{preset_label}.gate_policy.can_skip_stages must be a list")
        if not isinstance(gate_policy.get("can_merge_stages", []), list):
            failures.append(f"{preset_label}.gate_policy.can_merge_stages must be a list")
        for field in ("stage_skip_requires", "blocked_dependency_rule", "sibling_completion_rule"):
            if not isinstance(gate_policy.get(field), str) or not gate_policy.get(field, "").strip():
                failures.append(f"{preset_label}.gate_policy.{field} must be a non-empty string")

        preset_unit_templates = preset.get("unit_templates")
        if not _is_valid_string_list(preset_unit_templates):
            failures.append(f"{preset_label}.unit_templates must be a non-empty string list")
            preset_unit_templates = []
        elif isinstance(hooks, dict) and _is_valid_string_list(hooks.get("unit_templates")) and preset_unit_templates != hooks.get("unit_templates"):
            failures.append(f"{preset_label}.unit_templates must match project_type_hooks.{project_type}.unit_templates")
        default_flow_unit_type = preset.get("default_flow_unit_type")
        if isinstance(hooks, dict) and hooks.get("default_flow_unit_type") and default_flow_unit_type != hooks.get("default_flow_unit_type"):
            failures.append(f"{preset_label}.default_flow_unit_type must match project_type_hooks.{project_type}.default_flow_unit_type")
        if default_flow_unit_type not in preset_unit_templates:
            failures.append(f"{preset_label}.default_flow_unit_type must be included in unit_templates")
        gate_standards = preset.get("gate_standards")
        if not isinstance(gate_standards, list) or not gate_standards:
            failures.append(f"{preset_label}.gate_standards must be a non-empty list")
            gate_standards = []
        standard_ids = set()
        for standard in gate_standards:
            if not isinstance(standard, dict):
                failures.append(f"{preset_label}.gate_standards entries must be objects")
                continue
            standard_id = standard.get("standard_id")
            if not isinstance(standard_id, str) or not standard_id.strip():
                failures.append(f"{preset_label}.gate_standards entry missing standard_id")
            else:
                standard_ids.add(standard_id)
            gate_refs = standard.get("gate_references")
            if not _is_valid_string_list(gate_refs):
                failures.append(f"{preset_label}.gate_standards.{standard_id}.gate_references must be a non-empty string list")
            else:
                for gate_id in gate_refs:
                    if gate_id not in gate_id_set:
                        failures.append(f"{preset_label}.gate_standards.{standard_id}: unknown gate reference `{gate_id}`")
            if not _is_valid_string_list(standard.get("required_evidence")):
                failures.append(f"{preset_label}.gate_standards.{standard_id}.required_evidence must be a non-empty string list")
        if project_type == "game":
            missing_standards = sorted(LIFECYCLE_REGISTRY_REQUIRED_GAME_STANDARDS - standard_ids)
            if missing_standards:
                failures.append(
                    f"{preset_label}.gate_standards missing game standards: {', '.join(missing_standards)}"
                )
        if project_type == "library":
            missing_standards = sorted(LIFECYCLE_REGISTRY_REQUIRED_LIBRARY_STANDARDS - standard_ids)
            if missing_standards:
                failures.append(
                    f"{preset_label}.gate_standards missing library standards: {', '.join(missing_standards)}"
                )

    for text in _lifecycle_registry_text_values(registry):
        lowered = text.lower()
        for label, pattern in LIFECYCLE_REGISTRY_FORBIDDEN_OVERCLAIMS:
            for match in pattern.finditer(lowered):
                matched_text = text[match.start():match.end()]
                if not _line_has_scoped_claim_negation(text, matched_text):
                    failures.append(f"{display}: forbidden lifecycle overclaim `{label}`")
                    break
        for label, pattern in LIFECYCLE_REGISTRY_RISK_CLAIMS:
            if pattern.search(lowered) and not _line_has_scoped_claim_negation(text, label):
                failures.append(f"{display}: forbidden lifecycle overclaim `{label}`")

    return failures


def _flow_unit_runtime_path(root=None):
    return (root or HOST_PROJECT_ROOT) / FLOW_UNIT_RUNTIME_STATE_REL


def check_governance_packs(root=None):
    from host_governance_packs import check_governance_packs as run, PackRules
    return run(
        root, package_root=ROOT, display_path=_display_path,
        governance_pack_file_path=_governance_pack_file_path,
        governance_pack_text_values=_governance_pack_text_values,
        line_has_scoped_claim_negation=_line_has_scoped_claim_negation,
        manifest_artifact_entries=_manifest_artifact_entries,
        packs_rules=PackRules(
            boundary_tokens=_host_policy('GOVERNANCE_PACK_BOUNDARY_TOKENS'),
            forbidden_overclaims=_host_policy('GOVERNANCE_PACK_FORBIDDEN_OVERCLAIMS'),
            ids=_host_policy('GOVERNANCE_PACK_IDS'),
            known_checks=_host_policy('GOVERNANCE_PACK_KNOWN_CHECKS'),
            profile_ids=_host_policy('GOVERNANCE_PACK_PROFILE_IDS'),
            required_fields=_host_policy('GOVERNANCE_PACK_REQUIRED_FIELDS'),
        ),
    )


def check_readme_pack_guidance(root=None):
    from host_governance_packs import check_readme_pack_guidance as run
    return run(
        root, package_root=ROOT, governance_pack_ids=_host_policy('GOVERNANCE_PACK_IDS'),
        readme_pack_guidance_required_tokens=_host_policy('README_PACK_GUIDANCE_REQUIRED_TOKENS'),
        display_path=_display_path, line_has_scoped_claim_negation=_line_has_scoped_claim_negation,
    )


def _mainstream_loading_line_has_safe_negation(lines, index, phrase):
    from host_loading_claims import _mainstream_loading_line_has_safe_negation as run
    return run(
        lines, index, phrase,
        mainstream_agent_loading_forbidden_claim_terms=_host_policy('MAINSTREAM_AGENT_LOADING_FORBIDDEN_CLAIM_TERMS'),
        mainstream_agent_loading_forbidden_overclaims=_host_policy('MAINSTREAM_AGENT_LOADING_FORBIDDEN_OVERCLAIMS'),
    )


def _append_mainstream_loading_overclaim_issues(failures, path, content, root):
    from host_loading_claims import _append_mainstream_loading_overclaim_issues as run, LoadingClaimBoundaries
    return run(
        failures, path, content, root, display_path=_display_path,
        line_has_scoped_claim_negation=_line_has_scoped_claim_negation,
        mainstream_loading_line_has_safe_negation=_mainstream_loading_line_has_safe_negation,
        claims=LoadingClaimBoundaries(
            forbidden_claim_terms=_host_policy('MAINSTREAM_AGENT_LOADING_FORBIDDEN_CLAIM_TERMS'),
            forbidden_overclaims=_host_policy('MAINSTREAM_AGENT_LOADING_FORBIDDEN_OVERCLAIMS'),
            tier2=_host_policy('MAINSTREAM_AGENT_LOADING_TIER2'),
        ),
    )


def _append_mainstream_loading_common_doc_issues(failures, path, content, root, *, require_boundary=True):
    from host_loading_claims import _append_mainstream_loading_common_doc_issues as run
    return run(failures, path, content, root, require_boundary=require_boundary, display_path=_display_path)


def check_mainstream_agent_loading(root=None):
    from host_loading_claims import check_mainstream_agent_loading as run, HostLoadingRules
    return run(
        root, package_root=ROOT,
        append_mainstream_loading_common_doc_issues=_append_mainstream_loading_common_doc_issues,
        append_mainstream_loading_overclaim_issues=_append_mainstream_loading_overclaim_issues,
        display_path=_display_path, parse_markdown_table_rows=_parse_markdown_table_rows,
        loading=HostLoadingRules(
            adapters=_host_policy('MAINSTREAM_AGENT_LOADING_ADAPTERS'),
            readme_tokens=_host_policy('MAINSTREAM_AGENT_LOADING_README_TOKENS'),
            required_docs=_host_policy('MAINSTREAM_AGENT_LOADING_REQUIRED_DOCS'),
            requirements_tokens=_host_policy('MAINSTREAM_AGENT_LOADING_REQUIREMENTS_TOKENS'),
            tier1=_host_policy('MAINSTREAM_AGENT_LOADING_TIER1'),
            tier2=_host_policy('MAINSTREAM_AGENT_LOADING_TIER2'),
        ),
    )


def _append_pack_overclaim_issues(failures, path, content, root):
    from host_governance_packs import _append_pack_overclaim_issues as run
    return run(
        failures, path, content, root,
        governance_pack_status_forbidden_overclaims=_host_policy('GOVERNANCE_PACK_STATUS_FORBIDDEN_OVERCLAIMS'),
        display_path=_display_path, line_has_scoped_claim_negation=_line_has_scoped_claim_negation,
    )


def _append_missing_status_boundary_issues(failures, path, content, root):
    from host_governance_packs import _append_missing_status_boundary_issues as run
    return run(
        failures, path, content, root,
        governance_pack_status_boundary_tokens=_host_policy('GOVERNANCE_PACK_STATUS_BOUNDARY_TOKENS'),
        display_path=_display_path,
    )


def check_governance_pack_status(root=None):
    from host_governance_packs import check_governance_pack_status as run, PackReleaseBoundaries
    return run(
        root, package_root=ROOT,
        append_missing_status_boundary_issues=_append_missing_status_boundary_issues,
        append_pack_overclaim_issues=_append_pack_overclaim_issues, display_path=_display_path,
        release=PackReleaseBoundaries(
            release_boundary_path=_host_policy('GOVERNANCE_PACK_RELEASE_BOUNDARY_PATH'),
            release_boundary_tokens=_host_policy('GOVERNANCE_PACK_RELEASE_BOUNDARY_TOKENS'),
            status_doc_paths=_host_policy('GOVERNANCE_PACK_STATUS_DOC_PATHS'),
        ),
    )


def _validate_runtime_e2e_block(root, manifest_path, runtime_e2e, field_name, allow_unsupported=False):
    from adapter_contracts import _validate_runtime_e2e_block as run
    return run(root, manifest_path, runtime_e2e, field_name, allow_unsupported, display_path=_display_path)


def _validate_runtime_capabilities(root, manifest_path, manifest):
    from adapter_contracts import _validate_runtime_capabilities as run, CapabilityRules
    return run(
        root, manifest_path, manifest, display_path=_display_path,
        capabilities_rules=CapabilityRules(
            policy=_host_policy('ADAPTER_RUNTIME_CAPABILITY_POLICY'),
            keys=_host_policy('RUNTIME_CAPABILITY_KEYS'),
            statuses=_host_policy('RUNTIME_CAPABILITY_STATUSES'),
        ),
    )


def _validate_codex_runtime_e2e_claim(root, manifest_path, runtime_e2e):
    from adapter_contracts import _validate_codex_runtime_e2e_claim as run
    return run(root, manifest_path, runtime_e2e, display_path=_display_path)


def _gemini_settings_candidates(home=None):
    from runtime_preflight import _gemini_settings_candidates as run
    return run(home)


def _safe_env_present(name, env=None):
    from runtime_preflight import _safe_env_present as run
    return run(name, env)


def _detect_gemini_auth_from_settings(path):
    from runtime_preflight import _detect_gemini_auth_from_settings as run
    return run(path)


def _detect_gemini_env_auth_sources(env=None):
    from runtime_preflight import _detect_gemini_env_auth_sources as run, CredentialVariables
    return run(
        env, safe_env_present=_safe_env_present,
        variables=CredentialVariables(
            api_key_env_vars=_host_policy('GEMINI_API_KEY_ENV_VARS'),
            gca_credential_env_vars=_host_policy('GEMINI_GCA_CREDENTIAL_ENV_VARS'),
            vertex_credential_env_vars=_host_policy('GEMINI_VERTEX_CREDENTIAL_ENV_VARS'),
        ),
    )


def _gemini_auth_preflight(env=None, home=None, which=shutil.which, version_runner=_run_version_command):
    from runtime_preflight import _gemini_auth_preflight as run
    return run(
        env, home, which, version_runner, gemini_auth_remediation=_host_policy('GEMINI_AUTH_REMEDIATION'),
        detect_gemini_auth_from_settings=_detect_gemini_auth_from_settings,
        detect_gemini_env_auth_sources=_detect_gemini_env_auth_sources,
        gemini_settings_candidates=_gemini_settings_candidates, truncate_log=_truncate_log,
    )


def _validate_gemini_auth_preflight_claim(root, manifest_path, runtime_e2e):
    from adapter_contracts import _validate_gemini_auth_preflight_claim as run
    return run(root, manifest_path, runtime_e2e, display_path=_display_path)


def _run_opencode_probe_command(command, timeout=15):
    from runtime_preflight import _run_opencode_probe_command as run
    return run(command, timeout, package_root=ROOT, e2e_output=_e2e_output)


def _opencode_config_candidates(home=None, root=None):
    from runtime_preflight import _opencode_config_candidates as run
    return run(home, root, package_root=ROOT)


def _sanitize_opencode_probe_text(text):
    from runtime_preflight import _sanitize_opencode_probe_text as run
    return run(text, truncate_log=_truncate_log)


def _opencode_model_scan(text):
    from runtime_preflight import _opencode_model_scan as run
    return run(text, opencode_legal_deepseek_models=_host_policy('OPENCODE_LEGAL_DEEPSEEK_MODELS'))


def _opencode_provider_model_preflight(home=None, root=None, which=shutil.which, version_runner=_run_version_command, probe_runner=_run_opencode_probe_command, config_candidates=None):
    from runtime_preflight import _opencode_provider_model_preflight as run
    return run(
        home, root, which, version_runner, probe_runner, config_candidates,
        opencode_provider_model_remediation=_host_policy('OPENCODE_PROVIDER_MODEL_REMEDIATION'),
        opencode_config_candidates=_opencode_config_candidates, opencode_model_scan=_opencode_model_scan,
        sanitize_opencode_probe_text=_sanitize_opencode_probe_text,
    )


def _validate_opencode_provider_model_preflight_claim(root, manifest_path, runtime_e2e):
    from adapter_contracts import _validate_opencode_provider_model_preflight_claim as run
    return run(
        root, manifest_path, runtime_e2e,
        opencode_legal_deepseek_models=_host_policy('OPENCODE_LEGAL_DEEPSEEK_MODELS'),
        display_path=_display_path,
    )


def check_agent_adapter_contract(root=None, run_runtime=False):
    from adapter_contracts import check_agent_adapter_contract as run
    return run(
        root, run_runtime, package_root=ROOT, adapter_required_keys=_host_policy('ADAPTER_REQUIRED_KEYS'),
        mainstream_agent_adapters=_host_policy('MAINSTREAM_AGENT_ADAPTERS'), display_path=_display_path,
        load_adapter_manifest=_load_adapter_manifest, run_version_command=_run_version_command,
        validate_codex_runtime_e2e_claim=_validate_codex_runtime_e2e_claim,
        validate_gemini_auth_preflight_claim=_validate_gemini_auth_preflight_claim,
        validate_opencode_provider_model_preflight_claim=_validate_opencode_provider_model_preflight_claim,
        validate_runtime_capabilities=_validate_runtime_capabilities,
        validate_runtime_e2e_block=_validate_runtime_e2e_block,
    )


def _resolve_release_gate_timeout(raw):
    from release_execution import _resolve_release_gate_timeout as run
    return run(raw, release_gate_timeout_default=_product_policy("_RELEASE_GATE_TIMEOUT_DEFAULT"))


def _run_release_validation_command(label, command, timeout=None):
    from release_execution import _run_release_validation_command as run
    return run(
        label, command, timeout, package_root=ROOT,
        release_gate_timeout_env=_product_policy("_RELEASE_GATE_TIMEOUT_ENV"),
        resolve_release_gate_timeout=_resolve_release_gate_timeout,
    )


def run_release_execution_gates(runner=_run_release_validation_command, timeout=None):
    from release_execution import run_release_execution_gates as run
    return run(runner, timeout, package_root=ROOT)


def _release_docs_line_has_guard_context(label, line):
    from product_evidence import _release_docs_line_has_guard_context as run
    return run(label, line)


def _tagged_release_replay_hint(version):
    from product_evidence import _tagged_release_replay_hint as run
    return run(version)


def check_release_docs_coverage(version, root=None):
    from product_evidence import check_release_docs_coverage as run
    return run(
        version, root, package_root=ROOT, display_path=_display_path, git_files=_git_files,
        line_has_scoped_claim_negation=_line_has_scoped_claim_negation,
        release_docs_line_has_guard_context=_release_docs_line_has_guard_context,
        tagged_release_replay_hint=_tagged_release_replay_hint,
        check_manifest_consistency=check_manifest_consistency,
    )


def _markdown_table_row_by_first_cell(content, first_cell):
    from product_evidence import _markdown_table_row_by_first_cell as run
    return run(content, first_cell, split_markdown_table_row=_split_markdown_table_row)


def _contains_unnegated_phrase(content, phrases):
    from product_evidence import _contains_unnegated_phrase as run
    return run(
        content, phrases, line_has_scoped_claim_negation=_line_has_scoped_claim_negation,
        line_has_structured_status_negation=_line_has_structured_status_negation,
    )


def _line_has_structured_status_negation(line, phrase):
    from product_evidence import _line_has_structured_status_negation as run
    return run(line, phrase)


def _risk_status_is_closed(status):
    from product_evidence import _risk_status_is_closed as run
    return run(status)


def check_one_dot_zero_release_blockers(root=None, risk_log_path=None, external_validation_path=None, official_submission_path=None, desktop_lifecycle_path=None):
    from product_evidence import check_one_dot_zero_release_blockers as run
    return run(
        root, risk_log_path, external_validation_path, official_submission_path, desktop_lifecycle_path,
        package_root=ROOT, contains_unnegated_phrase=_contains_unnegated_phrase, display_path=_display_path,
        markdown_table_row_by_first_cell=_markdown_table_row_by_first_cell,
        risk_status_is_closed=_risk_status_is_closed,
    )



_extract_skill_version = version_checks.extract_skill_version


def _extract_json_version(path):
    from repository_projection import _extract_json_version as run
    return run(path)


def _extract_plan_workflow_version(path):
    from repository_projection import _extract_plan_workflow_version as run
    return run(path)


def _projection_hash(path):
    from repository_projection import _projection_hash as run
    return run(path, read_text_normalized=_read_text_normalized)


def _projection_source_files(root, patterns=None):
    from repository_projection import _projection_source_files as run
    return run(root, patterns, projection_sync_patterns=_product_policy("PROJECTION_SYNC_PATTERNS"))


def _projection_target_tracked_files(root, target_dir):
    from repository_projection import _projection_target_tracked_files as run
    return run(root, target_dir)


def _target_fixture_file_is_checkable(rel_path, target_tracked):
    from repository_projection import _target_fixture_file_is_checkable as run
    return run(rel_path, target_tracked)


def check_projection_sync(root=None, target_dir=None, patterns=None):
    """Delegate projection compatibility checks to the Phase 6 module."""
    return projection_checks.check_projection_sync(
        Path(root) if root is not None else ROOT,
        Path(target_dir) if target_dir is not None else None,
        patterns,
    )


def check_injection_contract(root=None):
    from repository_projection import check_injection_contract as run
    return run(
        root, package_root=ROOT, injection_contract_anchors=_product_policy("INJECTION_CONTRACT_ANCHORS"),
        injection_contract_staged_anchors=_product_policy("INJECTION_CONTRACT_STAGED_ANCHORS"),
        version_line_anchor=_product_policy("VERSION_LINE_ANCHOR"),
        extract_skill_version=_extract_skill_version,
    )


# ── FEAT-039 / AUDIT-154 slice A-8: injection-size budget gate ──────────────
#
# AUDIT-154 §5 ("诉点 3"): the workflow ships quality gates but owns no budget
# gate for its OWN injected surfaces — "预算不守护则瘦身必然回弹". The
# measurement + render leaf lives in ``checks/injection_budget.py`` (this
# engine's LOC and print counts are only-down under the ArchGuard ratchet), so
# the engine keeps dispatch wiring + the Check 33 sub-report only, and the
# tests/CLI/check all read ONE definition:
#
#   * ``checks.injection_budget``  — surfaces, tokenizer calibration, validation
#   * ``cmd_check_injection_budget`` — dispatch wiring (engine module path)
#   * Check 33 — prints the same report inside the aggregate box
#
# CI wiring (no new CI system): every commit/PR already runs
# ``check-governance``, which prints this report inside Check 33; a pipeline
# that needs its own exit code runs ``check-injection-budget
# --fail-on-issues`` (FAIL → exit 1), and a job that asserts values reads
# ``--format json`` (``verdict`` / ``tiers``).
from checks import injection_budget as injection_budget  # noqa: E402
from checks.injection_budget import cmd_check_injection_budget  # noqa: E402,F401
# Public surface re-exported for the check, the CLI and the test suite: one
# definition, three consumers (never re-implemented per caller).
from checks.injection_budget import (  # noqa: E402,F401
    BUDGET_TIER_POLICY,
    ENTRY_TEMPLATE_MARKERS,
    INJECTION_BUDGET_DEFAULT_PROFILE,
    INJECTION_BUDGET_PROFILES,
    INJECTION_BUDGET_SURFACES,
    INJECTION_BUDGET_TOKENS,
    INJECTION_SURFACE_SCOPE_FULL_FILE,
    INJECTION_SURFACE_SCOPE_PERSONA_PREFIX,
    INJECTION_SURFACE_SCOPE_TEMPLATE_BLOCK,
    check_tool_return_budget,
    count_ascii_chars,
    count_cjk_chars,
    estimate_surface_tokens,
    estimate_surface_tokens_host,
    extract_marked_block,
    extract_persona_prefix_from_template,
    find_marker_line,
    injection_budget_tier_gate,
    load_injection_surface,
    normalize_token_budget,
    set_injection_budget_surface_profiles,
    tokenizer_calibration,
)


def check_injection_budget(root=None, profile=None, budget_tokens=None):
    """Engine entry — the leaf supplies the default root (``ROOT`` is ours)."""
    return injection_budget.check_injection_budget(
        root if root is not None else ROOT, profile, budget_tokens)


def emit_injection_budget_section(indent="  ", result=None):
    """Engine entry — the Check 33 sub-report, framed inside the box."""
    return injection_budget.emit_check_section(indent=indent, result=result)


# ── FEAT-015 / RISK-049 ②: isolated preset-session smoke gate ───────────────
#
# RISK-049 closure standard (2): "安装后 preset 会话可用" must be a repeatable
# machine gate, not a reasoning step. The gate runs the adapter launcher's
# ``--smoke`` action under a temp DSH_HOME created here (M7.7 (a): env
# redirection; the real ~/.dsh is only fingerprinted by the launcher, never
# written) and reports the launcher's verdict.
#
# Fail-closed: a missing launcher, a non-zero exit, a timeout, or an isolation
# refusal is FAIL with the launcher's diagnostics — never a silent PASS. The
# temp home is removed afterwards so the gate leaves no residue.


def check_dsh_preset_smoke(root=None, timeout=120):
    from host_loader_probes import check_dsh_preset_smoke as run, SmokeMarkers
    return run(
        root, timeout, plugin_root=PLUGIN_ROOT,
        markers=SmokeMarkers(
            concurrent_writes=_host_policy('DSH_SMOKE_ATTRIBUTED_CONCURRENT_WRITES_RE'),
            home_writes=_host_policy('DSH_SMOKE_REAL_HOME_WRITES_RE'),
            passed=_host_policy('DSH_SMOKE_RESULT_PASS_RE'),
        ),
    )


# ── FEAT-016 / RISK-049 ③: dsh upgrade regression as a release gate ──────────
#
# RISK-049 closure standard (3) (risk-log L49): the dsh upgrade regression
# checklist (isolated re-verification command set, readme.md L380-440 — temp
# DSH_HOME link:/file: re-checks, launch.py preset install, --smoke) becomes
# a machine-enforced part of release readiness instead of a one-off manual
# ritual. The command set REUSES the FEAT-015 isolated preset-session smoke
# (check_dsh_preset_smoke): the launcher subprocess runs under a temp
# redirected DSH_HOME (M7.7 (a)) and fingerprints the real ~/.dsh — a run
# reporting real-home writes is refused, so this release gate inherits the
# zero-real-home-write guarantee. Timeout honors the FIX-234 precedent
# (SPG_RELEASE_GATE_TIMEOUT env override, module default — the FIX-400
# recalibration provenance lives on _RELEASE_GATE_TIMEOUT_DEFAULT).



def run_dsh_upgrade_regression_gates(smoke_runner=None):
    from host_loader_probes import run_dsh_upgrade_regression_gates as run
    return run(
        smoke_runner, plugin_root=PLUGIN_ROOT,
        dsh_upgrade_regression_label=_host_policy('DSH_UPGRADE_REGRESSION_LABEL'),
        release_gate_timeout_env=_product_policy("_RELEASE_GATE_TIMEOUT_ENV"),
        resolve_release_gate_timeout=_resolve_release_gate_timeout,
        check_dsh_preset_smoke=check_dsh_preset_smoke,
    )


# ── FEAT-080 / ADR-021 B3: provenance wiring plumbing ──────────────────────
#
# Engine-side assembly shared by the Check 41 (Priority Inversion Guard)
# box and the release-readiness provenance sub-check: the PriorityReport →
# provenance-rows mapping and the live row build. The judgement predicates
# stay in checks/provenance_domain.py (pure, ArchGuard R1 discipline — the
# engine does I/O assembly and rendering only).

def _provenance_rows_from_report(report):
    from release_provenance import _provenance_rows_from_report as run
    return run(report)


def _provenance_rows_for_governance(tracker_path=None, governance_dir=None):
    from release_provenance import _provenance_rows_for_governance as run
    return run(
        tracker_path, governance_dir, read_governance_dir=GOVERNANCE_DIR, plan_path=SAMPLE_PATH,
        provenance_rows_from_report=_provenance_rows_from_report,
    )


def _collect_session_closure_events(governance_dir=None, today=None):
    from release_provenance import _collect_session_closure_events as run
    return run(governance_dir, today, read_governance_dir=GOVERNANCE_DIR)


def check_release_readiness(
    version=None,
    require_changelog=False,
    run_runtime_adapters=False,
    changelog_path=None,
    run_execution_gates=False,
    execution_gate_runner=_run_release_validation_command,
    lineage_mode="candidate",
    release_commit=None,
    lineage_remote="origin",
    release_unit=None,
    dsh_upgrade_regression_runner=None,
    require_delivery_evidence=False,
):
    """FIX-072: aggregate release gate scripts behind the stage-release check-release command."""
    import release_readiness as gate

    plugin_release = not _host_plugin_roots_divergent()
    replay_hint = _tagged_release_replay_hint(version) if plugin_release else None
    if replay_hint:
        return {"pass": False, "issues": [replay_hint],
                "details": {"release_replay": {"pass": False, "issues": [replay_hint]}}}

    details = {}
    issues = []
    if plugin_release:
        gate.version_consistency(details, issues, check_version_consistency())
        gate.pack_status(details, issues, check_governance_pack_status())
    if version:
        gate.admission(details, issues, version, _provenance_rows_for_governance())
    gate.security_descriptors(details, issues, HOST_PROJECT_ROOT, PLUGIN_ROOT if plugin_release else None)
    if plugin_release:
        gate.agent_adapters(details, issues, check_agent_adapter_contract(run_runtime=run_runtime_adapters),
                            run_runtime_adapters)
        gate.projection_sync(details, issues, check_projection_sync())
        gate.cross_references(details, issues, check_cross_references())
    gate.archive_integrity(details, issues, check_archive_integrity())
    if plugin_release:
        gate.release_docs(details, issues, version, check_release_docs_coverage(version))

    lineage = check_release_lineage(version=version, mode=lineage_mode, release_commit=release_commit,
                                  remote=lineage_remote)
    details["release_lineage"] = lineage
    issues.extend(f"release lineage: {issue}" for issue in lineage["issues"])
    gate.release_delivery(details, issues, lambda: HOST_PROJECT_ROOT, release_unit, version,
                          lineage_mode, require_delivery_evidence)
    if plugin_release:
        gate.release_blockers(details, issues, version, check_one_dot_zero_release_blockers() if version == "1.0.0" else [])
        gate.execution_gates(details, issues, run_execution_gates,
                             run_release_execution_gates(runner=execution_gate_runner) if run_execution_gates else [])
    else:
        gate.project_ci(details, issues, check_ci_evidence(repo_root=HOST_PROJECT_ROOT))
    gate.dsh_upgrade(details, issues, plugin_release, run_execution_gates, lineage_mode,
                     lambda: (dsh_upgrade_regression_runner or run_dsh_upgrade_regression_gates)())
    path = changelog_path or (ROOT / "project/CHANGELOG.md" if plugin_release else HOST_PROJECT_ROOT / "CHANGELOG.md")
    gate.changelog(details, issues, version, require_changelog, path, _display_path)
    exceptions = _release_exception_block()
    if exceptions is not None:
        details["governance_exceptions"] = exceptions
    return {"pass": not issues, "issues": issues, "details": details}


def _run_git_lineage(args, root=None):
    from release_provenance import _run_git_lineage as run
    return run(
        args, root, host_project_root=HOST_PROJECT_ROOT,
        git_lineage_timeout_seconds=_product_policy("GIT_LINEAGE_TIMEOUT_SECONDS"),
    )


def _validated_git_remote_name(remote):
    from release_provenance import _validated_git_remote_name as run
    return run(remote, git_remote_name_re=_product_policy("GIT_REMOTE_NAME_RE"))


def check_release_lineage(version, mode='candidate', release_commit=None, remote='origin', root=None):
    from release_provenance import check_release_lineage as run
    return run(
        version, mode, release_commit, remote, root, host_project_root=HOST_PROJECT_ROOT,
        git_lineage_timeout_seconds=_product_policy("GIT_LINEAGE_TIMEOUT_SECONDS"),
        run_git_lineage=_run_git_lineage, inspect_lineage=commit_checks.check_release_lineage,
    )



def _specialist_skill_owner_issues(root, router):
    from product_evidence import _specialist_skill_owner_issues as run
    return run(root, router, active_agent_roles=_host_policy("ACTIVE_AGENT_ROLES"))


def check_architecture_fact_source(skill_path=None, skill_index_path=None, architecture_path=None, governance_command_path=None, agent_protocol_path=None, governance_developer_prompt_path=None):
    from product_evidence import check_architecture_fact_source as run
    return run(
        skill_path, skill_index_path, architecture_path, governance_command_path, agent_protocol_path,
        governance_developer_prompt_path, package_root=ROOT, active_agent_roles=_host_policy("ACTIVE_AGENT_ROLES"),
        loop_role_skill_contracts=_host_policy("LOOP_ROLE_SKILL_CONTRACTS"), named_reviewer_roles=_host_policy("NAMED_REVIEWER_ROLES"),
        display_path=_display_path, generic_reviewer_cells=_generic_reviewer_cells,
        markdown_has_heading=_markdown_has_heading, markdown_section=_markdown_section,
        specialist_skill_owner_issues=_specialist_skill_owner_issues,
        check_repository_navigation=check_repository_navigation,
    )


# ── Markdown parsing helpers ─────────────────────────────────────

# Governance FACTS (plan-tracker / session-snapshot) live in the HOST
# project .governance/, never in the plugin cache (FIX-187 / DEC-080).
SAMPLE_PATH = HOST_PROJECT_ROOT / ".governance" / "plan-tracker.md"
SESSION_SNAPSHOT_PATH = HOST_PROJECT_ROOT / ".governance" / "session-snapshot.md"


def _governance_dir():
    """Dynamic governance dir — tracks SAMPLE_PATH.parent at call time.

    Tests patch SAMPLE_PATH (e.g. to a tempdir); this helper makes every
    runtime governance-path read follow that patch, so GOVERNANCE_DIR no
    longer needs to be patched separately. Module-level constants derived
    from GOVERNANCE_DIR (EVIDENCE_PATH / RISK_PATH / ARCHIVE_*) are kept
    for backward-compat but runtime code SHOULD call this helper.
    """
    return SAMPLE_PATH.parent


# Plugin ASSETS (stage-gates / lifecycle / stage skills) live with the
# plugin, so they resolve against PLUGIN_ROOT.
GATES_PATH = PLUGIN_ROOT / "skills" / "software-project-governance" / "core" / "stage-gates.md"
LIFECYCLE_PATH = PLUGIN_ROOT / "skills" / "software-project-governance" / "core" / "lifecycle.md"
STAGE_SKILLS_ROOT = PLUGIN_ROOT / "skills"

STAGE_ORDER = [
    "initiation", "research", "selection", "infrastructure",
    "architecture", "development", "testing", "ci-cd",
    "release", "operations", "maintenance",
]

STAGE_SKILL_ALIASES = {
    "infra": "infrastructure",
    "infrastructure": "infrastructure",
    "cicd": "ci-cd",
    "ci-cd": "ci-cd",
}

STAGE_SKILL_DIR_NAMES = {
    "infrastructure": "stage-infra",
    "ci-cd": "stage-cicd",
}

STATUS_ICONS = {
    "passed": "[PASS]",
    "passed-on-entry": "[ENTRY]",
    "blocked": "[BLOCK]",
    "pending": "[????]",
}


def _extract_section(content, heading, stop_headings=None):
    from plan_status import _extract_section as read
    return read(content, heading, stop_headings)


def parse_project_config(path=None):
    from plan_status import parse_project_config as read
    return read(path, plan_path=SAMPLE_PATH)


def parse_overview():
    from plan_status import parse_overview as read
    return read(plan_path=SAMPLE_PATH)


def _normalize_task_status(status_text):
    from plan_status import _normalize_task_status as read
    return read(status_text)


def parse_task_stats():
    from plan_status import parse_task_stats as read
    return read(plan_path=SAMPLE_PATH)


def _context_root(root=None):
    return Path(root) if root is not None else ROOT


def _context_file(root, relative_path):
    return _context_root(root) / relative_path


def _empty_governance_context(root=None):
    from project_context import _empty_governance_context as read
    return read(_context_root(root))


def _capability_context_path(root, relative_path):
    return _context_root(root) / relative_path


def _capability_file_fact(root, relative_path, label):
    from capability_context import _capability_file_fact as read
    return read(_context_root(root), relative_path, label)


def _capability_text_contains(root, relative_path, token):
    from capability_context import _capability_text_contains as read
    return read(_context_root(root), relative_path, token)


def _capability_cli_registration_fact(root, relative_path):
    from capability_context import _capability_cli_registration_fact as read
    return read(_context_root(root), relative_path)


def _capability_host_id(root):
    from capability_context import _capability_host_id as read
    return read(_context_root(root))


def discover_capability_context(root=None):
    from capability_context import discover_capability_context as read
    return read(
        _context_root(root),
        requirements_path=CAPABILITY_CONTEXT_DOC_PATH,
        tools_path=CAPABILITY_CONTEXT_TOOLS_PATH,
        check_registry=check_capability_registry,
    )


def _host_capability_source_fact(root, relative_path, present_label, missing_label):
    from capability_context import _host_capability_source_fact as read
    return read(_context_root(root), relative_path, present_label, missing_label)


def _host_context_registry_capabilities(root):
    from capability_context import _host_context_registry_capabilities as read
    return read(_context_root(root), display_path=_display_path)


def _host_context_capability(capabilities, kind=None, capability_id=None):
    from capability_context import _host_context_capability as read
    return read(capabilities, kind, capability_id)


def _host_context_fact_contains(root, relative_path, tokens):
    from capability_context import _host_context_fact_contains as read
    return read(_context_root(root), relative_path, tokens)


def _host_restricted_scenario(scenario_id, constraint, preferred, selected, status, reason, source_facts, validation_command):
    from capability_context import _host_restricted_scenario as read
    return read(scenario_id, constraint, preferred, selected, status, reason, source_facts, validation_command)


def discover_host_capability_context(root=None):
    from capability_context import discover_host_capability_context as read
    return read(_context_root(root), registry_capabilities=_host_context_registry_capabilities)


def _host_context_values(value):
    from capability_context import _host_context_values as read
    return read(value)


def check_host_capability_context(root=None, *, sampled_context=None):
    from capability_context import RestrictedHostPolicy, check_host_capability_context as validate
    root = _context_root(root)
    context = discover_host_capability_context(root) if sampled_context is None else sampled_context
    policy = RestrictedHostPolicy(
        required_fields=HOST_CAPABILITY_CONTEXT_REQUIRED_FIELDS,
        allowed_statuses=HOST_CAPABILITY_CONTEXT_ALLOWED_STATUSES,
        scenario_fields=HOST_CAPABILITY_CONTEXT_REQUIRED_SCENARIO_FIELDS,
        scenarios=HOST_CAPABILITY_CONTEXT_SCENARIOS,
        unavailable_statuses=HOST_CAPABILITY_CONTEXT_UNAVAILABLE_STATUSES,
        boundary_tokens=HOST_CAPABILITY_CONTEXT_BOUNDARY_TOKENS,
        forbidden_claims=HOST_CAPABILITY_CONTEXT_FORBIDDEN_OVERCLAIMS,
        blocked_facts=HOST_CAPABILITY_CONTEXT_REQUIRED_BLOCKED_FACTS,
    )
    return validate(
        root, context, policy=policy, requirements_path=CAPABILITY_CONTEXT_DOC_PATH,
        tools_path=CAPABILITY_CONTEXT_TOOLS_PATH, display_path=_display_path,
        valid_string_list=_is_valid_string_list,
        has_scoped_negation=_line_has_scoped_claim_negation,
    )


def _context_task(item_id, title, status, source, raw_line, priority='', kind='task'):
    from project_context import _context_task as read
    return read(item_id, title, status, source, raw_line, priority, kind)


def _extract_task_title_from_line(line, task_id):
    from project_context import _extract_task_title_from_line as read
    return read(line, task_id)


def _parse_plan_context_tasks(root):
    from project_context import _parse_plan_context_tasks as read
    return read(
        _context_root(root), is_incomplete=_is_incomplete_task_status,
        normalize_priority=_normalize_priority,
    )


def _parse_snapshot_context_tasks(root):
    from project_context import _parse_snapshot_context_tasks as read
    return read(
        _context_root(root),
        is_incomplete=_is_incomplete_task_status,
        normalize_priority=_normalize_priority,
        sections=GOVERNANCE_CONTEXT_SNAPSHOT_SECTIONS,
    )


def _context_git_toplevel(root):
    from project_context import _context_git_toplevel as read
    return read(root)


def _is_context_git_repo_root(root):
    from project_context import _is_context_git_repo_root as read
    return read(root)


def _run_context_git(root, args):
    from project_context import _run_context_git as read
    return read(root, args)


def _is_context_product_file(path):
    from project_context import _is_context_product_file as read
    return read(path, entry_files=_product_policy("PLATFORM_ENTRY_FILES"), product_patterns=PRODUCT_CODE_PATTERNS)


def _parse_git_status_context_tasks(root):
    from project_context import _parse_git_status_context_tasks as read
    return read(root, is_product_file=_is_context_product_file)


def _parse_recent_commit_context_facts(root, limit=5):
    from project_context import _parse_recent_commit_context_facts as read
    return read(root, limit)


def _dedupe_context_items(items):
    from project_context import _dedupe_context_items as read
    return read(items)


def discover_governance_context(root=None, skip_evidence_log=False):
    from project_context import discover_governance_context as read
    return read(_context_root(root), skip_evidence_log)


def check_governance_context(root=None):
    from project_context import check_governance_context as read
    return read(
        _context_root(root),
        discover=discover_governance_context,
        display_path=_display_path,
        read_text=_read_text_normalized,
    )


def check_capability_context(root=None, *, sampled_context=None):
    from capability_context import SelectionPolicy, check_capability_context as validate
    root = _context_root(root)
    context = discover_capability_context(root) if sampled_context is None else sampled_context
    policy = SelectionPolicy(
        required_fields=CAPABILITY_CONTEXT_REQUIRED_FIELDS,
        allowed_statuses=CAPABILITY_CONTEXT_ALLOWED_STATUSES,
        degraded_statuses=CAPABILITY_CONTEXT_DEGRADED_STATUSES,
        boundary_tokens=CAPABILITY_CONTEXT_NO_OVERCLAIM_TOKENS,
    )
    return validate(
        root, context, policy=policy, requirements_path=CAPABILITY_CONTEXT_DOC_PATH,
        tools_path=CAPABILITY_CONTEXT_TOOLS_PATH, display_path=_display_path,
    )


def parse_session_snapshot_carry_over_tasks(snapshot_path=None):
    from governance_views import parse_session_snapshot_carry_over_tasks as read
    path = Path(snapshot_path) if snapshot_path is not None else SESSION_SNAPSHOT_PATH
    return read(path, is_incomplete=_is_incomplete_task_status, normalize_priority=_normalize_priority)


def build_delivery_trust_snapshot(project_root=None, unit_id=None):
    from governance_views import build_delivery_trust_snapshot as read
    return read(project_root if project_root is not None else GOVERNANCE_DIR.parent, unit_id)


FIRST_RUN_DEMO_REQUIRED_FIELDS = ["Work units", "State", "Next action"]
FIRST_RUN_DEMO_REQUIRED_MARKERS = ["Delivery Trust Snapshot", "demo-delivery", "demo-export",
                                   "totals match", "loop-evidence/", "local/demo-only"]


def render_delivery_trust_snapshot(snapshot):
    from governance_views import render_delivery_trust_snapshot as read
    return read(snapshot)

def build_first_run_demo_snapshot():
    from governance_views import build_first_run_demo_snapshot as read
    return read(build_delivery_trust_snapshot)


def assert_first_run_demo_snapshot(snapshot, rendered_text=None):
    from governance_views import assert_first_run_demo_snapshot as read
    return read(
        snapshot, rendered_text,
        required_fields=FIRST_RUN_DEMO_REQUIRED_FIELDS,
        required_markers=FIRST_RUN_DEMO_REQUIRED_MARKERS,
        render=render_delivery_trust_snapshot,
    )


def parse_gate_detail(gate_id):
    from governance_views import parse_gate_detail as read
    return read(gate_id, gates_path=GATES_PATH)


def normalize_stage_name(stage_name):
    from governance_views import normalize_stage_name as read
    return read(stage_name, aliases=STAGE_SKILL_ALIASES)


def stage_skill_dir_name(stage_name):
    from governance_views import stage_skill_dir_name as read
    return read(stage_name, directories=STAGE_SKILL_DIR_NAMES, normalize=normalize_stage_name)


def stage_skill_path(stage_name):
    from governance_views import stage_skill_path as read
    return read(stage_name, stages_root=STAGE_SKILLS_ROOT, directory_name=stage_skill_dir_name)


def _stage_name_from_skill_dir(dirname):
    from governance_views import _stage_name_from_skill_dir as read
    return read(dirname, directories=STAGE_SKILL_DIR_NAMES, normalize=normalize_stage_name)


def list_available_stages():
    from governance_views import list_available_stages as read
    return read(
        stage_order=STAGE_ORDER,
        stages_root=STAGE_SKILLS_ROOT,
        skill_path=stage_skill_path,
        stage_name=_stage_name_from_skill_dir)


# ── Governance health check parsers ─────────────────────────────
# These derive from SAMPLE_PATH.parent (== GOVERNANCE_DIR) rather than the
# module-level GOVERNANCE_DIR constant so that tests which patch SAMPLE_PATH
# (and thereby its parent) correctly redirect all governance-fact reads.
# SAMPLE_PATH itself is HOST_PROJECT_ROOT / ".governance" / "plan-tracker.md",
# so SAMPLE_PATH.parent is exactly the host project's governance dir.

EVIDENCE_PATH = SAMPLE_PATH.parent / "evidence-log.md"
RISK_PATH = SAMPLE_PATH.parent / "risk-log.md"
ARCHIVE_INDEX_PATH = SAMPLE_PATH.parent / "archive" / "index.md"
ARCHIVE_TASKS_DIR = SAMPLE_PATH.parent / "archive" / "tasks"
ARCHIVE_EVIDENCE_DIR = SAMPLE_PATH.parent / "archive" / "evidence"
ARCHIVE_DECISIONS_DIR = SAMPLE_PATH.parent / "archive" / "decisions"
ARCHIVE_RISKS_DIR = SAMPLE_PATH.parent / "archive" / "risks"


def _load_archive_module():
    from governance_archive_data import _load_archive_module as read
    return read(plugin_root=ROOT, host_root=HOST_PROJECT_ROOT)


# ── SYSGAP-030: GovernanceDataSource (archive-aware data source) ──

@_cache
def _archive_reader_class():
    """Build the historical public type once across imports and programmatic overrides."""
    from governance_archive_data import GovernanceDataSource as ArchiveReader

    class GovernanceDataSource(ArchiveReader):
        """Archive reader using the current host and the CLI's configurable fact paths."""

        def __init__(self, sample_path=None, evidence_path=None, archive_index_path=None,
                     archive_root=None, decision_path=None, risk_path=None):
            super().__init__(
                GOVERNANCE_DIR, SAMPLE_PATH if sample_path is None else sample_path,
                EVIDENCE_PATH if evidence_path is None else evidence_path,
                archive_index_path, archive_root, decision_path, risk_path,
            )

        @staticmethod
        def _table_cells(line):
            return _split_markdown_table_row(line)

        @staticmethod
        def _expand_task_ids(text):
            return expand_task_ids(text)

    GovernanceDataSource.__qualname__ = "GovernanceDataSource"
    return globals().setdefault("GovernanceDataSource", GovernanceDataSource)




def _archive_reader(*args, **kwargs):
    # Module-global lookup does not run PEP 562. Honor an installed reader override.
    try:
        reader = GovernanceDataSource
    except NameError:
        reader = __getattr__("GovernanceDataSource")
    return reader(*args, **kwargs)


def parse_completed_task_ids():
    from governance_archive_data import parse_completed_task_ids as read
    return read(plan_path=SAMPLE_PATH)


def expand_task_ids(raw_text):
    from governance_archive_data import expand_task_ids as read
    return read(raw_text)


def check_gate_consistency():
    """Check the evidence actually consumed by each unit, plus task closure references."""
    from checks.loop_receipts import receipt_issues

    ds = _archive_reader()
    evidenced = ds.get_all_evidence_task_map()
    issues = [{"type": "loop_receipt", "detail": issue} for issue in receipt_issues(GOVERNANCE_DIR.parent)]

    # Check for tasks marked 已完成 in plan-tracker but no evidence.
    # Uses GovernanceDataSource to cover both hot files + archive files.
    completeness = check_evidence_completeness()
    tasks_without_evidence = completeness["missing_evidence"]
    if tasks_without_evidence:
        issues.append({
            "type": "completed_tasks_missing_evidence",
            "detail": tasks_without_evidence,
        })
    if completeness.get("historical_missing_evidence"):
        issues.append({
            "type": "historical_completed_tasks_missing_evidence",
            "detail": completeness["historical_missing_evidence"],
        })

    # Check for evidence entries referencing non-existent tasks.
    # Uses GovernanceDataSource to include archived tasks.
    all_tasks = ds.get_all_task_ids()

    orphan_evidence = set(evidenced.keys()) - all_tasks
    if orphan_evidence:
        issues.append({
            "type": "orphan_evidence",
            "detail": sorted(orphan_evidence),
        })

    return issues


def check_protocol_compliance():
    """Check protocol compliance: DRI assignment, evidence format, conditional pass tracking.

    This is the external validation counterpart to M8 agent self-check.
    It independently detects structural protocol violations from governance records.
    """
    issues = {
        "dri_violations": [],       # Tasks without unique DRI
        "evidence_format": [],      # Evidence entries with missing required fields
        "conditional_pass": [],     # passed-with-conditions without corrective tasks
    }

    plan_content = SAMPLE_PATH.read_text(encoding="utf-8")

    # ── DRI Check: tasks with missing/multi-valued/ambiguous Owner ──
    task_rows = []
    in_table = False
    for line in plan_content.split("\n"):
        line = line.strip()
        if "## 样例跟踪表" in line:
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if in_table and line.startswith("|") and not "---" in line:
            parts = [p.strip() for p in line.split("|")]
            # Skip header row
            if parts[1] == "ID" or not re.match(r"[A-Z]+-\d+", parts[1]):
                continue
            task_rows.append(parts)

    dri_violations = []
    for parts in task_rows:
        if len(parts) < 11:
            continue
        task_id = parts[1]
        status = parts[10] if len(parts) > 10 else ""
        owner = parts[7] if len(parts) > 7 else ""

        # Only check active tasks — FIX-479: shared terminal predicate
        # (_status_is_terminal_cell; emoji-prefixed terminal shapes like
        # 「✅ 已完成」 are terminal too, same source as Check 9)
        if _status_is_terminal_cell(status):
            continue

        # Check for DRI violations
        violations = []
        if not owner or owner == "":
            violations.append("Owner is empty")
        elif any(sep in owner for sep in ("+", "/", "、", "&", ",")):
            violations.append(f"Owner is multi-valued: '{owner}'")
        elif owner in ("待定", "多人", "TBD", "N/A", "未分配"):
            violations.append(f"Owner is ambiguous: '{owner}'")

        if violations:
            dri_violations.append({
                "task_id": task_id,
                "status": status,
                "owner": owner,
                "violations": violations,
            })

    issues["dri_violations"] = dri_violations



    # ── Evidence Format Check: evidence entries with missing required fields ──
    evidence_path = GOVERNANCE_DIR / "evidence-log.md"
    if evidence_path.is_file():
        ev_content = evidence_path.read_text(encoding="utf-8")
        for line in ev_content.split("\n"):
            line = line.strip()
            if not line.startswith("| EVD-"):
                continue
            # FIX-372 (review-FIX-368-CODE-R0 P2-1): validate the LIVE
            # evidence-log column layout (FIX-368). _governance_table_cells
            # strips the leading/trailing empties and preserves pipes inside
            # JSON/code-span cells, so cells are pure data cells:
            #   LIVE 10-cell rows: 0=EVD, 1=TaskID, 2=Type, 3=Description,
            #     4=fact basis, 5=Location, 6=EntryMethod(录入方式), 7=Date,
            #     8=Gate, 9=Notes
            #   9-cell historical rows (no separate file column): 0=EVD,
            #     1=TaskID, 2=Type, 3=Description, 4=fact basis, 5=Author,
            #     6=Date, 7=Gate, 8=Notes
            # The pre-fix check validated the legacy Stage-column offsets
            # (3=Stage/4=Type/5=Description), reading the LIVE fact-basis
            # column as Description (false "missing Description" when the
            # fact cell was empty) and flagging 9-cell historical rows as
            # short rows. The Stage requirement is dropped: the LIVE layout
            # has no Stage column. 9-cell rows are validated against their
            # own offsets (Author/Date) instead of being rejected. FIX-374:
            # a date-shaped cells[6] proves the historical Date cell is
            # present; a 9-cell row failing that shape test is a truncated
            # LIVE row (Date cell lost) and is validated against the LIVE
            # offsets with Date reported missing (review-FIX-372-CODE-R0 F-1).
            cells = _governance_table_cells(line)
            if len(cells) < 9:
                issues["evidence_format"].append(
                    f"{cells[0] if cells else '???'}: only {len(cells)} data fields (expected ≥9)"
                )
                continue

            evd_id = cells[0]
            missing = []
            if not cells[1]:
                missing.append("TaskID")
            if not cells[2]:
                missing.append("Type")
            if not cells[3]:
                missing.append("Description")
            if len(cells) >= 10:
                # LIVE 10-cell shape
                if not cells[5]:
                    missing.append("Location")
                if not cells[6]:
                    missing.append("EntryMethod")
                if not cells[7]:
                    missing.append("Date")
            else:
                # FIX-374 (review-FIX-372-CODE-R0 F-1): a 9-cell row is
                # ambiguous — either a genuine historical row (Author in
                # cells[5], Date in cells[6]) or a truncated LIVE row that
                # lost its Date cell (the EntryMethod text then sits in
                # cells[6], and the pre-fix branch read Location/
                # EntryMethod as Author/Date, silently passing a genuinely
                # missing Date — fail-blind). Disambiguate by content
                # shape (_EVIDENCE_DATE_SHAPE_RE): a date-shaped cells[6]
                # proves the historical Date cell is present; anything
                # else contradicts the historical Date semantics and is
                # validated as a truncated LIVE row.
                #
                # FIX-382 (review-FIX-374 F-2② combo criterion): within
                # the non-date cells[6] face, a date-shaped cells[7]
                # proves the real Date cell survived at its shifted LIVE
                # offset — the row lost a TRAILING cell (Gate or Notes),
                # not Date, so "missing Date" there was a false positive;
                # report the trailing loss instead. Issue count is
                # unchanged (still flagged, fail-noisy) — only the
                # message becomes accurate. Residual face kept open by
                # decision (explicit no-fix + ledger disclosure): losing
                # a cell BEFORE Date (fact/Location/EntryMethod) is
                # content-indistinguishable from a genuine historical row
                # (identical Date/Gate/Notes tail; free-text middle
                # cells) — criteria extension would false-positive on the
                # historical exemption face.
                if _EVIDENCE_DATE_SHAPE_RE.match(cells[6]):
                    # Historical shape: the Date cell is date-shaped (and
                    # thus non-empty) by construction.
                    if not cells[5]:
                        missing.append("Author")
                elif _EVIDENCE_DATE_SHAPE_RE.match(cells[7]):
                    # Truncated LIVE, trailing loss (Gate or Notes): the
                    # Date cell is present at cells[7]; Location/
                    # EntryMethod emptiness stays validated at their
                    # unshifted offsets (an empty cell and a lost trailing
                    # cell can coexist).
                    if not cells[5]:
                        missing.append("Location")
                    if not cells[6]:
                        missing.append("EntryMethod")
                    missing.append(
                        "Gate/Notes (trailing LIVE cell lost"
                        " — Date present at shifted offset)"
                    )
                else:
                    # Truncated LIVE with a genuinely lost Date cell (or a
                    # historical row with an empty/non-separator Date cell
                    # — fail-noisy either way): validate the LIVE columns
                    # at their real offsets and report the lost Date cell.
                    if not cells[5]:
                        missing.append("Location")
                    if not cells[6]:
                        missing.append("EntryMethod")
                    missing.append("Date")

            if missing:
                issues["evidence_format"].append(
                    f"{evd_id}: missing fields — {', '.join(missing)}"
                )

    return issues


def parse_tier_definitions():
    """Parse Tier definitions from plan-tracker's DEC-052 implementation roadmap.

    Returns: dict mapping tier_id (e.g., "0-A") -> list of task IDs.
    """
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    lines = content.split("\n")

    in_roadmap = False
    tiers = {}
    current_tier = None

    for line in lines:
        # Detect start of implementation roadmap section
        if line.strip() == "## 实施路线图（DEC-052）":
            in_roadmap = True
            continue
        # Stop at next top-level section
        if in_roadmap and line.startswith("## "):
            break

        if not in_roadmap:
            continue

        # Detect Tier header: "Tier 0-A: description"
        tier_match = re.match(r"^Tier (\d+-[A-Z]):", line)
        if tier_match:
            current_tier = tier_match.group(1)
            tiers[current_tier] = []
            continue

        # Collect task IDs within current tier
        # Format: "  AUDIT-XXX (PX) — description" or "  MAINT-XXX (PX) — description"
        if current_tier:
            task_match = re.match(r"^\s+([A-Z]+-\d+)\s+\(P\d\)", line)
            if task_match:
                tiers[current_tier].append(task_match.group(1))

    return tiers


def parse_task_status_map():
    """Return dict mapping task_id -> status from ALL tracking tables in plan-tracker.

    Scans the entire file for task rows regardless of section boundaries,
    since tracking tables are spread across multiple subsections.
    """
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    status_map = {}

    for line in content.split("\n"):
        line_stripped = line.strip()
        if not line_stripped.startswith("| ") or "---" in line_stripped:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 11:
            task_id_match = re.match(r"([A-Z]+-\d+)", parts[1])
            if task_id_match:
                task_id = task_id_match.group(1)
                status = parts[10] if len(parts) > 10 else ""
                status_map[task_id] = status

    return status_map


def check_tier_audit_completeness():
    """Check that each completed Tier has a corresponding TIER-X-Y-AUDIT evidence entry.

    Per DEC-052 execution discipline rule #3: every completed Tier MUST have an audit.
    Audit evidence uses task ID format: TIER-<layer>-<tier>-AUDIT (e.g., TIER-0-C-AUDIT).

    Returns: dict with tier details and issue lists.
    """
    tiers = parse_tier_definitions()
    status_map = parse_task_status_map()
    evidence_task_ids = parse_evidence_task_ids()

    completed_without_audit = []
    completed_with_audit = []
    incomplete_tiers = []
    all_details = []

    for tier_id, task_ids in tiers.items():
        if not task_ids:
            continue

        # Check status of each task in this tier
        task_statuses = {}
        all_completed = True
        completed_count = 0
        for tid in task_ids:
            status = status_map.get(tid, "未找到")
            task_statuses[tid] = status
            if status == "已完成":
                completed_count += 1
            else:
                all_completed = False

        # Check for TIER audit evidence
        audit_evidence_id = f"TIER-{tier_id}-AUDIT"
        has_audit = audit_evidence_id in evidence_task_ids

        detail = {
            "tier_id": tier_id,
            "task_count": len(task_ids),
            "completed_count": completed_count,
            "task_statuses": task_statuses,
            "all_completed": all_completed,
            "has_audit": has_audit,
            "audit_evidence_id": audit_evidence_id,
        }
        all_details.append(detail)

        if all_completed and not has_audit:
            completed_without_audit.append(detail)
        elif all_completed and has_audit:
            completed_with_audit.append(detail)
        elif not all_completed:
            incomplete_tiers.append(detail)

    return {
        "completed_without_audit": completed_without_audit,
        "completed_with_audit": completed_with_audit,
        "incomplete_tiers": incomplete_tiers,
        "all_details": all_details,
    }


def check_version_consistency():
    """Delegate version consistency checks to the Phase 6 module."""
    return version_checks.check_version_consistency(ROOT, GOVERNANCE_DIR.parent)



def check_commit_task_references(limit=20):
    from checks.commit import check_commit_task_references as run
    return run(limit, product_root=ROOT)


def check_task_deadline():
    from checks.commit import check_task_deadline as run
    return run(plan_path=SAMPLE_PATH, status_is_terminal_cell=_status_is_terminal_cell)


# ── CLI commands ─────────────────────────────────────────────────

def cmd_verify(args):
    from plugin_assets import report_verification
    print("== Workflow Plugin Verification ==")
    return report_verification(check_files(), check_snippets(), check_architecture_fact_source(),
                               check_agent_adapter_contract(), check_version_consistency(),
                               check_loop_role_skill_consistency())


# ── FIX-270 交付 A: status 秒级状态快路径（Scenario F 结构化数据源）──────
# 行级/流式解析 .governance 热文件（plan-tracker / risk-log / decision-log /
# session-snapshot）。明确不读全量 evidence-log 大文件（其体量可达 MB 级）；
# 最近活动只从 plan-tracker task 表 + decision-log 派生。所有解析器为纯
# 确定性函数（可注入内容或走 live 读），任何异常 fail-safe 为缺省值，
# 状态快路径绝不以解析失败阻断。


def _status_col_name(raw):
    from plan_status import _status_col_name as read
    return read(raw)


def _status_clean_cell(value):
    from plan_status import _status_clean_cell as read
    return read(value)


def _status_iso_date(value):
    from plan_status import _status_iso_date as read
    return read(value)


# FIX-291 W-7/BC-7 (review-FIX-278-DESIGN-R1 §1.1 residual / §3 BC-7):
# terminal-marker vocabulary for MIXED transition-chain status cells. A status
# cell may record a state history whose FINAL state is terminal without ever
# using the bare 「完成」 wording — 「⏳ 待执行 (…) → ✅ 已发布 (…)」 /
# 「🔄 进行中 (…) → ✅ 已关闭 (…)」 (live instance: REL-069). The ✅ branch
# above is excluded by the active marker and the 完成( fallback misses the
# wording, so such cells were judged ACTIVE — a conservative missed downgrade
# (BC-7: fail-safe side, never a masking misjudge).
#
# R1 scope tightening (review-FIX-291-CODE-R0 P2-1 four prose-misjudge shapes
# + review-FIX-291-DESIGN-R0 P2-3 version-context shape): a terminal marker
# only counts as a TERMINAL ASSERTION when it IS the state word of a
# transition segment —
#   (a) segment start: the text before the marker (skipping whitespace and an
#       optional ✅ qualification) is empty (cell start) or ends with a
#       transition boundary (→ / — / ——);
#   (b) terminal date: the marker is immediately followed by a date annotation
#       （(YYYY-MM-DD …）or the cell end (the dogfood convention always dates
#       the terminal state).
# Narrative mentions are thereby excluded: a subject before the marker
# (「方案A已撤回」「依赖令牌失效」「窗口取消」), a parenthetical version context
# (「v0.78.0 已发布后启动」), a segment-initial version prefix
# (「——0.78.1 已发布」) and a comma continuation without a date
# (「——已撤回，改推方案B」) are NOT assertions. 「推进中」 stays in the ACTIVE
# set (not in the ✅-branch exclusion set) so 「0.78.0 已发布，0.79.0 推进中」
# remains ACTIVE.


def _last_marker_pos(text, markers):
    from plan_status import _last_marker_pos as read
    return read(text, markers)


def _w7_terminal_assertion_positions(text):
    from plan_status import _w7_terminal_assertion_positions as read
    return read(text, markers=_host_policy("_W7_TERMINAL_MARKERS"), terminal_date=_host_policy("_W7_TERMINAL_DATE_RE"))


# FIX-393 — writer-terminal recognition (0.89.0). verify_workflow already
# imports task_row_update (the governed task-row writer), so the writer's
# OWN chain object is consumed BY IDENTITY — zero drift by construction (the
# sibling mirrors in task_priority.py / archive.py are byte-pinned to it by
# tests/test_fix393_writer_terminal_states.py). Terminal ⟺ chain first-hit
# is ``committed`` (contracts.TASK_TRANSITIONS' only terminal state) AND the
# ops receipt anchor 〔op-<32hex>〕 is present on the cell — display-prefix
# text like 「committed 审查中」 without the anchor is never guessed
# terminal. Search-anywhere anchor: live cells may carry narrative brackets
# AFTER the anchor (FEAT-061's trailing 〔R0 …〕 group).
_WRITER_STATE_MARKER_CHAIN = task_row_update._STATE_MARKER_CHAIN


def _status_is_writer_committed_cell(text):
    from plan_status import _status_is_writer_committed_cell as read
    return read(text, operation_anchor=_host_policy("_WRITER_OP_ANCHOR_RE"), state_chain=_WRITER_STATE_MARKER_CHAIN)


def _status_is_completed_cell(cell):
    from plan_status import _status_is_completed_cell as read
    return read(
        cell,
        active_markers=_host_policy("_W7_ACTIVE_MARKERS"),
        writer_committed=_status_is_writer_committed_cell,
        terminal_positions=_w7_terminal_assertion_positions,
    )


# ── FIX-479 — shared TERMINAL-status predicate for plan-table task rows ────
#
# check_task_deadline (Check 9) and check_protocol_compliance (DRI) both
# filtered terminal rows with a bare two-word membership test (exact
# 「已完成」/「已终止」 only), which misses the emoji-prefixed
# terminal shapes live plan-trackers carry (host python_game Layer1 probe
# 2026-11-04: 35 false-overdue rows, e.g. DEV-001/ARC-001「✅ 已完成」).
# P5 single-semantic-source rule: terminal detection converges HERE — one
# vocabulary constant + one predicate, both plan-table call sites source
# from it. Completion semantics stay single-sourced in
# _status_is_completed_cell (bare/✅-prefixed wording, W-7 mixed chains,
# FIX-393 writer-committed); the ONLY vocabulary this predicate adds is
# the leading decoration set below — a display-prefix emoji before a
# terminal cell (「⏳ ✅ committed」 compound prefix) is not a state
# assertion and must not resurrect a delivered row as active.
_TERMINAL_CELL_DECORATIONS = ("⏳", "🔄", "📋", "🆕", "⏸")


def _status_is_terminal_cell(cell):
    from plan_status import _status_is_terminal_cell as read
    return read(cell, decorations=_TERMINAL_CELL_DECORATIONS, is_completed=_status_is_completed_cell)


def _status_table_stream(content):
    from plan_status import _status_table_stream as read
    return read(content)


def parse_task_table_rows(plan_content=None):
    from plan_status import parse_task_table_rows as read
    return read(plan_content, plan_path=SAMPLE_PATH)


def parse_recent_completed_tasks(rows, n=5):
    from plan_status import parse_recent_completed_tasks as read
    return read(rows, n, is_completed=_status_is_completed_cell)


def parse_recent_decisions(n=5, decision_content=None):
    from plan_status import parse_recent_decisions as read
    return read(n, decision_content, governance_dir=GOVERNANCE_DIR)


def _status_plugin_freshness(plan_content=None):
    from plan_status import _status_plugin_freshness as read
    return read(plan_content, plan_path=SAMPLE_PATH)


_STATUS_ID_TOKEN_RE = re.compile(r"(?<![-A-Z])([A-Z]+)-(\d+)\b")


def _status_priority_rank(priority):
    from plan_status import _status_priority_rank as read
    return read(priority)


def _status_raw_dependency_ids(rec):
    from plan_status import _status_raw_dependency_ids as read
    return read(rec, task_id_pattern=_STATUS_ID_TOKEN_RE)


def _status_next_steps(plan_content, max_results=3):
    from plan_status import _status_next_steps as read
    return read(
        plan_content, max_results,
        read_rows=parse_task_table_rows,
        is_completed=_status_is_completed_cell,
        dependency_ids=_status_raw_dependency_ids,
    )


def _status_task_stats(rows):
    from plan_status import _status_task_stats as read
    return read(rows, is_completed=_status_is_completed_cell)


def cmd_status(args):
    from status_cli import cmd_status as read
    return read(args, host_root=HOST_PROJECT_ROOT)

def _status_project_name(config, overview):
    from plan_status import _status_project_name as read
    return read(config, overview)


def cmd_governance_context(args):
    from status_cli import cmd_governance_context as read
    return read(args, host_root=HOST_PROJECT_ROOT)

def cmd_capability_context(args):
    from status_cli import cmd_capability_context as read
    return read(
        args,
        plugin_root=ROOT,
        discover=discover_capability_context,
        validate=check_capability_context,
        display_path=_display_path,
    )


def cmd_first_run_demo(args):
    from status_cli import cmd_first_run_demo as read
    return read(
        args,
        build_snapshot=build_first_run_demo_snapshot,
        validate_snapshot=assert_first_run_demo_snapshot,
        render=render_delivery_trust_snapshot,
        required_fields=FIRST_RUN_DEMO_REQUIRED_FIELDS,
    )


def cmd_gate(args):
    """Inspect the scoped gate and its evidence, without granting authorization."""
    return cmd_gates(args)


def cmd_gates(args):
    from status_cli import cmd_gates as read
    return read(args, host_root=HOST_PROJECT_ROOT)


def cmd_stage(args):
    from status_cli import cmd_stage as read
    return read(args, normalize=normalize_stage_name, skill_path=stage_skill_path)


def cmd_stages(args):
    from status_cli import cmd_stages as read
    return read(args, stages=list_available_stages)

# ── SYSGAP-008: Cross-Reference Checking ──────────────────────────

# ── FIX-432 (F-4 / F-A2, DEC-315 扩承载): quote-sync guard ──────────
# F-4: behavior-protocol.md M10.4 的触发入口引文是 SKILL.md 唯一注入面触发行的
# 规范描述（A9：SKILL 只携带指针）。引文 span MUST 与 SKILL.md 实文逐字一致；
# 任一侧单独改动即 FAIL——不建平行事实源（引文本身就是 SKILL 行的 spec）。
# F-A2: 六平台 adapter-manifest exploration_channels.note 是 M10.3 consult-draw
# 规则的转述拷贝（×6 同步债务）。每个 note MUST 携带规范标记，且规范源文件
# MUST 仍然携带该标记（双向 fail-closed）——转述/规则漂移均可机检。标记常量
# 只是 join key，不是平行事实源：规则语义只活在 M10.3（FIX-272 动态锚先例）。


def _check_quote_sync_issues():
    from exploration_evidence import _check_quote_sync_issues as run
    return run(
        package_root=ROOT, consult_draw_marker=_host_policy('CONSULT_DRAW_MARKER'),
        quote_sync_adapter_manifests=_host_policy('QUOTE_SYNC_ADAPTER_MANIFESTS'),
    )


# ── FEAT-088 (F-A3 / REVIEW-FEAT-086-DESIGN-R0 BM-1 residual): exploration-
#    channel evidence-form guard ──────────────────────────────────────────
# F-A3: the dsh exploration_channels native declarations were backed by
# live-session self-attestation ("used by the live sessions that author…")
# while claude/codex/gemini anchor their channel evidence to DATED E2E
# records. Host router drift (OAuth expiry / model decommission) never
# changes a static declaration, so the honest machine-checkable form of
# "channel liveness" is layered exactly like the ticket's honesty boundary:
#
#   layer (a) — evidence-form guard (static, FAIL-able): an adapter enrolled
#     in CHANNEL_DATE_ANCHOR_ADAPTERS MUST anchor every `native` channel
#     declaration to a date — a structured `verified_on` (YYYY-MM-DD) and/or
#     an inline date in the evidence prose (the dated-E2E convention the
#     sibling adapters already use). A dated claim is falsifiable in-repo;
#     an undated "live sessions used it" claim is not.
#   layer (b) — feasibility-limited live probes (read-only, real): when the
#     anchor carries an `evidence_ref`, the referenced document MUST exist
#     and MUST contain the anchor date — a dangling or date-less reference
#     is a broken anchor, not a verified one. Together with layer (a) this
#     is everything a CLI process can honestly check.
#   NOT probeable (physical boundary, MUST NOT be claimed): host-session
#     tool liveness — web_search / route_agent are harness-layer tools a
#     CLI process cannot invoke. Runtime drift stays governed by the
#     manifest degraded_mode + EXP-03, and by re-dating the anchor from a
#     live session. Wall-clock plausibility is likewise NOT judged (a
#     machine clock behind the repo timeline would manufacture future-date
#     FAILs): a structured date is only falsified through the evidence_ref
#     corroboration, never against the clock alone.
#
# Advisories (WARN-only, never counted toward the gate): anchor age beyond
# CHANNEL_EVIDENCE_STALE_DAYS suggests re-verification, with the EXP-03
# degradation path spelled out so the advice is the honest one. False-alarm
# protection: FAIL fires only on definite facts (missing / malformed /
# dangling / self-contradictory anchors), never on heuristics.
#: Adapters whose native channel declarations MUST carry dated anchors.
#: FEAT-088 remediates the dsh plane (F-A3); the other five enroll by
#: adopting the same anchor fields and adding their adapter_id here. Any
#: adapter that voluntarily carries anchor fields is validated meanwhile
#: (forward-compatible generalization, no retroactive FAIL on the five
#: not-yet-enrolled manifests — FEAT-088's scope guard).
#: Anchor staleness advisory threshold — aligned with the dsh host
#: contract's evidence TTL (verified_on_ttl_days = 180) rather than
#: inventing a second clock. Advisory only: staleness is age, not breakage.


def _anchor_date_or_none(value):
    from exploration_evidence import _anchor_date_or_none as run
    return run(
        value, channel_anchor_date_strict_re=_host_policy('CHANNEL_ANCHOR_DATE_STRICT_RE'),
        timestamp_type=datetime,
    )


def check_exploration_channels(root=None):
    from exploration_evidence import check_exploration_channels as run, ChannelRules
    return run(
        root, package_root=ROOT, anchor_date_or_none=_anchor_date_or_none, calendar_date=date,
        channel_rules=ChannelRules(
            dated_adapters=_host_policy('CHANNEL_DATE_ANCHOR_ADAPTERS'),
            evidence_date=_host_policy('CHANNEL_EVIDENCE_DATE_RE'),
            stale_days=_host_policy('CHANNEL_EVIDENCE_STALE_DAYS'),
            keys=_host_policy('EXPLORATION_CHANNEL_KEYS'),
            statuses=_host_policy('EXPLORATION_CHANNEL_STATUSES'),
            manifests=_host_policy('QUOTE_SYNC_ADAPTER_MANIFESTS'),
        ),
    )


# ── FIX-436 (F-B3 / DEC-317): M10.2 sample-report exploration-block ──
#    presence advisory — WARN-class, [ADVISORY]-rendered, never counted ──
# DEC-317 ruled this face OUT of FEAT-088's machine-check scope (four
# reasons: different judgment face / honest-vs-lazy omission not machine-
# distinguishable / A10 thinness / better carrier) and mandated the
# advisory (non-blocking) carrier on the check-governance host health
# surface. The thin honest form below checks ONE definite fact on
# committed exemplar docs only — every known sample report still carries
# at least one `exploration:` block (the M10.2 four-field schema's only
# committed usage examples). It deliberately does NOT judge omission
# legality (honest vs lazy stays human-review territory, DEC-317 reason
# ②) and never counts toward any gate (MUST NOT be made a blocking FAIL).


def check_exploration_sample_advisories(root=None):
    from exploration_evidence import check_exploration_sample_advisories as run
    return run(root, package_root=ROOT, exploration_sample_reports=_host_policy('EXPLORATION_SAMPLE_REPORTS'))


def check_cross_references():
    from ledger_references import check_cross_references as check
    return check(product_root=ROOT, validator_path=ROOT / "skills/software-project-governance/infra/verify_workflow.py",
                 quote_sync_issues=lambda: _check_quote_sync_issues(),
                 check_exploration_channels=lambda: check_exploration_channels())


# ── SYSGAP-009: Sequential ID Checking ────────────────────────────

def check_sequential_ids():
    from ledger_identifiers import check_sequential_ids as run
    return run(governance_dir=GOVERNANCE_DIR, data_source=_archive_reader)


def _format_id_sequence_status(prefix, ids):
    from ledger_identifiers import _format_id_sequence_status as run
    return run(prefix, ids)


def _print_sequential_id_check(si_result):
    from ledger_identifiers import _print_sequential_id_check as run
    return run(si_result)


def _scan_unicode_line_separators():
    from ledger_identifiers import _scan_unicode_line_separators as run
    return run(governance_dir=GOVERNANCE_DIR)


# ── SYSGAP-010: Structural Validity Checking ─────────────────────

def check_structural_validity():
    from ledger_identifiers import check_structural_validity as check
    return check(governance_dir=GOVERNANCE_DIR, extract_skill_version=_extract_skill_version,
                 skill_file=lambda: ROOT / "skills/software-project-governance/SKILL.md",
                 manifest_file=lambda: ROOT / "skills/software-project-governance/core/manifest.json",
                 split_markdown_table_row=_split_markdown_table_row)


# ── SYSGAP-012: Commit Scope Verification ────────────────────────

def check_commit_scope(limit=20):
    from checks.commit import check_commit_scope as run
    return run(limit, product_root=ROOT)


# ── SYSGAP-023: Goal Alignment Check ──────────────────────────────

from plan_impact import PRODUCT_CODE_PATTERNS


def _plan_hot_tracker_task_statuses():
    from plan_task_selection import _plan_hot_tracker_task_statuses as run
    return run(plan_path=SAMPLE_PATH)


def _hot_status_completion_state(status):
    from plan_task_selection import _hot_status_completion_state as run
    return run(status, status_clean_cell=_status_clean_cell,
               status_is_writer_committed_cell=_status_is_writer_committed_cell)


def _current_release_task_ids():
    from plan_task_selection import _current_release_task_ids as run
    return run(plan_path=SAMPLE_PATH, expand_task_ids=expand_task_ids)


def _normalize_priority(value):
    from plan_task_selection import _normalize_priority as run
    return run(value)


def _task_priority_from_table_parts(parts):
    from plan_task_selection import _task_priority_from_table_parts as run
    return run(parts)


def _split_governance_table_row(line):
    from plan_task_selection import _split_governance_table_row as run
    return run(line)


def _governance_table_cells(line):
    from plan_task_selection import _governance_table_cells as run
    return run(line)


def _is_incomplete_task_status(status):
    from plan_task_selection import _is_incomplete_task_status as run
    return run(status, status_is_completed_cell=_status_is_completed_cell)


def _is_nonactive_subsection(heading):
    from plan_task_selection import _is_nonactive_subsection as run
    return run(heading)


def parse_current_active_tasks():
    from plan_task_selection import parse_current_active_tasks as run
    return run(plan_path=SAMPLE_PATH)


def _active_execution_packet_tasks():
    from plan_task_selection import _active_execution_packet_tasks as run
    return run(status_is_completed_cell=_status_is_completed_cell,
               parse_current_active_tasks=lambda: parse_current_active_tasks())


def _declared_packet_checks(result, packet_path, contract=None):
    from execution_packet_checks import _declared_packet_checks as run
    return run(result, packet_path, contract, plan_path_now=lambda: SAMPLE_PATH,
               is_incomplete_task_status=lambda status: _is_incomplete_task_status(status),
               parse_current_active_tasks=lambda: parse_current_active_tasks(),
               read_document=lambda path, **options: _read_execution_packet_document(path, **options))


def parse_impact_analysis_entries():
    from plan_impact import parse_impact_analysis_entries as run
    return run(parse_impact_analysis_entries_with_exemptions=lambda: parse_impact_analysis_entries_with_exemptions())


def parse_impact_analysis_entries_with_exemptions():
    from plan_impact import parse_impact_analysis_entries_with_exemptions as run
    return run(evidence_path=EVIDENCE_PATH, current_release_task_ids=_current_release_task_ids,
               hot_status_completion_state=_hot_status_completion_state,
               plan_hot_tracker_task_statuses=_plan_hot_tracker_task_statuses,
               split_governance_table_row=_split_governance_table_row, expand_task_ids=expand_task_ids,
               requires_impact_evidence=requires_impact_evidence)


def check_goal_alignment():
    from plan_impact import check_goal_alignment as run
    return run(parse_impact_analysis_entries_with_exemptions=lambda: parse_impact_analysis_entries_with_exemptions(),
               parse_project_config=parse_project_config)


# ── SYSGAP-024: User Impact Check ────────────────────────────────

def check_user_impact():
    from plan_impact import check_user_impact as run
    return run(product_root=ROOT,
               parse_impact_analysis_entries_with_exemptions=lambda: parse_impact_analysis_entries_with_exemptions())


# ── FIX-080: Fact Grounding Check ────────────────────────────────

from checks.evidence_domain import FACT_BASIS_RE, UNGROUNDED_CLAIM_RE

def _current_release_impact_entries():
    from plan_impact import _current_release_impact_entries as run
    return run(current_release_task_ids=_current_release_task_ids,
               parse_impact_analysis_entries_with_exemptions=lambda: parse_impact_analysis_entries_with_exemptions())


# ── FIX-083: Structured Evidence Check ────────────────────────────

# ── FIX-084: AI Execution Packet Check ───────────────────────────

from contracts import EXECUTION_PACKET_REQUIRED_FIELDS


def _read_execution_packet_document(path, *, missing_ok=False):
    from execution_packet_checks import _read_execution_packet_document as run
    return run(path, missing_ok=missing_ok)


def _load_execution_packets(path=None):
    from execution_packet_checks import _load_execution_packets as run
    return run(path, packet_path_now=lambda: EXECUTION_PACKET_PATH, read_document=_read_execution_packet_document)


def _execution_packet_field_issues(packet):
    from execution_packet_checks import _execution_packet_field_issues as run
    return run(packet, required_fields=lambda: EXECUTION_PACKET_REQUIRED_FIELDS)


def _strip_markdown_bold_markers(text):
    from execution_packet_checks import _strip_markdown_bold_markers as run
    return run(text, span_pattern=_host_policy("_MARKDOWN_BOLD_SPAN_RE"))


def _is_too_broad_scope_text(text):
    from execution_packet_checks import _is_too_broad_scope_text as run
    return run(text, strip_markers=_strip_markdown_bold_markers,
               phrase_search=lambda value: _host_policy("_TOO_BROAD_SCOPE_PHRASE_RE").search(value))


def _validate_execution_packet(task, packet):
    from execution_packet_checks import _validate_execution_packet as run
    return run(task, packet, field_issues=_execution_packet_field_issues,
               broad_scope=lambda value: _is_too_broad_scope_text(value),
               placeholder_search=lambda value: _host_policy("PRODUCT_SUCCESS_PLACEHOLDER_RE").search(value))


DETERMINISTIC_SCAFFOLD_DIR = ROOT / "skills/software-project-governance/core/templates/deterministic-scaffolds"


ACCEPTANCE_CONTRACT_REQUIRED_FIELDS = {
    "scenario": str,
    "command": str,
    "expected_output": str,
    "last_run": dict,
    "demo_evidence": str,
}

ACCEPTANCE_RUNNABLE_COMMAND_RE = re.compile(
    r"^\s*(?:(?:python|pytest|node|npm|pnpm|yarn|uv|bash|sh|make|go|cargo|npx|cmd|powershell|pwsh)\b|"
    r"(?:\./|\.\\|skills/|skills\\|scripts/|scripts\\).+)",
    re.IGNORECASE,
)

ACCEPTANCE_PASS_STATUSES = {"pass", "passed", "ok", "success", "通过"}

ACCEPTANCE_NOT_RUN_STATUSES = {"not_run_yet", "not run yet", "pending", "planned", "待运行", "未运行"}

QUALITY_BUDGET_PASS_STATUSES = {"pass", "passed", "ok", "success", "通过"}

QUALITY_BUDGET_PENDING_STATUSES = {"not_run_yet", "not run yet", "pending", "planned", "待运行", "未运行"}

QUALITY_BUDGET_EXEMPT_STATUSES = {"exempt", "exception", "waived", "not_applicable", "n/a", "豁免", "不适用"}

QUALITY_BUDGET_VALIDATION_SIGNAL_RE = re.compile(
    r"(?:"
    r"python|pytest|node|npm|pnpm|yarn|uv|bash|sh|make|go|cargo|npx|cmd|powershell|pwsh|"
    r"test|check|scan|lint|audit|metric|score|coverage|threshold|budget|lighthouse|axe|"
    r"latency|p95|error rate|vulnerability|security|a11y|accessibility|maintainability|"
    r"测试|检查|扫描|指标|分数|覆盖率|阈值|预算|延迟|错误率|漏洞|安全|可访问|可维护"
    r")",
    re.IGNORECASE,
)

QUALITY_BUDGET_WEAK_PROSE_RE = re.compile(
    r"(?:"
    r"quality is okay|quality is ok|looks fine|looks good|good enough|review says|review artifact|"
    r"manual reviewer|manual review|prose|subjective|"
    r"质量还行|看起来可以|人工看看|人工审查|审查通过|主观"
    r")",
    re.IGNORECASE,
)

# FIX-475: single shared vocabulary + predicate for the Check 18f/18g
# pending allowance — no second semantic source (FIX-292 lesson). Markers
# substring-match the lowercased plan-tracker status cell, so live emoji
# forms (「📋 规划中 (…)」/「🚧 派发中 (…)」) match via the text marker.
# Terminal words (✅/完成/completed/…) must never join this whitelist;
# terminal tasks are already excluded upstream by
# _active_execution_packet_tasks -> _is_incomplete_task_status.
TASK_PENDING_STATUS_MARKERS = (
    "规划中",
    "待实施",
    "pending",
    "planned",
    "派发中",
    "进行中",
    "开发中",
    "in progress",
    "in_progress",
    "wip",
)

VERTICAL_SLICE_REQUIRED_FIELDS = (
    "user_visible_slice",
    "demo_path",
    "scope_guard",
    "rollback_plan",
    "status",
    "evidence",
)

VERTICAL_SLICE_PASS_STATUSES = {"pass", "passed", "ok", "success", "通过"}

VERTICAL_SLICE_PENDING_STATUSES = {"not_run_yet", "not run yet", "pending", "planned", "待运行", "未运行"}

VERTICAL_SLICE_DEMO_SIGNAL_RE = re.compile(
    r"(?:"
    r"\b(?:python|pytest|node|npm|pnpm|yarn|uv|bash|sh|make|go|cargo|npx|powershell|pwsh|"
    r"test|check|smoke|e2e|demo|browser|screenshot)\b|localhost|https?://|"
    r"测试|检查|冒烟|演示|截图|浏览器|验收"
    r")",
    re.IGNORECASE,
)

VERTICAL_SLICE_USER_SIGNAL_RE = re.compile(
    r"(?:user|persona|customer|operator|viewer|admin|用户|客户|使用者|操作者|可见|页面|命令输出|行为|场景)",
    re.IGNORECASE,
)

VERTICAL_SLICE_BEHAVIOR_SIGNAL_RE = re.compile(
    r"(?:\b(?:run|observe|see|click|open|use|complete|display|command output|scenario|page|form|result|pass)\b|"
    r"运行|观察|看到|点击|打开|使用|完成|显示|命令输出|场景|页面|表单|结果|通过)",
    re.IGNORECASE,
)

VERTICAL_SLICE_TECH_LAYER_RE = re.compile(
    r"(?:repository|service layer|abstraction|refactor|backend|database|schema|dao|model layer|internal|"
    r"技术层|服务层|抽象|重构|后端|数据库|数据表|内部)",
    re.IGNORECASE,
)

VERTICAL_SLICE_BROAD_SCOPE_RE = re.compile(
    r"(?:entire project|whole project|whole codebase|all files|everything|\*|全仓|整个项目|所有文件|全部重构|无边界)",
    re.IGNORECASE,
)

VERTICAL_SLICE_WEAK_PROSE_RE = re.compile(
    r"(?:review says|review artifact|manual review|looks good|looks fine|prose|subjective|审查通过|人工审查|看起来可以|主观)",
    re.IGNORECASE,
)

DETERMINISTIC_SCAFFOLD_REQUIRED_SECTIONS = (
    "## Product Success Contract",
    "## PRD-lite",
    "## Executable Acceptance",
    "## Quality Budget",
    "## Vertical Slice",
    "## Demo Checklist",
    "## Tooling",
)

DETERMINISTIC_SCAFFOLD_REQUIRED_QUALITY_DIMENSIONS = QUALITY_BUDGET_DIMENSIONS

DETERMINISTIC_SCAFFOLD_COMMAND_RE = re.compile(
    r"(?m)^\s*-\s*`(?:(?:python|pytest|node|npm|pnpm|yarn|uv|bash|sh|make|go|cargo|npx|powershell|pwsh)\b|"
    r"(?:\./|\.\\|skills/|skills\\|scripts/|scripts\\).+)",
    re.IGNORECASE,
)

DETERMINISTIC_SCAFFOLD_SIGNAL_RE = re.compile(
    r"(?:persona|jtbd|job to be done|non-goal|success metric|acceptance|quality budget|demo checklist|"
    r"vertical slice|rollback|PRD-lite|用户|验收|质量预算|演示|切片)",
    re.IGNORECASE,
)

DETERMINISTIC_SCAFFOLD_WEAK_RE = re.compile(
    r"(?:review says|review passed|reviewer approved|approved.*prose|looks good|manual review only|"
    r"ship it|whatever|\bTODO\b|\bTBD\b|\bTO_BE_DEFINED\b|待补|待定|占位)",
    re.IGNORECASE,
)

DETERMINISTIC_SCAFFOLD_BROAD_SCOPE_RE = re.compile(
    r"(?:entire repository|whole repository|whole repo|full repo|entire repo|"
    r"entire project|whole project|whole codebase|all files|everything|\*|全仓|整个项目|所有文件|全部重构|无边界)",
    re.IGNORECASE,
)

DETERMINISTIC_SCAFFOLD_SECTION_SIGNALS = {
    "## Product Success Contract": (
        r"(?:persona|用户|使用者)",
        r"(?:jtbd|job to be done|desired outcome|用户任务)",
        r"(?:non-goal|out of scope|非目标)",
        r"(?:success metric|metric|成功指标)",
    ),
    "## PRD-lite": (
        r"(?:problem|问题)",
        r"(?:workflow|scenario|user-visible|用户可见|流程|场景)",
    ),
    "## Executable Acceptance": (
        r"(?:expected output|exit code|pass|通过|预期输出)",
        r"(?:demo evidence|evidence|artifact|证据)",
    ),
    "## Quality Budget": tuple(DETERMINISTIC_SCAFFOLD_REQUIRED_QUALITY_DIMENSIONS),
    "## Vertical Slice": (
        r"(?:user-visible slice|user can|用户可见|用户)",
        r"(?:demo path|demo|smoke|command|演示)",
        r"(?:scope guard|scope|范围)",
        r"(?:rollback|回滚)",
    ),
    "## Demo Checklist": (
        r"(?:command|demo|evidence|exit code|artifact|演示|证据)",
        r"(?:expected|visible|invalid|failure|result|预期|结果)",
    ),
    "## Tooling": (
        r"(?:check-product-success-contracts|check-acceptance-contracts|check-quality-budget|check-vertical-slices|check-deterministic-scaffolds)",
    ),
}

INTERRUPTION_POLICY_REQUIRED_PHRASES = (
    "User Interruption Policy v2",
    "critical-only",
    "product intent",
    "acceptance standard",
    "irreversible",
    "record_assumption",
    "interruption_budget",
)

INTERRUPTION_POLICY_REQUIRED_TEMPLATE_PHRASES = (
    "interruption_policy:",
    "critical_triggers:",
    "auto_execute:",
    "assumption_record:",
    "interruption_budget:",
)

INTERRUPTION_POLICY_REQUIRED_ASSUMPTION_FIELDS = (
    "assumption",
    "basis",
    "reversibility",
    "validation",
    "rollback",
)

INTERRUPTION_POLICY_PLACEHOLDER_RE = re.compile(
    r"(?:\b(?:todo|tbd|to_be_defined|n/?a|none|null|unknown)\b|待补|待定|暂无|占位)",
    re.IGNORECASE,
)

INTERRUPTION_POLICY_CRITICAL_TRIGGER_KEYS = (
    "product_intent_unclear",
    "acceptance_standard_unclear",
    "irreversible",
    "risk_acceptance",
    "release_decision",
    "external_dependency",
    "mode_change",
)

INTERRUPTION_POLICY_PACKET_CRITICAL_SIGNALS = (
    "product intent",
    "acceptance",
    "irreversible",
    "release",
    "risk acceptance",
    "external dependency",
    "mode change",
)

INTERRUPTION_POLICY_DEFAULT_EXAMPLES = [
    {
        "id": "product-intent-ambiguity",
        "expected_action": "ask_user",
        "decision": {"product_intent_unclear": True, "reversible": True},
    },
    {
        "id": "acceptance-standard-ambiguity",
        "expected_action": "ask_user",
        "decision": {"acceptance_standard_unclear": True, "reversible": True},
    },
    {
        "id": "irreversible-file-delete",
        "expected_action": "ask_user",
        "decision": {"irreversible": True, "destructive": True},
    },
    {
        "id": "risk-acceptance",
        "expected_action": "ask_user",
        "decision": {"risk_acceptance": True, "reversible": False},
    },
    {
        "id": "release-go-no-go",
        "expected_action": "ask_user",
        "decision": {"release_decision": True, "reversible": False},
    },
    {
        "id": "new-external-dependency",
        "expected_action": "ask_user",
        "decision": {"external_dependency": True, "reversible": True},
    },
    {
        "id": "mode-change",
        "expected_action": "ask_user",
        "decision": {"mode_change": True, "reversible": True},
    },
    {
        "id": "routine-file-edit",
        "expected_action": "auto_execute",
        "decision": {"routine_execution": True, "reversible": True, "known_scope": True},
    },
    {
        "id": "local-validation",
        "expected_action": "auto_execute",
        "decision": {"local_validation": True, "reversible": True, "known_scope": True},
    },
    {
        "id": "governance-record-update",
        "expected_action": "auto_execute",
        "decision": {"governance_record_update": True, "reversible": True, "known_scope": True},
    },
    {
        "id": "normal-commit-push",
        "expected_action": "auto_execute",
        "decision": {"commit_push": True, "reversible": True, "known_scope": True},
    },
    {
        "id": "reversible-default-assumption",
        "expected_action": "record_assumption",
        "decision": {
            "routine_execution": True,
            "reversible": True,
            "known_scope": False,
            "assumption_record": {
                "assumption": "Use existing repository style for naming and structure.",
                "basis": "Nearby files show the prevailing pattern.",
                "reversibility": "Can be renamed or reverted in one focused commit.",
                "validation": "Run the focused test or checker after the edit.",
                "rollback": "Revert the focused change if validation fails.",
            },
        },
    },
]


def _product_success_policy():
    from delivery_contract_checks import ProductSuccessPolicy
    return ProductSuccessPolicy(
        required_fields=_host_policy("PRODUCT_SUCCESS_CONTRACT_REQUIRED_FIELDS"),
        placeholder=_host_policy("PRODUCT_SUCCESS_PLACEHOLDER_RE"),
        process_only_metric=_is_process_only_product_success_metric,
        user_outcome=_host_policy("PRODUCT_SUCCESS_USER_OUTCOME_RE"),
        runnable=_host_policy("PRODUCT_SUCCESS_RUNNABLE_RE"),
    )


def _acceptance_policy():
    from delivery_contract_checks import AcceptancePolicy
    return AcceptancePolicy(
        required_fields=ACCEPTANCE_CONTRACT_REQUIRED_FIELDS,
        runnable_command=ACCEPTANCE_RUNNABLE_COMMAND_RE,
        pass_statuses=ACCEPTANCE_PASS_STATUSES,
        not_run_statuses=ACCEPTANCE_NOT_RUN_STATUSES,
        placeholder=_host_policy("PRODUCT_SUCCESS_PLACEHOLDER_RE"),
    )


def _quality_budget_policy():
    from delivery_contract_checks import QualityBudgetPolicy
    return QualityBudgetPolicy(
        dimensions=QUALITY_BUDGET_DIMENSIONS,
        pass_statuses=QUALITY_BUDGET_PASS_STATUSES,
        pending_statuses=QUALITY_BUDGET_PENDING_STATUSES,
        exempt_statuses=QUALITY_BUDGET_EXEMPT_STATUSES,
        validation_signal=QUALITY_BUDGET_VALIDATION_SIGNAL_RE,
        weak_prose=QUALITY_BUDGET_WEAK_PROSE_RE,
        placeholder=_host_policy("PRODUCT_SUCCESS_PLACEHOLDER_RE"),
        pending_task=_is_task_pending_status_allowed,
    )


def _vertical_slice_policy():
    from delivery_contract_checks import VerticalSlicePolicy
    return VerticalSlicePolicy(
        required_fields=VERTICAL_SLICE_REQUIRED_FIELDS,
        pass_statuses=VERTICAL_SLICE_PASS_STATUSES,
        pending_statuses=VERTICAL_SLICE_PENDING_STATUSES,
        demo_signal=VERTICAL_SLICE_DEMO_SIGNAL_RE,
        user_signal=VERTICAL_SLICE_USER_SIGNAL_RE,
        behavior_signal=VERTICAL_SLICE_BEHAVIOR_SIGNAL_RE,
        tech_layer=VERTICAL_SLICE_TECH_LAYER_RE,
        broad_scope=VERTICAL_SLICE_BROAD_SCOPE_RE,
        weak_prose=VERTICAL_SLICE_WEAK_PROSE_RE,
        weak_quality_prose=QUALITY_BUDGET_WEAK_PROSE_RE,
        placeholder=_host_policy("PRODUCT_SUCCESS_PLACEHOLDER_RE"),
        pending_task=_is_task_pending_status_allowed,
    )


def _scaffold_policy():
    from scaffold_contracts import ScaffoldPolicy
    return ScaffoldPolicy(
        types=DETERMINISTIC_SCAFFOLD_TYPES,
        sections=DETERMINISTIC_SCAFFOLD_REQUIRED_SECTIONS,
        quality_dimensions=DETERMINISTIC_SCAFFOLD_REQUIRED_QUALITY_DIMENSIONS,
        command=DETERMINISTIC_SCAFFOLD_COMMAND_RE,
        signal=DETERMINISTIC_SCAFFOLD_SIGNAL_RE,
        weak=DETERMINISTIC_SCAFFOLD_WEAK_RE,
        broad_scope=DETERMINISTIC_SCAFFOLD_BROAD_SCOPE_RE,
        section_signals=DETERMINISTIC_SCAFFOLD_SECTION_SIGNALS,
    )


def _interruption_policy():
    from interruption_contracts import InterruptionPolicy
    return InterruptionPolicy(
        required_phrases=INTERRUPTION_POLICY_REQUIRED_PHRASES,
        template_phrases=INTERRUPTION_POLICY_REQUIRED_TEMPLATE_PHRASES,
        assumption_fields=INTERRUPTION_POLICY_REQUIRED_ASSUMPTION_FIELDS,
        placeholder=INTERRUPTION_POLICY_PLACEHOLDER_RE,
        critical_keys=INTERRUPTION_POLICY_CRITICAL_TRIGGER_KEYS,
        packet_signals=INTERRUPTION_POLICY_PACKET_CRITICAL_SIGNALS,
        examples=INTERRUPTION_POLICY_DEFAULT_EXAMPLES,
    )


def _is_process_only_product_success_metric(value):
    from delivery_contract_checks import _is_process_only_product_success_metric as judge
    return judge(value, _host_policy("PRODUCT_SUCCESS_PROCESS_ONLY_RE"))


def _is_task_pending_status_allowed(task):
    from delivery_contract_checks import _is_task_pending_status_allowed as judge
    return judge(task, TASK_PENDING_STATUS_MARKERS)


def _validate_product_success_contract(packet):
    from delivery_contract_checks import _validate_product_success_contract as validate
    return validate(packet, _product_success_policy())


def _validate_acceptance_contract(task, packet):
    from delivery_contract_checks import _validate_acceptance_contract as validate
    return validate(task, packet, _acceptance_policy())


def _validate_quality_budget(task, packet):
    from delivery_contract_checks import _validate_quality_budget as validate
    return validate(task, packet, _quality_budget_policy())


def _validate_vertical_slice(task, packet):
    from delivery_contract_checks import _validate_vertical_slice as validate
    return validate(task, packet, _vertical_slice_policy())


def check_product_success_contracts(packet_path=None):
    from delivery_contract_checks import check_declared_contracts
    return check_declared_contracts(
        "product_success_contract", packet_path, _declared_packet_checks,
        lambda task, packet: _validate_product_success_contract(packet),
    )


def check_acceptance_contracts(packet_path=None):
    from delivery_contract_checks import check_declared_contracts
    return check_declared_contracts(
        "acceptance_contract", packet_path, _declared_packet_checks,
        _validate_acceptance_contract,
    )


def check_quality_budget(packet_path=None):
    from delivery_contract_checks import check_declared_contracts
    return check_declared_contracts(
        "quality_budget", packet_path, _declared_packet_checks,
        _validate_quality_budget,
    )


def check_vertical_slices(packet_path=None):
    from delivery_contract_checks import check_declared_contracts
    return check_declared_contracts(
        "vertical_slice", packet_path, _declared_packet_checks,
        _validate_vertical_slice,
    )


def render_deterministic_scaffold(scaffold_type, scaffold_dir=None):
    from scaffold_contracts import render_deterministic_scaffold as render
    return render(scaffold_type, scaffold_dir, DETERMINISTIC_SCAFFOLD_TYPES, default_dir=DETERMINISTIC_SCAFFOLD_DIR)


def check_deterministic_scaffolds(scaffold_dir=None):
    from scaffold_contracts import check_deterministic_scaffolds as check
    return check(scaffold_dir, _scaffold_policy(), default_dir=DETERMINISTIC_SCAFFOLD_DIR)


def classify_user_interruption(decision):
    from interruption_contracts import classify_user_interruption as classify
    return classify(decision, INTERRUPTION_POLICY_CRITICAL_TRIGGER_KEYS)


def _validate_interruption_policy_examples(examples):
    from interruption_contracts import _validate_interruption_policy_examples as validate
    return validate(examples, _interruption_policy(), classify_user_interruption)


def check_interruption_policy(interaction_boundary_path=None, template_path=None, packet_path=None, examples=None):
    from interruption_contracts import check_interruption_policy as check
    return check(
        INTERACTION_BOUNDARY_PATH if interaction_boundary_path is None else Path(interaction_boundary_path),
        USER_INTERRUPTION_POLICY_TEMPLATE_PATH if template_path is None else Path(template_path),
        packet_path, examples, _declared_packet_checks, _interruption_policy(),
        classify_user_interruption, _validate_interruption_policy_examples,
    )


def build_execution_packet(task, **options):
    from execution_packet import build_execution_packet as build
    return build(task, **options)


def generate_execution_packets(existing=None, *, task_ids=None, governance_dir=None, contracts=(), quality_dimensions=()):
    from execution_packet_checks import generate_execution_packets as run
    return run(existing, task_ids=task_ids, governance_dir=governance_dir, contracts=contracts,
               quality_dimensions=quality_dimensions, plan_path_now=lambda: SAMPLE_PATH,
               active_execution_packet_tasks=lambda: _active_execution_packet_tasks(),
               is_incomplete_task_status=_is_incomplete_task_status,
               packet_builder=lambda: build_execution_packet,
               parse_current_active_tasks=lambda: parse_current_active_tasks())



def check_execution_packets(packet_path=None):
    from execution_packet_checks import check_execution_packets as run
    return run(packet_path, declared_packet_checks=_declared_packet_checks,
               validate_packet=lambda task, packet: _validate_execution_packet(task, packet))


def cmd_execution_packet(args):
    from governance_fact_cli import cmd_execution_packet as run
    return run(args, packet_path_now=lambda: EXECUTION_PACKET_PATH,
               read_execution_packet_document=lambda path, **options: _read_execution_packet_document(path, **options),
               generate_execution_packets=lambda **options: generate_execution_packets(**options))


# ── SYSGAP-036: Agent Activation Check (Check 20) ────────────────

def check_agent_activation():
    from team_activation import check_agent_activation as run
    return run(
        evidence_path=EVIDENCE_PATH, plan_path=SAMPLE_PATH,
        split_governance_table_row=_split_governance_table_row, expand_task_ids=expand_task_ids,
    )


# ── FIX-038: Profile Consistency Check (Check 23) ──────────────────

def check_profile_consistency():
    from team_activation import check_profile_consistency as run
    return run(plan_path=SAMPLE_PATH)
def _evidence_task_type_index():
    """FIX-174 R1 (P0-3): map task_id -> joined type+description text scanned
    from the evidence-log, so _task_routing_exempt can heuristically infer a
    task's type when the plan-tracker has no type column.

    Only work-delivery rows (evd_id starting with EVD-) contribute. We
    deliberately skip REVIEW-* rows: a REVIEW-{id} row's type cell carries the
    *reviewer's* activity label (e.g. "代码审查"), not the task's own type, so
    including it would mis-classify every reviewed task as a review-type task.

    Returns dict task_id -> str (the concatenation of the row's type cell and
    description cell, lowercased). Best-effort: returns {} on read failure.
    """
    index = {}
    if not EVIDENCE_PATH.is_file():
        return index
    try:
        content = EVIDENCE_PATH.read_text(encoding="utf-8")
    except (IOError, OSError):
        return index
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        parts = [p.strip() for p in stripped.split("|")]
        if len(parts) < 6:
            continue
        evd_id = parts[1]
        # Skip review-evidence rows — their type cell is the reviewer activity,
        # not the task's own type (see docstring).
        if evd_id.upper().startswith("REVIEW-"):
            continue
        raw_ids = parts[2]
        type_cell = parts[3] if len(parts) > 3 else ""
        desc_cell = parts[4] if len(parts) > 4 else ""
        for tid in re.findall(r"[A-Z]+-\d+", raw_ids):
            blob = f"{type_cell} {desc_cell}".strip().lower()
            if blob:
                index.setdefault(tid, "")
                if blob not in index[tid]:
                    index[tid] = (index[tid] + " " + blob).strip()
    return index


# Legacy entry points bind the host paths and collaborators used by Check 36.
def _archive_corpus_files():
    return risk_domain.archive_corpus_files(SAMPLE_PATH.parent)


def _resolve_archive_task_refs(task_ids):
    return risk_domain.resolve_archive_task_refs(
        task_ids, _archive_corpus_files,
        lambda path: _display_path(path, SAMPLE_PATH.parent.parent).as_posix())


def check_risk_mitigation_closure_with_archive(risk_content=None, task_status_map=None):
    """Run the archive-aware risk check with the current host configuration."""
    if task_status_map is None:
        task_status_map = _default_task_status_map()
    return risk_domain.check_risk_mitigation_closure_with_archive(
        risk_content, task_status_map, check=check_risk_mitigation_closure,
        resolve_refs=_resolve_archive_task_refs)


# ── Check 10 M5 record-doc scope whitelist (FIX-295 / AUDIT-149 N6) ──
# docs/release/** and docs/reviews/** are RECORD-class governance text —
# release-queue adjudication tables and review reports that DESCRIBE past
# events. Their ASCII "(a)/(b)/(c)" verification sub-clauses plus nearby
# "选项/选择" vocabulary (e.g. "可选项") are factual citations, not agent
# runtime instructions, but the Check 10 anti-pattern heuristic
# (m5_option_list_no_auq: option list + choice context, no AskUserQuestion)
# cannot tell a recorded list from an instructed menu, so it structurally
# false-positives on them. Two live instances (AUDIT-149 §3 域 6 / §4 N6):
#   - docs/release/queue-triage-0.78x.md:66 (queue task row citing 3 path-
#     traversal test-case paths; "(a)/(b)/(c)" rationale sub-clauses)
#   - docs/reviews/review-REL-074-RELEASE-R2.md:17 (R1-finding verification
#     row; "(a)~(e)" mapping sub-clauses + "选项")
# Same record-vs-runtime distinction as Check 29's session-snapshot
# auto-discovery exclusion (FIX-178; AUDIT-149 cites this precedent family
# as the "FIX-280 先例").
#
# FIX-348 extends the whitelist with docs/requirements/**: delivered design
# documents (docs/requirements/*-design-*.md) are the same record class —
# their "(a)/(b)" adjudication rows RECORD past disposition options plus a
# recommendation left for the DEC record, not agent runtime instructions,
# and m5_option_list_no_auq structurally false-positives on them the same
# way (live instance: docs/requirements/dsh-compat-design-0.81.0.md:292,
# the R1-expiry adjudication row). Same record-vs-runtime distinction, same
# PATH-CLASSIFICATION-only boundary; docs/requirements design docs being
# scanned-or-not does not change any other check's fact sourcing (the
# docs/requirements paths consumed by Checks 1x/2x are read directly, not
# routed through the M5 whitelist).
#
# Implementation: WRAPPER, not a base-scan edit — the FIX-294 precedent for
# a scope held to verify_workflow.py + tests. The base
# checks.review_domain.check_m5_compliance() stays byte-identical (scan
# list + FIX-054 plugin-scope filter untouched); only the Check 10 gate
# call site swaps to check_m5_compliance_with_record_scope(), which moves
# issues whose file lives under a record-class directory enumerated in
# M5_RECORD_DOC_DIRS into a disclosed exemption list (not counted).
#
# Fail-closed boundaries:
#   - PATH CLASSIFICATION ONLY — explicit directory whitelist; directory-
#     component match (exact dir or dir + "/"), never a bare string prefix
#     ("docs/release-notes.md" is NOT exempt) and never content heuristics.
#   - Everything else the base scans keeps FULL coverage: AGENTS.md,
#     CLAUDE.md, .governance/CLAUDE.md, and every docs/ subtree OUTSIDE the
#     whitelist (FIX-348 moved docs/requirements/** INTO the whitelist as
#     record-class design docs; every other docs/ subtree — e.g.
#     docs/other/** — stays scanned, and lookalike non-directory paths like
#     "docs/requirements-notes.md" never match) — plus the M5 structural
#     checks (bootstrap template / interaction-boundary / SELF-CHECK guard),
#     whose issue files can never match the whitelist.
#   - Exempt ≠ silent: every dropped issue is returned in
#     record_scope_exempted and printed as [EXEMPT] (DEC-151-style
#     disclosure, not counted into all_issues).

M5_RECORD_DOC_DIRS = ("docs/release", "docs/reviews", "docs/requirements")


def _is_m5_record_doc_path(rel_path):
    """FIX-295: True when rel_path is inside an M5 record-class doc dir.

    Directory-component whitelist match over M5_RECORD_DOC_DIRS: an entry
    must equal the path or be a leading directory component — "docs/release"
    matches "docs/release/x.md" and "docs/release/a/b.md" but NOT
    "docs/release-notes.md" or "docs/other/release/x.md". Backslashes are
    normalized. Fail-closed: anything not explicitly enumerated stays
    scanned.
    """
    rp = str(rel_path).replace("\\", "/")
    for record_dir in M5_RECORD_DOC_DIRS:
        if rp == record_dir or rp.startswith(record_dir + "/"):
            return True
    return False


def check_m5_compliance_with_record_scope():
    """FIX-295 / AUDIT-149 N6: Check 10 gate entry with record-doc scope.

    Thin wrapper over the UNCHANGED base ``check_m5_compliance()`` (FIX-294
    wrapper pattern): pass 1 runs the base scan byte-for-byte; issues whose
    ``file`` is under an M5_RECORD_DOC_DIRS directory (record-class text —
    release/review documents and delivered design docs; see the module
    comment above) are moved to
    ``record_scope_exempted`` (disclosed, never counted); every other issue
    — entry files, non-whitelisted docs/ subtrees, and all M5 structural
    checks — passes through untouched.

    Returns the base result dict extended with:
      ``record_scope_exempted``: list of exempted issue dicts
      ``record_scope_dirs``: the whitelist tuple (for disclosure)
    Never raises; never broadens or narrows the base scan itself.
    """
    base = check_m5_compliance()
    kept = []
    exempted = []
    for issue in base.get("issues", []):
        if _is_m5_record_doc_path(str(issue.get("file", ""))):
            exempted.append(issue)
        else:
            kept.append(issue)
    base["issues"] = kept
    base["record_scope_exempted"] = exempted
    base["record_scope_dirs"] = M5_RECORD_DOC_DIRS
    return base


def check_decision_premise(governance_dir=None):
    """FIX-463 — collapsed decision-premise verdict (Check 2b core).

    Returns ``{"declarations": {dec_id: premise}, "collapsed": [dec_id],
    "detail": {dec_id: {...}}}``. Registered as the R5 segment-2b loader
    (the segment registry's SegmentSpec table); read-only over
    decision-log.md + premise-events.jsonl, never raises on missing
    inputs (idle face when no premises are declared).
    """
    gov = Path(governance_dir) if governance_dir else GOVERNANCE_DIR
    decision_log = gov / "decision-log.md"
    declarations = premise_tracker.collect_premise_declarations(
        decision_log.read_text(encoding="utf-8")
        if decision_log.is_file() else "")
    events = premise_tracker.load_events(gov)
    status = premise_tracker.premise_status(declarations, events)
    return {"declarations": declarations, **status}


def cmd_check_governance(args):
    """Run governance health checks: evidence completeness, risk staleness, gate consistency.

    REQ-145.7/FIX-278 G1: with ``--summary-only``, the full engine is run under
    a stdout capture and only the ``Governance: {N} issues`` summary (+ first
    FAIL/WARN, plus --level standard's top-5 bounded detail lines and the
    ``共 N issues，--level strict 查看全部`` guidance — lightweight=summary+
    first FAIL; strict=all FAIL/WARN) is printed. The default (no
    ``--summary-only``) path is byte-identical to the pre-existing output —
    the engine body lives in ``_run_full_engine_checks``.

    FEAT-084 (DEC-303 form B): ``--scope quick|full`` declares the execution
    scope — quick normalizes onto the FEAT-026 wiring (four-state line); the
    default / ``--scope full`` stay byte-identical (full-caliber N for release
    gates, census baselines and golden samples — the caliber split is caller
    declared, never silent).
    """
    # Ensure UTF-8 stdout to handle Chinese characters from .md files (Windows GBK workaround)
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    # FEAT-084: scope quick ⇒ the quick face (FEAT-026 wiring below owns
    # selection + four-state rendering + FIX-304 fail-closed fallback).
    if getattr(args, "scope", "full") == "quick":
        setattr(args, "quick", True)

    if getattr(args, "quick", False) or getattr(args, "shadow", False):
        # FEAT-026 Slice-2 wiring: the selector owns the four-state contract and
        # the S-A/S-B shadow channel; the engine only provides the run + capture.
        from quickscan_selector import run_quick_checks
        all_issues, output = run_quick_checks(args, _run_full_engine_checks)
        print(output, end="")
    elif getattr(args, "summary_only", False):
        buf = io.StringIO()
        with redirect_stdout(buf):
            all_issues = _run_full_engine_checks(args)
        summary = _aggregate_check_summary(buf.getvalue())
        _print_check_summary(summary, args)
    else:
        all_issues = _run_full_engine_checks(args)

    if getattr(args, "fail_on_issues", False) and all_issues > 0:
        sys.exit(1)


# ── FIX-270 交付 B: 检查事实源根目录声明（product-gate 切分）─────────────
# 判定标准：以「检查事实源根」切分——每个检查的事实要么来自插件包本体
# （manifest / 交叉引用 / 插件 git / ArchGuard 树扫描 / 投影 fixtures /
# 注入锚点 / 插件版本资产 / loop-claim 扫描 / identity attestation），要么
# 来自宿主项目（.governance/ 热文件 + 宿主 git）。事实源 = 插件包本体的
# 检查（PLUGIN_PRODUCT）在宿主模式（HOST_PROJECT_ROOT 与 PLUGIN_ROOT 不同）
# 默认跳过，经 ``--product-gates`` 显式开启；dogfood（roots 相同）默认保留
# 全部。新增检查只需在目录中登记一行（先声明事实源，再决定归属），
# 不得在引擎代码里硬编码编号黑名单。
_PLUGIN_PRODUCT_CHECK_IDS = frozenset({
    # 插件 git 作为事实源（-C ROOT 而非宿主仓库）
    "Check 7",    # Commit-Task Traceability
    "Check 15",   # Commit Scope Verification
    # 插件包本体文件作为事实源
    "Check 10",   # M5 AskUserQuestion Compliance（插件 source 扫描）
    "Check 11",   # Manifest Consistency
    "Check 12",   # Cross-Reference Checking
    "Check 24",   # Version Consistency（插件版本资产）
    "Check 28b",  # Projection Sync Guard（source/fixtures/native entries）
    "Check 28d",  # Runtime Readiness Matrix（插件 docs）
    "Check 28e",  # First-Session Measurement（插件 docs）
    "Check 28f",  # Governance Pack Registry（插件 core JSON）
    "Check 28h",  # README Pack Guidance
    "Check 28i",  # Governance Pack Status Boundary
    "Check 28k",  # Capability Registry（插件 core JSON）
    "Check 28n",  # Mainstream Agent Loading（插件 docs）
    # ArchGuard 插件树扫描
    "Check 28o",  # Architecture Health
    "Check 28p",  # Duplicate Code
    "Check 28q",  # Technical Debt
    "Check 28r",  # Complexity
    "Check 28t",  # README Claim→Evidence Levels（插件包本体 README）
    "Check 28u",  # DSH Preset Session Smoke（插件包本体 launch.py + presets/）
    "Check 28v",  # DSH Preset Schema Compat（插件 presets/ + adapters/dsh 组合 ↔ 安装态 dsh schema）
    "Check 28w",  # DSH Dependency Boundary（契约 K-1~K-13：模板/令牌/hooks/patch/证据/覆盖/演练基线）
    "Check 30b",  # Loop wiring call sites（插件 infra AST 扫描）
    "Check 33",   # Injection Contract（插件 persona/SKILL/AGENTS 锚点）
})


def _host_plugin_roots_divergent():
    """True when the host project root differs from the plugin package root.

    FIX-270 mixed-root watchdog: every check's fact-source root must equal the
    project it is governed against. When the roots diverge (host scenario),
    plugin-package-rooted checks are product self-checks and are skipped by
    default (--product-gates re-enables); when they coincide (dogfood) all
    checks run.
    """
    try:
        host = os.path.normcase(os.path.abspath(os.fspath(HOST_PROJECT_ROOT)))
        plugin = os.path.normcase(os.path.abspath(os.fspath(PLUGIN_ROOT)))
        return host != plugin
    except Exception:
        return False


def _product_gate_active(args):
    """Whether PLUGIN_PRODUCT checks run in this invocation.

    dogfood（host==plugin）→ always; host mode → only with ``--product-gates``;
    ``--quick``（FX-195 Slice-2）→ never: the quick face is *defined* by the
    FEAT-025 registry as "everything except the not-quick exclusion set", and
    that exclusion set is machine-checked equal to this very product-gate set
    (the registry side asserts the identity), so quick reuses the existing
    ``[SKIP]`` machinery instead of introducing a second, parallel selection
    path in the monolith (§255 carrier discipline).
    """
    if getattr(args, "quick", False):
        return False
    if not _host_plugin_roots_divergent():
        return True
    return bool(getattr(args, "product_gates", False))


_PRODUCT_GATE_LABELS = {
    "Check 7": "Commit-Task Traceability",
    "Check 10": "M5 AskUserQuestion Compliance",
    "Check 11": "Manifest Consistency",
    "Check 12": "Cross-Reference Checking",
    "Check 15": "Commit Scope Verification",
    "Check 24": "Version Consistency",
    "Check 28b": "Projection Sync Guard",
    "Check 28d": "Runtime Readiness Matrix Guard",
    "Check 28e": "First-Session Measurement Guard",
    "Check 28f": "Governance Pack Registry",
    "Check 28h": "README Pack Guidance",
    "Check 28i": "Governance Pack Status Boundary",
    "Check 28k": "Capability Registry",
    "Check 28n": "Mainstream Agent Loading",
    "Check 28o": "Architecture Health (ArchGuard/REQ-101)",
    "Check 28p": "Duplicate Code (ArchGuard/REQ-101)",
    "Check 28q": "Technical Debt (ArchGuard/REQ-101)",
    "Check 28r": "Complexity (ArchGuard/REQ-101)",
    "Check 28t": "README Claim→Evidence Levels (FEAT-014)",
    "Check 28u": "DSH Preset Session Smoke (FEAT-015)",
    "Check 28v": "DSH Preset Schema Compat",
    "Check 28w": "DSH Dependency Boundary (FEAT-031)",
    "Check 30b": "Loop wiring call sites",
    "Check 33": "Injection Contract",
}


def _print_product_gate_skipped(check_id):
    """Print the standard SKIP banner for a plugin-product check in host mode."""
    label = _PRODUCT_GATE_LABELS.get(check_id, "")
    title = f"{check_id}: {label}" if label else check_id
    print(f"\n┌─ {title} {'─' * max(1, 60 - len(title))}┐")
    print("│  [SKIP] product self-check — plugin-package fact source; "
          "host/plugin roots diverge. Run with --product-gates to enable.")
    print("└──────────────────────────────────────────────────────┘")


def _full_check_results(args):
    """Bind each report to its current checks only when the full scan reaches it."""
    import health_governance_sections as governance
    import health_delivery_sections as delivery
    import health_review_sections as review
    import health_product_sections as product

    def product_gate_active():
        return _product_gate_active(args)

    yield governance.section_1_evidence_completeness(
        emit_evidence_completeness, check_evidence_completeness,
    )
    yield governance.section_2_risk_staleness(emit_risk_staleness, check_risk_staleness)
    yield governance.section_2b_decision_premises(check_decision_premise)
    yield governance.section_3_gate_consistency(check_gate_consistency)
    yield governance.section_4_evidence_quality(emit_evidence_quality, check_evidence_quality)
    yield governance.section_5_protocol_compliance(check_protocol_compliance)
    yield governance.section_6_tier_audits(check_tier_audit_completeness)
    yield product.section_7_commit_traceability(
        product_gate_active, check_commit_task_references,
        _print_product_gate_skipped,
    )
    yield governance.section_8_risk_escalation(emit_risk_escalation, check_risk_escalation)
    yield governance.section_9_task_deadlines(check_task_deadline)
    yield review.section_10_user_questions(
        product_gate_active, check_m5_compliance_with_record_scope,
        _print_product_gate_skipped,
    )
    yield product.section_11_manifest(
        product_gate_active, check_manifest_consistency, _print_product_gate_skipped,
    )
    yield governance.section_12_cross_references(
        product_gate_active, check_cross_references,
        check_exploration_sample_advisories, _print_product_gate_skipped,
    )
    yield governance.section_13_sequential_ids(check_sequential_ids, _print_sequential_id_check)
    yield governance.section_14_structural_validity(
        check_structural_validity, blocking_structural_issues,
    )
    yield product.section_15_commit_scope(
        product_gate_active, check_commit_scope, _print_product_gate_skipped,
    )
    yield delivery.section_16_goal_alignment(check_goal_alignment)
    yield delivery.section_17_user_impact(check_user_impact)
    yield delivery.section_18_fact_grounding(check_fact_grounding)
    yield delivery.section_18b_structured_evidence(check_structured_evidence)
    yield delivery.section_18c_execution_packets(check_execution_packets)
    yield delivery.section_18d_product_outcomes(
        check_product_success_contracts, render_rb2_goal_contract_block,
    )
    yield delivery.section_18e_acceptance(check_acceptance_contracts)
    yield delivery.section_18f_quality_budget(check_quality_budget)
    yield delivery.section_18g_vertical_slices(check_vertical_slices)
    yield delivery.section_18h_scaffolds(check_deterministic_scaffolds)
    yield delivery.section_18i_interruption_policy(check_interruption_policy)
    yield review.section_19_team_review(check_agent_team_review)
    yield review.section_20_agent_activation(check_agent_activation)
    yield review.section_21_review_debt(check_review_debt, DEGRADED_FUSE_THRESHOLD)
    yield review.section_22_review_coverage(check_review_coverage)
    yield review.section_23_profile(check_profile_consistency)
    yield product.section_24_version(
        product_gate_active, check_version_consistency, _print_product_gate_skipped,
    )
    yield governance.section_25_untracked_files(check_untracked_files)
    yield governance.section_26_locks(check_agent_lock_consistency, lock_issue_is_blocking)
    yield governance.section_27_archives(check_archive_integrity)
    yield review.section_28_review_fallback(check_governance_review_fallback_policy)
    yield product.section_28b_projection_sync(
        product_gate_active, check_projection_sync, _print_product_gate_skipped,
    )
    yield governance.section_28c_hot_facts(
        check_hot_fact_source_consistency, _host_plugin_roots_divergent,
    )
    yield product.section_28d_runtime_matrix(
        product_gate_active, check_runtime_readiness_matrix,
        _print_product_gate_skipped,
    )
    yield product.section_28e_first_session(
        product_gate_active, check_first_session_measurement,
        _print_product_gate_skipped,
    )
    yield product.section_28f_governance_packs(
        product_gate_active, check_governance_packs, _print_product_gate_skipped,
    )
    yield governance.section_28g_governance_context(check_governance_context)
    yield product.section_28h_readme_guidance(
        product_gate_active, check_readme_pack_guidance, _print_product_gate_skipped,
    )
    yield product.section_28i_pack_status(
        product_gate_active, check_governance_pack_status,
        _print_product_gate_skipped,
    )
    yield product.section_28j_capability_context(check_capability_context)
    yield product.section_28k_capability_registry(
        product_gate_active, check_capability_registry, _print_product_gate_skipped,
    )
    yield product.section_28l_host_capabilities(check_host_capability_context)
    yield product.section_28n_agent_loading(
        product_gate_active, check_mainstream_agent_loading,
        _print_product_gate_skipped,
    )
    yield product.section_28o_architecture_health(
        product_gate_active, check_architecture_health, _print_product_gate_skipped,
    )
    yield product.section_28p_duplicate_code(
        product_gate_active, check_duplicate_code, _print_product_gate_skipped,
    )
    yield product.section_28q_technical_debt(
        product_gate_active, check_technical_debt, _print_product_gate_skipped,
    )
    yield product.section_28r_complexity(
        product_gate_active, check_complexity, _print_product_gate_skipped,
    )
    yield governance.section_28s_data_size(
        check_governance_data_size, _exception_registry_error_note, _exception_note,
    )
    yield product.section_28t_readme_evidence(
        product_gate_active, check_readme_claim_evidence_levels,
        _print_product_gate_skipped,
    )
    yield review.section_29_runtime_triggers(check_m5_runtime_triggers)
    yield review.section_30_review_closure(check_review_closure)
    yield review.section_30c_review_provenance(check_review_machine_provenance)
    yield review.section_30b_loop_wiring(product_gate_active, check_loop_wiring_call_sites)
    yield delivery.section_32_change_triage(check_change_triage)
    yield product.section_33_injection_contract(
        product_gate_active, check_injection_contract, emit_injection_budget_section,
        _print_product_gate_skipped,
    )
    yield delivery.section_34_completion_recommendations(check_completion_recommendation)
    yield governance.section_35_snapshot_freshness(check_snapshot_freshness)
    yield governance.section_36_risk_mitigation(
        emit_risk_mitigation_closure, check_risk_mitigation_closure_with_archive,
    )
    yield delivery.section_37_release_gates(release_unit_issues, HOST_PROJECT_ROOT)
    yield delivery.section_38_ci_evidence(check_ci_evidence)
    yield review.section_39_completion_gate(check_r1_completion_gate)
    yield review.section_41_priority_inversion(_provenance_rows_for_governance)
    yield review.section_42_discovery_closure(
        _collect_session_closure_events, _DEFERRED_LEDGER_FILENAME,
    )
    yield product.section_28u_dsh_smoke(
        product_gate_active, check_dsh_preset_smoke, _print_product_gate_skipped,
    )
    yield product.section_28v_dsh_schema(product_gate_active, _print_product_gate_skipped)
    yield product.section_28w_dsh_boundary(product_gate_active, _print_product_gate_skipped)


def _run_full_engine_checks(args):
    """Run the public full-health profile and return its issue count."""
    from full_check_runner import run_full_checks
    return run_full_checks(_full_check_results(args))


# ── Summary-only engine (REQ-145.7) ──────────────────────────────

def _extract_summary_count(stdout_text):
    """Return (issues_count, parse_degraded) from the engine's summary line.

    Anchors on the stable ``Result: ISSUES FOUND — N issue(s)`` (or the
    ``Result: PASSED — 0 issues found``) line. A format drift (neither line
    matches) degrades to ``(0, True)`` so the caller emits a fail-safe
    ``(parse degraded)`` marker instead of a hard error.
    """
    m = re.search(r"Result:\s*ISSUES FOUND\s*[—\-–]\s*(\d+)\s*issue\(s\)", stdout_text)
    if m:
        return int(m.group(1)), False
    m2 = re.search(r"Result:\s*PASSED\s*[—\-–]\s*0\s*issues found", stdout_text)
    if m2:
        return 0, False
    return 0, True


def _aggregate_check_summary(stdout_text):
    """Parse captured full engine output into a summary dict (REQ-145.7).

    Anchors the issue count on the ``Result: ISSUES FOUND — N issue(s)`` line
    and the ``[FAIL]`` / ``[WARN]`` / ``[ADVISORY]`` severity lines, correlating
    each to its enclosing ``┌─ Check N: ... ┐`` section. Returns
    ``{issues_count, parse_degraded, first_fail, first_warn, fail_items,
    warn_items, advisory_items, advisory}``.
    """
    issues_count, parse_degraded = _extract_summary_count(stdout_text)
    fail_items, warn_items, advisory_items = [], [], []
    current_check = ""
    for line in stdout_text.splitlines():
        hm = re.search(r"┌─\s*Check\s+(.+?)\s*[─-]+┐", line)
        if hm:
            current_check = hm.group(1).strip()
            continue
        # FIX-278 G2/P2-4: [BLOCKING]/[ERROR] severity markers (M5 structural
        # gaps, runtime-readiness errors — counted into all_issues by the
        # engine) are FAIL-class tokens; leaving them out would render the
        # standard-summary detail section empty for M5-only inputs and push
        # the model back into a full-check chase (the G1 behavior gap).
        for token in ("[FAIL]", "[BLOCKING]", "[ERROR]", "[WARN]", "[ADVISORY]"):
            idx = line.find(token)
            if idx >= 0:
                detail = line[idx + len(token):].strip()
                label = f"{current_check}: {detail}" if current_check else detail
                if token in ("[FAIL]", "[BLOCKING]", "[ERROR]"):
                    fail_items.append(label)
                elif token == "[WARN]":
                    warn_items.append(label)
                else:
                    advisory_items.append(label)
                break
    return {
        "issues_count": issues_count,
        "parse_degraded": parse_degraded,
        "first_fail": fail_items[0] if fail_items else None,
        "first_warn": warn_items[0] if warn_items else None,
        "fail_items": fail_items,
        "warn_items": warn_items,
        "advisory_items": advisory_items,
        "advisory": advisory_items[0] if advisory_items else None,
    }


def _summary_detail_cap():
    """FIX-278 G1: max issue detail lines in the default summary output."""
    return 5


def _summary_detail_char_limit():
    """FIX-278 G1: per-line truncation budget for summary detail lines.

    130 chars × ≤5 lines ≲ 700 chars — the G1 output budget (audit-148 §2.1:
    the detail section must stay well under the ~1.7KB full-check output so a
    model never re-runs the whole engine to understand the summary).
    """
    return 130


def _truncate_summary_detail(label):
    """Bound one summary detail line (G1: header + ≤130 chars, ellipsis)."""
    limit = _summary_detail_char_limit()
    if len(label) <= limit:
        return label
    return label[: max(1, limit - 1)] + "…"


def _ordered_detail_items(summary):
    """Return [(severity, label), ...]: FAIL items first, then WARN — capped.

    FIX-278 G1: the default summary shows the first FAIL/WARN plus at most
    ``_summary_detail_cap()`` ordered details (audit-148 §2.1: the 103-char
    summary line alone triggered a 25KB model chase chain; giving the top
    items removes the need for the full check re-run).
    """
    items = []
    for item in summary.get("fail_items") or []:
        items.append(("FAIL", item))
    for item in summary.get("warn_items") or []:
        items.append(("WARN", item))
    return items[:_summary_detail_cap()]


def _print_check_summary(summary, args):
    """Render the ``--summary-only`` output (REQ-145.7 output contract).

    Summary line ``Governance: {N} issues`` (or ``Governance: [PASS]`` when
    N==0) followed by the first FAIL/WARN detail line; the detail granularity
    follows ``--level`` (lightweight → summary + first FAIL; standard →
    summary + first FAIL/WARN + top-5 ordered details + a TWO-STATE tail
    line — ``构成已全量展示（N 项）`` when all details are already displayed
    (≤ cap, FEAT-012 G6: no chase invitation) and ``共 N issues，--level
    strict 查看全部`` above the cap (FIX-278 G1); strict → summary + all
    FAIL/WARN). Advisory (``fatal_on_error=false``) issues are not counted
    and are only annotated when they are the first issue surfaced.
    """
    count = summary.get("issues_count") or 0
    if summary.get("parse_degraded"):
        print(f"Governance: {count} issues (parse degraded)")
        return
    if count == 0:
        print("Governance: [PASS]")
    else:
        print(f"Governance: {count} issues")
    level = getattr(args, "summary_level", None) or "standard"
    if count > 0:
        if level == "lightweight":
            if summary["first_fail"]:
                print(f"[FAIL] {summary['first_fail']}")
        elif level == "strict":
            for item in summary["fail_items"]:
                print(f"[FAIL] {item}")
            for item in summary["warn_items"]:
                print(f"[WARN] {item}")
        else:  # standard — FIX-278 G1 top-N + FEAT-012 G6 two-state tail
            for sev, item in _ordered_detail_items(summary):
                print(f"[{sev}] {_truncate_summary_detail(item)}")
            # FEAT-012 G6: when every FAIL/WARN detail is ALREADY on screen
            # (≤ _summary_detail_cap() lines) the tail states that fact
            # instead of inviting a --level strict chase — a small-N chase
            # invitation re-creates the audit-148 §2.1 amplification G1 was
            # built to remove (103-char summary → ~25KB chain). Judged on
            # the actual detail count (not issues_count) so the 全量展示
            # claim is literally true; count>0 with no parsed details keeps
            # the guidance (nothing is on screen to display).
            total_details = (len(summary.get("fail_items") or [])
                             + len(summary.get("warn_items") or []))
            tail = (f"构成已全量展示（{total_details} 项）"
                    if 0 < total_details <= _summary_detail_cap()
                    else f"共 {count} issues，--level strict 查看全部")
            print(tail)
    if not summary["fail_items"] and not summary["warn_items"] and summary["advisory"]:
        print(f"[ADVISORY] {summary['advisory']}")


# ── Gate auto-judgment (B-level automation) ───────────────────────

# Per-gate check item heuristics: (check_label, auto_judge_function)
# Each function returns: (PASS/FAIL/NEEDS_HUMAN, detail_message)

def _check_file_exists(relative_path, label):
    from gate_judgment import _check_file_exists as run
    return run(relative_path, label, product_root=ROOT)


def _check_snippet_in_file(relative_path, snippet, label):
    from gate_judgment import _check_snippet_in_file as run
    return run(relative_path, snippet, label, product_root=ROOT)


def _check_all_required_files_exist():
    from gate_judgment import _check_all_required_files_exist as run
    return run(required_files=lambda: _product_policy("REQUIRED_FILES"),
               build_required_files_from_manifest=build_required_files_from_manifest)


def _check_governance_file_exists(filename):
    from gate_judgment import _check_governance_file_exists as run
    return run(filename, governance_dir=GOVERNANCE_DIR)


def _check_quantifiable_metrics():
    from gate_judgment import _check_quantifiable_metrics as run
    return run(plan_path=SAMPLE_PATH)


def _check_scope_boundary():
    from gate_judgment import _check_scope_boundary as run
    return run(plan_path=SAMPLE_PATH)


def _check_stakeholders():
    from gate_judgment import _check_stakeholders as run
    return run(plan_path=SAMPLE_PATH)


def _check_out_of_scope():
    from gate_judgment import _check_out_of_scope as run
    return run(plan_path=SAMPLE_PATH)


def _check_completed_ratio(min_ratio=0.5):
    from gate_judgment import _check_completed_ratio as run
    return run(min_ratio, plan_path=SAMPLE_PATH)


def _check_evidence_mentions(keyword, label):
    from gate_judgment import _check_evidence_mentions as run
    return run(keyword, label, evidence_path=EVIDENCE_PATH)


def _read_archive_aware_governance_text(include=()):
    from gate_judgment import _read_archive_aware_governance_text as run
    return run(include, data_source=_archive_reader)


def _contains_all(text, keywords):
    from gate_judgment import _contains_all as run
    return run(text, keywords)


def _contains_any(text, keywords):
    from gate_judgment import _contains_any as run
    return run(text, keywords)


def _has_line_with_all(text, keyword_groups):
    from gate_judgment import _has_line_with_all as run
    return run(text, keyword_groups)


def _iter_archive_aware_evidence_units():
    from gate_judgment import _iter_archive_aware_evidence_units as run
    return run(data_source=_archive_reader)


def _line_has_issue_severity(line):
    from gate_judgment import _line_has_issue_severity as run
    return run(line)


def _line_has_issue_status_value(line):
    from gate_judgment import _line_has_issue_status_value as run
    return run(line)


def _line_has_real_issue_item(line):
    from gate_judgment import _line_has_real_issue_item as run
    return run(line)


def _plan_row_is_inactive(parts):
    from gate_judgment import _plan_row_is_inactive as run
    return run(parts)


def _check_g10_real_operation_data():
    from gate_judgment import _check_g10_real_operation_data as run
    return run(data_source=_archive_reader)


def _check_g10_feedback_archived_classified():
    from gate_judgment import _check_g10_feedback_archived_classified as run
    return run(data_source=_archive_reader)


def _check_g10_issue_list_severity_status():
    from gate_judgment import _check_g10_issue_list_severity_status as run
    return run(data_source=_archive_reader)


def _check_g10_executable_optimization_items():
    from gate_judgment import _check_g10_executable_optimization_items as run
    return run(data_source=_archive_reader)


def _check_g11_retro_complete():
    from gate_judgment import _check_g11_retro_complete as run
    return run(data_source=_archive_reader)


def _check_g11_rules_templates_backfilled():
    from gate_judgment import _check_g11_rules_templates_backfilled as run
    return run(data_source=_archive_reader)


def _check_g11_next_round_direction():
    from gate_judgment import _check_g11_next_round_direction as run
    return run(plan_path=SAMPLE_PATH, split_markdown_table_row=_split_markdown_table_row)


def _check_risk_has_closed(label='关键缺陷'):
    from gate_judgment import _check_risk_has_closed as run
    return run(label, risk_path=RISK_PATH)


def _check_plan_has_priority(priority='P0'):
    from gate_judgment import _check_plan_has_priority as run
    return run(priority, plan_path=SAMPLE_PATH)


def _check_version_consistency_heuristic():
    from gate_judgment import _check_version_consistency_heuristic as check
    return check(product_root=ROOT, extract_skill_version=_extract_skill_version,
                 skill_file=lambda: ROOT / "skills/software-project-governance/SKILL.md",
                 changelog_file=lambda: ROOT / "project/CHANGELOG.md")


_GATE_CHECK_BINDINGS = {
    'check_quantifiable_metrics': lambda: _check_quantifiable_metrics,
    'check_scope_boundary': lambda: _check_scope_boundary,
    'check_stakeholders': lambda: _check_stakeholders,
    'check_out_of_scope': lambda: _check_out_of_scope,
    'check_all_required_files_exist': lambda: _check_all_required_files_exist,
    'check_g10_real_operation_data': lambda: _check_g10_real_operation_data,
    'check_g10_feedback_archived_classified': lambda: _check_g10_feedback_archived_classified,
    'check_g10_issue_list_severity_status': lambda: _check_g10_issue_list_severity_status,
    'check_g10_executable_optimization_items': lambda: _check_g10_executable_optimization_items,
    'check_g11_retro_complete': lambda: _check_g11_retro_complete,
    'check_g11_rules_templates_backfilled': lambda: _check_g11_rules_templates_backfilled,
    'check_g11_next_round_direction': lambda: _check_g11_next_round_direction,
    'check_risk_has_closed': lambda: _check_risk_has_closed,
    'check_version_consistency_heuristic': lambda: _check_version_consistency_heuristic,
}


def _registered_gate_function(name):
    binding = _GATE_CHECK_BINDINGS.get(name)
    try:
        return binding() if binding is not None else None
    except NameError:
        return None


def _gate_check_result_from_definition(check_definition):
    from gate_judgment import _gate_check_result_from_definition as run
    return run(check_definition, evidence_path=EVIDENCE_PATH, product_root=ROOT, plan_path=SAMPLE_PATH,
               registered_gate_function=_registered_gate_function)


def auto_judge_gate(gate_id, unit_id=None):
    from gate_judgment import auto_judge_gate as run

    def validate_registry(registry):
        path = _display_path(LIFECYCLE_REGISTRY_PATH, ROOT)
        return _gate_execution_registry_contract_issues(registry, path)

    return run(gate_id, unit_id, parse_gate_detail=parse_gate_detail,
               load_lifecycle_registry=lambda: _load_lifecycle_registry(), validate_registry=validate_registry,
               gate_check_result_from_definition=lambda definition: _gate_check_result_from_definition(definition))


def cmd_gate_check(args):
    from governance_fact_cli import cmd_gate_check as run
    return run(args)

def check_plugin_freshness():
    """Compare installed plugin version with source repository HEAD."""
    import json
    import subprocess
    from datetime import datetime

    result = {
        "installed_version": "unknown",
        "installed_commit": "unknown",
        "installed_date": "unknown",
        "source_version": "unknown",
        "source_commit": "unknown",
        "status": "UNKNOWN",
        "commits_behind": 0,
        "action": "",
    }

    # Read installed plugin info
    installed_json = ROOT / ".claude-plugin" / "installed_plugins.json"
    if not installed_json.exists():
        # Try Claude's global installed_plugins.json
        import os as _os
        home = _os.path.expanduser("~")
        installed_json = _os_path(home) / ".claude" / "installed_plugins.json"

    if installed_json.exists():
        try:
            with open(installed_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            plugins = data.get("plugins", data) if isinstance(data, dict) else data
            if isinstance(plugins, list):
                for p in plugins:
                    if p.get("name") == "software-project-governance":
                        result["installed_version"] = p.get("version", "unknown")
                        result["installed_commit"] = (p.get("gitCommitSha") or "unknown")[:7]
                        result["installed_date"] = p.get("installedAt", "unknown")[:10] if p.get("installedAt") else "unknown"
                        break
        except (json.JSONDecodeError, KeyError, IOError):
            pass

    # Read source version from marketplace.json
    marketplace_json = ROOT / ".claude-plugin" / "marketplace.json"
    if marketplace_json.exists():
        try:
            with open(marketplace_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            plugins = data.get("plugins", [])
            for p in plugins:
                if p.get("name") == "software-project-governance":
                    result["source_version"] = p.get("version", "unknown")
                    break
        except (json.JSONDecodeError, KeyError, IOError):
            pass

    # Get source HEAD commit
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            cwd=str(ROOT), timeout=5
        )
        if r.returncode == 0:
            result["source_commit"] = r.stdout.strip()[:7]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # Determine status
    if result["installed_version"] == result["source_version"]:
        result["status"] = "UP TO DATE"
        result["action"] = "No action needed."
    elif result["installed_version"] == "unknown":
        result["status"] = "UNKNOWN (plugin not installed via marketplace?)"
        result["action"] = "Run /plugin marketplace add <path> to install."
    else:
        result["status"] = "OUTDATED"
        result["action"] = "Run /plugin update software-project-governance  or  /reload-plugins"

    return result


def check_untracked_files():
    """Check for untracked files in the working directory (FIX-057 Phase 2).

    Runs ``git ls-files --others --exclude-standard`` and reports any
    untracked files with heuristic classification suggestions.  Ordinary
    scratch files are non-blocking; unignored root platform entry files are
    actionable because they can change agent behavior outside versioned review.

    FIX-270 (mixed-root): the git fact source is the HOST project root
    (HOST_PROJECT_ROOT) — the project being governed — never the plugin
    package root. In dogfood mode (host == plugin) this is unchanged.
    """
    import subprocess

    result = {
        "pass": True,
        "untracked_count": 0,
        "untracked_files": [],
        "actionable_entry_files": [],
        "suggest_archive": [],
        "suggest_temp_script": [],
        "suggest_manual": [],
    }

    try:
        r = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True,
            cwd=str(HOST_PROJECT_ROOT), timeout=10
        )
        if r.returncode != 0:
            result["pass"] = None  # couldn't run
            return result

        files = [f.strip().replace("\\", "/") for f in r.stdout.splitlines() if f.strip()]
        if not files:
            return result  # PASS -- no untracked files

        result["pass"] = False
        result["untracked_count"] = len(files)
        result["untracked_files"] = files

        # Heuristic classification
        for f in files:
            # ── Root platform-native entry files affect active agent behavior ──
            if "/" not in f and f in _product_policy("PLATFORM_ENTRY_FILES"):
                result["actionable_entry_files"].append(f)
                continue

            # ── docs/** or project/references/** → suggest archive ──
            if f.startswith("docs/") or f.startswith("project/references/"):
                result["suggest_archive"].append(f)
                continue

            # ── *.py single file at repo root → possible temp script ──
            if "/" not in f and f.endswith(".py"):
                result["suggest_temp_script"].append(f)
                continue

            # ── Everything else needs human judgment ──
            result["suggest_manual"].append(f)

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        result["pass"] = None

    return result


def check_agent_locks_format():
    """Validate .governance/agent-locks.json existence, JSON validity, and schema integrity.

    Returns a list of WARN-level issue dicts.  Empty list = clean.
    This check is informational-only (WARN) -- format corruption does not block commit.
    Used as a helper by check_agent_lock_consistency() (Check 26, FIX-056 Phase 2).
    Phase 1 format-only check has been subsumed into the full Check 26.
    """
    import json

    issues = []
    locks_path = GOVERNANCE_DIR / "agent-locks.json"

    # ── Existence check ──
    if not locks_path.is_file():
        issues.append({
            "type": "missing",
            "detail": ".governance/agent-locks.json not found. Run governance init or create with: {\"active_tasks\": {}, \"file_locks\": {}}"
        })
        return issues

    # ── JSON validity ──
    try:
        with open(locks_path, "r", encoding="utf-8") as f:
            raw = f.read()
        if not raw.strip():
            issues.append({
                "type": "empty",
                "detail": ".governance/agent-locks.json is empty"
            })
            return issues
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        issues.append({
            "type": "invalid_json",
            "detail": f".governance/agent-locks.json is not valid JSON: {e}"
        })
        return issues
    except IOError as e:
        issues.append({
            "type": "io_error",
            "detail": f".governance/agent-locks.json read error: {e}"
        })
        return issues

    # ── Schema check ──
    if not isinstance(data, dict):
        issues.append({
            "type": "not_dict",
            "detail": ".governance/agent-locks.json root must be a JSON object (dict)"
        })
        return issues

    # Required top-level keys
    required_keys = ["active_tasks", "file_locks"]
    for key in required_keys:
        if key not in data:
            issues.append({
                "type": "missing_key",
                "detail": f".governance/agent-locks.json missing required key: '{key}'"
            })

    # active_tasks must be a dict
    if "active_tasks" in data and not isinstance(data["active_tasks"], dict):
        issues.append({
            "type": "type_error",
            "detail": ".governance/agent-locks.json 'active_tasks' must be a JSON object (dict), got " + type(data["active_tasks"]).__name__
        })

    # file_locks must be a dict
    if "file_locks" in data and not isinstance(data["file_locks"], dict):
        issues.append({
            "type": "type_error",
            "detail": ".governance/agent-locks.json 'file_locks' must be a JSON object (dict), got " + type(data["file_locks"]).__name__
        })

    # ── active_tasks entry schema check ──
    if "active_tasks" in data and isinstance(data["active_tasks"], dict):
        for task_id, entry in data["active_tasks"].items():
            if not isinstance(entry, dict):
                issues.append({
                    "type": "schema_violation",
                    "detail": f"agent-locks.json active_tasks['{task_id}'] must be a dict"
                })
                continue
            required_entry_keys = ["spawned_at", "coordinator_session", "target_files"]
            for rk in required_entry_keys:
                if rk not in entry:
                    issues.append({
                        "type": "schema_violation",
                        "detail": f"agent-locks.json active_tasks['{task_id}'] missing required field: '{rk}'"
                    })
            if "target_files" in entry and not isinstance(entry["target_files"], list):
                issues.append({
                    "type": "schema_violation",
                    "detail": f"agent-locks.json active_tasks['{task_id}'].target_files must be a list"
                })

    # ── file_locks entry schema check ──
    if "file_locks" in data and isinstance(data["file_locks"], dict):
        for file_path, entry in data["file_locks"].items():
            if not isinstance(entry, dict):
                issues.append({
                    "type": "schema_violation",
                    "detail": f"agent-locks.json file_locks['{file_path}'] must be a dict"
                })
                continue
            required_entry_keys = ["locked_by", "locked_at", "ttl_seconds", "ttl_reason"]
            for rk in required_entry_keys:
                if rk not in entry:
                    issues.append({
                        "type": "schema_violation",
                        "detail": f"agent-locks.json file_locks['{file_path}'] missing required field: '{rk}'"
                    })
            if "ttl_seconds" in entry and not isinstance(entry["ttl_seconds"], (int, float)):
                issues.append({
                    "type": "schema_violation",
                    "detail": f"agent-locks.json file_locks['{file_path}'].ttl_seconds must be a number"
                })
            # FEAT-013 (RISK-046): optional expected_new flag — the
            # pre-created-file exemption declared at acquire time
            # (agent-locks-acquire --expected-new). Absent = regular
            # existing-file lock (backward compatible: legacy locks PASS).
            if "expected_new" in entry and not isinstance(entry["expected_new"], bool):
                issues.append({
                    "type": "schema_violation",
                    "detail": f"agent-locks.json file_locks['{file_path}'].expected_new must be a boolean when present (FEAT-013 pre-created-file declaration)",
                })

    return issues


def check_agent_lock_consistency():
    """Comprehensive agent lock consistency check (FIX-056 Phase 2).

    Checks:
      - Format/schema validity (delegates to check_agent_locks_format)
      - Task existence: locked_by task_ids must exist in plan-tracker
      - Orphan locks: file_locks referencing task_ids not in active_tasks
      - Expired locks: locked_at + ttl_seconds < now
      - Multi-lock conflict: same file locked by multiple active tasks

    Returns a dict with keys:
      - skipped: str if check was skipped (agent-locks.json missing), else None
      - active_task_count: number of active_tasks entries
      - file_lock_count: number of file_locks entries
      - issues: list of WARN-level issue dicts (type + detail)
    """
    import json
    from datetime import datetime, timezone

    result = {
        "skipped": None,
        "active_task_count": 0,
        "file_lock_count": 0,
        "issues": [],
    }

    locks_path = GOVERNANCE_DIR / "agent-locks.json"

    # ── Format check (Phase 1, reused) ──
    fmt_issues = check_agent_locks_format()
    for fi in fmt_issues:
        result["issues"].append({
            "type": f"format_{fi['type']}",
            "detail": fi["detail"],
        })

    # If format is broken, skip consistency checks (can't parse data)
    if not locks_path.is_file():
        result["skipped"] = "agent-locks.json not found — lock consistency check skipped."
        return result

    try:
        with open(locks_path, "r", encoding="utf-8") as f:
            raw = f.read()
        if not raw.strip():
            result["skipped"] = "agent-locks.json is empty — lock consistency check skipped."
            return result
        data = json.loads(raw)
    except (json.JSONDecodeError, IOError, UnicodeDecodeError):
        result["skipped"] = "agent-locks.json is unparseable — lock consistency check skipped."
        return result

    if not isinstance(data, dict):
        result["skipped"] = "agent-locks.json root is not a dict — lock consistency check skipped."
        return result

    active_tasks = data.get("active_tasks", {})
    file_locks = data.get("file_locks", {})

    if not isinstance(active_tasks, dict):
        active_tasks = {}
    if not isinstance(file_locks, dict):
        file_locks = {}

    result["active_task_count"] = len(active_tasks)
    result["file_lock_count"] = len(file_locks)

    # If nothing active, skip consistency checks
    if not active_tasks and not file_locks:
        return result

    # ── Load plan-tracker task IDs ──
    plan_task_ids = set()
    try:
        pt_path = GOVERNANCE_DIR / "plan-tracker.md"
        if pt_path.is_file():
            pt_content = pt_path.read_text(encoding="utf-8")
            # Match task IDs in any table cell.  Active task tables often use
            # a priority first column, e.g. | **P1** | FIX-066 | ...
            for line in pt_content.split("\n"):
                if not line.lstrip().startswith("|"):
                    continue
                for task_id in re.findall(r"\b([A-Z]+-\d+)\b", line):
                    plan_task_ids.add(task_id)
    except Exception:
        pass  # Can't read plan-tracker — skip task-existence check

    now = datetime.now(timezone.utc)

    # ── Check 1: Task existence — every locked_by / active_tasks key must be in plan-tracker ──
    all_lock_task_ids = set()

    for task_id in active_tasks.keys():
        all_lock_task_ids.add(task_id)
        if plan_task_ids and task_id not in plan_task_ids:
            result["issues"].append({
                "type": "task_not_in_plan",
                "detail": f"active_tasks['{task_id}'] is not found in plan-tracker.md — lock references an unregistered task.",
            })

    for file_path, entry in file_locks.items():
        if isinstance(entry, dict):
            locker = entry.get("locked_by", "")
            if locker:
                all_lock_task_ids.add(locker)
                if plan_task_ids and locker not in plan_task_ids:
                    result["issues"].append({
                        "type": "task_not_in_plan",
                        "detail": f"file_locks['{file_path}'].locked_by='{locker}' is not found in plan-tracker.md.",
                    })

    # ── Check 2: Orphan locks — file_locks.locked_by not in active_tasks ──
    active_task_ids = set(active_tasks.keys())
    for file_path, entry in file_locks.items():
        if isinstance(entry, dict):
            locker = entry.get("locked_by", "")
            if locker and locker not in active_task_ids:
                result["issues"].append({
                    "type": "orphan_lock",
                    "detail": f"file_locks['{file_path}'] is locked by '{locker}' which has no active_tasks entry (orphan lock).",
                })

    # ── Check 3: Expired locks ──
    for file_path, entry in file_locks.items():
        if not isinstance(entry, dict):
            continue
        locked_at_str = entry.get("locked_at", "")
        ttl = entry.get("ttl_seconds", 0)
        if locked_at_str and ttl:
            try:
                locked_at = datetime.fromisoformat(locked_at_str.replace("Z", "+00:00"))
                expiry = locked_at.timestamp() + float(ttl)
                if now.timestamp() > expiry:
                    locker = entry.get("locked_by", "unknown")
                    elapsed = int(now.timestamp() - locked_at.timestamp())
                    result["issues"].append({
                        "type": "expired_lock",
                        "detail": (f"file_locks['{file_path}'] expired (locked by '{locker}', "
                                   f"TTL {ttl}s, elapsed {elapsed}s) — stale lock should be cleaned up."),
                    })
            except (ValueError, TypeError, OverflowError):
                pass

    # Also check active_tasks expiry (based on spawned_at + max TTL 600s)
    for task_id, entry in active_tasks.items():
        if not isinstance(entry, dict):
            continue
        spawned_at_str = entry.get("spawned_at", "")
        if spawned_at_str:
            try:
                spawned_at = datetime.fromisoformat(spawned_at_str.replace("Z", "+00:00"))
                # Use 600s as max reasonable TTL for any task
                if (now - spawned_at).total_seconds() > 600:
                    result["issues"].append({
                        "type": "expired_task",
                        "detail": (f"active_tasks['{task_id}'] spawned at {spawned_at_str} "
                                   f"({int((now - spawned_at).total_seconds())}s ago) — may be stale."),
                    })
            except (ValueError, TypeError, OverflowError):
                pass

    # ── Check 4: Multi-lock conflict — same file locked by multiple active tasks ──
    file_to_lockers = {}
    for file_path, entry in file_locks.items():
        if isinstance(entry, dict):
            locker = entry.get("locked_by", "")
            if locker and locker in active_task_ids:
                file_to_lockers.setdefault(file_path, set()).add(locker)

    for file_path, lockers in file_to_lockers.items():
        if len(lockers) > 1:
            result["issues"].append({
                "type": "multi_lock_conflict",
                "detail": (f"file_locks['{file_path}'] is locked by multiple active tasks: "
                           f"{sorted(lockers)} — potential concurrent write conflict."),
            })

    for issue in result["issues"]:
        issue["severity"] = "BLOCKING" if lock_issue_is_blocking(issue) else "WARN"

    return result


# ── SYSGAP-030: Archive Integrity Check ────────────────────────────

def _legacy_parse_index_refs(index_lines):
    from governance_archive_data import _legacy_parse_index_refs as read
    return read(index_lines)


def check_archive_integrity():
    from governance_archive_data import check_archive_integrity as read
    return read(
        plan_path=SAMPLE_PATH,
        governance_dir=GOVERNANCE_DIR,
        plan_directory=_governance_dir,
        load_archive=_load_archive_module)


def cmd_check_agent_locks(_args):
    """Standalone subcommand: check-locks — run agent lock consistency check."""
    result = check_agent_lock_consistency()

    if result.get("skipped"):
        print(f"[INFO] {result['skipped']}")
        return

    print(f"Active tasks: {result['active_task_count']}")
    print(f"File locks:   {result['file_lock_count']}")

    issues = result.get("issues", [])
    if not issues:
        print("Result: PASS — agent-locks.json is clean.")
    else:
        blocking = [i for i in issues if lock_issue_is_blocking(i)]
        print(f"\n{len(issues)} lock issue(s), {len(blocking)} blocking:")
        for issue in issues:
            severity = "BLOCKING" if lock_issue_is_blocking(issue) else "WARN"
            print(f"  [{severity}:{issue['type']}] {issue['detail']}")
        result_label = "WARN" if blocking else "INFO"
        print(f"\nResult: {result_label} — {len(issues)} lock consistency issue(s).")


def cmd_check_archive_integrity(_args):
    from status_cli import cmd_check_archive_integrity as read
    return read(_args, check_integrity=check_archive_integrity)


def cmd_check_plugin_freshness(_args):
    """Check if installed plugin is up to date with source repository."""
    result = check_plugin_freshness()

    # Calculate behind count
    import subprocess
    try:
        # Try to find installed commit in git log
        r = subprocess.run(
            ["git", "rev-list", "--count", f"{result['installed_commit']}..HEAD"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=5
        )
        if r.returncode == 0:
            result["commits_behind"] = int(r.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, ValueError):
        pass

    print()
    print("=== Plugin Freshness Check ===")
    print(f"  Installed: {result['installed_version']} (commit {result['installed_commit']}, {result['installed_date']})")
    print(f"  Source:    {result['source_version']} (commit {result['source_commit']})")
    print(f"  Status:    {result['status']}")
    if result["commits_behind"] > 0:
        print(f"  Behind:    {result['commits_behind']} commit(s)")
    if result["action"]:
        print(f"  Action:    {result['action']}")
    print()

    # Exit with error if outdated (for CI)
    if result["status"] == "OUTDATED":
        import sys
        sys.exit(1)


def _e2e_command_matrix():
    from product_fixture_validation import _e2e_command_matrix as run
    return run(
        validate_e2e_cleanup=_validate_e2e_cleanup, validate_e2e_gate_g99=_validate_e2e_gate_g99,
        validate_e2e_gates=_validate_e2e_gates, validate_e2e_governance_proxy=_validate_e2e_governance_proxy,
        validate_e2e_status=_validate_e2e_status,
        validate_e2e_verify_known_failure=_validate_e2e_verify_known_failure,
    )


def _e2e_target_cwd_command_matrix(e2e_dir):
    from product_fixture_validation import _e2e_target_cwd_command_matrix as run
    return run(
        e2e_dir, validate_e2e_cleanup=_validate_e2e_cleanup, validate_e2e_gate_g99=_validate_e2e_gate_g99,
        validate_e2e_gates=_validate_e2e_gates, validate_e2e_status=_validate_e2e_status,
    )


def _e2e_target_fixture_checks(e2e_dir):
    from product_fixture_validation import _e2e_target_fixture_checks as run
    return run(
        e2e_dir, package_root=ROOT, extract_plan_workflow_version=_extract_plan_workflow_version,
        extract_skill_version=_extract_skill_version,
    )


def _e2e_contract_checks():
    from product_fixture_validation import _e2e_contract_checks as run
    return run(package_root=ROOT)


# DSH has a headless profile. The adapter tracks live-session evidence separately.
# Adding DSH here requires a validated command and target-project evidence.
# See adapters/dsh/README.md for the tested CLI and authentication requirements.
AGENT_RUNTIME_E2E_PLATFORMS = ("claude", "codex", "gemini", "opencode", "pi")


def _agent_runtime_e2e_prompt(agent_id):
    from host_certification import _agent_runtime_e2e_prompt as run
    return run(agent_id)


def _agent_runtime_e2e_command_matrix(e2e_dir=None):
    from host_certification import _agent_runtime_e2e_command_matrix as run
    return run(
        e2e_dir, package_root=ROOT, agent_runtime_e2e_platforms=AGENT_RUNTIME_E2E_PLATFORMS,
        agent_runtime_e2e_prompt=_agent_runtime_e2e_prompt,
        validate_agent_runtime_e2e_passed=_validate_agent_runtime_e2e_passed,
    )


def _run_e2e_subprocess(command, timeout=30, cwd=None):
    from product_fixture_validation import _run_e2e_subprocess as run
    return run(command, timeout, cwd, package_root=ROOT)


def _e2e_output(result):
    from product_fixture_validation import _e2e_output as run
    return run(result)


def _truncate_log(text, limit=1200):
    from product_fixture_validation import _truncate_log as run
    return run(text, limit)


def _coerce_e2e_text(value):
    from product_fixture_validation import _coerce_e2e_text as run
    return run(value)


def _has_all(text, needles):
    from product_fixture_validation import _has_all as run
    return run(text, needles)


def _e2e_json_object(result):
    from product_fixture_validation import _e2e_json_object as run
    return run(result)


def _valid_e2e_loop_view(view):
    from product_fixture_validation import _valid_e2e_loop_view as run
    return run(view)


def _validate_e2e_status(result):
    from product_fixture_validation import _validate_e2e_status as run
    return run(result, e2e_json_object=_e2e_json_object, valid_e2e_loop_view=_valid_e2e_loop_view)


def _validate_e2e_gates(result):
    from product_fixture_validation import _validate_e2e_gates as run
    return run(result, e2e_json_object=_e2e_json_object, valid_e2e_loop_view=_valid_e2e_loop_view)


def _validate_e2e_gate_g99(result):
    from product_fixture_validation import _validate_e2e_gate_g99 as run
    return run(result, e2e_json_object=_e2e_json_object)
def _validate_e2e_cleanup(result):
    from product_fixture_validation import _validate_e2e_cleanup as run
    return run(result, e2e_output=_e2e_output)


def _normalize_e2e_verify_failure(line):
    from product_fixture_validation import _normalize_e2e_verify_failure as run
    return run(line)


def _extract_e2e_verify_failures(output):
    from product_fixture_validation import _extract_e2e_verify_failures as run
    return run(output, normalize_e2e_verify_failure=_normalize_e2e_verify_failure)


def _validate_e2e_verify_known_failure(result):
    from product_fixture_validation import _validate_e2e_verify_known_failure as run
    return run(
        result, known_verify_failure_signatures=_host_policy('_KNOWN_VERIFY_FAILURE_SIGNATURES'),
        e2e_output=_e2e_output, extract_e2e_verify_failures=_extract_e2e_verify_failures,
    )


def _evaluate_e2e_target_fixture_check(entry):
    from product_fixture_validation import _evaluate_e2e_target_fixture_check as run
    return run(entry, package_root=ROOT, extract_skill_version=_extract_skill_version)


def _validate_e2e_governance_proxy(result):
    from product_fixture_validation import _validate_e2e_governance_proxy as run
    return run(result, e2e_json_object=_e2e_json_object, valid_e2e_loop_view=_valid_e2e_loop_view)
def _evaluate_e2e_command(entry, runner=_run_e2e_subprocess):
    from product_fixture_validation import _evaluate_e2e_command as run
    return run(entry, runner)


def _evaluate_e2e_contract_check(entry):
    from product_fixture_validation import _evaluate_e2e_contract_check as run
    return run(entry, has_all=_has_all)


def _validate_agent_runtime_e2e_passed(agent_id, result, root=None):
    from host_certification import _validate_agent_runtime_e2e_passed as run
    return run(
        agent_id, result, root, package_root=ROOT, e2e_output=_e2e_output,
        is_valid_agent_runtime_mode=_is_valid_agent_runtime_mode,
        is_valid_agent_runtime_workflow_agent=_is_valid_agent_runtime_workflow_agent,
        parse_agent_runtime_e2e_fields=_parse_agent_runtime_e2e_fields,
    )


def _agent_runtime_e2e_candidate_texts(output):
    from host_certification import _agent_runtime_e2e_candidate_texts as run
    return run(output)


def _parse_agent_runtime_e2e_fields(output):
    from host_certification import _parse_agent_runtime_e2e_fields as run
    return run(output, agent_runtime_e2e_candidate_texts=_agent_runtime_e2e_candidate_texts)


def _is_non_placeholder_agent_runtime_value(value):
    from host_certification import _is_non_placeholder_agent_runtime_value as run
    return run(value)


def _is_valid_agent_runtime_workflow_agent(value):
    from host_certification import _is_valid_agent_runtime_workflow_agent as run
    return run(
        value, agent_runtime_e2e_platforms=AGENT_RUNTIME_E2E_PLATFORMS,
        is_non_placeholder_agent_runtime_value=_is_non_placeholder_agent_runtime_value,
    )


def _is_valid_agent_runtime_mode(value):
    from host_certification import _is_valid_agent_runtime_mode as run
    return run(value, is_non_placeholder_agent_runtime_value=_is_non_placeholder_agent_runtime_value)


def _classify_agent_runtime_blocked(agent_id, output='', exception=None):
    from host_certification import _classify_agent_runtime_blocked as run
    return run(agent_id, output, exception)


def _resolve_agent_runtime_command(command):
    from host_certification import _resolve_agent_runtime_command as run
    return run(command)


def _run_agent_runtime_e2e_subprocess(command, timeout=120, cwd=None):
    from host_certification import _run_agent_runtime_e2e_subprocess as run
    return run(
        command, timeout, cwd, package_root=ROOT,
        cleanup_agent_runtime_process_tree=_cleanup_agent_runtime_process_tree,
        resolve_agent_runtime_command=_resolve_agent_runtime_command,
    )


def _cleanup_agent_runtime_process_tree(process):
    from host_certification import _cleanup_agent_runtime_process_tree as run
    return run(process)


def _evaluate_agent_runtime_e2e_command(entry, timeout=120, runner=_run_agent_runtime_e2e_subprocess):
    from host_certification import _evaluate_agent_runtime_e2e_command as run
    return run(
        entry, timeout, runner, classify_agent_runtime_blocked=_classify_agent_runtime_blocked,
        coerce_e2e_text=_coerce_e2e_text, e2e_output=_e2e_output, truncate_log=_truncate_log,
    )


def cmd_agent_runtime_e2e(args):
    from host_certification import cmd_agent_runtime_e2e as run
    return run(
        args, package_root=ROOT, agent_runtime_e2e_platforms=AGENT_RUNTIME_E2E_PLATFORMS,
        agent_runtime_e2e_command_matrix=_agent_runtime_e2e_command_matrix,
        evaluate_agent_runtime_e2e_command=_evaluate_agent_runtime_e2e_command,
    )


def cmd_gemini_auth_preflight(_args):
    from runtime_preflight import cmd_gemini_auth_preflight as run
    return run(_args, gemini_auth_preflight=_gemini_auth_preflight)


def cmd_opencode_provider_preflight(_args):
    from runtime_preflight import cmd_opencode_provider_preflight as run
    return run(
        _args, opencode_provider_model_preflight=_opencode_provider_model_preflight,
        sanitize_opencode_probe_text=_sanitize_opencode_probe_text,
    )


def _external_validation_read_text(path):
    from external_project_diagnostics import read_text
    return read_text(path)


def _external_validation_canonical_hook_text(hook_name, root=None):
    from external_project_diagnostics import canonical_hook_text
    return canonical_hook_text(hook_name, ROOT if root is None else root)


# ── ArchGuard architecture-health stewardship (REQ-101 / FIX-152 / 0.58.0) ──────
# Four self-contained check_* helpers. Advisory-only in 0.58.0
# (gate_integration.fatal_on_error=false). Designed self-contained
# (signature ``root=None``) so they are the first candidates to extract
# in the 0.59.0+ per-domain split. See docs/requirements/archguard-design-0.58.0.md
# and its §7 design-review appendix for the G6/G7/G8/G9 constraints honored here.



def _archguard_load_schema(root=None):
    from architecture_diagnostics import _archguard_load_schema as run
    return run(
        root, package_root=ROOT, archguard_schema_rel=_product_policy("ARCHGUARD_SCHEMA_REL"),
        display_path=_display_path,
    )


from checks.architecture_health import (
    _archguard_excluded, _archguard_exclusion_match, _archguard_iter_code_files, _archguard_severity,
)


def check_architecture_health(root=None, schema=None):
    from architecture_diagnostics import check_architecture_health as run
    return run(root, schema, package_root=ROOT, archguard_load_schema=_archguard_load_schema)


def _archguard_normalized_lines(text, normalize_le=True, ignore_ws=True):
    from architecture_diagnostics import _archguard_normalized_lines as run
    return run(text, normalize_le, ignore_ws)


def _archguard_source_projection_pairs(root):
    from architecture_diagnostics import _archguard_source_projection_pairs as run
    return run(root)


def check_duplicate_code(root=None, schema=None):
    from architecture_diagnostics import check_duplicate_code as run
    return run(
        root, schema, package_root=ROOT, archguard_exclusion_match=_archguard_exclusion_match,
        archguard_load_schema=_archguard_load_schema, archguard_normalized_lines=_archguard_normalized_lines,
        archguard_source_projection_pairs=_archguard_source_projection_pairs,
    )


def check_technical_debt(root=None, schema=None):
    from architecture_diagnostics import check_technical_debt as run
    return run(
        root, schema, package_root=ROOT,
        archguard_default_root_residue=_product_policy("ARCHGUARD_DEFAULT_ROOT_RESIDUE"),
        archguard_hooks_rel=_product_policy("ARCHGUARD_HOOKS_REL"),
        archguard_ledger_rel=_product_policy("ARCHGUARD_LEDGER_REL"),
        archguard_load_schema=_archguard_load_schema,
        external_validation_canonical_hook_text=_external_validation_canonical_hook_text,
        external_validation_read_text=_external_validation_read_text,
        parse_markdown_table_rows=_parse_markdown_table_rows,
    )


def check_complexity(root=None, schema=None):
    from architecture_diagnostics import check_complexity as run
    return run(
        root, schema, package_root=ROOT, archguard_load_schema=_archguard_load_schema,
        archguard_severity=_archguard_severity, check_architecture_health=check_architecture_health,
    )


# ── FEAT-014 / RISK-049 ①: adapter claim→evidence level mapping ──────
#
# RISK-049 closure standard (1) (risk-log L49): user-facing adapter claims
# ("安装后 /governance 可用") must carry a machine-checkable claim→evidence
# level mapping. The defect class (RISK-049 ②): README claims exceeded the
# actually-verified range with no machine constraint — the plugin's own
# no-overclaim rule was not enforced on its adapter surface.
#
# Three evidence levels (aligned with the RISK-049 row + FIX-290 legacy
# facts: 2026-07-08 real-session adapter verification, 2026-09-05 isolated
# DSH_HOME re-verification on Windows, github:-form static reasoning):
#   live-session — verified in a real user session (real host + version);
#                  the annotation MUST cite an ISO verification date;
#   isolation    — re-verified in an isolated environment (redirected home /
#                  temp dir, zero real-home writes); MUST cite an ISO date;
#   static       — static/inspection or reasoning only, no execution
#                  evidence; the explicit label IS the disclosure
#                  (dates optional — "未验证" is a legal static detail).
#
# Annotation marker (machine-checked): 〔<level>: <detail>〕

# Claim registry: the dsh user-availability claim surface (RISK-049 ② —
# data, not heuristics; extend per adapter when new user-facing claims
# land). A registry line MUST carry ≥1 valid evidence-level marker.


def check_readme_claim_evidence_levels(readme_path=None):
    from host_loading_claims import check_readme_claim_evidence_levels as run
    return run(
        readme_path, package_root=ROOT, adapter_claim_registry=_host_policy('ADAPTER_CLAIM_REGISTRY'),
        evidence_level_marker_re=_host_policy('EVIDENCE_LEVEL_MARKER_RE'),
    )


def check_governance_data_size(root=None, schema=None):
    from architecture_diagnostics import check_governance_data_size as run
    return run(
        root, schema, host_project_root=HOST_PROJECT_ROOT, package_root=ROOT,
        archguard_load_schema=_archguard_load_schema, archguard_severity=_archguard_severity,
        archive_reader=_archive_reader,
    )


def _external_validation_plan_tracker(version):
    from external_project_validation import plan_tracker
    return plan_tracker(version)


def _write_external_validation_governance(workspace, target_facts):
    from external_project_validation import write_governance
    version = _extract_skill_version(ROOT / "skills/software-project-governance/SKILL.md")
    write_governance(workspace, target_facts, version or "unknown", _external_validation_plan_tracker)


def _copy_external_validation_surface(workspace):
    from external_project_validation import copy_surface
    return copy_surface(workspace, ROOT, _git_files(["ls-files", "--cached"]))


def _prepare_external_validation_git(workspace):
    from external_project_validation import prepare_git
    return prepare_git(workspace)


def _run_external_validation_command(workspace, args, timeout=120):
    from external_project_validation import run_command
    return run_command(workspace, args, timeout=timeout)


def _external_validation_target_native_diagnostics(target):
    from external_project_diagnostics import target_native_diagnostics
    return target_native_diagnostics(
        target, entry_files=_host_policy('EXTERNAL_PROJECT_NATIVE_ENTRY_FILES'),
        entry_patterns=_host_policy('EXTERNAL_PROJECT_NATIVE_ENTRY_PATTERNS'),
        required_hooks=_host_policy('EXTERNAL_PROJECT_REQUIRED_INSTALLED_HOOKS'),
        read_text=_external_validation_read_text, canonical_hook_text=_external_validation_canonical_hook_text)


def run_external_project_validation(target, keep_workspace=False, workspace_parent=None, timeout=120):
    import external_project_validation as validation
    return validation.validate_project(
        target, keep_workspace, workspace_parent, timeout, inspect_target=_external_validation_target_native_diagnostics,
        copy_surface=_copy_external_validation_surface,
        write_governance=_write_external_validation_governance,
        prepare_git=_prepare_external_validation_git,
        run_command=_run_external_validation_command,
        commands=_host_policy('EXTERNAL_PROJECT_VALIDATION_COMMANDS'), boundary=_host_policy('EXTERNAL_PROJECT_VALIDATION_BOUNDARY'),
    )


def cmd_external_project_validation(args):
    from external_project_validation import run_cli
    return run_cli(args, run_external_project_validation)


def cmd_e2e_check(_args):
    from product_fixture_validation import cmd_e2e_check as run
    return run(
        _args, plugin_root=PLUGIN_ROOT, package_root=ROOT, e2e_command_matrix=_e2e_command_matrix,
        e2e_contract_checks=_e2e_contract_checks,
        e2e_target_cwd_command_matrix=_e2e_target_cwd_command_matrix,
        e2e_target_fixture_checks=_e2e_target_fixture_checks, evaluate_e2e_command=_evaluate_e2e_command,
        evaluate_e2e_contract_check=_evaluate_e2e_contract_check,
        evaluate_e2e_target_fixture_check=_evaluate_e2e_target_fixture_check,
    )


# cmd_check_manifest_consistency moved to checks/manifest.py in 0.59.0
# (DEC-083 Phase 1 / REQ-102) and re-exported via the top-level import.


def cmd_check_agent_adapters(args):
    from host_validation_cli import cmd_check_agent_adapters as run
    return run(args, check_agent_adapter_contract=check_agent_adapter_contract)


def cmd_check_release(args):
    from release_validation_cli import cmd_check_release as run
    return run(args, check_release_readiness=check_release_readiness, write_cli_json=write_cli_json)


# ── Standalone CLI wrappers for new checks ────────────────────────

def cmd_check_cross_references(args):
    from governance_fact_cli import cmd_check_cross_references as run
    return run(args, check_cross_references=lambda: check_cross_references(),
               check_exploration_sample_advisories=lambda: check_exploration_sample_advisories())


def cmd_check_exploration_channels(args):
    from exploration_evidence import cmd_check_exploration_channels as run
    return run(args, check_exploration_channels=check_exploration_channels)


def cmd_check_loop_role_skills(_args):
    from host_validation_cli import cmd_check_loop_role_skills as run
    return run(_args, check_loop_role_skill_consistency=check_loop_role_skill_consistency)


def cmd_check_sequential_ids(args):
    from governance_fact_cli import cmd_check_sequential_ids as run
    return run(args, check_sequential_ids=check_sequential_ids)


def cmd_check_structural_validity(args):
    from governance_fact_cli import cmd_check_structural_validity as run
    return run(args, check_structural_validity=check_structural_validity)


def cmd_check_commit_scope(args):
    from governance_fact_cli import cmd_check_commit_scope as run
    return run(args, check_commit_scope=check_commit_scope)


def cmd_check_goal_alignment(args):
    from governance_fact_cli import cmd_check_goal_alignment as run
    return run(args, check_goal_alignment=check_goal_alignment)


def cmd_check_user_impact(args):
    from governance_fact_cli import cmd_check_user_impact as run
    return run(args, check_user_impact=check_user_impact)


# ── SYSGAP-037: check-agent-team subcommand ──────────────────────

def cmd_check_agent_team(args):
    from host_validation_cli import cmd_check_agent_team as run
    return run(args, check_agent_activation=check_agent_activation, check_agent_team_review=check_agent_team_review)


def cmd_check_version_consistency(_args):
    from repository_projection import cmd_check_version_consistency as run
    return run(_args, check_version_consistency=check_version_consistency)


def cmd_check_projection_sync(args):
    from repository_projection import cmd_check_projection_sync as run
    return run(
        args, check_projection_sync=check_projection_sync,
        check_entry_bootstrap_sync=lambda: projection_checks.check_entry_bootstrap_sync(),
        print_entry_bootstrap_report=lambda report: projection_checks.print_entry_bootstrap_report(report),
    )


cmd_check_entry_bootstrap_sync = projection_checks.cmd_check_entry_bootstrap_sync


def cmd_check_injection_contract(args):
    from repository_projection import cmd_check_injection_contract as run
    return run(args, check_injection_contract=check_injection_contract)


def cmd_check_dsh_preset_smoke(args):
    from host_loader_probes import cmd_check_dsh_preset_smoke as run
    return run(args, smoke=check_dsh_preset_smoke)


def cmd_check_dsh_preset_compat(args):
    from dsh_compat import cmd_check_dsh_preset_compat as run
    return run(args)


def cmd_check_dsh_boundary(args):
    from host_validation_cli import cmd_check_dsh_boundary as run
    return run(args)


def cmd_dsh_doctor(args):
    from host_validation_cli import cmd_dsh_doctor as run
    return run(args)


def cmd_release_ledger(args):
    from release_validation_cli import cmd_release_ledger as run
    return run(args)


def cmd_release_projection(args):
    from release_validation_cli import cmd_release_projection as run
    return run(args)


def cmd_quality_tools(_args):
    from release_validation_cli import cmd_quality_tools as run
    return run(_args)


def cmd_check_hot_fact_source(args):
    from governance_fact_cli import cmd_check_hot_fact_source as run
    return run(args,
               check_hot_fact_source_consistency=lambda *a, **kw: check_hot_fact_source_consistency(*a, **kw))


def cmd_check_runtime_readiness_matrix(args):
    from host_validation_cli import cmd_check_runtime_readiness_matrix as run
    return run(args, check_runtime_readiness_matrix=check_runtime_readiness_matrix)


def cmd_check_first_session_measurement(args):
    from host_validation_cli import cmd_check_first_session_measurement as run
    return run(args, check_first_session_measurement=check_first_session_measurement)


def cmd_check_governance_packs(args):
    from host_validation_cli import cmd_check_governance_packs as run
    return run(args, check_governance_packs=check_governance_packs)


# cmd_check_capability_registry moved to checks/capability_registry.py in 0.61.1
# (DEC-083 Phase 2 / REQ-103) and re-exported via the top-level import.


def cmd_check_lifecycle_registry(args):
    """Run dynamic lifecycle registry schema-only consistency guard."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    registry, load_issues = _load_lifecycle_registry()
    active_mode = registry.get("active_lifecycle_mode", "<unreadable>") if isinstance(registry, dict) else "<unreadable>"
    default_mode = registry.get("default_lifecycle_mode", "<unreadable>") if isinstance(registry, dict) else "<unreadable>"
    issues = load_issues or check_lifecycle_registry(registry=registry)
    print("\n=== Lifecycle Registry Check ===")
    print(f"  Active lifecycle mode: {active_mode}")
    print(f"  Default lifecycle mode: {default_mode}")
    if issues:
        print(f"  Result: FAILED — {len(issues)} issue(s)")
        for issue in issues[:20]:
            print(f"    - {issue}")
        if len(issues) > 20:
            print(f"    ... and {len(issues) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("  Result: PASSED — work-unit routes and evidence requirements resolve")
    print()


def cmd_check_flow_unit_runtime(args):
    """Validate the same project snapshot consumed by the session and dashboard."""
    from governance_readers import loop_state
    fixture = getattr(args, "fixture", None)
    root = (ROOT / Path(fixture)) if fixture else HOST_PROJECT_ROOT
    report = loop_state(root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["state"] == "invalid":
        sys.exit(2)


def cmd_check_host_capability_context(args):
    from status_cli import cmd_check_host_capability_context as read
    return read(
        args,
        plugin_root=ROOT,
        discover=discover_host_capability_context,
        validate=check_host_capability_context,
        display_path=_display_path,
    )


def cmd_check_mainstream_agent_loading(args):
    from host_validation_cli import cmd_check_mainstream_agent_loading as run
    return run(args, check_mainstream_agent_loading=check_mainstream_agent_loading)


# ── ArchGuard command handlers (REQ-101 / FIX-152 / 0.58.0, advisory-only) ─────
# 3-level PASS/WARN/ERROR model. G7: WARN/ERROR are advisory and do NOT fail the
# command (exit 0) unless gate_integration.fatal_on_error is true AND there are
# ERROR-level findings.

def _archguard_print_findings(title, result, hint_key='check'):
    from architecture_diagnostics import _archguard_print_findings as run
    return run(
        title, result, hint_key, exception_note=_exception_note,
        exception_registry_error_note=_exception_registry_error_note,
    )


def cmd_check_architecture_health(args):
    from architecture_diagnostics import cmd_check_architecture_health as run
    return run(
        args, host_project_root=HOST_PROJECT_ROOT, plugin_root=PLUGIN_ROOT,
        archguard_schema_rel=_product_policy("ARCHGUARD_SCHEMA_REL"),
        archguard_print_findings=_archguard_print_findings,
        check_architecture_health=check_architecture_health,
    )


def cmd_check_loop_health(args):
    """Thin entry — delegates to infra/loop_health.py (0.65.0 loop-engineering)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from loop_health import check_loop_health
    result = check_loop_health(getattr(args, "target", None) or HOST_PROJECT_ROOT)
    print("\n=== Loop Health Check (pause-point declarations) ===")
    findings = result.get("findings", [])
    for f in findings[:25]:
        print(f"  [{f.get('severity','?')}] {f.get('pause_point','')}: {f.get('message','')}")
    blocking = [f for f in findings if f.get("severity") == "FAIL"]
    print(f"\n  Result: {len(blocking)} BLOCKING, {len(findings)-len(blocking)} advisory")
    telemetry = result["telemetry"]
    print(f"  Loop observations: {telemetry['status']} (loop-telemetry --json)")
    if blocking and getattr(args, "fail_on_issues", False):
        sys.exit(1)


def _format_rollup(result):
    from bootstrap_aggregate import format_loop_lines

    print("\n".join(format_loop_lines(result)))
def _format_telemetry(report, json_out=False):
    from dataclasses import asdict
    if json_out:
        write_cli_json(asdict(report), indent=2)
        return
    print(f"Loop Telemetry ({report.window}): {report.units_considered} units, "
          f"{report.event_count} events")
    for name, metric in report.flow.items():
        value = f"{metric.value} {metric.unit}" if metric.status == "measured" else f"unknown ({metric.reason})"
        print(f"  {name}: {value}")
    for observation in report.observations:
        if "resolved_at" in observation and observation["resolved_at"] is None:
            print(f"  Waiting: {observation['unit_id']} since {observation['timestamp']}")
    print(report.scope_note)


def cmd_loop_rollup(args):
    """Thin entry — delegates to loop_engine.rollup_loop_state (FX-193)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from loop_engine import rollup_loop_state
    view = rollup_loop_state(getattr(args, "target", None) or HOST_PROJECT_ROOT)
    _format_rollup(view)
    if view.get("state") == "invalid":
        sys.exit(2)


def write_cli_json(payload, *, indent=None):
    """Write one JSON response from a governance command."""
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=indent)
    sys.stdout.write("\n")


def cmd_loop(args):
    from loop_workflow import run
    try:
        result = run(HOST_PROJECT_ROOT, args)
    except (OSError, ValueError) as exc:
        write_cli_json({"error": str(exc)})
        sys.exit(2)
    write_cli_json(result, indent=2)
    if result.get("state") == "invalid" or (args.action in ("verify", "accept") and result["decision"] in ("iterate", "escalate")):
        sys.exit(2)


def cmd_loop_telemetry(args):
    """Thin entry — delegates to infra/loop_telemetry.py (0.69.0 telemetry).

    Reads the event log via loop_event_log.read_events (RISK-040 HOST_PROJECT_ROOT,
    never PLUGIN_HOME) and delegates to loop_telemetry.compute_metrics. All logic
    lives in the pure module; this entry is argparse glue + 2 delegated calls
    (RISK-039 thin-entry discipline).
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from loop_event_log import read_events
    from loop_telemetry import compute_metrics
    root = getattr(args, "target", None) or HOST_PROJECT_ROOT
    log_path = Path(root) / ".governance" / "loop-event-log.jsonl" if root else None
    events = read_events(log_path=log_path) if log_path else []
    win = getattr(args, "window", None)
    # "all" maps to None (all-time) for the pure compute_metrics API.
    window = None if win in (None, "all") else win
    report = compute_metrics(events, window=window)
    _format_telemetry(report, json_out=getattr(args, "json", False))


# ── FIX-262 / REQ-108: completion-recommendation machine closure ─────────────
# Effective date: completion rows dated BEFORE this are legacy (the ~145
# completed tasks have no recommendation-snapshot association) and are never
# judged — same pattern as Check 30c's REQ107_MACHINE_PROVENANCE_DATE.
REQ108_RECOMMENDATION_DATE = date(2026, 8, 22)

# Machine-source marker (mirrors the review-record/change-triage precedent:
# the unforgeable-ish machine row is the trusted association anchor). Mirror
# of the canonical task_priority.RECO_ROW_MARKER (FEAT-012 G5 moved the
# writer there; this copy feeds Check 34's consumer logic).
RECO_ROW_MARKER = "task-priority-analysis 机器写入完成必推荐调用快照"
_LEGACY_SNAPSHOT_MARKER = "完成必推荐调用快照"
_RECO_TASK_ID_RE = re.compile(r"^[A-Z]+-\d+$")
_SNAPSHOT_REF_RE = re.compile(r"(?:RECO-[A-Z]+-\d+|EVD-\d+)")
from hot_governance_facts import _TASK_ID_IN_REF_RE, _TASK_ID_CELL_RE, _EVIDENCE_DATE_SHAPE_RE


def _recommendation_snapshot_row_text(task_id, report, date_str):
    """FIX-262 row text — thin alias; canonical home is
    task_priority.recommendation_snapshot_row_text (moved there by FEAT-012
    G5 so the writer, duplicate detector and row schema live in one module;
    alias kept for existing engine/test consumers)."""
    from task_priority import recommendation_snapshot_row_text
    return recommendation_snapshot_row_text(task_id, report, date_str)


def _write_recommendation_snapshot(task_id, report, evidence_path=None):
    """FIX-262 append — thin alias; canonical home is
    task_priority.write_recommendation_snapshot (FEAT-012 G5). Supplies the
    rebinding-aware EVIDENCE_PATH default the pure module cannot know."""
    from task_priority import write_recommendation_snapshot
    return write_recommendation_snapshot(
        task_id, report,
        evidence_path if evidence_path is not None else EVIDENCE_PATH)


def check_completion_recommendation(evidence_rows=None, snapshot_text=None):
    """FIX-262 / REQ-108: Check 34 — completion-recommendation closure.

    S1 (core, FAIL): a product-code COMPLETION evidence row (id ``EVD-*``,
    type ``产品代码``) dated on/after ``REQ108_RECOMMENDATION_DATE`` whose
    task has no associated recommendation-snapshot row. Association = a
    machine ``RECO-{task}`` row (marker ``task-priority-analysis 机器写入``)
    OR a legacy snapshot row (description marker ``完成必推荐调用快照``)
    whose task_ref column or “{task} 完成触发” description binds the task.

    S2 (WARN, gradual): the session-snapshot ``## 下次会话优先级`` section
    has entries but references no snapshot id (``RECO-*`` / ``EVD-*``) —
    the section is not verifiably derived from a snapshot (signal 4).

    S3 (FAIL): a referenced snapshot id does not exist in the evidence log
    (dangling derivation anchor).

    Returns ``{verdict, reason, violations, warnings, stats}``; verdict ∈
    PASS / WARN / FAIL / no-verdict. Never raises.
    """
    result = {
        "verdict": "no-verdict",
        "reason": "",
        "violations": [],
        "warnings": [],
        "stats": {"completions_judged": 0, "snapshots_machine": 0,
                  "snapshots_legacy": 0, "snapshot_section": "absent"},
    }

    rows = evidence_rows
    if rows is None:
        rows = []
        if EVIDENCE_PATH.is_file():
            try:
                content = EVIDENCE_PATH.read_text(encoding="utf-8")
            except (IOError, OSError):
                content = ""
            rows = [ln for ln in content.split("\n") if ln.strip().startswith("|")]

    if snapshot_text is None:
        snapshot_text = ""
        # Live snapshot read ONLY in full live mode (evidence_rows also None):
        # a rows-fixture run without an explicit snapshot_text means "no
        # snapshot section to judge", not "read the repo's live snapshot".
        if evidence_rows is None and SESSION_SNAPSHOT_PATH.is_file():
            try:
                snapshot_text = SESSION_SNAPSHOT_PATH.read_text(encoding="utf-8")
            except (IOError, OSError):
                snapshot_text = ""

    def _row_date(parts):
        for part in parts[3:]:
            if re.match(r"^\d{4}-\d{2}-\d{2}$", part):
                try:
                    return date.fromisoformat(part)
                except ValueError:
                    return None
        return None

    # Pass 1: collect snapshot associations + evidence ids.
    known_ids = set()
    assoc = set()  # task ids that have a snapshot association
    for raw in rows:
        parts = [p.strip() for p in str(raw or "").split("|")]
        if len(parts) < 5:
            continue
        row_id = parts[1]
        if row_id:
            known_ids.add(row_id)
        desc = parts[4] if len(parts) > 4 else ""
        is_machine = row_id.startswith("RECO-") and RECO_ROW_MARKER in desc
        is_legacy = _LEGACY_SNAPSHOT_MARKER in desc
        if not (is_machine or is_legacy):
            continue
        if is_machine:
            result["stats"]["snapshots_machine"] += 1
        else:
            result["stats"]["snapshots_legacy"] += 1
        # task_ref column binding (parts[2]) — may carry "FIX-260, FIX-261".
        for tid in _TASK_ID_IN_REF_RE.findall(parts[2] or ""):
            assoc.add(tid)
        # description trigger binding（"FIX-256 完成触发" — EVD-898 pattern).
        for tid in _TASK_ID_IN_REF_RE.findall(desc):
            if "{0} 完成触发".format(tid) in desc:
                assoc.add(tid)
        # machine row id binding: RECO-{task}.
        if is_machine:
            m = re.match(r"^RECO-([A-Z]+-\d+)$", row_id)
            if m:
                assoc.add(m.group(1))

    # Pass 2: completion rows → S1.
    for raw in rows:
        parts = [p.strip() for p in str(raw or "").split("|")]
        if len(parts) < 5:
            continue
        row_id = parts[1]
        if not row_id.startswith("EVD-"):
            continue  # REVIEW-/TRIAGE-/RECO- rows are not completion rows.
        if (parts[3] if len(parts) > 3 else "") != "产品代码":
            continue
        row_date = _row_date(parts)
        if row_date is None or row_date < REQ108_RECOMMENDATION_DATE:
            continue
        result["stats"]["completions_judged"] += 1
        for tid in _TASK_ID_IN_REF_RE.findall(parts[2] or ""):
            if tid not in assoc:
                result["violations"].append({
                    "rule": "S1",
                    "task_id": tid,
                    "reason": "completed product-code task {0} (evidence "
                              "{1}, {2}) has no recommendation-snapshot "
                              "row — M7.4 step 6 requires the "
                              "task-priority-analysis snapshot (machine "
                              "RECO row via --evidence-task, or a "
                              "完成必推荐调用快照 row)".format(
                                  tid, row_id, row_date.isoformat()),
                })

    # Signal 4: snapshot section derivation (S2/S3).
    section_lines = []
    in_section = False
    for line in (snapshot_text or "").split("\n"):
        if line.strip().startswith("## "):
            in_section = line.strip() == "## 下次会话优先级"
            continue
        if in_section and line.strip():
            section_lines.append(line.strip())
    if section_lines:
        result["stats"]["snapshot_section"] = "present"
        blob = "\n".join(section_lines)
        refs = set(_SNAPSHOT_REF_RE.findall(blob))
        if not refs:
            result["warnings"].append({
                "rule": "S2",
                "task_id": "",
                "reason": "session-snapshot ## 下次会话优先级 has entries but "
                          "references no snapshot id (RECO-*/EVD-*) — not "
                          "verifiably derived from a recommendation snapshot "
                          "(REQ-108 signal 4; gradual WARN)",
            })
        else:
            dangling = sorted(r for r in refs if r not in known_ids)
            if dangling:
                result["violations"].append({
                    "rule": "S3",
                    "task_id": "",
                    "reason": "snapshot section references missing evidence "
                              "id(s): {0} — dangling derivation anchor".format(
                                  ", ".join(dangling)),
                })

    if result["violations"]:
        result["verdict"] = "FAIL"
        result["reason"] = "{0} completion-recommendation violation(s)".format(
            len(result["violations"]))
    elif result["warnings"]:
        result["verdict"] = "WARN"
        result["reason"] = "{0} derivation warning(s)".format(
            len(result["warnings"]))
    elif result["stats"]["completions_judged"] == 0:
        result["verdict"] = "no-verdict"
        result["reason"] = (
            "no product-code completion row dated on/after {0} — Check 34 "
            "has nothing to judge".format(
                REQ108_RECOMMENDATION_DATE.isoformat()))
    else:
        result["verdict"] = "PASS"
        result["reason"] = (
            "{0} completion(s) all carry recommendation snapshots".format(
                result["stats"]["completions_judged"]))
    return result


def cmd_task_priority_analysis(args):
    """Thin entry — delegates to infra/task_priority.py (FIX-226 / FEAT-012 G5).

    Reads .governance paths via HOST_PROJECT_ROOT (never PLUGIN_HOME;
    RISK-040 dual-root discipline) and delegates the WHOLE flow — parse →
    compute → format, the FIX-262 RECO snapshot append, cycle tolerance
    (FIX-237.3: default exit 0 + WARNING banner; ``--strict`` restores the
    fail-closed exit 1), and the FEAT-012 G5 same-session duplicate-run
    suppression (same-day + unchanged-tracker runs reuse the cached report
    「复用上次分析（--force 重跑）」; a duplicate same-day RECO row is not
    re-appended; FIRST-TIME closures are never suppressed — FIX-262 /
    REQ-108) — to the pure task_priority module. This entry is argparse
    glue only (RISK-039 thin-entry discipline + ArchGuard R1 main-file
    budget). Exits 2 on a missing plan-tracker or a parse error.
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from task_priority import run_cli_analysis
    code = run_cli_analysis(
        SAMPLE_PATH, GOVERNANCE_DIR, EVIDENCE_PATH,
        evidence_task=getattr(args, "evidence_task", None),
        force=bool(getattr(args, "force", False)),
        strict=bool(getattr(args, "strict", False)),
    )
    if code:
        sys.exit(code)


def cmd_review_record(args):
    """Thin entry — review-record CLI (FIX-236.1 / ADR-017 §3.4 Wiring A).

    Delegates to infra/review_record.py: the single machine-written
    review-conclusion persistence path (review-{id}-R{n}.md + evidence-log
    row) + best-effort process_gate_result wiring. Prints the JSON summary;
    exits 2 on a fail-closed input error (the record was not written).
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from review_record import write_review_record
    summary = write_review_record(
        task_id=args.task,
        round_n=args.round,
        result=args.result,
        report_path=args.report,
        reviewer=args.reviewer,
        unit_id=args.unit,
        gate_id=args.gate,
        scope=getattr(args, "scope", "full"),
        delta_base=getattr(args, "delta_base", None),
        bind_files=getattr(args, "bind_file", None) or (), bind_tree=getattr(args, "bind_tree", None),
        abort_reason=getattr(args, "abort_reason", None),
        root=HOST_PROJECT_ROOT,
        require_loop=True, record_only=getattr(args, "record_only", False),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary.get("error"):
        sys.exit(2)


def cmd_next_candidates(args):
    """Read goal-scoped recommendations or the legacy loop_exit snapshot."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    # Goal mode reads the live sources. The legacy path below may persist a
    # recommendation snapshot based on loop-exit events.
    if getattr(args, "goal", None) is not None:
        from goal_planning import run_goal_candidates
        return run_goal_candidates(args, project_root=HOST_PROJECT_ROOT, load_packets=_load_execution_packets)
    from loop_exit_bridge import (
        CANDIDATES_FILENAME,
        read_candidates,
        refresh_candidates,
    )
    snapshot = HOST_PROJECT_ROOT / ".governance" / CANDIDATES_FILENAME
    report = None
    if not getattr(args, "refresh", False):
        report = read_candidates(snapshot)
    if report is None:
        report = refresh_candidates(
            HOST_PROJECT_ROOT,
            top_n=getattr(args, "top_n", 3) or 3,
            candidate_path=snapshot if getattr(args, "write", False) else None,
        )
    # FIX-463: inject the collapsed-premise verdict (read-only; DEC-368②
    # class) — a collapsed decision must surface in the next-unit bridge
    # too, not only in the full TPA report. Additive key: consumers that
    # do not know it are unaffected.
    try:
        _dec_log = HOST_PROJECT_ROOT / ".governance" / "decision-log.md"
        _decls = premise_tracker.collect_premise_declarations(
            _dec_log.read_text(encoding="utf-8")
            if _dec_log.is_file() else "")
        if _decls:
            _events = premise_tracker.load_events(
                HOST_PROJECT_ROOT / ".governance")
            _status = premise_tracker.premise_status(_decls, _events)
            if isinstance(report, dict):
                report["collapsed_premises"] = [
                    dict(_status["detail"][d], decision_id=d)
                    for d in _status["collapsed"]]
    except (OSError, ValueError, TypeError):
        pass  # the bridge stays additive — never block the candidate read
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _triage_write_structure_guard(evidence_path, record_path, record_id=None):
    from write_guard_records import _triage_write_structure_guard as inspect
    return inspect(evidence_path, record_path, record_id)


# ── FEAT-011 / G3 extension: Coordinator direct-write path guard ──────────

# Evidence-log machine-written row families (uniform column contract). The
# TRIAGE family is the DEC-168 authority (10 cols incl. the files cell,
# change_triage._evidence_row); RECO rows are machine-written by
# task-priority-analysis --evidence-task (same writer discipline). Manual
# families (EVD/REVIEW legacy 9/10/11-col mix) stay in Check 14's WARN domain.
_EVIDENCE_MACHINE_ROW_FAMILIES = ("TRIAGE", "RECO")

_PLAN_TRACKER_ROW_EXPECTED_SHAPE = (
    "| 优先级 | 任务ID | 标题 | 依赖 | 目标版本 | 闭环路径 | 状态 |"
    "（优先级恰一列且居于任务ID 之前；末列为状态列且必须非空；"
    "行尾不得追加空单元格——AUDIT-149 §4 M1）")


def _plan_tracker_task_row_issues(content):
    from write_guard_records import _plan_tracker_task_row_issues as inspect_rows
    return inspect_rows(
        content,
        expected_shape=_PLAN_TRACKER_ROW_EXPECTED_SHAPE,
        task_id_pattern=_TASK_ID_CELL_RE,
        normalize_priority=_normalize_priority,
    )


def _evidence_machine_row_issues(content):
    from write_guard_records import _evidence_machine_row_issues as inspect_rows
    return inspect_rows(content, machine_families=_EVIDENCE_MACHINE_ROW_FAMILIES)


_WRITE_GUARD_STATE_FILENAME = ".write-guard-state.json"
_WRITE_GUARD_STATE_SCHEMA_VERSION = 1
_WRITE_GUARD_STATE_TOOL = "governance-write-guard/row-family-reconciliation"

# Stable writer prefix of the governance_store provenance marker
# (``（机器写入：governance-store evidence-append op-…；schema vN）`` /
#  ``（机器写入：governance-store decision-append op-…；schema vN）`` —
# governance_store._build_evidence_row / _build_decision_row).

# FIX-390 (DEC-241 消解, 0.89.0) — the Check 18b machine-attestation
# credential for DEC-168 machine row-family EVIDENCE rows: the writer's own
# evidence-append marker with a well-formed op receipt anchor. Consumed, not
# re-stated (FIX-292 lesson): the prefix comes from the constant above (its
# drift is bound to really-built rows by the guard tests), and the op-anchor
# shape mirrors the writer's ``op-<32hex>`` receipt id. Authenticity
# enforcement (column shape + row-family reconciliation against the ops
# ledger) lives in governance-write-guard faces 2/5 — Check 18b only consumes
# the credential shape and never re-implements the ledger check. A marker
# with a malformed/truncated op id (or a foreign writer's marker) does NOT
# attest — 未知不猜.


def _row_has_governance_store_machine_credential(raw_line):
    from write_guard_records import _row_has_governance_store_machine_credential as has_receipt
    return has_receipt(raw_line, receipt_pattern=_host_policy("_EVIDENCE_MACHINE_CREDENTIAL_RE"))

# ops-ledger receipt anchor: task_row_update receipt lines carry the
# operation id under this key (task_row_update.RECEIPT_RECORD_KIND face).
_OPS_LEDGER_RECEIPT_ANCHOR = "operation_id"

_ROW_FAMILY_TEXT_SURFACES = ("evidence-log.md", "decision-log.md",
                             "plan-tracker.md")

# FEAT-081 / ADR-021 §3.2.1 B4: the M2 deferred-registration observation
# ledger — a guard-owned artifact (same class as the state baseline /
# violation ledger, FEAT-057/060 contract), append-only JSONL, written on
# the guard CLI face ONLY (cmd_governance_write_guard — the post-commit
# hook path; the converge/internal persist paths and probes never create
# it, keeping the rel089 "converge writes only guard state artifacts"
# compatibility contract byte-true). Three-key buckets:
# 命中词 × 行族 × 否定语境命中 — the RT-5 container the WARN→FAIL flip
# decision owes its false-positive report to. Judgement pieces live in
# checks/loop_gate_processor.py (pure leaf; the "loop" there is the
# discovery→closure loop of ADR-021 M2, NOT the ADR-014 PARO runtime
# module of the same basename at infra/ level).
_DEFERRED_LEDGER_FILENAME = ".write-guard-deferred-ledger.jsonl"


def _write_guard_row_digest(text):
    from write_guard_records import _write_guard_row_digest as digest
    return digest(text)


def _extract_managed_row_records(surface, content):
    from write_guard_records import _extract_managed_row_records as extract_rows
    return extract_rows(surface, content, task_id_pattern=_TASK_ID_CELL_RE)


def _extract_ops_ledger_records(content):
    from write_guard_records import _extract_ops_ledger_records as extract_receipts
    return extract_receipts(content)


def _row_family_credential_ok(surface, row_key, row_text):
    from write_guard_records import _row_family_credential_ok as has_receipt
    return has_receipt(
        surface, row_key, row_text,
        review_marker=REVIEW_MACHINE_ROW_MARKER,
        store_prefix=_host_policy("_GOVERNANCE_STORE_MARKER_PREFIX"),
        operation_anchor=_OPS_LEDGER_RECEIPT_ANCHOR,
    )


def _load_write_guard_state(governance_dir):
    from write_guard_state import _load_write_guard_state as load_state
    return load_state(
        governance_dir,
        filename=_WRITE_GUARD_STATE_FILENAME,
        version=_WRITE_GUARD_STATE_SCHEMA_VERSION,
        tool=_WRITE_GUARD_STATE_TOOL,
    )


def _stamp_deferred_observation(observation):
    from write_guard_reconciliation import _stamp_deferred_observation as stamp
    return stamp(observation)


def _reconcile_row_families(governance_dir, persist_state=False, detections_out=None, records_index_out=None, deferred_out=None):
    from write_guard_reconciliation import RowInspection, _reconcile_row_families as reconcile
    return reconcile(
        governance_dir, persist_state, detections_out, records_index_out, deferred_out,
        inspect=RowInspection(_extract_managed_row_records, _credential_index, _judge_row_delta),
        load_baseline=_load_write_guard_state, baseline_exists=state_path_seen,
        surfaces=_ROW_FAMILY_TEXT_SURFACES, schema_version=_WRITE_GUARD_STATE_SCHEMA_VERSION,
        tool=_WRITE_GUARD_STATE_TOOL, now=datetime.now,
    )


def state_path_seen(governance_dir):
    """True when the reconciliation state file exists (surface seen even
    with all managed files gone — the state must shrink, not vanish)."""
    return (governance_dir / _WRITE_GUARD_STATE_FILENAME).is_file()


def _write_guard_state_json(baseline_state):
    """THE serialization of the reconciliation baseline state file —
    delegated to ``write_guard_state.state_json_text`` (single serializer:
    the FEAT-060 consumption transaction's resume sha256 comparisons judge
    these exact bytes, so a second serializer here would be a FIX-292-class
    second shape source)."""
    import write_guard_state
    return write_guard_state.state_json_text(baseline_state)


def _rows_snapshot(records):
    from write_guard_reconciliation import _rows_snapshot as snapshot
    return snapshot(records)


def _credential_index(surface, records, surface_kind='text'):
    from write_guard_reconciliation import _credential_index as index
    return index(surface, records, surface_kind, has_receipt=_row_family_credential_ok)


def _judge_row_delta(surface, rel, records, baseline_rows, issues, surface_kind='text', detections_out=None, family_postures=None, honored_families=frozenset(), deferred_out=None, observation=None):
    from write_guard_reconciliation import _judge_row_delta as judge
    return judge(surface, rel, records, baseline_rows, issues, surface_kind, detections_out, family_postures, honored_families, deferred_out, observation, has_receipt=_row_family_credential_ok)


def _build_violation_detection(surface, surface_kind, rel, record, before_hash=None):
    from write_guard_reconciliation import _build_violation_detection as build_detection
    return build_detection(surface, surface_kind, rel, record, before_hash)


def check_governance_write_shapes(*, persist_state=False, session_id=None, deferred_ledger=False):
    from governance_write_shapes import StructureChecks, check_governance_write_shapes as inspect
    checks = StructureChecks(
        _plan_tracker_task_row_issues, _evidence_machine_row_issues, check_agent_locks_format,
        _load_execution_packets, _execution_packet_field_issues,
    )
    return inspect(
        GOVERNANCE_DIR, SAMPLE_PATH, ROOT, checks=checks, pin_ledger=pin_ledger,
        reconcile=_reconcile_row_families, state_filename=_WRITE_GUARD_STATE_FILENAME,
        deferred_filename=_DEFERRED_LEDGER_FILENAME, encode_baseline=_write_guard_state_json,
        persist_state=persist_state, session_id=session_id, deferred_ledger=deferred_ledger,
    )


def cmd_change_triage(args):
    from change_triage import cmd_change_triage as run
    return run(
        args,
        host_root=HOST_PROJECT_ROOT,
        governance_dir=GOVERNANCE_DIR,
        plan_path=SAMPLE_PATH,
        read_task_rows=parse_task_table_rows,
        check_write=_triage_write_structure_guard,
        output_json=write_cli_json,
    )



def cmd_demand_source_revise(args):
    from change_triage import cmd_demand_source_revise as run
    return run(args, governance_dir=GOVERNANCE_DIR)


def cmd_agent_locks_acquire(args):
    """Thin entry — agent-locks-acquire CLI (FEAT-013 / RISK-046 root fix).

    All validation and writing live in
    :func:`change_triage.acquire_dispatch_locks` (RISK-039 thin-entry
    discipline): pre-write path existence + expected-new exemption +
    same-day change-triage files cross-check (mismatch WARN-disclosed,
    never blocking). This glue injects the host paths and the Check 26
    post-write self-validation — the writer proves its own output
    against the SAME schema the FEAT-011 write guard consumes (no second
    schema definition). Exit 0 = written (WARNs may accompany on stderr);
    exit 2 = fail-closed refusal (nothing written).
    """
    from change_triage import agent_locks_acquire_cli
    agent_locks_acquire_cli(
        args, governance_dir=GOVERNANCE_DIR, repo_root=HOST_PROJECT_ROOT,
        post_write_check=check_agent_locks_format)


# ── FEAT-096 (0.98.0): execution-isolation engine thin entries ─────────
#
# All validation and writing live in execution_isolation.py (RISK-039
# thin-entry discipline).  These glue entries inject the ENGINE-resolved
# host paths (read at call time so an explicit --project-root override
# applies — the cmd_agent_locks_acquire pattern) and return the module's
# exit code (0 ok / 2 refusal; judge's allowed=false also exits 2).


def cmd_isolation_write_engine(args):
    """Thin entry — isolation-write CLI (FEAT-096 ① write slot)."""
    return cmd_isolation_write(
        args, governance_dir=GOVERNANCE_DIR, repo_root=HOST_PROJECT_ROOT)


def cmd_isolation_snapshot_engine(args):
    """Thin entry — isolation-snapshot CLI (FEAT-096 ②③ review snapshot)."""
    return cmd_isolation_snapshot(
        args, governance_dir=GOVERNANCE_DIR, repo_root=HOST_PROJECT_ROOT)


def cmd_isolation_lease_reclaim_engine(args):
    """Thin entry — isolation-lease-reclaim CLI (FEAT-096 ④ 失权回收)."""
    return cmd_isolation_lease_reclaim(
        args, governance_dir=GOVERNANCE_DIR, repo_root=HOST_PROJECT_ROOT)


def cmd_isolation_status_engine(args):
    """Thin entry — isolation-status CLI (machine-readable world)."""
    return cmd_isolation_status(
        args, governance_dir=GOVERNANCE_DIR, repo_root=HOST_PROJECT_ROOT)


def cmd_isolation_capability_engine(args):
    """Thin entry — isolation-capability CLI (honesty disclosure)."""
    return cmd_isolation_capability(
        args, governance_dir=GOVERNANCE_DIR, repo_root=HOST_PROJECT_ROOT)


# FEAT-097 (0.98.0): goal-bridge engine thin entry — all validation and
# writing live in goal_bridge.py (RISK-039 thin-entry discipline); this
# glue injects the ENGINE-resolved governance dir (read at call time so
# an explicit --project-root override applies) and returns the module's
# exit code (0 ok / 2 refusal; judge's any_danger also exits 2).


def cmd_goal_bridge_engine(args):
    """Thin entry — goal-bridge CLI (all actions)."""
    return cmd_goal_bridge(args, governance_dir=GOVERNANCE_DIR)


# FEAT-095 (0.98.0): enforcement engine thin entry — all validation and
# record-writing live in enforcement.py (RISK-039 thin-entry
# discipline); this glue injects the ENGINE-resolved governance dir
# (read at call time so an explicit --project-root override applies)
# and returns the module's family exit code (0 allow / 2 hard block
# incl. fail-closed / 3 throttle / 4 stale notice; switch off = 0 with
# zero side effects — zero drift vs the advisory baseline).


def cmd_enforcement_check_engine(args):
    """Thin entry — enforcement-check CLI (FEAT-095 six boundaries)."""
    return cmd_enforcement_check(
        args, governance_dir=GOVERNANCE_DIR, repo_root=HOST_PROJECT_ROOT)


def cmd_governance_write_guard(args):
    from write_guard_cli import cmd_governance_write_guard as run
    return run(args, governance_dir=GOVERNANCE_DIR, check_shapes=check_governance_write_shapes)


_BOOTSTRAP_CHECK_TOOL = "governance-write-guard/release-bootstrap-check"


def check_release_bootstrap_world():
    from release_bootstrap import check_release_bootstrap_world as inspect_world
    return inspect_world(
        governance_dir=GOVERNANCE_DIR,
        tool=_BOOTSTRAP_CHECK_TOOL,
        baseline_filename=_WRITE_GUARD_STATE_FILENAME,
        load_baseline=_load_write_guard_state,
        reconcile=_reconcile_row_families)


def run_release_bootstrap_converge():
    from release_bootstrap import run_release_bootstrap_converge as converge
    return converge(check_shapes=check_governance_write_shapes, check_world=check_release_bootstrap_world)


def cmd_write_guard_bootstrap(args):
    from release_bootstrap import cmd_write_guard_bootstrap as run
    return run(args, check_world=check_release_bootstrap_world, converge=run_release_bootstrap_converge)


def cmd_check_duplicate_code(args):
    from architecture_diagnostics import cmd_check_duplicate_code as run
    return run(args, archguard_print_findings=_archguard_print_findings, check_duplicate_code=check_duplicate_code)


def cmd_check_technical_debt(args):
    from architecture_diagnostics import cmd_check_technical_debt as run
    return run(args, archguard_print_findings=_archguard_print_findings, check_technical_debt=check_technical_debt)


def cmd_check_complexity(args):
    from architecture_diagnostics import cmd_check_complexity as run
    return run(args, archguard_print_findings=_archguard_print_findings, check_complexity=check_complexity)


def cmd_check_governance_data_size(args):
    from architecture_diagnostics import cmd_check_governance_data_size as run
    return run(
        args, archguard_print_findings=_archguard_print_findings,
        check_governance_data_size=check_governance_data_size,
    )


def cmd_check_readme_pack_guidance(args):
    from host_validation_cli import cmd_check_readme_pack_guidance as run
    return run(args, check_readme_pack_guidance=check_readme_pack_guidance)


def cmd_check_governance_pack_status(args):
    from host_validation_cli import cmd_check_governance_pack_status as run
    return run(args, check_governance_pack_status=check_governance_pack_status)


def cmd_check_product_success_contracts(args):
    from delivery_contract_cli import run_contract_check
    run_contract_check(
        args, check_product_success_contracts, title="Product Success Contract Check",
        count_label="Required active P0/P1 contract(s)", success="product success contracts are ready",
    )
    render_rb2_goal_contract_block()


def cmd_check_acceptance_contracts(args):
    from delivery_contract_cli import run_contract_check
    run_contract_check(
        args, check_acceptance_contracts, title="Executable Acceptance Contract Check",
        count_label="Required active P0/P1 acceptance contract(s)", success="executable acceptance contracts are ready",
    )


def cmd_check_quality_budget(args):
    from delivery_contract_cli import run_contract_check
    run_contract_check(
        args, check_quality_budget, title="Quality Budget Check",
        count_label="Required active P0/P1 quality budget(s)", success="quality budgets are ready",
    )


def cmd_check_vertical_slices(args):
    from delivery_contract_cli import run_contract_check
    run_contract_check(
        args, check_vertical_slices, title="Vertical Slice Check",
        count_label="Required active P0/P1 vertical slice(s)", success="vertical slice packets are ready",
    )


def cmd_check_deterministic_scaffolds(args):
    from delivery_contract_cli import run_contract_check
    run_contract_check(
        args, check_deterministic_scaffolds, title="Weak-LLM Deterministic Scaffold Check",
        count_label="Required scaffold type(s)", success="deterministic scaffolds are ready",
        required="required_types", entry_key="scaffold_type",
    )


def cmd_check_interruption_policy(args):
    from delivery_contract_cli import run_interruption_check
    run_interruption_check(args, check_interruption_policy)


def cmd_generate_deterministic_scaffold(args):
    from delivery_contract_cli import generate_scaffold
    generate_scaffold(args, render_deterministic_scaffold)


def _web_console_url(host="127.0.0.1", port=5173):
    return f"http://{host}:{port}/"


_WEB_INSTALL_TIMEOUT_DEFAULT = 120
_WEB_INSTALL_TIMEOUT_ENV = "SPG_WEB_INSTALL_TIMEOUT"


def _resolve_positive_timeout(raw, default):
    """Shared FIX-234-style env-var timeout resolution.

    Positive integer seconds win; absent/invalid values fall back to the
    supplied default (never crashes the caller).
    """
    raw = (raw or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _resolve_web_install_timeout(raw):
    """FIX-238.4: resolve the web-console npm install timeout.

    SPG_WEB_INSTALL_TIMEOUT (positive integer seconds, default 120s) with
    invalid values falling back to the default (FIX-234 precedent).
    """
    return _resolve_positive_timeout(raw, _WEB_INSTALL_TIMEOUT_DEFAULT)


def _web_console_is_live(url, timeout=1.5):
    return _web_console_probe(url, timeout=timeout)["state"] == "running"


def _web_console_probe(url, timeout=1.5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read(65536).decode("utf-8", errors="replace")
            if 'name="spg-web-console"' in body and "software-project-governance" in body:
                return {"state": "running", "status": response.status}
            return {"state": "occupied", "status": response.status}
    except Exception as exc:
        return {"state": "not_running", "error": str(exc)}


def _web_console_paths():
    web_dir = ROOT / "web"
    return {
        "web_dir": web_dir,
        "package_json": web_dir / "package.json",
        "node_modules": web_dir / "node_modules",
        "log": web_dir / "web-dev.log",
        "pid": web_dir / ".spg-web-console.pid",
    }


def _write_web_console_process(paths, process):
    try:
        paths["pid"].write_text(str(process.pid), encoding="utf-8")
    except OSError:
        pass


def cmd_web_console(args):
    """Expose the optional local Web console through the primary CLI/client path."""
    paths = _web_console_paths()
    url = _web_console_url(args.host, args.port)
    if getattr(args, "governance_entry", False):
        args.start = True

    print("Software Project Governance Web Console")
    print("Role: optional local companion dashboard")
    print("Primary interface remains: CLI / agent client")
    print(f"URL: {url}")
    print(f"Web directory: {_display_path(paths['web_dir'])}")
    probe = _web_console_probe(url)

    if args.summary_link and args.start:
        print("\nStatus: blocked")
        print("Reason: --summary-link is read-only and cannot be combined with a start path.")
        print("Boundary: summaries may report Web console status, while manual /governance uses --governance-entry to start or reuse it.")
        if args.fail_on_issues:
            sys.exit(1)
        return

    if not paths["package_json"].is_file():
        print("\nStatus: unavailable")
        print("Reason: web/package.json is missing in this checkout.")
        print("Boundary: this command does not replace /governance or run agent tasks.")
        if args.fail_on_issues:
            sys.exit(1)
        return

    if args.summary_link:
        if probe["state"] == "running":
            print(f"\nWeb console: {url} (optional local companion dashboard)")
        elif probe["state"] == "occupied":
            print(f"\nWeb console: unavailable at {url} (port is occupied by a non-SPG service).")
            print("Manual start command: python skills/software-project-governance/infra/verify_workflow.py web-console --start --port <free-port>")
            if args.fail_on_issues:
                sys.exit(1)
        else:
            print("\nWeb console: not running.")
            print("Manual start command: python skills/software-project-governance/infra/verify_workflow.py web-console --start")
        print("Boundary: summary link only; no Web service was started.")
        return

    if args.status and not args.start:
        if probe["state"] == "occupied":
            print("\nStatus: port occupied by a non-SPG service")
            print("Action: choose another port with --port, or stop the service using this port.")
            if args.fail_on_issues:
                sys.exit(1)
            return
        print("\nStatus:", "running" if probe["state"] == "running" else "not running")
        print("\nManual start command:")
        print(
            "python skills/software-project-governance/infra/verify_workflow.py "
            "web-console --start"
        )
        print("\nFirst run with dependency install:")
        print(
            "python skills/software-project-governance/infra/verify_workflow.py "
            "web-console --start --install"
        )
        print("\n/governance entry command:")
        print(
            "python skills/software-project-governance/infra/verify_workflow.py "
            "web-console --governance-entry"
        )
        print("\nBoundary: manual /governance starts or reuses the Web console for follow-up UI interaction; task/session summaries remain read-only with --summary-link.")
        return

    if not args.start:
        if probe["state"] == "occupied":
            print("\nStatus: port occupied by a non-SPG service")
            print("Use --port to select another local port.")
            if args.fail_on_issues:
                sys.exit(1)
            return
        print("\nStatus:", "running" if probe["state"] == "running" else "not running")
        print("Manual start command: python skills/software-project-governance/infra/verify_workflow.py web-console --start")
        return

    if probe["state"] == "occupied":
        print("\nStatus: blocked")
        print("Reason: the target port is serving a non-SPG page.")
        print("Action: use --port to select another local port, or stop the other service.")
        if args.fail_on_issues:
            sys.exit(1)
        return

    if probe["state"] == "running":
        print("\nStatus: already running")
        if getattr(args, "governance_entry", False):
            print("Entry: manual /governance reused the running Web console.")
        if args.open:
            webbrowser.open(url)
        return

    npm = shutil.which("npm")
    if not npm:
        print("\nStatus: blocked")
        print("Reason: npm was not found on PATH.")
        if args.fail_on_issues:
            sys.exit(1)
        return

    if not paths["node_modules"].is_dir():
        if not args.install:
            print("\nStatus: blocked")
            print("Reason: web/node_modules is missing.")
            print("First run command:")
            print(
                "python skills/software-project-governance/infra/verify_workflow.py "
                "web-console --start --install"
            )
            if getattr(args, "governance_entry", False):
                print("Governance entry: default start attempted; dependency install still requires explicit --install.")
            if args.fail_on_issues:
                sys.exit(1)
            return
        print("\nInstalling web dependencies with npm install...")
        install_timeout = _resolve_web_install_timeout(
            os.environ.get(_WEB_INSTALL_TIMEOUT_ENV, "")
        )
        try:
            install_result = subprocess.run(
                [npm, "install"], cwd=paths["web_dir"], timeout=install_timeout
            )
        except subprocess.TimeoutExpired:
            print("Status: blocked")
            print(
                f"Reason: npm install timed out after {install_timeout}s "
                f"(SPG_WEB_INSTALL_TIMEOUT); raise the value or inspect the npm log."
            )
            if args.fail_on_issues:
                sys.exit(124)
            return
        if install_result.returncode != 0:
            print("Status: blocked")
            print(f"Reason: npm install exited {install_result.returncode}.")
            if args.fail_on_issues:
                sys.exit(install_result.returncode)
            return

    api_server_script = ROOT / "web" / "server.py"
    api_port = args.port + 1 if args.port != 5173 else 5174
    api_started = False
    if api_server_script.is_file():
        api_log = paths["web_dir"] / ".api-server.log"
        api_log_handle = api_log.open("a", encoding="utf-8")
        api_log_handle.write(
            f"\n--- api-server start {datetime.now().isoformat(timespec='seconds')} ---\n"
        )
        api_log_handle.flush()
        api_popen_kwargs = {
            "cwd": str(ROOT),
            "stdout": api_log_handle,
            "stderr": subprocess.STDOUT,
            "stdin": subprocess.DEVNULL,
        }
        if os.name == "nt":
            api_popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            api_popen_kwargs["start_new_session"] = True
        try:
            api_process = subprocess.Popen(
                [sys.executable, str(api_server_script), "--port", str(api_port), "--project-root", str(HOST_PROJECT_ROOT)],
                **api_popen_kwargs,
            )
            api_started = True
            (paths["web_dir"] / ".api-server.pid").write_text(str(api_process.pid), encoding="utf-8")
        except Exception as exc_api:  # pragma: no cover - defensive
            print(f"\nNote: local API server could not start ({exc_api}); the dashboard will run without live data.")
        finally:
            api_log_handle.close()
    else:
        print("\nNote: web/server.py not found; the dashboard will run without live data.")

    command = [
        npm,
        "run",
        "dev",
        "--",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]

    if args.foreground:
        print("\nStatus: starting in foreground")
        print("Stop with Ctrl+C.")
        os.execvpe(command[0], command, os.environ)

    log_handle = paths["log"].open("a", encoding="utf-8")
    log_handle.write(f"\n--- web-console start {datetime.now().isoformat(timespec='seconds')} ---\n")
    log_handle.flush()

    popen_kwargs = {
        "cwd": paths["web_dir"],
        "stdout": log_handle,
        "stderr": subprocess.STDOUT,
        "stdin": subprocess.DEVNULL,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    try:
        process = subprocess.Popen(command, **popen_kwargs)
    finally:
        log_handle.close()
    _write_web_console_process(paths, process)

    for _ in range(30):
        if _web_console_is_live(url):
            print("\nStatus: running")
            print(f"PID: {process.pid}")
            print(f"Log: {_display_path(paths['log'])}")
            if api_started:
                print(f"Local API server: http://127.0.0.1:{api_port}/api/governance (live governance data)")
                print(f"API PID: {api_process.pid} (stop: taskkill /PID {api_process.pid} /F on Windows)")
            if args.open:
                webbrowser.open(url)
            return
        time.sleep(0.5)

    print("\nStatus: starting")
    print(f"PID: {process.pid}")
    print(f"Log: {_display_path(paths['log'])}")
    print("The server did not respond within 15 seconds; check the log above.")
    if args.fail_on_issues:
        sys.exit(1)


# ── resolve-entry thin wrapper (FIX-238.3, ADR-017 §2) ────────────────
# DEC-096 constraint: resolve_entry.py itself is untouched. The bounded
# timeout and classified fail-closed diagnostics live on the calling side
# (this thin entry, bootstrap.sh and bootstrap.cmd share one exit-code
# contract so hosts can delegate between them).
_RESOLVE_TIMEOUT_DEFAULT = 15
_RESOLVE_TIMEOUT_ENV = "SPG_RESOLVE_TIMEOUT"
_RESOLVE_ENTRY_REL = "skills/software-project-governance/infra/resolve_entry.py"
_RESOLVE_ENTRY_CANONICAL_MARKER = "Deterministic /governance entry resolver (FX-130)"
_RESOLVE_EXIT_OTHER = 1
_RESOLVE_EXIT_PYTHON_MISSING = 2
_RESOLVE_EXIT_FILE_NOT_FOUND = 3
_RESOLVE_EXIT_TIMEOUT = 4
_RESOLVE_EXIT_STORE_STUB = 5


def _resolve_resolve_timeout(raw):
    """FIX-238.3: resolve the resolve_entry timeout from an env-var value.

    SPG_RESOLVE_TIMEOUT (positive integer seconds, default 15s); invalid
    values fall back to the default (FIX-234 precedent) instead of crashing.
    """
    return _resolve_positive_timeout(raw, _RESOLVE_TIMEOUT_DEFAULT)


def cmd_resolve_entry(args):
    """Thin bounded invocation of resolve_entry.py with classified
    fail-closed diagnostics (file-not-found / timeout / python-missing /
    store-stub). Prints the JSON envelope on stdout on success."""
    script = ROOT / _RESOLVE_ENTRY_REL
    if not script.is_file():
        print(
            f"spg-bootstrap-error: file-not-found — resolve_entry.py missing at {script}",
            file=sys.stderr,
        )
        sys.exit(_RESOLVE_EXIT_FILE_NOT_FOUND)
    try:
        content = script.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(
            f"spg-bootstrap-error: file-not-found — cannot read {script}: {exc}",
            file=sys.stderr,
        )
        sys.exit(_RESOLVE_EXIT_FILE_NOT_FOUND)
    if _RESOLVE_ENTRY_CANONICAL_MARKER not in content:
        print(
            "spg-bootstrap-error: store-stub — resolve_entry.py exists but is not "
            "the canonical resolver (missing FX-130 marker); reinstall the plugin",
            file=sys.stderr,
        )
        sys.exit(_RESOLVE_EXIT_STORE_STUB)
    timeout = _resolve_resolve_timeout(os.environ.get(_RESOLVE_TIMEOUT_ENV, ""))
    command = [sys.executable, str(script), "--json"]
    if getattr(args, "project_root", None):
        command += ["--project-root", args.project_root]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print(
            f"spg-bootstrap-error: timeout — resolve_entry did not finish within "
            f"{timeout}s (SPG_RESOLVE_TIMEOUT); raise the value or inspect the host",
            file=sys.stderr,
        )
        sys.exit(_RESOLVE_EXIT_TIMEOUT)
    except FileNotFoundError as exc:
        print(f"spg-bootstrap-error: python-missing — {exc}", file=sys.stderr)
        sys.exit(_RESOLVE_EXIT_PYTHON_MISSING)
    if completed.returncode != 0:
        print(
            f"spg-bootstrap-error: resolve_entry exited {completed.returncode}",
            file=sys.stderr,
        )
        if completed.stderr:
            sys.stderr.write(completed.stderr)
        sys.exit(_RESOLVE_EXIT_OTHER)
    sys.stdout.write(completed.stdout)


def _build_cli_parser(parser_argv=()):
    """Build the command-line schema using the engine's current host and choices."""
    from workflow_cli import build_cli_parser
    return build_cli_parser(
        parser_argv, root=ROOT, quality_dimensions=QUALITY_BUDGET_DIMENSIONS,
        runtime_platforms=AGENT_RUNTIME_E2E_PLATFORMS,
        scaffold_types=DETERMINISTIC_SCAFFOLD_TYPES, replay_hint=_tagged_release_replay_hint)


def main(argv=None):
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    try:
        explicit_project_root, parser_argv = _extract_project_root_arg(raw_argv)
    except ValueError as exc:
        print(f"verify_workflow: error: {exc}", file=sys.stderr)
        sys.exit(2)

    parser, _ = _build_cli_parser(parser_argv)
    args = parser.parse_args(parser_argv)
    if args.project_root and explicit_project_root is None:
        explicit_project_root = args.project_root
    args.project_root = explicit_project_root
    if explicit_project_root is not None:
        _apply_project_root_override(explicit_project_root)
        if args.command == "governance-bootstrap":
            args._validated_host_root = HOST_PROJECT_ROOT

    import registry
    return registry.load_handler(args.command or "verify", parsed_args=True)(args)


_ENGINE_COMMAND_DEFAULTS = {cmd.__name__: cmd for cmd in (
    cmd_check_dsh_preset_smoke, cmd_check_dsh_preset_compat, cmd_check_dsh_boundary, cmd_dsh_doctor, cmd_gate_check,
)}


def _effective_engine_command(name, native):
    if name in _ENGINE_COMMAND_DEFAULTS:
        if name not in globals():
            raise AttributeError(name)
        current = globals()[name]
        if current is not _ENGINE_COMMAND_DEFAULTS[name]:
            return current
    return native


if __name__ in ("verify_workflow", "__main__"):
    try:
        from governance_fact_cli import bind_gate_command as _bind_gate_command
    except (ImportError, SyntaxError):
        # Unrelated commands can start. Dispatch reports a broken or missing gate owner.
        pass
    else:
        _bind_gate_command(_effective_engine_command)


_RELEASE_COMMAND_BINDINGS = {
    cmd_release_ledger.__name__: cmd_release_ledger,
    cmd_release_projection.__name__: cmd_release_projection,
    cmd_quality_tools.__name__: cmd_quality_tools,
}


def _effective_release_command(name, native):
    if name in _RELEASE_COMMAND_BINDINGS:
        if name not in globals():
            raise AttributeError(name)
        current = globals()[name]
        if current is not _RELEASE_COMMAND_BINDINGS[name]:
            return current
    return native


try:
    from host_loader_probes import bind_workflow_dsh as _bind_workflow_dsh
except ModuleNotFoundError as error:
    if error.name != "host_loader_probes":
        raise
else:
    if __name__ in ("verify_workflow", "__main__"):
        _bind_workflow_dsh(smoke=lambda **kwargs: check_dsh_preset_smoke(**kwargs),
                           channels=lambda root: check_exploration_channels(root),
                           command=_effective_engine_command)


# Standalone checks have native filesystem/contract readers. When this CLI is loaded,
# independently imported checks must also see changes to its historical public bindings.
_evidence_domain._governance_directory = lambda: GOVERNANCE_DIR
_evidence_domain._task_reference_source = lambda: (EVIDENCE_PATH, expand_task_ids)
_evidence_domain._evidence_archive_reader = _archive_reader
_evidence_domain._context_projection = lambda: (
    _context_file, _context_task, _extract_task_title_from_line, _governance_table_cells,
    _normalize_priority, _host_policy("GOVERNANCE_CONTEXT_EVIDENCE_TASK_HEADERS"))
_evidence_domain._state_headers = lambda: _host_policy("GOVERNANCE_CONTEXT_EVIDENCE_STATE_HEADERS")
_evidence_domain._closed_markers = lambda: _host_policy("GOVERNANCE_CONTEXT_EVIDENCE_CLOSED_MARKERS")
_evidence_domain._unfinished_markers = lambda: _host_policy("GOVERNANCE_CONTEXT_EVIDENCE_UNFINISHED_MARKERS")
_evidence_domain._grounding_inputs = lambda: (_current_release_impact_entries, FACT_BASIS_RE, UNGROUNDED_CLAIM_RE)
_evidence_domain._structured_inputs = lambda: (_current_release_impact_entries, _row_has_governance_store_machine_credential)
_evidence_domain._goal_inputs = lambda: (
    GOVERNANCE_DIR, _active_execution_packet_tasks, _load_execution_packets, _validate_product_success_contract)
import hot_governance_facts as _hot_facts
_hot_facts.snapshot_date_pattern = lambda: FIX_105_SNAPSHOT_DATE_RE
risk_domain._risk_path = lambda: RISK_PATH
risk_domain._plan_path = lambda: SAMPLE_PATH
risk_domain._task_reference_pattern = lambda: _TASK_ID_IN_REF_RE
risk_domain._context_readers = lambda: (_context_file, _context_task)
risk_domain._legacy_aliases = lambda: (RISK_PATH, SAMPLE_PATH, _context_file, _context_task, _TASK_ID_IN_REF_RE)


try:
    from release_validation_cli import bind_release_commands as _bind_release_commands
except ModuleNotFoundError as error:
    if error.name != "release_validation_cli":
        raise
else:
    if __name__ in ("verify_workflow", "__main__"):
        _bind_release_commands(ledger=lambda: (HOST_PROJECT_ROOT, lambda: PLUGIN_ROOT, RepositoryContext, validate_release_ledger),
                               projection=lambda: (lambda: PLUGIN_ROOT, check_projections, write_projections),
                               quality=lambda: _product_policy("probe_quality_tools")(),
                               command=_effective_release_command)


if __name__ in sys.modules and sys.modules[__name__].__dict__ is globals():
    sys.modules[__name__].__class__ = _WorkflowModule


__all__ = [name for name in __dir__() if not name.startswith("_")]


if __name__ == "__main__":
    sys.exit(main())
