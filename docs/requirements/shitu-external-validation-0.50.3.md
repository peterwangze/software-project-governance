# Shitu External Validation Report - 0.50.3

Date: 2026-06-14
Task: VAL-003
Target: `D:\AI\agent\claude\coding\android\shitu`
Scope: real external installed-state validation for the shitu project after FIX-134 diagnostics.

This report records a conservative validation run against the real shitu working copy. The result is **FAIL / PARTIAL diagnostic only** because the enhanced external-project validation harness found target-native installed-state issues.

No external validation full PASS. No official approval. No marketplace approval. No Codex Desktop lifecycle PASS. No RISK-036 closure. No 1.0.0 readiness.

## Command

| Command | Exit | Meaning |
| --- | --- | --- |
| `python skills/software-project-governance/infra/verify_workflow.py external-project-validation --target D:/AI/agent/claude/coding/android/shitu --fail-on-issues --timeout 180` | 1 | The harness completed and failed under `--fail-on-issues` because target-native diagnostics found installed-state problems. |

## Target Mutation Check

The target repository status was checked before and after the validation run. It remained unchanged:

```text
 M .claude/settings.local.json
?? .claude/worktrees/agent-a0658b1ef946d3a0d/
?? .claude/worktrees/agent-a18a0fd0b5e6d8bc2/
?? .claude/worktrees/agent-a4bd7ea3cb72cce41/
?? .claude/worktrees/agent-af740365b994a53e5/
```

Relevant `CLAUDE.md` and installed hook file hashes and mtimes were unchanged before and after the run:

- `CLAUDE.md`
- `.git/hooks/pre-commit`
- `.git/hooks/commit-msg`
- `.git/hooks/post-commit`

The validation harness remained read-only for the target.

## Target-Native Diagnostics

| Diagnostic | Result |
| --- | --- |
| `CLAUDE.md:44` references repo-local `skills/software-project-governance/` as the workflow home. | FAIL |
| `CLAUDE.md:206` references repo-local `python skills/.../verify_workflow.py` command usage. | FAIL |
| `CLAUDE.md:100` references repo-local `cp skills/.../hooks...` hook install command. | FAIL |
| `.git/hooks/pre-commit` installed hook has `@version=unknown`; expected `0.50.2`. | FAIL |
| `.git/hooks/pre-commit` uses legacy `COMMIT_EDITMSG` / `GOV_COMMIT_MSG` as semantic message sources. | FAIL |
| `.git/hooks/commit-msg` installed hook has `@version=0.33.0`; expected `0.50.2`. | FAIL |
| `.git/hooks/post-commit` installed hook has `@version=unknown`; expected `0.50.2`. | FAIL |

## Temporary Workspace Command Matrix

The harness-created temporary workspace checks all exited 0:

| Command | Exit |
| --- | --- |
| `status` | 0 |
| `gate G1` | 0 |
| `governance-context --fail-on-issues` | 0 |
| `check-governance --fail-on-issues` | 0 |

These successful temporary-workspace checks show that the harness workspace path was healthy. They do not override the target-native diagnostics above and do not constitute a full external PASS.

## Current VAL-003 Decision

VAL-003 is **not a full PASS**.

The validation proves that:

- the enhanced FIX-134 harness can inspect a real external target without mutating the target;
- the temporary workspace governance command matrix can complete cleanly;
- the harness detected real shitu target-native issues in entry-file assumptions and installed hook drift.

The validation does **not** prove:

- the shitu installed state is ready;
- target-native entry files are aligned with installed/global runtime behavior;
- installed hooks are current or free of stale commit-message source behavior;
- official submission or marketplace approval;
- Codex Desktop lifecycle PASS;
- RISK-036 closure;
- 1.0.0 production readiness.

## Remaining Next Step

Fix and update the shitu native entry file assumptions and installed hooks, then rerun VAL-003 against `D:\AI\agent\claude\coding\android\shitu`.

RISK-036 remains open until external validation reaches the acceptance boundary defined by governance.
