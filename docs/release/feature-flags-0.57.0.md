# Feature Flags - 0.57.0

**Version**: 0.57.0

0.57.0 is a documentation/governance-only release. It publishes the AUDIT-121 architecture degradation audit archive, a new technical-debt ledger, root-directory residue cleanup, and the refactor roadmap (0.58.0 ArchGuard + 0.59.0~0.64.0 progressive split). It does **not** change any functional code, lifecycle mode, check semantics, Web console behavior, or hook logic. All flags and surfaces carry forward from 0.56.1 unchanged.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| `verify_workflow.py` functional code | Unchanged | 0.57.0 does NOT modify functional code; only the version-string assertions in `REQUIRED_SNIPPETS` (6 lines) were bumped to 0.57.0 |
| `docs/requirements/architecture-degradation-audit-0.57.0.md` | New (documentation only) | Diagnosis-only report; F1-F6 facts + refactor roadmap; does not implement any fix |
| `skills/software-project-governance/core/technical-debt-ledger.md` | New (governance record) | Technical-debt registry TD-001~006; consumed by future ArchGuard (0.58.0) |
| Root-directory residue cleanup | New (cleanup only) | Removed untracked `nul` (Windows device-name miscreation) and `_fix_030_reconstruct.py` (one-shot FIX-030 script residue); no tracked file removed |
| `web/server.py` API (`/api/governance`) | Active (real-data, unchanged from 0.56.1) | Stdlib-only Python HTTP server; reads real plan-tracker/evidence-log/risk-log/manifest |
| Web console execution model | Read-only (unchanged boundary) | Dashboard does NOT execute agent tasks, release, archive, or approval actions |
| `web-console --governance-entry` | Active (unchanged from 0.56.0) | Manual `/governance` starts Vite + API server |
| `classic-phase-gate` lifecycle mode | Active/default (unchanged) | Existing classic registry-backed gate judgment unchanged |
| `dynamic-flow-gate` lifecycle mode | Inactive/non-default (unchanged) | 0.57.0 does not migrate projects |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open |
| RISK-037 open-risk boundary | Active release boundary | RISK-037 remains open |
| RISK-039 open-risk boundary | Active release boundary | RISK-039 remains open (new; architecture-health stewardship gap) |

## Kill Switch and Rollback Boundary

0.57.0 is a documentation/governance-only release with no functional code change. If the release package claims official/marketplace approval, universal runtime support, implements ArchGuard, modifies `verify_workflow.py` functional code, splits any module, introduces lint/type infrastructure, closes RISK-036/RISK-037/RISK-039, or overclaims readiness, revert the 0.57.0 release package and return to 0.56.1 while keeping RISK-036, RISK-037, and RISK-039 open.

## No-Overclaim Boundary

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No completed non-game preset generalization claim. No Web replacement for CLI/client execution. No Web-triggered agent task execution. No ArchGuard implementation. No `verify_workflow.py` split. No modern engineering infrastructure (lint/type/package). No docs/release archive mechanism. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness.

RISK-036 remains open. RISK-037 remains open. RISK-039 remains open.
