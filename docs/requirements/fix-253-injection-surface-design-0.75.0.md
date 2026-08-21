# FIX-253 — REQ-112 关键行为规则进入 DSH persona/SKILL 确定性注入面（设计文档）

- **日期**: 2026-08-21
- **作者**: Architect Agent（FIX-253 设计阶段产物；只读分析 + 本设计文档，未修改任何产品代码）
- **任务**: FIX-253（P1）——REQ-112 消费方，AUDIT-143 注入层主根因修复
- **承载版本**: 0.75.0（MINOR，DEC-143 候选）
- **上游输入**: `docs/requirements/audit-143-loop-planning-behavior-gap-0.74.0.md`（AUDIT-143 诊断）、DEC-143（修复链排布）、`.governance/execution-packets.json` FIX-253 执行包
- **状态**: Design Reviewer R0 = APPROVED_WITH_NOTES（unresolved_blockers=0，0 BLOCKING / 4 WARNING / 7 SUGGESTION）——本版为吸收 R0 发现的修订版；Reviewer 已裁定文档级小修免 R1 复审，修复核实由 Coordinator 承担。本文档不做最终决策——方案取舍由 Coordinator + 用户确认
- **修订**: R0 返工轮——W1（空推荐义务出处状态）/ W1b（step 6c 与 DEC-143 基线矛盾清理）/ W2（参数级出处补实现 + C3 引用错位修正 + OBS-1）/ W4（投影计数 12→13 ×2）/ ragged table row 修复（claim CLI 唯一 finding，§9.1 S3）/ S4+S7 转实现要求；各项定位见正文 R0-* 标注

---

## 1. 目标

### 1.1 问题定义

AUDIT-143 确认的注入层主根因（诊断报告 §2.0.1，逐字比对实证）：Coordinator 的三条关键行为规则——

| ID | 规则 | canonical 位置（第四层按需文件） |
|----|------|-------------------------------|
| **R1** | T1-T4 复审触发器（NEEDS_CHANGE → MUST 返工复审；熔断；终态判定） | `references/behavior-protocol.md` M7.4 step 4.6（L526-532） |
| **R2** | M7.4 step 6「任务完成 → MUST 依赖分析 + 推荐 top-1~3 + 不得直接结束」 | `references/behavior-protocol.md` M7.4 step 6（L552-556） |
| **R3** | 依赖排序交互规则（「接下来做什么」类选项 MUST 可追溯依赖分析输出，禁止机械枚举） | `references/interaction-boundary.md` L187 / L217 |

——只存在于第四层按需文件，DSH 会话的确定性注入链（① persona `adapters/dsh/agent.cordis.yml.template` L30-62 → ③ 入口 SKILL.md）**不携带**。行为是否发生全靠 Coordinator 自觉读取第四层文件，而 M2 预加载清单（behavior-protocol.md L77-82）不强制该读取。用户观察到的五簇缺陷（1a/1b/2a/2b/2c）中有四簇直接由此断链放大。

附带缺陷：persona 模板 L33 版本号硬编码 `v0.73.0`，未随 0.74.0 同步（FIX-250 漏网），且对现有两个版本机器检查均不可见（见 §3.2）。

### 1.2 设计目标

1. **G1**：R1/R2/R3 的等效强约束进入确定性注入链携带面——DSH 会话无需任何按需读取即受约束。
2. **G2**：修复 L33 版本漂移，并建立机器锚定机制使该类漂移从此被 check 拦截（防再发）。
3. **G3**：注入内容有机器可查的验收信号（grep/check 可证）+ 会话可观察的行为级验收信号。
4. **G4**：不破坏现有投影/版本一致性基础设施（check-projection-sync、check-version-consistency、test_dsh_adapter 契约）——改动后两者仍 PASS。

### 1.3 非目标（范围边界，DEC-143 排布）

- **不实现** REQ-107（复审链机器持久化/review-record 强制）、REQ-108（完成必产出推荐的 Check 化）、REQ-109（交互可追溯的 Check 化）、REQ-111（新事项分析覆盖面）、REQ-113（检测前移 pre-commit）、REQ-114（classic gate 宿主 loop 接线）——按 DEC-143 在放大器（REQ-112/110）生效后推进。本设计仅在注入文本措辞上与它们保持前向兼容（见 §6.1 注）。
- **不修改** launch.py 的生成逻辑语义（方案 C 论证后排除，见 §5.3）。
- **不做** 行为级最终验证（需真实 DSH 会话，属实现后验收，见 §9.2）。

---

## 2. 背景摘要（引用 AUDIT-143，不重复论证）

- 三环节断裂结论：0.73.0 修复全落工具层与静态检查层；「工具被真实会话调用」「行为规则到达 Coordinator 工作上下文」「推荐数据非空」三个环节全部断裂（诊断报告 §1）。
- 注入链四层现状（§2.0.1）：① persona 与 ③ SKILL.md 均不含 M7.4/交互推荐规则；④ behavior-protocol.md 含但无任何强制加载机制。
- 核心不对称（§2.0.3）：Check 有效性取决于判定源不可伪造性——change-triage 成活（JSON 机器记录）、Check 21/29/30 被手写合规绕过。**注入面修复是把「规则到达上下文」从不依赖自觉的层面解决，与 Check 判定源改造（REQ-107~109）互补，不替代。**
- DEC-143 决策 1（交互基线）：任务完成/关键节点后的推进交互 = **自动推荐 + 用户确认**——机器依赖分析产出 top-3 候选+理由，用户确认或改选。注入文本 MUST 携带该基线。

---

## 3. 现状事实基线（本设计新增核查）

### 3.1 注入链文件与关键行（2026-08-21 读取实证）

| 文件 | 关键事实 |
|------|---------|
| `adapters/dsh/agent.cordis.yml.template` | 247 行。persona text L30-62：bootstrap 3 步 + SELF-CHECK 4 条 + 模式确认 + Agent Team 映射 + hooks + 升级。**无 R1/R2/R3**。L33：`你是 software-project-governance 治理工作流（v0.73.0）的 Coordinator`——版本硬编码于正文，无机器锚定 |
| `skills/software-project-governance/SKILL.md` | 302 行，frontmatter `version: 0.74.0`（版本权威源）。L48-58 铁律段含锁检查/后置审查 spawn；L219 对 behavior-protocol.md 仅**引用式**；L251/L254 将其列入「按需读取」。**无 R1/R2/R3** |
| `adapters/dsh/AGENTS.md.template` | 53 行 thin pointer（launch.py docstring L23-24 明确「must not duplicate workflow rules」）。L3 `@bootstrap-version: 0.74.0`（正确同步）。**无 R1/R2/R3** |
| `adapters/dsh/launch.py` | 227 行。`install_preset` = 纯 token 替换（L112-121：3 个 `__GOVERNANCE_*__` token），替换后校验无残留 token。`--bootstrap-project` 渲染 AGENTS.md.template（L145-168） |
| `references/behavior-protocol.md` | 778 行。M7.4 step 4.6 状态机+强制条款 C1-C7+T1-T4（L493-544）；step 6 a-d（L552-556）；M1.2 快速通道（L46-57） |

### 3.2 机器锚定面覆盖分析（关键新事实——L33 漂移漏网的机制解释）

