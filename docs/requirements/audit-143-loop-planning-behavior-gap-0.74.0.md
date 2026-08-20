# AUDIT-143 — Loop engineering 效果与任务规划系统性缺陷复诊（0.74.0）

- **日期**: 2026-08-17
- **执行**: Analyst Agent（只读定位分析 + 需求转化；AUDIT-143，plan-tracker L216 已登记 ⏳ 审计中）
- **对象版本**: skills/software-project-governance SKILL.md frontmatter `version: 0.74.0`（plan-tracker L11 确认安装态 0.74.0 已激活）
- **前序审计**: AUDIT-140（0.71.0，loop 接线缺口）、AUDIT-141（0.71.0，任务依赖三重断裂）、AUDIT-142（0.72.0，三链复诊 → REQ-104/105/106 + FIX-236/237/238，0.73.0 发布）
- **性质**: 修复后复诊——三轮声称完成的修复之后，用户（本项目维护者、工作流产品唯一真实用户）于 2026-08-17 反馈同类问题仍存在

---

## 1. 执行摘要

用户反馈三大簇 5 个问题（1a/1b/2a/2b/2c）。本轮复诊的核心结论：**0.73.0 三链重构（FIX-236/237/238）修的全部是工具层与静态检查层——CLI 存在、Check 可验证、测试全绿；但"工具被真实会话调用""行为规则到达 Coordinator 工作上下文""推荐数据非空"三个环节全部断裂。工具在仓库里，行为没有发生。**

| # | 用户感受到的 | 根因（分层） | 置信度 |
|---|---|---|---|
| 1a | Developer 按检视意见修改后不会复审（小循环失效） | **接线层+投影层+行为层**：复审触发器 T1 是 behavior-protocol.md L528 的 prose，DSH 会话的注入链（persona → SKILL.md）不携带它；review-record CLI 从未被调用（机器标记 0 匹配）；复审链全靠 Coordinator 自觉，无会话内拦截 | 高 |
| 1b | 单点任务处理完直接结束，不回归上层循环推进计划（大循环失效） | **接线层+投影层+数据层+模型层**：M7.4 step 6（L552-556）不注入；loop_exit→next-candidates 桥从未运行（loop-event-log.jsonl / loop-exit-candidates.json 均不存在）；live 数据 unblocked=0 → recommended_next=[]；loop 引擎绑定 flow-unit 模型而宿主运行 classic gate 模型，无桥 | 高 |
| 2a | 规划/推进不先分析依赖和优先级，机械找一个未完成事项交互 | **投影层+数据层**：interaction-boundary L187/L217 已是"依赖分析推荐"，但按需读取不注入；task-priority-analysis 仅在 change-triage（任务入账）内被调用，任务完成后的推荐调用为 0；unblocked=0 时工具输出空推荐，agent 退化为机械枚举 | 高 |
| 2b | 关键节点完成后无法向用户推荐合理推进事项 | **同 2a + 交互设计张力**：maximum-autonomy 模式设计为"少打断"，step 6c 允许"自主执行不交互"——用户想要的"推进感"（推荐+交互）与协议的"自主连续执行"存在需求错配；且推荐内容规则（top-N + 依赖理由）不在注入面 | 高 |
| 2c | 新给事项时不结合项目状态系统分析优先级和依赖 | **覆盖面+呈现层**：change-triage 是唯一被真实调用的分析工具（12 条机器记录 ✅），但仅覆盖"创建产品代码任务"路径；用户口头/轻量新事项不触发；分析结论进 JSON 机器记录，不转化为用户交互中可见的推荐理由 | 高 |

**一句话总结**：Check 32（change-triage）之所以有效，是因为它的判定源（机器 triage 记录）无法被手写替代；Check 21/29/30（review/loop/推荐链）之所以无效，是因为它们的判定源（evidence-log 行 + review 文件）可以被 Coordinator 手写合规地绕过，而真正的机器路径（review-record CLI）没有任何 Check/hook/入口强制其被使用。

---

## 2. Part 1 定位分析

### 2.0 事实核查基线：三层注入链与工具/检查层现状

#### 2.0.1 行为规则的注入链（H3 核查）

规则要影响 Coordinator 行为，必须进入其工作上下文。当前 DSH 平台的注入链：

| 层 | 文件 | 实际内容（关键行） | 是否含 loop/推荐行为规则 |
|---|---|---|---|
| ① persona（会话 system 级） | `adapters/dsh/agent.cordis.yml.template` L30-62 | bootstrap 3 步（skill 加载/resolve_entry/fail-closed）+ SELF-CHECK 4 条（读 plan-tracker/阶段/问句检测/交互边界）+ 模式确认 + Agent Team 映射 + hooks + 升级 | **否**。无 M7.4、无 T1-T4、无 task-priority-analysis、无 review-record、无 loop_exit。且 L33 版本号仍写 `v0.73.0`（未随 0.74.0 同步——FIX-250 投影面同步遗漏） |
| ② 项目级 AGENTS.md（DSH 注入） | `adapters/dsh/AGENTS.md.template`（launch.py `--bootstrap-project` 写入目标）全文 53 行 | thin pointer：第一动作 + SELF-CHECK 4 条 + 模式 + Agent Team + hooks + 升级 | **否**（同上） |
| ②' 仓库根 AGENTS.md / CLAUDE.md（Codex/Claude 平台） | 仓库根 `AGENTS.md`（grep 实证） | 完整 bootstrap Step 0-4 + SELF-CHECK 5 条 | **否**。grep `task-priority-analysis|M7.4|review-record|T1|loop_exit|复审` 仅命中 1 处（L35 "M7.4 step 5" 交付物审查引用） |
| ③ 入口 SKILL（skill 工具加载） | `skills/software-project-governance/SKILL.md`（302 行） | 身份/铁律/路由表/边界。L219："Coordinator 执行行为约束，详见 `references/behavior-protocol.md`"——**引用式**；L251 将 behavior-protocol.md 列入"参考知识（按需读取）"表 | **否**（仅引用） |
| ④ 行为协议本体 | `references/behavior-protocol.md`（778 行） | M5.1b 触发器（L294-318）、M7.4 step 4.5b spawn 守卫（L477-492）、step 4.6 状态机+T1-T4（L493-544）、step 6 依赖分析+推荐（L552-556） | **是**——但本层不被任何确定性机制加载 |

