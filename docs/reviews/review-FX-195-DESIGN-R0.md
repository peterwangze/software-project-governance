# Review FX-195-DESIGN-R0 — 设计审查：quick-scan 前移评估（docs/requirements/quickscan-evaluation-0.79.0.md）

- **审查任务**: FX-195-R0（plan-tracker L202：设计任务 Architect → Design Reviewer；产出 docs/requirements/）
- **审查对象**: `docs/requirements/quickscan-evaluation-0.79.0.md`（330 行，10 节，未提交新文件；作者 Architect Agent，2026-09-10，测量 HEAD c96da1b）
- **审查者**: Design Reviewer Agent（round R0，首次审查——无前轮 findings 需比对）
- **审查日期**: 2026-09-10
- **加载规范**: `agents/design-reviewer.md` 全文 + `skills/design-review/SKILL.md` 全文 + `skills/tech-review/SKILL.md` 全文
- **审查模式**: 只读（本报告为唯一写入物；零产品代码/零 .governance 写入；未执行任何命令——全部验证经 Read/Grep/Glob 文件面完成）

---

## 1. 审查结论

# 终态：APPROVED_WITH_NOTES

unresolved_blockers=0

| 项 | 值 |
|---|---|
| BLOCKING | **0** |
| WARNING | **1**（W-1：热文件尺寸申报与同仓一日前实测记录不可调和，且未附复现命令） |
| SUGGESTION | **6**（S-1~S-6，均为锚点精度/口径统一类，可随入档或 triage 处置） |
| 硬门槛（agents/design-reviewer.md） | 全部通过（§7） |
| Design Doc 结构 5 项 | 全部通过（§4） |
| 事实锚定抽查 | **17 处核实 / 2 处部分核实 / 1 处工具面不可核**（§2）——远超任务书 ≥6 要求，无一锚点虚构 |
| Bar Raiser | 独立评审已执行，**不行使否决权**（§6） |

**结论依据（一句话）**：评估的策略取舍（Phase-1 注册表 → Phase-1.5 缓存 → Phase-2 闭包，A 的形态承载 B 的语义）论证充分且与演进 §9.3 既定架构位零冲突；四态输出契约与 §9.3 逐字一致且机器可判定；shadow 先行语义忠实且更保守；蓝军 4 条独立且各有缓解链；全部关键结论可溯源至已核实的事实源。唯一 WARNING 是支撑性数据（热文件尺寸）的「实测」标签与同仓既有记录存在未调和矛盾——不改变任何设计结论方向，入档前须一条命令补核。

---

## 2. 事实锚定抽查（任务书验收 ②：≥6 处；实际核查 20 处）

