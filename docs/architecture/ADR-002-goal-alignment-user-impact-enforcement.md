# ADR-002: 目标一致性与用户影响强制检查机制

**日期**: 2026-05-02  
**状态**: 提案（待 Coordinator 审查）  
**决策人**: Architect（老顾）  
**关联任务**: 待创建 SYSGAP-021~029  
**影响范围**: change-impact-checklist.md, verify_workflow.py, pre-commit hook, governance-init.md, behavior-protocol.md, audit-framework.md

---

## 背景

### 问题陈述

software-project-governance 工作流 v0.23.0 对"目标偏离"和"影响用户使用"的检查存在系统性缺口：

1. **目标一致性（无系统强制）**：`change-impact-checklist.md` 没有目标一致性检查项。`audit-framework.md` D1 在 Gate/Tier 级别触发——不在每次变更时触发。agent 可以在不做目标论证的情况下修改任何文件。

2. **用户影响（仅 agent 自觉）**：`change-impact-checklist.md` Step 3 的用户影响分析是 agent 手动执行的 checklist——可以被跳过、填写空洞答案、或完全忽略。没有脚本能检测 checklist 是否被执行。

3. **零系统强制**：所有现有机制是"文本规则 + agent 自觉"。pre-commit hook 中有 scope WARN 和 Agent Team WARN，但都不是 BLOCK。verify_workflow.py 的 10 项检查都不涵盖目标一致性和用户影响。

### 用户论点（来自需求方）

1. 过程偏离会随演进逐步放大，直到失控——必须现在阻止
2. 影响用户使用的问题会导致项目走向消亡——不允许"内部重构"借口掩盖用户体验退化
3. 当前 WARN/INFO 级别检查不足以阻止这两类问题——必须升级为 BLOCK

### 设计约束（来自需求方）

- **可脚本化判定**——不能丢给 LLM "自己判断"。必须是可以被 verify_workflow.py 脚本化检查的。脚本可以检测：checklist 是否被执行、论证是否为空、是否有对应的 evidence-log 记录。脚本不能判断论证的"质量"——但可以判断论证"是否存在"。
- **与现有体系集成**——必须改造 pre-commit hook、verify_workflow.py、change-impact-checklist、Gate 判定，而非另起炉灶。

---

## 决策

采用**三层强制体系**：agent 填表（change-impact-checklist 格式强制） + 脚本审核（verify_workflow.py 新增 Check 11/12） + hook 阻断（pre-commit hook Step 10-12 BLOCK）。

核心原则：**脚本不判断论证质量（那是 LLM 的事），只判断论证是否存在且格式合规（那是脚本的事）。**

---

## 详细设计

### 一、项目目标存储（基础设施）

**问题**：`governance-init.md` 接受 `project_goal` 作为必需参数，但当前 plan-tracker 模板不生成该字段。没有存储 = 没有机器可读的偏离检测参照物。

**方案**：在 plan-tracker `## 项目配置` 块中新增一个 grep-able 行：

```markdown
## 项目配置

- **项目名称**: {project_name}
- **项目目标**: {project_goal}
- **Profile**: {profile}
...
```

**改造文件**：`commands/governance-init.md` Step 5（plan-tracker 模板生成逻辑）

**格式约束**：`- **项目目标**: ` 后跟非空字符串（min 10 chars）。此行为 grep-able key，脚本不需要理解 Markdown 结构即可提取。

---

### 二、change-impact-checklist 增强（agent 填表层）

#### 2.1 新增 Step 3.5：目标一致性分析（在现有 Step 3 用户影响和 Step 4 架构影响之间）

```markdown
## Step 3.5: 目标一致性分析

- [ ] 读取 plan-tracker `## 项目配置` 中的 `- **项目目标**:` 字段
- [ ] 本次变更是否服务于项目目标？（MUST 回答并论证，min 30 字符）
- [ ] 如果变更引入新功能/新概念/新文件 → MUST 论证此变更如何服务于项目目标
- [ ] 如果变更与项目目标的关系不直接（如重构、基础设施改进）→ MUST 说明间接服务关系
- [ ] 论证缺失或不充分（< 30 字符）→ 本次变更将被 pre-commit hook BLOCK
```

#### 2.2 强化 Step 3：用户影响分析（从 checklist item 升级为强制格式）

保持现有四个问题，但增加**强制答案格式**：

```markdown
## Step 3: 用户影响分析