**断链判定**：M2 预加载清单（behavior-protocol.md L77-82）只强制 `main-workflow/SKILL.md` + `plan-tracker.md`；behavior-protocol.md 与 interaction-boundary.md 均为"按需读取"（SKILL.md L251/L254）。DSH 会话中 Coordinator 的默认上下文 = ①+③（若加载 skill）——**两层都不含 M7.4 step 4.6/step 6/交互推荐规则**。要看到这些规则需第三次主动读取（④），无任何强制触发点。

**佐证（本审计会话自身）**：派发本任务的 DSH 主会话 system prompt 即来自 ①（与 agent.cordis.yml.template L30-62 逐字一致），其中不含任何 loop/推荐规则。

#### 2.0.2 工具层现状（H1 核查）

三个 CLI 工具全部存在且功能完备（0.73.0 交付，EVD-875/EVD-880）：

| 工具 | 文件 | 能力 | 真实会话调用证据 |
|---|---|---|---|
| review-record | `infra/review_record.py`（379 行）+ verify_workflow.py L19191 薄入口（L20819 注册） | 机器写入 review-{id}-R{n}.md + evidence 行；NEEDS_CHANGE 输出复审必达 next_round/prev_report；Wiring A 调 process_gate_result；loop_exit 时刷新候选快照 | **❌ 零调用**。grep `.governance/**/*.md` 找机器标记 `machine-written by review-record`（review_record.py L204 首行固定输出）→ **0 匹配**。现存 160 个 `review-*.md` 全部手写（命名 `review-FIX-196-CODE-R0.md` 带 ROLE token，非 CLI 生成的 `review-{task}-R{n}.md` 纯格式） |
| loop_exit_bridge / next-candidates | `infra/loop_exit_bridge.py`（197 行）+ verify_workflow.py L19219 薄入口 | 消费 loop_exit 事件 → compute_unblocked_tasks → top-N 候选+三类依赖理由 → 快照 `.governance/loop-exit-candidates.json` | **❌ 零运行**。glob `.governance/loop*` → 无结果：`loop-event-log.jsonl`（事件源，loop_gate_processor L914-940 写入）与 `loop-exit-candidates.json`（输出快照）**均不存在**——生产路径从未执行 |
| change-triage | `infra/change_triage.py`（621 行）+ verify_workflow.py L19249 薄入口 | 四步 triage（依赖快照/优先级/冲突/版本）+ 机器记录 `.governance/change-triage/{id}.json` + TRIAGE- 证据行 | **✅ 真实调用 12 次**：glob 实证 FIX-242~252 + REL-067 共 12 条 JSON 记录（TRIAGE_NORMALIZATION_DATE=2026-08-03 之后） |

**事件链推论**：loop-event-log.jsonl 的唯一生产写方是 loop_gate_processor（process_gate_result 内部，L914-940）。它不存在 = Wiring A（review-record → process_gate_result）与 Wiring B（auto_judge_gate → process_gate_result）在真实会话中**均从未触发**。`.governance/` 下也无 `flow-unit-runtime.json`（glob `.governance/*.json*` 仅 val-009/execution-packets/agent-locks）——loop 引擎运行时在本仓库自身从未初始化。

#### 2.0.3 Check 层现状（H2 核查）

| Check | 位置 | 判定源 | 拦截时机 |
|---|---|---|---|
| Check 21（review debt/spawn gap） | verify_workflow.py L13675 | check_review_debt()——evidence-log 静态扫描 | **事后**。check-governance 由 post-commit hook（`infra/hooks/post-commit` L190）在 commit 后运行，或会话末尾手动运行。会话进行中不拦截 |
| Check 29（M5 运行时触发器） | verify_workflow.py L14137-14152 | check_m5_runtime_triggers()（review_domain.py L1334，签名 `text=None, contains_askuserquestion=False`）——live 模式扫描 session-snapshot / evidence-log **落盘文本** | **事后且间接**。会话实时输出（用户实际看到的回复）不落盘，Check 29 看不到；只能扫事后摘要。代码注释自认："Best-effort scan … Does not over-claim in CI"（L14135-14136） |
| Check 30（复审终态状态机） | verify_workflow.py L14157；review_domain.py L1818-1937 | live 扫描 evidence-log 的 REVIEW-{id}[-R{n}] 行 + review-*.md 文件，验证 V1-V4（轮次连续/终态合法/熔断/追溯） | **事后**。且**不验证写入路径**：无 machine-written 断言（grep review_domain.py 无 "machine-written"）——手写合规行 PASS。ADR-017 设计审查 R1 发现 N1 已指出："review-record 唯一机器化路径缺强制（建议机器标记+Check 断言 WARN 起步）"（evidence-log L44）——**未实施** |
| Check 30b（调用点 AST） | verify_workflow.py L14174-14185 | check_loop_wiring_call_sites()——**源代码静态 AST**：process_gate_result 生产调用点 ≥2 | 证明代码存在调用点（PASS/2），**不证明运行时被调用**。实际运行 0 次（见 2.0.2） |
| Check 32（change-triage 记录拦截） | verify_workflow.py L14217-14232；checks/triage_domain.py | 产品代码任务有 evidence 但无 `.governance/change-triage/{id}.json` → FAIL | **事后但有效**——判定源（机器 JSON 记录，含 created_at + 完整分析快照）**无法被手写 evidence 替代或事后伪造**；跳过会在 check-governance 留下无法补救的 FAIL |

