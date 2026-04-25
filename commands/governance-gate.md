# governance-gate — 特定 Gate 检查

检查指定的治理 Gate 是否满足通过条件。

## Input Parameters

| Parameter | Type | Required | Default | Valid Values | Description |
|-----------|------|----------|---------|-------------|-------------|
| gate_id | enum | no | — | G1 / G2 / G3 / G4 / G5 / G6 / G7 / G8 / G9 / G10 / G11 | 待检查的 Gate ID。不提供时展示所有 Gate 的摘要 |

## Execution Flow

### Step 1: 检查是否已初始化
- **IF** `.governance/plan-tracker.md` 不存在 → 返回错误 `GATE-ERR-001`（未初始化）
- **ELSE** → 继续 Step 2

### Step 2: 校验 gate_id（如果提供）
- **IF** gate_id 提供但不在 [G1, G2, ..., G11] 中 → 返回错误 `GATE-ERR-002`（无效 gate_id）
- **ELSE** → 继续 Step 3

### Step 3: 读取 Gate 定义
- 读取 `skills/software-project-governance/references/stage-gates.md`，提取以下内容：
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

### Step 6: 按 Output Format 模板输出结果

## Output Format

### Required Fields
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| gate_id | string | Gate ID | "G8" |
| gate_name | string | Gate 名称 | "防护网就绪" |
| current_status | string | 当前状态 | "passed" |
| check_items | table | 检查项及判定结果 | 见模板 |

### Output Template (单个 Gate)

```
Gate {gate_id} — {gate_name}
Current status: {current_status}

Check items:
  ✅ / ❌ / ⚠️ {check_item_1}
     Evidence: {evidence_reference or "缺失"}
  ✅ / ❌ / ⚠️ {check_item_2}
     Evidence: {evidence_reference or "缺失"}
  ...

Result: {passed / failed / blocked}
{if failed}Missing items: {count} — see ❌ lines above
{if blocked}Blocker: {description from plan-tracker}
```

### Output Template (All Gates Summary)

```
Gate Summary:
  G1  {status_icon} {status_text}
  G2  {status_icon} {status_text}
  ...
  G11 {status_icon} {status_text}

Legend: ✅ passed  ⚠️ passed-with-conditions  ⏳ pending  ❌ failed  🚫 blocked
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

## Error Codes

| Code | Condition | User Message | Agent Action |
|------|-----------|-------------|-------------|
| GATE-ERR-001 | `.governance/plan-tracker.md` 不存在 | "Project has not been initialized yet. Run `/governance-init` to set up governance tracking before checking gates." | 停止执行 |
| GATE-ERR-002 | gate_id 不在 G1~G11 范围内 | "Invalid gate '{value}'. Valid gates are: G1 through G11." | 停止执行 |

## Self-Validation

After execution, agent MUST verify:
- [ ] Gate ID is valid and recognized
- [ ] Every check item has a clear PASS/FAIL/BLOCKED determination
- [ ] FAIL items have the missing evidence/reason explicitly stated
- [ ] Output template structure matches the defined format
- [ ] Status icons match the icon mapping table
- [ ] If showing single gate, stage exit conditions are cross-referenced
