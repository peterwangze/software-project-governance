# Release Review · REL-082 · 0.86.0 版本规划发布半面 · R0

> Reviewer: Release Reviewer（独立）· Round: **R0**（首轮）· 日期: 2026-09-19
> 审查对象（主审）: `docs/planning/version-plan-0.86.0.md`（R0 修订版——批 0 阻塞依赖/三维验收/双层回退树）
> 对照输入: `docs/planning/0.86.0-architecture-evolution.md`（设计半面 R1 = APPROVED_WITH_NOTES/0，P3 遗留 N1~N8 非阻塞）· `docs/reviews/review-REL-082-DESIGN-R0.md`/`R1.md` · `docs/planning/0.86.0-arch-consult-round1/round2-external/round3-external.md`
> 先例基线: `docs/release/version-plan-0.85.0.md`（交付 1~6 结构）· `docs/reviews/review-REL-081-RELEASE-R0.md` · review-REL-073-DESIGN-R0:63（M-1~M-8 标准链九步定义）· DEC-217/DEC-221（decision-log L158/L162）
> 审查性质: **M-0/生效确认前规划阶段审查——审查对象是版本规划提案的发布可行性，非发布就绪**（发布执行链 M-1~M-8 未开始；CI/回滚演练/监控等执行面证据不在本轮判定范围，对应规划面可执行性已纳入审查——REL-081 RELEASE-R0 同口径）
> 独立性声明: 本审查只读核验全部引用（7 项独立核验，§4，含 git status 文件面实测），未修改审查对象、产品代码与 `.governance/`；本文件为唯一写入面。

---

## 1. 总结论

# **NEEDS_CHANGE**

**unresolved_blockers = 2**（P0 = 0 · P1 = 2 · P2 = 5 · P3 = 5）

**裁定语义**：两项 P1 均为**发布裁定材料/冻结文件面的事实性缺口**，修复面小且不触碰任何架构裁决——设计半面 R1 的批准与本轮发布可行性方向判断不受威胁。 NEEDS_CHANGE 的理由：

- **R-F1（P1）**：发布半面的首要交付物——semver bump 论证、版本号占用/跳号核查、roadmap 0.86.0 行提案——在计划中**全部缺失**（0.85.0 先例交付 1/交付 6 的同类物）。DEC-221 虽已锁定 tag v0.86.0（版本**选择**已裁），但 bump **依据论证**（M-1 CHANGELOG 与 roadmap 入账锚）在 §6「DEC-221 生效确认（无需再征询）」自动生效路径下**没有后续用户裁定点可补救**——必须在批 0 派发前补入计划。
- **R-F2（P1）**：R0 修订版的核心卖点「文件面冻结」（§2 标题）在其**首行票（FEAT-049，批 0 阻塞依赖）上失实**——`infra/contracts.py` 与 `infra/tests/test_contracts.py` 标注「（新）」，实测两者**已存在**（FEAT-021 `906b209` 交付 L0 最小契约层 466 行 + 87 测试；FIX-303 `4fcc354` 遗留批处置）。FEAT-049 实为**扩展既有契约层**；冻结文件面是批 1「文件面不相交」裁定、change-triage 冲突检测、M-1 Change Inventory 新旧分类的锚点，事实错误必须先更正，且须补「不破坏既有 frozen 形状与 87 测试」约束。

**独立复核后的结论预判（供 Coordinator 修复时引用，不替代复审）**：

- **发布链主体可行**：批 0→批 1→批 2 依赖图为有向无环、否决点齐备；M-1~M-8「照旧」经与九步标准链（review-REL-073-DESIGN-R0:63）对照**功能无缺环**（M-0 由 DEC-221 生效确认承载、M-4 由 DEC-221 预授权覆盖——但见 R-F8 措辞欠账）；文件面实测批 0/批 1 与 0.85.0 在途批 2 零交集。
- **0.86.0 = MINOR 判定预核成立**：新增四类写入器 CLI + 契约冻结 MUST 规则 + write-guard 上线路由 = VERSIONING L12「新增 MUST 规则/B-C 级自动化能力」；未发现 L11「Gate 行为语义变更」触发面（write-guard 为 WARN 姿态上线、无门禁硬化）——论证素材充分，唯欠落纸（R-F1）。
- **版本号占用预核通过**：plan-tracker 版本规划表无 0.86.0 行（grep 全表仅 L346 候选池注记）；tag 最新 v0.84.0、无 0.85.0/0.86.0 tag 占用；0.85.0→0.86.0 顺延不跳号。
- 五项 P2 为**执行前须闭合的发布边界缺口**（双轨时序/注入预算/benchmarks 承载/0.85.0 回退承接/B 分支版本语义），五项 P3 为措辞/承载/落位注记。

