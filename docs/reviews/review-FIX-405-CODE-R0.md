# Review: FIX-405 + B4（授权合并批）— CODE R0

- **Task**: FIX-405（SD 完好性扫描门——RISK-061 终局处置）+ B4 四件（B4-1 intake mirror / B4-2 INV 拆臂 / B4-3 BLOCKED 臂 / F-3 packet note）+ regen rider
- **Reviewer**: Code Reviewer Agent（独立，R0）
- **基线**: HEAD=344ec8c（工作区未提交变更）
- **Round**: R0（首轮）
- **结论**: **APPROVED_WITH_NOTES**（unresolved_blockers=0；P2×3 + P3×4，均非阻塞）
- **范围排除**: `infra/archive.py`（+353/-76）与 `tests/test_archive.py`（+291/-32）属 FEAT-076 并行任务——未评审、未触碰 ✓

## 0. ⚠ 审查期间工作区竞态披露（Coordinator 必读）

审查进行中（16:47:01），`verify_workflow.py` 被并行任务追加了两个**不属于本批八项审查对象**的 hunk：

- `@@ GovernanceDataSource`（+120 行）
- `@@ check_governance_data_size`（+20 行）
- 另出现新 M 文件 `checks/review_domain.py`

处置：①FIX-405 全部静态计量（行数 26965 / print 1338 / +52−8=净+44）在竞态发生**前**完成三重交叉验证（python readlines / AST / git numstat），对 FIX-405 快照成立；②新增 +140 行**未评审**（范围外，属并行任务）；③当前 live 行数 27105 **已超**本批 rider 锚 26965——ratchet 只升不降语义要求**下一个任务的 rider 负责抬锚**（非本批缺陷，本批快照 26965 精确）；④所有测试复跑在混合树上执行且全绿（同时证明 FIX-405 面与并行工作共存无冲突）。

## 1. 八项验收核验

