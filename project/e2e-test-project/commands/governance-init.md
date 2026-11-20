# governance-init — 开始第一项可验收的工作

`/governance` 从用户的目标进入本命令。先确定成品、受益者、独立验收操作和稳定的工作单元 ID。已有项目以当前要交付的事务为起点。宿主中已有的用户文件及治理原件应保留。

## 输入与选择

确认项目名、目标、验收条件和本次工作属于哪层。Profile 选择 lightweight、standard 或 strict。触发模式为 always-on、on-demand 或 silent-track，权限为 default-confirm 或 maximum-autonomy。用户已提供的约束直接沿用。运行环境、目标或权限未知时使用 AskUserQuestion 补齐。

### Step 0: 定位项目与已安装技能

复用同次启动、同一项目的结果，否则运行 `python "<plugin_home>/infra/verify_workflow.py" governance-bootstrap --format json`。须成功退出、JSON 有效且 `resolve.resolved_root_ok == true`，否则 MUST STOP 并显示诊断。 Claude 从插件根定位技能，Codex 使用技能文件位置，其他宿主使用已加载的资源根。整个初始化在已确认的宿主根执行。

### Step 1: 创建项目记录

仅为缺失文件从 `<plugin_home>/core/templates/` 创建 `.governance/plan-tracker.md`、`evidence-log.md`、`decision-log.md`、`risk-log.md`。用真实的项目名、目标、Profile、触发模式、权限和安装版本填好配置；清除样例。已经存在的记录按原内容保留。任务表记来源和验收，运行记录由 CLI 写入。

### Step 2: 登记首个工作单元

从宿主根执行 `python "<plugin_home>/infra/verify_workflow.py" loop start --unit <id> --goal "<用户成品目标>" --acceptance "<可复验条件>" --tier <setup|inner|middle|outer>`。若已有父单元或已受理任务，分别传 `--parent <父单元>` 和 `--task <任务编号>`。首次立项指定 `--tier setup --gate G1`；其他单元采用该层入口门。发布单元提供 `--release-version <版本号>`。具体范围见 `core/lifecycle.md`。重复接入先用 `loop status --json` 读取已有单元。损坏或目标冲突时保留原件，报告诊断。

### Step 7: 注入 governance bootstrap 到 agent 入口文件

Claude 选 `CLAUDE.md`，Codex 和读取 AGENTS 指引的宿主选 `AGENTS.md`。当两个文件都不存在，先在宿主根新建所选主入口的空文件；已有入口保留用户原文。安装根含 `commands/governance-init.md` 时，使用 `python "<plugin_home>/infra/sync_entry_projection.py" --project "<宿主根>" --source-root "<插件仓库>" --profile <profile> --primary <主入口>` 只读预览。初始化时加 `--write`，仅处理本节模板管理的段落；单入口使用完整模板，两入口共用同一事实源。独立技能分发场景沿本技能入口读取当前单元。入口、插件升级和对外发布遵守各自授权。

**lightweight profile 注入模板**：
```markdown
## Governance Bootstrap（由 software-project-governance 插件注入）

> @bootstrap-version: 0.99.0

### 每次会话第一动作

复用同次启动、同一项目的结果，否则运行 `python "<plugin_home>/infra/verify_workflow.py" governance-bootstrap --format json`。须成功退出、JSON 有效且 `resolve.resolved_root_ok == true`，否则 MUST STOP 并显示诊断。 仅当旧 CLI 明报未知子命令才用 `resolve_entry.py --json` 定位安装根。根或运行记录无效时停止并显示诊断。 从 `loops` 找到本次目标、单元及父单元、层级、轮次、最新裁决和证据。无单元时从用户的第一项交付登记工作；数据损坏或目标有歧义时保留原件并报告。

always-on 显示本次目标、工作单元、循环层、轮次及尚需的验收或裁决；on-demand 按用户请求展开；silent-track 仅在阻塞、权限边界或风险到期时打断。 从 `project` 读取权限模式。已授权的日常执行沿同一单元继续。关键方向、范围、架构、风险接受及发布决策使用 AskUserQuestion。`health.state="deferred"` 显示「待检查」；会话摘要用 `check-governance --summary-only --scope quick`，实质推进前按主技能执行 full 深检。

### 干活前检查

保留用户原意、可重放的验收条件和责任人。从 `loop status --unit <id> --json` 定位当前尝试。执行、审查按原契约交接；退回则携带失败样本和独立签核义务。需了解原有做法时先试用项目及社区候选。

### 收工前检查

记录工件和独立验收，本轮结论仅对该单元有效。用新进程恢复单元，核对继续、再试或阻塞的原因。完整规则见 `skills/software-project-governance/SKILL.md`。

关键行为契约第 5/6 条（完整规则 SKILL.md「关键行为契约」段）：5. **推荐必标需求源**：推荐与排序呈现逐项标注需求源（用户点名、活性缺陷、机器信号三选一标注），不标即违规；同优先级内 user-named 未闭合时 machine-signal 不得排前（DEC-286(7)）。6. **发现即闭环**：问题在触发点当场闭环（FAIL 即修/发现即改/风险即决/发布即结账）；「登记待以后」=违规；付不起闭环成本的动作不开始（DEC-286）。
关键行为契约第 7~9 条（FEAT-090，完整规则 M7.8）：7. 并行优先派发——独立任务单步批量 spawn，等待期间禁 Start-Sleep/轮询。8. 健康检查事件化——全量深检仅会话首检/推进类动作前/异常三类触发。9. 热路径单源——热数据唯一读取路径 governance-bootstrap，直读热面文件=违规。
关键行为契约第 10 条（FEAT-097）：goal 预算必收口（SKILL.md）。
```

