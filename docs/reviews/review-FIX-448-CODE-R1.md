# FIX-448 CODE R1 复审报告（同链承接 CODE R0）

- Task ID：FIX-448 · Round：R1（CODE 链 round 1；复审必达 T1——R0=NEEDS_CHANGE 后同链新实例）
- Reviewer：Code Reviewer（R0 同链新实例；注入 R0 报告路径复审）
- 结论：**APPROVED_WITH_NOTES · unresolved_blockers = 0**（P0=0 P1=0 P2=0；R0 遗留 P3-1/P3-3 已按处置登记 M2 前置，不阻断）
- 日期：2026-10-24（UTC 时点见 §命令审计）

## 1. 对象绑定（SHA-256 独立复算）

| 对象 | 声明 | 复算 | 一致 |
|---|---|---|---|
| infra/evidence_migration.py | 9DE94524 | 9DE94524 | ✅ |
| infra/tests/test_evidence_migration.py | E1088726 | E1088726 | ✅ |
| .codex-sandbox/FIX-448/m1-report.md | 85B829A0 | 85B829A0 | ✅ |
| 热表 evidence-log.md（只读基线） | 5232F184 | 5232F184（2,155,457B）审查前后逐位相同 | ✅ |

## 2. P1-1 修复判定（R0 阻断项）：PASS

亲读 evidence_migration.py L482-507（9DE94524）：

1. **真实盘面回读**：`on_disk = seg_path.read_bytes()`（L492）——cold publish 后从磁盘读回字节；不再存在内存自对照恒等式。
2. **双层对照**：① 文件整体 == 原语 payload 公式（`header+"\n"+join(剥LF行)+"\n"`）逐字节（L493-500 → `identity_changed` refusal）；② payload 行级 `line+"\n" == mover 原 chunk`（L501-507 → `byte_conservation_failed` refusal）。
3. **I4 顺序性声明与实现一致**：`phase=cold_verified`（L508）严格先于 hot CAS（L512-518 temp+fsync+replace）；refusal 路径全部早于 hot 提交，hot 分支不可达；staged/backup 保持可核对。
4. **"created" 首次路径覆盖**：盘面验证不依赖 outcome 分支（created/EEXIST 幂等均读盘）——R0 指出的"首次创建无盘面回读"缺口闭合。
5. **P3-3 边界 fail-loud**（L486-489 注记）：无尾 LF mover 行将 1B mismatch→loud refusal，绝不静默 CAS；M2 re-plan 断言边界登记（§10.2）。

## 3. 非空转证明：PASS

`test_p1_1_disk_readback_rejects_corrupted_segment`（E1088726 L403-425）：corrupting_publish 包装真实原语后追加 1 字节（post-fsync landing corruption）→ 断言 refusal code ∈ {identity_changed, byte_conservation_failed} + 热表逐位不变。**该注入在 R0 旧实现（内存恒等式）下不可能被捕获——用例对旧实现必 FAIL，证明盘面验证路径真实生效。**

## 4. P3-2 / P3-4 判定：PASS

- P3-2：`test_p3_2_cold_primitive_failure_hot_untouched`（L380-400）——原语 raise → 结构化 refusal（非 traceback）+ `archive_target_conflict` code + "hot table untouched" + 热表逐位不变。
- P3-4：L470-478 `except BigTableMigrationError → _refuse("archive_target_conflict", …)`——§7.2 结构化 Refusal 形态；fail-loud 语义保持（staged 状态保留声明）。

## 5. 独立复跑实数（全部 cwd=infra 或 tests/ 正确口径）

| 套件 | Developer 声明 | 独立复跑 | 一致 |
|---|---|---|---|
| test_evidence_migration.py | 16/16 | **16 passed** in 1.10s | ✅ |
| test_summary_only.py | 27/27 | **27 passed** in 0.56s | ✅ |
| test_archive.py 全量 | 206+1s | **206 passed, 1 skipped, 8 subtests** in 4.54s | ✅ |
| test_verify_workflow.py 冒烟（cwd=tests/） | 43/43 | **109 passed +18 subtests**（-k 面更宽，全绿） | ✅（≥声明） |
| 真实热表 dry-run | exit 0 / 120 / 207,338B / 热表逐位同 | **exit 0 / moved 120 / 207,338B / retained 1179 / 1,942,642B / hot 前后 5232F184 逐位 identical** | ✅ |
| stage 残留 | — | **0 个 evdt 残留** | ✅ |

## 6. delta 外零意外变更：PASS

- 变更面亲读确认=apply/cold-verify 段重写（L452-508）+ P3-4 包装（L470-478）+ 2 新用例（L380-425）；fixture 1 处 BigTableMigrationError 构造对齐（test_p3_2 内 monkeypatch 构造，fixture-only 不触产品面——Developer 自披露核验成立）。
- I1~I7 快检（重点 I4）：I1 切片 hash 身份、I2 canonical 单源、I3 retain 1179 实例热可达、**I4 声明=实现（本轮修复核心）**、I5 原语 never-overwrite 复用、I6 capacity blocked 如实（dry-run 输出确认）、I7 独立 transaction_id。
- `--execute` 硬门禁保持（dry-run 复跑 exit 0 全程 planned phase；M2 旗未设不可达）。

## 7. R0 遗留处置确认

P3-1（planner conservation/overlap refusal 真实覆盖）与 P3-3（尾 LF 边界）已登记 m1-report **§10 M2 前置清单**（§10.1/§10.2）；§10.3 pins 重捕（热表 F3C91B9A→5232F184 正常演化披露，M2 须重新 plan 禁复用本报告数字）——处置合规，不阻断本轮。

## 8. 边界合规

审查全程热表只读（5232F184 前后自证）；零治理写入；不 stage/commit/push；被审对象零修改；无收到转包/委派消息（通信异常：无）。

## 9. 命令审计

| # | 命令（摘要） | exit | UTC |
|---|---|---|---|
| 1 | Get-FileHash 三对象+热表基线 | 0 | 2026-10-23T~23:5xZ（本地 10-24 07:5x+08） |
| 2 | grep cold_verify/_refuse 定位 + read L452-529 | 0 | 同上 |
| 3 | grep/def test_p1_1/p3_2 + read L380-441 | 0 | 同上 |
| 4 | pytest test_evidence_migration.py（cwd=infra） | 0（16 passed） | 同上 |
| 5 | pytest test_summary_only.py | 0（27 passed） | 同上 |
| 6 | pytest test_verify_workflow.py -k（cwd=tests/，初次 cwd=infra 收集失败为预存在 bare-name 限制，已按正确口径重跑） | 0（109+18sub） | 同上 |
| 7 | pytest test_archive.py 全量 | 0（206+1s+8sub） | 同上 |
| 8 | evidence_migration.py --dry-run --governance-dir（两次参数修正后正确口径） | 0（120/207,338B；热表 identical） | 同上 |

*报告完。本文件为 R1 复审唯一产出写面（+scratch）；未修改任何产品/治理/取证文件。*
