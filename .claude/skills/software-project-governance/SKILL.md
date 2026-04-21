---
name: software-project-governance
description: 在软件项目治理相关任务中加载统一 workflow 规则、模板、Gate 和事实源，并将结果写回当前项目样例。
---

# Software Project Governance

当任务涉及软件项目治理 workflow 的规划、设计、验证、演进或样例记录维护时，使用本 skill。

## Use this skill when

- 需要修改 `protocol/`、`workflows/`、`adapters/`、`scripts/` 下的 workflow 资产
- 需要推进或复盘当前项目样例中的任务状态
- 需要检查 Gate 是否允许阶段推进
- 需要补证据、决策、风险记录，保证过程可信

## Required read order

在开始执行前，按以下顺序读取并理解：

1. `workflows/software-project-governance/manifest.md`
2. `protocol/workflow-schema.md`
3. `protocol/plugin-contract.md`
4. `workflows/software-project-governance/rules/lifecycle.md`
5. `workflows/software-project-governance/rules/stage-gates.md`
6. `workflows/software-project-governance/templates/plan-tracker.md`
7. `workflows/software-project-governance/templates/evidence-log.md`
8. `workflows/software-project-governance/templates/decision-log.md`
9. `workflows/software-project-governance/templates/risk-log.md`
10. `workflows/software-project-governance/examples/current-project-sample.md`

## Output rules

所有与当前项目样例有关的结果只允许写回以下事实源：

- `workflows/software-project-governance/examples/current-project-sample.md`
- `workflows/software-project-governance/examples/current-project-evidence-log.md`
- `workflows/software-project-governance/examples/current-project-decision-log.md`
- `workflows/software-project-governance/examples/current-project-risk-log.md`

不要为 Claude 额外创建第二套项目状态文件。

## Gate behavior

- 如果 Gate 未通过，不得声称进入下一阶段。
- 如果发现偏差或阻塞，必须更新风险记录或决策记录。
- 所有已完成事项必须补证据。

## Execution principle

**核心原则：用户负责思考，工作流负责执行。只在真正需要用户判断时停下，其余全自动推进。**

### 何时停下

仅在以下场景才暂停执行，通过 AskUserQuestion 等待用户：
1. **方向性决策**：有多条可行路线，需要用户选择（如"先做A还是先做B"）
2. **需求澄清**：任务描述模糊，存在多种理解，需要用户确认意图
3. **质量把关**：产出物需要用户审核确认后才能继续（如架构方案、技术选型）

### 何时不停

以下场景**不要停下**，直接执行：
- 任务已经通过 AskUserQuestion 确认了方向 → 直接按确认的方向执行到底
- 治理记录更新（决策、证据、风险）→ 做完主要工作后一次性补齐
- Gate 检查 → 自行判定，只在未通过时才告知用户
- 校验脚本运行 → 自行运行，只在失败时才告知用户
- git 全部操作（status / diff / log / add / commit / branch / checkout）→ 自行执行，不打断用户
- 文件创建、编辑、目录创建 → 直接执行
- 完成一个任务后 → 直接继续下一个最高优先级任务，不停下来问"接下来做什么"
- 复盘或审视发现问题 → **立即修复，不等下一轮**
- 远程仓库推送等需要外部配置的操作 → 记录为待办，不阻塞其他任务

### 反打断模式（基于实际执行中观察到的问题）

以下行为模式已被识别为**错误的中断**，必须避免：
1. **完成一项任务后停下来请示下一步** — 错误。用户已给方向，执行到下一个真正需要判断的节点。
2. **复盘产出改进项后停下来** — 错误。改进项中的可立即执行的修复应立即执行。
3. **推送远程失败后停下来** — 错误。记录为待办，继续执行其他任务。
4. **治理记录补齐后停下来展示结果** — 错误。治理记录是过程产出，不是需要用户确认的决策。
5. **两个紧密关联任务之间停下来** — 错误。如 DESIGN-012 完成后需要更新 verify_workflow.py 和治理记录，一气呵成。

### 连续执行模式

当用户通过 AskUserQuestion 确认了方向后，工作流应连续执行后续所有依赖任务，直到：
- 遇到下一个需要用户判断的节点
- 当前会话的上下文即将耗尽
- 用户主动中断

不要在两个紧密关联的任务之间停下来"请示"——用户已经给了方向，就执行到底。

### 实时闭环规则

**复盘或执行过程中发现的流程/体验问题，属于 P0 高价值改进，必须立即修复，不能记到"改进计划"等下次。**

具体执行方式：
1. 发现问题 → 记录到决策/风险日志（这是什么问题）
2. 立即修复 → 修改 SKILL.md、交互边界规则或其他相关文件
3. 补证据 → 写入证据日志（修复了什么、改了哪些文件）
4. 继续推进 → 不因修复过程打断主任务流

这条规则的底层逻辑：**样本项目中实时发现的问题就是最高价值的用户体验反馈。用户正在体验工作流的执行质量，每一处卡顿都是真实痛点。记到改进计划里等下次 = 把用户的痛感延后到不确定的未来。**

## Session lifecycle

### 会话开始时

1. 读取 `examples/current-project-sample.md` 的项目配置和 Gate 状态跟踪
2. 确认当前阶段、最近 Gate 结论、活跃风险数
3. 如果有遗留项（passed-with-conditions 的未关闭项），优先处理

### 会话结束时

每个会话在完成主要工作后，必须输出**会话状态总结**和**后续建议**。

#### 会话状态总结（纯文本输出）

```
## 会话状态总结

- 本轮完成：[列出本轮完成的事项]
- 治理记录已同步：[决策/证据/风险 是否已补齐]
- 校验结果：verify_workflow.py 通过/未通过
```

#### 后续建议（混合输出：文本 + AskUserQuestion）

后续建议由两部分组成：

**文本部分**（不需要用户判断，直接告知）：
- 下一个最优先事项（从样例跟踪表取最高优先级未开始任务）
- 待关闭的遗留项（passed-with-conditions 的未关闭项）
- 风险提醒（当前打开的高严重级别风险）

**AskUserQuestion 部分**（需要用户判断的问题）：
- 凡是需要用户做选择或判断的问题，必须通过 AskUserQuestion 工具以选项形式呈现
- 每个问题给出 2~4 个选项，每个选项附带简要说明
- 用户只需点击选择，不需要自己组织语言回答
- 如果问题之间有依赖关系，按依赖顺序排列

这个机制的目的是：用户只负责选择和判断，不需要自己组织语言、翻看项目状态或理解上下文。工作流负责整理信息、提炼选项、呈现决策点。

## Validation

在完成 workflow 相关改动后，运行以下命令：

```bash
python scripts/verify_workflow.py
```

如需检查 Claude adapter 的当前加载顺序，可运行：

```bash
python adapters/claude/launch.py
```

## Replacement boundary

当用户替换或移除 Claude 时，遵循以下边界：

### 必须保留（workflow 本体层）

- `protocol/`（通用协议）
- `workflows/software-project-governance/`（manifest、rules、stages、templates、examples、research）
- `scripts/verify_workflow.py`（校验脚本）

### 可以移除（Claude 投影层）

- `CLAUDE.md`（仓库级指针）
- `.claude/skills/software-project-governance/SKILL.md`（本文件）
- `adapters/claude/`（Claude adapter 目录）

### 替换为其他 agent 时

1. 移除上述"可以移除"的文件
2. 按 `adapters/<new-agent>/` 的 README 建立新投影层入口
3. workflow 本体层不需要任何修改
4. 统一事实源（`examples/` 四类文件）不受影响
