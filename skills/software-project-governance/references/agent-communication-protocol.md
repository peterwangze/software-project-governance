# Agent 通信协议

Coordinator 与角色 Agent 之间的输入/输出契约。

## 原则

1. **文件传递，非上下文传递**：Agent 之间不共享会话上下文——读取 Coordinator 指定的治理文件和项目文件，产出结构化结果
2. **Coordinator 是唯一用户界面**：角色 Agent 不与用户直接交互
3. **显式 I/O 契约**：每个 dispatch 声明输入文件和期望输出
4. **治理写回单口径**：Sub-agent 不直接写 `.governance/plan-tracker.md`、`.governance/evidence-log.md`、`.governance/decision-log.md`、`.governance/risk-log.md`；只返回 proposed entry，由 Coordinator 写回

## Dispatch 格式

Coordinator 使用 Agent 工具 spawn 子 Agent，prompt 从 `agents/<role>.md` 模板构建：

```
Agent(
  description: "{task_id}: {brief}",
  subagent_type: "general-purpose",
  prompt: "[agents/<role>.md 模板] + [具体任务]"
)
```

### 必填字段

| 字段 | 说明 |
|------|------|
| `Task` | task_id + 任务描述 |
| `Input` | 具体文件路径列表 |
| `Output` | 期望产出 + Coordinator 写回目标 |
| `Gate` | 验收标准——可自动判定的检查项 |
| `Dependencies` | 前置任务 ID 列表（无则标 `—`） |
| `ADR References` | 相关架构决策（如适用） |

## 角色 Agent I/O 契约

### Analyst

**Input**:
```
Task: {task_id} — {description}
Problem / Goal: {用户问题、项目目标、成功标准}
Input Files: {plan-tracker、需求材料、调研材料、既有 PR/FAQ/OKR}
Constraints: {范围、时间、用户边界}
Dependencies: {前置 task ID}
```

**Output**:
```
- Requirements / research artifacts (paths)
- Assumptions + validation plan
- Proposed plan-tracker updates (需求/任务/状态建议)
- Proposed evidence / decision / risk entries (if any)
```

**Escalation**: 需求不可判定或需用户取舍 → 返回澄清点给 Coordinator

### Architect

**Input**:
```
Task: {task_id} — {description}
Requirements: {需求文档路径}
Constraints: {技术约束}
Existing ADRs: {已有 ADR}
```

**Output**:
```
- Architecture design doc or ADR draft
- Module decomposition + interface definitions
- Non-functional requirements mapping
- Technical review conclusion
- Proposed decision-log entry
```

**Escalation**: Bar Raiser 否决 → Gate 阻塞，返回解除条件给 Coordinator

### Developer

**Input**:
```
Task: {task_id} — {description}
Input Files: {具体源文件路径}
Acceptance Criteria: {验收标准}
ADR References: {架构 ADR 引用}
Dependencies: {前置 task ID}
```

**Output**:
```
- Modified files + tests
- Validation results: lint/test/coverage/security
- Commit hash if commit was requested and allowed
- Proposed evidence-log entry
```

**Escalation**: 3 次失败 → 停止，质疑方案，升级给 Coordinator

### Governance Developer

**Input**:
```
Task: {task_id} — {governance infrastructure change}
Input Files: {skill / reference / agent / hook / manifest / verify files}
Allowed Scope: {明确可修改文件}
Rule-Check Pairing: {规则变更对应的验证脚本或检查项}
Dependencies: {前置 task ID}
```

**Output**:
```
- Modified governance product files
- Cross-reference / manifest impact summary
- Validation results: verify_workflow 子命令、测试、diff check
- Proposed evidence-log entry
- Proposed decision-log / risk-log entry when rule or risk posture changes
```

**Escalation**: 规则与检查无法同步、权限范围不足、验证三次失败 → 升级给 Coordinator

### QA

**Input**:
```
Task: {task_id} — {test objective}
Test Target: {build、feature、service、workflow}
Requirements / ADRs: {需求与设计依据}
Environment: {测试环境、数据、限制}
```

**Output**:
```
- Test plan / test cases / test report paths
- Defect report with severity + repro steps
- Coverage / performance / security results
- Proposed evidence-log entry
```

**Escalation**: P0/critical defect or environment blocker → 返回阻塞影响和复现路径给 Coordinator

### Code Reviewer

**Input**:
```
Review Target: {task_id} — {producer}
Files Changed: {文件列表}
Diff: {git diff 输出或文件路径}
ADR / Test References: {相关设计和验证}
```

**Output**:
```
Conclusion: APPROVED | NEEDS_CHANGE | BLOCKED
Findings:
  - File:Line | Severity: P0|P1|P2|P3
  - Description + fix suggestion
Proposed review evidence entry
```

**Escalation**: BLOCKED → 升级给 Coordinator，附带影响评估 + 建议方向

