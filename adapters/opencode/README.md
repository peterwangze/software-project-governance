# opencode Adapter

This directory is the opencode projection for `software-project-governance`.

## Current Status

opencode is runtime-detected and full target-cwd agent runtime E2E verified in
the current local validation host.

The current local validation host has `opencode` on PATH and
`opencode --version` returns `1.15.5`. The reproducible runtime command is:

```bash
python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent opencode --timeout 90
```

That command runs `opencode run` in `project/e2e-test-project`, where opencode
reads `.governance/plan-tracker.md` from the target cwd and returns structured
fields including `E2E_PLATFORM=opencode`, `E2E_AGENT=Coordinator`, and
`E2E_MODE=always-on x default-confirm`.

The earlier DeepSeek invalid model blocker is closed for this host. The adapter
still keeps a provider/model preflight so future regressions such as
`deepseek-v4-pro[1m]`, ANSI escape residue, or unsupported model output are
classified as BLOCKED before any full coverage claim is accepted.

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
python skills/software-project-governance/infra/verify_workflow.py opencode-provider-preflight
python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent opencode --timeout 90
python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters --runtime
```

The 90 second timeout is the current stable window. Shorter runs may time out
after partial tool use, so timeout output should be treated as a runtime window
issue unless the provider/model preflight or logs show an explicit model error.
