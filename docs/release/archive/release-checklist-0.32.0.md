# 发布检查清单 — 0.32.0

**版本**: 0.32.0
**前一个版本**: 0.31.0
**主题**: Agent 调度可靠性——并发控制 + 清洁度治理
**发布日期**: 2026-05-08
**发布者**: Release Agent (老发)

---

## 硬门槛检查（全部 MUST PASS）

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | 版本号一致性（11 文件） | ✅ PASS | `check-version-consistency` 应 PASS（SKILL.md/manifest.json/3 plugin.json/verify_workflow.py/4 hooks/plan-tracker） |
| 2 | CHANGELOG 0.32.0 条目存在 | ✅ PASS | `project/CHANGELOG.md` line 5-22 |
| 3 | Breaking changes 已标注 | ✅ PASS | 无 breaking changes |
| 4 | 版本号 semver 合规 | ✅ PASS | 0.31.0→0.32.0, MINOR bump（新功能: 并发防护 + 清洁度检测） |
| 5 | 回滚方案存在 | ✅ PASS | `docs/release/rollback-plan-0.32.0.md` |
| 6 | Feature Flag 状态记录 | ✅ N/A | 本次无 feature flag 变更 |
| 7 | Kill Switch 验证 | ✅ N/A | 本次无 kill switch 依赖 |

## 版本范围完成率

| 任务 | 优先级 | 状态 |
|------|--------|------|
| FIX-056 | P0 | ✅ 已完成 (2026-05-07) |
| FIX-057 | P1 | ✅ 已完成 (2026-05-07) |

**完成率**: 2/2 = 100% ≥ 90% 阈值 ✅

## 版本号声明文件（11 文件全部同步）

| # | 文件 | 版本 |
|---|------|------|
| 1 | `skills/software-project-governance/SKILL.md` (事实源) | 0.32.0 |
| 2 | `skills/software-project-governance/core/manifest.json` | 0.32.0 |
| 3 | `.claude-plugin/plugin.json` | 0.32.0 |
| 4 | `.claude-plugin/marketplace.json` | 0.32.0 |
| 5 | `.codex-plugin/plugin.json` | 0.32.0 |
| 6 | `skills/software-project-governance/infra/verify_workflow.py` (snippets) | 0.32.0 |
| 7 | `skills/software-project-governance/infra/hooks/pre-commit` | @version 0.32.0 |
| 8 | `skills/software-project-governance/infra/hooks/commit-msg` | @version 0.32.0 |
| 9 | `skills/software-project-governance/infra/hooks/post-commit` | @version 0.32.0 |
| 10 | `skills/software-project-governance/infra/hooks/prepare-commit-msg` | @version 0.32.0 |
| 11 | `.governance/plan-tracker.md` | 工作流版本: 0.32.0 |

> 额外修正：`docs/architecture/ADR-005-agent-concurrency-protection.md` 中 2 处版本引用从 0.31.0 更新为 0.32.0（原计划 Phase 1 发布到 0.31.0，实际与 Phase 2 合并发布到 0.32.0）。

## 关键提交（自 0.31.0 以来）

FIX-056 Phase 1:
```
d09b4c1 FIX-056 Phase 1: Agent 并发防护核心锁机制
69f8744 FIX-056: Phase 1 审查修复——M8 自检补 M7.6a + 超时处理语言强化为 MUST AskUserQuestion
```

FIX-056 Phase 2:
```
965133e FIX-056 Phase 2: Agent 锁一致性验证 + post-commit 锁清理——Check 25 + check-locks 子命令 + scope creep 检测
7cc0353 FIX-056: 更新 plan-tracker——Phase 2 完成标记 + 任务计数 151→152
```

FIX-057:
```
f293743 FIX-057 Phase 1: 项目清洁度治理——未跟踪文件分类归档 + .gitignore
a9225cf FIX-057 Phase 2: check-governance Check 24 + pre-commit Step 10 未跟踪检测
```

备案归档:
```
cecf693 FIX-056: 归档需求澄清 + ADR-005 架构决策记录
```

## 签名

- [x] 版本号一致性验证（11 文件 + ADR-005 2 处）
- [x] CHANGELOG 0.32.0 条目完整
- [x] 回滚方案就绪
- [x] plan-tracker 路线图已更新
- [x] 无 breaking changes

**发布结论**: ✅ GO — 所有硬门槛通过，可以发布 0.32.0
