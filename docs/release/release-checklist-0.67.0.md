# Release Checklist - 0.67.0

**Version**: 0.67.0 (minor)
**Release**: canonical Loop Runtime Contract + shared migration planner + decomposition confirmation
**Date**: 2026-07-23
**Decision**: DEC-104 + FEAT-002~004 + REL-059 (user decision "继续")
**Candidate parent (B)**: `4275e22` (FEAT-004, on top of FEAT-003 `2e79e5f` and FEAT-002 `b628a54`)

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined | PASS - 0.67.0 MINOR; canonical Loop Runtime Contract (FEAT-002), shared migration planner (FEAT-003), decomposition confirmation (FEAT-004); no breaking runtime API |
| 2 | Change list enumerated | PASS - FEAT-002~004 code commits + version projection 0.66.3 -> 0.67.0 + CHANGELOG + candidate manifest |
| 3 | Independent code review available | PASS - FEAT-002 APPROVED_WITH_NOTES/0 blocker, FEAT-003 APPROVED/0 blocker, FEAT-004 APPROVED_WITH_NOTES/0 blocker; 104 new tests, 0 P0 |
| 4 | Candidate lineage boundary explicit | PASS - candidate mode does not require or prove a tag |
| 5 | Historical tag and official-marketplace overclaims excluded | PASS |

### Included

- FEAT-002: canonical Loop Runtime Contract — `core/loop-runtime-contract.json` v2 schema + `flow_unit_runtime_v2.py` validator (452 lines); `flow_unit_runtime.py` v1 byte-frozen containment boundary (FIX-195 intact), +76 lines version routing. writer/validator/reader/rollup/health share a single contract and schema version; eliminates workflow_model, gate state, status source, and rollup field drift. v1/v2 drift parity 9/9 match, no regression. 40 tests pass.
- FEAT-003: shared migration planner + immutable plan hash — pure `build_migration_plan()` function (purity 16-thread CONFIRMED); `MigrationPlan` frozen/immutable; `plan_hash` = 8 structural-field SHA-256 NFC; dry-run and apply serialize the same plan, apply only validates and executes that plan; same target's unit IDs/count/project_type/gate schema must agree. FIX-195 containment byte-intact. 28+68 regression pass.
- FEAT-004: decomposition confirmation + canonical initial gate state — `confirm_decomposition` full logic (candidate validation + operator confirmation + hash recompute); `plan_to_payload` produces canonical initial state (dormant/pending gate/example-fixture guard); heuristic derivation stays advisory; dormant/example-data-only cannot masquerade as active (dormant-as-active is unrepresentable). 36+96 regression pass.
- Version declarations and e2e fixture pointers advance from 0.66.3 to 0.67.0 (M-set: plugins, marketplace, package.json, source/e2e SKILL frontmatter, manifest, plan-tracker, four source hooks, and the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`).
- `project/CHANGELOG.md` gains a 0.67.0 entry.

### Excluded

- No historical tag creation or backfill. Historical tag changes require a separate governance decision approving version-to-commit mappings.
- No zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-037/RISK-039/RISK-040/RISK-041/RISK-042 closure, or 1.0.0 production-ready claim.
- 0.67.0 does not activate execution engine; RISK-037 remains open; RISK-042 remains open. The runtime execution engine is scheduled for 0.68.0.

## 2. Version and SemVer

0.67.0 is a MINOR because it adds executable canonical contract / planner / decomposition-confirmation capability without changing existing plugin runtime APIs or introducing a breaking contract. Expected declarations are 0.67.0 in source SKILL, manifest, Claude/Codex/Zcode/Chrys plugin metadata, Claude marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, and the two e2e fixture pointers.

## 3. Candidate Validation

Run before release review:

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.67.0 --require-changelog --lineage-mode candidate
```

Candidate mode intentionally does not require `v0.67.0` and is not evidence that the tag exists. The final release commit, local tag, and remote tag do not yet exist during package preparation. After the Coordinator creates and pushes them, rerun:

```text
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.67.0 --require-changelog --lineage-mode released --release-commit <commit> --skip-execution-gates
```

## 4. Test and Review Evidence

- FEAT-002 Code Review: APPROVED_WITH_NOTES, 0 blocker; 40 tests pass.
- FEAT-003 Code Review: APPROVED, 0 blocker (purity 16-thread CONFIRMED, FIX-195 containment byte-intact); 28+68 regression pass.
- FEAT-004 Code Review: APPROVED_WITH_NOTES, 0 blocker; 36+96 regression pass.
- 104 new tests, 0 P0. preview/apply plan hash identical, validator PASS before and after apply; two units may hold different gate/phase.
- The release docs boundary wording is verified against `_line_has_scoped_claim_negation` and the `check_release_docs_coverage` `boundary_needles`: every forbidden-positive-claim phrase returns True (negated), and the `RISK-036` token is present in each of the three 0.67.0 release docs.
- This package does not claim a full-suite-green state. Any pre-existing gate FAIL unrelated to 0.67.0 (e.g. the loop runtime claim gate, RISK-037/042) is reported honestly and is out of scope for this MINOR.

## 5. Release Decision Boundary

This checklist prepares a candidate only. It does not commit, tag, push, approve marketplace submission, close risk, or make the final go/no-go decision. After tag creation and push, released lineage must verify the exact release commit locally and on the configured remote.

## 6. Rollback Verification

`docs/release/rollback-plan-0.67.0.md` defines full and partial rollback paths. After rollback, rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.
