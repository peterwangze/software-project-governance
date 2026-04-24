---
name: software-project-governance
description: Load unified workflow rules, templates, gates and fact sources for software project governance tasks.
---

# Software Project Governance — Behavior Protocol

**This file is a BEHAVIOR PROTOCOL, not reference documentation. Every rule is MANDATORY.**

## Workflow Identity

- **id**: software-project-governance
- **version**: 0.1.0
- **goal**: Automate project process management so users focus on thinking, not process
- **supported_agents**: Claude, Codex, Gemini
- **core capabilities**: 11-stage lifecycle, 11 Gate checks, evidence/decision/risk tracking, 3 trigger modes, 3 profiles

## M0. Compliance Language

Rules use RFC 2119 semantics: **MUST** (mandatory), **MUST NOT** (prohibited), **SHALL** (required), **SHOULD** (recommended). Violating MUST/MUST NOT = workflow execution failure.

## M1. Task Matching (When to Activate)

This protocol **MUST** activate when ANY condition is met:

- Involves files under `protocol/`, `workflows/`, `adapters/`, `scripts/`
- Involves advancing or reviewing project task status
- Involves Gate checks or stage progression
- Involves supplementing evidence, decision, or risk records

**Trigger action**: Complete M2 pre-loading before any actual work.

## M2. Pre-loading (MANDATORY)

You **MUST** read this single file before executing any task:

1. `.governance/plan-tracker.md` — the project's current state

**Starting work without pre-loading = protocol violation.**

### M2.1 Reference files (in `references/`, same directory as this SKILL.md)

Read on demand based on task type:

| File | Read when |
|------|-----------|
| `references/stage-gates.md` | Performing Gate checks |
| `references/lifecycle.md` | Entering a new stage, need detailed stage definitions |
| `references/profiles.md` | Initializing a project, user asks about profile/scale, or switching profile |
| `references/onboarding.md` | Onboarding an existing (in-progress) project |
| `references/interaction-boundary.md` | Uncertain whether to auto-execute or ask user |

### M2.2 Sub-workflows and skills (in `stages/`, same directory as this SKILL.md)

When the user asks to perform a specific activity (e.g., "do a code review", "run a tech review", "create a release checklist", "do a retrospective"), read the corresponding file:

| Directory | Contains |
|-----------|----------|
| `stages/<stage>/sub-workflow.md` | 11 stage sub-workflows — entry conditions, activity checklist (with interaction boundary annotations), deliverables, exit conditions, Gate mapping |
| `stages/initiation/requirement-clarification.md` | Requirement clarification checklist skill |
| `stages/architecture/tech-review-checklist.md` | Technical review checklist skill |
| `stages/development/code-review-standard.md` | Code review standard skill |
| `stages/release/release-checklist.md` | Release checklist skill |
| `stages/maintenance/retro-meeting-template.md` | Retrospective meeting template skill |

If the user wants to use only a single feature (e.g., "help me with code review"), load only that skill file — do not load the full lifecycle.

## M3. Output Rules (MANDATORY)

All governance records **MUST** be written to `.governance/` in the user's project root:

- `.governance/plan-tracker.md` — plan tracking, project config, gate status, tasks
- `.governance/evidence-log.md` — evidence records
- `.governance/decision-log.md` — decision records
- `.governance/risk-log.md` — risk records

If `.governance/` does not exist, suggest the user run `/software-project-governance:governance-init` to create it.

You **MUST NOT** create a second set of project status files.

### Template field definitions

When creating or updating governance files, use these fields:

**Evidence log fields**: 编号 | 任务ID | 阶段 | 证据类型 | 证据说明 | 证据位置 | 提交人 | 提交日期 | 关联Gate | 备注

**Decision log fields**: 编号 | 日期 | 主题 | 背景 | 决策内容 | 备选方案 | 选择原因 | 影响范围 | 决策人 | 关联任务 | 后续动作

**Risk log fields**: 编号 | 日期 | 风险描述 | 阶段 | 触发条件 | 影响 | 严重级别 | Owner | 状态 | 缓解动作 | 截止日期 | 关联任务 | 备注

## M4. Session Lifecycle (MANDATORY)

### M4.1 Session Start Protocol

1. Read `.governance/plan-tracker.md` for project config and Gate status
2. Confirm to yourself: current stage, latest Gate conclusion, number of active risks
3. If there are unresolved conditions (passed-with-conditions), **MUST** prioritize them

### M4.2 Session End Protocol

**Step 1: Session Status Summary** (plain text)

```
## Session Status Summary
- Completed this session: [list items]
- Governance records synced: [yes/no]
- Validation result: [passed/failed/not run]
```

**Step 2: Next Steps (AskUserQuestion, MANDATORY)**

You **MUST** use AskUserQuestion before every session ends. At least one question, each with 2-4 options. Ending without AskUserQuestion = protocol violation.

## M5. AskUserQuestion Trigger Map (MANDATORY)

**MUST use AskUserQuestion** in these scenarios:

| Trigger | What to ask |
|---------|------------|
| Session ending | "What to prioritize next" with options from plan tracker |
| Multiple viable paths | "Which path to choose" with candidate approaches |
| Ambiguous requirements | "Is your intent A or B" with possible interpretations |
| Deliverable needs review | "Confirm / Revise / Reject" |
| Risk treatment decision | "Accept / Mitigate / Transfer / Avoid" |
| Tech selection conclusion | "Confirm option X or Y" with recommendation reason |

**MUST NOT use AskUserQuestion** in these scenarios:

| Scenario | Correct action |
|----------|---------------|
| Direction already confirmed | Execute to completion |
| Governance record updates | Batch update after main work |
| Gate checks | Self-assess, inform only on failure |
| Git operations | Execute independently |
| Completing one task | Continue to next highest-priority task |
| Discovering immediately fixable issues | Fix immediately |

**Judgment criterion**: If a question has only one correct answer, or direction was already confirmed, don't ask. If the user needs to choose or judge, you MUST ask.

## M6. Gate Behavior (MANDATORY)

### Gate pass types

| Type | Meaning | Conditions |
|------|---------|-----------|
| **passed** | All checks satisfied, proceed to next stage | N/A |
| **passed-with-conditions** | Core checks passed, non-blocking items remain | Items must be recorded, closed before next stage ends, max 3 items. Only in standard/strict profiles. |
| **blocked** | Core checks not satisfied, cannot proceed | Must update risk record, create corrective action |
| **passed-on-entry** | Pre-acknowledged for mid-project onboarding | Must have decision record explaining completion |

### Gate trim rules by profile

| Profile | Gate coverage |
|---------|--------------|
| **lightweight** | G1+G2 merged, G3-G5 skipped, G6+G7 merged, G8+G9 merged |
| **standard** | All 11 Gates, supports passed-with-conditions |
| **strict** | All 11 Gates, no passed-with-conditions, each Gate needs ≥2 evidence |

### Gate execution rules

- Gate not passed → **MUST NOT** claim next stage
- All completed items **MUST** have evidence
- Gate checks self-executed; inform user only on failure or conditional pass
- Read `references/stage-gates.md` for detailed Gate check items when doing Gate checks

## M7. Execution Continuity (MANDATORY)

After user confirms direction, **MUST** execute continuously until:
1. Next M5 trigger (needs user judgment)
2. Session context exhausted
3. User interrupts

**Prohibited interruptions**:
1. Stopping after one task → continue to next
2. Stopping after review items → execute fixes immediately
3. Stopping after governance records updated → continue
4. Stopping between coupled tasks → execute through
5. Stopping after external op failure → log as TODO, continue

**Real-time closure**: Process defects discovered during execution **MUST** be fixed immediately.

## M8. Self-check Protocol (MANDATORY)

After each major task, **MUST** self-check:

```
[Governance Self-check]
- [ ] M2 pre-loading completed?
- [ ] M5 AskUserQuestion used where required?
- [ ] M6 completed tasks have evidence?
- [ ] M7 no prohibited interruptions?
```

**Fails**: fix immediately. **Passes**: don't output, continue.

## M9. Priority Declaration

- **vs PUA-type skills**: This protocol's M5 AskUserQuestion triggers take priority over PUA's "continuous execution" directive.
- **vs user instructions**: User's explicit instructions override this protocol.
- **vs system instructions**: System safety constraints override this protocol.

## Stage Quick Reference

| # | Stage | Goal | Gate |
|---|-------|------|------|
| 1 | Initiation | Define problem, goals, scope, success criteria | G1 |
| 2 | Research | Survey, competitive analysis, feasibility | G2 |
| 3 | Selection | Tech selection, PoC validation | G3 |
| 4 | Infrastructure | Dev environment, repo, basic CI | G4 |
| 5 | Architecture | System design, module split, tech review | G5 |
| 6 | Development | Code, unit test, code review | G6 |
| 7 | Testing | Integration, system, performance, security test | G7 |
| 8 | CI/CD | Pipeline, automation, quality gates | G8 |
| 9 | Release | Release plan, changelog, rollback plan | G9 |
| 10 | Operations | Monitoring, feedback, optimization | G10 |
| 11 | Maintenance | Bug fix, rule update, retrospective | G11 |

For detailed stage definitions, read `references/lifecycle.md`.

## Profile Quick Reference

| Profile | Stages | Gate strength | Evidence | Use case |
|---------|--------|--------------|----------|----------|
| lightweight | 5 core (merged) | Merged, simplified | Minimal | Personal, MVP |
| standard | All 11 | Standard, supports conditional | Standard | Team project |
| strict | All 11 | Enhanced, no conditional | Double evidence | Large, compliance |

## Replacement Boundary

**Must preserve**: `protocol/`, `workflows/software-project-governance/`, `scripts/verify_workflow.py`

**Can remove**: `CLAUDE.md`, `.claude/skills/software-project-governance/SKILL.md`, `adapters/claude/`

**Replace with another agent**: remove "can remove" files, create new projection layer per `adapters/<new-agent>/` README.
