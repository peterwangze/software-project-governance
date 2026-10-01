# 发布检查清单 — 0.43.0

**版本**: 0.43.0
**范围**: AUDIT-107, FIX-105, FIX-106, FIX-107, REL-019

| # | 检查项 | 状态 | 证据 |
|---|--------|------|------|
| 1 | 版本声明同步 | ✅ PASS | `check-version-consistency` |
| 2 | CHANGELOG 0.43.0 条目存在 | ✅ PASS | `project/CHANGELOG.md` |
| 3 | Snapshot freshness and 1.0 blocker guard | ✅ PASS | FIX-105, `check-hot-fact-source`, Check 28c |
| 4 | Public runtime/readiness matrix | ✅ PASS | `docs/requirements/runtime-readiness-matrix-0.43.0.md`, `check-runtime-readiness-matrix` |
| 5 | Real runtime matrix status is conservative | ✅ PASS | Claude/opencode PASS; Codex/Gemini BLOCKED; Cursor/Copilot RESEARCH_ONLY |
| 6 | First-session measurement evidence | ✅ PASS | `docs/requirements/first-session-measurement-0.43.0.md`, `check-first-session-measurement` |
| 7 | Local demo remains local/demo-only | ✅ PASS | `first-run-demo --assert-snapshot`; local_demo=PASS, external_pilot=NOT_MEASURED |
| 8 | README public pointers | ✅ PASS | Runtime readiness matrix link and first-session measured-state link |
| 9 | Target fixture/projection version sync | ✅ PASS | target skill and target plan-tracker at 0.43.0 |
| 10 | Hook @version | ✅ PASS | `skills/software-project-governance/infra/hooks/*` |
| 11 | Release gate | ✅ PASS | `check-release --version 0.43.0 --require-changelog --runtime-adapters` |
| 12 | Governance health | ✅ PASS | `check-governance --fail-on-issues` |
| 13 | Whitespace check | ✅ PASS | `git diff --check` |

## 版本声明文件

| 文件 | 期望版本 |
|------|----------|
| `skills/software-project-governance/SKILL.md` | 0.43.0 |
| `skills/software-project-governance/core/manifest.json` | 0.43.0 |
| `.claude-plugin/plugin.json` | 0.43.0 |
| `.claude-plugin/marketplace.json` | 0.43.0 |
| `.codex-plugin/plugin.json` | 0.43.0 |
| `project/e2e-test-project/skills/software-project-governance/SKILL.md` | 0.43.0 |
| `project/e2e-test-project/.governance/plan-tracker.md` | 0.43.0 |
| `skills/software-project-governance/infra/hooks/pre-commit` | @version 0.43.0 |
| `skills/software-project-governance/infra/hooks/commit-msg` | @version 0.43.0 |
| `skills/software-project-governance/infra/hooks/post-commit` | @version 0.43.0 |
| `skills/software-project-governance/infra/hooks/prepare-commit-msg` | @version 0.43.0 |

## 发布判定

0.43.0 release package 可以进入提交前审查：FIX-105、FIX-106 与 FIX-107 均已完成并有独立审查或验证证据；release package 完成版本声明、CHANGELOG、release docs、target fixture/projection、hook version、runtime readiness matrix、first-session measured state 和 release gate 期望同步。

本 release 不提交到任何 marketplace，不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success 或 1.0.0 production-ready。RISK-036 仍打开，后续 0.44.0~0.46.0 与外部验证闭环前不得关闭。
