# REVIEW-REL-086-CODE-M3 — 0.88.0 M-3 产品代码半面审查（发布就绪综合审查 · R0）

> **任务**: REL-086 M-3 产品代码半面（Code Reviewer · R0——版本级发布就绪综合审查）· **日期**: 2026-09-25
> **审查基线**: HEAD = `f350c95`（REL-089），工作树干净（`git status --porcelain` 零输出，实测）——与任务书一致
> **审查口径**: **跨票综合面**——24 票各自 R0/R1 审查链全 APPROVED 终态，本审查不重复票内内容，只审交互/汇总/一致性面
> **方法**: 只读 + 实测。门禁三连在 HEAD 现场复跑（check-version-consistency / release-projection check-only / check-manifest-consistency）；关键交互缝代码实读；双 changelog 节级字节比对；豁免账本 infra 全树 grep；决策链/证据链/发布四件套全文实读。零文件修改。

---

## 0. 输入面（全部实读）

| 输入 | 事实锚 |
|---|---|
| plan-tracker REL-086/REL-089/FEAT-061/FIX-385 行 | L103/109/111/116/117/120/309 |
| release-checklist-0.88.0.md | 全文（#1~#19 门禁表 + 四专席 + 披露①~⑨ + M-0~M-8 步骤） |
| release-plan-0.88.0.md / version-plan-0.88.0.md §3 条 1~2 | L68（组合测试集四条）/L77（F-6） |
| rel-089-m3-precondition-report.md | 全文（DEC-240 三放行条件产物） |
| decision-log DEC-237/238/239/240/241 | decision-log.md L179~183（机器凭证 op-b132…/op-db8e…/op-c307…/op-c16d…/op-bceb…） |
| M-2 commits | `501d8dc`（门禁实测批）/ `36cc899`（Check 18/18b 披露补充）——`git show --stat` 实测触达面 |
| evidence-log | EVD-1146/1147（L2630/2631）、EVD-1164/1165（L2694/2697）；文件现值 1,694.6 KB |
| rollback-plan §8/§9、feature-flags §B-12/B-13 | `f350c95` 落位实测；F-5①③ 归票落字核对 |

---

## 1. 维度一：组合一致性（FEAT-060 × FEAT-061 × FEAT-064 × FEAT-062/063 交互面）

### 1.1 F-5 四条组合测试归属链——**一致落字核实（五面一致，一行缺口）**

F-5①③ 归 cutover 授权票的归属，逐面核对结果：

| # | 载体 | 落字 | 判定 |
|---|---|---|---|
| 1 | DEC-239⑦（decision-log） | 「F-5①③ 组合测试（归切换授权票：台账损坏×切换窗共存/基线更新×投影失败恢复）」 | ✅ 权威裁定 |
| 2 | plan-tracker FEAT-061 行「cutover 授权票验收项」 | 「④F-5①③ 组合测试⑤FEAT-062 F-7 dec_in_world 耦合 md backend〔REVIEW-FEAT-062-R1 补落〕」 | ✅ 票面承接 |
| 3 | checklist 披露④ | 「DEC-239⑦ F-5①③ 组合测试归票，闭环+证明包审查后另行授权」 | ✅ |
| 4 | rollback-plan §9 候选池 #3 | 「B-13 真实切换授权票（…+ F-5①③ 组合测试 + …）」 | ✅ |
| 5 | feature-flags §B-13 切换通道 | 「前置 = DEC-238④ 三缺口（RISK-059…）+ **DEC-239⑦ 归票的 F-5①③**」 | ✅ |
| 6 | **checklist #12 门禁行** | 四条全文照列 + 「禁全量不得退化为只测单票」——**无 ①③ carve-out** | ⚠️ → F-3（P2） |
| 7 | version-plan §3 条 2 | 四条列为本版组合测试义务（M-0 冻结件，早于 DEC-239⑦） | 历史件，以 DEC 为准 |

