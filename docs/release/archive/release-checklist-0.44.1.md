# 发布检查清单 — 0.44.1

**版本**: 0.44.1
**类型**: Patch release
**范围**: FIX-113, FIX-114, REL-021

| # | 检查项 | 状态 | 证据 |
|---|--------|------|------|
| 1 | 版本声明同步到 0.44.1 | ✅ PASS | `skills/software-project-governance/SKILL.md`, `core/manifest.json`, Claude/Codex plugin manifests, marketplace metadata, target fixture, hook @version |
| 2 | CHANGELOG 0.44.1 条目存在 | ✅ PASS | `project/CHANGELOG.md` |
| 3 | FIX-113 included | ✅ PASS | Commit `777bd66758cb6515c488c2eac25dde5f7a7ddd1b`; GitHub Governance CI success |
| 4 | FIX-114 included | ✅ PASS | Commit `fa4f2d115a762afe8c92f7debea0cfa8f89beed9`; GitHub Governance CI success |
| 5 | No-overclaim false-pass guard preserved | ✅ PASS | Claim-scoped negation prevents unrelated `no`/`not` wording from masking official approval, marketplace approval, runtime, external pilot, or 1.0.0 claims |
| 6 | Governance context fact coverage preserved | ✅ PASS | Context discovery covers plan/session/risk plus evidence-log and root-scoped git facts without inventing active work from historical evidence or parent repos |
| 7 | Pack semantics unchanged | ✅ PASS | `governance-packs.json` version/release command synchronized only; no pack capability, profile, or file-boundary semantic change |
| 8 | Runtime/readiness facts remain unchanged unless separately evidenced | ✅ PASS | 0.44.1 does not claim universal/full runtime support |
| 9 | First-session measurement boundary preserved | ✅ PASS | 0.44.1 does not claim external first-session pilot success |
| 10 | Codex Desktop marketplace-management boundary preserved | ✅ PASS | 0.44.1 does not claim Desktop marketplace add/install/enable/upgrade/uninstall E2E PASS |
| 11 | RISK-036 remains open | ✅ PASS | 0.45.0/0.46.0 continue official-readiness preparation |
| 12 | Version consistency gate | ✅ PASS | `check-version-consistency` |
| 13 | Release gate | ✅ PASS | `check-release --version 0.44.1 --require-changelog --runtime-adapters --skip-execution-gates` |
| 14 | Projection sync regression | ✅ PASS | `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -k ProjectionSync -v` |
| 15 | Whitespace check | ✅ PASS | `git diff --check` |

## 版本声明文件

| 文件 | 期望版本 |
|------|----------|
| `skills/software-project-governance/SKILL.md` | 0.44.1 |
| `skills/software-project-governance/core/manifest.json` | 0.44.1 |
| `skills/software-project-governance/core/governance-packs.json` | 0.44.1 |
| `.claude-plugin/plugin.json` | 0.44.1 |
| `.claude-plugin/marketplace.json` | 0.44.1 |
| `.codex-plugin/plugin.json` | 0.44.1 |
| `project/e2e-test-project/skills/software-project-governance/SKILL.md` | 0.44.1 |
| `project/e2e-test-project/.governance/plan-tracker.md` | 0.44.1 |
| `skills/software-project-governance/infra/hooks/pre-commit` | @version 0.44.1 |
| `skills/software-project-governance/infra/hooks/commit-msg` | @version 0.44.1 |
| `skills/software-project-governance/infra/hooks/post-commit` | @version 0.44.1 |
| `skills/software-project-governance/infra/hooks/prepare-commit-msg` | @version 0.44.1 |

## 发布判定

0.44.1 release package 可以进入 Release Reviewer 审查：FIX-113 和 FIX-114 已按一事项一 commit 进入 master 并通过远端 CI；本次 release package 只同步 patch 版本声明、CHANGELOG、release checklist、feature flag 状态、rollback plan、target fixture/projection、hook @version 和 release gate 期望。

本 release 不提交到任何 marketplace，不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success、Codex Desktop marketplace-management E2E PASS 或 1.0.0 production-ready。RISK-036 仍打开，后续 0.45.0~0.46.0 与外部验证闭环前不得关闭。
