# 0.42.0 Five-Minute Success Path Gap Analysis

Date: 2026-06-03
Task: AUDIT-106
Requirement: REQ-083
Risk: RISK-036
Version target: 0.42.0

## Executive Summary

REQ-083 says a new user must see the perceptible value of the "AI coding delivery trust layer" within 5 minutes, before they understand the full governance system.

The current 0.41.0 package is marketplace-review ready: manifests, README first screen, privacy/security notes, submission checklist, and tracked assets are in place. The remaining 0.42.0 gap is not credibility for reviewers; it is first-session proof for users. A user can read that the workflow tracks evidence, gates, risks, and releases, but the happy path still asks them to understand too much before one concrete trust signal appears.

Recommended 0.42.0 direction: make the first successful experience a narrow demo loop:

1. User starts `/governance` in a repo.
2. Workflow detects new or existing project state.
3. Workflow offers a lite/standard/strict preset with a default.
4. Workflow creates or resumes local `.governance/` state.
5. Workflow shows one trust snapshot: goal, current stage, open risks, evidence status, next critical decision boundary, and one runnable verification command.
6. User can point at that snapshot and understand: "This catches drift, missing evidence, risky release claims, and weak review signals."

This document is a planning artifact. It does not claim official approval, marketplace approval, universal/full runtime support, or 1.0.0 production readiness. RISK-036 remains open.

## Source Facts

| Type | Fact | Source |
| --- | --- | --- |
| Fact | 0.41.0 released Official Marketplace Readiness and keeps RISK-036 open. | `.governance/plan-tracker.md`, `project/CHANGELOG.md`, `docs/release/release-checklist-0.41.0.md` |
| Fact | README now has an English marketplace first screen and a `5-Minute Start` section. | `README.md` |
| Fact | Existing 5-minute path says install, open project, run `/governance`, initialize `.governance/`, continue coding. | `README.md` |
| Fact | DEC-072 positions the product as an AI coding delivery trust layer, not another lightweight coding skill pack. | `.governance/decision-log.md`, `project/workflows/software-project-governance/research/competitive-positioning-and-official-marketplace-roadmap.md` |
| Fact | RISK-036 remains open until official submission package, at least 2 external project validations, public pass/blocked/degraded matrix, and clear delivery trust layer positioning are complete. | `.governance/risk-log.md` |
| Fact | Existing competitive research, dated 2026-06-01, records Superpowers, `wshobson/agents`, `addyosmani/agent-skills`, and Anthropic official plugins as adjacent options. | `project/workflows/software-project-governance/research/competitive-positioning-and-official-marketplace-roadmap.md` |

## Problem Clarification

### 5 Questions

| Question | Answer |
| --- | --- |
| Current pain | New users can see a serious governance system, but they may not see the first concrete value before learning many terms: Gate, evidence, Agent Team, degraded mode, release readiness, risk log, decision log, and profiles. |
| Why it matters | Marketplace users decide quickly. If the first session feels like process overhead, the product is mentally filed as "complex project management" rather than "delivery trust layer for AI coding." |
| Cost of not solving | RISK-036 remains likely: official reviewers and users may understand package quality but miss user value. 1.0.0 cannot honestly claim production-ready adoption readiness while first value is still implicit. |
| Ideal state | In under 5 minutes, a new user sees a local trust snapshot that identifies goal drift risk, evidence coverage, release readiness boundary, and the next safe action. |
| Success standard | At least 80% of pilot users in a 5-person external test can complete first-run setup and explain one observed trust signal within 5 minutes, with baseline initially assumed at 0/5 until measured. |

## Target Users And Scenarios

### Persona 1: Maya, Solo SaaS Founder

- Context: Maintains a small TypeScript SaaS repo and uses Claude Code or Codex for feature work.
- Job to be done: "Before I let the agent modify billing or auth code, I need confidence it will not silently drift from the goal or declare success without verification."
- Current pain: Existing AI coding tools help write code, but Maya still has to remember scope, risks, evidence, and release readiness manually.
- 5-minute success moment: Maya runs `/governance`, chooses the default preset, and sees a trust snapshot showing project goal, current stage, missing evidence status, and one recommended next action.
- Observable value: She can say, "This will stop the agent from treating a review note or unchecked command as delivery proof."

### Persona 2: Leo, Staff Engineer Onboarding Governance Into A Live Repo

- Context: Works on a mature backend service where several AI-generated patches have landed with weak evidence.
- Job to be done: "I need a low-friction way to attach delivery controls to an existing repo without rewriting our process."
- Current pain: He cannot ask every engineer to learn a full governance workflow before the first benefit appears.
- 5-minute success moment: Leo runs `/governance`, selects existing-project setup, and sees a snapshot that marks prior phases as entry-passed while surfacing active risks and missing hooks.
- Observable value: He can show the team a concrete "current risk + evidence + next verification" panel from their repo.

