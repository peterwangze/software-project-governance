---
name: software-project-governance
description: Load unified workflow rules, templates, gates and fact sources for software project governance tasks.
---

# Software Project Governance

When a task involves planning, designing, verifying, evolving, or maintaining the software project governance workflow, use this skill.

## Use this skill when

- Modifying assets under `protocol/`, `workflows/`, `adapters/`, `scripts/`
- Advancing or reviewing task status in the current project sample
- Checking whether Gates allow stage progression
- Supplementing evidence, decisions, or risk records to ensure process credibility

## Required read order

Before execution, read and understand in this order:

1. `workflows/software-project-governance/manifest.md`
2. `protocol/workflow-schema.md`
3. `protocol/plugin-contract.md`
4. `workflows/software-project-governance/rules/lifecycle.md`
5. `workflows/software-project-governance/rules/stage-gates.md`
6. `workflows/software-project-governance/templates/plan-tracker.md`
7. `workflows/software-project-governance/templates/evidence-log.md`
8. `workflows/software-project-governance/templates/decision-log.md`
9. `workflows/software-project-governance/templates/risk-log.md`
10. `workflows/software-project-governance/examples/current-project-sample.md`

## Output rules

**User project** (standard path): All governance records are written to `.governance/` in the user's project root:

- `.governance/plan-tracker.md` — plan tracking, project config, gate status, tasks
- `.governance/evidence-log.md` — evidence records
- `.governance/decision-log.md` — decision records
- `.governance/risk-log.md` — risk records

If `.governance/` does not exist, suggest the user run `/governance-init` to create it.

**Dogfood mode** (when developing this workflow itself): Records go to:

- `workflows/software-project-governance/examples/current-project-sample.md`
- `workflows/software-project-governance/examples/current-project-evidence-log.md`
- `workflows/software-project-governance/examples/current-project-decision-log.md`
- `workflows/software-project-governance/examples/current-project-risk-log.md`

Do not create a second set of project status files.

## Gate behavior

- If a Gate is not passed, do not claim to have entered the next stage.
- If deviations or blockers are found, update risk records or decision records.
- All completed items must have supporting evidence.

## Execution principle

**Core principle: Users think, the workflow executes. Only stop when user judgment is genuinely needed.**

### When to stop

Only pause execution and wait for user input via interactive prompts in these scenarios:
1. **Directional decisions**: Multiple viable paths exist and user needs to choose
2. **Requirement clarification**: Task description is ambiguous with multiple interpretations
3. **Quality gates**: Deliverables need user review before proceeding

### When NOT to stop

Do not stop for:
- Tasks where direction has already been confirmed
- Governance record updates (decisions, evidence, risks) - batch update after main work
- Gate checks - self-assess, only inform user when not passed
- Validation script runs - run independently, only inform on failure
- All file operations (create, edit, directory creation)
- After completing one task - continue to the next highest priority task
- Issues discovered during review - fix immediately, don't wait for next round

### Anti-interruption patterns

The following behaviors are identified as incorrect interruptions and must be avoided:
1. **Stopping to ask for next steps after completing a task** - Wrong. User gave direction, continue to next decision point.
2. **Stopping after review produces improvement items** - Wrong. Immediately executable fixes should be executed right away.
3. **Stopping after governance records are updated** - Wrong. Records are process outputs, not decisions needing confirmation.
4. **Stopping between tightly coupled tasks** - Wrong. Execute through the chain without interruption.

### Continuous execution mode

Once direction is confirmed, execute all dependent tasks continuously until:
- The next node requiring user judgment is reached
- Session context is about to be exhausted
- User actively interrupts

### Real-time closure rule

**Process/experience issues discovered during review or execution are P0 high-value improvements. Fix immediately, don't defer.**

## Session lifecycle

### Session start

1. Read project configuration and Gate status from `examples/current-project-sample.md`
2. Confirm current stage, latest Gate conclusion, number of active risks
3. If there are unclosed items (passed-with-conditions), handle them first

### Session end

After completing main work, output a session status summary and next steps.

## Validation

After workflow-related changes, run:

```bash
python scripts/verify_workflow.py
```

To check the Codex adapter's current load order, run:

```bash
python adapters/codex/launch.py
```

## Replacement boundary

When replacing or removing Codex, follow these boundaries:

### Must preserve (workflow core layer)

- `protocol/` (universal protocols)
- `workflows/software-project-governance/` (manifest, rules, stages, templates, examples, research)
- `scripts/verify_workflow.py` (validation script)

### Can remove (Codex projection layer)

- `.codex-plugin/plugin.json` (Codex plugin definition)
- `skills/software-project-governance/SKILL.md` (this file)
- `adapters/codex/` (Codex adapter directory)

### Replacing with another agent

1. Remove the "can remove" files above
2. Create new projection layer entry per `adapters/<new-agent>/` README
3. Workflow core layer needs no modification
4. Unified fact sources (`examples/` four files) are unaffected
