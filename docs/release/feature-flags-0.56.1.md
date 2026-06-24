# Feature Flags - 0.56.1

**Version**: 0.56.1

REL-043 / 0.56.1 publishes the Web console real-data dashboard patch. It replaces hardcoded mock dashboard data with a live API reading real `.governance/` files, makes all buttons functional, and keeps the Web console a read-only local companion dashboard.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| `web/server.py` API (`/api/governance`) | Active (real-data) | Stdlib-only Python HTTP server; reads real plan-tracker/evidence-log/risk-log/manifest; import-fallback for parser functions |
| `web/src/main.jsx` real-data driven | Active (refactored) | `fetch('/api/governance')` replaces all hardcoded mock constants; loading/error/refreshing/notice states |
| `web/vite.config.js` proxy | Active (dev mode) | `/api` → `http://127.0.0.1:5174`; no new npm dependencies |
| Dashboard buttons | Active (functional) | refresh re-fetches data; navigate switches routes; non-executable actions honestly labeled read-only/CLI-only |
| Web console execution model | Read-only (unchanged boundary) | Dashboard does NOT execute agent tasks, release, archive, or approval actions |
| `web-console --governance-entry` | Active (unchanged from 0.56.0) | Manual `/governance` starts Vite + API server |
| `classic-phase-gate` lifecycle mode | Active/default (unchanged) | Existing classic registry-backed gate judgment unchanged |
| `dynamic-flow-gate` lifecycle mode | Inactive/non-default (unchanged) | 0.56.1 does not migrate projects |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open |
| RISK-037 open-risk boundary | Active release boundary | RISK-037 remains open |

## Kill Switch and Rollback Boundary

0.56.1 is a Web console fix. If the release package claims official/marketplace approval, universal runtime support, changes the governance workflow/lifecycle, allows the dashboard to execute agent/release/approval actions, closes RISK-036/RISK-037, or overclaims readiness, revert the 0.56.1 release package and return to 0.56.0 while keeping RISK-036 and RISK-037 open.

## No-Overclaim Boundary

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No completed non-game preset generalization claim. No Web replacement for CLI/client execution. No summary footer service startup. No Web-triggered agent task execution. No RISK-036 closure. No RISK-037 closure. No 1.0.0 readiness.

RISK-036 remains open. RISK-037 remains open.
