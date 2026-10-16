# Pi Adapter

本目录定义 `software-project-governance` workflow 在 [pi](https://github.com/earendil-works/pi)（`@earendil-works/pi-coding-agent`）上的加载投影、扩展桥接与边界约束。

pi is a Tier 1 loading target. pi natively loads `AGENTS.md` and `CLAUDE.md` context files (no trust gate) and implements the Agent Skills spec: SKILL.md trees are discovered recursively, name/description are injected into the system prompt, full instructions load on demand, and `/skill:name` commands work. The current effective entry is the shared workflow skill:

- native context files: `AGENTS.md`, `CLAUDE.md`（pi 免信任双兼容）
- workflow entry: `skills/software-project-governance/SKILL.md`
- extension bridge: `adapters/pi/extension`（ask_user_question + dispatch_agent 两桥，接线可选）
- runtime records: the target project's `.governance/`

## Load · 加载模型

接线机制 = **settings 路径数组**（用户裁决①：其他用户代价/耦合/影响最小——零包改动、不动版本投影面）。在 `~/.pi/agent/settings.json` 追加（幂等，已存在不重复加；路径数组支持绝对路径，同名冲突 keep-first）：

```json
{
  "skills":     ["D:/AI/agent/claude/coding/project_management_workflow/skills"],
  "prompts":    ["D:/AI/agent/claude/coding/project_management_workflow/commands"],
  "extensions": ["D:/AI/agent/claude/coding/project_management_workflow/adapters/pi/extension"]
}
```

- `skills` 数组挂载工作流 skill 树（主 skill + 25 个子 skill，pi 按需加载正文）；
- `prompts` 数组把 `commands/*.md` 注册为斜杠命令（`/governance` 等；首行标题作 description 的展开语义待冒烟，失败则补 skill-shims 兜底）；
- `extensions` 数组启用治理两桥工具（可选但建议）。单次试用也可用 `pi -e <repo>/adapters/pi/extension`。

加载链：

```text
AGENTS.md / CLAUDE.md (auto-loaded context)
  -> skills/software-project-governance/SKILL.md (native Agent Skills discovery)
```

验证接线：`pi list` 列出注册路径；pi 启动诊断的 Skills/Extensions 列表含 governance 条目。

## Verify

静态 adapter 契约：

```bash
python adapters/pi/launch.py
python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters
```

运行时验证（真实 agent 矩阵）：

```bash
pi --version
python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent pi --timeout 90
```

## Boundary · 能力边界（no-overclaim）

- `ask_user_question`：**degraded**（extension 桥——`adapters/pi/extension` 注册 model-only 工具，经 `ctx.ui` dialog 方法族渲染；tui/rpc 交互模式可用（rpc 经 extension UI 子协议转发）；headless `-p`/`--mode json` 无 UI，工具 fail-fast 返回 `GOV_ASK_USER_HEADLESS` 结构化错误——此时交互边界走外宿主会话）。E2E 验证通过前按 degraded 声明。
- `sub_agent`：**degraded**（extension 桥 `dispatch_agent`——spawn 嵌套 `pi --mode json -p --no-session` 子进程，角色定义经 `--append-system-prompt` 注入、工具经 `--tools` allowlist 收窄；输入语义对齐 `references/agent-dispatch-template.md`。**继承披露（review F-3）**：嵌套子进程同样读取全局 settings 的 extensions 接线，两桥工具会被再次声明——dispatch_agent 默认追加 `--exclude-tools ask_user_question,dispatch_agent` 机器化阻断递归派发）。
- `tool_calling`：**native**（read/bash/powershell/edit/write/grep/find/ls；Windows 原生 powershell）。
- `browser`：**unsupported**（无内置浏览器自动化；pi-web-access 未验证为可声明通道）。
- `mcp`：**degraded**（机制 native，服务器可用性取决于主机配置）。
- `git_hooks`：**native**（仓库级控制，对 pi 驱动的改动同样生效）。
- workflow closure：**degraded**（两桥待 runtime E2E；browser/mcp 依赖主机）。

本适配器不声明 official approval、marketplace approval、universal/full runtime support 或 1.0.0 生产就绪。

## E2E

分层验收（设计 §6，混合口径 = 真实 agent-dir 只读凭证 + `--no-session`，写面 = 0）：

- L0 静态：`python adapters/pi/launch.py` + `check-agent-adapters` + `pi --version` / `pi --help`；
- L1 隔离冒烟：`PI_CODING_AGENT_DIR` 重定向至临时目录后 `pi list`（验收措辞「隔离环境安装冒烟（环境变量重定向至临时目录）通过」）；
- L2 extension 加载探测：`pi -e <repo>/adapters/pi/extension -p "Reply with the word ok only" --no-session --tools read`；
- L3 矩阵：`python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent pi --timeout 90`；ask_user 桥 headless fallback 独立判据（最终输出含 `GOV_ASK_USER_HEADLESS` 且进程正常退出）。

## 资产

- `adapters/pi/adapter-manifest.json`：机器可读的适配器元数据（能力声明 + E2E 证据位）。
- `adapters/pi/launch.py`：只读 launcher（打印 manifest——不做安装器；接线正道 = 本文 Load 段 + Coordinator runbook）。
- `adapters/pi/extension/`：治理两桥 extension（`ask_user_question` + `dispatch_agent`；多文件 extension，pi 经目录 `index.ts` 识别；零 npm 依赖——typebox 由 pi 运行时虚拟化提供）。

## 与其它适配器的差异

- pi 无 plugin marketplace，也无平台 dotfile 包目录（无 `.pi-plugin/` 约定）——接线是 settings 三个路径数组，仓库是唯一事实源。
- 两桥均为 extension 桥（非宿主原生工具）：设计裁定 FEASIBLE（证据链见 `docs/requirements/pi-adapter-design-0.99.0.md`），runtime E2E 通过前 capability 诚实记 degraded。
- 版本锚点：`pi >= 1.1.0`（本机验证 `pi --version` = 1.1.0）；pi 迭代快、机制面无稳定性承诺，E2E 矩阵条目即回归探针。