| 检查机制 | 覆盖范围 | 是否覆盖 adapters/dsh 模板 |
|---------|---------|--------------------------|
| `check-version-consistency`（`infra/checks/version.py` VERSION_PATHS） | SKILL.md frontmatter（权威）+ manifest.json + .claude-plugin/{plugin,marketplace}.json + .codex-plugin/.zcode-plugin/.chrys-plugin plugin.json + verify_workflow.py REQUIRED_SNIPPETS + 4 hooks `@version` + CHANGELOG 最新版本 + plan-tracker 工作流版本（WARN） | **否**——adapters/dsh 下任何文件不在 VERSION_PATHS |
| `check-projection-sync`（`core/version-projections.json` 13 个投影 + manifest `release_projection_contract`） | fixture-skill（byte_copy）+ core-manifest + claude-plugin + claude-marketplace + codex/zcode/chrys-plugin + package.json + fixture-plan + 4 hooks `@version`（transformed_text） | **否**——无任何 adapters/dsh 投影条目 |
| `@bootstrap-version` 陈旧标记链（FIX-238.2） | AGENTS.md.template L3（正确 0.74.0）；但唯一机器守护是**硬编码测试断言** `test_dsh_adapter.py` L343 `assertIn("@bootstrap-version: 0.74.0", text)`——每次发版需人工同步测试字面量 | 部分（仅 AGENTS.md.template，且靠测试字面量） |

**结论**：L33 漂移不是偶发失误，是**结构性盲区**——persona 模板的版本串对全部现有机器检查不可见。防再发机制必须把该文件纳入投影注册表（transformed_text 模式，与 hooks `@version` 完全同构），而不是再补一处人工纪律。

### 3.3 测试契约现状（注入改动的受影响面）

- `test_dsh_adapter.py`：`test_template_uses_only_known_tokens` / `test_template_contains_every_launcher_token`（token 契约）；`test_launch_link_generation_is_pure_substitution`（**生成 = 纯 token 替换**——方案 C 的硬约束）；`test_template_required_rows`（必需 marker 含 `ask_user_question`/`resolve_entry.py` 等）；`test_bootstrap_template_contract`（含硬编码版本断言 L343）。
- SKILL.md 是 version-projections 的 byte_copy 源（→ `project/e2e-test-project/skills/software-project-governance/SKILL.md`）——**SKILL.md 任何编辑必须同步 `release-projection --write` 重生成 fixture**，否则 check-projection-sync FAIL（fixture drift）。

---

## 4. 设计原则

1. **压缩投影，不搬运本体**：canonical 规则全文留在第四层（behavior-protocol.md / interaction-boundary.md）；注入面只携带一句话形式的**最小契约集**，并显式标注投影关系。注入面不是规则的定义处。
2. **单一权威源锚定版本**：版本串只认 SKILL.md frontmatter 一个权威源；模板中的版本串由投影机制生成与校验（与 hooks `@version` 同构），杜绝第二权威源。
3. **锚点检查而非全文相等**：注入面守护 check 断言**稳定关键词锚点**（如 `复审必达`/`task-priority-analysis`/`NEEDS_CHANGE`）存在，不断言与 canonical 全文相等——prose 全文相等检查脆弱（REQ-112 验收信号 2 的「与 check-projection-sync 同族」即此模式）。
4. **分层单向依赖**：canonical（第四层）→ 入口 SKILL.md（入口层）→ 平台模板（适配层）→ 检查锚点（基础设施层）。箭头只向左，检查层不定义规则文本（见 §8）。

---

## 5. 方案（候选与取舍）

四个候选方案。**推荐方案 A**；B/C/D 论证后排除（理由如下）。

### 5.1 方案 A —— 双点最小注入 + 投影锚定 + 锚点检查（推荐）

**结构**：

1. **persona 模板**（DSH 会话 system 级，无条件在上下文）注入 R1/R2/R3 压缩契约块（~13 行，≤1KB）；
2. **SKILL.md**（全平台共享入口层，bootstrap 第一动作加载）注入略完整契约段（~14 行）——这是**最小契约集的 canonical 投影定义处**，Claude/Codex/Gemini 等平台经由各自 bootstrap 链加载 SKILL.md 即获得同等覆盖；
3. **AGENTS.md.template**（DSH 项目级 thin pointer）仅加一行指针（不复制规则，维持 thin-pointer 纪律）；
4. **版本漂移**：L33 版本串纳入 version-projections.json（transformed_text）+ manifest 契约更新；AGENTS.md.template `@bootstrap-version` 同批纳入；测试断言去字面量化（动态读权威版本）；
5. **防再发**：新增 `check-injection-contract`（锚点检查，注册进 check-governance）。

**取舍**：

- ✅ 双点冗余与现有注入链结构一致（persona 携带骨架规则如 SELF-CHECK 的既有模式；SKILL.md 是全平台共享点）——AUDIT-143 指控的「①③两层都不含」被同时修复。
- ✅ 不触碰 launch.py 生成语义——`test_launch_link_generation_is_pure_substitution` 等测试零改动风险。
- ✅ 投影机制复用现成引擎（hooks @version 先例），防再发成本 = 1 条投影 + 1 条 manifest 契约 + 测试动态化。
- ⚠️ 代价：persona 与 SKILL.md 两处压缩文本存在双源失同步风险 → 由锚点检查 + §7.3 同步纪律缓解（BC-2）。
- ⚠️ 代价：注入面 token 增加（persona +~0.8KB / SKILL.md +~1.2KB）→ 预算约束见 §7.1。

### 5.2 方案 B —— SKILL.md 单点注入 + persona 指针（排除）

只改 SKILL.md；persona 与 AGENTS.md.template 各加一行「关键行为契约见 SKILL.md」指针。

- 排除理由 1：persona 指针仍依赖「skill 实际被加载」这一 prose 义务。若 Coordinator 跳过 bootstrap step 1，R1/R2/R3 全部失守——而 SELF-CHECK/模式确认等骨架规则恰恰因为直接内嵌 persona 才不依赖该前提。把三条「必须不依赖自觉发生」的行为规则挂在「自觉加载」的前提上，与 REQ-112 的设计目标（「无需依赖主动读第四层文件」）逻辑上自我削弱。AUDIT-143 佐证：① persona 是唯一无条件注入层，② 用户会话 system prompt 即来自 ①——这是链上最硬的一环。
- 排除理由 2：REQ-112 验收信号 1 明确列出了 `agent.cordis.yml.template` 含最小契约集（一句话形式）作为首选形态。方案 B 走「或等价机制」分支，验收说服力弱。
- 保留价值：其「单点定义」思想被方案 A 吸收——**完整契约段只定义在 SKILL.md**，persona 携带的是它的再压缩投影（§4 原则 1）。

### 5.3 方案 C —— launch.py 生成时动态装配（排除）

新增第 4 个 token（如 `__GOVERNANCE_CONTRACT__`），launch.py 在 install/sync 时从 canonical 文件（behavior-protocol.md 标记段或新文件）提取契约文本注入 persona。