**关键不对称**：Check 32 的判定物是不可伪造的机器记录；Check 21/29/30 的判定物是 Coordinator 可直接手写的治理文本（M1.2 快速通道，behavior-protocol.md L46-57，合法化了 evidence-log 直写）。因此前者被遵守（12 条记录）、后者被系统性绕过（手写 REVIEW 行 ×24+，机器记录 ×0）。

#### 2.0.4 数据层现状（H4 核查）

live plan-tracker 的 task-priority-analysis 实际输出（最新机器快照：`.governance/change-triage/FIX-252.json`，2026-08-17，内嵌 report_json）：

- `total: 131`（L411）——FIX-251 修复 headerless 表可见性后（EVD-FIX-251：live total 124→131）
- `unblocked: []`（L611）
- `recommended_next: []`（L612）
- blocked 11 项（FIX-155/156/REL-047/199/202/207/208/209/212/213/200，L22-33）；in-flight P0=13（L44）

即：**当前数据态下，即使 Coordinator 忠实运行 task-priority-analysis / next-candidates，输出也是空推荐**（无 unblocked 任务可推荐）。工具无"空推荐降级策略"（不输出 blocked 链分析或"为什么没有可推进事项"）——空输出交给 agent 自由发挥，退化为用户所见的"机械找一个未完成事项"。

对照：2026-08-02 时点 unblocked=AUDIT-142/FIX-231/FIX-233 3 项（EVD-873）；数据债清理（FIX-237.1）后随任务推进，活跃 unblocked 归零是常态而非异常——推荐机制对"全阻塞"态没有设计。

#### 2.0.5 模型层断层（H5，静态代码推演）

review_record.py 的 wiring 解析（L77-137）：

- 角色可从 task id / 报告文件名检测（CODE→G6 / DESIGN→G5 / RELEASE→G9，L43-47）
- 但映射成功后**必须再有 unit_id**，否则 `resolved=False`，reason="role maps to gate but no flow-unit id is available (pass --unit or register a unit mapping)"（L120-130）→ wiring SKIPPED with WARN
- classic G1-G11 gate 模式的宿主（本仓库即是：plan-tracker 维护 `## Gate 状态跟踪`，无 flow-unit 注册表）没有 flow-unit 概念，Coordinator 无从传 `--unit`

推论：**即使 Coordinator 调用 review-record CLI，在 classic 宿主上 loop 接线仍会跳过**（wired=false，WARN 记录在 review 文件的 wiring 行）。loop 引擎（FEAT-004~009 交付的 flow-unit/loop_state 体系）与 classic gate 双模型之间没有桥。此为静态代码分析结论（未运行验证，见 §4）。

---

### 2.1 问题 1a：Developer 修改检视意见后不会复审（小循环失效）

**现象重述**（用户原话）："没有感受到 loop 的效果，developer 修改检视意见之后，不会复审，说明小循环失效"。

**事实核查**：

- 规则存在：M7.4 step 4.6 状态机 C1（behavior-protocol.md L515）"NEEDS_CHANGE 后，Coordinator MUST spawn 同一 Reviewer 复审"；T1 触发器（L528）"审查结论含 NEEDS_CHANGE 且 round<3 → MUST 立即 spawn 复审……复审是强制的，不是可选的"；T1 自称"FIX-224 确定性触发器（M5.1b 风格——不依赖 Coordinator 自觉）"（L526）。
- 但"确定性"仅是 prose 断言：T1 的执行主体仍是 Coordinator 读到结论后的自觉行为。声称的脚本层防线（L532）："Check 21（review_spawn_gap）和 Check 30 会检测 evidence-log 中 NEEDS_CHANGE 后无对应 R{n+1} 的记录"——是**事后扫描**（§2.0.3）。
- 机器路径存在但未被用：review-record CLI 对 NEEDS_CHANGE 自动产出 `next_round: REVIEW-{id}-R{n+1}` + `prev_report` 机器字段（review_record.py L218-223）——复审义务变成可机读数据。grep 实证：`.governance/` 无任何机器写入的 review 文件（§2.0.2）。
- 会话行为证据（evidence-log 近期行，FIX-244~252）：REVIEW 行的提交人均为 "Code Reviewer sub-agent" / "Developer + Code Reviewer sub-agents（Coordinator 记录）"（如 L1265/L1269/L1288/L1292）——**Coordinator 直接写 evidence-log 表行**（M1.2 快速通道合法路径），不经 CLI。EVD-891（L1271）甚至记录了一次修复："REVIEW-FIX-244-R1 未写入（FIX-244 仅 R0 一轮，如实）"——手写路径连轮次字段都可能漏写。
- 复审本身并非从未发生：FIX-245（R0→R1）、FIX-249（R0→R1→R2）显示任务内"审查→返工→复审"链曾经人工闭合（L1269-1270/L1297-1298）。但这依赖 Coordinator 记得——无机器保障，无跨会话续链保障（CLI 的 next_round 字段从未生成）。

