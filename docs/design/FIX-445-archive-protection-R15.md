# FIX-445 — R15 保护设计：枚举错误传播与资源界、归档不覆写、apply 末检与统一口径（DEC-349；R14 frozen delta）

```json
{"role":"Architect (producer, not reviewer)","round":15,"scope":"archive_protection_per_dec349",
 "supersedes":"R14 §3.2 P3 闭表（扩容为 v2：错误传播枚举+预算+双相稳定性）、§3.3「迁移保真」无条件前提（撤回→条件化）、§4.2 G1（增 apply 锁内末检）、§6 比较表安全行（按 R14 随附条件①更新）；R14 其余沿用",
 "product_implemented":false,"product_authorized":false,"migration_authorized":false,
 "self_approved":false,"implementation_ready":"pending independent R15 review; all fixes are unauthorized future write-planes",
 "fix445_status":"blocked (unchanged)"}
```

- **日期**: 2026-10-14（Coordinator 供应）。**唯一写面**：本文件。R14（134 行，SHA `a80a768f…`）、R13/R12/R11、两 canonical 产品全部冻结（R14-closeout 11 件 SHA match/trust CLEAN）。
- **授权（DEC-349）**：仅本保护设计一次修齐 W-A1/W-A2/W-B1+两组 NOTE+口径/回滚推演；same Reviewer 一次 R15；零 R16、零产品/registry 生效/迁移/风险接受/白名单/提交发布/真实 HOME。

## 0. 基线与不变项

R14 为 frozen 基线；本文件只替换 supersedes 所列，其余沿用（六 context 沿 R13 §2.2，不复制；冷样例零改）。不变项：原三行零编辑；四任务源非零/hashbytes/latest/zero skipped/RC0；12 攻击与 R8/R9 反例逐例拒；GuardG/T2/M5/R3 零改动；B3 五 env；**CPU27.8/CLI36/434339/32MiB/1500 原门保持——本设计全部界值为设计界未实测，不凭界值声称 NFR 已证**；原源 NOT_ESTABLISHED、迁移未授权；产品 64tests/1FAIL、CodeR6 BLOCKED/3、full 18/exit1、隔离 witness FAIL（写者 unknown）不改绿。

## 1. 本轮实际输入与源码补证

**治理件实读 3**：`review-FIX-445-DESIGN-R14.md`（64 行，AWN/0+W-A1/W-A2/W-B1+N-A3/A4+N-B2+随附条件①②③）；`FIX-445-R14-closeout-and-scope.md`（64 行，呈报补充表+四项可审修正方案）；`FIX-445-R14-closeout-check.json`（150 行，11 件冻/锁 0/0）。Coordinator 单源事实：DEC-349/op `a9472056…`、R14 机录 seq52/txn `84a05273…`、goal rev6 active/armed（auto 轮 edit 被 runtime 拒，如实）、bridge RUNNING rev4/round11of16/wall 81592/129600 safe。

**源码补证（本轮一手，接 R14 读段）**：`archive_migration_engine.py:205-334`——`_atomic_write_text`(:217-243) 委托 `governance_store._atomic_write_bytes`（temp+fsync+os.replace+dir fsync；fallback mkstemp+replace）；`_big_table_target_lock`(:245-253) 委托 `governance_store._TargetLock`（热表互斥，apply :987 所用即此锁）；`_migration_load_journal`(:298-320) 坏件即拒纪律；`_migration_state_dir_impl`(:274) state dir 仅 .json 不入索引视野。**最小写面确认（glob 实测）**：`infra/tests/test_archive.py`、`test_archive_decision_attribution.py`、`test_migration_commit_window.py`、`test_governance_store.py` 实存——W-A2/W-B1 的测试落点=既有 `test_archive.py`（或新 fixture 测试文件=未授权提案）；方案 A 落点=`hooks/commit-msg`+`tests/test_hooks.py`（冻结在案）。

## 2. W-A1 — P3 面错误传播与资源预算（闭表 v2，替换 R14 §3.2 异常表）

### 2.1 检查顺序（规范序；每步故障=整次 ToolFault→BLOCK，无部分源结果）

