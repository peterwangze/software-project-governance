# User Interruption Policy v2 Template

Use this template inside an execution packet when a task needs explicit user-interruption boundaries.

```yaml
interruption_policy:
  mode: "critical-only: default execute routine reversible work and record assumptions when needed"
  critical_triggers:
    - "Ask the user when product intent is unclear."
    - "Ask the user when acceptance standard or done criteria are unclear."
    - "Ask the user before irreversible, release, risk acceptance, external dependency, or mode change decisions."
  auto_execute:
    - "Run routine execution, local validation, focused code edits, and governance record updates when scope is known and reversible."
    - "Commit and push normal single-task changes when validation, evidence, and review gates are satisfied."
  assumption_record:
    assumption: "Default choice used for a reversible non-critical ambiguity."
    basis: "Fact source or repository pattern supporting the default."
    reversibility: "Why the choice can be changed without product damage."
    validation: "Command or demo that will verify the assumption."
    rollback: "How to revert if the assumption is wrong."
  interruption_budget: "At most one user interruption per work unit unless a new critical trigger appears."
```

## Classification Examples

- product intent unclear -> `ask_user`
- acceptance standard unclear -> `ask_user`
- irreversible destructive action -> `ask_user`
- release go/no-go -> `ask_user`
- new external dependency -> `ask_user`
- routine scoped edit -> `auto_execute`
- local validation command -> `auto_execute`
- governance record update -> `auto_execute`
- normal single-task commit and push -> `auto_execute`
- reversible naming or file-placement ambiguity -> `record_assumption`

## Validation

Run:

```bash
python skills/software-project-governance/infra/verify_workflow.py check-interruption-policy --fail-on-issues
```

The checker validates this template, the canonical interaction-boundary document, deterministic classification examples, and active execution packet `interruption_policy` fields.
