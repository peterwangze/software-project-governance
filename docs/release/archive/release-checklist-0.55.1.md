# Release Checklist - 0.55.1

**Version**: 0.55.1

**Release theme**: REL-039 Web console CLI/client entry patch

## Checklist

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | FIX-148 is completed | PASS | `web-console --status` and `web-console --start [--install]` are implemented in `verify_workflow.py` |
| 2 | CLI/client remains the primary entry | PASS | README and Web first screen describe Web as an optional local companion dashboard |
| 3 | First-run dependency install is explicit | PASS | `--start` blocks when `node_modules` is missing unless `--install` is passed |
| 4 | Port identity detection is fail-closed | PASS | `web/index.html` exposes SPG identity meta and `_web_console_probe()` treats non-SPG HTML as `occupied` |
| 5 | Mobile entry actions are visible | PASS | Playwright verified Start and Copy actions inside a 390x844 first viewport |
| 6 | Web runtime artifacts remain ignored | PASS | `web/web-dev.log` and `web/.spg-web-console.pid` are ignored |
| 7 | 0.55.1 release docs are present and manifest-covered | PASS | `release-checklist-0.55.1.md`, `feature-flags-0.55.1.md`, and `rollback-plan-0.55.1.md` are listed in `core/manifest.json` |
| 8 | Version declarations are synchronized | PASS | Source SKILL, canonical manifest, Claude/Codex plugin metadata, Claude marketplace metadata, hook `@version`, target fixture skill/plan, CHANGELOG, README, and REQUIRED_SNIPPETS are 0.55.1 |
| 9 | 0.55.1 release gate is documented | PASS | Coordinator should run `check-release --version 0.55.1 --require-changelog --runtime-adapters` after this package is prepared |
| 10 | 0.55.0 dynamic lifecycle boundary is preserved | PASS | 0.55.1 does not add apply/write migration, project migration, dynamic-flow-gate default, or non-game preset generalization completion |
| 11 | RISK-036 remains open | PASS | 0.55.1 does not claim official approval, marketplace approval, two real external projects full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready |
| 12 | RISK-037 remains open | PASS | 0.55.1 does not close dynamic lifecycle migration/external validation blockers |

## Release Boundary

0.55.1 packages the reviewed FIX-148 Web console CLI/client entry patch on top of 0.55.0. It is a conservative usability release for discovering and launching the optional local Web console from the primary CLI/client workflow.

The release includes:

- version declarations for the 0.55.1 package;
- `web-console --status` and `web-console --start [--install]`;
- SPG Web identity probing and fail-closed occupied-port handling;
- README and Web first-screen copy that position Web as a companion dashboard;
- 0.55.1 release docs and manifest coverage;
- hook `@version` metadata synchronized to 0.55.1;
- target fixture and validator release/version snippets synchronized to 0.55.1.

The release excludes:

- Web replacing `/governance` or the CLI/client execution path;
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
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.55.1 --require-changelog --runtime-adapters
git diff --check
```

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No completed non-game preset generalization claim. No Web replacement for CLI/client execution. No Web-triggered agent task execution. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
