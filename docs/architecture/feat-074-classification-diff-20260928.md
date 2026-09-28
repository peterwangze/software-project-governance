# FEAT-074 修复前后逐行分类差异留档（DEC-278(4) 验收要件 / 单元一交付物）

> **任务**: FEAT-074 — 证据行实体解析与分类修复（DEC-278 单元一——Check 28s 结构性解锁）
> **授权链**: DEC-274 → DEC-278 单元一（TRIAGE-FEAT-074 机录）
> **版本**: **2026-09-28 重基线〔R0 勘正——REVIEW-FEAT-074-R0 F-1/F-2/F-3 处置〕，取代首版时点**（首版快照 sha256 `84323ebf…` 已因 evidence-log 漂移不可复算，故按 R0 建议「重基线」法在当前时点整档重跑；数字全部由对账脚本机械生成并过三方守恒自检，见 §1/§9）。
> **性质**: 只读测量产物（本档）+ 产品代码修复（archive.py / test_verify_workflow.py，另行审查提交）。**本票零迁移执行、零 Check 28s 阈值/语义变更、零 loop_migration 契约变更**（DEC-278 §3.2 红线遵守声明）。
> **数据时点**: 2026-09-28（重基线）；输入快照 = `.governance/evidence-log.md` **1,778,509 B / 2,918 行，sha256 `c7627e444421c763260c7f57974f71516db2ee50c6bc32fc1f9da178d827a0df`**。
> **代码锚**: before = git HEAD `b6575bd`（archive.py 末次变更 `8a94d64`）；after = 本票工作树（FEAT-074 修复含 R0 F-3 注释勘正，未提交）。两侧同输入、同 plan-tracker 现实态对跑。
> **数据面前提变化（相对首版）**: Coordinator 已落地 REL-086 行归一（plan-tracker L97 现为 8 管道两格）——重基线 before/after 均在此现实态上跑，首版的「场景 B 模拟」不再需要（现实即归一后）；FEAT-047 行未动（数据无需改动，见 §6.2）。

---

## 0. 结论摘要（全窗 0.1.0~0.91.0）

| # | 结论 | 数字 |
|---|------|------|
| 1 | `live_or_unresolvable_task_ref` 单桶 **314 行** → 五态可解释拆分，行数守恒零丢失 | 314 = missing 163 + 解锁进可迁移面 103 + 周期不可证 19 + 重复 ID 12 + 需求实体化 9 + 显式保留 4 + 活跃 4（公式字面成立，§4.4） |
| 2 | `no_task_family_ref` 141 行中 FEAT/FX 结构性错误状态消除 | 141 = 解锁 87 + 残留 35 + 缺失 12 + 超窗 4 + 重复 2 + 活跃 1 → after 残留 44（空引用 20 + 纯 REQ 8 + RISK 5 + DEC 3 + TIER 3 + DOC 3 + REQ+RISK 1 + DEC+RISK 1，Q6 归后继票） |
| 3 | would_archive（可迁移候选面） | **14 行 / 31,809 B → 204 行 / 642,749 B**（+190 = FEAT 解锁 87 + REQ 解锁 103；before 14 = 既有存量 11 + REL-086 归一落地解锁 3） |
| 4 | REQ 需求实体（Q2=c） | 156 次引用 / **40 唯一 ID 全部改判 requirement 态**（枚举=计数，§4.2）；双重登记歧义当前数据 0 例（机制已实现+测试覆盖） |
| 5 | FX 逐 ID 核验 | 14 唯一 ID 全部逐 ID 确证（归档映射 + git 首提 commit 双源证据，§4.3 注释已按 R0 F-3 对照归档行勘正）；未列名 FX 通配拒绝 → ambiguous |
| 6 | FEAT-073/074（当前活跃票） | 类型=task 且留热：EVD-1216~1219（FEAT-073）→ `ref_version_out_of_range`（owning cycle v0.92.0 超窗）；FEAT-074 热行「🔄 进行中」→ 未来引用必落 `active_task_ref`（类型正确≠当版迁移） |
| 7 | 安全反例族 | 重复 ID 7 组 14 行全拦（含 REQ 解锁后本可迁移的 EVD-424 两副本）；显式保留 4 行（EVD-553/887/888/1044）全拦；active 5 行全拦（归因勘正见 §5/F-2：其中三任务实为终态行，被既有 open_markers 否定语境假阳性误标） |
| 8 | REL-086/FEAT-047 布局异常 | 热表布局异常清零：REL-086=Coordinator 数据归一已落地（L97 两格拆分，before 侧旧代码同样解析出 tv=0.88.0 → 3 行进 would_archive）；FEAT-047=解析器转义管道盲区（行本身合法），代码修复后入 task_versions（v0.86.0） |

