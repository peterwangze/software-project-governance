# Python Game Dynamic Lifecycle Validation Report - 0.55.0

Date: 2026-06-20
Task: VAL-005
Target: `D:\AI\agent\claude\coding\python_game`
Scope: real external validation focused on dynamic lifecycle / flow-unit migration preview for the Python game project.

This report records a conservative validation run against the real `python_game` working copy. The dynamic lifecycle migration preview is **READY_FOR_REVIEW** and read-only, but the installed-state external validation remains **FAIL / PARTIAL diagnostic only** because the target native `CLAUDE.md` still contains a repo-local workflow path assumption.

No external validation full PASS. No project migration. No `dynamic-flow-gate` default activation. No official approval. No marketplace approval. No Codex Desktop lifecycle PASS. No RISK-036 closure. No RISK-037 closure. No 1.0.0 readiness.

## Commands

| Command | Exit | Meaning |
| --- | --- | --- |
| `python skills/software-project-governance/infra/verify_workflow.py dynamic-lifecycle-migration --target D:/AI/agent/claude/coding/python_game --dry-run --fail-on-issues` | 0 | Dry-run migration preview completed with `status=READY_FOR_REVIEW`, `validation_issues=[]`, and `write_operations=[]`. |
| `python skills/software-project-governance/infra/verify_workflow.py external-project-validation --target D:/AI/agent/claude/coding/python_game --fail-on-issues --timeout 180` | 1 | Installed-state validation completed and failed under `--fail-on-issues` because target-native diagnostics found a repo-local workflow home assumption in `CLAUDE.md:32`. |

## Dynamic Lifecycle Preview Result

| Field | Result |
| --- | --- |
| Current workflow model | `classic-phase-gate` |
| Target preview model | `dynamic-flow-gate` |
| Active/default mode after preview | `classic-phase-gate` remains active/default |
| Dynamic mode | opt-in only |
| Write operations | `[]` |
| Status | `READY_FOR_REVIEW` |
| Validation issues | `[]` |

The preview used the lifecycle registry `python_game_10_chapters` example and produced 10 flow units:

| Lane | Flow units |
| --- | --- |
| `released` | `game.chapter.01` |
| `testing` | `game.chapter.02` |
| `development` | `game.chapter.03` |
| `backlog` | `game.chapter.04` through `game.chapter.10` |

The preview preserved existing target evidence sources:

| Artifact | Exists | Preserved | SHA-256 |
| --- | --- | --- | --- |
| `.governance/plan-tracker.md` | true | true | `c930d47149a7c4f291168bb579694b5ef05aebf9764fd60a3d3c7dcc4270680b` |
| `.governance/evidence-log.md` | true | true | `1756bb97cf6a25f36a61317fb011f0e963f4e25a022042a7cebad8d29d7e1cd8` |

The target evidence log contained 33 evidence rows during the preview.

## Installed-State Diagnostics

| Diagnostic | Result |
| --- | --- |
| `CLAUDE.md:32` hardcodes repo-local `skills/software-project-governance/` as workflow home | FAIL |
| `.git/hooks/pre-commit` matches canonical source `@version=0.54.1` | PASS |
| `.git/hooks/commit-msg` matches canonical source `@version=0.54.1` | PASS |
| `.git/hooks/post-commit` matches canonical source `@version=0.54.1` | PASS |

The temporary workspace command matrix still passed:

| Command | Exit |
| --- | --- |
| `status` | 0 |
| `gate G1` | 0 |
| `governance-context --fail-on-issues` | 0 |
| `check-governance --fail-on-issues` | 0 |

These command results show that the isolated harness workspace can run the governance surface. They do not override the target-native `CLAUDE.md` issue and do not constitute external validation full PASS.

## Target Mutation Boundary

The target repository had a pre-existing local change:

```text
 M .claude/settings.local.json
```

The validation commands were read-only for the target. The same target status was observed after the validation commands, and no target file was intentionally modified by this validation.

## VAL-005 Decision

VAL-005 is **conservatively complete** as an external dynamic lifecycle validation archive, not as a full external installed-state PASS.

The validation proves that:

- the dry-run migration preview can read real `python_game` governance data;
- existing plan/evidence artifacts are preserved and hash-recorded;
- a 10-chapter dynamic lifecycle lane model can represent released, testing, development, and backlog chapters simultaneously;
- the preview remains read-only and requires future review before any write path;
- the external installed-state harness can still detect target-native entry-file drift.

The validation does **not** prove:

- project migration completed;
- `dynamic-flow-gate` is active/default;
- external validation full PASS;
- `python_game` installed native entry files are clean;
- official approval or marketplace approval;
- Codex Desktop lifecycle PASS;
- RISK-036 or RISK-037 closure;
- 1.0.0 production readiness.

## Remaining Next Step

Fix the `python_game` native entry file so it no longer hardcodes repo-local workflow home paths, then rerun installed-state validation before claiming full external PASS or using `python_game` as RISK-037 closure evidence.
