# 发布检查清单 — 0.35.0

**版本**: 0.35.0
**前一个版本**: 0.34.0
**主题**: 八维度复核收口——架构事实源、适配层、Agent 边界、工具化、防跑偏看护与 E2E 真实性
**发布日期**: 2026-05-20
**发布者**: Release Agent

---

## 硬门槛检查（全部 MUST PASS）

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | 版本号一致性 | ✅ PASS | `check-version-consistency` |
| 2 | CHANGELOG 0.35.0 条目存在 | ✅ PASS | `project/CHANGELOG.md` 顶部 0.35.0 条目 |
| 3 | Breaking changes 已标注 | ✅ PASS | 无 breaking changes |
| 4 | 版本号 semver 合规 | ✅ PASS | 0.34.0→0.35.0, MINOR bump（八维度复核收口 + E2E 真实性增强） |
| 5 | 回滚方案存在 | ✅ PASS | `docs/release/rollback-plan-0.35.0.md` |
| 6 | Feature Flag 状态记录 | ✅ N/A | 本次无 feature flag 变更 |
| 7 | Kill Switch 验证 | ✅ N/A | 本次无 kill switch 依赖 |

## 版本范围完成率

| 任务 | 优先级 | 状态 |
|------|--------|------|
| AUDIT-100 | P0 | ✅ 已完成 (2026-05-14) |
| FIX-069 | P0 | ✅ 已完成 (2026-05-19) |
| FIX-070 | P0 | ✅ 已完成 (2026-05-15) |
| FIX-071 | P0 | ✅ 已完成 (2026-05-19) |
| FIX-072 | P1 | ✅ 已完成 (2026-05-20) |
| FIX-073 | P1 | ✅ 已完成 (2026-05-20) |
| FIX-074 | P1 | ✅ 已完成 (2026-05-20) |

**完成率**: 7/7 = 100% ≥ 90% 阈值 ✅

## 版本号声明文件

| # | 文件 | 版本 |
|---|------|------|
| 1 | `skills/software-project-governance/SKILL.md` (事实源) | 0.35.0 |
| 2 | `skills/software-project-governance/core/manifest.json` | 0.35.0 |
| 3 | `.claude-plugin/plugin.json` | 0.35.0 |
| 4 | `.claude-plugin/marketplace.json` | 0.35.0 |
| 5 | `.codex-plugin/plugin.json` | 0.35.0 |
| 6 | `skills/software-project-governance/infra/verify_workflow.py` (snippets) | 0.35.0 |
| 7 | `skills/software-project-governance/infra/hooks/pre-commit` | @version 0.35.0 |
| 8 | `skills/software-project-governance/infra/hooks/commit-msg` | @version 0.35.0 |
| 9 | `skills/software-project-governance/infra/hooks/post-commit` | @version 0.35.0 |
| 10 | `skills/software-project-governance/infra/hooks/prepare-commit-msg` | @version 0.35.0 |

## 发布验证命令

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py verify
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py e2e-check
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.35.0 --require-changelog --runtime-adapters
python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -v
```

## 适配状态声明

0.35.0 真实化了四平台入口状态，但不把 blocked agent runtime 伪装为 full coverage：

| 平台 | 0.35.0 状态 |
|------|-------------|
| Claude Code | real agent target cwd E2E PASS |
| Codex | current Codex App workflow session PASS；headless `codex exec` timeout 已记录 |
| Gemini | runtime/version probe + target cwd Python 命令 PASS；real Gemini agent 因本机 auth 缺失 blocked |
| opencode | runtime/version probe + target cwd Python 命令 PASS；real `opencode run` 因 provider/model 配置 blocked |

## 签名

- [x] 版本号一致性验证
- [x] CHANGELOG 0.35.0 条目完整
- [x] 回滚方案就绪
- [x] feature flag 状态记录
- [x] 无 breaking changes
- [x] Release Reviewer 复核通过

**发布结论**: ✅ GO — 所有硬门槛通过，可以发布 0.35.0
