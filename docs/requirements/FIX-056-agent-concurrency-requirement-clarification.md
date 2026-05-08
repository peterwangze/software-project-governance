# FIX-056: Agent 意外并发防护 —— 需求澄清报告

**分析日期**: 2026-05-05
**分析人**: Analyst (阿析)
**关联任务**: FIX-056
**方法论**: 需求澄清 checklist (requirement-clarification SKILL)
**前置依赖**: SYSGAP-043 (M7.6 并行调度预检)、SYSGAP-044 (Worktree 物理隔离)、agent-communication-protocol.md

---

## 1. 问题场景枚举

### 核心问题链路（用户反馈）

```
Coordinator spawn Agent A 执行 Task X
  -> Agent A 在后台执行中（正常耗时，未超时）
  -> Coordinator 主观判定"超时"
  -> Coordinator 重新拆解 Task X，spawn Agent B
  -> Agent A + Agent B 同时修改相同文件
  -> 文件修改冲突
```

### 场景分类

#### 场景 1: Coordinator 主观超时误判

**触发条件**: Agent A 执行耗时超过 Coordinator 的"预期时间"，但 Agent A 仍在正常运行（LLM API 返回慢、推理时间长、文件操作多）。

**根本原因**: Coordinator 没有客观的超时判定机制——它基于自己的主观感知判断 Agent 是否"应该已经完成了"。当 Agent A 花了比预期更长的时间（例如 30 秒 vs 预期的 10 秒），Coordinator 可能错误地认为 Agent 已经"丢失"或"卡住"。

**典型表现**: 
- Agent A 在 spawn 后 15 秒未返回 → Coordinator 判定超时
- 实际上 Agent A 正在处理大文件的 multi-step 修改
- Coordinator 重新 spawn Agent B 执行同一任务

**数据点**: 当前 agent-communication-protocol.md 的"Agent 丢失/超时"行无超时阈值定义——Coordinator 自行判断"多久算超时"。

#### 场景 2: 用户干预导致的重复 spawn

**触发条件**: 用户在 Agent A 执行中修改了任务描述或需求，Coordinator 认为"上一轮指令已过时"，直接重新 spawn 而不等 Agent A 完成。

**根本原因**: Coordinator 缺乏"取消已运行 Agent"的机制。当用户追加新指令时，Coordinator 无法通知 Agent A "你的任务已废弃，请停止"。

**典型表现**:
- 用户: "在 SKILL.md 里加一段规则"
- Coordinator spawn Agent A
- 用户: "等等，也改一下 behavior-protocol.md"
- Coordinator 将需求合并为 Task X'，spawn Agent B 执行合并后的任务
- Agent A 仍在执行原始的 SKILL.md 修改

#### 场景 3: 网络/平台延迟导致的伪超时

**触发条件**: Agent 平台 (Claude Code / Codex) 的 agent spawn 返回延迟高，Coordinator 错误推断为"agent 调用失败"而重试。

**根本原因**: Coordinator 将"Agent 平台响应慢"误判为"Agent 调用超时或失败"。实际上 Agent 已经成功 spawn 并开始执行。

**典型表现**:
- Coordinator 调用 `Agent(description="TASK-X: ...", ...)` 
- 平台侧因负载高，spawn 确认延迟 20 秒
- Coordinator 认为 spawn 失败，重试 → 重复 spawn

#### 场景 4: 部分产出后超时误判

**触发条件**: Agent A 已完成部分文件修改（Write 了 3 个文件中的 1 个），但整体进度慢。Coordinator 误判超时，spawn Agent B 从头开始。

**根本原因**: 没有 Agent 进度反馈机制——Coordinator 看不到 Agent A 的部分产出。Agent A 已修改的文件和 Agent B 即将修改的文件有重叠。

**典型表现**:
- Agent A 修改了 `SKILL.md`（完成）→ 正在修改 `behavior-protocol.md`（进行中）
- Coordinator spawn Agent B → Agent B 也开始修改 `SKILL.md`（已改完）和 `behavior-protocol.md`
- `SKILL.md` 被两个 Agent 同时写入 → 损坏

#### 场景 5: 多 Agent 并行调度 + 单 Agent 超时误判

**触发条件**: Coordinator 并行 spawn Agent A (Task X) + Agent B (Task Y)。Agent A 正常执行中，Agent B 很快完成。Agent A 延迟导致 Coordinator 认为 A 超时 → spawn Agent C 重新执行 Task X。

