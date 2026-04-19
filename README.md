# Workflow Plugin Repository

这是一个面向主流 coding agent 的软件项目治理 workflow 资产仓库。

仓库的默认产品方向不是把 workflow 做成用户仓库资产，而是先沉淀可被多 agent 复用的 workflow 本体，再根据不同 agent 的真实能力选择低侵入接入方式。

## 当前目标

当前阶段的主目标已经收敛为四件事：

1. 用统一协议定义 workflow 本体、agent 投影和验证边界。
2. 将大型软件公司的项目管理经验固化为生命周期、Gate、证据、决策、风险等治理规则。
3. 以调研结果为依据，为 Claude、Codex、Gemini 与后续国内 agent CLI 收敛默认产品形态。
4. 将旧的 repo-local 主线降级为样例、fallback 和对比基线，不再把它当成默认推荐接法。

## 默认产品形态

当前仓库以 `workflows/software-project-governance/research/default-product-shape.md` 为默认产品形态事实源，核心结论是：

- 默认采用“三层结构”：workflow 本体层、agent 入口投影层、外部能力层。
- 默认推荐低侵入接法：user/global skill、plugin/extension、MCP、headless command。
- project-local 入口、repo rules、上下文指针文件只属于条件推荐。
- 不再把“把完整 workflow 长期复制进用户仓库”当作默认产品主线。

如果只读一个设计文件，优先读 `workflows/software-project-governance/research/default-product-shape.md`。

## 推荐阅读顺序

为了避免 README 和协议层各说各话，建议按以下顺序理解仓库：

1. `workflows/software-project-governance/manifest.md`
   - 理解 workflow 的目标、支持 agent 与边界。
2. `protocol/workflow-schema.md`
   - 理解通用对象模型与阶段 / Gate 结构。
3. `protocol/plugin-contract.md`
   - 理解三层承载模型、默认接入要求和 skill/plugin 描述要素。
4. `workflows/software-project-governance/research/default-product-shape.md`
   - 理解默认产品形态、分层设计和接入矩阵。
5. `workflows/software-project-governance/research/repo-local-termination-note.md`
   - 理解为什么旧的 repo-local 默认主线被正式终止。
6. `workflows/software-project-governance/research/domestic-agent-cli-compatibility.md`
   - 理解 Gemini 之后的国内 agent CLI 兼容抽象。
7. `workflows/software-project-governance/examples/`
   - 理解当前项目如何回写计划、证据、决策和风险。

## 当前仓库结构

- `protocol/`
  - 通用 schema 与 plugin contract。
- `workflows/software-project-governance/`
  - workflow 本体，包括 manifest、rules、templates、research、examples。
- `adapters/`
  - 探索性投影样例、调试入口或兼容占位，不代表默认产品形态。
- `scripts/`
  - 统一校验脚本与后续自动化抓手。

`adapters/` 是否存在，不决定 workflow 是否成立；真正的长期事实源在 `protocol/`、`workflows/` 和校验脚本。

## 当前接入结论

当前仓库的对外结论已经明确：

- 低侵入优先。
- 调研先于实现。
- 单一事实源优先于 agent 私有目录习惯。
- README 负责路由，不再承载完整设计说明。

具体到各 agent：

- Claude
  - 默认优先考虑 personal skill、plugin skill、MCP。
  - project skill 与仓库级指针只属于条件推荐或样例验证。
- Codex
  - 默认优先考虑全局配置、external skill/plugin、MCP、headless runner。
  - repo rules 或 repo-local adapter 只属于条件推荐或样例验证。
- Gemini
  - 默认优先考虑 MCP、custom commands、headless runner、extensions。
  - repo-local 方案当前不作为默认主线推进。
- 国内 agent CLI
  - 默认优先复用 `external runner / MCP / shared command + 最薄投影` 抽象。

## repo-local 探索性接法

以下入口继续保留，但它们的定位已经明确降级：

- Claude：`CLAUDE.md`、`.claude/skills/software-project-governance/SKILL.md`、`adapters/claude/launch.py`
- Codex：`adapters/codex/adapter-manifest.json`、`adapters/codex/launch.py`
- Gemini：`adapters/gemini/README.md`

这些入口的共同定位是：

- 样例
- fallback
- 调试入口
- 对比基线

它们可以证明“当前仓库内可以运行”，但不能推导出“这就是最终用户的默认最佳接法”。

## 验证

修改 workflow 协议、README 或样例治理记录后，运行：

```bash
python scripts/verify_workflow.py
```

如需查看当前探索性入口的读取顺序和验证方式，可运行：

```bash
python adapters/claude/launch.py
python adapters/codex/launch.py
```

这些命令用于验证样例闭环，不等于默认产品接入方案。

## 当前最重要的事实源

如果需要继续推进本仓库，优先引用以下文件，而不是重新从 README 发明一套说法：

- `protocol/plugin-contract.md`
- `workflows/software-project-governance/research/default-product-shape.md`
- `workflows/software-project-governance/research/repo-local-termination-note.md`
- `workflows/software-project-governance/research/domestic-agent-cli-compatibility.md`
- `workflows/software-project-governance/examples/current-project-sample.md`

README 的职责到这里为止：给出方向、边界和读取顺序，把后续细节交还给正式事实源。