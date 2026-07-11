# Release Checklist - 0.65.1

**Version**: 0.65.1 (patch)
**Release**: Evidence trust + post-0.65.0 hotfix closure (FIX-187/FIX-188/FIX-190/AUDIT-132/RISK-041)
**Date**: 2026-07-11

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined (semver) | ✅ 0.65.1 (PATCH: bug/evidence/hook/release-boundary corrections only) |
| 2 | Change list enumerated | ✅ FIX-187, FIX-188, FIX-190, AUDIT-132, RISK-041 |
| 3 | Change types marked | ✅ Fixed / Changed / Documentation-boundary correction |
| 4 | Release window | ✅ 2026-07-11 |
| 5 | Out-of-scope items explicit | ✅ No tag creation, no commit/push, no historical tag backfill, no 0.65.2/0.65.3 SKILL Loop Role or tag-gate implementation |

### Change inventory

- **FIX-187** — dual-root crash fix (commit `407b74c`), preserving DEC-096 PLUGIN_HOME vs HOST_PROJECT_ROOT separation.
- **FIX-188** — explicit `--project-root` override in `verify_workflow.py` + hook compatibility for `APPROVED_WITH_NOTES` review evidence.
- **FIX-190** — 0.65.0 release checklist / session snapshot evidence correction: archive integrity was pre-existing FAIL / non-blocking P2 at REL-053 review, not PASS.
- **AUDIT-132 / RISK-041** — post-0.55.3 quality audit and release-lineage risk captured as an explicit boundary for the 0.65.1 release package; risk remains open.
- **Version bump** — 0.65.0 → 0.65.1 across declaration files and e2e fixture pointers.

## 2. Version Consistency

| Item | Expected |
| --- | --- |
| Source SKILL frontmatter | 0.65.1 |
| Manifest | 0.65.1 |
| Claude/Codex/Zcode/Chrys plugin metadata | 0.65.1 |
| Claude marketplace metadata | 0.65.1 |
| package.json | 0.65.1 |
| Four source hooks `@version` | 0.65.1 |
| `verify_workflow.py` REQUIRED_SNIPPETS | 0.65.1 |
| E2E fixture SKILL + plan-tracker pointer | 0.65.1 |

## 3. Release Gate Evidence

Commands to execute before Coordinator handoff:

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync
python skills/software-project-governance/infra/verify_workflow.py check-hot-fact-source --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.65.1 --require-changelog
git diff --check
```

Expected interpretation:

- `check-version-consistency`, `check-projection-sync`, `check-hot-fact-source --fail-on-issues`, and `git diff --check` must PASS for this release package to be proposed.
- `check-release --version 0.65.1 --require-changelog` must be reported honestly. Pre-existing archive/tag/release-lineage/structural failures are not to be rewritten as green.

## 4. Release Decision Boundary

0.65.1 is prepared as a release package only. This document does **not** assert:

- a git tag exists;
- the release has been committed or pushed;
- official submission / marketplace approval exists;
- RISK-036, RISK-037, RISK-039, RISK-040, or RISK-041 is closed;
- 1.0.0 readiness is achieved;
- historical missing tags have been backfilled.

## 5. Review Handoff

Release Agent output must be reviewed by an independent Release Reviewer before Coordinator records release evidence. If review returns `APPROVED_WITH_NOTES`, hooks now recognize that status as approved review evidence; any `NEEDS_CHANGES` / `BLOCKED` status remains blocking.

## 6. E2E Fixture Pointer

- `project/e2e-test-project/skills/software-project-governance/SKILL.md` → `version: 0.65.1`
- `project/e2e-test-project/.governance/plan-tracker.md` → `工作流版本: 0.65.1`

## 7. No-overclaim boundaries

No git tag created. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK closure. No 1.0.0 readiness. Pre-existing archive/tag/release-lineage failures remain visible and must not be represented as a fully green release gate.
