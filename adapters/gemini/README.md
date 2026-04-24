# Gemini Adapter

本文件作为 `OPS-001` 的正式输出，用于定义 `software-project-governance` workflow 在 Gemini 与后续国内 agent CLI 场景下的兼容路线、接入顺序与边界约束。

## 当前定位

当前阶段仍不直接实现完整 Gemini 适配，而是先形成一份可执行的兼容路线，确保后续扩展继续遵守 `PLAN-003` 的三层结构：

- 运行时本体层在 `skills/software-project-governance/`，设计时资产在 `workflows/software-project-governance/`
- Gemini / 国内 agent CLI 只提供最薄投影层
- 默认优先复用外部能力层，而不是先做 repo-local 入口

## 兼容要求

后续适配 Gemini 或其他 agent CLI 时，应继续复用以下公共资产：

- `protocol/workflow-schema.md`
- `protocol/plugin-contract.md`
- `workflows/software-project-governance/manifest.md`
- `skills/software-project-governance/references/*`（运行时规则）
- `skills/software-project-governance/stages/*`（子工作流和 skills）
- `workflows/software-project-governance/templates/*`（设计时模板）
- `.governance/*`（活跃治理记录，项目级事实源）
- `workflows/software-project-governance/research/agent-integration-models.md`
- `workflows/software-project-governance/research/default-product-shape.md`

## Gemini 路线判断

结合 `RESEARCH-001` 的调研结论，Gemini 当前最值得优先投入的承载面是：

1. MCP
   - 适合承载结构化工具、外部事实源、统一验证和 workflow runner。
2. custom commands
   - 适合包装显式触发的治理动作，如阶段检查、Gate 校验、状态回写入口。
3. headless runner
   - 适合自动化、CI、批处理和外部编排。
4. `GEMINI.md` 最薄投影
   - 只作为项目级上下文指针，不承载完整 workflow 本体。
5. extensions
   - 作为后续产品化分发的观察方向，但在当前阶段不抢跑深做。

## 默认接入顺序

Gemini 兼容路线按以下顺序推进：

1. 外部能力层优先
   - 优先验证 MCP / custom commands / headless runner 的组合。
2. 最薄项目投影
   - 如需要项目内显式绑定，仅保留 `GEMINI.md` 这类上下文指针，并指向 workflow 本体。
3. 探索性样例
   - `adapters/gemini/README.md` 继续作为对齐边界、记录约束和调试假设的样例入口。
4. 延后重实现
   - 在没有更多官方稳定能力依据前，不新增 repo-local Gemini 专有目录结构。

## 国内 agent CLI 兼容抽象

国内 agent CLI 后续兼容优先复用 Gemini 抽象，而不是单独再开一套协议：

- 外部能力层：优先走 MCP、external runner、shared command
- 投影层：仅保留项目级上下文说明或命令指针
- workflow 本体层：继续共用同一套规则、模板、样例和验证脚本

需要重点观察的差异：

- 是否支持 MCP 或兼容的 tool server 协议
- 是否支持 custom commands / slash commands / workflow command
- 是否支持 headless 执行、JSON 输出或 CI 编排
- 是否要求额外的上下文文件或本地配置入口

## 适配原则

- 不复制第二套流程规则。
- 不复制第二套计划事实源。
- 只在 adapter 层解释如何消费已有 workflow 资产。
- 外部能力层优先于 repo-local 入口。
- 项目级入口只做最薄投影，不把 `GEMINI.md` 一类文件扩张为完整 workflow 容器。
- 兼容路线先于实现落地，避免在能力边界未稳定前过早绑定目录结构。

## 建议的最小验证顺序

1. 先定义一个 Gemini 可调用的 external runner / command 验证样例，确认读取顺序与校验动作能否稳定表达。
2. 再评估 MCP 是否适合承载结构化 Gate 检查、样例回写和验证能力。
3. 如需项目级显式绑定，再补最薄 `GEMINI.md` 投影样例。
4. 国内 agent CLI 后续沿相同顺序评估，不单独发明第二套产品形态。

## 当前不做

- 不直接新增 Gemini repo-local skill 目录。
- 不在缺少官方稳定依据时定义统一 plugin market 分发方案。
- 不为 Gemini 或国内 agent CLI 维护独立的计划、证据、决策、风险记录。

## TODO

- 为 Gemini 设计第一个最小可运行的 external runner / command 验证样例。
- 在 `MAINT-003` 中把国内 agent CLI 的差异收敛成更细的兼容约束说明。
- 待官方 extension 机制进一步稳定后，再判断是否值得新增产品化分发层。