| # | 验收项 | 判定 | 事实依据 |
|---|--------|------|---------|
| ① | SD 门语义（探测面=投影+hooks；OSError 保守；takeown/icacls 正确性） | **通过** | 探测面：write 面=`projection_face_paths`（live plan）[sd_integrity.py L70-84 → verify_workflow.py cmd_release_projection]；readiness 面=投影+hooks 目录+4 hook 文件（verify_workflow.py L7528-7530 实读）✓。OSError→`readable=False` 计不可读（scan_sd_readability L100-103，fail-closed 方向正确；该分支无专项测试→P3-5）。修复命令语法逐项核验：`takeown /f "<path>"`、目录变体 `/r /d y`、`icacls "<path>" /grant "%USERNAME%":F`（+`/t`）——`"%USERNAME%":F` 经 CommandLineToArgvW 解析为 `user:F` 单参数，与惯用 `"user:F"` 等价，语法正确；外国所有者 ACE 修复需管理员壳属该修复类固有约束非语法缺陷 |
| ② | intake mirror 与 Check 17 谓词一致性 | **通过（带注记）** | 四子字段（获得/感知/体验变化/迁移指南）存在性：两侧同判缺失=罚 ✓；枚举成员：`_VALID_OBTAIN_VALUES`（7 值）与 Check 17 `VALID_OBTAIN_VALUES`（L13291-13294）逐值比对**完全一致** ✓；passage 终止符集：两侧同为 目标对齐/范围/依赖/架构影响/结尾 ✓（mirror 多 re.S、少 `\s*`——表格单行单元格内语义等价）。**偏差（均 fail-closed 方向或范围残余）→ P2-2**：镜像枚举精确匹配 vs Check 17 contains 匹配；子字段值终止符 `[^,，;；]` vs Check 17 终止符型非贪婪（句读分隔形态下 mirror 过拒）；Check 17 第 5/6 条 BLOCKING 矛盾（体验变化=是+迁移指南=不需要）未镜像——注释"EVD-1252 类永不能再写入"**过度声明** |
| ③ | INV 拆臂语义 + ADR §2.2.3 引用真实性 | **通过** | ADR-021（docs/architecture/ADR-021-meta-mechanisms.md L206）原文实读：「排序键正确时本判据恒不触发，触发即排序实现缺陷或手写推荐绕过，两者都该 FAIL」——引用真实 ✓。分支结构核验（provenance_domain.py L228-269）：同 P 级→INV-1 FAIL（原臂不动）；`rank_m < rank_u`（M 更高优先级=D1 已知容忍）→INV-X WARN 臂**保留未动**（与 ADR L207 一致）；未解析→WARN（保守披露）；新增 `rank_m > rank_u`（已解析且 M 严格更低优先级排前）→INV-1 FAIL——正确排序键下不可能形态，L206 立论成立。注记→P3-3（该形态未入任何规范性条款，属立论延伸补缝，建议 ADR 微注收编） |
| ④ | BLOCKED 臂配对语义 | **通过** | `_collect_session_closure_events`（L7378-7386）：BLOCKED 并入 NEEDS_CHANGE 作 problem 事件；closure 仍=APPROVED* / EVD ✅。ADR §3.2.2（L334-335）实读：会话内配对判据 + 「未配对即计入未闭环（宁可多计不可漏计）」——BLOCKED=未通过终态计 problem 与该保守计数原则一致 ✓；BLOCKED 后无后续 review 行的形态（用户裁决终结）会保守挂 WARN，方向正确。测试 `test_collect_session_closure_events_blocked_review_is_problem` 覆盖 problem+closure 配对 ✓ |
| ⑤ | R4 print 零增殖 | **通过** | 独立 AST 计数 `print` 调用=**1338** == FACTS_PRINT_TOTAL（test_archguard_ratchet.py L99）；diff 逐行确认零新增 print（readiness 面经聚合 details 渲染、write 面复用既有 print）；ratchet `test_r4_total_matches_facts_census` 复跑 PASS（混合树上亦 1338——并行代码同样零 print） |
| ⑥ | regen +44 lineage | **通过** | git numstat verify_workflow.py = **+52/−8 → 净+44**；26921+44=**26965**；实测物理行数 **26965**（python readlines）== anchor_loc；baseline JSON +2/−2（git_head→344ec8c… 与 HEAD 一致、anchor_loc→26965）；ratchet 断言已更新至 26965 且带 lineage 注释，`-k anchor` 复跑 PASS。⚠ 竞态后 live=27105>26965——抬锚义务归并行任务的下一次 rider（§0） |
| ⑦ | 测试质量（声明复跑） | **通过（带注记）** | 实测（TEMP 重定向 `.governance/tmp/check-run-20260929`，一次性全绿零重试）：store 全量 **108 passed**（=声明 108 ✓）；provenance 全量 **36 passed**（收集 36 vs 声明 38，Δ2）；test_verify_workflow 定向选择（SdIntegrity/collect_session_closure/ExecutionPacketIncremental）**12 passed**；ratchet 定向（anchor/census）**2 passed**。声明 **312 无法归因**（-k release=114、扩选择器=124、全文件收集 1006 均不匹配；禁全量未复验）→P3-4。新增测试质量良好：注入式 access 模拟拒绝、零字节拒（evidence_bytes 前后相等）、无 passage 零行为变化、readiness 面兄弟子检查 patch 隔离；缺口：--write 接线无测试（P2-3）、OSError 抛出分支无测试（P3-5） |
| ⑧ | 零范围外（偏差清单核对） | **通过** | git status 逐文件核对：9 M + 1 新增 = sd_integrity.py（新 leaf）+ verify_workflow.py（六 hunk：collector/readiness/note/projection-docstring/--write 接线）+ governance_store.py + provenance_domain.py + architecture-baseline.json（rider）+ 四测试文件——与本批八项审查对象 **1:1 对应**；archive.py/test_archive.py/review_domain.py/GovernanceDataSource hunk = FEAT-076 等并行任务（§0 竞态披露），非本批产物。本 Reviewer 全程只读（零产品代码写入） |

