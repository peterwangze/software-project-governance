# Legacy 1.0.0 Requirement Reconciliation - 0.48.0

Date: 2026-06-10
Task: FIX-124
Source audit: AUDIT-113

This document reconciles early Agent Team / 1.0.0 requirement rows with the later 0.35.0 through 0.47.0 delivery evidence. The goal is to prevent old "downgraded to 1.0.0" rows from being read as current release blockers when the behavior has already been absorbed by later architecture, guard, adapter, and documentation releases.

No official approval. No marketplace approval. No universal/full runtime support. No external validation PASS. No Codex Desktop marketplace-management E2E PASS. No 1.0.0 production-ready status.

## Reconciliation Rules

| Status | Meaning |
| --- | --- |
| ABSORBED | The original requirement was delivered by later scoped releases under a different task ID or mechanism. Keep the old row as historical, but do not treat it as an open 1.0.0 blocker. |
| SUPERSEDED | The original requirement wording no longer matches the current product direction. Use the replacement requirement and evidence instead. |
| STILL_BLOCKING | The requirement remains a real 1.0.0 blocker and cannot be replaced by local fixtures, CI, or documentation. |
| NEEDS_FINAL_LEDGER | The behavior exists in pieces, but 1.0.0 still needs a single final evidence ledger before release. |

## Legacy Requirement Matrix

| Requirement | Earlier wording | 2026-06-10 status | Current evidence | 1.0.0 treatment |
| --- | --- | --- | --- | --- |
| REQ-014 | Task-Gate model data structure transformation. | ABSORBED | FIX-070, FIX-073, FIX-083, FIX-084, FIX-087, FIX-112, and governance pack/status guards moved task evidence, execution packets, review coverage, hot fact-source consistency, and context resume into checkable behavior. | Historical row only; no separate 1.0.0 blocker. |
| REQ-016 | Rewrite main workflow from serial routing to Agent Team routing. | ABSORBED | 0.35.0 FIX-070 clarified Coordinator, Governance Developer, Reviewer, communication I/O, and write-back boundaries; 0.38.0 FIX-085 added degraded runtime behavior. | Historical row only; keep degraded host boundary. |
| REQ-017 | Rewrite stage gates from Phase-Gate to Task-Gate. | SUPERSEDED | Later releases kept the 11-stage lifecycle for public compatibility while adding task-level evidence, acceptance, review, and release guards. | Do not require a disruptive stage-gate rewrite before 1.0.0. |
| REQ-018 | Upgrade verifier to validate Agent Team structure. | ABSORBED | `check-agent-team`, review coverage, runtime capability, structured evidence, hot fact-source, pack, capability, official-submission, and mainstream-loading checks now cover the operational structure. | Historical row only; final release still runs full gates. |
| REQ-019 | Update e2e-test-project for Agent Team mode. | ABSORBED_WITH_BOUNDARY | 0.35.0-0.47.0 upgraded target fixtures, native entries, runtime matrices, command contracts, and loading guides. Codex/Gemini blocked states remain explicit. | Not a standalone blocker; FIX-125 must publish the final command E2E ledger. |
| REQ-027 | Full governance model migration to task-level risk/decision/evidence granularity. | ABSORBED_WITH_BOUNDARY | Structured evidence, task IDs in commits, task evidence rows, risk linkage, release gates, and context discovery provide task-level traceability without forcing a breaking file schema migration. | Keep current schema; do not introduce a breaking migration before 1.0.0. |
| REQ-028 | Rewrite profiles.md so profiles define role-agent enablement. | SUPERSEDED | 0.44.0 established packs vs profiles: profiles remain governance intensity presets, packs are capability modules. | Do not rewrite profiles as role-agent scope. Use pack guidance instead. |
| REQ-029 | At least two external projects validate Agent Team workflow. | STILL_BLOCKING | No evidence exists for two external projects. Internal fixture, local demo, release gate, and GitHub CI are not substitutes. | Required before 1.0.0 unless governance records explicitly change acceptance criteria. |
| REQ-030 | Migration guide from old serial model to Agent Team. | ABSORBED_WITH_BOUNDARY | 0.46.0 published ecosystem migration guide and positioning docs; 0.47.0 published mainstream loading guides. | Keep migration docs, but no official approval claim. |
| REQ-031 | Phase-Gate deprecation notice and v2.0 removal timeline. | SUPERSEDED | Current product keeps the lifecycle and Phase-Gate vocabulary for compatibility while adding task-level guards. A v2.0 removal promise would be misleading. | Do not claim deprecation/removal before a new decision. |
| REQ-032 | Complete user docs: README, quick start, role configuration. | ABSORBED_WITH_BOUNDARY | README 5-minute start, Delivery Trust Snapshot, pack guidance, official submission docs, migration guide, and mainstream agent loading guides cover current user-facing docs. | Final release should spot-check docs, but this is not an open standalone blocker. |
| REQ-033 | Full E2E tests for all Agent Team roles and scenarios. | LEDGER_CREATED_BY_FIX-125 | FIX-125 publishes a final command E2E ledger. Full release readiness still needs FIX-127 because governance health currently fails on historical hot evidence structure. | Ledger debt closed; release-gate blocker moved to FIX-127. |
| REQ-058 | e2e-test-project all commands pass end to end. | LEDGER_CREATED_BY_FIX-125 | FIX-125 records source CLI proxy 6/6 PASS, target-cwd command matrix 4/4 PASS, target fixture 8/8 PASS, and contract-only items separately. | Ledger debt closed; not external project validation. |

## Current 1.0.0 Blockers After Reconciliation

Only these remain hard blockers after the legacy rows are reconciled:

| Blocker | Owner item | Reason |
| --- | --- | --- |
| Two external project validations | VAL-001 / 0.49.0 | Required by RISK-036 and REQ-029; no substitute evidence exists. |
| Desktop marketplace-management lifecycle or conservative blocked carry-forward | VAL-002 / 0.49.0 | RISK-036 allows either real PASS evidence or explicit blocked wording in the submission/release package. |
| Final official submission bundle review | FIX-126 / 0.49.0 | 0.46.0 created materials, but final 1.0.0 package must preserve current boundaries. |
| Governance health release-gate repair | FIX-127 / 0.48.0 | FIX-125 created the command ledger and discovered the remaining full release gate blocker. |
| RISK-036 closure decision | REL-026 / 0.49.0 or 1.0.0 release gate | Formal 1.0.0 cannot proceed while RISK-036 remains open. |

## No-Overclaim Boundary

This reconciliation reduces stale planning debt. It does not close RISK-036, does not provide external validation, and does not convert blocked Desktop lifecycle evidence into PASS.
