# Review: REL-095-B2-R1 — loop-claims 单条精确豁免（DEC-283 题 2 授权）审查

- **round**: R1（首审；round 0 已被 M-1 审查占用；无前轮引用）
- **审查对象**: 工作树未暂存修改，恰 3 文件（git diff --numstat 实证：账本 JSON +11/-0；loop_runtime_claims.py +6/-2；test_loop_runtime_claims.py +96/-1；`git diff --cached` 为空）
- **审查日期**: 2026-09-28
- **授权边界**: DEC-283 题 2（decision-log L225 实锚）——仅账本+1 条目/锚 re-pin/定向测试与注释；禁分类器规则/匹配范围/默认错误处理/历史报告/既有 4 条目/测试预期值；受控解冻-差异审查-重新冻结语义
- **结论**: **APPROVED_WITH_NOTES**，unresolved_blockers=0（P0=0，P1=0，P2=0，P3=3）

## 一、审查重点逐项结论

### 1. 九键逐键 — 通过（实测非猜造）
- 形态一致性：新条目 LRC-EXEMPT-FIX401R0-79-1 与既有 4 条逐键同构（命名范式/finding_code/root_owner/locator/claim_id 同型；第 4 条 AMBIGUOUS/空 claim_id 由 finding code 族差异自然解释）；REQUIRED_EXEMPTION_KEYS 恰 9 键、无 schema 外字段——符合 DEC-283「schema 外治理字段不扩九键」。
- 五元组 vs 引擎实测：实跑 exemptions_applied 第 5 条逐键吻合：UNSUPPORTED_AFFIRMATIVE | product_root | docs/reviews/review-FIX-401-R0.md | accounting:79:1 | LRC-ACTIVE-RUNTIME。
- locator→原文闭环：独立提取 ordinal 79 = md_table_cell @ 物理行 L68 = Findings 表 F-3 行「问题」列，payload 含「`resolved: true` 先于 R0 终态与 commit 落盘…」——账本 reason「F-3 行自身」表述精确。
- reason 事实支撑：env_failure_classification.json L176-177 实存 `"resolved": true` + resolved_by "pending R0/commit"（被引述对象逐字吻合）；F-3 行全文为方法论注记非能力声明——「元文本误判」定性成立；族归因由 DEC-283 裁决原文背书。
- source 事实支撑：「随 commit 136d65e 引入」git show 实证（+102 行恰引入此报告）；「AWN/0 终态」=报告 L7 原文；DEC-283 L225 实锚。

### 2. digest 正确性 — 通过（独立重算一致）
- 独立重算 sha256(json.dumps sort_keys 紧凑) = d47f5d16c9dc0e60f38c35ed15f3429ffec6d5025f55d1963465cdd912b9a41d 与锚逐字符一致；算法参数与 _exemptions_digest（L1361-1362）逐参相同。
- 锚残留：完整旧 digest 64 hex 全仓零命中；短前缀恰 1 命中=review-FIX-389-CODE-R0.md L69（历史文档合法不改写）。
- 实跑无 EXEMPTIONS_CONTRACT_DIGEST_DRIFT / SET_DRIFT → 锚-账本-加载器三方一致。

### 3. 测试质量 — 通过
- 三反相 7/7 零预期改动（FIX320ExemptionLedgerTests 全过；git diff 证既有断言零改动；docstring "four"→"five" 一词跟随事实非弱化）。
- 新增 2 条真实性：真实报告字节+真实账本字节（不 patch 常量——锚与账本一致性被测试本身证明）；负向因果「一致 re-anchor」构造纯净（_exemptions_digest(stripped) 重算+frozenset(4) 剩余；显式断言无 EXEMPTIONS_* 噪讯；finding 复活五元组复验+BLOCKED）。
- 全量实跑：1 failed + 63 passed + 81 subtests（281.7s）——唯一 fail 为预期红（重点 6）。

### 4. 六项验收复核 — 6/6 通过
单目标性（diff 恰 3 文件无夹带）/正向验证（实跑 PASS/0/5 披露+九要素）/三反相（7/7 零改动）/负向因果（定向测试五元组同）/差异闭包（numstat 恰 3 文件 staged 空）/历史不变（报告 numstat 空+旧锚零活代码残留）。

### 5. 实跑复验 — 通过
`check-loop-runtime-claims --product-root . --project-root .`：verdict=PASS / findings=0 / exemptions_count=5，新条目 9 键全部出现在披露面逐字段核对。符合 DEC-283(4)「loop 按既有契约 PASS 并披露豁免」。未遇 INVENTORY_* 瞬态（一次通过）。

