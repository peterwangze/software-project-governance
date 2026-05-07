# ADR-004: Coordinator 分离架构设计

**日期**: 2026-05-02
**状态**: 提案（待 Coordinator 审查）
**决策人**: Architect（老顾）
**关联任务**: 待创建（建议 SYSGAP-041~050）
**前置分析**: DEC-058 (Agent Team 协议强制执行缺陷分析)、DEC-056 (v0.20.0 系统性缺陷分析)
**影响范围**: CLAUDE.md bootstrap、SKILL.md 入口层、agents/coordinator.md、agents/architect.md、behavior-protocol.md、interaction-boundary.md、agent-communication-protocol.md

---

## 背景

### 问题陈述

`software-project-governance` v0.24.1。根因分析发现：**Coordinator 融合在主 agent 中是"自指涉盲区"的根源**。

当前架构中，SKILL.md 加载后，主 agent **直接成为** Coordinator（老周）。Coordinator 的"铁律"——不写产品代码、必须 spawn Agent Team、不审查自己的代码——是 **prompt 文本**，不是系统约束。主 agent 天然拥有 Write/Edit/Bash 工具权限，prompt 文本挡不住工具能力。

这导致了一个结构性矛盾：
- **其他 Agent**（Developer、Reviewer、QA、Architect）是被 spawn 的独立 agent，拥有独立的 prompt 上下文、独立的工具权限声明、独立的角色身份
- **Coordinator** 是唯一"特殊"的角色——它融合在主 agent 中，与主 agent 共享同一工具权限空间。当主 agent 想"这个简单，我自己写了"时，系统层面没有任何屏障阻止它

### 违规路径分析

```
用户请求 "在 SKILL.md 中加一行"
  → 主 Agent（= Coordinator）判断："很简单，一行 Markdown"
    → 工具权限检查：Write/Edit ✅ 可用
      → "这个简单我自己写" ← 系统层面零屏障
        → 绕过 Agent Team
          → 绕过 Code Reviewer
            → 绕过影响分析
              → 违反 Producer-Reviewer 分离
```

DEC-058 已通过四层堵漏体系（路由层 + 阻断层 + 验证层 + 身份层）修补了 Agent Team 审查缺失的问题。但 **Coordinator 融合模型本身** 是更深层的架构问题——它不在 DEC-058 的修补范围内，因为 DEC-058 修补的是"Coordinator 完成了执行后忘了 spawn Reviewer"，而非"Coordinator 不应该亲自执行"。

### 设计约束

1. **AskUserQuestion 独占**：Claude Code 平台约束——sub-agent **不能**使用 AskUserQuestion。用户交互的唯一合法渠道只在主 agent
2. **工具权限无系统级差异**：主 agent 和 sub-agent 都拥有 Write/Edit/Bash。分离后 Coordinator 如果被 spawn，在系统层面 **仍然**可以 Write——只能靠 prompt 约束，和现在一样
3. **Sub-agent 状态不持久**：spawn 的 sub-agent 在返回结果后终止。跨交互的协调需要多次 spawn，每次需要完整上下文
4. **CLAUDE.md bootstrap 必须在主 agent**：bootstrap（读 plan-tracker、SELF-CHECK）是首次加载行为，无法委托给 sub-agent
5. **不引入新的架构层**：改造必须在现有六层架构内完成（适配层→入口层→业务智能层→能力层→基础设施层→核心层）

---

## 备选方案评估

### 评估标准（评估前定义）

| 标准 | 权重 | 说明 |
|------|------|------|
| **自指涉盲区消除度** | 最高 | 能否阻止主 agent 自我赋予绕过 Agent Team 的权力 |
| **用户交互效率** | 高 | 新增的 spawn 往返是否显著增加延迟 |
| **跨会话状态管理** | 高 | Coordinator 状态能否在多次交互间保持 |
| **系统级强制执行** | 中 | 能否从 prompt 约束升级为系统约束 |
| **现有体系兼容性** | 中 | 与 6 层架构、bootstrap、hook、verify 的兼容 |
| **实现复杂度** | 中 | 改造的文件数和迁移成本 |

---

### 方案 A：薄代理模型（Thin Proxy）

**核心思路**：主 agent 退化为"用户代理（User Proxy）"——只负责 bootstrap + 用户 I/O + spawn Coordinator。所有协调/治理/路由决策全部委托给 spawned Coordinator。

```
┌─────────────────────────────────────┐
│              主 Agent               │
│  ┌─ Bootstrap (SELF-CHECK)         │
│  └─ AskUserQuestion (唯一)         │
│  ┌─ Spawn Coordinator ──────────┐  │
│  │  返回结构化结果               │  │
│  └─ 呈现给用户                  │  │
│  ┌─ 按 Coordinator 指令 spawn   │  │
│  │  Developer / Reviewer / ...  │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
         │  spawn
         ▼
┌─────────────────────────────────────┐
│     Coordinator (spawned agent)     │
│  ┌─ 接收任务 + 上下文              │
│  ├─ 分解任务 (子任务 DAG)          │
│  ├─ 路由 Agent (查路由表)          │
│  ├─ 设定 Gate 验收标准             │
│  └─ 返回: 协调计划 (JSON/Markdown) │
│  ┌─ 工具: Read/Write(.governance/) │
│  ├─ 工具: Grep/Glob                │
│  ├─ ❌ 工具: AskUserQuestion        │
│  └─ ❌ 工具: Edit (产品代码)        │
└─────────────────────────────────────┘
```

#### 主 agent 新身份：User Proxy（用户代理）

- **职责**：bootstrap 执行、读 plan-tracker、SELF-CHECK、用户 I/O、spawn Coordinator、按 Coordinator 指令 spawn 执行 Agent
- **铁律**：
  1. 不自行判断任务如何分解——等待 Coordinator 返回的协调计划
  2. 不自行选择 spawn 哪个 Agent——严格按 Coordinator 指令
  3. 不自行修改治理决策——Coordinator 返回的决策是权威
  4. 不自行判断"这个简单我自己做"——所有产品代码修改必须通过 Coordinator 路由的 Agent Team
- **工具**：Read ✅、Write ✅ (.governance/)、AskUserQuestion ✅、Agent ✅、Grep ✅、Glob ✅、Edit ❌、Bash ❌

#### Coordinator 新身份：Orchestrator（编排器）

