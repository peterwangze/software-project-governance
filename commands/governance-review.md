# governance-review — 触发独立审查

> **推荐使用 `/governance`**——自动检测项目状态并按需路由到对应 Reviewer Agent。本命令保留为手动触发快捷方式。

用户通过斜杠命令 `/governance-review` 手动触发 Reviewer Agent 对指定阶段/类型的产出物进行独立审查。

## 触发条件

用户说以下任意一句即触发：
- `/governance-review` — 交互式选择审查类型
- `/governance-review code` — 代码审查
- `/governance-review requirement` — 需求审查
- `/governance-review design` — 设计审查
- `/governance-review test` — 测试审查
- `/governance-review release` — 发布审查
- `/governance-review retro` — 复盘审查
- `/governance-review all` — 全阶段审查

## 执行流程

### Step 1: 确定审查类型

- **IF** 用户指定了审查类型 → 直接进入 Step 2
- **IF** 用户未指定 → AskUserQuestion："选择审查类型"选项：(1) 需求审查——立项+调研阶段 (2) 设计审查——选型+基础设施+架构阶段 (3) 代码审查——开发阶段 (4) 测试审查——测试阶段 (5) 发布审查——CI/CD+发布阶段 (6) 复盘审查——运营+维护阶段 (7) 全阶段审查

### Step 2: 派生 Reviewer Agent

通过 Agent 工具派生 Reviewer，加载对应的审查 SKILL：

| 审查类型 | 加载的 SKILL | 审查对象 |
|---------|-------------|---------|
| requirement | requirement-review | PR/FAQ、OKR、需求澄清报告、竞品分析 |
| design | design-review + tech-review | 技术选型报告、ADR、系统设计文档 |
| code | code-review | 代码 diff、实现质量 |
| test | test-review | 测试策略、测试计划、测试用例 |
| release | release-review | CI 配置、发布检查清单、回滚方案 |
| retro | retro-review | 运营数据、复盘报告、改进计划 |
| all | 全部 7 个审查 SKILL | 全阶段产出物 |

**Reviewer 不可用处理（强制）**：
1. 首先尝试平台原生 Reviewer Agent spawn。
2. 若平台不支持专用 Reviewer Agent，则使用平台支持的 fallback：`general-purpose` agent + 显式 Reviewer role prompt + 对应审查 SKILL。
3. 若 fallback 仍不可用，Coordinator MUST NOT 自行执行审查。只能二选一：
   - 输出 `BLOCKED`，说明 Reviewer runtime 不可用，审查未完成；
   - 生成 degraded evidence，明确写入：`不构成独立审查`、`不得计入审查通过`、`不得解锁产品代码交付`。

### Step 3: Reviewer 输出审查结论

- **APPROVED**：零 BLOCKING 问题
- **NEEDS_CHANGE**：有 BLOCKING 问题，逐条列出修复建议
- **BLOCKED**：存在根本性问题，需重新执行阶段
- **DEGRADED_EVIDENCE**：仅记录 Reviewer runtime 不可用的事实；不构成独立审查，不得解锁交付

### Step 4: 回写治理记录

- 审查结论写入 `.governance/evidence-log.md`（任务 ID 格式：`REVIEW-{type}-{date}`）
- 如有 BLOCKING 问题 → 创建纠正任务到 `.governance/plan-tracker.md`
- 如有风险发现 → 写入 `.governance/risk-log.md`
- degraded evidence 只能作为阻塞证据记录，不得计入独立审查通过率或审查覆盖率

## 输出格式

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
审查报告 — {审查类型}审查
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

审查人: Reviewer Agent
审查对象: {阶段} 阶段产出物
审查 SKILL: {skill-name}

结论: {APPROVED / NEEDS_CHANGE / BLOCKED}

发现:
  🔴 BLOCKING ({N} 项):
    - {文件:行号}: {问题描述} → {修复建议}
  🟡 WARNING ({M} 项):
    - {问题描述} → {建议}
  🔵 SUGGESTION ({K} 项):
    - {改进建议}

审查证据已写入: EVD-{编号}
```

Reviewer runtime 不可用时输出：

```
结论: BLOCKED / DEGRADED_EVIDENCE
原因: Reviewer Agent spawn 与 general-purpose Reviewer fallback 均不可用
声明: 本记录不构成独立审查，不得计入审查通过，不得解锁产品代码交付
```

## 错误码

| 代码 | 条件 | 动作 |
|------|------|------|
| REVIEW-ERR-001 | `.governance/` 不存在 | 提示用户先运行 `/governance` 初始化 |
| REVIEW-ERR-002 | 指定阶段无产出物可审查 | 告知用户该阶段尚未产生可审查的产出物 |
| REVIEW-ERR-003 | Reviewer Agent 不可用 | 先尝试平台 Reviewer spawn/fallback（`general-purpose` + Reviewer role prompt + 审查 SKILL）；仍不可用则 `BLOCKED` 或仅写 degraded evidence。Coordinator MUST NOT 自审；degraded evidence 不构成独立审查、不得解锁交付 |

## 自校验

- [ ] 审查类型已确定（用户指定或交互选择）
- [ ] Reviewer Agent 已派生且加载正确 SKILL，或已尝试平台支持的 Reviewer fallback
- [ ] Coordinator 未自行执行审查
- [ ] 审查结论已写入 evidence-log
- [ ] degraded evidence 未计入独立审查通过或交付解锁
- [ ] BLOCKING 问题已创建纠正任务
- [ ] 风险发现已写入 risk-log
