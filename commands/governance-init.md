Initialize governance files for the current project. This is the first command to run after installing the plugin.

Steps:
1. Ask the user: "What is your project name and goal?"
2. Ask the user: "Is this a new project or an existing project?" If existing, ask "What stage is it currently in?"
3. Ask the user: "What profile do you want? lightweight (personal/MVP), standard (team project), or strict (compliance/large)?"
4. Create a `.governance/` directory in the project root if it doesn't exist.
5. Copy templates into `.governance/`:
   - Copy `workflows/software-project-governance/templates/plan-tracker.md` to `.governance/plan-tracker.md` and fill in the project name, profile, trigger mode, and current stage.
   - Copy `workflows/software-project-governance/templates/evidence-log.md` to `.governance/evidence-log.md`.
   - Copy `workflows/software-project-governance/templates/decision-log.md` to `.governance/decision-log.md`.
   - Copy `workflows/software-project-governance/templates/risk-log.md` to `.governance/risk-log.md`.
6. If existing project (mid-stage onboarding): mark previous gates as `passed-on-entry` in the Gate Status Tracking table. Add at least one decision record for why the project is at its current stage.
7. Confirm to the user: "Governance files created at `.governance/`. Your agent will now automatically track project governance."
