# Privacy and Security Posture

Audience: official marketplace evaluators, security-conscious adopters, and team leads reviewing Software Project Governance before installation.

This document describes repository facts for version 0.41.0 readiness work. It is not a legal privacy policy, terms page, or listing approval notice.

## Local data boundary

| Area | Boundary |
| --- | --- |
| Governance records | Runtime state is written to the current project-local `.governance/` directory when the workflow is initialized and used. |
| Repository sample records | This repository's own `.governance/` directory is dogfood/sample runtime data for this project, not a template that should be copied into adopter projects. |
| Skills and docs | The workflow reads local skill, agent, command, adapter, and documentation files from the installed repository package. |
| Evidence | Evidence records are intended to describe local commands, diffs, review status, risks, and decisions. They should not contain secrets, tokens, passwords, private keys, or production credentials. |
| External policy links | No external privacy or terms link is introduced by this 0.41.0 readiness slice. |

## Permissions and side effects

The workflow is designed to coordinate local project governance. Depending on the host agent, user approvals, and project mode, it may guide or run local actions such as:

- Creating or updating project-local governance records under `.governance/`.
- Reading repository files needed for governance state, skill instructions, validation, and review.
- Running local validation commands such as `verify_workflow.py`, cross-reference checks, manifest checks, and release readiness checks.
- Installing or using git hooks when the adopter chooses to enable workflow enforcement.
- Invoking git commands, commits, pushes, package installs, or other side-effecting commands only when the active governance mode and host permissions allow them.
- Coordinating agent roles for development, review, testing, release, and maintenance when the host environment supports those capabilities.

The package should be evaluated as a workflow and validation layer, not as a silent background service. Side effects are local command and file-system side effects unless a host agent or user-directed command performs network or git remote operations.

## Runtime capability honesty

Runtime support is conservative and environment-dependent.

| Capability area | Stated posture |
| --- | --- |
| Claude Code plugin path | Supported installation path is documented, with project initialization still required before normal use. |
| Codex package assets | The repository provides `.codex-plugin/plugin.json` and `skills/software-project-governance/SKILL.md`; exact loading behavior depends on the Codex environment. |
| Other agents | Compatibility may be degraded, blocked, or pending validation depending on native skill loading, tools, browser support, AskUserQuestion support, reviewer separation, and git hook behavior. |
| Reviewer separation | Real independent review must be distinguished from degraded or self-review-like evidence. Degraded evidence must not be presented as independent approval. |
| E2E status | Pass, blocked, and degraded statuses should stay visible. Environment-dependent limitations must not be hidden behind broad support claims. |

## No telemetry service

This repository does not define a telemetry service, hosted analytics collector, or hosted monitoring backend for the workflow.

The workflow records governance facts in local project files. If a host AI coding environment, shell command, package manager, git remote, or third-party tool performs network activity, that behavior belongs to that host or command path and should be reviewed separately.

## No official acceptance claim

This package does not claim official marketplace acceptance, listing approval, or availability in every runtime.

0.41.0 readiness work prepares documentation, metadata, and review artifacts so evaluators can inspect the package more easily. Acceptance, listing, or approval can only be determined by the relevant marketplace process.

## Evaluator Review Pointers

| Review topic | Local file or command |
| --- | --- |
| Package metadata | `.codex-plugin/plugin.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` |
| First-screen positioning | `README.md` |
| Official readiness gaps | `docs/marketplace/official-readiness-gap-analysis-0.41.0.md` |
| Privacy/security posture | `docs/marketplace/privacy-security.md` |
| Submission readiness | `docs/marketplace/submission-checklist-0.41.0.md` |
| Validation entry | `python skills/software-project-governance/infra/verify_workflow.py verify` |
