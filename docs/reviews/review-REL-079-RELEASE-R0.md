# 发布审查报告 — REL-079（0.83.0 候选就绪状态）RELEASE 半面 R0

| 项 | 值 |
|---|---|
| Task ID | REL-079（0.83.0——治理健康收口 + 架构债批；M-3 RELEASE 半面） |
| 审查轮次 | R0（首轮；前轮引用：无） |
| 审查角色 | Release Reviewer（只读；本报告为唯一写入文件） |
| 审查日期 | 2026-09-17 |
| 审查对象 | `docs/release/release-checklist-0.83.0.md` / `feature-flags-0.83.0.md` / `rollback-plan-0.83.0.md`；`project/CHANGELOG.md` [0.83.0] 段；对照模板 0.82.0 三件套；`.governance/plan-tracker.md`（0.83.0 路线图行/任务行/总览）；`.governance/risk-log.md`（RISK-036/039/046/050/051）；`.governance/decision-log.md`（DEC-198~201） |
| 审查方法 | 纯 Read/Grep/Glob 只读核对——**未执行任何命令**（角色硬约束）；M-2 门禁事实全部取 Coordinator 申报口径，报告中标注为「申报值」而非本审查实测；`core/releases/0.83.0.json` 经只读抽查核对（见 §6 佐证） |
| **结论** | **APPROVED_WITH_NOTES（unresolved_blockers=0）** |
| 发现计数 | **6 = 0 BLOCKING / 3 WARNING / 3 NOTE**（详见 §5） |

---

## 1. 维度一：发布检查清单（0.83.0 checklist vs 0.82.0 模板 + 门禁事实一致性）

### 1.1 结构对照（vs `release-checklist-0.82.0.md`）——PASS

0.82.0 模板全部节在 0.83.0 中逐节对应：M-0 草案头注（含冻结纪律 + M-2 派生回填例外）、保守边界声明、Release Scope（含显式排除行）、Change Inventory（载荷编号 1..N 连续 + ⟦M-0⟧/⟦M-1⟧ 占位行）、行为变更节、Candidate Gate Results（含 Gate 10 明细指引）、RISK 复评提案（M-4 承载、不改 risk-log 的边界声明）、真机验收（禁声明纪律保留）、M-2 执行序、M-8 收尾义务。0.83.0 为**结构超集**：新增「版本号决策记录」「披露清单」「发布步骤 M-0~M-8 勾选框」三节——增强不缺位，无模板节缺失。0.82.0 特有节（F-R1-02 数据面处置提案）为该版专属事项，0.83.0 不需要（对应缺口已由 0.83.0 checklist Gate 17 的「任务列 token 已含 FIX-349/FIX-350/REL-079」预防面承接）。

### 1.2 Gate 表 1~18「M-2 回填」状态 vs 门禁事实——PASS（非通过化核实）

- **全部 18 行 Result 列 = ⟦M-2 回填⟧占位，无一行被写成通过**——符合「未回填项不得视为通过」硬规则。
- 逐行对照 Coordinator 申报事实，**零矛盾**：①~④ 五门禁申报 PASS（version/projection/manifest/injection/ratchet = Gate 1/2/3/4/6）与各行「预期」注记一致；Gate 13 申报 `release-ledger --version 0.83.0 --no-remote = NATIVE_CANDIDATE`（正确候选态）+ e2e-check PASS；Gate 17 申报初轮 3 FAIL 为治理数据面漂移（快照刷新/状态格清理/总览活跃版本+句读修正），复跑 PASS——修复走数据面、非引擎面，与 checklist「0.82.0 F-R1-02 过报族预防面」预期同族，无复审义务转移；执行门 2 项披露（governance health 21 基线 + unit 180s 预算口径）与披露清单 §1/§2 同口径；quality-tools NOT_RUN 如实（未安装）。
- **Gate 10 全量失败归因**：申报 30 failures 全为 WSL 环境族 + 活体数据漂移族——与 Gate 10 明细指引「预期仍红的既有基线族（①WSL 环境敏感 ②live replay 活体耦合）如实披露不阻断」一致；且明确「0.82.0 已收口基线（850 OK）不再出现，若出现即真回归」的守卫未触发。**但计数差额归因存在缺口 → F-3（WARNING）**。
- Gate 14（回滚方案）：已交付（见维度二）；revert 干跑如实标为 M-2/M-5 义务而非完成。
- **Gate 16 构成漂移缺口 → F-1（WARNING）**。