---

## 2. Findings（P1 → P3）

### P1（BLOCKING——须修复后 R1 复审）

#### R-F1 · P1 · 发布裁定材料缺失——semver 论证 / 版本占用核查 / roadmap 行提案三件全缺

- **位置**: `docs/planning/version-plan-0.86.0.md` 全文（§1~§6 无对应节）；对照先例 `docs/release/version-plan-0.85.0.md` 交付 1（semver 裁定建议，L25~70）与交付 6（roadmap 行提案，L218~227）。
- **描述**: ①计划通篇无 bump 理由论证——「0.86.0」仅作为既定号出现在标题/L47 tag/DEC-221；0.86.0 载荷（四类写入器 CLI、契约冻结 MUST 规则、write-guard 上线路由、量测协议、benchmarks）明确落入 VERSIONING L12「新增 MUST 规则、新增 B/C 级自动化能力」= MINOR 依据充分，但该论证未落纸，M-1 CHANGELOG「MINOR 依据」行与 roadmap 行「MINOR（…依据…）」格无锚。②版本占用/跳号核查未做（本审查已代验：plan-tracker 无 0.86.0 预留行、无 tag 占用、0.85.0→0.86.0 不跳号——修复时引用即可）。③roadmap 0.86.0 行提案文本缺失——先例（0.85.0 交付 6）由规划提供 6 列行文本、M-0/采纳时 Coordinator 注入；本计划 §6 的采纳路径为「Release 半面审查 → DEC-221 生效确认（无需再征询）」，**自动生效后无用户裁定点**，行文本必须在计划内预置。
- **影响**: 不翻转任何方向结论；但 DEC-221 生效确认若紧随本审查通过发生，批 0 派发即在无裁定材料的状态下启动，M-1 期补造将失去「采纳时点 = 材料齐备」的先例纪律（REL-081 F-1 同类教训：semver 论证必须先于裁定/生效闭合）。
- **建议**: 计划增补一节「版本号裁定（Release 半面）」：①MINOR 依据 = L12 + 载荷逐项定性表（精简版，五~七行）；②L11 处置预核 = 本版无 Gate 硬化面（write-guard WARN 姿态 + 硬门禁上线路由仅「路由」非翻转——如实写明，0.87 升 BLOCK 时再触发 L11 论证）；③占用/跳号核查引用本报告 §4 V5 实测；④roadmap 0.86.0 行提案文本（6 列，对照 0.85.0 行 L288 形态）。

#### R-F2 · P1 · 冻结文件面事实错误——FEAT-049「（新）」标注失实（contracts.py/test_contracts.py 已存在）

