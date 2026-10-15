```json
{"verdict":"APPROVED_WITH_NOTES","round":1,"unresolved_blockers":0,"review_scope":"feat095_p1_1_wording_fix_delta","parent_full_product_complete":false}
```

# FEAT-095 R1 delta 复审报告（Code Reviewer，round 1）

前轮引用：review-FEAT-095-CODE-R0.md（AWN0，P0=0/P1=1/P2=1/P3=6）。本轮为 M7.4 T1 同 Reviewer 复审，delta 面向 R0 findings；只读（Read/Grep/Glob only），未执行命令、未改码。复审方法：三处修正现场全文重读 + DEC-357 原文核验 + 两文件全称化残留全量扫描 + 代码锚点位移比对（零行为变更的内容级证明）。

## 1. R0 P1-1 逐条比对——**已修复（三处全部有效关闭，断言未弱化）**

1. **enforcement.py:24-28（修法①）——已修复**。旧全称声明「无关任务不受他票审查债影响（DEC-330 发布验证底线）」已删除；新文为 DEC-357 口径：「scoped 语义（DEC-357 口径）：硬阻断与未闭合复审按任务/通道 scoped；审查债预算是全局新工作准入限流（仅 dispatch-execute/goal-resume 两 admission 面），白名单通道与用户裁定额度逃生门保留；非 admission 边界无限流面」。与 DEC-357 裁决原文及 R0 修法建议逐点对应，无新的全称化表述。
2. **SKILL.md:260①（修法②）——已修复**。旧「scoped 非全局（…无关任务不被冻结——DEC-330 发布验证底线）」替换为 DEC-357 口径（**全局新工作准入限流**加粗 + admission 面限定 + 三通道+用户裁定逃生门）。投影 SKILL.md:260 与源逐字一致（grep 单命中同文本）——同步成立。
3. **test_verify_workflow.py:27057-27065（修法③）——已修复**。改名 `test_enforcement_accept_completion_non_admission_not_debt_throttled`；新注释明确「accept-completion is a NON-admission boundary — strategy table gives it no throttle face」并显式否定全称读法（"NOT a universal 'unrelated tasks are never frozen' claim"）；断言与 R0 逐字相同（rc==EXIT_ALLOW + decision==ALLOW）——**测试名/注释与实际验证面相符，断言强度未变**。
4. **DEC-357 核验**：decision-log L224 存在，governance-store 机写（op-9e260381…，schema v1）；内容=口径钉死（全局准入限流≠任务冻结、admission 面限定、白名单+用户裁定逃生门、非 admission 面不受他票债影响、WIP carve-out 优先）+ **M-7/M-8 故障注入预期结果已定义**（「无关任务派发执行 under 他票债」→ exit 3 可解除限流，非全局冻结）+ 本轮三处措辞与 R1 绑定均入账。R0 P1-1 的发布链末端口径空洞由此闭合。
5. **全称化残留全量扫描**：enforcement.py 全文 grep「无关任务|不受他票|全局冻结」**零命中**；SKILL.md 仅剩 :251 表格单元格一处（裁定见 §2）。无新引入。

## 2. Developer 边缘发现裁定（SKILL.md:251 表格单元格）——**可接受简写，非缺陷，不列本轮 finding（P3 备注级）**

理由：①**行局部为真**：该注释挂在 accept-completion 行的限流列（—=无限流面），无关任务的 accept-completion 确实永不被债限流——这正是改名后测试所验证的面，单元格陈述在其作用域内准确；②**规范口径已上移**：本节 scoped 语义的权威定义现居 :260①（DEC-357 锚定、admission 面限定），距表格两行，单元格无法覆盖规范行——P1-1 的缺陷形态是「未限定的全称声明被应用到 admission 面」，单元格未对 admission 面做任何声明；③**残留风险已评估**：仅扫表格不读 260① 的读者可能重新提取该短语——缓解建议（非本轮要求）：下次任何原因触碰 SKILL 执法段或投影 resync 时，顺手将单元格对齐为「—（非 admission 面，无债限流——DEC-357）」，不值得为此单独跑一轮投影同步。附注：调研报告 §10.4「无关任务不受他票审查债冻结（accept-completion 无限流面）」本就带括号限定（R0 已认可为精确口径），与本裁定同构，无需改动。

## 3. 零行为变更核验——**成立（内容级）**

- enforcement.py：724→727 行、28665→28912B（+247B/+3 行，与 docstring 扩张吻合）；全部代码锚点均匀位移 +3 且内容逐字不变——EXIT_STALE_NOTICE=4（117）、allowlist_exempt:True（169）、_ADMISSION_BOUNDARIES（177）、thresholds 100（193）、wip_carve_out_boundary "merge"（198）、def decide（230）、def _decide（262）、def cmd_enforcement_check（606）。策略表常量与执行器/CLI 面未动。
- test_verify_workflow.py：+2 行（注释扩张）；20 个 `def test_enforcement_*` 清点一致（新名替换旧名，其余 19 个位置逐一对应 +2 位移）；断言区未动。
- verify_workflow.py：三接线锚点行号与 R0 完全一致（25693/28046/28177）——零改动声明与内容相符。
- 回归「-k enforcement Ran 20 OK EXIT=0（0.509s）」：本 Reviewer 无命令权限未复跑，按 Coordinator 报告采信；与内容核验一致（断言/模块逻辑零变 → 结果应可复现）。SHA256/blob 由 Coordinator 声称已独立核验，本轮以内容级比对佐证（哈希未由 Reviewer 重算——工具约束，同 R0 声明）。

## 4. R0 其余 findings 处置标注（本轮不要求闭环）

| R0 finding | 本轮状态 |
|---|---|
| P2-1 facts 缺席字段静默跳过（revision 缺席→最强硬阻断无信号失效） | 留后续（代码零改动轮不可处置；建议随下一次执法面行为变更票或 REL-102 前小修） |
| P3-1 未用 import tempfile | 留后续（同上，代码面） |
| P3-2 argparse exit 2 与 HARD_BLOCK 码碰撞 | 留后续 |
| P3-3 SKILL:239 概括行未内联 exit 4 例外 | 留后续（措辞面，可与 :251 单元格对齐同批处理） |
| P3-4 损坏策略表直接测试缺失 | 留后续 |
| P3-5 run1（7F）未入 validation log | 留后续（流程透明度，无代码面） |
| P3-6 fnmatch 路径分隔符约定未入 facts 契约 | 留后续 |

## 5. 硬门槛与结论

- 复审纪律：已逐条比对 R0 findings（已修复/留后续逐项标注，无未标注项）；round 1 < 3，无熔断问题；前轮 P1-1 三修法 + DEC-357 全部落位。本轮新发现：无 P0-P2；1 项 P3 备注级裁定（:251 可接受简写，理由如上）。
- P0=0 ✓；五维维持 R0 结论（本轮零行为变更，五维不受影响）✓；AI 专项维持 R0 结论（本轮无代码变更）✓。
- **结论：APPROVED_WITH_NOTES（unresolved_blockers=0，round 1）**——R0 P1-1 有效关闭，delta 为 DEC-357 支撑的纯措辞收窄，复审链可终止于通过终态。留后续项（P2-1/P3-1~6 + :251 对齐建议）均为非阻塞备注，交 Coordinator 按发现即闭环成本裁量排期（均不属本票 done 定义阻断面）。

—— Code Reviewer R1 完（报告正文供逐字落盘 docs/reviews/review-FEAT-095-CODE-R1.md）
