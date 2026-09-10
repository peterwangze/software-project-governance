# Code Review 报告 — FIX-301-R0（归档识别修复，工作树 diff，commit 前置）

- **Round**: R0（首轮）
- **任务**: FIX-301 归档识别修复（AUDIT-150 P0 REFACTOR-archive-recognition-fix）——可审计解释输出 + 识别面修复
- **审查对象**: 未提交工作树改动（2 文件）：`skills/software-project-governance/infra/archive.py`（+~300/−38）、`skills/software-project-governance/infra/tests/test_archive.py`（+344）
- **审查人**: Code Reviewer Agent（只读审查）
- **日期**: 2026-09-10
- **规范**: `agents/code-reviewer.md` + `skills/code-review/SKILL.md`（仓库全文，已加载）

---

## 1. 审查方法与采信边界

- **代码面**：逐行读取完整 diff + 改动后文件全文关键函数（`_parse_priority_table_tasks` / `_parse_completed_task_versions` / `_migrate_decisions` / `_migrate_risks` / `_migrate_evidence` / `_finalize_explain` / `migrate_by_version` / `_extract_tasks_from_archive_file` / `verify_archive_integrity` / `analyze_auto_archive_candidates` / `migrate_auto` / `main`）。
- **真实数据独立复算（只读）**：对 `.governance/plan-tracker.md` 与 `.governance/evidence-log.md` 用只读脚本复刻 FIX-301 解析语义，交叉印证 Developer 声称数字。
- **temp 副本运行采信边界**：Developer 的 temp 副本真实运行结果（迁 88 task/58 DEC/5 RISK/12 EVD、plan-tracker −19%、守恒 8/8、integrity PASS、幂等再跑 0、全量 31F/E 零新增（4 新失败 stash A/B 同败证存量）、健康 A/B 仅 +1 WARN=trigger gap 88）——**temp 目录未留存（%TEMP% 无 *archive* 目录），无法独立复核，本审查按任务书采信 Developer 声称**，并以静态方法学交叉印证（见 §2）。
- **测试运行采信**：test_archive 119→126（+7 红绿）未复跑（Reviewer 只读纪律），静态核实 7 个新测试逐一存在且断言与实现对应。

## 2. 真实数据交叉印证（Reviewer 独立只读复算）

| Developer 声称 | Reviewer 复算 | 结论 |
|---|---|---|
| 优先级表 208 行总量、旧代码仅见 32 行（RC-A） | ID 形状匹配行 208 = pipe==8 可解析 193 + pipe 异常 15；旧语义（任意非表格行终止）在真实表组间空行处即失活——`test_fix235_evidence_dry_run_reports_hot_task_rows` fixture（test_archive.py:3196 表头后空行）即为该形态活体 | **精确吻合** |
| in-range completed 88 行（迁移量） | 0.1.0~0.78.1 口径复算 95 行；--auto bounded endpoint（DEC-140 方案 A，终点=最新已发布前一版本）排除 0.78.1 行 + already-archived 排除后方向一致 | 方向一致（采信 temp 88） |
| 复合证据 ID `EVD-FIX-247` 被 regex 拒绝（RC-C，52 行不可见） | 复合形状（`EVD-[A-Z]+-\d+`）实测 45 行真实存在（EVD-FIX-275…EVD-REL-071 等）；旧 plain `EVD-\d+`（match 无锚）确不匹配复合 ID 的第 2 列取值 `EVD-FIX-247` | 机制证实；45 vs 52 为时点/口径差异，方向一致 |
| 粗体 ID `**REL-071**` 提取面盲（RC-D，88 迁移 vs 87 提取） | plan-tracker 实测 2 行粗体 ID 单元格（`**REL-071**`、`**REL-072**`）真实存在；旧提取 regex `\|\s*([A-Z]+-\d+)\s*\|` 对 `| **REL-071** |` 确实不匹配 | 证实 |
| pipe 异常防御必要 | 实测 15 行 pipe≠8（FIX-176=13、FIX-232/239/272/273/275=9 等——单元格含裸管道符，与 FIX-232 治理的 EVD-486/487 同类问题在 plan-tracker 重现） | 证实（守卫有真实负载） |

