# Claude Code Project Guidance

## Governance Bootstrap（强制 — 每次会话第一动作）

**⚡ SELF-CHECK（在任何输出之前先问自己）**：
1. 我是否已经读了 `.governance/plan-tracker.md`？否 → **立即停止，先去读**

### Step 0: 确定双维度模式
读取 `.governance/plan-tracker.md` 的 `## 项目配置` 节，确认 `触发模式` 和 `操作权限模式`。

**治理开关——用户随时动态切换**：
会话中用户说"切换到最高权限模式"/"当前模式"等 → 立即切换并更新 plan-tracker。

**每次会话输出一句确认**：
> 🔍 Governance: {trigger_mode} × {permission_mode} | stage: {stage}, Gate {gate}: {status}

### Step 1: 读 plan-tracker + 跨会话恢复
读取 `.governance/plan-tracker.md`。**跨会话恢复**：读取 `.governance/session-snapshot.md`（如存在）。

**版本变化自动检测 + bootstrap 自升级**（用户更新后首次会话自动触发——零用户行动）：
1. 对比 plan-tracker `工作流版本` 与当前安装版本
2. IF 当前 > 记录 → 自动输出更新摘要 + 自动替换 bootstrap 段 + 自动补全 plan-tracker 缺失结构

### Step 2: 交叉验证（3 项强制检查）
1. 证据完整性 2. Gate 一致性 3. 风险过期

### Step 3: 阶段跳跃防护
用户请求跳过前置 Gate → MUST 警告风险。

### 干活前检查（每次收到任务时）
- 任务在计划跟踪表里吗？不在就先入账
- 做完后需要补什么证据？
- 用户视角三问：用户怎么获得？怎么知道？体验真的变了吗？

### 提问规则（强制）
**AskUserQuestion 是唯一合法的用户提问方式。**
**关键决策** — 永远停下来：范围变更/架构决策/发布决策/风险接受/外部依赖/模式变更
**危险操作确认** — default-confirm 下停下来：破坏性git/文件删除/外部副作用/不可逆操作

### 收工前检查（session 结束前）
1. 输出摘要 2. 补证据 3. 更新 plan-tracker 4. 写入 session-snapshot 5. commit 6. AskUserQuestion

### Bootstrap 变更纪律（MANDATORY）
MUST NOT 直接修改本文件添加新行为。MUST 先改 governance-init.md 模板。
