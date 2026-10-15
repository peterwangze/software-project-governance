# FIX-445 — Independent Design Review R11（DEC-344 限定 prose/mention 来源绑定接口设计）【最终完整版 v2——并入 Coordinator 追加核对点 W2/W3，替换前版】

```json
{"verdict":"BLOCKED","round":11,"unresolved_blockers":3,"review_scope":"prose_mention_source_binding_interface_design_static","implementation_authorized":false}
```

**持久化路径**：`docs/reviews/review-FIX-445-DESIGN-R11.md`（Coordinator 原样落盘 + review-record 机录：`--task FIX-445 --round 11 --result BLOCKED --report docs/reviews/review-FIX-445-DESIGN-R11.md --reviewer DesignReviewerR11`）。本 v2 为最终版：新增 W2（registry 自身路径纪律矛盾）与 W3（registry/载体验证资源上界缺失），解除条件增补 C-W2/C-W3；verdict、blocker 数与全部前版结论不变。

## 0. 绑定、独立性与输入

- **审查对象**：`docs/design/FIX-445-mention-interface-R11.md`（448 行全文实读）。SHA256 `5eaf97d0db641ad50340e9ef7c23ac5a3e2e30f4942121201860a01eead32f0f` 系派发与 `incidents/FIX-445-R11-artifact-check.json:7` 双源一致供应，本 Reviewer 未独立重测 hash（只读约束，如实标注）。
- **审查方**：DesignReviewerR11，fresh 非作者，只读。未参与 R11 设计编写，非 Architect/Analyst/Coordinator。human external membership / DRI 资格未知——不发明人类评审，不捏造外部资格（沿 R10:28、R10 补核 N3 边界）。
- **产品授权**：`implementation_authorized=false`——即使设计被批准也无产品授权；本结论为 BLOCKED，更无。
- **工具面**：read×23 + glob×1，零 shell/零执行/零探针/零实验/零产品与治理写/零子 agent/零用户交互。未读热 plan-tracker/evidence-log/execution-packets（热事实=Coordinator 单源供应）。日期 2026-10-13 沿 Coordinator 供应。

**强制全文输入清单（全部实际完整读取，无一缺席，不以摘要替代）**：
1. `agents/design-reviewer.md`（102 行）；2. `skills/design-review/SKILL.md`（81 行）；3. `skills/tech-review/SKILL.md`（196 行）；4. `docs/design/FIX-445-mention-interface-R11.md`（448 行）；5. `docs/reviews/review-FIX-445-DESIGN-R10.md`（132 行）；6. `docs/reviews/supplement-FIX-445-DESIGN-R10-evidence.md`（105 行）；7. `docs/reviews/supplement-FIX-445-DESIGN-R10-calibration.md`（44 行）；8. `docs/design/FIX-445-mention-contract-R10.md`（135 行）；9. `.governance/incidents/FIX-445-R10-source-extract.md`（27 行，完整 EVD-1536/1587/1588 原行——三行完整性独立核对，与 R11 附录 A 逐字一致）；10. `.governance/reports/FIX-445-R10-contract-decision.md`（81 行）；11. `.governance/reports/FIX-445-health-resume-20261013.md`（84 行）；12. `docs/requirements/FIX-445-health-resume-clarification-20261013.md`（295 行）；13. `docs/reviews/review-FIX-445-CODE-R6.md`（100 行）；14. `docs/design/FIX-445-source-verification.md`（304 行，七类映射）；15. `docs/design/FIX-445-source-verification-R3.md`（61 行）；16. `docs/design/FIX-445-source-verification-R5.md`（49 行）；17. `docs/reviews/review-FIX-445-DESIGN-R9.md`（50 行）；18. `docs/reviews/supplement-FIX-445-DESIGN-R9-protocol.md`（75 行）；19. `.governance/incidents/FIX-445-DEC336-contract.py`（24 行，只读未执行）；20. `.governance/reports/FIX-445-R4-escalation.md`（22 行）；21. `skills/software-project-governance/infra/hooks/commit-msg`（1284 行全文）；22. `skills/software-project-governance/infra/tests/test_hooks.py`（1480 行全文）。
补充输入（本轮）：23. `.governance/incidents/FIX-445-R11-artifact-check.json`（73 行，静态工件核对，`product_code_executed:false`）。