## 3. 审查重点逐项结论（任务书 ①~⑧）

### ① RC-A 组间容忍实现正确性 — **通过（附 P3-1 观察）**

- `archive.py:482-492`：扫描终止条件改为仅 heading（`###`/`##`）；表区域内非 `|` 行（空行/prose/blockquote）跳过不终止。与 FIX-235 兄弟解析器 `_parse_completed_task_versions`（archive.py:545-552）语义一致——**parity 声称核实成立**（两者均为 heading 终止 + pipe==8 守卫 + ID regex）。
- pipe-count 防御（archive.py:506-512）：置于 ID regex 之后——ID 合法但 pipe≠8 的行保守跳过并经 `anomalies_out` 上报（unknown-structure），**不迁移不删除**。方向正确：异常行误保留（可审计）优于误迁移（物理删除后列错位=数据损伤）。真实数据 15 行异常实测存在，守卫非空转。
- 误迁移边界评估：组间容忍使扫描跨越非表格行直至下一 heading；理论上若表后同 section 内存在「恰好 7 列且第 2 列为任务 ID 形状」的其他表格会被误识别。实测真实 plan-tracker 优先级表区域组间**仅空行**（无 prose/表格），且 pipe==8 + `^[A-Z]+-\d+$` 双重约束下误迁移面极窄 → P3-1 观察登记。

### ② explain 单源架构 — **通过（附 P3-2/P3-3 口径注记）**

- 核实成立：`_note`（decisions:929 / risks:1014 / evidence:1119）内嵌于各迁移函数的判定循环，would_archive 与 kept 分支同点发射；tasks 类别 `_note_task`（archive.py:1289-1292）内嵌于 `migrate_by_version` 两个扫描循环。`if not archived: return 0` 与 `if dry_run: return` 均在行记录收集之后——**解释与迁移行为同路径，不可漂移，声称成立**。
- early-return 面完备：plan-tracker 缺失 → 四类 `_finalize_explain([])` 零化（archive.py:1297-1302）；三类 log 文件缺失 → 空 scanned。`_format_explain_report`（archive.py:2938）对缺失类别 `isinstance` 防御。无 KeyError 面。
- `_migrate_evidence` 调用不再受 `evidence_task_versions` 非空门控（archive.py:1419）——空映射下全行归 no_archived_task_ref/live ref，无写入（`archived` 空 → return 0），换取真实 scanned 可见性。行为安全，注释（archive.py:1410-1415）如实声明。
- 口径注记见 P3-2（tasks 类别跨来源双计）与 P3-3（DEC/RISK 形状不匹配行无 note，与 evidence 面 unknown_evd_id_shape 不对称）。

### ③ RC-C regex 放宽面 — **通过（附 P2-1）**

- `archive.py:891`：`_EVD_ID_SHAPE_RE = ^EVD-(?:[A-Z]+-)?\d+$`——plain（EVD-969）+ 单段复合（EVD-FIX-247）双形状收编，加 `$` 锚（旧 `EVD-\d+` match 无锚）。
- **三面一致性**：迁移面（archive.py:1134）与提取面（archive.py:1715）共用同一常量 ✅；Check 3 index 计数 regex（archive.py:2184-2186，`[A-Z]+(?:-[A-Z]+)*-\d+` 无 $、多段容忍）比提取面宽——因 index 由提取面生成（同源数据），宽面不产生 mismatch，实测两段前缀 EVD 行 0 → 当前无实际影响（P3-4 注记：三面 regex 非同一常量，靠注释约定同步）。
- **过宽评估**：不过宽。单段前缀 + `$` 锚收口；`(?:[A-Z]+-)?` 不吞后缀变体（见 P2-1，方向为收窄非放宽）。
- **P2-1（发现）**：真实数据存在第三族形状——后缀变体 9 行（`EVD-231-FULL`、`EVD-224B`、`EVD-FEAT-010-R1/R2`、`EVD-FIX-271-1/R1`、`EVD-FIX-274-R1`、`EVD-FIX-288-BLOCKED`）。旧 regex（无 `$`）意外匹配其前缀；新 regex 拒收 → 归 `unknown_evd_id_shape`、永久保留热文件。**方向保守安全**（不迁移=无数据损伤，且 explain 可审计可见——优于旧行为的意外匹配），但 9 行真实证据行将永久不可迁移（28s 体积治理目标下的永久残留），且 docstring（archive.py:899-902 "two REAL shapes"）与事实（三族）不符。建议后续任务扩展形状（如 `^EVD-(?:[A-Z]+-)?\d+(?:-[A-Z0-9]+)?$` 类）并修正 docstring 措辞。

