# Feature Flags - 0.46.0

**Version**: 0.46.0

0.46.0 adds documentation and release-gate enforcement for ecosystem and official-submission positioning. It does not add a runtime feature flag and does not change capability execution behavior.

The release guard consumes `docs/requirements/capability-discovery-orchestration-0.45.0.md`, `docs/requirements/governance-eval-benchmark-0.45.0.md`, FIX-115, FIX-116, FIX-117, and Codex Desktop marketplace-management BLOCKED / NOT_RUN evidence.

## Flags

| Surface | State | Boundary |
| --- | --- | --- |
| Official submission ecosystem docs | Available as tracked documentation | Documentation is not official approval or marketplace approval |
| Ecosystem comparison page | Available as tracked documentation | Comparison explains complementarity, not replacement of external capabilities |
| Migration guide | Available as tracked documentation | Migration preserves host-specific availability and side-effect boundaries |
| Examples page | Available as tracked documentation | Examples are bounded scenarios, not universal runtime support |
| `check-release --version 0.46.0` official submission detail | Available as deterministic guard | Guard checks positioning and no-overclaim boundary only |

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No 1.0.0 production-ready.

RISK-036 remains open.
