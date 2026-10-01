# 发布检查清单 — 0.42.0

**版本**: 0.42.0
**范围**: AUDIT-106, FIX-100, FIX-101, FIX-102, FIX-103, FIX-104, REL-018

| # | 检查项 | 状态 | 证据 |
|---|--------|------|------|
| 1 | 版本声明同步 | ✅ PASS | `check-version-consistency` |
| 2 | CHANGELOG 0.42.0 条目存在 | ✅ PASS | `project/CHANGELOG.md` |
| 3 | 5-minute success path scope | ✅ PASS | AUDIT-106, FIX-100, FIX-101, FIX-102, FIX-103, FIX-104 |
| 4 | Delivery Trust Snapshot first signal | ✅ PASS | `/governance`, `/governance-status`, `first-run-demo --assert-snapshot` |
| 5 | Existing-project resume path | ✅ PASS | Resume state, carry-over, open risks, hooks, next action |
| 6 | First-run preset guidance | ✅ PASS | lite / standard / strict guidance |
| 7 | Demo fixture and acceptance harness | ✅ PASS | `first-run-demo --assert-snapshot` |
| 8 | README first-success refinement | ✅ PASS | English and Chinese 5-Minute Start |
| 9 | Target fixture/projection version sync | ✅ PASS | target skill and target plan-tracker at 0.42.0 |
| 10 | Hook @version | ✅ PASS | `skills/software-project-governance/infra/hooks/*` |
| 11 | Release gate | ✅ PASS | `check-release --version 0.42.0 --require-changelog --runtime-adapters` |
| 12 | Governance health | ✅ PASS | `check-governance --fail-on-issues` |
| 13 | Whitespace check | ✅ PASS | `git diff --check` |

## 版本声明文件

| 文件 | 期望版本 |
|------|----------|
| `skills/software-project-governance/SKILL.md` | 0.42.0 |
| `skills/software-project-governance/core/manifest.json` | 0.42.0 |
| `.claude-plugin/plugin.json` | 0.42.0 |
| `.claude-plugin/marketplace.json` | 0.42.0 |
| `.codex-plugin/plugin.json` | 0.42.0 |
| `project/e2e-test-project/skills/software-project-governance/SKILL.md` | 0.42.0 |
| `project/e2e-test-project/.governance/plan-tracker.md` | 0.42.0 |
| `skills/software-project-governance/infra/hooks/pre-commit` | @version 0.42.0 |
| `skills/software-project-governance/infra/hooks/commit-msg` | @version 0.42.0 |
| `skills/software-project-governance/infra/hooks/post-commit` | @version 0.42.0 |
| `skills/software-project-governance/infra/hooks/prepare-commit-msg` | @version 0.42.0 |

## 发布判定

0.42.0 release package 可以进入提交前审查：AUDIT-106、FIX-100、FIX-101、FIX-102、FIX-103 与 FIX-104 均已完成并有独立审查或验证证据；release package 完成版本声明、CHANGELOG、release docs、target fixture/projection、hook version 和 release gate 期望同步。

本 release 不提交到任何 marketplace，不声明 official approval、marketplace approval、universal/full runtime support 或 1.0.0 production-ready。RISK-036 仍打开，后续 0.43.0~0.46.0 与外部验证闭环前不得关闭。
