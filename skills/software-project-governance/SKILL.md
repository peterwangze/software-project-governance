---
name: software-project-governance
description: Load unified workflow rules, templates, gates and fact sources for software project governance tasks.
---

# Software Project Governance — Behavior Protocol

**This file is a BEHAVIOR PROTOCOL, not reference documentation. Every rule is MANDATORY.**

## Workflow Identity

- **id**: software-project-governance
- **version**: 0.7.3
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
- Involves audit execution (any of the 6 audit dimensions in `references/audit-framework.md`)
- Involves supplementing evidence, decision, or risk records

**Trigger action**: Complete M2 pre-loading before any actual work.

## M2. Pre-loading (MANDATORY)

You **MUST** read these files before executing any task:

1. `main-workflow.md` — the unified workflow entry point: two fundamental purposes, three-tier architecture, scene→sub-workflow matching rules, cross-tier invocation protocol
2. `.governance/plan-tracker.md` — the project's current state

**Starting work without pre-loading = protocol violation.**

### M2.1 Reference files (relative to this SKILL.md's directory)

Read on demand based on task type:

| File | Read when |
|------|-----------|
| `main-workflow.md` | **Always** — confirms fundamental purposes and matching rules (skill root, not in `references/`) |
| `TOOLS.md` | Need to find a specific tool/script/checklist (skill root, not in `references/`) |
| `references/stage-gates.md` | Performing Gate checks |
| `references/lifecycle.md` | Entering a new stage, need detailed stage definitions |
| `references/profiles.md` | Initializing a project, user asks about profile/scale, or switching profile |
| `references/onboarding.md` | Onboarding an existing (in-progress) project |
| `references/interaction-boundary.md` | Uncertain whether to auto-execute or ask user |
| `references/audit-framework.md` | Performing Gate checks, completing a stage, completing a Tier (per DEC-052 layered execution model), completing a P0 task, after significant changes |
| `references/agent-failure-modes.md` | Agent behavior anomaly detected (protocol skip, selective execution, false closure, hallucinated evidence) — troubleshoot and execute emergency actions |
| `references/agent-team-architecture.md` | Designing or evolving the Agent Team architecture — Coordinator + role agents + Task-Gate model. Read when planning architecture evolution, defining new agent roles, or migrating from Phase-Gate to Agent Team model |
| `references/user-perspective-principle.md` | **Every task** — before completing any change that affects user behavior, MUST verify user accessibility, discoverability, and verifiability. Also loaded when planning/designing new features |
| `references/data-boundary.md` | Clarifying user project data vs workflow sample data boundary — read when discussing data isolation or plugin deployment |
| `references/agent-entry-differences.md` | Understanding Claude/Codex/Gemini/domestic agent CLI entry path differences — read when expanding multi-agent support |

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

### M2.3 M5 Interaction Signal (MANDATORY — applies to ALL sub-workflow executions)

**When executing any sub-workflow or skill from `stages/`**, the agent **MUST** apply the following M5 interaction binding:

- All activities marked **`需用户确认`**, **`需用户输入`**, or **`需用户判断`** in the sub-workflow's 交互边界 (interaction boundary) column **MUST** be executed via the **AskUserQuestion** tool — per M5.1, inline text questions are protocol violations.
- The trigger phrases `询问用户` or `问用户` in sub-workflow text are **instructions to use AskUserQuestion**, NOT instructions to output inline text questions.
- The phrase `告知用户` (inform/tell the user) in sub-workflow text is a **one-way notification** — it does NOT require AskUserQuestion (not a question), but the agent SHOULD prefix such notifications with a clear signal that they are informational, not interactive.
- **Self-check before any user interaction**: "Am I about to output an inline question? If yes → STOP, use AskUserQuestion instead. Am I about to deliver a one-way notification? If yes → prefix with 'ℹ️' to distinguish from questions."

**Why this signal exists**: FIX-013 (M5 audit) fixed gaps in SKILL.md trigger coverage, but the root cause of M5 bypass persisted: sub-workflows contain natural-language interaction patterns (e.g., `询问用户："当前项目目标是什么？"`) that agents read as direct instructions to output inline text. M2.3 closes this gap by establishing a binding rule: sub-workflow interaction annotations → AskUserQuestion tool. The binding is enforced by verify_workflow.py's M5 anti-pattern check (Check 10).

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

