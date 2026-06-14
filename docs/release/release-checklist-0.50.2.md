# Release Checklist - 0.50.2

**Version**: 0.50.2

**Release theme**: REL-029 External Project Validation Harness

## Checklist

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | FIX-131 external project validation harness is included | PASS | `external-project-validation --target <path>` is wired into `verify_workflow.py` and documented as TOOL-036 |
| 2 | Harness target isolation is guarded | PASS | `--workspace-parent` cannot point to the target or a child of target; target smoke confirmed no mutation |
| 3 | Temporary external profile cannot spoof hot fact-source skip | PASS | Skip requires generated sentinel plus root temporary plan path |
| 4 | 0.50.2 release docs are present and manifest-covered | PASS | `release-checklist-0.50.2.md`, `feature-flags-0.50.2.md`, and `rollback-plan-0.50.2.md` are listed in `core/manifest.json` |
| 5 | Version declarations are synchronized | PASS | Source SKILL, canonical manifest, Claude/Codex plugin metadata, Claude marketplace metadata, hook @version, target fixture skill, CHANGELOG, README, and REQUIRED_SNIPPETS are 0.50.2 |
| 6 | 0.50.2 release gate is expected to pass | PASS | `check-release --version 0.50.2 --require-changelog --runtime-adapters` must pass after this package is prepared |
| 7 | RISK-036 remains open | PASS | 0.50.2 does not claim official approval, marketplace approval, two real external projects full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready |

## Release Boundary

0.50.2 packages FIX-131 as a supported external project validation harness. It turns the earlier partial-install smoke path into a repeatable, isolated command that can validate the workflow surface against an arbitrary external target without writing into that target.

The expected 1.0.0 blockers remain:

- RISK-036 is not closed.
- Two real external project validation full PASS evidence entries are still missing.
- Official submission result or approval evidence is missing.
- Codex Desktop lifecycle PASS or explicit conservative disposition remains required.

0.50.2 does not replace the future external validation evidence requirement. A harness smoke PASS proves the mechanism works; it is not itself two real external projects full PASS.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No RISK-036 closure. No 1.0.0 production-ready.

RISK-036 remains open.
