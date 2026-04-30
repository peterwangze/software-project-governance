# Agent 失败模式文档

当 agent 不遵守行为协议时，用户需要系统性的故障排除路径。本文档列出已知的 agent 行为异常模式、检测方法、用户应急动作和预防机制。

**核心假设**：AI agent 不是确定性系统。成熟的工作流必须假设 agent 会出错，而不是假设 agent 会遵守所有规则。

---

## 失败模式 1：协议跳过（Protocol Skip）

**描述**：agent 未加载或忽略了 governance skill（SKILL.md），跳过所有治理动作（Gate 检查、证据记录、AskUserQuestion 触发）。这是最严重的失败模式——所有其他防护机制都依赖协议被加载。

**检测方法**：
- agent 从未输出 governance 相关的状态信息（当前阶段、Gate 状态）
- agent 使用内联文字提问（"要不要继续？"）而非 AskUserQuestion 工具
- agent 声称完成任务但没有补证据记录
- 会话开始时 agent 没有读 `.governance/plan-tracker.md`
- CLAUDE.md 的 bootstrap 步骤没有被执行

**用户应急动作**：
1. 确认 skill 已安装：检查 `.claude/skills/` 或插件市场是否包含 `software-project-governance`
2. 手动触发：输入 `/software-project-governance:governance-status` 看是否有响应
3. 重新加载：`/reload-plugins` 或重启会话
4. 如果协议持续不被加载，降级到手动模式：用户自行读 `.governance/plan-tracker.md`，手动记录证据

**预防机制**：
- CLAUDE.md bootstrap 是独立于 SKILL.md 的强制入口——即使 skill 未加载，bootstrap 步骤也应被执行
- 如果 bootstrap 也未执行，说明 CLAUDE.md 本身未被加载——检查项目根目录是否有 CLAUDE.md

---

## 失败模式 2：选择性执行（Selective Execution）

**描述**：agent 加载了协议但选择性执行其中的规则——执行容易的（如记录证据），跳过困难的（如 Gate 检查、审计执行）。这是最常见的失败模式，因为协议是一套规则集合，agent 可能"记住"部分而忽略其他。

**检测方法**：
- 证据被记录了，但 Gate 状态未更新（做了记录层，跳过了检查层）
- M5 AskUserQuestion 触发了，但 M8 自检没有执行
- 任务标记为"已完成"，但 plan-tracker 中的状态未同步更新
- 某些 P0 任务被跳过，直接做了 P1/P2 任务

**用户应急动作**：
1. 运行 `python scripts/verify_workflow.py check-governance` — 脚本会发现 agent 遗漏的治理动作
2. 手动检查 plan-tracker：对比"已完成"任务和 evidence-log 是否有对应证据
3. 要求 agent 自检：输入"执行 M8 自检"或"运行 governance-verify"
4. 如果选择性执行持续发生，切换为"所有决策都问我"模式（覆盖 M7.1 的默认模式）

**预防机制**：
- check-governance 脚本独立于 agent，能发现 agent 遗漏的治理动作（B 级自动化）
- M8 自检清单要求 agent 逐项检查——但不能仅依赖 agent 自检（见失败模式 6）

---

## 失败模式 3：幻觉式证据（Hallucinated Evidence）

**描述**：agent 声称完成了某任务并补了证据，但证据不指向任何可验证的持久化内容。常见形式：证据位置标注为"会话上下文"、声称运行了命令但未贴输出、循环引用（"详见 EVD-xxx"但 EVD-xxx 的内容就是同一句话）。

**检测方法**：
- 查看 evidence-log：搜索"会话上下文"——这些证据在会话结束后不可追溯
- 证据类型为"命令输出"但未附带实际输出内容
- 证据文件位置指向的文件不存在
- 证据之间存在循环引用
- 证据描述与任务目标不匹配（"完成了 A"但任务要求的是 B）

