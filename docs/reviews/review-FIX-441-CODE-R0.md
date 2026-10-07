# REVIEW-FIX-441-R0 — archguard 基线 sanctioned regen rider 审查报告

**round = 0（R0 初审）** ｜ Reviewer: Code Reviewer Agent ｜ 2026-10-07
**审查面声明**：本票为纯基线 regen 执行票（DEC-324 裁定、DEC-320 先例同构），审查面收敛为两文件实读 + 非掩蔽性核验；审查为只读（未运行任何命令），开发者声称的执行结果均按「未复跑/台账采信」如实标注。裁定链 DEC-324 / DEC-320 行已实读。

**受审对象**：工作树 staged 变更（未 commit，基线 HEAD `1a56797`）
1. `skills/software-project-governance/core/architecture-baseline.json`
2. `skills/software-project-governance/infra/tests/test_archguard_ratchet.py`

---

## 一、非掩蔽性逐值对账表（核心审查面）

| # | 轴/值 | 旧→新 | 对合证据（实读） | 裁决 |
|---|-------|-------|------------------|------|
| 1 | R1 `anchor_loc` | 27792→**27866** | **文件态自证**：`verify_workflow.py` 实读 EOF 总行数 = 27866，与锚值恒等（`loc_caliber` 声明 physical lines/ReadAllLines 口径，JSON L14/L17）；test L625 断言 27866 与 JSON 恒等 | ✅ 非掩蔽 |
| 2 | R1 +74 归因 | c442e07 单 commit | DEC-324 台账 vs 文件态：①「advisory 函数 26 行」→ `check_exploration_sample_advisories` L12345-12370 **恰 26 行，精确对合**；②「双消费渲染」→ Check 12 engine 面 L16602-16606 + CLI 面 L22513-22517 双双实读在位；③「F-8 三处注释」→ L7505/L16565/L22481 三处 `FIX-436 F-8 wording` **恰好三处实证**；④「探针注释 9 行」→ carrier banner（L12327-12338，12 行）+ `EXPLORATION_SAMPLE_REPORTS` 常量（L12339-12342，4 行）构成 carrier 面其余部分。构成项全部实读存在、量级吻合（26+4+12+10+3~6+9≈74）；逐行精确闭合需 c442e07 diff（未复跑，见未验证项） | ✅ 采信（构成实证） |
| 3 | R4 `_run_full_engine_checks` | 620→**621**（+1） | 新增 print 恰 1 处：L16606（Check 12 advisory 渲染行）；for 循环头非 print 调用 | ✅ 精确闭合 |
| 4 | R4 `cmd_check_cross_references` | 23→**24**（+1） | 新增 print 恰 1 处：L22517（CLI-side advisory render） | ✅ 精确闭合 |
| 5 | R4 `total` | 1369→**1371**（+2） | 621+24 增量 = +2 = 1371，算术闭合；test `FACTS_PRINT_TOTAL = 1371`（L131）三方恒等断言在位（L287-297：实测 census == 冻结字面量 == committed total） | ✅ 精确闭合 |
| 6 | R2 零漂移 | 48 sites | JSON inventory 实读逐条累加 = **48 sites**（15 条目：6+3+3+3+6+3+3+3+4+1+2+3+3+4+1）= DEC-320 记录的 FIX-438 时点 48——**跨源对合零漂移**；`scan_exclusions` 仍 5 项未扩 | ✅ 零漂移 |
| 7 | R3 零漂移 | matrix 不变 | 实读：`asserted_edge_count`=12 / layers 6 / `managed_modules` 2（archguard_ratchet L5 + contracts L0）+ `legacy_note` 原样；test 断言 managed_modules 长度恒等（L635-637）。FIX-438 时点明细无独立第二来源，依赖 DEC-324 实测「R3 PASS 零漂移」+ git diff 零行声称（未复跑） | ✅ 采信（测试背书） |
| 8 | R5 零漂移 | faces 不变 | 实读：faces 2（cli_dispatch.keys / check_segments.ids）+ `snapshot_present_at_regen: true` + SKIP+disclose 策略原样；同上口径 | ✅ 采信（测试背书） |
| 9 | R6 零漂移 | 205/Δ0 | 实读 `import_count`=205；跨注释链对合：FEAT-083 注释「R6 stays 205/Δ0」（test L598）→ FIX-438 未动 → 本票 lineage L622「R6 205/Δ0」——三时点自洽 | ✅ 零漂移 |
| 10 | R7 `git_head` | e1457a8→**1a56797** | JSON L13 = `1a567974d...917` 全 40 位在位；R7 committed==fresh 恢复由 CLI green 测试背书（声称） | ✅（HEAD 值未独立复跑） |
| 11 | 掩蔽通道：exemptions | 无新增 | 实读 `exemptions` 仅 1 条（FEAT-019 R1 self-bootstrap，`allowance_lines: 0`，DEC-183/184/190）——历史原样，**无新增强豁免、无 allowance 抬升** | ✅ 无掩蔽 |
| 12 | 掩蔽通道：authored zone | 语义保留 | `design_anchor_note`「只降不升 semantics unchanged」原样保留；`test_authored_zone_survives_regen`（L627-637）守护 regen 不清洗 authored 区且 managed_modules 不被 regen 注入 | ✅ 无掩蔽 |
| 13 | 冻结字面量同步 | test 两处 | L131 `FACTS_PRINT_TOTAL = 1371` == JSON `total` 1371；L625 anchor 断言 27866 == JSON `anchor_loc` 27866——**恒等**；grep 全文无旧断言残留（27792/1369 仅存在于 lineage 历史记录，正确） | ✅ 恒等 |
| 14 | lineage 注释如实性 | 两段新增 | L121-130（+2 双函数拆分，620→621/23→24）与 L614-624（+74/-0、单一 commit c442e07、四构成项、R2 48/R3/R5/R6 205 零漂移）逐句与 DEC-324 台账对合，**无夸大归因**；「~26 lines」带波浪号且实测恰 26；AWN/0 引用（REVIEW-FIX-436-R0）与 DEC-323(4)/DEC-324 一致 | ✅ 如实 |

