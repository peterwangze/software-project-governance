Check a specific governance gate.

If `.governance/plan-tracker.md` does not exist, first tell the user the project has not been initialized yet, and direct them to run `/software-project-governance:governance-init` before doing Gate checks.

If the file exists, read `references/stage-gates.md` (from the skill directory) for the detailed check items. The user may provide a gate ID like "G1" or "G6". Then read `.governance/plan-tracker.md` for the current gate status and supporting evidence. If no gate ID provided, show summary of all gates. Present the check items and whether each passes, highlighting any blocked or pending gates.
