"""Discover capability facts and validate ordinary and restricted host scenarios."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SelectionPolicy:
    required_fields: list
    allowed_statuses: set
    degraded_statuses: set
    boundary_tokens: list


@dataclass(frozen=True)
class RestrictedHostPolicy:
    required_fields: list
    allowed_statuses: set
    scenario_fields: list
    scenarios: set
    unavailable_statuses: set
    boundary_tokens: list
    forbidden_claims: list
    blocked_facts: dict


def _capability_context_path(root, relative_path):
    return Path(root) / relative_path


def _capability_file_fact(root, relative_path, label):
    path = _capability_context_path(root, relative_path)
    if path.is_file():
        return True, f"{relative_path.as_posix()}: {label} present"
    return False, f"{relative_path.as_posix()}: {label} missing"


def _capability_text_contains(root, relative_path, token):
    path = _capability_context_path(root, relative_path)
    if not path.is_file():
        return False
    return token in path.read_text(encoding="utf-8")


def _capability_cli_registration_fact(root, relative_path):
    path = _capability_context_path(root, relative_path)
    if not path.is_file():
        return False, f"{relative_path.as_posix()}: `capability-context` CLI registration missing (file not found)"
    from cli_registration import inspect_cli_registration
    try:
        facts = inspect_cli_registration(path, "capability-context", "cmd_capability_context")
    except (OSError, UnicodeError, SyntaxError) as exc:
        return False, f"{relative_path.as_posix()}: `capability-context` CLI registration unreadable ({exc})"
    has_handler, has_parser, has_dispatch = facts["handler"], facts["argparse"], facts["dispatch"]
    registered = has_handler and has_parser and has_dispatch
    detail = (
        f"{relative_path.as_posix()}: `capability-context` CLI registration "
        f"top_level_handler={'yes' if has_handler else 'no'}, "
        f"main={'yes' if facts['main'] else 'no'}, "
        f"main_subparser={'yes' if has_parser else 'no'}, "
        f"main_dispatch={'yes' if has_dispatch else 'no'}"
    )
    return registered, detail


def _capability_host_id(root):
    host_facts = []
    if (root / ".codex-plugin/plugin.json").is_file():
        host_facts.append(".codex-plugin/plugin.json")
    if (root / ".claude-plugin/plugin.json").is_file():
        host_facts.append(".claude-plugin/plugin.json")
    if (root / "AGENTS.md").is_file():
        host_facts.append("AGENTS.md")
    if (root / "skills/software-project-governance/SKILL.md").is_file():
        host_facts.append("software-project-governance skill")
    if not host_facts:
        return "local-fixture", ["no host package metadata found; treating target as local fixture"]
    return "local-governance-repository", [f"host metadata: {', '.join(host_facts)}"]


def _host_capability_source_fact(root, relative_path, present_label, missing_label):
    path = _capability_context_path(root, Path(relative_path))
    if path.is_file():
        return True, f"{relative_path}: {present_label}"
    return False, f"{relative_path}: {missing_label}"


def _host_context_fact_contains(root, relative_path, tokens):
    path = _capability_context_path(root, Path(relative_path))
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8").lower()
    return all(token.lower() in text for token in tokens)


def _host_context_registry_capabilities(root, *, display_path):
    registry_path = _capability_context_path(root, Path("skills/software-project-governance/core/capability-registry.json"))
    if not registry_path.is_file():
        return [], [f"{display_path(registry_path, root)}: capability registry missing"]
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], [f"{display_path(registry_path, root)}: invalid JSON: {exc}"]
    capabilities = registry.get("capabilities", [])
    if not isinstance(capabilities, list):
        return [], [f"{display_path(registry_path, root)}: capabilities is not a list"]
    return [cap for cap in capabilities if isinstance(cap, dict)], [
        f"{display_path(registry_path, root)}: capability registry loaded as catalog facts only"
    ]


def discover_capability_context(root, *, requirements_path, tools_path, check_registry):
    """Build a fact-backed capability selection trace for the current host."""
    host_id, host_facts = _capability_host_id(root)
    verify_rel = Path("skills/software-project-governance/infra/verify_workflow.py")
    req_rel = requirements_path
    tools_rel = tools_path
    packs_rel = Path("skills/software-project-governance/core/governance-packs.json")
    runtime_rel = Path("docs/requirements/runtime-readiness-matrix-0.43.0.md")
    marketplace_rel = Path("docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md")
    future_registry_rel = Path("skills/software-project-governance/core/capability-registry.json")

    verify_exists, verify_fact = _capability_file_fact(root, verify_rel, "local verification script")
    req_exists, req_fact = _capability_file_fact(root, req_rel, "0.45.0 capability contract")
    tools_exists, tools_fact = _capability_file_fact(root, tools_rel, "tool index")
    packs_exists, packs_fact = _capability_file_fact(root, packs_rel, "internal governance pack registry")
    runtime_exists, runtime_fact = _capability_file_fact(root, runtime_rel, "runtime/readiness fact matrix")
    marketplace_exists, marketplace_fact = _capability_file_fact(root, marketplace_rel, "Codex Desktop marketplace-management E2E plan")
    future_registry_exists, future_registry_fact = _capability_file_fact(root, future_registry_rel, "external capability registry")
    command_registered, command_fact = _capability_cli_registration_fact(root, verify_rel)
    tools_registered = _capability_text_contains(root, tools_rel, "TOOL-031")

    source_facts = [
        *host_facts,
        verify_fact,
        req_fact,
        tools_fact,
        packs_fact,
        runtime_fact,
        marketplace_fact,
        future_registry_fact,
    ]
    source_facts.append(command_fact)
    source_facts.append(
        f"{tools_rel.as_posix()}: TOOL-031 {'registered' if tools_registered else 'not found'}"
    )

    available_capabilities = []
    if verify_exists:
        available_capabilities.append({
            "capability_id": "local.capability-context.cli",
            "kind": "script",
            "host_surface": "local shell",
            "scenario": "capability-context",
            "status": "AVAILABLE" if command_registered else "DEGRADED",
            "source_facts": [verify_fact, source_facts[-2]],
            "selection_reason": "read-only diagnostic can emit the required selection trace from local project facts",
            "side_effect_boundary": "read-only local files; no writes, network, package install, browser state, or external API calls",
            "validation_command": "python skills/software-project-governance/infra/verify_workflow.py capability-context --fail-on-issues",
        })
    if packs_exists:
        available_capabilities.append({
            "capability_id": "internal.governance-packs.catalog",
            "kind": "fallback",
            "host_surface": "local repository",
            "scenario": "governance-pack-boundary",
            "status": "DEGRADED",
            "availability_scope": "catalog-only internal governance capability facts; not runtime PASS",
            "source_facts": [packs_fact],
            "selection_reason": "useful as a boundary fact source, but not an external capability selector",
            "side_effect_boundary": "read-only local registry inspection",
            "validation_command": "python skills/software-project-governance/infra/verify_workflow.py check-governance-packs --fail-on-issues",
        })
    if runtime_exists:
        available_capabilities.append({
            "capability_id": "runtime.readiness-matrix.fact-source",
            "kind": "fallback",
            "host_surface": "local repository",
            "scenario": "runtime-readiness-facts",
            "status": "DEGRADED",
            "availability_scope": "runtime status evidence only; not selected capability execution",
            "source_facts": [runtime_fact],
            "selection_reason": "useful for host status facts, but not proof that a tool was executed for this scenario",
            "side_effect_boundary": "read-only public matrix inspection",
            "validation_command": "python skills/software-project-governance/infra/verify_workflow.py check-runtime-readiness-matrix --fail-on-issues",
        })

    registry_issues = check_registry(root) if future_registry_exists else []
    preferred_status = "DEGRADED" if future_registry_exists else "NOT_FOUND"
    registry_reason = (
        "FIX-116 registry exists as a catalog fact source; catalog membership is not runtime PASS"
        if future_registry_exists and not registry_issues
        else (
            "FIX-116 registry exists but validator found issues; cannot use it as a trusted catalog"
            if future_registry_exists
            else "preferred external capability registry is not implemented in FIX-115"
        )
    )
    if future_registry_exists:
        available_capabilities.append({
            "capability_id": "external.capability-registry.catalog",
            "kind": "tool",
            "host_surface": "local repository",
            "scenario": "capability-registry",
            "status": "DEGRADED",
            "availability_scope": "catalog-only external capability facts; not runtime PASS and not proof external capability is available",
            "source_facts": [future_registry_fact],
            "selection_reason": "registry can inform candidate discovery, but selection still requires runtime facts and no-overclaim boundary",
            "side_effect_boundary": "read-only registry inspection; no plugin install, MCP call, browser action, sub-agent spawn, network call, or external execution",
            "validation_command": "python skills/software-project-governance/infra/verify_workflow.py check-capability-registry --fail-on-issues",
        })
    rejected_alternatives = [
        {
            "capability_id": "external.capability-registry",
            "kind": "tool",
            "host_surface": "future 0.45.0 registry",
            "status": preferred_status,
            "source_facts": [future_registry_fact],
            "rejection_reason": registry_reason,
        },
        {
            "capability_id": "host.automatic-best-tool-selection",
            "kind": "host_builtin",
            "host_surface": "unspecified host",
            "status": "NOT_SUPPORTED",
            "source_facts": ["no source fact in this repository proves automatic global best-tool selection"],
            "rejection_reason": "would overclaim beyond the diagnostic selection trace contract",
        },
        {
            "capability_id": "codex-desktop.marketplace-management-e2e",
            "kind": "plugin",
            "host_surface": "Codex Desktop",
            "status": "BLOCKED" if marketplace_exists else "NOT_FOUND",
            "source_facts": [marketplace_fact],
            "rejection_reason": "marketplace management E2E is planned separately and cannot be treated as available capability execution",
        },
    ]

    if verify_exists and command_registered:
        selected = {
            "capability_id": "local.capability-context.cli",
            "kind": "script",
            "host_surface": "local shell",
            "status": "DEGRADED" if preferred_status != "NOT_FOUND" else "DEGRADED",
            "selection_reason": (
                "selected as a read-only fallback; registry presence informs catalog facts but is not runtime PASS"
                if preferred_status != "NOT_FOUND"
                else "selected as a read-only fallback because the preferred external capability registry is unavailable"
            ),
            "source_facts": [verify_fact, source_facts[-2]],
        }
        degradation_status = "DEGRADED"
        degradation_reason = (
            "capability registry exists only as a catalog fact source; using local diagnostic fallback without runtime PASS"
            if preferred_status != "NOT_FOUND"
            else "preferred external capability registry is unavailable; using local diagnostic fallback"
        )
    elif verify_exists:
        selected = {
            "capability_id": "local.verify-workflow.script",
            "kind": "script",
            "host_surface": "local shell",
            "status": "DEGRADED",
            "selection_reason": "`verify_workflow.py` exists but this fixture lacks a registered `capability-context` command",
            "source_facts": [verify_fact, source_facts[-2]],
        }
        degradation_status = "DEGRADED"
        degradation_reason = "local verification script exists, but the preferred command is not registered"
    else:
        selected = {
            "capability_id": "manual.blocked-fallback",
            "kind": "fallback",
            "host_surface": "manual inspection",
            "status": "BLOCKED",
            "selection_reason": "no local capability-context command or verification script was found in the target fixture",
            "source_facts": [verify_fact],
        }
        degradation_status = "BLOCKED"
        degradation_reason = "preferred and fallback diagnostic capabilities are unavailable"

    return {
        "scenario": "capability-context",
        "host_id": host_id,
        "available_capabilities": available_capabilities,
        "selected_capability": selected,
        "source_facts": source_facts,
        "rejected_alternatives": rejected_alternatives,
        "degradation": {
            "status": degradation_status,
            "reason": degradation_reason,
            "fallback": selected["capability_id"],
        },
        "side_effect_boundary": "read-only diagnostic; reads local project files only and performs no writes, commits, network calls, package installs, browser actions, or API calls",
        "validation_command": "python skills/software-project-governance/infra/verify_workflow.py capability-context --fail-on-issues",
        "review_requirement": "FIX-115 product-code closure still requires independent Code Reviewer approval; this command output is not self-review",
        "no_overclaim_boundary": [
            "Do not claim automatic global best-tool selection.",
            "Do not treat a catalog entry as runtime PASS.",
            "Do not treat runtime readiness facts as selected capability execution.",
            "Do not treat diagnostic selection trace as successful external execution.",
            "Report BLOCKED, DEGRADED, NOT_SUPPORTED, or NOT_FOUND when preferred capability facts are unavailable.",
        ],
    }


def discover_host_capability_context(root, *, registry_capabilities):
    """FIX-117: build restricted-environment capability benchmark facts."""
    host_id, host_facts = _capability_host_id(root)
    capabilities, registry_facts = registry_capabilities(root)
    verify_exists, verify_fact = _host_capability_source_fact(
        root,
        "skills/software-project-governance/infra/verify_workflow.py",
        "local validator present",
        "local validator missing",
    )
    skill_exists, skill_fact = _host_capability_source_fact(
        root,
        "skills/software-project-governance/SKILL.md",
        "local workflow skill present",
        "local workflow skill missing",
    )
    tools_exists, tools_fact = _host_capability_source_fact(
        root,
        "skills/software-project-governance/infra/TOOLS.md",
        "tool index present",
        "tool index missing",
    )
    req_exists, req_fact = _host_capability_source_fact(
        root,
        "docs/requirements/capability-discovery-orchestration-0.45.0.md",
        "FIX-117 contract doc present",
        "FIX-117 contract doc missing",
    )
    codex_fact = "restricted benchmark scenario: Codex CLI blocked"
    gemini_fact = "restricted benchmark scenario: Gemini auth blocked"

    fallback = _host_context_capability(capabilities, capability_id="fallback.local-diagnostic-readonly")
    local_skill = _host_context_capability(capabilities, capability_id="software-project-governance.skill-entry")
    local_script = _host_context_capability(capabilities, capability_id="verify-workflow.capability-context-tool")
    mcp = _host_context_capability(capabilities, kind="mcp")
    browser = _host_context_capability(capabilities, kind="browser")
    sub_agent = _host_context_capability(capabilities, kind="sub_agent")
    plugin = _host_context_capability(capabilities, kind="plugin")

    fallback_id = fallback.get("capability_id", "fallback.local-diagnostic-readonly") if fallback else "fallback.local-diagnostic-readonly"
    script_id = local_script.get("capability_id", "verify-workflow.capability-context-tool") if local_script else "verify-workflow.capability-context-tool"
    skill_id = local_skill.get("capability_id", "software-project-governance.skill-entry") if local_skill else "software-project-governance.skill-entry"

    validation = "python skills/software-project-governance/infra/verify_workflow.py check-host-capability-context --fail-on-issues"
    scenarios = [
        _host_restricted_scenario(
            "no_network",
            "Network access is unavailable or not allowed for capability selection.",
            "network.external-lookup",
            fallback_id,
            "DEGRADED",
            "Use local registry/context facts only; do not call external APIs or treat missing network as PASS.",
            [verify_fact, *registry_facts, "host constraint: no network"],
            validation,
        ),
        _host_restricted_scenario(
            "no_plugin_install",
            "Plugin installation, enable, disable, upgrade, or uninstall is unavailable.",
            plugin.get("capability_id", "codex.desktop.plugin-manifest") if plugin else "codex.desktop.plugin-manifest",
            fallback_id,
            "DEGRADED",
            "Inspect manifest/catalog facts only; do not claim Desktop marketplace-management E2E PASS.",
            [tools_fact, "host constraint: no plugin install"],
            validation,
        ),
        _host_restricted_scenario(
            "no_mcp",
            "No MCP server is installed or reachable in the current host.",
            mcp.get("capability_id", "host.mcp.connectors") if mcp else "host.mcp.connectors",
            fallback_id,
            "NOT_SUPPORTED",
            "Report MCP as unavailable and use local diagnostic fallback.",
            [*registry_facts, "host constraint: no MCP"],
            validation,
        ),
        _host_restricted_scenario(
            "no_browser",
            "Browser automation is not available or not allowed.",
            browser.get("capability_id", "browser.in-app-or-chrome-control") if browser else "browser.in-app-or-chrome-control",
            fallback_id,
            "NOT_SUPPORTED",
            "Do not open browser state; use local text and registry facts.",
            [*registry_facts, "host constraint: no browser"],
            validation,
        ),
        _host_restricted_scenario(
            "no_sub_agent",
            "Host-native sub-agent separation is unavailable.",
            sub_agent.get("capability_id", "agent-team.governance-developer") if sub_agent else "agent-team.governance-developer",
            script_id,
            "DEGRADED",
            "Record degraded execution; do not count self-review as independent review.",
            [*registry_facts, "host constraint: no sub-agent"],
            validation,
        ),
        _host_restricted_scenario(
            "local_skill_only",
            "Only the local workflow skill and local validator are available.",
            skill_id,
            script_id if verify_exists else skill_id,
            "PASS" if skill_exists and verify_exists else "DEGRADED",
            "Local skill and script may be used for diagnostics, but this is not external capability execution.",
            [skill_fact, verify_fact, "host constraint: local skill only"],
            validation,
        ),
        _host_restricted_scenario(
            "codex_cli_blocked",
            "Codex CLI headless target-cwd runtime is blocked.",
            "codex.cli.headless-runtime",
            fallback_id,
            "BLOCKED",
            "Codex App/session or plugin metadata cannot substitute for Codex CLI runtime PASS.",
            [codex_fact],
            validation,
        ),
        _host_restricted_scenario(
            "gemini_auth_blocked",
            "Gemini CLI authentication is missing or blocked.",
            "gemini.cli.runtime",
            fallback_id,
            "BLOCKED",
            "Gemini version or thin projection cannot substitute for authenticated runtime PASS.",
            [gemini_fact],
            validation,
        ),
    ]

    return {
        "scenario": "restricted-environment-capability-selection",
        "host_id": host_id,
        "benchmark_kind": "benchmark/diagnostic fixture; not external execution",
        "source_facts": [
            *host_facts,
            *registry_facts,
            verify_fact,
            skill_fact,
            tools_fact,
            req_fact,
            codex_fact,
            gemini_fact,
        ],
        "restricted_scenarios": scenarios,
        "side_effect_boundary": "read-only benchmark/diagnostic; no network, plugin install, MCP call, browser action, sub-agent spawn, Codex CLI execution, Gemini auth flow, commits, pushes, or external APIs",
        "validation_command": validation,
        "review_requirement": "FIX-117 closure still requires independent Code Reviewer approval; benchmark output is not self-review",
        "no_overclaim_boundary": [
            "FIX-117 fixture is benchmark/diagnostic, not external execution.",
            "FIX-117 fixture is not Desktop marketplace E2E PASS.",
            "blocked capability is not runtime PASS.",
            "catalog fact is not runtime PASS.",
            "Do not claim automatic best-tool selection.",
            "Do not claim universal plugin availability.",
        ],
    }


def check_capability_context(root, sampled_context, *, policy, requirements_path, tools_path, display_path):
    """FIX-115: capability selection trace must be fact-backed and no-overclaim safe."""
    context = sampled_context
    failures = []
    for field in policy.required_fields:
        if field not in context:
            failures.append(f"capability context: missing `{field}`")

    source_facts = context.get("source_facts", [])
    if not isinstance(source_facts, list) or not source_facts:
        failures.append("capability context: source_facts must be a non-empty list")

    selected = context.get("selected_capability", {})
    if not isinstance(selected, dict):
        failures.append("capability context: selected_capability must be an object")
        selected = {}
    selected_status = selected.get("status")
    if selected_status not in policy.allowed_statuses:
        failures.append("capability context: selected_capability.status must be a known capability status")
    if not selected.get("source_facts"):
        failures.append("capability context: selected_capability requires source_facts")
    selected_id = selected.get("capability_id", "")
    selected_text = json.dumps(selected, ensure_ascii=False).lower()
    if (
        selected_status == "AVAILABLE"
        and any(token in selected_id for token in ("catalog", "registry", "readiness-matrix"))
    ):
        failures.append("capability context: catalog or runtime fact-source cannot be selected as AVAILABLE runtime PASS")
    if selected_status == "AVAILABLE" and (
        "catalog-only" in selected_text or "not runtime pass" in selected_text
    ):
        failures.append("capability context: catalog-only fact cannot be treated as AVAILABLE")

    available = context.get("available_capabilities", [])
    if not isinstance(available, list):
        failures.append("capability context: available_capabilities must be a list")
        available = []
    if not available and selected_status not in policy.degraded_statuses:
        failures.append("capability context: no available capabilities requires blocked/degraded selected status")
    for index, capability in enumerate(available, start=1):
        if not isinstance(capability, dict):
            failures.append(f"capability context: available_capabilities[{index}] must be an object")
            continue
        status = capability.get("status")
        if status not in policy.allowed_statuses:
            failures.append(f"capability context: {capability.get('capability_id', index)} has unknown status `{status}`")
        if not capability.get("source_facts"):
            failures.append(f"capability context: {capability.get('capability_id', index)} missing source_facts")
        capability_text = json.dumps(capability, ensure_ascii=False).lower()
        if status == "AVAILABLE" and (
            "catalog-only" in capability_text
            or "not runtime pass" in capability_text
            or "runtime status evidence only" in capability_text
        ):
            failures.append(f"capability context: {capability.get('capability_id', index)} treats catalog/runtime facts as AVAILABLE")

    rejected = context.get("rejected_alternatives", [])
    if not isinstance(rejected, list) or not rejected:
        failures.append("capability context: rejected_alternatives must be a non-empty list")
        rejected = []
    if not any(item.get("status") in policy.degraded_statuses for item in rejected if isinstance(item, dict)):
        failures.append("capability context: rejected_alternatives must include blocked/degraded/unavailable alternatives")
    if not any("automatic" in json.dumps(item, ensure_ascii=False).lower() for item in rejected if isinstance(item, dict)):
        failures.append("capability context: rejected_alternatives must reject automatic best-tool selection overclaim")

    degradation = context.get("degradation", {})
    if not isinstance(degradation, dict):
        failures.append("capability context: degradation must be an object")
        degradation = {}
    degradation_status = degradation.get("status")
    if degradation_status not in policy.allowed_statuses:
        failures.append("capability context: degradation.status must be a known capability status")
    preferred_unavailable = any(
        isinstance(item, dict)
        and item.get("capability_id") == "external.capability-registry"
        and item.get("status") in policy.degraded_statuses
        for item in rejected
    )
    if preferred_unavailable and degradation_status not in policy.degraded_statuses:
        failures.append("capability context: unavailable preferred capability must produce degraded or blocked status")

    boundary_text = " ".join(context.get("no_overclaim_boundary", []))
    for token in policy.boundary_tokens:
        if token not in boundary_text:
            failures.append(f"capability context: no_overclaim_boundary missing `{token}`")
    if not any(
        "`capability-context` CLI registration" in fact
        and "top_level_handler=yes" in fact
        and "main=yes" in fact
        and "main_subparser=yes" in fact
        and "main_dispatch=yes" in fact
        for fact in source_facts
    ):
        failures.append("capability context: missing actual capability-context CLI registration facts")
    if "read-only" not in context.get("side_effect_boundary", "").lower():
        failures.append("capability context: side_effect_boundary must state read-only behavior")
    if "capability-context" not in context.get("validation_command", ""):
        failures.append("capability context: validation_command must name capability-context")
    if "independent Code Reviewer" not in context.get("review_requirement", ""):
        failures.append("capability context: review_requirement must preserve independent review")

    docs = [
        root / requirements_path,
        root / tools_path,
    ]
    required_doc_tokens = [
        "capability-context",
        "source_facts",
        "rejected_alternatives",
        "degradation",
        "side_effect_boundary",
        "validation_command",
        "review_requirement",
        "no_overclaim_boundary",
    ]
    for path in docs:
        if not path.is_file():
            failures.append(f"{display_path(path, root)}: missing capability context contract doc")
            continue
        text = path.read_text(encoding="utf-8")
        for token in required_doc_tokens:
            if token not in text:
                failures.append(f"{display_path(path, root)}: missing capability context token `{token}`")
    return failures


def check_host_capability_context(
    root, sampled_context, *, policy, requirements_path, tools_path,
    display_path, valid_string_list, has_scoped_negation,
):
    """FIX-117: restricted host benchmark must degrade honestly."""
    context = sampled_context
    failures = []
    for field in policy.required_fields:
        if field not in context:
            failures.append(f"host capability context: missing `{field}`")

    source_facts = context.get("source_facts", [])
    if not valid_string_list(source_facts):
        failures.append("host capability context: source_facts must be a non-empty string list")

    scenarios = context.get("restricted_scenarios", [])
    if not isinstance(scenarios, list) or not scenarios:
        failures.append("host capability context: restricted_scenarios must be a non-empty list")
        scenarios = []

    seen = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            failures.append("host capability context: restricted_scenarios entries must be objects")
            continue
        scenario_id = scenario.get("scenario_id", "<missing>")
        seen.add(scenario_id)
        label = f"host capability context: scenario {scenario_id}"
        for field in policy.scenario_fields:
            if field not in scenario:
                failures.append(f"{label}: missing `{field}`")
        status = scenario.get("status")
        if status not in policy.allowed_statuses:
            failures.append(f"{label}: unknown status `{status}`")
        if scenario_id != "local_skill_only" and status not in policy.unavailable_statuses:
            failures.append(f"{label}: restricted scenario must be blocked/degraded/not-supported/not-found")
        if scenario_id == "local_skill_only" and status not in {"PASS", "AVAILABLE", "DEGRADED"}:
            failures.append(f"{label}: local_skill_only must remain local PASS/AVAILABLE or DEGRADED")
        if scenario.get("selected_capability") == scenario.get("preferred_capability") and status in policy.unavailable_statuses:
            failures.append(f"{label}: unavailable preferred capability cannot be selected")
        if not valid_string_list(scenario.get("source_facts")):
            failures.append(f"{label}: source_facts must be a non-empty string list")
        if "check-host-capability-context" not in scenario.get("validation_command", ""):
            failures.append(f"{label}: validation_command must name check-host-capability-context")
        scenario_boundary = " ".join(scenario.get("no_overclaim_boundary", []))
        if "runtime PASS" not in scenario_boundary and "external execution" not in scenario_boundary:
            failures.append(f"{label}: no_overclaim_boundary must prevent runtime/external execution overclaim")
        required_blocked_fact = policy.blocked_facts.get(scenario_id)
        if required_blocked_fact and required_blocked_fact not in scenario.get("source_facts", []):
            failures.append(f"{label}: missing direct blocked runtime source fact `{required_blocked_fact}`")

    missing = sorted(policy.scenarios - seen)
    if missing:
        failures.append(f"host capability context: missing restricted scenario(s): {', '.join(missing)}")

    boundary_text = " ".join(context.get("no_overclaim_boundary", []))
    for token in policy.boundary_tokens:
        if token not in boundary_text:
            failures.append(f"host capability context: no_overclaim_boundary missing `{token}`")
    if "read-only" not in context.get("side_effect_boundary", "").lower():
        failures.append("host capability context: side_effect_boundary must state read-only behavior")
    for token in ("network", "plugin install", "MCP", "browser", "sub-agent"):
        if token.lower() not in context.get("side_effect_boundary", "").lower():
            failures.append(f"host capability context: side_effect_boundary missing `{token}`")
    if "check-host-capability-context" not in context.get("validation_command", ""):
        failures.append("host capability context: validation_command must name check-host-capability-context")
    if "independent Code Reviewer" not in context.get("review_requirement", ""):
        failures.append("host capability context: review_requirement must preserve independent review")
    if policy.blocked_facts["codex_cli_blocked"] not in source_facts:
        failures.append("host capability context: missing Codex CLI blocked source fact")
    if policy.blocked_facts["gemini_auth_blocked"] not in source_facts:
        failures.append("host capability context: missing Gemini auth blocked source fact")

    for text in _host_context_values(context):
        lowered = text.lower()
        for phrase in policy.forbidden_claims:
            if phrase in lowered and not has_scoped_negation(text, phrase):
                failures.append(f"host capability context: forbidden overclaim `{phrase}`")

    docs = [
        root / requirements_path,
        root / tools_path,
    ]
    required_doc_tokens = [
        "check-host-capability-context",
        "TOOL-033",
        "FIX-117",
        "benchmark/diagnostic",
        "not external execution",
        "not Desktop marketplace E2E PASS",
        "no network",
        "no plugin install",
        "no MCP",
        "no browser",
        "no sub-agent",
        "local skill only",
        "Codex CLI blocked",
        "Gemini auth blocked",
    ]
    for path in docs:
        if not path.is_file():
            failures.append(f"{display_path(path, root)}: missing FIX-117 host capability contract doc")
            continue
        text = path.read_text(encoding="utf-8")
        for token in required_doc_tokens:
            if token not in text:
                failures.append(f"{display_path(path, root)}: missing FIX-117 token `{token}`")
    return failures


def _host_context_capability(capabilities, kind=None, capability_id=None):
    for capability in capabilities:
        if capability_id and capability.get("capability_id") == capability_id:
            return capability
        if kind and capability.get("kind") == kind:
            return capability
    return None


def _host_restricted_scenario(
    scenario_id,
    constraint,
    preferred,
    selected,
    status,
    reason,
    source_facts,
    validation_command,
):
    return {
        "scenario_id": scenario_id,
        "constraint": constraint,
        "preferred_capability": preferred,
        "selected_capability": selected,
        "status": status,
        "degradation_boundary": reason,
        "validation_command": validation_command,
        "source_facts": source_facts,
        "no_overclaim_boundary": [
            "blocked capability is not runtime PASS",
            "catalog fact is not runtime PASS",
            "diagnostic trace is not external execution",
        ],
    }


def _host_context_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _host_context_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _host_context_values(item)