**standard profile 注入模板**：
```markdown
## Governance Bootstrap（强制 — 每次会话第一动作）

> @bootstrap-version: 0.99.0

**SELF-CHECK**：先核实根、工作单元、目标、父子关系、轮次和证据。缺少事实则标为待验证。需要用户取舍时使用 AskUserQuestion。

### Step 0: 确定双维度模式与工作单元

复用同次启动、同一项目的结果，否则运行 `python "<plugin_home>/infra/verify_workflow.py" governance-bootstrap --format json`。须成功退出、JSON 有效且 `resolve.resolved_root_ok == true`，否则 MUST STOP 并显示诊断。 仅当旧 CLI 明报未知子命令才用 `resolve_entry.py --json` 定位安装根。根或运行记录无效时停止并显示诊断。 always-on 显示本次目标、工作单元、循环层、轮次及尚需的验收或裁决；on-demand 按用户请求展开；silent-track 仅在阻塞、权限边界或风险到期时打断。 `project` 确定权限模式。`GOVERNANCE_LEGACY_BEHAVIOR=1` 仅调整性能行为；异常披露、升级确认、真实环境防护、独立复审和 fail-closed 持续有效。

### Step 0.5: Agent Team 激活

协调者按工作单元派发；开发者负责实现，独立审查者负责签核。派发前检查并登记 `.governance/agent-locks.json`，完成后释放。范围、权限和验收随任务交接，完整职责见主技能。

### Step 1: 恢复并推进当前循环

从 `loops` 找到本次目标、单元及父单元、层级、轮次、最新裁决和证据。无单元时从用户的第一项交付登记工作；数据损坏或目标有歧义时保留原件并报告。 只有接收方要求外部交接包时才读 `.governance/execution-packets.json`，其余工作沿用单元的目标与验收。`governance-bootstrap` 的汇总缺面或需复核单件时，运行 `loop status --unit <id> --json`。会话快照仅提供上下文。

### Step 2: 交叉验证

会话摘要采用 `check-governance --summary-only --scope quick`；`health.state="deferred"` 表示待检查。发布、版本变动、治理写回、恢复后的修改前运行 full 全检。核实完成声明所引原件、单元 Gate 对应的同轮回执、逾期风险；归档证据同样有效。收到 NEEDS_CHANGE 后带原样本返工并独立复审；熔断或风险接受交用户裁决。

### Step 3: 交接与退出条件

子单元依据证据收口，父单元独立核实交付条件。相邻任务、其他层或过去轮次的结论不能放行本轮。决策改变方向时在同一授权范围内修订目标并复验。

### Step 4: 优先级确认

从用户目标、当前阻塞、依赖和候选的需求来源选择下一项工作。

关键行为契约第 5/6 条（完整规则 SKILL.md「关键行为契约」段）：5. **推荐必标需求源**：推荐与排序呈现逐项标注需求源（用户点名、活性缺陷、机器信号三选一标注），不标即违规；同优先级内 user-named 未闭合时 machine-signal 不得排前（DEC-286(7)）。6. **发现即闭环**：问题在触发点当场闭环（FAIL 即修/发现即改/风险即决/发布即结账）；「登记待以后」=违规；付不起闭环成本的动作不开始（DEC-286）。
关键行为契约第 7~9 条（FEAT-090，完整规则 M7.8）：7. 并行优先派发——独立任务单步批量 spawn，等待期间禁 Start-Sleep/轮询。8. 健康检查事件化——全量深检仅会话首检/推进类动作前/异常三类触发。9. 热路径单源——热数据唯一读取路径 governance-bootstrap，直读热面文件=违规。
关键行为契约第 10 条（FEAT-097）：goal 预算必收口（SKILL.md）。

## 干活前检查（每次收到任务时）

确认目标、单元、可修改范围、测试入口和责任人；需要探索时以实际输入试用候选。

## 提问规则（强制）

已授权的可逆执行沿当前单元推进。范围、架构、发布、风险接受或外部权限发生变化时使用 AskUserQuestion。

## 收工前检查（session 结束前）

写入实物与独立回执，记录待决问题；从新进程复读该单元并核对快照。按权限模式与用户授权提交结果。

## 详细规则

加载 `skills/software-project-governance/SKILL.md`。根确认、升级确认及归档校验遵循 §B1；升级前沿安装根检查版本、改动及回滚路径。

## 故障排除（Agent 行为异常时）

无依据的完成声明沿原始工件和签核回执复查。无法独立验收时保留未决，详见 §B5。

## 当前项目治理状态快速入口

- `loop status --json` 查看并行工作单元；`.governance/plan-tracker.md` 记录范围及依赖。
- `.governance/evidence-log.md`、`decision-log.md`、`risk-log.md` 分别保存证据、决策与风险。PowerShell 读取治理记录使用 `Get-Content -Encoding UTF8`。
```

