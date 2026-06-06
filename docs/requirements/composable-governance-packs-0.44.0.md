# 0.44.0 Composable Governance Packs Plan

Date: 2026-06-05
Task: AUDIT-108
Version target: 0.44.0
Linked requirement: REQ-085
Risk: RISK-036

## Purpose

0.44.0 should reduce adoption friction without weakening the delivery trust layer. The current package is strong but monolithic: users see `lite`, `standard`, and `strict` profiles, yet installation still ships one broad governance asset set and the first-run language asks users to understand many capabilities at once.

Composable Governance Packs should let users start with a small pack and add stronger governance capabilities when the project needs them. The result should be easier first adoption, clearer capability boundaries, and a more official-review-friendly package shape.

## Source Facts

| Fact | Evidence |
| --- | --- |
| 0.43.0 is published and RISK-036 remains open. | `.governance/plan-tracker.md`, `project/CHANGELOG.md`, `docs/release/release-checklist-0.43.0.md` |
| DEC-072 positions this project as an AI coding delivery trust layer, not another coding-methodology skill pack. | `.governance/decision-log.md` |
| README already presents `lite`, `standard`, and `strict` first-run presets. | `README.md` |
| `core/profiles.md` defines governance strength, Gate behavior, record requirements, and Agent Team differences. | `skills/software-project-governance/core/profiles.md` |
| `core/manifest.json` currently treats the workflow as one product package with product and repo-only file groups. | `skills/software-project-governance/core/manifest.json` |
| 0.42.0 explicitly deferred composable packs to 0.44.0. | `docs/requirements/five-minute-success-path-0.42.0.md` |
| 0.43.0 rollback plan blocks mixing 0.44.0 changes into 0.43.0. | `docs/release/rollback-plan-0.43.0.md` |
| User feedback on 2026-06-05: running governance should explore context and handle unfinished user work in progress. | Current user request, `.governance/session-snapshot.md`, `.governance/plan-tracker.md` |

## User And JTBD

| User | Job to be done | Pain today | Success moment |
| --- | --- | --- | --- |
| Solo/MVP user | Start with one small governance layer that shows current state and protects against obvious drift. | Full standard governance looks heavy before value is proven. | User installs or enables `governance-core`, sees Delivery Trust Snapshot, and can defer heavier packs. |
| Returning active user | Resume work without re-explaining what was already in progress. | `/governance` can show state, but the agent may still leave unfinished user matters implicit unless it actively explores context. | User runs governance and sees the unfinished item, relevant evidence, blockers, and the next action already handled or queued. |
| Team maintainer | Add quality, review, release, and Agent Team controls only when the project crosses risk thresholds. | Profiles express intensity, but not a clear capability module boundary. | User can inspect a pack matrix and see what each pack adds, validates, and costs. |
| Official reviewer | Understand installable capability boundaries and conservative runtime claims. | One broad package makes review harder: capabilities, side effects, and degraded modes are mixed. | Reviewer can see pack manifests, no-overclaim boundaries, and validation commands per pack. |

## Non-Goals

- Do not split files physically into separate marketplace plugins in the first slice.
- Do not remove existing `lite` / `standard` / `strict` profiles.
- Do not close RISK-036.
- Do not claim official approval, marketplace approval, universal/full runtime support, or 1.0.0 production-ready.
- Do not change runtime adapter pass/blocked/degraded status in this version unless new real E2E evidence is added under a separate task.
- Do not treat `pack enabled` as proof that quality, review, release, or external validation has passed.
- Do not implement 0.45.0 governance benchmark or 0.46.0 official submission package.

## Proposed Pack Model

| Pack | Default profile fit | Capabilities | User-visible value | Validation boundary |
| --- | --- | --- | --- | --- |
| `governance-core` | lite | Bootstrap, status, plan/evidence/decision/risk files, Delivery Trust Snapshot, hook presence diagnostics, context discovery for unfinished user work. | First trust signal with minimal concept load and a usable resume handoff. | Status output and first-run demo remain local/no-credential; context discovery must be fact-based and must not invent unfinished work. |
| `quality-gates` | standard | Product Success Contract, executable acceptance, quality budget, vertical slice, deterministic scaffold checks. | Prevents process-complete but low-quality output. | Check 18d-18h and focused tests must pass. |
| `release-governance` | standard/strict | Version consistency, changelog, release checklist, rollback plan, feature flags, release readiness gate. | Safer versioned release and rollback. | `check-release --require-changelog` must explain pack scope. |
| `agent-team` | standard/strict | Producer-reviewer separation, Agent Team roles, review coverage, degraded-mode honesty. | Makes review boundaries explicit across hosts. | Review coverage and fallback policy checks must pass. |
| `enterprise` | strict | Strict evidence, risk escalation, external validation, compliance-style audit pressure. | Strongest governance for regulated/high-risk work. | Strict profile and escalation checks must be inspectable. |

## Minimum Product Slice