**根本原因**: SYSGAP-043 预检在 spawn 时做了一次性文件目标检查。并行时 Task X 和 Task Y 文件目标不重叠 → 预检通过。但后续 Agent C 与仍在运行的 Agent A 文件目标完全重叠 → 预检未覆盖此时间点。

这个场景的关键在于: SYSGAP-043 的预检只覆盖"同时 spawn 的时刻"，不覆盖"后续补充 spawn"。

### 场景总结表

| 场景 | 触发条件 | 关键因果 | 冲突类型 |
|------|---------|---------|---------|
| 1. 主观超时 | 耗时 > 预期 | 无客观超时判定 | 同任务重复执行 |
| 2. 用户干预 | 需求变更未取消旧 Agent | 无 Agent 取消机制 | 新旧需求冲突 |
| 3. 平台延迟 | spawn 确认慢 | 无"已 spawn 但未响应"状态 | 重复 spawn |
| 4. 部分产出后超时 | 部分完成但整体慢 | 无进度反馈 | 已修改文件覆盖 |
| 5. 并行+单超时 | 并行中的单 Agent 慢 | 预检只在 spawn 时刻做一次 | 补充 spawn 与运行中 Agent 重叠 |

---

## 2. 影响范围

### 2.1 最容易受影响的任务类型

| 任务类型 | 风险等级 | 原因 |
|---------|---------|------|
| **多文件修改任务** | 高 | 执行时间长，更容易触发 Coordinator 的主观超时判据 |
| **复杂代码重构** | 高 | 需要长序列推理步骤，耗时不可预测 |
| **跨层变更** | 高 | 涉及多个架构层文件，修改范围广 |
| **SKILL.md / behavior-protocol.md 修改** | 高 | 产品代码核心文件，多个 Agent 可能同时编辑 |
| **Agent 角色定义修改** | 中高 | agents/ 目录下文件，涉及多个角色定义 |
| **P0 任务** | 中高 | Coordinator 对 P0 任务有紧迫感，更容易误判超时 |
| **单文件简单修改** | 低 | 执行时间短，误判概率低 |
| **只读分析任务 (Analyst/Architect)** | 极低 | 不修改文件，无写冲突 |

### 2.2 冲突概率最高的条件组合

**必要条件（全部满足 = 高风险）**:
1. 任务涉及修改产品代码文件（有 Write 操作）
2. Agent 执行时间超过 Coordinator 的心理预期阈值
3. Coordinator 没有 Agent 存活状态查询机制
4. Coordinator 得到用户确认（或自主判断）后允许重新 spawn

**放大因子**:
- 两个修改 Agent 的目标文件完全重叠（同一文件）→ 文件损坏概率最高
- 两个修改 Agent 的目标文件部分重叠 → 部分损坏
- 项目文件数量少（高度集中）→ 重叠概率天然高

### 2.3 影响量化估算

| 后果 | 严重级别 | 可恢复性 | 说明 |
|------|---------|---------|------|
| 文件内容损坏 | P0 | 低——需手动修复 | 两个 Agent 的 Write 操作交叉写入 → 文件内容不可预测 |
| 逻辑不一致 | P0 | 低 | Agent A 的修改和 Agent B 的修改可能基于不同的前提 |
| 用户信任受损 | P1 | 中 | 用户看到"完成了两次但结果不对"→ 对工作流可靠性产生怀疑 |
| 时间浪费 | P1 | — | Agent A 的工作成果被 Agent B 覆盖或破坏 |
| 治理记录混乱 | P2 | 中 | evidence-log 中两个 Agent 都声称完成了同一任务 |

---

## 3. 边界条件

### 3.1 Agent 真超时 vs 伪超时 —— 如何区分？

**真超时**: Agent 确实已经停止执行（LLM API 超时、进程被终止、平台侧错误）。
**伪超时**: Agent 仍在运行，只是比 Coordinator 预期慢。

**区分信号**:

| 信号 | 真超时 | 伪超时 | 可获取性 |
|------|--------|--------|---------|
| Agent 返回了结果 | 否 | 是（终将返回） | 事后才能确定 |
| Agent 已开始修改文件 | 不确定 | 是 | 可通过 git status 检测 |
| Agent 仍在消费 token | 否 | 是 | 平台侧（Coordinator 不可见） |
| spawn 时的平台确认 | 可能无 | 有 | 返回了 call_id 或类似标识 |
| 任务进度（部分产出） | 无 | 可能有 | git diff 可检测 |

