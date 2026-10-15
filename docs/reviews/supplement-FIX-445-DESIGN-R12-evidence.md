R12 报告后置核验附注（不改动已交付的唯一最终报告，verdict 仍为 BLOCKED/unresolved_blockers=1）：

1. **context-check.json 已读取并逐格对照**（62 行，`product_code_executed:false`/`review_verdict_claimed:false`）。其六个 computed 邻接值与我在 R12 审查中基于冷原行重读 + hook :726-728 isterm 闭集的独立重推**逐字一致**：1536 右邻=`原门CPU27`（样例跨 `27.8` 小数点，mismatch）、1588 左邻=`9FFF与ASCIIalnum/符号集合空`（样例跨 `U4E00..` 双点，mismatch）、1536 左/1587 两邻/1588 右四值 match。行 SHA 与 codepoint 区间（1148..1158/428..454/572..600）与 R11 artifact-check 一致。**两路独立推导互证，B4 定级（BLOCKING）与解除条件三件（样例修正/schema context 合法性硬校验/迁移机检扩为三元组逐字核对）不变**。我的结论来源仍是我自己的冷行重推，审计件仅作佐证，未反向采信。

2. **C4 first-K 语义确认**：`c ≤ K` 绑定的是批内三元组逐字匹配的**前 K 次**出现，非「指定的第 K 个冻结出现」——迁移实 ordinal>1 时按实值登记 K 将连带豁免未经裁决的更早复本；K>1 且裁决出现未全部落地时存在前置偷位窗口。此即我报告 W-R12-3 的内容与定级（WARNING），解除条件（K 逐出现后置登记、只登记已存在且经裁决的出现）不变。

3. **归档通道≠用户风险接受（DEC-345 原门口径）**：确认。boundary.json `replay_risk_acceptance_authorized:false`；设计 BT-R12-1 自身也标注「过程+契约缓解，非运行时机闭，如实披露不冒充」。我的 W-R12-2 未将其计为已闭合或已接受——必要条件（迁移/实现票含机器可检归档守卫）保持；M3/M4 的 replay 攻击本身已由机制拒绝，不属风险接受面。

4. 本附注为独立验证记录；R12 最终报告文本与 JSON 结论零变更。产品/历史/registry 状态不变，无 R13、无实施/迁移授权。
