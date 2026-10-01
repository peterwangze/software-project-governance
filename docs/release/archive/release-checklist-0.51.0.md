# Release Checklist - 0.51.0

**Version**: 0.51.0

**Release theme**: REL-031 Dynamic Lifecycle Spec schema-only release

## Checklist

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | FIX-135 lifecycle registry is included | PASS | `core/lifecycle-registry.json` defines classic-phase-gate, dynamic-flow-gate, stage/subphase vocabulary, gate references, allowed transitions, flow unit schema, project type hooks, and python_game example data |
| 2 | Classic G1-G11 compatibility remains active | PASS | `classic-phase-gate` remains active/default; 0.51.0 does not replace the current classic stage-gate path |
| 3 | Dynamic flow-gate runtime remains inactive | PASS | `dynamic-flow-gate` remains inactive schema-only; flow-unit runtime behavior is not activated |
| 4 | Validator coverage is included | PASS | `check-lifecycle-registry --fail-on-issues` guards schema-only mode, runtime activation flags, classic gate preservation, project type hook/default drift, python_game lanes, and no-overclaim wording |
| 5 | 0.51.0 release docs are present and manifest-covered | PASS | `release-checklist-0.51.0.md`, `feature-flags-0.51.0.md`, and `rollback-plan-0.51.0.md` are listed in `core/manifest.json` |
| 6 | Version declarations are synchronized | PASS | Source SKILL, canonical manifest, Claude/Codex plugin metadata, Claude marketplace metadata, hook @version, target fixture skill, target fixture plan tracker, CHANGELOG, README, and REQUIRED_SNIPPETS are 0.51.0 |
| 7 | 0.51.0 release gate is expected to pass | PASS | `check-release --version 0.51.0 --require-changelog --runtime-adapters` must pass after this package is prepared |
| 8 | RISK-036 remains open | PASS | 0.51.0 does not claim official approval, marketplace approval, two real external projects full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready |
| 9 | RISK-037 remains open | PASS | 0.51.0 ships registry/schema/validator/docs only and does not claim dynamic lifecycle runtime readiness, project migration, or flow-unit runtime activation |

## Release Boundary

0.51.0 packages the Dynamic Lifecycle Spec schema-only scope. It versions the data contract and validation guard needed for later flow-unit runtime work while keeping the existing classic G1-G11 lifecycle as the active/default behavior.

The release includes:

- lifecycle registry/schema;
- lifecycle registry validator;
- manifest and metadata version declarations;
- release docs and README/changelog boundary text.

The release excludes:

- flow-unit runtime activation;
- project migration;
- classic G1-G11 replacement;
- RISK-036 or RISK-037 closure;
- official approval, marketplace approval, external validation full PASS, Codex Desktop lifecycle PASS, or 1.0.0 readiness.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
