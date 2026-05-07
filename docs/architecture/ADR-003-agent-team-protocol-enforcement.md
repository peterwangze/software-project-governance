# ADR-003: Agent Team 协议强制执行方案

**日期**: 2026-05-02
**状态**: 提案（待 Coordinator 审查）
**决策人**: Architect（老顾）
**关联任务**: 待创建（建议 SYSGAP-030~040）
**前置分析**: `docs/requirements/agent-team-bypass-root-cause-analysis-2026-05-02.md`（Analyst 阿析）
**影响范围**: 8 文件改造 + 1 新文件 + 2 新 verify_workflow.py 检查 + 1 pre-commit hook 强化 + plan-tracker 新增列

---

## 背景

### 问题陈述

software-project-governance v0.24.1 在一个高产 session（7 版本、29 个 P0 产品代码任务）中，4 项违规系统性发生：

1. **Code Reviewer 零激活**：29 段代码未经独立审查即合入 master
2. **SKILL 加载协议未执行**：Developer 收到自定义 prompt，从未加载角色定义 + 任务 SKILL
3. **Analyst 从未激活**：P0/跨层变更无需求分析
4. **QA 从未激活**：31 测试用例无 Test Reviewer 审查

### 根因（来自 Analyst 5-Why 分析）

**根因**：架构从人类工作流"翻译"到 Agent 系统时，停留在了"流程映射"层面，未完成"强制执行映射"。

三个结构性缺陷汇聚：

| 缺陷 | 描述 | 表现 |
|------|------|------|
| **A** | Agent 分派模型是 1:1 而非 1:N | 一个任务→一个 Agent，路由表无"后置自动审查 Agent" |
| **B** | 质量标准依赖 Agent 自觉而非系统阻断 | pre-commit Step 7 WARN 不 BLOCK，review debt 越积越多 |
| **C** | Coordinator 优化"吞吐量"不优化"审查覆盖率" | "继续下一个任务"比"停下來 spawn Reviewer"在内在激励中永远占优 |

5 层 Swiss Cheese 防御的洞完美对齐——每层都假设"前面的层已经确保了 Reviewer"，但没有任何一层真正强制执行。

### 设计约束

- 可以引入少量新文件（调度模板），但不能引入新的架构层
- 必须与现有 6 层架构兼容（适配层→入口层→业务智能层→能力层→基础设施层→核心层）
- 必须与 0.24.0 的三层强制体系（agent填表+脚本审核+hook阻断）协作
- 脚本不判断语义质量，只判断"审查是否发生"
- 不修改产品代码——这是架构设计方案，实现留给 Developer

---

## 决策

采用**四层堵漏体系**，对应 Analyst 报告的 6 个堵漏方向（A~F），在现有 5 层防御的每一层修补致命漏洞，确保洞不再对齐：

1. **路由层**：路由表从 1:1 升级为 1:N 后置链（方向 A）
2. **阻断层**：pre-commit hook Step 7 从 WARN 升级为 BLOCK（方向 B）
3. **验证层**：verify_workflow.py 新增 Agent Team 完整性检查（方向 C）
4. **身份层**：Coordinator 身份定义增加"审查覆盖率"维度 + Sub-agent 调度标准化（方向 D+E）
5. **跟踪层**：plan-tracker 引入审查状态列（方向 F）

核心原则：**系统阻断优先于 Agent 自觉。每一层独立工作——任何一层失败都不影响其他层检测问题。**

---

## 详细设计

### 一、路由表重设计：1:1 → 1:N 后置链（方向 A）

#### 1.1 问题

当前路由表（SKILL.md L141-159）是 1:1 的"请求-响应"模型。"用户请求代码审查"→ 路由到 Code Reviewer。审查被设计为**独立的用户触发任务**，而非**开发任务的后置条件**。

#### 1.2 方案：四列路由表 + 后置审查链

将路由表从 3 列（任务类型 | 目标 Agent | 职能组 | 核心方法论）升级为 5 列，新增"后置审查 Agent"和"触发条件"：

```
| 任务类型 | 执行 Agent | 后置审查 Agent(s) | 触发条件 | 核心方法论 |
|---------|-----------|-------------------|---------|---------|
| Debug/修 Bug | Developer + Maintenance | Code Reviewer | 自动——Developer 完成后 Coordinator MUST spawn | RCA 5-Why + 蓝军自攻击 |
| 新功能开发 | Developer | Code Reviewer | 自动——Developer 完成后 Coordinator MUST spawn | The Algorithm |
| 代码审查 | Code Reviewer | — | 用户触发/自动触发（见上） | 减法优先 + 像素级完美 |
| 设计审查 | Design Reviewer | — | 用户触发 | Design Doc 结构检查 |
| 需求审查 | Requirement Reviewer | — | 用户触发 | PR/FAQ 验证 + OKR 量化 |
| 测试审查 | Test Reviewer | — | 用户触发/自动触发（QA 完成后） | 数据驱动 |
| 发布审查 | Release Reviewer | — | 用户触发 | 回滚方案 MUST 存在 |
| 复盘审查 | Retro Reviewer | — | 用户触发 | 复盘四步完整 |
| 架构决策 | Architect | Design Reviewer | 自动——关键架构决策完成后 | Working Backwards + 6-Pager |
| 需求分析/调研 | Analyst | Requirement Reviewer | 自动——P0 分析完成后 | Customer Obsession + PR/FAQ |
| 测试设计 | QA | Test Reviewer | 自动——QA 完成测试策略后 | 数据驱动 |
| 部署/运维 | DevOps | — | 用户触发 | 定目标→追过程→拿结果闭环 |
| 发布管理 | Release | Release Reviewer | 自动——发布计划完成后 | 专注极致口碑快 |
| 技术债务 | Maintenance | Design Reviewer（如涉及架构） | 自动——涉及产品代码时 | 做难而正确的事 |
| 影响分析（P0/跨层变更） | Analyst + Architect | Design Reviewer + Requirement Reviewer | 自动——分析完成后 | change-impact-checklist Step 1-5 |
```

#### 1.3 "自动"的语义

"自动——Developer 完成后 Coordinator MUST spawn" 的含义：