**DEC-344 权威链**：授权事实来自 Coordinator 本会话 actual ask 机录（`reports/FIX-445-health-resume-20261013.md:50-57` + 澄清报告 §8.4/§9B）——限定 prose/mention 来源绑定接口**设计文档 + 独立 R11 审查**（账本 max10+1 不重置），零产品写入。R10 裁决报告 :80 的 DEC-342「保持原门并暂停」为历史时点事实，已被 DEC-344 取代为当前状态——两者不矛盾，本报告按 DEC-344 当前授权审查。

## 1. 结论摘要

设计的**授权边界诚实性、空态等价论证、来源资格调查（scoped NOT_ESTABLISHED）、包含困境证明（规则 P/T 排除）**经独立复核全部成立。但发现 **3 项 BLOCKING 设计缺陷**（B1 W1 验收例内部矛盾、B2 迁移态 replay 安全缺口、B3 raw-slice 偏移单位契约错误）与 **3 项 WARNING**（W1 存在预检故障语义欠规格、W2 registry 自身路径纪律矛盾、W3 registry/载体资源上界缺失），round 11 已超复审 fuse（max10+1）→ **BLOCKED 终态，零自动 R12**，升级用户裁决。产品侧一切不变：FIX-445 blocked、64 tests/92.738s/1FAIL、Code R6 BLOCKED/3（B1 live/B2 batch-any/B3 D20）、完整四任务源门、B3 保护、CPU27.8/CLI36/434339/32MiB/1500 全部保持。

## 2. Findings

### B1（BLOCKING）§8.4:349 去重锚定例与 §6.8 规范算法自相矛盾——W1 验收例不可用

§6.8 规范（:251-256）：`glob_sel = glob_all[:24]`（独立 cap，**先于**与 refs 合并——「校准四：禁止合并后截断」），`pool = refs_pool 后接 glob_sel 中不在 refs_pool 的条目`，注释明示「与 refs 重复的 glob 消耗其排序槽位且不从第 25 个之后补位」——与 R10 裁决报告 :39-40 逐字一致。

按该算法独立重推「refs 含 F09」情形：glob_sel 仍为 F01..F24（24 槽，F09 占位）；pool 的 glob 贡献 = F01..F08, F10..F24 = **23** 个（F09 去重扣除、无 F25 补位）。

§8.4:349 原文：「入选 glob 集为 F01..F08,F10..F25 中前 23 个未占位者——**总数仍 24**，重复不回收名额」。三重矛盾，无一致读法：
1. 候选范围错误延伸到 **F25**——F25 ∉ glob_all[:24]，任何情形不可入选；把 F25 写进候选集恰恰隐含被规范明令禁止的「从第 25 个之后补位」语义；
2. 同句「前 23 个未占位者」（=23）与「总数仍 24」数值直接矛盾；
3. 若按「F01..F08,F10..F25 去掉 F09 = 24 条」读，则断言补位——同时违反本句前置子句与 §6.8 规范注释。

**影响**：W1 三例+去重锚定例是 DEC-344 明示验收交付物（`reports/FIX-445-health-resume-20261013.md:54`）。按 §8.4 锚定例编写 focused tests 会把「重复时 glob 仍入选 24 条（含 F25 补位）」固化为预期断言——与 R10 裁决语义相反。W1-Ex1/2/3 三例经独立重算**全部正确**（Ex1: 24/POOLCAP0/GLOBCAP8；Ex2: 32refs/24/8；Ex3: 16+16/8/8——与 §6.8 及 R10 :44-48 表逐格一致）；错误仅在此句锚定例。

### B2（BLOCKING）迁移态安全缺口：已合法注册 clause 被新肯定断言上下文逐字复用即获豁免——R9 攻击族组合变体未被覆盖