**②④ 票内实测证据核验**：FEAT-064 `a8afcbf` commit message「F-5② 组合实测」；FEAT-062 `14797be`「F-5④ 组合真并发实测（真锁竞争注入 92.86s）」——与票位（D1/E1）及 REVIEW 终态（R0 APPROVED_WITH_NOTES/0 / R1 APPROVED/0）一致。

### 1.2 交互缝代码级抽查（本席独立实读，非转抄票内审查）

| 缝 | 实测锚 | 判定 |
|---|---|---|
| closure 取消/重开/接管 → DEC 登记（BLOCK 合规） | `closure_chain.py` L60-61「not a writer — every governed effect goes through the batch-1 writer CLIs」+ L72「deterministic per-step operation ids (stable across resume)」 | ✅ 与 FEAT-062 commit 声明（DEC 经写入器登记+幂等键恒定）一致 |
| FEAT-064 BLOCK 激活 × FEAT-061 迁移写入路径（F-5② 语义） | `decision_migration.py` L59「consume transaction remains the only baseline writer」+ L310「an in-flight writer holds the same lock」 | ✅ 迁移路径走同锁域写入器——零手工写入语义在代码结构上成立 |
| B-12 回退通道 | `verify_workflow.py` L23916「--deactivate-block is the audited B-12 flag rollback」+ L25893 argparse 面 | ✅ 通道在场，与 rollback-plan §7/feature-flags 口径一致 |
| 未激活缺省（B-12 全 WARN / B-13 MD_ACTIVE） | REL-089 `test_rel089_release_compat.py` 11 用例机器断言（干净安装+0.87 升级两路径：check-only 零写入/converge 不隐式激活/show-posture 全 WARN/load_authority 恒 MD_ACTIVE） | ✅ 文档边界有测试看护，非仅文字主张 |
| closure journal 0.87 回退误读向量 | rollback §8 运行手册门禁（回退前登记 0.88 事件闭包清单+禁止 resume/finalize）+ FIX-391 候选承接；伪造 tombstone 否决（DEC-241 附带裁定——P1/append-only 纪律） | ✅ 防线落位，残余风险如实披露 |

**维度一结论**：交互面**无阻塞性组合缺陷**；归属链五面一致落字，唯 #12 行级缺交叉引用（F-3，P2 文档面）。

---

## 2. 维度二：CHANGELOG / 发布文档终审（M-3 席位义务）

### 2.1 双位同文纪律实测（字节级）

根 `changelog.md` 与 `project/CHANGELOG.md` 各自 0.88.0 节（`## [0.88.0]` 起至下一 `## [` 前）提取后 `git diff --no-index` 比对：**内容逐字相同，仅差 1 行尾部空行 + EOL 规范化**（root LF / project CRLF——96 字符差 = 节内行数 × `\r`）。**双位漂移风险尚未 materialize**。

### 2.2 验证锚定面实测（canonical 裁决证据）

| 事实 | 锚 | 含义 |
|---|---|---|
| `REQUIRED_SNIPPETS` 含 `ROOT / "project/CHANGELOG.md"` | verify_workflow.py L1047（路径表 L521） | 防循环验证锚读 **project** 面 |
| version-consistency CHANGELOG 检查 | L7317 `changelog_path = … project/CHANGELOG.md`；L17474-17479「CHANGELOG.md 最新版本与 SKILL.md 不一致」即 FAIL；L25092 help 文本同 | 版本一致性机器裁决读 **project** 面 |
| manifest | project 面 manifest 已收；根 changelog.md = [UNTRACKED]（本审查三连实测） | **project** 面在账本内，根面在账本外 |
| 投影系统 | release-projection 28/28 PASS issues=[]（不含 changelog）——根面不是任何受管投影 | 根面**无任何机器验证锚** |

### 2.3 裁决项① —— **CHANGELOG canonical 双位归属（本席裁决）**

> **裁决：canonical = `project/CHANGELOG.md`；根 `changelog.md` 定位为根面用户入口投影。**

