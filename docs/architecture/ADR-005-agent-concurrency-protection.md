# ADR-005: Agent 意外并发防护 —— 文件锁 + 任务去重组合方案

**日期**: 2026-05-05
**状态**: 提案（待 Coordinator 审查）
**决策人**: Architect（老顾）
**关联任务**: FIX-056
**前置分析**: `docs/requirements/FIX-056-agent-concurrency-requirement-clarification.md`（Analyst 阿析）
**影响范围**: 1 新文件（`.governance/agent-locks.json`）+ 4 协议/模板文件修改 + 1 脚本增强 + 1 hook 增强
**可逆性**: 中高（锁文件可删除、协议规则可回退、verify check 可降级为 WARN）

---

## 背景

### 问题陈述

`software-project-governance` v0.30.0。Analyst（阿析）需求澄清报告（FIX-056 requirement clarification）识别出 5 个 Agent 意外并发场景：

```
Coordinator spawn Agent A 执行 Task X
  -> Agent A 在后台执行中（正常耗时，未超时）
  -> Coordinator 主观判定"超时"
  -> Coordinator 重新拆解 Task X，spawn Agent B
  -> Agent A + Agent B 同时修改相同文件
  -> 文件修改冲突
```

5 个场景总结：

| 场景 | 触发条件 | 关键因果 | 冲突类型 |
|------|---------|---------|---------|
| 1. 主观超时 | 耗时 > 预期 | 无客观超时判定 | 同任务重复执行 |
| 2. 用户干预 | 需求变更未取消旧 Agent | 无 Agent 取消机制 | 新旧需求冲突 |
| 3. 平台延迟 | spawn 确认慢 | 无"已 spawn 但未响应"状态 | 重复 spawn |
| 4. 部分产出后超时 | 部分完成但整体慢 | 无进度反馈 | 已修改文件覆盖 |
| 5. 并行+单超时 | 并行中的单 Agent 慢 | 预检只在 spawn 时刻做一次 | 补充 spawn 与运行中 Agent 重叠 |

### 根因

agent-communication-protocol.md line 104 承诺了一个不可靠的操作——"Agent 丢失/超时 → 重新 dispatch"——但没有提供实现此承诺所需的前提条件：

- 如何可靠判断 Agent 真的超时了（不是伪超时）？
- 重新 dispatch 前如何确认前一个 Agent 已经停止？
- 如果前一个 Agent 仍在运行，如何取消它或等待它？

### 现有防护为什么没防住

**SYSGAP-043（M7.6 并行调度预检）**：
- 触发条件是"Coordinator 同时 spawn >=2 个 agent"——但 FIX-056 场景中 Coordinator 认为 Agent A 已超时/丢失，不认为自己在"并行 spawn"
- 预检只在 spawn 的**同一时刻**执行——Agent B 的 spawn 发生在 Agent A 之后（几秒到几十秒），M7.6 不把时间上分开但执行上重叠的情况视为并行调度

**SYSGAP-044（Worktree 物理隔离）**：
- 启用条件是"Coordinator 检测到文件目标重叠"——但在 FIX-056 场景中，Coordinator 认为自己是在串行重试，不会对"同一任务的两次尝试"启用 worktree
- worktree 设计用于"两个不同任务修改不同版本的文件"——不适用于 FIX-056 中两个 Agent 在同一分支修改相同文件的场景

### 设计约束

1. **只做设计，不写实现代码**——代码留给 Developer
2. **不引入新的架构层**——在现有 6 层架构内修补（适配层→入口层→业务智能层→能力层→基础设施层→核心层）
3. **与 SYSGAP-043/044 互补而非替代**——锁机制增强 M7.6 预检，不替换 worktree 隔离
4. **不解决跨 Coordinator 实例并发**（多 Claude Code 会话操作同一项目——OUT of scope，极端边缘场景，需跨进程锁）
5. **不解决嵌套 spawn（Agent spawn Sub-agent）的并发控制**（当前无此机制，未来需要时独立设计）

### H5 验证结论（来自需求澄清报告 Section 7）

**H5 已证伪**：不同 task ID 但文件目标重叠的场景在实践中非常常见。4 个核心文件（SKILL.md、verify_workflow.py、governance.md、pre-commit）各被 6~10+ 个不同 task ID 修改。仅方案 C（任务去重）覆盖度不足——**方案 A（文件锁）是必需的**。

---

## 决策

**采用方案 A（文件锁）+ 方案 C（任务去重）组合方案**，构建两层防线：

1. **第一道防线（任务去重）**：Coordinator 在 spawn 前查询 active_tasks 表——同一 task_id 已有活跃 Agent → 阻止重复 spawn。覆盖场景 1/2/3/4/5 中"同一任务被 dispatch 两次"的核心问题。

2. **第二道防线（文件锁）**：Coordinator 在 spawn 前查询文件锁表——目标文件已被其他 task 的 Agent 锁定 → 串行等待或升级确认。覆盖 H5 证伪的场景——"不同 task ID 但文件目标重叠"。

### 决策理由

1. **方案 C 覆盖最常见的场景**（同一 task ID 重复 dispatch）——实现成本最低（Coordinator 内部状态跟踪），直接命中核心问题链路。
2. **方案 A 填补方案 C 的覆盖盲区**（不同 task ID 但文件目标重叠）——H5 验证已证伪"文件重叠不常见"的假设，文件锁是必需的。
3. **不选方案 B（心跳检测 / git status 检测）**——因为 git status 检测有一个不可消除的竞态窗口（检查→spawn 之间的时间）。在 Agent 平台的高延迟环境下，这个窗口可能很大。且 git status 的脏状态信号有噪声（用户手动修改、其他进程）。
4. **方案 A + C 组合的可逆性高**——锁文件删除 + 协议规则回退 = 完全回滚。与引入新的 Agent 平台依赖或架构层相比，影响可控。

