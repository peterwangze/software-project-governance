# Review Record: FIX-426 — 后置代码审查（CODE，R0）

- **Task**: FIX-426 — 裁决②探索票：docstring 口径 source-pinning 测试（+2 类 4 用例，零生产码变更）
- **Reviewer**: Code Reviewer Agent（只读；round 0；未修改任何文件；未运行命令——全部静态核验）
- **审查对象**: docs/reviews/FIX-426-R0.diff（113 新增行逐行 + 工作树 L524-636 逐行比对）+ provenance_domain.py / loop_gate_processor.py / version.py STATIC_PIN 面
- **日期**: 2026-10-03
- **结论**: **APPROVED_WITH_NOTES** · unresolved_blockers=0 · P0=0 / P1=0 / P2=0 / P3×6（全非阻塞）

## 一、审查范围与硬门槛自检

- **逐行**：113 新增行全部读完，hunk `@@ -521,5 +521,118 @@` 算术闭合（原 525 行 → 638 行，L1–L523 零位移）。
- **断言 vs 被测现状逐句事实比对**（独立于 Developer 自报）：
  - `pd.__doc__` bullet 面：L16 "Four functions"；L18/26/32/36 恰 4 条 `- :func:`name`` bullet → 正则恰好解析 4 名；四名全部实存（L151/317/433/619）且全在 `__all__`（L85/86/87/93）；Four→4 == 4。**静态判定现状绿**。
  - I/O-free 面：loop_gate_processor.py 全文 431 行 grep 三 token **零匹配**（含注释/docstring）——现状绿、断言面真实；docstring L48-50 "writes)/reads live" 字样不含三个精确 token（`.write(` 需 dot+write+paren 连续）→ 无假红。
  - ast import 面：模块级仅 `__future__`/json/re → 断言成立；仅遍历 `tree.body` 顶层，函数内 import 不计数，顶层新增即转红（强制 resync），稳健性方向正确。
- **可证伪性四红路径静态推演——全部真实**：①第 5 bullet 不改计数词 → assertEqual(4,5) 红；②:func: 笔误 → hasattr 红；③移出 __all__ → assertIn 红；④去前缀重排 → 零解析，assertTrue(names) 红（消息指向 resync）。负路径均有显式可操作失败消息。
- **STATIC_PIN 面结构核验**（验收④静态侧）：version.py L301-304 登记本文件两条豁免 **(323,"0.93.0") 与 (342,"0.93.0")**；工作树 L323/L342 均仍携 token 于原行 → 锚完好零漂移。新增块内唯一版本字样是 L557 注释 "0.93.0"——扫描器跳过 `#` 注试行 + 非 active token——双保险不触发。

## 二、5 维度逐项结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | ✅ 通过 | 4 用例断言操作数与两源文件实况逐项相符；正则/ast 行为推演无误；边界全部前置拦截 |
| 安全性 | ✅ 通过 | 无外部输入/注入面/敏感数据；路径由 `__file__` 派生；纯只读断言 |
| 可维护性 | ✅ 通过（附 P3） | 命名达意、docstring 声明可证伪性与纪律出处、与文件既有风格一致；行号引用注释易腐见 F-6 |
| 性能 | ✅ 通过 | 两小文件 read_text + 一次 ast.parse + docstring 正则；对 1300s 级全量无可感贡献 |
| 测试覆盖 | ✅ 通过 | 验收①②各 2 用例；红路径四条真实；负路径显式消息；范围克制无冗余 |

## 三、发现列表（每条已标级别）

