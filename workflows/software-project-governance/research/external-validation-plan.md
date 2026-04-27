# 外部项目验证最小路径

本文件定义 AUDIT-003 的执行计划——首次在非工作流仓库中验证 product 是否真的可用。

## 验证目标

证明工作流产品不是"只能在工作流仓库自身运行"的狗粮项目——用户安装后可以端到端使用。

## 测试项目选择标准

| 标准 | 说明 |
|------|------|
| 有实际代码 | 不是一个空仓库——有至少 1 个功能模块 |
| 无 .governance/ | 此前未使用过本工作流 |
| 可安装插件 | 支持 Claude Code 插件市场或本地安装 |
| 项目规模 | 轻量/标准 profile 均可——个人项目或小团队项目优先 |
| 用户参与 | 项目 Owner 愿意配合验证（提供项目信息、确认决策、反馈体验） |

## 最小验证路径（7 步）

### Step 1: 安装（预计 2 分钟）
1. 用户执行 `/plugin marketplace add <path>` 安装 `software-project-governance` 插件
2. 验证：`/plugin` 显示 `software-project-governance @ 0.5.1`

### Step 2: 初始化（预计 5 分钟）
1. 用户执行 `/governance-init` 或直接让 agent 执行初始化
2. Agent 询问：项目名称、项目目标、project_type (new/existing)、profile
3. 验证：`.governance/` 目录创建成功，含 plan-tracker / evidence-log / decision-log / risk-log
4. 验证：如果项目有 `CLAUDE.md`，bootstrap 已注入

### Step 3: 新会话 Bootstrap（预计 2 分钟）
1. 开启新会话（或等待下次会话）
2. Agent 第一动作是否执行了 CLAUDE.md bootstrap（读 plan-tracker）？
3. 验证：agent 自己确认当前阶段、Gate 状态、活跃风险

### Step 4: 执行一个完整阶段（预计 1 session）
1. 选择项目当前所处阶段（如 development）
2. Agent 加载对应子工作流（`stages/development/sub-workflow.md`）
3. Agent 按活动清单执行并记录产出
4. 用户确认 agent 是否：正确识别交互边界、使用了企业实践指导、AI 风险意识

### Step 5: 记录治理数据（每任务随行）
1. Agent 完成任务后在 plan-tracker 标记"已完成"
2. Agent 向 evidence-log 写入证据
3. 验证：证据位置可访问（非"会话上下文"）

### Step 6: 运行治理命令（预计 3 分钟）
1. 用户执行 `/governance-status` → 输出结构化状态
2. 用户执行 `/governance-gate G<N>` → 输出 Gate 判定
3. 用户执行 `/governance-verify` → 输出健康检查报告
4. 验证：3 个命令都有有效输出，未初始化时的错误码正确

### Step 7: Gate 检查（预计 5 分钟）
1. Agent 对当前阶段 Gate 执行检查
2. Gate 判定：通过 / 有条件通过 / 未通过
3. 验证：Gate 结论有对应证据支撑

## 成功标准

- [ ] 7 步全部走通，无阻塞性错误
- [ ] Agent 在整个过程中遵守了 governance protocol（bootstrap/证据/Gate）
- [ ] 所有命令返回正确输出（无崩溃/无空输出/无无限循环）
- [ ] 用户反馈"不会用的"问题在 2 个以内
- [ ] 发现的体验问题有记录和优先级

## 体验问题记录模板

| # | 步骤 | 问题描述 | 严重度 | 根因 | 修复建议 |
|---|------|---------|--------|------|---------|
| 1 |  |  | 阻塞/体验/建议 |  |  |

---

此验证计划待 AUDIT-003 执行时使用。验证结论将回灌到 README、命令文件和子工作流的改进。
