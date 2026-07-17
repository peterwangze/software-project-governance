# Loop Engineering Runtime Contract Migration - 0.66.1

## Scope

0.66.1 contains the existing migration writer. It does not introduce or
activate the planned Loop Engineering runtime contract. The canonical
flow-unit runtime contract remains visibility-v1 and continues to preserve
the classic lifecycle default.

## Containment Behavior

`loop-engineering-migration --apply` and the legacy dynamic-lifecycle apply
alias now build the proposed runtime completely in memory and validate it
with the same canonical validator used by `check-flow-unit-runtime`.

The current Loop Engineering payload is not valid visibility-v1 data. Apply
therefore returns a non-zero result with `applied=false` and structured
`validation_issues` before creating a backup, runtime file, or evidence row.
The contract is not widened and the payload is not disguised as a classic or
dynamic visibility record.

## Transaction Recovery

For a future payload that passes the canonical validator, runtime and evidence
updates form a compensating transaction. Runtime is committed first. If the
evidence commit fails, the prior runtime and evidence bytes are restored. An
originally absent runtime is removed. If compensation itself fails, the
command returns `BLOCKED` and retains a recovery journal plus immutable backup
material under the migration archive directory.

The commit is not considered complete until runtime and evidence are read back
from disk and revalidated. A readback mismatch or post-write validation failure
triggers the same compensation path. If the recovery journal itself cannot be
persisted, the structured `BLOCKED` result reports that failure without
claiming a journal exists and identifies the still-available backup material.

Retry only after a complete compensation or after following the retained
journal. A compensated retry appends the migration evidence exactly once.

## Operator Verification

```text
python skills/software-project-governance/infra/verify_workflow.py loop-engineering-migration --target <project> --apply
python skills/software-project-governance/infra/verify_workflow.py check-flow-unit-runtime --fixture <project> --fail-on-issues
```

Until the later runtime-contract version is released, the first command is
expected to stop before writes with validation diagnostics. Do not treat that
containment result as a completed migration.

Standalone and adapter dry-run commands use the same preview authority. An
invalid target therefore returns diagnostics and a non-zero standalone exit.

## Boundaries

- No lifecycle default changes.
- No Loop Engineering execution-engine activation.
- No relaxation or duplication of visibility-v1 validation.
- No RISK-037 or RISK-042 closure.
- Loop Engineering remains experimental scaffolding in 0.66.1. Persisted
  back-edges, per-unit loop counters, tier fuses, PARO transitions and
  automatic escalation are planned for 0.68.0 and are not active now.
- Release validation includes the fail-closed `check-loop-runtime-claims`
  command. Missing policy/authority, parser ambiguity, incomplete inventory,
  historical notice drift, and unsupported affirmative claims block release.