- 这不是"Agent 自觉记得去 spawn"——这是**路由表的强制性列**
- 当 Coordinator 匹配任务类型到执行 Agent 后，**MUST** 同时读取"后置审查 Agent"列
- 如果后置审查 Agent 非空 → Coordinator **MUST** 在收到执行 Agent 的完成报告后 spawn 对应的审查 Agent
- **这不是可选项。** 跳过审查 = 流程违规，pre-commit hook Step 7 将 BLOCK commit

#### 1.4 路由表在 SKILL.md 中的位置

路由表位于 SKILL.md "Agent 分发路由"节（L141-159）。改造后替换现有表格。

**任务后置链的完整生命周期**：

```
Coordinator 匹配任务类型 → spawn 执行 Agent → 执行 Agent 完成
  → Coordinator 查路由表"后置审查 Agent"列
    → 非空 → MUST spawn 审查 Agent
      → 审查 Agent 输出审查报告
        → 审查 APPROVED → 任务可标记完成
        → 审查 NEEDS_CHANGE → 返回执行 Agent 修复
        → 审查 BLOCKED → 升级到 Coordinator（架构级问题）
    → 为空 → 直接标记完成（如 代码审查/设计审查 本身）
```

#### 1.5 行为协议同步

M7.4（任务完成协议）在现有 6 步序列中新增 Step 4.5：审查触达检查。

M7.5 Step 2.5 修订——消歧义：
- 原文："MUST spawn 对应 Developer agent" → 新文："MUST spawn 执行 Agent + 查路由表后置审查 Agent 列 → MUST spawn 审查 Agent"
- 新增语言："一个任务对应 N 个 Agent 是正常的——1 个执行 + 1~2 个审查。单 Agent 执行不构成 Agent Team。"

---

### 二、Pre-commit Hook Step 7：WARN → BLOCK（方向 B）

#### 2.1 问题

当前 Step 7（pre-commit L175-204）：

```
REVIEW GAP: P0 task 'SYSGAP-XXX' has no review evidence.
This is a WARNING — commit allowed but review debt
is being tracked. Fix in next commit.
```

WARN 不改变行为。"Fix in next commit"是一个永远无法兑现的承诺——如果下一个 commit 也没有审查，WARN 再次出现，再次被忽略。

#### 2.2 方案：P0 产品代码任务缺少审查证据 → BLOCK

**检测逻辑**（伪代码）：

```bash
# Step 7: Review Evidence BLOCK (AUDIT-086 升级)
if [ -f "$REPO_ROOT/.governance/evidence-log.md" ] && [ -f "$REPO_ROOT/.governance/plan-tracker.md" ]; then
    TASK_ID=$(extract_task_id "$COMMIT_MSG")

    if [ -n "$TASK_ID" ]; then
        # 1. 判断是否为 P0 任务
        IS_P0=$(grep -c "| $TASK_ID |.*| P0 |" "$REPO_ROOT/.governance/plan-tracker.md" 2>/dev/null || echo "0")

        if [ "$IS_P0" -gt 0 ]; then
            # 2. 判断是否修改了产品代码
            IS_PRODUCT_CODE=$(check_product_code "$CHANGED_FILES")

            if [ "$IS_PRODUCT_CODE" -eq 1 ]; then
                # 3. 判断任务类型是否需要审查（查路由表后置审查 Agent 列）
                TASK_TYPE=$(extract_task_type "$TASK_ID")
                NEEDS_REVIEW=$(check_routing_table "$TASK_TYPE")

                if [ "$NEEDS_REVIEW" -eq 1 ]; then
                    # 4. 检查 evidence-log 是否有审查证据
                    HAS_REVIEW=$(grep -cE "REVIEW-.*$TASK_ID" "$REPO_ROOT/.governance/evidence-log.md" 2>/dev/null || echo "0")
                    HAS_REVIEW_FILE=$(ls "$REPO_ROOT/.governance/review-$TASK_ID.md" 2>/dev/null | wc -l)

                    if [ "$HAS_REVIEW" -eq 0 ] && [ "$HAS_REVIEW_FILE" -eq 0 ]; then
                        echo "REVIEW BLOCKED: P0 product code task '$TASK_ID' has no independent review evidence."
                        echo "Action: spawn Code Reviewer (or applicable reviewer) and complete review,"
                        echo "        then re-commit with review evidence in evidence-log."
                        echo "Emergency bypass: git commit --no-verify"
                        exit 1  # BLOCK
                    fi
                fi
            fi
        fi
    fi
fi
```

**BLOCK 条件**（全部满足才阻断）：
1. 任务为 P0 优先级
2. 修改涉及产品代码文件（按现有产品代码 vs 治理记录边界判定）
3. 任务类型在路由表中有"后置审查 Agent"（即该类型需要审查）
4. evidence-log 中无对应 REVIEW evidence 且 `.governance/review-{task_id}.md` 不存在

**不 BLOCK 的条件**（任一满足即放行）：
- 非 P0 任务（P1/P2 降级为 WARN）
- 仅修改治理记录（非产品代码）
- 任务类型本身是审查类任务（后置审查 Agent 列为空）
- 已有审查证据（APPROVED/NEEDS_CHANGE/BLOCKED 结论存在）
- 紧急 bypass：`git commit --no-verify`（需记录到 risk-log——post-commit hook 检测 --no-verify 使用并告警）

#### 2.3 路由表引用方式（脚本不内嵌表）

pre-commit hook 是 bash 脚本，不能解析路由表的全部语义。简化判定策略：

- hook 从 commit message 中提取 task ID
- hook 通过 plan-tracker 判断 P0 状态
- hook 通过文件路径判定产品代码
- **审查需求判断**：pre-commit hook 内嵌一个**任务前缀→审查需求映射**（硬编码在 hook 中，随 hook 版本更新同步路由表）