## 2. 五维度结论

| 维度 | 结论 | 要点 |
|------|------|------|
| 正确性 | 通过 | 六 hunk + leaf 逐行实读；分支边界（P 级四态、passage 触发、plan 空路径）逐一推演；F-3 `sorted(selected)` 报实集正确；缺陷仅 P2-1 fail-open 缝（低概率）与 P2-2 谓词边差（fail-closed 方向） |
| 安全性 | 通过 | 无输入注入面（路径来自 live plan/常量 hook 名）；无硬编码密钥；SD 扫描本身只读探测；remediation 模板输出到 JSON/issues 非执行 |
| 可维护性 | 通过 | leaf 单一职责（测量+指引，checks/ 分层符合 ArchGuard R1）；可注入 access 设计优良；P2-2c 注释过度声明需收敛 |
| 性能 | 通过 | 扫描 O(n) 路径数=投影目标+5；`projection_face_paths` 在 readiness 与 --write 各重建一次 plan（可接受，write 面本就需重建） |
| 测试覆盖 | 通过（带注记） | 11 个新测试覆盖 leaf/镜像/拆臂/配对核心路径与错误路径；缺口 P2-3（--write FAIL→exit1 无测试）、P3-5（OSError 分支） |

**AI 代码专项 5 项**：mock 残留=无（patch 均在测试内且即时还原）✓；硬编码返回值=无（test_release_readiness 测试的 fake 返回值属测试合法注入）✓；幻觉 API=无（build_projection_plan/PlannedWrite.relative_path 于 release/projection.py L131/L19 实存核验）✓；未实现 TODO=无 ✓；过度实现=无（八项对象外零多余面）✓。

## 3. Findings

| # | 级别 | 位置 | 问题 | 建议 |
|---|------|------|------|------|
| F-1 | **P2** | checks/sd_integrity.py L79-84 + verify_workflow.py L7528-7529 / cmd_release_projection | `projection_face_paths` 的 `error` 键在两个调用点均被 `.get("paths", [])` 丢弃：plan 构建失败时 SD 面空集**空转 PASS** 且错误串静默消失——与 leaf docstring「the SD scan never silently skips」不符。补偿面：--write 路径上 `write_projections` 先建同一 plan、同类异常返回 BLOCKED（exit 3，响亮）；readiness 聚合内**无其他** plan 构建子检查（projection_sync 是另一面），仅 stage-release 序列的 release-projection 兜底 | 调用点把 `error` 键提升进 details/issues（如 `details["sd_integrity"]["plan_error"]` 或直接计 issue），一行级修改 |
| F-2 | **P2** | governance_store.py L1067-1116 | 与 Check 17 谓词存在三处漂移：(a) 枚举精确匹配 vs Check 17 contains 匹配（`获得=见 plugin update 文档` Check 17 容、mirror 拒）；(b) 子字段值终止符 `[^,，;；]` 贪婪 vs Check 17 终止符型非贪婪（句读「。」分隔形态 mirror 拒、Check 17 过——本批被迫改测试 fixture 即同类证据）；(c) Check 17 第 5/6 条 BLOCKING 矛盾（体验变化=是+迁移指南=不需要）未镜像——该形态仍可写入后红灯，注释「EVD-1252 类永不能再写入」**过度声明**。(a)(b) 为过拒方向（fail-closed），(c) 为残余漏洞方向但属 Coordinator 规定的镜像范围（四子字段+枚举）之外的 Check 17 规则 | 提取共享解析器（单一事实源）或：镜像补齐第 5 条矛盾规则 + 收窄注释声明 + 注明「intake 严于 check」为有意姿态 |
| F-3 | **P2** | verify_workflow.py cmd_release_projection --write 接线 | `sd_integrity` 入 result JSON、FAIL 覆写 state、exit 1 映射——门禁的"牙齿"（退出码）**无自动化测试**（SdIntegrityGateTests 覆盖 leaf 与 readiness 面，未覆盖 --write 接线） | 后续补测：抽取 sd 附加逻辑为可测 helper，或 argv 级测试断言 exit code（write_projections 已有 `replace=` 注入点可避免真实写） |
| F-4 | P3 | cmd_execution_packet note（F-3 任务项） | `sorted(selected)` 报实集修改正确（逐行核验：`selected`=生成 payload∩wanted，缺席 id 不再显示为 regenerated）但无测试断言 note 文本 | 既有 ExecutionPacketIncrementalWriteTests 补一条 stdout 断言 |
| F-5 | P3 | sd_integrity.py remediation_for L51-58 | 受损目录 `is_dir()` 失败（OSError→False）时落文件模板：仅愈目录自身 ACE、无 /t 继承。子文件由扫描逐个出命令故覆盖不丢，仅失继承愈合力 | 可忽略或按 HOOK_FACE 名单判定目录形态 |
| F-6 | P3 | ADR-021 §2.2.3（L206-207） | 新拆臂（已解析 rank_m>rank_u）不在任何规范性条款内（INV-1=同级、INV-X=M 更高），立论依据是 L206 的理由句延伸——代码注释如实标注「立论」但 ADR 文本未收编该形态 | ADR 下次编辑机会补一行微注（B4-2 拆臂收编） |
| F-7 | P3 | 开发者交接声明 | 声明测试数 312+38+108：108 ✓ 精确；38 vs 实测收集 36（Δ2）；312 无法归因到任何合理选择器（-k release=114 / 扩选择器=124 / 全文件 1006） | 后续交接附可复现命令行，避免计数不可归因 |