### 1.3 披露清单 vs 实际构成——PASS with F-1

披露清单 6 项（§1 health 21 构成 / §2 unit 180s 先例 / §3 WSL 红 / §4 hooks replay 漂移 / §5 Check 30 V2=RISK-051 / §6 28q 移交中）全部标注「非通过项」性质，**无披露写成通过**。§5 与 risk-log RISK-051 行（打开-已接受，DEC-199 (a)）、CHANGELOG 如实披露① 三方一致。§1 构成枚举与 M-2 申报构成存在漂移（F-1）——两文档均带「以 M-2 当场输出为准」从属句，故非虚报，但 M-2 回填 MUST 逐条归因后刷新。

### 1.4 证据链核对——PASS

FIX-348/349/350 终态（`57c6fc4`/`bf7e25a`/`589e99f` + REVIEW-*-CODE-R0 APPROVED_WITH_NOTES/0 + EVD-1064/1066/1067 + DEC-198/199〔随 349 批落账〕/201）在 checklist、CHANGELOG、plan-tracker 任务行（L91~93）三源逐字一致；Scope「不发布什么」行与 DEC-201 ⑥（F-1 P2 + F-2/F-3/F-4 P3 → 0.84.0+）、FIX-349⑤（28s 评估-only）、RISK-046 遗留候选、28q 移交中、DEC-199 (a) 逐项对得上。Release Scope 各行版本归属无漂移。

## 2. 维度二：回滚方案（`rollback-plan-0.83.0.md`）——PASS with F-2

- **区间锚定**：`24cfb04..<发布 tip>`——起点 = 0.82.0 发布 tip（tag peel）、终点 = M-5 transition（占位不预填，附「不预先编造」红线）✓；F-01/F-04 先例教训注记在场且方向正确（起点不得用 HEAD `589e99f`；终点必须是发布 tip）。**锚点 hash 表述与 plan-tracker 存在冲突 → F-2（WARNING）**。
- **发布前中止两档**（§2.3）：仅弃工程批（reset → `589e99f`，保留 FIX-348/349/350 载荷 + candidate JSON/tag 清理）与连载荷放弃（reset → `24cfb04`）两档清晰；「已推送后不得 reset、改走 revert」+ DEC-200 预授权不覆盖中止面破坏性操作的边界声明 ✓——与 rollback §6 决策权节、CHANGELOG 预授权边界句三方一致。
- **验证表**（§4）：10 项含双值对照（渲染 sha256 0.82.0 基线 / 0.83.0 候选均 ⟦M-2 回填⟧不预填）、#7「计数下降是回滚预期结果」如实注记、#8 已知过报面回归逐项列名、#10 revert 干跑 = **M-2/M-5 期义务（≥1 次）**——未标已完成、未预填结果 ✓（「已验证」口径如实）。
- 影响分类（§1）：四类判定面回归（Check 16 假阳回归/requirements 误报回归/ArchGuard 三红回归/Unicode 防护面回退）逐项如实列名，含「不预判数字」纪律；治理数据面不进 git 窗口、豁免账本零触碰、渲染面零影响预期——与三件套其余文档零矛盾。
- 数据安全（§3）/不可回滚项（§5，含 RISK-051 历史缺口承载记录）/触发条件（§6，4 条 + 决策权）齐备。

## 3. 维度三：CHANGELOG（[0.83.0] 段）——PASS