---

## 详细设计

### 一、方案概览：两道防线

```
Coordinator 准备 spawn Agent 执行 Task X，声明文件目标 F1, F2, F3
    |
    ▼
┌─────────────────────────────────────────────────────────┐
│  第一道防线：任务去重（方案 C）                          │
│                                                         │
│  CHECK active_tasks[task_id] exists?                    │
│    ├─ YES → BLOCK: "Task X is already being executed    │
│    │         by {agent_role} (spawned at {time})."      │
│    │         选项: 等待 / 取消旧 Agent 并重试 / 降级    │
│    │                                                │
│    └─ NO → 继续到第二道防线                             │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  第二道防线：文件锁（方案 A）                            │
│                                                         │
│  FOR each file_path IN [F1, F2, F3]:                   │
│    CHECK lock_table[file_path] exists?                  │
│      ├─ YES → WAIT or BLOCK:                            │
│      │    "File {file_path} is locked by {task_id}      │
│      │     ({agent_role}, TTL {ttl}s)."                 │
│      │    选项: 等待锁释放 / 强制接管 / 降级为只读      │
│      │                                                  │
│      └─ NO → 继续下一个文件                              │
│                                                         │
│  IF all files available → ACQUIRE all locks            │
│    → RECORD active_tasks[task_id]                       │
│    → SPAWN Agent                                        │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
              Agent 执行中（最长 TTL 秒）
                         │
                         ▼
              Agent 返回结果
              → RELEASE all locks
              → REMOVE from active_tasks
```

### 二、六个设计决策点

#### 决策 1: 锁的存储位置与格式

**决策**: `.governance/agent-locks.json`，采用 JSON 格式。

**JSON Schema**:

```json
{
  "active_tasks": [
    {
      "task_id": "FIX-056",
      "agent_role": "Developer",
      "spawned_at": "2026-05-05T14:30:00Z",
      "status": "in_progress",
      "coordinator_session_id": "session-20260505-001"
    }
  ],
  "file_locks": [
    {
      "file_path": "skills/software-project-governance/SKILL.md",
      "task_id": "FIX-056",
      "agent_role": "Developer",
      "acquired_at": "2026-05-05T14:30:01Z",
      "ttl_seconds": 300,
      "ttl_reason": "default",
      "expires_at": "2026-05-05T14:35:01Z"
    }
  ]
}
```

**字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `active_tasks[].task_id` | string | 任务 ID（唯一） |
| `active_tasks[].agent_role` | string | 持有锁的 Agent 角色名 |
| `active_tasks[].spawned_at` | ISO 8601 | Agent spawn 时间 |
| `active_tasks[].status` | enum | `in_progress` / `completed` / `timed_out` |
| `active_tasks[].coordinator_session_id` | string | Coordinator 会话标识（跨会话冲突检测用） |
| `file_locks[].file_path` | string | 相对于仓库根目录的文件路径 |
| `file_locks[].task_id` | string | 关联任务 ID |
| `file_locks[].acquired_at` | ISO 8601 | 锁获取时间 |
| `file_locks[].ttl_seconds` | int | TTL 秒数 |
| `file_locks[].ttl_reason` | string | 修改 TTL 的原因（默认值 `"default"`；仅在 TTL 非默认值时填写调整理由，如 `"large multi-file refactoring"`） |
| `file_locks[].expires_at` | ISO 8601 | 锁过期时间 |

**排除方案**:

| 备选位置 | 排除理由 |
|---------|---------|
| `.git/agent-locks.json` | `.git/` 是 git 内部目录，不应用于应用状态存储。Hook 无法可靠写入 `.git/`（部分环境只读）。 |
| `skills/software-project-governance/infra/agent-locks.json` | 与治理数据分离——锁是运行时治理状态，应与其他治理状态文件（plan-tracker, evidence-log）在同一目录。 |
| 基于文件的锁（`mkdir .locks/file_path.lock`） | 比 JSON 更难查询"谁锁了哪个文件"、"所有活跃锁"、"哪个 task 锁了哪些文件"。JSON 综合查询只需一次 Read。 |

#### 决策 2: 锁的粒度

**决策**: **文件级精确路径匹配**。

**匹配规则**:
- `file_path` 字段存储相对于仓库根目录的完整路径（如 `skills/software-project-governance/SKILL.md`）
- 查询时使用 `==` 精确匹配，不做前缀匹配、glob 匹配或目录级匹配
- Agent 声明文件目标时 MUST 使用完整路径（不可使用通配符或目录路径）

**文件删除场景**: Agent 删除文件视为"修改"操作——删除文件前 MUST 获取该文件路径的写锁。理由：(1) 删除文件同样影响其他 Agent 对该文件的读写——如果 Agent A 正在读取某文件而 Agent B 删除了它，Agent A 的读取操作会失败；(2) 如果两个 Agent 分别尝试修改和删除同一文件，结果不可预测（修改先于删除 vs 删除先于修改，结果完全不同）。文件锁将删除序列化到修改操作之后，确保结果可预测。

**排除方案**:

| 备选粒度 | 排除理由 |
|---------|---------|
| 目录级（`skills/software-project-governance/`） | 过于粗粒度——会阻止同一目录下不同文件的无冲突并行修改。例如 `SKILL.md` 和 `behavior-protocol.md` 可安全并行修改。 |
| 通配符/pattern 级（`skills/**/*.md`） | 过度复杂——增加声明负担且容易误匹配。当前 Agent 的任务上下文指定的是具体文件路径，非 pattern。 |
| 文件 + 行号级 | 过度精细化——agent 的修改范围在 spawn 时无法精确到行号。Write 工具是全文件级别。 |

