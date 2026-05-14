# 回滚方案 — 0.34.0

**版本**: 0.34.0
**创建日期**: 2026-05-14
**创建者**: Release Agent (老发)

> 没有回滚方案的发布 = 赌博。任何发布——不管多小——都必须有回滚方案。

---

## 回滚触发条件

以下任一条件触发回滚：
1. `check-version-consistency` 在新环境中 FAIL（版本号声明文件不一致）
2. 真实 E2E 命令矩阵误报或漏报，导致 `/governance` 主路径验证失真
3. `/governance-review` review fallback 防护阻断正常独立审查
4. archive.py 持续归档触发误归档当前活跃任务或证据
5. G10/G11 Gate 判定仍被弱代理证据误判为 PASS
6. 治理信噪比收敛误伤真实失败信号

## 回滚步骤

### Step 1: 版本号回退

将所有版本声明文件从 0.34.0 回退到 0.33.0：

```bash
sed -i 's/0.34.0/0.33.0/g' \
  skills/software-project-governance/SKILL.md \
  skills/software-project-governance/core/manifest.json \
  skills/software-project-governance/infra/verify_workflow.py \
  .claude-plugin/plugin.json \
  .claude-plugin/marketplace.json \
  .codex-plugin/plugin.json \
  skills/software-project-governance/infra/hooks/pre-commit \
  skills/software-project-governance/infra/hooks/commit-msg \
  skills/software-project-governance/infra/hooks/post-commit \
  skills/software-project-governance/infra/hooks/prepare-commit-msg
```

### Step 2: Git tag 处理

```bash
git tag -d v0.34.0
git push origin :refs/tags/v0.34.0
```

仅在 tag 已创建或已推送时执行本步骤。

### Step 3: CHANGELOG 回退

```bash
# 从 project/CHANGELOG.md 移除 ## [0.34.0] 段
# 或使用 git revert 回退发布 commit
```

### Step 4: release docs 回退

移除本版本发布资料：

```bash
rm docs/release/release-checklist-0.34.0.md
rm docs/release/rollback-plan-0.34.0.md
rm docs/release/feature-flags-0.34.0.md
```

### Step 5: 验证

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py verify
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py e2e-check
```

预期：产品版本声明回到 0.33.0 且验证无新增 FAIL。

## 回滚分级

| 场景 | 严重程度 | 预计回滚时间 | 回滚范围 |
|------|---------|------------|---------|
| 版本号不一致 | LOW | 5 min | 仅修正遗漏的声明文件 |
| E2E 命令矩阵误报/漏报 | HIGH | 20 min | 回退 FIX-060 相关验证逻辑 |
| review fallback 阻断正常审查 | HIGH | 15 min | 回退 FIX-061 相关命令/检查 |
| 持续归档误归档活跃数据 | HIGH | 20 min | 回退 FIX-063 archive.py 触发逻辑 |
| G10/G11 Gate 误判 | MEDIUM | 15 min | 回退 FIX-067 Gate 判定逻辑 |
| 治理检查信噪比误伤 | MEDIUM | 10 min | 调整 FIX-066 相关检查阈值 |

## 时间估算

- 全量回退到 0.33.0: **~20 分钟**
- 单文件修正: **~5 分钟**
- 单项验证逻辑回退: **~10-20 分钟**

## 回滚后验证

1. `check-version-consistency` PASSED（产品声明文件显示 0.33.0）
2. `verify` 无新增 FAIL
3. `check-governance --fail-on-issues` 无新增 FAIL
4. `e2e-check` 恢复到 0.33.0 预期行为
5. Git hooks 四件套全部存在且版本正确（@version 0.33.0）

## 相关版本

- 前一个稳定版本: v0.33.0
- 回退目标版本: v0.33.0
