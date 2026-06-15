# Release Checklist - 0.52.0

**Version**: 0.52.0

**Release theme**: REL-032 Flow Unit Runtime Visibility release

## Checklist

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | FIX-136 flow-unit runtime visibility is included | PASS | `check-flow-unit-runtime`, optional `.governance/flow-unit-runtime.json` validation, and governance context/status flow-unit facts are present |
| 2 | Runtime hot state remains optional | PASS | Missing `.governance/flow-unit-runtime.json` is NOT_FOUND safe; malformed hot state fails closed without crashing context/status discovery |
| 3 | Flow-unit visibility scope is bounded | PASS | 0.52.0 exposes lanes, per-unit gate state, loop counters, blocked downstream units, and rollup status only |
| 4 | Classic G1-G11 compatibility remains active | PASS | `classic-phase-gate` remains active/default; 0.52.0 does not replace the current classic stage-gate path |
| 5 | Dynamic flow-gate engine remains inactive | PASS | `dynamic-flow-gate` is not default and no declarative gate engine is activated |
| 6 | 0.52.0 release docs are present and manifest-covered | PASS | `release-checklist-0.52.0.md`, `feature-flags-0.52.0.md`, and `rollback-plan-0.52.0.md` are listed in `core/manifest.json` |
| 7 | Version declarations are synchronized | PASS | Source SKILL, canonical manifest, Claude/Codex plugin metadata, Claude marketplace metadata, hook @version, target fixture skill, CHANGELOG, README, and REQUIRED_SNIPPETS are 0.52.0 |
| 8 | 0.52.0 release gate is expected to pass | PASS | `check-release --version 0.52.0 --require-changelog --runtime-adapters` must pass after this package is prepared |
| 9 | RISK-036 remains open | PASS | 0.52.0 does not claim official approval, marketplace approval, two real external projects full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready |
| 10 | RISK-037 remains open | PASS | 0.52.0 ships runtime visibility only and does not claim project-type presets, declarative gate execution, migration, external validation closure, or dynamic lifecycle readiness |

## Release Boundary

0.52.0 packages the Flow Unit Runtime Visibility scope. It versions optional hot-state validation and read-only governance visibility for projects that choose to record flow-unit runtime facts, while keeping classic G1-G11 as the active/default lifecycle path.

The release includes:

- optional flow-unit hot-state validator;
- `check-flow-unit-runtime` CLI;
- governance context/status visibility for flow-unit lanes and rollup;
- manifest and metadata version declarations;
- release docs and README/changelog boundary text.

The release excludes:

- declarative gate engine activation;
- project migration;
- `dynamic-flow-gate` as default;
- project-type gate presets;
- RISK-036 or RISK-037 closure;
- official approval, marketplace approval, external validation full PASS, Codex Desktop lifecycle PASS, or 1.0.0 readiness.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No declarative gate engine activation. No project migration. No dynamic-flow-gate default. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