**依据（四点，全部实测）**：
1. **全部机器验证锚定在 project 面**——REQUIRED_SNIPPETS（L1047）、version-consistency FAIL 判定（L17474-17479）、路径表（L521）无一读根面；canonical 必须是检查器裁决的对象，否则「canonical」无执行语义。
2. **历史连续判据面**——0.87.0 及更早全部历史仅在 project 面（2,195 行 vs 根面 68 行）；REQUIRED_SNIPPETS 历史判据锚在其中。
3. **账本状态**——project 面已入 canonical manifest；根面实测 [UNTRACKED]（见维度三），是当前唯一 manifest FAIL 成分。
4. **发布语义**——双位过渡注记（根面头部）自述「canonical 归属留 M-3 审查裁决，裁决前漂移风险由双位同段纪律控制」；本裁决后纪律目标明确化。

**配套义务（非本席执行——Coordinator 落字）**：
- **0.88.0 发布窗**：维持双位同文纪律不变（已实测同文）；**M-5 提交批把根 changelog.md 入 canonical manifest**（发布交付物入账——同时消解维度三的 manifest [FAIL] 唯一成分）；同步把根面头部「留 M-3 审查裁决」注记更新为裁决结果（→F-9，P3）。
- **0.89 候选**：把根面转为生成式投影（release-projection 托管）或增设 sync check；EOL 规范化一并钉死（当前 LF/CRLF 差异会制造 diff 噪声——→F-10，P3）。建议登记入 rollback §9 候选池。

### 2.4 发布四件套一致性抽查

- release-plan/checklist/rollback/feature-flags 对 B-12/B-13「机制交付未激活」双层姿态口径**五面一致**（checklist 保守边界 L14 + 披露④⑤、feature-flags L14/29-30/38、rollback §7/§8、CHANGELOG 披露④⑤、DEC-239②）——无越权主张面，no-overclaim 边界（官方认可/市场/全运行时/1.0.0）逐条在场。
- 29 提交窗口计数：checklist L31（`rev-list --count 602f8f3..HEAD` = 29 @3fb42c0）与 rollback §2.1 注记（M-5 现场重取，不写死）自洽；`f350c95` commit message 的「F-1 29 commits 双指涉留 M-5 刷新消解」与该设计一致（M-5 期义务，非缺陷）。

---

## 3. 维度三：版本锚终验（三连实测 @HEAD f350c95——M-1/REL-089 提交之后）

| 门禁 | 实测结果（本席 2026-09-25 HEAD 现场复跑） | 判定 |
|---|---|---|
| `check-version-consistency` | **PASSED**——source=0.88.0；13 文件+双入口 marker 全一致；唯一 WARN = plan-tracker 工作流版本 0.87.0（已知过渡态，M-8 消解义务在案） | ✅ 与 checklist #2 期望逐字吻合 |
| `release-projection`（check-only） | **state=PASS / source_version=0.88.0 / projections_checked=28 / issues=[]** | ✅ 与 #5 期望逐字吻合——M-1 单次收敛后经 M-2/REL-089 提交仍幂等 |
| `check-manifest-consistency` | canonical **894** / actual **1033**；**[UNTRACKED] 1 = 根 changelog.md** → 打印 **[FAIL]**（进程 exit 0——advisory 模式） | ⚠️ → F-2（P1，随裁决①收口） |

**锚结论**：版本锚三面在全部窗口提交（含 M-1 bump、M-1R 四件套、M-2 regen、REL-089 测试增量）之后**保持一致**；唯一开口 = 根 changelog.md manifest 缺口，即裁决项①的既有披露面，收口路径已由本报告裁决给出。REL-089 报告「唯一 UNTRACKED = 根 changelog.md」与本席实测一致（该缺口非 REL-089 引入）。

**测试基线链核对**：M-2 全量 `4108P/0F`（`501d8dc`）→ REL-089 纯测试增量 +11（`test_rel089_release_compat.py`，零产品代码修改——commit diff stat 四文件全部为报告/回滚文档/测试/审查报告）→ `4119P/0F`（`f350c95`）。任务书口径 4119P 为 REL-089 后值，与 M-2 值 4108P 差 = 11 用例，**数字链自洽**；version-plan §3 条 1「M-3 修改可执行代码须退回验证」规则被正确适用（本窗 M-3 前置票零产品代码修改，M-2 全量预算对产品代码持续有效）。

