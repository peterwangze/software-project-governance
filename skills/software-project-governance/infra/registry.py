"""FEAT-022 — light registry + per-command loading (AUDIT-150 §9.1).

The composition-root prototype of the 0.80.0 six-layer architecture: two
static declaration tables plus a controlled loader, so a command can be
selected and assembled **without** importing the monolith.

    COMMAND_SPECS   83 dispatch keys → handler dotted paths (§3.5 step 3)
    CHECK_SPECS     71 CheckIDs → ``contracts.CheckSpec`` rows (§3.6 / §9.1)
    LOADER_WHITELIST  the closed set of modules a declaration may name
    assemble()      L6 组合根雏形: resolve ONE command's handler on demand

Layer assignment is **L6** (§3.2: the composition root is the only layer that
may name concrete implementations). Module-level imports are stdlib +
``contracts`` (L0) + ``quickscan_registry`` (L1 data asset); nothing in the
forbidden set of §9.1 happens at import time — no directory scan, no
``pkgutil``, no engine import, no file read, no service instantiation. The
loader imports a module only when a caller resolves a declared key, and the
whitelist is an explicit closed tuple (never a package walk).

Fact sources (consumed, never re-derived — the registry owns no fact twice):

  * **FEAT-020 frozen faces** (``infra/contract_matrix/snapshots.json``):
    82 CLI dispatch keys / 70 Check segment ids — the R5 caliber. The live
    face is observed through that packet's own extractors
    (``contract_matrix.generator``), imported lazily inside the checker.
  * **FEAT-025** (``infra/quickscan_registry.py``): every segment's
    ``domain`` / ``input_deps`` / quick-policy face. Those facts are *not*
    copied here; ``_build_check_specs()`` joins them at import time and fails
    closed if the two tables ever disagree.
  * **The engine** (``verify_workflow.py``): the segment → entry mapping and
    the gate (``all_issues``) face. Both are re-judged against the live engine
    by ``tests/test_registry.py``; the declarations here are the frozen
    reading of that measurement.
  * **FEAT-021** (``infra/contracts.py``): ``CheckSpec`` is *consumed* — this
    module defines no L0 shape, and ``CHECK_SPEC_FIELDS`` is an alias of the
    contract's own field tuple.

Caliber decisions (each anchored to a measurement, not to preference):

  1. **Loader paths are attribute-qualified** (``verify_workflow.cmd_status``,
     ``checks.evidence_domain.check_evidence_completeness``). The L0 validator
     (``contracts._require_loader``) requires at least one dot and rejects
     root-level names, while the engine's dispatch table holds bare handler
     names and the 71 segments' entry points live in root-level modules
     (``verify_workflow``) as well as packages. A ``module.attr`` dotted path
     is the only form that is both contract-legal and truthfully resolvable in
     the engine's own import namespace (infra dir on ``sys.path``). Prefixing
     with ``infra.`` would be a *second* module object for the same file —
     deliberately not used.
  2. **``severity_floor`` mirrors the engine's gate face**, machine-derived:
     ``WARN`` for the segments whose section performs no ``all_issues``
     increment (advisory disclosure only — the 7 rows in
     ``ADVISORY_SEGMENTS``), ``BLOCKING`` otherwise (their findings count
     toward the gate). Segment 28o increments ``all_issues`` conditionally
     (``fatal_on_error``, default false in ``core/architecture-health.json``)
     and is therefore declared BLOCKING: the check *can* reach the gate.
  3. **Two segments are reached through a delegating engine wrapper**
     (``check-24`` → ``checks.version``, ``check-28b`` → ``checks.projection``).
     The declared loader names the *implementing* module; the degradation is
     disclosed in ``DELEGATED_LOADERS`` and machine-verified by the test
     suite (the engine function is a single-statement delegation).
  4. **``modes`` stays minimal and faithful**: the contract's mode vocabulary
     is ``full``/``quick``/``domain:<name>``; FEAT-025's ``not-quick:<CODE>``
     policy tokens are not mode names, so a segment's exclusion appears here
     as the absence of ``quick`` (the reason code stays owned by FEAT-025,
     where the Phase-2 selector reads it). No mode is invented.

Deferred by design (explicit non-goals of this slice, §9.2 / §9.3):

  * the command-scope execution context (shared file-tree / git / governance
    snapshot cache) needs the L2 ports and lands with the domain slices;
  * the command → check binding is not declared anywhere today, so
    ``assemble()`` exposes a mode/domain selection seam
    (:func:`select_checks`) and leaves ``Assembly.checks`` empty unless a
    selection token is passed — inventing a binding would be fabrication;
  * a command whose handler still lives in the monolith cannot be loaded
    without it: the registry makes that cost *visible*
    (:func:`legacy_engine_hosted`, the migrated-key disclosure) instead of
    hiding it.
"""

from __future__ import annotations

import importlib
import re
from dataclasses import dataclass, field, fields as dataclass_fields
from typing import Callable, Dict, List, Optional, Tuple

from contracts import (  # L0 — consumed, never redefined
    CheckID,
    CheckSpec,
    CommandKey,
)

import quickscan_registry as _segments  # L1 data asset (FEAT-025)

