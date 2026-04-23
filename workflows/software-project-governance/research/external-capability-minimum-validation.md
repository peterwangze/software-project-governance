# 外部能力层最小验证方案

本文件作为 `MAINT-004` 的正式方案文档，用于把 `PLAN-003` 中“优先选择一个外部能力层抓手做最小验证”的要求收敛成当前仓库的下一轮执行基线。

## 目标

本方案解决的问题不是“立刻实现完整 MCP 或 plugin”，而是：

1. 选择一个最低侵入、最容易跨 agent 复用的外部能力层抓手。
2. 定义首轮最小验证只需要证明什么，不提前扩张产品形态。
3. 让 Claude、Codex、Gemini 与国内 agent CLI 后续都能围绕同一验证基线推进。
4. 把验证动作继续约束在统一事实源和 Gate 口径下。

## 为什么先选 external runner / shared command

在当前已确认的外部能力层候选中：

- MCP 结构更强，但需要更多协议与运行时约束，当前仓库还没有正式 service 资产。
- plugin / extension 更贴近产品化分发，但官方能力和分发边界仍在演化。
- headless runner 适合作为自动化补充，但若没有统一命令入口，容易和具体 agent 的调用方式耦合。
- external runner / shared command 最接近“最低可验证闭环”：
  - 能明确读取顺序。
  - 能稳定触发校验命令。
  - 能作为 Claude、Codex、Gemini 与国内 agent CLI 的共同调用面。
  - 不要求先把 workflow 做成用户仓库资产。

因此，首轮最小验证默认先选 `external runner / shared command`，而不是先深做 MCP、plugin/extension 或 repo-local 投影。

## 验证对象

首轮最小验证对象定义为：

1. 一个仓库外部可调用的 workflow command / runner 约定。
2. 该约定至少能表达：
   - workflow 入口名
   - read order
   - write-back targets
   - gate behavior
   - validation command
3. 该约定默认服务于外部能力层，不要求新增用户仓库内规则副本。

## 最小验证范围

首轮最小验证只验证以下四件事：

1. 能否用统一命令入口触发 workflow 读取顺序。
2. 能否把允许回写的事实源限制在 `.governance/` 四类日志。
3. 能否在 Gate 未通过时给出稳定阻断语义。
4. 能否稳定调用 `python scripts/verify_workflow.py` 作为闭环验证。

明确不在首轮最小验证中承诺：

- 完整 MCP server 实现
- plugin market / registry 分发
- 新增 repo-local skill / adapter 目录
- 多 agent 的真实运行时集成细节全部打通

## 默认验证顺序

1. external runner / shared command
   - 先定义统一命令入口和最小输入输出约定。
2. headless verification
   - 再验证该入口是否适合 CI、批处理与自动化调用。
3. MCP 映射评估
   - 评估是否适合把同一命令语义进一步映射为 MCP tool。
4. 最薄投影补充
   - 只有在 agent 明确需要项目级指针时，才补最薄投影样例。

## 命令约定草案

建议的最小命令形态：

- command id: `software-project-governance.run`
- required inputs:
  - `workflow_id`
  - `entry_task`
  - `stage`
- required outputs:
  - `read_order`
  - `write_back_targets`
  - `gate_check`
  - `validation`

命令语义要求：

- `workflow_id` 默认指向 `software-project-governance`
- `entry_task` 用于声明当前要推进的样例任务
- `stage` 用于绑定当前阶段与 Gate 口径
- 输出必须明确禁止新增平行状态文件

## 与现有研究的关系

- `default-product-shape.md` 定义三层结构与默认产品形态。
- `adapters/gemini/README.md` 已确认 Gemini 首轮优先考虑 external runner / custom commands / MCP。
- `domestic-agent-cli-compatibility.md` 已确认国内 agent CLI 默认先评估 external runner / shared command。

因此，`MAINT-004` 不是另起一条线，而是把现有研究结论收敛成第一个可执行验证抓手。

## 成功标准

`MAINT-004` 视为完成，需要同时满足：

1. 有正式文档定义外部能力层首轮最小验证对象。
2. 文档明确为什么优先选择 `external runner / shared command`。
3. 样例、证据、决策、风险至少各回写一处。
4. 校验脚本已覆盖文档存在性与关键片段。
5. 验证命令通过。

## 当前不做

- 不直接实现真实的 runner 二进制或 service。
- 不为某一个 agent 单独定义专属外部能力层协议。
- 不把最小验证扩张成新的产品目录结构。

## 下一步建议

1. 基于本方案补一个最小 command contract 样例，验证字段是否足够表达 Gate 与回写约束。
2. 再决定这套命令语义更适合先映射到 MCP，还是先映射到 headless automation。
3. 后续所有外部能力层实现都应继续回写 `.governance/` 事实源，而不是另建状态文件。