- 排除理由 1：破坏「生成 = 纯 token 替换」确定性契约（`test_launch_link_generation_is_pure_substitution` 直接断言生成输出等于模板纯替换）——需重构该测试契约与 token 契约测试，引入超出 FIX-253 范围的适配层语义变更。
- 排除理由 2：标记段提取对 prose 编辑脆弱（canonical 改措辞 → 提取静默失配或失败）；模板文件不再完整可审（审阅者看不到实际注入内容，可审查性下降——本仓库对模板内容的审查恰恰依赖文件即事实）。
- 排除理由 3：preset 安装态时滞更严重——契约更新必须显式 `--sync` 才到达 persona（link 模式只链 skills/ 目录，不链 persona 文本）；方案 A 的模板是 git 跟踪文件，pull 后 `--sync` 重写 preset 即获得新文本，路径相同但少一层间接。
- 保留价值：其「单一物理源」目标由方案 A 的锚点检查达成等效守护（漂移即 FAIL）。

### 5.4 方案 D —— 不注入，纯 Check 事后拦截（排除）

不改注入面；扩展 Check 21/30 或新增 pre-commit 检查，在 commit 前拦截「NEEDS_CHANGE 无 R{n+1}」「完成无推荐快照」。

- 排除理由：这是 REQ-107/108/113 的路线（DEC-143 已排布在其后）。检测时序再前移也是**事后**——拦截发生时用户在会话中已感受到缺失（AUDIT-143 §2.1 检测时序断链）；且 Check 判定源可手写绕过的不对称（§2.0.3）未解决。规则不进上下文，agent 连「该做什么」都不知道，Check 只能抓「没做」。与 REQ-112 互补而非替代，单独采用不成立。
- 保留价值：Check 强化在 REQ-107/108/113 推进；本设计的 `check-injection-contract` 只守护**注入面自身**的完整性，不越界做行为检测。

---

## 6. 推荐方案（A）详设——逐文件修改点清单

> 以下为本设计产出的修改规范（实现由 Developer 在后续阶段执行；`skills/**`、`adapters/**` 均为产品代码路径，MUST 走 Governance Developer + 审查链）。所有行号以 2026-08-21 读取态为准。

### 6.1 `adapters/dsh/agent.cordis.yml.template`（persona 注入 + 版本修复）

**改动点 1 — L33 版本漂移修复（机器锚定，见 §7）**：

```diff
- 你是 software-project-governance 治理工作流（v0.73.0）的 Coordinator，不是单 agent 任务执行者。
+ 你是 software-project-governance 治理工作流（v0.74.0）的 Coordinator，不是单 agent 任务执行者。
```

实现时以 `release-projection --write` 写入（值=当时 SKILL.md frontmatter 权威版本；落地 0.75.0 时由发版链自动变为 0.75.0），此后由投影检查守护。

**改动点 2 — 新增关键行为契约块**。位置：`Agent Team（DSH 映射）` 块（现 L52-57）之后、`Git hooks`（现 L59）之前。注入原文（YAML `text: |-` 块内，缩进与相邻段一致）：

```text
关键行为契约（MUST——不依赖任何按需读取即生效；完整规则 behavior-protocol.md M7.4 / interaction-boundary.md）：
- 复审必达：Reviewer 结论 NEEDS_CHANGE（含 NEEDS_CHANGES）且 round<3（触发器 T1）→ MUST 立即 spawn 同一 Reviewer 复审（round+1，re-spawn prompt 注入前轮 review 报告路径），不得跳过复审标记完成，不得输出"是否需要复审"类问句——复审是强制义务；round≥3 仍 NEEDS_CHANGE（触发器 T2）→ MUST 转 BLOCKED + escalation（ask_user_question）。仅 APPROVED 或带 unresolved_blockers=0 的 APPROVED_WITH_NOTES 是通过终态。
- 完成必推荐：任务标记已完成 → MUST 运行 task-priority-analysis（工具缺失/失败按 fail-closed 升级，不得跳过分析），调用快照记入 evidence-log → 从 unblocked + 最高优先级未完成任务中推荐 1~3 个候选（含依赖理由），按"自动推荐 + 用户确认"呈现（DEC-143 交互基线）；推荐为空时 MUST 呈现结构化空原因，禁止机械枚举未完成任务充数。除非无未完成任务或用户明确选"暂停"，MUST NOT 因任务完成直接结束会话。
- 选项必带依据：凡向用户呈现"接下来做什么"类选项，每个候选 MUST 可追溯到 task-priority-analysis 输出并携带依赖状态理由；机械枚举未完成事项 = 违规。
```

规模：~13 行 / ~0.9KB（预算约束见 §7.1）。

**出处状态（R0-W1 修订）**：R1 段 → canonical M7.4 step 4.6 触发器 T1/T2 + 终态条款 C4（L526-531）；R2 段主体（分析 fail-closed / 快照入 evidence-log / 推荐 1~3 / 呈现 / 不得直接结束）→ canonical M7.4 step 6a-6d（L552-556）+ DEC-143 交互基线；**R2「推荐为空时 MUST 呈现结构化空原因，禁止机械枚举」句为注入面新增——canonical step 6 无对应源条款**（REQ-110/FIX-254 降级推荐的注入面前置），canonical 未同步，**同步义务随实现任务**：与 §6.7 注记同批写回 canonical step 6，或随 REQ-110 落地时写回（先到者负责）；R3 段 → interaction-boundary.md L187/L217。round=3 处 canonical C3/T2 既有矛盾见 §6.9 OBS-1（注入文本以 T1/T2 语义为准）。

### 6.2 `skills/software-project-governance/SKILL.md`（全平台契约段）

**改动点 — 新增「关键行为契约」小节**。位置：`### 你的铁律（违反 = 流程违规）` 段末尾（现 L58 之后）、`## 产品代码 vs 治理记录边界`（现 L60）之前——与铁律同簇，保持 MUST 级义务聚合。注入原文：

```markdown
### 关键行为契约（MUST——注入面最小契约集，FIX-253/REQ-112；完整规则见 references/behavior-protocol.md M7.4）

以下三条与铁律同级，违反任何一条 = 流程违规。本段是注入面的 canonical 投影定义处（DSH persona 携带其压缩形式；`check-injection-contract` 锚点守护）：

1. **复审必达（M7.4 step 4.6，T1-T4）**：收到 Reviewer 审查结论后 MUST 立即判定并执行——结论含 NEEDS_CHANGE 且 round<3（触发器 T1）→ spawn 同一 Reviewer 复审（round+1，prompt 注入前轮 review 报告路径为强制读取项），不得跳过、不得询问；round≥3 仍 NEEDS_CHANGE（触发器 T2）→ BLOCKED + escalation AskUserQuestion；APPROVED 或带 `unresolved_blockers=0` 的 APPROVED_WITH_NOTES 为唯一通过终态；BLOCKED → escalation。
2. **完成必推荐（M7.4 step 6，FIX-223/237.5 增强）**：任务标记已完成 → MUST 运行 `task-priority-analysis`（fail-closed：工具缺失/失败时升级，不得跳过）并将调用快照记入 evidence-log → 推荐 1~3 个候选（依赖排序 + 每项依赖理由），按 DEC-143 交互基线「自动推荐 + 用户确认」呈现；推荐为空 → 呈现结构化空原因（禁止机械枚举）；除无未完成任务或用户明确选"暂停"外，MUST NOT 直接结束会话。
3. **选项必带依据（interaction-boundary.md 任务排序行 + 反打断违规表）**：凡向用户呈现"接下来做什么"类选项，选项 MUST 可追溯到依赖分析输出（排序候选 + 每项依赖状态理由），禁止机械枚举未完成事项。
```