**根因链**：

```
T1 复审触发器写在 behavior-protocol.md L528（第四层，按需读取）
  → DSH 注入链（persona ① / SKILL.md ③）不携带（§2.0.1）——投影层断链
  → 即使读到，执行靠自觉；review-record CLI 无任何强制使用机制——接线层断链
    （Check 30 不验证机器来源；M1.2 快速通道合法化了手写替代，§2.0.3）
  → 即使调用 CLI，classic 宿主无 unit_id → wiring 跳过（§2.0.5）——模型层断链
  → Check 21/30 只在 commit 后/会话末报告，用户在会话中已感受到缺失——检测时序断链
  ⇒ 用户观察：改完没人复审
```

**分层结论**：投影层（主）+ 接线层（主）+ 模型层（次）+ 检测时序（次）。置信度：**高**（机器文件缺失 + persona 逐字比对 + evidence-log 提交人字段三重实证）。

---

### 2.2 问题 1b：单点任务处理完直接结束，不回归上层循环（大循环失效）

**现象重述**（用户原话）："单点任务处理完之后就直接结束了，不会像之前那样和用户交互推进计划或者继续往后推进，像是小循环结束直接不会回归到上层循环了"。

**事实核查**：

- 规则存在：M7.4 step 6（behavior-protocol.md L552-556）：a. 依赖分析 MUST 运行 task-priority-analysis 并将调用快照记录到 evidence-log（FIX-237.5 证据化，"不存在'如果存在'豁免……不得跳过分析"）；b. 推荐下一步 1~3 候选；c. AskUserQuestion 呈现（仅关键决策强制）；d. **不得直接结束**（"除非 plan-tracker 中无未完成任务，或用户明确选择'暂停'"）。
- 执行证据：**evidence-log 中不存在任何一条"任务完成后运行 task-priority-analysis/next-candidates 并记录调用快照"的证据**。grep `task-priority-analysis|next-candidates|loop_exit|loop-exit-candidates` 全部 10 处命中位于：FIX-236/237 实现描述（EVD-875/880/873/872）、FIX-240 CI 修复（EVD-877）、FIX-251 可见性修复验证（EVD-FIX-251）——**全部是工具自身开发/测试/入账场景，零条是 step 6a 推荐场景**。
- 会话推进实证（`.governance/session-snapshot.md`，2026-08-17）："下次会话优先级"为**手写有序列表**（L22-29：遗留观察项/CI 观察/planned_next 误判/归档 FAIL/SSH 观察/风险看护）——非 task-priority-analysis 或 next-candidates 输出，无依赖理由，无 top-N 结构。
- 机器链完全静止：loop_exit 事件从未产生（无 loop-event-log.jsonl）→ loop_exit_bridge.refresh_candidates 从未运行（无 loop-exit-candidates.json）→ next-candidates CLI 无数据可读。任务完成 → 推荐的数据流水线在生产中从未流过一滴水。
- 数据层：即使运行，输出为空（unblocked=0，§2.0.4）。

**根因链**：

```
step 6 规则在第四层按需文件（同 1a 的投影层断链）
  → 任务完成后无任何机制提醒/强制运行依赖分析（接线层）
  → loop_exit 事件链从未启动（无 review-record 调用 + classic 宿主 wiring 跳过，模型层）
  → 即使运行，recommended_next=[] 空输出（数据层，§2.0.4）
  → 无 Check 检测"完成证据缺推荐快照"（检测层：不存在对应 check）
  ⇒ Coordinator 默认行为 = 完成任务 → 写证据 → 会话自然终止（snapshot 手写列表）
  ⇒ 用户观察：小循环结束不回归上层
```

**分层结论**：投影层 + 接线层 + 数据层 + 模型层全链断裂。置信度：**高**（四类文件级证据交叉）。

---

### 2.3 问题 2a：规划与推进不先分析依赖/优先级，机械找一个未完成事项交互

**现象重述**（用户原话）："任务的规划以后后续的推进不会先分析任务的依赖关系和优先级，只会机械的找一个未完成事项和用户交互"。

**事实核查**：

- 规则存在且已经过两轮强化：interaction-boundary.md L187（非关键决策-任务排序行）："运行 `task-priority-analysis`，按依赖排序候选（FIX-237.5——替代机械取最高优先级，消除与违规表 :217 的矛盾）"；L217（反打断违规表）："按 M7.4 step 6（FIX-223 增强版）执行依赖分析→推荐最合理下一步→AskUserQuestion 呈现候选（含推荐理由），而非机械取'最高优先级'"。
- 两处规则均在按需读取的二级文件（SKILL.md L254 将 interaction-boundary.md 列入"按需读取"）——注入面不含（§2.0.1）。
- DSH persona 的 SELF-CHECK 第 4 条确实保证了"到达交互边界 → MUST ask_user_question"——这解释了用户观察到的另一半：**会问，但问得机械**。交互发生（骨架规则在注入面），交互内容的质量规则（依赖排序+理由）不在注入面。
- 工具调用实证：task-priority-analysis 的全部真实调用发生在 change-triage 内部（12 次入账分析）与 FIX-251 验证——"任务完成/推进时先分析"场景零调用（§2.2）。
- 数据层：unblocked=0 → 即使分析，候选为空（§2.0.4）。

**根因链**：投影层（内容质量规则不在注入面）→ 数据层（空推荐）→ 检测层（无"交互选项必须可追溯依赖分析输出"的 check）。会问（骨架在）+ 问得机械（内容规则不在 + 数据空）。置信度：**高**。