---

## 4. 维度四：门禁证据链（M-2 席位结果 vs checklist #1~#19 回填）

### 4.1 M-2 已执行证据（commit 载体）

`501d8dc`（门禁实测批）：全量 pytest **4108P/0F**（#11）· verify **PASSED**（#1）· LRC **PASS**（#16）· archguard `--regen` 锚 25462→26193 @a8a72a3 + R4 1318（#8/专席④，FEAT-055 先例 sanctioned）· 冻结测试再基线（FACTS_PRINT_TOTAL 1316→1318）· 自举链收敛运行活体生效（WV-755f converged=true——FIX-383 能力发布窗首用）· Check 28s/REQ-092 已知披露面维持（#17/专席②）。`36cc899`：Check 18/18b **2×2 FAIL** 披露入专席②（EVD-1140/EVD-1164——已由 DEC-241 例外覆盖，见维度五）。

### 4.2 回填状态实测——**发现 F-1（P1）**

**checklist #1~#19 门禁表在 HEAD 仍全部为 ⏳ 回填位**（本席逐行实读）；唯一回填动作 = `36cc899` 向专席②追加 1 行披露段。checklist 头部 L3 明文义务「实测后由执行工位原样回填命令输出」与 M-2 checkbox（L173）均未兑现。M-2 结果当前**仅存活于 commit message**——这是 M-3/M-4 go/no-go 主证据载体的缺失。

**缺跑/缺记录席位盘点**（M-4 窗补齐义务）：

| 席位 | 状态 |
|---|---|
| #3 注入预算 ×3 profile / #4 projection+entry sync 复跑 / #6 cross-refs / #9 contract-matrix 97 键复跑 / #14 e2e/dsh 冒烟 / #19 执行包面 | **无任何已记录执行证据**（M-2 commit 未提及） |
| #16 LRC | commit 称 PASS 但**当场 units 计数未记录**（专席③要求如实记录——0.87 期 308,248 先例形态） |
| #12 组合测试集 | ②④ 票内实测（EVD 在案）；①③ 归 cutover 票（DEC-239⑦）——回填时 MUST 行内注记 carve-out（F-3） |
| #13 独立证明包门 | FEAT-061 票内演练（179 行 round_trip）在案；「绑定发布提交」子项结构上属 M-5（F-8，P3） |
| #10 ledger / #15 check-release | 预提交态预期 FAIL / Coordinator 提交批义务——披露①口径，非缺口 |

**关联发现 F-6（P2）**：M-2 门禁批**无 evidence-log entry**（`501d8dc` 声明「M-2 EVD 随发布链总结机录」——截至 HEAD 未落；grep 零命中）。commit message 不是治理证据账本。

**F-2（P1）**：manifest [FAIL] 唯一成分 = 根 changelog.md（实测见维度三）——收口 = 裁决①配套义务（M-5 提交批入 manifest）。

---

## 5. 维度五：DEC-241 例外 + EVD-1146 处置口径终审（M-3 两点名席位）

### 5.1 裁决项② —— **EVD-1146 处置口径复核**

| 复核面 | 实测 | 判定 |
|---|---|---|
| 历史行未动 | EVD-1146 原行在 evidence-log L2630 原样在场（13-char 短目标对齐字段未被补录改写） | ✅ |
| 合格重写在场 | EVD-1147 L2631，独立机器凭证 `op-721bf76f…`，目标对齐字段完整化 | ✅ |
| 不入豁免账本 | infra 全树（py/json，含 verify_workflow.py/checks/、STATIC_PIN 账本面）grep `1146` **零命中** | ✅ 未入 B-11/static-pin 任何账本——DEC-227「新增行零豁免全严检」红线维持 |
| 披露承载 | checklist 专席② + 披露② + REL-089 报告三面同口径（不补录、不动+披露） | ✅ |
| 决策先例一致 | DEC-227 路线 a 否决先例（补录=编造风险违反 P-v1 原则 1） | ✅ |

