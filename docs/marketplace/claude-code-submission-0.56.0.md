# Claude Code Official Marketplace Submission Package - 0.56.0

Version target: 0.56.0

Related risk: RISK-036

## Purpose

This document is the actionable submission package for proposing `software-project-governance` to the Anthropic-managed Claude Code plugin directory (`anthropics/claude-plugins-official`). It captures the official submission channel, the pre-submission self-check, and the local verification steps. It does not constitute a submission, approval, or listing. The actual submission is a user action performed inside Claude Code.

## Official Submission Channel (Verified)

The official directory is `anthropics/claude-plugins-official` (https://github.com/anthropics/claude-plugins-official).

| Item | Detail |
| --- | --- |
| Repository | `anthropics/claude-plugins-official` — an Anthropic-managed curated directory of high-quality plugins. |
| Two marketplaces served | **Official** (Anthropic-written) at `main`, and **Community** (partly sourced by Anthropic) at `serving-community`. |
| Submission method | The repo does **not** directly accept plugin PRs. Submission is via the **in-app submission form** inside Claude Code, per the repo README and Claude Code docs. |
| Review standard | External plugins must meet Anthropic's quality and security standards. Anthropic does not formally endorse or vet every plugin; users must trust a plugin before installing. |
| Reserved name | `claude-plugins-official` is a reserved name for Anthropic use; submissions go through the review form, not direct PRs (GitHub issue #22310). |

Sources:
- https://github.com/anthropics/claude-plugins-official
- https://code.claude.com/docs/en/discover-plugins
- https://code.claude.com/docs/en/plugin-marketplaces
- https://code.claude.com/docs/en/plugins

## Self-Hosted Marketplace Already Available

The repository ships a self-hostable Claude Code marketplace registry that any Claude Code user can add today, independent of official review:

```bash
/plugin marketplace add peterwangze/software-project-governance
/plugin install software-project-governance@spg
```

The registry is `.claude-plugin/marketplace.json` with `name: "spg"`, an `owner` block, and a `plugins[]` array pointing at `source: "./"`. This is the `owner/repo` shorthand that Claude Code resolves to the repo's `.claude-plugin/marketplace.json`. This path works now; official directory inclusion is a separate, Anthropic-gated step.

## Pre-Submission Self-Check (0.56.0 Status)

| # | Requirement | Status | Notes |
| --- | --- | --- | --- |
| 1 | Open-source license | PASS (0.56.0) | `LICENSE` (MIT), `plugin.json`/`marketplace.json`/`package.json` license = `MIT`. Aligns with `superpowers` (MIT). `UNLICENSED` → `MIT` since 0.56.0. |
| 2 | Plugin structure `.claude-plugin/` | PASS | `.claude-plugin/plugin.json` + `marketplace.json` + `assets/`. |
| 3 | Marketplace registry `plugins[]` + `owner` | PASS | `.claude-plugin/marketplace.json` has owner + plugins[0] with source, version, license. |
| 4 | Skills/commands/agents entry points | PASS | `skills/` (main SKILL + role/stage skills), `commands/` (8 governance commands), `agents/` definitions. |
| 5 | README with install + trust guidance | PASS | README opens with an English first viewport: title, "AI coding delivery trust layer" tagline, and a value-proposition paragraph. Tier 1 install paths and a `/plugin marketplace add` code block are present. |
| 6 | README install path verified | PASS (documented) | README documents `/plugin marketplace add peterwangze/software-project-governance` and `/plugin install software-project-governance@spg`. Runtime verification against a target Claude Code version remains a pre-submit user step; a raw-URL fallback can be added if the shorthand is not resolved by a given Claude Code version. |
| 7 | Local validation before install | PASS | `verify_workflow.py` governance/manifest/version checks PASS; release gate PASS for 0.56.0. |
| 8 | Privacy/security boundary doc | PASS | `docs/marketplace/privacy-security.md` exists. |
| 9 | No overclaim | PASS | README + release docs consistently state no official/marketplace approval, no universal runtime support. |

## Format Alignment Checklist vs `anthropics/claude-plugins-official`

Before submitting, confirm the following match the official directory conventions (verify against the repo's README and an existing community plugin):

- [ ] `marketplace.json` top-level fields: `name`, `owner{name,url}`, `plugins[]`. (Present.)
- [ ] Each plugin entry: `name`, `description`, `source`, `version`, `license`. (Present; `source: "./"`.)
- [ ] `.claude-plugin/plugin.json` with `name`, `version`, `description`, `author`, `license`. (Present.)
- [ ] `LICENSE` file at repo root. (Present, MIT.)
- [ ] README install instructions using `/plugin marketplace add`. (Present.)
- [ ] No declared dependency on reserved/official names. (N/A — marketplace name is `spg`.)

## Submission Procedure (User Action — Not Automated)

1. Ensure all self-check items are PASS.
2. In Claude Code, open the plugin submission form (in-app).
3. Provide the repo `peterwangze/software-project-governance`, a concise value proposition, and the install verification.
4. Await Anthropic review. This package does not predict the outcome.

## No-Overclaim Boundary

This package prepares for submission; it does not submit, is not approved, and is not listed. The self-hosted marketplace works now for any Claude Code user; official directory inclusion is Anthropic-gated and not guaranteed. No official approval. No marketplace approval. No universal/full runtime support.

RISK-036 remains open. RISK-037 remains open.