**strict profile 注入模板**：
```markdown
### Strict Profile 强制规则

适用的高风险动作由独立审查者检验，P0 完成至少两条独立证据。未解决的阻断不得放行。真实环境操作、风险接受和发布沿各自授权边界办理。
```

**secondary-thin 注入模板**：
```markdown
## Governance Bootstrap（强制 — 每次会话第一动作 · 次要平台入口薄指针）

> @bootstrap-version: 0.99.0

主入口 `{PRIMARY_ENTRY}` 承接完整规则，或加载 `skills/software-project-governance/SKILL.md`。

### 最小存活检查（第一动作）

复用同次启动、同一项目的结果，否则运行 `python "<plugin_home>/infra/verify_workflow.py" governance-bootstrap --format json`。须成功退出、JSON 有效且 `resolve.resolved_root_ok == true`，否则 MUST STOP 并显示诊断。 仅当旧 CLI 明报未知子命令才用 `resolve_entry.py --json` 定位安装根。根或运行记录无效时停止并显示诊断。 从 `loops` 找到本次目标、单元及父单元、层级、轮次、最新裁决和证据。无单元时从用户的第一项交付登记工作；数据损坏或目标有歧义时保留原件并报告。

### SELF-CHECK

核对本轮对象、证据和可执行动作。待用户的关键决策使用 AskUserQuestion。`GOVERNANCE_LEGACY_BEHAVIOR=1` 仅调整性能。always-on 显示本次目标、工作单元、循环层、轮次及尚需的验收或裁决；on-demand 按用户请求展开；silent-track 仅在阻塞、权限边界或风险到期时打断。

### 治理状态快速入口

`.governance/plan-tracker.md` 记录任务来源，`.governance/evidence-log.md` 及归档记录提供回执，当前单元用 `loop status --json` 复读。PowerShell 使用 `Get-Content -Encoding UTF8`。
```

### Step 8: Git 项目的提交保护

已使用 Git 的宿主通过 `git rev-parse --git-path hooks` 定位 hooks 目录。安装 `<plugin_home>/infra/hooks/` 的 `prepare-commit-msg`、`pre-commit`、`commit-msg` 和 `post-commit`，保留可执行权限。命中已有自定义 hook 时保持现有行为，单独协调组合安装。提交前保护任务标识及提交说明，提交后检查证据回执。

### Step 9: 从新进程恢复

运行 `loop status --unit <id> --json` 及 `governance-bootstrap --format json`，核对两者所示目标、层级、首次待验事项及真实证据。说明第一项可执行操作和需要用户决定的边界。