- **用户视角完整**：Added（Check 14 子检查 6）/ Changed（B-1/B-3/B-4）/ Fixed（Check 16 假阳清零 / Check 5×13 + Check 17×14 数据清零 / 日期勘误）/ 行为变更 B-1~B-4（指向 feature-flags §2）/ 如实披露①~⑤ / Breaking changes：无 / MINOR 依据 / 版本投影过渡态说明——关键段全覆盖 ✓。
- **commit 对照**：FIX-348=`57c6fc4`、FIX-349=`bf7e25a`、FIX-350=`589e99f` 与 checklist Change Inventory、plan-tracker 三源一致；M-1 bump commit 明确**不列载荷行**（checklist ⟦5⟧ + CHANGELOG 末段同口径）✓。
- **B-1~B-4 与 feature-flags §2 逐条对表**：旧行为/新行为/理由/影响面四列语义一致，无文档间措辞冲突；「升级提示」面向用户段落与 checklist 行为变更节一致。
- **breaking=无 声明核实**：B-1~B-4 逐项按 VERSIONING.md L11 三判据（无接口删除/重命名、无 Gate 语义破坏、无治理字段格式变更）论证成立；B-1/B-4 为判定收窄（过报消除）、B-2 为加性告警面、B-3 为判定面校准+披露化——「过报消除面可能吞掉真实违规」的风险已由 rollback §6 触发条件 1 承接，无未披露的破坏面。
- **数字引用一致性**：33→21（CHANGELOG 首段+收敛段 = checklist Scope 行 = plan-tracker REL-079 行 ✓）；24453→24583（+130 = +85+45，算术自洽 ✓，三文档一致）；19→0 ✓；30→80（74 版本现状）✓；R4 print 1299→1301 ✓；棘轮套件 38/38 ✓；+102/+7 追认批 ✓；God-module 24583 行 ✓。
- 日期勘误（⑦）明示 scope = 治理热文件——CHANGELOG [0.82.0] 段日期头未随之改动，见 F-6（NOTE）。

## 4. 维度四：Feature Flag（`feature-flags-0.83.0.md`）——PASS

- **无 flag 声明充分性**：三点依据齐备且成立——① 无新运行时能力分支、无「新旧行为并存」灰度前提；② 变更方向为过报消除/披露化/阈值校准、无「需紧急关闭的新行为」形态；③ 回退通道 = 版本级回滚（指引到 rollback-plan）。§4 D-1/D-2 如实列出「本版未提供降级开关」+ kill switch 需求显式声明为无 ✓。
- **ArchGuard 边界如实登记**（§1.1）：28n/28o/28p 维持 `fatal_on_error=false` 既有边界，FIX-350 改判定面不改边界；28o 残余披露（归属/计数受 F-1 漂移影响）；豁免全走 [EXEMPT] 双面披露（DEC-151 不静默）、无豁免 schema 行为不变（负例锁定）✓。
- **§1.2 非开关登记**（Check 14 子检查 6 / Check 10 M5 白名单）、**§3 加性面表**（无新增 CLI 命令，棘轮口径以 M-2 当场值为准不预填）、**§5 与 0.82.0 对照无删除**（既有开关 + 4 条豁免 + digest 锚 + B-1~B-8 延续）——与「窗口三 commits 范围面」零触碰声明一致 ✓。

## 5. 维度五：版本号——PASS

- **MINOR 依据成立**：L12 触发（Check 14 子检查 6 新扫描面 + ArchGuard 豁免 gate 四面扩展 = 新增自动化能力面；Check 16/Check 10 = 判定规则扩展）+ L37 同型先例（0.79.0/0.82.0）+ L38 PATCH 不适用（含行为语义变更，非纯修缺陷）+ L11 MAJOR 无一触发。checklist「版本号决策记录」表 + CHANGELOG MINOR 段双载体一致。
- **路线图一致性**：plan-tracker 0.83.0 路线图行在案（2026-09-17，REL-079 承载，主题「治理健康收口 + 架构债批（MINOR）」与 CHANGELOG/checklist 一致）；无跳号（0.82.0 → 0.83.0 连续，两行均在）；无预留冲突（DEC-200「REL-079 全仓零占用已核」入档）。
- 任务行/路线图行交叉：REL-079 任务行（P1，0.83.0，🔄 进行中 M-2）与路线图行、总览活跃版本（0.83.0 候选）一致；热区两处「M-1 候选打包中」字样滞后于实际阶段 → F-4（NOTE）。

## 6. 佐证抽查（只读）

`skills/software-project-governance/core/releases/0.83.0.json`：`lifecycle_state="candidate"`、`provenance="native"`、`schema_version=1`、`artifacts.release_docs` = 本三件套路径全 registered、`events=[]`（无 transition 事件）——与申报 NATIVE_CANDIDATE、M-1 candidate 入库、M-5 未执行的阶段事实一致 ✓。

## 7. 发现清单