- [ ] Q1: 用户是否需要做什么来获得变更？
      答案 MUST 为以下之一：`plugin update` / `governance-init` / `governance-update` / `手动` / `自动生效（下次会话）`
- [ ] Q2: 用户如何知道变更存在？
      答案 MUST 为以下之一：`CHANGELOG` / `README` / `版本号 bump` / `不可见变更`
- [ ] Q3: 用户体验是否真的改变了？
      答案 MUST 为以下之一：`是-需迁移指南` / `是-有说明（见下文）` / `否-内部重构` / `否-治理记录`
- [ ] Q4: 变更是否需要迁移指南？
      IF Q3 = `是-需迁移指南` → MUST 提供迁移指南文件路径
      Breaking change 无迁移指南 → BLOCK
```

#### 2.3 增强 Step 5：记录（新增强制字段）

影响分析结论写入 evidence-log 时 MUST 包含两个新字段：

```
格式: EVD-XXX | TASK-ID | 影响分析 | 
范围:{文件数}文件, 
依赖:{N}引用者, 
目标对齐:{min 30 chars rationale}, 
用户影响: 获得={Q1答案}, 感知={Q2答案}, 体验变化={Q3答案}, 迁移指南={path 或 "不需要"}, 
架构影响:{无/有-详见risk-log}
```

**示例**：

```
EVD-XXX | SYSGAP-021 | 影响分析 | 
范围: governance-init.md (新增字段) + plan-tracker.md (模板), 
依赖: 无, 
目标对齐: 在 plan-tracker 中存储 project_goal 字段是实现目标一致性强制检查的基础设施——没有存储就没有机器可读的偏离检测参照物, 
用户影响: 获得=governance-init, 感知=CHANGELOG, 体验变化=否-治理记录, 迁移指南=不需要, 
架构影响: 无
```

---

### 三、verify_workflow.py 新增检查（脚本审核层）

#### 3.1 Check 11 — 目标一致性检查 (`check_goal_alignment`)

**检查逻辑**：

1. 读取 plan-tracker 中 `- **项目目标**:` 字段。如果缺失 → `[WARN] project_goal not defined in plan-tracker`
2. 扫描 evidence-log 中所有 `影响分析` 类型的条目
3. 对每条条目，检查是否包含 `目标对齐:` 字段：
   - 缺失 → `[FAIL] TASK-ID: missing 目标对齐 field in impact analysis`
   - 存在但内容 < 30 chars → `[FAIL] TASK-ID: 目标对齐 rationale too short ({N} chars < 30)`
   - 内容与非自身 task 的其他条目内容完全相同 → `[WARN] TASK-ID: 目标对齐 rationale identical to TASK-ID2 — possible template reuse`
4. 汇总：`total_checked`, `missing`, `too_short`, `duplicate`, `passed`

**输出格式**：

```
┌─ Check 11: Goal Alignment ────────────────────────────┐
│  Project goal: "构建面向AI agent的软件项目治理工作流..."
│  Impact analysis entries checked: {N}
│  [PASS] {N} entries have valid 目标对齐 field
│  [FAIL] {N} entries missing 目标对齐 field:
│    - TASK-ID1
│  [FAIL] {N} entries with 目标对齐 too short (< 30 chars):
│    - TASK-ID2 (12 chars)
│  [WARN] {N} entries have identical 目标对齐 text:
│    - TASK-ID3 same as TASK-ID4
```

#### 3.2 Check 12 — 用户影响检查 (`check_user_impact`)

**检查逻辑**：

1. 扫描 evidence-log 中所有 `影响分析` 类型的条目
2. 对每条条目，检查是否包含 `用户影响:` 字段：
   - 缺失 → `[FAIL] TASK-ID: missing 用户影响 field in impact analysis`
3. 解析 `用户影响:` 字段中的子字段：
   - `获得=` 值是否在合法集合中 → 不在 → `[FAIL] TASK-ID: invalid 获得 value`
   - `感知=` 值是否在合法集合中 → 不在 → `[FAIL]`
   - `体验变化=` 值是否在合法集合中 → 不在 → `[FAIL]`
   - `迁移指南=` 字段是否存在 → 缺失 → `[FAIL]`
4. 矛盾检测：
   - 如果 `体验变化=否-内部重构` 或 `否-治理记录`，但 diff 涉及用户可见文件（commands/**, .claude-plugin/plugin.json, CHANGELOG.md 等）→ `[WARN] TASK-ID: 体验变化 claimed '否' but diff touches user-visible files: {files}`
5. Breaking change 检测：
   - 如果 `体验变化` 值以 `是` 开头，但 `迁移指南=不需要` → `[BLOCKING] TASK-ID: breaking change claimed but no migration guide provided`
   - 如果 `体验变化` 值以 `是` 开头，且 `迁移指南={path}` 但 path 对应的文件不存在 → `[BLOCKING] TASK-ID: migration guide path '{path}' does not exist`

**输出格式**：

```
┌─ Check 12: User Impact ───────────────────────────────┐
│  Impact analysis entries checked: {N}
│  [PASS] {N} entries have valid 用户影响 field
│  [FAIL] {N} entries missing 用户影响 field:
│    - TASK-ID1
│  [BLOCKING] {N} breaking change(s) without migration guide:
│    - TASK-ID2: 体验变化=是-需迁移指南 but 迁移指南=不需要
│  [BLOCKING] {N} migration guide path(s) not found:
│    - TASK-ID3: 迁移指南=docs/missing.md (file not found)
│  [WARN] {N} 体验变化/visible files contradiction(s):
│    - TASK-ID4: claimed '否-内部重构' but modified commands/governance-status.md
```

#### 3.3 集成到 `cmd_check_governance`

在现有 Check 10 之后追加 Check 11 和 Check 12。`all_issues` 计数纳入 FAIL 和 BLOCKING 项（WARN 不计入 `all_issues`，保持现有行为一致性）。

---

### 四、pre-commit hook 增强（hook 阻断层）

在当前 9 个 Step 之后新增 3 个 Step。

#### Step 10: 目标一致性 BLOCK

```bash
# Only for product code changes
if [ "$IS_PRODUCT_CODE" -eq 1 ]; then
    # Check if project_goal exists in plan-tracker
    PROJECT_GOAL=$(grep -oP '^- \*\*项目目标\*\*: \K.+' "$REPO_ROOT/.governance/plan-tracker.md" 2>/dev/null || echo "")
    if [ -z "$PROJECT_GOAL" ]; then
        echo "WARN: project_goal not defined in plan-tracker — goal alignment check skipped"
        # WARN only — don't block for missing project_goal (bootstrapping period)
    else
        # Check if evidence-log has 目标对齐 for this task
        if [ -f "$REPO_ROOT/.governance/evidence-log.md" ]; then
            HAS_GOAL=$(grep -c "| $TASK_ID |.*目标对齐:" "$REPO_ROOT/.governance/evidence-log.md" 2>/dev/null || echo "0")
            if [ "$HAS_GOAL" -eq 0 ]; then
                echo "BLOCKED: Task '$TASK_ID' has no 目标对齐 in evidence-log."
                echo "  Every product code change MUST justify how it serves the project goal."
                echo "  Run change-impact-checklist Step 3.5 before committing."
                echo "  Emergency bypass: git commit --no-verify"
                exit 1
            fi
        fi
    fi