### M3.1 DRI (Directly Responsible Individual) Rule (MANDATORY)

Every task **MUST** have exactly one DRI — a single accountable person (Apple DRI model + Amazon Single-Threaded Owner).

**DRI assignment rules**:
- Owner column **MUST** be single-valued — one person/agent, not "X + Y"
- If multiple names appear in Owner → task is **unassigned**, not shared
- Each task **MUST** have an Escalation column — who to escalate to when blocked
- DRI has decision authority within the task's scope (decides how to execute)
- Decisions outside task scope → escalate to the Escalation person

**AI agent DRI specific**:
- When agent is DRI: agent has authority on execution decisions, human is Escalation
- When human is DRI: agent is collaborator, human makes key decisions
- DRI boundary aligns with M5.3 critical decision classification — DRI decides non-critical, Escalation decides critical

**Gate check**: Each active task without a DRI → Gate passes with conditions + corrective task created.

## M4. Session Lifecycle (MANDATORY)

### M4.1 Session Start Protocol

1. Read `.governance/plan-tracker.md` for project config and Gate status
2. **Cross-session state recovery (MANDATORY)**: Read `.governance/session-snapshot.md` if it exists. Compare with `.governance/plan-tracker.md`:
   - Tasks marked "in_progress" in snapshot but still "in_progress" in plan-tracker → these are carry-over tasks, continue
   - Tasks marked "in_progress" in snapshot but "未开始" in plan-tracker → stale snapshot, ignore
   - Decisions marked "pending" in snapshot → check if they were resolved in another session
   - Risks with escalation deadlines ≤ current date → escalate immediately
3. Confirm to yourself: current stage, latest Gate conclusion, number of active risks, carry-over tasks
4. If there are unresolved conditions (passed-with-conditions), **MUST** prioritize them

### M4.2 Session End Protocol

**Step 1: Generate Session Snapshot (MANDATORY)**

You **MUST** write `.governance/session-snapshot.md` at session end. This file preserves cross-session continuity:

```markdown
# Session Snapshot — {{DATE}}

## Current State
- **Stage**: {{CURRENT_STAGE}}
- **Active parallel stages**: {{ACTIVE_PARALLEL_STAGES}}
- **Profile**: {{PROFILE}}
- **Trigger mode**: {{TRIGGER_MODE}}
- **Last Gate**: {{LAST_GATE_ID}} — {{LAST_GATE_RESULT}}

## Carry-over Tasks
| Task ID | Description | Status | Since | Notes |
|---------|-------------|--------|-------|-------|
{{CARRY_OVER_TASKS}}

## Pending Decisions
| Decision ID | Question | Context | Created |
|-------------|----------|---------|---------|
{{PENDING_DECISIONS}}

## Active Risks
| Risk ID | Description | Escalation deadline | Days remaining |
|---------|-------------|---------------------|----------------|
{{ACTIVE_RISKS}}

## Completed This Session
{{COMPLETED_ITEMS}}

## Unfinished Work
{{UNFINISHED_ITEMS}}

## Next Session Priority
{{NEXT_PRIORITY}}
```

**Step 2: Session Status Summary** (plain text)

```
## Session Status Summary
- Completed this session: [list items]
- Governance records synced: [yes/no]
- Validation result: [passed/failed/not run]
```

**Step 3: Next Steps (AskUserQuestion, MANDATORY)**

You **MUST** use AskUserQuestion before every session ends. At least one question, each with 2-4 options. Ending without AskUserQuestion = protocol violation.

## M5. AskUserQuestion Protocol (MANDATORY)

### M5.1 The Only Legal Question Channel

**AskUserQuestion is the ONLY legal way to ask the user anything.** Inline text questions (e.g., "Should I proceed?", "Do you want me to...?", "要继续吗？", "要不要") are protocol violations. Every user-facing question MUST go through the AskUserQuestion tool.

**Self-interruption protocol (MANDATORY)**: If you catch yourself about to output an inline question — STOP IMMEDIATELY. Delete the question text. Replace it with an AskUserQuestion tool call. This is not optional. The most common violation pattern is ending a response with a natural-language confirmation question (e.g., "要继续吗？", "需要我继续吗？", "Shall I proceed?"). These are LLM conversational defaults, not instructions from any file — and they are M5.1 violations just the same.