__all__ = [
    "ADVISORY_SEGMENTS",
    "Assembly",
    "CHECK_SPECS",
    "CHECK_SPEC_FIELDS",
    "CLI_KEYS_AXIS",
    "COMMAND_SPECS",
    "CommandSpec",
    "DELEGATED_LOADERS",
    "ENGINE_MODULE",
    "LOADER_WHITELIST",
    "LoaderResolutionError",
    "LoaderWhitelistViolation",
    "RegistrationReport",
    "RegistryError",
    "SEGMENTS_AXIS",
    "SEVERITY_FLOOR_ADVISORY",
    "SEVERITY_FLOOR_BLOCKING",
    "UnknownCheckID",
    "UnknownCommandKey",
    "assemble",
    "check_id_of",
    "check_ids",
    "check_spec",
    "command_keys",
    "command_spec",
    "declared_domains",
    "handler_alias_groups",
    "handler_path",
    "legacy_engine_hosted",
    "load_check",
    "load_handler",
    "loader_attr",
    "loader_module",
    "resolve_loader",
    "segment_ids",
    "segment_of",
    "select_checks",
    "verify_registration",
]

# ── vocabulary / caliber constants ──────────────────────────────────────────

ENGINE_MODULE = "verify_workflow"
"""The legacy monolith hosting most declared entries at this slice (§3.3)."""

CHECK_ID_PREFIX = "check-"
"""Stable CheckID prefix (§3.5 step 1: ``check-28p``)."""

DOMAIN_MODE_PREFIX = "domain:"
"""Execution-mode selector form for a whole domain (§3.6 ``modes``)."""

SEVERITY_FLOOR_BLOCKING = "BLOCKING"
SEVERITY_FLOOR_ADVISORY = "WARN"

CONTRACT_MODE_VOCABULARY: Tuple[str, ...] = ("full", "quick")
"""Mirror of §3.6's literal mode tokens (``domain:<name>`` is a selector)."""

ADVISORY_SEGMENTS: Tuple[str, ...] = (
    "28p", "28q", "28r", "28s", "28t", "30c", "39",
)
"""Segments whose engine section never increments ``all_issues``.

Measured, not assumed: an AST pass over ``_run_full_engine_checks`` finds the
``all_issues`` AugAssign nodes inside each ``# ── <id>. `` section; these 7
sections have none (comments mentioning the counter do not count), so their
findings are advisory disclosures — ``28p`` prints ``(advisory)``, ``28s`` /
``28t`` cite ``gate_integration.fatal_on_error=false``, ``30c`` / ``39``
declare the FIX-260 / DEC-159 gradual-WARN convention, and ``28q`` / ``28r``
print findings without touching the counter. Re-judged by
``tests/test_registry.py::CheckRegistryTests``.
"""

DELEGATED_LOADERS: Dict[str, str] = {
    "check-24": "verify_workflow.check_version_consistency",
    "check-28b": "verify_workflow.check_projection_sync",
}
"""Segment → engine-side delegating wrapper (disclosure, §3.3).

Both segments' declared loaders point at the implementing domain module while
the engine still reaches it through a one-statement wrapper. Declaring the
wrapper as the loader would cement the coupling the strangler removes, so the
implementation host is declared and the degradation is explicit here.
"""

LOADER_WHITELIST: Tuple[str, ...] = (
    ENGINE_MODULE,
    "archguard_ratchet",
    "checks.capability_registry",
    "checks.ci_domain",
    "checks.evidence_domain",
    "checks.gate_domain",
    "checks.loop_runtime_claims",
    "checks.manifest",
    "checks.projection",
    "checks.review_domain",
    "checks.risk_domain",
    "checks.snapshot_domain",
    "checks.triage_domain",
    "checks.version",
    "dsh_compat",
)
"""Closed declaration of loadable modules (§9.1 controlled loader whitelist).

Exactly the modules the two tables below name — no package walk, no entry
points, no dynamic discovery. Admitting a new module is a deliberate edit of
this tuple (and of the table that needs it).
"""

# ── errors (fail-closed, explicit, one chained base) ────────────────────────


class RegistryError(ValueError):
    """Illegal or unresolvable registry operation (fail-closed, never guessed)."""


class UnknownCommandKey(RegistryError):
    """A dispatch key that the registry does not declare."""


class UnknownCheckID(RegistryError):
    """A CheckID / segment that the registry does not declare."""


class LoaderWhitelistViolation(RegistryError):
    """A loader path naming a module outside ``LOADER_WHITELIST`` (§9.1)."""


class LoaderResolutionError(RegistryError):
    """A malformed loader path, or a declared entry that cannot be resolved."""


# ── command declaration: 82 keys → handler dotted path (FEAT-020 caliber) ───