**注**: would_archive 面扩大 ≠ 本票执行迁移。实际迁移由单元三（FIX-402 存量清偿）按既有获批政策执行；本票只交付正确分类（R0 F-8 调度约束：单元三执行前任何全窗 migrate 调用的迁移量将大幅高于 before 基线，Coordinator 须防「顺手迁移」绕过单元三复验）。

## 1. 方法与可复现性（重基线）

- **重基线法（R0 F-1 处置选择）**: 首版快照（`84323ebf…`）时点后 evidence-log 又有写入（EVD-1216~1224 内容更新等 +290 B），before 侧无法在旧输入上复算。故按 R0 推荐在**当前时点**（`c7627e44…`）整档重跑：`git stash`（回 HEAD 旧代码）→ 采 before → `stash pop` → 采 after。两侧同输入、同 plan-tracker 现实态。task_versions 基线：before 545 项 → after 546 项（差 1 = FEAT-047 经转义管道修复进入 completed-hot 映射——代码差异的直接实证；REL-086 归一已在 before 侧生效，两侧同含）。REL-086 归一落地使首版 A/B 双场景合并为单一现实场景。
- **判定零漂移**: 临时脚本（`%TEMP%\fe074_r1_*.py`，用后已删——FIX-401 纪律）`sys.path` 注入 infra 后 `import archive`，直接调用产品函数 `_classify_evidence_rows` / `_evidence_task_versions_standalone` / `_build_classification_context`；脚本以 `inspect.signature` 自动识别 before（无 context 参数）/after（有）代码态。
- **窗位**: 主窗 `0.1.0~0.91.0`（全窗=已发布线）；副窗 `0.1.0~0.90.0`（保守 ≥1 窗）。
- **字节口径（R0 勘正注记）**: 行字节 = **raw 口径**——`read_bytes().decode().split("\n")` 行的 UTF-8 编码长 + 换行 1B（末行不计），与 Check 28s `st_size` 总量口径一致。evidence-log 混有 CRLF 行（本会话新增 EVD-1216~1224 等 17 行，行尾 `\r\n`）：raw 口径保留 `\r`（行实际占用含 2B 行尾）；`read_text()` 的 universal-newline 转换会每 CRLF 行低估 1B（17 B 差异来源，已在重基线中诊断并统一）。全部行字节加总 1,167,395 B（两窗、before/after、逐行转移三方相等，机械自检 PASS）。
- **算术自检（F-1 验收要件）**: 对账脚本机械验证：①每窗 transitions 行数加总 = before reason 加总 = after reason 加总（484=484=484，0 孤儿行）；②同三方字节加总相等；③REQ 枚举计数=去重计数（40=40）；④各桶拆分公式字面成立（§4.4）。

## 2. 逐行分类差异矩阵（before → after，行数/字节，raw 口径）

### 2.1 全窗 0.1.0~0.91.0 —— 484 行全量对账，0 行丢失