- **位置**: version-plan §2 批 0 表 FEAT-049 行文件面列：「`skills/software-project-governance/infra/contracts.py`（新）+ `infra/tests/test_contracts.py`（新）+ fixtures + `benchmarks/closure/protocol.md`（新）」。
- **证据（实测）**: `git log`：contracts.py 由 **FEAT-021 `906b209`**（「最小契约层 L0 落地……Finding（frozen）/CheckResult/CheckSpec（frozen）+ 四端口 Protocol……87 测试」）交付、FIX-303 `4fcc354` 遗留批处置；test_contracts.py 同两 commit 在案；两文件现存（contracts.py 466 行）、工作树对该两文件零未提交改动。设计 R0 P1-1 修复建议列原文即为「contracts.py **扩展**+契约测试+固定 fixture」——R1 修订誊写为「（新）」属失真。
- **影响**: ①文件面冻结是 R0 修订版对 arch P2-c「宣告可并行前冻结」义务的承载，首行票即失实=冻结质量信用受损；②change-triage conflict 检测与 M-1 Change Inventory 按「新文件 vs 修改文件」分类，错误标注将产生错误清单；③**既有 frozen 形状风险未被票面覆盖**——FEAT-021 契约层含 frozen dataclass 与 87 测试，FEAT-049 扩展（状态语义/operation_id/错误码/schema 版本新增契约）MUST 不破坏既有 frozen 形状，该约束在票面/验收入口均未声明。
- **建议**: 文件面改为「`infra/contracts.py`（**扩展既有**——FEAT-021 L0 契约层）+ `infra/tests/test_contracts.py`（扩展既有 87 测试面）+ 契约 fixtures（新）+ `benchmarks/closure/protocol.md`（新）」；FEAT-049 验收入口补一句「既有 frozen 形状与 87 存量契约测试零回归」。

### P2（重要——R1 复审逐条核销：修复或显式豁免理由）

#### R-F3 · P2 · 双轨发布链共享冻结面时序约束缺失（0.85.0 在途批 2 实测活跃）

- **位置**: version-plan L5「本计划不依赖其批 2 结果，M0 契约冻结独立」+ §2 M-1~M-8 照旧行；DEC-221「并行约束：……两轨道文件面已排查独立」。
- **证据（git status 实测，2026-09-19）**: 工作树 **13 个 M 态文件全部属于 0.85.0 批 2.1（FEAT-041 在途）**：`SKILL.md`、`core/version-projections.json`、`infra/sync_entry_projection.py`、`infra/tests/test_entry_projection.py`、`infra/tests/test_verify_workflow.py`、`commands/governance-init.md`、`AGENTS.md`、`adapters/dsh/AGENTS.md.template`、`agent-presets/governance/agent.cordis.yml.template`、e2e 三镜像。0.86.0 面全部为 `??` 未跟踪规划文档。
- **描述**: 「文件面已排查独立」的排查面 = 批 1 四票文件 vs FEAT-041 七锁（design R0 V10）；**未覆盖发布链面**。缺口两点：①0.86.0 的 **M-1 候选打包**（版本 bump 13 files + `release-projection --write`/`sync_entry_projection --write` + CHANGELOG + 三件套）与 0.85.0 的 M-1/M-8 操作**同一批冻结面**——两链 M 步交叠即 RISK-054 同族竞态（0.84.0 两例实测先例），计划未写「0.86.0 M-1 MUST 排他在 0.85.0 M-8 之后」；②M0 契约的状态语义源若取自 behavior-protocol/SKILL.md（design R0 §1.4 概念面注意点），在 0.85.0 批 2.1 正在重构 SKILL.md 的当下，**契约源 revision 未 pin**——design R1 未把该注意点传导进 version-plan。
- **影响**: 批 0/批 1 实际可安全并行（文件面实测零交集）；风险集中在 M-1 交叠与契约源漂移——均为低成本声明即可闭合的时序约束。
- **建议**: 计划补「双轨时序约束」两行：①0.86.0 M-1 候选打包 MUST 于 0.85.0 发布链 M-8 完成后启动（版本投影/CHANGELOG/三件套为共享冻结面）；②FEAT-049 契约源 pin 到 0.85.0 批 2 合并后 revision（或在票面声明契约源文件与 revision 锚）。

#### R-F4 · P2 · 注入预算（0.85.0 翻 hard 后=hard 门禁）交互未分析；「strict 余量 34 tok」未能复现（待验证）