**关键发现**: Coordinator 当前**没有能力**区分真超时和伪超时。agent-communication-protocol.md line 104 的"Agent 丢失/超时 → 重新 dispatch"规则基于一个未验证的前提：Coordinator 能可靠地判断 Agent 是否真的超时了。

### 3.2 Agent 已在修改 vs 还在规划 —— 不同阶段的冲突风险

| Agent 阶段 | 文件修改状态 | 冲突风险 | 检测方式 |
|-----------|------------|---------|---------|
| 加载角色定义+SKILL | 无修改 | 无风险 | — |
| 通读目标文件 | 无修改 | 无风险 | — |
| 规划修改方案 | 无修改 | 风险累积中 | — |
| **执行第一次 Write** | 已开始修改 | **高风险** | git diff / git status |
| 执行中间 Write | 部分修改中 | **最高风险** | git status 可检测 |
| 自检验收 | 修改完成，待自检 | 高风险（写回完成） | git diff 可见最终状态 |
| 返回结果给 Coordinator | 修改已完成 | 中风险（竞争条件） | Agent 返回消息 |

**关键发现**: Agent 从"规划"阶段进入"Write"阶段后，文件冲突风险从零跳到高。但 Coordinator 无法区分 Agent 当前处于哪个阶段。

### 3.3 单 Agent vs 多 Agent 并行 —— 场景差异

| 维度 | 单 Agent | 多 Agent 并行 |
|------|---------|-------------|
| **冲突源** | 超时误判 → 重复 spawn 同一任务 | 超时误判 + 并行调度的文件目标重叠 |
| **SYSGAP-043 是否覆盖** | 否——不在并行场景中 | 部分覆盖——仅覆盖同时 spawn 时刻 |
| **SYSGAP-044 是否覆盖** | 否——worktree 隔离只在"计划内并行+重叠"时启用 | 部分覆盖——仅覆盖"已知重叠" |
| **检测难度** | 中等——同一 task ID 被两次 dispatch | 高——不同 task ID，但文件目标重叠 |
| **典型用例** | Coordinator 以为 Agent 卡住了 | 并行编排中某个 Agent 表现异常 |

**关键发现**: SYSGAP-043/044 的设计前提是"Coordinator 知道自己正在并行调度"——它保护的是**计划内的并行**。FIX-056 的问题是**计划外的并发**——Coordinator 不知道 Agent A 还在运行。

---

## 4. 现有防护评估: SYSGAP-043/044 为什么没防住？

### 4.1 SYSGAP-043 (M7.6 并行调度预检)

**设计意图**: Coordinator 同时 spawn >=2 个 agent 前，校验文件修改目标无重叠。

**为什么没防住**:
1. **触发条件不匹配**: M7.6 的触发条件是 "Coordinator 同时 spawn >=2 个 agent"。FIX-056 的场景中，Coordinator 认为 Agent A 已超时/丢失——它不认为自己是在"并行 spawn"，而认为是在"重新分配同一任务"。
2. **时序错位**: SYSGAP-043 只在 spawn 的**同一时刻**执行预检。Agent B 的 spawn 发生在 Agent A 的 spawn 之后（几秒到几十秒），M7.6 不把这种"时间上分开但执行上重叠"的情况视为并行调度。
3. **任务 ID 重复**: 当 Agent B 被分配同一 Task ID 时，Coordinator 可能不认为这是"两个 agent 修改同一文件"——它认为这是"第二次尝试同一任务"。

### 4.2 SYSGAP-044 (Worktree 物理隔离)

**设计意图**: 当并行 Agent 文件修改目标重叠时，使用 `isolation: "worktree"` 参数物理隔离文件系统。

**为什么没防住**:
1. **启用条件不满足**: Worktree 隔离的启用条件是"Coordinator 检测到文件目标重叠"。但在 FIX-056 场景中，Coordinator 认为自己是在**串行重试**——它不会对"同一个任务的两次尝试"启用 worktree。
2. **worktree 机制本身不适用**: worktree 设计用于"两个不同任务修改不同版本的文件"——每个 worktree 有自己的分支。但 FIX-056 场景中，Agent A 和 Agent B 都在同一分支上修改相同的文件。worktree 隔离在这种情况下是"过度隔离"——两个 worktree 无法看到彼此修改，事后合并会有自己的冲突。