**残留风险**: 如果 Agent A 和 Agent B 分别修改同一文件的不同区域（不重叠的行块），文件锁会阻止这种理论上安全的并行。但：(1) 当前 Write 工具是全文件级别，不支持行级部分写入；(2) 两个 Agent 对同一文件的"非重叠区域"判断在 spawn 时不可靠（Agent 的修改范围可能扩展）。

#### 决策 3: TTL 超时 —— 阈值与超时判定

**决策**: **默认 TTL 300 秒（5 分钟），通过 git diff 辅助区分"真超时"和"慢任务"**。

**TTL 设定依据**:

| 参数 | 值 | 理由 |
|------|---|------|
| 默认 TTL | 300 秒 | Agent 平台实际观察：P0 产品代码修改任务通常在 30~120 秒内完成。300 秒为 5 倍中位数，留足余量。 |
| 最短 TTL | 60 秒 | 单文件简单修改（如修复 typo）的合理耗时 |
| 最长 TTL | 600 秒 | 多文件重构的合理耗时。超过此值 = 任务分解有问题，应拆分子任务 |
| 可配置性 | 是 | Coordinator 可根据任务类型调整 TTL。但 MUST 记录调整理由到 lock 条目中 |

**超时判定流程（TTL 过期后的自动处理）**:

```
TTL 过期，Agent 未返回结果
    │
    ▼
1. Run: git status --porcelain -- <locked_files>
    │
    ├─ 有修改（git status 显示 M 或 ??）
    │   → Agent 是"慢任务"——已在写文件
    │   → 记录 WARN 到 risk-log
    │   → Coordinator MUST AskUserQuestion:
    │      "Agent ({agent_role}) for task {task_id} has been working for {elapsed}s
    │       and has modified files. Continue waiting or force-cancel?"
    │   → 选项: (a) 等待（延长 TTL 2x） (b) 强制取消（丢弃锁，保留当前文件状态）
    │
    └─ 无修改（working tree clean for locked files）
        → Agent 很可能是"真超时"——尚未开始写或已 crash
        → 自动释放锁
        → 记录 EVD 到 evidence-log: "Agent timeout confirmed (no file changes)"
        → 允许重新 dispatch
```

**区分"真超时"和"慢任务"的关键信号**:

| 信号 | 真超时 | 慢任务 |
|------|--------|--------|
| 文件修改（git status） | 无 | 有 |
| Agent 返回结果 | 否（永不返回） | 是（终将返回） |
| 锁的处置 | 自动释放 | 需用户确认后释放 |
| 后续动作 | 安全重新 dispatch | 保留当前状态，用户决策 |

**排除方案**:

| 备选 TTL 值 | 排除理由 |
|------------|---------|
| 120 秒 | 太短——多文件重构、LLM 长推理任务可能超过。误判率高。 |
| 600 秒 | 太长——如果 Agent 真的 crash，用户需等 10 分钟才知道。且锁占用时间长会阻塞其他合法任务。 |
| 无自动释放（靠人工清理） | 与"过程自动化"项目目标矛盾。Agent 异常退出后残留锁需要手动清理 = 用户体验差。 |

#### 决策 4: 锁的获取时机

**决策**: **spawn 前检查 + 获取锁，Agent 完成后释放**。

**完整时序**:

```
1. Coordinator 解析任务，提取文件目标列表
2. Coordinator 读取 .governance/agent-locks.json
3. Coordinator 执行两道防线检查（任务去重 + 文件锁冲突）
4. IF 通过检查:
     a. 写入 active_tasks 条目（task_id + agent_role + spawned_at）
     b. 写入 file_locks 条目（每个目标文件一行）
     c. 写入 .governance/agent-locks.json
     d. spawn Agent
5. Agent 执行中...
6. Coordinator 等待 Agent 返回结果
7. Agent 返回后:
     a. 读取 .governance/agent-locks.json
     b. 移除该 task 的 active_tasks 条目
     c. 移除该 task 的 file_locks 条目
     d. 写入 .governance/agent-locks.json
8. TTL 监控（并发进行）:
     如果 Agent 在 TTL 秒内未返回 → 执行决策 3 的超时判定流程
```

**为什么是"spawn 前"而非"Agent 启动后"**:

| 时机 | 竞态窗口 | 
|------|---------|
| **spawn 前获取**（本决策） | 无——锁获取在 spawn 调用之前。Coordinator 持有锁后才 spawn。 |
| Agent 启动后声明 | 有——Coordinator spawn 和 Agent 读取 lock 文件之间存在窗口。且 Agent 可能未及时声明、可能不声明。 |

**关键假设**: Coordinator 在步骤 2~4 之间不会被中断。在 single-threaded LLM Agent 环境中，这个假设成立——Coordinator 的步骤 2~4 是同一 LLM 回合内的连续操作。

#### 决策 5: 任务去重的 key

**决策**: **task_id 作为唯一去重键**。

**去重判定逻辑**:

```
IF active_tasks 中存在 matching task_id:
    → 该 task 已被 dispatch，拒绝重复 dispatch
    → Coordinator MUST AskUserQuestion（关键决策——涉及"取消活跃 Agent"）
```

**设计说明**:
- 不同 task ID 但文件目标重叠的场景由第二道防线（文件锁）覆盖
- 同一 task ID 但文件目标不同的场景不应出现（task 定义包含文件目标——文件目标变了 = 不同 task）
- 如果需要重新 dispatch 同一 task（例如 Agent 返回了 NEEDS_CHANGE），必须先完成清理（释放锁 + 移除 active_tasks 条目）

**排除方案**:

| 备选 key | 排除理由 |
|---------|---------|
| `task_id + file_list_hash` | 不同 file_list 产生不同 hash → 同一 task_id 可创建多个 active_tasks 条目 → 去重失效。且文件列表变化意味着任务定义变化——应该是新 task，不是重试。 |
| `task_id + agent_role` | 同一 task 被分配给不同类型的 Agent（如先从 Developer 改为 Architect）不应绕过去重——旧 Agent 必须被取消。 |

#### 决策 6: 与 SYSGAP-043/044 的关系

**决策**: **增强，而非替代**。

**关系定义**:

| 机制 | 原有范围 | FIX-056 后的变化 |
|------|---------|-----------------|
| **SYSGAP-043** (M7.6 预检) | 同时 spawn >=2 agent 前的文件目标重叠检查 | **增强**: 预检查询源从"任务描述中提取"变为"lock 表实时状态"。同一文件路径被锁定 = 重叠 = 必须串行或 worktree。解决了"计划外并发"的检测盲区。 |
| **SYSGAP-044** (Worktree 隔离) | 文件目标重叠时，worktree 物理隔离 | **不变**: worktree 仍有价值——当 Coordinator 确实需要并行修改同一文件的不同版本时（如实验性重构 + 正式版本并行），worktree 是正确方案。文件锁解决的是"不应并行"的场景，worktree 解决的是"可以并行但需要隔离"的场景。 |
| **FIX-056 新增** (文件锁 + 任务去重) | — | **新增**: 在 M7.6 预检之外增加"活跃 Agent 检测"。M7.6 覆盖"已知并行"场景，FIX-056 覆盖"计划外并发"场景。锁表成为 SYSGAP-043 预检的实时检测源。 |

**升级后的 M7.6（行为协议修订）**:

```
### M7.6 并行调度安全（MANDATORY）— FIX-056 增强

**IF** Coordinator 准备 spawn Agent 执行任务：
  0. 读取 .governance/agent-locks.json
  1. 任务去重检查：task_id 已在 active_tasks 中 → 拒绝，按"重复 dispatch 处理流程"
  2. 文件锁检查：目标文件已被其他 task 锁定 → 等待/串行/升级
  3. 获取锁：通过检查后，写入 active_tasks + file_locks 条目
  4. spawn Agent

**IF** Coordinator 同时 spawn >=2 agent（原有 M7.6 预检保留）：
  5. 文件锁表查询代替原有"任务描述提取"作为重叠判定源
  6. 重叠判定基于 lock 表实时状态，而非 spawn 时刻的静态快照
```

### 三、边界条件与异常处理

#### 3.1 Coordinator 会话中途结束（锁泄漏防护）

**场景**: Coordinator 获取了锁，spawn 了 Agent，但 Agent 返回前 Coordinator 会话被用户关闭。

**风险**: 锁残留在 `agent-locks.json` 中——下次会话的 Coordinator 不知道这些锁是否仍有效。

**防护**: `coordinator_session_id` 字段区分不同会话。

```
新会话 Coordinator 读取 agent-locks.json:
  IF active_tasks 中存在不同 coordinator_session_id 的条目:
    CHECK 每个锁的 expires_at:
      IF expires_at < now():
        → 自动清理（TTL 已过期）
        → 记录 WARN: "Cleaned up {N} stale locks from session {session_id}"
      ELSE:
        → WARN: "{N} locks from previous session {session_id} still active (TTL not expired)"
        → Coordinator MUST AskUserQuestion:
           "上一个会话（{session_id}）留下了 {N} 个活跃锁。
            可能意味着 Agent 仍在运行。如何处理？"
           → 选项: (a) 等待 TTL 过期 (b) 强制清理所有跨会话锁 (c) 仅清理所属 task 的锁
```

#### 3.2 Agent 返回前锁被手动修改

**场景**: 用户在 Agent 执行中手动编辑了 `agent-locks.json`，移除了某些锁。

**风险**: Coordinator 读取到的锁状态与实际 Agent 执行状态不一致。

**防护**: 
- `agent-locks.json` 是治理状态文件——与 plan-tracker.md 同级。用户手动修改治理文件的行为 = 已知风险（所有治理文件都有此风险）
- Pre-commit hook 可在 commit 时检测 agent-locks.json 的非空状态 → 如果 agent-locks.json 有活跃条目 + commit 包含产品代码变更 → WARN（可能有并发 Agent 正在执行）
- 不做更强的防护——治理文件的可编辑性是设计特征，不是 bug

#### 3.3 Reviewer / 只读 Agent 是否需要声明文件目标

**决策**: **不需要**。Reviewer 只读取文件，不修改文件——与修改 Agent 的文件锁冲突判定无关。

**判定规则**: 
- 只读 Agent（Reviewer、Analyst 读分析阶段、Architect 读设计阶段）→ 不写入 active_tasks，不获取文件锁
- 修改 Agent（Developer）→ 写入 active_tasks + 获取文件锁
- QA / Architect（产出文件时）→ 如果产出物是新文件（不在已有锁中），获取新文件的锁。不获取只读文件的锁。

#### 3.4 锁与 worktree 的交互

**场景**: Coordinator 决定两个 task 可以并行，且目标文件有重叠 → 按 M7.6 启用 worktree 隔离。

**锁的处理**:
- Worktree 隔离的 Agent → **不需要文件锁**。每个 worktree 有独立的文件系统，物理隔离不开存在冲突。
- 但 task_id 仍写入 active_tasks——防止同一 task 的重复 dispatch
- Lock 条目中新增字段 `isolation: "worktree"` → 标记此 task 使用 worktree 隔离，不占用主分支锁

**文件锁 vs worktree 适用场景判定表**:

| 场景 | 使用机制 | 锁行为 |
|------|---------|--------|
| 同一 task 被重复 dispatch（错误） | 任务去重 BLOCK | active_tasks 去重阻止 |
| 不同 task，文件目标重叠，需要串行 | 文件锁 WAIT | 等待先到 task 释放锁 |
| 不同 task，文件目标重叠，计划内并行 | Worktree 隔离 | 不获取主分支锁，isolation=worktree |
| 不同 task，文件目标不重叠，计划内并行 | 直接并行 | 各自获取各自的文件锁 |
| 只读 Agent + 修改 Agent | 直接并行 | 只读不获取锁，修改获取锁 |

### 四、修改文件清单

| # | 文件 | 修改类型 | 改造内容 |
|---|------|---------|---------|
| 1 | `.governance/agent-locks.json` | **新文件** | 锁状态持久化文件。初始内容为空的 `{"active_tasks": [], "file_locks": []}`。governance-init 模板需自动创建此文件。 |
| 2 | `skills/software-project-governance/references/behavior-protocol.md` | 修改 | M7.6 并行调度安全升级——新增"活跃 Agent 检测"步骤（Step 0: 读 agent-locks.json → 任务去重 → 文件锁检查）。M8 自检协议新增一条：`[ ] FIX-056 锁协议已执行？（spawn 前查锁、获取锁、任务去重检查）`。 |
| 3 | `skills/software-project-governance/references/agent-communication-protocol.md` | 修改 | L104 "Agent 丢失/超时 → 重新 dispatch" 替换为"Agent 超时 → 执行 TTL 超时判定流程（git diff + AskUserQuestion）→ 按结果处理（等待/取消/重 dispatch）"。新增"Agent 并发防护"章节——引用 ADR-005。 |
| 4 | `skills/software-project-governance/references/agent-dispatch-template.md` | 修改 | 并行调度安全节新增"spawn 前锁检查"步骤说明 + 引用 behavior-protocol.md M7.6 FIX-056 增强。新增占位符 `{lock_files}` ——Coordinator 在 spawn 指令中告知 Agent 哪些文件已被锁定为其独占（信息性，Agent 不需要操作锁）。 |
| 5 | `skills/software-project-governance/SKILL.md` | 修改 | "并行调度安全"段落新增 FIX-056 引用："并行调度安全（M7.6 + FIX-056 增强）：除并行预检外，spawn 前 MUST 执行活跃 Agent 检测（读 agent-locks.json → 任务去重 → 文件锁检查）。" Coordinator 铁律新增一条："spawn Agent 前 MUST 检查 agent-locks.json——同一 task 不重复 dispatch，目标文件不被其他 Agent 占用。" |
| 6 | `skills/software-project-governance/infra/verify_workflow.py` | 修改 | 新增 Check 25: `check_agent_lock_consistency()`——检测 agent-locks.json 中的锁与 evidence-log/plan-tracker 的一致性：活跃锁对应的 task 是否确实在进行中？过期锁是否已清理？是否有文件被多个 task 同时锁定？新增子命令 `check-locks` 供独立使用。 |
| 7 | `skills/software-project-governance/infra/hooks/post-commit` | 修改 | 新增锁清理步骤 + scope creep 检测：(a) commit 后检查 agent-locks.json——如果当前 session 的锁全部已过期 → 自动清理。(b) 如果 commit 中涉及已锁定文件但对应 task 不是 commit 关联的 task → WARN（可能有并发 Agent 在修改同一文件）。(c) **scope creep 检测**: 检测 agent-locks.json 本身是否被意外提交——agent-locks.json 是运行时治理状态文件（与 plan-tracker.md 不同，它不应进入版本历史），如果检测到 agent-locks.json 被 `git add` 或出现在 commit diff 中 → WARN "agent-locks.json is runtime state and should not be committed. Run `git reset HEAD .governance/agent-locks.json` to unstage." 同时检测 agent-locks.json 文件完整性（JSON 可解析 + Schema 字段完整），如损坏 → FAIL commit。(d) 检测 .gitignore 中是否包含 agent-locks.json——用于防御性提示（不阻断 commit）。 |
| 8 | `skills/software-project-governance/core/templates/plan-tracker.md` | 修改（可选） | 新增"治理基础设施"节中提及 agent-locks.json 为治理状态文件之一。governance-init 模板同步创建初始 agent-locks.json。 |

### 五、不变的文件

- `skills/software-project-governance/references/behavior-protocol.md` 的 M5/M7/M8 其他部分——不变
- `agents/` 目录——Agent 不直接操作锁，锁的获取和释放由 Coordinator 负责
- 产品代码边界定义——不变
- 路由表——不变
- `skills/software-project-governance/infra/hooks/pre-commit`——本方案不新增 pre-commit 阻断（锁状态是运行时数据，pre-commit 时锁应为空。如不为空 → 属于异常场景，由 verify_workflow.py 追溯检测）

### 六、与版本规划的关系

本方案建议分 2 Phase 执行：

**Phase 1（0.32.0）——核心锁机制**:
- 修改 1（agent-locks.json 新文件）
- 修改 2（behavior-protocol.md M7.6 增强）
- 修改 3（agent-communication-protocol.md 超时处理修正）
- 修改 5（SKILL.md Coordinator 铁律）

Phase 1 完成后，Coordinator 的 spawn 协议中增加了"任务去重 + 文件锁"两道防线。即使 verify_workflow.py 和 post-commit hook 尚未更新，核心的"spawn 前检测"闭环已建立。