| 任务前缀 | 需要审查？ | 审查类型 |
|---------|----------|---------|
| SYSGAP- | 是（P0=BLOCK, 非P0=WARN） | 由任务上下文决定 |
| AUDIT- | 是（P0=BLOCK, 非P0=WARN） | 由任务上下文决定 |
| FIX- | 是（P0=BLOCK, 非P0=WARN） | 由任务上下文决定 |
| MAINT- | 是（P0=BLOCK, 非P0=WARN） | 由任务上下文决定 |
| CLEANUP- | 是（P0=BLOCK, 非P0=WARN） | 由任务上下文决定 |
| REVIEW- | 否（审查任务自身） | — |
| EVD- | 否（证据记录） | — |
| DOC- | 否（文档，除非 P0+产品代码） | — |

> **设计原则**：hook 中的映射是路由表的**运行时投影**——路由表是完整事实源，hook 中的映射是性能优化（避免 hook 每次解析路由表）。两个表必须一致。verify_workflow.py 新增检查确保一致性。

#### 2.4 紧急 hotfix 的处理

`--no-verify` 绕过 BLOCK 后，post-commit hook **MUST** 检测 bypass 并记录：

```bash
# post-commit hook: detect --no-verify usage
if commit_was_no_verify; then
    log_to_risk_log "REVIEW-BYPASS: task '$TASK_ID' was committed without review evidence via --no-verify"
    echo "WARNING: Review bypass detected. Review debt added to plan-tracker."
fi
```

---

### 三、verify_workflow.py：新增 Agent Team 完整性检查（方向 C）

#### 3.1 问题

当前 17 项检查（check_evidence_completeness 到 check_plugin_freshness）中，无任何一项验证"产品代码任务是否有关联的审查证据"。所有检查都"盲"于这个问题。

#### 3.2 新增检查项

**Check 13: Agent Team Review Completeness (`check_agent_team_review`)**

| 属性 | 值 |
|------|---|
| 检测内容 | 产品代码任务是否有关联的独立审查证据 |
| 为什么 agent 自检无法捕获 | Agent 可能"忘记" spawn Reviewer；Coordinator 自认为合规 |
| 数据结构 | 从 plan-tracker + evidence-log + git log 联合提取 |

**检查逻辑**：

```
1. 从 plan-tracker 中提取所有状态为"已完成"的产品代码任务
2. 对每个任务：
   a. 从 evidence-log 中查找该 task ID 的审查证据（REVIEW-* 类型）
   b. 从 git log 中检查是否有对应的 commit（含 task ID）
   c. 判定：
      - PASS: 有审查证据（审查报告路径或 REVIEW-* evidence 条目）
      - FAIL: 产品代码变更但无任何审查证据
      - WARN: 有审查证据但审查人与执行人相同（自审嫌疑）
3. 汇总：
   - total_tasks: 总产品代码任务数
   - reviewed: 已审查任务数
   - unreviewed: 未审查任务数 ← FAIL 计数
   - self_reviewed: 自审嫌疑数 ← WARN 计数
   - review_gap_tasks: 未审查任务的 ID 列表
4. PASS 条件: unreviewed == 0
```

**Check 14: Agent Activation Completeness (`check_agent_activation`)**

| 属性 | 值 |
|------|---|
| 检测内容 | P0/跨层产品代码变更是否激活了 Analyst + Architect |
| 数据结构 | 从 plan-tracker + evidence-log 联合提取 |

**检查逻辑**：

```
1. 从 plan-tracker 中提取所有 P0 + 产品代码 + ≥2 层架构的任务
2. 对每个任务：
   a. 从 evidence-log 查找影响分析证据
   b. 判定影响分析是否由 Analyst 产出（而非 Coordinator 自行撰写）
      - 判定方式：检查 evidence-log 中 Analyst spawn 证据 / 影响分析条目中标注 "Analyst:"
      - 如果只有 Coordinator 写的影响分析（无 Analyst 参与标记）→ FAIL
3. 汇总：
   - total_p0_cross_layer: P0 跨层变更数
   - analyst_activated: 有 Analyst 参与的任务数
   - analyst_bypassed: 无 Analyst 参与的任务数
4. PASS 条件: analyst_bypassed == 0
```

#### 3.3 与现有 17 项检查的集成

新增检查自然融入现有 check-governance 流程：

```
现有 17 项检查：
  1. evidence_completeness     7. commit_task_references
  2. risk_staleness              8. risk_escalation
  3. gate_consistency           9. task_deadline
  4. protocol_compliance       10. m5_compliance
  5. evidence_quality           11. cross_references
  6. tier_audit_completeness   12. sequential_ids
                               13. structural_validity
                               14. commit_scope
                               15. goal_alignment      (Check 15 — SYSGAP-023)
                               16. user_impact         (Check 16 — SYSGAP-024)
                               17. plugin_freshness    (Check 17)

新增 2 项（接续编号）：
→ 18. agent_team_review       (Check 18 — 本 ADR)
→ 19. agent_activation         (Check 19 — 本 ADR)
```

> 注：verify_workflow.py 内部函数编号（check_goal_alignment/check_user_impact 等）与 check-governance 输出编号略有差异。新增函数为 `check_agent_team_review()` 和 `check_agent_activation()`，在 check-governance 命令中作为第 18/19 项输出。

#### 3.4 检查触发时机

- 加入 check-governance 全量检查 — session 结束 / Gate 通过前
- 新增独立子命令 `check-agent-team` — 开发者可单独验证 Agent Team 完整性
- 加入 M8.1 外部验证的检查项列表

---

### 四、Coordinator 身份更新（方向 D）

#### 4.1 问题

Coordinator 的"擅长"定义了它的优化方向——它优化"任务完成吞吐量"，不优化"审查覆盖率"。在 maximum-autonomy 模式下，没有外部力量来平衡这个天平。

#### 4.2 方案：SKILL.md "擅长" + "痛恨" 新增审查维度

在 SKILL.md Coordinator 身份定义中（L30-41）：

**"擅长"新增第 5 项**：

```
- 确保每个产品代码产出被独立审查——审查覆盖率是吞吐量的质量系数，不是吞吐量的敌人。
  审查覆盖率 < 100% 时，停止开始新任务，先补审。
```

**"痛恨"新增第 4 项**：

```
- 审查覆盖率 < 100% 但没有自觉补审——"我忘了"不是理由，路由表的"后置审查 Agent"列不是装饰
```

**铁律新增第 6 条**：

