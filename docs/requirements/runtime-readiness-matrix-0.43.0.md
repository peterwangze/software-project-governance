# Runtime Readiness Matrix 0.43.0

Date: 2026-06-04
Task: FIX-106
Scope: public cross-harness runtime/readiness facts for the 0.43.0 release line.

This matrix is a public fact artifact for users and reviewers. It connects adapter manifests, real local runtime probes, first-success readiness, blocked/degraded reasons, and the no-overclaim boundary.

No official approval. No marketplace approval. No universal/full runtime support. RISK-036 remains open.

## Summary

| Agent | Public status | Workflow closure | Version command | Evidence and boundary |
| --- | --- | --- | --- | --- |
| claude | PASS | DEGRADED | claude --version | Version probe returned `2.1.161 (Claude Code)` on 2026-06-04. Real agent target-cwd E2E PASS: `agent-runtime-e2e --timeout 90` returned `E2E_PLATFORM=claude; E2E_AGENT=Coordinator; E2E_MODE=always-on x default-confirm`. `full_e2e_verified=true`; workflow closure remains DEGRADED because AskUserQuestion, browser, and MCP are host-dependent. |
| codex | BLOCKED | DEGRADED | codex --version | Version probe returned `codex-cli 0.125.0` on 2026-06-04. Codex CLI headless target-cwd E2E timed out in the real `codex exec` runtime. Current Codex App dogfood proves host-mode workflow use, not Codex CLI full runtime closure. |
| gemini | BLOCKED | DEGRADED | gemini --version | Version probe returned `0.35.3` on 2026-06-04. Gemini auth missing or not configured; real target-cwd E2E exited with auth/401 before model execution. Remediation remains GEMINI_API_KEY / GOOGLE_API_KEY / Vertex / GCA / settings auth. |
| opencode | PASS | DEGRADED | opencode --version | Version probe returned `1.15.5` on 2026-06-04. Real agent target-cwd E2E PASS: `agent-runtime-e2e --timeout 90` returned `E2E_PLATFORM=opencode; E2E_AGENT=Coordinator; E2E_MODE=always-on x default-confirm`. `full_e2e_verified=true`; workflow closure remains DEGRADED because interaction, sub-agent, browser, MCP, and write/tool-use closure are not fully native. |
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
python skills/software-project-governance/infra/verify_workflow.py check-runtime-readiness-matrix --fail-on-issues
```

## Current Real Runtime Result

`agent-runtime-e2e --timeout 90` completed with `pass=2, blocked=2, fail=0, total=4`.

| Agent | Real runtime result | Blocking or degraded reason |
| --- | --- | --- |
| claude | PASS | None for target-cwd read E2E; closure still host-dependent for AskUserQuestion/browser/MCP. |
| codex | BLOCKED | Codex CLI target-cwd command timed out. Log included a PowerShell shell snapshot warning in Codex CLI 0.125.0. |
| gemini | BLOCKED | Auth missing/401 before model execution. |
| opencode | PASS | None for target-cwd read E2E; closure still degraded for interaction/sub-agent/browser/MCP/tool-use beyond read validation. |

## Release Boundary

This matrix supports 0.43.0 Cross-Harness E2E Closure by making pass/blocked/degraded status inspectable. It does not close RISK-036 by itself. It does not claim official marketplace approval, universal runtime support, or 1.0.0 production readiness.