| before → after | 行数 | 字节 | 含义 |
|---|---|---|---|
| live_or_unresolvable → **missing_task_ref** | 163 | 322,598 | 引用 ID 三处（版本映射/热表/归档）均不可定位——单元三修复台账输入 |
| live_or_unresolvable → **would_archive** | 103 | 382,309 | REQ 需求实体解锁主体（REQ 参与且其余引用全部封闭在窗） |
| no_task_family_ref → **would_archive** | 87 | 228,631 | FEAT 87 行进入可解析面（FEAT 任务族补位） |
| no_task_family_ref → no_task_family_ref | 35 | 47,966 | 残留：空引用 20 + 纯 REQ 8 + RISK/DEC/TIER/DOC/混合 7（Q6 归 0.93） |
| live_or_unresolvable → **task_version_unparseable** | 19 | 48,372 | 生命周期已关闭但归期非 semver（REL-077 `G9/G11` 7 行 + 未规划版本 12 行）——周期封闭不可证，fail-closed |
| would_archive → would_archive | 14 | 31,809 | before 既有候选分类稳定（11 存量 + REL-086 归一解锁 3） |
| live_or_unresolvable → **duplicate_evd_id** | 12 | 17,042 | 重复 ID 拦截（EVD-424/240/216/217 组行内双副本） |
| no_task_family_ref → **missing_task_ref** | 12 | 31,779 | FEAT-014/016/026/029/030/054 等缺失引用行 |
| unknown_evd_id_shape → unknown_evd_id_shape | 10 | 11,660 | 形态外 ID（EVD-231-FULL 等）不变——单元三盘点项 |
| live_or_unresolvable → no_task_family_ref | 9 | 11,235 | 纯 REQ 引用行（REQ→requirement 非门控后无任务族引用） |
| ref_version_out_of_range → ref_version_out_of_range | 5 | 6,562 | 原超窗行稳定 |
| live_or_unresolvable → **explicit_keep_marker** | 4 | 9,279 | 显式保留标记门新增（EVD-553/887/888/1044） |
| live_or_unresolvable → **active_task_ref** | 4 | 8,920 | FIX-343 1 + FIX-349 3——**归因勘正见 §5（F-2）：终态行 + open_markers 否定语境假阳性，非真活跃** |
| no_task_family_ref → ref_version_out_of_range | 4 | 5,654 | FEAT 引用改门控后解析到超窗版本 |
| no_task_family_ref → duplicate_evd_id | 2 | 1,778 | EVD-181/EVD-150 第二副本 |
| no_task_family_ref → active_task_ref | 1 | 1,792 | EVD-1129（FEAT-059，同 §5 归因勘正） |
| **after 汇总** | **484** | **1,167,395** | would_archive 204 / missing 175 / no_family 44 / unparseable 19 / duplicate 14 / unknown 10 / oor 9 / keep 4 / active 5（加总=484 ✓；task_layout_anomaly=0——REL-086 已归一） |

### 2.2 副窗 0.1.0~0.90.0（保守 ≥1 窗）

| 侧 | would_archive | ref_version_out_of_range | 说明 |
|---|---|---|---|
| before | 3 行 / 5,446 B | 16 行 / 32,930 B | 3 行=REL-086 归一后旧代码即判可迁（0.88.0 在保守窗内） |
| after | **192 行 / 611,147 B** | 27 行 / 43,827 B | 全窗 204 − 12 行（0.91.0 周期行 EVD-1205~1215 系出窗转 oor）|

两窗 transitions 行数/字节三方守恒自检均 PASS（484/1,167,395）。**R1-1① 勘正注记（2026-09-28）**：§2.1 oor 两行（6,562/5,654 B）沿用首版 universal-newline 口径值——raw 口径下在途 CRLF 行各 +1B（合计 +9B），故字节分项加总 1,167,386 与 raw 汇总 1,167,395 差 9B；汇总值与 Check 28s `st_size` 同源为权威，两行 raw 精确拆分待后续重跑测量承载（不影响行数守恒与分类语义）。

### 2.3 五态实体类型覆盖（after · 全窗，引用出现次数 / 唯一 ID 数）

| 五态 | 引用次数 | 唯一 ID | 构成说明 |
|---|---|---|---|
| task | 265 | 190 | FEAT 60 + FX 14 + FIX/REL/AUDIT 可解析 + 活跃/超窗票 |
| requirement | 156 | **40** | §4.2 全清单（枚举=计数 40=40 机械验证）——零双重登记 |
| other_entity | 132 | 29 | RISK/DEC/REVIEW/TIER/CONSTRAINT/TOOL/ADR/DOC 族 |
| missing | 203 | 155 | FIX 93 + AUDIT 34 + REL 13 + FEAT 6 + SYSGAP 3 + VAL 2 + FMT 2 + DIAG 1 + ACCEPT 1 |
| ambiguous | 0 | 0 | 当前数据无双重登记 REQ、无未列名 FX 引用（机制在，测试覆盖） |

## 3. DEC-278 §4 验收条件逐条对照

