# Deterministic Scaffold: Workflow Plugin

Use this scaffold when the product is an agent workflow, governance plugin, skill bundle, adapter layer, release gate, or local automation that guides AI-assisted development. The first slice must demonstrate a real user workflow through a documented entry point and a machine-checkable guard.

## Product Success Contract

- Persona: a human lead using AI agents to deliver software while keeping goals, evidence, review, and release quality aligned.
- JTBD: install or run the workflow entry, trigger one governed task path, and observe a clear pass or block decision.
- Non-goal: do not rely on long prompt compliance alone when a script, hook, or template can make the behavior deterministic.
- Non-goal: do not claim complete platform coverage without real runtime or explicitly blocked evidence.
- Success metric: user can run a plugin command that validates the intended governed behavior.
- Success metric: runnable fixture or E2E command proves the entry, guard, and evidence path work together.
- Competitive baseline: successful platform teams convert policy into paved paths, guardrails, fixtures, and release checks.

## PRD-lite

- Problem: AI workflows drift when policy is only written as guidance and not reinforced by executable checks.
- User-visible workflow: load the entry, inspect the task packet, run the guard command, and see a pass or actionable failure.
- Primary objects: entry file, skill or plugin template, execution packet, validator command, evidence shape, release check.
- Constraints: keep source of truth explicit, keep adapter claims fact-based, and preserve degraded-mode language where runtime capabilities are missing.
- Out of scope for the first slice: unrelated platform adapters, broad release version bumps, and undocumented runtime claims.

## Executable Acceptance

- `python skills/software-project-governance/infra/verify_workflow.py check-deterministic-scaffolds --fail-on-issues` verifies this scaffold set.
- `python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues` proves the workflow guard is wired into the current project.
- Expected output: the target guard reports pass for a valid fixture and fails with clear issues for missing contract fields.
- Demo evidence: command output, fixture path, and evidence entry with command, exit code, summary, file diff, and review conclusion.

## Quality Budget

- performance: governance checks complete quickly enough for pre-commit or release-gate use on the scoped fixture.
- reliability: positive and negative tests prove the guard does not pass placeholder, prose-only, or overbroad claims.
- security: evidence parsing rejects secrets and commands do not print credentials or raw environment dumps.
- accessibility: CLI output is readable without color, names failing fields, and gives enough context for the next action.
- ux: the workflow interrupts users only for decisions that require human judgment and defaults routine checks to automation.
- maintainability: validator logic, templates, adapter manifests, and docs stay in clearly owned files with focused tests.

## Vertical Slice

- User-visible slice: a user runs the workflow guard and sees that a missing or weak contract is blocked before closure.
- Demo path: fixture test, `check-governance`, or dedicated validator command tied to an evidence entry.
- Scope guard: one guard, one template family, one fixture path, focused docs, and regression tests for bypass cases.
- Rollback plan: remove the guard registration, template files, tests, and tool index entry introduced by the slice.

## Demo Checklist

- Entry file or skill names the governed workflow.
- Guard command passes on valid fixture data.
- Guard command fails on placeholder, review-prose, or overbroad fixture data.
- Expected result is visible in CLI output with field-level failure names when invalid fixture data is used.
- Adapter or runtime claims include real pass, blocked, degraded, or unsupported status.
- Evidence includes command, exit code, output summary, changed files, and independent review conclusion.

## Tooling

- `python skills/software-project-governance/infra/verify_workflow.py check-product-success-contracts --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-acceptance-contracts --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-quality-budget --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-vertical-slices --fail-on-issues`
