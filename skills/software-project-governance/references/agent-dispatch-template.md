# Agent 调度模板

Coordinator spawn sub-agent 时 MUST 使用本模板，**禁止**传自定义 prompt。只能填充模板中的 `{placeholder}` 占位符。模板只传递角色、任务、范围、验收和硬门槛，不传递昵称、人设、风格或口号。

## 模板

```
## 任务：{task_id} — {task_summary}

你是 {agent_role} Agent。在执行任务前，MUST 先加载两个文件：

1. 角色定义：`{role_definition_path}`——理解你的职责边界、工具权限、硬门槛和输出格式
2. 任务规范：`{task_skill_path}`——理解确定性执行步骤

## 任务上下文

- **Task ID**: {task_id}
- **描述**: {task_description}
- **修改文件**: {file_list}
- **验收标准**: {acceptance_criteria}
- **优先级**: {priority}

## 硬门槛（执行前自检）

{hard_gates}

## 破坏性红线（真实环境任务 MUST 生效——AUDIT-146 / FIX-271 R3）

{destructive_redlines}

## 并发锁操作（Coordinator — spawn 前 MUST 执行）

Coordinator dispatch Agent 前 **MUST** 按 behavior-protocol.md M7.6a 执行锁检查与获取：

1. **读取** `.governance/agent-locks.json`
2. **任务去重检查**：`active_tasks` 中是否已有 `{task_id}` 键
   - 不存在 → 继续
   - 已存在 → 按 M7.6a 三步协议处理（等待 → 报告用户 → 强制重试）
3. **文件锁检查**：对 `{file_list}` 中的每个文件，检查 `file_locks` 中是否有其他 task 的锁
   - 无冲突 → 继续
   - 有冲突 → 启用 worktree 隔离或串行化
4. **获取锁**：写入 `active_tasks["{task_id}"]` + 每个目标文件的 `file_locks` 条目 → 保存 `agent-locks.json`
5. **Spawn Agent**

## Coordinator 锁释放（Agent 完成后 MUST 执行）

Agent 返回结果后，Coordinator **MUST** 立即：

1. 从 `active_tasks` 中移除 `{task_id}` 条目
2. 从 `file_locks` 中移除该 task 持有的所有文件锁条目
3. 保存 `agent-locks.json`

## 审查结论持久化（Coordinator — Reviewer 返回结论后 MUST 执行）

Reviewer sub-agent 返回审查结论后，Coordinator **MUST** 先通过机器路径持久化结论再进入后续触发器判定（FIX-260/REQ-107，behavior-protocol.md M7.4 step 4.6 C8）：

```
python skills/software-project-governance/infra/verify_workflow.py review-record \
  --task {task_id} --round {n} \
  --result {APPROVED|APPROVED_WITH_NOTES|NEEDS_CHANGE|BLOCKED} \
  --report {reviewer报告路径} --reviewer {reviewer角色}
```

- `review-{task}-R{n}.md` 文件与 evidence 行由 CLI 机器写入（唯一路径）；NEEDS_CHANGE 时 CLI 自动产出 `next_round`/`prev_report` 复审义务字段（跨会话可从证据直接推导待复审项）
- 禁止手写 `REVIEW-{id}` 证据行替代（M1.2 快速通道对 REVIEW 行已收窄）；Check 30c 对无机器来源标记的 REVIEW 记录与缺 `next_round` 的 NEEDS_CHANGE 记录 WARN（渐进 FAIL，ADR-017 R1 N1）
- CLI 失败 → fail-closed：修复环境后重试，不得降级为手写

## 执行流程

1. 加载角色定义和任务规范
2. 通读目标文件，理解现有结构
3. 执行修改
4. 自检硬门槛
5. 返回结构化结果给 Coordinator

## 禁止事项

- 不修改非目标文件（"顺带改"）
- 不直接与用户交互（无 AskUserQuestion）
- 不修改 .governance/ 治理记录（唯一例外：派发 prompt 预授权 incidents 留痕文件时，可向 `.governance/incidents/{task_id}-*.log` 追加 R4 实时命令日志——仅限该路径、仅限追加，见 behavior-protocol.md M7.7 R4 例外条款）
- 不做最终决策（决策型任务只出方案）
- 不把昵称、人设、风格或口号作为执行依据
```