- 从 `agents/coordinator.md`（当前标记 DEPRECATED）重新激活并增强
- **工具**（prompt 层约束）：Read ✅、Write ✅ (.governance/decision-log.md + docs/)、Grep ✅、Glob ✅、Edit ❌、Bash ❌、AskUserQuestion ❌、Agent ❌ (Coordinator 不递归 spawn——它输出协调计划让主 agent spawn)
- **新增权限**：Agent 工具 ✅（有限——Coordinator 可以 spawn 自己的子 agent 做分析，但不能做最终决策）

#### 用户交互协议

Coordinator 需要用户输入时，通过结构化消息格式返回给主 agent：

```
COORDINATOR_NEEDS_INPUT:
  type: "confirm" | "select" | "input"
  context: "我们有两个候选架构方案..."
  options:
    - id: "A"
      label: "方案A: 薄代理模型"
      description: "..."
    - id: "B"
      label: "方案B: 混合委托模型"
      description: "..."
  default: "A"
  priority: "critical" | "normal"
```

主 agent 收到此消息后，**MUST** 转换为 AskUserQuestion 调用呈现给用户。用户回复后，主 agent 在下次 spawn Coordinator 时将用户答案注入上下文。

#### 理由

- 主 agent 身份从"什么都管的 Coordinator"简化为"听话的代理"——减少"我自己做"的内在激励
- Coordinator 作为独立 spawned agent，在身份层面与 Developer 同级——都是"被调用的角色"，不是"什么都能做的主人"
- 用户体验不变——AskUserQuestion 仍在主 agent 层，用户感知不到 Coordinator 是 spawned agent

#### 缺陷

- **状态断裂**：Coordinator 每次 spawn 是独立的——需要用户交互意味着 Coordinator 终止，下次 spawn 需要完整上下文重建
- **效率损失**：每个决策都需要至少一次 spawn 往返。简单任务（"在 plan-tracker 补一个任务条目"）从直接执行变为 spawn → 返回 → 执行
- **递归 spawn 控制复杂**：Coordinator spawn Architect（分析）→ Architect 返回方案 → Coordinator spawn Design Reviewer（审查）→ Design Reviewer 返回 → Coordinator 返回给主 agent → 主 agent 呈现给用户。如果用户在查看方案后想修改——需要重新 spawn 整个链
- **Coordinator 仍可 Write**：系统层面无差异——如果 Coordinator prompt 写得不够强，它仍然可以绕过规则

---

### 方案 B：混合委托模型（Hybrid Delegation）

**核心思路**：主 agent 保留"薄 Coordinator"身份——处理简单治理操作（入账 plan-tracker、写 evidence-log、简单路由）。复杂多 agent 编排（开发+审查链、影响分析+设计审查链）spawn 独立 Coordinator 编排。

```
┌───────────────────────────────────────────┐
│                主 Agent                    │
│  ┌─ Bootstrap (SELF-CHECK)                │
│  ├─ AskUserQuestion (唯一)                │
│  ├─ 薄治理: plan-tracker 更新、证据写入   │
│  ├─ 简单路由: 代码审查→spawn Code Reviewer│
│  │          架构决策→spawn Architect       │
│  └─ 复杂编排: spawn Coordinator ───────┐  │
│     接收协调计划，按指令 spawn Agent Team │  │
└───────────────────────────────────────────┘
         │  spawn (only for complex workflows)
         ▼
┌───────────────────────────────────────────┐
│       Coordinator (spawned agent)         │
│  仅在以下场景 spawn:                       │
│  - P0 任务 + >=2 个 Agent 的编排链       │
│  - 跨层变更影响分析链                     │
│  - 关键架构决策 + 设计审查链              │
│  - 发布流水线 (QA+DevOps+Release+Review) │
│  工具: Read/Write(.governance/)/Grep/Glob │
│  ❌ Edit / ❌ Bash / ❌ AskUserQuestion     │
└───────────────────────────────────────────┘
```

#### 主 agent 新身份：Project Host（项目主机）

- **直接处理**（不 spawn Coordinator）：
  - 读/写 `.governance/` 治理记录
  - 简单单 Agent spawn（代码审查请求、设计审查请求、bug fix 等单 agent 任务）
  - Session 管理（plan-tracker 更新、evidence-log 补录、session-snapshot 生成）
  - 验证命令执行（verify_workflow.py check-governance）
  - Git commit/push
- **必须 spawn Coordinator**：
  - P0 任务涉及 >=2 个 Agent 的编排（如"开发 + 代码审查 + 测试审查"链）
  - 跨层变更影响分析（需要 Analyst + Architect 协作）
  - 关键架构决策（需要 Architect + Design Reviewer 链）
  - 发布流水线编排（QA + DevOps + Release + Release Reviewer）
  - 任何任务模糊、需要多步骤分解的情况

#### 判断规则

```
if task.agent_count >= 2 or task.priority == "P0" and task.cross_layer:
    spawn Coordinator
else:
    handle directly
```

#### 理由

- 保留简单操作的效率——大部分治理操作不需要 spawn 开销
- 在复杂场景引入"强制执行的分工"——Coordinator 的 spawn 是硬性要求，主 agent 不能自己做
- 与现有 DEC-058（四层堵漏）兼容——复杂编排的审查覆盖更容易被 hook 检查（commit 包含 multi-agent 任务时，hook 检查审查证据）
- 渐进式迁移：先让复杂场景走 Coordinator，简单场景逐步收紧

#### 缺陷

- **边界模糊**："简单"vs"复杂"的判断是 prompt 文本——主 agent 可以自我合理化"这个也不算复杂"从而绕过
- **两个身份冲突**：主 agent 同时是"Project Host"和"薄 Coordinator"——"我自己做"的诱惑仍在
- **固化现状**：简单场景仍然允许主 agent 直接执行——等于承认"简单修改可以绕过 Agent Team"，与 DEC-056 Phase 1 的产品代码边界定义矛盾
- **Coordinator spawn 频率低**：大部分任务仍是简单的单 agent spawn——Coordinator 很少被激活，等于没有真正分离

---

### 方案 C：状态保持增强模型（Status Quo Enhancement）—— 不做分离

**核心思路**：保持融合模型，通过非架构手段增强约束力——hook 阻断、verify 检查、身份 prompt 强化。这是四个方案中实现成本最低、与现有体系兼容度最高的方案。

