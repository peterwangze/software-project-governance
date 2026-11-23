"""Register the governance, adapter, runtime, architecture and delivery checks."""


def register_governance_checks(subparsers):
    # check-cross-references (SYSGAP-008)
    xr_p = subparsers.add_parser("check-cross-references",
                                 help="Scan .md/.py files for dangling, deprecated, and circular path references")
    xr_p.add_argument("--fail-on-issues", action="store_true",
                      help="Exit with non-zero code if issues found")

    subparsers.add_parser(
        "check-loop-role-skills",
        help="Validate the seven review SKILL loop-role documentation contracts",
    )

    # check-sequential-ids (SYSGAP-009)
    si_p = subparsers.add_parser("check-sequential-ids",
                                 help="Verify ID continuity and cross-reference integrity in governance records")
    si_p.add_argument("--fail-on-issues", action="store_true",
                      help="Exit with non-zero code if issues found")

    # check-structural-validity (SYSGAP-010)
    sv_p = subparsers.add_parser("check-structural-validity",
                                 help="Validate structural integrity of governance files")
    sv_p.add_argument("--fail-on-issues", action="store_true",
                      help="Exit with non-zero code if issues found")

    # check-commit-scope (SYSGAP-012)
    cs_p = subparsers.add_parser("check-commit-scope",
                                 help="Verify commit scope discipline (task ID uniqueness, bulk commits, side-effect keywords)")
    cs_p.add_argument("--limit", type=int, default=20,
                      help="Number of recent commits to check (default: 20)")

    # check-goal-alignment (SYSGAP-023)
    cga_p = subparsers.add_parser("check-goal-alignment",
                                  help="Verify goal alignment in impact analysis entries")
    cga_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if issues found")

    # check-user-impact (SYSGAP-024)
    cui_p = subparsers.add_parser("check-user-impact",
                                  help="Verify user impact analysis in impact analysis entries")
    cui_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if issues found")

    # check-agent-team (SYSGAP-037)
    cat_p = subparsers.add_parser("check-agent-team",
                                  help="Run Agent Team integrity checks (Check 19 + Check 20)")
    cat_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if issues found")

    # check-review-debt (SYSGAP-042)
    crd_p = subparsers.add_parser("check-review-debt",
                                  help="Run review debt check (Check 21)")
    crd_p.add_argument("--fail-on-issues", action="store_true",
                      help="Exit with non-zero code if review debt found")

    # check-version-consistency (FIX-052)
    subparsers.add_parser("check-version-consistency",
                          help="Check version consistency across all declaration files")

    # check-projection-sync (FIX-086)
    cps_p = subparsers.add_parser(
        "check-projection-sync",
        help="Check source-to-target fixture projection and plugin version sync",
    )
    cps_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if projection drift is found")

    # check-entry-bootstrap-sync (FEAT-037) — cmd lives in checks/projection.py
    cebs_p = subparsers.add_parser("check-entry-bootstrap-sync", help="Check AGENTS/CLAUDE bootstrap sections against the canonical templates (FEAT-037)")
    cebs_p.add_argument("--fail-on-issues", action="store_true", help="Exit with non-zero code if entry bootstrap drift is found")


