# Review: DESIGN-021 — ADR-021 元机制设计（M1 优先级执法 + M2 发现即闭环）DESIGN R0

- **Task**: DESIGN-021（P1）
- **审查对象**: `docs/architecture/ADR-021-meta-mechanisms.md`（439 行，2026-09-29 版——含 Coordinator 通知的 §2 L1 契约措辞修正〔斜杠枚举→顿号枚举〕，修正后文本已实读）
- **Reviewer**: Design Reviewer Agent（独立 Bar Raiser——非该 ADR 作者、非 plan-tracker DRI、无进度压力；单 agent 场景按 tech-review SKILL 第五步执行对立面框架切换后独立得出结论）
- **轮次**: R0（首审）
- **日期**: 2026-09-29
- **依据实读**: ADR-021 全文；decision-log.md L228-231（DEC-286/287/288 原文 + DEC-289 采纳记录）；verify_workflow.py（L6805-6845/L6942-6984/L17045-17119/L24109-24137 等九处）；change_triage.py L1038-1107；task_priority.py L132/L533/L1107/L1272/L1655-1719；write_guard_state.py L145-172/L270/L296；governance_store.py L1590-1634；checks/injection_budget.py（L78-80/L188 等）；agent-presets/governance/agent.cordis.yml.template L55-62；.governance/agent-locks.json 全文；.governance/plan-tracker.md L11；.governance/risk-log.md L31-48；infra/tests/test_registry.py L55-82（+ test_archguard_ratchet.py / test_contract_matrix.py 的 Check 40 退役注释）

---

## 0. 结论

**NEEDS_CHANGE**（unresolved_blockers = 3）

| 级别 | 计数 | 说明 |
|------|------|------|
| P0 | 0 | 无架构级致命缺陷（不 BLOCKED） |
| P1（BLOCKING） | 3 | 设计级缺陷，返工后必须复审 |
| P2 | 5 | 强烈建议修改（可随 P1 修复同批） |
| P3 | 6 | 建议改进，不阻塞 |

总体判断：ADR 的**裁决忠实度高**（DEC-286(1)(2)(6)(7)/287/288 逐条对照无稀释、无加戏语义；字段异名与 L3 接口不变式两处设计判断优秀），**事实基线扎实**（F1-F12 全部实读核对，仅 F10 锁事实过期）。但存在 **3 个 P1 级设计缺陷**：①M1 内部自相矛盾（D1 排序键 vs 契约文本/INV-1 判据——同一 ADR 三处对「machine-signal 不得排 user-named 前」给出不一致答案）；②B2/B3 写路径真空窗未设计（「必填参数」×「锁内唯一 CLI 调用面」×「B2 先行」三者组合在字面实现下必然破坏 triage CLI 或冻结新任务入库，且 FEAT-077 已派发）；③demand_source 无生命周期修订通道（triage 记录不可变 + conflict fail-closed ⇒ 「用户事后点名」这一 DEC-286(7) 核心场景在数据模型中不可表达）。三者均为小改可修复的规格缺口，非方向性错误——修复后建议直接进 R1。

---

## 1. 裁决忠实度对照（逐条）