> **裁决②：EVD-1146 处置口径「不动 + 披露 + 不入豁免账本」——维持，复核通过。** Check 16/17 的 EVD-1146 superseded 残留维持为活跃披露面（非豁免），M-2 期新增 FAIL 零入账本（FIX-375 EVD-1140 与 REL-087 EVD-1164 走的是 DEC-241 正式例外通道，非账本豁免——两条通道未被混用）。

### 5.2 DEC-241 正式例外合规复核（Check 18/18b 分叉面 2×2 FAIL）

| DEC-240② 要求 | 实测 | 判定 |
|---|---|---|
| 人工复核（身份+状态链+本应满足规则）留档 | rel-089 报告 §②：双记录身份（L2606/L2694）、ops 台账收据对账（op-0aff7f5b…/op-4328347b…——行内嵌同一 operation_id）、规则三面（basis 按 DEC-168 契约落 parts[5]，严检读 parts[4]——检查器读位分叉非数据缺陷） | ✅ |
| 例外限定（具体记录/检查项/候选版本） | {EVD-1140, EVD-1164} × {Check 18, 18b} × {0.88.0} | ✅ |
| 不做全局绕过（不改谓词、不加豁免行） | 谓词面 FIX-376 F-3 窄口径未触碰——M-2/REL-089 三 commit 触达面实测不含 verify_workflow.py 豁免谓词区；infra grep 无新增豁免行 | ✅ |
| 修复票 + 期限 | FIX-390 票面完整（三态回归/两行红→绿活体/差分归因验收）；0.89 候选 | ✅ 票面在案；**跟踪面缺口 → F-5（P2）** |
| REL-089 活体复现对账 | 报告 §② check-governance 输出与 M-2 记录（36cc899）2×2 逐字吻合 | ✅ |

> **DEC-241 例外终审：合规通过**（四要求全满足），附一项跟踪面条件（F-5）。例外属「登记+披露」型，未稀释任何检查语义——fail-closed 方向未被反转。

**衍生发现 F-4（P2）**：DEC-240③ 明文「Check 28s 等既有 ERROR 须正式例外（已披露后续消解不单独构成放行依据）」——Check 28s 目前仅有披露席承载（#17/专席②+M-2 commit「已知披露面维持」），**无正式例外登记**（DEC-241 只覆盖 Check 18/18b）；且 evidence-log 实测 1,694.6 KB，窗口内自 1,620 KB 继续增长（F-6 警示方向——增长面为 24 票机录的如实代价）。M-4 窗 Coordinator 按 DEC-241 同型登记正式例外，或以实测证明其非 ERROR 级并如实重归类；M-8 归档消解义务不变。

---

## 6. 五维度硬门槛裁决（适配版本级口径）

| 维度 | 结论 | 关键证据 |
|---|---|---|
| 1 组合一致性 | **无阻塞缺陷**；归属链一致（F-3 行级文档缺口 P2） | §1：五面落字 + 四缝代码实读 + F-5②④ 票内实测锚 |
| 2 安全性 | **通过**（跨票面） | break-glass 五限定+审计不可静默通道在场（verify L23916/25893）；伪造 tombstone 正确否决（P1/append-only 纪律）；未激活缺省有机器断言看护；无密钥/注入面新增 |
| 3 可维护性（汇总面） | **通过** | 四件套+CHANGELOG 双位+决策链口径五面一致；TODO/FIXME/XXX/HACK 四个关键新文件全 0；canonical 漂移风险已裁决收口路径 |
| 4 性能（汇总面） | **通过** | LRC PASS（M-2）；Check 28s 面如实披露（evidence-log 1,694.6KB 增长为机录如实代价，M-8 消解义务在案）；无 O(n²) 新增面报告 |
| 5 测试覆盖 | **通过** | 4108P/0F→+11→4119P/0F 链自洽；REL-089 两路径 11 断言看护未激活缺省；version-plan §3 条 1 退回规则正确适用 |