### 6. 预期红评估 — 声明合理（机理坐实+先例真实+断言零改动）
- 实测复现：恰 1 fail=test_three_run_performance_identity_and_median；失败快照=5 语义 finding+DIGEST/SET 双 drift。
- 机理（源码级）：该测试 L1097 从 git **index** 物化被测树；未暂存⇒物化树=HEAD（旧 4 条账本）vs 运行中检查器=工作树（新锚+5 IDs）→双 drift→豁免全作废（fail-closed）→F-3 无豁免存活→BLOCKED≠PASS→红。快照逐项吻合。
- FIX-320 先例真实（review-FIX-320-322-CODE-R0.md L60 两态模拟+L72 自愈机理；FIX-389 L65 佐证）；数字演进自洽（当年 4 classify→今 5）。
- 断言零改动（L1086-1173 无 hunk）。
- 判定：:index 物化对未暂存修改的结构性暂态敏感，非缺陷；暂存/提交后自愈。

### 7. AI 专项 5 项 — 全部完成零阻塞
九键取值来源实测（独立复验吻合）/先例引用真实/数字核对全吻合/mock 无残留（patch.object 为受控 re-anchor 手段同既有模式）/硬编码=锚定契约设计本身/无幻觉 API/无 TODO/无过度实现。

## 二、授权边界终判 — 零越界
允许面全命中（账本恰+1/锚恰 2 行+4 注释/定向测试恰 2+docstring 一词）；禁止面零触碰（分类器/范围/错误处理/历史报告/既有条目/既有预期值）。受控解冻-差异审查-重新冻结语义成立（本审查即差异审查环节）。

## 三、Findings

| ID | 级别 | 位置 | 问题 | 建议 |
|----|------|------|------|------|
| F-1 | P3 | docs/reviews/review-FIX-389-CODE-R0.md L69（历史文档非本次变更） | 历史报告引用锚行号 L114 因 +4 行注释移至 L118——未来按行号 grep 失准 | 无动作（历史禁改写）；知识记录：引用锚宜用 digest 前缀非行号 |
| F-2 | P3 | 任务元数据 | 申报「+97」实测 +96/-1（触达 97 行含 1 行 docstring）——口径差异 | 更正申报口径；无产品影响 |
| F-3 | P3 | test_loop_runtime_claims.py L1086-1173 | :index 物化测试对未暂存账本/锚修改结构性必红——commit 纪律需「add 后再跑全量」 | 知识记录；未来账本/锚变更执行清单明示「暂存后再跑全量」一步 |

## 四、硬门槛自检
P0=0 ✓；5 维度全覆盖（正确性/安全性〔fail-closed 保持·豁免面不可静默扩大〕/可维护性/性能〔锚 O(1) 无运行时影响〕/测试覆盖四层）✓；每条发现标注级别 ✓；设计一致性（DEC-283 边界逐条+FIX-320 锚定纪律）✓；AI 专项 ✓；实跑绝对路径零写操作 ✓。

## 五、终态结论
**APPROVED_WITH_NOTES — unresolved_blockers=0**。单条精确豁免全链路成立；唯一 pytest 失败为结构性预期红（机理源码级坐实+先例真实+断言零改动+暂存后自愈）不构成阻塞；3×P3 信息性。授权边界零越界。

## 六、证据清单
1. git diff --numstat/--cached/status：恰 3 文件 staged 空
2. digest 独立重算输出与 L118 锚逐字符一致；_exemptions_digest L1361-1362
3. check-loop-runtime-claims 实跑 PASS/0/5 九键披露
4. 全仓 grep 旧 digest 零命中（短前缀 1 历史合法）
5. git show --stat 136d65e（报告 +102 行恰引入）；报告 numstat 空
6. ordinal 79 独立提取=F-3 行 L68「问题」列
7. env_failure_classification.json L176-177 实存
8. decision-log L225 DEC-283 全文
9. pytest 全量 1F+63P+81 subtests；定向 9 passed+2 subtests
10. 测试源码 L997-1236（断言区零 diff）/L1740-1916/L1919-2012
11. review-FIX-320-322 L60/L72 + review-FIX-389 L65 先例

## 七、遗留不确定项
1. 「M-2 时点唯一未豁免 finding」为载体申报——四重独立证据交叉印证（正向 baseline classify=1/负向复活五元组/实跑 4 旧豁免全应用/live-tree IDS 集合相等），采信+注记
2. 暂存后全绿为机理预测——建议 Coordinator commit 前暂存复跑全量 pytest 确认 64 passed（闭环动作）
3. INVENTORY_* 瞬态本次未出现——无观测即无发现，注记