| 裁决条款 | ADR 承载 | 判定 | 依据 |
|---------|---------|------|------|
| DEC-286(1) fix-at-discovery（活性缺陷发现即修，禁入池） | M2 契约文本「检查 FAIL 任务内修/审查发现即改即合」＋词集含「候选池/留池/0.9[4-9]池」 | ✅ 忠实 | ADR §3.1 vs decision-log L228(1) |
| DEC-286(2) 过程内闭环（当场付清全部闭环成本；付不起就不开始） | §3.1 契约逐字保留两句核心；「付不起触发点闭环成本的动作不开始」原文进入契约 | ✅ 忠实（逐字级） | L228(2) 原文 vs ADR §3.1 |
| DEC-286(6) 零新账稳态（触发点闭环五情形；「登记待以后」废除） | §3.1 五情形逐项保留（检查 FAIL/审查发现/风险即决/证据沉档/发布结账与 L228(6) 一一对应）；「登记待以后」→可检违规（§3.2.1 词集） | ✅ 忠实 | L228(6) |
| DEC-286(6) 执行注记（不立「实现本条」新项目；结构件随 0.93 一次到位） | L3 测试面显式「随 FEAT-076/B-12 承载票——避免为本条立新项目」；B0-B5 归 0.93 清偿轮 | ✅ 忠实（难得的细节级忠实） | L228 执行注记 vs ADR §2.3 |
| DEC-286(7) 需求源加权（用户点名＞活性缺陷＞机器信号旧账） | `_DEMAND_RANK = {user-named:0, active-defect:1, machine-signal:2}` 同序 | ✅ 序忠实；⚠ 同 P 级限定引入语义张力（见 §5 F-P1-1） | L228(7) vs ADR §2.2.2 |
| DEC-286(7)「机器自设期限与用户点名项冲突时**撤机器闹钟**而非压用户项」 | D1 设计下 machine-signal P0 仍压 user-named P1（推荐位）；跨级仅发布门兜底 | ⚠ **部分承载**——撤销语义无推荐位机制承载，ADR 以「P0=阻断语义」论证豁免，但该论证与 (7) 自身分类学冲突（真阻断缺陷应分类 active-defect；machine-signal 按 (7) 定义即「旧账」，其 P0 位是机器自擢升——恰是 (7) 命令撤销的对象）。DEC-289 已采纳 D1，本审查不重裁，但该残余张力 MUST 作为显式残留风险披露且三处文本必须自洽（见 F-P1-1） | L228(7) vs ADR §2.2.2/§2.2.3/§2.1 契约文本 |
| DEC-286(7)「结构性大需求不得无限顺延——一等公民或显式请用户改期」 | INV-2 可机检近似 + 发布门「target_version > release_version = 显式改期豁免」 | ✅ 忠实（机检化合理） | L228(7) vs ADR §2.2.3/§2.2.4 |
| DEC-286(7)「入账默认 P1+期限由用户定」 | ❌ 未机化——§2.2.1 CLI 无 user-named 默认 P1 联动 | ⚠ 轻微缺口（F-P3-3） | L228(7) |
| DEC-286(7) 用词「provenance=user-named」 | 改名 demand_source | ✅ 合理偏离——governance_store.py L1597/L1625 实证 `provenance={"op_id","marker"}` 写入器溯源键已占用，一词两义=架构腐化；§6.3 三候选评估充分；DEC-289(2) 已采纳 | F9 实读 |
| DEC-287(1) 四个 B 级执法点（tpa/change-triage/反倒挂 Check/版本准入门） | §2.2 四件一一对应，零增零减 | ✅ 忠实（1:1） | L229(1) vs ADR §2.2 |
| DEC-287(2)(3) 废除复评窗式顺延/不产生 0.94 池/「登记待以后」废除 | D2 裁决（废顺延留复核，终局三选一）+ 词集「候选池/留池/0.9[4-9]池」+ §3.3「0.93 池退役」 | ✅ 忠实；D2 对「复评动作」与「顺延用法」的切分与 DEC-287(2)「废除**复评窗式顺延**」措辞精确咬合 | L229(2)(3) |
| DEC-287(5) 过渡期执法（推荐/排序逐项标需求源，不标即违规） | L1 契约即该纪律的软件化固定（F12 实证 L229 原句） | ✅ 忠实 | L229(5) vs ADR §2.1 |
| DEC-288 M1 形态「四级梯度：注入契约→B级执法→C级生成」 | L1/L2/L3 + L4 降级矩阵 | ✅ 忠实+一处补全：DEC-288 只点名三段，L4 降级为 ADR 自行补全的第 4 级（工程完备性增补而非语义偏移，已按设计内容而非用户裁决呈现——可接受，建议脚注披露，F-P3 附注） | L230 |
| DEC-288 M2 生效判据「触发会话内闭环率 100%（无新登记待以后行）」 | §3.2.3 `session_closure_rate == 1.0 ∧ deferred_detections == 0` 机检化 | ✅ 忠实（口径逐字对齐） | L230 vs ADR §3.2.3/§5.1 |
| DEC-288「FIX-403 保持第 0 项（M2 首例+解锁）」 | ADR F10/§4 以 FIX-403 为锁对象 | ⚠ 事实过期：FIX-403 已释放、FIX-404 继承锁（F-P3-1） | agent-locks.json 实查 |

**结论**：无偷换、无暗门式稀释；两处 ⚠（D1 跨级语义、默认 P1 未机化）+ 一处事实过期，均入 findings。

---

