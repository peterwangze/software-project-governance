# FEAT-075 四行族只读扫描 dry-run 实测与 495 行估算复核（DEC-278 单元二交付物）

> **任务**: FEAT-075 — 四行族只读扫描 dry-run + 发布聚合层例外标注（DEC-278 单元二）
> **授权链**: DEC-274 → DEC-278（单元二 §3.1 + MUST NOT §3.2 + 可证伪验收 §4）；TRIAGE-FEAT-075 机录；FEAT-074（单元一，commit c90768f）前置
> **性质**: 本档 = live 数据实测落档（DEC-278 §4 验收 1/4 两项）。测量工具为**入库产品代码**（`archive.py scan-families`——M-0 前置五项之一「可复现基线承载」）；本票**零迁移执行、零 Check 28s 阈值/语义变更、零 loop_migration 契约变更**（DEC-278 §3.2 红线遵守声明）。
> **数据时点**: 2026-09-28（FEAT-075 会话实测）。

---

## 1. 可复现输入锚（M-0 前置一：测量工具 + 输入 commit + 逐行输出）

| 锚 | 值 |
|---|---|
| git commit | `c90768fe89dc626e6654f26a92cf3370ff62fd6d`（= FEAT-074 交付 commit；扫描器代码为工作树态，待本票 commit 后即由锚完整复现） |
| evidence-log | **1,781,709 B / 2,922 行**，sha256 `537dae71f4e8adec335c0ae6fb3d39988f6c7f46caa5289392262471df811e71` |
| plan-tracker | sha256 `1fbc11e1a23570f050a3bb8846793bbd9d547dc5c1e826dba8a561a5177c2219` |
| task_versions 基线 | 547 项（archive/tasks 归档映射 + completed-hot） |
| 复现命令 | `python skills/software-project-governance/infra/archive.py scan-families 0.1.0 0.91.0 --output <tsv> --report-json <json>`（逐行 TSV 可 diff；`--family` 可限族；输出路径拒入 `.governance/`） |

> **扫描后 live 漂移注记（R0 复审期）**：R0 审查轮经 review-record 追加了 `REVIEW-FEAT-075-R0` 行——本档全部数字锚定 §1 输入（sha `537dae71…`，REVIEW 633 行）；追加发生于文件末尾，不扰动锚定行号（§3 机械分解自校验精确闭合佐证）。

**字节口径**：与 FEAT-074 差异档 §1 相同的 raw 口径（`read_bytes().decode()` 后逐行 UTF-8 长 + 1B 换行、末行不计；CRLF 行保留 `\r`）。

**只读证明（live 实测）**：扫描前后 evidence-log 与 plan-tracker 的 sha256 均相等（本会话 Get-FileHash 前后对比 PASS；产品级回归测试 `test_scan_is_read_only_sha256_unchanged` 常驻）。

## 2. 四族 dry-run 摘要（live 实测；主窗=全窗 0.1.0~0.91.0，副窗=保守 ≥1 0.1.0~0.90.0）

### 2.1 主窗（全窗 ≤0.91.0）

| 族 | 总行/字节 | would_archive 行/B | malformed/unknown | 逐原因（行/B） |
|---|---|---|---|---|
| EVD | 486 / 1,170,274 | **204 / 642,749** | 10 | missing 175/354,377 · no_family 44/59,201 · unparseable 19/48,372 · duplicate 14/18,820 · oor 11/15,104 · unknown_shape 10/11,660 · active 5/10,712 · keep 4/9,279 |
| REVIEW | 633 / 488,744 | **469 / 351,031** | 4 | missing 85/86,826 · duplicate 42/27,252 · unparseable 17/5,281 · oor 6/1,879 · keep 5/7,295 · unknown_shape 4/6,004 · active 2/648 · no_family 2/2,210 · ambiguous 1/318 |
| TRIAGE | 199 / 66,300 | **142 / 47,444** | 0 | missing 44/14,416 · active 4/1,346 · oor 4/1,348 · unparseable 3/1,002 · duplicate 2/744 |
| RECO | 159 / 53,013 | **111 / 36,806** | 0 | missing 26/8,889 · duplicate 12/4,081 · unparseable 6/1,953 · active 2/642 · no_family 2/642 |
| **四族合计** | 1,477 / 1,778,331 | **926 / 1,078,030** | 14 | — |

### 2.2 副窗（保守 ≥1，≤0.90.0——与盘点 §2.3 同窗口径）

| 族 | would_archive 行/B（≥1 窗） |
|---|---|
| EVD | 192 / 611,147（与 FEAT-074 差异档 §2.2 副窗 **精确一致**） |
| REVIEW | 459 / 347,814 |
| TRIAGE | 139 / 46,438 |
| RECO | 110 / 36,486 |
| **三族小计** | **708 / 430,738**（对比盘点估算 495 / 263,163，见 §3） |

### 2.3 覆盖对账（不静默漏扫）

2,922 行 = 1,477 四族行（含 malformed 14）+ 9 其他表行 + 1,436 非表行，零未认领行（`unclaimed_family_prefix_lines=0`）。盘点 §1.4 的「其他表行 9 行」精确吻合。

