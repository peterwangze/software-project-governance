# Rollback Plan - 0.46.0

**Version**: 0.46.0

Rollback is required if the official-submission ecosystem package overclaims approval, runtime support, automatic selection, Desktop lifecycle status, or 1.0.0 readiness.

## Triggers

- `check-release --version 0.46.0 --require-changelog --runtime-adapters` fails.
- Official submission docs, comparison, migration guide, examples, release docs, or CHANGELOG claim official approval, marketplace approval, universal/full runtime support, external first-session pilot success, Codex Desktop marketplace-management E2E PASS, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, or 1.0.0 production-ready.
- The package stops consuming FIX-115, FIX-116, FIX-117, or the 0.45.0 Codex Desktop marketplace-management BLOCKED / NOT_RUN report.
- The package stops consuming `docs/requirements/capability-discovery-orchestration-0.45.0.md` or `docs/requirements/governance-eval-benchmark-0.45.0.md`.

## Steps

1. Revert the 0.46.0 package commit after it exists:

```bash
git revert <0.46.0-release-package-commit>
```

2. Re-run the previous release gate:

```bash
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.45.0 --require-changelog --runtime-adapters
```

3. Re-prepare the ecosystem docs with the no-overclaim boundary below before retrying 0.46.0.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No 1.0.0 production-ready.

RISK-036 remains open.