---

### 2.4 问题 2b：关键节点完成后无法向用户推荐合理推进事项

**现象重述**（用户原话）："整个项目到各个层次的 loop 的缺乏任务规划能力，在 loop 中完成某个关键节点事项之后没法向用户推荐合理的推进事项"。

**事实核查**：

- 与 1b/2a 同源（step 6 / L217 未生效 + 数据空），另有**需求层张力**：
  - 当前模式 maximum-autonomy（session-snapshot L42）。该模式的合法行为是"自主连续执行、不打断"（interaction-boundary.md L112-127："唯一打断条件"三 类）。
  - M7.4 step 6c："当且仅当推荐项涉及关键决策（M5.3）时强制 AskUserQuestion；否则**可自主执行推荐项**并在完成后再次推荐"——maximum-autonomy 下"不问、自主推进"是协议允许的。
  - 用户期望的是"像之前那样和用户交互推进计划"——即任务完成节点上出现**携带推荐的交互**（信息性推荐，非确认）。
  - 两者的错配：协议把"推荐交互"设计成了可选/确认式，用户要的是推进感的载体。叠加 step 6 整体未生效（§2.2），用户既看不到推荐也感受不到推进。
- "推荐合理推进事项"的机器能力（loop_exit_bridge 三类依赖理由 + top-N）已建好但从未服务过用户（§2.0.2）。

**根因链**：同 1b 全链断裂 + 交互设计张力（maximum-autonomy 的少打断 vs 用户要的推荐交互）。置信度：**高**（断裂链）；张力部分为**分析推断**（用户"之前"的历史体验无档案证据，见 §4 未验证项 3）。

---

### 2.5 问题 2c：用户新给事项时不结合项目状态系统分析优先级和依赖

**现象重述**（用户原话）："用户给到一个新的事项/任务时候不会结合当前项目状态系统性的分析事项的优先级和依赖关系"。

**事实核查**：

- **正面事实**：change-triage 四步分析（依赖快照/优先级判定含 in-flight 计数/冲突检查/版本适配）是三个工具中唯一被真实、持续调用的——12 条机器记录（FIX-242~252 + REL-067），每条含完整 task-priority-analysis 快照（report_json + report_text，change_triage.py docstring L26-31）。最近记录 FIX-252.json 展示了完整分析：新任务依赖 FIX-251、blocked 11 项、in-flight P0=13、版本链全量。
- **缺口一（覆盖面）**：change-triage 的触发条件是"创建产品代码任务"（change_triage.py L41-44 快速通道边界："only .governance/ governance record changes may skip triage; any new task touching product code MUST run the standard path"）。**用户口头提出的新事项**——尚未成为 plan-tracker 产品代码任务、或属于咨询/轻量事项——没有对应的分析触发点。用户感受的"新事项不分析"发生在分析门禁覆盖不到的场景。
- **缺口二（呈现层）**：分析结论落进 `.governance/change-triage/*.json`（机器记录）与 evidence 行，**不进入用户可见的交互内容**。没有任何规则/check 要求"向用户呈现新事项处理选项时携带 triage 分析结论"（优先级依据、依赖关系、与 13 个 in-flight P0 的冲突、版本链位置）。用户看到的是任务被创建/被推进，看不到"系统性分析"的发生——分析做了等于没做（对用户感知而言）。
- **缺口三（数据层）**：依赖列结构化已交付（plan-tracker L74/L234 优先级表头含 `依赖` 列；FIX-225~229 链），FIX-251 又修复了 headerless 子节可见性——数据基础在。但 unblocked=0 的现状使"新事项与当前状态的交集分析"输出贫瘠（新事项的依赖判定可以做出，但"下一步该做什么"的推荐为空）。

**根因链**：门禁覆盖面（仅产品代码任务创建）+ 呈现层（分析结论不进交互）+ 数据层（空推荐）。**注意：这是五问题中唯一有实质机器进展的一簇**——门禁位置与不可伪造判定源使 change-triage 成活（对照 §2.0.3 不对称分析）。置信度：**高**。

---

## 3. Part 2 需求转化（REQ 草案）

编号依据：全仓 grep `REQ-10[7-9]|REQ-11[0-9]` 零占用（2026-08-17）；plan-tracker 需求跟踪矩阵现存最高 REQ-106（L200-202）。以下为需求草案（非实现方案）——每条给出用户可验证结果 + 可观察验收信号 + 根因关联 + 候选承载分类（技术选型留给后续设计任务）。

### REQ-107 — 审查结论机器持久化与复审义务可续链（根因：1a / H1+H3）

- **需求陈述**：任何 Reviewer 审查结论（尤其 NEEDS_CHANGE）必须经机器路径持久化，产生可机读的复审义务（next_round/prev_report）；复审触发不依赖 Coordinator 记忆或自觉。用户在任意会话中不再观察到"Developer 按意见修改后无人复审"。
- **验收信号**：
  1. `.governance/` 中存在带机器标记的 `review-{task}-R{n}.md` 文件与对应 evidence 行（review-record CLI 契约）；
  2. NEEDS_CHANGE 记录携带 `next_round`/`prev_report` 字段；跨会话可从证据直接推导待复审项；
  3. 存在 Check/hook 断言：REVIEW 证据行无机器来源标记 → 至少 WARN（渐进 FAIL）——落实 ADR-017 R1 发现 N1（evidence-log L44）；
  4. 抽查最近 N 个已完成产品代码任务，复审链（R0→Rn）要么完整闭合、要么有 BLOCKED/escalation 记录，无"NEEDS_CHANGE 后无 R{n+1}"的悬空态在事后 check 中才被发现。
