# opencode Adapter

This directory is the opencode projection for `software-project-governance`.

## Current Status

opencode is **runtime-detected but not full-E2E verified in this release**.
The adapter is intentionally explicit about this split so the project does not
claim mainstream agent coverage beyond the evidence that actually passed.

The current local validation host has `opencode` on PATH and
`opencode --version` returns `1.15.5`. A real `opencode run` target-cwd use case
was attempted, but the configured provider returned HTTP 400 for an invalid
DeepSeek model name before task execution. `check-agent-adapters --runtime`
must therefore report the runtime version probe as PASS while the manifest keeps
`runtime_e2e.agent_runtime_e2e.status=blocked` and `no_full_coverage_claim=true`.

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

Until an `opencode run` workflow use case passes in the real runtime, this
adapter must not be described as full-coverage verified.
