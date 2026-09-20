# Design Review · REL-082 · 0.86.0 架构演进规划设计半面 · R0

> Reviewer: Design Reviewer（独立）· Round: **R0**（首轮）· 日期: 2026-09-19
> 审查依据: agents/design-reviewer.md + skills/design-review/SKILL.md + skills/tech-review/SKILL.md（Bar Raiser 模式）
> 审查对象（REL-082 锁面内四文档）: ①docs/planning/0.86.0-architecture-evolution.md（主审）②docs/planning/version-plan-0.86.0.md ③docs/planning/0.86.0-boundary-audit.md（输入）④docs/planning/0.86.0-arch-consult-round1.md（输入）
> 独立性声明: 本审查只读核验全部引用（14 项独立核验，见 §4），未修改审查对象、产品代码与 `.governance/`；本文件为唯一写入面。

## 总结论

# **NEEDS_CHANGE**

- **P0 = 0 · P1 = 3 · P2 = 8 · P3 = 5**
- 判定理由: 存在 3 项 P1（M0 契约冻结无承载票 / 量化验收口径无基线 provenance / R1 回退树内矛盾）——均为规划文档结构性缺陷，修复后复审可过；**非架构级致命**：目标架构方向（六层确认+六模式封顶+写入器先行）经独立核验自洽且实证扎实（V1~V3/V5~V9 通过），不需要重新设计，故不判 BLOCKED。
- DESIGN 五维: 架构合理性 ✅ · 决策依据可追溯 ⚠️（P1-2/P2-1/P2-4）· 风险覆盖 ⚠️（P1-3/P2-8）· 一致性 ⚠️（P2-2/P2-3/P3-1）· 完备性 ⚠️（P1-1/P2-7）
- 硬门槛速览: 候选方案 ≥2 ✅ · 蓝军 ≥3 条独立 ID ✅（BT-1~7，但见 P2-8 两处遗漏）· 循环依赖 ✅（既有 R3 环检测+白名单）· Bar Raiser ✅（外部 gpt-6-astra 独立源参与，资格满足：非项目组、领域匹配、无进度压力——DEC-221 义务①背书）· ADR 字段完整性 ⚠️（evolution §7 决策留痕指向错误 ID，P2-3）

---

## 1. 五维审查明细

### 1.1 架构合理性 — ✅（无 P1/P2）

- 六层目标架构为**现状确认而非发明**：registry.py L3 原文「The composition-root prototype of the 0.80.0 six-layer architecture」独立核验命中（V7）；R1/R2 棘轮数学单调收缩为既有事实。
- 写入器先行修订（本地 R2 放弃「存储先行」）与实证链一致：boundary-audit §3 共性根因「校验器先行于写入器」直接支撑「最缺的是写入路径不是存储形态」——裁决有据。
- M0~M3 封顶合规性逐项检查：task-row-update/locks 族=状态机域+既有 Check 26 管道复用；evidence/decision-append=D3/D4 机录先例扩面；closure-chain=模式④（ADR-014 混合）推广+loop_event_log 零第二实现；类型化 --refs=判断外壳域「证据引用解析」（round1 §1.1 已归类）——**均落在六模式或既有六层域内，未发现隐藏新运行时机制**。零新依赖声明与stdlib-only 一致。
- 边缘（P3-5）: FEAT-047 BaselineMetadata provenance schema 是新横向机制，未对照六模式封顶清单归类（六模式无此项）——建议显式收编为「L0 契约/schema 冻结实例」或封顶清单模式⑦，否则未来 ratchet 化封顶执法时自家纪律票成为第一个例外。
- 「接管范围零手写」可执法性: 见 P2-7（WARN 姿态与「=0」验收的量测口径未定义）——执法面缺口，非设计方向缺陷。

### 1.2 决策依据可追溯 — ⚠️ P1-2 / P2-1 / P2-4