1. **目录判别**：对 `.governance/archive/evidence` 用显式 `os.scandir`+errno 分类——ENOENT/ENOTDIR → `APLANE=absent`、a(T)=0（合法前置态）；PermissionError/其它 OSError → `archive-plane-enum` 拒。**禁止 glob 容错语义**（glob 静默 `[]` 把「在场不可枚举」伪装成缺席——与 `governance_store:722-726` OSError-continue 先例明确分界：该先例属 ID 容错扫描，本面是资格判定输入，不可容错）。
2. **枚举与布局**：仅收 `*.md`（`.gitkeep` 等非 md 忽略，沿 verify :926-927 先例）；**出现子目录 → `archive-plane-unexpected-dir` 拒**（三处写路径布局均为扁平：engine :1168/legacy :426-432/verify :923-928——子目录=布局异常，保守拒）。names 排序。
3. **filecount 界**：>512 → `archive-plane-filecount` 拒。
4. **逐文件**：realpath 仓内（逃逸→`archive-path`）→ open OSError→`archive-read` → 严格 UTF-8 解码失败→`archive-decode` → 单文件 >2MiB→`archive-file-oversize` → 流式逐行（驻留=单行+计数器）；单行 >1MiB→`archive-line-oversize`。
5. **累计界**：Σbytes>16MiB→`archive-plane-oversize`；Σlines>1,500,000→`archive-plane-lines`；时间预算 `time.monotonic` 每文件检查点 >5s→`archive-plane-time`。
6. **双相枚举稳定性**：扫描完成后二次枚举（names+sizes）；snapshot 变化（增/删/size 变）→ `archive-snapshot-unstable` 拒。

### 2.2 资源预算表（全部=设计界，未实测；实测票与原门共同验收）

| 界 | 值 | 说明 |
|---|---|---|
| 文件数 | ≤512 | **采纳 Reviewer 候选值为设计界**——非实测/非既定配置，不据此声称 CLI36/1500 已保证 |
| 单文件 / 单行 | ≤2MiB / ≤1MiB | 行为单行；超=拒不截 |
| Σbytes / Σlines | ≤16MiB / ≤1.5M | 整次拒，无部分计数 |
| 时间 | ≤5s/spawn | monotonic 检查点 |
| 驻留 | 单文件流式+单行缓冲 | 无全量驻留 |

### 2.3 枚举竞态的方向性闭合（不以 CH-1 免除机制自身竞态）

双相枚举把活跃窗收窄到「二相枚举后、判定前」。该窗内变化的**方向分析**：窗内删除旧档 → 已计入 → 总数偏高 → 保守**假拒**；窗内新增档件 → 未计入，但偷位前提下的「原例」必在枚举时已存在（历史归档），新增件不承载原例 → 总数不因新增而低于真值所需的拒绝阈 → 判定仍拒或不劣化。故残余竞态**恒为假拒方向，无假授窗口**——以双相枚举+方向论证闭合，非以信任假设闭合。

### 2.4 完整性 pin ≠ hash 名单授权（逐字分清）

registry/回执可记录载体或归档件 SHA-256 作**完整性 pin**（漂移检测/审计/拒绝方向使用——发现变更→拒资格或触发重锚裁决）。这与被禁的「以 task/EVD/整行/hash/ID 名单**授予**来源资格」不同：pin 从不作为豁免依据，只用于 fail-closed 检测。两用不得混同，实现票红测各证一例。

## 3. W-A2 — legacy 归档写保真修正（撤回 R14 §3.3 无条件前提）

### 3.1 缺陷重述（源码锚定，R14 审查 W-A2 确认）

「归档保真」仅 resumable 路径成立：never-overwrite 命名（:135-174）+ existing-target digest 拒（:1000-1009）+ 原子写（:1015/:1017）。**legacy `_migrate_evidence_impl` 直接构造 base 名 `evidence-vX-Y.md`（entity :426-427）且 `_write_archive_file` 为 `open("w")` 截断写（:437）**——同范围二次调用（legacy 中断后重跑=其唯一恢复方式）以新行集覆写旧档 → 既有归档行**非对抗性静默丢失** → a(T) 下计 → 偷位窗口在普通运维下打开。此为活性缺陷（发现即须有修正裁决，不登记以后）。

### 3.2 单一修复策略（全部复用真实 helper，零编造接口）

- **命名**：legacy EVD 腿目标名改经既有 host-routed `host["_next_evidence_archive_filename"]`（engine :167-174 → `_make_incremental_archive_filename_impl` :135-165，never-overwrite 增量命名）——与该函数非 EVD 家族腿已走 `host["_next_family_archive_filename"]`（entity :430-432）的既有形态对齐。**不是**「调了生成名仍普通 w」——写入面同步换（下条）。
- **写入**：`_write_archive_file` 的 `open("w")` 替换为：目标不存在 → **O_CREAT|O_EXCL 独占原子创建**（新 ~6 行小原语；EEXIST → 读现内容：digest 与本次内容相等 → 幂等跳过（继续热腿）；不等 → `BigTableMigrationError archive_target_conflict` 拒绝，**旧字节原样保留**——语义沿 engine :1000-1009）；创建经 `_atomic_write_text`(:217) durability 纪律（O_EXCL 建临时终名或建后 replace 前保持独占语义——实现票二选一并测试）。**单一策略**：never-overwrite 名 + 存在即判（等=幂等/异=拒），不做 append 未知旧件。
- **热删顺序**：保持 archive-先-hot-后（:437→:438 既有序）。

