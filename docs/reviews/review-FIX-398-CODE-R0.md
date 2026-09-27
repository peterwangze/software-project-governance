# FIX-398 Code Review — Round 0

- **审查对象**: loop_migration.py（E-4 自愈 +386 行/E-5 孤儿清扫/P3-6 收口/勘察注释段）+ checks/evidence_domain.py（F-6/F-8）+ tests/test_migration_commit_window.py（16 测试）+ ADR §7 勘误 + fullchain F-7 注记
- **审查主体**: Code Reviewer Agent（只读 Read/Grep/Glob；未复跑测试/未重算计时——验证数据采信 EVD-1200 机录，如实披露）
- **轮次**: round 0（无前轮引用）
- **结论**: **APPROVED_WITH_NOTES（unresolved_blockers=0）**
- **日期**: 2026-09-27

## 5 维度

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | PASS | heal/sweep 逐分支审读正确：heal 先于幂等守卫（L1799→L1804）保证重入收敛；快照备份 newest-last 选择与 _list_migration_backups 名称序+冲突后缀语义一致；rollback restore 清除 MIGRATION 行（L2171）使「迁移→回滚→再迁移→窗口击杀」链的 heal 检测闭合成立（本审查专门推演确认）；wp-evidence 完整态→幂等拒绝语义正确；sweep 引用解析对 append-only 纪律下并发写天然免疫（快照哈希等值证明兜底） |
| 安全性 | PASS | P7 纯减法补偿实证：heal 只删 runtime+作用域 .tmp（mkstemp prefix 精确匹配 glob）+被中断事务自身备份（快照哈希==live 已证无信息）；plan/evidence 字节零重写；歧义/无快照两臂代码路径先于任何删除 return（零写）且有测试断言钉护；无注入面（re.escape 版本插值 L611/L643）；sweep 删除经 4 重无信息证明+live-runtime 全跳过守卫 |
| 可维护性 | PASS | +386 行集中于单一 banner 注释段（L514-566 勘察决策记录含提交序证伪论证）；docstring 锚定 ADR/DEC/RISK；P3-6 一行收口带理由注释（L2304-2306）；渲染器泛型 [WARN] {type} 无需新增消费方 |
| 性能 | PASS（记录证据） | 常规路径零热路径开销（heal 常态仅一次 is_file()）；detected 态加 2 次文件哈希；机录 23.8ms vs 40.9ms=1.72× 同量级（未独立复跑，如实披露） |
| 测试覆盖 | PASS-with-notes | 16/16 与实现分支映射核实（4 复演+7 清扫+2 fail-closed 臂+3 F-6/F-8）；wc6d 点真断言部分态复现；缺口见 P2-1/P3-1/P3-2 |

## 发现列表（0×P0 / 0×P1 / 1×P2 / 5×P3）

- **P2-1**｜test_migration_commit_window.py TestOrphanBackupSweep 全类——孤儿清扫 4 个安全验证臂无测试钉护（manifest 缺失/损坏臂 loop_migration.py:792-805、evidence 快照不一致臂 L817-824、runtime.before 非空臂 L825-832、rmtree 失败臂 L835-838）；其中 evidence-mismatch 与 runtime.before 非空两臂为「独有状态不得自动删除」承重防线。建议补 4 个自包含 fixture 测试。非阻塞（现行代码逐臂正确，风险=回归防护缺口）。
- **P3-1**｜test:360-376——backup= 引用保护测试名实不符（live runtime 存在时整个 sweep skip，断言由 skip 满足；backup= 臂仅经 restored_from 孪生测试间接覆盖 L785-786）。
- **P3-2**｜test:271-273 + loop_migration.py:697-707——.tmp 清扫臂复演空洞（击杀点均在 mkstemp→replace 跨度之外，不产生真实 .tmp 残留）；_COMMIT_TEMP_GLOBS 删除分支与 heal runtime-unlink 失败臂无测试执行。建议 seed 假 .tmp 断言 temp_files_removed。
- **P3-3**｜test:5-9 docstring——SIGKILL 保真度披露可再精确（未枚举指令级窗口：单次原子写内部 .tmp 残留窗/两次快照写之间窗——后者经 sweep 回退臂收敛且已被 wp-backup 实证覆盖）。
- **P3-4**｜loop_migration.py:729-733——rmtree 失败注记「next apply's sweep」应为「same apply」（结果优于文案，纯措辞）。
- **P3-5**｜范围面——子项⑥部分交付核实：F-8/P3-6 已收口；F-4/F-5 落点 verify_workflow.py 在 allowed_change_scope 之外留池，EVD-1200 已如实披露（与 FEAT-068 R0 原口径一致）。