## 2. 事实基线抽查（F1-F12 全查，任务要求 ≥5）

| # | ADR 声称 | 核对结果 | 证据（实读） |
|---|---------|---------|------------|
| F1 | 关键行为契约四条，SKILL.md L225-232 | ✅ 属实（SKILL.md L225 节标题，L229-232 恰四条）；附注：persona 面契约块为**五行**（含「审查结论必机录」，agent.cordis.yml.template L58-62）——「第五条/第六条」序数以 SKILL.md 为锚，persona 面落地为第 6/7 行（F-P3-2） | SKILL.md L225-232；template L55-62 |
| F2 | INJECTION_CONTRACT_ANCHORS L6805-6845 四面守护；check_injection_contract L6942 existence-only | ✅ 属实（行号精确命中；L6947 注释原文 "Boundary (design §6.5): existence only"；四面清单与 ADR 一致） | verify_workflow.py L6805-6845/L6942-6984 |
| F3 | resident 6000 tok 硬门；strict 余量 391（9→391）；三 profile | ✅ 属实（L78 `INJECTION_BUDGET_TOKENS = 6000`；L80 三 profile；"over-budget resident set now blocks"；plan-tracker L11「FEAT-073 e65b317 strict 注入预算余量 9→391 tok」） | injection_budget.py L78-80/L172-175；plan-tracker L11 |
| F4 | run_triage L1038-1233 五步唯一入口；fail-closed ERROR→{"error"} exit 2；记录不可变 re-triage 拒绝；side_effect additive 先例；CLI thin entry 在 verify_workflow.py | ✅ 属实（L1038 keyword-only 签名；L1046-1050/L1081 "Never raises"；L1097-1104 re-triage 拒绝原文 "the machine record is immutable"；L1062-1066 step-e side-effect WARN 语义；thin entry L24109/L24124 唯一调用点） | change_triage.py L1038-1107；verify_workflow.py L24109-24137 |
| F5 | TaskDep frozen dataclass L532-559；_priority_sort_key L1272-1276=(priority,version,task_id)；_parse_task_row L1107；_ID_TOKEN_RE 中文免疫；run_cli_analysis L2127 | ✅ 属实（TaskDep L533；sort key L1272；_ID_TOKEN_RE L132 `(?<![-A-Z])([A-Z]+)-(\d+)\b`——正则形态实证 CJK 不匹配，中文标注零回归论证成立）；**另实证 recommended_next=全量 unblocked 跨 P 级排序列表（L1696/L1714）**——此事实是 F-P1-1 的判定基础 | task_priority.py L132/L533/L1107/L1272/L1696/L1714 |
| F6 | Check 族最新编号=Check 39（R1 Completion Gate）；Check 33/32/34 对应关系；聚合接线 L16806-17054 | ✅ 属实（L17054 Check 39 box 实证；35-39 box 序列完整）；**但补充发现：Check 40 是退役编号**（FIX-310 退役 check-dsh-skills-manifest，test_registry.py L69-72 注释原文）——编号当前空闲可复用，然 verify_workflow.py L17105 存在以现在时引用旧 Check 40 的 stale 注释（F-P3-4） | verify_workflow.py L16901-17054/L17105；test_registry.py L65-79 |
| F7 | check_release_readiness L7201-7330 子检查列表模式 | ✅ 属实（函数存在于 L7201，行号精确；另有 L1841 fact_source 同族先例佐证子检查模式） | verify_workflow.py L7201 |
| F8 | write_guard_state 五族 FAMILY_VOCABULARY L296；DETECTION_TYPE L270；L156-157 type-agnostic 扩展点原文；新增行 diff window | ✅ 属实（L270/L296 行号精确命中；L156-157 原文逐字 "violations of NEW types ... are a FEAT-064 extension point; the state machine is type-agnostic"；L596 检测记录使用 DETECTION_TYPE）——M2「状态机零改动」论证的代码前提成立 | write_guard_state.py L156-157/L270/L296/L596 |
| F9 | governance_store JSON record `provenance={"op_id","marker"}`（L1597/L1625）；B-12/B-13 未激活 | ✅ 属实（两处行号精确命中；demand_source 异名论证事实成立） | governance_store.py L1597/L1625 |
| F10 | FIX-403 锁 verify_workflow.py+test（TTL 14400） | ⚠ **属实但已过期**——实查 agent-locks.json：FIX-403 已释放，**FIX-404** 持锁（TTL 14400 同）；DEC-289 已改称 FIX-404，ADR 文本未同步（F-P3-1） | agent-locks.json L41-52 |
| F11 | risk-log 活跃行普遍携带「下次复评={版本/事件}」顺延语义 | ✅ 属实（RISK-024「下次复评 0.93」/RISK-039/RISK-044 等多行实证） | risk-log.md L31-48 |
| F12 | DEC-287(5) 过渡期执法原文在 L229 | ✅ 属实（L229 逐字含「所有推荐/排序呈现必须逐项标注需求源〔用户点名/活性缺陷/机器信号〕，不标即违规」） | decision-log L229 |