### 3.3 并发/TOCTOU/中断重试/恢复（不靠 rebuild_index 复原已丢源）

- 并发/TOCTOU：O_EXCL 创建原子排他；两并发迁移同目标 → 一胜一转 existing-target 判定（等=幂等/异=拒）。
- 中断重试：档已写、热未重写（崩溃窗，预存在 :437-:438 属性——修正不消除该窗但改变其后果）→ 重跑经 never-overwrite 得**新**增量档（同批行）→ 行双在（档×2+热）→ 联合计数膨胀 → A 守卫保守拒（fail-loud）；**恢复程序（规范）**：对双在行一次性对账（删除冗余增量档或待下次合法迁移消化）——对账=数据操作需用户授权，标未授权；**rebuild_index 不复原行数据**（索引纯派生 :1018-1024，重建只恢复视图）。
- 修复前/后前提改述：A/B 的「归档保真」前提=「resumable（既有已证）+ legacy（按本节修正并经测试票证明后）」——修正实施前，legacy 腿不得作为保真前提（呈报比较表按此口径）。

### 3.4 最小未授权写面提案（不实施）

`archive_entity_migration.py`（:426-437 命名+写入两处）+ `archive_migration_engine.py`（O_EXCL 原语若共享则 :217 旁）+ 既有 `tests/test_archive.py` 增四情形（同范围二次迁移/中断重试/旧字节保留/增量名冲突，仓内隔离 fixture）——全部 infra=**需用户另裁**；若测试需新 fixture 文件，同属提案。本轮零实施零执行。

## 4. W-B1 — apply 锁内 registry 末检（消除 G1 的 plan→resume TOCTOU）

### 4.1 锁、时机与复检语义（明确到「同哪把锁、何时验证」）

- **锁**：`_big_table_target_lock(elog)`（:245-253，即 `governance_store._TargetLock` 热表锁——apply :987 所用同一把）。
- **时机**：`_evidence_apply_commit` 内、热表 digest 复核（:988-999）之后、**任何写之前**——「最后写前资格复检」，为该锁内的最终守卫步。
- **复检语义**：registry 增 `revision`（单调整数，权威写 +1，入 §2.4 pin 纪律）。plan 门记录当时 revision R1；apply 锁内重读 registry：缺席=无活跃条目→放行（与运行时 inert 语义一致）；不可读/坏件→`mention_registry_unreadable` 拒；revision R2≠R1 → 以**现值活跃集**对已分类候选行重跑三元组匹配（成本=候选行数×活跃条目数，有界）；命中活跃→`mention_registry_active_site` 拒。registry 状态由此进入 pinned 世界（journal 记 R1/R2 与复检结论）。
- **registry 写者协同（规范义务，双保险）**：①兜底主径=上述 apply 复检（任何 plan 后激活要么被复检拒、要么 apply 后由运行时联合计数守卫保守拒——两终点均 fail-loud）；②纪律辅径=未来登记程序在写 registry 前检查无未 finalized 迁移 journal（state dir :274-281 即检查面）。registry 写面本身=未授权未来面，其协同义务写入登记程序规范，不在本设计实施。

### 4.2 崩溃恢复/幂等/rollback 不绕门

- 拒绝发生在写前 → journal 未动 → 修复后重跑走既有 resume 世界判定（:667-702，幂等）。
- apply 后崩溃 → finalize 前重跑 → pinned digest 世界判定；已 finalize 迁移的行已离热表，后续新激活若指向已归档位点 → 运行时联合计数守卫保守拒直至重锚（真实新裁决，不从旧回执自授）。
- **rollback（:1074）不绕门**：rollback 只 unlink 档+热恢复，不产生新归档写 → 不经 G1（门管归档写不管恢复）；恢复后行回 live，资格由联合计数现值评估——机制上 (1,0,1)==N 即放行（rollback 恢复的世界与「从未归档」局部同构）；**审计义务（非阻断）**：rollback 涉及含登记位点的迁移时，登记程序必须产出 recount 回执（rollback 热恢复的逐字保真由其自身实现保证，不由本设计假设）——机制结果与审计义务分开陈述。

