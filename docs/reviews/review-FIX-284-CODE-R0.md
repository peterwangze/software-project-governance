# FIX-284 Code Review R0 — write-guard 写入行缺失路径回归测试 + remediation 定位标准行来源消息

- **Task**: FIX-284（P2，0.78.1 入槽，DEC-172 #5/#6 + DEC-173 入槽结构；DEC-168 契约延续——TRIAGE 行族为 write-guard 列数标准权威源）
- **Round**: R0
- **审查对象**: 工作树未提交变更（本任务净变更严格限定 2 文件）：
  1. `skills/software-project-governance/infra/verify_workflow.py`（P2-2，6 处）：:21199-21205 docstring Scope 段追加；:21238 `standard_source` 追踪变量；:21255 TRIAGE 行族分支来源标记；:21260-21261 EVD fallback 分支来源标记；:21268-21274 失配 issue 消息增强；:21356-21362 `cmd_change_triage` remediation 消息追加标准行来源说明
  2. `skills/software-project-governance/infra/tests/test_verify_workflow.py`（P2-1）：:16766-16799 `Fix284WriteGuardMissingRowTests::test_guard_reports_written_row_missing_after_write`
- **范围红线**: 两文件含 FIX-283/286/287/288 等已审未提交改动——不在本次范围；本任务净变更 = 上述 hunk
- **Reviewer**: Code Reviewer（独立 sub-agent，只读；全程无 Write/Edit/Bash）
- **来源报告**: `.governance/review-FIX-279-CODE-R0.md`（P2-1/P2-2）
- **Date**: 2026-08-28（Coordinator 补记）

## 终态结论

**APPROVED_WITH_NOTES — unresolved_blockers=0**

通过终态，可合并。P3×3 全部为非阻塞建议/可选改进，登记为遗留跟踪项，不阻塞本次收口。

## 发现计数

| 级别 | 计数 |
|---|---|
| P0 阻塞 | 0 |
| P1 关键 | 0 |
| P2 建议 | 0 |
| P3 讨论 | 3 |

## 五维度逐项结论表

| 维度 | 结论 | 事实依据 |
|---|---|---|
| 正确性 | PASS | ① `standard_source` 双源追踪时序正确：TRIAGE 行族分支（:21253-21255）置 `triage_family_found=True` 并原子赋值 `standard_cols`+`standard_source`；EVD fallback 分支（:21257-21261）受 `not triage_family_found and standard_cols is None` 双条件门控，行族先行时 EVD 不再覆盖（与 FIX-279 docstring「行族权威、EVD 仅 fallback」一致）；后置 TRIAGE 行族对先设 fallback 的覆盖为 cols+source 同分支同步覆盖，不存在 source/cols 脱同步路径（source 仅两处赋值点，各与 cols 同分支原子设置；初始 `""`/`None` 配对；渲染仅发生于失配分支，该分支要求 `standard_cols is not None`，故渲染时 source 必非空）。② 写入行缺失检测语义保持：`written_found` 按 `parts[1] == record_id` 行 ID 匹配（:21247-21248），缺失 → :21262-21265 显式 issue，`elif`（:21266）保证缺失时不再触发列数失配误报。③ 消息增强纯文本插值（:21268-21274），未改变 issue 触发条件与计数语义。 |
| 安全性 | PASS | 纯本地治理文件文本扫描与 stderr 消息构造；无注入面（消息经 `.format` 插值 record_id/计数/来源常量字符串，无 shell/路径拼接执行）；无敏感数据；无权限语义变更。guard 唯一调用点仍为 `cmd_change_triage` 成功路径（:21348-21351），失败路径不受影响（:21342-21343 先行 exit 2）。 |
| 可维护性 | PASS | docstring（:21199-21205）与实现同步更新；`standard_source` 命名表意清晰，双来源字符串自描述（"first non-written TRIAGE-family row" / "EVD fallback row (legacy log without a prior TRIAGE family)"）；消息为单行（源码隐式串接无换行），grep 实证无机器解析消费方（既有断言均为 substring 断言），不构成解析脆弱面。 |
| 性能 | PASS | 变更为每行至多 1 次字符串赋值 + 1 次布尔判断，O(n) 单趟扫描结构未变；无新增 I/O；消息增强仅在失配分支执行一次 format。 |
| 测试覆盖 | PASS | 新增 `test_guard_reports_written_row_missing_after_write`（test_verify_workflow.py:16780-16799）补齐 R0 P2-1 指认的「写入行缺失显式报错」无守护缺口：fixture 含 10 列 EVD 行 + 10 列 TRIAGE-OLD 行族 + 合法 record JSON，`record_id="TRIAGE-FIX-284"` 于日志中不存在 → 断言恰 1 条 issue、含 record_id、含 "not found"；`TRIAGE-OLD` 10 列行族在场而断言恰 1 条 issue，实质锁定「行族标准存在时不得误报 column-mismatch」（若误报则 count≥2 失败）。Developer 声明绿相 + FAIL-on-buggy 红相实录（移除检测 `if False and not written_found` → 1 failed AssertionError 0!=1 exit 1 → 恢复绿）；Coordinator 抽测复核：新测试 1 passed + test_triage_write_guard 15 passed；基线 747+89subtests → 748+89subtests（+1）均 exit 0（Developer 自报，Coordinator 抽测佐证）。语义上该测试为「补覆盖已正确行为」——本审逐行推演确认该检测路径在当前工作树实现中确实在位（:21262-21265），非先修后测。 |