| # | 级别 | 发现 | 证据 | 必须动作 |
|---|---|---|---|---|
| **F-1** | **WARNING** | **21-issue 存量构成枚举 vs M-2 申报构成漂移**。checklist 披露清单 §1 / 保守边界 / CHANGELOG 收敛段与披露② 枚举 = 28o 残余 4E（God-module）+ 28s ×1 + 30 V2 ×1 + 28q ×1；M-2 申报构成 = 28s + 30 + **28n×8**（God-module 真实 advisory）+ **14/36 legacy**（约 11 项）。差异：(a) God-module advisory 归属与计数（28o 4E vs 28n 8）；(b) 14/36 legacy 11 项未见于文档枚举（占 21 项过半）；(c) 28q ×1 未见于 M-2 申报枚举 | checklist L15/L107；feature-flags §1.1；CHANGELOG L17/L42 vs 任务上下文申报「28n×8=God-module、14/36=legacy」 | M-2 回填 Gate 16 时**逐条归因构成漂移**（checklist Gate 16 行自带「不得以旧值作新声明」纪律）；若终构成与枚举不同，M-5 冻结前刷新 checklist 披露 §1 与 CHANGELOG 构成句。文档已带「以 M-2 当场输出为准」从属句，故本项**不构成虚报**，但回填缺归因即升级 NEEDS_CHANGE |
| **F-2** | **WARNING** | **回滚锚点 hash 表述冲突**。0.83.0 checklist/rollback-plan 将 `24cfb04` 标注为「0.82.0 发布 tip = **transition 提交** = v0.82.0 tag peel」；plan-tracker REL-078 任务行记录「M-5 transition `b63584c`（…；integrity 公式修正 `24cfb04`）」。最自洽解读：b63584c = transition commit，24cfb04 = 其后继 integrity 公式修正提交 = 发布 tip/tag peel——但「24cfb04 = transition 提交」措辞与之冲突。若实际 tag peel ≠ `24cfb04`，回滚区间起点错锚（0.81.0 R0 **F-01 同形风险**） | rollback-plan §区间锚定 + §2.1；checklist L28/Gate 14 vs plan-tracker L94 | M-2/M-5 revert 干跑（本就是 ≥1 次义务）**执行前 MUST 机核实锚**：以 `v0.82.0` tag peel 实测值对照 `24cfb04`；若不等，区间锚定失效须先勘误再干跑。若 24cfb04 实为 post-transition 修正提交，更正「transition 提交」措辞（锚值本身按 peel 实测为准） |
| **F-3** | **WARNING** | **Gate 10 计数差额归因缺口**。申报独立全量 = **3211 tests**（30 failures 全为 WSL 环境族 + 数据漂移族，归因口径与预期基线族一致）；但 checklist Gate 10 注记预期「高于 3200」且已申报 FIX-350 追认批 **+102 + +7**（FIX-349 面另有新增）⇒ 朴素预期 ≥ ~3309，实测仅 +11，**差额 ≈ −98 无归因**（候选：discover `countTestCases` 口径 vs unittest `Ran` 口径差异、模块收集差异） | checklist Gate 10 行计数口径注记 vs 申报值 3211 | Gate 10 回填 MUST 按清单自带纪律「以当场 `Ran N tests` 为准并**披露与 3200 的差额归因**」补齐归因；全量原始失败清单逐条贴出 + pristine 对照仍为未闭合的 M-2 回填义务 |
| **F-4** | NOTE | **plan-tracker 热区新鲜度漂移（数据面，gitignored）**：`工作流版本` 行注记「M-1 候选打包中」+ 路线图 0.83.0 行状态格「候选打包中（M-1）」滞后于任务行/总览的「M-2 门禁实测中」；`工作流版本` 字段已 = 0.83.0，早于 checklist Gate 1 预期披露的「M-8 收尾才转 0.83.0」（实际状态优于披露，无风险） | plan-tracker L11/L270 vs L44/L96；checklist Gate 1 预期过渡态注记 | M-2 回填以当场值为准刷新状态格；Gate 1 预期披露句与实际数据已不符（实际更优），回填按现场写、不改文档预期句结构 |
| **F-5** | NOTE | checklist M-3 勾选框列举判定面语义独立审查对象为「B-1/B-2/B-4」，未列 B-3（本批最大判定面变更）。B-3 语义已由 REVIEW-FIX-350-CODE-R0（CODE 半面）覆盖，本审查已对 B-1~B-4 全量做文档一致性核对——无遗漏风险，仅范围列举措辞不完整 | checklist M-3 框 | 无强制动作；后续版本 M-3 措辞建议全列 B-1~B-N |
| **F-6** | NOTE | CHANGELOG [0.82.0] 段日期头仍为 `- 2026-09-18`，与 EVD-1065 勘误后的权威发布日期 2026-09-17（plan-tracker 三处 + 0.83.0 段⑦口径）不一致。FIX-349⑦ 明示 scope = 治理热文件，未动已发布 CHANGELOG 段——符合「历史不改」纪律，但 CHANGELOG 自身呈现日期与发布事实相反（0.83.0 段 09-17 早于 0.82.0 段 09-18） | CHANGELOG L48 vs L33/plan-tracker L11/L44/L94 | 登记为后续候选（DEC 裁决是否对已发布段加勘误注记）；本版不改（改即无 DEC 改写已发布载荷文本） |

