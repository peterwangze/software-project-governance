# Codex Adapter

本目录定义 `software-project-governance` workflow 在 Codex CLI 场景下的消费方式。

## 适配目标

让 Codex 类 coding agent 在执行项目任务时，以统一流程资产为约束，避免直接基于临时上下文做局部最优决策。

## Codex 入口约定

建议 Codex 适配入口至少包含以下动作：

1. 读取 workflow manifest：
   - `workflows/software-project-governance/manifest.md`
2. 读取协议层：
   - `protocol/workflow-schema.md`
   - `protocol/plugin-contract.md`
3. 读取规则层：
   - `workflows/software-project-governance/rules/lifecycle.md`
   - `workflows/software-project-governance/rules/stage-gates.md`
4. 读取模板层：
   - `workflows/software-project-governance/templates/plan-tracker.md`
   - `workflows/software-project-governance/templates/evidence-log.md`
   - `workflows/software-project-governance/templates/decision-log.md`
   - `workflows/software-project-governance/templates/risk-log.md`
5. 读取样例：
   - `workflows/software-project-governance/examples/current-project-sample.md`

## Codex 执行要求

- 将 workflow 视为执行任务前的治理约束，而不是事后补文档。
- 更新计划、证据、决策、风险时，必须复用同一套事实源。
- 不同阶段的任务推进必须引用 Gate 规则。
- 校验脚本通过后，才能声称 workflow 资产完整。

## 半可执行入口

当前目录已提供两类可被脚本消费的入口：

- `adapters/codex/adapter-manifest.json`：机器可读的适配器元数据
- `adapters/codex/launch.py`：输出读取顺序、输出目标、Gate 行为和校验命令的 launcher

可通过以下命令查看入口输出：

```bash
python adapters/codex/launch.py
```

## 后续可扩展方向

- 可进一步提供面向 Codex CLI 的命令式入口描述。
- 可补充更结构化的 adapter contract，使 Codex 更容易自动消费 workflow。
