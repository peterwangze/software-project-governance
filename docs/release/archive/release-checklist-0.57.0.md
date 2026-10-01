# Release Checklist - 0.57.0

**Version**: 0.57.0

**Release theme**: AUDIT-121 architecture degradation audit archive (documentation/governance-only release, no functional code change)

## Checklist

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | AUDIT-121 audit report archived | PASS | `docs/requirements/architecture-degradation-audit-0.57.0.md` documents F1-F6 degradation facts (verify_workflow.py God Module 20,294 lines / 439 def+class / 54 CLI subcommands; missing modern engineering infrastructure; source/projection duplication 6,128 lines; command-surface redundancy; self-evolution residue; architecture-health stewardship gap as root cause) + refactor roadmap |
| 2 | Technical-debt ledger established | PASS | `skills/software-project-governance/core/technical-debt-ledger.md` registers TD-001~006; consumed by future ArchGuard (0.58.0) |
| 3 | Root-directory residue cleaned | PASS | Untracked `nul` (Windows device-name miscreation, 189 bytes, no refs) and `_fix_030_reconstruct.py` (FIX-030 one-shot script residue, 90 lines, FIX-030 long completed) removed; F5 partial closure |
| 4 | Governance records updated | PASS | DEC-083, RISK-039, EVD-619 entered; plan-tracker version roadmap (0.57.0~0.64.0), active items, risk count (2→3) updated |
| 5 | Decision record for refactor direction | PASS | DEC-083 records three user decisions: full-project deep audit / independent version for ArchGuard / progressive per-domain split of verify_workflow.py |
| 6 | 0.57.0 release docs present and manifest-covered | PASS | `release-checklist-0.57.0.md`, `feature-flags-0.57.0.md`, `rollback-plan-0.57.0.md` listed in `core/manifest.json` |
| 7 | Version declarations synchronized | PASS | Source SKILL, canonical manifest, Claude/Codex/zcode plugin metadata, Claude marketplace, top-level package.json, hook `@version` (4 source + 4 installed), zcode-local-load.py, REQUIRED_SNIPPETS (6 assertions), target fixture projection are 0.57.0 |
| 8 | No functional code change | PASS | `verify_workflow.py` only the 6 version-string assertions in `REQUIRED_SNIPPETS` bumped; no check logic, no hook logic, no Web console code, no lifecycle change |
| 9 | 0.57.0 release gate is documented | PASS | Coordinator runs `check-release --version 0.57.0 --require-changelog --runtime-adapters` |
| 10 | RISK-036 remains open | PASS | 0.57.0 does not claim official approval, marketplace approval, universal runtime support, external validation full PASS, or 1.0.0 readiness |
| 11 | RISK-037 remains open | PASS | 0.57.0 does not close dynamic lifecycle or external validation blockers |
| 12 | RISK-039 remains open | PASS | 0.57.0 does not implement ArchGuard; RISK-039 (architecture-health stewardship gap) closure criteria require ArchGuard delivery + split completion + external host-project validation |

## Release Boundary

0.57.0 is a documentation/governance-only release that archives the AUDIT-121 full-project architecture degradation audit. It adds the diagnosis report, a technical-debt ledger, and cleans up root-directory residue. It plans the subsequent refactor roadmap (0.58.0 ArchGuard as an independent capability version, 0.59.0~0.64.0 progressive per-domain split of `verify_workflow.py`). It does NOT change any functional code, lifecycle model, check semantics, Web console behavior, or hook logic.

The release includes:

- version declarations for the 0.57.0 package (REQUIRED_SNIPPETS version-string assertions bumped from 0.56.1);
- `docs/requirements/architecture-degradation-audit-0.57.0.md` (diagnosis-only report);
- `skills/software-project-governance/core/technical-debt-ledger.md` (TD-001~006);
- removal of untracked root-directory residue (`nul`, `_fix_030_reconstruct.py`);
- README readiness boundary updated to reflect AUDIT-121 and RISK-039;
- manifest coverage for the 0.57.0 release docs.

The release does NOT include:

- any modification to `verify_workflow.py` functional code (only 6 version-string assertions);
- ArchGuard implementation (planned for 0.58.0);
- any `verify_workflow.py` split (planned for 0.59.0~0.64.0);
- lint/type/package engineering infrastructure (planned for 0.64.0);
- docs/release archive mechanism (planned for 0.58.0);
- submission to or approval from any official marketplace;
- RISK-036, RISK-037, or RISK-039 closure;
- 1.0.0 readiness.

## No-Overclaim Boundary

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No completed non-game preset generalization claim. No Web replacement for CLI/client execution. No Web-triggered agent task execution. No ArchGuard implementation. No `verify_workflow.py` split. No modern engineering infrastructure (lint/type/package). No docs/release archive mechanism. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness.

RISK-036 remains open. RISK-037 remains open. RISK-039 remains open.