多数裁决锚定扎实（V1/V2/V5/V6/V8/V9 全部精确命中），但存在三处实证链断裂：

- **P1-2**: version-plan §3 验收基线「0.85.0 会话实测（≥5 段）」全治理域零命中（V12）。
- **P2-1**: evolution §0「6 次事故」vs 上游 DEC-220/EVD-1101/boundary-audit 一致的「5 次」，第 6 次无引用。
- **P2-4**: boundary-audit 方法节自誓「每条结论附复现命令」，其「grep 53 处」实测不可复现（rg 29 行/Select-String 36 行）——结论方向成立但计数失真。

### 1.3 风险覆盖 — ⚠️ P1-3 / P2-8

- BT-1~7 全量登记且每条有缓解 ✅（超角色硬门槛 ≥3）。
- **R1 回退树内矛盾（P1-3）**:「不砍范围不降 DoD」与三选一中的「降级采纳」直接冲突——降级采纳若指带缺陷入版则必降 DoD；若指面退出则与「撤销该面」重叠且违反「不砍范围」。回退树是发布期故障时刻的决策装置，语义不闭合=故障时无法依赖。R2/R3 闭合性 ✅（R2 出口明确：链顺延 0.87+原子 CLI 独立价值保全；R3 升级架构裁决终点明确）。
- 混沌测试失败路径: R2 覆盖「不过且短期不可修」；「短期可修→修复复测」为隐含路径，可接受。
- **遗漏风险面（P2-8）**: ①WARN 姿态下 LLM 绕过 CLI 手写的搭便车行为（0.86 恰是习惯养成窗口）②混沌测试 kill 语义的 Windows/CI 可重复性未指定（本仓有 Windows+GBK 历史病灶；kill 进程语义 taskkill≠POSIX）——建议补 BT-8/BT-9 或记录豁免理由。

### 1.4 一致性 — ⚠️ P2-2 / P2-3 / P3-1 / P3-3

- evolution 与 version-plan 主体一致 ✅: M0~M3 范围、四类写入器、混沌测试发布门、存储 JSON 化后置 0.87+、「不依赖 0.85.0 批 2」声明均对齐。
- **P2-2**: evolution §7「FEAT-042/044/045 转为 0.86.0 M1/M3 工作票根」vs version-plan §5「FEAT-044/045 → 0.87.0 候选」直接矛盾；且 0.86.0 批次表实际无任何票承载 044/045——evolution 表述与真实批次安排不符。
- **P2-3**: evolution §7「采纳后入 decision-log（DEC-221 承载）」——实测 DEC-221 已入账（decision-log L162）且内容为「全链预授权」，非设计采纳记录。照抄将一 ID 两义。
- **P3-1**: B-6 snapshot-render 版本承载不一致（evolution 归 M5=0.87+；version-plan 列 0.86.0 in-scope 搭车）。
- **P3-3**: FEAT-046/047/048 新票号未入 plan-tracker 候选池（V11）——采纳后入账+FEAT-042→042R 改写+FEAT-043 并入 047 销账动作未写明，双轨候选风险。
- 与 0.85.0 在途（FEAT-041）冲突排查: **文件面零交集 ✅**（V10——FEAT-041 七锁：SKILL.md/governance-init.md/两测试/三模板 vs 批 1 三个新 infra 文件）；概念面注意点：FEAT-041 的 SKILL.md progressive disclosure 瘦身与 FEAT-042R 的 behavior-protocol 转移表引用相邻（协议面两轨道并行修改），M0 状态语义以 behavior-protocol L516-531 为源时须确认 0.85.0 轨道后续批不触碰该文件面；FEAT-041 的 85% 活跃门应纳入 FEAT-047 存量登记首批对象（version-plan 未指明存量登记范围）。

### 1.5 完备性 — ⚠️ P1-1 / P1-2 / P2-7 / P3-2