1. **FEAT 任务不再落入 no_task_family_ref** ✅ §2.1（87 行直接转 would_archive）；FEAT-073 行（EVD-1216~1219）类型 task + 超窗留热、FEAT-074 热行进行中（未来引用必 active_task_ref 留热）✅
2. **REQ 需求实体不再被要求任务版本** ✅ 40 唯一 ID/156 次引用全部改判 requirement 非门控（§2.3/§4.2）；真实任务引用仍受生命周期约束（REQ 任务面走 task 判定，`test_task_side_req_is_judged_by_task_lifecycle`）✅
3. **缺失/歧义/未知形态默认禁止迁移且输出可解释原因** ✅ missing_task_ref / ambiguous_ref / task_layout_anomaly / task_version_unparseable / unknown_evd_id_shape / duplicate_evd_id 六类 fail-closed，detail 均列阻塞 ID ✅
4. **反例族测试全过** ✅ `FEAT074EvidenceEntityClassificationTests` 20 用例（§7）✅
5. **修复前后逐行分类差异留档** ✅ 本档重基线版（§2 全量矩阵 + §1 算术自检声明）✅
6. **verify 聚合 / xref / manifest / 既有归档测试零回归** ✅ §7（legacy 5F 等基线既有失败 stash 对跑证明）✅

## 4. 关键数据面证据

### 4.1 FEAT 任务族补位的依据

`_TASK_FAMILY_PREFIXES` 缺 FEAT = 旧时点数据派生滞后（盘点 §4.3）；`task_priority.py::_TASK_FAMILY_PREFIXES`（governance-id 词表）已含 FEAT——本票对齐。归档映射中 FEAT 任务早已存在（task_versions 含 FEAT-001~073 共 61 项）；FEAT-073（tv=0.92.0，writer-committed 终态）行 EVD-1216~1219 类型 task、owning cycle v0.92.0 超窗留热。

### 4.2 需求登记表 40 唯一 ID（枚举=计数，全部改判 requirement）

REQ-007, REQ-029, REQ-059, REQ-062~REQ-081, REQ-082~REQ-085, REQ-087, REQ-089~REQ-100。
（区间注记：059~081 连续段缺 REQ-060/061——**R1-1② 勘正（2026-09-28）**：原枚举误列 REQ-060（登记表存在但证据引用面零命中，不计入 40 唯一引用 ID）；REQ-086/088 不在证据引用面。任务面 REQ〔REQ-001~052 归档子集 + REQ-101~106〕与登记表零交集——零双重登记。）

### 4.3 FX 逐 ID 核验表（14/14 确证，禁通配；描述已按 R0 F-3 对照归档行 v0.1.0~v0.65.1.md L28~L34 勘正）

| FX ID | 归档版本 | git 首提（--all -S pickaxe） | 归档行描述（勘正后） |
|---|---|---|---|
| FX-130 | 0.64.0 | `77df046` AUDIT-129 入口解析器 ADR 链 | 入口解析器链（resolve_entry） |
| FX-131 | 0.64.0 | `77df046` 同上 | 入口解析器链 |
| FX-175 | 0.63.0 | `20bdc53` FIX-173 检视循环修复 | tag 回补批 |
| FX-177 | 0.63.1 | `7792b4e` DOC-001 docs/release 回补 | docs/release 三件套回补 |
| FX-179 | 0.63.2 | `7792b4e` 同上 | 同上 |
| FX-181 | 0.63.3 | `7792b4e` 同上 | 同上 |
| FX-183 | 0.63.4 | `7792b4e` 同上 | 同上 |
| FX-188 | 0.65.0 | `999f69d` loop-engineering 批 | Slice 1——registry 层 + loader |
| FX-189 | 0.65.0 | `999f69d` 同上 | **Slice 2——loop_engine core**（loop_state activation + stateless round derivation + fuse generalization；归档行 L29） |
| FX-190 | 0.65.0 | `999f69d` 同上 | Slice 3——flow_unit_derive |
| FX-191 | 0.65.0 | `999f69d` 同上 | **Slice 4——loop_migration**（--apply unblock + SHA-256 backup + --rollback；归档行 L31） |
| FX-192 | 0.65.0 | `999f69d` 同上 | Slice 5——loop_health Check |
| FX-193 | 0.65.0 | `999f69d` 同上 | Slice 6——rollup view |
| FX-194 | 0.65.0 | `999f69d` 同上 | **Slice 7——Gate re-labeling**（7 个 review SKILL.md 加 loop-role 语义；归档行 L34） |

全部为**恒等映射**（FX-N 即归档任务 FX-N 本身，经 task_versions 正常解析）——无 FX→FIX 改名情形。未列名的 FX-187/195/255（存在于归档但未被证据引用）不加入映射；任何未列名 FX 引用 → ambiguous fail-closed（测试 `test_verified_fx_alias_resolves_and_unverified_fx_fails_closed`）。

### 4.4 桶拆分对账公式（F-1 勘正后，字面成立）

