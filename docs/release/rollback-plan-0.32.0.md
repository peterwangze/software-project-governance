# 回滚方案 — 0.32.0

**版本**: 0.32.0
**创建日期**: 2026-05-08
**创建者**: Release Agent (老发)

> 没有回滚方案的发布 = 赌博。任何发布——不管多小——都必须有回滚方案。

---

## 回滚触发条件

以下任一条件触发回滚：
1. `check-version-consistency` 在新环境中 FAIL（版本号声明文件不一致）
2. `agent-locks.json` 格式损坏导致锁机制全部失效（Coordinator 误判无锁 → 重复 spawn）
3. `check-locks` 子命令输出异常（误报锁残留或漏报）
4. pre-commit Step 10 未跟踪检测阻断正常 commit（误报）
5. Check 24 未跟踪检测在用户项目中误报

## 回滚步骤

### Step 1: 版本号回退

将所有版本声明文件从 0.32.0 回退到 0.31.0：

```bash
# 回退 11 个文件的版本声明
sed -i 's/0.32.0/0.31.0/g' \
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

# 回退 ADR-005 版本引用
sed -i 's/0.32.0/0.31.0/g' docs/architecture/ADR-005-agent-concurrency-protection.md
```

### Step 2: Git tag 处理

```bash
# 删除本地 tag
git tag -d v0.32.0

# 删除远程 tag（如已推送）
git push origin :refs/tags/v0.32.0
```

### Step 3: CHANGELOG 回退

```bash
# 从 project/CHANGELOG.md 移除 ## [0.32.0] 段（lines 5-22）
# 或使用 git revert 回退发布 commit
```

### Step 4: plan-tracker 路线图回退

在 `.governance/plan-tracker.md` 中：
- 将 0.32.0 行从 "已发布" 改回 "规划中"
- 将 `工作流版本` 从 0.32.0 回退到 0.31.0
- 将 REL-008 状态从 "✅ 已完成" 回退到 "🔄 进行中"

### Step 5: 验证

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-governance
```

预期：所有文件显示 0.31.0 且一致，check-governance 无新增 FAIL。

## 回滚分级

| 场景 | 严重程度 | 预计回滚时间 | 回滚范围 |
|------|---------|------------|---------|
| 版本号不一致（check-version-consistency FAIL） | LOW | 5 min | 仅修正遗漏的文件 |
| agent-locks.json 格式损坏 | HIGH | 15 min | 全量回退到 0.31.0 + 删除锁文件 + 通知所有活跃 session |
| check-locks 误报/漏报 | MEDIUM | 10 min | 回退 verify_workflow.py check-locks 子命令（不需全量版本回退） |
| pre-commit Step 10 误报阻断 | MEDIUM | 10 min | 回退 pre-commit hook Step 10（不需全量版本回退） |
| Check 24 误报 | LOW | 5 min | 调整 Check 24 阈值（不需版本回退） |

## 时间估算

- 全量回退到 0.31.0: **~15 分钟**
- 单文件修正: **~5 分钟**
- 子命令/hook 回退: **~10 分钟**

## 回滚后验证

1. `check-version-consistency` PASSED（所有文件显示 0.31.0）
2. `check-governance` 无新增 FAIL
3. `check-locks` 正常执行（如锁文件已删除则跳过）
4. Git hooks 四件套全部存在且版本正确（@version 0.31.0）
5. Coordinator spawn 协议回退到 M7.6（无锁检查）

## 相关版本

- 前一个稳定版本: v0.31.0 (tag)
- 回退目标版本: v0.31.0
