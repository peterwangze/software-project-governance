# 发布检查清单 — 0.44.0

**版本**: 0.44.0
**范围**: AUDIT-108, AUDIT-109, FIX-108, FIX-112, FIX-109, FIX-110, FIX-111, REL-020

| # | 检查项 | 状态 | 证据 |
|---|--------|------|------|
| 1 | 版本声明同步到 0.44.0 | ✅ PASS | `skills/software-project-governance/SKILL.md`, `core/manifest.json`, Claude/Codex plugin manifests, target fixture, hook @version |
| 2 | CHANGELOG 0.44.0 条目存在 | ✅ PASS | `project/CHANGELOG.md` |
| 3 | Pack registry and validator | ✅ PASS | FIX-108, `governance-packs.json`, `check-governance-packs`, Check 28f |
| 4 | Context-aware governance resume | ✅ PASS | FIX-112, `governance-context`, Check 28g, target fixture command contracts |
| 5 | README pack guidance | ✅ PASS | FIX-109, `check-readme-pack-guidance`, Check 28h |
| 6 | Manifest and cleanup integration | ✅ PASS | FIX-110, `canonical_product_artifacts.governance-pack-registry`, cleanup scope fail-closed, TOOL-029 |
| 7 | Pack-aware status/release boundary | ✅ PASS | FIX-111, `check-governance-pack-status`, Check 28i |
| 8 | Pack boundary is conservative | ✅ PASS | Pack enabled/membership is not task evidence, independent review, quality gate, release gate, official approval, marketplace approval, universal/full runtime support, or 1.0.0 production-ready |
| 9 | Runtime/readiness facts remain unchanged unless separately evidenced | ✅ PASS | 0.43.0 public matrix remains the runtime fact source; 0.44.0 does not claim universal/full runtime support |
| 10 | First-session measurement boundary preserved | ✅ PASS | 0.44.0 does not claim external first-session pilot success |
| 11 | RISK-036 remains open | ✅ PASS | `risk-log.md`; 0.45.0/0.46.0 continue official-readiness preparation |
| 12 | Version consistency gate | ✅ PASS | `check-version-consistency` PASS; `verify_workflow.py` REQUIRED_SNIPPETS version literals updated to 0.44.0 while historical 0.43.0 artifacts remain intact |
| 13 | Release gate | ✅ PASS | `check-release --version 0.44.0 --require-changelog --runtime-adapters` |
| 14 | Governance health | ✅ PASS | `check-governance --fail-on-issues` |
| 15 | Whitespace check | ✅ PASS | `git diff --check` |

## 版本声明文件

| 文件 | 期望版本 |
|------|----------|
| `skills/software-project-governance/SKILL.md` | 0.44.0 |
| `skills/software-project-governance/core/manifest.json` | 0.44.0 |
| `.claude-plugin/plugin.json` | 0.44.0 |
| `.claude-plugin/marketplace.json` | 0.44.0 |
| `.codex-plugin/plugin.json` | 0.44.0 |
| `project/e2e-test-project/skills/software-project-governance/SKILL.md` | 0.44.0 |
| `project/e2e-test-project/.governance/plan-tracker.md` | 0.44.0 |
| `skills/software-project-governance/infra/hooks/pre-commit` | @version 0.44.0 |
| `skills/software-project-governance/infra/hooks/commit-msg` | @version 0.44.0 |
| `skills/software-project-governance/infra/hooks/post-commit` | @version 0.44.0 |
| `skills/software-project-governance/infra/hooks/prepare-commit-msg` | @version 0.44.0 |

## 发布判定

0.44.0 release package 可以进入提交前发布审查：AUDIT-108、AUDIT-109、FIX-108、FIX-112、FIX-109、FIX-110 与 FIX-111 均已完成，并具备独立审查或验证证据；release package 已完成版本声明、CHANGELOG、release docs、target fixture/projection、hook version、pack registry、manifest/cleanup boundary、status/release pack boundary、`verify_workflow.py` release snippet 和 release gate 期望同步。

本 release 不提交到任何 marketplace，不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success、Codex Desktop marketplace-management E2E PASS 或 1.0.0 production-ready。RISK-036 仍打开，后续 0.45.0~0.46.0 与外部验证闭环前不得关闭。
