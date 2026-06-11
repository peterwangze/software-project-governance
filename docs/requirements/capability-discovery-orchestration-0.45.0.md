# Capability Discovery and Orchestration Plan

Version target: 0.45.0 and 0.46.0

Primary task: AUDIT-111

Related requirement: REQ-093

Related risk: RISK-036

## Purpose

The workflow should stay focused on trusted governance, not become a broad built-in toolbox. Its durable value is to keep goals, facts, evidence, risk, decisions, quality, review, and release boundaries trustworthy, then help the current host agent use the best available external capability for the current task.

This plan turns that product stance into a verifiable capability chain:

```
host facts -> scenario -> available capabilities -> chosen path -> fallback -> evidence boundary
```

The goal is not to claim global best-tool selection. The goal is to make the workflow inspect the user's constrained environment, explain the most suitable available plugin/skill/tool/fallback for the current governance scenario, and record why that choice is safe enough.

## Source Facts

| Fact | Evidence |
| --- | --- |
| The product is already positioned as an AI coding delivery trust layer rather than another coding skill pack. | `README.md`, DEC-072, REQ-088 |
| Runtime status is already fact-backed and conservative for Claude, Codex, Gemini, opencode, Cursor, and Copilot. | `docs/requirements/runtime-readiness-matrix-0.43.0.md`, TOOL-024 |
| Governance packs already make internal governance capability boundaries inspectable. | `skills/software-project-governance/core/governance-packs.json`, TOOL-026, TOOL-030 |
| Context-aware resume already discovers unfinished work from plan/session/evidence/risk/git/recent facts. | FIX-112, FIX-114, TOOL-027 |
| Codex Desktop marketplace-management E2E is already planned, but only for install/manage lifecycle evidence. | `docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md`, DEC-076, REQ-092 |
| The shared command contract already defines external command read order, write-back targets, gate behavior, validation, and replacement boundary. | `skills/software-project-governance/core/protocol/external-command-contract.md` |

## Gap

Current assets answer "what governance packs exist" and "which host runtimes are pass/blocked/degraded." They do not yet answer:

- Which plugin, skill, tool, MCP connector, browser path, sub-agent, shell command, local script, or fallback is available in this specific user environment.
- Why the workflow selected one capability and rejected alternatives.
- Which permission, side-effect, trust, rollback, validation, and review boundary applies to the selected capability.
- How a restricted environment should degrade without pretending the best unavailable capability was used.
- How release and official-submission docs should describe this ecosystem stance without overclaiming automatic best-tool selection.

## Product Boundary

This workflow owns the process trust layer:

- Goal alignment.
- Fact and evidence discipline.
- Risk, decision, and task continuity.
- Quality and release gates.
- Runtime capability honesty.
- Selection trace and no-overclaim boundary for external capabilities.

It does not need to own every implementation capability:

- It should discover and use host-provided plugins/skills/tools when available.
- It should prefer specialized external capabilities for domain work when their availability and side effects are known.
- It should fall back to local scripts, deterministic scaffolds, or blocked/degraded status when external capability is missing.
- It should record the choice and boundary rather than silently expanding internal scope.

## Proposed Capability Model

| Field | Meaning |
| --- | --- |
| `capability_id` | Stable ID for a plugin, skill, tool, script, MCP connector, browser path, sub-agent role, or fallback. |
| `kind` | `plugin`, `skill`, `tool`, `mcp`, `browser`, `sub_agent`, `script`, `host_builtin`, `fallback`. |
| `host_surface` | Host where the capability is available, such as Codex Desktop, Codex CLI, Claude Code, Gemini CLI, opencode, Browser plugin, Chrome plugin, or local shell. |
| `scenario` | Governance scenario where the capability can be used, such as context resume, requirement analysis, design review, code review, test execution, marketplace E2E, or release readiness. |
| `status` | `PASS`, `AVAILABLE`, `BLOCKED`, `DEGRADED`, `NOT_SUPPORTED`, `NOT_FOUND`, or `RESEARCH_ONLY`. |
| `source_facts` | Files, commands, tool metadata, runtime probes, docs, or observed host facts supporting the status. |
| `selection_reason` | Why this capability is the best available option for the current constrained environment. |
| `rejected_alternatives` | Better or possible alternatives that were unavailable, riskier, too broad, or not needed. |
| `side_effect_boundary` | Files, external systems, network, browser state, API calls, package installs, or user-visible effects the capability may touch. |
| `degraded_mode` | What remains true when the preferred capability is missing or partial. |
| `validation_command` | How the capability choice or result is checked. |
| `review_requirement` | Whether independent review is required before the result can close a task. |
| `no_overclaim_boundary` | Claims that must stay false unless direct evidence exists. |

