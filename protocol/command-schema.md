# Command Protocol Schema

本文件定义 `software-project-governance` 插件中所有治理命令（`commands/governance-*.md`）的通用协议约束。

## 目的

将治理命令从"给 agent 阅读的建议"升级为"可被 agent 稳定执行的协议"。每个命令的输入参数、执行流程、输出格式和错误处理均有显式定义，agent 执行完毕后必须进行自检。

## 通用结构要求

每个治理命令文件 MUST 包含以下 5 个章节，不得省略任何一项：

| 章节 | 必须性 | 说明 |
|------|--------|------|
| Input Parameters | MUST | 定义命令接受的参数、类型、是否必需、默认值、有效值 |
| Execution Flow | MUST | 决策树形式的执行步骤（IF → THEN → ELSE），消除歧义 |
| Output Format | MUST | 输出必须包含的字段及其格式，含示例 |
| Error Codes | MUST | 标准化的错误条件和响应模板 |
| Self-Validation | MUST | agent 执行完毕后自检输出是否符合 Output Format |

## Input Parameters 定义规范

```markdown
## Input Parameters

| Parameter | Type | Required | Default | Valid Values | Description |
|-----------|------|----------|---------|-------------|-------------|
| param_name | string/number/enum/boolean | yes/no | <default> | <list or regex> | <description> |
```

- 参数名 MUST 使用小写下划线命名
- 所有 Required=yes 的参数，缺失时 MUST 返回参数缺失错误
- 有 Default 值的参数，缺失时使用默认值
- Valid Values 为空时表示不限制

## Execution Flow 定义规范

采用决策树格式，消除自然语言的歧义空间：

```markdown
## Execution Flow

### Step N: <step name>
- **IF** `<condition>` → `<action>`
- **ELSE IF** `<condition>` → `<action>`
- **ELSE** → `<action>`
```

每一步的 action MUST 是可被 agent 执行的明确操作，禁止模糊表述（如 "适当处理"、"合理调整"）。

## Output Format 定义规范

```markdown
## Output Format

### Required Fields
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| field_name | string/number/list/table | <description> | <example value> |

### Output Template
```

输出模板（Output Template）提供完整的输出样例，agent 必须按此结构输出。

## Error Codes 定义规范

```markdown
## Error Codes

| Code | Condition | User Message | Agent Action |
|------|-----------|-------------|--------------|
| CMD-ERR-XXX | <触发条件> | <展示给用户的文字> | <agent 必须采取的行动> |
```

错误码格式：`{CMD}-ERR-{NNN}`，其中 CMD 为命令缩写（INIT/STATUS/GATE/VERIFY），NNN 为 3 位数字。

User Message MUST 包含：
1. 错误描述
2. 建议的修复动作

Agent Action MUST 是明确可执行的操作（不包含"考虑"、"可能"等模糊词）。

## Self-Validation 定义规范

```markdown
## Self-Validation

After execution, agent MUST verify:
- [ ] All Required Fields in Output Format are present
- [ ] No field contains placeholder text (e.g., "TBD", "TODO", "待补")
- [ ] Numeric fields contain actual numbers, not descriptions
- [ ] All error conditions were checked
```

## 命令列表

| 命令 | 文件 | 用途 | 输入参数 | 输出类型 |
|------|------|------|---------|---------|
| governance-init | `commands/governance-init.md` | 初始化项目治理 | 5 个参数 | 确认消息 |
| governance-status | `commands/governance-status.md` | 展示治理状态 | 0 个参数 | 状态面板 |
| governance-gate | `commands/governance-gate.md` | 检查特定 Gate | 1 个可选参数 | Gate 检查结果 |
| governance-verify | `commands/governance-verify.md` | 治理健康检查 | 0 个参数 | 健康报告 |

## Agent 执行纪律

当用户调用任一治理命令时，agent MUST：

1. **加载命令文件**：读取 `commands/governance-{name}.md`
2. **校验输入**：对照 Input Parameters 表格校验用户提供的参数
3. **按序执行**：严格按照 Execution Flow 的决策树执行，不跳步、不自创步骤
4. **按模板输出**：使用 Output Format 中定义的 Output Template 格式输出
5. **执行自检**：完成输出后执行 Self-Validation 检查清单

违反以上任一步骤 = 命令执行未通过质量门禁。