> **Phase 1 最小验证**: Phase 1 应包含一个轻量级 verify_workflow 检查——`check_agent_locks_format()`——仅校验 `agent-locks.json` 的 JSON 格式有效性和 Schema 字段完整性（不检查锁与 evidence-log/plan-tracker 的一致性，完整检测留给 Phase 2 Check 25）。理由：Phase 1 引入了新治理文件 `agent-locks.json`，其格式损坏会导致锁机制全部失效（残余风险 2）。格式校验是最小化的自动化防护，实现成本低（~30 行代码），防止了最坏情况（损坏的 JSON 导致 Coordinator 误判无锁）。

**Phase 2（0.31.1）——验证 + 自动化清理**:
- 修改 6（verify_workflow.py Check 25）
- 修改 7（post-commit hook 锁清理 + scope creep 检测）
- 修改 4（agent-dispatch-template.md）
- 修改 8（plan-tracker.md 模板——可选）

Phase 2 完成后，脚本可独立检测锁一致性和过期锁，post-commit hook 自动清理已过期锁并防御 agent-locks.json 被意外提交（scope creep 检测）。

---

## 备选方案评估

### 备选方案 1: 仅方案 C（任务去重）—— 被否决

**描述**: 只做 task_id 去重，不加文件锁。依赖"不同 task 间文件重叠很少"的假设。

**否决理由**: H5 已验证此假设不成立。4 个核心文件各被 6~10+ 个不同 task 修改。仅做任务去重会遗漏 FIX-056 场景 5 中"不同 task ID 但文件目标重叠"的并发冲突。且 REL-007 和 FIX-057 Phase 2 的 scope violation 事件直接证实此风险。

### 备选方案 2: 仅方案 A（文件锁）—— 被否决

**描述**: 只做文件锁，不做任务去重。依赖"文件锁覆盖了所有场景"的假设。

**否决理由**: 同一 task 被重复 dispatch 时，文件锁能检测到（目标文件相同），但无法提供"这是同一个任务被 dispatch 了两次"的语义信息——Coordinator 不知道这是意外重复还是故意重试。任务去重提供更精确的语义——"这个 task 已经有活跃 Agent"vs"这些文件碰巧被另一个 task 锁了"——两者的处理策略不同（前者 MUST 确认用户，后者可自动等待）。

### 备选方案 3: 方案 B（心跳检测 / git status）—— 被否决

**描述**: 在重新 dispatch 前，用 git status 检测 Agent A 是否已经开始修改文件。如果有修改 → 等待或接续。如果没有 → 安全重新 dispatch。

**否决理由**:
1. **竞态窗口不可消除**: git status 检查和 spawn 之间存在时间窗口——Agent A 可能恰好在检查后、spawn 前开始写文件。
2. **git status 信号有噪声**: 工作树脏状态可能来自用户手动修改、其他 Agent 的合法修改、或 .governance/ 治理文件更新。
3. **无法检测"规划中"的 Agent**: Agent A 可能正在读取文件、推理修改方案（耗时很长），但尚未执行任何 Write——git status 报告 clean，但 Agent A 即将开始写。
4. **不能主动取消 Agent**: 如果需要取消 Agent A 的过时任务（如用户变更需求），方案 B 只能被动等待，无法主动终止。

### 备选方案 4: Agent 平台依赖（心跳 API / 进程监控）—— 被否决（超出范围）

**描述**: 依赖 Agent 平台（Claude Code / Codex）提供 Agent 存活状态查询 API。Coordinator 通过 API 查询 Agent 是否真的停止了。

**否决理由**: 当前 Agent 平台不提供此 API。即使未来提供，工作流也不应绑定特定平台的能力——platform-agnostic 是设计目标。此方案可作为 Phase 2 的增强（如果平台 API 可用，TTL 超时判定可更精确），但不作为 Phase 1 的基础设计。

---

## 蓝军挑战

> 每条挑战有独立 ID 和对应缓解措施。

