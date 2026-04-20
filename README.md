# Software Project Governance Workflow

> **解放使用本工作流的用户非思考动作。** 让用户专注于对产品、需求、特性和竞争力的思考，其他所有的过程动作和实现由工作流完整看护。

## 项目愿景

本项目的最终目标是：**用户只需要思考，不需要做过程管理。**

具体来说：

- **用户专注思考**：产品方向、需求优先级、特性竞争力、技术取舍——这些需要人做判断的事，交给用户。
- **工作流看护过程**：阶段推进、Gate 检查、证据收集、决策留痕、风险跟踪、记录维护——这些不需要创造力的机械动作，全部由工作流自动完成。
- **过程可信**：所有治理记录可追溯、可复盘、不可伪造。
- **质量可靠**：Gate 门禁确保每个阶段达到质量标准才允许推进。
- **降低 LLM 依赖**：工作流不依赖某个具体 LLM 的能力，用户可以自由选择 Claude、Codex、Gemini 或国内 agent CLI，工作流本体不受影响。

## 快速接入

### 1. 选择 Profile

根据项目规模选择治理强度：

| Profile | 适用场景 | 阶段覆盖 | Gate 强度 |
|---------|---------|---------|----------|
| **lightweight** | 个人项目、探索性项目、MVP | 5 个核心阶段 | 合并 Gate，最小记录 |
| **standard** | 团队项目、正式产品 | 全部 11 个阶段 | 完整 Gate，支持有条件通过 |
| **strict** | 大型项目、合规项目、关键系统 | 全部 11 个阶段 | 增强 Gate，不允许有条件通过 |

详见 [`rules/profiles.md`](workflows/software-project-governance/rules/profiles.md)。

### 2. 中途接入

项目已在进行中？不需要从立项开始。按以下步骤接入：

1. 声明项目当前所处阶段（对照 [`rules/lifecycle.md`](workflows/software-project-governance/rules/lifecycle.md)）
2. 选择 Profile
3. 补齐当前阶段的最小记录
4. 前置阶段标记为 `passed-on-entry`，不需要补齐全部证据
5. 开始工作

详见 [`rules/onboarding.md`](workflows/software-project-governance/rules/onboarding.md)。

### 3. 选择 Agent

本工作流支持多种 coding agent，不绑定任何一个：

| Agent | 默认接入方式 | 状态 |
|-------|------------|------|
| **Claude** | personal skill / plugin skill / MCP | 探索性样例可用 |
| **Codex** | 全局配置 / external skill / MCP | 探索性样例可用 |
| **Gemini** | MCP / custom commands / headless runner | 兼容预研完成 |
| **国内 agent CLI** | external runner / MCP / 最薄投影 | 兼容抽象完成 |

接入方式不影响工作流本体。替换 agent 时，治理记录不受影响。

详见 [`protocol/plugin-contract.md`](protocol/plugin-contract.md)。

### 4. 验证

```bash
python scripts/verify_workflow.py
```

校验工作流资产完整性与一致性。

## 生命周期

工作流覆盖软件项目从立项到维护的 11 个阶段：

```
立项 → 调研 → 技术选型 → 环境搭建 → 架构设计 → 开发实现 → 测试 → 防护网与CI/CD → 版本发布 → 运营 → 维护
```

每个阶段有独立的子工作流，包含进入条件、活动清单、产出物标准和退出条件。用户可以按需使用任意阶段，不强制加载全流程。

详见 [`rules/lifecycle.md`](workflows/software-project-governance/rules/lifecycle.md) 和 [`rules/stage-gates.md`](workflows/software-project-governance/rules/stage-gates.md)。

## 三层架构

```
┌─────────────────────────────────┐
│  项目整体治理层                    │  全流程目标看护、阶段推进、全局 Gate
├─────────────────────────────────┤
│  阶段子工作流层                    │  每阶段独立进入条件、活动、产出、退出条件
├─────────────────────────────────┤
│  具体 skill / script 层           │  单个操作工具（需求澄清、技术评审等）
└─────────────────────────────────┘
```

用户可以：
- 加载整体治理层 → 获得全流程看护能力
- 只加载某个阶段 → 获得该阶段的独立执行能力
- 只加载某个 skill → 获得该具体事务的执行能力

## 仓库结构

```
protocol/                    通用协议层（schema、contract、shared command）
workflows/
  software-project-governance/
    manifest.md              工作流元信息
    rules/                   生命周期、Gate、Profile、中途接入规则
    templates/               计划、证据、决策、风险模板
    examples/                当前项目样例数据（治理记录事实源）
    research/                企业经验调研与产品形态研究
adapters/                    Agent 投影样例（探索性，不代表默认产品形态）
scripts/                     校验脚本
```

治理记录统一写入 `workflows/software-project-governance/examples/`，不同 agent 共享同一事实源。

## 如何更新工作流

### 修改规则

1. 修改 `rules/` 或 `protocol/` 下的对应文件
2. 更新 `scripts/verify_workflow.py` 中的校验片段
3. 运行 `python scripts/verify_workflow.py` 确认通过
4. 更新样例治理记录（决策、证据、风险）

### 新增阶段子工作流

1. 在 `workflows/software-project-governance/stages/<stage-id>/` 下创建 `sub-workflow.md`
2. 定义进入条件、活动清单、产出物标准、退出条件
3. 更新 `rules/lifecycle.md` 和 `rules/stage-gates.md` 中的对应引用
4. 更新校验脚本和样例记录

### 新增 Agent 适配

1. 先确认该 agent 能通过 [`protocol/plugin-contract.md`](protocol/plugin-contract.md) 中的 6 项准入问题
2. 优先选择外部能力层接入（MCP、shared command、headless runner）
3. 确保治理记录写入统一事实源，不维护第二套记录
4. 更新校验脚本覆盖新入口

## 设计原则

1. **低侵入优先**：不把工作流本体复制进用户仓库
2. **可替换**：替换或移除 agent 时不影响工作流本体和治理记录
3. **单一事实源**：不同 agent 共享同一套治理记录，不维护多版本
4. **先调研后实现**：产品形态以调研结论为依据，不拍脑袋
5. **LLM 无关**：工作流本体不依赖某个具体 LLM 的能力或 API

## 关键事实源

以下文件是长期事实源，README 只做导航，不承载完整设计：

- [`protocol/plugin-contract.md`](protocol/plugin-contract.md) — 三层承载模型、准入标准、冲击场景
- [`protocol/external-command-contract.md`](protocol/external-command-contract.md) — shared command 契约
- [`protocol/headless-runner-sample.md`](protocol/headless-runner-sample.md) — headless runner 运行态样例
- [`workflows/software-project-governance/research/default-product-shape.md`](workflows/software-project-governance/research/default-product-shape.md) — 默认产品形态
- [`workflows/software-project-governance/examples/current-project-sample.md`](workflows/software-project-governance/examples/current-project-sample.md) — 当前项目样例
