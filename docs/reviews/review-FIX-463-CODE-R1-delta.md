# CODE R1 delta 独立审查报告 — FIX-463 CI 热修 3b9926b

- 审查对象：`git show 3b9926b`（相对 8714d4d；3 文件 +26/-11：test_governance_store.py / test_quickscan_registry.py / verify_workflow.py）
- 触发：CI run 40098686909 四项失败后 Developer 自主热修推送，本 delta 未经独立审查——补审
- 审查人：Code Reviewer（独立，只读+复跑）
- 日期：2026-10-24
- 结论行见 L12。

FIX-463 delta 3b9926b: APPROVED_WITH_NOTES (unresolved_blockers=0)

## 1. 两处真树测试守卫（原 skipUnless 前置要求）— 通过

- 实现为运行时 `if not evidence_path.is_file(): self.skipTest("live governance data absent (CI checkout)")`（语义等同 skipUnless，且带可见 skip 理由）——两处：`test_dec368_retro_calibration_readonly_demo` 与 `test_live_tree_bypass_floor`。
- **根因成立**：`.governance/evidence-log.md` 为 gitignored 本地运行时数据，CI checkout 不携带；原实现无条件 read_text → CI 上 FileNotFoundError。四项失败中的两项即此。
- **语义承载不降级**：行形状契约（hook 语境/否定窗口/次数枚举/pin 复发计数）由合成 fixture 面（`test_bypass_row_shapes_and_exclusions` / `test_pin_recurrence_counter`）无条件全环境机判；真树底线断言（≥3）仅在有数据的机器跑——环境能力边界，非测试弱化。docstring 与注释双处注明 CI note。✓

## 2. check_decision_premise docstring 改词（载体纪律）— 通过，且是修复而非规避

- CarrierDiscipline 纪律实证（test_quickscan_registry.py L608-627 实读）：引擎源码必须**零** `quickscan_registry` 子串、含 "quickscan" 的行**恰好一行**（被钉死的 selector 接线）。原 docstring 写 `quickscan SegmentSpec "2b"` 使 "quickscan" 子串出现在第二行 → `len(wiring)==1` 失败（2!=1）。
- 改词 `the segment registry's SegmentSpec table` 去除子串 → 纪律恢复（1==1）；段登记说明仍准确（"Registered as the R5 segment-2b loader" 保留）；纯措辞、3 行换 3 行零行数变化——R1/R4 基线不动主张由本审查 archguard-ratchet 复跑 OK 佐证（38 tests OK）。✓

## 3. CensusIntegrity 首错位 55→56 重钉 — 通过

- 机制成立：新段 2b 在两个序（引擎源码序：Check 2 后；注册表序："2" 后）**同位置**插入 → 后续序号整体 +1 → 首分歧位 55→56，`("29","28u")` 对子不变——测试断言两者（L820-824），本审查复跑 test_quickscan_registry 82 tests OK 实证。FIX-463 注释含机制说明。✓

## 4. test_quickscan_registry.py 作为第 15 面文件 — 义务成立，披露在案（过程注记）

- census 钉扎=段登记纪律冻结字面量，段新增时同步=与 R1 锚同步同款 regen-sync 义务——定性正确（FIX-462 第 10 文件先例同构）。
- 过程注记：该文件不在 FIX-463 的 13 文件锁面内，编辑前未扩锁，以 commit message 披露（"disclosed 15th face file"）补救。冻结字面量同步、零语义变化，不构成 blocker；纪律改进建议：regen-sync 面文件应在勘察期枚举进锁面（本票两次踩同一形状：FIX-462 第 10 文件、本票第 15 文件——模式已知，勘察模板可固化「新段/新命令 → census 锚所在测试文件」检查项）。

## 复跑汇总（本审查独立执行）

| 套件 | 结果 |
|---|---|
| test_governance_store.py（123） | OK |
| test_quickscan_registry.py（82） | OK |
| test_archguard_ratchet.py（38，~176s） | OK（R1/R4 基线未动佐证） |
| test_registry.py（77）/ test_contract_matrix.py（27） | OK |
| test_task_priority.py（186） | OK |
| verify_workflow 全量 | **PASSED** exit 0 |

四项失败 → 四项修复一一对应（2×真树守卫 + 载体纪律 + census 重钉），无超范围改动（diff 恰 3 文件 +26/-11，与 stat 一致）。

## Notes（非阻塞）

- **N1（R0 审查盲区自省）**：本 delta 暴露 R0 审查的环境盲点——审查机带 .governance 数据，真树依赖不可见；R0 报告「全绿」为真但未标注 live-data 依赖。后续审查清单应固化「真树读取行 → 标注 CI checkout 行为」检查项。
- **N2**：锁面外第 15 文件的过程披露（见 §4）+ 勘察模板固化建议。
- **N3**：skip 守卫为运行时 skipTest 非 skipUnless 装饰器——语义等同（含可见理由），无需改。

## 审查边界声明

只读命令 + 仅写本报告文件；未改代码、未碰 .governance、未动 git/WIP。