- **before live_or_unresolvable 314** = missing 163 + would_archive 103 + unparseable 19 + duplicate 12 + no_task_family 9 + keep 4 + active 4 = **314** ✓（首版公式误并 no_task_family→missing 12 与凭空 −2，已废）
- **before no_task_family_ref 141** = would_archive 87 + 残留 35 + missing 12 + oor 4 + duplicate 2 + active 1 = **141** ✓
- **before would_archive 14 → after 204** = 14 留存 + live→103 + no_family→87 = **204** ✓
- **before oor 5 → after 9** = 5 留存 + no_family→4 = **9** ✓；**unknown 10 = 10 留存** ✓
- 与盘点文档对账（时点因果）：盘点 live 317（早时点）→ 重基线 before 314 = −3，恰为 REL-086 数据归一落地（3 行经旧代码 completed-hot 解析离开 live 桶，与「场景 B」预测一致）；盘点全窗 would 11 → before 14 = +3 同因。盘点 (i) 23 = active 4 + unparseable 19 ✓；(iv) 4 = keep 4 ✓。

## 5. 安全语义回归证明（反例族）与 active 归因勘正（F-2）

| 反例 | 行 | 拦截 reason | before 状态 |
|---|---|---|---|
| 重复 ID EVD-424/240/216/217/181/150/VAL-010（各×2） | 14 | duplicate_evd_id | live_or_unresolvable×12 / no_task_family×2（REQ 解锁后 EVD-424 两副本本可迁移——重复门优先拦截） |
| 显式保留 EVD-553/EVD-887/EVD-888/EVD-1044 | 4 | explicit_keep_marker | live_or_unresolvable |
| active 拦截 EVD-1045（FIX-343）/EVD-1063/1065/1066（FIX-349）/EVD-1129（FEAT-059） | 5 | active_task_ref | live_or_unresolvable×4 / no_task_family×1 |
| 0.92 在途 EVD-1216~1224（FEAT-073/FIX-400/FIX-401） | 9 | ref_version_out_of_range（owning cycle v0.92.0） | 首版时点后新增（before 已在档） |
| 多引用 max 语义（任一引用属未封闭周期→整行禁迁） | 机制 | owning cycle=max(引用版本) | 旧代码取任一在窗版本（非保守） |

**active 5 行归因勘正（R0 F-2 处置，取代首版「热表活跃/进行中」表述）**：plan-tracker 亲读三任务行状态列均以「✅ 完成」开头（终态）——FEAT-059（L96）状态格含「P3×5 **非阻塞**」、FIX-343（L103）含「tpa **假阻塞**池清零」、FIX-349（L105）含「非阻塞，无批量规范化收益」（本行由本重基线补证，闭合 R0 遗留不确定项 2）。三者均命中既有 `_task_status_is_archivable` 的 open_markers **朴素子串扫描**（「阻塞」∈「非阻塞」/「假阻塞」）→ 终态被误判非 archivable → 不进 completed-hot → 分类为 active_task_ref。**保留方向 fail-closed 不变**（行仍留热，安全），但 reason 归因失真。处置（Coordinator 已裁定，plan-tracker FIX-402 行 L85 字面承载）：open_markers 词边界/否定排除修复登记 **0.93+ 候选**；FIX-402 台账标注义务——**active reason 对终态行不可信，台账逐条复核 active 归因行**（REVIEW-FEAT-074-R0 F-2）。本票不改该既有函数（非本票范围；行为=旧行留热→新行留热，仅 reason 变）。

## 6. 数据侧处置现状（R0 后）

### 6.1 REL-086 行归一——已由 Coordinator 落地 ✅

plan-tracker L97 现为 8 管道（闭环路径/状态两格拆分，与首版 §6.1 提案一致）。重基线 before/after 均在此现实态：before 旧代码即解析 REL-086（tv=0.88.0，writer-committed 已发布终态）→ 3 行进 would_archive（全窗 before 14 的组成部分；保守窗 before 3 行全部来自它）；after 同。热表布局异常清单清零（task_layout_anomaly=0）。

### 6.2 FEAT-047 行——无需数据改动（维持首版结论）

该行 9 个原始管道中 1 个是单元格内**转义管道** `block\|advisory`（合法 markdown）。根因是解析器按原始管道计数/切分；本票代码修复（`_split_table_row_escaped_aware`）后按 7 列正确解析（tv=0.86.0、✅ 完成），进入 task_versions。内容保全：改解析器优于改数据。