**Why FIX-015 wasn't enough**: FIX-015 cleaned up source file contamination (sub-workflow files containing `询问用户："..."` instructions). But inline questions like "要继续吗？" are NOT caused by contaminated files — they are the LLM's natural conversational pattern, appearing billions of times in training data. No file told the agent to ask "要继续吗？" — it's how LLMs naturally end responses. The only defense is a pre-output self-check that catches the pattern BEFORE it reaches the user. This is why CLAUDE.md SELF-CHECK item #4 exists.

Rationale: Inline text doesn't enforce structured options, doesn't prevent the agent from continuing without reading the answer, and degrades the user experience. AskUserQuestion ensures the user sees a clear question with bounded options and the agent MUST wait for the response.

### M5.2 Trigger Map — When to Ask

**MUST use AskUserQuestion** in these scenarios:

| Trigger | What to ask |
|---------|------------|
| Session ending | "What to prioritize next" with options from plan tracker |
| Multiple viable paths | "Which path to choose" with candidate approaches |
| Ambiguous requirements | "Is your intent A or B" with possible interpretations |
| P0 task completion | "Confirm / Revise / Reject" — per M7.4 step 5, ALL P0 tasks and governance-critical file changes MUST trigger deliverable review via AskUserQuestion before continuing. Skipping this = M5 under-use violation |
| Deliverable needs review | "Confirm / Revise / Reject" |
| Risk treatment decision | "Accept / Mitigate / Transfer / Avoid" |
| Tech selection conclusion | "Confirm option X or Y" with recommendation reason |
| Critical decision point | Per M5.3 classification — stop and ask |
| Risk escalation triggered | "Fix / Record exception / Defer" — when check-governance detects stale risk or passed escalation deadline |
| Audit finding (Block/Deviation) | "Fix now / Schedule as task / Accept risk" — when audit discovers blocking or deviation-level findings |
| Destructive git operation (default-confirm mode only) | "Force push / reset --hard / branch -D?" — per interaction-boundary dangerous operations. Non-destructive git (commit, push, pull) auto-execute per M5.3/M5.4 |

### M5.3 Critical Decision Classification

The user MAY declare at session start (or at any point): **"仅在关键决策停下来"** (stop only for critical decisions). When this mode is active:

**Critical decisions** — MUST stop and use AskUserQuestion:
- Scope change (adding/removing features, changing project boundary)
- Architecture decision (tech stack, module split, interface design)
- Release decision (go/no-go, version bump, breaking change)
- Risk acceptance (accepting a known risk, bypassing a Gate)
- External dependency change (new library, new service, API change)
- Profile/trigger mode change
- **Stage jump (skipping a Gate)** — pre-acknowledged risk with decision-log recording required

**Non-critical decisions** — auto-execute, do NOT ask:
- Task ordering within confirmed direction
- Evidence format and detail level
- Commit timing at natural boundaries (commit autonomously per DEC-025)
- Governance record updates
- Minor implementation choices (file naming, variable names, code style)
- Gate self-assessment results (inform only on failure)

**Judgment criterion**: If the decision changes project direction, scope, architecture, or accepts risk → critical, MUST ask. If the decision is about how to execute within confirmed direction → non-critical, execute autonomously.

### M5.4 When NOT to Ask

| Scenario | Correct action |
|----------|---------------|
| Direction already confirmed | Execute to completion **until a new critical decision (per M5.3) arises during execution.** Do not re-ask about the already-confirmed direction. |
| Governance record updates | Batch update after main work |
| Gate checks (individual technical check items) | Self-assess, inform only on failure. **Stage advancement confirmation (entering next stage)** is a separate Type C interaction per interaction-boundary.md — MUST use AskUserQuestion. |
| Non-destructive git operations (commit, push, pull, status, diff, log) | Execute independently (commit per DEC-025). Destructive git (force push, reset --hard, branch -D) → AskUserQuestion per M5.2 trigger. |
| Completing one task | Continue to next highest-priority task |
| Discovering immediately fixable issues | Fix immediately |
| Non-critical decision in "stop only for critical" mode | Execute autonomously |

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