### 4.3 差距分析总结

```
                   SYSGAP-043 保护域          SYSGAP-044 保护域
                          │                         │
    ┌─────────────────────┼─────────────────────────┼──────────┐
    │  计划内并行           │  已知文件目标重叠        │          │
    │  (同时 spawn)        │  (worktree 隔离)        │          │
    │                      │                         │          │
    │  ✅ 已覆盖            │  ✅ 已覆盖               │          │
    └─────────────────────┴─────────────────────────┴──────────┘
    
    ┌──────────────────────────────────────────────────────────┐
    │  计划外并发 (FIX-056)                                     │
    │  - Coordinator 不知道 Agent A 还在运行                     │
    │  - Agent B 被 spawn 作为"重试"而非"并行"                   │
    │  - 同一任务 ID，同一文件目标                                │
    │  - 时间上分开，执行上重叠                                   │
    │                                                           │
    │  ❌ 未覆盖——不在 SYSGAP-043/044 设计范围内                  │
    └──────────────────────────────────────────────────────────┘
```

### 4.4 漏洞根因

**根因**: agent-communication-protocol.md line 104 承诺了一个不可靠的操作——"Agent 丢失/超时 → 重新 dispatch"——但没有提供实现这个承诺所需的前提条件：
- 如何可靠判断 Agent 真的超时了（不是伪超时）？
- 重新 dispatch 前如何确认前一个 Agent 已经停止？
- 如果前一个 Agent 仍在运行，如何取消它或等待它？

这是一个"语义承诺与执行能力之间的 gap"——协议承诺了行为，但没有提供支撑该行为的机制。

---

## 5. 用户期望

### 5.1 用户表达的需求（翻译为可验证行为）

基于问题描述和治理工作流的用户体验原则，推断用户期望的理想行为：

| # | 用户期望 | 翻译为可验证行为 | 优先级 |
|---|---------|---------------|--------|
| 1 | "不要同时有两个 Agent 改同一个文件" | 任何时刻，同一文件路径最多被一个修改 Agent 占用 | P0 |
| 2 | "如果 Agent 真的超时了，能重试" | 真超时后可安全重试——前一个 Agent 已确认停止 | P0 |
| 3 | "Coordinator 不要'瞎猜'超时" | 超时判定基于客观标准，非主观感知 | P1 |
| 4 | "不要浪费 Agent 的工作" | 如果 Agent A 已完成部分产出但被误判超时，Agent B 应能接续而非从头开始 | P2 |
| 5 | "告诉我发生了什么" | 如果发生了超时+重新 dispatch，用户应被明确告知 | P2 |

### 5.2 反模式（用户不希望的行为）

- "Coordinator 默默重新 dispatch，然后两个 Agent 打架"
- "Agent 被取消但 Coordinator 不告诉我为什么"
- "同样的任务被执行了两次，一次的结果被我浪费了"

---

## 6. 方案候选

### 方案 A: 文件级锁 + 请求-响应超时

**核心思路**: 在 Coordinator 和 Agent 之间引入文件级锁机制。Agent spawn 时声明文件修改目标 → Coordinator 记录锁 → 同一文件路径不能同时被两个修改 Agent 持有锁。Agent 完成后释放锁。设置客观的超时阈值（如 120 秒），超时后自动释放锁。

**优点**:
- 从根本上防止两个 Agent 同时修改同一文件——无论什么原因引起的重复 spawn
- 锁机制可与现有 SYSGAP-043 预检协议集成——预检时自动查询锁表
- 超时可客观判断（基于 wall-clock 时间 + 阈值），消除主观误判

**缺点**:
- 锁需要存储到文件系统（`.governance/agent-locks.json` 或类似）——新增治理基础设施
- 需要处理"Agent 已声明锁但从未修改文件"的情况（规划阶段占用锁）
- 锁的粒度需要定义（文件级 vs 任务级 vs 路径模式级）
- 如果 Agent 真的 crash 但锁未释放 → 需要超时自动释放机制
- 增加了 spawn 前的额外步骤——效率影响（微小）