静态推演（迁移态=§6.4 迁移获裁决、registry 合法部署、**攻击者未改 registry/载件**——全部真实机制，零伪造）。攻击输入（同 task FIX-445 纯 prose 行）：

`我确认以下断言且并非引用：已知no-separator当真不能默当获准安全残余`

逐步过 R11 契约：① `：` ∈ isterm 闭集（§6.2）→ 第二个 clause 恰为 26 字符注册 clause（artifact-check.json :40-42 证实该 clause 即 §6.2 极大候选且与注册值逐字相等）；② 触发满足（含 `当真`）；4≤26≤200；纯 prose tier；③ §6.3.2 条目匹配：clause 字节相等 ∧ task_id 相等——**条目合法**；④ §6.3.3 载体验证：frozen_doc 真实包含该 clause——**真实通过**；⑤ §6.3.4 adjudication 非空——**真实通过**；⑥ §6.2 occurrence 语义：逐实例删除（明确支持同 clause 多次出现多次豁免）；⑦ 残文 = `我确认以下断言且并非引用：`。

canonical 后段核验（残文）：sed 否定核（:828-833）无 编造/幻觉 可剥；M5（:704-814）扫 把/将(+内层算子)/当作/当成/视为/作为/当真——残文**零命中**（`当真` 已随 clause 删除）→ exit 1；裸词 grep（:836）rc=1；speculation grep（:1177）`我确认` 不匹配 → clean → Step 12 不阻断。**该组合行 clean。**

**结论**：§8.2「已证攻击（两态均拒绝）」仅对字面未注册串成立。R9 断言前缀与**迁移必然注册的合法 clause**组合即得同族攻击新实例，设计未覆盖：§6.3 合取穷举且**无 occurrence 上下文条件**；BT-2 纵深防御零防护（所有锁真实满足，无伪造）；§6.4(b) 对抗复核只约束「注册什么」（攻击串否决），不覆盖合法串复用，且注册时一次复核无法约束后续无限 replay；BT-6 只覆盖字节变形/跨任务/边界外附加，不覆盖逐字复用；§5 包含困境的 registry 解法把同一结构性弱点上移一层——**裁决边界约束了谁可注册，未约束已注册字节可被复用多少次**。canonical 哲学锚点：`test_hooks.py:800-806` `test_same_literal_second_instance_unverified_blocks`（「a verified literal span does not clear the SAME bytes appearing again in prose」）——现行引擎 per-instance 纪律明确要求同字节新上下文必须 BLOCK；R11 M 腿迁移态违反该纪律。§0 声称迁移「安全代价在 6.4/13 节具体展开」——replay 代价**未展开**，§8.2 迁移列全称声明**过度**，违反设计自身标准 2 与标准 8。

**边界（如实）**：当前授权态（registry 缺席）该行仍 BLOCK（M5 窗 `已知no-separator` 残留拒，与 R10 一致）；空态等价结论不受影响。攻击实现需同 task 新 EVD 行承载组合形——本工作流中 EVD 行经 Coordinator 机器路径追加，实际信道=失当追加或对 evidence-log.md 直接写（后者=CH-1 界）；但与其它 CH-1 情形不同，此处**无需伪造任何工件**，仅凭普通证据行撰写即可。

### B3（BLOCKING）§6.5 raw-slice 偏移单位契约错误：「字节偏移」与 canonical 引擎码点偏移体系不兼容

§6.5：「prose tier：clause 的 raw 偏移即行内**字节**偏移」。canonical 引擎全部在 `str`（码点）索引上运作：`regions()`(:445-473)、`top_string_fields`/dmap(:239-332)、`dels` 合并删除(:637-655)。artifact-check 双度量实证：EVD-1587 clause 字符区间 428..454（26 chars）vs UTF-8 字节区间 828..882（54 bytes）；1536 为 1148..1158 vs 1866..1888；1588 为 572..600 vs 954..1020——两套单位在真实行上分歧数百。§6.5 要求 M 删除区间与 record tier `dels`「合并后统一走既有排序/重叠/计数校验」——按字面实现字节偏移并与码点 dels 合并 → 切片错位 → `deletion-overlap`/`mcount-mismatch` ToolFault（**fail-closed 方向，无逃逸**）或不可实现。DEC-344 明示交付元素含「raw-slice 映射」——规范文本单位错误=契约缺陷。正确表述：clause 偏移是原始行 `str` 的**码点索引**（与 regions/dmap/dels 同轴）；「字节」仅适用于相等性比较语义（str 相等⇔规范 UTF-8 字节相等）。