- Gate not passed → **MUST NOT** claim next stage *in full-workflow mode*. Standalone sub-workflow or tool usage (per main-workflow.md scene matching) requires only goal anchor and quality baseline checks — gate progression is not enforced in standalone mode.
- All completed items **MUST** have evidence
- Gate checks self-executed; inform user only on failure or conditional pass
- Read `references/stage-gates.md` for detailed Gate check items when doing Gate checks

## M7. Execution Continuity (MANDATORY)

After user confirms direction, **MUST** execute continuously until:
1. Next M5 critical decision trigger (if user chose "stop only for critical")
2. Next M5 trigger of any kind (if user chose "stop for all decisions")
3. Session context exhausted
4. User interrupts

### M7.1 User Decision Mode Declaration

At session start or when direction is confirmed, the agent **SHALL** apply one of these modes:

| Mode | Behavior | Default for |
|------|----------|-------------|
| **Stop for critical only** | Auto-execute non-critical decisions; AskUserQuestion only for M5.3 critical list | standard, strict profiles |
| **Stop for all decisions** | AskUserQuestion for every M5.2 trigger | lightweight profile, first-time users |

The agent infers the mode from the project profile. The user can override at any time by saying "仅在关键决策停下来" or "所有决策都问我".

### M7.2 Prohibited Interruptions

These are NEVER valid reasons to stop **within a session** (session end per M4.2/M5.2 is a valid boundary):
1. Stopping after one task → continue to next, **except for P0/governance-critical task deliverable review per M7.4 step 5**
2. Stopping after **self-identified fixable defects** → execute fixes immediately. **Deliverable review requiring user judgment MUST use AskUserQuestion per M5.2.**
3. Stopping after governance records updated → continue
4. Stopping between coupled tasks → execute through
5. Stopping after external op failure → log as TODO, continue
6. **Inline text questions** → MUST use AskUserQuestion instead (M5.1)

### M7.3 Real-time Closure

Process defects discovered during execution **MUST** be fixed immediately. If the fix would change project direction/scope/architecture → it's a critical decision, use AskUserQuestion. If the fix is procedural (rules, templates, governance files) → execute immediately.

**Risk escalation deadline enforcement** (AUDIT-045): open risks with a passed escalation deadline (risk-log "截止日期" column) **MUST** be escalated — either closed with resolution or upgraded to a higher severity level. Risks left "打开" past their deadline are a protocol violation. `check-governance` Check 8 detects open risks with passed deadlines.

**Task deadline enforcement** (AUDIT-048): active tasks ("未开始" or "进行中") with a passed "计划完成" date **MUST** be escalated — either completed, re-planned with a new deadline, or explicitly deprioritized. `check-governance` Check 9 detects tasks with passed plan-complete dates.

### M7.4 Task Completion Protocol (MANDATORY)

After marking any task as "已完成" in `.governance/plan-tracker.md`, the agent **MUST** execute these 6 steps in order, as an atomic non-skippable sequence:

1. **Write evidence** — add an entry to `.governance/evidence-log.md` per M3 field definitions. Every completed task MUST have corresponding evidence.
2. **Run external validation** — `python scripts/verify_workflow.py check-governance`. Per M8.1, script validation catches structural issues agent self-check cannot.
3. **Self-audit** — if the task was P0, or modified any governance-critical file (SKILL.md, stage-gates.md, audit-framework.md, verify_workflow.py, lifecycle.md, profiles.md, onboarding.md, interaction-boundary.md, agent-failure-modes.md, main-workflow.md, TOOLS.md), execute D1 (goal alignment) + D4 (change closure) audit dimensions per `references/audit-framework.md`. Record audit conclusion in evidence-log.
4. **Deliverable review (BEFORE commit — MANDATORY for P0/governance-critical tasks)** — if the completed task was P0 priority OR modified any governance-critical file (SKILL.md, stage-gates.md, audit-framework.md, verify_workflow.py, lifecycle.md, profiles.md, onboarding.md, interaction-boundary.md, agent-failure-modes.md, main-workflow.md, TOOLS.md, pre-commit-hook.sh, post-commit-hook.sh, governance-init.md, CLAUDE.md) → **MUST** use AskUserQuestion to present the deliverable for user review. **The AskUserQuestion IS the output for this step.** DO NOT output a standalone summary or analysis before it — the summary lives INSIDE the AskUserQuestion body. The question body contains a brief summary of what was done and asks the user to confirm. Options: "Confirm — proceed to commit" / "Revise — needs changes" / "Reject — roll back". **Review comes BEFORE commit: commit is the reward for passed review, not the trigger to skip it.** Skipping this review for P0 tasks = M5 under-use violation (Failure Mode 11). For non-P0, non-governance-critical tasks → proceed to step 5.
5. **Commit** — `git add` the changed governance files and `git commit` with a message that **MUST** contain the task ID as prefix (e.g., "AUDIT-044: description", "MAINT-028: description"). Per DEC-025, every meaningful change is a commit unit. Task completion IS a commit boundary. The task ID prefix is the link between the code change and the plan-tracker entry — without it, traceability is broken. Commit messages without a task ID prefix are detectable by check-governance Check 7.
6. **Continue** — proceed to the next highest-priority task in plan-tracker per M7 execution continuity. If and only if the next task choice involves a critical decision (M5.3) → use AskUserQuestion. Otherwise → execute autonomously.

**Skipping any step = protocol violation.** The agent **MUST NOT** declare a task "done" without completing all 6 steps.

**Why review comes before commit (structural fix for Failure Mode 11)**: M5 under-use recurred 7 times because the old sequence (commit → review) created a structural trap: commit provides cognitive closure, and the summary that follows it satisfies the impulse to "tell the user what happened." The standalone summary competes with AskUserQuestion for the terminal slot — and summary always wins because it's simpler and doesn't pause for input. Two structural changes break this trap: (1) review moves BEFORE commit, so commit becomes the reward for passed review rather than the trigger to skip it; (2) the summary is embedded INSIDE the AskUserQuestion — there is no standalone summary output. The AskUserQuestion IS the deliverable review. This removes the summary as a competing terminal action and makes review the only path to closure.

**Protocol design rationale**: Each of the 4 violations detected in the AUDIT-040 incident (no audit triggered, no auto-commit, execution interrupted, inline question instead of AskUserQuestion) maps to a missing step in the task completion sequence. By making the sequence explicit and atomic, the protocol eliminates the gaps that allowed each violation. The M7.4 sequence has been restructured so that review gates commit rather than following it — ensuring unreviewed changes are never committed.

### M7.5 Pre-Task Protocol (MANDATORY)

Before executing any task that modifies files tracked in the repository, the agent **MUST** execute these steps in order:

1. **Verify task tracking** — check `.governance/plan-tracker.md`: does a task entry exist for this work? The task entry MUST have: a valid task ID (e.g., AUDIT-XXX, MAINT-XXX), a DRI assignment, a priority level, and a clear description of the expected output.
2. **If task not found → create first** — add a new task entry to plan-tracker with all required fields per the plan-tracker template (ID, 阶段, 任务项, 目标/预期结果, 输入, 输出, Owner/DRI, 协同角色, Escalation, 状态="进行中", 优先级, 计划开始, 计划完成, Gate, 验收标准). Then proceed with execution.
3. **If task found but status is "未开始"** → update status to "进行中" before starting work.
4. **Reference task ID in all commits** — every commit message **MUST** contain the task ID as prefix (e.g., "AUDIT-044: description"). Per DEC-025 and M7.4 step 4. The task ID in the commit message is the link between the code change and the plan-tracker entry — without it, traceability is broken.

**Modifying files without a corresponding plan-tracker entry = protocol violation.** Untracked modifications corrupt the project's traceability — without a task ID, evidence can't be linked, Gate checks can't verify completion, and the project Owner can't reconstruct why a change was made. Every file modification MUST be traceable back to exactly one task in plan-tracker.

**Why this protocol exists**: AUDIT-043 (M7.4 fix) was implemented BEFORE being added to plan-tracker — 8 files modified, 5 version declarations bumped, but no task entry existed. The task was retroactively created as AUDIT-043 after the code was already committed. M7.5 prevents this pattern by requiring the task entry to exist FIRST. AUDIT-044 is the first task to follow this protocol — the task entry was committed (04d0b7c) before any implementation began.

