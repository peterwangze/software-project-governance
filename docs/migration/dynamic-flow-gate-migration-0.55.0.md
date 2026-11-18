# Dynamic lifecycle migration preview

The preview introduced in 0.55.0 inventories a classic project's existing governance records. Run it against the project root.

```bash
python skills/software-project-governance/infra/verify_workflow.py dynamic-lifecycle-migration --target <path> --dry-run --fail-on-issues
```

`dynamic-flow-gate-migration` is an alias. With `--fail-on-issues`, an unusable input produces a JSON diagnostic and a nonzero exit code.

## Reading the result

- `workflow_model` reports the model inferred from the project tracker. Classic remains the default and dynamic migration requires explicit opt-in.
- `flow_units` reports existing units recorded in the project's optional `.governance/flow-unit-runtime.json`. A project without that file has `source: "none"`, a zero count and empty lanes. A runtime containing `{"flow_units":[]}` has a zero count and identifies the file as its source.
- Pre-schema runtime files can report unique unit IDs and project-defined lanes. Declared v1 and v2 runtimes are checked against their respective contracts. V2 units report their gate ID and can have an unassigned lane (`gate_lane: null`), which still counts as an observed unit. Unsupported versions and unreadable or invalid state block both preview and apply before any backup or repair.
- `evidence_preservation` records the SHA-256 of the same bytes used to read the tracker and count evidence rows. Missing or unreadable files and an evidence log without a parseable row appear in `blocked_checks`. Project decisions, risk IDs and release history belong to the project.
- `write_operations` is empty for a dry run. `READY_FOR_REVIEW` indicates that the inventory can be reviewed.

## Proposed units, application and rollback

For a target-derived migration plan, use the loop migration entry point. Its dry run includes `migration_plan` and `plan_hash` alongside the observed `flow_units`.

```bash
python skills/software-project-governance/infra/loop_migration.py --target <path> --dry-run
```

A write requires a separate explicit apply. The loop migration implementation validates the payload and protects host files with backups and integrity checks. The backup records whether the runtime existed and seals its exact bytes. `--rollback` restores them or removes the migration-created file when the backup proves prior absence. Recovery stops for ambiguous or damaged backups, including older backups that lack the runtime presence record. Explicit rollback replaces subsequent edits to the tracker, evidence log, and runtime with that snapshot and appends a rollback record. Automatic recovery of an interrupted apply also requires the live runtime to match the intended bytes and the evidence log to match the pre-migration snapshot. A preview alone leaves the project's files untouched.