### ④ RC-D 粗体容忍 — **通过**

- 提取面两个 regex 均加 `(?:\*{0,2})`（archive.py:1666-1670 col-1 与 col-2 两分支）；迁移面 `re.sub(r"[`*]", "", raw_id)`（archive.py:503，既有）——**提取面与迁移面双向一致**。
- 测试 `test_fix301_bold_id_cells_extract_from_archive_file`（test_archive.py:3617-3644 附近）同时覆盖提取与 `_get_archived_task_ids()` 防再迁移双面。真实数据 2 行粗体 ID 实测存在（§2）。
- 边界：`** REL-071 **`（星号与 ID 间含空格）不匹配——保守漏，可接受（真实数据无此形态）。

### ⑤ P7 合规（不强删/写入原子性/失败路径）— **通过（附 P2-2 登记）**

- **强删路径：无**。pipe 异常行（unknown structure）、ID 形状未知行、live 任务引用行、open risk 行、no_task_family_ref 行全部 `kept_lines` 保留；物理删除仅作用于满足全部业务条件的 would_archive 行；version-section 侧另有 sample_table 行保护（archive.py:1540-1550，既有）。
- **写入顺序**：全部为「先写归档文件 → 后 rewrite 热文件」（tasks: archive.py:1534→1568；decisions: 983→985；risks: 1065→1066；evidence: 1205→1206）。中途崩溃最坏形态=「已归档未删热」→ 数据无丢失；重复归档落 incremental 独立文件（`_make_incremental_archive_filename`，archive.py:612-631，不 append 旧文件）。方向正确。
- **P2-2（发现）**：`_write_archive_file`（`open("w")`，archive.py:674-680）与热文件 `write_text` 均非原子（无 tmp+rename）。此为既有模式非本次引入，但 FIX-301 将单次可迁移量从 0 提升至 88+ 行，热文件 rewrite 中途崩溃的截断窗口爆炸半径显著放大。TRIAGE-FIX-301 的 files 范围仅 2 文件（不含备份机制）；plan-tracker L301 的「配备份+完整性校验」属**真实归档执行面义务**——temp 副本验证已体现该纪律。登记：真实归档在 .governance 执行前 MUST 外部备份先行 + 迁移后 `check-archive-integrity`（P7 红线），并建议后续任务评估 tmp+rename 原子写。
- 安全扫描：无硬编码密钥、无注入面（纯本地文件解析）、无权限越界。

### ⑥ 测试 +7 真实性 — **通过**

- `TestArchiveFix301` 七个测试逐一核实：组间容忍 + parity 守卫 / pipe 异常上报 / 端到端四类解锁（含 compound ID 落 archive+index、out-of-range/anomalous 保留、integrity pass）/ 复合 ID 隔离（迁移+提取双面）/ explain 结构（逐行 reason 精确断言）/ 粗体提取 / CLI skip 路径渲染（黑箱场景验收）。119→126 与 +7 吻合。
- **fixture 真实形态**：`_REAL_SHAPE_TABLE` 含 header+组 1+空行+blockquote+组 2+pipe 异常行。Reviewer 实测真实表组间仅空行（无 blockquote/prose）——fixture 比真实**更丰富**（过度覆盖，安全方向）；docstring "interleaves blank lines, prose and blockquote notes"（archive.py:449-451）略宽于实测形态（P3-5 注记）。
- 行为变更测试更新（`test_fix235_evidence_migrates_for_hot_completed_tasks`：tasks_archived 0→3、decisions 0→1）论证充分：REL-055 经 this-run 物理归档级联解锁 DEC-200（FIX-162 契约「关联 task 已归档」经 this-run 集成立）；FEAT-001（out-of-range 热 row）保底原 FIX-235 语义。`test_fix235_evidence_dry_run_reports_hot_task_rows` 不断言 tasks_archived，行为变更下不受影响。
- 测试未覆盖面（P3 捆绑）：prose（非 blockquote 文字）组间容忍无显式用例（实现已覆盖）；version-section+priority-table 同任务双计场景无断言（对应 P3-2）。

