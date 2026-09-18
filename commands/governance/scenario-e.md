# Scenario E: 异常恢复

> 本文件不在默认注入面——命中 `scenario_hint == "E"` 后按路由层契约 Read。
> 完整执行规程：原 `## Scenario E: 异常恢复` 节逐字搬移（零语义丢失）。

## Scenario E: 异常恢复

**检测条件**：任一异常标记触发

**时序（FEAT-034 首次交互前置）**：异常标记本身来自 resolve_entry 判定（fail-closed 已在第一动作保证，不受本重排影响）——首次 ask 先呈现已知异常标记 + 选项（立即全量诊断 / 暂缓并记录为已知异常），下方 E1 全量诊断作为深检在用户选择后执行；用户选择推进类动作时 MUST 先补齐对应深检再继续。

### Step E1: 全量诊断

执行以下检查并分类严重级别：

**P0 — 阻断级（不修复则治理失效）**：
| 检查项 | 检测方法 |
|--------|---------|
| Hooks 缺失 | `test -f .git/hooks/pre-commit` |
| plan-tracker 损坏 | 解析 markdown 表格，检查 `## 项目配置` 和 `## Gate 状态跟踪` 节 |
| 文件缺失 | 检查 `.governance/` 中 plan-tracker/evidence/decision/risk 是否都存在且非空 |

**P1 — 警告级（治理退化但未完全失效）**：
| 检查项 | 检测方法 |
|--------|---------|
| 证据缺口 | 运行 `python <plugin_home>/infra/verify_workflow.py check-governance` Check 1（`<plugin_home>` 来自 resolve_entry.py） |
| Gate 不一致 | Check 3 |
| 过期风险 | Check 2 + Check 8 |
| 过期任务 deadline | Check 9 |
| Commit 无 task ID | Check 7 |
| **归档失效（FIX-159/160）** | Check 28s `check-governance-data-size`：plan-tracker/evidence-log/decision-log/risk-log 超 200KB(WARN)/250KB(ERROR) 但 `archive.py migrate --auto --dry-run` 报无可归档 = 异常（膨胀未被归档守护）|

### Step E2: 展示诊断面板

通过 AskUserQuestion 展示：

```
治理异常诊断:

P0 (阻断):
  ❌ Git hooks 缺失——commit 不受治理约束
  ❌ plan-tracker.md 损坏——无法读取项目状态

P1 (警告):
  ⚠️ 3个已完成任务无证据
  ⚠️ 2个风险超过7天未更新

修复选项:
(1) 一键修复全部 ({p0_count}P0 + {p1_count}P1)
(2) 仅修复 P0 ({p0_count}项)
(3) 先看详情
(4) 暂不处理（记录为已接受风险）
```

### Step E3: 执行修复

按用户选择执行：

- **Hooks 缺失**: 运行 `python <plugin_home>/infra/resolve_entry.py --json` 拿到 `plugin_home`，再执行 `cp "<plugin_home>/infra/hooks/pre-commit" .git/hooks/pre-commit && cp "<plugin_home>/infra/hooks/commit-msg" .git/hooks/commit-msg && cp "<plugin_home>/infra/hooks/post-commit" .git/hooks/post-commit`
- **plan-tracker 损坏**: 尝试从 markdown 表格结构恢复；失败则从 profile 模板重建（保留 evidence-log/decision-log/risk-log）
- **文件缺失**: 从 `core/templates/` 复制模板
- **证据缺口**: 创建占位证据条目（标记"补录——需用户确认"）
- **过期风险/任务**: 询问用户是否仍然活跃，是→更新截止日期，否→关闭

### Step E4: 输出修复报告

```
修复完成:
  ✅ Git hooks 已安装
  ✅ plan-tracker.md 已修复
  ⚠️ 3个证据缺口已创建占位条目(标记"补录")

仍需关注:
  - 补录证据需用户确认内容
```

**输出**：诊断报告 + 已执行的修复 + 仍需关注的事项

修复完成后 **MUST 自动衔接 Scenario F**——展示修复后的最新状态面板。