**未知/异形行显式计数**：REVIEW 4 行（`REVIEW-FIX-155a`、`REVIEW-0.45-0.46-FINAL`、`REVIEW-0.44.1-0.45.0`、`REVIEW-0.43-0.44.1`——历史版本区间复合审查行，非任务锚定）→ `unknown_row_id_shape`，显式留热（单元三/FIX-402 数据面盘点输入）；EVD 10 行 unknown_evd_id_shape 维持单元一判定。

### 2.4 EVD 面交叉验证（对 FEAT-074 差异档）

EVD 全窗 would_archive **204 行 / 642,749 B** 与 `feat-074-classification-diff-20260928.md` §2.1 after 汇总**字节级精确一致**；missing 175/no_family 44/unparseable 19/duplicate 14/unknown 10/keep 4 亦逐项一致（oor 11 vs 9、active 5 vs 5——差异源于 R1 快照后 evidence-log 在途新增行：484→486 行，EVD-1225/1226 等；时点漂移披露）。**四族扫描器与单元一分类器零漂移的构造性证明**（EVD 族直接调用 `_classify_evidence_rows`）。

## 3. 盘点 §2.3「495 行/263KB」估算复核（DEC-278 §4 验收 4）——R0 F-1 重做：机械分解、算术闭合

**口径**：盘点 §2.3 β 判据（关联任务列可解析 + max 版本周期封闭 ≥1 + 排 0.92）对 REVIEW/TRIAGE/RECO 的**估算**（临时脚本，已删——正是 M-0 前置一指出的不可复验问题）；本复核 = 同窗（≤0.90.0）六条件 dry-run **实测** + 对 495→708 偏差的**机械分解**（方法：以 §1 输入锚的 scan-families 逐行记录为底，逐行重建估算口径判定——判定基=关联任务列引用、**FEAT-074 前 allow-list**（无 FEAT/FX）、可解析=task_versions 映射成员、窗=≥1——与实测 verdict 交叉分桶；行数与字节双口径逐项闭合）。

**结论（R0 F-1 勘正版）：估算解析面无系统性高估证伪——估算判可迁的行中，被六条件实测阻塞的仅 28 行（估算未建模的更严门：重复 ID 24 + 显式保留 4）；+213 行/+167,575 B 偏差由「解锁 238 − 阻塞 28 + 重建漂移 +3」三项精确闭合（字节 187,753 − 18,060 − 2,118 = 167,575 ✓）。**

### 3.1 实测 708 行的机械分解（估算重建 × 实测 verdict 交叉，加总闭合）

| 分桶 | 定义（机械判定规则） | 行 / B | 实测归属 |
|---|---|---|---|
| **X** 估算判可迁 ∧ 实测可迁 | 列内旧族引用全部可解析且 max ≤0.90 → 实测 would_archive | **470 / 242,985** | 495 的主体在实测下成立 |
| **U₁** 解锁：FEAT/FX 门控行 | 列内**无**旧族引用（门控引用全为 FEAT/FX——估算时 FEAT/FX 非任务族 → 落估算「无任务引用」桶被排除）→ 实测可迁 | **164 / 67,501** | FEAT-074 任务族补位+FX 逐 ID 别名 |
| **U₂** 解锁：registry-REQ 行 | 列内旧族引用含登记表 REQ（REQ 在旧 allow-list 内但永无任务版本 → 落估算「引用不可解析」桶）→ 实测改判 requirement 非门控后可迁 | **74 / 120,252** | DEC-278 Q2=c |
| **U₃** 解锁：其他映射漂移 | （重建口径下无此桶行——映射漂移经 §3.3 漂移项承载） | **0 / 0** | — |
| **加总** | X+U₁+U₂+U₃ = 实测可迁 | **708 / 430,738** ✓ | 行/字节双口径与 §2.2 精确相等 |

### 3.2 估算 495 行的机械分解与偏差闭合

| 分桶 | 定义 | 行 / B |
|---|---|---|
| **X**（§3.1 同桶） | 估算判可迁 ∧ 实测可迁 | 470 / 242,985 |
| **B** 估算判可迁 → 六条件阻塞 | 估算口径可过、实测被六条件新门拦截（机械分桶实测 reason 分布：duplicate_row_id 24 + explicit_keep_marker 4——**仅此两门**；oor/unparseable/active 等其余被实测阻塞的行经重建判定证明估算当时同样排除〔引用不可解析/周期未封闭桶〕，不属「估算判可迁」） | **28 / 18,060** |
| **重建估算合计 X+B** | 与估算原值对照 | **498 / 261,045** vs 估算 **495 / 263,163** |
| **重建漂移 δ** | (X+B) − 495（行集漂移 985→991 行 + task_versions 映射漂移 545→547） | **+3 行 / −2,118 B** |
| **偏差闭合恒等式** | Δ = U − B + δ：行 238−28+3=**+213** ✓；字节 187,753−18,060−2,118=**+167,575** ✓ | Δ=+213/+167,575 ✓ |