The first implementation slice should create an inspectable pack registry without moving files:

1. Add a canonical pack manifest describing pack IDs, included capabilities, default profile fit, user value, files or checks owned by the pack, and no-overclaim boundary.
2. Add a validation command that verifies every pack has required fields and that all referenced checks/files exist.
3. Add a context-discovery contract for `governance-core`: governance entrypoints should inspect plan-tracker, session snapshot, risk/evidence logs, active version plans, git status, and recent committed/uncommitted work, then surface unfinished user matters with next actions.
4. Add README guidance that maps first-run presets to packs without forcing users to choose every module up front.
5. Keep the installed artifact backward compatible: existing users still load `skills/software-project-governance/SKILL.md`.

This slice is enough for users and reviewers to see modular boundaries while avoiding the risk of breaking plugin installation by physically splitting assets too early.

## Planned 0.44.0 Task Split

| Task | Priority | Scope | Done definition | Acceptance commands |
| --- | --- | --- | --- | --- |
| AUDIT-108 | P1 | This gap analysis and executable task split. | Document exists, maps facts to tasks, and preserves RISK-036/no-overclaim boundaries. | `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues` |
| FIX-108 | P0 | Pack registry and validator. | Add canonical pack registry plus `check-governance-packs [--fail-on-issues]`; reject missing fields, unknown pack IDs, missing referenced files/checks, and overclaim wording. | `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -k GovernancePack -v`; `python skills/software-project-governance/infra/verify_workflow.py check-governance-packs --fail-on-issues`; `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -v` |
| FIX-112 | P0 | Context-aware governance resume. | `/governance`/status explores current context and turns unfinished user work into a concrete handoff: detected item, source facts, blocker state, next action, and whether it can auto-continue without interrupting the user. Implemented as `governance-context`/TOOL-027 and `check-governance` Check 28g; no facts must produce `not found` and `do not invent`. | `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -k GovernanceContextDiscovery -v`; `python skills/software-project-governance/infra/verify_workflow.py governance-context --fixture project/e2e-test-project --fail-on-issues`; `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues` |
| FIX-109 | P0 | README and first-run pack guidance. | README maps lite/standard/strict to `governance-core`, `quality-gates`, `release-governance`, `agent-team`, and `enterprise` without replacing profiles. | `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -k ReadmePackGuidance -v`; `python skills/software-project-governance/infra/verify_workflow.py check-readme-pack-guidance --fail-on-issues`; `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues` |
| FIX-110 | P1 | Manifest and cleanup integration. | `core/manifest.json` or companion metadata makes pack registry a canonical product artifact; cleanup and manifest checks keep it tracked. | `python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues`; `python skills/software-project-governance/infra/verify_workflow.py verify`; `python skills/software-project-governance/infra/verify_workflow.py check-governance-packs --fail-on-issues` |
| FIX-111 | P1 | Pack-aware status/release docs boundary. | Status or docs can summarize enabled/default packs and release docs include pack boundary/no-overclaim wording. | `python -m unittest skills.software-project-governance.infra.tests.test_verify_workflow -k GovernancePackStatus -v`; `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.44.0 --require-changelog --runtime-adapters` |
| REL-020 | P0 | Release 0.44.0. | Version bump, changelog, release docs, release review, commit, push, tag, and CI success. | `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.44.0 --require-changelog --runtime-adapters`; `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -v` |

## Acceptance Signals

- A user can answer "which pack should I start with" from README without reading `SKILL.md`.
- A reviewer can inspect one registry and see each pack's capability boundary, files/checks, and claims.
- A command can fail when a pack references a missing file/check or includes forbidden no-overclaim wording.
- Existing standard profile dogfood remains valid after adding pack metadata.
- Running governance on an active project exposes unfinished user work from facts rather than asking the user to restate context.
- No release wording claims marketplace approval or 1.0.0 readiness.
- No wording treats pack membership or pack enablement as a substitute for task evidence, review evidence, quality budgets, or release gates.

## Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| Pack model duplicates profile model. | State that packs are capability modules and profiles are governance intensity presets; README and registry must show the distinction. |
| Physical split breaks plugin installation. | First slice is registry-first and backward compatible; physical split is deferred until validation proves the boundaries. |
| Weak LLM treats "pack enabled" as proof of quality. | Validator and docs must tie each pack to concrete checks and evidence, not marketing labels. |
| Context discovery invents or over-prioritizes work. | FIX-112 must require source facts for every detected item and keep "not found" as an acceptable result when no unfinished work is evidenced. |
| Official reviewers interpret packs as marketplace approval. | Every public 0.44.0 artifact keeps no official approval / no marketplace approval / no universal runtime support boundary. |

## 1.0.0 Relationship

0.44.0 reduces adoption friction and makes the package easier to review, but it does not close RISK-036 by itself. 1.0.0 remains blocked until 0.44.0-0.46.0 are complete, external validation is recorded, and the official submission package is ready.
