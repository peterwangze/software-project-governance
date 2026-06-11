# Mainstream Agent Loading Readiness 0.47.0

Date: 2026-06-10
Task: AUDIT-112
Scope: pre-1.0.0 loading and usage guidance for mainstream AI coding agents.

This document turns the user's requirement into a 0.47.0 release scope: mainstream agents should be able to discover how to load this workflow/plugin, verify the first trust signal, and understand current runtime boundaries without reading old adapter history.

No official approval. No marketplace approval. No universal/full runtime support. No Codex Desktop marketplace-management E2E PASS. RISK-036 remains open.

## Mainstream Scope

0.47.0 uses a two-tier compatibility model.

| Tier | Agents | 0.47.0 treatment |
| --- | --- | --- |
| Tier 1 loading guide | Codex, Claude Code, Gemini CLI, opencode | Provide direct README and adapter guidance, validation commands, status boundary, and no-overclaim wording. |
| Tier 2 compatibility matrix | Cursor, GitHub Copilot coding agent, Cline, Windsurf/Cascade, Kiro | Document official instruction/rules surfaces as compatibility references only. Do not create adapter manifests or claim runtime PASS until target-cwd E2E exists. |

## Official Surface Findings

| Agent | Official or primary source | Loading surface observed | 0.47.0 product implication |
| --- | --- | --- | --- |
| Codex | OpenAI Codex skills and customization docs: `https://developers.openai.com/codex/skills`, `https://developers.openai.com/codex/guides/agents-md`, `https://developers.openai.com/codex/concepts/customization` | Skills are reusable workflows; plugins package skills/apps; `AGENTS.md` provides persistent project guidance. | Keep `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, `AGENTS.md`, and `skills/software-project-governance/SKILL.md` aligned. 2026-06-11 Codex CLI headless target-cwd read E2E is PASS/DEGRADED; README must still distinguish this from Codex Desktop marketplace lifecycle PASS. |
| Claude Code | Anthropic official marketplace repository: `https://github.com/anthropics/claude-plugins-official` | Claude Code installs plugins from marketplaces via `/plugin install {plugin-name}@{marketplace}` and browse/discover surfaces. | Keep `.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json`, and README Claude install commands current. Current project install path remains `/plugin marketplace add peterwangze/software-project-governance` then `/plugin install software-project-governance@spg`. |
| Gemini CLI | Gemini CLI docs: `https://geminicli.com/docs/cli/gemini-md/`; Google codelab notes context files/custom commands/MCP: `https://codelabs.developers.google.com/gemini-cli-hands-on` | `GEMINI.md` context files provide persistent project instructions; custom commands and MCP are separate extension points. | Keep Gemini adapter as thin projection through `GEMINI.md` pointing to `skills/software-project-governance/SKILL.md`; 2026-06-11 agent-runtime E2E is PASS/DEGRADED when `GEMINI_CLI_TRUST_WORKSPACE=true` is set for headless execution. Do not claim Gemini plugin marketplace or universal/full runtime support. |
| opencode | opencode docs: `https://opencode.ai/docs/rules/`, `https://opencode.ai/docs/agents/`, `https://opencode.ai/docs/config/` | `AGENTS.md` provides custom instructions; agents/config/plugin directories are available through normal or custom config dirs. | Keep opencode adapter as thin `AGENTS.md`/configured instruction pointer; current read/load target-cwd E2E is PASS, workflow closure remains DEGRADED. |
| Cursor | Cursor rules docs: `https://cursor.com/docs/rules` | Project, team, user rules and `AGENTS.md` are persistent instruction surfaces. | Compatibility row only; no adapter manifest or runtime PASS in 0.47.0. |
| GitHub Copilot coding agent | GitHub docs and changelog: `https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot`, `https://github.blog/changelog/2025-08-28-copilot-coding-agent-now-supports-agents-md-custom-instructions/` | Repository custom instructions and `AGENTS.md` can guide Copilot coding agent behavior. | Compatibility row only; no adapter manifest or runtime PASS in 0.47.0. |
| Cline | Cline rules docs: `https://docs.cline.bot/customization/cline-rules` | Rules are Markdown files for persistent instructions. | Compatibility row only; likely pointer-to-SKILL pattern, but not runtime verified. |
| Windsurf/Cascade | Windsurf/Devin docs: `https://docs.windsurf.com/es/windsurf/cascade/memories` | Rules and memories provide workspace/global/system-level context. | Compatibility row only; no runtime PASS. |
| Kiro | Kiro steering docs: `https://kiro.dev/docs/steering/` | Workspace steering files live under `.kiro/steering/`. | Compatibility row only; no runtime PASS. |

## Current Repository Facts

| Agent | Existing assets | Runtime status from existing matrix | Gap for 0.47.0 |
| --- | --- | --- | --- |
| Claude Code | `.claude-plugin/*`, `skills/software-project-governance/SKILL.md`, `adapters/claude/*` | PASS / DEGRADED | Adapter README is historically framed as deprecated; needs current user-facing loading guide. |
| Codex | `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json`, `AGENTS.md`, `skills/software-project-governance/SKILL.md`, `adapters/codex/*` | PASS / DEGRADED for CLI headless target-cwd read E2E as of 2026-06-11 | README must include personal/repo marketplace guidance and avoid treating manifest or CLI read E2E as Desktop lifecycle PASS. |
| Gemini CLI | `GEMINI.md` projection in target fixture, `adapters/gemini/*`, auth/trust preflight | PASS / DEGRADED for target-cwd read E2E as of 2026-06-11 with headless trust enabled | README must use precise `GEMINI.md` thin projection and note `GEMINI_CLI_TRUST_WORKSPACE=true` for headless automation. |
| opencode | `AGENTS.md` projection, `adapters/opencode/*`, provider preflight | PASS / DEGRADED | README and adapter guide should show exact pointer and runtime validation commands. |

## 0.47.0 Work Items

| Task | Priority | Scope | Acceptance |
| --- | --- | --- | --- |
| AUDIT-112 | P0 | Research mainstream agent loading surfaces and plan 0.47.0 before 1.0.0. | This document exists, decision/evidence/roadmap updated, RISK-036 remains open. |
| FIX-121 | P0 | Update README and Tier 1 adapter READMEs with current loading steps, verification commands, and boundaries. | README includes a "Mainstream Agent Loading" matrix and each Tier 1 adapter README has loading/verify/no-overclaim sections. |
| FIX-122 | P1 | Add deterministic guard for README/adapter mainstream loading guidance. | `check-mainstream-agent-loading --fail-on-issues`, Check 28n, TOOL-035, and tests pass. |
| REL-024 | P0 | Release 0.47.0 with version bump, changelog, release docs, final 0.46.0~0.47.0 review, push, tag, CI. | `check-release --version 0.47.0 --require-changelog --runtime-adapters` passes before release; no unsupported claim appears. |

## No-Overclaim Boundary

0.47.0 loading readiness is documentation, adapter contract, and guard readiness. It is not:

- official approval or marketplace approval;
- universal/full runtime support;
- Codex Desktop marketplace-management E2E PASS;
- a claim that every listed agent can install the plugin through a native plugin marketplace;
- automatic best-tool selection;
- catalog entry runtime PASS;
- 1.0.0 production-ready status.

Compatibility rows remain RESEARCH_ONLY / NOT_RUNTIME_VERIFIED until a native entry projection, runtime harness, target-cwd E2E evidence, and degraded capability boundary are all recorded.