- **F-1（P3）披露失准——数词映射失败形态**：Developer 边缘披露③称 "Eleven → ERROR 而非干净失败"。代码事实相反：正则交替只匹配 One..Ten，"Eleven functions" 不产生匹配 → `assertIsNotNone` **干净失败**；`_WORD_COUNTS[...]` 的 KeyError 路径**不可达**。实际行为优于披露，代码无缺陷。处置：evidence 落盘时勘误该披露措辞，零代码改动。
- **F-2（P3）subtests 561→563 归因未证实**：+4 用例归因与 diff 内部一致（新代码零 subTest）✓；但「日期敏感 fixture 运行间方差」机制静态不可定位（全库 122 处 subTest 抽查均迭代固定常量/元组；固定常量不会增长）。裁决建议：delta 本身无害（双跑 0F/1S 恒定）不阻塞；归因按「未证实」入账，下次全量跑 per-file subtest 计数对比定位，复发再深查。
- **F-3（P3）STATIC_PIN 行号锚插入敏感——新实证**：事件机制核实为真（首版顶部 import → L323/L342 双锚位移 → stale-exemption WARN×2 → function-local import 重构恢复零位移；L504 先例属实）。计数双口径：session-snapshot 登记口径（FIX-422 两次为基）本次为**第三次实证**；version.py L306-329 审计链家族计数远超三次（FIX-373→388/380/382/410/411/421）。建议：作为内容锚定改造票的引用证据；`_bullet_names` 注释只提 L342，账本实际登记 L323+L342 两条（本次均保全）。
- **F-4（P3）import-face pin 仅覆盖模块级（残余缺口，已如实声明）**：函数级 `import verify_workflow`（纯导入无 I/O token）可逃逸两 pin；测试 docstring 已声明 scope。可选增强（后续票）：补 `assertNotIn("import verify_workflow", source)`。
- **F-5（P3）I/O token 扫描按设计过宽**：注释/docstring 含 token 即红——docstring 已声明为特性（fail-closed 取向，同 test_mirror 纪律）；当前零假红。属声明过的取舍。
- **F-6（P3）注释引用裸行号（L504/L342）**：与 STATIC_PIN 行号锚同族易腐；建议未来改「函数名+锚文本」式引用。不阻塞。

## 四、AI 代码专项 5 项

1. mock 残留：无 ✅ 2. 硬编码返回值：无（钉死值即 source-pinning 语义本体，与源码实况核实一致）✅ 3. 幻觉 API：无（re/hasattr/ast 用法真实正确）✅ 4. 未实现 TODO：无 ✅ 5. 过度实现：无（严格两个窄钉死，未框架化为通用 prose lint——正是裁决②边界约束）✅

## 五、设计一致性比对

- 与裁决链（review-FIX-424-CODE-R0 裁决② → FIX-425 R0 承接 → FIX-426.json demand_basis）：①source-pinning 模式 ✅ ②计数声称钉死 ✅ ③I/O-free 钉死 ✅ ④非通用 prose lint ✅ ⑤经 change-triage 立项 ✅
- 与 test_mirror_is_fully_retired：同型（read_text + assertNotIn 循环 + 失败消息含修复方向）✅
- 与 P-v4（测试看护/防护网）：三个评审周期的发现转机器拦截，P4 原则直接执行 ✅
- 与 D4（修改纯粹性）：单文件单一关注点尾部追加，零生产码变更；triage files 与交付一致 ✅

## 六、Developer 自报数据交叉核对（静态侧，未重跑）

定向 40（36+4）✓；全量 4662→4666P collection 恒等+4 ✓；新代码零 subTest（subtests 变化不可能来自本 diff）✓；4 用例断言操作数独立静态核验与源码现状相符 → 「现状绿」有独立静态依据。check-governance 0 FAIL 的 static-pin 面已结构核验通过，其余面由 Coordinator 复验。

## 七、三项边缘披露裁决建议（汇总）

① STATIC_PIN 事件：真实、修复形态正当；内容锚定改造票的引用证据（F-3，双口径计数）。② subtests +2：无害 delta，归因按「未证实」入账 + 复发时 per-file 定位（F-2）。③ 数词上限 Ten：披露的 KeyError/ERROR 形态不成立（实为干净失败）→ 勘误披露措辞即可（F-1）；">10 函数应重构模块"工程立场独立成立。

**硬门槛终检**：P0=0 ✓ · 5 维度 100% ✓ · 发现全标级 ✓ · 设计一致性完成 ✓ · AI 专项 5/5 ✓

**终态：APPROVED_WITH_NOTES（unresolved_blockers=0）**

## 限制声明

无 Bash：全部静态核验（未重跑测试/verify）；可静态核实的事实已全部独立核实。