def register_adapter_checks(subparsers):
    from checks import injection_budget

    # check-injection-contract (FIX-253 / REQ-112)
    cic_p = subparsers.add_parser(
        "check-injection-contract",
        help="Check injection-surface anchor presence (persona/SKILL/AGENTS contract)",
    )
    cic_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if injection-contract anchors are missing")

    # check-injection-budget (FEAT-039 / AUDIT-154 slice A-8): args + handler
    # live in checks/injection_budget.py — the engine only wires dispatch
    # (bootstrap_aggregate pattern; ArchGuard R4 print budget untouched).
    cib_p = subparsers.add_parser(
        "check-injection-budget",
        help="Price the actually-injected surface set (multi-file sum) against "
             "a token budget (FEAT-039 / AUDIT-154 A-8)",
    )
    injection_budget.add_arguments(cib_p)

    # check-dsh-preset-smoke (FEAT-015 / RISK-049 ②)
    csmk_p = subparsers.add_parser(
        "check-dsh-preset-smoke",
        help="Run the isolated DSH preset-session smoke gate — skill catalog "
             "+ /governance gesture resolution under a redirected DSH_HOME "
             "(FEAT-015 / RISK-049 ②)",
    )
    csmk_p.add_argument("--fail-on-issues", action="store_true",
                        help="Exit with non-zero code if the isolated smoke fails")

    # check-dsh-preset-compat (DSH preset composition ↔ installed schema guard)
    cdpc_p = subparsers.add_parser(
        "check-dsh-preset-compat",
        help="Validate every preset composition row against the INSTALLED "
             "dsh's own Config schemas (loader YAML dialect + loader evaluate "
             "+ cordis resolveConfig); NOT_RUN when no node / no dsh install",
    )
    profiles = cdpc_p.add_mutually_exclusive_group()
    profiles.add_argument("--isolated-home", metavar="DIR",
                          help="use the temporary profile directory assigned to this run")
    profiles.add_argument("--use-host-profile", action="store_true",
                          help="deliberately read the configured host profile")
    cdpc_p.add_argument("--fail-on-issues", action="store_true",
                        help="Exit with non-zero code if a row is rejected by the installed schemas")

    # check-dsh-boundary (FEAT-031 / 0.81.0 slice V8 — Check 28w)
    cdbs_p = subparsers.add_parser(
        "check-dsh-boundary",
        help="Check the dsh dependency-boundary contract (K-1…K-13): contract "
             "shape, template/token/hook/patch agreement, version evidence + "
             "TTL, coverage claims, dispositions, declarations, allowlist "
             "ratchet, single verdict, rehearsal baseline",
    )
    cdbs_p.add_argument("--fail-on-issues", action="store_true",
                        help="Exit with non-zero code if a criterion FAILs")
    cdbs_p.add_argument("--json", action="store_true",
                        help="Emit the criterion report as JSON")

    # dsh-doctor (FEAT-031 / 0.81.0 slice V8 — the single diagnostic entry)
    dd_p = subparsers.add_parser(
        "dsh-doctor",
        help="Single staged diagnostic entry for the dsh boundary (S0–S7): "
             "per-stage verdict + evidence + remediation, exit codes 0/1/2",
    )
    from dsh_doctor_cli import add_cli_arguments as add_doctor_arguments
    add_doctor_arguments(dd_p, engine_entry=True)


def register_runtime_checks(subparsers):
    # check-hot-fact-source (FIX-087)
    chfs_p = subparsers.add_parser(
        "check-hot-fact-source",
        help="Check hot plan-tracker fact-source consistency across active release sections",
    )
    chfs_p.add_argument("--fail-on-issues", action="store_true",
                        help="Exit with non-zero code if hot fact-source drift is found")

    # check-runtime-readiness-matrix (FIX-106)
    crrm_p = subparsers.add_parser(
        "check-runtime-readiness-matrix",
        help="Check public runtime/readiness matrix against adapter facts",
    )
    crrm_p.add_argument("--fail-on-issues", action="store_true",
                        help="Exit with non-zero code if matrix facts drift from adapter manifests")

    # check-first-session-measurement (FIX-107)
    cfsm_p = subparsers.add_parser(
        "check-first-session-measurement",
        help="Check first-session measurement evidence against local-demo and external-pilot boundaries",
    )
    cfsm_p.add_argument("--fail-on-issues", action="store_true",
                        help="Exit with non-zero code if measurement evidence overclaims external pilot status")

    # check-governance-packs (FIX-108)
    cgp_p = subparsers.add_parser(
        "check-governance-packs",
        help="Check canonical governance pack registry fields, references, and no-overclaim boundary",
    )
    cgp_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if pack registry is incomplete or overclaims")

    # check-capability-registry (FIX-116)
    ccr_p = subparsers.add_parser(
        "check-capability-registry",
        help="Check canonical external capability registry fields, sources, validation, and no-overclaim boundary",
    )
    ccr_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if capability registry is incomplete or overclaims")

    # check-lifecycle-registry (FIX-135)
    clr_p = subparsers.add_parser(
        "check-lifecycle-registry",
        help="Validate the active work-unit routes, local gates and evidence catalog",
    )
    clr_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if lifecycle registry is incomplete or activates runtime behavior")

    # check-flow-unit-runtime (FIX-136)
    cfur_p = subparsers.add_parser(
        "check-flow-unit-runtime",
        help="Check optional flow-unit runtime hot state without activating declarative gates",
    )
    cfur_p.add_argument(
        "--fixture",
        help="Optional project root/fixture to inspect instead of the current repository",
    )
    cfur_p.add_argument("--fail-on-issues", action="store_true",
                        help="Exit with non-zero code if flow-unit runtime hot state is invalid")



    # check-host-capability-context (FIX-117)
    chc_p = subparsers.add_parser(
        "check-host-capability-context",
        help="Check restricted-environment capability selection benchmark facts and no-overclaim boundary",
    )
    chc_p.add_argument(
        "--fixture",
        help="Optional project root/fixture to inspect instead of the current repository",
    )
    chc_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if restricted host capability context is incomplete or overclaims")

    # check-mainstream-agent-loading (FIX-122)
    cmal_p = subparsers.add_parser(
        "check-mainstream-agent-loading",
        help="Check 0.47.0 mainstream agent loading guidance and no-overclaim boundary",
    )
    cmal_p.add_argument("--fail-on-issues", action="store_true",
                        help="Exit with non-zero code if mainstream loading docs are incomplete or overclaim")

    # check-readme-pack-guidance (FIX-109)
    crpg_p = subparsers.add_parser(
        "check-readme-pack-guidance",
        help="Check README first-run profile-to-pack guidance and no-overclaim boundary",
    )
    crpg_p.add_argument("--fail-on-issues", action="store_true",
                        help="Exit with non-zero code if README pack guidance is incomplete or overclaims")