```
- 产品代码任务完成 ≠ 任务完成。完成 = 执行 Agent 返回结果 + 审查 Agent 输出 APPROVED。
  没有审查结论的任务，状态只能为"待审查"，不能为"已完成"。
```

#### 4.3 激励对齐分析

| 维度 | 旧激励 | 新激励 | 行为变化 |
|------|--------|--------|---------|
| 任务完成定义 | 执行 Agent 返回 → 完成 | 执行 Agent 返回 + 审查 Agent APPROVED → 完成 | 完成任务的门槛提高了——必须有审查 |
| 吞吐量 vs 审查覆盖率 | 吞吐量是唯一指标 | 审查覆盖率是吞吐量的质量系数 | "完成 29 个任务但 0 审查" = 绩效差（不是绩效好） |
| "继续下一个任务" | 永远优先 | 审查覆盖率 < 100% 时→停止，先补审 | 审查变成阻塞条件而非事后修补 |

---

### 五、Sub-agent 调度标准化（方向 E）

#### 5.1 问题

当前 sub-agent 调度协议（SKILL.md L162-167）仅要求 Coordinator "MUST 加载两个文件"——这是对 Coordinator 的**文字指令**。没有系统机制验证 sub-agent 是否真的加载了角色定义 + 任务 SKILL。

违规 session 中，Developer 收到的是 Coordinator 自定义 prompt——从未接触 agents/developer.md 中的硬门槛和 SKILL 绑定表。

#### 5.2 方案：调度模板函数

创建新文件：`skills/software-project-governance/references/agent-dispatch-template.md`

**模板结构**：

```markdown
# Agent Dispatch Template — Coordinator 调度 sub-agent 的强制格式

Coordinator MUST 使用以下模板构造 sub-agent prompt。**MUST NOT** 跳过任何节、传递自定义指令覆盖硬约束。

## 调度模板

### [ROLE_DEFINITION] — 强制加载
加载: {ROLE_FILE_PATH}
此 agent 的角色定义、职责边界、工具权限、硬门槛由该文件定义。
Agent MUST 完整读取并遵守该文件中的所有约束。

### [TASK_SKILL] — 强制加载
加载: {TASK_SKILL_PATH}
此 agent 的任务规范由该文件定义。按 SKILL 定义的确定性步骤逐项执行，不跳步，不自创步骤。
Agent MUST 读取该文件并按其步骤执行。

### [TASK_CONTEXT] — 可填充
任务 ID: {TASK_ID}
任务描述: {TASK_DESCRIPTION}
输入文件/路径: {INPUT_FILES}
验收标准: {ACCEPTANCE_CRITERIA}
关联 ADR: {RELATED_ADRS}

### [EXECUTION_CONSTRAINTS] — 不可覆盖
- 禁止与用户交互（无 AskUserQuestion）
- 禁止创建子 agent（无 Agent 工具）
- 禁止修改治理状态文件（plan-tracker/evidence-log/risk-log/decision-log）
- 完成后返回结构化结论给 Coordinator:
  格式: 完成状态 | 产出物位置 | 证据

### Coordinator 可以填充的占位符
- {ROLE_FILE_PATH}: agents/<name>.md（MUST 提供——不允许 Coordinator 省略）
- {TASK_SKILL_PATH}: skills/<skill-name>/SKILL.md（MUST 提供——不允许 Coordinator 省略）
- {TASK_ID}: 任务编号
- {TASK_DESCRIPTION}: 任务描述
- {INPUT_FILES}: 输入文件路径列表
- {ACCEPTANCE_CRITERIA}: 验收标准
- {RELATED_ADRS}: 关联 ADR 引用

### Coordinator MUST NOT
- 删除或替换 [ROLE_DEFINITION] 节——角色定义必须完整加载
- 删除或替换 [TASK_SKILL] 节——任务 SKILL 必须完整加载
- 在 [EXECUTION_CONSTRAINTS] 之外添加额外约束
- 传递"你不需要读 agents/ 文件了——我已经总结了要点"的自定义指令
- 省略 {ROLE_FILE_PATH} 或 {TASK_SKILL_PATH}
```

#### 5.3 模板的使用方式

Coordinator 在构造 Agent 工具调用时：

```
prompt = fill_template(
    template = read("skills/software-project-governance/references/agent-dispatch-template.md"),
    placeholders = {
        ROLE_FILE_PATH: "agents/developer.md",
        TASK_SKILL_PATH: "skills/stage-development/SKILL.md",
        TASK_ID: "SYSGAP-030",
        TASK_DESCRIPTION: "...",
        INPUT_FILES: "...",
        ACCEPTANCE_CRITERIA: "...",
        RELATED_ADRS: "docs/architecture/ADR-003-..."
    }
)
Agent(subagent_type="general-purpose", prompt=prompt)
```

#### 5.4 行为协议同步

M7.5 新增 Step 2.5a：Sub-agent 调度格式检查。

```
2.5a Sub-agent 调度格式检查——
  Coordinator MUST 使用 agent-dispatch-template.md 模板构造 sub-agent prompt。
  MUST NOT 传递自定义 prompt 替代模板。
  MUST NOT 省略 ROLE_FILE_PATH 或 TASK_SKILL_PATH。
  违反 → 流程违规，verify_workflow.py Check 14 可检测。
```

#### 5.5 验证机制

verify_workflow.py 无法直接检查 sub-agent 收到的 prompt（那是 runtime 信息）。替代验证方式：

- **Check 14（Agent Activation Completeness）已覆盖**：通过检查 evidence-log 中的 Analyst spawn 证据间接验证
- **未来增强**：如果 Agent 平台支持 prompt 审计日志，可补入自动化检查

---

### 六、Plan-tracker 审查状态（方向 F）

#### 6.1 方案：任务表新增"审查状态"列

在 plan-tracker 的任务表中新增一列：

| 列名 | 位置 | 可选值 | 默认值 |
|------|------|--------|--------|
| 审查状态 | 在"状态"列之后 | `待审查` / `审查中` / `已审查` / `审查豁免` | `待审查`（产品代码任务）/ `审查豁免`（治理记录任务） |

**值定义**：