fi
```

#### Step 11: 用户影响 BLOCK

```bash
if [ "$IS_PRODUCT_CODE" -eq 1 ]; then
    if [ -f "$REPO_ROOT/.governance/evidence-log.md" ]; then
        HAS_USER=$(grep -c "| $TASK_ID |.*用户影响:" "$REPO_ROOT/.governance/evidence-log.md" 2>/dev/null || echo "0")
        if [ "$HAS_USER" -eq 0 ]; then
            echo "BLOCKED: Task '$TASK_ID' has no 用户影响 in evidence-log."
            echo "  Every product code change MUST answer the user impact three questions."
            echo "  Run change-impact-checklist Step 3 before committing."
            echo "  Emergency bypass: git commit --no-verify"
            exit 1
        fi
    fi
fi
```

#### Step 12: Breaking Change 迁移指南 BLOCK

```bash
if [ "$IS_PRODUCT_CODE" -eq 1 ]; then
    if [ -f "$REPO_ROOT/.governance/evidence-log.md" ]; then
        # Extract user impact line for this task
        USER_IMPACT_LINE=$(grep "| $TASK_ID |.*用户影响:" "$REPO_ROOT/.governance/evidence-log.md" 2>/dev/null || echo "")
        if echo "$USER_IMPACT_LINE" | grep -q "体验变化=是" && echo "$USER_IMPACT_LINE" | grep -q "迁移指南=不需要"; then
            echo "BLOCKED: Task '$TASK_ID' claims user experience change but no migration guide."
            echo "  Breaking changes MUST include migration instructions."
            echo "  Add migration guide path to evidence-log or correct the 体验变化 claim."
            echo "  Emergency bypass: git commit --no-verify"
            exit 1
        fi
    fi
