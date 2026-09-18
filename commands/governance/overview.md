# /governance 概览：三方分工 · Web console · 自动化分级 · 文件变更清单

> FEAT-038 拆分自路由层（逐字搬移，零语义丢失）——「与 Bootstrap / SKILL.md 的分工」节、其中的 Web console 入口边界、「设计原则」节中的自动化能力分级声明、Coordinator 激活节的完整边界表 / Agent Team 路由表 / Sub-agent 调度 / 交互规则，以及「现有命令路由」与「文件变更清单」节。
> 本文件不在默认注入面——需要这几块说明、边界表、路由表、调度与交互规约全文时按需 Read。

## 与 Bootstrap / SKILL.md 的分工

三者各司其职，互不替代：

| 组件 | 触发时机 | 职责 |
|------|---------|------|
| **CLAUDE.md bootstrap** | 每次 session 自动 | "开机自检"——读 plan-tracker、SELF-CHECK、干活/收工纪律、版本升级检测 |
| **SKILL.md（插件自动加载）** | 每次 session 自动 | 注入 Coordinator 身份 + 铁律 + 完整路由表——agent 后台自动成为 Coordinator |
| **`/governance`（本命令）** | 用户手动输入 | "仪表盘"——Coordinator 激活 + 场景检测 + 用户交互（init/status/recovery/upgrade/diagnose） |

**关键原则**：
- Bootstrap 是"最小存活检查"——不依赖 SKILL.md，必定生效
- SKILL.md 是"完整 Coordinator 注入"——后台自动，用户无感
- `/governance` 是"用户按钮"——需要交互时用户主动使用，同时也是 Coordinator 激活的兜底（安装后首次 session 中途使用）
- `/governance` SHOULD 默认启动或复用本地 Web console，让用户后续可以用 Web UI 查看状态并继续交互；启动入口必须 fail-closed，端口被非 SPG 服务占用时不得误识别

### Web console 入口边界

Web console 是可选的本地伴随状态面板，也是用户手动 `/governance` 后的默认可视化入口。

> 路径约定：以下 `web-console` 命令中的 `<plugin_home>` 由 `resolve_entry.py` 提供（DEC-096）。`/governance` 的第一动作是运行 `python <plugin_home>/infra/resolve_entry.py --json`；`resolved_root_ok=false` 时 MUST STOP 并展示 diagnostic，不启动 Web console。

- 手动执行 `/governance` 时，SHOULD 运行 `python <plugin_home>/infra/verify_workflow.py web-console --governance-entry`，启动或复用本地 Web console，并把 URL 输出给用户。
- 如果 Web console 已运行，`/governance` 复用已有服务，不重复启动。
- 如果端口被非 SPG 服务占用，MUST fail-closed 并提示换端口，不能把其它服务当成治理 Web UI。
- 如果首次使用且缺少 `web/node_modules`，MUST 告知一次性命令 `python <plugin_home>/infra/verify_workflow.py web-console --start --install`；不得在没有明确安装路径的情况下伪装为已启动。
- 阶段性任务完成、工作单元收尾或 session 总结之后，MAY 在总结末尾追加一个只读 Web console 入口。
- 追加入口时优先运行 `python <plugin_home>/infra/verify_workflow.py web-console --summary-link`；该命令只报告本地 URL、未运行状态或手动启动命令，不启动服务。
- 如果 Web console 已运行，总结末尾显示：`Web console: http://127.0.0.1:5173/ (optional local companion dashboard)`。
- 如果 Web console 未运行，总结末尾显示：`Web console: not running. Manual start command: python <plugin_home>/infra/verify_workflow.py web-console --start`。
- Summary footer 仍然只读；不得把 `--summary-link` 和启动路径混用。

---

### 自动化能力分级声明（plugin-contract.md L114）

本命令对「自动/看护」的承诺按 plugin-contract.md 三级划分；**禁止用笼统的「自动」一词同时指向 A 级与 C 级能力**（plugin-contract.md L114 禁令——README 和对外文档必须显式说明当前各项能力处于哪一级）：

- **A 级（Agent Protocol Automation）**：行为协议自动化——agent 按协议纪律自动执行（本命令激活 Coordinator 后按场景规则自动推进 = A 级）。
- **B 级（CLI-Enforced Automation）**：CLI/脚本在命令/commit 时点强制——`verify_workflow.py check-governance`、`status` 与 git hooks（= B 级）；上方设计原则 1「自动分类，不问用户」属本级（命令时点，事件驱动、非持续）。
- **C 级（System Automation）**：后台系统自动触发、不依赖 agent 记忆——**未实现**（plugin-contract.md L102：MCP/headless runner 仅有协议样例，无可用实现）。

**当前治理自动级别 = A 级 + B 级；C 级为 roadmap（未实现）**。完整分级声明与对外宣示口径见 `skills/software-project-governance/SKILL.md`「自动化能力分级声明」。

---

## 文件变更清单

### 新增
- `/governance` 路由层（原「本文件」——拆分后本清单随概览移入，路由层为 `/governance` 命令入口）

