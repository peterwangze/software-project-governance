# Python Game External Validation Report - 0.50.3

Date: 2026-06-15
Task: VAL-004
Target: `D:\AI\agent\claude\coding\python_game`
Scope: real external installed-state validation for the python_game project after FIX-134 diagnostics.

This report records a conservative validation run against the real python_game working copy. The result is **FAIL / PARTIAL diagnostic only** because the enhanced external-project validation harness found installed hook drift in the target project.

No external validation full PASS. No official approval. No marketplace approval. No Codex Desktop lifecycle PASS. No RISK-036 closure. No 1.0.0 readiness.

## Command

| Command | Exit | Meaning |
| --- | --- | --- |
| `python skills/software-project-governance/infra/verify_workflow.py external-project-validation --target D:/AI/agent/claude/coding/python_game --fail-on-issues --timeout 180` | 1 | The harness completed and failed under `--fail-on-issues` because target-native diagnostics found installed hook drift. |

The validation was run with `PYTHONDONTWRITEBYTECODE=1` to avoid `.pyc` writes during the read-only check.

## Target Mutation Check

The target repository status was checked before and after the validation run. It remained unchanged:

```text
 M .claude/settings.local.json
 M .governance/evidence-log.md
 M .governance/plan-tracker.md
 M .governance/session-snapshot.md
 M kingdom_war
```

Relevant native entry and installed hook file hashes and mtimes were unchanged before and after the run:

- `CLAUDE.md`: `1e79952c82771035f6ef73c4d10de73ccd663789c38bbdfea15ad9b427ea0f7f`, `2026-06-12T12:47:23.8762898Z`
- `.git/hooks/pre-commit`: `d75f2604fd909682b2c77be4b26dd526e1aa76ea13530658aaf9ab62ad23a72b`, `2026-06-12T12:40:52.1963821Z`
- `.git/hooks/commit-msg`: `a1632c3493521ec618fe1e8a6ab6d5ab25a984f72bf851bd8276db009c9e77b9`, `2026-06-12T12:40:52.2668631Z`
- `.git/hooks/post-commit`: `47bf76f6bb5a8867f0c861b878f18cf6b7fe5b75c023dbd3cdca84bff7ae9464`, `2026-06-12T12:40:52.3069774Z`

The following optional native entry files were not present and remained absent:

- `AGENTS.md`
- `GEMINI.md`
- `.cursorrules`
- `.cursor/rules`
- `.github/copilot-instructions.md`

The validation harness remained read-only for the target.

## Target-Native Diagnostics

| Diagnostic | Result |
| --- | --- |
| `CLAUDE.md` native entry does not contain repo-local workflow path assumptions. | PASS |
| `.git/hooks/pre-commit` installed hook has `@version=0.49.0`; expected `0.50.2`. | FAIL |
| `.git/hooks/pre-commit` uses legacy `COMMIT_EDITMSG` / `GOV_COMMIT_MSG` as semantic message sources. | FAIL |
| `.git/hooks/pre-commit` self-upgrade source hardcodes repo-local `skills/software-project-governance/infra/hooks`. | FAIL |
| `.git/hooks/commit-msg` installed hook has `@version=0.49.0`; expected `0.50.2`. | FAIL |
| `.git/hooks/post-commit` installed hook has `@version=0.49.0`; expected `0.50.2`. | FAIL |

## Temporary Workspace Command Matrix

The harness-created temporary workspace checks all exited 0:

| Command | Exit |
| --- | --- |
| `status` | 0 |
| `gate G1` | 0 |
| `governance-context --fail-on-issues` | 0 |
| `check-governance --fail-on-issues` | 0 |

These successful temporary-workspace checks show that the harness workspace path was healthy. They do not override the target-native hook diagnostics above and do not constitute a full external PASS.

## Current VAL-004 Decision

VAL-004 is **not a full PASS**.

The validation proves that:

- the enhanced FIX-134 harness can inspect the python_game target without mutating it;
- the python_game native `CLAUDE.md` no longer shows repo-local workflow path assumptions;
- the temporary workspace governance command matrix can complete cleanly;
- the harness detected real installed hook drift in the target project.

The validation does **not** prove:

- the python_game installed hooks are current;
- the python_game installed hooks are free of stale commit-message source behavior;
- official submission or marketplace approval;
- Codex Desktop lifecycle PASS;
- RISK-036 closure;
- 1.0.0 production readiness.

## Remaining Next Step

Update the python_game installed hooks to the current workflow hook semantics, then rerun VAL-004 against `D:\AI\agent\claude\coding\python_game`.

RISK-036 remains open until external validation reaches the acceptance boundary defined by governance.