fi
```

**BLOCK 级别总结**：

| Step | 检查项 | 级别 | 逃生口 |
|------|--------|------|--------|
| 10 | 目标一致性 argument 缺失 | BLOCK（project_goal 缺失时降级为 WARN） | `--no-verify` |
| 11 | 用户影响分析缺失 | BLOCK | `--no-verify` |
| 12 | Breaking change 无迁移指南 | BLOCK | `--no-verify` |

---

### 五、与现有体系的集成

#### 5.1 behavior-protocol.md M7.5 Step 2.6

现有文本已要求执行 change-impact-checklist。增加一句系统强制说明：

```
2.6 **变更影响分析**（仅产品代码）——
    ...
    IF 修改涉及产品代码文件 →
      MUST 执行 `references/change-impact-checklist.md` 的 Step 1-5（含 Step 3.5 目标一致性）
      影响分析结论 MUST 包含 `目标对齐:` 和 `用户影响:` 字段（格式见 checklist Step 5）
      **系统强制**: pre-commit hook Step 10-12 验证这些字段。缺失 → BLOCK commit。
      如果影响分析发现风险 → MUST 创建 risk-log 条目
```

#### 5.2 audit-framework.md D1/D2

D1（目标一致性审计）和 D2（用户视角审计）的触发机制不变（Gate/Tier/里程碑），但增加对 Check 11/12 状态的引用：

D1 检查项增加：
- (5) verify_workflow.py Check 11 是否全部 PASS？是否有目标对齐缺失的条目？

D2 检查项增加：
- (5) verify_workflow.py Check 12 是否全部 PASS？是否有 breaking change 无迁移指南的条目？

**设计原理**：D1/D2 是深度审计（agent 逐项判断语义质量），Check 11/12 是轻量级格式检查（脚本判断字段是否存在）。两者互补——Gate 时做深度审计，每次 commit 时做格式阻断。

#### 5.3 Gate 系统（stage-gates.md）

Gate 检查项新增一条（适用于 G4 之后所有 Gate）：

```
- [ ] verify_workflow.py check-governance 全部 PASS（含 Check 11 目标一致性 + Check 12 用户影响）：0 BLOCKING, 0 FAIL
```

#### 5.4 产品代码边界（无需变更）

现有的产品代码 vs 治理记录边界（SKILL.md 定义）已覆盖所有需要强制执行的文件路径。pre-commit hook Step 9 已有 `IS_PRODUCT_CODE` 判定逻辑。新 Step 10-12 复用同一判定。

---

### 六、版本规划

**目标版本**: 0.24.0 — "纪律防线 2.0：目标一致性 + 用户影响系统强制"

| 任务 ID | 阶段 | 任务 | 依赖 | 目标版本 | 优先级 |
|---------|------|------|------|---------|--------|
| SYSGAP-021 | 维护 | Plan-tracker project_goal 字段存储——governance-init.md 模板更新 | — | 0.24.0 | P0 |
| SYSGAP-022 | 维护 | change-impact-checklist 增强——Step 3.5 目标一致性 + Step 3 强化 | SYSGAP-021 | 0.24.0 | P0 |
| SYSGAP-023 | 维护 | verify_workflow.py Check 11: 目标一致性检查 | SYSGAP-022 | 0.24.0 | P0 |
| SYSGAP-024 | 维护 | verify_workflow.py Check 12: 用户影响检查 | SYSGAP-022 | 0.24.0 | P0 |
| SYSGAP-025 | 维护 | pre-commit hook Step 10-12: 目标+用户影响 BLOCK | SYSGAP-023, SYSGAP-024 | 0.24.0 | P0 |
| SYSGAP-026 | 维护 | governance-init.md plan-tracker 模板更新（project_goal 注入） | SYSGAP-021 | 0.24.0 | P0 |
| SYSGAP-027 | 维护 | behavior-protocol.md M7.5 更新——注明系统强制 | SYSGAP-025 | 0.24.0 | P1 |
| SYSGAP-028 | 维护 | 审计框架 D1/D2 更新——引用 Check 11/12 | SYSGAP-023, SYSGAP-024 | 0.24.0 | P1 |
| SYSGAP-029 | 维护 | 回归测试——verify_workflow.py 单元测试 + e2e 验证 | SYSGAP-027 | 0.24.0 | P1 |

**执行顺序**：
```
SYSGAP-021 ──→ SYSGAP-026 (plan-tracker 模板更新)
         ──→ SYSGAP-022 ──→ SYSGAP-023 (Check 11)
                         ──→ SYSGAP-024 (Check 12)
                                   └──→ SYSGAP-025 ──→ SYSGAP-027
                                                  ──→ SYSGAP-028
                                                  ──→ SYSGAP-029