| ID | 挑战描述 | 缓解措施 |
|----|---------|---------|
| BC-001 | **"锁文件本身成为并发竞争的焦点。"** Coordinator 写入 agent-locks.json 时，如果两个 Coordinator 实例（两个 Claude Code 会话）同时写，JSON 损坏。 | 承认此风险——但 FIX-056 的 OUT of scope 已明确"不解决多 Coordinator 实例并发"（极端边缘场景，需跨进程锁，超出当前协议层能力）。在单 Coordinator 实例环境中，写入是单线程串行操作，无竞态。未来如果多实例场景变得常见，可引入 `.governance/agent-locks.json.lock` 文件系统锁（flock）。当前阶段接受此风险。 |
| BC-002 | **"锁的获取和释放依赖 Coordinator 记得执行——如果 Coordinator '忘了'释放锁（例如 Agent 返回后直接进入下一个任务），锁泄漏。"** Post-commit hook 和 verify check 可以事后发现，但修复窗口期内文件被误锁。 | (1) 锁释放与 M7.4 任务完成协议绑定——Coordinator MUST 在步骤 4（证据写入后）释放锁。不释放锁 = M7.4 未完整执行 = 协议违规。(2) 如果锁泄漏发生，verify_workflow.py Check 25 检测过期锁（expires_at < now 但仍存在）并报告。(3) Post-commit hook 在每次 commit 后自动清理过期锁。(4) 最坏情况：锁泄漏导致一个文件被错误锁定直到 TTL 过期（默认 300 秒 = 5 分钟）。超过 TTL 后自动过期释放。5 分钟的等待是可接受的。 |
| BC-003 | **"任务去重可能阻止合法的'用户确认后重新 dispatch'。"** 用户明确要求"取消之前的 Agent，重新开始"。但 active_tasks 表中有旧条目 → 去重 BLOCK。 | (1) 去重 BLOCK 不是死锁——它触发 AskUserQuestion，用户选择"取消旧 Agent"后 → Coordinator 写入 force_cancel 标记 → 移除 active_tasks 条目 → 释放文件锁 → 允许新 dispatch。(2) 在 lock 表中新增 `status: "force_cancelled"` 标记——表示此 task 的锁已被用户显式取消，新 dispatch 可以安全进行。(3) 这不是"阻止合法操作"——这是"确保合法操作被确认后执行"。如果用户真的想重新 dispatch，需要做一次确认——这是设计意图，不是 bug。 |
| BC-004 | **"TTL 300 秒可能对某些 Agent 平台不够（如 API 排队 + 大文件处理）。Agent 正常执行超过 5 分钟被误判为超时 → 锁释放 → 第二个 Agent spawn → 冲突。"** | (1) TTL 可配置——见决策 3。Coordinator 可以根据任务类型设置更长的 TTL（最多 600 秒）。(2) TTL 过期不自动释放锁——执行"超时判定流程"（决策 3）：先 git diff 检查是否有修改。有修改 = 认定为慢任务 → 不自动释放，而是 AskUserQuestion 确认。(3) 如果 Agent 执行 10+ 分钟仍未返回 = 任务分解有问题——单个任务不应超过 600 秒。(4) 长期看，如果 Agent 平台提供 progress callback，可替代 TTL 作为更精确的判定机制。 |
| BC-005 | **"Agent 在获取锁之后、执行第一次 Write 之前 crash 了。锁被占用 300 秒（直到 TTL 过期）。Coordinator 和用户都不知道 Agent 已经 crash——它们在等锁释放。"** | (1) 如果 Agent crash 是由平台报告给 Coordinator 的（例如 Agent 工具返回错误），Coordinator 立即释放锁。(2) 如果 crash 无通知（Agent quiet-fail），TTL 300 秒后自动过期——Coordinator 执行超时判定 → git diff 无修改 → 认定为真超时 → 自动释放锁。(3) 300 秒等待比当前"无锁机制下两个 Agent 打架导致文件损坏"好得多。(4) 最坏情况：用户等待 5 分钟。这是已知的折衷——在没有 Agent 平台存活 API 的约束下，TTL 是最可靠的降级方案。 |
| BC-006 | **"agent-locks.json 的读写频率高（每个任务 spawn 都要读+写），可能成为 I/O 瓶颈。"** | (1) JSON 文件只有两个数组（active_tasks + file_locks），活跃条目通常在 0~5 个之间。文件大小 ≤ 2KB。读写耗时 < 1ms。(2) Coordinator 的 LLM 推理耗时远大于文件 I/O（秒级 vs 毫秒级）。I/O 瓶颈不成立。(3) 如果未来并发任务量达到数十个，JSON 仍能处理——单文件 JSON 无锁竞争（单 Coordinator 实例）。 |

---

## 残余风险与缓解

### 风险 1: 锁协议依赖 Coordinator 的 prompt 约束——与所有其他行为协议面临相同挑战

**严重级别**: P1
**描述**: 文件锁 + 任务去重的执行依赖 Coordinator "记得"读取 agent-locks.json 并遵循协议。与 M7.6（已有）一样，如果 Coordinator 忽略了协议文本，锁机制不会生效。
**影响**: 锁机制的系统强制性取决于 Coordinator 的协议遵循度。在协议违规的情况下，并发冲突仍可能发生。
**缓解**:
1. SKILL.md 中新增 Coordinator 铁律——"spawn Agent 前 MUST 检查 agent-locks.json"——放在与其他铁律（不修改产品代码、MUST spawn Agent Team）同等位置
2. M8 自检协议新增一条："[ ] FIX-056 锁协议已执行？"——每次任务完成后自检
3. verify_workflow.py Check 25 追溯检测——发现活跃锁对应的 task 不在 plan-tracker 进行中 → 报告不一致
4. 与其他行为协议一样，接受 prompt 层面约束的局限性——通过多层防御（prompt + 自检 + 外部验证）降低违规概率，但无法降至零
**接受**: 在当前平台约束下，所有行为协议的 enforcement 都依赖 prompt。FIX-056 不改变这一前提——它在这个约束内增加防护。

### 风险 2: 锁文件成为新的"单点状态故障"

**严重级别**: P2
**描述**: agent-locks.json 如果损坏（手动编辑错误、并发写入、编码问题），锁机制全部失效。
**影响**: 损坏后 Coordinator 可能读取到错误状态 → 误判无锁 → spawn 冲突 Agent。
**缓解**:
1. JSON schema 简单（两个顶层数组，固定字段）——损坏概率低
2. verify_workflow.py Check 25 检测 JSON 解析错误 → FAIL + 报告
3. 如果 agent-locks.json 不存在或 JSON 解析失败 → Coordinator 回退到"无锁模式"（= 当前行为），并 WARN 用户
4. governance-init 模板创建带有正确初始结构的 agent-locks.json
**接受**: 与 plan-tracker.md、evidence-log.md 等治理文件面临相同的"文件损坏"风险。锁文件不比其他治理文件更脆弱。

### 风险 3: 锁机制可能被误解为"替代 worktree 隔离"

**严重级别**: P3
**描述**: 开发者可能认为有了文件锁，worktree 隔离就不再需要——导致 worktree 机制被废弃。
**影响**: Worktree 的合法使用场景（实验性重构 + 正式版本并行）失去支持。
**缓解**:
1. ADR 明确声明："文件锁不是 worktree 的替代品——两者解决不同场景。文件锁 = 防止不应并发的场景；worktree = 支持应并发但需隔离的场景。"
2. 决策 6 的详细设计保留了 worktree 的所有引用和判定规则
3. verify_workflow.py 不删除或弱化 worktree 相关检查
**接受**: 文档和代码层面的清晰边界 + 两套机制各自独立的错误检测 = 低概率混淆。