**抽查结论**：12/12 核对，10 项完全属实、1 项属实但事实过期（F10）、1 项属实+重要补充发现（F5 的 recommended_next 跨级语义 / F6 的 Check 40 退役史）。ADR §1.3 的事实质量在该仓库的 ADR 里属高水准。

---

## 3. 预算算术复核

| 项 | ADR 数值 | 复核 | 判定 |
|----|---------|------|------|
| M1 合计 | ~142 tok | 52+52+19+19=142 | ✅ |
| M2 合计 | ~156 tok | 62+62+16+16=156 | ✅ |
| M1+M2 | ~298 tok | 142+156=298 | ✅ |
| M1 后余量 | 249 | 391−142=249 | ✅ |
| 总余量（§3.1/§8/DEC-289 草案） | ~93 | 391−298=93 | ✅ |
| 总余量（**§2.1 行文**） | **~87** | 与 93 矛盾（疑为早期 M2≈162 估算残稿） | ❌ 内部不一致（F-P2-1） |
| <100 冻结线安全性 | 93<100 ⇒ 落地即触发冻结线 | 语义安全（93≥0 过硬门；冻结线即防回弹），但**冻结线未写入 §2.1 验收判据清单**——BC-1 与 §3.1 引用「§2.1 验收判据 5」而该清单只有 4 项（悬空引用，F-P2-1 合并项） | ⚠ |

逐字/压缩文本措辞修正（斜杠→顿号）对 tok 估算影响 ≈0（分隔符 1:1 替换），估算口径不受影响；真实值以 B1 验收的 check-injection-budget 实测为准（ADR 已如此设计，正确）。

---

## 4. 蓝军充分性评估（BC-1~4）+ 设计方回应

| BC | 击中真风险？ | 缓解实质性？ | 缺口 |
|----|------------|------------|------|
| BC-1 预算回弹 | ✅（391→93 后窗口极窄是真实约束） | 部分——冻结线概念对，但未入验收判据（悬空引用），机检抓手缺位 | F-P2-1 |
| BC-2 存量海瘫痪 | ✅（~199 旧记录实证） | ✅ 实质——覆盖率 0→SKIP+WARN、>0 即严；发布门只看版本载荷；有 Check 30c/DEC-159 渐进先例（L17050-17053 实证） | 无 |
| BC-3 词集误报 | ✅（治理文本自引规则原文是真实误报面） | ⚠ 部分——三层限域中「否定语境窗口」**只存在于 §7 BC-3，未落入 §3.2.1 规范文本**（§3.2.2 重申的仍是「三要素」）——按规范实现的 Developer 会漏掉它，B4 落地即对 DEC-286/287/288 引用文本自伤 | F-P2-4 |
| BC-4 出身洗白 | ✅（Goodhart 是三值枚举的天然攻击面） | ✅ 实质——demand_basis 强制+fail-closed+记录不可变留痕+人工抽验，闭环完整 | 无（但见 F-P1-3：不可变性同时制造了修订通道缺失） |

蓝军覆盖了「对抗使用」与「存量迁移」两族风险，但**漏掉了「合法生命周期事件」族**（需求源漂移）与「实施窗口」族（B2/B3 间写路径）——见红队 RT-1/RT-2，均已升级为 P1 findings。

---

## 5. Findings 清单

### P1（BLOCKING ×3）