- **位置**: version-plan §1「伴随纪律」/§2 各票文件面（均未提及注入面）；对照 `checks/injection_budget.py` INJECTION_BUDGET_SURFACES 六面（persona、governance-init ×2、AGENTS.md.template、SKILL.md、governance.md——candidate-analysis L139 实测清单）。
- **描述**: 0.85.0 批 2.3 翻 hard 后（大概率先于 0.86.0 发布链发生），standard/strict 注入预算为 **hard FAIL**。最新可溯源数字：EVD-1100/DEC-219「strict 缺口 ~270 tok」（试点门时点，外扩削减面已批）+ EVD-1099「A@90% 安全边际 +421/+250 tok」——**任务书声称的「strict 余量 34 tok（FEAT-041 交付后）」在 EVD-1092/1099/1100 与 DEC-218/219 中均未能复现，本审查标为待验证**（以 2.2 canonical 重测当场值为准）。在此余量极薄的背景下，0.86.0 计划对自身交付物的注入面影响**零分析**：W-4「扫描器禁入语义区」入审查项的落点面、FEAT-042R 对 M7.4 表述的引用面、bootstrap `@bootstrap-version` bump（同长度版本号=零增量，但未见声明）——任何对六注入面的文本新增都无预算闸。
- **影响**: 不阻断批 0/1（纯新 infra 代码文件，不入注入面）；若 SKILL.md 相关伴随纪律落地时无预算意识，0.86.0 M-2 将在 hard 门禁上撞墙且归因困难。
- **建议**: 计划补一句承诺：「0.86.0 全部交付物零注入面文本新增（六面清单锚 injection_budget.py INJECTION_BUDGET_SURFACES）；如不可避免，逐项 token 预算对照 2.2 重测后余量并留 EVD」。

#### R-F5 · P2 · benchmarks/closure 承载三未决——位置归属 / 入库策略 / 发布产物边界

- **位置**: version-plan §2 FEAT-049 文件面「`benchmarks/closure/protocol.md`（新）」（无仓库锚）+ §3 量测协议「工件落 `benchmarks/closure/{protocol.md, cases/, runs/<run-id>/…}`」。
- **证据**: 仓库根与插件内实测均无 `benchmarks/` 目录（新建面无冲突 ✓）；`.gitignore` **无 benchmarks 条目**（实测）——新建即默认全部入库。
- **描述**: ①**位置**：文件面写 `benchmarks/closure/` 但 FEAT-049 其余文件均在 `skills/software-project-governance/infra/` 下——benchmarks 在仓库根还是插件内未定（影响 manifest/check-manifest 口径与发布产物边界）。②**入库策略**：runs/<run-id>/ 含原始 trace（会话数据）——计划要求「敏感脱敏」但未定 runs 入库还是 gitignore 本地保留；round3 §P1-2 只定路径形态与「M2 后作为证据引用导入（保留原始测量时间+导入时间）」，未定 runs 的 git 承载。③**发布语义**：若入库，M-1 三件套/checklist 是否将 runs 计入发布产物、仓库膨胀边界；若不入库，「原始 trace 保留」的可审计性跨机器断裂。
- **建议**: 三选一并写入计划：(a) protocol.md+cases/ 入库、runs/ gitignore+本地保留（EVD 行记 run-id 与摘要路径）；(b) 全部入库+脱敏义务显式化；(c) 全部 gitignore+protocol.md 单独入库。推荐 (a)——与「测量工件 JSON ≠ 业务存储 JSON 化前移」及证据引用导入机制最自洽。

#### R-F6 · P2 · 0.85.0 回退分支承接面未登记（潜在范围扩张源）

- **位置**: version-plan §5 候选池衔接（仅处理 FEAT-043/044/045 去向）；对照 `docs/release/version-plan-0.85.0.md` 回退决策树 R1~R3/选项 c/降级分支 1a/1b。
- **描述**: 0.85.0 的回退出口**多处指向 0.86.0**：R3/选项 c =「翻 hard + P3-3 显式顺延 0.86.0，RISK-057/058 复评窗**改挂 0.86.0**」；降级分支 1b =「①瘦身随翻 hard 一并顺延 0.86.0」；选项 1a =「翻 hard 与 ⑧ entry-skill 顺延 0.86.0」；批 2.4 FEAT-039 预算面族同链顺延。0.86.0 计划对这些潜在承接**零登记**——若 0.85.0 批 2 回退触发，0.86.0 将在 DEC-221 生效确认（范围已冻结的预授权）之后面临计划外范围扩张。
- **影响**: DEC-221 保留边界（范围变更 MUST ask）有兜底、不构成越权风险；但 M-0/生效确认时点的范围信息不完整——用户预授权的「批 1/批 2 执行 → M-1~M-8」与潜在承接范围的关系未呈报。
- **建议**: §5 补一行承接声明：「若 0.85.0 批 2 回退分支触发（翻 hard/瘦身/entry-skill/预算面族顺延），0.86.0 承接范围按 DEC-221 范围变更边界**升请用户裁决后再入批**，不自动并入」。