### ⑦ temp 副本采信边界 + 守恒方法学 — **采信（边界如实标注）**

- temp 目录未留存，temp 运行数值不可独立复核（§1）。
- 方法学交叉印证成立：208=193+15 精确吻合（§2）；「88 迁移 vs 87 提取」的粗体盲机制静态证实；幂等性（再跑 0）与 `already_archived` + incremental 文件名机制（archive.py:1355、1449）自洽；守恒 8/8 与「先写归档后删热」+ verify Check 3 对账机制自洽。
- 「全量 31F/E 零新增（4 新失败 stash A/B 同败证存量）」「健康 A/B 仅 +1 WARN=trigger gap 88（修复的正确产物）」——未复核，采信。trigger gap 88 与 §2 复算 in-range completed 量级自洽（95 含 0.78.1 行口径差）。

### ⑧ AI 专项 5 项 — **全部通过**

| # | 检查项 | 结论 |
|---|---|---|
| 1 | mock 残留 | 无——产品代码零 mock/patch；测试 `patch.object(ROOT/PLUGIN_ROOT)` 为本仓既定 temp-root 手法 |
| 2 | 硬编码返回值 | 无——`_finalize_explain`（archive.py:1221-1252）纯聚合计算，无魔法数返回 |
| 3 | 幻觉 API 调用 | 无——全部标准库（re/pathlib/datetime/tempfile 语义），无虚构接口 |
| 4 | 未实现 TODO | 无——diff 内零 TODO/FIXME/占位 |
| 5 | 过度实现 | 无——explain 四类+CLI 双路径渲染均在任务书「可审计解释输出」范围内；两处 regex 修改最小必要 |

## 4. 发现列表

### P0（阻塞）— 0 项

### P1（关键）— 0 项

### P2（建议）— 2 项

- **P2-1** `skills/software-project-governance/infra/archive.py:891,899-902,1134-1139` — `_EVD_ID_SHAPE_RE` 未覆盖第三族真实形状（后缀变体：`EVD-FIX-271-R1`/`EVD-224B`/`EVD-FEAT-010-R1` 等实测 9 行）。新 regex 将其归 `unknown_evd_id_shape` 永久滞留热文件（保守安全、可审计，优于旧代码意外前缀匹配），但 9 行真实证据永不迁移与 28s 体积治理目标冲突；docstring "two REAL shapes" 与三族事实不符。建议：后续任务评估形状扩展（含 `-R1`/`-BLOCKED`/`B` 后缀）+ docstring 修正；explain 的 unknown_evd_id_shape 清单已提供审计入口。
- **P2-2** `skills/software-project-governance/infra/archive.py:674-680,1534,1568,983-985,1065-1066,1205-1206` — 归档文件写与热文件 rewrite 均非原子（无 tmp+rename，既有模式），FIX-301 使单次迁移量升至 88+ 行，热文件截断崩溃窗口的爆炸半径放大；且 diff 无代码级备份（TRIAGE files 范围仅 2 文件）。处置：真实归档在 .governance 执行前 MUST 外部备份先行 + 完整性校验收尾（P7 红线，执行面义务）；建议后续任务评估 tmp+rename 原子写。

### P3（讨论）— 5 项