## 0.45.0 Scope

0.45.0 should add Capability Inventory and Selection Trace as part of Governance Eval & Benchmark.

| Task | Priority | Scope | Done definition | Acceptance commands |
| --- | --- | --- | --- | --- |
| AUDIT-111 | P1 | This architecture and implementation evolution analysis. | Gap analysis exists, maps current facts to REQ-093/FIX-115~117/FIX-118/REL-022, and preserves no-overclaim boundaries. | `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues` |
| FIX-115 | P0 | Capability context and selection trace contract. | Add a fact-backed contract and diagnostic command such as `capability-context` that outputs host constraints, available capabilities, selected path, rejected alternatives, fallback, validation, and no-overclaim boundary. | `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -k CapabilityContext -v`; `python skills/software-project-governance/infra/verify_workflow.py capability-context --fail-on-issues`; `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues` |
| FIX-116 | P1 | External capability catalog/registry. | Add canonical `core/capability-registry.json` and `check-capability-registry` / Check 28k. Registry references governance packs, TOOLS.md, adapter manifests, plugin manifests, host tools, MCP/browser/sub-agent surfaces, scripts, and fallback paths without confusing internal packs with external capabilities. Validator rejects missing source facts, unknown kinds, missing validation commands, missing side-effect boundaries, catalog entry runtime PASS/external availability overclaims, governance pack confusion, official/marketplace/universal/automatic best-tool/1.0.0 overclaim wording. | `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -k CapabilityRegistry -v`; `python skills/software-project-governance/infra/verify_workflow.py check-capability-registry --fail-on-issues`; `python skills/software-project-governance/infra/verify_workflow.py capability-context --fail-on-issues`; `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues` |
| FIX-117 | P1 | Restricted-environment benchmark fixtures. | Add fixture-backed host capability context checks for no network, no plugin install, no MCP, no browser, no sub-agent, local skill only, and simulated Codex CLI / Gemini auth blocked scenarios; selection trace must produce PASS/BLOCKED/DEGRADED/NOT_SUPPORTED without inventing unavailable capability or treating catalog facts as runtime PASS. These fixtures do not require the current live Codex/Gemini runtime matrix to stay blocked. | `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -k CapabilitySelection -v`; `python skills/software-project-governance/infra/verify_workflow.py check-host-capability-context --fail-on-issues`; `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues` |
| REL-022 | P0 | Release 0.45.0. | 0.45.0 release docs include governance eval/benchmark, Codex Desktop marketplace-management E2E result or blocked status, and capability discovery/selection boundary. | `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.45.0 --require-changelog --runtime-adapters`; `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -v` |

0.45.0 should prove that the workflow can discover and explain capability choices. It does not need to fully automate every chosen external capability.

## FIX-115 Capability Context Contract

`capability-context [--fixture <project-root>] [--fail-on-issues]` is a read-only diagnostic command. It emits a capability selection trace for the current repository or fixture without writing files, installing packages, invoking browser state, calling network APIs, committing, pushing, or claiming that an external capability was executed.

Required output fields:

