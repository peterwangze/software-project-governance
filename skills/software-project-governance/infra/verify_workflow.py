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

    if "REQUIRED_FILES" in globals():
        REQUIRED_FILES.update({
            "Governance Plan Tracker": GOVERNANCE_DIR / "plan-tracker.md",
            "Governance Evidence Log": GOVERNANCE_DIR / "evidence-log.md",
            "Governance Decision Log": GOVERNANCE_DIR / "decision-log.md",
            "Governance Risk Log": GOVERNANCE_DIR / "risk-log.md",
        })


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
from release.quality import probe_quality_tools
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

# Governance FACTS live in the host project, never in the plugin cache.
GOVERNANCE_DIR = HOST_PROJECT_ROOT / ".governance"
EXECUTION_PACKET_PATH = GOVERNANCE_DIR / "execution-packets.json"


def _display_path(path, root=None):
    """Return repo-relative path when possible, without Path.is_relative_to()."""
    root = root or ROOT
    try:
        path_abs = os.path.abspath(os.fspath(path))
        root_abs = os.path.abspath(os.fspath(root))
        common = os.path.commonpath([path_abs, root_abs])
        if os.path.normcase(common) == os.path.normcase(root_abs):
            return Path(os.path.relpath(path_abs, root_abs))
    except (OSError, TypeError, ValueError):
        return path
    return path