**AI 代码专项 5 项（跨票面）**：mock 残留——抽查四缝均为真实写入器/锁域接线，零 mock 残留 ✅；硬编码返回值——未发现 ✅；幻觉 API——抽查调用面与 argparse/常量实读吻合 ✅；未实现 TODO——四文件 0 命中 ✅；过度实现——REL-089 条件三「最小修改面裁定」（五件安全忽略只加测试）为反过度实现的正面实例 ✅。

**设计一致性**：实现与 DEC-236/237/238/239 裁定逐面对照无偏离（§1.2 + §5.2）；无 ADR 偏离发现。

---

## 7. 发现清单（P0~P3 全量——零 P0）

| ID | 级别 | 发现 | 位置/事实锚 | 修复建议（工位） |
|---|---|---|---|---|
| F-1 | **P1** | M-2 已实测但 checklist **#1~#19 回填位全部未回填**；#3/#4/#6/#9/#14/#19 无已记录执行证据；#16 当场 units 未记录 | checklist L95-117 全 ⏳（HEAD 实读）；M-2 证据仅在 `501d8dc`/`36cc899` message | M-4 窗按 checklist L145 执行序补跑缺席位 + 原样回填全部行 + 新增 FAIL 逐项披露（Coordinator/执行工位） |
| F-2 | **P1** | manifest [FAIL]：根 changelog.md 在盘未入 canonical manifest（894/1033，1 UNTRACKED；exit 0 advisory） | 本席三连实测；REL-089 报告已知披露面 | M-5 提交批按裁决①入 manifest（消解唯一 FAIL 成分）（Coordinator） |
| F-3 | P2 | checklist **#12 行缺 F-5①③ carve-out**（归属链其余五面一致；「禁全量不得退化为只测单票」与①③缺跑在行文字面上自相矛盾） | checklist L110 vs DEC-239⑦/plan-tracker FEAT-061 行/checklist 披露④/rollback §9#3/feature-flags L38 | M-4 回填 #12 时行内注记「①③ 归 cutover 授权票（DEC-239⑦/FEAT-061 cutover 验收项④）；本版实测面=②④（FEAT-064/062 票内 EVD）」（Coordinator） |
| F-4 | P2 | Check 28s 仅有披露席、**无正式例外登记**——DEC-240③ 明文要求「既有 ERROR 须正式例外，披露不单独构成放行依据」；evidence-log 窗口内 1,620→1,694.6 KB 继续增长 | DEC-240③ 原文；DEC-241 只覆盖 Check 18/18b；本席文件实测 | M-4 窗按 DEC-241 同型登记正式例外，或实测证明非 ERROR 级并如实重归类；M-8 归档消解义务不变（Coordinator） |
| F-5 | P2 | **FIX-390/FIX-391 未入 plan-tracker TRIAGE 行**（REL-089 Coordinator 写回清单条 3 未完全兑现）——持久锚仅 rollback §9#8/#9 + DEC-241 行文；0.89 规划以 plan-tracker 热表为准时有漏票风险（DEC-241 消解条件 FIX-390 的可达性依赖） | plan-tracker grep 仅 L120 行内提及；rollback §9 在案 | M-4/M-8 窗补 TRIAGE 入账（0.89 候选态）（Coordinator） |
| F-6 | P2 | M-2 门禁批**无 evidence-log entry**（commit 声明「随发布链总结机录」未落） | evidence-log grep 零命中；`501d8dc` message | M-4/M-5 批机录入账（governance-store evidence-append，含全量 4108P→4119P 链、LRC units、archguard regen 前后计数）（Coordinator） |
| F-7 | P3 | plan-tracker REL-089 行状态滞后（「committed 收尾中……commit 待重试」——`f350c95` 已落库未刷新） | plan-tracker L120 vs git log | 随 M-8 收尾义务（REL-086/087/088 终态回填）一并纳入 REL-089 行刷新（Coordinator） |
| F-8 | P3 | checklist #13「绑定发布提交」子项在 M-2 时点结构上不可满足（发布提交 M-5 才存在），行内未注明拆分 | checklist L111 | M-4 回填时显式拆「M-2 已跑子项 / 绑定发布提交子项归 M-5」（Coordinator） |
| F-9 | P3 | 根 changelog.md 头部「canonical 留 M-3 审查裁决」注记在裁决后需同步更新 | changelog.md L5 | M-5 提交批随裁决①落字更新（Coordinator） |
| F-10 | P3 | 双位 0.88.0 段仅差尾部 1 空行 + EOL 规范化（root LF / project CRLF）——同文成立，但 EOL 噪声会掩盖未来真漂移 | 本席节级 diff 实测 | 0.89 候选 sync check 时一并钉死 EOL（登记候选池）（Coordinator） |

