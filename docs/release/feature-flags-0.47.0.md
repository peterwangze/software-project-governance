# Feature Flags - 0.47.0

**Version**: 0.47.0

REL-024 / 0.47.0 adds mainstream agent loading documentation and deterministic guard coverage. It does not add a runtime feature flag and does not change capability execution behavior.

FIX-120 is carried forward from `0.46.0-post` as a Codex marketplace root schema prerequisite for this package. It is metadata/schema readiness only, not Codex Desktop marketplace lifecycle E2E PASS.

## Flags

| Surface | State | Boundary |
| --- | --- | --- |
| README mainstream loading matrix | Available as tracked documentation | Matrix describes loading paths and compatibility rows only |
| Tier 1 adapter loading guides | Available as tracked documentation | Adapter guidance is not official approval or marketplace approval |
| Tier 2 compatibility rows | Available as research references | Compatibility rows remain RESEARCH_ONLY / NOT_RUNTIME_VERIFIED until native entry projection and target-cwd E2E evidence exist |
| `check-mainstream-agent-loading` | Available as deterministic guard | Guard checks README, Tier 1 adapters, requirements source citations, validation commands, and no-overclaim boundary |
| `check-release --version 0.47.0` mainstream loading detail | Available as release guard | Guard consumes Check 28n and TOOL-035 boundary only |

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No 1.0.0 production-ready.

RISK-036 remains open.