def register_architecture_and_loops(subparsers, parser_argv):
    # check-architecture-health (REQ-101 / FIX-152 / ArchGuard)
    cah_p = subparsers.add_parser(
        "check-architecture-health",
        help="ArchGuard: module/function/constant-size + duplicate-constant guard (advisory in 0.58.0)",
    )
    cah_p.add_argument("--scope", choices=("plugin", "host"), default="plugin",
                       help="Scan the installed plugin (default), or host .py/.js/.ts source under --project-root or cwd")
    cah_p.add_argument("--policy", metavar="JSON",
                       help="Host scope only: explicitly override installed thresholds, exclusions or gating; relative paths start at the host root")
    cah_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit non-zero only if gate_integration.fatal_on_error is true and ERRORs found")

    # archguard-ratchet (FEAT-019 / AUDIT-150 §4 — fatal ratchet gate R1~R7
    # vs core/architecture-baseline.json; violations exit non-zero by design)
    agr_p = subparsers.add_parser(
        "archguard-ratchet",
        help="ArchGuard ratchet R1~R7 vs core/architecture-baseline.json "
             "(fatal: any violation exits non-zero)",
    )
    agr_p.add_argument("--regen", action="store_true",
                       help="Explicitly regenerate the baseline (anchored at "
                            "current measurements; only-down from there)")
    agr_p.add_argument("--baseline", default=None,
                       help="Baseline JSON path (default: "
                            "core/architecture-baseline.json)")

    # check-loop-health (FX-192 / ADR §9.5 — advisory-only, NOT a Check 28 sub-item)
    clh_p = subparsers.add_parser(
        "check-loop-health",
        help="Check pause-point declarations and report whether unit observations are available",
    )
    clh_p.add_argument("--target", default=None,
                       help="Host project root (defaults to verify_workflow ROOT)")
    clh_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit non-zero if any blocking (FAIL) findings are present")



    loop_p = subparsers.add_parser("loop", help="Work in nested goal and evidence-bound loops")
    if "loop" in parser_argv:
        from loop_workflow import add_arguments
        add_arguments(loop_p)

    # loop-rollup (FX-193 — per-flow-unit loop_state rollup; RISK-037 criterion 2)
    lr_p = subparsers.add_parser(
        "loop-rollup",
        help="Per-flow-unit loop_state rollup (replaces single 当前阶段; 0.65.0)",
    )
    lr_p.add_argument("--target", default=None,
                      help="Host project root (defaults to verify_workflow ROOT)")

    # Unit observations from the host event log.
    lt_p = subparsers.add_parser(
        "loop-telemetry",
        help="Show unit completions, rework and observed waits from loop-event-log.jsonl",
    )
    lt_p.add_argument("--target", default=None,
                      help="Host project root (defaults to HOST_PROJECT_ROOT; RISK-040)")
    lt_p.add_argument("--window", choices=("all", "7d", "30d", "90d"),
                      default="all",
                      help="Time window relative to the latest event timestamp (default all)")
    lt_p.add_argument("--json", action="store_true",
                      help="Emit machine-readable JSON instead of human-readable text")


