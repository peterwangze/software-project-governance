# repo-local 默认主线终止说明

本文件作为 `PLAN-004` 的正式终止说明，用于明确此前以 repo-local 入口为默认主线的方案为何被终止、哪些资产保留、哪些资产降级，以及后续主线如何接管。

## 终止对象

本轮终止的不是“所有 repo-local 入口”，而是以下默认主线假设：

1. 把 workflow 默认做成用户仓库资产。
2. 以 `平台原生入口文件`、`.claude/skills/`、`adapters/codex/*` 这类仓库内入口作为最终用户的主推荐接法。
3. 在缺少主流集成方式调研的前提下，继续沿 repo-local 目录结构扩展更多 agent 入口。

## 终止原因

### 1. 易用性差

repo-local 方案要求用户在目标仓库中引入额外入口文件或目录，导致接入动作重、理解成本高，不符合“低侵入优先”的产品方向。

### 2. 可替换性差

一旦 workflow 深度嵌入用户仓库，用户替换 agent 或替换 workflow 时，需要清理大量项目级资产，破坏可替换性。

### 3. 容易误把投影层当本体层

`平台原生入口文件`、`.claude/skills/`、`adapters/*` 这类入口本质上只是 agent 投影层。若继续把它们当主线推进，会让 workflow 本体和 agent 私有入口混写，损害单一事实源。

### 4. 调研顺序倒置

用户已明确指出，当前问题不在于“仓库内能不能跑”，而在于“这是不是最符合用户利益的主流接法”。因此，必须先完成主流集成方式调研，再决定产品形态。

## 已形成的结论

`RESEARCH-001`、`PLAN-003`、`OPS-001`、`MAINT-003` 已进一步确认：

- workflow 本体应保持独立，继续承载在 `protocol/`、`workflows/`、`scripts/`。
- 默认产品形态应优先走外部能力层与最薄投影层，而不是继续扩 repo-local 入口。
- Gemini 与国内 agent CLI 的兼容路线都应优先复用 external runner、MCP、shared command 等低侵入抽象。

因此，repo-local 方案不再作为产品主线，而是被正式降级。

## 降级后的资产定位

以下资产继续保留，但定位已变化：

- `平台原生入口文件`
  - 保留为仓库级最薄指针，不再承载默认产品形态。
- `.claude/skills/software-project-governance/SKILL.md`
  - 保留为当前仓库内的 project skill 样例。
- `adapters/claude/*`
  - 保留为 Claude 投影样例、调试入口和 contract 对照基线。
- `adapters/codex/*`
  - 保留为 Codex 投影样例、调试入口和 contract 对照基线。
- `adapters/gemini/README.md`
  - 保留为 Gemini 路线说明与兼容占位，而不是默认产品入口。

这些资产的共同定位是：

- 样例
- fallback
- 调试入口
- 对比基线

不再承担“面向最终用户的默认推荐接法”角色。

## 新主线如何接管

repo-local 默认主线终止后，后续演进由以下主线接管：

1. `RESEARCH-001`
   - 先明确 Claude、Codex、Gemini 的真实集成方式。
2. `PLAN-003`
   - 用三层结构和默认接入矩阵重定义产品形态。
3. `OPS-001`
   - 为 Gemini 形成正式兼容路线。
4. `MAINT-003`
   - 为国内 agent CLI 形成统一兼容抽象。
5. 后续外部能力层最小验证
   - 优先选择 external runner、MCP、shared command 作为实现抓手。

## 对后续实施的硬约束

1. 不得再把新增 repo-local 入口包装成“默认产品主线进展”。
2. 新的跨 agent 抽象优先落到 `workflows/software-project-governance/research/` 或协议层，而不是某个单一 adapter。
3. 若确实需要新增 repo-local 入口，必须明确标注其性质是样例、fallback 或团队级显式绑定。
4. 后续任何实现动作都必须引用 `default-product-shape.md` 与相关 research 资产，而不是回退到目录结构驱动。

## 成功标准

`PLAN-004` 视为真正收口，需要同时满足：

1. 有正式终止说明文档。
2. 样例计划中 `PLAN-004` 有明确产出物与状态变化。
3. 证据、决策、风险至少各回写一处，形成治理闭环。
4. 校验脚本已覆盖终止说明文档及关键片段。
5. 验证命令通过。

## 下一步建议

1. 继续推进 `DESIGN-005` 和 `DOC-001`，把 README 与 plugin contract 中仍偏旧主线的表达进一步收敛。
2. 若进入实现验证，优先选 external runner / MCP，而不是新增 repo-local adapter。
3. 保留现有 repo-local 资产作为样例基线，但不要再让它们驱动产品方向。 
