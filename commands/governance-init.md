Initialize governance files for the current project. This is the first command to run after installing the plugin.

Steps:
1. Ask the user: "What is your project name and goal?"
2. Ask the user: "Is this a new project or an existing project?" If existing, ask "What stage is it currently in?"
3. Ask the user: "What profile do you want? lightweight (personal/MVP), standard (team project), or strict (compliance/large)?"
4. Create a `.governance/` directory in the project root if it doesn't exist.
5. Create the 4 governance files in `.governance/` using the template field definitions from the SKILL.md M3 section:
   - `plan-tracker.md` — fill in: project name, profile, trigger mode (default: always-on), current stage, Gate status tracking table (G1-G11 with appropriate statuses), project overview table, empty sample tracking table
   - `evidence-log.md` — create with evidence log field headers
   - `decision-log.md` — create with decision log field headers
   - `risk-log.md` — create with risk log field headers
6. If existing project (mid-stage onboarding): mark previous gates as `passed-on-entry` in the Gate Status Tracking table. Add at least one decision record for why the project is at its current stage.
7. Confirm to the user: "Governance files created at `.governance/`. Your agent will now automatically track project governance."
