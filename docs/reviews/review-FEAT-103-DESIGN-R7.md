# REVIEW-FEAT-103-DESIGN-R7 — R6 文本批 + 合入前设计终态聚焦复核

- 日期：2026-10-22（Asia/Shanghai；命令时刻 UTC）。独立 Design Reviewer（R11 同链新实例，承接 REVIEW-FEAT-103-R11；只写本报告 + scratch `.codex-sandbox/FEAT-103/review-design-r7/`）。
- **对象绑定**：设计 `docs/architecture/dsh-upstream-owned-registration-R1.md` 修订后 SHA-256 `D8DE745CA7CE826EA5DE4129B4CE53FC26C9011775D8E32553BC461E5C1B0092`（566 行 / 102,024 B——本 Reviewer 独立复算一致）；修订前基线 `2CA8A9B813E7B0DE2335C396F5709ADE17D67C4C1244AFE7896BEFE20B3FA4F3`（549 行 / 96,752 B）= R11 复核输入，与 Architect revision-log 及 R11 报告 §对象绑定一致。
- **delta 依据**：`docs/reviews/review-FEAT-103-DESIGN-R6.md`（REVIEW-FEAT-103-R11，AWN/0——R6-P3-1/R6-P3-2 与"可留合入前小修"授权原文）+ `.codex-sandbox/FEAT-103/design-r7/revision-log.md`（Architect 逐项落点）+ `.codex-sandbox/FEAT-103/M4-REPORT.md`（合入前终态判定的实施面事实，纯测试批 6/6 PASS）+ evidence-log `REVIEW-FEAT-103-R11` 机录行（L3060）。
- **范围**：只核 R6 批四项 + 零回退复验 + section 回归 + 合入前设计终态判定。未运行宿主/测试/SDK（纯文档审查；实施面事实以 M4-REPORT 与机录行为据）。

## 1. 结论

```text
conclusion=APPROVED_WITH_NOTES
unresolved_blockers=0
r6_items=PASS (4/4)
r11_p3_notes=CLOSED (R6-P3-1 / R6-P3-2)
zero_regression=PASS (10/10 anchors, independently re-read)
section_regression=PASS (+17 lines = §15 new section; inline-only elsewhere)
machine_record_consistency=PASS (§11 write-back ↔ evidence-log L3060)
premerge_final_state=PASS with 3 P3 status-lag notes (post-M4, hand to merge decision)
host_run=NOT_RUN
tests=NOT_RUN (design-doc review; M4 facts cited from M4-REPORT/machine records)
new_global_blocker=NONE
```

## 2. 逐项判定

| 项 | 判定 | 事实（本 Reviewer 亲读锚点） |
|---|---|---|
| **R6-1 acquire 三形态衔接（R6-P3-1）** | **PASS** | §5.4 L300 合同句内补："M2-FIX 起扩展为 `{id, generation}` 形态〔回退 attempt 携带冻结代，§5.3〕、M3 起扩展为 `{parent}` 形态〔继承分支，§4.2〕——三形态合同统一见 §4.2 记法注记；R6 补此衔接半句，R6-P3-1"。单独阅读 §5.4 即可获知全三形态+各自出处+统一注记指针——R11 §3 R6-P3-1 的"仅由 §4.2 注记衔接、:300 是合同句非伪码"缺口闭合。 |
| **R6-2 修辞替换（R6-P3-2）** | **PASS** | §4.2 依据 1 L232："materializeTracked 是 spawn 与 cold resume 汇合的子编排入口——子编排上下文在该入口就绪、`agents.create/resume` 在其后发起，冻结即取该入口的父现行代（R6 措辞替换：原文…依赖修辞解释，裁定实质不依赖该句）"。事实表述替代修辞且保留替换注记（可追溯）。**裁定实质零触碰**：依据 2 窗口语义（L233）、依据 3 双 fence（L234）、备选 b) 排除+留白（L235）逐字原样——R6-P3-2 闭合。 |
| **R6-3 §11 复核状态回写** | **PASS** | 三处亲读+机录核对：①L410 硬门槛自检段末句（R5 增量聚焦复核已完成——REVIEW-FEAT-103-R11 … AWN/0：锚点裁定接受、F-M3-1~4 PASS、零回退验证；2×P3 已由 R6 收敛）；②L424 代码块 `independent_review=R5 increment focused re-review DONE (… APPROVED_WITH_NOTES/unresolved_blockers=0 …)`；③L549 §14 待复审行 R6 注。与 evidence-log L3060 机录行（round 11 / report_sha256=acef4068… / 2026-10-22 / APPROVED_WITH_NOTES / unresolved_blockers=0）**逐项一致**。 |
| **R6-4 版本号升级与消歧** | **PASS** | L1 标题（+R6 增量链）、L3 日期（R6 增量 2026-10-22，与 §11 一致）、L5 性质段（R6=合入前文本批描述）、L417 `design_revision=R6` + 消歧注（DESIGN-R5.md=R8 复核 R4-P2、DESIGN-R6.md=R11 复核 R5 增量）、§15 L556 三轴消歧（设计版本号 R5/R6 ↔ M4 实施里程碑 ↔ 审查报告文件名——各有定义与例证）。混淆源（三轴同名不同物）被显式消除，文首↔§11 一致口径（N-R4-6 纪律）延续。 |
| **零回退复验（10/10）** | **PASS** | 本 Reviewer 独立亲读（非 Architect 自检转述）：N-R4-1 错误码映射段=L286；N-R4-2 `_forget` 措辞=L198；N-R4-3 §9 容量行=L390；N-R4-5 两类 fallback 用例段=L284；N-R4-6 文首↔§11=L1/L3/L5↔L417；R5 面：§4.4 映射注记=L253、§4.2 裁定段=L229-235、错误面 bullet=L238、§5.4 状态行=L304（除 R6-1 指定小修）、§5.6 状态行=L320。§3.5 证伪出口 L209 与 §12/§13 历史审计零改写（§14 仅 L549 追加声明面内的 R6 注）。 |
| **Section 回归（549→566，+17）** | **PASS** | +17 行全部 = §15 新节（L551-566 共 16 行 + L550 空行）；其余变更全部为行内改写（L1/L3/L5/L232/L300/L410/L417/L424/L549），逐处与 Architect 声明面吻合，**无未声明区段变更**。byte 级 diff NOT_RUN（基线 2CA8A9B8 三源一致但 untracked 无 git 历史——同 R11 口径如实声明，不伪造）。 |