_COMMANDS: Tuple[Tuple[CommandKey, str], ...] = (
    ("agent-locks-acquire", "verify_workflow.cmd_agent_locks_acquire"),
    ("agent-runtime-e2e", "verify_workflow.cmd_agent_runtime_e2e"),
    ("archguard-ratchet", "archguard_ratchet.cmd_archguard_ratchet"),
    ("capability-context", "verify_workflow.cmd_capability_context"),
    ("change-triage", "verify_workflow.cmd_change_triage"),
    ("check-acceptance-contracts",
     "verify_workflow.cmd_check_acceptance_contracts"),
    ("check-agent-adapters", "verify_workflow.cmd_check_agent_adapters"),
    ("check-agent-team", "verify_workflow.cmd_check_agent_team"),
    ("check-architecture-health",
     "verify_workflow.cmd_check_architecture_health"),
    ("check-archive-integrity", "verify_workflow.cmd_check_archive_integrity"),
    ("check-capability-registry",
     "checks.capability_registry.cmd_check_capability_registry"),
    ("check-commit-scope", "verify_workflow.cmd_check_commit_scope"),
    ("check-complexity", "verify_workflow.cmd_check_complexity"),
    ("check-cross-references", "verify_workflow.cmd_check_cross_references"),
    ("check-deterministic-scaffolds",
     "verify_workflow.cmd_check_deterministic_scaffolds"),
    ("check-dsh-preset-compat",
     "verify_workflow.cmd_check_dsh_preset_compat"),
    ("check-dsh-preset-smoke", "verify_workflow.cmd_check_dsh_preset_smoke"),
    ("check-dsh-skills-manifest",
     "verify_workflow.cmd_check_dsh_skills_manifest"),
    ("check-duplicate-code", "verify_workflow.cmd_check_duplicate_code"),
    ("check-first-session-measurement",
     "verify_workflow.cmd_check_first_session_measurement"),
    ("check-flow-unit-runtime", "verify_workflow.cmd_check_flow_unit_runtime"),
    ("check-goal-alignment", "verify_workflow.cmd_check_goal_alignment"),
    ("check-governance", "verify_workflow.cmd_check_governance"),
    ("check-governance-data-size",
     "verify_workflow.cmd_check_governance_data_size"),
    ("check-governance-pack-status",
     "verify_workflow.cmd_check_governance_pack_status"),
    ("check-governance-packs", "verify_workflow.cmd_check_governance_packs"),
    ("check-host-capability-context",
     "verify_workflow.cmd_check_host_capability_context"),
    ("check-hot-fact-source", "verify_workflow.cmd_check_hot_fact_source"),
    ("check-injection-contract", "verify_workflow.cmd_check_injection_contract"),
    ("check-interruption-policy",
     "verify_workflow.cmd_check_interruption_policy"),
    ("check-lifecycle-registry", "verify_workflow.cmd_check_lifecycle_registry"),
    ("check-locks", "verify_workflow.cmd_check_agent_locks"),
    ("check-loop-health", "verify_workflow.cmd_check_loop_health"),
    ("check-loop-role-skills", "verify_workflow.cmd_check_loop_role_skills"),
    ("check-loop-runtime-claims",
     "verify_workflow.cmd_check_loop_runtime_claims"),
    ("check-mainstream-agent-loading",
     "verify_workflow.cmd_check_mainstream_agent_loading"),
    ("check-manifest-consistency",
     "checks.manifest.cmd_check_manifest_consistency"),
    ("check-official-submission-ecosystem",
     "verify_workflow.cmd_check_official_submission_ecosystem"),
    ("check-plugin-freshness", "verify_workflow.cmd_check_plugin_freshness"),
    ("check-product-success-contracts",
     "verify_workflow.cmd_check_product_success_contracts"),
    ("check-projection-sync", "verify_workflow.cmd_check_projection_sync"),
    ("check-quality-budget", "verify_workflow.cmd_check_quality_budget"),
    ("check-readme-pack-guidance",
     "verify_workflow.cmd_check_readme_pack_guidance"),
    ("check-release", "verify_workflow.cmd_check_release"),
    ("check-review-debt", "checks.review_domain.cmd_check_review_debt"),
    ("check-runtime-readiness-matrix",
     "verify_workflow.cmd_check_runtime_readiness_matrix"),
    ("check-scaffold-templates",
     "verify_workflow.cmd_check_deterministic_scaffolds"),
    ("check-sequential-ids", "verify_workflow.cmd_check_sequential_ids"),
    ("check-structural-validity",
     "verify_workflow.cmd_check_structural_validity"),
    ("check-technical-debt", "verify_workflow.cmd_check_technical_debt"),
    ("check-user-impact", "verify_workflow.cmd_check_user_impact"),
    ("check-user-interruption-policy",
     "verify_workflow.cmd_check_interruption_policy"),
    ("check-version-consistency",
     "verify_workflow.cmd_check_version_consistency"),
    ("check-vertical-slices", "verify_workflow.cmd_check_vertical_slices"),
    ("dynamic-flow-gate-migration",
     "verify_workflow.cmd_dynamic_lifecycle_migration"),
    ("dynamic-lifecycle-migration",
     "verify_workflow.cmd_dynamic_lifecycle_migration"),
    ("e2e-check", "verify_workflow.cmd_e2e_check"),
    ("execution-packet", "verify_workflow.cmd_execution_packet"),
    ("external-project-validation",
     "verify_workflow.cmd_external_project_validation"),
    ("first-run-demo", "verify_workflow.cmd_first_run_demo"),
    ("gate", "verify_workflow.cmd_gate"),
    ("gate-check", "verify_workflow.cmd_gate_check"),
    ("gates", "verify_workflow.cmd_gates"),
    ("gemini-auth-preflight", "verify_workflow.cmd_gemini_auth_preflight"),
    ("generate-deterministic-scaffold",
     "verify_workflow.cmd_generate_deterministic_scaffold"),
    ("governance-context", "verify_workflow.cmd_governance_context"),
    ("governance-write-guard", "verify_workflow.cmd_governance_write_guard"),
    ("loop-engineering-migration",
     "verify_workflow.cmd_loop_engineering_migration"),
    ("loop-rollup", "verify_workflow.cmd_loop_rollup"),
    ("loop-telemetry", "verify_workflow.cmd_loop_telemetry"),
    ("next-candidates", "verify_workflow.cmd_next_candidates"),
    ("opencode-provider-preflight",
     "verify_workflow.cmd_opencode_provider_preflight"),
    ("quality-tools", "verify_workflow.cmd_quality_tools"),
    ("release-ledger", "verify_workflow.cmd_release_ledger"),
    ("release-projection", "verify_workflow.cmd_release_projection"),
    ("resolve-entry", "verify_workflow.cmd_resolve_entry"),
    ("review-record", "verify_workflow.cmd_review_record"),
    ("stage", "verify_workflow.cmd_stage"),
    ("stages", "verify_workflow.cmd_stages"),
    ("status", "verify_workflow.cmd_status"),
    ("task-priority-analysis", "verify_workflow.cmd_task_priority_analysis"),
    ("verify", "verify_workflow.cmd_verify"),
    ("web-console", "verify_workflow.cmd_web_console"),
)
"""83 dispatch keys from the FEAT-020 frozen face, each with the module that
*defines* its handler (machine-derived: the ``commands`` dict of ``main()``
cross-referenced with the defining module of every handler name — 4 keys are
already outside the engine, the other 79 ride the monolith)."""