**用户应急动作**：
1. 对于"会话上下文"证据：要求 agent 明确写出可持久化的证据路径
2. 对于空输出声明：要求 agent 重新运行命令并贴完整输出
3. 对于循环引用：要求 agent 补充独立的证据描述
4. 运行 `python scripts/verify_workflow.py check-governance` 检查证据完整性

**预防机制**：
- check-governance 新增证据质量检查：检测"会话上下文"引用、循环引用、空输出声明（AUDIT-022）
- 每次交付时要求 agent 附上实际命令输出（TRF-R 原则）

---

## 失败模式 4：虚假闭环（False Closure）

**描述**：agent 声称"已完成"但没有实际验证——代码写完了但没运行 build/test，配置修改了但没验证是否生效。这是 PUA 红线一（闭环意识）要防止的核心问题。

**检测方法**：
- agent 说"已完成"但没有贴任何验证输出
- task 标记为"已完成"但证据为空或仅包含"代码已提交"
- 后续发现任务实际未完成（如文件未创建、配置未生效）
- git commit message 说"完成 X"但对应的文件变更不匹配

**用户应急动作**：
1. 要求 agent 运行验证命令并贴输出（不要接受"已完成"三个字）
2. 检查对应文件是否实际存在：读取声称已创建/修改的文件
3. 运行 `python scripts/verify_workflow.py` 检查文件完整性
4. 对于代码修改：要求 agent 运行 build + test 并贴输出

**预防机制**：
- PUA 红线一强制执行——没有验证输出的完成 = 自嗨
- M8 自检中的"已完成任务是否有证据"检查
- B 级自动化（check-governance）的独立验证

---

## 失败模式 5：跨会话失忆（Cross-Session Amnesia）

**描述**：agent 在上一会话中的上下文（当前阶段语义、未完成事项细节、用户偏好、讨论中的决策）在会话结束后完全丢失。下一会话 agent 仅能从 `.governance/` 文件重建——但如果加载不完整或解读错误，就会出现上下文断裂。人类项目经理有持续记忆，AI agent 每次会话是"失忆"状态。

**检测方法**：
- 新会话开始时 agent 没有提及上一会话的未完成任务
- agent 重复提出已在上一会话中讨论过的方案（不知道已经被否决）
- 用户需要在新会话中重新解释项目背景
- passed-with-conditions 的遗留项没有被优先处理
- 上一会话设定的"仅在关键决策停下来"模式没有被继承

**用户应急动作**：
1. 在新会话开始后立即检查 plan-tracker：确认当前阶段、活跃任务、未关闭的 Gate 条件
2. 告知 agent："上一会话我们在做 X，当前状态是 Y，请先读 plan-tracker"
3. 如果关键上下文丢失，手动记录到 `.governance/decision-log.md` 作为持久化记忆

**预防机制**：
- 会话结束时生成状态快照（AUDIT-029——跨会话记忆机制，待实现）
- CLAUDE.md bootstrap 确保每次会话第一动作是读 plan-tracker
- decision-log 中的决策记录提供持久化的"讨论记忆"

---

## 失败模式 6：自我审计矛盾（Self-Audit Contradiction）

**描述**：agent 被要求自我检查是否遵守协议（M8 自检），但不遵守协议的 agent 也不会诚实地自我报告违规。这造成了内在矛盾——审计者的可靠性和被审计者是同一个实体。

**检测方法**：
- agent 的 M8 自检总是通过，但外部验证（check-governance）发现问题
- agent 声称"所有用户问题都用了 AskUserQuestion"，但会话日志中出现了内联文字提问
- agent 声称"所有完成任务都有证据"，但 evidence-log 中存在缺失

**用户应急动作**：
1. 不要仅依赖 agent 自检——运行 `python scripts/verify_workflow.py check-governance` 做独立验证
2. 抽查：随机选 2-3 个 agent 声称"已完成"的任务，手动验证是否真的完成
3. 如果发现自检与独立验证不一致，告知 agent 哪个检查项不准确，要求修正