| # | 评估中的声称 | 核验位置（本审查实测） | 裁决 |
|---|---|---|---|
| A-1 | F-1：§9.3 表态全文（L454-L462） | architecture-evolution-0.80.0.md L454-L462 逐字比对：「采纳顾问 Q7……选择策略」「原有实现（不改检查体）」「通过/未执行/缓存复用/无法判断（禁把"没查"报成"通过"）」「先 shadow 比较再改 hook 政策」「初期只做子集选择；跨进程缓存后置（缓存键 = 引擎/规则版本 + 配置 + 输入指纹）」全部原文在锚位置 | ✅ 一致 |
| A-2 | F-2：RISK-044 行（risk-log L41）两段摘引 | .governance/risk-log.md L41：31-32s 段、65.7/61.3/64.7/56.6s 段、DEC-177 ② 转「缓解中」、「下次复评 = quick-scan 评估结论入档 / 0.79.0 M-8」逐字一致 | ✅ 一致 |
| A-3 | F-3：FEAT-018 基线（median 41.796 / warm 41.311 / P95 44.663 / status 0.5215 / import self 103.21ms / c443757 / serial-exclusive） | perf-baseline-0.80.0.json：summary wall median 41.796（L182）/ warm_median 41.31145（L184）/ p95 44.6627（L183）/ status median 0.5215（L70）/ summary importtime self_total_ms 103.21（L189）/ status 101.925（L77，§5.1 脚注「101.9ms」对应）/ git_head c443757…（L38）/ load_class serial-exclusive（L39）/ Python 3.14.3（L32，§5「同机同版本」成立——cwd 同仓 L37） | ✅ 全数字一致 |
| A-4 | F-4：容差表（serial median_rel 0.10 / P95 0.25；parallel 仅观察） | core/perf-tolerance.json：summary serial-exclusive median_rel 0.1 / p95_rel 0.25（L31-32）；parallel-observed note「observation-only caliber, never a gate」（L39）；task=FEAT-018（L3） | ✅ 一致 |
| A-5 | F-5：FEAT-020 快照 count=70 + freeze note + version_status | infra/contract_matrix/snapshots.json：check_segments.count=70（L4）/ freeze_point.note「冻结基线含此清单（S6 版本规划对账用）」（L370）/ version_status「0.79.0 未 released」（L386）；freeze_point.residual_waves 含 FX-195（L375，与本文为 0.79.0 收尾波次一致） | ✅ 一致 |
| A-6 | C3 四段名（28g Governance Context Discovery / 28j Capability Context Trace / 28l Restricted Host Capability Context / 29 M5 Runtime Triggers） | snapshots.json L112/L115/L117/L127 逐字一致（含 FIX 编号） | ✅ 一致 |
| A-7 | F-6：FX-195 任务行（plan-tracker L202） | .governance/plan-tracker.md L202：P2 / 0.79.0 /「设计任务（Architect → Design Reviewer；产出 docs/requirements/……）」「实现任务另行 triage」逐字一致——本文非目标边界与任务行吻合 | ✅ 一致 |
| A-8 | F-7：summary-only 机制（L14630-L14657；_run_full_engine_checks L14767 起） | verify_workflow.py：cmd_check_governance L14630；summary_only 分支 StringIO+redirect_stdout L14647-14652；_run_full_engine_checks def 于 **L14767**（锚分毫不差）；docstring「The default (no --summary-only) path is byte-identical」L14637-14639——§2.4 硬约束④的契约先例注释属实；test_summary_only.py 存在（infra/tests/） | ✅ 一致 |
| A-9 | F-8：`_PLUGIN_PRODUCT_CHECK_IDS` 现行 25 段（L14669-L14698）+ 登记注释原文 | frozenset 起于 **L14669**；逐项清点 = **25** 个 ID（7,10,11,12,15,24,28b,28d,28e,28f,28h,28i,28k,28m,28n,28o,28p,28q,28r,28t,28u,30b,31,33,40）——与 §3.1 C1 清单 25 项**逐一相符**；注释原文「新增检查只需在目录中登记一行（先声明事实源，再决定归属），不得在引擎代码里硬编码编号黑名单」在 L14667-14668（ALT-1 引「L14668」成立） | ✅ 一致 |
| A-10 | F-8 数字：FIX-270 宿主 full 25.49s→2.40s（-91%）/ summary-only 2.49s（audit-facts §7.3 L431） | architecture-audit-facts-0.80.0.md L431 逐字一致（含「22 项产品自检」时点口径——评估正确区分「FIX-270 时 22 项 vs 现行 25 段」，无混淆） | ✅ 一致 |
| A-11 | F-9：bootstrap 摘要消费点（SKILL.md L64；behavior-protocol.md L221） | SKILL.md **L64**：「运行 …… check-governance --summary-only …… 读取 `Governance: {N} issues` 汇总 + 首个 FAIL/WARN 项」；behavior-protocol.md **L221**：健康摘要条款原文 | ✅ 锚行号精确 |
| A-12 | F-10：post-commit Step 4 每 commit 跑全量 check-governance（L188-L193） | infra/hooks/post-commit **L188-L193**：`python "$VERIFY_WORKFLOW" check-governance 2>/dev/null \| grep -E "(Check [0-9]\|PASS\|WARN\|issued)" \| head -12`——「全量 + grep head -12」与 §2.1 表逐字吻合 | ✅ 锚行号精确 |
| A-13 | F-11：EVD-969 issues 构成（27 = 28o×8 + 28p×3 + 28s×2 + Check 30×7 + 31×1 + WARN 族；audit-facts §8.2 L454） | audit-facts L454 逐字一致（evidence-log L1829，REL-074，2026-09-09）；§3.2 算术（12 个来自 C1；27→15）自洽。注：面板计数 26 vs 27 的 ±1 未归因缺口系 facts L455 自己如实登记——见 S-3 | ✅ 一致（带口径注） |
| A-14 | F-13：quickscan-orchestration deps/版本（§10 L525）；light-registry（L517，deps=contract-layer，0.80.0，M） | evolution L525：deps=「0.79.0 quick-scan 前移评估结论（DEC-177 ②）；REFACTOR-light-registry」/ 0.81.0~0.82.0 / L；L517：deps=REFACTOR-contract-layer / 0.80.0 / M——「对 REFACTOR 是硬前置、对 Slice 1/2/3 非硬前置」的依赖论证与演进编码吻合 | ✅ 一致 |
| A-15 | 实测子命令真实存在（§5.1 24 条） | 抽验 5 个冷门子命令在 verify_workflow.py subparser+dispatch 双表注册：check-loop-runtime-claims（L23917/L24297）、check-plugin-freshness（L23489/L24252）、check-injection-contract（L23701/L24277）、check-dsh-preset-smoke（L23717/L24279）、check-governance-data-size（L24007/L24303）；§5.4 复现命令形态与 A-8 入口一致 | ✅ 可复现 |
| A-16 | ALT-2 引 DEC-149 原文「产生第二套引擎语义（子集 ≠ 全量看护完整性）、与『复用同一引擎』设计冲突、规模扩张」；BM-1 引 DEC-149 初衷「会话开始看见全部 issues」 | DEC-149 已归档：.governance/archive/decisions/decisions-v0.1.0-0.78.0.md L303 方案 B 否决理由**逐字一致**；同行「完整性优先：bootstrap 摘要的目的是『会话开始就能看见全部 40/137 issues』」——BM-1 张力锚点属实。修订验收「单次 <60s 且每会话仅一次」亦在该行核实 | ✅ 一致（经归档路径） |
| A-17 | §2.3/§6 引 FEAT-019 先例「主文件仅 +18 行接线」 | plan-tracker L212（FEAT-019 行）：「独立模块 1,106 行 + ……主文件仅 +18 行接线」逐字一致 | ✅ 一致 |
| A-18 | 演进 §9.2/§9.4/§9.6 支撑引文（共享快照/编排隐性成本命名；「接受单进程下限，不虚承诺」；四态披露+[SKIP] 沿用） | evolution L452（「消除 70 段各自重复解析——facts §3.5 编排现状的隐性成本」）、L466（§9.4 原文）、L483（§9.6「quick 输出四态披露（§9.3）+ [SKIP] 披露沿用」）全部在锚位置；facts §3.5 标题「print 编排重复面抽样证据（≥3 处并排）」在 L210 | ✅ 一致 |
| A-19 | §3.1/§5.3 热文件尺寸「实测」（evidence-log 1,432KB / plan-tracker 288.5KB / decision-log 104.1KB） | **不可完全调和**：audit-facts §6.1/L381/L582（2026-09-09 实测）= evidence-log 1,419.5KB（方向一致，+12.5KB 日增量合理）/ plan-tracker **344.1KB**（评估值缩 16%）/ decision-log **205.7KB**（评估值缩 49%）；.governance/archive/index.md 无 2026-09 归档迁移条目（Task 索引最新远早于 09 月；Decision 归档止于 DEC-173/0.78.0），单日缩量无事件可解释；评估未附尺寸测量命令（§5.4 仅覆盖墙钟） | ⚠️ 部分——W-1 |
| A-20 | 「三 commit +12%」（41.796→47.0，c443757→c96da1b） | +12% 算术自洽（47.0/41.796 = 1.124）；commit 计数因审查工具面无 git log 不可独立复核（plan-tracker 可见 c443757=FEAT-019、c92bf5d=FEAT-020、1bb4268=FEAT-018、3a108c2/c96da1b=FEAT-013 区间内 ≥3 commit，量级吻合） | ◐ 部分（算术✓/计数未核） |