```
┌───────────────────────────────────────────┐
│         主 Agent = Coordinator            │
│  ┌─ Bootstrap + SELF-CHECK               │
│  ├─ AskUserQuestion                       │
│  ├─ 任务分解 + Agent 路由 + 治理看护     │
│  ├─ 产品代码: MUST spawn Agent Team      │
│  └─ 治理记录: 可直接操作                  │
│                                           │
│  🛡 三层防御（系统级）                    │
│  ├─ Layer 1: Pre-commit hook BLOCK       │
│  │   - 产品代码无 task ID → BLOCK         │
│  │   - P0 任务无审查证据 → BLOCK          │
│  │   - 目标一致性缺失 → BLOCK            │
│  │   - 用户影响缺失 → BLOCK              │
│  ├─ Layer 2: verify_workflow.py 追溯检查 │
│  │   - Agent Team 激活检查 (Check 18/19) │
│  │   - 审查覆盖率检查                     │
│  │   - 证据完整性检查                     │
│  └─ Layer 3: 身份 Prompt 硬化            │
│      - 铁律 MANDATORY 标记               │
│      - 产品代码边界分类表                 │
│      - 自检协议 M8                        │
└───────────────────────────────────────────┘
```

#### 增强措施

1. **Bootstrap SELF-CHECK 第 0 条新增**："我即将修改产品代码吗？是 → MUST spawn Agent Team；否 → 可继续"
2. **SKILL.md 铁律硬化**："直接修改产品代码 = 流程违规 = commit 被 pre-commit hook BLOCK"（明示系统后果）
3. **DEC-058 四层堵漏全部落地后**：pre-commit hook + verify_workflow.py 构成系统级防御网，与主 agent 的 prompt 约束形成"双层防御"
4. **Coordinator prompt 新增"反合理化"训练数据**："这个简单我自己写"这个念头出现的根因是吞吐量优化偏好——Coordinator 被显式告知：Commit 被 hook 挡住浪费的时间 > spawn Agent Team 的时间

#### 理由

- **零迁移成本**：不需要改动 bootstrap、SKILL.md 加载机制、sub-agent 调度方式
- **已有基础设施**：hook 阻断 + verify 检查 + 四层堵漏已经（或即将）就位——它们构成系统级防御，比 prompt 约束更强
- **避免"伪分离"**：方案 A/B 分离 Coordinator 到 spawned agent，在系统层面上仍然没有 Write/Edit/Bash 隔离——"分离"只是增加了 spawn 往返，没有增加真正的安全
- **状态连续**：融合模型下 Coordinator 可以在多次用户交互间保持上下文——方案 A/B 每次 spawn 都是新的上下文
- **用户无感**：不需要改变用户交互模式

#### 缺陷

- **不解决根因**：Coordinator 仍然是主 agent——"这个简单我自己写"的念头永远存在
- **完全依赖系统防御**：如果 hook 缺失、verify 被跳过——融合模型无第二道防线
- **"伪闭环"风险**：增强 prompt 后短期行为改善，但长期 agent 可能重新"适应"并绕过
- **不满足用户明确方向**：用户决策"将 Coordinator 从主 agent 中分离出来"——方案 C 是不分离

---

### 方案对比

| 评估标准 | 方案 A (薄代理) | 方案 B (混合委托) | 方案 C (现状增强) |
|---------|---------------|-----------------|-----------------|
| **自指涉盲区消除度** | 中高——主 agent 身份从"管理者"降为"代理" | 中——边界模糊，主 agent 仍有"薄 Coordinator"身份 | 低——融合模型未变，完全依赖系统防御 |
| **用户交互效率** | 低——每次决策需 spawn 往返 | 中——简单操作保留效率，复杂操作有 spawn 开销 | 高——零额外开销 |
| **跨会话状态管理** | 低——Coordinator 每次都需上下文重建 | 中——简单操作不丢状态，复杂操作有重建成本 | 高——状态自然在会话中保持 |
| **系统级强制执行** | 低——Coordinator 仍是 prompt 约束 | 低——主 agent 和 Coordinator 都是 prompt 约束 | 中——hook + verify 系统防御已就位 |
| **现有体系兼容性** | 低——需大改 bootstrap、SKILL.md、调度协议 | 中——需改动调度协议和判断逻辑 | 高——零兼容性改动 |
| **实现复杂度** | 高——10+ 文件改造 + 新协议 + 新调度模板 | 中——6-8 文件改造 + 边界判断规则 | 低——prompt 增强 + 依赖 DEC-058 落地 |
| **平台约束适应性** | 差——spawn 状态断裂问题严重 | 中——仍有状态断裂 | 好——融合模型天然无状态问题 |

---

## 决策

**采用方案 B（混合委托模型），但加入关键的硬化措施以弥补其边界模糊的缺陷。**

### 决策理由

1. **方案 A 在当前平台约束下不可行**——Coordinator 作为 spawned agent 需要频繁与用户交互（AskUserQuestion）。每次交互 = Coordinator 终止，下次需要完整上下文重建。而协调工作天然需要多次交互（分解→确认→路由→审查→交付）。方案 A 的"每次决策 spawn 一次"在架构设计、发布审批等需要多轮确认的场景中会变成"spawn→返回→spawn→返回→spawn→返回"的重复上下文重建——既不效率，也容易出错。

2. **方案 C 违背用户明确决策方向**——用户已决策"架构路线——将 Coordinator 从主 agent 中分离出来"。不做分离的方案不是"另一个选择"——是拒绝执行。

3. **方案 B 在效率和分离之间取得最优点**——简单操作保留融合模型的效率（治理记录更新、单 Agent spawn），复杂编排强制走独立 Coordinator（多 Agent 链、跨层变更、关键架构决策）。这避免了方案 A 的"连写一行 evidence-log 都要 spawn Coordinator"的过度分离，也避免了方案 C 的"什么都没变"。

4. **承认残余风险**——在当前平台约束下（sub-agent 仍有 Write/Edit/Bash），分离 **不能** 在系统层面创建工具隔离。分离的 **实际价值** 在于：
   - 主 agent 身份简化（从"全能 Coordinator"到"Project Host + 薄治理"）→ 减少"这个简单我自己做"的内在激励
   - 复杂编排场景中，Coordinator 作为独立 agent 编排 → 编排计划可被主 agent 记录和审查 → pre-commit hook 可检查复杂编排的审查覆盖率
   - 主 agent 违反协议时（跳过 Coordinator 直接执行复杂编排），hook/verify 可以检测并 BLOCK