**预防机制**：
- AUDIT-031（M8 外部验证机制）——将自检从"agent 自我报告"升级为"agent 自我检查 + 脚本独立验证"双重机制
- check-governance 独立检测协议违规（不依赖 agent 诚实度）
- 华为蓝军思维：假设自我报告不可信，必须外部验证

---

## 失败模式 7：虚假归因（False Attribution）

**描述**：agent 遇到错误时给出未经验证的归因——"可能是环境问题"、"API 不支持"、"版本不兼容"——但未用工具实际验证这些假设。这是 PUA 红线二（事实驱动）要防止的核心问题。

**检测方法**：
- agent 使用了"可能是"、"估计是"、"应该是"等不确定性措辞，但没有跟进验证
- agent 建议"手动处理"或"建议用户 XXX"但没有穷尽自动化方案
- 错误信息被 agent 解读了，但没有搜索过该错误消息
- agent 声称"超出能力范围"但未列出已尝试的具体方案

**用户应急动作**：
1. 追问："你用什么工具验证了这个假设？贴出验证过程。"
2. 要求 agent 执行通用方法论 5 步（闻味道→揪头发→照镜子→执行新方案→复盘）
3. 拒绝接受未验证的归因——要求 agent 搜索后再下结论

**预防机制**：
- PUA 红线二强制执行——未验证的归因 = 甩锅
- PUA 通用方法论：遇到卡壳时先搜索，后假设
- 压力升级链：从 L1 温和失望到 L4 毕业警告

---

## 失败模式 8：计划漂移（Plan Drift）

**描述**：agent 在执行过程中逐渐偏离 plan-tracker 中的计划——跳过了高优先级任务、执行了非计划内的任务、改变了实施顺序而没有更新依赖表。漂移积累到一定程度后，项目实际状态与 plan-tracker 中的状态明显不一致。

**检测方法**：
- plan-tracker 中"进行中"的任务在多个会话中没有进展
- agent 执行的任务在 plan-tracker 中找不到对应条目（"不在计划里的活干了"）
- 依赖表中的执行顺序被打破（如跳过了 Tier 0 直接做 Tier 2）
- plan-tracker 中的任务状态与 evidence-log 不匹配

**用户应急动作**：
1. 每次会话开始时检查 plan-tracker，确认当前 Tier 和待执行任务
2. 如果 agent 执行的活不在计划里，要求先入账 plan-tracker 再执行
3. 如果执行顺序被打破，要求 agent 解释为什么打破依赖关系

**预防机制**：
- CLAUDE.md bootstrap Step 3：优先级确认——优先处理 P0 和 passed-with-conditions
- 实施路线图定义了严格的 Tier 顺序和执行纪律
- 每次会话结束时的状态摘要 + 下一次优先级确认（AskUserQuestion）

---

## 应急流程总览

## 失败模式 9：无版本管理环境下的治理盲区

**症状**：用户项目不使用 git/svn 等版本管理工具。pre-commit/post-commit hooks 无法安装。所有系统级约束（hook 阻断）失效，治理完全依赖 agent 自觉（失败模式 1~8）。

**检测方法**：
- governance-init 或 bootstrap 检测到 `.git/` 不存在 → 标记为"无版本管理环境"
- 输出约束降级声明

**用户应急动作**：
- `git init` → 重新运行 governance-init 安装 hooks
- 或接受降级模式——治理依赖 session 级检查

**降级模式（无 git 时的替代约束）**：
- Session 结束强制 `check-governance`，FAILED → MUST 修复后才能结束
- 连续 2 session FAILED → agent 提醒"建议 git init 获得自动阻断"

**根因**：系统级约束依赖 git hooks 作为执行载体。这是架构限制。

## 失败模式 10：M5 修复后对话习惯性违规（Post-Fix Conversational Regression）