**锚定总评**：任务书点名的 6 类锚（§9.3 原文 / FEAT-018 数字 / FEAT-020 count / RISK-044 行 / L14669-14698 代码锚 / 实测命令）**全部核实且锚行号精确**；另核 14 处延伸锚中 12 处全一致、1 处部分（A-19→W-1）、1 处工具面受限（A-20）。无虚构锚点；唯一实质缺陷是 A-19 的尺寸申报（见 W-1）。

---

## 3. 设计面五项审查（任务书审查重点 ①~⑤）

### ① 策略取舍论证充分性（注册表 vs 直接闭包；Phase 分层必要性 vs 过度工程；「A 的形态承载 B 的语义」）——**通过**

- **必要性论证成立**：三支柱各自核实——(a) 疼痛在当下且单调恶化（47.0/46.8s 实测 + 3 commit +12%，对照链六时点全部锚定属实）；(b) Phase-2 最快 0.81.0（F-13 依赖链 contract-layer→light-registry→本体，演进 §10 原文核实——light-registry 本身 0.80.0 才开工）；(c) §9.3 自留过渡空间（「初期只做子集选择；跨进程缓存后置」原文核实）——把「后置」的缓存提前到 Phase-1.5 有量化理由（§4.2：纯选择 28-33s 达不到 <15s，量级突破必须靠缓存），不是拍脑袋加档。
- **「A 的形态承载 B 的语义」判定合理**：注册表每行「事实源根 + 输入路径清单」确实是 input_deps 的第一列字段；`_PLUGIN_PRODUCT_CHECK_IDS`（L14669 实测 25 项）已证明「按声明选择段」在生产可用（宿主 -91% 实测）；Slice-1 验收③「表 schema ⊂ CheckSpec.input_deps 字段集」把平移性做成机器判据，配合 FEAT-020 冻结清单（count=70 核实）保证「零弃子」主张可验证而非口号。
- **过度工程反证（stage-architecture AI 风险表视角）**：本设计对「AI 过度工程」的三种典型形态均有结构性防御——不造第二引擎（ALT-2 否决 + §9.3「原有实现」锚）；不为未来规模预支复杂度（Phase-1 是静态子集，增量语义全套留给 Phase-2 既定任务）；载体最小侵入（FEAT-019「主文件仅 +18 行」先例核实 + 默认路径字节等价 + §4.3 四条回退全可逆）。分档验收（Phase-1 <60s 下限/<15s STRETCH 如实披露）杜绝虚报。**结论：分层是收敛路径不是过度工程。**
- 残留弱点（不构成 finding）：Phase-1（~30s）与 Phase-1.5（暖 1-5s）是可分离切片，若 1.5 滑出 0.80.0，纯选择的边际收益仅 ~17s/会话——该风险已被 §2.3 版本槽建议（「同批或紧随」+ 最晚 0.81.0）与 QR-6 分档披露覆盖，可接受。

