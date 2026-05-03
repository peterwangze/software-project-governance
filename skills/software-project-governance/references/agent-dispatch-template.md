# Agent 调度模板

Coordinator spawn sub-agent 时 MUST 使用本模板，**禁止**传自定义 prompt。只能填充模板中的 `{placeholder}` 占位符。

## 模板

```
## 任务：{task_id} — {task_summary}

你是 {agent_role}（{agent_nickname}）。在执行任务前，MUST 先加载两个文件：

1. 角色定义：`{role_definition_path}`——理解你的身份、职责边界、硬门槛
2. 任务规范：`{task_skill_path}`——理解确定性执行步骤

## 任务上下文

- **Task ID**: {task_id}
- **描述**: {task_description}
- **修改文件**: {file_list}
- **验收标准**: {acceptance_criteria}
- **优先级**: {priority}

## 硬门槛（执行前自检）

{hard_gates}

## 执行流程

1. 加载角色定义和任务规范
2. 通读目标文件，理解现有结构
3. 执行修改
4. 自检硬门槛
5. 返回结构化结果给 Coordinator

## 禁止事项

- 不修改非目标文件（"顺带改"）
- 不直接与用户交互（无 AskUserQuestion）
- 不修改 .governance/ 治理记录
- 不做最终决策（决策型任务只出方案）
```

## Coordinator 可填充的占位符

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{task_id}` | 任务 ID | SYSGAP-030 |
| `{task_summary}` | 一句话任务摘要 | 路由表 1:1→1:N 升级 |
| `{agent_role}` | 角色名（英文） | Developer |
| `{agent_nickname}` | 角色昵称（中文） | 阿速 |
| `{role_definition_path}` | 角色定义文件路径 | agents/developer.md |
| `{task_skill_path}` | 任务 SKILL 文件路径 | skills/stage-development/SKILL.md |
| `{task_description}` | 任务详细描述 | 修改 SKILL.md 路由表... |
| `{file_list}` | 要修改的文件列表 | skills/software-project-governance/SKILL.md |
| `{acceptance_criteria}` | 验收标准 | 路由表含后置审查列，表格格式正确 |
| `{priority}` | 优先级 | P0 |
| `{hard_gates}` | 硬门槛列表 | verify_workflow.py PASSED, cross-reference consistency PASSED |

## Coordinator 不得做的事

- ❌ 传自定义 prompt 替代模板
- ❌ 在模板外追加额外指令
- ❌ 修改模板结构
- ❌ 跳过角色定义或任务 SKILL 的加载指令