## Coordinator 可填充的占位符

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{task_id}` | 任务 ID | SYSGAP-030 |
| `{task_summary}` | 一句话任务摘要 | 路由表 1:1→1:N 升级 |
| `{agent_role}` | 角色名（英文） | Developer |
| `{role_definition_path}` | 角色定义文件路径 | agents/developer.md |
| `{task_skill_path}` | 任务 SKILL 文件路径 | skills/stage-development/SKILL.md |
| `{task_description}` | 任务详细描述 | 修改 SKILL.md 路由表... |
| `{file_list}` | 要修改的文件列表 | skills/software-project-governance/SKILL.md |
| `{acceptance_criteria}` | 验收标准 | 路由表含后置审查列，表格格式正确 |
| `{priority}` | 优先级 | P0 |
| `{hard_gates}` | 硬门槛列表 | verify_workflow.py PASSED, cross-reference consistency PASSED |
| `{destructive_redlines}` | 破坏性红线段——任务涉及用户真实环境操作时 MUST 填入下方「红线捆绑包」（红线原文 + R1/R4 配套摘要）逐字文本；纯仓库内任务填「不适用——本任务无用户真实环境操作」 | 见下方「破坏性红线注入（真实环境任务）」 |

## 破坏性红线注入（真实环境任务 — AUDIT-146 / FIX-271 R3）

**注入时机（MUST 判定）**：任务满足以下任一条件时，Coordinator **MUST** 将「红线捆绑包」逐字填入模板的 `{destructive_redlines}` 占位符——捆绑包为下方固定文本，**不得改写、不得省略、不得转述、不得拆分**（红线原文源自 RCA §7.2 R3；配套规则为 behavior-protocol.md M7.7 R1/R4 的注入摘要，权威文本以 M7.7 为准）：

1. 任务 `files` 含仓库外路径（`$HOME`/`$DSH_HOME` 下配置目录、绝对路径、环境变量重定向目标）；或
2. 任务验收/描述要求在用户真实环境执行操作（安装、写入、清理、验证用户 HOME 下配置）；或
3. change-triage 第五步（`analysis.side_effect`）判定 `touches_real_env=true`。

纯仓库内任务（以上皆不满足）填「不适用——本任务无用户真实环境操作」——占位符 MUST 总是被显式填充，不得留空。

**红线捆绑包（verbatim——`{destructive_redlines}` 的唯一合法填充值，随派发 prompt 进入角色 agent 上下文）**：

```
【破坏性红线】禁止对用户 HOME 下任何配置目录执行删除/清空/重建/移动；构造测试场景一律使用临时目录；对用户环境的全部写操作限制为安装目标自身的追加式写入。

【配套规则 R1——真实环境三选一】任何涉及用户真实环境（$HOME 下配置目录、$DSH_HOME、仓库外任意路径）的测试/验收/安装操作，执行前必须满足三选一并留痕：(a) 隔离环境——环境变量重定向至临时目录（如 DSH_HOME=<tempdir>）；(b) 事先完整备份 + 操作后一致性校验；(c) 用户经 ask_user_question 逐项授权。三者皆缺禁止执行，无豁免。

【配套规则 R4——真实环境命令逐条上报】你在用户真实环境执行的每条命令必须在结构化返回中逐条上报（命令、时间、退出码、影响路径），由 Coordinator 于收到当下机写 evidence 行留痕；无上报的真实环境操作按违规处理。仅当本派发 prompt 预授权 incidents 留痕文件（.governance/incidents/{task_id}-*.log）时，方可向该文件追加实时命令日志（仅限该路径、仅限追加）——这是「不修改 .governance/ 治理记录」禁令的唯一例外。
```

注入纪律（Coordinator 侧）：

- 真实环境任务漏填捆绑包 = 调度违规（R3 注入是 MUST，不是可选）
- 捆绑包内「破坏性红线」三句与 RCA §7.2 R3 逐字一致——单一权威副本，修改须经决策记录
- 配套规则为 M7.7 注入摘要：摘要与 M7.7 权威文本不一致时以 M7.7 为准并回改摘要（防文本漂移）

## 并行调度安全

Coordinator 在并行 spawn 多个 agent 前 **MUST** 校验：任意两个 agent 的任务所涉及的文件修改目标无重叠。如两个 agent 都要修改同一文件路径 -> **MUST** 优先使用 `isolation: "worktree"` 物理隔离（见下方 Worktree 隔离参数）；不可用时回退为串行执行。仅读取文件（不修改）的 agent 之间无冲突风险——可安全并行。详见 `references/behavior-protocol.md` M7.6。

### Worktree 隔离参数

当并行 agent 文件修改目标重叠时，Coordinator MUST 在 Agent 工具调用中设置 `isolation: "worktree"`。此参数为 Agent 平台原生支持：

- **效果**: agent 在独立 git worktree 中执行，物理隔离文件系统
- **清理**: 无修改时自动清理 worktree；有修改时 Agent 工具结果中返回 worktree 路径和分支，供 Coordinator 后续处理
- **使用**: 仅对修改文件的 agent 使用；只读 agent（如 Reviewer）不需要

## 平台兼容性

当 plugin-namespaced agent type 不可用时，使用以下降级模板：

```
Agent(
  subagent_type="general-purpose",
  prompt="你是 {agent_role} Agent。在执行任务前，MUST 先加载两个文件：\n\n1. 角色定义：{role_definition_path}\n2. 任务规范：{task_skill_path}\n\n## 任务：{task_id} — {task_summary}\n\n[填充模板其余部分...]"
)
```

已验证：`general-purpose` agent 可成功 spawn 并完成任务（0.28.0 全部任务使用此方式）。

## 进度通知（FIX-039）

Coordinator spawn sub-agent 时 MUST 在用户可见输出中报告进度：

```
>> 派发 {agent_role} 执行 {TASK_ID}: {简短描述}...
```

完成后报告结果：

```
✅ {TASK_ID} 完成——{agent_role}: {关键成果摘要}
```

禁止静默 spawn——即 spawn agent 后不在用户侧输出任何进度信息。

## Coordinator 不得做的事

- ❌ 传自定义 prompt 替代模板
- ❌ 在模板外追加额外指令
- ❌ 修改模板结构
- ❌ 跳过角色定义或任务 SKILL 的加载指令
- ❌ 在未预检文件目标重叠的情况下并行 spawn 多个修改 agent
- ❌ 真实环境任务派发时漏填破坏性红线段（R3 注入是 MUST——见「破坏性红线注入」）