### ② 事实锚定抽查 ≥6 处——**通过**（20 处核查，见 §2）

### ③ 四态输出契约与 §9.3 一致性 + shadow 先行语义——**通过**

- 四态命名与 §9.3 L460 **逐字一致**（通过/未执行/缓存复用/无法判断）；「禁『没查』报『通过』」落实为四条机器可判定硬约束（N=unknown 规则、四态计数必现+守卫测试、--fail-on-issues 语义不变、默认路径 byte-identical——后者的契约先例 docstring 与 test_summary_only.py 均核实存在）。状态与 PASS/FAIL 正交的显式声明（§2.4 首句）是比 §9.3 原文更精确的语义澄清，方向正确。
- shadow 先行：§4.1 三级递进（S-A 干跑/S-B 执行/S-C 缓存）+ 量化切换门槛（≥3 会话或 ≥10 commit 零意外）是对 §9.3「先 shadow 比较再改 hook 政策」的忠实且更保守的落地——评估把 **bootstrap 切换**也置于 shadow 门之后，而 hooks 政策维持 full 直至 Phase-2 复评（§3.3 表四行政策与 §9.3「hooks 可消费**经验证** quick」对齐）。S-B 的「任何不一致 = BLOCKING（反哺 input_deps 完整性）」把等价性验证转化为 Phase-2 的输入，设计闭环良好。
- 缓存键与 §9.3 原文逐字一致（引擎/规则版本 + 配置 + 输入指纹）；「缓存复用态」的裁决时间戳披露（§2.4 表）满足审计可溯。