# ── check declaration: 71 segments → entry dotted path ──────────────────────

_SEGMENT_LOADERS: Tuple[Tuple[str, str], ...] = (
    ("1", "checks.evidence_domain.check_evidence_completeness"),
    ("2", "checks.risk_domain.check_risk_staleness"),
    ("3", "verify_workflow.check_gate_consistency"),
    ("4", "checks.evidence_domain.check_evidence_quality"),
    ("5", "verify_workflow.check_protocol_compliance"),
    ("6", "verify_workflow.check_tier_audit_completeness"),
    ("7", "verify_workflow.check_commit_task_references"),
    ("8", "checks.risk_domain.check_risk_escalation"),
    ("9", "verify_workflow.check_task_deadline"),
    ("10", "verify_workflow.check_m5_compliance_with_record_scope"),
    ("11", "checks.manifest.check_manifest_consistency"),
    ("12", "verify_workflow.check_cross_references"),
    ("13", "verify_workflow.check_sequential_ids"),
    ("14", "verify_workflow.check_structural_validity"),
    ("15", "verify_workflow.check_commit_scope"),
    ("16", "verify_workflow.check_goal_alignment"),
    ("17", "verify_workflow.check_user_impact"),
    ("18", "checks.evidence_domain.check_fact_grounding"),
    ("18b", "checks.evidence_domain.check_structured_evidence"),
    ("18c", "verify_workflow.check_execution_packets"),
    ("18d", "verify_workflow.check_product_success_contracts"),
    ("18e", "verify_workflow.check_acceptance_contracts"),
    ("18f", "verify_workflow.check_quality_budget"),
    ("18g", "verify_workflow.check_vertical_slices"),
    ("18h", "verify_workflow.check_deterministic_scaffolds"),
    ("18i", "verify_workflow.check_interruption_policy"),
    ("19", "checks.review_domain.check_agent_team_review"),
    ("20", "verify_workflow.check_agent_activation"),
    ("21", "checks.review_domain.check_review_debt"),
    ("22", "checks.review_domain.check_review_coverage"),
    ("23", "verify_workflow.check_profile_consistency"),
    ("24", "checks.version.check_version_consistency"),
    ("25", "verify_workflow.check_untracked_files"),
    ("26", "verify_workflow.check_agent_lock_consistency"),
    ("27", "verify_workflow.check_archive_integrity"),
    ("28", "checks.review_domain.check_governance_review_fallback_policy"),
    ("28b", "checks.projection.check_projection_sync"),
    ("28c", "verify_workflow.check_hot_fact_source_consistency"),
    ("28d", "verify_workflow.check_runtime_readiness_matrix"),
    ("28e", "verify_workflow.check_first_session_measurement"),
    ("28f", "verify_workflow.check_governance_packs"),
    ("28g", "verify_workflow.check_governance_context"),
    ("28h", "verify_workflow.check_readme_pack_guidance"),
    ("28i", "verify_workflow.check_governance_pack_status"),
    ("28j", "verify_workflow.check_capability_context"),
    ("28k", "checks.capability_registry.check_capability_registry"),
    ("28l", "verify_workflow.check_host_capability_context"),
    ("28m", "verify_workflow.check_official_submission_ecosystem"),
    ("28n", "verify_workflow.check_mainstream_agent_loading"),
    ("28o", "verify_workflow.check_architecture_health"),
    ("28p", "verify_workflow.check_duplicate_code"),
    ("28q", "verify_workflow.check_technical_debt"),
    ("28r", "verify_workflow.check_complexity"),
    ("28s", "verify_workflow.check_governance_data_size"),
    ("28t", "verify_workflow.check_readme_claim_evidence_levels"),
    ("28u", "verify_workflow.check_dsh_preset_smoke"),
    ("28v", "dsh_compat.emit_check_section"),
    ("29", "checks.review_domain.check_m5_runtime_triggers"),
    ("30", "checks.review_domain.check_review_closure"),
    ("30b", "checks.review_domain.check_loop_wiring_call_sites"),
    ("30c", "checks.review_domain.check_review_machine_provenance"),
    ("31", "checks.loop_runtime_claims.scan_loop_runtime_claims"),
    ("32", "checks.triage_domain.check_change_triage"),
    ("33", "verify_workflow.check_injection_contract"),
    ("34", "verify_workflow.check_completion_recommendation"),
    ("35", "checks.snapshot_domain.check_snapshot_freshness"),
    ("36", "verify_workflow.check_risk_mitigation_closure_with_archive"),
    ("37", "checks.gate_domain.check_gate_sequence_for_release"),
    ("38", "checks.ci_domain.check_ci_evidence"),
    ("39", "checks.triage_domain.check_r1_completion_gate"),
    ("40", "verify_workflow.check_dsh_skills_manifest"),
)
"""71 segments ↔ the entry point the engine's section actually calls.

Machine-derived in two passes: the section's single check-entry call name
(``check_*`` / ``scan_*``) cross-referenced with that symbol's defining infra
module. 69 of 71 resolve uniquely; ``24`` / ``28b`` name the implementing
domain module behind an engine delegating wrapper (``DELEGATED_LOADERS``).
"""