---

## 8. 总结论（发布半面口径）

## **GO_WITH_CONDITIONS**

- **P0 = 0**：零产品代码阻塞性缺陷。24 票交互面（guard 状态机×存储分离×BLOCK 激活×closure 取消/接管）经代码缝实读与归属链核对，**无组合性正确性缺陷**；未激活缺省（B-12 全 WARN / B-13 MD_ACTIVE）有 REL-089 机器断言看护；版本锚三连实测两绿一已知开口。
- **两项点名裁决**：① CHANGELOG **canonical = `project/CHANGELOG.md`**（根面=投影；M-5 入 manifest + 0.89 sync check）② **EVD-1146 处置维持**（不动+披露+不入账本——复核通过）；**DEC-241 例外合规通过**（附 F-5 跟踪面条件）。
- **放行条件（M-4 修复窗收口，M-5 提交批前完成——全部为流程/证据/文档收口义务，非代码修改）**：
  1. F-1：checklist #1~#19 补跑缺席位并原样回填（含 #12 carve-out 注记）；
  2. F-6：M-2 门禁批 EVD 机录入账；
  3. F-2：根 changelog.md 入 canonical manifest（随 M-5 提交批，按裁决①）；
  4. F-4：Check 28s 正式例外登记（或如实重归类）；
  5. F-5：FIX-390/391 TRIAGE 入账（0.89 候选态）。
- **unresolved_blockers=0**（零 P0/P 级代码阻塞；上述条件项均为发布链义务且已有明确收口工位与窗口）。
- **B-12/B-13 机制交付未激活边界随本审查重申**：本 GO 不构成 BLOCK 翻转或 JSON 切换授权——真实翻转/切换仍按 DEC-239②/DEC-238④+DEC-239⑦ 经授权票另行执行。

---
*REVIEW-REL-086-CODE-M3 · R0 · 2026-09-25 · Code Reviewer Agent（M-3 产品代码半面）。事实基线：门禁三连为 HEAD `f350c95` 现场复跑（version-consistency PASSED/1 预期 WARN；release-projection PASS 28/28 issues=[]；manifest 894/1033 [FAIL] 1 UNTRACKED=changelog.md）；双 changelog 节级 `git diff --no-index` 实测（1 空行+EOL 差）；REQUIRED_SNIPPETS/version-check/manifest 锚定面取 verify_workflow.py L521/L1047/L7317/L17474-17479/L25092 实读；交互缝取 closure_chain.py L60-61/72、decision_migration.py L59/310、verify_workflow.py L23916/25893 实读；M-2 取 `501d8dc`/`36cc899` `git show --stat`+message 实测；决策链取 decision-log DEC-238~241（机器凭证 op-db8e…/op-c307…/op-c16d…/op-bceb…）实读；EVD-1146/1147/1164/1165 取 evidence-log L2630/2631/2694/2697 实读；豁免账本面取 infra 全树 grep `1146` 零命中实测；4108P→4119P 链取两 commit message + REL-089 报告修改文件清单（零产品代码修改）对照。未复跑全量 pytest（M-2 一次预算纪律 + M-3 前置票零产品代码修改——退回评估规则正确适用）；LRC 当场 units 未复算（M-2 commit 称 PASS、数值未记录——已列 F-1）。*
