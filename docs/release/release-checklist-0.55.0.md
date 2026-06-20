# Release Checklist - 0.55.0

**Version**: 0.55.0

**Release theme**: REL-035 Dynamic Lifecycle migration preview and external validation archive

## Checklist

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Dry-run migration preview is shipped | PASS | FIX-139 added `dynamic-lifecycle-migration --target <path> --dry-run` and the `dynamic-flow-gate-migration` alias |
| 2 | Write/apply path remains blocked | PASS | 0.55.0 preview reports `write_operations=[]`; missing `--dry-run` and `--apply` fail closed |
| 3 | Migration guide is present | PASS | `docs/migration/dynamic-flow-gate-migration-0.55.0.md` documents classic/default and dynamic opt-in boundaries |
| 4 | `python_game` validation is archived | PASS | VAL-005 records dry-run `READY_FOR_REVIEW`, plan/evidence hashes, and 10 chapter flow units |
| 5 | `python_game` installed-state blocker is documented | PASS | VAL-005 records external validation exit 1 caused by `CLAUDE.md:32` repo-local workflow home assumption |
| 6 | Non-game validation is archived | PASS | VAL-006 records `shitu` dry-run `READY_FOR_REVIEW`, evidence preservation, and 89 evidence rows |
| 7 | Non-game preset generalization boundary is documented | PASS | VAL-006 records that flow units still come from `python_game_10_chapters`; preset generalization remains PARTIAL |
| 8 | Installed hook/native entry drift remains visible | PASS | VAL-006 records `shitu` native entry assumptions and installed hook version/source drift |
| 9 | 0.55.0 release docs are present and manifest-covered | PASS | `release-checklist-0.55.0.md`, `feature-flags-0.55.0.md`, and `rollback-plan-0.55.0.md` are listed in `core/manifest.json` |
| 10 | Version declarations are synchronized | PASS | Source SKILL, canonical manifest, Claude/Codex plugin metadata, Claude marketplace metadata, hook `@version`, target fixture skill/plan, CHANGELOG, README, and REQUIRED_SNIPPETS are 0.55.0 |
| 11 | 0.55.0 release gate is documented | PASS | Coordinator should run `check-release --version 0.55.0 --require-changelog --runtime-adapters` after this package is prepared |
| 12 | RISK-036 remains open | PASS | 0.55.0 does not claim official approval, marketplace approval, two real external projects full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready |
| 13 | RISK-037 remains open | PASS | 0.55.0 does not implement an apply/write path, migrate projects, make `dynamic-flow-gate` default, or claim dynamic lifecycle readiness |

## Release Boundary

0.55.0 packages the Dynamic Lifecycle migration preview and external validation archives for FIX-139, VAL-005, and VAL-006. It is a conservative release of read-only preview tooling and validation facts, not a project migration release.

The release includes:

- version declarations for the 0.55.0 package;
- dry-run-only migration preview command and migration guide;
- release docs and README/changelog boundary text for REL-035;
- manifest coverage for 0.55.0 release docs;
- hook `@version` metadata synchronized to 0.55.0;
- target fixture and validator release/version snippets synchronized to 0.55.0;
- VAL-005 `python_game` validation archive;
- VAL-006 `shitu` non-game validation archive.

The release excludes:

- an apply/write migration path;
- automatic project migration;
- `dynamic-flow-gate` as default;
- completed non-game preset generalization;
- external validation full PASS;
- registry automation command execution changes;
- official approval, marketplace approval, Codex Desktop lifecycle PASS, project migration, or 1.0.0 readiness;
- RISK-036 or RISK-037 closure.

## Coordinator Release Gate Commands

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.55.0 --require-changelog --runtime-adapters
git diff --check
```

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No completed non-game preset generalization claim. No registry automation command execution change. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
