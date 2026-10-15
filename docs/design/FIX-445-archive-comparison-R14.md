# FIX-445 — R14 归档闭合两方案比较设计与 R13 附带条件修订（DEC-348；R13 frozen delta）

```json
{"role":"Architect (producer, not reviewer)","round":14,"scope":"archive_closure_comparison_per_dec348",
 "supersedes":"R13 §4.1 引理全称（收窄至 P1/P2 谓词集）、§4.2/4.3「闭合唯一路径=infra 扩围」假两难、§3.2 预检作用域句与 §3.3 竞态首支、§5 site_evidence 元素格式（N1）；A 方案采纳时另涉 §5 计数域更名（见 §6）",
 "product_implemented":false,"product_authorized":false,"migration_authorized":false,
 "self_approved":false,"implementation_ready":"pending independent R14 review; both plans carry unproven aspects",
 "fix445_status":"blocked (unchanged)"}
```

- **日期**: 2026-10-14（Coordinator 供应）。**唯一写面**：本文件。R13（192 行，SHA `3b31304a…`，closeout 九件冻 SHA match/trust CLEAN）与 R12/R11/两产品全部冻结不改。
- **授权（DEC-348）**：仅比较设计（A 原 two-file 内 live+archive 联合计数 vs B infra 归档执行门）+ 修 R13 W1/W2/N1 + 同 Reviewer 一次 R14；零 R15、零产品/registry 生效/迁移/风险接受/白名单/提交发布/真实 HOME。

## 0. 基线与不变项

R13 为 frozen 基线：六 context 与九 cp 数按 R13 §2.2 沿用（本文不复制）；冷 source 样例零改；条目类型/version 维持 proposed。不变项重申：原三行零编辑；四任务源非零/hashbytes/latest/zero skipped/RC0；12 攻击与 R8/R9 反例逐例拒绝；GuardG/T2/M5/R3 零改动；B3 五 env；CPU27.8/CLI36/434339/32MiB/1500 不重测不放宽；原源资格 NOT_ESTABLISHED、迁移未授权；产品 64tests/1FAIL、CodeR6 BLOCKED/3、full 18/exit1、隔离 witness FAIL（写者 unknown）全部不改绿。

## 1. 本轮实际输入与源码核验清单

**治理件实读 4**：`docs/reviews/review-FIX-445-DESIGN-R13.md`（52 行，AWN/0+W-R13-1/2+N1/N2+随附条件三条）；`.governance/reports/FIX-445-R13-closeout-and-scope.md`（57 行，A/B 并列材料与推荐卡）；`.governance/incidents/FIX-445-R13-closeout-check.json`（134 行）；R13 终稿 192 行（本 agent 会话上下文，deliver 后未再触碰）。Coordinator 单源事实：DEC-348/op `0d43b430…`、goal rev6 active/armed（runtime 拒改 text——如实，不称 rev7）、bridge RUNNING rev4/round10of16/wall 77272/129600 safe、R13 机录 seq51 txn `txn-56ad77f…`、原 Reviewer 转录逐字零差异。

**infra 源码只读核验（本轮一手，零执行）**——先 glob 定位 7 个 archive*.py，再 grep 全函数测绘（171 命中），随后按下表精读命段（禁止以函数存在冒充机制已证）：