### ④ 蓝军 4 条独立性（尤其 BM-4）——**通过**

- **独立性成立**：BM-1（消费面信息回归——取舍型）、BM-2（缓存正确性/生产者缺失——机制型）、BM-3（分类错误看护窗口——数据型）、BM-4（分档成本效益——决策型）四条分属四个不重叠的失败域，无互相换皮；每条有独立缓解链（BM-1→四态披露+DEC-177② 裁决链；BM-2→内容哈希指纹+miss 即回退+S-C 零不一致门禁；BM-3→C3 默认保留+S-B 全量比对+窗口期非新增论证；BM-4→语义地基论+ALT-3 对照+分档验收）。
- **BM-4 回应说服力**：成立。Phase-1 的交付物本质是注册表+四态契约+shadow 通道（Phase-1.5/2 的硬前置），墙钟收益是顺带；「不做的替代」由 ALT-3 承载（依赖链最长+再忍 1~2 版 47s+ 且成本单调增长有实测）；分档验收保证不虚报。反驳「忙碌工作」的最强论据——**无论早晚都要做且零弃子**——有 Slice-1 验收③的机器判据背书。
- BM-1 的取舍锚点经归档 DEC-149 核实为真实张力（「会话开始就能看见全部 issues」原文），非稻草人；回应未回避（承认取舍+披露义务机器化 QR-4）。

### ⑤ 非目标边界 + 实现建议 triage 性——**通过**

- 非目标四条边界清晰且有行为对应：零产品代码（§5 只读口径 + 本文件单产物声明）、不重开 §9.3（「若偏离走 decision-log 裁决；本评估无此需要」——评估结论确实全部落在 §9.3 框内）、不虚承诺（§9.4 原文锚 + 分档 STRETCH 如实标注）、不处理宿主（FIX-270 已闭环，2.40-2.49s 锚核实）。
- Slice 三件 triage 六字段完备：内容/依赖/规模（S-M/M/M）/验收要点（每条可运行判定）表内齐备 + 版本槽建议（§6 正文，0.80.0 建议/最晚 0.81.0 + DEC-145 入账纪律声明）+ 回滚路径（§4.3 四条）。ID 显式留待 change-triage（符合 DEC-145 新任务新版本原则）；四处开放事项（§10 尾）逐项有归属（triage/Coordinator/Slice-1 验收/Slice-2 交付）。C3 待判定段不下逐段断言、默认 fail-safe 保留并绑定 Slice-1 验收——诚实且可执行。
- 与 REFACTOR-light-registry 前置关系的「任务书点名问题直接回答」结构（对 Slice 非硬前置/对 REFACTOR 硬前置 + 载体禁入巨石编排线的对冲）与演进 §10 依赖编码吻合（A-14 核实）。

---

## 4. Design Doc 结构 5 项检查（tech-review 第一步 + §10 自检复核）

