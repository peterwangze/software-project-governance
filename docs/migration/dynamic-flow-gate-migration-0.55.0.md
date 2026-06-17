# Dynamic Flow-Gate Migration Guide 0.55.0

## Purpose

This guide defines the verifiable preview path from `classic-phase-gate` to `dynamic-flow-gate` for 0.55.0. It is a migration planning and compatibility guide only. It does not perform migration writes, does not change the active/default lifecycle mode, and does not claim external validation or 1.0.0 readiness.

## Compatibility Boundary

- `classic-phase-gate remains active/default` for existing projects and new installs.
- `dynamic-flow-gate is opt-in`; no project is migrated by default.
- A classic-only project remains valid when it has a readable `.governance/plan-tracker.md` and `.governance/evidence-log.md`.
- `plan-tracker is preserved`; the preview records its hash and never rewrites it.
- `evidence-log is preserved`; the preview records its hash and never rewrites it.
- `dry-run is read-only`; the command prints a structured preview and leaves target files untouched.
- The preview does not close RISK-036.
- The preview does not close RISK-037.
- The preview does not claim 1.0.0 production-ready.

## Command

Run the dry-run preview against a fixture or project root:

```bash
python skills/software-project-governance/infra/verify_workflow.py dynamic-lifecycle-migration --target <path> --dry-run
```

`--dry-run` is required in 0.55.0. `--apply` is blocked.

## Structured Preview

The command prints JSON with these top-level sections:

- `workflow_model`: current model inferred from the target, target model `dynamic-flow-gate`, and the boundary that `classic-phase-gate` remains active/default.
- `flow_units`: flow-unit preview from optional `.governance/flow-unit-runtime.json`; if absent, the lifecycle registry example can be used as a preview source.
- `evidence_preservation`: readable plan/evidence paths, preservation flags, evidence row count, and SHA-256 hashes.
- `blocked_checks`: fail-closed reasons such as missing plan/evidence, missing lifecycle registry, dynamic default overclaim, or empty evidence rows.
- `no_overclaim_boundaries`: conservative boundaries for dry-run, opt-in, risk status, and readiness claims.
- `migration_plan`: read-only planning steps for inventory, preservation, opt-in review, and future human-reviewed migration.

## Evidence Preservation Rules

Existing classic governance evidence stays authoritative. A future real migration must copy forward or reference existing evidence instead of replacing it. The preview only proves whether current files are readable and hashable.

Fail-closed cases:

- Missing `.governance/plan-tracker.md`.
- Missing `.governance/evidence-log.md`.
- Evidence log has no parseable evidence rows.
- Lifecycle registry is unreadable or claims `dynamic-flow-gate` active/default.
- Target text claims dynamic default, risk closure, migration already applied, or 1.0.0 readiness.

## Rollback and Real Migration Boundary

There is no 0.55.0 write path to roll back because the command does not mutate target files. A future write-capable migration must ship a separate command, independent review, backup plan, and rollback proof before it can be used on a project.

Until that exists:

- Keep classic project gates valid.
- Treat dynamic flow units as preview/runtime visibility only.
- Require explicit user opt-in for any future migration.
- Keep RISK-036 and RISK-037 open until their external validation closure criteria are met.
