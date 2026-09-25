<!-- machine-record: FIX-384 | reviewer: code-reviewer | round-suggestion: none | verdict: APPROVED_WITH_NOTES | unresolved_blockers=0 -->

# Code Review R1 — FIX-384 B-7a 归档 index-rebuild（M7.4 T1 同席复审）

- **轮次声明**：R1；前轮引用 `docs/reviews/review-FIX-384-CODE-R0.md`（R0 = NEEDS_CHANGE，unresolved_blockers=1——P1-1 Check 3 口径不对称 + P2-1 测试缺口）。本轮按复审协议逐条比对前轮 findings（§4），全部实测以当前工作树 diff 为准。
- 审查对象：工作树未 commit diff，2 文件——`infra/archive.py`（实测 numstat **+328/−35**；R1 增量 Δ+68/−21）、`infra/tests/test_archive.py`（+460/−0；R1 增量 Δ+64 = 2 测试）；基线 HEAD `14797be`（R0 时 `a8afcbf`，期间并行 FEAT-062 落地、`.governance/` 保持干净）
- 审查者：Code Reviewer Agent（只读；实测在 `%TEMP%\fix384_r1_*` 隔离副本内，真实 `.governance/` 零写入）
- 结论：**APPROVED_WITH_NOTES**（unresolved_blockers=0——P0=0、P1=0；P1-1/P2-1 已修实证，P3 备查项与新微观察见 §4/§7）

## 1. R1 核验项 1——P1-1 修复形态（方向 (a)）✅

**共享函数单一来源达成，build 与 verify Check 3 同源调用，永不漂移：**

| 证据 | 结果 |
|---|---|
| 新增 `_extract_decisions_from_archive_file`（L1865-1891） | ✅ canon = build 严格式 `##\s+(DEC-\d+):\s*(.*)`（L1890） |
| 新增 `_extract_risks_from_archive_file`（L1894-1925） | ✅ canon = ≥4 cells 可索引（L1919-1924） |
| build_index 调用侧 | ✅ decisions L2199-2206、risks L2227-2234——内联正则/循环已删除 |
| verify Check 3 调用侧 | ✅ decisions L2487-2489、risks L2494——`^##\s+DEC-\d+` findall 与 risks 前缀计数循环已删除 |
| 全仓残留扫描 | ✅ `^##\s+DEC-\d+` 仅存于 verify 注释（L2484，历史记录）；decisions 提取正则全仓唯一命中 = 共享函数 L1890；risks 计数共享函数唯一（L1166 为 `_migrate_risks` 从热 risk-log 提取——写侧管线，不属 build/verify 口径对） |
| 死循环根因与口径裁决入档 | ✅ 两函数 docstring 记录 R0 P1-1 根因（两种正则→Check 3 永不 PASS→"Run build_index()"死循环）+ canon 裁决理由；build/verify 调用侧均有 `REVIEW-FIX-384-R0 P1-1` 注释 |

**canon 口径裁决合理性（verify 放宽旧口径有无合法依赖）——独立论证：无合法依赖，严格式正确。**
1. **writer 对齐**：`_migrate_decisions` 实际写 `## {dec_id}: {title}`（L1100-1101，冒号式）；risks 写侧行均带尾管（≥4 cells）。canon 与唯一合法写入者逐字节同构。
2. **真实数据合规**：真实仓库 12 个 decisions 文件 0 个无冒号头（R0 已测）；R1 后真实仓库只读 verify 仍 PASS 且 1131/1276 计数与 R0 逐字相同——放宽→收紧的口径切换在真实数据上零漂移（§3）。
3. **旧宽松口径无消费者**：`file_counts` 仅被 Check 3 比较消费；`total_archived_tasks` 只含 tasks+evidence（L2496），decisions/risks 计数无其他读取者；全仓 grep 无第三处 lenient 模式消费。
4. **损伤头去向正确**：冒号损坏头按 FIX-384 设计落入无条目登记路径（非计数对象）——与「登记只恢复视图，不创造数据」一致。

## 2. R1 核验项 2——红绿判别力（P2-1 两个新测试）✅