### 修改
- `skills/software-project-governance/SKILL.md` M3 节——将 `/governance-init` 引用更新为 `/governance`
- `commands/governance-init.md`——添加路由说明
- `commands/governance-status.md`——添加路由说明
- `commands/governance-verify.md`——添加路由说明
- `commands/governance-update.md`——标记为 DEPRECATED，路由到统一命令

### 不变
- `skills/software-project-governance/core/onboarding.md`——Scenario B 的参考协议
- `"<plugin_home>/infra/verify_workflow.py"`——Scenario E 的诊断引擎（`<plugin_home>` 来自 `resolve_entry.py`，先 resolve 后 verify）

---

## 产品代码 vs 治理记录边界（完整表）

> FEAT-038 拆分自路由层「Coordinator 激活」节（逐字搬移）。

### 产品代码 vs 治理记录边界

| 类型 | 路径模式 | 操作权限 |
|------|---------|---------|
| **产品代码** | `skills/**` `agents/**` `commands/**` `adapters/**` `infra/**` `.claude-plugin/**` `.codex-plugin/**` `.agents/**` | MUST spawn Agent Team |
| **治理记录** | `.governance/**` `docs/**` `project/CHANGELOG.md` `project/references/**` | Coordinator 可直接写入 |

判定依据是文件路径，不是修改复杂度。改一行 Python 和改一百行 Markdown 都是产品代码。

---

## Agent Team 路由表（完整版——核心 9 条）

> FEAT-038 拆分自路由层「Coordinator 激活」节（逐字搬移）。

### Agent Team 路由表（核心 9 条）

| 任务类型 | 执行 Agent | 后置审查 |
|---------|-----------|---------|
| Debug/修 Bug | Developer + Maintenance | Code Reviewer |
| 新功能/产品代码修改 | Developer | Code Reviewer |
| 治理基础设施/工作流本体修改 | Governance Developer | Code Reviewer 或 Design Reviewer |
| 架构/选型/设计 | Architect | Design Reviewer |
| 需求分析/调研 | Analyst | Requirement Reviewer |
| 测试设计/执行 | QA | Test Reviewer |
| 发布管理/版本规划 | Release | Release Reviewer |
| CI/部署 | DevOps | — |
| 复盘/维护 | Maintenance | Retro Reviewer（如涉及规则变更） |

完整路由表（19 行）见 `skills/software-project-governance/SKILL.md`。

---

## Sub-agent 调度（完整说明）

> FEAT-038 拆分自路由层「Coordinator 激活」节（逐字搬移）。

### Sub-agent 调度

使用 Agent 工具 spawn 子 agent。每个子 agent 必须指定 `subagent_type` 为对应的 plugin namespaced agent type（如 `software-project-governance:software-project-governance-developer`）。如 plugin agent type 不可用，降级为 `general-purpose` + 角色定义 prompt。

详细调度模板见 `skills/software-project-governance/references/agent-dispatch-template.md`。

---

## 交互规则（完整版）

> FEAT-038 拆分自路由层「Coordinator 激活」节（逐字搬移）。

### 交互规则

- **AskUserQuestion 是唯一合法用户提问方式**——MUST NOT 内联文字提问
- **关键决策永远停下来**：范围变更/架构决策/发布决策/风险接受/外部依赖变更/模式变更/阶段跳跃
- **非关键决策自动执行**：任务排序/证据格式/git commit/治理记录更新/实现细节/Gate 自评(通过时)
- **M7.4 任务完成协议**：完成 → evidence → check-governance → audit → 再开新任务
- **M7.5 先入账再动手**：任何新任务 MUST 先出现在 plan-tracker 中
- **健康摘要输出契约（FIX-278 G1）**：`check-governance --summary-only` 默认（standard）输出 = 汇总行 + 首个 FAIL/WARN + 最多 5 条明细（FAIL 优先，每条截断 130 字符）+「共 N issues，--level strict 查看全部」指引行——模型无需再自行跑完整 check 追查（audit-148 §2.1：103 字符摘要 → ≈25KB 追查链，10× 放大）
- **治理文件读取编码（FIX-278 G4/F）**：pwsh 读取 `.governance` 治理文件 MUST 显式 UTF-8——`Get-Content -Encoding UTF8`（或 `[System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8)`）；禁止裸 `Get-Content`——Windows 默认 ANSI/GBK 解码会产生 mojibake（AUDIT-147 D6 / AUDIT-148 §4.3 乱码实证：裸 `-Tail 30` 读 evidence-log 22KB 大面积乱码）

---

## 现有命令路由（完整表）

> FEAT-038 拆分自路由层（逐字搬移）。

## 现有命令路由

旧 5 个命令保留为快捷方式，路由到统一入口：

| 旧命令 | 等价场景 |
|--------|---------|
| `/governance-init` | 手动触发 Scenario A 或 B |
| `/governance-status` | 手动触发 Scenario F |
| `/governance-gate` | 独立 Gate 检查（保留为快捷方式，不路由） |
| `/governance-verify` | 触发 Scenario E 诊断 |
| `/governance-update` | 手动触发 Scenario C |
