# Dynamic Lifecycle and Flow-Gate Redesign

Date: 2026-06-15

Scope: planning and requirements for replacing the fixed G1->G11 execution mental model with a dynamic, project-type-aware lifecycle and flow-gate model. This is a planning artifact only; implementation is split across 0.51.0-0.55.0.

## Trigger

Real external validation exposed a severe experience gap: the workflow currently presents a fixed G1->G11 progression, but real projects often advance by independent increments. A Python game may finish chapter 1 and chapter 2, move those slices through G6/G7/G9, and still have chapter 3-10 in design, content production, or validation. The current lifecycle can record this only awkwardly through tasks and notes, so the user sees a rigid process even when the project is naturally iterative.

## Research Summary

Mainstream software organizations keep process discipline, but they do not treat lifecycle phases as a single irreversible conveyor belt:

- GitLab presents phases for clarity, but explicitly says the product flow is not linear, phases may overlap, and teams may skip or shorten phases when confidence is high. GitLab separates Validation and Build tracks, validates customer problems when confidence is low, and uses MVC delivery, measurement, iteration, or restart when outcomes fail. Source: https://handbook.gitlab.com/handbook/product-development/how-we-work/product-development-flow/
- Google Engineering Practices push small, self-contained changes, related tests, vertical splitting, and keeping the system working after every submitted change. Source: https://google.github.io/eng-practices/review/developer/small-cls.html
- Google SRE release engineering emphasizes repeatable automated release processes, frequent releases, test-gated release candidates, canarying, and rollback. Source: https://sre.google/sre-book/release-engineering/ and https://sre.google/workbook/canarying-releases/
- GitHub Flow is lightweight and branch-based: isolated branches, isolated commits, pull-request review, status checks, protected-branch requirements, and merge only after requirements are satisfied. Source: https://docs.github.com/en/get-started/using-github/github-flow
- Microsoft SDL says security practices apply across classic waterfall and modern DevOps, and across software types including AI applications, mobile apps, web services, plug-ins, firmware, IoT, and low-code/no-code. Source: https://www.microsoft.com/en-us/securityengineering/sdl/
- Atlassian's agile guidance frames Scrum as iterative delivery through sprints and valuable increments, while Kanban supports continuous flow when incoming work and priorities shift. Epics are decomposed into stories that can deliver value independently. Source: https://www.atlassian.com/agile/scrum and https://www.atlassian.com/agile/project-management/epics-stories-themes
- DORA's 2024 research warns that AI increases individual productivity but can hurt delivery stability and throughput unless teams keep fundamentals such as small batch sizes, robust testing, user-centricity, and stable priorities. Source: https://dora.dev/research/2024/dora-report/

Conclusion: mature processes use stages as risk lenses and evidence expectations, while execution flows through smaller units: stories, MVCs, CLs, branches, release candidates, experiments, canaries, and feedback loops. The next workflow model should preserve governance discipline but attach gates to flow units, not only to a global project phase.

## Current Assets We Can Reuse

- `skills/software-project-governance/core/task-gate-model.md`: already defines task-level gates, dependency graph, local blocking, parallelism, and cycle detection.
- `skills/software-project-governance/core/profiles.md`: already supports gate merging/skipping and custom profile overrides, but by governance strength rather than project type.
- `skills/software-project-governance/core/lifecycle.md`: already allows overlapping adjacent stages and says rollback means filling gaps, not discarding completed work.
- `skills/software-project-governance/core/stage-gates.md`: already allows gate retry after gaps are fixed.
- Product success, executable acceptance, quality budget, and vertical-slice packet templates from 0.39.0 already define the right cross-cutting completion checks.
- Governance packs from 0.44.0 already separate capabilities from profile strength.
- Capability discovery from 0.45.0 already records scenario, selected capability, fallback, validation command, review requirement, and no-overclaim boundary.

## Target Model

The optimized model has four layers:

1. **Lifecycle Map**: the 11 classic stages remain available as a high-level risk map and backward-compatible preset, not the only execution path.
2. **Flow Units**: the primary work object becomes a flow unit such as `game.chapter.03`, `web.checkout.mfa`, `library.public-api`, `mobile.onboarding`, or `hotfix.payment-timeout`.
3. **Dynamic Gates**: each flow unit has gates selected from its project type, work type, risk level, enabled packs, and evidence availability.
4. **Loop Policy**: validation, development, test, release, operations, and maintenance can loop per flow unit. Passing one unit's gate does not imply all sibling units have passed.

For the Python game example:

| Flow unit | Current gate lane | Required checks |
| --- | --- | --- |
| Chapter 1 | released / operations feedback | playable smoke, save/load, UX feedback, defect budget, release notes |
| Chapter 2 | testing / release candidate | playable slice, narrative continuity, performance, regression, review |
| Chapter 3 | development | implementation acceptance, asset/content checklist, unit/smoke tests |
| Chapter 4-10 | design / backlog | chapter brief, dependency map, scope budget, non-goals |
| Engine/core systems | architecture / quality gates | API/design review, integration tests, performance/security budget |

The project-level status then becomes a rollup: "game project is in active build; chapter flow units are distributed across design, development, test, and release lanes."

## Non-Goals

- Do not delete G1-G11 in the first redesign release.
- Do not force every old project to migrate immediately.
- Do not turn every project type into a separate workflow product.
- Do not treat project-type presets as proof of quality, external validation, official approval, marketplace approval, or 1.0.0 readiness.

## Versioned Landing Plan

### 0.51.0 - Dynamic Lifecycle Spec

Goal: introduce the declaration layer without changing runtime behavior.

Tasks:

- FIX-135: add `core/lifecycle-registry.json` with `classic-phase-gate` preset, flow unit schema, stage/subphase vocabulary, loop policy, allowed transitions, gate references, and project-type hooks.
- REL-031: release 0.51.0 as a schema-only package with docs, examples, manifest coverage, and no runtime migration claim.

Acceptance:

- Existing G1-G11 checks still work.
- Validator can parse the lifecycle registry and report active lifecycle mode.
- The Python game chapter example is represented as data, not prose only.

### 0.52.0 - Flow Unit Runtime and Task-Gate Activation

Goal: make flow units and task gates visible in hot project state.

Tasks:

- FIX-136: add plan-tracker fields for `workflow_model`, flow units, dependency graph, per-unit gate state, active lanes, loop counters, blocked downstream units, and rollup status.
- REL-032: release 0.52.0 with governance status / context output able to summarize distributed flow-unit progress.

Acceptance:

- A project can show Chapter 1 as released, Chapter 2 as testing, Chapter 3 as development, and Chapter 4-10 as backlog without forcing the whole project to one global phase.
- Blocking one flow unit blocks only its declared downstream dependents.

### 0.53.0 - Project-Type Gate Presets

Goal: choose gate standards by project type and work type.

Tasks:

- FIX-137: add project-type presets for at least `game`, `web-app`, `mobile-app`, `library`, `cli-tool`, `ai-agent-plugin`, and `internal-script`; each preset maps default packs, flow-unit templates, quality budgets, acceptance templates, release checks, and optional/required gates.
- REL-033: release 0.53.0 with examples and no-overclaim guards.

Acceptance:

- `game` preset supports chapters/levels/assets/narrative/playability.
- `library` preset emphasizes API compatibility, semver, docs, examples, and downstream tests.
- `internal-script` preset is lightweight and avoids enterprise ceremony unless risk requires it.

### 0.54.0 - Declarative Gate Engine

Goal: move gate logic from hardcoded G1-G11 heuristics to registry-driven checks.

Tasks:

- FIX-138: introduce a gate/check registry where each gate is defined by required artifacts, evidence queries, automation commands, human-confirmation policy, severity, and project-type overrides.
- REL-034: release 0.54.0 with parity tests showing classic G1-G11 behavior is preserved through the declarative engine.

Acceptance:

- `auto_judge_gate` becomes an engine over registry definitions.
- Project-type gates can add checks without editing the engine for each new domain.

### 0.55.0 - Migration, Compatibility, and External Validation

Goal: make the redesign usable in real existing projects.

Tasks:

- FIX-139: add migration guide and command path from `classic-phase-gate` to `dynamic-flow-gate`, preserving old plan-tracker data and evidence.
- VAL-005: run a real Python game external validation focused on chapter/flow-unit lifecycle tracking.
- VAL-006: run one non-game external validation to prove presets are not game-specific.
- REL-035: release 0.55.0 only after migration and at least one real external dynamic lifecycle validation are archived.

Acceptance:

- Existing projects remain valid under `classic-phase-gate`.
- Dynamic projects can opt in without losing old evidence.
- 1.0.0 remains blocked until this redesign and RISK-036 closure standards are reconciled.

## Success Criteria

- Users can see a project-level lifecycle rollup and flow-unit-level gates at the same time.
- Passing a gate for one flow unit never implies sibling flow units are complete.
- Project-type presets change gate standards and templates without changing governance strength profile.
- AI agents receive shorter, scenario-specific execution packets instead of a global 11-stage script.
- The workflow can explain why it selected a gate path, what evidence is missing, which units are blocked, and what can continue in parallel.

## Risk Boundary

This planning package does not implement the dynamic runtime. It records the optimization direction and version plan. No official approval, marketplace approval, external validation full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, RISK-037 closure, or 1.0.0 readiness is claimed.