5. **与 DEC-058 互补，不重叠**——DEC-058 解决"执行完成后忘了 Review"，本方案解决"是否应该亲自执行"。两者覆盖不同的漏洞层面。

### 核心设计原则

- **简单操作：主 agent 直接处理。** 治理记录读写、单 Agent spawn、验证命令、git 操作
- **复杂编排：MUST spawn Coordinator。** P0 + 多 Agent 链、跨层变更、关键架构决策、发布流水线
- **强制性判定表**（定义在 SKILL.md 和 behavior-protocol.md 中——不是 prompt 建议，是 MUST 规则）
- **hook 检查**：复杂编排场景无 Coordinator 参与证据 → BLOCK（与 DEC-058 的 pre-commit Step 7 协同）

---

## 详细设计

### 一、目标架构图

```
                             用户
                              │
                              │ AskUserQuestion
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     主 Agent                               │
│                   Project Host（项目主机）                    │
│                                                             │
│  ┌───────────────────────────────────────────────────┐    │
│  │  Bootstrap (CLAUDE.md)                            │    │
│  │  Step 0: 双维度模式 → Step 0.5: 身份确定          │    │
│  │  Step 1: plan-tracker → Step 2: 交叉验证           │    │
│  │  Step 3: 阶段跳跃防护 → Step 4: 优先级确认         │    │
│  └───────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─ 职责 ─────────────────────────────────────────┐       │
│  │  ✅ 用户交互 (AskUserQuestion)                  │       │
│  │  ✅ Bootstrap 执行 + 治理状态读取                │       │
│  │  ✅ .governance/ 治理记录直接写入                │       │
│  │  ✅ 简单单 Agent spawn (代码审查请求等)          │       │
│  │  ✅ Session 管理 (快照/commit/push)              │       │
│  │  ✅ 验证命令执行 (verify_workflow.py)            │       │
│  │  ✅ 按 Coordinator 指令 spawn Agent Team         │       │
│  └────────────────────────────────────────────────┘       │
│                                                             │
│  ┌─ 铁律 ─────────────────────────────────────────┐       │
│  │  1. 复杂编排 MUST spawn Coordinator            │       │
│  │  2. 不自行分解多 Agent 任务                     │       │
│  │  3. 不自行做架构决策                            │       │
│  │  4. 不修改产品代码 (MUST spawn Agent Team)      │       │
│  │  5. Sub-agent 不与用户交互                      │       │
│  └────────────────────────────────────────────────┘       │
│                                                             │
│  ┌─ 工具 ─────────────────────────────────────────┐       │
│  │  Read ✅  AskUserQuestion ✅  Agent ✅          │       │
│  │  Write ✅ (.governance/ + docs/)                 │       │
│  │  Edit ❌ (产品代码)  Bash ⚠️ (仅验证命令)        │       │
│  └────────────────────────────────────────────────┘       │
└────────────┬────────────────────────────────────────────────┘
             │
             │ spawn (仅复杂编排场景)
             │ Agent(description="COORD-xxx: ...",
             │       prompt=coordinator_template + task_context)
             ▼
┌─────────────────────────────────────────────────────────────┐
│              Coordinator Agent (spawned)                     │
│                Orchestrator（编排器）                         │
│                                                             │
│  ┌─ 职责 ─────────────────────────────────────────┐       │
│  │  ✅ 任务分解 (子任务 DAG + 依赖关系)            │       │
│  │  ✅ Agent 路由 (查路由表，确定执行+审查链)       │       │
│  │  ✅ Gate 设定 (每个子任务的验收标准)            │       │
│  │  ✅ 返回结构化协调计划给主 agent                │       │
│  │  ✅ 写入决策记录 (.governance/decision-log.md)  │       │
│  │  ✅ 写入架构文档 (docs/architecture/)           │       │
│  └────────────────────────────────────────────────┘       │
│                                                             │
│  ┌─ 铁律 ─────────────────────────────────────────┐       │
│  │  1. 不修改产品代码 (Edit/Bash 禁止用于产品路径) │       │
│  │  2. 不直接 spawn 执行 Agent (编排计划给主 agent)│       │
│  │  3. 不与用户直接交互 (无 AskUserQuestion)       │       │
│  │  4. 所有判断必须有 ADR 记录                    │       │
│  └────────────────────────────────────────────────┘       │
│                                                             │
│  ┌─ 工具 ─────────────────────────────────────────┐       │
│  │  Read ✅  Write ✅ (.governance/ + docs/)        │       │
│  │  Grep ✅  Glob ✅                               │       │
│  │  Edit ❌ (产品代码)  Bash ❌  Agent ❌           │       │
│  │  AskUserQuestion ❌                             │       │
│  └────────────────────────────────────────────────┘       │
│                                                             │
│  ┌─ 输出格式 ─────────────────────────────────────┐       │
│  │  coordination_plan: {                          │       │
│  │    task_id, task_dag, agent_routing,           │       │
│  │    gate_criteria, dependencies,                │       │
│  │    review_chain, escalation_contacts,          │       │
│  │    user_decisions_needed (optional)            │       │
│  │  }                                              │       │
│  └────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
         │
         │ 主 agent 按 coordination_plan 执行:
         │ 1. 按 agent_routing 逐个 spawn 执行 Agent
         │ 2. 完成后按 review_chain spawn 审查 Agent
         │ 3. 收集所有产出，验证 gate_criteria
         │ 4. 若有 user_decisions_needed → AskUserQuestion
         │ 5. 全部通过 → commit + 更新 plan-tracker
         ▼
┌─────────────────────────────────────────────────────────────┐
│              Agent Team (按计划 spawn)                       │
│                                                             │
│  Developer ←→ Code Reviewer                                │
│  QA ←→ Test Reviewer                                       │
│  Architect ←→ Design Reviewer                              │
│  DevOps / Release / Maintenance / Analyst                   │
│                                                             │
│  所有产品代码修改 → Developer (spawned)                     │
│  所有审查 → Reviewer agents (spawned)                      │
│  审查分离: Developer NEVER 审查自己, Reviewer NEVER 改代码  │
└─────────────────────────────────────────────────────────────┘
```

### 二、Hard Boundary（复杂编排判定表）