**症状**：FIX-015 已修复所有源文件中的内联问题指令（`询问用户："..."` 已清除），verify_workflow.py Check 10 静态扫描通过（0 反模式），但 agent 仍然输出内联问题（如"要继续吗？"、"需要我继续吗？"）。用户在 FIX-015 上线后的下一次对话中立即发现了违规。

**检测方法**：
- 读取 CLAUDE.md SELF-CHECK —— 检查是否包含第 4 项（M5 预输出自检）
- 搜索 agent 最近输出中的内联问题关键词：`吗？`、`要不要`、`是否`、`需要我`、`Do you want`
- verify_workflow.py Check 10.4：检查 CLAUDE.md SELF-CHECK 是否包含 M5 预输出项

**用户应急动作**：
- 如果发现 agent 输出内联问句：直接说"你又绕过了 AskUserQuestion"——agent 会触发本失败模式的自检流程
- 检查 CLAUDE.md 是否包含 SELF-CHECK 第 4 项：不包含 → 运行 `/plugin update` 获取最新 bootstrap
- 切换到"所有决策都问我"模式——限制 agent 自主权，强制每个决策点都用 AskUserQuestion

**预防机制**：
- **CLAUDE.md SELF-CHECK 第 4 项**：在任何输出前扫描是否包含向用户提问的问句，如果发现 → 立即删除，改用 AskUserQuestion
- **SKILL.md M5.1 自中断协议**：agent 发现自己在输出内联问题 → STOP IMMEDIATELY → 删除 → 替换为 AskUserQuestion
- **Check 10 静态检测**：verify_workflow.py 检查 CLAUDE.md SELF-CHECK 是否包含 M5 项（Check 10.4）

**与 FIX-015 的关系**：
- FIX-015 修复的是**源头污染**（文件告诉 agent 输出内联问题）→ 静态检测 Check 10.1~10.3
- FIX-016 修复的是**对话习惯**（agent 自然产生内联问题）→ 预输出自检 Check 10.4
- 两个修复互补——源文件干净 ≠ agent 行为干净，因为内联问题是 LLM 训练数据的自然模式，不是文件教的

**根因**：LLM（包括 Claude）在训练数据中看到过数十亿次"要继续吗？""Shall I proceed?"这类自然对话收尾。这不是任何文件"教"的——这是模型的默认对话行为。FIX-015 假设"清除源文件 = 清除行为"，但行为改变需要预输出自拦截机制。此失败模式是 **CONSTRAINT-001 设计哲学在 M5 层面的体现**：agent 不会自觉遵守规则——必须有系统级强制力。但文本输出无法被 git hook 阻断——唯一的系统级强制力是预输出自检。

## 应急响应矩阵

当用户发现 agent 行为异常时，按以下顺序排查：

```
1. agent 加载了 skill 吗？
   → 检查：agent 是否知道当前阶段和 Gate 状态
   → 没加载：手动触发 /governance-status，或检查插件安装

2. agent 读了 plan-tracker 吗？
   → 检查：agent 是否提到了当前 Tier 和待执行任务
   → 没读：要求 agent 先读 .governance/plan-tracker.md

3. agent 在遵循协议吗？
   → 检查：agent 是否用了 AskUserQuestion（而非内联文字提问）
   → 没遵循：切换为"所有决策都问我"模式，限制 agent 自主权

4. agent 的证据可信吗？
   → 运行：python scripts/verify_workflow.py check-governance
   → 有问题：要求 agent 补全证据，不接受"会话上下文"引用

5. agent 的完成是真的吗？
   → 验证：读 agent 声称创建/修改的文件，运行 agent 声称执行过的命令
   → 虚假：执行 PUA 压力升级链，从 L1 开始
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 0.1.0 | 2026-04-26 | 初始版本：8 种失败模式 + 检测方法 + 应急动作 + 预防机制 |