规模：~10 行 / ~1.2KB。

**出处状态（R0-W1 修订）**：第 1 条 → canonical M7.4 step 4.6 触发器 T1/T2 + 终态条款 C4；第 2 条主体 → canonical step 6a-6d + DEC-143 交互基线；**第 2 条「推荐为空 → 呈现结构化空原因」短句为注入面新增——canonical step 6 无对应源条款**（REQ-110 契约的注入面前置），canonical 未同步，**同步义务随实现任务**（与 §6.7 注记同批写回 canonical step 6，或随 REQ-110 落地，先到者负责）；第 3 条 → interaction-boundary.md L187/L217。参数级出处（R0-W2）：round<3 = 触发器 T1、round≥3 = 触发器 T2；round=3 处 canonical C3/T2 既有矛盾见 §6.9 OBS-1。

**配套必做**：编辑后运行 `release-projection --write` 重生成 fixture 镜像（`project/e2e-test-project/skills/software-project-governance/SKILL.md` 为 byte_copy 投影），否则 check-projection-sync FAIL。

> **与 REQ-107~111 的前向兼容注**：注入文本措辞已按「复审链机器持久化（REQ-107）」「推荐快照 Check 化（REQ-108）」「空推荐降级（REQ-110）」的验收形态预留接口（fail-closed / 结构化空原因 / 快照记 evidence-log），后续 REQ 落地时无需改写注入面语义，只加机器路径。

### 6.3 `adapters/dsh/AGENTS.md.template`（thin pointer 单行指针）

**改动点 — SELF-CHECK 节新增第 5 条**（现 L26 之后）：

```markdown
5. 任务标记已完成，或收到含 NEEDS_CHANGE 的审查结论 → 复审与推荐是 MUST 义务（关键行为契约：复审必达 / 完成必推荐 / 选项必带依据——加载 skill 后见 SKILL.md「关键行为契约」段）。
```

不复制规则本体，维持 launch.py docstring 的 thin-pointer 纪律；为「未用 governance 预设、仅项目级 AGENTS.md 引导」的会话提供契约存在性信号（该场景规则本体经 SKILL.md 到达）。

### 6.4 `skills/software-project-governance/core/version-projections.json` + `core/manifest.json`（版本锚定）

version-projections.json `projections` 数组新增两条（与 hooks `@version` transformed_text 同构）：

```json
{"id": "dsh-persona-version", "kind": "transformed_text",
 "target": "adapters/dsh/agent.cordis.yml.template",
 "pattern": "治理工作流（v[0-9]+\\.[0-9]+\\.[0-9]+）",
 "replacement": "治理工作流（v{version}）", "count": 1},
{"id": "dsh-agents-bootstrap-version", "kind": "transformed_text",
 "target": "adapters/dsh/AGENTS.md.template",
 "pattern": "(?m)^> @bootstrap-version: [0-9]+\\.[0-9]+\\.[0-9]+$",
 "replacement": "> @bootstrap-version: {version}", "count": 1}
```

`core/manifest.json` 的 `release_projection_contract.projection_ids` **必须同 commit 追加** `"dsh-persona-version"` 与 `"dsh-agents-bootstrap-version"`——投影引擎对注册表与 manifest 契约做集合相等校验（projection.py L137-141），漏改即 BLOCKED（fail-closed，by design）。

> `@bootstrap-version` 语义注记：其含义是「模板最低引导版本」，理论上允许 ≥ 权威版本；现行实践为相等（测试断言 0.74.0 == current）。锚定为相等消除了「测试字面量人工同步」这一再发通道，语义收紧为「随发版走」——与 FIX-238.2 陈旧判定（< active_version 即陈旧）兼容。

### 6.5 `skills/software-project-governance/infra/verify_workflow.py`（新检查）

新增锚点检查（REQ-112 验收信号 2 的承载）：

- 字面量清单（命名建议，实现可调）：

```python
INJECTION_CONTRACT_ANCHORS = {
    "adapters/dsh/agent.cordis.yml.template": [
        "关键行为契约", "复审必达", "NEEDS_CHANGE", "完成必推荐",
        "task-priority-analysis", "选项必带依据",
    ],
    "skills/software-project-governance/SKILL.md": [
        "关键行为契约", "复审必达", "完成必推荐",
        "task-priority-analysis", "选项必带依据",
    ],
    "adapters/dsh/AGENTS.md.template": ["关键行为契约"],
}
```

- 判定：目标文件存在且包含全部锚点，否则按文件+缺失锚点 FAIL。
- 接线：注册进 `check-governance` 聚合检查；可选独立子命令 `check-injection-contract`（与 check-projection-sync 同族注册模式，verify_workflow.py L20306-20316 先例）。
- **插入位置约束（R0-S4）**：`INJECTION_CONTRACT_ANCHORS` 字面量在 verify_workflow.py 中的定义位置 MUST 避让 `infra/checks/version.py` L58 的正则锚定区——该正则（`REQUIRED_SNIPPETS\s*=\s*\{(?P<body>.*?)\n\}\n{2,}# ── Manifest`）要求 REQUIRED_SNIPPETS 块的收尾 `}` 之后紧跟 ≥2 个换行与 `# ── Manifest` 注释行；若把新字面量插入该区间（或扰动其空行结构），check-version-consistency 将报 `[FAIL] verify_workflow.py snippet: REQUIRED_SNIPPETS block not found`。建议放置于远离 REQUIRED_SNIPPETS…`# ── Manifest` 区段的其它常量定义区；实现后 MUST 运行 check-version-consistency 验证 S5 不回归。
- 边界：只断言**存在性**，不断言全文相等（§4 原则 3）；不做行为检测（不越 REQ-107/108/113 的界）。

### 6.6 `skills/software-project-governance/infra/tests/test_dsh_adapter.py`（测试同步）

1. `test_template_required_rows`：markers 列表追加 `"关键行为契约"`、`"复审必达"`、`"完成必推荐"`、`"task-priority-analysis"`。
2. `test_bootstrap_template_contract`：删除硬编码 `"@bootstrap-version: 0.74.0"` 断言，改为动态——从 SKILL.md frontmatter 提取权威版本，断言 `f"@bootstrap-version: {version}"` 存在（发版零人工同步）；追加 `"关键行为契约"` 锚点断言。
3. 新增测试：persona 模板版本串 == SKILL.md frontmatter 版本（投影达成态断言，可调用 `build_projection_plan` 验证两条新投影 count 命中=1）；AGENTS.md.template 锚点存在。
4. `test_launch_link_generation_is_pure_substitution` / token 契约测试：**预期零改动**（无新 token）——若实现偏离本设计引入 token，即为范围违规信号。

### 6.7 `skills/software-project-governance/references/behavior-protocol.md`（canonical 侧可追溯注记，推荐伴生小改）

M7.4 step 4.6 的「FIX-224 确定性触发器」块（L526）之前新增注记：