以下判定表定义在 `behavior-protocol.md` M7.5 Step 2.5b，是 **MUST 规则**，不是参考建议：

| 场景 | 执行方式 | 理由 |
|------|---------|------|
| 治理记录更新（plan-tracker/evidence-log/decsion-log/risk-log/session-snapshot） | 主 agent 直接执行 | 属于治理记录路径，非产品代码 |
| docs/architecture/ 写入 | 主 agent 直接执行 | 治理记录路径 |
| 单 Agent spawn（代码审查、设计审查、需求审查等用户直接请求） | 主 agent 直接 spawn | 任务类型 1:1 映射，无分解需求 |
| **P0 任务 + 涉及 >=2 个执行 Agent** | **MUST spawn Coordinator** | 多 Agent 编排需要完整的依赖分析+路由+Gate 设定 |
| **跨层变更（修改涉及 >=2 个架构层）** | **MUST spawn Coordinator** | 需要影响分析 + 多 Agent 协作 |
| **关键架构决策（技术栈选择/模块拆分/接口设计）** | **MUST spawn Coordinator** | 架构决策需要 Architect → Design Reviewer 链 + ADR |
| **发布流水线（>=3 个 Agent：QA+DevOps+Release+Reviewer）** | **MUST spawn Coordinator** | 多阶段编排 + 多审查链 |
| **任务模糊、无明确 Agent 对应** | **MUST spawn Coordinator** | 需要 Coordinator 分解+路由 |
| 产品代码修改（任意复杂度） | **MUST spawn Developer agent** | 产品代码边界规则——与 Coordinator 无关 |

### 三、用户交互协议

#### 3.1 主 agent 作为唯一 AskUserQuestion 持有者

Coordinator 不需要 AskUserQuestion——它在 spawn 时接收完整任务上下文，产出 `coordination_plan`。如果协调计划中包含需要用户确认的决策点，Coordinator 在 `coordination_plan.user_decisions_needed` 中列出。

#### 3.2 Coordinator 输出：coordination_plan 格式

```markdown
## Coordination Plan: {TASK_ID}

### Task DAG
task_A (Developer: 实现 X) ──→ task_B (Code Reviewer: 审查 X)
task_C (QA: 测试 X) ──→ task_D (Test Reviewer: 审查测试)

### Agent Routing
| Step | Agent | Task | Input | Output | Gate |
|------|-------|------|-------|--------|------|
| 1 | Developer | 实现 X 模块 | docs/architecture/ADR-X.md | skills/stage-development/... | lint+test+coverage all green |
| 2 | Code Reviewer | 审查 Step 1 | Step 1 diff | review report (APPROVED/NEEDS_CHANGE/BLOCKED) | No BLOCKING issues |
| 3 | QA | 测试策略 | Step 1 output + requirements | test strategy doc | 覆盖所有 AC |
| 4 | Test Reviewer | 审查 Step 3 | Step 3 doc | review report | — |

### Review Chain
Developer → Code Reviewer (auto)
QA → Test Reviewer (auto)

### Gate Criteria
- Step 1: lint/test/coverage green + code review APPROVED
- Step 3: test strategy covers all acceptance criteria
- Step 4: test review APPROVED

### Dependencies
- Step 2 depends on Step 1
- Step 3 depends on Step 1
- Step 4 depends on Step 3

### User Decisions Needed
(如果有则需要主 agent 用 AskUserQuestion 确认)
- DECISION-1: "方案 A vs 方案 B 对 X 模块的设计选择"
- DECISION-2: "是否接受 Y 风险的缓解方案"

### ADR References
- ADR-004: Coordinator 分离架构设计

### Coordinator Evidence
- 影响分析: docs/architecture/impact-analysis-{task_id}.md
- 决策记录: .governance/decision-log.md (DEC-xxx)
```

#### 3.3 主 agent 收到 coordination_plan 后的执行流程

```
1. 读取 coordination_plan
2. IF user_decisions_needed 非空:
     → AskUserQuestion 逐项确认
     → 将用户答案回填到 coordination_plan 中
3. 按 task_dag 拓扑顺序执行:
     FOR each step IN sorted_by_dependency(plan.task_dag):
       spawn Agent(agent=step.agent, prompt=step.task + step.input + step.gate)
       等待返回
       IF 返回 NEEDS_CHANGE:
         返回给前一步 Agent 修复
       ELIF 返回 BLOCKED:
         升级——可能需重新 spawn Coordinator
       ELSE: 继续下一步
4. 所有 step 完成 → 检查 gate_criteria
5. 全部通过 → commit (引用 TASK_ID + Coordinator evidence)
6. 更新 plan-tracker (状态 → 已完成)
```

### 四、工具权限设计

#### 4.1 主 agent (Project Host)

| 工具 | 权限 | 适用范围 |
|------|------|---------|
| Read | ✅ | 全仓 |
| Write | ✅ | `.governance/**`, `docs/**`, `project/CHANGELOG.md` |
| Edit | ❌ | 禁止——产品代码留给 Developer |
| Bash | ⚠️ | 仅验证命令 (`verify_workflow.py check-governance`) 和 git 操作 |
| Grep | ✅ | 全仓 |
| Glob | ✅ | 全仓 |
| AskUserQuestion | ✅ | 唯一用户交互方式 |
| Agent | ✅ | spawn Coordinator / Developer / Reviewer / QA / DevOps / Analyst / Architect |
| WebFetch | ⚠️ | 仅参考信息查阅 |
| WebSearch | ⚠️ | 仅参考信息查阅 |

#### 4.2 Coordinator (spawned agent)

| 工具 | 权限 | 适用范围 |
|------|------|---------|
| Read | ✅ | 全仓 |
| Write | ✅ | `.governance/decision-log.md`, `docs/architecture/` |
| Grep | ✅ | 全仓 |
| Glob | ✅ | 全仓 |
| Edit | ❌ | 禁止——不写产品代码 |
| Bash | ❌ | 不执行命令 |
| Agent | ❌ | 不递归 spawn——输出协调计划给主 agent |
| AskUserQuestion | ❌ | 不与用户交互——user_decisions_needed 通过主 agent |
| WebFetch | ⚠️ | 仅技术调研 |
| WebSearch | ⚠️ | 仅技术调研 |

#### 4.3 产品代码 vs 治理记录边界（不变）

