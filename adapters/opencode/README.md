# opencode Adapter

This directory is the opencode projection for `software-project-governance`.

## Current Status

opencode is **not supported in this release**. The adapter is intentionally
present as an explicit unsupported projection so the project does not claim
mainstream agent coverage that has not been verified in a real runtime.

The current local validation host does not have an `opencode` command on PATH.
`check-agent-adapters --runtime` must therefore report opencode as
`UNSUPPORTED`, not `PASS`.

## Native Entry

opencode-compatible projects should use a thin project instruction entry such
as `AGENTS.md` or the platform's configured instruction file to point at:

```text
skills/software-project-governance/SKILL.md
```

The native entry must remain a pointer. It must not duplicate the workflow
rules, gate logic, evidence schema, or release policy.

## Verification

Static contract:

```bash
python adapters/opencode/launch.py
python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters
```

Runtime contract:

```bash
python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters --runtime
```

Until opencode is installed and an end-to-end workflow use case passes in that
runtime, this adapter remains explicitly unsupported.