#### R-F7 · P2 · B-延期分支的版本号语义未明示（缩范围发 0.86.0 vs 顺延 0.87.0 合并）

- **位置**: version-plan §4 触发与升级 R2 行「closure-chain 选 B（迁 0.87.0 确定里程碑）；原子 CLI 照发（批 0/1 独立价值保全）——用户确认」。
- **描述**: R2 触发后剩余范围（批 0 契约+批 1 三写入器+write-guard WARN）以什么版本号发布未写：①缩范围仍发 **v0.86.0**（DEC-221 锁定的 tag；合法 MINOR，但须满足本计划自己的硬规则——CHANGELOG/roadmap 如实缩范围、「部分发布不得标记原计划完整完成」、「其余照发」可隔离证明如何落到 M-8/CHANGELOG 措辞）；②还是整体顺延为 **0.87.0**（此时与 DEC-221「tag v0.86.0」授权字面冲突，须新裁决）。round3 顾问亦未裁决此点（通读原文无版本号分支语义）。M-1 打包在 R2 触发**之后**才发生，故此缺口不阻断批 0/1，但属回退树发布语义的未闭合项。
- **建议**: R2 行补一句：「缩范围发布默认仍为 v0.86.0（DEC-221 tag 授权内），CHANGELOG 显式披露 closure-chain 延期（交付裁决=deferred，迁 0.87.0）；用户如选整体顺延 0.87.0 则 DEC-221 tag 授权失效、须重新裁决」。

### P3（备注——采纳/批 0 派发时顺手处理，不阻塞）

#### R-F8 · P3 · 头部状态行过期 + 采纳门语义两读

- 头部「状态: 待 Design Reviewer 审查 → 用户裁定采纳（M-0 门）」与 §6「→ Release 半面审查 → **DEC-221 生效确认**（设计打磨完成=EVD 留痕，**无需再征询**——用户预授权在案）」矛盾；design R1 §5 亦仍写「后续门: M-0 用户裁定采纳」。实际门语义（DEC-221 生效条件）应以 §6 为准——建议头部状态行刷新 + 将「M-0 门」改写为「DEC-221 生效确认（用户预授权在案，EVD 留痕）」，防两轨执行者读出两个门。同族：M-1~M-8 照旧行建议补注「M-4 用户停点由 DEC-221 预授权承载（预授权不免除 M-2/M-3 门禁）」。

#### R-F9 · P3 · M-2 混沌测试复演的 checklist 承载面未指明

- L47「M-2 门禁实测 MUST 含混沌测试复演」——标准链 M-2 的 gate 表（先例 14~18 项）为固定清单，新增 gate 行须在 release-checklist-0.86.0 起草时显式落位（gate 编号/命令/判定口径）；建议计划预留一句「M-1 起草 checklist 时新增混沌复演 gate 行（引用批 2.2 同一测试入口，候选树复跑）」。执行环境（Windows 宿主 + Popen.kill）BT-9 已覆盖，余下为 checklist 承载动作。

#### R-F10 · P3 · NOT_EVALUABLE（维度①）在发布文档中的呈现规则未写全

- §3 已有核心规则「无可信基线时不得宣传达成」；缺 M-1/M-8 落地措辞规则——CHANGELOG/roadmap/feature-flags 中维度①应写「量测协议已冻结（批 0），历史改善指标 NOT_EVALUABLE（基线建设中），本版不主张达成」一类固定口径；「发布不受阻」语义已由三维表隐含（③机制正确性为独立发布门），建议一句话明示，防 M-8 路线图行「转已发布」时顺手写成达成。no-overclaim 既有纪律可覆盖大部分，此为显式化建议。

#### R-F11 · P3 · 「受管状态变更零人工直写」对账快照的执行点未锚定