### W1（WARNING）§6.7(5) 存在预检与 §6.6 registry-read 故障语义交互欠规格

分情形推演：① 悬空符号链接：bash `-f` 跟随链接 → false → 纯 prose 臂不 spawn、M 腿惰性 → 静默等价空态；② 路径为目录：同 ①；③ TOCTOU（预检后 open 前被删）：`FileNotFoundError` 属 OSError——§6.6 映射为 `registry-read` ToolFault，§6.3.1 却规定「缺席=M 腿惰性」——未规定判别，bash/python 侧缺席判定可分叉；④ 权限不可读：`-f` true → spawn → PermissionError → ToolFault → BLOCK ✓；⑤ 编码错误 → ToolFault ✓。所有分叉解收敛于零豁免（受污染 prose 仍被 M5 拒）——**无假 PASS 通道**；但 BT-5「权威面损坏不得静默降级」对纯 prose 臂**过度声明**（①②③恰是静默降级）。

### W2（WARNING）【新增——Coordinator 追加核对点 2】§6.4 registry 自身路径「与 6.3.3 同纪律」自相矛盾：三前缀闭集排除权威件自身位置

§6.4:211：「位置：`.governance/mention-registry.json`（…其路径检查纪律与 6.3.3 相同）」。§6.3.3:185 的纪律=**闭环三前缀闭集**（`docs/reviews/`、`.governance/incidents/`、`.governance/reports/` 之内，拒绝绝对路径/`..`/evidence-log.md，检查先于 open）+ realpath 落仓内。`.governance/mention-registry.json` 直接位于 `.governance/` 根，**不在三前缀之任一内**——按字面应用，权威件自身路径被自己的加载纪律拒绝。且 §6.6 故障表无「registry 自身路径非法」的故障码归属（registry-schema 仅覆盖条目 `carrier_path` 形非法）。两向解决均 fail-closed：字面自拒→registry 永久非法→全 BLOCK（可用性崩）；或实现者即兴「视为缺席」→静默空态（违反 fail-closed 意图但零豁免）。**定性 WARNING 而非 BLOCKING 的理由**：规范主句（固定常量路径）本身无歧义、registry 路径非数据驱动（无攻击者输入面）、无验收材料传播此错误（异于 B1）、两向均零逃逸。修订必备：明示**固定 authority path 例外**——registry 自身按常量路径加载，仅施加绝对/`..`/realpath 仓内检查；三前缀闭集检查只作用于条目 `carrier_path`。

### W3（WARNING）【新增——Coordinator 追加核对点 1】registry 与载体验证面无资源上界：原门 32MiB/1500 无设计措施，W1 cap 不约束 M6c IO 面

§6.4 schema（version+entries[]）**无 entries 数量上限、无文件字节上限**；§6.6 仅界定了单条 clause 4..200 字符与 `carrier_path` 形合法。§6.4 明示 registry「不占 W1 语料名额——权威单件，独立于 refs/glob 分配」——即 W1 的 glob24/总池32 cap **不约束**该新读面。更关键：§6.3.3 frozen_doc 载体为**条目自声明路径**（三前缀内任意文件），并非限定于 W1 corpus 池内——M6c 载体验证的 IO 面理论上为 O(entries × carrier 读取/解析成本)，而 §7 流程图又写「④ W1 corpus…供 ②③ 凭据/载体验证」——两种读法（直接验条目路径 vs 仅验 corpus 池内文件）契约歧义：(a) 直接验=无界 IO；(b) corpus-only=frozen_doc 载体若不在当前池内则不可验（可用性缺口，保守向）。§11 NFR 性能行仅有「registry 单件一次读…CPU27.8/CLI36/434339/32MiB/1500 不重测不放宽；实现后必须复测原门」——**无任何设计措施保证**新面不侵蚀原门（32MiB 内存界/1500 资源门），只承诺事后复测。**定性 WARNING 而非 BLOCKING 的理由**：增长信道=Coordinator-only 机器写入权威（治理受控，非威胁模型内攻击者直接写）、可达 fail-closed（超界→registry-schema ToolFault）、设计已强制实现后原门复测。修订必备：schema 契约加入显式界（max entries N、max registry 字节 B、单条 carrier 字节界、每 spawn 验证预算）+ 超界故障语义（fail-closed）+ 消除 §6.3.3/§7 的载体来源歧义。

