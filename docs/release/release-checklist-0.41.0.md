# 发布检查清单 — 0.41.0

**版本**: 0.41.0
**范围**: AUDIT-105, FIX-096, FIX-097, FIX-098, FIX-099, REL-017

| # | 检查项 | 状态 | 证据 |
|---|--------|------|------|
| 1 | 版本声明同步 | ✅ PASS | `check-version-consistency` / `verify` |
| 2 | CHANGELOG 0.41.0 条目存在 | ✅ PASS | `project/CHANGELOG.md` |
| 3 | Official readiness gap analysis | ✅ PASS | `docs/marketplace/official-readiness-gap-analysis-0.41.0.md` |
| 4 | Codex/Claude plugin metadata | ✅ PASS | `.codex-plugin/plugin.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` |
| 5 | README English first screen | ✅ PASS | `README.md` |
| 6 | Privacy/security and submission docs | ✅ PASS | `docs/marketplace/privacy-security.md`, `docs/marketplace/submission-checklist-0.41.0.md` |
| 7 | Marketplace assets tracked and referenced | ✅ PASS | `.codex-plugin/assets/*.svg`, `.claude-plugin/assets/*.svg` |
| 8 | Target fixture/projection version sync | ✅ PASS | `project/e2e-test-project/skills/software-project-governance/SKILL.md`, target fixture plan-tracker |
| 9 | Hook @version | ✅ PASS | `skills/software-project-governance/infra/hooks/*` |
| 10 | Release gate | ✅ PASS | `check-release --version 0.41.0 --require-changelog --runtime-adapters` |
| 11 | Governance health | ✅ PASS | `check-governance --fail-on-issues` |
| 12 | Whitespace check | ✅ PASS | `git diff --check` |

## 版本声明文件

| 文件 | 期望版本 |
|------|----------|
| `skills/software-project-governance/SKILL.md` | 0.41.0 |
| `skills/software-project-governance/core/manifest.json` | 0.41.0 |
| `.claude-plugin/plugin.json` | 0.41.0 |
| `.claude-plugin/marketplace.json` | 0.41.0 |
| `.codex-plugin/plugin.json` | 0.41.0 |
| `project/e2e-test-project/skills/software-project-governance/SKILL.md` | 0.41.0 |
| `project/e2e-test-project/.governance/plan-tracker.md` | 0.41.0 |
| `skills/software-project-governance/infra/hooks/pre-commit` | @version 0.41.0 |
| `skills/software-project-governance/infra/hooks/commit-msg` | @version 0.41.0 |
| `skills/software-project-governance/infra/hooks/post-commit` | @version 0.41.0 |
| `skills/software-project-governance/infra/hooks/prepare-commit-msg` | @version 0.41.0 |

## 发布判定

0.41.0 release package 可以进入提交前审查：AUDIT-105、FIX-096、FIX-097、FIX-098 与 FIX-099 均已完成并有独立审查证据；release package 完成版本声明、CHANGELOG、release docs、target fixture/projection、hook version 和 release gate 期望同步。

本 release 不提交到任何 marketplace，不声明 official acceptance、marketplace approval、1.0.0 production-ready 或 universal/full runtime support。RISK-036 仍打开，后续 0.42.0~0.46.0 与外部验证闭环前不得关闭。