## 5. NOTE-1 — 多 ID 成员精确匹配（live/archive/G1 共用单源谓词）

**谓词 `task_member(cell, task_id)`**：cell 按闭分隔符集 `[,，;；]`+空白拆分 → strip → token 集合（去重）；成员 ⟺ `task_id ∈ tokens`（**精确等值**；禁子串包含、禁整列等值）。G1 候选行、P3 归档行、（实现票后）live 计数共用此一源。

| 示例 cell（查询 FIX-445） | 判定 | 方向 |
|---|---|---|
| `FIX-445` | 成员 | — |
| `FIX-445,FEAT-097` / `FIX-445；REL-102` | 成员（拆分后） | 无漏计 |
| `FIX-44` / `FIX-4450` | 非成员 | **前缀碰撞免疫**（N-A3） |
| 空 cell | 非成员 | — |
| 含不可解析 token（如 `FIX_45!`）**且行文本匹配某三元组** | 计为潜在成员（计入 a(T)）+ 诊断 `taskcell-malformed` | 多计=保守拒向（宁假拒不假授） |
| `FIX-445,FIX-445` | 行计一次（token 去重） | — |
| 混合行（他任务+本任务） | 本任务成员即计入 | 成员性与他任务无关 |

**live 侧现状与对称化**：hook awk（:43）为单 cell 等值——多 ID cell 在 live 计 0、归档后计 1 的不对称（N-A3 指出）。规范：三处统一分词成员匹配；live 侧采用属两产品文件实现票（未授权）——期间不对称方向=live 漏计多 ID 行 → 总数偏低 → **假拒非假授**（安全向），availability 代价披露。四任务源提取（`task_evidence_lines`）零改动，四源门零 skip 不受影响。

## 6. NOTE-2 — 计数语义推演表（替换 R14 §3.3 攻击面行；G2 非 proof 重申）

| 情形 | live | archive | 总数 vs N | 判定 |
|---|---|---|---|---|
| 正常（未归档，登记位点在 live） | 1 | 0 | 1==N | 位点过 C1–C6″ → 豁免 |
| 合法 move（归档+已重锚，N 含档例） | 0 | 1 | 1==N | 无 live 出现，无豁免发生 |
| **偷位 M15**（原例归档+live 复本未重锚） | 1 | 1 | 2≠N | **全拒**（fail-loud） |
| 纯 append 复本 M13 | 2 | 0 | 2≠N | 全拒 |
| 崩溃双在（legacy 窗/修正后重试） | 1 | 1（或 2） | ≥2≠N | 全拒 → §3.3 对账恢复 |
| rollback（unlink 档+热恢复原行） | 1 | 0 | 1==N | 机制放行 + recount 回执审计义务（§4.2） |
| 枚举失败/超界/不稳定 snapshot（§2 全码） | — | — | 不评估 | 整次拒，无部分源结果 |

**G2 重申**：count==N 仅漂移观测，非逐 site 对应性 proof（R13 N2/R14 维持）；active 资格=条目 active ∧ 联合总数==N ∧ 该出现过 C1–C6″（邻接/载体/裁决逐字）。

## 7. 贯通验收矩阵（static walk，有据不新实验；拒绝「实现票再定」代设计）

| # | 情形 | 预期 | 机制锚定 |
|---|---|---|---|
| V1 | M13：同任务新行复本 append | 原行+复本均 BLOCK | §6 行 4 |
| V2 | M15：归档原例+live 复本 | 全拒 | §6 行 3（以 §3 修正后保真为前提；修正前=开放，呈报表口径） |
| V3 | 资源：513 文件 / 16MiB+1B / 5s+1 / 1,500,001 行 / 1MiB+1 行 | 各对应码整次拒、无部分计数 | §2.1/2.2 |
| V4 | 目录在场不可枚举 / 子目录出现 / snapshot 漂移 | `archive-plane-enum` / `-unexpected-dir` / `-unstable` 拒 | §2.1 |
| V5 | 旧档保真：同范围二次 legacy 迁移 | 旧档字节不变 + 新增量档承载新行集（或 existing-target digest 等幂等跳过）；**旧字节保留断言** | §3.2/3.3 |
| V6 | 中断重试（legacy 修正后） | never-overwrite 新档；双在→联合计数拒→对账（未授权）恢复 | §3.3 |
| V7 | W-B1：plan 后 registry 激活→resume | apply 锁内复检 `mention_registry_active_site` 拒；或 apply 后计数守卫保守拒 | §4.1 |
| V8 | rollback 含登记位点迁移 | 行回 live、机制按现值评估 + recount 回执义务 | §4.2/§6 |
| V9 | task 口径：前缀碰撞/多 ID/坏 token | 前缀非成员；多 ID 无漏计；坏 token+三元组行=保守计入 | §5 |
| V10 | 完整性 pin 漂移 vs hash 名单授格 | pin→拒/审计；任何 hash/ID 授格路径=不存在（红测断言拒绝） | §2.4 |