### Persona 3: Nina, Marketplace Reviewer Or Tool Evaluator

- Context: Evaluates AI coding plugins for safety, usefulness, and claims discipline.
- Job to be done: "I need to understand what this plugin does, what local state it writes, what it does not claim, and how a user sees value quickly."
- Current pain: A large workflow can look like impressive documentation rather than a usable first-run experience.
- 5-minute success moment: Nina follows the README path and sees a first-run demo or dry-run snapshot that does not require external credentials or unofficial runtime claims.
- Observable value: She can distinguish this package from coding methodology skill packs: it checks delivery trust signals after or around coding work.

## Current Path Gap Analysis

| Step | Current 0.41.0 path | Gap for REQ-083 | 0.42.0 need |
| --- | --- | --- | --- |
| Install | README has clear Claude install commands and conservative Codex/other-agent wording. | Install is not the success moment; users still need to run the workflow and see a local signal. | Keep install unchanged except pointing to a demonstrable first-run path. |
| Start | README says run `/governance`. | `/governance` may branch into initialization/status/diagnosis, but the first value story is not constrained to one happy path. | Define one default happy path with no concept overload. |
| Initialize | README describes project name, target, stage, profile, and `.governance/` creation. | The user may feel they are filling process forms before seeing value. | Use a default preset and defer non-critical fields where possible. |
| First output | Current governance state can be rich. | Richness hides the first trust signal. | First screen should show one compact "delivery trust snapshot." |
| Validation | Manual commands exist: `verify_workflow.py`, status, gates. | Commands are developer-facing and not tied to first success. | Provide a single runnable/observable smoke signal for first run. |
| Overclaim control | README and release docs avoid full support and official approval claims. | Good boundary, but not enough to show value. | Keep conservative claims while adding a local demo path. |
| Follow-up | Full workflow covers gates, evidence, risks, decisions, review, release. | The first user does not know which slice matters next. | Recommend a first vertical slice that only makes the first 5 minutes measurable. |

## Competitive And Adjacent Analysis

Facts below come from the 2026-06-01 local competitive research unless explicitly marked as a recommendation. They are not revalidated in this task.

| Option | User-perceived strength | Gap relative to delivery trust layer | Opportunity for this project |
| --- | --- | --- | --- |
| Superpowers (`obra/superpowers`) | Lightweight, memorable skills for brainstorming, planning, TDD, debugging, subagent work, code review, and branch finishing; research records strong adoption and official Codex plugin presence. | Helps agents perform coding workflows, but is not primarily a long-lived evidence/risk/release trust ledger. | Be complementary: after Superpowers helps generate work, SPG proves whether delivery is evidenced, reviewed, risk-aware, and release-ready. |
| `addyosmani/agent-skills` | Production-oriented engineering skills with clear lifecycle and progressive disclosure. | Strong task guidance, but less focused on project-local governance state, risk decisions, and release gate history as a durable trust layer. | Use a faster first-run UX while keeping durable `.governance/` records as the differentiator. |
| `wshobson/agents` | Large multi-harness marketplace of agents, skills, and commands generated across platforms. | Broad agent catalog can improve capability coverage, but breadth does not automatically prove each delivery is aligned, verified, and safe to release. | Position SPG as the governance wrapper that can coordinate specialized agents without pretending all runtimes are equivalent. |
| Anthropic official plugin ecosystem | Clear official directory expectations, plugin structure, safety, and installation trust. | Official packaging helps discovery but does not itself solve first-run product value. | 0.41.0 prepared packaging; 0.42.0 must demonstrate value before asking for deep workflow adoption. |

### Empty Space

The visible gap is a "trust receipt" for AI coding delivery: a compact, local, inspectable signal that connects goal, evidence, risk, review, and release boundaries. Competitors are strong at helping agents do the work; this project can be strong at proving whether the work should be trusted.

## In Scope And Out Of Scope

### In Scope For 0.42.0

- A defined 5-minute happy path for new and existing repos.
- Lite/standard/strict preset selection with a recommended default.
- First-run trust snapshot with goal, stage, risk, evidence, next action, and verification signal.
- A minimal demo or dry-run fixture that can show value without external credentials.
- Runnable or observable acceptance signals for first-run success.
- Documentation updates only as needed to support the first happy path.
- Conservative copy that preserves pass/blocked/degraded and no-overclaim boundaries.

### Non-Goals