## 发现列表（P3×3）

| # | 级别 | 位置 | 发现 | 事实依据 | 建议 | 处置 |
|---|------|------|------|---------|------|------|
| F-1 | P3 | test_verify_workflow.py:16797-16799 | 新测试「不误报 column-mismatch」经由 count≥2 失败间接锁定，可选补显式负断言 | 现断言为 `assertEqual(len(issues), 1)` + record_id substring + "not found" substring；column-mismatch 误报会以 `assertIn("columns", ...)` 维度暴露，但当前未显式断言 `"columns" not in issues[0]` | 可选改进：追加 `self.assertNotIn("columns", issues[0])` 使「缺失 ≠ 列数破坏」意图显式化（docstring 已声明该语义） | 遗留跟踪（可选，不阻塞） |
| F-2 | P3 | verify_workflow.py:21356-21362 | remediation 消息无条件追加标准行来源说明——非列数类失败（行缺失/JSON 无效/evidence-log 不可读）也显示「列数标准来源=…」提示 | `guard_issues` 非空即打印该 remediation（:21352），不区分 issue 类别；「列数标准来源」段对行缺失/JSON 无效场景为噪声。但消息主体前半段（修复写入产物/人工处置再重试）对全部失败类别通用有效；来源段以「写入行符合当前格式时先核对标准行本身」自限触发语境，不构成误导。噪声暴露面仅限 guard 失败路径 stderr（成功路径不打印），低频低害 | 可接受现状；如后续打磨，可按 issue 类别分流（列数失配才附来源段） | 遗留跟踪（不阻塞） |
| F-3 | P3 | test_verify_workflow.py:16766（落点） vs test_triage_write_guard.py（R0 审查建议落点） | 测试落点偏差：锁面指定 test_verify_workflow.py，审查建议 test_triage_write_guard.py | 语义等价成立：两者均为对 `_triage_write_structure_guard` 的直接单测（同函数、同构造手法、同 tempfile 隔离模式）；test_triage_write_guard.py 现有 15 用例（含 FIX-279 行族契约 6 例）为专用套件，write-guard 回归集中该文件更利维护定位。差异仅测试组织（可发现性），无覆盖/语义差异 | 可接受现状；若后续 test_triage_write_guard.py 扩展，可将本例迁移归并（纯移动，无断言变更） | 遗留跟踪（不阻塞） |

## AI 专项 5 项表

| # | 检查项 | 结论 | 事实依据 |
|---|--------|------|---------|
| 1 | mock 残留 | 0（未发现） | 新增测试无 mock/patch（直调 `vw._triage_write_structure_guard`）；变更 hunk 内无 mock 引入 |
| 2 | 硬编码返回值 | 0（未发现） | `standard_source` 两处赋值为描述性来源常量，非伪造返回值；函数返回的 issues 全部由真实扫描结果构造 |
| 3 | 幻觉 API 调用 | 0（未发现） | 变更仅使用既有 `Path.read_text`/`len`/`_split_markdown_table_row`/字符串 format，均为仓内既有用法 |
| 4 | 未实现 TODO | 0（未发现） | 变更 hunk 无 TODO/FIXME 标记 |
| 5 | 过度实现 | 0（未发现） | 变更严格限于：来源标记 2 处 + 变量 1 处 + 消息文本 2 处 + docstring 1 处 + 测试 1 例；未引入新抽象/新依赖/新配置面 |

## 硬门槛裁决表

| 门槛项 | 阈值 | 裁决 | 依据 |
|--------|------|------|------|
| P0 阻塞问题数 | = 0 | **PASS** | 发现列表 P0=0 |
| 5 维度全覆盖 | = 100% | **PASS** | 上表 5 维度逐项有结论 |
| 每条发现标注级别 | = 100% | **PASS** | F-1/F-2/F-3 均标 P3 |
| AI 代码专项 5 项检查 | 全部完成 | **PASS** | 上表 5 项逐一有结论 |
| 设计一致性 | 已完成 | **PASS** | ① 与 review-FIX-279-CODE-R0 P2-1/P2-2 逐条承载；② DEC-168 行族权威语义无回退：判定结构未动，仅增来源标记；③ DEC-172 #5/#6 与 DEC-173 入槽范围一致；④ FIX-279 既有测试契约零翻转：test_triage_write_guard.py 15 用例零断言更新全绿 |

## 重点审查项 1-8 逐项核实

