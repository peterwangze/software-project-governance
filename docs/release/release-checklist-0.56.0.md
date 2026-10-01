# Release Checklist - 0.56.0

**Version**: 0.56.0

**Release theme**: REL-042 zcode plugin marketplace adapter patch

## Checklist

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | AUDIT-118 is completed and committed | PASS | commit `127530b` adds `.zcode-plugin/plugin.json` + assets, top-level `package.json`, `project/zcode-local-load.py`, manifest/PLUGIN_SCOPE_DIRS coverage |
| 2 | zcode plugin manifest aligns with official format | PASS | `.zcode-plugin/plugin.json` fields (name/version/description/author/homepage/repository/license/skills/commands) match official superpowers/restore-legacy-sessions/skill-creator |
| 3 | Local load tool is faithful and reversible | PASS | `zcode-local-load.py` ports the runtime seed hash algorithm; `load/--verify/--reload/--unload` are idempotent with backups |
| 4 | Runtime load is verified | PASS | EVD-610: user restarted zcode, `/governance` consumed by the plugin, Coordinator activated, Web console started |
| 5 | Governance coverage is consistent | PASS | manifest four-point registration + PLUGIN_SCOPE_DIRS synced in verify_workflow.py and cleanup.py; `check-manifest-consistency --fail-on-issues` PASS |
| 6 | 0.56.0 release docs are present and manifest-covered | PASS | `release-checklist-0.56.0.md`, `feature-flags-0.56.0.md`, `rollback-plan-0.56.0.md` are listed in `core/manifest.json` |
| 7 | Version declarations are synchronized | PASS | Source SKILL, canonical manifest, Claude/Codex/zcode plugin metadata, Claude marketplace metadata, top-level package.json, hook `@version`, target fixture skill/plan, CHANGELOG, README, and REQUIRED_SNIPPETS are 0.56.0 |
| 8 | 0.56.0 release gate is documented | PASS | Coordinator should run `check-release --version 0.56.0 --require-changelog --runtime-adapters` after this package is prepared |
| 9 | RISK-036 remains open | PASS | 0.56.0 does not claim official approval, marketplace approval, zcode official marketplace listing, universal runtime support, external validation full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready |
| 10 | RISK-037 remains open | PASS | 0.56.0 does not close dynamic lifecycle migration/external validation blockers |

## Release Boundary

0.56.0 packages the reviewed AUDIT-118 zcode plugin marketplace adapter on top of 0.55.3. It is a conservative adapter patch that adds the zcode native plugin surface (`.zcode-plugin/`, top-level `package.json`) and a one-shot local load tool, without changing the Web console entry, dynamic lifecycle, or CLI/client execution model.

The release includes:

- version declarations for the 0.56.0 package;
- `.zcode-plugin/plugin.json` + assets for zcode native plugin format;
- top-level `package.json` with `@zcode/software-project-governance-plugin` scope;
- `project/zcode-local-load.py` local load tool (load/--verify/--reload/--unload);
- manifest four-point coverage and PLUGIN_SCOPE_DIRS sync;

The release does NOT include:

- submission to or approval from the zcode official marketplace;
- changes to Web console governance-entry or summary-link behavior;
- changes to dynamic lifecycle activation or migration paths;
- RISK-036 or RISK-037 closure; the release does not claim production-ready for the 1.0.0 milestone.

## No-Overclaim Boundary

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No completed non-game preset generalization claim. No Web replacement for CLI/client execution. No summary footer service startup. No Web-triggered agent task execution. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