| 项 | 结果 |
|---|---|
| 测试 1 `test_rebuild_passes_with_colon_damaged_decision_header`（test_archive.py L1275-1302） | ✅ fixture = `## DEC-001 Use SQLite…`（冒号丢失，decode-clean）；断言 `verify_pass` + 无条目登记（L1294-1302）——旧口径下该断言恰为红点（verify 计 1 vs 索引 0 → FAIL） |
| 测试 2 `test_rebuild_passes_with_truncated_risk_row`（L1304-1329） | ✅ fixture = 2-cell 截断行；同型断言（L1321-1329） |
| 红相签名逐字复现（本审查实测，R0 §6 P1-1 同源） | ✅ 在两个新测试的**精确 fixture** 上以旧口径内联重算，产出逐字签名：`Archive/index count mismatch (Check 3, category=decisions): archive files contain 1 but index.md has 0. Run \`archive.py build-index\` to rebuild the index, then re-verify.`（risks 同型）——与 R0 实测记录及修复声明引用的死循环签名一致 |
| 绿相 | ✅ 同 fixture 下新 `rebuild_index()` → `verify_pass=True` + 文件登记「无条目」（探针 `r1_green_*` 4/4） |
| 判别力说明 | 测试内未内嵌红相断言（红相由 docstring 记录 + 本审查外部复现钉死）——见 §7 微观察 |

## 3. R1 核验项 3——复现（仓库根口径）✅

| 项 | 命令/方式 | 实测 |
|---|---|---|
| 票面套件 | `pytest tests/test_archive.py -q` | **140 passed**（138+2，与申报一致；TestArchiveIndexRebuild 现 14 方法） |
| 相邻 4 套件 | `pytest tests/test_archive_decision_attribution.py tests/test_decision_migration.py tests/test_decision_migration_verify.py tests/test_decision_repository.py -q` | **66 passed**（14+22+7+23，与申报口径吻合）；五文件合计 1 条命令 **206 passed, 4 subtests**（17.10s） |
| 真实仓库 verify（只读） | `archive.py verify --project-root .` | **Pass: True**（1131/1276，与 R0 计数逐字相同——口径切换零漂移） |
| 单一来源 lockstep（混合损伤树实测） | 隔离副本：健康+无冒号+decode 损坏+截断行+U+FFFD 混合 | 共享函数重算 file counts == 索引行数 == result 计数（decisions 2/2/2、risks 1/1/1）+ verify PASS + 损伤文件 damaged_files 双报（探针 `r1_lockstep_*`） |
| 真实归档隔离副本 | copytree → rebuild ×2 | verify PASS、归档文件字节不变、二轮 no-op、`damaged_files=[]`；**首轮 changed=True 为诚实行为**——差异仅 122 字节 = 「非结构化归档」小节头文案更新（FIX-384 三行新版 vs 已提交索引的 FIX-176 两行旧版，`difflib` 证实仅此 1 hunk、**1305 行条目行零漂移**） |

## 4. R1 核验项 4——R0 findings 逐条比对

| R0 编号 | 内容 | R1 状态 |
|---|---|---|
| P1-1 | Check 3 与 build 口径不对称，损伤 decisions/risks 重建 PASS 不可达+死循环建议 | **已修复**（方向 (a)——共享函数单一来源，§1 全项实证；红绿双相实测 §2） |
| P2-1 | decisions/risks 登记分支与损伤恢复零测试 | **已修复**（+2 测试恰钉两个红相角落，均兼断无条目登记——登记分支覆盖补齐） |
| P3-1 | 申报 numstat +274 vs 实测 +260/−14 | 维持（口径修正建议已入档）；R1 现值 +328/−35（Δ+68/−21 与修复声明相符） |
| P3-2 | 非 ID 列 U+FFFD 透传 + changed 解码文本比较 | 维持（探针 `r1_p3_ufffd_no_fabrication_unchanged`：ID 格伪造防护不变；透传面未变化） |
| P3-3 | 换行损坏行混合（7 列 FIX-302 丢失/FIX-301 污染） | 维持（探针 `r1_p3_row_blend_persists_as_documented`：行为逐字节同 R0——边界未声明，维持建议） |
| P3-4 | unreadable narrative-* 登记标签 | 维持（未触碰） |
| P3-5 | empty-file 全链测试缺预态断言 / unreadable 命名 | 维持（未触碰） |
| P3-6 | build-index CLI 不打印 damaged_files | 维持（未触碰） |