## 8. 备选/蓝军/比较条件修正

**备选（≥2，公允；标准=R14 §5 六条+新增「保护前提已规范闭合」）**：Alt-A′（A+本设计 §2/§3 修正）/ Alt-B′（B+§3/§4 修正）/ Alt-C′（A+G2+§2/§3，**推荐仍以 W-A1/W-A2 修正实施为前提**——本设计提供规范，实施未授权）/ Alt-D（维持开放）。**比较表安全行更新（R14 随附条件①履行）**：A 残余=「直改归档件」（legacy 覆写通道经 §3 修正消除——修正实施后）；B 残余=「G1 旁路/回执信任」（§4 复检消除门位 TOCTOU 的规范面）；Alt-C′ 推荐=条件性，非用户最终选择。

| # | 蓝军挑战 | 响应 | 残余 |
|---|---|---|---|
| BT-R15-1 | 枚举竞态窗内操纵（W-A1 残余） | §2.3 双相枚举+方向论证：窗内变化恒假拒向 | 无假授窗口（论证级，实现票红测） |
| BT-R15-2 | O_EXCL 原语实现错误（新小原语） | 语义=engine :1000-1009 既有纪律移植；四情形测试钉死 | 未实施未测（如实） |
| BT-R15-3 | registry writer 不守协同纪律 | §4.1 兜底主径=apply 复检（不依赖纪律）；纪律为辅 | 权威面 CH-1 级（既有界） |
| BT-R15-4 | 界值过紧误拒正常档库 | 全部设计界可经新票调整+实测票校准；拒向=availability 非安全 | 未实测 |
| BT-R15-5 | live/archive 口径修复前不对称被滥用 | 不对称方向=保守（§5）；三处统一为既定规范 | 实现票前维持（披露） |

## 9. NFR / ADR delta

- NFR：§2 预算表为设计界（未测）；A 面 IO/时延=每次 spawn-armed 读档（未测）；B 面运行时近零；原门不重测不放宽，实测票=共同验收前置。DIAG 沿 R14（APLANE/ASITES）增 `AENUM=<files>/<bytes>/<lines>`。
- ADR delta（proposed）：标题=ADR-FIX-445-R15 — 归档保护三修正（错误传播枚举+资源界 / legacy 不覆写 / apply 锁内 registry 末检）+多 ID 口径+计数推演；决策=采纳规范、全部写面未授权提案；备选 Alt-A′/B′/C′/D；影响=A 面=原两产品文件、B/保全面=infra 三件+tests/test_archive.py（均未授权）；后续=独立 R15→用户架构裁决→实现票（含 §7 矩阵红绿+实测）；可逆=是（各面独立 revert）。

## 10. 未解与自检

**未解（如实）**：①全部修正=未授权未实施的未来写面（本设计只出规范）；②A 档面成本/界值未实测；③legacy 修正实施前「归档保真」前提对 legacy 腿不成立（V2 以修正为前提）；④崩溃双在对账恢复未授权；⑤M15 仍待用户架构裁决（A′/B′/C′/D）；⑥原源 NOT_ESTABLISHED/迁移三问/ordinal live 机检沿 R13 §10；⑦隔离 witness FAIL（写者 unknown）/冻结 M5 命中/full 18/exit1 不归本设计。产品侧全部不变；无自动 R16。

**自检**：三 W+两 NOTE 逐项有规范响应（§2/§3/§4/§5/§6）；R14 缺陷撤回与 supersedes 明确（status 块+§0）；贯通矩阵 §7 全 static walk 有源码锚定；备选 4≥2（标准先列）；蓝军 5≥3；ADR/NFR 齐全；单向依赖（P3/复检/谓词均消费既有遍历或锁，无新环）；真实 helper 全部行号锚定（`_next_evidence_archive_filename`/`_atomic_write_text`/`_big_table_target_lock`/O_EXCL 为显式新原语非编造既有）；测试落点经 glob 实存确认（§1）。过程：本轮 read 3 治理件+engine 补读 130 行+glob×3+write 1+readback ≈ 10 步/32；零 shell/probe/test/installer/热面读/治理写/子 agent/用户交互。