## 硬门槛逐项

1. P0 阻塞=0 ✓ 2. 5 维度逐一结论 ✓ 3. 每条发现 P0~P3 ✓ 4. 设计一致性 ✓（执行包六子项+RISK-060 关闭标准+DEC-257+前轮 F-4~F-8/P3-6 对照）5. AI 专项 5 项 ✓

## 专项核对

- **复演窗口点覆盖表**：PASS——4 窗口点+2 fail-closed 臂与实现分支 1:1；wc6d 点先红后绿为真（test:223-235 重入前断言部分态复现）；执行包「≥3 窗口点含 wc6d」满足；os._exit(137)「跳过 finally/atexit 清理」表述如实（边界 P3-3）。
- **P7 补偿安全**：PASS——三类产物模块自有实证（runtime 本模块原子写/.tmp prefix 与 glob 互证/备份目录本模块创建）；SHA-256 全字节比较（单字节 append 均触发歧义 fail-closed，无误补偿路径）；「补偿后新鲜 apply」与幂等拒绝由 MIGRATION 行存在性正交分流。
- **孤儿清扫安全**：PASS——_BACKUP_REF_ROW_RE 限定行首 MIGRATION/ROLLBACK（prose 不绑定）+backup=/restored_from= 双引用面与行格式互证；tampered/异版本臂测试实证；manifest 坏臂无测试（P2-1）；sweep 不创建目录断言实证；live runtime 全跳过实证；删除四重证明均保守方向。
- **F-6/F-8 语义**：PASS——分流非改名（test:573-595 对照臂）；branch-8 按 detail 锚点断言免改即绿（test_evidence_binding_drift.py:331-332）；except Exception 不吞 KeyboardInterrupt/SystemExit（BaseException 族排除核实）。
- **DEC-257 合规**：PASS——MIGRATION_VERSION="0.65.0"（L115）零触碰，19 处引用均只读；heal/sweep 异版本显式不碰；banner 注释 L548-549 载明。

## RISK-060 关闭条件评估（供 Coordinator）

技术面达成：自愈形态交付+16/16 复演（含 wc6d 实证点+部分态复现断言+fail-closed 臂）+族/相邻/全量回归机录于 EVD-1200。建议：(1) 执行关闭动作，复评锚 0.90.0 M-4 保持；(2) 残余边界（P2-1/P3-2）不构成关闭障碍——标准要求窗口点复演验证而非全臂覆盖，已如实披露；(3) P2-1 随下一批测试卫生票关闭（关闭后转常规回归防护项，不再挂风险 ID）。

## AI 专项 5 项

零 mock 残留（测试 mock 全对称 start/stop）/ 零硬编码返回（os._exit(137) 为故障注入常量，docstring 载明）/ 零幻觉 API（imports 与懒导入逐一核实）/ 零 TODO（F-4/F-5 留池为显式披露非隐藏桩）/ 无过度实现（否决形态以证伪论证记录而非双实现并存）。

---

**Coordinator 注记（2026-09-27，非 Reviewer 文本）**：
1. Coordinator commit 前亲验：复演 16 测试 + -k loop_migration 族。
2. P2-1/P3-1/P3-2 处置：入批 2（FEAT-071）前置小修面或随测试卫生票——与 FEAT-070-R0 遗留（P2-1/P2-2/P3-4/P3-5）同池排期；P3-3/P3-4 顺手项。
3. R7 基线 stale 债：DEC-260 sanctioned regen（FEAT-069/070/398 三票 reviewed 结构增量）——与 FIX-398 提交分离（D4 单一目的提交纪律）。