| Field | Contract |
| --- | --- |
| `scenario` | The capability selection scenario being diagnosed. FIX-115 uses `capability-context`. |
| `host_id` | The detected local host/project surface, backed by package metadata, entry files, or an explicit fixture fallback. |
| `available_capabilities` | Candidate capabilities supported by local source facts. Catalog-only or runtime-status fact sources must remain `DEGRADED` unless separate runtime execution evidence exists. |
| `selected_capability` | The selected read-only diagnostic path for this scenario, including `status`, `selection_reason`, and local source facts. |
| `source_facts` | Files or observed local facts that justify the host, candidates, selection, and unavailable preferred paths. |
| `rejected_alternatives` | Better or possible options that are blocked, not found, not supported, outside scope, or too risky. |
| `degradation` | `AVAILABLE`, `DEGRADED`, or `BLOCKED` result for the selection trace. Preferred capability unavailable facts must produce `DEGRADED`, `BLOCKED`, `NOT_SUPPORTED`, or `NOT_FOUND` rather than pretending success. |
| `side_effect_boundary` | Read-only local inspection boundary and explicit non-effects. |
| `validation_command` | Exact command for checking the trace: `python skills/software-project-governance/infra/verify_workflow.py capability-context --fail-on-issues`. |
| `review_requirement` | Product-code closure still requires independent Code Reviewer approval; the diagnostic output is not self-review. |
| `no_overclaim_boundary` | Explicitly forbids automatic global best-tool selection, treating a catalog entry as runtime PASS, treating runtime readiness facts as selected capability execution, and treating diagnostic selection trace as successful external execution. |

FIX-115 intentionally does not implement the full external registry. That belongs to FIX-116. When `skills/software-project-governance/core/capability-registry.json` is absent, the trace must select a local diagnostic fallback and mark the result `DEGRADED` rather than claiming automatic global best-tool selection.

## FIX-116 Capability Registry Contract

`skills/software-project-governance/core/capability-registry.json` is the canonical registry-first external capability catalog. It does not physically split plugins or install host capabilities. It records which plugin, skill, tool, MCP connector, browser path, sub-agent surface, script, or fallback may be considered for a scenario, and what evidence boundary applies before that capability can influence a task.

Required registry entry fields:

| Field | Contract |
| --- | --- |
| `capability_id` | Stable ID for a catalog entry. |
| `kind` | One of `plugin`, `skill`, `tool`, `mcp`, `browser`, `sub_agent`, `script`, or `fallback`; governance pack is not a valid external capability kind. |
| `host_surface` | Host or surface where the capability might be used, such as Codex Desktop, host skill loader, local shell, MCP runtime, browser plugin, Chrome plugin, or Agent Team orchestration. |
| `scenarios` | Scenario list where this capability can be considered. |
| `status` | One of `AVAILABLE`, `BLOCKED`, `DEGRADED`, `NOT_SUPPORTED`, `NOT_FOUND`, or `RESEARCH_ONLY`; status is catalog status, not runtime PASS. |
| `source_facts` | Non-empty facts from governance packs, `TOOLS.md`, adapter manifests, plugin manifests, host tools, docs, or local files. |
| `validation_command` | Exact command that checks this catalog entry or its fact source. |
| `side_effect_boundary` | Explicit statement of read/write, network, browser state, install, API, commit, push, or external-system effects. |
| `no_overclaim_boundary` | Explicit statements preventing catalog/runtime/availability/approval/production-ready overclaims. |

`check-capability-registry [--fail-on-issues]` is the acceptance guard. It fails on unknown `kind`, missing `source_facts`, missing `validation_command`, missing `side_effect_boundary`, catalog entry being treated as runtime PASS or external capability available, governance pack vs external capability confusion, and official approval / marketplace approval / universal plugin-skill-tool availability / automatic best-tool selection / 1.0.0 production-ready claims.

FIX-116 also updates `capability-context`: when `capability-registry.json` exists, the selected trace may report registry catalog status as `DEGRADED` or available as a fact source, but must not select the registry as runtime PASS or claim an external capability was executed. The local diagnostic fallback remains the selected execution path until a later task proves host runtime availability with direct source facts.

## FIX-117 Restricted Host Capability Context Contract

`check-host-capability-context [--fixture <project-root>] [--fail-on-issues]` is the TOOL-033 read-only benchmark/diagnostic guard. It may inspect local files, test fixtures, registry catalog facts, local skill/script facts, and runtime readiness facts. It must not execute external capabilities, call network APIs, install or mutate plugins, call MCP servers, open browsers, spawn host sub-agents, run Codex CLI target-cwd E2E, start Gemini auth flows, commit, push, or claim Desktop marketplace-management E2E PASS.

FIX-117 intentionally uses test-time fixtures and local discovery helpers instead of adding large canonical benchmark assets. The fixture is benchmark/diagnostic, not external execution, and not Desktop marketplace E2E PASS.