- **候选承载**：Check 增强（机器标记断言）+ 行为协议修订（M1.2 快速通道对 REVIEW 行的豁免收窄）+ 平台投影修正（入口注入面携带复审必达最小规则）+ 产品代码（若选择 hook/入口强制路线）。

### REQ-108 — 任务完成必产出依赖排序的下一步推荐（根因：1b / H1+H3+H4）

- **需求陈述**：任何任务标记"已完成"的同一会话内，必须产出并记录依赖排序的下一步推荐（候选+理由）；会话不得在无推荐的情况下因任务完成而终止（plan-tracker 无未完成任务或用户选暂停除外）。
- **验收信号**：
  1. 每条任务完成证据关联一份 task-priority-analysis 或 next-candidates 调用快照（命令输出 JSON 落 evidence-log——M7.4 step 6a 的 FIX-237.5 证据化要求的可验证形态）；
  2. 任务完成后的下一次用户交互（AskUserQuestion 或 ℹ️ 通知）携带 top-N 候选及依赖理由（可追溯到快照）；
  3. 新增 Check：已完成活跃任务的证据缺推荐快照 → FAIL（与 Check 18c 执行包检查同构的完成侧检查）；
  4. session-snapshot 的"下次会话优先级"节可验证为由推荐快照派生（引用快照 ID），而非自由手写。
- **候选承载**：Check 增强 + 行为协议修订（已有 prose，需检测化）+ 平台投影修正。

### REQ-109 — 交互选项必须可追溯依赖分析输出（根因：2a / H3+H4）

- **需求陈述**：凡向用户呈现"接下来做什么"类选项的交互，选项必须来自依赖分析输出（排序候选+每项依赖理由），不得机械枚举未完成事项。
- **验收信号**：
  1. 交互呈现中每个候选携带依赖状态理由（satisfied/pending/unknown 三类，loop_exit_bridge 既有输出契约）或空推荐的结构化原因（见 REQ-110）；
  2. 候选可追溯到一次分析快照（记录于 evidence-log 或交互日志）；
  3. Check 30/29 扩展或新 Check：治理记录中出现"下一步/继续推进"类交互记录（snapshot/证据）时校验快照引用存在。
- **候选承载**：行为协议修订（interaction-boundary L187/L217 从 prose 升级为可检测契约）+ 平台投影修正（该规则进入注入面）+ Check 增强。

### REQ-110 — 空推荐的降级策略（根因：2a/2b / H4）

- **需求陈述**：当依赖图无 unblocked 任务（当前 live 常态：total=131/unblocked=0）时，推荐输出不得为空列表——必须给出"解除阻塞路径"推荐（最值得解除的 blocked 任务 + 其阻塞因素）或显式结构化空原因（"无可推进任务，因为 X 个活跃任务全部阻塞于 Y"），使用户理解项目状态而非感到系统失能。
- **验收信号**：
  1. 在当前 live 数据（unblocked=0）上运行 next-candidates/task-priority-analysis，输出非空推荐（含 blocked 链分析）或结构化空原因——二者必居其一，禁止裸空列表；
  2. 用户交互呈现空推荐态时包含"为什么现在没有可推进事项 + 解除阻塞的最短路径"；
  3. 单元测试锁定：全阻塞 fixture 下输出含 blocked-chain 推荐或空原因。
- **候选承载**：产品代码（task_priority/loop_exit_bridge 推荐逻辑增强）+ 行为协议（空态呈现契约）。

### REQ-111 — 新事项分析先于创建且结论进入用户可见呈现（根因：2c / 覆盖面+呈现层）

- **需求陈述**：用户提出任何新事项（不限于产品代码任务；含口头/轻量事项）后、该事项进入 plan-tracker 或下次用户交互前，必须发生结合当前项目状态的系统分析（依赖/优先级/冲突/版本），且分析结论以用户可见形式进入呈现（选项理由/通知），不只是机器记录。
- **验收信号**：
  1. 新事项处理路径上存在分析产物（change-triage 记录或等价分析快照），覆盖非产品代码事项场景（当前 Check 32 只覆盖产品代码任务）；
  2. 向用户呈现新事项处置选项时，每个选项携带分析结论摘要（优先级依据、依赖关系、与 in-flight 任务的冲突、版本链位置）；
  3. 抽查最近 N 个新入事项：既有机器分析记录、又有用户可见呈现证据（交互记录/通知含分析要素）。
- **候选承载**：工具扩展（change-triage 覆盖面或新增轻量分析入口）+ 行为协议修订（呈现契约）+ Check 增强。

### REQ-112 — 关键行为规则进入确定性注入面（根因：H3，横切 1a/1b/2a/2b）

- **需求陈述**：Coordinator 的关键行为契约（复审必达、完成必推荐、交互必带依赖理由）必须进入平台投影的确定性注入面（persona/bootstrap/skill 摘要），使 DSH/任意平台会话无需依赖"主动读第四层文件"即受约束；或有等价的会话内机器拦截。
- **验收信号**：
  1. adapters/dsh/agent.cordis.yml.template 与 AGENTS.md.template 含最小行为契约集（上述三条的一句话形式）——或等价的注入机制文档化并可 Check；
  2. 新增投影一致性检查：注入面模板的关键契约关键词（复审/推荐/依赖理由）缺失 → FAIL（与 check-projection-sync 同族）；
  3. 投影字段版本一致性：agent.cordis.yml.template L33 `v0.73.0` 漂移修复并纳入版本同步检查（FIX-250 已建 @bootstrap-version 同步链，此文件漏网）；
  4. 在 DSH 新会话中直接询问/观察行为：不预读 behavior-protocol.md 的会话仍能执行复审与推荐（行为级验收，可抽样）。