## 8. 硬门槛裁决

| # | 硬门槛 | 裁决 | 依据 |
|---|---|---|---|
| 1 | checklist 逐项有证据；占位项显式标注 M-2/M-6 回填义务且非通过化 | **PASS** | 18/18 Gate 行 ⟦M-2 回填⟧ 占位、零通过化；冻结纪律例外（M-2 派生类）范围正确；发布步骤 M-0~M-8 勾选框未预勾；披露 6 项全部标「非通过项」 |
| 2 | 回滚方案存在 + 验证义务如实标注 | **PASS**（F-2 附条件） | 方案已交付且作为 Gate 14 交付物参与 check-release；干跑 = M-2/M-5 义务非已完成；sha256/发布 tip 占位不预填；区间锚定受 F-2 机核条件约束 |
| 3 | CHANGELOG 关键段全覆盖 + breaking 标注 100% | **PASS** | Added/Changed/Fixed + B-1~B-4 全覆盖；breaking=无 按 L11 三判据逐项论证、无未披露破坏面；commit 对照 3/3；数字引用全量一致（含 24453+130=24583 算术自洽） |
| 4 | flag 面如实（无 flag 声明亦须三点依据） | **PASS** | 三点依据齐备；kill switch 显式声明为无 + 理由；ArchGuard `fatal_on_error=false` 既有边界如实登记；D-1/D-2 无降级开关如实列出 |
| 5 | semver 合规 | **PASS** | MINOR = L12 触发 + L37 先例 + L38 排除 + L11 不触发；路线图行在案、无跳号、无预留冲突（DEC-200 零占用核） |

## 9. 审查结论

**APPROVED_WITH_NOTES（unresolved_blockers=0）**——RELEASE 半面（三件套 + CHANGELOG [0.83.0] 段）就绪状态成立：

1. 五维审查零 BLOCKING；硬门槛 5/5 PASS。
2. 3 条 WARNING（F-1/F-2/F-3）**全部为 M-2 回填阶段的核对/归因义务**，且均为 checklist 自带纪律的显式要求（「以当场值为准」「构成漂移逐条归因」「差额归因」「干跑前核实」），非发布文档缺陷；F-2 的机核动作本就内嵌于强制的 revert 干跑。
3. 3 条 NOTE（F-4/F-5/F-6）为记录性事项，不构成本版义务。
4. **约束性备注（binding notes）**：若 M-2 回填在未补齐 F-1 构成归因、F-3 计数差额归因，或未经 F-2 锚点机核即干跑的情况下完成并推进 M-4，本审查结论作废，发布链必须回到 RELEASE 半面复审（R1）。
5. CODE 半面（B-1~B-4 判定面语义、diff 级核对）不在本审查范围——由 REVIEW-FIX-348/349/350-CODE-R0 与 CODE 半面独立审查承载（REVIEW-FIX-348/349/350-CODE-R0 终态 APPROVED_WITH_NOTES/0 取自 plan-tracker 任务行，本审查仅作交叉引用未复核 diff）。

---

*审查方法声明：本审查为纯只读文档审查（Read/Grep/Glob），未执行任何命令；所有 M-2 门禁数值（五门禁 PASS、NATIVE_CANDIDATE、e2e PASS、3211 tests / 30 failures、health 21、hot-fact-source 复跑 PASS、quality-tools NOT_RUN）均为 Coordinator 申报口径，本报告标注为「申报值」。`core/releases/0.83.0.json` 为唯一经本审查只读抽查的机读佐证（candidate 态 + 三件套 registered）。事实依据红线遵守：未实测项一律不写为通过。*
