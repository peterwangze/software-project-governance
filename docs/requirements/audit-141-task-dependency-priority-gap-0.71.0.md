# AUDIT-141: 任务依赖与优先级系统三重断裂

> **状态**: 分析完成，待修复（FIX-225~229）
> **触发**: 用户反馈"任务规划不分析依赖关系和优先级" + "完成后没法推荐推进事项" + "新事项不分析优先级"
> **关联**: task-gate-model.md（依赖模型声明但未激活）, interaction-boundary.md:187/217（规定机械行为）, 变更控制 stub

## 1. 三重断裂

### 断裂 1：依赖数据是自由文本，无机器可解析图

plan-tracker.md 的 `依赖` 列存在（如 FIX-162 行：`TD-014✅, DEC-090, DEC-091, RISK-039`），但是：
- **自由文本 prose**——逗号分隔的混合 ID（task + decision + risk），无解析规则
- **`### 1.0.0 依赖链`**（行 191）是 release-milestone 时间线（ASCII 流程图：`0.11.0 ✅ → ... → 1.0.0 blocked`），不是 task-level DAG
- **模板从未升级**——`core/templates/plan-tracker.md` 有 **0** 个 `依赖` 引用，新项目 bootstrap 无依赖跟踪

**无拓扑排序、无传递闭包、无"什么被解除阻塞"计算。** grep `topolog|blocked_by|unblock|ready.*task` 在 infra/*.py 中零匹配（loop_admission.py 的 check_admission 在非活跃 runtime 中）。

### 断裂 2：依赖模型声明但从未激活

task-gate-model.md（行 23-46）定义了：
- `依赖` 列格式
- Task-Gate 状态（pending/passed/blocked/skipped）
- 传递阻塞规则（"前置 Gate blocked → 当前可执行但产出可能无效"）
- 循环检测（"Coordinator 在分解任务时检查循环依赖"）

但模型**需要 `workflow_model: agent-team`** 在 plan-tracker 配置中（行 19）。live plan-tracker.md **无 `workflow_model` 字段**——模型从未被激活。传递阻塞规则是纯 prose，无代码 emit 警告。

### 断裂 3：运行时指令主动规定机械行为

interaction-boundary.md:217（反打断规则）**明确规定**：
> 任务完成后停下来问"接下来做什么" → **查样例跟踪表，取下一个最高优先级未完成任务继续执行**

这就是用户投诉的机械行为——**编码为正确行为**。behavior-protocol.md M7.4 step 6（行 544）重复："继续 plan-tracker 中下一个最高优先级任务"。

**无任何指令**要求 Coordinator 在选择下一步前咨询 `依赖` 列。bootstrap Step 1 列 `## 1.0.0 依赖链` 为优先级 (f)，但不指示从它计算 unblocked tasks。

## 2. 完成关键节点无法推荐（CONFIRMED）

- loop_exit 事件（loop_gate_processor.py:586-599）只记录状态（fire-and-forget bookkeeping），**不产生**"find next unblocked unit" 或 "produce recommendation"
- AskUserQuestion 完成选项是"确认/修改/拒绝"（交付审查），不是"下一步做什么"
- `commands/governance.md:324` 有 `推荐下一步: {next_priority}` 但是**未填充模板变量**——无代码/指令从依赖计算它

## 3. 新事项不分析优先级（CONFIRMED）

- **变更控制 section 是 2 行 stub**（verify_workflow.py:17413-17417）："标准路径: 变更提出→优先级判定→版本适配→冲突检查→创建 task"——流程图标签，无可执行步骤
- **change-impact-checklist.md 只查代码级依赖**（"哪些文件引用了被修改的文件"），不查任务级依赖（新任务是否阻塞/解除阻塞其他任务）
- **M7.5 step 2**（行 578）说"创建任务→执行"，**无**"插入前分析优先级/依赖/冲突"步骤
- **快速通道**（M1.2 行 47-73）"最小入账→立即执行→事后补齐→Gate 审计"——**明确推迟**分析到执行后

## 4. 跨问题根因

三个问题共享一个根因：**依赖图只存在于声明式模型（task-gate-model.md）和非活跃 runtime（loop_admission.py）中，与标准 task-selection 流程无桥接。** 运行时指令（interaction-boundary.md:187/217, behavior-protocol.md M7.4 step 6）规定"next highest-priority incomplete task"无依赖推理，变更控制 section 应治理新任务插入但是 2 行 stub。

## 5. 修复方向

### FIX-225: plan-tracker 依赖列结构化 + 模板升级
- 将 `依赖` 列从自由文本升级为机器可解析格式（逗号分隔 task ID，如 `FIX-162,DEC-090`）
- 模板补齐依赖列 + `workflow_model` 字段
- 解析工具能区分 task-family ID vs cross-entity 引用（FIX-171 的 _is_task_family_id 先例）

### FIX-226: task-priority-analysis 工具
- 新增 verify_workflow 子命令：解析 plan-tracker 依赖列→构建 DAG→计算 blocked/unblocked→输出推荐下一步
- 纯读函数，不修改状态

### FIX-227: 行为协议升级
- 修改 interaction-boundary.md:217 + behavior-protocol.md M7.4 step 6
- 从"取最高优先级未完成"改为"运行 task-priority-analysis→推荐最合理下一步→AskUserQuestion 呈现"

### FIX-228: 变更控制实质化
- 将 2 行 stub 升级为可执行步骤：新任务插入前 MUST 运行依赖/冲突/优先级分析

### FIX-229: change-impact-checklist 扩展
- 增加"任务级依赖/冲突"检查维度（不只是代码级）