| # | 检查项 | 裁决 | 位置 |
|---|---|---|---|
| 1 | 目标（问题陈述 + 可度量目标） | ✅ | §1.1 问题陈述（机制实证+受害场景界定）/ §1.2 G-A~G-F 六目标 |
| 2 | 方案描述 | ✅ | §2（语义+四态契约）/ §3（范围分类）/ §4（shadow+性能+回退）/ §5（实测） |
| 3 | 替代方案 ≥2 含否决理由 | ✅ | §2.2 两策略对比 + §7.1 四否决项（ALT-1~4，各带引文/量化理由） |
| 4 | 风险评估含缓解与回滚 | ✅ | §7.2 QR-1~QR-6（QR-5 回滚列「—」为测试性防线无回退面，可接受）；§4.3 独立回退节 |
| 5 | 非功能需求覆盖 | ✅ | §9 七行矩阵（性能/可用性/可维护性/可测试性/兼容性/安全/可扩展性），每行有承载节 |

---

## 5. Findings（位置 + 严重级别）

### W-1（WARNING）热文件尺寸「实测」申报与同仓一日前记录不可调和，且无复现命令

- **位置**: §3.1（分类事实源句）/ §5.3（残差归因第 1 条）——「治理热文件实测：evidence-log.md 1,432KB、plan-tracker.md 288.5KB、decision-log.md 104.1KB」
- **事实**: audit-facts §6.1/L381 + L582（2026-09-09 实测，带字节级原始输出）= evidence-log 1,419.5KB / plan-tracker **344.1KB** / decision-log **205.7KB**。evidence-log 日增 +12.5KB 方向合理；但 plan-tracker 单日 −55.6KB（−16%）、decision-log 单日 −101.6KB（−49%）在无归档/压缩事件记录下不可解释（archive/index.md 无 2026-09 迁移条目，Decision 归档止于 DEC-173）。评估 §5.4 复现命令仅覆盖墙钟，未覆盖尺寸。
- **影响评估**: 不改变设计结论方向——残差归因本身已诚实标注为「假设链/数据缺口」（§5.3），且无论取哪组值，「大文件被十余段重复解析」的论证均成立（全部口径下三文件都 ≥100KB、evidence-log ≥1.4MB 两源一致）。但「实测」字样在本评估的事实锚定纪律（§0 全引用表）下必须可复现，同仓矛盾记录存在时尤甚。
- **修复建议（入档/commit 前一条命令）**: 在 §5.4 补尺寸复现命令（如 `Get-Item .governance\*.md | Select-Object Name,Length` 或直接引 Check 28s 输出——其报文格式含逐文件字节数，audit-facts L381 有先例），并二选一：确认评估值为 09-10 当前真值（同时注明与 audit-facts 09-09 值的差异归因），或改引 audit-facts 口径。处置后本条即闭环。

### S-1（SUGGESTION）R1 棘轮锚数值过时（两处）

- **位置**: §4.3 ③「R1 棘轮（24,302 锚）不受结构性冲击」/ §6 总原则「R1 棘轮 24,302 锚安全」
- **事实**: 24,302 是 FEAT-019 交付时点值（plan-tracker L212）；同日 FEAT-012 收紧至 24,269（L197）、FEAT-013 再生成至 24,329（L198）——core/architecture-baseline.json L17 现值 `anchor_loc: 24329`。评估 HEAD c96da1b 时点现锚应为 24,329。
- **影响**: 论证方向不变（「接线行级改动对任何锚值都可忽略」），但本评估以锚点精度自我要求，同日过时值应勘误。建议统一改为「R1 棘轮（现锚 24,329，architecture-baseline.json）」。

### S-2（SUGGESTION）§4.2 Phase-1 估算式口径混用

- **位置**: §4.2 Phase-1 行括号分项「31 段 9.5~11.0s + 28o 2.4s + 28b 2.1s + 15 1.5s + 7 类比 ~1s + 其余 ~0.5-1s」引用 §5.2，但总额标注 ~15-16.5s
- **事实**: 括号内为命令毛墙钟（§5.1 表 run 值），合计 ≈17-19s；15-16.5s 是 §5.2 扣底座后的**边际**口径（31：9.2-10.7 等）。两口径在同一条估算式内混用。最终结论不受影响（边际推导 47−(15-16.5)=30.5-32s 落在宣称的 28-33s 带内），但估算链标注建议统一为边际口径，避免 triage 时误读。

### S-3（SUGGESTION）「当前 27 issues」宜加口径注

