# Release Checklist - 0.71.0

**Version**: 0.71.0 (minor)
**Release**: systematic UX fixes for entry/loop/task-planning (FIX-222~229) — bootstrap entry determinism + behavior protocol dependency-aware recommendation + review deterministic triggers + task planning system
**Date**: 2026-07-27
**Decision**: FIX-222~229 (REL-063, user authorized "继续按照当前工作流要求往前推进")
**Candidate parent (B)**: `da1ac77` (FIX-225~229 task planning system commit, on top of `f81060a` FIX-222~224 bootstrap/behavior/review and `c069d89` docs)

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined | PASS - 0.71.0 MINOR; systematic UX fixes for entry/loop/task-planning (FIX-222~229): bootstrap entry 3-method plugin_home location (eliminated chicken-and-egg), task-completion dependency analysis → recommend next → AskUserQuestion, review deterministic triggers T1-T4, plan-tracker 依赖 column + workflow_model template, task-priority-analysis tool (DAG parser + unblocked computation + cycle detection, 57 tests), behavior-protocol dependency analysis replaces mechanical highest-priority, change-control substantiated, change-impact-checklist task-level analysis; no breaking runtime API |
| 2 | Change list enumerated | PASS - FIX-222~229 code commits + version projection 0.70.0 -> 0.71.0 + CHANGELOG + candidate manifest |
| 3 | Independent code review available | PASS - DEC-134 authorized FIX-222~229; 3 analysis reports (sysgap-047/audit-140/audit-141) root-caused the gaps before fixing; task_priority.py 57 tests cover DAG parsing / unblocked computation / cycle detection / CLI; check-version-consistency PASS (13 files), check-projection-sync PASS (13 projections) |
| 4 | Candidate lineage boundary explicit | PASS - candidate mode does not require or prove a tag |
| 5 | Historical tag and official-marketplace overclaims excluded | PASS |

### Included