- **P1-1**: M0 契约冻结（「0.86.0 首批」）在批次表无承载票、无文件面声明、无验收负责人；而批 1 三票并行依赖 M0 输出（operation_id/错误码/schema 版本为共用契约），批 2.0「M0 验收复跑」反向确认其前置地位。M0 不可派发=批 1 并行无法合规启动。
- DoD 九条可操作性: 整体 ✅（守护测试清单逐项具体且有 L871 负载先例，V6）——但见 P3-2（第 6 条「源已提交/投影待修复」两态语义面向 0.87+ 投影架构，对 0.86 单文件 markdown 追加器基本 N/A，建议标注条款适用阶段，防为不存在两态造测试）。
- 量化指标基线来源: P1-2（无 provenance）+ P2-7（「手写记录数=0」的量测方法/豁免口径未定义——推测靠 Check 30c 机器来源标记统计，两文档均未写明；R1 降级采纳若发生，与「=0」验收的交互亦未定义）。

---

## 2. Findings 清单（P1 → P3）

### P1（阻塞——须修复后复审）

| # | Finding | 位置 | 证据 | 建议修复 |
|---|---------|------|------|---------|
| P1-1 | M0 契约冻结无承载票/文件面，批 1 并行前置未排程 | version-plan §1/§2; evolution §2.3 M0 | 批 1 三票（FEAT-042R/046/047）交付物均不含 contracts.py/契约 fixture；批 2.0 依赖 M0 验收复跑 | 增设 M0 票根（含文件面：contracts.py 扩展+契约测试+固定 fixture），置于批 1 前或批 1 并行前置槽；同步声明 M0受阻即触发 R3 类升级 |
| P1-2 | 量化验收口径无基线 provenance，且口径数字三方不一致（≥5 段/4 段/5-8 步） | version-plan §3 第 2 条 | grep `.governance/`「LLM 往返\|往返数\|≥5 段」零命中；EVD-1101（evidence-log L2351）为「每票 4 段串行」；boundary-audit B-4 为「5-8 步」 | 以 FEAT-047 同款 BaselineMetadata（measured_at/测量器/分子分母口径/阈值依据）为该门补基线登记；基线未实测前该条降为「量测义务」而非验收门（FEAT-043 纪律自洽） |
| P1-3 | R1 三选一语义不闭合：「不降 DoD」×「降级采纳」矛盾，且与「撤销该面」重叠 | version-plan §4 R1 | R1 原文并列「不砍范围不降 DoD」与「修复顺延/降级采纳/撤销该面」 | 重定义三选项边界：建议「修复顺延（面保留在本版）/降级采纳（面保留但验收门对该面显式豁免并列 user-visible 差异——即承认局部降 DoD，由用户显式批准）/撤销（面移出本版入 0.87）」——删除「不降 DoD」绝对化表述或将其限定为「DoD 清单本身九条不裁剪」 |

### P2（重要——复审时逐条核销）

