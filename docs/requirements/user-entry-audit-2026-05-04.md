# User Entry Point Audit Report — software-project-governance v0.29.0

Date: 2026-05-04
Analyst: 阿析
Scope: README.md install links, command references, command/skill inventory, governance entry logic

---

## Executive Summary

Found **2 blocking errors**, **4 UX issues**, and **4 optimization suggestions**. The most critical finding is that README.md references a non-existent repo name (`peterwangze/governance`) in all install commands, while the actual repository is `peterwangze/software-project-governance`. This means **users following the README's install instructions will hit 404 errors**.

---

## 1. Installation Links — Repository Name Mismatch

### 1.1 README References

| Location | README Text | Actual Value | Status |
|----------|-------------|-------------|--------|
| Line 22 | `/plugin marketplace add peterwangze/governance` | repo `peterwangze/software-project-governance` | **MISMATCH** |
| Line 26 | `/plugin install https://github.com/peterwangze/governance.git` | repo `peterwangze/software-project-governance` | **MISMATCH** |
| Line 29 | `git clone https://github.com/peterwangze/governance.git` | repo `peterwangze/software-project-governance` | **MISMATCH** |
| Line 30 | `/plugin install /path/to/governance` | local path reference — neutral | OK (user provides path) |
| Line 38 | `git clone https://github.com/peterwangze/governance.git` (Codex) | repo `peterwangze/software-project-governance` | **MISMATCH** |

Git remote confirms: `origin  git@github.com:peterwangze/software-project-governance.git`

### 1.2 Install Command Format Analysis

```
README says:  /plugin marketplace add peterwangze/governance
              /plugin install software-project-governance@spg

Actual marketplace.json (.claude-plugin/):
  {
    "name": "spg",
    "plugins": [{ "name": "software-project-governance", "source": "./" }]
  }

Actual plugin.json (.claude-plugin/):
  {
    "name": "software-project-governance",
    "version": "0.29.0"
  }
```

**Verdict**: The marketplace name (`spg`) and plugin name (`software-project-governance`) are consistent. The `/plugin install software-project-governance@spg` command would work IF the marketplace was correctly registered. But the marketplace registration command (`/plugin marketplace add peterwangze/governance`) points to a non-existent repo.

### 1.3 Evidence

- `.claude-plugin/plugin.json`: plugin name = `"software-project-governance"` (L2)
- `.claude-plugin/marketplace.json`: marketplace name = `"spg"` (L2), plugin = `"software-project-governance"` (L9)
- Git remote: `git@github.com:peterwangze/software-project-governance.git`
- README L22: `/plugin marketplace add peterwangze/governance`

> **Category: RED — Blocking Error**
> 
> Users following the README will attempt to add a marketplace from `peterwangze/governance` which does not exist. The correct command should reference `peterwangze/software-project-governance`.

---

## 2. Command References — Namespace and Coverage Gaps

### 2.1 README Command Table (Lines 78-83)

The README lists ONLY these four commands:

| README Command | Exists in commands/ | File Status |
|---------------|---------------------|-------------|
| `/governance:governance-init` | YES | Active (marked as "shortcut" — recommends `/governance`) |
| `/governance:governance-status` | YES | Active (marked as "shortcut" — recommends `/governance`) |
| `/governance:governance-gate G6` | YES | Active |
| `/governance:governance-verify` | YES | Active (marked as "shortcut" — recommends `/governance`) |

### 2.2 Commands MISSING from README

| Command | File | Status |
|---------|------|--------|
| `/governance` | `commands/governance.md` | **MISSING** — This is the PRIMARY unified entry point. README never mentions it. |
| `/governance-cleanup` | `commands/governance-cleanup.md` | **MISSING** |
| `/governance-review` | `commands/governance-review.md` | **MISSING** |
| `/governance-update` | `commands/governance-update.md` | OK to omit — marked "已弃用" (deprecated) |

### 2.3 README Also Mentions Commands in Body Text

- Line 98: `/governance:governance-init` (inline, in "第一步" section)
- Line 107: `/governance:governance-init` (inline, in fallback paragraph)
- Line 186: `/governance:governance-verify` (inline, in "验证" section)

None of these inline references mention `/governance` as the unified entry.