**与现有机制的兼容性**:
- 与 SYSGAP-043 互补：SYSGAP-043 做并行调度预检 → 方案 A 增加了"活跃 Agent 检测"
- 与 SYSGAP-044 互补：如果使用了 worktree 隔离，物理隔离下不需要锁
- 需要修改 agent-dispatch-template.md → 锁信息作为 dispatch 模板的可选字段

### 方案 B: 心跳检测 + 重新 dispatch 前确认

**核心思路**: 在重新 dispatch 前，Coordinator 先检查 Agent A 是否还在运行。检查方式：(1) 读取 Agent A 声明要修改的文件，检查 git status 是否有未提交的修改（表示 Agent 已经在写）；(2) 如果有部分产出，等待或接续而非从头开始。

**优点**:
- 实现成本低——不需要新文件基础设施，利用现有 git 命令
- 不改变 Agent spawn 协议——只是在重新 dispatch 前加一个检查步骤
- 自然区分"Agent 还没开始写"vs"Agent 已经开始写了"——git status 提供了这个信号

**缺点**:
- 无法检测"Agent 正在读取和规划但还没开始写"的状态——git status 对此无感知
- git status 的脏状态可能来自其他原因（用户手动修改、其他进程）→ 误判风险
- 如果 Agent A 在 git status 检查和 Agent B spawn 之间的窗口开始写文件 → 竞态条件仍在
- 不能主动"取消"Agent A——只能被动等待

**与现有机制的兼容性**: 
- 修改 behavior-protocol.md M7.6 → 增加"重新 dispatch 前的活跃 Agent 检测"
- 修改 agent-communication-protocol.md line 104 → 不再说"重新 dispatch"，改为"检测前态 → 按结果处理"

### 方案 C: Agent 任务原子性 + 唯一任务 ID 去重

**核心思路**: 利用 task ID 作为去重键。同一 task ID 在任何时刻只能有一个活跃的 Agent 实例。Coordinator 在 spawn 时记录 task_id → agent_instance 映射。尝试重新 dispatch 同一 task ID 时 → 检测到已有活跃实例 → 进入等待/取消/通知用户的决策。

**优点**:
- 实现最简单——仅需 Coordinator 内部状态跟踪
- 不需要文件锁、不需要 git 操作
- 直接解决"同一任务被执行两次"的核心问题
- 可与现有 plan-tracker 的任务状态跟踪结合

**缺点**:
- 解决的是"同一 task ID 重复"场景，不解决"不同 task ID 但文件目标重叠"场景
- Coordinator 内部状态在跨会话时丢失——如果 Agent A 在上一个 session spawn 但尚未返回，新 session 中 Coordinator 不知道 Agent A 还在运行
- Agent 的"活跃"状态判定依赖 Coordinator 的局部知识——如果 Coordinator 误认为 Agent A 是活跃的但 A 其实已经死了 → 死锁
- 需要用户干预来打破死锁（"Agent X 似乎卡住了，取消还是等待？"）

**与现有机制的兼容性**:
- 最小的侵入性——仅 Coordinator 行为改变
- 不需要修改 agent-dispatch-template.md 或 Agent 端任何东西

### 方案对比

| 维度 | 方案 A (文件锁) | 方案 B (心跳检测) | 方案 C (任务去重) |
|------|---------------|-----------------|-----------------|
| **覆盖度** | 高——所有文件重叠场景 | 中——仅覆盖"已开始写的"Agent | 中——仅覆盖同一 task ID 场景 |
| **实现复杂度** | 高——新文件基础设施 | 中——新增检查步骤 | 低——Coordinator 内部逻辑 |
| **跨会话持久性** | 需持久化锁文件 | 不需要（git 天然持久） | 需考虑跨会话状态 |
| **误判风险** | 低——锁是硬约束 | 中——git status 信号有噪声 | 中——Agent 死活判断不准 |
| **用户体验** | 可能等待更长（等锁释放） | 透明——用户无感 | 可能需要用户介入打破死锁 |
| **与 SYSGAP-043/044 兼容** | 互补 | 互补 | 互补 |
| **对 Agent 端的修改** | 需要——锁声明 | 不需要 | 不需要 |

---

## 7. 需求假设显式化

### 未验证假设

