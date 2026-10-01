# 发布检查清单 — 0.39.0

**版本**: 0.39.0
**日期**: 2026-05-30
**范围**: AUDIT-103, FIX-088, FIX-089, FIX-090, FIX-091, FIX-092, FIX-093, REL-014

## 发布门槛

| # | 检查项 | 状态 | 证据 |
|---|---|---|---|
| 1 | 版本声明一致 | ✅ PASS | `check-version-consistency` |
| 2 | CHANGELOG 0.39.0 条目存在 | ✅ PASS | `project/CHANGELOG.md` |
| 3 | Product Success Contract 闭环 | ✅ PASS | `check-governance` Check 18d |
| 4 | Executable Acceptance Contract 闭环 | ✅ PASS | `check-governance` Check 18e |
| 5 | Quality Budget Gate 闭环 | ✅ PASS | `check-governance` Check 18f |
| 6 | Vertical Slice Delivery Packets 闭环 | ✅ PASS | `check-governance` Check 18g |
| 7 | Weak-LLM Deterministic Scaffolds 闭环 | ✅ PASS | `check-governance` Check 18h |
| 8 | User Interruption Policy v2 闭环 | ✅ PASS | `check-governance` Check 18i |
| 9 | 完整单测 | ✅ PASS | `test_verify_workflow.py` 285/285 |
| 10 | 发布门禁 | ✅ PASS | `check-release --version 0.39.0 --require-changelog --runtime-adapters` |
| 11 | 发布审查 | ✅ PASS | Release Reviewer APPROVED |

## 版本声明

| 文件 | 版本 |
|---|---|
| `skills/software-project-governance/SKILL.md` | 0.39.0 |
| `skills/software-project-governance/core/manifest.json` | 0.39.0 |
| `.claude-plugin/plugin.json` | 0.39.0 |
| `.claude-plugin/marketplace.json` | 0.39.0 |
| `.codex-plugin/plugin.json` | 0.39.0 |
| `project/e2e-test-project/skills/software-project-governance/SKILL.md` | 0.39.0 |
| `project/e2e-test-project/.governance/plan-tracker.md` | 0.39.0 |
| `skills/software-project-governance/infra/hooks/pre-commit` | @version 0.39.0 |
| `skills/software-project-governance/infra/hooks/commit-msg` | @version 0.39.0 |
| `skills/software-project-governance/infra/hooks/post-commit` | @version 0.39.0 |
| `skills/software-project-governance/infra/hooks/prepare-commit-msg` | @version 0.39.0 |

## 结论

0.39.0 可以发布的条件：FIX-088~093 均完成并独立审查通过，RISK-034 关闭，发布门禁与 Release Review 均通过。0.39.0 不声明 1.0.0 production-ready；1.0.0 仍需外部验证通过后再打正式标签。
