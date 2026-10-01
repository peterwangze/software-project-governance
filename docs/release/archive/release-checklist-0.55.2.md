# Release Checklist - 0.55.2

**Version**: 0.55.2

**Release theme**: REL-040 Web console passive summary entry patch

## Checklist

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | FIX-149 is completed | PASS | `web-console --summary-link` is implemented as a no-side-effect summary footer |
| 2 | Manual `/governance` does not start Web services | PASS | Source and target fixture `/governance` contracts forbid default Web/Vite/npm dev-server startup |
| 3 | Summary footer is passive | PASS | `--summary-link` prints a running URL, unavailable state, or manual start command without invoking npm, browser open, or `Popen` |
| 4 | Invalid mixed mode is blocked | PASS | `web-console --summary-link --start --fail-on-issues` exits non-zero before startup logic |
| 5 | External installed runtime path contract is preserved | PASS | `/governance` docs use resolved `WORKFLOW_HOME`, not repo-local `python skills/...` command paths |
| 6 | 0.55.2 release docs are present and manifest-covered | PASS | `release-checklist-0.55.2.md`, `feature-flags-0.55.2.md`, and `rollback-plan-0.55.2.md` are listed in `core/manifest.json` |
| 7 | Version declarations are synchronized | PASS | Source SKILL, canonical manifest, Claude/Codex plugin metadata, Claude marketplace metadata, hook `@version`, target fixture skill/plan, CHANGELOG, README, and REQUIRED_SNIPPETS are 0.55.2 |
| 8 | 0.55.2 release gate is documented | PASS | Coordinator should run `check-release --version 0.55.2 --require-changelog --runtime-adapters` after this package is prepared |
| 9 | RISK-036 remains open | PASS | 0.55.2 does not claim official approval, marketplace approval, two real external projects full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready |
| 10 | RISK-037 remains open | PASS | 0.55.2 does not close dynamic lifecycle migration/external validation blockers |

## Release Boundary

0.55.2 packages the reviewed FIX-149 Web console passive summary entry patch on top of 0.55.1. It is a conservative usability release: `/governance` remains a CLI/client governance entry, and Web remains an optional local companion dashboard.

The release includes:

- version declarations for the 0.55.2 package;
- `web-console --summary-link` for task, phase, and session summary footers;
- fail-closed blocking for `--summary-link --start`;
- README, TOOL-042, and `/governance` source/fixture wording that make Web startup explicit-only;
- 0.55.2 release docs and manifest coverage;
- hook `@version` metadata synchronized to 0.55.2;
- target fixture and validator release/version snippets synchronized to 0.55.2.

The release excludes:

- Web replacing `/governance` or the CLI/client execution path;
- default Web service startup from manual `/governance`;
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
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.55.2 --require-changelog --runtime-adapters
git diff --check
```

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No completed non-game preset generalization claim. No Web replacement for CLI/client execution. No default Web service startup from `/governance`. No Web-triggered agent task execution. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