- FIX-222: AGENTS.md bootstrap — 3 methods to locate plugin_home (platform skill `file:` path derivation / dev fallback / explicit param); all `<plugin_home>` references re-pointed to "see bootstrap first action above", eliminating the chicken-and-egg (needing plugin_home to run the script that obtains plugin_home). Analysis report: `docs/requirements/sysgap-047-entry-bootstrap-paradox-0.71.0.md`.
- FIX-223: `behavior-protocol.md` M7.4 step 6 + `interaction-boundary.md:217` — task-completion now runs dependency analysis (`task-priority-analysis`) → recommends next unblocked task → presents via AskUserQuestion → must not end directly (replaces mechanical "take highest-priority incomplete"). Analysis report: `docs/requirements/audit-140-loop-runtime-wiring-gap-0.71.0.md`.
- FIX-224: M7.4 step 4.6 — T1-T4 deterministic review re-review triggers (T1 NEEDS_CHANGE & round<3 → MUST spawn same Reviewer re-review, no "do you want re-review" prompt; T2 APPROVED/APPROVED_WITH_NOTES → terminal pass state with `unresolved_blockers=0`; T3 BLOCKED → escalation terminal; T4 round>3 still NEEDS_CHANGE → MUST convert to BLOCKED, no infinite loop).
- FIX-225: `core/templates/plan-tracker.md` upgraded — `workflow_model`/`permission_mode` config fields + `依赖` column upgraded from free text to machine-parseable format (comma-separated task IDs) + dependency format spec.
- FIX-226: `infra/task_priority.py` (861 lines) pure DAG parser — `parse_task_dependencies` (parses task table to DAG, distinguishes task-family vs cross-entity references per FIX-171 precedent) + `compute_unblocked_tasks` (computes executable tasks with no incomplete dependencies) + cycle detection (avoids circular-dependency deadlock) + `format_report`. `verify_workflow.py` adds `task-priority-analysis` CLI subcommand (thin entry, logic in pure module). 57 tests.
- FIX-227: behavior-protocol M7.4 step 6 + interaction-boundary.md:217 dependency analysis replaces mechanical highest-priority (co-committed with FIX-223; this FIX explicitly registers the behavior-protocol revision scope).
- FIX-228: `change-control` reference upgraded from 2-line stub to substantive steps — change proposal → dependency analysis (run `task-priority-analysis`, check blocking/blocked) → priority determination (P0/P1/P2 against in-flight tasks and version dependency chains) → conflict check (same-file edits as in-flight tasks) → version adaptation → create task → execute. Product code changes MUST run full dependency analysis + priority + conflict check.
- FIX-229: `change-impact-checklist.md` new section 2b task-level dependency/conflict analysis — product code changes must include task-level dependency graph analysis and cross-task conflict check in impact assessment.
- Version declarations and e2e fixture pointers advance from 0.70.0 to 0.71.0 (M-set: plugins, marketplace, package.json, source/e2e SKILL frontmatter, manifest, plan-tracker, four source hooks, and the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`).
- `project/CHANGELOG.md` gains a 0.71.0 entry.

### Excluded

- No zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039/RISK-040/RISK-041 closure, or 1.0.0 production-ready claim.
- 0.71.0 does not close RISK-036/RISK-039/RISK-040/RISK-041. RISK-039 (architecture-degradation guard) closure still requires ArchGuard validation in an external host project, source/projection double-write elimination, and technical-debt registration closure; RISK-036 requires official marketplace operations (Codex Desktop marketplace E2E / official submission package) that cannot be completed locally.

## 2. Version and SemVer

0.71.0 is a MINOR because it adds the systematic UX fixes (bootstrap entry determinism, dependency-aware task-completion recommendation, deterministic review re-review triggers, and the task planning system: plan-tracker dependency structure + task-priority-analysis tool + substantiated change-control) without changing existing plugin runtime APIs or introducing a breaking contract. Expected declarations are 0.71.0 in source SKILL, manifest, Claude/Codex/Zcode/Chrys plugin metadata, Claude marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, and the two e2e fixture pointers.

## 3. Candidate Validation

Run before release review:

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.71.0 --require-changelog --lineage-mode candidate
```

Candidate mode intentionally does not require `v0.71.0` and is not evidence that the tag exists. The final release commit, local tag, and remote tag do not yet exist during package preparation. After the Coordinator creates and pushes them, rerun:

```text
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.71.0 --require-changelog --lineage-mode released --release-commit <commit> --skip-execution-gates
```

## 4. Test and Review Evidence

- DEC-134 authorized FIX-222~229; EVD-852.
- 3 independent analysis reports (sysgap-047 / audit-140 / audit-141) root-caused the gaps before fixing, following the governance "analysis-first" principle.
- `task_priority.py`: 57 tests cover DAG parsing / unblocked computation / cycle detection / CLI, all PASS.
- `check-version-consistency` PASS (13 version declarations consistent); `check-projection-sync` PASS (13 projections synchronized).
- The release docs boundary wording is verified against `_line_has_scoped_claim_negation` and the `check_release_docs_coverage` `boundary_needles`: every forbidden-positive-claim phrase returns True (negated), and the `RISK-036` token is present in each of the three 0.71.0 release docs.
- This package does not claim a full-suite-green state. Any pre-existing gate FAIL unrelated to 0.71.0 is reported honestly and is out of scope for this MINOR.

## 5. Release Decision Boundary

This checklist prepares a candidate only. It does not commit, tag, push, approve marketplace submission, close risk, or make the final go/no-go decision. After tag creation and push, released lineage must verify the exact release commit locally and on the configured remote.

## 6. Rollback Verification

`docs/release/rollback-plan-0.71.0.md` defines full and partial rollback paths. After rollback, rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.

## No-overclaim Boundaries

This candidate does not create or prove `v0.71.0`, does not backfill historical tags, and does not close RISK-036, RISK-039, RISK-040, or RISK-041. 0.71.0 does not close RISK-036/RISK-039/RISK-040/RISK-041 (official marketplace operations, ArchGuard external validation, entry determinism host validation, and release-lineage historical-tag disposition each have independent closure criteria not yet satisfied). No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039/RISK-040/RISK-041 closure, or 1.0.0 production-ready claim is made.
