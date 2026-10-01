# 发布检查清单 — 0.31.0

**版本**: 0.31.0
**前一个版本**: 0.30.0
**主题**: 验证驱动修复——FIX-042 外部项目实战验证发现的 3 个问题修复 + 收尾打磨
**发布日期**: 2026-05-05
**发布者**: Release Agent (老发)

---

## 硬门槛检查（全部 MUST PASS）

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | 版本号一致性（11 文件） | ✅ PASS | `check-version-consistency` PASSED |
| 2 | CHANGELOG 0.31.0 条目存在 | ✅ PASS | `project/CHANGELOG.md` line 5-44 |
| 3 | Breaking changes 已标注 | ✅ PASS | 无 breaking changes |
| 4 | 版本号 semver 合规 | ✅ PASS | 0.30.0→0.31.0, MINOR bump (新功能+修复) |
| 5 | 回滚方案存在 | ✅ PASS | `docs/release/rollback-plan-0.31.0.md` |
| 6 | Feature Flag 状态记录 | ✅ N/A | 本次无 feature flag 变更 |
| 7 | Kill Switch 验证 | ✅ N/A | 本次无 kill switch 依赖 |

## 版本范围完成率

| 任务 | 优先级 | 状态 |
|------|--------|------|
| FIX-031 | P2 | ✅ 已完成 |
| FIX-032 | P2 | ✅ 已完成 |
| FIX-034 | P2 | ✅ 已完成 |
| FIX-039 | P2 | ✅ 已完成 |
| FIX-040 | P2 | ✅ 已完成 |
| FIX-041 | P2 | ✅ 已完成 |
| FIX-042 | P2 | ✅ 已完成 |
| FIX-052 | P1 | ✅ 已完成 |
| FIX-053 | P0 | ✅ 已完成 |
| FIX-054 | P1 | ✅ 已完成 |
| FIX-055 | P2 | ✅ 已完成 |

**完成率**: 11/11 = 100% ≥ 90% 阈值 ✅

## 版本号声明文件（11 文件全部同步）

| # | 文件 | 版本 |
|---|------|------|
| 1 | `skills/software-project-governance/SKILL.md` (事实源) | 0.31.0 |
| 2 | `skills/software-project-governance/core/manifest.json` | 0.31.0 |
| 3 | `.claude-plugin/plugin.json` | 0.31.0 |
| 4 | `.claude-plugin/marketplace.json` | 0.31.0 |
| 5 | `.codex-plugin/plugin.json` | 0.31.0 |
| 6 | `skills/software-project-governance/infra/verify_workflow.py` (snippets) | 0.31.0 |
| 7 | `skills/software-project-governance/infra/hooks/pre-commit` | @version 0.31.0 |
| 8 | `skills/software-project-governance/infra/hooks/commit-msg` | @version 0.31.0 |
| 9 | `skills/software-project-governance/infra/hooks/post-commit` | @version 0.31.0 |
| 10 | `skills/software-project-governance/infra/hooks/prepare-commit-msg` | @version 0.31.0 |
| 11 | `.governance/plan-tracker.md` | 工作流版本: 0.31.0 |

## 关键提交（自 0.30.0 以来）

```
c87652e FIX-055: 补充 commit-msg hook 到所有安装和检测位置
a791b9e FIX-054 P2 #4: 清理 check_m5_compliance() 死代码
029397c FIX-053 复查修复: PLUGIN_SCOPE_DIRS 添加 adapters 目录
3500c76 FIX-042: 外部项目实战验证——6/12 场景通过，3 问题发现并入账
cf45007 FIX-041: Scenario F 面板折叠优化
b94d5ce FIX-039+FIX-040: Agent 工作可见性 + 角色昵称收敛
495bacf FIX-031+FIX-032: 内部归档——空引用+预加载路径修复
fada870 FIX-052: 版本 bump 自动化
```

## 签名

- [x] 版本号一致性验证通过
- [x] CHANGELOG 完整
- [x] 回滚方案就绪
- [x] plan-tracker 路线图已更新

**发布结论**: ✅ GO — 所有硬门槛通过，可以发布 0.31.0
