# Weak-LLM Deterministic Scaffolds

These scaffolds are paved paths for AI-assisted delivery when the model may be weak at product judgment. Each scaffold encodes a small product plan, executable acceptance, six-dimension quality budget, smallest vertical slice, demo checklist, and tool commands before implementation begins.

## Available Scaffolds

| Type | Template | Best fit |
| --- | --- | --- |
| web-app | `web-app.md` | Browser based tools, dashboards, CRUD flows, internal workflow apps |
| cli-tool | `cli-tool.md` | Command line utilities, local automation, validation runners |
| workflow-plugin | `workflow-plugin.md` | Governance plugins, agent skills, adapter workflows, release checks |

## Generator

Render a scaffold to stdout:

```bash
python skills/software-project-governance/infra/verify_workflow.py generate-deterministic-scaffold --type web-app
```

Write a scaffold to a project file:

```bash
python skills/software-project-governance/infra/verify_workflow.py generate-deterministic-scaffold --type cli-tool --output project-scaffold.md
```

## Validation

```bash
python skills/software-project-governance/infra/verify_workflow.py check-deterministic-scaffolds --fail-on-issues
```

`check-governance` runs the same guard as Check 18h. A scaffold is valid only when it includes PRD-lite, Product Success Contract, Executable Acceptance, Quality Budget, Vertical Slice, Demo Checklist, and Tooling sections with runnable command bullets.
