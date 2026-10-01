# Release Checklist - 0.56.1

**Version**: 0.56.1

**Release theme**: REL-043 Web console real-data dashboard patch

## Checklist

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | FIX-151 is completed and committed | PASS | commit `cd3cda1` refactors `web/src/main.jsx` from hardcoded mock to real-data driven, adds `web/server.py` API + `web/vite.config.js` proxy + `cmd_web_console` API startup |
| 2 | Dashboard reads real governance data | PASS | `GET /api/governance` returns real project_root/project_name/version/gates/evidence/risks from `.governance/` files (live test confirmed project_name=project_management_workflow, release_version=0.56.0, gates=11, evidence_count=595) |
| 3 | All buttons have functional behavior | PASS | 17 buttons all have onClick (refresh/navigate/notice); non-executable actions honestly labeled read-only/CLI-only |
| 4 | API server is stdlib-only and safe | PASS | `web/server.py` uses `http.server`, path-traversal guard via `relative_to`, CORS configured, graceful degradation on missing governance files |
| 5 | Governance coverage is consistent | PASS | `web/server.py` + `web/vite.config.js` registered in manifest repo_only; `check-manifest-consistency --fail-on-issues` PASS |
| 6 | 0.56.1 release docs present and manifest-covered | PASS | `release-checklist-0.56.1.md`, `feature-flags-0.56.1.md`, `rollback-plan-0.56.1.md` listed in `core/manifest.json` |
| 7 | Version declarations synchronized | PASS | Source SKILL, canonical manifest, Claude/Codex/zcode plugin metadata, Claude marketplace, top-level package.json, hook `@version`, target fixture, REQUIRED_SNIPPETS are 0.56.1 |
| 8 | 0.56.1 release gate is documented | PASS | Coordinator runs `check-release --version 0.56.1 --require-changelog --runtime-adapters` |
| 9 | RISK-036 remains open | PASS | 0.56.1 does not claim official approval, marketplace approval, universal runtime support, external validation full PASS, or 1.0.0 readiness |
| 10 | RISK-037 remains open | PASS | 0.56.1 does not close dynamic lifecycle or external validation blockers |

## Release Boundary

0.56.1 packages the reviewed FIX-151 Web console real-data dashboard patch on top of 0.56.0. It is a conservative fix that replaces hardcoded mock dashboard data with a live API reading real `.governance/` files, and makes all buttons functional. It does not change the governance workflow, lifecycle model, or release boundary.

The release includes:

- version declarations for the 0.56.1 package;
- `web/server.py` lightweight Python API server (stdlib-only) reading real governance data;
- `web/vite.config.js` with `/api` proxy to the API server (dev mode);
- `web/src/main.jsx` refactored to `fetch('/api/governance')` real-data driven;
- `web/src/styles.css` loading/error/notice/spin state classes;
- `cmd_web_console` updated to start the API server alongside Vite;
- manifest repo_only coverage for new web files.

The release does NOT include:

- submission to or approval from any official marketplace;
- changes to the governance workflow or lifecycle model;
- RISK-036 or RISK-037 closure;
- 1.0.0 readiness.

## No-Overclaim Boundary

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No completed non-game preset generalization claim. No Web replacement for CLI/client execution. No summary footer service startup. No Web-triggered agent task execution. No RISK-036 closure. No RISK-037 closure. The Web console remains a read-only local companion dashboard. No 1.0.0 readiness.

RISK-036 remains open. RISK-037 remains open.