> **Category: YELLOW — UX Issue**
> 
> The README advertises a fragmented command interface that the project has already deprecated in favor of `/governance`. Three commands explicitly redirect users to `/governance` but the README never mentions it. Two newer commands (cleanup, review) are invisible to users.

### 2.4 Command Namespace Prefix

The README uses the prefix `/governance:` for all commands. However:

- Plugin name: `software-project-governance` (per `.claude-plugin/plugin.json`)
- Marketplace name: `spg` (per `.claude-plugin/marketplace.json`)
- No registered entity is named `governance`

Claude Code's plugin command naming convention typically uses `plugin-name:command-name`. If this convention holds:

- Expected: `/software-project-governance:governance-init`
- README says: `/governance:governance-init`
- Shortest possible: `/spg:governance-init` (if marketplace name is the namespace)

The `/governance:` prefix does not correspond to any registered identifier. It is plausible that the README author intended to use a shortened alias, but this alias is not backed by any configuration file.

> **Category: RED — Blocking Error (conditional)**
> 
> If Claude Code requires commands to be namespaced by plugin name or marketplace name, then `/governance:governance-init` will not resolve. Users will see "command not found." This needs verification against Claude Code's actual plugin command resolution behavior.

---

## 3. Command and SKILL Entry Point Inventory

### 3.1 Complete Command List (`commands/`)

| # | File | Purpose | README Listed? | Status |
|---|------|---------|:---:|--------|
| 1 | `governance.md` | Unified governance entry (decision tree router) | NO | **PRIMARY** |
| 2 | `governance-init.md` | Project initialization (shortcut to Scenario A) | YES | Active (legacy shortcut) |
| 3 | `governance-status.md` | Status display (shortcut to Scenario F) | YES | Active (legacy shortcut) |
| 4 | `governance-gate.md` | Specific Gate check | YES | Active |
| 5 | `governance-verify.md` | Health check (shortcut to Scenario E) | YES | Active (legacy shortcut) |
| 6 | `governance-cleanup.md` | Declarative plugin cleanup | NO | Active |
| 7 | `governance-update.md` | Bootstrap update | NO | **DEPRECATED** |
| 8 | `governance-review.md` | Manual review trigger | NO | Active |

### 3.2 Complete SKILL Entry List (`skills/*/SKILL.md`)

Total: **26 SKILL entries**

**Phase SKILLs (8):**
| SKILL | File |
|-------|------|
| stage-initiation | `skills/stage-initiation/SKILL.md` |
| stage-research | `skills/stage-research/SKILL.md` |
| stage-selection | `skills/stage-selection/SKILL.md` |
| stage-infra | `skills/stage-infra/SKILL.md` |
| stage-architecture | `skills/stage-architecture/SKILL.md` |
| stage-development | `skills/stage-development/SKILL.md` |
| stage-testing | `skills/stage-testing/SKILL.md` |
| stage-cicd | `skills/stage-cicd/SKILL.md` |
| stage-release | `skills/stage-release/SKILL.md` |
| stage-operations | `skills/stage-operations/SKILL.md` |
| stage-maintenance | `skills/stage-maintenance/SKILL.md` |

*(11 stage skills — covers all 11 lifecycle stages)*

**Tool SKILLs (6):**
| SKILL | File |
|-------|------|
| okr | `skills/okr/SKILL.md` |
| pr-faq | `skills/pr-faq/SKILL.md` |
| six-pager | `skills/six-pager/SKILL.md` |
| requirement-clarification | `skills/requirement-clarification/SKILL.md` |
| release-checklist | `skills/release-checklist/SKILL.md` |
| retro-meeting | `skills/retro-meeting/SKILL.md` |

**Review SKILLs (7):**
| SKILL | File |
|-------|------|
| code-review | `skills/code-review/SKILL.md` |
| design-review | `skills/design-review/SKILL.md` |
| requirement-review | `skills/requirement-review/SKILL.md` |
| test-review | `skills/test-review/SKILL.md` |
| release-review | `skills/release-review/SKILL.md` |
| retro-review | `skills/retro-review/SKILL.md` |
| tech-review | `skills/tech-review/SKILL.md` |

**Entry SKILLs (2):**
| SKILL | File |
|-------|------|
| software-project-governance | `skills/software-project-governance/SKILL.md` (Coordinator entry) |
| main-workflow | `skills/main-workflow/SKILL.md` (scene matching) |