def register_delivery_checks(subparsers, scaffold_types):
    # check-duplicate-code (REQ-101 / FIX-152 / ArchGuard)
    cdc_p = subparsers.add_parser(
        "check-duplicate-code",
        help="ArchGuard: source/projection duplicate-code guard (advisory in 0.58.0)",
    )
    cdc_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit non-zero only if gate_integration.fatal_on_error is true and ERRORs found")

    # check-technical-debt (REQ-101 / FIX-152 / ArchGuard)
    ctd_p = subparsers.add_parser(
        "check-technical-debt",
        help="ArchGuard: root residue / release docs / hooks-drift / ledger cross-validation (advisory)",
    )
    ctd_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit non-zero only if gate_integration.fatal_on_error is true and ERRORs found")

    # check-complexity (REQ-101 / FIX-152 / ArchGuard)
    ccx_p = subparsers.add_parser(
        "check-complexity",
        help="ArchGuard: complexity guard (line-based proxy in 0.58.0; advisory)",
    )
    ccx_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit non-zero only if gate_integration.fatal_on_error is true and ERRORs found")

    # check-governance-data-size (FIX-160 / ArchGuard)
    gds_p = subparsers.add_parser(
        "check-governance-data-size",
        help="ArchGuard: governance data volume threshold (FIX-160; advisory)",
    )
    gds_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit non-zero only if gate_integration.fatal_on_error is true and ERRORs found")


    # check-governance-pack-status (FIX-111)
    cgps_p = subparsers.add_parser(
        "check-governance-pack-status",
        help="Check status/release pack summary boundaries and no-overclaim wording",
    )
    cgps_p.add_argument("--fail-on-issues", action="store_true",
                        help="Exit with non-zero code if status or release pack boundaries are incomplete")

    # check-product-success-contracts (FIX-088)
    cpsc_p = subparsers.add_parser(
        "check-product-success-contracts",
        help="Check Product Success Contract fields for active P0/P1 execution packets",
    )
    cpsc_p.add_argument("--fail-on-issues", action="store_true",
                        help="Exit with non-zero code if a required contract is missing or incomplete")

    # check-acceptance-contracts (FIX-089)
    cac_p = subparsers.add_parser(
        "check-acceptance-contracts",
        help="Check executable acceptance contracts for active P0/P1 execution packets",
    )
    cac_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if a required acceptance contract is missing or incomplete")

    # check-quality-budget (FIX-090)
    cqb_p = subparsers.add_parser(
        "check-quality-budget",
        help="Check quality budgets for active P0/P1 execution packets",
    )
    cqb_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if a required quality budget is missing or incomplete")

    # check-vertical-slices (FIX-091)
    cvs_p = subparsers.add_parser(
        "check-vertical-slices",
        help="Check vertical slice delivery packets for active P0/P1 execution packets",
    )
    cvs_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if a required vertical slice packet is missing or incomplete")

    # check-deterministic-scaffolds (FIX-092)
    cds_p = subparsers.add_parser(
        "check-deterministic-scaffolds",
        aliases=["check-scaffold-templates"],
        help="Check weak-LLM deterministic scaffold templates and index",
    )
    cds_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if a deterministic scaffold is missing or incomplete")

    # check-interruption-policy (FIX-093)
    cip_p = subparsers.add_parser(
        "check-interruption-policy",
        aliases=["check-user-interruption-policy"],
        help="Check critical-only user interruption policy, examples, and execution packet fields",
    )
    cip_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if interruption policy is missing or incomplete")

    # generate-deterministic-scaffold (FIX-092)
    gds_p = subparsers.add_parser(
        "generate-deterministic-scaffold",
        help="Render a deterministic scaffold template by project type",
    )
    gds_p.add_argument("--type", required=True, choices=scaffold_types,
                       help="Scaffold type to render")
    gds_p.add_argument("--output",
                       help="Optional output file. Omit to print the scaffold to stdout")

    # check-locks (FIX-056 Phase 2)
    subparsers.add_parser("check-locks",
                          help="Check agent-locks.json consistency (FIX-056 Check 26)")

    # check-archive-integrity (SYSGAP-030)
    subparsers.add_parser("check-archive-integrity",
                          help="Check archive integrity (SYSGAP-030 Check 27)")