```markdown
> **最小契约投影（FIX-253/REQ-112）**：本节 T1-T4、step 6 与 interaction-boundary.md 任务排序规则的压缩形式由 SKILL.md「关键行为契约」段与 DSH persona（agent.cordis.yml.template）携带；`check-injection-contract` 锚点守护同步。修改本节关键词（复审/NEEDS_CHANGE/task-priority-analysis/依赖理由）时 MUST 同步注入面，否则 check FAIL。**step 6c 交互基线（DEC-143，R0-W1b 修订）**：step 6c 原「否则可自主执行推荐项并在完成后再次推荐」分支按 DEC-143 废止——任务完成后的推荐统一按「自动推荐 + 用户确认」呈现（选项含推荐候选与「自主执行推荐项」，由用户确认或改选，而非 agent 默认自主执行）；「当且仅当推荐项涉及关键决策（M5.3）时强制 AskUserQuestion」的既有规则不变。step 6 另补一句「推荐为空 → 呈现结构化空原因（禁止机械枚举）」（注入面已先行，出处状态见 §6.2 注）。
```

目的：canonical↔projection 双向可追溯（BC-2 缓解），并把 DEC-143 交互基线落到 canonical 侧。**R0-W1b 修订**：不再以「远程注记」方式搁置 step 6c 与 DEC-143 的正文矛盾——注记文本显式废止 step 6c 的「否则可自主执行推荐项」分支，统一为「自动推荐 + 用户确认」（「自主执行推荐项」保留为用户确认时的选项之一，不再是 agent 默认行为）；涉及关键决策强制 AskUserQuestion 的既有规则不变。canonical step 6c/step 6 正文的对应改写（替换该分支句 + 补空推荐句）由实现任务随本注记同批执行。

### 6.8 修改面总览与依赖顺序（实现批次建议）

| 序 | 文件 | 类型 | 依赖 |
|----|------|------|------|
| 1 | behavior-protocol.md 注记（§6.7） | 产品代码（references） | 无 |
| 2 | SKILL.md 契约段（§6.2） | 产品代码（入口层） | 无 |
| 3 | persona 模板契约块 + L33 版本（§6.1） | 产品代码（适配层） | 无 |
| 4 | AGENTS.md.template 指针行（§6.3） | 产品代码（适配层） | 无 |
| 5 | version-projections.json + manifest.json 契约（§6.4） | 产品代码（核心层配置） | 3、4 文本定型（pattern 命中） |
| 6 | verify_workflow.py 锚点检查（§6.5） | 产品代码（基础设施层） | 2、3、4 文本定型（锚点词）；插入位置避让 version.py L58 正则锚定区（§6.5 R0-S4） |
| 7 | test_dsh_adapter.py 同步（§6.6） | 产品代码（测试） | 1-6 |
| 8 | `release-projection --write`（重生成 fixture + 写入两条新投影） | 命令执行 | 5 |
| 9 | 全量验证：check-projection-sync / check-version-consistency / check-governance / test_dsh_adapter | 命令执行 | 1-8 |
| 10 | `.governance/execution-packets.json` FIX-253 `acceptance_contract.command` 升级（grep 'T1' → §9.1 S1-S4 语义锚定组合） | 治理记录（Coordinator 快速通道）——**强制配套，不可选**（R0-S7：注入文本落地后原命令必然失配） | 3 落地后、与 S1-S8 验收同批 |

### 6.9 观察项登记（R0-W2——canonical 既有矛盾，不在本轮修改范围）

- **OBS-1（round=3 熔断边界矛盾）**：canonical M7.4 step 4.6 内部，C3 分支文本（behavior-protocol.md L519「round ≤ 3 且 NEEDS_CHANGE → 继续返工」）与 T2（L529「round ≥ 3 → MUST 转 BLOCKED + escalation」）在 round=3 处方向相反：按 C3 分支文本，round=3 的 NEEDS_CHANGE 应继续返工（派生 R4），与 C3 自身「最大复审轮次 = 3」的标题语义及 T1 的 round<3 触发边界（round=3 不再 spawn）冲突；C5（L522）「round>3 的 APPROVED…」又暗示 round 可大于 3。注入文本采用 **T1/T2 语义**（round<3 复审、round≥3 熔断——在 round=3 点较 C3 分支文本更保守：提前终止）。canonical 对齐（统一为 T2 语义并将 C3 分支条件修正为 round<3，或显式澄清 round 计数定义）不在本轮范围——移交 REQ-107（复审链 canonical 对齐）或独立 canonical 修订任务；本轮仅登记，不修改 canonical 产品文件。

---

## 7. L33 版本漂移修复 + 防再发机制（验收标准 3）

### 7.1 修复本体

见 §6.1 改动点 1：`v0.73.0` → 权威版本（实现时点为 0.74.0；0.75.0 发版链自动升为 0.75.0）。修复动作本身通过 `release-projection --write` 执行，即「修复」与「锚定」是同一动作——修复后的值就是投影引擎的输出。

### 7.2 机器锚定方式（防再发，四层）

1. **投影注册表条目**（dsh-persona-version，§6.4）：版本串与 SKILL.md frontmatter 强制相等——发版 `write-projections` 自动改写、`check-projection-sync` 漂移即 FAIL。机制与 hooks `@version` 完全同构（既有先例，零新机制）。
2. **manifest 契约绑定**：projection_ids 集合相等校验使「悄悄删掉该投影条目」成为 BLOCKED 错误——防再发机制自身不可被无声移除。
3. **测试去字面量化**（§6.6.2）：测试动态读权威版本，发版零人工同步点——消灭「测试硬编码 0.74.0」这一 FIX-250 漏网的姊妹通道（AGENTS.md.template 的 @bootstrap-version 当前仅靠该测试守护）。
4. **锚点检查附带**：`check-injection-contract` 的 persona 锚点组含版本携带段所在文件（可选追加 `"治理工作流（v"` 锚点串，确保版本句存在）。

### 7.3 同步纪律（流程侧，写入 canonical 注记 §6.7）

canonical 关键词变更 → MUST 同 commit 更新注入面锚点 → check FAIL 强制（漏更即红）。注入面文本变更 → 锚点清单同 commit 更新（INJECTION_CONTRACT_ANCHORS 是唯一需要与文本共同演进的字面量）。

### 7.4 被排除的防再发替代方案

- **version.py VERSION_PATHS 追加条目**：只检测不写回（无自动修复），且与投影注册表形成两处判定（可能级别不一致：FAIL vs WARN）。排除为独立机制；投影注册表是唯一权威判定面（单一权威源原则 §4.2）。未来若需要 CLI 快速诊断可作只读补充，不参与门禁。
- **删除 persona 版本串**（消灭漂移类别）：最彻底（零维护），但 persona 失去即时自标识（skill 加载失败时唯一版本线索），且偏离任务框架「修复漂移」而非「移除字段」。作为备选记录，不推荐。

---

## 8. 模块分层与无循环依赖论证（硬门槛）

```
第四层 canonical（behavior-protocol.md / interaction-boundary.md）   规则定义（唯一）
        │  （压缩投影，单向）
        ▼
入口层 SKILL.md「关键行为契约」                                      契约的 canonical 投影定义处
        │  （再压缩投影，单向）                ┌──────────────────────┐
        ▼                                      │ AGENTS.md.template    │
适配层 DSH persona（agent.cordis.yml.template） │ （指针→SKILL.md，单向）│
        │                                      └──────────────────────┘
        │  （锚点存在性断言，单向读取）
        ▼
基础设施层 verify_workflow.py INJECTION_CONTRACT_ANCHORS + version-projections.json + manifest.json
```