**F-P1-1｜M1 排序规则三处自相矛盾（D1 排序键 vs L1 契约文本 vs INV-1 判据）**
- 位置：§2.1 L64/L68（契约文本）× §2.2.2 第 4 点（`_priority_sort_key`）× §2.2.3 INV-1
- 问题：三处对「machine-signal 不得排 user-named 前」给出不一致答案。契约文本（L64/L68「user-named 项未闭合时，machine-signal 项不得排位其前」）与 INV-1（「recommended_next 中存在 M 与 U 且 M 排在 U 之前」）均**无 P 级限定**；而排序键 `(priority, demand_rank, ...)` 按 D1 **刻意**让 P0 machine-signal 排在 P1 user-named 之前。实读证实 recommended_next 是全量 unblocked 跨 P 级列表（task_priority.py L1696 `sorted(unblocked, key=_priority_sort_key)`、L1714）——因此只要覆盖率>0 且「machine-signal P0 与 user-named P1 同时可执行」这一平常状态出现：按 D1 排序 → 契约文本即遭违反、Check 40 即 FAIL。设计自身输出被自己的执法判为违规。反向读法（INV-1 限同 P 级）则 §2.2.2「跨级倒挂由 Check 40 兜底」的自述为假，且 DEC-286(7)「撤机器闹钟而非压用户项」在推荐位无任何机制承载。两种读法都留下缺陷，不能两全。
- 建议（最小修复，尊重 DEC-289 已采纳的 D1）：①INV-1 加 same-priority 限定（同 P 级内 M 先于 U 才 FAIL）；②新增跨级**披露性 WARN**（M(machine-signal, P_i) 排在 U(user-named, P_j>i) 前 → WARN 列出行对，不 FAIL）；③§2.2.2「跨级倒挂由 Check 40 兜底」改为「跨级倒挂由发布门兜底（§2.2.4）+ Check 40 披露」；④契约文本 L64/L68 同步加限定语（如「同优先级内」）或改为「推荐位倒挂详见 Check 40 判据」的指针式表述，消除注入面与判据面的措辞差。⑤将 D1 与 DEC-286(7) 的残余张力（machine-signal P0 按其分类学即机器自擢升旧账，(7) 命令撤销而 D1 容忍其压用户项）作为显式残留风险写入 §7——由 Coordinator/用户知情，不隐含。

**F-P1-2｜B2/B3 写路径真空窗未设计（「必填参数」× 锁内唯一 CLI 调用面 × B2 先行）**
- 位置：§2.2.1 × §4 批次表 B2/B3
- 问题：run_triage 为 keyword-only 签名且契约「Never raises」（change_triage.py L1038/L1081 实读）；其唯一 CLI 调用面在**锁内** verify_workflow.py L24124（kwargs 全集不含新参数）。B2（未锁、**已派发**——FEAT-077 锁实查在案）若按「新增必填参数」字面实现：无默认值 → 锁内调用点 TypeError，CLI 崩溃且违反 Never-raises 契约；带默认值+校验 → 锁内 CLI 在 B3 前无法传参 → 窗口期**所有新 triage exit 2**（Check 32 冻结新任务入库，含可能的 P0 热修 triage）；等 B3 一起 → 「B2 无锁可立即派发」不成立。ADR 对该窗口零讨论（向后兼容节只覆盖读路径 legacy 处理，未覆盖写路径真空）。
- 建议：ADR 增补「窗口协议」并三选一显式化：(a) `demand_source: str = ""` 默认 + 函数内 fail-closed 错误字典（保 Never-raises），且 B2 验收判据增加「与锁内 CLI 的兼容性判据」，把 B3 安排为锁释放后第一动作、窗口内 triage 冻结作为已接受代价报 Coordinator 裁决；(b) 模块先行但硬失败激活经显式开关/版本门推迟到 B3 同窗启用（窗口内 WARN 记录不阻断）；(c) B2 重新定义为「模块+测试合入但发布门/CLI 门不激活」。任选其一写死，不许实现者自由发挥。

