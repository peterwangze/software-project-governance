# Release Checklist - 0.66.3

**Version**: 0.66.3 (patch)
**Release**: docs-fix PATCH repairing 0.66.2 release docs content defects
**Date**: 2026-07-23
**Decision**: DEC-131 (user decision "0.66.3 PATCH 修复 docs")
**Candidate parent (B)**: `f859bb6f662ecc187dc5f49ba20b077f5b35d882` (released v0.66.2)

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined | PASS - 0.66.3 PATCH; docs-only content fix, no runtime API or logic change |
| 2 | Change list enumerated | PASS - release docs content fix (boundary wording) + version projection 0.66.2 -> 0.66.3 + CHANGELOG + candidate manifest |
| 3 | Independent code review available | N/A - this is a docs-fix PATCH following the standard `check-release --lineage-mode candidate/released` flow; no incident-compensation evidence gate applies |
| 4 | Candidate lineage boundary explicit | PASS - candidate mode does not require or prove a tag |
| 5 | Historical tag and official-marketplace overclaims excluded | PASS |

### Included

- Release docs content fix: the 0.66.2 release-checklist/feature-flags/rollback-plan boundary lines are rewritten to the proven 0.65.3 compact wording so that `check-release` boundary tokens and scoped-claim negation detection both pass.
- The fix adds the `RISK-036` boundary token (required by `check-release` `boundary_needles`) and uses the compact 0.65.3 negation wording so that `_line_has_scoped_claim_negation` returns True for each scoped claim phrase.
- Version declarations and e2e fixture pointers advance from 0.66.2 to 0.66.3 (M-set: plugins, marketplace, package.json, source/e2e SKILL frontmatter, manifest, plan-tracker, four source hooks, and the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`).
- `project/CHANGELOG.md` gains a 0.66.3 entry.

### Excluded

- No historical tag creation or backfill. Historical tag changes require a separate governance decision approving version-to-commit mappings.
- No zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-037/RISK-039/RISK-040/RISK-041 closure, or 1.0.0 production-ready claim.
- No runtime, logic, or product behavior change. This is a docs-fix PATCH only.

## 2. Version and SemVer

0.66.3 is a PATCH because it repairs release docs content defects and advances version metadata without changing plugin runtime APIs or introducing a breaking contract. Expected declarations are 0.66.3 in source SKILL, manifest, Claude/Codex/Zcode/Chrys plugin metadata, Claude marketplace metadata, package.json, four source hooks, and the two e2e fixture pointers.

## 3. Candidate Validation

Run before release review:

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.66.3 --require-changelog --lineage-mode candidate
```

Candidate mode intentionally does not require `v0.66.3` and is not evidence that the tag exists. The final release commit, local tag, and remote tag do not yet exist during package preparation. After the Coordinator creates and pushes them, rerun:

```text
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.66.3 --require-changelog --lineage-mode released --release-commit <commit> --skip-execution-gates
```

## 4. Test and Review Evidence

- The release docs boundary fix is verified against `_line_has_scoped_claim_negation` and the `check_release_docs_coverage` `boundary_needles`: every forbidden-positive-claim phrase returns True (negated), and the `RISK-036` token is present in each of the three 0.66.3 release docs.
- This package does not claim a full-suite-green state. Any pre-existing gate FAIL unrelated to the release docs content (e.g. the loop runtime claim gate) is reported honestly and is out of scope for this docs-fix PATCH.

## 5. Release Decision Boundary

This checklist prepares a candidate only. It does not commit, tag, push, approve marketplace submission, close risk, or make the final go/no-go decision. After tag creation and push, released lineage must verify the exact release commit locally and on the configured remote.

## 6. Rollback Verification

`docs/release/rollback-plan-0.66.3.md` defines full and partial rollback paths. After rollback, rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.
