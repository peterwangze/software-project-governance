# Release Checklist - 0.55.3

**Version**: 0.55.3

**Release theme**: REL-041 Web console governance-entry correction patch

## Checklist

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | FIX-150 is completed | PASS | `web-console --governance-entry` starts or reuses the local Web console for manual `/governance` |
| 2 | Manual `/governance` starts or reuses Web UI | PASS | Source and target fixture `/governance` contracts call `web-console --governance-entry` after resolving `WORKFLOW_HOME` |
| 3 | Summary footer remains passive | PASS | `web-console --summary-link` reports status/URL only and cannot be combined with start/governance-entry paths |
| 4 | Startup safety boundaries are preserved | PASS | Non-SPG port occupation is fail-closed; missing dependencies require explicit `--install`; no silent install |
| 5 | Regression coverage is present | PASS | WebConsoleGovernanceEntry tests cover reuse, missing deps, occupied port, start path, and summary-link conflict |
| 6 | 0.55.3 release docs are present and manifest-covered | PASS | `release-checklist-0.55.3.md`, `feature-flags-0.55.3.md`, and `rollback-plan-0.55.3.md` are listed in `core/manifest.json` |
| 7 | Version declarations are synchronized | PASS | Source SKILL, canonical manifest, Claude/Codex plugin metadata, Claude marketplace metadata, hook `@version`, target fixture skill/plan, CHANGELOG, README, and REQUIRED_SNIPPETS are 0.55.3 |
| 8 | 0.55.3 release gate is documented | PASS | Coordinator should run `check-release --version 0.55.3 --require-changelog --runtime-adapters` after this package is prepared |
| 9 | RISK-036 remains open | PASS | 0.55.3 does not claim official approval, marketplace approval, two real external projects full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready |
| 10 | RISK-037 remains open | PASS | 0.55.3 does not close dynamic lifecycle migration/external validation blockers |

## Release Boundary

0.55.3 packages the reviewed FIX-150 Web console governance-entry correction on top of 0.55.2. It is a conservative usability patch that restores the intended product entry: manual `/governance` starts or reuses the optional local Web console and prints the URL for follow-up UI interaction.

The release includes:

- version declarations for the 0.55.3 package;
- `web-console --governance-entry` for manual `/governance`;
- preserved `web-console --summary-link` read-only behavior for task, phase, and session summaries;
- fail-closed handling for non-SPG port occupation and missing dependency startup;
- README, TOOL-042, and `/governance` source/fixture wording for the corrected entry model;
- 0.55.3 release docs and manifest coverage;
- hook `@version` metadata synchronized to 0.55.3;
- target fixture and validator release/version snippets synchronized to 0.55.3.

The release excludes:

- Web replacing the CLI/client execution path;
- summary footer startup side effects;
- automatic agent task execution from the Web console;
- silent dependency installation;
- Desktop embedded UI or marketplace lifecycle PASS claims;
- an apply/write migration path;
- automatic project migration;
- `dynamic-flow-gate` as default;
- completed non-game preset generalization;
- external validation full PASS;
- official approval, marketplace approval, Codex Desktop lifecycle PASS, project migration, or 1.0.0 readiness;
- RISK-036 or RISK-037 closure.

## Coordinator Release Gate Commands

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.55.3 --require-changelog --runtime-adapters
git diff --check
```

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No completed non-game preset generalization claim. No Web replacement for CLI/client execution. No summary footer service startup. No Web-triggered agent task execution. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
