# 发布检查清单 — 0.40.1

**版本**: 0.40.1
**范围**: FIX-095, REL-016

| # | 检查项 | 状态 | 证据 |
|---|--------|------|------|
| 1 | 版本声明同步 | ✅ PASS | `check-version-consistency` / `verify` |
| 2 | CHANGELOG 0.40.1 条目存在 | ✅ PASS | `project/CHANGELOG.md` |
| 3 | Source workflow SKILL | ✅ PASS | `skills/software-project-governance/SKILL.md` |
| 4 | Target fixture workflow SKILL | ✅ PASS | `project/e2e-test-project/skills/software-project-governance/SKILL.md` |
| 5 | Target fixture plan-tracker | ✅ PASS | `project/e2e-test-project/.governance/plan-tracker.md` |
| 6 | Hook @version | ✅ PASS | `skills/software-project-governance/infra/hooks/*` |
| 7 | Clean checkout CI boundary | ✅ PASS | FIX-095 + GitHub run `26754020310` |
| 8 | Python 3.11 compatibility | ✅ PASS | FIX-095 py_compile / CI success |
| 9 | Governance health | ✅ PASS | `check-governance --fail-on-issues` |
| 10 | 发布门禁 | ✅ PASS | `check-release --version 0.40.1 --require-changelog --runtime-adapters` |

## 版本声明文件

| 文件 | 期望版本 |
|------|----------|
| `skills/software-project-governance/SKILL.md` | 0.40.1 |
| `skills/software-project-governance/core/manifest.json` | 0.40.1 |
| `.claude-plugin/plugin.json` | 0.40.1 |
| `.claude-plugin/marketplace.json` | 0.40.1 |
| `.codex-plugin/plugin.json` | 0.40.1 |
| `project/e2e-test-project/skills/software-project-governance/SKILL.md` | 0.40.1 |
| `project/e2e-test-project/.governance/plan-tracker.md` | 0.40.1 |
| `skills/software-project-governance/infra/hooks/pre-commit` | @version 0.40.1 |
| `skills/software-project-governance/infra/hooks/commit-msg` | @version 0.40.1 |
| `skills/software-project-governance/infra/hooks/post-commit` | @version 0.40.1 |
| `skills/software-project-governance/infra/hooks/prepare-commit-msg` | @version 0.40.1 |

## 发布判定

0.40.1 可以发布的条件：FIX-095 已在本地、clean worktree 和 GitHub Actions 上闭环，RISK-035 已关闭，且本 release 只包含版本声明、CHANGELOG、release docs、tag/push，不混入 0.41.0 official marketplace readiness 新功能。