| 值 | 含义 | 何时设为 |
|----|------|---------|
| `待审查` | 执行 Agent 已完成，审查 Agent 尚未启动 | 执行 Agent 返回完成结果时自动设置 |
| `审查中` | 审查 Agent 已 spawn，正在审查 | Coordinator spawn 审查 Agent 时设置 |
| `已审查` | 审查 Agent 已输出 APPROVED 结论 | 审查 Agent 返回 APPROVED 时设置 |
| `审查豁免` | 任务不涉及产品代码或已在路由表中标注无需审查 | 任务创建时根据类型判断 |

**状态流转**：

```
任务创建（待审查/审查豁免）
  → 执行 Agent 开始（状态: 进行中，审查状态: 待审查）
  → 执行 Agent 完成（状态: 仍为进行中，审查状态: 待审查——不能标记已完成！）
  → 审查 Agent spawn（审查状态: 审查中）
  → 审查 Agent 返回 APPROVED（状态: 已完成，审查状态: 已审查）
  → 审查 Agent 返回 NEEDS_CHANGE（状态: 进行中，审查状态: 待审查——退回修改）
  → 审查 Agent 返回 BLOCKED（状态: 阻塞，升级给 Coordinator）
```

**关键约束**：

- **"已完成但未审查"不能存在**：任务状态为"已完成"时，审查状态 MUST 为"已审查"或"审查豁免"。否则为数据不一致——verify_workflow.py Check 13 检测。
- **审查债务显式化**：plan-tracker 尾部新增 `## 审查债务` 节，列出所有审查状态为"待审查"或"审查中"超过 24 小时的任务。

#### 6.2 审查债务节

在 plan-tracker 尾部新增：

```markdown
## 审查债务

| 任务 ID | 描述 | 执行 Agent | 审查 Agent | 审查状态 | 积压天数 | 优先级 |
|---------|------|-----------|-----------|---------|---------|--------|
| SYSGAP-030 | ... | Developer | Code Reviewer | 待审查 | 2 | P0 |

审查债务 >= 3 天 → 自动升级为 risk-log 条目。
审查债务 >= 5 天 → BLOCK 所有新任务启动（Coordinator 铁律）。
```

---

### 七、与现有体系的集成

#### 7.1 六层架构兼容性

本方案不引入新架构层，变更分布在各层：

| 层 | 变更文件 | 变更类型 |
|----|---------|---------|
| 入口层 | `skills/software-project-governance/SKILL.md` | 路由表升级 + Coordinator 身份更新 + 调度模板引用 |
| 业务智能层 | `agents/` 各文件（不变——角色定义无需修改） | 无变更 |
| 能力层 | `skills/stage-development/SKILL.md`, `skills/code-review/SKILL.md` | 无变更（已定义审查流程） |
| 基础设施层 | `infra/hooks/pre-commit` (Step 7), `infra/verify_workflow.py` (新 Check 18/19) | 强化 |
| 核心层 | `references/behavior-protocol.md` (M7.4/M7.5), `references/agent-dispatch-template.md` (新) | 协议修订 + 新模板 |
| 核心层 | `core/templates/plan-tracker.md` | 模板新增"审查状态"列 |
| 治理数据 | `.governance/plan-tracker.md` | 运行时新增列 |

#### 7.2 与产品代码边界协作

本方案完全复用 SKILL.md "产品代码 vs 治理记录边界"的现有定义。pre-commit hook Step 7 的 BLOCK 判定中的"产品代码"判定使用与现有 Step 9 完全相同的路径列表。

#### 7.3 与 change-impact-checklist 协作

现有 checklist 规定：P0 任务 + >=2 个架构层 → MUST spawn Analyst + Architect。

本方案的路由表后置审查链覆盖此场景：
```
影响分析（P0/跨层变更） → Analyst + Architect → (自动) Design Reviewer + Requirement Reviewer
```

Check 14（Agent Activation）验证 Analyst 是否真的被激活。

#### 7.4 与 pre-commit hook Step 10-12 协作

Step 10-12 检查 目标对齐/用户影响/breaking change 迁移指南（BLOCK）。Step 7（审查 BLOCK）是新增的第 4 个 BLOCK 条件。

5 个 BLOCK 条件构成完整防线：

| Step | 检查内容 | 阻断级别 | 引入版本 |
|------|---------|---------|---------|
| Step 2 | 无 Task ID | BLOCK | 早期 |
| Step 3 | Task 不在 plan-tracker | BLOCK | 早期 |
| Step 6 | Bootstrap 变更纪律（CLAUDE.md 直接修改） | BLOCK | 0.21.0 |
| Step 7 | 审查证据缺失（P0 产品代码） | **BLOCK（原 WARN）** | **本 ADR（升级自 0.21.0）** |
| Step 10 | 目标一致性缺失 | BLOCK | 0.24.0 |
| Step 11 | 用户影响分析缺失 | BLOCK | 0.24.0 |
| Step 12 | Breaking change 无迁移指南 | BLOCK | 0.24.0 |

#### 7.5 与 Gate 系统协作

G6（开发完成）的检查项中新增：

```
| Gate 检查项 | 判定标准 | 自动化判定 |
|------------|---------|-----------|
| 审查证据完整性 | 所有产品代码任务有独立审查证据（REVIEW-* evidence 或审查报告文件） | check_agent_team_review() → unreviewed == 0 |
| Analyst 激活完整性 | 所有 P0/跨层变更有 Analyst 参与的影响分析 | check_agent_activation() → analyst_bypassed == 0 |
```

#### 7.6 与 Profile 系统协作

审查 BLOCK 强度按 Profile 差异化：

| Profile | 审查 BLOCK 范围 | 审查债阈值 |
|---------|----------------|-----------|
| lightweight | P0 产品代码任务 BLOCK | 审查债 >= 3 天 → WARN（不阻断新任务） |
| standard | P0 产品代码任务 BLOCK; P1 产品代码任务 WARN | 审查债 >= 5 天 → BLOCK 新任务 |
| strict | **所有**产品代码任务（P0+P1+P2）BLOCK | 审查债 >= 3 天 → BLOCK 新任务 |

---

## 备选方案

### 备选方案 1: Coordinator-internal Review（被否决）