### Design Reviewer

**Input**:
```
Review Target: {task_id} — {architect / design owner}
Design Artifacts: {ADR、架构文档、接口定义}
Implementation References: {代码路径或依赖图，如适用}
```

**Output**:
```
Conclusion: APPROVED | NEEDS_CHANGE | BLOCKED
Design findings: {候选方案、ADR 字段、蓝军挑战、依赖、接口、非功能}
Proposed review evidence entry
```

**Escalation**: 架构级致命缺陷 → BLOCKED 给 Coordinator

### Requirement Reviewer

**Input**:
```
Review Target: {task_id} — {analyst / requirement owner}
Requirement Artifacts: {PR/FAQ、OKR、需求澄清、竞品分析}
Project Goal / Scope: {目标、范围、成功标准}
```

**Output**:
```
Conclusion: APPROVED | NEEDS_CHANGE | BLOCKED
Requirement findings: {用户价值、范围、假设、验收标准、需求追踪}
Proposed review evidence entry
```

**Escalation**: 需求无法追踪到用户价值或验收标准 → BLOCKED 给 Coordinator

### Test Reviewer

**Input**:
```
Review Target: {task_id} — {QA}
Test Artifacts: {测试策略、测试用例、测试报告、缺陷报告}
Requirements / Risk References: {需求、风险、发布目标}
```

**Output**:
```
Conclusion: APPROVED | NEEDS_CHANGE | BLOCKED
Test findings: {覆盖、边界、回归、性能、安全、缺陷质量}
Proposed review evidence entry
```

**Escalation**: 测试体系不能支撑发布或关键路径未覆盖 → BLOCKED 给 Coordinator

### Release Reviewer

**Input**:
```
Review Target: {release task / version}
Release Artifacts: {CHANGELOG、release checklist、rollback plan、feature flags}
Validation Evidence: {CI、verify、review evidence}
```

**Output**:
```
Conclusion: APPROVED | NEEDS_CHANGE | BLOCKED
Release findings: {版本号、范围、门禁、回滚、breaking changes}
Proposed review evidence entry
```

**Escalation**: 发布 artifact 缺失或回滚不可验证 → BLOCKED 给 Coordinator

### Retro Reviewer

**Input**:
```
Review Target: {retro / maintenance task}
Retro Artifacts: {复盘报告、运营数据、改进计划、SOP}
Evidence References: {相关 evidence / risk / decision}
```

**Output**:
```
Conclusion: APPROVED | NEEDS_CHANGE | BLOCKED
Retro findings: {目标回顾、结果评估、原因分析、经验沉淀、改进项}
Proposed review evidence entry
```

**Escalation**: 复盘缺失根因、数据或可执行改进项 → BLOCKED 给 Coordinator

### DevOps

**Input**:
```
Task: {task_id} — {CI/CD or infrastructure objective}
Config Targets: {workflow、Docker、部署、监控、环境配置}
Quality Gates: {门禁阈值、回滚要求、环境一致性}
```

**Output**:
```
- CI/CD or infra configuration changes
- Rollback / alert / environment documentation
- Validation results
- Proposed evidence-log entry
```

**Escalation**: Pipeline、回滚、环境一致性或告警无法达标 → 升级给 Coordinator

### Release

**Input**:
```
Task: {task_id} — {release / version planning objective}
Release Scope: {版本、任务范围、变更列表}
Validation Evidence: {测试、审查、CI、Gate 状态}
```

**Output**:
```
- CHANGELOG / release notes / release checklist / rollback plan
- Version bump rationale
- Proposed decision-log entry for version scope changes
- Proposed evidence-log entry
```

**Escalation**: 版本范围、门禁或回滚计划不满足发布标准 → 升级给 Coordinator

### Maintenance

**Input**:
```
Task: {task_id} — {bug / tech debt / retro objective}
Incident / Defect Data: {日志、报告、复现路径}
Related Code / Rules: {相关文件、规则、测试}
```

**Output**:
```
- Fix / retro / improvement artifacts
- 5-Why + same-class scan + prevention mechanism
- Validation results
- Proposed evidence-log entry with 5-Why summary
- Proposed risk-log / decision-log entry when risk or rule posture changes
```

**Escalation**: 根因无法确认、同类问题扩散、预防机制不能落地 → 升级给 Coordinator

## Review 结论的 Coordinator 处理流程

每个 Reviewer 的 Output 均为 `Conclusion: APPROVED | NEEDS_CHANGE | BLOCKED` 三元组。Coordinator 收到后 MUST 按下表驱动任务到终态，对应 `behavior-protocol.md` M7.4 step 4.6 闭环状态机：