Required restricted scenarios:

| Scenario | Required behavior |
| --- | --- |
| `no_network` | Select local diagnostic fallback and mark `DEGRADED`; do not call external APIs or treat missing network as runtime PASS. |
| `no_plugin_install` | Inspect manifest/catalog facts only and mark `DEGRADED`; do not claim plugin install, enable, upgrade, uninstall, marketplace approval, or Desktop marketplace E2E PASS. |
| `no_mcp` | Mark MCP unavailable as `NOT_SUPPORTED`, `NOT_FOUND`, `RESEARCH_ONLY`, or `DEGRADED`; do not treat MCP catalog facts as runtime PASS. |
| `no_browser` | Mark browser automation unavailable as `NOT_SUPPORTED`, `NOT_FOUND`, or `DEGRADED`; do not open or mutate browser state. |
| `no_sub_agent` | Mark true host-native sub-agent separation unavailable or degraded; do not count self-review as independent review. |
| `local_skill_only` | Permit local skill/script diagnostic PASS when local facts exist, while stating it is not external capability execution. |
| `codex_cli_blocked` | Preserve a restricted benchmark scenario where Codex CLI blocked / unavailable behavior is simulated; Codex App/session or plugin metadata cannot substitute for Codex CLI runtime PASS in that scenario. |
| `gemini_auth_blocked` | Preserve a restricted benchmark scenario where Gemini auth blocked / unavailable behavior is simulated; Gemini version or thin projection cannot substitute for authenticated runtime PASS in that scenario. |

Each scenario must include `source_facts`, `selected_capability`, `degradation_boundary`, `validation_command`, and `no_overclaim_boundary`. The validator fails if a blocked/degraded/catalog fact is declared runtime PASS/AVAILABLE, if the degradation boundary is missing, if the validation command is missing, or if text claims automatic best-tool selection or universal plugin availability.

## 0.46.0 Scope

0.46.0 should connect the capability model to ecosystem and official-submission materials.

| Task | Priority | Scope | Done definition | Acceptance commands |
| --- | --- | --- | --- | --- |
| FIX-118 | P1 | Ecosystem positioning and official submission integration. | Submission docs, comparison page, migration guide, examples, and marketplace materials explain that this product is a governance trust layer that orchestrates external capabilities instead of replacing Superpowers, Agent Skills, MCP servers, browser tools, or host-native plugins. | `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues`; `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.46.0 --require-changelog --runtime-adapters` |

0.46.0 may also move selection trace into `/governance` scenarios and execution packets if 0.45.0 proves the schema stable enough. If that integration is not ready, official-submission docs must state that capability selection is diagnostic/trace-backed rather than universally automated.

## 1.0.0 Relationship

1.0.0 should freeze a stable Host Capability Contract only after 0.45.0 and 0.46.0 close.

Before 1.0.0 can claim production-ready or official-candidate readiness, release evidence should show:

- Mainstream host runtime status remains public and conservative.
- Capability registry and selection trace checks pass.
- Degraded or blocked capability paths are not counted as full support.
- External validation projects demonstrate that the selection trace is portable beyond this repository.
- Codex Desktop marketplace-management E2E is PASS or explicitly blocked with conservative submission wording.

## Acceptance Signals

- A user can see which capability the workflow would use in their current constrained environment and why.
- A user can see a better unavailable option listed as blocked rather than silently skipped.
- A reviewer can inspect source facts for capability availability and side-effect boundaries.
- A benchmark can simulate restricted environments and prove the workflow falls back honestly.
- Official-submission materials describe complementarity with external ecosystems rather than implying this workflow contains every capability.

## No-Overclaim Boundary

- Do not claim automatic global best-tool selection.
- Do not claim the workflow can fetch or install every plugin/skill/tool in every host.
- Do not treat internal governance pack enablement as external plugin/skill/tool availability.
- Do not treat a catalog entry as runtime PASS.
- Do not treat Codex App dogfood, Codex CLI headless, or local demo evidence as Codex Desktop marketplace-management E2E PASS.
- Do not treat diagnostic selection trace as successful external execution.
- In restricted environments, output `BLOCKED`, `DEGRADED`, `NOT_SUPPORTED`, or `NOT_FOUND` when facts require it.