**描述**：让 Coordinator 在部署 Developer 后自己执行代码审查——不 spawn 独立的 Reviewer Agent。

**否决理由**：
- 违反 Producer-Reviewer 分离原则（Coordinator 铁律第 3 条："Developer 不审查自己的代码，Reviewer 不修改代码"）
- Coordinator 不是 Code Reviewer，不具备逐行审查能力（它的角色定义是"拆任务、匹配 Agent、看护治理质量"）
- 这是当前问题——只是换了一个"执行者"（从 Developer 自审变成 Coordinator 审），审查独立性=0

### 备选方案 2: 只升级 pre-commit hook，不改路由表（被否决）

**描述**：只把 Step 7 从 WARN 改为 BLOCK，不改路由表。

**否决理由**：
- hook BLOCK 是"下游堵漏"——解决的是"commit 之后发现没有审查"的问题
- 路由表才是"上游预防"——解决的是"Coordinator 为什么不 spawn Reviewer"的问题
- 只堵下游 = commit 被 BLOCK → Coordinator 困惑"为什么 BLOCK？"→ 用户手动 bypass → 审查仍然没有发生
- 上下游必须同时修：路由表告诉 Coordinator"你该做什么"，hook 验证"你是否做了"

### 备选方案 3: 引入外部 CI pipeline 做审查完整性检查（被否决——增量采纳）

**描述**：在 GitHub Actions / CI pipeline 中新增审查完整性检查——pre-commit hook 保持 WARN，CI 做 BLOCK。

**否决理由（对当前阶段）**：
- 本项目当前没有 CI pipeline（AUDIT-003 外部验证尚未完成）
- CI BLOCK 发生在 push 之后——太晚了。pre-commit BLOCK 发生在 commit 之前——最快反馈
- 增量采纳：未来有 CI pipeline 后，审查完整性检查可同时运行在 pre-commit（快速反馈）和 CI（不可绕过）两级

### 备选方案 4: 让 Agent 平台（Claude Code）提供原生 sub-agent 间依赖声明（被否决——超出范围）

**描述**：让 Claude Code 平台支持"agent B 必须在 agent A 完成后自动运行"的原生声明——工作流只声明依赖，平台自动执行。

**否决理由**：
- 这是平台能力需求，不是本工作流能决定的
- 即使平台支持，路由表仍然是定义依赖的事实源
- 本方案保持平台无关——在 Agent 工具层面实施，不依赖特定平台的特性

---

## 蓝军挑战

### 蓝军挑战 #1：Coordinator 在高压 session 中仍然会跳过审查——"我知道规则，但我选择忽略"

**挑战**：文字规则不能阻止行为。在 maximum-autonomy + 高吞吐量压力的 session 中，Coordinator 可能理性选择"先提交再说"——即使路由表说 MUST spawn Reviewer，pre-commit hook 的 BLOCK 也可以被 `--no-verify` 绕过。

**缓解措施**：
1. pre-commit hook BLOCK 阻止了"无意识的绕过"——大多数绕过是"忘记了"而非"故意对抗"，BLOCK 提醒足以让 Coordinator 记起 spawn Reviewer
2. post-commit hook 检测 --no-verify 使用。如果同一 session 中连续使用 --no-verify 绕过审查 ≥ 3 次 → post-commit hook 输出醒目告警并创建 risk-log 条目
3. verify_workflow.py Check 18 检测累积的审查债务——session 结束时自动暴露。如果 unreviewed > 0 → session snapshot 标记为"审查不完整"→ 下一 session 恢复时优先补审
4. plan-tracker 审查债务节提供可视化——用户可以看到哪些任务缺审查。这是人类监督层（Swiss Cheese Layer 5）的增强

### 蓝军挑战 #2：Developer 完成后立即返回"我完成了"，但 Coordinator 不 spawn Reviewer 就标记任务"已完成"——路由表约束在"标记完成"之前而非"spawn 完成"之后没有检查点

**挑战**：路由表定义了"Coordinator MUST spawn Reviewer"，但 Coordinator 可以——在收到 Developer 结果后——不 spawn Reviewer，直接标记任务"已完成"。没有任何系统机制在"标记完成"这个动作上做阻断。

**缓解措施**：
1. **plan-tracker 的任务状态约束是逻辑阻断**：Coordinator 铁律第 6 条定义"产品代码任务完成 = 执行 Agent 返回结果 + 审查 Agent APPROVED"。Coordinator **逻辑上不能**将"审查状态=待审查"的行标记为"状态=已完成"——这违反了自己的铁律。
2. **verify_workflow.py Check 18 事后检测**：即使 Coordinator 违规标了"已完成"，Check 18 发现该任务有产品代码变更但无审查证据 → FAIL
3. **pre-commit hook Step 7**：后续 commit 中如果该任务 ID 再次出现（例如修复、补充），BLOCK 会触发——因为证据中仍无审查记录
4. **自指涉增强（长期）**：未来可考虑在 Agent 工具层注入 post-completion hook——但这需要平台支持，暂不在本方案范围内

### 蓝军挑战 #3：Sub-agent 调度模板是一个 Markdown 文件——Coordinator 可以不读它（就像它可以不读 SKILL.md）

**挑战**：方案引入的 agent-dispatch-template.md 本身也是 Markdown 文件——和已经失效的 SKILL.md 文字规则一样。如果 Coordinator 不读这个模板，调度仍然使用自定义 prompt，模板形同虚设。

