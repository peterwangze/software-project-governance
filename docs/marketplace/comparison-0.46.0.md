# Ecosystem Comparison - 0.46.0

Version target: 0.46.0

Related task: FIX-118

## Comparison Summary

| Product or capability | Primary job | How Software Project Governance complements it |
| --- | --- | --- |
| Superpowers-style packs | Add specialized agent behaviors and task capabilities. | Provides governance continuity, evidence discipline, release boundaries, and selection traces around when such capabilities are used. |
| Agent Skills | Execute focused domain workflows. | Records why a skill is appropriate, what facts support availability, and what review or fallback boundary applies. |
| MCP servers | Connect agents to external systems and data. | Keeps MCP use evidence-backed and side-effect-aware; blocked MCP remains blocked instead of being treated as runtime PASS. |
| Browser tools | Inspect or automate browser workflows. | Adds governance checks for user-visible effects, validation evidence, screenshots or logs, and review handoff. |
| Host-native plugins | Provide installation and host integration. | Supplies plugin metadata and governance entry points while preserving approval and marketplace lifecycle boundaries. |
| Local scripts | Provide deterministic checks and fallbacks. | Keeps restricted environments useful without claiming external capability execution. |

## Capability Boundary

Software Project Governance is not a broad replacement for external capability ecosystems. It is the trust layer that:

- Tracks source facts and evidence.
- Explains selected and rejected capabilities.
- Defines side-effect boundaries.
- Requires validation commands.
- Preserves independent review requirements.
- Falls back honestly in restricted environments.

## 0.45.0 Evidence Consumed

The comparison uses `docs/requirements/capability-discovery-orchestration-0.45.0.md`, `docs/requirements/governance-eval-benchmark-0.45.0.md`, the 0.45.0 capability selection trace, capability registry, restricted-environment benchmark, and Codex Desktop marketplace-management BLOCKED / NOT_RUN report as source evidence. These facts keep the comparison conservative: catalog facts, manifests, or blocked lifecycle rows are not rewritten as successful runtime execution.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No 1.0.0 production-ready.
