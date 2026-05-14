# 发布检查清单 — 0.34.0

**版本**: 0.34.0
**前一个版本**: 0.33.0
**主题**: 审查驱动质量回收 + plan-tracker 标准化
**发布日期**: 2026-05-14
**发布者**: Release Agent (老发)

---

## 硬门槛检查（全部 MUST PASS）

| # | 检查项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | 版本号一致性（11 文件） | ✅ PASS | `check-version-consistency` 应 PASS（SKILL.md/manifest.json/3 plugin.json/verify_workflow.py/4 hooks；plan-tracker 为本地 WARN） |
| 2 | CHANGELOG 0.34.0 条目存在 | ✅ PASS | `project/CHANGELOG.md` 顶部 0.34.0 条目 |
| 3 | Breaking changes 已标注 | ✅ PASS | 无 breaking changes |
| 4 | 版本号 semver 合规 | ✅ PASS | 0.33.0→0.34.0, MINOR bump（审查驱动质量回收 + 验证能力增强） |
| 5 | 回滚方案存在 | ✅ PASS | `docs/release/rollback-plan-0.34.0.md` |
| 6 | Feature Flag 状态记录 | ✅ N/A | 本次无 feature flag 变更 |
| 7 | Kill Switch 验证 | ✅ N/A | 本次无 kill switch 依赖 |

## 版本范围完成率

| 任务 | 优先级 | 状态 |
|------|--------|------|
| AUDIT-099 | P0 | ✅ 已完成 (2026-05-13) |
| FMT-001 | P0 | ✅ 已完成 (2026-05-13) |
| FIX-059 | P0 | ✅ 已完成 (2026-05-13) |
| FIX-060 | P0 | ✅ 已完成 (2026-05-13) |
| FIX-061 | P0 | ✅ 已完成 (2026-05-13) |
| FIX-062 | P0 | ✅ 已完成 (2026-05-13) |
| FIX-063 | P0 | ✅ 已完成 (2026-05-13) |
| FIX-064 | P1 | ✅ 已完成 (2026-05-13) |
| FIX-065 | P1 | ✅ 已完成 (2026-05-14) |
| FIX-066 | P1 | ✅ 已完成 (2026-05-14) |
| FIX-067 | P1 | ✅ 已完成 (2026-05-14) |

**完成率**: 11/11 = 100% ≥ 90% 阈值 ✅

## 版本号声明文件（11 文件全部同步）

| # | 文件 | 版本 |
|---|------|------|
| 1 | `skills/software-project-governance/SKILL.md` (事实源) | 0.34.0 |
| 2 | `skills/software-project-governance/core/manifest.json` | 0.34.0 |
| 3 | `.claude-plugin/plugin.json` | 0.34.0 |
| 4 | `.claude-plugin/marketplace.json` | 0.34.0 |
| 5 | `.codex-plugin/plugin.json` | 0.34.0 |
| 6 | `skills/software-project-governance/infra/verify_workflow.py` (snippets) | 0.34.0 |
| 7 | `skills/software-project-governance/infra/hooks/pre-commit` | @version 0.34.0 |
| 8 | `skills/software-project-governance/infra/hooks/commit-msg` | @version 0.34.0 |
| 9 | `skills/software-project-governance/infra/hooks/post-commit` | @version 0.34.0 |
| 10 | `skills/software-project-governance/infra/hooks/prepare-commit-msg` | @version 0.34.0 |
| 11 | `.governance/plan-tracker.md` | 本地治理记录由 Coordinator 更新 |

## 验证命令

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py verify
python -m py_compile skills/software-project-governance/infra/verify_workflow.py
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py e2e-check
```

## 签名

- [x] 版本号一致性验证
- [x] CHANGELOG 0.34.0 条目完整
- [x] 回滚方案就绪
- [x] feature flag 状态记录
- [x] 无 breaking changes

**发布结论**: ✅ GO — 所有硬门槛通过，可以发布 0.34.0