- §3 验收方法=「验收窗口起止快照差异 vs 操作记录比对」，但窗口起止未绑定里程碑、比对由谁执行、证据落入哪个工件未写。建议锚定：「快照起点=批 1 首票开工、终点=批 2.3 完成；比对由 M-2 门禁实测执行（新增 gate 行或并入 BT-8 release 对账检查），证据入 checklist gate + EVD」。hook 拦截仅辅助、绕过不计数已明确（诚实边界 ✓）。

#### R-F12 · P3 · version-plan-0.86.0.md 落位 docs/planning/ 偏离先例（docs/release/）

- 既有 8 份 version-plan（0.78.0~0.85.0）均在 `docs/release/`；本件在 `docs/planning/`（与 boundary-audit/consult 件同批）。未发现门禁破损（check-* 以声明面为准）；属可发现性/一致性注记——若「采纳前规划态居 planning、采纳后迁 release」为有意设计，建议在计划头注一句明示，否则 M-1 前迁位对齐先例。

---

## 3. 任务六个审查重点逐面结论

| # | 审查重点 | 结论 | 依据摘要 |
|---|---------|------|---------|
| 1 | 发布链完备性 | **基本完备（R-F8/R-F9 措辞级）** | L47 七要素 vs 九步标准链（REL-073-DESIGN-R0:63）对照：M-1 候选打包/M-2 门禁/M-3 双审查/M-5 transition/M-6 tag+push/M-8 归档显式；M-0 由 §6 DEC-221 生效确认承载、M-4 由 DEC-221 预授权覆盖、M-7 远端对账属 push 后照旧——功能无缺环；缺环仅在措辞（M-4 预授权出处、M-2 混沌 gate 行承载）。0.86.0 特有面：benchmarks 入库未决（R-F5）；closure 工件非 manifest 面（protocol.md 随 FEAT-049 入库、runs 承载待决）。**M-2 含混沌复演的要求本身已显式写入 ✓**（超出 0.85.0 先例的明确化程度） |
| 2 | 版本边界（vs 0.85.0 在途） | **有缺口（R-F3/R-F6/R-F1③）** | 内容依赖独立 ✓（「不依赖其批 2 结果」+ 批 0 M0 契约冻结独立可验证）；文件面批 0/1 vs 0.85.0 批 2 实测零交集 ✓（V2）；但发布链面（版本 bump 13 files/投影/CHANGELOG）排他约束缺失、契约源 revision 未 pin（R-F3）；0.85.0 回退分支顺延承接未登记（R-F6）；semver/占用核查未做（本审查代验通过——V5）。版本号序 0.84.0（已发）→0.85.0（在途）→0.86.0（本计划）顺延不跳号 ✓ |
| 3 | 范围可行性（工作量 vs 周期；strict 余量） | **可行，附约束（R-F4；§4 V3）** | 批 0（1 票）+批 1（3 票并行≤3）+批 2（4 步串行）≈ 8~9 工作单元，量级与 0.84.0（9+4 切片批）相当、单位偏重（DoD 九条负控/契约测试/混沌 harness 均为首做）；既有节奏（0.82.0 21 任务/日、0.84.0 9 任务/日）下单人维护可行，计划已内置否决点（契约冻结/R2/R3）替代死线——无工期承诺与 0.85.0 先例一致，不构成缺陷。strict 余量：34 tok 待验证（V4）；结构性结论不依赖该数字——翻 hard 后任何注入面新增均需预算闸（R-F4） |
| 4 | 验收可执行性（NOT_EVALUABLE 呈现；对账快照执行点） | **主体可裁决，两执行点欠锚（R-F10/R-F11）** | 三维验收判定规则清晰（NOT_EVALUABLE 不得宣传达成=防过陈述的口径已立；机制正确性独立发布门=「发布不受阻」隐含成立）；「受管状态变更零人工直写」三指标+快照对账法+诚实边界完整，唯窗口起止/执行者/证据工件未锚（R-F11）；发布文档措辞规则待补（R-F10） |
| 5 | 回退树发布语义 | **双层结构成立；B 分支版本号语义未闭合（R-F7）** | 第一层交付裁决（A/B/C 互斥）+第二层运行处置（可组合）+状态三分+「其余照发」可隔离证明+「M0/核心写入器/effect-based resume 不得绕过」硬规则——发布语义较 0.85.0 单层树显著增强；R1/R3 升级终点明确（用户裁决/架构裁决）；缺口仅在 R2 缩范围发布的版本号处理（R-F7）与 CHANGELOG 落地措辞 |
| 6 | DEC-221 合规 | **合规（附 R-F8 表达欠账）** | 保留升级边界逐项在计划体现：R1 用户裁决（§4）/R2 用户确认（§4 R2 行）/R3 用户架构裁决（§4）/范围变更不得静默砍（§1）——与 DEC-221「回退树 R1~R3 触发/范围变更/新风险接受 MUST ask」逐点对齐；打磨期义务①②③已兑现（三轮外部顾问原文保全落盘+设计链 R0 NEEDS_CHANGE→R1 APPROVED_WITH_NOTES/0 如实+轮次留痕入档）；授权范围（批 1/批 2→M-1~M-8→tag v0.86.0→push→归档）与计划链一致；「预授权不免除门禁/审查照常」语义在计划中经「M-2 门禁实测 MUST 含混沌复演+三维验收」延续。BT-1~7 入 risk-log「随规划采纳」为生效确认时点动作，非缺口 |