# ── loader path parsing (shared by both tables) ──────────────────────────────

_LOADER_SEGMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _is_identifier_path(text: str) -> bool:
    return all(_LOADER_SEGMENT_RE.match(part) for part in text.split("."))


def loader_module(loader_path: str) -> str:
    """The module part of a dotted loader path (fail-closed on malformed)."""
    if not isinstance(loader_path, str) or not loader_path.strip():
        raise LoaderResolutionError(
            f"loader path must be a non-empty string, got {loader_path!r}")
    if (loader_path.endswith(".py") or "/" in loader_path
            or "\\" in loader_path or ":" in loader_path):
        raise LoaderResolutionError(
            f"loader path {loader_path!r} looks like a file path — §9.1 "
            f"loaders are dotted module paths (no extension, no separators)")
    module, separator, _attr = loader_path.rpartition(".")
    if not separator or not module:
        raise LoaderResolutionError(
            f"loader path {loader_path!r} has no dotted module segment — "
            f"expected '<module>.<entry>' (e.g. 'verify_workflow.cmd_status')")
    if not _is_identifier_path(module):
        raise LoaderResolutionError(
            f"loader path {loader_path!r} has a non-identifier module part "
            f"{module!r}")
    return module


def loader_attr(loader_path: str) -> str:
    """The entry (attribute) part of a dotted loader path."""
    module = loader_module(loader_path)
    attr = loader_path[len(module) + 1:]
    if not _LOADER_SEGMENT_RE.match(attr):
        raise LoaderResolutionError(
            f"loader path {loader_path!r} has a non-identifier entry "
            f"{attr!r}")
    return attr


def _ensure_whitelisted(loader_path: str) -> str:
    module = loader_module(loader_path)
    if module not in LOADER_WHITELIST:
        raise LoaderWhitelistViolation(
            f"loader module {module!r} (from {loader_path!r}) is not in the "
            f"controlled whitelist (§9.1) — declared modules are: "
            f"{', '.join(sorted(LOADER_WHITELIST))}")
    return module


def resolve_loader(loader_path: str) -> Callable:
    """Import the module a declared path names and return its callable entry.

    This is the *only* place the registry imports anything: malformed paths,
    out-of-whitelist modules, import failures and missing / non-callable
    entries all fail closed with an explicit message (never a guessed
    fallback).
    """
    module_name = _ensure_whitelisted(loader_path)
    attr = loader_attr(loader_path)
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 — re-raised with full context
        raise LoaderResolutionError(
            f"whitelisted module {module_name!r} ({loader_path!r}) failed to "
            f"import: {type(exc).__name__}: {exc}") from exc
    try:
        target = getattr(module, attr)
    except AttributeError as exc:
        raise LoaderResolutionError(
            f"module {module_name!r} does not define {attr!r} "
            f"(declared loader {loader_path!r}) — registration drift") from exc
    if not callable(target):
        raise LoaderResolutionError(
            f"{loader_path!r} resolves to {type(target).__name__}, not a "
            f"callable entry")
    return target


# ── command specs ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CommandSpec:
    """One registration row of the 82-key dispatch face (§3.5 step 3)."""

    key: CommandKey
    handler: str

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key.strip():
            raise RegistryError(
                f"CommandSpec.key must be a non-empty string, got {self.key!r}")
        if self.handler != self.handler.strip():
            raise RegistryError(
                f"CommandSpec({self.key!r}).handler has surrounding "
                f"whitespace: {self.handler!r}")
        _ensure_whitelisted(self.handler)


COMMAND_SPECS: Tuple[CommandSpec, ...] = tuple(
    CommandSpec(key=key, handler=handler) for key, handler in sorted(_COMMANDS)
)

_BY_KEY: Dict[str, CommandSpec] = {spec.key: spec for spec in COMMAND_SPECS}
if len(_BY_KEY) != len(COMMAND_SPECS):
    raise RegistryError("registry declares duplicate command keys")
_COMMAND_KEYS: Tuple[str, ...] = tuple(spec.key for spec in COMMAND_SPECS)


def command_keys() -> Tuple[CommandKey, ...]:
    """Every declared dispatch key, sorted (the declared CLI face)."""
    return _COMMAND_KEYS


def command_spec(key: CommandKey) -> CommandSpec:
    """Look up one command row. Unknown keys raise (fail-closed, §9.1)."""
    if not isinstance(key, str) or key not in _BY_KEY:
        raise UnknownCommandKey(
            f"command key {key!r} is not declared in the registry "
            f"({len(_COMMAND_KEYS)} keys, FEAT-020 frozen face) — undeclared "
            f"keys are refused rather than guessed (§9.1 controlled dispatch)")
    return _BY_KEY[key]


def handler_path(key: CommandKey) -> str:
    """The dotted handler path declared for one command key."""
    return command_spec(key).handler


def load_handler(key: CommandKey) -> Callable:
    """Import the module that hosts one command's handler (§9.1 按命令加载)."""
    return resolve_loader(command_spec(key).handler)


def handler_alias_groups() -> Dict[str, Tuple[str, ...]]:
    """Entry name → the keys dispatching to it, for entries with >1 key."""
    grouped: Dict[str, List[str]] = {}
    for spec in COMMAND_SPECS:
        grouped.setdefault(loader_attr(spec.handler), []).append(spec.key)
    return {attr: tuple(sorted(keys)) for attr, keys in sorted(grouped.items())
            if len(keys) > 1}


# ── check specs ─────────────────────────────────────────────────────────────

