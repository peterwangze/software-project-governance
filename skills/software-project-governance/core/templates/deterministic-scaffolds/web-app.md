# Deterministic Scaffold: Web App

Use this scaffold when the product is primarily experienced in a browser: an internal dashboard, CRUD application, workflow console, report viewer, or task-focused SaaS surface. Keep the first slice small enough that a user can open it, complete one meaningful workflow, and see a result.

## Product Success Contract

- Persona: an operator who needs to complete a repeated browser workflow without reading implementation notes.
- JTBD: open the app, enter or inspect domain data, make one decision, and receive a visible confirmation or updated state.
- Non-goal: do not build marketing pages, oversized hero sections, or decorative panels before the working flow is usable.
- Non-goal: do not treat component creation, evidence entries, or review approval as product success.
- Success metric: user can complete the primary scenario in the browser and observe the expected state change.
- Success metric: runnable smoke or E2E command passes and proves the browser route, interaction, and visible result.
- Competitive baseline: mature product teams ship a thin end-to-end browser path before expanding settings, reports, or polish.

## PRD-lite

- Problem: users lose trust when a browser app has screens but no complete workflow.
- User-visible workflow: load the route, inspect the starting state, perform the primary action, and see a confirmation or updated record.
- Primary objects: route, page state, form or control, persisted or computed result, empty state, error state.
- Constraints: keep navigation predictable, keep labels concrete, avoid one-note visual themes, and maintain keyboard reachable controls.
- Out of scope for the first slice: admin configuration, multi-tenant permissions, analytics exports, and large visual redesigns.

## Executable Acceptance

- `python skills/software-project-governance/infra/verify_workflow.py check-deterministic-scaffolds --fail-on-issues` verifies the scaffold library before implementation.
- `npm test -- --runInBand` or `npm run test:e2e` proves the browser scenario in the target project when the app stack exists.
- Expected output: the smoke or E2E run reports pass, and the captured route shows the primary user action and visible result.
- Demo evidence: screenshot, browser trace, or CLI output path recorded in evidence with command, exit code, and summary.

## Quality Budget

- performance: first meaningful workflow route is usable without unnecessary blocking work; validation uses browser smoke timing or target framework performance check.
- reliability: empty, loading, success, and error states are covered by tests or fixture scenarios.
- security: user input is encoded, secret values stay out of logs, and auth-sensitive actions require explicit permission boundaries.
- accessibility: controls have names, focus order follows the workflow, contrast is readable, and keyboard operation covers the primary path.
- ux: the screen is dense enough for repeated use, avoids explanatory wall text, and keeps primary action placement stable.
- maintainability: page state, domain logic, and presentation are separated only where the local stack already benefits from that boundary.

## Vertical Slice

- User-visible slice: a user opens the browser route, performs one domain action, and sees a confirmation or changed state.
- Demo path: browser smoke test, Playwright trace, or local route screenshot tied to a runnable command.
- Scope guard: one route, one workflow, one primary data shape, focused tests, and minimal styles needed for the scenario.
- Rollback plan: revert the route, tests, and data fixture introduced for the slice.

## Demo Checklist

- The route loads from a clean checkout.
- The primary action can be completed without hidden setup.
- The visible result matches the acceptance expectation.
- Empty and failure states are understandable to the target persona.
- Evidence includes command, exit code, output summary, and artifact path when available.

## Tooling

- `python skills/software-project-governance/infra/verify_workflow.py check-product-success-contracts --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-acceptance-contracts --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-quality-budget --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-vertical-slices --fail-on-issues`