## 3. Coordinator 六项观察的独立裁决汇总

| # | 观察 | 独立复核结论 | 定级 |
|---|---|---|---|
| 1 | §8.4:349 重复 glob 例与 §6.8 矛盾 | **成立**（三重矛盾，见 B1；正确值=23 条 F01..F08,F10..F24，无 F25 补位） | BLOCKING |
| 2 | 同 task 合法注册 clause 被新断言上下文复用仍删 | **成立**（逐步过 §6.2/6.3/6.5 + canonical :828-839/:704-814/:1177，残文 clean；canonical :800-806 纪律反证） | BLOCKING |
| 3 | §6.5 码点/字节混淆 | **成立**（artifact-check 双区间实证；fail-closed 方向但契约错） | BLOCKING |
| 4 | 存在预检 vs registry-read 故障交互 | **成立但保守方向**（悬空链接/目录/TOCTOU 静默空态；无假 PASS） | WARNING（W1） |
| 5 | registry 资源上界（entries/字节/内存界） | **成立**（schema 无界；W1 cap 不约束 M6c IO 面，§6.3.3/§7 载体来源歧义；原门仅事后复测承诺） | WARNING（W3） |
| 6 | §6.4「与 6.3.3 同纪律」排除自身路径 | **成立**（三前缀闭集不含 `.governance/` 根；§6.6 无对应故障码；两向解决均 fail-closed） | WARNING（W2） |

## 4. 六维评估与硬门槛

| 维度 | 结论 |
|---|---|
| 完整性/结构 | 目标/预定义标准（§1 先于 §9）/替代 6 案/风险/ADR §14 字段全（日期=Coordinator 供应，如实标注）。**通过**（但 §8.4 锚定例事实错误→B1；registry 契约缺上界→W3） |
| 架构/依赖 | §6.1 M6a→M6b→M6c→M3 无环；Guard G/T2/M5/R3 零改动与 canonical 一致；registry 加载路径纪律文本自相矛盾（W2）。**通过（附 W2）** |
| 接口契约 | 语法/occurrence/registry schema/故障码表大体完备；**契约级缺陷**：§6.5 偏移单位（B3）、§6.3 无 occurrence 上下文条件（B2）、§6.4 自身路径纪律（W2）、资源上界缺席（W3）。**不通过** |
| 安全与授权边界 | 空态等价成立（:823-827 一手核对：纯 prose 无 registry → residual=input 零 spawn）；tier 分离、任务域封闭、检查先于 open、CH-1 边界如实；**迁移态存在未披露 replay 面（B2）**。**不通过** |
| NFR/演进 | §11 映射大体如实；BT-5 对预检洞过度声明（W1）；性能门「不重测不放宽+实现后复测」正确但新面无界（W3）。**有条件通过** |
| 独立评审 | 本报告 fresh 非作者；人类外部资格未知如实。**通过（边界内）** |

硬门槛：备选 **6≥2** ✓；蓝军 **6≥3**（BT-1..6）数量过但覆盖漏 B2 场景；ADR 字段 ✓；无循环依赖 ✓；接口契约与安全一致性门 **FAIL（B1/B2/B3）**。

## 5. 独立蓝军挑战（≥3，标准格式；视角切换：从「设计为何对」→「设计最可能在哪里失败」）

被挑战的隐含假设：H1=裁决边界足以约束豁免面；H2=验收例与规范算法自动一致；H3=偏移单位是实现细节；H4=权威单件天然有界；H5=规范引用（「同纪律」）天然自洽。