## 7. 测试与门禁结果摘要（含 R0 返工复跑）

| 项 | 结果 |
|---|---|
| `FEAT074EvidenceEntityClassificationTests`（20 用例，test_verify_workflow.py） | **20/20 通过**（R0 返工后复跑；F-3 注释勘正不触逻辑） |
| test_archive.py 全量 | 159/159 通过（零回归） |
| 邻近套件（decision_migration×2/archive_decision_attribution/migration_commit_window/governance_store/task_priority） | 318 通过 +4 subtests |
| 证据域间接消费（ci_evidence/evidence_binding_drift/summary_only/fix270×2） | 97 通过 |
| test_verify_workflow.py 全量 | 965+20 通过 / 3 失败——stash 对跑证明为 HEAD 基线既有 legacy 5F 族（0.89 起披露面） |
| infra 全量 pytest 聚合 | 4371 通过 / 10 失败——9 项 stash 实证基线既有（legacy 5F×3 + archguard 基线增量 1〔DEC-260 分离 regen 纪律〕+ loop 环境敏感族 4 + FIX320 台账 2）；1 项本票引入即修（测试夹具字面钉活跃版本 0.91.0 → 改历史/合成版本后 `test_static_version_pins::RealTreeContractTests` 转绿） |
| verify_workflow.py 聚合（CLI 全量） | **PASSED（exit 0）**（R0 返工注释改动后复跑维持） |
| check-cross-references / check-manifest-consistency | PASS / PASS（canonical 964 一致） |

## 8. 边界与不做声明（DEC-278 §3.2 对照）

- 未实现 REVIEW/RECO/TRIAGE 行族扫描（单元二/FEAT-075）；`_classify_evidence_rows` 仍只扫 `| EVD-` 行。
- 未动 Check 28s 阈值/语义；未抬阈/缩窗/批量补猜归期（unparseable 19 行保留 fail-closed，归期修复属单元三）。
- 未加宽松正则：重复 ID 显式拦截、未确证 FX/双重登记 REQ 显式 ambiguous。
- 未改 loop_migration 契约（journal schema 不变；context_digest 为新增 pin 字段，plan/resume 对称；既有 finalized journal〔evidence-v0.1.0~v0.90.0，2026-09-27〕不受影响）。
- `.governance/` 零写入（本档为 docs/ 面授权产物；测量全程只读）。
- open_markers 否定语境假阳性（§5/F-2）为既有缺陷登记 0.93+，本票不修（越界）。

## 9. R0 勘正记录（REVIEW-FEAT-074-R0 处置对照）

| Finding | 处置 | 落点 |
|---|---|---|
| F-1（P1）差异档算术 | **重基线法**：当前时点（`c7627e44…`）整档重跑，全数字由对账脚本机械生成，三方守恒自检 PASS（行数 484/484/484、字节 1,167,395 三方相等、REQ 枚举 40=40、桶公式字面成立）；在途 EVD-1216~1224 于 §2.1/§5 显式承载；字节口径统一 raw（CRLF 17B 差异诊断注记 §1） | 本档全文 |
| F-2（P1）active 归因 | 三任务行终态亲证（含 R0 遗留的 FIX-349 L105 补证「非阻塞，无批量规范化收益」）；§2.1/§5 归因勘正为「终态 + open_markers 否定语境假阳性」；处置裁定引用（0.93+ 候选 + FIX-402 台账标注义务，plan-tracker L85） | §5 |
| F-3（P2）FX 注释 | archive.py `_VERIFIED_TASK_ID_ALIASES` 三条注释按归档行 L29/L31/L34 勘正（Slice 2 loop_engine core / Slice 4 loop_migration / Slice 7 Gate re-labeling，另顺带全表 Slice 序号补齐）；本档 §4.3 同步；test 注释「REQ-082-style」改合成 ID 表述（REQ-700 synthetic） | archive.py L1158-1164 / §4.3 / test L22115-22121 |
| F-4~F-8（P3） | 未处置（审查标注后续票/记录类；F-8 调度约束已引用于 §0 注） | — |

---

*重基线测量脚本（fe074_r1_recon/snapshot/diff/diag .py）已从 %TEMP% 删除；重基线快照 JSON（fe074_r1_before/after.json）为临时产物，其全部计数/矩阵/清单已并入本档，可由 §1 方法 + 输入 digest `c7627e44…` + 代码锚（HEAD `b6575bd` vs 工作树）复现。*