- **候选承载**：平台投影修正 + manifest/Check 增强（投影字段与契约集一致性）+ 行为协议（最小契约集定义）。

### REQ-113 — 违规检测时序前移（根因：H2，横切 1a/1b）

- **需求陈述**：关键协议违规（review spawn gap/复审悬空/完成无推荐）的检测必须在 commit 之前拦截（pre-commit），而非 commit 之后报告；推荐缺失类违规需在会话内可见（下一次 check 或交互前产生 WARN）。
- **验收信号**：
  1. pre-commit hook 运行 Check 21/30 子集（当前 check-governance 全量在 post-commit L190 运行）——违规 commit 被拒（exit 非零）而非事后打印；
  2. 会话中任务完成而未产出推荐快照时，下一次 verify_workflow 运行输出该 WARN（新 Check 生效）；
  3. 会话实时问句违规（M5.1b T1/T2）的检测范围有明确文档：当前 Check 29 仅覆盖落盘文本（session-snapshot/evidence-log），会话实时输出不落盘不可检——此限制需文档化或由宿主层提供输出钩子（超出本仓库范围的边界写明）。
- **候选承载**：hooks 增强（pre-commit 扩展）+ Check 增强 + 文档边界声明。

### REQ-114 — loop 接线在 classic gate 宿主可用（根因：H5，横切 1a/1b）

- **需求陈述**：classic G1-G11 gate 模式的宿主（含本仓库自身）中，review-record/gate 判定也能驱动 loop 事件与复审/推荐链，不再因"无 flow-unit id"结构性跳过接线。
- **验收信号**：
  1. classic 宿主调用 review-record 后，`.governance/loop-event-log.jsonl` 产生事件（或等价桥接记录）——Wiring A 不再输出 "no flow-unit id available" WARN 跳过（review_record.py L120-130 的路径）；
  2. ADR 决策记录 classic↔flow-unit 映射策略（gate_id 即 unit 锚点或显式默认 unit）；
  3. 在本仓库 dogfood 一个完整小循环：NEEDS_CHANGE → 修复 → 复审 → 事件链落盘。
- **候选承载**：产品代码（review_record/loop_gate_processor 映射桥）+ ADR（架构决策）。
- **注意**：本需求基于静态代码推演（§2.0.5），实施前需先运行验证（§4 未验证项 1）。

**REQ 优先级建议**（供 Coordinator/用户决策，非本 Analyst 决策）：REQ-112（注入面）与 REQ-110（空推荐）是其余各条的前置放大器——规则不进上下文、数据为空，则其余修复仍会退化为"工具存在但行为不发生"。REQ-107/108 为用户感受最痛的两条直连修复。

---

## 4. 未验证项与验证计划

| # | 未验证项 | 现状依据 | 验证计划 | 阻碍 |
|---|---|---|---|---|
| 1 | process_gate_result 在 classic 宿主的实际行为（review-record 调用后 wiring 是否如静态推演跳过） | review_record.py L120-130 静态代码推演；无运行实证 | 在测试 fixture 或 dry-run 中调用 `verify_workflow.py review-record --task-id TEST-001 --result NEEDS_CHANGE --report-path <x>`，观察 wiring.reason 与 loop-event-log.jsonl 是否产生 | 本审计角色约束不执行产品代码；需 Developer/QA 或 Coordinator 在受控环境运行 |
| 2 | 主会话 Coordinator 是否读过 behavior-protocol.md（注入链断链的行为学确认） | 从行为证据反推（step 6 未执行、无推荐交互、snapshot 手写列表）；无法观测主会话上下文 | 无直接验证手段（上下文不可观测）；以 REQ-112 的行为级验收替代（新会话不预读仍执行） | 平台不提供会话上下文审计 |
| 3 | 用户所说"之前那样和用户交互推进计划"的历史版本行为基线 | 无档案证据指明哪个版本/何种交互 | git 考古（历史 session-snapshot/交互记录）或请用户澄清期望的具体交互形态；建议作为 REQ-109/112 验收设计的输入 | 用户交互超出 Analyst 权限，返回 Coordinator |
| 4 | Check 32 拦截 vs skill 可见性：change-triage 被遵守的归因（是 post-commit FAIL 威慑、任务创建门禁 prose、还是 change-triage skill 在目录可见） | 12 条记录证明行为发生；归因无法从档案区分 | 若需要精确归因：对照实验（移除其一观察行为）——成本高，仅当 REQ 设计需要时执行 | 实验成本；建议仅做用户访谈确认 |
| 5 | 0.74.0 会话中 M7.4 step 1-5（证据/check/审计/交付物审查/commit）的实际执行率 | 部分证据（evidence-log 行规整、post-commit hook 存在且可运行）；step 6 零证据已实证 | 抽样最近 N 个任务的证据链逐项对照 step 1-5 清单 | 本轮时间盒内未展开；AUDIT 后续可扩展 |
| 6 | hooks 实际安装与运行状态（.git/hooks/ 是否存在、post-commit 是否真的跑了 check-governance） | infra/hooks/ 源文件存在（post-commit L190 含 check-governance 调用）；.git/hooks 安装态未检查（bootstrap 要求检测，本审计未验） | `ls .git/hooks/` + 最近 commit 的 hook 输出核对 | 简单补查即可，未做是因为与五问题根因弱相关 |

