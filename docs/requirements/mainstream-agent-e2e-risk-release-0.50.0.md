# Mainstream Agent E2E Risk Release - 0.50.0

Date: 2026-06-11
Task: FIX-129
Scope: release the mainstream-agent target-cwd runtime E2E sub-risk after the user configured Codex, Claude Code, Gemini CLI, and opencode.

No official approval. No marketplace approval. No universal/full runtime support. No external validation PASS. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No 1.0.0 production-ready status.

## Validation Result

Command:

```bash
GEMINI_CLI_TRUST_WORKSPACE=true python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --timeout 180
```

Result:

```text
pass=4, blocked=0, fail=0, total=4
```

| Agent | Result | Evidence |
| --- | --- | --- |
| Claude Code | PASS / DEGRADED | Real `claude -p` target-cwd run returned `E2E_PLATFORM=claude`, `E2E_AGENT=Coordinator`, and `E2E_MODE=always-on x default-confirm`. |
| Codex CLI | PASS / DEGRADED | Real `codex exec -C . -s read-only --ephemeral` target-cwd run returned `E2E_PLATFORM=codex`, `E2E_AGENT=Coordinator`, and `E2E_MODE=always-on x default-confirm`. |
| Gemini CLI | PASS / DEGRADED | Real `gemini --prompt ... --approval-mode plan --output-format text` target-cwd run returned `E2E_PLATFORM=gemini`, `E2E_AGENT=Coordinator`, and `E2E_MODE=always-on x default-confirm` after setting `GEMINI_CLI_TRUST_WORKSPACE=true` for headless workspace trust. |
| opencode | PASS / DEGRADED | Real `opencode run --dir . --format json` target-cwd run returned `E2E_PLATFORM=opencode`, `E2E_AGENT=Coordinator`, and `E2E_MODE=always-on x default-confirm`. |

## Risk Disposition

The mainstream agent target-cwd read E2E sub-risk is released for the four Tier 1 agents: Codex, Claude Code, Gemini CLI, and opencode.

RISK-036 remains open because this evidence does not satisfy the remaining 1.0.0 closure criteria:

- at least two external project validations with full PASS;
- official submission result or approval evidence;
- Codex Desktop marketplace-management lifecycle PASS or conservative blocked carry-forward;
- final release review for the 1.0.0 tag boundary.

## Follow-Up Boundary

`check-host-capability-context` continues to keep restricted-environment benchmark scenarios for unavailable Codex CLI and Gemini auth paths. Those scenarios are simulated diagnostic fixtures and no longer require the current live Codex/Gemini runtime matrix to stay blocked.