| Reviewer 结论 | Coordinator MUST 动作 |
|--------------|----------------------|
| APPROVED | 写 REVIEW-{task_id}-R{n} 证据（含 round 号）；任务可标记已完成 |
| NEEDS_CHANGE | 写 REVIEW-{task_id}-R{n} 证据；退回 Developer 修复；修复后 MUST 重 spawn 同一 Reviewer 复审（round+1）；查 M7.4 step 4.6 熔断（最大 3 轮） |
| BLOCKED | 写证据；走 escalation（既有规则）；不得标记已完成 |

### 复审协议（re-review）

Reviewer 是无状态的——每次 spawn 都是新会话。Coordinator 在 NEEDS_CHANGE 返工后重 spawn 同一 Reviewer 复审时，**MUST 在 re-spawn prompt 中注入前轮 `review-{task_id}-R{n-1}.md` 路径为强制读取项**。否则 Reviewer 不会看到前轮 findings，复审退化为首轮审查。

Reviewer 复审 MUST：
1. 逐条比对前轮 findings，标注"已修复/未修复/新引入"
2. 在审查报告头部声明 round 号（R1/R2/R3）和前轮引用
3. round ≥ 3 时，若仍有 BLOCKING → 建议 Coordinator 转 BLOCKED
4. 不得不看前轮直接 APPROVED——复审的本质是验证修复

### Escalation 行统一补充

每个 Reviewer 的 Escalation 行（上文各角色定义中的 `**Escalation**`）均隐含以下两条，本节统一声明：

- 原（既有）：BLOCKED → 升级给 Coordinator
- 新增：NEEDS_CHANGE 经 ≥3 轮复审未收敛 → 视同 BLOCKED，升级给 Coordinator（对应 M7.4 step 4.6 C3 熔断）

### escalation 上下文区分（两种 4 选项）

Coordinator 通过 AskUserQuestion 处理 escalation 时，MUST 根据触发源区分选项集：

- **复审熔断 escalation**（round>3 NEEDS_CHANGE/BLOCKED）：(1) 用户介入裁决 (2) 拆分任务降低复杂度 (3) 接受降级（degraded evidence，明确不计审查通过）(4) 撤回该任务
- **Agent 丢失 escalation**（degraded 超限/spawn 失败）：(1) 修复宿主能力 (2) 接受永久降级 (3) 放弃任务 (4) 重试一次

### 证据字段约定

REVIEW-{task_id}-R{round} 证据行含：
- `round={n}`：本轮 round 号（R0/首轮无后缀时省略，从 R1 起显式标注）
- `prev={n-1}`：前轮 round 号（首轮省略）
- `conclusion={APPROVED/NEEDS_CHANGE/BLOCKED}`：本轮结论
- degraded 审查额外标注 `degraded=yes`（用于 step 4.6 degraded 限额计数）

round 完全由 evidence-log 中已存在 R{n} 的最大值派生，无内存状态——并行安全。

## 错误处理

| 场景 | 处理 |
|------|------|
| Agent 产出不满足 Gate | Coordinator 退回给 Agent 修复，附带具体差距 |
| Agent 需要澄清 | Agent 向 Coordinator 提问（不直接问用户），Coordinator 向用户确认后回答 |
| Agent 产出有跨 Agent 矛盾 | Coordinator 验证一致性——发现矛盾则回退给两个 Agent 协调 |
| Agent 丢失/超时 | Coordinator **MUST** 先检查 `agent-locks.json` 中是否仍有该 task 的活跃锁 → 检查 `git diff` 是否有该 Agent 的新产出 → 根据结果决定：锁已释放且有产出 → 收集产出不重新 dispatch；锁未释放但 git diff 有新产出 → 等待锁释放或超时后收集；锁未释放且无产出 → 等待 TTL 过期后强制释放锁并重新 dispatch；不确定 → MUST 通过 AskUserQuestion 向用户报告检查结果并提供选项 (1) 继续等待 (2) 强制重新 dispatch (3) 取消任务 |

## 治理写回

四个规范治理日志由 Coordinator 单点写回：

- `.governance/plan-tracker.md`
- `.governance/evidence-log.md`
- `.governance/decision-log.md`
- `.governance/risk-log.md`

Sub-agent 必须返回结构化 proposed entry，不直接写上述文件。Coordinator 校验 task_id、Gate、证据完整性和跨日志一致性后写回。

**Proposed evidence entry**:
```
| EVD-{N} | {TASK_ID} | {阶段} | {证据类型} | {摘要} | {文件位置} | {ROLE_AGENT} | {日期} | {GATE} | {备注} |
```

**Proposed decision entry**:
```
| DEC-{N} | {日期} | {标题} | {背景} | {决策} | {备选方案} | {选择原因} | {影响范围} | {Owner} | {关联任务} | {后续动作} |
```

**Proposed risk entry**:
```
| RISK-{N} | {日期} | {风险/阻塞描述} | {所属阶段} | {触发条件} | {影响} | {严重级别} | {Owner} | {当前状态} | {缓解动作} | {截止日期} | {关联任务} | {备注} |
```