### 3.3 plugin.json Registration

Contents of `.claude-plugin/plugin.json`:

```json
{
  "name": "software-project-governance",
  "version": "0.29.0",
  "description": "...",
  "author": { "name": "peterwangze" },
  "keywords": ["project-management", "governance", "workflow", "code-review", "agent-team"]
}
```

**No `commands` array, no `skills` array.** This is a minimal plugin.json that declares identity but does not register any commands or skills. Claude Code's plugin system may or may not auto-discover commands from the `commands/` directory — this depends on Claude Code's version-specific behavior.

> **Category: YELLOW — UX Issue**
> 
> If Claude Code requires explicit `commands` and `skills` entries in plugin.json, then NONE of the 8 commands or 26 skills are actually registered for user invocation. This would mean the plugin installs successfully but exposes no slash commands.

### 3.4 User-Visible Entry Points (Current State)

Based on what actually exists vs what README says:

| Entry Point | Type | User Can Invoke? | README Says? |
|------------|------|:---:|:---:|
| `/governance` | Slash command | YES | **NO** |
| `/governance-init` | Slash command (legacy) | YES | YES (but format wrong) |
| `/governance-status` | Slash command (legacy) | YES | YES (but format wrong) |
| `/governance-gate` | Slash command | YES | YES (but format wrong) |
| `/governance-verify` | Slash command (legacy) | YES | YES (but format wrong) |
| `/governance-cleanup` | Slash command | YES | **NO** |
| `/governance-review` | Slash command | YES | **NO** |
| `software-project-governance` SKILL | SKILL entry | YES (via Skill tool) | Not as user command |
| 26 sub-SKILLs | SKILL entry | YES (via Skill tool) | Mentioned indirectly |

---

## 4. SKILL Entry Logic — Overlap Analysis

### 4.1 `skills/software-project-governance/SKILL.md` (Coordinator Entry)

First 50 lines establish:
- **Identity**: "You are the Coordinator (老周) — not a 'single agent task executor', but the leader of an Agent Team"
- **Architecture**: 6-layer architecture (adapters -> entry -> business intelligence -> capability -> infra -> core)
- **Role**: Coordinating 7 functional groups with 13 agents
- **Rules**: Direct product code modification forbidden; all user interaction via AskUserQuestion; sub-agents never talk to users directly

### 4.2 `commands/governance.md` (Unified Command Entry)

First 60 lines establish:
- **Design principle**: Auto-classify, don't ask users; minimal AskUserQuestion; secure defaults; session continuity
- **Bootstrap division**: CLAUDE.md bootstrap = "power-on self-test" (automatic, minimal). /governance = "dashboard" (full interaction, on-demand)
- **Decision tree**: 6 scenarios (A: new project init, B: mid-way onboarding, C: upgrade, D: session recovery, E: anomaly recovery, F: status display)

### 4.3 Functional Overlap Analysis