_SEGMENT_RE = re.compile(r"^([0-9]+)([a-z]?)$")


def _segment_sort_key(segment: str) -> Tuple[int, str]:
    match = _SEGMENT_RE.match(segment)
    if match is None:
        return (10 ** 9, segment)
    return (int(match.group(1)), match.group(2))


def check_id_of(segment: str) -> CheckID:
    """Bare segment → stable CheckID (``28p`` → ``check-28p``).

    Only a bare segment form is accepted. Prefixing an arbitrary string would
    mint a "CheckID" no consumer could ever resolve (``""`` → ``check-``),
    which contradicts the module's own caliber — fail-closed, never guessed —
    and the form check ``segment_of`` already applies in the other direction.
    """
    if not isinstance(segment, str) or _SEGMENT_RE.match(segment) is None:
        raise UnknownCheckID(
            f"segment {segment!r} is not a bare segment form "
            f"(expected '<digits><optional lowercase letter>', e.g. '28p')")
    return CHECK_ID_PREFIX + segment


def segment_of(check_id: CheckID) -> str:
    """Stable CheckID → bare segment; unknown forms raise (fail-closed)."""
    if not isinstance(check_id, str) or not check_id.startswith(CHECK_ID_PREFIX):
        raise UnknownCheckID(
            f"check id {check_id!r} is not a stable CheckID "
            f"(expected '{CHECK_ID_PREFIX}<segment>', e.g. 'check-28p')")
    if check_id not in _BY_CHECK_ID:
        raise UnknownCheckID(
            f"check id {check_id!r} is not declared in the registry "
            f"({len(CHECK_SPECS)} segments, FEAT-020 frozen face)")
    return check_id[len(CHECK_ID_PREFIX):]


def _build_check_specs() -> Tuple[CheckSpec, ...]:
    """Join the segment → entry table with FEAT-025's declaration face.

    ``domain`` / ``input_deps`` / the quick policy are read from FEAT-025
    rather than copied (single source per fact); the join fails closed if the
    two tables ever disagree, which is the import-time half of R5.
    """
    declared = set(_segments.registry_ids())
    authored = {segment for segment, _ in _SEGMENT_LOADERS}
    if declared != authored:
        raise RegistryError(
            f"segment registry (FEAT-025) and the loader declaration "
            f"disagree — only in FEAT-025: {sorted(declared - authored)}; "
            f"only in the registry: {sorted(authored - declared)}")
    rows: List[CheckSpec] = []
    for segment, loader in sorted(_SEGMENT_LOADERS,
                                  key=lambda row: _segment_sort_key(row[0])):
        source = _segments.segment(segment)
        modes = tuple(mode for mode in CONTRACT_MODE_VOCABULARY
                      if mode in source.modes)
        if not modes:
            raise RegistryError(
                f"segment {segment!r} declares no contract-vocabulary mode "
                f"(FEAT-025 modes={tuple(source.modes)!r})")
        _ensure_whitelisted(loader)
        rows.append(CheckSpec(
            check_id=check_id_of(segment),
            domain=source.domain,
            loader=loader,
            input_deps=tuple(source.input_deps),
            severity_floor=(SEVERITY_FLOOR_ADVISORY
                            if segment in ADVISORY_SEGMENTS
                            else SEVERITY_FLOOR_BLOCKING),
            modes=modes,
        ))
    return tuple(rows)


CHECK_SPECS: Tuple[CheckSpec, ...] = _build_check_specs()

CHECK_SPEC_FIELDS: Tuple[str, ...] = tuple(
    spec_field.name for spec_field in dataclass_fields(CheckSpec))
"""Alias of the consumed ``contracts.CheckSpec`` field tuple (no redefinition)."""

_BY_CHECK_ID: Dict[str, CheckSpec] = {spec.check_id: spec for spec in CHECK_SPECS}
if len(_BY_CHECK_ID) != len(CHECK_SPECS):
    raise RegistryError("registry declares duplicate CheckIDs")
_SEGMENTS: Tuple[str, ...] = tuple(
    spec.check_id[len(CHECK_ID_PREFIX):] for spec in CHECK_SPECS)
_BY_SEGMENT: Dict[str, CheckSpec] = {
    spec.check_id[len(CHECK_ID_PREFIX):]: spec for spec in CHECK_SPECS}
_DECLARED_DOMAINS: Tuple[str, ...] = tuple(
    sorted({spec.domain for spec in CHECK_SPECS}))


def check_ids() -> Tuple[CheckID, ...]:
    """Every declared stable CheckID (the declared Check face)."""
    return tuple(spec.check_id for spec in CHECK_SPECS)


def segment_ids() -> Tuple[str, ...]:
    """Every declared bare segment id (FEAT-020 caliber)."""
    return _SEGMENTS


def declared_domains() -> Tuple[str, ...]:
    """Every domain the declared checks belong to."""
    return _DECLARED_DOMAINS


def check_spec(check_id: CheckID) -> CheckSpec:
    """Look up one CheckSpec; accepts ``check-28p`` or bare ``28p``."""
    if isinstance(check_id, str) and not check_id.startswith(CHECK_ID_PREFIX):
        if check_id in _BY_SEGMENT:
            return _BY_SEGMENT[check_id]
    if not isinstance(check_id, str) or check_id not in _BY_CHECK_ID:
        raise UnknownCheckID(
            f"check id {check_id!r} is not declared in the registry "
            f"({len(CHECK_SPECS)} segments, FEAT-020 frozen face)")
    return _BY_CHECK_ID[check_id]