```

---

### 七、备选方案与排除理由

#### 备选方案 A: "仅靠 LLM 判断"

**描述**: 让 agent 在执行 change-impact-checklist 时自行判断目标是否偏离、用户是否受影响，不依赖脚本化检查。

**排除理由**:
1. LLM 的"判断"不可审计——同一个变更，不同 agent 可能给出不同结论
2. Agent 可以声称"无影响"而脚本无法检测——这正是用户指出的"零系统强制"问题
3. 与设计约束"必须可以被 verify_workflow.py 脚本化检查"矛盾

#### 备选方案 B: "在 CI pipeline 中运行完整语义分析"

**描述**: 在 CI 中分析 commit diff，自动检测新功能是否服务于项目目标，自动判断是否影响用户。

**排除理由**:
1. 语义分析需要理解代码意图——这是 AI 的问题域，不是正则/静态分析的问题域
2. CI pipeline 能做格式验证但不能做语义判断——过度工程化
3. 引入对 LLM API 的运行时依赖——CI 的可靠性和成本无法保证

#### 备选方案 C: "把 D1/D2 审计频率从 Gate 级别改为每次 commit"

**描述**: 修改 audit-framework.md，让 D1/D2 在每次 commit 时触发（而非 Gate/里程碑）。

**排除理由**:
1. D1/D2 审计是深度检查——需要对比项目目标、逐项核查、生成审计报告
2. 每次 commit 都做完整审计 → agent 上下文爆炸 + 用户体验崩溃（每次 git commit 都要等 5 分钟审计）
3. 保留 D1/D2 在关键节点（深度），新增 Check 11/12 在每次变更时执行（轻量）——互补而非替代

#### 备选方案 D: "新增独立 command（governance-goal-check）代替 pre-commit 集成"

**描述**: 创建一个独立的 `/governance-goal-check` 斜杠命令用于目标一致性和用户影响检查，不集成到 pre-commit hook。

**排除理由**:
1. 独立命令 = agent 自觉调用——与现有 change-impact-checklist 同样的漏洞
2. 用户要求的是"系统强制"——pre-commit hook 是项目中唯一的系统级阻断点
3. 独立命令可以存在（作为手动验证工具），但不能替代 hook 阻断

---

### 八、蓝军挑战

#### 挑战 #1: "Agent 可以填空洞论证绕过 min-length 检查"

**漏洞**: Agent 填写 `目标对齐: 此变更服务于项目目标因为它是项目的一部分所以需要进行此变更确保项目正常运作。` — 31 字符，格式合规，语义完全空洞。

**风险级别**: 中

**缓解措施**:
1. **min-length >= 30 字符**（提高空洞论证的编写成本）。短论证如"服务于项目目标"（7 字符）被 BLOCK，但空洞长论证仍需更高防线。
2. **verify_workflow.py Check 11 重复模式检测**：多个任务使用相同论证文本（完全相同或编辑距离 < 5）→ 标记 `[WARN]`，提醒协调员审查。
3. **D1 审计在 Gate 时做深度检查**：Gate-level D1 是 agent 驱动的深度审计——agent 需要阅读论证内容并判断其语义有效性。Gate D1 发现空洞论证 → 创建纠偏任务 → 重新论证。
4. **交付物审查（M7.4 step 4）**：P0 任务完成后，用户看到 agent 的论证——用户可以在 AskUserQuestion 中质疑空洞论证。
5. **防线层级**：格式检查（脚本, commit 时）→ 模式检测（脚本, verify 时）→ 深度审计（agent, Gate 时）→ 人工审查（用户, 交付物确认时）

**残余风险**: 脚本无法判断语义质量——这是"可脚本化"约束的根本限制。接受此风险，依赖多层防线组合防护。

---

#### 挑战 #2: "存量项目无 project_goal → pre-commit BLOCK 所有 commit"

**漏洞**: governance-init 收集了 project_goal 但当前模板不存储它。0.24.0 升级后，存量项目的 project_goal 为空。pre-commit hook Step 10 检测到 project_goal 缺失 → 如果设计为 BLOCK，所有产品代码 commit 被阻断。

**风险级别**: 高（升级阻断风险）

**缓解措施**:
1. **project_goal 缺失时降级为 WARN**（不 BLOCK）——pre-commit hook Step 10 的 project_goal 检查逻辑：缺失 → WARN "请补充项目目标以启用目标一致性保护"，不阻断 commit。
2. **bootstrap 自升级自动补全**：版本升级时检测到 project_goal 缺失 → 通过 AskUserQuestion 提示用户补充（在 CLAUDE.md bootstrap 自升级段中）。
3. **governance-update 命令支持**：用户可以手动运行 `/governance-update` 补充 project_goal。
4. **verify_workflow.py Check 11** 在 project_goal 缺失时标记 `[WARN]` 而非 `[FAIL]`——不给存量项目制造噪音。
5. **project_goal 一旦填写 → 立即启用完整 BLOCK 保护**。

**残余风险**: 低——过渡设计充分。project_goal 缺失时 WARN 而非 BLOCK，填写后自动升级为 BLOCK。

---

#### 挑战 #3: "用户影响三问的答案过于模板化，失去实际保护价值"

**漏洞**: Agent 可以机械化填 `用户影响: 获得=自动生效（下次会话）, 感知=不可见变更, 体验变化=否-内部重构, 迁移指南=不需要` ——即使实际变更影响了用户可见行为（如改了 CLI 参数名但声称是"内部重构"）。

**风险级别**: 中

**缓解措施**:
1. **verify_workflow.py Check 12 矛盾检测**：如果 `体验变化=否-内部重构` 但 diff 涉及 commands/**, .claude-plugin/plugin.json, CHANGELOG.md → 标记 `[WARN] 体验变化 claimed '否' but diff touches user-visible files`。
2. **D2 审计在里程碑时做深度用户视角检查**：agent 需要实际测试用户路径——不是读 evidence-log，是执行用户操作。
3. **M7.4 step 4 交付物审查**：用户可看到声称的"无影响"并在确认时质疑。
4. **矛盾检测的精确性提升策略**：随着时间的推移，积累"visible files"模式——如果某类文件几乎总是与用户体验变化相关，升级其矛盾检测从 WARN 到 FAIL。

**残余风险**: 中——依赖 agent 诚实度。但这是"可脚本化"的根本限制：脚本只能检测矛盾，不能检测谎言。多层防线将谎言成本推到足够高。接受此风险。

---

#### 挑战 #4: "Pre-commit hook BLOCK 使紧急修复流程受阻"

**漏洞**: 紧急 hotfix 需要绕过所有检查快速提交。虽然有 `--no-verify` 逃生口，但如果每次紧急修复都用它，逃生口会成为常态——系统信任崩溃。

**风险级别**: 低

**缓解措施**:
1. **现有紧急 hotfix 条款**：change-impact-checklist 已有"紧急 hotfix（事后 MUST 补影响分析）"条款。这个条款在 pre-commit BLOCK 时仍然有效——用户使用 `--no-verify` + 事后补 evidence。
2. **verify_workflow.py 追责**：Check 11/12 会检测 `--no-verify` 的 commit——因为后续 check-governance 会检测到之前的 task 没有影响分析证据。标记为事后补。
3. **逃生口可审计**：post-commit hook 可以记录 `--no-verify` 使用次数 → 如果频率超过阈值 → escalation。

**残余风险**: 低——逃生口存在但可审计。

---

#### 挑战 #5: "新字段使 evidence-log 条目过长，破坏可读性"

**漏洞**: 当前影响分析条目已经很长（行内 100+ 字符）。新增 `目标对齐:` 和 `用户影响:` 字段会使单条 evidence 超过 200 字符——在 Markdown 表格中难以阅读。

**风险级别**: 低

**缓解措施**:
1. **evidence-log 的表格格式允许折行**——Markdown 表格单元格可以包含换行符。长文本自然折行不影响机器解析。
2. **verify_workflow.py 解析的是正则匹配的字段，不是表格列**——字段级别的正则解析不依赖表格排版。
3. **如果需要**，未来可以将 evidence-log 从 Markdown 表格迁移到结构化格式（JSON/YAML）。但这是长期优化——不在本次方案范围内。
4. **当前观察**：evidence-log 已有多个长条目（100-150 字符），额外的 50-80 字符不会显著恶化可读性。

**残余风险**: 极低——格式问题，不影响功能。

---

#### 挑战 #6: "Coordinator 直接写入的治理记录变更不受检查——攻击面"

**漏洞**: 治理记录（.governance/**, docs/**, project/**）是 Coordinator 直接写入的——不受 M7.5 Step 2.6 影响分析约束，不受 pre-commit BLOCK 约束。如果产品代码边界被错误定义或利用，变更可以通过"治理记录"路径绕过所有检查。

**风险级别**: 低

**缓解措施**:
1. **产品代码边界白名单足够明确**：skills/**, agents/**, commands/**, infra/**, adapter files。治理记录路径不在白名单中，也不是产品代码的替代路径。
2. **如果 infra/verify_workflow.py 被修改**——它是产品代码（在白名单中），受检查约束。这是正确的。
3. **如果 docs/architecture/ 新增了 ADR 但没有对应代码变更**——这是文档活动，不需要产品代码检查。合理。
4. **定期审查边界完整性**：纳入 D6 防护网审计维度——检查是否有产品代码通过治理记录路径被修改的案例。

**残余风险**: 低——当前边界定义充分。D6 审计提供持续看护。

---

### 九、后续动作

1. **Coordinator 审查本 ADR** → 确认或否决方案
2. **Coordinator 创建 SYSGAP-021~029 任务** → 纳入 plan-tracker
3. **Developer 按执行顺序实现**：SYSGAP-021 → SYSGAP-022 → SYSGAP-023 + SYSGAP-024 → SYSGAP-025 → SYSGAP-026~029
4. **每个 P0 任务完成后运行 verify_workflow.py check-governance** → 确保新检查不引入误报
5. **0.24.0 发布前执行完整回归**：现有 36 tests + 新增 Check 11/12 测试 + e2e 验证

---

### 十、ADR 元数据

| 属性 | 值 |
|------|-----|
| ADR 编号 | ADR-002 |
| 标题 | 目标一致性与用户影响强制检查机制 |
| 日期 | 2026-05-02 |
| 状态 | 提案（待 Coordinator 审查） |
| 决策人 | Architect（老顾） |
| 影响范围 | 6 文件改造 + 2 新 check + 3 新 pre-commit step + 1 模板更新 |
| 关联风险 | 本 ADR 蓝军挑战 #1~#6 |
| 上级文档 | 需求方要求（2026-05-02） |
| 下级任务 | SYSGAP-021~029（待创建） |