| 文件 | 实读行段 | 获证事实 |
|---|---|---|
| `infra/archive.py` | :608-797, :895-1024 | `migrate_by_version` 编排（tasks 腿直接 write_text :755；evidence 腿经 :535 `_run_entity_migrations` 派发）；`verify_archive_integrity`(:895) 三查=索引引用存在/无孤儿/逐类计数交叉；`rebuild_index`(:1018) 索引=纯派生物，重建不造数据 |
| `infra/archive_migration_engine.py` | :85-204, :667-866, :981-1170 | `_write_archive_file`(:85) 普通 open/write；`_make_incremental_archive_filename_impl`(:135) 重复范围独立增量文件、回滚按文件粒度、永不覆写异源内容；FIX-417 五阶段（finalized/resume 世界判定按 committed→input→diverged 序）；`_evidence_apply_commit`(:981) 单线性化窗：`_big_table_target_lock` 下 **archive→hot→finalize** 序+双 digest 复核+`archive_target_conflict`/`hot_table_diverged` 拒绝+原子写；journal/batches 断点续迁+游标-工件一致性校验 |
| `infra/archive_entity_migration.py` | :330-449 | `_migrate_evidence_impl`(:330) **遗留非事务路径**：分类→`_write_archive_file`(:437 普通 write)→`elog.write_text`(:438 直接热重写)——无锁/无 journal/两写间崩溃=行双在（archive+hot）窗口；EVD 行两形态（plain+compound `EVD-FIX-247`）共享 `_EVD_ID_SHAPE_RE`；分类单源 `_classify_rows_for_family` |
| `infra/archive_indexing.py` | :200-359 | `_extract_evidence_from_archive_file`(:218)：`| EVD-` 行+parts[2]=task 列，damage-tolerant `errors="replace"`（仅 ID 提取面）；家族抽取(:251)同形；`_extract_decisions/risks`(:282/:310) 单源口径教训（双 regex 漂移曾致 Check3 死循环）；非结构化归档前缀识别(:346) |
| `infra/governance_store.py` | :715-834 | **hot∪archive 读先例**：`_scan_archive_ids`(:715) `rglob("*.md")`+`errors="replace"`+regex 抽 ID；`_next_row_id`(:738) hot∪archive 碰撞拒（`cross_record_violation`）；`_validate_row_shape`(:756) 写前写后同校验器；`_post_write_append_check`(:793) 写后重读+前缀比对（并发写披露不自动恢复） |
| `infra/archive_cli.py` / `archive_verdicts.py` / `archive_parsing.py` | 函数测绘（grep）+按需片段 | CLI 入口族与分类/verdict 单源模块实存；未全文读段如实标注，不据其下机制结论 |

## 2. R13 附带条件修订（W1/W2/N1——随 R13 §5 随附条件②）

### 2.1 W-R13-1：引理收窄（撤回全称）

R13 §4.1 引理**仅在以下谓词集与读面内成立**：live 批计数、clause/邻接上下文字节、载体（P2 面）内容——即 P1/P2 读面内不闭合。**反例（R13 审查 BR-W1 给出，本设计采纳为方案 A）**：引擎新增 `archive/evidence/` 读面做 live+archive 联合计数——偷位世界（原出现已归档+live 复本）总数 N+1≠N 可分。撤回「运行时层可证不可闭合」全称与「闭合唯一路径=infra 扩围」表述；G1/G2 裁决材料的并列呈报条件由本文 §6 比较表履行。

### 2.2 W-R13-2：预检作用域与竞态叙事修正

- **作用域**：notfile bash 预检（`[ -e ]∧[ ! -f ]`）**仅在 registry 触发的 spawn 决策臂（P-A/P-C）运行**；P-B（record 非空→恒 spawn）**不跑 bash 预检**，目录/缺席分类由引擎权威给出（IsADirectoryError→`registry-notfile`；ENOENT→absent）。
- **竞态叙事**：删除 R13 §3.3 不可达首支「预检 notfile→被换普通文件→引擎 loaded」（notfile 预检即阻断、无后继引擎）。修正后的可达竞态闭集（spawn 决策臂内）：预检 file→open 被删→引擎 absent；预检 file→open 被换目录→引擎 `registry-notfile`；预检 notfile→BLOCK 无引擎。逐场景矩阵（R13 §3.3）其余各行不变，P-B 列目录格由引擎分类（原本如此）——两臂判定恒一致（notfile 硬断/absent 惰性）。

### 2.3 N1：site_evidence 元素格式（与 adjudication 同 schema）

`site_evidence[]` 元素 = **与 `adjudication` 字段同格式的 typed 裁决引用**：非空 `DEC-<n>` 串（R11 §6.3.4 起 adjudication 的既定纪律——hook/登记侧仅非空+格式校验，不解析 DEC 内容）。运行时 `registry-schema` 检查：每元素匹配 `^DEC-\d+$` 且互异；**不发明新 writer 接口**（写入仍属未来经裁决的登记程序）。重申（R13 N2 边界）：长度/非空/互异是结构一致性，**不构成逐 site 对应性证明**——对应性=登记程序机检义务（R13 §2.4），运行时不可验。

## 3. 方案 A — 归档感知运行时联合计数（原两产品文件内；未实施提案）

### 3.1 机制