---

## 4. 独立核验表（7 项）

| # | 核验项 | 核验方式 | 结果 |
|---|--------|---------|------|
| V1 | M-1~M-8 标准链九步定义 vs 计划 L47「照旧」七要素 | Read review-REL-073-DESIGN-R0:63 + version-plan-0.85.0 交付 3 + DEC-197/DEC-221 | ✅ 功能无缺环；M-0/M-4 承载改由 DEC-221，措辞欠账记 R-F8 |
| V2 | 文件面冲突实测（0.85.0 在途 vs 0.86.0 申明面） | `git status --porcelain` + `git log -- <files>` + Test-Path 四票文件 | ⚠️ 13 M 态文件全属 0.85.0 批 2.1（SKILL.md/version-projections.json/sync_entry_projection.py 等）——共享冻结面活跃 → R-F3；task_row_update/governance_store/baseline_metadata 不存在 ✓；**contracts.py/test_contracts.py 已存在**（FEAT-021 `906b209`/FIX-303 `4fcc354`）→ R-F2 |
| V3 | 工作量对照既有版本史 | Read plan-tracker 归档完成行（0.82.0=21 任务 09-16→09-17 发布；0.83.0=3 收口；0.84.0=9+4 切片；0.85.0 批 1 六票单日） | ✅ 0.86.0 ≈8~9 单元，量级可行；首做工件（混沌/量测协议/契约冻结）无工时先例——以批内否决点承接，建议不设死线 |
| V4 | 「strict 余量 34 tok（FEAT-041 交付后）」 | Grep EVD-1092/1099/1100 + DEC-218/219 + 0.85.0-2.0-injection-measurement.md | ❌ **未能复现**——最新可溯源：EVD-1092 当前树 strict 10,918（ADVISORY，超 4,918）、EVD-1099 A@90% 边际 +250、EVD-1100/DEC-219 试点门 strict 缺口 ~270（外扩削减面已批）；FEAT-041 在途未交付（plan-tracker L98 🔄）。**标待验证**；结构性风险（R-F4）不依赖该数字 |
| V5 | 0.86.0 版本号占用与跳号 | Grep plan-tracker 版本规划全表 + `git tag --list v0.8*` | ✅ 无 0.86.0 roadmap 行/预留占用（仅 L346 候选池注记）；tag 至 v0.84.0；0.85.0 在途未 tag → 顺延不跳号（供 R-F1 修复引用） |
| V6 | CHANGELOG 承载现态 | Read project/CHANGELOG.md 头部 | ✅ 最新段 0.84.0；0.85.0 段未入（其 M-1 在途）→ 0.86.0 段顺序承载无冲突；0.86.0 计划未提 CHANGELOG 属「照旧」吸纳（M-1 先例固定承载面），附 R-F7 的 B 分支措辞义务 |
| V7 | benchmarks/ 目录与 .gitignore 承载 | Test-Path（仓库根+插件内）+ Read .gitignore | ✅ 目录不存在（新建面干净）；.gitignore 无 benchmarks 条目 → 新建即默认入库，入库策略未决 → R-F5 |