此边界在 SKILL.md 和 interaction-boundary.md 中已有定义，Coordinator 分离后**不变**：

- **产品代码**（MUST 通过 Agent Team）：`skills/**`, `agents/**`, `commands/**`, `infra/**`, `.claude-plugin/**`, `.codex-plugin/**`, `.agents/**`
- **治理记录**（主 agent + Coordinator 可直接写入）：`.governance/**`, `docs/**`, `project/CHANGELOG.md`, `project/references/**`, `project/research/**`, `project/workflows/**`

### 五、CLAUDE.md Bootstrap 改造

#### 5.1 现有 bootstrap 的 Step 0.5（当前）

```
你是 Coordinator（老周），不是单 agent。
加载 SKILL.md 后你即 Coordinator。
```

#### 5.2 改造后 bootstrap Step 0.5

```
你是 Project Host（项目主机），不是单 agent executor，也不是 Coordinator。

你的职责是：
1. 维护治理状态 (plan-tracker/evidence-log/decision-log/risk-log/session-snapshot)
2. 作为用户唯一的 AskUserQuestion 界面
3. 判定任务复杂度——简单任务直接 spawn Agent，复杂编排 MUST spawn Coordinator
4. 按 Coordinator 返回的 coordination_plan 逐个 spawn Agent 并收集产出
5. 验证 gate_criteria 全部满足后 commit

复杂编排判定：任务涉及 >=2 个执行 Agent OR 跨层变更 OR 关键架构决策 OR 发布流水线 → MUST spawn Coordinator。

你不是 Coordinator。你是 Project Host。Coordinator 是被你 spawn 的角色 agent——和 Developer、Reviewer 一样。区别仅在于 Coordinator 的任务是"编排"，不是"执行"。
```

#### 5.3 SKILL.md 入口层改造

**当前入口层**：`加载本 SKILL 后，你进入软件项目治理工作流。你是 Coordinator（老周）`

**改造后入口层**：

```markdown
加载本 SKILL 后，你进入软件项目治理工作流。你是 **Project Host（项目主机）**——不是单 agent 执行者，不是 Coordinator。

## 你的身份：Project Host

你是 Agent Team 的宿主进程。你负责：
- 维护治理状态
- 用户交互 (AskUserQuestion)
- 判定任务复杂度并路由
- **简单任务**：直接 spawn 执行 Agent (Developer / Reviewer / QA / etc.)
- **复杂编排**：spawn Coordinator Agent → 接收 coordination_plan → 按计划逐个 spawn Agent → 收集产出 → 验证 gate → commit

你是"主机"——提供运行时环境、用户界面、治理记录。
Coordinator 是"编排器"——在复杂场景中产出协调计划，由你执行。
Developer/Reviewer/QA 是"工作者"——执行具体任务，产出结果。
```

### 六、Coordinator Agent 重新激活

`agents/coordinator.md` 当前标记 DEPRECATED（AUDIT-095 将 Coordinator 人格融入入口 SKILL.md）。本方案将其**重新激活并增强**：

```markdown
---
name: software-project-governance-coordinator
description: Coordinator Agent — 编排器。复杂多 Agent 工作流编排。不执行产品代码，不与用户直接交互。
---

# Coordinator — 编排器

## 身份定位

你是 Coordinator（编排器），一个被 Project Host spawn 的角色 agent。你的唯一产出是 **coordination_plan**——一份完整的编排计划。

你不是"项目的管理者"（Project Host 才是），你不是"代码的编写者"（Developer 才是），你不是"质量的审查者"（Reviewer 才是）。你是"工作的编排者"——你把模糊任务拆成明确步骤，把 Agent 路由写好，把验收标准定清楚。

## 你擅长的事
- 把复杂任务拆成子任务 DAG——每个有明确输入、输出、验收标准、依赖关系
- 按路由表匹配执行 Agent + 审查 Agent 链
- 设定 Gate 标准——每个子任务完成后如何判定通过
- 识别需要用户决策的点——标注在 user_decisions_needed 中

## 你痛恨的事
- 模糊的任务描述——没有验收标准的任务不是任务，是坑
- 跳过后置审查——路由表写了 MUST spawn Reviewer，跳过 = 流程违规
- 直接执行——你是编排者，不是执行者。产出 coordination_plan，执行交给 Project Host

## 铁律
1. 不修改产品代码（Edit/Bash 禁止用于产品路径）
2. 不直接 spawn 执行 Agent（编排计划交给 Project Host 执行）
3. 不与用户直接交互（无 AskUserQuestion——user_decisions_needed 通过 Project Host）
4. 所有判断有 ADR 记录（写入 .governance/decision-log.md）

## 工具权限
| 工具 | 权限 | 说明 |
|------|------|------|
| Read | ✅ | 读取需求、代码、已有 ADR |
| Write | ✅ | 写 coordination_plan + ADR 到 .governance/decision-log.md + docs/architecture/ |
| Grep | ✅ | 搜索代码库 |
| Glob | ✅ | 查找文件 |
| Edit | ❌ | 不写产品代码 |
| Bash | ❌ | 不执行命令 |
| Agent | ❌ | 不递归 spawn |
| AskUserQuestion | ❌ | 不与用户直接交互 |

## 输出格式

coordination_plan 格式见 `references/agent-communication-protocol.md`。
```

### 七、与现有体系的兼容

#### 7.1 Pre-commit Hook

现有 hook Step 7（DEC-058 升级后）检查 P0 任务是否有审查证据。Coordinator 分离后新增：

```
# Step 7b: Coordinator Evidence Check (ADR-004)
# 如果 commit 包含 >=2 个执行 Agent 产出的任务
# MUST 有 Coordinator coordination_plan 证据
if commit_msg_contains_multi_agent_task "$COMMIT_MSG"; then
    if ! grep -q "COORD-.*coordination_plan" "$REPO_ROOT/.governance/evidence-log.md"; then
        echo "BLOCK: Multi-agent task without Coordinator coordination_plan."
        echo "See ADR-004: complex orchestration MUST spawn Coordinator."
        exit 1
    fi
fi
```

#### 7.2 verify_workflow.py

新增检查：

```
# Check 20: Coordinator Evidence Chain
# 对每个复杂编排任务（>=2 Agent），evidence-log 中 MUST 有 Coordinator 条目
```

#### 7.3 Agent 分发路由表