---

## 后续动作

1. **Coordinator 审阅本 ADR**——确认 6 个设计决策 + 2 Phase 执行计划
2. **创建 FIX-056 子任务入账 plan-tracker**——按 Phase 1/2 拆分
3. **Phase 1 执行（Developer 实现）**：
   - 创建 `governance-init` 模板中的 agent-locks.json 初始结构
   - 修改 behavior-protocol.md M7.6（活跃 Agent 检测 + 任务去重 + 文件锁获取 + 文件删除锁处理）
   - 修改 agent-communication-protocol.md L104（超时处理替换）
   - 修改 SKILL.md（Coordinator 铁律 + 并行调度安全引用）
   - verify_workflow.py 新增轻量级格式校验 `check_agent_locks_format()`（JSON 解析 + Schema 字段完整性）
4. **Phase 2 执行（Developer 实现）**：
   - verify_workflow.py 新增 Check 25（agent_lock_consistency——完整一致性检测）
   - Post-commit hook 新增锁清理 + scope creep 检测（agent-locks.json 提交防御）
   - agent-dispatch-template.md 新增锁声明占位符
5. **Phase 1 完成后执行 check-governance**——验证无回归
6. **至少 3 个并发场景走通完整链路验证**：
   a. 同一 task 重复 dispatch → 被任务去重阻止
   b. 不同 task 修改同一文件 → 后到 task 等待锁释放
   c. Agent 真超时 → TTL 过期 → git diff 无修改 → 锁自动释放 → 安全重新 dispatch
7. **0.32.0 发布**——Phase 1 + Phase 2 完成后发布

---

## 附录 A: 决策可逆性

| 决策项 | 可逆性 | 回滚成本 |
|--------|--------|---------|
| agent-locks.json 位置与格式 | 高（删除文件 + 改回协议即可） | SKILL.md + behavior-protocol.md 几行变更 |
| 锁粒度（文件级） | 中（如果改为目录级，需要 migrate 锁条目格式） | agent-locks.json 中的现有锁条目需重新解析 |
| TTL 300 秒 | 高（修改常量值） | SKILL.md 一行变更 |
| 锁获取时机（spawn 前） | 中（改为 Agent 声明式需要修改 Agent 端行为） | behavior-protocol.md + agent-dispatch-template.md 多行变更 |
| 任务去重 key（task_id） | 高（改为复合 key 需修改去重逻辑） | behavior-protocol.md 一段变更 |
| SYSGAP-043/044 关系（增强而非替代） | 高（改回原有 M7.6 即可） | behavior-protocol.md M7.6 回退 |

---

## 附录 B: 与 FIX-056 需求澄清报告的对应关系

| 需求澄清报告中的需求 | 本 ADR 对应方案 | 覆盖程度 |
|--------------------|---------------|---------|
| R1 (P0): 同一文件路径的修改互斥 | 决策 2（文件级锁）+ 第二道防线（文件锁） | 完整 |
| R2 (P1): 超时判定的客观化 | 决策 3（TTL 300s + git diff 辅助判定） | 完整 |
| R3 (P1): 重新 dispatch 前的安全确认 | 决策 3（超时判定流程：git diff → AskUserQuestion）+ 决策 5（任务去重） | 完整 |
| R4 (P2): 部分产出的接续 | TTL 超时判定流程中——git diff 有修改 → AskUserQuestion "保留当前状态"? → 新 Agent 从当前状态继续 | 部分（决策权给用户，非自动接续） |
| R5 (P2): 用户可见性 | BC-003 缓解措施（去重 BLOCK → AskUserQuestion） + 决策 3 超时判定流程（AskUserQuestion） | 完整 |
| IN scope: Coordinator 误判超时 → 重复 spawn | 第一道防线（任务去重） | 完整 |
| IN scope: 不同 task 但文件目标重叠 | 第二道防线（文件锁） | 完整 |
| IN scope: Agent 真超时后的安全重 dispatch | 决策 3（超时判定流程） | 完整 |
| IN scope: 文件级修改互斥 | 决策 2（文件级锁粒度） | 完整 |

---

## 附录 C: 设计原理 —— 为什么不是"在 Agent 平台层解决"

一个合理的质疑是："为什么不直接在 Agent 平台（Claude Code）层面阻止重复 spawn？这是平台能力，不是工作流能力。"

回答：

1. **工作流是 platform-agnostic**——`software-project-governance` 设计为跨 Claude Code / Codex / Gemini / 国内 agent CLI 的通用工作流。在 Agent 调度协议层（即本工作流层）实施并发防护，确保跨平台一致性。

2. **平台可能永远不会提供"Agent 存活状态查询 API"**——而 FIX-056 问题是现在就需要解决的。等平台能力 = 无限期推迟。

3. **Agent 平台即使提供"同一 task 不重复 spawn"的原语，也不会处理"不同 task 修改同一文件"的场景**——这需要工作流层的任务语义理解（哪些文件属于哪个 task、两个 task 的文件目标是否重叠）。平台层不知道 task 的语义。

4. **当前工作流已经在 Agent 调度协议层定义了 M7.6（并行调度安全）**——FIX-056 是 M7.6 的自然扩展，从"计划内并行"扩展到"计划外并发"。协议层的增强是最小、最自然的增强路径。

---

*本 ADR 由 Architect（老顾）基于 Analyst（阿析）的 FIX-056 需求澄清报告撰写。只做设计方案，不写实现代码。实现留给 Developer。*
*所有备选方案评估基于 Claude Code Agent 平台 2026-05 的工具约束。如平台提供 Agent 存活状态查询 API，TTL 判定机制可升级为更精确的实时查询。但核心设计（任务去重 + 文件锁）不依赖此假设。*