- **P3-1** `archive.py:490-492` — 组间容忍后扫描可跨越非表格行直至下一 heading；「同 section 内后续 7 列表格且第 2 列恰为任务 ID 形状」理论上可被误识别。实测真实表区域组间仅空行、双重约束（pipe==8+ID regex）下风险极窄。观察项：真实 plan-tracker 结构演化时留意。
- **P3-2** `archive.py:1313-1374` — explain tasks 类别：同一任务同时出现于 version section 与 priority table 时贡献 2 条记录（would_archive + already_archived），scanned 虚增。实测真实 plan-tracker 仅 1 个 version section（`### 1.0.0 依赖链`，预留版本 out of range），实际影响趋零；fixture 场景口径可议。
- **P3-3** `archive.py:945-947,1034-1036` — DEC/RISK 循环中 ID 形状不匹配行 kept 无 note（evidence 面对应分支有 unknown_evd_id_shape note），四类 explain 的「未知结构」口径不对称。`DEC-\d+`/`RISK-\d+` 为唯一真实形状，实际影响趋零。
- **P3-4** `archive.py:2184-2186` — Check 3 计数 regex（多段前缀容忍、无 $）与 `_EVD_ID_SHAPE_RE`（单段、有 $）非同一常量，靠注释约定同步。当前数据无两段前缀 EVD（实测 0 行）且 index 与提取同源，不产生 mismatch；建议后续统一为共享形状定义。
- **P3-5** `archive.py:449-451`（docstring）— "interleaves blank lines, prose and blockquote notes" 中 prose/blockquote 宽于实测（真实组间仅空行）；fixture 已含 blockquote（过度覆盖，安全方向）。措辞事实校准建议。

## 5. 五维度结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 1 正确性 | ✅ 通过 | RC-A/B/C/D 实现逐行核实正确；边界处理保守方向一致；独立复算 208=193+15 精确吻合；explain 单源架构成立 |
| 2 安全性 | ✅ 通过 | 零强删路径；先归档后删热写序；无注入/密钥面；P2-2 原子性既有债务放大已登记（执行面备份义务） |
| 3 可维护性 | ✅ 通过 | `_note` 单源收集、`_EVD_ID_SHAPE_RE` 共享常量、docstring 详实带根因锚；P3-4 共享常量统一建议 |
| 4 性能 | ✅ 通过 | 全线性扫描（O(rows)），无 N+1；`_migrate_*` 空映射仍全扫为审计可见性，开销可接受（454 EVD 行级） |
| 5 测试覆盖 | ✅ 通过 | 7 新测试真实复刻形态（组间+异常+粗体+复合 ID）+ 端到端含 integrity；红绿与全量零新增采信 + 静态印证 |

## 6. 硬门槛裁决

| 门槛 | 阈值 | 实测 |
|---|---|---|
| P0 阻塞数 | = 0 | **0** ✅ |
| 5 维度全覆盖 | 100% | 5/5 ✅ |
| 每条发现标注级别 | 100% | P2×2 + P3×5 全标注 ✅ |
| 设计一致性检查 | 已完成 | 与 FIX-235/243（DEC-140 bounded endpoint）/162/164/170/172 既有契约逐项比对无偏离；FIX-235 行为更新有测试论证 ✅ |
| AI 专项 5 项 | 全部完成 | 5/5 ✅（§3⑧） |

## 7. 审查结论

**APPROVED_WITH_NOTES**

- **unresolved_blockers=0**
- P0=0 / P1=0 / P2=2（P2-1 第三族 EVD 形状、P2-2 原子写+执行面备份义务——均非阻塞，附处置建议）/ P3=5（观察/口径/措辞级）
- 通过理由：四根因修复实现正确且经真实数据独立复算印证；explain 单源架构名副其实；识别面与提取面/索引面三面同步；P7 无强删、写序安全。P2 两项均为后续债务方向，不构成本次合并阻塞。
- 遗留项（建议登记后续任务）：P2-1 EVD 后缀变体形状扩展；P2-2 tmp+rename 原子写评估；真实归档执行时的外部备份 + `check-archive-integrity` 收尾（P7 执行面义务，M 阶段 MUST）。

## 8. 采信与未验证声明

- 未独立复核（采信 Developer，方法学自洽性已交叉印证）：test_archive 126 全绿、全量 31F/E 零新增（stash A/B 同败）、temp 迁移数值（88/58/5/12、−19%、守恒 8/8、幂等）、健康 A/B +1 WARN。
- 已独立复核（Reviewer 只读复算/逐行核实）：208 行分解、pipe 异常 15 行、粗体 ID 2 行、复合 EVD 45 行、后缀变体 9 行、版本 section 1 个、全部代码路径与测试断言对应关系。