- 依赖方向严格单向（canonical → 入口 → 适配 → 检查/锚定）；检查层只读取上层文本断言锚点，**不定义任何规则文本**；注入面不回写 canonical。
- version-projections.json ↔ manifest.json 是**契约校验**关系（集合相等，fail-closed），非循环依赖：注册表声明投影，manifest 声明「必须存在哪些投影」，两者不一致即 BLOCKED——这是刻意的双向锁定，不是依赖环。
- 各模块职责一句话：canonical=规则本体；SKILL.md 段=全平台契约投影；persona 块=DSH 无条件携带投影；AGENTS 指针=项目级存在性信号；锚点检查=投影完整性守护；投影注册表=版本机械同步。

---

## 9. REQ-112 行为级验收信号（验收标准 5）

### 9.1 机器可查（grep / check）

| # | 信号 | 命令（示例） | 判定 |
|---|------|-------------|------|
| S1 | R1 进 persona | `grep -n "NEEDS_CHANGE" adapters/dsh/agent.cordis.yml.template` | 命中 ≥1（契约块内） |
| S2 | R2 进 persona + SKILL.md | `grep -n "task-priority-analysis" adapters/dsh/agent.cordis.yml.template skills/software-project-governance/SKILL.md` | 两文件均命中 |
| S3 | R3 进 persona + SKILL.md | `grep -n "选项必带依据" <两文件>` + `grep -n "依赖状态理由" <两文件>` | 均命中 |
| S4 | 版本漂移修复 + 锚定 | `python skills/software-project-governance/infra/verify_workflow.py check-projection-sync` | PASS（含 dsh-persona-version 投影；漂移态 FAIL） |
| S5 | 版本一致性 | `check-version-consistency` | PASS（不受本改动影响） |
| S6 | 锚点检查 | `check-governance`（含新 check-injection-contract） | PASS；人为删锚点 → FAIL |
| S7 | fixture 镜像同步 | `check-projection-sync`（fixture-skill byte_copy） | PASS（SKILL.md 改动已随 `release-projection --write` 重生成） |
| S8 | 测试契约 | `python -m unittest ... test_dsh_adapter.py -v` | 全绿；纯替换/token 契约测试零改动 |

执行包 `acceptance_contract.command` 字段 **MUST 同步升级为 S1-S4 组合——强制配套项（R0-S7，已列入 §6.8 批次 10）**：现占位为单条 grep 'T1'，注入文本落地后 persona 压缩块不含 'T1' 字面量（压缩投影按 §4 原则 1 不携带条款编号；SKILL.md 段含「T1-T4」仅部分命中），原命令必然失配。验收命令锚定语义关键词而非条款编号；T1-T4 可追溯性由 canonical 注记（§6.7）与参数级出处标注（round<3=触发器 T1 / round≥3=触发器 T2，R0-W2）承载。

### 9.2 会话可观察（行为级，实现后抽样验收）

| # | 场景 | 期望观察 |
|---|------|---------|
| B1 | 新 DSH 会话（不预读 behavior-protocol.md）注入 Reviewer 结论含 NEEDS_CHANGE（round &lt; 3） | Coordinator 立即输出 `>> 派发 {Reviewer} 执行复审（round+1）...` 并 spawn 同一 Reviewer，prompt 含前轮报告路径；无「是否需要复审」问句 |
| B2 | 任务标记已完成 | 同会话内出现 task-priority-analysis 的 pwsh 调用（transcript 可见命令行）+ 调用快照 evidence 行 + ask_user_question 呈现 1~3 候选且每个候选携带依赖理由 |
| B3 | unblocked=0 空推荐态（当前 live 常态） | 不出现机械枚举未完成事项的选项菜单；呈现结构化空原因（「无可推进任务，因为活跃任务阻塞于 …」）——注：空原因的机器侧产出依赖 REQ-110，FIX-253 时点至少要求注入面规则生效（不机械枚举） |
| B4 | 版本自述 | 会话 Governance 面板/persona 自述版本 == resolve_entry.py --json 的 active_version（无 v0.73.0 陈旧自述） |

B1-B4 为 REQ-112 验收信号 4（「不预读第四层文件的会话仍能执行复审与推荐」）的操作化。执行方式：实现合入后由 Coordinator 在真实 DSH 会话抽样并记录 evidence（AUDIT-143 §4 未验证项 2 的替代验证路径）。

---

## 10. 非功能覆盖（验收标准 1）

| 维度 | 约束/影响 | 设计措施 |
|------|----------|---------|
| **注入面 token 预算** | persona 契约块 ~0.9KB（块内 ≤13 行），persona text 总量 1.9KB→~2.8KB（远低于 agent-instructions 64KB 量级，system prompt 增幅 <5%）；SKILL.md +~1.2KB（302→~315 行） | 硬预算：persona 契约块 ≤1.5KB / SKILL.md 段 ≤2KB（超限 = 设计违规需重新压缩）；注入准入判据（仅「不依赖按需读取即须生效」的横切行为义务可入选，当前=3 条封顶）写入本设计；锚点检查不限制长度，长度由审查把关（BC-1 缓解） |
| **可维护性** | 双点压缩文本（persona/SKILL.md）+ canonical 全文 = 三处相关文本 | §4 原则 1/3：单一定义处（canonical）+ 两级标注投影 + 锚点检查守护存在性；canonical 注记建立双向追溯（§6.7）；版本串零人工维护点（投影 + 动态测试） |
| **check-projection-sync 影响** | ① 新增 2 条投影（persona 版本、AGENTS @bootstrap-version）→ 检查面 +2，漂移判定覆盖此前盲区；② SKILL.md 编辑触发 fixture byte_copy 重生成（MUST `release-projection --write`，漏做 = fixture drift FAIL——预期内的 fail-closed）；③ manifest 契约不同步 = BLOCKED | §6.4/§6.8 批次 5/8 强制同 commit；测试覆盖投影命中（§6.6.3） |
| **check-version-consistency 影响** | 零规则改动（VERSION_PATHS 不动）；其 PASS 前提（CHANGELOG/manifest/plugin.json 等 == SKILL frontmatter）不受本设计影响 | 单一权威源原则：版本判定归投影注册表，避免双判定面分歧（§7.4） |
| **跨平台投影一致性** | SKILL.md 契约段随既有入口链自动覆盖 Claude/Codex/Gemini/Chrys 等（各平台 bootstrap 加载同一 SKILL.md；plugin.json 版本投影已锚定）；persona 块为 DSH 增量；fixture 镜像 byte_copy 保持 e2e 一致 | 无需新建平台投影；非 DSH 平台的会话级覆盖依赖其 bootstrap 完整执行（RISK-D3，见 §11） |
| **性能** | 静态文本/check 变更，无运行时路径改动；launch.py 生成语义不变（纯替换测试零改动） | 无 |
| **安全** | 注入文本不含路径穿越/命令；投影 pattern 为字面量正则（projection.py `_safe_repo_path` 已有 symlink/绝对路径防护） | 无新增面 |

