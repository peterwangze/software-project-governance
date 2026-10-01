# 发布检查清单 — 0.40.0

**版本**: 0.40.0
**范围**: AUDIT-104, FIX-094, REL-015

| # | 检查项 | 状态 | 证据 |
|---|--------|------|------|
| 1 | 版本声明同步 | ✅ PASS | `check-version-consistency` / `verify` |
| 2 | CHANGELOG 0.40.0 条目存在 | ✅ PASS | `project/CHANGELOG.md` |
| 3 | Source workflow SKILL | ✅ PASS | `skills/software-project-governance/SKILL.md` |
| 4 | Target fixture workflow SKILL | ✅ PASS | `project/e2e-test-project/skills/software-project-governance/SKILL.md` |
| 5 | Target fixture plan-tracker | ✅ PASS | `project/e2e-test-project/.governance/plan-tracker.md` |
| 6 | Hook @version | ✅ PASS | `skills/software-project-governance/infra/hooks/*` |
| 7 | AI-facing text convergence | ✅ PASS | FIX-094 + REVIEW-FIX-094 |
| 8 | Projection sync | ✅ PASS | `check-projection-sync --fail-on-issues` |
| 9 | Governance health | ✅ PASS | `check-governance --fail-on-issues` |
| 10 | 发布门禁 | ✅ PASS | `check-release --version 0.40.0 --require-changelog --runtime-adapters` |

## 版本声明文件

| 文件 | 期望版本 |
|------|----------|
| `skills/software-project-governance/SKILL.md` | 0.40.0 |
| `skills/software-project-governance/core/manifest.json` | 0.40.0 |
| `.claude-plugin/plugin.json` | 0.40.0 |
| `.claude-plugin/marketplace.json` | 0.40.0 |
| `.codex-plugin/plugin.json` | 0.40.0 |
| `project/e2e-test-project/skills/software-project-governance/SKILL.md` | 0.40.0 |
| `project/e2e-test-project/.governance/plan-tracker.md` | 0.40.0 |
| `skills/software-project-governance/infra/hooks/pre-commit` | @version 0.40.0 |
| `skills/software-project-governance/infra/hooks/commit-msg` | @version 0.40.0 |
| `skills/software-project-governance/infra/hooks/post-commit` | @version 0.40.0 |
| `skills/software-project-governance/infra/hooks/prepare-commit-msg` | @version 0.40.0 |

## 发布判定

0.40.0 可以发布的条件：AUDIT-104 与 FIX-094 均完成并独立审查通过，发布门禁与 Release Review 均通过。0.40.0 不声明 1.0.0 production-ready；1.0.0 仍需外部验证通过后再打正式标签。