引擎新增第三读面 **P3=archive evidence 面**：`.governance/archive/evidence/*.md`（sorted glob，仓内 realpath）。计数对象=**结构化 EVD 归档行**（行以 `| EVD-` 起、parts[2] task 列含当前 task——沿用 `_extract_evidence_from_archive_file` 的解析形状 :229-242），在其中做三元组逐字匹配，得 `a(T)`。**联合守卫 C4″（A 采纳时取代 C4′）**：`live c(T) + a(T) == site_count_total`（登记时对 live+archive 双面机测的总数；字段由 R13 `live_site_count` 更名扩域——见 supersedes）。

### 3.2 计数对象与异常闭表（拒方向全列；与 W1 语料截断语义**相反**——P3 不允许静默截断）

| 项 | 规范 |
|---|---|
| 计入 | 仅 `archive/evidence/*.md` 内 `| EVD-` 行（task 列匹配）；EVD 两形态（plain/compound）同 `_EVD_ID_SHAPE_RE` 纪律 |
| 不计入 | `archive/index.md`（纯派生物——按索引计会双计）；tasks/decisions/risks 子目录；非结构化归档（narrative-/recent-completed- 前缀，:346-358）；标题/头部行；`evidence-{family}-*.md` 中非 EVD 行（家族行 `| REVIEW-` 等不匹配前缀，天然排除） |
| discover 顺序/去重 | 文件名 sorted；**行级不去重**——同一三元组在多归档文件/多行出现即多计（正常运维下移动语义不产生重复：迁移=写档+热删；rollback=unlink+热恢复；增量文件只装新行。异常双在→总数膨胀→拒，fail-loud 即设计意图） |
| 纯 move 前提 | 正常归档=移动，总数不变（1→1）；复本增殖（偷位）→总数 N+1→**三元组全拒** |
| 合法 replay 重新裁 | 新 live 出现经逐 site 裁决后，登记程序对 live+archive 双面机测更新 `site_count_total`（例：归档原例 1+新 live 1→N=2） |
| `.governance/archive/` 或 `evidence/` 子目录缺席 | `APLANE=absent`，a(T)=0——合法前置态非故障（DIAG 可见） |
| 索引缺失/损坏 | **不影响计数**（计数直读文件不读索引）；索引面归 G2/verify 三查（:895）披露 |
| 单文件 >2MiB / 累计 >16MiB | ToolFault `archive-file-oversize` / `archive-plane-oversize` → **BLOCK**（部分扫描可能凑巧 ==N 造成假授予——**禁截断**，与 W1 语料「截断=诊断」语义严格区分：容量不足=拒，不当来源 skip 也不偷授豁免） |
| realpath 出仓/符号链接逃逸 | ToolFault `archive-path` → BLOCK |
| OSError / 严格 UTF-8 解码失败 | `archive-read` / `archive-decode` → BLOCK（**偏离** :226 `errors="replace"` 先例——该容忍仅适用 ID 抽取；字节精确三元组匹配须严格解码，差异已论证） |

DIAG 扩展：`APLANE=absent|ok|fault:<code> ASITES=<a(T)>`。

### 3.3 攻击面与残余（不以计数证原出现在场的界已换）

- 偷位（归档原例+live 复本）：总 N+1 → 拒 ✓（M15 在 A 内闭合）。M13（纯 append）：live N+1 → 拒 ✓（沿 R13）。位点流失（归档无复本）：live 0+archive 1==N，零 live 出现可豁免 → 资格自然失效 ✓。
- **残余（如实）**：攻击者直改归档件删除原例（或手工造档）→ 总数可复位 → 偷位成功——信任边界=「归档文件不被对抗性直改」，与「evidence-log 不被直改」同级（CH-1 类：git diff 可见、verify/重建漂移可检、审查可查）。**不声称闭合直改面**；检出辅助=G2/三查+`rebuild_index` 前后比对（:1018 索引纯派生）。
- 前提：归档行迁移保真（`_migrate_evidence_impl` :376-378 逐字保留行；R13 六值机检对 archive 行同样成立——登记程序机检域含 P3）。

### 3.4 成本面（设计上界 vs 未实测，分列）