def load_check(check_id: CheckID) -> Callable:
    """Import the module that hosts one check's entry (§9.1 按命令加载)."""
    return resolve_loader(check_spec(check_id).loader)


def legacy_engine_hosted() -> Tuple[CheckID, ...]:
    """CheckIDs still loaded from the monolith — the migration face (§3.3)."""
    return tuple(spec.check_id for spec in CHECK_SPECS
                 if loader_module(spec.loader) == ENGINE_MODULE)


def select_checks(mode: Optional[str] = None,
                  domain: Optional[str] = None) -> Tuple[CheckSpec, ...]:
    """Declared check subset for a mode and/or domain (the §9.3 seam).

    Returns *declarations* only: the selector matches tokens against the
    ``modes`` / ``domain`` fields the registry already carries — it neither
    derives policy nor inspects changed files (§9.3 places the selection
    policy in L4). Unknown tokens raise instead of silently selecting
    everything, so a typo can never widen a scan.
    """
    if mode is None and domain is None:
        raise RegistryError(
            "select_checks requires a mode and/or a domain token (§9.3)")
    selected = CHECK_SPECS
    if mode is not None:
        token = _require_mode_token(mode)
        if token.startswith(DOMAIN_MODE_PREFIX):
            name = token[len(DOMAIN_MODE_PREFIX):]
            selected = tuple(spec for spec in selected if spec.domain == name)
        else:
            selected = tuple(spec for spec in selected if token in spec.modes)
    if domain is not None:
        name = _require_domain_token(domain)
        selected = tuple(spec for spec in selected if spec.domain == name)
    return selected


def _require_mode_token(mode: str) -> str:
    if not isinstance(mode, str) or not mode.strip():
        raise RegistryError(
            f"selection mode must be a non-empty string, got {mode!r}")
    if mode.startswith(DOMAIN_MODE_PREFIX):
        name = mode[len(DOMAIN_MODE_PREFIX):]
        if name not in _DECLARED_DOMAINS:
            raise RegistryError(
                f"selection mode {mode!r} names an undeclared domain "
                f"{name!r} — declared domains: {', '.join(_DECLARED_DOMAINS)}")
        return mode
    if mode not in CONTRACT_MODE_VOCABULARY:
        raise RegistryError(
            f"selection mode {mode!r} is not a contract mode "
            f"({', '.join(CONTRACT_MODE_VOCABULARY)}, or "
            f"'{DOMAIN_MODE_PREFIX}<domain>')")
    return mode


def _require_domain_token(domain: str) -> str:
    if not isinstance(domain, str) or not domain.strip():
        raise RegistryError(
            f"selection domain must be a non-empty string, got {domain!r}")
    if domain not in _DECLARED_DOMAINS:
        raise RegistryError(
            f"selection domain {domain!r} is not declared — declared "
            f"domains: {', '.join(_DECLARED_DOMAINS)}")
    return domain


# ── L6 composition root prototype (per-command assembly) ────────────────────


@dataclass(frozen=True)
class Assembly:
    """One resolved command: the spec, its handler, and an optional subset.

    ``checks`` is empty unless a selection token was passed, because no
    command → check binding is declared anywhere yet (inventing one would be
    fabrication); the mode / domain selector is the honest seam available.
    """

    key: CommandKey
    command: CommandSpec = field(compare=False)
    handler: Callable = field(compare=False)
    checks: Tuple[CheckSpec, ...] = field(default=(), compare=False)


def assemble(key: CommandKey, mode: Optional[str] = None,
             domain: Optional[str] = None) -> Assembly:
    """Resolve one command's handler (and optional check subset) on demand.

    The L6 组合根雏形: only the selected command's module is imported, so a
    dispatch that lives outside the monolith never pays for loading it (§9.1).
    """
    spec = command_spec(key)
    handler = resolve_loader(spec.handler)
    checks = (select_checks(mode=mode, domain=domain)
              if mode is not None or domain is not None else ())
    return Assembly(key=spec.key, command=spec, handler=handler, checks=checks)


# ── R5 registration integrity ───────────────────────────────────────────────

LIVE_SOURCE = "live-engine"
INJECTED_SOURCE = "injected"
LIVE_PROVIDER = ("contract_matrix.generator.extract_cli_dispatch / "
                 "contract_matrix.generator.extract_check_segments (FEAT-020)")

CLI_KEYS_AXIS = "cli-keys"
SEGMENTS_AXIS = "segments"
"""Axis tokens naming which face an observation actually covers (F-2).

An axis absent from ``RegistrationReport.observed_axes`` was defaulted to the
registry's own declaration, so that half of the comparison is a
self-comparison rather than a measurement — the report has to say so.
"""