- Do not close RISK-036.
- Do not claim official approval, marketplace approval, official directory acceptance, universal runtime support, full runtime support, or 1.0.0 production-ready status.
- Do not solve cross-harness E2E expansion; that belongs to 0.43.0.
- Do not split composable governance packs; that belongs to 0.44.0.
- Do not create governance benchmark/eval claims; that belongs to 0.45.0.
- Do not prepare or submit the full official ecosystem package; that belongs to 0.46.0.
- Do not require all users to understand Agent Team, all stage gates, all review roles, or full release governance before the first value moment.

## Assumptions And Validation Plan

| Type | Statement | Validation plan |
| --- | --- | --- |
| Assumption | A user can perceive delivery trust value from one snapshot without understanding the full workflow. | Run 5 external first-session tests and ask users to name one trust signal they saw. |
| Assumption | The first happy path can complete without real external agent runtime E2E credentials. | Implement dry-run/demo fixture path and verify it is clearly labeled as demo/local, not full runtime support. |
| Assumption | Lite preset is the best default for first-run success, while standard remains recommended for real team projects after setup. | A/B test lite-default vs standard-default in pilot onboarding; compare time-to-first-signal and confusion count. |
| Assumption | Existing README wording is good enough for install but insufficient for first success proof. | Usability test: give users only README and measure whether they reach a trust snapshot in 5 minutes. |
| Recommendation | First-run output should be called "Delivery Trust Snapshot" to make value concrete. | Validate naming in PR/FAQ and pilot feedback; rename if users misinterpret it as release approval. |

## PR/FAQ

### Press Release

Software Project Governance 0.42.0 introduces a five-minute success path for AI coding users who need delivery trust before they adopt a full governance workflow.

After installation, a new user can run `/governance`, choose a default preset, and see a compact Delivery Trust Snapshot from their repository. The snapshot shows the project goal, current stage, open risk status, evidence readiness, next critical decision boundary, and one runnable or observable verification signal. The first experience is intentionally narrow: it demonstrates how the workflow prevents goal drift, missing evidence, weak review signals, and premature release claims without forcing the user to learn the entire governance model up front.

This release keeps the product's existing honesty boundary. It does not claim official marketplace approval, universal runtime support, or 1.0.0 production readiness. It makes the first value visible while RISK-036 continues to track broader official adoption readiness.

### FAQ

**1. What does a user actually see in 5 minutes?**

They see a Delivery Trust Snapshot: goal, stage, risk status, evidence status, next action, and a verification signal. The exact implementation can be CLI text, slash-command output, or a generated local markdown summary, but it must be visible without reading long documentation.

**2. Is this just another onboarding wizard?**

No. The first-run prompts are only useful if they produce a trust signal. The success criterion is not "the user initialized files"; it is "the user can explain one way the workflow will make AI coding delivery more trustworthy."

**3. Does the 5-minute path prove all agents are fully supported?**

No. The path must preserve pass/blocked/degraded wording. It may demonstrate a local or dry-run signal, but it must not imply full runtime support across Claude, Codex, Gemini, OpenCode, Cursor, Copilot, or other environments.

**4. Why not make Superpowers-style lightweight coding skills instead?**

That would blur the product position. Superpowers and agent skill packs help agents plan, test, debug, and review. This project should prove whether delivery remains aligned, evidenced, risk-aware, and release-safe.

**5. What is the first vertical slice?**

Implement the minimal first-run Delivery Trust Snapshot for a new or existing repo, with one demo path and one acceptance command/signal. Do not start with the full preset system, cross-runtime matrix, or governance pack split.

**6. What happens if the user already has `.governance/`?**

The happy path should resume instead of reinitialize. The snapshot should show carry-over work, open risks, hook state, or missing evidence as the first value signal.

**7. Does 0.42.0 close RISK-036?**

No. It reduces one adoption gap, but RISK-036 remains open until the broader 0.42.0-0.46.0 readiness chain, external validation, public runtime matrix, and official submission package are complete.

## OKR

### Objective

Make the first 5 minutes of Software Project Governance demonstrate AI coding delivery trust value without requiring the user to learn the full governance system.

| KR | Baseline | Target | Measurement |
| --- | --- | --- | --- |
| KR1: Time to first trust signal | Baseline: not yet measured; assumed 0/5 external users have completed a trust-signal explanation within 5 minutes because no constrained happy path exists. | 4/5 pilot users complete setup/resume and correctly explain one trust signal within 5 minutes. | Timed pilot using README + 0.42.0 path; evaluator records completion and explanation. |
| KR2: First-run concept load | Baseline: README introduces many concepts across install, governance, profiles, gates, evidence, and commands. | First happy path requires at most 3 user choices before the trust snapshot. | Prompt/output review and pilot observation. |
| KR3: No-overclaim preservation | Baseline: 0.41.0 release docs already preserve no official approval/full support claims. | 0 affirmative claims of official approval, marketplace approval, universal/full runtime support, or 1.0.0 production-ready in 0.42.0 first-run copy. | Focused text scan and Requirement Reviewer review. |
| KR4: Acceptance observability | Baseline: manual validation commands exist but are not framed as first-run success. | At least 1 runnable command or observable generated artifact proves the first-run snapshot was produced. | Release checklist or acceptance contract for 0.42.0 vertical slice. |

