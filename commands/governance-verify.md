Run a governance health check on the current project.

If `.governance/` does not exist, do not treat that as a generic verification failure. First tell the user the project has not been initialized yet, and direct them to run `/software-project-governance:governance-init`.

If `.governance/` exists, verify that it has all 4 required files (plan-tracker.md, evidence-log.md, decision-log.md, risk-log.md). Check that each completed task in the plan tracker has a corresponding evidence entry. Report any gaps or issues found. If the project is the workflow repo itself (has `scripts/verify_workflow.py`), also run that script for a full check.