## 5. R0 报告更正（审查者自纠）

R0 §2① 写有「真实归档隔离副本**首轮** rebuild 输出与已提交 index.md 逐字节一致」——该句**失准**：R0 实际测量的是「二轮==一轮 && 二轮 changed=False」，未直接比对首轮输出与已提交索引。R1 精确测量还原真相：首轮 rebuild 与已提交索引相差 122 字节，**全部为「非结构化归档」小节头文案更新**（FIX-384 设计内变更），条目行 1305 行零差异。据此：(a) 「errors="replace" 对健康数据零行为变化」的论证结论不变，但正确依据是**条目行零漂移**而非整文件字节一致；(b) R1 申报「健康 DEC 头 Decision entries=1 零变化」实测成立（条目级）。更正不影响 R0 结论链。

## 6. 五维度裁决（R1 增量面）+ AI 专项

| 维度 | 结论 |
|---|---|
| 正确性 | ✅ 共享函数语义与 R0 build 侧逐字符同构（正则/cell 规则未变）；两侧同源后 Check 3 不可能再漂移；混合损伤树 lockstep 实测 2/2/2、1/1/1 |
| 安全性 | ✅ 无新写面（共享函数只读；verify/build 落点不变）；fail-visible exit 1 语义保持 |
| 可维护性 | ✅ 净删除重构（−21 行内联逻辑）；docstring 根因+裁决入档；消除了 R0 指出的口径分叉根因 |
| 性能 | ✅ 每文件一次共享提取，verify 与 build 各自调用一次，无新增重读 |
| 测试覆盖 | ✅ 两个红相角落钉死 + 登记分支覆盖补齐；140+66 全绿 |

**AI 专项 5 项（R1 增量）**：① mock 残留：无（既有 ROOT seam 惯例）；② 硬编码返回值：无；③ 幻觉 API：无（共享函数仅 stdlib re/pathlib；调用键真实）；④ 未实现 TODO：无；⑤ 过度实现：无——两函数最小实现、无夹带重构（hunk 比对：R1 唯一新增块 = 共享函数 +63 行，其余为调用侧净删除）。

## 7. 新观察（均非阻塞，P3 级备查）

- **N-1（台账）**：FIX-384 两轮合计对 archive.py mainfile 净增 +258 行（HEAD 基线 ~3422→3680），计入 archguard R1/mainfile 既有欠账台账（`test_r1_passes_on_current_tree` 在 HEAD 即红，R1 失败签名不变——本票未引入新违规模式）。归 0.88 阶段 A 契约卫生域。
- **N-2（口径备忘）**：`_extract_risks_from_archive_file` 保留 `re.match(r"RISK-\d+", risk_id)` 前缀匹配（非 fullmatch）——这是 canon=build 严格式的忠实保留（R0 前既有行为），意味着 `RISK-001x` 仍按 RISK-001 索引。属既有口径，非本票引入；如需收紧应另立票。
- **N-3（测试微强化候选）**：两个新测试的红相由 docstring+外部复现钉死，测试体内未断言旧口径签名；可选强化：fixture 上先断言 `assertNotIn("Archive/index count mismatch", ...)` 型预态（对当前代码恒真，锁死回归方向）。不阻塞。
- **N-4（诚实行为确认）**：代码更新后对真实归档首轮 rebuild 必然 `changed=True`（小节头文案）；运维预期应表述为「首轮 changed=True 属正常，二次起 no-op」——CLI 输出已如实反映。

## 8. 结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`（无 P0/P1）。

P1-1 按方向 (a) 修复且形态优于最低要求（writer 对齐论证 + 残留扫描清零 + 红相签名逐字复现钉死）；P2-1 补测恰中两个角落。140P + 相邻 66P + verify（仓库根口径）全部复现；真实数据零漂移；R0 findings 8 条全部闭环（2 修复 + 6 维持备查）。2 文件可合并；N-1~N-4 随本审查转 Coordinator 备查，不构成合并前置条件。

*取证留存：`%TEMP%\fix384_r1_probe.py` / `fix384_r1_probe_results.json` / `fix384_r1_diff.py`；本报告为唯一仓库内写入物。*