**1. standard_source 双源追踪正确性 — 成立。**
赋值时序：TRIAGE 行族分支 `elif not triage_family_found:` 首个非写入行命中后置位并原子设置 cols+source（:21252-21255）；EVD fallback 分支双条件门控（:21257-21258）——行族已找到时不触发；行族未找到但 EVD 已设时 `standard_cols is None` 阻止重复 fallback。覆盖关系：「EVD 行先于首个非写入 TRIAGE 行出现」布局下 EVD 先设 fallback，后续行族命中时 cols 与 source 同分支同步覆盖；反向布局 EVD 永不触发。来源字符串经 `{3}` 渲染入消息（:21269-21274）；渲染点唯一（失配分支），且该分支仅当 `standard_cols is not None` 时可达——不存在渲染空 source 的路径。边界：`record_id` 为空时 fail-closed 方向正确（既有行为，非本任务改动）。

**2. 失配消息增强的向后兼容 — 成立。**
消费方 grep 全量盘点：test_triage_write_guard.py :130-132/:178-179/:201-202/:245-246/:254-255（substring+计数断言）、:144-145（"record JSON invalid"——本任务未触碰）、:273/:287/:305（空断言）；test_verify_workflow.py 新测试。全部为 substring/计数断言，无全串相等断言。新消息保留既有前缀结构，仅在 `{2}` 后增补 `from the {3}` 段——既有断言语义全部保持。解析脆弱性：消息单行、无机器解析方（grep 实证消息字面量仅被测试 substring 断言引用，Check 14 evidence_col_mismatch :11611 为独立 check 路径，与 guard issue 无交集——本审已独立 grep 核验）。

**3. 新测试断言实质性 — 成立。**
双断言实质锁定（count==1 同时锁两个方向）；fixture 特意含 TRIAGE-OLD 10 列行族使「不误报」被 count 断言实质覆盖。红相推演：移除检测 → issues=[] → `len([])!=1` → AssertionError "0 != 1" → exit 1，与 Developer 红相实录逐字对应。测试 docstring 如实声明 green-by-coverage 性质——行为在位性由本审 :21262-21265 逐行读独立确认。可选增强见 F-1。

**4. remediation 无条件追加的取舍 — 可接受（F-2）。**
条件式措辞自限适用语境、主体段全类别通用、暴露面仅 guard 失败路径 stderr——低频低害；分流方案收益小于复杂度成本。

**5. docstring 契约例外声明 — 准确。**
「唯一例外重叠」与 Scope 段「ONLY the written artifacts are judged」形成显式例外关系；与 DEC-168 权威源裁决同义重述（"column contract is read FROM the evidence-log itself"）。

**6. 测试落点偏差 — 语义等价，可接受（F-3）。**
同一函数等价直接单测；差异仅测试组织。裁决：可接受，登记遗留。

**7. 范围纪律 — 成立。**
FIX-284 全仓 grep 命中 6 处全部落在声明 hunk 内；hunk 之外变更均属已审批次（:21300-21306 FIX-288、:21144-21171 FIX-236.3、:16707-16763 FIX-286），边界行号精确对齐。

**8. 来源覆盖完整性 — 全部承载，无扩界。**
P2-1 → :16766-16799 精确承载；P2-2 → 五处 hunk + docstring 承载（失配 issue 消息与 CLI remediation 双出口）。R0 P2-3 按 DEC-172 既有处置属观察项不在范围、实际未承载——与声明一致。

## 未验证声明

1. **测试执行结果**（748+89subtests/verify 五项/红相实录实际输出）——Developer 自报 + Coordinator 抽测（1 passed + 15 passed）佐证；本审只读未复跑。红相推演已由本审逐行核实与代码现状对应（**红相实际执行输出未独立复现**）。
2. **范围红线外两文件其余改动的完整性**——本审以 hunk 边界 + grep 命中分布核验，未对 FIX-283/286/287/288 批次自身做全量 diff 复核（不在本任务范围）（**未验证**）。
3. guard 唯一调用点与 check 路径无交集——本审已独立 grep 核验成立，不列入未验证。

## 遗留项表

| # | 级别 | 位置 | 遗留内容 | 建议关闭时点 |
|---|------|------|---------|-------------|
| F-1 | P3 | test_verify_workflow.py:16797-16799 | 可选补 `assertNotIn("columns", issues[0])` 显式负断言 | 0.78.x 后续测试卫生批（可选） |
| F-2 | P3 | verify_workflow.py:21356-21362 | remediation 按 issue 类别分流裁剪「列数标准来源」段 | 0.78.x 评估；现状可接受 |
| F-3 | P3 | test_verify_workflow.py:16766 | FIX-284 用例可迁移归并至 test_triage_write_guard.py 专用套件 | 下次该文件扩展时顺带（纯移动） |

---

**结论**：APPROVED_WITH_NOTES（unresolved_blockers=0）。可按 0.78.1 收口流程合并。Reviewer 全程只读，未修改任何文件。