| # | 假设 | 验证计划 | 验证方式 |
|---|------|---------|---------|
| H1 | Coordinator 的主观超时判定是问题的首要触发条件 | 在生产环境中统计"重新 dispatch"事件中，Agent A 事后返回了结果的比例 | 如果 >50% 的重新 dispatch 后 Agent A 返回了结果 → H1 成立 |
| H2 | 文件级锁不会显著降低吞吐量 | 在测试环境中测量锁获取/释放的耗时 | 如果 p99 < 500ms → 可接受 |
| H3 | Agent 平台在未来版本中会提供 Agent 存活状态查询 API | 查阅 Claude Code / Codex 平台更新路线图 | 如果即将可用 → 方案 B (心跳检测) 可能变得更简单 |
| H4 | 用户会接受"偶尔需要手动取消卡住的 Agent" | 如果采用方案 C，在用户反馈中追踪死锁事件频率和用户满意度 | 如果死锁频率 < 1次/100个任务且用户未抱怨 → H4 成立 |
| H5 | 不同 task ID 但文件目标重叠的场景在实践中不常见 | 分析 plan-tracker 历史中所有 >1 Agent 的任务，检查文件目标重叠情况 | 如果重叠率 < 5% → 方案 C 的覆盖度足够 |

### H5 验证结果 (2026-05-07): ❌ FALSE — 文件重叠非常常见

通过 `git log --oneline` 分析 4 个核心文件被不同 task ID 修改的频率：

| 文件 | 不同 task 数 | 示例 |
|------|-------------|------|
| `SKILL.md` | **10+** | FIX-031, FIX-039, FIX-050, FIX-055, REL-005/006/007... |
| `verify_workflow.py` | **10+** | FIX-036, FIX-052, FIX-054, REL-003/004/005/006/007... |
| `governance.md` | **6** | FIX-033, FIX-041, FIX-050, FIX-051, FIX-055, AUDIT-089 |
| `pre-commit` | **10+** | FIX-025/026/028/029/036/044/047/048, REL-007... |

**关键证据**: 在本会话中，Release Agent (REL-007) 和 Developer (FIX-057 Phase 2) 同时修改了 `verify_workflow.py` 和 `pre-commit`，导致 FIX-057 代码被混入 REL-007 提交（scope violation）。——这正是 FIX-056 要防护的场景。

**结论**: H5 不成立。不同 task ID 文件重叠率远高于 5%，方案 A（文件锁）是必需的，不能仅依赖方案 C（任务去重）。

---

## 8. IN scope / OUT of scope

### IN scope（本任务解决）

| 场景 | 说明 |
|------|------|
| Coordinator 误判超时 → 重复 spawn 同一 task | 同一 task ID 被 dispatch 两次 |
| Coordinator spawn 不同 task 但文件目标重叠 | 两个 task 修改同一文件路径 |
| Agent 真超时后的安全重 dispatch | 确认 Agent 已死 → 允许重新 spawn |
| 文件级修改互斥 | 同一文件同时最多一个修改 Agent |

### OUT of scope（本任务不解决）

| 场景 | 说明 | 原因 |
|------|------|------|
| 多 Coordinator 实例 | 多个 Claude Code 会话同时操作同一项目 | 极端边缘场景，需跨进程锁——超出当前协议层能力 |
| 跨 session Agent 追踪 | 关闭 Claude Code 后残留 lock 文件 | 通过 post-commit/session 结束时清理锁解决，不纳入 FIX-056 |
| 嵌套 spawn（Agent spawn Sub-agent） | Agent 内部再 spawn agent 的并发控制 | 当前无此机制，未来需要时独立设计 |
| Agent crash 后的锁泄漏恢复 | Agent 异常退出后 lock 文件残留 | 纳入 lock 文件设计（TTL 过期 + 手动清理命令），但不作为 FIX-056 主流程 |

---

## 9. 需求澄清结论

### 8.1 核心需求（P0 — 必须解决）

**R1: 同一文件路径的修改互斥**

任何时候，同一文件路径最多被一个修改 Agent 占用。如果 Coordinator 尝试 spawn 第二个修改同一路径的 Agent，系统（无论是 Coordinator 自身逻辑还是基础设施）必须阻止或隔离。

**验证方式**: 在 behavior-protocol.md M7.6 中增加"活跃 Agent 冲突检测"规则 → pre-commit hook 或 verify_workflow.py 可检测违反情况。

### 8.2 语义需求（P1 — 应该解决）

**R2: 超时判定的客观化**