| # | Finding | 位置 | 证据 | 建议修复 |
|---|---------|------|------|---------|
| P2-1 | 手工事故计数 6 vs 上游一致的 5，第 6 次无锚 | evolution §0 | DEC-220（decision-log L161）「5 次事故（3 行锚定+1 锁 schema+1 入账截断）」；boundary-audit 头部同口径 5 次 | 对齐 5 或补第 6 次实证引用（若计入 FEAT-041 外扩锁活体须显式说明计数口径） |
| P2-2 | FEAT-044/045 去向两文档矛盾（0.86.0 M1/M3 票根 vs 0.87.0 候选） | evolution §7; version-plan §5 | 批 1/2 票根（042R/046/047/048）实际无 044/045 承载位 | 统一为 version-plan §5 口径（044/045→0.87.0），修订 evolution §7 |
| P2-3 | 「采纳后入 decision-log（DEC-221 承载）」指向已占用 ID | evolution §7 | decision-log L162: DEC-221=全链预授权（含打磨期义务①②③），非采纳记录 | 采纳决策改用新 DEC ID，或修订 §7 为「采纳经用户 M-0 裁定入账（DEC-22x）；DEC-221 预授权语义依其生效条件衔接」 |
| P2-4 | boundary-audit「grep 53 处」不可复现（实测 rg 29 行/Select-String 36 行）；方向性结论成立 | boundary-audit §0 方法节 | 本审查双工具复测（V4）；抽查 L20407/L20410 确为 init 写入 ✓；「零运行时写入 CLI」结论经 29 处样本核验成立 | 统一工具口径（建议 rg 行级）重记计数；方法节补「计数以 X 工具 Y 口径为准」 |
| P2-5 | 第二轮双源顾问记录无原文保全件，evolution §2.2 分歧采纳逻辑不可回查原文 | evolution 头部/§2; version-plan §6 | docs/planning/ 仅 6 文件（V14）；round1 有「原文全文保全零改写」先例；DEC-221 义务③「每次讨论与修订留痕（顾问轮次记录入档）」 | 补 round2 双源保全件（0.86.0-arch-consult-round2.md 形态），或至少在 evolution §2 标注「转述自会话记录」并说明原文不可复查的原因 |
| P2-6 | FEAT-046 文件面「governance_store.py（新或并入既有）」未冻结 | version-plan §2 批 1 | 「并入既有」若指 change_triage.py/verify_workflow.py，则批 1「文件面不相交」约束失效且触碰 R2 棘轮 | 派发前冻结为「新建」；复用 acquire 管道指 import 复用而非同文件并入 |
| P2-7 | 「LLM 手写记录数=0」验收无量测定义与豁免口径 | version-plan §3; evolution §1 | write-guard 0.86 为 WARN 姿态（2.3）；机检来源未写明（Check 30c 机器来源标记族？行族统计？）；emergency-append 隔离区行是否计入未定义 | 写明量测命令/检查项与豁免口径；定义 R1 降级采纳发生时该验收的换算规则 |
| P2-8 | 蓝军遗漏两面：绕行搭便车 + 混沌测试跨平台 kill 语义 | evolution §5; version-plan 2.2 | BT-1~7 无对应项；本仓 Windows+GBK 病灶（FIX-278/GBK 例外先例）；混沌测试进 M-2 发布门但执行环境未指定 | 补 BT-8（WARN 期绕行行为——缓解：接管面手写行为进 Review 检查项+30c 渐进 FAIL 提速）/BT-9（kill 语义平台差异——缓解：指定混沌测试执行环境与 kill 方法并纳入 fixture）或记录豁免理由 |

### P3（备注——采纳时顺手处理，不阻塞）

| # | Finding | 位置 | 建议修复 |
|---|---------|------|---------|
| P3-1 | B-6 版本承载两文档不一致（M5=0.87+ vs 0.86.0 搭车） | evolution §2.3 M5; version-plan §1 | version-plan 标注「B-6 搭车须满足 evolution M5 验收点不缩水」 |
| P3-2 | DoD 第 6 条两态语义与 0.86 阶段错位（markdown 仍为规范源） | evolution §4.6 | 标注条款适用阶段（0.87+ 投影架构），0.86 交付面按单文件一致性态执行 |
| P3-3 | FEAT-046/047/048 未入 plan-tracker 候选池 | version-plan §2; V11 | 采纳入账时同步：新票入池、FEAT-042→042R 改写、FEAT-043 并入 047 销账、044/045 按统一口径标注去向 |
| P3-4 | 双轨协议引用 emergency-append 隔离区（0.86 行为），其 schema 正式化在 0.87（§6③） | evolution §2.1/§6③ | 明示 0.86 降级终态=「BLOCKED 响亮披露」（无隔离区写入）；隔离区随 0.87 正式化 |
| P3-5 | BaselineMetadata provenance schema 未对照六模式封顶归类 | evolution §2.3 贯穿纪律; round1 §6 | 显式收编（L0 schema 冻结实例或模式⑦），保持封顶执法无例外 |