新增 IO/延迟面：每次 spawn-armed 运行读 archive/evidence 全量（当前该目录体量**未测**——本轮不读热面不假实测）；上界=文件数 ×2MiB、Σ16MiB 硬拒。驻留=逐文件「读-匹配-释」（沿 R13 §6 逐条释放纪律）。原门 CPU27.8/CLI36/434339/32MiB/1500 不放宽；**实测为实现票强制项**（含 A 拒绝路径红绿）。复杂度=线性扫描+码点匹配，无回溯。

## 4. 方案 B — 权威侧归档执行门（infra 扩围；**未授权提案，不实现**）

### 4.1 真实写入口与事务事实（源码钉死）

evidence 归档**两条真实写路径**：① `migrate_evidence_resumable_impl`（engine :1022-1170，FIX-417 可续迁：journal/batches/stage/compose/apply，`_big_table_target_lock` 下 archive→hot→finalize，双 digest 复核，崩溃可恢复/幂等）；② `_migrate_evidence_impl`（entity :330-439，遗留路径：`:437` 普通 write 档 + `:438` 直接热重写——**无锁无 journal**，两写间崩溃=行双在窗口【预存在属性，非门引入，如实披露】）。tasks 腿（archive.py :608-764）不涉 evidence 行。`migrate_auto`(:1405) 复用同腿。rollback(:1074) 按文件粒度 unlink+热恢复。

### 4.2 G1 门语义（两写路径**均须**设门；拒绝先于任何写）

- **规则**：分类得候选行集后、任何写之前，对每候选行文本做活跃条目三元组匹配；命中**活跃**（active）条目 → `BigTableMigrationError({code:"mention_registry_active_site"})` 拒绝整次迁移（FEAT-061 fail-closed 风格，CLI 非零退出——沿 :199-204 纪律）。插入点：①engine plan 阶段（journal 写前）；②entity `:411` archived 列表得后、`:437` 写前。两点缺一=旁路（单点风险，测试钉死）。
- **顺序与回执（重锚/失活证明）**：合法序列=**先**登记程序 deactivated/re-anchored（registry 状态变更记录+`DEC-<n>` 引用+live 机测回执工件），**后**归档——门在归档时读到非活跃即放行。无跨文件事务需求（拒绝发生在任何写前；「先失活后归档」的两步间崩溃=条目非活跃而行仍在 live → 联合/live 计数漂移 → 运行时守卫保守拒，完成归档后自愈）。回执验证者=G1 门自身（机器读 registry 状态+变更记录）；授权对象=registry 条目（非行/EVD/hash 名单）。
- **G2（一致性健康面，非门）**：`verify_workflow.py` 检查面：活跃条目 live（或 A 采纳时 live+archive）计数==申报；不等→FAIL。**G2 不以 count==N 证明已裁原位保全**（R13 N2 确认的盲区维持）——G2 是漂移观测，非对应性证明。
- **最小未授权写面提案**：engine+entity 两插入点（各 ~一函数+拒绝码）+ registry 只读 helper + CLI 文案；G2 另涉 verify_workflow.py。全部 infra=**需用户另裁**（`guard_design_boundary`），本轮零实施。

## 5. 预定义评价标准（先列后比）

① 安全完整性：M15 闭合至何种残余界、不弱化任何原门/攻击拒绝；② 授权范围：是否需未授权扩围；③ 成本可测性：新增面有界+实测待办明确；④ 原源与资源门维持（NOT_ESTABLISHED/CPU/CLI/32MiB/1500 不动）；⑤ 回滚：实现可逆路径；⑥ 可审计性：诊断/回执/独立复核面。

## 6. 同表比较（A/B 均有未证项——不强选；推荐=提案非裁决）

| 维度 | A 联合计数（界内） | B 权威门（infra） |
|---|---|---|
| M15 闭合 | 偷位总 N+1 拒；**残余=归档件直改**（CH-1 级） | 门拒归档活跃位点；**残余=G1 旁路/回执伪造**（治理写面 CH-1 级）+ G2 对完成偷位盲 |
| 授权范围 | **原两文件内**（引擎 P3 读面）——零扩围 | infra 三件+（G2）verify——**须另裁** |
| 成本 | 每次 spawn-armed 读档面（Σ≤16MiB 硬拒）；**未实测** | 运行时近零；开发/治理面成本前置 |
| 原门维持 | 不触碰（读面增量）；实测待办 | 不触碰；G2 为新增健康面 |
| 回滚 | revert 两文件即净（无数据面） | G1/G2 独立 revert；门存在期间的行为面 |
| 可审计 | `APLANE/ASITES` DIAG+登记机检含 P3 | 拒绝码+回执工件+G2 报告 |
| 组合 | **A+G2（Alt-C）**：A 闭合运行时+G2 观漂移；G1 降为卫生项（A 下归档活跃位点安全：总数不变、live 豁免自然失效，见 §3.3） | B 单用（Alt-B）：运行时成本敏感时的替代 |