- **位置**: §0 F-11 行 / §3.2 / §8 BM-1
- **事实**: 27 为 EVD-969 定性口径（audit-facts L454 逐字核实）；session-snapshot 终态面板计数 26，±1 未归因缺口系 facts L455 自己如实登记的数据缺口。评估引用 F-11 锚本身准确，但「当前」措辞宜注口径（「27（EVD-969 定性口径；面板计数 26/27 差一未归因——facts §8.2」），与全文其余锚的精度对齐。BM-1 的 12/15 算术不受 ±1 影响。

### S-4（SUGGESTION）ALT-4 对 DEC-149 方案 C 的转述超出档案定性

- **位置**: §7.1 ALT-4「DEC-149 方案 C 已定性（超范围、不治本）」
- **事实**: 归档原文（decisions-v0.1.0-0.78.0.md L303）为「超本任务范围，与慢 check 零相关（FIX-264 未引入新耗时），可作为 0.77+ 独立批次」。「超范围」有据；「不治本」是本评估自己的量化加持（四重域仅 15-16.5s/47s、残差 ~30s 在宿主段——论证本身成立且充分），不宜归入 DEC-149 定性。建议措辞改为「DEC-149 定性超范围；本评估量化加持：不治本（残差 ~30s 不在重域）」。

### S-5（SUGGESTION）C2 段数「约 40」与列举 41 不一致

- **位置**: §3.1 C2 行标题「约 40 段」vs 列举 41 项；§3.1 汇总行「41 保留」
- **事实**: 逐项清点 C2 列举 = 41；41+25+4=70 与 FEAT-020 count 闭合。建议表头统一为 41，避免「约」与精确汇总行并存的微瑕。

### S-6（SUGGESTION）Phase-2 终态双选择器关系宜显式命名

- **位置**: §6 REFACTOR 行（平移 Slice-1 注册表为 CheckSpec.input_deps）/ §10 开放事项
- **事实**: Phase-2 落地前，巨石内 `_PLUGIN_PRODUCT_CHECK_IDS`（L14669，事实源根切分）与 Slice-1 注册表将并存——QR-5 已保证并存期的**运行时正交**（宿主 quick∩product-skip = NOT_RUN(product-gate)，不产生第三语义），但未声明终态是否由 CheckSpec.input_deps **吸收/退役** `_PLUGIN_PRODUCT_CHECK_IDS`。§2.3 称注册表是其「推广」，建议在开放事项补一句终态归属，防止第二份选择清单永久化（RISK-046「登记与实际漂移」同族病理的远期防线）。

---

## 6. 蓝军挑战（Reviewer 独立蓝军——tech-review 第四步单 agent 协议）+ Bar Raiser（第五步）

**视角切换序列执行记录**：框架已从「这个设计为什么是对的」切换为「这个设计最可能在哪里失败」；识别出的 3 个核心假设——A1 分类边界稳定（25 排除段事实源判对）、A2 post-commit full 作为缓存生产者的节律在真实工作流中持续存在、A3 残差 ~30s 确由保留段重复解析主导（未插桩）。攻击者/最愤怒用户/维护者三视角各完成「出问题后第一块多米诺骨牌」推演，输出如下（标准格式）：

