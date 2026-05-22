# 发布检查清单 — 0.37.0

**版本**: 0.37.0
**日期**: 2026-05-22
**范围**: FIX-080, FIX-081, REL-012

## 发布门槛

| # | 检查项 | 状态 | 证据 |
|---|---|---|---|
| 1 | 版本声明一致 | ✅ PASS | `check-version-consistency` |
| 2 | CHANGELOG 0.37.0 条目存在 | ✅ PASS | `project/CHANGELOG.md` |
| 3 | 事实依据看护闭环 | ✅ PASS | FactGrounding tests 7/7 + Check 18 |
| 4 | `CLAUDE.md` 合法升级例外闭环 | ✅ PASS | PreCommitClaudeBootstrapUpgradeHookTests 5/5 |
| 5 | 完整单测 | ✅ PASS | `test_verify_workflow.py` 195/195 |
| 6 | 治理健康 | ✅ PASS | `check-governance --fail-on-issues` |
| 7 | 发布审查 | 待执行 | Release Reviewer |

## 版本声明

| 文件 | 版本 |
|---|---|
| `skills/software-project-governance/SKILL.md` | 0.37.0 |
| `skills/software-project-governance/core/manifest.json` | 0.37.0 |
| `.claude-plugin/plugin.json` | 0.37.0 |
| `.claude-plugin/marketplace.json` | 0.37.0 |
| `.codex-plugin/plugin.json` | 0.37.0 |
| `skills/software-project-governance/infra/hooks/pre-commit` | @version 0.37.0 |
| `skills/software-project-governance/infra/hooks/commit-msg` | @version 0.37.0 |
| `skills/software-project-governance/infra/hooks/post-commit` | @version 0.37.0 |
| `skills/software-project-governance/infra/hooks/prepare-commit-msg` | @version 0.37.0 |

## 结论

0.37.0 可以发布的条件：FIX-080/FIX-081 均完成并独立审查通过，RISK-032 关闭，发布门禁与 Release Review 均通过。
