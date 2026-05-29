# Deterministic Scaffold: CLI Tool

Use this scaffold when the product is a command line utility, local automation, validation runner, data converter, or developer workflow command. The first slice should accept real inputs, produce deterministic output, return meaningful exit codes, and keep logs safe.

## Product Success Contract

- Persona: a developer or operator who needs a repeatable command instead of manual steps.
- JTBD: run one command with documented inputs, receive clear output, and know whether the job succeeded.
- Non-goal: do not build hidden interactive flows when a deterministic command and options can solve the first use case.
- Non-goal: do not accept success based on prose summaries, review approval, or unverified command descriptions.
- Success metric: user can run the command from a clean checkout and receive the expected output and exit code.
- Success metric: runnable test or fixture command proves success, failure, and help text behavior.
- Competitive baseline: strong internal tools make correct usage obvious through help output, fixtures, and stable exit codes.

## PRD-lite

- Problem: manual local operations are error-prone when each user has to reconstruct command syntax and expected outputs.
- User-visible workflow: run help, run the happy-path command against a fixture, inspect output, and observe a nonzero exit for invalid input.
- Inputs: command name, options, fixture path or stdin, target output path when needed.
- Outputs: concise stdout summary, structured file or report when needed, stderr for actionable failures, stable exit code.
- Out of scope for the first slice: background daemons, remote service orchestration, shell-specific aliases, and unrelated format support.

## Executable Acceptance

- `python skills/software-project-governance/infra/verify_workflow.py check-deterministic-scaffolds --fail-on-issues` verifies the scaffold library before implementation.
- `python -m unittest` or `pytest` proves parser, happy path, invalid input, and fixture behavior in the target project.
- Expected output: help text names the command, happy path returns exit code 0, invalid input returns a nonzero exit and actionable error.
- Demo evidence: terminal transcript or captured log with command, exit code, output summary, and fixture path.

## Quality Budget

- performance: fixture command completes within a bounded local runtime appropriate for the data size.
- reliability: tests cover help, happy path, missing input, invalid input, and deterministic output ordering.
- security: command output never prints secrets, tokens, passwords, or raw environment dumps.
- accessibility: help text is readable in a terminal, option names are descriptive, and errors explain recovery without color dependence.
- ux: the default output is concise, verbose output is opt-in, and exit codes map to user action.
- maintainability: parsing, validation, domain operation, and reporting have clear boundaries without inventing extra frameworks.

## Vertical Slice

- User-visible slice: a user runs the command against one fixture and receives a stable report with exit code 0.
- Demo path: unit test, fixture run, or shell transcript tied to a runnable command.
- Scope guard: one command, one fixture format, one output format, parser tests, and failure-path tests.
- Rollback plan: remove the command entry, fixture, tests, and generated docs for the slice.

## Demo Checklist

- Help output names required inputs and common options.
- Happy-path fixture run returns exit code 0.
- Invalid input returns a nonzero exit and actionable error.
- Output avoids secrets and machine-specific absolute paths unless explicitly needed.
- Evidence includes command, exit code, output summary, and fixture path.

## Tooling

- `python skills/software-project-governance/infra/verify_workflow.py check-product-success-contracts --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-acceptance-contracts --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-quality-budget --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-vertical-slices --fail-on-issues`
