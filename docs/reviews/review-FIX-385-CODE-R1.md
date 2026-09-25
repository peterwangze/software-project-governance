# Review Report — FIX-385（B-7b 大表迁移）· Code Review R1

> round: **R1**（M7.4 T1 同席复审——聚焦 F-1 修复验证） · 前轮引用: `docs/reviews/review-FIX-385-CODE-R0.md`（R0 结论 APPROVED_WITH_NOTES/0——P0=0/P1=1[F-1]/P2=3/P3=6）
> reviewer: Code Reviewer Agent（同一 Reviewer，governance workflow 0.87.0）
> 日期: 2026-09-24
> 审查对象: R0→R1 增量 = `archive.py` 恰 1 新 hunk（`_migrate_decisions` L1197-1223 临界区化）+ deferral 透传块（L2294-2302，net −2）+ `test_archive.py` 恰 2 新测试及其探针助手（+76 diff 行）；其余 hunk 与 R0 逐一比对同位（hunk header 全表核对，位移一致）。并行面未触碰。

---

## 总结论

## **APPROVED_WITH_NOTES** · `unresolved_blockers=0`

R0 findings 逐条比对：**F-1 已修复（形态与申报一致，实测验证）**；F-2/F-3 勘正归 Coordinator 处理（在途，非代码项）；F-4 已路由 FEAT-044/045 面且在账可查；F-5~F-9 维持备查；F-10 未采纳（D4 理由留痕——owner 决策，记录保留）。零新引入 finding（修复面新增 P3 观察一条，见 N-1，不阻塞）。

| 项 | R0 | R1 |
| --- | --- | --- |
| P0 | 0 | **0** |
| P1 | 1 | **0**（F-1 已修复并验证） |
| P2 | 3 | 0 阻塞性遗留（F-2/F-3 勘正在 Coordinator 处理中；F-4 已路由闭环） |
| P3 | 6 | 6 维持备查 + N-1 观察 |

---

## 1. F-1 修复形态核验（逐条对照申报）

| 申报项 | 核验 | 证据 |
| --- | --- | --- |
| 临界区化 `_big_table_target_lock(dlog)` | ✅ | archive.py L1206 `with _big_table_target_lock(dlog):` 恰包裹落盘段（archive 写 L1220 + 投影重写 L1222） |
| 临界区第一步 in-lock 重判，先于落盘 | ✅ | L1207 `_decision_authority_state()` 为临界区首语句；raise L1209 先于首个写 L1220——重判先于落盘成立，refusal 时零写入 |
| 非 MD_ACTIVE→Conflict + `recheck=in_lock` + 零写入 | ✅ | L1208-1219：payload 含 `authority_state`/`recheck:"in_lock"`/detail 明言 zero writes performed |
| 与 FEAT-061 投影腿同锁域互斥 | ✅ | cutover `md_target = governance_dir / drepo.MD_FILE_NAME`（decision_migration L262/380/485/723/801），`MD_FILE_NAME="decision-log.md"`（decision_repository L129）≡ archive `_decision_log()`=`_gov_dir()/decision-log.md` → `_TargetLock` 派生同一 lockfile `.governance/.governance-store-locks/decision-log.md.lock` → 同锁域互斥成立 |
| 隔离加载降级无锁但世界判定不降级 | ✅ | `_big_table_target_lock` fallback 路径无锁 yield，但 with 体（含 in-lock 重判）无条件执行——正确性保留、仅互斥丢失，与申报一致 |
| deferral 全量 payload 透传 | ✅ | L2302 `result["decision_migration_deferred"] = dict(exc.payload)`（含 recheck 字段全量透传） |
| 锁序安全 | ✅ | archive.py 无既有 dlog 锁持有者（R0 已核）；临界区内仅 `_write_archive_file`/`write_text` 纯文件操作，无嵌套锁获取；elog 锁（migrate_evidence_resumable）与 dlog 锁不同 target 且无嵌套 → 无死锁面 |
| dry-run 写段前返回不加锁 | ✅ | L1174-1177（`not archived`/`dry_run` return）均在 `_ensure_archive_dirs()`/L1206 之前——dry-run 永不加锁 |

**对照先例**：修复形态与 REVIEW-FEAT-061-CODE-R0 P0-F1（decision_append in-lock 复核，governance_store L1345-1350）同构——R0 F-1 建议的镜像形态如实落地。

## 2. 2 新测试判别力（RED 真实性实测）

