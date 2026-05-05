# governance-gate — 特定 Gate 检查

> **推荐使用 `/governance`**——自动检测项目状态并在 Scenario F 中展示 Gate 状态表。本命令保留为快捷方式，直接检查指定 Gate。

检查指定的治理 Gate 是否满足通过条件。

## 输入参数

| 参数 | 类型 | 必需 | 默认值 | 有效值 | 描述 |
|-----------|------|----------|---------|-------------|-------------|
| gate_id | 枚举 | 否 | — | G1 / G2 / G3 / G4 / G5 / G6 / G7 / G8 / G9 / G10 / G11 | 待检查的 Gate ID。不提供时展示所有 Gate 的摘要 |

## 执行流程

### Step 1: 检查是否已初始化
- **IF** `.governance/plan-tracker.md` 不存在 → 返回错误 `GATE-ERR-001`（未初始化）
- **ELSE** → 继续 Step 2

### Step 2: 校验 gate_id（如果提供）
- **IF** gate_id 提供但不在 [G1, G2, ..., G11] 中 → 返回错误 `GATE-ERR-002`（无效 gate_id）
- **ELSE** → 继续 Step 3

### Step 3: 读取 Gate 定义
- 读取 `skills/software-project-governance/core/stage-gates.md`，提取以下内容：
  - gate_id 对应的 Gate 检查项列表
  - 每个检查项的判定标准
- 读取对应阶段的子工作流文件 `skills/software-project-governance/stages/{stage}/sub-workflow.md`，提取退出条件 checklist

### Step 4: 读取项目当前状态
- 读取 `.governance/plan-tracker.md`：
  - gate_id 在 Gate 状态跟踪表中的当前状态
  - 关联阶段的任务完成情况
- 读取 `.governance/evidence-log.md`：查找关联 gate_id 的证据条目
- 读取 `.governance/decision-log.md`：查找关联 gate_id 的决策条目

### Step 5: 逐项判定
对每个 Gate 检查项：
- **IF** evidence-log 中有对应的证据条目 → 标记为 PASS
- **IF** evidence-log 中无对应证据 BUT 子工作流的退出条件 checklist 全部完成 → 标记为 PASS（注明：证据待补录）
- **IF** evidence-log 中无对应证据 AND 退出条件 checklist 未完成 → 标记为 FAIL
- **IF** plan-tracker 中该 Gate 状态为 blocked → 标记为 BLOCKED（注明阻塞原因）

### Step 6: 按输出格式模板输出结果

## 输出格式

### 必要字段
| 字段 | 类型 | 说明 | 示例 |
|-------|------|-------------|---------|
| gate_id | 字符串 | Gate ID | "G8" |
| gate_name | 字符串 | Gate 名称 | "防护网就绪" |
| current_status | 字符串 | 当前状态 | "passed" |
| check_items | 表格 | 检查项及判定结果 | 见模板 |

### 输出模板（单个 Gate）

```
Gate {gate_id} — {gate_name}
当前状态: {current_status}

检查项:
  ✅ / ❌ / ⚠️ {check_item_1}
     证据: {evidence_reference 或 "缺失"}
  ✅ / ❌ / ⚠️ {check_item_2}
     证据: {evidence_reference 或 "缺失"}
  ...

结果: {passed / failed / blocked}
{if failed}缺失项: {count} — 见上方 ❌ 行
{if blocked}阻塞原因: {从 plan-tracker 获取的描述}
```

### 输出模板（全部 Gate 摘要）

```
Gate 摘要:
  G1  {status_icon} {status_text}
  G2  {status_icon} {status_text}
  ...
  G11 {status_icon} {status_text}

图例: ✅ passed  ⚠️ passed-with-conditions  ⏳ pending  ❌ failed  🚫 blocked
```

状态图标映射：
| 状态 | 图标 |
|------|------|
| passed | ✅ |
| passed-on-entry | ✅ |
| passed-with-conditions | ⚠️ |
| pending | ⏳ |
| failed | ❌ |
| blocked | 🚫 |

## 错误码

| 代码 | 条件 | 用户消息 | Agent 动作 |
|------|-----------|-------------|-------------|
| GATE-ERR-001 | `.governance/plan-tracker.md` 不存在 | "项目尚未初始化。在检查 Gate 之前，请先运行 `/governance-init` 设置治理跟踪。" | 停止执行 |
| GATE-ERR-002 | gate_id 不在 G1~G11 范围内 | "无效 Gate '{value}'。有效 Gate 为：G1 至 G11。" | 停止执行 |

## 自校验

执行后，agent MUST 验证：
- [ ] Gate ID 有效且可识别
- [ ] 每个检查项均有明确的 PASS/FAIL/BLOCKED 判定
- [ ] FAIL 项已明确说明缺失的证据/原因
- [ ] 输出模板结构与定义的格式一致
- [ ] 状态图标与图标映射表一致
- [ ] 若展示单个 Gate，已交叉引用阶段退出条件