**F-P1-3｜demand_source 无生命周期修订通道（状态模型缺口）**
- 位置：§2.2.1/§2.2.2/§2.2.3（conflict 处置）/L4 表
- 问题：triage 记录不可变 + re-triage 拒绝（change_triage.py L1097-1104 原文）+ resolve_demand_source 冲突→conflict→FAIL。组合后果：任务生命周期内的**合法需求源漂移**（用户事后点名一个 active-defect 任务、用户采纳一个 machine-signal 项——前者恰是 DEC-286(7) 防倒挂的核心场景）只有两条出路：手改行内标注 → 与不可变 JSON 永久 conflict → check-governance FAIL；或删行内标注 → 权威面永远停留在旧值，「用户点名」这一事实在机器视界中不可表达。M1 的存在理由是用户点名＞机器信号，但「用户事后点名」无法入账，Goodhart 之外的正向漂移通道被一并焊死。
- 建议：设计 append-only 修订通道：demand_source 修订事件（新 triage 附记录或独立修订记录，强制 demand_basis=用户原话/DEC 引用 + 不可变审计链），resolve_demand_source 取「最新有效修订」为权威、conflict 仅指未声明修订的矛盾；§2.3 L3 字段位置声明同步补「修订记录」键（`demand_source_revisions` 或同形）；BC-4 的防造假属性不损失（修订本身带溯源且不可变）。

### P2（×5）

**F-P2-1｜预算数字内部不一致 + 冻结线悬空引用**：§2.1「~87 tok」与 §3.1/§8/DEC-289 草案「~93 tok」矛盾（正确值 93）；BC-1/§3.1 引用「§2.1 验收判据 5 冻结线」但 §2.1 验收判据仅 4 项、冻结线未落入任何验收清单。建议：统一 93；冻结线写为验收判据第 5 项（机检形式：check-injection-budget 输出余量 <100 时禁止任何使余量下降的注入面变更——可在 B1 测试计划断言）。

**F-P2-2｜B1「整批等锁」原子性论断过强（拆批存在安全序）**：check_injection_contract 为 existence-only（L6947 注释实读）→ 「文本面先行、注册表后行」不产生 FAIL 中间态（旧锚全在场即 PASS，多出的文本不违规）；FAIL 只在「注册表先行、文本未落」序出现。B1 的五个文本面文件（persona/SKILL/behavior-protocol/AGENTS.template/governance-init）均不在任何锁内（agent-locks.json 实查）。建议：改为 B1a 文本面先行（未锁，立即）+ B1b 注册表+预算验证等锁，约束表述为「注册表 commit 不得先于文本 commit」——L1 契约可提前一个锁周期落地（DEC-287(5) 过渡纪律的软件化提前），或至少修正论断措辞以免误导后续排期。

**F-P2-3｜发布门对「未排期 user-named」过触发**：UN=全部非完成 user-named 不限版本，豁免仅 target_version>release_version；而 DEC-286(7)「入账默认 P1+期限由用户定」意味着**未排期是 user-named 的常态默认态** → 任何载 machine-signal 工作的版本恒 FAIL 直到用户逐项显式排期。方向正确（显式改期正是 (7) 原意）但缺交互协议：建议 FAIL issue 附 remediation 说明（一次 AskUserQuestion 完成排期/改期决策），或首版 WARN→FAIL 渐进（与 Check 41 同姿态），并把「未排期=user-named 默认态 ⇒ 过触发常态」的后果明示于 §2.2.4。

**F-P2-4｜BC-3「否定语境窗口」未入规范**：§3.2.1 判定规则仅含行级+新增行限域+豁免清单三要素（§3.2.2 重申三要素），否定语境窗口（词前 8 字符含 废除\|禁止\|违规\|=\|不得）只在 §7 BC-3 出现。建议：升入 §3.2.1 规范文本与验收判据（补负例：引用「‘登记待以后’=违规」类表述 → 零 issue）。

**F-P2-5｜B3 接线面遗漏 FEAT-020 契约矩阵/registry 冻结面**：新增 Check 40/41 box 与 CMD 键改变 check segments/CLI key 计数，test_registry.py 文档化路径要求 contract_matrix snapshot regen + registry 双表一致（quickscan_registry.py 同步声明，E-17 import-time raise；L65-79 实读）。ADR 的 B3 文件清单与「15 行接线」估算均未含 registry.py/quickscan_registry.py/contract_matrix 面。建议：B3 清单补该面，regen 流程入验收判据。

### P3（×6）

**F-P3-1｜F10 锁事实过期**：ADR 通篇 FIX-403；实查 FIX-403 已释放、FIX-404 持锁（DEC-289 已改称）。建议 ADR 文本全局替换并注明「FIX-403→FIX-404 锁继承」事实。