路由表新增一行：

```
| 复杂编排 (>=2 Agent / 跨层 / 架构决策 / 发布) | Coordinator (spawned by Project Host) | 管理组 | coordination_plan → Project Host 执行 |
```

#### 7.4 Agent 通信协议

`agent-communication-protocol.md` 新增 Coordinator I/O 契约：

```
### Coordinator (编排器)

**Input**:
```
Task: {task_id} — {description}
Task Context: {需求/设计文档/约束}
Existing Plan: {plan-tracker 相关条目}
Constraints: {复杂编排判定条件——为什么需要 Coordinator}
```

**Output**:
```
- coordination_plan (Markdown/结构化):
  - task_dag (子任务依赖图)
  - agent_routing (每步: Agent + Task + Input + Output + Gate)
  - review_chain (执行→审查对)
  - gate_criteria (完成判定标准)
  - dependencies (前置依赖)
  - user_decisions_needed (可选——需要用户确认的点)
  - adr_references (相关架构决策)
- Evidence entries → .governance/evidence-log.md
- Decision record → .governance/decision-log.md (如有新决策)
```
```

### 八、迁移路径

#### Phase 1: 身份定义 (0.25.0)

- [ ] **SYSGAP-041**: 重新激活 `agents/coordinator.md`——Coordinator 角色定义（编排器）
- [ ] **SYSGAP-042**: CLAUDE.md bootstrap Step 0.5 改造——"你是 Project Host" 替换 "你是 Coordinator"
- [ ] **SYSGAP-043**: SKILL.md 入口层改造——Coordinator 人格移除，替换为 Project Host 身份 + 复杂编排判定表
- [ ] **SYSGAP-044**: behavior-protocol.md M7.5 新增 Step 2.5b——复杂编排判定表（MUST 规则）

#### Phase 2: 协议和工具 (0.25.1)

- [ ] **SYSGAP-045**: agent-communication-protocol.md 新增 Coordinator I/O 契约 + coordination_plan 格式
- [ ] **SYSGAP-046**: interaction-boundary.md 新增 Project Host 交互分类
- [ ] **SYSGAP-047**: 产品代码 vs 治理记录边界——确认 Coordinator 可访问范围

#### Phase 3: 系统防御 (0.26.0)

- [ ] **SYSGAP-048**: pre-commit hook 新增 Step 7b——Coordinator Evidence Check
- [ ] **SYSGAP-049**: verify_workflow.py 新增 Check 20——Coordinator Evidence Chain
- [ ] **SYSGAP-050**: behavior-protocol.md M8 自检协议新增 Coordinator spawn 检查项

#### Phase 4: 实战验证

- [ ] 至少 3 个复杂编排场景走通 Coordinator → coordination_plan → Project Host 执行 → hook 验证的完整链路
- [ ] 验证简单场景仍保持效率（治理记录更新、单 Agent spawn 不走 Coordinator）
- [ ] 验证 hook Step 7b 在缺少 Coordinator 证据时正确 BLOCK

---

## 残余风险与缓解

### 风险 1: 分离不能创建系统级工具隔离

**严重级别**: P0
**描述**: Spawned Coordinator 在系统层面仍然拥有 Write/Edit/Bash 工具权限。与主 agent 一样，只能靠 prompt 约束限制这些工具的使用。
**影响**: Coordinator 如果 prompt 被忽略，仍然可以写入产品代码。分离在系统安全性上没有增益。
**缓解**:
1. Pre-commit hook Step 7b 检查——如果 Coordinator 产出了产品代码变更，hook BLOCK（Coordinator 的 task ID 前缀 COORD-xxx + 产品代码路径 = BLOCK）
2. verify_workflow.py Check 20 追溯检查——COORD 任务 ID 关联的文件路径必须在治理记录路径内
3. Coordinator 角色定义中的工具权限表（Edit ❌, Bash ❌）是 prompt 约束——与现有融合模型相同。但区别在于：Coordinator 是"被指派做编排"的角色身份，不是"什么都能做"的主 agent 身份——prompt 的身份暗示更强
**接受**: 在当前平台约束下无法创建系统级工具隔离。接受此风险，通过 hook + verify 双重系统防御兜底

### 风险 2: 复杂编排判定边界被突破

**严重级别**: P1
**描述**: 主 agent 可能自我合理化"这个也不算复杂"从而跳过 Coordinator spawn。
**影响**: 复杂编排场景被"降级"为主 agent 直接执行——回到融合模型的问题。
**缓解**:
1. 复杂编排判定表是 MUST 规则（behavior-protocol.md），不是建议——违反 = 协议违规
2. verify_workflow.py Check 20 追溯——如果一个 >2 Agent 的任务没有 Coordinator 证据 → 检测到
3. Pre-commit hook Step 7b——多 Agent 任务无 Coordinator 证据 → BLOCK
4. 主 agent 的 Project Host 身份 prompt 强化："你不是 Coordinator"的重复声明
**接受**: Prompt 约束仍然是最主要手段。但 hook + verify 的追溯检测提供了"事后发现"的防御

### 风险 3: Coordinator spawn 的上下文重建成本

**严重级别**: P1
**描述**: 每次 spawn Coordinator 需要注入完整的任务上下文（需求、约束、已有 ADR、plan-tracker 状态）。上下文不完整 → coordination_plan 质量下降。
**影响**: 编排质量下降，可能需要多次迭代修正。
**缓解**:
1. Coordinator I/O 契约要求 Project Host 一次性注入完整上下文（见 agent-communication-protocol.md 改造）
2. Coordinator 可以 Read 全仓——缺失上下文可自行读取
3. 参考已有 ADR 和 plan-tracker 重建项目认知
**接受**: 与所有 spawned agent 面临的挑战相同（Developer 也需要完整上下文）。这是平台约束的通用问题

### 风险 4: 效率损失——简单操作的 spawn 往返

**严重级别**: P2
**描述**: 敏感度过高的判定表可能导致简单操作也被路由到 Coordinator（如用户问"下一步做什么"）。
**影响**: 响应延迟增加，用户体验下降。
**缓解**: 复杂编排判定表**排他定义**——只有明确列出的 5 类场景 MUST spawn Coordinator。不在列表内的场景主 agent 直接处理。判定表本身通过 behavior-protocol.md 的 MUST 规则定义——不容易被"宽松解读"
**接受**: 方案 B（混合委托）的设计初衷就是保留简单操作的效率。如果实际操作中误判率高，可以通过调整判定表解决