---

## 5. 边缘问题（不计 finding，交 Coordinator 参考）

1. **「34 tok」数字溯源建议**：若该数字来自 FEAT-041 试点后某次未入 EVD 的实测，须补 EVD 行方可作为规划输入（本仓纪律：无 provenance 数字不得进计划——REL-082 设计半面 P1-2 同类教训）；更稳妥做法是 R-F4 修复直接采用「以 2.2 canonical 重测当场值为准」的动态口径，回避静态余量数字。
2. **混沌测试的 push 边界安全**：三边界含「push 凭据失败/push 超时」——设计已承诺凭据零记录+注入接口仅内部测试入口；M-2 复演在候选树执行时，checklist 应标注「混沌测试不产生真实远端副作用」（mock/隔离 remote），防 M-2 安静窗内误触真实 push。
3. **FEAT-049 关闭证据四项**中「哪些票被阻塞」= 批 1 三票+批 2.0，依赖图已显式——无缺口；批 0 验收入口「契约测试通过=冻结 revision」建议同时约定 revision 的记录位置（EVD 或 fixtures 内 manifest），供批 2.0 复跑对照。
4. **e2e 镜像面**：0.86.0 新 infra 文件是否进入 `project/e2e-test-project/` 镜像清单由 check-manifest 当场值裁决（M-1 注意项，本审查未核 manifest 清单，不预判）。
5. **DEC-221 生效确认时序**：本报告 NEEDS_CHANGE 期间 DEC-221 生效条件（设计打磨完成）未达成——R1 复审通过前不应有批 0 派发/生效确认 EVD 行；本报告 §1 预判仅供修复引用。

---

## 6. 硬门槛自检（本审查任务）

| 门槛项 | 判定 |
|--------|------|
| 结论四态之一 + unresolved_blockers 计数显式 | ✅ **NEEDS_CHANGE**（unresolved_blockers = 2：R-F1/R-F2） |
| P0-P3 findings 分级齐全 | ✅ P0=0 / P1=2 / P2=5 / P3=5（§2） |
| 独立核验 1~3 项（含 0.85.0 发布链对照/git status 文件面/工作量对照版本史） | ✅ 7 项（§4：V1 链对照 / V2 git status 实测 / V3 版本史对照 / V4 预算数字溯源 / V5 版本占用 / V6 CHANGELOG / V7 benchmarks 承载） |
| 审查报告落盘 docs/reviews/（唯一写入目录）；不修改审查对象/产品代码/.governance/ | ✅ 本文件；审查对象零改动、`.governance/` 零改动、产品代码零改动 |
| 事实依据红线（未实测不写通过） | ✅ 34 tok 标待验证（V4）；发布就绪执行面（CI/演练/监控）显式声明不在本轮范围；「照旧」链的 M-2/M-4 承载语义按文档与 DEC 原文核对，未虚构执行证据 |

---

*审查人：Release Reviewer｜任务：REL-082（0.86.0 版本规划发布半面独立审查）｜Round: R0｜复审指引：R1 MUST 逐条比对 R-F1~R-F12 标注「已修复/未修复/新引入」。R-F1 验证点 = 计划出现版本号裁定节（MINOR 依据 + L11 无触发面声明 + 占用/跳号核查〔可引本报告 V5〕+ roadmap 0.86.0 行提案文本）；R-F2 验证点 = FEAT-049 文件面改「扩展既有（FEAT-021 L0 契约层）」+ frozen 形状/87 测试零回归约束入验收入口。R-F3~R-F7 逐项处置（修复或显式豁免理由）为 R1 通过前置；P3（R-F8~R-F12）可随生效确认/批 0 派发顺手关闭。修复范围不涉及架构裁决——设计半面 R1 结论继续有效。*
