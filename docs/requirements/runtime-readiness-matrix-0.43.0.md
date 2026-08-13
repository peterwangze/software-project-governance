# Runtime Readiness Matrix 0.43.0

Date: 2026-06-04; updated with 2026-06-11 mainstream agent E2E risk-release evidence
Task: FIX-106
Scope: public cross-harness runtime/readiness facts for the 0.43.0 release line.

This matrix is a public fact artifact for users and reviewers. It connects adapter manifests, real local runtime probes, first-success readiness, blocked/degraded reasons, and the no-overclaim boundary.

No official approval. No marketplace approval. No universal/full runtime support. RISK-036 remains open.

## Summary

| Agent | Public status | Workflow closure | Version command | Evidence and boundary |
| --- | --- | --- | --- | --- |
| claude | PASS | DEGRADED | claude --version | Version probe returned `2.1.161 (Claude Code)` on 2026-06-04. Real agent target-cwd E2E PASS: `agent-runtime-e2e --timeout 90` returned `E2E_PLATFORM=claude; E2E_AGENT=Coordinator; E2E_MODE=always-on x default-confirm`. `full_e2e_verified=true`; workflow closure remains DEGRADED because AskUserQuestion, browser, and MCP are host-dependent. |
| codex | PASS | DEGRADED | codex --version | Version probe returned `codex-cli 0.125.0`; on 2026-06-11 real Codex CLI headless target-cwd E2E PASS: `agent-runtime-e2e --timeout 180` returned `E2E_PLATFORM=codex; E2E_AGENT=Coordinator; E2E_MODE=always-on x default-confirm`. `full_e2e_verified=true`; workflow closure remains DEGRADED because AskUserQuestion, sub-agent, browser, MCP, and broader tool-use closure are host-dependent. |
| gemini | PASS | DEGRADED | gemini --version | Version probe returned `0.46.0`; on 2026-06-11 real Gemini CLI target-cwd E2E PASS after setting `GEMINI_CLI_TRUST_WORKSPACE=true` for the headless run. Output included `E2E_PLATFORM=gemini; E2E_AGENT=Coordinator; E2E_MODE=always-on x default-confirm`. `full_e2e_verified=true`; workflow closure remains DEGRADED because interaction, Agent Team, browser, MCP, and broader tool-use closure are host-dependent. |
| opencode | PASS | DEGRADED | opencode --version | Version probe returned `1.15.5` on 2026-06-04. Real agent target-cwd E2E PASS: `agent-runtime-e2e --timeout 90` returned `E2E_PLATFORM=opencode; E2E_AGENT=Coordinator; E2E_MODE=always-on x default-confirm`. `full_e2e_verified=true`; workflow closure remains DEGRADED because interaction, sub-agent, browser, MCP, and write/tool-use closure are not fully native. |
| chrys | PASS | DEGRADED | chrys is the agent running this verification session | E2E verified 2026-07-01 from live Chrys session reading `.governance/plan-tracker.md`. `full_e2e_verified=true`; workflow closure remains DEGRADED because browser and MCP are host-dependent. Chrys has native ask_user, sub_agent, tool_calling, and git_hooks — the first adapter to reach that native capability profile (dsh matches it in 0.73.0). |
| dsh | PASS | DEGRADED | dsh --version | Version probe returned `0.1.0-rc.6` on 2026-07-08. Real agent target-cwd E2E PASS: the adapter was authored from a live DeepSeek Harness session that loaded skills through the native `skill` tool, spawned three parallel subagents, used ask_user_question/pwsh/fs/web_search, and mount-validated the generated governance preset via `agentPresets.standingKeyFor`. `full_e2e_verified=true`; workflow closure remains DEGRADED because browser automation and MCP are host-dependent. dsh has native ask_user_question, sub_agent, tool_calling, and git_hooks — tied with Chrys for the strongest native capability profile. |
| cursor | RESEARCH_ONLY | NOT_RUNTIME_VERIFIED | manual research | Cursor is a high-adoption AI coding surface, but this repository currently has no Cursor adapter manifest, native-entry projection, or real target-cwd E2E. This row is intentionally NOT_RUNTIME_VERIFIED and must not be read as PASS. |
| copilot | RESEARCH_ONLY | NOT_RUNTIME_VERIFIED | manual research | GitHub Copilot coding agent is a high-adoption target surface, but this repository currently has no Copilot adapter manifest, native-entry projection, or real target-cwd E2E. This row is intentionally NOT_RUNTIME_VERIFIED and must not be read as PASS. |

## Commands

```bash
claude --version
codex --version
gemini --version
opencode --version
python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters --runtime
python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --timeout 90
GEMINI_CLI_TRUST_WORKSPACE=true python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --timeout 180
python skills/software-project-governance/infra/verify_workflow.py check-runtime-readiness-matrix --fail-on-issues
```

## Current Real Runtime Result

`GEMINI_CLI_TRUST_WORKSPACE=true agent-runtime-e2e --timeout 180` completed on 2026-06-11 with `pass=4, blocked=0, fail=0, total=4`.

| Agent | Real runtime result | Blocking or degraded reason |
| --- | --- | --- |
| claude | PASS | None for target-cwd read E2E; closure still host-dependent for AskUserQuestion/browser/MCP. |
| codex | PASS | None for target-cwd read E2E; closure still host-dependent for AskUserQuestion/sub-agent/browser/MCP/tool-use beyond read validation. |
| gemini | PASS | None for target-cwd read E2E when `GEMINI_CLI_TRUST_WORKSPACE=true` is set for headless execution; closure still host-dependent for AskUserQuestion/sub-agent/browser/MCP/tool-use beyond read validation. |
| opencode | PASS | None for target-cwd read E2E; closure still degraded for interaction/sub-agent/browser/MCP/tool-use beyond read validation. |
| chrys | PASS | None for target-cwd read E2E; closure still degraded for browser/MCP. Chrys was the first adapter with native ask_user_question, sub_agent, and tool_calling. |
| dsh | PASS | None for target-cwd read E2E; closure still degraded for browser/MCP. dsh ties Chrys with native ask_user_question, sub_agent, and tool_calling, and adds native preset composition (no runtime-side plugin install needed). |

## Release Boundary

This matrix supports 0.43.0 Cross-Harness E2E Closure by making pass/blocked/degraded status inspectable. It does not close RISK-036 by itself. It does not claim official marketplace approval, universal runtime support, or 1.0.0 production readiness.
