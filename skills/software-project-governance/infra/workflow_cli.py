"""Build the governance CLI argument schema in public help order."""

import argparse
import sys

from resolve_entry import extract_project_root_arg as _extract_project_root_arg

import workflow_cli_checks
import workflow_cli_operations

from contracts import DETERMINISTIC_SCAFFOLD_TYPES, QUALITY_BUDGET_DIMENSIONS


def build_runtime_parser(parser_argv=()):
    """Build the production parser using the current root and the supported command choices."""
    import workflow_project_roots as paths
    import workflow_runtime_bindings as runtime
    import release_check_bindings as release

    return build_cli_parser(
        parser_argv, root=paths.ROOT, quality_dimensions=QUALITY_BUDGET_DIMENSIONS,
        runtime_platforms=runtime.AGENT_RUNTIME_E2E_PLATFORMS,
        scaffold_types=DETERMINISTIC_SCAFFOLD_TYPES, replay_hint=release._tagged_release_replay_hint)


def build_cli_parser(parser_argv, *, root, quality_dimensions, runtime_platforms,
                     scaffold_types, replay_hint):
    parser = argparse.ArgumentParser(
        prog="verify_workflow",
        description="Software Project Governance CLI",
    )
    if parser_argv[:1] == ["check-official-submission-ecosystem"]:
        parser.error(replay_hint("0.46.0"))
    parser.add_argument(
        "--project-root",
        help=(
            "Host project root whose .governance facts should be read. "
            "May also be placed after the subcommand."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    register_navigation(subparsers)
    register_governance(subparsers, quality_dimensions)
    register_release(subparsers)
    register_host_tools(subparsers, root, runtime_platforms)
    workflow_cli_checks.register_governance_checks(subparsers)
    workflow_cli_checks.register_adapter_checks(subparsers)
    workflow_cli_checks.register_runtime_checks(subparsers)
    workflow_cli_checks.register_architecture_and_loops(subparsers, parser_argv)
    workflow_cli_checks.register_delivery_checks(subparsers, scaffold_types)
    workflow_cli_operations.register_task_review(subparsers)
    workflow_cli_operations.register_change_requests(subparsers)
    workflow_cli_operations.register_governance_tools(subparsers)
    workflow_cli_operations.register_write_guard(subparsers)
    workflow_cli_operations.register_ledger_writers(subparsers)
    workflow_cli_operations.register_authority_and_isolation(subparsers)
    return parser, subparsers


def register_navigation(subparsers):
    # verify (default, backward compatible)
    subparsers.add_parser("verify", help="Verify workflow assets exist and contain required snippets")

    # status
    status_p = subparsers.add_parser("status", help="Show project status overview")
    status_p.add_argument("--json", action="store_true",
                          help="Emit machine-readable JSON (FIX-270 status fast path)")

    # governance-context (FIX-112)
    gctx_p = subparsers.add_parser(
        "governance-context",
        help="Discover unfinished user work from governance facts and print a resume handoff",
    )
    gctx_p.add_argument(
        "--fixture",
        help="Optional project root/fixture to inspect instead of the current repository",
    )
    gctx_p.add_argument("--fail-on-issues", action="store_true",
                        help="Exit with non-zero code if the context contract is invalid")

    # capability-context (FIX-115)
    capctx_p = subparsers.add_parser(
        "capability-context",
        help="Print fact-backed host capability context and selection trace",
    )
    capctx_p.add_argument(
        "--fixture",
        help="Optional project root/fixture to inspect instead of the current repository",
    )
    capctx_p.add_argument("--fail-on-issues", action="store_true",
                          help="Exit with non-zero code if the capability context contract is invalid")

    # gate <id>
    gate_p = subparsers.add_parser("gate", help="Show details for a specific Gate")
    gate_p.add_argument("--unit")
    gate_p.add_argument("gate_id", help="Gate ID (e.g. G3, 3, g5)")

    # gate-check <id> (auto-judge)
    gc_p = subparsers.add_parser("gate-check", help="Auto-judge a Gate's check items (B-level automation)")
    gc_p.add_argument("gate_id", help="Gate ID (e.g. G3, 3, g5)")
    gc_p.add_argument("--review", help="Scoped review record id")
    gc_p.add_argument("--unit", default=None,
                      help="Flow-unit id — route the rendered verdict to the "
                           "loop engine (Wiring B, FIX-236.2)")
    gc_p.add_argument("--fail-on-blocked", action="store_true",
                      help="Exit with non-zero code if gate is blocked")

    # gates (list all)
    subparsers.add_parser("gates", help="Show the current gate per work unit").add_argument("--unit")

    # stage <name>
    stage_p = subparsers.add_parser("stage", help="Show workflow SKILL.md for a stage")
    stage_p.add_argument("stage_name", help="Stage name (e.g. initiation, research, development)")

    # stages (list all)
    subparsers.add_parser("stages", help="List all available stages")


def register_governance(subparsers, quality_dimensions):
    # check-governance
    check_p = subparsers.add_parser("check-governance", help="Run governance health checks")
    check_p.add_argument("--fail-on-issues", action="store_true",
                         help="Exit with non-zero code if issues found")
    check_p.add_argument("--summary-only", action="store_true",
                         help="Print only the governance health summary + first "
                              "FAIL/WARN + top-5 issue details + guidance "
                              "(REQ-145.7 / FIX-278 G1)")
    check_p.add_argument("--level", dest="summary_level", default="standard",
                         choices=("lightweight", "standard", "strict"),
                         help="Detail level for --summary-only (REQ-145.7 / FIX-278 G1)")
    check_p.add_argument("--product-gates", action="store_true",
                         help="Run plugin product self-checks in host mode "
                              "(Check 28o-28r/11/12/28b etc., FIX-270 — "
                              "skipped by default when host/plugin roots diverge)")
    check_p.add_argument("--quick", action="store_true",
                         help="Quick scan (FX-195 Slice-2): run only the FEAT-025 "
                              "registry's quick face; every not-quick segment is "
                              "disclosed as NOT_RUN(<reason>) and the four-state "
                              "counts are printed in the summary line")
    check_p.add_argument("--shadow", action="store_true",
                         help="S-A/S-B shadow channel (FX-195 §4.1): run quick + full "
                              "in one invocation and compare per-segment verdicts — "
                              "any mismatch is BLOCKING")
    check_p.add_argument("--scope", dest="scope", default="full",
                         choices=("quick", "full"),
                         help="Execution scope (FEAT-084/DEC-303 form B): 'quick' "
                              "runs the registry quick face with the four-state "
                              "summary; 'full' (default) keeps full-engine output "
                              "byte-identical — gates/census stay full")

    # execution-packet
    xp_p = subparsers.add_parser(
        "execution-packet",
        help="Prepare a selected handoff, or refresh previously selected packets",
    )
    xp_p.add_argument("--write", action="store_true",
                      help="Write .governance/execution-packets.json")
    xp_p.add_argument("--task", action="append",
                      help="Limit packet generation to a task id; may be repeated")
    xp_p.add_argument("--contract", action="append", choices=("product_success_contract", "vertical_slice", "interruption_policy"),
                      help="Include a contract specifically required by the receiving party")
    xp_p.add_argument("--quality-dimension", action="append", choices=quality_dimensions,
                      help="Include the specified contractual quality threshold")
    xp_p.add_argument("--budget", type=int, default=None,
                      help="Advisory step budget (FEAT-092): stamp "
                           "budget.max_steps (positive integer) on the "
                           "generated packets; omitted by default")


def register_release(subparsers):
    # check-manifest-consistency
    cmc_p = subparsers.add_parser("check-manifest-consistency",
                                   help="Compare manifest.json canonical set against actual filesystem")
    cmc_p.add_argument("--fail-on-issues", action="store_true",
                        help="Exit with non-zero code if mismatch detected")

    # check-plugin-freshness
    subparsers.add_parser("check-plugin-freshness", help="Check if installed plugin is up to date with source")

    # check-exploration-channels
    cec_p = subparsers.add_parser(
        "check-exploration-channels",
        help="Check exploration_channels evidence forms (FEAT-088 F-A3): dated "
             "anchors on native declarations of enrolled adapters + read-only "
             "anchor-document probes (host-tool liveness is NOT probed)")
    cec_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if evidence-form issues are found")

    # check-agent-adapters
    caa_p = subparsers.add_parser("check-agent-adapters",
                                  help="Check mainstream code agent adapter contracts")
    caa_p.add_argument("--runtime", action="store_true",
                       help="Also execute local runtime version commands for supported adapters")

    # check-release
    cr_p = subparsers.add_parser("check-release",
                                 help="Run release readiness checks used by stage-release")
    cr_p.add_argument("--json", action="store_true", help="Output the scoped release checks as JSON")
    cr_p.add_argument("--version",
                      help="Release version to validate (semver X.Y.Z)")
    cr_p.add_argument("--require-changelog", action="store_true",
                      help="Require project/CHANGELOG.md to contain ## [version]")
    cr_p.add_argument("--runtime-adapters", action="store_true",
                      help="Also execute local runtime version commands for supported adapters")
    cr_p.add_argument("--skip-execution-gates", action="store_true",
                      help="Diagnostic only: skip verify/check-governance/e2e/unit-test execution gates")
    cr_p.add_argument("--require-delivery-evidence", action="store_true",
                      help="Require the local delivery contract and accepted artifact evidence, "
                           "including in released-mode verification")
    cr_p.add_argument("--unit", help="Release work unit bound to the requested version")
    cr_p.add_argument("--lineage-mode", choices=("candidate", "released"), default=None,
                      help="candidate skips pre-tag validation; released requires local and remote tag lineage. "
                           "Default (unset): candidate — except that checks against an ALREADY-PUBLISHED "
                           "version run the embedded gate-sequence interlock in released mode (BR-4 / DEC-153)")
    cr_p.add_argument("--release-commit",
                      help="Expected release commit (required when --lineage-mode released)")
    cr_p.add_argument("--lineage-remote", default="origin",
                      help="Git remote whose release tag must match (default: origin)")

    ledger_p = subparsers.add_parser(
        "release-ledger",
        help="Validate declarative release manifests and live Git lineage facts",
    )
    ledger_p.add_argument("--version", help="Validate only one release manifest")
    ledger_p.add_argument("--remote", default="origin", help="Configured Git remote name")
    ledger_p.add_argument("--no-remote", action="store_true", help="Skip remote tag verification")
    ledger_p.add_argument("--timeout", type=int, default=15, help="Git command timeout in seconds")

    projection_p = subparsers.add_parser(
        "release-projection",
        help="Check declared projections, or write all projections atomically",
    )
    projection_p.add_argument("--write", action="store_true", help="Atomically write projections; default is check-only")
    projection_p.add_argument("--config", help="Optional projection config path")
    subparsers.add_parser("quality-tools", help="Probe optional ruff/mypy tools as PASS/NOT_RUN/FAIL")

    # e2e-check
    subparsers.add_parser("e2e-check", help="Run E2E governance verification against e2e-test-project")


def register_host_tools(subparsers, root, runtime_platforms):
    # external-project-validation (FIX-131)
    epv_p = subparsers.add_parser(
        "external-project-validation",
        help="Run a temporary external-project validation workspace without mutating the target",
    )
    epv_p.add_argument("--target", required=True,
                       help="External project directory to inspect as the validation source target")
    epv_p.add_argument("--workspace-parent",
                       help="Optional parent directory for the temporary validation workspace")
    epv_p.add_argument("--keep-workspace", action="store_true",
                       help="Keep the temporary validation workspace for inspection")
    epv_p.add_argument("--timeout", type=int, default=120,
                       help="Per-command timeout in seconds")
    epv_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if any validation command fails")

    # first-run-demo (FIX-103)
    frd_p = subparsers.add_parser(
        "first-run-demo",
        help="Run the local first happy path demo harness",
    )
    frd_p.add_argument(
        "--assert-snapshot",
        action="store_true",
        help="Assert required Delivery Trust Snapshot fields and no-overclaim markers",
    )

    # web-console (FIX-148)
    wc_p = subparsers.add_parser(
        "web-console",
        help="Discover or launch the optional local Web console from the CLI/client path",
    )
    wc_p.add_argument("--status", action="store_true",
                      help="Print Web console availability and manual start command without starting it")
    wc_p.add_argument("--summary-link", action="store_true",
                      help="Print a no-side-effect Web console footer for task/session summaries")
    wc_p.add_argument("--governance-entry", action="store_true",
                      help="Start or reuse the local Web console for a manual /governance invocation")
    wc_p.add_argument("--start", action="store_true",
                      help="Start the local Web console and print its URL")
    wc_p.add_argument("--install", action="store_true",
                      help="Run npm install first when web/node_modules is missing "
                           "(SPG_WEB_INSTALL_TIMEOUT, default 120s)")
    wc_p.add_argument("--foreground", action="store_true",
                      help="Run the Vite dev server in the foreground instead of backgrounding it")
    wc_p.add_argument("--open", action="store_true",
                      help="Open the Web console URL in the default browser after start or reuse")
    wc_p.add_argument("--host", default="127.0.0.1",
                      help="Host passed to Vite (default: 127.0.0.1)")
    wc_p.add_argument("--port", type=int, default=5173,
                      help="Port passed to Vite (default: 5173)")
    wc_p.add_argument("--fail-on-issues", action="store_true",
                      help="Exit with non-zero code when the console cannot be started")

    # resolve-entry (FIX-238.3)
    re_p = subparsers.add_parser(
        "resolve-entry",
        help="Thin bounded resolve_entry invocation with classified fail-closed diagnostics (FIX-238.3)",
    )
    re_p.add_argument("--project-root", default=None,
                      help="Explicit host project root forwarded to resolve_entry.py")

    # agent-runtime-e2e
    are_p = subparsers.add_parser(
        "agent-runtime-e2e",
        help="Run real agent runtime E2E harness against e2e-test-project",
    )
    are_p.add_argument(
        "--target",
        default=str(root / "project/e2e-test-project"),
        help="Target project cwd for real agent runtime E2E commands",
    )
    are_p.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Per-agent command timeout in seconds",
    )
    are_p.add_argument(
        "--agent",
        action="append",
        choices=runtime_platforms,
        help="Limit to one agent; may be repeated. Defaults to all mainstream agents.",
    )

    # gemini-auth-preflight
    subparsers.add_parser(
        "gemini-auth-preflight",
        help="Check Gemini CLI PATH/version/auth sources without printing secrets",
    )

    # opencode-provider-preflight
    subparsers.add_parser(
        "opencode-provider-preflight",
        help="Check opencode CLI PATH/version/provider model without printing secrets",
    )


def main(argv=None):
    from workflow_project_roots import _apply_project_root_override
    import workflow_project_roots as paths

    raw_argv = list(sys.argv[1:] if argv is None else argv)
    try:
        explicit_project_root, parser_argv = _extract_project_root_arg(raw_argv)
    except ValueError as exc:
        print(f"verify_workflow: error: {exc}", file=sys.stderr)
        sys.exit(2)

    parser, _ = build_runtime_parser(parser_argv)
    args = parser.parse_args(parser_argv)
    if args.project_root and explicit_project_root is None:
        explicit_project_root = args.project_root
    args.project_root = explicit_project_root
    if explicit_project_root is not None:
        _apply_project_root_override(explicit_project_root)
        if args.command == "governance-bootstrap":
            args._validated_host_root = paths.HOST_PROJECT_ROOT

    import registry
    return registry.load_handler(args.command or "verify", parsed_args=True)(args)
