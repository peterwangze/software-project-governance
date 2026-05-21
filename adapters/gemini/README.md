# Gemini Adapter

本目录定义 `software-project-governance` workflow 在 Gemini CLI 场景下的最薄投影、运行时验证状态与边界约束。

## 当前定位

当前阶段不复制第二套 workflow 规则，而是提供一组可复跑 adapter 资产：

- `adapters/gemini/adapter-manifest.json`：声明 Gemini CLI 如何消费同一套 workflow 本体。
- `adapters/gemini/launch.py`：输出 read order、native entry、runtime E2E 和 validation 命令。
- `check-agent-adapters --runtime`：在真实 Gemini CLI 环境中验证 `gemini --version` 可执行。
- `gemini-auth-preflight`：在不打印 secret 的前提下检查 Gemini CLI PATH、`gemini --version` 和可识别认证来源。

本机 2026-05-21 验证结果：`gemini --version` 返回 `0.35.3`，目标 cwd 的 Python 治理命令可运行；`gemini-auth-preflight` 当前为 `BLOCKED`，因为本机没有可识别的 `GEMINI_API_KEY`、`GOOGLE_API_KEY`、Vertex、GCA 或 Gemini `settings.json` auth provider/token 类型字段。真实 Gemini agent 用例返回 auth missing/401 语义，因此当前 blocked 是认证缺失，不是 workflow、fixture 或 `GEMINI.md` 投影失败。该结果只证明 Gemini CLI runtime 存在和 adapter contract 可被验证，不代表 Gemini 已通过真实 agent E2E，也不代表 Gemini 已拥有独立 plugin marketplace 分发。

Gemini full E2E 的升级顺序必须是：先让 `python skills/software-project-governance/infra/verify_workflow.py gemini-auth-preflight` 返回 `PASS`，再复跑 `python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent gemini`。只有真实 Gemini agent 在 `project/e2e-test-project` target cwd 读取 `GEMINI.md` thin projection 并返回结构化 E2E 字段后，才能把 `agent_runtime_e2e.status` 和 `full_e2e_verified` 升级为 passed/true。

后续扩展必须继续遵守 `PLAN-003` 的三层结构：

- 运行时本体层在 `skills/software-project-governance/`，设计时资产在 `project/workflows/software-project-governance/`
- Gemini / 国内 agent CLI 只提供最薄投影层
- 默认优先复用外部能力层，而不是先做 repo-local 入口

## 兼容要求

后续适配 Gemini 或其他 agent CLI 时，应继续复用以下公共资产：

- `skills/software-project-governance/core/protocol/workflow-schema.md`
- `skills/software-project-governance/core/protocol/plugin-contract.md`
- `skills/software-project-governance/core/manifest.md`
- `skills/software-project-governance/references/*`（运行时规则）
- `skills/software-project-governance/stages/*`（子工作流和 skills）
- `core/templates/*`（设计时模板）
- `.governance/*`（活跃治理记录，项目级事实源）
- `project/workflows/software-project-governance/research/agent-integration-models.md`
- `project/workflows/software-project-governance/research/default-product-shape.md`

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
3. 最薄 adapter 资产
   - `adapter-manifest.json` + `launch.py` 只声明如何消费已有 workflow 资产，并提供可复跑验证入口。
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

1. 运行 `python adapters/gemini/launch.py`，确认 adapter manifest 可被消费。
2. 运行 `python skills/software-project-governance/infra/verify_workflow.py gemini-auth-preflight`，确认 Gemini CLI 和认证来源均可用。
3. 运行 `python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent gemini`，确认真实 Gemini agent target-cwd E2E 通过。
4. 运行 `python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters --runtime`，确认 adapter contract 和 runtime probe 同步。
5. 再评估 MCP 是否适合承载结构化 Gate 检查、样例回写和验证能力。
6. 如需项目级显式绑定，继续保持最薄 `GEMINI.md` 投影样例。
7. 国内 agent CLI 后续沿相同顺序评估，不单独发明第二套产品形态。

## 当前不做

- 不直接新增 Gemini repo-local skill 目录。
- 不在缺少官方稳定依据时定义统一 plugin market 分发方案。
- 不为 Gemini 或国内 agent CLI 维护独立的计划、证据、决策、风险记录。

## TODO

- 配置 Gemini CLI 认证后，先让 `gemini-auth-preflight` PASS，再复跑真实 agent 用例，把 `agent_runtime_e2e.status` 从 `blocked` 升级为 `passed`。
- 在 `MAINT-003` 中把国内 agent CLI 的差异收敛成更细的兼容约束说明。
- 待官方 extension 机制进一步稳定后，再判断是否值得新增产品化分发层。