**F-P3-2｜契约条数序数双面漂移**：persona 契约块现为五行（含审查结论必机录，template L58-62），SKILL.md 节为四条；「第五条/第 6 条」以 SKILL.md 为锚，persona 面落地为第 6/7 行。建议措辞改锚点关键词制（锚「推荐必标需求源」「发现即闭环」已唯一），序数仅作描述。

**F-P3-3｜「user-named 入账默认 P1」未机化**（DEC-286(7) 明文默认值）：建议 §2.2.1 校验加联动（demand_source=user-named 且未显式给 P → 建议/默认 P1）或至少 L1 契约声明，避免裁决语义只存活于 decision-log。

**F-P3-4｜Check 40 为退役编号复用 + stale 注释反向误导**：FIX-310 退役旧 Check 40（check-dsh-skills-manifest）；verify_workflow.py L17105 注释仍以现在时提「Check 40」——新 Check 40 落地后该注释会指向无关检查。建议：同批清理该注释，或跳用 Check 42/43 避考古混淆（编号卫生）。

**F-P3-5｜会话边界欠规格**：§3.2.2「同一会话窗口（session-snapshot 会话标识+当日 evidence 行）」——evidence 行无会话 ID 时退化为按日聚合，同日多会话误配对。建议 Check 41 实施前定义精确窗口函数（session-snapshot 起止时间窗或快照 ID 关联）。

**F-P3-6｜L4 降级矩阵缺 Check 41 数据不可用行**（session-snapshot 缺失/损坏时指标行为未定义），与 M2 检测器异常 fail-closed 行不对称。建议补一行并判定（建议 SKIP+WARN 披露，不 FAIL）。

---

## 6. 红队补充发现（ADR 未覆盖的攻击面，≥2 ✅ 实际 4 条）

按 tech-review SKILL 第四步完成视角切换序列（框架→攻击者/最愤怒用户/维护者三角色→多米诺推演）后独立得出；RT-1/RT-2/RT-3 因严重度升级为正式 findings：

- **RT-1（→F-P1-3）攻击者视角**：不需要造假（BC-4 防的是造假），只需要让「用户的真实点名」晚于 triage 发生——不可变记录+conflict FAIL 会把最忠诚的合规行为（用户升级需求源）转化为 FAIL 或语义丢失。多米诺第三步：Coordinator 学会「干脆不标注行内」→ demand_source 数据面悄然腐化 → Check 40 覆盖率虚高但语义失真。
- **RT-2（→F-P1-2）维护者视角**：接手 FEAT-077 的 Developer 面对「必填参数」+「调用方在锁内」的规格只有坏选项可选；多米诺第一步是 TypeError 或 triage 冻结，第二步是有人临时注释掉校验（未入库的口头豁免），第三步是 fail-closed 语义被无声侵蚀——恰是 DEC-286(5) 作废的「静默降级」形态复活。
- **RT-3（→F-P2-5）维护者视角**：B3 合入当晚 contract_matrix/registry 测试全红（E-17 import-time raise 是即抛的）， Developer 若不熟悉 regen 文档路径，最短路径是改快照绕过——FEAT-020 冻结面的「deliberate change」纪律被当作障碍清除。
- **RT-4（→F-P3-4）考古攻击面**：编号是接口。复用退役编号使「grep Check 40」同时命中三个语义世界（退役的 manifest guard/stale 注释/新的 Priority Inversion Guard），六个月后的故障排查会为此付出一次完全可避免的混淆成本。
- **RT-5（增强建议，不计数）**：词集观察期台账建议按「命中词 × 行族 × 否定语境命中」三键分桶回流，翻转 FAIL 前产出误报率报告——BC-3 的「一版观察期数据回流后调词集」目前无数据结构支撑，等于承诺了没有容器的观测。

---

## 7. Coordinator 通报事项的审查注记（M5 扫描器误报面）