## Runnable Or Observable Acceptance Signals

The implementation tasks should choose exact commands, but AUDIT-106 recommends these acceptance signals:

| Signal | Type | Expected result |
| --- | --- | --- |
| First-run smoke command | Runnable | A command or slash-command path creates/resumes governance state and emits a Delivery Trust Snapshot in under 5 minutes on a small fixture repo. |
| Snapshot artifact | Observable | A local artifact or command output contains goal, stage, risk, evidence, next action, and no-overclaim wording. |
| Existing-project resume path | Runnable/observable | On a fixture with `.governance/`, first run resumes state and surfaces carry-over/open-risk signal instead of reinitializing. |
| No-overclaim scan | Runnable | Focused text scan finds no affirmative official approval, marketplace approval, universal/full runtime support, or production-ready claim. |
| Pilot usability result | Observable | At least 4/5 pilot users can name one trust signal after the 5-minute path. Planning baseline is 0/5 until measured. |

## Recommended 0.42.0 Task Split

| Task | Priority | Scope | Done definition |
| --- | --- | --- | --- |
| AUDIT-106 | P0 | This gap analysis and minimum slice plan. | Document covers user profiles, current gaps, competitors, PR/FAQ, OKR, non-goals, acceptance signals, RISK-036 boundary, and task split. |
| FIX-100 | P0 | First-run Delivery Trust Snapshot vertical slice. | `/governance` or equivalent first-run path emits a compact trust snapshot for a fixture/new repo with goal, stage, risk, evidence, next action, and verification signal. |
| FIX-101 | P0 | Existing-project resume happy path. | Fixture with existing `.governance/` resumes and surfaces carry-over/open-risk/hook state within 5 minutes, without reinitialization confusion. |
| FIX-102 | P1 | Lite/standard/strict preset simplification for first run. | First-run path defaults safely, asks no more than 3 non-critical questions before the snapshot, and records assumptions for deferred fields. |
| FIX-103 | P1 | Demo fixture and acceptance harness. | A small demo repo or fixture can run the first happy path and assert the snapshot fields; no external credentials required. |
| FIX-104 | P1 | README/docs first-success refinement. | README `5-Minute Start` points to the exact happy path and explains the first trust signal without expanding the full governance model. |
| REL-018 | P0 | Release 0.42.0. | Version bump, changelog, release docs, acceptance evidence, requirement review, release review, no-overclaim scan, commit/push/tag. |

## First Vertical Slice

### FIX-100: Delivery Trust Snapshot

The first slice should not be a full onboarding redesign. It should implement the smallest visible loop:

1. Use an empty or small fixture repo.
2. Run `/governance` or the closest supported command path.
3. Accept a default preset.
4. Create or simulate required local governance state.
5. Emit a Delivery Trust Snapshot with:
   - project goal,
   - current stage,
   - gate or setup status,
   - open risk count or "no open risks yet",
   - evidence status,
   - next action,
   - no-overclaim boundary if runtime support is degraded or demo-only.
6. Provide one runnable or observable verification signal.

Done definition: a reviewer can run or inspect the slice and see the trust snapshot without reading `plan-tracker.md`, `evidence-log.md`, `risk-log.md`, or the full SKILL file first.

## Requirement Quality Self-Check

| Criterion | Status |
| --- | --- |
| Real user profiles/scenarios | PASS: Maya, Leo, Nina include context, JTBD, pain, and success moment. |
| Current path gaps | PASS: gap table covers install, start, init, first output, validation, overclaim control, follow-up. |
| At least 3 competitor/adjacent comparisons | PASS: Superpowers, `addyosmani/agent-skills`, `wshobson/agents`, Anthropic official ecosystem. |
| PR/FAQ with at least 5 FAQs | PASS: 7 FAQ items. |
| OKR with at least one quantified KR and baseline/target | PASS: KR1 includes baseline and target; KRs 2-4 add supporting measures. |
| Explicit non-goals | PASS: non-goals section includes RISK-036 and overclaim boundaries. |
| Runnable/observable acceptance signals | PASS: signals table includes runnable and observable checks. |
| Follow-up task split with first vertical slice | PASS: FIX-100 is first vertical slice. |
| RISK-036 remains open and no official/full-support claims | PASS: explicitly preserved in executive summary, FAQ, non-goals, OKR, and release split. |
| Facts, assumptions, recommendations separated | PASS: source facts, assumptions table, and recommendations are labeled. |
