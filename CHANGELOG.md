# Changelog

本文件记录 `software-project-governance` 的每个版本变更。

## [0.5.0] — 2026-04-26

### 新增

- **M7.3 风险 escalation 强制执行**：打开状态的风险在截止日期过后 MUST 升级或关闭。`check_risk_escalation()` 检测过期未处理的风险——解决"风险 escalation deadline 过了但什么都没发生"的系统性漏洞（与 M7.4/M7.5 同类模式）
- **M7.3 任务 deadline 强制执行**：未完成任务在"计划完成"日期过后 MUST 完成、重排或显式降级。`check_task_deadline()` 检测过期未处理的任务
- **Check 8：Risk Escalation Deadline**：check-governance 第 8 项检查——检测 risk-log 中"打开"状态且 escalation 截止日期已过的风险
- **Check 9：Task Deadline Enforcement**：check-governance 第 9 项检查——检测 plan-tracker 中非"已完成/已终止"状态且"计划完成"日期已过的任务
- **M8 自检升级**：新增 M7.3 风险 escalation 和任务 deadline 检查项
- **M8.1 表格升级**：从 7 checks 扩展到 9 checks

### 修复

- **Deadline 盲区闭环**：风险 escalation 和任务 deadline 两个字段被定义但从未被自动检测——check-governance 的 Check 2（风险 staleness）只检测 >7 天未更新，不检测 escalation deadline。Check 8/9 补上了这个检测盲区

---

## [0.4.0] — 2026-04-26

### 新增

- **M7.5 任务启动协议**：M7.4 的镜像——修改文件前 MUST 验证任务已在 plan-tracker 中存在。不在则先入账（创建 task ID + 填必填字段）再动手。解决"agent 可绕过 plan-tracker 直接修改文件"的系统性跟踪漏洞
- **M7.4 步骤 4 commit 格式强化**：commit message MUST 包含 task ID 前缀（如 "AUDIT-044: description"）——task ID 是代码变更与 plan-tracker 条目之间的链接，没有它 traceability 就断了
- **Check 7：Commit-Task Traceability**：check-governance 新增第 7 项检查——检测最近 20 个 commit message 是否包含 plan-tracker 中存在的 task ID，无引用→WARN。`check_commit_task_references()` 是 M7.5 步骤 4 的外部验证对应物
- **M8 自检升级**：新增 M7.5 检查项（pre-task protocol executed?）
- **M8.1 表格升级**：从 6 checks 扩展到 7 checks（新增 Check 7：Commit-task traceability）

### 修复

- **跟踪漏洞闭环**：AUDIT-043（M7.4 fix）在入账前就动手修改了 8 个文件——事后才补的 task 条目。M7.5 将这个教训固化为协议：先入账再动手。AUDIT-044 是第一个遵循 M7.5 的任务——task 条目先于任何代码修改被提交

---

## [0.3.0] — 2026-04-26

### 新增

- **M7.4 任务完成协议**：将 evidence → check-governance → audit → commit → continue 绑定为原子不可跳过序列。解决"规则存在但 agent 不执行"的系统性执行一致性问题——每项任务标记"已完成"后 MUST 按序执行 5 步
- **M8 自检升级**：新增 M7.4 检查项（任务完成协议是否执行？）
- **M8.1 表格升级**：从 5 checks 扩展到 6 checks（新增 Check 6：Tier 审计完整性）
- **audit-framework.md D1 触发条件具体化**：新增 governance-critical 文件清单——任何修改了这些文件的任务完成时 MUST 触发审计（不论任务优先级）

### 修复

- **执行一致性漏洞闭环**：AUDIT-040 完成时发现的 4 项 MUST 规则被跳过（审计未触发/未 commit/执行中断/内联提问）通过 M7.4 原子协议系统性修复

## [0.2.0] — 2026-04-26

### 新增

- **M3.1 DRI 规则**：直接责任人模型（Apple DRI + Amazon STO）——每任务 MUST 有唯一 DRI，多 owner=未分配，AI agent DRI 时 agent 有执行决策权/human 是 Escalation
- **M8.1 外部验证机制**：双重机制（agent 自检 + 脚本独立验证）——`check_protocol_compliance()` 独立检测 DRI 违规/条件通过未纠偏/证据格式缺失
- **M5.1~M5.4 AskUserQuestion 协议**：唯一合法提问通道 + 关键决策分类（6 类关键 + 6 类非关键）+ 禁止场景
- **M7.1~M7.3 执行连续性**：用户决策模式声明（stop for critical only / stop for all）、5 条禁止中断模式、实时闭环规则
- **Gate 自动判定**：`gate-check G<N>` 子命令——对 G1~G5 执行启发式自动判定（PASS/FAIL/NEEDS_HUMAN），支持 `--fail-on-blocked` 用于 CI 集成
- **证据质量自动检查**：`check_evidence_quality()` — 检测会话上下文引用/循环引用/空输出声明
- **协议合规自动检查**：`check_protocol_compliance()` — 独立检测 3 类协议违规（DRI/条件通过/证据格式）
- **审计框架**（`audit-framework.md`）：6 维度 × 3 类别审计体系，融入 Gate 原则 #7 / SKILL.md M2.1 / lifecycle.md 治理规则 #5
- **Agent 失败模式文档**（`agent-failure-modes.md`）：8 种失败模式 + 检测方法 + 用户应急动作
- **Tier 审计检查点**（stage-gates.md 原则 #9）：分层推进模型的 Tier 完成后必须执行审计
- **CLAUDE.md 自包含升级**：关键决策分类内嵌（不依赖 SKILL.md 加载状态）+ 故障排除章节

### 变更

- **DRI 模型落地**：plan-tracker Owner 列改为单值 DRI，新增 Escalation 列（20 列模板）
- **交互边界规则升级**：新增 DRI 决策权限定义章节
- **stage-gates.md**：新增原则 #6（Closure Follow-Through）、原则 #7（审计检查点）、原则 #8（DRI 检查）、原则 #9（Tier 审计检查点）
- **Tier 1 双源合并**：skills/ 成为运行时唯一事实源，workflows/rules/ 和 workflows/stages/ 已删除
- **审计触发条件扩展**：SKILL.md M2.1 + audit-framework.md D1/D3/D4 新增"Tier 完成"触发条件

### 修复

- parse_gate_detail regex 从 `###` 改为 `##`（pre-existing bug——gate 和 gate-check 子命令均无法找到 Gate 定义）
- 证据质量升级：5 条"会话上下文"引用替换为持久化文件路径，EVD-070 循环引修复
- CLAUDE.md/SKILL.md 循环依赖解耦

---

## [0.1.0] — 2026-04-17

### 初始版本

- 三层承载模型（workflow 本体层 + agent 入口投影层 + 外部能力层）
- 11 阶段生命周期定义 + 11 Gate 检查
- 4 个治理记录模板（plan-tracker / evidence-log / decision-log / risk-log）
- verify_workflow.py 基础校验脚本
- Claude/Codex adapter 基础入口
- 4 家企业实践调研（Google/Amazon/华为/字节）
- 11 个子工作流骨架
- 5 个 stage skill（需求澄清/技术评审/Code Review/发布 checklist/回顾会议）
- 3 种项目 Profile（lightweight/standard/strict）
- 中途接入协议（onboarding）
- 交互边界规则
