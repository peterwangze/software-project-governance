Show the current project governance status.

If `.governance/plan-tracker.md` does not exist, do not fail silently. First tell the user the project has not been initialized yet, and direct them to run `/software-project-governance:governance-init` (or provide project name, goal, project type, current stage, and profile if slash commands are unavailable).

If the file exists, read `.governance/plan-tracker.md` and present a summary including: current stage, Gate status (G1-G11), task completion rate, and active risks. Format as a readable dashboard.