**条件性推荐（非最终架构裁决）**：若实现票实测证实 A 的 IO 面可受（界内拒绝语义可测），**Alt-C（A+G2）** 为首选——最小授权面+闭合至直改界+可观测；若实测超界且不可优化，退 Alt-B。两案均含未证项（A=成本未测；B=扩围未授权+旁路/回执信任），**任何未证项落空即回本表重裁**。决策权在用户。

## 7. 替代与蓝军（标准=§5+R13 §1–16 沿用）

**备选（≥2，公允）**：Alt-A（界内联合计数）/ Alt-B（权威门）/ Alt-C（A+G2 组合，§6 推荐）/ Alt-D（维持开放=R13 现状，M15 继续阻断 readiness——仅用于证「不作为」亦是显式选项）。

| # | 蓝军挑战 | 响应 | 残余 |
|---|---|---|---|
| BT-R14-1 | A 的档面 IO 放大（大档库×每提交） | §3.2 预算硬拒（fail-closed 非截断）+逐文件释放；实测票 | 未实测（如实） |
| BT-R14-2 | 直改归档件复位计数（A 残余） | 信任界=CH-1 级（diff 可见+三查/重建漂移检出）；不称闭合 | 开放（界明确） |
| BT-R14-3 | B 的双写路径旁路/遗留非原子窗 | 两插入点+测试钉死；遗留窗为预存在属性（:437-:438），披露不隐 | 单点纪律 |
| BT-R14-4 | 假两难复发（以成本否定可行性） | §2.1 引理已收窄；成本=实测票条件，非可行性否定 | — |
| BT-R14-5 | 计数域语义漂移（live vs live+archive） | §6 表列明各案计数域；A 更名 `site_count_total` 入 schema 提案；登记机检域随之扩 P3 | — |

## 8. NFR / 回滚 / ADR delta

- NFR：A 新读面上界（2MiB/文件、16MiB/spawn、严格解码、逐文件释放）；B 近零运行时+治理面前置；原门全部不重测不放宽；实测票=实现前置条件。DIAG 增 `APLANE/ASITES`（A）。
- 回滚：A=revert 两文件（无数据面）；B=G1/G2 独立 revert（未实施无从回滚，提案态）；组合案按件独立。
- ADR delta（proposed，Coordinator 写回）：标题=ADR-FIX-445-R14 — 归档闭合 A/B 比较与 R13 附带条件修订（引理收窄/预检作用域/N1 格式）；决策=呈报 Alt-C 条件推荐，未裁决未实施；备选=Alt-A/B/C/D；影响=两文件（A）或 infra 三件+verify（B）——均未授权；后续=独立 R14→用户架构裁决→（若裁）实现票含实测；可逆=是。

## 9. 未解与自检

**未解（如实）**：①M15 在本设计后仍是「待架构裁决」非已闭合（A/B 均未实施未实测/未授权）；②A 档面成本未实测；③B 扩围未授权且 G1 旁路/回执信任=CH-1 级；④A 残余=归档直改界；⑤原源 NOT_ESTABLISHED、迁移三问、ordinal live 机检、原门实测全部沿 R13 §10 待办；⑥环境 FAIL 事实（隔离 witness 写者 unknown/冻结 M5 命中/full 18/exit1）不归本设计不称已修。

**自检**：备选 4≥2（§5 标准先列）；蓝军 5≥3；ADR 字段全；无环（P3 消费既有候选遍历；B 插入点为界外提案不入依赖图）；源码结论全部带文件:行号锚定，无凭函数名断机制、无引用不存在接口；六 context 不复制沿 R13；零 shell/probe/测试/安装/热面读/治理写/子 agent/用户交互；治理件 4+源码 5 文件 9 读段一手实读（§1 表）。约 14 步/32 建议。