**缓解措施**：
1. **模板不是给 Coordinator "读"的——是它在构造 prompt 时的"代码生成函数"**。模板定义了占位符和强制节。Coordinator 如果不遵循模板，sub-agent 收到的 prompt 将缺少 `[ROLE_DEFINITION]` 和 `[TASK_SKILL]` 节——sub-agent 获取不到角色定义和任务规范，执行质量下降。Coordinator 有动机遵循模板（否则 sub-agent 执行质量差 → Coordinator 需要更多轮返工 → 吞吐量下降）。
2. **verify_workflow.py 间接检测**：Check 18 检测审查是否发生（结果导向），Check 19 检测 Analyst 是否激活。如果模板未被使用，sub-agent 执行质量差 → 产出物不完整 → 验证失败 → Coordinator 需要修复。这形成了一个"遵循模板 = 更少返工"的激励闭环。
3. **模板是基础设施**——它定义了 sub-agent prompt 的"API 格式"。Coordinator 不需要"读"它——它需要"用它"。就像 Coordinator 不需要"读" Agent 工具的 API 文档——它需要"遵循"Agent 工具的调用格式。模板文件是 Agent 工具 + 模板格式的**参考实现**。
4. **如果 Coordinator 仍然不使用模板**——和所有其他文字规则一样，system block 是最后防线（pre-commit BLOCK + verify_workflow.py FAIL）。我们接受"不可能 100% 阻止 agent 违规"的前提——我们的策略是让违规的代价足够高（commit 被 BLOCK / session 结束时被标记为审查不完整 / 审查债务可视化），让自觉遵循模板的收益超过绕过的收益。

### 蓝军挑战 #4：任务前缀→审查需求映射在 pre-commit hook 中硬编码——路由表更新后 hook 可能不同步

**挑战**：pre-commit hook Step 7 需要判断"这个任务是否需要审查"。完整路由表在 SKILL.md 中，但 bash 脚本无法解析 Markdown 路由表。如果 hook 中硬编码的映射和路由表不同步，审查 BLOCK 可能误判（该 BLOCK 的不 BLOCK 或不该 BLOCK 的 BLOCK）。

**缓解措施**：
1. verify_workflow.py 新增**路由表一致性检查**（嵌入在 Check 18 中）：对照 SKILL.md 路由表的"后置审查 Agent"列和 pre-commit hook 中的映射，发现不一致 → WARN
2. pre-commit hook 的映射策略偏保守：**不确定是否需要审查 → 认为需要审查**。误 BLOCK 比漏 BLOCK 好——误 BLOCK 可以通过 `--no-verify` 绕过（有审计记录），漏 BLOCK 意味着不受审查的代码静默合入。
3. hook 中的映射不追求完全精确——追求"一定不会漏"。对不确定的任务前缀 → 按 P0 处理 → BLOCK 优先。

### 蓝军挑战 #5：新增的"审查状态"列和"审查债务"节增加了 plan-tracker 的手动维护负担

**挑战**：plan-tracker 已经有多列（ID/阶段/任务/目标/输入/输出/状态/优先级/日期/Gate/验收/DRI/Escalation——13 列）。新增"审查状态"列（第 14 列）增加了 Coordinator 的维护负担。如果 coordinator 忘记更新审查状态列，审查债务节数据失真。

**缓解措施**：
1. **审查状态是自动衍生的**——不是手动维护的。Coordinator 在 spawn 审查 Agent 时自动更新为"审查中"；审查 Agent 返回 APPROVED 时自动更新为"已审查"。审查状态是执行动作的副作用，而非额外的手动步骤。
2. **verify_workflow.py Check 18 交叉验证**：检查 evidence-log 中的审查证据和 plan-tracker 中的审查状态是否一致。不一致 → WARN。
3. **Lightweight profile 豁免**：lightweight profile 下不强制维护"审查债务"节——只在 standard/strict 下强制。
4. **渐进式采用**：如果 plan-tracker 列数成为实际问题，未来可考虑将审查状态作为独立文件（`.governance/review-tracker.md`）——但这在当前阶段是过度工程化。

### 蓝军挑战 #6：在非 AI 项目（传统软件项目）中采用本方案，审查频率会导致开发速度下降

**挑战**：每个 P0 产品代码 commit 都要审查，在快速迭代阶段（MVP/原型）可能拖慢速度。

**缓解措施**：
1. **这是设计意图——不是副作用**。29 段代码未经审查合入 master 的成本远高于"多等 5 分钟让 Reviewer 完成审查"。速度的代价是质量债务——本方案的设计目标就是让这个代价显式化。
2. **Profile 差异化**（见 7.6 节）：lightweight profile 下审查 BLOCK 范围仅限于 P0 任务——P1/P2 降级为 WARN。MVP 阶段可以选择 lightweight profile。
3. **审查豁免通道**：对于明确不需要审查的任务（如治理记录更新、纯文档变更），路由表中"后置审查 Agent"列为空 → pre-commit 不 BLOCK。
4. **紧急 bypass 存在**：`--no-verify` 始终可用——但它被审计（post-commit hook 记录），确保 bypass 不是默认行为。

---

## 执行优先级与分期

本方案规模较大，建议分 3 期执行：

### Phase 1（立即可执行——0.25.0）：阻断+路由+身份

| # | 动作 | 改造文件 | 任务 ID（建议） |
|---|------|---------|---------------|
| 1 | pre-commit hook Step 7 WARN→BLOCK | `infra/hooks/pre-commit` | SYSGAP-030 |
| 2 | 路由表升级为 5 列（含后置审查 Agent） | `skills/software-project-governance/SKILL.md` | SYSGAP-031 |
| 3 | Coordinator 身份更新（擅长+痛恨+铁律） | `skills/software-project-governance/SKILL.md` | SYSGAP-032 |
| 4 | M7.4 新增 Step 4.5 审查触达检查 | `references/behavior-protocol.md` | SYSGAP-033 |
| 5 | M7.5 Step 2.5 消歧义 | `references/behavior-protocol.md` | SYSGAP-034 |

Phase 1 完成后，路由表会"告诉"Coordinator 该 spawn Reviewer，pre-commit hook 会"阻止"不审查就 commit。即使 verify_workflow.py 和 plan-tracker 尚未更新，核心的"告知+阻断"闭环已建立。

### Phase 2（0.25.1）：验证+模板

| # | 动作 | 改造文件 | 任务 ID（建议） |
|---|------|---------|---------------|
| 6 | verify_workflow.py Check 18 (agent_team_review) | `infra/verify_workflow.py` | SYSGAP-035 |
| 7 | verify_workflow.py Check 19 (agent_activation) | `infra/verify_workflow.py` | SYSGAP-036 |
| 8 | agent-dispatch-template.md 创建 | `references/agent-dispatch-template.md`（新） | SYSGAP-037 |
| 9 | M7.5 Step 2.5a Sub-agent 调度格式检查 | `references/behavior-protocol.md` | SYSGAP-038 |
| 10 | pre-commit hook 路由一致性引用 | `infra/hooks/pre-commit` | SYSGAP-039 |

