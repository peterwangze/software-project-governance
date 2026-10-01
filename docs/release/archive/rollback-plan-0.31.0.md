# 回滚方案 — 0.31.0

**版本**: 0.31.0
**创建日期**: 2026-05-05
**创建者**: Release Agent (老发)

> 没有回滚方案的发布 = 赌博。任何发布——不管多小——都必须有回滚方案。

---

## 回滚触发条件

以下任一条件触发回滚：
1. `check-version-consistency` 在新环境中 FAIL
2. cleanup.py 在生产环境中误删用户文件（边界回归）
3. commit-msg hook 缺失导致消息检查跳空
4. Check 10 M5 检测在用户项目中出现误报

## 回滚步骤

### Step 1: 版本号回退

将所有版本声明文件从 0.31.0 回退到 0.30.0：

```bash
# 回退 11 个文件的版本声明
sed -i 's/0.31.0/0.30.0/g' \
  skills/software-project-governance/SKILL.md \
  skills/software-project-governance/core/manifest.json \
  skills/software-project-governance/infra/verify_workflow.py \
  .claude-plugin/plugin.json \
  .claude-plugin/marketplace.json \
  .codex-plugin/plugin.json \
  skills/software-project-governance/infra/hooks/pre-commit \
  skills/software-project-governance/infra/hooks/commit-msg \
  skills/software-project-governance/infra/hooks/post-commit \
  skills/software-project-governance/infra/hooks/prepare-commit-msg \
  .governance/plan-tracker.md

# 回退 plan-tracker 路线图状态
# 在 .governance/plan-tracker.md 中将 0.31.0 行从 "已发布" 改回 "发布中"
```

### Step 2: Git tag 处理

```bash
# 删除本地 tag
git tag -d v0.31.0

# 删除远程 tag（如已推送）
git push origin :refs/tags/v0.31.0
```

### Step 3: CHANGELOG 回退

```bash
# 手动从 project/CHANGELOG.md 移除 ## [0.31.0] 段（lines 5-44）
# 或使用 git revert 回退发布 commit
```

### Step 4: 验证

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
```

预期：所有文件显示 0.30.0 且一致。

## 回滚分级

| 场景 | 严重程度 | 预计回滚时间 | 回滚范围 |
|------|---------|------------|---------|
| 版本号不一致（check-version-consistency FAIL） | LOW | 5 min | 仅修正遗漏的文件 |
| cleanup.py 误删用户文件 | CRITICAL | 15 min | 全量回退到 0.30.0 + 通知受影响用户 |
| commit-msg hook 缺失 | MEDIUM | 10 min | 补充 hook 安装（不需版本回退） |
| Check 10 误报 | MEDIUM | 10 min | 回退 verify_workflow.py（不需版本回退） |

## 时间估算

- 全量回退到 0.30.0: **~15 分钟**
- 单文件修正: **~5 分钟**
- Hook 补充安装: **~10 分钟**

## 回滚后验证

1. `check-version-consistency` PASSED
2. `check-governance` 无新增 FAIL
3. cleanup.py `--dry-run` 不输出用户文件
4. Git hooks 三件套全部存在且版本正确

## 相关版本

- 前一个稳定版本: v0.30.0 (tag)
- 回退目标版本: v0.30.0