---

## 3. 蓝军挑战记录（本 Reviewer 独立挑战——Bar Raiser 框架切换后）

设计隐含三核心假设: ①「LLM 手滑是主要事故源」②「CLI 写入器自身可靠性可用守护测试兜住」③「接管范围边界可静态枚举」。框架切换（这个设计最可能在哪里失败）后三条独立挑战:

| 攻击向量 | 影响评估 | 当前缓解 | 残余风险 | 建议增强 |
|---------|---------|---------|---------|---------|
| BT-8' 批 1 并行开发期，Dev 为省回合在 WARN 姿态面直接手写（习惯未成型窗口） | 中——「零手写」验收在发布日不可信，量测被污染 | write-guard WARN+Check 30c 渐进 | 中 | 接管面手写行为列入 Reviewer 检查项；30c 该族 FAIL 提速日程表写进 version-plan |
| BT-9' 混沌测试 kill 语义在 Windows（本仓宿主）与 CI 载体行为不一致，发布门复演结果不可比 | 高——发布门形同虚设或误判 | 无（未指定环境） | 高 | M-2 前指定混沌测试执行环境+kill 方法+判定口径，入 fixture |
| BT-10' M0 冻结的契约（operation_id/错误码）与批 1 三票实际实现互相反馈修订，冻结被渐进冲蚀 | 中——契约测试 fixture 与实现漂移 | M0 固定 fixture+契约测试 | 中 | 冻结后契约变更走显式版本协议（M0 已含「schema 版本与旧 CLI 拒写行为」——补「契约变更须 bump fixture 并复跑批 1 契约测试」一句） |

（设计方回应义务: BT-8/9/10 的逐条回应随返工修订记录——对应 tech-review strict profile「设计方的逐条回应记录」。）

## 4. 独立核验表（14 项）

| # | 核验项 | 声称来源 | 实测结果 | 判定 |
|---|--------|---------|---------|------|
| V1 | DEC-220 公理原文 @ decision-log L161 | boundary-audit §7/evolution §0 | L161 命中，内容一致（含 5 次事故明记） | ✅ |
| V2 | EVD-1101 @ evidence-log L2351 | boundary-audit §7 | L2351 命中，摩擦四项与引用一致 | ✅ |
| V3 | verify_workflow.py 行数 24,769/24,770 | boundary-audit D2 / round1 §0 | 实测 24,769 行 1.06MB——boundary-audit 精确 ✓；round1 差 1 行 | ✅ |
| V4 | decision-log/session_snapshot「53 处」引用 | boundary-audit §0 | rg 29 行 / Select-String 36 行，两口径均≠53；L20407/L20410 确为 init 写入 ✓；「零运行时写入 CLI」方向成立 | ❌ 计数不可复现（P2-4） |
| V5 | loop_paro_engine L524 per-file lock 串行化 CAS 临界区 | evolution §2.1 | L524 原文「Per-file locks guarding the CAS critical section (re-read → check → replace)」精确命中 | ✅ |
| V6 | test_loop_paro_engine L871 threading 负载先例 | evolution §4.7 | L871「Threading test — CAS correctness (no lost updates) [LOAD-BEARING]」精确命中 | ✅ |
| V7 | registry.py 六层组合根自述 | round1 §0 | L3「The composition-root prototype of the 0.80.0 six-layer architecture」精确命中 | ✅ |
| V8 | acquire_dispatch_locks L769/L962 | boundary-audit §7 | L769/L962 双双精确命中 | ✅ |
| V9 | agent-locks.json L63-80 FEAT-041 三条外扩锁活体 | boundary-audit B-3② | L63-80 命中，ttl_reason 自述「外扩追加…cross-check WARN 披露」与引用一致 | ✅ |
| V10 | 批 1 文件面 vs FEAT-041 在途锁面冲突 | version-plan §2 vs agent-locks.json | FEAT-041 七锁（commands/governance-init.md、SKILL.md、两 test、三模板）vs 批 1 三个新 infra 文件=零交集；概念面注意点见 §1.4 | ✅（附条件） |
| V11 | FEAT-042~048 候选在册 | evolution §7 | FEAT-042/043/044/045 @ plan-tracker L351-354 ✅；FEAT-046/047/048 不在册 | 部分（P3-3） |
| V12 | 验收基线「0.85.0 会话实测 ≥5 段」 | version-plan §3 | `.governance/` 全域「LLM 往返/往返数/≥5 段」零命中；EVD-1101 为「4 段」 | ❌ 无源（P1-2） |
| V13 | DEC-221 承载设计采纳 | evolution §7 | decision-log L162: DEC-221=「0.86.0 设计演进全链预授权」（含打磨期义务①②③），非采纳记录 | ❌ ID 被占用（P2-3） |
| V14 | 第二轮双源顾问记录落盘 | DEC-221 义务③ | docs/planning/ 全目录仅 6 文件，无 round2 保全件；round1 有全文保全先例 | ❌（P2-5） |