已实读修正后 L64/L68：顿号枚举「三类之一：用户点名、活性缺陷、机器信号」语义零变化确认（三值封闭+逐项标注+倒挂禁令完整保留），修正本身不影响本报告任何结论与预算复核。观察项采纳并扩展：**Check 10 M5 扫描器把「斜杠枚举+选项语境词」判为内联选择菜单的误报面，对治理契约文本是结构性风险**——契约条款天然密集使用「A/B/C 三选一」句式（本 ADR 之外，behavior-protocol/SKILL.md 现有条款同样暴露）。建议（仅建议）：FIX-295 白名单评估扩展至 docs/architecture/**（治理设计文档语体），或扫描器增加「枚举定义语境」窗口（「三类之一：」「三选一」前导词豁免）——与 F-P2-4 的否定语境窗口同构，可同一批实现。此项不计入 findings（非本 ADR 缺陷）。

---

## 8. 批次与锁约束核验（B0-B5）

- B2/B1 并行零交集声明：✅ 正确（B2 文件集与 B1 文本面无交集；FEAT-077 锁清单实查佐证）。
- B1 原子性论断「拆开会出现锚点 FAIL 中间态」：❌ 过强——安全拆序存在（文本先行），见 F-P2-2。
- B3 依赖 B2、B4 域函数可随 B2 先行：✅ 合理。
- B5 生效确认闸设计（Check 40 在场+排序实测+Check 41 首测→evidence+decision 入账）：✅ 与 DEC-288「可验证效果」口径咬合。
- 锁事实：F10 过期（F-P3-1），DEC-289 层已纠正。

## 9. 降级矩阵评估（L4）

八行中七行与 DEC-286 fail-closed 精神一致且有实证先例（锚点 existence-only、预算硬门、triage 零写入、发布门未申报即拒、检测器异常 loud disclosure——各自代码语义均已实读核对）。「tpa 联查 fail-open to 行内标注」是唯一 fail-open 行，其理由（md 优先落地保证单面可用+conflict 仍 fail-closed）成立，属可用性与一致性的正确权衡而非语义回退。缺口一行（Check 41 数据不可用，F-P3-6）。Check 40 覆盖率 SKIP+WARN 的分阶段设计有 Check 30c/DEC-159 先例支撑（L17050-17053 实证）。

## 10. 过程内闭环声明核验

§附录声明基本成立：L3 以「引用既有票据而非新立项目」规避 DEC-286 执行注记违反——论证成立；词集/渐进翻转均显式登记为治理动作。唯一自违点：§2.1 正文承诺「写入验收判据」的冻结线实际未写入验收清单（F-P2-1）——按 ADR 自己的标准这算一处「说了没做」的闭环缺口，随 P2 修复即可。

## 11. 硬门槛自检（design-reviewer 角色 + tech-review 结构检查）

| 门槛 | 结果 |
|------|------|
| 候选方案 ≥2（每组） | ✅ §6.1/6.2/6.3 各三候选+排除理由 |
| ADR 关键字段完整（日期/背景/决策/备选/排除/影响/后续/可逆性） | ✅ 全 |
| 蓝军 ≥3 条带 ID+缓解 | ✅ BC-1~4（缺口已由红队 RT 补足并升级） |
| 无循环依赖 | ✅ 新模块 checks/provenance_domain.py 单向依赖 task_priority/change_triage；无环 |
| 结构完整性四项（目标/方案/替代/风险） | ✅ |
| 架构质量（职责/依赖/契约/数据流/错误处理/扩展/测试） | ⚠ 错误处理面含 P1-1/P1-2 两处不一致；其余合格 |
| 事实依据红线 | ✅ 本报告全部结论附实读行号 |

## 12. 返工最小修复集（供 R1 复审逐条比对）

1. 统一 M1 排序规则三处表述并明确 INV-1 的 P 级限定与跨级兜底归属（F-P1-1，含契约文本 L64/L68 措辞同步）。
2. 写死 B2/B3 窗口协议三选一（F-P1-2），B2 验收补锁内 CLI 兼容性判据。
3. 设计 demand_source 修订通道（append-only + demand_basis 溯源 + resolve 取最新有效；L3 字段声明同步）（F-P1-3）。
4. 预算数字统一 93 + 冻结线入验收判据第 5 项（F-P2-1）。
5. 否定语境窗口升入 §3.2.1 规范+负例（F-P2-4）。
6. P2-2/P2-3/P2-5 与 P3 各项按需随批处理（P3 不阻塞 R1 通过）。

---

**审查结论：NEEDS_CHANGE**（unresolved_blockers=3；P0=0 / P1=3 / P2=5 / P3=6）

按 M7.4：Coordinator 需将本报告退回 Architect 修复 ADR，随后 re-spawn 同一 Design Reviewer 执行 R1（round+1，本报告路径为强制读取项）。R1 复审重点 = §12 最小修复集逐条「已修复/未修复/新引入」比对。
