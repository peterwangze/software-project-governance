# Shitu Dynamic Lifecycle Validation Report - 0.55.0

Date: 2026-06-20
Task: VAL-006
Target: `D:\AI\agent\claude\coding\android\shitu`
Scope: real external validation against a non-game Android/Kotlin project to test dynamic lifecycle migration preview and project-type generalization boundaries.

This report records a conservative validation run against the real `shitu` working copy. The dynamic lifecycle migration preview is **READY_FOR_REVIEW** and read-only for a non-game target with existing governance data, but project-type preset generalization is **PARTIAL** because the preview still uses the registry `python_game_10_chapters` example flow units instead of deriving Android/mobile-app specific flow units from the target. Installed-state external validation also remains **FAIL / PARTIAL diagnostic only** because the target native entry and installed hooks still contain drift.

No external validation full PASS. No project migration. No `dynamic-flow-gate` default activation. No claim that non-game preset generalization is complete. No official approval. No marketplace approval. No Codex Desktop lifecycle PASS. No RISK-036 closure. No RISK-037 closure. No 1.0.0 readiness.

## Commands

| Command | Exit | Meaning |
| --- | --- | --- |
| `python skills/software-project-governance/infra/verify_workflow.py dynamic-lifecycle-migration --target D:/AI/agent/claude/coding/android/shitu --dry-run --fail-on-issues` | 0 | Dry-run migration preview completed with `status=READY_FOR_REVIEW`, `validation_issues=[]`, and `write_operations=[]`. |
| `python skills/software-project-governance/infra/verify_workflow.py external-project-validation --target D:/AI/agent/claude/coding/android/shitu --fail-on-issues --timeout 180` | 1 | Installed-state validation completed and failed under `--fail-on-issues` because target-native diagnostics found entry-file path assumptions and installed hook drift. |

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

The preview preserved existing target evidence sources:

| Artifact | Exists | Preserved | SHA-256 |
| --- | --- | --- | --- |
| `.governance/plan-tracker.md` | true | true | `e4131a1206578aa5d91f3f500763235bb8a082c05e3c64765e4eace64742777a` |
| `.governance/evidence-log.md` | true | true | `59c11f17dd2c88447ac500fd9c1f22a0d245cf3967396071e21242ed980eaacd` |

The target evidence log contained 89 evidence rows during the preview.

## Preset Generalization Boundary

The run confirms that the migration preview can operate read-only on a non-game target and preserve its existing governance facts. It does **not** prove non-game preset generalization is complete:

| Observation | Result |
| --- | --- |
| Target project type | Android/Kotlin app, not game |
| Target governance artifacts | Present and preserved |
| Preview flow-unit source | `lifecycle-registry example python_game_10_chapters` |
| Preview lanes | `game.chapter.01` released, `game.chapter.02` testing, `game.chapter.03` development, `game.chapter.04` through `game.chapter.10` backlog |
| Non-game target-derived flow units | Not produced by the current preview |
| Conclusion | Non-game dry-run compatibility is demonstrated; non-game preset generalization remains partial |

This is acceptable as a conservative validation archive, but it is not enough to close RISK-037 or claim complete dynamic Flow-Gate readiness.

## Installed-State Diagnostics

| Diagnostic | Result |
| --- | --- |
| `CLAUDE.md:44` hardcodes repo-local `skills/software-project-governance/` as workflow home | FAIL |
| `CLAUDE.md:206` hardcodes repo-local `python skills/software-project-governance/infra/verify_workflow.py` verify command | FAIL |
| `CLAUDE.md:100` hardcodes repo-local hook install command | FAIL |
| `.git/hooks/pre-commit` has `@version=unknown`; expected `0.54.1` | FAIL |
| `.git/hooks/pre-commit` still uses legacy `COMMIT_EDITMSG` / `GOV_COMMIT_MSG` semantic message source | FAIL |
| `.git/hooks/commit-msg` has `@version=0.33.0`; expected `0.54.1` | FAIL |
| `.git/hooks/post-commit` has `@version=unknown`; expected `0.54.1` | FAIL |

The temporary workspace command matrix still passed:

| Command | Exit |
| --- | --- |
| `status` | 0 |
| `gate G1` | 0 |
| `governance-context --fail-on-issues` | 0 |
| `check-governance --fail-on-issues` | 0 |

These command results show that the isolated harness workspace can run the governance surface. They do not override the target-native issues and do not constitute external validation full PASS.

## Target Mutation Boundary

The target repository had pre-existing local changes:

```text
 M .claude/settings.local.json
?? .claude/worktrees/
```

The validation commands were read-only for the target. The same target status was observed after the validation commands, and no target file was intentionally modified by this validation.

## VAL-006 Decision

VAL-006 is **conservatively complete** as a non-game external validation archive, not as a full preset generalization PASS.

The validation proves that:

- the dry-run migration preview can run against a real non-game target with existing governance data;
- existing plan/evidence artifacts are preserved and hash-recorded;
- the preview remains read-only and requires future review before any write path;
- the external installed-state harness can still detect target-native entry-file and installed hook drift.

The validation does **not** prove:

- non-game target-derived flow units are generated;
- project-type preset generalization is complete;
- project migration completed;
- `dynamic-flow-gate` is active/default;
- external validation full PASS;
- `shitu` installed native entry files or hooks are clean;
- official approval or marketplace approval;
- Codex Desktop lifecycle PASS;
- RISK-036 or RISK-037 closure;
- 1.0.0 production readiness.

## Remaining Next Step

Future work should make the migration preview derive flow units and gate lanes from non-game project types such as mobile apps, then rerun validation on `shitu` after native entry assumptions and installed hooks are updated.