## 4. 硬门槛裁决

- P0 计数 = **0** ✓
- 五维度 100% 覆盖 ✓（§2）
- 每条发现标注级别 ✓（P2×3 / P3×4）
- 设计一致性检查（对 ADR-021 / Check 17 / 任务规格）：已完成 ✓（验收②③④逐条源文实读）
- AI 代码专项 5 项：全部完成 ✓

## 5. 复跑证据汇总（TEMP=.governance/tmp/check-run-20260929；重试 0/2）

| 命令 | 结果 |
|------|------|
| pytest tests/test_governance_store.py + tests/test_provenance_domain.py | **144 passed**（108+36）in 3.43s |
| pytest tests/test_verify_workflow.py -k "SdIntegrity or collect_session_closure or ExecutionPacketIncremental" | **12 passed**, 994 deselected |
| pytest tests/test_archguard_ratchet.py -k "anchor or census" | **2 passed**（anchor 26965 + print 1338） |
| verify_workflow.py check-release --skip-execution-gates | `[PASS] sd integrity`（新面渲染通过）；FAILED/exit 1 的 4 issue 均为本批外面：version consistency 0.92 措辞 / archive 归档触发缺口（FEAT-076 域）/ loop claim 身份证明 |
| verify_workflow.py check-governance --summary-only | exit 0；顶部 FAIL 含 Check 17×EVD-1252 历史行（B4-1 所防类的存量实证——镜像防新增、不追诉历史）与 FEAT-076 缺包（并行任务域） |

## 6. 裁决

**APPROVED_WITH_NOTES** — unresolved_blockers=0。八项验收全部成立（②⑦带注记）；P2×3 均为加固/一致性收敛项，不构成合并阻塞。附加义务移交 Coordinator：①竞态披露 §0（并行任务抬锚义务 + review_domain.py/GovernanceDataSource 未评审声明）；②F-1/F-2 建议随下一批次闭环（发现即闭环原则下若本批内可一行修 F-1 更佳）。
