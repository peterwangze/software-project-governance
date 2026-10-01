# Release Checklist - 0.47.0

**Version**: 0.47.0

**Release theme**: REL-024 Mainstream Agent Loading Readiness

## Checklist

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Mainstream loading requirements are documented | PASS | `docs/requirements/mainstream-agent-loading-0.47.0.md` / AUDIT-112 |
| 2 | Codex marketplace root schema hotfix is disclosed as carried-forward prerequisite | PASS | FIX-120 / `0.46.0-post` / `.agents/plugins/marketplace.json`; not Desktop marketplace lifecycle E2E PASS |
| 3 | Codex manifest asset paths are valid after repo-root marketplace source | PASS | FIX-123 / `.codex-plugin/plugin.json` |
| 4 | README exposes Tier 1 and Tier 2 loading guidance | PASS | FIX-121 / `README.md` |
| 5 | Tier 1 adapter READMEs expose load, verify, and boundary sections | PASS | FIX-121 / `adapters/claude/README.md`, `adapters/codex/README.md`, `adapters/gemini/README.md`, `adapters/opencode/README.md` |
| 6 | Mainstream loading guard is wired into governance checks | PASS | FIX-122 / Check 28n / TOOL-035 |
| 7 | Release gate enforces mainstream loading boundary | PASS | `check-release --version 0.47.0 --require-changelog --runtime-adapters` |
| 8 | RISK-036 remains open | PASS | Release does not claim official approval, marketplace approval, Desktop lifecycle PASS, external validation closure, or 1.0.0 readiness |

## Release Boundary

0.47.0 makes mainstream agent loading paths easier to discover and verify. It is a documentation, adapter guide, manifest-path, and guard-readiness release. FIX-120 is carried forward from `0.46.0-post` as the Codex marketplace root schema prerequisite for this package; it remains metadata/schema readiness, not Desktop marketplace lifecycle E2E PASS.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No 1.0.0 production-ready.

RISK-036 remains open.
