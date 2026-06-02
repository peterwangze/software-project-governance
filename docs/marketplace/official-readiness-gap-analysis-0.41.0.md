# 0.41.0 Official Marketplace Readiness Gap Analysis

Date: 2026-06-02
Task: AUDIT-105
Version target: 0.41.0

## Purpose

0.41.0 turns the project from an internally strong governance workflow into a package that Codex and Claude marketplace reviewers can understand quickly. The package should present Software Project Governance as an AI coding delivery trust layer: goal alignment, evidence, risk, quality budget, real E2E status, degraded-mode honesty, and release gates.

This audit compares the current repository against two source facts:

- OpenAI `plugins/superpowers` Codex manifest contains package metadata plus `skills` and rich `interface` metadata: display name, short and long descriptions, developer, category, capabilities, default prompts, website, privacy policy, terms, brand color, composer icon, logo, and screenshots.
- Claude Code plugin documentation requires plugin metadata, a README, validation before installation, marketplace repository submission, and user trust around what the plugin can do.

## Current Package State

| Area | Current state | Readiness |
| --- | --- | --- |
| Codex manifest | `.codex-plugin/plugin.json` has `name`, `version`, `description`, `author.name`, and `keywords`. | Partial |
| Claude manifest | `.claude-plugin/plugin.json` has the same minimal metadata as Codex. | Partial |
| Claude marketplace index | `.claude-plugin/marketplace.json` points at the plugin and current version. | Partial |
| README first screen | README opens in Chinese and positions the product as project governance/process automation. | Not ready for official English review |
| Assets | No plugin logo, composer icon, screenshots, or marketplace visual assets were found under `.codex-plugin`, `.claude-plugin`, `docs`, `project`, or `skills`. | Missing |
| Privacy/security | No dedicated privacy, security, terms, or data-boundary page is linked from plugin manifests. | Missing |
| Submission checklist | Release checklists exist, but no official marketplace submission checklist exists. | Missing |
| Differentiation | DEC-072 and the competitive roadmap define "AI coding delivery trust layer", but the public first screen and manifests do not yet carry that message. | Partial |

## P0 Gaps

1. Codex interface metadata is missing.
   Current `.codex-plugin/plugin.json` cannot express the user-facing plugin card expected by the OpenAI Superpowers example: display name, concise value proposition, category, capabilities, default prompts, brand color, logo/icon, screenshots, website, privacy policy, and terms.

2. Public README positioning is not marketplace-ready.
   The current first screen is useful for an existing Chinese-speaking project user, but official reviewers and new users need an English first viewport that says what the product is, what problem it solves, and why it is different from methodology skill packs.

3. Trust and data-boundary documentation is missing.
   This workflow reads and writes local project governance records, runs validation commands, can invoke git, and may coordinate agents. The package needs explicit privacy/security wording before it is suitable for marketplace review.

4. Visual assets are missing.
   Official marketplace readiness needs at least a logo/icon and ideally screenshots or simple visual previews of governance status, evidence, and release readiness.

5. Submission checklist is missing.
   The repository has release checklists, but 0.41.0 needs a marketplace-specific checklist covering manifest fields, assets, README, docs, validation, E2E status, risk disclosures, and no-overclaim rules.

## P1 Gaps

1. Claude plugin metadata is less rich than the Codex package can be.
   Claude's plugin manifest does not appear to use the same `interface` block, but it still benefits from homepage, repository, license, author URL/email, and consistent keywords.

2. Default prompts are absent.
   A reviewer cannot see high-value entry prompts such as "Set up governance for this repo" or "Check whether this release is ready".

3. Marketplace claims need pass/blocked/degraded wording.
   The public package must avoid implying full coverage for Codex/Gemini/opencode where runtime state is degraded or environment-dependent.

4. Existing release docs are version-specific rather than package-review-specific.
   They prove release discipline, but they do not answer official reviewer questions about install, permissions, trust, rollback, and support.

## Recommended 0.41.0 Task Split

| Task | Priority | Scope | Done definition |
| --- | --- | --- | --- |
| AUDIT-105 | P0 | Official marketplace readiness gap analysis | This document exists, cites source facts, and turns DEC-072/REQ-082 into executable 0.41.0 tasks. |
| FIX-096 | P0 | Codex/Claude plugin metadata readiness | `.codex-plugin/plugin.json`, `.claude-plugin/plugin.json`, and `.claude-plugin/marketplace.json` contain official-review-friendly metadata without overclaiming runtime support. |
| FIX-097 | P0 | README English first-screen repositioning | README first viewport clearly presents "AI coding delivery trust layer", install paths, trust/data boundary summary, and a concise 5-minute path pointer. |
| FIX-098 | P0 | Privacy/security and submission checklist docs | Add dedicated trust docs and a marketplace submission checklist linked from manifests/README. |
| FIX-099 | P1 | Marketplace assets | Add logo/icon assets and at least one inspectable screenshot or rendered preview plan; manifests reference tracked assets. |
| REL-017 | P0 | Release 0.41.0 | Version bump, changelog, release docs, release gate, independent release review, commit, push, and tag. |

## First Vertical Slice

The first implementation slice should be FIX-096 because it is small, reviewable, and immediately changes marketplace inspectability:

- Add Codex `interface` metadata based on the OpenAI Superpowers manifest shape.
- Add homepage, repository, license, richer author, and keywords to both Codex and Claude manifests.
- Add conservative default prompts focused on governance setup, release readiness, and evidence quality.
- Avoid new runtime claims; keep pass/blocked/degraded distinctions for later 0.43.0 public matrix work.
- Run `check-version-consistency`, `verify`, `check-governance --fail-on-issues`, and a focused manifest validation check if one exists or is added.

## Non-Goals For 0.41.0

- Do not claim official acceptance.
- Do not claim full runtime support across all agents.
- Do not solve the 5-minute success path; that is 0.42.0.
- Do not implement cross-harness E2E expansion; that is 0.43.0.
- Do not split governance packs; that is 0.44.0.

## Source Facts

- OpenAI plugins Superpowers manifest: `https://raw.githubusercontent.com/openai/plugins/main/plugins/superpowers/.codex-plugin/plugin.json`
- Claude Code plugins documentation: `https://code.claude.com/docs/en/plugins`
- Local competitive roadmap: `project/workflows/software-project-governance/research/competitive-positioning-and-official-marketplace-roadmap.md`