Coordinator 的"Agent 超时"判定必须基于客观标准（如 wall-clock 时间阈值），而非主观感知。

**验证方式**: 在 agent-communication-protocol.md 中定义明确的超时阈值和判定流程。

**R3: 重新 dispatch 前的安全确认**

在重新 dispatch 任何任务前，Coordinator 必须确认以下至少一项为真：
- (a) 前一个 Agent 实例已确认停止（返回了结果或明确的失败信号）
- (b) 前一个 Agent 实例尚未开始修改任何文件
- (c) 用户已明确确认"取消前一个 Agent，重新开始"

**验证方式**: behavior-protocol.md 新增规则，pre-commit hook 可检测违反。

### 8.3 增强需求（P2 — 建议解决）

**R4: 部分产出的接续**

如果 Agent A 已完成部分文件修改后被判定（正确或错误地）需要重新 dispatch，Agent B 应能接续 Agent A 的产出而非从头开始。

**R5: 用户可见性**

当发生超时+重新 dispatch 时，用户应被明确告知（通过 AskUserQuestion 或通知消息）。

### 8.4 推荐方案组合

基于需求分析和方案评估，建议采用 **方案 A (文件锁) + 方案 C (任务去重)** 的组合：

- **方案 C 作为第一道防线**: Coordinator 在 spawn 时记录 task_id 映射，阻止同一 task ID 的重复 spawn。这是最小的改动，覆盖最常见的场景。
- **方案 A 作为第二道防线**: 文件级锁机制覆盖"不同 task ID 但文件目标重叠"的场景。锁持久化到 `.governance/agent-locks.json`。

**为什么不选方案 B**: 方案 B 的 git status 检测虽然实现成本低，但有一个不可消除的竞态窗口（检查 → spawn 之间的时间窗口）。在 Agent 平台的高延迟环境下，这个窗口可能很大。

### 8.5 留给 Architect 的决策点

1. **锁的存储格式和位置**: `.governance/agent-locks.json` 还是其他位置？JSON 格式还是更简单的锁文件模式？
2. **锁的粒度**: 文件路径精确匹配 vs 通配符/目录级别？
3. **超时自动释放的阈值**: 多少秒后自动释放锁？（建议 120-300 秒，基于 Agent 平台的实际情况）
4. **死锁打破机制**: 如果锁因为 Agent crash 而被持有，如何打破？手动（用户确认）还是自动（超时释放）？
5. **与 worktree 的交互**: 如果未来 worktree 隔离变得更成熟，锁机制是否还需要？
6. **verify_workflow.py 新检查**: 是否需要新增 Check 来检测"活跃 Agent 数量异常"？

---

## 附录 A: 相关文件索引

| 文件 | 相关行/节 | 关联度 |
|------|----------|--------|
| `skills/software-project-governance/SKILL.md` | L186: 并行调度安全规则 | 直接关联 |
| `skills/software-project-governance/references/behavior-protocol.md` | M7.6: 并行调度安全 | 直接关联——需增强 |
| `skills/software-project-governance/references/agent-communication-protocol.md` | L104: Agent 丢失/超时处理 | 直接关联——需修正 |
| `skills/software-project-governance/references/agent-dispatch-template.md` | L59-69: 并行调度安全 + Worktree | 间接关联 |
| `docs/architecture/ADR-004-coordinator-separation-architecture.md` | Phase 3: 系统防御 | 引用——未来可增加锁检查 |
| `project/CHANGELOG.md` | v0.27.0: SYSGAP-043/044 | 追溯参考 |

## 附录 B: 方法论说明

本报告遵循需求澄清 checklist (requirement-clarification SKILL) 的步骤:
1. 问题场景枚举（5 个场景）
2. 影响范围分析（任务类型、条件组合、严重级别）
3. 边界条件界定（真/伪超时区分、Agent 阶段区分、单/多 Agent 差异）
4. 现有防护评估（SYSGAP-043/044 的覆盖 gap）
5. 用户期望翻译（5 条可验证行为）
6. 方案候选（3 个方案 + 对比矩阵）
7. 需求假设显式化（5 条假设 + 验证计划）

无竞品分析——此为内部工作流基础设施的缺陷修复，非面向市场的功能开发。

---

*本报告由 Analyst (阿析) 基于用户反馈和代码库分析撰写。不做技术决策——技术决策留给 Architect。*