## 3. 合入前设计终态判定（第 7 项）

**判定：PASS（带 3 项状态滞后备注，均交合入决策，非合同缺口）**

| 面 | 判定 | 事实 |
|---|---|---|
| 设计↔M1-M3 事实一致性 | **PASS** | §11 `implementation_progress=M1/M2/M2-FIX/M3 done` + 套件实数（B 12/12、A 12/12、C 14/14、d1 10/10、T01 9/9）与机录事实一致；`implementation_authorized=true`（DEC-367 面内）而 `upstream_patch_authorized=false` / `release_authorized=false` 保持——真实链面"交合入决策"口径已成文（§11 runtime/storage_regression=NOT_RUN）。 |
| M4 完成事实的登记 | **P3 滞后（R6 批时序上无法包含，非疏漏）** | M4 测试批（纯测试、副本七文件零改动、6/6 PASS）完成于 R6 批之后。三处状态滞后：①§11 L426 `implementation_progress` 不含 M4 done；②§5.4 L304 残余 NOT_RUN 清单中"attach 的 rebind 抛错分支（A8 仅覆盖 join 抛错…NOT_RUN）"**已被 M4-2 PASS 闭合**（rebind 抛错→原错误透传/HELD 保持/users 不变/无 ATTACHED 泄漏）；③§5.6 L320 "legacy 面与容量策略未实现/未测"——legacy 分类面**已被 M4-1 覆盖**（legacy 关闭=not-found / owned 关闭=closed 对照成立），容量策略仍未测（维持）。建议合入前终态回写批一次处理。 |
| C-1（T09+ closed 变体未单测） | **非设计缺陷** | 设计合同已成文（§5.3 #2："live 同 preset 直接返回…全 operation 零 admission；closed registration 不影响"）——C-1 是测试覆盖缺口（M4-REPORT §5 #4 自报，建议下轮或合入前小批）。**设计侧无需合同变更**，仅需在合入决策清单登记。 |
| webhook / 多 Cordis | **PASS** | M4-7 NOT_APPLICABLE 判定与设计 §7 :362 / §6.1 :338 口径一致（webhook 未安装不声称覆盖；多 Cordis 无合同条目，M1 P3 风险注记维持原披露）——设计明示无合同面，实现侧不造用例是正确处理。 |

## 4. 新偏差（均 P3，非阻断）

**R7-P3-1 — M4 后三处状态行滞后（合入前终态回写批候选）**
- §11 `implementation_progress` 未含 M4 测试批；§5.4 状态行 rebind NOT_RUN 残余已被 M4-2 闭合；§5.6 "legacy 未测"已被 M4-1 部分闭合。均状态滞后非合同缺口；建议与 M4 CODE R5 复审结论一并做一次终态回写。

**R7-P3-2 — C-1（T09+ closed 变体）需在合入决策清单登记**
- 测试缺口（"live 同 preset 且 registration closed → 复用成功且 P=0"变体无单测）；设计合同已在 §5.3 #2 成文，无需设计变更——仅登记交合入决策。

## 5. 命令审计（本 Reviewer，全只读）

| # | label | UTC | exit | 要点 |
|---|---|---|---:|---|
| V1 | 设计 SHA/bytes 复算 | 2026-10-22T10:5x–11:0xZ | 0 | `D8DE745C…B0092` / 102,024 B（行数 split 口径 567 含末行换行，read 口径 566——与 R11 V1 同类口径注记，非矛盾） |
| V2 | 设计全文亲读 | 同上 | 0 | L1-120 / L193-208 / L200-329 / L380-469 / L470-566 五窗口；R6 四项+零回退锚点逐处亲读 |
| V3 | evidence-log 机录核对 | 同上 | 0 | REVIEW-FEAT-103-R11 行（L3060）与 §11 三处回写逐项一致 |
| V4 | M4-REPORT 亲读 | 同上 | 0 | 121 行全文；§2.1 T 合同对照表/§5 剩余 NOT_RUN（C-1）/§1 双端 SHA——终态判定输入 |

- 未运行任何测试/宿主/SDK；无写入（除本报告与 scratch 说明）。

## 6. 边界合规

- **写面**：仅本报告 `docs/reviews/review-FEAT-103-DESIGN-R7.md`；未改设计/代码/测试/副本/治理记录；未 stage/commit/push；未启动宿主；未设置/读取 DSH_HOME；安装态 SDK 零访问。
- 审查对象 SHA 独立复算与派单一致（对象绑定无漂移）；delta 依据三源一致（R11 报告 / revision-log / M4-REPORT）。

**结论：APPROVED_WITH_NOTES，unresolved_blockers=0。** R6 批四项全部落地且 R11 两项 P3 备注闭合；R4-P2/R5 已批面零回退（10/10 独立复验）；+17 行 section 回归吻合；合入前设计终态与 M1-M3 机录事实一致，M4 后三处状态滞后（R7-P3-1）与 C-1 测试缺口（R7-P3-2）交合入决策。host/运行面维持 NOT_RUN 诚实披露。