---

## 11. 风险

| ID | 风险 | 可能性/影响 | 缓解 |
|----|------|------------|------|
| RISK-D1 | **注入 ≠ 执行**：规则进入上下文后 LLM 合规仍是概率性的，用户观察到的行为缺口可能仅部分收窄（AUDIT-143 §2.1 已证「即使读到，执行靠自觉」） | 高 / 中 | 定位诚实：REQ-112 是放大器（提高行为基线概率 + 消除「不知道有此义务」类失效），不是充分条件；机器确定性由 REQ-107/108/113（review-record 强制路径、推荐快照 Check、pre-commit 前移）按 DEC-143 后续交付；B1-B4 行为抽样量化收窄幅度 |
| RISK-D2 | 注入面与 canonical 漂移：canonical 措辞演进后压缩投影陈旧，Coordinator 执行旧版义务 | 中 / 中 | 锚点选低频稳定关键词；check FAIL 强制同 commit；canonical 注记声明同步纪律（§6.7）；蓝军 BC-2 |
| RISK-D3 | 非 DSH 平台覆盖不均：契约段到达依赖各平台 bootstrap 链完整执行（audit §2.0.1 ②' 层曾证弱覆盖） | 中 / 低 | SKILL.md 是全部 adapter manifest 声明的 read_order 首位共享入口；行为级验收以 DSH 为主（REQ-112 验收信号 4 措辞即 DSH 会话）；其他平台抽样留待 REQ-108/109 验收 |
| RISK-D4 | 投影 pattern 脆弱：persona 版本句措辞被改写 → transformed_text count 命中 ≠1 → check BLOCKED/FAIL | 低 / 低 | fail-closed 即设计意图（改措辞必须同步 pattern——漂移即报，不会静默通过）；pattern 简单（单一字面量句式）降低误伤 |
| RISK-D5 | preset 安装态时滞：`git pull` 后未 `--sync`，DSH_HOME 旧 persona 继续服役（契约块不达新会话） | 中 / 中 | 既有升级路径已含 `--sync`（persona L62、AGENTS.md.template L50）；发版说明强调；@bootstrap-version 陈旧链对 AGENTS.md 侧兜底；残余风险记录（无法远程探测用户 DSH_HOME 状态——平台边界） |

---

## 12. 蓝军挑战（≥3，验收标准 4）

| ID | 挑战（"如果…会怎样"） | 缓解措施 |
|----|---------------------|---------|
| **BC-1 注入面膨胀** | 如果本次开了「关键规则进 persona」的先例，后续每个 AUDIT 都能论证自己的规则「关键」——persona/SKILL.md 逐版本膨胀，每条规则的注意力权重被稀释，最终回到「规则都在、行为都没有」的原点，只是换了一层 | ① 准入判据写入设计并要求后续变更引用：仅满足「不依赖任何按需读取即须生效的横切行为义务」（三簇测试：复审触发/完成推荐/交互依据——均为 AUDIT-143 实证的高频失效点）可入选；② 硬预算封顶（persona 块 ≤1.5KB、条目数 =3，超限须先淘汰再新增——零和）；③ 复盘检查点：每次 RETRO 审视注入面条目是否仍全部满足判据（退出机制）；④ 锚点检查只锁当前 3 条锚点，不为新条目自动扩面 |
| **BC-2 规则漂移（双源失同步）** | 如果 behavior-protocol.md 的 T1-T4/step 6 语义演进（如熔断轮次从 3 改 4），而注入面压缩文本仍写 round<3，Coordinator 会忠实执行一条已被废弃的规则——且因为注入面在上下文里、canonical 不在，旧版反而赢得执行竞争 | ① canonical 注记（§6.7）把「改关键词 MUST 同步注入面」写进规则本体；② 锚点关键词选取稳定词干（复审必达/task-priority-analysis/依赖理由），轮次等易变参数在注入文本中标注触发器级出处——已实现：round<3（触发器 T1）/ round≥3（触发器 T2），见 §6.1/§6.2 注入原文（R0-W2 修正：原稿引用"M7.4 C3"系错位——round<3 的 canonical 出处是 T1 而非 C3），语义变更时 check 不一定红——因此补 ③ 版本联动：注入块首行携带 FIX 编号（FIX-253），规则语义变更的执行包 MUST 检索注入面引用（变更影响分析 checklist Step 1-5 的既有关口）；④ Design Reviewer 审查本设计时专门核对注入文本与 canonical 当前文本逐条等效性；⑤ round=3 处 canonical C3/T2 既有矛盾已登记 §6.9 OBS-1——注入文本以 T1/T2 语义为准，canonical 对齐移交后续任务 |
| **BC-3 多平台投影不同步** | 如果 SKILL.md 契约段改了但 fixture 镜像没重生成（check-projection-sync FAIL 被 --no-verify 绕过），或某平台 plugin 包内的 SKILL 副本由旧管线打包——不同平台的 Coordinator 看到不同版本的契约，行为验收在 A 平台过、B 平台败 | ① fixture 重生成是同 commit 强制批次（§6.8 序 8），check-projection-sync 在 pre-commit/post-commit 门禁内（hook 已装）；② plugin 包版本与 SKILL frontmatter 由 check-version-consistency 全量锁定（打包旧副本 = 版本不一致 FAIL）；③ 部署面（非仓库面）的分发陈旧由 @bootstrap-version 陈旧链 + `--sync` 升级路径兜底（RISK-D5）；④ e2e fixture 的 CLAUDE.md @bootstrap-version 当前为人工维护——本设计不扩面，记录为观察项移交 REQ-113 |
| **BC-4 注入后的行为自满** | 如果团队把「规则已注入」当作「行为已修复」记账（证据=grep 命中），B1-B4 行为抽样被跳过——注入层修复重复 0.73.0 的错误：工具/规则存在 ≠ 行为发生（AUDIT-143 一句话结论的同构复发） | ① 本设计明确区分两级验收（§9.1 机器可查=注入完成定义；§9.2 行为可观察=REQ-112 效果定义），FIX-253 闭环要求 B1/B2 至少各一次真实会话抽样证据，B3/B4 可随 0.75.0 dogfood 补；② 执行包 done_definition 写入该区分（防「过程证据替代产品价值」——执行包 non_goals 模板的既有关口）；③ DEC-143 排布本身即承认放大器≠修复，REQ-107~110 未交付前不宣称五簇缺陷修复 |
| **BC-5 锚点检查的假阳性/阴性** | 如果锚点词过于通用（如"NEEDS_CHANGE"在模板其他段落已存在），删掉契约块后检查仍绿（假阴性）；反之锚点过严（含易变措辞），正常编辑触发误报（假阳性）造成检查疲劳 | ① 锚点组设计为「通用词+专有词」复合（每文件 ≥4 个锚点须全部命中，其中「复审必达/完成必推荐/选项必带依据」为 FIX-253 新造专有短语——删除契约块必然失配，假阴性封堵）；② 专有短语同时是注入文本的段首标记，措辞演进时锚点与文本同 commit 更新（§7.3）；③ 检查输出按「文件×缺失锚点」粒度报告，误报可快速定位；④ 测试（§6.6）与 check 双轨锚点，互为交叉验证 |