**方向合法性**：DEC-324 路径 A 裁定——增量为已审合法功能面（c442e07 经 REVIEW-FIX-436-R0 AWN/0），无债务可收缩，only-down 语义自新锚 27866 起算；rider re-anchor 先例链 FEAT-080/081/FIX-416/420/421/423/083/**438**→**441** 追加合规。

## 二、5 维度结论

| 维度 | 结论 | 依据 |
|------|------|------|
| 1 正确性 | ✅ PASS | 三轴同步（R1/R4/R7）全部文件态对合（对账表 #1-#5、#10）；恒等断言与负对照（tampered baseline→FAIL、missing baseline→fail-closed）在位且未被本票削弱 |
| 2 安全性 | ✅ PASS | 变更面为治理内部数据文件 + 测试冻结字面量；无输入校验面、无注入面、无敏感数据、无权限面变化 |
| 3 可维护性 | ✅ PASS | lineage 注释链完整可追溯（DEC-324/DEC-322(1)/REVIEW-FIX-436-R0 引用齐全）；无命名/结构变化（观察项见 F-3） |
| 4 性能 | ✅ PASS | 无运行时影响；R6 import_count 205 不变、threshold 仍 null（advisory 姿态未变） |
| 5 测试覆盖 | ✅ PASS | 冻结字面量双镜像恒等断言 + CLI 四态测试（green/red/fail-closed/regen 幂等）继续覆盖新锚；执行结果 38 OK 为开发者声称（见未验证项） |

## 三、发现列表

| ID | 级别 | 位置 | 描述 | 处置建议 |
|----|------|------|------|----------|
| F-1 | **P3**（讨论/披露） | test L619 / DEC-324 | 「探针注释 9 行」构成项无法从当前文件态独立切分复算（需 c442e07 逐行 diff）；构成物存在性已全部实读证实、量级吻合，+74 总值由 R1 锚=实测行数 27866 文件态自证兜底 | 知识分享级：无需修改；如后续需要可由 Coordinator 存档 c442e07 diff 快照备查 |
| F-2 | **P3**（讨论/披露） | 全局 | 开发者声称的执行结果（archguard 全轴 PASS 0 violations、test_archguard_ratchet 38 OK、verify 主命令 PASS、manifest 1041、cross-refs PASS、test_contract_matrix 27+3）本审查未复跑（只读审查面）。其中 test_contract_matrix 3 失败的 stash 红绿对照归因（HEAD 预存、result_shapes 面 agent_locks/plan_tracker/governance-write）与本票两文件零接触面的交叉验证**一致**——采信为预存披露，不构成本票退化 | Coordinator 机录时引用开发者 evidence 快照背书；建议 FIX-441 闭环证据中留存命令输出原文 |
| F-3 | **P2**（建议/遗留） | test L42-131、L520-625 | lineage 注释链持续单调增长（FACTS_PRINT_TOTAL 头部链 ~131 行 + R1 anchor 注释 ~90 行），每轮 regen rider 追加一段；结构性观察同 DEC-320「做薄结构性动因转 REQ-147/B16 候选池」先例 | 不阻塞本票；建议随 REQ-147/B16 候选池后续票承载（lineage 外置为独立 lineage 文件或压缩历史段），沿用 DEC-320 的「不阻塞发布门」处置口径 |

**P0 = 0，P1 = 0**；P2 × 1（遗留候选，有 DEC-320 先例处置口径），P3 × 2（纯披露）。

## 四、AI 专项 5 项检查

| # | 检查项 | 结论 |
|---|--------|------|
| 1 | mock 残留 | ✅ 无——变更面仅数据文件五值 + 测试两字面量/两注释段，无 mock 引入 |
| 2 | 硬编码返回值 | ✅ 无异常——1371/27866 为**有意冻结镜像**（frozen-count 三方恒等模式，先例链 FEAT-080~FIX-438 一致），且被恒等断言机器锁定，非幻觉硬编码 |
| 3 | 幻觉 API 调用 | ✅ 无新增 API 调用 |
| 4 | 未实现 TODO | ✅ 无 |
| 5 | 过度实现 | ✅ 无——变更面最小（两文件、五值、两注释段），无越界修改、无第三文件（与 DEC-320 先例需 locks-extend 三文件相比本票更收敛） |

## 五、硬门槛裁决表

| 门槛项 | 阈值 | 裁决 |
|--------|------|------|
| P0 阻塞问题数 | = 0 | ✅ **0** |
| 5 维度全覆盖 | = 100% | ✅ 5/5 逐项有结论 |
| 每条发现标注级别 | = 100% | ✅ F-1~F-3 均标注（P3/P3/P2） |
| 设计一致性（DEC-324/DEC-320 口径） | 已完成 | ✅ 路径 A sanctioned regen 同构对合：抬锚值逐项归因单一已审 commit、零漂移轴未动、冻结字面量同步、lineage 记账、only-down 自新锚起算 |
| AI 专项 5 项 | 全部完成 | ✅ 5/5（见上表） |

## 六、未验证项（如实披露）

1. **所有命令执行结果**（archguard-ratchet 全轴 PASS / 38 OK / verify PASS / manifest 1041 / cross-refs PASS / test_contract_matrix 27+3）——只读审查未复跑，采信开发者声称 + 交叉一致性（F-2）；其中 R7 的 HEAD==1a56797 未独立核对。
2. **R1 +74 的逐行 diff 闭合**——c442e07 diff 未复算（F-1）；有锚值=实测行数的文件态自证兜底。
3. **R3/R5 的 FIX-438 时点明细**——无独立第二来源值，依赖 DEC-324 实测台账 + 「git diff 零行」声称；由 CLI green / authored-zone 测试面背信。

## 七、最终结论

### **APPROVED_WITH_NOTES**（unresolved_blockers = 0）

**理由**：纯基线 regen 执行票的非掩蔽性核心成立——①R1 锚 27866 由引擎文件实测行数**文件态自证**；②R4 +2 双函数**精确闭合**（两消费点各恰 1 print）；③R2/R6 跨源零漂移、R3/R5 台账+测试背书零漂移；④exemptions/authored zone 无新增强豁免、无掩蔽通道；⑤冻结字面量与基线恒等、lineage 注释如实无夸大；⑥与 DEC-324/DEC-320 先例口径完全同构且变更面更收敛。备注（F-1/F-2 披露级 + F-3 遗留候选）均不构成 BLOCKING。0.96.0 M-0 发布门的 archguard 解堵条件（「regen 产物过独立 R0 审查」）**已满足**。

---

*审查报告全文（本文件）返回 Coordinator，经 review-record CLI 机录；Reviewer 未修改任何代码、未运行任何命令、未触碰 .governance/。*
