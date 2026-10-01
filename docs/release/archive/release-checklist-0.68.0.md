# Release Checklist - 0.68.0

**Version**: 0.68.0 (minor)
**Release**: executable Loop Engine — persistent PARO state machine + production gate back-edge/fuse/escalation + restart-safe event log
**Date**: 2026-07-23
**Decision**: FEAT-005~007 + REL-060 (user decision "继续")
**Candidate parent (B)**: `59e08fc` (FEAT-007, on top of FEAT-006 `697f2bd` and FEAT-005 `c33799f`)

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined | PASS - 0.68.0 MINOR; executable Loop Engine: FEAT-005 (persistent PARO state machine + CAS), FEAT-006 (production gate back-edge/fuse/escalation + system-level fuse block), FEAT-007 (restart-safe append-only event log + dependency blocking + WIP); no breaking runtime API |
| 2 | Change list enumerated | PASS - FEAT-005~007 code commits + version projection 0.67.0 -> 0.68.0 + CHANGELOG + candidate manifest |
| 3 | Independent code review available | PASS - FEAT-005 APPROVE/0 blocker, FEAT-006 APPROVED_WITH_NOTES/0 blocker, FEAT-007 APPROVED_WITH_NOTES/0 blocker; 159 new tests, 0 P0 |
| 4 | Candidate lineage boundary explicit | PASS - candidate mode does not require or prove a tag |
| 5 | Historical tag and official-marketplace overclaims excluded | PASS |

### Included

- FEAT-005: persistent PARO state machine + CAS — `loop_paro_engine.py` `validate_transition` (6 legal + 3 terminal) + `apply_transition` CAS writer + `activate_unit` + `recover_state`; `flow_unit_runtime_v2.py` +257/0 `validate_loop_runtime_v2_with_transitions` (0.67.0 byte-frozen intact). CAS threading 12-thread 1-success/11-conflict 60x stable; fuse boundary >max_rounds. 61 new tests.
- FEAT-006: production gate back-edge/fuse/escalation + system-level fuse block — `loop_gate_processor.py` `process_gate_result` terminal processor + `loop_fuse_check` pure read + `collect_loop_fuse_issues`; `verify_workflow.py` +25/0 `check_release_readiness` fuse check (system-level block, not Coordinator advisory). End-to-end gate fail→back-edge→round→fuse→escalation→block. `loop_fuse_check` pure read CONFIRMED. 45 new tests.
- FEAT-007: restart-safe event log + dependency blocking + WIP — `loop_event_log.py` append-only JSONL event log (14 types, cross-process lock, monotonicity/legality checks); `loop_admission.py` dependency blocking + WIP budget (setup=1/inner=5/middle=2/outer=1); `loop_paro_engine.py` + `loop_gate_processor.py` additive event_log hook (state-first/event-second, backward compat). multi-process 4×100=400 0 loss win32, restart consistency CONFIRMED. 53 new tests.
- Version declarations and e2e fixture pointers advance from 0.67.0 to 0.68.0 (M-set: plugins, marketplace, package.json, source/e2e SKILL frontmatter, manifest, plan-tracker, four source hooks, and the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`).
- `project/CHANGELOG.md` gains a 0.68.0 entry.

### Excluded

- No zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-037/RISK-039/RISK-040/RISK-041/RISK-042 closure, or 1.0.0 production-ready claim.
- 0.68.0 does not close RISK-037/RISK-042 (external validation 0.69.0). Execution engine activates but runtime completeness requires 0.69.0 dogfood + external validation.

## 2. Version and SemVer

0.68.0 is a MINOR because it adds executable Loop Engine capability (persistent PARO state machine + production gate fuse + restart-safe event log) without changing existing plugin runtime APIs or introducing a breaking contract. Expected declarations are 0.68.0 in source SKILL, manifest, Claude/Codex/Zcode/Chrys plugin metadata, Claude marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, and the two e2e fixture pointers.

## 3. Candidate Validation

Run before release review:

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.68.0 --require-changelog --lineage-mode candidate
```

Candidate mode intentionally does not require `v0.68.0` and is not evidence that the tag exists. The final release commit, local tag, and remote tag do not yet exist during package preparation. After the Coordinator creates and pushes them, rerun:

```text
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.68.0 --require-changelog --lineage-mode released --release-commit <commit> --skip-execution-gates
```

## 4. Test and Review Evidence

- FEAT-005 Code Review: APPROVE, 0 blocker (CAS threading 12-thread 1-success/11-conflict 60x stable; fuse boundary >max_rounds); 61 new + 104 regression pass.
- FEAT-006 Code Review: APPROVED_WITH_NOTES, 0 blocker (`loop_fuse_check` pure read CONFIRMED, end-to-end gate fail→back-edge→round→fuse→escalation→block); 45 new + 101 regression pass.
- FEAT-007 Code Review: APPROVED_WITH_NOTES, 0 blocker (multi-process 4×100=400 0 loss win32, restart consistency CONFIRMED); 53 new + 146 regression pass.
- 159 new tests, 0 P0.
- The release docs boundary wording is verified against `_line_has_scoped_claim_negation` and the `check_release_docs_coverage` `boundary_needles`: every forbidden-positive-claim phrase returns True (negated), and the `RISK-036` token is present in each of the three 0.68.0 release docs.
- This package does not claim a full-suite-green state. Any pre-existing gate FAIL unrelated to 0.68.0 (e.g. the loop runtime claim gate, RISK-037/042) is reported honestly and is out of scope for this MINOR.

## 5. Release Decision Boundary

This checklist prepares a candidate only. It does not commit, tag, push, approve marketplace submission, close risk, or make the final go/no-go decision. After tag creation and push, released lineage must verify the exact release commit locally and on the configured remote.

## 6. Rollback Verification

`docs/release/rollback-plan-0.68.0.md` defines full and partial rollback paths. After rollback, rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.
