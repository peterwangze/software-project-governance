# Ecosystem Examples - 0.46.0

Version target: 0.46.0

Related task: FIX-118

These examples consume `docs/requirements/capability-discovery-orchestration-0.45.0.md`, `docs/requirements/governance-eval-benchmark-0.45.0.md`, FIX-115, FIX-116, FIX-117, and the Codex Desktop marketplace-management BLOCKED / NOT_RUN report.

## Example 1: Restricted Host, Local Governance Fallback

Context: no network, no plugin install, no MCP, no browser, and no sub-agent surface.

Expected governance behavior:

- Select local governance diagnostics or scripts.
- Mark external capability paths DEGRADED, BLOCKED, NOT_SUPPORTED, or NOT_FOUND.
- Preserve the validation command.
- Record that local fallback success is not external capability execution.

Source evidence: FIX-117 restricted-environment benchmark.

## Example 2: Capability Registry Is Present

Context: `skills/software-project-governance/core/capability-registry.json` lists plugin, skill, tool, MCP, browser, sub-agent, script, and fallback entries.

Expected governance behavior:

- Treat registry entries as catalog facts.
- Use source facts and side-effect boundaries to decide whether a capability can be considered.
- Do not treat catalog entry runtime PASS as true without separate runtime evidence.

Source evidence: FIX-116 capability registry.

## Example 3: Codex Desktop Submission Boundary

Context: plugin manifests and local marketplace metadata exist, but no real Codex Desktop add/install/enable/invoke/upgrade/uninstall lifecycle was executed.

Expected governance behavior:

- Carry forward BLOCKED / NOT_RUN for Codex Desktop marketplace-management.
- Do not claim official approval or marketplace approval.
- Do not treat manifest, asset, or catalog presence as Desktop lifecycle PASS.

Source evidence: `docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md`.

## Example 4: Complementary Skill Use

Context: a host provides a specialized Agent Skill for a domain task.

Expected governance behavior:

- Keep using the specialized skill.
- Record the selection reason, source facts, side-effect boundary, validation command, and review requirement.
- Keep Software Project Governance focused on delivery trust instead of reimplementing the skill.

Source evidence: FIX-115 capability context selection trace.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No 1.0.0 production-ready.