---

## 5. 附录：检查过的文件清单（路径 + 关键行）

**产品代码（行为规则与工具）**

| 文件 | 关键行/内容 | 用途 |
|---|---|---|
| `skills/software-project-governance/SKILL.md` | L2 version 0.74.0；L219 引用 behavior-protocol；L247-258 按需读取表；L281-297 DSH 平台说明 | 入口层注入面核查 |
| `skills/software-project-governance/references/behavior-protocol.md` | L46-57 M1.2 快速通道；L77-82 M2 预加载；L294-318 M5.1b；L454-560 M7.4 全文（step 4.5b L477、4.6+T1-T4 L493-544、step 6 L552-556） | 规则存在性核查 |
| `skills/software-project-governance/references/interaction-boundary.md` | L187 依赖排序（FIX-237.5）；L213-221 反打断违规表（L217 推荐要求）；L112-127 maximum-autonomy 边界 | 规则存在性核查 |
| `skills/software-project-governance/infra/review_record.py` | L43-47 REVIEW_GATE_MAPPING；L120-130 unit_id 缺失跳过；L200-251 机器文件/evidence 行格式（L204 机器标记）；L218-223 NEEDS_CHANGE next_round | Wiring A 核查 |
| `skills/software-project-governance/infra/loop_exit_bridge.py` | L31 CANDIDATES_FILENAME；L153-187 refresh_candidates；L175 事件日志读取 | Wiring 桥核查 |
| `skills/software-project-governance/infra/change_triage.py` | L1-66 行为契约（四步+fail-closed+快速通道边界）；L26-31 机器记录 | 唯一成活工具核查 |
| `skills/software-project-governance/infra/loop_gate_processor.py` | L890-945 _append_gate_events（事件唯一生产写方）；L953-962 loop_fuse_check | 事件链核查 |
| `skills/software-project-governance/infra/verify_workflow.py` | L13675-13697 Check 21；L14134-14152 Check 29；L14154-14172 Check 30；L14174-14185 Check 30b；L14212-14232 Check 32；L19191/19219/19249 三个 CLI 薄入口；L20678/20701/20715 注册 | Check 层核查 |
| `skills/software-project-governance/infra/checks/review_domain.py` | L870 check_review_spawn_gap；L1334 check_m5_runtime_triggers（签名）；L1818-1937 check_review_closure（判定源=evidence 行+文件，无机器来源断言） | Check 判定源核查 |
| `skills/software-project-governance/infra/hooks/post-commit` | L182-190 check-governance 运行位置（commit 后） | 检测时序核查 |
| `adapters/dsh/agent.cordis.yml.template` | L30-62 persona text（注入面内容）；L33 v0.73.0 版本漂移 | H3 核心证据 |
| `adapters/dsh/AGENTS.md.template` | 全文 53 行（thin pointer） | H3 证据 |
| `adapters/dsh/preset.yml`、`adapters/dsh/launch.py` | preset 无规则内容；launch L44-50 模板替换机制 | 投影机制核查 |
| 仓库根 `AGENTS.md` / `CLAUDE.md` | grep 命中仅 L35 一处 M7.4 step 5 引用 | 平台入口注入面核查 |

**治理运行时数据（行为证据）**

| 路径 | 关键证据 |
|---|---|
| `.governance/loop-event-log.jsonl` | **不存在**（glob 无结果）——loop 事件链零运行 |
| `.governance/loop-exit-candidates.json` | **不存在**——推荐桥零运行 |
| `.governance/flow-unit-runtime.json` | **不存在**（glob `.governance/*.json*`）——loop 引擎运行时未初始化 |
| `.governance/review-*.md`（160 个） | grep 机器标记 `machine-written by review-record` **0 匹配**——全部手写 |
| `.governance/change-triage/*.json`（12 个） | FIX-242~252 + REL-067——change-triage 真实调用 ✅ |
| `.governance/change-triage/FIX-252.json` | L21/L411/L611-612：unblocked=[]、total=131、recommended_next=[]（live 空推荐实证）；L44 in-flight P0=13 |
| `.governance/evidence-log.md` | L30/L32（FIX-236 交付描述）；L44（ADR-017 R1 N1 建议未实施）；L1264-1307（FIX-244~251 REVIEW 行均为 sub-agent/Coordinator 手写）；grep task-priority-analysis 10 处全为工具开发场景 |
| `.governance/session-snapshot.md` | L22-29 手写"下次会话优先级"；L42 maximum-autonomy |
| `.governance/plan-tracker.md` | L11 版本 0.74.0；L74/L234 优先级表含依赖列；L199-206（REQ-104/105/106 与 FIX-236/237/238 声称交付）；L216 AUDIT-143 登记；L200-202 现存最高 REQ 编号=REQ-106 |
| `docs/requirements/`（39 文件） | 前序审计报告（audit-140/141/142 等）；REQ-107+ 编号零占用（全仓 grep） |

---

## 边界声明

- 本报告为只读分析产物；未修改任何产品代码与 `.governance/` 治理记录（plan-tracker/evidence 状态由 Coordinator 更新）。
- 所有结论附文件路径+行号或命令输出依据；无法从事实验证的内容已标"未验证"并列入 §4。
- REQ 草案的"候选承载"仅为分类（产品代码/行为协议/平台投影/Check），不含技术选型决策。
- 与用户的交互（如"之前行为基线"澄清）超出 Analyst 权限，已列入验证计划返回 Coordinator。