@dataclass(frozen=True)
class RegistrationReport:
    """Declared face vs observed face (§4.1 R5, both key and segment axes).

    ``missing_*`` = declared but not observed (registration drift);
    ``extra_*`` = observed but not declared (the declaration is stale).

    ``observed_axes`` names the faces that were actually *observed* (F-2). A
    face missing from it was defaulted to the registry's own declaration, so
    ``ok`` can be green with a face that was never measured; :meth:`lines`
    labels that axis ``unobserved`` instead of presenting it as a measurement.
    """

    source: str
    declared_keys: Tuple[str, ...]
    observed_keys: Tuple[str, ...]
    missing_keys: Tuple[str, ...]
    extra_keys: Tuple[str, ...]
    declared_segments: Tuple[str, ...]
    observed_segments: Tuple[str, ...]
    missing_segments: Tuple[str, ...]
    extra_segments: Tuple[str, ...]
    observed_axes: Tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        """Both axes agree — read :attr:`unobserved_axes` for their coverage."""
        return not (self.missing_keys or self.extra_keys
                    or self.missing_segments or self.extra_segments)

    @property
    def unobserved_axes(self) -> Tuple[str, ...]:
        """Declared axes whose face was defaulted, not measured (F-2).

        Computed rather than stored, so a report built without axis
        information never claims a measurement it cannot back.
        """
        return tuple(axis for axis in (CLI_KEYS_AXIS, SEGMENTS_AXIS)
                     if axis not in self.observed_axes)

    def lines(self) -> Tuple[str, ...]:
        """Human-readable verdict lines (never a silent pass)."""
        out = [f"R5 registration integrity [{self.source}]: "
               f"{'PASS' if self.ok else 'FAIL'}"]
        out.append(f"  cli keys: registry={len(self.declared_keys)} "
                   f"observed={len(self.observed_keys)} "
                   f"missing={list(self.missing_keys)} "
                   f"extra={list(self.extra_keys)}"
                   f"{self._unobserved_note(CLI_KEYS_AXIS)}")
        out.append(f"  segments: registry={len(self.declared_segments)} "
                   f"observed={len(self.observed_segments)} "
                   f"missing={list(self.missing_segments)} "
                   f"extra={list(self.extra_segments)}"
                   f"{self._unobserved_note(SEGMENTS_AXIS)}")
        if self.missing_keys or self.missing_segments:
            out.append("  [FAIL] declared entries missing from the observed "
                       "face — registration drift")
        if self.extra_keys or self.extra_segments:
            out.append("  [FAIL] observed entries missing from the registry — "
                       "the declaration is stale")
        return tuple(out)

    def _unobserved_note(self, axis: str) -> str:
        """A defaulted face is labelled as such — never read as measured."""
        if axis in self.observed_axes:
            return ""
        return (f"  [unobserved] {axis}: face defaulted to the registry's own "
                f"declaration — a self-comparison, not a measurement")


def _live_faces() -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """Observe the live engine faces through FEAT-020's own extractors.

    The import is deliberately deferred: importing the extractor package
    pulls the engine, which must never happen at registry load (§9.1).
    """
    try:
        from contract_matrix import generator as extractors
    except Exception as exc:  # noqa: BLE001 — re-raised with full context
        raise RegistryError(
            f"live face provider {LIVE_PROVIDER} is unavailable: "
            f"{type(exc).__name__}: {exc} — pass observed faces explicitly") \
            from exc
    dispatch = extractors.extract_cli_dispatch()
    segments = extractors.extract_check_segments()
    return tuple(dispatch["keys"]), tuple(segments["ids"])


def _diff(expected, actual) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    return (tuple(sorted(set(expected) - set(actual))),
            tuple(sorted(set(actual) - set(expected))))


def verify_registration(
    observed_cli_keys: Optional[Tuple[str, ...]] = None,
    observed_segment_ids: Optional[Tuple[str, ...]] = None,
    source: Optional[str] = None,
) -> RegistrationReport:
    """R5: the declared faces must equal the observed faces.

    With no arguments the live engine is observed through the FEAT-020
    extractors; passing either face injects an observation (the frozen
    snapshot, or a synthetic negative-control projection) and the other face
    defaults to the registry's own declaration so a single-axis comparison
    stays meaningful — that defaulted axis is *labelled* unobserved in the
    report (:attr:`RegistrationReport.observed_axes`), never presented as a
    measurement.

    ``source`` is provenance, so it can only agree with the branch actually
    taken, never assert over it (F-1): the live branch reports
    :data:`LIVE_SOURCE` and refuses any other label, and an injected
    observation may not claim :data:`LIVE_SOURCE` (it defaults to
    :data:`INJECTED_SOURCE`, or keeps a caller-supplied fixture label such as
    ``frozen-snapshot``).
    """
    if observed_cli_keys is None and observed_segment_ids is None:
        if source is not None and source != LIVE_SOURCE:
            raise RegistryError(
                f"source {source!r} contradicts the face actually observed: "
                f"with no injected face the live engine is observed, so the "
                f"only honest provenance is {LIVE_SOURCE!r} — provenance is "
                f"derived from the observation, never asserted")
        observed_axes = (CLI_KEYS_AXIS, SEGMENTS_AXIS)
        observed_cli_keys, observed_segment_ids = _live_faces()
        source = LIVE_SOURCE
    else:
        if source == LIVE_SOURCE:
            raise RegistryError(
                f"source {LIVE_SOURCE!r} contradicts the face actually "
                f"observed: injected faces are not the live engine — pass "
                f"{INJECTED_SOURCE!r} or a fixture-specific label")
        observed_axes = tuple(
            axis for axis, face in ((CLI_KEYS_AXIS, observed_cli_keys),
                                    (SEGMENTS_AXIS, observed_segment_ids))
            if face is not None)
        if observed_cli_keys is None:
            observed_cli_keys = _COMMAND_KEYS
        if observed_segment_ids is None:
            observed_segment_ids = _SEGMENTS
        source = source or INJECTED_SOURCE
    missing_keys, extra_keys = _diff(_COMMAND_KEYS, observed_cli_keys)
    missing_segments, extra_segments = _diff(_SEGMENTS, observed_segment_ids)
    return RegistrationReport(
        source=source,
        declared_keys=_COMMAND_KEYS,
        observed_keys=tuple(observed_cli_keys),
        missing_keys=missing_keys,
        extra_keys=extra_keys,
        declared_segments=_SEGMENTS,
        observed_segments=tuple(observed_segment_ids),
        missing_segments=missing_segments,
        extra_segments=extra_segments,
        observed_axes=observed_axes,
    )