---

## 13. Proposed `.governance/decision-log.md` entry（ADR——由 Coordinator 写回，本任务不落盘）

> 编号建议 DEC-144（decision-log 现存最新为 DEC-143，2026-08-21 grep 确认 DEC-144+ 零占用；Coordinator 写回时复核序号）。按 decision-log 表字段组织（M3 字段定义）：

| 字段 | 内容 |
|------|------|
| **编号** | DEC-144 |
| **日期** | 2026-08-21（Coordinator 写回日） |
| **主题** | FIX-253/REQ-112 关键行为规则注入面设计决策——双点最小注入（DSH persona + SKILL.md 契约段）+ 版本投影锚定 + 锚点检查守护 |
| **背景** | AUDIT-143 确认注入层主根因：T1-T4 复审触发器（behavior-protocol.md M7.4 step 4.6 L526-532）、step 6 完成推荐义务（L552-556）、依赖排序交互规则（interaction-boundary.md L187/L217）仅存于第四层按需文件，DSH 注入链（persona agent.cordis.yml.template L30-62 / 入口 SKILL.md）不携带（AUDIT-143 §2.0.1 逐字比对），行为全靠 Coordinator 自觉；附带 persona L33 版本硬编码 v0.73.0 漂移（0.74.0 漏网），且该文件对 check-version-consistency（version.py VERSION_PATHS）与 check-projection-sync（version-projections.json 13 投影）均为盲区（Architect 核查新增事实）——漂移为结构性盲区而非偶发。DEC-143 已定前置放大器优先 + 交互基线（自动推荐+用户确认） |
| **决策内容** | 采用方案 A（4 候选取舍见设计文档 §5）：① R1/R2/R3 压缩契约块注入 persona（~0.9KB）+ SKILL.md 新增「关键行为契约」段（全平台 canonical 投影定义处，~1.2KB）+ AGENTS.md.template 单行指针（维持 thin-pointer）；② L33 版本串纳入 version-projections.json transformed_text 投影（dsh-persona-version，与 hooks @version 同构）+ manifest release_projection_contract 同步，AGENTS.md.template @bootstrap-version（dsh-agents-bootstrap-version）同批锚定；③ 新增 check-injection-contract 锚点存在性检查（persona/SKILL/AGENTS 三文件 × 专有短语锚点组）进 check-governance；④ test_dsh_adapter 版本断言去字面量化（动态读 frontmatter）。**可逆性：完全可逆**——纯文本/配置/检查/测试变更，无数据迁移、无运行时接口变更，git revert 单 commit 即完整回滚（投影条目回滚后恢复盲区但不产生不一致） |
| **备选方案** | (B) SKILL.md 单点注入 + persona 指针；(C) launch.py 生成时动态装配（新 token + canonical 标记段提取）；(D) 不注入、纯 Check 事后/前移拦截 |
| **选择原因（含排除理由）** | B 排除：persona 指针仍依赖「skill 被加载」prose 前提，与 REQ-112「无需依赖主动读取」目标自相矛盾，且 REQ-112 验收信号 1 首选形态即 persona 携带一句话契约。C 排除：破坏「launch 生成=纯 token 替换」确定性契约（test_launch_link_generation_is_pure_substitution 直接断言），标记段提取对 prose 脆弱、模板可审查性下降，preset 时滞更重。D 排除：检测时序断链未解（拦截时用户已感受缺失）、Check 判定源可手写绕过不对称未解，系 REQ-107/108/113 路线而非替代。A 中选：双点冗余与现有注入链结构一致（persona 骨架规则既有模式）、launch.py 零语义变更、投影机制复用 hooks 先例零新机制、锚点检查与 check-projection-sync 同族 |
| **影响范围** | 产品代码 7 文件：adapters/dsh/agent.cordis.yml.template（persona 契约块 + L33）、skills/software-project-governance/SKILL.md（契约段 + fixture 重生成）、adapters/dsh/AGENTS.md.template（指针行 + @bootstrap-version 锚定）、core/version-projections.json + core/manifest.json（2 投影 + 契约）、infra/verify_workflow.py（新检查）、infra/tests/test_dsh_adapter.py（断言动态化）、references/behavior-protocol.md（canonical 注记）；承载版本 0.75.0；不涉及 REQ-107~111/113/114 实现（DEC-143 排布不变） |
| **决策人** | 用户确认（经 Coordinator AskUserQuestion 呈现本设计结论后）+ Coordinator（写回） |
| **关联任务** | FIX-253, REQ-112, AUDIT-143, DEC-143, FIX-250（版本同步链漏网）, FIX-223/224/237.5（被投影规则的原始强化链） |
| **后续动作** | ① Design Reviewer 独立审查本设计（重点：注入文本与 canonical 等效性、BC-2 漂移防护充分性）；② 用户确认方案 A 后 Developer（Governance Developer）按 §6.8 批次实现；③ 实现后 S1-S8 机器验收 + B1/B2 真实会话行为抽样入 evidence；④ 执行包 FIX-253 的 acceptance_contract/done_definition 按 §9 更新（消灭 TO_BE_DEFINED 占位）；⑤ REQ-110 设计任务并行立项（同版本放大器）；⑥ 0.75.0 打包评估（REL）；⑦ OBS-1（canonical C3/T2 round=3 熔断边界矛盾，设计文档 §6.9）移交 REQ-107 对齐 |

---

## 14. 硬门槛自检（Architect 角色）

| 门槛项 | 阈值 | 本设计 | 状态 |
|--------|------|--------|------|
| 候选方案数 | ≥2 | 4（A/B/C/D，各含取舍与排除理由 §5） | ✅ |
| ADR 关键字段完整 | =100% | 标题/日期/背景/决策/备选/排除理由/影响范围/后续动作 + 可逆性标注（§13，8 字段全） | ✅ |
| 蓝军挑战条数 | ≥3（独立 ID + 缓解） | 5（BC-1~BC-5，§12） | ✅ |
| 模块无循环依赖 | =0 | 单向分层图 + 契约锁定非环论证（§8） | ✅ |
| 不修改产品代码 | — | 仅写本设计文档（docs/ 设计时资产） | ✅ |
| 不写 .governance/ | — | ADR 仅 proposed（§13，Coordinator 写回） | ✅ |
| 不与用户交互/不建子 agent/不做最终决策 | — | 结构化结果返回 Coordinator（report） | ✅ |

## 15. 边界声明

- 本文档为设计阶段产物：除本文档外未修改任何文件；`skills/**`、`adapters/**`、`.governance/**` 均未触碰。
- 所有现状事实附文件+行号依据（§3.1-§3.3，2026-08-21 读取态）；§6 的修改规范是**待实现设计**，非已生效变更——行号在实现时点可能因并行改动漂移，Developer 实现时按锚点文本定位而非行号。
- §9.2 行为级信号（B1-B4）在实现合入前不可验证——列为验收计划而非现状声明。
- 方案取舍（A/B/C/D）为 Architect 论证建议，最终决策经 Design Reviewer 独立审查 + 用户确认（DEC-144 决策人字段）。
- 版本「0.75.0」为 DEC-143 候选承载版本的沿用地标；若版本规划变更，本文档锚定语义不变（投影机制与版本号解耦）。
