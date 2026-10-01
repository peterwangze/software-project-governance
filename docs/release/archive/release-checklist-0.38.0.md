# 发布检查清单 — 0.38.0

**版本**: 0.38.0
**日期**: 2026-05-28
**范围**: AUDIT-102, FIX-082, FIX-083, FIX-084, FIX-085, FIX-086, FIX-087, REL-013

## 发布门槛

| # | 检查项 | 状态 | 证据 |
|---|---|---|---|
| 1 | 版本声明一致 | ✅ PASS | `check-version-consistency` |
| 2 | CHANGELOG 0.38.0 条目存在 | ✅ PASS | `project/CHANGELOG.md` |
| 3 | Runtime capability contract 闭环 | ✅ PASS | `check-agent-adapters --runtime` |
| 4 | Structured evidence schema 闭环 | ✅ PASS | `check-governance` Check 18b |
| 5 | AI execution packet 闭环 | ✅ PASS | `check-governance` Check 18c |
| 6 | Agent Team degraded mode 闭环 | ✅ PASS | `check-governance` Check 19 |
| 7 | Projection sync guard 闭环 | ✅ PASS | `check-projection-sync` + Check 28b |
| 8 | Hot fact-source consistency guard 闭环 | ✅ PASS | `check-hot-fact-source` + Check 28c |
| 9 | 完整单测 | ✅ PASS | `test_verify_workflow.py` 229/229 |
| 10 | 治理健康 | ✅ PASS | `check-governance --fail-on-issues` |
| 11 | 发布审查 | 待执行 | Release Reviewer |

## 版本声明

| 文件 | 版本 |
|---|---|
| `skills/software-project-governance/SKILL.md` | 0.38.0 |
| `skills/software-project-governance/core/manifest.json` | 0.38.0 |
| `.claude-plugin/plugin.json` | 0.38.0 |
| `.claude-plugin/marketplace.json` | 0.38.0 |
| `.codex-plugin/plugin.json` | 0.38.0 |
| `skills/software-project-governance/infra/hooks/pre-commit` | @version 0.38.0 |
| `skills/software-project-governance/infra/hooks/commit-msg` | @version 0.38.0 |
| `skills/software-project-governance/infra/hooks/post-commit` | @version 0.38.0 |
| `skills/software-project-governance/infra/hooks/prepare-commit-msg` | @version 0.38.0 |

## 结论

0.38.0 可以发布的条件：FIX-082~087 均完成并独立审查通过，RISK-033 关闭，发布门禁与 Release Review 均通过。0.38.0 不声明 1.0.0 production-ready；1.0.0 仍需外部验证通过后再打正式标签。