### 风险 5: 与 DEC-058 四层堵漏的重叠或矛盾

**严重级别**: P2
**描述**: DEC-058 已定义了"路由层 1:N 后置链 + 阻断层 + 验证层 + 身份层 + 跟踪层"的五层体系。本方案的 Coordinator separation 可能与 DEC-058 的路由层、身份层定义产生重叠。
**影响**: 两个方案各自定义了路由表和 Coordinator 身份——不一致可能导致 agent 困惑。
**缓解**:
1. 本方案的路由表与 DEC-058 的路由表是**互补**关系——DEC-058 路由表定义"执行 agent → 审查 agent"的配对链，本方案定义"Project Host → Coordinator"何时被触发
2. 两个方案的身份定义也不重叠——DEC-058 强化"Coordinator 必须确保审查覆盖率"，本方案强化"Coordinator 是一个被 spawn 的 agent，不是主 agent"
3. 合并两个方案的路由表和身份定义为单一事实源（一次改造同时落地）
**接受**: 两个方案都是在 SKILL.md 中落地的——Coordinator 在加载 SKILL.md 时会同时看到两个方案的内容。合并后不会矛盾

---

## 附录 A: 蓝军挑战

> 每条挑战有独立 ID 和对应缓解措施。挑战对应上文的残余风险。

| ID | 挑战描述 | 缓解措施 |
|----|---------|---------|
| BC-001 | **"Spawn Coordinator 对简单操作是浪费——主 agent 明明可以自己判断。"** 用户修改了一行配置文件，主 agent 还去 spawn Coordinator 做"编排"——这是 2 分钟的等待变成 20 秒的合理等待？ | 复杂编排判定表排他定义——只有 5 类场景 MUST spawn。配置文件修改 = Developer agent（不是 Coordinator）。M7.5 Step 2.5b 的判定表由 hook 验证——误用会被检测。 |
| BC-002 | **"Coordinator 作为 spawned agent 仍然可以 Write 产品代码——分离在安全层面是假的。"** Prompt 约束在融合模型中也存在，分离没有增加真正的系统屏障。 | 承认。在当前平台约束下无法创建系统级工具隔离。但：hook Step 7b 检查 COORD task ID 关联的文件路径范围——Coordinator 写入产品代码会被 BLOCK。分离的价值不在系统层，在身份层——Project Host 的身份暗示比融合 Coordinator 更不容易触发"我自己做"的冲动。 |
| BC-003 | **"Coordinator spawn 的频率太低——大部分任务是单 Agent 的。分离了一个很少被调用的模块有什么意义？"** 统计显示 85%+ 的任务是单 Agent spawn（代码审查请求、架构咨询等）。Coordinator 只在复杂编排场景激活——可能永远不会被充分测试。 | 正确——在简单项目中 Coordinator 很少被激活。但 (1) 在复杂项目中（本项目的 DEC-058 执行、发布流水线、跨层变更）Coordinator 被激活的频率高；(2) 即使很少被激活，它的存在本身改变了主 agent 的身份认知——"我不是 Coordinator"的声明对行为有约束力；(3) hook Step 7b 确保复杂编排场景不被绕过。 |
| BC-004 | **"Project Host + Coordinator 双层结构增加了认知负担。"** 现在 agent 需要理解两个角色——什么时候是 Host 的职责，什么时候要 spawn Coordinator。额外的模型复杂度 = 额外的违规可能。 | 判定表的清晰性（5 类场景）简化了决策——不是"判断什么是复杂"，是"对照 5 类——命中则 spawn，否则自己做"。与 DEC-058 路由表一起，构成单一的行为参考。初期认知成本存在，但长期降低"该做什么"的模糊性。 |
| BC-005 | **"如果 pre-commit hook 被 --no-verify 绕过，Coordinator 分离的所有系统防御完全失效。"** Hook 缺失 = 所有系统防御归零——Coordinator 分离不能解决这个单点故障。 | 正确。--no-verify 是所有 hook-based 防御的共同单点故障，非 Coordiantor 分离特有。缓解：(1) verify_workflow.py 追溯检查可检测 --no-verify 的历史使用模式；(2) 在未来版本中引入 CI pipeline 验证 hook 完整性；(3) 短期接受此风险——我们信任用户不会滥用 --no-verify。 |
| BC-006 | **"spawn 的 Coordinator 不能使用 Agent 工具递归 spawn——这意味着 Coordinator 不能做子编排。"** 如果编排本身很复杂（如发布流水线有 5+ Agent 需要分阶段），Coordinator 不能递归分解——只能产出一个扁平的 coordination_plan。 | 扁平 coordination_plan 对当前复杂度足够——最复杂的编排场景（发布流水线）最多涉及 4-5 个 Agent，扁平 DAG 可表达。如果未来出现递归编排需求（10+ Agent），考虑让 Coordinator 产出一个"多阶段 coordination_plan"——Phase 1 完成后 spawn 新的 Coordinator 做 Phase 2。但当前不需要。 |

---

## 附录 B: 方案适用性边界

### 本方案适用于

- `software-project-governance` v0.25.0+ 的入口层改造
- 有 Agent Team 激活场景的项目（涉及 >=2 个 Agent 的任务编排）
- Standard / Strict profile 项目（有完整的 hook + verify 基础设施）

### 本方案不适用于

- Lightweight profile 项目（无 hook、无 verify、无 Agent Team）——Coordinator 分离在无系统防御的环境中无意义
- 纯单 Agent 场景的项目——Coordinator 永远不会被激活
- 非 Claude Code 平台（其他平台可能有不同的 sub-agent 工具权限模型）——需要在对应 adapter 中评估

### 与 1.0.0 的关系

本方案是 1.0.0 之前的**架构升级**——不 blocking 1.0.0。1.0.0 的核心目标（外部验证、子工作流深度）与 Coordinator 分离是正交的。分离可以在 0.25.x 系列完成，不依赖 1.0.0 的前置条件。

---

*本 ADR 由 Architect（老顾）基于 2026-05-02 会话中的设计讨论撰写。*
*所有备选方案评估基于 Clause Code 2026-05 的 Agent 工具约束。如平台约束变化（例如 sub-agent 工具权限可差异化配置），需重新评估方案优先级。*
