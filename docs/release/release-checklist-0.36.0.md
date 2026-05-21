# 发布检查清单 — 0.36.0

**版本**: 0.36.0
**前一个版本**: 0.35.0
**主题**: 真实 agent runtime E2E 闭环补强
**发布日期**: 2026-05-22
**发布者**: Release Agent

---

## 硬门槛检查（全部 MUST PASS）

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | 版本号一致性 | ✅ PASS | `check-version-consistency` |
| 2 | CHANGELOG 0.36.0 条目存在 | ✅ PASS | `project/CHANGELOG.md` 顶部 0.36.0 条目 |
| 3 | Breaking changes 已标注 | ✅ PASS | 无 breaking changes |
| 4 | 版本号 semver 合规 | ✅ PASS | 0.35.0→0.36.0, MINOR bump（真实 runtime E2E 补强） |
| 5 | 回滚方案存在 | ✅ PASS | `docs/release/rollback-plan-0.36.0.md` |
| 6 | Feature Flag 状态记录 | ✅ N/A | 本次无 feature flag 变更 |
| 7 | Kill Switch 验证 | ✅ N/A | 本次无 kill switch 依赖 |

## 版本范围完成率

| 任务 | 优先级 | 状态 |
|------|--------|------|
| AUDIT-101 | P0 | ✅ 已完成 (2026-05-20) |
| FIX-075 | P0 | ✅ 已完成 (2026-05-21) |
| FIX-076 | P0 | ✅ 已完成 (2026-05-21) |
| FIX-077 | P0 | ✅ 已完成 (2026-05-21) |
| FIX-078 | P1 | ✅ 已完成 (2026-05-21) |
| FIX-079 | P1 | ✅ 已完成 (2026-05-21) |

**完成率**: 6/6 = 100% ≥ 90% 阈值 ✅

## 版本号声明文件

| # | 文件 | 版本 |
|---|------|------|
| 1 | `skills/software-project-governance/SKILL.md` (事实源) | 0.36.0 |
| 2 | `skills/software-project-governance/core/manifest.json` | 0.36.0 |
| 3 | `.claude-plugin/plugin.json` | 0.36.0 |
| 4 | `.claude-plugin/marketplace.json` | 0.36.0 |
| 5 | `.codex-plugin/plugin.json` | 0.36.0 |
| 6 | `skills/software-project-governance/infra/verify_workflow.py` (snippets) | 0.36.0 |
| 7 | `skills/software-project-governance/infra/hooks/pre-commit` | @version 0.36.0 |
| 8 | `skills/software-project-governance/infra/hooks/commit-msg` | @version 0.36.0 |
| 9 | `skills/software-project-governance/infra/hooks/post-commit` | @version 0.36.0 |
| 10 | `skills/software-project-governance/infra/hooks/prepare-commit-msg` | @version 0.36.0 |

## 发布验证命令

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py verify
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py e2e-check
python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters --runtime
python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --timeout 90
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.36.0 --require-changelog --runtime-adapters
python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -v
```

## 适配状态声明

0.36.0 把主流 agent 适配闭环标准固定为真实环境 E2E 证据，不把 blocked 平台伪装为 full coverage：

| 平台 | 0.36.0 状态 |
|------|-------------|
| Claude Code | real agent target cwd E2E PASS |
| Codex | CLI runtime probe PASS；headless `codex exec` target-cwd timeout BLOCKED；Codex App session 不替代 full coverage |
| Gemini | runtime/version probe + `gemini-auth-preflight` BLOCKED（auth missing/401）；不宣称 full coverage |
| opencode | provider/model preflight PASS；90s target-cwd real runtime E2E PASS；full_e2e_verified=true |

## 签名

- [x] 版本号一致性验证
- [x] CHANGELOG 0.36.0 条目完整
- [x] 回滚方案就绪
- [x] feature flag 状态记录
- [x] 无 breaking changes
- [x] Release Reviewer 复核通过

**发布结论**: ✅ GO — 所有硬门槛通过，可以发布 0.36.0
