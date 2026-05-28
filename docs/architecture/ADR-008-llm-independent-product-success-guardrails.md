# ADR-008: LLM-Independent Product Success Guardrails

## Status

Accepted for 0.39.0 planning.

## Context

Real usage exposed a severe failure mode: an agent can complete the workflow and still deliver a poor half-finished product when the underlying LLM is weak. The current 0.38.0 workflow already improves process reliability with runtime capability contracts, structured evidence, AI execution packets, degraded-mode handling, projection sync, and hot fact-source consistency. That makes the governance trail more trustworthy, but it does not yet prove that the delivered software is useful, competitive, or pleasant to use.

The core gap is that product judgment is still too implicit. The workflow checks whether tasks, evidence, reviews, and versions are coherent; it does not consistently force every user-visible change to carry an explicit product success contract, runnable acceptance proof, quality budget, demo path, and small vertical slice boundary.

## External Practice Signals

- DORA capabilities emphasize delivery performance through repeatable capabilities such as continuous delivery, test automation, fast feedback, small batches, and loosely coupled architecture: https://dora.dev/capabilities/
- Google SRE release engineering treats release as an engineered, repeatable discipline rather than an ad hoc final step: https://sre.google/sre-book/release-engineering/
- Google Engineering Practices code review asks reviewers to evaluate correctness, design, tests, complexity, and code health, not only whether code exists: https://google.github.io/eng-practices/review/reviewer/standard.html
- Microsoft SDL makes security requirements and threat modeling part of the lifecycle, not a late optional review: https://learn.microsoft.com/en-us/security/sdl/
- Atlassian Product Discovery frames discovery as validating problems, opportunities, and product direction before and during delivery: https://www.atlassian.com/agile/product-management/discovery
- GitHub Copilot coding agent guidance stresses well-scoped tasks, clear repository instructions, testable expectations, and human review: https://docs.github.com/en/enterprise-cloud@latest/copilot/using-github-copilot/coding-agent/best-practices-for-using-copilot-to-work-on-tasks
- Claude Code best practices similarly favor clear instructions, iterative work, testing, and context management over vague one-shot prompts: https://docs.anthropic.com/en/docs/claude-code/best-practices

## Decision

0.39.0 will add a product-success operating layer before 1.0.0 resumes. The goal is to move more intelligence out of the LLM and into executable workflow assets.

The planned 0.39.0 chain is:

- `FIX-088`: Product Success Contract
- `FIX-089`: Executable Acceptance Contract
- `FIX-090`: Quality Budget Gate
- `FIX-091`: Vertical Slice Delivery Packets
- `FIX-092`: Weak-LLM Deterministic Scaffolds
- `FIX-093`: User Interruption Policy v2
- `REL-014`: Release 0.39.0

## Design Principles

1. Product success must be explicit before implementation starts.
   Every P0/P1 user-visible task should name the user, job-to-be-done, non-goals, success metrics, competitive baseline, and done definition.

2. Completion must be executable.
   A task should not close on narrative evidence alone when it changes user-visible behavior. It needs a runnable acceptance command, E2E path, smoke path, or demo proof with expected results.

3. Quality must be budgeted.
   Performance, reliability, security, accessibility, UX, and maintainability need default thresholds or explicit exceptions. The workflow should make exceptions visible instead of letting the LLM silently skip them.

4. Delivery should prefer vertical slices.
   Large goals should be broken into user-visible increments with a demo path and rollback/scope guard. This reduces the chance of a polished process around an unusable artifact.

5. Weak LLMs need rails, not pep talks.
   Common project types should have deterministic scaffolds for product contracts, acceptance maps, quality budgets, and verification scripts.

6. The user should be interrupted only for thinking.
   The workflow should pause for product intent, acceptance standards, irreversible decisions, and risk acceptance. Routine formatting, task bookkeeping, and default implementation choices should proceed and record assumptions.

## Consequences

- 1.0.0 remains blocked until 0.39.0 closes `RISK-034`.
- Future execution packets must evolve from process packets into product-success packets.
- Release readiness must eventually include acceptance and quality-budget checks, not only version and evidence checks.
- The workflow will become less dependent on the chosen LLM because more of the product bar is represented as templates, schemas, commands, and gates.