| # | 攻击向量 | 影响评估 | 当前缓解 | 残余风险 | 建议增强 |
|---|---|---|---|---|---|
| BR-1（攻击者） | 断言前缀+合法注册 clause 组合（B2） | 迁移态新断言 false-clean，破坏 Step-12 事实门 | registry 裁决边界（约束注册不约束复用） | **高——未缓解** | occurrence 级绑定（EVD 行/冻结位点锚定）或显式裁决 replay 边界+组合攻击矩阵行 |
| BR-2（攻击者/维护者） | 按 §8.4 锚定例编写 focused tests（B1） | 永久测试固化「补位」语义，违背 R10 裁决 | §6.8 规范算法本身无歧义 | 中 | 修锚定例；测试同时覆盖去重与不补位两断言 |
| BR-3（维护者） | 按字面实现「字节偏移」（B3） | CJK 行删除错位→ToolFault 噪音/不可实现 | 既有 deletion-overlap/mcount 校验 fail-closed | 中（无逃逸） | 规定码点索引；以 artifact-check 双区间做钉死测试 |
| BR-4（愤怒用户） | registry 误部署（悬空链接/目录/竞态）静默空态（W1） | 「已迁移」假象下合法行仍拒，BT-5 承诺落空 | 零豁免方向保守 | 低 | 规定 FileNotFoundError 判别+预检读探+部署自检 |
| BR-5（攻击者/规模） | registry 无界增长或条目指向大载体（W3） | 每 spawn 全量读+逐条载体验证 → 内存/IO 侵蚀 32MiB/1500 原门；W1 cap 不约束此面 | 写权威治理受控+实现后原门复测承诺 | 中 | schema 显式界（entries/字节/carrier/预算）+超界 fail-closed |
| BR-6（维护者） | 按「与 6.3.3 同纪律」字面实现 registry 加载（W2） | 权威件自拒→全 BLOCK，或即兴「视为缺席」→静默空态 | 固定常量路径本身无歧义 | 低（两向零逃逸） | 明示固定 authority path 例外条款 |

（另：incidents 人口增长 54→59→65+≥2 目录——GLOBCAP 实丢 ≥37→≥41，可用性向，固定 fixture 纪律已覆盖，沿 §8.4 声明不升级。）

## 6. 旧发现对照（已修/未修/新引入）

| 前链项 | R11 判定 |
|---|---|
| R10 B1（4 源文件未注入） | **已修**——本轮全部强制输入实际全文在手 |
| R10 W1（corpus 分配歧义） | **规范面已修**（§6.8 与 R10 裁决 :36-50 一致）；**新引入** §8.4:349 锚定例矛盾（B1） |
| R9 B1（语法≠提及范围） | 未注册串面**已闭合**（registry 裁决分量）；**新引入**迁移态组合变体缺口（B2）——同族攻击换载体存活 |
| CODE-R6 B1/B2/B3 | **未修且不归本设计**（正确：§11/§13.4 明示；canonical `:1198` batch-any 一手确认仍在） |
| 历史 R0 C1-C7 / R3 prefix / R5 GuardG | §3 现状描述与 canonical 逐符号核对**无失实**（:339/:381-428/:427-428/:478-497/:704-814/:817-839 锚点全命中） |
| 健康 16 issues/exit1、Check 2/8 风险盲点 | 界外保持未解，设计未触碰（正确） |

## 7. NFR 映射（摘要）

