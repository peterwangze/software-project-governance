# opencode Adapter

This directory is the opencode projection for `software-project-governance`.

opencode is a Tier 1 loading guide target in 0.47.0. The current loading model is a thin project instruction pointer, usually `AGENTS.md` or an opencode-configured instruction file, to the shared workflow entry:

```text
skills/software-project-governance/SKILL.md
```

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

## Load

opencode-compatible projects should use a thin project instruction entry such
as `AGENTS.md` or the platform's configured instruction file to point at:

```text
skills/software-project-governance/SKILL.md
```

The native entry must remain a pointer. It must not duplicate the workflow
rules, gate logic, evidence schema, or release policy.

If a project uses a custom opencode config directory or agent definitions, keep those files as host-native routing/configuration only. The governance workflow still lives in `skills/software-project-governance/SKILL.md`, and active records still live in the target project's `.governance/` directory.

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

## Boundary

opencode target-cwd runtime E2E is PASS/DEGRADED in the current local validation host. PASS means the local harness proved opencode could read target-cwd governance facts and return structured E2E fields. DEGRADED means the workflow still does not claim official approval, marketplace approval, universal/full runtime support, automatic best-tool selection, or 1.0.0 production-ready status.

Keep the provider/model preflight in front of any runtime claim. A provider configuration problem is BLOCKED evidence, not a reason to claim the workflow failed or that all opencode hosts are supported.