def _read_text_normalized(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


# ── PLUGIN_SCOPE_DIRS (keep in sync with cleanup.py) ─────────────
# Directories that constitute the plugin installation boundary.
# Check 10 (M5 compliance) skips these to avoid false positives from
# legitimate checklists in plugin SKILL.md files (FIX-054).
PLUGIN_SCOPE_DIRS = {
    "skills",
    "agents",
    "commands",
    "adapters",
    # FIX-310: the dsh delivery surface — the preset payload the host row
    # renders (`agent-presets/governance/`: composition template + preset.yml)
    # and the host row module itself (`lib/index.js`). Declared here so
    # cleanup.py can purge stale payload files after an upgrade, and so the
    # manifest cleanup_scope stays in sync (FIX-053 F-001).
    "agent-presets",
    "lib",
    ".claude-plugin",
    ".codex-plugin",
    ".zcode-plugin",
    ".agents",
}


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
    """Return repo-relative paths from git, or None when git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT)] + args,
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    return {
        line.strip().replace("\\", "/")
        for line in result.stdout.splitlines()
        if line.strip()
    }


def _split_markdown_table_row(line):
    from governance_readers import markdown_table_cells
    return markdown_table_cells(line)


PLATFORM_ENTRY_FILES = {
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "CODEX.md",
}


BLOCKING_LOCK_ISSUE_TYPES = {
    "schema_violation",
    "orphan_lock",
    "expired_lock",
    "task_not_in_plan",
    "multi_lock_conflict",
    "format_invalid_json",
    "format_empty",
    "format_not_dict",
    "format_missing_key",
    "format_type_error",
    "format_schema_violation",
}


def lock_issue_is_blocking(issue):
    """Return True when a lock issue should affect --fail-on-issues."""
    issue_type = issue.get("type", "")
    normalized = issue_type.removeprefix("format_")
    return issue_type in BLOCKING_LOCK_ISSUE_TYPES or normalized in BLOCKING_LOCK_ISSUE_TYPES


def structural_issue_is_blocking(issue):
    """Return True when a structural validity issue should fail governance health."""
    severity = str(issue.get("severity", "ERROR")).upper()
    return severity not in {"INFO", "WARN", "WARNING"}


def blocking_structural_issues(issues):
    return [issue for issue in issues if structural_issue_is_blocking(issue)]


REQUIRED_FILES = {
    "README": ROOT / "README.md",
    "Workflow Schema": ROOT / "skills/software-project-governance/core/protocol/workflow-schema.md",
    "Plugin Contract": ROOT / "skills/software-project-governance/core/protocol/plugin-contract.md",
    "External Command Contract": ROOT / "skills/software-project-governance/core/protocol/external-command-contract.md",
    "Headless Runner Sample": ROOT / "skills/software-project-governance/core/protocol/headless-runner-sample.md",
    "Command Protocol Schema": ROOT / "skills/software-project-governance/core/protocol/command-schema.md",
    "Workflow Manifest": ROOT / "skills/software-project-governance/core/manifest.md",
    "Company Practices": ROOT / "project/workflows/software-project-governance/research/company-practices.md",
    "Plan Tracker": ROOT / "skills/software-project-governance/core/templates/plan-tracker.md",
    "Evidence Template": ROOT / "skills/software-project-governance/core/templates/evidence-log.md",
    "Decision Template": ROOT / "skills/software-project-governance/core/templates/decision-log.md",
    "Risk Template": ROOT / "skills/software-project-governance/core/templates/risk-log.md",
    "Governance Plan Tracker": GOVERNANCE_DIR / "plan-tracker.md",
    "Governance Evidence Log": GOVERNANCE_DIR / "evidence-log.md",
    "Governance Decision Log": GOVERNANCE_DIR / "decision-log.md",
    "Governance Risk Log": GOVERNANCE_DIR / "risk-log.md",
    "Skill Main Workflow Entry": ROOT / "skills/main-workflow/SKILL.md",
    "Skill Tools Index": ROOT / "skills/software-project-governance/infra/TOOLS.md",
    "Core Stage Gates": ROOT / "skills/software-project-governance/core/stage-gates.md",
    "Core Lifecycle": ROOT / "skills/software-project-governance/core/lifecycle.md",
    "Core Profiles": ROOT / "skills/software-project-governance/core/profiles.md",
    "Core Onboarding": ROOT / "skills/software-project-governance/core/onboarding.md",
    "Skill References Interaction Boundary": ROOT / "skills/software-project-governance/references/interaction-boundary.md",
    "Core Audit Framework": ROOT / "skills/software-project-governance/core/audit-framework.md",
    "Skill References Agent Failure Modes": ROOT / "skills/software-project-governance/references/agent-failure-modes.md",
    "Skill References Company Practices Summary": ROOT / "skills/software-project-governance/references/company-practices-summary.md",
    "Agent Integration Research": ROOT / "project/workflows/software-project-governance/research/agent-integration-models.md",
    "Default Product Shape": ROOT / "project/workflows/software-project-governance/research/default-product-shape.md",
    "External Capability Minimum Validation": ROOT / "project/workflows/software-project-governance/research/external-capability-minimum-validation.md",
    "Domestic Agent CLI Compatibility": ROOT / "project/workflows/software-project-governance/research/domestic-agent-cli-compatibility.md",
    "Repo-local Termination Note": ROOT / "project/workflows/software-project-governance/research/repo-local-termination-note.md",
    "Governance Init Command": ROOT / "commands/governance-init.md",
    "Governance Status Command": ROOT / "commands/governance-status.md",
    "Governance Gate Command": ROOT / "commands/governance-gate.md",
    "Governance Verify Command": ROOT / "commands/governance-verify.md",
    "Governance Update Command": ROOT / "commands/governance-update.md",
    "Codex Skill": ROOT / "skills/software-project-governance/SKILL.md",
    "Skill Stages Initiation Sub-workflow": ROOT / "skills/stage-initiation/SKILL.md",
    "Skill Stages Research Sub-workflow": ROOT / "skills/stage-research/SKILL.md",
    "Skill Stages Architecture Sub-workflow": ROOT / "skills/stage-architecture/SKILL.md",
    "Skill Stages Development Sub-workflow": ROOT / "skills/stage-development/SKILL.md",
    "Skill Stages Selection Sub-workflow": ROOT / "skills/stage-selection/SKILL.md",
    "Skill Stages Infrastructure Sub-workflow": ROOT / "skills/stage-infra/SKILL.md",
    "Skill Stages Testing Sub-workflow": ROOT / "skills/stage-testing/SKILL.md",
    "Skill Stages CI-CD Sub-workflow": ROOT / "skills/stage-cicd/SKILL.md",
    "Skill Stages Release Sub-workflow": ROOT / "skills/stage-release/SKILL.md",
    "Skill Stages Operations Sub-workflow": ROOT / "skills/stage-operations/SKILL.md",
    "Skill Stages Maintenance Sub-workflow": ROOT / "skills/stage-maintenance/SKILL.md",
    "Skill Stages Requirement Clarification": ROOT / "skills/requirement-clarification/SKILL.md",
    "Skill Stages Tech Review Checklist": ROOT / "skills/tech-review/SKILL.md",
    "Skill Stages Code Review Standard": ROOT / "skills/code-review/SKILL.md",
    "Skill Stages Release Checklist": ROOT / "skills/release-checklist/SKILL.md",
    "SKILL Retro Meeting": ROOT / "skills/retro-meeting/SKILL.md",
    "SKILL PR-FAQ Template": ROOT / "skills/pr-faq/SKILL.md",
    "SKILL OKR Template": ROOT / "skills/okr/SKILL.md",
    "SKILL Six-Pager Template": ROOT / "skills/six-pager/SKILL.md",
    "Behavior Protocol (M0-M10)": ROOT / "skills/software-project-governance/references/behavior-protocol.md",
    "Five-Layer Architecture Design": ROOT / "project/references/architecture.md",
    "Asset Migration Map": ROOT / "project/references/asset-migration-map.md",
}

OPTIONAL_PROJECTION_FILES = {
    "Sample Project": ROOT / "project/workflows/software-project-governance/examples/current-project-sample.md",
    "Sample Evidence": ROOT / "project/workflows/software-project-governance/examples/current-project-evidence-log.md",
    "Sample Decision": ROOT / "project/workflows/software-project-governance/examples/current-project-decision-log.md",
    "Sample Risk": ROOT / "project/workflows/software-project-governance/examples/current-project-risk-log.md",

    "Claude Adapter": ROOT / "adapters/claude/README.md",
    "Claude Adapter Manifest": ROOT / "adapters/claude/adapter-manifest.json",
    "Claude Launcher": ROOT / "adapters/claude/launch.py",
    "Codex Adapter": ROOT / "adapters/codex/README.md",
    "Codex Adapter Manifest": ROOT / "adapters/codex/adapter-manifest.json",
    "Codex Launcher": ROOT / "adapters/codex/launch.py",
    "Gemini Adapter": ROOT / "adapters/gemini/README.md",
    "Gemini Adapter Manifest": ROOT / "adapters/gemini/adapter-manifest.json",
    "Gemini Launcher": ROOT / "adapters/gemini/launch.py",
    "opencode Adapter": ROOT / "adapters/opencode/README.md",
    "opencode Adapter Manifest": ROOT / "adapters/opencode/adapter-manifest.json",
    "opencode Launcher": ROOT / "adapters/opencode/launch.py",
    "Pi Adapter": ROOT / "adapters/pi/README.md",
    "Pi Adapter Manifest": ROOT / "adapters/pi/adapter-manifest.json",
    "Pi Launcher": ROOT / "adapters/pi/launch.py",
    "Claude Plugin Marketplace": ROOT / ".claude-plugin/marketplace.json",
    "Claude Plugin Definition": ROOT / ".claude-plugin/plugin.json",
    "Codex Plugin Definition": ROOT / ".codex-plugin/plugin.json",
    "Codex Marketplace": ROOT / ".agents/plugins/marketplace.json",
    "Core VERSIONING": ROOT / "skills/software-project-governance/core/VERSIONING.md",
    "Core Task Gate Model": ROOT / "skills/software-project-governance/core/task-gate-model.md",
    "CHANGELOG": ROOT / "project/CHANGELOG.md",
}

PROJECTION_SNIPPETS = {
    ROOT / "project/workflows/software-project-governance/examples/current-project-sample.md": [
        "已迁移",
    ],
    ROOT / "adapters/claude/README.md": [
        "Tier 1",
        "## Load",
        "## Verify",
        "## Boundary",
        "skills/software-project-governance/SKILL.md",
        "python adapters/claude/launch.py",
        "check-agent-adapters",
        "check-agent-adapters --runtime",
    ],
    ROOT / "adapters/claude/adapter-manifest.json": [
        "adapter_id", "workflow_id", "native_entry", "runtime_e2e", "runtime_capabilities", "launcher",
    ],
    ROOT / "adapters/claude/launch.py": [
        'MANIFEST_PATH = ROOT / "adapters/claude/adapter-manifest.json"',
        "adapters/manifest_report.py", 'report["print_manifest_report"](MANIFEST_PATH, "Claude")',
    ],
    ROOT / "adapters/manifest_report.py": [
        "{platform} Adapter Launcher", 'print("read_order:")', 'print("native_entry:")',
        'print("runtime_e2e:")', 'print("validation:")',
    ],
    ROOT / "adapters/codex/README.md": [
        "Tier 1",
        "## Load",
        "## Verify",
        "## Boundary",
        "skills/software-project-governance/SKILL.md",
        ".codex-plugin/plugin.json",
        ".agents/plugins/marketplace.json",
        "python adapters/codex/launch.py",
        "check-agent-adapters",
        "agent-runtime-e2e --agent codex",
    ],
    ROOT / "adapters/codex/adapter-manifest.json": [
        "adapter_id", "workflow_id", "native_entry", "runtime_e2e", "runtime_capabilities", "launcher",
    ],
    ROOT / "adapters/codex/launch.py": [
        'MANIFEST_PATH = ROOT / "adapters/codex/adapter-manifest.json"',
        "adapters/manifest_report.py", 'report["print_manifest_report"](MANIFEST_PATH, "Codex")',
    ],
    ROOT / "adapters/gemini/README.md": [
        "## 兼容要求",
        "## Gemini 路线判断",
        "## 默认接入顺序",
        "## 国内 agent CLI 兼容抽象",
        "## 适配原则",
        "## 建议的最小验证顺序",
    ],
    ROOT / "adapters/gemini/adapter-manifest.json": [
        "adapter_id",
        "support_status",
        "native_entry",
        "runtime_e2e",
        "runtime_capabilities",
    ],
    ROOT / "adapters/gemini/launch.py": [
        "Gemini Adapter Launcher",
        "runtime_e2e",
        "native_entry",
    ],
    ROOT / "adapters/opencode/README.md": [
        "opencode Adapter",
        "full target-cwd agent runtime E2E verified",
        "opencode-provider-preflight",
        "check-agent-adapters --runtime",
    ],
    ROOT / "adapters/opencode/adapter-manifest.json": [
        "adapter_id",
        "runtime-verified",
        "provider_model_preflight",
        "runtime_capabilities",
        "full_e2e_verified",
    ],
    ROOT / "adapters/opencode/launch.py": [
        "opencode Adapter Launcher",
        "provider_model_preflight",
        "runtime_e2e",
    ],
    ROOT / "adapters/pi/README.md": [
        "Tier 1",
        "加载模型",
        "能力边界",
        "agent-runtime-e2e --agent pi",
    ],
    ROOT / "adapters/pi/adapter-manifest.json": [
        "ask_user_question",
        "dispatch_agent",
        "生成≠咨询",
        "adapters/pi/extension",
    ],
    ROOT / "adapters/pi/launch.py": [
        "Pi Adapter Launcher",
        "native_entry",
        "read_order",
        "validation",
    ],
    ROOT / ".claude-plugin/marketplace.json": [
        "software-project-governance",
    ],
    ROOT / ".claude-plugin/plugin.json": [
        "software-project-governance",
        "skills",
    ],
    ROOT / ".codex-plugin/plugin.json": [
        "software-project-governance",
        "skills",
    ],
    ROOT / ".agents/plugins/marketplace.json": [
        "software-project-governance",
    ],
}

# PROJECT_FACT_SNIPPETS removed in 0.61.1 Step A (FIX-155a) — confirmed dead code
# (zero references across skills/ tests/ project/, only its definition existed).

WORKFLOW_SNIPPETS = {
    ROOT / "README.md": [
        "让 coding agent 帮你看护项目质量",
        "## 安装",
        "## 5 分钟开始",
        "## 内部文档",
    ],
    ROOT / "project/workflows/software-project-governance/research/agent-integration-models.md": [
        "## 调研目标",
        "## Claude Code",
        "## 通用集成模式对比",
    ],
    ROOT / "project/workflows/software-project-governance/research/default-product-shape.md": [
        "## 方案摘要",
        "## 分层设计",
        "## 默认接入矩阵",
    ],
    ROOT / "project/workflows/software-project-governance/research/external-capability-minimum-validation.md": [
        "## 目标",
        "## 为什么先选 external runner / shared command",
        "## 最小验证范围",
        "## 命令约定草案",
        "software-project-governance.run",
    ],
    ROOT / "project/workflows/software-project-governance/research/domestic-agent-cli-compatibility.md": [
        "## 目标",
        "## 兼容抽象",
        "## 默认接入顺序",
        "## 能力检查清单",
    ],
    ROOT / "project/workflows/software-project-governance/research/repo-local-termination-note.md": [
        "## 终止对象",
        "## 终止原因",
        "## 降级后的资产定位",
        "## 新主线如何接管",
    ],
    ROOT / "skills/software-project-governance/core/protocol/workflow-schema.md": [
        "governance-bootstrap --format json",
        "loop status --unit",
        "(../lifecycle.md)",
        "(../loop-engineering-registry.json)",
    ],
    ROOT / "skills/software-project-governance/core/protocol/plugin-contract.md": [
        "## 最小承载单元",
        "## 三层承载模型",
        "## Skill / Plugin 行为描述要素",
        "## 默认接入要求",
        "workflow 本体层 + agent 入口投影层 + 外部能力层",
        "software-project-governance",
        "stages",
        "interaction-boundary",
        "Agent 适配准入标准",
        "冲击场景",
        "SC-1",
    ],
    ROOT / "skills/software-project-governance/core/protocol/external-command-contract.md": [
        "## 目标",
        "software-project-governance.run",
        "## 最小输入",
        "## 最小输出",
        "## write-back targets",
        "## replacement boundary",
        "### 协议层（必读）",
        "### 当前阶段子工作流（按 stage 参数加载）",
        "interaction-boundary",
        "Validation Matrix",
        "失败与阻断语义",
    ],
    ROOT / "skills/software-project-governance/core/protocol/headless-runner-sample.md": [
        "## 目标",
        "software-project-governance.headless",
        "## 输入映射",
        "## execution mode",
        "dry-run",
        "## 最小返回样例",
        "### 当前阶段子工作流（按 stage 参数加载）",
    ],
    ROOT / "skills/software-project-governance/core/manifest.md": [
        "supported_agents",
        "Claude",
        "Codex",
    ],
}

# FEAT-038 补修 / F-2 (data-inventory-0.80.0.md §F-2): the `REQUIRED_SNIPPETS = {}`
# + two `.update()` calls removed here were DEAD — the literal below rebinds the
# name, so check_snippets() never saw them (dead since AUDIT-082/f9a18d0; removal
# advised by REL-078 CODE R0 L121). Literal is the sole authority; F-2 items open.
REQUIRED_SNIPPETS = {
    ROOT / "README.md": [
        "让 coding agent 帮你看护项目质量",
        "## 安装",
        "## 5 分钟开始",
        "## 内部文档",
    ],
    ROOT / "project/workflows/software-project-governance/research/agent-integration-models.md": [
        "## 调研目标",
        "## Claude Code",
        "## 通用集成模式对比",
    ],
    ROOT / "project/workflows/software-project-governance/research/default-product-shape.md": [
        "## 方案摘要",
        "## 分层设计",
        "## 默认接入矩阵",
    ],
    ROOT / "project/workflows/software-project-governance/research/external-capability-minimum-validation.md": [
        "## 目标",
        "## 为什么先选 external runner / shared command",
        "## 最小验证范围",
        "## 命令约定草案",
        "software-project-governance.run",
    ],
    ROOT / "project/workflows/software-project-governance/research/domestic-agent-cli-compatibility.md": [
        "## 目标",
        "## 兼容抽象",
        "## 默认接入顺序",
        "## 能力检查清单",
    ],
    ROOT / "project/workflows/software-project-governance/research/repo-local-termination-note.md": [
        "## 终止对象",
        "## 终止原因",
        "## 降级后的资产定位",
        "## 新主线如何接管",
    ],
    ROOT / "project/workflows/software-project-governance/examples/current-project-sample.md": [
        "已迁移",
    ],
    ROOT / "skills/software-project-governance/core/protocol/workflow-schema.md": [
        "governance-bootstrap --format json",
        "loop status --unit",
        "(../lifecycle.md)",
        "(../loop-engineering-registry.json)",
    ],
    ROOT / "skills/software-project-governance/core/protocol/plugin-contract.md": [
        "## 最小承载单元",
        "## 三层承载模型",
        "## Skill / Plugin 行为描述要素",
        "## 默认接入要求",
        "workflow 本体层 + agent 入口投影层 + 外部能力层",
        "software-project-governance",
        "stages",
        "interaction-boundary",
        "Agent 适配准入标准",
        "冲击场景",
        "SC-1",
    ],
    ROOT / "skills/software-project-governance/core/protocol/external-command-contract.md": [
        "## 目标",
        "software-project-governance.run",
        "## 最小输入",
        "## 最小输出",
        "## write-back targets",
        "## replacement boundary",
        "### 协议层（必读）",
        "### 当前阶段子工作流（按 stage 参数加载）",
        "interaction-boundary",
        "Validation Matrix",
        "失败与阻断语义",
    ],
    ROOT / "skills/software-project-governance/core/protocol/headless-runner-sample.md": [
        "## 目标",
        "software-project-governance.headless",
        "## 输入映射",
        "## execution mode",
        "dry-run",
        "## 最小返回样例",
        "### 当前阶段子工作流（按 stage 参数加载）",
    ],
    ROOT / "skills/software-project-governance/core/manifest.md": [
        "supported_agents",
        "Claude",
        "Codex",
    ],
    # ── Command Protocol Schema + Upgraded Commands ──
    ROOT / "skills/software-project-governance/core/protocol/command-schema.md": [
        "## Input Parameters 定义规范",
        "## Execution Flow 定义规范",
        "## Output Format 定义规范",
        "## Error Codes 定义规范",
        "## Self-Validation 定义规范",
        "## Agent 执行纪律",
    ],
    ROOT / "commands/governance-init.md": [
        "governance-bootstrap --format json", "resolve.resolved_root_ok",
        "loop start --unit", "--goal", "--acceptance", "--tier",
    ],
    ROOT / "commands/governance-status.md": [
        "governance-bootstrap --format json", "loop status --unit", "loop status --json",
    ],
    ROOT / "commands/governance-gate.md": [
        "loop status --unit", "loop gate --unit", "--gate", "--review",
    ],
    ROOT / "commands/governance-verify.md": [
        "## 输入参数",
        "## 执行流程",
        "## 输出格式",
        "## 错误码",
        "## 自校验",
        "VERIFY-ERR-001",
    ],
    ROOT / "commands/governance-update.md": [
        "## 输入参数",
        "## 执行流程",
        "## 输出格式",
        "## 错误码",
        "## 自校验",
        "UPDATE-ERR-001",
    ],
    ROOT / "adapters/claude/README.md": [
        "Tier 1",
        "## Load",
        "## Verify",
        "## Boundary",
        "skills/software-project-governance/SKILL.md",
        "python adapters/claude/launch.py",
        "check-agent-adapters",
        "check-agent-adapters --runtime",
    ],
    ROOT / "adapters/claude/adapter-manifest.json": [
        "adapter_id",
        "workflow_id",
        "native_entry",
        "launcher",
    ],
    ROOT / "adapters/claude/launch.py": [
        'MANIFEST_PATH = ROOT / "adapters/claude/adapter-manifest.json"',
        "adapters/manifest_report.py", 'report["print_manifest_report"](MANIFEST_PATH, "Claude")',
    ],
    ROOT / "adapters/manifest_report.py": [
        "{platform} Adapter Launcher", 'print("read_order:")', 'print("native_entry:")',
        'print("runtime_e2e:")', 'print("validation:")',
    ],
    ROOT / "adapters/codex/README.md": [
        "Tier 1",
        "## Load",
        "## Verify",
        "## Boundary",
        "skills/software-project-governance/SKILL.md",
        ".codex-plugin/plugin.json",
        ".agents/plugins/marketplace.json",
        "python adapters/codex/launch.py",
        "check-agent-adapters",
        "agent-runtime-e2e --agent codex",
    ],
    ROOT / "adapters/codex/adapter-manifest.json": [
        "adapter_id",
        "workflow_id",
        "launcher",
    ],
    ROOT / "adapters/codex/launch.py": [
        'MANIFEST_PATH = ROOT / "adapters/codex/adapter-manifest.json"',
        "adapters/manifest_report.py", 'report["print_manifest_report"](MANIFEST_PATH, "Codex")',
    ],
    ROOT / "adapters/gemini/README.md": [
        "## 兼容要求",
        "## Gemini 路线判断",
        "## 默认接入顺序",
        "## 国内 agent CLI 兼容抽象",
        "## 适配原则",
        "## 建议的最小验证顺序",
    ],
    # Plugin marketplace packaging
    ROOT / ".claude-plugin/marketplace.json": [
        "software-project-governance",
    ],
    ROOT / ".claude-plugin/plugin.json": [
        "software-project-governance",
        "skills",
    ],
    ROOT / ".codex-plugin/plugin.json": [
        "software-project-governance",
        "skills",
    ],
    ROOT / "skills/software-project-governance/SKILL.md": [
        "# 软件项目治理工作流入口",
        "加载本 SKILL 后，你进入软件项目治理工作流",
        "你是 Coordinator，不是单 agent 任务执行者",
        "Coordinator 接管用户交互",
        "Producer-Reviewer 分离",
        "references/behavior-protocol.md",
        "core/lifecycle.md",
        "core/stage-gates.md",
        "core/task-gate-model.md",
        "references/agent-communication-protocol.md",
        "六层架构",
        "适配层（平台投影）",
        "infra/verify_workflow.py",
        "infra/hooks/",
    ],
    ROOT / "skills/software-project-governance/references/behavior-protocol.md": [
        "# 行为协议",
        "M0-M10 强制性规则",
        "## M0. 合规语言",
        "## M1. 任务匹配",
        "## M2. 预加载",
        "## M3. 输出规则",
        "## M4. 会话生命周期",
        "## M5. AskUserQuestion 协议",
        "## M6. Gate 行为",
        "## M7. 执行连续性",
        "## M8. 自检协议",
        "## M9. 优先级声明",
        "## M10. 主动生态探索协议",
        "M7.4 任务完成协议",
        "M7.5 任务前协议",
        "证据 → check-governance → 审计 → 交付物审查在 commit 之前 → commit → 继续",
        "双重机制",
        "9 项 agent 无法造假的检查",
        "阶段快速参考",
        "Profile 快速参考",
    ],
    ROOT / "project/references/architecture.md": [
        "# 六层架构设计",
        "适配层（Adapter）",
        "入口层",
        "业务智能层（Agent 库）",
        "能力层（SKILL 库）",
        "基础设施层",
        "核心层",
        "依赖方向（铁律）",
        "能力层 vs 业务智能层（关键区分）",
        "入口层 vs 适配层（关键区分）",
        "单向依赖，不可反向",
        "与协议层概念的对齐",
    ],
    ROOT / "skills/software-project-governance/core/audit-framework.md": [
        "# 审计框架",
        "审计作为一等治理看护手段",
        "## 审计维度",
        "D1 — 项目目标一致性审计",
        "D2 — 用户使用角度审计",
        "D3 — 阶段闭环质量审计",
        "D4 — 修改闭环标准审计",
        "D5 — 用户易用性审计",
        "D6 — 质量防护网看护预期审计",
        "## 审计执行协议",
        "## Profile 对审计的影响",
        "## Agent 审计纪律",
        "governance-critical 文件",
    ],
    ROOT / "skills/software-project-governance/references/agent-failure-modes.md": [
        "# Agent 失败模式文档",
        "## 失败模式 1：协议跳过",
        "## 失败模式 2：选择性执行",
        "## 失败模式 3：幻觉式证据",
        "## 失败模式 4：虚假闭环",
        "## 失败模式 5：跨会话失忆",
        "## 失败模式 6：自我审计矛盾",
        "## 失败模式 7：虚假归因",
        "## 失败模式 8：计划漂移",
        "## 应急流程总览",
    ],
    ROOT / ".agents/plugins/marketplace.json": [
        "software-project-governance",
    ],
    ROOT / "skills/software-project-governance/core/stage-gates.md": [
        "loop status --unit",
    ],
    ROOT / "skills/software-project-governance/core/audit-framework.md": [
        "Tier 完成时",
    ],
    ROOT / "skills/software-project-governance/references/behavior-protocol.md": [
        "完成 Tier 时",
    ],
    ROOT / "skills/software-project-governance/core/VERSIONING.md": [
        "# 版本管理策略",
        "语义化版本规则",
        "版本升级触发条件",
    ],
    ROOT / "changelog.md": ["](project/CHANGELOG.md)"],
    ROOT / "project/CHANGELOG.md": [
        "# 变更日志",
        "## [0.10.0]",
        "## [0.9.0]",
        "## [0.8.0]",
        "## [0.7.1]",
        "## [0.7.0]",
        "## [0.5.0]",
    ],
    ROOT / ".claude-plugin/plugin.json": [
        "0.101.0",
    ],
    ROOT / ".claude-plugin/marketplace.json": [
        "0.101.0",
    ],
    ROOT / ".codex-plugin/plugin.json": [
        "0.101.0",
    ],
    ROOT / ".zcode-plugin/plugin.json": [
        "0.101.0",
    ],
    ROOT / "package.json": [
        "0.101.0",
    ],
    ROOT / "skills/software-project-governance/core/manifest.json": [
        "0.101.0",
    ],
}


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

# ── Evidence domain (extracted to infra/checks/evidence_domain.py in 0.70.0) ──
# DEC-083 Phase 5a / ADR-016 / FEAT-009: the evidence check domain (Checks 1,
# 1b, 6, 6b plus evidence-only parsing helpers) now lives in
# checks.evidence_domain. Thin re-export keeps existing call sites (the
# Check 1/1b/6/6b blocks in cmd_check_governance, the test suite
# `import verify_workflow as vw; vw.check_evidence_completeness()`, and
# discover_governance_context) working unchanged. Shared helpers/constants
# stay here and are reached by the new module via its deferred `_vw()`
# accessor (same pattern as manifest/capability_registry).
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
from checks.risk_domain import (  # noqa: E402
    _parse_context_open_risks,
    is_risk_status_open,
    parse_open_risks,
    parse_active_risks,
    check_risk_staleness,
    check_risk_escalation,
    emit_risk_staleness,
    emit_risk_escalation, emit_risk_mitigation_closure,
    _ARCHIVE_FAMILY_RANGE_RE, _ARCHIVE_RANGE_SPAN_CAP, _ARCHIVE_RESOLVED_STATUS,
    check_risk_mitigation_closure,  # FIX-265 / REQ-145.3 (Check 36)
    _default_task_status_map,  # FIX-294: active map for the archive wrapper
    _resolve_shared,  # FIX-294: refresh deferred shared names before the
    # map build — _default_task_status_map reads risk_domain's deferred
    # globals (SAMPLE_PATH), which are stale unless refreshed in-process.
)

# ── Snapshot domain (new in 0.76.0) ──────────────────────────────────────
# FIX-268 / REQ-145.2 (design §3.2): the snapshot-freshness watchdog
# (Check 35). New domain module checks/snapshot_domain.py mirrors the
# risk_domain pattern: deferred _vw() shared accessor, no import cycle.
from checks.snapshot_domain import (  # noqa: E402
    check_snapshot_freshness,  # FIX-268 / REQ-145.2 (Check 35)
)

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
    check_ci_evidence,  # FIX-267 / REQ-145.5 (Check 38)
)

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
from checks.triage_domain import (  # noqa: E402
    check_change_triage,
    check_r1_completion_gate,
)


# ── Existing verification functions ──────────────────────────────

def check_files():
    failures = []

    # Attempt manifest.json first; fall back to builtin hard-coded dicts
    required = build_required_files_from_manifest()
    if required is None:
        required = REQUIRED_FILES
        optional = OPTIONAL_PROJECTION_FILES
    else:
        optional = {}  # manifest covers everything

    for label, path in required.items():
        if path.is_file():
            print(f"[OK] file exists: {label} -> {path.relative_to(ROOT)}")
        else:
            failures.append(f"missing required file: {label} -> {path.relative_to(ROOT)}")
            print(f"[FAIL] missing required file: {label} -> {path.relative_to(ROOT)}")

    for label, path in optional.items():
        if path.is_file():
            print(f"[OK] optional projection exists: {label} -> {path.relative_to(ROOT)}")
        else:
            print(f"[INFO] optional projection missing: {label} -> {path.relative_to(ROOT)}")

    return failures


def check_snippets():
    failures = []
    for path, snippets in REQUIRED_SNIPPETS.items():
        if not path.is_file():
            failures.append(f"missing snippet source file: {_display_path(path)}")
            print(f"[FAIL] missing snippet source file: {_display_path(path)}")
            continue
        content = path.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet in content:
                print(f"[OK] snippet found: {path.relative_to(ROOT)} :: {snippet}")
            else:
                failures.append(f"missing snippet in {path.relative_to(ROOT)}: {snippet}")
                print(f"[FAIL] missing snippet: {path.relative_to(ROOT)} :: {snippet}")
    return failures


_HOST_POLICY_OWNERS = {
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


def __getattr__(name):
    """Resolve the public archive reader and installed host policies on first access."""
    if name == "GovernanceDataSource":
        return _archive_reader_class()
    module = _HOST_POLICY_OWNERS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(module), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(globals().keys() | _HOST_POLICY_OWNERS.keys() | {"GovernanceDataSource"})


def _host_policy(name):
    """Read the current legacy binding, including changes made by programmatic callers."""
    try:
        return globals()[name]
    except KeyError:
        return __getattr__(name)


def check_loop_role_skill_consistency(root=None):
    from team_activation import check_loop_role_skill_consistency as run
    return run(
        root, package_root=ROOT, lifecycle_registry_gates=LIFECYCLE_REGISTRY_GATES,
        loop_role_skill_contracts=_host_policy('LOOP_ROLE_SKILL_CONTRACTS'), display_path=_display_path,
        markdown_section_by_prefix=_markdown_section_by_prefix, read_text_normalized=_read_text_normalized,
    )


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


def _hot_status_cell_is_delivered(status):
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
    return _status_is_writer_committed_cell(_status_clean_cell(status))


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


def _hot_task_is_delivered(plan_content, task_id, version=None):
    statuses = _task_statuses_for_hot_source(plan_content, task_id, version=version)
    # FIX-395: writer-committed terminal cells count delivered (FIX-393
    # criteria by identity) — S_new ⊇ S_old, guarded shapes unchanged.
    return bool(statuses) and any(_hot_status_cell_is_delivered(status) for status in statuses)


def _hot_task_is_open(plan_content, task_id, version=None):
    statuses = _task_statuses_for_hot_source(plan_content, task_id, version=version)
    # FIX-395: mirror of _hot_task_is_delivered — a writer-committed row no
    # longer counts open; dev/triaged rows (anchored or not) still do.
    return bool(statuses) and any(not _hot_status_cell_is_delivered(status) for status in statuses)


def _hot_task_ids_for_version(plan_content, version):
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
            release_delivered = release_delivered or _hot_status_cell_is_delivered(cells[-1])
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


def _latest_published_release_fact(plan_content):
    latest = None
    for version, date_cell in FIX_105_SNAPSHOT_RELEASE_VERSION_RE.findall(plan_content):
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


def _snapshot_fact_source_issues(plan_content, plan_tracker_path):
    plan_version_match = FIX_105_PLAN_WORKFLOW_VERSION_RE.search(plan_content)
    plan_version = plan_version_match.group(1) if plan_version_match else ""
    latest_release = _latest_published_release_fact(plan_content)

    snapshot_path = Path(plan_tracker_path).with_name("session-snapshot.md")
    if not snapshot_path.exists():
        return []

    snapshot_content = snapshot_path.read_text(encoding="utf-8")
    rel_snapshot = _display_path(snapshot_path)
    issues = []

    snapshot_version_match = FIX_105_SNAPSHOT_VERSION_RE.search(snapshot_content)
    snapshot_version = snapshot_version_match.group(1) if snapshot_version_match else ""
    if plan_version and snapshot_version and snapshot_version != plan_version:
        issues.append(f"{rel_snapshot}: session snapshot workflow version {snapshot_version} does not match plan-tracker {plan_version}")
    elif plan_version and not snapshot_version:
        issues.append(f"{rel_snapshot}: session snapshot missing workflow version")

    date_match = FIX_105_SNAPSHOT_DATE_RE.search(snapshot_content)
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


def _hot_fact_source_plugin_scope():
    """Check 28c plugin-project scope (FIX-270 mixed-root fix).

    The FIX-087-era expectations (0.38.0 roadmap row, FIX-082~087 active
    task table, REQ-070~074 requirement matrix, RISK-033 / REL-013 blocker
    chain, ``### 1.0.0 依赖链`` section) assert facts about the governed
    object being the plugin project itself. They may only run in dogfood
    mode (host root == plugin root); a host project (roots diverge) must not
    be FAILed on those expectations — generic section/snapshot consistency
    still applies there.
    """
    return not _host_plugin_roots_divergent()


def check_hot_fact_source_consistency(plan_tracker_path=None):
    """FIX-087: keep plan-tracker hot sections aligned across active release facts.

    FIX-270 (mixed-root): generic consistency (snapshot version/date vs
    plan-tracker + required hot sections) applies to every project. The
    plugin-project expectations (0.38.0 roadmap / FIX-082~087 / REQ-070~074 /
    RISK-033 / REL-013 / ``### 1.0.0 依赖链``) assert facts about the governed
    object being the plugin project and are enforced only in dogfood mode
    (see :func:`_hot_fact_source_plugin_scope`); host mode reports the
    downgrade honestly instead of FAILing host data.
    """
    plan_tracker_path = plan_tracker_path or _governance_dir() / "plan-tracker.md"
    failures = []
    if not plan_tracker_path.is_file():
        return [f"{_display_path(plan_tracker_path)}: plan-tracker unavailable"]
    plan_content = plan_tracker_path.read_text(encoding="utf-8")
    rel_plan = _display_path(plan_tracker_path)
    _gov = _governance_dir()
    if (
        "External Validation Temporary Project" in plan_content
        and "temporary external-project workspace" in plan_content
        and (_gov / "external-validation-target.json").is_file()
        and plan_tracker_path.resolve() == (_gov / "plan-tracker.md").resolve()
    ):
        print("[OK] hot fact-source consistency skipped for external validation temporary workspace")
        return []
    failures.extend(_snapshot_fact_source_issues(plan_content, plan_tracker_path))

    plugin_scope = _hot_fact_source_plugin_scope()
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
        version_task_ids, release_delivered, release_declared = _hot_task_ids_for_version(plan_content, active_version)
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
        if not any(version != active_version for version, _date_text in FIX_105_SNAPSHOT_RELEASE_VERSION_RE.findall(plan_content)):
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
            if FIX_087_READINESS_VERSION not in dependency_chain:
                failures.append(f"{rel_plan}: {FIX_087_READINESS_VERSION} dependency chain missing active blocker token {FIX_087_READINESS_VERSION}")
            for token in ["RISK-033", "REL-013"]:
                if token in plan_content and token not in dependency_chain:
                    failures.append(f"{rel_plan}: {FIX_087_READINESS_VERSION} dependency chain missing active blocker token {token}")
            for token in FIX_105_READINESS_RELEASE_BLOCKERS:
                if token in plan_content and token not in dependency_chain:
                    failures.append(f"{rel_plan}: {FIX_087_READINESS_VERSION} dependency chain missing readiness release blocker token {token}")
            if released_face:
                risk033_lines = [line for line in dependency_chain.splitlines() if "RISK-033" in line]
                if risk033_lines and not any("已关闭" in line for line in risk033_lines):
                    failures.append(f"{rel_plan}: {FIX_087_READINESS_VERSION} dependency chain still lacks RISK-033 closure after release")
            elif "不得打 1.0.0" not in dependency_chain and "不得推进 1.0.0" not in dependency_chain:
                failures.append(f"{rel_plan}: {FIX_087_READINESS_VERSION} dependency chain missing blocking language for active release")
            # FIX-339 (REVIEW-FIX-339-CODE-R1 F-R1-05): completion lookups span
            # the task's own rows (version=None, same caliber as F-02 above) —
            # exact-anchor filtering silently no-oped these checks for
            # `或后续`/gate-reference target cells. Recall-only: this never
            # relaxes a completion judgment, it only restores recall.
            completed_active_tasks = [task_id for task_id in version_task_ids if _hot_task_is_delivered(plan_content, task_id, version=None)]
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
                if _hot_task_is_delivered(plan_content, task_id, version=None):
                    failures.append(f"{rel_plan}: project overview says completed {task_id} still carries RISK-033")
        elif "RISK-033" in overview and "FIX-087" not in overview:
            failures.append(f"{rel_plan}: project overview mentions RISK-033 but does not name remaining FIX-087")
        for req_id, task_ids in FIX_087_REQ_TASKS.items():
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
            all_tasks_delivered = all(_hot_task_is_delivered(plan_content, task_id, version=None) for task_id in task_ids)
            any_task_open = any(_hot_task_is_open(plan_content, task_id, version=None) for task_id in task_ids)
            if all_tasks_delivered and not _status_cell_is_delivered(req_status):
                failures.append(f"{rel_plan}: requirement matrix {req_id} is not delivered while {', '.join(task_ids)} are complete")
            if any_task_open and _status_cell_is_delivered(req_status):
                failures.append(f"{rel_plan}: requirement matrix {req_id} is delivered while linked task remains open")

    for failure in failures:
        print(f"[FAIL] hot fact-source consistency: {failure}")
    if not failures:
        print("[OK] hot fact-source consistency synchronized")
    return failures


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


# FIX-400 (2026-09-28) wall-clock recalibration 180 -> 2333, following the
# DEC-262(1)/FIX-346 discipline (formula re-anchor with measured provenance —
# silent raises are forbidden; this is a re-anchored budget, NOT a green-wash).
# The 180 s default dates to FIX-234, when the bounded unit-test suite still
# fit inside it; the suite has outgrown it deterministically ever since
# (0.80.0 REL-077 ~258 s; 0.84.0 273.4 s; 0.91.0 M 1554.78 s) and the known
# check-release FAILED-2 disclosure carries this same cause (DEC-264(2);
# M-3 RELEASE ruled the wall-clock component non-blocking).
# Scope: this timeout bounds the four release execution-gate subprocesses in
# run_release_execution_gates ("verify" / "governance health" / "e2e check" /
# the "unit tests" -m unittest run over test_verify_workflow.py — the wall-
# clock driver) plus the FEAT-016 dsh preset-session smoke (upgrade gate).
# Provenance: 0.91.0 M calibration-session machine records (DEC-264(2)) —
# full bounded suite 1554.78 s in a single measurement (pwsh-167 M-1 run:
# 4351P/1F/1S/540 subtests; M-2 dual-source runs pwsh-170/171: 4359P/0F/1S/
# 527). Single observation, so it serves as the p50 proxy (n=1, disclosed).
# New budget = p50 x 1.5 = ceil(1554.78 x 1.5) = ceil(2332.17) = 2333 s.
# Inverse check at calibration time: halved (1166.5 s) it stays RED against
# the observed run (1554.78 s), so the budget still bites. Same-session
# targeted corroboration (2026-09-28, this repo): bounded-command
# representative subset (release/upgrade-gate/smoke/hook classes, exit 0)
# single run 15.844 s; static TestLoader count 948 methods — the full-suite
# machine-record anchor above remains the calibration basis. The
# SPG_RELEASE_GATE_TIMEOUT env override (FIX-234) keeps priority.
_RELEASE_GATE_TIMEOUT_DEFAULT = 2333
_RELEASE_GATE_TIMEOUT_ENV = "SPG_RELEASE_GATE_TIMEOUT"


def _resolve_release_gate_timeout(raw):
    """FIX-234: resolve the release-gate timeout from an env-var value.

    Returns the value when it is a positive integer, otherwise the module
    default (_RELEASE_GATE_TIMEOUT_DEFAULT — 180 s in the FIX-234 era,
    recalibrated to 2333 s by FIX-400; provenance lives on the constant).
    Invalid values fall back instead of crashing the gate; that
    fallback-not-crash contract is unchanged by the recalibration.
    """
    raw = (raw or "").strip()
    if not raw:
        return _RELEASE_GATE_TIMEOUT_DEFAULT
    try:
        value = int(raw)
    except ValueError:
        return _RELEASE_GATE_TIMEOUT_DEFAULT
    return value if value > 0 else _RELEASE_GATE_TIMEOUT_DEFAULT


def _run_release_validation_command(label, command, timeout=None):
    """Run one release validation command and normalize its result.

    timeout: explicit seconds; when None (default) the
    SPG_RELEASE_GATE_TIMEOUT env var (integer seconds, FIX-234) is honored,
    falling back to the module default for absent/invalid values.
    """
    if timeout is None:
        timeout = _resolve_release_gate_timeout(
            os.environ.get(_RELEASE_GATE_TIMEOUT_ENV, "")
        )
    try:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding=locale.getpreferredencoding(False),
            errors="replace",
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        return {
            "label": label,
            "pass": False,
            "exit_code": None,
            "issue": f"{label}: command did not complete: {exc}",
            "command": " ".join(str(part) for part in command),
        }

    output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
    issue = None if completed.returncode == 0 else (
        f"{label}: exit={completed.returncode}; "
        f"output={output[-500:] if output else '<empty>'}"
    )
    return {
        "label": label,
        "pass": completed.returncode == 0,
        "exit_code": completed.returncode,
        "issue": issue,
        "command": " ".join(str(part) for part in command),
    }


def run_release_execution_gates(runner=_run_release_validation_command,
                                timeout=None):
    """Run command-backed release gates that must be green before publishing.

    timeout: optional explicit seconds forwarded to the runner. When omitted,
    the runner resolves its own timeout (SPG_RELEASE_GATE_TIMEOUT env var,
    module default — FIX-234, recalibrated by FIX-400). Custom two-arg
    runners keep working unchanged.
    """
    verify_script = ROOT / "skills/software-project-governance/infra/verify_workflow.py"
    commands = [
        ("verify", [sys.executable, str(verify_script), "verify"]),
        ("governance health", [sys.executable, str(verify_script), "check-governance", "--fail-on-issues"]),
        ("e2e check", [sys.executable, str(verify_script), "e2e-check"]),
        ("unit tests", [sys.executable, "-m", "unittest", "skills/software-project-governance/infra/tests/test_verify_workflow.py", "-v"]),
    ]
    if timeout is None:
        return [runner(label, command) for label, command in commands]
    return [runner(label, command, timeout=timeout) for label, command in commands]


def _release_docs_line_has_guard_context(label, line):
    if label != "rollback plan":
        return False
    lower = line.lower()
    return (
        ("release docs" in lower and "changelog" in lower and "声明" in lower)
        or ("release docs" in lower and "claim" in lower)
        or ("requirement reports" in lower and "claim" in lower)
        or "发布提交混入" in lower
        or "release package mixes" in lower
    )


def _tagged_release_replay_hint(version):
    """Release-specific acceptance lives with the source and evidence it inspected."""
    if version in ("0.45.0", "0.46.0", "0.47.0", "0.66.2"):
        return (f"Release v{version} uses its tagged verifier. From the repository root run:\n"
                f"  git worktree add --detach ../replay-{version} v{version}\n"
                "See the historical acceptance steps in skills/software-project-governance/infra/TOOLS.md.")
    return None


def check_release_docs_coverage(version, root=None):
    """REL-021: versioned release docs must be present, tracked, and conservative."""
    root = Path(root) if root is not None else ROOT
    issues = []
    if not version or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        return issues

    replay_hint = _tagged_release_replay_hint(version)
    if replay_hint:
        return [replay_hint]

    release_docs = [
        ("release checklist", f"docs/release/release-checklist-{version}.md"),
        ("feature flags", f"docs/release/feature-flags-{version}.md"),
        ("rollback plan", f"docs/release/rollback-plan-{version}.md"),
    ]
    tracked_files = _git_files(["ls-files", "--cached"])
    manifest_result = check_manifest_consistency(root / "skills/software-project-governance/core/manifest.json")
    manifest_missing = set(manifest_result.get("missing", [])) if manifest_result.get("pass") is not None else set()
    manifest_untracked = set(manifest_result.get("untracked", [])) if manifest_result.get("pass") is not None else set()
    boundary_needles = [
        "official approval",
        "marketplace approval",
        "universal/full runtime support",
        "external first-session pilot success",
        "RISK-036",
    ]
    forbidden_positive_claims = [
        "official approval granted",
        "official approval approved",
        "officially approved",
        "marketplace approval granted",
        "marketplace approval approved",
        "marketplace approved",
        "universal runtime support is verified",
        "universal runtime support is supported",
        "universal runtime support verified",
        "universal runtime support supported",
        "full runtime support is verified",
        "full runtime support is supported",
        "full runtime support verified",
        "full runtime support supported",
        "universal/full runtime support is verified",
        "universal/full runtime support is supported",
        "universal/full runtime support verified",
        "universal/full runtime support supported",
        "external first-session pilot success",
        "external first-session pilot pass",
        "external first-session pilot passed",
        "codex desktop marketplace-management e2e pass",
        "codex desktop marketplace-management e2e passed",
        "automatic best-tool selection pass",
        "automatic best-tool selection is passed",
        "automatic best-tool selection passed",
        "automatic best-tool selection is available",
        "automatic best-tool selection available",
        "automatic best-tool selection is verified",
        "automatic best-tool selection verified",
        "universal plugin/skill/tool availability pass",
        "universal plugin/skill/tool availability is passed",
        "universal plugin/skill/tool availability passed",
        "universal plugin/skill/tool availability is available",
        "universal plugin/skill/tool availability available",
        "universal plugin/skill/tool availability is verified",
        "universal plugin/skill/tool availability verified",
        "catalog entry runtime pass",
        "catalog entry runtime is passed",
        "catalog entry runtime passed",
        "catalog entry runtime is available",
        "catalog entry runtime available",
        "catalog entry runtime is verified",
        "catalog entry runtime verified",
        "1.0.0 production-ready",
        "risk-036 closed",
    ]

    for label, rel_path in release_docs:
        path = root / rel_path
        display = _display_path(path, root)
        if not path.is_file():
            issues.append(f"{display}: missing {label} for release {version}")
            continue
        if tracked_files is not None and rel_path not in tracked_files:
            issues.append(f"{display}: {label} must be tracked by git")
        if rel_path in manifest_missing:
            issues.append(f"{display}: {label} is declared in manifest but missing from tracked files")
        if rel_path in manifest_untracked:
            issues.append(f"{display}: {label} exists but is not covered by manifest")

        content = path.read_text(encoding="utf-8")
        if version not in content:
            issues.append(f"{display}: {label} missing release version {version}")
        lower_content = content.lower()
        missing_needles = [needle for needle in boundary_needles if needle.lower() not in lower_content]
        if missing_needles:
            issues.append(f"{display}: {label} missing conservative boundary tokens: {', '.join(missing_needles)}")
        for phrase in forbidden_positive_claims:
            for line in content.splitlines():
                if (
                    phrase in line.lower()
                    and not _line_has_scoped_claim_negation(line, phrase)
                    and not _release_docs_line_has_guard_context(label, line)
                ):
                    issues.append(f"{display}: {label} forbidden release docs overclaim `{phrase}`")
                    break

    return issues


def _markdown_table_row_by_first_cell(content, first_cell):
    for line in content.splitlines():
        cells = _split_markdown_table_row(line)
        if cells and cells[0].strip() == first_cell:
            return cells
    return None


def _contains_unnegated_phrase(content, phrases):
    for line in content.splitlines():
        lower_line = line.lower()
        for phrase in phrases:
            phrase_lower = phrase.lower()
            if (
                phrase_lower in lower_line
                and not _line_has_scoped_claim_negation(line, phrase_lower)
                and not _line_has_structured_status_negation(line, phrase_lower)
            ):
                return True
    return False


def _line_has_structured_status_negation(line, phrase):
    lower = line.lower()
    negated_values = (
        "no",
        "false",
        "fail",
        "failed",
        "blocked",
        "not_run",
        "not run",
        "missing",
        "unavailable",
        "not_available",
        "not available",
    )
    value_pattern = "|".join(re.escape(value) for value in negated_values)
    for match in re.finditer(re.escape(phrase.lower()), lower):
        suffix = lower[match.end():match.end() + 96]
        if re.match(rf"\s*(?:[:=：|]\s*)+(?:status\s*)?(?:{value_pattern})(?![a-z0-9_-])", suffix):
            return True
        if re.match(rf"\s+(?:is|are)\s+(?:{value_pattern})(?![a-z0-9_-])", suffix):
            return True
    return False


def _risk_status_is_closed(status):
    normalized = status.strip().strip("*`").lower()
    return normalized in {
        "已关闭",
        "关闭",
        "closed",
        "resolved",
        "closed/resolved",
        "resolved/closed",
    } or normalized.startswith("已关闭 ") or normalized.startswith("closed ")


def check_one_dot_zero_release_blockers(
    root=None,
    risk_log_path=None,
    external_validation_path=None,
    official_submission_path=None,
    desktop_lifecycle_path=None,
):
    """FIX-130: hard-block 1.0.0 while final release evidence remains insufficient."""
    root = Path(root) if root is not None else ROOT
    risk_log_path = Path(risk_log_path) if risk_log_path is not None else root / ".governance/risk-log.md"
    external_validation_path = (
        Path(external_validation_path)
        if external_validation_path is not None
        else root / "docs/requirements/external-project-validation-0.49.0.md"
    )
    official_submission_path = (
        Path(official_submission_path)
        if official_submission_path is not None
        else root / "docs/requirements/official-submission-final-bundle-review-0.49.0.md"
    )
    desktop_lifecycle_path = (
        Path(desktop_lifecycle_path)
        if desktop_lifecycle_path is not None
        else root / "docs/requirements/codex-desktop-marketplace-lifecycle-0.49.0.md"
    )

    issues = []

    if not risk_log_path.is_file():
        issues.append(f"{_display_path(risk_log_path, root)}: missing RISK-036 status for 1.0.0 release")
    else:
        risk_content = risk_log_path.read_text(encoding="utf-8")
        risk_row = _markdown_table_row_by_first_cell(risk_content, "RISK-036")
        if risk_row is None:
            issues.append(f"{_display_path(risk_log_path, root)}: missing RISK-036 row for 1.0.0 release")
        else:
            status = risk_row[8].strip() if len(risk_row) > 8 else ""
            if not _risk_status_is_closed(status):
                status_detail = status or "missing/unknown"
                issues.append(
                    "RISK-036 is not explicitly closed "
                    f"(`{status_detail}`); 1.0.0 release is blocked until the risk is closed"
                )

    if not external_validation_path.is_file():
        issues.append(f"{_display_path(external_validation_path, root)}: missing external validation fact source")
    else:
        external_content = external_validation_path.read_text(encoding="utf-8")
        external_lower = external_content.lower()
        external_blocked_tokens = [
            "not a full pass",
            "no external project validation pass",
            "no external project validation full pass",
            "no external validation pass",
            "no external validation full pass",
            "external validation still未 full pass",
            "external validation full pass is missing",
            "missing external validation full pass",
            "still not full pass",
            "partial / blocked",
            "partial/blocked",
        ]
        external_pass_tokens = [
            "external validation full pass",
            "external project validation full pass",
            "two external project validations full pass",
            "2 external project validations full pass",
        ]
        has_positive_external_pass = _contains_unnegated_phrase(external_content, external_pass_tokens)
        if any(token in external_lower for token in external_blocked_tokens):
            issues.append(
                f"{_display_path(external_validation_path, root)}: external validation full PASS is missing"
            )
        elif not has_positive_external_pass:
            issues.append(
                f"{_display_path(external_validation_path, root)}: missing explicit external validation full PASS evidence"
            )

    if not official_submission_path.is_file():
        issues.append(f"{_display_path(official_submission_path, root)}: missing official submission result fact source")
    else:
        official_content = official_submission_path.read_text(encoding="utf-8")
        official_lower = official_content.lower()
        official_blocked_tokens = [
            "does not report any official response",
            "no official approval",
            "no marketplace approval",
            "not_available",
            "official result is not_available",
            "missing official submission result",
            "missing official approval",
            "without official approval",
        ]
        official_positive_tokens = [
            "official submission result: approved",
            "official submission result approved",
            "official approval granted",
            "officially approved",
            "marketplace approval granted",
        ]
        has_positive_official_result = _contains_unnegated_phrase(official_content, official_positive_tokens)
        if any(token in official_lower for token in official_blocked_tokens):
            issues.append(
                f"{_display_path(official_submission_path, root)}: official submission result or approval evidence is missing"
            )
        elif not has_positive_official_result:
            issues.append(
                f"{_display_path(official_submission_path, root)}: missing explicit official submission result or approval evidence"
            )

    if not desktop_lifecycle_path.is_file():
        issues.append(f"{_display_path(desktop_lifecycle_path, root)}: missing Codex Desktop lifecycle fact source")
    else:
        desktop_content = desktop_lifecycle_path.read_text(encoding="utf-8")
        desktop_lower = desktop_content.lower()
        desktop_pass = _contains_unnegated_phrase(desktop_content, [
            "codex desktop marketplace-management e2e pass",
            "desktop lifecycle e2e pass",
            "desktop lifecycle pass",
        ])
        conservative_disposition = any(token in desktop_lower for token in [
            "conservative blocked carry-forward",
            "conservative blocked carry forward",
            "carry forward the desktop lifecycle blocker",
            "keeps 1.0.0 blocked",
            "desktop ui install/enable/invoke/upgrade/uninstall remains blocked/not_run",
            "desktop lifecycle remains blocked/not_run",
        ])
        if not desktop_pass and not conservative_disposition:
            issues.append(
                f"{_display_path(desktop_lifecycle_path, root)}: Codex Desktop lifecycle PASS or explicit conservative disposition is missing"
            )

    return issues


PROJECTION_SYNC_PATTERNS = (
    "skills/*/SKILL.md",
    "skills/software-project-governance/SKILL.md",
    "skills/software-project-governance/core/**/*.md",
    "skills/software-project-governance/core/**/*.json",
    "skills/software-project-governance/infra/**/*.py",
    "skills/software-project-governance/infra/**/*.md",
    "skills/software-project-governance/infra/**/*.sh",
    "skills/software-project-governance/infra/hooks/*",
    "skills/software-project-governance/references/**/*.md",
    "commands/*.md",
    # FEAT-038 (AUDIT-154 A-7): `/governance` was split into a router layer plus
    # per-Scenario on-demand documents under `commands/governance/`. The extra
    # pattern keeps the fixture-mirror inventory (and its manifest contract
    # `required_members`) exact — the legacy glob `commands/*.md` does not
    # descend into the new directory.
    "commands/governance/*.md",
    "agents/*.md",
)

# FIX-253 / REQ-112 (design §6.5): injection-contract anchor registry.
# Existence-only anchors over the deterministic injection surfaces — the
# compressed R1/R2/R3 behavior contract must be carried by the DSH persona
# template, the entry SKILL, and the DSH thin pointer without any on-demand
# read. Deliberately asserted as keyword presence, never full-text equality
# (design §4 principle 3: prose-equality checks are brittle). Placement note
# (design §6.5 R0-S4): this literal lives FAR away from the REQUIRED_SNIPPETS
# block and its "# ── Manifest" anchor line so checks/version.py L58 regex
# (`REQUIRED_SNIPPETS\s*=\s*\{(?P<body>.*?)\n\}\n{2,}# ── Manifest`) keeps
# matching — do not move it into that region.
#
# FIX-272 / FEAT-010 R0 F1: the `@version-line` marker is a DYNAMIC anchor —
# at check time it resolves to the persona version line
# `治理工作流（v<SKILL.md frontmatter version>）` of the authoritative source
# (FIX-253 §6.6.3 pattern), so the guard itself can never drift to a stale
# hardcoded literal (the FIX-250 precedent: preset version line silently
# drifted to bundle end users). Unresolvable authority → FAIL (fail-closed).
VERSION_LINE_ANCHOR = "@version-line"

INJECTION_CONTRACT_ANCHORS = {
    # FIX-310 / DEC-187: the composition template is the SINGLE persona surface
    # (the former second spelling, `presets/governance/agent.cordis.yml`, is
    # gone with the copy model), so it carries the whole anchor set:
    #   * FIX-274 / F-02 — the M7.7 real-environment contract keywords;
    #   * FIX-272 / FEAT-010 R0 F1 — the persona VERSION-LINE same-source guard
    #     (`治理工作流（vX.Y.Z）` must track the SKILL.md authority; the
    #     dsh-persona-version projection guards it too, the dynamic marker here
    #     is the belt-and-braces layer that also covers a hand-edited file).
    "agent-presets/governance/persona.md.template": [
        "关键行为契约", "复审必达", "NEEDS_CHANGE", "完成必推荐",
        "task-priority-analysis", "选项必带依据",
        # FIX-260 / REQ-107: 4th contract line — review conclusions MUST be
        # persisted through the review-record CLI machine path.
        "审查结论必机录", "review-record",
        # FIX-274 / F-02 (M7.7 projection): 5th contract line — user
        # real-environment protection (R1 one-of-three / R4 per-command
        # relay / R5 acceptance wording).
        "真实环境必防护", "三选一", "逐条上报", "隔离环境安装冒烟",
        # FEAT-072 / DEC-266: three-element recommendation-card contract
        # (M7.4 step 6 projection — card prose before AskUserQuestion).
        "三要素", "推荐卡",
        VERSION_LINE_ANCHOR,
    ],
    "skills/software-project-governance/SKILL.md": [
        "关键行为契约", "复审必达", "完成必推荐",
        "task-priority-analysis", "选项必带依据",
        # FIX-274 / F-02 (M7.7 projection): 4th contract item.
        "真实环境必防护", "三选一", "逐条上报", "隔离环境安装冒烟",
        # FEAT-072 / DEC-266: three-element recommendation-card contract
        # (M7.4 step 6 projection — card prose before AskUserQuestion).
        "三要素", "推荐卡",
    ],
    # FEAT-072 / DEC-266: canonical surface — M7.4 step 6c MUST carry the
    # three full card labels; existence-only, fail-closed like every path
    # above.
    "skills/software-project-governance/references/behavior-protocol.md": [
        "服务目标：", "解决问题：", "方案要点：",
    ],
    "adapters/dsh/AGENTS.md.template": ["关键行为契约"],
}

# FEAT-079 / DEC-290(4): ADR-021 B1b staged anchor registry — the B1a
# contract-clause anchors, activation-gated. B1a (text) and B1b (registry)
# are parallel batches with an ordered COMMIT sequence (B1a text commit
# first); this registry therefore does not fail while the B1a text is
# absent: every staged anchor absent = stage INACTIVE (disclosed, the
# commit-order window is legitimate), ANY anchor present = stage ACTIVE and
# every staged anchor is then a hard existence assertion (a partial
# injection fails closed — anti-silent-partial). Keyword-anchored like the
# base registry (ADR-021 §2.1: ordinal counts drift between surfaces,
# keywords do not). The budget twin of this gate (clause tier freeze line,
# DEC-290(6)) lives in checks/injection_budget.py.
INJECTION_CONTRACT_STAGED_ANCHORS = {
    "ADR-021-B1a": {
        # persona face: M1 clause + the persona-only 用户点名 (ADR-021 §2.1
        # file table) + M2 clause.
        "agent-presets/governance/persona.md.template": [
            "推荐必标需求源", "用户点名", "发现即闭环",
        ],
        "skills/software-project-governance/SKILL.md": [
            "推荐必标需求源", "发现即闭环",
        ],
        "skills/software-project-governance/references/behavior-protocol.md": [
            "推荐必标需求源", "发现即闭环",
        ],
        "adapters/dsh/AGENTS.md.template": [
            "推荐必标需求源", "发现即闭环",
        ],
    },
}


_extract_skill_version = version_checks.extract_skill_version


def _extract_json_version(path):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(payload.get("version", "")).strip()


def _extract_plan_workflow_version(path):
    if not path.is_file():
        return ""
    content = path.read_text(encoding="utf-8")
    match = re.search(r"工作流版本\*\*:\s*([0-9]+\.[0-9]+\.[0-9]+)", content)
    if not match:
        match = re.search(r"工作流版本.*?([0-9]+\.[0-9]+\.[0-9]+)", content)
    return match.group(1) if match else ""


def _projection_hash(path):
    text = _read_text_normalized(path)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _projection_source_files(root, patterns=None):
    root = Path(root)
    patterns = patterns or PROJECTION_SYNC_PATTERNS
    files = set()
    for pattern in patterns:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if "__pycache__" in rel or rel.endswith(".pyc"):
                continue
            files.add(rel)
    return sorted(files)


def _projection_target_tracked_files(root, target_dir):
    """Return target fixture files tracked by git, or None outside a git checkout."""
    root = Path(root)
    target_dir = Path(target_dir)
    if not (root / ".git").exists():
        return None
    try:
        target_rel = target_dir.relative_to(root).as_posix()
    except ValueError:
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--", target_rel],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    prefix = target_rel.rstrip("/") + "/"
    tracked = set()
    for line in result.stdout.splitlines():
        item = line.strip().replace("\\", "/")
        if item.startswith(prefix):
            tracked.add(item[len(prefix):])
    return tracked


def _target_fixture_file_is_checkable(rel_path, target_tracked):
    if target_tracked is None:
        return True
    return rel_path.replace("\\", "/") in target_tracked


def check_projection_sync(root=None, target_dir=None, patterns=None):
    """Delegate projection compatibility checks to the Phase 6 module."""
    return projection_checks.check_projection_sync(
        Path(root) if root is not None else ROOT,
        Path(target_dir) if target_dir is not None else None,
        patterns,
    )


def check_injection_contract(root=None):
    """FIX-253 / REQ-112 (design §6.5): injection-surface anchor existence check.

    Asserts that each deterministic injection surface (DSH persona template /
    entry SKILL / DSH thin pointer) carries its anchor keyword set from
    INJECTION_CONTRACT_ANCHORS. Boundary (design §6.5): existence only —
    never full-text equality, and no behavior detection (that boundary stays
    with REQ-107/108/113 per DEC-143).

    FIX-272 / FEAT-010 R0 F1: ``VERSION_LINE_ANCHOR`` entries are DYNAMIC —
    resolved at check time to the persona version line
    ``治理工作流（v<authority>）`` from the SKILL.md frontmatter version, so
    the shipped preset can never silently drift from the release authority
    (FIX-250 precedent). Unresolvable authority → explicit FAIL (fail-closed:
    useless to report a missing keyword when the version source is broken).
    """
    root = Path(root) if root is not None else ROOT
    issues = []
    files_checked = 0
    authority = _extract_skill_version(
        root / "skills/software-project-governance/SKILL.md")
    for relative, anchors in sorted(INJECTION_CONTRACT_ANCHORS.items()):
        path = root / relative
        if not path.is_file():
            issues.append(f"{relative}: injection-surface file missing")
            continue
        files_checked += 1
        text = path.read_text(encoding="utf-8")
        for anchor in anchors:
            if anchor == VERSION_LINE_ANCHOR:
                if not authority:
                    issues.append(
                        f"{relative}: {VERSION_LINE_ANCHOR} unresolved — "
                        "SKILL.md frontmatter version missing")
                    continue
                anchor = f"治理工作流（v{authority}）"
            if anchor not in text:
                issues.append(f"{relative}: anchor missing: {anchor}")
    # FEAT-079 / DEC-290(4): staged anchor faces — activation-gated
    # existence assertions (all-absent → inactive + disclosure; any-present
    # → active, every staged anchor then fails closed when missing).
    staged = {}
    for stage, anchors_by_path in sorted(
            INJECTION_CONTRACT_STAGED_ANCHORS.items()):
        present = {}
        for relative, anchors in sorted(anchors_by_path.items()):
            path = root / relative
            if not path.is_file():
                present[relative] = {anchor: False for anchor in anchors}
                continue
            text = path.read_text(encoding="utf-8")
            present[relative] = {anchor: anchor in text
                                 for anchor in anchors}
        active = any(any(hits.values()) for hits in present.values())
        missing = []
        if active:
            for relative, hits in sorted(present.items()):
                for anchor, hit in hits.items():
                    if not hit:
                        missing.append(
                            f"{relative}: staged anchor missing "
                            f"({stage}): {anchor}")
        staged[stage] = {
            "active": active,
            "missing": missing,
            "anchors_checked": sum(len(v) for v in anchors_by_path.values()),
            "inactive_reason": (
                None if active else
                f"{stage}: no staged anchor present yet — B1a contract "
                "text not landed (activation-gated; DEC-290(4) commit "
                "order: text before registry)"),
        }
        issues.extend(missing)
    staged_summary = "; ".join(
        (f"staged {stage}: inactive (B1a text not landed; DEC-290(4))"
         if not state["active"] else
         f"staged {stage}: active, {state['anchors_checked']} anchors guarded")
        for stage, state in sorted(staged.items()))
    return {
        "issues": issues,
        "files_checked": files_checked,
        "anchors_checked": sum(len(v) for v in INJECTION_CONTRACT_ANCHORS.values()),
        "staged": staged,
        "staged_summary": staged_summary,
    }


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
        release_gate_timeout_env=_RELEASE_GATE_TIMEOUT_ENV,
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
    """Map a task_priority.PriorityReport to provenance_domain row dicts.

    Bucket vocabulary parity is the contract (module docstring of
    provenance_domain): recommended_next → recommended, non_executable →
    non_executable, blocked → blocked, completed → completed.
    """
    def _row(task, bucket):
        return {
            "task_id": task.task_id,
            "demand_source": task.demand_source,
            "bucket": bucket,
            "priority": task.priority,
            "target_version": task.target_version,
        }

    rows = []
    for task in getattr(report, "recommended_next", None) or []:
        rows.append(_row(task, "recommended"))
    for task in getattr(report, "non_executable", None) or []:
        rows.append(_row(task, "non_executable"))
    for blocked in getattr(report, "blocked", None) or []:
        task = getattr(blocked, "task", None) or blocked
        rows.append(_row(task, "blocked"))
    for task in getattr(report, "completed", None) or []:
        rows.append(_row(task, "completed"))
    return rows


def _provenance_rows_for_governance(tracker_path=None, governance_dir=None):
    """Live provenance rows: parse → demand-source resolve → report → rows.

    The same orchestration run_cli_analysis uses (L2514-2520): parse the
    plan-tracker, resolve demand sources against the triage records +
    revision streams, then compute the bucketed report.
    """
    import task_priority as tpa
    path = Path(tracker_path) if tracker_path else SAMPLE_PATH
    gov = Path(governance_dir) if governance_dir else GOVERNANCE_DIR
    if not path.is_file():
        return []
    try:
        resolved, _lag_warnings = tpa._resolve_row_demand_sources(
            tpa.parse_task_dependencies(path), gov)
        report = tpa.compute_unblocked_tasks(
            resolved,
            archive_completed_ids=tpa.read_archive_index_completed_ids(gov))
    except Exception:
        return []
    return _provenance_rows_from_report(report)


def _collect_session_closure_events(governance_dir=None, today=None):
    """FEAT-083: thin delegation to the shared collection leaf.

    The W(session) collection core (the evidence/risk row arms, the
    deferred-ledger arm, the window note) lives in
    ``checks.provenance_domain.collect_session_closure_events`` — engine
    (Check 42) and bootstrap (the behavior.session_closure sub-face) both
    consume that ONE source; the FEAT-082 bootstrap mirror is retired
    (zero second implementation — review-FEAT-082-CODE-R0 §6.3). The
    legacy signature is preserved (Check 42 + the FEAT-080/081 test call
    sites unchanged), including the ``governance_dir=None →
    GOVERNANCE_DIR`` default the leaf cannot own (it must stay
    engine-global-free); the delegation import is FUNCTION-LOCAL so the
    frozen cold-import face (ArchGuard R6) is untouched.
    """
    from checks.provenance_domain import collect_session_closure_events
    return collect_session_closure_events(
        governance_dir if governance_dir else GOVERNANCE_DIR, today=today)


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
    plugin_release = not _host_plugin_roots_divergent()
    replay_hint = _tagged_release_replay_hint(version) if plugin_release else None
    if replay_hint:
        return {
            "pass": False,
            "issues": [replay_hint],
            "details": {"release_replay": {"pass": False, "issues": [replay_hint]}},
        }

    issues = []
    details = {}

    if plugin_release:
        version_issues = check_version_consistency()
        version_failures = [issue for issue in version_issues if not issue.startswith("[WARN]")]
        details["version_consistency"] = {
            "pass": not version_failures,
            "issues": version_failures,
            "warnings": [issue for issue in version_issues if issue.startswith("[WARN]")],
        }
        issues.extend(f"version consistency: {issue}" for issue in version_failures)

        pack_status_issues = check_governance_pack_status()
        details["governance_pack_status"] = {
            "pass": not pack_status_issues,
            "issues": pack_status_issues,
            "boundary": (
                "packs are capability modules; profiles are intensity presets; "
                "pack enabled or membership is not task evidence, independent review, "
                "quality gate, release gate, official approval, marketplace approval, "
                "universal/full runtime support, or 1.0.0 production-ready proof"
            ),
        }
        issues.extend(f"governance pack status: {issue}" for issue in pack_status_issues)

    # FEAT-080 / ADR-021 §2.2.4: provenance release gate (DEC-290(5) wiring;
    # NF-2 semantics — 排期/改期豁免 rides the task row's target_version,
    # never a revision event). A release version carrying OPEN
    # machine-signal work while user-named items stay open → FAIL; payload
    # rows with undeclared provenance → FAIL (未申报 fail-closed — the
    # release gate is the last line); no parseable version → SKIP face
    # inside the sub-check itself (never a silent PASS).
    if version:
        from checks import provenance_domain as _provenance_gate_mod
        provenance_rows = _provenance_rows_for_governance()
        admission = _provenance_gate_mod.check_release_admission(
            provenance_rows, {"version": str(version)})
        details["provenance_release_gate"] = {
            "pass": admission["status"] != "FAIL",
            "status": admission["status"],
            "issues": admission["issues"],
            "warnings": admission["warnings"],
            "machine_signal_payload": admission["machine_signal_payload"],
            "open_user_named": admission["open_user_named"],
            "deferred_user_named": admission["deferred_user_named"],
            "undeclared_payload": admission["undeclared_payload"],
        }
        issues.extend(f"provenance release gate: {issue}"
                      for issue in admission["issues"])
        for warning in admission["warnings"]:
            details.setdefault("release_warnings", []).append(
                f"provenance release gate: {warning}")

    # A Git lookup failure is distinct from denied access to a resolved hook.
    from checks.sd_integrity import release_face_paths, scan_sd_readability
    _sd_face = release_face_paths(HOST_PROJECT_ROOT, PLUGIN_ROOT if plugin_release else None)
    _sd_face_error = _sd_face.get("error")
    if _sd_face_error:
        issues.append(f"sd integrity: {_sd_face_error}")
    sd_scan = scan_sd_readability(_sd_face["paths"])
    if _sd_face_error:
        sd_scan["pass"] = False
    sd_issues = [f"{path} unreadable — remediate: {cmd}"
                 for path, cmd in zip(sd_scan["unreadable"], sd_scan["remediation"])]
    details["sd_integrity"] = {**sd_scan, "face_error": _sd_face_error, "issues": sd_issues}
    issues.extend(f"sd integrity: {issue}" for issue in sd_issues)

    if plugin_release:
        adapter_issues = check_agent_adapter_contract(run_runtime=run_runtime_adapters)
        details["agent_adapters"] = {
            "pass": not adapter_issues,
            "issues": adapter_issues,
            "runtime": run_runtime_adapters,
        }
        issues.extend(f"agent adapters: {issue}" for issue in adapter_issues)

        projection_result = check_projection_sync()
        details["projection_sync"] = {
            "pass": projection_result["pass"],
            "issues": projection_result["issues"],
            "mirrors_checked": projection_result["mirrors_checked"],
            "mirrors_discovered": projection_result["mirrors_discovered"],
            "mirrors_skipped_untracked": projection_result["mirrors_skipped_untracked"],
            "source_version": projection_result["source_version"],
        }
        issues.extend(f"projection sync: {issue}" for issue in projection_result["issues"])

        cross_ref_result = check_cross_references()
        cross_ref_issues = (
            [f"dangling reference: {item['source']}:{item['line']} -> {item['target']}" for item in cross_ref_result["dangling"]]
            + [f"deprecated reference: {item['source']}:{item['line']} -> {item['target']}" for item in cross_ref_result["deprecated"]]
            + [f"circular reference: {' -> '.join(cycle)}" for cycle in cross_ref_result["cycles"]]
            # FIX-432 (F-4/F-A2) / FIX-436 F-8 wording: quote-sync issues ride
            # the same gate; the current check_cross_references() always emits
            # the key — .get only tolerates pre-FIX-432/partial dict shapes
            # (e.g. fixtures or older cached results) that lack it.
            + [f"quote sync: {issue}" for issue in cross_ref_result.get("quote_sync", [])]
        )
        details["cross_references"] = {
            "pass": not cross_ref_issues,
            "issues": cross_ref_issues,
        }
        issues.extend(cross_ref_issues)

    archive_result = check_archive_integrity()
    archive_issues = archive_result.get("issues", [])
    details["archive_integrity"] = {
        "pass": not archive_issues,
        "issues": archive_issues,
        "pending_archive_tasks": archive_result.get("pending_archive_tasks", 0),
    }
    issues.extend(f"archive integrity: {issue}" for issue in archive_issues)

    if plugin_release:
        release_docs_issues = check_release_docs_coverage(version)
        details["release_docs"] = {
            "pass": not release_docs_issues,
            "issues": release_docs_issues,
            "version": version,
        }
        issues.extend(f"release docs: {issue}" for issue in release_docs_issues)

    lineage_result = check_release_lineage(
        version=version,
        mode=lineage_mode,
        release_commit=release_commit,
        remote=lineage_remote,
    )
    details["release_lineage"] = lineage_result
    issues.extend(f"release lineage: {issue}" for issue in lineage_result["issues"])

    # Release certification belongs to the candidate/version being shipped.
    if lineage_mode == "candidate":
        from loop_workflow import release_issues
        scoped_issues = release_issues(HOST_PROJECT_ROOT, release_unit, version)
        details["release_loop"] = {"pass": not scoped_issues, "unit": release_unit, "issues": scoped_issues}
        issues.extend(scoped_issues)

    # Delivery acceptance also applies when broader execution gates are disabled.
    from delivery_acceptance import evaluate_delivery_acceptance

    delivery_acceptance = evaluate_delivery_acceptance(
        HOST_PROJECT_ROOT,
        release_version=version,
        required=require_delivery_evidence,
        released_history=lineage_mode == "released")
    details["delivery_acceptance"] = delivery_acceptance
    issues.extend(f"delivery acceptance: {issue}" for issue in delivery_acceptance["issues"])

    one_dot_zero_blocker_issues = []
    if plugin_release and version == "1.0.0":
        one_dot_zero_blocker_issues = check_one_dot_zero_release_blockers()
        issues.extend(f"1.0.0 blocker: {issue}" for issue in one_dot_zero_blocker_issues)
    if plugin_release:
        details["one_dot_zero_blockers"] = {
            "pass": not one_dot_zero_blocker_issues,
            "issues": one_dot_zero_blocker_issues,
            "required": plugin_release and version == "1.0.0",
            "version": version,
        }

    execution_gate_results = []
    execution_gate_issues = []
    if run_execution_gates and plugin_release:
        execution_gate_results = run_release_execution_gates(runner=execution_gate_runner)
        execution_gate_issues = [result["issue"] for result in execution_gate_results if result.get("issue")]
        issues.extend(f"execution gate: {issue}" for issue in execution_gate_issues)
    if plugin_release:
        details["execution_gates"] = {
            "pass": not execution_gate_issues,
            "issues": execution_gate_issues,
            "required": run_execution_gates and plugin_release,
            "results": execution_gate_results,
        }

    if not plugin_release:
        ci = check_ci_evidence(repo_root=HOST_PROJECT_ROOT)
        ci_issues = [item["reason"] for item in ci["violations"]]
        details["project_ci_evidence"] = {
            **ci, "pass": not ci_issues, "issues": ci_issues,
            "skipped": ci["verdict"] == "no-verdict", "skip_reason": ci["reason"],
        }
        issues.extend(f"project CI: {issue}" for issue in ci_issues)

    # ── FEAT-016 / RISK-049 ③: dsh upgrade regression gate component ──
    # The isolated dsh upgrade re-verification command set (reuses the
    # FEAT-015 preset smoke: temp DSH_HOME redirection, real ~/.dsh
    # zero-write, M7.7 (a)) actually runs whenever execution gates run for
    # a CANDIDATE release and blocks the release on FAIL. Skip paths stay
    # explicit (WARN disclosure — never a silent absence, never a new FAIL
    # for history queries): --skip-execution-gates, and BR-4
    # released-history checks (effective lineage or gate-sequence mode
    # "released", DEC-153 ②) — a working-tree regression proves nothing
    # about an already-published version.
    dsh_regression_skipped_reason = None
    dsh_regression_results = []
    dsh_regression_issues = []
    dsh_regression_isolation = None
    if not plugin_release:
        dsh_regression_skipped_reason = "DSH preset regression applies to the governance plugin release."
    elif not run_execution_gates:
        dsh_regression_skipped_reason = (
            "execution gates skipped (--skip-execution-gates); the dsh "
            "upgrade regression command set was not run — WARN disclosure, "
            "not a release verdict")
    elif lineage_mode == "released":
        dsh_regression_skipped_reason = (
            "released-history check (BR-4 / DEC-153 ②); the dsh upgrade "
            "regression targets the candidate working tree and is not run "
            "for already-published version queries — WARN disclosure")
    else:
        dsh_regression = (dsh_upgrade_regression_runner
                          or run_dsh_upgrade_regression_gates)()
        dsh_regression_results = dsh_regression["results"]
        dsh_regression_issues = dsh_regression["issues"]
        dsh_regression_isolation = dsh_regression.get("isolation")
        issues.extend(f"dsh upgrade regression: {issue}"
                      for issue in dsh_regression_issues)
    details["dsh_upgrade_regression"] = {
        "pass": not dsh_regression_issues,
        "skipped": dsh_regression_skipped_reason is not None,
        "skip_reason": dsh_regression_skipped_reason,
        "required": dsh_regression_skipped_reason is None,
        "results": dsh_regression_results,
        "issues": dsh_regression_issues,
        "isolation": dsh_regression_isolation,
        "boundary": (
            "isolated temp-DSH_HOME preset install/load smoke; proves the "
            "packaged preset session boots in a redirected home with zero "
            "real-home writes — not a live marketplace upgrade"),
    }

    changelog_path = changelog_path or (ROOT / "project/CHANGELOG.md" if plugin_release else HOST_PROJECT_ROOT / "CHANGELOG.md")
    changelog_issues = []
    if version:
        if not re.fullmatch(r"\d+\.\d+\.\d+", version):
            changelog_issues.append(f"release version `{version}` is not semver X.Y.Z")
        if require_changelog:
            if not changelog_path.exists():
                changelog_issues.append(f"{_display_path(changelog_path)}: missing changelog")
            else:
                changelog_content = changelog_path.read_text(encoding="utf-8")
                if f"## [{version}]" not in changelog_content:
                    changelog_issues.append(f"{_display_path(changelog_path)}: missing changelog entry ## [{version}]")
    elif require_changelog:
        changelog_issues.append("--require-changelog requires --version")

    details["changelog"] = {
        "pass": not changelog_issues,
        "issues": changelog_issues,
        "required": require_changelog,
        "version": version,
    }
    issues.extend(changelog_issues)

    # ── FEAT-075 (DEC-278 单元二 item 4 / M-0 prerequisite 4 of 5): the
    # exception-acceptance disclosure. Annotation-only — the block NEVER
    # touches ``issues`` (a release verdict can't be flipped by an
    # exception), and it is ABSENT when no .governance/exceptions.json
    # exists (backward compatibility; the Coordinator registers the real
    # exceptions after M-0, tests use synthetic fixtures).
    exceptions_detail = _release_exception_block()
    if exceptions_detail is not None:
        details["governance_exceptions"] = exceptions_detail

    return {
        "pass": not issues,
        "issues": issues,
        "details": details,
    }


GIT_LINEAGE_TIMEOUT_SECONDS = 15
GIT_REMOTE_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}\Z")


def _run_git_lineage(args, root=None):
    root = Path(root or HOST_PROJECT_ROOT)
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=GIT_LINEAGE_TIMEOUT_SECONDS,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return 124, "", f"git command timed out after {GIT_LINEAGE_TIMEOUT_SECONDS}s"
    except OSError as exc:
        return 125, "", f"git command could not be started ({type(exc).__name__})"
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _validated_git_remote_name(remote):
    """Return a safe Git remote name; URLs, options, and control/whitespace input are rejected."""
    if not isinstance(remote, str) or not GIT_REMOTE_NAME_RE.fullmatch(remote):
        return None
    if ".." in remote or "//" in remote:
        return None
    return remote


def check_release_lineage(version, mode="candidate", release_commit=None, remote="origin", root=None):
    """Delegate release lineage checks while preserving the 0.65.3 API."""
    return commit_checks.check_release_lineage(
        version,
        mode=mode,
        release_commit=release_commit,
        remote=remote,
        root=Path(root or HOST_PROJECT_ROOT),
        git=lambda args, git_root, _timeout: _run_git_lineage(args, git_root),
        timeout=GIT_LINEAGE_TIMEOUT_SECONDS,
    )



def _specialist_skill_owner_issues(root, router):
    """Check the same role files and skill-table binding that a dispatched agent reads."""
    roles = {path.stem: path for path in (root / "agents").glob("*.md")}
    expected = {role.lower().replace(" ", "-") for role in _host_policy('ACTIVE_AGENT_ROLES')}
    issues = [f"active role files differ: {sorted(set(roles) ^ expected)}"] if set(roles) != expected else []
    specialists = {path.parent.name for path in (root / "skills").glob("*/SKILL.md")}
    specialists -= {"software-project-governance", "main-workflow"}
    owners = {}
    for role, path in roles.items():
        if f"agents/{role}.md" not in router:
            issues.append(f"dispatch route missing role {role}")
        for name in re.findall(r"^\|\s*`?([a-z][a-z0-9-]*)`?\s*\|", path.read_text(encoding="utf-8"), re.M):
            if name not in specialists:
                issues.append(f"{role}: unknown bound skill {name}")
            owners.setdefault(name, set()).add(role)
    issues.extend(f"no dispatched role consumes {name}" for name in sorted(specialists - owners.keys()))
    if owners.get("stage-operations") != {"release"}:
        issues.append("operational feedback requires Release as the responsible role")
    return issues


def check_architecture_fact_source(
    skill_path=None,
    skill_index_path=None,
    architecture_path=None,
    governance_command_path=None,
    agent_protocol_path=None,
    governance_developer_prompt_path=None,
):
    """FIX-065: keep Agent/team architecture facts synchronized."""
    navigation_root = ROOT if architecture_path is None else None
    skill_path = skill_path or ROOT / "skills/software-project-governance/SKILL.md"
    skill_index_path = skill_index_path or ROOT / "skills/software-project-governance/references/skill-index.md"
    architecture_path = architecture_path or ROOT / "project/references/architecture.md"
    governance_command_path = governance_command_path or ROOT / "commands/governance.md"
    agent_protocol_path = agent_protocol_path or ROOT / "skills/software-project-governance/references/agent-communication-protocol.md"
    governance_developer_prompt_path = governance_developer_prompt_path or ROOT / "agents/governance-developer.md"

    documents = (
        skill_path, skill_index_path, architecture_path, governance_command_path,
        agent_protocol_path, governance_developer_prompt_path,
    )
    contents = {path: path.read_text(encoding="utf-8") for path in documents}

    current_navigation = _markdown_section(contents[architecture_path], "## 当前目录导航")
    failures = check_repository_navigation(architecture_path, current_navigation, navigation_root)
    forbidden_patterns = [
        ("legacy 7 groups / 9 Agent narrative", r"7\s*组\s*9\s*Agent|7组9Agent"),
        ("legacy 46-line SKILL.md entry narrative", r"46\s*行"),
        ("legacy entry-layer no behavior rules narrative", r"不包含任何行为规则"),
        ("legacy native-entry exclusion narrative", r"仓库不包含任何平台原生入口文件"),
    ]
    for path, content in contents.items():
        rel = _display_path(path)
        for label, pattern in forbidden_patterns:
            if re.search(pattern, content):
                failures.append(f"{rel}: forbidden {label}")

    skill_index_content = contents[skill_index_path]
    skill_content = contents[skill_path]
    required_skill_phrases = [
        "Coordinator 融入入口层",
        "Coordinator 接管用户交互",
        "Producer-Reviewer 分离",
    ]
    for phrase in required_skill_phrases:
        if phrase not in skill_content:
            failures.append(f"{_display_path(skill_path)}: missing architecture fact phrase: {phrase}")

    if "skills/software-project-governance/SKILL.md" not in contents[governance_command_path]:
        failures.append(f"{_display_path(governance_command_path)}: missing dispatch route to the main SKILL")
    if "后置审查" not in _markdown_section(skill_content, "## Agent 分发路由"):
        failures.append(f"{_display_path(skill_path)}: missing post-review routing for the review reader")
    if navigation_root is not None:
        failures.extend(_specialist_skill_owner_issues(navigation_root, skill_content))

    rel_skill_index = _display_path(skill_index_path)
    from governance_readers import markdown_table_cells
    routes = [cells for line in skill_index_content.splitlines()
              if len(cells := markdown_table_cells(line)) == 3 and "`" in cells[1]]
    reviewed = set()
    governance_route = False
    for activity, producers, consumers in routes:
        skill_ids = re.findall(r"`([a-z][a-z0-9-]*)`", producers + " " + consumers)
        for skill_id in skill_ids:
            if not (ROOT / "skills" / skill_id / "SKILL.md").is_file():
                failures.append(f"{rel_skill_index}: {activity} references missing skill {skill_id}")
        if not consumers.strip():
            failures.append(f"{rel_skill_index}: {activity} has no artifact consumer")
        local_reviewers = re.findall(r"`([a-z]+-review)`", consumers)
        reviewed.update(local_reviewers)
        if local_reviewers and not any(role in consumers for role in _host_policy('NAMED_REVIEWER_ROLES')):
            failures.append(f"{rel_skill_index}: {activity} needs a named independent reviewer")
        if "Governance Developer" in producers and "`code-review`" in consumers and "Code Reviewer" in consumers:
            governance_route = True
    if not governance_route:
        failures.append(f"{rel_skill_index}: missing Governance Developer → independent Code Reviewer route")
    for name in sorted(set(_host_policy('LOOP_ROLE_SKILL_CONTRACTS')) - reviewed):
        failures.append(f"{rel_skill_index}: missing independent consumer for {name}")
    agent_protocol_content = contents[agent_protocol_path]
    rel_protocol = _display_path(agent_protocol_path)
    for role in _host_policy('ACTIVE_AGENT_ROLES'):
        if not _markdown_has_heading(agent_protocol_content, 3, role):
            failures.append(f"{rel_protocol}: missing active role communication contract: {role}")
    for reviewer_role in _host_policy('NAMED_REVIEWER_ROLES'):
        if not _markdown_has_heading(agent_protocol_content, 3, reviewer_role):
            failures.append(f"{rel_protocol}: missing named reviewer communication contract: {reviewer_role}")
    if _markdown_has_heading(agent_protocol_content, 3, "Reviewer"):
        failures.append(f"{rel_protocol}: generic Reviewer communication contract is forbidden")

    governance_developer_protocol = _markdown_section(agent_protocol_content, "### Governance Developer")
    required_governance_developer_protocol_phrases = [
        "Proposed evidence-log entry",
        "Proposed decision-log / risk-log entry",
    ]
    if not governance_developer_protocol:
        failures.append(f"{rel_protocol}: missing Governance Developer communication contract")
    else:
        for phrase in required_governance_developer_protocol_phrases:
            if phrase not in governance_developer_protocol:
                failures.append(f"{rel_protocol}: Governance Developer contract missing {phrase}")

    governance_developer_prompt_content = contents[governance_developer_prompt_path]
    rel_governance_developer_prompt = _display_path(governance_developer_prompt_path)
    if not re.search(r"治理记录由 Coordinator.{0,12}写回|Coordinator 负责最终写回", governance_developer_prompt_content):
        failures.append(f"{rel_governance_developer_prompt}: missing coordinator governance writeback boundary")
    if not re.search(r"(?:不|不得)直接写\s*`\.governance/`", governance_developer_prompt_content):
        failures.append(f"{rel_governance_developer_prompt}: direct governance writes must be prohibited")
    for path in (skill_path, skill_index_path, agent_protocol_path):
        rel = _display_path(path)
        for line_no in _generic_reviewer_cells(contents[path]):
            failures.append(f"{rel}:{line_no}: generic Reviewer role is forbidden; use named reviewer roles")

    for failure in failures:
        print(f"[FAIL] architecture fact source: {failure}")
    if not failures:
        print("[OK] architecture fact source synchronized")
    return failures


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
    return read(path, entry_files=PLATFORM_ENTRY_FILES, product_patterns=PRODUCT_CODE_PATTERNS)


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
    """Check that recent commit messages contain task ID references.

    Per M7.4 step 4 and M7.5 step 4, every commit message MUST contain
    a task ID as prefix (e.g., "AUDIT-044: description", "MAINT-028: description").
    This function is the external validation counterpart — it detects commits
    without task ID prefixes, which indicate untracked modifications.

    FIX-420 revert awareness: a revert of tracked work quotes the original
    subject (``Revert "FIX-397: ..."``), so the tracked-task evidence lives
    at the start of the quoted original subject, not at the message start.
    Such a commit counts as tracked, and ``task_id`` records the ORIGINAL
    task ID in plain machine-readable form (e.g. "FIX-397" — no decorated
    "(revert)" suffix, so downstream consumers can match it with the same
    ``[A-Z]+-\\d+`` caliber). Fail-closed boundary: ONLY a ``Revert "``
    prefix whose quoted original subject itself starts with a legal task
    ID counts as tracked — plain no-ID subjects and reverts of no-ID
    subjects remain reported as untracked.

    Returns: dict with commits list, issues list, and summary stats.
    """
    import subprocess
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "log", f"--format=%H %s", f"-{limit}"],
            capture_output=True, text=True, timeout=10, encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            return {"error": f"git log failed: {result.stderr}", "commits": [], "issues": []}
    except FileNotFoundError:
        return {"error": "git command not found", "commits": [], "issues": []}
    except Exception as e:
        return {"error": str(e), "commits": [], "issues": []}

    commits = []
    issues = []
    # Match task ID prefix at start of commit message: "AUDIT-044: ..." or "MAINT-028: ..."
    task_id_pattern = re.compile(r"^([A-Z]+-\d+)")
    # FIX-420: revert subjects quote the original — `Revert "FIX-397: ..."`.
    revert_subject_pattern = re.compile(r'^Revert "([^"]*)"')

    if not result.stdout:
        return {"error": "git log returned empty output", "commits": [], "issues": []}

    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split(" ", 1)
        if len(parts) < 2:
            continue
        sha = parts[0][:7]
        message = parts[1]

        task_match = task_id_pattern.match(message)
        if task_match is None:
            # FIX-420: fall back to the quoted original subject of a revert.
            revert_match = revert_subject_pattern.match(message)
            if revert_match is not None:
                task_match = task_id_pattern.match(revert_match.group(1))
            else:
                # A GitHub-generated merge may have no ticket in its title.
                # Its incoming ticket applies only when Git proves that the
                # wrapper contributes no additional content or divergence.
                task_match = commit_checks.github_merge_task_match(ROOT, parts[0], message, task_id_pattern)
        has_task_id = task_match is not None
        task_id = task_match.group(1) if has_task_id else None

        commit_info = {
            "sha": sha,
            "message": message,
            "has_task_id": has_task_id,
            "task_id": task_id,
        }
        commits.append(commit_info)

        if not has_task_id:
            issues.append(commit_info)

    return {
        "commits": commits,
        "issues": issues,
        "total_checked": len(commits),
        "without_task_id": len(issues),
    }


def check_task_deadline():
    """Check for non-completed tasks whose planned completion date has passed.

    Per AUDIT-048: plan-tracker has "计划完成" column for each task,
    but when the date passes with task still in "未开始" or "进行中",
    nothing detects or escalates it. This is the same pattern as risk escalation
    (AUDIT-045) — deadline fields exist but are not enforced.

    Returns: dict with overdue tasks list and summary stats.
    """
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    today = date.today()
    overdue = []
    all_active = 0

    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| ") or "---" in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 15:
            continue

        task_id_match = re.match(r"([A-Z]+-\d+)", parts[1])
        if not task_id_match:
            continue

        task_id = task_id_match.group(1)
        status = parts[10] if len(parts) > 10 else ""
        priority = parts[11] if len(parts) > 11 else ""
        # Column mapping: 0=empty,1=ID,...,12=计划开始,13=计划完成,14=实际完成
        plan_complete_str = parts[13] if len(parts) > 13 else ""

        # Only check non-terminal tasks — FIX-479: shared terminal
        # predicate (_status_is_terminal_cell, same source as the DRI
        # face in check_protocol_compliance) normalizes emoji-prefixed
        # terminal shapes (「✅ 已完成」/「✅ committed」/「✅ 完成」/
        # 「⏳ ✅ committed」); the overdue semantics for genuinely active
        # rows (passed deadline → WARN) are unchanged.
        if _status_is_terminal_cell(status):
            continue

        all_active += 1

        if not plan_complete_str or plan_complete_str == "":
            continue

        try:
            plan_complete = datetime.strptime(plan_complete_str, "%Y-%m-%d").date()
            if today > plan_complete:
                overdue.append({
                    "task_id": task_id,
                    "status": status,
                    "priority": priority,
                    "plan_complete": plan_complete_str,
                    "days_overdue": (today - plan_complete).days,
                })
        except ValueError:
            continue

    # Sort by priority then days overdue
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    overdue.sort(key=lambda t: (priority_order.get(t["priority"], 99), -t["days_overdue"]))

    return {
        "overdue": overdue,
        "total_active": all_active,
        "overdue_count": len(overdue),
    }


# ── CLI commands ─────────────────────────────────────────────────

def cmd_verify(args):
    """Run existing file + snippet verification."""
    print("== Workflow Plugin Verification ==")
    file_failures = check_files()
    snippet_failures = check_snippets()
    architecture_failures = check_architecture_fact_source()
    agent_adapter_failures = check_agent_adapter_contract()
    version_failures = check_version_consistency()
    loop_role_result = check_loop_role_skill_consistency()
    loop_role_failures = [f"[FAIL] loop-role SKILL consistency: {issue}"
                          for issue in loop_role_result["issues"]]
    all_items = (
        file_failures
        + snippet_failures
        + architecture_failures
        + agent_adapter_failures
        + version_failures
        + loop_role_failures
    )

    # Separate WARN (non-blocking drift) from FAIL (hard gate)
    fail_items = [f for f in all_items if not f.startswith("[WARN]")]
    warn_items = [f for f in all_items if f.startswith("[WARN]")]

    if warn_items:
        print("\n== Warnings (non-blocking) ==")
        for w in warn_items:
            print(f"  - {w}")

    if fail_items:
        print("\n== Verification Result: FAILED ==")
        for failure in fail_items:
            print(f"  - {failure}")
        sys.exit(1)

    print("\n== Verification Result: PASSED ==")


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
_W7_TERMINAL_MARKERS = (
    "✅", "已发布", "已关闭", "已终止", "已撤回", "失效", "不可信", "取消", "废弃",
)
_W7_ACTIVE_MARKERS = ("进行中", "待执行", "推进中", "⏳", "🔄")
_W7_TERMINAL_DATE_RE = re.compile(r"^[（(]\s*\d{4}-\d{2}-\d{2}")


def _last_marker_pos(text, markers):
    from plan_status import _last_marker_pos as read
    return read(text, markers)


def _w7_terminal_assertion_positions(text):
    from plan_status import _w7_terminal_assertion_positions as read
    return read(text, markers=_W7_TERMINAL_MARKERS, terminal_date=_W7_TERMINAL_DATE_RE)


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
_WRITER_OP_ANCHOR_RE = re.compile(r"〔op-[0-9a-f]{32}〕")


def _status_is_writer_committed_cell(text):
    from plan_status import _status_is_writer_committed_cell as read
    return read(text, operation_anchor=_WRITER_OP_ANCHOR_RE, state_chain=_WRITER_STATE_MARKER_CHAIN)


def _status_is_completed_cell(cell):
    from plan_status import _status_is_completed_cell as read
    return read(
        cell,
        active_markers=_W7_ACTIVE_MARKERS,
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
    """Scan .md and .py files for path references, build a reference graph,
    and detect: (1) dangling references (target file does not exist),
    (2) deprecated path patterns, (3) circular references (cycle detection).

    Path reference patterns extracted:
    - Markdown: [text](path), bare `` file.md `` paths, `` `path/to/file` ``
    - Python: ROOT / "relative/path" format
    """
    import collections

    scan_dirs = [
        "skills/software-project-governance/",
        "commands/",
        "agents/",
    ]

    # Collect all .md files from scan directories
    md_files = []
    for d in scan_dirs:
        p = ROOT / d
        if p.is_dir():
            md_files.extend(p.rglob("*.md"))

    # Also include verify_workflow.py itself
    py_files = [ROOT / "skills/software-project-governance/infra/verify_workflow.py"]

    # Build: dict[source_relpath] -> list of (target_raw, line_num)
    refs = {}
    source_lines = {}

    for f in md_files + py_files:
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            continue
        source = str(f.relative_to(ROOT)).replace("\\", "/")
        refs[source] = []
        source_lines[source] = content.split("\n")

        in_code_block = False
        for i, line in enumerate(source_lines[source], 1):
            if f.suffix == ".py":
                # Python: ROOT / "relative/path"  pattern
                for m in re.finditer(r'\bROOT\s*/\s*"([^"]+)"', line):
                    target = m.group(1)
                    if Path(target).suffix:
                        refs[source].append((target, i))
            else:
                # ── Code block tracking: skip fenced and indented code blocks ──
                # Fenced code blocks (``` or ~~~). Strip language tag if present.
                if re.match(r'^\s*```', line):
                    in_code_block = not in_code_block
                    continue
                if re.match(r'^\s*~~~', line):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    continue
                # Indented code block (4+ spaces or 1+ tab at line start)
                if re.match(r'^ {4,}', line) or line.startswith('\t'):
                    continue

                # Backticked explicit paths with a directory separator are
                # intentional references and should still be validated.
                for m in re.finditer(r"`([^`]+/[^\s`]+\.(?:md|py)(?:\.template)?)`", line):
                    refs[source].append((m.group(1), i))

                # ── Strip inline code (backtick-quoted) from the line ──
                stripped_line = re.sub(r'`+[^`]*`+', '', line)

                # Markdown: [text](path) — skip http/https/#/mailto links
                for m in re.finditer(r'\[([^\]]*)\]\(([^)]+)\)', stripped_line):
                    target = m.group(2)
                    if not target.startswith(("http://", "https://", "#", "mailto:")):
                        refs[source].append((target, i))
                # Bare paths must include a directory separator.  A lone
                # filename such as "SKILL.md" is often prose shorthand and
                # caused hundreds of dangling-reference false positives after
                # archive cleanup. Markdown links still cover explicit
                # same-directory references.
                for m in re.finditer(r'(?<!["\w/\-.])([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-/]+\.(?:md|py)(?:\.template)?)(?!\w|\.\w)', stripped_line):
                    refs[source].append((m.group(1), i))

    # ── Detect dangling references ──
    dangling = []
    root_relative_prefixes = (
        "skills/", "agents/", "agent-presets/", "commands/", "adapters/", "project/", "docs/",
        ".governance/", ".github/", ".agents/", ".claude-plugin/", ".codex-plugin/",
    )
    skill_root_relative_prefixes = ("core/", "infra/", "references/")
    placeholder_prefixes = ("skill/", "relative/")
    placeholder_markers = ("<", ">", "{", "}", "*")
    entry_source = "skills/software-project-governance/SKILL.md"
    validator_source = "skills/software-project-governance/infra/verify_workflow.py"

    def normalize_ref_target(target):
        target = target.strip()
        if target.startswith("python "):
            target = target.split(None, 1)[1]
        if target.startswith("./"):
            target = target[2:]
        return target

    def is_placeholder_ref(target):
        return target.startswith(placeholder_prefixes) or any(m in target for m in placeholder_markers)

    def source_supports_skill_root_relative(source):
        return (
            source.startswith("skills/software-project-governance/")
            or source.startswith("commands/")
            or source.startswith("agents/")
        )

    def resolve_ref(source, target):
        source_dir = (ROOT / source).parent
        if source.endswith(".py"):
            return (ROOT / target).resolve()
        if target.startswith(root_relative_prefixes):
            return (ROOT / target).resolve()
        if (source_supports_skill_root_relative(source)
                and target.startswith(skill_root_relative_prefixes)):
            return (ROOT / "skills/software-project-governance" / target).resolve()
        return (source_dir / target).resolve()

    def line_text(source, line_num):
        lines = source_lines.get(source, [])
        if 1 <= line_num <= len(lines):
            return lines[line_num - 1].strip()
        return ""

    def is_in_generated_output_section(source, line_num):
        if not source.startswith("agents/"):
            return False
        lines = source_lines.get(source, [])
        in_output = False
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if idx > line_num:
                break
            if stripped.startswith("## "):
                in_output = stripped == "## 输出格式"
                continue
        return in_output

    def is_generated_output_ref(source, target, line_num):
        if not is_in_generated_output_section(source, line_num):
            return False
        if not target.startswith(("docs/", ".github/", "Dockerfile", "docker-compose.yml")):
            return False
        context = "\n".join(source_lines.get(source, [])[max(0, line_num - 4):line_num + 1])
        return "必须生成" in context or line_text(source, line_num).startswith("-")

    def is_external_or_runtime_generated_ref(source, target, line_num):
        current_line = line_text(source, line_num)
        if target.startswith(".governance/"):
            return True
        if target.startswith((
            "project/e2e-test-project/agents/",
            "project/e2e-test-project/commands/",
            "project/e2e-test-project/skills/",
        )):
            return True
        if target == "archive/index.md" and ("不" in current_line and "自动生成" in current_line):
            return True
        return False

    def should_ignore_ref(source, target, line_num):
        return (
            is_placeholder_ref(target)
            or is_generated_output_ref(source, target, line_num)
            or is_external_or_runtime_generated_ref(source, target, line_num)
        )

    for source, targets in refs.items():
        for target, line_num in targets:
            target = normalize_ref_target(target)
            if should_ignore_ref(source, target, line_num):
                continue
            # Resolve target relative to the source file's directory
            try:
                resolved = resolve_ref(source, target)
                resolved.relative_to(ROOT)
            except (ValueError, OSError):
                continue  # outside project or unresolvable
            if not resolved.exists():
                dangling.append({
                    "source": source,
                    "line": line_num,
                    "target": target,
                })

    # ── Detect deprecated path patterns ──
    deprecated_patterns = [
        "skills/software-project-governance/skills/",
        "skills/software-project-governance/agents/",
    ]
    deprecated = []
    for source, targets in refs.items():
        for target, line_num in targets:
            for dp in deprecated_patterns:
                if dp in target:
                    deprecated.append({
                        "source": source,
                        "line": line_num,
                        "target": target,
                        "deprecated_pattern": dp,
                    })

    # ── Detect circular references (DFS on directed graph) ──
    graph = collections.defaultdict(list)
    for source, targets in refs.items():
        # verify_workflow.py contains coverage constants and check fixtures that
        # cite product files. Those are validation edges, not runtime or
        # architecture dependencies, so they must not create source↔validator
        # circular-reference failures.
        if source in (entry_source, validator_source):
            continue
        for target, line_num in targets:
            target = normalize_ref_target(target)
            if should_ignore_ref(source, target, line_num):
                continue
            try:
                resolved = resolve_ref(source, target)
                rel_target = str(resolved.relative_to(ROOT)).replace("\\", "/")
            except (ValueError, OSError):
                continue
            if rel_target in (entry_source, validator_source):
                continue
            if rel_target in refs:  # only edges within scanned scope
                graph[source].append(rel_target)

    cycles = []
    seen_nodes = set()
    WHITE, GRAY, BLACK = 0, 1, 2

    def _dfs_cycle(node, colors, parent_map, stack):
        colors[node] = GRAY
        stack.append(node)
        for neighbor in graph.get(node, []):
            ncolors_key = neighbor
            if colors.get(ncolors_key, WHITE) == WHITE:
                parent_map[neighbor] = node
                _dfs_cycle(neighbor, colors, parent_map, stack)
            elif colors.get(ncolors_key, WHITE) == GRAY:
                # Found a cycle — extract the subsequence
                try:
                    idx = stack.index(neighbor)
                    cycle = stack[idx:] + [neighbor]
                    cycles.append(cycle)
                except ValueError:
                    pass
        colors[node] = BLACK
        stack.pop()

    colors_map = {}
    for node in list(graph):
        if colors_map.get(node, WHITE) == WHITE:
            _dfs_cycle(node, colors_map, {}, [])

    # Deduplicate cycles (same set of nodes in different rotations)
    unique_cycles = []
    seen_cycles = set()
    for cycle in cycles:
        if len(cycle) == 2 and cycle[0] == cycle[1]:
            continue
        key = tuple(sorted(cycle))
        if key not in seen_cycles:
            seen_cycles.add(key)
            unique_cycles.append(cycle)

    # ── FIX-432 (F-4 / F-A2): citation/note quote-sync guard ──
    quote_sync = _check_quote_sync_issues()

    # ── FEAT-088 (F-A3): exploration-channel evidence-form guard ──
    # Same carrier discipline as quote_sync: a related-but-distinct manifest
    # sub-face riding the manifest/cross-reference machine-check surface
    # instead of a new numbered check section (registry/frozen-snapshot zero
    # churn; fact source stays plugin-package like its host section).
    exploration_channels = check_exploration_channels()

    return {
        "dangling": dangling,
        "deprecated": deprecated,
        "cycles": unique_cycles,
        "quote_sync": quote_sync,
        "exploration_channels": exploration_channels,
        "total_files_scanned": len(md_files) + len(py_files),
        "total_refs": sum(len(t) for t in refs.values()),
    }


# ── SYSGAP-009: Sequential ID Checking ────────────────────────────

def check_sequential_ids():
    """Verify ID continuity in governance records:
    1. DEC-XXX: detect numbering gaps starting from 001
    2. EVD-XXX: detect numbering gaps
    3. RISK-XXX: detect numbering gaps
    4. Cross-reference integrity: task IDs referenced in evidence/decision/risk
       must exist in plan-tracker
    5. Completed tasks in plan-tracker must have evidence entries
    """

    def _extract_ids(file_path, prefix):
        """Extract sequential IDs with given prefix from a file, return sorted list of ints."""
        if not file_path.is_file():
            return []
        content = file_path.read_text(encoding="utf-8")
        ids = set()
        for m in re.finditer(rf"\b{re.escape(prefix)}(\d+)\b", content):
            ids.add(int(m.group(1)))
        return sorted(ids)

    def _find_gaps(sorted_ids, prefix):
        """Find gaps in a sorted list of integer IDs. Returns list of missing numbers."""
        if not sorted_ids:
            return []
        gaps = []
        expected = 1  # IDs start at 001
        for num in sorted_ids:
            while expected < num:
                gaps.append(expected)
                expected += 1
            expected = num + 1
        return gaps

    dec_path = GOVERNANCE_DIR / "decision-log.md"
    evd_path = GOVERNANCE_DIR / "evidence-log.md"
    risk_path = GOVERNANCE_DIR / "risk-log.md"

    # Use GovernanceDataSource for archive-aware ID collection.
    # Falls back to hot-file-only when archive/index.md does not exist.
    ds = _archive_reader()

    # DEC/RISK: via GovernanceDataSource (hot + archive)
    dec_ids = ds.get_all_decision_ids()
    risk_ids = ds.get_all_risk_ids()

    # EVD: collect from hot evidence-log + archive evidence files
    evd_id_set = set()
    if evd_path.is_file():
        evd_content = evd_path.read_text(encoding="utf-8")
        for m in re.finditer(r"\bEVD-(\d+)\b", evd_content):
            evd_id_set.add(int(m.group(1)))
    for entry in ds._scan_archive_files(ds.archive_evidence_dir,
                                         ds._extract_evidence_entries):
        evd_match = re.match(r"EVD-(\d+)", entry.get("evd_id", ""))
        if evd_match:
            evd_id_set.add(int(evd_match.group(1)))
    evd_ids = sorted(evd_id_set)

    dec_gaps = _find_gaps(dec_ids, "DEC-")
    evd_gaps = _find_gaps(evd_ids, "EVD-")
    risk_gaps = _find_gaps(risk_ids, "RISK-")

    # Cross-reference: all task IDs in evidence/decision/risk must exist
    # in plan-tracker.  Use GovernanceDataSource to include archived tasks.
    all_task_ids = ds.get_all_task_ids()

    # Collect task IDs referenced in evidence-log (hot + archive)
    evd_task_ids = ds.get_all_evidence_task_ids()

    # Collect task IDs referenced in decision-log
    dec_task_ids = set()
    if dec_path.is_file():
        dec_content = dec_path.read_text(encoding="utf-8")
        for m in re.finditer(r"\b([A-Z]+-\d+)\b", dec_content):
            task_id = m.group(1)
            if re.match(r"^[A-Z]+-\d+$", task_id) and not task_id.startswith("DEC-"):
                dec_task_ids.add(task_id)

    # Collect task IDs referenced in risk-log
    risk_task_ids = set()
    if risk_path.is_file():
        risk_content = risk_path.read_text(encoding="utf-8")
        for m in re.finditer(r"\b([A-Z]+-\d+)\b", risk_content):
            task_id = m.group(1)
            if re.match(r"^[A-Z]+-\d+$", task_id) and not task_id.startswith("RISK-"):
                risk_task_ids.add(task_id)

    orphan_evd = sorted(evd_task_ids - all_task_ids)
    orphan_dec = sorted(dec_task_ids - all_task_ids - evd_task_ids)  # avoid dup reporting
    orphan_risk = sorted(risk_task_ids - all_task_ids)

    # Completed tasks without evidence (archive-aware). Only hot missing
    # evidence is actionable; archived gaps are historical residue.
    completed_entries = ds.get_all_completed_task_entries()
    completed = {entry["id"] for entry in completed_entries}
    hot_completed = {
        entry["id"] for entry in completed_entries
        if entry.get("source") == "hot"
    }
    missing_evd_all = completed - evd_task_ids
    missing_evd = sorted(missing_evd_all & hot_completed)
    historical_missing_evd = sorted(missing_evd_all - set(missing_evd))

    return {
        "dec_ids": dec_ids,
        "evd_ids": evd_ids,
        "risk_ids": risk_ids,
        "dec_gaps": dec_gaps,
        "evd_gaps": evd_gaps,
        "risk_gaps": risk_gaps,
        "orphan_evidence_refs": orphan_evd,
        "orphan_decision_refs": orphan_dec,
        "orphan_risk_refs": orphan_risk,
        "completed_missing_evidence": missing_evd,
        "historical_completed_missing_evidence": historical_missing_evd,
    }


def _format_id_sequence_status(prefix, ids):
    """Return a compact, empty-safe ID range summary."""
    if not ids:
        return f"{prefix}-IDs: no entries found."
    return f"{prefix}-IDs: {ids[0]:03d}-{ids[-1]:03d} ({len(ids)} entries, no gaps)"


def _print_sequential_id_check(si_result):
    """Print Check 13 details and return the blocking issue count."""
    issue_count = 0
    if si_result["dec_gaps"]:
        issue_count += 1
        print(f"│  [WARN] DEC-ID gaps: missing {si_result['dec_gaps']}")
    else:
        print(f"│  [PASS] {_format_id_sequence_status('DEC', si_result['dec_ids'])}")

    if si_result["evd_gaps"]:
        print(f"│  [INFO] EVD-ID gaps: missing {si_result['evd_gaps']} "
              f"(historical archive residue)")
    else:
        print(f"│  [PASS] {_format_id_sequence_status('EVD', si_result['evd_ids'])}")

    if si_result["risk_gaps"]:
        issue_count += 1
        print(f"│  [WARN] RISK-ID gaps: missing {si_result['risk_gaps']}")
    else:
        print(f"│  [PASS] {_format_id_sequence_status('RISK', si_result['risk_ids'])}")

    # Orphan cross-references: info-only — these are historical cleanup residues
    # (old task IDs removed from plan-tracker during intentional cleanup, not errors)
    orphans = (si_result.get("orphan_evidence_refs", []) +
               si_result.get("orphan_decision_refs", []) +
               si_result.get("orphan_risk_refs", []))
    if orphans:
        print(f"│  [INFO] {len(orphans)} cross-reference(s) to non-existent task ID(s)"
              f" (historical cleanup residue): {orphans[:10]}")
        if len(orphans) > 10:
            print(f"│         ... and {len(orphans) - 10} more")
    else:
        print(f"│  [PASS] All cross-referenced task IDs exist in plan-tracker.")

    missing_evd = si_result.get("completed_missing_evidence", [])
    if missing_evd:
        issue_count += len(missing_evd)
        print(f"│  [WARN] {len(missing_evd)} completed task(s) without evidence: {missing_evd[:10]}")
    else:
        print(f"│  [PASS] All completed tasks have evidence entries.")

    historical_missing_evd = si_result.get("historical_completed_missing_evidence", [])
    if historical_missing_evd:
        print(f"│  [INFO] {len(historical_missing_evd)} archived completed task(s) "
              f"without evidence (historical residue): {historical_missing_evd[:10]}")
    if issue_count == 0:
        print(f"│  [PASS] All ID sequences are clean.")
    return issue_count


def _scan_unicode_line_separators():
    """FIX-349 ⑥: Unicode line/segment separators in governance hot files.

    EVD-890: a U+000B (VT) inside one evidence-log row silently became a line
    boundary for splitlines-style consumers (Python ``str.splitlines``,
    editors, markdown renderers) while the "\\n"-based governance checks saw
    one long line — the M5.4b false positive. EVD-1063 repaired that single
    occurrence without a systemic guard; this scan closes the class. It
    reports every occurrence of the FIX-349 ⑥ separator family (VT, FF,
    FS/GS/RS, NEL, LS, PS — all honored as line boundaries by splitlines-style
    consumers) in the hot files that line-based governance checks parse.

    Severity caliber (FIX-350 F-2): the WARN issues emitted here are
    non-blocking inside the ``check-governance`` aggregation
    (``structural_issue_is_blocking`` treats WARN as non-blocking), but the
    standalone ``check-structural-validity`` CLI exits 1 on ANY issue,
    WARN included — run it only when a fail-closed reading is intended.

    WARN severity (same caliber as ``evidence_col_mismatch``): the
    characters are a parsing hazard, not a broken schema, and the data fix
    belongs to the Coordinator's governance write-back, not to this check.
    """
    scan_files = (
        "plan-tracker.md", "evidence-log.md", "decision-log.md",
        "risk-log.md", "session-snapshot.md",
    )
    separators = (
        ("U+000B", "\x0b"),    # VT  — vertical tab (EVD-890 incident character)
        ("U+000C", "\x0c"),    # FF  — form feed (FIX-350 F-1: splitlines boundary)
        ("U+001C", "\x1c"),    # FS  — file separator
        ("U+001D", "\x1d"),    # GS  — group separator
        ("U+001E", "\x1e"),    # RS  — record separator
        ("U+0085", "\x85"),    # NEL — next line
        ("U+2028", "\u2028"),  # LS  — line separator
        ("U+2029", "\u2029"),  # PS  — paragraph separator
    )
    issues = []
    for name in scan_files:
        path = GOVERNANCE_DIR / name
        if not path.is_file():
            continue  # 存在才扫 — optional hot files (e.g. session-snapshot)
        content = path.read_text(encoding="utf-8")
        for label, char in separators:
            pos = content.find(char)
            while pos != -1:
                issues.append({
                    "type": "unicode_line_separator",
                    "severity": "WARN",
                    "file": f".governance/{name}",
                    "line": content.count("\n", 0, pos) + 1,
                    "col": pos - content.rfind("\n", 0, pos),
                    "detail": f"{label} line/segment separator in hot file "
                              f"(breaks splitlines-style parsing; "
                              f"EVD-890 class)",
                })
                pos = content.find(char, pos + 1)
    return issues


# ── SYSGAP-010: Structural Validity Checking ─────────────────────

def check_structural_validity():
    """Validate structural integrity of governance files:
    1. plan-tracker.md: table column count consistency (every row
       pipe-count matches header)
    2. evidence-log.md: every record has consistent column count
       (10 columns standard)
    3. decision-log.md: each ADR contains all required fields
    4. SKILL.md: frontmatter contains required fields (name/version/description)
    5. manifest.json: product / repo_only / exclude sections all present
    6. Unicode line/segment separators (FIX-349 ⑥) in the governance hot
       files — WARN-level disclosure via _scan_unicode_line_separators()
    """
    import json as _json
    issues = []

    # ── 1. plan-tracker.md table column consistency ──
    pt_path = GOVERNANCE_DIR / "plan-tracker.md"
    if pt_path.is_file():
        pt_content = pt_path.read_text(encoding="utf-8")
        # Find all markdown tables: contiguous |...| lines after a header row
        lines = pt_content.split("\n")
        current_header_cols = None
        current_header_line = 0
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line.startswith("|"):
                current_header_cols = None
                continue
            if "---" in line or ":--" in line:
                continue  # separator row
            # Strip inline code (backtick-quoted) to avoid false | in column count
            # e.g., | text `✅ 已完成 |` next | → the | inside backticks is NOT a column separator
            clean_line = re.sub(r'`+[^`]*`+', '__CODE__', line)
            cols = len(clean_line.split("|")) - 2  # strip outer empty parts
            if not cols:
                continue

            # Heuristic: if this looks like a header (next line is separator),
            # treat it as header
            is_header = False
            if i < len(lines):
                next_line = lines[i].strip()
                if re.match(r"^\|[\s\-:]+\|", next_line):
                    is_header = True

            if is_header:
                current_header_cols = cols
                current_header_line = i
                continue

            if current_header_cols is not None and cols != current_header_cols:
                issues.append({
                    "type": "table_column_mismatch",
                    "file": ".governance/plan-tracker.md",
                    "line": i,
                    "detail": f"Row has {cols} columns, header (line {current_header_line}) has {current_header_cols}",
                })
    else:
        issues.append({
            "type": "file_missing",
            "file": ".governance/plan-tracker.md",
            "detail": "plan-tracker.md not found",
        })

    # ── 2. evidence-log.md column count consistency ──
    evd_path = GOVERNANCE_DIR / "evidence-log.md"
    if evd_path.is_file():
        evd_content = evd_path.read_text(encoding="utf-8")
        evd_lines = evd_content.split("\n")
        standard_cols = None
        for i, line in enumerate(evd_lines, 1):
            line = line.strip()
            if not line.startswith("| EVD-"):
                continue
            parts = _split_markdown_table_row(line)
            cols = len(parts)
            if standard_cols is None:
                standard_cols = cols
            elif cols != standard_cols:
                evd_id = parts[0] if parts else "???"
                issues.append({
                    "type": "evidence_col_mismatch",
                    "severity": "WARN",
                    "file": ".governance/evidence-log.md",
                    "line": i,
                    "detail": f"{evd_id}: {cols} columns (expected {standard_cols})",
                })
    else:
        issues.append({
            "type": "file_missing",
            "file": ".governance/evidence-log.md",
            "detail": "evidence-log.md not found",
        })

    # ── 3. decision-log.md ADR required fields ──
    dec_path = GOVERNANCE_DIR / "decision-log.md"
    required_decision_fields = ["日期", "状态", "决策", "原因"]
    if dec_path.is_file():
        dec_content = dec_path.read_text(encoding="utf-8")
        # Parse ADR sections: each ADR starts with "## DEC-XXX"
        adr_sections = re.split(r"\n(?=## DEC-)", dec_content)
        for section in adr_sections:
            if not section.strip().startswith("## DEC-"):
                continue
            adr_id = section.split("\n")[0].replace("##", "").strip()
            missing = []
            for field in required_decision_fields:
                if field not in section:
                    missing.append(field)
            if missing:
                issues.append({
                    "type": "decision_missing_fields",
                    "file": ".governance/decision-log.md",
                    "detail": f"{adr_id}: missing required fields — {', '.join(missing)}",
                })
    else:
        issues.append({
            "type": "file_missing",
            "file": ".governance/decision-log.md",
            "detail": "decision-log.md not found",
        })

    # ── 4. SKILL.md frontmatter required fields ──
    skill_path = ROOT / "skills/software-project-governance/SKILL.md"
    if skill_path.is_file():
        content = skill_path.read_text(encoding="utf-8")
        # Extract frontmatter: content between first --- and second ---
        fm_match = re.match(r"^\s*---\s*\n(.*?)\n\s*---", content, re.DOTALL)
        if fm_match:
            fm_text = fm_match.group(1)
            required_frontmatter = ["name:", "description:"]
            missing = []
            for fm_field in required_frontmatter:
                if fm_field not in fm_text:
                    missing.append(fm_field.rstrip(":"))
            if not _extract_skill_version(skill_path):
                missing.append("version")
            if missing:
                issues.append({
                    "type": "skill_frontmatter_missing",
                    "file": "skills/software-project-governance/SKILL.md",
                    "detail": f"Frontmatter missing required fields: {', '.join(missing)}",
                })
        else:
            issues.append({
                "type": "skill_frontmatter_missing",
                "file": "skills/software-project-governance/SKILL.md",
                "detail": "No YAML frontmatter found (missing --- delimiters)",
            })

    # ── 5. manifest.json structure ──
    manifest_path = ROOT / "skills/software-project-governance/core/manifest.json"
    if manifest_path.is_file():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = _json.load(f)
            for section in ["product", "repo_only", "exclude_from_cleanup"]:
                if section not in manifest:
                    issues.append({
                        "type": "manifest_section_missing",
                        "file": "skills/software-project-governance/core/manifest.json",
                        "detail": f"manifest.json is missing '{section}' section",
                    })
        except (_json.JSONDecodeError, IOError) as e:
            issues.append({
                "type": "manifest_parse_error",
                "file": "skills/software-project-governance/core/manifest.json",
                "detail": str(e),
            })
    else:
        issues.append({
            "type": "file_missing",
            "file": "skills/software-project-governance/core/manifest.json",
            "detail": "manifest.json not found",
        })

    # ── 6. Unicode line/segment separators in hot files (FIX-349 ⑥) ──
    issues.extend(_scan_unicode_line_separators())

    return issues


# ── SYSGAP-012: Commit Scope Verification ────────────────────────

def check_commit_scope(limit=20):
    """Check recent commits for scope discipline violations:
    1. If commit message contains "顺带" / "also" / "顺便" keywords -> WARN
    2. Single commit touching > 15 files -> WARN (possible bulk commit)

    Multiple commits for the same task are normal for review/rework loops and
    are not a scope violation.
    """
    import subprocess

    try:
        # Get full commit log with stats
        result = subprocess.run(
            ["git", "-C", str(ROOT), "log", f"--format=%H%x00%s", f"-{limit}",
             "--no-merges"],
            capture_output=True, text=True, timeout=10, encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            return {"error": f"git log failed: {result.stderr}", "issues": []}
    except FileNotFoundError:
        return {"error": "git command not found", "issues": []}
    except Exception as e:
        return {"error": str(e), "issues": []}

    if not result.stdout:
        return {"error": "git log returned empty output", "issues": []}

    issues = []
    duo_commits = []        # commits with "also"/"顺带"/"顺便"

    lines = result.stdout.strip().split("\n")
    for line in lines:
        if not line or "\x00" not in line:
            continue
        sha, message = line.split("\x00", 1)
        sha_short = sha[:7]

        # Check 1: "顺带"/"also"/"顺便" keywords
        if re.search(r"顺带|顺便|also\b", message, re.IGNORECASE):
            duo_commits.append({"sha": sha_short, "message": message[:100]})

        # Check 2: files touched > 15 (use git show --stat)
        try:
            stat_result = subprocess.run(
                ["git", "-C", str(ROOT), "show", "--stat", "--format=", sha],
                capture_output=True, text=True, timeout=5, encoding="utf-8",
                errors="replace",
            )
            if stat_result.returncode == 0:
                # Count changed files from --stat output
                file_count = len([l for l in stat_result.stdout.split("\n")
                                 if l.strip() and "|" in l and not l.startswith(" ")])
                if file_count > 15:
                    issues.append({
                        "type": "bulk_commit",
                        "sha": sha_short,
                        "detail": f"{file_count} files changed in single commit",
                    })
        except (subprocess.TimeoutExpired, Exception):
            pass

    # Add duo keyword warnings
    for duo in duo_commits:
        issues.append({
            "type": "side_effect_warning",
            "sha": duo["sha"],
            "detail": f"Commit contains 'also/顺带/顺便': {duo['message']}",
        })

    return {
        "issues": issues,
        "total_checked": len(lines),
        "issue_count": len(issues),
    }


# ── SYSGAP-023: Goal Alignment Check ──────────────────────────────

PRODUCT_CODE_PATTERNS = [
    "skills/", "agents/", "infra/", "commands/",
    "adapters/", ".claude-plugin/", ".codex-plugin/", ".agents/",
    "project/",
]


# FIX-371/DEC-227 路线 b: a hot-tracker status cell leading with ✅ marks the
# terminal (完成) state — the row is historical bookkeeping retained in the
# hot table, not an active task. Only the ✅ prefix exempts; every other
# status (🔄 活跃 / 📋 待启 / plain text / chains not led by ✅) stays fully
# guarded — active/new rows have ZERO exemption (non-weakening red line).
_COMPLETED_STATUS_PREFIX = "✅"


def _plan_hot_tracker_task_statuses():
    """Return {task_id: status cell} from the current active hot-task table.

    FIX-371: single scan-source for the Check 16/17 entry collection —
    parse_impact_analysis_entries_with_exemptions consumes this statuses
    dict directly (same section boundaries: `## 当前活跃事项` until
    `### 最近完成`), so the exemption set is always a subset of the id set
    the entry collection consumes.

    Status-cell read (FIX-376 F-7 勘正): the compact layout ends with 状态 —
    those rows read the same cell parse_current_active_tasks reads (last
    cell, 同源). The legacy REQ-row layout carries 状态 second-to-last —
    there the ✅ word-prefix read overrides the last-cell read (F-3 分叉
    口径: a deliberate divergence from parse_current_active_tasks, which
    always reads the last cell and cannot see a legacy-row ✅ status).

    FIX-376 F-3 刻意分叉 (conservative; DEC-227 unchanged): the exemption
    predicate stays NARROWER than the FIX-292 authoritative terminal
    predicate ``_status_is_completed_cell`` — a mixed chain 「🔄 … → ✅ 完成」
    is W-7-terminal by that predicate but does not lead with ✅ → stays
    guarded (no exemption — conservative false-FAIL direction). FIX-390
    (DEC-241 消解, 0.89.0) evolves the exemption face to the three-state
    structured read :func:`_hot_status_completion_state` — the writer-era
    terminal (``committed`` + ops anchor, FIX-393 identity) joins the
    hand-era ✅ prefix — while EVERY other shape (mixed chains, triaged/dev
    cells with anchors, anchor-less hand-written 「committed」, unknown
    tokens) keeps the guarded verdict. The F-3 conservative direction is
    preserved for everything outside those two terminal eras.
    """
    if not SAMPLE_PATH.is_file():
        return {}
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    statuses = {}
    in_active_section = False
    for line in content.split("\n"):
        if line.startswith("## 当前活跃事项"):
            in_active_section = True
            continue
        if in_active_section and line.startswith("### 最近完成"):
            break
        if not in_active_section:
            continue
        stripped = line.strip()
        if not stripped.startswith("| ") or "---" in stripped:
            continue
        match = re.search(r"\|\s*(?:\*\*)?([A-Z]+-\d+)(?:\*\*)?\s*\|", stripped)
        if not match:
            continue
        cells = _governance_table_cells(stripped)
        # FIX-371: the hot table mixes shapes — the compact layout ends with
        # 状态 while the legacy REQ-row layout carries 状态 second-to-last.
        # FIX-376 F-3: the ✅ cell is scanned RIGHT-TO-LEFT — the status
        # column is a row-end anchor in both shapes, so the rightmost
        # ✅-led cell is the status-cell candidate. The old left-to-right
        # "first ✅ cell" read let an early ✅-led description/来源 cell
        # outrank the real status cell whenever both lead with ✅. Residual
        # theoretical vector outside this ticket's decided scope: an active
        # row whose real status does not lead with ✅ while an earlier cell
        # does — column-position pinning was R0's alternative and is not
        # adopted. Fallback stays the last cell when no ✅-led cell exists
        # (active rows).
        status = ""
        for cell in reversed(cells):
            if cell.startswith(_COMPLETED_STATUS_PREFIX):
                status = cell.strip()
                break
        if not status and cells:
            status = cells[-1].strip()
        statuses[match.group(1)] = status
    return statuses


# FIX-390 (DEC-241 消解, 0.89.0) — three-state structured completion read for
# the Check 16/17/18/18b exemption face. Display prefixes are no longer the
# only completion authority: the governed writer's own terminal state
# (``committed`` + ops receipt anchor, FIX-393 criterion consumed BY IDENTITY
# via :func:`_status_is_writer_committed_cell`) is the machine-era exact
# analog of the hand-era ✅ prefix (DEC-227 路线 b). States:
#   "committed" — writer-terminal + 〔op-<32hex>〕 anchor → completed/exempt;
#   "legacy"    — ✅-led hand-era terminal → completed/exempt (byte-for-byte
#                 the FIX-371/DEC-227 semantics — S_new ⊇ S_old invariant);
#   ""          — EVERYTHING else (mixed chains not led by ✅, triaged/dev
#                 cells with anchors, hand-written 「committed」 without the
#                 anchor, unknown tokens, empty) → 未知不猜: stays guarded
#                 (fail-closed; the row is judged on its fact merits instead).
_HOT_STATUS_STATE_COMMITTED = "committed"
_HOT_STATUS_STATE_LEGACY = "legacy"


def _hot_status_completion_state(status):
    """Classify a hot-tracker status cell into the FIX-390 three states.

    Returns :data:`_HOT_STATUS_STATE_COMMITTED`, :data:
    `_HOT_STATUS_STATE_LEGACY` or ``""`` (unknown — never guessed). The
    committed branch reuses the FIX-393 writer-terminal predicate by
    identity; a cell that merely displays 「committed」 without the ops
    anchor was not written by the governed writer (B-1 hand-edit class) and
    resolves to unknown.
    """
    text = _status_clean_cell(status)
    if not text:
        return ""
    if _status_is_writer_committed_cell(text):
        return _HOT_STATUS_STATE_COMMITTED
    if text.startswith(_COMPLETED_STATUS_PREFIX):
        return _HOT_STATUS_STATE_LEGACY
    return ""


def _current_release_task_ids():
    """Return task IDs from the active in-progress version roadmap row."""
    if not SAMPLE_PATH.is_file():
        return set()
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    task_ids = set()
    for line in content.split("\n"):
        if not line.strip().startswith("| "):
            continue
        if "进行中" not in line:
            continue
        for raw in re.findall(r"[A-Z]+-\d+(?:~\d+)?", line):
            task_ids |= expand_task_ids(raw)
    return task_ids


def _normalize_priority(value):
    normalized = value.strip().strip("*")
    return normalized if normalized in ("P0", "P1", "P2") else ""


def _task_priority_from_table_parts(parts):
    priority_first = _normalize_priority(parts[1]) if len(parts) > 1 else ""
    if priority_first:
        return priority_first
    old_table_priority = _normalize_priority(parts[11]) if len(parts) >= 12 else ""
    return old_table_priority


def _split_governance_table_row(line):
    from governance_readers import split_governance_table_row
    return split_governance_table_row(line)


# Standalone task-ID table cell (e.g. ``FIX-222`` / ``**REL-070**``). Single
# definition shared by parse_current_active_tasks and the FEAT-011
# governance-write-guard task-row scanner — no second shape source (FIX-292
# semantic dual-source lesson).
_TASK_ID_CELL_RE = re.compile(r"^(?:\*\*)?[A-Z]+-\d+(?:\*\*)?$")


def _governance_table_cells(line):
    from governance_readers import governance_table_cells
    return governance_table_cells(line)


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


def _is_incomplete_task_status(status):
    """Active-task test for plan/snapshot status cells (FIX-292, DEC-181).

    Delegates to the W-7/BC-7 authoritative terminal-chain predicate
    :func:`_status_is_completed_cell` (FIX-291) instead of maintaining a
    second naive marker vocabulary — the authoritative predicate is
    consumed as-is, never rewritten here. Effects (AUDIT-149 §3 域 1):

    - a mixed transition chain whose trailing state is terminal
      (「🔄 进行中 (…) → ✅ 完成 (…)」, live: FIX-253/254/255/266/
      REL-069) is COMPLETED — the old 「进行中」 substring hit hid the
      trailing terminal state (M2; the FIX-274 M2-shaped cell still
      verdicts ACTIVE via the inherited 「未完成」 narrative guard);
    - narrative English tokens (``p0_pending=0``, live: FIX-291) no
      longer hit a ``pending`` substring blacklist (M3);
    - conservative verdicts of the authoritative predicate are inherited
      (reopened trailing-active chains stay ACTIVE; bare 「终止」 is not
      in the W-7 terminal vocabulary → stays ACTIVE — fail-safe side);
    - empty/missing status stays incomplete (fail-closed: completion
      that cannot be proven = active, aligned with the execution-packet
      ``assumption_record``; ragged-row M1 shapes therefore keep their
      conservative ACTIVE verdict — the data-side write guard is
      FEAT-011's domain).
    """
    text = str(status or "").strip()
    if not text:
        return True
    return not _status_is_completed_cell(text)


# FIX-287③: subsection headings inside `## 当前活跃事项` that hold completed /
# archived content — collection suspends on them regardless of section order.
_NONACTIVE_SUBSECTION_MARKERS = ("最近完成", "已完成", "已归档", "依赖链")


def _is_nonactive_subsection(heading):
    """Return True for `### ` subsections that terminate active-task collection."""
    return any(marker in heading for marker in _NONACTIVE_SUBSECTION_MARKERS)


def parse_current_active_tasks():
    """Parse hot active task rows from plan-tracker compact tables.

    FIX-481 (D1 third round): two live header shapes inside 当前活跃事项.
    The compact 优先级-led table keeps the ID-anchored relative-offset
    reads below (unchanged behavior). The 0.54-era ID-first 20-column
    table (任务ID / ``ID`` leading, 状态 at a header-declared offset,
    trailing 备注) is parsed by HEADER SEMANTICS through the same public
    mapping dependency analysis uses — ``task_priority.parse_task_dependencies``
    is fed the table's own header + the single row, so task_id / priority
    / status / target_version come from the SAME header-semantic mapping
    FIX-480 established (P5 single semantic source; no second header-index
    implementation lives here). Host python_game Layer1 probe 2026-11-04:
    the old positional read took the trailing 备注 cell as the status and
    阶段 as the title, so 20 ✅-terminal history rows fed
    ``_active_execution_packet_tasks`` as fake active P0/P1 — host Check
    18c~18i ×20 = 120 fake FAILs (89% of the host's 135 quick issues),
    and ``discover_governance_context``'s active_tasks projection was
    equally polluted.

    Field trade-offs on the ID-first shape (honest not-applicable
    marking): title is read from the header-declared 事项 column when
    present (task_priority's column index deliberately ignores
    display-only columns — the lookup here is by exact header cell name,
    not a second semantic index); dependency carries the task-family IDs
    the header declares (empty on the stock 0.54 template — fail-closed,
    never a neighbouring-column guess); target_version likewise
    header-declared or empty; closure_path stays empty (the 0.54 template
    declares no 闭环路径 column; consumers fall back closure_path →
    title → task_id).
    """
    if not SAMPLE_PATH.is_file():
        return []
    # Deferred peer import (matches the module's TPA call style, e.g. the
    # dependency-analysis entry): the public FIX-480 mapping is the single
    # header-semantics source for ID-first rows.
    from task_priority import parse_task_dependencies  # noqa: WPS433
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    tasks = []
    in_active_section = False
    collecting = True
    # FIX-481: remember the header of the table currently being walked.
    # 优先级-led headers keep the compact positional parser; ID-first
    # headers (任务ID / ID leading — the lead labels task_priority's own
    # header detection accepts) switch data rows to header semantics.
    table_header_line = ""
    table_header_cells = []
    for line in content.split("\n"):
        if line.startswith("## 当前活跃事项"):
            in_active_section = True
            collecting = True
            continue
        if not in_active_section:
            continue
        if line.startswith("## "):
            # FIX-287③: the next top-level section always ends the active section.
            break
        if line.startswith("### "):
            # FIX-287③: order-tolerant subsection boundary — known completed/
            # archived subsections suspend collection; other subsections resume
            # it (host trackers may reorder, e.g. 最近完成 before active tables).
            collecting = not _is_nonactive_subsection(line)
            continue
        if not collecting:
            continue
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = _governance_table_cells(stripped)
        if not cells or cells[0] in {"优先级", "任务ID", "ID"}:
            # Header row: record the current table's shape, never emit
            # (the pre-FIX-481 skip set plus the plain-``ID`` lead FIX-480
            # recognizes).
            table_header_line = stripped
            table_header_cells = cells
            continue
        task_idx = next(
            (idx for idx, cell in enumerate(cells)
             if _TASK_ID_CELL_RE.match(cell.strip())),
            None,
        )
        if task_idx is None:
            continue
        acceptance = next((value for header, value in zip(table_header_cells, cells)
                           if header == "验收要求"), "")
        if table_header_cells and table_header_cells[0] in {"任务ID", "ID"}:
            # FIX-481 header-semantic path — single source: the row is
            # parsed by the same public mapping dependency analysis uses.
            # The micro-document (this table's header + this one row)
            # drives task_priority's own header detection and ID-first
            # dispatch, so the semantic columns land where the header
            # declares them — 状态 never the trailing 备注, 优先级 never
            # a prose scan hit. A row the shared parser cannot resolve
            # (no ID cell) is skipped — same conservative skip the
            # task_idx guard above applies to the compact path.
            dep_rows = parse_task_dependencies(
                table_header_line + "\n" + stripped)
            if not dep_rows:
                continue
            dep = dep_rows[0]
            title_idx = next(
                (idx for idx, cell in enumerate(table_header_cells)
                 if cell.strip() in {"事项", "任务项"}),
                None,
            )
            tasks.append({
                "task_id": dep.task_id,
                "priority": dep.priority,
                "title": (cells[title_idx].strip()
                          if title_idx is not None and title_idx < len(cells)
                          else ""),
                "dependency": ",".join(dep.dependencies),
                "target_version": dep.target_version,
                "closure_path": "",
                "status": dep.status,
                **({"acceptance": acceptance} if acceptance else {}),
                "raw_line": stripped,
            })
            continue
        task_id = cells[task_idx].strip().strip("*")
        priority = ""
        for cell in cells:
            normalized = _normalize_priority(cell)
            if normalized:
                priority = normalized
                break
        status = cells[-1].strip() if cells else ""
        title = cells[task_idx + 1].strip() if task_idx + 1 < len(cells) else ""
        dependency = cells[task_idx + 2].strip() if task_idx + 2 < len(cells) else ""
        target_version = cells[task_idx + 3].strip() if task_idx + 3 < len(cells) else ""
        closure_path = cells[task_idx + 4].strip() if task_idx + 4 < len(cells) else ""
        tasks.append({
            "task_id": task_id,
            "priority": priority,
            "title": title,
            "dependency": dependency,
            "target_version": target_version,
            "closure_path": closure_path,
            "status": status,
            **({"acceptance": acceptance} if acceptance else {}),
            "raw_line": stripped,
        })
    return tasks


def _active_execution_packet_tasks():
    """Plan rows available for an explicit bulk handoff."""
    return [
        task for task in parse_current_active_tasks()
        if task.get("priority") in {"P0", "P1"} and _is_incomplete_task_status(task.get("status", ""))
    ]


def _declared_packet_checks(result, packet_path, contract=None):
    """Select actual handoffs. Native local work has its own acceptance receipt."""
    from governance_readers import loop_state
    path = packet_path or SAMPLE_PATH.parent / "execution-packets.json"
    try:
        packets, _ = _read_execution_packet_document(path, missing_ok=True)
        if not packets:
            return []
        tasks = {task["task_id"]: task for task in parse_current_active_tasks()
                 if _is_incomplete_task_status(task.get("status", ""))}
        view = loop_state(SAMPLE_PATH.parent.parent)
        if view["state"] == "invalid":
            raise ValueError(view["message"])
        for unit in view["units"]:
            if unit["runtime_status"] != "completed":
                for key in (unit["flow_unit_id"], unit["task_id"]):
                    tasks.setdefault(key, {"task_id": key, "status": unit["runtime_status"]})
        selected = []
        for key, task in tasks.items():
            if key not in packets:
                continue
            packet = packets[key]
            if contract and contract != "acceptance_contract" and isinstance(packet, dict):
                required = packet.get("required_contracts", [])
                if isinstance(required, list) and contract not in required and contract not in packet:
                    continue
            result["required_tasks"].append(key)
            selected.append((task, packet))
        return selected
    except (ValueError, OSError) as exc:
        result["pass"] = False
        result["issues"].append(str(exc))
        return []


def parse_impact_analysis_entries():
    """Parse evidence-log entries that must carry goal/user impact guardrails.

    This includes explicit type=影响分析 rows and hot plan product-code delivery
    evidence rows. FIX-073: product-code evidence with no standalone impact
    analysis must not make Check 16/17 silently pass with 0 entries.

    FIX-371/DEC-227 路线 b: EVD rows whose task row is terminal-complete in
    the hot tracker (historical hand-written-era ✅ rows; writer-committed
    rows since FIX-390) are exempt from the entry set.
    Backward-compatible wrapper — returns only the non-exempt entries; use
    parse_impact_analysis_entries_with_exemptions() for the disclosure ledger.

    Returns list of dicts: {evd_id, task_id, description, file_location, raw_line}
    """
    entries, _ = parse_impact_analysis_entries_with_exemptions()
    return entries


def parse_impact_analysis_entries_with_exemptions():
    """parse_impact_analysis_entries + historical-exemption ledger (FIX-371).

    DEC-227 路线 b: an EVD row whose task row is terminal-complete in the hot
    tracker (historical hand-written-era data) is exempt from the Check 16/17
    entry set; every exemption is disclosed in the returned ledger — never
    silent. Rows whose task is active/new or whose terminal status is
    unprovable keep zero exemption (fail-closed).

    FIX-390 (DEC-241 消解): terminal-complete is the three-state structured
    read :func:`_hot_status_completion_state` — writer-committed terminal
    cells (ops anchor, FIX-393 identity) join the legacy ✅ prefix; unknown
    tokens are never guessed. The ✅ face of the ledger is unchanged
    (S_new ⊇ S_old); the expansion is exactly the writer-committed rows and
    stays fully disclosed.

    Returns (entries, historical_exempted); historical_exempted is a list of
    {evd_id, task_id, status} dicts.
    """
    if not EVIDENCE_PATH.is_file():
        return [], []
    content = EVIDENCE_PATH.read_text(encoding="utf-8")
    entries = []
    historical_exempted = []
    hot_task_statuses = _plan_hot_tracker_task_statuses()
    completed_hot_task_ids = {
        task_id
        for task_id, status in hot_task_statuses.items()
        if _hot_status_completion_state(status)
    }
    hot_task_ids = _current_release_task_ids() | set(hot_task_statuses)

    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in _split_governance_table_row(line)]
        if len(parts) < 8:
            continue
        evd_id = parts[1]
        task_id = parts[2]
        # FIX-368: LIVE evidence-log column layout is
        # parts[3]=type, parts[4]=description, parts[5]=fact basis,
        # parts[6]=file location (10 data cells -> 12 split parts incl. the
        # leading/trailing empties). The pre-fix parts[4]/parts[5] read was a
        # +1 offset that matched 目标对齐/用户影响 against the fact-basis
        # column — the EVD-1118 false-FAIL root cause in Check 16/17.
        evd_type = parts[3] if len(parts) > 3 else ""
        description = parts[4] if len(parts) > 4 else ""
        file_location = parts[6] if len(parts) > 6 else ""

        covered_ids = expand_task_ids(task_id) if task_id and re.search(r"[A-Z]+-\d+", task_id) else set()
        if requires_impact_evidence(task_id, evd_type, file_location, active=bool(covered_ids & hot_task_ids)):
            hot_covered = covered_ids & hot_task_ids
            target_ids = sorted(hot_covered) if hot_covered else [task_id]
            if not target_ids:
                target_ids = [task_id]
            for covered_task_id in target_ids:
                # FIX-371/DEC-227 路线 b: ✅-terminal hot-tracker task -> exempt
                # with ledger disclosure; anything unproven stays guarded.
                if covered_task_id in completed_hot_task_ids:
                    historical_exempted.append({
                        "evd_id": evd_id,
                        "task_id": covered_task_id,
                        "status": hot_task_statuses.get(covered_task_id, ""),
                    })
                    continue
                entries.append({
                    "evd_id": evd_id,
                    "task_id": covered_task_id,
                    "description": description,
                    # FIX-390: the DEC-168 machine row-family contract lands
                    # the fact basis in the independent basis column
                    # (parts[5], governance_store._build_evidence_row
                    # --basis channel). Surfaced so the Check 18/18b strict
                    # judgment reads the structured column instead of only
                    # the description narrative.
                    "fact_basis": parts[5] if len(parts) > 5 else "",
                    "file_location": file_location,
                    "raw_line": line,
                })
    return entries, historical_exempted


def check_goal_alignment():
    """SYSGAP-023: Check that all impact analysis entries have goal alignment.

    Checks:
    1. plan-tracker has 项目目标 field (WARN if missing)
    2. Each 影响分析 entry has 目标对齐: field with >= 30 chars (FAIL if missing/short)
    3. Identical goal alignment text across different EVD rows
       (WARN — template reuse; FIX-349 ③: entries fanned out of ONE EVD row
       share a single description by construction and are never compared)

    Returns dict with 'has_project_goal', 'entries', 'duplicates', 'pass' and
    'historical_exempted' (FIX-371 ledger: terminal-complete hot-tracker rows
    exempted from the entry set — ✅ prefix, and writer-committed cells since
    FIX-390; disclosed, never silent).
    """
    result = {
        "has_project_goal": False,
        "project_goal": "",
        "entries": [],
        "duplicates": [],
        "historical_exempted": [],
        "pass": True,
    }

    # 1. Check project goal in plan-tracker
    config = parse_project_config()
    project_goal = config.get("项目目标", "")
    result["project_goal"] = project_goal
    if project_goal:
        result["has_project_goal"] = True

    # 2. Parse impact analysis entries (FIX-371/DEC-227 路线 b: historical
    # ✅-terminal rows exempted with an explicit ledger)
    entries, historical_exempted = parse_impact_analysis_entries_with_exemptions()
    result["historical_exempted"] = historical_exempted
    if not entries:
        return result

    goal_map = {}  # goal_text -> [(evd_id, task_id)]

    for entry in entries:
        desc = entry["description"]
        # Extract 目标对齐: field — captures text until next known field or end
        goal_match = re.search(
            r'目标对齐[:：]\s*(.+?)(?:\s*(?:用户影响[:：]|范围[:：]|依赖[:：]|架构影响[:：]|$))',
            desc
        )
        goal_text = goal_match.group(1).strip() if goal_match else ""
        goal_len = len(goal_text)

        has_goal = bool(goal_text)
        status = "PASS"
        if not has_goal:
            status = "FAIL"
            result["pass"] = False
        elif goal_len < 30:
            status = "FAIL"
            result["pass"] = False
        else:
            # Track for duplicate detection
            if goal_text in goal_map:
                goal_map[goal_text].append((entry["evd_id"], entry["task_id"]))
            else:
                goal_map[goal_text] = [(entry["evd_id"], entry["task_id"])]

        result["entries"].append({
            "task_id": entry["task_id"],
            "evd_id": entry["evd_id"],
            "has_goal": has_goal,
            "goal_text": goal_text[:80] + ("..." if goal_len > 80 else ""),
            "goal_len": goal_len,
            "status": status,
        })

    # 3. Check duplicates
    # FIX-349 ③: compare only entries from DIFFERENT evd_id rows. One EVD row
    # fanning out to several tasks (expand_task_ids in
    # parse_impact_analysis_entries) shares a single description by
    # construction, so identical goal text inside one row is structural, not
    # template reuse (live false positive: EVD-507 -> REQ-094<->REQ-095).
    # Cross-EVD comparison — the real template-reuse signal — is unchanged.
    for goal_text, evd_tasks in goal_map.items():
        if len(evd_tasks) >= 2:
            for i in range(len(evd_tasks)):
                for j in range(i + 1, len(evd_tasks)):
                    if evd_tasks[i][0] != evd_tasks[j][0]:
                        result["duplicates"].append(
                            (evd_tasks[i][1], evd_tasks[j][1]))

    return result


# ── SYSGAP-024: User Impact Check ────────────────────────────────

def check_user_impact():
    """SYSGAP-024: Check that all impact analysis entries have user impact analysis.

    Checks:
    1. Each 影响分析 entry has 用户影响: field (FAIL if missing)
    2. Required sub-fields parsed: 获得= / 感知= / 体验变化= / 迁移指南=
    3. Value validity for 获得= (WARN if unrecognized)
    4. Contradiction: 体验变化=否 but diff involves user-visible files (WARN)
    5. Breaking change: 体验变化=是 but 迁移指南=不需要 (BLOCKING)
    6. Breaking change: migration guide path does not exist (BLOCKING — if path provided)

    Returns dict with 'entries', 'blocking', 'pass' and 'historical_exempted'
    (FIX-371 ledger: terminal-complete hot-tracker rows exempted from the
    entry set — ✅ prefix, and writer-committed cells since FIX-390;
    disclosed, never silent).
    """
    USER_VISIBLE_PATTERNS = [
        "CLAUDE.md", "README.md", "CHANGELOG.md",
        "plugin.json", "marketplace.json",
        "commands/", ".claude-plugin/", ".codex-plugin/",
    ]

    # FIX-406 F-2 predicate unification: the closed vocabulary is defined
    # ONCE in the writer domain (governance_store.VALID_OBTAIN_VALUES —
    # the intake mirror and this engine check consume the same constant;
    # the pre-fix local copy is retired so the two faces can never drift).
    from governance_store import VALID_OBTAIN_VALUES

    result = {
        "entries": [],
        "blocking": [],
        "historical_exempted": [],
        "pass": True,
    }

    # FIX-371/DEC-227 路线 b: historical ✅-terminal rows exempted with an
    # explicit ledger — disclosed, never silent.
    entries, historical_exempted = parse_impact_analysis_entries_with_exemptions()
    result["historical_exempted"] = historical_exempted
    if not entries:
        return result

    # FIX-410 read-side latest-wins: per task, ONLY the latest
    # field-carrying (用户影响:) row is judged — a compliant correction
    # row supersedes older malformed rows of the same task (live RCA:
    # EVD-1252 kept Check 17 FAILing forever although a compliant
    # correction row was in place; the write side already prevents NEW
    # bad rows — the intake mirror — but the read side refused to
    # recognize corrections). Superseded rows stay in the log as
    # append-only history and are disclosed via a counter, never silent.
    # A task with NO field-carrying row keeps the original per-entry
    # logic (missing-field FAIL stands — fail-closed).
    _field_re = re.compile(r'用户影响[:：]\s*(.+?)')
    _latest_field_index = {}
    for _index, _entry in enumerate(entries):
        if _field_re.search(_entry["description"]):
            _latest_field_index[_entry["task_id"]] = _index
    _judged_entries = []
    _superseded = 0
    for _index, _entry in enumerate(entries):
        _latest = _latest_field_index.get(_entry["task_id"])
        # P1-1 (FIX-410 R0 review): supersede applies ONLY to field-carrying
        # rows — a LATER fieldless row keeps its original per-row judgment
        # (missing field -> FAIL); the earlier combination seam let such a
        # row be superseded away, swallowing the rule-1 missing-field FAIL.
        if (_latest is None or _index == _latest
                or not _field_re.search(_entry["description"])):
            _judged_entries.append(_entry)
        else:
            _superseded += 1
    result["latest_wins_superseded"] = _superseded
    entries = _judged_entries

    for entry in entries:
        desc = entry["description"]
        file_location = entry["file_location"]

        # Extract 用户影响: field — captures text until next known field or end
        user_impact_match = re.search(
            r'用户影响[:：]\s*(.+?)(?:\s*(?:目标对齐[:：]|范围[:：]|依赖[:：]|架构影响[:：]|$))',
            desc
        )
        user_impact_text = user_impact_match.group(1).strip() if user_impact_match else ""

        has_field = bool(user_impact_text)

        # Parse sub-fields
        obtain_match = re.search(r'获得=([^,]*?)(?:,|，|\s*(?:感知=|体验变化=|迁移指南=|$))', user_impact_text)
        obtain = obtain_match.group(1).strip() if obtain_match else ""

        perceive_match = re.search(r'感知=([^,]*?)(?:,|，|\s*(?:获得=|体验变化=|迁移指南=|$))', user_impact_text)
        perceive = perceive_match.group(1).strip() if perceive_match else ""

        exp_change_match = re.search(r'体验变化=([^,]*?)(?:,|，|\s*(?:获得=|感知=|迁移指南=|$))', user_impact_text)
        exp_change = exp_change_match.group(1).strip() if exp_change_match else ""

        migration_match = re.search(r'迁移指南=([^,]*?)(?:,|，|\s*(?:获得=|感知=|体验变化=|$))', user_impact_text)
        migration = migration_match.group(1).strip() if migration_match else ""

        status = "PASS"
        issues = []

        if not has_field:
            status = "FAIL"
            issues.append("缺少 用户影响: 字段")
            result["pass"] = False
        else:
            # Check sub-fields presence
            missing_subs = []
            if not obtain:
                missing_subs.append("获得=")
            if not perceive:
                missing_subs.append("感知=")
            if not exp_change:
                missing_subs.append("体验变化=")
            if not migration:
                missing_subs.append("迁移指南=")
            if missing_subs:
                issues.append(f"缺少子字段: {', '.join(missing_subs)}")
                status = "FAIL"
                result["pass"] = False

            # Value validity for 获得=
            if obtain:
                # Check if obtain value matches any valid value (lenient — contains check)
                found_valid = any(v in obtain for v in VALID_OBTAIN_VALUES)
                if not found_valid:
                    issues.append(
                        f"获得= 值 '{obtain}' 不在合法范围内"
                        f" ({', '.join(VALID_OBTAIN_VALUES[:4])} 等)"
                    )
                    if status == "PASS":
                        status = "WARN"

            # Contradiction: 体验变化=否 but file_location contains user-visible patterns
            if exp_change == "否":
                for pattern in USER_VISIBLE_PATTERNS:
                    if pattern in file_location:
                        issues.append(
                            f"体验变化=否 但证据位置涉及用户可见文件 '{pattern}'"
                        )
                        if status == "PASS":
                            status = "WARN"
                        break

            # Breaking change: 体验变化=是 + 迁移指南=不需要
            if exp_change == "是" and migration == "不需要":
                status = "BLOCKING"
                issues.append("体验变化=是（Breaking Change）但 迁移指南=不需要")

            # Breaking change: migration guide path validity
            if exp_change == "是" and migration and migration not in ("不需要", ""):
                # migration could be a relative file path from repo root
                migration_path = ROOT / migration.lstrip("/")
                if not migration_path.is_file():
                    status = "BLOCKING"
                    issues.append(
                        f"体验变化=是（Breaking Change）但迁移指南路径不存在: {migration}"
                    )

        entry_result = {
            "task_id": entry["task_id"],
            "evd_id": entry["evd_id"],
            "has_field": has_field,
            "obtain": obtain,
            "perceive": perceive,
            "exp_change": exp_change,
            "migration": migration,
            "status": status,
            "issues": issues,
        }
        result["entries"].append(entry_result)

        if status in ("FAIL", "BLOCKING"):
            result["pass"] = False
        if status == "BLOCKING":
            result["blocking"].append(entry["task_id"])

    return result


# ── FIX-080: Fact Grounding Check ────────────────────────────────

FACT_BASIS_RE = re.compile(
    r'事实依据[:：]\s*(.+?)(?:\s*(?:目标对齐[:：]|用户影响[:：]|范围[:：]|依赖[:：]|架构影响[:：]|$))'
)

UNGROUNDED_CLAIM_RE = re.compile(
    r"(?:我\s*)?(?:假设|猜测|推测|估计)|(?:大概|应该|可能)(?:已经|是|可以|完成|存在)|编造|幻觉"
)

def _current_release_impact_entries():
    """Return impact/product-delivery entries for the active in-progress release.

    FIX-080 avoids retroactively failing historical evidence that predates the
    fact-grounding field. The commit hook enforces every new product-code commit;
    check-governance enforces the active version row so future work cannot omit it.
    """
    release_task_ids = _current_release_task_ids()
    if not release_task_ids:
        return []
    return [entry for entry in parse_impact_analysis_entries()
            if entry["task_id"] in release_task_ids]


# ── FIX-083: Structured Evidence Check ────────────────────────────

# ── FIX-084: AI Execution Packet Check ───────────────────────────

EXECUTION_PACKET_REQUIRED_FIELDS = {
    "task_id": str,
    "goal": str,
    "allowed_change_scope": list,
    "required_evidence": list,
    "next_commands": list,
    "done_definition": list,
}


def _read_execution_packet_document(path, *, missing_ok=False):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if missing_ok:
            return {}, {}
        raise
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("execution packet root must be object")
    if "version" in data and (type(data["version"]) is not int or data["version"] != 1):
        raise ValueError(f"unsupported execution packet version: {data['version']!r}")
    packets = data.get("packets", data)
    if not isinstance(packets, dict):
        raise ValueError("packets must be object")
    from execution_packet import has_native_unit_identity

    for key, packet in packets.items():
        if not governance_store._TASK_ID_RE.fullmatch(key) and not has_native_unit_identity(key, packet):
            raise ValueError("execution packet map must be keyed by its task or native work unit")
    metadata = {k: v for k, v in data.items() if k != "packets"} if "packets" in data else {}
    return packets, metadata


def _load_execution_packets(path=None):
    packet_path = path or EXECUTION_PACKET_PATH
    try:
        packets, _ = _read_execution_packet_document(packet_path)
        return packets, ""
    except FileNotFoundError:
        return {}, f"{packet_path} not found"
    except (OSError, ValueError) as exc:
        return {}, str(exc)


def _execution_packet_field_issues(packet):
    """Structural field issues for one packet (shared validator — single
    definition of the EXECUTION_PACKET_REQUIRED_FIELDS semantics).

    Consumed by Check 18c (:func:`_validate_execution_packet`) and by the
    FEAT-011 governance-write-guard structural face — no second field
    semantics (FIX-292 dual-source lesson). Pure: no I/O.
    """
    issues = []
    if not isinstance(packet, dict):
        return ["packet must be object"]
    for field, expected_type in EXECUTION_PACKET_REQUIRED_FIELDS.items():
        value = packet.get(field)
        if not isinstance(value, expected_type):
            issues.append(f"{field} missing or invalid")
            continue
        if expected_type is str and not value.strip():
            issues.append(f"{field} must be non-empty")
        if expected_type is list and (
            not value or not all(isinstance(item, str) and item.strip() for item in value)
        ):
            issues.append(f"{field} must be non-empty string array")
    from execution_packet import OPTIONAL_CONTRACTS
    required = packet.get("required_contracts", [])
    if not isinstance(required, list) or not all(isinstance(name, str) and name in OPTIONAL_CONTRACTS for name in required):
        issues.append("required_contracts must list supported handoff contracts")
    else:
        issues.extend(f"missing required {name}" for name in required if name not in packet)
    # FEAT-092: optional advisory budget field — absent is legal (缺省不写),
    # present must be exactly {max_steps: positive int} (fail-closed on
    # illegal shapes so Check 18c / write-guard surface them).
    budget = packet.get("budget")
    if budget is not None:
        if (not isinstance(budget, dict)
                or set(budget) != {"max_steps"}
                or isinstance(budget.get("max_steps"), bool)
                or not isinstance(budget.get("max_steps"), int)
                or budget["max_steps"] <= 0):
            issues.append(
                "budget must be {max_steps: positive integer} (FEAT-092)")
    return issues


# FIX-319: `allowed_change_scope` is assembled from plan-tracker row text (see
# `build_execution_packet`), which carries markdown emphasis — `**NOT_RUN**`,
# `**契约层**`. Bold uses a PAIRED `**` delimiter, so the old substring
# predicate `"*" in scope.lower()` reported EVERY bold-bearing scope as
# `too broad` (systematic false positive: FIX-315 / FIX-317 / FEAT-031).
#
# Only `**` needs neutralising: the predicate inspects `*` and the whole-repo
# phrases, and `` ` `` / `_` carry no asterisk semantics (stripping them would
# change no verdict). A single `*` is deliberately NOT stripped — in a scope
# string it is far more often a glob (`src/*`, `*.py`, `*foo*`) than italic
# emphasis, so leaving it in place keeps the judgement on the strict side.
# The same decision covers italic emphasis: `*foo*` is NOT neutralised and is
# still reported `too broad` (FIX-319 boundary, restated by FIX-321).
#
# FIX-321 (review FIX-319 F-01): the pairing alone was not enough — a `**` run
# must also be a TRUE run boundary, otherwise `**/tests/**` falls inside one
# span, becomes ` /tests/ ` and PASSes, while its sibling `**/*.py` still FAILs
# (the `/` blocked the span) — an inconsistency, and exactly the laundering the
# predicate's contract forbids. So a `**` run counts as a bold delimiter only
# when it is a MAXIMAL run of exactly two stars that touches neither another
# `*` nor a path separator `/` on EITHER side — the glob tokens are `**/`,
# `/**` and `/**/`. A rejected span is left verbatim, its `*` survives, and the
# scope stays FAIL: an ambiguous boundary always resolves to the strict side.
_MARKDOWN_BOLD_SPAN_RE = re.compile(
    r"(?<![\*/])\*\*(?![\*/])(?P<inner>[^*]+?)(?<![\*/])\*\*(?![\*/])"
)

# Whole-repo phrases, anchored at a WORD START (and case-insensitive) so that
# natural language merely containing the sequence — `install files`,
# `as many files as` — is not misread as an unbounded scope. The start anchor
# alone is enough: the trailing part is left open so the old substring
# coverage of plurals (`any files`, `whole repository`) is preserved.
_TOO_BROAD_SCOPE_PHRASE_RE = re.compile(r"\b(?:any file|all files|whole repo)", re.IGNORECASE)


def _strip_markdown_bold_markers(text):
    """Neutralise PAIRED markdown bold markers, keeping the inner text.

    `**X**` becomes ` X ` — the inner text survives so a genuinely broad bold
    phrase (`**all files**`) is still caught. A single pass is sufficient: the
    inner group excludes `*` and the replacement only inserts the inner text
    plus spaces, so no new `**` pair can appear for a second pass to find.

    FIX-321: only spans whose two `**` runs are TRUE run boundaries are
    neutralised — a maximal two-star run that touches neither `*` nor `/` on
    either side (see `_MARKDOWN_BOLD_SPAN_RE`). Everything else is left
    verbatim, so a glob such as `**/tests/**` or `**/*.py` keeps its `*` and
    stays `too broad`. The slash may live inside the span (`**a/b**` is bold);
    only a slash glued to a delimiter disqualifies it. Ambiguity therefore
    fails closed instead of laundering a wildcard.

    Deliberate boundary (FIX-319, restated by FIX-321): single-`*` emphasis
    (`*foo*`) is NOT stripped either, because in a scope string a lone `*` is
    far more often a glob than italic emphasis — it is reported `too broad`.
    """
    return _MARKDOWN_BOLD_SPAN_RE.sub(lambda match: f" {match.group('inner')} ", text)


def _is_too_broad_scope_text(text):
    """True when an `allowed_change_scope` blob declares an unbounded scope.

    FIX-319: markdown bold is stripped first. A *surviving* `*` is a genuine
    wildcard — standalone (`*`), attached (`src/*`, `*.py`) or glob
    (`**/*.py`, `**/tests/**`, `/**`) — and stays `too broad`; stripping must
    never launder it. FIX-321 makes that guarantee mechanical rather than
    incidental: `_strip_markdown_bold_markers` refuses any span whose `**`
    runs are not true run boundaries, so a recursive-directory glob can no
    longer land inside one.
    """
    stripped = _strip_markdown_bold_markers(text)
    if "*" in stripped:
        return True
    return bool(_TOO_BROAD_SCOPE_PHRASE_RE.search(stripped))


def _validate_execution_packet(task, packet):
    issues = _execution_packet_field_issues(packet)
    if not isinstance(packet, dict):
        return issues  # HEAD-identical early exit: ["packet must be object"]
    if packet.get("task_id") and packet.get("task_id") != task["task_id"]:
        issues.append("task_id does not match active task")
    if any(not isinstance(packet.get(field), list) or not all(isinstance(value, str) for value in packet[field])
           for field in ("allowed_change_scope", "required_evidence", "done_definition")):
        return issues
    allowed_text = " ".join(packet["allowed_change_scope"])
    if allowed_text and _is_too_broad_scope_text(allowed_text):
        issues.append("allowed_change_scope is too broad")
    for field in ("goal", "allowed_change_scope", "required_evidence", "next_commands", "done_definition"):
        values = packet.get(field, [])
        if isinstance(values, str):
            values = [values]
        if isinstance(values, list) and any(isinstance(value, str) and PRODUCT_SUCCESS_PLACEHOLDER_RE.search(value)
                                            for value in values):
            issues.append(f"{field} contains a placeholder")
    return issues


DETERMINISTIC_SCAFFOLD_DIR = ROOT / "skills/software-project-governance/core/templates/deterministic-scaffolds"


PRODUCT_SUCCESS_CONTRACT_REQUIRED_FIELDS = {
    "user": str,
    "job_to_be_done": str,
    "non_goals": list,
    "success_metrics": list,
    "competitive_baseline": str,
    "done_definition": list,
}

PRODUCT_SUCCESS_PLACEHOLDER_RE = re.compile(
    r"(?:\b(?:todo|tbd|to_be_defined|n/?a|none|null|unknown)\b|待补|待定|暂无|占位)",
    re.IGNORECASE,
)

PRODUCT_SUCCESS_PROCESS_ONLY_RE = re.compile(
    r"(?:check-governance|verify_workflow|evidence-log|plan-tracker|review|commit|push|archive|"
    r"治理|证据|归档|提交|审查|记录|hook|\bgate\s*(?:G?\d+\s*)?(?:已?通过|pass(?:ed)?\b))",
    re.IGNORECASE,
)

PRODUCT_SUCCESS_USER_OUTCOME_RE = re.compile(
    r"(?:user|customer|persona|outcome|value|usable|acceptance|scenario|quality|competitive|"
    r"用户|客户|使用者|产品|体验|价值|可用|可见|验收|场景|质量|竞争)",
    re.IGNORECASE,
)

PRODUCT_SUCCESS_RUNNABLE_RE = re.compile(
    r"(?:e2e|test|unit|integration|fixture|ci|command|script|execute|run|pass|"
    r"测试|验证|用例|命令|脚本|执行|通过)",
    re.IGNORECASE,
)

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
        required_fields=PRODUCT_SUCCESS_CONTRACT_REQUIRED_FIELDS,
        placeholder=PRODUCT_SUCCESS_PLACEHOLDER_RE,
        process_only_metric=_is_process_only_product_success_metric,
        user_outcome=PRODUCT_SUCCESS_USER_OUTCOME_RE,
        runnable=PRODUCT_SUCCESS_RUNNABLE_RE,
    )


def _acceptance_policy():
    from delivery_contract_checks import AcceptancePolicy
    return AcceptancePolicy(
        required_fields=ACCEPTANCE_CONTRACT_REQUIRED_FIELDS,
        runnable_command=ACCEPTANCE_RUNNABLE_COMMAND_RE,
        pass_statuses=ACCEPTANCE_PASS_STATUSES,
        not_run_statuses=ACCEPTANCE_NOT_RUN_STATUSES,
        placeholder=PRODUCT_SUCCESS_PLACEHOLDER_RE,
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
        placeholder=PRODUCT_SUCCESS_PLACEHOLDER_RE,
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
        placeholder=PRODUCT_SUCCESS_PLACEHOLDER_RE,
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
    return judge(value, PRODUCT_SUCCESS_PROCESS_ONLY_RE)


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
    from execution_packet import generate_packet_document
    existing = existing or {}
    if any(not isinstance(packet, dict) for packet in existing.values()):
        raise ValueError("each execution packet must be object")
    from functools import partial
    tasks = _active_execution_packet_tasks()
    if task_ids:
        known = {task["task_id"] for task in tasks}
        tasks.extend(task for task in parse_current_active_tasks() if task["task_id"] in task_ids - known
                     and _is_incomplete_task_status(task.get("status", "")))
    return generate_packet_document(tasks, task_ids=task_ids, existing=existing,
                                    governance_dir=governance_dir or SAMPLE_PATH.parent,
                                    build_packet=partial(build_execution_packet, contracts=contracts,
                                                         quality_dimensions=quality_dimensions))



def check_execution_packets(packet_path=None):
    result = {
        "required_tasks": [],
        "entries": [],
        "missing": [],
        "issues": [],
        "pass": True,
    }
    for task, packet in _declared_packet_checks(result, packet_path, None):
        task_id = task["task_id"]
        issues = _validate_execution_packet(task, packet)
        status = "PASS" if not issues else "FAIL"
        if issues:
            result["pass"] = False
        result["entries"].append({"task_id": task_id, "status": status, "issues": issues})
    return result


def cmd_execution_packet(args):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from contextlib import nullcontext

    budget = getattr(args, "budget", None)
    if budget is not None and (type(budget) is not int or budget <= 0):
        print(f"[ERROR] --budget must be a positive integer (got {budget!r})")
        sys.exit(2)

    wanted = set(args.task) if args.task else None
    note = ""
    try:
        path = EXECUTION_PACKET_PATH.resolve()
        with governance_store._TargetLock(path) if args.write else nullcontext():
            packets, metadata = _read_execution_packet_document(path, missing_ok=True)
            contracts = set(getattr(args, "contract", None) or [])
            dimensions = list(dict.fromkeys(getattr(args, "quality_dimension", None) or []))
            if dimensions:
                contracts.add("quality_budget")
            selection = wanted if wanted is not None else set(packets)
            payload = generate_execution_packets(existing=packets, task_ids=selection, governance_dir=path.parent,
                                                 contracts=contracts, quality_dimensions=dimensions)
            generated = payload["packets"]
            if budget is not None:
                for packet in generated.values():
                    packet["budget"] = {"max_steps": budget}
            if not args.write:
                message = json.dumps(payload, ensure_ascii=False, indent=2)
            elif not generated:
                message = "[OK] no active execution packets matched the selected tasks"
            else:
                payload["packets"] = {**packets, **generated}
                if wanted is not None:
                    preserved = len(payload["packets"]) - len(generated)
                    note = (f" (incremental merge: regenerated {', '.join(sorted(generated))};"
                            f" preserved {preserved} other {'entry' if preserved == 1 else 'entries'})")
                document = {**metadata, **payload}
                data = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
                governance_store._atomic_write_bytes(path, data)
                message = f"[OK] wrote {len(payload['packets'])} execution packet(s) to {EXECUTION_PACKET_PATH}{note}"
    except (OSError, ValueError, governance_store.StoreError) as exc:
        print(f"[ERROR] {EXECUTION_PACKET_PATH}: {exc}", file=sys.stderr)
        sys.exit(1)
    print(message)


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
    _resolve_shared()
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
    """Check if a file or directory exists."""
    path = ROOT / relative_path
    if path.exists():
        return "PASS", f"{label}: {relative_path} exists"
    return "FAIL", f"{label}: {relative_path} NOT FOUND"


def _check_snippet_in_file(relative_path, snippet, label):
    """Check if a snippet exists in a file."""
    path = ROOT / relative_path
    if not path.is_file():
        return "FAIL", f"{label}: file {relative_path} NOT FOUND"
    content = path.read_text(encoding="utf-8")
    if snippet in content:
        return "PASS", f"{label}: '{snippet[:50]}...' found in {relative_path}"
    return "FAIL", f"{label}: '{snippet[:50]}...' NOT found in {relative_path}"


def _check_all_required_files_exist():
    """Silently check if all required files exist (for auto-judgment)."""
    required = build_required_files_from_manifest()
    if required is None:
        required = REQUIRED_FILES
    missing = [label for label, path in required.items() if not path.is_file()]
    if not missing:
        return "PASS", "所有必需文件存在 — 仓库结构符合约定"
    return "FAIL", f"缺失 {len(missing)} 个必需文件: {', '.join(missing[:3])}..."


def _check_governance_file_exists(filename):
    """Check if a governance file exists and has content."""
    path = GOVERNANCE_DIR / filename
    if path.is_file() and path.stat().st_size > 0:
        return "PASS", f".governance/{filename} 存在且非空"
    return "FAIL", f".governance/{filename} 不存在或为空"


def _check_quantifiable_metrics():
    """Check if project has quantifiable success metrics in plan-tracker."""
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    # Look for numeric targets in plan-tracker overview or config
    metrics_patterns = [
        r"≥\s*\d+",           # ≥ N
        r"\d+%",              # N%
        r"≤\s*\d+",           # ≤ N
        r"coverage.*\d+",      # coverage mention with number
        r"PASSED.*\d+",        # PASSED with count
    ]
    for pattern in metrics_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return "PASS", "项目目标含量化指标（检测到数字阈值或百分比）"
    return "NEEDS_HUMAN", "无法自动检测量化指标——需人工确认项目目标是否可衡量"


def _check_scope_boundary():
    """Check if scope boundaries are defined."""
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    if "范围" in content or "scope" in content.lower():
        return "PASS", "plan-tracker 中包含范围相关描述"
    return "NEEDS_HUMAN", "需人工确认范围边界是否清晰"


def _check_stakeholders():
    """Check if stakeholders are identified."""
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    # Check for role descriptions in plan-tracker tasks or config
    if "项目负责人" in content or "Owner" in content:
        return "PASS", "检测到干系人角色（项目负责人/Owner）"
    return "NEEDS_HUMAN", "需人工确认干系人列表"


def _check_out_of_scope():
    """Check if out-of-scope items are explicitly listed."""
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    if "范围外" in content or "不做什么" in content or "out of scope" in content.lower():
        return "PASS", "检测到范围外/不做什么声明"
    return "NEEDS_HUMAN", "需人工确认范围外事项是否明确"


def _check_completed_ratio(min_ratio=0.5):
    """Check if plan-tracker completed ratio meets threshold."""
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    # Match the overview table: after "总任务数" header line, the data row has:
    # | name | stage | total | completed | blocked | risks | gate | date |
    lines = content.split("\n")
    in_overview = False
    for i, line in enumerate(lines):
        if "总任务数" in line and "已完成" in line:
            in_overview = True
            continue
        if in_overview and line.strip().startswith("|") and not "---" in line:
            # Data row: extract columns
            parts = [p.strip() for p in line.split("|")]
            # parts[0]=empty, [1]=name, [2]=stage, [3]=total, [4]=completed, ...
            if len(parts) >= 5:
                try:
                    total = int(parts[3])
                    completed = int(parts[4])
                    ratio = completed / total if total > 0 else 0
                    if ratio >= min_ratio:
                        return "PASS", f"任务完成率 {ratio:.0%} ≥ {min_ratio:.0%}（{completed}/{total}）"
                    return "FAIL", f"任务完成率 {ratio:.0%} < {min_ratio:.0%}（{completed}/{total}）"
                except ValueError:
                    continue
            break
    return "NEEDS_HUMAN", "无法从 plan-tracker 解析完成率"


def _check_evidence_mentions(keyword, label):
    """Check if evidence-log contains a keyword."""
    content = EVIDENCE_PATH.read_text(encoding="utf-8")
    if keyword in content:
        return "PASS", f"{label}: evidence-log 含'{keyword[:30]}'相关证据"
    return "NEEDS_HUMAN", f"{label}: evidence-log 未找到'{keyword[:30]}'——需人工确认"


def _read_archive_aware_governance_text(include=()):
    """Read hot governance files plus selected archive directories."""
    ds = _archive_reader()
    chunks = []
    hot_paths = []
    if "plan" in include:
        hot_paths.append(ds.sample_path)
    if "evidence" in include:
        hot_paths.append(ds.evidence_path)
    if "decision" in include:
        hot_paths.append(ds.decision_path)
    if "risk" in include:
        hot_paths.append(ds.risk_path)

    for path in hot_paths:
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8"))

    archive_dirs = []
    if "plan" in include:
        archive_dirs.append(ds.archive_tasks_dir)
    if "evidence" in include:
        archive_dirs.append(ds.archive_evidence_dir)
    if "decision" in include:
        archive_dirs.append(ds.archive_decisions_dir)
    if "risk" in include:
        archive_dirs.append(ds.archive_risks_dir)

    if ds._has_archive():
        for archive_dir in archive_dirs:
            if not archive_dir.exists():
                continue
            for path in sorted(archive_dir.glob("*.md")):
                if path.name != ".gitkeep":
                    chunks.append(path.read_text(encoding="utf-8"))

    return "\n".join(chunks)


def _contains_all(text, keywords):
    return all(keyword in text for keyword in keywords)


def _contains_any(text, keywords):
    return any(keyword in text for keyword in keywords)


def _has_line_with_all(text, keyword_groups):
    """Return True when one line contains at least one keyword from each group."""
    for line in text.splitlines():
        if all(_contains_any(line, group) for group in keyword_groups):
            return True
    return False


def _iter_archive_aware_evidence_units():
    """Yield hot/archive evidence rows; fallback to whole non-table archive docs."""
    ds = _archive_reader()
    if ds.evidence_path.is_file():
        for line in ds.evidence_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("| EVD-"):
                yield line

    if not ds._has_archive() or not ds.archive_evidence_dir.exists():
        return

    for path in sorted(ds.archive_evidence_dir.glob("*.md")):
        if path.name == ".gitkeep":
            continue
        content = path.read_text(encoding="utf-8")
        rows = [
            line for line in content.splitlines()
            if line.strip().startswith("| EVD-")
        ]
        if rows:
            for row in rows:
                yield row
        else:
            yield content


def _line_has_issue_severity(line):
    """Detect explicit issue severity values, not schema/header field names."""
    severity_patterns = [
        r"严重级别\s*[:：=|]\s*(P0|P1|P2|高风险|中风险|低风险|高严重|中严重|低严重|critical|high|medium|low)\b",
        r"\bseverity\s*[:：=|]\s*(P0|P1|P2|critical|high|medium|low)\b",
        r"\b(P0|P1|P2|critical|high|medium|low)\b",
        r"(高风险|中风险|低风险|高严重|中严重|低严重)",
    ]
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in severity_patterns)


def _line_has_issue_status_value(line):
    """Detect explicit issue status values, not only a status field name."""
    status_patterns = [
        r"状态\s*[:：=|]\s*(打开|已关闭|进行中|待处理|处理中|已解决|closed|open|done|resolved|in progress)\b",
        r"\bstatus\s*[:：=|]\s*(closed|open|done|resolved|in progress)\b",
    ]
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in status_patterns)


def _line_has_real_issue_item(line):
    """Detect an actual issue item/task entry rather than a schema-only line."""
    if _contains_any(line.lower(), ("schema", "header")):
        return False
    if _contains_any(line, ("字段", "表头", "模板", "格式")):
        return False
    item_patterns = [
        r"(问题项|问题条目|问题实例|issue item)",
        r"\b(ISSUE|BUG|TASK|FIX|AUDIT)-\d+\b",
        r"问题\s*\d+",
        r"问题\s*[:：]\s*\S+",
        r"任务\s*[:：]\s*\S+",
    ]
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in item_patterns)


def _plan_row_is_inactive(parts):
    """Return True when a plan table row is completed/terminated/cancelled."""
    joined = " ".join(parts).lower()
    inactive_markers = (
        "已完成", "✅", "已终止", "终止", "取消", "已取消",
        "closed", "done", "completed", "terminated", "cancelled", "canceled",
    )
    return any(marker in joined for marker in inactive_markers)


def _check_g10_real_operation_data():
    """G10: require explicit real operation data for at least one week."""
    text = _read_archive_aware_governance_text(include=("evidence",))
    if _has_line_with_all(text, (
        ("真实运营数据", "真实运行数据", "运行数据", "运营数据"),
        ("至少 1 周", "至少1周", "一周", "7天", "7 天", "1 week", "one week"),
    )):
        return "PASS", "检测到至少 1 周真实运营/运行数据证据（含归档 evidence）"
    return "NEEDS_HUMAN", "未检测到明确的至少 1 周真实运营数据证据"


def _check_g10_feedback_archived_classified():
    """G10: feedback must be archived and classified."""
    text = _read_archive_aware_governance_text(include=("evidence", "plan"))
    if _has_line_with_all(text, (
        ("用户反馈", "反馈汇总", "反馈归档"),
        ("已归档", "归档", "archive"),
        ("分类", "类别", "类型"),
    )):
        return "PASS", "检测到已归档且已分类的用户反馈证据（含归档 evidence）"
    return "NEEDS_HUMAN", "未检测到反馈归档+分类的完整证据"


def _check_g10_issue_list_severity_status():
    """G10: issue list must include severity and status, not just priority."""
    text = _read_archive_aware_governance_text(include=("evidence", "plan", "risk"))
    for line in text.splitlines():
        has_issue_list = _contains_any(line, ("问题清单", "issue list", "问题列表"))
        if (
            has_issue_list
            and _line_has_real_issue_item(line)
            and _line_has_issue_severity(line)
            and _line_has_issue_status_value(line)
        ):
            return "PASS", "检测到包含严重级别和状态的问题清单"
    return "NEEDS_HUMAN", "未检测到真实问题项及其严重级别值和状态值"


def _check_g10_executable_optimization_items():
    """G10: optimization direction must be executable, not only a slogan."""
    text = _read_archive_aware_governance_text(include=("evidence", "plan"))
    if _has_line_with_all(text, (
        ("优化项", "改进项", "优化方向", "改进方向", "可执行优化项"),
        ("Owner", "DRI", "截止", "验收", "验证", "命令", "文件", "任务"),
    )):
        return "PASS", "检测到带执行标记的优化/改进项"
    return "NEEDS_HUMAN", "未检测到可执行优化项（需 Owner/截止/验收/验证等执行标记）"


def _check_g11_retro_complete():
    """G11: retro must include the four required sections."""
    required = ("目标回顾", "结果评估", "原因分析", "经验沉淀")
    evidence_units = list(_iter_archive_aware_evidence_units())
    for unit in evidence_units:
        if _contains_all(unit, required):
            return "PASS", "复盘证据包含目标回顾/结果评估/原因分析/经验沉淀（含归档 evidence）"
    text = "\n".join(evidence_units)
    if not text:
        text = _read_archive_aware_governance_text(include=("evidence",))
    missing = [keyword for keyword in required if keyword not in text]
    if not missing:
        return "NEEDS_HUMAN", "复盘四要素分散在多条证据中，未检测到同一条复盘证据包含全部四要素"
    return "NEEDS_HUMAN", f"复盘证据缺少: {', '.join(missing)}"


def _check_g11_rules_templates_backfilled():
    """G11: rules/templates backfill needs evidence, commit, or file-change proof."""
    text = _read_archive_aware_governance_text(include=("evidence",))
    if _has_line_with_all(text, (
        ("回灌", "规则修订", "模板更新", "经验回灌"),
        ("规则", "模板", "protocol", "template", "SKILL.md", "stage-gates.md"),
        ("commit", "提交", "文件变更", "修改", "更新", ".md", ".py"),
    )):
        return "PASS", "检测到规则/模板回灌及提交或文件变更证据"
    return "NEEDS_HUMAN", "未检测到规则/模板回灌的提交或文件变更证据"


def _check_g11_next_round_direction():
    """G11: next-round direction must be explicit or an active P0, not any historical P0."""
    content = SAMPLE_PATH.read_text(encoding="utf-8") if SAMPLE_PATH.is_file() else ""
    active_section = content
    marker = "## 当前活跃事项"
    if marker in content:
        active_section = content.split(marker, 1)[1].split("\n## ", 1)[0]

    for line in active_section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        parts = _split_markdown_table_row(line)
        normalized = [part.replace("*", "").strip() for part in parts]
        has_active_p0 = any(part == "P0" for part in normalized)
        if has_active_p0 and not _plan_row_is_inactive(normalized):
            return "PASS", "当前活跃事项中存在未完成的 P0 任务，下一轮方向明确"

    next_round_terms = ("下一轮", "下轮")
    for line in active_section.splitlines():
        if (
            _contains_any(line, next_round_terms)
            and re.search(r"[A-Z]+-\d+", line)
            and not _plan_row_is_inactive([line])
        ):
            return "PASS", "当前活跃事项显式描述下一轮方向并关联任务"

    return "FAIL", "未检测到计划中的下一轮方向或活跃 P0 任务"


def _check_risk_has_closed(label="关键缺陷"):
    """Check if risk-log has any closed/critical risk entries."""
    content = RISK_PATH.read_text(encoding="utf-8")
    closed_count = sum(1 for line in content.split("\n") if "已关闭" in line or "已缓解" in line)
    if closed_count > 0:
        return "PASS", f"{label}: {closed_count} 条风险已关闭/已缓解"
    return "NEEDS_HUMAN", f"{label}: 无已关闭风险——需人工确认是否所有关键缺陷已处理"


def _check_plan_has_priority(priority="P0"):
    """Check if plan-tracker has tasks at a given priority."""
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    count = len(re.findall(rf"\|\s*{priority}\s*\|", content))
    if count > 0:
        return "PASS", f"plan-tracker 含 {count} 条 {priority} 任务"
    return "FAIL", f"plan-tracker 无 {priority} 任务——下轮方向不明确"


def _check_version_consistency_heuristic():
    """Lightweight version consistency check for G11 auto-judgment (SYSGAP-020 enhanced).

    Checks: SKILL.md frontmatter version must appear consistently in all
    version declaration files (8 positions), CHANGELOG latest entry,
    and verify_workflow.py hardcoded snippets.
    """
    try:
        skill_version = _extract_skill_version(ROOT / "skills/software-project-governance/SKILL.md")
        if not skill_version:
            return "NEEDS_HUMAN", "无法从 SKILL.md 提取版本号"

        # Version declaration files
        version_files = [
            "skills/software-project-governance/core/manifest.json",
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            ".codex-plugin/plugin.json",
            "skills/software-project-governance/infra/verify_workflow.py",
        ]
        for vf in version_files:
            vf_path = ROOT / vf
            if vf_path.exists():
                vf_content = vf_path.read_text(encoding="utf-8")
                if skill_version not in vf_content:
                    return "FAIL", f"{vf} 版本与 SKILL.md ({skill_version}) 不一致"

        # CHANGELOG latest entry
        changelog_path = ROOT / "project/CHANGELOG.md"
        if changelog_path.exists():
            changelog_content = changelog_path.read_text(encoding="utf-8")
            cl_match = re.search(r'##\s*\[([\d.]+)\]', changelog_content)
            if cl_match and cl_match.group(1) != skill_version:
                return "FAIL", f"CHANGELOG.md 最新版本 [{cl_match.group(1)}] 与 SKILL.md ({skill_version}) 不一致"

        return "PASS", f"版本 {skill_version} 在 {len(version_files)} 个声明文件中一致"
    except Exception as e:
        return "NEEDS_HUMAN", f"版本检查异常: {e}"


def _gate_check_result_from_definition(check_definition):
    executor = check_definition.get("executor")
    if executor == "function":
        function_map = {
            "check_quantifiable_metrics": "_check_quantifiable_metrics",
            "check_scope_boundary": "_check_scope_boundary",
            "check_stakeholders": "_check_stakeholders",
            "check_out_of_scope": "_check_out_of_scope",
            "check_all_required_files_exist": "_check_all_required_files_exist",
            "check_g10_real_operation_data": "_check_g10_real_operation_data",
            "check_g10_feedback_archived_classified": "_check_g10_feedback_archived_classified",
            "check_g10_issue_list_severity_status": "_check_g10_issue_list_severity_status",
            "check_g10_executable_optimization_items": "_check_g10_executable_optimization_items",
            "check_g11_retro_complete": "_check_g11_retro_complete",
            "check_g11_rules_templates_backfilled": "_check_g11_rules_templates_backfilled",
            "check_g11_next_round_direction": "_check_g11_next_round_direction",
            "check_risk_has_closed": "_check_risk_has_closed",
            "check_version_consistency_heuristic": "_check_version_consistency_heuristic",
        }
        fn = globals().get(function_map.get(check_definition.get("function"), ""))
        if not callable(fn):
            return "FAIL", f"未知检查函数 `{check_definition.get('function')}`"
        return fn()
    if executor == "file_exists":
        return _check_file_exists(check_definition.get("path", ""), check_definition["label"])
    if executor == "snippet_in_file":
        return _check_snippet_in_file(
            check_definition.get("path", ""),
            check_definition.get("snippet", ""),
            check_definition["label"],
        )
    if executor == "completed_ratio":
        return _check_completed_ratio(check_definition.get("min_ratio", 0.5))
    if executor == "research_doc_count":
        path = ROOT / check_definition.get("path", "project/workflows/software-project-governance/research")
        min_count = check_definition.get("min_count", 0)
        if path.exists() and len(list(path.glob("*.md"))) >= min_count:
            return "PASS", check_definition.get("message", "research docs count satisfied")
        return "FAIL", check_definition.get("failure_message", f"{path} 文档数量不足")
    if executor == "constant_result":
        return check_definition.get("result", "NEEDS_HUMAN"), check_definition.get("message", "")
    if executor == "evidence_mentions":
        return _check_evidence_mentions(check_definition.get("keyword", ""), check_definition["label"])
    return "FAIL", f"未知 executor `{executor}`"


def auto_judge_gate(gate_id, unit_id=None):
    """Auto-judge a specific Gate based on available evidence.

    Returns: dict with overall_result (passed/blocked/passed-with-conditions/needs_human)
             and per-item results list.

    ``unit_id`` (optional, FIX-236.2 Wiring B): when a flow-unit id is given
    and the gate rendered a verdict (not needs_human), the judgment is routed
    to :func:`loop_gate_processor.process_gate_result` as a thin best-effort
    call (actor="gate-engine"). The wiring result is attached under the
    ``wiring`` key only when ``unit_id`` is provided, so existing callers see
    an unchanged dict shape.
    """
    gate_id = gate_id.upper()
    if not gate_id.startswith("G"):
        gate_id = "G" + gate_id

    detail = parse_gate_detail(gate_id)
    if not detail:
        return {"error": f"Gate {gate_id} not found", "items": []}

    registry, registry_issues = _load_lifecycle_registry()
    if registry_issues or not isinstance(registry, dict):
        return {"error": f"Lifecycle registry unavailable for {gate_id}", "items": []}
    registry_display = _display_path(LIFECYCLE_REGISTRY_PATH, ROOT)
    registry_contract_issues = _gate_execution_registry_contract_issues(registry, registry_display)
    if registry_contract_issues:
        detail_text = "; ".join(registry_contract_issues[:3])
        if len(registry_contract_issues) > 3:
            detail_text += f"; ... ({len(registry_contract_issues)} total issues)"
        return {
            "gate": gate_id,
            "title": detail["title"],
            "overall": "blocked",
            "items": [{
                "check": "Gate execution registry contract",
                "result": "FAIL",
                "detail": detail_text,
            }],
            "summary": f"registry validation failed: {len(registry_contract_issues)} issue(s)",
        }

    gate_registry = registry.get("gate_execution_registry", {})
    gate_checks = gate_registry.get("gate_checks", []) if isinstance(gate_registry, dict) else []
    gate_entry = next(
        (item for item in gate_checks if isinstance(item, dict) and item.get("gate_id") == gate_id),
        None,
    )
    if not gate_entry:
        return {"error": f"Gate {gate_id} not found in execution registry", "items": []}

    # ── Execute auto-judgment ──
    items = []
    pass_count = 0
    fail_count = 0
    human_count = 0

    for check_definition in gate_entry.get("checks", []):
        try:
            result, message = _gate_check_result_from_definition(check_definition)
        except Exception as e:
            result, message = "FAIL", f"判定异常: {e}"

        items.append({
            "check": check_definition.get("label", check_definition.get("check_id", "<missing>")),
            "result": result,
            "detail": message,
        })
        if result == "PASS":
            pass_count += 1
        elif result == "FAIL":
            fail_count += 1
        else:
            human_count += 1

    # ── Overall result ──
    total = len(items)
    if total == 0:
        overall = "needs_human"
    elif fail_count > 0:
        overall = "blocked"
    elif human_count > 0:
        overall = "passed-with-conditions"
    else:
        overall = "passed"

    # Diagnostics report local checks. Scoped review is applied by the native writer.
    result = {
        "gate": gate_id,
        "title": detail["title"],
        "overall": overall,
        "items": items,
        "summary": f"PASS={pass_count} FAIL={fail_count} NEEDS_HUMAN={human_count}",
    }
    return result


def cmd_gate_check(args):
    """Evaluate only an identified unit's current gate using its scoped receipt."""
    from loop_workflow import gate_review
    if not getattr(args, "unit", None) or not getattr(args, "review", None):
        print("gate-check requires --unit and --review from this unit and iteration", file=sys.stderr)
        sys.exit(2)
    try:
        outcome = gate_review(HOST_PROJECT_ROOT, args.unit, args.gate_id.upper(), args.review)
    except (ValueError, OSError) as exc:
        print(f"gate-check: {exc}", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    if outcome.get("decision") in ("escalate", "iterate") and getattr(args, "fail_on_blocked", False):
        sys.exit(1)

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
            if "/" not in f and f in PLATFORM_ENTRY_FILES:
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

ARCHGUARD_SCHEMA_REL = "skills/software-project-governance/core/architecture-health.json"
ARCHGUARD_LEDGER_REL = "skills/software-project-governance/core/technical-debt-ledger.md"
ARCHGUARD_HOOKS_REL = "skills/software-project-governance/infra/hooks"
ARCHGUARD_DEFAULT_ROOT_RESIDUE = ("_fix_*", "_tmp_*", "debug_*", "scratch_*")


def _archguard_load_schema(root=None):
    """Load architecture-health.json; return (schema_dict, error_str_or_None)."""
    root = Path(root) if root is not None else ROOT
    schema_path = root / ARCHGUARD_SCHEMA_REL
    if not schema_path.is_file():
        return None, f"missing schema: {_display_path(schema_path, root)}"
    try:
        return json.loads(schema_path.read_text(encoding="utf-8")), None
    except (ValueError, OSError) as exc:
        return None, f"invalid schema {schema_path}: {exc}"


from checks.architecture_health import (
    _archguard_excluded, _archguard_exclusion_match, _archguard_iter_code_files, _archguard_severity,
)


def check_architecture_health(root=None, schema=None):
    """Check the plugin (or a supplied fixture root) with its original policy."""
    from checks.architecture_health import scan_architecture

    root = Path(root) if root is not None else ROOT
    if schema is None:
        schema, err = _archguard_load_schema(root)
        if schema is None:
            return {"error": err, "findings": [], "summary": {"errors": 0, "warnings": 0}}
    return scan_architecture(root, schema)


def _archguard_normalized_lines(text, normalize_le=True, ignore_ws=True):
    """Normalize text to a list of content lines (the CRLF/whitespace-safe comparator)."""
    if normalize_le:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    out = []
    for ln in text.split("\n"):
        if ignore_ws:
            compact = re.sub(r"\s+", "", ln)
            if not compact:
                continue
            out.append(compact)
        else:
            if not ln.strip():
                continue
            out.append(ln)
    return out


def _archguard_source_projection_pairs(root):
    """Return [(source_rel, source_abs, projection_abs), ...] for source/projection dup check.

    Derives pairs from the e2e-test-project projection tree: for each infra/*.py under
    the source skills tree, look for the mirrored file under the projection copy.
    """
    root = Path(root)
    src_base = root / "skills/software-project-governance/infra"
    proj_base = root / "project/e2e-test-project/skills/software-project-governance/infra"
    pairs = []
    if not src_base.is_dir() or not proj_base.is_dir():
        return pairs
    for py in sorted(src_base.glob("*.py")):
        candidate = proj_base / py.name
        if candidate.is_file():
            pairs.append((py.relative_to(root), py, candidate))
    return pairs


def check_duplicate_code(root=None, schema=None):
    """REQ-101 ArchGuard check 2: source/projection semantic duplicate.

    MUST normalize line endings + ignore whitespace, otherwise CRLF(source) vs
    LF(projection) yields a false ~100% diff.
    """
    root = Path(root) if root is not None else ROOT
    if schema is None:
        schema, err = _archguard_load_schema(root)
        if schema is None:
            return {"error": err, "findings": [], "pairs_checked": 0,
                    "summary": {"errors": 0, "warnings": 0}}
    dc = schema.get("duplicate_code", {})
    warn_pct = dc.get("warn_pct", 60)
    error_pct = dc.get("error_pct", 80)
    normalize_le = bool(dc.get("normalize_line_endings", True))
    ignore_ws = bool(dc.get("ignore_whitespace", True))
    # FIX-350: schema-driven pair exemptions ([{path, reason}] on the SOURCE
    # rel path, same caliber as module_size.exclusions). An exempt pair still
    # counts toward pairs_checked and is disclosed — never silently dropped.
    dc_exclusions = dc.get("exclusions", [])

    findings = []
    exemptions = []
    pairs = _archguard_source_projection_pairs(root)
    for rel, src_abs, proj_abs in pairs:
        match = _archguard_exclusion_match(rel, dc_exclusions)
        if match is not None:
            reason = match.get("reason", "") if isinstance(match, dict) else ""
            # posix form for the disclosure — same caliber as the schema glob.
            exemptions.append({"path": str(rel).replace("\\", "/"),
                               "reason": reason})
            continue
        try:
            src_text = src_abs.read_text(encoding="utf-8", errors="replace")
            proj_text = proj_abs.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        src_lines = set(_archguard_normalized_lines(src_text, normalize_le, ignore_ws))
        proj_lines = set(_archguard_normalized_lines(proj_text, normalize_le, ignore_ws))
        denom = max(len(src_lines), len(proj_lines)) or 1
        diff_count = len(src_lines.symmetric_difference(proj_lines))
        duplicate_pct = round((1 - diff_count / denom) * 100, 1)
        sev = None
        if duplicate_pct >= error_pct:
            sev = "ERROR"
        elif duplicate_pct >= warn_pct:
            sev = "WARN"
        if sev:
            findings.append({
                "check": "duplicate_code", "severity": sev, "path": str(rel),
                "source_lines": len(src_lines), "projection_lines": len(proj_lines),
                "duplicate_pct": duplicate_pct,
            })
    errors = sum(1 for f in findings if f["severity"] == "ERROR")
    warnings = sum(1 for f in findings if f["severity"] == "WARN")
    return {
        "findings": findings, "pairs_checked": len(pairs),
        "exemptions": exemptions,
        "summary": {"errors": errors, "warnings": warnings},
    }


def check_technical_debt(root=None, schema=None):
    """REQ-101 ArchGuard check 3: root residue / release docs / hooks drift / ledger cross-validate.

    G9: hooks-drift MUST reuse ``_external_validation_read_text`` and
    ``_external_validation_canonical_hook_text`` — do not reimplement.
    """
    root = Path(root) if root is not None else ROOT
    if schema is None:
        schema, err = _archguard_load_schema(root)
        if schema is None:
            return {"error": err, "findings": [],
                    "summary": {"errors": 0, "warnings": 0,
                                "open_items": 0, "deferred_items": 0}}
    td = schema.get("technical_debt", {})
    findings = []

    # 1. root-directory residue scripts
    patterns = td.get("root_residue_patterns") or list(ARCHGUARD_DEFAULT_ROOT_RESIDUE)
    for entry in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        for pat in patterns:
            if fnmatch.fnmatch(entry, pat):
                findings.append({
                    "check": "root_residue", "severity": "WARN",
                    "path": entry, "pattern": pat,
                })
                break

    # 2. historical release docs version count
    threshold = td.get("release_docs_archive_threshold_versions", 30)
    release_dir = root / "docs/release"
    versions = set()
    if release_dir.is_dir():
        for child in release_dir.iterdir():
            # collect version-like tokens from filenames (e.g. 0.57.0)
            m = re.search(r"(\d+\.\d+\.\d+)", child.name)
            if m:
                versions.add(m.group(1))
    if len(versions) >= threshold:
        findings.append({
            "check": "release_docs_versions", "severity": "WARN",
            "path": str(release_dir.relative_to(root)) if release_dir.is_dir() else "docs/release",
            "versions": len(versions), "threshold": threshold,
        })

    # 3. hooks content drift (G9: reuse existing helpers)
    if td.get("hooks_drift_detection", True):
        hooks_src_dir = root / ARCHGUARD_HOOKS_REL
        git_hooks_dir = root / ".git/hooks"
        if hooks_src_dir.is_dir():
            for hook_name in sorted(p.name for p in hooks_src_dir.iterdir() if p.is_file()):
                installed = git_hooks_dir / hook_name
                if not installed.is_file():
                    findings.append({
                        "check": "hooks_drift", "severity": "WARN",
                        "hook": hook_name, "reason": "not installed in .git/hooks",
                    })
                    continue
                installed_text, read_err = _external_validation_read_text(installed)
                if installed_text is None:
                    findings.append({
                        "check": "hooks_drift", "severity": "WARN",
                        "hook": hook_name, "reason": f"cannot read installed: {read_err}",
                    })
                    continue
                installed_text = installed_text.replace("\r\n", "\n")
                source_text = _external_validation_canonical_hook_text(hook_name, root=root)
                if source_text is None:
                    findings.append({
                        "check": "hooks_drift", "severity": "WARN",
                        "hook": hook_name, "reason": "canonical source missing",
                    })
                elif source_text != installed_text:
                    findings.append({
                        "check": "hooks_drift", "severity": "WARN",
                        "hook": hook_name, "reason": "source != installed content",
                    })

    # 4. technical-debt ledger cross-validation
    open_items = deferred_items = 0
    if td.get("ledger_cross_validate", True):
        ledger_path = root / ARCHGUARD_LEDGER_REL
        if ledger_path.is_file():
            try:
                ledger_text = ledger_path.read_text(encoding="utf-8")
                # Restrict to the 登记项 section so other tables are not parsed.
                rows = _parse_markdown_table_rows(ledger_text, section_title="登记项")
            except OSError:
                rows = []
            # _parse_markdown_table_rows returns list-of-cell-lists. The first surviving
            # row is the header (e.g. 债务 ID | ... | 承载版本 | 状态 | ...).
            header = rows[0] if rows else []
            norm_header = [h.strip().replace(" ", "") for h in header]
            idx_status = norm_header.index("状态") if "状态" in norm_header else None
            idx_carry = norm_header.index("承载版本") if "承载版本" in norm_header else None
            idx_id = norm_header.index("债务ID") if "债务ID" in norm_header else 0
            for cells in rows[1:]:
                def _cell(i):
                    return cells[i].strip() if (i is not None and i < len(cells)) else ""
                status = _cell(idx_status)
                carrying = _cell(idx_carry)
                tid = _cell(idx_id) or "?"
                if status in ("OPEN", "IN_PROGRESS"):
                    open_items += 1
                    if not carrying or carrying in ("待评估", "TBD", "N/A"):
                        findings.append({
                            "check": "ledger_no_carrying_version", "severity": "WARN",
                            "ledger_id": tid, "status": status,
                            "reason": "OPEN/IN_PROGRESS without 承载版本",
                        })
                elif status == "DEFERRED":
                    deferred_items += 1

    errors = sum(1 for f in findings if f["severity"] == "ERROR")
    warnings = sum(1 for f in findings if f["severity"] == "WARN")
    return {
        "findings": findings,
        "summary": {"errors": errors, "warnings": warnings,
                    "open_items": open_items, "deferred_items": deferred_items},
    }


def check_complexity(root=None, schema=None):
    """REQ-101 ArchGuard check 4: complexity. 0.58.0 uses a line-based proxy.

    AST cyclomatic complexity is deferred to 0.59.0+ (complexity.enabled=false).
    The line-based proxy reuses function-length data from architecture-health.
    """
    root = Path(root) if root is not None else ROOT
    if schema is None:
        schema, err = _archguard_load_schema(root)
        if schema is None:
            return {"error": err, "findings": [],
                    "summary": {"errors": 0, "warnings": 0},
                    "enabled": False}
    cx = schema.get("complexity", {})
    enabled = bool(cx.get("enabled", False))
    if not enabled:
        return {
            "enabled": False,
            "findings": [],
            "summary": {"errors": 0, "warnings": 0},
            "note": cx.get("note") or "AST complexity deferred; 0.58.0 uses line-based proxy — see check-architecture-health",
        }
    # When enabled (future 0.59.0+), repurpose the architecture-health function-size
    # data as a line-based proxy for cyclomatic complexity.
    arch = check_architecture_health(root=root, schema=schema)
    warn_n = cx.get("warn_cyclomatic", 15)
    error_n = cx.get("error_cyclomatic", 30)
    findings = []
    for f in arch.get("findings", []):
        if f.get("check") != "function_size":
            continue
        n = f.get("lines", 0)
        sev = _archguard_severity(n, warn_n, error_n)
        if sev:
            findings.append({
                "check": "complexity_proxy", "severity": sev,
                "path": f.get("path"), "name": f.get("name"),
                "lines": n, "lineno": f.get("lineno"),
            })
    errors = sum(1 for f in findings if f["severity"] == "ERROR")
    warnings = sum(1 for f in findings if f["severity"] == "WARN")
    return {
        "enabled": True, "findings": findings,
        "summary": {"errors": errors, "warnings": warnings},
    }


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
    """FIX-160: ArchGuard check 5 — governance data volume threshold.

    Guards RISK-039 (governance data bloat) directly. Scans the governance
    hot files (plan-tracker / evidence-log / decision-log / risk-log) declared
    in architecture-health.json `governance_data_size.files` and emits a
    WARN/ERROR finding when a file exceeds warn_bytes / error_bytes. The
    error threshold (250KB) is set just below the 256KB agent single-read
    limit so the warning fires before a governance file becomes unreadable.

    FIX-270 (mixed-root): the *schema* (thresholds / file list) is a plugin
    asset and is loaded from the plugin package; the *facts* to measure are
    the governed project's hot files, so when ``root`` is not explicit the
    file paths resolve against HOST_PROJECT_ROOT (never the plugin package
    root). An explicit ``root`` keeps the legacy fixture semantics (schema +
    facts from the same root).

    Advisory by default (inherits gate_integration.fatal_on_error=false).
    """
    if root is not None:
        schema_root = fact_root = Path(root)
    else:
        schema_root = ROOT
        fact_root = HOST_PROJECT_ROOT
    if schema is None:
        schema, err = _archguard_load_schema(schema_root)
        if schema is None:
            return {"error": err, "findings": [],
                    "summary": {"errors": 0, "warnings": 0},
                    "enabled": False}
    gds = schema.get("governance_data_size", {})
    enabled = bool(gds.get("enabled", True))
    if not enabled:
        return {
            "enabled": False, "findings": [],
            "summary": {"errors": 0, "warnings": 0},
            "note": gds.get("note") or "governance_data_size disabled",
        }
    # DEC-295(1) track-1 recalibration (user ruling, 2026-09-29): the
    # evidence-log face carries a PER-FILE override — warn 400000 /
    # error 650000. Calibration basis: the typed hot-table steady state =
    # 199 permanently-hot registered-ID rows (~280-300KB) + the working
    # set (0.92 closeout + 0.93 in flight); measured 515KB + migration
    # wobble headroom. All OTHER faces keep the global 200000/250000
    # lines (the 256KB single-read guard rationale stays intact for
    # them; decision-log's EXC-003 exception remains meaningful).
    warn_bytes = gds.get("warn_bytes", 200000)
    error_bytes = gds.get("error_bytes", 250000)
    file_overrides = gds.get("file_overrides", {})
    files = gds.get("files", [])
    findings = []
    for rel in files:
        path = fact_root / rel
        if not path.exists():
            continue
        size = path.stat().st_size
        override = file_overrides.get(rel, {})
        face_warn = override.get("warn_bytes", warn_bytes)
        face_error = override.get("error_bytes", error_bytes)
        sev = _archguard_severity(size, face_warn, face_error)
        if sev:
            findings.append({
                "check": "governance_data_size", "severity": sev,
                "path": rel, "bytes": size,
                "reason": f"{size} bytes ({size/1024:.1f} KB) exceeds {sev.lower()}_bytes={face_warn if sev=='WARN' else face_error}",
            })
    errors = sum(1 for f in findings if f["severity"] == "ERROR")
    warnings = sum(1 for f in findings if f["severity"] == "WARN")
    result = {
        "enabled": True, "findings": findings,
        "summary": {"errors": errors, "warnings": warnings},
    }
    # FEAT-076 (DEC-278 Q5 three-track semantics, 0.93 switch): track 1 =
    # the hot working-set capacity gate above (unchanged schema-driven
    # severity); track 2 = full-library integrity (check-archive-integrity,
    # separate check); track 3 = total-volume growth monitoring — reported
    # here as informational layer facts (hot/cold/total), no new finding
    # severity. Growth-rate alerting rides the weekly metric duty (EXC
    # family terms) instead of a second threshold.
    try:
        if root is not None:
            _gov = Path(root) / ".governance"
            ds = _archive_reader(
                sample_path=_gov / "plan-tracker.md",
                evidence_path=_gov / "evidence-log.md",
            )
        else:
            ds = _archive_reader()
        _stats = ds.layer_stats()
        result["layers"] = _stats["layers"]
        result["family_stats"] = _stats["families"]
    except Exception:  # noqa: BLE001 — informational track, never fatal
        result["layers"] = None
    return result


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
    """Run release readiness checks used by the stage-release workflow."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    skip_execution_gates = getattr(args, "skip_execution_gates", False)
    lineage_mode = getattr(args, "lineage_mode", None) or "candidate"
    result = check_release_readiness(
        version=getattr(args, "version", None),
        require_changelog=getattr(args, "require_changelog", False),
        run_runtime_adapters=getattr(args, "runtime_adapters", False),
        run_execution_gates=not skip_execution_gates,
        lineage_mode=lineage_mode,
        release_commit=getattr(args, "release_commit", None),
        lineage_remote=getattr(args, "lineage_remote", "origin"),
        release_unit=getattr(args, "unit", None),
        require_delivery_evidence=getattr(args, "require_delivery_evidence", False),
    )
    if getattr(args, "json", False):
        write_cli_json(result, indent=2)
        if not result["pass"]:
            sys.exit(1)
        return
    if "release_replay" in result["details"]:
        sys.exit(result["issues"][0])


    print()
    print("=== Release Readiness Check ===")
    if getattr(args, "version", None):
        print(f"  Version: {args.version}")
    print(f"  Runtime adapters: {'enabled' if getattr(args, 'runtime_adapters', False) else 'static'}")
    print(f"  Execution gates: {'skipped' if skip_execution_gates else 'enabled'}")
    print(f"  Lineage mode: {lineage_mode}")
    for label, detail in result["details"].items():
        if detail.get("skipped"):
            # FEAT-016 / RISK-049 ③: an intentionally not-run gate must be
            # disclosed with its reason (WARN semantics) — never a silent
            # absence, never a mis-FAIL of history queries
            # (--skip-execution-gates / BR-4 released-history).
            print(f"  [SKIP] {label.replace('_', ' ')} — "
                  f"{detail.get('skip_reason')}")
            continue
        status = "PASS" if detail["pass"] else "FAIL"
        print(f"  [{status}] {label.replace('_', ' ')}")
        if detail.get("boundary"):
            print(f"    boundary: {detail['boundary']}")
        for gate_result in detail.get("results", []):
            gate_status = "PASS" if gate_result["pass"] else "FAIL"
            exit_code = gate_result["exit_code"]
            print(f"    [{gate_status}] {gate_result['label']} (exit={exit_code})")
        for issue in detail.get("issues", [])[:10]:
            print(f"    - {issue}")
        if len(detail.get("issues", [])) > 10:
            print(f"    ... and {len(detail['issues']) - 10} more")
    if result["pass"]:
        print("\n  Result: PASSED - release readiness checks are green.")
    else:
        print(f"\n  Result: FAILED - {len(result['issues'])} issue(s).")
        sys.exit(1)


# ── Standalone CLI wrappers for new checks ────────────────────────

def cmd_check_cross_references(args):
    """CLI wrapper for cross-reference checking (SYSGAP-008)."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    result = check_cross_references()
    print()
    print("=== Cross-Reference Check ===")
    print(f"  Files scanned: {result['total_files_scanned']}")
    print(f"  References extracted: {result['total_refs']}")
    fail = False

    if result["dangling"]:
        fail = True
        print(f"\n  [FAIL] {len(result['dangling'])} dangling reference(s):")
        for d in result["dangling"]:
            print(f"    - {d['source']}:{d['line']} -> {d['target']}")
    else:
        print(f"\n  [PASS] No dangling references.")

    if result["deprecated"]:
        fail = True
        print(f"\n  [FAIL] {len(result['deprecated'])} deprecated path(s):")
        for d in result["deprecated"]:
            print(f"    - {d['source']}:{d['line']}: {d['target']} ({d['deprecated_pattern']})")
    else:
        print(f"\n  [PASS] No deprecated paths.")

    if result["cycles"]:
        fail = True
        print(f"\n  [FAIL] {len(result['cycles'])} circular reference(s):")
        for cycle in result["cycles"]:
            print(f"    - {' -> '.join(cycle)}")
    else:
        print(f"\n  [PASS] No circular references.")

    # FIX-432 (F-4/F-A2) / FIX-436 F-8 wording: citation/note quote-sync
    # guard; the current check_cross_references() always emits the key —
    # .get only tolerates pre-FIX-432/partial dict shapes that lack it.
    quote_sync = result.get("quote_sync", [])
    if quote_sync:
        fail = True
        print(f"\n  [FAIL] {len(quote_sync)} quote-sync issue(s) (FIX-432 F-4/F-A2):")
        for issue in quote_sync:
            print(f"    - {issue}")
    else:
        print(f"\n  [PASS] Citation/note quote sync clean (FIX-432 F-4/F-A2).")

    # FEAT-088 (F-A3): exploration-channel evidence-form guard sub-face.
    channels_face = result.get("exploration_channels", {}) or {}
    channel_issues = channels_face.get("issues", [])
    if channel_issues:
        fail = True
        print(f"\n  [FAIL] {len(channel_issues)} exploration-channel "
              f"evidence-form issue(s) (FEAT-088 F-A3):")
        for issue in channel_issues:
            print(f"    - {issue}")
    else:
        print(f"\n  [PASS] Exploration-channel evidence forms clean "
              f"(FEAT-088 F-A3).")
    for advisory in (channels_face.get("advisories") or [])[:5]:
        print(f"  [ADVISORY] {advisory}")
    layering = channels_face.get("probe_layering") or {}
    if layering:
        print("\n  Probe layering (honesty statement):")
        for label, text in layering.items():
            print(f"    - {label}: {text}")

    # FIX-436 (F-B3 / DEC-317): M10.2 sample-report exploration-block
    # presence advisory — WARN-class, disclosed but never counted toward
    # the exit code (MUST NOT be a blocking FAIL per DEC-317).
    for advisory in check_exploration_sample_advisories():
        print(f"  [ADVISORY] {advisory}")

    print()
    if fail:
        sys.exit(1)


def cmd_check_exploration_channels(args):
    from exploration_evidence import cmd_check_exploration_channels as run
    return run(args, check_exploration_channels=check_exploration_channels)


def cmd_check_loop_role_skills(_args):
    from host_validation_cli import cmd_check_loop_role_skills as run
    return run(_args, check_loop_role_skill_consistency=check_loop_role_skill_consistency)


def cmd_check_sequential_ids(args):
    """CLI wrapper for sequential ID checking (SYSGAP-009)."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    result = check_sequential_ids()
    print()
    print("=== Sequential ID Check ===")
    fail = False

    def _report(prefix, ids, gaps):
        nonlocal fail
        if ids:
            print(f"  {prefix}: {ids[0]:03d}-{ids[-1]:03d} ({len(ids)} entries)")
        else:
            print(f"  {prefix}: no entries found")
        if gaps:
            fail = True
            print(f"    [FAIL] Gaps detected: missing {gaps}")
        else:
            print(f"    [PASS] No gaps.")

    _report("DEC", result["dec_ids"], result["dec_gaps"])
    _report("EVD", result["evd_ids"], result["evd_gaps"])
    _report("RISK", result["risk_ids"], result["risk_gaps"])

    orphans = (result.get("orphan_evidence_refs", []) +
               result.get("orphan_decision_refs", []) +
               result.get("orphan_risk_refs", []))
    if orphans:
        fail = True
        print(f"\n  [FAIL] {len(orphans)} cross-reference(s) to non-existent task IDs: {orphans}")
    else:
        print(f"\n  [PASS] All cross-referenced task IDs exist in plan-tracker.")

    missing_evd = result.get("completed_missing_evidence", [])
    if missing_evd:
        fail = True
        print(f"  [FAIL] {len(missing_evd)} completed task(s) without evidence: {missing_evd}")
    else:
        print(f"  [PASS] All completed tasks have evidence.")

    print()
    if fail:
        sys.exit(1)


def cmd_check_structural_validity(args):
    """CLI wrapper for structural validity checking (SYSGAP-010)."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    issues = check_structural_validity()
    print()
    print("=== Structural Validity Check ===")
    if issues:
        print(f"  [FAIL] {len(issues)} structural issue(s):")
        for v in issues:
            ftype = v.get("type", "unknown")
            ffile = v.get("file", "?")
            detail = v.get("detail", "")
            print(f"    - [{ftype}] {ffile}: {detail}")
        print()
        sys.exit(1)
    print(f"  [PASS] All governance files have valid structure.")
    print()


def cmd_check_commit_scope(args):
    """CLI wrapper for commit scope verification (SYSGAP-012)."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    limit = args.limit if hasattr(args, 'limit') else 20
    result = check_commit_scope(limit=limit)
    print()
    print("=== Commit Scope Verification ===")
    if result.get("error"):
        print(f"  [ERROR] {result['error']}")
        print()
        return
    print(f"  Recent commits checked: {result['total_checked']}")
    issues = result["issues"]
    if issues:
        print(f"\n  [WARN] {len(issues)} scope discipline issue(s):")
        for v in issues:
            itype = v.get("type", "?")
            detail = v.get("detail", "")
            sha = v.get("sha", "?")
            print(f"    - [{itype}] {sha}: {detail}")
    else:
        print(f"\n  [PASS] All recent commits have clean scope discipline.")
    print()


def cmd_check_goal_alignment(args):
    """CLI wrapper for goal alignment checking (SYSGAP-023)."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    result = check_goal_alignment()
    fail = False
    print()
    print("=== Goal Alignment Check ===")
    if not result["has_project_goal"]:
        print(f"  [WARN] plan-tracker missing 项目目标 field.")
    else:
        project_goal_short = result["project_goal"][:60]
        print(f"  [INFO] 项目目标: {project_goal_short}...")
    print(f"  Impact analysis entries: {len(result['entries'])}")
    exempted = result.get("historical_exempted", [])
    print(f"  Historical exempted (FIX-371/DEC-227 ✅-terminal + FIX-390 writer-committed, skipped): {len(exempted)}")
    for row in exempted:
        print(f"    - {row['task_id']} ({row['evd_id']}): {row['status']}")
    if result["entries"]:
        for e in result["entries"]:
            if e["status"] == "FAIL":
                fail = True
                if not e["has_goal"]:
                    print(f"  [FAIL] {e['task_id']} ({e['evd_id']}): 缺少 目标对齐: 字段")
                else:
                    print(f"  [FAIL] {e['task_id']} ({e['evd_id']}): 目标对齐: 仅 {e['goal_len']} chars (需 >= 30)")
            elif e["status"] == "PASS":
                print(f"  [PASS] {e['task_id']} ({e['evd_id']}): {e['goal_len']} chars")
        if result["duplicates"]:
            print(f"  [WARN] {len(result['duplicates'])} duplicate goal alignment(s):")
            for t1, t2 in result["duplicates"]:
                print(f"    - {t1} <-> {t2}")
    else:
        print(f"  [PASS] No impact analysis entries to check.")
    if not fail and result["has_project_goal"]:
        print(f"  [PASS] All impact analysis entries have valid goal alignment.")
    print()
    if fail:
        sys.exit(1)


def cmd_check_user_impact(args):
    """CLI wrapper for user impact checking (SYSGAP-024)."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    result = check_user_impact()
    fail = False
    print()
    print("=== User Impact Check ===")
    print(f"  Impact analysis entries: {len(result['entries'])}")
    exempted = result.get("historical_exempted", [])
    print(f"  Historical exempted (FIX-371/DEC-227 ✅-terminal + FIX-390 writer-committed, skipped): {len(exempted)}")
    for row in exempted:
        print(f"    - {row['task_id']} ({row['evd_id']}): {row['status']}")
    if result["entries"]:
        for e in result["entries"]:
            status_label = {
                "BLOCKING": "BLOCK",
                "FAIL": "FAIL",
                "WARN": "WARN",
                "PASS": "PASS",
            }.get(e["status"], "?")
            if e["status"] in ("BLOCKING", "FAIL"):
                fail = True
                for issue in e["issues"]:
                    print(f"  [{status_label}] {e['task_id']} ({e['evd_id']}): {issue}")
            elif e["status"] == "WARN":
                for issue in e["issues"]:
                    print(f"  [WARN] {e['task_id']} ({e['evd_id']}): {issue}")
            else:
                print(f"  [PASS] {e['task_id']} ({e['evd_id']}): "
                      f"获得={e['obtain']}, 体验变化={e['exp_change']}, "
                      f"迁移指南={e['migration']}")
    else:
        print(f"  [PASS] No impact analysis entries to check.")
    if not fail and not result["blocking"]:
        print(f"  [PASS] All impact analysis entries have valid user impact analysis.")
    print()
    if fail:
        sys.exit(1)


# ── SYSGAP-037: check-agent-team subcommand ──────────────────────

def cmd_check_agent_team(args):
    from host_validation_cli import cmd_check_agent_team as run
    return run(args, check_agent_activation=check_agent_activation, check_agent_team_review=check_agent_team_review)


def cmd_check_version_consistency(_args):
    """Run version consistency check across all declaration locations."""
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    issues = check_version_consistency()

    print("\n=== Version Consistency Check ===")
    print(f"  Source of truth: skills/software-project-governance/SKILL.md")
    print(f"  Files checked: 12 (SKILL.md, manifest.json, marketplace.json, 3 plugin.json, CHANGELOG, plan-tracker, 4 hooks) + bootstrap markers (AGENTS.md, CLAUDE.md)")

    fail_items = [i for i in issues if not i.startswith("[WARN]")]
    warn_items = [i for i in issues if i.startswith("[WARN]")]

    if warn_items:
        print(f"\n  Warnings ({len(warn_items)}):")
        for w in warn_items:
            print(f"    {w}")

    if fail_items:
        print(f"\n  Failures ({len(fail_items)}):")
        for f in fail_items:
            print(f"    {f}")
        print(f"\n  Result: FAILED — {len(fail_items)} mismatch(es)")
        sys.exit(1)
    else:
        print(f"\n  Result: PASSED — all version declarations consistent")
    print()


def cmd_check_projection_sync(args):
    """Run projection/fixture sync guard independently."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    result = check_projection_sync()
    print("\n=== Projection Sync Check ===")
    print(f"  Source version: {result['source_version'] or 'unknown'}")
    print(f"  Mirrored files checked: {result['mirrors_checked']}")
    if result.get("mirrors_skipped_untracked"):
        print(f"  Untracked local projection copies skipped: {result['mirrors_skipped_untracked']}")
    if result["version_checks"]:
        print("  Version checks:")
        for item in result["version_checks"]:
            print(f"    - {item['label']}: {item['version'] or 'missing'} ({item['path']})")
    if result["issues"]:
        print(f"\n  Result: FAILED — {len(result['issues'])} issue(s)")
        for issue in result["issues"][:20]:
            print(f"    - {issue}")
        if len(result["issues"]) > 20:
            print(f"    ... and {len(result['issues']) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("\n  Result: PASSED — projection files and version declarations are synchronized")
    print()
    # FEAT-037: entry-file bootstrap projection rides the same guard (one command covers both surfaces).
    entry_result = projection_checks.check_entry_bootstrap_sync()
    entry_failed = not projection_checks.print_entry_bootstrap_report(entry_result)
    if entry_failed or (getattr(args, "fail_on_issues", False) and not entry_result["pass"]):
        sys.exit(1)


cmd_check_entry_bootstrap_sync = projection_checks.cmd_check_entry_bootstrap_sync


def cmd_check_injection_contract(args):
    """Run the injection-surface anchor check independently (FIX-253/REQ-112)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    result = check_injection_contract()
    print("\n=== Injection Contract Check (FIX-253/REQ-112) ===")
    print(f"  Files checked: {result['files_checked']}; anchors: {result['anchors_checked']}"
          + (f"; {result['staged_summary']}" if result["staged_summary"] else ""))
    if result["issues"]:
        print(f"\n  Result: FAILED — {len(result['issues'])} issue(s)")
        for issue in result["issues"][:20]:
            print(f"    - {issue}")
        if len(result["issues"]) > 20:
            print(f"    ... and {len(result['issues']) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("\n  Result: PASSED — injection surfaces carry the behavior-contract anchors")
    print()


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
    """Validate declarative per-version release manifests and live Git facts."""
    result = validate_release_ledger(
        RepositoryContext(HOST_PROJECT_ROOT, timeout=getattr(args, "timeout", 15)),
        manifests_dir=PLUGIN_ROOT / "skills/software-project-governance/core/releases",
        version=getattr(args, "version", None),
        remote=getattr(args, "remote", "origin"),
        verify_remote=not getattr(args, "no_remote", False),
    ).as_dict()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["state"] != "PASS":
        sys.exit({"FAIL": 1, "UNKNOWN": 2, "BLOCKED": 3}.get(result["state"], 1))


def cmd_release_projection(args):
    """Check or atomically write declared artifact projections.

    FIX-405 / RISK-061: the --write face appends an ``sd_integrity`` scan
    over the just-written projection targets (os.access R_OK + takeown/
    icacls remediation template) — restricted-token SD damage surfaces at
    the write moment; a damaged face FAILs the command (exit 1) instead
    of biting the next random access.
    """
    config = Path(args.config).resolve() if getattr(args, "config", None) else None
    if getattr(args, "write", False):
        result = write_projections(PLUGIN_ROOT, config).as_dict()
        from checks.sd_integrity import projection_face_paths, scan_sd_readability
        # FIX-406 F-1: lift the face error instead of silently scanning an
        # empty path set behind .get("paths", []).
        _face = projection_face_paths(PLUGIN_ROOT, config)
        _face_error = _face.get("error")
        sd_scan = scan_sd_readability(_face.get("paths", []))
        result["sd_integrity"] = {**sd_scan, "face_error": _face_error}
        if _face_error:
            result["state"] = "FAIL"
            result["issues"] = list(result.get("issues", [])) + [
                f"sd integrity: {_face_error}"]
        elif not sd_scan["pass"]:
            result["state"] = "FAIL"
            result["issues"] = list(result.get("issues", [])) + [
                "sd integrity: {0} unreadable — remediate: {1}".format(
                    path, cmd)
                for path, cmd in zip(sd_scan["unreadable"],
                                      sd_scan["remediation"])]
    else:
        result = check_projections(PLUGIN_ROOT, config).as_dict()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["state"] != "PASS":
        sys.exit({"FAIL": 1, "UNKNOWN": 2, "BLOCKED": 3}.get(result["state"], 1))


def cmd_quality_tools(_args):
    """Report optional ruff/mypy availability without overclaiming PASS."""
    result = probe_quality_tools()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["state"] == "FAIL":
        sys.exit(1)


def cmd_check_hot_fact_source(args):
    """Run hot fact-source consistency guard independently."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    issues = check_hot_fact_source_consistency()
    print("\n=== Hot Fact-Source Consistency Check ===")
    if issues:
        print(f"  Result: FAILED — {len(issues)} issue(s)")
        for issue in issues[:20]:
            print(f"    - {issue}")
        if len(issues) > 20:
            print(f"    ... and {len(issues) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("  Result: PASSED — hot fact-source sections are synchronized")
    print()


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

def _archguard_print_findings(title, result, hint_key="check"):
    """Render a 3-level ArchGuard result; return (errors, warnings).

    FEAT-075: findings matched by an EFFECTIVE governance exception carry an
    ``exception accepted (ref, expires)`` suffix — annotation only; the
    severity, bytes, and summary counts above stay exactly as the check
    produced them (no registry → byte-identical pre-FEAT-075 output).
    """
    s = result.get("summary", {}) or {}
    errors = int(s.get("errors", 0))
    warnings = int(s.get("warnings", 0))
    # FEAT-075 R0 F-2: file-level registry errors disclosed once (first
    # finding line); "" when clean — output unchanged.
    reg_err = _exception_registry_error_note()
    err_shown = not reg_err
    for f in result.get("findings", [])[:25]:
        sev = f.get("severity", "?")
        extra = ""
        for k in ("lines", "count", "duplicate_pct", "versions", "bytes"):
            if k in f:
                extra = f" {k}={f[k]}"
                break
        loc = f.get("path") or f.get("hook") or f.get("ledger_id") or ""
        detail = f.get("name") or f.get("reason") or f.get("pattern") or ""
        note = _exception_note(f.get(hint_key), loc, f.get("severity"),
                               bytes_value=f.get("bytes"))
        if not err_shown:
            note += ("  " if note else "") + reg_err
            err_shown = True
        print(f"  [{sev}] {f.get(hint_key, '?')}: {loc} {detail}{extra}{note}".rstrip())
    more = len(result.get("findings", [])) - 25
    if more > 0:
        print(f"    ... and {more} more")
    return errors, warnings


def cmd_check_architecture_health(args):
    from checks.architecture_health import run_architecture_health

    run_architecture_health(args, HOST_PROJECT_ROOT, PLUGIN_ROOT, PLUGIN_ROOT / ARCHGUARD_SCHEMA_REL,
                            check_architecture_health, _archguard_print_findings)


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
_TASK_ID_IN_REF_RE = re.compile(r"\b([A-Z]+-\d+)\b")


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
_GOVERNANCE_STORE_MARKER_PREFIX = "机器写入：governance-store"

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
_EVIDENCE_MACHINE_CREDENTIAL_RE = re.compile(
    re.escape(_GOVERNANCE_STORE_MARKER_PREFIX)
    + r"\s+evidence-append\s+op-[0-9a-f]{32}\b"
)


def _row_has_governance_store_machine_credential(raw_line):
    from write_guard_records import _row_has_governance_store_machine_credential as has_receipt
    return has_receipt(raw_line, receipt_pattern=_EVIDENCE_MACHINE_CREDENTIAL_RE)

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
        store_prefix=_GOVERNANCE_STORE_MARKER_PREFIX,
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
    """Run REQ-101 ArchGuard source/projection duplicate-code guard (advisory in 0.58.0)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    result = check_duplicate_code()
    print("\n=== Duplicate Code Check (ArchGuard) ===")
    if result.get("error"):
        print(f"  [ERROR] {result['error']}")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
        print()
        return
    errors, warnings = _archguard_print_findings("Duplicate Code", result)
    print(f"\n  Pairs checked: {result.get('pairs_checked', 0)}")
    for x in result.get("exemptions", []):
        reason = x.get("reason", "")
        print(f"  [EXEMPT] {x.get('path', '')}"
              + (f" — {reason}" if reason else ""))
    print(f"  Result: ISSUES FOUND — {errors} ERROR, {warnings} WARN")
    if getattr(args, "fail_on_issues", False) and errors > 0:
        sys.exit(1)
    print()


def cmd_check_technical_debt(args):
    """Run REQ-101 ArchGuard technical-debt guard (residue/docs/hooks-drift/ledger; advisory)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    result = check_technical_debt()
    print("\n=== Technical Debt Check (ArchGuard) ===")
    if result.get("error"):
        print(f"  [ERROR] {result['error']}")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
        print()
        return
    errors, warnings = _archguard_print_findings("Technical Debt", result)
    s = result.get("summary", {}) or {}
    print(f"\n  Ledger: {s.get('open_items', 0)} OPEN/IN_PROGRESS, {s.get('deferred_items', 0)} DEFERRED")
    print(f"  Result: ISSUES FOUND — {errors} ERROR, {warnings} WARN")
    if getattr(args, "fail_on_issues", False) and errors > 0:
        sys.exit(1)
    print()


def cmd_check_complexity(args):
    """Run REQ-101 ArchGuard complexity guard (line-based proxy in 0.58.0; advisory)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    result = check_complexity()
    print("\n=== Complexity Check (ArchGuard) ===")
    if result.get("error"):
        print(f"  [ERROR] {result['error']}")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
        print()
        return
    if not result.get("enabled", False):
        print(f"  [INFO] complexity disabled — {result.get('note', 'line-based proxy; see check-architecture-health')}")
        print()
        return
    errors, warnings = _archguard_print_findings("Complexity", result)
    print(f"\n  Result: ISSUES FOUND — {errors} ERROR, {warnings} WARN")
    if getattr(args, "fail_on_issues", False) and errors > 0:
        sys.exit(1)
    print()


def cmd_check_governance_data_size(args):
    """FIX-160: Run governance data volume threshold guard (advisory)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    result = check_governance_data_size()
    print("\n=== Governance Data Size Check (ArchGuard/FIX-160) ===")
    if result.get("error"):
        print(f"  [ERROR] {result['error']}")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
        print()
        return
    if not result.get("enabled", False):
        print(f"  [INFO] governance_data_size disabled — {result.get('note', '')}")
        print()
        return
    errors, warnings = _archguard_print_findings("GovernanceDataSize", result)
    if errors or warnings:
        print(f"\n  Result: ISSUES FOUND — {errors} ERROR, {warnings} WARN")
        print("  (advisory — fatal_on_error=false; see architecture-health.json governance_data_size)")
    else:
        print("\n  Result: PASSED — all governance files within size budget")
    if getattr(args, "fail_on_issues", False) and errors > 0:
        sys.exit(1)
    print()


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


_DSH_WORKFLOW_COMMANDS = {cmd.__name__: cmd for cmd in (
    cmd_check_dsh_preset_smoke, cmd_check_dsh_preset_compat, cmd_check_dsh_boundary, cmd_dsh_doctor,
)}


def _effective_dsh_command(name, native):
    if name in _DSH_WORKFLOW_COMMANDS:
        if name not in globals():
            raise AttributeError(name)
        current = globals()[name]
        if current is not _DSH_WORKFLOW_COMMANDS[name]:
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
                           command=_effective_dsh_command)


__all__ = sorted({name for name in globals() if not name.startswith("_")}
                 | {name for name in _HOST_POLICY_OWNERS if not name.startswith("_")}
                 | {"GovernanceDataSource"})


if __name__ == "__main__":
    sys.exit(main())
