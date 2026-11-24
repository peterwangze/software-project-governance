# Claude Code 项目指引

## Governance Bootstrap（强制 — 每次会话第一动作）

> @bootstrap-version: 0.101.1

**SELF-CHECK**：先核实根、工作单元、目标、父子关系、轮次和证据。缺少事实则标为待验证。需要用户取舍时使用 AskUserQuestion。

### Step 0: 确定双维度模式与工作单元

复用同次启动、同一项目的结果。首次运行时把 `<plugin_home>` 换成本次宿主技能清单中主技能 `software-project-governance` 的 `SKILL.md` 所在绝对目录；仅给插件包根时取其 `skills/software-project-governance` 子目录。确认技能名和脚本存在，从用户项目根运行 `python "<plugin_home>/infra/verify_workflow.py" governance-bootstrap --format json`。须成功退出、JSON 有效且 `resolve.resolved_root_ok == true`，否则 MUST STOP 并显示诊断。 仅当旧 CLI 明报未知子命令才用 `resolve_entry.py --json` 定位安装根。根或运行记录无效时停止并显示诊断。 always-on 显示本次目标、工作单元、循环层、轮次及尚需的验收或裁决；on-demand 按用户请求展开；silent-track 仅在阻塞、权限边界或风险到期时打断。 `project` 确定权限模式。`GOVERNANCE_LEGACY_BEHAVIOR=1` 仅调整性能行为；异常披露、升级确认、真实环境防护、独立复审和 fail-closed 持续有效。

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