- **测试 1** `test_concurrent_cutover_into_window_refuses_rewrite_in_lock`（test_archive.py L5100-5126）：状态探针 `_concurrent_cutover_state_probe`（L5083-5098）以 call 计数模拟 TOCTOU——call 1（entry 门）放行 MD_ACTIVE，call 2（in-lock 重判）**先将 JSON_ACTIVE marker 落盘再读**（L5093-5096，因果链忠实）；断言 `recheck=="in_lock"` + `authority_state=="JSON_ACTIVE"` + 投影零写入（DEC-501 留守 + decisions 归档目录为空——写入发生则 DEC-501 必被移除且归档文件必出现，双断言充分）。
- **测试 2** `test_concurrent_cutover_window_records_deferral`（L5128-5152）：全 `migrate_by_version` 路径——deferral 记录 `recheck=in_lock` + 投影**逐字节相等**（L5149-5151 精确文本比对）+ `evidence_archived==54`（其余类别照常）。
- **RED 实测**（isolate：HEAD worktree + R0 archive diff `git apply` 重建 R0 态〔apply exit 0，+878/−86 与 R0 申报一致〕+ R1 测试文件）：`TestDecisionStoreAuthorityInterface` = **恰 2 failed（即此二测试）/ 5 passed**。R0 态下无临界区重判 → 探针 call 2 永不触发 → 迁移完成 → 两测试的拒绝/deferral 断言必然失败——**判别力真实，非恒过**。
- 探针方法评估：patch 的是产品自身的 state seam（`_decision_authority_state`），无产品测试钩子新增，与套件 crash 注入风格一致。

## 3. 复跑记录

```text
[RED ] %TEMP%/fix385_wt_r1（HEAD d7b9add worktree + git apply R0 archive diff）+ R1 test 文件
       pytest TestDecisionStoreAuthorityInterface → 2 failed, 5 passed in 0.38s
       （worktree 用后即删，git worktree list 核实仅余他人既有 pristine 副本）
[GREEN] pytest skills/…/infra/tests/test_archive.py -q → 159 passed in 1.76s（157+2 精确复现）
[VERIFY] verify_workflow.py verify --project-root <repo> → == Verification Result: PASSED ==
```

申报「2R→2G；159P（157+2）+相邻 286P；verify full PASSED」——前两项与 verify 复跑**实测一致**；「相邻 286P」为申报方 scoped 口径（未给命令，无法逐数复原；R0 已以全量 infra 套件 4099P/7F〔6F HEAD 存量 + 1F 并行面〕覆盖更强证据，本票零新增失败结论不变）。

## 4. R0 findings 处置比对（复审本质：逐条验证）

| # | R0 级别 | R1 处置 | 核验 |
| --- | --- | --- | --- |
| F-1 衔接面 TOCTOU | P1 | **已修复** | §1 全表 ✅ + §2 RED/GREEN 实测 ✅ |
| F-2 RED 16F/141P 勘正 | P2 | Coordinator 处理中（EVD 勘正，非代码项） | 接受处置路径；不阻塞 |
| F-3 manifest 882 勘正 | P2 | 同上 | 同上 |
| F-4 全量 7F 第 7 项路由 | P2 | 已归 FEAT-044/045 面——**在账核实**：evidence-log EVD-1161（FEAT-044）/EVD-1159（FEAT-045）+ REVIEW-FEAT-044-R0/REVIEW-FEAT-045-R0 机录记录（evidence-log L2674/L2675/L2680/L2681） | ✅ 快查通过 |
| F-5 journal payload 信任面 | P3 | 维持备查（未修，未扩大） | — |
| F-6 行尾字节不对称披露 | P3 | 维持备查 | — |
| F-7 365 行函数 | P3 | 维持备查（仅记录） | — |
| F-8 peer-import 耦合 | P3 | 维持备查；修复未降级世界判定（§1 行 5 ✅） | — |
| F-9 rollback 不清 .migration | P3 | 维持备查 | — |
| F-10 StoreError 未映射 | P3 | **未采纳（owner 决策，D4 理由留痕）**——单票单 commit 纯粹性，属后续 archive 域切片；R0 记录保留 | 接受 |

**新引入检查**：修复 hunks 逐行读——无新逻辑面（锁包装+提前 raise+payload 透传），无 mock 残留/硬编码/幻觉 API/TODO/过度实现；唯一新观察：

> **N-1（P3 观察，不阻塞）**：in-lock 重判在 fallback（无 `_TargetLock`）下仍执行（正确），但 `_TargetLock` 真实路径上，若 cutover 持锁则 migrate 侧 `_TargetLock.__enter__` 10s 争用超时抛 `StoreError`——经 `migrate_by_version`/CLI 冒泡为裸 traceback（响亮、非零退出、零写入；F-10 同族）。现状可接受；与 F-10 一并在后续 archive 域切片吸收即可。

## 5. 硬门槛裁决（R1）

- P0=0 ✅ · 五维度维持 R0 结论（修复面仅收窄 F-1，无其他维度回归——159P 全绿佐证）✅ · 发现全标注 ✅ · 设计一致性：修复与 ADR-006/FEAT-061 P0-F1 先例同构 ✅ · AI 专项 5 项复扫修复区段全过 ✅

## 结论

**APPROVED_WITH_NOTES · `unresolved_blockers=0`**——F-1 修复验证通过，FIX-385 可合并；备注：F-2/F-3 EVD 勘正由 Coordinator 收口，P3×6+N-1 备查随 archive 域后续切片吸收。