### 3.3 R0 第三方向假说行级定谳 + 时点漂移

- **假说「估算仅按关联任务列判可解析（盘点 L141）vs 扫描器门控=ID 内嵌∪关联列（archive.py `_parse_family_row`）」经行级验证：对偏差零贡献**——锚定输入下三族 col2 与 ID 内嵌任务**全量一致**（REVIEW 633/TRIAGE 199/RECO 159 逐行核验零失配、零空列），门控并集与列-only 同判。真正承载第三方向的是 **U₁ 的旧 allow-list 语义面**（列内任务引用为 FEAT/FX → 估算按「无任务引用」排除），已入 §3.1。
- **时点漂移披露**：盘点时点三族 985 行（REVIEW 630/TRIAGE 196/RECO 159）→ 本实测锚定 991 行（+REVIEW 3：FEAT-074 R0/R1 等；+TRIAGE 3：FEAT-075/FIX-402 等；RECO 持平）；重建口径的映射=现行 547 项（估算时点 545）。估算逐行分类无存档（临时脚本已删），重建漂移 δ 即其不可复现性的量化——这正是本票测量入库（`scan-families` + 输入锚 + 可 diff 逐行 TSV）消除的缺口。
- **残余（估算「不可解析」面的现存核）**：missing_task_ref 实测 155 行 / 110,131 B（三处均不可定位）——FIX-402 单元三台账输入；实测另有 oor 24/unparseable 26/active 8 等 91 行被六条件阻塞但经重建判定证明估算当时亦排除（不在 495 内，非「估算被证伪」行）。

**含义**（供 0.93 FEAT-076 规划）：三族若随分层票纳入实际迁移面，可迁量按现行数据为 **708~722 行 / 430,738~435,281 B**（保守 ≥1 窗~全窗），显著高于盘点估算——「分层范围扩展到 REVIEW/RECO/TRIAGE」的缓解结论被强化（DEC-278(1) 的 6.96× 投影相应改善）。

## 4. 写边界与例外机制（验收 2/3 的 live 面）

- **三族写迁移代码级拒绝**：`migrate`/`migrate-big-table`/`migrate_auto`/`_migrate_evidence`/`migrate_evidence_resumable` 全部入口经 `_guard_row_family_write_migration` 拒绝 REVIEW/RECO/TRIAGE（不论 dry_run 与否；`RowFamilyMigrationRejected`，payload code=`row_family_write_migration_rejected`）；EVD 既有路径保持。CLI `--row-family` 显式暴露拒绝面。负例测试 12 组（4 入口 × 3 族）+ CLI 拒绝测试常驻 `test_archive.py FEAT075RowFamilyScanTests`。
- **dry-run 零写入**：live 前后 sha256 相等（§1）+ 产品级回归断言。
- **例外标注机制**（`.governance/exceptions.json`，schema `governance-exceptions/1`）：作用域（check_id+制品）/原始状态/有效期/批准引用/增长控制量五要素登记；聚合层（`_archguard_print_findings` 共享渲染、Check 28s 段、check-release `governance_exceptions` 披露块）读到**有效**例外时标注 `exception accepted (id, ref=…, expires=…)` 而**不改动**底层检查结果（severity/bytes/summary/exit 原样）；过期/超增长控制量/状态不匹配/登记缺失 → 标注不生效且披露（fail-closed）；**注册表文件级错误（畸形条目/错 schema/不可读）在两条渲染路径一次性披露 `registry-error: N entry(ies) malformed/unreadable…`（R0 F-2）**。四态+额外态+registry-error 披露合成 fixture 测试 12 项常驻 `test_verify_workflow.py FEAT075ExceptionAnnotationTests`。**本票交付机制与测试；实际登记内容（日期/批准）由 Coordinator 在 M-0 后写入。**

## 5. 边界与不做声明（DEC-278 §3.2 对照）

- 未执行任何实际迁移（含 EVD——本票零迁移执行；would_archive 全部为 dry-run 候选投影）。
- 未动 Check 28s 阈值/语义（例外标注≠语义切换：28s 仍 advisory、原始字节数照报）。
- 未改 loop_migration 契约；未做热冷读取切换；未抬阈缩窗；未批量补猜归期。
- `.governance/` 零写入（本档为 docs/ 面授权产物；TSV/JSON 报告输出至 %TEMP%）。

## 6. 复现与对账链

- 工具：`archive.py scan-families`（产品代码；分类核 `_make_ref_verdict`/`_REF_FAILURE_SUBSTATE_ORDER` 自单元一 `_classify_evidence_rows` 原样抽取，EVD 族直接复用该函数——零平行实现）。
- 逐行 TSV（本会话产物，%TEMP%，列：family/id/line_idx/bytes/candidate/owning_version/reason/ref_types/detail）两窗各一份；本档全部汇总数字由其机械聚合。
- 交叉验证：§2.4 EVD 对 FEAT-074 差异档；§2.3 其他表行 9 对盘点 §1.4；§3 三族对盘点 §2.3。

---

*本档为只读测量落档（唯一写入=本文件）。测量工具已入库（非临时脚本）。未 commit。*