| 维度 | 措施核验 | 遗留 |
|---|---|---|
| 安全 | 全腿 fail-closed（§6.6 表方向全 BLOCK ✓）；闭环前缀+检查先于 open（沿 :508-519 ✓）；tier 分离护 Guard G；任务域封闭 | 迁移态 replay 面（B2）；非密码学承诺如实 |
| 可靠性 | registry 三级 ToolFault+载体内容失败行级保守（与 :991-1015 canonical 二分一致）；诊断分列可观测 | 预检静默降级（W1）；自身路径纪律矛盾（W2） |
| 性能 | 单件一次读、4..200 线性界、纯 prose 零 spawn（CH-7）；原门不重测不放宽（正确） | **新面无界**（W3）：entries/字节/carrier IO 无 cap，32MiB/1500 无设计措施仅事后复测；实现后必须复测原门 |
| 可用性 | 空态合法行仍拒（如实=R10 CH2 High 保持）；迁移态方可用 | W1 预检洞；W2 字面自拒变体 |
| 可维护性/可测试性 | 单 schema+闭语法+「不再加标记」纪律；每故障码一红一绿；W1 fixture 具体集合 | B1 锚定例必须先修否则测试面被污染 |

## 8. 熔断与解除条件（BLOCKED 必须具体可解除）

Round 11 = 账本 max10+1（DEC-344 不重置）。存在需修改的阻断 → **BLOCKED，零自动 R12**。解除条件（全部满足后须经用户新裁决授权修订设计 + 新独立审查，本 Reviewer 不代行）：
1. **C-B1**：修订 §8.4:349 锚定例至与 §6.8 自洽（正确期望=「F01..F08,F10..F24 共 23 条，重复槽位不回收、无 F25 补位」），或若设计意图确为「总数24」则须改 §6.8 规范并回到用户裁决（与 R10 :40 语义冲突，须明示）。
2. **C-B2**：迁移态契约闭合 replay 面，二选一并入设计：(a) occurrence 级绑定机制（registry 条目锚定具体 EVD 行/冻结出现位点，hook 验证出现位置而非仅字节）；或 (b) 将 replay 边界作为显式安全代价逐字披露、列为 §6.4 迁移裁决必审项（组合攻击行入 §8.2/8.3 矩阵并给出裁决后期望）——**闭合前，§8.2「迁移态全部攻击仍拒」全称声明必须撤回或限定**。
3. **C-B3**：修正 §6.5 偏移语义为码点索引（与 regions/dmap/dels 同轴），字节语义仅限相等性比较；以 artifact-check 双区间行为测试锚。
4. **C-W1**：规定 load_registry 对 FileNotFoundError 的判别（缺席 vs 故障）与 bash 侧存在预检语义（悬空链接/目录/竞态），使 BT-5 声明与实际行为一致。
5. **C-W2**：明示固定 authority path 例外——registry 自身按常量路径加载，仅施加绝对/`..`/realpath 仓内检查；三前缀闭集仅作用于条目 `carrier_path`；§6.6 补「registry 自身路径非法」的故障码归属（或声明该情形不可达）。
6. **C-W3**：schema 契约加入显式资源界（max entries、max registry 字节、单条 carrier 字节界、每 spawn 验证预算）+ 超界 fail-closed 故障语义；消除 §6.3.3（条目自声明载体路径）与 §7（corpus 供载体验证）之间的载体来源歧义；实现票必须含 32MiB/1500 原门复测与界值实测。

## 9. 不变项与非授权声明

产品两文件零改动（blob a327f812…/0e8aff2f… 继承 R6 绑定，本轮未重测如实）；FIX-445 保持 blocked；inherited 64 tests/92.738s/1FAIL、Code R6 BLOCKED/3、W1 产品面、完整四任务源（非零/hashbytes/latest/zero skipped/RC0）、B3 五 env 保护、性能资源门（CPU27.8/CLI36/434339/32MiB/1500）全部保持失败/未解，本审查不使其任何一项通过或减轻。本 BLOCKED 不否定「限定设计+独立审查」授权边界——边界内诚实性良好；阻断仅针对上述契约缺陷。无自动 R12、无实施授权、无验收放宽、无风险接受、无新权威自授；迁移（Mig-A/B）维持未授权未实施，本报告不催促。当前 full 健康 16 issues/exit1 与 Check 2/8 盲点不因本报告变化。

（完整正文约 5400 中文字。建议 Coordinator 将本 v2 作为唯一最终版原样持久化至 `docs/reviews/review-FIX-445-DESIGN-R11.md`（弃用前版），按上方 JSON 机录 review-record，随后释放锁。）
