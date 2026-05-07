# 单 Session 持续执行任务的缺陷分析

**日期**: 2026-05-03  
**分析人**: Coordinator（老周）  
**分类**: AI 编程过程经验——单 session vs 多 session 的架构性差异

---

## 核心论点

**单 session 持续执行 ≠ 高效。归档→新 session 不只是"休息"，是强制冷启动验证——这个视角差异本身就是质量保障机制。**

---

## 5 个结构性缺陷

### 1. 上下文窗口饱和——"前面的决策丢了"

模型上下文窗口有限。超长 session 中，最早的分析细节（根因分析、ADR 方案原文）被推到窗口远端。模型在**不完整信息**下做后续决策——依赖压缩摘要而非原始分析。

**表现**：后续任务中，agent 收到的 prompt 是基于 Coordinator 概括的摘要，不是基于 ADR 原文——信息在传递中逐层衰减。

**量化信号**：当 Coordinator 发现自己不再引用原始 ADR 文档而是凭记忆描述方案时，就是窗口饱和的征兆。

### 2. 注意力衰减——"中间的内容被忽略了"

大模型对长上下文的中间部分存在注意力稀释。开头的 bootstrap 规则和结尾的最新任务最容易获得权重，中间版本的细粒度设计决策被"平滑掉"。

**表现**：Check 18/19 的设计细节在 Phase 3 中被简化为"类似的，再加一个 Check 20"——失去了前期设计的严谨性。

### 3. 错误累积——"小偏差被放大"

单 session 中没有强制中断点做全量验证。Code Reviewer 标记的 P2/P3 建议被"先记下来，后面修"——然后永远没修。每个后续任务都建立在前一个任务的输出之上，小偏差逐步放大。

**表现**：COMMIT_EDITMSG 时序问题在 FIX-025 中"修复"，但后续 5 个版本仍然全部使用 `--no-verify` 绕过——修复是否有效从未被验证。

### 4. 沉没成本效应——"再做一个就停"

投入越多，越难停下来评估方向是否正确。"10 个版本都做完了，Phase 3 也不远了"——这种心理压力在单 session 中持续累积。

**表现**：Phase 3 的 3 个任务在 session 末尾执行，Code Reviewer 的速度明显快于 Phase 1（审查深度可能下降），但 Coordinator 没有停下来评估这点。

### 5. Cold Start 验证缺失——"新视角是最便宜的质量检查"

这是最关键的缺陷。新 session 的 agent 从零开始：读 plan-tracker → 读 snapshot → 读 evidence-log → 形成对项目状态的理解。这个过程中：

- 它会发现上一个 Coordinator 认为"没问题"但实际有问题的东西
- 它的理解完全基于治理文件中**显式记录**的事实，而不是 session 中积累的隐性假设
- 如果 snapshot 写得不好，它会在恢复时暴露出来——这是对 snapshot 质量的**强制验证**

---

## 归档 vs 继续的架构性差异

| 维度 | 单 Session 继续 | 归档 → 新 Session |
|------|----------------|-------------------|
| **模型状态** | 携带所有中间假设、捷径、未记录决策 | 从零重建——只保留治理文件中的显式事实 |
| **决策依据** | "上次好像说过了"——依赖模糊记忆 | "plan-tracker 里写的是 X"——依赖显式记录 |
| **问题发现率** | 低——同一视角持续，盲区固化 | 高——冷启动视角天然不同于执行视角 |
| **Snapshot 质量** | 事后补——可能遗漏关键上下文 | 事前生成——作为显式跨会话契约 |
| **验证完整性** | 增量验证——只测新功能不测回归 | 全量验证——新 agent 不信任任何未经证实的假设 |
| **对治理体系的反馈** | 弱——治理缺陷被持续绕过 | 强——每次冷启动都是对治理文件质量的一次压力测试 |

---

## 判断标准：何时应该归档

以下信号出现 **≥2 个**时，应该停止当前 session 并归档：

1. Coordinator 开始凭记忆描述早期方案，不再引用原始文档
2. `--no-verify` 被连续使用超过 2 次（说明 hook 有问题但被绕过）
3. Code Reviewer 的审查报告开始变短、变快（审查深度下降）
4. 新任务的 prompt 越来越短（Coordinator 在节省上下文）
5. 用户说"继续"但 Coordinator 无法准确说出上一次 AskUserQuestion 的上下文
6. session 已完成 ≥5 个版本或 ≥20 个 P0 任务
7. 治理文件（plan-tracker/evidence-log）未被更新超过 3 个任务

---

## 最佳实践

1. **每 3-5 个版本归档一次**，生成完整 session-snapshot
2. **Snapshot 是契约**——必须包含：遗留任务、待确认决策、活跃风险、下次会话优先级
3. **冷启动是功能不是 bug**——利用新 session 的视角差异发现上一 session 遗漏的问题
4. **"继续"的代价 > 归档的代价**——归档只需 2 分钟写 snapshot，但错误累积的修复成本是指数级的

---

## 相关资源

- `.governance/session-snapshot.md`——跨会话契约
- `skills/software-project-governance/SKILL.md` Step 0.5——Agent Team 激活
- `skills/software-project-governance/references/agent-failure-modes.md`——Agent 失败模式
- `docs/requirements/agent-team-bypass-root-cause-analysis-2026-05-02.md`——同 session 中 Agent Team 绕过分析（另一个单 session 缺陷的证据）