| Dimension | SKILL.md (Coordinator) | governance.md (Command) |
|-----------|----------------------|------------------------|
| **When loaded** | Plugin installed -> agent loads SKILL at session start | User types /governance |
| **Scope** | Comprehensive: all governance behavior, agent team coordination, lifecycle management | Operational: state display, scenario routing, anomaly handling |
| **User interaction** | Indirect (through bootstrap and agent behavior) | Direct (slash command invocation) |
| **Content duplication** | Defines Coordinator identity, agent routing, behavior protocol | Defines decision tree for governance scenarios |
| **Overlap** | Both handle session recovery (SCENARIO D in command vs SKILL's cross-session restore) | Both check `.governance/` existence |

**Key Insight**: The SKILL.md and governance.md serve DIFFERENT purposes with minimal overlap. SKILL.md is the "runtime personality" of the agent — loaded automatically, defining HOW the agent behaves. governance.md is the "user-facing dashboard" — invoked explicitly, showing WHAT the project state is.

The overlap is at the session recovery point: SKILL.md Step 1 reads `session-snapshot.md` for carry-over tasks; governance.md Scenario D also handles session recovery. This is intentional — SKILL's bootstrap handles the automatic recovery on session start, while `/governance` handles the explicit recovery when the user asks for it.

> **Category: GREEN — Suggestion**
> 
> The dual entry (SKILL.md + governance.md) is architecturally sound. SKILL.md is auto-load behavior; governance.md is user-invoked dashboard. The overlap at session recovery is by design. However, the README leads users to the legacy fragmented commands instead of the unified `/governance` entry.

### 4.4 Deprecated Commands Still Present

`commands/governance-update.md`: Marked "已弃用" (deprecated). Its content says: "已弃用——使用 `/governance`". It is retained as "manual fallback." This creates confusion — should users EVER use this?

> **Category: YELLOW — UX Issue**
> 
> A deprecated command with 4617 bytes of documentation is still in the commands/ directory. If it's truly deprecated, it should either be removed or its documentation reduced to a one-line redirect. Keeping it as a "fallback" without clear criteria for when to use it creates cognitive load.

---

## 5. Consolidated Findings Summary

### RED — Blocking Errors (2)

| # | Finding | Impact | Evidence |
|---|---------|--------|----------|
| **E1** | README install commands reference `peterwangze/governance` — repo does not exist. Actual repo is `peterwangze/software-project-governance`. | Users cannot install. All install paths break. | `git remote -v` confirms repo name. README L22, L26, L29, L38 all use wrong name. |
| **E2** | README command namespace `/governance:` does not match any registered entity (plugin `software-project-governance`, marketplace `spg`). | Users may see "command not found" for all 4 documented commands. | `.claude-plugin/plugin.json` L2, `.claude-plugin/marketplace.json` L2. No entity named "governance." |

### YELLOW — UX Issues (4)

| # | Finding | Impact |
|---|---------|--------|
| **U1** | README never mentions the unified `/governance` command — the project's PRIMARY user entry. | Users learn a fragmented, legacy interface. New users never discover the streamlined path. |
| **U2** | Two active commands missing from README: `/governance-cleanup` and `/governance-review`. | Users don't know these features exist. |
| **U3** | `governance-update.md` is deprecated but still fully documented in commands/. | Creates dead weight and confusion about whether it should ever be used. |
| **U4** | `.claude-plugin/plugin.json` is minimal — no `commands` or `skills` arrays. | If Claude Code requires explicit registration, all 8 commands and 26 skills are unreachable. |

### GREEN — Optimization Suggestions (4)

| # | Suggestion |
|---|-----------|
| **S1** | Replace README's "常用命令" table with a single `/governance` command, then link to a detailed command reference. Three legacy shortcuts can be documented as "also available." |
| **S2** | Add `commands` and `skills` arrays to `.claude-plugin/plugin.json` for explicit registration, removing ambiguity about plugin discovery behavior. |
| **S3** | Remove `governance-update.md` or reduce it to a 3-line redirect stub. A "deprecated fallback" that nobody knows when to use is worse than no fallback. |
| **S4** | Verify the command namespace resolution: does `/governance:governance-init` actually work in a Claude Code instance with this plugin installed? If not, determine the correct format (likely `/software-project-governance:governance-init`) and update README. |

---

## 6. Verification Items (Not yet confirmed)

These items require a live Claude Code instance with the plugin installed to verify:

- [ ] **V1**: Does `/plugin marketplace add peterwangze/software-project-governance` resolve correctly?
- [ ] **V2**: Does `/plugin install software-project-governance@spg` work after marketplace is added?
- [ ] **V3**: What command namespace does Claude Code actually register? Is it `/governance:`, `/software-project-governance:`, `/spg:`, or something else?
- [ ] **V4**: Are commands auto-discovered from `commands/` directory without explicit plugin.json registration?
- [ ] **V5**: Does `/governance` (the unified command) actually work as a slash command?

---

## 7. Appendix: Repo vs README Cross-Reference

| Aspect | Actual (from repo) | README says | Mismatch |
|--------|-------------------|-------------|:---:|
| Repo name | `software-project-governance` | `governance` (in URLs) | YES |
| Primary command | `/governance` | `/governance:governance-init` | YES |
| Plugin name | `software-project-governance` | `governance` (in namespace prefix) | YES |
| Marketplace name | `spg` | `spg` (in install cmd) | NO |
| Available commands | 8 | 4 | YES |
| Deprecated commands | 1 (update) | 0 mentioned | YES |