## 5. 硬门槛裁决（tech-review 严格档）

| 门槛项 | 阈值 | 裁决 |
|--------|------|------|
| 候选方案数 | ≥2 | ✅ 五裁决均含「反方案不取」（强 prompt/daemon/mega-command/SQLite/markdown 真相/event-sourcing） |
| ADR 关键字段完整 | 100% | ⚠️ DEC-220/221 字段完整 ✅；evolution §7 留痕 ID 错误（P2-3） |
| 蓝军挑战 | ≥3 独立 ID | ✅ BT-1~7；完备性缺口见 P2-8/BT-8~10 |
| 循环依赖 | 0 | ✅ 六层单向+R3 白名单/Tarjan 既有执法（round1 §0 实证） |
| Bar Raiser | 已执行 | ✅ 外部 gpt-6-astra 独立源（资格满足）；但第二轮原文未保全（P2-5） |
| 量化验收可裁决 | 可操作 | ❌ P1-2/P2-7——两项验收口径不可客观裁决 |

## 6. 设计优点确认（返工时 MUST 保留，防止改坏）

1. 「写入器先行、存储分离后置」修订有完整实证链（boundary-audit B-1~7 共性根因）——方向正确。
2. Q-4 外部精化（评估结果与继续策略分离，NOT_EVALUABLE 独立态）确实封堵「过期=放行」与「过期=用户失败」两个漏洞——采纳逻辑在转述层自洽（P2-5 解决后可回查原文）。
3. effect-based 幂等（查世界不信日志）+ 三事实分离是跨 git/push 边界恢复的正确教科书形态，且有 L524/L871 双实证先例背书。
4. 存量 ×415 只检读取安全不强改写（防 W-6）与「新行硬校验+存量 WARN」边界与 DEC-168/FIX-349⑤ 先例一致。
5. DoD 九条整体可操作，守护测试负控清单具体（V6 先例在场）。

## 7. 复审指引（Coordinator → Architect 返工 → 本 Reviewer R1）

R1 复审 MUST 逐条比对 §2 全部 16 项 findings 的「已修复/未修复/新引入」；P1 三项全部修复 + P2 至少给出处置方案（修复或显式豁免理由）是 APPROVED(_WITH_NOTES) 的前置。修复建议聚焦: ①补 M0 票根 ②验收基线 provenance 化 ③R1 三选一重定义 ④FEAT-044/045 口径统一 ⑤DEC-221 引用更正 ⑥round2 保全件补档。禁止为过审放宽 P1-2 的 provenance 要求（FEAT-043 纪律是本设计的自有承诺）。

*报告完 —— Design Reviewer（REL-082 设计半面 R0），2026-09-19。只读审查，唯一写入面为本文件。*
