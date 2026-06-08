# Release Checklist - 0.45.0

**Version**: 0.45.0
**Type**: Minor release
**Scope**: AUDIT-110, AUDIT-111, FIX-115, FIX-116, FIX-117, REL-022, REQ-092, REQ-093, RISK-036

| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | Version declarations synchronized to 0.45.0 | PASS | `SKILL.md`, canonical manifest, Claude/Codex plugin manifests, marketplace metadata, governance packs, capability registry, hook @version, target fixture skill, target fixture plan tracker |
| 2 | CHANGELOG 0.45.0 entry exists | PASS | `project/CHANGELOG.md` |
| 3 | FIX-115 capability context trace included | PASS | Commit `3fa8162d0429eab1d3b728c856ae03ff46022cc3`; GitHub Governance CI success |
| 4 | FIX-116 external capability registry included | PASS | Commit `9325af6d022d1a0c642eee1af6465119fd8cdeb6`; GitHub Governance CI success |
| 5 | FIX-117 restricted-environment fixtures included | PASS | Commit `25677d76bc1317be20f32ef70db3fd1f3a25a8fc`; GitHub Governance CI run `27143439126` success |
| 6 | Governance Eval & Benchmark scope documented | PASS | `docs/requirements/governance-eval-benchmark-0.45.0.md` |
| 7 | Codex Desktop marketplace-management E2E report exists | BLOCKED | `docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md` result matrix marks lifecycle steps BLOCKED/NOT_RUN because real Desktop evidence is absent |
| 8 | No-overclaim boundary preserved | PASS | Release docs and requirements state no official approval, marketplace approval, universal/full runtime support, external first-session pilot success, Codex Desktop marketplace-management E2E PASS, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, or 1.0.0 production-ready |
| 9 | Runtime/readiness facts remain conservative | PASS | 0.45.0 does not convert runtime matrix, local demo proof, catalog facts, or current Codex App session into universal/full runtime support |
| 10 | Capability registry remains catalog-only | PASS | `check-capability-registry --fail-on-issues`; catalog entry is not runtime PASS |
| 11 | Restricted-environment benchmark remains diagnostic | PASS | `check-host-capability-context --fail-on-issues`; fixture is not external execution and not Desktop marketplace E2E PASS |
| 12 | RISK-036 remains open | PASS | Release docs keep RISK-036 open until official submission package, external validation, Desktop E2E PASS or conservative blocked carry-forward, and capability selection evidence close |

## Version Declaration Files

| File | Expected version |
|---|---|
| `skills/software-project-governance/SKILL.md` | 0.45.0 |
| `skills/software-project-governance/core/manifest.json` | 0.45.0 |
| `skills/software-project-governance/core/governance-packs.json` | 0.45.0 |
| `skills/software-project-governance/core/capability-registry.json` | 0.45.0 |
| `.claude-plugin/plugin.json` | 0.45.0 |
| `.claude-plugin/marketplace.json` | 0.45.0 |
| `.codex-plugin/plugin.json` | 0.45.0 |
| `project/e2e-test-project/skills/software-project-governance/SKILL.md` | 0.45.0 |
| `project/e2e-test-project/.governance/plan-tracker.md` | 0.45.0 |
| `skills/software-project-governance/infra/hooks/pre-commit` | @version 0.45.0 |
| `skills/software-project-governance/infra/hooks/commit-msg` | @version 0.45.0 |
| `skills/software-project-governance/infra/hooks/post-commit` | @version 0.45.0 |
| `skills/software-project-governance/infra/hooks/prepare-commit-msg` | @version 0.45.0 |

## Release Decision

0.45.0 can be prepared as a release package for Release Reviewer inspection. The package is conservative: it publishes the capability discovery and restricted benchmark evidence now available, and it explicitly blocks Codex Desktop marketplace-management lifecycle PASS because no real Desktop add/install/enable/invoke/upgrade/uninstall evidence exists in this workspace.

This release package is not committed, tagged, pushed, submitted to any marketplace, or approved by any marketplace. RISK-036 remains open.