Phase 2 完成后，脚本可以独立检测审查完整性——不受 Coordinator 自觉影响。调度模板确保 sub-agent 必定加载角色定义 + 任务 SKILL。

### Phase 3（0.26.0）：追踪+可视化

| # | 动作 | 改造文件 | 任务 ID（建议） |
|---|------|---------|---------------|
| 11 | plan-tracker 模板新增"审查状态"列 | `core/templates/plan-tracker.md` | SYSGAP-040 |
| 12 | plan-tracker 运行时新增"审查债务"节 | `.governance/plan-tracker.md`（Coordinator 维护） | 无独立任务——Coordinator 按模板维护 |
| 13 | G6 新增审查完整性检查项 | `core/stage-gates.md` | 与 SYSGAP-035 联动 |
| 14 | post-commit hook 新增 --no-verify 绕过审计 | `infra/hooks/post-commit` | 增量任务 |

Phase 3 完成后，用户和 Coordinator 都可以看到审查覆盖率——审查债务可视化。

---

## 影响范围

### 改造文件清单

| # | 文件 | 改造类型 | 阶段 |
|---|------|---------|------|
| 1 | `skills/software-project-governance/SKILL.md` | 路由表升级（5列）+ Coordinator 身份更新 + 调度模板引用 | Phase 1 |
| 2 | `skills/software-project-governance/references/behavior-protocol.md` | M7.4 新增 Step 4.5 + M7.5 Step 2.5 修订 + Step 2.5a 新增 | Phase 1+2 |
| 3 | `skills/software-project-governance/infra/hooks/pre-commit` | Step 7 WARN→BLOCK + 路由一致性引用 | Phase 1+2 |
| 4 | `skills/software-project-governance/infra/verify_workflow.py` | check_agent_team_review() + check_agent_activation() | Phase 2 |
| 5 | `skills/software-project-governance/references/agent-dispatch-template.md` | 新文件——调度模板 | Phase 2 |
| 6 | `skills/software-project-governance/core/templates/plan-tracker.md` | 模板新增"审查状态"列 | Phase 3 |
| 7 | `.governance/plan-tracker.md` | 运行时新增列 + 审查债务节 | Phase 3 |
| 8 | `skills/software-project-governance/core/stage-gates.md` | G6 新增审查完整性检查项 | Phase 3 |
| 9 | `skills/software-project-governance/infra/hooks/post-commit` | --no-verify 绕过审计 | Phase 3 |

### 不变的文件

- `agents/developer.md`, `agents/code-reviewer.md`, `agents/qa.md`, `agents/analyst.md`——角色定义无变更（它们的行为协议已经正确：Developer 不审查自己，Code Reviewer 被动等待调度，QA 独立于 Developer）
- `skills/stage-development/SKILL.md`, `skills/code-review/SKILL.md`——审查流程已正确定义
- `skills/software-project-governance/references/change-impact-checklist.md`——已正确要求 P0/跨层 spawn Analyst
- `skills/software-project-governance/core/lifecycle.md`——阶段定义无变更
- `skills/software-project-governance/core/profiles.md`——Profile 定义无变更（审查强度差异化通过 pre-commit hook + verify_workflow.py 实现）

### 向后兼容性

- **无 Breaking Change**——现有 plan-tracker 中的任务无需回填"审查状态"列（缺失列时 verify_workflow.py 降级为 WARN）
- **存量审查债务**——在 Phase 3 plan-tracker 新增列后，历史产品代码任务默认"审查豁免"（不追溯审查），新增任务强制执行审查状态流转
- **Lightweight profile 不受影响**——审查 BLOCK 仅对 P0 产品代码任务生效

---

## 后续动作

1. **Coordinator 审阅本 ADR**——确认 6 个堵漏方向和 3 期分期执行计划
2. **创建 10 个 SYSGAP 任务**（SYSGAP-030~040）入账 plan-tracker
3. **按 Phase 1 → Phase 2 → Phase 3 顺序执行**
4. **每个 Phase 完成后执行 check-governance + agent_team_review 验证**
5. **Phase 3 完成后**，本 ADR 的设计决策正式生效——Coordinator 铁律第 6 条强制执行
6. **发布 0.25.0/0.25.1/0.26.0**——按 Phase 分版本发布

---

## 附录 A: 决策可逆性

| 决策项 | 可逆性 | 回滚成本 |
|--------|--------|---------|
| 路由表 1:1→1:N | 高（改回 3 列表即可） | SKILL.md 一行变更 |
| pre-commit Step 7 WARN→BLOCK | 中（改回 WARN 即可） | pre-commit hook 一行变更 |
| verify_workflow.py 新检查 | 高（删除函数即可） | 删除 2 个函数 + 2 个调用 |
| Coordinator 身份更新 | 高（改回原文即可） | SKILL.md 4 行变更 |
| agent-dispatch-template.md | 高（删除文件即可） | 删除 1 个文件 |
| plan-tracker 审查状态列 | 低（数据迁移成本） | 已填充的审查状态数据需要回填或清理 |

---

## 附录 B: 与根因分析报告的对应关系

| Analyst 堵漏方向 | 本 ADR 对应方案 | 覆盖程度 |
|-----------------|----------------|---------|
| A: 路由表 1:1→1:N 后置链 | 一、路由表重设计（5列+后置审查Agent） | 完整 |
| B: Pre-commit hook WARN→BLOCK | 二、Pre-commit hook Step 7 BLOCK | 完整 |
| C: verify_workflow.py 新增检查 | 三、Check 18 + Check 19 | 完整 |
| D: Coordinator 身份更新 | 四、Coordinator 擅長+痛恨+铁律 | 完整 |
| E: Sub-agent 调度标准化 | 五、agent-dispatch-template.md | 完整 |
| F: 审查债概念入 plan-tracker | 六、审查状态列 + 审查债务节 | 完整 |

---

*本 ADR 遵循 Architect（老顾）的职责边界：只做设计方案，不写产品代码。实现留给 Developer。*