| 攻击向量 | 影响评估 | 当前缓解 | 残余风险 | 建议增强 |
|---|---|---|---|---|
| 攻击者：会话中途直接改写 .governance（不经 commit），缓存指纹过期但 bootstrap 读到的是「改写前生产者+改写后输入」的组合 | 高危若指纹机制漏输入；实际=指纹集合不完整时缓存 miss 回退执行 | 缓存键=内容哈希指纹（非 mtime）；指纹不完整→UNDETERMINED→回退（§2.4）；S-C 零不一致门禁 + 中毒负对照（Slice-3 ②） | 低（依赖 Slice-1 输入路径清单的完整性——恰是 S-B shadow 的检验对象） | Slice-1 验收可加一条：指纹输入集 ⊆ 注册表输入路径声明的机判对账（与 Slice-1 ①②同源，成本近零） |
| 最愤怒用户（dogfood 会话 agent）：切了 quick 后 bootstrap 仍 ~30s（Phase-1.5 未跟上），「秒级」预期落空 → 信任摘要而跳过 | 中——体验预期管理失败会反噬采纳 | 分档验收如实披露（Phase-1 <60s 为 PASS 下限、<15s STRETCH 大概率未达已预告）；切换门槛 shadow 先行 | 低-中（若 Phase-1.5 滑档，纯选择收益 ~17s/会话） | 可在 C-3 消费切换条件中显式挂接「暖缓存达标」作为切换偏好项（非硬门），或声明 Phase-1 期间 bootstrap 可暂缓切换至 1.5 就绪——留 triage 裁决即可 |
| 维护者：Phase-2 前双选择器并存（巨石 frozenset + infra 注册表），新检查需登记两处 → 漂移面翻倍 | 中——长期第二事实源 | QR-5 运行时正交；Slice-1 ②完整性守卫（未入表回退 full + 告警）；FEAT-020 harness 对账 70 段 | 中（守卫降低漏检概率但不消除双登记维护成本） | 即 S-6：命名终态吸收关系 + 可选守卫增强（注册表与 `_PLUGIN_PRODUCT_CHECK_IDS` 的交集段声明一致性 WARN） |

**Bar Raiser 独立结论**（切换分析框架后得出，不复用 §8 Architect 自蓝军框架）：三核心假设中 A3 为显式声明的假设链（数据缺口诚实登记 + Phase-2 复测基线承诺——处置合规）；A1/A2 均有 fail-safe 方向的错误后果（判错只损失性能不损失覆盖：C3 默认保留；生产者缺失降级为冷缓存行为——均已核实为设计内建而非口号）。**不行使否决权**；否决解除条件不适用。W-1 为数据标签精度问题，不构成否决事由（其承载论证已自标假设链）。

---

## 7. 硬门槛裁决（agents/design-reviewer.md）

| 门槛 | 阈值 | 裁决 | 依据 |
|---|---|---|---|
| 候选方案数 | ≥2 | ✅ | §2.2 两策略 + §7.1 四否决（ALT-1~4） |
| 蓝军挑战条数 | ≥3（独立 ID） | ✅ | §8 BM-1~BM-4（独立性见 §3④）；本审查另附独立蓝军 3 条（§6） |
| 关键结论可溯 | 全部 | ✅ | §0 F-1~F-14 引用表；本审查 20 处抽查（§2）无一虚构 |
| 不写产品代码 | — | ✅ | 评估自声明 + 本审查确认其产物为单文件 docs/requirements/；未发现任何产品文件修改迹象 |
| ADR 式字段 | 按文档类型 | ✅（评估文档型） | 本评估不含架构决策变更（确认 §9.3 既定位，无需新 DEC）——自检 §10 声明与内容相符；Slice 入账走 change-triage 的路径已显式编码 |

---

## 8. 结论与移交

# APPROVED_WITH_NOTES

unresolved_blockers=0

- **通过性质**: 设计可进入 commit/triage 流程；保留 W-1 + S-1~S-6 为非阻塞备注。
- **W-1 处置建议**：commit 前完成（一条命令补核 + 口径调和，预计 ≤10 分钟）；处置责任建议随 FX-195 收尾归 Coordinator/Architect。
- **S-1~S-5**：文字勘误级，可随 W-1 同批小修或留 triage；**S-6** 建议随 Slice-1 triage 时在任务描述中显式承接（终态归属一句话）。
- **复审链说明**: 本报告为 R0 终态（APPROVED_WITH_NOTES/unresolved_blockers=0）——按 review-record 契约可结束复审链；若 Coordinator 要求先处置 W-1 再入档，属备注处置而非新一轮设计缺陷返工。
- **移交 Coordinator 事项**: ① 结论机录（review-record）；② W-1 是否 commit 前处置的裁决；③ Slice-1/2/3 的 change-triage 时点（0.80.0 建议 + 开放事项四项）。