## M8. Self-check Protocol (MANDATORY)

After each major task, **MUST** self-check:

```
[Governance Self-check]
- [ ] M2 pre-loading completed?
- [ ] M5.1 no inline text questions? All user questions via AskUserQuestion?
- [ ] M5.2/M5.3 AskUserQuestion used where required? Non-critical decisions auto-executed?
- [ ] M6 completed tasks have evidence?
- [ ] M7 no prohibited interruptions? Decision mode respected?
- [ ] M7.4 task completion protocol executed? (evidence → check-governance → audit → **deliverable review BEFORE commit** → commit → continue). NO standalone summary before review — the AskUserQuestion IS the output.
- [ ] M7.5 pre-task protocol executed? (task in plan-tracker before modifying files?)
- [ ] M7.3 risk escalation deadlines checked? Any open risks past deadline?
- [ ] M7.3 task deadlines checked? Any active tasks past plan-complete date?
- [ ] M5 source clean? (Check 10: no `询问用户` anti-patterns in staged skill files; bootstrap has AskUserQuestion rule)
```

**Fails**: fix immediately. **Passes**: don't output, continue.

### M8.1 External Validation (Dual Mechanism)

Agent self-check alone is insufficient — an agent that violates protocol will also not honestly self-report violations (self-audit contradiction). This protocol therefore requires a **dual mechanism**: agent self-check (M8) + independent script validation.

**Independent script validation** via `python scripts/verify_workflow.py check-governance` performs 10 checks that the agent cannot fake:

| Check | What it detects | Why agent self-check can't catch it |
|-------|----------------|-------------------------------------|
| 1. Evidence completeness | Completed tasks without evidence entries | Agent may "forget" to write evidence |
| 2. Risk staleness | Open risks >7 days without update | Agent has no built-in staleness awareness |
| 3. Gate consistency | Gate status vs evidence mismatch | Agent may mark Gate passed without evidence |
| 4. Evidence quality | Circular refs, session-context refs, empty claims | Agent may produce self-referencing or transient evidence |
| 5. Protocol compliance | DRI violations, conditional passes without corrective tasks, evidence format errors | Structural violations agent won't self-report |
| 6. Tier audit completeness | Completed Tiers without TIER-X-Y-AUDIT evidence | Agent may skip Tier audit, and agent self-check won't detect it (same self-audit contradiction as Check 5) |
| 7. Commit-task traceability | Commits without task ID references in message | Agent may modify files without creating a plan-tracker entry first — untracked changes corrupt traceability |
| 8. Risk escalation deadline | Open risks with passed escalation deadlines | Agent has no built-in deadline awareness — risk deadlines pass silently |
| 9. Task deadline enforcement | Active tasks with passed plan-complete dates | Same pattern as Check 8 — task deadlines exist but are never enforced |
| 10. M5 AskUserQuestion compliance | Source files containing `询问用户` anti-patterns (teaching agent to output inline questions); bootstrap missing AskUserQuestion rule; interaction-boundary.md missing AskUserQuestion bindings | Agent reads sub-workflow files containing literal `询问用户："..."` instructions and follows them literally — outputting inline text instead of using AskUserQuestion. Agent self-check can't detect this because the agent is following the (contaminated) instruction it read. Static anti-pattern detection catches the ROOT CAUSE before the agent encounters it |

**When to run external validation** (MANDATORY):
- Before declaring a Gate as passed → run check-governance, confirm 0 issues
- At session end → run check-governance, fix any issues before closing
- After completing a P0 task → run check-governance to verify governance integrity

**Session end protocol** (M4.2) **MUST** include running `python scripts/verify_workflow.py check-governance` as validation step. If check-governance reports issues, they **MUST** be fixed before session end.

This dual mechanism eliminates the "student grading their own exam" problem — agent self-check for immediate execution quality, script validation for structural governance integrity.

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

**Must preserve** (project root paths, not relative to this SKILL.md): `./protocol/`, `./workflows/software-project-governance/`, `./scripts/verify_workflow.py`

**Can remove**: `./CLAUDE.md`, `./adapters/claude/`

**Replace with another agent**: remove "can remove" files, create new projection layer per `adapters/<new-agent>/` README.
